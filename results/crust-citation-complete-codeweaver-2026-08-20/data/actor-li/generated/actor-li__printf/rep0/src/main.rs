mod format;
mod numparse;
mod printf;

#[cfg(unix)]
use std::os::unix::ffi::OsStrExt;
use std::process::ExitCode;

#[cfg(not(unix))]
compile_error!("the byte-oriented printf process adapter requires a Unix target");

#[cfg(unix)]
fn raw_args() -> Vec<Vec<u8>> {
    std::env::args_os()
        .map(|argument| argument.as_os_str().as_bytes().to_vec())
        .collect()
}

fn main() -> ExitCode {
    let args = raw_args();
    let mut output = printf::StdioOutput::new();

    match printf::run(&args, &mut output) {
        Ok(outcome) => ExitCode::from(outcome.status),
        Err(_) => ExitCode::FAILURE,
    }
}
