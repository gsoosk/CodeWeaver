use std::fmt;
use std::io::Write;
use std::process;
use std::sync::atomic::{AtomicBool, Ordering};

#[derive(Debug, PartialEq, Eq)]
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

pub fn print_ast_verbose(n: &AstNode) {
    if !VERBOSE_MODE.load(Ordering::SeqCst) {
        return;
    }
    let lambda_ast = ast_to_string(n);
    println!("{}", lambda_ast);
}

pub fn print_verbose(format: &str, args: fmt::Arguments) {
    let _ = format;
    if !VERBOSE_MODE.load(Ordering::SeqCst) {
        return;
    }
    println!();
    print!("{}", args);
    let _ = std::io::stdout().flush();
}

pub fn error(msg: &str, file: &str, line: i32, func: &str) {
    eprintln!("ERROR: {} at {}:{} in {}()", msg, file, line, func);
    process::exit(1);
}

pub fn format(fmt: &str, args: fmt::Arguments) -> String {
    let _ = fmt;
    fmt::format(args)
}

pub fn append_to_buffer(buffer: &mut String, str: &str) {
    buffer.push_str(str);
}

pub fn append_ast_to_buffer(buffer: &mut String, node: &AstNode) {
    match &node.node {
        AstNodeUnion::LambdaExpr(lambda_expr) => {
            append_to_buffer(buffer, "(@");
            append_to_buffer(buffer, &lambda_expr.parameter);
            append_to_buffer(buffer, " : ");
            append_to_buffer(buffer, &lambda_expr.type_);
            append_to_buffer(buffer, " .");
            if let Some(body) = &lambda_expr.body {
                append_ast_to_buffer(buffer, body);
            }
            append_to_buffer(buffer, ") ");
        }
        AstNodeUnion::Application(application) => {
            append_to_buffer(buffer, "(");
            if let Some(function) = &application.function {
                append_ast_to_buffer(buffer, function);
            }
            if let Some(argument) = &application.argument {
                append_ast_to_buffer(buffer, argument);
            }
            append_to_buffer(buffer, ") ");
        }
        AstNodeUnion::Variable(variable) => {
            append_to_buffer(buffer, "(");
            append_to_buffer(buffer, &variable.name);
            match node.type_ {
                AstNodeType::VAR => {
                    if !variable.type_.is_empty() {
                        append_to_buffer(buffer, " : ");
                        append_to_buffer(buffer, &variable.type_);
                    }
                }
                _ => {}
            }
            append_to_buffer(buffer, ") ");
        }
    }
}

pub fn ast_to_string(node: &AstNode) -> String {
    let mut buffer = String::new();
    append_ast_to_buffer(&mut buffer, node);
    buffer
}
