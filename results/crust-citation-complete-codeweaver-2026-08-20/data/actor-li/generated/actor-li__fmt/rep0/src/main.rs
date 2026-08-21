mod fmt;
mod locale;
mod runtime;

use std::io;
use std::process::ExitCode;

fn main() -> ExitCode {
    #[cfg(unix)]
    sigpipe::reset();

    let context = runtime::ProcessContext::capture();
    let file_source = runtime::RealFileSource;
    let stdin = io::stdin();
    let stdout = io::stdout();
    let stderr = io::stderr();
    let mut stdin = stdin.lock();
    let mut stdout = stdout.lock();
    let mut stderr = stderr.lock();

    match fmt::run(&context, &mut stdin, &mut stdout, &mut stderr, &file_source) {
        Ok(status) => ExitCode::from(status),
        Err(_) => ExitCode::FAILURE,
    }
}
