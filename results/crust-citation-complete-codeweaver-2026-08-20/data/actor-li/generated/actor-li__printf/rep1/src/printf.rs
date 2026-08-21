use crate::format::{self, Directive, DirectiveErrorKind, Field, ResolvedDirective, Value};
use crate::number::{self, Parsed, RangeState};
use std::io::{self, Write};

pub(crate) const USAGE: &[u8] = b"usage: printf format [argument ...]\n";
pub(crate) const STDOUT_BUFFER_SIZE: usize = 4096;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExitStatus {
    Success,
    Failure,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum RunControl {
    Continue,
    Stop,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BufferMode {
    Full,
    Line,
}

pub struct CStdout<W: Write> {
    inner: W,
    buffer: Vec<u8>,
    mode: BufferMode,
}

impl<W: Write> CStdout<W> {
    pub fn new(inner: W, mode: BufferMode) -> Self {
        Self {
            inner,
            buffer: Vec::with_capacity(STDOUT_BUFFER_SIZE),
            mode,
        }
    }

    pub fn finish(mut self) -> io::Result<W> {
        self.flush()?;
        Ok(self.inner)
    }

    fn write_buffered(&mut self, mut bytes: &[u8]) -> io::Result<()> {
        while !bytes.is_empty() {
            let available = STDOUT_BUFFER_SIZE - self.buffer.len();
            let count = available.min(bytes.len());
            self.buffer.extend_from_slice(&bytes[..count]);
            bytes = &bytes[count..];
            if self.buffer.len() == STDOUT_BUFFER_SIZE {
                self.flush_buffer()?;
            }
        }
        Ok(())
    }

    fn flush_buffer(&mut self) -> io::Result<()> {
        let mut written = 0;
        while written < self.buffer.len() {
            match self.inner.write(&self.buffer[written..]) {
                Ok(0) => {
                    if written != 0 {
                        self.buffer.drain(..written);
                    }
                    return Err(io::Error::new(
                        io::ErrorKind::WriteZero,
                        "failed to flush stdout buffer",
                    ));
                }
                Ok(count) if count <= self.buffer.len() - written => {
                    written += count;
                }
                Ok(_) => {
                    if written != 0 {
                        self.buffer.drain(..written);
                    }
                    return Err(io::Error::new(
                        io::ErrorKind::InvalidData,
                        "stdout writer returned an invalid byte count",
                    ));
                }
                Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
                Err(error) => {
                    if written != 0 {
                        self.buffer.drain(..written);
                    }
                    return Err(error);
                }
            }
        }
        self.buffer.clear();
        Ok(())
    }
}

impl<W: Write> Write for CStdout<W> {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        match self.mode {
            BufferMode::Full => self.write_buffered(bytes)?,
            BufferMode::Line => {
                for segment in bytes.split_inclusive(|byte| *byte == b'\n') {
                    self.write_buffered(segment)?;
                    if segment.last() == Some(&b'\n') {
                        self.flush_buffer()?;
                        self.inner.flush()?;
                    }
                }
            }
        }
        Ok(bytes.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        self.flush_buffer()?;
        self.inner.flush()
    }
}

pub(crate) struct Engine<'args, 'io, O: Write + ?Sized, E: Write + ?Sized> {
    args: &'args [&'args [u8]],
    initial_argument_index: usize,
    argument_index: usize,
    program_name: &'args [u8],
    status: ExitStatus,
    stdout: &'io mut O,
    stderr: &'io mut E,
}

impl<'args, 'io, O: Write + ?Sized, E: Write + ?Sized> Engine<'args, 'io, O, E> {
    pub(crate) fn new(
        args: &'args [&'args [u8]],
        initial_argument_index: usize,
        program_name: &'args [u8],
        stdout: &'io mut O,
        stderr: &'io mut E,
    ) -> Self {
        Self {
            args,
            initial_argument_index,
            argument_index: initial_argument_index,
            program_name,
            status: ExitStatus::Success,
            stdout,
            stderr,
        }
    }

    pub(crate) fn run_format(&mut self, format: &[u8]) -> io::Result<RunControl> {
        loop {
            let mut index = 0;
            while index < format.len() {
                match format[index] {
                    b'%' if format.get(index + 1) == Some(&b'%') => {
                        self.stdout.write_all(b"%")?;
                        index += 2;
                    }
                    b'%' if format.get(index + 1) == Some(&b'b') => {
                        let value = self.getstr();
                        if self.print_escape_str(value)? == RunControl::Stop {
                            return Ok(RunControl::Stop);
                        }
                        index += 2;
                    }
                    b'%' => match format::parse(format, index) {
                        Ok(parsed) => {
                            index = parsed.next_index;
                            if self.render_directive(parsed.directive)? == RunControl::Stop {
                                return Ok(RunControl::Stop);
                            }
                        }
                        Err(error) => {
                            self.status = ExitStatus::Failure;
                            match error.kind {
                                DirectiveErrorKind::MissingFormatCharacter => {
                                    self.warnx(&[b"missing format character"])?;
                                }
                                DirectiveErrorKind::InvalidDirective => {
                                    self.warnx(&[&format[error.span], b": invalid directive"])?;
                                }
                            }
                            return Ok(RunControl::Stop);
                        }
                    },
                    b'\\' => {
                        let consumed = self.print_escape(format, index)?;
                        index += consumed + 1;
                    }
                    byte => {
                        self.stdout.write_all(&[byte])?;
                        index += 1;
                    }
                }
            }

            if self.should_repeat_format() {
                continue;
            }
            return Ok(RunControl::Continue);
        }
    }

    fn should_repeat_format(&self) -> bool {
        self.argument_index > self.initial_argument_index && self.argument_index < self.args.len()
    }

    pub(crate) fn render_directive(&mut self, directive: Directive) -> io::Result<RunControl> {
        let dynamic_width = if directive.width == Field::Dynamic {
            Some(self.getint())
        } else {
            None
        };
        let dynamic_precision = if directive.precision == Field::Dynamic {
            Some(self.getint())
        } else {
            None
        };
        let directive = format::resolve(directive, dynamic_width, dynamic_precision);

        match directive.conversion {
            b'c' => {
                let value = self.getchr();
                self.render_value(&directive, Value::Character(value))?;
            }
            b's' => {
                let value = self.getstr();
                format::render(self.stdout, &directive, Value::String(value))?;
            }
            b'd' | b'i' => {
                let value = self.getlong()?;
                self.render_value(&directive, Value::Signed(value))?;
            }
            b'o' | b'u' | b'x' | b'X' => {
                let value = self.getulong()?;
                self.render_value(&directive, Value::Unsigned(value))?;
            }
            b'a' | b'A' | b'e' | b'E' | b'f' | b'F' | b'g' | b'G' => {
                let value = self.getdouble()?;
                self.render_value(&directive, Value::Float(value))?;
            }
            _ => {
                self.status = ExitStatus::Failure;
                self.warnx(&[&self.args[0][0..0], b"invalid directive"])?;
                return Ok(RunControl::Stop);
            }
        }
        Ok(RunControl::Continue)
    }

    pub(crate) fn render_value(
        &mut self,
        directive: &ResolvedDirective,
        value: Value<'_>,
    ) -> io::Result<()> {
        format::render(self.stdout, directive, value)
    }

    pub(crate) fn print_escape_str(&mut self, bytes: &[u8]) -> io::Result<RunControl> {
        let mut remaining = bytes;
        while let Some((&byte, tail)) = remaining.split_first() {
            if byte != b'\\' {
                self.stdout.write_all(&[byte])?;
                remaining = tail;
                continue;
            }

            match tail.first() {
                Some(b'0') => {
                    let after_marker = &tail[1..];
                    let mut value = 0_u16;
                    let mut digits = 0;
                    for &digit in after_marker
                        .iter()
                        .take(3)
                        .take_while(|digit| number::isodigit(**digit))
                    {
                        value = (value << 3) + u16::from(number::octtobin(digit));
                        digits += 1;
                    }
                    self.stdout.write_all(&[(value & 0xff) as u8])?;
                    remaining = &after_marker[digits..];
                }
                Some(b'c') => return Ok(RunControl::Stop),
                _ => {
                    let consumed = self.print_escape(remaining, 0)?;
                    remaining = &remaining[consumed + 1..];
                }
            }
        }
        Ok(RunControl::Continue)
    }

    pub(crate) fn print_escape(&mut self, format: &[u8], slash_index: usize) -> io::Result<usize> {
        let escaped_bytes = format
            .get(slash_index..)
            .and_then(|tail| tail.get(1..))
            .unwrap_or_default();
        let Some((&escaped, following)) = escaped_bytes.split_first() else {
            self.status = ExitStatus::Failure;
            self.warnx(&[b"null escape sequence"])?;
            return Ok(0);
        };

        if number::isodigit(escaped) {
            let mut value = 0_u16;
            let mut digits = 0;
            for &byte in escaped_bytes
                .iter()
                .take(3)
                .take_while(|byte| number::isodigit(**byte))
            {
                value = (value << 3) + u16::from(number::octtobin(byte));
                digits += 1;
            }
            self.stdout.write_all(&[(value & 0xff) as u8])?;
            return Ok(digits);
        }

        if escaped == b'x' {
            let mut value = 0_u8;
            let mut digits = 0;
            for &byte in following
                .iter()
                .take(2)
                .take_while(|byte| byte.is_ascii_hexdigit())
            {
                value = (value << 4).wrapping_add(number::hextobin(byte));
                digits += 1;
            }
            self.stdout.write_all(&[value])?;
            return Ok(1 + digits);
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
            byte => {
                self.stdout.write_all(&[byte])?;
                self.status = ExitStatus::Failure;
                let byte = [byte];
                self.warnx(&[b"unknown escape sequence `\\", &byte, b"'"])?;
                return Ok(1);
            }
        };
        self.stdout.write_all(&[output])?;
        Ok(1)
    }

    pub(crate) fn getchr(&mut self) -> u8 {
        let Some(value) = self.args.get(self.argument_index).copied() else {
            return 0;
        };
        self.argument_index += 1;
        value.first().copied().unwrap_or(0)
    }

    pub(crate) fn getstr(&mut self) -> &'args [u8] {
        let Some(value) = self.args.get(self.argument_index).copied() else {
            return b"";
        };
        self.argument_index += 1;
        value
    }

    pub(crate) fn getint(&mut self) -> i32 {
        let Some(value) = self.args.get(self.argument_index).copied() else {
            return 0;
        };
        if number::getint_consumes(value) {
            self.argument_index += 1;
            number::parse_getint(value)
        } else {
            0
        }
    }

    pub(crate) fn getlong(&mut self) -> io::Result<i64> {
        let Some(source) = self.args.get(self.argument_index).copied() else {
            return Ok(0);
        };
        self.argument_index += 1;
        if let Some(value) = number::quote_value(source) {
            return Ok(i64::from(value));
        }
        let parsed = number::parse_long(source);
        self.check_conversion(source, &parsed)?;
        Ok(parsed.value)
    }

    pub(crate) fn getulong(&mut self) -> io::Result<u64> {
        let Some(source) = self.args.get(self.argument_index).copied() else {
            return Ok(0);
        };
        self.argument_index += 1;
        if let Some(value) = number::quote_value(source) {
            return Ok(u64::from(value));
        }
        let parsed = number::parse_ulong(source);
        self.check_conversion(source, &parsed)?;
        Ok(parsed.value)
    }

    pub(crate) fn getdouble(&mut self) -> io::Result<f64> {
        let Some(source) = self.args.get(self.argument_index).copied() else {
            return Ok(0.0);
        };
        self.argument_index += 1;
        if let Some(value) = number::quote_value(source) {
            return Ok(f64::from(value));
        }
        let parsed = number::parse_double(source);
        self.check_conversion(source, &parsed)?;
        Ok(parsed.value)
    }

    pub(crate) fn check_conversion<T>(
        &mut self,
        source: &[u8],
        parsed: &Parsed<T>,
    ) -> io::Result<()> {
        let warning = if source.get(parsed.end).copied().unwrap_or(0) != 0 {
            Some(if parsed.converted {
                b": not completely converted".as_slice()
            } else {
                b": expected numeric value".as_slice()
            })
        } else if parsed.range != RangeState::InRange {
            Some(b": Numerical result out of range".as_slice())
        } else {
            None
        };
        if let Some(warning) = warning {
            let displayed_source = source.split(|byte| *byte == 0).next().unwrap_or_default();
            self.warnx(&[displayed_source, warning])?;
            self.status = ExitStatus::Failure;
        }
        Ok(())
    }

    pub(crate) fn warnx(&mut self, fragments: &[&[u8]]) -> io::Result<()> {
        self.stderr.write_all(self.program_name)?;
        self.stderr.write_all(b": ")?;
        for fragment in fragments {
            self.stderr.write_all(fragment)?;
        }
        self.stderr.write_all(b"\n")?;
        self.stderr.flush()
    }
}

