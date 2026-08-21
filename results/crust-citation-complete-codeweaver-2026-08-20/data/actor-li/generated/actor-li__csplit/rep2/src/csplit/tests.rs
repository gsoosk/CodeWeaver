use std::cell::RefCell;
use std::ffi::OsString;
use std::io::{BufWriter, Cursor, ErrorKind, Write};
use std::os::unix::ffi::OsStringExt;
use std::rc::Rc;

use super::{render_diagnostic, run, Streams};
use crate::cli::{program_names, Invocation};
use crate::split_io::mock::{FailurePoint, MockRuntime};

struct Outcome {
    success: bool,
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    runtime: MockRuntime,
}

#[derive(Clone)]
struct SharedWriter {
    bytes: Rc<RefCell<Vec<u8>>>,
}

impl Write for SharedWriter {
    fn write(&mut self, buffer: &[u8]) -> std::io::Result<usize> {
        self.bytes.borrow_mut().extend_from_slice(buffer);
        Ok(buffer.len())
    }

    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}

struct FailingWriter;

impl Write for FailingWriter {
    fn write(&mut self, _buffer: &[u8]) -> std::io::Result<usize> {
        Err(std::io::Error::from(ErrorKind::BrokenPipe))
    }

    fn flush(&mut self) -> std::io::Result<()> {
        Err(std::io::Error::from(ErrorKind::BrokenPipe))
    }
}

impl Outcome {
    fn file(&self, path: &[u8]) -> Option<Vec<u8>> {
        self.runtime
            .files
            .get(path)
            .map(|bytes| bytes.borrow().clone())
    }
}

fn invoke(input: &[u8], arguments: &[&[u8]]) -> Outcome {
    invoke_with_input(Some(input), arguments)
}

fn invoke_without_input(arguments: &[&[u8]]) -> Outcome {
    invoke_with_input(None, arguments)
}

fn invoke_with_input(input: Option<&[u8]>, arguments: &[&[u8]]) -> Outcome {
    invoke_with_runtime(input, arguments, MockRuntime::default())
}

fn invoke_with_runtime(
    input: Option<&[u8]>,
    arguments: &[&[u8]],
    mut runtime: MockRuntime,
) -> Outcome {
    let mut argv = vec![OsString::from("./main")];
    argv.extend(
        arguments
            .iter()
            .map(|argument| OsString::from_vec(argument.to_vec())),
    );
    let invocation = Invocation {
        argv,
        posixly_correct: false,
    };
    let input_name = crate::cli::scan_options(&invocation)
        .ok()
        .and_then(|(_, operands)| operands.first().cloned())
        .unwrap_or_else(|| OsString::from("input"));
    if let Some(input) = input {
        runtime
            .files
            .insert(input_name.into_vec(), Rc::new(RefCell::new(input.to_vec())));
    }
    let names = program_names(invocation.argv[0].as_os_str());
    let mut stdin = Cursor::new(Vec::new());
    let mut stdout = Vec::new();
    let mut stderr = Vec::new();
    let result = {
        let mut streams = Streams {
            stdin: &mut stdin,
            stdout: &mut stdout,
            stderr: &mut stderr,
        };
        let result = run(&invocation, &mut streams, &mut runtime);
        if let Err(error) = &result {
            render_diagnostic(error, &names, streams.stderr).unwrap();
        }
        result
    };

    Outcome {
        success: result.is_ok(),
        stdout,
        stderr,
        runtime,
    }
}

mod line_mode {
    use super::*;

