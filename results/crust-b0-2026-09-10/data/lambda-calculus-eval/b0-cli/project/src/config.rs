use std::fs::File;
use std::io::{self, BufRead};
use std::path::Path;
pub const CONFIG_PATH: &str = "config";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum reduction_order_t {
    APPLICATIVE,
    NORMAL,
}

#[derive(Debug, PartialEq, Eq)]
pub enum option_type_t {
    FILENAME,
    STEP_REDUCTION,
    REDUCTION_ORDER,
    CONFIG_ERROR,
}

pub struct Options {
    pub file: File,
    pub step_by_step_reduction: bool,
    pub reduction_order: reduction_order_t,
}

pub fn trim(str: &mut String) {
    let trimmed = str.trim().to_string();
    *str = trimmed;
}

pub fn get_config_type(key: &str) -> option_type_t {
    if key == "file" {
        option_type_t::FILENAME
    } else if key == "step_by_step_reduction" {
        option_type_t::STEP_REDUCTION
    } else if key == "reduction_order" {
        option_type_t::REDUCTION_ORDER
    } else {
        crate::common::error(
            &format!("ERROR: Invalid key '{}' at config file.", key),
            file!(),
            line!() as i32,
            "get_config_type",
        );
        option_type_t::CONFIG_ERROR
    }
}

pub fn parse_config(line: &str, key: &mut String, value: &mut String) {
    if !line.contains('=') {
        crate::common::error(
            &format!(
                "Malformed config file at line: {} . Expected = sign.\n",
                line
            ),
            file!(),
            line!() as i32,
            "parse_config",
        );
    }
    let mut parts = line.splitn(2, '=');
    *key = parts.next().unwrap_or("").to_string();
    *value = parts.next().unwrap_or("").to_string();
    trim(key);
    trim(value);
}

pub fn get_config_from_file() -> Options {
    let config_file = match File::open(Path::new(CONFIG_PATH)) {
        Ok(f) => f,
        Err(_) => {
            crate::common::error(
                "ERROR: Could not open config file",
                file!(),
                line!() as i32,
                "get_config_from_file",
            );
            unreachable!()
        }
    };
    let reader = io::BufReader::new(config_file);

    let mut file_opt: Option<File> = None;
    let mut step_by_step_reduction = false;
    let mut reduction_order_val = reduction_order_t::APPLICATIVE;

    for line_result in reader.lines() {
        let line = match line_result {
            Ok(l) => l,
            Err(_) => break,
        };
        if line.trim().is_empty() {
            continue;
        }
        let mut key = String::new();
        let mut value = String::new();
        parse_config(&line, &mut key, &mut value);
        let cfg = get_config_type(&key);

        match cfg {
            option_type_t::FILENAME => {
                file_opt = Some(match File::open(&value) {
                    Ok(f) => f,
                    Err(_) => {
                        crate::common::error(
                            &format!("ERROR: Could not open file {}\n", value),
                            file!(),
                            line!() as i32,
                            "get_config_from_file",
                        );
                        unreachable!()
                    }
                });
            }
            option_type_t::STEP_REDUCTION => {
                step_by_step_reduction = value == "true";
            }
            option_type_t::REDUCTION_ORDER => {
                if value == "applicative" {
                    reduction_order_val = reduction_order_t::APPLICATIVE;
                } else if value == "normal" {
                    reduction_order_val = reduction_order_t::NORMAL;
                } else {
                    crate::common::error(
                        "ERROR: reduction order in cfg file should be 'normal' or 'applicative'.",
                        file!(),
                        line!() as i32,
                        "get_config_from_file",
                    );
                }
            }
            option_type_t::CONFIG_ERROR => {
                crate::common::error(
                    &format!("Unrecognized key: {}", key),
                    file!(),
                    line!() as i32,
                    "get_config_from_file",
                );
            }
        }
    }

    let file = match file_opt {
        Some(f) => f,
        None => {
            crate::common::error(
                "ERROR: File cannot be null in cfg file.\n",
                file!(),
                line!() as i32,
                "get_config_from_file",
            );
            unreachable!()
        }
    };

    Options {
        file,
        step_by_step_reduction,
        reduction_order: reduction_order_val,
    }
}
