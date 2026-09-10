use std::fmt;
use std::sync::atomic::{AtomicBool, Ordering};

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum tokens_t {
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

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum AstNodeType {
    LAMBDA_EXPR,
    APPLICATION,
    VAR,
    DEFINITION,
}

#[derive(Debug, Clone)]
pub struct LambdaExpression {
    pub parameter: String,
    pub type_: String,
    pub body: Option<Box<AstNode>>,
}

#[derive(Debug, Clone)]
pub struct Application {
    pub function: Option<Box<AstNode>>,
    pub argument: Option<Box<AstNode>>,
}

#[derive(Debug, Clone)]
pub struct Variable {
    pub name: String,
    pub type_: String,
}

#[derive(Debug, Clone)]
pub enum AstNodeUnion {
    LambdaExpr(LambdaExpression),
    Application(Application),
    Variable(Variable),
}

#[derive(Debug, Clone)]
pub struct AstNode {
    pub type_: AstNodeType,
    pub node: AstNodeUnion,
}

impl Default for AstNode {
    fn default() -> Self {
        AstNode {
            type_: AstNodeType::VAR,
            node: AstNodeUnion::Variable(Variable {
                name: String::new(),
                type_: String::new(),
            }),
        }
    }
}

static VERBOSE_MODE: AtomicBool = AtomicBool::new(false);

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
    if !is_verbose() {
        return;
    }
    let _ = format;
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
            if let AstNodeUnion::LambdaExpr(le) = &node.node {
                append_to_buffer(buffer, "(@");
                append_to_buffer(buffer, &le.parameter);
                append_to_buffer(buffer, " : ");
                append_to_buffer(buffer, &le.type_);
                append_to_buffer(buffer, " .");
                if let Some(body) = &le.body {
                    append_ast_to_buffer(buffer, body);
                }
                append_to_buffer(buffer, ") ");
            }
        }
        AstNodeType::APPLICATION => {
            if let AstNodeUnion::Application(app) = &node.node {
                append_to_buffer(buffer, "(");
                if let Some(f) = &app.function {
                    append_ast_to_buffer(buffer, f);
                }
                if let Some(a) = &app.argument {
                    append_ast_to_buffer(buffer, a);
                }
                append_to_buffer(buffer, ") ");
            }
        }
        AstNodeType::VAR => {
            if let AstNodeUnion::Variable(v) = &node.node {
                append_to_buffer(buffer, "(");
                append_to_buffer(buffer, &v.name);
                if !v.type_.is_empty() {
                    append_to_buffer(buffer, " : ");
                    append_to_buffer(buffer, &v.type_);
                }
                append_to_buffer(buffer, ") ");
            }
        }
        AstNodeType::DEFINITION => {
            if let AstNodeUnion::Variable(v) = &node.node {
                append_to_buffer(buffer, "(");
                append_to_buffer(buffer, &v.name);
                append_to_buffer(buffer, ") ");
            } else {
                append_to_buffer(buffer, "(UNKNOWN) ");
            }
        }
    }
}

pub fn ast_to_string(node: &AstNode) -> String {
    let mut buffer = String::with_capacity(1024);
    append_ast_to_buffer(&mut buffer, node);
    buffer
}
