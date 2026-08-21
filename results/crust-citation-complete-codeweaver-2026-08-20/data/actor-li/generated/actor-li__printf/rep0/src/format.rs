#![allow(dead_code)]

use crate::printf::Output;
use fish_printf::{sprintf_locale, Error as PrintfError, ToArg, C_LOCALE};
use std::io;

pub const SKIP1: &[u8] = b"#-+ 0";
pub const SKIP2: &[u8] = b"0123456789";

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct Flags {
    pub alternate: bool,
    pub left_adjust: bool,
    pub force_sign: bool,
    pub leading_space: bool,
    pub zero_pad: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FieldWidth {
    None,
    Static(u64),
    Dynamic,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Precision {
    None,
    Static(u64),
    Dynamic,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Conversion {
    Char,
    String,
    SignedDecimal,
    SignedInteger,
    Octal,
    UnsignedDecimal,
    HexLower,
    HexUpper,
    HexFloatLower,
    HexFloatUpper,
    ScientificLower,
    ScientificUpper,
    FixedLower,
    FixedUpper,
    GeneralLower,
    GeneralUpper,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Directive<'a> {
    pub original: &'a [u8],
    pub flags: Flags,
    pub width: FieldWidth,
    pub precision: Precision,
    pub conversion: Conversion,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ResolvedFields {
    pub width: Option<i32>,
    pub precision: Option<i32>,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum FormatValue<'a> {
    Character(u8),
    String(&'a [u8]),
    Signed(i64),
    Unsigned(u64),
    Float(f64),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectiveError {
    MissingFormatCharacter,
    InvalidDirective { end: usize },
}

#[derive(Debug)]
pub enum FormatError {
    Io(io::Error),
    RendererRejected,
    BadFormatString,
    InternalInvariant,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RenderOutcome {
    Written,
    SuppressedOversizedField,
}

pub fn parse_directive(
    format: &[u8],
    percent_index: usize,
) -> Result<(Directive<'_>, usize), DirectiveError> {
    let mut index = percent_index
        .checked_add(1)
        .ok_or(DirectiveError::MissingFormatCharacter)?;
    if index >= format.len() {
        return Err(DirectiveError::MissingFormatCharacter);
    }

    let mut flags = Flags::default();
    while let Some(byte) = format.get(index) {
        match byte {
            b'#' => flags.alternate = true,
            b'-' => flags.left_adjust = true,
            b'+' => flags.force_sign = true,
            b' ' => flags.leading_space = true,
            b'0' => flags.zero_pad = true,
            _ => break,
        }
        index += 1;
    }

    let width = if format.get(index) == Some(&b'*') {
        index += 1;
        FieldWidth::Dynamic
    } else {
        let start = index;
        let mut value = 0_u64;
        while let Some(byte @ b'0'..=b'9') = format.get(index) {
            value = value
                .saturating_mul(10)
                .saturating_add((byte - b'0') as u64);
            index += 1;
        }
        if index == start {
            FieldWidth::None
        } else {
            FieldWidth::Static(value)
        }
    };
    while format.get(index).is_some_and(u8::is_ascii_digit) {
        index += 1;
    }

    let precision = if format.get(index) == Some(&b'.') {
        index += 1;
        let precision = if format.get(index) == Some(&b'*') {
            index += 1;
            Precision::Dynamic
        } else {
            let mut value = 0_u64;
            while let Some(byte @ b'0'..=b'9') = format.get(index) {
                value = value
                    .saturating_mul(10)
                    .saturating_add((byte - b'0') as u64);
                index += 1;
            }
            Precision::Static(value)
        };
        while format.get(index).is_some_and(u8::is_ascii_digit) {
            index += 1;
        }
        precision
    } else {
        Precision::None
    };

    let Some(conversion_byte) = format.get(index).copied() else {
        return Err(DirectiveError::MissingFormatCharacter);
    };
    let conversion = match conversion_byte {
        b'c' => Conversion::Char,
        b's' => Conversion::String,
        b'd' => Conversion::SignedDecimal,
        b'i' => Conversion::SignedInteger,
        b'o' => Conversion::Octal,
        b'u' => Conversion::UnsignedDecimal,
        b'x' => Conversion::HexLower,
        b'X' => Conversion::HexUpper,
        b'a' => Conversion::HexFloatLower,
        b'A' => Conversion::HexFloatUpper,
        b'e' => Conversion::ScientificLower,
        b'E' => Conversion::ScientificUpper,
        b'f' => Conversion::FixedLower,
        b'F' => Conversion::FixedUpper,
        b'g' => Conversion::GeneralLower,
        b'G' => Conversion::GeneralUpper,
        _ => {
            return Err(DirectiveError::InvalidDirective {
                end: index.saturating_add(1),
            })
        }
    };
    let end = index + 1;
    Ok((
        Directive {
            original: &format[percent_index..end],
            flags,
            width,
            precision,
            conversion,
        },
        end,
    ))
}

pub fn mklong(directive: &Directive<'_>) -> Result<Vec<u8>, FormatError> {
    if !is_integer_conversion(directive.conversion)
        || directive.original.first() != Some(&b'%')
        || directive.original.len() < 2
    {
        return Err(FormatError::InternalInvariant);
    }
    let mut normalized = Vec::with_capacity(directive.original.len().saturating_add(1));
    normalized.extend_from_slice(&directive.original[..directive.original.len() - 1]);
    normalized.push(b'l');
    normalized.push(conversion_byte(directive.conversion));
    Ok(normalized)
}

pub fn render_directive(
    output: &mut dyn Output,
    directive: &Directive<'_>,
    fields: ResolvedFields,
    value: FormatValue<'_>,
) -> Result<RenderOutcome, FormatError> {
    match (directive.conversion, value) {
        (Conversion::Char, FormatValue::Character(value)) => {
            render_char(output, directive, fields, value)
        }
        (Conversion::String, FormatValue::String(value)) => {
            render_string(output, directive, fields, value)
        }
        (
            Conversion::SignedDecimal
            | Conversion::SignedInteger
            | Conversion::Octal
            | Conversion::UnsignedDecimal
            | Conversion::HexLower
            | Conversion::HexUpper,
            FormatValue::Signed(_) | FormatValue::Unsigned(_),
        ) => render_integer(output, directive, fields, value),
        (
            Conversion::ScientificLower
            | Conversion::ScientificUpper
            | Conversion::FixedLower
            | Conversion::FixedUpper
            | Conversion::GeneralLower
            | Conversion::GeneralUpper,
            FormatValue::Float(value),
        ) => render_decimal_float(output, directive, fields, value),
        (Conversion::HexFloatLower | Conversion::HexFloatUpper, FormatValue::Float(value)) => {
            render_hex_float(output, directive, fields, value)
        }
        _ => Err(FormatError::InternalInvariant),
    }
}

pub fn render_char(
    output: &mut dyn Output,
    directive: &Directive<'_>,
    fields: ResolvedFields,
    value: u8,
) -> Result<RenderOutcome, FormatError> {
    if has_oversized_static_width(directive) {
        return Ok(RenderOutcome::SuppressedOversizedField);
    }
    if let Some(malformed) = malformed_dynamic_field(directive) {
        return render_malformed_dynamic_field(output, directive, fields, malformed, false);
    }
    if has_oversized_static_precision(directive)
        || has_unrenderable_dynamic_width(directive, fields)
    {
        return Ok(RenderOutcome::SuppressedOversizedField);
    }
    let (width, left_adjust) = resolve_width(directive, fields);
    let padding = width.saturating_sub(1);
    if !left_adjust {
        write_padding(output, padding)?;
    }
    output.write_stdout(&[value]).map_err(FormatError::Io)?;
    if left_adjust {
        write_padding(output, padding)?;
    }
    Ok(RenderOutcome::Written)
}

pub fn render_string(
    output: &mut dyn Output,
    directive: &Directive<'_>,
    fields: ResolvedFields,
    value: &[u8],
) -> Result<RenderOutcome, FormatError> {
    if has_oversized_static_width(directive) {
        return Ok(RenderOutcome::SuppressedOversizedField);
    }
    if let Some(malformed) = malformed_dynamic_field(directive) {
        return render_malformed_dynamic_field(output, directive, fields, malformed, false);
    }
    if has_oversized_static_precision(directive)
        || has_unrenderable_dynamic_width(directive, fields)
    {
        return Ok(RenderOutcome::SuppressedOversizedField);
    }
    let precision = resolve_precision(directive, fields);
    let rendered = match precision {
        Some(precision) => &value[..value.len().min(precision)],
        None => value,
    };
    let (width, left_adjust) = resolve_width(directive, fields);
    let padding = width.saturating_sub(rendered.len());
    if !left_adjust {
        write_padding(output, padding)?;
    }
    output.write_stdout(rendered).map_err(FormatError::Io)?;
    if left_adjust {
        write_padding(output, padding)?;
    }
    Ok(RenderOutcome::Written)
}

pub fn render_integer(
    output: &mut dyn Output,
    directive: &Directive<'_>,
    fields: ResolvedFields,
    value: FormatValue<'_>,
) -> Result<RenderOutcome, FormatError> {
    if has_oversized_static_width(directive) {
        return Ok(RenderOutcome::SuppressedOversizedField);
    }
    if !is_integer_conversion(directive.conversion) {
        return Err(FormatError::InternalInvariant);
    }
    if let Some(malformed) = malformed_dynamic_field(directive) {
        return render_malformed_dynamic_field(output, directive, fields, malformed, true);
    }
    if has_oversized_static_precision(directive)
        || has_unrenderable_dynamic_width(directive, fields)
    {
        return Ok(RenderOutcome::SuppressedOversizedField);
    }
    let format = numeric_format(directive, fields, true)?;
    let mut rendered = String::new();
    let result = match value {
        FormatValue::Signed(value)
            if matches!(
                directive.conversion,
                Conversion::SignedDecimal | Conversion::SignedInteger
            ) =>
        {
            sprintf_locale(
                &mut rendered,
                format.as_str(),
                &C_LOCALE,
                &mut [value.to_arg()],
            )
        }
        FormatValue::Unsigned(value)
            if matches!(
                directive.conversion,
                Conversion::Octal
                    | Conversion::UnsignedDecimal
                    | Conversion::HexLower
                    | Conversion::HexUpper
            ) =>
        {
            sprintf_locale(
                &mut rendered,
                format.as_str(),
                &C_LOCALE,
                &mut [value.to_arg()],
            )
        }
        _ => return Err(FormatError::InternalInvariant),
    };
    map_printf_result(result)?;
    output
        .write_stdout(rendered.as_bytes())
        .map_err(FormatError::Io)?;
    Ok(RenderOutcome::Written)
}

pub fn render_decimal_float(
    output: &mut dyn Output,
    directive: &Directive<'_>,
    fields: ResolvedFields,
    value: f64,
) -> Result<RenderOutcome, FormatError> {
    if !matches!(
        directive.conversion,
        Conversion::ScientificLower
            | Conversion::ScientificUpper
            | Conversion::FixedLower
            | Conversion::FixedUpper
            | Conversion::GeneralLower
            | Conversion::GeneralUpper
    ) {
        return Err(FormatError::InternalInvariant);
    }
    render_float_with_fish(output, directive, fields, value)
}

pub fn render_hex_float(
    output: &mut dyn Output,
    directive: &Directive<'_>,
    fields: ResolvedFields,
    value: f64,
) -> Result<RenderOutcome, FormatError> {
    if !matches!(
        directive.conversion,
        Conversion::HexFloatLower | Conversion::HexFloatUpper
    ) {
        return Err(FormatError::InternalInvariant);
    }
    if has_oversized_static_width(directive) {
        return Ok(RenderOutcome::SuppressedOversizedField);
    }
    if let Some(malformed) = malformed_dynamic_field(directive) {
        return render_malformed_dynamic_field(output, directive, fields, malformed, false);
    }
    if has_oversized_static_precision(directive)
        || has_unrenderable_dynamic_width(directive, fields)
    {
        return Ok(RenderOutcome::SuppressedOversizedField);
    }

    let lower = directive.conversion == Conversion::HexFloatLower;
    if !value.is_finite() {
        return render_hex_nonfinite(output, directive, fields, value, lower);
    }

    let bits = value.to_bits();
    let exponent_bits = ((bits >> 52) & 0x7ff) as i32;
    let fraction = bits & ((1_u64 << 52) - 1);
    let significand = if exponent_bits == 0 {
        fraction
    } else {
        (1_u64 << 52) | fraction
    };
    let exponent = if exponent_bits == 0 {
        if fraction == 0 {
            0
        } else {
            -1022
        }
    } else {
        exponent_bits - 1023
    };

    let precision = resolve_precision(directive, fields);
    let (rendered_significand, stored_digits, output_digits) = match precision {
        Some(precision) if precision < 13 => (
            round_hex_significand(significand, precision),
            precision,
            precision,
        ),
        Some(precision) => (significand, 13, precision),
        None => {
            let trailing_nibbles = (fraction.trailing_zeros() as usize / 4).min(13);
            let digits = 13 - trailing_nibbles;
            (significand >> (4 * (13 - digits)), digits, digits)
        }
    };
    let leading = (rendered_significand >> (4 * stored_digits)) as u8;
    let radix = output_digits > 0 || directive.flags.alternate;
    let exponent_digits = exponent.unsigned_abs().to_string();
    let sign = float_sign_prefix(value, directive);
    let prefix = if lower { b"0x".as_slice() } else { b"0X" };
    let exponent_marker = if lower { b'p' } else { b'P' };
    let exponent_sign = if exponent < 0 { b'-' } else { b'+' };

    let body_len = 1_usize
        .checked_add(usize::from(radix))
        .and_then(|length| length.checked_add(output_digits))
        .and_then(|length| length.checked_add(2))
        .and_then(|length| length.checked_add(exponent_digits.len()))
        .ok_or(FormatError::RendererRejected)?;
    let unpadded_width = sign
        .len()
        .checked_add(prefix.len())
        .and_then(|length| length.checked_add(body_len))
        .ok_or(FormatError::RendererRejected)?;
    let (width, left_adjust) = resolve_width(directive, fields);
    let padding = width.saturating_sub(unpadded_width);

    if !left_adjust && !directive.flags.zero_pad {
        write_padding(output, padding)?;
    }
    output.write_stdout(sign).map_err(FormatError::Io)?;
    output.write_stdout(prefix).map_err(FormatError::Io)?;
    if !left_adjust && directive.flags.zero_pad {
        write_zero_padding(output, padding)?;
    }

    let digits = if lower {
        b"0123456789abcdef"
    } else {
        b"0123456789ABCDEF"
    };
    output
        .write_stdout(&[digits[leading as usize]])
        .map_err(FormatError::Io)?;
    if radix {
        output.write_stdout(b".").map_err(FormatError::Io)?;
    }
    if stored_digits > 0 {
        let mut rendered = [0_u8; 13];
        for (index, byte) in rendered[..stored_digits].iter_mut().enumerate() {
            let shift = 4 * (stored_digits - index - 1);
            *byte = digits[((rendered_significand >> shift) & 0xf) as usize];
        }
        output
            .write_stdout(&rendered[..stored_digits])
            .map_err(FormatError::Io)?;
    }
    write_zero_padding(output, output_digits - stored_digits)?;
    output
        .write_stdout(&[exponent_marker, exponent_sign])
        .map_err(FormatError::Io)?;
    output
        .write_stdout(exponent_digits.as_bytes())
        .map_err(FormatError::Io)?;
    if left_adjust {
        write_padding(output, padding)?;
    }
    Ok(RenderOutcome::Written)
}

fn render_hex_nonfinite(
    output: &mut dyn Output,
    directive: &Directive<'_>,
    fields: ResolvedFields,
    value: f64,
    lower: bool,
) -> Result<RenderOutcome, FormatError> {
    let sign = float_sign_prefix(value, directive);
    let body = match (value.is_nan(), lower) {
        (true, true) => b"nan".as_slice(),
        (true, false) => b"NAN".as_slice(),
        (false, true) => b"inf".as_slice(),
        (false, false) => b"INF".as_slice(),
    };
    let unpadded_width = sign
        .len()
        .checked_add(body.len())
        .ok_or(FormatError::RendererRejected)?;
    let (width, left_adjust) = resolve_width(directive, fields);
    let padding = width.saturating_sub(unpadded_width);
    if !left_adjust {
        write_padding(output, padding)?;
    }
    output.write_stdout(sign).map_err(FormatError::Io)?;
    output.write_stdout(body).map_err(FormatError::Io)?;
    if left_adjust {
        write_padding(output, padding)?;
    }
    Ok(RenderOutcome::Written)
}

fn float_sign_prefix(value: f64, directive: &Directive<'_>) -> &'static [u8] {
    if value.is_sign_negative() {
        b"-"
    } else if directive.flags.force_sign {
        b"+"
    } else if directive.flags.leading_space {
        b" "
    } else {
        b""
    }
}

fn round_hex_significand(significand: u64, precision: usize) -> u64 {
    debug_assert!(precision < 13);
    let discarded_bits = 4 * (13 - precision);
    let retained = significand >> discarded_bits;
    let mask = (1_u64 << discarded_bits) - 1;
    let discarded = significand & mask;
    let halfway = 1_u64 << (discarded_bits - 1);
    retained + u64::from(discarded > halfway || (discarded == halfway && retained & 1 != 0))
}

fn render_float_with_fish(
    output: &mut dyn Output,
    directive: &Directive<'_>,
    fields: ResolvedFields,
    value: f64,
) -> Result<RenderOutcome, FormatError> {
    if has_oversized_static_width(directive) {
        return Ok(RenderOutcome::SuppressedOversizedField);
    }
    if let Some(malformed) = malformed_dynamic_field(directive) {
        return render_malformed_dynamic_field(output, directive, fields, malformed, false);
    }
    if has_oversized_static_precision(directive)
        || has_unrenderable_dynamic_width(directive, fields)
    {
        return Ok(RenderOutcome::SuppressedOversizedField);
    }
    let format = numeric_format(directive, fields, false)?;
    let mut rendered = String::new();
    let result = sprintf_locale(
        &mut rendered,
        format.as_str(),
        &C_LOCALE,
        &mut [value.to_arg()],
    );
    map_printf_result(result)?;
    output
        .write_stdout(rendered.as_bytes())
        .map_err(FormatError::Io)?;
    Ok(RenderOutcome::Written)
}

fn numeric_format(
    directive: &Directive<'_>,
    fields: ResolvedFields,
    long_integer: bool,
) -> Result<String, FormatError> {
    let mut format = String::from("%");
    if directive.flags.alternate {
        format.push('#');
    }

    let (width, dynamic_left_adjust) = resolved_signed_width(directive, fields);
    if directive.flags.left_adjust || dynamic_left_adjust {
        format.push('-');
    }
    if directive.flags.force_sign {
        format.push('+');
    }
    if directive.flags.leading_space {
        format.push(' ');
    }
    if directive.flags.zero_pad {
        format.push('0');
    }
    if let Some(width) = width {
        format.push_str(&width.to_string());
    }

    if let Some(precision) = resolved_signed_precision(directive, fields) {
        format.push('.');
        format.push_str(&precision.to_string());
    }
    if long_integer {
        format.push('l');
    }
    format.push(conversion_byte(directive.conversion) as char);
    Ok(format)
}

fn map_printf_result(result: Result<usize, PrintfError>) -> Result<(), FormatError> {
    match result {
        Ok(_) => Ok(()),
        Err(PrintfError::Overflow) => Err(FormatError::RendererRejected),
        Err(PrintfError::BadFormatString) => Err(FormatError::BadFormatString),
        Err(
            PrintfError::MissingArg
            | PrintfError::ExtraArg
            | PrintfError::BadArgType
            | PrintfError::Fmt(_),
        ) => Err(FormatError::InternalInvariant),
    }
}

fn has_oversized_static_width(directive: &Directive<'_>) -> bool {
    matches!(directive.width, FieldWidth::Static(value) if value > i32::MAX as u64)
}

fn has_oversized_static_precision(directive: &Directive<'_>) -> bool {
    matches!(directive.precision, Precision::Static(value) if value > i32::MAX as u64)
}

fn has_unrenderable_dynamic_width(directive: &Directive<'_>, fields: ResolvedFields) -> bool {
    directive.width == FieldWidth::Dynamic && fields.width == Some(i32::MIN)
}

#[derive(Clone, Copy)]
enum MalformedDynamicField {
    Width { remainder: usize },
    Precision { remainder: usize },
}

fn malformed_dynamic_field(directive: &Directive<'_>) -> Option<MalformedDynamicField> {
    let format = directive.original;
    if format.first() != Some(&b'%') {
        return None;
    }

    let mut index = 1;
    while format.get(index).is_some_and(|byte| SKIP1.contains(byte)) {
        index += 1;
    }

    if format.get(index) == Some(&b'*') {
        index += 1;
        if format.get(index).is_some_and(u8::is_ascii_digit) {
            return Some(MalformedDynamicField::Width { remainder: index });
        }
    } else {
        while format.get(index).is_some_and(u8::is_ascii_digit) {
            index += 1;
        }
    }

    if format.get(index) != Some(&b'.') {
        return None;
    }
    index += 1;
    if format.get(index) == Some(&b'*') {
        index += 1;
        if format.get(index).is_some_and(u8::is_ascii_digit) {
            return Some(MalformedDynamicField::Precision { remainder: index });
        }
    }
    None
}

fn render_malformed_dynamic_field(
    output: &mut dyn Output,
    directive: &Directive<'_>,
    fields: ResolvedFields,
    malformed: MalformedDynamicField,
    long_integer: bool,
) -> Result<RenderOutcome, FormatError> {
    // The source scanner accepts digits after `*`; glibc echoes that malformed
    // specification after substituting stars instead of formatting the value.
    let mut rendered = Vec::with_capacity(directive.original.len().saturating_add(24));
    rendered.push(b'%');
    if directive.flags.alternate {
        rendered.push(b'#');
    }
    if directive.flags.force_sign {
        rendered.push(b'+');
    } else if directive.flags.leading_space {
        rendered.push(b' ');
    }

    let (width, dynamic_left_adjust) = resolved_signed_width(directive, fields);
    if directive.flags.left_adjust || dynamic_left_adjust {
        rendered.push(b'-');
    }
    if directive.flags.zero_pad && !directive.flags.left_adjust {
        rendered.push(b'0');
    }
    if let Some(width) = width.filter(|width| *width != 0) {
        let displayed_width =
            if directive.width == FieldWidth::Dynamic && fields.width == Some(i32::MIN) {
                (i32::MIN as i64 as u64).to_string()
            } else {
                width.to_string()
            };
        rendered.extend_from_slice(displayed_width.as_bytes());
    }

    let remainder = match malformed {
        MalformedDynamicField::Width { remainder } => remainder,
        MalformedDynamicField::Precision { remainder } => {
            if let Some(precision) = resolved_signed_precision(directive, fields) {
                rendered.push(b'.');
                rendered.extend_from_slice(precision.to_string().as_bytes());
            }
            remainder
        }
    };
    let tail = directive
        .original
        .get(remainder..)
        .ok_or(FormatError::InternalInvariant)?;
    if long_integer {
        let (conversion, prefix) = tail.split_last().ok_or(FormatError::InternalInvariant)?;
        rendered.extend_from_slice(prefix);
        rendered.push(b'l');
        rendered.push(*conversion);
    } else {
        rendered.extend_from_slice(tail);
    }
    output.write_stdout(&rendered).map_err(FormatError::Io)?;
    Ok(RenderOutcome::Written)
}

fn resolve_width(directive: &Directive<'_>, fields: ResolvedFields) -> (usize, bool) {
    let (width, dynamic_left_adjust) = resolved_signed_width(directive, fields);
    (
        width.unwrap_or(0) as usize,
        directive.flags.left_adjust || dynamic_left_adjust,
    )
}

fn resolved_signed_width(directive: &Directive<'_>, fields: ResolvedFields) -> (Option<u32>, bool) {
    let width = match directive.width {
        FieldWidth::None => return (None, false),
        FieldWidth::Static(value) => return (Some(value as u32), false),
        FieldWidth::Dynamic => fields.width.unwrap_or(0),
    };
    if width < 0 {
        (Some(width.unsigned_abs()), true)
    } else {
        (Some(width as u32), false)
    }
}

fn resolve_precision(directive: &Directive<'_>, fields: ResolvedFields) -> Option<usize> {
    resolved_signed_precision(directive, fields).map(|value| value as usize)
}

fn resolved_signed_precision(directive: &Directive<'_>, fields: ResolvedFields) -> Option<u32> {
    match directive.precision {
        Precision::None => None,
        Precision::Static(value) => Some(value as u32),
        Precision::Dynamic => {
            let value = fields.precision.unwrap_or(0);
            (value >= 0).then_some(value as u32)
        }
    }
}

fn write_padding(output: &mut dyn Output, mut count: usize) -> Result<(), FormatError> {
    const SPACES: &[u8] = b"                                ";
    while count > 0 {
        let chunk = count.min(SPACES.len());
        output
            .write_stdout(&SPACES[..chunk])
            .map_err(FormatError::Io)?;
        count -= chunk;
    }
    Ok(())
}

fn write_zero_padding(output: &mut dyn Output, mut count: usize) -> Result<(), FormatError> {
    const ZEROES: &[u8] = b"00000000000000000000000000000000";
    while count > 0 {
        let chunk = count.min(ZEROES.len());
        output
            .write_stdout(&ZEROES[..chunk])
            .map_err(FormatError::Io)?;
        count -= chunk;
    }
    Ok(())
}

fn is_integer_conversion(conversion: Conversion) -> bool {
    matches!(
        conversion,
        Conversion::SignedDecimal
            | Conversion::SignedInteger
            | Conversion::Octal
            | Conversion::UnsignedDecimal
            | Conversion::HexLower
            | Conversion::HexUpper
    )
}

fn conversion_byte(conversion: Conversion) -> u8 {
    match conversion {
        Conversion::Char => b'c',
        Conversion::String => b's',
        Conversion::SignedDecimal => b'd',
        Conversion::SignedInteger => b'i',
        Conversion::Octal => b'o',
        Conversion::UnsignedDecimal => b'u',
        Conversion::HexLower => b'x',
        Conversion::HexUpper => b'X',
        Conversion::HexFloatLower => b'a',
        Conversion::HexFloatUpper => b'A',
        Conversion::ScientificLower => b'e',
        Conversion::ScientificUpper => b'E',
        Conversion::FixedLower => b'f',
        Conversion::FixedUpper => b'F',
        Conversion::GeneralLower => b'g',
        Conversion::GeneralUpper => b'G',
    }
}

#[cfg(test)]
mod tests {
    use super::{
        map_printf_result, mklong, parse_directive, render_directive, Conversion, Directive,
        DirectiveError, FieldWidth, Flags, FormatError, FormatValue, Precision, RenderOutcome,
        ResolvedFields, SKIP1, SKIP2,
    };
    use crate::printf::{run, MockOutput};
    use fish_printf::Error as PrintfError;

    const NO_FIELDS: ResolvedFields = ResolvedFields {
        width: None,
        precision: None,
    };

    fn parse(format: &[u8]) -> Directive<'_> {
        let (directive, end) =
            parse_directive(format, 0).unwrap_or_else(|error| panic!("{format:?}: {error:?}"));
        assert_eq!(end, format.len(), "end for {format:?}");
        directive
    }

    fn render(
        format: &[u8],
        fields: ResolvedFields,
        value: FormatValue<'_>,
    ) -> (RenderOutcome, MockOutput) {
        let directive = parse(format);
        let mut output = MockOutput::default();
        let outcome = render_directive(&mut output, &directive, fields, value)
            .unwrap_or_else(|error| panic!("{format:?}: {error:?}"));
        (outcome, output)
    }

    #[test]
    fn directive_grammar_and_errors() {
        assert_eq!(SKIP1, b"#-+ 0");
        assert_eq!(SKIP2, b"0123456789");

        let conversions = [
            (b'c', Conversion::Char),
            (b's', Conversion::String),
            (b'd', Conversion::SignedDecimal),
            (b'i', Conversion::SignedInteger),
            (b'o', Conversion::Octal),
            (b'u', Conversion::UnsignedDecimal),
            (b'x', Conversion::HexLower),
            (b'X', Conversion::HexUpper),
            (b'a', Conversion::HexFloatLower),
            (b'A', Conversion::HexFloatUpper),
            (b'e', Conversion::ScientificLower),
            (b'E', Conversion::ScientificUpper),
            (b'f', Conversion::FixedLower),
            (b'F', Conversion::FixedUpper),
            (b'g', Conversion::GeneralLower),
            (b'G', Conversion::GeneralUpper),
        ];
        for (byte, expected) in conversions {
            let format = [b'%', byte];
            let directive = parse(&format);
            assert_eq!(directive.conversion, expected, "conversion {byte:?}");
            assert_eq!(directive.original, format);
        }

        let directive = parse(b"%##--++  00s");
        assert_eq!(
            directive.flags,
            Flags {
                alternate: true,
                left_adjust: true,
                force_sign: true,
                leading_space: true,
                zero_pad: true,
            }
        );
        assert_eq!(directive.width, FieldWidth::None);
        assert_eq!(directive.precision, Precision::None);

        let directive = parse(b"%0012.003s");
        assert!(directive.flags.zero_pad);
        assert_eq!(directive.width, FieldWidth::Static(12));
        assert_eq!(directive.precision, Precision::Static(3));

        let directive = parse(b"%*s");
        assert_eq!(directive.width, FieldWidth::Dynamic);
        assert_eq!(directive.precision, Precision::None);

        let directive = parse(b"%.s");
        assert_eq!(directive.width, FieldWidth::None);
        assert_eq!(directive.precision, Precision::Static(0));

        let directive = parse(b"%12.*s");
        assert_eq!(directive.width, FieldWidth::Static(12));
        assert_eq!(directive.precision, Precision::Dynamic);

        let directive = parse(b"%#-+ 0*12.*34s");
        assert_eq!(directive.width, FieldWidth::Dynamic);
        assert_eq!(directive.precision, Precision::Dynamic);
        assert_eq!(directive.original, b"%#-+ 0*12.*34s");

        let (directive, next) = parse_directive(b"xx%5.2s!", 2).expect("embedded directive");
        assert_eq!(directive.original, b"%5.2s");
        assert_eq!(directive.width, FieldWidth::Static(5));
        assert_eq!(directive.precision, Precision::Static(2));
        assert_eq!(next, 7);

        for format in [
            b"%".as_slice(),
            b"%#-+ 0".as_slice(),
            b"%123".as_slice(),
            b"%*".as_slice(),
            b"%*123".as_slice(),
            b"%.".as_slice(),
            b"%.123".as_slice(),
            b"%.*".as_slice(),
            b"%.*123".as_slice(),
            b"%12.".as_slice(),
            b"%12.*".as_slice(),
            b"%#*12.*34".as_slice(),
        ] {
            assert_eq!(
                parse_directive(format, 0),
                Err(DirectiveError::MissingFormatCharacter),
                "missing conversion for {format:?}"
            );
        }
        assert_eq!(
            parse_directive(b"", 0),
            Err(DirectiveError::MissingFormatCharacter)
        );
        assert_eq!(
            parse_directive(b"%", usize::MAX),
            Err(DirectiveError::MissingFormatCharacter)
        );

        for (format, end, span) in [
            (b"%Qtail".as_slice(), 2, b"%Q".as_slice()),
            (b"%#12Qtail".as_slice(), 5, b"%#12Q".as_slice()),
            (b"%*12Qtail".as_slice(), 5, b"%*12Q".as_slice()),
            (b"%.*12Qtail".as_slice(), 6, b"%.*12Q".as_slice()),
            (b"%1*s".as_slice(), 3, b"%1*".as_slice()),
            (b"%..s".as_slice(), 3, b"%..".as_slice()),
            (b"%ls".as_slice(), 2, b"%l".as_slice()),
            (b"%b".as_slice(), 2, b"%b".as_slice()),
            (b"%%".as_slice(), 2, b"%%".as_slice()),
            (b"%#\xfftail".as_slice(), 3, b"%#\xff".as_slice()),
        ] {
            assert_eq!(
                parse_directive(format, 0),
                Err(DirectiveError::InvalidDirective { end }),
                "error for {format:?}"
            );
            assert_eq!(&format[..end], span, "span for {format:?}");
        }
    }

    #[test]
    fn byte_string_and_character_fields() {
        let (outcome, output) =
            render(b"%s", NO_FIELDS, FormatValue::String(b"\xff\0A".as_slice()));
        assert_eq!(outcome, RenderOutcome::Written);
        assert_eq!(output.stdout, b"\xff\0A");

        let (_, output) = render(
            b"%5.2s",
            NO_FIELDS,
            FormatValue::String(b"\xff\0A".as_slice()),
        );
        assert_eq!(output.stdout, b"   \xff\0");

        let (_, output) = render(
            b"%-5.2s",
            NO_FIELDS,
            FormatValue::String(b"\xff\0A".as_slice()),
        );
        assert_eq!(output.stdout, b"\xff\0   ");

        let (_, output) = render(
            b"%#+ 05.3s",
            NO_FIELDS,
            FormatValue::String(b"abcdef".as_slice()),
        );
        assert_eq!(output.stdout, b"  abc");

        let (_, output) = render(
            b"%0*s",
            ResolvedFields {
                width: Some(-4),
                precision: None,
            },
            FormatValue::String(b"x".as_slice()),
        );
        assert_eq!(output.stdout, b"x   ");

        let (outcome, output) = render(
            b"%*s",
            ResolvedFields {
                width: Some(i32::MIN),
                precision: None,
            },
            FormatValue::String(b"x".as_slice()),
        );
        assert_eq!(outcome, RenderOutcome::SuppressedOversizedField);
        assert!(output.stdout.is_empty());

        let (_, output) = render(
            b"%*.*s",
            ResolvedFields {
                width: Some(5),
                precision: Some(2),
            },
            FormatValue::String(b"abcdef".as_slice()),
        );
        assert_eq!(output.stdout, b"   ab");

        let (_, output) = render(
            b"%5.*s",
            ResolvedFields {
                width: None,
                precision: Some(-1),
            },
            FormatValue::String(b"abcdef".as_slice()),
        );
        assert_eq!(output.stdout, b"abcdef");

        let (_, output) = render(b"%3.0c", NO_FIELDS, FormatValue::Character(0));
        assert_eq!(output.stdout, b"  \0");

        let (_, output) = render(
            b"%# +0*c",
            ResolvedFields {
                width: Some(-3),
                precision: None,
            },
            FormatValue::Character(0xff),
        );
        assert_eq!(output.stdout, b"\xff  ");

        let (_, output) = render(
            b"%.*c",
            ResolvedFields {
                width: None,
                precision: Some(0),
            },
            FormatValue::Character(b'Z'),
        );
        assert_eq!(output.stdout, b"Z");

        let (_, output) = render(
            b"%*5s",
            ResolvedFields {
                width: Some(3),
                precision: None,
            },
            FormatValue::String(b"ignored".as_slice()),
        );
        assert_eq!(output.stdout, b"%35s");

        let (_, output) = render(
            b"%*5.2147483648s",
            ResolvedFields {
                width: Some(3),
                precision: None,
            },
            FormatValue::String(b"ignored".as_slice()),
        );
        assert_eq!(output.stdout, b"%35.2147483648s");

        let (_, output) = render(
            b"%0*5s",
            ResolvedFields {
                width: Some(-3),
                precision: None,
            },
            FormatValue::String(b"ignored".as_slice()),
        );
        assert_eq!(output.stdout, b"%-035s");

        let (_, output) = render(
            b"%*5s",
            ResolvedFields {
                width: Some(i32::MIN),
                precision: None,
            },
            FormatValue::String(b"ignored".as_slice()),
        );
        assert_eq!(output.stdout, b"%-184467440715620679685s");

        let (_, output) = render(
            b"%0010.*5s",
            ResolvedFields {
                width: None,
                precision: Some(2),
            },
            FormatValue::String(b"ignored".as_slice()),
        );
        assert_eq!(output.stdout, b"%010.25s");

        let (_, output) = render(
            b"%.*5s",
            ResolvedFields {
                width: None,
                precision: Some(-2),
            },
            FormatValue::String(b"ignored".as_slice()),
        );
        assert_eq!(output.stdout, b"%5s");
    }

    #[test]
    fn integer_rendering_matrix() {
        let cases: &[(&[u8], FormatValue<'_>, &[u8])] = &[
            (b"%d", FormatValue::Signed(-42), b"-42"),
            (b"%i", FormatValue::Signed(-42), b"-42"),
            (b"%o", FormatValue::Unsigned(0o777), b"777"),
            (
                b"%u",
                FormatValue::Unsigned(u64::MAX),
                b"18446744073709551615",
            ),
            (b"%x", FormatValue::Unsigned(u64::MAX), b"ffffffffffffffff"),
            (b"%X", FormatValue::Unsigned(u64::MAX), b"FFFFFFFFFFFFFFFF"),
            (
                b"%d",
                FormatValue::Signed(i64::MIN),
                b"-9223372036854775808",
            ),
            (b"%i", FormatValue::Signed(i64::MAX), b"9223372036854775807"),
            (b"%#d", FormatValue::Signed(42), b"42"),
            (b"%+d", FormatValue::Signed(42), b"+42"),
            (b"% d", FormatValue::Signed(42), b" 42"),
            (b"% +d", FormatValue::Signed(42), b"+42"),
            (b"%05d", FormatValue::Signed(-42), b"-0042"),
            (b"%-05d", FormatValue::Signed(42), b"42   "),
            (b"%##--++  005d", FormatValue::Signed(42), b"+42  "),
            (b"%#o", FormatValue::Unsigned(9), b"011"),
            (b"%#x", FormatValue::Unsigned(42), b"0x2a"),
            (b"%#X", FormatValue::Unsigned(42), b"0X2A"),
            (b"%#x", FormatValue::Unsigned(0), b"0"),
            (b"%8.5d", FormatValue::Signed(42), b"   00042"),
            (b"%08.5d", FormatValue::Signed(42), b"   00042"),
            (b"%#8.4x", FormatValue::Unsigned(42), b"  0x002a"),
            (b"%#08x", FormatValue::Unsigned(42), b"0x00002a"),
            (b"%.0d", FormatValue::Signed(0), b""),
            (b"%+.0d", FormatValue::Signed(0), b"+"),
            (b"% .0i", FormatValue::Signed(0), b" "),
            (b"%#.0o", FormatValue::Unsigned(0), b"0"),
            (b"%#.0x", FormatValue::Unsigned(0), b""),
            (b"%.0u", FormatValue::Unsigned(0), b""),
        ];
        for &(format, value, expected) in cases {
            let (outcome, output) = render(format, NO_FIELDS, value);
            assert_eq!(outcome, RenderOutcome::Written, "{format:?}");
            assert_eq!(output.stdout, expected, "{format:?}");
        }

        let dynamic_cases = [
            (
                b"%*d".as_slice(),
                ResolvedFields {
                    width: Some(-6),
                    precision: None,
                },
                FormatValue::Signed(42),
                b"42    ".as_slice(),
            ),
            (
                b"%0*d".as_slice(),
                ResolvedFields {
                    width: Some(6),
                    precision: None,
                },
                FormatValue::Signed(-42),
                b"-00042".as_slice(),
            ),
            (
                b"%*.*x".as_slice(),
                ResolvedFields {
                    width: Some(8),
                    precision: Some(4),
                },
                FormatValue::Unsigned(42),
                b"    002a".as_slice(),
            ),
            (
                b"%08.*u".as_slice(),
                ResolvedFields {
                    width: None,
                    precision: Some(-1),
                },
                FormatValue::Unsigned(42),
                b"00000042".as_slice(),
            ),
            (
                b"%*.*d".as_slice(),
                ResolvedFields {
                    width: None,
                    precision: None,
                },
                FormatValue::Signed(0),
                b"".as_slice(),
            ),
        ];
        for (format, fields, value, expected) in dynamic_cases {
            let (outcome, output) = render(format, fields, value);
            assert_eq!(outcome, RenderOutcome::Written, "{format:?}");
            assert_eq!(output.stdout, expected, "{format:?}");
        }

        let directive = parse(b"%#08.4x");
        assert_eq!(
            mklong(&directive).expect("normalize hexadecimal directive"),
            b"%#08.4lx"
        );
        let directive = parse(b"%*.*i");
        assert_eq!(
            mklong(&directive).expect("normalize signed directive"),
            b"%*.*li"
        );
        assert!(matches!(
            mklong(&parse(b"%s")),
            Err(FormatError::InternalInvariant)
        ));

        let (_, output) = render(
            b"%*5d",
            ResolvedFields {
                width: Some(3),
                precision: None,
            },
            FormatValue::Signed(42),
        );
        assert_eq!(output.stdout, b"%35ld");
        let (_, output) = render(
            b"%.*5x",
            ResolvedFields {
                width: None,
                precision: Some(2),
            },
            FormatValue::Unsigned(42),
        );
        assert_eq!(output.stdout, b"%.25lx");

        for format in [b"%2147483648d".as_slice(), b"%.2147483648u"] {
            let value = if format.ends_with(b"d") {
                FormatValue::Signed(42)
            } else {
                FormatValue::Unsigned(42)
            };
            let (outcome, output) = render(format, NO_FIELDS, value);
            assert_eq!(outcome, RenderOutcome::SuppressedOversizedField);
            assert!(output.stdout.is_empty());
        }
        let (outcome, output) = render(
            b"%*x",
            ResolvedFields {
                width: Some(i32::MIN),
                precision: None,
            },
            FormatValue::Unsigned(42),
        );
        assert_eq!(outcome, RenderOutcome::SuppressedOversizedField);
        assert!(output.stdout.is_empty());

        let args = vec![b"printf".to_vec(), b"%d|%i|%o|%u|%x|%X".to_vec()];
        let mut output = MockOutput::default();
        let outcome = run(&args, &mut output).expect("render missing integer defaults");
        assert_eq!(outcome.status, 0);
        assert_eq!(output.stdout, b"0|0|0|0|0|0");
        assert!(output.stderr.is_empty());
    }

    #[test]
    fn decimal_float_rendering_matrix() {
        let negative_nan = f64::from_bits(f64::NAN.to_bits() | (1_u64 << 63));
        let cases: &[(&[u8], f64, &[u8])] = &[
            (b"%e", 123.456, b"1.234560e+02"),
            (b"%E", 123.456, b"1.234560E+02"),
            (b"%f", 123.456, b"123.456000"),
            (b"%F", 123.456, b"123.456000"),
            (b"%g", 1_234_567.0, b"1.23457e+06"),
            (b"%G", 1_234_567.0, b"1.23457E+06"),
            (b"%.0f", 2.5, b"2"),
            (b"%.0f", 3.5, b"4"),
            (b"%#.0f", 2.5, b"2."),
            (b"%.1e", 9.99, b"1.0e+01"),
            (b"%.1g", 9.99, b"1e+01"),
            (b"%.0g", 9.9, b"1e+01"),
            (b"%#.5g", 1.0, b"1.0000"),
            (b"%010.2f", 1.25, b"0000001.25"),
            (b"%+010.2f", 1.25, b"+000001.25"),
            (b"% 010.2f", 1.25, b" 000001.25"),
            (b"%-10.2f", 1.25, b"1.25      "),
            (b"%f", -0.0, b"-0.000000"),
            (b"%+f", 0.0, b"+0.000000"),
            (b"% f", 0.0, b" 0.000000"),
            (b"%f", f64::INFINITY, b"inf"),
            (b"%F", f64::INFINITY, b"INF"),
            (b"%+010F", f64::INFINITY, b"      +INF"),
            (b"%-10f", f64::NEG_INFINITY, b"-inf      "),
            (b"%f", negative_nan, b"-nan"),
            (b"%F", negative_nan, b"-NAN"),
        ];
        for &(format, value, expected) in cases {
            let (outcome, output) = render(format, NO_FIELDS, FormatValue::Float(value));
            assert_eq!(outcome, RenderOutcome::Written, "{format:?}");
            assert_eq!(output.stdout, expected, "{format:?}");
        }

        let (_, output) = render(
            b"%*.*f",
            ResolvedFields {
                width: Some(10),
                precision: Some(3),
            },
            FormatValue::Float(1.25),
        );
        assert_eq!(output.stdout, b"     1.250");

        let (_, output) = render(
            b"%0*.*g",
            ResolvedFields {
                width: Some(-10),
                precision: Some(4),
            },
            FormatValue::Float(12.5),
        );
        assert_eq!(output.stdout, b"12.5      ");

        let args = vec![b"printf".to_vec(), b"%e|%E|%f|%F|%g|%G".to_vec()];
        let mut output = MockOutput::default();
        let outcome = run(&args, &mut output).expect("render missing decimal float defaults");
        assert_eq!(outcome.status, 0);
        assert_eq!(
            output.stdout,
            b"0.000000e+00|0.000000E+00|0.000000|0.000000|0|0"
        );
        assert!(output.stderr.is_empty());
    }

    #[test]
    fn hexadecimal_float_rendering_matrix() {
        let negative_nan = f64::from_bits(f64::NAN.to_bits() | (1_u64 << 63));
        let cases: &[(&[u8], f64, &[u8])] = &[
            (b"%a", 0.0, b"0x0p+0"),
            (b"%a", -0.0, b"-0x0p+0"),
            (b"%a", 1.0, b"0x1p+0"),
            (b"%#a", 1.0, b"0x1.p+0"),
            (b"%A", 1.5, b"0X1.8P+0"),
            (b"%.0a", 1.5, b"0x2p+0"),
            (b"%#.0a", 1.5, b"0x2.p+0"),
            (b"%.1a", 1.90625, b"0x1.ep+0"),
            (b"%.1a", 1.84375, b"0x1.ep+0"),
            (b"%.1a", 1.78125, b"0x1.cp+0"),
            (b"%.20a", 1.5, b"0x1.80000000000000000000p+0"),
            (b"%a", f64::from_bits(1), b"0x0.0000000000001p-1022"),
            (b"%A", f64::from_bits(1), b"0X0.0000000000001P-1022"),
            (
                b"%a",
                f64::from_bits((1_u64 << 52) - 1),
                b"0x0.fffffffffffffp-1022",
            ),
            (b"%.0a", f64::from_bits((1_u64 << 52) - 1), b"0x1p-1022"),
            (b"%a", f64::MIN_POSITIVE, b"0x1p-1022"),
            (b"%a", f64::MAX, b"0x1.fffffffffffffp+1023"),
            (b"%+020.3a", 1.5, b"+0x0000000001.800p+0"),
            (b"% 020.3a", 1.5, b" 0x0000000001.800p+0"),
            (b"%-020.3a", 1.5, b"0x1.800p+0          "),
            (b"%20a", f64::INFINITY, b"                 inf"),
            (b"%020a", f64::INFINITY, b"                 inf"),
            (b"%-20A", negative_nan, b"-NAN                "),
        ];
        for &(format, value, expected) in cases {
            let (outcome, output) = render(format, NO_FIELDS, FormatValue::Float(value));
            assert_eq!(outcome, RenderOutcome::Written, "{format:?}");
            assert_eq!(output.stdout, expected, "{format:?}");
        }

        let (_, output) = render(
            b"%*.*a",
            ResolvedFields {
                width: Some(20),
                precision: Some(3),
            },
            FormatValue::Float(1.5),
        );
        assert_eq!(output.stdout, b"          0x1.800p+0");

        let (_, output) = render(
            b"%0*.*A",
            ResolvedFields {
                width: Some(-16),
                precision: Some(2),
            },
            FormatValue::Float(1.5),
        );
        assert_eq!(output.stdout, b"0X1.80P+0       ");

        for format in [b"%2147483648a".as_slice(), b"%.2147483648A"] {
            let (outcome, output) = render(format, NO_FIELDS, FormatValue::Float(1.5));
            assert_eq!(outcome, RenderOutcome::SuppressedOversizedField);
            assert!(output.stdout.is_empty());
        }

        let args = vec![b"printf".to_vec(), b"%a|%A".to_vec()];
        let mut output = MockOutput::default();
        let outcome = run(&args, &mut output).expect("render missing hexadecimal float defaults");
        assert_eq!(outcome.status, 0);
        assert_eq!(output.stdout, b"0x0p+0|0X0P+0");
        assert!(output.stderr.is_empty());
    }

    #[test]
    fn fields_above_int_max_are_suppressed() {
        for format in [
            b"%2147483648s".as_slice(),
            b"%.2147483648s".as_slice(),
            b"%999999999999999999999999999999999999s".as_slice(),
        ] {
            let (outcome, output) =
                render(format, NO_FIELDS, FormatValue::String(b"value".as_slice()));
            assert_eq!(
                outcome,
                RenderOutcome::SuppressedOversizedField,
                "{format:?}"
            );
            assert!(output.stdout.is_empty(), "{format:?}");
        }

        let (outcome, output) = render(b"%2147483648c", NO_FIELDS, FormatValue::Character(b'X'));
        assert_eq!(outcome, RenderOutcome::SuppressedOversizedField);
        assert!(output.stdout.is_empty());

        let (outcome, output) = render(
            b"%2147483648.*5s",
            ResolvedFields {
                width: None,
                precision: Some(2),
            },
            FormatValue::String(b"value".as_slice()),
        );
        assert_eq!(outcome, RenderOutcome::SuppressedOversizedField);
        assert!(output.stdout.is_empty());

        for format in [b"%2147483648s|%s".as_slice(), b"%.2147483648s|%s"] {
            let args = vec![
                b"printf".to_vec(),
                format.to_vec(),
                b"suppressed".to_vec(),
                b"visible".to_vec(),
            ];
            let mut output = MockOutput::default();
            let outcome = run(&args, &mut output).expect("run oversized field command");
            assert_eq!(outcome.status, 0, "{format:?}");
            assert_eq!(output.stdout, b"|visible", "{format:?}");
            assert!(output.stderr.is_empty(), "{format:?}");
        }

        let args = vec![
            b"printf".to_vec(),
            b"%*s|%s".to_vec(),
            b"-2147483648".to_vec(),
            b"suppressed".to_vec(),
            b"visible".to_vec(),
        ];
        let mut output = MockOutput::default();
        let outcome = run(&args, &mut output).expect("run minimum dynamic width");
        assert_eq!(outcome.status, 0);
        assert_eq!(output.stdout, b"|visible");
        assert!(output.stderr.is_empty());
    }

    #[test]
    fn renderer_errors_preserve_source_categories() {
        assert!(map_printf_result(Ok(0)).is_ok());
        assert!(matches!(
            map_printf_result(Err(PrintfError::Overflow)),
            Err(FormatError::RendererRejected)
        ));
        assert!(matches!(
            map_printf_result(Err(PrintfError::BadFormatString)),
            Err(FormatError::BadFormatString)
        ));
        assert!(matches!(
            map_printf_result(Err(PrintfError::MissingArg)),
            Err(FormatError::InternalInvariant)
        ));
    }
}
