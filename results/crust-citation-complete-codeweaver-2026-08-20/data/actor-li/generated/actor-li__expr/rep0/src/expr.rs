use std::cmp::Ordering;
use std::io::Write;

use crate::posix_bre::{RegexCompileError, RegexEngine};

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum Val {
    Integer(i64),
    String(Vec<u8>),
}

impl Val {
    pub(crate) fn make_int(value: i64) -> Self {
        Self::Integer(value)
    }

    pub(crate) fn make_str(value: Vec<u8>) -> Self {
        Self::String(value)
    }

    pub(crate) fn is_integer(&self) -> Result<i64, NumberError> {
        match self {
            Self::Integer(value) => Ok(*value),
            Self::String(value) => parse_i64_decimal(value),
        }
    }

    pub(crate) fn to_integer(&mut self) -> Result<(), NumberError> {
        let value = match self {
            Self::Integer(_) => return Ok(()),
            Self::String(value) => parse_i64_decimal(value)?,
        };
        *self = Self::Integer(value);
        Ok(())
    }

    pub(crate) fn to_string(&mut self) -> &[u8] {
        let rendered = match self {
            Self::Integer(value) => Some(value.to_string().into_bytes()),
            Self::String(_) => None,
        };
        if let Some(rendered) = rendered {
            *self = Self::String(rendered);
        }

        match self {
            Self::String(value) => value,
            Self::Integer(_) => unreachable!("integer value was converted to a string"),
        }
    }

    pub(crate) fn is_zero_or_null(&mut self) -> bool {
        match self {
            Self::Integer(value) => return *value == 0,
            Self::String(value) if value.is_empty() => return true,
            Self::String(_) => {}
        }

        self.to_integer().is_ok() && matches!(self, Self::Integer(0))
    }

