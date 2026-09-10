use crate::common::{self, AstNode};

pub fn typecheck(node: &AstNode) -> bool {
    match node {
        AstNode::Var(_) => true,
        AstNode::LambdaExpr(lambda) => typecheck(&lambda.body),
        AstNode::Application(func, arg) => {
            if !typecheck(func) {
                common::error("invalid function in application");
                return false;
            }
            if !typecheck(arg) {
                common::error("invalid argument in application");
                return false;
            }
            true
        }
        AstNode::Definition(_, expr) => typecheck(expr),
    }
}
