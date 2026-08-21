mod csplit;
mod regex_compat;

use std::process::ExitCode;

fn main() -> ExitCode {
    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    let stderr = std::io::stderr();

    csplit::run_process(
        std::env::args_os(),
        stdin.lock(),
        stdout.lock(),
        stderr.lock(),
        csplit::RealFileSystem,
        regex_compat::GlibcBreCompiler,
    )
}
