use std::ops::Range;

use posix_regex::compile::Error as PosixError;
use posix_regex::PosixRegexBuilder;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct RegexMatch {
    pub(crate) capture_count: usize,
    pub(crate) whole_match: Option<Range<usize>>,
    pub(crate) first_capture: Option<Range<usize>>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct RegexError {
    pub(crate) message: Vec<u8>,
}

pub(crate) trait RegexBackend {
    fn compile_and_match(&self, pattern: &[u8], subject: &[u8]) -> Result<RegexMatch, RegexError>;
}

#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct PosixRegexBackend;

impl PosixRegexBackend {
    pub(crate) fn new() -> Self {
        Self
    }
}

impl RegexBackend for PosixRegexBackend {
    fn compile_and_match(&self, pattern: &[u8], subject: &[u8]) -> Result<RegexMatch, RegexError> {
        validate_pattern(pattern)?;
        let normalized = normalize_pattern(pattern);
        let regex = PosixRegexBuilder::new(&normalized)
            .with_default_classes()
            .extended(false)
            .compile()
            .map_err(|error| map_compile_error(compile_error_message(&error)))?;
        let capture_count = regex.count_groups().saturating_sub(1);
        let groups = regex
            .matches(subject, Some(1))
            .into_iter()
            .next()
            .filter(|groups| {
                groups
                    .first()
                    .and_then(|range| *range)
                    .is_some_and(|(start, _)| start == 0)
            });
        let whole_match = groups
            .as_ref()
            .and_then(|groups| groups.first())
            .and_then(|range| *range)
            .map(|(start, end)| start..end);
        let first_capture = groups
            .as_ref()
            .and_then(|groups| groups.get(1))
            .and_then(|range| *range)
            .map(|(start, end)| start..end);

        Ok(RegexMatch {
            capture_count,
            whole_match,
            first_capture,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum RepeatState {
    None,
    Atom,
    Star,
    Plus,
    Question,
    Interval,
}

fn validate_pattern(pattern: &[u8]) -> Result<(), RegexError> {
    let mut index = 0;
    let mut states = vec![RepeatState::None];
    let mut open_group_ids = Vec::new();
    let mut closed_groups = vec![false];
    let mut group_count = 0_usize;

    while index < pattern.len() {
        match pattern[index] {
            b'[' => {
                index = validate_bracket(pattern, index)?;
                *states.last_mut().expect("root parser state") = RepeatState::Atom;
            }
            b'\\' => {
                let Some(&escaped) = pattern.get(index + 1) else {
                    return Err(regex_error(b"Trailing backslash"));
                };
                match escaped {
                    b'(' => {
                        group_count += 1;
                        closed_groups.push(false);
                        open_group_ids.push(group_count);
                        states.push(RepeatState::None);
                    }
                    b')' => {
                        if states.len() == 1 {
                            return Err(regex_error(b"Unmatched ( or \\("));
                        }
                        states.pop();
                        let group_id = open_group_ids.pop().expect("open group state");
                        closed_groups[group_id] = true;
                        *states.last_mut().expect("parent parser state") = RepeatState::Atom;
                    }
                    b'1'..=b'9' => {
                        let group_id = usize::from(escaped - b'0');
                        if !closed_groups.get(group_id).copied().unwrap_or(false) {
                            return Err(regex_error(b"Invalid back reference"));
                        }
                        *states.last_mut().expect("root parser state") = RepeatState::Atom;
                    }
                    b'0' => {
                        *states.last_mut().expect("root parser state") = RepeatState::Atom;
                    }
                    b'+' => {
                        let state = states.last_mut().expect("root parser state");
                        *state = apply_repetition(*state, RepeatState::Plus)?;
                    }
                    b'?' => {
                        let state = states.last_mut().expect("root parser state");
                        *state = apply_repetition(*state, RepeatState::Question)?;
                    }
                    b'{' => {
                        let state = states.last_mut().expect("root parser state");
                        if *state == RepeatState::None {
                            return Err(regex_error(b"Invalid preceding regular expression"));
                        }
                        let omitted_lower_bound = pattern.get(index + 2) == Some(&b',');
                        index = validate_interval(pattern, index)?;
                        if !omitted_lower_bound {
                            *state = apply_repetition(*state, RepeatState::Interval)?;
                        }
                    }
                    b'|' => {
                        *states.last_mut().expect("root parser state") = RepeatState::None;
                    }
                    _ => {
                        *states.last_mut().expect("root parser state") = RepeatState::Atom;
                    }
                }
                index += 2;
            }
            b'*' => {
                let state = states.last_mut().expect("root parser state");
                *state = apply_repetition(*state, RepeatState::Star)?;
                index += 1;
            }
            _ => {
                *states.last_mut().expect("root parser state") = RepeatState::Atom;
                index += 1;
            }
        }
    }

    if states.len() != 1 {
        return Err(regex_error(b"Unmatched ( or \\("));
    }
    Ok(())
}

fn apply_repetition(
    current: RepeatState,
    repetition: RepeatState,
) -> Result<RepeatState, RegexError> {
    match (current, repetition) {
        (RepeatState::None, RepeatState::Star | RepeatState::Plus | RepeatState::Question) => {
            Ok(RepeatState::Atom)
        }
        (RepeatState::None, RepeatState::Interval) => {
            Err(regex_error(b"Invalid preceding regular expression"))
        }
        (RepeatState::Atom, repetition) => Ok(repetition),
        (
            RepeatState::Star | RepeatState::Plus | RepeatState::Question | RepeatState::Interval,
            RepeatState::Plus | RepeatState::Question,
        ) => Ok(current),
        _ => Err(regex_error(b"Invalid preceding regular expression")),
    }
}

fn validate_bracket(pattern: &[u8], start: usize) -> Result<usize, RegexError> {
    let mut index = start + 1;
    if pattern.get(index) == Some(&b'^') {
        index += 1;
    }
    if index == pattern.len() {
        return Err(regex_error(b"Invalid regular expression"));
    }

    let mut item_count = 0_usize;
    if pattern.get(index) == Some(&b']') {
        index += 1;
        item_count += 1;
    }
    let mut previous_was_range = false;

    while index < pattern.len() {
        if pattern[index] == b']' && item_count > 0 {
            return Ok(index + 1);
        }
        if previous_was_range
            && pattern[index] == b'-'
            && pattern.get(index + 1).is_some_and(|byte| *byte != b']')
        {
            return Err(regex_error(b"Invalid range end"));
        }

        let (begin, next) = bracket_element(pattern, index)?;
        item_count += 1;
        index = next;

        if pattern.get(index) == Some(&b'-')
            && pattern.get(index + 1).is_some_and(|byte| *byte != b']')
        {
            let Some(begin) = begin else {
                return Err(regex_error(b"Invalid range end"));
            };
            let (end, next) = bracket_element(pattern, index + 1)?;
            let Some(end) = end else {
                return Err(regex_error(b"Invalid range end"));
            };
            if begin > end {
                return Err(regex_error(b"Invalid range end"));
            }
            item_count += 1;
            index = next;
            previous_was_range = true;
        } else {
            previous_was_range = false;
        }
    }

    Err(regex_error(b"Unmatched [, [^, [:, [., or [="))
}

fn bracket_element(pattern: &[u8], index: usize) -> Result<(Option<u8>, usize), RegexError> {
    if pattern.get(index) == Some(&b'[') {
        if let Some(&delimiter @ (b':' | b'.' | b'=')) = pattern.get(index + 1) {
            let closing = [delimiter, b']'];
            let Some(offset) = pattern[index + 2..]
                .windows(2)
                .position(|window| window == closing)
            else {
                return Err(regex_error(b"Unmatched [, [^, [:, [., or [="));
            };
            let content = &pattern[index + 2..index + 2 + offset];
            if delimiter != b':' && content.len() != 1 {
                return Err(regex_error(b"Invalid collation character"));
            }
            let endpoint = (delimiter == b'.').then(|| content[0]);
            return Ok((endpoint, index + offset + 4));
        }
    }
    pattern
        .get(index)
        .copied()
        .map(|byte| (Some(byte), index + 1))
        .ok_or_else(|| regex_error(b"Unmatched [, [^, [:, [., or [="))
}

fn validate_interval(pattern: &[u8], slash: usize) -> Result<usize, RegexError> {
    let mut index = slash + 2;
    let first_start = index;
    while pattern.get(index).is_some_and(u8::is_ascii_digit) {
        index += 1;
    }
    if index == first_start {
        if index == pattern.len() {
            return Err(regex_error(b"Unmatched \\{"));
        }
        if pattern[index] == b',' {
            index += 1;
            let second_start = index;
            while pattern.get(index).is_some_and(u8::is_ascii_digit) {
                index += 1;
            }
            if index > second_start {
                parse_bound(&pattern[second_start..index])?;
            }
            if pattern.get(index..index + 2) != Some(br"\}") {
                return Err(interval_closing_error(pattern, index));
            }
            return Ok(index);
        }
        return Err(regex_error(b"Invalid content of \\{\\}"));
    }
    let first = parse_bound(&pattern[first_start..index])?;
    let mut second = Some(first);
    if pattern.get(index) == Some(&b',') {
        index += 1;
        let second_start = index;
        while pattern.get(index).is_some_and(u8::is_ascii_digit) {
            index += 1;
        }
        second = if index == second_start {
            None
        } else {
            Some(parse_bound(&pattern[second_start..index])?)
        };
    }
    if let Some(second) = second {
        if first > second {
            return Err(regex_error(b"Invalid content of \\{\\}"));
        }
    }
    if pattern.get(index..index + 2) != Some(br"\}") {
        return Err(interval_closing_error(pattern, index));
    }
    Ok(index)
}

fn interval_closing_error(pattern: &[u8], index: usize) -> RegexError {
    if pattern.get(index).is_none_or(|byte| *byte == b'}') {
        regex_error(b"Unmatched \\{")
    } else {
        regex_error(b"Invalid content of \\{\\}")
    }
}

fn parse_bound(bytes: &[u8]) -> Result<u32, RegexError> {
    bytes.iter().try_fold(0_u32, |value, byte| {
        let value = value
            .checked_mul(10)
            .and_then(|value| value.checked_add(u32::from(*byte - b'0')))
            .ok_or_else(|| regex_error(b"Regular expression too big"))?;
        if value > 32_767 {
            Err(regex_error(b"Regular expression too big"))
        } else {
            Ok(value)
        }
    })
}

const EMPTY_EXPRESSION: &[u8] = br"x\{0\}";
const IMPOSSIBLE_EXPRESSION: &[u8] = b"[^\x00-\xff]";

#[derive(Clone, Copy, Debug)]
struct NormalizeState {
    has_token: bool,
    repetition: RepeatState,
    quantifier_start: usize,
    interval_minimum: u32,
    branch_start_word: Option<bool>,
    last_word: Option<bool>,
}

impl NormalizeState {
    fn new(previous_word: Option<bool>) -> Self {
        Self {
            has_token: false,
            repetition: RepeatState::None,
            quantifier_start: 0,
            interval_minimum: 0,
            branch_start_word: previous_word,
            last_word: previous_word,
        }
    }

    fn mark_atom(&mut self, word: Option<bool>) {
        self.has_token = true;
        self.repetition = RepeatState::Atom;
        self.last_word = word;
    }

    fn mark_zero_width(&mut self) {
        self.has_token = true;
        self.repetition = RepeatState::Atom;
    }
}

fn normalize_pattern(pattern: &[u8]) -> Vec<u8> {
    let mut normalized = Vec::with_capacity(pattern.len());
    let mut states = vec![NormalizeState::new(Some(false))];
    let mut index = 0;
    while index < pattern.len() {
        match pattern[index] {
            b'[' => {
                let end = validate_bracket(pattern, index)
                    .expect("pattern was validated before normalization");
                normalize_bracket(&pattern[index..end], &mut normalized);
                states.last_mut().expect("root branch").mark_atom(None);
                index = end;
            }
            b'^' => {
                let state = states.last_mut().expect("root branch");
                if state.has_token {
                    normalized.extend_from_slice(br"\^");
                    state.mark_atom(Some(false));
                } else {
                    normalized.push(b'^');
                    state.mark_zero_width();
                }
                index += 1;
            }
            b'$' => {
                let state = states.last_mut().expect("root branch");
                if is_branch_end(pattern, index + 1) {
                    normalized.push(b'$');
                    state.mark_zero_width();
                } else {
                    normalized.extend_from_slice(br"\$");
                    state.mark_atom(Some(false));
                }
                index += 1;
            }
            b'\\' => {
                let escaped = pattern[index + 1];
                match escaped {
                    b'(' => {
                        normalized.extend_from_slice(br"\(");
                        let previous_word = states.last().expect("group parent").last_word;
                        states.push(NormalizeState::new(previous_word));
                        index += 2;
                    }
                    b')' => {
                        let state = states.pop().expect("validated group");
                        if !state.has_token {
                            normalized.extend_from_slice(EMPTY_EXPRESSION);
                        }
                        normalized.extend_from_slice(br"\)");
                        states.last_mut().expect("group parent").mark_atom(None);
                        index += 2;
                    }
                    b'|' => {
                        let state = states.last_mut().expect("root branch");
                        if !state.has_token {
                            normalized.extend_from_slice(EMPTY_EXPRESSION);
                        }
                        normalized.extend_from_slice(br"\|");
                        *state = NormalizeState::new(state.branch_start_word);
                        index += 2;
                    }
                    b'a' | b'd' | b'n' | b'r' | b't' | b'0' => {
                        normalized.push(escaped);
                        states
                            .last_mut()
                            .expect("root branch")
                            .mark_atom(Some(is_word_byte(escaped)));
                        index += 2;
                    }
                    b's' => {
                        normalized.extend_from_slice(br"\s");
                        states
                            .last_mut()
                            .expect("root branch")
                            .mark_atom(Some(false));
                        index += 2;
                    }
                    b'S' => {
                        normalized.extend_from_slice(br"\S");
                        states.last_mut().expect("root branch").mark_atom(None);
                        index += 2;
                    }
                    b'w' => {
                        normalized.extend_from_slice(b"[[:alnum:]_]");
                        states
                            .last_mut()
                            .expect("root branch")
                            .mark_atom(Some(true));
                        index += 2;
                    }
                    b'W' => {
                        normalized.extend_from_slice(b"[^[:alnum:]_]");
                        states
                            .last_mut()
                            .expect("root branch")
                            .mark_atom(Some(false));
                        index += 2;
                    }
                    b'b' | b'B' => {
                        normalize_word_boundary(
                            escaped == b'b',
                            pattern,
                            index + 2,
                            &mut normalized,
                            states.last_mut().expect("root branch"),
                        );
                        index += 2;
                    }
                    b'1'..=b'9' => {
                        normalized.extend_from_slice(&pattern[index..index + 2]);
                        states.last_mut().expect("root branch").mark_atom(None);
                        index += 2;
                        while let Some(&digit @ b'0'..=b'9') = pattern.get(index) {
                            normalized.extend_from_slice(&[b'[', digit, b']']);
                            states
                                .last_mut()
                                .expect("root branch")
                                .mark_atom(Some(true));
                            index += 1;
                        }
                    }
                    b'`' => {
                        normalized.push(b'^');
                        states.last_mut().expect("root branch").mark_zero_width();
                        index += 2;
                    }
                    b'\'' => {
                        normalized.push(b'$');
                        states.last_mut().expect("root branch").mark_zero_width();
                        index += 2;
                    }
                    b'+' | b'?' => {
                        append_quantifier(
                            &mut normalized,
                            states.last_mut().expect("root branch"),
                            if escaped == b'+' {
                                RepeatState::Plus
                            } else {
                                RepeatState::Question
                            },
                            &pattern[index..index + 2],
                            0,
                        );
                        index += 2;
                    }
                    b'{' => {
                        let closing = validate_interval(pattern, index)
                            .expect("pattern was validated before normalization");
                        let end = closing + 2;
                        if pattern.get(index + 2) != Some(&b',') {
                            let minimum = interval_minimum(pattern, index);
                            append_quantifier(
                                &mut normalized,
                                states.last_mut().expect("root branch"),
                                RepeatState::Interval,
                                &pattern[index..end],
                                minimum,
                            );
                        }
                        index = end;
                    }
                    b'<' | b'>' => {
                        normalized.extend_from_slice(&pattern[index..index + 2]);
                        states.last_mut().expect("root branch").mark_zero_width();
                        index += 2;
                    }
                    _ => {
                        normalized.extend_from_slice(&pattern[index..index + 2]);
                        states
                            .last_mut()
                            .expect("root branch")
                            .mark_atom(Some(is_word_byte(escaped)));
                        index += 2;
                    }
                }
            }
            b'*' => {
                append_quantifier(
                    &mut normalized,
                    states.last_mut().expect("root branch"),
                    RepeatState::Star,
                    b"*",
                    0,
                );
                index += 1;
            }
            b'.' => {
                normalized.push(b'.');
                states.last_mut().expect("root branch").mark_atom(None);
                index += 1;
            }
            byte => {
                normalized.push(byte);
                states
                    .last_mut()
                    .expect("root branch")
                    .mark_atom(Some(is_word_byte(byte)));
                index += 1;
            }
        }
    }
    let state = states.pop().expect("root branch");
    if !state.has_token {
        normalized.extend_from_slice(EMPTY_EXPRESSION);
    }
    normalized
}

fn append_quantifier(
    normalized: &mut Vec<u8>,
    state: &mut NormalizeState,
    repetition: RepeatState,
    spelling: &[u8],
    interval_minimum: u32,
) {
    match state.repetition {
        RepeatState::None => {
            normalized.extend_from_slice(spelling);
            state.mark_atom(Some(false));
        }
        RepeatState::Atom => {
            state.quantifier_start = normalized.len();
            state.interval_minimum = interval_minimum;
            normalized.extend_from_slice(spelling);
            state.repetition = repetition;
        }
        RepeatState::Star | RepeatState::Question if repetition == RepeatState::Plus => {
            normalized.truncate(state.quantifier_start);
            normalized.extend_from_slice(br"\+");
            state.repetition = RepeatState::Plus;
        }
        RepeatState::Plus if repetition == RepeatState::Plus => {}
        RepeatState::Interval if repetition == RepeatState::Plus => {
            normalized.truncate(state.quantifier_start);
            normalized.extend_from_slice(br"\{");
            normalized.extend_from_slice(state.interval_minimum.to_string().as_bytes());
            normalized.extend_from_slice(br",\}");
        }
        RepeatState::Star | RepeatState::Plus | RepeatState::Question | RepeatState::Interval
            if repetition == RepeatState::Question => {}
        _ => unreachable!("validation rejects this repetition combination"),
    }
}

fn interval_minimum(pattern: &[u8], slash: usize) -> u32 {
    let start = slash + 2;
    let end = pattern[start..]
        .iter()
        .position(|byte| !byte.is_ascii_digit())
        .map_or(pattern.len(), |offset| start + offset);
    pattern[start..end]
        .iter()
        .fold(0_u32, |value, byte| value * 10 + u32::from(*byte - b'0'))
}

fn normalize_word_boundary(
    wants_boundary: bool,
    pattern: &[u8],
    next_index: usize,
    normalized: &mut Vec<u8>,
    state: &mut NormalizeState,
) {
    let next_word = next_word_kind(pattern, next_index);
    let boundary = state
        .last_word
        .zip(next_word)
        .map(|(previous, next)| previous != next);

    match boundary {
        Some(actual) if actual == wants_boundary => {
            normalized.extend_from_slice(EMPTY_EXPRESSION);
            state.mark_zero_width();
        }
        Some(_) => {
            normalized.extend_from_slice(IMPOSSIBLE_EXPRESSION);
            state.mark_atom(None);
        }
        None if wants_boundary && next_word == Some(true) => {
            normalized.extend_from_slice(br"\<");
            state.mark_zero_width();
        }
        None if wants_boundary && state.last_word == Some(true) => {
            normalized.extend_from_slice(br"\>");
            state.mark_zero_width();
        }
        None => {
            normalized.extend_from_slice(IMPOSSIBLE_EXPRESSION);
            state.mark_atom(None);
        }
    }
}

fn next_word_kind(pattern: &[u8], mut index: usize) -> Option<bool> {
    loop {
        let Some(&byte) = pattern.get(index) else {
            return Some(false);
        };
        match byte {
            b'^' | b'$' => index += 1,
            b'[' | b'.' => return None,
            b'\\' => {
                let escaped = *pattern.get(index + 1)?;
                match escaped {
                    b')' | b'|' => return Some(false),
                    b'(' | b'b' | b'B' | b'<' | b'>' | b'`' | b'\'' => index += 2,
                    b'w' => return Some(true),
                    b'W' | b's' => return Some(false),
                    b'S' | b'1'..=b'9' => return None,
                    b'a' | b'd' | b'n' | b'r' | b't' | b'0' => {
                        return Some(is_word_byte(escaped));
                    }
                    _ => return Some(is_word_byte(escaped)),
                }
            }
            _ => return Some(is_word_byte(byte)),
        }
    }
}

fn is_word_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'_'
}

fn normalize_bracket(bracket: &[u8], normalized: &mut Vec<u8>) {
    let mut expanded = Vec::with_capacity(bracket.len());
    let mut index = 0;
    while index < bracket.len() {
        if bracket.get(index) == Some(&b'[')
            && bracket
                .get(index + 1)
                .is_some_and(|byte| matches!(byte, b'.' | b'='))
        {
            let delimiter = bracket[index + 1];
            expanded.push(bracket[index + 2]);
            let closing = [delimiter, b']'];
            let offset = bracket[index + 3..]
                .windows(2)
                .position(|window| window == closing)
                .expect("validated collation element");
            index += offset + 5;
        } else {
            expanded.push(bracket[index]);
            index += 1;
        }
    }

    index = 0;
    while index < expanded.len() {
        if expanded.get(index) == Some(&0xff)
            && expanded.get(index + 1) == Some(&b'-')
            && expanded.get(index + 2) == Some(&0xff)
        {
            normalized.push(0xff);
            index += 3;
        } else {
            normalized.push(expanded[index]);
            index += 1;
        }
    }
}

fn is_branch_end(pattern: &[u8], index: usize) -> bool {
    index == pattern.len()
        || pattern.get(index..index + 2) == Some(br"\|")
        || pattern.get(index..index + 2) == Some(br"\)")
}

fn compile_error_message(error: &PosixError) -> &'static [u8] {
    match error {
        PosixError::EOF => b"Invalid regular expression",
        PosixError::EmptyRepetition | PosixError::IllegalRange => b"Invalid content of \\{\\}",
        PosixError::IntegerOverflow => b"Regular expression too big",
        PosixError::UnclosedRepetition => b"Unmatched \\{",
        PosixError::InvalidBackRef(_) => b"Invalid back reference",
        PosixError::LeadingRepetition => b"Invalid preceding regular expression",
        PosixError::UnknownClass(_) => b"Invalid character class name",
        PosixError::UnknownCollation => b"Invalid collation character",
        PosixError::Expected(_, _) | PosixError::UnexpectedToken(_) => {
            b"Invalid regular expression"
        }
    }
}

fn map_compile_error(diagnostic: &[u8]) -> RegexError {
    regex_error(diagnostic)
}

fn regex_error(message: &[u8]) -> RegexError {
    RegexError {
        message: message.to_vec(),
    }
}

#[cfg(test)]
pub(crate) mod test_support {
    use std::cell::RefCell;
    use std::collections::VecDeque;

    use super::{RegexBackend, RegexError, RegexMatch};

    #[derive(Default)]
    pub(crate) struct FakeRegexBackend {
        responses: RefCell<VecDeque<Result<RegexMatch, RegexError>>>,
        calls: RefCell<Vec<(Vec<u8>, Vec<u8>)>>,
    }

    impl FakeRegexBackend {
        pub(crate) fn new(responses: Vec<Result<RegexMatch, RegexError>>) -> Self {
            Self {
                responses: RefCell::new(responses.into()),
                calls: RefCell::new(Vec::new()),
            }
        }

        pub(crate) fn calls(&self) -> Vec<(Vec<u8>, Vec<u8>)> {
            self.calls.borrow().clone()
        }
    }

    impl RegexBackend for FakeRegexBackend {
        fn compile_and_match(
            &self,
            pattern: &[u8],
            subject: &[u8],
        ) -> Result<RegexMatch, RegexError> {
            self.calls
                .borrow_mut()
                .push((pattern.to_vec(), subject.to_vec()));
            self.responses
                .borrow_mut()
                .pop_front()
                .expect("fake regex response queue exhausted")
        }
    }
}

#[cfg(test)]
mod tests {
    use std::ops::Range;

    use super::{PosixRegexBackend, RegexBackend, RegexError, RegexMatch};

    fn compile_and_match(pattern: &[u8], subject: &[u8]) -> Result<RegexMatch, RegexError> {
        PosixRegexBackend::new().compile_and_match(pattern, subject)
    }

    fn assert_match(
        pattern: &[u8],
        subject: &[u8],
        capture_count: usize,
        whole_match: Option<Range<usize>>,
        first_capture: Option<Range<usize>>,
    ) {
        assert_eq!(
            compile_and_match(pattern, subject),
            Ok(RegexMatch {
                capture_count,
                whole_match,
                first_capture,
            }),
            "pattern {pattern:?}, subject {subject:?}"
        );
    }

    fn assert_error(pattern: &[u8], message: &[u8]) {
        assert_eq!(
            compile_and_match(pattern, b"subject"),
            Err(RegexError {
                message: message.to_vec(),
            }),
            "pattern {pattern:?}"
        );
    }

    #[test]
    fn backend_matches_literals_dots_anchors_and_classes() {
        assert_match(b"abc", b"abcdef", 0, Some(0..3), None);
        assert_match(b"abc", b"zabc", 0, None, None);
        assert_match(b"a.c", b"abc", 0, Some(0..3), None);
        assert_match(b"^a", b"abc", 0, Some(0..1), None);
        assert_match(b"a$", b"a", 0, Some(0..1), None);
        assert_match(b"a$", b"ab", 0, None, None);
        assert_match(b"a^b", b"a^b", 0, Some(0..3), None);
        assert_match(b"a$b", b"a$b", 0, Some(0..3), None);
        assert_match(b"[a-c][^0-9]", b"b!", 0, Some(0..2), None);
        assert_match(b"[[:upper:]][[:digit:]]", b"A7", 0, Some(0..2), None);
        assert_match(b"[[.a.]][[=b=]]", b"ab", 0, Some(0..2), None);
        assert_match(b"[[.a.]-c]", b"b", 0, Some(0..1), None);
        assert_match(b"[a-[.c.]]", b"b", 0, Some(0..1), None);
    }

    #[test]
    fn backend_reports_match_and_first_capture_ranges() {
        assert_match(br"a\(bc\)d", b"abcdef", 1, Some(0..4), Some(1..3));
        assert_match(br"\(a\)\(bc\)", b"abcdef", 2, Some(0..3), Some(0..1));
        assert_match(br"\(a\(b\)c\)", b"abcdef", 2, Some(0..3), Some(0..3));
        assert_match(br"\(ab\)*", b"ababx", 1, Some(0..4), Some(2..4));
    }

    #[test]
    fn backend_handles_optional_multiple_and_empty_groups() {
        assert_match(br"\(a\)\?\(b\)", b"b", 2, Some(0..1), None);
        assert_match(br"\(a\)\?\(b\)", b"ab", 2, Some(0..2), Some(0..1));
        assert_match(br"\(\)a", b"a", 1, Some(0..1), Some(0..0));
        assert_match(br"\(a*\)b", b"b", 1, Some(0..1), Some(0..0));
        assert_match(br"\(a\)\?", b"", 1, Some(0..0), None);
        assert_match(b"", b"abc", 0, Some(0..0), None);
        assert_match(br"a\|", b"", 0, Some(0..0), None);
        assert_match(br"\(a\|\)", b"", 1, Some(0..0), Some(0..0));
    }

    #[test]
    fn backend_uses_leftmost_longest_greedy_matching() {
        assert_match(b"a*", b"aaaab", 0, Some(0..4), None);
        assert_match(br"a\|aa", b"aab", 0, Some(0..2), None);
        assert_match(br"\(a\|aa\)", b"aab", 1, Some(0..2), Some(0..2));
        assert_match(b".*b", b"abbbx", 0, Some(0..4), None);
        assert_match(br"[ab]\{1,3\}", b"aaab", 0, Some(0..3), None);
    }

    #[test]
    fn backend_supports_gnu_bre_extensions_and_backreferences() {
        assert_match(br"a\+", b"aaab", 0, Some(0..3), None);
        assert_match(br"a\?b", b"b", 0, Some(0..1), None);
        assert_match(br"a\|bc", b"bc", 0, Some(0..2), None);
        assert_match(br"\<word\>", b"word!", 0, Some(0..4), None);
        assert_match(br"\(ab\)\1", b"ababx", 1, Some(0..4), Some(0..2));
        assert_match(br"\s\+", b" \tx", 0, Some(0..2), None);
        assert_match(br"\S\+", b"abc ", 0, Some(0..3), None);
        assert_match(br"\w\+", b"abc_12!", 0, Some(0..6), None);
        assert_match(br"\W\+", b"!!!a", 0, Some(0..3), None);
        assert_match(br"\bword\b", b"word!", 0, Some(0..4), None);
        assert_match(br"a\Bword", b"aword", 0, Some(0..5), None);
        assert_match(br"\`word", b"word", 0, Some(0..4), None);
        assert_match(br"word\'", b"word", 0, Some(0..4), None);
        assert_match(br"\0", b"0", 0, Some(0..1), None);
        assert_match(br"\(a\)\10", b"aa0", 1, Some(0..3), Some(0..1));
        assert_match(br"a\+\+", b"aaa", 0, Some(0..3), None);
        assert_match(br"a*\+", b"aaa", 0, Some(0..3), None);
        assert_match(br"a\+\?", b"aaa", 0, Some(0..3), None);
        assert_match(br"a\{2,3\}\+", b"aaaa", 0, Some(0..4), None);
    }

    #[test]
    fn backend_treats_escaped_ordinary_letters_like_libc() {
        assert_match(br"\a\d\n\r\t", b"adnrt", 0, Some(0..5), None);
        assert_match(br"\q\x\z", b"qxz", 0, Some(0..3), None);
        assert_match(br"\^a\$", b"^a$", 0, Some(0..3), None);
    }

    #[test]
    fn backend_rejects_invalid_ranges_repetitions_groups_and_references() {
        let cases: &[(&[u8], &[u8])] = &[
            (b"[a", b"Unmatched [, [^, [:, [., or [="),
            (b"[z-a]", b"Invalid range end"),
            (b"[[:digit:]-a]", b"Invalid range end"),
            (b"a**", b"Invalid preceding regular expression"),
            (br"\(a", br"Unmatched ( or \("),
            (br"a\)", br"Unmatched ( or \("),
            (br"\1", b"Invalid back reference"),
            (br"\(a\)\2", b"Invalid back reference"),
            (br"\(\1a\)", b"Invalid back reference"),
            (br"a\{2", br"Unmatched \{"),
            (br"a\{2}", br"Unmatched \{"),
            (br"a\{\}", br"Invalid content of \{\}"),
            (br"a\{2,1\}", br"Invalid content of \{\}"),
            (br"a\{1x\}", br"Invalid content of \{\}"),
            (br"a\{32768\}", b"Regular expression too big"),
            (b"[[.ab.]]", b"Invalid collation character"),
            (b"[[=a=]-c]", b"Invalid range end"),
        ];
        for &(pattern, message) in cases {
            assert_error(pattern, message);
        }

        assert_match(b"*a", b"*a", 0, Some(0..2), None);
        assert_match(br"\+a", b"+a", 0, Some(0..2), None);
        assert_match(br"\?a", b"?a", 0, Some(0..2), None);
        assert_match(br"a\{,\}", b"a{,}", 0, Some(0..1), None);
        assert_match(br"a\{,1\}", b"a{,1}", 0, Some(0..1), None);
    }

    #[test]
    fn backend_maps_compile_errors_to_libc_text() {
        let cases: &[(&[u8], &[u8])] = &[
            (b"\\", b"Trailing backslash"),
            (b"[", b"Invalid regular expression"),
            (b"[]", b"Unmatched [, [^, [:, [., or [="),
            (b"[[:bogus:]]", b"Invalid character class name"),
            (b"[z-a]", b"Invalid range end"),
            (br"\1", b"Invalid back reference"),
            (br"\(", br"Unmatched ( or \("),
            (br"a\{", br"Unmatched \{"),
            (br"a\{\}", br"Invalid content of \{\}"),
            (b"a**", b"Invalid preceding regular expression"),
        ];
        for &(pattern, message) in cases {
            assert_error(pattern, message);
        }
    }

    #[test]
    fn backend_preserves_raw_high_bytes() {
        assert_match(b"\xffa", b"\xffabc", 0, Some(0..2), None);
        assert_match(b".", b"\xff", 0, Some(0..1), None);
        assert_match(b"[^\x00-\x7f]", b"\xff", 0, Some(0..1), None);
        assert_match(b"[\xfe-\xff]", b"\xff", 0, Some(0..1), None);
        assert_match(b"[\xff-\xff]", b"\xff", 0, Some(0..1), None);
        assert_match(b"[[.\xff.]-\xff]", b"\xff", 0, Some(0..1), None);
        assert_match(b"\\(\xff\\)", b"\xff", 1, Some(0..1), Some(0..1));
    }

    #[test]
    fn reported_regex_misses_compile_with_capture_counts() {
        let backend = super::PosixRegexBackend::new();
        let literal_miss = super::RegexBackend::compile_and_match(&backend, b"world", b"hello")
            .expect("literal pattern must compile");
        assert_eq!(
            literal_miss,
            super::RegexMatch {
                capture_count: 0,
                whole_match: None,
                first_capture: None,
            }
        );

        let capture_miss =
            super::RegexBackend::compile_and_match(&backend, br"h\(xyz\)o", b"hello")
                .expect("capturing pattern must compile");
        assert_eq!(
            capture_miss,
            super::RegexMatch {
                capture_count: 1,
                whole_match: None,
                first_capture: None,
            }
        );

        let empty_subject_miss = super::RegexBackend::compile_and_match(&backend, b"hello", b"")
            .expect("literal pattern must compile");
        assert_eq!(
            empty_subject_miss,
            super::RegexMatch {
                capture_count: 0,
                whole_match: None,
                first_capture: None,
            }
        );
    }
}
