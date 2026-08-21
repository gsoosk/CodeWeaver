#![forbid(unsafe_code)]

#[cfg(unix)]
mod cli_process_tests {
    use std::ffi::OsString;
    use std::os::unix::ffi::OsStringExt;
    use std::os::unix::process::CommandExt;
    use std::process::{Command, Output};

    fn invoke(program_name: &[u8], args: &[&[u8]]) -> Output {
        let mut command = Command::new(env!("CARGO_BIN_EXE_expr"));
        command.arg0(OsString::from_vec(program_name.to_vec()));
        command.args(
            args.iter()
                .map(|argument| OsString::from_vec(argument.to_vec())),
        );
        command.output().expect("launch expr binary")
    }

    fn assert_process(
        output: Output,
        expected_status: i32,
        expected_stdout: &[u8],
        expected_stderr: &[u8],
    ) {
        assert_eq!(output.status.code(), Some(expected_status));
        assert_eq!(output.stdout, expected_stdout);
        assert_eq!(output.stderr, expected_stderr);
    }

    #[test]
    fn emits_raw_success_and_false_values_with_one_final_lf() {
        assert_process(
            invoke(
                b"expr",
                &[b"20", b"/", b"5", b"*", b"2", b"-", b"3", b"+", b"1"],
            ),
            0,
            b"6\n",
            b"",
        );
        assert_process(invoke(b"expr", &[b"+0"]), 1, b"+0\n", b"");
        assert_process(invoke(b"expr", &[b"\xff\x80"]), 0, b"\xff\x80\n", b"");
        assert_process(invoke(b"expr", &[b"--", b"--"]), 0, b"--\n", b"");
    }

    #[test]
    fn sends_status_two_diagnostics_only_to_stderr() {
        assert_process(
            invoke(b"expr", &[b"not-a-number", b"*", b"2"]),
            2,
            b"",
            b"expr: number \"not-a-number\" is invalid\n",
        );
        assert_process(
            invoke(b"expr", &[b"7", b"%", b"0"]),
            2,
            b"",
            b"expr: division by zero\n",
        );
        assert_process(
            invoke(b"expr", &[b"input", b":", b"\\"]),
            2,
            b"",
            b"expr: Trailing backslash\n",
        );
    }

    #[test]
    fn uses_raw_runtime_alias_bytes_for_syntax_diagnostics() {
        assert_process(
            invoke(b"/tmp/\xfe-alias", &[]),
            2,
            b"",
            b"\xfe-alias: syntax error\n",
        );
    }

    #[test]
    fn reports_checked_arithmetic_overflow_with_status_three() {
        assert_process(
            invoke(b"expr", &[b"9223372036854775807", b"+", b"1"]),
            3,
            b"",
            b"expr: overflow\n",
        );
    }
}
