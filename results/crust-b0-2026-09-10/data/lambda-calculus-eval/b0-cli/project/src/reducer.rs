use crate::{common, config, hash_table};
use std::sync::atomic::{AtomicBool, Ordering};

pub const SIZE: usize = 122;

static REDUCTION_ORDER_IS_NORMAL: AtomicBool = AtomicBool::new(false);

pub fn set_reduction_order(t: config::reduction_order_t) {
    REDUCTION_ORDER_IS_NORMAL.store(
        matches!(t, config::reduction_order_t::NORMAL),
        Ordering::SeqCst,
    );
}

fn get_reduction_order() -> config::reduction_order_t {
    if REDUCTION_ORDER_IS_NORMAL.load(Ordering::SeqCst) {
        config::reduction_order_t::NORMAL
    } else {
        config::reduction_order_t::APPLICATIVE
    }
}

pub fn print_reduction_order(t: config::reduction_order_t) {
    match t {
        config::reduction_order_t::APPLICATIVE => print!("Applicative"),
        config::reduction_order_t::NORMAL => print!("Normal"),
    }
    println!();
}

pub fn reduce(table: &mut hash_table::HashTable, n: &common::AstNode) -> common::AstNode {
    common::print_verbose("Order of reduction is: ", format_args!(""));
    print_reduction_order(get_reduction_order());
    common::print_verbose(
        "-------------------------------------------\n",
        format_args!(""),
    );

    let mut n_clone = n.clone();
    expand_definitions(table, &mut n_clone);
    common::print_verbose("Expanded expression:\n", format_args!(""));
    common::print_ast_verbose(&n_clone);

    let reduced = reduce_ast(table, &n_clone);
    common::print_verbose("Final reduced expression:\n", format_args!(""));
    common::print_ast_verbose(&reduced);
    common::print_verbose(
        "-------------------------------------------\n",
        format_args!(""),
    );
    reduced
}

pub fn expand_definitions(table: &mut hash_table::HashTable, n: &mut common::AstNode) {
    match n.type_ {
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(le) = &mut n.node {
                if let Some(body) = &mut le.body {
                    expand_definitions(table, body);
                }
            }
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(app) = &mut n.node {
                if let Some(f) = &mut app.function {
                    expand_definitions(table, f);
                }
                if let Some(a) = &mut app.argument {
                    expand_definitions(table, a);
                }
            }
        }
        common::AstNodeType::DEFINITION => {
            let def_name = match &n.node {
                common::AstNodeUnion::Variable(v) => v.name.clone(),
                _ => String::new(),
            };
            let expanded_def = table.search(&def_name).cloned();
            match expanded_def {
                Some(expanded) => {
                    common::print_verbose(
                        &format!(
                            "Expanding definition of: {} . Term expanded to:\n",
                            def_name
                        ),
                        format_args!(""),
                    );
                    common::print_ast_verbose(&expanded);
                    *n = expanded;
                }
                None => {
                    common::error(
                        &format!("Null pointer encountered expanding {}", def_name),
                        file!(),
                        line!() as i32,
                        "expand_definitions",
                    );
                }
            }
        }
        common::AstNodeType::VAR => {}
    }
}

pub fn replace(n: &mut common::AstNode, old: &str, new_name: &str) {
    match n.type_ {
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(le) = &mut n.node {
                if le.parameter == old {
                    le.parameter = new_name.to_string();
                }
                if let Some(body) = &mut le.body {
                    replace(body, old, new_name);
                }
            }
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(app) = &mut n.node {
                if let Some(f) = &mut app.function {
                    replace(f, old, new_name);
                }
                if let Some(a) = &mut app.argument {
                    replace(a, old, new_name);
                }
            }
        }
        common::AstNodeType::VAR => {
            if let common::AstNodeUnion::Variable(v) = &mut n.node {
                if v.name == old {
                    v.name = new_name.to_string();
                }
            }
        }
        common::AstNodeType::DEFINITION => {}
    }
}

