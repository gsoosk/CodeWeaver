use std::ffi::OsStr;
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, BufReader, Read, Seek, SeekFrom, Write};

use posix_regex::{PosixRegex, PosixRegexBuilder};

pub const FGETS_CAPACITY: usize = 2048;
pub const OVERFLOW_BLOCK_SIZE: usize = 8192;

#[derive(Debug)]
pub struct LineChunk {
    pub consumed: Vec<u8>,
}

impl LineChunk {
    pub fn c_prefix(&self) -> &[u8] {
        let end = self
            .consumed
            .iter()
            .position(|byte| *byte == 0)
            .unwrap_or(self.consumed.len());
        &self.consumed[..end]
    }
}

#[derive(Debug)]
pub struct ChunkRead {
    pub chunk: Option<LineChunk>,
    pub eof: bool,
    pub error: Option<io::Error>,
}

pub trait InputStream {
    fn read_chunk(&mut self, capacity: usize) -> ChunkRead;
    fn eof(&self) -> bool;
}

pub trait SplitStream {
    fn write_c_prefix(&mut self, bytes: &[u8]);
    fn position(&mut self) -> io::Result<u64>;
    fn seek(&mut self, from: SeekFrom) -> io::Result<u64>;
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize>;
    fn flush_checked(&mut self) -> io::Result<()>;
    fn set_len(&mut self, len: u64) -> io::Result<()>;
    fn finish(self: Box<Self>) -> io::Result<()>;
}

pub trait FileSystem {
    fn open_input(&mut self, path: &OsStr) -> io::Result<Box<dyn InputStream>>;
    fn stdin(&mut self) -> io::Result<Box<dyn InputStream>>;
    fn open_output(&mut self, path: &OsStr) -> io::Result<Box<dyn SplitStream>>;
    fn temporary(&mut self) -> io::Result<Box<dyn SplitStream>>;
    fn remove(&mut self, path: &OsStr) -> io::Result<()>;
}

#[derive(Debug, Eq, PartialEq)]
pub struct RegexCompileError;

pub trait RegexMatcher {
    fn is_match(&mut self, subject: &[u8]) -> bool;
}

pub trait RegexCompiler {
    fn compile(&mut self, pattern: &[u8]) -> Result<Box<dyn RegexMatcher>, RegexCompileError>;
}

pub trait OutputWriter: Write {}

impl<T: Write + ?Sized> OutputWriter for T {}

struct RealInputStream {
    reader: BufReader<Box<dyn Read>>,
    eof: bool,
}

impl RealInputStream {
    fn new(reader: Box<dyn Read>) -> Self {
        Self {
            reader: BufReader::new(reader),
            eof: false,
        }
    }
}

impl InputStream for RealInputStream {
    fn read_chunk(&mut self, capacity: usize) -> ChunkRead {
        let limit = capacity.saturating_sub(1);
        let mut consumed = Vec::with_capacity(limit);
        let mut error = None;

        while consumed.len() < limit {
            let read = {
                match self.reader.fill_buf() {
                    Ok(available) if available.is_empty() => {
                        self.eof = true;
                        None
                    }
                    Ok(available) => {
                        let remaining = limit - consumed.len();
                        let available = &available[..available.len().min(remaining)];
                        let newline = available.iter().position(|byte| *byte == b'\n');
                        let amount = newline.map_or(available.len(), |index| index + 1);
                        consumed.extend_from_slice(&available[..amount]);
                        Some((amount, newline.is_some()))
                    }
                    Err(source) => {
                        error = Some(source);
                        None
                    }
                }
            };

            let Some((amount, found_newline)) = read else {
                break;
            };
            self.reader.consume(amount);
            if found_newline {
                break;
            }
        }

        ChunkRead {
            chunk: (!consumed.is_empty()).then_some(LineChunk { consumed }),
            eof: self.eof,
            error,
        }
    }

    fn eof(&self) -> bool {
        self.eof
    }
}

