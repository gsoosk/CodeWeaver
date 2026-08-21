mod printf;

use std::env;
use std::ffi::OsString;
use std::io::{self, BufWriter, Write};
use std::os::unix::ffi::OsStrExt;
use std::process::ExitCode;

fn main() -> Result<ExitCode, printf::RunError> {
    let os_args: Vec<OsString> = env::args_os().collect();
    let args: Vec<Vec<u8>> = os_args
        .iter()
        .map(|arg| arg.as_os_str().as_bytes().to_vec())
        .collect();

    let stdout = io::stdout();
    let stderr = io::stderr();
    let mut stdout = BufWriter::new(stdout.lock());
    let mut stderr = stderr.lock();

    let run_result = printf::run(&args, &mut stdout, &mut stderr);
    let flush_result = stdout.flush();
    let status = run_result?;
    flush_result?;

    Ok(ExitCode::from(status))
}
