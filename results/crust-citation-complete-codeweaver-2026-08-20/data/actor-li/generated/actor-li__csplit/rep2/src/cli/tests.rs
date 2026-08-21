use std::ffi::{OsStr, OsString};
use std::os::unix::ffi::{OsStrExt, OsStringExt};

use super::{
    maxfiles_for_suffix, parse, parse_c_long, parse_repetition, program_names, scan_options, usage,
    Invocation, PATH_MAX,
};
use crate::csplit::{render_diagnostic, Diagnostic};

fn invocation(arguments: &[&str], posixly_correct: bool) -> Invocation {
    Invocation {
        argv: arguments.iter().map(OsString::from).collect(),
        posixly_correct,
    }
}

fn message(error: crate::csplit::CsplitError) -> (Option<Vec<u8>>, &'static str) {
    match error.diagnostic {
        Diagnostic::Message { argument, text, .. } => (argument, text),
        diagnostic => panic!("unexpected diagnostic: {diagnostic:?}"),
    }
}

fn rendered(error: crate::csplit::CsplitError, argv0: &OsStr) -> Vec<u8> {
    let mut stderr = Vec::new();
    render_diagnostic(&error, &program_names(argv0), &mut stderr).unwrap();
    stderr
}

#[test]
fn defaults() {
    let parsed = parse(&invocation(&["csplit", "input"], false)).unwrap();
    assert_eq!(parsed.options.prefix, b"xx");
    assert_eq!(parsed.options.sufflen, 2);
    assert!(!parsed.options.sflag);
    assert!(!parsed.options.kflag);
}

#[test]
fn clustered_and_attached_options() {
    let parsed = parse(&invocation(
        &["csplit", "-ksfout-", "-n3", "input", "2"],
        false,
    ))
    .unwrap();
    assert!(parsed.options.kflag);
    assert!(parsed.options.sflag);
    assert_eq!(parsed.options.prefix, b"out-");
    assert_eq!(parsed.options.sufflen, 3);
}

#[test]
fn double_dash_ends_options() {
    let (_, operands) = scan_options(&invocation(&["csplit", "--", "input", "-1"], false)).unwrap();
    assert_eq!(operands, [OsString::from("input"), OsString::from("-1")]);
}

#[test]
fn permutation_preserves_operand_order_and_consumes_option_values() {
    let (options, operands) = scan_options(&invocation(
        &["./main", "input", "-f", "part-", "2", "-n3", "{1}", "tail"],
        false,
    ))
    .unwrap();
    assert_eq!(options.prefix, b"part-");
    assert_eq!(options.sufflen, 3);
    assert_eq!(
        operands,
        [
            OsString::from("input"),
            OsString::from("2"),
            OsString::from("{1}"),
            OsString::from("tail"),
        ]
    );
}

#[test]
fn required_option_value_may_look_like_option_terminator() {
    let error = scan_options(&invocation(&["./main", "-n", "--", "input"], false)).unwrap_err();
    assert_eq!(
        rendered(error, OsStr::new("./main")),
        b"main: --: bad suffix length\n"
    );
}

#[test]
fn options_after_operands_without_posixly_correct() {
    let (options, operands) =
        scan_options(&invocation(&["csplit", "input", "-s", "2"], false)).unwrap();
    assert!(options.sflag);
    assert_eq!(operands, [OsString::from("input"), OsString::from("2")]);
}

#[test]
fn options_after_operands_with_posixly_correct() {
    let (options, operands) =
        scan_options(&invocation(&["csplit", "input", "-s", "2"], true)).unwrap();
    assert!(!options.sflag);
    assert_eq!(
        operands,
        [
            OsString::from("input"),
            OsString::from("-s"),
            OsString::from("2")
        ]
    );
}

#[test]
fn full_invocation_and_basename_are_distinct() {
    let names = program_names(OsStr::new("../bin/main"));
    assert_eq!(names.invocation, "../bin/main");
    assert_eq!(names.basename, "main");
}

