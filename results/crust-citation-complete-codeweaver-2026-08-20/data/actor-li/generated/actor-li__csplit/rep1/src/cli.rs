use std::ffi::OsString;
use std::os::unix::ffi::OsStringExt;

use crate::csplit::{getopt_error, usage, CsplitError};

const PATH_MAX: usize = 4096;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Options {
    pub prefix: Vec<u8>,
    pub sufflen: i64,
    pub sflag: bool,
    pub kflag: bool,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            prefix: b"xx".to_vec(),
            sufflen: 2,
            sflag: false,
            kflag: false,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Invocation {
    pub argv0: Vec<u8>,
    pub progname: Vec<u8>,
    pub options: Options,
    pub input: Vec<u8>,
    pub expressions: Vec<Vec<u8>>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Strtol10Result {
    pub value: i64,
    pub end: usize,
    pub converted: bool,
    pub overflowed: bool,
}

pub fn parse(args: Vec<OsString>, posixly_correct: bool) -> Result<Invocation, CsplitError> {
    let mut args = args.into_iter().map(OsStringExt::into_vec);
    let argv0 = args.next().unwrap_or_else(|| b"csplit".to_vec());
    let progname = argv0
        .rsplit(|byte| *byte == b'/')
        .next()
        .unwrap_or(&argv0)
        .to_vec();
    let arguments: Vec<Vec<u8>> = args.collect();
    let mut options = Options::default();
    let mut operands = Vec::new();
    let mut index = 0;

    while index < arguments.len() {
        let argument = &arguments[index];
        if argument == b"--" {
            operands.extend(arguments[index + 1..].iter().cloned());
            break;
        }
        if argument.len() < 2 || argument[0] != b'-' {
            if posixly_correct {
                operands.extend(arguments[index..].iter().cloned());
                break;
            }
            operands.push(argument.clone());
            index += 1;
            continue;
        }

        let mut option_index = 1;
        while option_index < argument.len() {
            let option = argument[option_index];
            match option {
                b'k' => {
                    options.kflag = true;
                    option_index += 1;
                }
                b's' => {
                    options.sflag = true;
                    option_index += 1;
                }
                b'f' | b'n' => {
                    let value = if option_index + 1 < argument.len() {
                        let value = argument[option_index + 1..].to_vec();
                        option_index = argument.len();
                        value
                    } else {
                        index += 1;
                        if index >= arguments.len() {
                            return Err(getopt_error(&argv0, &progname, option, true));
                        }
                        option_index = argument.len();
                        arguments[index].clone()
                    };

                    if option == b'f' {
                        options.prefix = value;
                    } else {
                        let parsed = strtol10(&value);
                        if parsed.value <= 0 || parsed.end != value.len() || parsed.overflowed {
                            let mut detail = value;
                            detail.extend_from_slice(b": bad suffix length");
                            return Err(CsplitError::message(progname.clone(), detail));
                        }
                        options.sufflen = parsed.value;
                    }
                }
                _ => return Err(getopt_error(&argv0, &progname, option, false)),
            }
        }
        index += 1;
    }

    let suffix_len = usize::try_from(options.sufflen).unwrap_or(usize::MAX);
    if options
        .prefix
        .len()
        .checked_add(suffix_len)
        .map_or(true, |length| length >= PATH_MAX)
    {
        return Err(CsplitError::message(
            progname.clone(),
            b"name too long".to_vec(),
        ));
    }

    let Some(input) = operands.first().cloned() else {
        return Err(usage(&progname));
    };

    Ok(Invocation {
        argv0,
        progname,
        options,
        input,
        expressions: operands.into_iter().skip(1).collect(),
    })
}

pub fn strtol10(bytes: &[u8]) -> Strtol10Result {
    let mut index = 0;
    while bytes
        .get(index)
        .is_some_and(|byte| matches!(byte, b' ' | b'\t' | b'\n' | 0x0b | 0x0c | b'\r'))
    {
        index += 1;
    }

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
        (i64::MAX as u64) + 1
    } else {
        i64::MAX as u64
    };
    let mut magnitude = 0_u64;
    let mut overflowed = false;

    while let Some(digit @ b'0'..=b'9') = bytes.get(index).copied() {
        let value = u64::from(digit - b'0');
        if magnitude > (limit - value) / 10 {
            overflowed = true;
        } else if !overflowed {
            magnitude = magnitude * 10 + value;
        }
        index += 1;
    }

    if index == digit_start {
        return Strtol10Result {
            value: 0,
            end: 0,
            converted: false,
            overflowed: false,
        };
    }

    let value = if overflowed {
        if negative {
            i64::MIN
        } else {
            i64::MAX
        }
    } else if negative {
        if magnitude == (i64::MAX as u64) + 1 {
            i64::MIN
        } else {
            -(magnitude as i64)
        }
    } else {
        magnitude as i64
    };

    Strtol10Result {
        value,
        end: index,
        converted: true,
        overflowed,
    }
}

pub fn parse_repetition(token: &[u8]) -> Result<i64, CsplitError> {
    let body = token.get(1..).unwrap_or_default();
    let parsed = strtol10(body);
    if parsed.value < 0 || parsed.overflowed || body.get(parsed.end).copied() != Some(b'}') {
        let mut detail = body.to_vec();
        detail.extend_from_slice(b": bad repetition count");
        return Err(CsplitError::deferred_message(detail));
    }
    Ok(parsed.value)
}

#[cfg(test)]
mod tests {
    use std::ffi::OsString;
    use std::os::unix::ffi::OsStringExt;

    use super::{parse, parse_repetition, strtol10, Options};

    fn args(values: &[&[u8]]) -> Vec<OsString> {
        values
            .iter()
            .map(|value| OsString::from_vec(value.to_vec()))
            .collect()
    }

    fn render(error: crate::csplit::CsplitError) -> Vec<u8> {
        let mut output = Vec::new();
        error.write_to(&mut output).expect("render error");
        output
    }

    #[test]
    fn defaults_and_each_option() {
        let invocation = parse(
            args(&[b"csplit", b"-ks", b"-fp", b"-n3", b"in", b"2"]),
            false,
        )
        .expect("parse invocation");
        assert_eq!(
            invocation.options,
            Options {
                prefix: b"p".to_vec(),
                sufflen: 3,
                sflag: true,
                kflag: true,
            }
        );
        assert_eq!(invocation.expressions, vec![b"2".to_vec()]);
    }

    #[test]
    fn clustered_and_attached_arguments() {
        let invocation = parse(
            args(&[b"csplit", b"input", b"2", b"-sk", b"-fprefix", b"-n", b"+3"]),
            false,
        )
        .expect("parse permuted options");

        assert_eq!(
            invocation.options,
            Options {
                prefix: b"prefix".to_vec(),
                sufflen: 3,
                sflag: true,
                kflag: true,
            }
        );
        assert_eq!(invocation.input, b"input");
        assert_eq!(invocation.expressions, vec![b"2".to_vec()]);
    }

    #[test]
    fn gnu_permutation_treats_minus_one_as_option() {
        let error = parse(args(&[b"../csplit", b"in", b"-1"]), false).unwrap_err();
        assert_eq!(
            render(error),
            b"../csplit: invalid option -- '1'\nusage: csplit [-ks] [-f prefix] [-n number] file args ...\n"
        );
    }

    #[test]
    fn posixly_correct_stops_at_first_operand() {
        let invocation = parse(args(&[b"csplit", b"-k", b"in", b"-s", b"2"]), true)
            .expect("parse POSIX ordering");

        assert!(invocation.options.kflag);
        assert!(!invocation.options.sflag);
        assert_eq!(invocation.input, b"in");
        assert_eq!(invocation.expressions, vec![b"-s".to_vec(), b"2".to_vec()]);
    }

    #[test]
    fn double_dash_and_lone_dash() {
        let permuted =
            parse(args(&[b"csplit", b"-", b"-s"]), false).expect("lone dash remains an operand");
        assert!(permuted.options.sflag);
        assert_eq!(permuted.input, b"-");
        assert!(permuted.expressions.is_empty());

        let terminated = parse(args(&[b"csplit", b"--", b"-s", b"-"]), false)
            .expect("double dash terminates options");
        assert!(!terminated.options.sflag);
        assert_eq!(terminated.input, b"-s");
        assert_eq!(terminated.expressions, vec![b"-".to_vec()]);
    }

    #[test]
    fn unknown_and_missing_option_use_original_argv0() {
        let unknown = parse(args(&[b"../bin/alias", b"-z"]), false).unwrap_err();
        assert_eq!(
            render(unknown),
            b"../bin/alias: invalid option -- 'z'\nusage: alias [-ks] [-f prefix] [-n number] file args ...\n"
        );

        let missing = parse(args(&[b"../bin/alias", b"-f"]), false).unwrap_err();
        assert_eq!(
            render(missing),
            b"../bin/alias: option requires an argument -- 'f'\nusage: alias [-ks] [-f prefix] [-n number] file args ...\n"
        );
    }

    #[test]
    fn negative_suffix_is_rejected() {
        let error = parse(args(&[b"csplit", b"-n", b"-1", b"in"]), false).unwrap_err();
        assert_eq!(render(error), b"csplit: -1: bad suffix length\n");
    }

    #[test]
    fn strtol_whitespace_sign_end_and_overflow_matrix() {
        let positive = strtol10(b" \t\n\x0b\x0c\r+42x");
        assert_eq!(positive.value, 42);
        assert_eq!(positive.end, 9);
        assert!(positive.converted);
        assert!(!positive.overflowed);

        for no_digits in [b"".as_slice(), b" \t", b"+", b" -x"] {
            let parsed = strtol10(no_digits);
            assert_eq!(parsed.value, 0);
            assert_eq!(parsed.end, 0);
            assert!(!parsed.converted);
            assert!(!parsed.overflowed);
        }

        assert_eq!(strtol10(b"9223372036854775807").value, i64::MAX);
        assert_eq!(strtol10(b"-9223372036854775808").value, i64::MIN);

        let positive_overflow = strtol10(b"9223372036854775808tail");
        assert_eq!(positive_overflow.value, i64::MAX);
        assert_eq!(positive_overflow.end, 19);
        assert!(positive_overflow.overflowed);

        let negative_overflow = strtol10(b"-9223372036854775809");
        assert_eq!(negative_overflow.value, i64::MIN);
        assert_eq!(negative_overflow.end, 20);
        assert!(negative_overflow.overflowed);
    }

    #[test]
    fn invalid_repetition_omits_opening_brace() {
        let error = parse_repetition(b"{abc}").unwrap_err();
        assert_eq!(render(error), b"abc}: bad repetition count\n");
    }

    #[test]
    fn repetition_accepts_empty_and_trailing_bytes() {
        assert_eq!(parse_repetition(b"{}").unwrap(), 0);
        assert_eq!(parse_repetition(b"{2}junk").unwrap(), 2);
        assert_eq!(parse_repetition(b"{+2}").unwrap(), 2);
        assert_eq!(parse_repetition(b"{-0}").unwrap(), 0);
    }
}
