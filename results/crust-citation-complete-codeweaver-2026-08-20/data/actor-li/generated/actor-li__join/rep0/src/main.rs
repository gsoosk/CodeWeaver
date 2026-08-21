#![forbid(unsafe_code)]

use std::cmp::Ordering;
use std::env;
use std::ffi::OsString;
use std::fs::File;
use std::io::{self, BufRead, BufReader, Write};
use std::ops::Range;
use std::os::unix::ffi::OsStringExt;
use std::path::PathBuf;
use std::process::ExitCode;

const STATUS_SUCCESS: u8 = 0;
const STATUS_ERROR: u8 = 1;

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct Line {
    line: Vec<u8>,
    fields: Vec<Range<usize>>,
}

impl Line {
    fn field(&self, fieldno: usize) -> Option<&[u8]> {
        self.fields
            .get(fieldno)
            .and_then(|range| self.line.get(range.clone()))
    }
}

enum InputReader<'a> {
    Stdin(&'a mut dyn BufRead),
    Owned(Box<dyn BufRead>),
}

impl InputReader<'_> {
    fn read_until(&mut self, delimiter: u8, buffer: &mut Vec<u8>) -> io::Result<usize> {
        match self {
            Self::Stdin(reader) => reader.read_until(delimiter, buffer),
            Self::Owned(reader) => reader.read_until(delimiter, buffer),
        }
    }
}

struct Input<'a> {
    reader: InputReader<'a>,
    joinf: usize,
    unpair: bool,
    number: u8,
    set: Vec<Line>,
    pending: Option<Line>,
}