#[test]
fn invocation_names_and_usage_preserve_non_utf8_bytes() {
    let argv0 = OsString::from_vec(vec![b'.', b'.', b'/', b'b', b'i', b'n', b'/', b'm', 0xff]);
    let names = program_names(&argv0);
    assert_eq!(names.invocation.as_os_str().as_bytes(), b"../bin/m\xff");
    assert_eq!(names.basename.as_os_str().as_bytes(), b"m\xff");
    assert_eq!(
        usage(&names.basename),
        b"usage: m\xff [-ks] [-f prefix] [-n number] file args ...\n"
    );
}

#[test]
fn missing_option_value_text() {
    let error = scan_options(&invocation(&["./main", "-n"], false)).unwrap_err();
    match &error.diagnostic {
        Diagnostic::Getopt {
            message,
            include_usage,
        } => {
            assert_eq!(message, b"option requires an argument -- 'n'");
            assert!(*include_usage);
        }
        diagnostic => panic!("unexpected diagnostic: {diagnostic:?}"),
    }
    assert_eq!(
        rendered(error, OsStr::new("./main")),
        b"./main: option requires an argument -- 'n'\n\
usage: main [-ks] [-f prefix] [-n number] file args ...\n"
    );
}

#[test]
fn unknown_option_text() {
    let error = scan_options(&invocation(&["./main", "input", "-1"], false)).unwrap_err();
    match error.diagnostic {
        Diagnostic::Getopt { message, .. } => {
            assert_eq!(message, b"invalid option -- '1'");
        }
        diagnostic => panic!("unexpected diagnostic: {diagnostic:?}"),
    }
}

#[test]
fn getopt_diagnostic_uses_full_invocation_then_basename_usage() {
    let error = scan_options(&invocation(&["../bin/main", "input", "-x"], false)).unwrap_err();
    assert_eq!(
        rendered(error, OsStr::new("../bin/main")),
        b"../bin/main: invalid option -- 'x'\n\
usage: main [-ks] [-f prefix] [-n number] file args ...\n"
    );
}

#[test]
fn raw_byte_prefixes() {
    let raw = OsString::from_vec(vec![b'-', b'f', 0xff]);
    let invocation = Invocation {
        argv: vec![OsString::from("csplit"), raw, OsString::from("input")],
        posixly_correct: false,
    };
    let (options, _) = scan_options(&invocation).unwrap();
    assert_eq!(options.prefix, [0xff]);
}

#[test]
fn c_long_leading_whitespace() {
    assert_eq!(parse_c_long(b" \t\n42x").value, 42);
    assert_eq!(parse_c_long(b" \t\n42x").end, 5);
    assert_eq!(parse_c_long(b"  x").end, 0);
}

#[test]
fn c_long_without_digits_leaves_end_at_start() {
    for value in [
        b"".as_slice(),
        b" ".as_slice(),
        b" +x".as_slice(),
        b"-".as_slice(),
    ] {
        assert_eq!(
            parse_c_long(value),
            super::ParsedLong {
                value: 0,
                end: 0,
                overflowed: false,
            }
        );
    }
}

#[test]
fn c_long_sign() {
    assert_eq!(parse_c_long(b"+17").value, 17);
    assert_eq!(parse_c_long(b"-17").value, -17);
    assert_eq!(parse_c_long(b"-9223372036854775808").value, i64::MIN);
}

#[test]
fn c_long_exact_limits_do_not_overflow() {
    let positive = parse_c_long(b"9223372036854775807!");
    assert_eq!(positive.value, i64::MAX);
    assert_eq!(positive.end, 19);
    assert!(!positive.overflowed);

    let negative = parse_c_long(b"-9223372036854775808!");
    assert_eq!(negative.value, i64::MIN);
    assert_eq!(negative.end, 20);
    assert!(!negative.overflowed);
}

#[test]
fn c_long_overflow() {
    let positive = parse_c_long(b"92233720368547758080");
    assert_eq!(positive.value, i64::MAX);
    assert!(positive.overflowed);
    let negative = parse_c_long(b"-92233720368547758080");
    assert_eq!(negative.value, i64::MIN);
    assert!(negative.overflowed);
}

#[test]
fn repetition_empty() {
    assert_eq!(parse_repetition(b"{}").unwrap(), 0);
}

#[test]
fn repetition_zero() {
    assert_eq!(parse_repetition(b"{0}").unwrap(), 0);
}

