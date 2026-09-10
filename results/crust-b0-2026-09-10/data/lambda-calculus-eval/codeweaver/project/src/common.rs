use std::fmt;
use std::sync::atomic::{AtomicBool, Ordering};

/// Private-use sentinel char standing in for C's `EOF` (-1) since Rust's
/// `char` has no EOF value. Chosen because it cannot appear in valid ASCII
/// lambda source. Shared by `io`/`parser` wherever the C compared against EOF.
pub const EOF_SENTINEL: char = '\u{FFFF}';

static VERBOSE_MODE: AtomicBool = AtomicBool::new(false);

#[derive(Debug, PartialEq, Eq)]
pub enum tokens_t{
    L_PAREN,
    R_PAREN,
    LAMBDA,
    DOT,
    VARIABLE,
    ERROR,
    WHITESPACE,
    NEWLINE,
    EQ,
    QUOTE,
    COLON,
} 
#[derive(Debug, PartialEq, Eq)]
pub enum AstNodeType {
LAMBDA_EXPR,
APPLICATION,
VAR,
DEFINITION,
}
#[derive(Debug)]
pub struct LambdaExpression {
pub parameter: String,
pub type_: String,
pub body: Option<Box<AstNode>>,
}
#[derive(Debug)]
pub struct Application {
pub function: Option<Box<AstNode>>,
pub argument: Option<Box<AstNode>>,
}
#[derive(Debug)]
pub struct Variable {
pub name: String,
pub type_: String,
}
#[derive(Debug)]
pub enum AstNodeUnion {
LambdaExpr(LambdaExpression),
Application(Application),
Variable(Variable),
}
#[derive(Debug)]
pub struct AstNode {
pub type_: AstNodeType,
pub node: AstNodeUnion,
}
impl Default for AstNode {
    fn default() -> Self {
        // Empty-VAR sentinel: models C's NULL-valued hash table bucket entry.
        AstNode {
            type_: AstNodeType::VAR,
            node: AstNodeUnion::Variable(Variable {
                name: String::new(),
                type_: String::new(),
            }),
        }
    }
}
pub fn set_verbose(verbose: bool) {
    VERBOSE_MODE.store(verbose, Ordering::SeqCst);
}
fn is_verbose() -> bool {
    VERBOSE_MODE.load(Ordering::SeqCst)
}
pub fn print_ast_verbose(n: &AstNode) {
    if !is_verbose() {
        return;
    }
    let lambda_ast = ast_to_string(n);
    println!("{}", lambda_ast);
}
pub fn print_verbose(format: &str, args: fmt::Arguments) {
    let _ = format;
    if !is_verbose() {
        return;
    }
    println!();
    print!("{}", args);
}
pub fn error(msg: &str, file: &str, line: i32, func: &str) {
    eprintln!("ERROR: {} at {}:{} in {}()", msg, file, line, func);
    std::process::exit(1);
}
pub fn format(fmt: &str, args: fmt::Arguments) -> String {
    let _ = fmt;
    fmt::format(args)
}
pub fn append_to_buffer(buffer: &mut String, str: &str) {
    buffer.push_str(str);
}
pub fn append_ast_to_buffer(buffer: &mut String, node: &AstNode) {
    match node.type_ {
        AstNodeType::LAMBDA_EXPR => {
            if let AstNodeUnion::LambdaExpr(lambda_expr) = &node.node {
                append_to_buffer(buffer, "(@");
                append_to_buffer(buffer, &lambda_expr.parameter);
                append_to_buffer(buffer, " : ");
                append_to_buffer(buffer, &lambda_expr.type_);
                append_to_buffer(buffer, " .");
                if let Some(body) = &lambda_expr.body {
                    append_ast_to_buffer(buffer, body);
                }
                append_to_buffer(buffer, ") ");
            } else {
                append_to_buffer(buffer, "(UNKNOWN) ");
            }
        }
        AstNodeType::APPLICATION => {
            if let AstNodeUnion::Application(application) = &node.node {
                append_to_buffer(buffer, "(");
                if let Some(function) = &application.function {
                    append_ast_to_buffer(buffer, function);
                }
                if let Some(argument) = &application.argument {
                    append_ast_to_buffer(buffer, argument);
                }
                append_to_buffer(buffer, ") ");
            } else {
                append_to_buffer(buffer, "(UNKNOWN) ");
            }
        }
        AstNodeType::VAR => {
            if let AstNodeUnion::Variable(variable) = &node.node {
                append_to_buffer(buffer, "(");
                append_to_buffer(buffer, &variable.name);
                if !variable.type_.is_empty() {
                    append_to_buffer(buffer, " : ");
                    append_to_buffer(buffer, &variable.type_);
                }
                append_to_buffer(buffer, ") ");
            } else {
                append_to_buffer(buffer, "(UNKNOWN) ");
            }
        }
        AstNodeType::DEFINITION => {
            if let AstNodeUnion::Variable(variable) = &node.node {
                append_to_buffer(buffer, "(");
                append_to_buffer(buffer, &variable.name);
                append_to_buffer(buffer, ") ");
            } else {
                append_to_buffer(buffer, "(UNKNOWN) ");
            }
        }
    }
}
pub fn ast_to_string(node: &AstNode) -> String {
    let mut buffer = String::new();
    append_ast_to_buffer(&mut buffer, node);
    buffer
}