    pub(crate) fn output_bytes(&self) -> Vec<u8> {
        match self {
            Self::Integer(value) => value.to_string().into_bytes(),
            Self::String(value) => value.clone(),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum NumberError {
    Invalid,
    TooSmall,
    TooLarge,
}

pub(crate) fn parse_i64_decimal(value: &[u8]) -> Result<i64, NumberError> {
    let mut position = 0;
    while value
        .get(position)
        .is_some_and(|byte| matches!(byte, b' ' | b'\t' | b'\n' | 0x0b | 0x0c | b'\r'))
    {
        position += 1;
    }

    let negative = match value.get(position) {
        Some(b'-') => {
            position += 1;
            true
        }
        Some(b'+') => {
            position += 1;
            false
        }
        _ => false,
    };

    let digit_start = position;
    let limit = if negative {
        (i64::MAX as u64) + 1
    } else {
        i64::MAX as u64
    };
    let mut magnitude = 0_u64;
    let mut out_of_range = false;

    while let Some(&byte) = value.get(position) {
        if !byte.is_ascii_digit() {
            return Err(NumberError::Invalid);
        }

        if !out_of_range {
            let digit = u64::from(byte - b'0');
            match magnitude
                .checked_mul(10)
                .and_then(|number| number.checked_add(digit))
            {
                Some(number) if number <= limit => magnitude = number,
                _ => out_of_range = true,
            }
        }
        position += 1;
    }

    if position == digit_start {
        return Err(NumberError::Invalid);
    }
    if out_of_range {
        return Err(if negative {
            NumberError::TooSmall
        } else {
            NumberError::TooLarge
        });
    }

    if negative {
        if magnitude == (i64::MAX as u64) + 1 {
            Ok(i64::MIN)
        } else {
            Ok(-(magnitude as i64))
        }
    } else {
        Ok(magnitude as i64)
    }
}

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
    LParen,
    RParen,
    Ne,
    Le,
    Ge,
    Operand,
    Eoi,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum ExprError {
    Syntax,
    Number { operand: Vec<u8>, kind: NumberError },
    DivisionByZero,
    RegexCompile(RegexCompileError),
    Overflow,
    System { message: Vec<u8> },
}

impl ExprError {
    pub(crate) fn status(&self) -> i32 {
        match self {
            Self::Syntax | Self::Number { .. } | Self::DivisionByZero | Self::RegexCompile(_) => 2,
            Self::Overflow | Self::System { .. } => 3,
        }
    }

    pub(crate) fn message(&self) -> Vec<u8> {
        match self {
            Self::Syntax => b"syntax error".to_vec(),
            Self::Number { operand, kind } => {
                let mut message = b"number \"".to_vec();
                message.extend_from_slice(operand);
                message.extend_from_slice(b"\" is ");
                message.extend_from_slice(match kind {
                    NumberError::Invalid => b"invalid",
                    NumberError::TooSmall => b"too small",
                    NumberError::TooLarge => b"too large",
                });
                message
            }
            Self::DivisionByZero => b"division by zero".to_vec(),
            Self::RegexCompile(error) => error.message.clone(),
            Self::Overflow => b"overflow".to_vec(),
            Self::System { message } => message.clone(),
        }
    }
}

pub(crate) struct Parser<'engine> {
    argv: Vec<Vec<u8>>,
    position: usize,
    token: Token,
    tokval: Option<Val>,
    regex_engine: &'engine dyn RegexEngine,
}

impl<'engine> Parser<'engine> {
    pub(crate) fn new(argv: Vec<Vec<u8>>, regex_engine: &'engine dyn RegexEngine) -> Self {
        Self {
            argv,
            position: 0,
            token: Token::Eoi,
            tokval: None,
            regex_engine,
        }
    }

    pub(crate) fn nexttoken(&mut self, pattern_operand: bool) -> Result<(), ExprError> {
        self.tokval = None;
        let Some(value) = self.argv.get(self.position).cloned() else {
            self.token = Token::Eoi;
            return Ok(());
        };
        self.position += 1;

        if !pattern_operand {
            self.token = match value.as_slice() {
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
                b"(" => Token::LParen,
                b")" => Token::RParen,
                b"!=" => Token::Ne,
                b"<=" => Token::Le,
                b">=" => Token::Ge,
                _ => Token::Operand,
            };
            if self.token != Token::Operand {
                return Ok(());
            }
        }

        self.token = Token::Operand;
        self.tokval = Some(Val::make_str(value));
        Ok(())
    }

    pub(crate) fn eval6(&mut self) -> Result<Val, ExprError> {
        match self.token {
            Token::Operand => {
                let value = self.tokval.take().ok_or(ExprError::Syntax)?;
                self.nexttoken(false)?;
                Ok(value)
            }
            Token::LParen => {
                self.nexttoken(false)?;
                let value = self.eval0()?;
                if self.token != Token::RParen {
                    return Err(ExprError::Syntax);
                }
                self.nexttoken(false)?;
                Ok(value)
            }
            _ => Err(ExprError::Syntax),
        }
    }

    pub(crate) fn eval5(&mut self) -> Result<Val, ExprError> {
        let mut left = self.eval6()?;
        while self.token == Token::Match {
            self.nexttoken(true)?;
            let mut right = self.eval6()?;

            let input = left.to_string().to_vec();
            let pattern = right.to_string().to_vec();
            let outcome = self
                .regex_engine
                .execute(&input, &pattern)
                .map_err(ExprError::RegexCompile)?;

            left = match outcome.whole_match.filter(|span| span.start == 0) {
                Some(whole_match) => {
                    if whole_match.start > whole_match.end || whole_match.end > input.len() {
                        return Err(ExprError::System {
                            message: b"invalid regular expression match span".to_vec(),
                        });
                    }
                    if let Some(first_capture) = outcome.first_capture {
                        if first_capture.start > first_capture.end
                            || first_capture.start < whole_match.start
                            || first_capture.end > whole_match.end
                        {
                            return Err(ExprError::System {
                                message: b"invalid regular expression match span".to_vec(),
                            });
                        }
                        let capture = input
                            .get(first_capture.start..first_capture.end)
                            .ok_or_else(|| ExprError::System {
                                message: b"invalid regular expression match span".to_vec(),
                            })?;
                        Val::make_str(capture.to_vec())
                    } else {
                        let length =
                            whole_match
                                .end
                                .checked_sub(whole_match.start)
                                .ok_or_else(|| ExprError::System {
                                    message: b"invalid regular expression match span".to_vec(),
                                })?;
                        let length = i64::try_from(length).map_err(|_| ExprError::System {
                            message: b"regular expression match is too long".to_vec(),
                        })?;
                        Val::make_int(length)
                    }
                }
                None if outcome.capture_count == 0 => Val::make_int(0),
                None => Val::make_str(Vec::new()),
            };
        }
        Ok(left)
    }

    pub(crate) fn eval4(&mut self) -> Result<Val, ExprError> {
        let mut left = self.eval5()?;
        while matches!(self.token, Token::Mul | Token::Div | Token::Mod) {
            let operator = self.token;
            self.nexttoken(false)?;
            let mut right = self.eval5()?;

            let left_number = coerce_arithmetic_operand(&mut left)?;
            let right_number = coerce_arithmetic_operand(&mut right)?;
            let result = match operator {
                Token::Mul => left_number
                    .checked_mul(right_number)
                    .ok_or(ExprError::Overflow)?,
                Token::Div => {
                    if right_number == 0 {
                        return Err(ExprError::DivisionByZero);
                    }
                    if left_number == i64::MIN && right_number == -1 {
                        return Err(ExprError::Overflow);
                    }
                    left_number / right_number
                }
                Token::Mod => {
                    if right_number == 0 {
                        return Err(ExprError::DivisionByZero);
                    }
                    if left_number == i64::MIN && right_number == -1 {
                        0
                    } else {
                        left_number % right_number
                    }
                }
                _ => unreachable!("multiplicative loop accepted a different operator"),
            };
            left = Val::make_int(result);
        }
        Ok(left)
    }

    pub(crate) fn eval3(&mut self) -> Result<Val, ExprError> {
        let mut left = self.eval4()?;
        while matches!(self.token, Token::Add | Token::Sub) {
            let operator = self.token;
            self.nexttoken(false)?;
            let mut right = self.eval4()?;

            let left_number = coerce_arithmetic_operand(&mut left)?;
            let right_number = coerce_arithmetic_operand(&mut right)?;
            let result = match operator {
                Token::Add => left_number
                    .checked_add(right_number)
                    .ok_or(ExprError::Overflow)?,
                Token::Sub => left_number
                    .checked_sub(right_number)
                    .ok_or(ExprError::Overflow)?,
                _ => unreachable!("additive loop accepted a different operator"),
            };
            left = Val::make_int(result);
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
            self.nexttoken(false)?;
            let mut right = self.eval3()?;

            let ordering = match (left.is_integer(), right.is_integer()) {
                (Ok(left_number), Ok(right_number)) => left_number.cmp(&right_number),
                _ => left.to_string().cmp(right.to_string()),
            };
            let result = match operator {
                Token::Eq => ordering == Ordering::Equal,
                Token::Ne => ordering != Ordering::Equal,
                Token::Lt => ordering == Ordering::Less,
                Token::Gt => ordering == Ordering::Greater,
                Token::Le => ordering != Ordering::Greater,
                Token::Ge => ordering != Ordering::Less,
                _ => unreachable!("comparison loop accepted a different operator"),
            };
            left = Val::make_int(i64::from(result));
        }
        Ok(left)
    }

    pub(crate) fn eval1(&mut self) -> Result<Val, ExprError> {
        let mut left = self.eval2()?;
        while self.token == Token::And {
            self.nexttoken(false)?;
            let mut right = self.eval2()?;

            if left.is_zero_or_null() || right.is_zero_or_null() {
                left = Val::make_int(0);
            }
        }
        Ok(left)
    }

    pub(crate) fn eval0(&mut self) -> Result<Val, ExprError> {
        let mut left = self.eval1()?;
        while self.token == Token::Or {
            self.nexttoken(false)?;
            let right = self.eval1()?;
            if left.is_zero_or_null() {
                left = right;
            }
        }
        Ok(left)
    }
}

fn coerce_arithmetic_operand(value: &mut Val) -> Result<i64, ExprError> {
    if let Err(kind) = value.to_integer() {
        let operand = match value {
            Val::String(value) => value.clone(),
            Val::Integer(_) => unreachable!("failed integer conversion changed the value"),
        };
        return Err(ExprError::Number { operand, kind });
    }

    match value {
        Val::Integer(value) => Ok(*value),
        Val::String(_) => unreachable!("successful integer conversion retained a string"),
    }
}

pub fn run(
    program_name: &[u8],
    mut expression_args: Vec<Vec<u8>>,
    regex_engine: &dyn RegexEngine,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
) -> i32 {
    if expression_args
        .first()
        .is_some_and(|argument| argument == b"--")
    {
        expression_args.remove(0);
    }

    let result = (|| {
        let mut parser = Parser::new(expression_args, regex_engine);
        parser.nexttoken(false)?;
        let value = parser.eval0()?;
        if parser.token != Token::Eoi {
            return Err(ExprError::Syntax);
        }
        Ok(value)
    })();

    match result {
        Ok(mut value) => {
            let mut output = value.output_bytes();
            output.push(b'\n');
            let _ = stdout.write_all(&output);
            i32::from(value.is_zero_or_null())
        }
        Err(error) => {
            let basename = program_name
                .rsplit(|byte| *byte == b'/')
                .next()
                .unwrap_or(program_name);
            let mut diagnostic = basename.to_vec();
            diagnostic.extend_from_slice(b": ");
            diagnostic.extend_from_slice(&error.message());
            diagnostic.push(b'\n');
            let _ = stderr.write_all(&diagnostic);
            error.status()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{parse_i64_decimal, run, ExprError, NumberError, Parser, Token, Val};
    use crate::posix_bre::mock::{MockRegexEngine, RegexCall};
    use crate::{RegexCompileError, RegexOutcome, Span};

    fn run_case(args: &[&[u8]], regex_engine: &MockRegexEngine) -> (i32, Vec<u8>, Vec<u8>) {
        run_case_with_program(b"/tmp/main", args, regex_engine)
    }

    fn run_case_with_program(
        program_name: &[u8],
        args: &[&[u8]],
        regex_engine: &MockRegexEngine,
    ) -> (i32, Vec<u8>, Vec<u8>) {
        let mut stdout = Vec::new();
        let mut stderr = Vec::new();
        let status = run(
            program_name,
            args.iter().map(|argument| argument.to_vec()).collect(),
            regex_engine,
            &mut stdout,
            &mut stderr,
        );
        (status, stdout, stderr)
    }

    #[test]
    fn parser_and_mock_seams_compile() {
        let regex_engine = MockRegexEngine::default();
        let _parser = Parser::new(Vec::new(), &regex_engine);
    }

    mod number_tests {
        use super::{parse_i64_decimal, NumberError};

        #[test]
        fn accepts_source_decimal_grammar_and_i64_endpoints() {
            let cases: &[(&[u8], i64)] = &[
                (b"0", 0),
                (b"+0", 0),
                (b"-0", 0),
                (b"+17", 17),
                (b"-17", -17),
                (b"00042", 42),
                (b" \t\n\x0b\x0c\r-2", -2),
                (b"-9223372036854775808", i64::MIN),
                (b"9223372036854775807", i64::MAX),
            ];

            for &(input, expected) in cases {
                assert_eq!(parse_i64_decimal(input), Ok(expected), "{input:?}");
            }

            for whitespace in [b' ', b'\t', b'\n', 0x0b, 0x0c, b'\r'] {
                let input = [whitespace, b'+', b'4', b'2'];
                assert_eq!(parse_i64_decimal(&input), Ok(42), "{input:?}");
            }
        }

        #[test]
        fn accepts_arbitrarily_long_zero_padding_without_false_overflow() {
            let zero = vec![b'0'; 16_384];
            assert_eq!(parse_i64_decimal(&zero), Ok(0));

            let mut maximum = vec![b'0'; 8_192];
            maximum.extend_from_slice(b"9223372036854775807");
            assert_eq!(parse_i64_decimal(&maximum), Ok(i64::MAX));

            let mut minimum = vec![b'-'];
            minimum.extend(std::iter::repeat(b'0').take(8_192));
            minimum.extend_from_slice(b"9223372036854775808");
            assert_eq!(parse_i64_decimal(&minimum), Ok(i64::MIN));
        }

        #[test]
        fn distinguishes_both_range_directions() {
            assert_eq!(
                parse_i64_decimal(b"9223372036854775808"),
                Err(NumberError::TooLarge)
            );
            assert_eq!(
                parse_i64_decimal(b"-9223372036854775809"),
                Err(NumberError::TooSmall)
            );

            let too_large = vec![b'9'; 4_096];
            assert_eq!(parse_i64_decimal(&too_large), Err(NumberError::TooLarge));

            let mut too_small = vec![b'-'];
            too_small.extend(std::iter::repeat(b'9').take(4_096));
            assert_eq!(parse_i64_decimal(&too_small), Err(NumberError::TooSmall));
        }

        #[test]
        fn rejects_missing_digits_and_every_trailing_byte() {
            let invalid: &[&[u8]] = &[
                b"", b" ", b"+", b"-", b" +", b" --1", b"1x", b"0+", b"\xff", b"12\xff", b"12\0",
            ];
            for &input in invalid {
                assert_eq!(
                    parse_i64_decimal(input),
                    Err(NumberError::Invalid),
                    "{input:?}"
                );
            }

            for whitespace in [b' ', b'\t', b'\n', 0x0b, 0x0c, b'\r'] {
                let input = [b'7', whitespace];
                assert_eq!(
                    parse_i64_decimal(&input),
                    Err(NumberError::Invalid),
                    "{input:?}"
                );
            }

            let mut overflow_then_invalid = vec![b'9'; 256];
            overflow_then_invalid.push(b'x');
            assert_eq!(
                parse_i64_decimal(&overflow_then_invalid),
                Err(NumberError::Invalid)
            );
        }
    }

    mod value_tests {
        use super::{NumberError, Val};

        #[test]
        fn constructors_and_output_preserve_owned_value_bytes() {
            assert_eq!(Val::make_int(-7), Val::Integer(-7));
            assert_eq!(
                Val::make_str(vec![b'a', 0xff, 0, b'z']),
                Val::String(vec![b'a', 0xff, 0, b'z'])
            );
            assert_eq!(
                Val::make_int(i64::MIN).output_bytes(),
                i64::MIN.to_string().as_bytes()
            );
            assert_eq!(
                Val::make_str(vec![0xff, b'\n']).output_bytes(),
                vec![0xff, b'\n']
            );
        }

        #[test]
        fn integer_recognition_is_non_mutating_and_conversion_canonicalizes() {
            let mut value = Val::make_str(b" \t+00012".to_vec());
            assert_eq!(value.is_integer(), Ok(12));
            assert_eq!(value, Val::make_str(b" \t+00012".to_vec()));

            assert_eq!(value.to_integer(), Ok(()));
            assert_eq!(value, Val::make_int(12));
            assert_eq!(value.to_string(), b"12");
            assert_eq!(value, Val::make_str(b"12".to_vec()));
        }

        #[test]
        fn failed_integer_conversion_does_not_mutate_the_string() {
            let mut invalid = Val::make_str(b"12 ".to_vec());
            assert_eq!(invalid.to_integer(), Err(NumberError::Invalid));
            assert_eq!(invalid, Val::make_str(b"12 ".to_vec()));

            let mut too_large = Val::make_str(b"9223372036854775808".to_vec());
            assert_eq!(too_large.to_integer(), Err(NumberError::TooLarge));
            assert_eq!(too_large, Val::make_str(b"9223372036854775808".to_vec()));
        }

        #[test]
        fn truth_coercion_is_in_place_for_numeric_strings() {
            let mut integer_zero = Val::make_int(0);
            assert!(integer_zero.is_zero_or_null());
            assert_eq!(integer_zero, Val::make_int(0));

            let mut integer_nonzero = Val::make_int(-1);
            assert!(!integer_nonzero.is_zero_or_null());

            let mut empty = Val::make_str(Vec::new());
            assert!(empty.is_zero_or_null());
            assert_eq!(empty, Val::make_str(Vec::new()));

            let mut zero = Val::make_str(b"+0".to_vec());
            assert_eq!(zero.output_bytes(), b"+0");
            assert!(zero.is_zero_or_null());
            assert_eq!(zero, Val::make_int(0));

            let mut negative_zero = Val::make_str(b"-000".to_vec());
            assert!(negative_zero.is_zero_or_null());
            assert_eq!(negative_zero, Val::make_int(0));

            let mut nonzero = Val::make_str(b"01".to_vec());
            assert!(!nonzero.is_zero_or_null());
            assert_eq!(nonzero, Val::make_int(1));

            let mut non_number = Val::make_str(vec![0xff]);
            assert!(!non_number.is_zero_or_null());
            assert_eq!(non_number, Val::make_str(vec![0xff]));
        }

        #[test]
        fn truth_conversion_uses_the_complete_source_numeric_grammar() {
            let mut whitespace_zero = Val::make_str(b" \t\n\x0b\x0c\r+000".to_vec());
            assert!(whitespace_zero.is_zero_or_null());
            assert_eq!(whitespace_zero, Val::make_int(0));

            let mut signed_nonzero = Val::make_str(b" \t-0007".to_vec());
            assert!(!signed_nonzero.is_zero_or_null());
            assert_eq!(signed_nonzero, Val::make_int(-7));

            let mut trailing_whitespace = Val::make_str(b"0 ".to_vec());
            assert!(!trailing_whitespace.is_zero_or_null());
            assert_eq!(trailing_whitespace, Val::make_str(b"0 ".to_vec()));

            let mut too_large = Val::make_str(b"9223372036854775808".to_vec());
            assert!(!too_large.is_zero_or_null());
            assert_eq!(too_large, Val::make_str(b"9223372036854775808".to_vec()));
        }
    }

    mod lexer_tests {
        use super::{MockRegexEngine, Parser, Token, Val};

        fn lex_one(value: &[u8], pattern_operand: bool) -> (Token, Option<Val>) {
            let regex_engine = MockRegexEngine::default();
            let mut parser = Parser::new(vec![value.to_vec()], &regex_engine);
            parser.nexttoken(pattern_operand).unwrap();
            (parser.token, parser.tokval)
        }

        #[test]
        fn recognizes_only_the_exact_operator_argv_elements() {
            let operators: &[(&[u8], Token)] = &[
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
                (b"(", Token::LParen),
                (b")", Token::RParen),
                (b"!=", Token::Ne),
                (b"<=", Token::Le),
                (b">=", Token::Ge),
            ];

            for &(spelling, expected) in operators {
                assert_eq!(lex_one(spelling, false), (expected, None), "{spelling:?}");
            }
        }

        #[test]
        fn preserves_empty_multibyte_and_near_miss_arguments_as_operands() {
            let operands: &[&[u8]] = &[
                b"",
                b"==",
                b"!",
                b"=>",
                b"=<",
                b"||",
                b"++",
                b"--",
                b"word with spaces",
                b"\xff=",
            ];

            for &operand in operands {
                assert_eq!(
                    lex_one(operand, false),
                    (Token::Operand, Some(Val::make_str(operand.to_vec()))),
                    "{operand:?}"
                );
            }
        }

        #[test]
        fn consumes_exactly_one_argument_per_token() {
            let regex_engine = MockRegexEngine::default();
            let mut parser = Parser::new(
                vec![b"left right".to_vec(), b"+".to_vec(), b"tail".to_vec()],
                &regex_engine,
            );

            parser.nexttoken(false).unwrap();
            assert_eq!(parser.token, Token::Operand);
            assert_eq!(parser.tokval, Some(Val::make_str(b"left right".to_vec())));

            parser.nexttoken(false).unwrap();
            assert_eq!(parser.token, Token::Add);
            assert_eq!(parser.tokval, None);

            parser.nexttoken(false).unwrap();
            assert_eq!(parser.token, Token::Operand);
            assert_eq!(parser.tokval, Some(Val::make_str(b"tail".to_vec())));

            parser.nexttoken(false).unwrap();
            assert_eq!(parser.token, Token::Eoi);
            assert_eq!(parser.tokval, None);
        }

        #[test]
        fn pattern_mode_forces_operator_looking_arguments_to_operands() {
            let spellings: &[&[u8]] = &[
                b"|", b"&", b"=", b"<", b">", b"+", b"-", b"*", b"/", b"%", b":", b"(", b")",
                b"!=", b"<=", b">=",
            ];
            for &spelling in spellings {
                assert_eq!(
                    lex_one(spelling, true),
                    (Token::Operand, Some(Val::make_str(spelling.to_vec()))),
                    "{spelling:?}"
                );
            }

            let regex_engine = MockRegexEngine::default();
            let mut parser = Parser::new(Vec::new(), &regex_engine);
            parser.nexttoken(true).unwrap();
            assert_eq!(parser.token, Token::Eoi);
            assert_eq!(parser.tokval, None);
        }
    }

    mod eval6_primary_tests {
        use super::{run_case, ExprError, MockRegexEngine, Parser, Token, Val};

        #[test]
        fn returns_one_owned_operand_and_advances_once() {
            let regex_engine = MockRegexEngine::default();
            let mut parser =
                Parser::new(vec![vec![0xff, b'a'], b"trailing".to_vec()], &regex_engine);
            parser.nexttoken(false).unwrap();

            assert_eq!(parser.eval6(), Ok(Val::make_str(vec![0xff, b'a'])));
            assert_eq!(parser.token, Token::Operand);
            assert_eq!(parser.tokval, Some(Val::make_str(b"trailing".to_vec())));
        }

        #[test]
        fn evaluates_nested_parentheses_and_advances_past_each_closing_token() {
            let regex_engine = MockRegexEngine::default();
            let mut parser = Parser::new(
                [
                    b"(".as_slice(),
                    b"(".as_slice(),
                    b"2".as_slice(),
                    b"+".as_slice(),
                    b"3".as_slice(),
                    b")".as_slice(),
                    b"*".as_slice(),
                    b"4".as_slice(),
                    b")".as_slice(),
                    b"trailing".as_slice(),
                ]
                .into_iter()
                .map(<[u8]>::to_vec)
                .collect(),
                &regex_engine,
            );
            parser.nexttoken(false).unwrap();

            assert_eq!(parser.eval6(), Ok(Val::make_int(20)));
            assert_eq!(parser.token, Token::Operand);
            assert_eq!(parser.tokval, Some(Val::make_str(b"trailing".to_vec())));
        }

        #[test]
        fn grouping_overrides_additive_and_multiplicative_precedence() {
            let regex_engine = MockRegexEngine::default();
            for (args, expected) in [
                (
                    [b"(".as_slice(), b"2", b"+", b"3", b")", b"*", b"4"].as_slice(),
                    b"20\n".as_slice(),
                ),
                (
                    [b"2".as_slice(), b"*", b"(", b"3", b"+", b"4", b")"].as_slice(),
                    b"14\n".as_slice(),
                ),
                (
                    [
                        b"(".as_slice(),
                        b"20",
                        b"-",
                        b"8",
                        b")",
                        b"/",
                        b"(",
                        b"2",
                        b"+",
                        b"1",
                        b")",
                    ]
                    .as_slice(),
                    b"4\n".as_slice(),
                ),
            ] {
                assert_eq!(
                    run_case(args, &regex_engine),
                    (0, expected.to_vec(), Vec::new()),
                    "{args:?}"
                );
            }
        }

        #[test]
        fn rejects_absent_operator_and_unmatched_parenthesis_primaries() {
            let regex_engine = MockRegexEngine::default();

            let mut empty = Parser::new(Vec::new(), &regex_engine);
            empty.nexttoken(false).unwrap();
            assert_eq!(empty.eval6(), Err(ExprError::Syntax));

            for &argument in &[b"+".as_slice(), b":", b")", b"("] {
                let mut parser = Parser::new(vec![argument.to_vec()], &regex_engine);
                parser.nexttoken(false).unwrap();
                assert_eq!(parser.eval6(), Err(ExprError::Syntax), "{argument:?}");
            }
        }

        #[test]
        fn rejects_empty_missing_extra_and_mismatched_parentheses() {
            let regex_engine = MockRegexEngine::default();
            let cases: &[&[&[u8]]] = &[
                &[b"(", b")"],
                &[b"(", b"(", b")", b")"],
                &[b"(", b"1"],
                &[b"(", b"(", b"1", b")"],
                &[b"1", b")"],
                &[b"(", b"1", b")", b")"],
                &[b"(", b"1", b")", b"("],
                &[b")", b"1", b"("],
            ];

            for &args in cases {
                assert_eq!(
                    run_case(args, &regex_engine),
                    (2, Vec::new(), b"main: syntax error\n".to_vec()),
                    "{args:?}"
                );
            }
        }

        #[test]
        fn complete_expression_check_rejects_missing_and_extra_operands() {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case(&[b"left", b"right"], &regex_engine),
                (2, Vec::new(), b"main: syntax error\n".to_vec())
            );
            assert_eq!(
                run_case(&[b"left", b"+"], &regex_engine),
                (2, Vec::new(), b"main: syntax error\n".to_vec())
            );
            assert_eq!(
                run_case(&[b"(", b"left"], &regex_engine),
                (2, Vec::new(), b"main: syntax error\n".to_vec())
            );
        }

        #[test]
        fn forced_pattern_operand_can_be_consumed_as_a_primary() {
            let regex_engine = MockRegexEngine::default();
            let mut parser = Parser::new(vec![b")".to_vec()], &regex_engine);
            parser.nexttoken(true).unwrap();
            assert_eq!(parser.eval6(), Ok(Val::make_str(b")".to_vec())));
            assert_eq!(parser.token, Token::Eoi);
        }
    }

    mod eval5_match_tests {
        use super::{run_case, MockRegexEngine, RegexCall, RegexCompileError, RegexOutcome, Span};

        fn plain_match(end: usize) -> RegexOutcome {
            RegexOutcome {
                capture_count: 0,
                whole_match: Some(Span { start: 0, end }),
                first_capture: None,
            }
        }

        #[test]
        fn no_match_type_depends_on_capture_count() {
            let plain = MockRegexEngine::with_responses([Ok(RegexOutcome {
                capture_count: 0,
                whole_match: None,
                first_capture: None,
            })]);
            assert_eq!(
                run_case(&[b"hello", b":", b"world"], &plain),
                (1, b"0\n".to_vec(), Vec::new())
            );

            let grouped = MockRegexEngine::with_responses([Ok(RegexOutcome {
                capture_count: 1,
                whole_match: None,
                first_capture: None,
            })]);
            assert_eq!(
                run_case(&[b"hello", b":", b"h\\(xyz\\)o"], &grouped),
                (1, b"\n".to_vec(), Vec::new())
            );
        }

        #[test]
        fn first_capture_is_returned_from_a_prefix_match() {
            let regex_engine = MockRegexEngine::with_responses([Ok(RegexOutcome {
                capture_count: 1,
                whole_match: Some(Span { start: 0, end: 5 }),
                first_capture: Some(Span { start: 1, end: 4 }),
            })]);
            assert_eq!(
                run_case(&[b"hello", b":", b"h\\(ell\\)o"], &regex_engine),
                (0, b"ell\n".to_vec(), Vec::new())
            );
        }

        #[test]
        fn unmatched_first_capture_returns_whole_length_even_when_later_groups_match() {
            let regex_engine = MockRegexEngine::with_responses([Ok(RegexOutcome {
                capture_count: 2,
                whole_match: Some(Span { start: 0, end: 1 }),
                first_capture: None,
            })]);
            assert_eq!(
                run_case(&[b"b", b":", b"\\(a\\)\\?\\(b\\)"], &regex_engine),
                (0, b"1\n".to_vec(), Vec::new())
            );
        }

        #[test]
        fn only_the_first_of_multiple_captures_is_returned() {
            let regex_engine = MockRegexEngine::with_responses([Ok(RegexOutcome {
                capture_count: 2,
                whole_match: Some(Span { start: 0, end: 2 }),
                first_capture: Some(Span { start: 0, end: 1 }),
            })]);
            assert_eq!(
                run_case(&[b"ab", b":", b"\\(a\\)\\(b\\)"], &regex_engine),
                (0, b"a\n".to_vec(), Vec::new())
            );
        }

        #[test]
        fn participating_empty_capture_returns_an_empty_string() {
            let regex_engine = MockRegexEngine::with_responses([Ok(RegexOutcome {
                capture_count: 1,
                whole_match: Some(Span { start: 0, end: 3 }),
                first_capture: Some(Span { start: 0, end: 0 }),
            })]);
            assert_eq!(
                run_case(&[b"abc", b":", b"\\(\\)abc"], &regex_engine),
                (1, b"\n".to_vec(), Vec::new())
            );
        }

        #[test]
        fn passes_exact_operand_bytes_and_returns_the_whole_match_byte_length() {
            let regex_engine = MockRegexEngine::with_responses([Ok(plain_match(2))]);
            assert_eq!(
                run_case(&[b"\xffa", b":", b"\xff."], &regex_engine),
                (0, b"2\n".to_vec(), Vec::new())
            );
            assert_eq!(
                regex_engine.calls(),
                vec![RegexCall {
                    input: b"\xffa".to_vec(),
                    pattern: b"\xff.".to_vec(),
                }]
            );
        }

        #[test]
        fn coerces_integer_subexpressions_to_canonical_pattern_input_bytes() {
            let regex_engine = MockRegexEngine::with_responses([Ok(plain_match(1))]);
            assert_eq!(
                run_case(&[b"(", b"02", b"+", b"3", b")", b":", b"5"], &regex_engine,),
                (0, b"1\n".to_vec(), Vec::new())
            );
            assert_eq!(
                regex_engine.calls(),
                vec![RegexCall {
                    input: b"5".to_vec(),
                    pattern: b"5".to_vec(),
                }]
            );
        }

        #[test]
        fn treats_an_operator_looking_pattern_as_an_operand() {
            let regex_engine = MockRegexEngine::with_responses([Ok(plain_match(1))]);
            assert_eq!(
                run_case(&[b"x", b":", b":"], &regex_engine),
                (0, b"1\n".to_vec(), Vec::new())
            );
            assert_eq!(
                regex_engine.calls(),
                vec![RegexCall {
                    input: b"x".to_vec(),
                    pattern: b":".to_vec(),
                }]
            );
        }

        #[test]
        fn evaluates_match_chains_left_associatively() {
            let regex_engine =
                MockRegexEngine::with_responses([Ok(plain_match(3)), Ok(plain_match(1))]);
            assert_eq!(
                run_case(&[b"abc", b":", b"a.*", b":", b"3"], &regex_engine,),
                (0, b"1\n".to_vec(), Vec::new())
            );
            assert_eq!(
                regex_engine.calls(),
                vec![
                    RegexCall {
                        input: b"abc".to_vec(),
                        pattern: b"a.*".to_vec(),
                    },
                    RegexCall {
                        input: b"3".to_vec(),
                        pattern: b"3".to_vec(),
                    },
                ]
            );
        }

        #[test]
        fn capture_results_feed_the_next_match_in_exact_call_order() {
            let regex_engine = MockRegexEngine::with_responses([
                Ok(RegexOutcome {
                    capture_count: 1,
                    whole_match: Some(Span { start: 0, end: 4 }),
                    first_capture: Some(Span { start: 1, end: 3 }),
                }),
                Ok(plain_match(2)),
            ]);
            assert_eq!(
                run_case(&[b"xaby", b":", b"x\\(ab\\)y", b":", b"ab"], &regex_engine,),
                (0, b"2\n".to_vec(), Vec::new())
            );
            assert_eq!(
                regex_engine.calls(),
                vec![
                    RegexCall {
                        input: b"xaby".to_vec(),
                        pattern: b"x\\(ab\\)y".to_vec(),
                    },
                    RegexCall {
                        input: b"ab".to_vec(),
                        pattern: b"ab".to_vec(),
                    },
                ]
            );
        }

        #[test]
        fn rejects_out_of_bounds_engine_spans() {
            let regex_engine = MockRegexEngine::with_responses([Ok(RegexOutcome {
                capture_count: 0,
                whole_match: Some(Span { start: 0, end: 4 }),
                first_capture: None,
            })]);
            assert_eq!(
                run_case(&[b"abc", b":", b".*"], &regex_engine),
                (
                    3,
                    Vec::new(),
                    b"main: invalid regular expression match span\n".to_vec(),
                )
            );

            let regex_engine = MockRegexEngine::with_responses([Ok(RegexOutcome {
                capture_count: 1,
                whole_match: Some(Span { start: 0, end: 3 }),
                first_capture: Some(Span { start: 2, end: 4 }),
            })]);
            assert_eq!(
                run_case(&[b"abc", b":", b"\\(.*\\)"], &regex_engine),
                (
                    3,
                    Vec::new(),
                    b"main: invalid regular expression match span\n".to_vec(),
                )
            );
        }

        #[test]
        fn rejects_a_nonprefix_engine_match() {
            let regex_engine = MockRegexEngine::with_responses([Ok(RegexOutcome {
                capture_count: 0,
                whole_match: Some(Span { start: 1, end: 3 }),
                first_capture: None,
            })]);
            assert_eq!(
                run_case(&[b"abc", b":", b"bc"], &regex_engine),
                (1, b"0\n".to_vec(), Vec::new())
            );
        }

        #[test]
        fn propagates_regex_compile_errors_without_a_success_value() {
            let regex_engine = MockRegexEngine::with_responses([Err(RegexCompileError {
                message: b"mock regular expression error".to_vec(),
            })]);
            assert_eq!(
                run_case(&[b"abc", b":", b"["], &regex_engine),
                (
                    2,
                    Vec::new(),
                    b"main: mock regular expression error\n".to_vec(),
                )
            );
            assert_eq!(
                regex_engine.calls(),
                vec![RegexCall {
                    input: b"abc".to_vec(),
                    pattern: b"[".to_vec(),
                }]
            );
        }
    }

    mod eval4_multiplicative_tests {
        use super::{run_case, ExprError, MockRegexEngine, Parser, Token, Val};

        fn assert_value(args: &[&[u8]], status: i32, output: &[u8]) {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case(args, &regex_engine),
                (status, output.to_vec(), Vec::new()),
                "{args:?}"
            );
        }

        fn assert_error(args: &[&[u8]], status: i32, message: &[u8]) {
            let regex_engine = MockRegexEngine::default();
            let mut diagnostic = b"main: ".to_vec();
            diagnostic.extend_from_slice(message);
            diagnostic.push(b'\n');
            assert_eq!(
                run_case(args, &regex_engine),
                (status, Vec::new(), diagnostic),
                "{args:?}"
            );
        }

        #[test]
        fn evaluates_mixed_operators_left_associatively() {
            assert_value(&[b"96", b"/", b"4", b"/", b"3"], 0, b"8\n");
            assert_value(&[b"100", b"%", b"30", b"%", b"8"], 0, b"2\n");
            assert_value(&[b"9", b"*", b"5", b"/", b"2", b"%", b"6"], 0, b"4\n");
        }

        #[test]
        fn handles_signed_products_quotients_and_remainders() {
            assert_value(&[b" \t+006", b"*", b"-03"], 0, b"-18\n");
            assert_value(&[b"-6", b"*", b"-7"], 0, b"42\n");
            assert_value(
                &[b"-9223372036854775808", b"*", b"1"],
                0,
                b"-9223372036854775808\n",
            );
            assert_value(&[b"7", b"/", b"3"], 0, b"2\n");
            assert_value(&[b"-7", b"/", b"3"], 0, b"-2\n");
            assert_value(&[b"7", b"/", b"-3"], 0, b"-2\n");
            assert_value(&[b"-7", b"/", b"-3"], 0, b"2\n");
            assert_value(&[b"7", b"%", b"3"], 0, b"1\n");
            assert_value(&[b"-7", b"%", b"3"], 0, b"-1\n");
            assert_value(&[b"7", b"%", b"-3"], 0, b"1\n");
            assert_value(&[b"-7", b"%", b"-3"], 0, b"-1\n");
        }

        #[test]
        fn leaves_lower_precedence_operator_for_the_next_level() {
            let regex_engine = MockRegexEngine::default();
            let mut parser = Parser::new(
                vec![
                    b"2".to_vec(),
                    b"*".to_vec(),
                    b"3".to_vec(),
                    b"+".to_vec(),
                    b"4".to_vec(),
                ],
                &regex_engine,
            );
            parser.nexttoken(false).unwrap();

            assert_eq!(parser.eval4(), Ok(Val::make_int(6)));
            assert_eq!(parser.token, Token::Add);
            assert_eq!(parser.tokval, None);
        }

        #[test]
        fn reports_exact_conversion_diagnostics_for_both_operands() {
            assert_error(&[b"left?", b"*", b"2"], 2, b"number \"left?\" is invalid");
            assert_error(
                &[b"-9223372036854775809", b"/", b"2"],
                2,
                b"number \"-9223372036854775809\" is too small",
            );
            assert_error(
                &[b"9223372036854775808", b"%", b"2"],
                2,
                b"number \"9223372036854775808\" is too large",
            );
            assert_error(&[b"2", b"*", b"right?"], 2, b"number \"right?\" is invalid");
            assert_error(
                &[b"2", b"/", b"-9223372036854775809"],
                2,
                b"number \"-9223372036854775809\" is too small",
            );
            assert_error(
                &[b"2", b"%", b"9223372036854775808"],
                2,
                b"number \"9223372036854775808\" is too large",
            );
            assert_error(
                &[b"left-first", b"*", b"right-second"],
                2,
                b"number \"left-first\" is invalid",
            );
        }

        #[test]
        fn detects_multiplication_overflow_for_every_sign_pair() {
            for args in [
                [b"9223372036854775807".as_slice(), b"*", b"2"],
                [b"9223372036854775807".as_slice(), b"*", b"-2"],
                [b"-9223372036854775808".as_slice(), b"*", b"2"],
                [b"-9223372036854775808".as_slice(), b"*", b"-1"],
            ] {
                assert_error(&args, 3, b"overflow");
            }
        }

        #[test]
        fn rejects_zero_for_both_divisor_operators() {
            assert_error(&[b"8", b"/", b"0"], 2, b"division by zero");
            assert_error(&[b"8", b"%", b"+0"], 2, b"division by zero");
        }

        #[test]
        fn handles_minimum_divided_or_reduced_by_negative_one() {
            assert_error(&[b"-9223372036854775808", b"/", b"-1"], 3, b"overflow");
            assert_value(&[b"-9223372036854775808", b"%", b"-1"], 1, b"0\n");
        }

        #[test]
        fn evaluates_the_right_side_before_coercing_the_left() {
            let regex_engine = MockRegexEngine::with_responses([Err(crate::RegexCompileError {
                message: b"right-side failure".to_vec(),
            })]);

            assert_eq!(
                run_case(
                    &[b"not-a-number", b"*", b"subject", b":", b"pattern"],
                    &regex_engine,
                ),
                (2, Vec::new(), b"main: right-side failure\n".to_vec(),)
            );
            assert_eq!(regex_engine.calls().len(), 1);

            let regex_engine = MockRegexEngine::default();
            let mut parser =
                Parser::new(vec![b"not-a-number".to_vec(), b"*".to_vec()], &regex_engine);
            parser.nexttoken(false).unwrap();
            assert_eq!(parser.eval4(), Err(ExprError::Syntax));
        }
    }

    mod eval3_additive_tests {
        use super::{run_case, ExprError, MockRegexEngine, Parser};

        fn assert_value(args: &[&[u8]], status: i32, output: &[u8]) {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case(args, &regex_engine),
                (status, output.to_vec(), Vec::new()),
                "{args:?}"
            );
        }

        fn assert_error(args: &[&[u8]], status: i32, message: &[u8]) {
            let regex_engine = MockRegexEngine::default();
            let mut diagnostic = b"main: ".to_vec();
            diagnostic.extend_from_slice(message);
            diagnostic.push(b'\n');
            assert_eq!(
                run_case(args, &regex_engine),
                (status, Vec::new(), diagnostic),
                "{args:?}"
            );
        }

        #[test]
        fn evaluates_positive_and_negative_addition_and_subtraction() {
            for (args, expected) in [
                ([b"7".as_slice(), b"+", b"5"], b"12\n".as_slice()),
                ([b"-7".as_slice(), b"+", b"5"], b"-2\n".as_slice()),
                ([b"7".as_slice(), b"+", b"-5"], b"2\n".as_slice()),
                ([b"-7".as_slice(), b"+", b"-5"], b"-12\n".as_slice()),
                ([b"7".as_slice(), b"-", b"5"], b"2\n".as_slice()),
                ([b"-7".as_slice(), b"-", b"5"], b"-12\n".as_slice()),
                ([b"7".as_slice(), b"-", b"-5"], b"12\n".as_slice()),
                ([b"-7".as_slice(), b"-", b"-5"], b"-2\n".as_slice()),
            ] {
                assert_value(&args, 0, expected);
            }
        }

        #[test]
        fn folds_mixed_additive_operators_left_associatively() {
            assert_value(&[b"20", b"-", b"6", b"-", b"3"], 0, b"11\n");
            assert_value(&[b"20", b"-", b"6", b"+", b"3"], 0, b"17\n");
            assert_value(&[b"2", b"+", b"3", b"+", b"4"], 0, b"9\n");
            assert_value(&[b"2", b"-", b"3", b"+", b"4"], 0, b"3\n");
        }

        #[test]
        fn detects_each_addition_and_subtraction_overflow_direction() {
            for args in [
                [b"9223372036854775807".as_slice(), b"+", b"1"],
                [b"-9223372036854775808".as_slice(), b"+", b"-1"],
                [b"9223372036854775807".as_slice(), b"-", b"-1"],
                [b"-9223372036854775808".as_slice(), b"-", b"1"],
            ] {
                assert_error(&args, 3, b"overflow");
            }

            assert_value(
                &[b"9223372036854775807", b"+", b"0"],
                0,
                b"9223372036854775807\n",
            );
            assert_value(
                &[b"-9223372036854775808", b"-", b"0"],
                0,
                b"-9223372036854775808\n",
            );
        }

        #[test]
        fn reports_exact_conversion_diagnostics_for_both_operands() {
            assert_error(&[b"left?", b"+", b"2"], 2, b"number \"left?\" is invalid");
            assert_error(
                &[b"-9223372036854775809", b"-", b"0"],
                2,
                b"number \"-9223372036854775809\" is too small",
            );
            assert_error(
                &[b"9223372036854775808", b"+", b"0"],
                2,
                b"number \"9223372036854775808\" is too large",
            );
            assert_error(&[b"2", b"-", b"right?"], 2, b"number \"right?\" is invalid");
            assert_error(
                &[b"2", b"+", b"-9223372036854775809"],
                2,
                b"number \"-9223372036854775809\" is too small",
            );
            assert_error(
                &[b"2", b"-", b"9223372036854775808"],
                2,
                b"number \"9223372036854775808\" is too large",
            );
            assert_error(
                &[b"left-first", b"+", b"right-second"],
                2,
                b"number \"left-first\" is invalid",
            );
        }

        #[test]
        fn evaluates_each_multiplicative_term_before_addition() {
            assert_value(&[b"2", b"+", b"3", b"*", b"4", b"-", b"5"], 0, b"9\n");
            assert_value(&[b"20", b"/", b"5", b"+", b"3", b"*", b"4"], 0, b"16\n");
            assert_value(&[b"20", b"-", b"4", b"*", b"3", b"+", b"2"], 0, b"10\n");
        }

        #[test]
        fn distinguishes_binary_subtraction_from_a_negative_number_operand() {
            assert_value(&[b"-2"], 0, b"-2\n");
            assert_value(&[b"5", b"-", b"-2"], 0, b"7\n");
            assert_value(&[b"-5", b"-", b"-2"], 0, b"-3\n");
            assert_error(&[b"-", b"2"], 2, b"syntax error");
            assert_error(&[b"5", b"-", b"-", b"2"], 2, b"syntax error");
        }

        #[test]
        fn evaluates_the_right_term_before_coercing_the_left() {
            assert_error(
                &[b"not-a-number", b"+", b"1", b"/", b"0"],
                2,
                b"division by zero",
            );

            let regex_engine = MockRegexEngine::default();
            let mut parser =
                Parser::new(vec![b"not-a-number".to_vec(), b"+".to_vec()], &regex_engine);
            parser.nexttoken(false).unwrap();
            assert_eq!(parser.eval3(), Err(ExprError::Syntax));
        }
    }

    mod eval2_comparison_tests {
        use super::{run_case, MockRegexEngine};

        fn assert_comparison(args: &[&[u8]], expected: bool) {
            let regex_engine = MockRegexEngine::default();
            let status = if expected { 0 } else { 1 };
            let output = if expected {
                b"1\n".to_vec()
            } else {
                b"0\n".to_vec()
            };
            assert_eq!(
                run_case(args, &regex_engine),
                (status, output, Vec::new()),
                "{args:?}"
            );
        }

        #[test]
        fn returns_integer_booleans_for_every_comparison_operator() {
            assert_comparison(&[b"5", b"=", b"+05"], true);
            assert_comparison(&[b"5", b"=", b"6"], false);
            assert_comparison(&[b"5", b"!=", b"6"], true);
            assert_comparison(&[b"5", b"!=", b"+05"], false);
            assert_comparison(&[b"4", b"<", b"5"], true);
            assert_comparison(&[b"5", b"<", b"4"], false);
            assert_comparison(&[b"5", b">", b"4"], true);
            assert_comparison(&[b"4", b">", b"5"], false);
            assert_comparison(&[b"5", b"<=", b"5"], true);
            assert_comparison(&[b"6", b"<=", b"5"], false);
            assert_comparison(&[b"5", b">=", b"5"], true);
            assert_comparison(&[b"4", b">=", b"5"], false);
        }

        #[test]
        fn folds_chained_comparisons_from_left_to_right() {
            assert_comparison(&[b"3", b"<", b"4", b"<", b"2"], true);
            assert_comparison(&[b"3", b"<", b"4", b"<", b"1"], false);
            assert_comparison(&[b"3", b">", b"2", b"=", b"1"], true);
            assert_comparison(&[b"3", b"<", b"2", b"=", b"0"], true);
        }

        #[test]
        fn compares_full_i64_numeric_spellings_by_value() {
            assert_comparison(&[b" \t\n\x0b\x0c\r+00042", b"=", b"42"], true);
            assert_comparison(&[b"-0009", b"<", b" \t+0008"], true);
            assert_comparison(&[b"-0", b"=", b"+000"], true);
            assert_comparison(
                &[b"-9223372036854775808", b"<", b"9223372036854775807"],
                true,
            );

            // Trailing whitespace is not part of the accepted numeric grammar.
            assert_comparison(&[b"2 ", b"<", b"10"], false);
        }

        #[test]
        fn falls_back_to_raw_bytes_when_either_value_is_not_an_i64() {
            assert_comparison(&[b"10", b"<", b"2x"], true);
            assert_comparison(&[b"2x", b">", b"10"], true);
            assert_comparison(&[b"9", b">", b"10x"], true);
            assert_comparison(&[b"010", b"<", b"02x"], true);
            assert_comparison(&[b"02x", b">", b"010"], true);
            assert_comparison(&[b" \t9", b"<", b"0x"], true);
            assert_comparison(&[b"9223372036854775808", b"<", b"99"], true);
        }

        #[test]
        fn canonicalizes_integer_subexpressions_for_byte_comparison() {
            assert_comparison(&[b"5", b"+", b"5", b"<", b"10x"], true);
            assert_comparison(&[b"10x", b">", b"5", b"+", b"5"], true);
            assert_comparison(&[b"0", b"-", b"2", b"<", b"-20x"], true);
            assert_comparison(&[b"(", b"0009", b"+", b"1", b")", b">", b"010x"], true);
        }

        #[test]
        fn uses_c_locale_unsigned_byte_ordering_for_arbitrary_strings() {
            assert_comparison(&[b"", b"=", b""], true);
            assert_comparison(&[b"", b"<", b"\x80"], true);
            assert_comparison(&[b"\xff\x80", b"=", b"\xff\x80"], true);
            assert_comparison(&[b"abc", b"!=", b"abd"], true);
            assert_comparison(&[b"abc", b"<=", b"abd"], true);
            assert_comparison(&[b"abd", b">=", b"abc"], true);
            assert_comparison(&[b"\x80", b">", b"\x7f"], true);
            assert_comparison(&[b"\xff", b">", b"\x80"], true);
        }

        #[test]
        fn binds_below_arithmetic_and_above_logical_operators() {
            assert_comparison(&[b"1", b"+", b"2", b"=", b"3"], true);
            assert_comparison(&[b"2", b"<", b"1", b"+", b"2"], true);
            assert_comparison(&[b"1", b"+", b"2", b">", b"2", b"*", b"1"], true);
            assert_comparison(&[b"0", b"|", b"2", b">", b"1"], true);
            assert_comparison(&[b"1", b"=", b"1", b"&", b"2", b"=", b"3"], false);
            assert_comparison(&[b"0", b"=", b"1", b"|", b"2", b">=", b"2"], true);
        }
    }

    mod eval1_conjunction_tests {
        use super::{run_case, ExprError, MockRegexEngine, Parser, Token, Val};

        fn assert_value(args: &[&[u8]], status: i32, output: &[u8]) {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case(args, &regex_engine),
                (status, output.to_vec(), Vec::new()),
                "{args:?}"
            );
        }

        fn assert_error(args: &[&[u8]], status: i32, message: &[u8]) {
            let regex_engine = MockRegexEngine::default();
            let mut diagnostic = b"main: ".to_vec();
            diagnostic.extend_from_slice(message);
            diagnostic.push(b'\n');
            assert_eq!(
                run_case(args, &regex_engine),
                (status, Vec::new(), diagnostic),
                "{args:?}"
            );
        }

        #[test]
        fn returns_zero_if_either_value_is_false_and_the_left_if_both_are_true() {
            assert_value(&[b"", b"&", b""], 1, b"0\n");
            assert_value(&[b"", b"&", b"right"], 1, b"0\n");
            assert_value(&[b"left", b"&", b""], 1, b"0\n");
            assert_value(&[b"left", b"&", b"right"], 0, b"left\n");

            assert_value(&[b"+000", b"&", b"right"], 1, b"0\n");
            assert_value(&[b"left", b"&", b"-000"], 1, b"0\n");
            assert_value(&[b"0 ", b"&", b"right"], 0, b"0 \n");
            assert_value(&[b"\xffleft", b"&", b"right"], 0, b"\xffleft\n");
        }

        #[test]
        fn preserves_and_canonicalizes_the_selected_left_value() {
            assert_value(&[b"original", b"&", b"other"], 0, b"original\n");
            assert_value(&[b"01", b"&", b"02"], 0, b"1\n");
            assert_value(&[b" \t+00012", b"&", b"-03"], 0, b"12\n");
            assert_value(
                &[b"9223372036854775808", b"&", b"1"],
                0,
                b"9223372036854775808\n",
            );
        }

        #[test]
        fn folds_left_to_right_and_evaluates_comparisons_first() {
            assert_value(&[b"first", b"&", b"second", b"&", b"third"], 0, b"first\n");
            assert_value(&[b"01", b"&", b"02", b"&", b"03"], 0, b"1\n");
            assert_value(&[b"01", b"&", b"0", b"&", b"03"], 1, b"0\n");
            assert_value(&[b"2", b">", b"1", b"&", b"3", b"<=", b"3"], 0, b"1\n");
            assert_value(&[b"2", b">", b"1", b"&", b"3", b"<", b"3"], 1, b"0\n");

            let regex_engine = MockRegexEngine::default();
            let mut parser = Parser::new(
                vec![
                    b"left".to_vec(),
                    b"&".to_vec(),
                    b"right".to_vec(),
                    b"|".to_vec(),
                    b"fallback".to_vec(),
                ],
                &regex_engine,
            );
            parser.nexttoken(false).unwrap();
            assert_eq!(parser.eval1(), Ok(Val::make_str(b"left".to_vec())));
            assert_eq!(parser.token, Token::Or);
        }

        #[test]
        fn evaluates_every_right_operand_before_applying_false_selection() {
            assert_error(&[b"0", b"&"], 2, b"syntax error");
            assert_error(&[b"0", b"&", b"1", b"/", b"0"], 2, b"division by zero");
            assert_error(
                &[b"0", b"&", b"not-a-number", b"+", b"1"],
                2,
                b"number \"not-a-number\" is invalid",
            );
            assert_error(
                &[b"0", b"&", b"9223372036854775807", b"+", b"1"],
                3,
                b"overflow",
            );
            assert_error(
                &[b"0", b"&", b"1", b"&", b"2", b"/", b"0"],
                2,
                b"division by zero",
            );

            let regex_engine = MockRegexEngine::default();
            let mut parser = Parser::new(
                vec![b"0".to_vec(), b"&".to_vec(), b"1".to_vec(), b"&".to_vec()],
                &regex_engine,
            );
            parser.nexttoken(false).unwrap();
            assert_eq!(parser.eval1(), Err(ExprError::Syntax));
        }
    }

