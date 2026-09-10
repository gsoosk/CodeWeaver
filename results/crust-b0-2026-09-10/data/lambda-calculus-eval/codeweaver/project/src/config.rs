use std::fs::File;
use std::io::{self, BufRead};
use crate::{common, io as lce_io};
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
    let bytes = str.as_bytes();
    if bytes.is_empty() {
        return;
    }
    let len = bytes.len();
    let mut start: usize = 0;
    while start < len && (bytes[start] as char).is_whitespace() {
        start += 1;
    }
    let mut end: isize = len as isize - 1;
    while end > start as isize && (bytes[end as usize] as char).is_whitespace() {
        end -= 1;
    }
    if start > 0 || end < (len as isize - 1) {
        if end < start as isize {
            *str = String::new();
        } else {
            *str = str[start..(end as usize + 1)].to_string();
        }
    }
}
pub fn get_config_type(key: &str) -> option_type_t {
    if key == "file" {
        option_type_t::FILENAME
    } else if key == "step_by_step_reduction" {
        option_type_t::STEP_REDUCTION
    } else if key == "reduction_order" {
        option_type_t::REDUCTION_ORDER
    } else {
        let error_msg = common::format(
            "ERROR: Invalid key '%s' at config file.",
            format_args!("ERROR: Invalid key '{}' at config file.", key),
        );
        common::error(&error_msg, file!(), line!() as i32, "get_config_type");
        option_type_t::CONFIG_ERROR
    }
}
pub fn parse_config(line: &str, key: &mut String, value: &mut String) {
    match line.find('=') {
        None => {
            let error_msg = common::format(
                "Malformed config file",
                format_args!(
                    "Malformed config file at line: {} . Expected = sign.\n",
                    line
                ),
            );
            common::error(&error_msg, file!(), line!() as i32, "parse_config");
        }
        Some(eq_pos) => {
            let mut k = line[..eq_pos].to_string();
            let mut v = line[eq_pos + 1..].to_string();
            // Mirror strtok's behavior of stopping at the next '=' or end.
            if let Some(next_eq) = v.find('=') {
                v.truncate(next_eq);
            }
            trim(&mut k);
            trim(&mut v);
            *key = k;
            *value = v;
        }
    }
}
pub fn get_config_from_file() -> Options {
    let config_file = lce_io::get_file(CONFIG_PATH, "r")
        .unwrap_or_else(|e| panic!("ERROR: Could not open file {}: {}", CONFIG_PATH, e));
    let reader_handle = config_file
        .try_clone()
        .unwrap_or_else(|e| panic!("ERROR: Could not open file {}: {}", CONFIG_PATH, e));

    let mut options = Options {
        reduction_order: reduction_order_t::APPLICATIVE,
        step_by_step_reduction: false,
        file: config_file,
    };
    let mut has_file = false;

    let reader = io::BufReader::new(reader_handle);

    for line_result in reader.lines() {
        let line = match line_result {
            Ok(l) => l,
            Err(_) => break,
        };
        if line.is_empty() {
            continue;
        }
        let mut key = String::new();
        let mut value = String::new();
        parse_config(&line, &mut key, &mut value);
        let cfg = get_config_type(&key);

        match cfg {
            option_type_t::FILENAME => {
                let f = lce_io::get_file(&value, "r")
                    .unwrap_or_else(|e| panic!("ERROR: Could not open file {}: {}", value, e));
                options.file = f;
                has_file = true;
            }
            option_type_t::STEP_REDUCTION => {
                options.step_by_step_reduction = value == "true";
            }
            option_type_t::REDUCTION_ORDER => {
                if value == "applicative" {
                    options.reduction_order = reduction_order_t::APPLICATIVE;
                } else if value == "normal" {
                    options.reduction_order = reduction_order_t::NORMAL;
                } else {
                    common::error(
                        "ERROR: reduction order in cfg file should be 'normal' or 'applicative'.",
                        file!(),
                        line!() as i32,
                        "get_config_from_file",
                    );
                }
            }
            option_type_t::CONFIG_ERROR => {
                let error_msg = common::format(
                    "Unrecognized key",
                    format_args!("Unrecognized key: {}", key),
                );
                common::error(&error_msg, file!(), line!() as i32, "get_config_from_file");
            }
        }
    }

    if !has_file {
        common::error(
            "ERROR: File cannot be null in cfg file.\n",
            file!(),
            line!() as i32,
            "get_config_from_file",
        );
    }
    options
}

#[cfg(test)]
mod tests {
    use super::*;

    // Fixture-based: pure string helpers (trim/get_config_type/parse_config) are
    // unit-tested directly with no I/O; get_config_from_file needs a real temp
    // config-formatted file since it is fatal-on-error rather than Result-returning.

    #[test]
    fn test_trim_strips_leading_and_trailing_whitespace() {
        let mut s = "  hello world  ".to_string();
        trim(&mut s);
        assert_eq!(s, "hello world");

        let mut single = " x".to_string();
        trim(&mut single);
        assert_eq!(single, "x");

        let mut all_ws = "   ".to_string();
        trim(&mut all_ws);
        assert_eq!(all_ws, "");
    }

    #[test]
    fn test_get_config_type_maps_known_keys() {
        assert_eq!(get_config_type("file"), option_type_t::FILENAME);
        assert_eq!(
            get_config_type("step_by_step_reduction"),
            option_type_t::STEP_REDUCTION
        );
        assert_eq!(
            get_config_type("reduction_order"),
            option_type_t::REDUCTION_ORDER
        );
    }

    #[test]
    fn test_parse_config_splits_on_first_equals_and_trims() {
        let mut key = String::new();
        let mut value = String::new();
        parse_config(" file = my_file.lambda ", &mut key, &mut value);
        assert_eq!(key, "file");
        assert_eq!(value, "my_file.lambda");
    }
}