#[test]
fn repetition_two() {
    assert_eq!(parse_repetition(b"{2}").unwrap(), 2);
}

#[test]
fn repetition_accepts_c_whitespace_and_sign() {
    assert_eq!(parse_repetition(b"{ \t+2}").unwrap(), 2);
    assert_eq!(parse_repetition(b"{-0}").unwrap(), 0);
}

#[test]
fn repetition_rejects_negative_and_preserves_raw_argument() {
    let error = parse_repetition(b"{-1}tail").unwrap_err();
    assert_eq!(
        message(error),
        (Some(b"-1}tail".to_vec()), "bad repetition count")
    );
}

#[test]
fn repetition_malformed() {
    let error = parse_repetition(b"{abc}").unwrap_err();
    assert_eq!(
        message(error),
        (Some(b"abc}".to_vec()), "bad repetition count")
    );
}

#[test]
fn repetition_trailing_text() {
    assert_eq!(parse_repetition(b"{1}junk").unwrap(), 1);
}

#[test]
fn repetition_look_ahead_uses_only_the_next_arguments_first_byte() {
    let parsed = parse(&invocation(
        &["csplit", "input", "2", "{1}junk", "4", "x{2}"],
        false,
    ))
    .unwrap();
    assert_eq!(parsed.patterns.len(), 3);
    assert_eq!(parsed.patterns[0].expr, b"2");
    assert_eq!(parsed.patterns[0].reps, 1);
    assert_eq!(parsed.patterns[1].expr, b"4");
    assert_eq!(parsed.patterns[1].reps, 0);
    assert_eq!(parsed.patterns[2].expr, b"x{2}");
    assert_eq!(parsed.patterns[2].reps, 0);
}

#[test]
fn suffix_width_eighteen() {
    assert_eq!(maxfiles_for_suffix(18).unwrap(), 1_000_000_000_000_000_000);
}

#[test]
fn suffix_width_nineteen() {
    let error = maxfiles_for_suffix(19).unwrap_err();
    assert_eq!(
        message(error),
        (Some(b"19".to_vec()), "suffix too long (limit 18)")
    );
}

#[test]
fn suffix_validation_uses_c_numeric_rules() {
    let parsed = parse(&invocation(&["csplit", "-n", " \t+3", "input"], false)).unwrap();
    assert_eq!(parsed.options.sufflen, 3);

    let error = parse(&invocation(&["csplit", "-n", "3 ", "input"], false)).unwrap_err();
    assert_eq!(message(error), (Some(b"3 ".to_vec()), "bad suffix length"));
}

#[test]
fn filename_capacity_checks_raw_prefix_bytes_at_path_max_boundary() {
    let accepted = OsString::from_vec(vec![0xff; PATH_MAX - 3]);
    let rejected = OsString::from_vec(vec![0xff; PATH_MAX - 2]);

    let accepted = Invocation {
        argv: vec![
            OsString::from("csplit"),
            OsString::from("-f"),
            accepted,
            OsString::from("input"),
        ],
        posixly_correct: false,
    };
    assert!(parse(&accepted).is_ok());

    let rejected = Invocation {
        argv: vec![
            OsString::from("csplit"),
            OsString::from("-f"),
            rejected,
            OsString::from("input"),
        ],
        posixly_correct: false,
    };
    assert_eq!(
        message(parse(&rejected).unwrap_err()),
        (None, "name too long")
    );
}

#[test]
fn suffix_overflow_precedes_repetition_validation() {
    let error = parse(&invocation(
        &["csplit", "-n19", "input", "2", "{bad}"],
        false,
    ))
    .unwrap_err();
    assert_eq!(
        message(error),
        (Some(b"19".to_vec()), "suffix too long (limit 18)")
    );
}

#[test]
fn missing_input_precedes_suffix_overflow() {
    let error = parse(&invocation(&["csplit", "-n19"], false)).unwrap_err();
    assert!(matches!(error.diagnostic, Diagnostic::Usage));
}

#[test]
fn reserved_suffix_calculation() {
    let parsed = parse(&invocation(&["csplit", "-n", "2", "input"], false)).unwrap();
    assert_eq!(parsed.maxfiles - 1, 99);
}