struct RealSplitStream {
    file: File,
    sticky_write_error: Option<io::Error>,
}

impl RealSplitStream {
    fn new(file: File) -> Self {
        Self {
            file,
            sticky_write_error: None,
        }
    }
}

impl SplitStream for RealSplitStream {
    fn write_c_prefix(&mut self, bytes: &[u8]) {
        if self.sticky_write_error.is_some() {
            return;
        }
        let end = bytes
            .iter()
            .position(|byte| *byte == 0)
            .unwrap_or(bytes.len());
        if let Err(source) = self.file.write_all(&bytes[..end]) {
            self.sticky_write_error = Some(source);
        }
    }

    fn position(&mut self) -> io::Result<u64> {
        self.file.stream_position()
    }

    fn seek(&mut self, from: SeekFrom) -> io::Result<u64> {
        self.file.seek(from)
    }

    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        self.file.read(buffer)
    }

    fn flush_checked(&mut self) -> io::Result<()> {
        if let Some(source) = self.sticky_write_error.take() {
            return Err(source);
        }
        self.file.flush()
    }

    fn set_len(&mut self, len: u64) -> io::Result<()> {
        self.file.set_len(len)
    }

    fn finish(mut self: Box<Self>) -> io::Result<()> {
        if let Some(source) = self.sticky_write_error.take() {
            return Err(source);
        }
        self.file.flush()
    }
}

#[derive(Default)]
pub struct RealFileSystem;

impl FileSystem for RealFileSystem {
    fn open_input(&mut self, path: &OsStr) -> io::Result<Box<dyn InputStream>> {
        Ok(Box::new(RealInputStream::new(Box::new(File::open(path)?))))
    }

    fn stdin(&mut self) -> io::Result<Box<dyn InputStream>> {
        Ok(Box::new(RealInputStream::new(Box::new(io::stdin()))))
    }

    fn open_output(&mut self, path: &OsStr) -> io::Result<Box<dyn SplitStream>> {
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(true)
            .open(path)?;
        Ok(Box::new(RealSplitStream::new(file)))
    }

    fn temporary(&mut self) -> io::Result<Box<dyn SplitStream>> {
        Ok(Box::new(RealSplitStream::new(tempfile::tempfile()?)))
    }

    fn remove(&mut self, path: &OsStr) -> io::Result<()> {
        fs::remove_file(path)
    }
}

#[derive(Default)]
pub struct PosixRegexCompiler;

struct PosixRegexMatcher {
    regex: Option<PosixRegex<'static>>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum BreRepeat {
    Star,
    Plus,
    Optional,
    Interval,
}

#[derive(Clone, Copy)]
struct BreAtomState {
    can_repeat: bool,
    repeat: Option<BreRepeat>,
    repeat_start: usize,
    at_branch_start: bool,
}

impl Default for BreAtomState {
    fn default() -> Self {
        Self {
            can_repeat: false,
            repeat: None,
            repeat_start: 0,
            at_branch_start: true,
        }
    }
}

fn mark_bre_atom(state: &mut BreAtomState, output_len: usize) {
    state.can_repeat = true;
    state.repeat = None;
    state.repeat_start = output_len;
    state.at_branch_start = false;
}

fn mark_bre_assertion(state: &mut BreAtomState) {
    state.can_repeat = false;
    state.repeat = None;
    state.at_branch_start = false;
}

fn append_repeat(output: &mut Vec<u8>, state: &mut BreAtomState, repeat: BreRepeat) {
    state.repeat_start = output.len();
    state.repeat = Some(repeat);
    match repeat {
        BreRepeat::Star => output.push(b'*'),
        BreRepeat::Plus => output.extend_from_slice(br"\+"),
        BreRepeat::Optional => output.extend_from_slice(br"\?"),
        BreRepeat::Interval => {}
    }
}

