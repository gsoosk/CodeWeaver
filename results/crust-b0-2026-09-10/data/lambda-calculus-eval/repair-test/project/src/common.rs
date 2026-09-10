use std::sync::atomic::{AtomicBool, Ordering};

/// Global verbose flag, toggled by callers (e.g. via a `-v` CLI flag).
pub static VERBOSE: AtomicBool = AtomicBool::new(false);

/// Enable or disable verbose output.
pub fn set_verbose(v: bool) {
    VERBOSE.store(v, Ordering::SeqCst);
}

/// Check whether verbose output is currently enabled.
pub fn is_verbose() -> bool {
    VERBOSE.load(Ordering::SeqCst)
}

/// The different kinds of AST nodes used by the lambda calculus evaluator.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AstNodeKind {
    Var,
    Abs,
    App,
}

/// Print a message only if verbose mode is enabled.
pub fn print_verbose(msg: &str) {
    if is_verbose() {
        println!("{}", msg);
    }
}

/// Print an AST-related message (tagged with the node kind) only if verbose
/// mode is enabled.
pub fn print_ast_verbose(kind: AstNodeKind, msg: &str) {
    if is_verbose() {
        println!("[{:?}] {}", kind, msg);
    }
}
