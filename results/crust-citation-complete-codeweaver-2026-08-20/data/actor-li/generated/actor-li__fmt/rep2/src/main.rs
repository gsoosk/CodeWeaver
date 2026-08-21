use std::env;
use std::ffi::{OsStr, OsString};
use std::fs::File;
use std::io::{self, Read, Write};
use std::os::unix::ffi::{OsStrExt, OsStringExt};

use unicode_width::UnicodeWidthChar;

const SILLY: usize = usize::MAX;
const MAX_ERRORS: u8 = 127;

#[derive(Clone, Debug, Eq, PartialEq)]
struct Options {
    center_p: bool,
    goal_length: usize,
    max_length: usize,
    coalesce_spaces_p: bool,
    allow_indented_paragraphs: bool,
    tab_width: i32,
    output_tab_width: usize,
    sentence_enders: Vec<u8>,
    grok_mail_headers: bool,
    format_troff: bool,
}

impl Default for Options {
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

#[derive(Debug, Default, Eq, PartialEq)]
struct OutputState {
    x: usize,
    x0: usize,
    pending_spaces: usize,
    output_in_paragraph: bool,
}

#[derive(Debug)]
struct RunState {
    options: Options,
    output: OutputState,
    n_errors: u8,
}

impl RunState {
    fn new(options: Options) -> Self {
        Self {
            options,
            output: OutputState::default(),
            n_errors: 0,
        }
    }

    fn record_error(&mut self) {
        if self.n_errors < MAX_ERRORS {
            self.n_errors += 1;
        }
    }

    fn process_named_file(
        &mut self,
        name: &OsStr,
        file_system: &mut dyn FileSystem,
        characters: &dyn CharacterSemantics,
        stdout: &mut OutputWriter<'_>,
        stderr: &mut OutputWriter<'_>,
        program_name: &ProgramName,
    ) -> Result<(), FatalError> {
        let mut stream = match file_system.open(name) {
            Ok(stream) => stream,
            Err(error) => {
                render_diagnostic(&io_diagnostic(name, &error), program_name, stderr);
                self.record_error();
                return Ok(());
            }
        };

        match self.process_stream(&mut *stream, name, characters, stdout) {
            Ok(()) => Ok(()),
            Err(StreamFailure::Read(error)) => {
                render_diagnostic(&io_diagnostic(name, &error), program_name, stderr);
                self.record_error();
                Ok(())
            }
            Err(StreamFailure::OutOfMemory) => Err(FatalError::Diagnostic(Diagnostic::OutOfMemory)),
        }
    }

    fn process_stream(
        &mut self,
        stream: &mut dyn Read,
        _name: &OsStr,
        characters: &dyn CharacterSemantics,
        stdout: &mut OutputWriter<'_>,
    ) -> Result<(), StreamFailure> {
        if self.options.center_p {
            return self.center_stream(stream, _name, characters, stdout);
        }

        let mut reader = LineReader::new(stream);
        let mut last_indent = SILLY;
        let mut para_line_number = 0usize;
        let mut first_indent = SILLY;
        let mut prev_header_type = HdrType::ParagraphStart;
        let mut read_failure = None;

        loop {
            let raw_line = match reader.get_line(self.options.format_troff) {
                Ok(Some(line)) => line,
                Ok(None) => break,
                Err(error) => {
                    read_failure = Some(error);
                    break;
                }
            };
            let line_end = raw_line
                .iter()
                .position(|byte| *byte == 0)
                .unwrap_or(raw_line.len());
            let line = &raw_line[..line_end];
            let indent = indent_length(line, self.options.tab_width);
            let mut header_type = HdrType::NonHeader;
            if self.options.grok_mail_headers && prev_header_type != HdrType::NonHeader {
                if indent == 0 && might_be_header(line) {
                    header_type = HdrType::Header;
                } else if indent > 0
                    && prev_header_type.source_value() > HdrType::NonHeader.source_value()
                {
                    header_type = HdrType::Continuation;
                }
            }

            let begins_troff_request = line.first() == Some(&b'.') && !self.options.format_troff;
            let starts_paragraph = line.is_empty()
                || begins_troff_request
                || header_type == HdrType::Header
                || (header_type == HdrType::NonHeader
                    && prev_header_type.source_value() > HdrType::NonHeader.source_value())
                || (indent != last_indent
                    && header_type != HdrType::Continuation
                    && (!self.options.allow_indented_paragraphs || para_line_number != 1));

            if starts_paragraph {
                self.new_paragraph(indent, stdout);
                para_line_number = 0;
                first_indent = indent;
                last_indent = indent;

                if begins_troff_request {
                    stdout.write_all_compat(line);
                    stdout.write_all_compat(b"\n");
                    continue;
                }
                if header_type == HdrType::Header {
                    last_indent = 2;
                }
                if line.is_empty() {
                    stdout.write_all_compat(b"\n");
                    prev_header_type = HdrType::ParagraphStart;
                    continue;
                } else if indent != last_indent && header_type != HdrType::Continuation {
                    last_indent = indent;
                }
                prev_header_type = header_type;
            }

            let mut line_width = indent;
            let mut word_start = 0usize;
            while word_start < line.len() {
                let mut cursor = word_start;
                let mut word_length = 0usize;
                let mut word_width = 0usize;
                let mut space_width = 0usize;

                while cursor < line.len() {
                    let unit = characters.decode(&line[cursor..]);
                    let consumed = unit.consumed.max(1).min(line.len() - cursor);
                    let character_width = if unit.value == DecodedValue::Scalar('\t') {
                        next_tab_stop(line_width, self.options.tab_width).wrapping_sub(line_width)
                    } else {
                        unit.display_width
                    };
                    let is_word_blank =
                        unit.is_blank && unit.value != DecodedValue::Scalar('\u{00a0}');

                    if is_word_blank {
                        if word_length == 0 {
                            word_start += consumed;
                            cursor += consumed;
                            line_width = line_width.wrapping_add(character_width);
                            continue;
                        }
                        space_width = space_width.wrapping_add(character_width);
                    } else {
                        if space_width > 0 {
                            break;
                        }
                        word_length = word_length.wrapping_add(consumed);
                        word_width = word_width.wrapping_add(character_width);
                    }

                    line_width = line_width.wrapping_add(character_width);
                    cursor += consumed;
                }

                let word_end = word_start.saturating_add(word_length).min(line.len());
                self.output_word(
                    first_indent,
                    last_indent,
                    &line[word_start..word_end],
                    word_width,
                    space_width,
                    stdout,
                );
                word_start = cursor;
            }
            para_line_number = para_line_number.wrapping_add(1);
        }

        self.new_paragraph(0, stdout);
        match read_failure {
            Some(error) => Err(error),
            None => Ok(()),
        }
    }

