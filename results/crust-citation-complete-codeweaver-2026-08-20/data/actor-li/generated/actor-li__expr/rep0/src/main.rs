#![forbid(unsafe_code)]

#[cfg(unix)]
fn main() {
    use std::os::unix::ffi::OsStringExt;

    let mut argv = std::env::args_os();
    let program_name = argv.next().unwrap_or_default().into_vec();
    let expression_args = argv.map(OsStringExt::into_vec).collect();
    let regex_engine = actor_li_expr::PosixRegexEngine::new();
    let mut stdout = std::io::stdout().lock();
    let mut stderr = std::io::stderr().lock();

    let status = actor_li_expr::run(
        &program_name,
        expression_args,
        &regex_engine,
        &mut stdout,
        &mut stderr,
    );
    std::process::exit(status);
}

#[cfg(not(unix))]
compile_error!("the expr translation requires Unix byte-oriented process arguments");