pub(crate) fn program_name(argv0: &[u8]) -> &[u8] {
    argv0.rsplit(|byte| *byte == b'/').next().unwrap_or(argv0)
}

pub(crate) fn usage<E: Write + ?Sized>(stderr: &mut E) -> io::Result<ExitStatus> {
    stderr.write_all(USAGE)?;
    stderr.flush()?;
    Ok(ExitStatus::Failure)
}

pub fn run<O: Write + ?Sized, E: Write + ?Sized>(
    args: &[&[u8]],
    stdout: &mut O,
    stderr: &mut E,
) -> io::Result<ExitStatus> {
    let argv0 = args.first().copied().unwrap_or(b"printf");
    let mut format_index = 1;
    if args.get(format_index) == Some(&b"--".as_slice()) {
        format_index += 1;
    }
    let Some(format) = args.get(format_index).copied() else {
        let usage_result = usage(stderr);
        let flush_result = stdout.flush();
        let status = usage_result?;
        flush_result?;
        return Ok(status);
    };
    let initial_argument_index = format_index + 1;
    let mut engine = Engine::new(
        args,
        initial_argument_index,
        program_name(argv0),
        stdout,
        stderr,
    );
    let run_result = engine.run_format(format);
    let status = engine.status;
    let flush_result = engine.stdout.flush();
    run_result?;
    flush_result?;
    Ok(status)
}

