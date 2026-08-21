#![forbid(unsafe_code)]

use std::fs;
use std::os::unix::process::ExitStatusExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

struct TempDir(PathBuf);

impl TempDir {
    fn new() -> Self {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock must be after the Unix epoch")
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "actor-li-join-process-{}-{nonce}",
            std::process::id()
        ));
        fs::create_dir(&path).expect("create process-test directory");
        Self(path)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn closed_stdout_uses_default_sigpipe_disposition() {
    let temp = TempDir::new();
    let left = temp.path().join("left");
    let right = temp.path().join("right");

    let mut left_record = b"k ".to_vec();
    left_record.extend(std::iter::repeat_n(b'x', 2 * 1024 * 1024));
    left_record.push(b'\n');
    fs::write(&left, left_record).expect("write first input");
    fs::write(&right, b"k right\n").expect("write second input");

    let mut child = Command::new(env!("CARGO_BIN_EXE_join"))
        .arg(left)
        .arg(right)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn join");

    drop(child.stdout.take());
    let output = child.wait_with_output().expect("wait for join");

    assert_eq!(output.status.signal(), Some(13));
    assert!(output.stderr.is_empty());
}