impl<'a> Input<'a> {
    fn new(reader: InputReader<'a>, joinf: usize, unpair: bool, number: u8) -> Self {
        Self {
            reader,
            joinf,
            unpair,
            number,
            set: Vec::new(),
            pending: None,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Olist {
    filenum: u8,
    fieldno: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Config {
    joinf1: usize,
    joinf2: usize,
    unpair1: bool,
    unpair2: bool,
    joinout: bool,
    empty: Option<Vec<u8>>,
    delimiters: Vec<u8>,
    output_separator: u8,
    spans: bool,
    olist: Option<Vec<Olist>>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            joinf1: 0,
            joinf2: 0,
            unpair1: false,
            unpair2: false,
            joinout: true,
            empty: None,
            delimiters: vec![b' ', b'\t'],
            output_separator: b' ',
            spans: true,
            olist: None,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ParsedLong {
    value: i64,
    end: usize,
}

#[derive(Debug)]
struct ParsedArgs {
    raw_argv0: Vec<u8>,
    progname: Vec<u8>,
    config: Config,
    operands: [Vec<u8>; 2],
}

#[derive(Debug)]
enum AppError {
    Usage,
    Message(Vec<u8>),
    Open { path: Vec<u8>, source: io::Error },
    Stdout(io::Error),
}

trait FileOpener {
    fn open(&mut self, path: &[u8]) -> io::Result<Box<dyn BufRead>>;
}

struct RealFileOpener;

impl FileOpener for RealFileOpener {
    fn open(&mut self, path: &[u8]) -> io::Result<Box<dyn BufRead>> {
        let path = PathBuf::from(OsString::from_vec(path.to_vec()));
        File::open(path).map(|file| Box::new(BufReader::new(file)) as Box<dyn BufRead>)
    }
}

fn main() -> ExitCode {
    let raw_args = env::args_os().map(|arg| arg.into_vec()).collect();
    let mut stdin = io::stdin().lock();
    let mut stdout = io::stdout().lock();
    let mut stderr = io::stderr().lock();
    let mut opener = RealFileOpener;

    ExitCode::from(run_with(
        raw_args,
        &mut stdin,
        &mut opener,
        &mut stdout,
        &mut stderr,
    ))
}

fn run_with(
    mut raw_args: Vec<Vec<u8>>,
    stdin_reader: &mut dyn BufRead,
    file_opener: &mut dyn FileOpener,
    stdout_writer: &mut dyn Write,
    stderr_writer: &mut dyn Write,
) -> u8 {
    let progname = raw_args
        .first()
        .map(|arg| basename(arg))
        .unwrap_or_default();

    let result = (|| -> Result<(), AppError> {
        obsolete(&mut raw_args, stderr_writer)?;
        let parsed = parse_args(
            &mut raw_args,
            env::var_os("POSIXLY_CORRECT").is_some(),
            stderr_writer,
        )?;
        debug_assert_eq!(
            parsed.raw_argv0.as_slice(),
            raw_args.first().map_or(&[][..], |arg| c_visible(arg))
        );
        debug_assert_eq!(parsed.progname, progname);
        let config = parsed.config;
        let [first_path, second_path] = parsed.operands;
        let first_is_stdin = first_path == b"-";
        let second_is_stdin = second_path == b"-";

        if first_is_stdin {
            if second_is_stdin {
                return Err(AppError::Message(
                    b"only one input file may be stdin".to_vec(),
                ));
            }
            let second_reader =
                file_opener
                    .open(&second_path)
                    .map_err(|source| AppError::Open {
                        path: second_path,
                        source,
                    })?;
            let first = Input::new(
                InputReader::Stdin(stdin_reader),
                config.joinf1,
                config.unpair1,
                1,
            );
            let second = Input::new(
                InputReader::Owned(second_reader),
                config.joinf2,
                config.unpair2,
                2,
            );
            process_inputs(first, second, &config, stdout_writer)
        } else {
            let first_reader = file_opener
                .open(&first_path)
                .map_err(|source| AppError::Open {
                    path: first_path,
                    source,
                })?;
            if second_is_stdin {
                let first = Input::new(
                    InputReader::Owned(first_reader),
                    config.joinf1,
                    config.unpair1,
                    1,
                );
                let second = Input::new(
                    InputReader::Stdin(stdin_reader),
                    config.joinf2,
                    config.unpair2,
                    2,
                );
                process_inputs(first, second, &config, stdout_writer)
            } else {
                let second_reader =
                    file_opener
                        .open(&second_path)
                        .map_err(|source| AppError::Open {
                            path: second_path,
                            source,
                        })?;
                let first = Input::new(
                    InputReader::Owned(first_reader),
                    config.joinf1,
                    config.unpair1,
                    1,
                );
                let second = Input::new(
                    InputReader::Owned(second_reader),
                    config.joinf2,
                    config.unpair2,
                    2,
                );
                process_inputs(first, second, &config, stdout_writer)
            }
        }
    })();

    match result {
        Ok(()) => STATUS_SUCCESS,
        Err(error) => {
            report_error(&progname, error, stderr_writer);
            STATUS_ERROR
        }
    }
}

fn process_inputs(
    mut first: Input<'_>,
    mut second: Input<'_>,
    config: &Config,
    output: &mut dyn Write,
) -> Result<(), AppError> {
    slurp(&mut first, config)?;
    slurp(&mut second, config)?;

    while !first.set.is_empty() && !second.set.is_empty() {
        match cmp(&first.set[0], first.joinf, &second.set[0], second.joinf) {
            Ordering::Equal => {
                if config.joinout {
                    joinlines(&first, Some(&second), config, output)?;
                }
                slurp(&mut first, config)?;
                slurp(&mut second, config)?;
            }
            Ordering::Less => {
                if first.unpair {
                    joinlines(&first, None, config, output)?;
                }
                slurp(&mut first, config)?;
            }
            Ordering::Greater => {
                if second.unpair {
                    joinlines(&second, None, config, output)?;
                }
                slurp(&mut second, config)?;
            }
        }
    }

    if first.unpair {
        while !first.set.is_empty() {
            joinlines(&first, None, config, output)?;
            slurp(&mut first, config)?;
        }
    }
    if second.unpair {
        while !second.set.is_empty() {
            joinlines(&second, None, config, output)?;
            slurp(&mut second, config)?;
        }
    }

    Ok(())
}

fn obsolete(args: &mut [Vec<u8>], diagnostics: &mut dyn Write) -> Result<(), AppError> {
    let progname = args.first().map(|arg| basename(arg)).unwrap_or_default();
    let mut index = 1;

    while index < args.len() {
        let argument = c_visible(&args[index]).to_vec();
        if argument.starts_with(b"--") {
            return Ok(());
        }
        if !argument.starts_with(b"-") || argument.len() < 2 {
            index += 1;
            continue;
        }

        match argument[1] {
            b'a' => {
                let next_is_file_number = args
                    .get(index + 1)
                    .map(|next| {
                        let next = c_visible(next);
                        next == b"1" || next == b"2"
                    })
                    .unwrap_or(false);
                if argument.len() == 2 && !next_is_file_number {
                    args[index][1] = 1;
                    let _ = warnx(
                        &progname,
                        b"-a option used without an argument; reverting to historical behavior",
                        diagnostics,
                    );
                }
            }
            b'j' => match argument.get(2).copied() {
                Some(b'1' | b'2') if argument.len() == 3 => {
                    args[index] = vec![b'-', argument[2]];
                }
                None => {}
                _ => {
                    let mut message = b"unknown option -- ".to_vec();
                    message.extend_from_slice(&argument[1..]);
                    let _ = warnx(&progname, &message, diagnostics);
                    return Err(AppError::Usage);
                }
            },
            b'o' if argument.len() == 2 && index + 1 < args.len() => {
                let mut scan = index + 2;
                while scan < args.len() {
                    let candidate = c_visible(&args[scan]);
                    if candidate.first() == Some(&b'0') {
                        break;
                    }
                    let valid_prefix = candidate.len() >= 2
                        && matches!(candidate[0], b'1' | b'2')
                        && candidate[1] == b'.';
                    if !valid_prefix || !candidate[2..].iter().all(u8::is_ascii_digit) {
                        break;
                    }
                    let mut replacement = b"-o".to_vec();
                    replacement.extend_from_slice(candidate);
                    args[scan] = replacement;
                    scan += 1;
                }
                index = scan.saturating_sub(1);
            }
            _ => {}
        }
        index += 1;
    }

    Ok(())
}

fn parse_args(
    args: &mut [Vec<u8>],
    posixly_correct: bool,
    diagnostics: &mut dyn Write,
) -> Result<ParsedArgs, AppError> {
    let raw_argv0 = args
        .first()
        .map(|arg| c_visible(arg).to_vec())
        .unwrap_or_default();
    let progname = basename(&raw_argv0);
    let mut config = Config::default();
    let mut output_list = Vec::new();
    let mut operands = Vec::new();
    let mut aflag = false;
    let mut vflag = false;
    let mut options_enabled = true;
    let mut index = 1;

    while index < args.len() {
        let argument = c_visible(&args[index]).to_vec();

        if options_enabled && argument == b"--" {
            options_enabled = false;
            index += 1;
            continue;
        }

        if options_enabled && argument.len() >= 2 && argument[0] == b'-' && argument != b"-" {
            let mut option_index = 1;
            while option_index < argument.len() {
                let option = argument[option_index];
                if option == 1 {
                    aflag = true;
                    config.unpair1 = true;
                    config.unpair2 = true;
                    option_index += 1;
                    continue;
                }

                let recognized = matches!(
                    option,
                    b'a' | b'e' | b'j' | b'1' | b'2' | b'o' | b't' | b'v'
                );
                if !recognized {
                    let _ =
                        getopt_diagnostic(&raw_argv0, b"invalid option -- '", option, diagnostics);
                    return Err(AppError::Usage);
                }

                let value = if option_index + 1 < argument.len() {
                    argument[option_index + 1..].to_vec()
                } else if index + 1 < args.len() {
                    index += 1;
                    c_visible(&args[index]).to_vec()
                } else {
                    let _ = getopt_diagnostic(
                        &raw_argv0,
                        b"option requires an argument -- '",
                        option,
                        diagnostics,
                    );
                    return Err(AppError::Usage);
                };

                match option {
                    b'1' => config.joinf1 = parse_join_field(&value, b"-1")?,
                    b'2' => config.joinf2 = parse_join_field(&value, b"-2")?,
                    b'a' => {
                        aflag = true;
                        match parse_file_number(&value, b"-a")? {
                            1 => config.unpair1 = true,
                            2 => config.unpair2 = true,
                            _ => unreachable!(),
                        }
                    }
                    b'e' => config.empty = Some(c_visible(&value).to_vec()),
                    b'j' => {
                        let field = parse_join_field(&value, b"-j")?;
                        config.joinf1 = field;
                        config.joinf2 = field;
                    }
                    b'o' => fieldarg(&value, &mut output_list)?,
                    b't' => {
                        let value = c_visible(&value);
                        if value.len() > 1 || value.first().is_some_and(|byte| !byte.is_ascii()) {
                            return Err(AppError::Message(
                                b"illegal tab character specification".to_vec(),
                            ));
                        }
                        config.spans = false;
                        config.delimiters = value.to_vec();
                        config.output_separator = value.first().copied().unwrap_or(0);
                    }
                    b'v' => {
                        vflag = true;
                        config.joinout = false;
                        match parse_file_number(&value, b"-v")? {
                            1 => config.unpair1 = true,
                            2 => config.unpair2 = true,
                            _ => unreachable!(),
                        }
                    }
                    _ => unreachable!(),
                }
                break;
            }
            index += 1;
            continue;
        }

        if options_enabled && posixly_correct {
            operands.extend(args[index..].iter().map(|arg| c_visible(arg).to_vec()));
            break;
        }
        operands.push(argument);
        index += 1;
    }

    if aflag && vflag {
        return Err(AppError::Message(
            b"the -a and -v options are mutually exclusive".to_vec(),
        ));
    }
    if operands.len() != 2 {
        return Err(AppError::Usage);
    }
    if !output_list.is_empty() {
        config.olist = Some(output_list);
    }

    Ok(ParsedArgs {
        raw_argv0,
        progname,
        config,
        operands: [operands.remove(0), operands.remove(0)],
    })
}

fn parse_c_long(value: &[u8]) -> ParsedLong {
    let value = c_visible(value);
    let mut index = 0;
    while value.get(index).is_some_and(|byte| is_c_whitespace(*byte)) {
        index += 1;
    }

    let negative = match value.get(index) {
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
    let limit = if negative {
        (i64::MAX as u64) + 1
    } else {
        i64::MAX as u64
    };
    let mut magnitude = 0_u64;
    let mut overflow = false;

    while let Some(byte) = value.get(index).filter(|byte| byte.is_ascii_digit()) {
        let digit = u64::from(*byte - b'0');
        if magnitude > (limit - digit) / 10 {
            overflow = true;
        } else if !overflow {
            magnitude = magnitude * 10 + digit;
        }
        index += 1;
    }

    if index == digit_start {
        return ParsedLong { value: 0, end: 0 };
    }

    let parsed = if overflow {
        if negative {
            i64::MIN
        } else {
            i64::MAX
        }
    } else if negative {
        if magnitude == (i64::MAX as u64) + 1 {
            i64::MIN
        } else {
            -(magnitude as i64)
        }
    } else {
        magnitude as i64
    };

    ParsedLong {
        value: parsed,
        end: index,
    }
}

fn fieldarg(option: &[u8], olist: &mut Vec<Olist>) -> Result<(), AppError> {
    let option = c_visible(option);
    for token in option.split(|byte| matches!(byte, b',' | b' ' | b'\t')) {
        if token.is_empty() {
            continue;
        }

        let (filenum, fieldno) = if token[0] == b'0' {
            (0, 0)
        } else if token.len() >= 2 && matches!(token[0], b'1' | b'2') && token[1] == b'.' {
            let parsed = parse_c_long(&token[2..]);
            if has_trailing(&token[2..], parsed.end) {
                return Err(AppError::Message(b"malformed -o option field".to_vec()));
            }
            let fieldno = c_unsigned(parsed.value);
            if fieldno == 0 {
                return Err(AppError::Message(b"field numbers are 1 based".to_vec()));
            }
            (token[0] - b'0', fieldno.wrapping_sub(1))
        } else {
            return Err(AppError::Message(b"malformed -o option field".to_vec()));
        };

        olist.push(Olist { filenum, fieldno });
    }

    Ok(())
}

fn parse_join_field(value: &[u8], option: &[u8]) -> Result<usize, AppError> {
    let parsed = parse_c_long(value);
    let field = c_unsigned(parsed.value);
    if field < 1 {
        let mut message = option.to_vec();
        message.extend_from_slice(b" option field number less than 1");
        return Err(AppError::Message(message));
    }
    if has_trailing(value, parsed.end) {
        let mut message = b"illegal field number -- ".to_vec();
        message.extend_from_slice(c_visible(value));
        return Err(AppError::Message(message));
    }
    Ok(field.wrapping_sub(1))
}

fn parse_file_number(value: &[u8], option: &[u8]) -> Result<u8, AppError> {
    let parsed = parse_c_long(value);
    let number = match parsed.value {
        1 => 1,
        2 => 2,
        _ => {
            let mut message = option.to_vec();
            message.extend_from_slice(b" option file number not 1 or 2");
            return Err(AppError::Message(message));
        }
    };
    if has_trailing(value, parsed.end) {
        let mut message = b"illegal file number -- ".to_vec();
        message.extend_from_slice(c_visible(value));
        return Err(AppError::Message(message));
    }
    Ok(number)
}

fn parse_line(mut line: Vec<u8>, delimiters: &[u8], spans: bool) -> Line {
    if line.last() == Some(&b'\n') {
        line.pop();
    }
    if let Some(nul) = line.iter().position(|byte| *byte == 0) {
        line.truncate(nul);
    }
    let fields = mbssep(&line, delimiters, spans);
    Line { line, fields }
}

fn mbssep(line: &[u8], delimiters: &[u8], spans: bool) -> Vec<Range<usize>> {
    if delimiters.is_empty() {
        return vec![0..line.len()];
    }

    let mut fields = Vec::new();
    let mut start = 0;
    for (index, byte) in line.iter().enumerate() {
        if delimiters.contains(byte) {
            if !spans || start != index {
                fields.push(start..index);
            }
            start = index + 1;
        }
    }
    if !spans || start != line.len() {
        fields.push(start..line.len());
    }
    fields
}

fn cmp(first: &Line, first_fieldno: usize, second: &Line, second_fieldno: usize) -> Ordering {
    match (first.field(first_fieldno), second.field(second_fieldno)) {
        (None, None) => Ordering::Equal,
        (None, Some(_)) => Ordering::Less,
        (Some(_), None) => Ordering::Greater,
        (Some(first), Some(second)) => first.cmp(second),
    }
}

fn slurp(input: &mut Input<'_>, config: &Config) -> Result<(), AppError> {
    input.set.clear();
    let first = match input.pending.take() {
        Some(line) => Some(line),
        None => read_line(input, config),
    };
    let Some(first) = first else {
        return Ok(());
    };
    input.set.push(first);

    loop {
        let Some(line) = read_line(input, config) else {
            break;
        };
        let last = &input.set[input.set.len() - 1];
        if cmp(&line, input.joinf, last, input.joinf) != Ordering::Equal {
            input.pending = Some(line);
            break;
        }
        input.set.push(line);
    }

    Ok(())
}

fn read_line(input: &mut Input<'_>, config: &Config) -> Option<Line> {
    let mut bytes = Vec::new();
    match input.reader.read_until(b'\n', &mut bytes) {
        Ok(0) | Err(_) => None,
        Ok(_) => Some(parse_line(bytes, &config.delimiters, config.spans)),
    }
}

fn joinlines(
    first: &Input<'_>,
    second: Option<&Input<'_>>,
    config: &Config,
    output: &mut dyn Write,
) -> Result<(), AppError> {
    if let Some(second) = second {
        for first_line in &first.set {
            for second_line in &second.set {
                outtwoline(first, first_line, second, second_line, config, output)?;
            }
        }
    } else {
        for line in &first.set {
            outoneline(first, line, config, output)?;
        }
    }
    Ok(())
}

fn outoneline(
    input: &Input<'_>,
    line: &Line,
    config: &Config,
    output: &mut dyn Write,
) -> Result<(), AppError> {
    let mut needsep = false;
    if let Some(olist) = &config.olist {
        for field in olist {
            if field.filenum == input.number {
                outfield(line, field.fieldno, false, config, output, &mut needsep)?;
            } else if field.filenum == 0 {
                outfield(line, input.joinf, false, config, output, &mut needsep)?;
            } else {
                outfield(line, 0, true, config, output, &mut needsep)?;
            }
        }
    } else {
        outfield(line, input.joinf, false, config, output, &mut needsep)?;
        for fieldno in 0..line.fields.len() {
            if fieldno != input.joinf {
                outfield(line, fieldno, false, config, output, &mut needsep)?;
            }
        }
    }
    write_output(output, b"\n")
}

fn outtwoline(
    first_input: &Input<'_>,
    first_line: &Line,
    second_input: &Input<'_>,
    second_line: &Line,
    config: &Config,
    output: &mut dyn Write,
) -> Result<(), AppError> {
    let mut needsep = false;
    if let Some(olist) = &config.olist {
        for field in olist {
            if field.filenum == 0 {
                if first_line.fields.len() >= first_input.joinf {
                    outfield(
                        first_line,
                        first_input.joinf,
                        false,
                        config,
                        output,
                        &mut needsep,
                    )?;
                } else {
                    outfield(
                        second_line,
                        second_input.joinf,
                        false,
                        config,
                        output,
                        &mut needsep,
                    )?;
                }
            } else if field.filenum == 1 {
                outfield(
                    first_line,
                    field.fieldno,
                    false,
                    config,
                    output,
                    &mut needsep,
                )?;
            } else {
                outfield(
                    second_line,
                    field.fieldno,
                    false,
                    config,
                    output,
                    &mut needsep,
                )?;
            }
        }
    } else {
        outfield(
            first_line,
            first_input.joinf,
            false,
            config,
            output,
            &mut needsep,
        )?;
        for fieldno in 0..first_line.fields.len() {
            if fieldno != first_input.joinf {
                outfield(first_line, fieldno, false, config, output, &mut needsep)?;
            }
        }
        for fieldno in 0..second_line.fields.len() {
            if fieldno != second_input.joinf {
                outfield(second_line, fieldno, false, config, output, &mut needsep)?;
            }
        }
    }
    write_output(output, b"\n")
}

fn outfield(
    line: &Line,
    fieldno: usize,
    out_empty: bool,
    config: &Config,
    output: &mut dyn Write,
    needsep: &mut bool,
) -> Result<(), AppError> {
    if *needsep {
        write_output(output, &[config.output_separator])?;
    }
    *needsep = true;

    if out_empty {
        if let Some(empty) = &config.empty {
            write_output(output, empty)?;
        }
    } else if let Some(field) = line.field(fieldno) {
        if !field.is_empty() {
            write_output(output, field)?;
        }
    } else if let Some(empty) = &config.empty {
        write_output(output, empty)?;
    }
    Ok(())
}

fn write_output(output: &mut dyn Write, bytes: &[u8]) -> Result<(), AppError> {
    output.write_all(bytes).map_err(AppError::Stdout)
}

fn warnx(progname: &[u8], message: &[u8], diagnostics: &mut dyn Write) -> io::Result<()> {
    write_prefixed(progname, message, diagnostics)
}

fn errx(progname: &[u8], message: &[u8], diagnostics: &mut dyn Write) -> io::Result<()> {
    write_prefixed(progname, message, diagnostics)
}

fn err(
    progname: &[u8],
    context: Option<&[u8]>,
    source: &io::Error,
    diagnostics: &mut dyn Write,
) -> io::Result<()> {
    diagnostics.write_all(progname)?;
    diagnostics.write_all(b": ")?;
    if let Some(context) = context {
        diagnostics.write_all(context)?;
        diagnostics.write_all(b": ")?;
    }
    diagnostics.write_all(&os_error_text(source))?;
    diagnostics.write_all(b"\n")
}

fn usage(progname: &[u8], diagnostics: &mut dyn Write) -> io::Result<()> {
    diagnostics.write_all(b"usage: ")?;
    diagnostics.write_all(progname)?;
    diagnostics
        .write_all(b" [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n")?;
    diagnostics.write_all(&vec![b' '; progname.len() + 8])?;
    diagnostics.write_all(b"[-o list] [-t char] file1 file2\n")
}

fn report_error(progname: &[u8], error: AppError, diagnostics: &mut dyn Write) {
    match error {
        AppError::Usage => {
            let _ = usage(progname, diagnostics);
        }
        AppError::Message(message) => {
            let _ = errx(progname, &message, diagnostics);
        }
        AppError::Open { path, source } => {
            let _ = err(progname, Some(&path), &source, diagnostics);
        }
        AppError::Stdout(source) => {
            let _ = err(progname, Some(b"stdout"), &source, diagnostics);
        }
    }
}

fn write_prefixed(progname: &[u8], message: &[u8], diagnostics: &mut dyn Write) -> io::Result<()> {
    diagnostics.write_all(progname)?;
    diagnostics.write_all(b": ")?;
    diagnostics.write_all(message)?;
    diagnostics.write_all(b"\n")
}

fn getopt_diagnostic(
    raw_argv0: &[u8],
    message: &[u8],
    option: u8,
    diagnostics: &mut dyn Write,
) -> io::Result<()> {
    diagnostics.write_all(raw_argv0)?;
    diagnostics.write_all(b": ")?;
    diagnostics.write_all(message)?;
    diagnostics.write_all(&[option])?;
    diagnostics.write_all(b"'\n")
}

fn basename(argument: &[u8]) -> Vec<u8> {
    c_visible(argument)
        .rsplit(|byte| *byte == b'/')
        .next()
        .unwrap_or_default()
        .to_vec()
}

fn c_visible(value: &[u8]) -> &[u8] {
    &value[..value
        .iter()
        .position(|byte| *byte == 0)
        .unwrap_or(value.len())]
}

fn has_trailing(value: &[u8], end: usize) -> bool {
    c_visible(value).get(end).is_some()
}

fn c_unsigned(value: i64) -> usize {
    (value as u64) as usize
}

fn is_c_whitespace(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | 0x0b | 0x0c | b'\r')
}

fn os_error_text(source: &io::Error) -> Vec<u8> {
    let mut text = source.to_string();
    if let Some(code) = source.raw_os_error() {
        let suffix = format!(" (os error {code})");
        if text.ends_with(&suffix) {
            text.truncate(text.len() - suffix.len());
        }
    }
    text.into_bytes()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;
    use std::io::{Cursor, Read};

    #[derive(Default)]
    struct MemoryOpener {
        files: BTreeMap<Vec<u8>, Vec<u8>>,
        failures: BTreeMap<Vec<u8>, i32>,
        open_order: Vec<Vec<u8>>,
    }

    impl FileOpener for MemoryOpener {
        fn open(&mut self, path: &[u8]) -> io::Result<Box<dyn BufRead>> {
            self.open_order.push(path.to_vec());
            if let Some(code) = self.failures.get(path) {
                return Err(io::Error::from_raw_os_error(*code));
            }
            let bytes = self
                .files
                .get(path)
                .cloned()
                .ok_or_else(|| io::Error::from(io::ErrorKind::NotFound))?;
            Ok(Box::new(Cursor::new(bytes)))
        }
    }

    struct FailingReader {
        bytes: Cursor<Vec<u8>>,
        fail_after: usize,
    }

    impl Read for FailingReader {
        fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
            let position = self.bytes.position() as usize;
            if position >= self.fail_after {
                return Err(io::Error::new(
                    io::ErrorKind::Other,
                    "injected read failure",
                ));
            }
            let allowed = (self.fail_after - position).min(buffer.len());
            self.bytes.read(&mut buffer[..allowed])
        }
    }

    struct FailingWriter {
        bytes: Vec<u8>,
        fail_on_call: Option<usize>,
        fail_on_flush: bool,
        calls: usize,
        flushes: usize,
    }

    impl FailingWriter {
        fn on_call(call: usize) -> Self {
            Self {
                bytes: Vec::new(),
                fail_on_call: Some(call),
                fail_on_flush: false,
                calls: 0,
                flushes: 0,
            }
        }

        fn on_flush() -> Self {
            Self {
                bytes: Vec::new(),
                fail_on_call: None,
                fail_on_flush: true,
                calls: 0,
                flushes: 0,
            }
        }
    }

    impl Write for FailingWriter {
        fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
            self.calls += 1;
            if self.fail_on_call == Some(self.calls) {
                return Err(io::Error::new(
                    io::ErrorKind::BrokenPipe,
                    "injected write failure",
                ));
            }
            self.bytes.extend_from_slice(buffer);
            Ok(buffer.len())
        }

        fn flush(&mut self) -> io::Result<()> {
            self.flushes += 1;
            if self.fail_on_flush {
                return Err(io::Error::new(
                    io::ErrorKind::BrokenPipe,
                    "injected flush failure",
                ));
            }
            Ok(())
        }
    }

    fn argv(values: &[&[u8]]) -> Vec<Vec<u8>> {
        values.iter().map(|value| value.to_vec()).collect()
    }

    fn run_case(
        arguments: Vec<Vec<u8>>,
        files: &[(&[u8], &[u8])],
        stdin: &[u8],
    ) -> (u8, Vec<u8>, Vec<u8>, MemoryOpener) {
        let mut opener = MemoryOpener::default();
        for (path, bytes) in files {
            opener.files.insert(path.to_vec(), bytes.to_vec());
        }
        let mut input = Cursor::new(stdin.to_vec());
        let mut output = Vec::new();
        let mut diagnostics = Vec::new();
        let status = run_with(
            arguments,
            &mut input,
            &mut opener,
            &mut output,
            &mut diagnostics,
        );
        (status, output, diagnostics, opener)
    }

    fn fields(line: &Line) -> Vec<&[u8]> {
        (0..line.fields.len())
            .map(|index| line.field(index).unwrap())
            .collect()
    }

    mod obsolete_and_parser {
        use super::*;

        fn parse_ok(values: &[&[u8]], posixly_correct: bool) -> (ParsedArgs, Vec<u8>) {
            let mut arguments = argv(values);
            let mut diagnostics = Vec::new();
            obsolete(&mut arguments, &mut diagnostics).unwrap();
            let parsed = parse_args(&mut arguments, posixly_correct, &mut diagnostics).unwrap();
            (parsed, diagnostics)
        }

        #[test]
        fn option_compatibility_matrix() {
            let (defaults, diagnostics) = parse_ok(&[b"/tmp/join", b"left", b"right"], false);
            assert_eq!(defaults.raw_argv0, b"/tmp/join");
            assert_eq!(defaults.progname, b"join");
            assert_eq!(defaults.operands, [b"left".to_vec(), b"right".to_vec()]);
            assert_eq!(defaults.config, Config::default());
            assert!(diagnostics.is_empty());

            let (attached, diagnostics) = parse_ok(
                &[
                    b"/tmp/join",
                    b"left",
                    b"-12",
                    b"-2",
                    b"3",
                    b"-eold",
                    b"-enew",
                    b"-t,",
                    b"-o1.1,2.2",
                    b"right",
                ],
                false,
            );
            assert_eq!(attached.operands, [b"left".to_vec(), b"right".to_vec()]);
            assert_eq!(attached.config.joinf1, 1);
            assert_eq!(attached.config.joinf2, 2);
            assert_eq!(attached.config.empty, Some(b"new".to_vec()));
            assert_eq!(attached.config.delimiters, b",");
            assert_eq!(attached.config.output_separator, b',');
            assert!(!attached.config.spans);
            assert_eq!(
                attached.config.olist,
                Some(vec![
                    Olist {
                        filenum: 1,
                        fieldno: 0,
                    },
                    Olist {
                        filenum: 2,
                        fieldno: 1,
                    },
                ])
            );
            assert!(diagnostics.is_empty());

            let mut clustered = vec![
                b"join".to_vec(),
                vec![b'-', 1, b'j', b'2'],
                b"left".to_vec(),
                b"right".to_vec(),
            ];
            let parsed = parse_args(&mut clustered, false, &mut Vec::new()).unwrap();
            assert_eq!(parsed.config.joinf1, 1);
            assert_eq!(parsed.config.joinf2, 1);
            assert!(parsed.config.unpair1 && parsed.config.unpair2);

            let (permuted, _) = parse_ok(&[b"join", b"left", b"-j", b"2", b"right"], false);
            assert_eq!(permuted.operands, [b"left".to_vec(), b"right".to_vec()]);
            assert_eq!(permuted.config.joinf1, 1);
            assert_eq!(permuted.config.joinf2, 1);

            let mut posix = argv(&[b"join", b"left", b"-j", b"2", b"right"]);
            obsolete(&mut posix, &mut Vec::new()).unwrap();
            assert!(matches!(
                parse_args(&mut posix, true, &mut Vec::new()),
                Err(AppError::Usage)
            ));

            let (after_double_dash, _) = parse_ok(&[b"join", b"--", b"-j", b"2"], false);
            assert_eq!(after_double_dash.operands, [b"-j".to_vec(), b"2".to_vec()]);
            assert_eq!(after_double_dash.config, Config::default());

            let mut arguments = argv(&[
                b"/tmp/join",
                b"left",
                b"-j2",
                b"2",
                b"right",
                b"-o",
                b"1.1",
                b"2.2",
            ]);
            let mut diagnostics = Vec::new();
            obsolete(&mut arguments, &mut diagnostics).unwrap();
            assert_eq!(arguments[2], b"-2");
            assert_eq!(arguments[7], b"-o2.2");
            let parsed = parse_args(&mut arguments, false, &mut diagnostics).unwrap();
            assert_eq!(parsed.raw_argv0, b"/tmp/join");
            assert_eq!(parsed.progname, b"join");
            assert_eq!(parsed.operands, [b"left".to_vec(), b"right".to_vec()]);
            assert_eq!(parsed.config.joinf2, 1);
            assert_eq!(
                parsed.config.olist,
                Some(vec![
                    Olist {
                        filenum: 1,
                        fieldno: 0,
                    },
                    Olist {
                        filenum: 2,
                        fieldno: 1,
                    },
                ])
            );

            let mut historical = argv(&[b"alias", b"-a", b"left", b"right"]);
            diagnostics.clear();
            obsolete(&mut historical, &mut diagnostics).unwrap();
            let parsed = parse_args(&mut historical, false, &mut diagnostics).unwrap();
            assert!(parsed.config.unpair1 && parsed.config.unpair2);
            assert_eq!(
                diagnostics,
                b"alias: -a option used without an argument; reverting to historical behavior\n"
            );

            let (numbered_a, numbered_diagnostics) =
                parse_ok(&[b"alias", b"-a", b"1", b"left", b"right"], false);
            assert!(numbered_a.config.unpair1);
            assert!(!numbered_a.config.unpair2);
            assert!(numbered_diagnostics.is_empty());

            let mut malformed = argv(&[b"alias", b"-j3", b"left", b"right"]);
            diagnostics.clear();
            assert!(matches!(
                obsolete(&mut malformed, &mut diagnostics),
                Err(AppError::Usage)
            ));
            assert_eq!(diagnostics, b"alias: unknown option -- j3\n");

            let mut malformed_value = argv(&[b"alias", b"-e", b"-j12", b"left", b"right"]);
            diagnostics.clear();
            assert!(matches!(
                obsolete(&mut malformed_value, &mut diagnostics),
                Err(AppError::Usage)
            ));
            assert_eq!(diagnostics, b"alias: unknown option -- j12\n");

            let (repeated, _) = parse_ok(
                &[
                    b"join", b"-1", b"2", b"-j", b"3", b"-2", b"4", b"-eold", b"-e", b"new",
                    b"-t:", b"-t", b"", b"-a1", b"-a2", b"left", b"right",
                ],
                false,
            );
            assert_eq!(repeated.config.joinf1, 2);
            assert_eq!(repeated.config.joinf2, 3);
            assert_eq!(repeated.config.empty, Some(b"new".to_vec()));
            assert!(repeated.config.delimiters.is_empty());
            assert_eq!(repeated.config.output_separator, 0);
            assert!(repeated.config.unpair1 && repeated.config.unpair2);

            let (status, _, diagnostics, opener) = run_case(
                argv(&[b"/tmp/alias", b"-a1", b"-v2", b"left", b"right"]),
                &[],
                b"",
            );
            assert_eq!(status, STATUS_ERROR);
            assert_eq!(
                diagnostics,
                b"alias: the -a and -v options are mutually exclusive\n"
            );
            assert!(opener.open_order.is_empty());

            let (status, _, diagnostics, _) = run_case(argv(&[b"/tmp/alias", b"only"]), &[], b"");
            assert_eq!(status, STATUS_ERROR);
            assert_eq!(
                diagnostics,
                b"usage: alias [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n             [-o list] [-t char] file1 file2\n"
            );

            let (status, _, diagnostics, _) =
                run_case(argv(&[b"./raw-name", b"-x", b"left", b"right"]), &[], b"");
            assert_eq!(status, STATUS_ERROR);
            assert_eq!(
                diagnostics,
                b"./raw-name: invalid option -- 'x'\nusage: raw-name [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n                [-o list] [-t char] file1 file2\n"
            );

            let (status, _, diagnostics, _) = run_case(argv(&[b"./raw-name", b"-1"]), &[], b"");
            assert_eq!(status, STATUS_ERROR);
            assert_eq!(
                diagnostics,
                b"./raw-name: option requires an argument -- '1'\nusage: raw-name [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n                [-o list] [-t char] file1 file2\n"
            );

            let (status, _, diagnostics, _) = run_case(
                argv(&[b"./raw-name", b"--foo", b"left", b"right"]),
                &[],
                b"",
            );
            assert_eq!(status, STATUS_ERROR);
            assert_eq!(
                diagnostics,
                b"./raw-name: invalid option -- '-'\nusage: raw-name [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n                [-o list] [-t char] file1 file2\n"
            );

            let mut stopped = argv(&[b"join", b"--foo", b"-j3", b"left", b"right"]);
            let mut stopped_diagnostics = Vec::new();
            obsolete(&mut stopped, &mut stopped_diagnostics).unwrap();
            assert!(stopped_diagnostics.is_empty());
            assert!(matches!(
                parse_args(&mut stopped, false, &mut stopped_diagnostics),
                Err(AppError::Usage)
            ));
            assert_eq!(stopped_diagnostics, b"join: invalid option -- '-'\n");
        }
    }

    mod numeric_compatibility {
        use super::*;

        #[test]
        fn c_strtol_matrix() {
            let cases: &[(&[u8], ParsedLong)] = &[
                (b"", ParsedLong { value: 0, end: 0 }),
                (b"0", ParsedLong { value: 0, end: 1 }),
                (b"x", ParsedLong { value: 0, end: 0 }),
                (b" \t+", ParsedLong { value: 0, end: 0 }),
                (b" \t+12x", ParsedLong { value: 12, end: 5 }),
                (b"\n\x0b\x0c\r42", ParsedLong { value: 42, end: 6 }),
                (b"-1", ParsedLong { value: -1, end: 2 }),
                (
                    b"9223372036854775807",
                    ParsedLong {
                        value: i64::MAX,
                        end: 19,
                    },
                ),
                (
                    b"-9223372036854775808",
                    ParsedLong {
                        value: i64::MIN,
                        end: 20,
                    },
                ),
                (
                    b"999999999999999999999999",
                    ParsedLong {
                        value: i64::MAX,
                        end: 24,
                    },
                ),
                (
                    b"-999999999999999999999999",
                    ParsedLong {
                        value: i64::MIN,
                        end: 25,
                    },
                ),
            ];
            for (input, expected) in cases {
                assert_eq!(parse_c_long(input), *expected);
            }

            assert_eq!(parse_join_field(b"-1", b"-1").unwrap(), usize::MAX - 1);
            assert_eq!(parse_join_field(b" +2", b"-j").unwrap(), 1);
            assert!(matches!(
                parse_join_field(b"0x10", b"-j"),
                Err(AppError::Message(message))
                    if message == b"-j option field number less than 1"
            ));
            assert!(matches!(
                parse_join_field(b"1x", b"-1"),
                Err(AppError::Message(message))
                    if message == b"illegal field number -- 1x"
            ));
            assert!(matches!(
                parse_file_number(b"xyz", b"-v"),
                Err(AppError::Message(message))
                    if message == b"-v option file number not 1 or 2"
            ));
            assert_eq!(parse_file_number(b" +2", b"-a").unwrap(), 2);
            assert!(matches!(
                parse_file_number(b"1x", b"-a"),
                Err(AppError::Message(message))
                    if message == b"illegal file number -- 1x"
            ));

            let mut list = vec![Olist {
                filenum: 1,
                fieldno: 8,
            }];
            fieldarg(b"0junk, 1.-1\t2.3,1.999999999999999999999999", &mut list).unwrap();
            assert_eq!(
                list,
                vec![
                    Olist {
                        filenum: 1,
                        fieldno: 8,
                    },
                    Olist {
                        filenum: 0,
                        fieldno: 0,
                    },
                    Olist {
                        filenum: 1,
                        fieldno: usize::MAX - 1,
                    },
                    Olist {
                        filenum: 2,
                        fieldno: 2,
                    },
                    Olist {
                        filenum: 1,
                        fieldno: (i64::MAX as usize) - 1,
                    },
                ]
            );
            assert!(matches!(
                fieldarg(b"1.0", &mut Vec::new()),
                Err(AppError::Message(message))
                    if message == b"field numbers are 1 based"
            ));
            assert!(matches!(
                fieldarg(b"1.", &mut Vec::new()),
                Err(AppError::Message(message))
                    if message == b"field numbers are 1 based"
            ));
            assert!(matches!(
                fieldarg(b"1.2x", &mut Vec::new()),
                Err(AppError::Message(message))
                    if message == b"malformed -o option field"
            ));
            assert!(matches!(
                fieldarg(b"3.1", &mut Vec::new()),
                Err(AppError::Message(message))
                    if message == b"malformed -o option field"
            ));
        }
    }

    mod tokenization_and_cmp {
        use super::*;

        #[test]
        fn byte_field_matrix() {
            let cases: Vec<(&[u8], &[u8], bool, Vec<&[u8]>)> = vec![
                (
                    b" \ta\tb  \n",
                    b" \t",
                    true,
                    vec![b"a".as_slice(), b"b".as_slice()],
                ),
                (b"\n", b" \t", true, vec![]),
                (
                    b"unterminated",
                    b" \t",
                    true,
                    vec![b"unterminated".as_slice()],
                ),
                (b"a\r\n", b" \t", true, vec![b"a\r".as_slice()]),
                (
                    b":a::\n",
                    b":",
                    false,
                    vec![
                        b"".as_slice(),
                        b"a".as_slice(),
                        b"".as_slice(),
                        b"".as_slice(),
                    ],
                ),
                (b"\n", b":", false, vec![b"".as_slice()]),
                (b"a:b\n", b"", false, vec![b"a:b".as_slice()]),
                (b"\n", b"", false, vec![b"".as_slice()]),
                (b"a\0ignored\n", b" \t", true, vec![b"a".as_slice()]),
                (
                    b"\xff \x80",
                    b" \t",
                    true,
                    vec![b"\xff".as_slice(), b"\x80".as_slice()],
                ),
                (b"a\n\n", b" \t", true, vec![b"a\n".as_slice()]),
            ];
            for (input, delimiters, spans, expected) in cases {
                let parsed = parse_line(input.to_vec(), delimiters, spans);
                assert_eq!(fields(&parsed), expected, "input: {input:?}");
            }

            let nul = parse_line(b"a\0ignored\n".to_vec(), b" \t", true);
            assert_eq!(nul.line, b"a");

            let missing = parse_line(Vec::new(), b" \t", true);
            let also_missing = parse_line(b" \t\n".to_vec(), b" \t", true);
            let present_empty = parse_line(Vec::new(), b":", false);
            assert_eq!(missing.field(usize::MAX), None);
            assert_eq!(cmp(&missing, 0, &also_missing, 0), Ordering::Equal);
            assert_eq!(cmp(&missing, 0, &present_empty, 0), Ordering::Less);
            assert_eq!(cmp(&present_empty, 0, &missing, 0), Ordering::Greater);
            assert_eq!(
                cmp(
                    &parse_line(b"10".to_vec(), b" \t", true),
                    0,
                    &parse_line(b"2".to_vec(), b" \t", true),
                    0,
                ),
                Ordering::Less
            );
            assert_eq!(
                cmp(
                    &parse_line(b"\xc3\xa9".to_vec(), b" \t", true),
                    0,
                    &parse_line(b"\xe6\xbc\xa2".to_vec(), b" \t", true),
                    0,
                ),
                Ordering::Less
            );
            assert_eq!(
                cmp(
                    &parse_line(b"\x80".to_vec(), b" \t", true),
                    0,
                    &parse_line(b"\x7f".to_vec(), b" \t", true),
                    0,
                ),
                Ordering::Greater
            );
        }
    }

    mod slurp_behavior {
        use super::*;

        #[test]
        fn grouping_and_read_error_matrix() {
            let config = Config::default();
            let mut single = Input::new(
                InputReader::Owned(Box::new(Cursor::new(b"solo value".to_vec()))),
                0,
                false,
                1,
            );
            slurp(&mut single, &config).unwrap();
            assert_eq!(single.set.len(), 1);
            assert_eq!(single.set[0].field(0), Some(b"solo".as_slice()));
            assert_eq!(single.set[0].field(1), Some(b"value".as_slice()));
            assert!(single.pending.is_none());
            slurp(&mut single, &config).unwrap();
            assert!(single.set.is_empty());

            let mut input = Input::new(
                InputReader::Owned(Box::new(Cursor::new(b"a 1\na 2\nb 3\n".to_vec()))),
                0,
                false,
                1,
            );
            slurp(&mut input, &config).unwrap();
            assert_eq!(input.set.len(), 2);
            assert_eq!(input.set[0].field(1), Some(b"1".as_slice()));
            assert_eq!(input.set[1].field(1), Some(b"2".as_slice()));
            assert!(input.pending.is_some());
            slurp(&mut input, &config).unwrap();
            assert_eq!(input.set.len(), 1);
            assert_eq!(input.set[0].field(0), Some(b"b".as_slice()));
            assert!(input.pending.is_none());
            slurp(&mut input, &config).unwrap();
            assert!(input.set.is_empty());

            let reader = FailingReader {
                bytes: Cursor::new(b"a 1\nb 2\n".to_vec()),
                fail_after: 4,
            };
            let mut failing = Input::new(
                InputReader::Owned(Box::new(BufReader::new(reader))),
                0,
                false,
                1,
            );
            slurp(&mut failing, &config).unwrap();
            assert_eq!(failing.set.len(), 1);
            slurp(&mut failing, &config).unwrap();
            assert!(failing.set.is_empty());

            let reader = FailingReader {
                bytes: Cursor::new(b"partial".to_vec()),
                fail_after: 2,
            };
            let mut partial_failure = Input::new(
                InputReader::Owned(Box::new(BufReader::new(reader))),
                0,
                false,
                1,
            );
            slurp(&mut partial_failure, &config).unwrap();
            assert!(partial_failure.set.is_empty());

            let mut missing_keys = Input::new(
                InputReader::Owned(Box::new(Cursor::new(b"a\nb\n".to_vec()))),
                usize::MAX,
                false,
                1,
            );
            slurp(&mut missing_keys, &config).unwrap();
            assert_eq!(missing_keys.set.len(), 2);

            let long_field = vec![b'x'; 32 * 1024];
            let mut records = b"k ".to_vec();
            records.extend_from_slice(&long_field);
            records.extend_from_slice(b"\nz next\n");
            let mut long_record = Input::new(
                InputReader::Owned(Box::new(BufReader::with_capacity(31, Cursor::new(records)))),
                0,
                false,
                1,
            );
            slurp(&mut long_record, &config).unwrap();
            assert_eq!(long_record.set.len(), 1);
            assert_eq!(long_record.set[0].field(1), Some(long_field.as_slice()));
            assert_eq!(
                long_record.pending.as_ref().and_then(|line| line.field(0)),
                Some(b"z".as_slice())
            );
        }
    }

    mod merge_behavior {
        use super::*;

        #[test]
        fn join_order_and_selection_matrix() {
            struct Case {
                name: &'static str,
                arguments: &'static [&'static [u8]],
                left: &'static [u8],
                right: &'static [u8],
                expected: &'static [u8],
            }

            const RICH_LEFT: &[u8] = b"a LA1\na LA2\nc LC1\nc LC2\ne LE\ng LG\ni LI1\ni LI2\n";
            const RICH_RIGHT: &[u8] = b"b RB\nc RC1\nc RC2\nd RD\ng RG\nh RH\nj RJ1\nj RJ2\n";

            let cases = [
                Case {
                    name: "no match",
                    arguments: &[b"join", b"left", b"right"],
                    left: b"a left\n",
                    right: b"b right\n",
                    expected: b"",
                },
                Case {
                    name: "equal singletons",
                    arguments: &[b"join", b"left", b"right"],
                    left: b"key left extra\n",
                    right: b"key right more\n",
                    expected: b"key left extra right more\n",
                },
                Case {
                    name: "selected join fields",
                    arguments: &[b"join", b"-1", b"3", b"-2", b"2", b"left", b"right"],
                    left: b"L 10 alpha tail\nM 20 beta end\n",
                    right: b"R alpha info\nS gamma other\n",
                    expected: b"alpha L 10 tail R info\n",
                },
                Case {
                    name: "one by many, many by one, and many by many",
                    arguments: &[b"join", b"left", b"right"],
                    left: b"a LA\nb LB1\nb LB2\nc LC1\nc LC2\n",
                    right: b"a RA1\na RA2\nb RB\nc RC1\nc RC2\n",
                    expected: b"a LA RA1\na LA RA2\nb LB1 RB\nb LB2 RB\nc LC1 RC1\nc LC1 RC2\nc LC2 RC1\nc LC2 RC2\n",
                },
                Case {
                    name: "missing-key Cartesian product",
                    arguments: &[
                        b"join", b"-1", b"-1", b"-2", b"-1", b"left", b"right",
                    ],
                    left: b"L1 p\nL2\n",
                    right: b"R1 q\nR2\n",
                    expected: b" L1 p R1 q\n L1 p R2\n L2 R1 q\n L2 R2\n",
                },
                Case {
                    name: "file 1 outer selection",
                    arguments: &[b"join", b"-a1", b"left", b"right"],
                    left: RICH_LEFT,
                    right: RICH_RIGHT,
                    expected: b"a LA1\na LA2\nc LC1 RC1\nc LC1 RC2\nc LC2 RC1\nc LC2 RC2\ne LE\ng LG RG\ni LI1\ni LI2\n",
                },
                Case {
                    name: "file 2 outer selection",
                    arguments: &[b"join", b"-a2", b"left", b"right"],
                    left: RICH_LEFT,
                    right: RICH_RIGHT,
                    expected: b"b RB\nc LC1 RC1\nc LC1 RC2\nc LC2 RC1\nc LC2 RC2\nd RD\ng LG RG\nh RH\nj RJ1\nj RJ2\n",
                },
                Case {
                    name: "full outer selection",
                    arguments: &[b"join", b"-a1", b"-a2", b"left", b"right"],
                    left: RICH_LEFT,
                    right: RICH_RIGHT,
                    expected: b"a LA1\na LA2\nb RB\nc LC1 RC1\nc LC1 RC2\nc LC2 RC1\nc LC2 RC2\nd RD\ne LE\ng LG RG\nh RH\ni LI1\ni LI2\nj RJ1\nj RJ2\n",
                },
                Case {
                    name: "file 1 anti-join",
                    arguments: &[b"join", b"-v1", b"left", b"right"],
                    left: RICH_LEFT,
                    right: RICH_RIGHT,
                    expected: b"a LA1\na LA2\ne LE\ni LI1\ni LI2\n",
                },
                Case {
                    name: "file 2 anti-join",
                    arguments: &[b"join", b"-v2", b"left", b"right"],
                    left: RICH_LEFT,
                    right: RICH_RIGHT,
                    expected: b"b RB\nd RD\nh RH\nj RJ1\nj RJ2\n",
                },
                Case {
                    name: "symmetric difference",
                    arguments: &[b"join", b"-v1", b"-v2", b"left", b"right"],
                    left: RICH_LEFT,
                    right: RICH_RIGHT,
                    expected: b"a LA1\na LA2\nb RB\nd RD\ne LE\nh RH\ni LI1\ni LI2\nj RJ1\nj RJ2\n",
                },
                Case {
                    name: "file 1 tail after file 2 exhaustion",
                    arguments: &[b"join", b"-a1", b"left", b"right"],
                    left: b"z L1\nz L2\n",
                    right: b"",
                    expected: b"z L1\nz L2\n",
                },
                Case {
                    name: "file 2 tail after file 1 exhaustion",
                    arguments: &[b"join", b"-a2", b"left", b"right"],
                    left: b"",
                    right: b"a R1\nb R2\n",
                    expected: b"a R1\nb R2\n",
                },
                Case {
                    name: "deterministic unsorted full outer merge",
                    arguments: &[b"join", b"-a1", b"-a2", b"left", b"right"],
                    left: b"b LB1\na LA\nb LB2\n",
                    right: b"a RA1\nb RB\na RA2\n",
                    expected: b"a RA1\nb LB1 RB\na LA RA2\nb LB2\n",
                },
            ];

            for case in cases {
                let files = [
                    (b"left".as_slice(), case.left),
                    (b"right".as_slice(), case.right),
                ];
                let (status, output, diagnostics, _) = run_case(argv(case.arguments), &files, b"");
                assert_eq!(status, STATUS_SUCCESS, "{}", case.name);
                assert_eq!(output, case.expected, "{}", case.name);
                assert!(diagnostics.is_empty(), "{}", case.name);
            }
        }
    }

    mod output_behavior {
        use super::*;

        #[test]
        fn formatting_and_writer_error_matrix() {
            struct Case {
                name: &'static str,
                arguments: &'static [&'static [u8]],
                left: &'static [u8],
                right: &'static [u8],
                expected: &'static [u8],
            }

            let cases = [
                Case {
                    name: "file 1 default layout",
                    arguments: &[b"join", b"-a1", b"left", b"right"],
                    left: b"a left extra\n",
                    right: b"z right\n",
                    expected: b"a left extra\n",
                },
                Case {
                    name: "file 2 default layout",
                    arguments: &[b"join", b"-a2", b"left", b"right"],
                    left: b"a left\n",
                    right: b"z right extra\n",
                    expected: b"z right extra\n",
                },
                Case {
                    name: "file 1 nonzero join index",
                    arguments: &[b"join", b"-1", b"2", b"-a1", b"left", b"right"],
                    left: b"head b tail\n",
                    right: b"z right\n",
                    expected: b"b head tail\n",
                },
                Case {
                    name: "file 2 nonzero join index",
                    arguments: &[b"join", b"-2", b"3", b"-a2", b"left", b"right"],
                    left: b"a left\n",
                    right: b"head payload z\n",
                    expected: b"z head payload\n",
                },
                Case {
                    name: "file 1 missing join key",
                    arguments: &[b"join", b"-1", b"3", b"-a1", b"left", b"right"],
                    left: b"a payload\n",
                    right: b"z right\n",
                    expected: b" a payload\n",
                },
                Case {
                    name: "file 2 missing join key",
                    arguments: &[b"join", b"-2", b"3", b"-a2", b"left", b"right"],
                    left: b"z left\n",
                    right: b"a payload\n",
                    expected: b" a payload\n",
                },
                Case {
                    name: "file 1 record without payload fields",
                    arguments: &[b"join", b"-a1", b"left", b"right"],
                    left: b"a\n",
                    right: b"z payload\n",
                    expected: b"a\n",
                },
                Case {
                    name: "file 2 record without payload fields",
                    arguments: &[b"join", b"-a2", b"left", b"right"],
                    left: b"a payload\n",
                    right: b"z\n",
                    expected: b"z\n",
                },
                Case {
                    name: "record without key or payload fields",
                    arguments: &[b"join", b"-1", b"2", b"-a1", b"left", b"right"],
                    left: b"\n",
                    right: b"z payload\n",
                    expected: b"\n",
                },
                Case {
                    name: "matched missing join keys",
                    arguments: &[b"join", b"-1", b"-1", b"-2", b"-1", b"left", b"right"],
                    left: b"left\n",
                    right: b"right\n",
                    expected: b" left right\n",
                },
                Case {
                    name: "ordered selectors with repeated join keys",
                    arguments: &[b"join", b"-o", b"2.2,0,1.1,0,1.3,2.1", b"left", b"right"],
                    left: b"k L X\n",
                    right: b"k R Y\n",
                    expected: b"R k k k X k\n",
                },
                Case {
                    name: "selector options append and split on comma space and tab",
                    arguments: &[
                        b"join",
                        b"-o",
                        b"2.2,0",
                        b"-o",
                        b" 1.2,\t0 ",
                        b"left",
                        b"right",
                    ],
                    left: b"k L\n",
                    right: b"k R\n",
                    expected: b"R k L k\n",
                },
                Case {
                    name: "replacement distinguishes missing from present empty fields",
                    arguments: &[
                        b"join",
                        b"-t:",
                        b"-eM",
                        b"-o0,1.2,1.4,2.3,2.4",
                        b"left",
                        b"right",
                    ],
                    left: b"k::L\n",
                    right: b"k:R:\n",
                    expected: b"k::M::M\n",
                },
                Case {
                    name: "default custom-delimiter layout preserves empty fields",
                    arguments: &[b"join", b"-t:", b"left", b"right"],
                    left: b"k::L\n",
                    right: b"k:R:\n",
                    expected: b"k::L:R:\n",
                },
                Case {
                    name: "empty delimiter emits NUL separators",
                    arguments: &[b"join", b"-t", b"", b"-o", b"0,0,1.2", b"left", b"right"],
                    left: b"key\n",
                    right: b"key\n",
                    expected: b"key\0key\0\n",
                },
                Case {
                    name: "replacement bytes are emitted without interpretation",
                    arguments: &[
                        b"join",
                        b"-t|",
                        b"-e",
                        b"<|\n\xff>",
                        b"-o",
                        b"0,1.2,2.2",
                        b"left",
                        b"right",
                    ],
                    left: b"k\n",
                    right: b"k\n",
                    expected: b"k|<|\n\xff>|<|\n\xff>\n",
                },
                Case {
                    name: "file 1 selectors force absent-file replacements",
                    arguments: &[
                        b"join",
                        b"-t:",
                        b"-a1",
                        b"-eX",
                        b"-o0,1.2,2.1,2.3,1.4",
                        b"left",
                        b"right",
                    ],
                    left: b"a:L\n",
                    right: b"z:R\n",
                    expected: b"a:L:X:X:X\n",
                },
                Case {
                    name: "file 2 absent-file selectors retain empty positions",
                    arguments: &[b"join", b"-a2", b"-o1.1,0,2.2,1.3", b"left", b"right"],
                    left: b"a L\n",
                    right: b"z R\n",
                    expected: b" z R \n",
                },
                Case {
                    name: "unpaired zero selectors use the present nonzero join field",
                    arguments: &[
                        b"join",
                        b"-1",
                        b"2",
                        b"-a1",
                        b"-o0,0,1.1,2.2",
                        b"left",
                        b"right",
                    ],
                    left: b"head k tail\n",
                    right: b"z R\n",
                    expected: b"k k head \n",
                },
                Case {
                    name: "matched and unpaired rows share replacement semantics",
                    arguments: &[
                        b"join",
                        b"-t:",
                        b"-a1",
                        b"-eX",
                        b"-o0,1.2,2.3",
                        b"left",
                        b"right",
                    ],
                    left: b"a:\nb:L\n",
                    right: b"a:R\n",
                    expected: b"a::X\nb:L:X\n",
                },
                Case {
                    name: "last delimiter controls tokenization and output",
                    arguments: &[b"join", b"-t:", b"-t|", b"left", b"right"],
                    left: b"k|L\n",
                    right: b"k|R\n",
                    expected: b"k|L|R\n",
                },
                Case {
                    name: "single-byte C-locale delimiter includes ASCII DEL",
                    arguments: &[b"join", b"-t\x7f", b"left", b"right"],
                    left: b"k\x7fL\n",
                    right: b"k\x7fR\n",
                    expected: b"k\x7fL\x7fR\n",
                },
                Case {
                    name: "last replacement value wins",
                    arguments: &[
                        b"join", b"-eOLD", b"-e", b"NEW", b"-o0,1.3", b"left", b"right",
                    ],
                    left: b"k L\n",
                    right: b"k R\n",
                    expected: b"k NEW\n",
                },
            ];

            for case in cases {
                let files = [
                    (b"left".as_slice(), case.left),
                    (b"right".as_slice(), case.right),
                ];
                let (status, output, diagnostics, _) = run_case(argv(case.arguments), &files, b"");
                assert_eq!(status, STATUS_SUCCESS, "{}", case.name);
                assert_eq!(output, case.expected, "{}", case.name);
                assert!(diagnostics.is_empty(), "{}", case.name);
            }

            for delimiter in [b"::".as_slice(), b"\xc3\xa9".as_slice(), b"\xff".as_slice()] {
                let (status, output, diagnostics, opener) = run_case(
                    argv(&[b"join", b"-t", delimiter, b"left", b"right"]),
                    &[],
                    b"",
                );
                assert_eq!(status, STATUS_ERROR, "delimiter: {delimiter:?}");
                assert!(output.is_empty(), "delimiter: {delimiter:?}");
                assert_eq!(
                    diagnostics, b"join: illegal tab character specification\n",
                    "delimiter: {delimiter:?}"
                );
                assert!(opener.open_order.is_empty(), "delimiter: {delimiter:?}");
            }

            let mut opener = MemoryOpener::default();
            opener.files.insert(b"left".to_vec(), b"k:\n".to_vec());
            opener.files.insert(b"right".to_vec(), b"k:\n".to_vec());
            let mut stdin = Cursor::new(Vec::new());
            let mut output = FailingWriter::on_call(1);
            let mut diagnostics = Vec::new();
            let status = run_with(
                argv(&[b"join", b"-t:", b"-o1.2,2.2", b"left", b"right"]),
                &mut stdin,
                &mut opener,
                &mut output,
                &mut diagnostics,
            );
            assert_eq!(status, STATUS_ERROR);
            assert!(output.bytes.is_empty());
            assert_eq!(output.calls, 1);
            assert_eq!(output.flushes, 0);
            assert_eq!(diagnostics, b"join: stdout: injected write failure\n");
        }
    }

    mod boundary_behavior {
        use super::*;

        #[test]
        fn run_with_and_opening_matrix() {
            let files = [
                (b"first".as_slice(), b"a one\n".as_slice()),
                (b"second".as_slice(), b"a two\n".as_slice()),
            ];
            let (status, output, diagnostics, opener) =
                run_case(argv(&[b"/tmp/alias", b"first", b"second"]), &files, b"");
            assert_eq!(status, 0);
            assert_eq!(output, b"a one two\n");
            assert!(diagnostics.is_empty());
            assert_eq!(
                opener.open_order,
                vec![b"first".to_vec(), b"second".to_vec()]
            );

            let mut opener = MemoryOpener::default();
            opener.failures.insert(b"missing".to_vec(), 2);
            let mut stdin = Cursor::new(Vec::new());
            let mut output = Vec::new();
            let mut diagnostics = Vec::new();
            let status = run_with(
                argv(&[b"/tmp/alias", b"missing", b"second"]),
                &mut stdin,
                &mut opener,
                &mut output,
                &mut diagnostics,
            );
            assert_eq!(status, 1);
            assert_eq!(opener.open_order, vec![b"missing".to_vec()]);
            assert_eq!(diagnostics, b"alias: missing: No such file or directory\n");

            let mut opener = MemoryOpener::default();
            opener.files.insert(b"first".to_vec(), Vec::new());
            opener.failures.insert(b"missing".to_vec(), 2);
            let mut stdin = Cursor::new(Vec::new());
            let mut output = Vec::new();
            diagnostics.clear();
            let status = run_with(
                argv(&[b"alias", b"first", b"missing"]),
                &mut stdin,
                &mut opener,
                &mut output,
                &mut diagnostics,
            );
            assert_eq!(status, STATUS_ERROR);
            assert_eq!(
                opener.open_order,
                vec![b"first".to_vec(), b"missing".to_vec()]
            );
            assert_eq!(diagnostics, b"alias: missing: No such file or directory\n");

            let mut opener = MemoryOpener::default();
            opener.failures.insert(Vec::new(), 2);
            let mut stdin = Cursor::new(Vec::new());
            let mut output = Vec::new();
            diagnostics.clear();
            let status = run_with(
                argv(&[b"alias", b"", b"second"]),
                &mut stdin,
                &mut opener,
                &mut output,
                &mut diagnostics,
            );
            assert_eq!(status, STATUS_ERROR);
            assert_eq!(opener.open_order, vec![Vec::new()]);
            assert_eq!(diagnostics, b"alias: : No such file or directory\n");

            let raw_path = b"missing\xff".as_slice();
            let mut opener = MemoryOpener::default();
            opener.failures.insert(raw_path.to_vec(), 2);
            let mut stdin = Cursor::new(Vec::new());
            let mut output = Vec::new();
            diagnostics.clear();
            let status = run_with(
                vec![
                    b"/tmp/alias".to_vec(),
                    raw_path.to_vec(),
                    b"second".to_vec(),
                ],
                &mut stdin,
                &mut opener,
                &mut output,
                &mut diagnostics,
            );
            assert_eq!(status, STATUS_ERROR);
            assert_eq!(opener.open_order, vec![raw_path.to_vec()]);
            assert_eq!(
                diagnostics,
                b"alias: missing\xff: No such file or directory\n"
            );

            let stdin_files = [(b"right".as_slice(), b"a file\n".as_slice())];
            let (status, output, _, opener) =
                run_case(argv(&[b"join", b"-", b"right"]), &stdin_files, b"a stdin\n");
            assert_eq!(status, 0);
            assert_eq!(output, b"a stdin file\n");
            assert_eq!(opener.open_order, vec![b"right".to_vec()]);

            let stdin_files = [(b"left".as_slice(), b"a file\n".as_slice())];
            let (status, output, diagnostics, opener) =
                run_case(argv(&[b"join", b"left", b"-"]), &stdin_files, b"a stdin\n");
            assert_eq!(status, STATUS_SUCCESS);
            assert_eq!(output, b"a file stdin\n");
            assert!(diagnostics.is_empty());
            assert_eq!(opener.open_order, vec![b"left".to_vec()]);

            let (status, _, diagnostics, opener) = run_case(argv(&[b"join", b"-", b"-"]), &[], b"");
            assert_eq!(status, 1);
            assert_eq!(diagnostics, b"join: only one input file may be stdin\n");
            assert!(opener.open_order.is_empty());

            let (status, _, diagnostics, _) = run_case(argv(&[b"/tmp/alias", b"-a"]), &[], b"");
            assert_eq!(status, 1);
            assert_eq!(
                diagnostics,
                b"alias: -a option used without an argument; reverting to historical behavior\nusage: alias [-1 field] [-2 field] [-a file_number | -v file_number] [-e string]\n             [-o list] [-t char] file1 file2\n"
            );

            let mut opener = MemoryOpener::default();
            opener.failures.insert(b"missing".to_vec(), 2);
            let mut stdin = Cursor::new(Vec::new());
            let mut output = Vec::new();
            let mut diagnostics = Vec::new();
            let status = run_with(
                argv(&[b"/tmp/alias", b"-a", b"missing", b"right"]),
                &mut stdin,
                &mut opener,
                &mut output,
                &mut diagnostics,
            );
            assert_eq!(status, STATUS_ERROR);
            assert_eq!(opener.open_order, vec![b"missing".to_vec()]);
            assert_eq!(
                diagnostics,
                b"alias: -a option used without an argument; reverting to historical behavior\nalias: missing: No such file or directory\n"
            );

            for (fail_on_call, expected_prefix) in [
                (1, b"".as_slice()),
                (2, b"a".as_slice()),
                (3, b"a ".as_slice()),
                (4, b"a one".as_slice()),
                (5, b"a one ".as_slice()),
                (6, b"a one two".as_slice()),
            ] {
                let mut opener = MemoryOpener::default();
                opener.files.insert(b"first".to_vec(), b"a one\n".to_vec());
                opener.files.insert(b"second".to_vec(), b"a two\n".to_vec());
                let mut stdin = Cursor::new(Vec::new());
                let mut output = FailingWriter::on_call(fail_on_call);
                let mut diagnostics = Vec::new();
                let status = run_with(
                    argv(&[b"join", b"first", b"second"]),
                    &mut stdin,
                    &mut opener,
                    &mut output,
                    &mut diagnostics,
                );

                assert_eq!(status, STATUS_ERROR, "write call {fail_on_call}");
                assert_eq!(output.bytes, expected_prefix, "write call {fail_on_call}");
                assert_eq!(output.calls, fail_on_call, "write call {fail_on_call}");
                assert_eq!(output.flushes, 0, "write call {fail_on_call}");
                assert_eq!(
                    diagnostics, b"join: stdout: injected write failure\n",
                    "write call {fail_on_call}"
                );
            }

            let mut opener = MemoryOpener::default();
            opener.files.insert(b"first".to_vec(), b"a one\n".to_vec());
            opener.files.insert(b"second".to_vec(), b"a two\n".to_vec());
            let mut stdin = Cursor::new(Vec::new());
            let mut output = FailingWriter::on_flush();
            let mut diagnostics = Vec::new();
            let status = run_with(
                argv(&[b"join", b"first", b"second"]),
                &mut stdin,
                &mut opener,
                &mut output,
                &mut diagnostics,
            );
            assert_eq!(status, STATUS_SUCCESS);
            assert_eq!(output.bytes, b"a one two\n");
            assert_eq!(output.calls, 6);
            assert_eq!(output.flushes, 0);
            assert!(diagnostics.is_empty());
        }
    }
}
