use crate::common::{Application, AstNode, AstNodeType, LambdaExpr, Variable};

pub struct Parser {
    tokens: Vec<String>,
    pos: usize,
}

impl Parser {
    pub fn new(tokens: Vec<String>) -> Self {
        Parser { tokens, pos: 0 }
    }

    fn peek(&self) -> Option<&String> {
        self.tokens.get(self.pos)
    }

    fn next(&mut self) -> Option<String> {
        let tok = self.tokens.get(self.pos).cloned();
        self.pos += 1;
        tok
    }

    pub fn parse_expr(&mut self) -> AstNode {
        if let Some(tok) = self.peek() {
            if tok == "\\" || tok == "λ" {
                self.next();
                let param = self.next().unwrap_or_default();
                if let Some(dot) = self.peek() {
                    if dot == "." {
                        self.next();
                    }
                }
                let body = self.parse_expr();
                return AstNode {
                    node_type: AstNodeType::LambdaExpr,
                    variable: None,
                    application: None,
                    lambda_expr: Some(LambdaExpr {
                        parameter: param,
                        body: Box::new(body),
                    }),
                };
            }
        }
        self.parse_application()
    }

    fn parse_application(&mut self) -> AstNode {
        let mut left = self.parse_atom();
        while let Some(tok) = self.peek() {
            if tok == ")" || tok == "." {
                break;
            }
            let right = self.parse_atom();
            left = AstNode {
                node_type: AstNodeType::Application,
                variable: None,
                application: Some(Application {
                    function: Box::new(left),
                    argument: Box::new(right),
                }),
                lambda_expr: None,
            };
        }
        left
    }

    fn parse_atom(&mut self) -> AstNode {
        if let Some(tok) = self.next() {
            if tok == "(" {
                let expr = self.parse_expr();
                if let Some(close) = self.peek() {
                    if close == ")" {
                        self.next();
                    }
                }
                return expr;
            }
            return AstNode {
                node_type: AstNodeType::Variable,
                variable: Some(Variable { name: tok }),
                application: None,
                lambda_expr: None,
            };
        }
        AstNode {
            node_type: AstNodeType::Variable,
            variable: Some(Variable {
                name: String::new(),
            }),
            application: None,
            lambda_expr: None,
        }
    }
}

pub fn ast_to_string(node: &AstNode) -> String {
    match node.node_type {
        AstNodeType::Variable => {
            if let Some(v) = &node.variable {
                v.name.clone()
            } else {
                String::new()
            }
        }
        AstNodeType::Application => {
            if let Some(app) = &node.application {
                format!(
                    "({} {})",
                    ast_to_string(&app.function),
                    ast_to_string(&app.argument)
                )
            } else {
                String::new()
            }
        }
        AstNodeType::LambdaExpr => {
            if let Some(l) = &node.lambda_expr {
                format!("(\\{}.{})", l.parameter, ast_to_string(&l.body))
            } else {
                String::new()
            }
        }
    }
}