fn combine_repeat(
    output: &mut Vec<u8>,
    state: &mut BreAtomState,
    outer: BreRepeat,
) -> Result<(), RegexCompileError> {
    let Some(inner) = state.repeat else {
        append_repeat(output, state, outer);
        return Ok(());
    };

    let combined = match (inner, outer) {
        (BreRepeat::Star, BreRepeat::Plus | BreRepeat::Optional) => BreRepeat::Star,
        (BreRepeat::Plus, BreRepeat::Plus) => BreRepeat::Plus,
        (BreRepeat::Plus, BreRepeat::Optional) => BreRepeat::Star,
        (BreRepeat::Optional, BreRepeat::Plus) => BreRepeat::Star,
        (BreRepeat::Optional, BreRepeat::Optional) => BreRepeat::Optional,
        (BreRepeat::Interval, BreRepeat::Plus | BreRepeat::Optional) => return Ok(()),
        _ => return Err(RegexCompileError),
    };
    output.truncate(state.repeat_start);
    append_repeat(output, state, combined);
    Ok(())
}

#[derive(Clone, Copy)]
struct BreInterval {
    lower: u64,
    upper: Option<u64>,
    has_comma: bool,
    end: usize,
}

fn parse_bre_number(pattern: &[u8], index: &mut usize) -> Result<Option<u64>, RegexCompileError> {
    let start = *index;
    let mut value = 0_u64;
    while let Some(digit @ b'0'..=b'9') = pattern.get(*index).copied() {
        value = value
            .checked_mul(10)
            .and_then(|current| current.checked_add(u64::from(digit - b'0')))
            .ok_or(RegexCompileError)?;
        *index += 1;
    }
    Ok((*index != start).then_some(value))
}

fn parse_bre_interval(pattern: &[u8], start: usize) -> Result<BreInterval, RegexCompileError> {
    const RE_DUP_MAX: u64 = 32_767;

    let mut index = start + 2;
    let parsed_lower = parse_bre_number(pattern, &mut index)?;
    let has_comma = pattern.get(index) == Some(&b',');
    let parsed_upper = if has_comma {
        index += 1;
        parse_bre_number(pattern, &mut index)?
    } else {
        parsed_lower
    };
    if parsed_lower.is_none() && !has_comma {
        return Err(RegexCompileError);
    }

    let lower = parsed_lower.unwrap_or(0);
    if lower > RE_DUP_MAX
        || parsed_upper.is_some_and(|upper| upper > RE_DUP_MAX || lower > upper)
        || pattern.get(index..index + 2) != Some(br"\}")
    {
        return Err(RegexCompileError);
    }

    Ok(BreInterval {
        lower,
        upper: parsed_upper,
        has_comma,
        end: index + 2,
    })
}

fn append_interval(output: &mut Vec<u8>, interval: BreInterval) {
    output.extend_from_slice(br"\{");
    output.extend_from_slice(interval.lower.to_string().as_bytes());
    if interval.has_comma {
        output.push(b',');
        if let Some(upper) = interval.upper {
            output.extend_from_slice(upper.to_string().as_bytes());
        }
    }
    output.extend_from_slice(br"\}");
}

enum BreBracketMember {
    Byte { value: u8, rangeable: bool },
    Set([bool; 256]),
}

fn class_contains(name: &[u8], byte: u8) -> Option<bool> {
    let matches = match name {
        b"alnum" => byte.is_ascii_alphanumeric(),
        b"alpha" => byte.is_ascii_alphabetic(),
        b"blank" => matches!(byte, b' ' | b'\t'),
        b"cntrl" => byte <= 0x1f || byte == 0x7f,
        b"digit" => byte.is_ascii_digit(),
        b"graph" => (0x21..=0x7e).contains(&byte),
        b"lower" => byte.is_ascii_lowercase(),
        b"print" => (0x20..=0x7e).contains(&byte),
        b"punct" => (0x21..=0x7e).contains(&byte) && !byte.is_ascii_alphanumeric(),
        b"space" => matches!(byte, b' ' | b'\t' | b'\n' | 0x0b | 0x0c | b'\r'),
        b"upper" => byte.is_ascii_uppercase(),
        b"xdigit" => byte.is_ascii_hexdigit(),
        _ => return None,
    };
    Some(matches)
}

