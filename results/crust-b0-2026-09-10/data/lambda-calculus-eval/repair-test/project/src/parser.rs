use crate::{common, hash_table};
use common::{AstNode, AstNodeType, Application, LambdaExpression, Variable, tokens_t};
use hash_table::HashTable;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::sync::atomic::{AtomicI64, Ordering};

static N: AtomicI64 = AtomicI64::new(1);

const EOF_CHAR: char = '\u{0}';

fn read_char(in_: &mut File) -> char {
    let mut buf = [0u8; 1];
    match in_.read(&mut buf) {
        Ok(0) => EOF_CHAR,
        Ok(_) => buf[0] as char,
        Err(_) => EOF_CHAR,
    }
}

fn next_char(in_: &mut File) -> char {
    read_char(in_)
}

fn error_msg(msg: &str) -> ! {
    eprint!("{}", msg);
    std::process::exit(1);
}

fn replace_variable(node: &mut AstNode, old: &str, new: &str) {
    match node.node_type {
        AstNodeType::Var | AstNodeType::Definition => {
            if let Some(v) = &mut node.variable {
                if v.name == old {
                    v.name = new.to_string();
                }
            }
        }
        AstNodeType::Application => {
            if let Some(app) = &mut node.application {
                replace_variable(&mut app.function, old, new);
                replace_variable(&mut app.argument, old, new);
            }
        }
        AstNodeType::LambdaExpr => {
            if let Some(le) = &mut node.lambda_expr {
                if le.parameter != old {
                    replace_variable(&mut le.body, old, new);
                }
            }
        }
    }
}

pub fn parse_token(token: char) -> tokens_t {
    if token == '(' {
        tokens_t::L_PAREN
    } else if token == ')' {
        tokens_t::R_PAREN
    } else if token == '@' {
        tokens_t::LAMBDA
    } else if token == '.' {
        tokens_t::DOT
    } else if is_variable(token) {
        tokens_t::VARIABLE
    } else if token == ' ' {
        tokens_t::WHITESPACE
    } else if token == '\n' {
        tokens_t::NEWLINE
    } else if token == '=' {
        tokens_t::EQ
    } else if token == '"' {
        tokens_t::QUOTE
    } else if token == ':' {
        tokens_t::COLON
    } else {
        tokens_t::ERROR
    }
}

pub fn p_print_token(token: tokens_t) {
    match token {
        tokens_t::L_PAREN => print!("( "),
        tokens_t::R_PAREN => print!(") "),
        tokens_t::LAMBDA => print!("@ "),
        tokens_t::DOT => print!(". "),
        tokens_t::VARIABLE => print!("VARIABLE "),
        tokens_t::WHITESPACE => print!("WHITESPACE "),
        tokens_t::NEWLINE => print!("NEWLINE "),
        tokens_t::EQ => print!("= "),
        _ => print!("ERROR "),
    }
}

pub fn p_print_astNode_type(n: &AstNode) {
    match n.node_type {
        AstNodeType::LambdaExpr => println!("AstNode Type: LAMBDA_EXPR"),
        AstNodeType::Application => println!("AstNode Type: APPLICATION"),
        AstNodeType::Var => println!("AstNode Type: VAR"),
        AstNodeType::Definition => println!("AstNode Type: DEFINITION"),
    }
}

