use crate::common::{self, AstNode, LambdaExpression};
use crate::config::reduction_order_t;
use crate::hash_table::HashTable;

pub struct Reducer {
    pub order: reduction_order_t,
    pub verbose: bool,
}

impl Reducer {
    pub fn new(order: reduction_order_t, verbose: bool) -> Self {
        Reducer { order, verbose }
    }

    pub fn reduce(&self, node: &AstNode, defs: &HashTable) -> AstNode {
        if self.verbose {
            common::print_verbose("Reducing:");
            common::print_ast_verbose(node);
        }
        match self.order {
            reduction_order_t::NormalOrder => self.reduce_normal(node, defs),
            reduction_order_t::ApplicativeOrder => self.reduce_applicative(node, defs),
        }
    }

    fn reduce_normal(&self, node: &AstNode, defs: &HashTable) -> AstNode {
        if self.verbose {
            common::print_verbose("Normal order reduction");
            common::print_ast_verbose(node);
        }
        match node {
            AstNode::LambdaExpr(lambda) => AstNode::LambdaExpr(lambda.clone()),
            AstNode::Application(func, arg) => {
                let func_reduced = self.reduce_normal(func, defs);
                match func_reduced {
                    AstNode::LambdaExpr(lambda) => {
                        let substituted = self.substitute(&lambda.body, &lambda.param, arg);
                        self.reduce_normal(&substituted, defs)
                    }
                    _ => AstNode::Application(Box::new(func_reduced), arg.clone()),
                }
            }
            AstNode::Definition(name, expr) => {
                if self.verbose {
                    common::print_verbose("Definition:");
                    common::print_ast_verbose(expr);
                }
                AstNode::Definition(name.clone(), Box::new(self.reduce_normal(expr, defs)))
            }
            AstNode::Var(name) => {
                if self.verbose {
                    common::print_verbose("Var lookup:");
                }
                if let Some(val) = defs.get(name) {
                    val.clone()
                } else {
                    AstNode::Var(name.clone())
                }
            }
        }
    }

    fn reduce_applicative(&self, node: &AstNode, defs: &HashTable) -> AstNode {
        if self.verbose {
            common::print_verbose("Applicative order reduction");
            common::print_ast_verbose(node);
        }
        match node {
            AstNode::LambdaExpr(lambda) => AstNode::LambdaExpr(lambda.clone()),
            AstNode::Application(func, arg) => {
                let func_reduced = self.reduce_applicative(func, defs);
                let arg_reduced = self.reduce_applicative(arg, defs);
                match func_reduced {
                    AstNode::LambdaExpr(lambda) => {
                        let substituted =
                            self.substitute(&lambda.body, &lambda.param, &arg_reduced);
                        self.reduce_applicative(&substituted, defs)
                    }
                    _ => AstNode::Application(Box::new(func_reduced), Box::new(arg_reduced)),
                }
            }
            AstNode::Definition(name, expr) => {
                AstNode::Definition(name.clone(), Box::new(self.reduce_applicative(expr, defs)))
            }
            AstNode::Var(name) => {
                if let Some(val) = defs.get(name) {
                    val.clone()
                } else {
                    AstNode::Var(name.clone())
                }
            }
        }
    }

    fn substitute(&self, node: &AstNode, var: &str, value: &AstNode) -> AstNode {
        match node {
            AstNode::Var(name) => {
                if name == var {
                    value.clone()
                } else {
                    AstNode::Var(name.clone())
                }
            }
            AstNode::LambdaExpr(lambda) => {
                if lambda.param == var {
                    AstNode::LambdaExpr(lambda.clone())
                } else {
                    AstNode::LambdaExpr(LambdaExpression {
                        param: lambda.param.clone(),
                        body: Box::new(self.substitute(&lambda.body, var, value)),
                    })
                }
            }
            AstNode::Application(func, arg) => AstNode::Application(
                Box::new(self.substitute(func, var, value)),
                Box::new(self.substitute(arg, var, value)),
            ),
            AstNode::Definition(name, expr) => {
                AstNode::Definition(name.clone(), Box::new(self.substitute(expr, var, value)))
            }
        }
    }
}
