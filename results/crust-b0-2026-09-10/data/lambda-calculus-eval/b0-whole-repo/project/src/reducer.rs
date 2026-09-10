use crate::{common, hash_table, parser, config};
use std::sync::atomic::{AtomicBool, Ordering};

pub const SIZE: usize = 122;

static REDUCTION_ORDER_APPLICATIVE: AtomicBool = AtomicBool::new(true);

pub fn set_reduction_order(t: config::reduction_order_t) {
    let is_app = matches!(t, config::reduction_order_t::APPLICATIVE);
    REDUCTION_ORDER_APPLICATIVE.store(is_app, Ordering::SeqCst);
}

fn get_reduction_order() -> config::reduction_order_t {
    if REDUCTION_ORDER_APPLICATIVE.load(Ordering::SeqCst) {
        config::reduction_order_t::APPLICATIVE
    } else {
        config::reduction_order_t::NORMAL
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
    common::print_verbose("-------------------------------------------\n", format_args!(""));

    let mut n_owned = n.clone();
    expand_definitions(table, &mut n_owned);
    common::print_verbose("Expanded expression:\n", format_args!(""));
    common::print_ast_verbose(&n_owned);

    let reduced = reduce_ast(table, &n_owned);
    common::print_verbose("Final reduced expression:\n", format_args!(""));
    common::print_ast_verbose(&reduced);
    common::print_verbose("-------------------------------------------\n", format_args!(""));
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
            let def_name = if let common::AstNodeUnion::Variable(v) = &n.node {
                v.name.clone()
            } else {
                String::new()
            };
            let expanded = table.search(&def_name).cloned();
            match expanded {
                Some(expanded_def) => {
                    let msg = format!("Expanding definition of: {} . Term expanded to:\n", def_name);
                    common::print_verbose(&msg, format_args!(""));
                    common::print_ast_verbose(&expanded_def);
                    *n = expanded_def;
                }
                None => {
                    common::error("HANDLE_NULL: expanded_def is null", file!(), line!() as i32, "expand_definitions");
                }
            }
        }
        common::AstNodeType::VAR => {}
    }
}

pub fn replace(n: &mut common::AstNode, old: &str, new_name: &str) {
    let is_var = n.type_ == common::AstNodeType::VAR;
    match &mut n.node {
        common::AstNodeUnion::LambdaExpr(le) => {
            if le.parameter == old {
                le.parameter = new_name.to_string();
            }
            if let Some(body) = &mut le.body {
                replace(body, old, new_name);
            }
        }
        common::AstNodeUnion::Application(app) => {
            if let Some(f) = &mut app.function {
                replace(f, old, new_name);
            }
            if let Some(a) = &mut app.argument {
                replace(a, old, new_name);
            }
        }
        common::AstNodeUnion::Variable(v) => {
            if is_var && v.name == old {
                v.name = new_name.to_string();
            }
        }
    }
}

pub fn reduce_ast(table: &mut hash_table::HashTable, n: &common::AstNode) -> common::AstNode {
    match n.type_ {
        common::AstNodeType::LAMBDA_EXPR => {
            if let common::AstNodeUnion::LambdaExpr(le) = &n.node {
                let mut new_body = le.body.clone();
                if matches!(get_reduction_order(), config::reduction_order_t::APPLICATIVE) {
                    if let Some(body) = &le.body {
                        new_body = Some(Box::new(reduce_ast(table, body)));
                    }
                }
                common::AstNode {
                    type_: common::AstNodeType::LAMBDA_EXPR,
                    node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
                        parameter: le.parameter.clone(),
                        type_: le.type_.clone(),
                        body: new_body,
                    }),
                }
            } else {
                n.clone()
            }
        }
        common::AstNodeType::APPLICATION => {
            if let common::AstNodeUnion::Application(app) = &n.node {
                let function_reduced = if let Some(f) = &app.function {
                    reduce_ast(table, f)
                } else {
                    common::AstNode::default()
                };

                let argument_reduced = if matches!(get_reduction_order(), config::reduction_order_t::APPLICATIVE) {
                    if let Some(a) = &app.argument {
                        reduce_ast(table, a)
                    } else {
                        common::AstNode::default()
                    }
                } else {
                    if let Some(a) = &app.argument {
                        (**a).clone()
                    } else {
                        common::AstNode::default()
                    }
                };

                if function_reduced.type_ == common::AstNodeType::LAMBDA_EXPR {
                    if let common::AstNodeUnion::LambdaExpr(le) = &function_reduced.node {
                        let param = le.parameter.clone();
                        if let Some(body_ref) = &le.body {
                            let reduced = substitute(body_ref, &param, &argument_reduced);
                            let msg = format!(
                                "Applied substitution to lambda expr of parameter <{}> and resulted in:\n",
                                param
                            );
                            common::print_verbose(&msg, format_args!(""));
                            common::print_ast_verbose(&reduced);

                            if matches!(get_reduction_order(), config::reduction_order_t::APPLICATIVE) {
                                return reduced;
                            }
                            return reduce_ast(table, &reduced);
                        }
                    }
                }

                common::AstNode {
                    type_: common::AstNodeType::APPLICATION,
                    node: common::AstNodeUnion::Application(common::Application {
                        function: Some(Box::new(function_reduced)),
                        argument: Some(Box::new(argument_reduced)),
                    }),
                }
            } else {
                n.clone()
            }
        }
        _ => n.clone(),
    }
}

pub fn substitute(expression: &common::AstNode, variable: &str, replacement: &common::AstNode) -> common::AstNode {
    match &expression.node {
        common::AstNodeUnion::Variable(v) if expression.type_ == common::AstNodeType::VAR => {
            if v.name == variable {
                deepcopy(replacement)
            } else {
                expression.clone()
            }
        }
        common::AstNodeUnion::LambdaExpr(le) => {
            let new_body = if let Some(body) = &le.body {
                substitute(body, variable, replacement)
            } else {
                common::AstNode::default()
            };
            if le.parameter != variable {
                common::AstNode {
                    type_: common::AstNodeType::LAMBDA_EXPR,
                    node: common::AstNodeUnion::LambdaExpr(common::LambdaExpression {
                        parameter: le.parameter.clone(),
                        type_: le.type_.clone(),
                        body: Some(Box::new(new_body)),
                    }),
                }
            } else {
                new_body
            }
        }
        common::AstNodeUnion::Application(app) => {
            let new_func = if let Some(f) = &app.function {
                substitute(f, variable, replacement)
            } else {
                common::AstNode::default()
            };
            let new_arg = if let Some(a) = &app.argument {
                substitute(a, variable, replacement)
            } else {
                common::AstNode::default()
            };
            common::AstNode {
                type_: common::AstNodeType::APPLICATION,
                node: common::AstNodeUnion::Application(common::Application {
                    function: Some(Box::new(new_func)),
                    argument: Some(Box::new(new_arg)),
                }),
            }
        }
        _ => expression.clone(),
    }
}

pub fn deepcopy(n: &common::AstNode) -> common::AstNode {
    n.clone()
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