    #[test]
    fn no_patterns_on_empty_input() {
        let outcome = invoke(b"", &[b"input"]);
        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(Vec::new()));
        assert_eq!(outcome.stdout, b"0\n");
    }

    #[test]
    fn target_one() {
        let outcome = invoke(b"Single line", &[b"input", b"1"]);
        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(Vec::new()));
        assert_eq!(outcome.file(b"xx01"), Some(b"Single line".to_vec()));
    }

    #[test]
    fn target_current_plus_one() {
        let outcome = invoke(b"one\ntwo\n", &[b"input", b"2"]);
        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"one\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"two\n".to_vec()));
    }

    #[test]
    fn target_out_of_range() {
        let outcome = invoke(b"one\n", &[b"input", b"3"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: 3: out of range\n");
        assert_eq!(outcome.file(b"xx00"), None);
    }

    #[test]
    fn multiple_patterns() {
        let input = b"Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6";
        let outcome = invoke(input, &[b"input", b"2", b"4"]);
        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"Line 1\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"Line 2\nLine 3\n".to_vec()));
        assert_eq!(
            outcome.file(b"xx02"),
            Some(b"Line 4\nLine 5\nLine 6".to_vec())
        );
    }

    #[test]
    fn repeated_multiples() {
        let outcome = invoke(b"1\n2\n3\n4\n5\n", &[b"input", b"2", b"{1}"]);
        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"1\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"2\n3\n".to_vec()));
        assert_eq!(outcome.file(b"xx02"), Some(b"4\n5\n".to_vec()));
    }

    #[test]
    fn backwards_rejection() {
        let outcome = invoke(b"1\n2\n3\n", &[b"input", b"3", b"2"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: 2: can't go backwards\n");
        assert_eq!(outcome.file(b"xx00"), None);
    }

    #[test]
    fn silent_flag() {
        let outcome = invoke(b"one\ntwo", &[b"-s", b"input", b"2"]);
        assert!(outcome.success);
        assert!(outcome.stdout.is_empty());
    }

    #[test]
    fn maximum_file_reservation() {
        let outcome = invoke(
            b"1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n",
            &[b"-n1", b"input", b"1", b"{20}"],
        );

        assert!(outcome.success);
        assert_eq!(
            outcome.runtime.create_order,
            (0..10)
                .map(|index| format!("xx{index}").into_bytes())
                .collect::<Vec<_>>()
        );
        assert_eq!(outcome.file(b"xx0"), Some(Vec::new()));
        for index in 1..=8 {
            assert_eq!(
                outcome.file(format!("xx{index}").as_bytes()),
                Some(format!("{index}\n").into_bytes())
            );
        }
        assert_eq!(outcome.file(b"xx9"), Some(b"9\n10\n11\n12\n".to_vec()));
        assert_eq!(outcome.stdout, b"0\n2\n2\n2\n2\n2\n2\n2\n2\n11\n");
        assert_eq!(outcome.file(b"xx10"), None);
    }

    #[test]
    fn exact_names_counts_and_content() {
        let outcome = invoke(
            b"aa\nb\0hidden\nccc\nlast",
            &[b"-f", b"p\xff-", b"-n3", b"input", b"2", b"4"],
        );

        assert!(outcome.success);
        assert_eq!(
            outcome.runtime.create_order,
            [
                b"p\xff-000".to_vec(),
                b"p\xff-001".to_vec(),
                b"p\xff-002".to_vec(),
            ]
        );
        assert_eq!(outcome.file(b"p\xff-000"), Some(b"aa\n".to_vec()));
        assert_eq!(outcome.file(b"p\xff-001"), Some(b"bccc\n".to_vec()));
        assert_eq!(outcome.file(b"p\xff-002"), Some(b"last".to_vec()));
        assert_eq!(outcome.stdout, b"3\n5\n4\n");
    }
}

mod regex_mode {
    use super::*;

    #[test]
    fn first_chunk_is_never_matched() {
        let outcome = invoke(b"hit\nmiss", &[b"input", b"/hit/"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: hit: no match\n");
        assert_eq!(outcome.file(b"xx00"), None);
    }

    #[test]
    fn no_match() {
        let outcome = invoke(b"one\ntwo", &[b"input", b"/absent/"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: absent: no match\n");
    }

    #[test]
    fn compile_error() {
        let outcome = invoke(b"one\ntwo", &[b"input", b"/[/"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: [: bad regular expression\n");
        assert!(outcome.runtime.create_order.is_empty());
    }

    #[test]
    fn escaped_final_delimiter_is_missing() {
        let outcome = invoke(b"one\ntwo", &[b"input", b"/absent\\/"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: /absent\\/: missing trailing /\n");
        assert!(outcome.runtime.create_order.is_empty());
    }

    #[test]
    fn malformed_offset() {
        let outcome = invoke(b"one\ntwo", &[b"input", b"/two/not-a-number"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: not-a-number: bad offset\n");
        assert!(outcome.runtime.create_order.is_empty());
    }

    #[test]
    fn zero_offset() {
        let outcome = invoke(b"abc\naxc\na.c\ntest", &[b"input", b"/a.c/"]);
        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"abc\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"axc\na.c\ntest".to_vec()));
    }

    #[test]
    fn offset_one() {
        let outcome = invoke(
            b"Line 1\nLine 2\nLine 3\nLine 4\nLine 5",
            &[b"input", b"/Line 2/1"],
        );
        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"Line 1\nLine 2\n".to_vec()));
        assert_eq!(
            outcome.file(b"xx01"),
            Some(b"Line 3\nLine 4\nLine 5".to_vec())
        );
    }

    #[test]
    fn offset_one_at_lf_terminated_eof_creates_empty_remainder() {
        let outcome = invoke(b"pre\ncut\n", &[b"input", b"/cut/1"]);

        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"pre\ncut\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(Vec::new()));
        assert_eq!(outcome.stdout, b"8\n0\n");
    }

    #[test]
    fn repeated_matches() {
        let outcome = invoke(
            b"start\ncut\nmiddle\ncut\nend",
            &[b"input", b"/cut/", b"{1}"],
        );
        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"start\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"cut\nmiddle\n".to_vec()));
        assert_eq!(outcome.file(b"xx02"), Some(b"cut\nend".to_vec()));
    }

    #[test]
    fn negative_offset() {
        let outcome = invoke(b"pre\none\ncut\npost\nend", &[b"input", b"/cut/-1"]);

        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"pre\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"one\ncut\npost\nend".to_vec()));
        assert_eq!(outcome.stdout, b"4\n16\n");
    }

    #[test]
    fn offset_greater_than_one() {
        let outcome = invoke(b"pre\none\ncut\npost\nend", &[b"input", b"/cut/2"]);

        assert!(outcome.success);
        assert_eq!(
            outcome.file(b"xx00"),
            Some(b"pre\none\ncut\npost\n".to_vec())
        );
        assert_eq!(outcome.file(b"xx01"), Some(b"end".to_vec()));
        assert_eq!(outcome.stdout, b"17\n3\n");
    }

    #[test]
    fn offset_past_eof() {
        let outcome = invoke(b"pre\ncut\npost\n", &[b"input", b"/cut/9"]);

        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"pre\ncut\npost\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), None);
        assert_eq!(outcome.stdout, b"13\n");
    }

    #[test]
    fn final_non_lf_match_data_loss() {
        let outcome = invoke(b"pre\ncut", &[b"input", b"/cut/"]);

        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(Vec::new()));
        assert_eq!(outcome.file(b"xx01"), None);
        assert_eq!(outcome.stdout, b"0\n");
    }

    #[test]
    fn percent_positive_offset() {
        let outcome = invoke(b"drop\ncut\nskip\nkeep\n", &[b"input", b"%cut%2"]);

        assert!(outcome.success);
        assert_eq!(outcome.runtime.create_order, [b"xx00".to_vec()]);
        assert_eq!(outcome.file(b"xx00"), Some(b"keep\n".to_vec()));
        assert_eq!(outcome.stdout, b"5\n");
    }

    #[test]
    fn percent_non_positive_offset() {
        let outcome = invoke(b"drop\nprior\ncut\nkeep\n", &[b"input", b"%cut%-1"]);

        assert!(outcome.success);
        assert_eq!(outcome.runtime.create_order, [b"xx00".to_vec()]);
        assert_eq!(outcome.file(b"xx00"), Some(b"prior\ncut\nkeep\n".to_vec()));
        assert_eq!(outcome.stdout, b"15\n");
    }

    #[test]
    fn percent_has_no_suffix_or_count() {
        let outcome = invoke(b"drop\ncut\nkeep\n", &[b"input", b"%cut%"]);

        assert!(outcome.success);
        assert_eq!(outcome.runtime.create_order, [b"xx00".to_vec()]);
        assert_eq!(outcome.file(b"xx00"), Some(b"cut\nkeep\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), None);
        assert_eq!(outcome.stdout, b"9\n");
    }

    #[test]
    fn mixed_line_and_regex_patterns() {
        let outcome = invoke(b"1\n2\n3\n4\n5\n6\n7\n8", &[b"input", b"3", b"/5/", b"7"]);

        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"1\n2\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"3\n4\n".to_vec()));
        assert_eq!(outcome.file(b"xx02"), Some(b"5\n6\n".to_vec()));
        assert_eq!(outcome.file(b"xx03"), Some(b"7\n8".to_vec()));
        assert_eq!(outcome.stdout, b"4\n4\n4\n3\n");
    }
}

mod repair_contract {
    use super::*;

    #[test]
    fn regex_missing_trailing_uses_bad_offset_quirk() {
        let outcome = invoke(b"Line 1\n", &[b"input", b"/Line"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: Line: bad offset\n");
    }

    #[test]
    fn whitespace_in_regex() {
        let outcome = invoke(
            b"no space\nhas space\nno\tspace\nend",
            &[b"input", b"/has space/"],
        );
        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"no space\n".to_vec()));
        assert_eq!(
            outcome.file(b"xx01"),
            Some(b"has space\nno\tspace\nend".to_vec())
        );
    }

    #[test]
    fn multiline_pattern_match() {
        let outcome = invoke(b"start\nmiddle\nend pattern\nafter", &[b"input", b"/end/"]);
        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"start\nmiddle\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"end pattern\nafter".to_vec()));
    }

    #[test]
    fn alternation_in_regex() {
        let outcome = invoke(
            b"apple\nbanana\ncherry\ndate",
            &[b"input", b"/apple\\|cherry/"],
        );
        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"apple\nbanana\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"cherry\ndate".to_vec()));
    }

    #[test]
    fn special_chars_only_on_first_chunk_cleanup() {
        let outcome = invoke(
            b"line [1]\nline (2)\nline {3}\nline .4.",
            &[b"input", b"/\\[1\\]/"],
        );
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: \\[1\\]: no match\n");
        assert_eq!(outcome.file(b"xx00"), None);
    }

    #[test]
    fn unescaped_plus_reports_no_match() {
        let outcome = invoke(b"a\naa\naaa\ntest", &[b"input", b"/a+/"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: a+: no match\n");
    }

    #[test]
    fn strict_line_boundary_reports_no_match() {
        let outcome = invoke(
            b"start test\ntest middle\ntest\nend",
            &[b"input", b"/^test$/"],
        );
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: ^test$: no match\n");
    }

    #[test]
    fn bad_line_number_is_a_getopt_error() {
        let outcome = invoke(b"Line 1\n", &[b"input", b"-1"]);
        assert!(!outcome.success);
        assert_eq!(
            outcome.stderr,
            b"./main: invalid option -- '1'\nusage: main [-ks] [-f prefix] [-n number] file args ...\n"
        );
        assert!(outcome.runtime.create_order.is_empty());
    }

    #[test]
    fn negative_suffix_length() {
        let outcome = invoke(b"Line 1\n", &[b"-n", b"-1", b"input", b"2"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: -1: bad suffix length\n");
        assert!(outcome.runtime.create_order.is_empty());
    }

    #[test]
    fn invalid_repetition() {
        let outcome = invoke(b"Line 1\n", &[b"input", b"2", b"{abc}"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: abc}: bad repetition count\n");
        assert!(outcome.runtime.create_order.is_empty());
    }

    #[test]
    fn suffix_overflow() {
        let outcome = invoke(b"Line 1\n", &[b"-n", b"20", b"input", b"2"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: 20: suffix too long (limit 18)\n");
        assert!(outcome.runtime.create_order.is_empty());
    }

    #[test]
    fn named_input_open_error_precedes_suffix_overflow() {
        let outcome = invoke_without_input(&[b"-n20", b"missing", b"2"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: missing: not found\n");
        assert!(outcome.runtime.create_order.is_empty());
    }

    #[test]
    fn suffix_overflow_precedes_repetition_validation() {
        let outcome = invoke(b"Line 1\n", &[b"-n20", b"input", b"2", b"{not-a-number}"]);
        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: 20: suffix too long (limit 18)\n");
        assert!(outcome.runtime.create_order.is_empty());
    }
}

mod failure_lifecycle {
    use super::*;

    #[test]
    fn no_match_cleanup() {
        let outcome = invoke(b"one\ntwo", &[b"input", b"/missing/"]);
        assert!(!outcome.success);
        assert_eq!(outcome.runtime.create_order, [b"xx00".to_vec()]);
        assert_eq!(outcome.runtime.remove_order, [b"xx00".to_vec()]);
        assert_eq!(outcome.file(b"xx00"), None);
    }

    #[test]
    fn no_match_keep() {
        let outcome = invoke(b"one\ntwo", &[b"-k", b"input", b"/missing/"]);

        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: missing: no match\n");
        assert_eq!(outcome.runtime.create_order, [b"xx00".to_vec()]);
        assert!(outcome.runtime.remove_order.is_empty());
        assert_eq!(outcome.file(b"xx00"), Some(b"one\ntwo".to_vec()));
    }

    #[test]
    fn default_cleanup_after_partial_output() {
        let outcome = invoke(b"one\ntwo\n", &[b"input", b"2", b"5"]);

        assert!(!outcome.success);
        assert_eq!(outcome.stdout, b"4\n");
        assert_eq!(outcome.stderr, b"main: 5: out of range\n");
        assert_eq!(
            outcome.runtime.create_order,
            [b"xx00".to_vec(), b"xx01".to_vec()]
        );
        assert_eq!(
            outcome.runtime.remove_order,
            [b"xx00".to_vec(), b"xx01".to_vec()]
        );
        assert_eq!(outcome.file(b"xx00"), None);
        assert_eq!(outcome.file(b"xx01"), None);
    }

    #[test]
    fn keep_after_partial_output() {
        let outcome = invoke(b"one\ntwo\n", &[b"-k", b"input", b"2", b"5"]);

        assert!(!outcome.success);
        assert_eq!(outcome.stdout, b"4\n");
        assert_eq!(outcome.stderr, b"main: 5: out of range\n");
        assert_eq!(
            outcome.runtime.create_order,
            [b"xx00".to_vec(), b"xx01".to_vec()]
        );
        assert!(outcome.runtime.remove_order.is_empty());
        assert_eq!(outcome.file(b"xx00"), Some(b"one\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"two\n".to_vec()));
    }

    #[test]
    fn keep_retains_untruncated_overflow() {
        let outcome = invoke(b"pre\ncut\nend\n", &[b"-k", b"input", b"/cut/", b"1"]);

        assert!(!outcome.success);
        assert_eq!(outcome.stdout, b"4\n");
        assert_eq!(outcome.stderr, b"main: 1: can't go backwards\n");
        assert!(outcome.runtime.remove_order.is_empty());
        assert_eq!(outcome.file(b"xx00"), Some(b"pre\ncut\n".to_vec()));
    }

    #[test]
    fn existing_file_truncation() {
        let mut runtime = MockRuntime::default();
        runtime.files.insert(
            b"xx00".to_vec(),
            Rc::new(RefCell::new(b"stale bytes that must not survive".to_vec())),
        );

        let outcome = invoke_with_runtime(Some(b"x\nremainder"), &[b"input", b"2"], runtime);

        assert!(outcome.success);
        assert_eq!(outcome.file(b"xx00"), Some(b"x\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"remainder".to_vec()));
        assert_eq!(outcome.stdout, b"2\n9\n");
    }

    #[test]
    fn input_open_error() {
        let outcome = invoke_without_input(&[b"missing", b"2"]);

        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: missing: not found\n");
        assert!(outcome.runtime.create_order.is_empty());
        assert!(outcome.runtime.remove_order.is_empty());
    }

    #[test]
    fn output_open_error() {
        let mut runtime = MockRuntime::default();
        runtime
            .failures
            .insert(FailurePoint::CreateSplit, ErrorKind::PermissionDenied);

        let outcome = invoke_with_runtime(Some(b"one\n"), &[b"input", b"2"], runtime);

        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: xx00: permission denied\n");
        assert_eq!(outcome.runtime.create_order, [b"xx00".to_vec()]);
        assert!(outcome.runtime.remove_order.is_empty());
        assert_eq!(outcome.file(b"xx00"), None);
    }

    #[test]
    fn temporary_file_error() {
        let mut runtime = MockRuntime::default();
        runtime
            .failures
            .insert(FailurePoint::CreateTemp, ErrorKind::PermissionDenied);

        let outcome = invoke_with_runtime(
            Some(b"one\ncut\nend\n"),
            &[b"input", b"2", b"%cut%"],
            runtime,
        );

        assert!(!outcome.success);
        assert_eq!(outcome.stdout, b"4\n");
        assert_eq!(outcome.stderr, b"main: tmpfile: permission denied\n");
        assert_eq!(outcome.runtime.create_order, [b"xx00".to_vec()]);
        assert_eq!(outcome.runtime.remove_order, [b"xx00".to_vec()]);
        assert_eq!(outcome.file(b"xx00"), None);
    }

    #[test]
    fn seek_error() {
        let mut runtime = MockRuntime::default();
        runtime
            .failures
            .insert(FailurePoint::Seek, ErrorKind::PermissionDenied);

        let outcome =
            invoke_with_runtime(Some(b"pre\ncut\nrest\n"), &[b"input", b"/cut/"], runtime);

        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: xx00: can't seek\n");
        assert_eq!(outcome.runtime.remove_order, [b"xx00".to_vec()]);
        assert_eq!(outcome.file(b"xx00"), None);
    }

    #[test]
    fn truncate_error() {
        let mut runtime = MockRuntime::default();
        runtime
            .failures
            .insert(FailurePoint::Truncate, ErrorKind::PermissionDenied);

        let outcome =
            invoke_with_runtime(Some(b"pre\ncut\nrest\n"), &[b"input", b"/cut/"], runtime);

        assert!(!outcome.success);
        assert_eq!(outcome.stdout, b"4\n9\n");
        assert_eq!(outcome.stderr, b"main: overflow: permission denied\n");
        assert_eq!(
            outcome.runtime.remove_order,
            [b"xx00".to_vec(), b"xx01".to_vec()]
        );
        assert_eq!(outcome.file(b"xx00"), None);
        assert_eq!(outcome.file(b"xx01"), None);
    }

    #[test]
    fn finalize_error() {
        let mut runtime = MockRuntime::default();
        runtime
            .failures
            .insert(FailurePoint::Finalize, ErrorKind::PermissionDenied);

        let outcome = invoke_with_runtime(Some(b"pre\ncut"), &[b"input", b"/cut/"], runtime);

        assert!(!outcome.success);
        assert_eq!(outcome.stdout, b"0\n");
        assert_eq!(outcome.stderr, b"main: overflow: permission denied\n");
        assert_eq!(outcome.runtime.remove_order, [b"xx00".to_vec()]);
        assert_eq!(outcome.file(b"xx00"), None);
    }

    #[test]
    fn ignored_file_write_error_is_deferred() {
        let mut runtime = MockRuntime::default();
        runtime
            .failures
            .insert(FailurePoint::Write, ErrorKind::BrokenPipe);

        let outcome = invoke_with_runtime(Some(b"one\ntwo\n"), &[b"input", b"2"], runtime);

        assert!(!outcome.success);
        assert!(outcome.stdout.is_empty());
        assert_eq!(outcome.stderr, b"main: xx00: broken pipe\n");
        assert_eq!(outcome.runtime.remove_order, [b"xx00".to_vec()]);
    }

    #[test]
    fn stdout_errors_are_ignored() {
        let invocation = Invocation {
            argv: vec![
                OsString::from("./main"),
                OsString::from("input"),
                OsString::from("2"),
            ],
            posixly_correct: false,
        };
        let mut runtime = MockRuntime::default();
        runtime.files.insert(
            b"input".to_vec(),
            Rc::new(RefCell::new(b"one\ntwo\n".to_vec())),
        );
        let mut stdin = Cursor::new(Vec::new());
        let mut stdout = FailingWriter;
        let mut stderr = Vec::new();
        let mut streams = Streams {
            stdin: &mut stdin,
            stdout: &mut stdout,
            stderr: &mut stderr,
        };

        assert!(run(&invocation, &mut streams, &mut runtime).is_ok());
        assert_eq!(
            runtime
                .files
                .get(b"xx00".as_slice())
                .unwrap()
                .borrow()
                .as_slice(),
            b"one\n"
        );
        assert_eq!(
            runtime
                .files
                .get(b"xx01".as_slice())
                .unwrap()
                .borrow()
                .as_slice(),
            b"two\n"
        );
    }

    #[test]
    fn ignored_unlink_errors() {
        let mut runtime = MockRuntime::default();
        runtime
            .failures
            .insert(FailurePoint::Remove, ErrorKind::PermissionDenied);

        let outcome = invoke_with_runtime(Some(b"one\ntwo\n"), &[b"input", b"2", b"5"], runtime);

        assert!(!outcome.success);
        assert_eq!(outcome.stderr, b"main: 5: out of range\n");
        assert_eq!(
            outcome.runtime.remove_order,
            [b"xx00".to_vec(), b"xx01".to_vec()]
        );
        assert_eq!(outcome.file(b"xx00"), Some(b"one\n".to_vec()));
        assert_eq!(outcome.file(b"xx01"), Some(b"two\n".to_vec()));
    }

    #[test]
    fn stderr_precedes_buffered_stdout() {
        let invocation = Invocation {
            argv: vec![
                OsString::from("./main"),
                OsString::from("input"),
                OsString::from("2"),
                OsString::from("5"),
            ],
            posixly_correct: false,
        };
        let names = program_names(invocation.argv[0].as_os_str());
        let mut runtime = MockRuntime::default();
        runtime.files.insert(
            b"input".to_vec(),
            Rc::new(RefCell::new(b"one\ntwo\n".to_vec())),
        );
        let merged = Rc::new(RefCell::new(Vec::new()));
        let mut stdin = Cursor::new(Vec::new());
        let mut stdout = BufWriter::new(SharedWriter {
            bytes: merged.clone(),
        });
        let mut stderr = SharedWriter {
            bytes: merged.clone(),
        };

        let result = {
            let mut streams = Streams {
                stdin: &mut stdin,
                stdout: &mut stdout,
                stderr: &mut stderr,
            };
            let result = run(&invocation, &mut streams, &mut runtime);
            render_diagnostic(result.as_ref().unwrap_err(), &names, streams.stderr).unwrap();
            result
        };
        assert!(result.is_err());
        assert!(merged.borrow().ends_with(b"main: 5: out of range\n"));

        drop(stdout);
        assert_eq!(merged.borrow().as_slice(), b"main: 5: out of range\n4\n");
    }
}
