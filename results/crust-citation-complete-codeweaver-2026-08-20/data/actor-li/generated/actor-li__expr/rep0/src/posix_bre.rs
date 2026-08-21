use posix_regex::compile::Error as PosixCompileError;
use posix_regex::PosixRegexBuilder;
use std::collections::HashSet;

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub struct Span {
    pub start: usize,
    pub end: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegexOutcome {
    pub capture_count: usize,
    pub whole_match: Option<Span>,
    pub first_capture: Option<Span>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegexCompileError {
    pub message: Vec<u8>,
}

pub trait RegexEngine {
    fn execute(&self, input: &[u8], pattern: &[u8]) -> Result<RegexOutcome, RegexCompileError>;
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum BreErrorKind {
    InvalidRegularExpression,
    TrailingBackslash,
    InvalidRangeEnd,
    InvalidCharacterClassName,
    InvalidBackReference,
    UnmatchedParenthesis,
    UnmatchedBracket,
    InvalidCollationCharacter,
    InvalidPrecedingRegularExpression,
    InvalidRepetitionContent,
    UnmatchedRepetition,
    RegularExpressionTooBig,
}

#[cfg_attr(not(test), allow(dead_code))]
pub(crate) fn validate_pattern(pattern: &[u8]) -> Result<(), BreErrorKind> {
    let prepared = prepare_pattern(pattern)?;
    compile_normalized(pattern, &prepared.normalized)
}

#[cfg_attr(not(test), allow(dead_code))]
pub(crate) fn normalize_pattern(pattern: &[u8]) -> Result<Vec<u8>, BreErrorKind> {
    let prepared = prepare_pattern(pattern)?;
    compile_normalized(pattern, &prepared.normalized)?;
    Ok(prepared.normalized)
}

pub(crate) fn compile_error_message(kind: BreErrorKind) -> Vec<u8> {
    match kind {
        BreErrorKind::InvalidRegularExpression => b"Invalid regular expression".to_vec(),
        BreErrorKind::TrailingBackslash => b"Trailing backslash".to_vec(),
        BreErrorKind::InvalidRangeEnd => b"Invalid range end".to_vec(),
        BreErrorKind::InvalidCharacterClassName => b"Invalid character class name".to_vec(),
        BreErrorKind::InvalidBackReference => b"Invalid back reference".to_vec(),
        BreErrorKind::UnmatchedParenthesis => b"Unmatched ( or \\(".to_vec(),
        BreErrorKind::UnmatchedBracket => b"Unmatched [, [^, [:, [., or [=".to_vec(),
        BreErrorKind::InvalidCollationCharacter => b"Invalid collation character".to_vec(),
        BreErrorKind::InvalidPrecedingRegularExpression => {
            b"Invalid preceding regular expression".to_vec()
        }
        BreErrorKind::InvalidRepetitionContent => b"Invalid content of \\{\\}".to_vec(),
        BreErrorKind::UnmatchedRepetition => b"Unmatched \\{".to_vec(),
        BreErrorKind::RegularExpressionTooBig => b"Regular expression too big".to_vec(),
    }
}

fn compile_normalized(original: &[u8], normalized: &[u8]) -> Result<(), BreErrorKind> {
    if normalized.is_empty() {
        return Ok(());
    }
    PosixRegexBuilder::new(normalized)
        .with_default_classes()
        .extended(false)
        .compile()
        .map(|_| ())
        .map_err(|error| classify_compile_error(original, &error))
}

fn classify_compile_error(pattern: &[u8], error: &PosixCompileError) -> BreErrorKind {
    if pattern
        .iter()
        .rev()
        .take_while(|byte| **byte == b'\\')
        .count()
        % 2
        == 1
    {
        return BreErrorKind::TrailingBackslash;
    }

    match error {
        PosixCompileError::IllegalRange => BreErrorKind::InvalidRangeEnd,
        PosixCompileError::UnknownClass(_) => BreErrorKind::InvalidCharacterClassName,
        PosixCompileError::InvalidBackRef(_) => BreErrorKind::InvalidBackReference,
        PosixCompileError::LeadingRepetition => BreErrorKind::InvalidPrecedingRegularExpression,
        PosixCompileError::EmptyRepetition => BreErrorKind::InvalidRepetitionContent,
        PosixCompileError::UnclosedRepetition => BreErrorKind::UnmatchedRepetition,
        PosixCompileError::IntegerOverflow => BreErrorKind::RegularExpressionTooBig,
        _ => BreErrorKind::InvalidRegularExpression,
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Repetition {
    min: u32,
    max: Option<u32>,
}

impl Repetition {
    const ONCE: Self = Self {
        min: 1,
        max: Some(1),
    };
    const ZERO_OR_MORE: Self = Self { min: 0, max: None };
    const ONE_OR_MORE: Self = Self { min: 1, max: None };
    const OPTIONAL: Self = Self {
        min: 0,
        max: Some(1),
    };
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Expression {
    alternatives: Vec<Sequence>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Sequence {
    pieces: Vec<Piece>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Piece {
    atom: Atom,
    repetition: Repetition,
}

impl Piece {
    fn once(atom: Atom) -> Self {
        Self {
            atom,
            repetition: Repetition::ONCE,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum Atom {
    Literal(u8),
    Any,
    Bracket(BracketExpression),
    Group {
        id: usize,
        expression: Box<Expression>,
    },
    BackReference(usize),
    NestedRepetition(Box<Piece>),
    Assertion(Assertion),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Assertion {
    Start,
    End,
    WordStart,
    WordEnd,
    WordBoundary,
    NotWordBoundary,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct BracketExpression {
    raw: Vec<u8>,
    inverted: bool,
    items: Vec<BracketItem>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum BracketItem {
    Byte(u8),
    Range(u8, u8),
    Class(CharacterClass),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum CharacterClass {
    Alnum,
    Alpha,
    Blank,
    Cntrl,
    Digit,
    Graph,
    Lower,
    Print,
    Punct,
    Space,
    Upper,
    Xdigit,
    Word,
}

impl CharacterClass {
    fn from_name(name: &[u8]) -> Option<Self> {
        match name {
            b"alnum" => Some(Self::Alnum),
            b"alpha" => Some(Self::Alpha),
            b"blank" => Some(Self::Blank),
            b"cntrl" => Some(Self::Cntrl),
            b"digit" => Some(Self::Digit),
            b"graph" => Some(Self::Graph),
            b"lower" => Some(Self::Lower),
            b"print" => Some(Self::Print),
            b"punct" => Some(Self::Punct),
            b"space" => Some(Self::Space),
            b"upper" => Some(Self::Upper),
            b"xdigit" => Some(Self::Xdigit),
            _ => None,
        }
    }

    fn matches(self, byte: u8) -> bool {
        match self {
            Self::Alnum => byte.is_ascii_alphanumeric(),
            Self::Alpha => byte.is_ascii_alphabetic(),
            Self::Blank => matches!(byte, b' ' | b'\t'),
            Self::Cntrl => byte.is_ascii_control(),
            Self::Digit => byte.is_ascii_digit(),
            Self::Graph => byte.is_ascii_graphic(),
            Self::Lower => byte.is_ascii_lowercase(),
            Self::Print => byte.is_ascii_graphic() || byte == b' ',
            Self::Punct => byte.is_ascii_punctuation(),
            Self::Space => byte.is_ascii_whitespace(),
            Self::Upper => byte.is_ascii_uppercase(),
            Self::Xdigit => byte.is_ascii_hexdigit(),
            Self::Word => is_word_byte(byte),
        }
    }
}

impl BracketExpression {
    fn extension(raw: &[u8], inverted: bool, class: CharacterClass) -> Self {
        Self {
            raw: raw.to_vec(),
            inverted,
            items: vec![BracketItem::Class(class)],
        }
    }

    fn matches(&self, byte: u8) -> bool {
        self.contains(byte) != self.inverted
    }

    fn contains(&self, byte: u8) -> bool {
        self.items.iter().any(|item| match *item {
            BracketItem::Byte(expected) => byte == expected,
            BracketItem::Range(start, end) => (start..=end).contains(&byte),
            BracketItem::Class(class) => class.matches(byte),
        })
    }
}

#[derive(Clone, Debug)]
struct ParsedPattern {
    expression: Expression,
    capture_count: usize,
}

#[derive(Clone, Debug)]
struct PreparedPattern {
    parsed: ParsedPattern,
    normalized: Vec<u8>,
}

fn prepare_pattern(pattern: &[u8]) -> Result<PreparedPattern, BreErrorKind> {
    let parsed = BreParser::new(pattern).parse()?;
    let rendered = PatternRenderer::new(parsed.capture_count).render(&parsed.expression);
    Ok(PreparedPattern {
        parsed,
        normalized: rendered.bytes,
    })
}

struct BreParser<'a> {
    input: &'a [u8],
    position: usize,
    capture_count: usize,
    closed_groups: Vec<bool>,
}

impl<'a> BreParser<'a> {
    fn new(input: &'a [u8]) -> Self {
        Self {
            input,
            position: 0,
            capture_count: 0,
            closed_groups: vec![true],
        }
    }

    fn parse(mut self) -> Result<ParsedPattern, BreErrorKind> {
        let expression = self.parse_expression(false)?;
        if self.position != self.input.len() {
            return Err(BreErrorKind::UnmatchedParenthesis);
        }
        Ok(ParsedPattern {
            expression,
            capture_count: self.capture_count,
        })
    }

    fn parse_expression(&mut self, in_group: bool) -> Result<Expression, BreErrorKind> {
        let mut alternatives = Vec::new();
        loop {
            alternatives.push(self.parse_sequence(in_group)?);
            if self.starts_with(br"\|") {
                self.position += 2;
            } else {
                break;
            }
        }
        Ok(Expression { alternatives })
    }

    fn parse_sequence(&mut self, in_group: bool) -> Result<Sequence, BreErrorKind> {
        let mut pieces = Vec::new();
        while self.position < self.input.len()
            && !self.starts_with(br"\|")
            && !self.starts_with(br"\)")
        {
            let atom = self.parse_atom(pieces.is_empty(), in_group)?;
            pieces.push(self.parse_repetitions(Piece::once(atom))?);
        }
        Ok(Sequence { pieces })
    }

    fn parse_atom(&mut self, at_branch_start: bool, in_group: bool) -> Result<Atom, BreErrorKind> {
        let byte = self.input[self.position];
        self.position += 1;
        match byte {
            b'^' if at_branch_start => Ok(Atom::Assertion(Assertion::Start)),
            b'$' if self.at_branch_end(in_group) => Ok(Atom::Assertion(Assertion::End)),
            b'.' => Ok(Atom::Any),
            b'[' => self.parse_bracket(),
            b'\\' => self.parse_escape(),
            byte => Ok(Atom::Literal(byte)),
        }
    }

    fn parse_escape(&mut self) -> Result<Atom, BreErrorKind> {
        let Some(&escaped) = self.input.get(self.position) else {
            return Err(BreErrorKind::TrailingBackslash);
        };
        self.position += 1;
        match escaped {
            b'(' => {
                self.capture_count += 1;
                let id = self.capture_count;
                self.closed_groups.push(false);
                let expression = self.parse_expression(true)?;
                if !self.starts_with(br"\)") {
                    return Err(BreErrorKind::UnmatchedParenthesis);
                }
                self.position += 2;
                self.closed_groups[id] = true;
                Ok(Atom::Group {
                    id,
                    expression: Box::new(expression),
                })
            }
            b')' => Err(BreErrorKind::UnmatchedParenthesis),
            b'|' => unreachable!("alternation is consumed by parse_expression"),
            b'1'..=b'9' => {
                let id = usize::from(escaped - b'0');
                if !self.closed_groups.get(id).copied().unwrap_or(false) {
                    return Err(BreErrorKind::InvalidBackReference);
                }
                Ok(Atom::BackReference(id))
            }
            b'0' => Ok(Atom::Literal(b'0')),
            b'+' | b'?' => Ok(Atom::Literal(escaped)),
            b'{' => Err(BreErrorKind::InvalidPrecedingRegularExpression),
            b'<' => Ok(Atom::Assertion(Assertion::WordStart)),
            b'>' => Ok(Atom::Assertion(Assertion::WordEnd)),
            b'b' => Ok(Atom::Assertion(Assertion::WordBoundary)),
            b'B' => Ok(Atom::Assertion(Assertion::NotWordBoundary)),
            b'`' => Ok(Atom::Assertion(Assertion::Start)),
            b'\'' => Ok(Atom::Assertion(Assertion::End)),
            b'w' => Ok(Atom::Bracket(BracketExpression::extension(
                b"[[:alnum:]_]",
                false,
                CharacterClass::Word,
            ))),
            b'W' => Ok(Atom::Bracket(BracketExpression::extension(
                b"[^[:alnum:]_]",
                true,
                CharacterClass::Word,
            ))),
            b's' => Ok(Atom::Bracket(BracketExpression::extension(
                b"[[:space:]]",
                false,
                CharacterClass::Space,
            ))),
            b'S' => Ok(Atom::Bracket(BracketExpression::extension(
                b"[^[:space:]]",
                true,
                CharacterClass::Space,
            ))),
            escaped => Ok(Atom::Literal(escaped)),
        }
    }

    fn parse_repetitions(&mut self, mut piece: Piece) -> Result<Piece, BreErrorKind> {
        if matches!(piece.atom, Atom::Assertion(_)) {
            return Ok(piece);
        }
        let mut has_repetition = false;
        loop {
            let repetition = if self.input.get(self.position) == Some(&b'*') {
                if has_repetition {
                    return Err(BreErrorKind::InvalidPrecedingRegularExpression);
                }
                self.position += 1;
                Some(Repetition::ZERO_OR_MORE)
            } else if self.starts_with(br"\+") {
                self.position += 2;
                Some(Repetition::ONE_OR_MORE)
            } else if self.starts_with(br"\?") {
                self.position += 2;
                Some(Repetition::OPTIONAL)
            } else if self.starts_with(br"\{") {
                if has_repetition {
                    return Err(BreErrorKind::InvalidPrecedingRegularExpression);
                }
                Some(self.parse_interval()?)
            } else {
                None
            };

            let Some(repetition) = repetition else {
                break;
            };
            if has_repetition {
                piece = Piece {
                    atom: Atom::NestedRepetition(Box::new(piece)),
                    repetition,
                };
            } else {
                piece.repetition = repetition;
                has_repetition = true;
            }
        }
        Ok(piece)
    }

    fn parse_interval(&mut self) -> Result<Repetition, BreErrorKind> {
        self.position += 2;
        let content_start = self.position;
        let Some(relative_end) = self.input[self.position..]
            .windows(2)
            .position(|window| window == br"\}")
        else {
            return Err(BreErrorKind::UnmatchedRepetition);
        };
        let content_end = self.position + relative_end;
        let content = &self.input[content_start..content_end];
        self.position = content_end + 2;

        let mut comma = None;
        for (index, &byte) in content.iter().enumerate() {
            if byte == b',' {
                if comma.replace(index).is_some() {
                    return Err(BreErrorKind::InvalidRepetitionContent);
                }
            } else if !byte.is_ascii_digit() {
                return Err(BreErrorKind::InvalidRepetitionContent);
            }
        }

        let (minimum, maximum) = if let Some(comma) = comma {
            let minimum = self.parse_bound(&content[..comma])?.unwrap_or(0);
            let maximum = self.parse_bound(&content[comma + 1..])?;
            (minimum, maximum)
        } else {
            let Some(bound) = self.parse_bound(content)? else {
                return Err(BreErrorKind::InvalidRepetitionContent);
            };
            (bound, Some(bound))
        };
        if maximum.map(|maximum| minimum > maximum).unwrap_or(false) {
            return Err(BreErrorKind::InvalidRepetitionContent);
        }
        Ok(Repetition {
            min: minimum,
            max: maximum,
        })
    }

    fn parse_bound(&self, bytes: &[u8]) -> Result<Option<u32>, BreErrorKind> {
        if bytes.is_empty() {
            return Ok(None);
        }
        let mut value = 0_u32;
        for &byte in bytes {
            value = value
                .checked_mul(10)
                .and_then(|value| value.checked_add(u32::from(byte - b'0')))
                .ok_or(BreErrorKind::RegularExpressionTooBig)?;
            if value > 32_767 {
                return Err(BreErrorKind::RegularExpressionTooBig);
            }
        }
        Ok(Some(value))
    }

    fn parse_bracket(&mut self) -> Result<Atom, BreErrorKind> {
        let start = self.position - 1;
        let inverted = self.input.get(self.position) == Some(&b'^');
        if inverted {
            self.position += 1;
        }
        let mut items = Vec::new();
        let mut first = true;
        let mut parsed_range = false;
        let mut normalize_for_dependency = false;

        loop {
            let Some(&byte) = self.input.get(self.position) else {
                return Err(if first {
                    BreErrorKind::InvalidRegularExpression
                } else {
                    BreErrorKind::UnmatchedBracket
                });
            };
            if byte == b']' && !first {
                self.position += 1;
                break;
            }

            let item = self.parse_bracket_item()?;
            normalize_for_dependency |= matches!(item, BracketItem::Byte(b'['));
            first = false;
            if self.input.get(self.position) == Some(&b'-')
                && self.input.get(self.position + 1).is_some()
                && self.input.get(self.position + 1) != Some(&b']')
            {
                self.position += 1;
                let destination = self.parse_bracket_item()?;
                let (BracketItem::Byte(range_start), BracketItem::Byte(range_end)) =
                    (item, destination)
                else {
                    return Err(BreErrorKind::InvalidRangeEnd);
                };
                if range_start > range_end {
                    return Err(BreErrorKind::InvalidRangeEnd);
                }
                if range_start == u8::MAX {
                    normalize_for_dependency = true;
                }
                items.push(BracketItem::Range(range_start, range_end));
                parsed_range = true;
            } else {
                if parsed_range
                    && matches!(item, BracketItem::Byte(b'-'))
                    && self.input.get(self.position) != Some(&b']')
                {
                    return Err(BreErrorKind::InvalidRangeEnd);
                }
                items.push(item);
                parsed_range = false;
            }
        }

        let raw = if normalize_for_dependency {
            canonical_bracket_pattern(inverted, &items)
        } else {
            self.input[start..self.position].to_vec()
        };
        Ok(Atom::Bracket(BracketExpression {
            raw,
            inverted,
            items,
        }))
    }

    fn parse_bracket_item(&mut self) -> Result<BracketItem, BreErrorKind> {
        let byte = self.input[self.position];
        self.position += 1;
        if byte != b'[' {
            return Ok(BracketItem::Byte(byte));
        }
        let Some(&kind @ (b':' | b'.' | b'=')) = self.input.get(self.position) else {
            return Ok(BracketItem::Byte(b'['));
        };
        self.position += 1;
        let content_start = self.position;
        let Some(relative_end) = self.input[self.position..]
            .windows(2)
            .position(|window| window == [kind, b']'])
        else {
            return Err(BreErrorKind::UnmatchedBracket);
        };
        let content_end = self.position + relative_end;
        let content = &self.input[content_start..content_end];
        self.position = content_end + 2;
        match kind {
            b':' => CharacterClass::from_name(content)
                .map(BracketItem::Class)
                .ok_or(BreErrorKind::InvalidCharacterClassName),
            b'.' | b'=' if content.len() == 1 => Ok(BracketItem::Byte(content[0])),
            b'.' | b'=' => Err(BreErrorKind::InvalidCollationCharacter),
            _ => unreachable!(),
        }
    }

    fn at_branch_end(&self, in_group: bool) -> bool {
        self.position == self.input.len()
            || self.starts_with(br"\|")
            || (in_group && self.starts_with(br"\)"))
    }

    fn starts_with(&self, bytes: &[u8]) -> bool {
        self.input[self.position..].starts_with(bytes)
    }
}

fn canonical_bracket_pattern(inverted: bool, items: &[BracketItem]) -> Vec<u8> {
    let expression = BracketExpression {
        raw: Vec::new(),
        inverted,
        items: items.to_vec(),
    };
    let mut pattern = vec![b'['];
    if inverted {
        pattern.push(b'^');
    }
    for value in 0_u16..=u16::from(u8::MAX) {
        let byte = value as u8;
        if expression.contains(byte) {
            pattern.extend_from_slice(b"[.");
            pattern.push(byte);
            pattern.extend_from_slice(b".]");
        }
    }
    pattern.push(b']');
    pattern
}

struct RenderedPattern {
    bytes: Vec<u8>,
}

struct PatternRenderer {
    bytes: Vec<u8>,
    next_group: usize,
    original_groups: Vec<Option<usize>>,
}

impl PatternRenderer {
    fn new(capture_count: usize) -> Self {
        Self {
            bytes: Vec::new(),
            next_group: 1,
            original_groups: vec![None; capture_count + 1],
        }
    }

    fn render(mut self, expression: &Expression) -> RenderedPattern {
        self.render_expression(expression);
        RenderedPattern { bytes: self.bytes }
    }

    fn render_expression(&mut self, expression: &Expression) {
        for (index, sequence) in expression.alternatives.iter().enumerate() {
            if index != 0 {
                self.bytes.extend_from_slice(br"\|");
            }
            for piece in &sequence.pieces {
                self.render_piece(piece);
            }
        }
    }

    fn render_piece(&mut self, piece: &Piece) {
        self.render_atom(&piece.atom);
        match piece.repetition {
            Repetition {
                min: 1,
                max: Some(1),
            } => {}
            Repetition { min: 0, max: None } => self.bytes.push(b'*'),
            Repetition { min: 1, max: None } => self.bytes.extend_from_slice(br"\+"),
            Repetition {
                min: 0,
                max: Some(1),
            } => self.bytes.extend_from_slice(br"\?"),
            Repetition { min, max } => {
                self.bytes.extend_from_slice(br"\{");
                self.bytes.extend_from_slice(min.to_string().as_bytes());
                match max {
                    Some(maximum) if maximum == min => {}
                    Some(maximum) => {
                        self.bytes.push(b',');
                        self.bytes.extend_from_slice(maximum.to_string().as_bytes());
                    }
                    None => self.bytes.push(b','),
                }
                self.bytes.extend_from_slice(br"\}");
            }
        }
    }

    fn render_atom(&mut self, atom: &Atom) {
        match atom {
            Atom::Literal(byte) => self.render_literal(*byte),
            Atom::Any => self.bytes.push(b'.'),
            Atom::Bracket(bracket) => self.bytes.extend_from_slice(&bracket.raw),
            Atom::Group { id, expression } => {
                let normalized_id = self.open_group();
                self.original_groups[*id] = Some(normalized_id);
                self.render_expression(expression);
                self.close_group();
            }
            Atom::BackReference(id) => {
                self.open_group();
                self.bytes.push(b'\\');
                self.bytes.extend_from_slice(
                    self.original_groups[*id]
                        .expect("validated back reference must have a rendered group")
                        .to_string()
                        .as_bytes(),
                );
                self.close_group();
            }
            Atom::NestedRepetition(piece) => {
                self.open_group();
                self.render_piece(piece);
                self.close_group();
            }
            Atom::Assertion(assertion) => match assertion {
                Assertion::Start => self.bytes.push(b'^'),
                Assertion::End => self.bytes.push(b'$'),
                Assertion::WordStart => self.bytes.extend_from_slice(br"\<"),
                Assertion::WordEnd => self.bytes.extend_from_slice(br"\>"),
                Assertion::WordBoundary => {
                    self.open_group();
                    self.bytes.extend_from_slice(br"\<\|\>");
                    self.close_group();
                }
                Assertion::NotWordBoundary => {
                    self.open_group();
                    self.close_group();
                }
            },
        }
    }

    fn render_literal(&mut self, byte: u8) {
        if matches!(byte, b'\\' | b'^' | b'$' | b'.' | b'[' | b'*') {
            self.bytes.push(b'\\');
        }
        self.bytes.push(byte);
    }

    fn open_group(&mut self) -> usize {
        let id = self.next_group;
        self.next_group += 1;
        self.bytes.extend_from_slice(br"\(");
        id
    }

    fn close_group(&mut self) {
        self.bytes.extend_from_slice(br"\)");
    }
}

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
struct MatchState {
    position: usize,
    captures: Vec<Option<Span>>,
}

struct SafeBreMatcher<'a> {
    input: &'a [u8],
}

impl<'a> SafeBreMatcher<'a> {
    fn execute(&self, pattern: &ParsedPattern) -> RegexOutcome {
        let initial = MatchState {
            position: 0,
            captures: vec![None; pattern.capture_count + 1],
        };
        let mut matches = self.match_expression(&pattern.expression, initial);
        deduplicate_states(&mut matches);
        let best = matches.into_iter().reduce(|best, candidate| {
            if candidate.position > best.position {
                candidate
            } else {
                best
            }
        });
        RegexOutcome {
            capture_count: pattern.capture_count,
            whole_match: best.as_ref().map(|state| Span {
                start: 0,
                end: state.position,
            }),
            first_capture: best.and_then(|state| state.captures.get(1).copied().flatten()),
        }
    }

    fn match_expression(&self, expression: &Expression, state: MatchState) -> Vec<MatchState> {
        let mut matches = Vec::new();
        for sequence in &expression.alternatives {
            matches.extend(self.match_sequence(sequence, state.clone()));
        }
        deduplicate_states(&mut matches);
        matches
    }

    fn match_sequence(&self, sequence: &Sequence, state: MatchState) -> Vec<MatchState> {
        let mut states = vec![state];
        for piece in &sequence.pieces {
            let mut next = Vec::new();
            for state in states {
                next.extend(self.match_piece(piece, state));
            }
            deduplicate_states(&mut next);
            if next.is_empty() {
                return next;
            }
            states = next;
        }
        states
    }

    fn match_piece(&self, piece: &Piece, state: MatchState) -> Vec<MatchState> {
        if matches!(
            piece.atom,
            Atom::Literal(_) | Atom::Any | Atom::Bracket(_) | Atom::BackReference(_)
        ) {
            return self.match_deterministic_repetition(piece, state);
        }
        if piece.repetition.min == 0 && piece.repetition.max.is_some() {
            return self.match_zero_based_bounded_repetition(piece, state);
        }
        let fallback_limit = piece
            .repetition
            .min
            .saturating_add(u32::try_from(self.input.len()).unwrap_or(u32::MAX))
            .saturating_add(1);
        let limit = piece.repetition.max.unwrap_or(fallback_limit);
        let mut matches = Vec::new();
        let mut path = HashSet::new();
        path.insert(state.clone());
        self.match_greedy_repetition(piece, state, 0, limit, &mut path, &mut matches);
        deduplicate_states(&mut matches);
        matches
    }

    fn match_deterministic_repetition(&self, piece: &Piece, state: MatchState) -> Vec<MatchState> {
        let fallback_limit = piece
            .repetition
            .min
            .saturating_add(u32::try_from(self.input.len()).unwrap_or(u32::MAX))
            .saturating_add(1);
        let limit = piece.repetition.max.unwrap_or(fallback_limit);
        let mut current = state;
        let mut accepted = if piece.repetition.min == 0 {
            vec![current.clone()]
        } else {
            Vec::new()
        };
        for count in 1..=limit {
            let mut next = self.match_atom(&piece.atom, current.clone()).into_iter();
            let Some(next_state) = next.next() else {
                break;
            };
            debug_assert!(
                next.next().is_none(),
                "deterministic atom returned branches"
            );
            if next_state.position == current.position {
                if count >= piece.repetition.min || limit >= piece.repetition.min {
                    accepted.push(next_state);
                }
                break;
            }
            current = next_state;
            if count >= piece.repetition.min {
                accepted.push(current.clone());
            }
        }
        accepted.reverse();
        deduplicate_states(&mut accepted);
        accepted
    }

    fn match_zero_based_bounded_repetition(
        &self,
        piece: &Piece,
        state: MatchState,
    ) -> Vec<MatchState> {
        let mut level = vec![state];
        let mut accepted_levels = vec![level.clone()];
        let limit = piece
            .repetition
            .max
            .expect("zero-based bounded repetition has a maximum");

        for _ in 1..=limit {
            let previous = level;
            let mut next = Vec::new();
            for state in &previous {
                next.extend(self.match_atom(&piece.atom, state.clone()));
            }
            deduplicate_states(&mut next);
            if next.is_empty() {
                break;
            }
            let stable = same_state_set(&previous, &next);
            accepted_levels.push(next.clone());
            if stable {
                break;
            }
            level = next;
        }
        accepted_levels.reverse();
        let mut accepted = accepted_levels.into_iter().flatten().collect::<Vec<_>>();
        deduplicate_states(&mut accepted);
        accepted
    }

    fn match_greedy_repetition(
        &self,
        piece: &Piece,
        state: MatchState,
        count: u32,
        limit: u32,
        path: &mut HashSet<MatchState>,
        matches: &mut Vec<MatchState>,
    ) {
        if count < limit {
            for next in self.match_atom(&piece.atom, state.clone()) {
                if next.position == state.position {
                    if count < piece.repetition.min && limit >= piece.repetition.min {
                        matches.push(next);
                    }
                    continue;
                }
                if path.insert(next.clone()) {
                    self.match_greedy_repetition(
                        piece,
                        next.clone(),
                        count + 1,
                        limit,
                        path,
                        matches,
                    );
                    path.remove(&next);
                } else if count + 1 >= piece.repetition.min {
                    matches.push(next);
                }
            }
        }
        if count >= piece.repetition.min {
            matches.push(state);
        }
    }

    fn match_atom(&self, atom: &Atom, mut state: MatchState) -> Vec<MatchState> {
        match atom {
            Atom::Literal(expected) => self
                .input
                .get(state.position)
                .filter(|byte| *byte == expected)
                .map(|_| {
                    state.position += 1;
                    vec![state]
                })
                .unwrap_or_default(),
            Atom::Any => self
                .input
                .get(state.position)
                .map(|_| {
                    state.position += 1;
                    vec![state]
                })
                .unwrap_or_default(),
            Atom::Bracket(bracket) => self
                .input
                .get(state.position)
                .filter(|byte| bracket.matches(**byte))
                .map(|_| {
                    state.position += 1;
                    vec![state]
                })
                .unwrap_or_default(),
            Atom::Group { id, expression } => {
                clear_expression_captures(expression, &mut state.captures);
                state.captures[*id] = None;
                let start = state.position;
                let mut matches = self.match_expression(expression, state);
                for matched in &mut matches {
                    matched.captures[*id] = Some(Span {
                        start,
                        end: matched.position,
                    });
                }
                matches
            }
            Atom::BackReference(id) => {
                let Some(span) = state.captures.get(*id).copied().flatten() else {
                    return Vec::new();
                };
                let Some(captured) = self.input.get(span.start..span.end) else {
                    return Vec::new();
                };
                let Some(end) = state.position.checked_add(captured.len()) else {
                    return Vec::new();
                };
                if self.input.get(state.position..end) == Some(captured) {
                    state.position = end;
                    vec![state]
                } else {
                    Vec::new()
                }
            }
            Atom::NestedRepetition(piece) => self.match_piece(piece, state),
            Atom::Assertion(assertion) => {
                if self.assertion_matches(*assertion, state.position) {
                    vec![state]
                } else {
                    Vec::new()
                }
            }
        }
    }

    fn assertion_matches(&self, assertion: Assertion, position: usize) -> bool {
        let previous_is_word = position
            .checked_sub(1)
            .and_then(|index| self.input.get(index))
            .copied()
            .map(is_word_byte)
            .unwrap_or(false);
        let next_is_word = self
            .input
            .get(position)
            .copied()
            .map(is_word_byte)
            .unwrap_or(false);
        match assertion {
            Assertion::Start => position == 0,
            Assertion::End => position == self.input.len(),
            Assertion::WordStart => !previous_is_word && next_is_word,
            Assertion::WordEnd => previous_is_word && !next_is_word,
            Assertion::WordBoundary => previous_is_word != next_is_word,
            Assertion::NotWordBoundary => previous_is_word == next_is_word,
        }
    }
}

fn is_word_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'_'
}

fn clear_expression_captures(expression: &Expression, captures: &mut [Option<Span>]) {
    for sequence in &expression.alternatives {
        for piece in &sequence.pieces {
            clear_atom_captures(&piece.atom, captures);
        }
    }
}

fn clear_atom_captures(atom: &Atom, captures: &mut [Option<Span>]) {
    match atom {
        Atom::Group { id, expression } => {
            captures[*id] = None;
            clear_expression_captures(expression, captures);
        }
        Atom::NestedRepetition(piece) => clear_atom_captures(&piece.atom, captures),
        _ => {}
    }
}

fn same_state_set(left: &[MatchState], right: &[MatchState]) -> bool {
    left.len() == right.len()
        && left.iter().collect::<HashSet<_>>() == right.iter().collect::<HashSet<_>>()
}

fn deduplicate_states(states: &mut Vec<MatchState>) {
    let mut seen = HashSet::with_capacity(states.len());
    states.retain(|state| seen.insert(state.clone()));
}

#[derive(Clone, Copy, Debug, Default)]
pub struct PosixRegexEngine;

impl PosixRegexEngine {
    pub const fn new() -> Self {
        Self
    }
}

impl RegexEngine for PosixRegexEngine {
    fn execute(&self, input: &[u8], pattern: &[u8]) -> Result<RegexOutcome, RegexCompileError> {
        let prepared = prepare_pattern(pattern).map_err(|kind| RegexCompileError {
            message: compile_error_message(kind),
        })?;
        compile_normalized(pattern, &prepared.normalized).map_err(|kind| RegexCompileError {
            message: compile_error_message(kind),
        })?;
        Ok(SafeBreMatcher { input }.execute(&prepared.parsed))
    }
}

#[cfg(test)]
pub(crate) mod mock {
    use std::cell::RefCell;
    use std::collections::VecDeque;

    use super::{RegexCompileError, RegexEngine, RegexOutcome};

    #[derive(Clone, Debug, Eq, PartialEq)]
    pub(crate) struct RegexCall {
        pub input: Vec<u8>,
        pub pattern: Vec<u8>,
    }

    #[derive(Default)]
    pub(crate) struct MockRegexEngine {
        calls: RefCell<Vec<RegexCall>>,
        responses: RefCell<VecDeque<Result<RegexOutcome, RegexCompileError>>>,
    }

    impl MockRegexEngine {
        pub(crate) fn with_responses(
            responses: impl IntoIterator<Item = Result<RegexOutcome, RegexCompileError>>,
        ) -> Self {
            Self {
                calls: RefCell::new(Vec::new()),
                responses: RefCell::new(responses.into_iter().collect()),
            }
        }

        pub(crate) fn calls(&self) -> Vec<RegexCall> {
            self.calls.borrow().clone()
        }
    }

    impl RegexEngine for MockRegexEngine {
        fn execute(&self, input: &[u8], pattern: &[u8]) -> Result<RegexOutcome, RegexCompileError> {
            self.calls.borrow_mut().push(RegexCall {
                input: input.to_vec(),
                pattern: pattern.to_vec(),
            });
            self.responses
                .borrow_mut()
                .pop_front()
                .expect("MockRegexEngine response queue exhausted")
        }
    }
}

#[cfg(test)]
mod tests {
    use super::mock::MockRegexEngine;
    use super::{
        normalize_pattern, validate_pattern, PosixRegexEngine, RegexEngine, RegexOutcome, Span,
    };

    #[test]
    fn recording_mock_seam_compiles() {
        let regex_engine = MockRegexEngine::default();
        let _engine: &dyn RegexEngine = &regex_engine;
        let _ = regex_engine.calls();
        let _ = MockRegexEngine::with_responses([]);
    }

    mod validator_tests {
        use super::super::BreErrorKind;
        use super::validate_pattern;

        #[test]
        fn accepts_basic_literal_and_metacharacter_patterns() {
            let patterns: &[&[u8]] = &[
                b"",
                b"literal",
                b"^a.*z$",
                b"[a-z][[:digit:]]*",
                b"a\\|alphabet",
                b"colou\\?r",
            ];

            for &pattern in patterns {
                assert_eq!(validate_pattern(pattern), Ok(()), "{pattern:?}");
            }
        }

        #[test]
        fn accepts_balanced_groups_backreferences_and_gnu_operators() {
            let patterns: &[&[u8]] = &[
                br"\(a\)\1",
                br"\(a\)\(b\)",
                br"a\+b\?c\|d",
                br"a\{,2\}",
                br"\<\w\+\s\W\>",
                br"\`word\'",
                b"[\xff-\xff]",
            ];

            for &pattern in patterns {
                assert_eq!(validate_pattern(pattern), Ok(()), "{pattern:?}");
            }
        }

        #[test]
        fn rejects_unbalanced_groups_and_invalid_backreferences() {
            for pattern in [br"\(".as_slice(), br"\)".as_slice(), br"\(a\)\)".as_slice()] {
                assert_eq!(
                    validate_pattern(pattern),
                    Err(BreErrorKind::UnmatchedParenthesis),
                    "{pattern:?}"
                );
            }
            for pattern in [
                br"\1".as_slice(),
                br"\(a\)\2".as_slice(),
                br"\(\1\)".as_slice(),
            ] {
                assert_eq!(
                    validate_pattern(pattern),
                    Err(BreErrorKind::InvalidBackReference),
                    "{pattern:?}"
                );
            }
        }

        #[test]
        fn classifies_bracket_and_escape_failures() {
            let cases: &[(&[u8], BreErrorKind)] = &[
                (b"\\", BreErrorKind::TrailingBackslash),
                (b"[", BreErrorKind::InvalidRegularExpression),
                (b"[^", BreErrorKind::InvalidRegularExpression),
                (b"[]", BreErrorKind::UnmatchedBracket),
                (b"[z-a]", BreErrorKind::InvalidRangeEnd),
                (b"[[:missing:]]", BreErrorKind::InvalidCharacterClassName),
                (b"[[.ab.]]", BreErrorKind::InvalidCollationCharacter),
            ];

            for &(pattern, expected) in cases {
                assert_eq!(validate_pattern(pattern), Err(expected), "{pattern:?}");
            }
        }

        #[test]
        fn validates_interval_and_repetition_placement() {
            let cases: &[(&[u8], BreErrorKind)] = &[
                (br"\{1\}", BreErrorKind::InvalidPrecedingRegularExpression),
                (b"a**", BreErrorKind::InvalidPrecedingRegularExpression),
                (br"a\{\}", BreErrorKind::InvalidRepetitionContent),
                (br"a\{2,1\}", BreErrorKind::InvalidRepetitionContent),
                (br"a\{1", BreErrorKind::UnmatchedRepetition),
                (br"a\{32768\}", BreErrorKind::RegularExpressionTooBig),
            ];

            for &(pattern, expected) in cases {
                assert_eq!(validate_pattern(pattern), Err(expected), "{pattern:?}");
            }
            for pattern in [
                br"a\{0\}".as_slice(),
                br"a\{,2\}".as_slice(),
                br"a\{2,\}".as_slice(),
                br"a\{1,2\}".as_slice(),
                br"a*\+".as_slice(),
                br"a\+\?".as_slice(),
            ] {
                assert_eq!(validate_pattern(pattern), Ok(()), "{pattern:?}");
            }
        }
    }

    mod normalizer_tests {
        use super::normalize_pattern;

        #[test]
        fn preserves_supported_basic_patterns_byte_for_byte() {
            let patterns: &[&[u8]] = &[
                b"",
                b"literal",
                b"^a.*z$",
                b"[a-z][[:digit:]]*",
                b"a\\|alphabet",
                b"colou\\?r",
            ];

            for &pattern in patterns {
                assert_eq!(
                    normalize_pattern(pattern),
                    Ok(pattern.to_vec()),
                    "{pattern:?}"
                );
            }
        }

        #[test]
        fn adapts_only_verified_parser_differences() {
            assert_eq!(
                normalize_pattern(br"\a\d\n\r\t\0\."),
                Ok(br"adnrt0\.".to_vec())
            );
            assert_eq!(
                normalize_pattern(br"\w\W\s\S"),
                Ok(br"[[:alnum:]_][^[:alnum:]_][[:space:]][^[:space:]]".to_vec())
            );
            assert_eq!(normalize_pattern(b"a^b$c"), Ok(br"a\^b\$c".to_vec()));
            assert_eq!(normalize_pattern(br"a\{,2\}"), Ok(br"a\{0,2\}".to_vec()));
        }

        #[test]
        fn preserves_capture_numbering_while_delimiting_backreferences() {
            assert_eq!(
                normalize_pattern(br"\(a\)\10"),
                Ok(br"\(a\)\(\1\)0".to_vec())
            );
            assert_eq!(
                normalize_pattern(br"\b\(a\)\1"),
                Ok(br"\(\<\|\>\)\(a\)\(\2\)".to_vec())
            );
        }
    }

    mod engine_tests {
        use super::{PosixRegexEngine, RegexEngine, RegexOutcome, Span};

        fn plain_match(start: usize, end: usize) -> RegexOutcome {
            RegexOutcome {
                capture_count: 0,
                whole_match: Some(Span { start, end }),
                first_capture: None,
            }
        }

        #[test]
        fn reports_prefix_matches_and_capture_counts() {
            let engine = PosixRegexEngine::new();
            assert_eq!(
                engine.execute(b"hello", b"h\\(ell\\)o"),
                Ok(RegexOutcome {
                    capture_count: 1,
                    whole_match: Some(Span { start: 0, end: 5 }),
                    first_capture: Some(Span { start: 1, end: 4 }),
                })
            );
            assert_eq!(
                engine.execute(b"hello", b"world"),
                Ok(RegexOutcome {
                    capture_count: 0,
                    whole_match: None,
                    first_capture: None,
                })
            );
            assert_eq!(
                engine.execute(b"hello", b"h\\(xyz\\)o"),
                Ok(RegexOutcome {
                    capture_count: 1,
                    whole_match: None,
                    first_capture: None,
                })
            );
        }

        #[test]
        fn reports_first_capture_participation_across_multiple_groups() {
            let engine = PosixRegexEngine::new();
            assert_eq!(
                engine.execute(b"ab", br"\(a\)\(b\)"),
                Ok(RegexOutcome {
                    capture_count: 2,
                    whole_match: Some(Span { start: 0, end: 2 }),
                    first_capture: Some(Span { start: 0, end: 1 }),
                })
            );
            assert_eq!(
                engine.execute(b"b", br"\(a\)\?\(b\)"),
                Ok(RegexOutcome {
                    capture_count: 2,
                    whole_match: Some(Span { start: 0, end: 1 }),
                    first_capture: None,
                })
            );
            assert_eq!(
                engine.execute(b"abc", br"\(\)abc"),
                Ok(RegexOutcome {
                    capture_count: 1,
                    whole_match: Some(Span { start: 0, end: 3 }),
                    first_capture: Some(Span { start: 0, end: 0 }),
                })
            );
        }

        #[test]
        fn retains_group_count_when_a_grouped_pattern_does_not_match() {
            let engine = PosixRegexEngine::new();
            assert_eq!(
                engine.execute(b"hello", br"h\(xyz\)o"),
                Ok(RegexOutcome {
                    capture_count: 1,
                    whole_match: None,
                    first_capture: None,
                })
            );
        }

        #[test]
        fn supports_backreferences_and_repeated_capture_selection() {
            let engine = PosixRegexEngine::new();
            assert_eq!(
                engine.execute(b"abab", br"\(ab\)\1"),
                Ok(RegexOutcome {
                    capture_count: 1,
                    whole_match: Some(Span { start: 0, end: 4 }),
                    first_capture: Some(Span { start: 0, end: 2 }),
                })
            );
            assert_eq!(
                engine.execute(b"aaaa", br"\(a*\)\1"),
                Ok(RegexOutcome {
                    capture_count: 1,
                    whole_match: Some(Span { start: 0, end: 4 }),
                    first_capture: Some(Span { start: 0, end: 2 }),
                })
            );
        }

        #[test]
        fn supports_gnu_basic_operators_and_word_assertions() {
            let engine = PosixRegexEngine::new();
            assert_eq!(
                engine.execute(b"colour", br"colou\?r"),
                Ok(plain_match(0, 6))
            );
            assert_eq!(
                engine.execute(b"color", br"colou\?r"),
                Ok(plain_match(0, 5))
            );
            assert_eq!(engine.execute(b"aaaa", br"a\+"), Ok(plain_match(0, 4)));
            assert_eq!(engine.execute(b"aaa", br"a\{2,3\}"), Ok(plain_match(0, 3)));
            assert_eq!(
                engine.execute(b"alphabet", br"a\|alpha"),
                Ok(plain_match(0, 5))
            );
            assert_eq!(
                engine.execute(b"word!", br"\<\w\+\>"),
                Ok(plain_match(0, 4))
            );
            assert_eq!(engine.execute(b"wordx", br"word\B"), Ok(plain_match(0, 4)));
            assert_eq!(
                engine.execute(b"foo bar", br"foo\s\+bar"),
                Ok(plain_match(0, 7))
            );
        }

        #[test]
        fn treats_escaped_ordinary_bytes_as_literals() {
            let engine = PosixRegexEngine::new();
            for &(input, pattern) in &[
                (b"a".as_slice(), br"\a".as_slice()),
                (b"d".as_slice(), br"\d".as_slice()),
                (b"n".as_slice(), br"\n".as_slice()),
                (b"t".as_slice(), br"\t".as_slice()),
                (b"_".as_slice(), br"\_".as_slice()),
            ] {
                assert_eq!(engine.execute(input, pattern), Ok(plain_match(0, 1)));
            }
        }

        #[test]
        fn matches_literals_and_basic_metacharacters_at_offset_zero() {
            let engine = PosixRegexEngine::new();
            assert_eq!(engine.execute(b"alphabet", b"alpha"), Ok(plain_match(0, 5)));
            assert_eq!(engine.execute(b"alphabet", b"a.*"), Ok(plain_match(0, 8)));
            assert_eq!(engine.execute(b"abc", b"^a.c$"), Ok(plain_match(0, 3)));
        }

        #[test]
        fn reports_no_match_when_only_a_later_offset_matches() {
            let engine = PosixRegexEngine::new();
            assert_eq!(
                engine.execute(b"abc", b"b"),
                Ok(RegexOutcome {
                    capture_count: 0,
                    whole_match: None,
                    first_capture: None,
                })
            );
        }

        #[test]
        fn supports_empty_input_and_zero_length_prefix_matches() {
            let engine = PosixRegexEngine::new();
            assert_eq!(engine.execute(b"", b""), Ok(plain_match(0, 0)));
            assert_eq!(engine.execute(b"", b"a*"), Ok(plain_match(0, 0)));
            assert_eq!(engine.execute(b"abc", b""), Ok(plain_match(0, 0)));
        }

        #[test]
        fn spans_count_input_bytes_not_unicode_characters() {
            let engine = PosixRegexEngine::new();
            assert_eq!(engine.execute(b"\xc3\xa9x", b".."), Ok(plain_match(0, 2)));
            assert_eq!(
                engine.execute(b"\xff\xff", b"\\(\xff\\)\\1"),
                Ok(RegexOutcome {
                    capture_count: 1,
                    whole_match: Some(Span { start: 0, end: 2 }),
                    first_capture: Some(Span { start: 0, end: 1 }),
                })
            );
            assert_eq!(
                engine.execute(b"\xff", b"[\xff-\xff]"),
                Ok(plain_match(0, 1))
            );
        }

        #[test]
        fn supports_ranges_and_default_character_classes() {
            let engine = PosixRegexEngine::new();
            assert_eq!(
                engine.execute(b"abc123!", b"[a-z]*[[:digit:]]*"),
                Ok(plain_match(0, 6))
            );
            assert_eq!(
                engine.execute(b"123abc", b"[[:alpha:]]*"),
                Ok(plain_match(0, 0))
            );
        }

        #[test]
        fn selects_the_longest_alternative_at_the_leftmost_offset() {
            let engine = PosixRegexEngine::new();
            assert_eq!(
                engine.execute(b"alphabet", b"a\\|alpha\\|alphabet"),
                Ok(plain_match(0, 8))
            );
        }
    }

    mod diagnostic_tests {
        use super::super::{compile_error_message, BreErrorKind, RegexCompileError};
        use super::{PosixRegexEngine, RegexEngine};

        #[test]
        fn renders_exact_regerror_message_bodies() {
            let cases: &[(BreErrorKind, &[u8])] = &[
                (
                    BreErrorKind::InvalidRegularExpression,
                    b"Invalid regular expression",
                ),
                (BreErrorKind::TrailingBackslash, b"Trailing backslash"),
                (BreErrorKind::InvalidRangeEnd, b"Invalid range end"),
                (
                    BreErrorKind::InvalidCharacterClassName,
                    b"Invalid character class name",
                ),
                (
                    BreErrorKind::InvalidBackReference,
                    b"Invalid back reference",
                ),
                (BreErrorKind::UnmatchedParenthesis, b"Unmatched ( or \\("),
                (
                    BreErrorKind::InvalidRepetitionContent,
                    b"Invalid content of \\{\\}",
                ),
            ];

            for &(kind, expected) in cases {
                assert_eq!(compile_error_message(kind), expected, "{kind:?}");
            }
        }

        #[test]
        fn engine_returns_exact_compile_diagnostics() {
            let engine = PosixRegexEngine::new();
            let cases: &[(&[u8], &[u8])] = &[
                (b"[", b"Invalid regular expression"),
                (b"\\", b"Trailing backslash"),
                (b"[z-a]", b"Invalid range end"),
                (b"[[:missing:]]", b"Invalid character class name"),
                (br"\1", b"Invalid back reference"),
            ];

            for &(pattern, message) in cases {
                assert_eq!(
                    engine.execute(b"input", pattern),
                    Err(RegexCompileError {
                        message: message.to_vec(),
                    }),
                    "{pattern:?}"
                );
            }
        }
    }
}
