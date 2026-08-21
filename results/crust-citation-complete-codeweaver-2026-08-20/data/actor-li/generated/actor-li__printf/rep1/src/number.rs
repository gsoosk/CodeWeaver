#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum RangeState {
    InRange,
    Underflow,
    Overflow,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub(crate) struct Parsed<T> {
    pub(crate) value: T,
    pub(crate) end: usize,
    pub(crate) converted: bool,
    pub(crate) range: RangeState,
}

pub(crate) const GETINT_GATE: &[u8] = b"+-.0123456789";

pub(crate) fn getint_consumes(bytes: &[u8]) -> bool {
    bytes
        .first()
        .is_none_or(|byte| *byte == 0 || GETINT_GATE.contains(byte))
}

pub(crate) fn isodigit(byte: u8) -> bool {
    matches!(byte, b'0'..=b'7')
}

pub(crate) fn octtobin(byte: u8) -> u8 {
    byte - b'0'
}

pub(crate) fn hextobin(byte: u8) -> u8 {
    match byte {
        b'A'..=b'F' => byte - b'A' + 10,
        b'a'..=b'f' => byte - b'a' + 10,
        _ => byte - b'0',
    }
}

pub(crate) fn parse_getint(bytes: &[u8]) -> i32 {
    let mut index = 0;
    let negative = match bytes.first() {
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
    let mut value = 0_u32;
    while let Some(byte @ b'0'..=b'9') = bytes.get(index) {
        value = value.wrapping_mul(10).wrapping_add(u32::from(*byte - b'0'));
        index += 1;
    }
    if negative {
        0_u32.wrapping_sub(value) as i32
    } else {
        value as i32
    }
}

pub(crate) fn parse_long(bytes: &[u8]) -> Parsed<i64> {
    let prefix = parse_integer_prefix(bytes);
    if !prefix.converted {
        return Parsed {
            value: 0,
            end: 0,
            converted: false,
            range: RangeState::InRange,
        };
    }

    let limit = if prefix.negative {
        (i64::MAX as u128) + 1
    } else {
        i64::MAX as u128
    };
    if prefix.overflowed || prefix.magnitude > limit {
        return Parsed {
            value: if prefix.negative { i64::MIN } else { i64::MAX },
            end: prefix.end,
            converted: true,
            range: if prefix.negative {
                RangeState::Underflow
            } else {
                RangeState::Overflow
            },
        };
    }

    let value = if prefix.negative {
        if prefix.magnitude == (1_u128 << 63) {
            i64::MIN
        } else {
            -(prefix.magnitude as i64)
        }
    } else {
        prefix.magnitude as i64
    };
    Parsed {
        value,
        end: prefix.end,
        converted: true,
        range: RangeState::InRange,
    }
}

pub(crate) fn parse_ulong(bytes: &[u8]) -> Parsed<u64> {
    let prefix = parse_integer_prefix(bytes);
    if !prefix.converted {
        return Parsed {
            value: 0,
            end: 0,
            converted: false,
            range: RangeState::InRange,
        };
    }

    if prefix.overflowed || prefix.magnitude > u64::MAX as u128 {
        return Parsed {
            value: u64::MAX,
            end: prefix.end,
            converted: true,
            range: RangeState::Overflow,
        };
    }

    let magnitude = prefix.magnitude as u64;
    Parsed {
        value: if prefix.negative {
            magnitude.wrapping_neg()
        } else {
            magnitude
        },
        end: prefix.end,
        converted: true,
        range: RangeState::InRange,
    }
}

pub(crate) fn parse_double(bytes: &[u8]) -> Parsed<f64> {
    if let Some(parsed) = parse_special_float(bytes) {
        return parsed;
    }

    let hex = parse_hex_float(bytes);
    if hex.converted {
        return hex;
    }
    parse_decimal_float(bytes)
}

pub(crate) fn quote_value(bytes: &[u8]) -> Option<u8> {
    match bytes.first() {
        Some(b'\'') | Some(b'"') => Some(bytes.get(1).copied().unwrap_or(0)),
        _ => None,
    }
}

pub(crate) fn parse_decimal_float(bytes: &[u8]) -> Parsed<f64> {
    let start = skip_ascii_whitespace(bytes);
    let mut index = start;
    if matches!(bytes.get(index), Some(b'+') | Some(b'-')) {
        index += 1;
    }
    let numeric_start = start;
    let integer_start = index;
    let mut significand_nonzero = false;
    while matches!(bytes.get(index), Some(b'0'..=b'9')) {
        significand_nonzero |= bytes[index] != b'0';
        index += 1;
    }
    let mut digit_count = index - integer_start;
    if bytes.get(index) == Some(&b'.') {
        index += 1;
        let fraction_start = index;
        while matches!(bytes.get(index), Some(b'0'..=b'9')) {
            significand_nonzero |= bytes[index] != b'0';
            index += 1;
        }
        digit_count += index - fraction_start;
    }
    if digit_count == 0 {
        return Parsed {
            value: 0.0,
            end: 0,
            converted: false,
            range: RangeState::InRange,
        };
    }

    if matches!(bytes.get(index), Some(b'e') | Some(b'E')) {
        let exponent_marker = index;
        index += 1;
        if matches!(bytes.get(index), Some(b'+') | Some(b'-')) {
            index += 1;
        }
        let exponent_start = index;
        while matches!(bytes.get(index), Some(b'0'..=b'9')) {
            index += 1;
        }
        if exponent_start == index {
            index = exponent_marker;
        }
    }

    let token = std::str::from_utf8(&bytes[numeric_start..index])
        .expect("the decimal scanner accepts only ASCII");
    let value = token
        .parse::<f64>()
        .expect("a validated decimal floating token must parse");
    let range = decimal_range(token.as_bytes(), value, significand_nonzero);
    Parsed {
        value,
        end: index,
        converted: true,
        range,
    }
}

pub(crate) fn parse_hex_float(bytes: &[u8]) -> Parsed<f64> {
    let start = skip_ascii_whitespace(bytes);
    let mut index = start;
    let negative = match bytes.get(index) {
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
    if bytes.get(index) != Some(&b'0') || !matches!(bytes.get(index + 1), Some(b'x') | Some(b'X')) {
        return unconverted_float();
    }
    index += 2;

    let mut digits = Vec::new();
    while let Some(byte) = bytes
        .get(index)
        .copied()
        .filter(|byte| byte.is_ascii_hexdigit())
    {
        digits.push(hextobin(byte));
        index += 1;
    }
    let mut fraction_digits = 0_usize;
    if bytes.get(index) == Some(&b'.') {
        index += 1;
        while let Some(byte) = bytes
            .get(index)
            .copied()
            .filter(|byte| byte.is_ascii_hexdigit())
        {
            digits.push(hextobin(byte));
            index += 1;
            fraction_digits += 1;
        }
    }
    if digits.is_empty() {
        return unconverted_float();
    }

    let mut binary_exponent = 0_i128;
    if matches!(bytes.get(index), Some(b'p') | Some(b'P')) {
        let exponent_marker = index;
        if let Some((exponent, exponent_index)) = parse_signed_decimal_exponent(bytes, index + 1) {
            binary_exponent = exponent;
            index = exponent_index;
        } else {
            index = exponent_marker;
        }
    }

    let (value, range) =
        convert_hex_significand(&digits, fraction_digits, binary_exponent, negative);
    Parsed {
        value,
        end: index,
        converted: true,
        range,
    }
}

pub(crate) fn parse_special_float(bytes: &[u8]) -> Option<Parsed<f64>> {
    let start = skip_ascii_whitespace(bytes);
    let mut index = start;
    let negative = match bytes.get(index) {
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

    if has_ascii_prefix_case_insensitive(&bytes[index..], b"inf") {
        index += 3;
        if has_ascii_prefix_case_insensitive(&bytes[index..], b"inity") {
            index += 5;
        }
        return Some(Parsed {
            value: if negative {
                f64::NEG_INFINITY
            } else {
                f64::INFINITY
            },
            end: index,
            converted: true,
            range: RangeState::InRange,
        });
    }

    if !has_ascii_prefix_case_insensitive(&bytes[index..], b"nan") {
        return None;
    }
    index += 3;
    let mut payload = None;
    if bytes.get(index) == Some(&b'(') {
        if let Some(close_offset) = bytes[index + 1..].iter().position(|byte| *byte == b')') {
            let candidate = &bytes[index + 1..index + 1 + close_offset];
            if candidate
                .iter()
                .all(|byte| byte.is_ascii_alphanumeric() || *byte == b'_')
            {
                payload = Some(candidate);
                index += close_offset + 2;
            }
        }
    }
    let payload_bits = payload.and_then(nan_payload).unwrap_or(0) & ((1_u64 << 52) - 1);
    let sign = if negative { 1_u64 << 63 } else { 0 };
    let value = f64::from_bits(sign | 0x7ff8_0000_0000_0000 | payload_bits);
    Some(Parsed {
        value,
        end: index,
        converted: true,
        range: RangeState::InRange,
    })
}

const F64_SIGN_BIT: u64 = 1_u64 << 63;
const F64_INFINITY_BITS: u64 = 0x7ff0_0000_0000_0000;
const F64_MIN_NORMAL_BITS: u64 = 1_u64 << 52;

fn signed_zero(negative: bool) -> f64 {
    f64::from_bits(if negative { F64_SIGN_BIT } else { 0 })
}

fn decimal_range(token: &[u8], value: f64, significand_nonzero: bool) -> RangeState {
    if !significand_nonzero {
        return RangeState::InRange;
    }
    if value.is_infinite() {
        return RangeState::Overflow;
    }

    let magnitude_bits = value.to_bits() & !F64_SIGN_BIT;
    if magnitude_bits == 0 {
        return RangeState::Underflow;
    }

    let input =
        canonical_decimal(token).expect("a nonzero decimal token has a canonical representation");
    if magnitude_bits < F64_MIN_NORMAL_BITS {
        let exact = canonical_binary_fraction(magnitude_bits, 1074);
        return if input == exact {
            RangeState::InRange
        } else {
            RangeState::Underflow
        };
    }

    if magnitude_bits == F64_MIN_NORMAL_BITS {
        // glibc's round-to-nearest path stops reporting underflow once the
        // exact magnitude reaches one quarter of an ulp below DBL_MIN.
        let no_underflow_threshold = canonical_binary_fraction((1_u64 << 54) - 1, 1076);
        if compare_canonical_decimal(&input, &no_underflow_threshold).is_lt() {
            return RangeState::Underflow;
        }
    }

    RangeState::InRange
}

#[derive(Debug, PartialEq, Eq)]
struct CanonicalDecimal {
    digits: Vec<u8>,
    power: i128,
}

fn canonical_decimal(token: &[u8]) -> Option<CanonicalDecimal> {
    let mut index = usize::from(matches!(token.first(), Some(b'+') | Some(b'-')));
    let mut digits = Vec::with_capacity(token.len());
    let mut fractional_digits = 0_i128;
    let mut in_fraction = false;

    while let Some(byte) = token.get(index) {
        match byte {
            b'0'..=b'9' => {
                digits.push(*byte);
                if in_fraction {
                    fractional_digits = fractional_digits.saturating_add(1);
                }
                index += 1;
            }
            b'.' => {
                in_fraction = true;
                index += 1;
            }
            b'e' | b'E' => break,
            _ => unreachable!("decimal canonicalization receives a validated token"),
        }
    }

    let exponent = if index < token.len() {
        parse_signed_decimal_exponent(token, index + 1)
            .expect("the decimal scanner retains only complete exponents")
            .0
    } else {
        0
    };
    let first = digits.iter().position(|digit| *digit != b'0')?;
    let mut last = digits.len();
    while digits.get(last.wrapping_sub(1)) == Some(&b'0') {
        last -= 1;
    }
    let trailing_zeros = (digits.len() - last) as i128;
    Some(CanonicalDecimal {
        digits: digits[first..last].to_vec(),
        power: exponent
            .saturating_sub(fractional_digits)
            .saturating_add(trailing_zeros),
    })
}

fn canonical_binary_fraction(coefficient: u64, denominator_power: usize) -> CanonicalDecimal {
    debug_assert_ne!(coefficient, 0);
    let mut coefficient = coefficient;
    let mut reversed_digits = Vec::new();
    while coefficient != 0 {
        reversed_digits.push((coefficient % 10) as u8);
        coefficient /= 10;
    }

    for _ in 0..denominator_power {
        let mut carry = 0_u8;
        for digit in &mut reversed_digits {
            let product = *digit * 5 + carry;
            *digit = product % 10;
            carry = product / 10;
        }
        while carry != 0 {
            reversed_digits.push(carry % 10);
            carry /= 10;
        }
    }

    let mut digits: Vec<u8> = reversed_digits
        .into_iter()
        .rev()
        .map(|digit| digit + b'0')
        .collect();
    let mut power = -(denominator_power as i128);
    while digits.last() == Some(&b'0') {
        digits.pop();
        power += 1;
    }
    CanonicalDecimal { digits, power }
}

fn compare_canonical_decimal(
    left: &CanonicalDecimal,
    right: &CanonicalDecimal,
) -> std::cmp::Ordering {
    let left_order = left.digits.len() as i128 + left.power;
    let right_order = right.digits.len() as i128 + right.power;
    match left_order.cmp(&right_order) {
        std::cmp::Ordering::Equal => {}
        ordering => return ordering,
    }

    let compared_digits = left.digits.len().max(right.digits.len());
    for index in 0..compared_digits {
        let left_digit = left.digits.get(index).copied().unwrap_or(b'0');
        let right_digit = right.digits.get(index).copied().unwrap_or(b'0');
        match left_digit.cmp(&right_digit) {
            std::cmp::Ordering::Equal => {}
            ordering => return ordering,
        }
    }
    std::cmp::Ordering::Equal
}

fn parse_signed_decimal_exponent(bytes: &[u8], mut index: usize) -> Option<(i128, usize)> {
    let negative = match bytes.get(index) {
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
    let digit_start = index;
    let limit = if negative {
        1_u128 << 127
    } else {
        i128::MAX as u128
    };
    let mut magnitude = 0_u128;
    while let Some(byte @ b'0'..=b'9') = bytes.get(index) {
        magnitude = magnitude
            .saturating_mul(10)
            .saturating_add(u128::from(*byte - b'0'))
            .min(limit);
        index += 1;
    }
    if index == digit_start {
        return None;
    }

    let exponent = if negative {
        if magnitude == 1_u128 << 127 {
            i128::MIN
        } else {
            -(magnitude as i128)
        }
    } else {
        magnitude as i128
    };
    Some((exponent, index))
}

fn nan_payload(payload: &[u8]) -> Option<u64> {
    if payload.is_empty() {
        return None;
    }
    let parsed = parse_ulong(payload);
    (parsed.converted && parsed.end == payload.len()).then_some(parsed.value)
}

fn convert_hex_significand(
    digits: &[u8],
    fraction_digits: usize,
    binary_exponent: i128,
    negative: bool,
) -> (f64, RangeState) {
    let Some(first_nonzero) = digits.iter().position(|digit| *digit != 0) else {
        return (signed_zero(negative), RangeState::InRange);
    };
    let bits = HexBits::new(&digits[first_nonzero..]);
    let scale = binary_exponent.saturating_sub((fraction_digits as i128).saturating_mul(4));
    let mut highest_exponent = scale.saturating_add(bits.bit_len as i128 - 1);
    let sign = if negative { F64_SIGN_BIT } else { 0 };

    if highest_exponent > 1023 {
        return (
            f64::from_bits(sign | F64_INFINITY_BITS),
            RangeState::Overflow,
        );
    }

    if highest_exponent >= -1022 {
        let mut significand = if bits.bit_len > 53 {
            bits.round_after_right_shift(bits.bit_len - 53).value
        } else {
            bits.extract(0, bits.bit_len) << (53 - bits.bit_len)
        };
        if significand == 1_u64 << 53 {
            significand >>= 1;
            highest_exponent += 1;
            if highest_exponent > 1023 {
                return (
                    f64::from_bits(sign | F64_INFINITY_BITS),
                    RangeState::Overflow,
                );
            }
        }

        let exponent_bits = (highest_exponent + 1023) as u64;
        let fraction_bits = significand - (1_u64 << 52);
        return (
            f64::from_bits(sign | (exponent_bits << 52) | fraction_bits),
            RangeState::InRange,
        );
    }

    let quantum_shift = scale.saturating_add(1074);
    let rounded = if quantum_shift >= 0 {
        let left_shift = usize::try_from(quantum_shift).expect("a subnormal left shift fits usize");
        debug_assert!(bits.bit_len + left_shift <= 52);
        RoundedBits {
            value: bits.extract(0, bits.bit_len) << left_shift,
            discarded: false,
            remainder_at_least_three_quarters: false,
        }
    } else {
        let right_shift = quantum_shift
            .checked_neg()
            .and_then(|shift| usize::try_from(shift).ok());
        match right_shift {
            Some(shift) => bits.round_after_right_shift(shift),
            None => RoundedBits {
                value: 0,
                discarded: true,
                remainder_at_least_three_quarters: false,
            },
        }
    };

    let range = if !rounded.discarded
        || (rounded.value == F64_MIN_NORMAL_BITS && rounded.remainder_at_least_three_quarters)
    {
        RangeState::InRange
    } else {
        RangeState::Underflow
    };
    (f64::from_bits(sign | rounded.value), range)
}

struct HexBits<'a> {
    digits: &'a [u8],
    bit_len: usize,
}

impl<'a> HexBits<'a> {
    fn new(digits: &'a [u8]) -> Self {
        debug_assert!(digits.first().is_some_and(|digit| *digit != 0));
        let first_width = (u8::BITS - digits[0].leading_zeros()) as usize;
        Self {
            digits,
            bit_len: (digits.len() - 1) * 4 + first_width,
        }
    }

    fn bit(&self, position: usize) -> bool {
        if position >= self.bit_len {
            return false;
        }
        let nibble_from_end = position / 4;
        let digit = self.digits[self.digits.len() - 1 - nibble_from_end];
        digit & (1 << (position % 4)) != 0
    }

    fn extract(&self, start: usize, count: usize) -> u64 {
        debug_assert!(count <= 53);
        debug_assert!(start + count <= self.bit_len);
        let mut value = 0_u64;
        for offset in (0..count).rev() {
            value = (value << 1) | u64::from(self.bit(start + offset));
        }
        value
    }

    fn has_nonzero_below(&self, bit_count: usize) -> bool {
        let bit_count = bit_count.min(self.bit_len);
        let complete_nibbles = bit_count / 4;
        if self.digits[self.digits.len() - complete_nibbles..]
            .iter()
            .any(|digit| *digit != 0)
        {
            return true;
        }
        let remaining_bits = bit_count % 4;
        remaining_bits != 0
            && self.digits[self.digits.len() - complete_nibbles - 1] & ((1 << remaining_bits) - 1)
                != 0
    }

    fn round_after_right_shift(&self, shift: usize) -> RoundedBits {
        if shift == 0 {
            return RoundedBits {
                value: self.extract(0, self.bit_len),
                discarded: false,
                remainder_at_least_three_quarters: false,
            };
        }

        let kept = self.bit_len.saturating_sub(shift);
        let truncated = self.extract(shift.min(self.bit_len), kept);
        let guard = shift <= self.bit_len && self.bit(shift - 1);
        let sticky = self.has_nonzero_below(shift.saturating_sub(1));
        let discarded = self.has_nonzero_below(shift);
        let round_up = guard && (sticky || truncated & 1 != 0);
        RoundedBits {
            value: truncated + u64::from(round_up),
            discarded,
            remainder_at_least_three_quarters: shift >= 2
                && shift <= self.bit_len
                && self.bit(shift - 1)
                && self.bit(shift - 2),
        }
    }
}

struct RoundedBits {
    value: u64,
    discarded: bool,
    remainder_at_least_three_quarters: bool,
}

#[derive(Debug, Clone, Copy)]
struct IntegerPrefix {
    negative: bool,
    magnitude: u128,
    overflowed: bool,
    end: usize,
    converted: bool,
}

fn parse_integer_prefix(bytes: &[u8]) -> IntegerPrefix {
    let start = skip_ascii_whitespace(bytes);
    let mut index = start;
    let negative = match bytes.get(index) {
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
    if bytes.get(index) == Some(&b'0') {
        if matches!(bytes.get(index + 1), Some(b'x') | Some(b'X'))
            && bytes
                .get(index + 2)
                .is_some_and(|byte| byte.is_ascii_hexdigit())
        {
            base = 16;
            index += 2;
        } else {
            base = 8;
        }
    }

    let digit_start = index;
    let mut magnitude = 0_u128;
    let mut overflowed = false;
    while let Some(digit) = bytes.get(index).and_then(|byte| digit_value(*byte)) {
        if digit >= base {
            break;
        }
        magnitude = match magnitude
            .checked_mul(u128::from(base))
            .and_then(|value| value.checked_add(u128::from(digit)))
        {
            Some(value) => value,
            None => {
                overflowed = true;
                u128::MAX
            }
        };
        index += 1;
    }
    IntegerPrefix {
        negative,
        magnitude,
        overflowed,
        end: if index == digit_start { 0 } else { index },
        converted: index != digit_start,
    }
}

fn digit_value(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

fn skip_ascii_whitespace(bytes: &[u8]) -> usize {
    bytes
        .iter()
        .position(|byte| !matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c))
        .unwrap_or(bytes.len())
}

fn has_ascii_prefix_case_insensitive(bytes: &[u8], prefix: &[u8]) -> bool {
    bytes
        .get(..prefix.len())
        .is_some_and(|candidate| candidate.eq_ignore_ascii_case(prefix))
}

fn unconverted_float() -> Parsed<f64> {
    Parsed {
        value: 0.0,
        end: 0,
        converted: false,
        range: RangeState::InRange,
    }
}

#[cfg(test)]
mod tests {
    use super::{
        getint_consumes, parse_getint, parse_long, parse_ulong, quote_value, Parsed, RangeState,
    };

    #[test]
    fn parser_test_module_is_wired() {
        let _ = Parsed {
            value: 0_u64,
            end: 0,
            converted: false,
            range: RangeState::InRange,
        };
    }

    mod getint_cases {
        use super::{getint_consumes, parse_getint};

        #[test]
        fn consumption_gate_matches_strchr_first_byte_semantics() {
            let accepted: &[&[u8]] = &[
                b"",
                b"\0ignored",
                b"+suffix",
                b"-suffix",
                b".suffix",
                b"0suffix",
                b"9suffix",
            ];
            for &operand in accepted {
                assert!(getint_consumes(operand), "{operand:?}");
            }

            let rejected: &[&[u8]] = &[b" 3", b"\t4", b"x5", b"/6", b"\xff"];
            for &operand in rejected {
                assert!(!getint_consumes(operand), "{operand:?}");
            }
        }

        #[test]
        fn atoi_compatible_parser_uses_only_a_signed_decimal_prefix() {
            let cases: &[(&[u8], i32)] = &[
                (b"", 0),
                (b".", 0),
                (b"+", 0),
                (b"-", 0),
                (b"+.5", 0),
                (b"0x10", 0),
                (b"12tail", 12),
                (b"-007.5", -7),
                (b"+003suffix", 3),
            ];
            for &(operand, expected) in cases {
                assert_eq!(parse_getint(operand), expected, "{operand:?}");
            }
        }

        #[test]
        fn decimal_accumulation_truncates_to_a_c_32_bit_int() {
            let cases: &[(&[u8], i32)] = &[
                (b"2147483647", i32::MAX),
                (b"2147483648", i32::MIN),
                (b"4294967295", -1),
                (b"4294967296", 0),
                (b"4294967298tail", 2),
                (b"-2147483649", i32::MAX),
                (b"-4294967298tail", -2),
            ];
            for &(operand, expected) in cases {
                assert_eq!(parse_getint(operand), expected, "{operand:?}");
            }
        }
    }

    mod integer_cases {
        use super::{parse_long, parse_ulong, quote_value, Parsed, RangeState};

        #[test]
        fn quoted_operand_uses_the_unsigned_second_byte_without_a_closing_quote() {
            assert_eq!(quote_value(b"'A"), Some(b'A'));
            assert_eq!(quote_value(b"\"z"), Some(b'z'));
            assert_eq!(quote_value(b"''"), Some(b'\''));
            assert_eq!(quote_value(b"'"), Some(0));
            assert_eq!(quote_value(b"'\xffsuffix"), Some(0xff));
            assert_eq!(quote_value(b"not quoted"), None);
        }

        #[test]
        fn signed_parser_selects_c_base_zero_and_reports_exact_prefix_offsets() {
            let cases = [
                (
                    b"0".as_slice(),
                    Parsed {
                        value: 0,
                        end: 1,
                        converted: true,
                        range: RangeState::InRange,
                    },
                ),
                (
                    b" \t\n\r\x0b\x0c+42tail".as_slice(),
                    Parsed {
                        value: 42,
                        end: 9,
                        converted: true,
                        range: RangeState::InRange,
                    },
                ),
                (
                    b"-077".as_slice(),
                    Parsed {
                        value: -63,
                        end: 4,
                        converted: true,
                        range: RangeState::InRange,
                    },
                ),
                (
                    b"0x7f".as_slice(),
                    Parsed {
                        value: 127,
                        end: 4,
                        converted: true,
                        range: RangeState::InRange,
                    },
                ),
                (
                    b"-0XfFrest".as_slice(),
                    Parsed {
                        value: -255,
                        end: 5,
                        converted: true,
                        range: RangeState::InRange,
                    },
                ),
                (
                    b"09".as_slice(),
                    Parsed {
                        value: 0,
                        end: 1,
                        converted: true,
                        range: RangeState::InRange,
                    },
                ),
                (
                    b"0x".as_slice(),
                    Parsed {
                        value: 0,
                        end: 1,
                        converted: true,
                        range: RangeState::InRange,
                    },
                ),
                (
                    b"  -xyz".as_slice(),
                    Parsed {
                        value: 0,
                        end: 0,
                        converted: false,
                        range: RangeState::InRange,
                    },
                ),
            ];

            for (operand, expected) in cases {
                assert_eq!(parse_long(operand), expected, "{operand:?}");
            }
        }

        #[test]
        fn signed_parser_saturates_both_lp64_boundaries_and_finishes_scanning() {
            let cases = [
                (
                    b"9223372036854775807".as_slice(),
                    i64::MAX,
                    RangeState::InRange,
                ),
                (
                    b"9223372036854775808".as_slice(),
                    i64::MAX,
                    RangeState::Overflow,
                ),
                (
                    b"-9223372036854775808".as_slice(),
                    i64::MIN,
                    RangeState::InRange,
                ),
                (
                    b"-9223372036854775809".as_slice(),
                    i64::MIN,
                    RangeState::Underflow,
                ),
                (
                    b"0x7fffffffffffffff".as_slice(),
                    i64::MAX,
                    RangeState::InRange,
                ),
                (
                    b"-0x8000000000000000".as_slice(),
                    i64::MIN,
                    RangeState::InRange,
                ),
            ];

            for (operand, value, range) in cases {
                let parsed = parse_long(operand);
                assert_eq!(parsed.value, value, "{operand:?}");
                assert_eq!(parsed.end, operand.len(), "{operand:?}");
                assert!(parsed.converted, "{operand:?}");
                assert_eq!(parsed.range, range, "{operand:?}");
            }

            let operand = b"999999999999999999999999999999999999999999999999tail";
            let parsed = parse_long(operand);
            assert_eq!(parsed.value, i64::MAX);
            assert_eq!(parsed.end, operand.len() - b"tail".len());
            assert_eq!(parsed.range, RangeState::Overflow);
        }

        #[test]
        fn unsigned_parser_saturates_or_applies_modulo_negation() {
            let cases = [
                (
                    b"18446744073709551615".as_slice(),
                    u64::MAX,
                    RangeState::InRange,
                ),
                (
                    b"18446744073709551616".as_slice(),
                    u64::MAX,
                    RangeState::Overflow,
                ),
                (
                    b"0xffffffffffffffff".as_slice(),
                    u64::MAX,
                    RangeState::InRange,
                ),
                (
                    b"0x10000000000000000".as_slice(),
                    u64::MAX,
                    RangeState::Overflow,
                ),
                (b"-0".as_slice(), 0, RangeState::InRange),
                (b"-1".as_slice(), u64::MAX, RangeState::InRange),
                (b"-18446744073709551615".as_slice(), 1, RangeState::InRange),
                (
                    b"-18446744073709551616".as_slice(),
                    u64::MAX,
                    RangeState::Overflow,
                ),
            ];

            for (operand, value, range) in cases {
                let parsed = parse_ulong(operand);
                assert_eq!(parsed.value, value, "{operand:?}");
                assert_eq!(parsed.end, operand.len(), "{operand:?}");
                assert!(parsed.converted, "{operand:?}");
                assert_eq!(parsed.range, range, "{operand:?}");
            }
        }

        #[test]
        fn unsigned_parser_stops_at_the_first_digit_invalid_for_the_selected_base() {
            let cases = [
                (b"0779".as_slice(), 63, 3, true),
                (b"0xg".as_slice(), 0, 1, true),
                (b"+123suffix".as_slice(), 123, 4, true),
                (b" whitespace".as_slice(), 0, 0, false),
                (b"".as_slice(), 0, 0, false),
            ];

            for (operand, value, end, converted) in cases {
                let parsed = parse_ulong(operand);
                assert_eq!(parsed.value, value, "{operand:?}");
                assert_eq!(parsed.end, end, "{operand:?}");
                assert_eq!(parsed.converted, converted, "{operand:?}");
                assert_eq!(parsed.range, RangeState::InRange, "{operand:?}");
            }
        }
    }

    mod float_cases {
        use super::super::{parse_double, Parsed, RangeState};

        #[test]
        fn decimal_scanner_keeps_c_prefix_end_offsets_and_signed_zero() {
            let cases: &[(&[u8], u64, usize)] = &[
                (b".5", 0.5_f64.to_bits(), 2),
                (b"1.", 1.0_f64.to_bits(), 2),
                (b"1.e2", 100.0_f64.to_bits(), 4),
                (b"1e+", 1.0_f64.to_bits(), 1),
                (b" \t-12.5e+2tail", (-1250.0_f64).to_bits(), 10),
                (b"  +.125E2!", 12.5_f64.to_bits(), 9),
                (b"0x", 0.0_f64.to_bits(), 1),
                (b"-0x", (-0.0_f64).to_bits(), 2),
                (b"-0e999999999999999999999", (-0.0_f64).to_bits(), 24),
            ];
            for &(operand, expected_bits, expected_end) in cases {
                assert_parsed_bits(operand, expected_bits, expected_end, RangeState::InRange);
            }

            for &operand in &[b"".as_slice(), b" \t", b"+", b"-", b".", b".e2", b"word"] {
                assert_eq!(
                    parse_double(operand),
                    Parsed {
                        value: 0.0,
                        end: 0,
                        converted: false,
                        range: RangeState::InRange,
                    },
                    "{operand:?}"
                );
            }
        }

        #[test]
        fn special_spellings_are_case_insensitive_and_preserve_nan_payload_and_sign() {
            assert_parsed_bits(b"inf", f64::INFINITY.to_bits(), 3, RangeState::InRange);
            assert_parsed_bits(
                b" -INFINITYtail",
                f64::NEG_INFINITY.to_bits(),
                10,
                RangeState::InRange,
            );
            assert_parsed_bits(b"infinite", f64::INFINITY.to_bits(), 3, RangeState::InRange);
            assert_parsed_bits(b"nan", 0x7ff8_0000_0000_0000, 3, RangeState::InRange);
            assert_parsed_bits(
                b"-NAN(0x123)!",
                0xfff8_0000_0000_0123,
                11,
                RangeState::InRange,
            );
            assert_parsed_bits(b"nan(0123)", 0x7ff8_0000_0000_0053, 9, RangeState::InRange);
            assert_parsed_bits(
                b"nan(foo-bar)",
                0x7ff8_0000_0000_0000,
                3,
                RangeState::InRange,
            );
            assert_parsed_bits(b"nan(a)b", 0x7ff8_0000_0000_0000, 6, RangeState::InRange);
        }

        #[test]
        fn hexadecimal_scanner_accepts_optional_points_and_complete_binary_exponents() {
            let cases: &[(&[u8], u64, usize)] = &[
                (b"0x1.8p+1", 3.0_f64.to_bits(), 8),
                (b"0X1f", 31.0_f64.to_bits(), 4),
                (b"0x.8", 0.5_f64.to_bits(), 4),
                (b"0x1.", 1.0_f64.to_bits(), 4),
                (b"-0x1p", (-1.0_f64).to_bits(), 4),
                (b"0x1p+", 1.0_f64.to_bits(), 3),
                (b"  +0x1.2P-3z", 0.140625_f64.to_bits(), 11),
                (b"0x.p1", 0.0_f64.to_bits(), 1),
            ];
            for &(operand, expected_bits, expected_end) in cases {
                assert_parsed_bits(operand, expected_bits, expected_end, RangeState::InRange);
            }
        }

        #[test]
        fn hexadecimal_rounding_uses_guard_round_sticky_and_ties_to_even() {
            let one = 1.0_f64.to_bits();
            let cases = [
                (b"0x1.00000000000008p0".as_slice(), one),
                (b"0x1.000000000000080001p0".as_slice(), one + 1),
                (b"0x1.00000000000018p0".as_slice(), one + 2),
                (b"0x1.fffffffffffff7p0".as_slice(), 2.0_f64.to_bits() - 1),
                (b"0x1.fffffffffffff8p0".as_slice(), 2.0_f64.to_bits()),
            ];
            for (operand, expected_bits) in cases {
                assert_parsed_bits(operand, expected_bits, operand.len(), RangeState::InRange);
            }
        }

        #[test]
        fn hexadecimal_range_metadata_distinguishes_exact_and_inexact_tiny_values() {
            let cases = [
                (
                    b"0x0p-999999999999999999999".as_slice(),
                    0.0_f64.to_bits(),
                    RangeState::InRange,
                ),
                (
                    b"-0x0p-999999999999999999999".as_slice(),
                    (-0.0_f64).to_bits(),
                    RangeState::InRange,
                ),
                (b"0x1p-1074".as_slice(), 1, RangeState::InRange),
                (b"0x2p-1075".as_slice(), 1, RangeState::InRange),
                (
                    b"0x1.000000000000000000p-1074".as_slice(),
                    1,
                    RangeState::InRange,
                ),
                (
                    b"0x1.000000000000000001p-1074".as_slice(),
                    1,
                    RangeState::Underflow,
                ),
                (b"0x1p-1075".as_slice(), 0, RangeState::Underflow),
                (
                    b"-0x1p-1075".as_slice(),
                    (-0.0_f64).to_bits(),
                    RangeState::Underflow,
                ),
                (
                    b"0x0.fffffffffffffbp-1022".as_slice(),
                    f64::MIN_POSITIVE.to_bits(),
                    RangeState::Underflow,
                ),
                (
                    b"0x0.fffffffffffffcp-1022".as_slice(),
                    f64::MIN_POSITIVE.to_bits(),
                    RangeState::InRange,
                ),
                (
                    b"0x1.fffffffffffffp1023".as_slice(),
                    f64::MAX.to_bits(),
                    RangeState::InRange,
                ),
                (
                    b"0x1.fffffffffffff8p1023".as_slice(),
                    f64::INFINITY.to_bits(),
                    RangeState::Overflow,
                ),
                (
                    b"0x1p999999999999999999999".as_slice(),
                    f64::INFINITY.to_bits(),
                    RangeState::Overflow,
                ),
            ];
            for (operand, expected_bits, expected_range) in cases {
                assert_parsed_bits(operand, expected_bits, operand.len(), expected_range);
            }
        }

        #[test]
        fn decimal_range_metadata_matches_exactness_and_rounded_boundary_rules() {
            let cases = [
                (
                    b"0e-999999999999999999999".as_slice(),
                    0.0_f64.to_bits(),
                    RangeState::InRange,
                ),
                (
                    b"1e-999999999999999999999".as_slice(),
                    0.0_f64.to_bits(),
                    RangeState::Underflow,
                ),
                (b"5e-324".as_slice(), 1, RangeState::Underflow),
                (
                    b"2.2250738585072012e-308".as_slice(),
                    f64::MIN_POSITIVE.to_bits(),
                    RangeState::Underflow,
                ),
                (
                    b"2.2250738585072013e-308".as_slice(),
                    f64::MIN_POSITIVE.to_bits(),
                    RangeState::InRange,
                ),
                (
                    b"1.7976931348623157e308".as_slice(),
                    f64::MAX.to_bits(),
                    RangeState::InRange,
                ),
                (
                    b"1.7976931348623159e308".as_slice(),
                    f64::INFINITY.to_bits(),
                    RangeState::Overflow,
                ),
            ];
            for (operand, expected_bits, expected_range) in cases {
                assert_parsed_bits(operand, expected_bits, operand.len(), expected_range);
            }

            let exact_minimum_subnormal = format!("{:.1074}", f64::from_bits(1));
            assert_parsed_bits(
                exact_minimum_subnormal.as_bytes(),
                1,
                exact_minimum_subnormal.len(),
                RangeState::InRange,
            );
        }

        fn assert_parsed_bits(
            operand: &[u8],
            expected_bits: u64,
            expected_end: usize,
            expected_range: RangeState,
        ) {
            let parsed = parse_double(operand);
            assert!(parsed.converted, "{operand:?}");
            assert_eq!(parsed.value.to_bits(), expected_bits, "{operand:?}");
            assert_eq!(parsed.end, expected_end, "{operand:?}");
            assert_eq!(parsed.range, expected_range, "{operand:?}");
        }
    }
}
