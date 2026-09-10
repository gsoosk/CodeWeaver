use std::fs::File;
use std::io::{self, BufRead};
use std::path::Path;
pub const CONFIG_PATH: &str = "config";
#[derive(Debug)]
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
    match key {
        "file" => option_type_t::FILENAME,
        "step_by_step_reduction" => option_type_t::STEP_REDUCTION,
        "reduction_order" => option_type_t::REDUCTION_ORDER,
        _ => {
            let msg = format!("ERROR: Invalid key '{}' at config file.", key);
            crate::common::error(&msg, file!(), line!() as i32, "get_config_type");
        }
    }
}
pub fn parse_config(line: &str, key: &mut String, value: &mut String) {
    if !line.contains('=') {
        let msg = format!("Malformed config file at line: {} . Expected = sign.\n", line);
        crate::common::error(&msg, file!(), line!() as i32, "parse_config");
    }
    let mut parts = line.splitn(2, '=');
    let k = parts.next().unwrap_or("").to_string();
    let v = parts.next().unwrap_or("").to_string();
    *key = k;
    *value = v;
    trim(key);
    trim(value);
}
pub fn get_config_from_file() -> Options {
    let file = File::open(CONFIG_PATH).unwrap_or_else(|_| {
        crate::common::error(
            &format!("ERROR: Could not open file {}\n", CONFIG_PATH),
            file!(),
            line!() as i32,
            "get_config_from_file",
        );
    });
    let reader = io::BufReader::new(file);

    let mut opt_file: Option<File> = None;
    let mut step = false;
    let mut order = reduction_order_t::APPLICATIVE;

    for line_res in reader.lines() {
        let line = match line_res {
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
                opt_file = Some(File::open(&value).unwrap_or_else(|_| {
                    crate::common::error(
                        &format!("ERROR: Could not open file {}\n", value),
                        file!(),
                        line!() as i32,
                        "get_config_from_file",
                    );
                }));
            }
            option_type_t::STEP_REDUCTION => {
                step = value == "true";
            }
            option_type_t::REDUCTION_ORDER => {
                if value == "applicative" {
                    order = reduction_order_t::APPLICATIVE;
                } else if value == "normal" {
                    order = reduction_order_t::NORMAL;
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
    if opt_file.is_none() {
        crate::common::error(
            "ERROR: File cannot be null in cfg file.\n",
            file!(),
            line!() as i32,
            "get_config_from_file",
        );
    }
    Options {
        file: opt_file.unwrap(),
        step_by_step_reduction: step,
        reduction_order: order,
    }
}
