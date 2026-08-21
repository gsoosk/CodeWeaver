use std::cmp::Ordering;
use std::fmt;
use std::io::{self, Write};

const NUMBER_START: &[u8] = b"+-.0123456789";
const SKIP1: &[u8] = b"#-+ 0";
const SKIP2: &[u8] = b"0123456789";
const DECIMAL_BIG_CAPACITY: usize = 800;

#[derive(Debug)]
pub enum RunError {
    Io(io::Error),
    Allocation,
    Formatter,
}

impl fmt::Display for RunError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(error) => error.fmt(formatter),
            Self::Allocation => formatter.write_str("out of memory"),
            Self::Formatter => formatter.write_str("formatting failed"),
        }
    }
}

impl std::error::Error for RunError {}

impl From<io::Error> for RunError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

pub type RunResult<T> = Result<T, RunError>;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum EscapeOutcome {
    Complete,
    Cancel,
    Fatal,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ConversionIssue {
    None,
    NoDigits,
    Trailing,
    Range,
}

#[derive(Clone, Copy, Debug)]
struct Parsed<T> {
    value: T,
    end_index: usize,
    range_error: bool,
}

#[derive(Clone, Copy, Debug, Default)]
struct DynamicControls {
    field_width: Option<i32>,
    precision: Option<i32>,
}

#[derive(Clone, Copy, Debug)]
struct Directive<'a> {
    raw: &'a [u8],
    conversion: u8,
    controls: DynamicControls,
}

#[derive(Clone, Copy, Debug)]
enum ConversionValue<'a> {
    Character(u8),
    String(&'a [u8]),
    Signed(i64),
    Unsigned(u64),
    Float(f64),
}

struct State<'a> {
    rval: u8,
    operands: &'a [Vec<u8>],
    cursor: usize,
    program_name: &'a [u8],
}

struct IoFmtWriter<'a, W: Write> {
    inner: &'a mut W,
    io_error: Option<io::Error>,
}

impl<'a, W: Write> IoFmtWriter<'a, W> {
    fn new(inner: &'a mut W) -> Self {
        Self {
            inner,
            io_error: None,
        }
    }

    fn finish(self) -> RunResult<()> {
        match self.io_error {
            Some(error) => Err(RunError::Io(error)),
            None => Ok(()),
        }
    }
}

impl<W: Write> fmt::Write for IoFmtWriter<'_, W> {
    fn write_str(&mut self, value: &str) -> fmt::Result {
        if self.io_error.is_some() {
            return Err(fmt::Error);
        }

        if let Err(error) = self.inner.write_all(value.as_bytes()) {
            self.io_error = Some(error);
            return Err(fmt::Error);
        }

        Ok(())
    }
}

impl<'a> State<'a> {
    fn new(operands: &'a [Vec<u8>], program_name: &'a [u8]) -> Self {
        Self {
            rval: 0,
            operands,
            cursor: 0,
            program_name,
        }
    }

    fn getchr(&mut self) -> u8 {
        let Some(value) = self.operands.get(self.cursor) else {
            return 0;
        };
        self.cursor += 1;
        value.first().copied().unwrap_or(0)
    }

    fn getstr(&mut self) -> &'a [u8] {
        let Some(value) = self.operands.get(self.cursor) else {
            return b"";
        };
        self.cursor += 1;
        value
    }

    fn getint(&mut self) -> i32 {
        let Some(operand) = self.operands.get(self.cursor).map(Vec::as_slice) else {
            return 0;
        };
        if !operand
            .first()
            .is_some_and(|byte| NUMBER_START.contains(byte))
        {
            return 0;
        }
        self.cursor += 1;

        let mut index = 0;
        let negative = match operand.first() {
            Some(b'-') => {
                index = 1;
                true
            }
            Some(b'+') => {
                index = 1;
                false
            }
            _ => false,
        };
        let limit = if negative {
            i64::MAX as u64 + 1
        } else {
            i64::MAX as u64
        };
        let mut magnitude = 0_u64;
        while let Some(byte @ b'0'..=b'9') = operand.get(index) {
            let digit = u64::from(*byte - b'0');
            magnitude = magnitude
                .checked_mul(10)
                .and_then(|value| value.checked_add(digit))
                .unwrap_or(limit)
                .min(limit);
            index += 1;
        }

        let value = if negative {
            if magnitude == i64::MAX as u64 + 1 {
                i64::MIN
            } else {
                -(magnitude as i64)
            }
        } else {
            magnitude as i64
        };
        value as i32
    }

    fn getlong<W: Write>(&mut self, stderr: &mut W) -> RunResult<i64> {
        let Some(operand): Option<&'a [u8]> = self.operands.get(self.cursor).map(Vec::as_slice)
        else {
            return Ok(0);
        };
        self.cursor += 1;

        if matches!(operand.first(), Some(b'"' | b'\'')) {
            return Ok(i64::from(operand.get(1).copied().unwrap_or(0)));
        }

        let parsed = parse_signed(operand);
        let issue = conversion_issue(operand, parsed.end_index, parsed.range_error);
        self.check_conversion(operand, issue, stderr)?;
        Ok(parsed.value)
    }

    fn getulong<W: Write>(&mut self, stderr: &mut W) -> RunResult<u64> {
        let Some(operand): Option<&'a [u8]> = self.operands.get(self.cursor).map(Vec::as_slice)
        else {
            return Ok(0);
        };
        self.cursor += 1;

        if matches!(operand.first(), Some(b'"' | b'\'')) {
            return Ok(u64::from(operand.get(1).copied().unwrap_or(0)));
        }

        let parsed = parse_unsigned(operand);
        let issue = conversion_issue(operand, parsed.end_index, parsed.range_error);
        self.check_conversion(operand, issue, stderr)?;
        Ok(parsed.value)
    }

    fn getdouble<W: Write>(&mut self, stderr: &mut W) -> RunResult<f64> {
        let Some(operand): Option<&'a [u8]> = self.operands.get(self.cursor).map(Vec::as_slice)
        else {
            return Ok(0.0);
        };
        self.cursor += 1;

        if matches!(operand.first(), Some(b'"' | b'\'')) {
            return Ok(f64::from(operand.get(1).copied().unwrap_or(0)));
        }

        let parsed = parse_double(operand)?;
        let issue = conversion_issue(operand, parsed.end_index, parsed.range_error);
        self.check_conversion(operand, issue, stderr)?;
        Ok(parsed.value)
    }

    fn check_conversion<W: Write>(
        &mut self,
        operand: &[u8],
        issue: ConversionIssue,
        stderr: &mut W,
    ) -> RunResult<()> {
        match issue {
            ConversionIssue::None => return Ok(()),
            ConversionIssue::NoDigits => {
                stderr.write_all(self.program_name)?;
                stderr.write_all(b": ")?;
                stderr.write_all(operand)?;
                stderr.write_all(b": expected numeric value\n")?;
            }
            ConversionIssue::Trailing => {
                stderr.write_all(self.program_name)?;
                stderr.write_all(b": ")?;
                stderr.write_all(operand)?;
                stderr.write_all(b": not completely converted\n")?;
            }
            ConversionIssue::Range => {
                warn_range(self.program_name, operand, stderr)?;
            }
        }
        self.rval = 1;
        Ok(())
    }
}

pub fn run<W: Write, E: Write>(args: &[Vec<u8>], stdout: &mut W, stderr: &mut E) -> RunResult<u8> {
    let mut format_index = 1;
    if args.get(format_index).map(Vec::as_slice) == Some(b"--") {
        format_index += 1;
    }

    let Some(format) = args.get(format_index) else {
        return usage(stderr);
    };

    let program_path = args.first().map(Vec::as_slice).unwrap_or_default();
    let program_name = short_program_name(program_path);
    let operands = args.get(format_index + 1..).unwrap_or_default();
    let mut state = State::new(operands, program_name);

    loop {
        let pass_start = state.cursor;
        match scan_format(format, &mut state, stdout, stderr)? {
            EscapeOutcome::Complete => {}
            EscapeOutcome::Cancel | EscapeOutcome::Fatal => break,
        }

        if state.cursor == pass_start || state.cursor >= operands.len() {
            break;
        }
    }
    Ok(state.rval)
}

fn short_program_name(path: &[u8]) -> &[u8] {
    path.rsplit(|byte| *byte == b'/').next().unwrap_or(path)
}

fn usage<W: Write>(stderr: &mut W) -> RunResult<u8> {
    stderr.write_all(b"usage: printf format [argument ...]\n")?;
    Ok(1)
}

fn warnx<W: Write>(program_name: &[u8], message: &[u8], stderr: &mut W) -> RunResult<()> {
    stderr.write_all(program_name)?;
    stderr.write_all(b": ")?;
    stderr.write_all(message)?;
    stderr.write_all(b"\n")?;
    Ok(())
}

fn warn_range<W: Write>(program_name: &[u8], operand: &[u8], stderr: &mut W) -> RunResult<()> {
    stderr.write_all(program_name)?;
    stderr.write_all(b": ")?;
    stderr.write_all(operand)?;
    stderr.write_all(b": Numerical result out of range\n")?;
    Ok(())
}

fn scan_format<W: Write, E: Write>(
    format: &[u8],
    state: &mut State<'_>,
    stdout: &mut W,
    stderr: &mut E,
) -> RunResult<EscapeOutcome> {
    let mut index = 0;
    while index < format.len() {
        match format[index] {
            b'%' => {
                let Some(next) = format.get(index + 1).copied() else {
                    warnx(state.program_name, b"missing format character", stderr)?;
                    state.rval = 1;
                    return Ok(EscapeOutcome::Fatal);
                };

                if next == b'%' {
                    stdout.write_all(b"%")?;
                    index += 2;
                    continue;
                }
                if next == b'b' {
                    let value = state.getstr();
                    if print_escape_str(value, state, stdout, stderr)? == EscapeOutcome::Cancel {
                        return Ok(EscapeOutcome::Cancel);
                    }
                    index += 2;
                    continue;
                }

                let (directive, next_index) = match parse_directive(format, index, state) {
                    Ok(parsed) => parsed,
                    Err(RunError::Formatter) => {
                        warnx(state.program_name, b"missing format character", stderr)?;
                        state.rval = 1;
                        return Ok(EscapeOutcome::Fatal);
                    }
                    Err(error) => return Err(error),
                };
                let value = match directive.conversion {
                    b'c' => ConversionValue::Character(state.getchr()),
                    b's' => ConversionValue::String(state.getstr()),
                    b'd' | b'i' => ConversionValue::Signed(state.getlong(stderr)?),
                    b'o' | b'u' | b'x' | b'X' => ConversionValue::Unsigned(state.getulong(stderr)?),
                    b'a' | b'A' | b'e' | b'E' | b'f' | b'F' | b'g' | b'G' => {
                        ConversionValue::Float(state.getdouble(stderr)?)
                    }
                    _ => {
                        stderr.write_all(state.program_name)?;
                        stderr.write_all(b": ")?;
                        stderr.write_all(directive.raw)?;
                        stderr.write_all(b": invalid directive\n")?;
                        state.rval = 1;
                        return Ok(EscapeOutcome::Fatal);
                    }
                };
                if let Err(error) = emit_conversion(directive, value, stdout) {
                    match error {
                        RunError::Allocation => {
                            warnx(state.program_name, b"out of memory", stderr)?;
                            state.rval = 1;
                            return Ok(EscapeOutcome::Fatal);
                        }
                        other => return Err(other),
                    }
                }
                index = next_index;
            }
            b'\\' => {
                let consumed = print_escape(format, index, state, stdout, stderr)?;
                index = index.saturating_add(consumed).saturating_add(1);
            }
            _ => {
                let start = index;
                while index < format.len() && !matches!(format[index], b'%' | b'\\') {
                    index += 1;
                }
                stdout.write_all(&format[start..index])?;
            }
        }
    }

    Ok(EscapeOutcome::Complete)
}

