use crate::{common, hash_table};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::sync::atomic::{AtomicU32, Ordering};

/// Mirrors C's `static int n` counter in `alpha_convert`.
static ALPHA_COUNTER: AtomicU32 = AtomicU32::new(1);

pub fn parse_token(token: char) -> common::tokens_t {
    if token == '(' {
        common::tokens_t::L_PAREN
    } else if token == ')' {
        common::tokens_t::R_PAREN
    } else if token == '@' {
        common::tokens_t::LAMBDA
    } else if token == '.' {
        common::tokens_t::DOT
    } else if is_variable(token) {
        common::tokens_t::VARIABLE
    } else if token == ' ' {
        common::tokens_t::WHITESPACE
    } else if token == '\n' {
        common::tokens_t::NEWLINE
    } else if token == '=' {
        common::tokens_t::EQ
    } else if token == '"' {
        common::tokens_t::QUOTE
    } else if token == ':' {
        common::tokens_t::COLON
    } else {
        common::tokens_t::ERROR
    }
}
pub fn p_print_token(token: common::tokens_t) {
    match token {
        common::tokens_t::L_PAREN => print!("( "),
        common::tokens_t::R_PAREN => print!(") "),
        common::tokens_t::LAMBDA => print!("@ "),
        common::tokens_t::DOT => print!(". "),
        common::tokens_t::VARIABLE => print!("VARIABLE "),
        common::tokens_t::WHITESPACE => print!("WHITESPACE "),
        common::tokens_t::NEWLINE => print!("NEWLINE "),
        common::tokens_t::EQ => print!("= "),
        _ => print!("ERROR "),
    }
}
pub fn p_print_astNode_type(n: &common::AstNode) {
    match n.type_ {
        common::AstNodeType::LAMBDA_EXPR => println!("AstNode Type: LAMBDA_EXPR"),
        common::AstNodeType::APPLICATION => println!("AstNode Type: APPLICATION"),
        common::AstNodeType::VAR => println!("AstNode Type: VAR"),
        common::AstNodeType::DEFINITION => println!("AstNode Type: DEFINITION"),
    }
}
pub fn print_ast(node: &common::AstNode) {
    match node.type_ {
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(lambda_expr) = &node.node {
                print!(
                    "(LAMBDA {} : {}",
                    lambda_expr.parameter, lambda_expr.type_
                );
                if let Some(body) = &lambda_expr.body {
                    print_ast(body);
                }
                print!(") ");
            }
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(application) = &node.node {
                print!("(APP ");
                if let Some(function) = &application.function {
                    print_ast(function);
                }
                if let Some(argument) = &application.argument {
                    print_ast(argument);
                }
                print!(") ");
            }
        }
        common::AstNodeType::VAR => {
            if let common::AstNodeUnion::Variable(variable) = &node.node {
                print!("(VAR {} ", variable.name);
                if !variable.type_.is_empty() {
                    print!(": {}", variable.type_);
                }
                print!(")");
            }
        }
        common::AstNodeType::DEFINITION => {
            if let common::AstNodeUnion::Variable(variable) = &node.node {
                print!("(DEFINITION {}) ", variable.name);
            }
        }
    }
}
pub fn is_variable(token: char) -> bool {
    let cmp = token as i32;
    if cmp == '_' as i32 {
        return true;
    }
    (97..=122).contains(&cmp) || (65..=90).contains(&cmp)
}

/// Internal `fgetc`-equivalent used throughout the grammar (mirrors C's
/// `next()`, declared in `io.c` but consumed directly here for lexing).
fn read_char(in_: &mut File) -> char {
    let mut buf = [0u8; 1];
    match in_.read(&mut buf) {
        Ok(0) => common::EOF_SENTINEL,
        Ok(_) => buf[0] as char,
        Err(_) => common::EOF_SENTINEL,
    }
}

