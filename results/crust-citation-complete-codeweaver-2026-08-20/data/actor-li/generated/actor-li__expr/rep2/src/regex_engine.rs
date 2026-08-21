#![allow(dead_code)]

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct ByteRange {
    pub(crate) start: usize,
    pub(crate) end: usize,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct RegexOutcome {
    pub(crate) subexpression_count: usize,
    pub(crate) whole_match: Option<ByteRange>,
    pub(crate) first_capture: Option<ByteRange>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct RegexError {
    pub(crate) message: Vec<u8>,
}

impl RegexError {
    fn unimplemented() -> Self {
        Self {
            message: b"TODO: RegexEngine::execute".to_vec(),
        }
    }
}

pub(crate) trait RegexEngine {
    fn execute(&self, pattern: &[u8], subject: &[u8]) -> Result<RegexOutcome, RegexError>;
}

#[derive(Default)]
pub(crate) struct PosixRegexEngine;

impl RegexEngine for PosixRegexEngine {
    fn execute(&self, _pattern: &[u8], _subject: &[u8]) -> Result<RegexOutcome, RegexError> {
        // TODO(Translator): dispatch UTF-8 inputs to regex-rs and byte inputs to posix-regex.
        Err(RegexError::unimplemented())
    }
}

pub(crate) fn normalize_regerror(_message: &[u8]) -> Vec<u8> {
    // TODO(Translator): strip only regex-rs's synthetic regcomp prefix.
    Vec::new()
}

pub(crate) fn scan_bre_subexpressions(_pattern: &[u8]) -> usize {
    // TODO(Translator): count escaped BRE groups outside bracket expressions.
    0
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum FallbackCompileError {
    InvalidRepetition,
    UnbalancedBracket,
    UnbalancedGroup,
    InvalidBackreference,
    Other,
}

pub(crate) fn map_fallback_compile_error(_error: FallbackCompileError) -> Vec<u8> {
    // TODO(Translator): normalize each byte-backend error to libc regerror bytes.
    Vec::new()
}

#[cfg(test)]
pub(crate) struct FakeRegexEngine {
    scripted: std::cell::RefCell<std::collections::VecDeque<Result<RegexOutcome, RegexError>>>,
}

#[cfg(test)]
impl FakeRegexEngine {
    pub(crate) fn new(scripted: Vec<Result<RegexOutcome, RegexError>>) -> Self {
        Self {
            scripted: std::cell::RefCell::new(scripted.into()),
        }
    }
}

#[cfg(test)]
impl RegexEngine for FakeRegexEngine {
    fn execute(&self, _pattern: &[u8], _subject: &[u8]) -> Result<RegexOutcome, RegexError> {
        match self.scripted.borrow_mut().pop_front() {
            Some(outcome) => outcome,
            None => Err(RegexError {
                message: b"FakeRegexEngine script exhausted".to_vec(),
            }),
        }
    }
}

#[cfg(test)]
mod tests {
    #[test]
    #[ignore = "TODO(M1): mock seam test stub"]
    fn fake_regex_engine_returns_scripted_outcomes() {
        todo!("implement during M1")
    }

    #[test]
    #[ignore = "TODO(M6): behavioral test stub"]
    fn real_engine_uses_bre_not_ere() {
        todo!("implement during M6")
    }

    #[test]
    #[ignore = "TODO(M6): behavioral test stub"]
    fn real_engine_rejects_unanchored_match() {
        todo!("implement during M6")
    }

    #[test]
    #[ignore = "TODO(M6): behavioral test stub"]
    fn real_engine_uses_leftmost_longest() {
        todo!("implement during M6")
    }

    #[test]
    #[ignore = "TODO(M7): behavioral test stub"]
    fn real_engine_extracts_first_capture() {
        todo!("implement during M7")
    }

    #[test]
    #[ignore = "TODO(M7): behavioral test stub"]
    fn real_engine_preserves_byte_offsets_inside_utf8() {
        todo!("implement during M7")
    }

    #[test]
    #[ignore = "TODO(M7): behavioral test stub"]
    fn real_engine_distinguishes_grouped_no_match() {
        todo!("implement during M7")
    }

    #[test]
    #[ignore = "TODO(M7): behavioral test stub"]
    fn real_engine_supports_backreferences_and_bracket_classes() {
        todo!("implement during M7")
    }

    #[test]
    #[ignore = "TODO(M6): behavioral test stub"]
    fn normalize_regerror_strips_only_wrapper() {
        todo!("implement during M6")
    }

    #[test]
    #[ignore = "TODO(M7): behavioral test stub"]
    fn scan_bre_subexpressions_handles_escapes_and_brackets() {
        todo!("implement during M7")
    }

    #[test]
    #[ignore = "TODO(M7): behavioral test stub"]
    fn byte_fallback_handles_invalid_utf8_literal_dot_capture_and_no_match() {
        todo!("implement during M7")
    }

    #[test]
    #[ignore = "TODO(M7): behavioral test stub"]
    fn fallback_error_mapper_covers_all_variants() {
        todo!("implement during M7")
    }
}