#[cfg(test)]
mod tests {
    use super::{run, BufferMode, CStdout, Engine, ExitStatus};
    use crate::test_support::{FailAfterWriter, MockWriter, RecordingWriter, Stream};

    #[test]
    fn command_and_writer_test_seams_are_wired() {
        let _ = (
            MockWriter::default(),
            FailAfterWriter::new(0),
            RecordingWriter::new(Stream::Stdout),
            RecordingWriter::new(Stream::Stderr),
        );
    }

    mod dynamic_dimension_cases {
        use super::{assert_case, capture, Engine, ExitStatus, MockWriter};

        #[test]
        fn getint_consumes_accepted_operands_and_retains_rejected_ones() {
            let accepted: &[(&[u8], i32)] = &[
                (b"", 0),
                (b"\0ignored", 0),
                (b".", 0),
                (b"+", 0),
                (b"-", 0),
                (b"0x10", 0),
                (b"12tail", 12),
                (b"-7tail", -7),
                (b"4294967298tail", 2),
            ];
            for &(operand, expected) in accepted {
                let operands = [operand, b"next".as_slice()];
                let (value, next, stderr) = getint_then_getstr(&operands);
                assert_eq!(value, expected, "{operand:?}");
                assert_eq!(next, b"next", "{operand:?}");
                assert!(stderr.is_empty(), "{operand:?}");
            }

            for &operand in &[b" 3".as_slice(), b"\t4", b"x5", b"\xff"] {
                let operands = [operand, b"next".as_slice()];
                let (value, next, stderr) = getint_then_getstr(&operands);
                assert_eq!(value, 0, "{operand:?}");
                assert_eq!(next, operand, "{operand:?}");
                assert!(stderr.is_empty(), "{operand:?}");
            }
        }

        #[test]
        fn missing_getint_value_is_zero_without_advancing() {
            let operands: [&[u8]; 0] = [];
            let (value, next, stderr) = getint_then_getstr(&operands);
            assert_eq!(value, 0);
            assert!(next.is_empty());
            assert!(stderr.is_empty());
        }

        #[test]
        fn width_and_precision_stars_use_decimal_prefixes_in_source_order() {
            let (status, stdout, stderr, _, _) =
                capture(&[b"printf", b"[%*.*s]", b"6tail", b"3suffix", b"abcdef"]);

            assert_eq!(status, ExitStatus::Success);
            assert_eq!(stdout, b"[   abc]");
            assert!(stderr.is_empty());
        }

        #[test]
        fn negative_and_missing_dynamic_dimensions_follow_printf_defaults() {
            assert_case(&[b"printf", b"[%*.*s]", b"-6", b"-1", b"abc"], b"[abc   ]");
            assert_case(&[b"printf", b"<%*s><%.*s><%*.*s>"], b"<><><>");
        }