fn parse_bre_bracket_member(
    pattern: &[u8],
    start: usize,
) -> Result<(BreBracketMember, usize), RegexCompileError> {
    if pattern.get(start) == Some(&b'[')
        && matches!(pattern.get(start + 1), Some(b'.' | b'=' | b':'))
    {
        let marker = pattern[start + 1];
        let content_start = start + 2;
        let relative_end = pattern[content_start..]
            .windows(2)
            .position(|window| window == [marker, b']'])
            .ok_or(RegexCompileError)?;
        let content_end = content_start + relative_end;
        let content = &pattern[content_start..content_end];
        let end = content_end + 2;

        if marker == b':' {
            let mut set = [false; 256];
            for value in 0_u8..=u8::MAX {
                set[value as usize] = class_contains(content, value).ok_or(RegexCompileError)?;
            }
            return Ok((BreBracketMember::Set(set), end));
        }
        if content.len() != 1 {
            return Err(RegexCompileError);
        }
        return Ok((
            BreBracketMember::Byte {
                value: content[0],
                rangeable: marker == b'.',
            },
            end,
        ));
    }

    let value = pattern.get(start).copied().ok_or(RegexCompileError)?;
    Ok((
        BreBracketMember::Byte {
            value,
            rangeable: true,
        },
        start + 1,
    ))
}

fn add_bre_bracket_member(
    set: &mut [bool; 256],
    member: BreBracketMember,
) -> Result<(), RegexCompileError> {
    match member {
        BreBracketMember::Byte { value, .. } => set[value as usize] = true,
        BreBracketMember::Set(members) => {
            for (selected, member) in set.iter_mut().zip(members) {
                *selected |= member;
            }
        }
    }
    Ok(())
}

fn normalized_bracket(set: &[bool; 256], invert: bool) -> Vec<u8> {
    let mut output = Vec::new();
    output.push(b'[');
    if invert {
        output.push(b'^');
    }
    for (value, selected) in set.iter().enumerate() {
        if *selected {
            output.extend_from_slice(b"[.");
            output.push(value as u8);
            output.extend_from_slice(b".]");
        }
    }
    output.push(b']');
    output
}

fn parse_bre_bracket(pattern: &[u8], start: usize) -> Result<(usize, Vec<u8>), RegexCompileError> {
    let mut index = start + 1;
    let invert = pattern.get(index) == Some(&b'^');
    if invert {
        index += 1;
    }

    let mut set = [false; 256];
    let mut first = true;
    loop {
        let byte = pattern.get(index).copied().ok_or(RegexCompileError)?;
        if byte == b']' {
            if first {
                set[b']' as usize] = true;
                first = false;
                index += 1;
                continue;
            }
            return Ok((index + 1, normalized_bracket(&set, invert)));
        }

        let (left, next) = parse_bre_bracket_member(pattern, index)?;
        index = next;
        if pattern.get(index) == Some(&b'-')
            && pattern.get(index + 1).is_some_and(|byte| *byte != b']')
        {
            let (right, end) = parse_bre_bracket_member(pattern, index + 1)?;
            let (
                BreBracketMember::Byte {
                    value: lower,
                    rangeable: true,
                },
                BreBracketMember::Byte {
                    value: upper,
                    rangeable: true,
                },
            ) = (left, right)
            else {
                return Err(RegexCompileError);
            };
            if lower > upper {
                return Err(RegexCompileError);
            }
            for value in lower..=upper {
                set[value as usize] = true;
            }
            index = end;
        } else {
            add_bre_bracket_member(&mut set, left)?;
        }
        first = false;
    }
}

