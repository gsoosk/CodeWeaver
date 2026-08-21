use std::io::{self, Write};
use std::ops::Range;

pub(crate) const SKIP1: &[u8] = b"#-+ 0";
pub(crate) const SKIP2: &[u8] = b"0123456789";
const SUPPORTED_CONVERSIONS: &[u8] = b"csdiouxXaAeEfFgG";

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub(crate) struct Flags {
    pub(crate) alternate: bool,
    pub(crate) left: bool,
    pub(crate) plus: bool,
    pub(crate) space: bool,
    pub(crate) zero: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct StaticField {
    pub(crate) value: u32,
    pub(crate) exceeds_int: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Field {
    Omitted,
    Static(StaticField),
    Dynamic,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Directive {
    pub(crate) flags: Flags,
    pub(crate) width: Field,
    pub(crate) precision: Field,
    pub(crate) conversion: u8,
    pub(crate) span: Range<usize>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ResolvedDirective {
    pub(crate) flags: Flags,
    pub(crate) width: Option<u32>,
    pub(crate) precision: Option<u32>,
    pub(crate) conversion: u8,
    pub(crate) span: Range<usize>,
    pub(crate) suppress_output: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum DirectiveErrorKind {
    MissingFormatCharacter,
    InvalidDirective,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct DirectiveError {
    pub(crate) kind: DirectiveErrorKind,
    pub(crate) span: Range<usize>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ParsedDirective {
    pub(crate) directive: Directive,
    pub(crate) next_index: usize,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub(crate) enum Value<'a> {
    Character(u8),
    String(&'a [u8]),
    Signed(i64),
    Unsigned(u64),
    Float(f64),
}

pub(crate) fn parse(
    format: &[u8],
    percent_index: usize,
) -> Result<ParsedDirective, DirectiveError> {
    let mut index = percent_index + 1;
    let mut flags = Flags::default();
    while let Some(byte) = format
        .get(index)
        .copied()
        .filter(|byte| SKIP1.contains(byte))
    {
        match byte {
            b'#' => flags.alternate = true,
            b'-' => flags.left = true,
            b'+' => flags.plus = true,
            b' ' => flags.space = true,
            b'0' => flags.zero = true,
            _ => {}
        }
        index += 1;
    }

    let width = if format.get(index) == Some(&b'*') {
        index += 1;
        Field::Dynamic
    } else if format.get(index).is_some_and(|byte| SKIP2.contains(byte)) {
        Field::Static(parse_static_field(format, &mut index))
    } else {
        Field::Omitted
    };

    let mut saw_precision = false;
    let precision = if format.get(index) == Some(&b'.') {
        saw_precision = true;
        index += 1;
        if format.get(index) == Some(&b'*') {
            index += 1;
            Field::Dynamic
        } else {
            Field::Static(parse_static_field(format, &mut index))
        }
    } else {
        Field::Omitted
    };

    let Some(&conversion) = format.get(index) else {
        return Err(DirectiveError {
            kind: if saw_precision {
                DirectiveErrorKind::InvalidDirective
            } else {
                DirectiveErrorKind::MissingFormatCharacter
            },
            span: percent_index..format.len(),
        });
    };
    let next_index = index + 1;
    if !SUPPORTED_CONVERSIONS.contains(&conversion) {
        return Err(DirectiveError {
            kind: DirectiveErrorKind::InvalidDirective,
            span: percent_index..next_index,
        });
    }

    Ok(ParsedDirective {
        directive: Directive {
            flags,
            width,
            precision,
            conversion,
            span: percent_index..next_index,
        },
        next_index,
    })
}

pub(crate) fn resolve(
    directive: Directive,
    dynamic_width: Option<i32>,
    dynamic_precision: Option<i32>,
) -> ResolvedDirective {
    let mut flags = directive.flags;
    let mut suppress_output = false;
    let width = match directive.width {
        Field::Omitted => None,
        Field::Static(field) => {
            suppress_output |= field.exceeds_int;
            Some(field.value)
        }
        Field::Dynamic => {
            let value = dynamic_width.unwrap_or(0);
            if value < 0 {
                flags.left = true;
                Some(value.unsigned_abs())
            } else {
                Some(value as u32)
            }
        }
    };
    let precision = match directive.precision {
        Field::Omitted => None,
        Field::Static(field) => {
            suppress_output |= field.exceeds_int;
            Some(field.value)
        }
        Field::Dynamic => {
            let value = dynamic_precision.unwrap_or(0);
            (value >= 0).then_some(value as u32)
        }
    };
    if flags.left {
        flags.zero = false;
    }
    if flags.plus {
        flags.space = false;
    }
    ResolvedDirective {
        flags,
        width,
        precision,
        conversion: directive.conversion,
        span: directive.span,
        suppress_output,
    }
}

pub(crate) fn render<W: Write + ?Sized>(
    writer: &mut W,
    directive: &ResolvedDirective,
    value: Value<'_>,
) -> io::Result<()> {
    if directive.suppress_output {
        return Ok(());
    }
    match value {
        Value::Character(value) => render_character(writer, directive, value),
        Value::String(value) => render_string(writer, directive, value),
        Value::Signed(value) => render_signed(writer, directive, value),
        Value::Unsigned(value) => render_unsigned(writer, directive, value),
        Value::Float(value) => render_float(writer, directive, value),
    }
}

pub(crate) fn render_character<W: Write + ?Sized>(
    writer: &mut W,
    directive: &ResolvedDirective,
    value: u8,
) -> io::Result<()> {
    let padding = padding_for(directive.width, 1);
    if !directive.flags.left {
        write_padding(writer, b' ', padding)?;
    }
    writer.write_all(&[value])?;
    if directive.flags.left {
        write_padding(writer, b' ', padding)?;
    }
    Ok(())
}

pub(crate) fn render_string<W: Write + ?Sized>(
    writer: &mut W,
    directive: &ResolvedDirective,
    value: &[u8],
) -> io::Result<()> {
    let length = directive
        .precision
        .map_or(value.len(), |precision| value.len().min(precision as usize));
    let padding = padding_for(directive.width, length as u64);
    if !directive.flags.left {
        write_padding(writer, b' ', padding)?;
    }
    writer.write_all(&value[..length])?;
    if directive.flags.left {
        write_padding(writer, b' ', padding)?;
    }
    Ok(())
}

pub(crate) fn render_signed<W: Write + ?Sized>(
    writer: &mut W,
    directive: &ResolvedDirective,
    value: i64,
) -> io::Result<()> {
    if !matches!(directive.conversion, b'd' | b'i') {
        return Err(invalid_conversion());
    }
    let sign = if value < 0 {
        Some(b'-')
    } else if directive.flags.plus {
        Some(b'+')
    } else if directive.flags.space {
        Some(b' ')
    } else {
        None
    };
    let raw_digits = unsigned_digits(value.unsigned_abs(), 10, false);
    let digits = if value == 0 && directive.precision == Some(0) {
        &b""[..]
    } else {
        raw_digits.as_slice()
    };
    let precision_zeros = directive
        .precision
        .unwrap_or(0)
        .saturating_sub(digits.len() as u32) as u64;
    render_numeric(
        writer,
        directive,
        sign,
        &[],
        digits,
        precision_zeros,
        directive.precision.is_none(),
    )
}

pub(crate) fn render_unsigned<W: Write + ?Sized>(
    writer: &mut W,
    directive: &ResolvedDirective,
    value: u64,
) -> io::Result<()> {
    let (base, uppercase) = match directive.conversion {
        b'o' => (8, false),
        b'u' => (10, false),
        b'x' => (16, false),
        b'X' => (16, true),
        _ => return Err(invalid_conversion()),
    };
    let raw_digits = unsigned_digits(value, base, uppercase);
    let digits = if value == 0 && directive.precision == Some(0) {
        &b""[..]
    } else {
        raw_digits.as_slice()
    };
    let mut precision_zeros = directive
        .precision
        .unwrap_or(0)
        .saturating_sub(digits.len() as u32) as u64;
    let prefix: &[u8] = match directive.conversion {
        b'o' if directive.flags.alternate => {
            if digits.is_empty() {
                precision_zeros = 1;
            } else if precision_zeros == 0 && digits.first() != Some(&b'0') {
                precision_zeros = 1;
            }
            b""
        }
        b'x' if directive.flags.alternate && value != 0 => b"0x",
        b'X' if directive.flags.alternate && value != 0 => b"0X",
        _ => b"",
    };
    render_numeric(
        writer,
        directive,
        None,
        prefix,
        digits,
        precision_zeros,
        directive.precision.is_none(),
    )
}

pub(crate) fn render_float<W: Write + ?Sized>(
    writer: &mut W,
    directive: &ResolvedDirective,
    value: f64,
) -> io::Result<()> {
    match directive.conversion {
        b'e' | b'E' => render_scientific(writer, directive, value),
        _ => Err(invalid_conversion()),
    }
}

pub(crate) fn render_fixed<W: Write + ?Sized>(
    writer: &mut W,
    directive: &ResolvedDirective,
    value: f64,
) -> io::Result<()> {
    let _ = (writer, directive, value);
    todo!("Translator: render %f and %F")
}

pub(crate) fn render_scientific<W: Write + ?Sized>(
    writer: &mut W,
    directive: &ResolvedDirective,
    value: f64,
) -> io::Result<()> {
    let uppercase = directive.conversion == b'E';
    let sign = if value.is_sign_negative() {
        Some(b'-')
    } else if directive.flags.plus {
        Some(b'+')
    } else if directive.flags.space {
        Some(b' ')
    } else {
        None
    };
    let finite = value.is_finite();
    let body = if value.is_nan() {
        if uppercase {
            b"NAN".to_vec()
        } else {
            b"nan".to_vec()
        }
    } else if value.is_infinite() {
        if uppercase {
            b"INF".to_vec()
        } else {
            b"inf".to_vec()
        }
    } else {
        let precision = directive.precision.unwrap_or(6) as usize;
        let raw = format!("{:.*e}", precision, value.abs());
        let (mantissa, exponent) = raw.rsplit_once('e').ok_or_else(invalid_conversion)?;
        let exponent = exponent.parse::<i32>().map_err(|_| invalid_conversion())?;
        let mut body = Vec::with_capacity(mantissa.len() + 5);
        body.extend_from_slice(mantissa.as_bytes());
        if directive.flags.alternate && precision == 0 && !mantissa.contains('.') {
            body.push(b'.');
        }
        body.push(if uppercase { b'E' } else { b'e' });
        body.push(if exponent < 0 { b'-' } else { b'+' });
        let exponent_digits = exponent.unsigned_abs().to_string();
        if exponent_digits.len() < 2 {
            body.push(b'0');
        }
        body.extend_from_slice(exponent_digits.as_bytes());
        body
    };
    render_numeric(writer, directive, sign, &[], &body, 0, finite)
}

pub(crate) fn render_general<W: Write + ?Sized>(
    writer: &mut W,
    directive: &ResolvedDirective,
    value: f64,
) -> io::Result<()> {
    let _ = (writer, directive, value);
    todo!("Translator: render %g and %G")
}

pub(crate) fn render_hex_float<W: Write + ?Sized>(
    writer: &mut W,
    directive: &ResolvedDirective,
    value: f64,
) -> io::Result<()> {
    let _ = (writer, directive, value);
    todo!("Translator: render %a and %A")
}

pub(crate) fn write_padding<W: Write + ?Sized>(
    writer: &mut W,
    byte: u8,
    count: u64,
) -> io::Result<()> {
    const CHUNK_SIZE: usize = 256;
    let chunk = [byte; CHUNK_SIZE];
    let mut remaining = count;
    while remaining >= CHUNK_SIZE as u64 {
        writer.write_all(&chunk)?;
        remaining -= CHUNK_SIZE as u64;
    }
    writer.write_all(&chunk[..remaining as usize])
}

fn parse_static_field(format: &[u8], index: &mut usize) -> StaticField {
    let mut value = 0_u32;
    let mut exceeds_int = false;
    while let Some(byte) = format.get(*index).filter(|byte| SKIP2.contains(byte)) {
        value = match value
            .checked_mul(10)
            .and_then(|value| value.checked_add(u32::from(*byte - b'0')))
        {
            Some(value) => value,
            None => {
                exceeds_int = true;
                u32::MAX
            }
        };
        exceeds_int |= value > i32::MAX as u32;
        *index += 1;
    }
    StaticField { value, exceeds_int }
}

fn padding_for(width: Option<u32>, content_length: u64) -> u64 {
    u64::from(width.unwrap_or(0)).saturating_sub(content_length)
}

fn render_numeric<W: Write + ?Sized>(
    writer: &mut W,
    directive: &ResolvedDirective,
    sign: Option<u8>,
    prefix: &[u8],
    digits: &[u8],
    precision_zeros: u64,
    width_zero_allowed: bool,
) -> io::Result<()> {
    let content_length =
        sign.is_some() as u64 + prefix.len() as u64 + precision_zeros + digits.len() as u64;
    let width_padding = padding_for(directive.width, content_length);
    let use_width_zero = directive.flags.zero && !directive.flags.left && width_zero_allowed;

    if !directive.flags.left && !use_width_zero {
        write_padding(writer, b' ', width_padding)?;
    }
    if let Some(sign) = sign {
        writer.write_all(&[sign])?;
    }
    writer.write_all(prefix)?;
    if use_width_zero {
        write_padding(writer, b'0', width_padding)?;
    }
    write_padding(writer, b'0', precision_zeros)?;
    writer.write_all(digits)?;
    if directive.flags.left {
        write_padding(writer, b' ', width_padding)?;
    }
    Ok(())
}

fn unsigned_digits(mut value: u64, base: u8, uppercase: bool) -> Vec<u8> {
    if value == 0 {
        return vec![b'0'];
    }
    let table = if uppercase {
        b"0123456789ABCDEF"
    } else {
        b"0123456789abcdef"
    };
    let mut reversed = Vec::with_capacity(22);
    while value != 0 {
        reversed.push(table[(value % u64::from(base)) as usize]);
        value /= u64::from(base);
    }
    reversed.reverse();
    reversed
}

fn invalid_conversion() -> io::Error {
    io::Error::new(io::ErrorKind::InvalidInput, "unsupported conversion")
}

#[cfg(test)]
mod tests {
    use super::{parse, render, resolve, DirectiveErrorKind, Field, Flags, StaticField, Value};

    #[test]
    fn formatter_test_module_is_wired() {
        let _ = (
            Flags::default(),
            Field::Static(StaticField {
                value: 0,
                exceeds_int: false,
            }),
        );
    }

    mod directive_cases {
        use super::{parse, render, resolve, DirectiveErrorKind, Field, Flags, StaticField, Value};
        use std::ops::Range;

        #[test]
        fn parses_dynamic_width_and_precision_in_order() {
            let parsed = parse(b"%*.*s", 0).expect("valid directive");
            assert_eq!(parsed.directive.width, Field::Dynamic);
            assert_eq!(parsed.directive.precision, Field::Dynamic);
            assert_eq!(parsed.next_index, 5);
        }

        #[test]
        fn parses_character_and_string_static_dimensions() {
            let parsed = parse(b"prefix%-05.2s", 6).expect("valid directive");
            assert!(parsed.directive.flags.left);
            assert!(parsed.directive.flags.zero);
            assert_eq!(
                parsed.directive.width,
                Field::Static(super::StaticField {
                    value: 5,
                    exceeds_int: false,
                })
            );
            assert_eq!(
                parsed.directive.precision,
                Field::Static(super::StaticField {
                    value: 2,
                    exceeds_int: false,
                })
            );
            assert_eq!(parsed.directive.conversion, b's');
            assert_eq!(parsed.next_index, 13);
        }

        #[test]
        fn parses_duplicate_flags_and_static_dimensions() {
            let format = b"%##--++ 00012.003s!";
            let parsed = parse(format, 0).expect("valid directive");

            assert_eq!(
                parsed.directive.flags,
                Flags {
                    alternate: true,
                    left: true,
                    plus: true,
                    space: true,
                    zero: true,
                }
            );
            assert_eq!(
                parsed.directive.width,
                Field::Static(StaticField {
                    value: 12,
                    exceeds_int: false,
                })
            );
            assert_eq!(
                parsed.directive.precision,
                Field::Static(StaticField {
                    value: 3,
                    exceeds_int: false,
                })
            );
            assert_eq!(parsed.directive.span, 0..format.len() - 1);
            assert_eq!(parsed.next_index, format.len() - 1);

            let resolved = resolve(parsed.directive, None, None);
            assert!(resolved.flags.left);
            assert!(!resolved.flags.zero);
            assert!(resolved.flags.plus);
            assert!(!resolved.flags.space);
        }

        #[test]
        fn resolves_dynamic_defaults_negative_values_and_conflicting_flags() {
            let missing = resolve(parse(b"%*.*s", 0).unwrap().directive, None, None);
            assert_eq!(missing.width, Some(0));
            assert_eq!(missing.precision, Some(0));

            let resolved = resolve(parse(b"%0+ *.*s", 0).unwrap().directive, Some(-5), Some(-1));
            assert_eq!(resolved.width, Some(5));
            assert_eq!(resolved.precision, None);
            assert!(resolved.flags.left);
            assert!(!resolved.flags.zero);
            assert!(resolved.flags.plus);
            assert!(!resolved.flags.space);

            let minimum = resolve(parse(b"%*s", 0).unwrap().directive, Some(i32::MIN), None);
            assert_eq!(minimum.width, Some(2_147_483_648));
            assert!(minimum.flags.left);
        }

        #[test]
        fn accepts_exactly_the_source_conversion_letters() {
            for &conversion in b"csdiouxXaAeEfFgG" {
                let format = [b'%', conversion];
                let parsed = parse(&format, 0).expect("source conversion is supported");
                assert_eq!(parsed.directive.conversion, conversion);
                assert_eq!(parsed.next_index, format.len());
            }

            for &conversion in b"b%ClmnpS" {
                let format = [b'%', conversion];
                assert_error(
                    &format,
                    0,
                    DirectiveErrorKind::InvalidDirective,
                    0..format.len(),
                );
            }
        }

        #[test]
        fn reports_safe_exact_spans_for_bad_and_unterminated_directives() {
            assert_error(b"pre%Qtail", 3, DirectiveErrorKind::InvalidDirective, 3..5);
            assert_error(b"pre%ld", 3, DirectiveErrorKind::InvalidDirective, 3..5);
            assert_error(b"pre%", 3, DirectiveErrorKind::MissingFormatCharacter, 3..4);
            assert_error(
                b"pre%#012",
                3,
                DirectiveErrorKind::MissingFormatCharacter,
                3..8,
            );
            assert_error(b"pre%.", 3, DirectiveErrorKind::InvalidDirective, 3..5);
            assert_error(b"pre%.123", 3, DirectiveErrorKind::InvalidDirective, 3..8);
            assert_error(b"pre%.*", 3, DirectiveErrorKind::InvalidDirective, 3..6);
        }

        #[test]
        fn oversized_static_dimensions_suppress_output_after_parsing() {
            let parsed = parse(b"%2147483648.42949672960s", 0).expect("grammar remains valid");
            assert_eq!(
                parsed.directive.width,
                Field::Static(StaticField {
                    value: 2_147_483_648,
                    exceeds_int: true,
                })
            );
            assert_eq!(
                parsed.directive.precision,
                Field::Static(StaticField {
                    value: u32::MAX,
                    exceeds_int: true,
                })
            );

            let resolved = resolve(parsed.directive, None, None);
            assert!(resolved.suppress_output);
            let mut output = Vec::new();
            render(&mut output, &resolved, Value::String(b"still consumed")).unwrap();
            assert!(output.is_empty());
        }

        fn assert_error(
            format: &[u8],
            percent_index: usize,
            kind: DirectiveErrorKind,
            span: Range<usize>,
        ) {
            let error = parse(format, percent_index).expect_err("directive must be rejected");
            assert_eq!(error.kind, kind);
            assert_eq!(error.span, span);
        }
    }

    mod text_rendering_cases {
        use super::{parse, render, resolve, Value};
        use std::io::{self, Write};

        #[test]
        fn character_rendering_outputs_one_raw_byte_and_space_width() {
            assert_eq!(rendered(b"%5c", Value::Character(0)), b"    \0");
            assert_eq!(rendered(b"%-5c", Value::Character(0xff)), b"\xff    ");
            assert_eq!(rendered(b"%.0c", Value::Character(b'X')), b"X");
        }

        #[test]
        fn string_precision_counts_bytes_and_zero_flag_is_ignored() {
            assert_eq!(rendered(b"%5.2s", Value::String(b"\xffABC")), b"   \xffA");
            assert_eq!(rendered(b"%-5.2s", Value::String(b"hello")), b"he   ");
            assert_eq!(rendered(b"%05s", Value::String(b"x")), b"    x");
            assert_eq!(rendered(b"%3.s", Value::String(b"hello")), b"   ");
        }

        #[test]
        fn non_applicable_flags_do_not_change_character_or_string_bytes() {
            assert_eq!(rendered(b"%#+ 05.0c", Value::Character(0)), b"    \0");
            assert_eq!(rendered(b"%-#+ 05.9c", Value::Character(0xff)), b"\xff    ");
            assert_eq!(
                rendered(b"%#+ 05.2s", Value::String(b"\x80ABC")),
                b"   \x80A"
            );
        }

        #[test]
        fn large_text_padding_is_written_in_bounded_chunks() {
            let directive = resolve(parse(b"%600s", 0).unwrap().directive, None, None);
            let mut output = BoundedWriter::default();
            render(&mut output, &directive, Value::String(b"x")).unwrap();

            assert_eq!(output.bytes.len(), 600);
            assert_eq!(output.bytes.last(), Some(&b'x'));
            assert!(output.largest_write <= 256);
        }

        #[test]
        fn large_dynamic_padding_is_streamed_in_bounded_chunks() {
            for width in [600, -600] {
                let directive = resolve(parse(b"%*s", 0).unwrap().directive, Some(width), None);
                let mut output = BoundedWriter::default();
                render(&mut output, &directive, Value::String(b"x")).unwrap();

                assert_eq!(output.bytes.len(), 600);
                if width < 0 {
                    assert_eq!(output.bytes.first(), Some(&b'x'));
                } else {
                    assert_eq!(output.bytes.last(), Some(&b'x'));
                }
                assert!(output.largest_write <= 256);
            }
        }

        fn rendered(format: &[u8], value: Value<'_>) -> Vec<u8> {
            let directive = resolve(parse(format, 0).unwrap().directive, None, None);
            let mut output = Vec::new();
            render(&mut output, &directive, value).unwrap();
            output
        }

        #[derive(Default)]
        struct BoundedWriter {
            bytes: Vec<u8>,
            largest_write: usize,
        }

        impl Write for BoundedWriter {
            fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
                self.largest_write = self.largest_write.max(bytes.len());
                self.bytes.extend_from_slice(bytes);
                Ok(bytes.len())
            }

            fn flush(&mut self) -> io::Result<()> {
                Ok(())
            }
        }
    }

    mod integer_rendering_cases {
        use super::{parse, render, resolve, Value};
        use std::io::{self, Write};

        #[test]
        fn renders_both_signed_decimal_conversions_and_the_full_lp64_domain() {
            assert_eq!(rendered(b"%d", Value::Signed(42)), b"42");
            assert_eq!(rendered(b"%i", Value::Signed(-42)), b"-42");
            assert_eq!(
                rendered(b"%d", Value::Signed(i64::MIN)),
                b"-9223372036854775808"
            );
            assert_eq!(
                rendered(b"%d", Value::Signed(i64::MAX)),
                b"9223372036854775807"
            );
        }

        #[test]
        fn signed_flags_width_and_precision_follow_c_precedence() {
            let cases: &[(&[u8], i64, &[u8])] = &[
                (b"%+d", 42, b"+42"),
                (b"% d", 42, b" 42"),
                (b"%+ d", 42, b"+42"),
                (b"%#d", 42, b"42"),
                (b"%05d", 42, b"00042"),
                (b"%05d", -42, b"-0042"),
                (b"%-05d", 42, b"42   "),
                (b"%8.5d", 42, b"   00042"),
                (b"%08.5d", 42, b"   00042"),
                (b"%+.0d", 0, b"+"),
                (b"%5.0d", 0, b"     "),
            ];

            for &(format, value, expected) in cases {
                assert_eq!(
                    rendered(format, Value::Signed(value)),
                    expected,
                    "{format:?}"
                );
            }
        }

        #[test]
        fn renders_unsigned_decimal_octal_and_both_hexadecimal_alphabets() {
            assert_eq!(rendered(b"%u", Value::Unsigned(0)), b"0");
            assert_eq!(
                rendered(b"%u", Value::Unsigned(u64::MAX)),
                b"18446744073709551615"
            );
            assert_eq!(rendered(b"%o", Value::Unsigned(511)), b"777");
            assert_eq!(
                rendered(b"%x", Value::Unsigned(u64::MAX)),
                b"ffffffffffffffff"
            );
            assert_eq!(rendered(b"%X", Value::Unsigned(0xdead_beef)), b"DEADBEEF");
            assert_eq!(rendered(b"%#+ u", Value::Unsigned(42)), b"42");
        }

        #[test]
        fn alternate_forms_obey_zero_and_precision_special_cases() {
            let cases: &[(&[u8], u64, &[u8])] = &[
                (b"%#o", 0, b"0"),
                (b"%#o", 8, b"010"),
                (b"%#.0o", 0, b"0"),
                (b"%#.3o", 8, b"010"),
                (b"%#x", 0, b"0"),
                (b"%#x", 42, b"0x2a"),
                (b"%#X", 42, b"0X2A"),
                (b"%#08x", 42, b"0x00002a"),
                (b"%#8.4x", 42, b"  0x002a"),
                (b"%-#8X", 42, b"0X2A    "),
            ];

            for &(format, value, expected) in cases {
                assert_eq!(
                    rendered(format, Value::Unsigned(value)),
                    expected,
                    "{format:?}"
                );
            }
        }

        #[test]
        fn zero_precision_suppresses_zero_except_for_alternate_octal() {
            let cases: &[(&[u8], &[u8])] = &[
                (b"%.0u", b""),
                (b"%.0x", b""),
                (b"%#.0x", b""),
                (b"%#.0o", b"0"),
                (b"%5.0u", b"     "),
                (b"%05.0u", b"     "),
            ];

            for &(format, expected) in cases {
                assert_eq!(rendered(format, Value::Unsigned(0)), expected, "{format:?}");
            }
        }

        #[test]
        fn negative_dynamic_width_and_precision_resolve_before_integer_rendering() {
            let directive = resolve(parse(b"%0*.*x", 0).unwrap().directive, Some(-8), Some(4));
            let mut output = Vec::new();
            render(&mut output, &directive, Value::Unsigned(42)).unwrap();
            assert_eq!(output, b"002a    ");
        }

        #[test]
        fn large_integer_width_and_precision_are_streamed_in_bounded_chunks() {
            let width = resolve(parse(b"%0600u", 0).unwrap().directive, None, None);
            let mut width_output = BoundedWriter::default();
            render(&mut width_output, &width, Value::Unsigned(1)).unwrap();
            assert_eq!(width_output.bytes.len(), 600);
            assert_eq!(width_output.bytes.first(), Some(&b'0'));
            assert_eq!(width_output.bytes.last(), Some(&b'1'));
            assert!(width_output.largest_write <= 256);

            let precision = resolve(parse(b"%.600x", 0).unwrap().directive, None, None);
            let mut precision_output = BoundedWriter::default();
            render(&mut precision_output, &precision, Value::Unsigned(1)).unwrap();
            assert_eq!(precision_output.bytes.len(), 600);
            assert_eq!(precision_output.bytes.first(), Some(&b'0'));
            assert_eq!(precision_output.bytes.last(), Some(&b'1'));
            assert!(precision_output.largest_write <= 256);
        }

        fn rendered(format: &[u8], value: Value<'_>) -> Vec<u8> {
            let directive = resolve(parse(format, 0).unwrap().directive, None, None);
            let mut output = Vec::new();
            render(&mut output, &directive, value).unwrap();
            output
        }

        #[derive(Default)]
        struct BoundedWriter {
            bytes: Vec<u8>,
            largest_write: usize,
        }

        impl Write for BoundedWriter {
            fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
                self.largest_write = self.largest_write.max(bytes.len());
                self.bytes.extend_from_slice(bytes);
                Ok(bytes.len())
            }

            fn flush(&mut self) -> io::Result<()> {
                Ok(())
            }
        }
    }

    mod float_rendering_cases {
        // TODO(Translator): add decimal and hexadecimal golden edge vectors.
    }
}