#[cfg(test)]
mod tests {
    use super::*;

    // Fixture-based, new tests mirroring the removed C `tests/` style (no
    // mocks: build small AstNode trees by hand and assert on ast_to_string).

    #[test]
    fn test_ast_to_string_var_no_type() {
        let var = AstNode {
            type_: AstNodeType::VAR,
            node: AstNodeUnion::Variable(Variable {
                name: "x".to_string(),
                type_: String::new(),
            }),
        };
        assert_eq!(ast_to_string(&var), "(x) ");
    }

    #[test]
    fn test_ast_to_string_var_with_type() {
        let var = AstNode {
            type_: AstNodeType::VAR,
            node: AstNodeUnion::Variable(Variable {
                name: "x".to_string(),
                type_: "Bool".to_string(),
            }),
        };
        assert_eq!(ast_to_string(&var), "(x : Bool) ");
    }

    #[test]
    fn test_ast_to_string_lambda_expr() {
        let body = AstNode {
            type_: AstNodeType::VAR,
            node: AstNodeUnion::Variable(Variable {
                name: "x".to_string(),
                type_: String::new(),
            }),
        };
        let lambda = AstNode {
            type_: AstNodeType::LAMBDA_EXPR,
            node: AstNodeUnion::LambdaExpr(LambdaExpression {
                parameter: "x".to_string(),
                type_: "Bool".to_string(),
                body: Some(Box::new(body)),
            }),
        };
        assert_eq!(ast_to_string(&lambda), "(@x : Bool .(x) ) ");
    }

    #[test]
    fn test_ast_to_string_application() {
        let func = AstNode {
            type_: AstNodeType::VAR,
            node: AstNodeUnion::Variable(Variable {
                name: "f".to_string(),
                type_: String::new(),
            }),
        };
        let arg = AstNode {
            type_: AstNodeType::VAR,
            node: AstNodeUnion::Variable(Variable {
                name: "y".to_string(),
                type_: String::new(),
            }),
        };
        let app = AstNode {
            type_: AstNodeType::APPLICATION,
            node: AstNodeUnion::Application(Application {
                function: Some(Box::new(func)),
                argument: Some(Box::new(arg)),
            }),
        };
        assert_eq!(ast_to_string(&app), "((f) (y) ) ");
    }

    #[test]
    fn test_default_ast_node_is_empty_var_sentinel() {
        let sentinel = AstNode::default();
        assert_eq!(sentinel.type_, AstNodeType::VAR);
        match &sentinel.node {
            AstNodeUnion::Variable(v) => {
                assert_eq!(v.name, "");
                assert_eq!(v.type_, "");
            }
            _ => panic!("expected Variable variant"),
        }
        assert_eq!(ast_to_string(&sentinel), "() ");
    }
}