        fn getint_then_getstr<'a>(operands: &'a [&'a [u8]]) -> (i32, &'a [u8], Vec<u8>) {
            let mut stdout = MockWriter::default();
            let mut stderr = MockWriter::default();
            let mut engine = Engine::new(operands, 0, b"printf", &mut stdout, &mut stderr);
            let value = engine.getint();
            let next = engine.getstr();
            drop(engine);
            (value, next, stderr.bytes)
        }
    }

    mod escape_cases {
        use super::{arg, assert_case, capture, ExitStatus};

        #[test]
        fn expands_every_direct_named_escape() {
            let cases: &[(&[u8], &[u8])] = &[
                (b"\\\\", b"\\"),
                (b"\\'", b"'"),
                (b"\\\"", b"\""),
                (b"\\a", b"\x07"),
                (b"\\b", b"\x08"),
                (b"\\e", b"\x1b"),
                (b"\\f", b"\x0c"),
                (b"\\n", b"\n"),
                (b"\\r", b"\r"),
                (b"\\t", b"\t"),
                (b"\\v", b"\x0b"),
            ];

            for &(format, expected) in cases {
                assert_case(&[b"printf", format], expected);
            }
        }

        #[test]
        fn direct_octal_and_hex_escapes_obey_digit_limits() {
            let cases: &[(&[u8], &[u8])] = &[
                (b"\\0", b"\0"),
                (b"\\07", b"\x07"),
                (b"\\077", b"?"),
                (b"\\0777", b"?7"),
                (b"\\400", b"\0"),
                (b"\\777", b"\xff"),
                (b"\\x", b"\0"),
                (b"\\xA", b"\x0a"),
                (b"\\x41", b"A"),
                (b"\\x414", b"A4"),
                (b"\\x80", b"\x80"),
                (b"\\xff", b"\xff"),
            ];

            for &(format, expected) in cases {
                assert_case(&[b"printf", format], expected);
            }
        }

        #[test]
        fn direct_unknown_and_trailing_escapes_warn_exactly() {
            let (status, stdout, stderr, stdout_flushes, stderr_flushes) =
                capture(&[b"/tmp/raw-\xff", b"A\\qZ"]);
            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"AqZ");
            assert_eq!(stderr, b"raw-\xff: unknown escape sequence `\\q'\n");
            assert_eq!(stdout_flushes, 1);
            assert_eq!(stderr_flushes, 1);

