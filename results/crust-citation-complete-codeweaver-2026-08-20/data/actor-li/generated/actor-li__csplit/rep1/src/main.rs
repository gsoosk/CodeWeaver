mod boundary;
mod cli;
mod csplit;
#[cfg(test)]
mod test_support;

use std::env;
use std::io::{self, Write};
use std::process::ExitCode;

use boundary::{PosixRegexCompiler, RealFileSystem};
use csplit::CsplitError;

fn execute() -> Result<(), CsplitError> {
    let invocation = cli::parse(
        env::args_os().collect(),
        env::var_os("POSIXLY_CORRECT").is_some(),
    )?;
    let mut file_system = RealFileSystem;
    let mut regex_compiler = PosixRegexCompiler;
    let mut stdout = io::stdout().lock();

    csplit::run(
        invocation,
        &mut file_system,
        &mut regex_compiler,
        &mut stdout,
    )
}

fn render_failure(error: &CsplitError, stderr: &mut dyn Write) -> ExitCode {
    let _ = error.write_to(stderr);
    let _ = stderr.flush();
    ExitCode::from(error.exit_status())
}

fn main() -> ExitCode {
    match execute() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            let mut stderr = io::stderr().lock();
            render_failure(&error, &mut stderr)
        }
    }
}

#[cfg(test)]
mod tests {
    use std::process::ExitCode;

    use crate::csplit::usage;
    use crate::test_support::MockWriter;

    use super::render_failure;

    #[test]
    fn validation_errors_return_one_even_when_stderr_fails() {
        let mut stderr = MockWriter {
            fail: true,
            ..MockWriter::default()
        };
        let status = render_failure(&usage(b"alias"), &mut stderr);
        assert_eq!(status, ExitCode::FAILURE);
    }
}
