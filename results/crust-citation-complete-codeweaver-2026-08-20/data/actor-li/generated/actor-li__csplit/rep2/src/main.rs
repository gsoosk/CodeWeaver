#![forbid(unsafe_code)]
#![allow(dead_code)]

mod bre;
mod cli;
mod csplit;
mod split_io;

use std::env;
use std::ffi::OsStr;
use std::io::{self, BufWriter};
use std::process::ExitCode;

use cli::{program_names, Invocation};
use csplit::{render_diagnostic, run, Streams};
use split_io::RealRuntime;

fn main() -> ExitCode {
    let argv: Vec<_> = env::args_os().collect();
    let argv0 = argv
        .first()
        .map(|value| value.as_os_str())
        .unwrap_or_else(|| OsStr::new("csplit"));
    let names = program_names(argv0);
    let invocation = Invocation {
        argv,
        posixly_correct: env::var_os("POSIXLY_CORRECT").is_some(),
    };

    let stdin = io::stdin();
    let stdout = io::stdout();
    let stderr = io::stderr();
    let mut stdin = stdin.lock();
    let mut stdout = BufWriter::new(stdout.lock());
    let mut stderr = stderr.lock();
    let mut streams = Streams {
        stdin: &mut stdin,
        stdout: &mut stdout,
        stderr: &mut stderr,
    };
    let mut runtime = RealRuntime;

    match run(&invocation, &mut streams, &mut runtime) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            let _ = render_diagnostic(&error, &names, streams.stderr);
            ExitCode::from(1)
        }
    }
}
