use onig::{
    EncodedBytes, MatchParam, Regex, RegexOptions, SearchOptions, Syntax, SyntaxBehavior,
    SyntaxOperator,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct BreCompileError;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct BreMatchError;

pub(crate) trait Matcher {
    fn is_match(&self, _bytes: &[u8]) -> Result<bool, BreMatchError>;
}

#[derive(Debug)]
pub(crate) struct Bre {
    regex: Regex,
}

impl Bre {
    pub(crate) fn compile(pattern: &[u8]) -> Result<Self, BreCompileError> {
        let normalized = tokenize_bre(pattern)?;
        let mut syntax = Syntax::grep().clone();
        syntax.enable_operators(
            SyntaxOperator::SYNTAX_OPERATOR_ESC_GNU_BUF_ANCHOR
                | SyntaxOperator::SYNTAX_OPERATOR_ESC_W_WORD
                | SyntaxOperator::SYNTAX_OPERATOR_ESC_LTGT_WORD_BEGIN_END
                | SyntaxOperator::SYNTAX_OPERATOR_ESC_B_WORD_BOUND
                | SyntaxOperator::SYNTAX_OPERATOR_ESC_S_WHITE_SPACE,
        );
        syntax.disable_operators(
            SyntaxOperator::SYNTAX_OPERATOR_ESC_AZ_BUF_ANCHOR
                | SyntaxOperator::SYNTAX_OPERATOR_ESC_D_DIGIT
                | SyntaxOperator::SYNTAX_OPERATOR_ESC_CONTROL_CHARS,
        );
        syntax.set_behavior(SyntaxBehavior::empty());
        let options =
            RegexOptions::REGEX_OPTION_MULTILINE | RegexOptions::REGEX_OPTION_FIND_LONGEST;
        let regex =
            Regex::with_options_and_encoding(EncodedBytes::ascii(&normalized), options, &syntax)
                .map_err(|_| BreCompileError)?;
        Ok(Self { regex })
    }
}

impl Matcher for Bre {
    fn is_match(&self, bytes: &[u8]) -> Result<bool, BreMatchError> {
        self.regex
            .search_with_param(
                EncodedBytes::ascii(bytes),
                0,
                bytes.len(),
                SearchOptions::SEARCH_OPTION_NONE,
                None,
                MatchParam::default(),
            )
            .map(|result| result.is_some())
            .map_err(|_| BreMatchError)
    }
}

pub(crate) fn tokenize_bre(pattern: &[u8]) -> Result<Vec<u8>, BreCompileError> {
    let mut normalized = Vec::with_capacity(pattern.len());
    let mut index = 0;
    let mut at_branch_start = true;

    while index < pattern.len() {
        let byte = pattern[index];

        if byte == b'[' {
            let end = bracket_expression_end(pattern, index);
            normalized.extend_from_slice(&pattern[index..end]);
            index = end;
            at_branch_start = false;
            continue;
        }

        if byte == b'\\' {
            normalized.push(byte);
            if index + 1 < pattern.len() {
                index += 1;
                let escaped = pattern[index];
                if escaped == b'{' {
                    validate_interval(pattern, index)?;
                }
                normalized.push(escaped);
                at_branch_start = matches!(escaped, b'(' | b'|');
            } else {
                at_branch_start = false;
            }
            index += 1;
            continue;
        }

        match byte {
            b'^' if at_branch_start => normalized.extend_from_slice(b"\\`"),
            b'^' => normalized.extend_from_slice(b"\\^"),
            b'$' if is_end_anchor(pattern, index) => normalized.extend_from_slice(b"\\'"),
            b'$' => normalized.extend_from_slice(b"\\$"),
            _ => normalized.push(byte),
        }
        at_branch_start = false;
        index += 1;
    }

    Ok(normalized)
}

fn bracket_expression_end(pattern: &[u8], start: usize) -> usize {
    let mut index = start + 1;
    if pattern.get(index) == Some(&b'^') {
        index += 1;
    }
    if pattern.get(index) == Some(&b']') {
        index += 1;
    }

    while index < pattern.len() {
        if pattern[index] == b'[' {
            if let Some(marker @ (b'.' | b':' | b'=')) = pattern.get(index + 1).copied() {
                if let Some(end) = pattern[index + 2..]
                    .windows(2)
                    .position(|pair| pair == [marker, b']'])
                {
                    index += end + 4;
                    continue;
                }
            }
        }
        if pattern[index] == b']' {
            return index + 1;
        }
        index += 1;
    }

    pattern.len()
}

fn is_end_anchor(pattern: &[u8], index: usize) -> bool {
    index + 1 == pattern.len()
        || (index + 2 < pattern.len()
            && pattern[index + 1] == b'\\'
            && matches!(pattern[index + 2], b')' | b'|'))
}

fn validate_interval(pattern: &[u8], open: usize) -> Result<(), BreCompileError> {
    let mut close = open + 1;
    while close + 1 < pattern.len() {
        if pattern[close] == b'\\' {
            if pattern[close + 1] == b'}' {
                let body = &pattern[open + 1..close];
                let mut fields = body.split(|byte| *byte == b',');
                let lower = fields.next().and_then(parse_interval_bound);
                let upper = fields.next().and_then(parse_interval_bound);
                if fields.next().is_none()
                    && (lower.is_some() || upper.is_some())
                    && (lower.is_some_and(|value| value > 32_767)
                        || upper.is_some_and(|value| value > 32_767)
                        || matches!((lower, upper), (Some(lower), Some(upper)) if lower > upper))
                {
                    return Err(BreCompileError);
                }
                return Ok(());
            }
            close += 2;
        } else {
            close += 1;
        }
    }
    Ok(())
}

fn parse_interval_bound(bytes: &[u8]) -> Option<u64> {
    if bytes.is_empty() || !bytes.iter().all(u8::is_ascii_digit) {
        return None;
    }

    bytes.iter().try_fold(0_u64, |value, byte| {
        value.checked_mul(10)?.checked_add(u64::from(*byte - b'0'))
    })
}

#[cfg(test)]
pub(crate) mod mock {
    use super::{BreMatchError, Matcher};

    #[derive(Debug, Clone, Copy)]
    pub(crate) struct MockMatcher {
        pub(crate) result: Result<bool, BreMatchError>,
    }

    impl Matcher for MockMatcher {
        fn is_match(&self, _bytes: &[u8]) -> Result<bool, BreMatchError> {
            self.result
        }
    }
}

#[cfg(test)]
#[path = "bre/tests.rs"]
mod tests;