pub fn peek(in_: &mut File) -> char {
    let mut buf = [0u8; 1];
    match in_.read(&mut buf) {
        Ok(0) => common::EOF_SENTINEL,
        Ok(_) => {
            let _ = in_.seek(SeekFrom::Current(-1));
            buf[0] as char
        }
        Err(_) => common::EOF_SENTINEL,
    }
}
pub fn peek_print(in_: &mut File, n: usize) {
    let mut buf: Vec<u8> = Vec::with_capacity(n);
    for _ in 0..n {
        let mut b = [0u8; 1];
        match in_.read(&mut b) {
            Ok(0) => break,
            Ok(_) => buf.push(b[0]),
            Err(_) => break,
        }
    }
    let s: String = buf.iter().map(|&b| b as char).collect();
    print!("{}", s);
    if !buf.is_empty() {
        let _ = in_.seek(SeekFrom::Current(-(buf.len() as i64)));
    }
}
pub fn consume(t: common::tokens_t, in_: &mut File, expected: &str) {
    let c = read_char(in_);
    let p = parse_token(c);
    if p != t {
        expect(expected, c);
    }
}
pub fn create_variable(name: &str, type_: &str) -> common::AstNode {
    common::AstNode {
        type_: common::AstNodeType::VAR,
        node: common::AstNodeUnion::Variable(common::Variable {
            name: name.to_string(),
            type_: type_.to_string(),
        }),
    }
}
pub fn create_application(function: &common::AstNode, argument: &common::AstNode) -> common::AstNode {
    common::AstNode {
        type_: common::AstNodeType::APPLICATION,
        node: common::AstNodeUnion::Application(common::Application {
            function: Some(Box::new(crate::reducer::deepcopy(function))),
            argument: Some(Box::new(crate::reducer::deepcopy(argument))),
        }),
    }
}
pub fn create_lambda(variable: &str, body: &common::AstNode, type_: &str) -> common::AstNode {
    common::AstNode {
        type_: common::AstNodeType::LAMBDA_EXPR,
        node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
            parameter: variable.to_string(),
            type_: type_.to_string(),
            body: Some(Box::new(crate::reducer::deepcopy(body))),
        }),
    }
}
pub fn alpha_convert(old: &str) -> String {
    let n = ALPHA_COUNTER.fetch_add(1, Ordering::SeqCst);
    format!("{}_{}", old, n)
}
pub fn is_used(table: &hash_table::HashTable, variable: &str) -> bool {
    table.table_exists(variable)
}
pub fn parse_space_chars(in_: &mut File) {
    let mut c = peek(in_);
    while c == ' ' || c == '\n' || c == '\t' {
        read_char(in_);
        c = peek(in_);
    }
}
pub fn parse_lambda(table: &mut hash_table::HashTable, in_: &mut File) -> common::AstNode {
    if parse_token(peek(in_)) != common::tokens_t::VARIABLE {
        expect("A variable", peek(in_));
    }

    let var = parse_variable(in_);
    let mut new_var: Option<String> = None;
    if is_used(table, &var) {
        if table.search(&var).is_some() {
            let error_msg = common::format(
                "definition already exists",
                format_args!(
                    "A definition with name {} already exists. Cannot use same name for lambda abstraction.\n",
                    var
                ),
            );
            common::error(&error_msg, file!(), line!() as i32, "parse_lambda");
        }
        let nv = alpha_convert(&var);
        table.insert(&nv, common::AstNode::default());
        new_var = Some(nv);
    } else {
        table.insert(&var, common::AstNode::default());
    }

    parse_space_chars(in_);

    consume(common::tokens_t::COLON, in_, ":");

    parse_space_chars(in_);

    if parse_token(peek(in_)) != common::tokens_t::VARIABLE {
        common::error(
            "Lambda abstractions should be typed.",
            file!(),
            line!() as i32,
            "parse_lambda",
        );
    }
    let type_ = parse_type(table, in_);

    consume(common::tokens_t::DOT, in_, ".");

    let mut body = parse_expression(table, in_);

    if let Some(nv) = &new_var {
        crate::reducer::replace(&mut body, &var, nv);
        common::print_verbose(
            "Alpha converted",
            format_args!("Alpha converted {} to {}\n", var, nv),
        );
        return create_lambda(nv, &body, &type_);
    }
    create_lambda(&var, &body, &type_)
}
pub fn parse_expression(table: &mut hash_table::HashTable, in_: &mut File) -> common::AstNode {
    while parse_token(peek(in_)) == common::tokens_t::WHITESPACE
        || parse_token(peek(in_)) == common::tokens_t::NEWLINE
    {
        read_char(in_);
    }
    let scanned = parse_token(peek(in_));

    if scanned == common::tokens_t::ERROR {
        println!("Error: {} is  a valid token", peek(in_));
        std::process::exit(1);
    }

    if scanned == common::tokens_t::LAMBDA {
        read_char(in_);
        return parse_lambda(table, in_);
    } else if scanned == common::tokens_t::L_PAREN {
        read_char(in_);
        let expr = parse_expression(table, in_);

        print_ast(&expr);
        let next_token = parse_token(peek(in_));

        if next_token == common::tokens_t::WHITESPACE {
            let expr_2 = parse_expression(table, in_);
            let application = common::AstNode {
                type_: common::AstNodeType::APPLICATION,
                node: common::AstNodeUnion::Application(common::Application {
                    function: Some(Box::new(expr)),
                    argument: Some(Box::new(expr_2)),
                }),
            };

            consume(common::tokens_t::R_PAREN, in_, ")");

            return application;
        }
        consume(common::tokens_t::R_PAREN, in_, ")");
        return expr;
    } else if scanned == common::tokens_t::VARIABLE {
        let var_name = parse_variable(in_);

        if var_name == "def" {
            parse_definition(table, in_);
            if peek(in_) != common::EOF_SENTINEL {
                return parse_expression(table, in_);
            }
            return common::AstNode::default();
        } else if var_name == "import" {
            parse_import(table, in_);
            if peek(in_) != common::EOF_SENTINEL {
                return parse_expression(table, in_);
            }
        } else if var_name == "type" {
            parse_type_definition(table, in_);
            if peek(in_) != common::EOF_SENTINEL {
                return parse_expression(table, in_);
            }
        }

        let mut type_ = String::new();

        parse_space_chars(in_);
        if !table.table_exists(&var_name) {
            if parse_token(peek(in_)) != common::tokens_t::COLON {
                let error_msg = common::format(
                    "Constant not typed",
                    format_args!(
                        "Constant Variable {} is not typed. Please provide a type.\n",
                        var_name
                    ),
                );
                common::error(&error_msg, file!(), line!() as i32, "parse_expression");
            }
            consume(common::tokens_t::COLON, in_, ":");
            parse_space_chars(in_);
            type_ = parse_type(table, in_);
        }

        let mut variable = create_variable(&var_name, &type_);
        if table.search(&var_name).is_some() {
            variable.type_ = common::AstNodeType::DEFINITION;
        }
        return variable;
    }
    common::AstNode::default()
}
pub fn parse_import(table: &mut hash_table::HashTable, in_: &mut File) {
    consume(common::tokens_t::WHITESPACE, in_, "a whitespace");

    consume(common::tokens_t::QUOTE, in_, "\"");

    let mut file_path = String::new();
    let mut next_token = read_char(in_);
    let mut n = parse_token(next_token);

    while n != common::tokens_t::QUOTE {
        if file_path.len() < 99 {
            file_path.push(next_token);
        } else {
            common::error(
                "File path is too long. Please make sure it is less than 100 characters.",
                file!(),
                line!() as i32,
                "parse_import",
            );
        }

        next_token = read_char(in_);
        n = parse_token(next_token);
    }

    if n != common::tokens_t::QUOTE {
        expect("a closing quote", next_token);
    }

    let mut imported_file = crate::io::get_file(&file_path, "r")
        .unwrap_or_else(|e| panic!("ERROR: Could not open file {}: {}", file_path, e));

    let mut imported_tkn = peek(&mut imported_file);
    while imported_tkn != common::EOF_SENTINEL {
        let scanned = parse_token(imported_tkn);
        parse_space_chars(&mut imported_file);
        if scanned == common::tokens_t::VARIABLE {
            let var_name = parse_variable(&mut imported_file);
            if var_name == "def" {
                parse_definition(table, &mut imported_file);
            } else if var_name == "type" {
                parse_type_definition(table, &mut imported_file);
            } else {
                let error_msg = common::format(
                    "Expected a definition",
                    format_args!(
                        "Expected a definition in the imported file, but got {}\n",
                        var_name
                    ),
                );
                common::error(&error_msg, file!(), line!() as i32, "parse_import");
            }
        }
        imported_tkn = peek(&mut imported_file);
    }
}
pub fn parse_definition(table: &mut hash_table::HashTable, in_: &mut File) {
    consume(common::tokens_t::WHITESPACE, in_, "a whitespace");

    if parse_token(peek(in_)) != common::tokens_t::VARIABLE {
        expect("a variable", peek(in_));
    }

    let def_name = parse_variable(in_);

    consume(common::tokens_t::WHITESPACE, in_, "a whitespace");

    consume(common::tokens_t::EQ, in_, "=");

    consume(common::tokens_t::WHITESPACE, in_, "a whitespace");

    let definition = parse_expression(table, in_);
    table.insert(&def_name, definition);
}
pub fn is_uppercase(c: char) -> bool {
    ('A'..='Z').contains(&c)
}
pub fn parse_type_definition(types_table: &mut hash_table::HashTable, in_: &mut File) {
    let mut next_token = read_char(in_);
    let mut n = parse_token(next_token);
    if n != common::tokens_t::WHITESPACE {
        expect(" ", next_token);
    }

    next_token = peek(in_);
    n = parse_token(next_token);
    if n != common::tokens_t::VARIABLE {
        expect("a type definition", next_token);
    }

    if !is_uppercase(next_token) {
        common::error(
            "Type names must start with an uppercase letter",
            file!(),
            line!() as i32,
            "parse_type_definition",
        );
    }

    let type_name = parse_variable(in_);
    if types_table.table_exists(&type_name) {
        let error_msg = common::format(
            "Type already defined",
            format_args!("Type {} was already defined.\n", type_name),
        );
        common::error(&error_msg, file!(), line!() as i32, "parse_type_definition");
    }
    types_table.insert(&type_name, common::AstNode::default());
}
pub fn parse_type(types_table: &mut hash_table::HashTable, in_: &mut File) -> String {
    let mut type_name = String::new();
    let token = read_char(in_);

    if !is_uppercase(token) {
        common::error(
            "Types should start with an uppercase letter.",
            file!(),
            line!() as i32,
            "parse_type",
        );
    }

    type_name.push(token);

    while is_variable(peek(in_)) {
        type_name.push(read_char(in_));
    }

    if !types_table.table_exists(&type_name) {
        let error_msg = common::format(
            "Type not defined",
            format_args!("Type {} was not defined.\n", type_name),
        );
        common::error(&error_msg, file!(), line!() as i32, "parse_type");
    }
    type_name
}
pub fn parse_variable(in_: &mut File) -> String {
    let mut variable_name = String::new();
    while is_variable(peek(in_)) {
        variable_name.push(read_char(in_));
    }
    variable_name
}
pub fn expect(expected: &str, received: char) {
    println!("Syntax Error: Expected {} , received {} ", expected, received);
    std::process::exit(1);
}
pub fn free_ast(node: &mut common::AstNode) {
    // Rust owns the tree via Box/Option; dropping is automatic. Reset to the
    // empty sentinel to mirror C's "node is gone" semantics for callers that
    // continue to hold the (now-freed-in-C) pointer.
    *node = common::AstNode::default();
}