    fn new_paragraph(&mut self, indent: usize, stdout: &mut OutputWriter<'_>) {
        if self.output.x0 > 0 {
            stdout.write_all_compat(b"\n");
        }
        self.output.x = indent;
        self.output.x0 = 0;
        self.output.pending_spaces = 0;
        self.output.output_in_paragraph = false;
    }

    fn output_indent(&self, mut n_spaces: usize, stdout: &mut OutputWriter<'_>) {
        if n_spaces == 0 {
            return;
        }
        if self.options.output_tab_width > 0 {
            let tabs = n_spaces / self.options.output_tab_width;
            stdout.write_repeated(b'\t', tabs);
            n_spaces %= self.options.output_tab_width;
        }
        stdout.write_repeated(b' ', n_spaces);
    }

    #[allow(clippy::too_many_arguments)]
    fn output_word(
        &mut self,
        indent0: usize,
        indent1: usize,
        word: &[u8],
        width: usize,
        mut spaces: usize,
        stdout: &mut OutputWriter<'_>,
    ) {
        let new_x = self
            .output
            .x
            .wrapping_add(self.output.pending_spaces)
            .wrapping_add(width);

        if self.options.coalesce_spaces_p || spaces == 0 {
            spaces = if word
                .last()
                .is_some_and(|byte| self.options.sentence_enders.contains(byte))
            {
                2
            } else {
                1
            };
        }

        if self.output.x0 == 0 {
            self.output_indent(
                if self.output.output_in_paragraph {
                    indent1
                } else {
                    indent0
                },
                stdout,
            );
        } else if new_x > self.options.max_length
            || self.output.x >= self.options.goal_length
            || (new_x > self.options.goal_length
                && new_x.wrapping_sub(self.options.goal_length)
                    > self.options.goal_length.wrapping_sub(self.output.x))
        {
            stdout.write_all_compat(b"\n");
            self.output_indent(indent1, stdout);
            self.output.x0 = 0;
            self.output.x = indent1;
        } else {
            self.output.x0 = self.output.x0.wrapping_add(self.output.pending_spaces);
            self.output.x = self.output.x.wrapping_add(self.output.pending_spaces);
            stdout.write_repeated(b' ', self.output.pending_spaces);
        }

        self.output.x0 = self.output.x0.wrapping_add(width);
        self.output.x = self.output.x.wrapping_add(width);
        stdout.write_all_compat(word);
        self.output.pending_spaces = spaces;
        self.output.output_in_paragraph = true;
    }

