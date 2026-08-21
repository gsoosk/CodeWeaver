use std::io::{self, Write};

use crate::regex_backend::RegexBackend;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Token {
    Or,
    And,
    Eq,
    Lt,
    Gt,
    Add,
    Sub,
    Mul,
    Div,
    Mod,
    Match,
    Rp,
    Lp,
    Ne,
    Le,
    Ge,
    Operand,
    Eoi,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum Val {
    Integer(i64),
    String(Vec<u8>),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum NumberError {
    Invalid,
    TooSmall,
    TooLarge,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ExprError {
    pub(crate) status: i32,
    pub(crate) message: Vec<u8>,
}

pub(crate) struct Parser<'a> {
    args: &'a [Vec<u8>],
    index: usize,
    token: Token,
    tokval: Option<Val>,
    regex: &'a dyn RegexBackend,
}

impl<'a> Parser<'a> {
    pub(crate) fn new(args: &'a [Vec<u8>], regex: &'a dyn RegexBackend) -> Self {
        Self {
            args,
            index: 0,
            token: Token::Eoi,
            tokval: None,
            regex,
        }
    }

    pub(crate) fn nexttoken(&mut self, pattern: bool) {
        let Some(arg) = self.args.get(self.index) else {
            self.token = Token::Eoi;
            self.tokval = None;
            return;
        };
        self.index += 1;

        self.token = if !pattern {
            match arg.as_slice() {
                b"|" => Token::Or,
                b"&" => Token::And,
                b"=" => Token::Eq,
                b"<" => Token::Lt,
                b">" => Token::Gt,
                b"+" => Token::Add,
                b"-" => Token::Sub,
                b"*" => Token::Mul,
                b"/" => Token::Div,
                b"%" => Token::Mod,
                b":" => Token::Match,
                b"(" => Token::Rp,
                b")" => Token::Lp,
                b"!=" => Token::Ne,
                b"<=" => Token::Le,
                b">=" => Token::Ge,
                _ => Token::Operand,
            }
        } else {
            Token::Operand
        };

        self.tokval = (self.token == Token::Operand).then(|| make_str(arg));
    }

    pub(crate) fn eval6(&mut self) -> Result<Val, ExprError> {
        match self.token {
            Token::Operand => {
                let value = self.tokval.take().ok_or_else(error)?;
                self.nexttoken(false);
                Ok(value)
            }
            Token::Rp => {
                self.nexttoken(false);
                let value = self.eval0()?;
                if self.token != Token::Lp {
                    return Err(error());
                }
                self.nexttoken(false);
                Ok(value)
            }
            _ => Err(error()),
        }
    }

    pub(crate) fn eval5(&mut self) -> Result<Val, ExprError> {
        let mut left = self.eval6()?;
        while self.token == Token::Match {
            self.nexttoken(true);
            let mut right = self.eval6()?;
            to_string(&mut left);
            to_string(&mut right);

            let subject = match &left {
                Val::String(value) => value.as_slice(),
                Val::Integer(_) => unreachable!("to_string always produces a string"),
            };
            let pattern = match &right {
                Val::String(value) => value.as_slice(),
                Val::Integer(_) => unreachable!("to_string always produces a string"),
            };
            let matched = self
                .regex
                .compile_and_match(pattern, subject)
                .map_err(|error| ExprError {
                    status: 2,
                    message: error.message,
                })?;

            if matched.first_capture.is_some() && matched.capture_count == 0 {
                return Err(invalid_regex_result());
            }
            if let Some(whole_match) = &matched.whole_match {
                if whole_match.start > whole_match.end || whole_match.end > subject.len() {
                    return Err(invalid_regex_result());
                }
                if let Some(first_capture) = &matched.first_capture {
                    if first_capture.start > first_capture.end
                        || first_capture.end > subject.len()
                        || first_capture.start < whole_match.start
                        || first_capture.end > whole_match.end
                    {
                        return Err(invalid_regex_result());
                    }
                }
            } else if matched.first_capture.is_some() {
                return Err(invalid_regex_result());
            }

            let anchored_match = matched
                .whole_match
                .as_ref()
                .filter(|range| range.start == 0);
            left = if let Some(whole_match) = anchored_match {
                if let Some(first_capture) = matched.first_capture {
                    make_str(&subject[first_capture])
                } else {
                    make_int(
                        i64::try_from(whole_match.end - whole_match.start)
                            .map_err(|_| invalid_regex_result())?,
                    )
                }
            } else if matched.capture_count == 0 {
                make_int(0)
            } else {
                make_str(b"")
            };
        }
        Ok(left)
    }

    pub(crate) fn eval4(&mut self) -> Result<Val, ExprError> {
        let mut left = self.eval5()?;
        while matches!(self.token, Token::Mul | Token::Div | Token::Mod) {
            let operator = self.token;
            self.nexttoken(false);
            let mut right = self.eval5()?;
            let left_value = arithmetic_integer(&mut left)?;
            let right_value = arithmetic_integer(&mut right)?;

            let result = match operator {
                Token::Mul => left_value.checked_mul(right_value).ok_or_else(overflow)?,
                Token::Div => {
                    if right_value == 0 {
                        return Err(division_by_zero());
                    }
                    left_value.checked_div(right_value).ok_or_else(overflow)?
                }
                Token::Mod => {
                    if right_value == 0 {
                        return Err(division_by_zero());
                    }
                    if left_value == i64::MIN && right_value == -1 {
                        0
                    } else {
                        left_value.checked_rem(right_value).ok_or_else(overflow)?
                    }
                }
                _ => unreachable!("operator loop admits only multiplicative tokens"),
            };
            left = make_int(result);
        }
        Ok(left)
    }

    pub(crate) fn eval3(&mut self) -> Result<Val, ExprError> {
        let mut left = self.eval4()?;
        while matches!(self.token, Token::Add | Token::Sub) {
            let operator = self.token;
            self.nexttoken(false);
            let mut right = self.eval4()?;
            let left_value = arithmetic_integer(&mut left)?;
            let right_value = arithmetic_integer(&mut right)?;
            let result = match operator {
                Token::Add => left_value.checked_add(right_value).ok_or_else(overflow)?,
                Token::Sub => left_value.checked_sub(right_value).ok_or_else(overflow)?,
                _ => unreachable!("operator loop admits only additive tokens"),
            };
            left = make_int(result);
        }
        Ok(left)
    }

    pub(crate) fn eval2(&mut self) -> Result<Val, ExprError> {
        let mut left = self.eval3()?;
        while matches!(
            self.token,
            Token::Eq | Token::Ne | Token::Lt | Token::Gt | Token::Le | Token::Ge
        ) {
            let operator = self.token;
            self.nexttoken(false);
            let mut right = self.eval3()?;

            let ordering = match (is_integer(&left), is_integer(&right)) {
                (Ok(left_value), Ok(right_value)) => left_value.cmp(&right_value),
                _ => {
                    to_string(&mut left);
                    to_string(&mut right);
                    let Val::String(left_value) = &left else {
                        unreachable!("to_string always produces a string");
                    };
                    let Val::String(right_value) = &right else {
                        unreachable!("to_string always produces a string");
                    };
                    left_value.cmp(right_value)
                }
            };
            let result = match operator {
                Token::Eq => ordering.is_eq(),
                Token::Ne => ordering.is_ne(),
                Token::Lt => ordering.is_lt(),
                Token::Gt => ordering.is_gt(),
                Token::Le => ordering.is_le(),
                Token::Ge => ordering.is_ge(),
                _ => unreachable!("operator loop admits only comparison tokens"),
            };
            left = make_int(i64::from(result));
        }
        Ok(left)
    }

    pub(crate) fn eval1(&mut self) -> Result<Val, ExprError> {
        let mut left = self.eval2()?;
        while self.token == Token::And {
            self.nexttoken(false);
            let mut right = self.eval2()?;
            if is_zero_or_null(&mut left) || is_zero_or_null(&mut right) {
                left = make_int(0);
            }
        }
        Ok(left)
    }

    pub(crate) fn eval0(&mut self) -> Result<Val, ExprError> {
        let mut left = self.eval1()?;
        while self.token == Token::Or {
            self.nexttoken(false);
            let right = self.eval1()?;
            if is_zero_or_null(&mut left) {
                left = right;
            }
        }
        Ok(left)
    }
}

pub(crate) fn make_int(value: i64) -> Val {
    Val::Integer(value)
}

pub(crate) fn make_str(value: &[u8]) -> Val {
    Val::String(value.to_vec())
}

pub(crate) fn strtonum(value: &[u8]) -> Result<i64, NumberError> {
    let mut index = 0;
    while value
        .get(index)
        .is_some_and(|byte| matches!(byte, b' ' | b'\t' | b'\n' | 0x0b | 0x0c | b'\r'))
    {
        index += 1;
    }

    let negative = match value.get(index) {
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
    let first_digit = index;
    let mut magnitude = 0_u64;
    let mut overflowed = false;
    while let Some(byte @ b'0'..=b'9') = value.get(index) {
        if !overflowed {
            magnitude = match magnitude
                .checked_mul(10)
                .and_then(|number| number.checked_add(u64::from(*byte - b'0')))
            {
                Some(number) => number,
                None => {
                    overflowed = true;
                    magnitude
                }
            };
        }
        index += 1;
    }

    if first_digit == index || index != value.len() {
        return Err(NumberError::Invalid);
    }

    let limit = if negative {
        (i64::MAX as u64) + 1
    } else {
        i64::MAX as u64
    };
    if overflowed || magnitude > limit {
        return Err(if negative {
            NumberError::TooSmall
        } else {
            NumberError::TooLarge
        });
    }

    if negative {
        if magnitude == limit {
            Ok(i64::MIN)
        } else {
            Ok(-(magnitude as i64))
        }
    } else {
        Ok(magnitude as i64)
    }
}

pub(crate) fn is_integer(value: &Val) -> Result<i64, NumberError> {
    match value {
        Val::Integer(number) => Ok(*number),
        Val::String(bytes) => strtonum(bytes),
    }
}

pub(crate) fn to_integer(value: &mut Val) -> Result<(), NumberError> {
    if matches!(value, Val::Integer(_)) {
        return Ok(());
    }
    let number = is_integer(value)?;
    *value = make_int(number);
    Ok(())
}

pub(crate) fn to_string(value: &mut Val) {
    if let Val::Integer(number) = value {
        *value = Val::String(number.to_string().into_bytes());
    }
}

pub(crate) fn is_zero_or_null(value: &mut Val) -> bool {
    match value {
        Val::Integer(number) => *number == 0,
        Val::String(bytes) if bytes.is_empty() => true,
        Val::String(_) => to_integer(value).is_ok() && matches!(value, Val::Integer(0)),
    }
}

pub(crate) fn render(value: &Val) -> Vec<u8> {
    match value {
        Val::Integer(number) => number.to_string().into_bytes(),
        Val::String(bytes) => bytes.clone(),
    }
}

pub(crate) fn error() -> ExprError {
    ExprError {
        status: 2,
        message: b"syntax error".to_vec(),
    }
}

pub(crate) fn evaluate(args: &[Vec<u8>], regex: &dyn RegexBackend) -> Result<Val, ExprError> {
    let mut parser = Parser::new(args, regex);
    parser.nexttoken(false);
    let value = parser.eval0()?;
    if parser.token != Token::Eoi {
        return Err(error());
    }
    Ok(value)
}

pub(crate) fn program_basename(argv0: &[u8]) -> &[u8] {
    argv0
        .iter()
        .rposition(|byte| *byte == b'/')
        .map_or(argv0, |index| &argv0[index + 1..])
}

pub(crate) fn run_cli(
    argv0: &[u8],
    args: &[Vec<u8>],
    regex: &dyn RegexBackend,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
) -> io::Result<i32> {
    let args = if args.first().is_some_and(|arg| arg == b"--") {
        &args[1..]
    } else {
        args
    };

    match evaluate(args, regex) {
        Ok(mut value) => {
            stdout.write_all(&render(&value))?;
            stdout.write_all(b"\n")?;
            Ok(i32::from(is_zero_or_null(&mut value)))
        }
        Err(error) => {
            stderr.write_all(program_basename(argv0))?;
            stderr.write_all(b": ")?;
            stderr.write_all(&error.message)?;
            stderr.write_all(b"\n")?;
            Ok(error.status)
        }
    }
}

fn arithmetic_integer(value: &mut Val) -> Result<i64, ExprError> {
    if let Err(classification) = to_integer(value) {
        let raw = match value {
            Val::String(bytes) => bytes.as_slice(),
            Val::Integer(_) => unreachable!("integer coercion cannot fail for integers"),
        };
        let mut message = b"number \"".to_vec();
        message.extend_from_slice(raw);
        message.extend_from_slice(b"\" is ");
        message.extend_from_slice(match classification {
            NumberError::Invalid => b"invalid",
            NumberError::TooSmall => b"too small",
            NumberError::TooLarge => b"too large",
        });
        return Err(ExprError { status: 2, message });
    }
    match value {
        Val::Integer(number) => Ok(*number),
        Val::String(_) => unreachable!("successful coercion always produces an integer"),
    }
}

fn division_by_zero() -> ExprError {
    ExprError {
        status: 2,
        message: b"division by zero".to_vec(),
    }
}

fn overflow() -> ExprError {
    ExprError {
        status: 3,
        message: b"overflow".to_vec(),
    }
}

fn invalid_regex_result() -> ExprError {
    ExprError {
        status: 2,
        message: b"Invalid regular expression".to_vec(),
    }
}

#[cfg(test)]
mod tests {
    use std::io::{self, Write};

    use super::{
        error, evaluate, is_integer, is_zero_or_null, make_int, make_str, render, run_cli,
        strtonum, to_integer, to_string, ExprError, NumberError, Parser, Token, Val,
    };
    use crate::regex_backend::test_support::FakeRegexBackend;
    use crate::regex_backend::{RegexBackend, RegexError, RegexMatch};

    fn parser_with_fake<'a>(args: &'a [Vec<u8>], backend: &'a FakeRegexBackend) -> Parser<'a> {
        Parser::new(args, backend)
    }

    fn exact_operator_tokens() -> &'static [(&'static [u8], Token)] {
        &[
            (b"|", Token::Or),
            (b"&", Token::And),
            (b"=", Token::Eq),
            (b"<", Token::Lt),
            (b">", Token::Gt),
            (b"+", Token::Add),
            (b"-", Token::Sub),
            (b"*", Token::Mul),
            (b"/", Token::Div),
            (b"%", Token::Mod),
            (b":", Token::Match),
            (b"(", Token::Rp),
            (b")", Token::Lp),
            (b"!=", Token::Ne),
            (b"<=", Token::Le),
            (b">=", Token::Ge),
        ]
    }

    #[test]
    fn tokenizes_every_exact_operator_spelling() {
        for &(spelling, expected) in exact_operator_tokens() {
            let args = owned_args(&[spelling]);
            let backend = FakeRegexBackend::default();
            let mut parser = parser_with_fake(&args, &backend);

            parser.nexttoken(false);
            assert_eq!(parser.token, expected, "token for {spelling:?}");
            assert!(parser.tokval.is_none(), "operator value for {spelling:?}");
            assert_eq!(parser.index, 1, "cursor for {spelling:?}");

            parser.nexttoken(false);
            assert_eq!(parser.token, Token::Eoi, "end token for {spelling:?}");
            assert!(parser.tokval.is_none(), "end value for {spelling:?}");
        }
    }

    #[test]
    fn treats_nonoperators_as_operands() {
        let cases: &[&[u8]] = &[
            b"", b"==", b"!", b"=>", b"<>", b"||", b"++", b"--help", b"-2", b"1 + 2", b"!=x",
            b"\xff",
        ];

        for &input in cases {
            let args = owned_args(&[input]);
            let backend = FakeRegexBackend::default();
            let mut parser = parser_with_fake(&args, &backend);

            parser.nexttoken(false);
            assert_eq!(parser.token, Token::Operand, "token for {input:?}");
            assert_eq!(
                parser.tokval.as_ref(),
                Some(&Val::String(input.to_vec())),
                "operand for {input:?}"
            );
        }
    }

    #[test]
    fn shields_pattern_tokens_after_match() {
        for &(spelling, _) in exact_operator_tokens() {
            let args = owned_args(&[spelling]);
            let backend = FakeRegexBackend::default();
            let mut parser = parser_with_fake(&args, &backend);

            parser.nexttoken(true);
            assert_eq!(parser.token, Token::Operand, "shielded token {spelling:?}");
            assert_eq!(
                parser.tokval.as_ref(),
                Some(&Val::String(spelling.to_vec())),
                "shielded value {spelling:?}"
            );
        }

        let args = owned_args(&[b":" as &[u8], b"*", b"+"]);
        let backend = FakeRegexBackend::default();
        let mut parser = parser_with_fake(&args, &backend);
        parser.nexttoken(false);
        assert_eq!(parser.token, Token::Match);
        parser.nexttoken(true);
        assert_eq!(parser.token, Token::Operand);
        assert_eq!(parser.tokval, Some(Val::String(b"*".to_vec())));
        parser.nexttoken(false);
        assert_eq!(parser.token, Token::Add);
    }

    #[test]
    fn parses_c_locale_i64_boundaries() {
        let cases: &[(&[u8], i64)] = &[
            (b"0", 0),
            (b"-0", 0),
            (b"+0", 0),
            (b"42", 42),
            (b"+42", 42),
            (b"-42", -42),
            (b"00000042", 42),
            (b"9223372036854775807", i64::MAX),
            (b"+9223372036854775807", i64::MAX),
            (b"-9223372036854775808", i64::MIN),
            (b" \t\n\x0b\x0c\r-17", -17),
        ];

        for &(input, expected) in cases {
            assert_eq!(strtonum(input), Ok(expected), "number {input:?}");
        }

        for whitespace in [b' ', b'\t', b'\n', 0x0b, 0x0c, b'\r'] {
            let input = [whitespace, b'+', b'7'];
            assert_eq!(
                strtonum(&input),
                Ok(7),
                "leading whitespace byte {whitespace:#04x}"
            );
        }
    }

    #[test]
    fn classifies_invalid_too_small_and_too_large_numbers() {
        let cases: &[(&[u8], NumberError)] = &[
            (b"", NumberError::Invalid),
            (b" ", NumberError::Invalid),
            (b"+", NumberError::Invalid),
            (b"-", NumberError::Invalid),
            (b"  +", NumberError::Invalid),
            (b"1 ", NumberError::Invalid),
            (b"1\t", NumberError::Invalid),
            (b"1x", NumberError::Invalid),
            (b"--1", NumberError::Invalid),
            (b"+-1", NumberError::Invalid),
            (b"\0", NumberError::Invalid),
            (b"1\0", NumberError::Invalid),
            (b"\xff", NumberError::Invalid),
            (b"1\xff", NumberError::Invalid),
            (b"999999999999999999999999999999x", NumberError::Invalid),
            (b"9223372036854775808", NumberError::TooLarge),
            (b"+9223372036854775808", NumberError::TooLarge),
            (b"999999999999999999999999999999", NumberError::TooLarge),
            (b"-9223372036854775809", NumberError::TooSmall),
            (b"-999999999999999999999999999999", NumberError::TooSmall),
        ];

        for &(input, expected) in cases {
            assert_eq!(strtonum(input), Err(expected), "number {input:?}");
        }
    }

    #[test]
    fn coerces_and_renders_values() {
        assert_eq!(make_int(-7), Val::Integer(-7));

        let mut source = vec![0xff, b'a'];
        let owned = make_str(&source);
        source[0] = b'x';
        assert_eq!(owned, Val::String(vec![0xff, b'a']));

        let uncoerced = make_str(b" \t+00042");
        assert_eq!(is_integer(&uncoerced), Ok(42));
        assert_eq!(uncoerced, Val::String(b" \t+00042".to_vec()));

        let mut numeric = make_str(b" \t+00042");
        assert_eq!(to_integer(&mut numeric), Ok(()));
        assert_eq!(numeric, Val::Integer(42));

        let mut invalid = make_str(b"12x");
        assert_eq!(to_integer(&mut invalid), Err(NumberError::Invalid));
        assert_eq!(invalid, Val::String(b"12x".to_vec()));

        let mut oversized = make_str(b"9223372036854775808");
        assert_eq!(to_integer(&mut oversized), Err(NumberError::TooLarge));
        assert_eq!(oversized, Val::String(b"9223372036854775808".to_vec()));

        let mut integer = make_int(i64::MIN);
        to_string(&mut integer);
        assert_eq!(integer, Val::String(b"-9223372036854775808".to_vec()));

        let mut raw = make_str(b"\xff\0");
        to_string(&mut raw);
        assert_eq!(raw, Val::String(vec![0xff, 0]));
        assert_eq!(render(&raw), vec![0xff, 0]);
        assert_eq!(raw, Val::String(vec![0xff, 0]));
        assert_eq!(render(&make_int(i64::MAX)), b"9223372036854775807");
    }

    #[test]
    fn tests_zero_null_and_numeric_string_truth() {
        let mut integer_zero = make_int(0);
        assert!(is_zero_or_null(&mut integer_zero));
        assert_eq!(integer_zero, Val::Integer(0));

        let mut integer_nonzero = make_int(-1);
        assert!(!is_zero_or_null(&mut integer_nonzero));
        assert_eq!(integer_nonzero, Val::Integer(-1));

        let mut empty = make_str(b"");
        assert!(is_zero_or_null(&mut empty));
        assert_eq!(empty, Val::String(Vec::new()));

        for input in [b"0".as_slice(), b"-0", b"+000", b" \t00"] {
            let mut value = make_str(input);
            assert!(is_zero_or_null(&mut value), "truth for {input:?}");
            assert_eq!(value, Val::Integer(0), "canonical value for {input:?}");
        }

        let mut numeric_nonzero = make_str(b"0002");
        assert!(!is_zero_or_null(&mut numeric_nonzero));
        assert_eq!(numeric_nonzero, Val::Integer(2));

        for input in [b"zero".as_slice(), b"9223372036854775808", b"\xff"] {
            let mut value = make_str(input);
            assert!(!is_zero_or_null(&mut value), "truth for {input:?}");
            assert_eq!(
                value,
                Val::String(input.to_vec()),
                "failed coercion for {input:?}"
            );
        }
    }

    #[test]
    fn eval6_handles_operands_and_reversed_named_parentheses() {
        let args = owned_args(&[b"\xffraw" as &[u8], b"+"]);
        let backend = FakeRegexBackend::default();
        let mut parser = parser_with_fake(&args, &backend);
        parser.nexttoken(false);
        assert_eq!(parser.token, Token::Operand);
        assert_eq!(parser.eval6(), Ok(Val::String(b"\xffraw".to_vec())));
        assert_eq!(parser.token, Token::Add);

        let no_args = Vec::new();
        let mut missing = parser_with_fake(&no_args, &backend);
        missing.nexttoken(false);
        assert_eq!(missing.eval6(), Err(error()));

        for &(spelling, expected_token) in
            &[(b"(".as_slice(), Token::Rp), (b")".as_slice(), Token::Lp)]
        {
            let args = owned_args(&[spelling]);
            let mut parser = parser_with_fake(&args, &backend);
            parser.nexttoken(false);
            assert_eq!(parser.token, expected_token);
            assert_eq!(parser.eval6(), Err(error()));
        }
    }

    fn eval4_result(args: &[&[u8]]) -> Result<Val, ExprError> {
        let args = owned_args(args);
        let backend = FakeRegexBackend::default();
        let mut parser = parser_with_fake(&args, &backend);
        parser.nexttoken(false);
        let result = parser.eval4();
        if result.is_ok() {
            assert_eq!(parser.token, Token::Eoi, "unconsumed token for {args:?}");
        }
        assert!(backend.calls().is_empty(), "unexpected regex call");
        result
    }

    fn eval3_result(args: &[&[u8]]) -> Result<Val, ExprError> {
        let args = owned_args(args);
        let backend = FakeRegexBackend::default();
        let mut parser = parser_with_fake(&args, &backend);
        parser.nexttoken(false);
        let result = parser.eval3();
        if result.is_ok() {
            assert_eq!(parser.token, Token::Eoi, "unconsumed token for {args:?}");
        }
        assert!(backend.calls().is_empty(), "unexpected regex call");
        result
    }

    fn eval2_result(args: &[&[u8]]) -> Result<Val, ExprError> {
        let args = owned_args(args);
        let backend = FakeRegexBackend::default();
        let mut parser = parser_with_fake(&args, &backend);
        parser.nexttoken(false);
        let result = parser.eval2();
        if result.is_ok() {
            assert_eq!(parser.token, Token::Eoi, "unconsumed token for {args:?}");
        }
        assert!(backend.calls().is_empty(), "unexpected regex call");
        result
    }

    fn eval1_result(args: &[&[u8]]) -> Result<Val, ExprError> {
        let args = owned_args(args);
        let backend = FakeRegexBackend::default();
        let mut parser = parser_with_fake(&args, &backend);
        parser.nexttoken(false);
        let result = parser.eval1();
        if result.is_ok() {
            assert_eq!(parser.token, Token::Eoi, "unconsumed token for {args:?}");
        }
        assert!(backend.calls().is_empty(), "unexpected regex call");
        result
    }

    fn eval0_result(args: &[&[u8]]) -> Result<Val, ExprError> {
        let args = owned_args(args);
        let backend = FakeRegexBackend::default();
        let mut parser = parser_with_fake(&args, &backend);
        parser.nexttoken(false);
        let result = parser.eval0();
        if result.is_ok() {
            assert_eq!(parser.token, Token::Eoi, "unconsumed token for {args:?}");
        }
        assert!(backend.calls().is_empty(), "unexpected regex call");
        result
    }

    #[test]
    fn eval4_multiplies_divides_and_remainders_left_associatively() {
        let cases: &[(&[&[u8]], i64)] = &[
            (&[b"2", b"*", b"3"], 6),
            (&[b"7", b"/", b"2"], 3),
            (&[b"7", b"%", b"3"], 1),
            (&[b"100", b"/", b"10", b"/", b"2"], 5),
            (&[b"20", b"/", b"5", b"*", b"3", b"%", b"7"], 5),
            (&[b"-7", b"/", b"3"], -2),
            (&[b"7", b"/", b"-3"], -2),
            (&[b"-7", b"%", b"3"], -1),
            (&[b"7", b"%", b"-3"], 1),
            (&[b" \t+0006", b"*", b"-02"], -12),
        ];

        for &(args, expected) in cases {
            assert_eq!(
                eval4_result(args),
                Ok(make_int(expected)),
                "multiplicative expression {args:?}"
            );
        }
    }

    #[test]
    fn eval4_reports_zero_divisors_and_overflow() {
        let operand_errors: &[(&[&[u8]], &[u8])] = &[
            (
                &[b"not-a-number", b"*", b"also-invalid"],
                b"number \"not-a-number\" is invalid",
            ),
            (
                &[b"1", b"/", b"also-invalid"],
                b"number \"also-invalid\" is invalid",
            ),
            (
                &[b"9223372036854775808", b"%", b"1"],
                b"number \"9223372036854775808\" is too large",
            ),
            (
                &[b"1", b"*", b"-9223372036854775809"],
                b"number \"-9223372036854775809\" is too small",
            ),
        ];
        for &(args, message) in operand_errors {
            assert_eq!(
                eval4_result(args),
                Err(ExprError {
                    status: 2,
                    message: message.to_vec(),
                }),
                "operand error for {args:?}"
            );
        }

        for args in [
            &[b"8".as_slice(), b"/", b"0"][..],
            &[b"8".as_slice(), b"%", b" \t+000"][..],
        ] {
            assert_eq!(
                eval4_result(args),
                Err(ExprError {
                    status: 2,
                    message: b"division by zero".to_vec(),
                }),
                "zero divisor for {args:?}"
            );
        }

        for args in [
            &[b"9223372036854775807".as_slice(), b"*", b"2"][..],
            &[b"-9223372036854775808".as_slice(), b"*", b"-1"][..],
            &[b"-9223372036854775808".as_slice(), b"/", b"-1"][..],
        ] {
            assert_eq!(
                eval4_result(args),
                Err(ExprError {
                    status: 3,
                    message: b"overflow".to_vec(),
                }),
                "overflow for {args:?}"
            );
        }
    }

    #[test]
    fn eval4_handles_i64_min_remainder_negative_one() {
        assert_eq!(
            eval4_result(&[b"-9223372036854775808", b"%", b"-1"]),
            Ok(make_int(0))
        );
    }

    #[test]
    fn eval3_adds_and_subtracts_left_associatively() {
        let cases: &[(&[&[u8]], i64)] = &[
            (&[b"2", b"+", b"3"], 5),
            (&[b"2", b"-", b"5"], -3),
            (&[b"3", b"+", b"-2"], 1),
            (&[b"-3", b"+", b"-4"], -7),
            (&[b"-3", b"-", b"-4"], 1),
            (&[b"20", b"-", b"7", b"-", b"5"], 8),
            (&[b"1", b"-", b"2", b"+", b"3"], 2),
            (&[b"10", b"+", b"2", b"-", b"5", b"+", b"1"], 8),
            (&[b" \t+0006", b"+", b"-02"], 4),
            (&[b"9223372036854775807", b"+", b"0"], i64::MAX),
            (&[b"-9223372036854775808", b"-", b"0"], i64::MIN),
        ];

        for &(args, expected) in cases {
            assert_eq!(
                eval3_result(args),
                Ok(make_int(expected)),
                "additive expression {args:?}"
            );
        }
    }

    #[test]
    fn eval3_preserves_multiplicative_precedence() {
        let cases: &[(&[&[u8]], i64)] = &[
            (&[b"3", b"+", b"4", b"*", b"5", b"+", b"0"], 23),
            (&[b"20", b"-", b"12", b"/", b"3", b"*", b"2"], 12),
            (
                &[
                    b"2", b"*", b"3", b"+", b"20", b"/", b"5", b"-", b"7", b"%", b"4",
                ],
                7,
            ),
            (
                &[b"100", b"/", b"10", b"/", b"2", b"+", b"3", b"*", b"4"],
                17,
            ),
            (&[b"18", b"%", b"5", b"*", b"4", b"-", b"6", b"/", b"4"], 11),
        ];

        for &(args, expected) in cases {
            assert_eq!(
                eval3_result(args),
                Ok(make_int(expected)),
                "precedence expression {args:?}"
            );
        }
    }

    #[test]
    fn eval3_reports_operand_classes_and_overflow() {
        let operand_errors: &[(&[&[u8]], &[u8])] = &[
            (
                &[b"not-a-number", b"+", b"also-invalid"],
                b"number \"not-a-number\" is invalid",
            ),
            (&[b"1", b"-", b"\xffbad"], b"number \"\xffbad\" is invalid"),
            (
                &[b"9223372036854775808", b"-", b"1"],
                b"number \"9223372036854775808\" is too large",
            ),
            (
                &[b"1", b"+", b"-9223372036854775809"],
                b"number \"-9223372036854775809\" is too small",
            ),
        ];
        for &(args, message) in operand_errors {
            assert_eq!(
                eval3_result(args),
                Err(ExprError {
                    status: 2,
                    message: message.to_vec(),
                }),
                "operand error for {args:?}"
            );
        }

        for args in [
            &[b"9223372036854775807".as_slice(), b"+", b"1"][..],
            &[b"-9223372036854775808".as_slice(), b"+", b"-1"][..],
            &[b"9223372036854775807".as_slice(), b"-", b"-1"][..],
            &[b"-9223372036854775808".as_slice(), b"-", b"1"][..],
        ] {
            assert_eq!(
                eval3_result(args),
                Err(ExprError {
                    status: 3,
                    message: b"overflow".to_vec(),
                }),
                "overflow for {args:?}"
            );
        }
    }

    #[test]
    fn eval2_compares_numeric_operands() {
        let cases: &[(&[&[u8]], i64)] = &[
            (&[b"+0002", b"=", b"2"], 1),
            (&[b"-2", b"=", b"2"], 0),
            (&[b"-7", b"!=", b"-07"], 0),
            (&[b"-9223372036854775808", b"!=", b"9223372036854775807"], 1),
            (&[b"-2", b"<", b"+1"], 1),
            (&[b"9223372036854775807", b"<", b"-9223372036854775808"], 0),
            (&[b"2", b"<=", b"2"], 1),
            (&[b"3", b"<=", b"2"], 0),
            (&[b" \t+0002", b">", b"-1"], 1),
            (&[b"-9223372036854775808", b">", b"9223372036854775807"], 0),
            (&[b"9223372036854775807", b">=", b"9223372036854775807"], 1),
            (&[b"-1", b">=", b"0"], 0),
        ];

        for &(args, expected) in cases {
            assert_eq!(
                eval2_result(args),
                Ok(make_int(expected)),
                "numeric comparison {args:?}"
            );

            let backend = FakeRegexBackend::default();
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let status = run_cli(
                b"./main",
                &owned_args(args),
                &backend,
                &mut stdout,
                &mut stderr,
            )
            .expect("in-memory writes must succeed");
            assert_eq!(
                stdout,
                if expected == 0 {
                    b"0\n".as_slice()
                } else {
                    b"1\n".as_slice()
                },
                "stdout for {args:?}"
            );
            assert!(stderr.is_empty(), "stderr for {args:?}");
            assert_eq!(status, i32::from(expected == 0), "status for {args:?}");
            assert!(backend.calls().is_empty(), "unexpected regex call");
        }
    }

    #[test]
    fn eval2_falls_back_to_raw_byte_order() {
        let cases: &[(&[&[u8]], i64)] = &[
            (&[b"abc", b"=", b"abc"], 1),
            (&[b"abc", b"!=", b"abd"], 1),
            (&[b"abc", b"<", b"abd"], 1),
            (&[b"abc", b"<=", b"abc"], 1),
            (&[b"abd", b">", b"abc"], 1),
            (&[b"def", b">=", b"abc"], 1),
            (&[b"", b"<", b"a"], 1),
            (&[b"\x7f", b"<", b"\x80"], 1),
            (&[b"\xff", b">", b"\x80"], 1),
            (&[b"12x", b"<", b"2"], 1),
            (&[b"02", b"<", b"1x"], 1),
            (&[b"9223372036854775808", b"<", b"99"], 1),
            (&[b"-9223372036854775809", b"<", b"-8"], 0),
            (&[b"2", b"+", b"8", b"<", b"2x"], 1),
            (&[b"2x", b">", b"2", b"+", b"8"], 1),
        ];

        for &(args, expected) in cases {
            assert_eq!(
                eval2_result(args),
                Ok(make_int(expected)),
                "raw-byte comparison {args:?}"
            );
        }
    }

    #[test]
    fn eval2_chains_comparisons_left_associatively() {
        let cases: &[(&[&[u8]], i64)] = &[
            (&[b"3", b"<", b"2", b"<", b"1"], 1),
            (&[b"3", b">", b"2", b">", b"1"], 0),
            (&[b"5", b"=", b"5", b"!=", b"0"], 1),
            (&[b"2", b"<", b"3", b">=", b"1"], 1),
            (&[b"z", b">", b"a", b"=", b"1"], 1),
            (&[b"z", b">", b"a", b">", b"00x"], 1),
            (&[b"a", b"<", b"z", b"<", b"00x"], 0),
        ];

        for &(args, expected) in cases {
            assert_eq!(
                eval2_result(args),
                Ok(make_int(expected)),
                "chained comparison {args:?}"
            );
        }
    }
    #[test]
    fn eval1_and_eval0_are_eager() {
        let division_error = ExprError {
            status: 2,
            message: b"division by zero".to_vec(),
        };
        for args in [
            &[b"0".as_slice(), b"&", b"8", b"/", b"0"][..],
            &[b"0".as_slice(), b"&", b"1", b"&", b"8", b"/", b"0"][..],
            &[b"1".as_slice(), b"|", b"8", b"/", b"0"][..],
            &[b"1".as_slice(), b"|", b"0", b"|", b"8", b"/", b"0"][..],
        ] {
            assert_eq!(
                eval0_result(args),
                Err(division_error.clone()),
                "eager arithmetic error for {args:?}"
            );
        }

        for args in [
            &[b"0".as_slice(), b"&", b")"][..],
            &[b"1".as_slice(), b"|", b")"][..],
        ] {
            assert_eq!(
                eval0_result(args),
                Err(error()),
                "eager syntax error for {args:?}"
            );
        }

        for args in [
            &[b"0".as_slice(), b"&", b"subject", b":", b"pattern"][..],
            &[b"1".as_slice(), b"|", b"subject", b":", b"pattern"][..],
        ] {
            let diagnostic = b"mock regular expression error".to_vec();
            let backend = FakeRegexBackend::new(vec![Err(RegexError {
                message: diagnostic.clone(),
            })]);
            let owned = owned_args(args);
            let mut parser = parser_with_fake(&owned, &backend);
            parser.nexttoken(false);

            assert_eq!(
                parser.eval0(),
                Err(ExprError {
                    status: 2,
                    message: diagnostic,
                }),
                "eager regex error for {args:?}"
            );
            assert_eq!(
                backend.calls(),
                vec![(b"pattern".to_vec(), b"subject".to_vec())]
            );
        }

        assert_eq!(
            eval1_result(&[b"first", b"&", b"second", b"&", b"third"]),
            Ok(make_str(b"first"))
        );
        assert_eq!(
            eval0_result(&[b"", b"|", b"second", b"|", b"third"]),
            Ok(make_str(b"second"))
        );
    }

    #[test]
    fn eval1_and_eval0_preserve_selected_operand() {
        assert_eq!(
            eval1_result(&[b"left", b"&", b"right"]),
            Ok(make_str(b"left"))
        );
        assert_eq!(eval1_result(&[b"left", b"&", b""]), Ok(make_int(0)));
        assert_eq!(eval1_result(&[b"", b"&", b"right"]), Ok(make_int(0)));
        assert_eq!(
            eval1_result(&[b"1", b"=", b"0", b"&", b"right"]),
            Ok(make_int(0))
        );

        assert_eq!(
            eval0_result(&[b"left", b"|", b"right"]),
            Ok(make_str(b"left"))
        );
        assert_eq!(eval0_result(&[b"", b"|", b"right"]), Ok(make_str(b"right")));
        assert_eq!(
            eval0_result(&[b"1", b"=", b"0", b"|", b"right"]),
            Ok(make_str(b"right"))
        );
        assert_eq!(
            eval0_result(&[b"", b"|", b"first", b"|", b"second"]),
            Ok(make_str(b"first"))
        );
        assert_eq!(
            eval0_result(&[b"9223372036854775808", b"|", b"fallback"]),
            Ok(make_str(b"9223372036854775808"))
        );
    }

    #[test]
    fn logical_truth_canonicalizes_numeric_strings() {
        assert_eq!(eval1_result(&[b"0002", b"&", b"right"]), Ok(make_int(2)));
        assert_eq!(
            eval1_result(&[b" \t+0002", b"&", b"right"]),
            Ok(make_int(2))
        );
        assert_eq!(eval1_result(&[b"000", b"&", b"right"]), Ok(make_int(0)));
        assert_eq!(eval1_result(&[b"left", b"&", b"-0"]), Ok(make_int(0)));

        assert_eq!(eval0_result(&[b"0002", b"|", b"fallback"]), Ok(make_int(2)));
        assert_eq!(
            eval0_result(&[b"000", b"|", b"fallback"]),
            Ok(make_str(b"fallback"))
        );
        assert_eq!(eval0_result(&[b"0", b"|", b"0002"]), Ok(make_str(b"0002")));
        assert_eq!(
            eval0_result(&[b"0", b"|", b"0002", b"|", b"fallback"]),
            Ok(make_int(2))
        );
        assert_eq!(
            eval0_result(&[b"0", b"|", b"000", b"|", b"fallback"]),
            Ok(make_str(b"fallback"))
        );
    }
    #[test]
    fn complete_grammar_respects_precedence() {
        let cases: &[(&[&[u8]], i64)] = &[
            (&[b"3", b"+", b"4", b"*", b"5", b"+", b"0"], 23),
            (
                &[
                    b"0", b"|", b"5", b"&", b"14", b"=", b"2", b"+", b"3", b"*", b"4",
                ],
                5,
            ),
            (
                &[
                    b"9", b">", b"2", b"+", b"3", b"*", b"2", b"&", b"4", b"|", b"8",
                ],
                1,
            ),
            (
                &[
                    b"0", b"|", b"0", b"&", b"1", b"=", b"1", b"+", b"2", b"*", b"3",
                ],
                0,
            ),
        ];

        for &(args, expected) in cases {
            assert_eq!(
                eval0_result(args),
                Ok(make_int(expected)),
                "complete expression {args:?}"
            );
        }
    }

    #[test]
    fn grouping_recurses_and_consumes_closing_token() {
        let cases: &[(&[&[u8]], i64)] = &[
            (&[b"(", b"3", b"+", b"4", b")"], 7),
            (&[b"(", b"2", b"+", b"(", b"3", b"*", b"4", b")", b")"], 14),
            (
                &[
                    b"(", b"2", b"+", b"3", b")", b"*", b"(", b"4", b"-", b"1", b")",
                ],
                15,
            ),
            (
                &[
                    b"(", b"2", b"+", b"3", b")", b"=", b"(", b"10", b"/", b"2", b")",
                ],
                1,
            ),
            (
                &[
                    b"(", b"0", b"|", b"7", b")", b"&", b"(", b"2", b">", b"1", b")",
                ],
                7,
            ),
        ];

        for &(args, expected) in cases {
            assert_eq!(
                eval0_result(args),
                Ok(make_int(expected)),
                "grouped expression {args:?}"
            );
        }

        let args = owned_args(&[b"(", b"2", b"+", b"3", b")", b"*", b"4"]);
        let backend = FakeRegexBackend::default();
        let mut parser = parser_with_fake(&args, &backend);
        parser.nexttoken(false);
        assert_eq!(parser.eval6(), Ok(make_int(5)));
        assert_eq!(parser.token, Token::Mul);
        assert_eq!(parser.index, 6);
        assert!(backend.calls().is_empty());
    }

    #[test]
    fn syntax_errors_cover_missing_extra_and_unmatched_tokens() {
        let cases: &[(&str, &[&[u8]])] = &[
            ("no arguments", &[]),
            ("operator only", &[b"+"]),
            ("unsupported unary minus", &[b"-", b"1"]),
            ("missing additive rhs", &[b"1", b"+"]),
            ("missing multiplicative rhs", &[b"1", b"*"]),
            ("missing comparison rhs", &[b"1", b"="]),
            ("missing logical-and rhs", &[b"1", b"&"]),
            ("missing logical-or rhs", &[b"1", b"|"]),
            ("missing match rhs", &[b"1", b":"]),
            ("empty group", &[b"(", b")"]),
            ("unmatched opening parenthesis", &[b"(", b"1"]),
            (
                "unmatched nested opening parenthesis",
                &[b"(", b"(", b"1", b")"],
            ),
            ("unmatched closing parenthesis", &[b")"]),
            ("extra closing parenthesis", &[b"1", b")"]),
            (
                "extra nested closing parenthesis",
                &[b"(", b"1", b")", b")"],
            ),
            ("closing parenthesis as rhs", &[b"1", b"+", b")"]),
            ("adjacent operands", &[b"1", b"2"]),
            ("operand after complete group", &[b"(", b"1", b")", b"2"]),
            ("trailing opening parenthesis", &[b"1", b"("]),
            ("trailing operand", &[b"1", b"+", b"2", b"3"]),
        ];

        for &(description, args) in cases {
            let args = owned_args(args);
            let backend = FakeRegexBackend::default();
            assert_eq!(
                evaluate(&args, &backend),
                Err(error()),
                "{description}: {args:?}"
            );
            assert!(
                backend.calls().is_empty(),
                "unexpected regex call for {description}"
            );
        }
    }

    #[test]
    fn eval5_is_anchored_and_pattern_shielded() {
        let args = owned_args(&[b"xxabc", b":", b"abc"]);
        let backend = FakeRegexBackend::new(vec![Ok(RegexMatch {
            capture_count: 0,
            whole_match: Some(2..5),
            first_capture: None,
        })]);
        let mut parser = parser_with_fake(&args, &backend);
        parser.nexttoken(false);
        assert_eq!(parser.eval5(), Ok(make_int(0)));
        assert_eq!(parser.token, Token::Eoi);
        assert_eq!(backend.calls(), vec![(b"abc".to_vec(), b"xxabc".to_vec())]);

        for &(pattern, _) in exact_operator_tokens() {
            let args = owned_args(&[b"x", b":", pattern]);
            let backend = FakeRegexBackend::new(vec![Ok(RegexMatch {
                capture_count: 0,
                whole_match: Some(0..1),
                first_capture: None,
            })]);
            let mut parser = parser_with_fake(&args, &backend);
            parser.nexttoken(false);

            assert_eq!(
                parser.eval5(),
                Ok(make_int(1)),
                "shielded pattern {pattern:?}"
            );
            assert_eq!(parser.token, Token::Eoi);
            assert_eq!(backend.calls(), vec![(pattern.to_vec(), b"x".to_vec())]);
        }
    }

    #[test]
    fn eval5_is_left_associative() {
        let args = owned_args(&[b"abcdef", b":", b"first", b":", b":"]);
        let backend = FakeRegexBackend::new(vec![
            Ok(RegexMatch {
                capture_count: 1,
                whole_match: Some(0..6),
                first_capture: Some(1..3),
            }),
            Ok(RegexMatch {
                capture_count: 0,
                whole_match: Some(0..2),
                first_capture: None,
            }),
        ]);
        let mut parser = parser_with_fake(&args, &backend);
        parser.nexttoken(false);

        assert_eq!(parser.eval5(), Ok(make_int(2)));
        assert_eq!(parser.token, Token::Eoi);
        assert_eq!(
            backend.calls(),
            vec![
                (b"first".to_vec(), b"abcdef".to_vec()),
                (b":".to_vec(), b"bc".to_vec()),
            ]
        );
    }

    #[test]
    fn eval5_selects_first_capture_or_match_length() {
        let cases = [
            (
                b"abcd".as_slice(),
                RegexMatch {
                    capture_count: 1,
                    whole_match: Some(0..4),
                    first_capture: Some(1..3),
                },
                make_str(b"bc"),
            ),
            (
                b"abcd".as_slice(),
                RegexMatch {
                    capture_count: 0,
                    whole_match: Some(0..4),
                    first_capture: None,
                },
                make_int(4),
            ),
            (
                b"abcd".as_slice(),
                RegexMatch {
                    capture_count: 2,
                    whole_match: Some(0..4),
                    first_capture: None,
                },
                make_int(4),
            ),
            (
                b"".as_slice(),
                RegexMatch {
                    capture_count: 0,
                    whole_match: Some(0..0),
                    first_capture: None,
                },
                make_int(0),
            ),
            (
                b"".as_slice(),
                RegexMatch {
                    capture_count: 1,
                    whole_match: Some(0..0),
                    first_capture: Some(0..0),
                },
                make_str(b""),
            ),
        ];

        for (subject, response, expected) in cases {
            let args = owned_args(&[subject, b":", b"pattern"]);
            let backend = FakeRegexBackend::new(vec![Ok(response)]);
            let mut parser = parser_with_fake(&args, &backend);
            parser.nexttoken(false);

            assert_eq!(parser.eval5(), Ok(expected), "subject {subject:?}");
            assert_eq!(parser.token, Token::Eoi);
            assert_eq!(
                backend.calls(),
                vec![(b"pattern".to_vec(), subject.to_vec())]
            );
        }

        for response in [
            RegexMatch {
                capture_count: 0,
                whole_match: Some(0..5),
                first_capture: None,
            },
            RegexMatch {
                capture_count: 1,
                whole_match: Some(0..4),
                first_capture: Some(2..5),
            },
            RegexMatch {
                capture_count: 0,
                whole_match: Some(0..4),
                first_capture: Some(1..2),
            },
            RegexMatch {
                capture_count: 1,
                whole_match: None,
                first_capture: Some(0..1),
            },
            RegexMatch {
                capture_count: 0,
                whole_match: Some(2..5),
                first_capture: None,
            },
        ] {
            let args = owned_args(&[b"abcd", b":", b"pattern"]);
            let backend = FakeRegexBackend::new(vec![Ok(response)]);
            let mut parser = parser_with_fake(&args, &backend);
            parser.nexttoken(false);
            assert_eq!(
                parser.eval5(),
                Err(ExprError {
                    status: 2,
                    message: b"Invalid regular expression".to_vec(),
                })
            );
        }
    }

    #[test]
    fn eval5_returns_capture_sensitive_misses() {
        let cases = [
            (
                RegexMatch {
                    capture_count: 0,
                    whole_match: None,
                    first_capture: None,
                },
                make_int(0),
            ),
            (
                RegexMatch {
                    capture_count: 2,
                    whole_match: None,
                    first_capture: None,
                },
                make_str(b""),
            ),
            (
                RegexMatch {
                    capture_count: 0,
                    whole_match: Some(2..4),
                    first_capture: None,
                },
                make_int(0),
            ),
            (
                RegexMatch {
                    capture_count: 1,
                    whole_match: Some(2..4),
                    first_capture: Some(2..4),
                },
                make_str(b""),
            ),
        ];

        for (response, expected) in cases {
            let args = owned_args(&[b"xxab", b":", b"pattern"]);
            let backend = FakeRegexBackend::new(vec![Ok(response)]);
            let mut parser = parser_with_fake(&args, &backend);
            parser.nexttoken(false);

            assert_eq!(parser.eval5(), Ok(expected));
            assert_eq!(parser.token, Token::Eoi);
            assert_eq!(
                backend.calls(),
                vec![(b"pattern".to_vec(), b"xxab".to_vec())]
            );
        }
    }

    #[test]
    fn eval5_propagates_backend_diagnostics() {
        let diagnostic = b"Invalid range end".to_vec();
        let args = owned_args(&[b"subject", b":", b"[z-a]"]);
        let backend = FakeRegexBackend::new(vec![Err(RegexError {
            message: diagnostic.clone(),
        })]);
        let mut parser = parser_with_fake(&args, &backend);
        parser.nexttoken(false);

        assert_eq!(
            parser.eval5(),
            Err(ExprError {
                status: 2,
                message: diagnostic,
            })
        );
        assert_eq!(parser.token, Token::Eoi);
        assert_eq!(
            backend.calls(),
            vec![(b"[z-a]".to_vec(), b"subject".to_vec())]
        );
    }
    #[test]
    fn cli_separates_stdout_stderr_and_statuses() {
        let cases: &[(&[&[u8]], &[u8], &[u8], i32)] = &[
            (&[b"7"], b"7\n", b"", 0),
            (&[b"0"], b"0\n", b"", 1),
            (&[], b"", b"expr: syntax error\n", 2),
            (
                &[b"abc", b"+", b"1"],
                b"",
                b"expr: number \"abc\" is invalid\n",
                2,
            ),
            (&[b"1", b"/", b"0"], b"", b"expr: division by zero\n", 2),
            (
                &[b"9223372036854775807", b"+", b"1"],
                b"",
                b"expr: overflow\n",
                3,
            ),
        ];

        for &(args, expected_stdout, expected_stderr, expected_status) in cases {
            let backend = FakeRegexBackend::default();
            let (stdout, stderr, status) = cli_output(b"/usr/bin/expr", args, &backend);
            assert_eq!(stdout, expected_stdout, "stdout for {args:?}");
            assert_eq!(stderr, expected_stderr, "stderr for {args:?}");
            assert_eq!(status, expected_status, "status for {args:?}");
            assert!(backend.calls().is_empty(), "unexpected regex call");
        }

        let backend = FakeRegexBackend::new(vec![Err(RegexError {
            message: b"Invalid range end".to_vec(),
        })]);
        let (stdout, stderr, status) =
            cli_output(b"/usr/bin/expr", &[b"subject", b":", b"[z-a]"], &backend);
        assert!(stdout.is_empty());
        assert_eq!(stderr, b"expr: Invalid range end\n");
        assert_eq!(status, 2);
        assert_eq!(
            backend.calls(),
            vec![(b"[z-a]".to_vec(), b"subject".to_vec())]
        );
    }

    #[test]
    fn cli_removes_exactly_one_leading_double_dash() {
        let cases: &[(&[&[u8]], &[u8], &[u8], i32)] = &[
            (&[b"--", b"7"], b"7\n", b"", 0),
            (&[b"--", b"--"], b"--\n", b"", 0),
            (&[b"--"], b"", b"expr: syntax error\n", 2),
            (&[b"--", b"--", b"7"], b"", b"expr: syntax error\n", 2),
            (&[b"---"], b"---\n", b"", 0),
            (&[b"--help"], b"--help\n", b"", 0),
            (&[b"-n"], b"-n\n", b"", 0),
        ];

        for &(args, expected_stdout, expected_stderr, expected_status) in cases {
            let backend = FakeRegexBackend::default();
            let (stdout, stderr, status) = cli_output(b"expr", args, &backend);
            assert_eq!(stdout, expected_stdout, "stdout for {args:?}");
            assert_eq!(stderr, expected_stderr, "stderr for {args:?}");
            assert_eq!(status, expected_status, "status for {args:?}");
            assert!(backend.calls().is_empty(), "unexpected regex call");
        }
    }

    #[test]
    fn cli_uses_raw_invoked_basename() {
        let cases: &[(&[u8], &[u8])] = &[
            (b"/usr/local/bin/expr", b"expr: syntax error\n"),
            (b"expr-alias", b"expr-alias: syntax error\n"),
            (b"/tmp/symlink-alias", b"symlink-alias: syntax error\n"),
            (b"", b": syntax error\n"),
            (b"/", b": syntax error\n"),
            (b"/tmp/\xffexpr", b"\xffexpr: syntax error\n"),
        ];

        for &(argv0, expected_stderr) in cases {
            let backend = FakeRegexBackend::default();
            let (stdout, stderr, status) = cli_output(argv0, &[], &backend);
            assert!(stdout.is_empty(), "stdout for argv0 {argv0:?}");
            assert_eq!(stderr, expected_stderr, "stderr for argv0 {argv0:?}");
            assert_eq!(status, 2, "status for argv0 {argv0:?}");
            assert!(backend.calls().is_empty(), "unexpected regex call");
        }
    }

    #[test]
    fn cli_preserves_invalid_utf8_arguments() {
        let backend = FakeRegexBackend::default();
        let (stdout, stderr, status) = cli_output(b"expr", &[b"\xffvalue"], &backend);
        assert_eq!(stdout, b"\xffvalue\n");
        assert!(stderr.is_empty());
        assert_eq!(status, 0);

        let backend = FakeRegexBackend::default();
        let (stdout, stderr, status) =
            cli_output(b"/tmp/\xfdexpr", &[b"\xfe", b"+", b"1"], &backend);
        assert!(stdout.is_empty());
        assert_eq!(
            stderr, b"\xfdexpr: number \"\xfe\" is invalid\n",
            "raw argv0 and operand bytes"
        );
        assert_eq!(status, 2);
    }

    #[test]
    fn cli_renders_before_final_truth() {
        let cases: &[(&[u8], &[u8], i32)] = &[
            (b"-0", b"-0\n", 1),
            (b"000", b"000\n", 1),
            (b"0002", b"0002\n", 0),
        ];

        for &(arg, expected_stdout, expected_status) in cases {
            let backend = FakeRegexBackend::default();
            let (stdout, stderr, status) = cli_output(b"expr", &[arg], &backend);
            assert_eq!(stdout, expected_stdout, "stdout for {arg:?}");
            assert!(stderr.is_empty(), "stderr for {arg:?}");
            assert_eq!(status, expected_status, "status for {arg:?}");
            assert!(backend.calls().is_empty(), "unexpected regex call");
        }
    }

    #[test]
    fn cli_has_no_stdin_or_filesystem_boundary() {
        let boundary: fn(
            &[u8],
            &[Vec<u8>],
            &dyn RegexBackend,
            &mut dyn Write,
            &mut dyn Write,
        ) -> io::Result<i32> = run_cli;
        let _ = boundary;

        let backend = FakeRegexBackend::default();
        let (stdout, stderr, status) =
            cli_output(b"expr", &[b"/path/that/does/not/exist"], &backend);
        assert_eq!(stdout, b"/path/that/does/not/exist\n");
        assert!(stderr.is_empty());
        assert_eq!(status, 0);
        assert!(backend.calls().is_empty());

        let args = owned_args(&[b"1"]);
        let mut stdout = FailingWriter;
        let mut stderr = Vec::new();
        let error = run_cli(b"expr", &args, &backend, &mut stdout, &mut stderr)
            .expect_err("stdout failures must be returned");
        assert_eq!(error.kind(), io::ErrorKind::BrokenPipe);
        assert!(stderr.is_empty());

        let args = Vec::new();
        let mut stdout = Vec::new();
        let mut stderr = FailingWriter;
        let error = run_cli(b"expr", &args, &backend, &mut stdout, &mut stderr)
            .expect_err("stderr failures must be returned");
        assert_eq!(error.kind(), io::ErrorKind::BrokenPipe);
        assert!(stdout.is_empty());
    }

    struct FailingWriter;

    impl Write for FailingWriter {
        fn write(&mut self, _buffer: &[u8]) -> io::Result<usize> {
            Err(io::Error::new(
                io::ErrorKind::BrokenPipe,
                "injected write failure",
            ))
        }

        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }

    fn cli_output(
        argv0: &[u8],
        args: &[&[u8]],
        backend: &FakeRegexBackend,
    ) -> (Vec<u8>, Vec<u8>, i32) {
        let mut stdout = Vec::new();
        let mut stderr = Vec::new();
        let status = run_cli(argv0, &owned_args(args), backend, &mut stdout, &mut stderr)
            .expect("in-memory writes must succeed");
        (stdout, stderr, status)
    }

    fn owned_args(args: &[&[u8]]) -> Vec<Vec<u8>> {
        args.iter().map(|arg| arg.to_vec()).collect()
    }

    #[test]
    fn reported_non_regex_failures_match_the_cli_contract() {
        let cases: &[(&[&[u8]], &[u8], &[u8], i32)] = &[
            (&[b"3", b">=", b"5"], b"0\n", b"", 1),
            (&[b"5", b">=", b"3"], b"1\n", b"", 0),
            (
                &[b"abc", b"+", b"1"],
                b"",
                b"main: number \"abc\" is invalid\n",
                2,
            ),
            (&[b"2", b"-", b"5"], b"-3\n", b"", 0),
            (&[b"def", b">=", b"abc"], b"1\n", b"", 0),
            (&[b"3", b"+", b"-2"], b"1\n", b"", 0),
            (&[b"6", b"/", b"2"], b"3\n", b"", 0),
            (&[b"3", b"+", b"4", b"*", b"5", b"+", b"0"], b"23\n", b"", 0),
            (&[b"(", b"3", b"+", b"4", b")"], b"7\n", b"", 0),
            (&[b"2", b"*", b"3"], b"6\n", b"", 0),
            (&[b"1", b"&", b"2"], b"1\n", b"", 0),
            (&[b"1", b"&", b"0"], b"0\n", b"", 1),
        ];

        for (args, expected_stdout, expected_stderr, expected_status) in cases {
            let backend = FakeRegexBackend::new(Vec::new());
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let status = run_cli(
                b"./main",
                &owned_args(args),
                &backend,
                &mut stdout,
                &mut stderr,
            )
            .expect("in-memory writes must succeed");
            assert_eq!(stdout, *expected_stdout, "stdout for {args:?}");
            assert_eq!(stderr, *expected_stderr, "stderr for {args:?}");
            assert_eq!(status, *expected_status, "status for {args:?}");
            assert!(backend.calls().is_empty(), "unexpected regex call");
        }
    }

    #[test]
    fn reported_regex_misses_use_capture_sensitive_results() {
        let cases: &[(&[&[u8]], RegexMatch, &[u8], i32, (&[u8], &[u8]))] = &[
            (
                &[b"hello", b":", b"world"],
                RegexMatch {
                    capture_count: 0,
                    whole_match: None,
                    first_capture: None,
                },
                b"0\n",
                1,
                (b"world", b"hello"),
            ),
            (
                &[b"hello", b":", br"h\(xyz\)o"],
                RegexMatch {
                    capture_count: 1,
                    whole_match: None,
                    first_capture: None,
                },
                b"\n",
                1,
                (br"h\(xyz\)o", b"hello"),
            ),
            (
                &[b"", b":", b"hello"],
                RegexMatch {
                    capture_count: 0,
                    whole_match: None,
                    first_capture: None,
                },
                b"0\n",
                1,
                (b"hello", b""),
            ),
        ];

        for (args, response, expected_stdout, expected_status, expected_call) in cases {
            let backend = FakeRegexBackend::new(vec![Ok(response.clone())]);
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let status = run_cli(
                b"./main",
                &owned_args(args),
                &backend,
                &mut stdout,
                &mut stderr,
            )
            .expect("in-memory writes must succeed");
            assert_eq!(stdout, *expected_stdout, "stdout for {args:?}");
            assert!(stderr.is_empty(), "stderr for {args:?}");
            assert_eq!(status, *expected_status, "status for {args:?}");
            assert_eq!(
                backend.calls(),
                vec![(expected_call.0.to_vec(), expected_call.1.to_vec())]
            );
        }
    }
}
