use std::ffi::{OsStr, OsString};
use std::os::unix::ffi::{OsStrExt, OsStringExt};

use crate::csplit::{CsplitError, Diagnostic, DiagnosticPrefix, Options};

pub(crate) const OPTION_STRING: &[u8] = b"f:kn:s";
pub(crate) const PATH_MAX: usize = 4096;
pub(crate) const LONG_MAX: i64 = i64::MAX;

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Invocation {
    pub(crate) argv: Vec<OsString>,
    pub(crate) posixly_correct: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ProgramNames {
    pub(crate) invocation: OsString,
    pub(crate) basename: OsString,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct ParsedLong {
    pub(crate) value: i64,
    pub(crate) end: usize,
    pub(crate) overflowed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct PatternOperand {
    pub(crate) expr: Vec<u8>,
    pub(crate) reps: i64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ParsedCli {
    pub(crate) names: ProgramNames,
    pub(crate) options: Options,
    pub(crate) input: OsString,
    pub(crate) patterns: Vec<PatternOperand>,
    pub(crate) maxfiles: i64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ParsedCliHead {
    names: ProgramNames,
    options: Options,
    pub(crate) input: OsString,
    pattern_arguments: Vec<OsString>,
}

pub(crate) fn program_names(argv0: &OsStr) -> ProgramNames {
    let invocation = argv0.to_os_string();
    let bytes = argv0.as_bytes();
    let basename = bytes.rsplit(|byte| *byte == b'/').next().unwrap_or(bytes);

    ProgramNames {
        invocation,
        basename: OsString::from_vec(basename.to_vec()),
    }
}

pub(crate) fn usage(progname: &OsStr) -> Vec<u8> {
    let mut rendered = b"usage: ".to_vec();
    rendered.extend_from_slice(progname.as_bytes());
    rendered.extend_from_slice(b" [-ks] [-f prefix] [-n number] file args ...\n");
    rendered
}

pub(crate) fn parse_c_long(bytes: &[u8]) -> ParsedLong {
    let mut index = 0;
    while index < bytes.len() && matches!(bytes[index], b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
    {
        index += 1;
    }

    let mut negative = false;
    if index < bytes.len() {
        match bytes[index] {
            b'+' => index += 1,
            b'-' => {
                negative = true;
                index += 1;
            }
            _ => {}
        }
    }

    let digits_start = index;
    let limit = if negative {
        (i64::MAX as u64) + 1
    } else {
        i64::MAX as u64
    };
    let mut magnitude = 0_u64;
    let mut overflowed = false;

    while index < bytes.len() && bytes[index].is_ascii_digit() {
        let digit = u64::from(bytes[index] - b'0');
        if magnitude > (limit - digit) / 10 {
            overflowed = true;
            magnitude = limit;
        } else if !overflowed {
            magnitude = magnitude * 10 + digit;
        }
        index += 1;
    }

    if index == digits_start {
        return ParsedLong {
            value: 0,
            end: 0,
            overflowed: false,
        };
    }

    let value = if negative {
        if magnitude == (i64::MAX as u64) + 1 {
            i64::MIN
        } else {
            -(magnitude as i64)
        }
    } else {
        magnitude as i64
    };

    ParsedLong {
        value,
        end: index,
        overflowed,
    }
}

pub(crate) fn parse_repetition(argument: &[u8]) -> Result<i64, CsplitError> {
    let value_bytes = argument.strip_prefix(b"{").unwrap_or(argument);
    let parsed = parse_c_long(value_bytes);
    let valid_close = value_bytes.get(parsed.end) == Some(&b'}');

    if parsed.value < 0 || parsed.overflowed || !valid_close {
        return Err(message(Some(value_bytes.to_vec()), "bad repetition count"));
    }

    Ok(parsed.value)
}

pub(crate) fn maxfiles_for_suffix(sufflen: i64) -> Result<i64, CsplitError> {
    let mut maxfiles = 1_i64;
    for index in 0..sufflen {
        if maxfiles > LONG_MAX / 10 {
            return Err(message(
                Some(sufflen.to_string().into_bytes()),
                if index == 18 {
                    "suffix too long (limit 18)"
                } else {
                    "suffix too long"
                },
            ));
        }
        maxfiles *= 10;
    }
    Ok(maxfiles)
}

pub(crate) fn scan_options(
    invocation: &Invocation,
) -> Result<(Options, Vec<OsString>), CsplitError> {
    let mut options = Options {
        prefix: b"xx".to_vec(),
        sufflen: 2,
        sflag: false,
        kflag: false,
    };
    let mut operands = Vec::new();
    let mut index = 1;

    while index < invocation.argv.len() {
        let argument = &invocation.argv[index];
        let bytes = argument.as_os_str().as_bytes();

        if bytes == b"--" {
            operands.extend(invocation.argv[index + 1..].iter().cloned());
            break;
        }
        if bytes.len() < 2 || bytes[0] != b'-' || bytes == b"-" {
            if invocation.posixly_correct {
                operands.extend(invocation.argv[index..].iter().cloned());
                break;
            }
            operands.push(argument.clone());
            index += 1;
            continue;
        }

        let mut option_index = 1;
        while option_index < bytes.len() {
            let option = bytes[option_index];
            match option {
                b'k' => options.kflag = true,
                b's' => options.sflag = true,
                b'f' | b'n' => {
                    let value = if option_index + 1 < bytes.len() {
                        OsString::from_vec(bytes[option_index + 1..].to_vec())
                    } else {
                        index += 1;
                        let Some(value) = invocation.argv.get(index) else {
                            return Err(getopt_error(option, true));
                        };
                        value.clone()
                    };

                    if option == b'f' {
                        options.prefix = value.as_os_str().as_bytes().to_vec();
                    } else {
                        let value_bytes = value.as_os_str().as_bytes();
                        let parsed = parse_c_long(value_bytes);
                        if parsed.value <= 0 || parsed.end != value_bytes.len() || parsed.overflowed
                        {
                            return Err(message(Some(value_bytes.to_vec()), "bad suffix length"));
                        }
                        options.sufflen = parsed.value;
                    }
                    break;
                }
                _ => return Err(getopt_error(option, false)),
            }
            option_index += 1;
        }
        index += 1;
    }

    Ok((options, operands))
}

pub(crate) fn parse_head(invocation: &Invocation) -> Result<ParsedCliHead, CsplitError> {
    let argv0 = invocation
        .argv
        .first()
        .map(OsString::as_os_str)
        .unwrap_or_else(|| OsStr::new("csplit"));
    let names = program_names(argv0);
    let (options, operands) = scan_options(invocation)?;

    let suffix_width =
        usize::try_from(options.sufflen).map_err(|_| message(None, "name too long"))?;
    if options
        .prefix
        .len()
        .checked_add(suffix_width)
        .is_none_or(|length| length >= PATH_MAX)
    {
        return Err(message(None, "name too long"));
    }

    let mut operands = operands.into_iter();
    let Some(input) = operands.next() else {
        return Err(CsplitError {
            diagnostic: Diagnostic::Usage,
        });
    };

    Ok(ParsedCliHead {
        names,
        options,
        input,
        pattern_arguments: operands.collect(),
    })
}

pub(crate) fn finish_parse(head: ParsedCliHead) -> Result<ParsedCli, CsplitError> {
    let maxfiles = maxfiles_for_suffix(head.options.sufflen)?;
    let mut patterns = Vec::new();
    let mut arguments = head.pattern_arguments.into_iter().peekable();
    while let Some(argument) = arguments.next() {
        let expr = argument.as_os_str().as_bytes().to_vec();
        let mut reps = 0;
        if let Some(repetition) = arguments.peek() {
            if repetition.as_os_str().as_bytes().first() == Some(&b'{') {
                reps = parse_repetition(repetition.as_os_str().as_bytes())?;
                arguments.next();
            }
        }
        patterns.push(PatternOperand { expr, reps });
    }

    Ok(ParsedCli {
        names: head.names,
        options: head.options,
        input: head.input,
        patterns,
        maxfiles,
    })
}

pub(crate) fn parse(invocation: &Invocation) -> Result<ParsedCli, CsplitError> {
    finish_parse(parse_head(invocation)?)
}

fn message(argument: Option<Vec<u8>>, text: &'static str) -> CsplitError {
    CsplitError {
        diagnostic: Diagnostic::Message {
            prefix: DiagnosticPrefix::Program,
            argument,
            text,
        },
    }
}

fn getopt_error(option: u8, missing_argument: bool) -> CsplitError {
    let mut message = if missing_argument {
        b"option requires an argument -- '".to_vec()
    } else {
        b"invalid option -- '".to_vec()
    };
    message.push(option);
    message.push(b'\'');
    CsplitError {
        diagnostic: Diagnostic::Getopt {
            message,
            include_usage: true,
        },
    }
}

#[cfg(test)]
#[path = "cli/tests.rs"]
mod tests;