    fn center_stream(
        &mut self,
        stream: &mut dyn Read,
        _name: &OsStr,
        characters: &dyn CharacterSemantics,
        stdout: &mut OutputWriter<'_>,
    ) -> Result<(), StreamFailure> {
        let mut reader = LineReader::new(stream);
        loop {
            let source_line = match reader.get_line(self.options.format_troff) {
                Ok(Some(line)) => line,
                Ok(None) => return Ok(()),
                Err(error) => return Err(error),
            };
            let line_end = source_line
                .iter()
                .position(|byte| *byte == 0)
                .unwrap_or(source_line.len());
            let mut line = source_line[..line_end].to_vec();
            let mut width = 0usize;
            let mut cursor = 0usize;
            let mut output_start = 0usize;

            while cursor < line.len() {
                if line[cursor] == b'\t' {
                    line[cursor] = b' ';
                }
                let unit = characters.decode(&line[cursor..]);
                let consumed = unit.consumed.max(1).min(line.len() - cursor);
                let (character_width, is_space) = if unit.value == DecodedValue::Invalid {
                    line[cursor] = b'?';
                    (1, false)
                } else {
                    (unit.display_width, unit.is_space)
                };

                if width == 0 && is_space {
                    output_start = output_start.saturating_add(consumed).min(line.len());
                } else {
                    width = width.wrapping_add(character_width);
                }
                cursor += consumed;
            }

            let mut padding = 0usize;
            while width < self.options.goal_length {
                padding += 1;
                width = width.wrapping_add(2);
            }
            stdout.write_repeated(b' ', padding);
            stdout.write_all_compat(&line[output_start..]);
            stdout.write_all_compat(b"\n");
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum HdrType {
    ParagraphStart,
    NonHeader,
    Header,
    Continuation,
}

impl HdrType {
    fn source_value(self) -> i8 {
        match self {
            Self::ParagraphStart => -1,
            Self::NonHeader => 0,
            Self::Header => 1,
            Self::Continuation => 2,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum LocaleMode {
    C,
    Utf8,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct LocaleEnvironment {
    lc_all: Option<OsString>,
    lc_ctype: Option<OsString>,
    lang: Option<OsString>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct Invocation {
    args: Vec<OsString>,
    locale_environment: LocaleEnvironment,
    posixly_correct: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ProgramName {
    argv0: OsString,
    basename: OsString,
}

impl ProgramName {
    fn from_argv0(argv0: &OsStr) -> Self {
        let bytes = argv0.as_bytes();
        let basename = bytes.rsplit(|byte| *byte == b'/').next().unwrap_or(bytes);
        Self {
            argv0: argv0.to_os_string(),
            basename: OsString::from_vec(basename.to_vec()),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DecodedValue {
    Scalar(char),
    Invalid,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DecodedUnit {
    consumed: usize,
    value: DecodedValue,
    display_width: usize,
    is_blank: bool,
    is_space: bool,
}

trait CharacterSemantics {
    fn decode(&self, input: &[u8]) -> DecodedUnit;
}

#[derive(Debug)]
struct RealCharacterSemantics {
    mode: LocaleMode,
}

impl RealCharacterSemantics {
    fn new(mode: LocaleMode) -> Self {
        Self { mode }
    }

    fn scalar_unit(&self, character: char, consumed: usize) -> DecodedUnit {
        let is_space = match self.mode {
            LocaleMode::C => matches!(
                character,
                ' ' | '\t' | '\n' | '\r' | '\u{000b}' | '\u{000c}'
            ),
            LocaleMode::Utf8 => character.is_whitespace(),
        };
        let is_blank = match self.mode {
            LocaleMode::C => matches!(character, ' ' | '\t'),
            LocaleMode::Utf8 => {
                character.is_whitespace()
                    && !matches!(
                        character,
                        '\n' | '\r'
                            | '\u{000b}'
                            | '\u{000c}'
                            | '\u{0085}'
                            | '\u{2028}'
                            | '\u{2029}'
                    )
            }
        };
        DecodedUnit {
            consumed,
            value: DecodedValue::Scalar(character),
            display_width: character.width().unwrap_or(1),
            is_blank,
            is_space,
        }
    }

    fn invalid_unit() -> DecodedUnit {
        DecodedUnit {
            consumed: 1,
            value: DecodedValue::Invalid,
            display_width: 1,
            is_blank: false,
            is_space: false,
        }
    }
}

impl CharacterSemantics for RealCharacterSemantics {
    fn decode(&self, input: &[u8]) -> DecodedUnit {
        let Some(first) = input.first().copied() else {
            return Self::invalid_unit();
        };
        if self.mode == LocaleMode::C {
            return if first.is_ascii() {
                self.scalar_unit(char::from(first), 1)
            } else {
                Self::invalid_unit()
            };
        }
        if first.is_ascii() {
            return self.scalar_unit(char::from(first), 1);
        }

        let expected = match first {
            0xc2..=0xdf => 2,
            0xe0..=0xef => 3,
            0xf0..=0xf4 => 4,
            _ => return Self::invalid_unit(),
        };
        if input.len() < expected {
            return Self::invalid_unit();
        }
        match std::str::from_utf8(&input[..expected]) {
            Ok(value) => {
                let character = value.chars().next().unwrap_or('\0');
                self.scalar_unit(character, expected)
            }
            Err(_) => Self::invalid_unit(),
        }
    }
}

trait FileSystem {
    fn open(&mut self, path: &OsStr) -> io::Result<Box<dyn Read>>;
}

#[derive(Debug, Default)]
struct RealFileSystem;

impl FileSystem for RealFileSystem {
    fn open(&mut self, path: &OsStr) -> io::Result<Box<dyn Read>> {
        File::open(path).map(|file| Box::new(file) as Box<dyn Read>)
    }
}

struct OutputWriter<'a> {
    inner: &'a mut dyn Write,
    first_error: Option<io::Error>,
}

impl<'a> OutputWriter<'a> {
    fn new(inner: &'a mut dyn Write) -> Self {
        Self {
            inner,
            first_error: None,
        }
    }

    fn write_all_compat(&mut self, bytes: &[u8]) {
        if self.first_error.is_some() {
            return;
        }
        if let Err(error) = self.inner.write_all(bytes) {
            self.first_error = Some(error);
        }
    }

    fn write_repeated(&mut self, byte: u8, mut count: usize) {
        const CHUNK_SIZE: usize = 256;
        let chunk = [byte; CHUNK_SIZE];
        while count >= CHUNK_SIZE && !self.has_failed() {
            self.write_all_compat(&chunk);
            count -= CHUNK_SIZE;
        }
        if count > 0 {
            self.write_all_compat(&chunk[..count]);
        }
    }

    fn flush_compat(&mut self) {
        if self.first_error.is_some() {
            return;
        }
        if let Err(error) = self.inner.flush() {
            self.first_error = Some(error);
        }
    }

    fn has_failed(&self) -> bool {
        self.first_error.is_some()
    }
}

#[derive(Debug)]
enum Diagnostic {
    Usage,
    Getopt(Vec<u8>),
    Application(Vec<u8>),
    OutOfMemory,
}

#[derive(Debug)]
enum FatalError {
    Diagnostic(Diagnostic),
}

#[derive(Debug)]
enum StreamFailure {
    Read(io::Error),
    OutOfMemory,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum PositiveValue {
    Value(usize),
    NotNumeric,
}

#[derive(Debug)]
struct ParsedArguments {
    options: Options,
    operands: Vec<OsString>,
}

fn get_positive(
    input: &[u8],
    error_message: &'static [u8],
    fussy_p: bool,
) -> Result<PositiveValue, Diagnostic> {
    let error = || Diagnostic::Application(error_message.to_vec());
    let mut cursor = 0usize;
    while cursor < input.len() && is_narrow_space(input[cursor]) {
        cursor += 1;
    }

    let mut negative = false;
    if let Some(sign) = input.get(cursor) {
        if *sign == b'+' || *sign == b'-' {
            negative = *sign == b'-';
            cursor += 1;
        }
    }
    let digits_start = cursor;
    let base = if input.get(cursor) == Some(&b'0') {
        if matches!(input.get(cursor + 1), Some(b'x' | b'X'))
            && input
                .get(cursor + 2)
                .and_then(|byte| digit_value(*byte))
                .is_some_and(|digit| digit < 16)
        {
            cursor += 2;
            16u32
        } else {
            8u32
        }
    } else {
        10u32
    };

    let limit = if negative {
        (i64::MAX as u128) + 1
    } else {
        i64::MAX as u128
    };
    let mut magnitude = 0u128;
    let mut digits = 0usize;
    while let Some(byte) = input.get(cursor).copied() {
        let Some(digit) = digit_value(byte) else {
            break;
        };
        if digit >= base {
            break;
        }
        magnitude = magnitude
            .saturating_mul(u128::from(base))
            .saturating_add(u128::from(digit))
            .min(limit);
        cursor += 1;
        digits += 1;
    }

    if digits == 0 {
        cursor = 0;
    } else if base == 8 && digits_start < cursor {
        // The leading zero is one of the octal digits.
    }

    if cursor < input.len() {
        return if fussy_p {
            Err(error())
        } else {
            Ok(PositiveValue::NotNumeric)
        };
    }
    if digits == 0 || negative || magnitude == 0 {
        return Err(error());
    }
    Ok(PositiveValue::Value(magnitude as usize))
}

fn digit_value(byte: u8) -> Option<u32> {
    match byte {
        b'0'..=b'9' => Some(u32::from(byte - b'0')),
        b'a'..=b'f' => Some(u32::from(byte - b'a') + 10),
        b'A'..=b'F' => Some(u32::from(byte - b'A') + 10),
        _ => None,
    }
}

fn parse_arguments(
    invocation: &Invocation,
    program_name: &ProgramName,
) -> Result<ParsedArguments, Diagnostic> {
    let mut options = Options::default();
    let mut operands = Vec::new();
    let arguments = invocation
        .args
        .iter()
        .skip(1)
        .map(|argument| argument.as_bytes().to_vec())
        .collect::<Vec<_>>();
    let mut argument_index = 0usize;
    let mut options_finished = false;

    while argument_index < arguments.len() {
        let argument = &arguments[argument_index];
        if options_finished {
            operands.push(OsString::from_vec(argument.clone()));
            argument_index += 1;
            continue;
        }
        if argument == b"--" {
            options_finished = true;
            argument_index += 1;
            continue;
        }
        if argument.len() < 2 || argument[0] != b'-' || argument == b"-" {
            operands.push(OsString::from_vec(argument.clone()));
            argument_index += 1;
            if invocation.posixly_correct {
                options_finished = true;
            }
            continue;
        }

        let mut option_index = 1usize;
        while option_index < argument.len() {
            let option = argument[option_index];
            match option {
                b'c' => options.center_p = true,
                b'm' => options.grok_mail_headers = true,
                b'n' => options.format_troff = true,
                b'p' => options.allow_indented_paragraphs = true,
                b's' => options.coalesce_spaces_p = true,
                b'h' => return Err(Diagnostic::Usage),
                b'd' | b'l' | b't' | b'w' => {
                    let value = if option_index + 1 < argument.len() {
                        argument[option_index + 1..].to_vec()
                    } else if argument_index + 1 < arguments.len() {
                        argument_index += 1;
                        arguments[argument_index].clone()
                    } else {
                        return Err(missing_option_argument(program_name, option));
                    };
                    match option {
                        b'd' => options.sentence_enders = value,
                        b'l' => {
                            options.output_tab_width =
                                positive_option(&value, b"output tab width must be positive")?
                        }
                        b't' => {
                            options.tab_width =
                                positive_option(&value, b"tab width must be positive")? as i32
                        }
                        b'w' => {
                            options.goal_length =
                                positive_option(&value, b"width must be positive")?;
                            options.max_length = options.goal_length;
                        }
                        _ => {}
                    }
                    break;
                }
                b'0'..=b'9' => {
                    if options.goal_length == 0 {
                        options.goal_length =
                            positive_option(&argument[1..], b"width must be nonzero")?;
                        options.max_length = options.goal_length;
                    }
                }
                _ => {
                    return Err(invalid_option(program_name, option));
                }
            }
            option_index += 1;
        }
        argument_index += 1;
    }

    if options.goal_length == 0 && !operands.is_empty() {
        match get_positive(
            operands[0].as_bytes(),
            b"goal length must be positive",
            false,
        )? {
            PositiveValue::NotNumeric => {}
            PositiveValue::Value(goal) => {
                options.goal_length = goal;
                operands.remove(0);
                if !operands.is_empty() {
                    match get_positive(
                        operands[0].as_bytes(),
                        b"max length must be positive",
                        false,
                    )? {
                        PositiveValue::NotNumeric => {}
                        PositiveValue::Value(maximum) => {
                            options.max_length = maximum;
                            operands.remove(0);
                            if options.max_length < options.goal_length {
                                return Err(Diagnostic::Application(
                                    b"max length must be >= goal length".to_vec(),
                                ));
                            }
                        }
                    }
                }
            }
        }
    }

    if options.goal_length == 0 {
        options.goal_length = 65;
    }
    if options.max_length == 0 {
        options.max_length = options.goal_length.wrapping_add(10);
    }
    Ok(ParsedArguments { options, operands })
}

fn positive_option(value: &[u8], message: &'static [u8]) -> Result<usize, Diagnostic> {
    match get_positive(value, message, true)? {
        PositiveValue::Value(value) => Ok(value),
        PositiveValue::NotNumeric => Err(Diagnostic::Application(message.to_vec())),
    }
}

fn invalid_option(program_name: &ProgramName, option: u8) -> Diagnostic {
    let mut message = program_name.argv0.as_bytes().to_vec();
    message.extend_from_slice(b": invalid option -- '");
    message.push(option);
    message.extend_from_slice(b"'\n");
    Diagnostic::Getopt(message)
}

fn missing_option_argument(program_name: &ProgramName, option: u8) -> Diagnostic {
    let mut message = program_name.argv0.as_bytes().to_vec();
    message.extend_from_slice(b": option requires an argument -- '");
    message.push(option);
    message.extend_from_slice(b"'\n");
    Diagnostic::Getopt(message)
}

fn select_locale_mode(environment: &LocaleEnvironment) -> LocaleMode {
    let selected = [
        environment.lc_all.as_ref(),
        environment.lc_ctype.as_ref(),
        environment.lang.as_ref(),
    ]
    .into_iter()
    .flatten()
    .find(|value| !value.as_bytes().is_empty());
    let Some(locale) = selected else {
        return LocaleMode::C;
    };
    let mut normalized = locale.as_bytes().to_vec();
    normalized.make_ascii_lowercase();
    if normalized == b"c.utf-8" || normalized == b"c.utf8" {
        LocaleMode::Utf8
    } else {
        LocaleMode::C
    }
}

fn usage(program_name: &ProgramName) -> Vec<u8> {
    let mut message = b"usage: ".to_vec();
    message.extend_from_slice(program_name.basename.as_bytes());
    message.extend_from_slice(
        b" [-cmnps] [-d chars] [-l number] [-t number]\n\
\t[goal [maximum] | -width | -w width] [file ...]\n",
    );
    message
}

fn render_diagnostic(
    diagnostic: &Diagnostic,
    program_name: &ProgramName,
    stderr: &mut OutputWriter<'_>,
) {
    match diagnostic {
        Diagnostic::Usage => stderr.write_all_compat(&usage(program_name)),
        Diagnostic::Getopt(message) => {
            stderr.write_all_compat(message);
            stderr.write_all_compat(&usage(program_name));
        }
        Diagnostic::Application(message) => {
            stderr.write_all_compat(program_name.basename.as_bytes());
            stderr.write_all_compat(b": ");
            stderr.write_all_compat(message);
            stderr.write_all_compat(b"\n");
        }
        Diagnostic::OutOfMemory => {
            stderr.write_all_compat(program_name.basename.as_bytes());
            stderr.write_all_compat(b": out of memory\n");
        }
    }
}

fn io_diagnostic(name: &OsStr, error: &io::Error) -> Diagnostic {
    let mut message = name.as_bytes().to_vec();
    message.extend_from_slice(b": ");
    let mut error_text = error.to_string();
    if let Some(code) = error.raw_os_error() {
        let suffix = format!(" (os error {code})");
        if let Some(stripped) = error_text.strip_suffix(&suffix) {
            error_text = stripped.to_owned();
        }
    }
    message.extend_from_slice(error_text.as_bytes());
    Diagnostic::Application(message)
}

struct LineReader<'a> {
    reader: &'a mut dyn Read,
    buffer: Vec<u8>,
    input_buffer: [u8; 8192],
    input_start: usize,
    input_end: usize,
    pending_error: Option<io::Error>,
    finished: bool,
}

impl<'a> LineReader<'a> {
    fn new(reader: &'a mut dyn Read) -> Self {
        Self {
            reader,
            buffer: Vec::new(),
            input_buffer: [0; 8192],
            input_start: 0,
            input_end: 0,
            pending_error: None,
            finished: false,
        }
    }

    fn read_byte(&mut self) -> io::Result<Option<u8>> {
        loop {
            if self.input_start < self.input_end {
                let byte = self.input_buffer[self.input_start];
                self.input_start += 1;
                return Ok(Some(byte));
            }
            match self.reader.read(&mut self.input_buffer) {
                Ok(0) => return Ok(None),
                Ok(count) => {
                    self.input_start = 0;
                    self.input_end = count;
                }
                Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
                Err(error) => return Err(error),
            }
        }
    }

    fn get_line(&mut self, format_troff: bool) -> Result<Option<&[u8]>, StreamFailure> {
        if let Some(error) = self.pending_error.take() {
            self.finished = true;
            return Err(StreamFailure::Read(error));
        }
        if self.finished {
            return Ok(None);
        }
        self.buffer.clear();
        let mut troff = false;
        let mut terminated = false;

        loop {
            let byte = match self.read_byte() {
                Ok(Some(byte)) => byte,
                Ok(None) => {
                    self.finished = true;
                    break;
                }
                Err(error) => {
                    if self.buffer.is_empty() {
                        self.finished = true;
                        return Err(StreamFailure::Read(error));
                    }
                    self.pending_error = Some(error);
                    break;
                }
            };
            if byte == b'\n' {
                terminated = true;
                break;
            }
            if self.buffer.is_empty() && byte == b'.' && !format_troff {
                troff = true;
            }
            if troff || byte == b'\t' || !byte.is_ascii_control() {
                if self.buffer.capacity() <= self.buffer.len() + 1 {
                    let capacity = self.buffer.capacity();
                    let target = if capacity == 0 {
                        100
                    } else {
                        capacity
                            .checked_mul(2)
                            .unwrap_or(usize::MAX)
                            .max(self.buffer.len().saturating_add(2))
                    };
                    xreallocarray(&mut self.buffer, target)
                        .map_err(|_| StreamFailure::OutOfMemory)?;
                }
                self.buffer.push(byte);
            } else if byte == b'\x08' {
                self.buffer.pop();
            }
        }

        while self.buffer.last().copied().is_some_and(is_narrow_space) {
            self.buffer.pop();
        }
        if !self.buffer.is_empty() || terminated {
            Ok(Some(&self.buffer))
        } else if let Some(error) = self.pending_error.take() {
            self.finished = true;
            Err(StreamFailure::Read(error))
        } else {
            Ok(None)
        }
    }
}

fn xreallocarray(buffer: &mut Vec<u8>, minimum_capacity: usize) -> Result<(), FatalError> {
    if minimum_capacity <= buffer.capacity() {
        return Ok(());
    }
    buffer
        .try_reserve_exact(minimum_capacity - buffer.capacity())
        .map_err(|_| FatalError::Diagnostic(Diagnostic::OutOfMemory))
}

fn is_narrow_space(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
}

fn next_tab_stop(column: usize, tab_width: i32) -> usize {
    let width = tab_width as usize;
    if width == 0 {
        return column;
    }
    column
        .wrapping_div(width)
        .wrapping_add(1)
        .wrapping_mul(width)
}

fn indent_length(line: &[u8], tab_width: i32) -> usize {
    let mut length = 0usize;
    for byte in line {
        match byte {
            b' ' => length = length.wrapping_add(1),
            b'\t' => length = next_tab_stop(length, tab_width),
            _ => break,
        }
    }
    length
}

fn might_be_header(line: &[u8]) -> bool {
    if !line.first().is_some_and(u8::is_ascii_uppercase) {
        return false;
    }
    let mut cursor = 1usize;
    while line
        .get(cursor)
        .is_some_and(|byte| byte.is_ascii_alphanumeric() || *byte == b'-')
    {
        cursor += 1;
    }
    line.get(cursor) == Some(&b':') && line.get(cursor + 1).copied().is_some_and(is_narrow_space)
}

fn run(
    invocation: &Invocation,
    stdin: &mut dyn Read,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
    file_system: &mut dyn FileSystem,
    characters: &dyn CharacterSemantics,
) -> i32 {
    let argv0 = invocation
        .args
        .first()
        .map(OsString::as_os_str)
        .unwrap_or_else(|| OsStr::new("fmt"));
    let program_name = ProgramName::from_argv0(argv0);
    let parsed = match parse_arguments(invocation, &program_name) {
        Ok(parsed) => parsed,
        Err(diagnostic) => {
            let mut stderr = OutputWriter::new(stderr);
            render_diagnostic(&diagnostic, &program_name, &mut stderr);
            stderr.flush_compat();
            return 1;
        }
    };

    let mut stdout = OutputWriter::new(stdout);
    let mut stderr = OutputWriter::new(stderr);
    let mut state = RunState::new(parsed.options);
    if parsed.operands.is_empty() {
        if let Err(error) =
            state.process_stream(stdin, OsStr::new("standard input"), characters, &mut stdout)
        {
            match error {
                StreamFailure::Read(error) => {
                    render_diagnostic(
                        &io_diagnostic(OsStr::new("standard input"), &error),
                        &program_name,
                        &mut stderr,
                    );
                    state.record_error();
                }
                StreamFailure::OutOfMemory => {
                    render_diagnostic(&Diagnostic::OutOfMemory, &program_name, &mut stderr);
                    stdout.flush_compat();
                    stderr.flush_compat();
                    return 1;
                }
            }
        }
    } else {
        for operand in parsed.operands {
            if let Err(FatalError::Diagnostic(diagnostic)) = state.process_named_file(
                &operand,
                file_system,
                characters,
                &mut stdout,
                &mut stderr,
                &program_name,
            ) {
                render_diagnostic(&diagnostic, &program_name, &mut stderr);
                stdout.flush_compat();
                stderr.flush_compat();
                return 1;
            }
        }
    }
    stdout.flush_compat();
    stderr.flush_compat();
    i32::from(state.n_errors)
}

fn process_main() -> i32 {
    let invocation = Invocation {
        args: env::args_os().collect(),
        locale_environment: LocaleEnvironment {
            lc_all: env::var_os("LC_ALL"),
            lc_ctype: env::var_os("LC_CTYPE"),
            lang: env::var_os("LANG"),
        },
        posixly_correct: env::var_os("POSIXLY_CORRECT").is_some(),
    };
    let characters =
        RealCharacterSemantics::new(select_locale_mode(&invocation.locale_environment));
    let mut file_system = RealFileSystem;
    let stdin_handle = io::stdin();
    let stdout_handle = io::stdout();
    let stderr_handle = io::stderr();
    let mut stdin = stdin_handle.lock();
    let mut stdout = io::BufWriter::new(stdout_handle.lock());
    let mut stderr = io::BufWriter::new(stderr_handle.lock());
    let status = run(
        &invocation,
        &mut stdin,
        &mut stdout,
        &mut stderr,
        &mut file_system,
        &characters,
    );
    let _ = stdout.flush();
    let _ = stderr.flush();
    status
}

fn main() {
    std::process::exit(process_main());
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;
    use std::collections::{HashMap, VecDeque};
    use std::io::Cursor;

    enum MockFile {
        Bytes(Vec<u8>),
        OpenError(io::ErrorKind),
        Scripted(ScriptedReader),
    }

    #[derive(Default)]
    struct MockFileSystem {
        entries: HashMap<OsString, VecDeque<MockFile>>,
    }

    impl MockFileSystem {
        fn add(&mut self, path: &[u8], file: MockFile) {
            self.entries
                .entry(OsString::from_vec(path.to_vec()))
                .or_default()
                .push_back(file);
        }
    }

    impl FileSystem for MockFileSystem {
        fn open(&mut self, path: &OsStr) -> io::Result<Box<dyn Read>> {
            let file = self
                .entries
                .get_mut(path)
                .and_then(VecDeque::pop_front)
                .ok_or_else(|| io::Error::from(io::ErrorKind::NotFound))?;
            match file {
                MockFile::Bytes(bytes) => Ok(Box::new(Cursor::new(bytes))),
                MockFile::OpenError(kind) => Err(io::Error::from(kind)),
                MockFile::Scripted(reader) => Ok(Box::new(reader)),
            }
        }
    }

    struct ScriptedReader {
        bytes: Cursor<Vec<u8>>,
        fail_after: Option<usize>,
        error_kind: io::ErrorKind,
    }

    impl Read for ScriptedReader {
        fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
            let position = self.bytes.position() as usize;
            if self
                .fail_after
                .is_some_and(|fail_after| position >= fail_after)
            {
                return Err(io::Error::from(self.error_kind));
            }
            let permitted = self
                .fail_after
                .map(|fail_after| fail_after.saturating_sub(position))
                .unwrap_or(buffer.len())
                .min(buffer.len());
            self.bytes.read(&mut buffer[..permitted])
        }
    }

    #[derive(Default)]
    struct MockCharacterSemantics {
        decoded_units: RefCell<VecDeque<DecodedUnit>>,
    }

    impl CharacterSemantics for MockCharacterSemantics {
        fn decode(&self, _input: &[u8]) -> DecodedUnit {
            self.decoded_units
                .borrow_mut()
                .pop_front()
                .expect("a decoded unit was queued")
        }
    }

    struct FailingWriter {
        fail_after: usize,
        accepted: Vec<u8>,
        fail_flush: bool,
    }

    impl Write for FailingWriter {
        fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
            if self.accepted.len() >= self.fail_after {
                return Err(io::Error::from(io::ErrorKind::BrokenPipe));
            }
            let count = buffer.len().min(self.fail_after - self.accepted.len());
            self.accepted.extend_from_slice(&buffer[..count]);
            Ok(count)
        }

        fn flush(&mut self) -> io::Result<()> {
            if self.fail_flush {
                Err(io::Error::from(io::ErrorKind::BrokenPipe))
            } else {
                Ok(())
            }
        }
    }

    fn invocation(arguments: &[&[u8]]) -> Invocation {
        Invocation {
            args: arguments
                .iter()
                .map(|argument| OsString::from_vec(argument.to_vec()))
                .collect(),
            locale_environment: LocaleEnvironment::default(),
            posixly_correct: false,
        }
    }

    fn run_case(arguments: &[&[u8]], input: &[u8]) -> (i32, Vec<u8>, Vec<u8>) {
        let invocation = invocation(arguments);
        let mut input = Cursor::new(input.to_vec());
        let mut stdout = Vec::new();
        let mut stderr = Vec::new();
        let mut files = MockFileSystem::default();
        let characters = RealCharacterSemantics::new(LocaleMode::Utf8);
        let status = run(
            &invocation,
            &mut input,
            &mut stdout,
            &mut stderr,
            &mut files,
            &characters,
        );
        (status, stdout, stderr)
    }

    mod cli_parser {
        use super::*;

        #[test]
        fn parses_options_clusters_and_operands() {
            let invocation = invocation(&[
                b"/tmp/fmt",
                b"-cmnps",
                b"-d.!",
                b"-l",
                b"4",
                b"-t2",
                b"-w",
                b"20",
                b"file",
            ]);
            let program = ProgramName::from_argv0(&invocation.args[0]);
            let parsed = parse_arguments(&invocation, &program).unwrap();
            assert!(parsed.options.center_p);
            assert!(parsed.options.grok_mail_headers);
            assert!(parsed.options.format_troff);
            assert!(parsed.options.allow_indented_paragraphs);
            assert!(parsed.options.coalesce_spaces_p);
            assert_eq!(parsed.options.sentence_enders, b".!");
            assert_eq!(parsed.options.output_tab_width, 4);
            assert_eq!(parsed.options.tab_width, 2);
            assert_eq!(
                (parsed.options.goal_length, parsed.options.max_length),
                (20, 20)
            );
            assert_eq!(parsed.operands, [OsString::from("file")]);
        }

        #[test]
        fn parses_base_zero_positionals_and_numeric_shorthand() {
            let positional = invocation(&[b"fmt", b"0x10", b"020", b"file"]);
            let program = ProgramName::from_argv0(&positional.args[0]);
            let parsed = parse_arguments(&positional, &program).unwrap();
            assert_eq!(
                (parsed.options.goal_length, parsed.options.max_length),
                (16, 16)
            );
            assert_eq!(parsed.operands, [OsString::from("file")]);

            let shorthand = invocation(&[b"fmt", b"-72"]);
            let program = ProgramName::from_argv0(&shorthand.args[0]);
            let parsed = parse_arguments(&shorthand, &program).unwrap();
            assert_eq!(
                (parsed.options.goal_length, parsed.options.max_length),
                (72, 72)
            );
        }

        #[test]
        fn permutation_and_posix_stop_match_getopt_modes() {
            let normal = invocation(&[b"fmt", b"10", b"-s", b"file"]);
            let program = ProgramName::from_argv0(&normal.args[0]);
            let parsed = parse_arguments(&normal, &program).unwrap();
            assert!(parsed.options.coalesce_spaces_p);
            assert_eq!(parsed.options.goal_length, 10);
            assert_eq!(parsed.operands, [OsString::from("file")]);

            let mut posix = invocation(&[b"fmt", b"10", b"-s"]);
            posix.posixly_correct = true;
            let program = ProgramName::from_argv0(&posix.args[0]);
            let parsed = parse_arguments(&posix, &program).unwrap();
            assert!(!parsed.options.coalesce_spaces_p);
            assert_eq!(parsed.options.goal_length, 10);
            assert_eq!(parsed.operands, [OsString::from("-s")]);
        }

        #[test]
        fn reports_value_and_option_errors() {
            assert!(matches!(
                get_positive(b"abc", b"bad", false),
                Ok(PositiveValue::NotNumeric)
            ));
            assert!(matches!(
                get_positive(b"0", b"bad", false),
                Err(Diagnostic::Application(_))
            ));
            assert_eq!(
                get_positive(b"999999999999999999999999", b"bad", true).unwrap(),
                PositiveValue::Value(i64::MAX as usize)
            );

            let (status, _, stderr) = run_case(&[b"/tmp/alias", b"-z"], b"");
            assert_eq!(status, 1);
            assert!(stderr.starts_with(b"/tmp/alias: invalid option -- 'z'\nusage: alias "));
        }
    }

    mod line_reader {
        use super::*;

        #[test]
        fn distinguishes_blank_final_and_empty_input() {
            let mut input = Cursor::new(b"\nlast".to_vec());
            let mut reader = LineReader::new(&mut input);
            assert_eq!(reader.get_line(false).unwrap(), Some(&b""[..]));
            assert_eq!(reader.get_line(false).unwrap(), Some(&b"last"[..]));
            assert_eq!(reader.get_line(false).unwrap(), None);
        }

        #[test]
        fn filters_controls_backspaces_and_trailing_space() {
            let mut input = Cursor::new(b"ab\x08c\x01\tword \t\n".to_vec());
            let mut reader = LineReader::new(&mut input);
            assert_eq!(reader.get_line(false).unwrap(), Some(&b"ac\tword"[..]));
        }

        #[test]
        fn preserves_troff_bytes_and_grows_for_long_lines() {
            let mut bytes = b".a\x01\x08\0b\n".to_vec();
            bytes.extend(std::iter::repeat_n(b'x', 20_000));
            let mut input = Cursor::new(bytes);
            let mut reader = LineReader::new(&mut input);
            assert_eq!(reader.get_line(false).unwrap(), Some(&b".a\x01\x08\0b"[..]));
            assert_eq!(reader.get_line(false).unwrap().unwrap().len(), 20_000);
        }

        #[test]
        fn returns_partial_line_before_read_error() {
            let mut input = ScriptedReader {
                bytes: Cursor::new(b"abcdef".to_vec()),
                fail_after: Some(3),
                error_kind: io::ErrorKind::Other,
            };
            let mut reader = LineReader::new(&mut input);
            assert_eq!(reader.get_line(false).unwrap(), Some(&b"abc"[..]));
            assert!(matches!(
                reader.get_line(false),
                Err(StreamFailure::Read(_))
            ));
        }
    }

    mod character_semantics {
        use super::*;

        #[test]
        fn decodes_c_and_utf8_units_with_display_widths() {
            let c = RealCharacterSemantics::new(LocaleMode::C);
            assert_eq!(c.decode("α".as_bytes()).value, DecodedValue::Invalid);

            let utf8 = RealCharacterSemantics::new(LocaleMode::Utf8);
            let greek = utf8.decode("α".as_bytes());
            assert_eq!(greek.value, DecodedValue::Scalar('α'));
            assert_eq!((greek.consumed, greek.display_width), (2, 1));
            assert_eq!(utf8.decode("界".as_bytes()).display_width, 2);
            assert_eq!(utf8.decode("\u{0301}".as_bytes()).display_width, 0);
            assert_eq!(utf8.decode(&[0xe6]).value, DecodedValue::Invalid);
        }

        #[test]
        fn classifies_wide_space_and_selects_locale_precedence() {
            let utf8 = RealCharacterSemantics::new(LocaleMode::Utf8);
            let nbsp = utf8.decode("\u{00a0}".as_bytes());
            assert!(nbsp.is_blank);
            assert!(nbsp.is_space);

            let environment = LocaleEnvironment {
                lc_all: Some(OsString::from("C")),
                lc_ctype: Some(OsString::from("C.UTF-8")),
                lang: None,
            };
            assert_eq!(select_locale_mode(&environment), LocaleMode::C);
            let environment = LocaleEnvironment {
                lc_all: None,
                lc_ctype: Some(OsString::from("C.utf8")),
                lang: None,
            };
            assert_eq!(select_locale_mode(&environment), LocaleMode::Utf8);
        }

        #[test]
        fn deterministic_mock_is_used_through_the_seam() {
            let mock = MockCharacterSemantics::default();
            mock.decoded_units.borrow_mut().push_back(DecodedUnit {
                consumed: 1,
                value: DecodedValue::Scalar('x'),
                display_width: 7,
                is_blank: false,
                is_space: false,
            });
            assert_eq!(mock.decode(b"x").display_width, 7);
        }
    }

    mod pure_helpers {
        use super::*;

        #[test]
        fn measures_ascii_and_tab_indentation() {
            assert_eq!(indent_length(b" \t x", 4), 5);
            assert_eq!(indent_length(b"\t\tword", 4), 8);
            assert_eq!(indent_length(b"word", 8), 0);
        }

        #[test]
        fn conservatively_recognizes_mail_headers() {
            assert!(might_be_header(b"Subject: value"));
            assert!(might_be_header(b"X-1:\tvalue"));
            assert!(!might_be_header(b"Subject:"));
            assert!(!might_be_header(b"subject: value"));
            assert!(!might_be_header(b"Subject : value"));
        }

        #[test]
        fn emits_grouped_output_indentation() {
            let mut options = Options::default();
            options.output_tab_width = 4;
            let state = RunState::new(options);
            let mut bytes = Vec::new();
            let mut output = OutputWriter::new(&mut bytes);
            state.output_indent(10, &mut output);
            assert_eq!(bytes, b"\t\t  ");
        }
    }

    mod wrapping {
        use super::*;

        #[test]
        fn wraps_at_goal_word_boundary() {
            let (status, stdout, stderr) = run_case(&[b"fmt", b"-w", b"11"], b"Hello world test\n");
            assert_eq!(status, 0);
            assert_eq!(stdout, b"Hello world\ntest\n");
            assert!(stderr.is_empty());
        }

        #[test]
        fn expands_physical_tabs_and_coalesces_sentence_space() {
            let (_, stdout, _) = run_case(&[b"fmt", b"-t", b"4", b"-w", b"20"], b"a\tb\tc\n");
            assert_eq!(stdout, b"a   b   c\n");

            let (_, stdout, _) = run_case(&[b"fmt", b"-s"], b"One.      Two\n");
            assert_eq!(stdout, b"One.  Two\n");
        }

        #[test]
        fn handles_overlong_words_and_output_tabs() {
            let (_, stdout, _) = run_case(&[b"fmt", b"-w5"], b"extraordinary word\n");
            assert_eq!(stdout, b"extraordinary\nword\n");

            let (_, stdout, _) = run_case(&[b"fmt", b"-l4"], b"        text\n");
            assert_eq!(stdout, b"\t\ttext\n");
        }
    }

    mod paragraph_state {
        use super::*;

        #[test]
        fn preserves_dot_requests_unless_troff_formatting_is_enabled() {
            let (_, stdout, _) = run_case(&[b"fmt", b"-w10"], b".Not troff\nRegular text\n");
            assert_eq!(stdout, b".Not troff\nRegular\ntext\n");

            let (_, stdout, _) = run_case(&[b"fmt", b"-n", b"-w10"], b".TH MANUAL\nRegular text\n");
            assert_eq!(stdout, b".TH MANUAL\nRegular\ntext\n");
        }

        #[test]
        fn transitions_from_mail_header_to_body() {
            let (_, stdout, _) =
                run_case(&[b"fmt", b"-m"], b"Subject: Test\nNot a header\n\nBody\n");
            assert_eq!(stdout, b"Subject: Test\nNot a header\n\nBody\n");
        }

        #[test]
        fn permits_only_the_second_indentation_change_with_p() {
            let (_, stdout, _) = run_case(&[b"fmt", b"-p"], b"first\n  second\n  third\n");
            assert_eq!(stdout, b"first second\n  third\n");
        }
    }

    mod centering {
        use super::*;

        #[test]
        fn centers_odd_width_and_blank_lines() {
            let (_, stdout, _) = run_case(&[b"fmt", b"-c", b"-w21"], b"Hello\n");
            assert_eq!(stdout, b"        Hello\n");

            let (_, stdout, _) = run_case(&[b"fmt", b"-c", b"-w5"], b"\n");
            assert_eq!(stdout, b"   \n");
        }

        #[test]
        fn center_replaces_tabs_and_invalid_input() {
            let (_, stdout, _) = run_case(&[b"fmt", b"-c", b"-t4", b"-w20"], b"Hello\tWorld\n");
            assert_eq!(stdout, b"     Hello World\n");

            let (_, stdout, _) = run_case(&[b"fmt", b"-c", b"-w6"], b"z\xe6\n");
            assert_eq!(stdout, b"  z?\n");
        }

        #[test]
        fn center_trims_leading_wide_whitespace() {
            let (_, stdout, _) = run_case(&[b"fmt", b"-c", b"-w5"], b"  x\n");
            assert_eq!(stdout, b"  x\n");
        }
    }

    mod coordinator_boundaries {
        use super::*;

        #[test]
        fn processes_named_files_in_order() {
            let invocation = invocation(&[b"/bin/fmt", b"one", b"two"]);
            let mut files = MockFileSystem::default();
            files.add(b"one", MockFile::Bytes(b"first\n".to_vec()));
            files.add(b"two", MockFile::Bytes(b"second\n".to_vec()));
            let mut stdin = Cursor::new(Vec::new());
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let characters = RealCharacterSemantics::new(LocaleMode::Utf8);
            let status = run(
                &invocation,
                &mut stdin,
                &mut stdout,
                &mut stderr,
                &mut files,
                &characters,
            );
            assert_eq!(status, 0);
            assert_eq!(stdout, b"first\nsecond\n");
            assert!(stderr.is_empty());
        }

        #[test]
        fn reports_open_and_partial_read_failures_and_continues() {
            let invocation = invocation(&[b"/tmp/alias", b"missing", b"partial", b"ok"]);
            let mut files = MockFileSystem::default();
            files.add(
                b"missing",
                MockFile::OpenError(io::ErrorKind::PermissionDenied),
            );
            files.add(
                b"partial",
                MockFile::Scripted(ScriptedReader {
                    bytes: Cursor::new(b"partly".to_vec()),
                    fail_after: Some(4),
                    error_kind: io::ErrorKind::Other,
                }),
            );
            files.add(b"ok", MockFile::Bytes(b"done\n".to_vec()));
            let mut stdin = Cursor::new(Vec::new());
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let characters = RealCharacterSemantics::new(LocaleMode::Utf8);
            let status = run(
                &invocation,
                &mut stdin,
                &mut stdout,
                &mut stderr,
                &mut files,
                &characters,
            );
            assert_eq!(status, 2);
            assert_eq!(stdout, b"part\ndone\n");
            assert!(stderr.starts_with(b"alias: missing: "));
            assert!(stderr.windows(16).any(|part| part == b"alias: partial: "));
        }

        #[test]
        fn caps_failed_file_status_at_127() {
            let mut arguments = vec![b"fmt".as_slice()];
            arguments.extend(std::iter::repeat_n(b"x".as_slice(), 130));
            let invocation = invocation(&arguments);
            let mut files = MockFileSystem::default();
            for _ in 0..130 {
                files.add(b"x", MockFile::OpenError(io::ErrorKind::NotFound));
            }
            let mut stdin = Cursor::new(Vec::new());
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let characters = RealCharacterSemantics::new(LocaleMode::C);
            let status = run(
                &invocation,
                &mut stdin,
                &mut stdout,
                &mut stderr,
                &mut files,
                &characters,
            );
            assert_eq!(status, 127);
            assert_eq!(
                stderr
                    .split(|byte| *byte == b'\n')
                    .filter(|line| !line.is_empty())
                    .count(),
                130
            );
        }
    }

    mod output_failures {
        use super::*;

        #[test]
        fn retains_first_write_failure_without_panicking() {
            let mut writer = FailingWriter {
                fail_after: 3,
                accepted: Vec::new(),
                fail_flush: false,
            };
            {
                let mut output = OutputWriter::new(&mut writer);
                output.write_all_compat(b"abcdef");
                assert!(output.has_failed());
                output.write_all_compat(b"ignored");
            }
            assert_eq!(writer.accepted, b"abc");
        }

        #[test]
        fn retains_flush_failure() {
            let mut writer = FailingWriter {
                fail_after: usize::MAX,
                accepted: Vec::new(),
                fail_flush: true,
            };
            let mut output = OutputWriter::new(&mut writer);
            output.flush_compat();
            assert!(output.has_failed());
        }
    }
}
