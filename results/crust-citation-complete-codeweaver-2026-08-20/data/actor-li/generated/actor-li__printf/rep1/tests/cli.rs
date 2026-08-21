#![forbid(unsafe_code)]

use std::ffi::OsString;
use std::fs::{self, OpenOptions};
use std::os::unix::ffi::OsStringExt;
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};

#[test]
fn cli_test_module_is_wired() {
    let _ = Command::new(env!("CARGO_BIN_EXE_printf"));
}

mod process_boundaries {
    use super::{command, merged_output_path, OsString, OsStringExt, Output, Stdio};
    use std::fs;
    use std::os::unix::process::CommandExt;

    #[test]
    fn no_format_emits_exact_usage_and_status_one() {
        let output = command().output().unwrap();

        assert_failure(&output);
        assert!(output.stdout.is_empty());
        assert_eq!(output.stderr, b"usage: printf format [argument ...]\n");
    }

    #[test]
    fn one_optional_first_double_dash_is_ignored() {
        let output = command().args(["--", "[%s]", "value"]).output().unwrap();

        assert!(output.status.success());
        assert_eq!(output.stdout, b"[value]");
        assert!(output.stderr.is_empty());

        let output = command().arg("--").output().unwrap();
        assert_failure(&output);
        assert_eq!(output.stderr, b"usage: printf format [argument ...]\n");
    }

    #[test]
    fn raw_argv0_basename_is_retained_for_diagnostics() {
        let alias = OsString::from_vec(b"/tmp/raw-\xff-alias".to_vec());
        let format = OsString::from_vec(b"\\q".to_vec());
        let output = command().arg0(alias).arg(format).output().unwrap();

        assert_failure(&output);
        assert_eq!(output.stdout, b"q");
        assert_eq!(
            output.stderr,
            b"raw-\xff-alias: unknown escape sequence `\\q'\n"
        );
    }

    #[test]
    fn non_utf8_format_and_operand_bytes_round_trip() {
        let format = OsString::from_vec(b"<%s>:\xff".to_vec());
        let operand = OsString::from_vec(vec![0x80, b'X']);
        let output = command().arg(format).arg(operand).output().unwrap();

        assert!(output.status.success());
        assert_eq!(output.stdout, b"<\x80X>:\xff");
        assert!(output.stderr.is_empty());
    }

    #[test]
    fn merged_stream_keeps_warning_before_residual_stdout() {
        let (path, file) = merged_output_path();
        let stdout_file = file.try_clone().unwrap();
        let status = command()
            .arg("abc\\")
            .stdout(Stdio::from(stdout_file))
            .stderr(Stdio::from(file))
            .status()
            .unwrap();

        assert_eq!(status.code(), Some(1));
        assert_eq!(
            fs::read(&path.0).unwrap(),
            b"printf: null escape sequence\nabc"
        );
    }

    fn assert_failure(output: &Output) {
        assert_eq!(output.status.code(), Some(1));
    }
}

fn command() -> Command {
    Command::new(env!("CARGO_BIN_EXE_printf"))
}

fn merged_output_path() -> (TemporaryPath, fs::File) {
    static NEXT_PATH: AtomicU64 = AtomicU64::new(0);

    let sequence = NEXT_PATH.fetch_add(1, Ordering::Relaxed);
    let path = std::env::temp_dir().join(format!(
        "actor-li-printf-merged-{}-{sequence}",
        std::process::id()
    ));
    let file = OpenOptions::new()
        .create_new(true)
        .read(true)
        .write(true)
        .open(&path)
        .unwrap();
    (TemporaryPath(path), file)
}

struct TemporaryPath(PathBuf);

impl Drop for TemporaryPath {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
