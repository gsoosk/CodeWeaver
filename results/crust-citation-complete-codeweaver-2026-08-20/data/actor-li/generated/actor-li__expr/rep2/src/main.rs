mod expr;
mod regex_engine;

use std::io::Write;
use std::os::unix::ffi::OsStrExt;

use regex_engine::PosixRegexEngine;

fn main() {
    let argv = std::env::args_os()
        .map(|argument| argument.as_os_str().as_bytes().to_vec())
        .collect::<Vec<_>>();
    let regex_engine = PosixRegexEngine;
    let outcome = expr::run(&argv, &regex_engine);

    let _ = std::io::stdout().write_all(&outcome.stdout);
    let _ = std::io::stderr().write_all(&outcome.stderr);
    std::process::exit(outcome.status);
}