    mod eval0_alternative_tests {
        use super::{run_case, MockRegexEngine};

        fn assert_value(args: &[&[u8]], status: i32, output: &[u8]) {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case(args, &regex_engine),
                (status, output.to_vec(), Vec::new()),
                "{args:?}"
            );
        }

        fn assert_error(args: &[&[u8]], status: i32, message: &[u8]) {
            let regex_engine = MockRegexEngine::default();
            let mut diagnostic = b"main: ".to_vec();
            diagnostic.extend_from_slice(message);
            diagnostic.push(b'\n');
            assert_eq!(
                run_case(args, &regex_engine),
                (status, Vec::new(), diagnostic),
                "{args:?}"
            );
        }

        #[test]
        fn preserves_a_truthy_left_value_and_its_truth_coercion() {
            assert_value(&[b"left", b"|", b"right"], 0, b"left\n");
            assert_value(&[b"\xffleft", b"|", b"right"], 0, b"\xffleft\n");
            assert_value(&[b"01", b"|", b"right"], 0, b"1\n");
            assert_value(&[b" \t-0002", b"|", b"right"], 0, b"-2\n");
            assert_value(
                &[b"9223372036854775808", b"|", b"right"],
                0,
                b"9223372036854775808\n",
            );
        }

        #[test]
        fn selects_a_false_lefts_right_value_without_coercing_it_early() {
            assert_value(&[b"0", b"|", b"02"], 0, b"02\n");
            assert_value(&[b"+000", b"|", b"-000"], 1, b"-000\n");
            assert_value(&[b"", b"|", b" \t+000"], 1, b" \t+000\n");
            assert_value(&[b"-0", b"|", b"\xffright"], 0, b"\xffright\n");
        }

