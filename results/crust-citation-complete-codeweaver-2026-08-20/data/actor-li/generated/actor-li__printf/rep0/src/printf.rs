#![allow(dead_code)]

use crate::format::{
    self, Conversion, DirectiveError, FieldWidth, FormatError, FormatValue, Precision,
    ResolvedFields,
};
use crate::numparse::{
    self, parse_double, parse_long, parse_ulong, quoted_byte, ParsedNumber, RangeState,
};
use std::io::{self, BufWriter, IsTerminal, LineWriter, Write};

pub const NUMBER: &[u8] = b"+-.0123456789";
pub const USAGE: &[u8] = b"usage: printf format [argument ...]\n";

pub trait Output {
    fn write_stdout(&mut self, bytes: &[u8]) -> io::Result<()>;
    fn write_stderr(&mut self, bytes: &[u8]) -> io::Result<()>;
    fn flush_stdout(&mut self) -> io::Result<()>;
}

enum StdoutBuffer {
    Line(LineWriter<io::Stdout>),
    Block(BufWriter<io::Stdout>),
}

pub struct StdioOutput {
    stdout: StdoutBuffer,
    stderr: io::Stderr,
}

impl StdioOutput {
    pub fn new() -> Self {
        let stdout = io::stdout();
        let stdout = if stdout.is_terminal() {
            StdoutBuffer::Line(LineWriter::new(stdout))
        } else {
            StdoutBuffer::Block(BufWriter::new(stdout))
        };
        Self {
            stdout,
            stderr: io::stderr(),
        }
    }
}

impl Output for StdioOutput {
    fn write_stdout(&mut self, bytes: &[u8]) -> io::Result<()> {
        match &mut self.stdout {
            StdoutBuffer::Line(stdout) => stdout.write_all(bytes),
            StdoutBuffer::Block(stdout) => stdout.write_all(bytes),
        }
    }

    fn write_stderr(&mut self, bytes: &[u8]) -> io::Result<()> {
        self.stderr.write_all(bytes)?;
        self.stderr.flush()
    }

