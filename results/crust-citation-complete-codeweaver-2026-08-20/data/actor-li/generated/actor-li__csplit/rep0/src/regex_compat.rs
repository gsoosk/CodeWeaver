use crate::csplit::{parse_c_long, AppError, RegexCompiler, RegexMatcher};
use posix_regex::{PosixRegex, PosixRegexBuilder};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct ParsedExpression<'a> {
    pub(crate) delimiter: u8,
    pub(crate) pattern: &'a [u8],
    pub(crate) offset: i64,
}

pub(crate) fn parse_expression(expression: &[u8]) -> Result<ParsedExpression<'_>, AppError> {
    let delimiter = expression.first().copied().unwrap_or(b'/');
    let closing = expression
        .iter()
        .rposition(|byte| *byte == delimiter)
        .unwrap_or(0);

    if closing > 0 && expression.get(closing - 1) == Some(&b'\\') {
        let mut message = expression.to_vec();
        message.extend_from_slice(b": missing trailing ");
        message.push(delimiter);
        return Err(AppError::Message(message));
    }

    let (pattern, suffix) = if closing == 0 {
        let tail = expression.get(1..).unwrap_or_default();
        (&tail[..0], tail)
    } else {
        (&expression[1..closing], &expression[closing + 1..])
    };
    let offset = if suffix.is_empty() {
        0
    } else {
        let parsed = parse_c_long(suffix);
        if !parsed.had_digits || parsed.overflow || parsed.end != suffix.len() {
            let mut message = suffix.to_vec();
            message.extend_from_slice(b": bad offset");
            return Err(AppError::Message(message));
        }
        parsed.value
    };

    Ok(ParsedExpression {
        delimiter,
        pattern,
        offset,
    })
}

#[derive(Debug, Clone, Copy, Default)]
pub(crate) struct GlibcBreCompiler;

impl RegexCompiler for GlibcBreCompiler {
    fn compile(&self, pattern: &[u8]) -> Result<Box<dyn RegexMatcher>, AppError> {
        let normalized = if pattern
            .windows(2)
            .any(|pair| pair[0] == b'\\' && matches!(pair[1], b'b' | b'B' | b'<' | b'>'))
        {
            normalize_glibc_bre_details(pattern)?
        } else {
            NormalizedBre {
                bytes: normalize_glibc_bre(pattern)?,
                boundaries: Vec::new(),
                without_boundaries: None,
            }
        };
        if normalized.bytes.is_empty() {
            return Ok(Box::new(EmptyBreMatcher));
        }
        let regex = PosixRegexBuilder::new(&normalized.bytes)
            .with_default_classes()
            .compile()
            .map_err(|_| bad_regex(pattern))?;
        let without_boundaries = normalized
            .without_boundaries
            .as_deref()
            .map(|bytes| {
                PosixRegexBuilder::new(bytes)
                    .with_default_classes()
                    .compile()
                    .map_err(|_| bad_regex(pattern))
            })
            .transpose()?;
        Ok(Box::new(GlibcBreMatcher {
            regex,
            boundaries: normalized.boundaries,
            without_boundaries,
        }))
    }
}

struct EmptyBreMatcher;

impl RegexMatcher for EmptyBreMatcher {
    fn is_match(&self, _bytes: &[u8]) -> bool {
        true
    }
}

pub(crate) struct GlibcBreMatcher {
    regex: PosixRegex<'static>,
    boundaries: Vec<BoundaryAssertion>,
    without_boundaries: Option<PosixRegex<'static>>,
}

impl RegexMatcher for GlibcBreMatcher {
    fn is_match(&self, bytes: &[u8]) -> bool {
        let visible = bytes
            .iter()
            .position(|byte| *byte == b'\0')
            .map_or(bytes, |nul| &bytes[..nul]);
        if !self.boundaries.is_empty() {
            let boundary_match = (0..=visible.len()).any(|offset| {
                let regex = self.regex.clone().no_start(offset != 0);
                regex
                    .matches_exact(&visible[offset..])
                    .is_some_and(|groups| {
                        self.boundaries
                            .iter()
                            .all(|assertion| assertion.matches(visible, offset, groups.as_ref()))
                    })
            });
            // The dependency can retain captures from a rejected alternative.
            // Retry branches that contain no GNU boundary assertions.
            return boundary_match
                || self
                    .without_boundaries
                    .as_ref()
                    .is_some_and(|regex| has_match(regex, visible));
        }
        has_match(&self.regex, visible)
    }
}