fn append_literal(output: &mut Vec<u8>, byte: u8) {
    let mut set = [false; 256];
    set[byte as usize] = true;
    output.extend_from_slice(&normalized_bracket(&set, false));
}

fn append_word_class(output: &mut Vec<u8>, invert: bool) {
    let mut set = [false; 256];
    for value in 0_u8..=u8::MAX {
        set[value as usize] = value.is_ascii_alphanumeric() || value == b'_';
    }
    output.extend_from_slice(&normalized_bracket(&set, invert));
}

fn dollar_is_anchor(pattern: &[u8], index: usize) -> bool {
    index + 1 == pattern.len() || matches!(pattern.get(index + 1..index + 3), Some(br"\|" | br"\)"))
}

fn normalize_basic_regex(pattern: &[u8]) -> Result<Vec<u8>, RegexCompileError> {
    let mut groups = vec![BreAtomState::default()];
    let mut output = Vec::new();
    let mut index = 0;

    while let Some(byte) = pattern.get(index).copied() {
        match byte {
            b'[' => {
                let (end, bracket) = parse_bre_bracket(pattern, index)?;
                output.extend_from_slice(&bracket);
                mark_bre_atom(
                    groups.last_mut().expect("BRE state always has a root"),
                    output.len(),
                );
                index = end;
            }
            b'*' => {
                let state = groups.last_mut().expect("BRE state always has a root");
                if state.can_repeat {
                    if state.repeat.is_some() {
                        return Err(RegexCompileError);
                    }
                    append_repeat(&mut output, state, BreRepeat::Star);
                } else {
                    append_literal(&mut output, b'*');
                    mark_bre_atom(state, output.len());
                }
                index += 1;
            }
            b'\\' => {
                let escaped = pattern.get(index + 1).copied().ok_or(RegexCompileError)?;
                match escaped {
                    b'(' => {
                        output.extend_from_slice(br"\(");
                        groups.push(BreAtomState::default());
                        index += 2;
                    }
                    b')' => {
                        if groups.len() == 1 {
                            return Err(RegexCompileError);
                        }
                        groups.pop();
                        output.extend_from_slice(br"\)");
                        mark_bre_atom(
                            groups.last_mut().expect("BRE state always has a root"),
                            output.len(),
                        );
                        index += 2;
                    }
                    b'|' => {
                        output.extend_from_slice(br"\|");
                        *groups.last_mut().expect("BRE state always has a root") =
                            BreAtomState::default();
                        index += 2;
                    }
                    b'+' | b'?' => {
                        let state = groups.last_mut().expect("BRE state always has a root");
                        if !state.can_repeat {
                            return Err(RegexCompileError);
                        }
                        let repeat = if escaped == b'+' {
                            BreRepeat::Plus
                        } else {
                            BreRepeat::Optional
                        };
                        combine_repeat(&mut output, state, repeat)?;
                        index += 2;
                    }
                    b'{' => {
                        let state = groups.last_mut().expect("BRE state always has a root");
                        let interval = parse_bre_interval(pattern, index)?;
                        if !state.can_repeat || state.repeat.is_some() {
                            return Err(RegexCompileError);
                        }
                        state.repeat_start = output.len();
                        state.repeat = Some(BreRepeat::Interval);
                        append_interval(&mut output, interval);
                        index = interval.end;
                    }
                    b'<' | b'>' | b's' | b'S' => {
                        output.push(b'\\');
                        output.push(escaped);
                        let state = groups.last_mut().expect("BRE state always has a root");
                        if matches!(escaped, b'<' | b'>') {
                            mark_bre_assertion(state);
                        } else {
                            mark_bre_atom(state, output.len());
                        }
                        index += 2;
                    }
                    b'w' | b'W' => {
                        append_word_class(&mut output, escaped == b'W');
                        mark_bre_atom(
                            groups.last_mut().expect("BRE state always has a root"),
                            output.len(),
                        );
                        index += 2;
                    }
                    b'1'..=b'9' => {
                        output.push(b'\\');
                        output.push(escaped);
                        mark_bre_atom(
                            groups.last_mut().expect("BRE state always has a root"),
                            output.len(),
                        );
                        index += 2;
                    }
                    _ => {
                        append_literal(&mut output, escaped);
                        mark_bre_atom(
                            groups.last_mut().expect("BRE state always has a root"),
                            output.len(),
                        );
                        index += 2;
                    }
                }
            }
            b'^' => {
                let state = groups.last_mut().expect("BRE state always has a root");
                if state.at_branch_start {
                    output.push(b'^');
                    mark_bre_assertion(state);
                } else {
                    append_literal(&mut output, b'^');
                    mark_bre_atom(state, output.len());
                }
                index += 1;
            }
            b'$' => {
                let state = groups.last_mut().expect("BRE state always has a root");
                if dollar_is_anchor(pattern, index) {
                    output.push(b'$');
                    mark_bre_assertion(state);
                } else {
                    append_literal(&mut output, b'$');
                    mark_bre_atom(state, output.len());
                }
                index += 1;
            }
            b'.' => {
                output.push(b'.');
                mark_bre_atom(
                    groups.last_mut().expect("BRE state always has a root"),
                    output.len(),
                );
                index += 1;
            }
            _ => {
                append_literal(&mut output, byte);
                mark_bre_atom(
                    groups.last_mut().expect("BRE state always has a root"),
                    output.len(),
                );
                index += 1;
            }
        }
    }

    if groups.len() == 1 {
        Ok(output)
    } else {
        Err(RegexCompileError)
    }
}

