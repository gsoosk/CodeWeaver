#![forbid(unsafe_code)]
#![allow(dead_code)]

use std::cmp::Ordering;
use std::ffi::OsString;
use std::fs::File;
use std::io::{self, BufRead, BufReader, Write};
use std::ops::Range;
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::path::PathBuf;

const EXIT_SUCCESS: i32 = 0;
const EXIT_FAILURE: i32 = 1;

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct Line {
    bytes: Vec<u8>,
    fields: Vec<Range<usize>>,
}

impl Line {
    fn field(&self, index: usize) -> Option<&[u8]> {
        self.fields
            .get(index)
            .map(|range| &self.bytes[range.clone()])
    }
}

struct Input<R: BufRead> {
    reader: R,
    joinf: usize,
    unpair: bool,
    number: u8,
    set: Vec<Line>,
    pushback: Option<Line>,
    terminal: bool,
}

impl<R: BufRead> Input<R> {
    fn new(reader: R, options: &InputOptions) -> Self {
        Self {
            reader,
            joinf: options.joinf,
            unpair: options.unpair,
            number: options.number,
            set: Vec::new(),
            pushback: None,
            terminal: false,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct InputOptions {
    joinf: usize,
    unpair: bool,
    number: u8,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct OList {
    filenum: u8,
    fieldno: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum Delimiter {
    SpanningWhitespace,
    Exact(Option<u8>),
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Config {
    input1: InputOptions,
    input2: InputOptions,
    joinout: bool,
    delimiter: Delimiter,
    empty: Option<Vec<u8>>,
    olist: Vec<OList>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            input1: InputOptions {
                joinf: 0,
                unpair: false,
                number: 1,
            },
            input2: InputOptions {
                joinf: 0,
                unpair: false,
                number: 2,
            },
            joinout: true,
            delimiter: Delimiter::SpanningWhitespace,
            empty: None,
            olist: Vec::new(),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ProgramNames {
    invocation: Vec<u8>,
    short: Vec<u8>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ParsedArgs {
    names: ProgramNames,
    config: Config,
    operands: [Vec<u8>; 2],
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct CLong {
    signed: i64,
    unsigned: u64,
    end: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum StreamOrientation {
    Unoriented,
    Byte,
    Wide,
}

#[derive(Debug)]
struct OutputState {
    needsep: usize,
    orientation: StreamOrientation,
    byte_side: Vec<u8>,
    wide_side: Vec<u8>,
}

impl Default for OutputState {
    fn default() -> Self {
        Self {
            needsep: 0,
            orientation: StreamOrientation::Unoriented,
            byte_side: Vec::new(),
            wide_side: Vec::new(),
        }
    }
}

#[derive(Debug)]
enum ParseFailure {
    Usage,
    Message(Vec<u8>),
    GetoptThenUsage(Vec<u8>),
}

#[derive(Debug)]
enum RunFailure {
    Parse(ParseFailure),
    Open { path: Vec<u8>, source: io::Error },
    Stdout(io::Error),
    Allocation,
}

trait InputOpener {
    fn open(&mut self, path: &[u8]) -> io::Result<Box<dyn BufRead>>;
}

struct FileInputOpener;

impl InputOpener for FileInputOpener {
    fn open(&mut self, path: &[u8]) -> io::Result<Box<dyn BufRead>> {
        let path = PathBuf::from(OsString::from_vec(path.to_vec()));
        Ok(Box::new(BufReader::new(File::open(path)?)))
    }
}

fn raw_os_args(args: &[OsString]) -> Result<Vec<Vec<u8>>, RunFailure> {
    Ok(args
        .iter()
        .map(|argument| argument.as_os_str().as_bytes().to_vec())
        .collect())
}

fn program_names(args: &[Vec<u8>]) -> Result<ProgramNames, RunFailure> {
    let invocation = args.first().cloned().unwrap_or_default();
    let short = invocation
        .rsplit(|byte| *byte == b'/')
        .next()
        .unwrap_or(&invocation)
        .to_vec();
    Ok(ProgramNames { invocation, short })
}

fn parse_c_long(argument: &[u8]) -> CLong {
    let mut cursor = 0;
    while argument
        .get(cursor)
        .is_some_and(|byte| matches!(*byte, b' ' | b'\t' | b'\n' | b'\x0b' | b'\x0c' | b'\r'))
    {
        cursor += 1;
    }

    let negative = match argument.get(cursor) {
        Some(b'+') => {
            cursor += 1;
            false
        }
        Some(b'-') => {
            cursor += 1;
            true
        }
        _ => false,
    };
    let digits_start = cursor;
    let limit = if negative {
        (i64::MAX as u128) + 1
    } else {
        i64::MAX as u128
    };
    let mut magnitude = 0_u128;
    let mut overflow = false;

    while let Some(byte @ b'0'..=b'9') = argument.get(cursor) {
        let digit = u128::from(*byte - b'0');
        if magnitude > (limit.saturating_sub(digit)) / 10 {
            overflow = true;
        } else if !overflow {
            magnitude = magnitude * 10 + digit;
        }
        cursor += 1;
    }

    if cursor == digits_start {
        return CLong {
            signed: 0,
            unsigned: 0,
            end: 0,
        };
    }

    let signed = if overflow {
        if negative {
            i64::MIN
        } else {
            i64::MAX
        }
    } else if negative {
        if magnitude == (i64::MAX as u128) + 1 {
            i64::MIN
        } else {
            -(magnitude as i64)
        }
    } else {
        magnitude as i64
    };

    CLong {
        signed,
        unsigned: signed as u64,
        end: cursor,
    }
}

fn obsolete<W: Write>(
    args: &mut Vec<Vec<u8>>,
    names: &ProgramNames,
    stderr: &mut W,
) -> Result<(), RunFailure> {
    let mut index = 1;
    while index < args.len() {
        if args[index].starts_with(b"--") {
            break;
        }
        if args[index].first() != Some(&b'-') {
            index += 1;
            continue;
        }

        match args[index].get(1).copied() {
            Some(b'a') => {
                if args[index].len() == 2
                    && !matches!(args.get(index + 1).map(Vec::as_slice), Some(b"1" | b"2"))
                {
                    args[index][1] = b'\x01';
                    let _ = stderr.write_all(&names.short);
                    let _ = stderr.write_all(
                        b": -a option used without an argument; reverting to historical behavior\n",
                    );
                }
            }
            Some(b'j') => match args[index].get(2).copied() {
                Some(which @ (b'1' | b'2')) if args[index].len() == 3 => {
                    args[index] = vec![b'-', which];
                }
                None => {}
                _ => {
                    let _ = stderr.write_all(&names.short);
                    let _ = stderr.write_all(b": unknown option -- ");
                    let _ = stderr.write_all(&args[index][1..]);
                    let _ = stderr.write_all(b"\n");
                    return Err(RunFailure::Parse(ParseFailure::Usage));
                }
            },
            Some(b'o') if args[index].len() == 2 && index + 1 < args.len() => {
                let mut following = index + 2;
                while following < args.len() {
                    let token = &args[following];
                    if token.first() == Some(&b'0')
                        || token.len() < 2
                        || !matches!(token[0], b'1' | b'2')
                        || token[1] != b'.'
                        || !token[2..].iter().all(u8::is_ascii_digit)
                    {
                        break;
                    }

                    let mut rewritten = Vec::with_capacity(token.len() + 2);
                    rewritten.extend_from_slice(b"-o");
                    rewritten.extend_from_slice(token);
                    args[following] = rewritten;
                    following += 1;
                }
                index = following;
                continue;
            }
            _ => {}
        }
        index += 1;
    }
    Ok(())
}

fn fieldarg(option: &[u8], olist: &mut Vec<OList>) -> Result<(), ParseFailure> {
    for token in option.split(|byte| matches!(*byte, b',' | b' ' | b'\t')) {
        if token.is_empty() {
            continue;
        }

        let selector = if token[0] == b'0' {
            OList {
                filenum: 0,
                fieldno: 0,
            }
        } else if token.len() >= 2 && matches!(token[0], b'1' | b'2') && token[1] == b'.' {
            let parsed = parse_c_long(&token[2..]);
            if parsed.end != token.len() - 2 {
                return Err(ParseFailure::Message(b"malformed -o option field".to_vec()));
            }
            if parsed.unsigned == 0 {
                return Err(ParseFailure::Message(b"field numbers are 1 based".to_vec()));
            }
            OList {
                filenum: token[0] - b'0',
                fieldno: parsed.unsigned.wrapping_sub(1) as usize,
            }
        } else {
            return Err(ParseFailure::Message(b"malformed -o option field".to_vec()));
        };
        olist.push(selector);
    }
    Ok(())
}

fn message_with_argument(prefix: &[u8], argument: &[u8]) -> ParseFailure {
    let mut message = Vec::with_capacity(prefix.len() + argument.len());
    message.extend_from_slice(prefix);
    message.extend_from_slice(argument);
    ParseFailure::Message(message)
}

fn getopt_failure(names: &ProgramNames, option: u8, missing_argument: bool) -> ParseFailure {
    let text: &[u8] = if missing_argument {
        b": option requires an argument -- '"
    } else {
        b": invalid option -- '"
    };
    let mut message = Vec::with_capacity(names.invocation.len() + text.len() + 3);
    message.extend_from_slice(&names.invocation);
    message.extend_from_slice(text);
    message.push(option);
    message.extend_from_slice(b"'\n");
    ParseFailure::GetoptThenUsage(message)
}

fn parse_options(
    args: Vec<Vec<u8>>,
    names: ProgramNames,
    posixly_correct: bool,
) -> Result<ParsedArgs, ParseFailure> {
    let mut config = Config::default();
    let mut aflag = false;
    let mut vflag = false;
    let mut operands = Vec::new();
    let mut parse_options = true;
    let mut index = 1;

    while index < args.len() {
        let argument = args[index].clone();
        if !parse_options {
            operands.push(argument);
            index += 1;
            continue;
        }
        if argument == b"--" {
            parse_options = false;
            index += 1;
            continue;
        }
        if argument.len() < 2 || argument[0] != b'-' {
            if posixly_correct {
                operands.extend(args[index..].iter().cloned());
                break;
            }
            operands.push(argument);
            index += 1;
            continue;
        }
        if argument == b"-" {
            if posixly_correct {
                operands.extend(args[index..].iter().cloned());
                break;
            }
            operands.push(argument);
            index += 1;
            continue;
        }

        let mut option_index = 1;
        while option_index < argument.len() {
            let option = argument[option_index];
            option_index += 1;

            if option == b'\x01' {
                aflag = true;
                config.input1.unpair = true;
                config.input2.unpair = true;
                continue;
            }

            if !matches!(
                option,
                b'a' | b'e' | b'j' | b'1' | b'2' | b'o' | b't' | b'v'
            ) {
                return Err(getopt_failure(&names, option, false));
            }

            let option_argument = if option_index < argument.len() {
                argument[option_index..].to_vec()
            } else {
                index += 1;
                if index >= args.len() {
                    return Err(getopt_failure(&names, option, true));
                }
                args[index].clone()
            };
            option_index = argument.len();

            match option {
                b'1' | b'2' | b'j' => {
                    let parsed = parse_c_long(&option_argument);
                    if parsed.unsigned < 1 {
                        let message = match option {
                            b'1' => b"-1 option field number less than 1".as_slice(),
                            b'2' => b"-2 option field number less than 1".as_slice(),
                            _ => b"-j option field number less than 1".as_slice(),
                        };
                        return Err(ParseFailure::Message(message.to_vec()));
                    }
                    if parsed.end != option_argument.len() {
                        return Err(message_with_argument(
                            b"illegal field number -- ",
                            &option_argument,
                        ));
                    }
                    let field = parsed.unsigned.wrapping_sub(1) as usize;
                    if option == b'1' || option == b'j' {
                        config.input1.joinf = field;
                    }
                    if option == b'2' || option == b'j' {
                        config.input2.joinf = field;
                    }
                }
                b'a' | b'v' => {
                    let parsed = parse_c_long(&option_argument);
                    if option == b'a' {
                        aflag = true;
                    } else {
                        vflag = true;
                        config.joinout = false;
                    }
                    match parsed.signed {
                        1 => config.input1.unpair = true,
                        2 => config.input2.unpair = true,
                        _ => {
                            let message = if option == b'a' {
                                b"-a option file number not 1 or 2".as_slice()
                            } else {
                                b"-v option file number not 1 or 2".as_slice()
                            };
                            return Err(ParseFailure::Message(message.to_vec()));
                        }
                    }
                    if parsed.end != option_argument.len() {
                        return Err(message_with_argument(
                            b"illegal file number -- ",
                            &option_argument,
                        ));
                    }
                }
                b'e' => config.empty = Some(option_argument),
                b'o' => fieldarg(&option_argument, &mut config.olist)?,
                b't' => {
                    config.delimiter = match option_argument.as_slice() {
                        [] => Delimiter::Exact(None),
                        [byte] if byte.is_ascii() => Delimiter::Exact(Some(*byte)),
                        _ => {
                            return Err(ParseFailure::Message(
                                b"illegal tab character specification".to_vec(),
                            ))
                        }
                    };
                }
                _ => unreachable!(),
            }
        }
        index += 1;
    }

    if aflag && vflag {
        return Err(ParseFailure::Message(
            b"the -a and -v options are mutually exclusive".to_vec(),
        ));
    }
    let operands: [Vec<u8>; 2] = operands.try_into().map_err(|_| ParseFailure::Usage)?;
    Ok(ParsedArgs {
        names,
        config,
        operands,
    })
}

fn parse_args<W: Write>(
    args: &[OsString],
    posixly_correct: bool,
    stderr: &mut W,
) -> Result<ParsedArgs, RunFailure> {
    let mut args = raw_os_args(args)?;
    let names = program_names(&args)?;
    obsolete(&mut args, &names, stderr)?;
    parse_options(args, names, posixly_correct).map_err(RunFailure::Parse)
}

fn usage<W: Write>(names: &ProgramNames, stderr: &mut W) -> io::Result<()> {
    stderr.write_all(b"usage: ")?;
    stderr.write_all(&names.short)?;
    stderr.write_all(b" [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n")?;
    for _ in 0..names.short.len() + 8 {
        stderr.write_all(b" ")?;
    }
    stderr.write_all(b"[-o list] [-t char] file1 file2\n")
}

fn mbssep(line: &[u8], delimiter: &Delimiter) -> Vec<Range<usize>> {
    let end = line
        .iter()
        .position(|byte| *byte == 0)
        .unwrap_or(line.len());
    match delimiter {
        Delimiter::SpanningWhitespace => {
            let mut fields = Vec::new();
            let mut cursor = 0;
            while cursor < end {
                while cursor < end && matches!(line[cursor], b' ' | b'\t') {
                    cursor += 1;
                }
                let start = cursor;
                while cursor < end && !matches!(line[cursor], b' ' | b'\t') {
                    cursor += 1;
                }
                if start < cursor {
                    fields.push(start..cursor);
                }
            }
            fields
        }
        Delimiter::Exact(None) => vec![0..end],
        Delimiter::Exact(Some(delimiter)) => {
            let mut fields = Vec::new();
            let mut start = 0;
            for cursor in 0..end {
                if line[cursor] == *delimiter {
                    fields.push(start..cursor);
                    start = cursor + 1;
                }
            }
            fields.push(start..end);
            fields
        }
    }
}

fn cmp(line1: &Line, fieldno1: usize, line2: &Line, fieldno2: usize) -> Ordering {
    match (line1.field(fieldno1), line2.field(fieldno2)) {
        (None, None) => Ordering::Equal,
        (None, Some(_)) => Ordering::Less,
        (Some(_), None) => Ordering::Greater,
        (Some(field1), Some(field2)) => field1.cmp(field2),
    }
}

fn slurp<R: BufRead>(input: &mut Input<R>, delimiter: &Delimiter) -> Result<(), RunFailure> {
    input.set.clear();
    if let Some(line) = input.pushback.take() {
        input
            .set
            .try_reserve(1)
            .map_err(|_| RunFailure::Allocation)?;
        input.set.push(line);
    }

    while !input.terminal {
        let mut bytes = Vec::new();
        match input.reader.read_until(b'\n', &mut bytes) {
            Ok(0) | Err(_) => {
                input.terminal = true;
                break;
            }
            Ok(_) => {}
        }
        if bytes.last() == Some(&b'\n') {
            bytes.pop();
        }
        let fields = mbssep(&bytes, delimiter);
        let line = Line { bytes, fields };

        if input
            .set
            .last()
            .is_some_and(|last| cmp(&line, input.joinf, last, input.joinf) != Ordering::Equal)
        {
            input.pushback = Some(line);
            break;
        }
        input
            .set
            .try_reserve(1)
            .map_err(|_| RunFailure::Allocation)?;
        input.set.push(line);
    }
    Ok(())
}

fn output_separator<W: Write>(
    separator: u8,
    state: &mut OutputState,
    stdout: &mut W,
) -> io::Result<()> {
    match state.orientation {
        StreamOrientation::Unoriented => {
            state.orientation = StreamOrientation::Wide;
            state.wide_side.push(separator);
            Ok(())
        }
        StreamOrientation::Byte => stdout.write_all(&[separator]),
        StreamOrientation::Wide => {
            state.wide_side.push(separator);
            Ok(())
        }
    }
}

fn output_bytes<W: Write>(bytes: &[u8], state: &mut OutputState, stdout: &mut W) -> io::Result<()> {
    match state.orientation {
        StreamOrientation::Unoriented => {
            state.orientation = StreamOrientation::Byte;
            stdout.write_all(bytes)
        }
        StreamOrientation::Byte => stdout.write_all(bytes),
        StreamOrientation::Wide => Ok(()),
    }
}

fn outfield<W: Write>(
    line: Option<&Line>,
    fieldno: usize,
    out_empty: bool,
    config: &Config,
    state: &mut OutputState,
    stdout: &mut W,
) -> io::Result<()> {
    if state.needsep != 0 {
        let separator = match config.delimiter {
            Delimiter::SpanningWhitespace => b' ',
            Delimiter::Exact(Some(separator)) => separator,
            Delimiter::Exact(None) => b'\0',
        };
        output_separator(separator, state, stdout)?;
    }
    state.needsep += 1;

    let field = line.and_then(|line| line.field(fieldno));
    if out_empty || field.is_none() {
        if let Some(empty) = &config.empty {
            output_bytes(empty, state, stdout)?;
        }
    } else if let Some(field) = field {
        if !field.is_empty() {
            output_bytes(field, state, stdout)?;
        }
    }
    Ok(())
}

fn finish_record<W: Write>(state: &mut OutputState, stdout: &mut W) -> io::Result<()> {
    let result = match state.orientation {
        StreamOrientation::Unoriented => {
            state.orientation = StreamOrientation::Byte;
            stdout.write_all(b"\n")
        }
        StreamOrientation::Byte => stdout.write_all(b"\n"),
        StreamOrientation::Wide => {
            state.byte_side.push(b'\n');
            Ok(())
        }
    };
    state.needsep = 0;
    result
}

fn flush_compat_output<W: Write>(state: &mut OutputState, stdout: &mut W) -> io::Result<()> {
    if state.orientation == StreamOrientation::Wide {
        stdout.write_all(&state.byte_side)?;
        stdout.write_all(&state.wide_side)?;
        state.byte_side.clear();
        state.wide_side.clear();
    }
    stdout.flush()
}

fn outoneline<R: BufRead, W: Write>(
    input: &Input<R>,
    line: &Line,
    config: &Config,
    state: &mut OutputState,
    stdout: &mut W,
) -> io::Result<()> {
    if config.olist.is_empty() {
        outfield(Some(line), input.joinf, false, config, state, stdout)?;
        for fieldno in 0..line.fields.len() {
            if fieldno != input.joinf {
                outfield(Some(line), fieldno, false, config, state, stdout)?;
            }
        }
    } else {
        for selector in &config.olist {
            if selector.filenum == input.number {
                outfield(Some(line), selector.fieldno, false, config, state, stdout)?;
            } else if selector.filenum == 0 {
                outfield(Some(line), input.joinf, false, config, state, stdout)?;
            } else {
                outfield(Some(line), 0, true, config, state, stdout)?;
            }
        }
    }
    finish_record(state, stdout)
}

fn outtwoline<R1: BufRead, R2: BufRead, W: Write>(
    input1: &Input<R1>,
    line1: &Line,
    input2: &Input<R2>,
    line2: &Line,
    config: &Config,
    state: &mut OutputState,
    stdout: &mut W,
) -> io::Result<()> {
    if config.olist.is_empty() {
        outfield(Some(line1), input1.joinf, false, config, state, stdout)?;
        for fieldno in 0..line1.fields.len() {
            if fieldno != input1.joinf {
                outfield(Some(line1), fieldno, false, config, state, stdout)?;
            }
        }
        for fieldno in 0..line2.fields.len() {
            if fieldno != input2.joinf {
                outfield(Some(line2), fieldno, false, config, state, stdout)?;
            }
        }
    } else {
        for selector in &config.olist {
            match selector.filenum {
                0 => {
                    if line1.fields.len() >= input1.joinf {
                        outfield(Some(line1), input1.joinf, false, config, state, stdout)?;
                    } else {
                        outfield(Some(line2), input2.joinf, false, config, state, stdout)?;
                    }
                }
                1 => outfield(Some(line1), selector.fieldno, false, config, state, stdout)?,
                _ => outfield(Some(line2), selector.fieldno, false, config, state, stdout)?,
            }
        }
    }
    finish_record(state, stdout)
}

fn joinlines<R1: BufRead, R2: BufRead, W: Write>(
    input1: &Input<R1>,
    input2: Option<&Input<R2>>,
    config: &Config,
    state: &mut OutputState,
    stdout: &mut W,
) -> io::Result<()> {
    if let Some(input2) = input2 {
        for line1 in &input1.set {
            for line2 in &input2.set {
                outtwoline(input1, line1, input2, line2, config, state, stdout)?;
            }
        }
    } else {
        for line in &input1.set {
            outoneline(input1, line, config, state, stdout)?;
        }
    }
    Ok(())
}

fn merge_inputs<R1: BufRead, R2: BufRead, W: Write>(
    input1: &mut Input<R1>,
    input2: &mut Input<R2>,
    config: &Config,
    stdout: &mut W,
) -> Result<(), RunFailure> {
    let mut state = OutputState::default();
    slurp(input1, &config.delimiter)?;
    slurp(input2, &config.delimiter)?;

    while !input1.set.is_empty() && !input2.set.is_empty() {
        match cmp(&input1.set[0], input1.joinf, &input2.set[0], input2.joinf) {
            Ordering::Equal => {
                if config.joinout {
                    joinlines(input1, Some(&*input2), config, &mut state, stdout)
                        .map_err(RunFailure::Stdout)?;
                }
                slurp(input1, &config.delimiter)?;
                slurp(input2, &config.delimiter)?;
            }
            Ordering::Less => {
                if input1.unpair {
                    joinlines(input1, None::<&Input<R2>>, config, &mut state, stdout)
                        .map_err(RunFailure::Stdout)?;
                }
                slurp(input1, &config.delimiter)?;
            }
            Ordering::Greater => {
                if input2.unpair {
                    joinlines(input2, None::<&Input<R1>>, config, &mut state, stdout)
                        .map_err(RunFailure::Stdout)?;
                }
                slurp(input2, &config.delimiter)?;
            }
        }
    }

    if input1.unpair {
        while !input1.set.is_empty() {
            joinlines(input1, None::<&Input<R2>>, config, &mut state, stdout)
                .map_err(RunFailure::Stdout)?;
            slurp(input1, &config.delimiter)?;
        }
    }
    if input2.unpair {
        while !input2.set.is_empty() {
            joinlines(input2, None::<&Input<R1>>, config, &mut state, stdout)
                .map_err(RunFailure::Stdout)?;
            slurp(input2, &config.delimiter)?;
        }
    }

    flush_compat_output(&mut state, stdout).map_err(RunFailure::Stdout)
}

fn error_text(error: &io::Error) -> String {
    let rendered = error.to_string();
    if let Some(code) = error.raw_os_error() {
        let suffix = format!(" (os error {code})");
        rendered
            .strip_suffix(&suffix)
            .unwrap_or(&rendered)
            .to_owned()
    } else {
        rendered
    }
}

fn render_failure<W: Write>(
    failure: &RunFailure,
    names: &ProgramNames,
    stderr: &mut W,
) -> io::Result<()> {
    match failure {
        RunFailure::Parse(ParseFailure::Usage) => usage(names, stderr),
        RunFailure::Parse(ParseFailure::Message(message)) => {
            stderr.write_all(&names.short)?;
            stderr.write_all(b": ")?;
            stderr.write_all(message)?;
            stderr.write_all(b"\n")
        }
        RunFailure::Parse(ParseFailure::GetoptThenUsage(message)) => {
            stderr.write_all(message)?;
            usage(names, stderr)
        }
        RunFailure::Open { path, source } => {
            stderr.write_all(&names.short)?;
            stderr.write_all(b": ")?;
            stderr.write_all(path)?;
            stderr.write_all(b": ")?;
            stderr.write_all(error_text(source).as_bytes())?;
            stderr.write_all(b"\n")
        }
        RunFailure::Stdout(source) => {
            stderr.write_all(&names.short)?;
            stderr.write_all(b": stdout: ")?;
            stderr.write_all(error_text(source).as_bytes())?;
            stderr.write_all(b"\n")
        }
        RunFailure::Allocation => {
            stderr.write_all(&names.short)?;
            stderr.write_all(b": Cannot allocate memory\n")
        }
    }
}

fn run_with<O, R, W, E>(
    args: &[OsString],
    posixly_correct: bool,
    opener: &mut O,
    stdin: &mut R,
    stdout: &mut W,
    stderr: &mut E,
) -> i32
where
    O: InputOpener,
    R: BufRead,
    W: Write,
    E: Write,
{
    let names = raw_os_args(args)
        .and_then(|arguments| program_names(&arguments))
        .unwrap_or(ProgramNames {
            invocation: Vec::new(),
            short: Vec::new(),
        });
    let parsed = match parse_args(args, posixly_correct, stderr) {
        Ok(parsed) => parsed,
        Err(failure) => {
            let _ = render_failure(&failure, &names, stderr);
            return EXIT_FAILURE;
        }
    };

    let ParsedArgs {
        names,
        config,
        operands,
    } = parsed;
    let first_stdin = operands[0] == b"-";
    let second_stdin = operands[1] == b"-";

    let result = match (first_stdin, second_stdin) {
        (true, true) => Err(RunFailure::Parse(ParseFailure::Message(
            b"only one input file may be stdin".to_vec(),
        ))),
        (true, false) => match opener.open(&operands[1]) {
            Ok(reader2) => {
                let mut input1 = Input::new(stdin, &config.input1);
                let mut input2 = Input::new(reader2, &config.input2);
                merge_inputs(&mut input1, &mut input2, &config, stdout)
            }
            Err(source) => Err(RunFailure::Open {
                path: operands[1].clone(),
                source,
            }),
        },
        (false, true) => match opener.open(&operands[0]) {
            Ok(reader1) => {
                let mut input1 = Input::new(reader1, &config.input1);
                let mut input2 = Input::new(stdin, &config.input2);
                merge_inputs(&mut input1, &mut input2, &config, stdout)
            }
            Err(source) => Err(RunFailure::Open {
                path: operands[0].clone(),
                source,
            }),
        },
        (false, false) => match opener.open(&operands[0]) {
            Err(source) => Err(RunFailure::Open {
                path: operands[0].clone(),
                source,
            }),
            Ok(reader1) => match opener.open(&operands[1]) {
                Err(source) => Err(RunFailure::Open {
                    path: operands[1].clone(),
                    source,
                }),
                Ok(reader2) => {
                    let mut input1 = Input::new(reader1, &config.input1);
                    let mut input2 = Input::new(reader2, &config.input2);
                    merge_inputs(&mut input1, &mut input2, &config, stdout)
                }
            },
        },
    };

    match result {
        Ok(()) => EXIT_SUCCESS,
        Err(failure) => {
            let _ = render_failure(&failure, &names, stderr);
            EXIT_FAILURE
        }
    }
}

fn main() {
    let args: Vec<OsString> = std::env::args_os().collect();
    let posixly_correct = std::env::var_os("POSIXLY_CORRECT").is_some();
    let mut opener = FileInputOpener;

    let stdin = io::stdin();
    let stdout = io::stdout();
    let stderr = io::stderr();
    let mut stdin = stdin.lock();
    let mut stdout = stdout.lock();
    let mut stderr = stderr.lock();

    let status = run_with(
        &args,
        posixly_correct,
        &mut opener,
        &mut stdin,
        &mut stdout,
        &mut stderr,
    );
    if status != 0 {
        std::process::exit(status);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::Cell;
    use std::collections::VecDeque;
    use std::io::{Cursor, Read};
    use std::os::unix::ffi::OsStringExt;
    use std::rc::Rc;

    enum MockOpen {
        Bytes(Vec<u8>),
        TrackedBytes(Vec<u8>, Rc<Cell<usize>>),
        Error(io::ErrorKind, &'static str),
        RawError(i32),
    }

    #[derive(Default)]
    struct MockInputOpener {
        responses: VecDeque<MockOpen>,
        open_order: Vec<Vec<u8>>,
    }

    impl InputOpener for MockInputOpener {
        fn open(&mut self, path: &[u8]) -> io::Result<Box<dyn BufRead>> {
            self.open_order.push(path.to_vec());
            match self.responses.pop_front() {
                Some(MockOpen::Bytes(bytes)) => Ok(Box::new(Cursor::new(bytes))),
                Some(MockOpen::TrackedBytes(bytes, read_calls)) => {
                    Ok(Box::new(TrackedReader::new(bytes, read_calls)))
                }
                Some(MockOpen::Error(kind, message)) => Err(io::Error::new(kind, message)),
                Some(MockOpen::RawError(code)) => Err(io::Error::from_raw_os_error(code)),
                None => Err(io::Error::new(
                    io::ErrorKind::NotFound,
                    "unconfigured mock input",
                )),
            }
        }
    }

    struct TrackedReader {
        inner: Cursor<Vec<u8>>,
        read_calls: Rc<Cell<usize>>,
    }

    impl TrackedReader {
        fn new(bytes: Vec<u8>, read_calls: Rc<Cell<usize>>) -> Self {
            Self {
                inner: Cursor::new(bytes),
                read_calls,
            }
        }

        fn record_read(&self) {
            self.read_calls.set(self.read_calls.get() + 1);
        }
    }

    impl Read for TrackedReader {
        fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
            self.record_read();
            self.inner.read(buffer)
        }
    }

    impl BufRead for TrackedReader {
        fn fill_buf(&mut self) -> io::Result<&[u8]> {
            self.record_read();
            self.inner.fill_buf()
        }

        fn consume(&mut self, amount: usize) {
            self.inner.consume(amount);
        }
    }

    struct ScriptedReader {
        inner: Cursor<Vec<u8>>,
        fail_at: Option<u64>,
        error_kind: io::ErrorKind,
        error_message: &'static str,
        read_calls: usize,
    }

    impl ScriptedReader {
        fn new(
            bytes: Vec<u8>,
            fail_at: Option<u64>,
            error_kind: io::ErrorKind,
            error_message: &'static str,
        ) -> Self {
            Self {
                inner: Cursor::new(bytes),
                fail_at,
                error_kind,
                error_message,
                read_calls: 0,
            }
        }

        fn should_fail(&self) -> bool {
            self.fail_at
                .is_some_and(|fail_at| self.inner.position() >= fail_at)
        }

        fn scripted_error(&self) -> io::Error {
            io::Error::new(self.error_kind, self.error_message)
        }
    }

    impl Read for ScriptedReader {
        fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
            self.read_calls += 1;
            if self.should_fail() {
                return Err(self.scripted_error());
            }

            let limit = self
                .fail_at
                .map(|fail_at| fail_at.saturating_sub(self.inner.position()) as usize)
                .unwrap_or(buffer.len())
                .min(buffer.len());
            self.inner.read(&mut buffer[..limit])
        }
    }

    impl BufRead for ScriptedReader {
        fn fill_buf(&mut self) -> io::Result<&[u8]> {
            self.read_calls += 1;
            if self.should_fail() {
                return Err(self.scripted_error());
            }

            let position = self.inner.position();
            let limit = self
                .fail_at
                .map(|fail_at| fail_at.saturating_sub(position) as usize);
            let available = self.inner.fill_buf()?;
            let length = limit.unwrap_or(available.len()).min(available.len());
            Ok(&available[..length])
        }

        fn consume(&mut self, amount: usize) {
            self.inner.consume(amount);
        }
    }

    #[derive(Clone, Copy)]
    enum MockIoError {
        Message(io::ErrorKind, &'static str),
        Raw(i32),
    }

    impl MockIoError {
        fn into_error(self) -> io::Error {
            match self {
                Self::Message(kind, message) => io::Error::new(kind, message),
                Self::Raw(code) => io::Error::from_raw_os_error(code),
            }
        }
    }

    struct FailingWriter {
        bytes: Vec<u8>,
        remaining: usize,
        write_error: MockIoError,
        flush_error: Option<MockIoError>,
        flush_calls: usize,
    }

    impl FailingWriter {
        fn new(remaining: usize) -> Self {
            Self {
                bytes: Vec::new(),
                remaining,
                write_error: MockIoError::Message(
                    io::ErrorKind::BrokenPipe,
                    "scripted write error",
                ),
                flush_error: None,
                flush_calls: 0,
            }
        }

        fn with_raw_write_error(remaining: usize, code: i32) -> Self {
            Self {
                write_error: MockIoError::Raw(code),
                ..Self::new(remaining)
            }
        }

        fn with_flush_error(error: MockIoError) -> Self {
            Self {
                bytes: Vec::new(),
                remaining: usize::MAX,
                write_error: MockIoError::Message(
                    io::ErrorKind::BrokenPipe,
                    "scripted write error",
                ),
                flush_error: Some(error),
                flush_calls: 0,
            }
        }
    }

    impl Write for FailingWriter {
        fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
            if self.remaining == 0 && !buffer.is_empty() {
                return Err(self.write_error.into_error());
            }

            let written = self.remaining.min(buffer.len());
            self.bytes.extend_from_slice(&buffer[..written]);
            self.remaining -= written;
            Ok(written)
        }

        fn flush(&mut self) -> io::Result<()> {
            self.flush_calls += 1;
            match self.flush_error {
                Some(error) => Err(error.into_error()),
                None => Ok(()),
            }
        }
    }

    fn raw_args(arguments: &[&[u8]]) -> Vec<OsString> {
        arguments
            .iter()
            .map(|argument| OsString::from_vec(argument.to_vec()))
            .collect()
    }

    fn parse_for_test(
        arguments: &[&[u8]],
        posixly_correct: bool,
    ) -> (Result<ParsedArgs, RunFailure>, Vec<u8>) {
        let mut stderr = Vec::new();
        let result = parse_args(&raw_args(arguments), posixly_correct, &mut stderr);
        (result, stderr)
    }

    fn invoke(
        arguments: &[&[u8]],
        responses: Vec<MockOpen>,
        stdin_bytes: &[u8],
    ) -> (i32, Vec<u8>, Vec<u8>, MockInputOpener) {
        let mut opener = MockInputOpener {
            responses: responses.into(),
            open_order: Vec::new(),
        };
        let mut stdin = Cursor::new(stdin_bytes.to_vec());
        let mut stdout = Vec::new();
        let mut stderr = Vec::new();
        let status = run_with(
            &raw_args(arguments),
            false,
            &mut opener,
            &mut stdin,
            &mut stdout,
            &mut stderr,
        );
        (status, stdout, stderr, opener)
    }

    fn line(bytes: &[u8], delimiter: &Delimiter) -> Line {
        Line {
            bytes: bytes.to_vec(),
            fields: mbssep(bytes, delimiter),
        }
    }

    fn merge_bytes(config: &Config, first: &[u8], second: &[u8]) -> Vec<u8> {
        let mut input1 = Input::new(Cursor::new(first.to_vec()), &config.input1);
        let mut input2 = Input::new(Cursor::new(second.to_vec()), &config.input2);
        let mut stdout = Vec::new();
        merge_inputs(&mut input1, &mut input2, config, &mut stdout).unwrap();
        stdout
    }

    mod cli_compatibility {
        use super::*;

        fn assert_parse_message(arguments: &[&[u8]], expected: &[u8]) {
            let (parsed, stderr) = parse_for_test(arguments, false);
            assert_eq!(stderr, b"");
            assert!(matches!(
                parsed,
                Err(RunFailure::Parse(ParseFailure::Message(message)))
                    if message == expected
            ));
        }

        #[test]
        fn normal_attached_and_permuted_options() {
            let (parsed, stderr) = parse_for_test(
                &[
                    b"join",
                    b"left\xff",
                    b"-12",
                    b"-23",
                    b"-eNA",
                    b"-o0,1.2",
                    b"-t:",
                    b"-a2",
                    b"right\xfe",
                ],
                false,
            );
            let parsed = parsed.unwrap();
            assert_eq!(stderr, b"");
            assert_eq!(
                parsed.operands,
                [b"left\xff".to_vec(), b"right\xfe".to_vec()]
            );
            assert_eq!(parsed.config.input1.joinf, 1);
            assert_eq!(parsed.config.input2.joinf, 2);
            assert_eq!(parsed.config.empty, Some(b"NA".to_vec()));
            assert_eq!(parsed.config.delimiter, Delimiter::Exact(Some(b':')));
            assert!(!parsed.config.input1.unpair);
            assert!(parsed.config.input2.unpair);
            assert_eq!(
                parsed.config.olist,
                vec![
                    OList {
                        filenum: 0,
                        fieldno: 0,
                    },
                    OList {
                        filenum: 1,
                        fieldno: 1,
                    },
                ]
            );

            let (parsed, stderr) =
                parse_for_test(&[b"join", b"-j", b"4", b"-v1", b"left", b"right"], false);
            let parsed = parsed.unwrap();
            assert_eq!(stderr, b"");
            assert_eq!(parsed.config.input1.joinf, 3);
            assert_eq!(parsed.config.input2.joinf, 3);
            assert!(parsed.config.input1.unpair);
            assert!(!parsed.config.input2.unpair);
            assert!(!parsed.config.joinout);
        }

        #[test]
        fn posix_mode_terminator_and_getopt_diagnostics() {
            let (parsed, stderr) = parse_for_test(&[b"join", b"left", b"-v2"], true);
            let parsed = parsed.unwrap();
            assert_eq!(stderr, b"");
            assert_eq!(parsed.operands, [b"left".to_vec(), b"-v2".to_vec()]);
            assert!(parsed.config.joinout);

            let (parsed, _) = parse_for_test(&[b"join", b"--", b"-x", b"right"], false);
            assert_eq!(
                parsed.unwrap().operands,
                [b"-x".to_vec(), b"right".to_vec()]
            );

            let (status, _, stderr, _) = invoke(&[b"/tmp/join", b"-x"], vec![], b"");
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(
                stderr,
                b"/tmp/join: invalid option -- 'x'\nusage: join [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n            [-o list] [-t char] file1 file2\n"
            );

            let (status, _, stderr, _) = invoke(&[b"/tmp/join", b"--long"], vec![], b"");
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(
                stderr,
                b"/tmp/join: invalid option -- '-'\nusage: join [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n            [-o list] [-t char] file1 file2\n"
            );

            let usage = b"usage: prog [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n            [-o list] [-t char] file1 file2\n";
            for option in [b'1', b'2', b'e', b'j', b'o', b't', b'v'] {
                let argument = [b'-', option];
                let (status, stdout, stderr, opener) =
                    invoke(&[b"/tmp/prog", argument.as_slice()], vec![], b"");
                let mut expected = b"/tmp/prog: option requires an argument -- '".to_vec();
                expected.push(option);
                expected.extend_from_slice(b"'\n");
                expected.extend_from_slice(usage);

                assert_eq!(status, EXIT_FAILURE);
                assert_eq!(stdout, b"");
                assert_eq!(stderr, expected);
                assert!(opener.open_order.is_empty());
            }

            let (status, _, stderr, _) = invoke(&[b"/tmp/\xffjoin", b"-x"], vec![], b"");
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(
                stderr,
                b"/tmp/\xffjoin: invalid option -- 'x'\nusage: \xffjoin [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n             [-o list] [-t char] file1 file2\n"
            );
        }

        #[test]
        fn bare_a_and_legacy_j_rewrites() {
            let (parsed, stderr) = parse_for_test(&[b"join", b"-a", b"left", b"right"], false);
            let parsed = parsed.unwrap();
            assert!(parsed.config.input1.unpair);
            assert!(parsed.config.input2.unpair);
            assert_eq!(
                stderr,
                b"join: -a option used without an argument; reverting to historical behavior\n"
            );

            let (parsed, stderr) =
                parse_for_test(&[b"join", b"-a", b"1", b"left", b"right"], false);
            let parsed = parsed.unwrap();
            assert_eq!(stderr, b"");
            assert!(parsed.config.input1.unpair);
            assert!(!parsed.config.input2.unpair);

            let (parsed, stderr) = parse_for_test(
                &[b"join", b"-j1", b"2", b"-j2", b"3", b"left", b"right"],
                false,
            );
            let parsed = parsed.unwrap();
            assert_eq!(stderr, b"");
            assert_eq!(parsed.config.input1.joinf, 1);
            assert_eq!(parsed.config.input2.joinf, 2);

            for malformed in [b"-j3".as_slice(), b"-j11", b"-jx"] {
                let (parsed, stderr) =
                    parse_for_test(&[b"join", malformed, b"left", b"right"], false);
                let mut expected = b"join: unknown option -- ".to_vec();
                expected.extend_from_slice(&malformed[1..]);
                expected.push(b'\n');
                assert!(matches!(
                    parsed,
                    Err(RunFailure::Parse(ParseFailure::Usage))
                ));
                assert_eq!(stderr, expected);
            }

            let (status, _, stderr, _) = invoke(&[b"/tmp/join", b"-a"], vec![], b"");
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(
                stderr,
                b"join: -a option used without an argument; reverting to historical behavior\nusage: join [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n            [-o list] [-t char] file1 file2\n"
            );
        }

        #[test]
        fn legacy_multi_argument_o_and_repeated_selectors() {
            let (parsed, _) = parse_for_test(
                &[
                    b"join", b"-o", b"2.1", b"1.2", b"2.2", b"-o0,0", b"left", b"right",
                ],
                false,
            );
            assert_eq!(
                parsed.unwrap().config.olist,
                vec![
                    OList {
                        filenum: 2,
                        fieldno: 0,
                    },
                    OList {
                        filenum: 1,
                        fieldno: 1,
                    },
                    OList {
                        filenum: 2,
                        fieldno: 1,
                    },
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

            let (parsed, stderr) =
                parse_for_test(&[b"join", b"-o", b"2.1", b"1.2", b"left", b"right"], false);
            let parsed = parsed.unwrap();
            assert_eq!(stderr, b"");
            assert_eq!(parsed.operands, [b"left".to_vec(), b"right".to_vec()]);
            assert_eq!(
                parsed.config.olist,
                vec![
                    OList {
                        filenum: 2,
                        fieldno: 0,
                    },
                    OList {
                        filenum: 1,
                        fieldno: 1,
                    },
                ]
            );

            for stopping_token in [b"0".as_slice(), b"1.2x"] {
                let (parsed, _) = parse_for_test(
                    &[b"join", b"-o", b"2.1", stopping_token, b"left", b"right"],
                    false,
                );
                assert!(matches!(
                    parsed,
                    Err(RunFailure::Parse(ParseFailure::Usage))
                ));
            }

            let names = ProgramNames {
                invocation: b"join".to_vec(),
                short: b"join".to_vec(),
            };
            let mut arguments = vec![
                b"join".to_vec(),
                b"-o".to_vec(),
                b"2.1".to_vec(),
                b"1.2".to_vec(),
                b"2.".to_vec(),
                b"0suffix".to_vec(),
                b"1.9".to_vec(),
            ];
            let mut stderr = Vec::new();
            obsolete(&mut arguments, &names, &mut stderr).unwrap();
            assert_eq!(stderr, b"");
            assert_eq!(
                arguments,
                vec![
                    b"join".to_vec(),
                    b"-o".to_vec(),
                    b"2.1".to_vec(),
                    b"-o1.2".to_vec(),
                    b"-o2.".to_vec(),
                    b"0suffix".to_vec(),
                    b"1.9".to_vec(),
                ]
            );

            let mut arguments = vec![b"join".to_vec(), b"--stop".to_vec(), b"-j3".to_vec()];
            obsolete(&mut arguments, &names, &mut stderr).unwrap();
            assert_eq!(
                arguments,
                vec![b"join".to_vec(), b"--stop".to_vec(), b"-j3".to_vec()]
            );
        }

        #[test]
        fn c_number_and_fieldarg_quirks() {
            assert_eq!(
                parse_c_long(b" \t-42tail"),
                CLong {
                    signed: -42,
                    unsigned: (-42_i64) as u64,
                    end: 5,
                }
            );
            let saturated = parse_c_long(b"999999999999999999999999");
            assert_eq!(saturated.signed, i64::MAX);
            assert_eq!(saturated.end, 24);
            let saturated = parse_c_long(b"-999999999999999999999999");
            assert_eq!(saturated.signed, i64::MIN);
            assert_eq!(saturated.unsigned, i64::MIN as u64);
            assert_eq!(saturated.end, 25);
            assert_eq!(parse_c_long(b" +x").end, 0);

            let mut selectors = Vec::new();
            fieldarg(b"0suffix,1.-2,2.+3", &mut selectors).unwrap();
            assert_eq!(
                selectors,
                vec![
                    OList {
                        filenum: 0,
                        fieldno: 0,
                    },
                    OList {
                        filenum: 1,
                        fieldno: usize::MAX - 2,
                    },
                    OList {
                        filenum: 2,
                        fieldno: 2,
                    },
                ]
            );

            let (parsed, _) = parse_for_test(&[b"join", b"-1", b"-2", b"left", b"right"], false);
            assert_eq!(parsed.unwrap().config.input1.joinf, usize::MAX - 2);
            let (parsed, _) = parse_for_test(&[b"join", b"-j", b"-1", b"left", b"right"], false);
            let parsed = parsed.unwrap();
            assert_eq!(parsed.config.input1.joinf, usize::MAX - 1);
            assert_eq!(parsed.config.input2.joinf, usize::MAX - 1);

            assert_parse_message(
                &[b"join", b"-1", b"0", b"left", b"right"],
                b"-1 option field number less than 1",
            );
            assert_parse_message(
                &[b"join", b"-2", b"x", b"left", b"right"],
                b"-2 option field number less than 1",
            );
            assert_parse_message(
                &[b"join", b"-j", b"1x", b"left", b"right"],
                b"illegal field number -- 1x",
            );
            assert_parse_message(
                &[b"join", b"-a0", b"left", b"right"],
                b"-a option file number not 1 or 2",
            );
            assert_parse_message(
                &[b"join", b"-a1x", b"left", b"right"],
                b"illegal file number -- 1x",
            );
            assert_parse_message(
                &[b"join", b"-v", b"xyz", b"left", b"right"],
                b"-v option file number not 1 or 2",
            );
            assert_parse_message(
                &[b"join", b"-a1", b"-v2", b"left", b"right"],
                b"the -a and -v options are mutually exclusive",
            );

            for (selector, expected) in [
                (b"1.0".as_slice(), b"field numbers are 1 based".as_slice()),
                (b"1.".as_slice(), b"field numbers are 1 based".as_slice()),
                (b"1.x".as_slice(), b"malformed -o option field".as_slice()),
                (b"x".as_slice(), b"malformed -o option field".as_slice()),
            ] {
                let mut selectors = Vec::new();
                assert!(matches!(
                    fieldarg(selector, &mut selectors),
                    Err(ParseFailure::Message(message)) if message == expected
                ));
            }
        }

        #[test]
        fn delimiter_validation_and_exact_usage() {
            for (argument, expected) in [
                (b"".as_slice(), Delimiter::Exact(None)),
                (b":".as_slice(), Delimiter::Exact(Some(b':'))),
                (b"\x7f".as_slice(), Delimiter::Exact(Some(b'\x7f'))),
            ] {
                let (parsed, stderr) =
                    parse_for_test(&[b"join", b"-t", argument, b"left", b"right"], false);
                assert_eq!(stderr, b"");
                assert_eq!(parsed.unwrap().config.delimiter, expected);
            }

            for argument in [b"ab".as_slice(), b"\x80", b"\xc3\xa9"] {
                assert_parse_message(
                    &[b"join", b"-t", argument, b"left", b"right"],
                    b"illegal tab character specification",
                );
            }

            let names = ProgramNames {
                invocation: b"/tmp/x".to_vec(),
                short: b"x".to_vec(),
            };
            let mut output = Vec::new();
            usage(&names, &mut output).unwrap();
            assert_eq!(
                output,
                b"usage: x [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n         [-o list] [-t char] file1 file2\n"
            );

            let (status, stdout, stderr, opener) = invoke(&[b"/tmp/x"], vec![], b"");
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stdout, b"");
            assert_eq!(stderr, output);
            assert!(opener.open_order.is_empty());
        }
    }

    mod splitting_and_comparison {
        use super::*;

        #[test]
        fn default_and_exact_delimiter_fields() {
            let whitespace = line(b" \ta  b\t", &Delimiter::SpanningWhitespace);
            assert_eq!(whitespace.fields, vec![2..3, 5..6]);
            assert_eq!(whitespace.field(0), Some(b"a".as_slice()));
            assert_eq!(whitespace.field(1), Some(b"b".as_slice()));
            assert_eq!(whitespace.field(2), None);

            let exact = line(b"a::b:", &Delimiter::Exact(Some(b':')));
            assert_eq!(exact.fields, vec![0..1, 2..2, 3..4, 5..5]);
            assert_eq!(exact.field(0), Some(b"a".as_slice()));
            assert_eq!(exact.field(1), Some(b"".as_slice()));
            assert_eq!(exact.field(2), Some(b"b".as_slice()));
            assert_eq!(exact.field(3), Some(b"".as_slice()));
        }

        #[test]
        fn empty_delimiter_nul_cr_and_final_line() {
            let empty = line(b"", &Delimiter::Exact(None));
            assert_eq!(empty.fields, vec![0..0]);
            assert_eq!(empty.field(0), Some(b"".as_slice()));

            let unsplit = line(b"a:b", &Delimiter::Exact(None));
            assert_eq!(unsplit.fields, vec![0..3]);
            assert_eq!(unsplit.field(0), Some(b"a:b".as_slice()));

            let nul = line(b"a:b\0:c", &Delimiter::Exact(Some(b':')));
            assert_eq!(nul.bytes, b"a:b\0:c");
            assert_eq!(nul.fields, vec![0..1, 2..3]);
            assert_eq!(nul.field(0), Some(b"a".as_slice()));
            assert_eq!(nul.field(1), Some(b"b".as_slice()));
            assert_eq!(nul.field(2), None);

            let config = Config::default();
            let mut input = Input::new(Cursor::new(b"k v\r\nlast x".to_vec()), &config.input1);
            slurp(&mut input, &config.delimiter).unwrap();
            assert_eq!(input.set[0].bytes, b"k v\r");
            assert_eq!(input.set[0].field(1), Some(b"v\r".as_slice()));
            slurp(&mut input, &config.delimiter).unwrap();
            assert_eq!(input.set[0].bytes, b"last x");
            assert_eq!(input.set[0].field(0), Some(b"last".as_slice()));
            assert_eq!(input.set[0].field(1), Some(b"x".as_slice()));
            assert!(input.terminal);
        }

        #[test]
        fn invalid_utf8_and_unsigned_byte_order() {
            let lower = line(&[0x7f], &Delimiter::Exact(None));
            let higher = line(&[0x80], &Delimiter::Exact(None));
            assert_eq!(higher.bytes, vec![0x80]);
            assert_eq!(higher.field(0), Some([0x80].as_slice()));
            assert_eq!(cmp(&lower, 0, &higher, 0), Ordering::Less);
            assert_eq!(cmp(&higher, 0, &lower, 0), Ordering::Greater);

            let ten = line(b"ignored 10", &Delimiter::SpanningWhitespace);
            let two = line(b"2", &Delimiter::SpanningWhitespace);
            assert_eq!(cmp(&ten, 1, &two, 0), Ordering::Less);
        }

        #[test]
        fn missing_and_present_empty_key_classes() {
            let missing = line(b"", &Delimiter::SpanningWhitespace);
            let also_missing = line(b" \t", &Delimiter::SpanningWhitespace);
            let present_empty = line(b":value", &Delimiter::Exact(Some(b':')));
            let also_present_empty = line(b":other", &Delimiter::Exact(Some(b':')));
            assert_eq!(cmp(&missing, 0, &also_missing, 0), Ordering::Equal);
            assert_eq!(cmp(&missing, 0, &present_empty, 0), Ordering::Less);
            assert_eq!(cmp(&present_empty, 0, &missing, 0), Ordering::Greater);
            assert_eq!(
                cmp(&present_empty, 0, &also_present_empty, 0),
                Ordering::Equal
            );
        }
    }

    mod grouping_and_merge {
        use super::*;

        #[test]
        fn one_line_pushback_and_duplicate_groups() {
            let config = Config::default();
            let mut input = Input::new(
                Cursor::new(b"a 1\na 2\nb 3\nb 4\n".to_vec()),
                &config.input1,
            );
            slurp(&mut input, &config.delimiter).unwrap();
            assert_eq!(input.set.len(), 2);
            assert_eq!(
                input
                    .set
                    .iter()
                    .map(|line| line.bytes.as_slice())
                    .collect::<Vec<_>>(),
                vec![b"a 1".as_slice(), b"a 2".as_slice()]
            );
            assert_eq!(input.set[0].field(0), Some(b"a".as_slice()));
            assert_eq!(
                input.pushback.as_ref().map(|line| line.bytes.as_slice()),
                Some(b"b 3".as_slice())
            );
            assert_eq!(
                input.pushback.as_ref().and_then(|line| line.field(0)),
                Some(b"b".as_slice())
            );

            slurp(&mut input, &config.delimiter).unwrap();
            assert_eq!(input.set.len(), 2);
            assert_eq!(
                input
                    .set
                    .iter()
                    .map(|line| line.bytes.as_slice())
                    .collect::<Vec<_>>(),
                vec![b"b 3".as_slice(), b"b 4".as_slice()]
            );
            assert_eq!(input.set[0].field(0), Some(b"b".as_slice()));
            assert!(input.pushback.is_none());
            assert!(input.terminal);

            slurp(&mut input, &config.delimiter).unwrap();
            assert!(input.set.is_empty());
            assert!(input.pushback.is_none());
        }

        #[test]
        fn cartesian_order_and_unsorted_progression() {
            let config = Config::default();
            assert_eq!(
                merge_bytes(&config, b"a 1\na 2\nc 3\n", b"a x\na y\nb z\n"),
                b"a 1 x\na 1 y\na 2 x\na 2 y\n"
            );

            let mut unpair = Config::default();
            unpair.input1.unpair = true;
            unpair.input2.unpair = true;
            assert_eq!(
                merge_bytes(&unpair, b"b 1\na 2\n", b"a x\nb y\n"),
                b"a x\nb 1 y\na 2\n"
            );
        }

        #[test]
        fn unmatched_tails_and_both_v_selections() {
            let (status, stdout, stderr, _) = invoke(
                &[b"join", b"-a", b"1", b"-a", b"2", b"left", b"right"],
                vec![
                    MockOpen::Bytes(b"a left\nc left\nf left\n".to_vec()),
                    MockOpen::Bytes(b"b right\nc right\ne right\n".to_vec()),
                ],
                b"",
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"a left\nb right\nc left right\ne right\nf left\n");
            assert_eq!(stderr, b"");

            let (status, stdout, stderr, _) = invoke(
                &[b"join", b"-v", b"2", b"left", b"right"],
                vec![
                    MockOpen::Bytes(b"dup 1\ndup 2\n".to_vec()),
                    MockOpen::Bytes(b"dup a\ndup b\nother x\n".to_vec()),
                ],
                b"",
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"other x\n");
            assert_eq!(stderr, b"");

            let (status, stdout, _, _) = invoke(
                &[b"join", b"-v", b"1", b"-v", b"2", b"left", b"right"],
                vec![
                    MockOpen::Bytes(b"a 1\nc 3\n".to_vec()),
                    MockOpen::Bytes(b"a x\nb y\n".to_vec()),
                ],
                b"",
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"b y\nc 3\n");
        }

        #[test]
        fn each_a_and_v_selection_preserves_group_order() {
            let first = b"a left-a\nc left-c\ne left-e\ng left-g\ni left-i\n";
            let second = b"b right-b\nc right-c\nf right-f\ng right-g\nh right-h\n";
            let run = |options: &[&[u8]]| {
                let mut arguments = vec![b"join".as_slice()];
                arguments.extend_from_slice(options);
                arguments.extend_from_slice(&[b"left".as_slice(), b"right".as_slice()]);
                invoke(
                    &arguments,
                    vec![
                        MockOpen::Bytes(first.to_vec()),
                        MockOpen::Bytes(second.to_vec()),
                    ],
                    b"",
                )
            };

            let (status, stdout, stderr, _) = run(&[b"-a", b"1"]);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(
                stdout,
                b"a left-a\nc left-c right-c\ne left-e\ng left-g right-g\ni left-i\n"
            );
            assert_eq!(stderr, b"");

            let (status, stdout, stderr, _) = run(&[b"-a2"]);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(
                stdout,
                b"b right-b\nc left-c right-c\nf right-f\ng left-g right-g\nh right-h\n"
            );
            assert_eq!(stderr, b"");

            let (status, stdout, stderr, _) = run(&[b"-v1"]);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"a left-a\ne left-e\ni left-i\n");
            assert_eq!(stderr, b"");

            let (status, stdout, stderr, _) = run(&[b"-v", b"2"]);
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"b right-b\nf right-f\nh right-h\n");
            assert_eq!(stderr, b"");
        }

        #[test]
        fn terminal_read_error_matches_eof() {
            let config = Config::default();
            let eof_reader = ScriptedReader::new(
                b"a 1\n".to_vec(),
                None,
                io::ErrorKind::UnexpectedEof,
                "unused EOF error",
            );
            let mut eof_input = Input::new(eof_reader, &config.input1);
            slurp(&mut eof_input, &config.delimiter).unwrap();
            assert!(eof_input.terminal);

            let error_reader = ScriptedReader::new(
                b"a 1\nb 2\n".to_vec(),
                Some(4),
                io::ErrorKind::PermissionDenied,
                "configured read failure",
            );
            let mut error_input = Input::new(error_reader, &config.input1);
            slurp(&mut error_input, &config.delimiter).unwrap();
            assert_eq!(error_input.set, eof_input.set);
            assert_eq!(error_input.pushback, eof_input.pushback);
            assert!(error_input.terminal);
            assert_eq!(
                error_input.reader.error_kind,
                io::ErrorKind::PermissionDenied
            );
            assert_eq!(error_input.reader.error_message, "configured read failure");

            let error_read_calls = error_input.reader.read_calls;
            slurp(&mut error_input, &config.delimiter).unwrap();
            assert!(error_input.set.is_empty());
            assert_eq!(error_input.reader.read_calls, error_read_calls);

            let eof_read_calls = eof_input.reader.read_calls;
            slurp(&mut eof_input, &config.delimiter).unwrap();
            assert!(eof_input.set.is_empty());
            assert_eq!(eof_input.reader.read_calls, eof_read_calls);
        }
    }

    mod projection_and_output {
        use super::*;

        #[test]
        fn default_alternate_and_selected_projection() {
            let mut alternate = Config::default();
            alternate.input1.joinf = 2;
            alternate.input2.joinf = 3;
            assert_eq!(
                merge_bytes(&alternate, b"A left key\n", b"B right x key\n"),
                b"key A left B right x\n"
            );

            let (status, stdout, stderr, _) = invoke(
                &[b"join", b"-o", b"2.2,0,1.1", b"left", b"right"],
                vec![
                    MockOpen::Bytes(b"a 1\nb 2\nc 3\n".to_vec()),
                    MockOpen::Bytes(b"a 1\nb 4\nd 4\n".to_vec()),
                ],
                b"",
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"1 a a\n4 b b\n");
            assert_eq!(stderr, b"");
        }

        #[test]
        fn repeated_output_options_append_and_keep_each_source() {
            let (status, stdout, stderr, _) = invoke(
                &[
                    b"join",
                    b"-o",
                    b"2.3,0",
                    b"-o",
                    b"1.2,0,2.2",
                    b"left",
                    b"right",
                ],
                vec![
                    MockOpen::Bytes(b"k left-one left-two\n".to_vec()),
                    MockOpen::Bytes(b"k right-one right-two\n".to_vec()),
                ],
                b"",
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"right-two k left-one k right-one\n");
            assert_eq!(stderr, b"");

            let (status, stdout, stderr, _) = invoke(
                &[
                    b"join", b"-a", b"2", b"-e", b"NA", b"-o", b"0,1.2", b"-o", b"2.2", b"left",
                    b"right",
                ],
                vec![
                    MockOpen::Bytes(b"a left\n".to_vec()),
                    MockOpen::Bytes(b"z right\n".to_vec()),
                ],
                b"",
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"z NA right\n");
            assert_eq!(stderr, b"");
        }

        #[test]
        fn bare_a_preserves_absent_input_projection_slots() {
            let responses = || {
                vec![
                    MockOpen::Bytes(b"a left-a\nc left-c\n".to_vec()),
                    MockOpen::Bytes(b"b right-b\nc right-c\n".to_vec()),
                ]
            };
            let warning =
                b"join: -a option used without an argument; reverting to historical behavior\n";

            let (status, stdout, stderr, opener) = invoke(
                &[b"join", b"-a", b"-o", b"0,1.2,2.2", b"left", b"right"],
                responses(),
                b"",
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"a left-a \nb  right-b\nc left-c right-c\n");
            assert_eq!(stderr, warning);
            assert_eq!(opener.open_order, vec![b"left".to_vec(), b"right".to_vec()]);

            let (status, stdout, stderr, _) = invoke(
                &[
                    b"join",
                    b"-a",
                    b"-e",
                    b"NA",
                    b"-o",
                    b"0,1.2,2.2",
                    b"left",
                    b"right",
                ],
                responses(),
                b"",
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"a left-a NA\nb NA right-b\nc left-c right-c\n");
            assert_eq!(stderr, warning);
        }

        #[test]
        fn duplicate_join_missing_empty_and_replacement_fields() {
            let mut config = Config::default();
            config.empty = Some(b"NA".to_vec());
            config.olist = vec![
                OList {
                    filenum: 0,
                    fieldno: 0,
                },
                OList {
                    filenum: 0,
                    fieldno: 0,
                },
                OList {
                    filenum: 1,
                    fieldno: 1,
                },
                OList {
                    filenum: 2,
                    fieldno: 2,
                },
            ];
            assert_eq!(
                merge_bytes(&config, b"k left\n", b"k right\n"),
                b"k k left NA\n"
            );

            config.delimiter = Delimiter::Exact(Some(b':'));
            config.input1.unpair = true;
            config.olist = vec![
                OList {
                    filenum: 0,
                    fieldno: 0,
                },
                OList {
                    filenum: 1,
                    fieldno: 1,
                },
                OList {
                    filenum: 2,
                    fieldno: 0,
                },
            ];
            assert_eq!(merge_bytes(&config, b"a:\n", b"z:x\n"), b"a::NA\n");
        }

        #[test]
        fn replacement_distinguishes_present_empty_from_missing_fields() {
            let mut config = Config::default();
            config.delimiter = Delimiter::Exact(Some(b':'));
            config.empty = Some(b"NA".to_vec());
            config.olist = vec![
                OList {
                    filenum: 1,
                    fieldno: 1,
                },
                OList {
                    filenum: 1,
                    fieldno: 2,
                },
            ];
            assert_eq!(merge_bytes(&config, b"k::x\n", b"k::y\n"), b"\n:");

            config.empty = Some(Vec::new());
            config.olist = vec![
                OList {
                    filenum: 1,
                    fieldno: 3,
                },
                OList {
                    filenum: 1,
                    fieldno: 1,
                },
                OList {
                    filenum: 1,
                    fieldno: 2,
                },
                OList {
                    filenum: 2,
                    fieldno: 3,
                },
            ];
            assert_eq!(merge_bytes(&config, b"k::x\n", b"k::y\n"), b"::x:\n");
        }

        #[test]
        fn separator_positions_and_nul_separator() {
            let mut config = Config::default();
            config.delimiter = Delimiter::Exact(Some(b':'));
            config.olist = vec![
                OList {
                    filenum: 1,
                    fieldno: 0,
                },
                OList {
                    filenum: 1,
                    fieldno: 1,
                },
                OList {
                    filenum: 1,
                    fieldno: 2,
                },
            ];
            assert_eq!(merge_bytes(&config, b"k::x\n", b"k::y\n"), b"k::x\n");

            config.delimiter = Delimiter::Exact(None);
            config.olist = vec![
                OList {
                    filenum: 0,
                    fieldno: 0,
                },
                OList {
                    filenum: 1,
                    fieldno: 0,
                },
                OList {
                    filenum: 2,
                    fieldno: 0,
                },
            ];
            assert_eq!(merge_bytes(&config, b"k\n", b"k\n"), b"k\0k\0k\n");
        }

        #[test]
        fn byte_newline_and_wide_first_orientations() {
            let input_options = InputOptions {
                joinf: 0,
                unpair: true,
                number: 1,
            };
            let input = Input::new(Cursor::new(Vec::<u8>::new()), &input_options);
            let source_line = line(b"k", &Delimiter::SpanningWhitespace);

            let mut config = Config::default();
            config.olist = vec![
                OList {
                    filenum: 1,
                    fieldno: 9,
                },
                OList {
                    filenum: 1,
                    fieldno: 0,
                },
            ];
            let mut state = OutputState::default();
            let mut stdout = Vec::new();
            outoneline(&input, &source_line, &config, &mut state, &mut stdout).unwrap();
            flush_compat_output(&mut state, &mut stdout).unwrap();
            assert_eq!(stdout, b"\n ");

            config.empty = Some(Vec::new());
            let mut state = OutputState::default();
            let mut stdout = Vec::new();
            outoneline(&input, &source_line, &config, &mut state, &mut stdout).unwrap();
            flush_compat_output(&mut state, &mut stdout).unwrap();
            assert_eq!(stdout, b" k\n");

            config.empty = None;
            config.olist.truncate(1);
            let mut state = OutputState::default();
            let mut stdout = Vec::new();
            outoneline(&input, &source_line, &config, &mut state, &mut stdout).unwrap();
            flush_compat_output(&mut state, &mut stdout).unwrap();
            assert_eq!(stdout, b"\n");
        }

        #[test]
        fn stream_orientation_persists_across_records() {
            let mut config = Config::default();
            config.input1.unpair = true;
            config.olist = vec![OList {
                filenum: 1,
                fieldno: 1,
            }];
            assert_eq!(merge_bytes(&config, b"a\nb value\n", b""), b"\nvalue\n");

            config.olist = vec![
                OList {
                    filenum: 1,
                    fieldno: 9,
                },
                OList {
                    filenum: 1,
                    fieldno: 0,
                },
            ];
            assert_eq!(merge_bytes(&config, b"a\nb\n", b""), b"\n\n  ");

            config.olist.swap(0, 1);
            assert_eq!(merge_bytes(&config, b"a\nb\n", b""), b"a \nb \n");
        }
    }

    mod runtime_and_errors {
        use super::*;

        #[test]
        fn ordered_open_success_and_failure() {
            let (status, stdout, stderr, opener) = invoke(
                &[b"join", b"first", b"second"],
                vec![
                    MockOpen::Bytes(b"a 1\n".to_vec()),
                    MockOpen::Bytes(b"a 2\n".to_vec()),
                ],
                b"",
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"a 1 2\n");
            assert_eq!(stderr, b"");
            assert_eq!(
                opener.open_order,
                vec![b"first".to_vec(), b"second".to_vec()]
            );

            let (status, _, stderr, opener) = invoke(
                &[b"join", b"first", b"second"],
                vec![MockOpen::Error(io::ErrorKind::PermissionDenied, "denied")],
                b"",
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stderr, b"join: first: denied\n");
            assert_eq!(opener.open_order, vec![b"first".to_vec()]);

            let first_read_calls = Rc::new(Cell::new(0));
            let (status, _, stderr, opener) = invoke(
                &[b"join", b"first", b"second"],
                vec![
                    MockOpen::TrackedBytes(Vec::new(), Rc::clone(&first_read_calls)),
                    MockOpen::Error(io::ErrorKind::NotFound, "missing"),
                ],
                b"",
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stderr, b"join: second: missing\n");
            assert_eq!(
                opener.open_order,
                vec![b"first".to_vec(), b"second".to_vec()]
            );
            assert_eq!(first_read_calls.get(), 0);
        }

        #[test]
        fn stdin_branches_and_dual_stdin_rejection() {
            let (status, stdout, _, opener) = invoke(
                &[b"join", b"-", b"second"],
                vec![MockOpen::Bytes(b"a 2\n".to_vec())],
                b"a 1\n",
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"a 1 2\n");
            assert_eq!(opener.open_order, vec![b"second".to_vec()]);

            let (status, stdout, _, opener) = invoke(
                &[b"join", b"first", b"-"],
                vec![MockOpen::Bytes(b"a 1\n".to_vec())],
                b"a 2\n",
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout, b"a 1 2\n");
            assert_eq!(opener.open_order, vec![b"first".to_vec()]);

            let (status, stdout, stderr, opener) = invoke(&[b"join", b"-", b"-"], vec![], b"a 1\n");
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stdout, b"");
            assert_eq!(stderr, b"join: only one input file may be stdin\n");
            assert!(opener.open_order.is_empty());

            let mut opener = MockInputOpener {
                responses: vec![MockOpen::Error(
                    io::ErrorKind::PermissionDenied,
                    "second denied",
                )]
                .into(),
                open_order: Vec::new(),
            };
            let mut stdin = ScriptedReader::new(
                b"a 1\n".to_vec(),
                None,
                io::ErrorKind::Other,
                "unused read error",
            );
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let status = run_with(
                &raw_args(&[b"join", b"-", b"second"]),
                false,
                &mut opener,
                &mut stdin,
                &mut stdout,
                &mut stderr,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stdout, b"");
            assert_eq!(stderr, b"join: second: second denied\n");
            assert_eq!(opener.open_order, vec![b"second".to_vec()]);
            assert_eq!(stdin.read_calls, 0);

            let mut opener = MockInputOpener::default();
            let mut stdin = ScriptedReader::new(
                b"a 1\n".to_vec(),
                None,
                io::ErrorKind::Other,
                "unused read error",
            );
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let status = run_with(
                &raw_args(&[b"join", b"-", b"-"]),
                false,
                &mut opener,
                &mut stdin,
                &mut stdout,
                &mut stderr,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stdin.read_calls, 0);
        }

        #[test]
        fn raw_invocation_path_diagnostics_and_statuses() {
            let (status, _, stderr, _) = invoke(
                &[b"/tmp/\xffjoin", b"bad\xff", b"second"],
                vec![MockOpen::Error(io::ErrorKind::Other, "raw failure")],
                b"",
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stderr, b"\xffjoin: bad\xff: raw failure\n");

            let (status, _, stderr, _) = invoke(
                &[b"/tmp/join", b"missing", b"second"],
                vec![MockOpen::RawError(2)],
                b"",
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stderr, b"join: missing: No such file or directory\n");
        }

        #[test]
        fn stdout_failure_uses_failing_writer() {
            let matching_responses = || {
                vec![
                    MockOpen::Bytes(b"a 1\n".to_vec()),
                    MockOpen::Bytes(b"a 2\n".to_vec()),
                ]
            };
            let mut opener = MockInputOpener {
                responses: matching_responses().into(),
                open_order: Vec::new(),
            };
            let mut stdin = Cursor::new(Vec::<u8>::new());
            let mut stdout = FailingWriter::new(0);
            let mut stderr = Vec::new();
            let status = run_with(
                &raw_args(&[b"join", b"first", b"second"]),
                false,
                &mut opener,
                &mut stdin,
                &mut stdout,
                &mut stderr,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stdout.bytes, b"");
            assert_eq!(stdout.flush_calls, 0);
            assert_eq!(stderr, b"join: stdout: scripted write error\n");

            let mut opener = MockInputOpener {
                responses: matching_responses().into(),
                open_order: Vec::new(),
            };
            let mut stdin = Cursor::new(Vec::<u8>::new());
            let mut stdout = FailingWriter::new(2);
            let mut stderr = Vec::new();
            let status = run_with(
                &raw_args(&[b"join", b"first", b"second"]),
                false,
                &mut opener,
                &mut stdin,
                &mut stdout,
                &mut stderr,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stdout.bytes, b"a ");
            assert_eq!(stdout.flush_calls, 0);
            assert_eq!(stderr, b"join: stdout: scripted write error\n");

            let mut opener = MockInputOpener {
                responses: matching_responses().into(),
                open_order: Vec::new(),
            };
            let mut stdin = Cursor::new(Vec::<u8>::new());
            let mut stdout = FailingWriter::new(usize::MAX);
            let mut stderr = Vec::new();
            let status = run_with(
                &raw_args(&[b"join", b"first", b"second"]),
                false,
                &mut opener,
                &mut stdin,
                &mut stdout,
                &mut stderr,
            );
            assert_eq!(status, EXIT_SUCCESS);
            assert_eq!(stdout.bytes, b"a 1 2\n");
            assert_eq!(stdout.flush_calls, 1);
            assert_eq!(stderr, b"");
        }

        #[test]
        fn raw_stdout_flush_and_diagnostic_failures_preserve_status() {
            let responses = || {
                vec![
                    MockOpen::Bytes(b"a 1\n".to_vec()),
                    MockOpen::Bytes(b"a 2\n".to_vec()),
                ]
            };
            let mut opener = MockInputOpener {
                responses: responses().into(),
                open_order: Vec::new(),
            };
            let mut stdin = Cursor::new(Vec::<u8>::new());
            let mut stdout = FailingWriter::with_raw_write_error(0, 32);
            let mut stderr = Vec::new();
            let status = run_with(
                &raw_args(&[b"/tmp/\xffjoin", b"first", b"second"]),
                false,
                &mut opener,
                &mut stdin,
                &mut stdout,
                &mut stderr,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stderr, b"\xffjoin: stdout: Broken pipe\n");

            let mut opener = MockInputOpener {
                responses: vec![MockOpen::Bytes(Vec::new()), MockOpen::Bytes(Vec::new())].into(),
                open_order: Vec::new(),
            };
            let mut stdin = Cursor::new(Vec::<u8>::new());
            let mut stdout = FailingWriter::with_flush_error(MockIoError::Message(
                io::ErrorKind::Other,
                "scripted flush error",
            ));
            let mut stderr = Vec::new();
            let status = run_with(
                &raw_args(&[b"join", b"first", b"second"]),
                false,
                &mut opener,
                &mut stdin,
                &mut stdout,
                &mut stderr,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stdout.flush_calls, 1);
            assert_eq!(stderr, b"join: stdout: scripted flush error\n");

            let mut opener = MockInputOpener {
                responses: vec![MockOpen::RawError(2)].into(),
                open_order: Vec::new(),
            };
            let mut stdin = Cursor::new(Vec::<u8>::new());
            let mut stdout = Vec::new();
            let mut stderr = FailingWriter::new(0);
            let status = run_with(
                &raw_args(&[b"join", b"missing", b"second"]),
                false,
                &mut opener,
                &mut stdin,
                &mut stdout,
                &mut stderr,
            );
            assert_eq!(status, EXIT_FAILURE);
            assert_eq!(stdout, b"");
            assert_eq!(stderr.bytes, b"");
        }
    }
}