pub fn reduce_ast(table: &mut hash_table::HashTable, n: &common::AstNode) -> common::AstNode {
    match n.type_ {
        common::AstNodeType::LAMBDA_EXPR => {
            let le = match &n.node {
                common::AstNodeUnion::LambdaExpr(le) => le,
                _ => return n.clone(),
            };
            let body = match &le.body {
                Some(b) => b,
                None => {
                    return common::AstNode {
                        type_: common::AstNodeType::LAMBDA_EXPR,
                        node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
                            parameter: le.parameter.clone(),
                            type_: le.type_.clone(),
                            body: None,
                        }),
                    }
                }
            };
            let new_body = if get_reduction_order() == config::reduction_order_t::APPLICATIVE {
                reduce_ast(table, body)
            } else {
                (**body).clone()
            };
            common::AstNode {
                type_: common::AstNodeType::LAMBDA_EXPR,
                node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
                    parameter: le.parameter.clone(),
                    type_: le.type_.clone(),
                    body: Some(Box::new(new_body)),
                }),
            }
        }
        common::AstNodeType::APPLICATION => {
            let app = match &n.node {
                common::AstNodeUnion::Application(app) => app,
                _ => return n.clone(),
            };
            let function = app.function.as_ref().unwrap();
            let argument = app.argument.as_ref().unwrap();

            let function_reduced = reduce_ast(table, function);
            let argument_reduced = if get_reduction_order() == config::reduction_order_t::APPLICATIVE
            {
                reduce_ast(table, argument)
            } else {
                (**argument).clone()
            };

            if function_reduced.type_ == common::AstNodeType::LAMBDA_EXPR {
                if let common::AstNodeUnion::LambdaExpr(le) = &function_reduced.node {
                    let param = le.parameter.clone();
                    let body = le.body.as_ref().unwrap();
                    let reduced = substitute(body, &param, &argument_reduced);
                    common::print_verbose(
                        &format!(
                            "Applied substitution to lambda expr of parameter <{}> and resulted in:\n",
                            param
                        ),
                        format_args!(""),
                    );
                    common::print_ast_verbose(&reduced);

                    if get_reduction_order() == config::reduction_order_t::APPLICATIVE {
                        return reduced;
                    }
                    return reduce_ast(table, &reduced);
                }
            }

            common::AstNode {
                type_: common::AstNodeType::APPLICATION,
                node: common::AstNodeUnion::Application(common::Application {
                    function: Some(Box::new(function_reduced)),
                    argument: Some(Box::new(argument_reduced)),
                }),
            }
        }
        _ => n.clone(),
    }
}

pub fn substitute(
    expression: &common::AstNode,
    variable: &str,
    replacement: &common::AstNode,
) -> common::AstNode {
    match expression.type_ {
        common::AstNodeType::VAR => {
            if let common::AstNodeUnion::Variable(v) = &expression.node {
                if v.name == variable {
                    return deepcopy(replacement);
                }
            }
            expression.clone()
        }
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(le) = &expression.node {
                let new_body = match &le.body {
                    Some(b) => substitute(b, variable, replacement),
                    None => common::AstNode::default(),
                };
                if le.parameter != variable {
                    return common::AstNode {
                        type_: common::AstNodeType::LAMBDA_EXPR,
                        node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
                            parameter: le.parameter.clone(),
                            type_: le.type_.clone(),
                            body: Some(Box::new(new_body)),
                        }),
                    };
                }
                return new_body;
            }
            expression.clone()
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(app) = &expression.node {
                let new_func = match &app.function {
                    Some(f) => substitute(f, variable, replacement),
                    None => common::AstNode::default(),
                };
                let new_arg = match &app.argument {
                    Some(a) => substitute(a, variable, replacement),
                    None => common::AstNode::default(),
                };
                return common::AstNode {
                    type_: common::AstNodeType::APPLICATION,
                    node: common::AstNodeUnion::Application(common::Application {
                        function: Some(Box::new(new_func)),
                        argument: Some(Box::new(new_arg)),
                    }),
                };
            }
            expression.clone()
        }
        common::AstNodeType::DEFINITION => expression.clone(),
    }
}

pub fn deepcopy(n: &common::AstNode) -> common::AstNode {
    match n.type_ {
        common::AstNodeType::VAR => {
            if let common::AstNodeUnion::Variable(v) = &n.node {
                deepcopy_var(&v.name, &v.type_)
            } else {
                n.clone()
            }
        }
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(le) = &n.node {
                match &le.body {
                    Some(body) => deepcopy_lambda_expr(&le.parameter, body, &le.type_),
                    None => n.clone(),
                }
            } else {
                n.clone()
            }
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(app) = &n.node {
                match (&app.function, &app.argument) {
                    (Some(f), Some(a)) => deepcopy_application(f, a),
                    _ => n.clone(),
                }
            } else {
                n.clone()
            }
        }
        common::AstNodeType::DEFINITION => n.clone(),
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