impl RegexMatcher for PosixRegexMatcher {
    fn is_match(&mut self, subject: &[u8]) -> bool {
        let end = subject
            .iter()
            .position(|byte| *byte == 0)
            .unwrap_or(subject.len());
        self.regex
            .as_ref()
            .is_none_or(|regex| !regex.matches(&subject[..end], Some(1)).is_empty())
    }
}

impl RegexCompiler for PosixRegexCompiler {
    fn compile(&mut self, pattern: &[u8]) -> Result<Box<dyn RegexMatcher>, RegexCompileError> {
        let end = pattern
            .iter()
            .position(|byte| *byte == 0)
            .unwrap_or(pattern.len());
        let pattern = &pattern[..end];
        let normalized = normalize_basic_regex(pattern)?;
        if pattern.is_empty() {
            return Ok(Box::new(PosixRegexMatcher { regex: None }));
        }
        let regex = PosixRegexBuilder::new(&normalized)
            .with_default_classes()
            .compile()
            .map_err(|_| RegexCompileError)?;
        Ok(Box::new(PosixRegexMatcher { regex: Some(regex) }))
    }
}

#[cfg(test)]
mod tests {
    use std::collections::VecDeque;
    use std::io::{self, Cursor, Read};

    use super::{InputStream, PosixRegexCompiler, RealInputStream, RegexCompiler, FGETS_CAPACITY};

    enum ReadStep {
        Bytes(Vec<u8>),
        Error(io::Error),
        Eof,
    }

    struct StepReader {
        steps: VecDeque<ReadStep>,
    }

