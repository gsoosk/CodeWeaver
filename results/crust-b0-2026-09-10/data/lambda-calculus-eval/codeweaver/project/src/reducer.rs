use crate::{common, hash_table, config};
use std::sync::atomic::{AtomicU8, Ordering};
pub const SIZE: usize = 122;

static REDUCTION_ORDER: AtomicU8 = AtomicU8::new(0); // 0 = APPLICATIVE, 1 = NORMAL

fn current_reduction_order() -> config::reduction_order_t {
    if REDUCTION_ORDER.load(Ordering::SeqCst) == 0 {
        config::reduction_order_t::APPLICATIVE
    } else {
        config::reduction_order_t::NORMAL
    }
}

pub fn set_reduction_order(t: config::reduction_order_t) {
    let v = match t {
        config::reduction_order_t::APPLICATIVE => 0,
        config::reduction_order_t::NORMAL => 1,
    };
    REDUCTION_ORDER.store(v, Ordering::SeqCst);
}

pub fn print_reduction_order(t: config::reduction_order_t) {
    match t {
        config::reduction_order_t::APPLICATIVE => print!("Applicative"),
        config::reduction_order_t::NORMAL => print!("Normal"),
    }
    println!();
}
pub fn reduce(table: &mut hash_table::HashTable, n: &common::AstNode) -> common::AstNode {
    common::print_verbose(
        "Order of reduction is: ",
        format_args!("Order of reduction is: "),
    );
    print_reduction_order(current_reduction_order());
    common::print_verbose(
        "-------------------------------------------\n",
        format_args!("-------------------------------------------\n"),
    );
    let mut expanded = deepcopy(n);
    expand_definitions(table, &mut expanded);
    common::print_verbose("Expanded expression:\n", format_args!("Expanded expression:\n"));
    common::print_ast_verbose(&expanded);
    let reduced = reduce_ast(table, &expanded);
    common::print_verbose(
        "Final reduced expression:\n",
        format_args!("Final reduced expression:\n"),
    );
    common::print_ast_verbose(&reduced);
    common::print_verbose(
        "-------------------------------------------\n",
        format_args!("-------------------------------------------\n"),
    );
    reduced
}
pub fn expand_definitions(table: &mut hash_table::HashTable, n: &mut common::AstNode) {
    match n.type_ {
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(lambda_expr) = &mut n.node {
                if let Some(body) = &mut lambda_expr.body {
                    expand_definitions(table, body);
                }
            }
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(application) = &mut n.node {
                if let Some(function) = &mut application.function {
                    expand_definitions(table, function);
                }
                if let Some(argument) = &mut application.argument {
                    expand_definitions(table, argument);
                }
            }
        }
        common::AstNodeType::DEFINITION => {
            let def_name = if let common::AstNodeUnion::Variable(variable) = &n.node {
                variable.name.clone()
            } else {
                String::new()
            };
            let expanded_def = table
                .search(&def_name)
                .unwrap_or_else(|| panic!("ERROR: Null pointer encountered: definition '{}' not found", def_name));
            let expanded_copy = deepcopy(expanded_def);
            common::print_verbose(
                "Expanding definition of:",
                format_args!("Expanding definition of: {} . Term expanded to:\n", def_name),
            );
            common::print_ast_verbose(&expanded_copy);
            n.type_ = expanded_copy.type_;
            n.node = expanded_copy.node;
        }
        common::AstNodeType::VAR => {}
    }
}
pub fn replace(n: &mut common::AstNode, old: &str, new_name: &str) {
    match n.type_ {
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(lambda_expr) = &mut n.node {
                if lambda_expr.parameter == old {
                    lambda_expr.parameter = new_name.to_string();
                }
                if let Some(body) = &mut lambda_expr.body {
                    replace(body, old, new_name);
                }
            }
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(application) = &mut n.node {
                if let Some(function) = &mut application.function {
                    replace(function, old, new_name);
                }
                if let Some(argument) = &mut application.argument {
                    replace(argument, old, new_name);
                }
            }
        }
        common::AstNodeType::VAR => {
            if let common::AstNodeUnion::Variable(variable) = &mut n.node {
                if variable.name == old {
                    variable.name = new_name.to_string();
                }
            }
        }
        common::AstNodeType::DEFINITION => {}
    }
}
pub fn reduce_ast(table: &mut hash_table::HashTable, n: &common::AstNode) -> common::AstNode {
    match n.type_ {
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(lambda_expr) = &n.node {
                let body = if current_reduction_order() == config::reduction_order_t::APPLICATIVE {
                    lambda_expr
                        .body
                        .as_ref()
                        .map(|b| reduce_ast(table, b))
                } else {
                    lambda_expr.body.as_ref().map(|b| deepcopy(b))
                };
                common::AstNode {
                    type_: common::AstNodeType::LAMBDA_EXPR,
                    node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
                        parameter: lambda_expr.parameter.clone(),
                        type_: lambda_expr.type_.clone(),
                        body: body.map(Box::new),
                    }),
                }
            } else {
                deepcopy(n)
            }
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(application) = &n.node {
                let function = application
                    .function
                    .as_ref()
                    .map(|f| reduce_ast(table, f))
                    .unwrap_or_default();
                let argument = if current_reduction_order() == config::reduction_order_t::APPLICATIVE
                {
                    application
                        .argument
                        .as_ref()
                        .map(|a| reduce_ast(table, a))
                        .unwrap_or_default()
                } else {
                    application
                        .argument
                        .as_ref()
                        .map(|a| deepcopy(a))
                        .unwrap_or_default()
                };

                if function.type_ == common::AstNodeType::LAMBDA_EXPR {
                    if let common::AstNodeUnion::LambdaExpr(lambda_expr) = &function.node {
                        let param = lambda_expr.parameter.clone();
                        let reduced = lambda_expr
                            .body
                            .as_ref()
                            .map(|b| substitute(b, &param, &argument))
                            .unwrap_or_default();
                        common::print_verbose(
                            "Applied substitution",
                            format_args!(
                                "Applied substitution to lambda expr of parameter <{}> and resulted in:\n",
                                param
                            ),
                        );
                        common::print_ast_verbose(&reduced);

                        if current_reduction_order() == config::reduction_order_t::APPLICATIVE {
                            return reduced;
                        }
                        return reduce_ast(table, &reduced);
                    }
                }

                common::AstNode {
                    type_: common::AstNodeType::APPLICATION,
                    node: common::AstNodeUnion::Application(common::Application {
                        function: Some(Box::new(function)),
                        argument: Some(Box::new(argument)),
                    }),
                }
            } else {
                deepcopy(n)
            }
        }
        _ => deepcopy(n),
    }
}
pub fn substitute(expression: &common::AstNode, variable: &str, replacement: &common::AstNode) -> common::AstNode {
    match expression.type_ {
        common::AstNodeType::VAR => {
            if let common::AstNodeUnion::Variable(v) = &expression.node {
                if v.name == variable {
                    return deepcopy(replacement);
                }
            }
            deepcopy(expression)
        }
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(lambda_expr) = &expression.node {
                let new_body = lambda_expr
                    .body
                    .as_ref()
                    .map(|b| substitute(b, variable, replacement))
                    .unwrap_or_default();
                if lambda_expr.parameter != variable {
                    return common::AstNode {
                        type_: common::AstNodeType::LAMBDA_EXPR,
                        node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
                            parameter: lambda_expr.parameter.clone(),
                            type_: lambda_expr.type_.clone(),
                            body: Some(Box::new(new_body)),
                        }),
                    };
                }
                return new_body;
            }
            deepcopy(expression)
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(application) = &expression.node {
                let new_function = application
                    .function
                    .as_ref()
                    .map(|f| substitute(f, variable, replacement))
                    .unwrap_or_default();
                let new_argument = application
                    .argument
                    .as_ref()
                    .map(|a| substitute(a, variable, replacement))
                    .unwrap_or_default();
                return common::AstNode {
                    type_: common::AstNodeType::APPLICATION,
                    node: common::AstNodeUnion::Application(common::Application {
                        function: Some(Box::new(new_function)),
                        argument: Some(Box::new(new_argument)),
                    }),
                };
            }
            deepcopy(expression)
        }
        common::AstNodeType::DEFINITION => deepcopy(expression),
    }
}
pub fn deepcopy(n: &common::AstNode) -> common::AstNode {
    match n.type_ {
        common::AstNodeType::VAR => {
            if let common::AstNodeUnion::Variable(v) = &n.node {
                deepcopy_var(&v.name, &v.type_)
            } else {
                common::AstNode::default()
            }
        }
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(lambda_expr) = &n.node {
                let body = lambda_expr
                    .body
                    .as_deref()
                    .map(deepcopy)
                    .unwrap_or_default();
                deepcopy_lambda_expr(&lambda_expr.parameter, &body, &lambda_expr.type_)
            } else {
                common::AstNode::default()
            }
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(application) = &n.node {
                let function = application
                    .function
                    .as_deref()
                    .map(deepcopy)
                    .unwrap_or_default();
                let argument = application
                    .argument
                    .as_deref()
                    .map(deepcopy)
                    .unwrap_or_default();
                deepcopy_application(&function, &argument)
            } else {
                common::AstNode::default()
            }
        }
        common::AstNodeType::DEFINITION => {
            if let common::AstNodeUnion::Variable(v) = &n.node {
                common::AstNode {
                    type_: common::AstNodeType::DEFINITION,
                    node: common::AstNodeUnion::Variable(common::Variable {
                        name: v.name.clone(),
                        type_: v.type_.clone(),
                    }),
                }
            } else {
                common::AstNode::default()
            }
        }
    }
}

