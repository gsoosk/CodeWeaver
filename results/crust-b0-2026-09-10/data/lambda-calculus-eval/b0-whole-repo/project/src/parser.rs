use crate::{common, hash_table};
use crate::{io, reducer};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::sync::atomic::{AtomicI64, Ordering};

fn read_char(in_: &mut File) -> char {
    let mut buf = [0u8; 1];
    match in_.read(&mut buf) {
        Ok(1) => buf[0] as char,
        _ => '\u{0}',
    }
}

pub fn parse_token(token: char) -> common::tokens_t {
    use common::tokens_t::*;
    if token == '(' {
        L_PAREN
    } else if token == ')' {
        R_PAREN
    } else if token == '@' {
        LAMBDA
    } else if token == '.' {
        DOT
    } else if is_variable(token) {
        VARIABLE
    } else if token == ' ' {
        WHITESPACE
    } else if token == '\n' {
        NEWLINE
    } else if token == '=' {
        EQ
    } else if token == '"' {
        QUOTE
    } else if token == ':' {
        COLON
    } else {
        ERROR
    }
}

pub fn p_print_token(token: common::tokens_t) {
    use common::tokens_t::*;
    match token {
        L_PAREN => print!("( "),
        R_PAREN => print!(") "),
        LAMBDA => print!("@ "),
        DOT => print!(". "),
        VARIABLE => print!("VARIABLE "),
        WHITESPACE => print!("WHITESPACE "),
        NEWLINE => print!("NEWLINE "),
        EQ => print!("= "),
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
            if let common::AstNodeUnion::LambdaExpr(le) = &node.node {
                print!("(LAMBDA {} : {}", le.parameter, le.type_);
                if let Some(body) = &le.body {
                    print_ast(body);
                }
                print!(") ");
            }
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(app) = &node.node {
                print!("(APP ");
                if let Some(f) = &app.function {
                    print_ast(f);
                }
                if let Some(a) = &app.argument {
                    print_ast(a);
                }
                print!(") ");
            }
        }
        common::AstNodeType::VAR => {
            if let common::AstNodeUnion::Variable(v) = &node.node {
                print!("(VAR {} ", v.name);
                if !v.type_.is_empty() {
                    print!(": {}", v.type_);
                }
                print!(")");
            }
        }
        common::AstNodeType::DEFINITION => {
            if let common::AstNodeUnion::Variable(v) = &node.node {
                print!("(DEFINITION {}) ", v.name);
            }
        }
    }
}

pub fn is_variable(token: char) -> bool {
    if token == '_' {
        return true;
    }
    token.is_ascii_alphabetic()
}

pub fn peek(in_: &mut File) -> char {
    let c = read_char(in_);
    if c != '\u{0}' {
        let _ = in_.seek(SeekFrom::Current(-1));
    }
    c
}

pub fn peek_print(in_: &mut File, n: usize) {
    let mut buf = Vec::new();
    for _ in 0..n {
        let c = read_char(in_);
        if c == '\u{0}' {
            break;
        }
        buf.push(c);
    }
    let s: String = buf.iter().collect();
    print!("{}", s);
    let _ = in_.seek(SeekFrom::Current(-(buf.len() as i64)));
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
            function: Some(Box::new(function.clone())),
            argument: Some(Box::new(argument.clone())),
        }),
    }
}

pub fn create_lambda(variable: &str, body: &common::AstNode, type_: &str) -> common::AstNode {
    common::AstNode {
        type_: common::AstNodeType::LAMBDA_EXPR,
        node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
            parameter: variable.to_string(),
            type_: type_.to_string(),
            body: Some(Box::new(body.clone())),
        }),
    }
}

static N: AtomicI64 = AtomicI64::new(1);