    impl Read for StepReader {
        fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
            match self.steps.pop_front().unwrap_or(ReadStep::Eof) {
                ReadStep::Bytes(bytes) => {
                    assert!(bytes.len() <= buffer.len());
                    buffer[..bytes.len()].copy_from_slice(&bytes);
                    Ok(bytes.len())
                }
                ReadStep::Error(source) => Err(source),
                ReadStep::Eof => Ok(0),
            }
        }
    }

    fn matches(pattern: &[u8], subject: &[u8]) -> bool {
        PosixRegexCompiler
            .compile(pattern)
            .expect("pattern should compile")
            .is_match(subject)
    }

    #[test]
    fn real_input_stream_preserves_fgets_bytes_limits_and_eof_timing() {
        let mut raw = RealInputStream::new(Box::new(Cursor::new(b"\xff\0tail\n".to_vec())));
        let first = raw.read_chunk(FGETS_CAPACITY);
        assert_eq!(first.chunk.expect("raw chunk").consumed, b"\xff\0tail\n");
        assert!(!first.eof);
        assert!(first.error.is_none());
        let exhausted = raw.read_chunk(FGETS_CAPACITY);
        assert!(exhausted.chunk.is_none());
        assert!(exhausted.eof);
        assert!(exhausted.error.is_none());

        let mut exact = RealInputStream::new(Box::new(Cursor::new(vec![b'x'; FGETS_CAPACITY - 1])));
        let full = exact.read_chunk(FGETS_CAPACITY);
        assert_eq!(
            full.chunk.expect("full chunk").consumed,
            vec![b'x'; FGETS_CAPACITY - 1]
        );
        assert!(!full.eof);
        assert!(exact.read_chunk(FGETS_CAPACITY).eof);

        let mut over = RealInputStream::new(Box::new(Cursor::new(vec![b'y'; FGETS_CAPACITY])));
        let full = over.read_chunk(FGETS_CAPACITY);
        assert_eq!(
            full.chunk.expect("first over-limit chunk").consumed,
            vec![b'y'; FGETS_CAPACITY - 1]
        );
        assert!(!full.eof);
        let tail = over.read_chunk(FGETS_CAPACITY);
        assert_eq!(tail.chunk.expect("unterminated tail").consumed, b"y");
        assert!(tail.eof);
    }

    #[test]
    fn real_input_stream_exposes_immediate_and_partial_read_errors() {
        let mut immediate = RealInputStream::new(Box::new(StepReader {
            steps: VecDeque::from([ReadStep::Error(io::Error::other("immediate"))]),
        }));
        let failed = immediate.read_chunk(FGETS_CAPACITY);
        assert!(failed.chunk.is_none());
        assert!(!failed.eof);
        assert_eq!(
            failed.error.expect("immediate error").to_string(),
            "immediate"
        );

        let mut partial = RealInputStream::new(Box::new(StepReader {
            steps: VecDeque::from([
                ReadStep::Bytes(b"partial".to_vec()),
                ReadStep::Error(io::Error::other("after bytes")),
            ]),
        }));
        let failed = partial.read_chunk(FGETS_CAPACITY);
        assert_eq!(failed.chunk.expect("partial chunk").consumed, b"partial");
        assert!(!failed.eof);
        assert_eq!(
            failed.error.expect("partial error").to_string(),
            "after bytes"
        );
    }

    #[test]
    fn bre_dot_matches_any_byte() {
        assert!(matches(b"a.c", b"axc\n"));
    }

    #[test]
    fn bre_literal_space_matches() {
        assert!(matches(b"has space", b"has space\n"));
    }

    #[test]
    fn bre_escaped_alternation_matches() {
        assert!(matches(br"apple\|cherry", b"cherry\n"));
        assert!(matches(br"a\+", b"aaa\n"));
        assert!(matches(br"colou\?r", b"color\n"));
        assert!(matches(br"colou\?r", b"colour\n"));
    }

    #[test]
    fn bre_unescaped_plus_is_literal() {
        assert!(!matches(b"a+", b"aaa\n"));
        assert!(matches(b"a+", b"a+\n"));
    }

    #[test]
    fn bre_unescaped_operators_are_literals() {
        let pattern = b"^a+?|(b){c}$";
        assert!(matches(pattern, b"a+?|(b){c}"));
        assert!(!matches(pattern, b"a+?|(b){c}\n"));
        assert!(!matches(b"a|b", b"a"));
        assert!(matches(b"a|b", b"a|b"));
        assert!(matches(b"(a)", b"(a)"));
    }

    #[test]
    fn bre_dollar_does_not_match_before_newline() {
        assert!(!matches(b"^test$", b"test\n"));
        assert!(matches(b"^test$", b"test"));
    }

    #[test]
    fn bre_anchors_are_contextual() {
        assert!(matches(b"a^b", b"a^b\n"));
        assert!(matches(b"a$b", b"a$b\n"));
        assert!(matches(b"^^a", b"^a"));
        assert!(matches(b"a$$", b"a$"));
        assert!(matches(br"\(^a\|b$\)", b"a"));
        assert!(matches(br"\(^a\|b$\)", b"b"));
        assert!(!matches(br"\(^a\|b$\)", b"xa"));
        assert!(matches(br"\^a", b"^a"));
        assert!(matches(br"a\$", b"a$"));
    }

    #[test]
    fn bre_groups_backreferences_intervals_and_classes() {
        assert!(matches(br"^\([[:alpha:]]\)\1[[:digit:]]\{2,3\}$", b"aa123"));
        assert!(!matches(
            br"^\([[:alpha:]]\)\1[[:digit:]]\{2,3\}$",
            b"ab123"
        ));
        assert!(matches(br"colou\{0,1\}r", b"color"));
        assert!(matches(br"colou\{0,1\}r", b"colour"));
    }

    #[test]
    fn bre_bracket_literals_collation_and_classes() {
        assert!(matches(b"[[]", b"["));
        assert!(matches(b"[]a]", b"]"));
        assert!(matches(b"[]a]", b"a"));
        assert!(matches(b"[^]a]", b"\xff"));
        assert!(!matches(b"[^]a]", b"a"));
        assert!(matches(b"[[.a.]-c]", b"b"));
        assert!(matches(b"[a-[.c.]]", b"c"));
        assert!(matches(b"[[:space:]]", b"\n"));
        assert!(matches(b"[[:punct:]]", b"!"));
        assert!(!matches(b"[[:alpha:]]", b"\xff"));
    }

    #[test]
    fn bre_gnu_escapes_and_interval_edges() {
        assert!(matches(br"\n", b"n"));
        assert!(!matches(br"\n", b"\n"));
        assert!(matches(br"\d", b"d"));
        assert!(!matches(br"\d", b"5"));
        assert!(matches(br"\s", b"\n"));
        assert!(matches(br"\w\+", b"_a9"));
        assert!(matches(br"^\(a\)\10$", b"aa0"));
        assert!(matches(br"^a\{,2\}$", b""));
        assert!(matches(br"^a\{,2\}$", b"aa"));
        assert!(!matches(br"^a\{,2\}$", b"aaa"));
        assert!(matches(br"^a\{,\}$", b"aaa"));
        assert!(matches(br"^a\+\+$", b"aaa"));
        assert!(matches(br"^a*\+$", b""));
        assert!(PosixRegexCompiler.compile(br"a\{2\}\+").is_ok());
        assert!(PosixRegexCompiler.compile(br"a\{2\}\?").is_ok());
    }

    #[test]
    fn bre_empty_invalid_high_byte_and_nul_subjects() {
        assert!(matches(b"", b"anything"));
        assert!(matches(b"\xff", b"x\xffy"));
        assert!(matches(b"a\0[", b"a"));
        assert!(matches(b"abc", b"abc\0ignored"));
        assert!(!matches(b"ignored", b"abc\0ignored"));
        assert!(matches(b"*", b"literal *"));

        for malformed in [
            b"[".as_slice(),
            b"[]",
            b"[[:bogus:]]",
            b"[[.ab.]]",
            br"\(",
            br"\)",
            br"\{2\}",
            br"\{x",
            b"a**",
            b"***",
            br"a\+*",
            br"a\{2}",
            br"a\{2,1\}",
            br"a\{32768\}",
            b"[z-a]",
            br"\",
        ] {
            assert!(
                PosixRegexCompiler.compile(malformed).is_err(),
                "{malformed:?}"
            );
        }
    }
}
