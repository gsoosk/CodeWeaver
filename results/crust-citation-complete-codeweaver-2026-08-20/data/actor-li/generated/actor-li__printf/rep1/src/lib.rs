#![forbid(unsafe_code)]

pub mod format;
pub mod number;
pub mod printf;

pub use printf::{run, ExitStatus};

#[cfg(test)]
pub(crate) mod test_support;