pub fn alpha_convert(old: &str) -> String {
    let n = N.fetch_add(1, Ordering::SeqCst);
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
            let msg = format!(
                "A definition with name {} already exists. Cannot use same name for lambda abstraction.\n",
                var
            );
            common::error(&msg, file!(), line!() as i32, "parse_lambda");
        }
        let nv = alpha_convert(&var);
        table.insert_none(&nv);
        new_var = Some(nv);
    } else {
        table.insert_none(&var);
    }

    parse_space_chars(in_);
    consume(common::tokens_t::COLON, in_, ":");
    parse_space_chars(in_);

    if parse_token(peek(in_)) != common::tokens_t::VARIABLE {
        common::error("Lambda abstractions should be typed.", file!(), line!() as i32, "parse_lambda");
    }
    let type_ = parse_type(table, in_);

    consume(common::tokens_t::DOT, in_, ".");

    let mut body = parse_expression(table, in_);

    if let Some(nv) = new_var {
        reducer::replace(&mut body, &var, &nv);
        let msg = format!("Alpha converted {} to {}\n", var, nv);
        common::print_verbose(&msg, format_args!(""));
        common::AstNode {
            type_: common::AstNodeType::LAMBDA_EXPR,
            node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
                parameter: nv,
                type_,
                body: Some(Box::new(body)),
            }),
        }
    } else {
        common::AstNode {
            type_: common::AstNodeType::LAMBDA_EXPR,
            node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
                parameter: var,
                type_,
                body: Some(Box::new(body)),
            }),
        }
    }
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
            if peek(in_) != '\u{0}' {
                return parse_expression(table, in_);
            }
            return common::AstNode::default();
        } else if var_name == "import" {
            parse_import(table, in_);
            if peek(in_) != '\u{0}' {
                return parse_expression(table, in_);
            }
        } else if var_name == "type" {
            parse_type_definition(table, in_);
            if peek(in_) != '\u{0}' {
                return parse_expression(table, in_);
            }
        }

        let mut type_ = String::new();
        parse_space_chars(in_);
        if !table.table_exists(&var_name) {
            if parse_token(peek(in_)) != common::tokens_t::COLON {
                let msg = format!(
                    "Constant Variable {} is not typed. Please provide a type.\n",
                    var_name
                );
                common::error(&msg, file!(), line!() as i32, "parse_expression");
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

    let mut imported_file = io::get_file(&file_path, "r").unwrap_or_else(|_| {
        common::error(
            &format!("ERROR: Could not open file {}\n", file_path),
            file!(),
            line!() as i32,
            "parse_import",
        );
    });

    loop {
        let imported_tkn = peek(&mut imported_file);
        if imported_tkn == '\u{0}' {
            break;
        }
        let scanned = parse_token(imported_tkn);
        parse_space_chars(&mut imported_file);
        if scanned == common::tokens_t::VARIABLE {
            let var_name = parse_variable(&mut imported_file);
            if var_name == "def" {
                parse_definition(table, &mut imported_file);
            } else if var_name == "type" {
                parse_type_definition(table, &mut imported_file);
            } else {
                let msg = format!(
                    "Expected a definition in the imported file, but got {}\n",
                    var_name
                );
                common::error(&msg, file!(), line!() as i32, "parse_import");
            }
        }
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
    c >= 'A' && c <= 'Z'
}

pub fn parse_type_definition(types_table: &mut hash_table::HashTable, in_: &mut File) {
    let next_token = read_char(in_);
    let n = parse_token(next_token);
    if n != common::tokens_t::WHITESPACE {
        expect(" ", next_token);
    }

    let next_token2 = peek(in_);
    let n2 = parse_token(next_token2);
    if n2 != common::tokens_t::VARIABLE {
        expect("a type definition", next_token2);
    }

    if !is_uppercase(next_token2) {
        common::error(
            "Type names must start with an uppercase letter",
            file!(),
            line!() as i32,
            "parse_type_definition",
        );
    }

    let type_name = parse_variable(in_);
    if types_table.table_exists(&type_name) {
        let msg = format!("Type {} was already defined.\n", type_name);
        common::error(&msg, file!(), line!() as i32, "parse_type_definition");
    }
    types_table.insert_none(&type_name);
}

pub fn parse_type(types_table: &mut hash_table::HashTable, in_: &mut File) -> String {
    let token = read_char(in_);
    if !is_uppercase(token) {
        common::error(
            "Types should start with an uppercase letter.",
            file!(),
            line!() as i32,
            "parse_type",
        );
    }
    let mut type_name = String::new();
    type_name.push(token);
    while is_variable(peek(in_)) {
        type_name.push(read_char(in_));
    }
    if !types_table.table_exists(&type_name) {
        let msg = format!("Type {} was not defined.\n", type_name);
        common::error(&msg, file!(), line!() as i32, "parse_type");
    }
    type_name
}

pub fn parse_variable(in_: &mut File) -> String {
    let mut name = String::new();
    while is_variable(peek(in_)) {
        name.push(read_char(in_));
    }
    name
}

pub fn expect(expected: &str, received: char) {
    println!("Syntax Error: Expected {} , received {} ", expected, received);
    std::process::exit(1);
}

pub fn free_ast(node: &mut common::AstNode) {
    let _ = node;
}
