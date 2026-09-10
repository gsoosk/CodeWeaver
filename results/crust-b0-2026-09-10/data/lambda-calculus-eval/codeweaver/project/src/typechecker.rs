use crate::{common, reducer};
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
            let type_ = get_type_from_expr(expr);
            create_type(&type_, "", expr)
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(application) = &expr.node {
                let func_type = application
                    .function
                    .as_ref()
                    .map(|f| typecheck(f, env))
                    .unwrap_or_else(|| create_type("", "", expr));
                let arg_type = application
                    .argument
                    .as_ref()
                    .map(|a| typecheck(a, env))
                    .unwrap_or_else(|| create_type("", "", expr));

                assert_(type_equal(&func_type, &arg_type), "Type mismatch.");
                // TODO (preserved from C source): should return the return_type
                // of func_type; for now assume functions are pure with simple types.
                func_type
            } else {
                create_type("", "", expr)
            }
        }
        common::AstNodeType::LAMBDA_EXPR => {
            let type_ = get_type_from_expr(expr);
            // TODO (preserved from C source): fix for function types.
            create_type(&type_, "", expr)
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
            if let common::AstNodeUnion::LambdaExpr(l) = &expr.node {
                l.type_.clone()
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
        expr: reducer::deepcopy(expr),
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
    // C compares raw pointer identity (`t->expr != expr`); since `Type` owns a
    // deep copy of its `expr` rather than a raw pointer, structural equality
    // via `ast_to_string` is the faithful adaptation for owned values.
    if common::ast_to_string(&t.expr) != common::ast_to_string(expr) {
        return false;
    }

    let type_ = get_type_from_expr(expr);
    if type_.is_empty() {
        panic!("ERROR: Null pointer encountered in expr_type_equal");
    }

    let parsed_type = parse_function_type(&type_);

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
    let mut cur = Some(env);
    while let Some(e) = cur {
        if expr_type_equal(&e.type_, expr) {
            return clone_type(&e.type_);
        }
        cur = e.next.as_deref();
    }
    panic!("ERROR: type not found in environment");
}

fn clone_type(t: &Type) -> Type {
    Type {
        expr: reducer::deepcopy(&t.expr),
        type_: t.type_.clone(),
        return_type: t.return_type.clone(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Fixture-based: small ASTs with matching/mismatched types; typecheck's
    // known non-arrow-codomain limitation on APPLICATION must NOT be "fixed".

    fn var(name: &str, type_: &str) -> common::AstNode {
        common::AstNode {
            type_: common::AstNodeType::VAR,
            node: common::AstNodeUnion::Variable(common::Variable {
                name: name.to_string(),
                type_: type_.to_string(),
            }),
        }
    }

    #[test]
    fn test_typecheck_var_returns_its_declared_type() {
        let expr = var("x", "Bool");
        let t = typecheck(&expr, None);
        assert_eq!(t.type_, "Bool");
        assert_eq!(t.return_type, "");
    }

    #[test]
    fn test_typecheck_lambda_expr_builds_arrow_like_type() {
        let body = var("x", "");
        let lambda = common::AstNode {
            type_: common::AstNodeType::LAMBDA_EXPR,
            node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
                parameter: "x".to_string(),
                type_: "Bool".to_string(),
                body: Some(Box::new(body)),
            }),
        };
        let t = typecheck(&lambda, None);
        assert_eq!(t.type_, "Bool");
    }

    #[test]
    fn test_type_equal_compares_by_type_name() {
        let expr = var("x", "Bool");
        let a = create_type("Bool", "", &expr);
        let b = create_type("Bool", "", &expr);
        assert!(type_equal(&a, &b));

        let c = create_type("Nat", "", &expr);
        assert!(!type_equal(&a, &c));
    }

    #[test]
    fn test_add_to_env_and_lookup_type_roundtrip() {
        let expr = var("x", "Bool");
        let t = create_type("Bool", "", &expr);
        let mut env: Option<Box<TypeEnv>> = None;
        add_to_env(&mut env, t);
        let env_ref = env.as_deref().expect("expected environment entry");
        let found = lookup_type(env_ref, &expr);
        assert_eq!(found.type_, "Bool");
    }
}