    fn flush_stdout(&mut self) -> io::Result<()> {
        match &mut self.stdout {
            StdoutBuffer::Line(stdout) => stdout.flush(),
            StdoutBuffer::Block(stdout) => stdout.flush(),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RunOutcome {
    pub status: u8,
}

#[derive(Debug)]
pub enum RunError {
    Io(io::Error),
    InternalInvariant,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EscapeControl {
    Continue,
    Stop,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EscapeWarning {
    NullSequence,
    Unknown(u8),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct EscapeResult {
    pub consumed: usize,
    pub output: Option<u8>,
    pub warning: Option<EscapeWarning>,
}

pub struct ArgCursor<'a> {
    args: &'a [Vec<u8>],
    index: usize,
}

impl<'a> ArgCursor<'a> {
    pub fn new(args: &'a [Vec<u8>]) -> Self {
        Self { args, index: 0 }
    }

    pub fn position(&self) -> usize {
        self.index
    }

    pub fn has_remaining(&self) -> bool {
        self.index < self.args.len()
    }

    fn peek(&self) -> Option<&'a [u8]> {
        self.args.get(self.index).map(Vec::as_slice)
    }

    fn next(&mut self) -> Option<&'a [u8]> {
        let value = self.peek()?;
        self.index += 1;
        Some(value)
    }
}

pub struct PrintfState<'args, 'output> {
    cursor: ArgCursor<'args>,
    rval: u8,
    program_name: &'args [u8],
    output: &'output mut dyn Output,
}

impl<'args, 'output> PrintfState<'args, 'output> {
    pub fn new(
        program_name: &'args [u8],
        operands: &'args [Vec<u8>],
        output: &'output mut dyn Output,
    ) -> Self {
        Self {
            cursor: ArgCursor::new(operands),
            rval: 0,
            program_name,
            output,
        }
    }

    pub fn print_escape_str(&mut self, value: &[u8]) -> Result<EscapeControl, RunError> {
        let mut index = 0;
        while index < value.len() {
            if value[index] != b'\\' {
                self.write_stdout(&value[index..index + 1])?;
                index += 1;
                continue;
            }

            match value.get(index + 1) {
                Some(b'0') => {
                    let mut cursor = index + 2;
                    let mut decoded = 0_u8;
                    for _ in 0..3 {
                        let Some(byte) = value.get(cursor).copied().filter(|byte| isodigit(*byte))
                        else {
                            break;
                        };
                        decoded = decoded.wrapping_shl(3).wrapping_add(octtobin(byte));
                        cursor += 1;
                    }
                    self.write_stdout(&[decoded])?;
                    index = cursor;
                }
                Some(b'c') => return Ok(EscapeControl::Stop),
                _ => {
                    let escaped = print_escape(&value[index..]);
                    if let Some(byte) = escaped.output {
                        self.write_stdout(&[byte])?;
                    }
                    if let Some(warning) = escaped.warning {
                        self.emit_escape_warning(warning)?;
                    }
                    index = index.saturating_add(1 + escaped.consumed);
                }
            }
        }
        Ok(EscapeControl::Continue)
    }

    pub fn getchr(&mut self) -> u8 {
        self.cursor
            .next()
            .and_then(|value| value.first().copied())
            .unwrap_or(0)
    }

    pub fn getstr(&mut self) -> &'args [u8] {
        self.cursor.next().unwrap_or(b"")
    }

    pub fn getint(&mut self) -> i32 {
        let Some(value) = self.cursor.peek() else {
            return 0;
        };
        if !value.is_empty() && !NUMBER.contains(&value[0]) {
            return 0;
        }
        let parsed = numparse::atoi(value);
        let _ = self.cursor.next();
        parsed
    }

    pub fn getlong(&mut self) -> Result<i64, RunError> {
        let Some(value) = self.cursor.next() else {
            return Ok(0);
        };
        if let Some(value) = quoted_byte(value) {
            return Ok(value as i64);
        }
        let parsed = parse_long(value);
        self.check_conversion(value, &parsed)?;
        Ok(parsed.value)
    }

    pub fn getulong(&mut self) -> Result<u64, RunError> {
        let Some(value) = self.cursor.next() else {
            return Ok(0);
        };
        if let Some(value) = quoted_byte(value) {
            return Ok(value as u64);
        }
        let parsed = parse_ulong(value);
        self.check_conversion(value, &parsed)?;
        Ok(parsed.value)
    }

    pub fn getdouble(&mut self) -> Result<f64, RunError> {
        let Some(value) = self.cursor.next() else {
            return Ok(0.0);
        };
        if let Some(value) = quoted_byte(value) {
            return Ok(value as f64);
        }
        let parsed = parse_double(value);
        self.check_conversion(value, &parsed)?;
        Ok(parsed.value)
    }

    pub fn check_conversion<T>(
        &mut self,
        source: &[u8],
        parsed: &ParsedNumber<T>,
    ) -> Result<(), RunError> {
        let message = if parsed.end < source.len() {
            if parsed.end == 0 {
                Some(b": expected numeric value".as_slice())
            } else {
                Some(b": not completely converted".as_slice())
            }
        } else if parsed.range != RangeState::InRange {
            Some(b": Numerical result out of range".as_slice())
        } else {
            None
        };

        if let Some(message) = message {
            let mut diagnostic = self.diagnostic_prefix();
            diagnostic.extend_from_slice(source);
            diagnostic.extend_from_slice(message);
            diagnostic.push(b'\n');
            self.output
                .write_stderr(&diagnostic)
                .map_err(RunError::Io)?;
            self.rval = 1;
        }
        Ok(())
    }

    pub fn usage(&mut self) -> Result<RunOutcome, RunError> {
        self.output.write_stderr(USAGE).map_err(RunError::Io)?;
        Ok(RunOutcome { status: 1 })
    }

    fn write_stdout(&mut self, bytes: &[u8]) -> Result<(), RunError> {
        self.output.write_stdout(bytes).map_err(RunError::Io)
    }

    fn diagnostic_prefix(&self) -> Vec<u8> {
        let mut diagnostic = Vec::with_capacity(self.program_name.len().saturating_add(2));
        diagnostic.extend_from_slice(self.program_name);
        diagnostic.extend_from_slice(b": ");
        diagnostic
    }

    fn warning(&mut self, message: &[u8]) -> Result<(), RunError> {
        let mut diagnostic = self.diagnostic_prefix();
        diagnostic.extend_from_slice(message);
        diagnostic.push(b'\n');
        self.output.write_stderr(&diagnostic).map_err(RunError::Io)
    }

    fn emit_escape_warning(&mut self, warning: EscapeWarning) -> Result<(), RunError> {
        match warning {
            EscapeWarning::NullSequence => self.warning(b"null escape sequence")?,
            EscapeWarning::Unknown(byte) => {
                let mut message = Vec::from(b"unknown escape sequence `\\".as_slice());
                message.push(byte);
                message.push(b'\'');
                self.warning(&message)?;
            }
        }
        self.rval = 1;
        Ok(())
    }

    fn invalid_directive(&mut self, directive: &[u8]) -> Result<RunOutcome, RunError> {
        let mut message = Vec::with_capacity(directive.len().saturating_add(19));
        message.extend_from_slice(directive);
        message.extend_from_slice(b": invalid directive");
        self.warning(&message)?;
        Ok(RunOutcome { status: 1 })
    }
}

pub fn isodigit(byte: u8) -> bool {
    matches!(byte, b'0'..=b'7')
}

pub fn octtobin(byte: u8) -> u8 {
    byte.saturating_sub(b'0')
}

pub fn hextobin(byte: u8) -> u8 {
    match byte {
        b'A'..=b'F' => byte - b'A' + 10,
        b'a'..=b'f' => byte - b'a' + 10,
        b'0'..=b'9' => byte - b'0',
        _ => 0,
    }
}

pub fn print_escape(input: &[u8]) -> EscapeResult {
    let Some(escaped) = input.get(1).copied() else {
        return EscapeResult {
            consumed: 0,
            output: None,
            warning: Some(EscapeWarning::NullSequence),
        };
    };

    if isodigit(escaped) {
        let mut consumed = 0;
        let mut value = 0_u8;
        for byte in input.iter().skip(1).take(3).copied() {
            if !isodigit(byte) {
                break;
            }
            value = value.wrapping_shl(3).wrapping_add(octtobin(byte));
            consumed += 1;
        }
        return EscapeResult {
            consumed,
            output: Some(value),
            warning: None,
        };
    }

    if escaped == b'x' {
        let mut consumed = 1;
        let mut value = 0_u8;
        for byte in input.iter().skip(2).take(2).copied() {
            if !byte.is_ascii_hexdigit() {
                break;
            }
            value = value.wrapping_shl(4).wrapping_add(hextobin(byte));
            consumed += 1;
        }
        return EscapeResult {
            consumed,
            output: Some(value),
            warning: None,
        };
    }

    let output = match escaped {
        b'\\' => b'\\',
        b'\'' => b'\'',
        b'"' => b'"',
        b'a' => 0x07,
        b'b' => 0x08,
        b'e' => 0x1b,
        b'f' => 0x0c,
        b'n' => b'\n',
        b'r' => b'\r',
        b't' => b'\t',
        b'v' => 0x0b,
        _ => {
            return EscapeResult {
                consumed: 1,
                output: Some(escaped),
                warning: Some(EscapeWarning::Unknown(escaped)),
            }
        }
    };
    EscapeResult {
        consumed: 1,
        output: Some(output),
        warning: None,
    }
}

pub fn run(args: &[Vec<u8>], output: &mut dyn Output) -> Result<RunOutcome, RunError> {
    let result = run_inner(args, output);
    let flush = output.flush_stdout().map_err(RunError::Io);
    match result {
        Ok(outcome) => {
            flush?;
            Ok(outcome)
        }
        Err(error) => {
            let _ = flush;
            Err(error)
        }
    }
}

fn run_inner(args: &[Vec<u8>], output: &mut dyn Output) -> Result<RunOutcome, RunError> {
    let program_name = args
        .first()
        .map(Vec::as_slice)
        .map(program_basename)
        .unwrap_or(b"");
    let mut format_index = 1;
    if args
        .get(format_index)
        .is_some_and(|argument| argument == b"--")
    {
        format_index += 1;
    }

    if format_index >= args.len() {
        let mut state = PrintfState::new(program_name, &[], output);
        return state.usage();
    }

    let format = args[format_index].as_slice();
    let operands = &args[format_index + 1..];
    let mut state = PrintfState::new(program_name, operands, output);

    loop {
        let pass_start = state.cursor.position();
        let mut index = 0;
        while index < format.len() {
            match format[index] {
                b'%' => {
                    match format.get(index + 1).copied() {
                        Some(b'%') => {
                            state.write_stdout(b"%")?;
                            index += 2;
                            continue;
                        }
                        Some(b'b') => {
                            let value = state.getstr();
                            if state.print_escape_str(value)? == EscapeControl::Stop {
                                return Ok(RunOutcome { status: state.rval });
                            }
                            index += 2;
                            continue;
                        }
                        _ => {}
                    }

                    let (directive, next) = match format::parse_directive(format, index) {
                        Ok(parsed) => parsed,
                        Err(DirectiveError::MissingFormatCharacter) => {
                            state.warning(b"missing format character")?;
                            return Ok(RunOutcome { status: 1 });
                        }
                        Err(DirectiveError::InvalidDirective { end }) => {
                            return state.invalid_directive(&format[index..end.min(format.len())]);
                        }
                    };
                    let fields = ResolvedFields {
                        width: match directive.width {
                            FieldWidth::None => None,
                            FieldWidth::Static(value) if value <= i32::MAX as u64 => {
                                Some(value as i32)
                            }
                            FieldWidth::Static(_) => None,
                            FieldWidth::Dynamic => Some(state.getint()),
                        },
                        precision: match directive.precision {
                            Precision::None => None,
                            Precision::Static(value) if value <= i32::MAX as u64 => {
                                Some(value as i32)
                            }
                            Precision::Static(_) => None,
                            Precision::Dynamic => Some(state.getint()),
                        },
                    };

                    let rendered = match directive.conversion {
                        Conversion::Char => {
                            let value = state.getchr();
                            format::render_directive(
                                state.output,
                                &directive,
                                fields,
                                FormatValue::Character(value),
                            )
                        }
                        Conversion::String => {
                            let value = state.getstr();
                            format::render_directive(
                                state.output,
                                &directive,
                                fields,
                                FormatValue::String(value),
                            )
                        }
                        Conversion::SignedDecimal | Conversion::SignedInteger => {
                            let value = state.getlong()?;
                            format::render_directive(
                                state.output,
                                &directive,
                                fields,
                                FormatValue::Signed(value),
                            )
                        }
                        Conversion::Octal
                        | Conversion::UnsignedDecimal
                        | Conversion::HexLower
                        | Conversion::HexUpper => {
                            let value = state.getulong()?;
                            format::render_directive(
                                state.output,
                                &directive,
                                fields,
                                FormatValue::Unsigned(value),
                            )
                        }
                        Conversion::HexFloatLower
                        | Conversion::HexFloatUpper
                        | Conversion::ScientificLower
                        | Conversion::ScientificUpper
                        | Conversion::FixedLower
                        | Conversion::FixedUpper
                        | Conversion::GeneralLower
                        | Conversion::GeneralUpper => {
                            let value = state.getdouble()?;
                            format::render_directive(
                                state.output,
                                &directive,
                                fields,
                                FormatValue::Float(value),
                            )
                        }
                    };
                    match rendered {
                        Ok(_) | Err(FormatError::RendererRejected) => {}
                        Err(FormatError::Io(error)) => return Err(RunError::Io(error)),
                        Err(FormatError::BadFormatString) => {
                            return state.invalid_directive(directive.original);
                        }
                        Err(FormatError::InternalInvariant) => {
                            return Err(RunError::InternalInvariant)
                        }
                    }
                    index = next;
                }
                b'\\' => {
                    let escaped = print_escape(&format[index..]);
                    if let Some(byte) = escaped.output {
                        state.write_stdout(&[byte])?;
                    }
                    if let Some(warning) = escaped.warning {
                        state.emit_escape_warning(warning)?;
                    }
                    index = index.saturating_add(1 + escaped.consumed);
                }
                _ => {
                    state.write_stdout(&format[index..index + 1])?;
                    index += 1;
                }
            }
        }

        if state.cursor.position() == pass_start || !state.cursor.has_remaining() {
            return Ok(RunOutcome { status: state.rval });
        }
    }
}

fn program_basename(program: &[u8]) -> &[u8] {
    program
        .iter()
        .rposition(|byte| *byte == b'/')
        .map(|index| &program[index + 1..])
        .unwrap_or(program)
}

#[cfg(test)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum OutputOperation {
    StdoutWrite,
    StderrWrite,
    StdoutFlush,
}

#[cfg(test)]
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum OutputEvent {
    Stdout(Vec<u8>),
    Stderr(Vec<u8>),
    Flush,
}

#[cfg(test)]
#[derive(Debug, Default)]
pub struct MockOutput {
    pub stdout: Vec<u8>,
    pub stderr: Vec<u8>,
    pub events: Vec<OutputEvent>,
    pub fail_on: Option<OutputOperation>,
}

#[cfg(test)]
impl Output for MockOutput {
    fn write_stdout(&mut self, bytes: &[u8]) -> io::Result<()> {
        self.events.push(OutputEvent::Stdout(bytes.to_vec()));
        if self.fail_on == Some(OutputOperation::StdoutWrite) {
            return Err(io::Error::new(
                io::ErrorKind::BrokenPipe,
                "injected stdout write failure",
            ));
        }
        self.stdout.extend_from_slice(bytes);
        Ok(())
    }

