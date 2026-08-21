use std::env;
use std::ffi::{OsStr, OsString};
use std::fs::File;
use std::io::{self, IsTerminal, Read, Write};
use std::os::unix::ffi::OsStrExt;
use std::process;

use unicode_width::UnicodeWidthChar;

const SILLY: usize = usize::MAX;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum LocaleMode {
    C,
    Utf8,
}

#[derive(Debug)]
struct Invocation {
    argv: Vec<OsString>,
    locale_mode: LocaleMode,
    posixly_correct: bool,
}

impl Invocation {
    fn from_process() -> Self {
        Self {
            argv: env::args_os().collect(),
            locale_mode: locale_mode_from_environment(),
            posixly_correct: env::var_os("POSIXLY_CORRECT").is_some(),
        }
    }
}

#[derive(Clone, Debug)]
struct Config {
    center_p: bool,
    goal_length: usize,
    max_length: usize,
    coalesce_spaces_p: bool,
    allow_indented_paragraphs: bool,
    tab_width: usize,
    output_tab_width: usize,
    sentence_enders: Vec<u8>,
    grok_mail_headers: bool,
    format_troff: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            center_p: false,
            goal_length: 0,
            max_length: 0,
            coalesce_spaces_p: false,
            allow_indented_paragraphs: false,
            tab_width: 8,
            output_tab_width: 0,
            sentence_enders: b".?!".to_vec(),
            grok_mail_headers: false,
            format_troff: false,
        }
    }
}

#[derive(Debug)]
struct ParsedInvocation {
    program_name: Vec<u8>,
    config: Config,
    files: Vec<OsString>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum PositiveParse {
    Value(usize),
    NotNumber,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct FatalError {
    message: &'static [u8],
}

#[derive(Debug)]
enum InvocationError {
    Fatal(FatalError),
    Usage { diagnostic: Option<Vec<u8>> },
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(i8)]
enum HdrType {
    ParagraphStart = -1,
    NonHeader = 0,
    Header = 1,
    Continuation = 2,
}

impl HdrType {
    fn is_nonzero(self) -> bool {
        self != Self::NonHeader
    }

    fn is_positive(self) -> bool {
        matches!(self, Self::Header | Self::Continuation)
    }
}

#[derive(Debug, Default)]
struct RunState {
    n_errors: u8,
}

impl RunState {
    fn record_error(&mut self) {
        if self.n_errors < 127 {
            self.n_errors += 1;
        }
    }
}

#[derive(Debug, Default)]
struct Formatter {
    x: usize,
    x0: usize,
    pending_spaces: usize,
    output_in_paragraph: bool,
}

struct CompatibilityWriter<'a> {
    inner: &'a mut dyn Write,
    failed: bool,
}

impl<'a> CompatibilityWriter<'a> {
    fn new(inner: &'a mut dyn Write) -> Self {
        Self {
            inner,
            failed: false,
        }
    }

    fn write_all(&mut self, bytes: &[u8]) {
        if !self.failed && self.inner.write_all(bytes).is_err() {
            self.failed = true;
        }
    }

    fn flush(&mut self) {
        if !self.failed && self.inner.flush().is_err() {
            self.failed = true;
        }
    }
}

// glibc uses a 4096-byte full buffer for redirected stdout on this target.
struct FullyBufferedWriter<'a> {
    inner: &'a mut dyn Write,
    buffer: [u8; 4096],
    length: usize,
}

impl<'a> FullyBufferedWriter<'a> {
    fn new(inner: &'a mut dyn Write) -> Self {
        Self {
            inner,
            buffer: [0; 4096],
            length: 0,
        }
    }

    fn flush_buffer(&mut self) -> io::Result<()> {
        self.inner.write_all(&self.buffer[..self.length])?;
        self.length = 0;
        Ok(())
    }
}

impl Write for FullyBufferedWriter<'_> {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        if bytes.is_empty() {
            return Ok(0);
        }
        if self.length == self.buffer.len() {
            self.flush_buffer()?;
        }
        let count = bytes.len().min(self.buffer.len() - self.length);
        self.buffer[self.length..self.length + count].copy_from_slice(&bytes[..count]);
        self.length += count;
        Ok(count)
    }

    fn flush(&mut self) -> io::Result<()> {
        self.flush_buffer()?;
        self.inner.flush()
    }
}

trait FileOpener {
    fn open(&mut self, path: &OsStr) -> io::Result<Box<dyn Read>>;
}

struct RealFileOpener;

impl FileOpener for RealFileOpener {
    fn open(&mut self, path: &OsStr) -> io::Result<Box<dyn Read>> {
        File::open(path).map(|file| Box::new(file) as Box<dyn Read>)
    }
}

#[derive(Clone, Copy)]
enum InputName<'a> {
    StandardInput,
    Path(&'a OsStr),
}

struct LineReader<'a> {
    stream: &'a mut dyn Read,
    buffer: Vec<u8>,
    buffer_offset: usize,
    pending_error: Option<io::Error>,
    reached_eof: bool,
}

impl<'a> LineReader<'a> {
    fn new(stream: &'a mut dyn Read) -> Self {
        Self {
            stream,
            buffer: Vec::new(),
            buffer_offset: 0,
            pending_error: None,
            reached_eof: false,
        }
    }
}

