#[derive(Debug, Clone, PartialEq)]
pub enum AstNodeType {
    Variable,
    Application,
    LambdaExpr,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Variable {
    pub name: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Application {
    pub function: Box<AstNode>,
    pub argument: Box<AstNode>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct LambdaExpr {
    pub parameter: String,
    pub body: Box<AstNode>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct AstNode {
    pub node_type: AstNodeType,
    pub variable: Option<Variable>,
    pub application: Option<Application>,
    pub lambda_expr: Option<LambdaExpr>,
}