fn parse_directive<'a>(
    format: &'a [u8],
    percent_index: usize,
    state: &mut State<'_>,
) -> RunResult<(Directive<'a>, usize)> {
    let mut index = percent_index.checked_add(1).ok_or(RunError::Formatter)?;
    while format.get(index).is_some_and(|byte| SKIP1.contains(byte)) {
        index += 1;
    }

    let mut controls = DynamicControls::default();
    if format.get(index) == Some(&b'*') {
        controls.field_width = Some(state.getint());
        index += 1;
    }
    while format.get(index).is_some_and(|byte| SKIP2.contains(byte)) {
        index += 1;
    }

    if format.get(index) == Some(&b'.') {
        index += 1;
        if format.get(index) == Some(&b'*') {
            controls.precision = Some(state.getint());
            index += 1;
        }
        while format.get(index).is_some_and(|byte| SKIP2.contains(byte)) {
            index += 1;
        }
    }

    let conversion = format.get(index).copied().ok_or(RunError::Formatter)?;
    let next_index = index.checked_add(1).ok_or(RunError::Formatter)?;
    Ok((
        Directive {
            raw: &format[percent_index..next_index],
            conversion,
            controls,
        },
        next_index,
    ))
}

fn isodigit(byte: u8) -> bool {
    matches!(byte, b'0'..=b'7')
}

fn octtobin(byte: u8) -> Option<u8> {
    isodigit(byte).then_some(byte - b'0')
}

fn hextobin(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

fn print_escape_str<W: Write, E: Write>(
    value: &[u8],
    state: &mut State<'_>,
    stdout: &mut W,
    stderr: &mut E,
) -> RunResult<EscapeOutcome> {
    let mut index = 0;
    while index < value.len() {
        if value[index] != b'\\' {
            let start = index;
            while index < value.len() && value[index] != b'\\' {
                index += 1;
            }
            stdout.write_all(&value[start..index])?;
            continue;
        }

        match value.get(index + 1).copied() {
            Some(b'0') => {
                let mut cursor = index + 2;
                let mut decoded = 0_u16;
                for _ in 0..3 {
                    let Some(digit) = value.get(cursor).and_then(|byte| octtobin(*byte)) else {
                        break;
                    };
                    decoded = (decoded << 3) + u16::from(digit);
                    cursor += 1;
                }
                stdout.write_all(&[decoded as u8])?;
                index = cursor;
            }
            Some(b'c') => return Ok(EscapeOutcome::Cancel),
            _ => {
                let consumed = print_escape(value, index, state, stdout, stderr)?;
                index = index.saturating_add(consumed).saturating_add(1);
            }
        }
    }

    Ok(EscapeOutcome::Complete)
}

fn print_escape<W: Write, E: Write>(
    value: &[u8],
    slash_index: usize,
    state: &mut State<'_>,
    stdout: &mut W,
    stderr: &mut E,
) -> RunResult<usize> {
    let Some(escape) = value.get(slash_index + 1).copied() else {
        warnx(state.program_name, b"null escape sequence", stderr)?;
        state.rval = 1;
        return Ok(0);
    };

    if isodigit(escape) {
        let mut cursor = slash_index + 1;
        let mut decoded = 0_u16;
        let mut count = 0;
        while count < 3 {
            let Some(digit) = value.get(cursor).and_then(|byte| octtobin(*byte)) else {
                break;
            };
            decoded = (decoded << 3) + u16::from(digit);
            cursor += 1;
            count += 1;
        }
        stdout.write_all(&[decoded as u8])?;
        return Ok(count);
    }

    if escape == b'x' {
        let mut cursor = slash_index + 2;
        let mut decoded = 0_u16;
        let mut count = 0;
        while count < 2 {
            let Some(digit) = value.get(cursor).and_then(|byte| hextobin(*byte)) else {
                break;
            };
            decoded = (decoded << 4) + u16::from(digit);
            cursor += 1;
            count += 1;
        }
        stdout.write_all(&[decoded as u8])?;
        return Ok(count + 1);
    }

    let decoded = match escape {
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
        unknown => {
            stdout.write_all(&[unknown])?;
            stderr.write_all(state.program_name)?;
            stderr.write_all(b": unknown escape sequence `\\")?;
            stderr.write_all(&[unknown])?;
            stderr.write_all(b"'\n")?;
            state.rval = 1;
            return Ok(1);
        }
    };
    stdout.write_all(&[decoded])?;
    Ok(1)
}

fn mklong(directive: &[u8], conversion: u8) -> RunResult<Vec<u8>> {
    if directive.last() != Some(&conversion) {
        return Err(RunError::Formatter);
    }
    let capacity = directive.len().checked_add(1).ok_or(RunError::Allocation)?;
    let mut result = Vec::new();
    result
        .try_reserve_exact(capacity)
        .map_err(|_| RunError::Allocation)?;
    result.extend_from_slice(&directive[..directive.len() - 1]);
    result.push(b'l');
    result.push(conversion);
    Ok(result)
}

fn parse_signed(operand: &[u8]) -> Parsed<i64> {
    let (mut index, negative) = integer_start(operand);
    let (base, digits_start) = integer_base(operand, index);
    index = digits_start;
    let limit = if negative {
        i64::MAX as u64 + 1
    } else {
        i64::MAX as u64
    };
    let (magnitude, end_index, range_error) = parse_magnitude(operand, index, base, limit);
    if end_index == index {
        return Parsed {
            value: 0,
            end_index: 0,
            range_error: false,
        };
    }

    let value = if range_error {
        if negative {
            i64::MIN
        } else {
            i64::MAX
        }
    } else if negative {
        if magnitude == i64::MAX as u64 + 1 {
            i64::MIN
        } else {
            -(magnitude as i64)
        }
    } else {
        magnitude as i64
    };
    Parsed {
        value,
        end_index,
        range_error,
    }
}

fn parse_unsigned(operand: &[u8]) -> Parsed<u64> {
    let (mut index, negative) = integer_start(operand);
    let (base, digits_start) = integer_base(operand, index);
    index = digits_start;
    let (magnitude, end_index, range_error) = parse_magnitude(operand, index, base, u64::MAX);
    if end_index == index {
        return Parsed {
            value: 0,
            end_index: 0,
            range_error: false,
        };
    }

    Parsed {
        value: if negative && !range_error {
            magnitude.wrapping_neg()
        } else {
            magnitude
        },
        end_index,
        range_error,
    }
}

fn parse_double(operand: &[u8]) -> RunResult<Parsed<f64>> {
    let mut index = operand
        .iter()
        .position(|byte| !is_c_whitespace(*byte))
        .unwrap_or(operand.len());
    let negative = match operand.get(index) {
        Some(b'-') => {
            index += 1;
            true
        }
        Some(b'+') => {
            index += 1;
            false
        }
        _ => false,
    };

    if starts_ascii_case_insensitive(&operand[index..], b"infinity") {
        return Ok(Parsed {
            value: if negative {
                f64::NEG_INFINITY
            } else {
                f64::INFINITY
            },
            end_index: index + b"infinity".len(),
            range_error: false,
        });
    }
    if starts_ascii_case_insensitive(&operand[index..], b"inf") {
        return Ok(Parsed {
            value: if negative {
                f64::NEG_INFINITY
            } else {
                f64::INFINITY
            },
            end_index: index + b"inf".len(),
            range_error: false,
        });
    }
    if starts_ascii_case_insensitive(&operand[index..], b"nan") {
        let mut end_index = index + 3;
        if operand.get(end_index) == Some(&b'(') {
            let payload_start = end_index + 1;
            let mut cursor = payload_start;
            while operand
                .get(cursor)
                .is_some_and(|byte| byte.is_ascii_alphanumeric() || *byte == b'_')
            {
                cursor += 1;
            }
            if operand.get(cursor) == Some(&b')') {
                end_index = cursor + 1;
            }
        }
        let value = if negative { -f64::NAN } else { f64::NAN };
        return Ok(Parsed {
            value,
            end_index,
            range_error: false,
        });
    }

    if operand.get(index) == Some(&b'0') && matches!(operand.get(index + 1), Some(b'x' | b'X')) {
        let body_start = index + 2;
        let body_end = scan_hex_float(&operand[body_start..]) + body_start;
        if body_end > body_start {
            let body = &operand[body_start..body_end];
            let (mut value, range_error) = parse_hex_float(body).ok_or(RunError::Formatter)?;
            if negative {
                value = -value;
            }
            return Ok(Parsed {
                value,
                end_index: body_end,
                range_error,
            });
        }
    }

    let number_start = index;
    while operand.get(index).is_some_and(u8::is_ascii_digit) {
        index += 1;
    }
    let mut digit_count = index - number_start;
    if operand.get(index) == Some(&b'.') {
        index += 1;
        let fraction_start = index;
        while operand.get(index).is_some_and(u8::is_ascii_digit) {
            index += 1;
        }
        digit_count += index - fraction_start;
    }
    if digit_count == 0 {
        return Ok(Parsed {
            value: 0.0,
            end_index: 0,
            range_error: false,
        });
    }

    if matches!(operand.get(index), Some(b'e' | b'E')) {
        let exponent_marker = index;
        let mut cursor = index + 1;
        if matches!(operand.get(cursor), Some(b'+' | b'-')) {
            cursor += 1;
        }
        let exponent_start = cursor;
        while operand.get(cursor).is_some_and(u8::is_ascii_digit) {
            cursor += 1;
        }
        if cursor > exponent_start {
            index = cursor;
        } else {
            index = exponent_marker;
        }
    }

    const DECIMAL_OPTIONS: lexical_core::ParseFloatOptions = lexical_core::ParseFloatOptions::new();
    let source = &operand[number_start..index];
    let value = lexical_core::parse_with_options::<f64, { lexical_core::format::C_STRING }>(
        source,
        &DECIMAL_OPTIONS,
    )
    .map_err(|_| RunError::Formatter)?
    .copysign(if negative { -1.0 } else { 1.0 });
    Ok(Parsed {
        value,
        end_index: index,
        range_error: decimal_range_error(value, source).ok_or(RunError::Formatter)?,
    })
}

fn emit_conversion<W: Write>(
    directive: Directive<'_>,
    value: ConversionValue<'_>,
    stdout: &mut W,
) -> RunResult<()> {
    match value {
        ConversionValue::Character(value) => emit_character(value, directive, stdout),
        ConversionValue::String(value) => emit_string(value, directive, stdout),
        ConversionValue::Signed(value) => {
            let format = mklong(directive.raw, directive.conversion)?;
            emit_numeric(
                &format,
                directive.controls,
                fish_printf::Arg::SInt(value, 64),
                stdout,
            )
        }
        ConversionValue::Unsigned(value) => {
            let format = mklong(directive.raw, directive.conversion)?;
            emit_numeric(
                &format,
                directive.controls,
                fish_printf::Arg::UInt(value),
                stdout,
            )
        }
        ConversionValue::Float(value) => {
            // glibc anchors subnormal hexadecimal output at p-1022,
            // while the musl-derived formatter normalizes it further.
            if matches!(directive.conversion, b'a' | b'A') && value.is_subnormal() {
                emit_subnormal_hex_float(value, directive, stdout)
            } else {
                emit_numeric(
                    directive.raw,
                    directive.controls,
                    fish_printf::Arg::Float(value),
                    stdout,
                )
            }
        }
    }
}

fn emit_string<W: Write>(value: &[u8], directive: Directive<'_>, stdout: &mut W) -> RunResult<()> {
    let Some(layout) = output_layout(directive) else {
        return Ok(());
    };
    let output_length = layout
        .precision
        .map_or(value.len(), |precision| value.len().min(precision));
    let padding = layout.width.saturating_sub(output_length);
    if !layout.left_adjust {
        write_spaces(stdout, padding)?;
    }
    stdout.write_all(&value[..output_length])?;
    if layout.left_adjust {
        write_spaces(stdout, padding)?;
    }
    Ok(())
}

fn emit_character<W: Write>(value: u8, directive: Directive<'_>, stdout: &mut W) -> RunResult<()> {
    let Some(layout) = output_layout(directive) else {
        return Ok(());
    };
    let padding = layout.width.saturating_sub(1);
    if !layout.left_adjust {
        write_spaces(stdout, padding)?;
    }
    stdout.write_all(&[value])?;
    if layout.left_adjust {
        write_spaces(stdout, padding)?;
    }
    Ok(())
}

fn emit_subnormal_hex_float<W: Write>(
    value: f64,
    directive: Directive<'_>,
    stdout: &mut W,
) -> RunResult<()> {
    let Some(layout) = output_layout(directive) else {
        return Ok(());
    };
    let uppercase = directive.conversion == b'A';
    let fraction_bits = value.to_bits() & ((1_u64 << 52) - 1);
    let default_precision = 13 - (fraction_bits.trailing_zeros() as usize / 4).min(13);
    let fraction_length = layout.precision.unwrap_or(default_precision);
    let show_point = fraction_length != 0 || layout.alternate_form;
    let sign = if value.is_sign_negative() {
        Some(b'-')
    } else if layout.force_sign {
        Some(b'+')
    } else if layout.space_sign {
        Some(b' ')
    } else {
        None
    };

    let content_length = usize::from(sign.is_some())
        .checked_add(2)
        .and_then(|length| length.checked_add(1))
        .and_then(|length| length.checked_add(usize::from(show_point)))
        .and_then(|length| length.checked_add(fraction_length))
        .and_then(|length| length.checked_add(6))
        .ok_or(RunError::Allocation)?;
    let padding = layout.width.saturating_sub(content_length);
    let zero_padding = layout.zero_pad && !layout.left_adjust;

    if !layout.left_adjust && !zero_padding {
        write_spaces(stdout, padding)?;
    }
    if let Some(sign) = sign {
        stdout.write_all(&[sign])?;
    }
    stdout.write_all(if uppercase { b"0X" } else { b"0x" })?;
    if zero_padding {
        write_zeros(stdout, padding)?;
    }

    let mut leading_digit = 0_u8;
    let mut rounded_fraction = None;
    if fraction_length < 13 {
        let discarded_bits = (13 - fraction_length) * 4;
        let mut kept = fraction_bits >> discarded_bits;
        let discarded_mask = (1_u64 << discarded_bits) - 1;
        let discarded = fraction_bits & discarded_mask;
        let halfway = 1_u64 << (discarded_bits - 1);
        if discarded > halfway || (discarded == halfway && kept & 1 != 0) {
            kept += 1;
        }
        let carry = 1_u64 << (fraction_length * 4);
        if kept == carry {
            leading_digit = 1;
            kept = 0;
        }
        rounded_fraction = Some(kept);
    }

    stdout.write_all(&[b'0' + leading_digit])?;
    if show_point {
        stdout.write_all(b".")?;
    }
    if let Some(fraction) = rounded_fraction {
        write_hex_fraction(stdout, fraction, fraction_length, uppercase)?;
    } else {
        let exact_digits = fraction_length.min(13);
        for index in 0..exact_digits {
            let shift = (12 - index) * 4;
            write_hex_digit(stdout, ((fraction_bits >> shift) & 0xf) as u8, uppercase)?;
        }
        write_zeros(stdout, fraction_length.saturating_sub(exact_digits))?;
    }
    stdout.write_all(if uppercase { b"P-1022" } else { b"p-1022" })?;
    if layout.left_adjust {
        write_spaces(stdout, padding)?;
    }
    Ok(())
}

fn write_hex_fraction<W: Write>(
    stdout: &mut W,
    fraction: u64,
    digits: usize,
    uppercase: bool,
) -> RunResult<()> {
    for index in 0..digits {
        let shift = (digits - index - 1) * 4;
        write_hex_digit(stdout, ((fraction >> shift) & 0xf) as u8, uppercase)?;
    }
    Ok(())
}

fn write_hex_digit<W: Write>(stdout: &mut W, digit: u8, uppercase: bool) -> RunResult<()> {
    let byte = match digit {
        0..=9 => b'0' + digit,
        10..=15 if uppercase => b'A' + digit - 10,
        10..=15 => b'a' + digit - 10,
        _ => return Err(RunError::Formatter),
    };
    stdout.write_all(&[byte])?;
    Ok(())
}

fn conversion_issue(operand: &[u8], end_index: usize, range_error: bool) -> ConversionIssue {
    if end_index < operand.len() {
        if end_index == 0 {
            ConversionIssue::NoDigits
        } else {
            ConversionIssue::Trailing
        }
    } else if range_error {
        ConversionIssue::Range
    } else {
        ConversionIssue::None
    }
}

fn is_c_whitespace(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | 0x0b | 0x0c | b'\r')
}

