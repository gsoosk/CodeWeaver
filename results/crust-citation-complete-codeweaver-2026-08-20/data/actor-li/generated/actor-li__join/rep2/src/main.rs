mod join;

use std::env;
use std::os::unix::ffi::OsStringExt;
use std::process::ExitCode;

fn main() -> ExitCode {
    let argv = env::args_os()
        .map(OsStringExt::into_vec)
        .collect::<Vec<_>>();
    let posixly_correct = env::var_os("POSIXLY_CORRECT").is_some();

    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    let stderr = std::io::stderr();
    let mut stdin = stdin.lock();
    let mut stdout = stdout.lock();
    let mut stderr = stderr.lock();
    let mut opener = join::RealFileOpener;

    ExitCode::from(join::run(
        &argv,
        posixly_correct,
        &mut stdin,
        &mut stdout,
        &mut stderr,
        &mut opener,
    ))
}