fn has_match(regex: &PosixRegex<'_>, input: &[u8]) -> bool {
    if input.is_empty() {
        regex.matches_exact(input).is_some()
    } else {
        !regex.matches(input, Some(1)).is_empty()
    }
}

#[derive(Clone, Copy)]
enum BoundaryKind {
    Boundary,
    NotBoundary,
    WordStart,
    WordEnd,
}

#[derive(Clone, Copy)]
struct BoundaryAssertion {
    group: usize,
    kind: BoundaryKind,
    normalized_start: usize,
    normalized_end: usize,
}

impl BoundaryAssertion {
    fn matches(self, input: &[u8], base: usize, groups: &[Option<(usize, usize)>]) -> bool {
        let Some(Some((start, end))) = groups.get(self.group) else {
            return true;
        };
        if start != end {
            return false;
        }
        let Some(position) = base.checked_add(*start) else {
            return false;
        };
        let left = position
            .checked_sub(1)
            .and_then(|index| input.get(index))
            .is_some_and(|byte| is_word(*byte));
        let right = input.get(position).is_some_and(|byte| is_word(*byte));
        match self.kind {
            BoundaryKind::Boundary => left != right,
            BoundaryKind::NotBoundary => left == right,
            BoundaryKind::WordStart => !left && right,
            BoundaryKind::WordEnd => left && !right,
        }
    }
}