fn integer_start(operand: &[u8]) -> (usize, bool) {
    let mut index = 0;
    while operand
        .get(index)
        .is_some_and(|byte| is_c_whitespace(*byte))
    {
        index += 1;
    }
    let negative = match operand.get(index) {
        Some(b'-') => {
            index += 1;
            true
        }
        Some(b'+') => {
            index += 1;
            false
        }
        _ => false,
    };
    (index, negative)
}

fn integer_base(operand: &[u8], index: usize) -> (u8, usize) {
    if operand.get(index) == Some(&b'0') {
        if matches!(operand.get(index + 1), Some(b'x' | b'X'))
            && operand
                .get(index + 2)
                .and_then(|byte| hextobin(*byte))
                .is_some()
        {
            (16, index + 2)
        } else {
            (8, index)
        }
    } else {
        (10, index)
    }
}

fn parse_magnitude(operand: &[u8], mut index: usize, base: u8, limit: u64) -> (u64, usize, bool) {
    let mut value = 0_u64;
    let mut range_error = false;
    while let Some(digit) = operand
        .get(index)
        .and_then(|byte| digit_for_base(*byte, base))
    {
        if value > (limit - u64::from(digit)) / u64::from(base) {
            value = limit;
            range_error = true;
        } else if !range_error {
            value = value * u64::from(base) + u64::from(digit);
        }
        index += 1;
    }
    (value, index, range_error)
}

fn digit_for_base(byte: u8, base: u8) -> Option<u8> {
    let digit = hextobin(byte)?;
    (digit < base).then_some(digit)
}

fn starts_ascii_case_insensitive(value: &[u8], prefix: &[u8]) -> bool {
    value
        .get(..prefix.len())
        .is_some_and(|candidate| candidate.eq_ignore_ascii_case(prefix))
}

fn scan_hex_float(value: &[u8]) -> usize {
    let mut index = 0;
    let mut digits = 0;
    while value.get(index).and_then(|byte| hextobin(*byte)).is_some() {
        index += 1;
        digits += 1;
    }
    if value.get(index) == Some(&b'.') {
        index += 1;
        while value.get(index).and_then(|byte| hextobin(*byte)).is_some() {
            index += 1;
            digits += 1;
        }
    }
    if digits == 0 {
        return 0;
    }

    if matches!(value.get(index), Some(b'p' | b'P')) {
        let marker = index;
        let mut cursor = index + 1;
        if matches!(value.get(cursor), Some(b'+' | b'-')) {
            cursor += 1;
        }
        let exponent_start = cursor;
        while value.get(cursor).is_some_and(u8::is_ascii_digit) {
            cursor += 1;
        }
        if cursor > exponent_start {
            index = cursor;
        } else {
            index = marker;
        }
    }
    index
}

// Convert the hexadecimal significand directly: lexical-core 1.0.6's
// short C-hex path assumes equal mantissa and exponent bases.
fn parse_hex_float(body: &[u8]) -> Option<(f64, bool)> {
    let significand_end = body
        .iter()
        .position(|byte| matches!(byte, b'p' | b'P'))
        .unwrap_or(body.len());
    let (fraction_digits, bit_length) = hex_significand_metadata(&body[..significand_end])?;
    if bit_length == 0 {
        return Some((0.0, false));
    }

    let explicit_exponent = if significand_end < body.len() {
        parse_decimal_exponent(&body[significand_end + 1..])?
    } else {
        0
    };
    let fraction_exponent = i128::try_from(fraction_digits).ok()?.checked_mul(4)?;
    let binary_scale = explicit_exponent.saturating_sub(fraction_exponent);
    let mut exponent = (bit_length - 1).saturating_add(binary_scale);

    if exponent >= -1022 {
        if exponent > 1023 {
            return Some((f64::INFINITY, true));
        }

        let (mut significand, round_bit, sticky) = collect_hex_bits(body, 53)?;
        if bit_length < 53 {
            significand <<= u32::try_from(53 - bit_length).ok()?;
        } else if round_bit && (sticky || significand & 1 != 0) {
            significand += 1;
            if significand == 1_u64 << 53 {
                significand >>= 1;
                exponent += 1;
                if exponent > 1023 {
                    return Some((f64::INFINITY, true));
                }
            }
        }

        let exponent_bits = u64::try_from(exponent + 1023).ok()? << 52;
        let fraction_bits = significand & ((1_u64 << 52) - 1);
        return Some((f64::from_bits(exponent_bits | fraction_bits), false));
    }

    // Subnormal values are integral multiples of 2^-1074.
    let unit_scale = binary_scale.saturating_add(1074);
    if unit_scale >= 0 {
        let keep = usize::try_from(bit_length).ok()?;
        let (significand, _, _) = collect_hex_bits(body, keep)?;
        let shift = u32::try_from(unit_scale).ok()?;
        return significand
            .checked_shl(shift)
            .map(f64::from_bits)
            .map(|value| (value, false));
    }

    let discarded_bits = unit_scale.checked_neg()?;
    if discarded_bits > bit_length {
        return Some((0.0, true));
    }
    let keep = usize::try_from(bit_length - discarded_bits).ok()?;
    let (mut units, round_bit, sticky) = collect_hex_bits(body, keep)?;
    if round_bit && (sticky || units & 1 != 0) {
        units += 1;
    }
    Some((f64::from_bits(units), round_bit || sticky))
}

fn hex_significand_metadata(value: &[u8]) -> Option<(usize, i128)> {
    let mut after_decimal = false;
    let mut fraction_digits = 0_usize;
    let mut significant_digits = 0_usize;
    let mut first_digit_bits = 0_u32;

    for byte in value {
        if *byte == b'.' {
            after_decimal = true;
            continue;
        }
        let digit = hextobin(*byte)?;
        if after_decimal {
            fraction_digits = fraction_digits.checked_add(1)?;
        }
        if significant_digits != 0 || digit != 0 {
            if significant_digits == 0 {
                first_digit_bits = u8::BITS - digit.leading_zeros();
            }
            significant_digits = significant_digits.checked_add(1)?;
        }
    }

    if significant_digits == 0 {
        return Some((fraction_digits, 0));
    }
    let trailing_bits = i128::try_from(significant_digits - 1)
        .ok()?
        .checked_mul(4)?;
    Some((
        fraction_digits,
        trailing_bits.checked_add(i128::from(first_digit_bits))?,
    ))
}