#[cfg(test)]
mod tests {
    use super::*;

    // Fixture-based: File used as an in-memory byte cursor via small real temp
    // files (the scaffold pins parser fns to &mut File, so no Cursor mock).

    fn write_temp_file(name: &str, content: &str) -> File {
        let path = std::env::temp_dir().join(format!(
            "lce_parser_test_{}_{}",
            std::process::id(),
            name
        ));
        {
            let mut f = std::fs::File::create(&path).expect("create temp file failed");
            use std::io::Write;
            f.write_all(content.as_bytes()).expect("write temp file failed");
        }
        std::fs::OpenOptions::new()
            .read(true)
            .open(&path)
            .expect("reopen temp file failed")
    }

    #[test]
    fn test_parse_token_maps_chars_to_tokens() {
        assert_eq!(parse_token('('), common::tokens_t::L_PAREN);
        assert_eq!(parse_token(')'), common::tokens_t::R_PAREN);
        assert_eq!(parse_token('@'), common::tokens_t::LAMBDA);
        assert_eq!(parse_token('.'), common::tokens_t::DOT);
        assert_eq!(parse_token('x'), common::tokens_t::VARIABLE);
        assert_eq!(parse_token('_'), common::tokens_t::VARIABLE);
        assert_eq!(parse_token(' '), common::tokens_t::WHITESPACE);
        assert_eq!(parse_token('\n'), common::tokens_t::NEWLINE);
        assert_eq!(parse_token('='), common::tokens_t::EQ);
        assert_eq!(parse_token('"'), common::tokens_t::QUOTE);
        assert_eq!(parse_token(':'), common::tokens_t::COLON);
        assert_eq!(parse_token('1'), common::tokens_t::ERROR);
    }

    #[test]
    fn test_is_variable_accepts_underscore_and_letters() {
        assert!(is_variable('_'));
        assert!(is_variable('a'));
        assert!(is_variable('Z'));
        assert!(!is_variable('1'));
        assert!(!is_variable(' '));
    }

    #[test]
    fn test_alpha_convert_appends_monotonic_suffix() {
        let first = alpha_convert("x");
        let second = alpha_convert("x");
        assert!(first.starts_with("x_"));
        assert!(second.starts_with("x_"));
        let n1: u32 = first["x_".len()..].parse().unwrap();
        let n2: u32 = second["x_".len()..].parse().unwrap();
        assert_eq!(n2, n1 + 1);
    }

    #[test]
    fn test_parse_expression_builds_expected_ast_shape() {
        let mut file = write_temp_file("expr", "@x : Bool.x");
        let mut table = hash_table::HashTable::new();
        table.insert("Bool", common::AstNode::default());
        let result = parse_expression(&mut table, &mut file);
        assert_eq!(common::ast_to_string(&result), "(@x : Bool .(x) ) ");
    }
}