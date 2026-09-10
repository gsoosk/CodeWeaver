use crate::common;
use crate::common::{AstNode, AstNodeKind};

#[derive(Clone)]
pub struct Type {
    pub expr: AstNode,
    pub type_: String,
    pub return_type: Option<String>,
}

pub struct TypeEnv {
    pub type_: Type,
    pub next: Option<Box<TypeEnv>>,
}

pub fn assert_(expr: bool, error_msg: &str) {
    if expr {
        return;
    }
    common::error(error_msg);
}

pub fn typecheck(expr: &common::AstNode, env: Option<&TypeEnv>) -> Type {
    let mut local_env: Option<Box<TypeEnv>> = env.map(|e| {
        Box::new(TypeEnv {
            type_: e.type_.clone(),
            next: e.next.as_ref().map(|n| Box::new(TypeEnv {
                type_: n.type_.clone(),
                next: None,
            })),
        })
    });

    match expr.kind {
        AstNodeKind::Var => {
            let type_ = get_type_from_expr(expr);
            let t = create_type(&type_, "", expr);
            add_to_env(&mut local_env, t.clone());
            t
        }
        AstNodeKind::Application => {
            let application = expr
                .application
                .as_ref()
                .expect("application node missing application data");

            let func_type = typecheck(&application.function, local_env.as_deref());
            let arg_type = typecheck(&application.argument, local_env.as_deref());

            assert_(type_equal(&func_type, &arg_type), "Type mismatch.");
            // TODO: This should return the return_type of func_type, for now we assume
            // functions are always pure and return values with simple types
            func_type
        }
        AstNodeKind::LambdaExpr => {
            let type_ = get_type_from_expr(expr);
            // TODO: Fix me for function types
            let t = create_type(&type_, "", expr);
            add_to_env(&mut local_env, t.clone());
            t
        }
        _ => panic!("typecheck: unhandled AST node kind"),
    }
}

pub fn type_equal(a: &Type, b: &Type) -> bool {
    let type_eql = a.type_ == b.type_;

    let return_eql = match (&a.return_type, &b.return_type) {
        (None, None) => true,
        (None, Some(_)) | (Some(_), None) => false,
        (Some(a_ret), Some(b_ret)) => a_ret == b_ret,
    };

    type_eql && return_eql
}

pub fn get_type_from_expr(expr: &common::AstNode) -> String {
    match expr.kind {
        AstNodeKind::Var => expr
            .variable
            .as_ref()
            .map(|v| v.type_.clone())
            .unwrap_or_default(),
        AstNodeKind::LambdaExpr => expr
            .lambda_expr
            .as_ref()
            .map(|l| l.type_.clone())
            .unwrap_or_default(),
        _ => String::new(),
    }
}

pub fn p_print_type(t: &Type) {
    if t.type_.is_empty() && t.return_type.is_none() {
        println!("(type null)");
        return;
    }
    if !t.type_.is_empty() {
        println!("Type: {}", t.type_);
    }
    if let Some(ref rt) = t.return_type {
        println!("Return type: {}", rt);
    }
}

pub fn create_type(type_: &str, return_type: &str, expr: &common::AstNode) -> Type {
    Type {
        expr: expr.clone(),
        type_: type_.to_string(),
        return_type: if return_type.is_empty() {
            None
        } else {
            Some(return_type.to_string())
        },
    }
}

pub fn parse_function_type(type_: &str) -> Type {
    Type {
        expr: common::AstNode::default(),
        type_: type_.to_string(),
        return_type: None,
    }
}

pub fn expr_type_equal(t: &Type, expr: &common::AstNode) -> bool {
    if t.expr != *expr {
        return false;
    }

    let type_ = get_type_from_expr(expr);
    if type_.is_empty() {
        common::error("get_type_from_expr returned null");
    }

    let parsed_type = parse_function_type(&type_);

    if t.type_ != parsed_type.type_ {
        return false;
    }

    match (&parsed_type.return_type, &t.return_type) {
        (None, None) => true,
        (None, Some(_)) => false,
        (Some(_), None) => false,
        (Some(parsed_ret), Some(t_ret)) => parsed_ret == t_ret,
    }
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
    while let Some(node) = current {
        if expr_type_equal(&node.type_, expr) {
            return node.type_.clone();
        }
        current = node.next.as_deref();
    }
    panic!("lookup_type: type not found in environment");
}
