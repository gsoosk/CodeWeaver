#![forbid(unsafe_code)]

use actor_li_printf::printf::{BufferMode, CStdout};
use actor_li_printf::{run, ExitStatus};
use std::env;
use std::io::{self, IsTerminal, Write};
use std::os::unix::ffi::OsStringExt;
use std::process::ExitCode;

fn main() -> ExitCode {
    let owned_args: Vec<Vec<u8>> = env::args_os().map(|arg| arg.into_vec()).collect();
    let args: Vec<&[u8]> = owned_args.iter().map(|arg| arg.as_slice()).collect();

    let stdout = io::stdout();
    let stderr = io::stderr();
    let mode = if stdout.is_terminal() {
        BufferMode::Line
    } else {
        BufferMode::Full
    };
    let mut stdout = CStdout::new(stdout.lock(), mode);
    let mut stderr = stderr.lock();

    let result = run(&args, &mut stdout, &mut stderr);
    let recovery_flush = if result.is_err() {
        stdout.flush()
    } else {
        Ok(())
    };

    match (result, recovery_flush) {
        (Ok(ExitStatus::Success), Ok(())) => ExitCode::SUCCESS,
        _ => ExitCode::from(1),
    }
}