fn collect_hex_bits(value: &[u8], keep: usize) -> Option<(u64, bool, bool)> {
    let mut started = false;
    let mut bit_index = 0_usize;
    let mut kept = 0_u64;
    let mut round_bit = false;
    let mut sticky = false;

    for byte in value.iter().take_while(|byte| !matches!(byte, b'p' | b'P')) {
        if *byte == b'.' {
            continue;
        }
        let digit = hextobin(*byte)?;
        for shift in (0..4).rev() {
            let bit = (digit >> shift) & 1;
            if !started {
                if bit == 0 {
                    continue;
                }
                started = true;
            }

            if bit_index < keep {
                kept = (kept << 1) | u64::from(bit);
            } else if bit_index == keep {
                round_bit = bit != 0;
            } else {
                sticky |= bit != 0;
            }
            bit_index = bit_index.saturating_add(1);
        }
    }
    Some((kept, round_bit, sticky))
}

fn parse_decimal_exponent(value: &[u8]) -> Option<i128> {
    let (negative, digits) = match value.first() {
        Some(b'-') => (true, &value[1..]),
        Some(b'+') => (false, &value[1..]),
        _ => (false, value),
    };
    if digits.is_empty() {
        return None;
    }

    let mut exponent = 0_i128;
    for byte in digits {
        let digit = match byte {
            b'0'..=b'9' => i128::from(*byte - b'0'),
            _ => return None,
        };
        exponent = exponent.saturating_mul(10).saturating_add(digit);
    }
    Some(if negative { -exponent } else { exponent })
}

fn decimal_range_error(value: f64, source: &[u8]) -> Option<bool> {
    let source_nonzero = source
        .iter()
        .take_while(|byte| !matches!(byte, b'e' | b'E'))
        .any(|byte| matches!(byte, b'1'..=b'9'));
    if !source_nonzero {
        return Some(false);
    }
    if value.is_infinite() || value == 0.0 {
        return Some(true);
    }

    let magnitude = value.abs();
    if magnitude < f64::MIN_POSITIVE {
        let units = magnitude.to_bits();
        return compare_decimal_to_binary_fraction(source, units, 1074)
            .map(|ordering| ordering != Ordering::Equal);
    }
    if magnitude == f64::MIN_POSITIVE {
        // glibc's decimal path reports underflow below
        // 2^-1022 - 2^-1076, even when rounding produces DBL_MIN.
        return compare_decimal_to_binary_fraction(source, (1_u64 << 54) - 1, 1076)
            .map(|ordering| ordering == Ordering::Less);
    }
    Some(false)
}

fn compare_decimal_to_binary_fraction(
    source: &[u8],
    numerator: u64,
    denominator_power: u32,
) -> Option<Ordering> {
    // numerator * 2^-power equals (numerator * 5^power) * 10^-power.
    let exponent_index = source
        .iter()
        .position(|byte| matches!(byte, b'e' | b'E'))
        .unwrap_or(source.len());
    let significand = &source[..exponent_index];
    let explicit_exponent = if exponent_index < source.len() {
        parse_decimal_exponent(&source[exponent_index + 1..])?
    } else {
        0
    };

    let mut after_decimal = false;
    let mut fraction_digits = 0_usize;
    let mut saw_nonzero = false;
    let mut significant_digits = 0_usize;
    let mut trailing_zeros = 0_usize;
    for byte in significand {
        if *byte == b'.' {
            after_decimal = true;
            continue;
        }
        let digit = match byte {
            b'0'..=b'9' => *byte - b'0',
            _ => return None,
        };
        if after_decimal {
            fraction_digits = fraction_digits.checked_add(1)?;
        }
        if !saw_nonzero && digit == 0 {
            continue;
        }
        saw_nonzero = true;
        significant_digits = significant_digits.checked_add(1)?;
        if digit == 0 {
            trailing_zeros = trailing_zeros.checked_add(1)?;
        } else {
            trailing_zeros = 0;
        }
    }
    if !saw_nonzero {
        return Some(Ordering::Less);
    }

    let canonical_length = significant_digits.checked_sub(trailing_zeros)?;
    let source_power = explicit_exponent
        .saturating_sub(i128::try_from(fraction_digits).ok()?)
        .saturating_add(i128::try_from(trailing_zeros).ok()?);
    let decimal_shift = source_power.saturating_add(i128::from(denominator_power));

    let mut target = [0_u8; DECIMAL_BIG_CAPACITY];
    let mut target_length = 0_usize;
    let mut remaining = numerator;
    while remaining != 0 {
        *target.get_mut(target_length)? = (remaining % 10) as u8;
        target_length += 1;
        remaining /= 10;
    }
    for _ in 0..denominator_power {
        multiply_decimal(&mut target, &mut target_length, 5)?;
    }

    let left_zeros = decimal_shift.max(0);
    let right_zeros = decimal_shift.min(0).checked_neg()?;
    let left_length = i128::try_from(canonical_length)
        .ok()?
        .checked_add(left_zeros)?;
    let right_length = i128::try_from(target_length)
        .ok()?
        .checked_add(right_zeros)?;
    match left_length.cmp(&right_length) {
        Ordering::Equal => {}
        ordering => return Some(ordering),
    }

    let total_length = usize::try_from(left_length).ok()?;
    let mut source_digits = significand
        .iter()
        .filter_map(|byte| match byte {
            b'0'..=b'9' => Some(*byte - b'0'),
            _ => None,
        })
        .skip_while(|digit| *digit == 0)
        .take(canonical_length);
    for index in 0..total_length {
        let left = if index < canonical_length {
            source_digits.next()?
        } else {
            0
        };
        let right = if index < target_length {
            target[target_length - index - 1]
        } else {
            0
        };
        match left.cmp(&right) {
            Ordering::Equal => {}
            ordering => return Some(ordering),
        }
    }
    Some(Ordering::Equal)
}

fn multiply_decimal(digits: &mut [u8], length: &mut usize, multiplier: u8) -> Option<()> {
    let mut carry = 0_u16;
    for digit in &mut digits[..*length] {
        let product = u16::from(*digit) * u16::from(multiplier) + carry;
        *digit = (product % 10) as u8;
        carry = product / 10;
    }
    while carry != 0 {
        *digits.get_mut(*length)? = (carry % 10) as u8;
        *length += 1;
        carry /= 10;
    }
    Some(())
}

fn emit_numeric<W: Write>(
    format: &[u8],
    controls: DynamicControls,
    value: fish_printf::Arg<'_>,
    stdout: &mut W,
) -> RunResult<()> {
    let format = std::str::from_utf8(format).map_err(|_| RunError::Formatter)?;
    let mut arguments = Vec::new();
    arguments
        .try_reserve_exact(3)
        .map_err(|_| RunError::Allocation)?;
    if let Some(width) = controls.field_width {
        arguments.push(fish_printf::Arg::SInt(i64::from(width), 32));
    }
    if let Some(precision) = controls.precision {
        arguments.push(fish_printf::Arg::SInt(i64::from(precision), 32));
    }
    arguments.push(value);

    let mut writer = IoFmtWriter::new(stdout);
    let format_result = fish_printf::printf_c_locale(&mut writer, format, &mut arguments);
    writer.finish()?;
    format_result.map(|_| ()).map_err(|_| RunError::Formatter)
}

#[derive(Clone, Copy, Debug, Default)]
struct OutputLayout {
    alternate_form: bool,
    left_adjust: bool,
    force_sign: bool,
    space_sign: bool,
    zero_pad: bool,
    width: usize,
    precision: Option<usize>,
}

fn output_layout(directive: Directive<'_>) -> Option<OutputLayout> {
    let mut layout = OutputLayout::default();
    let mut index = 1;
    while directive
        .raw
        .get(index)
        .is_some_and(|byte| SKIP1.contains(byte))
    {
        match directive.raw[index] {
            b'#' => layout.alternate_form = true,
            b'-' => layout.left_adjust = true,
            b'+' => layout.force_sign = true,
            b' ' => layout.space_sign = true,
            b'0' => layout.zero_pad = true,
            _ => {}
        }
        index += 1;
    }

    if directive.raw.get(index) == Some(&b'*') {
        let width = directive.controls.field_width.unwrap_or(0);
        layout.left_adjust |= width < 0;
        layout.width = width.unsigned_abs() as usize;
        index += 1;
    } else {
        layout.width = parse_static_control(directive.raw, &mut index)?;
    }

    if directive.raw.get(index) == Some(&b'.') {
        index += 1;
        if directive.raw.get(index) == Some(&b'*') {
            layout.precision = directive
                .controls
                .precision
                .filter(|precision| *precision >= 0)
                .map(|precision| precision as usize);
        } else {
            layout.precision = Some(parse_static_control(directive.raw, &mut index)?);
        }
    }
    Some(layout)
}

fn parse_static_control(value: &[u8], index: &mut usize) -> Option<usize> {
    let mut parsed = 0_u32;
    while let Some(byte @ b'0'..=b'9') = value.get(*index) {
        parsed = parsed
            .checked_mul(10)?
            .checked_add(u32::from(*byte - b'0'))?;
        if parsed > i32::MAX as u32 {
            return None;
        }
        *index += 1;
    }
    Some(parsed as usize)
}

fn write_spaces<W: Write>(stdout: &mut W, mut count: usize) -> RunResult<()> {
    const SPACES: [u8; 64] = [b' '; 64];
    while count > 0 {
        let chunk = count.min(SPACES.len());
        stdout.write_all(&SPACES[..chunk])?;
        count -= chunk;
    }
    Ok(())
}