    fn write_stderr(&mut self, bytes: &[u8]) -> io::Result<()> {
        self.events.push(OutputEvent::Stderr(bytes.to_vec()));
        if self.fail_on == Some(OutputOperation::StderrWrite) {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "injected stderr write failure",
            ));
        }
        self.stderr.extend_from_slice(bytes);
        Ok(())
    }

    fn flush_stdout(&mut self) -> io::Result<()> {
        self.events.push(OutputEvent::Flush);
        if self.fail_on == Some(OutputOperation::StdoutFlush) {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "injected stdout flush failure",
            ));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        hextobin, isodigit, octtobin, print_escape, run, EscapeWarning, MockOutput, OutputEvent,
        OutputOperation, PrintfState, RunError, RunOutcome, USAGE,
    };
    use std::io;

    fn execute(args: &[&[u8]]) -> (RunOutcome, MockOutput) {
        let args = args
            .iter()
            .map(|argument| argument.to_vec())
            .collect::<Vec<_>>();
        let mut output = MockOutput::default();
        let outcome = run(&args, &mut output)
            .unwrap_or_else(|error| panic!("unexpected run error: {error:?}"));
        (outcome, output)
    }

    fn assert_command(
        args: &[&[u8]],
        expected_status: u8,
        expected_stdout: &[u8],
        expected_stderr: &[u8],
    ) {
        let (outcome, output) = execute(args);
        assert_eq!(outcome.status, expected_status, "status for {args:?}");
        assert_eq!(output.stdout, expected_stdout, "stdout for {args:?}");
        assert_eq!(output.stderr, expected_stderr, "stderr for {args:?}");
    }

    #[test]
    fn released_seed_vectors() {
        let cases = vec![
            (
                "escape_string_mixed",
                vec![b"%b".to_vec(), b"A\\nB\\tC".to_vec()],
                b"A\nB\tC".to_vec(),
            ),
            (
                "zero_unsigned",
                vec![b"%u".to_vec(), b"0".to_vec()],
                b"0".to_vec(),
            ),
            (
                "width_zero",
                vec![b"%*s".to_vec(), b"0".to_vec(), b"hello".to_vec()],
                b"hello".to_vec(),
            ),
            (
                "escape_string_hex",
                vec![b"%b".to_vec(), b"\\x41\\x42\\x43".to_vec()],
                b"ABC".to_vec(),
            ),
            (
                "empty_char_literal",
                vec![b"%d".to_vec(), b"''".to_vec()],
                b"39".to_vec(),
            ),
            ("vertical_tab_escape", vec![b"\\v".to_vec()], vec![0x0b]),
            ("single_quote_escape", vec![b"\\'".to_vec()], b"'".to_vec()),
            (
                "scientific_lower",
                vec![b"%e".to_vec(), b"123.456".to_vec()],
                b"1.234560e+02".to_vec(),
            ),
            (
                "zero_hex",
                vec![b"%x".to_vec(), b"0".to_vec()],
                b"0".to_vec(),
            ),
            (
                "field_width_arg",
                vec![b"%*s".to_vec(), b"7".to_vec(), b"hello".to_vec()],
                b"  hello".to_vec(),
            ),
            ("string_from_null", vec![b"%s".to_vec()], Vec::new()),
            (
                "width_precision_args",
                vec![
                    b"%*.*s".to_vec(),
                    b"4".to_vec(),
                    b"2".to_vec(),
                    b"hello".to_vec(),
                ],
                b"  he".to_vec(),
            ),
            ("int_no_arg", vec![b"%d".to_vec()], b"0".to_vec()),
            (
                "complex_b_octal",
                vec![b"%b".to_vec(), b"\\001\\002\\003".to_vec()],
                vec![1, 2, 3],
            ),
            (
                "format_reuse_insufficient",
                vec![b"%d %d".to_vec(), b"123".to_vec()],
                b"123 0".to_vec(),
            ),
        ];

        for (name, mut operands, expected) in cases {
            let mut args = vec![b"printf".to_vec()];
            args.append(&mut operands);
            let mut output = MockOutput::default();
            let outcome = run(&args, &mut output).unwrap_or_else(|error| {
                panic!("{name}: unexpected run error: {error:?}");
            });
            assert_eq!(outcome.status, 0, "{name}: status");
            assert_eq!(output.stdout, expected, "{name}: stdout");
            assert!(output.stderr.is_empty(), "{name}: stderr");
        }
    }

    #[test]
    fn process_shell_defaults_and_double_dash() {
        assert_command(&[], 1, b"", USAGE);
        assert_command(&[b"printf".as_slice()], 1, b"", USAGE);
        assert_command(&[b"printf".as_slice(), b"--".as_slice()], 1, b"", USAGE);
        assert_command(
            &[b"printf".as_slice(), b"--".as_slice(), b"%s".as_slice()],
            0,
            b"",
            b"",
        );
        assert_command(
            &[b"printf".as_slice(), b"--".as_slice(), b"--".as_slice()],
            0,
            b"--",
            b"",
        );
        assert_command(
            &[b"printf".as_slice(), b"literal\xff".as_slice()],
            0,
            b"literal\xff",
            b"",
        );
        assert_command(
            &[b"printf".as_slice(), b"100%% done".as_slice()],
            0,
            b"100% done",
            b"",
        );
        assert_command(&[b"printf".as_slice(), b"%s".as_slice()], 0, b"", b"");

        let operands = vec![Vec::new(), b"\xfftail".to_vec(), b"value".to_vec()];
        let mut output = MockOutput::default();
        let mut state = PrintfState::new(b"printf", &operands, &mut output);
        assert_eq!(state.getchr(), 0);
        assert_eq!(state.cursor.position(), 1);
        assert_eq!(state.getchr(), 0xff);
        assert_eq!(state.cursor.position(), 2);
        state.rval = 1;
        assert_eq!(state.getstr(), b"value");
        assert_eq!(state.rval, 1);
        assert_eq!(state.getchr(), 0);
        assert_eq!(state.getstr(), b"");
        assert_eq!(state.cursor.position(), 3);
    }

    #[test]
    fn raw_program_name_and_diagnostics() {
        assert_command(&[b"/usr/local/bin/not-printf".as_slice()], 1, b"", USAGE);
        assert_command(
            &[b"/usr/local/bin/not-printf".as_slice(), b"%".as_slice()],
            1,
            b"",
            b"not-printf: missing format character\n",
        );
        assert_command(
            &[b"/tmp/\xffprintf".as_slice(), b"%".as_slice()],
            1,
            b"",
            b"\xffprintf: missing format character\n",
        );
        assert_command(
            &[b"alias".as_slice(), b"%Q".as_slice()],
            1,
            b"",
            b"alias: %Q: invalid directive\n",
        );
        assert_command(
            &[b"".as_slice(), b"%".as_slice()],
            1,
            b"",
            b": missing format character\n",
        );
        assert_command(
            &[b"/path/ending/in/".as_slice(), b"%".as_slice()],
            1,
            b"",
            b": missing format character\n",
        );
    }

    #[test]
    fn format_reuse_tracks_operand_consumption() {
        assert_command(
            &[
                b"printf".as_slice(),
                b"%s".as_slice(),
                b"a".as_slice(),
                b"b".as_slice(),
                b"c".as_slice(),
            ],
            0,
            b"abc",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%s:%s".as_slice(),
                b"a".as_slice(),
                b"b".as_slice(),
                b"c".as_slice(),
            ],
            0,
            b"a:bc:",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%s%%".as_slice(),
                b"a".as_slice(),
                b"b".as_slice(),
            ],
            0,
            b"a%b%",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%s".as_slice(),
                b"".as_slice(),
                b"after-empty".as_slice(),
            ],
            0,
            b"after-empty",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"literal".as_slice(),
                b"ignored".as_slice(),
                b"also-ignored".as_slice(),
            ],
            0,
            b"literal",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%%".as_slice(),
                b"ignored".as_slice(),
            ],
            0,
            b"%",
            b"",
        );
        assert_command(
            &[b"printf".as_slice(), b"".as_slice(), b"ignored".as_slice()],
            0,
            b"",
            b"",
        );
    }

    #[test]
    fn escape_digit_helpers_are_ascii_only() {
        for (value, byte) in (b'0'..=b'7').enumerate() {
            assert!(isodigit(byte));
            assert_eq!(octtobin(byte), value as u8);
        }
        for byte in [0, b'/', b'8', b'9', b'a', 0x80, 0xff] {
            assert!(!isodigit(byte), "{byte:#04x} is not an octal digit");
        }

        for (byte, value) in [
            (b'0', 0),
            (b'9', 9),
            (b'A', 10),
            (b'F', 15),
            (b'a', 10),
            (b'f', 15),
        ] {
            assert_eq!(hextobin(byte), value);
        }
    }

    #[test]
    fn standard_escape_matrix() {
        let cases: &[(&str, &[u8], usize, Option<u8>, Option<EscapeWarning>)] = &[
            ("backslash", b"\\\\tail", 1, Some(b'\\'), None),
            ("single_quote", b"\\'tail", 1, Some(b'\''), None),
            ("double_quote", b"\\\"tail", 1, Some(b'"'), None),
            ("alert", b"\\a", 1, Some(0x07), None),
            ("backspace", b"\\b", 1, Some(0x08), None),
            ("escape", b"\\e", 1, Some(0x1b), None),
            ("form_feed", b"\\f", 1, Some(0x0c), None),
            ("newline", b"\\n", 1, Some(b'\n'), None),
            ("carriage_return", b"\\r", 1, Some(b'\r'), None),
            ("tab", b"\\t", 1, Some(b'\t'), None),
            ("vertical_tab", b"\\v", 1, Some(0x0b), None),
            ("octal_zero", b"\\0Z", 1, Some(0), None),
            ("octal_one_digit", b"\\7Z", 1, Some(0o7), None),
            ("octal_two_digits", b"\\12Z", 2, Some(0o12), None),
            ("octal_three_digits", b"\\1234", 3, Some(0o123), None),
            ("octal_low_byte", b"\\777", 3, Some(0xff), None),
            ("hex_zero_digits", b"\\xZ", 1, Some(0), None),
            ("hex_one_digit", b"\\x4Z", 2, Some(0x04), None),
            ("hex_two_digits", b"\\xAfZ", 3, Some(0xaf), None),
            (
                "null_sequence",
                b"\\",
                0,
                None,
                Some(EscapeWarning::NullSequence),
            ),
            (
                "unknown",
                b"\\c",
                1,
                Some(b'c'),
                Some(EscapeWarning::Unknown(b'c')),
            ),
            (
                "unknown_raw_byte",
                b"\\\xfftail",
                1,
                Some(0xff),
                Some(EscapeWarning::Unknown(0xff)),
            ),
        ];

        for &(name, input, consumed, output, warning) in cases {
            let actual = print_escape(input);
            assert_eq!(actual.consumed, consumed, "{name}: consumed");
            assert_eq!(actual.output, output, "{name}: output");
            assert_eq!(actual.warning, warning, "{name}: warning");
        }

        assert_command(
            &[
                b"printf".as_slice(),
                b"\\a\\b\\e\\f\\n\\r\\t\\v\\\\\\'\\\"".as_slice(),
            ],
            0,
            b"\x07\x08\x1b\x0c\n\r\t\x0b\\'\"",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"\\7|\\12|\\1234|\\777|\\x|\\x4|\\x4A!".as_slice(),
            ],
            0,
            b"\x07|\x0a|S4|\xff|\x00|\x04|J!",
            b"",
        );
        assert_command(
            &[b"printf".as_slice(), b"\\cstill\\".as_slice()],
            1,
            b"cstill",
            b"printf: unknown escape sequence `\\c'\nprintf: null escape sequence\n",
        );
        assert_command(
            &[b"printf".as_slice(), b"\\\xff".as_slice()],
            1,
            b"\xff",
            b"printf: unknown escape sequence `\\\xff'\n",
        );
    }

    #[test]
    fn percent_b_octal_and_stop_control() {
        let cases: &[(&str, &[u8], &[u8])] = &[
            ("marker_without_digit", b"\\0", b"\x00"),
            ("marker_then_non_octal", b"\\08", b"\x008"),
            ("marker_plus_one_digit", b"\\07", b"\x07"),
            ("marker_plus_two_digits", b"\\012", b"\x0a"),
            ("marker_plus_three_digits", b"\\0123", b"S"),
            ("marker_stops_after_three_digits", b"\\01234", b"S4"),
            ("marker_low_byte", b"\\0777", b"\xff"),
            ("marker_plus_three_zeroes", b"\\0000", b"\x00"),
            ("ordinary_octal_still_uses_three_digits", b"\\1234", b"S4"),
        ];

        for &(name, value, expected) in cases {
            let (outcome, output) = execute(&[b"printf".as_slice(), b"%b".as_slice(), value]);
            assert_eq!(outcome.status, 0, "{name}: status");
            assert_eq!(output.stdout, expected, "{name}: stdout");
            assert!(output.stderr.is_empty(), "{name}: stderr");
        }

        assert_command(
            &[b"printf".as_slice(), b"\\0123".as_slice()],
            0,
            b"\x0a3",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%b:unreached:%s".as_slice(),
                b"before\\cafter".as_slice(),
                b"unused".as_slice(),
                b"unused-second-pass".as_slice(),
            ],
            0,
            b"before",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%b:unreached:%s".as_slice(),
                b"\\qbefore\\cafter".as_slice(),
                b"unused".as_slice(),
                b"unused-second-pass".as_slice(),
            ],
            1,
            b"qbefore",
            b"printf: unknown escape sequence `\\q'\n",
        );
    }

    #[test]
    fn star_cursor_and_fatal_directives() {
        assert_command(
            &[b"printf".as_slice(), b"%*s".as_slice(), b"oops".as_slice()],
            0,
            b"oops",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%.*s:%s".as_slice(),
                b"oops".as_slice(),
                b"tail".as_slice(),
            ],
            0,
            b":tail",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%*.*s:%s".as_slice(),
                b"5".as_slice(),
                b"oops".as_slice(),
                b"tail".as_slice(),
            ],
            0,
            b"     :tail",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%*s:%s".as_slice(),
                b"".as_slice(),
                b"first".as_slice(),
                b"second".as_slice(),
            ],
            0,
            b"first:second",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%*s".as_slice(),
                b".".as_slice(),
                b"value".as_slice(),
            ],
            0,
            b"value",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%*s".as_slice(),
                b"3junk".as_slice(),
                b"x".as_slice(),
            ],
            0,
            b"  x",
            b"",
        );

        for format in [
            b"%".as_slice(),
            b"%#-+ 0".as_slice(),
            b"%123".as_slice(),
            b"%*123".as_slice(),
            b"%.".as_slice(),
            b"%.123".as_slice(),
            b"%.*123".as_slice(),
            b"%12.*".as_slice(),
        ] {
            assert_command(
                &[
                    b"/usr/bin/printf".as_slice(),
                    format,
                    b"4".as_slice(),
                    b"value".as_slice(),
                ],
                1,
                b"",
                b"printf: missing format character\n",
            );
        }

        for (format, diagnostic) in [
            (
                b"%Qtail".as_slice(),
                b"printf: %Q: invalid directive\n".as_slice(),
            ),
            (
                b"%#12Qtail".as_slice(),
                b"printf: %#12Q: invalid directive\n".as_slice(),
            ),
            (
                b"%*12Qtail".as_slice(),
                b"printf: %*12Q: invalid directive\n".as_slice(),
            ),
            (
                b"%.*12Qtail".as_slice(),
                b"printf: %.*12Q: invalid directive\n".as_slice(),
            ),
            (
                b"%ls".as_slice(),
                b"printf: %l: invalid directive\n".as_slice(),
            ),
            (
                b"%5b".as_slice(),
                b"printf: %5b: invalid directive\n".as_slice(),
            ),
            (
                b"%\xfftail".as_slice(),
                b"printf: %\xff: invalid directive\n".as_slice(),
            ),
        ] {
            assert_command(
                &[
                    b"printf".as_slice(),
                    format,
                    b"4".as_slice(),
                    b"value".as_slice(),
                ],
                1,
                b"",
                diagnostic,
            );
        }

        assert_command(
            &[b"printf".as_slice(), b"before:%#Qafter".as_slice()],
            1,
            b"before:",
            b"printf: %#Q: invalid directive\n",
        );
    }

    #[test]
    fn sticky_conversion_warning_status() {
        assert_command(
            &[
                b"printf".as_slice(),
                b"%d".as_slice(),
                b"not-a-number".as_slice(),
            ],
            1,
            b"0",
            b"printf: not-a-number: expected numeric value\n",
        );
        assert_command(
            &[b"alias".as_slice(), b"%u".as_slice(), b"12tail".as_slice()],
            1,
            b"12",
            b"alias: 12tail: not completely converted\n",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%d".as_slice(),
                b"9223372036854775808".as_slice(),
            ],
            1,
            b"9223372036854775807",
            b"printf: 9223372036854775808: Numerical result out of range\n",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%d".as_slice(),
                b"-9223372036854775809".as_slice(),
            ],
            1,
            b"-9223372036854775808",
            b"printf: -9223372036854775809: Numerical result out of range\n",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%u".as_slice(),
                b"18446744073709551616".as_slice(),
            ],
            1,
            b"18446744073709551615",
            b"printf: 18446744073709551616: Numerical result out of range\n",
        );

        // A trailing byte takes precedence over ERANGE, as in check_conversion.
        assert_command(
            &[
                b"printf".as_slice(),
                b"%x".as_slice(),
                b"18446744073709551616tail".as_slice(),
            ],
            1,
            b"ffffffffffffffff",
            b"printf: 18446744073709551616tail: not completely converted\n",
        );

        assert_command(
            &[b"printf".as_slice(), b"%g".as_slice(), b"oops".as_slice()],
            1,
            b"0",
            b"printf: oops: expected numeric value\n",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%a".as_slice(),
                b"0x1p2tail".as_slice(),
            ],
            1,
            b"0x1p+2",
            b"printf: 0x1p2tail: not completely converted\n",
        );
        assert_command(
            &[b"printf".as_slice(), b"%g".as_slice(), b"1e309".as_slice()],
            1,
            b"inf",
            b"printf: 1e309: Numerical result out of range\n",
        );
        assert_command(
            &[b"printf".as_slice(), b"%a".as_slice(), b"5e-324".as_slice()],
            1,
            b"0x0.0000000000001p-1022",
            b"printf: 5e-324: Numerical result out of range\n",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%a".as_slice(),
                b"0x1p-1074".as_slice(),
            ],
            0,
            b"0x0.0000000000001p-1022",
            b"",
        );

        // A trailing byte also masks floating-point ERANGE.
        assert_command(
            &[
                b"printf".as_slice(),
                b"%a".as_slice(),
                b"0x1p-1075tail".as_slice(),
            ],
            1,
            b"0x0p+0",
            b"printf: 0x1p-1075tail: not completely converted\n",
        );

        // Empty, missing, and quoted operands bypass conversion warnings.
        assert_command(
            &[b"printf".as_slice(), b"%d".as_slice(), b"".as_slice()],
            0,
            b"0",
            b"",
        );
        assert_command(&[b"printf".as_slice(), b"%d".as_slice()], 0, b"0", b"");
        assert_command(
            &[
                b"printf".as_slice(),
                b"%d".as_slice(),
                b"'Aignored".as_slice(),
            ],
            0,
            b"65",
            b"",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%f".as_slice(),
                b"'Aignored".as_slice(),
            ],
            0,
            b"65.000000",
            b"",
        );

        assert_command(
            &[
                b"printf".as_slice(),
                b"%d|%u|%x|%i".as_slice(),
                b"oops".as_slice(),
                b"12tail".as_slice(),
                b"18446744073709551616".as_slice(),
                b"7".as_slice(),
            ],
            1,
            b"0|12|ffffffffffffffff|7",
            b"printf: oops: expected numeric value\n\
              printf: 12tail: not completely converted\n\
              printf: 18446744073709551616: Numerical result out of range\n",
        );
        assert_command(
            &[
                b"printf".as_slice(),
                b"%d,".as_slice(),
                b"1tail".as_slice(),
                b"2".as_slice(),
            ],
            1,
            b"1,2,",
            b"printf: 1tail: not completely converted\n",
        );
        assert_command(
            &[
                b"/tmp/raw-\xff".as_slice(),
                b"%d".as_slice(),
                b"\xff".as_slice(),
            ],
            1,
            b"0",
            b"raw-\xff: \xff: expected numeric value\n",
        );
    }

    #[test]
    fn output_mock_channels_order_flush_and_failures() {
        let warning = b"printf: unknown escape sequence `\\q'\n";
        let args = vec![b"printf".to_vec(), b"X\\q".to_vec()];
        let mut output = MockOutput::default();
        let outcome = run(&args, &mut output).expect("warning command");
        assert_eq!(outcome.status, 1);
        assert_eq!(output.stdout, b"Xq");
        assert_eq!(output.stderr, warning);
        assert_eq!(
            output.events,
            vec![
                OutputEvent::Stdout(b"X".to_vec()),
                OutputEvent::Stdout(b"q".to_vec()),
                OutputEvent::Stderr(warning.to_vec()),
                OutputEvent::Flush,
            ]
        );

        let exit_paths: &[(&str, &[&[u8]], u8)] = &[
            ("clean", &[b"printf", b"ok"], 0),
            ("usage", &[b"printf"], 1),
            ("missing directive", &[b"printf", b"%"], 1),
            ("invalid directive", &[b"printf", b"A%Q"], 1),
            ("percent-b stop", &[b"printf", b"%b", b"before\\cafter"], 0),
            ("renderer", &[b"printf", b"%d", b"7"], 0),
            (
                "oversized directive",
                &[
                    b"printf",
                    b"%999999999999999999999999999999999999sZ",
                    b"value",
                ],
                0,
            ),
        ];
        for &(name, raw_args, expected_status) in exit_paths {
            let args = raw_args
                .iter()
                .map(|argument| argument.to_vec())
                .collect::<Vec<_>>();
            let mut output = MockOutput::default();
            let outcome = run(&args, &mut output)
                .unwrap_or_else(|error| panic!("{name}: unexpected error: {error:?}"));
            assert_eq!(outcome.status, expected_status, "{name}: status");
            assert_eq!(
                output
                    .events
                    .iter()
                    .filter(|event| **event == OutputEvent::Flush)
                    .count(),
                1,
                "{name}: flush count"
            );
            assert_eq!(output.events.last(), Some(&OutputEvent::Flush), "{name}");
        }

        let assert_io_kind =
            |result: Result<RunOutcome, RunError>, expected: io::ErrorKind, context: &str| {
                match result {
                    Err(RunError::Io(error)) => assert_eq!(error.kind(), expected, "{context}"),
                    other => panic!("{context}: expected I/O error, got {other:?}"),
                }
            };

        let args = vec![b"printf".to_vec(), b"AB".to_vec()];
        let mut output = MockOutput {
            fail_on: Some(OutputOperation::StdoutWrite),
            ..MockOutput::default()
        };
        assert_io_kind(
            run(&args, &mut output),
            io::ErrorKind::BrokenPipe,
            "broken stdout",
        );
        assert!(output.stdout.is_empty());
        assert!(output.stderr.is_empty());
        assert_eq!(
            output.events,
            vec![OutputEvent::Stdout(b"A".to_vec()), OutputEvent::Flush]
        );

        let args = vec![b"printf".to_vec(), b"X\\qY".to_vec()];
        let mut output = MockOutput {
            fail_on: Some(OutputOperation::StderrWrite),
            ..MockOutput::default()
        };
        assert_io_kind(
            run(&args, &mut output),
            io::ErrorKind::Other,
            "failed warning",
        );
        assert_eq!(output.stdout, b"Xq");
        assert!(output.stderr.is_empty());
        assert_eq!(
            output.events,
            vec![
                OutputEvent::Stdout(b"X".to_vec()),
                OutputEvent::Stdout(b"q".to_vec()),
                OutputEvent::Stderr(warning.to_vec()),
                OutputEvent::Flush,
            ]
        );

        let args = vec![b"printf".to_vec(), b"OK".to_vec()];
        let mut output = MockOutput {
            fail_on: Some(OutputOperation::StdoutFlush),
            ..MockOutput::default()
        };
        assert_io_kind(
            run(&args, &mut output),
            io::ErrorKind::Other,
            "failed flush",
        );
        assert_eq!(output.stdout, b"OK");
        assert!(output.stderr.is_empty());
        assert_eq!(
            output.events,
            vec![
                OutputEvent::Stdout(b"O".to_vec()),
                OutputEvent::Stdout(b"K".to_vec()),
                OutputEvent::Flush,
            ]
        );
    }
}
