#![allow(dead_code)]

use std::cmp::Ordering;
use std::sync::OnceLock;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RangeState {
    InRange,
    Underflow,
    Overflow,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ParsedNumber<T> {
    pub value: T,
    pub end: usize,
    pub range: RangeState,
}

pub fn atoi(input: &[u8]) -> i32 {
    let mut index = 0;
    while input.get(index).is_some_and(|byte| is_c_whitespace(*byte)) {
        index += 1;
    }

    let negative = match input.get(index) {
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

    let limit = if negative {
        (i64::MAX as u128) + 1
    } else {
        i64::MAX as u128
    };
    let mut magnitude = 0_u128;
    while let Some(byte @ b'0'..=b'9') = input.get(index) {
        magnitude = magnitude
            .saturating_mul(10)
            .saturating_add((byte - b'0') as u128)
            .min(limit);
        index += 1;
    }

    let value = if negative {
        if magnitude == (i64::MAX as u128) + 1 {
            i64::MIN
        } else {
            -(magnitude as i64)
        }
    } else {
        magnitude as i64
    };
    value as i32
}

pub fn parse_long(input: &[u8]) -> ParsedNumber<i64> {
    let scanned = scan_integer(input);
    if !scanned.converted {
        return ParsedNumber {
            value: 0,
            end: 0,
            range: RangeState::InRange,
        };
    }

    let limit = if scanned.negative {
        (i64::MAX as u128) + 1
    } else {
        i64::MAX as u128
    };
    if scanned.overflow || scanned.magnitude > limit {
        return ParsedNumber {
            value: if scanned.negative { i64::MIN } else { i64::MAX },
            end: scanned.end,
            range: if scanned.negative {
                RangeState::Underflow
            } else {
                RangeState::Overflow
            },
        };
    }

    let value = if scanned.negative {
        if scanned.magnitude == (i64::MAX as u128) + 1 {
            i64::MIN
        } else {
            -(scanned.magnitude as i64)
        }
    } else {
        scanned.magnitude as i64
    };
    ParsedNumber {
        value,
        end: scanned.end,
        range: RangeState::InRange,
    }
}

pub fn parse_ulong(input: &[u8]) -> ParsedNumber<u64> {
    let scanned = scan_integer(input);
    if !scanned.converted {
        return ParsedNumber {
            value: 0,
            end: 0,
            range: RangeState::InRange,
        };
    }

    if scanned.overflow || scanned.magnitude > u64::MAX as u128 {
        return ParsedNumber {
            value: u64::MAX,
            end: scanned.end,
            range: RangeState::Overflow,
        };
    }

    let magnitude = scanned.magnitude as u64;
    ParsedNumber {
        value: if scanned.negative {
            0_u64.wrapping_sub(magnitude)
        } else {
            magnitude
        },
        end: scanned.end,
        range: RangeState::InRange,
    }
}

pub fn parse_double(input: &[u8]) -> ParsedNumber<f64> {
    let mut index = 0;
    while input.get(index).is_some_and(|byte| is_c_whitespace(*byte)) {
        index += 1;
    }
    let negative = match input.get(index) {
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
    let body_start = index;

    if starts_ascii_case_insensitive(&input[index..], b"inf") {
        index += 3;
        if starts_ascii_case_insensitive(&input[index..], b"inity") {
            index += 5;
        }
        return ParsedNumber {
            value: if negative {
                f64::NEG_INFINITY
            } else {
                f64::INFINITY
            },
            end: index,
            range: RangeState::InRange,
        };
    }

    if starts_ascii_case_insensitive(&input[index..], b"nan") {
        index += 3;
        if input.get(index) == Some(&b'(') {
            let mut payload_end = index + 1;
            while input
                .get(payload_end)
                .is_some_and(|byte| byte.is_ascii_alphanumeric() || *byte == b'_')
            {
                payload_end += 1;
            }
            if input.get(payload_end) == Some(&b')') {
                index = payload_end + 1;
            }
        }
        let value = if negative { -f64::NAN } else { f64::NAN };
        return ParsedNumber {
            value,
            end: index,
            range: RangeState::InRange,
        };
    }

    if input.get(index) == Some(&b'0') && matches!(input.get(index + 1), Some(b'x' | b'X')) {
        if let Some(parsed) = parse_hex_double(input, body_start, negative) {
            return parsed;
        }
    }

    let mut cursor = index;
    let mut digits = 0_usize;
    while input.get(cursor).is_some_and(u8::is_ascii_digit) {
        cursor += 1;
        digits += 1;
    }
    if input.get(cursor) == Some(&b'.') {
        cursor += 1;
        while input.get(cursor).is_some_and(u8::is_ascii_digit) {
            cursor += 1;
            digits += 1;
        }
    }
    if digits == 0 {
        return ParsedNumber {
            value: 0.0,
            end: 0,
            range: RangeState::InRange,
        };
    }

    let significand_end = cursor;
    if matches!(input.get(cursor), Some(b'e' | b'E')) {
        let mut exponent = cursor + 1;
        if matches!(input.get(exponent), Some(b'+' | b'-')) {
            exponent += 1;
        }
        let exponent_digits = exponent;
        while input.get(exponent).is_some_and(u8::is_ascii_digit) {
            exponent += 1;
        }
        if exponent > exponent_digits {
            cursor = exponent;
        }
    }

    let mut normalized = String::new();
    if negative {
        normalized.push('-');
    }
    let body = &input[body_start..cursor];
    let exponent_at = body
        .iter()
        .position(|byte| matches!(byte, b'e' | b'E'))
        .unwrap_or(body.len());
    let mantissa = &body[..exponent_at];
    if mantissa.first() == Some(&b'.') {
        normalized.push('0');
    }
    for byte in mantissa {
        normalized.push(*byte as char);
    }
    if mantissa.last() == Some(&b'.') {
        normalized.push('0');
    }
    for byte in &body[exponent_at..] {
        normalized.push(*byte as char);
    }

    let value = match normalized.parse::<f64>() {
        Ok(value) => value,
        Err(_) => {
            debug_assert!(false, "the checked decimal grammar must be accepted by f64");
            return ParsedNumber {
                value: if negative { -0.0 } else { 0.0 },
                end: cursor,
                range: if input[body_start..significand_end]
                    .iter()
                    .any(|byte| matches!(byte, b'1'..=b'9'))
                {
                    RangeState::Underflow
                } else {
                    RangeState::InRange
                },
            };
        }
    };
    let nonzero = input[body_start..significand_end]
        .iter()
        .any(|byte| matches!(byte, b'1'..=b'9'));
    ParsedNumber {
        value,
        end: cursor,
        range: decimal_range(body, value, nonzero),
    }
}

pub fn quoted_byte(input: &[u8]) -> Option<u8> {
    match input.first() {
        Some(b'\'' | b'"') => Some(input.get(1).copied().unwrap_or(0)),
        _ => None,
    }
}

#[derive(Clone, Copy, Debug)]
struct ScannedInteger {
    magnitude: u128,
    end: usize,
    negative: bool,
    converted: bool,
    overflow: bool,
}

fn scan_integer(input: &[u8]) -> ScannedInteger {
    let mut index = 0;
    while input.get(index).is_some_and(|byte| is_c_whitespace(*byte)) {
        index += 1;
    }
    let negative = match input.get(index) {
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

    let mut base = 10_u8;
    if input.get(index) == Some(&b'0') {
        if matches!(input.get(index + 1), Some(b'x' | b'X'))
            && input
                .get(index + 2)
                .is_some_and(|byte| byte.is_ascii_hexdigit())
        {
            base = 16;
            index += 2;
        } else {
            base = 8;
        }
    }

    let digits_start = index;
    let mut magnitude = 0_u128;
    let mut overflow = false;
    while let Some(digit) = input.get(index).and_then(|byte| digit_value(*byte)) {
        if digit >= base {
            break;
        }
        match magnitude
            .checked_mul(base as u128)
            .and_then(|value| value.checked_add(digit as u128))
        {
            Some(value) => magnitude = value,
            None => {
                magnitude = u128::MAX;
                overflow = true;
            }
        }
        index += 1;
    }

    ScannedInteger {
        magnitude,
        end: index,
        negative,
        converted: index > digits_start,
        overflow,
    }
}

fn parse_hex_double(input: &[u8], body_start: usize, negative: bool) -> Option<ParsedNumber<f64>> {
    let mut index = body_start + 2;
    let mut digits = Vec::new();
    let mut fractional_digits = 0_usize;

    while let Some(digit) = input.get(index).and_then(|byte| digit_value(*byte)) {
        digits.push(digit);
        index += 1;
    }
    if input.get(index) == Some(&b'.') {
        index += 1;
        while let Some(digit) = input.get(index).and_then(|byte| digit_value(*byte)) {
            digits.push(digit);
            fractional_digits += 1;
            index += 1;
        }
    }
    if digits.is_empty() {
        return None;
    }

    let mut binary_exponent = 0_i128;
    if matches!(input.get(index), Some(b'p' | b'P')) {
        let marker = index;
        let mut exponent_index = index + 1;
        let exponent_negative = if input.get(exponent_index) == Some(&b'-') {
            exponent_index += 1;
            true
        } else {
            if input.get(exponent_index) == Some(&b'+') {
                exponent_index += 1;
            }
            false
        };
        let exponent_start = exponent_index;
        while input.get(exponent_index).is_some_and(u8::is_ascii_digit) {
            exponent_index += 1;
        }
        if exponent_index > exponent_start {
            index = exponent_index;
            let exponent = parse_decimal_exponent(&input[exponent_start..exponent_index]);
            binary_exponent = if exponent_negative {
                -exponent
            } else {
                exponent
            };
        } else {
            index = marker;
        }
    }

    let (value, range) = convert_hex_double(&digits, fractional_digits, binary_exponent, negative);
    Some(ParsedNumber {
        value,
        end: index,
        range,
    })
}

fn decimal_range(input: &[u8], value: f64, nonzero_significand: bool) -> RangeState {
    if value.is_infinite() {
        RangeState::Overflow
    } else if nonzero_significand && decimal_is_tiny_and_inexact(input, value.abs()) {
        RangeState::Underflow
    } else {
        RangeState::InRange
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct DecimalMagnitude {
    digits: Vec<u8>,
    power10: i128,
}

fn decimal_is_tiny_and_inexact(input: &[u8], rounded: f64) -> bool {
    let Some(source) = decimal_magnitude(input) else {
        return false;
    };
    if compare_decimal_magnitudes(&source, minimum_normal_decimal()) != Ordering::Less {
        return false;
    }
    if rounded == 0.0 {
        return true;
    }

    // Every binary64 value at this magnitude has a terminating decimal
    // expansion with at most 1074 fractional digits.
    let exact = format!("{rounded:.1074}");
    let exact =
        decimal_magnitude(exact.as_bytes()).expect("a nonzero finite f64 has a decimal magnitude");
    source != exact
}

fn minimum_normal_decimal() -> &'static DecimalMagnitude {
    static MINIMUM: OnceLock<DecimalMagnitude> = OnceLock::new();
    MINIMUM.get_or_init(|| {
        let exact = format!("{:.1074}", f64::MIN_POSITIVE);
        decimal_magnitude(exact.as_bytes()).expect("minimum normal is nonzero")
    })
}

fn decimal_magnitude(input: &[u8]) -> Option<DecimalMagnitude> {
    let exponent_at = input.iter().position(|byte| matches!(byte, b'e' | b'E'));
    let mantissa_end = exponent_at.unwrap_or(input.len());
    let exponent = exponent_at
        .map(|index| parse_signed_decimal_exponent(&input[index + 1..]))
        .unwrap_or(0);

    let mut digits = Vec::with_capacity(mantissa_end);
    let mut fractional_digits = 0_usize;
    let mut after_point = false;
    for &byte in &input[..mantissa_end] {
        match byte {
            b'.' => after_point = true,
            b'0'..=b'9' => {
                digits.push(byte);
                if after_point {
                    fractional_digits += 1;
                }
            }
            _ => {}
        }
    }

    let first_nonzero = digits.iter().position(|byte| *byte != b'0')?;
    digits.drain(..first_nonzero);
    let trailing_zeros = digits
        .iter()
        .rev()
        .take_while(|byte| **byte == b'0')
        .count();
    digits.truncate(digits.len() - trailing_zeros);
    let power10 = exponent
        .saturating_sub(fractional_digits as i128)
        .saturating_add(trailing_zeros as i128);
    Some(DecimalMagnitude { digits, power10 })
}

fn compare_decimal_magnitudes(left: &DecimalMagnitude, right: &DecimalMagnitude) -> Ordering {
    let left_order = left.power10.saturating_add(left.digits.len() as i128);
    let right_order = right.power10.saturating_add(right.digits.len() as i128);
    match left_order.cmp(&right_order) {
        Ordering::Equal => {
            let width = left.digits.len().max(right.digits.len());
            for index in 0..width {
                let left_digit = left.digits.get(index).copied().unwrap_or(b'0');
                let right_digit = right.digits.get(index).copied().unwrap_or(b'0');
                match left_digit.cmp(&right_digit) {
                    Ordering::Equal => {}
                    ordering => return ordering,
                }
            }
            Ordering::Equal
        }
        ordering => ordering,
    }
}

fn parse_signed_decimal_exponent(input: &[u8]) -> i128 {
    let (negative, digits) = match input.first() {
        Some(b'-') => (true, &input[1..]),
        Some(b'+') => (false, &input[1..]),
        _ => (false, input),
    };
    let magnitude = parse_decimal_exponent(digits);
    if negative {
        -magnitude
    } else {
        magnitude
    }
}

fn parse_decimal_exponent(input: &[u8]) -> i128 {
    input.iter().fold(0_i128, |value, byte| {
        value
            .saturating_mul(10)
            .saturating_add((byte - b'0') as i128)
    })
}

struct HexSignificand<'a> {
    digits: &'a [u8],
    first: usize,
    first_width: usize,
    bit_len: usize,
}

impl<'a> HexSignificand<'a> {
    fn new(digits: &'a [u8]) -> Option<Self> {
        let first = digits.iter().position(|digit| *digit != 0)?;
        let first_width = (u8::BITS - digits[first].leading_zeros()) as usize;
        let bit_len = first_width + (digits.len() - first - 1).saturating_mul(4);
        Some(Self {
            digits,
            first,
            first_width,
            bit_len,
        })
    }

    fn bit(&self, index: usize) -> bool {
        if index < self.first_width {
            let shift = self.first_width - index - 1;
            return (self.digits[self.first] >> shift) & 1 != 0;
        }
        let remainder = index - self.first_width;
        let digit = self.digits[self.first + 1 + remainder / 4];
        (digit >> (3 - remainder % 4)) & 1 != 0
    }

    fn prefix(&self, count: usize) -> u64 {
        let mut value = 0_u64;
        for index in 0..count {
            value = (value << 1) | u64::from(self.bit(index));
        }
        value
    }

    fn any_from(&self, start: usize) -> bool {
        (start..self.bit_len).any(|index| self.bit(index))
    }
}

fn convert_hex_double(
    digits: &[u8],
    fractional_digits: usize,
    binary_exponent: i128,
    negative: bool,
) -> (f64, RangeState) {
    let sign = if negative { 1_u64 << 63 } else { 0 };
    let Some(significand) = HexSignificand::new(digits) else {
        return (f64::from_bits(sign), RangeState::InRange);
    };
    let scale = binary_exponent.saturating_sub((fractional_digits as i128).saturating_mul(4));
    let mut exponent = (significand.bit_len as i128)
        .saturating_sub(1)
        .saturating_add(scale);

    if exponent > 1023 {
        return (
            f64::from_bits(sign | (0x7ff_u64 << 52)),
            RangeState::Overflow,
        );
    }

    if exponent >= -1022 {
        let mut rounded = round_normal_significand(&significand);
        if rounded == 1_u64 << 53 {
            rounded = 1_u64 << 52;
            exponent += 1;
        }
        if exponent > 1023 {
            return (
                f64::from_bits(sign | (0x7ff_u64 << 52)),
                RangeState::Overflow,
            );
        }
        let exponent_bits = (exponent + 1023) as u64;
        let fraction = rounded & ((1_u64 << 52) - 1);
        return (
            f64::from_bits(sign | (exponent_bits << 52) | fraction),
            RangeState::InRange,
        );
    }

    let (rounded, inexact) = round_subnormal_significand(&significand, scale.saturating_add(1074));
    let bits = if rounded >= 1_u64 << 52 {
        sign | (1_u64 << 52)
    } else {
        sign | rounded
    };
    (
        f64::from_bits(bits),
        if inexact {
            RangeState::Underflow
        } else {
            RangeState::InRange
        },
    )
}

fn round_normal_significand(significand: &HexSignificand<'_>) -> u64 {
    if significand.bit_len <= 53 {
        return significand.prefix(significand.bit_len) << (53 - significand.bit_len);
    }

    let retained = significand.prefix(53);
    let guard = significand.bit(53);
    let sticky = significand.any_from(54);
    retained + u64::from(guard && (sticky || retained & 1 != 0))
}

fn round_subnormal_significand(significand: &HexSignificand<'_>, shift: i128) -> (u64, bool) {
    if shift >= 0 {
        let shift = shift as usize;
        debug_assert!(significand.bit_len + shift <= 52);
        return (significand.prefix(significand.bit_len) << shift, false);
    }

    let right = shift.saturating_neg();
    let bit_len = significand.bit_len as i128;
    let retained_bits = bit_len.saturating_sub(right).max(0) as usize;
    let retained = significand.prefix(retained_bits);
    let inexact = significand.any_from(retained_bits);
    let can_reach_half = right <= bit_len;
    let guard = can_reach_half && significand.bit(retained_bits);
    let sticky = can_reach_half && significand.any_from(retained_bits + 1);
    (
        retained + u64::from(guard && (sticky || retained & 1 != 0)),
        inexact,
    )
}

fn starts_ascii_case_insensitive(input: &[u8], expected: &[u8]) -> bool {
    input.len() >= expected.len()
        && input[..expected.len()]
            .iter()
            .zip(expected)
            .all(|(actual, expected)| actual.eq_ignore_ascii_case(expected))
}

fn digit_value(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

fn is_c_whitespace(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | 0x0b | 0x0c | b'\r')
}

#[cfg(test)]
mod tests {
    use super::{
        atoi, parse_double, parse_long, parse_ulong, quoted_byte, ParsedNumber, RangeState,
    };
    use crate::printf::{MockOutput, PrintfState};

    #[test]
    fn getint_eligibility_and_consumption() {
        fn assert_getint(input: &[u8], expected: i32, consumed: bool) {
            let operands = vec![input.to_vec(), b"next".to_vec()];
            let mut output = MockOutput::default();
            let mut state = PrintfState::new(b"printf", &operands, &mut output);

            assert_eq!(state.getint(), expected, "value for {input:?}");
            assert_eq!(
                state.getstr(),
                if consumed { b"next" } else { input },
                "cursor for {input:?}"
            );
        }

        let operands = Vec::new();
        let mut output = MockOutput::default();
        let mut state = PrintfState::new(b"printf", &operands, &mut output);
        assert_eq!(state.getint(), 0);
        assert_eq!(state.getstr(), b"");

        for (input, expected) in [
            (b"".as_slice(), 0),
            (b"+".as_slice(), 0),
            (b"-".as_slice(), 0),
            (b".".as_slice(), 0),
            (b".75".as_slice(), 0),
            (b"+12tail".as_slice(), 12),
            (b"-12tail".as_slice(), -12),
            (b"012x".as_slice(), 12),
            (b"4294967297".as_slice(), 1),
        ] {
            assert_getint(input, expected, true);
        }
        for input in [
            b"oops".as_slice(),
            b"_12".as_slice(),
            b" 12".as_slice(),
            b"\t12".as_slice(),
            b"\xff12".as_slice(),
        ] {
            assert_getint(input, 0, false);
        }

        assert_eq!(atoi(b" \t-42tail"), -42);
        assert_eq!(atoi(b"2147483648"), i32::MIN);
        assert_eq!(atoi(b"9223372036854775808"), -1);
        assert_eq!(atoi(b"-9223372036854775809"), 0);
    }

    #[test]
    fn integer_prefixes_limits_and_ranges() {
        let signed_cases: &[(&[u8], i64, usize, RangeState)] = &[
            (b"42", 42, 2, RangeState::InRange),
            (b"-42", -42, 3, RangeState::InRange),
            (b" \t\n\x0b\x0c\r+42", 42, 9, RangeState::InRange),
            (b"077", 0o77, 3, RangeState::InRange),
            (b"-010", -8, 4, RangeState::InRange),
            (b"0x2a", 0x2a, 4, RangeState::InRange),
            (b"+0XFF", 0xff, 5, RangeState::InRange),
            (b"9223372036854775807", i64::MAX, 19, RangeState::InRange),
            (b"-9223372036854775808", i64::MIN, 20, RangeState::InRange),
            (b"9223372036854775808", i64::MAX, 19, RangeState::Overflow),
            (b"-9223372036854775809", i64::MIN, 20, RangeState::Underflow),
            (b"0x7fffffffffffffff", i64::MAX, 18, RangeState::InRange),
            (b"0x8000000000000000", i64::MAX, 18, RangeState::Overflow),
            (b"-0x8000000000000000", i64::MIN, 19, RangeState::InRange),
            (b"-0x8000000000000001", i64::MIN, 19, RangeState::Underflow),
            (
                b"340282366920938463463374607431768211456",
                i64::MAX,
                39,
                RangeState::Overflow,
            ),
        ];
        for &(input, value, end, range) in signed_cases {
            assert_eq!(
                parse_long(input),
                ParsedNumber { value, end, range },
                "signed parse for {input:?}"
            );
        }

        let unsigned_cases: &[(&[u8], u64, usize, RangeState)] = &[
            (b"42", 42, 2, RangeState::InRange),
            (b"077", 0o77, 3, RangeState::InRange),
            (b"0xFF", 0xff, 4, RangeState::InRange),
            (b"18446744073709551615", u64::MAX, 20, RangeState::InRange),
            (b"18446744073709551616", u64::MAX, 20, RangeState::Overflow),
            (b"-1", u64::MAX, 2, RangeState::InRange),
            (b"-2", u64::MAX - 1, 2, RangeState::InRange),
            (b"-18446744073709551615", 1, 21, RangeState::InRange),
            (b"-18446744073709551616", u64::MAX, 21, RangeState::Overflow),
            (b"0xffffffffffffffff", u64::MAX, 18, RangeState::InRange),
            (b"0x10000000000000000", u64::MAX, 19, RangeState::Overflow),
            (
                b"340282366920938463463374607431768211456",
                u64::MAX,
                39,
                RangeState::Overflow,
            ),
        ];
        for &(input, value, end, range) in unsigned_cases {
            assert_eq!(
                parse_ulong(input),
                ParsedNumber { value, end, range },
                "unsigned parse for {input:?}"
            );
        }
    }

    #[test]
    fn integer_partial_and_quoted_inputs() {
        let cases: &[(&[u8], i64, usize)] = &[
            (b"", 0, 0),
            (b" \t", 0, 0),
            (b"+", 0, 0),
            (b"-", 0, 0),
            (b"word", 0, 0),
            (b".5", 0, 0),
            (b"123tail", 123, 3),
            (b" \t-0779", -0o77, 6),
            (b"0x", 0, 1),
            (b"0Xg", 0, 1),
            (b"0x+1", 0, 1),
            (b"0b101", 0, 1),
            (b"08", 0, 1),
            (b"-0x2Ag", -0x2a, 5),
            (b"  +x", 0, 0),
        ];
        for &(input, value, end) in cases {
            assert_eq!(
                parse_long(input),
                ParsedNumber {
                    value,
                    end,
                    range: RangeState::InRange,
                },
                "signed prefix for {input:?}"
            );
            assert_eq!(parse_ulong(input).end, end, "unsigned end for {input:?}");
        }

        let quoted_cases: &[(&[u8], Option<u8>)] = &[
            (b"'Aignored", Some(b'A')),
            (b"\"Zignored", Some(b'Z')),
            (b"'", Some(0)),
            (b"\"", Some(0)),
            (b"''", Some(b'\'')),
            (b"\"\"", Some(b'"')),
            (b"'\xfftail", Some(0xff)),
            (b"", None),
            (b"A", None),
        ];
        for &(input, expected) in quoted_cases {
            assert_eq!(quoted_byte(input), expected, "quoted byte for {input:?}");
        }
    }

    #[test]
    fn float_prefixes_special_values_and_ranges() {
        let cases: &[(&[u8], u64, usize, RangeState)] = &[
            (b"1.25", 1.25_f64.to_bits(), 4, RangeState::InRange),
            (b"-.5", (-0.5_f64).to_bits(), 3, RangeState::InRange),
            (
                b" \t\n\x0b\x0c\r+1.5",
                1.5_f64.to_bits(),
                10,
                RangeState::InRange,
            ),
            (b"-0", (-0.0_f64).to_bits(), 2, RangeState::InRange),
            (b"-0.0e99", (-0.0_f64).to_bits(), 7, RangeState::InRange),
            (b"1e", 1.0_f64.to_bits(), 1, RangeState::InRange),
            (b"1e+", 1.0_f64.to_bits(), 1, RangeState::InRange),
            (b"1e-", 1.0_f64.to_bits(), 1, RangeState::InRange),
            (b".75tail", 0.75_f64.to_bits(), 3, RangeState::InRange),
            (b"0x1.8p+2", 6.0_f64.to_bits(), 8, RangeState::InRange),
            (
                b"-0X.8P+1rest",
                (-1.0_f64).to_bits(),
                8,
                RangeState::InRange,
            ),
            (b"0x1p+", 1.0_f64.to_bits(), 3, RangeState::InRange),
            (b"0x", 0.0_f64.to_bits(), 1, RangeState::InRange),
            (b"0x.", 0.0_f64.to_bits(), 1, RangeState::InRange),
            (b"  +", 0.0_f64.to_bits(), 0, RangeState::InRange),
            (b".", 0.0_f64.to_bits(), 0, RangeState::InRange),
        ];
        for &(input, bits, end, range) in cases {
            let parsed = parse_double(input);
            assert_eq!(parsed.value.to_bits(), bits, "value for {input:?}");
            assert_eq!(parsed.end, end, "end for {input:?}");
            assert_eq!(parsed.range, range, "range for {input:?}");
        }

        for (input, value, end) in [
            (b"inf".as_slice(), f64::INFINITY, 3),
            (b"-INFINITY".as_slice(), f64::NEG_INFINITY, 9),
            (b"infinity-tail".as_slice(), f64::INFINITY, 8),
            (b"infini".as_slice(), f64::INFINITY, 3),
        ] {
            assert_eq!(
                parse_double(input),
                ParsedNumber {
                    value,
                    end,
                    range: RangeState::InRange,
                },
                "infinity for {input:?}"
            );
        }

        for (input, end, negative) in [
            (b"nan".as_slice(), 3, false),
            (b"nan()".as_slice(), 5, false),
            (b"NAN(payload)tail".as_slice(), 12, false),
            (b"nan(_)".as_slice(), 6, false),
            (b"nan(pay-load)".as_slice(), 3, false),
            (b"-nan(123)".as_slice(), 9, true),
        ] {
            let parsed = parse_double(input);
            assert!(parsed.value.is_nan(), "NaN value for {input:?}");
            assert_eq!(
                parsed.value.is_sign_negative(),
                negative,
                "NaN sign for {input:?}"
            );
            assert_eq!(parsed.end, end, "NaN end for {input:?}");
            assert_eq!(parsed.range, RangeState::InRange, "NaN range");
        }
    }

    #[test]
    fn float_binary_boundaries_and_trailing_input() {
        let max_decimal = b"1.7976931348623157e308";
        assert_eq!(
            parse_double(max_decimal),
            ParsedNumber {
                value: f64::MAX,
                end: max_decimal.len(),
                range: RangeState::InRange,
            }
        );
        let rounded_max = b"1.7976931348623158e308";
        assert_eq!(
            parse_double(rounded_max),
            ParsedNumber {
                value: f64::MAX,
                end: rounded_max.len(),
                range: RangeState::InRange,
            }
        );

        for input in [b"1e309".as_slice(), b"-1e999999999999999999999"] {
            let parsed = parse_double(input);
            assert!(parsed.value.is_infinite(), "{input:?}");
            assert_eq!(
                parsed.value.is_sign_negative(),
                input.first() == Some(&b'-')
            );
            assert_eq!(parsed.end, input.len());
            assert_eq!(parsed.range, RangeState::Overflow);
        }

        for (input, bits) in [(b"5e-324".as_slice(), 1_u64), (b"1e-324".as_slice(), 0_u64)] {
            let parsed = parse_double(input);
            assert_eq!(parsed.value.to_bits(), bits, "{input:?}");
            assert_eq!(parsed.end, input.len());
            assert_eq!(parsed.range, RangeState::Underflow);
        }

        let exact_minimum = format!("{:.1074}", f64::from_bits(1));
        assert_eq!(
            parse_double(exact_minimum.as_bytes()),
            ParsedNumber {
                value: f64::from_bits(1),
                end: exact_minimum.len(),
                range: RangeState::InRange,
            }
        );

        let hex_cases: &[(&[u8], u64, RangeState)] = &[
            (
                b"0x1.fffffffffffffp1023",
                f64::MAX.to_bits(),
                RangeState::InRange,
            ),
            (
                b"0x1.fffffffffffff7p1023",
                f64::MAX.to_bits(),
                RangeState::InRange,
            ),
            (
                b"0x1.fffffffffffff8p1023",
                f64::INFINITY.to_bits(),
                RangeState::Overflow,
            ),
            (b"0x1p-1074", 1, RangeState::InRange),
            (
                b"0x0.fffffffffffffp-1022",
                (1_u64 << 52) - 1,
                RangeState::InRange,
            ),
            (b"0x1p-1075", 0, RangeState::Underflow),
            (b"0x1.0000000000001p-1075", 1, RangeState::Underflow),
            (b"0x3p-1075", 2, RangeState::Underflow),
            (
                b"0x0.fffffffffffff8p-1022",
                1_u64 << 52,
                RangeState::Underflow,
            ),
            (
                b"0x1.00000000000008p0",
                1.0_f64.to_bits(),
                RangeState::InRange,
            ),
            (
                b"0x1.00000000000018p0",
                1.0_f64.to_bits() + 2,
                RangeState::InRange,
            ),
        ];
        for &(input, bits, range) in hex_cases {
            let parsed = parse_double(input);
            assert_eq!(parsed.value.to_bits(), bits, "value for {input:?}");
            assert_eq!(parsed.end, input.len(), "end for {input:?}");
            assert_eq!(parsed.range, range, "range for {input:?}");
        }

        let overflow_with_tail = parse_double(b"1e309tail");
        assert!(overflow_with_tail.value.is_infinite());
        assert_eq!(overflow_with_tail.end, 5);
        assert_eq!(overflow_with_tail.range, RangeState::Overflow);

        let underflow_with_tail = parse_double(b"0x1p-1075tail");
        assert_eq!(underflow_with_tail.value.to_bits(), 0);
        assert_eq!(underflow_with_tail.end, 9);
        assert_eq!(underflow_with_tail.range, RangeState::Underflow);
    }
}
