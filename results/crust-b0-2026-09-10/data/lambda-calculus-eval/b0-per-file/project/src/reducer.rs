use crate::{common, hash_table, parser, config};

pub const SIZE: usize = 122;

// Mirrors the C static global `reduction_order`.
static mut REDUCTION_ORDER: config::reduction_order_t = config::reduction_order_t::Applicative;

pub fn set_reduction_order(t: config::reduction_order_t) {
    unsafe {
        REDUCTION_ORDER = t;
    }
}

fn get_reduction_order() -> config::reduction_order_t {
    unsafe { REDUCTION_ORDER }
}

pub fn print_reduction_order(t: config::reduction_order_t) {
    match t {
        config::reduction_order_t::Applicative => print!("Applicative"),
        config::reduction_order_t::Normal => print!("Normal"),
    }
    println!();
}

pub fn reduce(table: &mut hash_table::HashTable, n: &common::AstNode) -> common::AstNode {
    common::print_verbose("Order of reduction is: ");
    print_reduction_order(get_reduction_order());
    common::print_verbose("-------------------------------------------\n");

    let mut n_copy = n.clone();
    expand_definitions(table, &mut n_copy);

    common::print_verbose("Expanded expression:\n");
    common::print_ast_verbose(&n_copy);

    let reduced = reduce_ast(table, &n_copy);

    common::print_verbose("Final reduced expression:\n");
    common::print_ast_verbose(&reduced);
    common::print_verbose("-------------------------------------------\n");

    reduced
}

pub fn expand_definitions(table: &mut hash_table::HashTable, n: &mut common::AstNode) {
    match n {
        common::AstNode::LambdaExpr(lambda_expr) => {
            expand_definitions(table, &mut lambda_expr.body);
        }
        common::AstNode::Application(application) => {
            expand_definitions(table, &mut application.function);
            expand_definitions(table, &mut application.argument);
        }
        common::AstNode::Definition(variable) => {
            let def_name = variable.name.clone();
            let expanded_def = table
                .search(&def_name)
                .expect("HANDLE_NULL: definition not found");
            common::print_verbose(&format!(
                "Expanding definition of: {} . Term expanded to:\n",
                def_name
            ));
            common::print_ast_verbose(&expanded_def);

            *n = expanded_def.clone();
        }
        _ => {}
    }
}

pub fn replace(n: &mut common::AstNode, old: &str, new_name: &str) {
    match n {
        common::AstNode::LambdaExpr(lambda_expr) => {
            if lambda_expr.parameter == old {
                lambda_expr.parameter = new_name.to_string();
            }
            replace(&mut lambda_expr.body, old, new_name);
        }
        common::AstNode::Application(application) => {
            replace(&mut application.function, old, new_name);
            replace(&mut application.argument, old, new_name);
        }
        common::AstNode::Var(variable) => {
            if variable.name == old {
                variable.name = new_name.to_string();
            }
        }
        _ => {}
    }
}

pub fn reduce_ast(table: &mut hash_table::HashTable, n: &common::AstNode) -> common::AstNode {
    match n {
        common::AstNode::LambdaExpr(lambda_expr) => {
            let mut lambda_expr = lambda_expr.clone();
            // recursively reduce the body
            // if order is applicative, reduce the body right now
            if get_reduction_order() == config::reduction_order_t::Applicative {
                lambda_expr.body = Box::new(reduce_ast(table, &lambda_expr.body));
            }
            common::AstNode::LambdaExpr(lambda_expr)
        }

        common::AstNode::Application(application) => {
            let mut application = application.clone();

            application.function = Box::new(reduce_ast(table, &application.function));

            if get_reduction_order() == config::reduction_order_t::Applicative {
                application.argument = Box::new(reduce_ast(table, &application.argument));
            }

            if let common::AstNode::LambdaExpr(lambda_expr) = application.function.as_ref() {
                let param = lambda_expr.parameter.clone();
                let reduced = substitute(&lambda_expr.body, &param, &application.argument);

                common::print_verbose(&format!(
                    "Applied substitution to lambda expr of parameter <{}> and resulted in:\n",
                    param
                ));
                common::print_ast_verbose(&reduced);

                if get_reduction_order() == config::reduction_order_t::Applicative {
                    return reduced;
                }
                return reduce_ast(table, &reduced);
            }

            common::AstNode::Application(application)
        }

        // base case leaf node or variable, nothing to reduce
        _ => n.clone(),
    }
}

pub fn substitute(
    expression: &common::AstNode,
    variable: &str,
    replacement: &common::AstNode,
) -> common::AstNode {
    match expression {
        common::AstNode::Var(var) => {
            if var.name == variable {
                deepcopy(replacement)
            } else {
                expression.clone()
            }
        }

        common::AstNode::LambdaExpr(lambda_expr) => {
            // ex: @x.(x y) -> if variable is equal to @x (x), we should then
            // replace all x in the body of expression with replacement
            let mut lambda_expr = lambda_expr.clone();
            lambda_expr.body = Box::new(substitute(&lambda_expr.body, variable, replacement));

            if lambda_expr.parameter != variable {
                // if @x.(x y) and we're substituting for y, for example, we
                // do not want to remove the lambda term
                common::AstNode::LambdaExpr(lambda_expr)
            } else {
                *lambda_expr.body
            }
        }

        common::AstNode::Application(application) => {
            let mut application = application.clone();
            application.function = Box::new(substitute(&application.function, variable, replacement));
            application.argument = Box::new(substitute(&application.argument, variable, replacement));
            common::AstNode::Application(application)
        }

        _ => expression.clone(),
    }
}

pub fn deepcopy(n: &common::AstNode) -> common::AstNode {
    match n {
        common::AstNode::Var(variable) => deepcopy_var(&variable.name, &variable.type_),

        common::AstNode::LambdaExpr(lambda_expr) => {
            deepcopy_lambda_expr(&lambda_expr.parameter, &lambda_expr.body, &lambda_expr.type_)
        }

        common::AstNode::Application(application) => {
            deepcopy_application(&application.function, &application.argument)
        }

        _ => n.clone(),
    }
}

pub fn deepcopy_application(function: &common::AstNode, argument: &common::AstNode) -> common::AstNode {
    common::AstNode::Application(common::Application {
        function: Box::new(deepcopy(function)),
        argument: Box::new(deepcopy(argument)),
    })
}

pub fn deepcopy_lambda_expr(parameter: &str, body: &common::AstNode, type_: &str) -> common::AstNode {
    common::AstNode::LambdaExpr(common::LambdaExpression {
        parameter: parameter.to_string(),
        type_: type_.to_string(),
        body: Box::new(deepcopy(body)),
    })
}

pub fn deepcopy_var(name: &str, type_: &str) -> common::AstNode {
    common::AstNode::Var(common::Variable {
        name: name.to_string(),
        type_: type_.to_string(),
    })
}
