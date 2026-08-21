#![allow(dead_code)]

use std::cmp::Ordering;
use std::ffi::OsStr;
use std::fs::File;
use std::io::{self, BufRead, BufReader, Write};
use std::ops::Range;
use std::os::unix::ffi::OsStrExt;

pub(crate) const EXIT_SUCCESS: u8 = 0;
pub(crate) const EXIT_FAILURE: u8 = 1;
pub(crate) const STDIO_BUFFER_CAPACITY: usize = 4096;
const MIXED_EXIT_BYTE_LIMIT: usize = STDIO_BUFFER_CAPACITY - 16;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct Line {
    bytes: Vec<u8>,
    fields: Vec<Range<usize>>,
}

impl Line {
    fn from_record(mut record: Vec<u8>, delimiter: DelimiterMode) -> Self {
        if record.last() == Some(&b'\n') {
            record.pop();
        }
        let fields = mbssep(&record, delimiter);
        Self {
            bytes: record,
            fields,
        }
    }

    fn field(&self, fieldno: u64) -> Option<&[u8]> {
        let index = usize::try_from(fieldno).ok()?;
        let range = self.fields.get(index)?;
        self.bytes.get(range.clone())
    }
}

pub(crate) struct Input<'a> {
    reader: Box<dyn BufRead + 'a>,
    joinf: u64,
    unpair: bool,
    number: u8,
    set: Vec<Line>,
    lookahead: Option<Line>,
}

