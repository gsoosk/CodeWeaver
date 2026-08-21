use super::{Bre, Matcher};

fn matches(pattern: &[u8], input: &[u8]) -> bool {
    Bre::compile(pattern).unwrap().is_match(input).unwrap()
}

#[test]
fn dot_matches_newline() {
    assert!(matches(b".", b"\n"));
}

#[test]
fn unescaped_plus_is_literal() {
    assert!(matches(b"a+", b"a+"));
    assert!(!matches(b"a+", b"aaa"));
}

#[test]
fn other_unescaped_extended_operators_are_literal() {
    assert!(matches(b"a?", b"a?"));
    assert!(!matches(b"a?", b"a"));
    assert!(matches(b"a|b", b"a|b"));
    assert!(!matches(b"a|b", b"a"));
    assert!(matches(b"(ab)", b"(ab)"));
    assert!(!matches(b"(ab)", b"ab"));
}

#[test]
fn escaped_plus_is_operator() {
    assert!(matches(b"a\\+", b"aaa"));
}

#[test]
fn escaped_question_is_operator() {
    assert!(matches(b"ab\\?", b"a"));
    assert!(matches(b"ab\\?", b"ab"));
}

#[test]
fn escaped_alternation() {
    assert!(matches(b"apple\\|cherry", b"cherry\n"));
}

#[test]
fn groups_and_backreferences() {
    assert!(matches(b"\\(ab\\)\\1", b"abab"));
    assert!(!matches(b"\\(ab\\)\\1", b"abac"));
}

#[test]
fn posix_bracket_classes() {
    assert!(matches(b"[[:digit:]]\\+", b"123"));
    assert!(!matches(b"^[[:digit:]]\\+$", b"12x"));
    assert!(matches(b"[^x]", b"\n"));
    assert!(matches(b"[[:digit:]\\(^]", b"^"));
}

#[test]
fn escaped_delimiters() {
    assert!(matches(b"\\/", b"/"));
}

#[test]
fn gnu_whitespace_classes() {
    assert!(matches(b"\\s", b"\t"));
    assert!(matches(b"\\S", b"x"));
}

#[test]
fn gnu_word_classes() {
    assert!(matches(b"\\w\\+", b"word_1"));
    assert!(matches(b"\\W", b"!"));
}

#[test]
fn gnu_word_boundaries() {
    assert!(matches(b"\\<word\\>", b"a word!"));
    assert!(!matches(b"\\<word\\>", b"swordfish"));
    assert!(matches(b"\\bword\\b", b"a word!"));
    assert!(!matches(b"\\bword\\b", b"swordfish"));
    assert!(matches(b"\\Boo\\B", b"book"));
}

#[test]
fn escaped_n_is_literal_n() {
    assert!(matches(b"\\n", b"n"));
    assert!(!matches(b"\\n", b"\n"));
}

#[test]
fn escaped_t_is_literal_t() {
    assert!(matches(b"\\t", b"t"));
    assert!(!matches(b"\\t", b"\t"));
}

#[test]
fn escaped_a_is_literal_a() {
    assert!(matches(b"\\a", b"a"));
}

#[test]
fn escaped_d_is_literal_d() {
    assert!(matches(b"\\d", b"d"));
    assert!(!matches(b"\\d", b"7"));
}

#[test]
fn non_gnu_buffer_escapes_are_literal() {
    for (pattern, literal) in [
        (b"\\A".as_slice(), b"A".as_slice()),
        (b"\\Z".as_slice(), b"Z".as_slice()),
        (b"\\z".as_slice(), b"z".as_slice()),
    ] {
        assert!(matches(pattern, literal));
        assert!(!matches(pattern, b"x"));
    }
    assert!(matches(b"\\`word\\'", b"word"));
    assert!(!matches(b"\\`word\\'", b"xword"));
}

#[test]
fn strict_start_anchor() {
    assert!(matches(b"^test", b"test\n"));
    assert!(!matches(b"^test", b"x test"));
    assert!(matches(b"a^b", b"a^b"));
    assert!(matches(b"\\(^a\\|^b\\)", b"b"));
    assert!(!matches(b"\\(^a\\|^b\\)", b"xb"));
    assert!(matches(b"\\\\(^", b"\\(^"));
    assert!(matches(b"\\\\|^", b"\\|^"));
}

#[test]
fn strict_end_anchor_with_retained_lf() {
    assert!(matches(b"^test$", b"test"));
    assert!(!matches(b"^test$", b"test\n"));
    assert!(matches(b"a$b", b"a$b"));
    assert!(matches(b"\\(a$\\|b$\\)", b"b"));
    assert!(!matches(b"\\(a$\\|b$\\)", b"b\n"));
}

#[test]
fn invalid_patterns() {
    assert!(Bre::compile(b"\\(").is_err());
    assert!(Bre::compile(b"[").is_err());
    assert!(Bre::compile(b"[z-a]").is_err());
    assert!(Bre::compile(b"a\\{2,1\\}").is_err());
}
