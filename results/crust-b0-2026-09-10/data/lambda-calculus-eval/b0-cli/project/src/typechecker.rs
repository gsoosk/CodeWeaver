use crate::common;

#[derive(Clone)]
pub struct Type {
    pub expr: common::AstNode,
    pub type_: String,
    pub return_type: String,
}

#[derive(Clone)]
pub struct TypeEnv {
    pub type_: Type,
    pub next: Option<Box<TypeEnv>>,
}

pub fn assert_(expr: bool, error_msg: &str) {
    if expr {
        return;
    }
    common::error(error_msg, file!(), line!() as i32, "assert_");
}

pub fn typecheck(expr: &common::AstNode, env: Option<&TypeEnv>) -> Type {
    // NOTE: in the original C, `env` is passed by value and `add_to_env`
    // only ever mutates the *local copy* of that pointer, so the extension
    // never propagates back to the caller. We mirror that (functionally
    // inert) behaviour with a throwaway local environment.
    let _ = env;
    match expr.type_ {
        common::AstNodeType::VAR => {
            let type_ = get_type_from_expr(expr);
            let t = create_type(&type_, "", expr);
            let mut local_env: Option<Box<TypeEnv>> = None;
            add_to_env(&mut local_env, t.clone());
            t
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(app) = &expr.node {
                let func_type = match &app.function {
                    Some(f) => typecheck(f, env),
                    None => create_type("", "", expr),
                };
                let arg_type = match &app.argument {
                    Some(a) => typecheck(a, env),
                    None => create_type("", "", expr),
                };
                assert_(type_equal(&func_type, &arg_type), "Type mismatch.");
                func_type
            } else {
                create_type("", "", expr)
            }
        }
        common::AstNodeType::LAMBDA_EXPR => {
            let type_ = get_type_from_expr(expr);
            let t = create_type(&type_, "", expr);
            let mut local_env: Option<Box<TypeEnv>> = None;
            add_to_env(&mut local_env, t.clone());
            t
        }
        common::AstNodeType::DEFINITION => create_type("", "", expr),
    }
}

pub fn type_equal(a: &Type, b: &Type) -> bool {
    let type_eql = a.type_ == b.type_;

    let return_eql = if a.return_type.is_empty() && b.return_type.is_empty() {
        true
    } else if a.return_type.is_empty() || b.return_type.is_empty() {
        false
    } else {
        a.return_type == b.return_type
    };

    type_eql && return_eql
}

pub fn get_type_from_expr(expr: &common::AstNode) -> String {
    match expr.type_ {
        common::AstNodeType::VAR => {
            if let common::AstNodeUnion::Variable(v) = &expr.node {
                v.type_.clone()
            } else {
                String::new()
            }
        }
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(le) = &expr.node {
                le.type_.clone()
            } else {
                String::new()
            }
        }
        _ => String::new(),
    }
}

pub fn p_print_type(t: &Type) {
    if !t.type_.is_empty() {
        println!("Type: {}", t.type_);
    }
    if !t.return_type.is_empty() {
        println!("Return type: {}", t.return_type);
    }
}

pub fn create_type(type_: &str, return_type: &str, expr: &common::AstNode) -> Type {
    Type {
        return_type: return_type.to_string(),
        type_: type_.to_string(),
        expr: expr.clone(),
    }
}

pub fn parse_function_type(type_: &str) -> Type {
    Type {
        return_type: String::new(),
        type_: type_.to_string(),
        expr: common::AstNode::default(),
    }
}

pub fn expr_type_equal(t: &Type, expr: &common::AstNode) -> bool {
    if common::ast_to_string(&t.expr) != common::ast_to_string(expr) {
        return false;
    }

    let type_ = get_type_from_expr(expr);
    if type_.is_empty() {
        common::error(
            "Null pointer encountered",
            file!(),
            line!() as i32,
            "expr_type_equal",
        );
    }

    let parsed_type = parse_function_type(&type_);

    if t.type_ != parsed_type.type_ {
        return false;
    }

    if parsed_type.return_type.is_empty() {
        return t.return_type.is_empty();
    }

    t.return_type == parsed_type.return_type
}

pub fn add_to_env(env: &mut Option<Box<TypeEnv>>, type_: Type) {
    let new_env = Box::new(TypeEnv {
        type_,
        next: env.take(),
    });
    *env = Some(new_env);
}

pub fn lookup_type(env: &TypeEnv, expr: &common::AstNode) -> Type {
    let mut cur: Option<&TypeEnv> = Some(env);
    while let Some(e) = cur {
        if expr_type_equal(&e.type_, expr) {
            return create_type(&e.type_.type_, &e.type_.return_type, expr);
        }
        cur = e.next.as_deref();
    }
    create_type("", "", expr)
}
