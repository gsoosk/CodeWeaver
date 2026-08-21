mod expr;
mod regex_backend;

use std::env;
use std::io::{self, Write};
use std::os::unix::ffi::OsStringExt;

use expr::{program_basename, run_cli};
use regex_backend::PosixRegexBackend;

fn main() {
    let mut argv = env::args_os();
    let argv0 = argv.next().map(OsStringExt::into_vec).unwrap_or_default();
    let args: Vec<Vec<u8>> = argv.map(OsStringExt::into_vec).collect();
    let regex = PosixRegexBackend::new();

    let stdout = io::stdout();
    let stderr = io::stderr();
    let mut stdout = stdout.lock();
    let mut stderr = stderr.lock();
    let status = match run_cli(&argv0, &args, &regex, &mut stdout, &mut stderr) {
        Ok(status) => status,
        Err(io_error) => {
            let _ = stderr.write_all(program_basename(&argv0));
            let _ = stderr.write_all(b": ");
            let _ = stderr.write_all(io_error.to_string().as_bytes());
            let _ = stderr.write_all(b"\n");
            3
        }
    };
    std::process::exit(status);
}