pub fn deepcopy_application(function: &common::AstNode, argument: &common::AstNode) -> common::AstNode {
    common::AstNode {
        type_: common::AstNodeType::APPLICATION,
        node: common::AstNodeUnion::Application(common::Application {
            function: Some(Box::new(deepcopy(function))),
            argument: Some(Box::new(deepcopy(argument))),
        }),
    }
}
pub fn deepcopy_lambda_expr(parameter: &str, body: &common::AstNode, type_: &str) -> common::AstNode {
    common::AstNode {
        type_: common::AstNodeType::LAMBDA_EXPR,
        node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
            parameter: parameter.to_string(),
            type_: type_.to_string(),
            body: Some(Box::new(deepcopy(body))),
        }),
    }
}
pub fn deepcopy_var(name: &str, type_: &str) -> common::AstNode {
    common::AstNode {
        type_: common::AstNodeType::VAR,
        node: common::AstNodeUnion::Variable(common::Variable {
            name: name.to_string(),
            type_: type_.to_string(),
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    // Fixture-based: small in-memory ASTs, no file I/O; compared via
    // common::ast_to_string since AstNode has no PartialEq.

    // `reduction_order` is process-global state (mirroring C's `static
    // reduction_order_t`), so tests that flip it must not run concurrently
    // with each other under the default multi-threaded test harness.
    static ORDER_TEST_LOCK: Mutex<()> = Mutex::new(());

    fn var(name: &str, type_: &str) -> common::AstNode {
        common::AstNode {
            type_: common::AstNodeType::VAR,
            node: common::AstNodeUnion::Variable(common::Variable {
                name: name.to_string(),
                type_: type_.to_string(),
            }),
        }
    }

    fn lambda(param: &str, type_: &str, body: common::AstNode) -> common::AstNode {
        common::AstNode {
            type_: common::AstNodeType::LAMBDA_EXPR,
            node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
                parameter: param.to_string(),
                type_: type_.to_string(),
                body: Some(Box::new(body)),
            }),
        }
    }

    fn app(function: common::AstNode, argument: common::AstNode) -> common::AstNode {
        common::AstNode {
            type_: common::AstNodeType::APPLICATION,
            node: common::AstNodeUnion::Application(common::Application {
                function: Some(Box::new(function)),
                argument: Some(Box::new(argument)),
            }),
        }
    }

    #[test]
    fn test_reduce_ast_applicative_order() {
        let _guard = ORDER_TEST_LOCK.lock().unwrap();
        set_reduction_order(config::reduction_order_t::APPLICATIVE);
        // (@x:T.(x z)) (@y:T.y) -- applicative returns the reduced substitution
        // without recursing further, so a fresh redex is left unreduced.
        let expr = app(
            lambda("x", "T", app(var("x", ""), var("z", ""))),
            lambda("y", "T", var("y", "")),
        );
        let mut table = hash_table::HashTable::new();
        let result = reduce_ast(&mut table, &expr);
        assert_eq!(
            common::ast_to_string(&result),
            "((@y : T .(y) ) (z) ) "
        );
    }

    #[test]
    fn test_reduce_ast_normal_order() {
        let _guard = ORDER_TEST_LOCK.lock().unwrap();
        set_reduction_order(config::reduction_order_t::NORMAL);
        let expr = app(
            lambda("x", "T", app(var("x", ""), var("z", ""))),
            lambda("y", "T", var("y", "")),
        );
        let mut table = hash_table::HashTable::new();
        let result = reduce_ast(&mut table, &expr);
        assert_eq!(common::ast_to_string(&result), "(z) ");
        // restore default order for other tests
        set_reduction_order(config::reduction_order_t::APPLICATIVE);
    }

    #[test]
    fn test_substitute_replaces_free_variable() {
        let expr = var("x", "");
        let replacement = var("y", "Bool");
        let result = substitute(&expr, "x", &replacement);
        assert_eq!(common::ast_to_string(&result), "(y : Bool) ");
    }

    #[test]
    fn test_expand_definitions_replaces_definition_node() {
        let mut table = hash_table::HashTable::new();
        table.insert("foo", var("bar", "Nat"));
        let mut def_node = common::AstNode {
            type_: common::AstNodeType::DEFINITION,
            node: common::AstNodeUnion::Variable(common::Variable {
                name: "foo".to_string(),
                type_: String::new(),
            }),
        };
        expand_definitions(&mut table, &mut def_node);
        assert_eq!(common::ast_to_string(&def_node), "(bar : Nat) ");
    }

    #[test]
    fn test_deepcopy_produces_independent_tree() {
        let mut original = var("x", "Bool");
        let copy = deepcopy(&original);
        if let common::AstNodeUnion::Variable(v) = &mut original.node {
            v.name = "mutated".to_string();
        }
        assert_eq!(common::ast_to_string(&copy), "(x : Bool) ");
        assert_eq!(common::ast_to_string(&original), "(mutated : Bool) ");
    }
}