fn is_word(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'_'
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Previous {
    None,
    Atom,
    Repetition,
}

struct GroupState {
    previous: Previous,
    original_group: Option<usize>,
}

pub(crate) fn normalize_glibc_bre(pattern: &[u8]) -> Result<Vec<u8>, AppError> {
    normalize_glibc_bre_details(pattern).map(|normalized| normalized.bytes)
}

struct NormalizedBre {
    bytes: Vec<u8>,
    boundaries: Vec<BoundaryAssertion>,
    without_boundaries: Option<Vec<u8>>,
}

fn normalize_glibc_bre_details(pattern: &[u8]) -> Result<NormalizedBre, AppError> {
    let mut normalized = Vec::with_capacity(pattern.len());
    let mut boundaries = Vec::new();
    let mut groups = vec![GroupState {
        previous: Previous::None,
        original_group: None,
    }];
    let mut original_groups: Vec<(usize, bool)> = Vec::new();
    let mut normalized_group_count = 0usize;
    let mut index = 0;

    while index < pattern.len() {
        let byte = pattern[index];
        match byte {
            b'[' => {
                let (bracket, end) =
                    normalize_bracket(pattern, index).ok_or_else(|| bad_regex(pattern))?;
                normalized.extend_from_slice(&bracket);
                groups.last_mut().expect("root regex group state").previous = Previous::Atom;
                index = end;
            }
            b'\\' => {
                let Some(escaped) = pattern.get(index + 1).copied() else {
                    return Err(bad_regex(pattern));
                };
                match escaped {
                    b'(' => {
                        normalized_group_count = normalized_group_count
                            .checked_add(1)
                            .ok_or_else(|| bad_regex(pattern))?;
                        original_groups.push((normalized_group_count, false));
                        normalized.extend_from_slice(br"\(");
                        groups.push(GroupState {
                            previous: Previous::None,
                            original_group: Some(original_groups.len() - 1),
                        });
                        index += 2;
                    }
                    b')' => {
                        if groups.len() == 1 {
                            return Err(bad_regex(pattern));
                        }
                        normalized.extend_from_slice(br"\)");
                        let closed = groups.pop().expect("checked regex group depth");
                        if let Some(group) = closed.original_group {
                            original_groups[group].1 = true;
                        }
                        groups.last_mut().expect("root regex group state").previous =
                            Previous::Atom;
                        index += 2;
                    }
                    b'|' => {
                        normalized.extend_from_slice(br"\|");
                        groups.last_mut().expect("root regex group state").previous =
                            Previous::None;
                        index += 2;
                    }
                    b'{' => {
                        if groups.last().expect("root regex group state").previous != Previous::Atom
                        {
                            return Err(bad_regex(pattern));
                        }
                        let (interval, end) =
                            normalize_interval(pattern, index).ok_or_else(|| bad_regex(pattern))?;
                        normalized.extend_from_slice(&interval);
                        groups.last_mut().expect("root regex group state").previous =
                            Previous::Repetition;
                        index = end;
                    }
                    b'+' | b'?' => {
                        normalized.push(b'\\');
                        normalized.push(escaped);
                        let state = groups.last_mut().expect("root regex group state");
                        state.previous = if state.previous == Previous::Atom {
                            Previous::Repetition
                        } else {
                            Previous::Atom
                        };
                        index += 2;
                    }
                    b'0' => {
                        normalized.extend_from_slice(b"[0]");
                        groups.last_mut().expect("root regex group state").previous =
                            Previous::Atom;
                        index += 2;
                    }
                    b'1'..=b'9' => {
                        let original = usize::from(escaped - b'0');
                        let Some(&(mapped, true)) = original_groups.get(original - 1) else {
                            return Err(bad_regex(pattern));
                        };
                        normalized.push(b'\\');
                        normalized.extend_from_slice(mapped.to_string().as_bytes());

                        index += 2;
                        while let Some(digit @ b'0'..=b'9') = pattern.get(index).copied() {
                            normalized.extend_from_slice(&[b'[', digit, b']']);
                            index += 1;
                        }
                        groups.last_mut().expect("root regex group state").previous =
                            Previous::Atom;
                    }
                    // posix-regex gives these ordinary glibc BRE escapes
                    // character-class or control-byte meanings.
                    b'a' | b'd' | b'n' | b'r' | b't' => {
                        normalized.push(escaped);
                        groups.last_mut().expect("root regex group state").previous =
                            Previous::Atom;
                        index += 2;
                    }
                    b'w' => {
                        normalized.extend_from_slice(b"[[:alnum:]_]");
                        groups.last_mut().expect("root regex group state").previous =
                            Previous::Atom;
                        index += 2;
                    }
                    b'W' => {
                        normalized.extend_from_slice(b"[^[:alnum:]_]");
                        groups.last_mut().expect("root regex group state").previous =
                            Previous::Atom;
                        index += 2;
                    }
                    b'b' | b'B' | b'<' | b'>' => {
                        normalized_group_count = normalized_group_count
                            .checked_add(1)
                            .ok_or_else(|| bad_regex(pattern))?;
                        let normalized_start = normalized.len();
                        let kind = match escaped {
                            b'b' => {
                                normalized.extend_from_slice(br"\(\<\|\>\)");
                                BoundaryKind::Boundary
                            }
                            b'B' => {
                                normalized.extend_from_slice(br"\(.\{0\}\)");
                                BoundaryKind::NotBoundary
                            }
                            b'<' => {
                                normalized.extend_from_slice(br"\(\<\)");
                                BoundaryKind::WordStart
                            }
                            b'>' => {
                                normalized.extend_from_slice(br"\(\>\)");
                                BoundaryKind::WordEnd
                            }
                            _ => unreachable!(),
                        };
                        boundaries.push(BoundaryAssertion {
                            group: normalized_group_count,
                            kind,
                            normalized_start,
                            normalized_end: normalized.len(),
                        });
                        groups.last_mut().expect("root regex group state").previous =
                            Previous::Atom;
                        index += 2;
                    }
                    _ => {
                        normalized.push(b'\\');
                        normalized.push(escaped);
                        groups.last_mut().expect("root regex group state").previous =
                            Previous::Atom;
                        index += 2;
                    }
                }
            }
            b'*' => {
                let state = groups.last_mut().expect("root regex group state");
                match state.previous {
                    Previous::None => state.previous = Previous::Atom,
                    Previous::Atom => state.previous = Previous::Repetition,
                    Previous::Repetition => return Err(bad_regex(pattern)),
                }
                normalized.push(byte);
                index += 1;
            }
            b'^' if groups.last().expect("root regex group state").previous != Previous::None => {
                normalized.extend_from_slice(br"\^");
                groups.last_mut().expect("root regex group state").previous = Previous::Atom;
                index += 1;
            }
            b'$' if !is_branch_end(pattern, index + 1) => {
                normalized.extend_from_slice(br"\$");
                groups.last_mut().expect("root regex group state").previous = Previous::Atom;
                index += 1;
            }
            b'^' | b'$' => {
                normalized.push(byte);
                index += 1;
            }
            _ => {
                normalized.push(byte);
                groups.last_mut().expect("root regex group state").previous = Previous::Atom;
                index += 1;
            }
        }
    }

    if groups.len() != 1 {
        return Err(bad_regex(pattern));
    }
    let without_boundaries = if boundaries.is_empty() {
        None
    } else {
        let mut disabled = Vec::with_capacity(normalized.len());
        let mut copied = 0;
        for assertion in &boundaries {
            disabled.extend_from_slice(&normalized[copied..assertion.normalized_start]);
            // This group preserves capture numbering but cannot match.
            disabled.extend_from_slice(br"\(^$.\)");
            copied = assertion.normalized_end;
        }
        disabled.extend_from_slice(&normalized[copied..]);
        Some(disabled)
    };
    Ok(NormalizedBre {
        bytes: normalized,
        boundaries,
        without_boundaries,
    })
}

fn is_branch_end(pattern: &[u8], index: usize) -> bool {
    index == pattern.len()
        || pattern
            .get(index..)
            .is_some_and(|tail| tail.starts_with(br"\)") || tail.starts_with(br"\|"))
}

fn normalize_interval(pattern: &[u8], start: usize) -> Option<(Vec<u8>, usize)> {
    let mut index = start.checked_add(2)?;
    let lower_start = index;
    let lower = parse_bound(pattern, &mut index)?;
    let has_comma = pattern.get(index) == Some(&b',');
    if has_comma {
        index += 1;
    }
    let upper_start = index;
    let upper = if has_comma {
        parse_bound(pattern, &mut index)?
    } else {
        None
    };

    if lower.is_none() && !has_comma {
        return None;
    }
    if !pattern.get(index..)?.starts_with(br"\}") {
        return None;
    }

    let lower_value = lower.unwrap_or(0);
    if lower_value > 0x7fff || upper.is_some_and(|value| value > 0x7fff || lower_value > value) {
        return None;
    }

    let mut interval = Vec::new();
    interval.extend_from_slice(br"\{");
    if lower.is_some() {
        interval.extend_from_slice(
            &pattern[lower_start..if has_comma { upper_start - 1 } else { index }],
        );
    } else {
        interval.push(b'0');
    }
    if has_comma {
        interval.push(b',');
        interval.extend_from_slice(&pattern[upper_start..index]);
    }
    interval.extend_from_slice(br"\}");
    Some((interval, index + 2))
}

fn parse_bound(pattern: &[u8], index: &mut usize) -> Option<Option<u32>> {
    let mut value = None;
    while let Some(digit @ b'0'..=b'9') = pattern.get(*index).copied() {
        value = Some(
            value
                .unwrap_or(0u32)
                .checked_mul(10)?
                .checked_add(u32::from(digit - b'0'))?,
        );
        *index += 1;
    }
    Some(value)
}

fn normalize_bracket(pattern: &[u8], start: usize) -> Option<(Vec<u8>, usize)> {
    let mut normalized = vec![b'['];
    let mut index = start.checked_add(1)?;
    if pattern.get(index) == Some(&b'^') {
        normalized.push(b'^');
        index += 1;
    }
    let mut first = true;

    loop {
        let byte = pattern.get(index).copied()?;
        if byte == b']' && !first {
            normalized.push(b']');
            return Some((normalized, index + 1));
        }

        if byte == b'[' {
            if let Some(end) = bracket_special_end(pattern, index) {
                normalized.extend_from_slice(&pattern[index..end]);
                index = end;
                first = false;
                continue;
            }
        }

        normalized.push(byte);
        index += 1;
        if pattern.get(index) == Some(&b'-')
            && pattern.get(index + 1).is_some()
            && pattern[index + 1] != b']'
        {
            let end = pattern[index + 1];
            if end < byte {
                return None;
            }
            if byte == u8::MAX {
                index += 2;
            } else {
                normalized.extend_from_slice(&[b'-', end]);
                index += 2;
            }
        }
        first = false;
    }
}

fn bracket_special_end(pattern: &[u8], start: usize) -> Option<usize> {
    let marker @ (b'.' | b':' | b'=') = pattern.get(start + 1).copied()? else {
        return None;
    };
    pattern[start + 2..]
        .windows(2)
        .position(|window| window == [marker, b']'])
        .map(|relative| start + relative + 4)
}

fn bad_regex(pattern: &[u8]) -> AppError {
    let mut message = pattern.to_vec();
    message.extend_from_slice(b": bad regular expression");
    AppError::Message(message)
}

#[cfg(test)]
mod tests {
    mod expression_parser {
        use super::super::*;

        fn assert_message(result: Result<ParsedExpression<'_>, AppError>, expected: &[u8]) {
            match result {
                Err(AppError::Message(message)) => assert_eq!(message, expected),
                other => panic!("unexpected parse result: {other:?}"),
            }
        }

        #[test]
        fn uses_last_delimiter() {
            assert_eq!(
                parse_expression(br"/part/with/slashes/+2").expect("valid slash expression"),
                ParsedExpression {
                    delimiter: b'/',
                    pattern: b"part/with/slashes",
                    offset: 2,
                }
            );
            assert_eq!(
                parse_expression(br"%left%right%-3").expect("valid percent expression"),
                ParsedExpression {
                    delimiter: b'%',
                    pattern: b"left%right",
                    offset: -3,
                }
            );
        }

        #[test]
        fn escaped_final_delimiter_is_missing() {
            assert_message(
                parse_expression(br"/part\/"),
                br"/part\/: missing trailing /",
            );
            assert_message(
                parse_expression(br"%part\%"),
                br"%part\%: missing trailing %",
            );
        }

        #[test]
        fn opening_delimiter_only_uses_safe_line_quirk() {
            assert_message(parse_expression(b"/Line"), b"Line: bad offset");
            assert_eq!(
                parse_expression(b"/").expect("opening delimiter alone is an empty expression"),
                ParsedExpression {
                    delimiter: b'/',
                    pattern: b"",
                    offset: 0,
                }
            );
        }

        #[test]
        fn accepts_all_signed_offsets() {
            for (expression, expected) in [
                (b"/body/".as_slice(), 0),
                (b"/body/+0".as_slice(), 0),
                (b"/body/-0".as_slice(), 0),
                (b"/body/+27".as_slice(), 27),
                (b"/body/-27".as_slice(), -27),
                (b"/body/ \t+3".as_slice(), 3),
                (b"/body/9223372036854775807".as_slice(), i64::MAX),
                (b"/body/-9223372036854775808".as_slice(), i64::MIN),
            ] {
                assert_eq!(
                    parse_expression(expression)
                        .unwrap_or_else(|error| panic!("failed to parse {expression:?}: {error:?}"))
                        .offset,
                    expected
                );
            }
        }

        #[test]
        fn rejects_invalid_offset_suffix() {
            for (expression, expected) in [
                (b"/body/+".as_slice(), b"+: bad offset".as_slice()),
                (b"/body/ \t".as_slice(), b" \t: bad offset".as_slice()),
                (b"/body/2junk".as_slice(), b"2junk: bad offset".as_slice()),
                (
                    b"/body/9223372036854775808".as_slice(),
                    b"9223372036854775808: bad offset".as_slice(),
                ),
                (
                    b"/body/-9223372036854775809".as_slice(),
                    b"-9223372036854775809: bad offset".as_slice(),
                ),
            ] {
                assert_message(parse_expression(expression), expected);
            }
        }
    }

    mod core_bre {
        use super::super::*;

        fn matcher(pattern: &[u8]) -> Box<dyn RegexMatcher> {
            GlibcBreCompiler
                .compile(pattern)
                .expect("pattern should compile")
        }

        #[test]
        fn searches_byte_chunks_as_basic_regular_expressions() {
            assert!(matcher(b"a.c").is_match(&[0xff, b'a', b'x', b'c', 0xfe]));
            assert!(matcher(b"[[:digit:]]").is_match(b"value 7\n"));
            assert!(matcher(b"has space").is_match(b"prefix has space suffix\n"));
            assert!(!matcher(b"a.c").is_match(b"ac\n"));
        }

        #[test]
        fn compile_failures_use_body_diagnostic() {
            match GlibcBreCompiler.compile(b"[") {
                Err(AppError::Message(message)) => {
                    assert_eq!(message, b"[: bad regular expression")
                }
                _ => panic!("malformed bracket expression unexpectedly compiled"),
            }
        }
    }

    mod dialect {
        use super::super::*;

        fn matcher(pattern: &[u8]) -> Box<dyn RegexMatcher> {
            GlibcBreCompiler
                .compile(pattern)
                .unwrap_or_else(|error| panic!("failed to compile {pattern:?}: {error:?}"))
        }

        fn assert_bad(pattern: &[u8]) {
            match GlibcBreCompiler.compile(pattern) {
                Err(AppError::Message(message)) => {
                    let mut expected = pattern.to_vec();
                    expected.extend_from_slice(b": bad regular expression");
                    assert_eq!(message, expected);
                }
                _ => panic!("malformed pattern {pattern:?} unexpectedly compiled"),
            }
        }

        #[test]
        fn dot_and_brackets() {
            let dot = matcher(b"a.c");
            assert!(dot.is_match(b"prefix a\nc suffix"));
            assert!(dot.is_match(&[0xff, b'a', b'x', b'c', 0xfe]));
            assert!(!dot.is_match(b"ac"));

            let classes = matcher(b"[[:digit:]][^x]");
            assert!(classes.is_match(b"value 7\n"));
            assert!(!classes.is_match(b"7x"));
            assert!(matcher(br"\[1\]").is_match(b"line [1]"));
            assert!(matcher(b"[]]").is_match(b"]"));
            assert!(matcher(b"[\xff-\xff]").is_match(&[0xff]));
        }

        #[test]
        fn bare_plus_is_literal_and_escaped_plus_repeats() {
            assert!(matcher(b"a+").is_match(b"value a+"));
            assert!(!matcher(b"a+").is_match(b"aaa"));
            assert!(matcher(br"a\+").is_match(b"aaa"));

            assert!(matcher(b"a?").is_match(b"a?"));
            assert!(!matcher(b"a?").is_match(b"a"));
            assert!(matcher(br"a\?b").is_match(b"b"));
            assert!(matcher(b"(a){2}").is_match(b"(a){2}"));
            assert!(matcher(br"\(ab\)\{2\}").is_match(b"abab"));
            assert!(matcher(br"a\{,\}").is_match(b"anything"));
            assert!(matcher(br"a\{,2\}b").is_match(b"aab"));
        }

        #[test]
        fn escaped_alternation() {
            let alternation = matcher(br"apple\|cherry");
            assert!(alternation.is_match(b"apple"));
            assert!(alternation.is_match(b"cherry"));
            assert!(!alternation.is_match(b"banana"));

            let bare = matcher(b"apple|cherry");
            assert!(bare.is_match(b"apple|cherry"));
            assert!(!bare.is_match(b"apple"));
        }

        #[test]
        fn anchors_do_not_special_case_newline() {
            let anchored = matcher(b"^test$");
            assert!(anchored.is_match(b"test"));
            assert!(!anchored.is_match(b"test\n"));
            assert!(!anchored.is_match(b"prefix\ntest"));
            assert!(matcher(b".").is_match(b"\n"));
            assert!(matcher(b"[^x]").is_match(b"\n"));

            assert!(matcher(b"a^b").is_match(b"a^b"));
            assert!(matcher(b"a$b").is_match(b"a$b"));
            assert!(!matcher(b"after").is_match(b"before\0after"));
        }

        #[test]
        fn backreferences() {
            let repeated = matcher(br"\([ab]\)\1");
            assert!(repeated.is_match(b"aa"));
            assert!(repeated.is_match(b"bb"));
            assert!(!repeated.is_match(b"ab"));

            assert!(matcher(br"\b\(word\)\1\b").is_match(b"wordword"));
            assert!(matcher(br"\(a\)\10").is_match(b"aa0"));
            assert!(matcher(br"\0").is_match(b"0"));
            assert_bad(br"\1");
            assert_bad(br"\(a\)\2");
        }

        #[test]
        fn empty_regex() {
            let empty = matcher(b"");
            assert!(empty.is_match(b""));
            assert!(empty.is_match(b"anything\n"));
        }

        #[test]
        fn escaped_n_matches_literal_n() {
            assert!(matcher(br"\n").is_match(b"line"));
            assert!(!matcher(br"\n").is_match(b"\n"));
            assert!(matcher(br"\a\d\r\t").is_match(b"adrt"));
            assert!(!matcher(br"\a\d\r\t").is_match(b"\x07\x07\r\t"));
            assert!(matcher(br"\s").is_match(b" "));
            assert!(matcher(br"\S").is_match(b"x"));
            assert!(!matcher(br"\S").is_match(b"\n"));
        }

        #[test]
        fn gnu_word_classes_and_boundaries() {
            let words = matcher(br"\w\+");
            assert!(words.is_match(b"_word42"));
            assert!(!words.is_match(b"---"));
            assert!(matcher(br"\W").is_match(b"-"));
            assert!(!matcher(br"\W").is_match(b"_"));

            let bounded = matcher(br"\bword\b");
            assert!(bounded.is_match(b"a word!"));
            assert!(!bounded.is_match(b"sword"));
            assert!(!bounded.is_match(b"words"));
            assert!(matcher(br"\<word\>").is_match(b"a word!"));

            assert!(matcher(br"\b").is_match(b"a"));
            assert!(!matcher(br"\b").is_match(b" "));
            assert!(!matcher(br"\b").is_match(b""));
            assert!(matcher(br"\B").is_match(b""));
            assert!(matcher(br"\B").is_match(b" "));
            assert!(!matcher(br"\<").is_match(b" "));
            assert!(matcher(br"\<").is_match(b"word"));
            assert!(!matcher(br"\>").is_match(b" "));
            assert!(matcher(br"\>").is_match(b"word"));
            assert!(matcher(br"\bword\|word").is_match(b"sword"));
            assert!(matcher(br"word\|\bword").is_match(b"sword"));
        }

        #[test]
        fn malformed_constructs_fail() {
            for pattern in [
                b"[".as_slice(),
                b"[]".as_slice(),
                b"[z-a]".as_slice(),
                br"a\{2,1\}".as_slice(),
                br"a\{".as_slice(),
                br"\{2\}".as_slice(),
                br"\(".as_slice(),
                br"\)".as_slice(),
                br"\(a".as_slice(),
                b"a**".as_slice(),
                br"a\{32768\}".as_slice(),
                b"\\".as_slice(),
            ] {
                assert_bad(pattern);
            }
        }

        #[test]
        fn compile_failures_use_generic_diagnostic() {
            assert_bad(b"[[:unknown:]]");
            assert_bad(br"\(body\)\2");
            assert_bad(b"[z-a]");
        }
    }

    mod repair_contract {
        use super::super::*;

        fn matcher(pattern: &[u8]) -> Box<dyn RegexMatcher> {
            GlibcBreCompiler
                .compile(pattern)
                .expect("pattern should compile")
        }

        #[test]
        fn parses_offsets_and_opening_delimiter_quirk() {
            assert_eq!(
                parse_expression(br"/Line 2/1").expect("valid expression"),
                ParsedExpression {
                    delimiter: b'/',
                    pattern: b"Line 2",
                    offset: 1,
                }
            );

            match parse_expression(b"/Line") {
                Err(AppError::Message(message)) => assert_eq!(message, b"Line: bad offset"),
                other => panic!("unexpected parse result: {other:?}"),
            }
        }

        #[test]
        fn matches_released_bre_forms() {
            assert!(matcher(b"a.c").is_match(b"axc\n"));
            assert!(matcher(b"has space").is_match(b"has space\n"));
            assert!(matcher(br"apple\|cherry").is_match(b"cherry\n"));
            assert!(matcher(br"\[1\]").is_match(b"line [1]\n"));
        }

        #[test]
        fn preserves_bare_plus_and_no_newline_anchor_mode() {
            assert!(!matcher(b"a+").is_match(b"aaa\n"));
            assert!(matcher(br"a\+").is_match(b"aaa\n"));
            assert!(!matcher(b"^test$").is_match(b"test\n"));
            assert!(matcher(b"^test$").is_match(b"test"));
        }

        #[test]
        fn ordinary_glibc_escapes_remain_literals() {
            assert!(matcher(br"\n").is_match(b"line"));
            assert!(!matcher(br"\n").is_match(b"\n"));
        }
    }
}