impl<'a> Input<'a> {
    fn new(reader: Box<dyn BufRead + 'a>, joinf: u64, unpair: bool, number: u8) -> Self {
        Self {
            reader,
            joinf,
            unpair,
            number,
            set: Vec::new(),
            lookahead: None,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct OList {
    filenum: u8,
    fieldno: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DelimiterMode {
    SpanningWhitespace,
    Exact(u8),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct Config {
    joinout: bool,
    delimiter: DelimiterMode,
    empty: Option<Vec<u8>>,
    olist: Vec<OList>,
    joinf1: u64,
    joinf2: u64,
    unpair1: bool,
    unpair2: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            joinout: true,
            delimiter: DelimiterMode::SpanningWhitespace,
            empty: None,
            olist: Vec::new(),
            joinf1: 0,
            joinf2: 0,
            unpair1: false,
            unpair2: false,
        }
    }
}

#[derive(Debug)]
pub(crate) enum JoinError {
    Usage,
    Message(Vec<u8>),
    Path { path: Vec<u8>, source: io::Error },
    Stdout(io::Error),
    Allocation,
}

type JoinResult<T> = Result<T, JoinError>;

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
enum StreamOrientation {
    #[default]
    Unoriented,
    Byte,
    Wide,
}

#[derive(Debug, Default)]
struct OutputState {
    orientation: StreamOrientation,
    byte_buffer: Vec<u8>,
    wide_buffer: Vec<u8>,
}

impl OutputState {
    fn write_buffered<W: Write + ?Sized>(
        buffer: &mut Vec<u8>,
        mut bytes: &[u8],
        output: &mut W,
    ) -> JoinResult<()> {
        while !bytes.is_empty() {
            if buffer.len() == STDIO_BUFFER_CAPACITY {
                output.write_all(buffer).map_err(JoinError::Stdout)?;
                output.flush().map_err(JoinError::Stdout)?;
                buffer.clear();
            }
            let count = bytes
                .len()
                .min(STDIO_BUFFER_CAPACITY.saturating_sub(buffer.len()));
            buffer
                .try_reserve(count)
                .map_err(|_| JoinError::Allocation)?;
            buffer.extend_from_slice(&bytes[..count]);
            bytes = &bytes[count..];
        }
        Ok(())
    }

    fn separator<W: Write + ?Sized>(&mut self, byte: u8, output: &mut W) -> JoinResult<()> {
        match self.orientation {
            StreamOrientation::Unoriented | StreamOrientation::Wide => {
                self.orientation = StreamOrientation::Wide;
                if self.wide_buffer.len() == STDIO_BUFFER_CAPACITY && !self.byte_buffer.is_empty() {
                    output
                        .write_all(&self.byte_buffer)
                        .map_err(JoinError::Stdout)?;
                    output.flush().map_err(JoinError::Stdout)?;
                    self.byte_buffer.clear();
                }
                Self::write_buffered(&mut self.wide_buffer, &[byte], output)
            }
            StreamOrientation::Byte => Self::write_buffered(&mut self.byte_buffer, &[byte], output),
        }
    }

    fn fputs<W: Write + ?Sized>(&mut self, bytes: &[u8], output: &mut W) -> JoinResult<()> {
        match self.orientation {
            StreamOrientation::Unoriented => {
                self.orientation = StreamOrientation::Byte;
                Self::write_buffered(&mut self.byte_buffer, bytes, output)
            }
            StreamOrientation::Byte => Self::write_buffered(&mut self.byte_buffer, bytes, output),
            StreamOrientation::Wide => Ok(()),
        }
    }

    fn newline<W: Write + ?Sized>(&mut self, output: &mut W) -> JoinResult<()> {
        if self.orientation == StreamOrientation::Unoriented {
            self.orientation = StreamOrientation::Byte;
        }
        Self::write_buffered(&mut self.byte_buffer, b"\n", output)
    }

    fn finish<W: Write + ?Sized>(&mut self, output: &mut W) -> JoinResult<()> {
        // join.c mixes putwchar with byte-oriented stdio. On glibc, a separator
        // written before any byte operation orients stdout wide: later fputs
        // calls are ignored, while byte newlines flush before wide separators.
        let byte_near_full =
            (MIXED_EXIT_BYTE_LIMIT + 1..STDIO_BUFFER_CAPACITY).contains(&self.byte_buffer.len());
        let wide_near_full =
            (MIXED_EXIT_BYTE_LIMIT + 1..STDIO_BUFFER_CAPACITY).contains(&self.wide_buffer.len());
        if self.orientation != StreamOrientation::Wide || !byte_near_full || !wide_near_full {
            let _ = output.write_all(&self.byte_buffer);
        }
        let _ = output.write_all(&self.wide_buffer);
        let _ = output.flush();
        self.byte_buffer.clear();
        self.wide_buffer.clear();
        // The C main returns without fflush, so an error first encountered by
        // the runtime's exit-time flush does not change join's exit status.
        Ok(())
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ProgramNames {
    getopt: Vec<u8>,
    short: Vec<u8>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ParsedArgs {
    config: Config,
    operands: [Vec<u8>; 2],
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct StrtolResult {
    value: i64,
    end: usize,
}

pub(crate) trait FileOpener {
    fn open(&mut self, path: &OsStr) -> io::Result<Box<dyn BufRead>>;
}

pub(crate) struct RealFileOpener;

impl FileOpener for RealFileOpener {
    fn open(&mut self, path: &OsStr) -> io::Result<Box<dyn BufRead>> {
        File::open(path).map(|file| Box::new(BufReader::new(file)) as Box<dyn BufRead>)
    }
}

fn program_names(argv0: &[u8]) -> ProgramNames {
    ProgramNames {
        getopt: argv0.to_vec(),
        short: argv0
            .rsplit(|byte| *byte == b'/')
            .next()
            .unwrap_or(argv0)
            .to_vec(),
    }
}

fn is_historical_output_selector(token: &[u8]) -> bool {
    match token {
        [b'1' | b'2', b'.', rest @ ..] => rest.iter().all(u8::is_ascii_digit),
        _ => false,
    }
}

fn obsolete<W: Write + ?Sized>(
    argv: &mut [Vec<u8>],
    names: &ProgramNames,
    stderr: &mut W,
) -> JoinResult<()> {
    let mut index = 1;
    while index < argv.len() {
        let argument = argv[index].clone();
        if argument.starts_with(b"--") {
            return Ok(());
        }
        if argument.first() != Some(&b'-') || argument.len() < 2 {
            index += 1;
            continue;
        }

        match argument[1] {
            b'a' if argument == b"-a" => {
                let has_file_number = argv
                    .get(index + 1)
                    .is_some_and(|next| next == b"1" || next == b"2");
                if !has_file_number {
                    argv[index][1] = 1;
                    let _ = warnx(
                        names,
                        b"-a option used without an argument; reverting to historical behavior",
                        stderr,
                    );
                }
            }
            b'j' => match argument.get(2).copied() {
                Some(which @ (b'1' | b'2')) if argument.len() == 3 => {
                    argv[index] = vec![b'-', which];
                }
                None => {}
                Some(_) => {
                    let mut message = b"unknown option -- ".to_vec();
                    message.extend_from_slice(&argument[1..]);
                    let _ = warnx(names, &message, stderr);
                    return Err(JoinError::Usage);
                }
            },
            b'o' if argument == b"-o" && index + 1 < argv.len() => {
                let mut next = index + 2;
                while next < argv.len() {
                    let token = &argv[next];
                    if !is_historical_output_selector(token) {
                        break;
                    }
                    let mut rewritten = Vec::with_capacity(token.len() + 2);
                    rewritten.extend_from_slice(b"-o");
                    rewritten.extend_from_slice(token);
                    argv[next] = rewritten;
                    next += 1;
                }
                index = next;
                continue;
            }
            _ => {}
        }
        index += 1;
    }
    Ok(())
}

fn parse_args<W: Write + ?Sized>(
    argv: &[Vec<u8>],
    posixly_correct: bool,
    names: &ProgramNames,
    stderr: &mut W,
) -> JoinResult<ParsedArgs> {
    let mut arguments = argv.to_vec();
    obsolete(&mut arguments, names, stderr)?;

    let mut config = Config::default();
    let mut operands = Vec::new();
    let mut aflag = false;
    let mut vflag = false;
    let mut index = usize::from(!arguments.is_empty());

    while index < arguments.len() {
        let argument = arguments[index].clone();
        if argument == b"--" {
            operands.extend(arguments[index + 1..].iter().cloned());
            break;
        }
        if argument == b"-" || argument.first() != Some(&b'-') {
            if posixly_correct {
                operands.extend(arguments[index..].iter().cloned());
                break;
            }
            operands.push(argument);
            index += 1;
            continue;
        }

        let mut option_offset = 1;
        while argument.get(option_offset) == Some(&1) {
            aflag = true;
            config.unpair1 = true;
            config.unpair2 = true;
            option_offset += 1;
        }
        if option_offset == argument.len() {
            index += 1;
            continue;
        }

        let option = argument[option_offset];
        if !matches!(
            option,
            b'1' | b'2' | b'a' | b'e' | b'j' | b'o' | b't' | b'v'
        ) {
            write_getopt_error(names, b"invalid option -- '", option, stderr);
            return Err(JoinError::Usage);
        }

        let option_argument = if argument.len() > option_offset + 1 {
            index += 1;
            argument[option_offset + 1..].to_vec()
        } else if let Some(value) = arguments.get(index + 1) {
            index += 2;
            value.clone()
        } else {
            write_getopt_error(names, b"option requires an argument -- '", option, stderr);
            return Err(JoinError::Usage);
        };

        match option {
            b'1' | b'2' | b'j' => {
                let parsed = c_strtol(&option_argument);
                let field = parsed.value as u64;
                if field < 1 {
                    let message = match option {
                        b'1' => b"-1 option field number less than 1".as_slice(),
                        b'2' => b"-2 option field number less than 1".as_slice(),
                        _ => b"-j option field number less than 1".as_slice(),
                    };
                    return Err(JoinError::Message(message.to_vec()));
                }
                if parsed.end != option_argument.len() {
                    let mut message = b"illegal field number -- ".to_vec();
                    message.extend_from_slice(&option_argument);
                    return Err(JoinError::Message(message));
                }
                let field = field - 1;
                match option {
                    b'1' => config.joinf1 = field,
                    b'2' => config.joinf2 = field,
                    _ => {
                        config.joinf1 = field;
                        config.joinf2 = field;
                    }
                }
            }
            b'a' | b'v' => {
                if option == b'a' {
                    aflag = true;
                } else {
                    vflag = true;
                    config.joinout = false;
                }
                let parsed = c_strtol(&option_argument);
                match parsed.value {
                    1 => config.unpair1 = true,
                    2 => config.unpair2 = true,
                    _ => {
                        let mut message = vec![b'-', option];
                        message.extend_from_slice(b" option file number not 1 or 2");
                        return Err(JoinError::Message(message));
                    }
                }
                if parsed.end != option_argument.len() {
                    let mut message = b"illegal file number -- ".to_vec();
                    message.extend_from_slice(&option_argument);
                    return Err(JoinError::Message(message));
                }
            }
            b'e' => config.empty = Some(option_argument),
            b'o' => fieldarg(&mut config, &option_argument)?,
            b't' => config.delimiter = validate_delimiter(&option_argument)?,
            _ => unreachable!(),
        }
    }

    if aflag && vflag {
        return Err(JoinError::Message(
            b"the -a and -v options are mutually exclusive".to_vec(),
        ));
    }
    let operands: [Vec<u8>; 2] = operands.try_into().map_err(|_| JoinError::Usage)?;
    Ok(ParsedArgs { config, operands })
}

fn c_strtol(bytes: &[u8]) -> StrtolResult {
    let mut index = 0;
    while bytes
        .get(index)
        .is_some_and(|byte| matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c))
    {
        index += 1;
    }

    let negative = match bytes.get(index) {
        Some(b'-') => {
            index += 1;
            true
        }
        Some(b'+') => {
            index += 1;
            false
        }
        _ => false,
    };
    let digit_start = index;
    let mut magnitude = 0_u128;
    while let Some(byte) = bytes.get(index).filter(|byte| byte.is_ascii_digit()) {
        magnitude = magnitude
            .saturating_mul(10)
            .saturating_add(u128::from(*byte - b'0'));
        index += 1;
    }
    if index == digit_start {
        return StrtolResult { value: 0, end: 0 };
    }

    let value = if negative {
        if magnitude >= (1_u128 << 63) {
            i64::MIN
        } else {
            -(magnitude as i64)
        }
    } else if magnitude > i64::MAX as u128 {
        i64::MAX
    } else {
        magnitude as i64
    };
    StrtolResult { value, end: index }
}

fn fieldarg(config: &mut Config, option: &[u8]) -> JoinResult<()> {
    for token in option.split(|byte| matches!(byte, b',' | b' ' | b'\t')) {
        if token.is_empty() {
            continue;
        }
        let (filenum, fieldno) = if token[0] == b'0' {
            (0, 0)
        } else if token.len() >= 2 && matches!(token[0], b'1' | b'2') && token[1] == b'.' {
            let parsed = c_strtol(&token[2..]);
            let field = parsed.value as u64;
            if parsed.end != token.len() - 2 {
                return Err(JoinError::Message(b"malformed -o option field".to_vec()));
            }
            if field == 0 {
                return Err(JoinError::Message(b"field numbers are 1 based".to_vec()));
            }
            (token[0] - b'0', field - 1)
        } else {
            return Err(JoinError::Message(b"malformed -o option field".to_vec()));
        };
        config
            .olist
            .try_reserve(1)
            .map_err(|_| JoinError::Allocation)?;
        config.olist.push(OList { filenum, fieldno });
    }
    Ok(())
}

fn validate_delimiter(option: &[u8]) -> JoinResult<DelimiterMode> {
    match option {
        [] => Ok(DelimiterMode::Exact(0)),
        [byte] if *byte < 0x80 => Ok(DelimiterMode::Exact(*byte)),
        _ => Err(JoinError::Message(
            b"illegal tab character specification".to_vec(),
        )),
    }
}

fn mbssep(record: &[u8], delimiter: DelimiterMode) -> Vec<Range<usize>> {
    let semantic_len = record
        .iter()
        .position(|byte| *byte == 0)
        .unwrap_or(record.len());
    let record = &record[..semantic_len];
    match delimiter {
        DelimiterMode::SpanningWhitespace => {
            let mut fields = Vec::new();
            let mut start = 0;
            for (index, byte) in record.iter().enumerate() {
                if matches!(byte, b' ' | b'\t') {
                    if start < index {
                        fields.push(start..index);
                    }
                    start = index + 1;
                }
            }
            if start < record.len() {
                fields.push(start..record.len());
            }
            fields
        }
        DelimiterMode::Exact(0) => vec![0..record.len()],
        DelimiterMode::Exact(delimiter) => {
            let mut fields = Vec::new();
            let mut start = 0;
            for (index, byte) in record.iter().enumerate() {
                if *byte == delimiter {
                    fields.push(start..index);
                    start = index + 1;
                }
            }
            fields.push(start..record.len());
            fields
        }
    }
}

fn cmp(lp1: &Line, fieldno1: u64, lp2: &Line, fieldno2: u64) -> Ordering {
    match (lp1.field(fieldno1), lp2.field(fieldno2)) {
        (None, None) => Ordering::Equal,
        (None, Some(_)) => Ordering::Less,
        (Some(_), None) => Ordering::Greater,
        (Some(field1), Some(field2)) => field1.cmp(field2),
    }
}

fn slurp(input: &mut Input<'_>, delimiter: DelimiterMode) -> JoinResult<()> {
    input.set.clear();
    loop {
        let line = if let Some(line) = input.lookahead.take() {
            line
        } else {
            let mut record = Vec::new();
            match input.reader.read_until(b'\n', &mut record) {
                Ok(0) => break,
                Ok(_) => Line::from_record(record, delimiter),
                // The C caller treats getline's -1 result as EOF without checking ferror.
                Err(_read_error) => break,
            }
        };

        if input
            .set
            .last()
            .is_some_and(|last| cmp(&line, input.joinf, last, input.joinf) != Ordering::Equal)
        {
            input.lookahead = Some(line);
            break;
        }
        input
            .set
            .try_reserve(1)
            .map_err(|_| JoinError::Allocation)?;
        input.set.push(line);
    }
    Ok(())
}

fn outfield<W: Write + ?Sized>(
    line: Option<&Line>,
    fieldno: u64,
    out_empty: bool,
    config: &Config,
    needsep: &mut bool,
    state: &mut OutputState,
    output: &mut W,
) -> JoinResult<()> {
    if *needsep {
        let separator = match config.delimiter {
            DelimiterMode::SpanningWhitespace => b' ',
            DelimiterMode::Exact(byte) => byte,
        };
        state.separator(separator, output)?;
    }
    *needsep = true;

    if out_empty {
        if let Some(empty) = &config.empty {
            state.fputs(empty, output)?;
        }
    } else if let Some(field) = line.and_then(|line| line.field(fieldno)) {
        if !field.is_empty() {
            state.fputs(field, output)?;
        }
    } else if let Some(empty) = &config.empty {
        state.fputs(empty, output)?;
    }
    Ok(())
}

fn outoneline<W: Write + ?Sized>(
    input: &Input<'_>,
    line: &Line,
    config: &Config,
    state: &mut OutputState,
    output: &mut W,
) -> JoinResult<()> {
    let mut needsep = false;
    if config.olist.is_empty() {
        outfield(
            Some(line),
            input.joinf,
            false,
            config,
            &mut needsep,
            state,
            output,
        )?;
        for fieldno in 0..line.fields.len() as u64 {
            if fieldno != input.joinf {
                outfield(
                    Some(line),
                    fieldno,
                    false,
                    config,
                    &mut needsep,
                    state,
                    output,
                )?;
            }
        }
    } else {
        for selector in &config.olist {
            if selector.filenum == input.number {
                outfield(
                    Some(line),
                    selector.fieldno,
                    false,
                    config,
                    &mut needsep,
                    state,
                    output,
                )?;
            } else if selector.filenum == 0 {
                outfield(
                    Some(line),
                    input.joinf,
                    false,
                    config,
                    &mut needsep,
                    state,
                    output,
                )?;
            } else {
                outfield(Some(line), 0, true, config, &mut needsep, state, output)?;
            }
        }
    }
    state.newline(output)?;
    Ok(())
}

fn outtwoline<W: Write + ?Sized>(
    input1: &Input<'_>,
    line1: &Line,
    input2: &Input<'_>,
    line2: &Line,
    config: &Config,
    state: &mut OutputState,
    output: &mut W,
) -> JoinResult<()> {
    let mut needsep = false;
    if config.olist.is_empty() {
        outfield(
            Some(line1),
            input1.joinf,
            false,
            config,
            &mut needsep,
            state,
            output,
        )?;
        for fieldno in 0..line1.fields.len() as u64 {
            if fieldno != input1.joinf {
                outfield(
                    Some(line1),
                    fieldno,
                    false,
                    config,
                    &mut needsep,
                    state,
                    output,
                )?;
            }
        }
        for fieldno in 0..line2.fields.len() as u64 {
            if fieldno != input2.joinf {
                outfield(
                    Some(line2),
                    fieldno,
                    false,
                    config,
                    &mut needsep,
                    state,
                    output,
                )?;
            }
        }
    } else {
        for selector in &config.olist {
            match selector.filenum {
                0 => {
                    let (line, fieldno) = if line1.fields.len() as u64 >= input1.joinf {
                        (line1, input1.joinf)
                    } else {
                        (line2, input2.joinf)
                    };
                    outfield(
                        Some(line),
                        fieldno,
                        false,
                        config,
                        &mut needsep,
                        state,
                        output,
                    )?;
                }
                1 => outfield(
                    Some(line1),
                    selector.fieldno,
                    false,
                    config,
                    &mut needsep,
                    state,
                    output,
                )?,
                _ => outfield(
                    Some(line2),
                    selector.fieldno,
                    false,
                    config,
                    &mut needsep,
                    state,
                    output,
                )?,
            }
        }
    }
    state.newline(output)?;
    Ok(())
}

fn joinlines<W: Write + ?Sized>(
    input1: &Input<'_>,
    input2: Option<&Input<'_>>,
    config: &Config,
    state: &mut OutputState,
    output: &mut W,
) -> JoinResult<()> {
    if let Some(input2) = input2 {
        for line1 in &input1.set {
            for line2 in &input2.set {
                outtwoline(input1, line1, input2, line2, config, state, output)?;
            }
        }
        Ok(())
    } else {
        for line in &input1.set {
            outoneline(input1, line, config, state, output)?;
        }
        Ok(())
    }
}

fn merge<W: Write + ?Sized>(
    input1: &mut Input<'_>,
    input2: &mut Input<'_>,
    config: &Config,
    state: &mut OutputState,
    output: &mut W,
) -> JoinResult<()> {
    slurp(input1, config.delimiter)?;
    slurp(input2, config.delimiter)?;
    while !input1.set.is_empty() && !input2.set.is_empty() {
        match cmp(&input1.set[0], input1.joinf, &input2.set[0], input2.joinf) {
            Ordering::Equal => {
                if config.joinout {
                    joinlines(input1, Some(input2), config, state, output)?;
                }
                slurp(input1, config.delimiter)?;
                slurp(input2, config.delimiter)?;
            }
            Ordering::Less => {
                if input1.unpair {
                    joinlines(input1, None, config, state, output)?;
                }
                slurp(input1, config.delimiter)?;
            }
            Ordering::Greater => {
                if input2.unpair {
                    joinlines(input2, None, config, state, output)?;
                }
                slurp(input2, config.delimiter)?;
            }
        }
    }
    if input1.unpair {
        while !input1.set.is_empty() {
            joinlines(input1, None, config, state, output)?;
            slurp(input1, config.delimiter)?;
        }
    }
    if input2.unpair {
        while !input2.set.is_empty() {
            joinlines(input2, None, config, state, output)?;
            slurp(input2, config.delimiter)?;
        }
    }
    Ok(())
}

fn usage<W: Write + ?Sized>(names: &ProgramNames, stderr: &mut W) -> JoinError {
    let _ = stderr.write_all(b"usage: ");
    let _ = stderr.write_all(&names.short);
    let _ =
        stderr.write_all(b" [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n");
    let _ = stderr.write_all(&vec![b' '; names.short.len() + 8]);
    let _ = stderr.write_all(b"[-o list] [-t char] file1 file2\n");
    JoinError::Usage
}

fn warnx<W: Write + ?Sized>(
    names: &ProgramNames,
    message: &[u8],
    stderr: &mut W,
) -> io::Result<()> {
    stderr.write_all(&names.short)?;
    stderr.write_all(b": ")?;
    stderr.write_all(message)?;
    stderr.write_all(b"\n")
}

fn report_error<W: Write + ?Sized>(
    names: &ProgramNames,
    error: &JoinError,
    stderr: &mut W,
) -> io::Result<()> {
    if matches!(error, JoinError::Usage) {
        let _ = usage(names, stderr);
        return Ok(());
    }

    stderr.write_all(&names.short)?;
    match error {
        JoinError::Message(message) => {
            stderr.write_all(b": ")?;
            stderr.write_all(message)?;
        }
        JoinError::Path { path, source } => {
            stderr.write_all(b": ")?;
            stderr.write_all(path)?;
            stderr.write_all(b": ")?;
            write_io_error(source, stderr)?;
        }
        JoinError::Stdout(source) => {
            stderr.write_all(b": stdout: ")?;
            write_io_error(source, stderr)?;
        }
        JoinError::Allocation => stderr.write_all(b": Cannot allocate memory")?,
        JoinError::Usage => unreachable!(),
    }
    stderr.write_all(b"\n")
}

fn write_getopt_error<W: Write + ?Sized>(
    names: &ProgramNames,
    message: &[u8],
    option: u8,
    stderr: &mut W,
) {
    let _ = stderr.write_all(&names.getopt);
    let _ = stderr.write_all(b": ");
    let _ = stderr.write_all(message);
    let _ = stderr.write_all(&[option]);
    let _ = stderr.write_all(b"'\n");
}

fn write_io_error<W: Write + ?Sized>(error: &io::Error, output: &mut W) -> io::Result<()> {
    let mut message = error.to_string();
    if let Some(code) = error.raw_os_error() {
        let suffix = format!(" (os error {code})");
        if message.ends_with(&suffix) {
            message.truncate(message.len() - suffix.len());
        }
    }
    output.write_all(message.as_bytes())
}

fn execute_join<'a>(
    reader1: Box<dyn BufRead + 'a>,
    reader2: Box<dyn BufRead + 'a>,
    config: &Config,
    stdout: &mut dyn Write,
) -> JoinResult<()> {
    let mut input1 = Input::new(reader1, config.joinf1, config.unpair1, 1);
    let mut input2 = Input::new(reader2, config.joinf2, config.unpair2, 2);
    let mut state = OutputState::default();
    merge(&mut input1, &mut input2, config, &mut state, stdout)?;
    state.finish(stdout)
}

pub(crate) fn run(
    argv: &[Vec<u8>],
    posixly_correct: bool,
    stdin: &mut dyn BufRead,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
    opener: &mut dyn FileOpener,
) -> u8 {
    let argv0 = argv.first().map(Vec::as_slice).unwrap_or(b"join");
    let names = program_names(argv0);
    let parsed = match parse_args(argv, posixly_correct, &names, stderr) {
        Ok(parsed) => parsed,
        Err(error) => {
            let _ = report_error(&names, &error, stderr);
            return EXIT_FAILURE;
        }
    };

    let [path1, path2] = parsed.operands;
    let reader1 = if path1 == b"-" {
        None
    } else {
        match opener.open(OsStr::from_bytes(&path1)) {
            Ok(reader) => Some(reader),
            Err(source) => {
                let error = JoinError::Path {
                    path: path1,
                    source,
                };
                let _ = report_error(&names, &error, stderr);
                return EXIT_FAILURE;
            }
        }
    };
    let reader2 = if path2 == b"-" {
        None
    } else {
        match opener.open(OsStr::from_bytes(&path2)) {
            Ok(reader) => Some(reader),
            Err(source) => {
                let error = JoinError::Path {
                    path: path2,
                    source,
                };
                let _ = report_error(&names, &error, stderr);
                return EXIT_FAILURE;
            }
        }
    };

    if reader1.is_none() && reader2.is_none() {
        let error = JoinError::Message(b"only one input file may be stdin".to_vec());
        let _ = report_error(&names, &error, stderr);
        return EXIT_FAILURE;
    }

    let result = match (reader1, reader2) {
        (Some(reader1), Some(reader2)) => execute_join(reader1, reader2, &parsed.config, stdout),
        (None, Some(reader2)) => {
            execute_join(Box::new(&mut *stdin), reader2, &parsed.config, stdout)
        }
        (Some(reader1), None) => {
            execute_join(reader1, Box::new(&mut *stdin), &parsed.config, stdout)
        }
        (None, None) => unreachable!(),
    };
    match result {
        Ok(()) => EXIT_SUCCESS,
        Err(error) => {
            let _ = report_error(&names, &error, stderr);
            EXIT_FAILURE
        }
    }
}

#[cfg(test)]
#[allow(dead_code, unused_imports)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use std::io::{Cursor, ErrorKind, Read};
    use std::os::unix::ffi::OsStrExt;

    enum MockOpenResult {
        Bytes(Vec<u8>),
        Error(ErrorKind),
        RawError(i32),
    }

    #[derive(Default)]
    struct MockFileOpener {
        responses: HashMap<Vec<u8>, MockOpenResult>,
        opened: Vec<Vec<u8>>,
    }

    impl FileOpener for MockFileOpener {
        fn open(&mut self, path: &OsStr) -> io::Result<Box<dyn BufRead>> {
            let key = path.as_bytes().to_vec();
            self.opened.push(key.clone());
            match self.responses.remove(&key) {
                Some(MockOpenResult::Bytes(bytes)) => Ok(Box::new(Cursor::new(bytes))),
                Some(MockOpenResult::Error(kind)) => Err(io::Error::from(kind)),
                Some(MockOpenResult::RawError(code)) => Err(io::Error::from_raw_os_error(code)),
                None => Err(io::Error::new(
                    ErrorKind::NotFound,
                    "unconfigured mock path",
                )),
            }
        }
    }

    struct FailingBufRead {
        kind: ErrorKind,
    }

    impl Read for FailingBufRead {
        fn read(&mut self, _buffer: &mut [u8]) -> io::Result<usize> {
            Err(io::Error::from(self.kind))
        }
    }

    impl BufRead for FailingBufRead {
        fn fill_buf(&mut self) -> io::Result<&[u8]> {
            Err(io::Error::from(self.kind))
        }

        fn consume(&mut self, _amount: usize) {}
    }

    struct FailingWriter {
        kind: ErrorKind,
    }

    impl Write for FailingWriter {
        fn write(&mut self, _buffer: &[u8]) -> io::Result<usize> {
            Err(io::Error::from(self.kind))
        }

        fn flush(&mut self) -> io::Result<()> {
            Err(io::Error::from(self.kind))
        }
    }

    fn argv(arguments: &[&[u8]]) -> Vec<Vec<u8>> {
        arguments.iter().map(|argument| argument.to_vec()).collect()
    }

    fn parse_case(arguments: &[&[u8]], posixly_correct: bool) -> (JoinResult<ParsedArgs>, Vec<u8>) {
        let arguments = argv(arguments);
        let names = program_names(arguments.first().map(Vec::as_slice).unwrap_or(b"join"));
        let mut stderr = Vec::new();
        let result = parse_args(&arguments, posixly_correct, &names, &mut stderr);
        (result, stderr)
    }

    fn line(record: &[u8], delimiter: DelimiterMode) -> Line {
        Line::from_record(record.to_vec(), delimiter)
    }

    fn input(bytes: &[u8], joinf: u64, unpair: bool, number: u8) -> Input<'static> {
        Input::new(Box::new(Cursor::new(bytes.to_vec())), joinf, unpair, number)
    }

    fn merged(file1: &[u8], file2: &[u8], config: &Config) -> Vec<u8> {
        let mut input1 = input(file1, config.joinf1, config.unpair1, 1);
        let mut input2 = input(file2, config.joinf2, config.unpair2, 2);
        let mut state = OutputState::default();
        let mut output = Vec::new();
        merge(&mut input1, &mut input2, config, &mut state, &mut output).unwrap();
        state.finish(&mut output).unwrap();
        output
    }

    fn opener(files: &[(&[u8], &[u8])]) -> MockFileOpener {
        let mut opener = MockFileOpener::default();
        for (path, contents) in files {
            opener
                .responses
                .insert(path.to_vec(), MockOpenResult::Bytes(contents.to_vec()));
        }
        opener
    }

    fn run_case(
        arguments: &[&[u8]],
        stdin_bytes: &[u8],
        opener: &mut MockFileOpener,
    ) -> (u8, Vec<u8>, Vec<u8>) {
        let mut stdin = Cursor::new(stdin_bytes.to_vec());
        let mut stdout = Vec::new();
        let mut stderr = Vec::new();
        let status = run(
            &argv(arguments),
            false,
            &mut stdin,
            &mut stdout,
            &mut stderr,
            opener,
        );
        (status, stdout, stderr)
    }

    mod obsolete_and_parser {
        use super::*;

        #[test]
        fn bare_a_warns_and_enables_both() {
            let (parsed, stderr) = parse_case(&[b"join", b"-a", b"left", b"right"], false);
            let parsed = parsed.unwrap();
            assert!(parsed.config.unpair1);
            assert!(parsed.config.unpair2);
            assert_eq!(parsed.operands, [b"left".to_vec(), b"right".to_vec()]);
            assert_eq!(
                stderr,
                b"join: -a option used without an argument; reverting to historical behavior\n"
            );
        }

        #[test]
        fn bare_a_with_valid_file_argument_is_not_rewritten() {
            let (parsed, stderr) = parse_case(&[b"join", b"-a", b"1", b"left", b"right"], false);
            let parsed = parsed.unwrap();
            assert!(parsed.config.unpair1);
            assert!(!parsed.config.unpair2);
            assert_eq!(parsed.operands, [b"left".to_vec(), b"right".to_vec()]);
            assert!(stderr.is_empty());
        }

        #[test]
        fn j1_and_j2_rewrite_to_join_field_options() {
            let (parsed, _) = parse_case(
                &[b"join", b"-j1", b"2", b"-j2", b"3", b"left", b"right"],
                false,
            );
            let parsed = parsed.unwrap();
            assert_eq!(parsed.config.joinf1, 1);
            assert_eq!(parsed.config.joinf2, 2);
        }

        #[test]
        fn malformed_attached_j_warns_then_uses_usage() {
            let mut files = MockFileOpener::default();
            let (status, stdout, stderr) =
                run_case(&[b"join", b"-j12", b"left", b"right"], b"", &mut files);
            assert_eq!(status, EXIT_FAILURE);
            assert!(stdout.is_empty());
            assert!(files.opened.is_empty());
            assert_eq!(
                stderr,
                concat!(
                    "join: unknown option -- j12\n",
                    "usage: join [-1 field] [-2 field] ",
                    "[-a file_number | -v file_number] [-e string]\n",
                    "            [-o list] [-t char] file1 file2\n"
                )
                .as_bytes()
            );
        }

        #[test]
        fn historical_multi_token_o_appends_selectors() {
            let (parsed, _) = parse_case(
                &[b"join", b"-o", b"1.1", b"2.2", b"1.3", b"left", b"right"],
                false,
            );
            assert_eq!(
                parsed.unwrap().config.olist,
                vec![
                    OList {
                        filenum: 1,
                        fieldno: 0,
                    },
                    OList {
                        filenum: 2,
                        fieldno: 1,
                    },
                    OList {
                        filenum: 1,
                        fieldno: 2,
                    },
                ]
            );
        }

        #[test]
        fn historical_o_only_rewrites_selector_continuations() {
            let (parsed, stderr) =
                parse_case(&[b"join", b"-o", b"1.1", b"0", b"left", b"right"], false);
            assert!(matches!(parsed, Err(JoinError::Usage)));
            assert!(stderr.is_empty());

            let (parsed, stderr) = parse_case(
                &[b"join", b"-o", b"1.1", b"0suffix", b"left", b"right"],
                false,
            );
            assert!(matches!(parsed, Err(JoinError::Usage)));
            assert!(stderr.is_empty());

            let (parsed, stderr) = parse_case(&[b"join", b"-o0suffix", b"left", b"right"], false);
            assert_eq!(
                parsed.unwrap().config.olist,
                vec![OList {
                    filenum: 0,
                    fieldno: 0,
                }]
            );
            assert!(stderr.is_empty());
        }

        #[test]
        fn attached_required_arguments_parse() {
            let (parsed, _) = parse_case(
                &[
                    b"join", b"-12", b"-22", b"-a1", b"-t:", b"-o0,1.2", b"left", b"right",
                ],
                false,
            );
            let config = parsed.unwrap().config;
            assert_eq!((config.joinf1, config.joinf2), (1, 1));
            assert!(config.unpair1);
            assert_eq!(config.delimiter, DelimiterMode::Exact(b':'));
            assert_eq!(config.olist.len(), 2);
        }

        #[test]
        fn raw_historical_marker_continues_the_option_cluster() {
            let (parsed, stderr) = parse_case(&[b"join", b"-\x01v2", b"left", b"right"], false);
            assert!(matches!(
                parsed,
                Err(JoinError::Message(message))
                    if message == b"the -a and -v options are mutually exclusive"
            ));
            assert!(stderr.is_empty());
        }

        #[test]
        fn double_dash_ends_options() {
            let (parsed, _) = parse_case(&[b"join", b"--", b"-v", b"2"], false);
            let parsed = parsed.unwrap();
            assert_eq!(parsed.operands, [b"-v".to_vec(), b"2".to_vec()]);
            assert!(parsed.config.joinout);

            let (parsed, stderr) =
                parse_case(&[b"join", b"--bad", b"-j12", b"left", b"right"], false);
            assert!(matches!(parsed, Err(JoinError::Usage)));
            assert_eq!(stderr, b"join: invalid option -- '-'\n");
        }

        #[test]
        fn unknown_option_uses_full_argv0() {
            let mut files = MockFileOpener::default();
            let (status, stdout, stderr) =
                run_case(&[b"./path/main", b"-x", b"left", b"right"], b"", &mut files);
            assert_eq!(status, EXIT_FAILURE);
            assert!(stdout.is_empty());
            assert!(files.opened.is_empty());
            assert_eq!(
                stderr,
                concat!(
                    "./path/main: invalid option -- 'x'\n",
                    "usage: main [-1 field] [-2 field] ",
                    "[-a file_number | -v file_number] [-e string]\n",
                    "            [-o list] [-t char] file1 file2\n"
                )
                .as_bytes()
            );
        }

        #[test]
        fn missing_option_argument_uses_full_argv0() {
            let mut files = MockFileOpener::default();
            let (status, stdout, stderr) = run_case(&[b"./path/main", b"-v"], b"", &mut files);
            assert_eq!(status, EXIT_FAILURE);
            assert!(stdout.is_empty());
            assert!(files.opened.is_empty());
            assert_eq!(
                stderr,
                concat!(
                    "./path/main: option requires an argument -- 'v'\n",
                    "usage: main [-1 field] [-2 field] ",
                    "[-a file_number | -v file_number] [-e string]\n",
                    "            [-o list] [-t char] file1 file2\n"
                )
                .as_bytes()
            );
        }

        #[test]
        fn non_options_permute_without_posixly_correct() {
            let (parsed, _) = parse_case(&[b"join", b"left", b"-v2", b"right"], false);
            let parsed = parsed.unwrap();
            assert_eq!(parsed.operands, [b"left".to_vec(), b"right".to_vec()]);
            assert!(!parsed.config.joinout);
            assert!(parsed.config.unpair2);
        }

        #[test]
        fn posixly_correct_stops_at_first_operand() {
            let (parsed, _) = parse_case(&[b"join", b"left", b"-v2"], true);
            let parsed = parsed.unwrap();
            assert_eq!(parsed.operands, [b"left".to_vec(), b"-v2".to_vec()]);
            assert!(parsed.config.joinout);
        }

        #[test]
        fn a_and_v_are_mutually_exclusive() {
            let mut files = MockFileOpener::default();
            let (status, stdout, stderr) = run_case(
                &[b"join", b"-a1", b"-v2", b"left", b"right"],
                b"",
                &mut files,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert!(stdout.is_empty());
            assert!(files.opened.is_empty());
            assert_eq!(
                stderr,
                b"join: the -a and -v options are mutually exclusive\n"
            );
        }

        #[test]
        fn repeated_options_apply_in_order() {
            let (parsed, _) = parse_case(
                &[
                    b"join", b"-j", b"2", b"-13", b"-eold", b"-enew", b"-o0", b"-o2.2", b"left",
                    b"right",
                ],
                false,
            );
            let config = parsed.unwrap().config;
            assert_eq!((config.joinf1, config.joinf2), (2, 1));
            assert_eq!(config.empty, Some(b"new".to_vec()));
            assert_eq!(config.olist.len(), 2);
        }

        #[test]
        fn wrong_operand_count_uses_basename_usage() {
            let mut files = MockFileOpener::default();
            let (status, stdout, stderr) = run_case(&[b"./dir/main"], b"", &mut files);
            assert_eq!(status, EXIT_FAILURE);
            assert!(stdout.is_empty());
            assert!(files.opened.is_empty());
            assert_eq!(
                stderr,
                b"usage: main [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n            [-o list] [-t char] file1 file2\n"
            );

            let mut stdin = Cursor::new(Vec::new());
            let mut stdout = Vec::new();
            let mut stderr = FailingWriter {
                kind: ErrorKind::BrokenPipe,
            };
            let mut files = MockFileOpener::default();
            let status = run(
                &argv(&[b"join"]),
                false,
                &mut stdin,
                &mut stdout,
                &mut stderr,
                &mut files,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert!(stdout.is_empty());
            assert!(files.opened.is_empty());
        }
    }

    mod numeric_compatibility {
        use super::*;

        #[test]
        fn strtol_zero_and_no_digits() {
            assert_eq!(c_strtol(b"0"), StrtolResult { value: 0, end: 1 });
            assert_eq!(c_strtol(b"  +x"), StrtolResult { value: 0, end: 0 });

            let (parsed, _) = parse_case(&[b"join", b"-1", b"0", b"left", b"right"], false);
            assert!(matches!(
                parsed,
                Err(JoinError::Message(message))
                    if message == b"-1 option field number less than 1"
            ));
            let (parsed, _) = parse_case(&[b"join", b"-j", b"x", b"left", b"right"], false);
            assert!(matches!(
                parsed,
                Err(JoinError::Message(message))
                    if message == b"-j option field number less than 1"
            ));
        }

        #[test]
        fn strtol_numeric_prefix_reports_end() {
            assert_eq!(c_strtol(b"123xyz"), StrtolResult { value: 123, end: 3 });

            let (parsed, _) = parse_case(&[b"join", b"-2", b"123xyz", b"left", b"right"], false);
            assert!(matches!(
                parsed,
                Err(JoinError::Message(message))
                    if message == b"illegal field number -- 123xyz"
            ));
            let (parsed, _) = parse_case(&[b"join", b"-v", b"1x", b"left", b"right"], false);
            assert!(matches!(
                parsed,
                Err(JoinError::Message(message))
                    if message == b"illegal file number -- 1x"
            ));
            let mut files = MockFileOpener::default();
            let (status, stdout, stderr) = run_case(
                &[b"join", b"-v", b"xyz", b"left", b"right"],
                b"",
                &mut files,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert!(stdout.is_empty());
            assert!(files.opened.is_empty());
            assert_eq!(stderr, b"join: -v option file number not 1 or 2\n");
        }

        #[test]
        fn strtol_whitespace_sign_and_negative_wrap() {
            assert_eq!(c_strtol(b"\t -12"), StrtolResult { value: -12, end: 5 });
            let (parsed, _) = parse_case(&[b"join", b"-1", b"\t -1", b"left", b"right"], false);
            assert_eq!(parsed.unwrap().config.joinf1, u64::MAX - 1);

            let mut config = Config::default();
            fieldarg(&mut config, b"2.-1").unwrap();
            assert_eq!(
                config.olist,
                vec![OList {
                    filenum: 2,
                    fieldno: u64::MAX - 1,
                }]
            );
        }

        #[test]
        fn strtol_saturates_signed_64_overflow() {
            assert_eq!(
                c_strtol(b"999999999999999999999999"),
                StrtolResult {
                    value: i64::MAX,
                    end: 24,
                }
            );
            assert_eq!(
                c_strtol(b"-999999999999999999999999"),
                StrtolResult {
                    value: i64::MIN,
                    end: 25,
                }
            );

            let (parsed, _) = parse_case(
                &[
                    b"join",
                    b"-1",
                    b"999999999999999999999999",
                    b"left",
                    b"right",
                ],
                false,
            );
            assert_eq!(parsed.unwrap().config.joinf1, i64::MAX as u64 - 1);
        }

        #[test]
        fn fieldarg_accepts_leading_zero_suffix() {
            let mut config = Config::default();
            fieldarg(&mut config, b"0suffix,0").unwrap();
            assert_eq!(
                config.olist,
                vec![
                    OList {
                        filenum: 0,
                        fieldno: 0,
                    },
                    OList {
                        filenum: 0,
                        fieldno: 0,
                    },
                ]
            );
        }

        #[test]
        fn fieldarg_rejects_malformed_and_zero_fields() {
            let mut config = Config::default();
            assert!(matches!(
                fieldarg(&mut config, b"3.1"),
                Err(JoinError::Message(message))
                    if message == b"malformed -o option field"
            ));
            assert!(matches!(
                fieldarg(&mut config, b"1.0"),
                Err(JoinError::Message(message))
                    if message == b"field numbers are 1 based"
            ));
            assert!(matches!(
                fieldarg(&mut config, b"1."),
                Err(JoinError::Message(message))
                    if message == b"field numbers are 1 based"
            ));
            assert!(matches!(
                fieldarg(&mut config, b"2.1x"),
                Err(JoinError::Message(message))
                    if message == b"malformed -o option field"
            ));

            let mut config = Config::default();
            fieldarg(&mut config, b", \t").unwrap();
            assert!(config.olist.is_empty());
        }

        #[test]
        fn delimiter_accepts_empty_and_one_byte_values() {
            assert_eq!(validate_delimiter(b"").unwrap(), DelimiterMode::Exact(0));
            assert_eq!(
                validate_delimiter(b":").unwrap(),
                DelimiterMode::Exact(b':')
            );
        }

        #[test]
        fn delimiter_rejects_multibyte_values() {
            assert!(matches!(
                validate_delimiter("é".as_bytes()),
                Err(JoinError::Message(message))
                    if message == b"illegal tab character specification"
            ));
            assert!(validate_delimiter(b"::").is_err());
        }
    }

    mod mbssep_and_line {
        use super::*;

        #[test]
        fn default_split_collapses_space_and_tab() {
            let line = line(b"  alpha\t\tbeta  \n", DelimiterMode::SpanningWhitespace);
            assert_eq!(line.bytes, b"  alpha\t\tbeta  ");
            assert_eq!(line.fields, vec![2..7, 9..13]);
            assert_eq!(line.field(0), Some(b"alpha".as_slice()));
            assert_eq!(line.field(1), Some(b"beta".as_slice()));
            assert_eq!(line.field(2), None);
        }

        #[test]
        fn exact_split_preserves_leading_adjacent_trailing_empty_fields() {
            let line = line(b":a::b:\n", DelimiterMode::Exact(b':'));
            assert_eq!(line.bytes, b":a::b:");
            assert_eq!(line.fields, vec![0..0, 1..2, 3..3, 4..5, 6..6]);
            let fields = (0..5)
                .map(|index| line.field(index).unwrap().to_vec())
                .collect::<Vec<_>>();
            assert_eq!(
                fields,
                vec![
                    b"".to_vec(),
                    b"a".to_vec(),
                    b"".to_vec(),
                    b"b".to_vec(),
                    b"".to_vec()
                ]
            );
            assert_eq!(line.field(5), None);
        }

        #[test]
        fn empty_delimiter_preserves_record() {
            let line = line(b"a b\tc\n", DelimiterMode::Exact(0));
            assert_eq!(line.bytes, b"a b\tc");
            assert_eq!(line.fields, vec![0..5]);
            assert_eq!(line.field(0), Some(b"a b\tc".as_slice()));
            assert_eq!(line.field(1), None);
        }

        #[test]
        fn record_strips_one_lf_and_preserves_cr() {
            let crlf = line(b"a b\r\n", DelimiterMode::SpanningWhitespace);
            assert_eq!(crlf.bytes, b"a b\r");
            assert_eq!(crlf.fields, vec![0..1, 2..4]);
            assert_eq!(crlf.field(1), Some(b"b\r".as_slice()));

            let one_lf = line(b"value\n\n", DelimiterMode::SpanningWhitespace);
            assert_eq!(one_lf.bytes, b"value\n");
            assert_eq!(one_lf.fields, vec![0..6]);
            assert_eq!(one_lf.field(0), Some(b"value\n".as_slice()));
        }

        #[test]
        fn blank_and_unterminated_records() {
            let blank = line(b"\n", DelimiterMode::SpanningWhitespace);
            let unterminated = line(b"key value", DelimiterMode::SpanningWhitespace);
            assert!(blank.bytes.is_empty());
            assert!(blank.fields.is_empty());
            assert_eq!(blank.field(0), None);
            assert_eq!(unterminated.bytes, b"key value");
            assert_eq!(unterminated.fields, vec![0..3, 4..9]);
            assert_eq!(unterminated.field(0), Some(b"key".as_slice()));
            assert_eq!(unterminated.field(1), Some(b"value".as_slice()));
        }

        #[test]
        fn embedded_nul_hides_suffix() {
            let whitespace = line(b"a b\0 hidden fields\n", DelimiterMode::SpanningWhitespace);
            assert_eq!(whitespace.bytes, b"a b\0 hidden fields");
            assert_eq!(whitespace.fields, vec![0..1, 2..3]);
            assert_eq!(whitespace.field(0), Some(b"a".as_slice()));
            assert_eq!(whitespace.field(1), Some(b"b".as_slice()));
            assert_eq!(whitespace.field(2), None);

            let exact = line(b"a:\0ignored:fields\n", DelimiterMode::Exact(b':'));
            assert_eq!(exact.fields, vec![0..1, 2..2]);
            assert_eq!(exact.field(1), Some(b"".as_slice()));
            assert_eq!(exact.field(2), None);
        }

        #[test]
        fn non_utf8_bytes_remain_raw() {
            let line = line(
                &[0xff, b' ', 0x80, b'\n'],
                DelimiterMode::SpanningWhitespace,
            );
            assert_eq!(line.bytes, [0xff, b' ', 0x80]);
            assert_eq!(line.fields, vec![0..1, 2..3]);
            assert_eq!(line.field(0), Some([0xff].as_slice()));
            assert_eq!(line.field(1), Some([0x80].as_slice()));
        }
    }

    mod cmp_and_slurp {
        use super::*;

        #[test]
        fn missing_field_ordering() {
            let missing = line(b"a\n", DelimiterMode::SpanningWhitespace);
            let present = line(b"a value\n", DelimiterMode::SpanningWhitespace);
            let present_empty = line(b":value\n", DelimiterMode::Exact(b':'));
            assert_eq!(cmp(&missing, 1, &present, 1), Ordering::Less);
            assert_eq!(cmp(&present, 1, &missing, 1), Ordering::Greater);
            assert_eq!(cmp(&missing, 1, &missing, 99), Ordering::Equal);
            assert_eq!(cmp(&missing, 1, &present_empty, 0), Ordering::Less);
            assert_eq!(cmp(&present_empty, 0, &missing, 1), Ordering::Greater);
        }

        #[test]
        fn unsigned_byte_lexicographic_order() {
            let high = line(&[0xff, b'\n'], DelimiterMode::SpanningWhitespace);
            let low = line(&[0x7f, b'\n'], DelimiterMode::SpanningWhitespace);
            assert_eq!(cmp(&high, 0, &low, 0), Ordering::Greater);
        }

        #[test]
        fn duplicate_group_with_lookahead() {
            let mut input = input(b"a 1\na 2\nb 3\n", 0, false, 1);

            slurp(&mut input, DelimiterMode::SpanningWhitespace).unwrap();
            assert_eq!(
                input
                    .set
                    .iter()
                    .map(|line| line.field(1).unwrap())
                    .collect::<Vec<_>>(),
                vec![b"1".as_slice(), b"2".as_slice()]
            );
            assert_eq!(
                input.lookahead.as_ref().and_then(|line| line.field(0)),
                Some(b"b".as_slice())
            );

            slurp(&mut input, DelimiterMode::SpanningWhitespace).unwrap();
            assert_eq!(
                input
                    .set
                    .iter()
                    .map(|line| line.field(0).unwrap())
                    .collect::<Vec<_>>(),
                vec![b"b".as_slice()]
            );
            assert!(input.lookahead.is_none());

            slurp(&mut input, DelimiterMode::SpanningWhitespace).unwrap();
            assert!(input.set.is_empty());
            assert!(input.lookahead.is_none());
        }

        #[test]
        fn empty_input_yields_no_group() {
            let mut input = input(b"", 0, false, 1);
            slurp(&mut input, DelimiterMode::SpanningWhitespace).unwrap();
            assert!(input.set.is_empty());
            assert!(input.lookahead.is_none());
        }

        #[test]
        fn huge_field_index_is_missing() {
            let first = line(b"a b\n", DelimiterMode::SpanningWhitespace);
            let other = line(b"c d\n", DelimiterMode::SpanningWhitespace);
            assert_eq!(first.field(u64::MAX), None);
            assert_eq!(cmp(&first, u64::MAX, &other, u64::MAX), Ordering::Equal);
            assert_eq!(cmp(&first, u64::MAX, &other, 0), Ordering::Less);
        }

        #[test]
        fn unsorted_group_order_is_not_corrected() {
            let mut input = input(b"b 1\nb 2\na 3\nb 4\n", 0, false, 1);

            slurp(&mut input, DelimiterMode::SpanningWhitespace).unwrap();
            assert_eq!(input.set.len(), 2);
            assert!(input
                .set
                .iter()
                .all(|line| line.field(0) == Some(b"b".as_slice())));
            assert_eq!(
                input.lookahead.as_ref().and_then(|line| line.field(0)),
                Some(b"a".as_slice())
            );

            slurp(&mut input, DelimiterMode::SpanningWhitespace).unwrap();
            assert_eq!(input.set.len(), 1);
            assert_eq!(input.set[0].field(0), Some(b"a".as_slice()));
            assert_eq!(
                input.lookahead.as_ref().and_then(|line| line.field(0)),
                Some(b"b".as_slice())
            );

            slurp(&mut input, DelimiterMode::SpanningWhitespace).unwrap();
            assert_eq!(input.set.len(), 1);
            assert_eq!(input.set[0].field(0), Some(b"b".as_slice()));
            assert!(input.lookahead.is_none());

            slurp(&mut input, DelimiterMode::SpanningWhitespace).unwrap();
            assert!(input.set.is_empty());
            assert!(input.lookahead.is_none());
        }

        #[test]
        fn read_error_is_compatible_eof() {
            let mut input = Input::new(
                Box::new(FailingBufRead {
                    kind: ErrorKind::Other,
                }),
                0,
                false,
                1,
            );
            slurp(&mut input, DelimiterMode::SpanningWhitespace).unwrap();
            assert!(input.set.is_empty());
            assert!(input.lookahead.is_none());
        }
    }

    mod output_helpers {
        use super::*;

        #[test]
        fn default_matched_layout() {
            let input1 = input(b"", 0, false, 1);
            let input2 = input(b"", 0, false, 2);
            let line1 = line(b"k left extra\n", DelimiterMode::SpanningWhitespace);
            let line2 = line(b"k right\n", DelimiterMode::SpanningWhitespace);
            let mut state = OutputState::default();
            let mut output = Vec::new();
            outtwoline(
                &input1,
                &line1,
                &input2,
                &line2,
                &Config::default(),
                &mut state,
                &mut output,
            )
            .unwrap();
            state.finish(&mut output).unwrap();
            assert_eq!(output, b"k left extra right\n");
        }

        #[test]
        fn default_unpaired_layout() {
            let input = input(b"", 1, true, 1);
            let line = line(b"left key extra\n", DelimiterMode::SpanningWhitespace);
            let mut state = OutputState::default();
            let mut output = Vec::new();
            outoneline(&input, &line, &Config::default(), &mut state, &mut output).unwrap();
            state.finish(&mut output).unwrap();
            assert_eq!(output, b"key left extra\n");
        }

        #[test]
        fn custom_selector_kinds_and_order() {
            let input1 = input(b"", 0, false, 1);
            let input2 = input(b"", 0, false, 2);
            let line1 = line(b"k one\n", DelimiterMode::SpanningWhitespace);
            let line2 = line(b"k dos\n", DelimiterMode::SpanningWhitespace);
            let mut config = Config::default();
            fieldarg(&mut config, b"2.2,0,1.1").unwrap();
            let mut state = OutputState::default();
            let mut output = Vec::new();
            outtwoline(
                &input1,
                &line1,
                &input2,
                &line2,
                &config,
                &mut state,
                &mut output,
            )
            .unwrap();
            state.finish(&mut output).unwrap();
            assert_eq!(output, b"dos k k\n");
        }

        #[test]
        fn repeated_selectors() {
            let input1 = input(b"", 0, false, 1);
            let input2 = input(b"", 0, false, 2);
            let line1 = line(b"k one\n", DelimiterMode::SpanningWhitespace);
            let line2 = line(b"k two\n", DelimiterMode::SpanningWhitespace);
            let mut config = Config::default();
            fieldarg(&mut config, b"0,0,1.2,2.2").unwrap();
            let mut state = OutputState::default();
            let mut output = Vec::new();
            outtwoline(
                &input1,
                &line1,
                &input2,
                &line2,
                &config,
                &mut state,
                &mut output,
            )
            .unwrap();
            state.finish(&mut output).unwrap();
            assert_eq!(output, b"k k one two\n");
        }

        #[test]
        fn missing_and_present_empty_with_replacement() {
            let input = input(b"", 0, true, 1);
            let line = line(b"k::value\n", DelimiterMode::Exact(b':'));
            let mut config = Config {
                delimiter: DelimiterMode::Exact(b':'),
                empty: Some(b"EMPTY".to_vec()),
                ..Config::default()
            };
            fieldarg(&mut config, b"0,1.2,1.4").unwrap();
            let mut state = OutputState::default();
            let mut output = Vec::new();
            outoneline(&input, &line, &config, &mut state, &mut output).unwrap();
            state.finish(&mut output).unwrap();
            assert_eq!(output, b"k::EMPTY\n");
        }

        #[test]
        fn absent_side_replacement() {
            let input1 = input(b"", 0, true, 1);
            let line1 = line(b"k one\n", DelimiterMode::SpanningWhitespace);
            let mut config = Config {
                empty: Some(b"-".to_vec()),
                ..Config::default()
            };
            fieldarg(&mut config, b"0,2.2").unwrap();
            let mut state = OutputState::default();
            let mut output = Vec::new();
            outoneline(&input1, &line1, &config, &mut state, &mut output).unwrap();
            state.finish(&mut output).unwrap();
            assert_eq!(output, b"k -\n");

            let input2 = input(b"", 0, true, 2);
            let line2 = line(b"k two\n", DelimiterMode::SpanningWhitespace);
            config.olist.clear();
            fieldarg(&mut config, b"1.2,0,2.2").unwrap();
            output.clear();
            let mut state = OutputState::default();
            outoneline(&input2, &line2, &config, &mut state, &mut output).unwrap();
            state.finish(&mut output).unwrap();
            assert_eq!(output, b"- k two\n");
        }

        #[test]
        fn doubled_and_trailing_separators() {
            let input1 = input(b"", 0, false, 1);
            let input2 = input(b"", 0, false, 2);
            let line1 = line(b"k\n", DelimiterMode::SpanningWhitespace);
            let line2 = line(b"k value\n", DelimiterMode::SpanningWhitespace);
            let mut config = Config::default();
            fieldarg(&mut config, b"0,1.2,2.3").unwrap();
            let mut state = OutputState::default();
            let mut output = Vec::new();
            outtwoline(
                &input1,
                &line1,
                &input2,
                &line2,
                &config,
                &mut state,
                &mut output,
            )
            .unwrap();
            state.finish(&mut output).unwrap();
            assert_eq!(output, b"k  \n");
        }

        #[test]
        fn exact_delimiter_and_final_lf() {
            let input1 = input(b"", 0, false, 1);
            let input2 = input(b"", 0, false, 2);
            let line1 = line(b"user:100:admin\n", DelimiterMode::Exact(b':'));
            let line2 = line(b"user:active:2024\n", DelimiterMode::Exact(b':'));
            let config = Config {
                delimiter: DelimiterMode::Exact(b':'),
                ..Config::default()
            };
            let mut state = OutputState::default();
            let mut output = Vec::new();
            outtwoline(
                &input1,
                &line1,
                &input2,
                &line2,
                &config,
                &mut state,
                &mut output,
            )
            .unwrap();
            state.finish(&mut output).unwrap();
            assert_eq!(output, b"user:100:admin:active:2024\n");

            let line1 = line(b"key\n", DelimiterMode::Exact(0));
            let line2 = line(b"key\n", DelimiterMode::Exact(0));
            let mut config = Config {
                delimiter: DelimiterMode::Exact(0),
                ..Config::default()
            };
            fieldarg(&mut config, b"0,0").unwrap();
            output.clear();
            let mut state = OutputState::default();
            outtwoline(
                &input1,
                &line1,
                &input2,
                &line2,
                &config,
                &mut state,
                &mut output,
            )
            .unwrap();
            state.finish(&mut output).unwrap();
            assert_eq!(output, b"key\0key\n");
        }

        #[test]
        fn wide_first_separator_matches_mixed_stdio_behavior() {
            let input1 = input(b"", 0, false, 1);
            let input2 = input(b"", 0, false, 2);
            let line1 = line(b"a\n", DelimiterMode::SpanningWhitespace);
            let line2 = line(b"a 2\n", DelimiterMode::SpanningWhitespace);
            let mut config = Config::default();
            fieldarg(&mut config, b"1.2,2.2,0").unwrap();
            let mut state = OutputState::default();
            let mut output = Vec::new();

            outtwoline(
                &input1,
                &line1,
                &input2,
                &line2,
                &config,
                &mut state,
                &mut output,
            )
            .unwrap();
            state.finish(&mut output).unwrap();

            assert_eq!(output, b"\n  ");
        }

        #[test]
        fn empty_missing_replacement_orients_output_as_byte_stream() {
            let input1 = input(b"", 0, false, 1);
            let input2 = input(b"", 0, false, 2);
            let line1 = line(b"a\n", DelimiterMode::SpanningWhitespace);
            let line2 = line(b"a 2\n", DelimiterMode::SpanningWhitespace);
            let mut config = Config {
                empty: Some(Vec::new()),
                ..Config::default()
            };
            fieldarg(&mut config, b"1.2,2.2").unwrap();
            let mut state = OutputState::default();
            let mut output = Vec::new();

            outtwoline(
                &input1,
                &line1,
                &input2,
                &line2,
                &config,
                &mut state,
                &mut output,
            )
            .unwrap();
            state.finish(&mut output).unwrap();

            assert_eq!(output, b" 2\n");
        }

        #[test]
        fn present_empty_first_slot_leaves_output_unoriented() {
            let input1 = input(b"", 0, false, 1);
            let input2 = input(b"", 0, false, 2);
            let line1 = line(b"a::x\n", DelimiterMode::Exact(b':'));
            let line2 = line(b"a:2\n", DelimiterMode::Exact(b':'));
            let mut config = Config {
                delimiter: DelimiterMode::Exact(b':'),
                ..Config::default()
            };
            fieldarg(&mut config, b"1.2,2.2").unwrap();
            let mut state = OutputState::default();
            let mut output = Vec::new();

            outtwoline(
                &input1,
                &line1,
                &input2,
                &line2,
                &config,
                &mut state,
                &mut output,
            )
            .unwrap();
            state.finish(&mut output).unwrap();

            assert_eq!(output, b"\n:");
        }

        #[test]
        fn full_wide_buffer_flushes_before_byte_newline() {
            let mut state = OutputState::default();
            let mut output = Vec::new();
            for _ in 0..STDIO_BUFFER_CAPACITY + 2 {
                state.separator(b' ', &mut output).unwrap();
            }
            state.newline(&mut output).unwrap();
            state.finish(&mut output).unwrap();

            let mut expected = vec![b' '; STDIO_BUFFER_CAPACITY];
            expected.push(b'\n');
            expected.extend_from_slice(b"  ");
            assert_eq!(output, expected);
        }

        #[test]
        fn wide_overflow_flushes_pending_byte_buffer_first() {
            let mut state = OutputState::default();
            let mut output = Vec::new();
            for _ in 0..STDIO_BUFFER_CAPACITY {
                state.separator(b' ', &mut output).unwrap();
            }
            state.newline(&mut output).unwrap();
            state.separator(b' ', &mut output).unwrap();
            state.finish(&mut output).unwrap();

            let mut expected = b"\n".to_vec();
            expected.extend(vec![b' '; STDIO_BUFFER_CAPACITY + 1]);
            assert_eq!(output, expected);
        }

        #[test]
        fn mixed_full_buffers_flush_byte_then_wide_at_exit() {
            let mut state = OutputState::default();
            let mut output = Vec::new();
            for _ in 0..STDIO_BUFFER_CAPACITY {
                state.separator(b' ', &mut output).unwrap();
                state.newline(&mut output).unwrap();
            }
            state.finish(&mut output).unwrap();

            let mut expected = vec![b'\n'; STDIO_BUFFER_CAPACITY];
            expected.extend(vec![b' '; STDIO_BUFFER_CAPACITY]);
            assert_eq!(output, expected);
        }

        #[test]
        fn mixed_near_full_byte_buffer_is_lost_at_exit() {
            let count = MIXED_EXIT_BYTE_LIMIT + 1;
            let mut state = OutputState::default();
            let mut output = Vec::new();
            for _ in 0..count {
                state.separator(b' ', &mut output).unwrap();
                state.newline(&mut output).unwrap();
            }
            state.finish(&mut output).unwrap();

            assert_eq!(output, vec![b' '; count]);
        }

        #[test]
        fn wide_exit_flush_failure_does_not_change_status() {
            let mut state = OutputState::default();
            let mut buffered_output = std::io::BufWriter::with_capacity(
                4,
                FailingWriter {
                    kind: ErrorKind::BrokenPipe,
                },
            );
            state.separator(b' ', &mut buffered_output).unwrap();
            for _ in 0..4 {
                state.newline(&mut buffered_output).unwrap();
            }

            state.finish(&mut buffered_output).unwrap();
            assert_eq!(buffered_output.buffer(), b" ");
        }

        #[test]
        fn output_failure_is_stdout_error() {
            let input = input(b"", 0, true, 1);
            let mut record = b"k ".to_vec();
            record.extend(vec![b'x'; STDIO_BUFFER_CAPACITY]);
            record.push(b'\n');
            let line = line(&record, DelimiterMode::SpanningWhitespace);
            let mut output = FailingWriter {
                kind: ErrorKind::BrokenPipe,
            };
            let mut state = OutputState::default();

            let error =
                outoneline(&input, &line, &Config::default(), &mut state, &mut output).unwrap_err();
            assert!(
                matches!(error, JoinError::Stdout(source) if source.kind() == ErrorKind::BrokenPipe)
            );
        }
    }

    mod merge_engine {
        use super::*;

        #[test]
        fn one_to_one() {
            assert_eq!(
                merged(b"a left\n", b"a right\n", &Config::default()),
                b"a left right\n"
            );
        }

        #[test]
        fn many_to_many_file1_major() {
            assert_eq!(
                merged(b"a 1\na 2\n", b"a 10\na 20\n", &Config::default()),
                b"a 1 10\na 1 20\na 2 10\na 2 20\n"
            );
        }

        #[test]
        fn advances_lower_side() {
            assert_eq!(
                merged(
                    b"a ignored\nb left\n",
                    b"b right\nc ignored\n",
                    &Config::default()
                ),
                b"b left right\n"
            );
        }

        #[test]
        fn drains_remaining_enabled_groups() {
            let config = Config {
                unpair2: true,
                ..Config::default()
            };
            assert_eq!(
                merged(b"a left\n", b"a right\nc tail\n", &config),
                b"a left right\nc tail\n"
            );
        }

        #[test]
        fn a_one_and_both() {
            let file1 = b"a 1\nb 2\n";
            let file2 = b"b 20\nc 30\n";
            let file1_only = Config {
                unpair1: true,
                ..Config::default()
            };
            assert_eq!(merged(file1, file2, &file1_only), b"a 1\nb 2 20\n");

            let both = Config {
                unpair1: true,
                unpair2: true,
                ..Config::default()
            };
            assert_eq!(merged(file1, file2, &both), b"a 1\nb 2 20\nc 30\n");
        }

        #[test]
        fn v_one_and_both() {
            let file2_only = Config {
                joinout: false,
                unpair2: true,
                ..Config::default()
            };
            assert_eq!(
                merged(b"dup 1\ndup 2\n", b"dup a\ndup b\nother x\n", &file2_only),
                b"other x\n"
            );

            let both = Config {
                joinout: false,
                unpair1: true,
                unpair2: true,
                ..Config::default()
            };
            assert_eq!(
                merged(b"a 1\nb 2\n", b"b 20\nc 30\n", &both),
                b"a 1\nc 30\n"
            );
        }

        #[test]
        fn both_selected_fields_missing() {
            let config = Config {
                joinf1: 9,
                joinf2: 9,
                ..Config::default()
            };
            assert_eq!(
                merged(b"a 1\nb 2\n", b"x 3\ny 4\n", &config),
                b"\n\n\n\n                "
            );
        }

        #[test]
        fn no_matches_and_empty_files() {
            assert!(merged(b"a 1\n", b"b 2\n", &Config::default()).is_empty());
            assert!(merged(b"", b"", &Config::default()).is_empty());

            let file1_only = Config {
                unpair1: true,
                ..Config::default()
            };
            assert_eq!(merged(b"a 1\n", b"", &file1_only), b"a 1\n");

            let file2_only = Config {
                unpair2: true,
                ..Config::default()
            };
            assert_eq!(merged(b"", b"b 2\n", &file2_only), b"b 2\n");

            let both = Config {
                unpair1: true,
                unpair2: true,
                ..Config::default()
            };
            assert_eq!(merged(b"a 1\n", b"b 2\n", &both), b"a 1\nb 2\n");
        }
    }

    mod process_orchestration {
        use super::*;

        #[test]
        fn first_and_second_open_order() {
            let first = b"first\xff";
            let second = b"second\xfe";
            let mut files = opener(&[(first, b"a 1"), (second, b"a 2")]);
            let (status, output, stderr) = run_case(&[b"join", first, second], b"", &mut files);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(output, b"a 1 2\n");
            assert!(stderr.is_empty());
            assert_eq!(files.opened, vec![first.to_vec(), second.to_vec()]);
        }

        #[test]
        fn first_open_failure_precedes_second() {
            let mut files = MockFileOpener::default();
            files
                .responses
                .insert(b"missing".to_vec(), MockOpenResult::RawError(2));
            files
                .responses
                .insert(b"second".to_vec(), MockOpenResult::Bytes(b"a 2\n".to_vec()));
            let (status, output, stderr) =
                run_case(&[b"./main", b"missing", b"second"], b"", &mut files);
            assert_eq!(status, EXIT_FAILURE);
            assert!(output.is_empty());
            assert_eq!(files.opened, vec![b"missing".to_vec()]);
            assert_eq!(stderr, b"main: missing: No such file or directory\n");
        }

        #[test]
        fn stdin_as_either_operand() {
            let mut files = opener(&[(b"right", b"a file\n")]);
            let (status, output, _) =
                run_case(&[b"join", b"-", b"right"], b"a stdin\n", &mut files);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(output, b"a stdin file\n");

            let mut files = opener(&[(b"left", b"a file\n")]);
            let (status, output, _) = run_case(&[b"join", b"left", b"-"], b"a stdin\n", &mut files);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(output, b"a file stdin\n");
        }

        #[test]
        fn double_stdin_rejected_after_setup_order() {
            let mut files = MockFileOpener::default();
            let (status, output, stderr) = run_case(&[b"join", b"-", b"-"], b"a 1\n", &mut files);
            assert_eq!(status, EXIT_FAILURE);
            assert!(output.is_empty());
            assert!(files.opened.is_empty());
            assert_eq!(stderr, b"join: only one input file may be stdin\n");
        }

        #[test]
        fn full_argv0_vs_basename_diagnostics() {
            let mut files = MockFileOpener::default();
            let (status, _, stderr) =
                run_case(&[b"./bin/main", b"-x", b"left", b"right"], b"", &mut files);
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(
                stderr,
                b"./bin/main: invalid option -- 'x'\nusage: main [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n            [-o list] [-t char] file1 file2\n"
            );

            let (status, _, stderr) = run_case(
                &[b"./bin/main", b"-v", b"xyz", b"left", b"right"],
                b"",
                &mut files,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stderr, b"main: -v option file number not 1 or 2\n");
        }

        #[test]
        fn wrong_operand_usage() {
            let mut files = MockFileOpener::default();
            let (status, output, stderr) = run_case(&[b"join", b"only-one"], b"", &mut files);
            assert_eq!(status, EXIT_FAILURE);
            assert!(output.is_empty());
            assert_eq!(
                stderr,
                b"usage: join [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n            [-o list] [-t char] file1 file2\n"
            );
        }

        #[test]
        fn stdout_failure_visibility_matches_source() {
            let mut large_left = b"a ".to_vec();
            large_left.extend(vec![b'x'; STDIO_BUFFER_CAPACITY]);
            large_left.push(b'\n');
            let mut files = opener(&[(b"left", &large_left), (b"right", b"a 2\n")]);
            let mut stdin = Cursor::new(Vec::new());
            let mut stdout = FailingWriter {
                kind: ErrorKind::BrokenPipe,
            };
            let mut stderr = Vec::new();
            let status = run(
                &argv(&[b"main", b"left", b"right"]),
                false,
                &mut stdin,
                &mut stdout,
                &mut stderr,
                &mut files,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stderr, b"main: stdout: broken pipe\n");

            let mut files = opener(&[(b"left", b"a 1\n"), (b"right", b"a 2\n")]);
            let mut stdout = std::io::BufWriter::new(FailingWriter {
                kind: ErrorKind::BrokenPipe,
            });
            let mut stderr = Vec::new();
            let status = run(
                &argv(&[b"main", b"left", b"right"]),
                false,
                &mut stdin,
                &mut stdout,
                &mut stderr,
                &mut files,
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout.buffer(), b"a 1 2\n");
            assert!(stderr.is_empty());
        }

        #[test]
        fn in_memory_end_to_end_default_join() {
            let mut files = opener(&[
                (b"left", b"1 first\n2 second\n3 third\n5 fifth\n8 eighth\n"),
                (b"right", b"2 dos\n4 cuatro\n5 cinco\n6 seis\n8 ocho\n"),
            ]);
            let (status, output, stderr) = run_case(&[b"join", b"left", b"right"], b"", &mut files);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(output, b"2 second dos\n5 fifth cinco\n8 eighth ocho\n");
            assert!(stderr.is_empty());
        }

        #[test]
        fn reported_raw_string_key_cases() {
            let cases: &[(&[u8], &[u8], &[u8])] = &[
                (
                    b"caf\xc3\xa9 1\nna\xc3\xafve 2\nr\xc3\xa9sum\xc3\xa9 3\n",
                    b"caf\xc3\xa9 10\nnaive 20\nresume 30\n",
                    b"caf\xc3\xa9 1 10\n",
                ),
                (
                    b"001 alpha\n002 beta\n010 gamma\n",
                    b"001 uno\n003 tres\n010 diez\n",
                    b"001 alpha uno\n010 gamma diez\n",
                ),
                (
                    b"1.5 data1\n2.7 data2\n3.14159 pi\n",
                    b"1.5 info1\n2.8 info2\n3.14159 circle\n",
                    b"1.5 data1 info1\n3.14159 pi circle\n",
                ),
            ];

            for (left, right, expected) in cases {
                let mut files = opener(&[(b"left", left), (b"right", right)]);
                let (status, output, stderr) =
                    run_case(&[b"join", b"left", b"right"], b"", &mut files);
                assert_eq!(status, EXIT_SUCCESS);
                assert_eq!(&output, expected);
                assert!(stderr.is_empty());
            }
        }

        #[test]
        fn reported_duplicate_and_unpaired_cases() {
            let mut files = opener(&[
                (b"left", b"a 1\na 2\nb 3\nb 4\nc 5\n"),
                (b"right", b"a 10\na 20\nb 30\nd 40\n"),
            ]);
            let (status, output, _) = run_case(&[b"join", b"left", b"right"], b"", &mut files);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(output, b"a 1 10\na 1 20\na 2 10\na 2 20\nb 3 30\nb 4 30\n");

            let mut files = opener(&[
                (b"left", b"a 1 extra\nb\nc 3 more data\n"),
                (b"right", b"a 10\nb 20 extra\nd\n"),
            ]);
            let (status, output, _) =
                run_case(&[b"join", b"-a", b"1", b"left", b"right"], b"", &mut files);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(output, b"a 1 extra 10\nb 20 extra\nc 3 more data\n");

            let mut files = opener(&[
                (b"left", b"dup 1\ndup 2\ndup 3\ndup 4\ndup 5\n"),
                (b"right", b"dup a\ndup b\ndup c\nother x\n"),
            ]);
            let (status, output, _) =
                run_case(&[b"join", b"-v", b"2", b"left", b"right"], b"", &mut files);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(output, b"other x\n");
        }

        #[test]
        fn reported_custom_output_cases() {
            let left = b"a 1\nb 2\nc 3\n";
            let right = b"a 1\nb 4\nd 4\n";
            let mut files = opener(&[(b"left", left), (b"right", right)]);
            let (status, output, _) = run_case(
                &[b"join", b"-o", b"2.2,0,1.1", b"left", b"right"],
                b"",
                &mut files,
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(output, b"1 a a\n4 b b\n");

            let mut files = opener(&[(b"left", left), (b"right", right)]);
            let (status, output, _) = run_case(
                &[b"join", b"-o", b"0,0,1.2,2.2", b"left", b"right"],
                b"",
                &mut files,
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(output, b"a a 1 1\nb b 2 4\n");

            let mut files = opener(&[
                (b"left", b"a 1 extra\nb\nc 3 more data\n"),
                (b"right", b"a 10\nb 20 extra\nd\n"),
            ]);
            let (status, output, _) = run_case(
                &[b"join", b"-o", b"0,1.2,2.3", b"left", b"right"],
                b"",
                &mut files,
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(output, b"a 1 \nb  extra\n");
        }

        #[test]
        fn reported_delimiter_and_independent_field_cases() {
            let mut files = opener(&[
                (
                    b"left",
                    b"user1:1001:admin\nuser2:1002:user\nuser3:1003:guest\n",
                ),
                (
                    b"right",
                    b"user1:active:2023\nuser2:inactive:2022\nuser4:pending:2024\n",
                ),
            ]);
            let (status, output, _) =
                run_case(&[b"join", b"-t", b":", b"left", b"right"], b"", &mut files);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(
                output,
                b"user1:1001:admin:active:2023\nuser2:1002:user:inactive:2022\n"
            );

            let mut files = opener(&[
                (b"left", b"a 1 2 3 4 5\nb 6 7 8 9 10\nc 11 12 13 14 15\n"),
                (
                    b"right",
                    b"a 20 21 22 23 24\nb 25 26 27 28 29\nd 30 31 32 33 34\n",
                ),
            ]);
            let (status, output, stderr) = run_case(
                &[b"join", b"-1", b"3", b"-2", b"4", b"left", b"right"],
                b"",
                &mut files,
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert!(output.is_empty());
            assert!(stderr.is_empty());
        }
    }
}