fn write_zeros<W: Write>(stdout: &mut W, mut count: usize) -> RunResult<()> {
    const ZEROS: [u8; 64] = [b'0'; 64];
    while count > 0 {
        let chunk = count.min(ZEROS.len());
        stdout.write_all(&ZEROS[..chunk])?;
        count -= chunk;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io;

    #[derive(Debug, Default)]
    struct RunHarness {
        stdout: Vec<u8>,
        stderr: Vec<u8>,
    }

    impl RunHarness {
        fn run(&mut self, args: &[Vec<u8>]) -> RunResult<u8> {
            super::run(args, &mut self.stdout, &mut self.stderr)
        }

        fn stdout(&self) -> &[u8] {
            &self.stdout
        }

        fn stderr(&self) -> &[u8] {
            &self.stderr
        }
    }

    #[derive(Debug)]
    struct FailingWriter {
        remaining: usize,
        written: Vec<u8>,
    }

    impl FailingWriter {
        fn after(byte_count: usize) -> Self {
            Self {
                remaining: byte_count,
                written: Vec::new(),
            }
        }

        fn written(&self) -> &[u8] {
            &self.written
        }
    }

    impl Write for FailingWriter {
        fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
            if self.remaining == 0 {
                return Err(io::Error::new(
                    io::ErrorKind::Other,
                    "injected writer failure",
                ));
            }

            let written = buffer.len().min(self.remaining);
            self.remaining -= written;
            self.written.extend_from_slice(&buffer[..written]);
            Ok(written)
        }

        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }

    mod cli_state {
        use super::*;

        #[test]
        fn no_format_writes_exact_usage_to_stderr() {
            let mut harness = RunHarness::default();

            let status = harness.run(&[b"printf".to_vec()]).unwrap();

            assert_eq!(status, 1);
            assert_eq!(harness.stdout(), b"");
            assert_eq!(harness.stderr(), b"usage: printf format [argument ...]\n");
        }

        #[test]
        fn double_dash_without_format_is_usage() {
            let mut harness = RunHarness::default();

            let status = harness.run(&[b"printf".to_vec(), b"--".to_vec()]).unwrap();

            assert_eq!(status, 1);
            assert_eq!(harness.stdout(), b"");
            assert_eq!(harness.stderr(), b"usage: printf format [argument ...]\n");
        }

        #[test]
        fn double_dash_is_discarded_once() {
            let mut harness = RunHarness::default();

            let status = harness
                .run(&[b"printf".to_vec(), b"--".to_vec(), b"--".to_vec()])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), b"--");
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn other_dash_prefix_is_a_format() {
            let mut harness = RunHarness::default();

            let status = harness.run(&[b"printf".to_vec(), b"-n".to_vec()]).unwrap();

            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), b"-n");
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn argv_zero_basename_prefixes_diagnostics() {
            let mut stderr = Vec::new();
            let program_name = short_program_name(b"/tmp/tools/printf-alias");

            warnx(program_name, b"diagnostic", &mut stderr).unwrap();

            assert_eq!(program_name, b"printf-alias");
            assert_eq!(stderr, b"printf-alias: diagnostic\n");
        }

        #[test]
        fn non_utf8_argv_is_preserved() {
            let mut stderr = Vec::new();
            let program_name = short_program_name(b"/tmp/\xffprintf");

            warnx(program_name, b"bad \xfe value", &mut stderr).unwrap();

            assert_eq!(program_name, b"\xffprintf");
            assert_eq!(stderr, b"\xffprintf: bad \xfe value\n");
        }

        #[test]
        fn format_repeats_only_after_operand_consumption() {
            let mut repeated = RunHarness::default();
            let status = repeated
                .run(&[
                    b"printf".to_vec(),
                    b"%s:%s;".to_vec(),
                    b"a".to_vec(),
                    b"b".to_vec(),
                    b"c".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(repeated.stdout(), b"a:b;c:;");
            assert_eq!(repeated.stderr(), b"");

            let mut no_consumption = RunHarness::default();
            let status = no_consumption
                .run(&[
                    b"printf".to_vec(),
                    b"literal:%%".to_vec(),
                    b"ignored-one".to_vec(),
                    b"ignored-two".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(no_consumption.stdout(), b"literal:%");
            assert_eq!(no_consumption.stderr(), b"");
        }

        #[test]
        fn shortage_defaults_complete_the_current_pass() {
            let mut values = RunHarness::default();
            let status = values
                .run(&[b"printf".to_vec(), b"%s|%c|%*.*s".to_vec(), b"ok".to_vec()])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(values.stdout(), &[b'o', b'k', b'|', 0, b'|']);
            assert_eq!(values.stderr(), b"");

            let mut width_only = RunHarness::default();
            let status = width_only
                .run(&[b"printf".to_vec(), b"%*s".to_vec(), b"3".to_vec()])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(width_only.stdout(), b"   ");
            assert_eq!(width_only.stderr(), b"");
        }
    }

    mod escapes {
        use super::*;

        fn run_case(args: Vec<Vec<u8>>) -> (u8, RunHarness) {
            let mut harness = RunHarness::default();
            let status = harness.run(&args).unwrap();
            (status, harness)
        }

        #[test]
        fn all_simple_escapes_emit_exact_bytes() {
            let cases: &[(&[u8], u8)] = &[
                (br"\\", b'\\'),
                (br"\'", b'\''),
                (br#"\""#, b'"'),
                (br"\a", 0x07),
                (br"\b", 0x08),
                (br"\e", 0x1b),
                (br"\f", 0x0c),
                (br"\n", b'\n'),
                (br"\r", b'\r'),
                (br"\t", b'\t'),
                (br"\v", 0x0b),
            ];

            for &(escape, expected) in cases {
                let (status, top_level) = run_case(vec![b"printf".to_vec(), escape.to_vec()]);
                assert_eq!(status, 0, "top-level escape {escape:?}");
                assert_eq!(
                    top_level.stdout(),
                    &[expected],
                    "top-level escape {escape:?}"
                );
                assert_eq!(top_level.stderr(), b"", "top-level escape {escape:?}");

                let (status, percent_b) =
                    run_case(vec![b"printf".to_vec(), b"%b".to_vec(), escape.to_vec()]);
                assert_eq!(status, 0, "%b escape {escape:?}");
                assert_eq!(percent_b.stdout(), &[expected], "%b escape {escape:?}");
                assert_eq!(percent_b.stderr(), b"", "%b escape {escape:?}");
            }
        }

        #[test]
        fn octal_consumes_zero_to_three_digits_at_boundaries() {
            let standard_cases: &[(&[u8], &[u8])] = &[
                (br"\1Z", &[0x01, b'Z']),
                (br"\12Z", &[0x0a, b'Z']),
                (br"\1234", &[0x53, b'4']),
                (br"\777", &[0xff]),
            ];
            for &(format, expected) in standard_cases {
                let (status, harness) = run_case(vec![b"printf".to_vec(), format.to_vec()]);
                assert_eq!(status, 0, "octal format {format:?}");
                assert_eq!(harness.stdout(), expected, "octal format {format:?}");
                assert_eq!(harness.stderr(), b"", "octal format {format:?}");
            }

            let marker_cases: &[(&[u8], &[u8])] = &[
                (br"\0Z", &[0x00, b'Z']),
                (br"\01Z", &[0x01, b'Z']),
                (br"\012Z", &[0x0a, b'Z']),
                (br"\0123Z", &[0x53, b'Z']),
                (br"\0777", &[0xff]),
            ];
            for &(operand, expected) in marker_cases {
                let (status, harness) =
                    run_case(vec![b"printf".to_vec(), b"%b".to_vec(), operand.to_vec()]);
                assert_eq!(status, 0, "%b octal operand {operand:?}");
                assert_eq!(harness.stdout(), expected, "%b octal operand {operand:?}");
                assert_eq!(harness.stderr(), b"", "%b octal operand {operand:?}");
            }
        }

        #[test]
        fn hex_consumes_zero_to_two_digits_at_boundaries() {
            let cases: &[(&[u8], &[u8])] = &[
                (br"\xZ", &[0x00, b'Z']),
                (br"\x4Z", &[0x04, b'Z']),
                (br"\x41Z", &[b'A', b'Z']),
                (br"\x414", &[b'A', b'4']),
                (br"\xff", &[0xff]),
            ];

            for &(format, expected) in cases {
                let (status, harness) = run_case(vec![b"printf".to_vec(), format.to_vec()]);
                assert_eq!(status, 0, "hex format {format:?}");
                assert_eq!(harness.stdout(), expected, "hex format {format:?}");
                assert_eq!(harness.stderr(), b"", "hex format {format:?}");
            }
        }

        #[test]
        fn unknown_escape_warns_and_sets_sticky_status() {
            let (status, harness) =
                run_case(vec![b"/tmp/escape-alias".to_vec(), br"A\qB\n".to_vec()]);

            assert_eq!(status, 1);
            assert_eq!(harness.stdout(), b"AqB\n");
            assert_eq!(
                harness.stderr(),
                b"escape-alias: unknown escape sequence `\\q'\n"
            );
        }

        #[test]
        fn trailing_backslash_warns_without_output_byte() {
            let (status, harness) = run_case(vec![b"printf".to_vec(), b"before\\".to_vec()]);

            assert_eq!(status, 1);
            assert_eq!(harness.stdout(), b"before");
            assert_eq!(harness.stderr(), b"printf: null escape sequence\n");
        }

        #[test]
        fn percent_b_marker_octal_consumes_marker_plus_digits() {
            let (status, top_level) = run_case(vec![b"printf".to_vec(), br"\0123".to_vec()]);
            assert_eq!(status, 0);
            assert_eq!(top_level.stdout(), &[0x0a, b'3']);
            assert_eq!(top_level.stderr(), b"");

            let (status, percent_b) =
                run_case(vec![b"printf".to_vec(), b"%b".to_vec(), br"\0123".to_vec()]);
            assert_eq!(status, 0);
            assert_eq!(percent_b.stdout(), &[0x53]);
            assert_eq!(percent_b.stderr(), b"");
        }

        #[test]
        fn percent_b_cancel_suppresses_remaining_command() {
            let (status, harness) = run_case(vec![
                b"printf".to_vec(),
                b"head:%b:tail:%b".to_vec(),
                br"one\n\cignored".to_vec(),
                b"second".to_vec(),
            ]);

            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), b"head:one\n");
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn percent_b_cancel_returns_prior_sticky_status() {
            let (status, harness) = run_case(vec![
                b"/tmp/escape-alias".to_vec(),
                b"%bSHOULD-NOT-PRINT".to_vec(),
                br"\q\cignored".to_vec(),
            ]);

            assert_eq!(status, 1);
            assert_eq!(harness.stdout(), b"q");
            assert_eq!(
                harness.stderr(),
                b"escape-alias: unknown escape sequence `\\q'\n"
            );
        }
    }

    mod operand_getters {
        use super::*;

        #[test]
        fn getstr_and_getchr_consume_or_default() {
            let operands = vec![b"alpha".to_vec(), Vec::new(), vec![0xff, b'z']];
            let mut state = State::new(&operands, b"printf");

            assert_eq!(state.getstr(), b"alpha");
            assert_eq!(state.cursor, 1);
            assert_eq!(state.getstr(), b"");
            assert_eq!(state.cursor, 2);
            assert_eq!(state.getchr(), 0xff);
            assert_eq!(state.cursor, 3);

            assert_eq!(state.getstr(), b"");
            assert_eq!(state.getchr(), 0);
            assert_eq!(state.cursor, 3);
        }

        #[test]
        fn getint_peeks_invalid_initial_byte() {
            let operands = vec![
                b"x7".to_vec(),
                b" 7".to_vec(),
                Vec::new(),
                vec![0xff, b'7'],
                b"9".to_vec(),
            ];
            let mut state = State::new(&operands, b"printf");

            for expected in [b"x7".as_slice(), b" 7", b"", b"\xff7"] {
                let cursor = state.cursor;
                assert_eq!(state.getint(), 0);
                assert_eq!(state.cursor, cursor);
                assert_eq!(state.getstr(), expected);
            }

            assert_eq!(state.getint(), 9);
            assert_eq!(state.cursor, operands.len());
        }

        #[test]
        fn getint_consumes_number_start_and_uses_decimal_prefix() {
            let cases: &[(&[u8], i32)] = &[
                (b".", 0),
                (b"+", 0),
                (b"-", 0),
                (b"17tail", 17),
                (b"-12suffix", -12),
                (b"+003x", 3),
                (b"2147483648", i32::MIN),
                (b"4294967296tail", 0),
                (b"4294967297", 1),
                (b"9223372036854775808", -1),
                (b"-9223372036854775809", 0),
            ];
            let operands: Vec<Vec<u8>> = cases.iter().map(|(value, _)| value.to_vec()).collect();
            let mut state = State::new(&operands, b"printf");

            for (index, (_, expected)) in cases.iter().enumerate() {
                assert_eq!(state.getint(), *expected, "case {index}");
                assert_eq!(state.cursor, index + 1, "case {index}");
            }
        }

        #[test]
        fn dynamic_controls_and_quote_operands_follow_source_consumption() {
            let operands = vec![
                b"7".to_vec(),
                b"''".to_vec(),
                b"0".to_vec(),
                b"123.456".to_vec(),
            ];
            let mut state = State::new(&operands, b"printf");
            let mut stderr = Vec::new();

            assert_eq!(state.getint(), 7);
            assert_eq!(state.getlong(&mut stderr).unwrap(), 39);
            assert_eq!(state.getulong(&mut stderr).unwrap(), 0);
            assert_eq!(state.getdouble(&mut stderr).unwrap(), 123.456);
            assert_eq!(state.cursor, operands.len());
            assert_eq!(stderr, b"");
        }

        #[test]
        fn quoted_numeric_operand_returns_second_byte_or_nul() {
            let operands = vec![
                b"'A".to_vec(),
                b"\"".to_vec(),
                b"''".to_vec(),
                vec![b'"', 0xff],
            ];
            let mut state = State::new(&operands, b"printf");
            let mut stderr = Vec::new();

            assert_eq!(state.getlong(&mut stderr).unwrap(), 65);
            assert_eq!(state.getulong(&mut stderr).unwrap(), 0);
            assert_eq!(state.getlong(&mut stderr).unwrap(), 39);
            assert_eq!(state.getulong(&mut stderr).unwrap(), 255);
            assert_eq!(state.cursor, operands.len());
            assert_eq!(stderr, b"");
            assert_eq!(state.rval, 0);
        }

        #[test]
        fn signed_base_zero_boundaries_and_saturation() {
            let cases: &[(&[u8], i64, bool)] = &[
                (b"0", 0, false),
                (b"  +42", 42, false),
                (b"077", 63, false),
                (b"-077", -63, false),
                (b"0x2a", 42, false),
                (b"-0X2A", -42, false),
                (b"9223372036854775807", i64::MAX, false),
                (b"-9223372036854775808", i64::MIN, false),
                (b"9223372036854775808", i64::MAX, true),
                (b"-9223372036854775809", i64::MIN, true),
                (b"0xffffffffffffffff", i64::MAX, true),
            ];

            for &(operand, expected, range_error) in cases {
                let parsed = parse_signed(operand);
                assert_eq!(parsed.value, expected, "operand {operand:?}");
                assert_eq!(parsed.end_index, operand.len(), "operand {operand:?}");
                assert_eq!(parsed.range_error, range_error, "operand {operand:?}");
            }
        }

        #[test]
        fn unsigned_base_zero_negative_wrap_and_saturation() {
            let cases: &[(&[u8], u64, bool)] = &[
                (b"0", 0, false),
                (b"  +42", 42, false),
                (b"077", 63, false),
                (b"0x2a", 42, false),
                (b"18446744073709551615", u64::MAX, false),
                (b"01777777777777777777777", u64::MAX, false),
                (b"-1", u64::MAX, false),
                (b"-18446744073709551615", 1, false),
                (b"18446744073709551616", u64::MAX, true),
                (b"02000000000000000000000", u64::MAX, true),
                (b"-18446744073709551616", u64::MAX, true),
            ];

            for &(operand, expected, range_error) in cases {
                let parsed = parse_unsigned(operand);
                assert_eq!(parsed.value, expected, "operand {operand:?}");
                assert_eq!(parsed.end_index, operand.len(), "operand {operand:?}");
                assert_eq!(parsed.range_error, range_error, "operand {operand:?}");
            }
        }

        #[test]
        fn integer_partial_and_no_digit_metadata() {
            for operand in [
                b"".as_slice(),
                b"word".as_slice(),
                b" \t+".as_slice(),
                b"-".as_slice(),
            ] {
                let parsed = parse_signed(operand);
                assert_eq!(parsed.value, 0, "operand {operand:?}");
                assert_eq!(parsed.end_index, 0, "operand {operand:?}");
                assert!(!parsed.range_error, "operand {operand:?}");
            }

            let partial = parse_signed(b"12tail");
            assert_eq!(partial.value, 12);
            assert_eq!(partial.end_index, 2);
            assert!(!partial.range_error);

            let prefix_without_hex_digit = parse_unsigned(b"0x");
            assert_eq!(prefix_without_hex_digit.value, 0);
            assert_eq!(prefix_without_hex_digit.end_index, 1);
            assert!(!prefix_without_hex_digit.range_error);

            let ranged_partial = parse_signed(b"9223372036854775808tail");
            assert_eq!(ranged_partial.value, i64::MAX);
            assert_eq!(ranged_partial.end_index, b"9223372036854775808".len());
            assert!(ranged_partial.range_error);

            assert_eq!(conversion_issue(b"", 0, false), ConversionIssue::None);
            assert_eq!(
                conversion_issue(b"word", 0, false),
                ConversionIssue::NoDigits
            );
            assert_eq!(
                conversion_issue(b"12tail", 2, false),
                ConversionIssue::Trailing
            );
            assert_eq!(
                conversion_issue(b"9223372036854775808tail", ranged_partial.end_index, true,),
                ConversionIssue::Trailing
            );
            assert_eq!(
                conversion_issue(b"9223372036854775808", 19, true),
                ConversionIssue::Range
            );
        }

        #[test]
        fn decimal_hex_special_float_prefixes() {
            let finite_cases: &[(&[u8], f64, &[u8])] = &[
                (b"  -12.5e+2tail", -1250.0, b"  -12.5e+2"),
                (b".125", 0.125, b".125"),
                (b"+0x1.8p+1suffix", 3.0, b"+0x1.8p+1"),
                (b"-0X.8P-1", -0.25, b"-0X.8P-1"),
                (b"0x1", 1.0, b"0x1"),
            ];
            for &(operand, expected, prefix) in finite_cases {
                let parsed = parse_double(operand).unwrap();
                assert_eq!(parsed.value, expected, "operand {operand:?}");
                assert_eq!(parsed.end_index, prefix.len(), "operand {operand:?}");
                assert!(!parsed.range_error, "operand {operand:?}");
            }

            let positive_zero = parse_double(b"+0").unwrap();
            assert_eq!(positive_zero.value.to_bits(), 0.0_f64.to_bits());
            let negative_zero = parse_double(b"-0").unwrap();
            assert_eq!(negative_zero.value.to_bits(), (-0.0_f64).to_bits());

            let infinity = parse_double(b" \t-InFiNiTy!").unwrap();
            assert_eq!(infinity.value, f64::NEG_INFINITY);
            assert_eq!(infinity.end_index, b" \t-InFiNiTy".len());
            assert!(!infinity.range_error);

            let short_infinity = parse_double(b"+INFrest").unwrap();
            assert_eq!(short_infinity.value, f64::INFINITY);
            assert_eq!(short_infinity.end_index, b"+INF".len());

            let nan = parse_double(b"-NaN(payload)tail").unwrap();
            assert!(nan.value.is_nan());
            assert!(nan.value.is_sign_negative());
            assert_eq!(nan.end_index, b"-NaN(payload)".len());
            assert!(!nan.range_error);

            let malformed_payload = parse_double(b"nan(bad-payload)").unwrap();
            assert!(malformed_payload.value.is_nan());
            assert_eq!(malformed_payload.end_index, b"nan".len());

            let operands = vec![b"'A".to_vec(), b"\"".to_vec(), vec![b'\'', 0xff]];
            let mut state = State::new(&operands, b"printf");
            let mut stderr = Vec::new();
            assert_eq!(state.getdouble(&mut stderr).unwrap(), 65.0);
            assert_eq!(state.getdouble(&mut stderr).unwrap(), 0.0);
            assert_eq!(state.getdouble(&mut stderr).unwrap(), 255.0);
            assert_eq!(state.cursor, operands.len());
            assert_eq!(stderr, b"");
        }

        #[test]
        fn float_partial_overflow_underflow_metadata() {
            fn exact_binary_fraction_operand(numerator: u64, power: u32) -> Vec<u8> {
                let mut digits = [0_u8; DECIMAL_BIG_CAPACITY];
                let mut length = 0_usize;
                let mut remaining = numerator;
                while remaining != 0 {
                    digits[length] = (remaining % 10) as u8;
                    length += 1;
                    remaining /= 10;
                }
                for _ in 0..power {
                    multiply_decimal(&mut digits, &mut length, 5).unwrap();
                }

                let mut operand: Vec<u8> = digits[..length]
                    .iter()
                    .rev()
                    .map(|digit| b'0' + digit)
                    .collect();
                operand.extend_from_slice(format!("e-{power}").as_bytes());
                operand
            }

            for operand in [
                b"".as_slice(),
                b"word".as_slice(),
                b".".as_slice(),
                b" \t+".as_slice(),
            ] {
                let parsed = parse_double(operand).unwrap();
                assert_eq!(parsed.value, 0.0, "operand {operand:?}");
                assert_eq!(parsed.end_index, 0, "operand {operand:?}");
                assert!(!parsed.range_error, "operand {operand:?}");
            }

            let decimal_partial = parse_double(b"1.25tail").unwrap();
            assert_eq!(decimal_partial.value, 1.25);
            assert_eq!(decimal_partial.end_index, b"1.25".len());
            assert!(!decimal_partial.range_error);

            let exponent_partial = parse_double(b"1e").unwrap();
            assert_eq!(exponent_partial.value, 1.0);
            assert_eq!(exponent_partial.end_index, 1);
            assert!(!exponent_partial.range_error);

            let hex_exponent_partial = parse_double(b"0x1p").unwrap();
            assert_eq!(hex_exponent_partial.value, 1.0);
            assert_eq!(hex_exponent_partial.end_index, b"0x1".len());
            assert!(!hex_exponent_partial.range_error);

            for &(operand, expected) in &[
                (b"1e9999".as_slice(), f64::INFINITY),
                (b"-1e9999".as_slice(), f64::NEG_INFINITY),
                (b"0x1p1024".as_slice(), f64::INFINITY),
            ] {
                let parsed = parse_double(operand).unwrap();
                assert_eq!(parsed.value, expected, "operand {operand:?}");
                assert_eq!(parsed.end_index, operand.len(), "operand {operand:?}");
                assert!(parsed.range_error, "operand {operand:?}");
            }

            let decimal_underflow = parse_double(b"1e-9999").unwrap();
            assert_eq!(decimal_underflow.value.to_bits(), 0.0_f64.to_bits());
            assert!(decimal_underflow.range_error);

            let negative_underflow = parse_double(b"-1e-9999").unwrap();
            assert_eq!(negative_underflow.value.to_bits(), (-0.0_f64).to_bits());
            assert!(negative_underflow.range_error);

            let decimal_subnormal = parse_double(b"5e-324").unwrap();
            assert_eq!(decimal_subnormal.value.to_bits(), 1);
            assert!(decimal_subnormal.range_error);

            let hex_subnormal = parse_double(b"0x1p-1074").unwrap();
            assert_eq!(hex_subnormal.value.to_bits(), 1);
            assert!(!hex_subnormal.range_error);

            let equivalent_exact_subnormal = parse_double(b"0x2p-1075").unwrap();
            assert_eq!(equivalent_exact_subnormal.value.to_bits(), 1);
            assert!(!equivalent_exact_subnormal.range_error);

            let hex_halfway_to_zero = parse_double(b"0x1p-1075").unwrap();
            assert_eq!(hex_halfway_to_zero.value.to_bits(), 0);
            assert!(hex_halfway_to_zero.range_error);

            let minimum_normal = parse_double(b"2.2250738585072014e-308").unwrap();
            assert_eq!(minimum_normal.value, f64::MIN_POSITIVE);
            assert!(!minimum_normal.range_error);

            let below_decimal_underflow_threshold =
                parse_double(b"2.22507385850720125e-308").unwrap();
            assert_eq!(below_decimal_underflow_threshold.value, f64::MIN_POSITIVE);
            assert!(below_decimal_underflow_threshold.range_error);
            let above_decimal_underflow_threshold =
                parse_double(b"2.22507385850720126e-308").unwrap();
            assert_eq!(above_decimal_underflow_threshold.value, f64::MIN_POSITIVE);
            assert!(!above_decimal_underflow_threshold.range_error);

            let exact_decimal_subnormal =
                parse_double(&exact_binary_fraction_operand(1, 1074)).unwrap();
            assert_eq!(exact_decimal_subnormal.value.to_bits(), 1);
            assert!(!exact_decimal_subnormal.range_error);
            let exact_decimal_threshold =
                parse_double(&exact_binary_fraction_operand((1_u64 << 54) - 1, 1076)).unwrap();
            assert_eq!(exact_decimal_threshold.value, f64::MIN_POSITIVE);
            assert!(!exact_decimal_threshold.range_error);

            let decimal_maximum = parse_double(b"1.7976931348623157e308").unwrap();
            assert_eq!(decimal_maximum.value, f64::MAX);
            assert!(!decimal_maximum.range_error);
            let decimal_overflow = parse_double(b"1.7976931348623159e308").unwrap();
            assert_eq!(decimal_overflow.value, f64::INFINITY);
            assert!(decimal_overflow.range_error);

            let maximum = parse_double(b"0x1.fffffffffffffp1023").unwrap();
            assert_eq!(maximum.value, f64::MAX);
            assert!(!maximum.range_error);

            let normal_tie_even_down = parse_double(b"0x1.00000000000008p0").unwrap();
            assert_eq!(normal_tie_even_down.value.to_bits(), 1.0_f64.to_bits());
            let normal_tie_even_up = parse_double(b"0x1.00000000000018p0").unwrap();
            assert_eq!(normal_tie_even_up.value.to_bits(), 1.0_f64.to_bits() + 2);
            let normal_above_half = parse_double(b"0x1.000000000000080001p0").unwrap();
            assert_eq!(normal_above_half.value.to_bits(), 1.0_f64.to_bits() + 1);

            let subnormal_tie_even_up = parse_double(b"0x3p-1075").unwrap();
            assert_eq!(subnormal_tie_even_up.value.to_bits(), 2);
            assert!(subnormal_tie_even_up.range_error);
            let subnormal_tie_even_down = parse_double(b"0x5p-1075").unwrap();
            assert_eq!(subnormal_tie_even_down.value.to_bits(), 2);
            assert!(subnormal_tie_even_down.range_error);

            let below_overflow_half = parse_double(b"0x1.fffffffffffff7p1023").unwrap();
            assert_eq!(below_overflow_half.value, f64::MAX);
            assert!(!below_overflow_half.range_error);
            let at_overflow_half = parse_double(b"0x1.fffffffffffff8p1023").unwrap();
            assert_eq!(at_overflow_half.value, f64::INFINITY);
            assert!(at_overflow_half.range_error);

            let tiny_value_rounded_normal = parse_double(b"0x0.fffffffffffff8p-1022").unwrap();
            assert_eq!(tiny_value_rounded_normal.value, f64::MIN_POSITIVE);
            assert!(tiny_value_rounded_normal.range_error);
            let normal_value_rounded_normal = parse_double(b"0x1.00000000000008p-1022").unwrap();
            assert_eq!(normal_value_rounded_normal.value, f64::MIN_POSITIVE);
            assert!(!normal_value_rounded_normal.range_error);

            for bits in [
                1,
                2,
                3,
                (1_u64 << 52) - 1,
                1_u64 << 52,
                0x3ff0_0000_0000_0000,
                0x4009_21fb_5444_2d18,
                0x7fef_ffff_ffff_ffff,
            ] {
                let exponent_field = (bits >> 52) & 0x7ff;
                let fraction = bits & ((1_u64 << 52) - 1);
                let operand = if exponent_field == 0 {
                    format!("0x{fraction:x}p-1074")
                } else {
                    let significand = (1_u64 << 52) | fraction;
                    let exponent = exponent_field as i32 - 1023 - 52;
                    format!("0x{significand:x}p{exponent}")
                };
                let parsed = parse_double(operand.as_bytes()).unwrap();
                assert_eq!(parsed.value.to_bits(), bits, "operand {operand}");
                assert!(!parsed.range_error, "operand {operand}");
            }

            for operand in [
                b"0e9999".as_slice(),
                b"0e-9999".as_slice(),
                b"0x0p9999".as_slice(),
                b"-0x0p-9999".as_slice(),
            ] {
                let parsed = parse_double(operand).unwrap();
                assert_eq!(parsed.value, 0.0, "operand {operand:?}");
                assert_eq!(parsed.end_index, operand.len(), "operand {operand:?}");
                assert!(!parsed.range_error, "operand {operand:?}");
            }
        }
    }

    mod directive_scanner {
        use super::*;

        #[test]
        fn static_and_dynamic_controls_are_parsed_with_repeated_flags() {
            let operands = vec![b"-6".to_vec(), b"-2".to_vec()];
            let mut state = State::new(&operands, b"printf");

            let static_format = b"%--00+#12.003s";
            let (directive, next) = parse_directive(static_format, 0, &mut state).unwrap();
            assert_eq!(next, static_format.len());
            assert_eq!(directive.raw, static_format);
            assert_eq!(directive.conversion, b's');
            assert_eq!(directive.controls.field_width, None);
            assert_eq!(directive.controls.precision, None);
            assert_eq!(state.cursor, 0);
            let layout = output_layout(directive).unwrap();
            assert!(layout.left_adjust);
            assert_eq!(layout.width, 12);
            assert_eq!(layout.precision, Some(3));

            let dynamic_format = b"%0-*.*s";
            let (directive, next) = parse_directive(dynamic_format, 0, &mut state).unwrap();
            assert_eq!(next, dynamic_format.len());
            assert_eq!(directive.controls.field_width, Some(-6));
            assert_eq!(directive.controls.precision, Some(-2));
            assert_eq!(state.cursor, 2);
            let layout = output_layout(directive).unwrap();
            assert!(layout.left_adjust);
            assert_eq!(layout.width, 6);
            assert_eq!(layout.precision, None);
        }

        #[test]
        fn missing_dynamic_controls_default_without_consumption() {
            let operands = Vec::new();
            let mut state = State::new(&operands, b"printf");
            let (directive, next) = parse_directive(b"%*.*s", 0, &mut state).unwrap();

            assert_eq!(next, 5);
            assert_eq!(directive.controls.field_width, Some(0));
            assert_eq!(directive.controls.precision, Some(0));
            assert_eq!(state.cursor, 0);
        }

        #[test]
        fn dynamic_width_and_precision_are_consumed_in_order() {
            let operands = vec![b"4".to_vec(), b"2".to_vec()];
            let mut state = State::new(&operands, b"printf");
            let (directive, next) = parse_directive(b"%*.*s", 0, &mut state).unwrap();

            assert_eq!(next, 5);
            assert_eq!(directive.raw, b"%*.*s");
            assert_eq!(directive.conversion, b's');
            assert_eq!(directive.controls.field_width, Some(4));
            assert_eq!(directive.controls.precision, Some(2));
            assert_eq!(state.cursor, 2);
        }
    }

    mod formatter {
        use super::*;

        #[test]
        fn string_width_and_precision_count_raw_bytes() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[
                    b"printf".to_vec(),
                    b"%6.3s|%-5.2s|%05s".to_vec(),
                    vec![0xff, 0xfe, b'A', b'B'],
                    vec![0xf0, 0x9f, b'X'],
                    b"xy".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(
                harness.stdout(),
                &[
                    b' ', b' ', b' ', 0xff, 0xfe, b'A', b'|', 0xf0, 0x9f, b' ', b' ', b' ', b'|',
                    b' ', b' ', b' ', b'x', b'y',
                ]
            );
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn string_precision_can_split_utf8() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[
                    b"printf".to_vec(),
                    b"%.1s|%.2s".to_vec(),
                    vec![0xc3, 0xa9, b'Z'],
                    vec![0xc3, 0xa9, b'Z'],
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), &[0xc3, b'|', 0xc3, 0xa9]);
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn missing_character_emits_nul() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[b"printf".to_vec(), b"%c|%c".to_vec(), b"AB".to_vec()])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), &[b'A', b'|', 0]);
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn negative_dynamic_width_left_adjusts() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[
                    b"printf".to_vec(),
                    b"%*s|%*c".to_vec(),
                    b"-5".to_vec(),
                    b"xy".to_vec(),
                    b"-3".to_vec(),
                    b"Qtail".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), b"xy   |Q  ");
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn negative_dynamic_precision_is_omitted() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[
                    b"printf".to_vec(),
                    b"%.*s|%.*s".to_vec(),
                    b"-2".to_vec(),
                    b"hello".to_vec(),
                    b"2".to_vec(),
                    b"hello".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), b"hello|he");
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn overflowing_static_control_suppresses_only_its_conversion() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[
                    b"printf".to_vec(),
                    b"A%2147483648sB%.2147483648cC".to_vec(),
                    b"value".to_vec(),
                    b"Q".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), b"ABC");
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn repaired_string_integer_and_float_paths_emit_exactly() {
            let mut strings = RunHarness::default();
            let status = strings
                .run(&[
                    b"printf".to_vec(),
                    b"%*s|%*.*s".to_vec(),
                    b"7".to_vec(),
                    b"hello".to_vec(),
                    b"4".to_vec(),
                    b"2".to_vec(),
                    b"hello".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(strings.stdout(), b"  hello|  he");
            assert_eq!(strings.stderr(), b"");

            let mut numeric = RunHarness::default();
            let status = numeric
                .run(&[
                    b"printf".to_vec(),
                    b"%u %x %d %e".to_vec(),
                    b"0".to_vec(),
                    b"0".to_vec(),
                    b"''".to_vec(),
                    b"123.456".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(numeric.stdout(), b"0 0 39 1.234560e+02");
            assert_eq!(numeric.stderr(), b"");
        }

        #[test]
        fn integer_zero_precision_alternate_form_matrix() {
            let mut harness = RunHarness::default();
            let mut args = vec![
                b"printf".to_vec(),
                b"<%.0d>|<%+.0d>|<% .0d>|<%.0u>|<%.0o>|<%#.0o>|<%#.0x>|<%#o>|<%#x>".to_vec(),
            ];
            args.extend((0..9).map(|_| b"0".to_vec()));

            let status = harness.run(&args).unwrap();

            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), b"<>|<+>|< >|<>|<>|<0>|<>|<0>|<0>");
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn integer_sign_prefix_and_zero_padding_order() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[
                    b"printf".to_vec(),
                    b"<%+08d>|<% 08d>|<%08d>|<%#08x>|<%#08X>|<%#08o>|<%-#8x>|<%*.*d>|<%#0*.*X>"
                        .to_vec(),
                    b"42".to_vec(),
                    b"42".to_vec(),
                    b"-42".to_vec(),
                    b"42".to_vec(),
                    b"42".to_vec(),
                    b"42".to_vec(),
                    b"42".to_vec(),
                    b"8".to_vec(),
                    b"5".to_vec(),
                    b"42".to_vec(),
                    b"8".to_vec(),
                    b"5".to_vec(),
                    b"42".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(
                harness.stdout(),
                b"<+0000042>|< 0000042>|<-0000042>|<0x00002a>|<0X00002A>|<00000052>|<0x2a    >|<   00042>|< 0X0002A>"
            );
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn all_signed_and_unsigned_integer_directives() {
            assert_eq!(mklong(b"%#08x", b'x').unwrap(), b"%#08lx");

            let mut harness = RunHarness::default();
            let status = harness
                .run(&[
                    b"printf".to_vec(),
                    b"%d|%i|%o|%u|%x|%X".to_vec(),
                    b"-42".to_vec(),
                    b"0x2a".to_vec(),
                    b"42".to_vec(),
                    b"42".to_vec(),
                    b"42".to_vec(),
                    b"42".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), b"-42|42|52|42|2a|2A");
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn all_float_directives_and_case_variants() {
            let mut default_precision = RunHarness::default();
            let mut args = vec![b"printf".to_vec(), b"%a|%A|%e|%E|%f|%F|%g|%G".to_vec()];
            args.extend((0..8).map(|_| b"3.5".to_vec()));

            let status = default_precision.run(&args).unwrap();

            assert_eq!(status, 0);
            assert_eq!(
                default_precision.stdout(),
                b"0x1.cp+1|0X1.CP+1|3.500000e+00|3.500000E+00|3.500000|3.500000|3.5|3.5"
            );
            assert_eq!(default_precision.stderr(), b"");

            let mut explicit_precision = RunHarness::default();
            let mut args = vec![
                b"printf".to_vec(),
                b"%.3a|%.3A|%.2e|%.2E|%.2f|%.2F|%.3g|%.3G|%#.0f|%#.0e|%#.3g".to_vec(),
            ];
            args.extend((0..8).map(|_| b"3.5".to_vec()));
            args.extend([b"1".to_vec(), b"1".to_vec(), b"3.5".to_vec()]);

            let status = explicit_precision.run(&args).unwrap();

            assert_eq!(status, 0);
            assert_eq!(
                explicit_precision.stdout(),
                b"0x1.c00p+1|0X1.C00P+1|3.50e+00|3.50E+00|3.50|3.50|3.5|3.5|1.|1.e+00|3.50"
            );
            assert_eq!(explicit_precision.stderr(), b"");

            let mut flags_and_width = RunHarness::default();
            let mut args = vec![
                b"printf".to_vec(),
                b"<%+#020.3a>|<%-#20.0A>|<% 015.2f>|<%+15.2E>|<%#012.5g>|<%-#12.5G>".to_vec(),
            ];
            args.extend((0..6).map(|_| b"3.5".to_vec()));

            let status = flags_and_width.run(&args).unwrap();

            assert_eq!(status, 0);
            assert_eq!(
                flags_and_width.stdout(),
                b"<+0x0000000001.c00p+1>|<0X2.P+1             >|< 00000000003.50>|<      +3.50E+00>|<0000003.5000>|<3.5000      >"
            );
            assert_eq!(flags_and_width.stderr(), b"");
        }

        #[test]
        fn float_notation_thresholds_rounding_ties_and_signed_zero() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[
                    b"printf".to_vec(),
                    b"%g|%g|%g|%g|%G|%.7g|%.0g|%.0f|%.0f|%.2f|%.2f|%.0a|%a|%e|%F|%g|%+g".to_vec(),
                    b"0.0001".to_vec(),
                    b"0.00001".to_vec(),
                    b"123456".to_vec(),
                    b"1234567".to_vec(),
                    b"1234567".to_vec(),
                    b"1234567".to_vec(),
                    b"9.99".to_vec(),
                    b"2.5".to_vec(),
                    b"3.5".to_vec(),
                    b"1.125".to_vec(),
                    b"1.375".to_vec(),
                    b"3.141592653589793".to_vec(),
                    b"-0".to_vec(),
                    b"-0".to_vec(),
                    b"-0".to_vec(),
                    b"-0".to_vec(),
                    b"0".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(
                harness.stdout(),
                b"0.0001|1e-05|123456|1.23457e+06|1.23457E+06|1234567|1e+01|2|4|1.12|1.38|0x2p+1|-0x0p+0|-0.000000e+00|-0.000000|-0|+0"
            );
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn float_infinity_and_nan_casing() {
            let mut harness = RunHarness::default();
            let mut args = vec![
                b"printf".to_vec(),
                b"%a|%A|%e|%E|%f|%F|%g|%G;%a|%A|%e|%E|%f|%F|%g|%G;<%+010F>|<%-10f>|<%+f>|<% f>|<%f>"
                    .to_vec(),
            ];
            args.extend((0..8).map(|_| b"inf".to_vec()));
            args.extend((0..8).map(|_| b"nan(payload)".to_vec()));
            args.extend([
                b"inf".to_vec(),
                b"inf".to_vec(),
                b"nan".to_vec(),
                b"nan".to_vec(),
                b"-nan".to_vec(),
            ]);

            let status = harness.run(&args).unwrap();

            assert_eq!(status, 0);
            assert_eq!(
                harness.stdout(),
                b"inf|INF|inf|INF|inf|INF|inf|INF;nan|NAN|nan|NAN|nan|NAN|nan|NAN;<      +INF>|<inf       >|<+nan>|< nan>|<-nan>"
            );
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn float_dynamic_controls_match_c() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[
                    b"printf".to_vec(),
                    b"<%*.*f>|<%0*.*e>|<%*.*G>|<%*.*a>".to_vec(),
                    b"10".to_vec(),
                    b"2".to_vec(),
                    b"3.5".to_vec(),
                    b"12".to_vec(),
                    b"3".to_vec(),
                    b"12".to_vec(),
                    b"-12".to_vec(),
                    b"5".to_vec(),
                    b"123.456".to_vec(),
                    b"14".to_vec(),
                    b"-1".to_vec(),
                    b"3.5".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(
                harness.stdout(),
                b"<      3.50>|<0001.200e+01>|<123.46      >|<      0x1.cp+1>"
            );
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn subnormal_hex_float_uses_glibc_normalization_and_rounding() {
            fn render(format: &[u8], value: f64) -> Vec<u8> {
                let operands = Vec::new();
                let mut state = State::new(&operands, b"printf");
                let (directive, next) = parse_directive(format, 0, &mut state).unwrap();
                assert_eq!(next, format.len());
                let mut output = Vec::new();
                emit_conversion(directive, ConversionValue::Float(value), &mut output).unwrap();
                output
            }

            let minimum = f64::from_bits(1);
            for &(format, expected) in &[
                (b"%a".as_slice(), b"0x0.0000000000001p-1022".as_slice()),
                (b"%A", b"0X0.0000000000001P-1022"),
                (b"%.0a", b"0x0p-1022"),
                (b"%#.0a", b"0x0.p-1022"),
                (b"%.5a", b"0x0.00000p-1022"),
                (b"%.13a", b"0x0.0000000000001p-1022"),
                (b"%.14a", b"0x0.00000000000010p-1022"),
                (b"%+020.5a", b"+0x00000.00000p-1022"),
                (b"%-20.5a", b"0x0.00000p-1022     "),
            ] {
                assert_eq!(render(format, minimum), expected, "format {format:?}");
            }

            let maximum_subnormal = f64::from_bits((1_u64 << 52) - 1);
            assert_eq!(render(b"%a", maximum_subnormal), b"0x0.fffffffffffffp-1022");
            assert_eq!(render(b"%.0a", maximum_subnormal), b"0x1p-1022");
            assert_eq!(render(b"%.1a", maximum_subnormal), b"0x1.0p-1022");
            assert_eq!(
                render(b"%.12a", f64::from_bits(8)),
                b"0x0.000000000000p-1022"
            );
            assert_eq!(
                render(b"%.12a", f64::from_bits(24)),
                b"0x0.000000000002p-1022"
            );

            let operands = vec![b"20".to_vec(), b"5".to_vec()];
            let mut state = State::new(&operands, b"printf");
            let (directive, next) = parse_directive(b"%+0*.*a", 0, &mut state).unwrap();
            assert_eq!(next, b"%+0*.*a".len());
            let mut output = Vec::new();
            emit_conversion(directive, ConversionValue::Float(minimum), &mut output).unwrap();
            assert_eq!(output, b"+0x00000.00000p-1022");

            let mut harness = RunHarness::default();
            let status = harness
                .run(&[b"printf".to_vec(), b"%a".to_vec(), b"0x1p-1074".to_vec()])
                .unwrap();
            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), b"0x0.0000000000001p-1022");
            assert_eq!(harness.stderr(), b"");
        }
    }

    mod run_level {
        use super::*;

        fn assert_injected_failure(error: RunError) {
            match error {
                RunError::Io(error) => {
                    assert_eq!(error.kind(), io::ErrorKind::Other);
                    assert_eq!(error.to_string(), "injected writer failure");
                }
                other => panic!("unexpected error: {other:?}"),
            }
        }

        #[test]
        fn writer_failure_propagates_without_panic() {
            let args = [b"printf".to_vec()];

            let mut stdout = Vec::new();
            let mut immediate_failure = FailingWriter::after(0);
            let error = run(&args, &mut stdout, &mut immediate_failure).unwrap_err();
            assert_injected_failure(error);
            assert_eq!(stdout, b"");
            assert_eq!(immediate_failure.written(), b"");

            let mut stdout = Vec::new();
            let mut prefix_failure = FailingWriter::after(7);
            let error = run(&args, &mut stdout, &mut prefix_failure).unwrap_err();
            assert_injected_failure(error);
            assert_eq!(stdout, b"");
            assert_eq!(prefix_failure.written(), b"usage: ");
        }

        #[test]
        fn literal_format_ignores_surplus_operands() {
            let mut literal = RunHarness::default();
            let status = literal
                .run(&[
                    b"printf".to_vec(),
                    vec![b'L', 0xff, b'T'],
                    b"ignored-one".to_vec(),
                    b"ignored-two".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(literal.stdout(), &[b'L', 0xff, b'T']);
            assert_eq!(literal.stderr(), b"");

            let mut percent = RunHarness::default();
            let status = percent
                .run(&[
                    b"printf".to_vec(),
                    b"100%% done".to_vec(),
                    b"ignored".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(percent.stdout(), b"100% done");
            assert_eq!(percent.stderr(), b"");
        }

        #[test]
        fn shortage_defaults_are_emitted_after_consumed_operands() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[b"printf".to_vec(), b"%d %d".to_vec(), b"123".to_vec()])
                .unwrap();

            assert_eq!(status, 0);
            assert_eq!(harness.stdout(), b"123 0");
            assert_eq!(harness.stderr(), b"");
        }

        #[test]
        fn conversion_warning_precedence_and_sticky_status() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[
                    b"/tmp/integer-alias".to_vec(),
                    b"[%d][%d][%d][%d][%d][%d]".to_vec(),
                    Vec::new(),
                    b"word".to_vec(),
                    b"077tail".to_vec(),
                    b"9223372036854775808tail".to_vec(),
                    b"9223372036854775808".to_vec(),
                    b"7".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 1);
            assert_eq!(
                harness.stdout(),
                b"[0][0][63][9223372036854775807][9223372036854775807][7]"
            );
            assert_eq!(
                harness.stderr(),
                b"integer-alias: word: expected numeric value\n\
integer-alias: 077tail: not completely converted\n\
integer-alias: 9223372036854775808tail: not completely converted\n\
integer-alias: 9223372036854775808: Numerical result out of range\n"
            );
        }

        #[test]
        fn float_conversion_warning_precedence() {
            let mut harness = RunHarness::default();
            let status = harness
                .run(&[
                    b"/tmp/float-alias".to_vec(),
                    b"[%g][%g][%g][%g][%g][%g][%g]".to_vec(),
                    Vec::new(),
                    b"word".to_vec(),
                    b"1.25tail".to_vec(),
                    b"1e9999tail".to_vec(),
                    b"1e9999".to_vec(),
                    b"1e-9999".to_vec(),
                    b"7".to_vec(),
                ])
                .unwrap();

            assert_eq!(status, 1);
            assert_eq!(harness.stdout(), b"[0][0][1.25][inf][inf][0][7]");
            assert_eq!(
                harness.stderr(),
                b"float-alias: word: expected numeric value\n\
float-alias: 1.25tail: not completely converted\n\
float-alias: 1e9999tail: not completely converted\n\
float-alias: 1e9999: Numerical result out of range\n\
float-alias: 1e-9999: Numerical result out of range\n"
            );
        }

        #[test]
        fn numeric_writer_failure_retains_concrete_io_error() {
            let expected = b"0x00002a";
            for byte_count in [0, 1, 2, 4, 7] {
                let args = [b"printf".to_vec(), b"%#08x".to_vec(), b"42".to_vec()];
                let mut stdout = FailingWriter::after(byte_count);
                let mut stderr = Vec::new();

                let error = run(&args, &mut stdout, &mut stderr).unwrap_err();

                assert_injected_failure(error);
                assert_eq!(stdout.written(), &expected[..byte_count]);
                assert_eq!(stderr, b"");
            }
        }
    }
}
