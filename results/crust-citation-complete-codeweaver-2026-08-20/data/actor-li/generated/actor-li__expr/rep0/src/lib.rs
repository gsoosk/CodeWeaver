#![forbid(unsafe_code)]

mod expr;
mod posix_bre;

pub use expr::run;
pub use posix_bre::{PosixRegexEngine, RegexCompileError, RegexEngine, RegexOutcome, Span};