enum LineEvent {
    Line(Vec<u8>),
    End,
    ReadError(io::Error),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DisplayUnit {
    byte_len: usize,
    width: usize,
    character: Option<char>,
    valid: bool,
}

fn process_program_name(argv0: Option<&OsStr>) -> Vec<u8> {
    let bytes = argv0.map(OsStrExt::as_bytes).unwrap_or_default();
    bytes
        .rsplit(|byte| *byte == b'/')
        .next()
        .unwrap_or_default()
        .to_vec()
}

fn locale_mode_from_environment() -> LocaleMode {
    let locale = ["LC_ALL", "LC_CTYPE", "LANG"]
        .iter()
        .filter_map(|name| env::var_os(name))
        .map(|value| value.as_bytes().to_vec())
        .find(|value| !value.is_empty());

    let Some(locale) = locale else {
        return LocaleMode::C;
    };
    if is_available_utf8_locale(&locale) {
        LocaleMode::Utf8
    } else {
        LocaleMode::C
    }
}

fn is_available_utf8_locale(locale: &[u8]) -> bool {
    let Some(codeset) = locale.strip_prefix(b"C.") else {
        return false;
    };
    let codeset_length = if codeset
        .get(..5)
        .is_some_and(|value| value.eq_ignore_ascii_case(b"UTF-8"))
    {
        5
    } else if codeset
        .get(..4)
        .is_some_and(|value| value.eq_ignore_ascii_case(b"UTF8"))
    {
        4
    } else {
        return false;
    };
    let suffix = &codeset[codeset_length..];
    suffix.is_empty()
        || suffix.iter().all(u8::is_ascii_whitespace)
        || (suffix.first() == Some(&b'@') && !suffix.contains(&b'/'))
}

fn option_diagnostic(program_name: &[u8], prefix: &[u8], option: u8) -> Vec<u8> {
    let mut diagnostic = Vec::with_capacity(program_name.len() + prefix.len() + 4);
    diagnostic.extend_from_slice(program_name);
    diagnostic.extend_from_slice(prefix);
    diagnostic.push(option);
    diagnostic.extend_from_slice(b"'\n");
    diagnostic
}

fn parse_invocation(invocation: &Invocation) -> Result<ParsedInvocation, InvocationError> {
    let program_name = process_program_name(invocation.argv.first().map(OsString::as_os_str));
    let getopt_program_name = invocation
        .argv
        .first()
        .map(|argument| argument.as_os_str().as_bytes())
        .unwrap_or_default();
    let mut config = Config::default();
    let mut files = Vec::new();
    let mut index = 1;

    while index < invocation.argv.len() {
        let argument = invocation.argv[index].as_os_str();
        let bytes = argument.as_bytes();

        if bytes == b"--" {
            files.extend(invocation.argv[index + 1..].iter().cloned());
            break;
        }

        if bytes.len() <= 1 || bytes[0] != b'-' {
            if invocation.posixly_correct {
                files.extend(invocation.argv[index..].iter().cloned());
                break;
            }
            files.push(invocation.argv[index].clone());
            index += 1;
            continue;
        }

        let mut option_index = 1;
        while option_index < bytes.len() {
            let option = bytes[option_index];
            match option {
                b'c' => config.center_p = true,
                b'm' => config.grok_mail_headers = true,
                b'n' => config.format_troff = true,
                b'p' => config.allow_indented_paragraphs = true,
                b's' => config.coalesce_spaces_p = true,
                b'h' => {
                    return Err(InvocationError::Usage { diagnostic: None });
                }
                b'd' | b'l' | b't' | b'w' => {
                    let value = if option_index + 1 < bytes.len() {
                        &bytes[option_index + 1..]
                    } else {
                        index += 1;
                        if index >= invocation.argv.len() {
                            return Err(InvocationError::Usage {
                                diagnostic: Some(option_diagnostic(
                                    getopt_program_name,
                                    b": option requires an argument -- '",
                                    option,
                                )),
                            });
                        }
                        invocation.argv[index].as_os_str().as_bytes()
                    };

                    match option {
                        b'd' => config.sentence_enders = value.to_vec(),
                        b'l' => {
                            config.output_tab_width =
                                positive_value(value, b"output tab width must be positive")?;
                        }
                        b't' => {
                            config.tab_width =
                                positive_value(value, b"tab width must be positive")?;
                        }
                        b'w' => {
                            config.goal_length = positive_value(value, b"width must be positive")?;
                            config.max_length = config.goal_length;
                        }
                        _ => unreachable!(),
                    }
                    option_index = bytes.len();
                    continue;
                }
                b'0'..=b'9' => {
                    if config.goal_length == 0 {
                        // fmt reads either the complete legacy token or argv[optind] + 1.
                        // The latter is the following argument when a digit ends a bundle.
                        let value = if bytes.len() == 2 {
                            &bytes[1..]
                        } else if option_index + 1 < bytes.len() {
                            &bytes[1..]
                        } else {
                            invocation
                                .argv
                                .get(index + 1)
                                .map(|argument| {
                                    argument.as_os_str().as_bytes().get(1..).unwrap_or_default()
                                })
                                .unwrap_or_default()
                        };
                        config.goal_length = positive_value(value, b"width must be nonzero")?;
                        config.max_length = config.goal_length;
                    }
                }
                unknown => {
                    return Err(InvocationError::Usage {
                        diagnostic: Some(option_diagnostic(
                            getopt_program_name,
                            b": invalid option -- '",
                            unknown,
                        )),
                    });
                }
            }
            option_index += 1;
        }
        index += 1;
    }

    if config.goal_length == 0 && !files.is_empty() {
        match get_positive(
            files[0].as_os_str().as_bytes(),
            b"goal length must be positive",
            false,
        )
        .map_err(InvocationError::Fatal)?
        {
            PositiveParse::NotNumber => {}
            PositiveParse::Value(goal) => {
                config.goal_length = goal;
                files.remove(0);
                if !files.is_empty() {
                    match get_positive(
                        files[0].as_os_str().as_bytes(),
                        b"max length must be positive",
                        false,
                    )
                    .map_err(InvocationError::Fatal)?
                    {
                        PositiveParse::NotNumber => {}
                        PositiveParse::Value(maximum) => {
                            config.max_length = maximum;
                            files.remove(0);
                            if config.max_length < config.goal_length {
                                return Err(InvocationError::Fatal(FatalError {
                                    message: b"max length must be >= goal length",
                                }));
                            }
                        }
                    }
                }
            }
        }
    }

    if config.goal_length == 0 {
        config.goal_length = 65;
    }
    if config.max_length == 0 {
        config.max_length = config.goal_length.wrapping_add(10);
    }

    Ok(ParsedInvocation {
        program_name,
        config,
        files,
    })
}

fn positive_value(s: &[u8], message: &'static [u8]) -> Result<usize, InvocationError> {
    match get_positive(s, message, true).map_err(InvocationError::Fatal)? {
        PositiveParse::Value(value) => Ok(value),
        PositiveParse::NotNumber => unreachable!(),
    }
}

fn get_positive(
    s: &[u8],
    err_mess: &'static [u8],
    fussy_p: bool,
) -> Result<PositiveParse, FatalError> {
    let input = match s.iter().position(|byte| *byte == 0) {
        Some(end) => &s[..end],
        None => s,
    };
    let mut cursor = 0;
    while cursor < input.len() && input[cursor].is_ascii_whitespace() {
        cursor += 1;
    }

    let mut negative = false;
    if cursor < input.len() && matches!(input[cursor], b'+' | b'-') {
        negative = input[cursor] == b'-';
        cursor += 1;
    }

    let mut base = 10_u128;
    if cursor < input.len() && input[cursor] == b'0' {
        if cursor + 2 < input.len()
            && matches!(input[cursor + 1], b'x' | b'X')
            && input[cursor + 2].is_ascii_hexdigit()
        {
            base = 16;
            cursor += 2;
        } else if cursor + 2 < input.len()
            && matches!(input[cursor + 1], b'b' | b'B')
            && matches!(input[cursor + 2], b'0' | b'1')
        {
            base = 2;
            cursor += 2;
        } else {
            base = 8;
        }
    }

    let digit_start = cursor;
    let mut magnitude = 0_u128;
    while cursor < input.len() {
        let digit = match input[cursor] {
            b'0'..=b'9' => u128::from(input[cursor] - b'0'),
            b'a'..=b'f' => u128::from(input[cursor] - b'a' + 10),
            b'A'..=b'F' => u128::from(input[cursor] - b'A' + 10),
            _ => break,
        };
        if digit >= base {
            break;
        }
        magnitude = magnitude.saturating_mul(base).saturating_add(digit);
        cursor += 1;
    }

    let converted = cursor > digit_start;
    let end = if converted { cursor } else { 0 };
    if end < input.len() {
        if fussy_p {
            return Err(FatalError { message: err_mess });
        }
        return Ok(PositiveParse::NotNumber);
    }

    if !converted || negative || magnitude == 0 {
        return Err(FatalError { message: err_mess });
    }

    const LONG_MAX: u128 = i64::MAX as u128;
    Ok(PositiveParse::Value(magnitude.min(LONG_MAX) as usize))
}

#[allow(clippy::too_many_arguments)]
fn process_named_file(
    name: &OsStr,
    config: &Config,
    locale_mode: LocaleMode,
    file_opener: &mut dyn FileOpener,
    stdout: &mut CompatibilityWriter<'_>,
    stderr: &mut dyn Write,
    program_name: &[u8],
    state: &mut RunState,
) -> Result<(), FatalError> {
    match file_opener.open(name) {
        Ok(mut stream) => process_stream(
            &mut *stream,
            InputName::Path(name),
            config,
            locale_mode,
            stdout,
            stderr,
            program_name,
            state,
        ),
        Err(error) => {
            warn_io(program_name, InputName::Path(name), &error, stderr);
            state.record_error();
            Ok(())
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn process_stream(
    stream: &mut dyn Read,
    name: InputName<'_>,
    config: &Config,
    locale_mode: LocaleMode,
    stdout: &mut CompatibilityWriter<'_>,
    stderr: &mut dyn Write,
    program_name: &[u8],
    state: &mut RunState,
) -> Result<(), FatalError> {
    if config.center_p {
        return center_stream(
            stream,
            name,
            config,
            locale_mode,
            stdout,
            stderr,
            program_name,
            state,
        );
    }

    let mut reader = LineReader::new(stream);
    let mut formatter = Formatter::default();
    let mut last_indent = SILLY;
    let mut para_line_number = 0_usize;
    let mut first_indent = SILLY;
    let mut prev_header_type = HdrType::ParagraphStart;
    let mut read_error = None;

    loop {
        let line = match get_line(&mut reader, config, locale_mode)? {
            LineEvent::Line(line) => line,
            LineEvent::End => break,
            LineEvent::ReadError(error) => {
                read_error = Some(error);
                break;
            }
        };
        let line = c_string_slice(&line);
        let np = indent_length(line, config.tab_width);
        let mut header_type = HdrType::NonHeader;
        if config.grok_mail_headers && prev_header_type.is_nonzero() {
            if np == 0 && might_be_header(line, locale_mode) {
                header_type = HdrType::Header;
            } else if np > 0 && prev_header_type.is_positive() {
                header_type = HdrType::Continuation;
            }
        }

        let dot_line = line.first() == Some(&b'.') && !config.format_troff;
        if line.is_empty()
            || dot_line
            || header_type == HdrType::Header
            || (header_type == HdrType::NonHeader && prev_header_type.is_positive())
            || (np != last_indent
                && header_type != HdrType::Continuation
                && (!config.allow_indented_paragraphs || para_line_number != 1))
        {
            new_paragraph(&mut formatter, np, stdout);
            para_line_number = 0;
            first_indent = np;
            last_indent = np;

            if dot_line {
                stdout.write_all(line);
                stdout.write_all(b"\n");
                continue;
            }
            if header_type == HdrType::Header {
                last_indent = 2;
            }
            if line.is_empty() {
                stdout.write_all(b"\n");
                prev_header_type = HdrType::ParagraphStart;
                continue;
            } else if np != last_indent && header_type != HdrType::Continuation {
                last_indent = np;
            }
            prev_header_type = header_type;
        }

        let mut line_width = np;
        let mut wordp = 0_usize;
        while wordp < line.len() {
            let mut cp = wordp;
            let mut word_length = 0_usize;
            let mut word_width = 0_usize;
            let mut space_width = 0_usize;

            while cp < line.len() {
                let unit = decode_display_unit(&line[cp..], locale_mode);
                if unit.byte_len == 0 {
                    break;
                }
                let width = if unit.character == Some('\t') {
                    next_tab_width(line_width, config.tab_width)
                } else {
                    unit.width
                };
                let is_blank =
                    unit.character.is_some_and(is_wide_blank) && unit.character != Some('\u{00a0}');

                if is_blank {
                    if word_length == 0 {
                        wordp += unit.byte_len;
                        cp += unit.byte_len;
                        continue;
                    }
                    space_width = space_width.wrapping_add(width);
                } else {
                    if space_width > 0 {
                        break;
                    }
                    word_length += unit.byte_len;
                    word_width = word_width.wrapping_add(width);
                }
                line_width = line_width.wrapping_add(width);
                cp += unit.byte_len;
            }

            if word_length == 0 {
                break;
            }
            let word_end = wordp + word_length;
            output_word(
                config,
                &mut formatter,
                first_indent,
                last_indent,
                &line[wordp..word_end],
                word_length,
                word_width,
                space_width,
                stdout,
            );
            wordp = cp;
        }
        para_line_number = para_line_number.wrapping_add(1);
    }

    new_paragraph(&mut formatter, 0, stdout);
    if let Some(error) = read_error {
        warn_io(program_name, name, &error, stderr);
        state.record_error();
    }
    Ok(())
}

fn decode_display_unit(input: &[u8], locale_mode: LocaleMode) -> DisplayUnit {
    let Some(&first) = input.first() else {
        return DisplayUnit {
            byte_len: 0,
            width: 0,
            character: None,
            valid: false,
        };
    };

    if locale_mode == LocaleMode::C && !first.is_ascii() {
        return invalid_display_unit();
    }

    // glibc's UTF-8 mbtowc still accepts the historical five- and six-byte forms.
    let (expected, mut value, minimum) = match first {
        0x00..=0x7f => (1, u32::from(first), 0),
        0xc2..=0xdf => (2, u32::from(first & 0x1f), 0x80),
        0xe0..=0xef => (3, u32::from(first & 0x0f), 0x800),
        0xf0..=0xf7 => (4, u32::from(first & 0x07), 0x1_0000),
        0xf8..=0xfb => (5, u32::from(first & 0x03), 0x20_0000),
        0xfc..=0xfd => (6, u32::from(first & 0x01), 0x400_0000),
        _ => return invalid_display_unit(),
    };
    if input.len() < expected {
        return invalid_display_unit();
    }
    for &continuation in &input[1..expected] {
        if continuation & 0xc0 != 0x80 {
            return invalid_display_unit();
        }
        value = (value << 6) | u32::from(continuation & 0x3f);
    }
    if value < minimum || (0xd800..=0xdfff).contains(&value) {
        return invalid_display_unit();
    }

    let character = char::from_u32(value);

    DisplayUnit {
        byte_len: expected,
        width: character.map(display_width).unwrap_or(1),
        character,
        valid: true,
    }
}

fn display_width(character: char) -> usize {
    let value = character as u32;
    // The pinned crate shares glibc's Unicode version; these are wcwidth policy differences.
    match value {
        0x2d7f | 0xfff9..=0xfffb | 0x13430..=0x1343f => 0,
        0x302e..=0x302f | 0x3164 | 0x3248..=0x324f | 0x4dc0..=0x4dff => 2,
        0x00ad
        | 0x0605
        | 0x070f
        | 0x0890..=0x0891
        | 0x08e2
        | 0x09be
        | 0x09d7
        | 0x0b3e
        | 0x0b57
        | 0x0bbe
        | 0x0bd7
        | 0x0cc0
        | 0x0cc2
        | 0x0cc7..=0x0cc8
        | 0x0cca..=0x0ccb
        | 0x0cd5..=0x0cd6
        | 0x0d3e
        | 0x0d4e
        | 0x0d57
        | 0x0dcf
        | 0x0ddf
        | 0x17a4
        | 0x17d8
        | 0x1b35
        | 0x1b3b
        | 0x1b3d
        | 0x1b43
        | 0x2065
        | 0xa8fa
        | 0xfa6e..=0xfa6f
        | 0xfada..=0xfaff
        | 0xff9e..=0xffa0
        | 0xfff0..=0xfff8
        | 0x111c2..=0x111c3
        | 0x1133e
        | 0x11357
        | 0x114b0
        | 0x114bd
        | 0x115af
        | 0x11930
        | 0x1193f
        | 0x11941
        | 0x11a3a
        | 0x11a84..=0x11a89
        | 0x11d46
        | 0x11f02
        | 0x1d165
        | 0x1d16e..=0x1d172
        | 0x2a6e0..=0x2a6ff
        | 0x2b73a..=0x2b73f
        | 0x2b81e..=0x2b81f
        | 0x2cea2..=0x2ceaf
        | 0x2ebe1..=0x2ebef
        | 0x2ee5e..=0x2f7ff
        | 0x2fa1e..=0x2fffd
        | 0x3134b..=0x3134f
        | 0x323b0..=0x3fffd
        | 0xe0000
        | 0xe0002..=0xe001f
        | 0xe0080..=0xe00ff
        | 0xe01f0..=0xe0fff => 1,
        _ => UnicodeWidthChar::width(character).unwrap_or(1),
    }
}

fn invalid_display_unit() -> DisplayUnit {
    DisplayUnit {
        byte_len: 1,
        width: 1,
        character: None,
        valid: false,
    }
}

fn is_wide_blank(character: char) -> bool {
    matches!(
        character,
        '\t' | ' ' | '\u{1680}' | '\u{2000}'..='\u{2006}' | '\u{2008}'
            ..='\u{200a}' | '\u{205f}' | '\u{3000}'
    )
}

fn is_wide_space(character: char) -> bool {
    matches!(
        character,
        '\t'..='\r'
            | ' '
            | '\u{1680}'
            | '\u{2000}'..='\u{2006}'
            | '\u{2008}'..='\u{200a}'
            | '\u{2028}'
            | '\u{2029}'
            | '\u{205f}'
            | '\u{3000}'
    )
}

fn is_narrow_control(byte: u8, _locale_mode: LocaleMode) -> bool {
    byte < b' ' || byte == 0x7f
}

fn is_narrow_space(byte: u8, _locale_mode: LocaleMode) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | 0x0b | 0x0c | b'\r')
}

fn next_tab_width(column: usize, tab_width: usize) -> usize {
    let next = (column / tab_width).wrapping_add(1).wrapping_mul(tab_width);
    next.wrapping_sub(column)
}

fn indent_length(line: &[u8], tab_width: usize) -> usize {
    let mut width = 0_usize;
    for byte in line {
        match byte {
            b' ' => width = width.wrapping_add(1),
            b'\t' => width = width.wrapping_add(next_tab_width(width, tab_width)),
            _ => break,
        }
    }
    width
}

fn might_be_header(line: &[u8], locale_mode: LocaleMode) -> bool {
    if !line.first().is_some_and(u8::is_ascii_uppercase) {
        return false;
    }
    let mut cursor = 1;
    while cursor < line.len() && (line[cursor].is_ascii_alphanumeric() || line[cursor] == b'-') {
        cursor += 1;
    }
    cursor + 1 < line.len()
        && line[cursor] == b':'
        && is_narrow_space(line[cursor + 1], locale_mode)
}

fn new_paragraph(formatter: &mut Formatter, indent: usize, stdout: &mut CompatibilityWriter<'_>) {
    if formatter.x0 > 0 {
        stdout.write_all(b"\n");
    }
    formatter.x = indent;
    formatter.x0 = 0;
    formatter.pending_spaces = 0;
    formatter.output_in_paragraph = false;
}

fn write_spaces(count: usize, stdout: &mut CompatibilityWriter<'_>) {
    const SPACES: &[u8; 128] = &[b' '; 128];
    let mut remaining = count;
    while remaining > 0 {
        let amount = remaining.min(SPACES.len());
        stdout.write_all(&SPACES[..amount]);
        remaining -= amount;
    }
}

fn output_indent(config: &Config, mut n_spaces: usize, stdout: &mut CompatibilityWriter<'_>) {
    if config.output_tab_width > 0 {
        while n_spaces >= config.output_tab_width {
            stdout.write_all(b"\t");
            n_spaces -= config.output_tab_width;
        }
    }
    write_spaces(n_spaces, stdout);
}

#[allow(clippy::too_many_arguments)]
fn output_word(
    config: &Config,
    formatter: &mut Formatter,
    indent0: usize,
    indent1: usize,
    word: &[u8],
    length: usize,
    width: usize,
    mut spaces: usize,
    stdout: &mut CompatibilityWriter<'_>,
) {
    let new_x = formatter
        .x
        .wrapping_add(formatter.pending_spaces)
        .wrapping_add(width);

    if config.coalesce_spaces_p || spaces == 0 {
        spaces = if word
            .get(length.wrapping_sub(1))
            .is_some_and(|byte| config.sentence_enders.contains(byte))
        {
            2
        } else {
            1
        };
    }

    if formatter.x0 == 0 {
        output_indent(
            config,
            if formatter.output_in_paragraph {
                indent1
            } else {
                indent0
            },
            stdout,
        );
    } else if new_x > config.max_length
        || formatter.x >= config.goal_length
        || (new_x > config.goal_length
            && new_x - config.goal_length > config.goal_length - formatter.x)
    {
        stdout.write_all(b"\n");
        output_indent(config, indent1, stdout);
        formatter.x0 = 0;
        formatter.x = indent1;
    } else {
        formatter.x0 = formatter.x0.wrapping_add(formatter.pending_spaces);
        formatter.x = formatter.x.wrapping_add(formatter.pending_spaces);
        write_spaces(formatter.pending_spaces, stdout);
    }

    formatter.x0 = formatter.x0.wrapping_add(width);
    formatter.x = formatter.x.wrapping_add(width);
    stdout.write_all(&word[..length]);
    formatter.pending_spaces = spaces;
    formatter.output_in_paragraph = true;
}

#[allow(clippy::too_many_arguments)]
fn center_stream(
    stream: &mut dyn Read,
    name: InputName<'_>,
    config: &Config,
    locale_mode: LocaleMode,
    stdout: &mut CompatibilityWriter<'_>,
    stderr: &mut dyn Write,
    program_name: &[u8],
    state: &mut RunState,
) -> Result<(), FatalError> {
    let mut reader = LineReader::new(stream);
    let mut read_error = None;
    let mut last_character = Some('?');

    loop {
        let mut line = match get_line(&mut reader, config, locale_mode)? {
            LineEvent::Line(line) => line,
            LineEvent::End => break,
            LineEvent::ReadError(error) => {
                read_error = Some(error);
                break;
            }
        };
        if let Some(nul) = line.iter().position(|byte| *byte == 0) {
            line.truncate(nul);
        }

        let mut line_start = 0_usize;
        let mut line_width = 0_usize;
        let mut cursor = 0_usize;
        while cursor < line.len() {
            if line[cursor] == b'\t' {
                line[cursor] = b' ';
            }
            let unit = decode_display_unit(&line[cursor..], locale_mode);
            if unit.byte_len == 0 {
                break;
            }
            let (width, space_character) = if unit.valid {
                last_character = unit.character;
                (unit.width, unit.character)
            } else {
                line[cursor] = b'?';
                (1, last_character)
            };
            if line_width == 0 && space_character.is_some_and(is_wide_space) {
                line_start = line_start.wrapping_add(unit.byte_len).min(line.len());
            } else {
                line_width = line_width.wrapping_add(width);
            }
            cursor += unit.byte_len;
        }

        while line_width < config.goal_length {
            stdout.write_all(b" ");
            line_width = line_width.wrapping_add(2);
        }
        stdout.write_all(&line[line_start..]);
        stdout.write_all(b"\n");
    }

    if let Some(error) = read_error {
        warn_io(program_name, name, &error, stderr);
        state.record_error();
    }
    Ok(())
}

fn get_line(
    reader: &mut LineReader<'_>,
    config: &Config,
    locale_mode: LocaleMode,
) -> Result<LineEvent, FatalError> {
    if let Some(error) = reader.pending_error.take() {
        return Ok(LineEvent::ReadError(error));
    }

    let mut raw_line = Vec::new();
    let mut ended_with_newline = false;
    let mut encountered_error = None;

    loop {
        if reader.buffer_offset < reader.buffer.len() {
            let available = &reader.buffer[reader.buffer_offset..];
            if let Some(newline) = available.iter().position(|byte| *byte == b'\n') {
                reserve_line_buffer(&mut raw_line, newline)?;
                raw_line.extend_from_slice(&available[..newline]);
                reader.buffer_offset += newline + 1;
                ended_with_newline = true;
                break;
            }
            reserve_line_buffer(&mut raw_line, available.len())?;
            raw_line.extend_from_slice(available);
            reader.buffer_offset = reader.buffer.len();
            continue;
        }

        if reader.reached_eof {
            break;
        }

        let mut chunk = [0_u8; 8192];
        match reader.stream.read(&mut chunk) {
            Ok(0) => {
                reader.reached_eof = true;
                break;
            }
            Ok(count) => {
                reader.buffer.clear();
                reader.buffer_offset = 0;
                reserve_line_buffer(&mut reader.buffer, count)?;
                reader.buffer.extend_from_slice(&chunk[..count]);
            }
            Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
            Err(error) => {
                reader.reached_eof = true;
                encountered_error = Some(error);
                break;
            }
        }
    }

    let mut line = Vec::new();
    reserve_line_buffer(&mut line, raw_line.len())?;
    let mut troff = false;
    for byte in raw_line {
        if line.is_empty() && byte == b'.' && !config.format_troff {
            troff = true;
        }
        if troff || byte == b'\t' || !is_narrow_control(byte, locale_mode) {
            line.push(byte);
        } else if byte == b'\x08' {
            line.pop();
        }
    }
    while line
        .last()
        .is_some_and(|byte| is_narrow_space(*byte, locale_mode))
    {
        line.pop();
    }

    if ended_with_newline || !line.is_empty() {
        reader.pending_error = encountered_error;
        return Ok(LineEvent::Line(line));
    }
    if let Some(error) = encountered_error {
        return Ok(LineEvent::ReadError(error));
    }
    Ok(LineEvent::End)
}

fn reserve_line_buffer(buffer: &mut Vec<u8>, additional: usize) -> Result<(), FatalError> {
    buffer.try_reserve(additional).map_err(|_| FatalError {
        message: b"out of memory",
    })
}

fn c_string_slice(line: &[u8]) -> &[u8] {
    match line.iter().position(|byte| *byte == 0) {
        Some(end) => &line[..end],
        None => line,
    }
}

fn usage(program_name: &[u8], stderr: &mut dyn Write) {
    let _ = stderr.write_all(b"usage: ");
    let _ = stderr.write_all(program_name);
    let _ = stderr.write_all(
        b" [-cmnps] [-d chars] [-l number] [-t number]\n\
\t[goal [maximum] | -width | -w width] [file ...]\n",
    );
}

fn input_name_bytes(name: InputName<'_>) -> &[u8] {
    match name {
        InputName::StandardInput => b"standard input",
        InputName::Path(path) => path.as_bytes(),
    }
}

fn warn_io(program_name: &[u8], name: InputName<'_>, error: &io::Error, stderr: &mut dyn Write) {
    let _ = stderr.write_all(program_name);
    let _ = stderr.write_all(b": ");
    let _ = stderr.write_all(input_name_bytes(name));
    let _ = stderr.write_all(b": ");

    let mut message = error.to_string();
    if let Some(code) = error.raw_os_error() {
        let suffix = format!(" (os error {code})");
        if message.ends_with(&suffix) {
            message.truncate(message.len() - suffix.len());
        }
    }
    let _ = stderr.write_all(message.as_bytes());
    let _ = stderr.write_all(b"\n");
}

fn render_invocation_error(
    program_name: &[u8],
    error: InvocationError,
    stderr: &mut dyn Write,
) -> u8 {
    match error {
        InvocationError::Fatal(error) => {
            let _ = stderr.write_all(program_name);
            let _ = stderr.write_all(b": ");
            let _ = stderr.write_all(error.message);
            let _ = stderr.write_all(b"\n");
        }
        InvocationError::Usage { diagnostic } => {
            if let Some(diagnostic) = diagnostic {
                let _ = stderr.write_all(&diagnostic);
            }
            usage(program_name, stderr);
        }
    }
    1
}

fn run(
    invocation: Invocation,
    stdin: &mut dyn Read,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
    file_opener: &mut dyn FileOpener,
) -> u8 {
    let program_name = process_program_name(invocation.argv.first().map(OsString::as_os_str));
    let parsed = match parse_invocation(&invocation) {
        Ok(parsed) => parsed,
        Err(error) => return render_invocation_error(&program_name, error, stderr),
    };

    let mut stdout = CompatibilityWriter::new(stdout);
    let mut state = RunState::default();
    let result = if parsed.files.is_empty() {
        process_stream(
            stdin,
            InputName::StandardInput,
            &parsed.config,
            invocation.locale_mode,
            &mut stdout,
            stderr,
            &parsed.program_name,
            &mut state,
        )
    } else {
        let mut result = Ok(());
        for file in &parsed.files {
            result = process_named_file(
                file,
                &parsed.config,
                invocation.locale_mode,
                file_opener,
                &mut stdout,
                stderr,
                &parsed.program_name,
                &mut state,
            );
            if result.is_err() {
                break;
            }
        }
        result
    };

    stdout.flush();
    match result {
        Ok(()) => state.n_errors,
        Err(error) => {
            let _ = stderr.write_all(&parsed.program_name);
            let _ = stderr.write_all(b": ");
            let _ = stderr.write_all(error.message);
            let _ = stderr.write_all(b"\n");
            1
        }
    }
}

fn main() {
    let invocation = Invocation::from_process();
    let stdin = io::stdin();
    let stdout = io::stdout();
    let stderr = io::stderr();
    let stdout_is_terminal = stdout.is_terminal();
    let mut stdin = stdin.lock();
    let mut stdout = stdout.lock();
    let mut stderr = stderr.lock();
    let mut file_opener = RealFileOpener;

    let status = if stdout_is_terminal {
        run(
            invocation,
            &mut stdin,
            &mut stdout,
            &mut stderr,
            &mut file_opener,
        )
    } else {
        let mut stdout = FullyBufferedWriter::new(&mut stdout);
        run(
            invocation,
            &mut stdin,
            &mut stdout,
            &mut stderr,
            &mut file_opener,
        )
    };
    process::exit(i32::from(status));
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::{HashMap, VecDeque};
    use std::io::Cursor;

    enum MockOpen {
        Bytes(Vec<u8>),
        Error(io::ErrorKind, &'static str),
        RawOsError(i32),
        ReadError(Vec<u8>, io::ErrorKind, &'static str),
        RawOsReadError(Vec<u8>, i32),
    }

    #[derive(Default)]
    struct MockFileOpener {
        entries: HashMap<OsString, VecDeque<MockOpen>>,
        opened: Vec<OsString>,
    }

    impl MockFileOpener {
        fn with_entry(mut self, path: OsString, entry: MockOpen) -> Self {
            self.entries.entry(path).or_default().push_back(entry);
            self
        }

        fn with_bytes(mut self, path: OsString, bytes: Vec<u8>) -> Self {
            self = self.with_entry(path, MockOpen::Bytes(bytes));
            self
        }

        fn with_error(
            mut self,
            path: OsString,
            kind: io::ErrorKind,
            message: &'static str,
        ) -> Self {
            self = self.with_entry(path, MockOpen::Error(kind, message));
            self
        }

        fn with_raw_os_error(mut self, path: OsString, code: i32) -> Self {
            self = self.with_entry(path, MockOpen::RawOsError(code));
            self
        }

        fn with_read_error(
            mut self,
            path: OsString,
            prefix: Vec<u8>,
            kind: io::ErrorKind,
            message: &'static str,
        ) -> Self {
            self = self.with_entry(path, MockOpen::ReadError(prefix, kind, message));
            self
        }

        fn with_raw_os_read_error(mut self, path: OsString, prefix: Vec<u8>, code: i32) -> Self {
            self = self.with_entry(path, MockOpen::RawOsReadError(prefix, code));
            self
        }
    }

    impl FileOpener for MockFileOpener {
        fn open(&mut self, path: &OsStr) -> io::Result<Box<dyn Read>> {
            self.opened.push(path.to_os_string());
            let entry = self.entries.get_mut(path).and_then(VecDeque::pop_front);
            if self.entries.get(path).is_some_and(VecDeque::is_empty) {
                self.entries.remove(path);
            }
            match entry {
                Some(MockOpen::Bytes(bytes)) => Ok(Box::new(Cursor::new(bytes))),
                Some(MockOpen::Error(kind, message)) => Err(io::Error::new(kind, message)),
                Some(MockOpen::RawOsError(code)) => Err(io::Error::from_raw_os_error(code)),
                Some(MockOpen::ReadError(prefix, kind, message)) => Ok(Box::new(
                    PrefixThenErrorReader::new(prefix, io::Error::new(kind, message)),
                )),
                Some(MockOpen::RawOsReadError(prefix, code)) => Ok(Box::new(
                    PrefixThenErrorReader::new(prefix, io::Error::from_raw_os_error(code)),
                )),
                None => Err(io::Error::new(
                    io::ErrorKind::NotFound,
                    "mock path was not configured",
                )),
            }
        }
    }

    struct PrefixThenErrorReader {
        prefix: Cursor<Vec<u8>>,
        error: Option<io::Error>,
    }

    impl PrefixThenErrorReader {
        fn new(prefix: Vec<u8>, error: io::Error) -> Self {
            Self {
                prefix: Cursor::new(prefix),
                error: Some(error),
            }
        }
    }

    impl Read for PrefixThenErrorReader {
        fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
            let count = self.prefix.read(buffer)?;
            if count > 0 {
                return Ok(count);
            }
            match self.error.take() {
                Some(error) => Err(error),
                None => Ok(0),
            }
        }
    }

    struct FailingWriter {
        bytes_before_error: usize,
        bytes: Vec<u8>,
        flush_fails: bool,
    }

    impl FailingWriter {
        fn new(bytes_before_error: usize, flush_fails: bool) -> Self {
            Self {
                bytes_before_error,
                bytes: Vec::new(),
                flush_fails,
            }
        }
    }

    impl Write for FailingWriter {
        fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
            if self.bytes_before_error == 0 && !buffer.is_empty() {
                return Err(io::Error::new(
                    io::ErrorKind::BrokenPipe,
                    "injected write failure",
                ));
            }
            let count = buffer.len().min(self.bytes_before_error);
            self.bytes.extend_from_slice(&buffer[..count]);
            self.bytes_before_error -= count;
            Ok(count)
        }

        fn flush(&mut self) -> io::Result<()> {
            if self.flush_fails {
                Err(io::Error::new(
                    io::ErrorKind::BrokenPipe,
                    "injected flush failure",
                ))
            } else {
                Ok(())
            }
        }
    }

    fn run_case(
        arguments: &[&str],
        input: &[u8],
        file_opener: &mut dyn FileOpener,
    ) -> (u8, Vec<u8>, Vec<u8>) {
        run_os_case(
            arguments.iter().map(OsString::from).collect(),
            input,
            file_opener,
        )
    }

    fn run_os_case(
        arguments: Vec<OsString>,
        input: &[u8],
        file_opener: &mut dyn FileOpener,
    ) -> (u8, Vec<u8>, Vec<u8>) {
        let file_invocation = Invocation {
            argv: arguments,
            locale_mode: LocaleMode::Utf8,
            posixly_correct: false,
        };
        let mut stdin = Cursor::new(input.to_vec());
        let mut stdout = Vec::new();
        let mut stderr = Vec::new();
        let status = run(
            file_invocation,
            &mut stdin,
            &mut stdout,
            &mut stderr,
            file_opener,
        );
        (status, stdout, stderr)
    }

    fn assert_case(arguments: &[&str], input: &[u8], expected: &[u8]) {
        let mut opener = MockFileOpener::default();
        let (status, stdout, stderr) = run_case(arguments, input, &mut opener);
        assert_eq!(status, 0);
        assert_eq!(stdout, expected);
        assert!(stderr.is_empty());
    }

    mod m1_invocation_and_boundaries {
        use super::*;
        use std::os::unix::ffi::OsStringExt;

        fn invocation(arguments: &[&str], posixly_correct: bool) -> Invocation {
            Invocation {
                argv: arguments.iter().map(OsString::from).collect(),
                locale_mode: LocaleMode::Utf8,
                posixly_correct,
            }
        }

        fn parse(arguments: &[&str]) -> ParsedInvocation {
            parse_invocation(&invocation(arguments, false)).expect("valid invocation")
        }

        fn assert_fatal(arguments: &[&str], expected: &'static [u8]) {
            match parse_invocation(&invocation(arguments, false)) {
                Err(InvocationError::Fatal(error)) => assert_eq!(error.message, expected),
                result => panic!("expected fatal error, got {result:?}"),
            }
        }

        fn expected_usage(program_name: &[u8]) -> Vec<u8> {
            let mut expected = b"usage: ".to_vec();
            expected.extend_from_slice(program_name);
            expected.extend_from_slice(
                b" [-cmnps] [-d chars] [-l number] [-t number]\n\
\t[goal [maximum] | -width | -w width] [file ...]\n",
            );
            expected
        }

        fn run_raw(arguments: Vec<OsString>) -> (u8, Vec<u8>, Vec<u8>) {
            let invocation = Invocation {
                argv: arguments,
                locale_mode: LocaleMode::Utf8,
                posixly_correct: false,
            };
            let mut stdin = Cursor::new(b"unused input\n".to_vec());
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let mut opener = MockFileOpener::default();
            let status = run(
                invocation,
                &mut stdin,
                &mut stdout,
                &mut stderr,
                &mut opener,
            );
            (status, stdout, stderr)
        }

        #[test]
        fn get_positive_accepts_base_zero_and_clamps_overflow() {
            let cases: &[(&[u8], usize)] = &[
                (b"42", 42),
                (b"+42", 42),
                (b" \t\n42", 42),
                (b"010", 8),
                (b"0x10", 16),
                (b"0Xf", 15),
                (b"0b10", 2),
                (b"0B11", 3),
                (b"9223372036854775807", i64::MAX as usize),
                (
                    b"999999999999999999999999999999999999999999999",
                    i64::MAX as usize,
                ),
            ];

            for &(input, expected) in cases {
                assert_eq!(
                    get_positive(input, b"bad width", true),
                    Ok(PositiveParse::Value(expected)),
                    "input {input:?}"
                );
            }
        }

        #[test]
        fn get_positive_distinguishes_suffixes_from_bad_numbers() {
            for input in [b"12x".as_slice(), b"08", b"0x", b"0b", b"-1x", b" "] {
                assert_eq!(
                    get_positive(input, b"bad width", false),
                    Ok(PositiveParse::NotNumber),
                    "input {input:?}"
                );
                assert_eq!(
                    get_positive(input, b"bad width", true),
                    Err(FatalError {
                        message: b"bad width"
                    }),
                    "input {input:?}"
                );
            }

            for input in [b"".as_slice(), b"0", b"-1", b"-0", b"+0"] {
                assert_eq!(
                    get_positive(input, b"bad width", false),
                    Err(FatalError {
                        message: b"bad width"
                    }),
                    "input {input:?}"
                );
            }
        }

        #[test]
        fn parse_defaults_and_every_short_option() {
            let defaults = parse(&["fmt"]);
            assert_eq!(defaults.program_name, b"fmt");
            assert_eq!(defaults.config.goal_length, 65);
            assert_eq!(defaults.config.max_length, 75);
            assert_eq!(defaults.config.tab_width, 8);
            assert_eq!(defaults.config.output_tab_width, 0);
            assert_eq!(defaults.config.sentence_enders, b".?!");
            assert!(!defaults.config.center_p);
            assert!(!defaults.config.coalesce_spaces_p);
            assert!(!defaults.config.allow_indented_paragraphs);
            assert!(!defaults.config.grok_mail_headers);
            assert!(!defaults.config.format_troff);
            assert!(defaults.files.is_empty());

            let parsed = parse(&["fmt", "-cmnps", "-d.!;", "-l4", "-t", "3", "-w22", "file"]);
            assert!(parsed.config.center_p);
            assert!(parsed.config.grok_mail_headers);
            assert!(parsed.config.format_troff);
            assert!(parsed.config.allow_indented_paragraphs);
            assert!(parsed.config.coalesce_spaces_p);
            assert_eq!(parsed.config.sentence_enders, b".!;");
            assert_eq!(parsed.config.output_tab_width, 4);
            assert_eq!(parsed.config.tab_width, 3);
            assert_eq!(parsed.config.goal_length, 22);
            assert_eq!(parsed.config.max_length, 22);
            assert_eq!(parsed.files, [OsString::from("file")]);
        }

        #[test]
        fn parse_required_arguments_can_be_attached_or_separate() {
            let attached = parse(&["fmt", "-d.!?", "-l2", "-t4", "-w30"]);
            assert_eq!(attached.config.sentence_enders, b".!?");
            assert_eq!(attached.config.output_tab_width, 2);
            assert_eq!(attached.config.tab_width, 4);
            assert_eq!(attached.config.goal_length, 30);
            assert_eq!(attached.config.max_length, 30);

            let separate = parse(&["fmt", "-d", "", "-l", "6", "-t", "7", "-w", "31"]);
            assert!(separate.config.sentence_enders.is_empty());
            assert_eq!(separate.config.output_tab_width, 6);
            assert_eq!(separate.config.tab_width, 7);
            assert_eq!(separate.config.goal_length, 31);
            assert_eq!(separate.config.max_length, 31);

            let consumed_option = parse(&["fmt", "-d", "-c"]);
            assert_eq!(consumed_option.config.sentence_enders, b"-c");
            assert!(!consumed_option.config.center_p);
        }

        #[test]
        fn parse_legacy_numeric_width_preserves_getopt_quirks() {
            let decimal = parse(&["fmt", "-72"]);
            assert_eq!(decimal.config.goal_length, 72);
            assert_eq!(decimal.config.max_length, 72);

            let octal = parse(&["fmt", "-012"]);
            assert_eq!(octal.config.goal_length, 10);
            assert_eq!(octal.config.max_length, 10);

            let bundled_tail = parse(&["fmt", "-c1", "x23"]);
            assert!(bundled_tail.config.center_p);
            assert_eq!(bundled_tail.config.goal_length, 23);
            assert_eq!(bundled_tail.config.max_length, 23);
            assert_eq!(bundled_tail.files, [OsString::from("x23")]);

            let following_option = parse(&["fmt", "-c1", "-23"]);
            assert!(following_option.config.center_p);
            assert_eq!(following_option.config.goal_length, 23);
            assert!(following_option.files.is_empty());

            let already_set = parse(&["fmt", "-w5", "-c1"]);
            assert!(already_set.config.center_p);
            assert_eq!(already_set.config.goal_length, 5);

            for arguments in [
                &["fmt", "-08"][..],
                &["fmt", "-1x"][..],
                &["fmt", "-c12"][..],
                &["fmt", "-12c"][..],
                &["fmt", "-c1"][..],
            ] {
                assert_fatal(arguments, b"width must be nonzero");
            }

            match parse_invocation(&invocation(&["fmt", "-0x10"], false)) {
                Err(InvocationError::Usage {
                    diagnostic: Some(diagnostic),
                }) => assert_eq!(diagnostic, b"fmt: invalid option -- 'x'\n"),
                result => panic!("expected invalid-option usage, got {result:?}"),
            }
        }

        #[test]
        fn parse_base_zero_positionals_and_width_ordering() {
            let parsed = parse(&["fmt", "010", "0x10", "file"]);
            assert_eq!(parsed.config.goal_length, 8);
            assert_eq!(parsed.config.max_length, 16);
            assert_eq!(parsed.files, [OsString::from("file")]);

            let binary = parse(&["fmt", "0b10", "0B11"]);
            assert_eq!(binary.config.goal_length, 2);
            assert_eq!(binary.config.max_length, 3);

            let signed = parse(&["fmt", "+7"]);
            assert_eq!(signed.config.goal_length, 7);
            assert_eq!(signed.config.max_length, 17);

            let malformed = parse(&["fmt", "08", "7"]);
            assert_eq!(malformed.config.goal_length, 65);
            assert_eq!(malformed.config.max_length, 75);
            assert_eq!(malformed.files, [OsString::from("08"), OsString::from("7")]);

            let malformed_maximum = parse(&["fmt", "10", "20x", "file"]);
            assert_eq!(malformed_maximum.config.goal_length, 10);
            assert_eq!(malformed_maximum.config.max_length, 20);
            assert_eq!(
                malformed_maximum.files,
                [OsString::from("20x"), OsString::from("file")]
            );

            assert_fatal(&["fmt", ""], b"goal length must be positive");
            assert_fatal(&["fmt", "0"], b"goal length must be positive");
            assert_fatal(&["fmt", "--", "-1"], b"goal length must be positive");
            assert_fatal(&["fmt", "10", "0"], b"max length must be positive");
            assert_fatal(&["fmt", "20", "10"], b"max length must be >= goal length");
            assert_fatal(&["fmt", "-l0"], b"output tab width must be positive");
            assert_fatal(&["fmt", "-t-1"], b"tab width must be positive");
            assert_fatal(&["fmt", "-wbad"], b"width must be positive");
            assert_fatal(&["fmt", "-0"], b"width must be nonzero");
        }

        #[test]
        fn parse_double_dash_lone_dash_and_option_ordering() {
            let terminated = parse(&["fmt", "10", "--", "20", "file"]);
            assert_eq!(terminated.config.goal_length, 10);
            assert_eq!(terminated.config.max_length, 20);
            assert_eq!(terminated.files, [OsString::from("file")]);

            let lone_dash = parse(&["fmt", "-", "10"]);
            assert_eq!(lone_dash.config.goal_length, 65);
            assert_eq!(lone_dash.files, [OsString::from("-"), OsString::from("10")]);

            let permuted = parse(&["fmt", "10", "-c", "20", "file"]);
            assert!(permuted.config.center_p);
            assert_eq!(permuted.config.goal_length, 10);
            assert_eq!(permuted.config.max_length, 20);
            assert_eq!(permuted.files, [OsString::from("file")]);

            let option_argument = parse(&["fmt", "first", "-w", "30", "second"]);
            assert_eq!(option_argument.config.goal_length, 30);
            assert_eq!(
                option_argument.files,
                [OsString::from("first"), OsString::from("second")]
            );

            let posix = parse_invocation(&invocation(&["fmt", "10", "-c", "20", "file"], true))
                .expect("valid POSIX invocation");
            assert!(!posix.config.center_p);
            assert_eq!(posix.config.goal_length, 10);
            assert_eq!(posix.config.max_length, 20);
            assert_eq!(
                posix.files,
                [
                    OsString::from("-c"),
                    OsString::from("20"),
                    OsString::from("file")
                ]
            );
        }

        #[test]
        fn diagnostics_use_getopt_argv0_and_usage_basename() {
            let (status, stdout, stderr) = run_raw(vec![
                OsString::from("/tmp/tools/myfmt"),
                OsString::from("-z"),
            ]);
            assert_eq!(status, 1);
            assert!(stdout.is_empty());
            let mut expected = b"/tmp/tools/myfmt: invalid option -- 'z'\n".to_vec();
            expected.extend_from_slice(&expected_usage(b"myfmt"));
            assert_eq!(stderr, expected);

            for option in b"dltw" {
                let (status, stdout, stderr) = run_raw(vec![
                    OsString::from("/tmp/tools/myfmt"),
                    OsString::from_vec(vec![b'-', *option]),
                ]);
                assert_eq!(status, 1);
                assert!(stdout.is_empty());
                let mut expected = b"/tmp/tools/myfmt: option requires an argument -- '".to_vec();
                expected.push(*option);
                expected.extend_from_slice(b"'\n");
                expected.extend_from_slice(&expected_usage(b"myfmt"));
                assert_eq!(stderr, expected);
            }

            let (status, stdout, stderr) = run_raw(vec![
                OsString::from("/tmp/tools/myfmt"),
                OsString::from("-w0"),
            ]);
            assert_eq!(status, 1);
            assert!(stdout.is_empty());
            assert_eq!(stderr, b"myfmt: width must be positive\n");
        }

        #[test]
        fn diagnostics_preserve_empty_and_non_utf8_program_names() {
            let (status, stdout, stderr) = run_raw(vec![OsString::new(), OsString::from("-h")]);
            assert_eq!(status, 1);
            assert!(stdout.is_empty());
            assert_eq!(stderr, expected_usage(b""));

            let raw_name = OsString::from_vec(b"/tmp/\xff".to_vec());
            let (status, stdout, stderr) = run_raw(vec![raw_name.clone(), OsString::from("-h")]);
            assert_eq!(status, 1);
            assert!(stdout.is_empty());
            assert_eq!(stderr, expected_usage(b"\xff"));

            let (status, stdout, stderr) = run_raw(vec![raw_name, OsString::from("-z")]);
            assert_eq!(status, 1);
            assert!(stdout.is_empty());
            let mut expected = b"/tmp/\xff: invalid option -- 'z'\n".to_vec();
            expected.extend_from_slice(&expected_usage(b"\xff"));
            assert_eq!(stderr, expected);
        }

        #[test]
        fn program_name_uses_the_final_raw_path_component() {
            assert_eq!(process_program_name(None), b"");
            assert_eq!(process_program_name(Some(OsStr::new(""))), b"");
            assert_eq!(process_program_name(Some(OsStr::new("fmt"))), b"fmt");
            assert_eq!(
                process_program_name(Some(OsStr::new("/usr/local/bin/alias"))),
                b"alias"
            );
            assert_eq!(process_program_name(Some(OsStr::new("/trailing/"))), b"");
            let raw = OsString::from_vec(b"/tmp/\xfe\xff".to_vec());
            assert_eq!(process_program_name(Some(raw.as_os_str())), b"\xfe\xff");
        }

        #[test]
        fn locale_mode_only_accepts_the_available_c_utf8_aliases() {
            for locale in [
                b"C.UTF-8".as_slice(),
                b"C.utf8",
                b"C.Utf-8@modifier",
                b"C.UTF8 ",
            ] {
                assert!(is_available_utf8_locale(locale), "{locale:?}");
            }
            for locale in [
                b"C".as_slice(),
                b"POSIX",
                b"en_US.UTF-8",
                b"bogus.UTF-8",
                b"c.utf8",
                b"C.UTF_8",
                b"C.UTF-16",
                b"C.UTF-8/path",
            ] {
                assert!(!is_available_utf8_locale(locale), "{locale:?}");
            }
        }

        #[test]
        fn boundaries_latch_stdout_errors_and_ignore_flush_failures() {
            let mut failing = FailingWriter::new(2, true);
            {
                let mut writer = CompatibilityWriter::new(&mut failing);
                writer.write_all(b"abcdef");
                writer.write_all(b"ignored");
                writer.flush();
                assert!(writer.failed);
            }
            assert_eq!(failing.bytes, b"ab");

            let mut flush_failing = FailingWriter::new(10, true);
            {
                let mut writer = CompatibilityWriter::new(&mut flush_failing);
                writer.flush();
                writer.write_all(b"ignored");
                assert!(writer.failed);
            }
            assert!(flush_failing.bytes.is_empty());

            let mut stdin = Cursor::new(b"output\n".to_vec());
            let mut stdout = FailingWriter::new(0, true);
            let mut stderr = Vec::new();
            let mut opener = MockFileOpener::default();
            let status = run(
                invocation(&["fmt"], false),
                &mut stdin,
                &mut stdout,
                &mut stderr,
                &mut opener,
            );
            assert_eq!(status, 0);
            assert!(stderr.is_empty());
        }

        #[test]
        fn boundaries_saturate_error_status_at_127() {
            let mut state = RunState::default();
            state.record_error();
            assert_eq!(state.n_errors, 1);

            state.n_errors = 126;
            state.record_error();
            assert_eq!(state.n_errors, 127);
            state.record_error();
            assert_eq!(state.n_errors, 127);

            state.n_errors = 127;
            state.record_error();
            assert_eq!(state.n_errors, 127);
        }

        #[test]
        fn boundaries_select_stdin_or_open_files_in_argument_order() {
            #[derive(Default)]
            struct RecordingOpener {
                opened: Vec<OsString>,
            }

            impl FileOpener for RecordingOpener {
                fn open(&mut self, path: &OsStr) -> io::Result<Box<dyn Read>> {
                    self.opened.push(path.to_os_string());
                    Ok(Box::new(Cursor::new(Vec::<u8>::new())))
                }
            }

            let raw_path = OsString::from_vec(b"raw-\xff".to_vec());
            let file_invocation = Invocation {
                argv: vec![
                    OsString::from("fmt"),
                    OsString::from("second"),
                    raw_path.clone(),
                    OsString::from("-"),
                ],
                locale_mode: LocaleMode::Utf8,
                posixly_correct: false,
            };
            let mut stdin = Cursor::new(b"stdin must be ignored\n".to_vec());
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let mut opener = RecordingOpener::default();
            let status = run(
                file_invocation,
                &mut stdin,
                &mut stdout,
                &mut stderr,
                &mut opener,
            );
            assert_eq!(status, 0);
            assert!(stdout.is_empty());
            assert!(stderr.is_empty());
            assert_eq!(
                opener.opened,
                [OsString::from("second"), raw_path, OsString::from("-")]
            );

            let mut stdin = Cursor::new(b"stdin is selected\n".to_vec());
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let mut opener = RecordingOpener::default();
            let status = run(
                invocation(&["fmt"], false),
                &mut stdin,
                &mut stdout,
                &mut stderr,
                &mut opener,
            );
            assert_eq!(status, 0);
            assert_eq!(stdout, b"stdin is selected\n");
            assert!(stderr.is_empty());
            assert!(opener.opened.is_empty());
        }
    }

    mod m2_byte_lines_and_core_formatter {
        use super::*;

        fn formatter_config() -> Config {
            Config {
                goal_length: 65,
                max_length: 75,
                ..Config::default()
            }
        }

        fn read_all_lines(input: &[u8], config: &Config, locale_mode: LocaleMode) -> Vec<Vec<u8>> {
            let mut stream = Cursor::new(input.to_vec());
            let mut reader = LineReader::new(&mut stream);
            let mut lines = Vec::new();
            loop {
                match get_line(&mut reader, config, locale_mode).expect("line read") {
                    LineEvent::Line(line) => lines.push(line),
                    LineEvent::End => return lines,
                    LineEvent::ReadError(error) => panic!("unexpected read error: {error}"),
                }
            }
        }

        fn indent_bytes(output_tab_width: usize, spaces: usize) -> Vec<u8> {
            let config = Config {
                output_tab_width,
                ..Config::default()
            };
            let mut bytes = Vec::new();
            {
                let mut writer = CompatibilityWriter::new(&mut bytes);
                output_indent(&config, spaces, &mut writer);
            }
            bytes
        }

        mod characters {
            use super::*;

            #[test]
            fn decodes_ascii_utf8_combining_and_double_width_units() {
                assert_eq!(
                    decode_display_unit(b"", LocaleMode::Utf8),
                    DisplayUnit {
                        byte_len: 0,
                        width: 0,
                        character: None,
                        valid: false,
                    }
                );
                assert_eq!(
                    decode_display_unit(b"A", LocaleMode::Utf8),
                    DisplayUnit {
                        byte_len: 1,
                        width: 1,
                        character: Some('A'),
                        valid: true,
                    }
                );
                assert_eq!(
                    decode_display_unit("\u{00e9}".as_bytes(), LocaleMode::Utf8),
                    DisplayUnit {
                        byte_len: 2,
                        width: 1,
                        character: Some('\u{00e9}'),
                        valid: true,
                    }
                );
                assert_eq!(
                    decode_display_unit("\u{0301}".as_bytes(), LocaleMode::Utf8),
                    DisplayUnit {
                        byte_len: 2,
                        width: 0,
                        character: Some('\u{0301}'),
                        valid: true,
                    }
                );
                assert_eq!(
                    decode_display_unit("\u{754c}".as_bytes(), LocaleMode::Utf8),
                    DisplayUnit {
                        byte_len: 3,
                        width: 2,
                        character: Some('\u{754c}'),
                        valid: true,
                    }
                );
                assert_eq!(
                    decode_display_unit(b"\x07", LocaleMode::Utf8),
                    DisplayUnit {
                        byte_len: 1,
                        width: 1,
                        character: Some('\x07'),
                        valid: true,
                    }
                );
            }

            #[test]
            fn invalid_and_incomplete_utf8_consumes_one_byte() {
                for input in [
                    b"\x80".as_slice(),
                    b"\xc0".as_slice(),
                    b"\xf5".as_slice(),
                    b"\xff".as_slice(),
                    b"\xc3".as_slice(),
                    b"\xe2\x82".as_slice(),
                    b"\xf0\x9f\x92".as_slice(),
                    b"\xe2(\xa1".as_slice(),
                ] {
                    assert_eq!(
                        decode_display_unit(input, LocaleMode::Utf8),
                        DisplayUnit {
                            byte_len: 1,
                            width: 1,
                            character: None,
                            valid: false,
                        },
                        "input {input:?}"
                    );
                }

                assert_eq!(
                    decode_display_unit("\u{00e9}".as_bytes(), LocaleMode::C),
                    DisplayUnit {
                        byte_len: 1,
                        width: 1,
                        character: None,
                        valid: false,
                    }
                );
                assert_eq!(
                    decode_display_unit(b"A", LocaleMode::C),
                    DisplayUnit {
                        byte_len: 1,
                        width: 1,
                        character: Some('A'),
                        valid: true,
                    }
                );
            }

            #[test]
            fn utf8_mode_accepts_the_extended_sequences_used_by_mbtowc() {
                for input in [
                    b"\xf4\x90\x80\x80".as_slice(),
                    b"\xf7\xbf\xbf\xbf",
                    b"\xf8\x88\x80\x80\x80",
                    b"\xfb\xbf\xbf\xbf\xbf",
                    b"\xfc\x84\x80\x80\x80\x80",
                    b"\xfd\xbf\xbf\xbf\xbf\xbf",
                ] {
                    let unit = decode_display_unit(input, LocaleMode::Utf8);
                    assert_eq!(unit.byte_len, input.len());
                    assert_eq!(unit.width, 1);
                    assert_eq!(unit.character, None);
                    assert!(unit.valid);
                }

                for input in [
                    b"\xf0\x8f\xbf\xbf".as_slice(),
                    b"\xf8\x87\xbf\xbf\xbf",
                    b"\xfc\x83\xbf\xbf\xbf\xbf",
                    b"\xed\xa0\x80",
                ] {
                    assert_eq!(
                        decode_display_unit(input, LocaleMode::Utf8),
                        invalid_display_unit()
                    );
                }
            }

            #[test]
            fn display_width_tracks_the_reference_unicode_15_1_tables() {
                for character in [
                    '\u{00ad}',
                    '\u{17a4}',
                    '\u{17d8}',
                    '\u{fa6e}',
                    '\u{323b0}',
                    '\u{e0000}',
                ] {
                    assert_eq!(display_width(character), 1, "{character:?}");
                }
                for character in ['\u{2d7f}', '\u{fff9}', '\u{13430}'] {
                    assert_eq!(display_width(character), 0, "{character:?}");
                }
                for character in ['\u{302e}', '\u{3164}', '\u{3248}', '\u{4dc0}'] {
                    assert_eq!(display_width(character), 2, "{character:?}");
                }
            }

            #[test]
            fn wide_and_narrow_character_classes_stay_distinct() {
                for character in [
                    '\t', ' ', '\u{1680}', '\u{2000}', '\u{2006}', '\u{2008}', '\u{200a}',
                    '\u{205f}', '\u{3000}',
                ] {
                    assert!(is_wide_blank(character), "{character:?}");
                }
                for character in ['\n', '\u{00a0}', '\u{2007}', '\u{202f}'] {
                    assert!(!is_wide_blank(character), "{character:?}");
                }

                for character in [
                    '\t', '\n', '\r', ' ', '\u{1680}', '\u{2028}', '\u{2029}', '\u{3000}',
                ] {
                    assert!(is_wide_space(character), "{character:?}");
                }
                for character in ['A', '\u{0085}', '\u{00a0}', '\u{2007}', '\u{202f}'] {
                    assert!(!is_wide_space(character), "{character:?}");
                }

                assert!(is_narrow_control(0, LocaleMode::Utf8));
                assert!(is_narrow_control(0x1f, LocaleMode::C));
                assert!(is_narrow_control(0x7f, LocaleMode::Utf8));
                assert!(!is_narrow_control(b' ', LocaleMode::Utf8));
                assert!(!is_narrow_control(0x80, LocaleMode::C));

                for byte in [b' ', b'\t', b'\n', 0x0b, 0x0c, b'\r'] {
                    assert!(is_narrow_space(byte, LocaleMode::Utf8));
                }
                assert!(!is_narrow_space(0x85, LocaleMode::Utf8));
            }

            #[test]
            fn wide_blanks_split_words_but_nonbreaking_spaces_do_not() {
                assert_case(&["fmt"], b"left\xe2\x80\x83right\n", b"left right\n");
                assert_case(&["fmt"], b"left\xc2\xa0right\n", b"left\xc2\xa0right\n");
                assert_case(
                    &["fmt"],
                    b"left\xe2\x80\x87right\xe2\x80\xafagain\n",
                    b"left\xe2\x80\x87right\xe2\x80\xafagain\n",
                );
            }
        }

        mod lines {
            use super::*;

            #[test]
            fn lf_and_unterminated_eof() {
                let config = formatter_config();
                assert_eq!(
                    read_all_lines(b"alpha\nbeta", &config, LocaleMode::Utf8),
                    [b"alpha".to_vec(), b"beta".to_vec()]
                );
                assert_case(&["fmt"], b"alpha\n", b"alpha\n");
                assert_case(&["fmt"], b"alpha", b"alpha\n");
            }

            #[test]
            fn empty_and_repeated_blank_lines() {
                let config = formatter_config();
                assert!(read_all_lines(b"", &config, LocaleMode::Utf8).is_empty());
                assert_eq!(
                    read_all_lines(b"\n\n", &config, LocaleMode::Utf8),
                    [Vec::<u8>::new(), Vec::<u8>::new()]
                );
                assert_case(&["fmt"], b"", b"");
                assert_case(&["fmt"], b"\n\n", b"\n\n");
                assert_case(&["fmt"], b"   ", b"");
            }

            #[test]
            fn bytewise_backspaces_and_cr() {
                let config = formatter_config();
                let input = b"ab\x08c\r\n\x08a\x08\x08b\n\xc3\xa9\x08\nA\x01\tB\x7f\r\n";
                assert_eq!(
                    read_all_lines(input, &config, LocaleMode::Utf8),
                    [
                        b"ac".to_vec(),
                        b"b".to_vec(),
                        b"\xc3".to_vec(),
                        b"A\tB".to_vec(),
                    ]
                );
            }

            #[test]
            fn dot_lines_retain_controls_at_the_first_retained_position() {
                let config = formatter_config();
                assert_eq!(
                    read_all_lines(b"\x01.\x02\x08X \t\r\n", &config, LocaleMode::Utf8),
                    [b".\x02\x08X".to_vec()]
                );

                let format_troff = Config {
                    format_troff: true,
                    ..formatter_config()
                };
                assert_eq!(
                    read_all_lines(b"\x01.\x02\x08X \t\r\n", &format_troff, LocaleMode::Utf8),
                    [b"X".to_vec()]
                );
            }

            #[test]
            fn invalid_utf8_preserved() {
                let config = formatter_config();
                let input = b"\xff\xc3\n";
                assert_eq!(
                    read_all_lines(input, &config, LocaleMode::Utf8),
                    [b"\xff\xc3".to_vec()]
                );
                assert_case(&["fmt"], input, input);

                assert_eq!(
                    read_all_lines("\u{00e9}\n".as_bytes(), &config, LocaleMode::C),
                    ["\u{00e9}".as_bytes().to_vec()]
                );
            }

            #[test]
            fn partial_line_is_yielded_before_a_deferred_read_error() {
                let config = formatter_config();
                let mut stream = PrefixThenErrorReader::new(
                    b"partial".to_vec(),
                    io::Error::new(io::ErrorKind::Other, "injected read failure"),
                );
                let mut reader = LineReader::new(&mut stream);
                match get_line(&mut reader, &config, LocaleMode::Utf8).expect("partial line") {
                    LineEvent::Line(line) => assert_eq!(line, b"partial"),
                    _ => panic!("expected partial line"),
                }
                match get_line(&mut reader, &config, LocaleMode::Utf8).expect("deferred error") {
                    LineEvent::ReadError(error) => {
                        assert_eq!(error.to_string(), "injected read failure");
                    }
                    _ => panic!("expected deferred read error"),
                }

                let mut stream = PrefixThenErrorReader::new(
                    b"partial".to_vec(),
                    io::Error::new(io::ErrorKind::Other, "injected read failure"),
                );
                let mut output = Vec::new();
                let mut stderr = Vec::new();
                let mut state = RunState::default();
                {
                    let mut writer = CompatibilityWriter::new(&mut output);
                    process_stream(
                        &mut stream,
                        InputName::StandardInput,
                        &config,
                        LocaleMode::Utf8,
                        &mut writer,
                        &mut stderr,
                        b"fmt",
                        &mut state,
                    )
                    .expect("stream processing");
                }
                assert_eq!(output, b"partial\n");
                assert_eq!(stderr, b"fmt: standard input: injected read failure\n");
                assert_eq!(state.n_errors, 1);
            }
        }

        mod indentation {
            use super::*;

            #[test]
            fn input_tabs_advance_to_the_next_custom_stop() {
                assert_eq!(indent_length(b"", 8), 0);
                assert_eq!(indent_length(b"   word", 8), 3);
                assert_eq!(indent_length(b"\tword", 8), 8);
                assert_eq!(indent_length(b" \tword", 8), 8);
                assert_eq!(indent_length(b"\t word", 8), 9);
                assert_eq!(indent_length(b"\t\tword", 8), 16);
                assert_eq!(indent_length(b" \t\tword", 4), 8);
                assert_eq!(indent_length(b"\xc2\xa0 word", 8), 0);
                assert_eq!(indent_length(b"\x0b word", 8), 0);
            }

            #[test]
            fn output_indent_uses_greedy_tabs_and_remainder_spaces() {
                assert_eq!(indent_bytes(0, 0), b"");
                assert_eq!(indent_bytes(0, 5), b"     ");
                assert_eq!(indent_bytes(4, 3), b"   ");
                assert_eq!(indent_bytes(4, 4), b"\t");
                assert_eq!(indent_bytes(4, 9), b"\t\t ");
                assert_eq!(indent_bytes(8, 5), b"     ");
                assert_eq!(indent_bytes(8, 8), b"\t");
            }

            #[test]
            fn source_tabs_after_indentation_use_the_physical_column() {
                assert_case(&["fmt", "-t", "4", "-w", "20"], b" a\tb\n", b" a  b\n");
                assert_case(&["fmt", "-t", "4", "-w", "20"], b"  a\tb\n", b"  a b\n");
            }

            #[test]
            fn output_tab_compression() {
                assert_case(
                    &["fmt", "-l", "4", "-w", "20"],
                    b"         hello\n",
                    b"\t\t hello\n",
                );
            }
        }

        mod wrapping {
            use super::*;

            #[test]
            fn wrap_below_on_over_and_tie() {
                assert_case(&["fmt", "10", "20"], b"aaaa bbb\n", b"aaaa bbb\n");
                assert_case(&["fmt", "10", "20"], b"aaaa bbbbb c\n", b"aaaa bbbbb\nc\n");
                assert_case(&["fmt", "10", "20"], b"aaaaaaa bbbb\n", b"aaaaaaa bbbb\n");
                assert_case(&["fmt", "10", "20"], b"aaaaaaaa bbb\n", b"aaaaaaaa bbb\n");
                assert_case(
                    &["fmt", "10", "20"],
                    b"aaaaaaaa bbbb\n",
                    b"aaaaaaaa\nbbbb\n",
                );
            }

            #[test]
            fn maximum_overflow_and_overlong_word() {
                assert_case(&["fmt", "10", "11"], b"aaaaaaaa bbb\n", b"aaaaaaaa\nbbb\n");
                assert_case(&["fmt", "5", "5"], b"abcdefgh ij\n", b"abcdefgh\nij\n");
            }

            #[test]
            fn zero_and_double_width_units() {
                assert_case(&["fmt"], "\u{0301}\n".as_bytes(), "\u{0301}".as_bytes());
                assert_case(&["fmt"], "\u{0301}a\n".as_bytes(), "\u{0301}a\n".as_bytes());
                assert_case(
                    &["fmt", "4", "6"],
                    "\u{754c} \u{754c}\n".as_bytes(),
                    "\u{754c} \u{754c}\n".as_bytes(),
                );
            }

            #[test]
            fn preserved_and_coalesced_spacing() {
                assert_case(&["fmt"], b"a   b\tc\n", b"a   b   c\n");
                assert_case(&["fmt", "-s"], b"a   b\tc\n", b"a b c\n");
                assert_case(&["fmt", "-s"], b"End.   Next\n", b"End.  Next\n");
                assert_case(&["fmt"], b"End.\nNext\n", b"End.  Next\n");
                assert_case(&["fmt"], b"a   \n", b"a\n");
            }
        }

        #[test]
        fn very_long_line() {
            assert_case(
                &["fmt", "-w", "50"],
                b"This is a very long line that should test the dynamic buffer allocation in get_line function and make sure it can handle arbitrarily long input lines without crashing\n",
                b"This is a very long line that should test the\n\
dynamic buffer allocation in get_line function and\n\
make sure it can handle arbitrarily long input\n\
lines without crashing\n",
            );
        }

        #[test]
        fn goal_word_boundary() {
            assert_case(
                &["fmt", "-w", "11"],
                b"Hello world test\n",
                b"Hello world\ntest\n",
            );
        }

        #[test]
        fn tab_expansion_custom() {
            assert_case(
                &["fmt", "-t", "4", "-w", "20"],
                b"a\tb\tc\n",
                b"a   b   c\n",
            );
        }

        #[test]
        fn wide_characters() {
            let greek = b"\xce\xb1\xce\xb2\xce\xb3\xce\xb4\xce\xb5\xce\xb6\xce\xb7\xce\xb8\xce\xb9\xce\xba\xce\xbb\xce\xbc\xce\xbd\xce\xbe\xce\xbf\n";
            assert_case(&["fmt", "-w", "10"], greek, greek);
        }

        #[test]
        fn control_chars_stripped() {
            assert_case(
                &["fmt", "-w", "20"],
                b"Hello\x01\x02world\n",
                b"Helloworld\n",
            );
        }

        #[test]
        fn multiple_tabs() {
            assert_case(
                &["fmt", "-t", "4", "-w", "20"],
                b"\t\tDouble tab\n",
                b"        Double tab\n",
            );
        }
    }

    mod m3_paragraph_and_special_modes {
        use super::*;

        mod headers {
            use super::*;

            #[test]
            fn accepts_each_header_name_class_and_ascii_separator() {
                let accepted: &[&[u8]] = &[
                    b"A: ",
                    b"Z:\tvalue",
                    b"A-Z: value",
                    b"Aa: value",
                    b"A0: value",
                    b"A:\n",
                    b"A:\x0b",
                    b"A:\x0c",
                    b"A:\r",
                ];

                for &line in accepted {
                    assert!(
                        might_be_header(line, LocaleMode::Utf8),
                        "expected header: {line:?}"
                    );
                    assert!(
                        might_be_header(line, LocaleMode::C),
                        "expected C-locale header: {line:?}"
                    );
                }
            }

            #[test]
            fn rejects_bytes_outside_the_conservative_header_pattern() {
                let rejected: &[&[u8]] = &[
                    b"",
                    b": ",
                    b"a: ",
                    b" A: ",
                    b"A",
                    b"A:",
                    b"A:no-space",
                    b"A_: value",
                    b"A.: value",
                    b"A:: value",
                    b"\xff: value",
                    b"A\xff: value",
                ];

                for &line in rejected {
                    assert!(
                        !might_be_header(line, LocaleMode::Utf8),
                        "unexpected header: {line:?}"
                    );
                }
            }

            #[test]
            fn state_predicates_preserve_the_source_enum_comparisons() {
                assert_eq!(HdrType::ParagraphStart as i8, -1);
                assert_eq!(HdrType::NonHeader as i8, 0);
                assert_eq!(HdrType::Header as i8, 1);
                assert_eq!(HdrType::Continuation as i8, 2);

                assert!(HdrType::ParagraphStart.is_nonzero());
                assert!(!HdrType::ParagraphStart.is_positive());
                assert!(!HdrType::NonHeader.is_nonzero());
                assert!(!HdrType::NonHeader.is_positive());
                assert!(HdrType::Header.is_nonzero());
                assert!(HdrType::Header.is_positive());
                assert!(HdrType::Continuation.is_nonzero());
                assert!(HdrType::Continuation.is_positive());
            }
        }

        mod spacing {
            use super::*;

            #[test]
            fn default_empty_and_custom_sentence_enders_apply_at_line_ends() {
                assert_case(
                    &["fmt", "-w", "80"],
                    b"One.\nTwo!\nThree?\nFour:\nFive\n",
                    b"One.  Two!  Three?  Four: Five\n",
                );
                assert_case(
                    &["fmt", "-d", "", "-w", "80"],
                    b"One.\nTwo!\n",
                    b"One. Two!\n",
                );
                assert_case(
                    &["fmt", "-d", ":", "-w", "80"],
                    b"One:\nTwo.\n",
                    b"One:  Two.\n",
                );
            }

            #[test]
            fn coalescing_replaces_internal_but_not_only_line_end_spacing() {
                assert_case(
                    &["fmt", "-w", "80"],
                    b"End.   Next\nTail\n",
                    b"End.   Next Tail\n",
                );
                assert_case(
                    &["fmt", "-s", "-w", "80"],
                    b"End.   Next\nTail\n",
                    b"End.  Next Tail\n",
                );
                assert_case(
                    &["fmt", "-s", "-d", "", "-w", "80"],
                    b"End.   Next\nTail\n",
                    b"End. Next Tail\n",
                );
            }

            #[test]
            fn sentence_ender_membership_uses_the_final_source_byte() {
                assert_case(
                    &["fmt", "-d", "界", "-w", "80"],
                    "界\nnext\n".as_bytes(),
                    "界  next\n".as_bytes(),
                );
                assert_case(
                    &["fmt", "-d", "é", "-w", "80"],
                    "©\nnext\n".as_bytes(),
                    "©  next\n".as_bytes(),
                );
                assert_case(
                    &["fmt", "-w", "80"],
                    "界\nnext\n".as_bytes(),
                    "界 next\n".as_bytes(),
                );
            }
        }

        mod paragraphs {
            use super::*;

            #[test]
            fn equal_indentation_joins_while_upward_and_downward_changes_split() {
                assert_case(
                    &["fmt", "-w", "80"],
                    b"one\none again\n  two\n  three\none final\n",
                    b"one one again\n  two three\none final\n",
                );
            }

            #[test]
            fn indented_paragraph_mode_only_suppresses_the_second_line_break() {
                let input = b"first\n  second\n  third\n";
                assert_case(&["fmt", "-w", "80"], input, b"first\n  second third\n");
                assert_case(
                    &["fmt", "-p", "-w", "80"],
                    input,
                    b"first second\n  third\n",
                );
            }

            #[test]
            fn blank_and_whitespace_only_lines_are_independent_boundaries() {
                assert_case(&["fmt", "-w", "80"], b"a\n\n\nb\n", b"a\n\n\nb\n");
                assert_case(&["fmt", "-w", "80"], b"a\n   \n\tb\n", b"a\n\n        b\n");
            }

            #[test]
            fn first_and_wrapped_lines_use_the_source_selected_indentation() {
                assert_case(
                    &["fmt", "-w", "10"],
                    b"    one two three four five\n",
                    b"    one\n    two\n    three\n    four\n    five\n",
                );
                assert_case(
                    &["fmt", "-p", "-w", "10"],
                    b"    one\n  two three four\n",
                    b"    one\n    two\n    three\n    four\n",
                );
            }

            #[test]
            fn zero_width_words_retain_width_based_paragraph_state() {
                assert_case(
                    &["fmt", "-w", "80"],
                    "\u{0301}\n\nx\n".as_bytes(),
                    "\u{0301}\nx\n".as_bytes(),
                );
                assert_case(
                    &["fmt", "-w", "80"],
                    "\u{0301}\n  x\n".as_bytes(),
                    "\u{0301}  x\n".as_bytes(),
                );
            }
        }

        mod mail {
            use super::*;

            #[test]
            fn header_after_ordinary_text_waits_for_a_blank_reset() {
                assert_case(
                    &["fmt", "-m", "-w", "80"],
                    b"ordinary\nSubject: value\n\nFrom: reset\nordinary after\n",
                    b"ordinary Subject: value\n\nFrom: reset\nordinary after\n",
                );
            }

            #[test]
            fn consecutive_headers_and_continuations_follow_the_mail_states() {
                assert_case(
                    &["fmt", "-m", "-w", "80"],
                    b"Subject: one\n  continued\nFrom: two\n  more\nordinary\n",
                    b"Subject: one continued\nFrom: two more\nordinary\n",
                );
                assert_case(
                    &["fmt", "-m", "-w", "80"],
                    b"ordinary\n  indented\n",
                    b"ordinary\n  indented\n",
                );
            }

            #[test]
            fn header_wrapping_retains_the_literal_last_indent_update_order() {
                assert_case(
                    &["fmt", "-m", "-w", "10"],
                    b"Subject: one two three four\n",
                    b"Subject:\none two\nthree four\n",
                );
                assert_case(
                    &["fmt", "-m", "-w", "14"],
                    b"Subject: one\n  two three four five\n",
                    b"Subject: one\ntwo three four\nfive\n",
                );
            }
        }

        mod troff {
            use super::*;

            #[test]
            fn default_dot_requests_preserve_controls_and_trim_trailing_space() {
                assert_case(
                    &["fmt", "-w", "80"],
                    b".x\x01\t y \t\n.\n",
                    b".x\x01\t y\n.\n",
                );
            }

            #[test]
            fn format_troff_strips_controls_and_formats_the_line() {
                assert_case(&["fmt", "-n", "-w", "5"], b".x\x01\t y \t\n", b".x\ny\n");
            }

            #[test]
            fn dot_requests_are_separate_from_adjacent_formatted_paragraphs() {
                assert_case(
                    &["fmt", "-w", "80"],
                    b"before words\n.request\nafter words\n",
                    b"before words\n.request\nafter words\n",
                );
            }

            #[test]
            fn passthrough_preserves_the_active_mail_state() {
                let input = b"Subject: one\n.request\n  continued after dot\n";
                assert_case(
                    &["fmt", "-m", "-w", "80"],
                    input,
                    b"Subject: one\n.request\ncontinued after dot\n",
                );
                assert_case(
                    &["fmt", "-m", "-n", "-w", "80"],
                    input,
                    b"Subject: one\n.request\n  continued after dot\n",
                );
            }

            #[test]
            fn only_a_dot_at_the_first_retained_position_is_passthrough() {
                assert_case(&["fmt", "-w", "80"], b"\x01.request\n", b".request\n");
                assert_case(
                    &["fmt", "-w", "80"],
                    b"\t.request words\n",
                    b"        .request words\n",
                );
            }
        }

        #[test]
        fn format_troff_enabled() {
            assert_case(
                &["fmt", "-n", "-w", "10"],
                b".TH MANUAL\nRegular text\n",
                b".TH MANUAL\nRegular\ntext\n",
            );
        }

        #[test]
        fn custom_sentence_enders2() {
            assert_case(
                &["fmt", "-d", ".!?", "-w", "20"],
                b"End.  Next!  Another?\n",
                b"End.  Next!\nAnother?\n",
            );
        }

        #[test]
        fn dot_line_start() {
            assert_case(
                &["fmt", "-w", "10"],
                b".Not troff\nRegular text\n",
                b".Not troff\nRegular\ntext\n",
            );
        }

        #[test]
        fn non_header_after_header() {
            assert_case(
                &["fmt", "-m"],
                b"Subject: Test\nNot a header\n\nBody\n",
                b"Subject: Test\nNot a header\n\nBody\n",
            );
        }

        #[test]
        fn mail_header_continuation() {
            assert_case(
                &["fmt", "-m"],
                b"Subject:\n  This is a long subject\n  that continues\n\nBody text\n",
                b"Subject:\n  This is a long subject that continues\n\nBody text\n",
            );
        }
    }

    mod m4_center_mode {
        use super::*;

        #[test]
        fn center_even_deficit() {
            assert_case(&["fmt", "-c", "-w", "9"], b"abc\nab\n", b"   abc\n    ab\n");
        }

        #[test]
        fn center_line_wider_than_goal() {
            assert_case(
                &["fmt", "-c", "-w", "5"],
                b"12345\n123456\n",
                b"12345\n123456\n",
            );
        }

        #[test]
        fn center_blank_and_whitespace_only() {
            assert_case(&["fmt", "-c", "-w", "5"], b"", b"");
            assert_case(
                &["fmt", "-c", "-w", "5"],
                b"\n \t  \n\xe2\x80\x83\xe3\x80\x80\n",
                b"   \n   \n   \n",
            );
        }

        #[test]
        fn center_leading_unicode_space() {
            assert_case(
                &["fmt", "-c", "-w", "10"],
                b" \t\xe2\x80\x83A  \n",
                b"     A\n",
            );
            assert_case(
                &["fmt", "-c", "-w", "10"],
                b"\xe2\x80\x83A\xe2\x80\x83 \t\n",
                b"    A\xe2\x80\x83\n",
            );
        }

        #[test]
        fn center_combining_and_wide() {
            assert_case(
                &["fmt", "-c", "-w", "10"],
                "e\u{0301}\u{754c}\n".as_bytes(),
                "    e\u{0301}\u{754c}\n".as_bytes(),
            );
            assert_case(
                &["fmt", "-c", "-w", "5"],
                "\u{0301}\n".as_bytes(),
                "   \u{0301}\n".as_bytes(),
            );
        }

        #[test]
        fn center_unterminated_final_line() {
            assert_case(&["fmt", "-c", "-w", "6"], b"ab\nxyz", b"  ab\n  xyz\n");
            assert_case(&["fmt", "-c", "-w", "6"], b"   ", b"");
        }

        #[test]
        fn center_replaces_each_invalid_byte() {
            assert_case(&["fmt", "-c", "-w", "9"], b"\xffA\xe2(\xa1\n", b"  ?A?(?\n");
        }

        #[test]
        fn center_reuses_the_previous_character_after_decode_failure() {
            assert_case(&["fmt", "-c", "-w", "5"], b" \xffA\n", b"  A\n");
            assert_case(
                &["fmt", "-c", "-w", "5"],
                b"\xcc\x81\xffA\n",
                b"  \xcc\x81?A\n",
            );
            assert_case(
                &["fmt", "-c", "-w", "5"],
                b"A \xff\n\xfeB\n",
                b" A ?\n  B\n",
            );
        }

        #[test]
        fn center_partial_line_precedes_deferred_read_error() {
            struct ErrorOpener;

            impl FileOpener for ErrorOpener {
                fn open(&mut self, _path: &OsStr) -> io::Result<Box<dyn Read>> {
                    Ok(Box::new(PrefixThenErrorReader::new(
                        b"ab".to_vec(),
                        io::Error::new(io::ErrorKind::Other, "read failed"),
                    )))
                }
            }

            let mut opener = ErrorOpener;
            let (status, stdout, stderr) =
                run_case(&["fmt", "-c", "-w", "6", "input"], b"", &mut opener);
            assert_eq!(status, 1);
            assert_eq!(stdout, b"  ab\n");
            assert_eq!(stderr, b"fmt: input: read failed\n");
        }

        #[test]
        fn center_odd_width() {
            assert_case(&["fmt", "-c", "-w", "21"], b"Hello\n", b"        Hello\n");
        }

        #[test]
        fn center_invalid_utf8() {
            assert_case(
                &["fmt", "-w", "20", "-c"],
                b"z\xc3\x9f\xe6\n",
                b"         z\xc3\x9f?\n",
            );
        }

        #[test]
        fn center_custom_tab() {
            assert_case(
                &["fmt", "-c", "-t", "4", "-w", "20"],
                b"Hello\tWorld\n",
                b"     Hello World\n",
            );
        }
    }

    mod m5_filesystem_and_conformance {
        use super::*;
        use std::os::unix::ffi::OsStringExt;

        #[test]
        fn file_processing() {
            let path = OsString::from("test_input.txt");
            let mut opener = MockFileOpener::default()
                .with_bytes(path, b"This is a test file\nwith multiple lines\n".to_vec());
            let (status, stdout, stderr) =
                run_case(&["fmt", "-w", "10", "test_input.txt"], b"", &mut opener);
            assert_eq!(status, 0);
            assert_eq!(stdout, b"This is a\ntest file\nwith\nmultiple\nlines\n");
            assert!(stderr.is_empty());
        }

        mod ordering {
            use super::*;

            #[test]
            fn stdin_is_used_only_when_no_files_are_selected() {
                let mut opener = MockFileOpener::default();
                let (status, stdout, stderr) =
                    run_case(&["fmt"], b"standard input words\n", &mut opener);
                assert_eq!(status, 0);
                assert_eq!(stdout, b"standard input words\n");
                assert!(stderr.is_empty());
                assert!(opener.opened.is_empty());

                let mut opener = MockFileOpener::default()
                    .with_bytes(OsString::from("named"), b"named input\n".to_vec());
                let (status, stdout, stderr) =
                    run_case(&["fmt", "named"], b"ignored stdin\n", &mut opener);
                assert_eq!(status, 0);
                assert_eq!(stdout, b"named input\n");
                assert!(stderr.is_empty());
                assert_eq!(opener.opened, [OsString::from("named")]);
            }

            #[test]
            fn one_multiple_and_empty_files_finalize_independently() {
                let mut opener = MockFileOpener::default()
                    .with_bytes(OsString::from("first"), b"alpha".to_vec())
                    .with_bytes(OsString::from("empty"), Vec::new())
                    .with_bytes(OsString::from("second"), b"beta\ngamma\n".to_vec());
                let (status, stdout, stderr) = run_case(
                    &["fmt", "-w", "80", "first", "empty", "second"],
                    b"ignored\n",
                    &mut opener,
                );
                assert_eq!(status, 0);
                assert_eq!(stdout, b"alpha\nbeta gamma\n");
                assert!(stderr.is_empty());
                assert_eq!(
                    opener.opened,
                    [
                        OsString::from("first"),
                        OsString::from("empty"),
                        OsString::from("second")
                    ]
                );
            }

            #[test]
            fn literal_dash_and_raw_byte_filenames_are_opened_as_paths() {
                let raw_path = OsString::from_vec(b"raw-\xff".to_vec());
                let mut opener = MockFileOpener::default()
                    .with_bytes(OsString::from("-"), b"dash file".to_vec())
                    .with_bytes(raw_path.clone(), b"raw file".to_vec());
                let arguments = vec![
                    OsString::from("fmt"),
                    OsString::from("-w"),
                    OsString::from("80"),
                    OsString::from("-"),
                    raw_path.clone(),
                ];
                let (status, stdout, stderr) =
                    run_os_case(arguments, b"ignored stdin\n", &mut opener);
                assert_eq!(status, 0);
                assert_eq!(stdout, b"dash file\nraw file\n");
                assert!(stderr.is_empty());
                assert_eq!(opener.opened, [OsString::from("-"), raw_path]);
            }
        }

        mod open {
            use super::*;

            #[test]
            fn failures_before_between_and_after_successes_do_not_stop_processing() {
                let mut opener = MockFileOpener::default()
                    .with_error(
                        OsString::from("before"),
                        io::ErrorKind::PermissionDenied,
                        "before denied",
                    )
                    .with_bytes(OsString::from("first"), b"alpha".to_vec())
                    .with_raw_os_error(OsString::from("between"), 2)
                    .with_bytes(OsString::from("second"), b"beta".to_vec())
                    .with_error(
                        OsString::from("after"),
                        io::ErrorKind::Other,
                        "after failed",
                    );
                let (status, stdout, stderr) = run_case(
                    &["fmt", "before", "first", "between", "second", "after"],
                    b"",
                    &mut opener,
                );
                assert_eq!(status, 3);
                assert_eq!(stdout, b"alpha\nbeta\n");
                assert_eq!(
                    stderr,
                    b"fmt: before: before denied\n\
fmt: between: No such file or directory\n\
fmt: after: after failed\n"
                );
                assert_eq!(
                    opener.opened,
                    [
                        OsString::from("before"),
                        OsString::from("first"),
                        OsString::from("between"),
                        OsString::from("second"),
                        OsString::from("after")
                    ]
                );
            }

            #[test]
            fn open_warning_preserves_raw_program_and_filename_bytes() {
                let raw_path = OsString::from_vec(b"missing-\xff".to_vec());
                let mut opener = MockFileOpener::default().with_error(
                    raw_path.clone(),
                    io::ErrorKind::NotFound,
                    "not found",
                );
                let arguments = vec![
                    OsString::from_vec(b"/tmp/raw-\xfe".to_vec()),
                    raw_path.clone(),
                ];
                let (status, stdout, stderr) = run_os_case(arguments, b"", &mut opener);
                assert_eq!(status, 1);
                assert!(stdout.is_empty());
                assert_eq!(stderr, b"raw-\xfe: missing-\xff: not found\n");
                assert_eq!(opener.opened, [raw_path]);
            }
        }

        mod read_errors {
            use super::*;

            #[test]
            fn partial_file_line_is_finalized_before_one_warning() {
                let mut opener = MockFileOpener::default().with_read_error(
                    OsString::from("input"),
                    b"first line\npartial".to_vec(),
                    io::ErrorKind::Other,
                    "read failed",
                );
                let (status, stdout, stderr) =
                    run_case(&["fmt", "-w", "80", "input"], b"", &mut opener);
                assert_eq!(status, 1);
                assert_eq!(stdout, b"first line partial\n");
                assert_eq!(stderr, b"fmt: input: read failed\n");
            }

            #[test]
            fn directory_style_deferred_error_uses_source_os_text() {
                let mut opener = MockFileOpener::default().with_raw_os_read_error(
                    OsString::from("directory"),
                    Vec::new(),
                    21,
                );
                let (status, stdout, stderr) = run_case(&["fmt", "directory"], b"", &mut opener);
                assert_eq!(status, 1);
                assert!(stdout.is_empty());
                assert_eq!(stderr, b"fmt: directory: Is a directory\n");
            }

            #[test]
            fn stdin_partial_read_failure_uses_the_standard_input_name() {
                let invocation = Invocation {
                    argv: vec![OsString::from("fmt")],
                    locale_mode: LocaleMode::Utf8,
                    posixly_correct: false,
                };
                let mut stdin = PrefixThenErrorReader::new(
                    b"stdin prefix".to_vec(),
                    io::Error::new(io::ErrorKind::Other, "stdin failed"),
                );
                let mut stdout = Vec::new();
                let mut stderr = Vec::new();
                let mut opener = MockFileOpener::default();
                let status = run(
                    invocation,
                    &mut stdin,
                    &mut stdout,
                    &mut stderr,
                    &mut opener,
                );
                assert_eq!(status, 1);
                assert_eq!(stdout, b"stdin prefix\n");
                assert_eq!(stderr, b"fmt: standard input: stdin failed\n");
                assert!(opener.opened.is_empty());
            }
        }

        mod errors {
            use super::*;
            use std::cell::RefCell;
            use std::rc::Rc;

            #[test]
            fn read_failures_continue_with_later_files() {
                let mut opener = MockFileOpener::default()
                    .with_read_error(
                        OsString::from("broken"),
                        b"broken prefix".to_vec(),
                        io::ErrorKind::Other,
                        "deferred failure",
                    )
                    .with_bytes(OsString::from("later"), b"later success".to_vec());
                let (status, stdout, stderr) =
                    run_case(&["fmt", "broken", "later"], b"", &mut opener);
                assert_eq!(status, 1);
                assert_eq!(stdout, b"broken prefix\nlater success\n");
                assert_eq!(stderr, b"fmt: broken: deferred failure\n");
                assert_eq!(
                    opener.opened,
                    [OsString::from("broken"), OsString::from("later")]
                );
            }

            #[test]
            fn status_saturates_at_127_without_stopping_opens_or_warnings() {
                let mut arguments = vec![OsString::from("fmt")];
                arguments.extend((0..130).map(|index| OsString::from(format!("missing-{index}"))));
                let mut opener = MockFileOpener::default();
                let (status, stdout, stderr) = run_os_case(arguments, b"", &mut opener);
                assert_eq!(status, 127);
                assert!(stdout.is_empty());
                assert_eq!(opener.opened.len(), 130);
                assert_eq!(
                    stderr
                        .split(|byte| *byte == b'\n')
                        .filter(|line| !line.is_empty())
                        .count(),
                    130
                );
                assert!(stderr.starts_with(b"fmt: missing-0: mock path was not configured\n"));
                assert!(stderr.ends_with(b"fmt: missing-129: mock path was not configured\n"));
            }

            #[test]
            fn stderr_write_failure_does_not_change_status_or_stop_files() {
                let invocation = Invocation {
                    argv: vec![
                        OsString::from("fmt"),
                        OsString::from("missing"),
                        OsString::from("later"),
                    ],
                    locale_mode: LocaleMode::Utf8,
                    posixly_correct: false,
                };
                let mut stdin = Cursor::new(Vec::<u8>::new());
                let mut stdout = Vec::new();
                let mut stderr = FailingWriter::new(4, false);
                let mut opener = MockFileOpener::default()
                    .with_error(
                        OsString::from("missing"),
                        io::ErrorKind::Other,
                        "open failed",
                    )
                    .with_bytes(OsString::from("later"), b"later success".to_vec());
                let status = run(
                    invocation,
                    &mut stdin,
                    &mut stdout,
                    &mut stderr,
                    &mut opener,
                );
                assert_eq!(status, 1);
                assert_eq!(stdout, b"later success\n");
                assert_eq!(stderr.bytes, b"fmt:");
                assert_eq!(
                    opener.opened,
                    [OsString::from("missing"), OsString::from("later")]
                );
            }

            #[test]
            fn redirected_stdout_is_flushed_after_immediate_warnings() {
                struct SharedWriter(Rc<RefCell<Vec<u8>>>);

                impl Write for SharedWriter {
                    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
                        self.0.borrow_mut().extend_from_slice(bytes);
                        Ok(bytes.len())
                    }

                    fn flush(&mut self) -> io::Result<()> {
                        Ok(())
                    }
                }

                let invocation = Invocation {
                    argv: vec![
                        OsString::from("fmt"),
                        OsString::from("missing-before"),
                        OsString::from("first"),
                        OsString::from("missing-after"),
                        OsString::from("second"),
                    ],
                    locale_mode: LocaleMode::Utf8,
                    posixly_correct: false,
                };
                let merged = Rc::new(RefCell::new(Vec::new()));
                let mut stdin = Cursor::new(Vec::<u8>::new());
                let mut unbuffered_stdout = SharedWriter(Rc::clone(&merged));
                let mut stdout = FullyBufferedWriter::new(&mut unbuffered_stdout);
                let mut stderr = SharedWriter(Rc::clone(&merged));
                let mut opener = MockFileOpener::default()
                    .with_error(
                        OsString::from("missing-before"),
                        io::ErrorKind::Other,
                        "before failed",
                    )
                    .with_bytes(OsString::from("first"), b"alpha".to_vec())
                    .with_error(
                        OsString::from("missing-after"),
                        io::ErrorKind::Other,
                        "after failed",
                    )
                    .with_bytes(OsString::from("second"), b"beta".to_vec());
                let status = run(
                    invocation,
                    &mut stdin,
                    &mut stdout,
                    &mut stderr,
                    &mut opener,
                );
                assert_eq!(status, 2);
                assert_eq!(
                    merged.borrow().as_slice(),
                    b"fmt: missing-before: before failed\n\
fmt: missing-after: after failed\n\
alpha\n\
beta\n"
                );
            }

            #[test]
            fn redirected_stdout_flushes_in_source_sized_blocks() {
                struct SharedWriter(Rc<RefCell<Vec<u8>>>);

                impl Write for SharedWriter {
                    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
                        self.0.borrow_mut().extend_from_slice(bytes);
                        Ok(bytes.len())
                    }

                    fn flush(&mut self) -> io::Result<()> {
                        Ok(())
                    }
                }

                let invocation = Invocation {
                    argv: vec![
                        OsString::from("fmt"),
                        OsString::from("-w"),
                        OsString::from("10000"),
                        OsString::from("large"),
                        OsString::from("missing"),
                    ],
                    locale_mode: LocaleMode::Utf8,
                    posixly_correct: false,
                };
                let merged = Rc::new(RefCell::new(Vec::new()));
                let mut stdin = Cursor::new(Vec::<u8>::new());
                let mut unbuffered_stdout = SharedWriter(Rc::clone(&merged));
                let mut stdout = FullyBufferedWriter::new(&mut unbuffered_stdout);
                let mut stderr = SharedWriter(Rc::clone(&merged));
                let mut opener = MockFileOpener::default()
                    .with_bytes(OsString::from("large"), vec![b'a'; 4097])
                    .with_error(
                        OsString::from("missing"),
                        io::ErrorKind::Other,
                        "open failed",
                    );
                let status = run(
                    invocation,
                    &mut stdin,
                    &mut stdout,
                    &mut stderr,
                    &mut opener,
                );
                assert_eq!(status, 1);

                let merged = merged.borrow();
                let warning = b"fmt: missing: open failed\n";
                let warning_start = merged
                    .windows(warning.len())
                    .position(|window| window == warning)
                    .expect("warning in merged output");
                assert_eq!(warning_start, 4096);
                assert!(merged[..warning_start].iter().all(|byte| *byte == b'a'));
                assert_eq!(&merged[warning_start + warning.len()..], b"a\n");
            }
        }
    }
}
