use crate::common;

pub struct Type {
pub expr: common::AstNode,
pub type_: String,
pub return_type: String,
}
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
    match expr.type_ {
        common::AstNodeType::VAR => {
            let type_str = get_type_from_expr(expr);
            let t = create_type(&type_str, "", expr);
            let _ = env;
            t
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(app) = &expr.node {
                let func_type = if let Some(f) = &app.function {
                    typecheck(f, env)
                } else {
                    create_type("", "", expr)
                };
                let arg_type = if let Some(a) = &app.argument {
                    typecheck(a, env)
                } else {
                    create_type("", "", expr)
                };
                assert_(type_equal(&func_type, &arg_type), "Type mismatch.");
                func_type
            } else {
                create_type("", "", expr)
            }
        }
        common::AstNodeType::LAMBDA_EXPR => {
            let type_str = get_type_from_expr(expr);
            let t = create_type(&type_str, "", expr);
            let _ = env;
            t
        }
        _ => create_type("", "", expr),
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
    match &expr.node {
        common::AstNodeUnion::Variable(v) if expr.type_ == common::AstNodeType::VAR => v.type_.clone(),
        common::AstNodeUnion::LambdaExpr(le) if expr.type_ == common::AstNodeType::LAMBDA_EXPR => le.type_.clone(),
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
        expr: expr.clone(),
        type_: type_.to_string(),
        return_type: return_type.to_string(),
    }
}

pub fn parse_function_type(type_: &str) -> Type {
    Type {
        expr: common::AstNode::default(),
        type_: type_.to_string(),
        return_type: String::new(),
    }
}

pub fn expr_type_equal(t: &Type, expr: &common::AstNode) -> bool {
    if &t.expr != expr {
        return false;
    }

    let type_str = get_type_from_expr(expr);
    if type_str.is_empty() {
        common::error("HANDLE_NULL: type is null", file!(), line!() as i32, "expr_type_equal");
    }

    let parsed_type = parse_function_type(&type_str);

    if t.type_ != parsed_type.type_ {
        return false;
    }

    if parsed_type.return_type.is_empty() {
        return t.return_type.is_empty();
    }

    if t.return_type != parsed_type.return_type {
        return false;
    }

    true
}

pub fn add_to_env(env: &mut Option<Box<TypeEnv>>, type_: Type) {
    let new_env = Box::new(TypeEnv {
        type_,
        next: env.take(),
    });
    *env = Some(new_env);
}

pub fn lookup_type(env: &TypeEnv, expr: &common::AstNode) -> Type {
    let mut current: Option<&TypeEnv> = Some(env);
    while let Some(e) = current {
        if expr_type_equal(&e.type_, expr) {
            return Type {
                expr: e.type_.expr.clone(),
                type_: e.type_.type_.clone(),
                return_type: e.type_.return_type.clone(),
            };
        }
        current = e.next.as_deref();
    }
    Type {
        expr: common::AstNode::default(),
        type_: String::new(),
        return_type: String::new(),
    }
}