pub fn print_ast(node: &AstNode) {
    match node.node_type {
        AstNodeType::LambdaExpr => {
            if let Some(le) = &node.lambda_expr {
                print!("(LAMBDA {} : {}", le.parameter, le.type_);
                print_ast(&le.body);
                print!(") ");
            }
        }
        AstNodeType::Application => {
            if let Some(app) = &node.application {
                print!("(APP ");
                print_ast(&app.function);
                print_ast(&app.argument);
                print!(") ");
            }
        }
        AstNodeType::Var => {
            if let Some(v) = &node.variable {
                print!("(VAR {} ", v.name);
                if let Some(t) = &v.type_ {
                    print!(": {}", t);
                }
                print!(")");
            }
        }
        AstNodeType::Definition => {
            if let Some(v) = &node.variable {
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
    if c != EOF_CHAR {
        let _ = in_.seek(SeekFrom::Current(-1));
    }
    c
}

pub fn peek_print(in_: &mut File, n: usize) {
    let mut buffer: Vec<char> = Vec::with_capacity(n);
    for _ in 0..n {
        let c = read_char(in_);
        if c == EOF_CHAR {
            break;
        }
        buffer.push(c);
    }
    let s: String = buffer.iter().collect();
    print!("{}", s);
    if !buffer.is_empty() {
        let _ = in_.seek(SeekFrom::Current(-(buffer.len() as i64)));
    }
}

pub fn consume(t: tokens_t, in_: &mut File, expected: &str) {
    let c = next_char(in_);
    let p = parse_token(c);
    if p != t {
        expect(expected, c);
    }
}

pub fn create_variable(name: &str, type_: &str) -> AstNode {
    let t = if type_.is_empty() {
        None
    } else {
        Some(type_.to_string())
    };
    AstNode {
        node_type: AstNodeType::Var,
        lambda_expr: None,
        application: None,
        variable: Some(Box::new(Variable {
            name: name.to_string(),
            type_: t,
        })),
    }
}

pub fn create_application(function: &AstNode, argument: &AstNode) -> AstNode {
    AstNode {
        node_type: AstNodeType::Application,
        lambda_expr: None,
        application: Some(Box::new(Application {
            function: Box::new(function.clone()),
            argument: Box::new(argument.clone()),
        })),
        variable: None,
    }
}

pub fn create_lambda(variable: &str, body: &AstNode, type_: &str) -> AstNode {
    AstNode {
        node_type: AstNodeType::LambdaExpr,
        lambda_expr: Some(Box::new(LambdaExpression {
            parameter: variable.to_string(),
            body: Box::new(body.clone()),
            type_: type_.to_string(),
        })),
        application: None,
        variable: None,
    }
}

pub fn alpha_convert(old: &str) -> String {
    let current = N.fetch_add(1, Ordering::SeqCst);
    format!("{}_{}", old, current)
}

pub fn is_used(table: &HashTable, variable: &str) -> bool {
    hash_table::table_exists(table, variable)
}

pub fn parse_space_chars(in_: &mut File) {
    let mut c = peek(in_);
    while c == ' ' || c == '\n' || c == '\t' {
        next_char(in_);
        c = peek(in_);
    }
}

pub fn parse_lambda(table: &mut HashTable, in_: &mut File) -> AstNode {
    let parameter_char = '\0';

    if parse_token(peek(in_)) != tokens_t::VARIABLE {
        expect("A variable", parameter_char);
    }

    let var = parse_variable(in_);
    let mut new_var: Option<String> = None;

    if is_used(table, &var) {
        if hash_table::search(table, &var).is_some() {
            let msg = format!(
                "A definition with name {} already exists. Cannot use same name for lambda abstraction.\n",
                var
            );
            error_msg(&msg);
        }
        let nv = alpha_convert(&var);
        hash_table::insert(table, &nv, None);
        new_var = Some(nv);
    } else {
        hash_table::insert(table, &var, None);
    }

    parse_space_chars(in_);

    consume(tokens_t::COLON, in_, ":");

    parse_space_chars(in_);

    if parse_token(peek(in_)) != tokens_t::VARIABLE {
        error_msg("Lambda abstractions should be typed.");
    }
    let type_ = parse_type(table, in_);

    consume(tokens_t::DOT, in_, ".");

    let mut body = parse_expression(table, in_);

    if let Some(nv) = new_var.clone() {
        replace_variable(&mut body, &var, &nv);
        create_lambda(&nv, &body, &type_)
    } else {
        create_lambda(&var, &body, &type_)
    }
}

pub fn parse_expression(table: &mut HashTable, in_: &mut File) -> AstNode {
    while parse_token(peek(in_)) == tokens_t::WHITESPACE
        || parse_token(peek(in_)) == tokens_t::NEWLINE
    {
        next_char(in_);
    }
    let scanned = parse_token(peek(in_));

    if scanned == tokens_t::ERROR {
        println!("Error: {} is  a valid token", peek(in_));
        std::process::exit(1);
    }

    if scanned == tokens_t::LAMBDA {
        next_char(in_);
        return parse_lambda(table, in_);
    } else if scanned == tokens_t::L_PAREN {
        next_char(in_);
        let expr = parse_expression(table, in_);

        print_ast(&expr);
        let next_token = parse_token(peek(in_));

        if next_token == tokens_t::WHITESPACE {
            let expr_2 = parse_expression(table, in_);
            let application = AstNode {
                node_type: AstNodeType::Application,
                lambda_expr: None,
                application: Some(Box::new(Application {
                    function: Box::new(expr),
                    argument: Box::new(expr_2),
                })),
                variable: None,
            };

            consume(tokens_t::R_PAREN, in_, ")");

            return application;
        }
        consume(tokens_t::R_PAREN, in_, ")");
        return expr;
    } else if scanned == tokens_t::VARIABLE {
        let var_name = parse_variable(in_);

        if var_name == "def" {
            parse_definition(table, in_);
            if peek(in_) != EOF_CHAR {
                return parse_expression(table, in_);
            }
            return AstNode {
                node_type: AstNodeType::Definition,
                lambda_expr: None,
                application: None,
                variable: Some(Box::new(Variable {
                    name: String::new(),
                    type_: None,
                })),
            };
        } else if var_name == "import" {
            parse_import(table, in_);
            if peek(in_) != EOF_CHAR {
                return parse_expression(table, in_);
            }
        } else if var_name == "type" {
            parse_type_definition(table, in_);
            if peek(in_) != EOF_CHAR {
                return parse_expression(table, in_);
            }
        }

        let mut type_str = String::new();

        parse_space_chars(in_);
        if !hash_table::table_exists(table, &var_name) {
            if parse_token(peek(in_)) != tokens_t::COLON {
                let msg = format!(
                    "Constant Variable {} is not typed. Please provide a type.\n",
                    var_name
                );
                error_msg(&msg);
            }
            consume(tokens_t::COLON, in_, ":");
            parse_space_chars(in_);
            type_str = parse_type(table, in_);
        }

        let mut variable = create_variable(&var_name, &type_str);
        if hash_table::search(table, &var_name).is_some() {
            variable.node_type = AstNodeType::Definition;
        }
        return variable;
    }

    AstNode {
        node_type: AstNodeType::Var,
        lambda_expr: None,
        application: None,
        variable: Some(Box::new(Variable {
            name: String::new(),
            type_: None,
        })),
    }
}

pub fn parse_import(table: &mut HashTable, in_: &mut File) {
    consume(tokens_t::WHITESPACE, in_, "a whitespace");

    consume(tokens_t::QUOTE, in_, "\"");

    let mut file_path = String::new();

    let mut next_token = next_char(in_);
    let mut n = parse_token(next_token);

    while n != tokens_t::QUOTE {
        if file_path.len() < 99 {
            file_path.push(next_token);
        } else {
            error_msg(
                "File path is too long. Please make sure it is less than 100 characters.",
            );
        }

        next_token = next_char(in_);
        n = parse_token(next_token);
    }

    if n != tokens_t::QUOTE {
        expect("a closing quote", next_token);
    }

    let mut imported_file = match File::open(&file_path) {
        Ok(f) => f,
        Err(_) => {
            error_msg(&format!("Could not open imported file {}\n", file_path));
        }
    };

    loop {
        let imported_tkn = peek(&mut imported_file);
        if imported_tkn == EOF_CHAR {
            break;
        }
        let scanned = parse_token(imported_tkn);
        parse_space_chars(&mut imported_file);
        if scanned == tokens_t::VARIABLE {
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
                error_msg(&msg);
            }
        }
    }
}

pub fn parse_definition(table: &mut HashTable, in_: &mut File) {
    consume(tokens_t::WHITESPACE, in_, "a whitespace");

    if parse_token(peek(in_)) != tokens_t::VARIABLE {
        expect("a variable", peek(in_));
    }

    let def_name = parse_variable(in_);

    consume(tokens_t::WHITESPACE, in_, "a whitespace");

    consume(tokens_t::EQ, in_, "=");

    consume(tokens_t::WHITESPACE, in_, "a whitespace");

    let definition = parse_expression(table, in_);
    hash_table::insert(table, &def_name, Some(definition));
}

pub fn is_uppercase(c: char) -> bool {
    c.is_ascii_uppercase()
}

pub fn parse_type_definition(types_table: &mut HashTable, in_: &mut File) {
    let mut next_token = next_char(in_);
    let mut n = parse_token(next_token);
    if n != tokens_t::WHITESPACE {
        expect(" ", next_token);
    }

    next_token = peek(in_);
    n = parse_token(next_token);
    if n != tokens_t::VARIABLE {
        expect("a type definition", next_token);
    }

    if !is_uppercase(next_token) {
        error_msg("Type names must start with an uppercase letter");
    }

    let type_name = parse_variable(in_);
    if hash_table::table_exists(types_table, &type_name) {
        let msg = format!("Type {} was already defined.\n", type_name);
        error_msg(&msg);
    }
    hash_table::insert(types_table, &type_name, None);
}

pub fn parse_type(types_table: &mut HashTable, in_: &mut File) -> String {
    let mut type_name = String::new();
    let token = next_char(in_);

    if !is_uppercase(token) {
        error_msg("Types should start with an uppercase letter.");
    }

    type_name.push(token);

    while is_variable(peek(in_)) {
        type_name.push(next_char(in_));
    }

    if !hash_table::table_exists(types_table, &type_name) {
        let msg = format!("Type {} was not defined.\n", type_name);
        error_msg(&msg);
    }
    type_name
}

pub fn parse_variable(in_: &mut File) -> String {
    let mut variable_name = String::new();

    while is_variable(peek(in_)) {
        variable_name.push(next_char(in_));
    }
    variable_name
}

pub fn expect(expected: &str, received: char) {
    println!("Syntax Error: Expected {} , received {} ", expected, received);
    std::process::exit(1);
}

pub fn free_ast(node: &mut AstNode) {
    let _ = node;
}