            let (status, stdout, stderr, _, _) = capture(&[b"printf", b"before\\"]);
            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"before");
            assert_eq!(stderr, b"printf: null escape sequence\n");
        }

        #[test]
        fn direct_backslash_c_is_unknown_and_does_not_stop_later_output() {
            let (status, stdout, stderr, _, _) = capture(&[b"printf", b"before\\c:%s", b"after"]);
            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"beforec:after");
            assert_eq!(stderr, b"printf: unknown escape sequence `\\c'\n");
        }

        #[test]
        fn percent_b_expands_named_octal_hex_and_raw_high_bytes() {
            let named_cases: &[(&[u8], &[u8])] = &[
                (b"\\\\", b"\\"),
                (b"\\'", b"'"),
                (b"\\\"", b"\""),
                (b"\\a", b"\x07"),
                (b"\\b", b"\x08"),
                (b"\\e", b"\x1b"),
                (b"\\f", b"\x0c"),
                (b"\\n", b"\n"),
                (b"\\r", b"\r"),
                (b"\\t", b"\t"),
                (b"\\v", b"\x0b"),
                (b"\\x", b"\0"),
                (b"\\x80", b"\x80"),
                (b"\\0", b"\0"),
                (b"\\0777", b"\xff"),
                (b"\\0000", b"\0"),
                (b"\\777", b"\xff"),
                (b"\xff", b"\xff"),
            ];

            for &(value, expected) in named_cases {
                assert_case(&[b"printf", b"%b", value], expected);
            }
        }

        #[test]
        fn percent_b_recognition_is_exact_and_missing_values_are_empty() {
            assert_case(&[b"printf", b"<%b>"], b"<>");
            assert_case(&[b"printf", b"%%b:%bb", b"\\n"], b"%b:\nb");

            let (status, stdout, stderr, _, _) = capture(&[b"printf", b"%1b", b"unused"]);
            assert_eq!(status, ExitStatus::Failure);
            assert!(stdout.is_empty());
            assert_eq!(stderr, b"printf: %1b: invalid directive\n");
        }

        #[test]
        fn percent_b_sysv_octal_marker_accepts_zero_through_three_digits() {
            let cases: &[(&[u8], &[u8])] = &[
                (b"\\0Z", b"\0Z"),
                (b"\\07Z", b"\x07Z"),
                (b"\\077Z", b"?Z"),
                (b"\\0777Z", b"\xffZ"),
                (b"\\07777", b"\xff7"),
                (b"\\08", b"\x008"),
                (b"\\1Z", b"\x01Z"),
                (b"\\12Z", b"\x0aZ"),
                (b"\\123Z", b"SZ"),
                (b"\\1234", b"S4"),
            ];

            for &(value, expected) in cases {
                assert_case(&[b"printf", b"%b", value], expected);
            }
        }

        #[test]
        fn percent_b_fallback_escapes_preserve_warnings_and_output() {
            let (status, stdout, stderr, _, _) = capture(&[b"printf", b"%b", b"A\\qB"]);
            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"AqB");
            assert_eq!(stderr, b"printf: unknown escape sequence `\\q'\n");

            let (status, stdout, stderr, _, _) = capture(&[b"printf", b"%b", b"before\\"]);
            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"before");
            assert_eq!(stderr, b"printf: null escape sequence\n");
        }

        #[test]
        fn percent_b_stop_is_immediate_and_preserves_sticky_status() {
            assert_case(
                &[b"printf", b"%bAFTER%s", b"before\\cafter", b"unused"],
                b"before",
            );

            let (status, stdout, stderr, _, _) = capture(&[b"printf", b"\\q%bAFTER", b"\\c"]);
            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"q");
            assert_eq!(stderr, b"printf: unknown escape sequence `\\q'\n");
        }

        #[test]
        fn percent_b_stop_ends_repeated_formats_and_leaves_later_operands_unused() {
            assert_case(
                &[b"printf", b"%b|", b"first", b"second\\cignored", b"third"],
                b"first|second",
            );
        }

        #[test]
        fn escaped_backslash_before_c_does_not_stop_percent_b() {
            assert_case(
                &[b"printf", b"%b:%s", b"\\\\c", b"continued"],
                b"\\c:continued",
            );
        }

        #[test]
        fn escape_string_mixed() {
            assert_case(&[arg(b"printf"), arg(b"%b"), arg(b"A\\nB\\tC")], b"A\nB\tC");
        }

        #[test]
        fn escape_string_hex() {
            assert_case(
                &[arg(b"printf"), arg(b"%b"), arg(b"\\x41\\x42\\x43")],
                b"ABC",
            );
        }

        #[test]
        fn vertical_tab_escape() {
            assert_case(&[arg(b"printf"), arg(b"\\v")], b"\x0b");
        }

        #[test]
        fn single_quote_escape() {
            assert_case(&[arg(b"printf"), arg(b"\\'")], b"'");
        }

        #[test]
        fn complex_b_octal() {
            assert_case(
                &[arg(b"printf"), arg(b"%b"), arg(b"\\001\\002\\003")],
                b"\x01\x02\x03",
            );
        }
    }

    mod traversal_cases {
        use super::{arg, assert_case, Engine, MockWriter};

        #[test]
        fn literals_and_percent_percent_ignore_extra_operands() {
            assert_case(
                &[b"printf", b"literal-%%", b"unused", b"also-unused"],
                b"literal-%",
            );
        }

        #[test]
        fn character_and_string_conversions_consume_in_order() {
            assert_case(&[b"printf", b"<%c:%5.2s>", b"XYZ", b"hello"], b"<X:   he>");
            assert_case(&[b"printf", b"%c"], b"\0");
        }

        #[test]
        fn character_and_string_rendering_stays_bytewise_with_c_defaults() {
            assert_case(
                &[
                    b"printf",
                    b"[%#0+ 5.2s][%-#0+ 4.9c][%3c][%3s]",
                    b"\xffABC",
                    b"\x80tail",
                ],
                b"[   \xffA][\x80   ][  \0][   ]",
            );
        }

        #[test]
        fn complete_format_is_reused_only_while_operands_remain() {
            assert_case(
                &[b"printf", b"[%s]", b"one", b"two", b"three"],
                b"[one][two][three]",
            );
            assert_case(
                &[b"printf", b"[%s,%s]", b"one", b"two", b"three"],
                b"[one,two][three,]",
            );
        }

        #[test]
        fn reused_pass_replays_literals_and_percent_percent() {
            assert_case(
                &[b"printf", b"literal-%%<%s>|", b"one", b"two"],
                b"literal-%<one>|literal-%<two>|",
            );
        }

        #[test]
        fn final_partial_pass_uses_each_type_specific_default() {
            assert_case(
                &[
                    b"printf",
                    b"<%s>|<%c>|<%d>|<%u>|<%b>;",
                    b"text",
                    b"C",
                    b"-7",
                    b"8",
                    b"raw",
                    b"tail",
                ],
                b"<text>|<C>|<-7>|<8>|<raw>;<tail>|<\0>|<0>|<0>|<>;",
            );
        }

        #[test]
        fn final_partial_pass_defaults_missing_dynamic_operands() {
            assert_case(
                &[b"printf", b"[%*.*s]", b"4", b"2", b"abc", b"3"],
                b"[  ab][   ]",
            );
        }

        #[test]
        fn missing_getters_return_defaults_without_advancing() {
            let operands: [&[u8]; 0] = [];
            let mut stdout = MockWriter::default();
            let mut stderr = MockWriter::default();
            let mut engine = Engine::new(&operands, 0, b"printf", &mut stdout, &mut stderr);

            assert_eq!(engine.getchr(), 0);
            assert_eq!(engine.getstr(), b"");
            assert_eq!(engine.getint(), 0);
            assert_eq!(engine.getlong().unwrap(), 0);
            assert_eq!(engine.getulong().unwrap(), 0);
            assert_eq!(engine.getdouble().unwrap(), 0.0);
            assert_eq!(engine.argument_index, engine.initial_argument_index);
            drop(engine);
            assert!(stdout.bytes.is_empty());
            assert!(stderr.bytes.is_empty());
        }

        #[test]
        fn an_existing_empty_operand_is_still_consumed() {
            assert_case(&[b"printf", b"<%s>", b"", b"after"], b"<><after>");
            assert_case(&[b"printf", b"<%c>", b"", b"Z"], b"<\0><Z>");
        }

        #[test]
        fn rejected_getint_operand_remains_for_the_value_conversion() {
            assert_case(&[b"printf", b"%*s", b"x", b"y"], b"xy");
        }

        #[test]
        fn zero_unsigned() {
            assert_case(&[arg(b"printf"), arg(b"%u"), arg(b"0")], b"0");
        }

        #[test]
        fn width_zero() {
            assert_case(
                &[arg(b"printf"), arg(b"%*s"), arg(b"0"), arg(b"hello")],
                b"hello",
            );
        }

        #[test]
        fn empty_char_literal() {
            assert_case(&[arg(b"printf"), arg(b"%d"), arg(b"''")], b"39");
        }

        #[test]
        fn scientific_lower() {
            assert_case(
                &[arg(b"printf"), arg(b"%e"), arg(b"123.456")],
                b"1.234560e+02",
            );
        }

        #[test]
        fn zero_hex() {
            assert_case(&[arg(b"printf"), arg(b"%x"), arg(b"0")], b"0");
        }

        #[test]
        fn field_width_arg() {
            assert_case(
                &[arg(b"printf"), arg(b"%*s"), arg(b"7"), arg(b"hello")],
                b"  hello",
            );
        }

        #[test]
        fn string_from_null() {
            assert_case(&[arg(b"printf"), arg(b"%s")], b"");
        }

        #[test]
        fn width_precision_args() {
            assert_case(
                &[
                    arg(b"printf"),
                    arg(b"%*.*s"),
                    arg(b"4"),
                    arg(b"2"),
                    arg(b"hello"),
                ],
                b"  he",
            );
        }

        #[test]
        fn int_no_arg() {
            assert_case(&[arg(b"printf"), arg(b"%d")], b"0");
        }

        #[test]
        fn format_reuse_insufficient() {
            assert_case(&[arg(b"printf"), arg(b"%d %d"), arg(b"123")], b"123 0");
        }

        #[test]
        fn every_integer_conversion_uses_zero_for_a_missing_operand() {
            assert_case(&[b"printf", b"%d|%i|%o|%u|%x|%X"], b"0|0|0|0|0|0");
        }

        #[test]
        fn integer_getters_apply_quote_and_base_zero_rules_in_dispatch_order() {
            assert_case(
                &[
                    b"printf",
                    b"%d|%i|%o|%u|%x|%X",
                    b"'A",
                    b"-010",
                    b"010",
                    b"-1",
                    b"0x2a",
                    b"0X2a",
                ],
                b"65|-8|10|18446744073709551615|2a|2A",
            );
        }

        #[test]
        fn existing_empty_integer_operand_is_consumed_before_missing_defaults() {
            assert_case(&[b"printf", b"<%d><%u><%x>", b"", b"7"], b"<0><7><0>");
        }
    }

    mod floating_input_cases {
        use super::{Engine, ExitStatus, MockWriter};

        #[test]
        fn getdouble_handles_missing_empty_quoted_and_signed_operands_without_warnings() {
            let operands: &[&[u8]] = &[b"'A", b"\"\xff", b"'", b"-0", b"-nan", b""];
            let mut stdout = MockWriter::default();
            let mut stderr = MockWriter::default();
            let mut engine = Engine::new(operands, 0, b"printf", &mut stdout, &mut stderr);

            assert_eq!(engine.getdouble().unwrap(), 65.0);
            assert_eq!(engine.getdouble().unwrap(), 255.0);
            assert_eq!(engine.getdouble().unwrap(), 0.0);
            assert_eq!(engine.getdouble().unwrap().to_bits(), (-0.0_f64).to_bits());
            let nan = engine.getdouble().unwrap();
            assert!(nan.is_nan());
            assert!(nan.is_sign_negative());
            assert_eq!(engine.getdouble().unwrap(), 0.0);
            assert_eq!(engine.getdouble().unwrap(), 0.0);
            assert_eq!(engine.argument_index, operands.len());
            assert_eq!(engine.status, ExitStatus::Success);
            drop(engine);

            assert!(stdout.bytes.is_empty());
            assert!(stderr.bytes.is_empty());
        }

        #[test]
        fn floating_diagnostics_use_partial_conversion_before_range_state() {
            let operands: &[&[u8]] = &[
                b"bad",
                b"1.25tail",
                b"1e999tail",
                b"1e999",
                b"1e-999",
                b"0e-999",
            ];
            let mut stdout = MockWriter::default();
            let mut stderr = MockWriter::default();
            let mut engine = Engine::new(operands, 0, b"float-alias", &mut stdout, &mut stderr);

            assert_eq!(engine.getdouble().unwrap(), 0.0);
            assert_eq!(engine.getdouble().unwrap(), 1.25);
            assert_eq!(engine.getdouble().unwrap(), f64::INFINITY);
            assert_eq!(engine.getdouble().unwrap(), f64::INFINITY);
            assert_eq!(engine.getdouble().unwrap(), 0.0);
            assert_eq!(engine.getdouble().unwrap(), 0.0);
            assert_eq!(engine.status, ExitStatus::Failure);
            drop(engine);

            assert!(stdout.bytes.is_empty());
            assert_eq!(
                stderr.bytes,
                b"float-alias: bad: expected numeric value\n\
float-alias: 1.25tail: not completely converted\n\
float-alias: 1e999tail: not completely converted\n\
float-alias: 1e999: Numerical result out of range\n\
float-alias: 1e-999: Numerical result out of range\n"
            );
            assert_eq!(stderr.flush_count, 5);
        }
    }

    mod diagnostic_cases {
        use super::{capture, ExitStatus};

        #[test]
        fn usage_is_exact_unprefixed_and_accepts_one_leading_double_dash() {
            let no_operands: &[&[u8]] = &[b"/tmp/not-printf"];
            let only_double_dash: &[&[u8]] = &[b"printf", b"--"];
            for args in [no_operands, only_double_dash] {
                let (status, stdout, stderr, stdout_flushes, stderr_flushes) = capture(args);
                assert_eq!(status, ExitStatus::Failure);
                assert!(stdout.is_empty());
                assert_eq!(stderr, b"usage: printf format [argument ...]\n");
                assert_eq!(stdout_flushes, 1);
                assert_eq!(stderr_flushes, 1);
            }

            let (status, stdout, stderr, _, _) = capture(&[b"printf", b"--", b"[%s]", b"value"]);
            assert_eq!(status, ExitStatus::Success);
            assert_eq!(stdout, b"[value]");
            assert!(stderr.is_empty());
        }

        #[test]
        fn warning_prefix_uses_the_raw_argv0_basename() {
            let (status, stdout, stderr, _, _) = capture(&[b"/dir/raw-\xff-name", b"\\?"]);
            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"?");
            assert_eq!(stderr, b"raw-\xff-name: unknown escape sequence `\\?'\n");
        }

        #[test]
        fn escape_warning_status_is_sticky_across_later_output() {
            let (status, stdout, stderr, _, _) = capture(&[b"printf", b"\\q:%s", b"okay"]);
            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"q:okay");
            assert_eq!(stderr, b"printf: unknown escape sequence `\\q'\n");
        }

        #[test]
        fn fatal_format_diagnostics_are_exact() {
            let (status, stdout, stderr, _, _) = capture(&[b"alias", b"prefix%"]);
            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"prefix");
            assert_eq!(stderr, b"alias: missing format character\n");

            let (status, stdout, stderr, _, _) = capture(&[b"alias", b"%Q"]);
            assert_eq!(status, ExitStatus::Failure);
            assert!(stdout.is_empty());
            assert_eq!(stderr, b"alias: %Q: invalid directive\n");
        }

        #[test]
        fn unsupported_and_unterminated_directive_spans_are_exact() {
            let cases: &[(&[u8], &[u8], &[u8])] = &[
                (
                    b"prefix%#12",
                    b"prefix",
                    b"alias: missing format character\n",
                ),
                (b"%.", b"", b"alias: %.: invalid directive\n"),
                (b"%.123", b"", b"alias: %.123: invalid directive\n"),
                (b"%.*", b"", b"alias: %.*: invalid directive\n"),
                (b"%ld", b"", b"alias: %l: invalid directive\n"),
                (b"%1b", b"", b"alias: %1b: invalid directive\n"),
                (b"%#%", b"", b"alias: %#%: invalid directive\n"),
                (b"%\xff", b"", b"alias: %\xff: invalid directive\n"),
            ];

            for &(format, expected_stdout, expected_stderr) in cases {
                let (status, stdout, stderr, _, _) = capture(&[b"alias", format]);
                assert_eq!(status, ExitStatus::Failure, "{format:?}");
                assert_eq!(stdout, expected_stdout, "{format:?}");
                assert_eq!(stderr, expected_stderr, "{format:?}");
            }
        }

        #[test]
        fn integer_conversion_failures_emit_values_and_exact_raw_diagnostics() {
            let (status, stdout, stderr, _, stderr_flushes) = capture(&[
                b"/tmp/raw-\xff-alias",
                b"%d|%i|%u",
                b"\xffbad",
                b"09",
                b"18446744073709551616",
            ]);

            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"0|0|18446744073709551615");
            assert_eq!(
                stderr,
                b"raw-\xff-alias: \xffbad: expected numeric value\n\
raw-\xff-alias: 09: not completely converted\n\
raw-\xff-alias: 18446744073709551616: Numerical result out of range\n"
            );
            assert_eq!(stderr_flushes, 3);
        }

        #[test]
        fn trailing_text_takes_precedence_over_integer_range_errors() {
            let (status, stdout, stderr, _, _) = capture(&[
                b"printf",
                b"%d|%u",
                b"-9223372036854775809tail",
                b"18446744073709551616tail",
            ]);

            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"-9223372036854775808|18446744073709551615");
            assert_eq!(
                stderr,
                b"printf: -9223372036854775809tail: not completely converted\n\
printf: 18446744073709551616tail: not completely converted\n"
            );
        }

        #[test]
        fn conversion_status_stays_sticky_while_later_integer_output_continues() {
            let (status, stdout, stderr, _, _) =
                capture(&[b"printf", b"%d:%#x:%+d", b"bad", b"42", b"7"]);

            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"0:0x2a:+7");
            assert_eq!(stderr, b"printf: bad: expected numeric value\n");
        }

        #[test]
        fn empty_missing_and_quoted_integer_values_do_not_warn() {
            let (status, stdout, stderr, _, stderr_flushes) =
                capture(&[b"printf", b"%d|%u|%d|%u", b"", b"'A", b"\"\xff"]);

            assert_eq!(status, ExitStatus::Success);
            assert_eq!(stdout, b"0|65|255|0");
            assert!(stderr.is_empty());
            assert_eq!(stderr_flushes, 0);
        }

        #[test]
        fn conversion_end_checks_the_nul_byte_before_trailing_storage() {
            let (status, stdout, stderr, _, _) =
                capture(&[b"printf", b"%d|%u", b"12\0ignored", b"bad\0ignored"]);

            assert_eq!(status, ExitStatus::Failure);
            assert_eq!(stdout, b"12|0");
            assert_eq!(stderr, b"printf: bad: expected numeric value\n");
        }
    }

    mod buffering_cases {
        use super::{
            run, BufferMode, CStdout, ExitStatus, FailAfterWriter, MockWriter, RecordingWriter,
            Stream,
        };
        use crate::test_support::WriterEvent;
        use std::io::{ErrorKind, Write};

        #[test]
        fn full_buffer_retains_4095_bytes_and_streams_4096() {
            let inner = RecordingWriter::new(Stream::Stdout);
            let events = inner.events.clone();
            let mut stdout = CStdout::new(inner, BufferMode::Full);

            stdout.write_all(&vec![b'a'; 4095]).unwrap();
            assert!(events.borrow().is_empty());

            stdout.write_all(b"b").unwrap();
            assert_eq!(
                *events.borrow(),
                vec![WriterEvent::Write {
                    stream: Stream::Stdout,
                    bytes: [vec![b'a'; 4095], vec![b'b']].concat(),
                }]
            );

            stdout.write_all(b"tail").unwrap();
            let inner = stdout.finish().unwrap();
            assert_eq!(
                *events.borrow(),
                vec![
                    WriterEvent::Write {
                        stream: Stream::Stdout,
                        bytes: [vec![b'a'; 4095], vec![b'b']].concat(),
                    },
                    WriterEvent::Write {
                        stream: Stream::Stdout,
                        bytes: b"tail".to_vec(),
                    },
                    WriterEvent::Flush {
                        stream: Stream::Stdout,
                    },
                ]
            );
            assert_eq!(inner.stream, Stream::Stdout);
        }

        #[test]
        fn line_buffer_flushes_through_each_newline() {
            let inner = RecordingWriter::new(Stream::Stdout);
            let events = inner.events.clone();
            let mut stdout = CStdout::new(inner, BufferMode::Line);

            stdout.write_all(b"one\ntwo").unwrap();
            assert_eq!(
                *events.borrow(),
                vec![
                    WriterEvent::Write {
                        stream: Stream::Stdout,
                        bytes: b"one\n".to_vec(),
                    },
                    WriterEvent::Flush {
                        stream: Stream::Stdout,
                    },
                ]
            );

            stdout.finish().unwrap();
            assert_eq!(
                &events.borrow()[2..],
                &[
                    WriterEvent::Write {
                        stream: Stream::Stdout,
                        bytes: b"two".to_vec(),
                    },
                    WriterEvent::Flush {
                        stream: Stream::Stdout,
                    },
                ]
            );
        }

        #[test]
        fn warning_precedes_residual_stdout_but_follows_a_complete_block() {
            let mut residual_format = vec![b'a'; 4095];
            residual_format.push(b'\\');
            let residual_events = run_with_recorded_streams(&residual_format, &[]);
            let first_stderr = first_write(&residual_events, Stream::Stderr);
            let first_stdout = first_write(&residual_events, Stream::Stdout);
            assert!(first_stderr < first_stdout);

            let mut block_format = vec![b'a'; 4096];
            block_format.push(b'\\');
            let block_events = run_with_recorded_streams(&block_format, &[]);
            let first_stdout = first_write(&block_events, Stream::Stdout);
            let first_stderr = first_write(&block_events, Stream::Stderr);
            assert!(first_stdout < first_stderr);
        }

        #[test]
        fn early_percent_b_stop_and_fatal_return_flush_residual_stdout() {
            let stop_events = run_with_recorded_streams(b"%bignored", &[b"before\\cafter"]);
            assert!(stop_events.iter().any(|event| {
                matches!(
                    event,
                    WriterEvent::Write {
                        stream: Stream::Stdout,
                        bytes
                    } if bytes == b"before"
                )
            }));
            assert!(stop_events.iter().any(|event| {
                matches!(
                    event,
                    WriterEvent::Flush {
                        stream: Stream::Stdout
                    }
                )
            }));

            let fatal_events = run_with_recorded_streams(b"before%", &[]);
            let stderr_index = first_write(&fatal_events, Stream::Stderr);
            let stdout_index = first_write(&fatal_events, Stream::Stdout);
            assert!(stderr_index < stdout_index);
            assert!(matches!(
                fatal_events.last(),
                Some(WriterEvent::Flush {
                    stream: Stream::Stdout
                })
            ));
        }

        #[test]
        fn write_and_flush_failures_propagate_without_panic_output() {
            let mut stdout = FailAfterWriter::new(2);
            let mut stderr = MockWriter::default();
            let error = run(&[b"printf", b"abcd"], &mut stdout, &mut stderr).unwrap_err();
            assert_eq!(error.kind(), ErrorKind::BrokenPipe);
            assert_eq!(stdout.bytes, b"ab");
            assert!(stderr.bytes.is_empty());

            let mut stdout = FailAfterWriter::failing_flush();
            let error = run(&[b"printf", b"abc"], &mut stdout, &mut stderr).unwrap_err();
            assert_eq!(error.kind(), ErrorKind::BrokenPipe);
            assert_eq!(stdout.bytes, b"abc");
        }

        fn run_with_recorded_streams(format: &[u8], operands: &[&[u8]]) -> Vec<WriterEvent> {
            let stdout_inner = RecordingWriter::new(Stream::Stdout);
            let events = stdout_inner.events.clone();
            let mut stdout = CStdout::new(stdout_inner, BufferMode::Full);
            let mut stderr = RecordingWriter::with_events(Stream::Stderr, events.clone());
            let mut args = Vec::with_capacity(2 + operands.len());
            args.push(b"printf".as_slice());
            args.push(format);
            args.extend_from_slice(operands);

            let status = run(&args, &mut stdout, &mut stderr).unwrap();
            if format.ends_with(b"\\") || format.ends_with(b"%") {
                assert_eq!(status, ExitStatus::Failure);
            }
            let recorded = events.borrow().clone();
            recorded
        }

        fn first_write(events: &[WriterEvent], stream: Stream) -> usize {
            events
                .iter()
                .position(|event| {
                    matches!(
                        event,
                        WriterEvent::Write {
                            stream: event_stream,
                            ..
                        } if *event_stream == stream
                    )
                })
                .expect("stream wrote bytes")
        }
    }

    fn arg<const N: usize>(bytes: &'static [u8; N]) -> &'static [u8] {
        bytes
    }

    fn assert_case(args: &[&[u8]], expected: &[u8]) {
        let (status, stdout, stderr, _, _) = capture(args);
        assert_eq!(status, ExitStatus::Success);
        assert_eq!(stdout, expected);
        assert!(stderr.is_empty());
    }

    fn capture(args: &[&[u8]]) -> (ExitStatus, Vec<u8>, Vec<u8>, usize, usize) {
        let mut stdout = MockWriter::default();
        let mut stderr = MockWriter::default();
        let status = run(args, &mut stdout, &mut stderr).expect("run succeeds");
        (
            status,
            stdout.bytes,
            stderr.bytes,
            stdout.flush_count,
            stderr.flush_count,
        )
    }
}
