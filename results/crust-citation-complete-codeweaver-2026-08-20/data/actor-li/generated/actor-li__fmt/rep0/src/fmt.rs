use crate::locale::{decode_next, is_wide_blank, is_wide_space, DecodedUnit, LocaleMode};
use crate::runtime::{os_error_text, os_str_bytes, program_names, FileSource, ProcessContext};
use std::ffi::{OsStr, OsString};
use std::io::{self, BufRead, BufReader, Read, Write};

const DEFAULT_GOAL_LENGTH: usize = 65;
const DEFAULT_MAXIMUM_DELTA: usize = 10;
const MAX_ERRORS: u8 = 127;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct Config {
    pub(crate) center_p: bool,
    pub(crate) goal_length: usize,
    pub(crate) max_length: usize,
    pub(crate) coalesce_spaces_p: bool,
    pub(crate) allow_indented_paragraphs: bool,
    pub(crate) tab_width: usize,
    pub(crate) output_tab_width: usize,
    pub(crate) sentence_enders: Vec<u8>,
    pub(crate) grok_mail_headers: bool,
    pub(crate) format_troff: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum HdrType {
    ParagraphStart,
    NonHeader,
    Header,
    Continuation,
}

impl HdrType {
    fn classify(grok_mail_headers: bool, previous: Self, indent: usize, line: &[u8]) -> Self {
        if !grok_mail_headers || previous == Self::NonHeader {
            return Self::NonHeader;
        }
        if indent == 0 && might_be_header(line) {
            Self::Header
        } else if indent > 0 && previous.is_mail_line() {
            Self::Continuation
        } else {
            Self::NonHeader
        }
    }

    fn is_mail_line(self) -> bool {
        matches!(self, Self::Header | Self::Continuation)
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct OutputState {
    x: usize,
    x0: usize,
    pending_spaces: usize,
    output_in_paragraph: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum PositiveParse {
    Value(usize),
    NotNumber,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DiagnosticPrefix {
    RawArgv0,
    Progname,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct CliError {
    message: Vec<u8>,
    prefix: DiagnosticPrefix,
    show_usage: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ResolvedArgs {
    config: Config,
    operands: Vec<OsString>,
}

struct LineReader<R: BufRead> {
    reader: R,
    format_troff: bool,
    sticky_error: Option<io::Error>,
}

impl<R: BufRead> LineReader<R> {
    fn new(reader: R, format_troff: bool) -> Self {
        Self {
            reader,
            format_troff,
            sticky_error: None,
        }
    }

    fn get_line(&mut self) -> Option<Vec<u8>> {
        if self.sticky_error.is_some() {
            return None;
        }

        let mut physical = Vec::new();
        let mut terminated = false;
        loop {
            match self.reader.fill_buf() {
                Ok([]) => break,
                Ok(buffer) => {
                    if let Some(index) = buffer.iter().position(|byte| *byte == b'\n') {
                        physical.extend_from_slice(&buffer[..index]);
                        self.reader.consume(index + 1);
                        terminated = true;
                        break;
                    }
                    let count = buffer.len();
                    physical.extend_from_slice(buffer);
                    self.reader.consume(count);
                }
                Err(error) => {
                    self.sticky_error = Some(error);
                    break;
                }
            }
        }

        let mut line = Vec::with_capacity(physical.len());
        let mut troff = false;
        for byte in physical {
            if line.is_empty() && byte == b'.' && !self.format_troff {
                troff = true;
            }
            if troff || byte == b'\t' || !byte.is_ascii_control() {
                line.push(byte);
            } else if byte == b'\x08' {
                line.pop();
            }
        }
        while line.last().is_some_and(|byte| is_byte_space(*byte)) {
            line.pop();
        }

        (terminated || !line.is_empty()).then_some(line)
    }

    fn take_error(&mut self) -> Option<io::Error> {
        self.sticky_error.take()
    }
}

struct Formatter<'a> {
    config: Config,
    locale_mode: LocaleMode,
    output: &'a mut dyn Write,
    state: OutputState,
}

impl<'a> Formatter<'a> {
    fn new(config: Config, locale_mode: LocaleMode, output: &'a mut dyn Write) -> Self {
        Self {
            config,
            locale_mode,
            output,
            state: OutputState::default(),
        }
    }

    fn process_stream(
        &mut self,
        stream: &mut dyn Read,
        name: &[u8],
    ) -> io::Result<Option<io::Error>> {
        if self.config.center_p {
            return self.center_stream(stream, name);
        }

        let reader = BufReader::new(stream);
        let mut lines = LineReader::new(reader, self.config.format_troff);
        let mut last_indent = None;
        let mut para_line_number = 0usize;
        let mut first_indent = 0usize;
        let mut current_last_indent = 0usize;
        let mut prev_header_type = HdrType::ParagraphStart;

        while let Some(stored_line) = lines.get_line() {
            let line = effective_line(&stored_line);
            let indent = indent_length(line, self.config.tab_width);
            let header_type = HdrType::classify(
                self.config.grok_mail_headers,
                prev_header_type,
                indent,
                line,
            );

            let raw_troff = line.first() == Some(&b'.') && !self.config.format_troff;
            let indentation_changed = last_indent != Some(indent);
            let needs_paragraph = line.is_empty()
                || raw_troff
                || header_type == HdrType::Header
                || (header_type == HdrType::NonHeader && prev_header_type.is_mail_line())
                || (indentation_changed
                    && header_type != HdrType::Continuation
                    && (!self.config.allow_indented_paragraphs || para_line_number != 1));

            if needs_paragraph {
                self.new_paragraph(indent)?;
                para_line_number = 0;
                first_indent = indent;
                current_last_indent = indent;
                last_indent = Some(indent);

                if raw_troff {
                    self.output.write_all(line)?;
                    self.output.write_all(b"\n")?;
                    continue;
                }
                if header_type == HdrType::Header {
                    current_last_indent = 2;
                    last_indent = Some(2);
                }
                if line.is_empty() {
                    self.output.write_all(b"\n")?;
                    prev_header_type = HdrType::ParagraphStart;
                    continue;
                } else if indent != current_last_indent && header_type != HdrType::Continuation {
                    current_last_indent = indent;
                    last_indent = Some(indent);
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
                    let unit = decoded_word_unit(&line[cursor..], self.locale_mode)
                        .expect("nonempty input has a decoded unit");
                    let unit_width = if unit.scalar == Some('\t') {
                        self.config.tab_width - line_width % self.config.tab_width
                    } else {
                        unit.display_width
                    };

                    if is_wide_blank(unit) {
                        if word_length == 0 {
                            word_start += unit.byte_len;
                            cursor += unit.byte_len;
                            continue;
                        }
                        space_width = space_width.saturating_add(unit_width);
                    } else {
                        if space_width > 0 {
                            break;
                        }
                        word_length = word_length.saturating_add(unit.byte_len);
                        word_width = word_width.saturating_add(unit_width);
                    }
                    line_width = line_width.saturating_add(unit_width);
                    cursor += unit.byte_len;
                }

                if word_length == 0 {
                    // The C loop still dispatches an empty word after skipping
                    // a nonempty line made entirely of wide blank characters.
                    self.output_word(
                        first_indent,
                        current_last_indent,
                        &line[word_start..word_start],
                        0,
                        space_width,
                        line.last().copied(),
                    )?;
                    break;
                }
                let word_end = word_start + word_length;
                self.output_word(
                    first_indent,
                    current_last_indent,
                    &line[word_start..word_end],
                    word_width,
                    space_width,
                    None,
                )?;
                word_start = cursor;
            }
            para_line_number = para_line_number.saturating_add(1);
        }

        self.new_paragraph(0)?;
        Ok(lines.take_error())
    }

    fn new_paragraph(&mut self, indent: usize) -> io::Result<()> {
        if self.state.x0 > 0 {
            self.output.write_all(b"\n")?;
        }
        self.state.x = indent;
        self.state.x0 = 0;
        self.state.pending_spaces = 0;
        self.state.output_in_paragraph = false;
        Ok(())
    }

    fn output_indent(&mut self, mut n_spaces: usize) -> io::Result<()> {
        if self.config.output_tab_width > 0 {
            while n_spaces >= self.config.output_tab_width {
                self.output.write_all(b"\t")?;
                n_spaces -= self.config.output_tab_width;
            }
        }
        write_spaces(self.output, n_spaces)
    }

    fn output_word(
        &mut self,
        indent0: usize,
        indent1: usize,
        word: &[u8],
        width: usize,
        measured_spaces: usize,
        empty_word_predecessor: Option<u8>,
    ) -> io::Result<()> {
        let new_x = self
            .state
            .x
            .saturating_add(self.state.pending_spaces)
            .saturating_add(width);
        let sentence_byte = word.last().copied().or(empty_word_predecessor);
        let pending_spaces = if !self.config.coalesce_spaces_p && measured_spaces > 0 {
            measured_spaces
        } else if sentence_byte.is_some_and(|byte| self.config.sentence_enders.contains(&byte)) {
            2
        } else {
            1
        };

        if self.state.x0 == 0 {
            self.output_indent(if self.state.output_in_paragraph {
                indent1
            } else {
                indent0
            })?;
        } else if new_x > self.config.max_length
            || self.state.x >= self.config.goal_length
            || (new_x > self.config.goal_length
                && new_x - self.config.goal_length > self.config.goal_length - self.state.x)
        {
            self.output.write_all(b"\n")?;
            self.output_indent(indent1)?;
            self.state.x0 = 0;
            self.state.x = indent1;
        } else {
            write_spaces(self.output, self.state.pending_spaces)?;
            self.state.x0 = self.state.x0.saturating_add(self.state.pending_spaces);
            self.state.x = self.state.x.saturating_add(self.state.pending_spaces);
        }

        self.state.x0 = self.state.x0.saturating_add(width);
        self.state.x = self.state.x.saturating_add(width);
        self.output.write_all(word)?;
        self.state.pending_spaces = pending_spaces;
        self.state.output_in_paragraph = true;
        Ok(())
    }

    fn center_stream(
        &mut self,
        stream: &mut dyn Read,
        _name: &[u8],
    ) -> io::Result<Option<io::Error>> {
        let reader = BufReader::new(stream);
        let mut lines = LineReader::new(reader, self.config.format_troff);
        // center_stream leaves wc unchanged after mbtowc fails, so its prior
        // value still controls leading-space classification for that byte.
        let mut previous_scalar = None;
        while let Some(stored_line) = lines.get_line() {
            let mut line = effective_line(&stored_line).to_vec();
            for byte in &mut line {
                if *byte == b'\t' {
                    *byte = b' ';
                }
            }

            let mut width = 0usize;
            let mut output_start = 0usize;
            let mut cursor = 0usize;
            while cursor < line.len() {
                let unit = decode_next(&line[cursor..], self.locale_mode)
                    .expect("nonempty input has a decoded unit");
                let classification_scalar = unit.scalar.or(previous_scalar);
                let measured = if unit.scalar.is_none() {
                    line[cursor] = b'?';
                    DecodedUnit {
                        scalar: Some('?'),
                        byte_len: 1,
                        display_width: 1,
                    }
                } else {
                    previous_scalar = unit.scalar;
                    unit
                };
                let classification = DecodedUnit {
                    scalar: classification_scalar,
                    byte_len: measured.byte_len,
                    display_width: measured.display_width,
                };
                if width == 0 && is_wide_space(classification) {
                    output_start += measured.byte_len;
                } else {
                    width = width.saturating_add(measured.display_width);
                }
                cursor += measured.byte_len;
            }

            let shortfall = self.config.goal_length.saturating_sub(width);
            let padding = shortfall / 2 + shortfall % 2;
            write_spaces(self.output, padding)?;
            self.output
                .write_all(&line[output_start.min(line.len())..])?;
            self.output.write_all(b"\n")?;
        }
        Ok(lines.take_error())
    }
}

struct Application<'a> {
    formatter: Formatter<'a>,
    stderr: &'a mut dyn Write,
    file_source: &'a dyn FileSource,
    progname: Vec<u8>,
    n_errors: u8,
}

impl<'a> Application<'a> {
    fn new(
        formatter: Formatter<'a>,
        stderr: &'a mut dyn Write,
        file_source: &'a dyn FileSource,
        progname: Vec<u8>,
    ) -> Self {
        Self {
            formatter,
            stderr,
            file_source,
            progname,
            n_errors: 0,
        }
    }

    fn process_named_file(&mut self, name: &OsStr) -> io::Result<()> {
        match self.file_source.open(name) {
            Ok(mut stream) => {
                let display_name = os_str_bytes(name);
                self.process_stream(&mut *stream, &display_name)
            }
            Err(error) => {
                self.warn(os_str_bytes(name).as_ref(), &error)?;
                self.increment_errors();
                Ok(())
            }
        }
    }

    fn process_stream(&mut self, stream: &mut dyn Read, name: &[u8]) -> io::Result<()> {
        if let Some(error) = self.formatter.process_stream(stream, name)? {
            self.warn(name, &error)?;
            self.increment_errors();
        }
        Ok(())
    }

    fn increment_errors(&mut self) {
        self.n_errors = self.n_errors.saturating_add(1).min(MAX_ERRORS);
    }

    fn warn(&mut self, name: &[u8], error: &io::Error) -> io::Result<()> {
        self.stderr.write_all(&self.progname)?;
        self.stderr.write_all(b": ")?;
        self.stderr.write_all(name)?;
        self.stderr.write_all(b": ")?;
        self.stderr.write_all(&os_error_text(error))?;
        self.stderr.write_all(b"\n")
    }
}

fn get_positive(
    input: &[u8],
    error_message: &'static [u8],
    fussy_p: bool,
) -> Result<PositiveParse, CliError> {
    let fatal = || CliError {
        message: error_message.to_vec(),
        prefix: DiagnosticPrefix::Progname,
        show_usage: false,
    };

    let mut index = 0usize;
    while input.get(index).is_some_and(|byte| is_byte_space(*byte)) {
        index += 1;
    }
    let negative = match input.get(index) {
        Some(b'+') => {
            index += 1;
            false
        }
        Some(b'-') => {
            index += 1;
            true
        }
        _ => false,
    };

    let digit_start = index;
    let (base, prefix_len) = if input.get(index) == Some(&b'0') {
        if matches!(input.get(index + 1), Some(b'x' | b'X'))
            && input
                .get(index + 2)
                .is_some_and(|byte| byte.is_ascii_hexdigit())
        {
            (16u32, 2usize)
        } else {
            (8u32, 0usize)
        }
    } else {
        (10u32, 0usize)
    };
    index += prefix_len;
    let value_start = index;
    let mut value = 0u64;
    let mut overflow = false;
    while let Some(byte) = input.get(index) {
        let digit = match byte {
            b'0'..=b'9' => u32::from(*byte - b'0'),
            b'a'..=b'f' => u32::from(*byte - b'a') + 10,
            b'A'..=b'F' => u32::from(*byte - b'A') + 10,
            _ => break,
        };
        if digit >= base {
            break;
        }
        match value
            .checked_mul(u64::from(base))
            .and_then(|current| current.checked_add(u64::from(digit)))
        {
            Some(current) if current <= i64::MAX as u64 => value = current,
            _ => {
                value = i64::MAX as u64;
                overflow = true;
            }
        }
        index += 1;
    }

    let converted = index > value_start || (base == 8 && input.get(digit_start) == Some(&b'0'));
    if !converted {
        if fussy_p || input.is_empty() {
            return Err(fatal());
        }
        return Ok(PositiveParse::NotNumber);
    }
    if index != input.len() {
        if fussy_p {
            return Err(fatal());
        }
        return Ok(PositiveParse::NotNumber);
    }
    if negative || (!overflow && value == 0) {
        return Err(fatal());
    }
    Ok(PositiveParse::Value(value as usize))
}

fn resolve_arguments(context: &ProcessContext) -> Result<ResolvedArgs, CliError> {
    let mut config = Config {
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
    };
    let mut operands = Vec::new();
    let args = context.argv.get(1..).unwrap_or_default();
    let mut argument_index = 0usize;

    while argument_index < args.len() {
        let bytes = os_str_bytes(&args[argument_index]);
        if bytes.as_ref() == b"--" {
            operands.extend(args[argument_index + 1..].iter().cloned());
            break;
        }
        if bytes.len() <= 1 || bytes[0] != b'-' {
            if context.posixly_correct {
                operands.extend(args[argument_index..].iter().cloned());
                break;
            }
            operands.push(args[argument_index].clone());
            argument_index += 1;
            continue;
        }

        let mut option_index = 1usize;
        while option_index < bytes.len() {
            let option = bytes[option_index];
            match option {
                b'c' => config.center_p = true,
                b'm' => config.grok_mail_headers = true,
                b'n' => config.format_troff = true,
                b'p' => config.allow_indented_paragraphs = true,
                b's' => config.coalesce_spaces_p = true,
                b'h' => {
                    return Err(CliError {
                        message: Vec::new(),
                        prefix: DiagnosticPrefix::Progname,
                        show_usage: true,
                    });
                }
                b'd' | b'l' | b't' | b'w' => {
                    let value = if option_index + 1 < bytes.len() {
                        let attached = bytes[option_index + 1..].to_vec();
                        option_index = bytes.len();
                        attached
                    } else if argument_index + 1 < args.len() {
                        argument_index += 1;
                        option_index = bytes.len();
                        os_str_bytes(&args[argument_index]).into_owned()
                    } else {
                        return Err(option_error(b"option requires an argument -- '", option));
                    };
                    match option {
                        b'd' => config.sentence_enders = value,
                        b'l' => {
                            config.output_tab_width =
                                positive_value(&value, b"output tab width must be positive")?
                        }
                        b't' => {
                            config.tab_width =
                                positive_value(&value, b"tab width must be positive")?
                        }
                        b'w' => {
                            let width = positive_value(&value, b"width must be positive")?;
                            config.goal_length = width;
                            config.max_length = width;
                        }
                        _ => unreachable!(),
                    }
                    continue;
                }
                b'0'..=b'9' => {
                    if config.goal_length == 0 {
                        let value = if bytes.len() == 2 {
                            &bytes[1..]
                        } else if option_index + 1 < bytes.len() {
                            &bytes[1..]
                        } else {
                            return Err(CliError {
                                message: b"width must be nonzero".to_vec(),
                                prefix: DiagnosticPrefix::Progname,
                                show_usage: false,
                            });
                        };
                        let width = positive_value(value, b"width must be nonzero")?;
                        config.goal_length = width;
                        config.max_length = width;
                    }
                }
                _ => {
                    return Err(option_error(b"invalid option -- '", option));
                }
            }
            option_index += 1;
        }
        argument_index += 1;
    }

    if config.goal_length == 0 && !operands.is_empty() {
        match get_positive(
            &os_str_bytes(&operands[0]),
            b"goal length must be positive",
            false,
        )? {
            PositiveParse::Value(value) => {
                config.goal_length = value;
                operands.remove(0);
                if !operands.is_empty() {
                    match get_positive(
                        &os_str_bytes(&operands[0]),
                        b"max length must be positive",
                        false,
                    )? {
                        PositiveParse::Value(value) => {
                            config.max_length = value;
                            operands.remove(0);
                            if config.max_length < config.goal_length {
                                return Err(CliError {
                                    message: b"max length must be >= goal length".to_vec(),
                                    prefix: DiagnosticPrefix::Progname,
                                    show_usage: false,
                                });
                            }
                        }
                        PositiveParse::NotNumber => {}
                    }
                }
            }
            PositiveParse::NotNumber => {}
        }
    }
    if config.goal_length == 0 {
        config.goal_length = DEFAULT_GOAL_LENGTH;
    }
    if config.max_length == 0 {
        config.max_length = config.goal_length.saturating_add(DEFAULT_MAXIMUM_DELTA);
    }

    Ok(ResolvedArgs { config, operands })
}

fn indent_length(line: &[u8], tab_width: usize) -> usize {
    let mut width = 0usize;
    for byte in line {
        match byte {
            b' ' => width = width.saturating_add(1),
            b'\t' => width = width.saturating_add(tab_width - width % tab_width),
            _ => break,
        }
    }
    width
}

fn might_be_header(line: &[u8]) -> bool {
    if !line.first().is_some_and(u8::is_ascii_uppercase) {
        return false;
    }
    let mut index = 1usize;
    while line
        .get(index)
        .is_some_and(|byte| byte.is_ascii_alphanumeric() || *byte == b'-')
    {
        index += 1;
    }
    line.get(index) == Some(&b':') && line.get(index + 1).is_some_and(|byte| is_byte_space(*byte))
}

fn usage(progname: &[u8], stderr: &mut dyn Write) -> io::Result<()> {
    stderr.write_all(b"usage: ")?;
    stderr.write_all(progname)?;
    stderr.write_all(b" [-cmnps] [-d chars] [-l number] [-t number]\n")?;
    stderr.write_all(b"\t[goal [maximum] | -width | -w width] [file ...]\n")
}

fn decoded_word_unit(bytes: &[u8], mode: LocaleMode) -> Option<DecodedUnit> {
    decode_next(bytes, mode)
}

pub(crate) fn run(
    context: &ProcessContext,
    stdin: &mut dyn Read,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
    file_source: &dyn FileSource,
) -> io::Result<u8> {
    let names = program_names(context);
    let resolved = match resolve_arguments(context) {
        Ok(resolved) => resolved,
        Err(error) => {
            if !error.message.is_empty() {
                let prefix = match error.prefix {
                    DiagnosticPrefix::RawArgv0 => &names.raw_argv0,
                    DiagnosticPrefix::Progname => &names.progname,
                };
                stderr.write_all(prefix)?;
                stderr.write_all(b": ")?;
                stderr.write_all(&error.message)?;
                stderr.write_all(b"\n")?;
            }
            if error.show_usage {
                usage(&names.progname, stderr)?;
            }
            return Ok(1);
        }
    };

    let locale_mode = crate::locale::locale_mode_from_environment(
        context.lc_all.as_deref(),
        context.lc_ctype.as_deref(),
        context.lang.as_deref(),
    );
    let formatter = Formatter::new(resolved.config, locale_mode, stdout);
    let mut application = Application::new(formatter, stderr, file_source, names.progname);
    if resolved.operands.is_empty() {
        application.process_stream(stdin, b"standard input")?;
    } else {
        for operand in resolved.operands {
            application.process_named_file(&operand)?;
        }
    }
    Ok(application.n_errors)
}

fn effective_line(line: &[u8]) -> &[u8] {
    line.iter()
        .position(|byte| *byte == 0)
        .map_or(line, |index| &line[..index])
}

fn is_byte_space(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | b'\x0b' | b'\x0c' | b'\r')
}

fn write_spaces(output: &mut dyn Write, mut count: usize) -> io::Result<()> {
    const SPACES: [u8; 64] = [b' '; 64];
    while count > 0 {
        let chunk = count.min(SPACES.len());
        output.write_all(&SPACES[..chunk])?;
        count -= chunk;
    }
    Ok(())
}

fn positive_value(input: &[u8], message: &'static [u8]) -> Result<usize, CliError> {
    match get_positive(input, message, true)? {
        PositiveParse::Value(value) => Ok(value),
        PositiveParse::NotNumber => unreachable!("strict positive parsing has no probe result"),
    }
}

fn option_error(prefix: &[u8], option: u8) -> CliError {
    let mut message = prefix.to_vec();
    message.push(option);
    message.push(b'\'');
    CliError {
        message,
        prefix: DiagnosticPrefix::RawArgv0,
        show_usage: true,
    }
}

#[cfg(test)]
mod tests {
    #[cfg(unix)]
    mod cli {
        use super::super::*;
        use crate::runtime::MockFileSource;
        use std::ffi::OsString;
        use std::io::Cursor;
        use std::os::unix::ffi::OsStringExt;

        fn context(argv0: &[u8], arguments: &[&[u8]], posixly_correct: bool) -> ProcessContext {
            let mut argv = vec![OsString::from_vec(argv0.to_vec())];
            argv.extend(
                arguments
                    .iter()
                    .map(|argument| OsString::from_vec(argument.to_vec())),
            );
            let mut context = ProcessContext::fixture(argv);
            context.posixly_correct = posixly_correct;
            context
        }

        fn resolve(arguments: &[&[u8]]) -> ResolvedArgs {
            resolve_arguments(&context(b"fmt", arguments, false)).unwrap()
        }

        fn resolve_with_ordering(arguments: &[&[u8]], posixly_correct: bool) -> ResolvedArgs {
            resolve_arguments(&context(b"fmt", arguments, posixly_correct)).unwrap()
        }

        fn execute(
            argv0: &[u8],
            arguments: &[&[u8]],
            posixly_correct: bool,
        ) -> (u8, Vec<u8>, Vec<u8>) {
            let context = context(argv0, arguments, posixly_correct);
            let mut stdin = Cursor::new(Vec::<u8>::new());
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let files = MockFileSource::new();
            let status = run(&context, &mut stdin, &mut stdout, &mut stderr, &files).unwrap();
            (status, stdout, stderr)
        }

        fn assert_failure(argv0: &[u8], arguments: &[&[u8]], expected_stderr: &[u8]) {
            let (status, stdout, stderr) = execute(argv0, arguments, false);
            assert_eq!(status, 1);
            assert!(stdout.is_empty());
            assert_eq!(stderr, expected_stderr);
        }

        fn usage_bytes(progname: &[u8]) -> Vec<u8> {
            let mut bytes = b"usage: ".to_vec();
            bytes.extend_from_slice(progname);
            bytes.extend_from_slice(b" [-cmnps] [-d chars] [-l number] [-t number]\n");
            bytes.extend_from_slice(b"\t[goal [maximum] | -width | -w width] [file ...]\n");
            bytes
        }

        fn operand_bytes(resolved: &ResolvedArgs) -> Vec<Vec<u8>> {
            resolved
                .operands
                .iter()
                .map(|operand| os_str_bytes(operand).into_owned())
                .collect()
        }

        #[test]
        fn defaults_are_goal_65_and_maximum_75() {
            let resolved = resolve(&[]);

            assert_eq!(resolved.config.goal_length, 65);
            assert_eq!(resolved.config.max_length, 75);
            assert_eq!(resolved.config.tab_width, 8);
            assert_eq!(resolved.config.output_tab_width, 0);
            assert_eq!(resolved.config.sentence_enders, b".?!");
            assert!(!resolved.config.center_p);
            assert!(!resolved.config.coalesce_spaces_p);
            assert!(!resolved.config.allow_indented_paragraphs);
            assert!(!resolved.config.grok_mail_headers);
            assert!(!resolved.config.format_troff);
            assert!(resolved.operands.is_empty());
        }

        #[test]
        fn option_c_enables_centering() {
            assert!(resolve(&[b"-c"]).config.center_p);
        }

        #[test]
        fn option_d_replaces_sentence_enders_and_accepts_empty() {
            assert!(resolve(&[b"-d", b""]).config.sentence_enders.is_empty());
            assert_eq!(
                resolve(&[b"-d", b"\xff!?"]).config.sentence_enders,
                b"\xff!?"
            );
        }

        #[test]
        fn option_l_requires_a_positive_width() {
            assert_eq!(resolve(&[b"-l", b"4"]).config.output_tab_width, 4);
            assert_failure(
                b"dir/fmt",
                &[b"-l", b"0"],
                b"fmt: output tab width must be positive\n",
            );
        }

        #[test]
        fn option_m_enables_mail_headers() {
            assert!(resolve(&[b"-m"]).config.grok_mail_headers);
        }

        #[test]
        fn option_n_enables_troff_formatting() {
            assert!(resolve(&[b"-n"]).config.format_troff);
        }

        #[test]
        fn option_p_enables_indented_paragraphs() {
            assert!(resolve(&[b"-p"]).config.allow_indented_paragraphs);
        }

        #[test]
        fn option_s_coalesces_spaces() {
            assert!(resolve(&[b"-s"]).config.coalesce_spaces_p);
        }

        #[test]
        fn option_t_requires_a_positive_width() {
            assert_eq!(resolve(&[b"-t", b"4"]).config.tab_width, 4);
            assert_failure(
                b"dir/fmt",
                &[b"-t", b"-4"],
                b"fmt: tab width must be positive\n",
            );
        }

        #[test]
        fn option_w_sets_goal_and_maximum() {
            let resolved = resolve(&[b"-w", b"42"]);
            assert_eq!(resolved.config.goal_length, 42);
            assert_eq!(resolved.config.max_length, 42);
            assert_failure(
                b"dir/fmt",
                &[b"-w", b"42x"],
                b"fmt: width must be positive\n",
            );
        }

        #[test]
        fn attached_option_values_are_accepted() {
            let resolved = resolve(&[b"-cd!?", b"-l010", b"-t0x10", b"-w+20"]);

            assert!(resolved.config.center_p);
            assert_eq!(resolved.config.sentence_enders, b"!?");
            assert_eq!(resolved.config.output_tab_width, 8);
            assert_eq!(resolved.config.tab_width, 16);
            assert_eq!(resolved.config.goal_length, 20);
            assert_eq!(resolved.config.max_length, 20);
        }

        #[test]
        fn historical_digit_width_is_accepted() {
            let decimal = resolve(&[b"-72"]);
            assert_eq!(decimal.config.goal_length, 72);
            assert_eq!(decimal.config.max_length, 72);

            let octal = resolve(&[b"-010"]);
            assert_eq!(octal.config.goal_length, 8);
            assert_eq!(octal.config.max_length, 8);
        }

        #[test]
        fn base_zero_numbers_accept_decimal_octal_and_hex() {
            for (input, expected) in [
                (&b"10"[..], 10),
                (&b"010"[..], 8),
                (&b"0x10"[..], 16),
                (&b" \t+0X20"[..], 32),
            ] {
                assert_eq!(
                    get_positive(input, b"invalid", true).unwrap(),
                    PositiveParse::Value(expected)
                );
            }

            let positional = resolve(&[b"010", b"0x10"]);
            assert_eq!(positional.config.goal_length, 8);
            assert_eq!(positional.config.max_length, 16);
            assert_failure(b"dir/fmt", &[b"0"], b"fmt: goal length must be positive\n");
            assert_failure(
                b"dir/fmt",
                &[b"10", b"0"],
                b"fmt: max length must be positive\n",
            );
        }

        #[test]
        fn positive_overflow_saturates_at_linux_long_max() {
            let overflow = b"999999999999999999999999999999999999999999";
            let expected = i64::MAX as usize;

            assert_eq!(
                get_positive(overflow, b"invalid", true).unwrap(),
                PositiveParse::Value(expected)
            );
            let resolved = resolve(&[b"-w", overflow]);
            assert_eq!(resolved.config.goal_length, expected);
            assert_eq!(resolved.config.max_length, expected);
        }

        #[test]
        fn partial_positional_number_remains_a_filename() {
            assert_eq!(
                get_positive(b"12x", b"invalid", false).unwrap(),
                PositiveParse::NotNumber
            );

            let first = resolve(&[b"12x", b"80"]);
            assert_eq!(first.config.goal_length, 65);
            assert_eq!(first.config.max_length, 75);
            assert_eq!(operand_bytes(&first), vec![b"12x".to_vec(), b"80".to_vec()]);

            let maximum = resolve(&[b"12", b"13x", b"file"]);
            assert_eq!(maximum.config.goal_length, 12);
            assert_eq!(maximum.config.max_length, 22);
            assert_eq!(
                operand_bytes(&maximum),
                vec![b"13x".to_vec(), b"file".to_vec()]
            );
        }

        #[test]
        fn maximum_less_than_goal_is_fatal() {
            assert_failure(
                b"path/to/fmt",
                &[b"20", b"19"],
                b"fmt: max length must be >= goal length\n",
            );
        }

        #[test]
        fn option_clusters_preserve_defined_digit_behavior() {
            let flags = resolve(&[b"-cmnps"]).config;
            assert!(flags.center_p);
            assert!(flags.grok_mail_headers);
            assert!(flags.format_troff);
            assert!(flags.allow_indented_paragraphs);
            assert!(flags.coalesce_spaces_p);

            assert_failure(b"path/to/fmt", &[b"-c20"], b"fmt: width must be nonzero\n");

            let width_already_set = resolve(&[b"-w10", b"-c20"]);
            assert!(width_already_set.config.center_p);
            assert_eq!(width_already_set.config.goal_length, 10);
            assert_eq!(width_already_set.config.max_length, 10);
        }

        #[test]
        fn undefined_c2_cluster_is_rejected_safely() {
            assert_failure(b"path/to/fmt", &[b"-c2"], b"fmt: width must be nonzero\n");
        }

        #[test]
        fn default_mode_permutes_options_after_operands() {
            let resolved =
                resolve_with_ordering(&[b"40", b"first", b"-c", b"\xffname", b"-s"], false);

            assert!(resolved.config.center_p);
            assert!(resolved.config.coalesce_spaces_p);
            assert_eq!(resolved.config.goal_length, 40);
            assert_eq!(resolved.config.max_length, 50);
            assert_eq!(
                operand_bytes(&resolved),
                vec![b"first".to_vec(), b"\xffname".to_vec()]
            );
        }

        #[test]
        fn double_dash_ends_option_parsing() {
            let resolved = resolve(&[b"-s", b"name", b"--", b"-c", b"40"]);

            assert!(resolved.config.coalesce_spaces_p);
            assert!(!resolved.config.center_p);
            assert_eq!(
                operand_bytes(&resolved),
                vec![b"name".to_vec(), b"-c".to_vec(), b"40".to_vec()]
            );
        }

        #[test]
        fn lone_dash_is_a_filename() {
            let resolved = resolve(&[b"-", b"-c"]);

            assert!(resolved.config.center_p);
            assert_eq!(operand_bytes(&resolved), vec![b"-".to_vec()]);
        }

        #[test]
        fn posixly_correct_stops_at_first_operand() {
            let resolved = resolve_with_ordering(&[b"-s", b"file", b"-c", b"40"], true);
            assert!(resolved.config.coalesce_spaces_p);
            assert!(!resolved.config.center_p);
            assert_eq!(resolved.config.goal_length, 65);
            assert_eq!(
                operand_bytes(&resolved),
                vec![b"file".to_vec(), b"-c".to_vec(), b"40".to_vec()]
            );

            let positional = resolve_with_ordering(&[b"40", b"-c"], true);
            assert_eq!(positional.config.goal_length, 40);
            assert_eq!(positional.config.max_length, 50);
            assert!(!positional.config.center_p);
            assert_eq!(operand_bytes(&positional), vec![b"-c".to_vec()]);
        }

        #[test]
        fn help_is_usage_with_status_one() {
            assert_failure(b"path/to/alias", &[b"-h"], &usage_bytes(b"alias"));
        }

        #[test]
        fn unknown_option_uses_raw_argv0_then_usage_basename() {
            let mut expected = b"path/to/alias: invalid option -- 'x'\n".to_vec();
            expected.extend_from_slice(&usage_bytes(b"alias"));

            assert_failure(b"path/to/alias", &[b"-x"], &expected);
        }

        #[test]
        fn missing_option_argument_uses_raw_argv0_then_usage_basename() {
            let mut expected = b"path/to/alias: option requires an argument -- 'w'\n".to_vec();
            expected.extend_from_slice(&usage_bytes(b"alias"));

            assert_failure(b"path/to/alias", &[b"-w"], &expected);
        }
    }

    mod lines {
        use super::super::*;
        use crate::runtime::FaultingReader;
        use std::io::{BufReader, Cursor};

        fn line_reader(input: &[u8], format_troff: bool) -> LineReader<BufReader<Cursor<Vec<u8>>>> {
            LineReader::new(
                BufReader::with_capacity(7, Cursor::new(input.to_vec())),
                format_troff,
            )
        }

        #[test]
        fn empty_input_has_no_line_event() {
            let mut lines = line_reader(b"", false);

            assert_eq!(lines.get_line(), None);
            assert!(lines.take_error().is_none());
        }

        #[test]
        fn physical_blank_line_has_an_empty_line_event() {
            let mut lines = line_reader(b"\n\n", false);

            assert_eq!(lines.get_line(), Some(Vec::new()));
            assert_eq!(lines.get_line(), Some(Vec::new()));
            assert_eq!(lines.get_line(), None);
        }

        #[test]
        fn final_line_without_lf_is_returned() {
            let mut lines = line_reader(b"unterminated", false);

            assert_eq!(lines.get_line(), Some(b"unterminated".to_vec()));
            assert_eq!(lines.get_line(), None);
        }

        #[test]
        fn line_longer_than_initial_capacity_is_returned() {
            let expected = vec![b'x'; 32 * 1024 + 17];
            let mut input = expected.clone();
            input.push(b'\n');
            let mut lines = line_reader(&input, false);

            assert_eq!(lines.get_line(), Some(expected));
            assert_eq!(lines.get_line(), None);
        }

        #[test]
        fn trailing_byte_whitespace_is_removed() {
            let mut lines = line_reader(b".text \t\x0b\x0c\r\nnext\t \n", false);

            assert_eq!(lines.get_line(), Some(b".text".to_vec()));
            assert_eq!(lines.get_line(), Some(b"next".to_vec()));
        }

        #[test]
        fn ordinary_control_bytes_are_removed() {
            let mut lines = line_reader(b"a\0\x01b\tc\x1f\x7f\r\n", false);

            assert_eq!(lines.get_line(), Some(b"ab\tc".to_vec()));
        }

        #[test]
        fn backspace_removes_one_preceding_retained_byte() {
            let mut ascii = line_reader(b"ab\x08\x08\x08c\n", false);
            assert_eq!(ascii.get_line(), Some(b"c".to_vec()));

            let mut multibyte = line_reader(b"\xc3\xa9\x08x\n", false);
            assert_eq!(multibyte.get_line(), Some(b"\xc3x".to_vec()));
        }

        #[test]
        fn dot_line_preserves_control_bytes_without_n() {
            let mut lines = line_reader(b".a\x01\x08\0b\t \n\x01.\x02\n", false);

            assert_eq!(lines.get_line(), Some(b".a\x01\x08\0b".to_vec()));
            assert_eq!(lines.get_line(), Some(b".\x02".to_vec()));
        }

        #[test]
        fn first_retained_dot_preserves_the_rest_of_the_line() {
            let mut lines = line_reader(b"\x01a\x08.\x02\x08\t \n", false);

            assert_eq!(lines.get_line(), Some(b".\x02\x08".to_vec()));
        }

        #[test]
        fn dot_line_is_sanitized_with_n() {
            let mut lines = line_reader(b".a\x01\x08\0b\t \n", true);

            assert_eq!(lines.get_line(), Some(b".b".to_vec()));
        }

        #[test]
        fn preserved_dot_line_nul_truncates_effective_output() {
            let mut lines = line_reader(b".visible\0hidden\n", false);
            let stored = lines.get_line().unwrap();

            assert_eq!(stored, b".visible\0hidden");
            assert_eq!(effective_line(&stored), b".visible");
        }

        #[test]
        fn read_error_after_partial_line_is_sticky() {
            let stream = FaultingReader::new(b"partial".to_vec(), 7, 5);
            let mut lines = LineReader::new(BufReader::with_capacity(2, stream), false);

            assert_eq!(lines.get_line(), Some(b"partial".to_vec()));
            assert_eq!(lines.get_line(), None);
            let error = lines.take_error().unwrap();
            assert_eq!(error.raw_os_error(), Some(5));
            assert!(lines.take_error().is_none());
            assert_eq!(lines.get_line(), None);

            let stream = FaultingReader::new(Vec::new(), 0, 5);
            let mut empty = LineReader::new(BufReader::new(stream), false);
            assert_eq!(empty.get_line(), None);
            assert_eq!(empty.take_error().unwrap().raw_os_error(), Some(5));
        }

        #[test]
        fn indentation_counts_spaces_and_tab_stops() {
            for (line, tab_width, expected) in [
                (&b"text"[..], 8, 0),
                (&b"   text"[..], 8, 3),
                (&b"\ttext"[..], 8, 8),
                (&b" \ttext"[..], 8, 8),
                (&b"\t text"[..], 8, 9),
                (&b"\t\ttext"[..], 8, 16),
                (&b"  \ttext"[..], 4, 4),
                (&b"\t\ttext"[..], 3, 6),
                (&b" \t text"[..], 1, 3),
                (&b" \xc2\xa0text"[..], 8, 1),
            ] {
                assert_eq!(indent_length(line, tab_width), expected, "{line:?}");
            }
        }

        #[test]
        fn header_predicate_accepts_conservative_shape() {
            for line in [
                &b"A: "[..],
                &b"Subject: value"[..],
                &b"X-Test9:\tvalue"[..],
                &b"Z9-foo:\rvalue"[..],
                &b"A-:\n"[..],
            ] {
                assert!(might_be_header(line), "{line:?}");
            }
        }

        #[test]
        fn header_predicate_rejects_near_misses() {
            for line in [
                &b""[..],
                &b"subject: value"[..],
                &b"9Subject: value"[..],
                &b" Subject: value"[..],
                &b"A:"[..],
                &b"A:value"[..],
                &b"A_B: value"[..],
                &b"A B: value"[..],
                &b"A:: value"[..],
                &b"A\xff: value"[..],
            ] {
                assert!(!might_be_header(line), "{line:?}");
            }
        }

        #[test]
        fn mail_classification_requires_option_and_header_context() {
            assert_eq!(
                HdrType::classify(false, HdrType::ParagraphStart, 0, b"Subject: value"),
                HdrType::NonHeader
            );
            assert_eq!(
                HdrType::classify(true, HdrType::ParagraphStart, 0, b"Subject: value"),
                HdrType::Header
            );
            assert_eq!(
                HdrType::classify(true, HdrType::NonHeader, 0, b"Subject: value"),
                HdrType::NonHeader
            );
            assert_eq!(
                HdrType::classify(true, HdrType::Header, 0, b"ordinary text"),
                HdrType::NonHeader
            );
        }

        #[test]
        fn mail_continuation_requires_indent_after_mail_line() {
            for previous in [HdrType::Header, HdrType::Continuation] {
                assert_eq!(
                    HdrType::classify(true, previous, 1, b" continued"),
                    HdrType::Continuation
                );
                assert_eq!(
                    HdrType::classify(true, previous, 8, b"\tcontinued"),
                    HdrType::Continuation
                );
            }
            assert_eq!(
                HdrType::classify(true, HdrType::ParagraphStart, 1, b" orphan"),
                HdrType::NonHeader
            );
            assert_eq!(
                HdrType::classify(true, HdrType::NonHeader, 1, b" ordinary"),
                HdrType::NonHeader
            );
        }
    }

    mod normal {
        use super::super::*;
        use std::io::Cursor;

        fn config(goal_length: usize, max_length: usize) -> Config {
            Config {
                center_p: false,
                goal_length,
                max_length,
                coalesce_spaces_p: false,
                allow_indented_paragraphs: false,
                tab_width: 8,
                output_tab_width: 0,
                sentence_enders: b".?!".to_vec(),
                grok_mail_headers: false,
                format_troff: false,
            }
        }

        fn format_with(input: &[u8], config: Config, locale_mode: LocaleMode) -> Vec<u8> {
            let mut output = Vec::new();
            {
                let mut input = Cursor::new(input);
                let mut formatter = Formatter::new(config, locale_mode, &mut output);
                assert!(formatter
                    .process_stream(&mut input, b"fixture")
                    .unwrap()
                    .is_none());
            }
            output
        }

        fn format(input: &[u8], goal_length: usize, max_length: usize) -> Vec<u8> {
            format_with(input, config(goal_length, max_length), LocaleMode::Utf8)
        }

        #[test]
        fn same_indentation_joins_physical_lines() {
            assert_eq!(
                format(b"  alpha beta\n  gamma delta\n", 80, 90,),
                b"  alpha beta gamma delta\n"
            );
        }

        #[test]
        fn changed_indentation_starts_a_paragraph() {
            assert_eq!(
                format(b" alpha beta\n  gamma delta\n", 80, 90),
                b" alpha beta\n  gamma delta\n"
            );
        }

        #[test]
        fn p_allows_first_line_indentation_to_differ() {
            let mut config = config(80, 90);
            config.allow_indented_paragraphs = true;

            assert_eq!(
                format_with(b"    alpha\n  beta\n", config, LocaleMode::Utf8,),
                b"    alpha beta\n"
            );
        }

        #[test]
        fn p_keeps_first_indent_when_joined_words_wrap() {
            let mut config = config(12, 12);
            config.allow_indented_paragraphs = true;

            assert_eq!(
                format_with(
                    b"    alpha beta\n  gamma delta epsilon\n",
                    config,
                    LocaleMode::Utf8,
                ),
                b"    alpha\n    beta\n    gamma\n    delta\n    epsilon\n"
            );
        }

        #[test]
        fn blank_lines_are_preserved_as_paragraphs() {
            assert_eq!(format(b"alpha\n\n\n beta\n", 80, 90), b"alpha\n\n\n beta\n");
        }

        #[test]
        fn wide_blank_only_line_materializes_pending_spacing() {
            assert_eq!(
                format_with(b"word\n\xe2\x80\x83\n", config(80, 90), LocaleMode::Utf8,),
                b"word \n"
            );
        }

        #[test]
        fn mail_header_starts_a_new_paragraph() {
            let mut config = config(80, 90);
            config.grok_mail_headers = true;

            assert_eq!(
                format_with(b"Subject: one\nFrom: two\n", config, LocaleMode::Utf8,),
                b"Subject: one\nFrom: two\n"
            );
        }

        #[test]
        fn mail_continuation_uses_two_output_spaces() {
            let mut config = config(65, 75);
            config.grok_mail_headers = true;

            assert_eq!(
                format_with(
                    b"Subject:\n  This is a long subject\n  that continues\n",
                    config,
                    LocaleMode::Utf8,
                ),
                b"Subject:\n  This is a long subject that continues\n"
            );
        }

        #[test]
        fn recognized_mail_continuation_stays_in_header_paragraph() {
            let mut config = config(80, 90);
            config.grok_mail_headers = true;

            assert_eq!(
                format_with(
                    b"Subject: value\n  continued words\n",
                    config,
                    LocaleMode::Utf8,
                ),
                b"Subject: value continued words\n"
            );
        }

        #[test]
        fn mail_continuations_ignore_source_indent_changes() {
            let mut config = config(100, 110);
            config.grok_mail_headers = true;

            assert_eq!(
                format_with(
                    b"Subject: value\n continued one\n        continued two\n\tcontinued three\n",
                    config,
                    LocaleMode::Utf8,
                ),
                b"Subject: value continued one continued two continued three\n"
            );
        }

        #[test]
        fn non_header_after_header_starts_a_paragraph() {
            let mut config = config(80, 90);
            config.grok_mail_headers = true;

            assert_eq!(
                format_with(b"Subject: value\nordinary body\n", config, LocaleMode::Utf8,),
                b"Subject: value\nordinary body\n"
            );
        }

        #[test]
        fn header_like_line_after_body_is_not_special() {
            let mut config = config(80, 90);
            config.grok_mail_headers = true;

            assert_eq!(
                format_with(
                    b"ordinary body\nSubject: still body\n",
                    config,
                    LocaleMode::Utf8,
                ),
                b"ordinary body Subject: still body\n"
            );
        }

        #[test]
        fn ordinary_text_blocks_headers_until_blank_line() {
            let mut config = config(100, 110);
            config.grok_mail_headers = true;

            assert_eq!(
                format_with(
                    b"ordinary body\nSubject: still body\n\nSubject: active\n continued\n",
                    config,
                    LocaleMode::Utf8,
                ),
                b"ordinary body Subject: still body\n\nSubject: active continued\n"
            );
        }

        #[test]
        fn mail_transition_matrix_preserves_exact_paragraphs() {
            let mut config = config(100, 110);
            config.grok_mail_headers = true;

            assert_eq!(
                format_with(
                    b"Subject: value\n continued\nordinary body\nFrom: body text\n\nFrom: sender\n next words\nbody tail\n",
                    config,
                    LocaleMode::Utf8,
                ),
                b"Subject: value continued\nordinary body From: body text\n\nFrom: sender next words\nbody tail\n"
            );
        }

        #[test]
        fn raw_troff_request_interrupts_paragraph() {
            assert_eq!(
                format(b"before words\n.TH\x01 title\nnext words\n", 80, 90),
                b"before words\n.TH\x01 title\nnext words\n"
            );
        }

        #[test]
        fn n_formats_troff_request_as_ordinary_paragraph_text() {
            let mut config = config(80, 90);
            config.format_troff = true;

            assert_eq!(
                format_with(
                    b"before words\n.TH\x01 title\nnext words\n",
                    config,
                    LocaleMode::Utf8,
                ),
                b"before words .TH title next words\n"
            );
        }

        #[test]
        fn exact_goal_stays_on_current_line() {
            assert_eq!(
                format(b"Hello world test\n", 11, 21),
                b"Hello world\ntest\n"
            );
        }

        #[test]
        fn nearest_goal_tie_goes_over() {
            assert_eq!(format(b"1234567 abcde\n", 10, 20), b"1234567 abcde\n");
        }

        #[test]
        fn maximum_forces_a_break() {
            assert_eq!(format(b"1234567 abcde\n", 10, 12), b"1234567\nabcde\n");
        }

        #[test]
        fn overlong_first_word_is_not_split() {
            assert_eq!(format(b"abcdefghij x\n", 5, 5), b"abcdefghij\nx\n");
        }

        #[test]
        fn source_space_width_is_preserved() {
            assert_eq!(format(b"one   two\n", 80, 90), b"one   two\n");
        }

        #[test]
        fn source_spacing_after_sentence_ender_is_preserved_without_s() {
            assert_eq!(format(b"End. next\n", 80, 90), b"End. next\n");
            assert_eq!(format(b"End.   next\n", 80, 90), b"End.   next\n");
        }

        #[test]
        fn s_replaces_source_spacing() {
            let mut config = config(80, 90);
            config.coalesce_spaces_p = true;

            assert_eq!(
                format_with(b"one    two\n", config, LocaleMode::Utf8),
                b"one two\n"
            );
        }

        #[test]
        fn s_uses_two_spaces_after_sentence_ender() {
            let mut config = config(80, 90);
            config.coalesce_spaces_p = true;

            assert_eq!(
                format_with(b"End.     next\n", config, LocaleMode::Utf8),
                b"End.  next\n"
            );
        }

        #[test]
        fn custom_sentence_enders_replace_defaults_during_coalescing() {
            let mut config = config(80, 90);
            config.coalesce_spaces_p = true;
            config.sentence_enders = b";".to_vec();

            assert_eq!(
                format_with(b"End.   next;   last\n", config, LocaleMode::Utf8),
                b"End. next;  last\n"
            );
        }

        #[test]
        fn sentence_ender_gets_two_spaces_at_physical_eol() {
            assert_eq!(format(b"End.\nNext\n", 80, 90), b"End.  Next\n");
        }

        #[test]
        fn sentence_ender_must_be_the_final_word_byte() {
            assert_eq!(format(b"middle.dot\nNext\n", 80, 90), b"middle.dot Next\n");
        }

        #[test]
        fn custom_sentence_enders_are_byte_based() {
            let mut config = config(80, 90);
            config.sentence_enders = vec![0xa9];

            assert_eq!(
                format_with(b"\xc3\xa9\nnext\n", config, LocaleMode::Utf8,),
                b"\xc3\xa9  next\n"
            );
        }

        #[test]
        fn empty_sentence_enders_disable_double_spacing() {
            let mut config = config(80, 90);
            config.sentence_enders.clear();

            assert_eq!(
                format_with(b"End.\nNext\n", config, LocaleMode::Utf8),
                b"End. Next\n"
            );
        }

        #[test]
        fn internal_tabs_use_physical_tab_stops() {
            let mut config = config(20, 20);
            config.tab_width = 4;

            assert_eq!(
                format_with(b"a\tb\tc\n", config, LocaleMode::Utf8),
                b"a   b   c\n"
            );
        }

        #[test]
        fn l_compresses_only_leading_indentation() {
            let mut config = config(30, 30);
            config.output_tab_width = 4;

            assert_eq!(
                format_with(b"      one    two\n", config, LocaleMode::Utf8,),
                b"\t  one    two\n"
            );
        }

        #[test]
        fn l_compresses_indentation_on_every_wrapped_line() {
            let mut config = config(8, 8);
            config.output_tab_width = 3;

            assert_eq!(
                format_with(b"        alpha beta gamma\n", config, LocaleMode::Utf8,),
                b"\t\t  alpha\n\t\t  beta\n\t\t  gamma\n"
            );
        }

        #[test]
        fn l_applies_to_indent_emitted_for_wide_blank_only_line() {
            let mut config = config(80, 90);
            config.output_tab_width = 3;

            assert_eq!(
                format_with(b"        \xe2\x80\x83\n", config, LocaleMode::Utf8),
                b"\t\t  "
            );
        }

        #[test]
        fn invalid_utf8_is_emitted_unchanged() {
            assert_eq!(
                format_with(b"\xffa b\n", config(3, 3), LocaleMode::Utf8,),
                b"\xffa\nb\n"
            );
        }

        #[test]
        fn wide_scalars_use_display_width() {
            assert_eq!(
                format_with(
                    b"\xe7\x95\x8c \xe7\x95\x8c \xe7\x95\x8c\n",
                    config(5, 5),
                    LocaleMode::Utf8,
                ),
                b"\xe7\x95\x8c \xe7\x95\x8c\n\xe7\x95\x8c\n"
            );
        }

        #[test]
        fn nbsp_is_not_a_word_separator() {
            assert_eq!(
                format_with(b"a\xc2\xa0b c\n", config(3, 3), LocaleMode::Utf8,),
                b"a\xc2\xa0b\nc\n"
            );
        }

        #[test]
        fn control_bytes_are_sanitized_before_wrapping() {
            assert_eq!(format(b"Hello\x01\x02world\n", 20, 20), b"Helloworld\n");
        }

        #[test]
        fn final_line_without_lf_gets_one_lf() {
            assert_eq!(format(b"unterminated", 80, 90), b"unterminated\n");
        }

        #[test]
        fn multiple_files_flush_independently() {
            let mut output = Vec::new();
            {
                let mut formatter = Formatter::new(config(80, 90), LocaleMode::Utf8, &mut output);
                for bytes in [&b"first file"[..], &b"second file"[..]] {
                    let mut input = Cursor::new(bytes);
                    assert!(formatter
                        .process_stream(&mut input, b"fixture")
                        .unwrap()
                        .is_none());
                }
            }

            assert_eq!(output, b"first file\nsecond file\n");
        }
    }

    mod centering {
        use super::super::*;
        use std::io::Cursor;

        fn config(goal_length: usize) -> Config {
            Config {
                center_p: true,
                goal_length,
                max_length: 1,
                coalesce_spaces_p: true,
                allow_indented_paragraphs: true,
                tab_width: 8,
                output_tab_width: 4,
                sentence_enders: Vec::new(),
                grok_mail_headers: true,
                format_troff: false,
            }
        }

        fn center_with(input: &[u8], config: Config, locale_mode: LocaleMode) -> Vec<u8> {
            let mut input = Cursor::new(input);
            let mut output = Vec::new();
            {
                let mut formatter = Formatter::new(config, locale_mode, &mut output);
                assert!(formatter
                    .process_stream(&mut input, b"fixture")
                    .unwrap()
                    .is_none());
            }
            output
        }

        fn center(input: &[u8], goal_length: usize) -> Vec<u8> {
            center_with(input, config(goal_length), LocaleMode::Utf8)
        }

        #[test]
        fn empty_line_is_centered_and_terminated() {
            assert_eq!(center(b"\n", 5), b"   \n");
        }

        #[test]
        fn overwide_line_has_no_padding() {
            assert_eq!(center(b"overwide\n", 4), b"overwide\n");
        }

        #[test]
        fn even_goal_padding_is_exact() {
            assert_eq!(center(b"rust\n", 10), b"   rust\n");
        }

        #[test]
        fn odd_goal_padding_rounds_up() {
            assert_eq!(center(b"rust\n", 9), b"   rust\n");
        }

        #[test]
        fn leading_wide_whitespace_is_removed() {
            let input = b" \xe2\x80\x83\xe3\x80\x80\xe7\x95\x8c\n";
            assert_eq!(center(input, 6), b"  \xe7\x95\x8c\n");
        }

        #[test]
        fn tabs_become_one_space_independent_of_t() {
            let expected = b"     Hello World\n";
            for tab_width in [1, 4, 32] {
                let mut configured = config(20);
                configured.tab_width = tab_width;
                assert_eq!(
                    center_with(b"Hello\tWorld\n", configured, LocaleMode::Utf8),
                    expected
                );
            }
        }

        #[test]
        fn invalid_bytes_become_question_marks() {
            let input = &[b'z', 0xc3, 0x9f, 0xe6, 0xff, b'\n'];
            assert_eq!(
                center_with(input, config(10), LocaleMode::Utf8),
                b"   z\xc3\x9f??\n"
            );
        }

        #[test]
        fn malformed_byte_reuses_prior_wide_character_for_leading_space() {
            assert_eq!(
                center_with(b" \xffX\n", config(8), LocaleMode::Utf8),
                b"    X\n"
            );
            assert_eq!(
                center_with(b"\xe2\x80\x83\n\xffX\n", config(8), LocaleMode::Utf8,),
                b"    \n    X\n"
            );
        }

        #[test]
        fn final_line_without_lf_gets_lf() {
            assert_eq!(center(b"last", 8), b"  last\n");
        }

        #[test]
        fn scalar_display_width_controls_padding() {
            let input = b"\xe7\x95\x8ce\xcc\x81\n";
            assert_eq!(center(input, 8), b"   \xe7\x95\x8ce\xcc\x81\n");
        }

        #[test]
        fn sanitized_physical_lines_are_never_joined_as_paragraphs() {
            let input = b"ab\x08c\x01  \nnext line\n\n";
            assert_eq!(center(input, 10), b"    ac\n next line\n     \n");
        }
    }

    mod application {
        use super::super::*;
        use crate::runtime::{FaultingReader, FaultingWriter, MockFileSource};
        use std::ffi::OsString;
        use std::io::{Cursor, Read};

        #[cfg(unix)]
        use std::os::unix::ffi::OsStringExt;

        fn context(argv0: OsString, arguments: Vec<OsString>) -> ProcessContext {
            let mut argv = vec![argv0];
            argv.extend(arguments);
            let mut context = ProcessContext::fixture(argv);
            context.lang = Some(OsString::from("C.UTF-8"));
            context
        }

        fn execute_os(
            argv0: OsString,
            arguments: Vec<OsString>,
            input: &[u8],
            files: &MockFileSource,
        ) -> (u8, Vec<u8>, Vec<u8>) {
            let context = context(argv0, arguments);
            let mut stdin = Cursor::new(input.to_vec());
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let status = run(&context, &mut stdin, &mut stdout, &mut stderr, files).unwrap();
            (status, stdout, stderr)
        }

        fn execute(
            argv0: &str,
            arguments: &[&str],
            input: &[u8],
            files: &MockFileSource,
        ) -> (u8, Vec<u8>, Vec<u8>) {
            execute_os(
                OsString::from(argv0),
                arguments.iter().map(OsString::from).collect(),
                input,
                files,
            )
        }

        #[test]
        fn no_operands_selects_standard_input() {
            let files = MockFileSource::new();
            let (status, stdout, stderr) = execute("fmt", &["72"], b"standard input text", &files);

            assert_eq!(status, 0);
            assert_eq!(stdout, b"standard input text\n");
            assert!(stderr.is_empty());
            assert!(files.open_order().is_empty());

            let dash_files = MockFileSource::new();
            dash_files.insert_file(OsString::from("-"), b"named dash file".to_vec());
            let (status, stdout, stderr) =
                execute("fmt", &["-"], b"unused standard input", &dash_files);

            assert_eq!(status, 0);
            assert_eq!(stdout, b"named dash file\n");
            assert!(stderr.is_empty());
            assert_eq!(dash_files.open_order(), [OsString::from("-")]);

            let fault_files = MockFileSource::new();
            let context = context(OsString::from("fmt"), Vec::new());
            let partial = b"partial stdin".to_vec();
            let mut stdin = FaultingReader::new(partial.clone(), partial.len(), 5);
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let status = run(&context, &mut stdin, &mut stdout, &mut stderr, &fault_files).unwrap();

            assert_eq!(status, 1);
            assert_eq!(stdout, b"partial stdin\n");
            assert_eq!(stderr, b"fmt: standard input: Input/output error\n");
            assert!(fault_files.open_order().is_empty());
        }

        #[test]
        fn files_open_and_process_left_to_right() {
            let files = MockFileSource::new();
            files.insert_file(OsString::from("first"), b"first file".to_vec());
            files.insert_file(OsString::from("second"), b"second file".to_vec());
            files.insert_file(OsString::from("third"), b"third file".to_vec());

            let (status, stdout, stderr) = execute(
                "fmt",
                &["first", "second", "third"],
                b"unused standard input",
                &files,
            );

            assert_eq!(status, 0);
            assert_eq!(stdout, b"first file\nsecond file\nthird file\n");
            assert!(stderr.is_empty());
            assert_eq!(
                files.open_order(),
                [
                    OsString::from("first"),
                    OsString::from("second"),
                    OsString::from("third"),
                ]
            );
        }

        #[test]
        fn file_boundaries_do_not_invent_separators() {
            let files = MockFileSource::new();
            files.insert_file(OsString::from("one"), b"alpha beta".to_vec());
            files.insert_file(OsString::from("empty"), Vec::new());
            files.insert_file(OsString::from("two"), b"gamma delta".to_vec());

            let (status, stdout, stderr) = execute("fmt", &["one", "empty", "two"], b"", &files);

            assert_eq!(status, 0);
            assert_eq!(stdout, b"alpha beta\ngamma delta\n");
            assert!(stderr.is_empty());
        }

        #[test]
        fn open_error_warns_and_continues() {
            let files = MockFileSource::new();
            files.insert_file(OsString::from("before"), b"before".to_vec());
            files.insert_error(OsString::from("missing"), 2);
            files.insert_file(OsString::from("after"), b"after".to_vec());

            let (status, stdout, stderr) =
                execute("fmt", &["before", "missing", "after"], b"", &files);

            assert_eq!(status, 1);
            assert_eq!(stdout, b"before\nafter\n");
            assert_eq!(stderr, b"fmt: missing: No such file or directory\n");
            assert_eq!(
                files.open_order(),
                [
                    OsString::from("before"),
                    OsString::from("missing"),
                    OsString::from("after"),
                ]
            );
        }

        #[test]
        fn mixed_read_and_open_failures_accumulate_in_order() {
            let files = MockFileSource::new();
            files.insert_read_error(
                OsString::from("broken"),
                b"partial".to_vec(),
                b"partial".len(),
                5,
            );
            files.insert_error(OsString::from("missing"), 2);
            files.insert_file(OsString::from("after"), b"after".to_vec());

            let (status, stdout, stderr) =
                execute("fmt", &["broken", "missing", "after"], b"", &files);

            assert_eq!(status, 2);
            assert_eq!(stdout, b"partial\nafter\n");
            assert_eq!(
                stderr,
                b"fmt: broken: Input/output error\n\
                  fmt: missing: No such file or directory\n"
            );
            assert_eq!(
                files.open_order(),
                [
                    OsString::from("broken"),
                    OsString::from("missing"),
                    OsString::from("after"),
                ]
            );
        }

        #[cfg(unix)]
        #[test]
        fn raw_non_utf8_paths_are_opened_and_reported() {
            let readable = OsString::from_vec(b"readable-\xff".to_vec());
            let missing = OsString::from_vec(b"missing-\xfe".to_vec());
            let files = MockFileSource::new();
            files.insert_file(readable.clone(), b"raw path data".to_vec());
            files.insert_error(missing.clone(), 2);

            let (status, stdout, stderr) = execute_os(
                OsString::from("/usr/bin/fmt"),
                vec![readable.clone(), missing.clone()],
                b"",
                &files,
            );
            let mut expected_stderr = b"fmt: missing-\xfe: ".to_vec();
            expected_stderr.extend_from_slice(b"No such file or directory\n");

            assert_eq!(status, 1);
            assert_eq!(stdout, b"raw path data\n");
            assert_eq!(stderr, expected_stderr);
            assert_eq!(files.open_order(), [readable, missing]);
        }

        #[cfg(unix)]
        #[test]
        fn raw_invocation_alias_is_preserved_in_file_diagnostics() {
            let missing = OsString::from_vec(b"missing-\xfe".to_vec());
            let files = MockFileSource::new();
            files.insert_error(missing.clone(), 2);

            let (status, stdout, stderr) = execute_os(
                OsString::from_vec(b"/tmp/f\xffmt".to_vec()),
                vec![missing.clone()],
                b"",
                &files,
            );

            assert_eq!(status, 1);
            assert!(stdout.is_empty());
            assert_eq!(
                stderr,
                b"f\xffmt: missing-\xfe: No such file or directory\n"
            );
            assert_eq!(files.open_order(), [missing]);
        }

        #[test]
        fn partial_read_error_flushes_then_warns_once() {
            let broken_bytes = b"partial data".to_vec();
            let fail_after = broken_bytes.len();
            let files = MockFileSource::new();
            files.insert_read_error(OsString::from("broken"), broken_bytes, fail_after, 5);
            files.insert_file(OsString::from("after"), b"next file".to_vec());

            let (status, stdout, stderr) = execute("fmt", &["broken", "after"], b"", &files);

            assert_eq!(status, 1);
            assert_eq!(stdout, b"partial data\nnext file\n");
            assert_eq!(stderr, b"fmt: broken: Input/output error\n");
            assert_eq!(
                files.open_order(),
                [OsString::from("broken"), OsString::from("after")]
            );
        }

        #[test]
        fn stream_error_count_saturates_at_127() {
            let files = MockFileSource::new();
            let arguments = (0..130)
                .map(|_| OsString::from("missing"))
                .collect::<Vec<_>>();

            let (status, stdout, stderr) =
                execute_os(OsString::from("fmt"), arguments, b"", &files);

            assert_eq!(status, 127);
            assert!(stdout.is_empty());
            assert_eq!(
                stderr,
                b"fmt: missing: No such file or directory\n".repeat(130)
            );
            assert_eq!(files.open_order().len(), 130);
        }

        #[test]
        fn input_files_are_never_mutated() {
            let path = OsString::from("source");
            let original = b"input bytes stay unchanged\n".to_vec();
            let files = MockFileSource::new();
            files.insert_file(path.clone(), original.clone());

            let (status, stdout, stderr) = execute("fmt", &["source"], b"", &files);

            assert_eq!(status, 0);
            assert_eq!(stdout, original);
            assert!(stderr.is_empty());
            assert_eq!(files.open_order(), [path.clone()]);

            let mut reopened = files.open(&path).unwrap();
            let mut stored = Vec::new();
            reopened.read_to_end(&mut stored).unwrap();
            assert_eq!(stored, original);
        }

        #[test]
        fn stdout_and_stderr_remain_separate() {
            let files = MockFileSource::new();
            files.insert_error(OsString::from("denied"), 13);
            files.insert_file(OsString::from("readable"), b"formatted output".to_vec());

            let (status, stdout, stderr) = execute("fmt", &["denied", "readable"], b"", &files);

            assert_eq!(status, 1);
            assert_eq!(stdout, b"formatted output\n");
            assert_eq!(stderr, b"fmt: denied: Permission denied\n");
        }

        #[test]
        fn writer_failure_propagates_without_invented_diagnostic() {
            let files = MockFileSource::new();
            files.insert_file(OsString::from("first"), b"abcdef".to_vec());
            files.insert_file(OsString::from("second"), b"unreached".to_vec());
            let context = context(
                OsString::from("fmt"),
                vec![OsString::from("first"), OsString::from("second")],
            );
            let mut stdin = Cursor::new(Vec::<u8>::new());
            let mut stdout = FaultingWriter::new(3, 28);
            let mut stderr = Vec::new();

            let error = run(&context, &mut stdin, &mut stdout, &mut stderr, &files).unwrap_err();

            assert_eq!(error.raw_os_error(), Some(28));
            assert_eq!(stdout.bytes(), b"abc");
            assert!(stderr.is_empty());
            assert_eq!(files.open_order(), [OsString::from("first")]);
        }

        #[test]
        fn diagnostic_writer_failure_stops_before_later_files() {
            let files = MockFileSource::new();
            files.insert_error(OsString::from("denied"), 13);
            files.insert_file(OsString::from("unreached"), b"unreached".to_vec());
            let context = context(
                OsString::from("fmt-special"),
                vec![OsString::from("denied"), OsString::from("unreached")],
            );
            let mut stdin = Cursor::new(Vec::<u8>::new());
            let mut stdout = Vec::new();
            let mut stderr = FaultingWriter::new(4, 28);

            let error = run(&context, &mut stdin, &mut stdout, &mut stderr, &files).unwrap_err();

            assert_eq!(error.raw_os_error(), Some(28));
            assert!(stdout.is_empty());
            assert_eq!(stderr.bytes(), b"fmt-");
            assert_eq!(files.open_order(), [OsString::from("denied")]);
        }

        #[test]
        fn locale_controls_centered_multibyte_decoding() {
            let files = MockFileSource::new();
            for (locale, expected) in [("C", &b"  z??\n"[..]), ("C.UTF-8", &b"  z\xc3\xa9\n"[..])] {
                let mut context = context(
                    OsString::from("fmt"),
                    vec![
                        OsString::from("-c"),
                        OsString::from("-w"),
                        OsString::from("6"),
                    ],
                );
                context.lc_all = Some(OsString::from(locale));
                let mut stdin = Cursor::new(b"z\xc3\xa9\n");
                let mut stdout = Vec::new();
                let mut stderr = Vec::new();

                let status = run(&context, &mut stdin, &mut stdout, &mut stderr, &files).unwrap();

                assert_eq!(status, 0, "{locale}");
                assert_eq!(stdout, expected, "{locale}");
                assert!(stderr.is_empty(), "{locale}");
            }
        }

        #[test]
        fn invocation_alias_changes_diagnostic_prefixes() {
            let files = MockFileSource::new();
            files.insert_error(OsString::from("denied"), 13);

            let (status, stdout, stderr) =
                execute("/tmp/tools/fmt-special", &["denied"], b"", &files);

            assert_eq!(status, 1);
            assert!(stdout.is_empty());
            assert_eq!(stderr, b"fmt-special: denied: Permission denied\n");
        }
    }

    mod seed_equivalents {
        use super::super::*;
        use crate::runtime::MockFileSource;
        use std::ffi::OsString;
        use std::io::Cursor;

        fn execute(
            arguments: &[&str],
            input: &[u8],
            files: &MockFileSource,
        ) -> (u8, Vec<u8>, Vec<u8>) {
            let mut argv = vec![OsString::from("fmt")];
            argv.extend(arguments.iter().map(OsString::from));
            let mut context = ProcessContext::fixture(argv);
            context.lang = Some(OsString::from("C.UTF-8"));
            let mut stdin = Cursor::new(input);
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let status = run(&context, &mut stdin, &mut stdout, &mut stderr, files).unwrap();
            (status, stdout, stderr)
        }

        fn assert_stdin_case(arguments: &[&str], input: &[u8], expected: &[u8]) {
            let files = MockFileSource::new();
            let (status, stdout, stderr) = execute(arguments, input, &files);
            assert_eq!(status, 0);
            assert_eq!(stdout, expected);
            assert!(stderr.is_empty());
        }

        #[test]
        fn seed_center_odd_width() {
            assert_stdin_case(&["-c", "-w", "21"], b"Hello\n", b"        Hello\n");
        }

        #[test]
        fn seed_very_long_line() {
            let input = b"This is a very long line that should test the dynamic buffer allocation in get_line function and make sure it can handle arbitrarily long input lines without crashing\n";
            let expected = b"This is a very long line that should test the\n\
dynamic buffer allocation in get_line function and\n\
make sure it can handle arbitrarily long input\n\
lines without crashing\n";
            assert_stdin_case(&["-w", "50"], input, expected);
        }

        #[test]
        fn seed_format_troff_enabled() {
            assert_stdin_case(
                &["-n", "-w", "10"],
                b".TH MANUAL\nRegular text\n",
                b".TH MANUAL\nRegular\ntext\n",
            );
        }

        #[test]
        fn seed_custom_sentence_enders2() {
            assert_stdin_case(
                &["-d", ".!?", "-w", "20"],
                b"End.  Next!  Another?\n",
                b"End.  Next!\nAnother?\n",
            );
        }

        #[test]
        fn seed_center_invalid_utf8() {
            assert_stdin_case(
                &["-w", "20", "-c"],
                &[b'z', 0xc3, 0x9f, 0xe6, b'\n'],
                &[
                    b' ', b' ', b' ', b' ', b' ', b' ', b' ', b' ', b' ', b'z', 0xc3, 0x9f, b'?',
                    b'\n',
                ],
            );
        }

        #[test]
        fn seed_center_custom_tab() {
            assert_stdin_case(
                &["-c", "-t", "4", "-w", "20"],
                b"Hello\tWorld\n",
                b"     Hello World\n",
            );
        }

        #[test]
        fn seed_goal_word_boundary() {
            assert_stdin_case(&["-w", "11"], b"Hello world test\n", b"Hello world\ntest\n");
        }

        #[test]
        fn seed_tab_expansion_custom() {
            assert_stdin_case(&["-t", "4", "-w", "20"], b"a\tb\tc\n", b"a   b   c\n");
        }

        #[test]
        fn seed_wide_characters() {
            let mut input = Vec::new();
            for trailing in 0xb1..=0xbf {
                input.extend_from_slice(&[0xce, trailing]);
            }
            input.push(b'\n');
            let expected = input.clone();
            assert_stdin_case(&["-w", "10"], &input, &expected);
        }

        #[test]
        fn seed_control_chars_stripped() {
            assert_stdin_case(&["-w", "20"], b"Hello\x01\x02world\n", b"Helloworld\n");
        }

        #[test]
        fn seed_file_processing() {
            let files = MockFileSource::new();
            files.insert_file(
                OsString::from("test_input.txt"),
                b"This is a test file\nwith multiple lines\n".to_vec(),
            );
            let (status, stdout, stderr) = execute(&["-w", "10", "test_input.txt"], b"", &files);
            assert_eq!(status, 0);
            assert_eq!(stdout, b"This is a\ntest file\nwith\nmultiple\nlines\n");
            assert!(stderr.is_empty());
            assert_eq!(files.open_order(), [OsString::from("test_input.txt")]);
        }

        #[test]
        fn seed_multiple_tabs() {
            assert_stdin_case(
                &["-t", "4", "-w", "20"],
                b"\t\tDouble tab\n",
                b"        Double tab\n",
            );
        }

        #[test]
        fn seed_dot_line_start() {
            assert_stdin_case(
                &["-w", "10"],
                b".Not troff\nRegular text\n",
                b".Not troff\nRegular\ntext\n",
            );
        }

        #[test]
        fn seed_non_header_after_header() {
            assert_stdin_case(
                &["-m"],
                b"Subject: Test\nNot a header\n\nBody\n",
                b"Subject: Test\nNot a header\n\nBody\n",
            );
        }

        #[test]
        fn seed_mail_header_continuation() {
            assert_stdin_case(
                &["-m"],
                b"Subject:\n  This is a long subject\n  that continues\n\nBody text\n",
                b"Subject:\n  This is a long subject that continues\n\nBody text\n",
            );
        }
    }
}