        #[test]
        fn folds_chained_alternatives_from_left_to_right() {
            assert_value(&[b"first", b"|", b"second", b"|", b"third"], 0, b"first\n");
            assert_value(&[b"0", b"|", b"00", b"|", b"003"], 0, b"003\n");
            assert_value(&[b"0", b"|", b"02", b"|", b"003"], 0, b"2\n");
            assert_value(&[b"", b"|", b"-0", b"|", b"last"], 0, b"last\n");
            assert_value(&[b"", b"|", b"0", b"|", b"+000"], 1, b"+000\n");
        }

        #[test]
        fn gives_conjunction_higher_precedence_than_alternative() {
            assert_value(&[b"left", b"|", b"0", b"&", b"right"], 0, b"left\n");
            assert_value(&[b"0", b"&", b"right", b"|", b"selected"], 0, b"selected\n");
            assert_value(&[b"0", b"|", b"01", b"&", b"02"], 0, b"1\n");
            assert_value(
                &[b"0", b"|", b"2", b">", b"1", b"&", b"3", b"=", b"3"],
                0,
                b"1\n",
            );
        }

        #[test]
        fn evaluates_every_right_operand_even_when_the_left_is_truthy() {
            assert_error(&[b"left", b"|"], 2, b"syntax error");
            assert_error(&[b"left", b"|", b"1", b"/", b"0"], 2, b"division by zero");
            assert_error(
                &[
                    b"left",
                    b"|",
                    b"ignored",
                    b"|",
                    b"9223372036854775807",
                    b"+",
                    b"1",
                ],
                3,
                b"overflow",
            );
            assert_error(
                &[b"left", b"|", b"0", b"&", b"1", b"/", b"0"],
                2,
                b"division by zero",
            );
            assert_error(&[b"left", b"|", b"ignored", b"|"], 2, b"syntax error");
        }
    }

    mod run_tests {
        use super::{
            run_case, run_case_with_program, MockRegexEngine, RegexCompileError, RegexOutcome, Span,
        };

        #[test]
        fn preserves_every_precedence_level_and_left_associativity_at_the_run_boundary() {
            let regex_engine = MockRegexEngine::with_responses([Ok(RegexOutcome {
                capture_count: 1,
                whole_match: Some(Span { start: 0, end: 6 }),
                first_capture: Some(Span { start: 0, end: 3 }),
            })]);
            assert_eq!(
                run_case(
                    &[
                        b"abcdef",
                        b":",
                        b"\\(abc\\)def",
                        b"=",
                        b"abc",
                        b"&",
                        b"20",
                        b"/",
                        b"5",
                        b"*",
                        b"2",
                        b"-",
                        b"3",
                        b"+",
                        b"1",
                        b"=",
                        b"6",
                        b"=",
                        b"1",
                        b"|",
                        b"fallback",
                    ],
                    &regex_engine,
                ),
                (0, b"1\n".to_vec(), Vec::new())
            );
        }

        #[test]
        fn writes_raw_values_before_final_truth_coercion() {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case(&[b"plain"], &regex_engine),
                (0, b"plain\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"\xff\x80"], &regex_engine),
                (0, b"\xff\x80\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b""], &regex_engine),
                (1, b"\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"+0"], &regex_engine),
                (1, b"+0\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b" 000"], &regex_engine),
                (1, b" 000\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"001"], &regex_engine),
                (0, b"001\n".to_vec(), Vec::new())
            );
        }

        #[test]
        fn removes_exactly_one_leading_double_dash() {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case(&[b"--", b"value"], &regex_engine),
                (0, b"value\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"--", b"--"], &regex_engine),
                (0, b"--\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"--"], &regex_engine),
                (2, Vec::new(), b"main: syntax error\n".to_vec())
            );
            assert_eq!(
                run_case(&[b"value", b"--"], &regex_engine),
                (2, Vec::new(), b"main: syntax error\n".to_vec())
            );
        }

        #[test]
        fn syntax_failures_use_only_stderr_and_status_two() {
            let regex_engine = MockRegexEngine::default();
            for args in [
                Vec::<&[u8]>::new(),
                vec![b"+".as_slice()],
                vec![b"value".as_slice(), b"extra"],
                vec![b"(".as_slice(), b"value"],
            ] {
                assert_eq!(
                    run_case(&args, &regex_engine),
                    (2, Vec::new(), b"main: syntax error\n".to_vec()),
                    "{args:?}"
                );
            }
        }

        #[test]
        fn diagnostics_use_the_raw_runtime_basename() {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case_with_program(b"/usr/local/bin/alias", &[], &regex_engine),
                (2, Vec::new(), b"alias: syntax error\n".to_vec())
            );
            assert_eq!(
                run_case_with_program(b"/tmp/\xffexpr", &[], &regex_engine),
                (2, Vec::new(), b"\xffexpr: syntax error\n".to_vec())
            );
            assert_eq!(
                run_case_with_program(b"relative-name", &[], &regex_engine),
                (2, Vec::new(), b"relative-name: syntax error\n".to_vec())
            );
        }

        #[test]
        fn number_diagnostics_do_not_escape_raw_operand_bytes() {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case_with_program(
                    b"/tmp/\xfealias",
                    &[b"a\"b\n\xff", b"+", b"1"],
                    &regex_engine,
                ),
                (
                    2,
                    Vec::new(),
                    b"\xfealias: number \"a\"b\n\xff\" is invalid\n".to_vec(),
                )
            );
            assert_eq!(
                run_case(&[b"9223372036854775808", b"+", b"0"], &regex_engine),
                (
                    2,
                    Vec::new(),
                    b"main: number \"9223372036854775808\" is too large\n".to_vec(),
                )
            );
            assert_eq!(
                run_case(&[b"-9223372036854775809", b"+", b"0"], &regex_engine),
                (
                    2,
                    Vec::new(),
                    b"main: number \"-9223372036854775809\" is too small\n".to_vec(),
                )
            );
        }

        #[test]
        fn returns_status_two_for_runtime_failures_and_status_three_for_overflow() {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case(&[b"invalid", b"*", b"2"], &regex_engine),
                (
                    2,
                    Vec::new(),
                    b"main: number \"invalid\" is invalid\n".to_vec(),
                )
            );
            assert_eq!(
                run_case(&[b"7", b"%", b"0"], &regex_engine),
                (2, Vec::new(), b"main: division by zero\n".to_vec(),)
            );
            assert_eq!(
                run_case(&[b"9223372036854775807", b"+", b"1"], &regex_engine,),
                (3, Vec::new(), b"main: overflow\n".to_vec())
            );

            let regex_engine = MockRegexEngine::with_responses([Err(RegexCompileError {
                message: b"Trailing backslash".to_vec(),
            })]);
            assert_eq!(
                run_case(&[b"input", b":", b"\\"], &regex_engine),
                (2, Vec::new(), b"main: Trailing backslash\n".to_vec(),)
            );
        }

        #[test]
        fn repaired_non_regex_seed_paths_match_the_source_contract() {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case(&[b"3", b">=", b"5"], &regex_engine),
                (1, b"0\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"5", b">=", b"3"], &regex_engine),
                (0, b"1\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"2", b"-", b"5"], &regex_engine),
                (0, b"-3\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"def", b">=", b"abc"], &regex_engine),
                (0, b"1\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"3", b"+", b"-2"], &regex_engine),
                (0, b"1\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"6", b"/", b"2"], &regex_engine),
                (0, b"3\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"3", b"+", b"4", b"*", b"5", b"+", b"0"], &regex_engine),
                (0, b"23\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"(", b"3", b"+", b"4", b")"], &regex_engine),
                (0, b"7\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"2", b"*", b"3"], &regex_engine),
                (0, b"6\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"1", b"&", b"2"], &regex_engine),
                (0, b"1\n".to_vec(), Vec::new())
            );
            assert_eq!(
                run_case(&[b"1", b"&", b"0"], &regex_engine),
                (1, b"0\n".to_vec(), Vec::new())
            );
        }

        #[test]
        fn invalid_addition_operand_has_exact_diagnostic() {
            let regex_engine = MockRegexEngine::default();
            assert_eq!(
                run_case(&[b"abc", b"+", b"1"], &regex_engine),
                (2, Vec::new(), b"main: number \"abc\" is invalid\n".to_vec())
            );
        }
    }
}
