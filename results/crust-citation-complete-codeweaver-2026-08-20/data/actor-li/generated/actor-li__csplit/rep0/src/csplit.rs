use crate::regex_compat::parse_expression;
use std::ffi::{OsStr, OsString};
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, BufReader, Read, Seek, SeekFrom, Write};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::process::ExitCode;

pub(crate) const PATH_MAX: usize = 4096;
pub(crate) const LINE_MAX: usize = 2048;
pub(crate) const CHUNK_MAX: usize = LINE_MAX - 1;
pub(crate) const REVERSE_SCAN_SIZE: usize = 8192;
pub(crate) const C_LONG_MAX: i64 = i64::MAX;

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Config {
    pub(crate) prefix: OsString,
    pub(crate) sufflen: u32,
    pub(crate) silent: bool,
    pub(crate) keep: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ParsedArgs {
    pub(crate) config: Config,
    pub(crate) input: OsString,
    pub(crate) expressions: Vec<OsString>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct ParsedLong {
    pub(crate) value: i64,
    pub(crate) end: usize,
    pub(crate) overflow: bool,
    pub(crate) had_digits: bool,
}

#[derive(Debug)]
pub(crate) enum AppError {
    Usage { getopt_diagnostic: Option<Vec<u8>> },
    Message(Vec<u8>),
    Io { context: Vec<u8>, source: io::Error },
}

pub(crate) trait RegexMatcher {
    fn is_match(&self, bytes: &[u8]) -> bool;
}

pub(crate) trait RegexCompiler {
    fn compile(&self, pattern: &[u8]) -> Result<Box<dyn RegexMatcher>, AppError>;
}

pub(crate) trait OutputFile: Read + Write + Seek {
    fn set_len(&mut self, len: u64) -> io::Result<()>;
}

impl OutputFile for File {
    fn set_len(&mut self, len: u64) -> io::Result<()> {
        File::set_len(self, len)
    }
}

pub(crate) trait FileSystem {
    fn open_input(&mut self, path: &OsStr) -> io::Result<Box<dyn BufRead>>;
    fn create_output(&mut self, path: &OsStr) -> io::Result<Box<dyn OutputFile>>;
    fn temporary_output(&mut self) -> io::Result<Box<dyn OutputFile>>;
    fn remove_output(&mut self, path: &OsStr) -> io::Result<()>;
}

#[derive(Debug, Clone, Copy, Default)]
pub(crate) struct RealFileSystem;

impl FileSystem for RealFileSystem {
    fn open_input(&mut self, path: &OsStr) -> io::Result<Box<dyn BufRead>> {
        Ok(Box::new(BufReader::new(File::open(path)?)))
    }

    fn create_output(&mut self, path: &OsStr) -> io::Result<Box<dyn OutputFile>> {
        Ok(Box::new(
            OpenOptions::new()
                .read(true)
                .write(true)
                .create(true)
                .truncate(true)
                .open(path)?,
        ))
    }

    fn temporary_output(&mut self) -> io::Result<Box<dyn OutputFile>> {
        Ok(Box::new(tempfile::tempfile()?))
    }

    fn remove_output(&mut self, path: &OsStr) -> io::Result<()> {
        fs::remove_file(path)
    }
}

pub(crate) struct CInput<R: BufRead> {
    pub(crate) reader: R,
    pub(crate) eof_seen: bool,
    pub(crate) diagnostic_name: Vec<u8>,
}

impl<R: BufRead> CInput<R> {
    pub(crate) fn new(reader: R, diagnostic_name: Vec<u8>) -> Self {
        Self {
            reader,
            eof_seen: false,
            diagnostic_name,
        }
    }

    pub(crate) fn read_chunk_2047(&mut self) -> Result<Option<Vec<u8>>, AppError> {
        let mut chunk = Vec::with_capacity(CHUNK_MAX);

        while chunk.len() < CHUNK_MAX {
            let (consumed, newline_seen) = {
                let available = self.reader.fill_buf().map_err(|source| AppError::Io {
                    context: self.diagnostic_name.clone(),
                    source,
                })?;

                if available.is_empty() {
                    self.eof_seen = true;
                    return if chunk.is_empty() {
                        Ok(None)
                    } else {
                        Ok(Some(chunk))
                    };
                }

                let limit = available.len().min(CHUNK_MAX - chunk.len());
                let visible = &available[..limit];
                let newline = visible.iter().position(|byte| *byte == b'\n');
                let consumed = newline.map_or(limit, |index| index + 1);
                chunk.extend_from_slice(&visible[..consumed]);
                (consumed, newline.is_some())
            };

            self.reader.consume(consumed);
            if newline_seen {
                break;
            }
        }

        Ok(Some(chunk))
    }
}

pub(crate) struct PendingOverflow {
    pub(crate) file: Box<dyn OutputFile>,
    pub(crate) truncate_at: u64,
}

pub(crate) struct Csplit<F: FileSystem, R: BufRead> {
    pub(crate) config: Config,
    pub(crate) fs: F,
    pub(crate) input: CInput<R>,
    pub(crate) regex_compiler: Box<dyn RegexCompiler>,
    pub(crate) lineno: i64,
    pub(crate) reps: i64,
    pub(crate) nfiles: i64,
    pub(crate) maxfiles: i64,
    pub(crate) currfile: OsString,
    pub(crate) overflow: Option<PendingOverflow>,
    pub(crate) cleanup_armed: bool,
}

impl<F: FileSystem, R: BufRead> Csplit<F, R> {
    pub(crate) fn new(
        config: Config,
        fs: F,
        input: CInput<R>,
        regex_compiler: Box<dyn RegexCompiler>,
    ) -> Result<Self, AppError> {
        let maxfiles = compute_maxfiles(config.sufflen)?;
        let cleanup_armed = !config.keep;

        Ok(Self {
            config,
            fs,
            input,
            regex_compiler,
            lineno: 0,
            reps: 0,
            nfiles: 0,
            maxfiles,
            currfile: OsString::new(),
            overflow: None,
            cleanup_armed,
        })
    }

    pub(crate) fn run<W: Write>(
        &mut self,
        expressions: &[OsString],
        stdout: &mut W,
    ) -> Result<(), AppError> {
        let mut index = 0;
        while self.nfiles < self.maxfiles - 1 && index < expressions.len() {
            let expression = expressions[index].as_os_str().as_bytes();
            index += 1;

            self.reps = if index < expressions.len()
                && expressions[index].as_os_str().as_bytes().first() == Some(&b'{')
            {
                let parsed = parse_repetition(expressions[index].as_os_str().as_bytes())?;
                index += 1;
                parsed
            } else {
                0
            };

            match expression.first().copied() {
                Some(b'/' | b'%') => loop {
                    self.do_rexp(expression, stdout)?;
                    if self.reps == 0 || self.nfiles >= self.maxfiles - 1 {
                        break;
                    }
                    self.reps -= 1;
                },
                Some(byte) if byte.is_ascii_digit() => self.do_lineno(expression, stdout)?,
                _ => {
                    let mut message = expression.to_vec();
                    message.extend_from_slice(b": unrecognised pattern");
                    return Err(AppError::Message(message));
                }
            }
        }

        self.copy_remainder(stdout)
    }

    pub(crate) fn newfile(&mut self) -> Result<Box<dyn OutputFile>, AppError> {
        self.currfile = format_output_name(&self.config.prefix, self.config.sufflen, self.nfiles);
        if self.currfile.as_os_str().as_bytes().len() >= PATH_MAX {
            return Err(AppError::Io {
                context: self.currfile.as_os_str().as_bytes().to_vec(),
                source: io::Error::new(io::ErrorKind::InvalidFilename, "File name too long"),
            });
        }

        let output = self
            .fs
            .create_output(&self.currfile)
            .map_err(|source| AppError::Io {
                context: self.currfile.as_os_str().as_bytes().to_vec(),
                source,
            })?;
        self.nfiles = self
            .nfiles
            .checked_add(1)
            .ok_or_else(|| AppError::Message(b"too many output files".to_vec()))?;
        Ok(output)
    }

    pub(crate) fn cleanup(&mut self) {
        if !self.cleanup_armed {
            return;
        }

        for index in 0..self.nfiles {
            let path = format_output_name(&self.config.prefix, self.config.sufflen, index);
            let _ = self.fs.remove_output(&path);
        }
    }

    pub(crate) fn get_line(&mut self) -> Result<Option<Vec<u8>>, AppError> {
        if let Some(overflow) = self.overflow.as_mut() {
            if let Some(chunk) = read_output_chunk(&mut *overflow.file)? {
                self.lineno = self
                    .lineno
                    .checked_add(1)
                    .ok_or_else(|| AppError::Message(b"line number overflow".to_vec()))?;
                return Ok(Some(chunk));
            }
        }

        let chunk = self.input.read_chunk_2047()?;
        if chunk.is_some() {
            self.lineno = self
                .lineno
                .checked_add(1)
                .ok_or_else(|| AppError::Message(b"line number overflow".to_vec()))?;
        }
        Ok(chunk)
    }

    pub(crate) fn toomuch(
        &mut self,
        output: Option<Box<dyn OutputFile>>,
        count: u64,
    ) -> Result<(), AppError> {
        if let Some(mut previous) = self.overflow.take() {
            previous.file.flush().map_err(|source| AppError::Io {
                context: b"overflow".to_vec(),
                source,
            })?;
            previous
                .file
                .set_len(previous.truncate_at)
                .map_err(|source| AppError::Io {
                    context: b"overflow".to_vec(),
                    source,
                })?;
            drop(previous);
        }

        if count == 0 {
            return Ok(());
        }

        let mut file =
            output.ok_or_else(|| AppError::Message(b"can't read overflowed output".to_vec()))?;
        let adjusted_lineno = i128::from(self.lineno)
            .checked_sub(i128::from(count))
            .ok_or_else(|| AppError::Message(b"line number overflow".to_vec()))?;
        self.lineno = i64::try_from(adjusted_lineno)
            .map_err(|_| AppError::Message(b"line number overflow".to_vec()))?;

        let scan_size = u64::try_from(REVERSE_SCAN_SIZE)
            .map_err(|_| AppError::Message(b"offset overflow".to_vec()))?;
        let mut remaining = count;
        let final_position = loop {
            let current = file
                .seek(SeekFrom::Current(0))
                .map_err(|_| self.cant_seek_error())?;
            let block_start = current.saturating_sub(scan_size);
            file.seek(SeekFrom::Start(block_start))
                .map_err(|_| self.cant_seek_error())?;

            let mut block = vec![0; REVERSE_SCAN_SIZE];
            let mut nread = 0;
            while nread < block.len() {
                match file.read(&mut block[nread..]) {
                    Ok(0) => break,
                    Ok(amount) => nread += amount,
                    Err(_) => {
                        return Err(AppError::Message(b"can't read overflowed output".to_vec()))
                    }
                }
            }
            if nread == 0 {
                return Err(AppError::Message(b"can't read overflowed output".to_vec()));
            }

            file.seek(SeekFrom::Start(block_start))
                .map_err(|source| self.output_io_error(source))?;

            let mut selected = None;
            for reverse_index in 1..=nread {
                if block[nread - reverse_index] == b'\n' {
                    if remaining == 0 {
                        let relative = u64::try_from(nread - reverse_index + 1)
                            .map_err(|_| AppError::Message(b"offset overflow".to_vec()))?;
                        selected = Some(
                            block_start
                                .checked_add(relative)
                                .ok_or_else(|| AppError::Message(b"offset overflow".to_vec()))?,
                        );
                        break;
                    }
                    remaining -= 1;
                }
            }

            if let Some(position) = selected {
                break position;
            }
            if block_start == 0 || remaining == 0 {
                break block_start;
            }
        };

        file.seek(SeekFrom::Start(final_position))
            .map_err(|source| self.output_io_error(source))?;
        self.overflow = Some(PendingOverflow {
            file,
            truncate_at: final_position,
        });
        Ok(())
    }

    pub(crate) fn do_rexp<W: Write>(
        &mut self,
        expression: &[u8],
        stdout: &mut W,
    ) -> Result<(), AppError> {
        let parsed = parse_expression(expression)?;
        let matcher = self.regex_compiler.compile(parsed.pattern)?;
        let saved = parsed.delimiter == b'/';
        let mut output = if saved {
            self.newfile()?
        } else {
            self.fs.temporary_output().map_err(|source| AppError::Io {
                context: b"tmpfile".to_vec(),
                source,
            })?
        };

        let mut first = true;
        let mut matched = false;
        while let Some(chunk) = self.get_line()? {
            write_visible(&mut *output, &chunk, self.output_context(saved))?;
            if !first && matcher.is_match(c_visible(&chunk)) {
                matched = true;
                break;
            }
            first = false;
        }

        if !matched {
            self.toomuch(None, 0)?;
            let mut message = parsed.pattern.to_vec();
            message.extend_from_slice(b": no match");
            return Err(AppError::Message(message));
        }

        if parsed.offset <= 0 {
            let count = parsed.offset.unsigned_abs().checked_add(1).ok_or_else(|| {
                let mut message = parsed.pattern.to_vec();
                message.extend_from_slice(b": bad offset");
                AppError::Message(message)
            })?;
            self.toomuch(Some(output), count)?;
            if saved && !self.config.silent {
                let written = self
                    .overflow
                    .as_ref()
                    .map(|pending| pending.truncate_at)
                    .unwrap_or(0);
                write_count(stdout, written)?;
            }
        } else {
            let mut additional = parsed.offset - 1;
            while additional > 0 {
                let Some(chunk) = self.get_line()? else {
                    break;
                };
                write_visible(&mut *output, &chunk, self.output_context(saved))?;
                additional -= 1;
            }
            self.toomuch(None, 0)?;
            let written = output
                .seek(SeekFrom::Current(0))
                .map_err(|source| self.output_io_error(source))?;
            output.flush().map_err(|source| AppError::Io {
                context: self.output_context(saved),
                source,
            })?;
            drop(output);
            if saved && !self.config.silent {
                write_count(stdout, written)?;
            }
        }

        Ok(())
    }

    pub(crate) fn do_lineno<W: Write>(
        &mut self,
        expression: &[u8],
        stdout: &mut W,
    ) -> Result<(), AppError> {
        let parsed = parse_c_long(expression);
        if !parsed.had_digits
            || parsed.overflow
            || parsed.value <= 0
            || parsed.end != expression.len()
        {
            let mut message = expression.to_vec();
            message.extend_from_slice(b": bad line number");
            return Err(AppError::Message(message));
        }

        let target = parsed.value;
        let mut lastline = target;
        if lastline <= self.lineno {
            let mut message = expression.to_vec();
            message.extend_from_slice(b": can't go backwards");
            return Err(AppError::Message(message));
        }

        while self.nfiles < self.maxfiles - 1 {
            let mut output = self.newfile()?;
            while self
                .lineno
                .checked_add(1)
                .ok_or_else(|| AppError::Message(b"line number overflow".to_vec()))?
                != lastline
            {
                let Some(chunk) = self.get_line()? else {
                    let mut message = lastline.to_string().into_bytes();
                    message.extend_from_slice(b": out of range");
                    return Err(AppError::Message(message));
                };
                write_visible(
                    &mut *output,
                    &chunk,
                    self.currfile.as_os_str().as_bytes().to_vec(),
                )?;
            }

            let written = output
                .seek(SeekFrom::Current(0))
                .map_err(|source| self.output_io_error(source))?;
            if !self.config.silent {
                write_count(stdout, written)?;
            }
            output.flush().map_err(|source| AppError::Io {
                context: self.currfile.as_os_str().as_bytes().to_vec(),
                source,
            })?;
            drop(output);

            if self.reps == 0 {
                break;
            }
            self.reps -= 1;
            lastline = lastline
                .checked_add(target)
                .ok_or_else(|| AppError::Message(b"line number overflow".to_vec()))?;
        }
        Ok(())
    }

    pub(crate) fn copy_remainder<W: Write>(&mut self, stdout: &mut W) -> Result<(), AppError> {
        if !self.input.eof_seen {
            let mut output = self.newfile()?;
            while let Some(chunk) = self.get_line()? {
                write_visible(
                    &mut *output,
                    &chunk,
                    self.currfile.as_os_str().as_bytes().to_vec(),
                )?;
            }
            let written = output
                .seek(SeekFrom::Current(0))
                .map_err(|source| self.output_io_error(source))?;
            if !self.config.silent {
                write_count(stdout, written)?;
            }
            output.flush().map_err(|source| AppError::Io {
                context: self.currfile.as_os_str().as_bytes().to_vec(),
                source,
            })?;
        }

        self.toomuch(None, 0)?;
        self.cleanup_armed = false;
        Ok(())
    }

    fn output_context(&self, saved: bool) -> Vec<u8> {
        if saved {
            self.currfile.as_os_str().as_bytes().to_vec()
        } else {
            b"tmpfile".to_vec()
        }
    }

    fn output_io_error(&self, source: io::Error) -> AppError {
        AppError::Io {
            context: self.currfile.as_os_str().as_bytes().to_vec(),
            source,
        }
    }

    fn cant_seek_error(&self) -> AppError {
        let mut message = self.currfile.as_os_str().as_bytes().to_vec();
        message.extend_from_slice(b": can't seek");
        AppError::Message(message)
    }
}

pub(crate) fn parse_c_long(bytes: &[u8]) -> ParsedLong {
    let mut index = 0;
    while bytes
        .get(index)
        .is_some_and(|byte| matches!(byte, b' ' | b'\t' | b'\n' | 0x0b | 0x0c | b'\r'))
    {
        index += 1;
    }

    let negative = match bytes.get(index) {
        Some(b'+') => {
            index += 1;
            false
        }
        Some(b'-') => {
            index += 1;
            true
        }
        _ => false,
    };
    let digit_start = index;
    let limit = if negative {
        (C_LONG_MAX as u64) + 1
    } else {
        C_LONG_MAX as u64
    };
    let mut magnitude = 0_u64;
    let mut overflow = false;

    while let Some(byte @ b'0'..=b'9') = bytes.get(index).copied() {
        let digit = u64::from(byte - b'0');
        match magnitude
            .checked_mul(10)
            .and_then(|value| value.checked_add(digit))
        {
            Some(value) if value <= limit => magnitude = value,
            _ => {
                magnitude = limit;
                overflow = true;
            }
        }
        index += 1;
    }

    if index == digit_start {
        return ParsedLong {
            value: 0,
            end: 0,
            overflow: false,
            had_digits: false,
        };
    }

    let value = if negative {
        if magnitude == (C_LONG_MAX as u64) + 1 {
            i64::MIN
        } else {
            -(magnitude as i64)
        }
    } else {
        magnitude as i64
    };

    ParsedLong {
        value,
        end: index,
        overflow,
        had_digits: true,
    }
}

pub(crate) fn parse_args(argv: &[OsString], posixly_correct: bool) -> Result<ParsedArgs, AppError> {
    let argv0 = argv
        .first()
        .map(|value| value.as_os_str().as_bytes())
        .unwrap_or(b"csplit");
    let mut prefix = OsString::from("xx");
    let mut sufflen = 2_i64;
    let mut silent = false;
    let mut keep = false;
    let mut operands = Vec::new();
    let mut index = 1;

    while index < argv.len() {
        let bytes = argv[index].as_os_str().as_bytes();
        if bytes == b"--" {
            operands.extend(argv[index + 1..].iter().cloned());
            break;
        }
        if bytes.len() < 2 || bytes[0] != b'-' {
            if posixly_correct {
                operands.extend(argv[index..].iter().cloned());
                break;
            }
            operands.push(argv[index].clone());
            index += 1;
            continue;
        }

        let mut option_index = 1;
        while option_index < bytes.len() {
            let option = bytes[option_index];
            option_index += 1;
            match option {
                b'k' => keep = true,
                b's' => silent = true,
                b'f' | b'n' => {
                    let argument = if option_index < bytes.len() {
                        OsString::from_vec(bytes[option_index..].to_vec())
                    } else {
                        index += 1;
                        if index >= argv.len() {
                            return Err(AppError::Usage {
                                getopt_diagnostic: Some(getopt_diagnostic(
                                    argv0,
                                    b"option requires an argument",
                                    option,
                                )),
                            });
                        }
                        argv[index].clone()
                    };

                    if option == b'f' {
                        prefix = argument;
                    } else {
                        let raw = argument.as_os_str().as_bytes();
                        let parsed = parse_c_long(raw);
                        if !parsed.had_digits
                            || parsed.overflow
                            || parsed.value <= 0
                            || parsed.end != raw.len()
                        {
                            let mut message = raw.to_vec();
                            message.extend_from_slice(b": bad suffix length");
                            return Err(AppError::Message(message));
                        }
                        sufflen = parsed.value;
                    }
                    break;
                }
                _ => {
                    return Err(AppError::Usage {
                        getopt_diagnostic: Some(getopt_diagnostic(
                            argv0,
                            b"invalid option",
                            option,
                        )),
                    });
                }
            }
        }
        index += 1;
    }

    let prefix_len = prefix.as_os_str().as_bytes().len();
    if usize::try_from(sufflen)
        .ok()
        .and_then(|width| prefix_len.checked_add(width))
        .is_none_or(|length| length >= PATH_MAX)
    {
        return Err(AppError::Message(b"name too long".to_vec()));
    }

    let Some(input) = operands.first().cloned() else {
        return Err(AppError::Usage {
            getopt_diagnostic: None,
        });
    };

    Ok(ParsedArgs {
        config: Config {
            prefix,
            sufflen: sufflen as u32,
            silent,
            keep,
        },
        input,
        expressions: operands[1..].to_vec(),
    })
}

pub(crate) fn parse_repetition(bytes: &[u8]) -> Result<i64, AppError> {
    let body = bytes.get(1..).unwrap_or_default();
    let parsed = parse_c_long(body);
    if parsed.overflow || parsed.value < 0 || body.get(parsed.end) != Some(&b'}') {
        let mut message = body.to_vec();
        message.extend_from_slice(b": bad repetition count");
        return Err(AppError::Message(message));
    }
    Ok(parsed.value)
}

pub(crate) fn compute_maxfiles(sufflen: u32) -> Result<i64, AppError> {
    let mut maxfiles = 1_i64;
    for index in 0..sufflen {
        if maxfiles > C_LONG_MAX / 10 {
            let message = format!("{sufflen}: suffix too long (limit {index})").into_bytes();
            return Err(AppError::Message(message));
        }
        maxfiles *= 10;
    }
    Ok(maxfiles)
}

pub(crate) fn format_output_name(prefix: &OsStr, width: u32, index: i64) -> OsString {
    let mut bytes = prefix.as_bytes().to_vec();
    let number = index.to_string();
    let padding = usize::try_from(width)
        .unwrap_or(usize::MAX)
        .saturating_sub(number.len());
    bytes.extend(std::iter::repeat_n(b'0', padding));
    bytes.extend_from_slice(number.as_bytes());
    OsString::from_vec(bytes)
}

pub(crate) fn c_visible(chunk: &[u8]) -> &[u8] {
    &chunk[..chunk
        .iter()
        .position(|byte| *byte == b'\0')
        .unwrap_or(chunk.len())]
}

pub(crate) fn basename_bytes(argv0: &OsStr) -> Vec<u8> {
    let bytes = argv0.as_bytes();
    bytes
        .iter()
        .rposition(|byte| *byte == b'/')
        .map_or(bytes, |index| &bytes[index + 1..])
        .to_vec()
}

pub(crate) fn write_usage<W: Write>(program_name: &[u8], stderr: &mut W) -> io::Result<()> {
    stderr.write_all(b"usage: ")?;
    stderr.write_all(program_name)?;
    stderr.write_all(b" [-ks] [-f prefix] [-n number] file args ...\n")
}

pub(crate) fn write_error<W: Write>(
    program_name: &[u8],
    error: &AppError,
    stderr: &mut W,
) -> io::Result<()> {
    match error {
        AppError::Usage { getopt_diagnostic } => {
            if let Some(diagnostic) = getopt_diagnostic {
                stderr.write_all(diagnostic)?;
            }
            write_usage(program_name, stderr)
        }
        AppError::Message(message) => {
            stderr.write_all(program_name)?;
            stderr.write_all(b": ")?;
            stderr.write_all(message)?;
            stderr.write_all(b"\n")
        }
        AppError::Io { context, source } => {
            stderr.write_all(program_name)?;
            stderr.write_all(b": ")?;
            stderr.write_all(context)?;
            stderr.write_all(b": ")?;
            let rendered = render_io_error(source);
            stderr.write_all(rendered.as_bytes())?;
            stderr.write_all(b"\n")
        }
    }
}

pub(crate) fn run_process<I, R, O, E, F, C>(
    argv: I,
    stdin: R,
    stdout: O,
    stderr: E,
    fs: F,
    regex_compiler: C,
) -> ExitCode
where
    I: IntoIterator<Item = OsString>,
    R: BufRead,
    O: Write,
    E: Write,
    F: FileSystem,
    C: RegexCompiler + 'static,
{
    let argv: Vec<OsString> = argv.into_iter().collect();
    let argv0 = argv
        .first()
        .cloned()
        .unwrap_or_else(|| OsString::from("csplit"));
    let program_name = basename_bytes(&argv0);
    let mut stdout = stdout;
    let mut stderr = stderr;
    let mut fs = fs;

    let parsed = match parse_args(&argv, std::env::var_os("POSIXLY_CORRECT").is_some()) {
        Ok(parsed) => parsed,
        Err(error) => {
            let _ = write_error(&program_name, &error, &mut stderr);
            let _ = stderr.flush();
            return ExitCode::FAILURE;
        }
    };

    let ParsedArgs {
        config,
        input,
        expressions,
    } = parsed;
    let diagnostic_name;
    let selected_input;
    if input.as_os_str().as_bytes() == b"-" {
        diagnostic_name = b"stdin".to_vec();
        selected_input = SelectedInput::Stdin(stdin);
    } else {
        diagnostic_name = input.as_os_str().as_bytes().to_vec();
        let reader = match fs.open_input(&input) {
            Ok(reader) => reader,
            Err(source) => {
                let error = AppError::Io {
                    context: diagnostic_name,
                    source,
                };
                let _ = write_error(&program_name, &error, &mut stderr);
                let _ = stderr.flush();
                return ExitCode::FAILURE;
            }
        };
        selected_input = SelectedInput::File(reader);
    }

    let input = CInput::new(selected_input, diagnostic_name);
    let mut splitter = match Csplit::new(config, fs, input, Box::new(regex_compiler)) {
        Ok(splitter) => splitter,
        Err(error) => {
            let _ = write_error(&program_name, &error, &mut stderr);
            let _ = stderr.flush();
            return ExitCode::FAILURE;
        }
    };
    let mut buffered_stdout = Vec::new();

    match splitter.run(&expressions, &mut buffered_stdout) {
        Ok(()) => {
            let _ = stdout.write_all(&buffered_stdout);
            let _ = stdout.flush();
            ExitCode::SUCCESS
        }
        Err(error) => {
            let _ = write_error(&program_name, &error, &mut stderr);
            let _ = stderr.flush();
            splitter.cleanup();
            let _ = stdout.write_all(&buffered_stdout);
            let _ = stdout.flush();
            ExitCode::FAILURE
        }
    }
}

enum SelectedInput<R: BufRead> {
    Stdin(R),
    File(Box<dyn BufRead>),
}

impl<R: BufRead> Read for SelectedInput<R> {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        match self {
            Self::Stdin(reader) => reader.read(buffer),
            Self::File(reader) => reader.read(buffer),
        }
    }
}

impl<R: BufRead> BufRead for SelectedInput<R> {
    fn fill_buf(&mut self) -> io::Result<&[u8]> {
        match self {
            Self::Stdin(reader) => reader.fill_buf(),
            Self::File(reader) => reader.fill_buf(),
        }
    }

    fn consume(&mut self, amount: usize) {
        match self {
            Self::Stdin(reader) => reader.consume(amount),
            Self::File(reader) => reader.consume(amount),
        }
    }
}

fn read_output_chunk(file: &mut dyn OutputFile) -> Result<Option<Vec<u8>>, AppError> {
    let mut chunk = Vec::with_capacity(CHUNK_MAX);
    while chunk.len() < CHUNK_MAX {
        let mut byte = [0_u8; 1];
        match file.read(&mut byte) {
            Ok(0) => break,
            Ok(_) => {
                chunk.push(byte[0]);
                if byte[0] == b'\n' {
                    break;
                }
            }
            Err(source) => {
                return Err(AppError::Io {
                    context: b"overflow".to_vec(),
                    source,
                });
            }
        }
    }
    Ok((!chunk.is_empty()).then_some(chunk))
}

fn write_visible(
    output: &mut dyn OutputFile,
    chunk: &[u8],
    context: Vec<u8>,
) -> Result<(), AppError> {
    output
        .write_all(c_visible(chunk))
        .map_err(|source| AppError::Io { context, source })
}

fn write_count<W: Write>(stdout: &mut W, count: u64) -> Result<(), AppError> {
    writeln!(stdout, "{count}").map_err(|source| AppError::Io {
        context: b"stdout".to_vec(),
        source,
    })
}

fn getopt_diagnostic(argv0: &[u8], message: &[u8], option: u8) -> Vec<u8> {
    let mut diagnostic = argv0.to_vec();
    diagnostic.extend_from_slice(b": ");
    diagnostic.extend_from_slice(message);
    diagnostic.extend_from_slice(b" -- '");
    diagnostic.push(option);
    diagnostic.extend_from_slice(b"'\n");
    diagnostic
}

fn render_io_error(error: &io::Error) -> String {
    let rendered = error.to_string();
    if let Some(code) = error.raw_os_error() {
        let suffix = format!(" (os error {code})");
        if let Some(without_suffix) = rendered.strip_suffix(&suffix) {
            return without_suffix.to_owned();
        }
    }
    rendered
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;
    use std::collections::BTreeMap;
    use std::io::{Cursor, SeekFrom};
    use std::rc::Rc;

    #[derive(Debug, Clone, PartialEq, Eq)]
    enum MockOperation {
        OpenInput(OsString),
        CreateOutput(OsString),
        TemporaryOutput,
        RemoveOutput(OsString),
        Read,
        Write,
        Seek,
        Flush,
        Truncate(u64),
    }

    #[derive(Debug, Clone, Default)]
    struct FailurePlan {
        open_input: bool,
        create_output: bool,
        temporary_output: bool,
        remove_output: bool,
        read: bool,
        write: bool,
        seek: bool,
        flush: bool,
        truncate: bool,
    }

    #[derive(Debug, Default)]
    struct MockState {
        files: BTreeMap<OsString, Vec<u8>>,
        operations: Vec<MockOperation>,
        failures: FailurePlan,
    }

    #[derive(Debug)]
    struct MockOutputFile {
        path: Option<OsString>,
        cursor: Cursor<Vec<u8>>,
        state: Rc<RefCell<MockState>>,
    }

    impl Read for MockOutputFile {
        fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
            let mut state = self.state.borrow_mut();
            state.operations.push(MockOperation::Read);
            if state.failures.read {
                return Err(io::Error::other("mock read failure"));
            }
            drop(state);
            self.cursor.read(buffer)
        }
    }

    impl Write for MockOutputFile {
        fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
            let mut state = self.state.borrow_mut();
            state.operations.push(MockOperation::Write);
            if state.failures.write {
                return Err(io::Error::other("mock write failure"));
            }
            drop(state);

            let written = self.cursor.write(buffer)?;
            self.sync_named();
            Ok(written)
        }

        fn flush(&mut self) -> io::Result<()> {
            let mut state = self.state.borrow_mut();
            state.operations.push(MockOperation::Flush);
            if state.failures.flush {
                return Err(io::Error::other("mock flush failure"));
            }
            drop(state);
            self.sync_named();
            Ok(())
        }
    }

    impl Seek for MockOutputFile {
        fn seek(&mut self, position: SeekFrom) -> io::Result<u64> {
            let mut state = self.state.borrow_mut();
            state.operations.push(MockOperation::Seek);
            if state.failures.seek {
                return Err(io::Error::other("mock seek failure"));
            }
            drop(state);
            self.cursor.seek(position)
        }
    }

    impl OutputFile for MockOutputFile {
        fn set_len(&mut self, len: u64) -> io::Result<()> {
            let mut state = self.state.borrow_mut();
            state.operations.push(MockOperation::Truncate(len));
            if state.failures.truncate {
                return Err(io::Error::other("mock truncate failure"));
            }
            drop(state);

            let len = usize::try_from(len)
                .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "length overflow"))?;
            self.cursor.get_mut().resize(len, 0);
            self.sync_named();
            Ok(())
        }
    }

    impl MockOutputFile {
        fn sync_named(&self) {
            if let Some(path) = &self.path {
                self.state
                    .borrow_mut()
                    .files
                    .insert(path.clone(), self.cursor.get_ref().clone());
            }
        }
    }

    #[derive(Debug, Clone, Default)]
    struct MockFileSystem {
        state: Rc<RefCell<MockState>>,
    }

    impl FileSystem for MockFileSystem {
        fn open_input(&mut self, path: &OsStr) -> io::Result<Box<dyn BufRead>> {
            let path = path.to_os_string();
            let mut state = self.state.borrow_mut();
            state
                .operations
                .push(MockOperation::OpenInput(path.clone()));
            if state.failures.open_input {
                return Err(io::Error::other("mock open input failure"));
            }
            let bytes = state
                .files
                .get(&path)
                .cloned()
                .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "missing mock input"))?;
            Ok(Box::new(Cursor::new(bytes)))
        }

        fn create_output(&mut self, path: &OsStr) -> io::Result<Box<dyn OutputFile>> {
            let path = path.to_os_string();
            let mut state = self.state.borrow_mut();
            state
                .operations
                .push(MockOperation::CreateOutput(path.clone()));
            if state.failures.create_output {
                return Err(io::Error::other("mock create output failure"));
            }
            state.files.insert(path.clone(), Vec::new());
            drop(state);

            Ok(Box::new(MockOutputFile {
                path: Some(path),
                cursor: Cursor::new(Vec::new()),
                state: Rc::clone(&self.state),
            }))
        }

        fn temporary_output(&mut self) -> io::Result<Box<dyn OutputFile>> {
            let mut state = self.state.borrow_mut();
            state.operations.push(MockOperation::TemporaryOutput);
            if state.failures.temporary_output {
                return Err(io::Error::other("mock temporary output failure"));
            }
            drop(state);

            Ok(Box::new(MockOutputFile {
                path: None,
                cursor: Cursor::new(Vec::new()),
                state: Rc::clone(&self.state),
            }))
        }

        fn remove_output(&mut self, path: &OsStr) -> io::Result<()> {
            let path = path.to_os_string();
            let mut state = self.state.borrow_mut();
            state
                .operations
                .push(MockOperation::RemoveOutput(path.clone()));
            if state.failures.remove_output {
                return Err(io::Error::other("mock remove output failure"));
            }
            state.files.remove(&path);
            Ok(())
        }
    }

    type MockMatchPredicate = dyn Fn(&[u8]) -> bool;

    #[derive(Clone)]
    struct MockRegexCompiler {
        compile_log: Rc<RefCell<Vec<Vec<u8>>>>,
        match_log: Rc<RefCell<Vec<Vec<u8>>>>,
        predicate: Rc<MockMatchPredicate>,
        compile_failure: Option<Vec<u8>>,
    }

    impl Default for MockRegexCompiler {
        fn default() -> Self {
            Self::matching(|_| false)
        }
    }

    impl MockRegexCompiler {
        fn matching(predicate: impl Fn(&[u8]) -> bool + 'static) -> Self {
            Self {
                compile_log: Rc::new(RefCell::new(Vec::new())),
                match_log: Rc::new(RefCell::new(Vec::new())),
                predicate: Rc::new(predicate),
                compile_failure: None,
            }
        }

        fn failing(message: &[u8]) -> Self {
            Self {
                compile_failure: Some(message.to_vec()),
                ..Self::default()
            }
        }
    }

    impl RegexCompiler for MockRegexCompiler {
        fn compile(&self, pattern: &[u8]) -> Result<Box<dyn RegexMatcher>, AppError> {
            self.compile_log.borrow_mut().push(pattern.to_vec());
            if let Some(message) = &self.compile_failure {
                return Err(AppError::Message(message.clone()));
            }
            Ok(Box::new(MockRegexMatcher {
                match_log: Rc::clone(&self.match_log),
                predicate: Rc::clone(&self.predicate),
            }))
        }
    }

    #[derive(Clone)]
    struct MockRegexMatcher {
        match_log: Rc<RefCell<Vec<Vec<u8>>>>,
        predicate: Rc<MockMatchPredicate>,
    }

    impl RegexMatcher for MockRegexMatcher {
        fn is_match(&self, bytes: &[u8]) -> bool {
            self.match_log.borrow_mut().push(bytes.to_vec());
            (self.predicate)(bytes)
        }
    }

    struct CaseResult {
        status: ExitCode,
        stdout: Vec<u8>,
        stderr: Vec<u8>,
        files: BTreeMap<OsString, Vec<u8>>,
        operations: Vec<MockOperation>,
    }

    fn run_case(input_name: &str, input: &[u8], arguments: &[&str]) -> CaseResult {
        run_case_with_setup(input_name, input, arguments, |_| {})
    }

    fn run_case_with_setup(
        input_name: &str,
        input: &[u8],
        arguments: &[&str],
        setup: impl FnOnce(&mut MockState),
    ) -> CaseResult {
        run_case_with_setup_and_compiler(
            input_name,
            input,
            arguments,
            setup,
            crate::regex_compat::GlibcBreCompiler,
        )
    }

    fn run_case_with_compiler<C>(
        input_name: &str,
        input: &[u8],
        arguments: &[&str],
        regex_compiler: C,
    ) -> CaseResult
    where
        C: RegexCompiler + 'static,
    {
        run_case_with_setup_and_compiler(input_name, input, arguments, |_| {}, regex_compiler)
    }

    fn run_case_with_setup_and_compiler<C>(
        input_name: &str,
        input: &[u8],
        arguments: &[&str],
        setup: impl FnOnce(&mut MockState),
        regex_compiler: C,
    ) -> CaseResult
    where
        C: RegexCompiler + 'static,
    {
        let fs = MockFileSystem::default();
        {
            let mut state = fs.state.borrow_mut();
            state
                .files
                .insert(OsString::from(input_name), input.to_vec());
            setup(&mut state);
        }
        let state = Rc::clone(&fs.state);
        let mut stdout = Vec::new();
        let mut stderr = Vec::new();
        let argv = std::iter::once(OsString::from("main"))
            .chain(arguments.iter().map(OsString::from))
            .collect::<Vec<_>>();

        let status = run_process(
            argv,
            Cursor::new(Vec::<u8>::new()),
            &mut stdout,
            &mut stderr,
            fs,
            regex_compiler,
        );
        let (files, operations) = {
            let state = state.borrow();
            (state.files.clone(), state.operations.clone())
        };

        CaseResult {
            status,
            stdout,
            stderr,
            files,
            operations,
        }
    }

    fn output<'a>(case: &'a CaseResult, name: &str) -> Option<&'a [u8]> {
        case.files.get(&OsString::from(name)).map(Vec::as_slice)
    }

    macro_rules! stub_test {
        ($name:ident) => {
            #[test]
            #[ignore = "Translator TODO: implement the planned behavioral assertion"]
            fn $name() {
                todo!("Translator: replace this behavioral test stub")
            }
        };
    }

    mod cli_and_diagnostics {
        use super::*;

        fn argv(values: &[&str]) -> Vec<OsString> {
            values.iter().map(OsString::from).collect()
        }

        fn render(argv0: &OsStr, error: &AppError) -> Vec<u8> {
            let mut stderr = Vec::new();
            write_error(&basename_bytes(argv0), error, &mut stderr).expect("write diagnostic");
            stderr
        }

        #[test]
        fn defaults() {
            let parsed =
                parse_args(&argv(&["csplit", "input", "2"]), false).expect("valid arguments");
            assert_eq!(
                parsed.config,
                Config {
                    prefix: OsString::from("xx"),
                    sufflen: 2,
                    silent: false,
                    keep: false,
                }
            );
            assert_eq!(parsed.input, OsString::from("input"));
            assert_eq!(parsed.expressions, argv(&["2"]));
        }

        #[test]
        fn each_short_option() {
            let with_prefix =
                parse_args(&argv(&["main", "-f", "part", "input"]), false).expect("valid -f");
            assert_eq!(with_prefix.config.prefix, OsString::from("part"));

            let with_keep = parse_args(&argv(&["main", "-k", "input"]), false).expect("valid -k");
            assert!(with_keep.config.keep);

            let with_width =
                parse_args(&argv(&["main", "-n", "7", "input"]), false).expect("valid -n");
            assert_eq!(with_width.config.sufflen, 7);

            let with_silent = parse_args(&argv(&["main", "-s", "input"]), false).expect("valid -s");
            assert!(with_silent.config.silent);
        }

        #[test]
        fn clusters_and_attached_values() {
            let parsed = parse_args(&argv(&["main", "-ksn3", "-fpart", "input", "4"]), false)
                .expect("valid option clusters");
            assert_eq!(
                parsed.config,
                Config {
                    prefix: OsString::from("part"),
                    sufflen: 3,
                    silent: true,
                    keep: true,
                }
            );
            assert_eq!(parsed.input, OsString::from("input"));
            assert_eq!(parsed.expressions, argv(&["4"]));
        }

        #[test]
        fn options_after_operands_are_permuted() {
            let parsed = parse_args(
                &argv(&["main", "input", "2", "-s", "-f", "part", "-k", "-n3", "4"]),
                false,
            )
            .expect("GNU permutation");
            assert_eq!(
                parsed.config,
                Config {
                    prefix: OsString::from("part"),
                    sufflen: 3,
                    silent: true,
                    keep: true,
                }
            );
            assert_eq!(parsed.input, OsString::from("input"));
            assert_eq!(parsed.expressions, argv(&["2", "4"]));
        }

        #[test]
        fn posixly_correct_stops_at_first_operand() {
            let parsed = parse_args(
                &argv(&["main", "-k", "input", "2", "-s", "-f", "part", "-n3"]),
                true,
            )
            .expect("POSIX option parsing");
            assert!(parsed.config.keep);
            assert!(!parsed.config.silent);
            assert_eq!(parsed.config.prefix, OsString::from("xx"));
            assert_eq!(parsed.config.sufflen, 2);
            assert_eq!(parsed.input, OsString::from("input"));
            assert_eq!(parsed.expressions, argv(&["2", "-s", "-f", "part", "-n3"]));
        }

        #[test]
        fn double_dash_ends_options() {
            let parsed = parse_args(&argv(&["main", "-k", "--", "-n", "4"]), false)
                .expect("-- terminates options");
            assert!(parsed.config.keep);
            assert_eq!(parsed.config.sufflen, 2);
            assert_eq!(parsed.input, OsString::from("-n"));
            assert_eq!(parsed.expressions, argv(&["4"]));
        }

        #[test]
        fn lone_dash_selects_stdin() {
            let fs = MockFileSystem::default();
            let state = Rc::clone(&fs.state);
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let status = run_process(
                argv(&["main", "-"]),
                Cursor::new(b"from stdin".to_vec()),
                &mut stdout,
                &mut stderr,
                fs,
                MockRegexCompiler::default(),
            );

            assert_eq!(status, ExitCode::SUCCESS);
            assert_eq!(stdout, b"10\n");
            assert!(stderr.is_empty());
            assert_eq!(
                state.borrow().files.get(&OsString::from("xx00")),
                Some(&b"from stdin".to_vec())
            );
            assert!(!state
                .borrow()
                .operations
                .iter()
                .any(|operation| matches!(operation, MockOperation::OpenInput(_))));
        }

        #[test]
        fn missing_and_unknown_option_diagnostics() {
            let missing_f = parse_args(&argv(&["main", "-f"]), false).expect_err("missing -f arg");
            assert_eq!(
                render(OsStr::new("main"), &missing_f),
                b"main: option requires an argument -- 'f'\nusage: main [-ks] [-f prefix] [-n number] file args ...\n"
            );

            let missing_n = parse_args(&argv(&["main", "-n"]), false).expect_err("missing -n arg");
            assert_eq!(
                render(OsStr::new("main"), &missing_n),
                b"main: option requires an argument -- 'n'\nusage: main [-ks] [-f prefix] [-n number] file args ...\n"
            );

            let unknown = parse_args(&argv(&["main", "-q"]), false).expect_err("unknown option");
            assert_eq!(
                render(OsStr::new("main"), &unknown),
                b"main: invalid option -- 'q'\nusage: main [-ks] [-f prefix] [-n number] file args ...\n"
            );

            let no_input = parse_args(&argv(&["main"]), false).expect_err("missing input");
            assert_eq!(
                render(OsStr::new("main"), &no_input),
                b"usage: main [-ks] [-f prefix] [-n number] file args ...\n"
            );
        }

        #[test]
        fn argv0_and_basename_have_distinct_roles() {
            let invoked = OsString::from("./tools/my-csplit");
            let error = parse_args(&[invoked.clone(), OsString::from("-q")], false)
                .expect_err("unknown option");
            assert_eq!(
                render(&invoked, &error),
                b"./tools/my-csplit: invalid option -- 'q'\nusage: my-csplit [-ks] [-f prefix] [-n number] file args ...\n"
            );
            assert_eq!(basename_bytes(OsStr::new("/")), b"");
            assert_eq!(basename_bytes(OsStr::new("plain")), b"plain");
        }

        #[test]
        fn non_utf8_prefix_and_path() {
            let prefix = OsString::from_vec(b"part-\xff".to_vec());
            let input = OsString::from_vec(b"input-\xfe".to_vec());
            let parsed = parse_args(
                &[
                    OsString::from("main"),
                    OsString::from("-s"),
                    OsString::from("-f"),
                    prefix.clone(),
                    input.clone(),
                ],
                false,
            )
            .expect("raw-byte arguments");
            assert_eq!(parsed.config.prefix, prefix);
            assert_eq!(parsed.input, input.clone());

            let fs = MockFileSystem::default();
            fs.state
                .borrow_mut()
                .files
                .insert(input.clone(), b"raw input".to_vec());
            let state = Rc::clone(&fs.state);
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let status = run_process(
                vec![
                    OsString::from_vec(b"./main-\xfd".to_vec()),
                    OsString::from("-s"),
                    OsString::from("-f"),
                    parsed.config.prefix,
                    input,
                ],
                Cursor::new(Vec::<u8>::new()),
                &mut stdout,
                &mut stderr,
                fs,
                MockRegexCompiler::default(),
            );

            assert_eq!(status, ExitCode::SUCCESS);
            assert!(stdout.is_empty());
            assert!(stderr.is_empty());
            assert_eq!(
                state
                    .borrow()
                    .files
                    .get(&OsString::from_vec(b"part-\xff00".to_vec())),
                Some(&b"raw input".to_vec())
            );
        }
    }

    mod c_number_parsing {
        use super::*;
        use crate::regex_compat::parse_expression;

        fn argv(values: &[&str]) -> Vec<OsString> {
            values.iter().map(OsString::from).collect()
        }

        fn message(error: AppError) -> Vec<u8> {
            match error {
                AppError::Message(message) => message,
                other => panic!("unexpected error: {other:?}"),
            }
        }

        #[test]
        fn whitespace_and_signs() {
            assert_eq!(
                parse_c_long(b" \t\n\x0b\x0c\r+42x"),
                ParsedLong {
                    value: 42,
                    end: 9,
                    overflow: false,
                    had_digits: true,
                }
            );
            assert_eq!(
                parse_c_long(b"\t-17!"),
                ParsedLong {
                    value: -17,
                    end: 4,
                    overflow: false,
                    had_digits: true,
                }
            );
            assert_eq!(parse_c_long(b"+0").value, 0);
        }

        #[test]
        fn no_digits() {
            for input in [
                b"".as_slice(),
                b" \t\r".as_slice(),
                b"+".as_slice(),
                b"-x".as_slice(),
            ] {
                assert_eq!(
                    parse_c_long(input),
                    ParsedLong {
                        value: 0,
                        end: 0,
                        overflow: false,
                        had_digits: false,
                    }
                );
            }
        }

        #[test]
        fn exact_i64_bounds() {
            let maximum = b"9223372036854775807";
            let minimum = b"-9223372036854775808";
            assert_eq!(
                parse_c_long(maximum),
                ParsedLong {
                    value: i64::MAX,
                    end: maximum.len(),
                    overflow: false,
                    had_digits: true,
                }
            );
            assert_eq!(
                parse_c_long(minimum),
                ParsedLong {
                    value: i64::MIN,
                    end: minimum.len(),
                    overflow: false,
                    had_digits: true,
                }
            );
        }

        #[test]
        fn overflow() {
            let positive = parse_c_long(b"9223372036854775808x");
            assert_eq!(positive.value, i64::MAX);
            assert_eq!(positive.end, 19);
            assert!(positive.overflow);
            assert!(positive.had_digits);

            let negative = parse_c_long(b"-9223372036854775809!");
            assert_eq!(negative.value, i64::MIN);
            assert_eq!(negative.end, 20);
            assert!(negative.overflow);
            assert!(negative.had_digits);

            let many_digits = parse_c_long(b"999999999999999999999999999999");
            assert_eq!(many_digits.end, 30);
            assert!(many_digits.overflow);
        }

        #[test]
        fn suffix_zero_and_negative() {
            for (raw, expected) in [
                ("0", b"0: bad suffix length".as_slice()),
                ("-1", b"-1: bad suffix length".as_slice()),
                ("+", b"+: bad suffix length".as_slice()),
                ("2x", b"2x: bad suffix length".as_slice()),
            ] {
                let error = parse_args(&argv(&["main", "-n", raw, "input"]), false)
                    .expect_err("invalid suffix");
                assert_eq!(message(error), expected);
            }
        }

        #[test]
        fn empty_repetition() {
            assert_eq!(parse_repetition(b"{}").expect("empty repetition"), 0);
        }

        #[test]
        fn repetition_count_and_trailing_junk() {
            assert_eq!(parse_repetition(b"{2}").expect("count"), 2);
            assert_eq!(
                parse_repetition(b"{2}trailing").expect("trailing bytes are ignored"),
                2
            );
            assert_eq!(
                parse_repetition(b"{ \t+3}tail").expect("strtol whitespace and sign"),
                3
            );
        }

        #[test]
        fn malformed_and_negative_repetition() {
            for (raw, expected) in [
                (
                    b"{abc}".as_slice(),
                    b"abc}: bad repetition count".as_slice(),
                ),
                (b"{-1}".as_slice(), b"-1}: bad repetition count".as_slice()),
                (b"{2".as_slice(), b"2: bad repetition count".as_slice()),
                (
                    b"{9223372036854775808}".as_slice(),
                    b"9223372036854775808}: bad repetition count".as_slice(),
                ),
            ] {
                assert_eq!(
                    message(parse_repetition(raw).expect_err("invalid repetition")),
                    expected
                );
            }
        }

        #[test]
        fn signed_regex_offsets() {
            assert_eq!(
                parse_expression(br"/pattern/+2")
                    .expect("positive offset")
                    .offset,
                2
            );
            assert_eq!(
                parse_expression(br"%pattern%-2")
                    .expect("negative offset")
                    .offset,
                -2
            );
            assert_eq!(
                parse_expression(b"/pattern/ \t-3")
                    .expect("whitespace offset")
                    .offset,
                -3
            );
            assert_eq!(
                parse_expression(b"/pattern/-9223372036854775808")
                    .expect("minimum offset")
                    .offset,
                i64::MIN
            );
            assert_eq!(
                message(parse_expression(b"/pattern/+").expect_err("invalid offset")),
                b"+: bad offset"
            );
        }

        #[test]
        fn numeric_dispatch_uses_first_byte() {
            for expression in ["+2", " 2"] {
                let case = run_case("input", b"one\ntwo\n", &["input", expression]);
                assert_eq!(case.status, ExitCode::FAILURE);
                assert_eq!(
                    case.stderr,
                    [
                        b"main: ".as_slice(),
                        expression.as_bytes(),
                        b": unrecognised pattern\n".as_slice()
                    ]
                    .concat()
                );
            }

            let malformed_number = run_case("input", b"one\ntwo\n", &["input", "2x"]);
            assert_eq!(malformed_number.status, ExitCode::FAILURE);
            assert_eq!(malformed_number.stderr, b"main: 2x: bad line number\n");

            let repetition_first =
                run_case("input", b"one\ntwo\n", &["input", "not-numeric", "{bad}"]);
            assert_eq!(repetition_first.status, ExitCode::FAILURE);
            assert_eq!(
                repetition_first.stderr,
                b"main: bad}: bad repetition count\n"
            );
        }
    }

    mod limits_and_naming {
        use super::*;

        fn message(error: AppError) -> Vec<u8> {
            match error {
                AppError::Message(message) => message,
                other => panic!("unexpected error: {other:?}"),
            }
        }

        fn config(prefix: OsString, sufflen: u32) -> Config {
            Config {
                prefix,
                sufflen,
                silent: false,
                keep: false,
            }
        }

        #[test]
        fn suffix_widths_one_and_eighteen() {
            assert_eq!(compute_maxfiles(1).expect("width one"), 10);
            assert_eq!(
                compute_maxfiles(18).expect("width eighteen"),
                1_000_000_000_000_000_000
            );
        }

        #[test]
        fn suffix_widths_nineteen_and_twenty_fail() {
            assert_eq!(
                message(compute_maxfiles(19).expect_err("width nineteen")),
                b"19: suffix too long (limit 18)"
            );
            assert_eq!(
                message(compute_maxfiles(20).expect_err("width twenty")),
                b"20: suffix too long (limit 18)"
            );
        }

        #[test]
        fn path_limit_4095_and_4096() {
            let accepted_prefix = OsString::from_vec(vec![b'p'; PATH_MAX - 3]);
            let accepted = parse_args(
                &[
                    OsString::from("main"),
                    OsString::from("-f"),
                    accepted_prefix.clone(),
                    OsString::from("input"),
                ],
                false,
            )
            .expect("4095-byte generated name");
            assert_eq!(accepted.config.prefix, accepted_prefix);

            let rejected_prefix = OsString::from_vec(vec![b'p'; PATH_MAX - 2]);
            let error = parse_args(
                &[
                    OsString::from("main"),
                    OsString::from("-f"),
                    rejected_prefix,
                    OsString::from("input"),
                ],
                false,
            )
            .expect_err("4096-byte generated name");
            assert_eq!(message(error), b"name too long");
        }

        #[test]
        fn zero_padding() {
            assert_eq!(
                format_output_name(OsStr::new("xx"), 1, 0).as_bytes(),
                b"xx0"
            );
            assert_eq!(
                format_output_name(OsStr::new("part"), 3, 7).as_bytes(),
                b"part007"
            );
            assert_eq!(
                format_output_name(OsStr::new("part"), 3, 123).as_bytes(),
                b"part123"
            );
        }

        #[test]
        fn open_failure_does_not_increment_nfiles() {
            let fs = MockFileSystem::default();
            fs.state.borrow_mut().failures.create_output = true;
            let input = CInput::new(Cursor::new(Vec::<u8>::new()), b"input".to_vec());
            let mut splitter = Csplit::new(
                config(OsString::from("xx"), 2),
                fs,
                input,
                Box::new(MockRegexCompiler::default()),
            )
            .expect("splitter");

            let error = match splitter.newfile() {
                Ok(_) => panic!("create should fail"),
                Err(error) => error,
            };
            match error {
                AppError::Io { context, source } => {
                    assert_eq!(context, b"xx00");
                    assert_eq!(source.to_string(), "mock create output failure");
                }
                other => panic!("unexpected error: {other:?}"),
            }
            assert_eq!(splitter.nfiles, 0);
            assert_eq!(splitter.currfile.as_bytes(), b"xx00");
        }

        #[test]
        fn highest_suffix_is_reserved_for_remainder() {
            let fs = MockFileSystem::default();
            let state = Rc::clone(&fs.state);
            let input = CInput::new(Cursor::new(Vec::<u8>::new()), b"input".to_vec());
            let mut splitter = Csplit::new(
                config(OsString::from("xx"), 1),
                fs,
                input,
                Box::new(MockRegexCompiler::default()),
            )
            .expect("splitter");
            splitter.nfiles = splitter.maxfiles - 1;
            let mut stdout = Vec::new();

            splitter
                .run(&[OsString::from("would-be-an-error")], &mut stdout)
                .expect("expression is skipped at the reserved suffix");

            assert_eq!(splitter.nfiles, splitter.maxfiles);
            assert_eq!(stdout, b"0\n");
            assert_eq!(
                state.borrow().files.get(&OsString::from("xx9")),
                Some(&Vec::new())
            );
        }
    }

    mod input_model {
        use super::*;

        fn input(bytes: &[u8]) -> CInput<Cursor<Vec<u8>>> {
            CInput::new(Cursor::new(bytes.to_vec()), b"input".to_vec())
        }

        #[test]
        fn empty_input() {
            let mut input = input(b"");
            assert!(!input.eof_seen);
            assert_eq!(input.read_chunk_2047().expect("empty read"), None);
            assert!(input.eof_seen);
            assert_eq!(input.read_chunk_2047().expect("repeat EOF"), None);
        }

        #[test]
        fn terminated_and_unterminated_final_chunks() {
            let mut terminated = input(b"first\nlast\n");
            assert_eq!(
                terminated.read_chunk_2047().expect("first line"),
                Some(b"first\n".to_vec())
            );
            assert_eq!(
                terminated.read_chunk_2047().expect("last line"),
                Some(b"last\n".to_vec())
            );
            assert!(!terminated.eof_seen);
            assert_eq!(terminated.read_chunk_2047().expect("terminated EOF"), None);
            assert!(terminated.eof_seen);

            let mut unterminated = input(b"first\nlast");
            assert_eq!(
                unterminated.read_chunk_2047().expect("first line"),
                Some(b"first\n".to_vec())
            );
            assert_eq!(
                unterminated.read_chunk_2047().expect("last line"),
                Some(b"last".to_vec())
            );
            assert!(unterminated.eof_seen);
            assert_eq!(
                unterminated.read_chunk_2047().expect("unterminated EOF"),
                None
            );
        }

        #[test]
        fn chunks_at_2047_2048_and_4094_bytes() {
            for length in [CHUNK_MAX, CHUNK_MAX + 1, CHUNK_MAX * 2] {
                for terminated in [false, true] {
                    let mut bytes = vec![b'x'; length];
                    if terminated {
                        bytes.push(b'\n');
                    }
                    let mut input = input(&bytes);
                    let mut chunks = Vec::new();
                    while let Some(chunk) = input.read_chunk_2047().expect("bounded read") {
                        chunks.push(chunk);
                    }

                    assert_eq!(chunks.concat(), bytes);
                    assert!(chunks.iter().all(|chunk| chunk.len() <= CHUNK_MAX));

                    let mut expected_lengths = vec![CHUNK_MAX; length / CHUNK_MAX];
                    let remainder = length % CHUNK_MAX;
                    if remainder != 0 {
                        expected_lengths.push(remainder);
                    }
                    if terminated {
                        if remainder == 0 {
                            expected_lengths.push(1);
                        } else {
                            *expected_lengths.last_mut().expect("partial chunk") += 1;
                        }
                    }
                    assert_eq!(
                        chunks.iter().map(Vec::len).collect::<Vec<_>>(),
                        expected_lengths
                    );
                    assert!(input.eof_seen);
                }
            }
        }

        #[test]
        fn overflow_replay_has_priority() {
            let fs = MockFileSystem::default();
            let state = Rc::clone(&fs.state);
            let mut splitter = Csplit::new(
                Config {
                    prefix: OsString::from("xx"),
                    sufflen: 2,
                    silent: false,
                    keep: false,
                },
                fs,
                input(b"original\n"),
                Box::new(MockRegexCompiler::default()),
            )
            .expect("splitter");
            splitter.overflow = Some(PendingOverflow {
                file: Box::new(MockOutputFile {
                    path: None,
                    cursor: Cursor::new(b"replay\n".to_vec()),
                    state,
                }),
                truncate_at: 0,
            });

            assert_eq!(
                splitter.get_line().expect("replayed chunk"),
                Some(b"replay\n".to_vec())
            );
            assert_eq!(
                splitter.get_line().expect("original chunk"),
                Some(b"original\n".to_vec())
            );
            assert_eq!(splitter.get_line().expect("EOF"), None);
            assert_eq!(splitter.lineno, 2);
        }

        #[test]
        fn eof_flag_timing() {
            let mut terminated = input(b"x\n");
            assert_eq!(
                terminated.read_chunk_2047().expect("terminated chunk"),
                Some(b"x\n".to_vec())
            );
            assert!(!terminated.eof_seen);
            assert_eq!(terminated.read_chunk_2047().expect("EOF probe"), None);
            assert!(terminated.eof_seen);

            let mut unterminated = input(b"x");
            assert_eq!(
                unterminated.read_chunk_2047().expect("unterminated chunk"),
                Some(b"x".to_vec())
            );
            assert!(unterminated.eof_seen);

            let exact = vec![b'x'; CHUNK_MAX];
            let mut exact_limit = input(&exact);
            assert_eq!(
                exact_limit
                    .read_chunk_2047()
                    .expect("limit-sized chunk")
                    .map(|chunk| chunk.len()),
                Some(CHUNK_MAX)
            );
            assert!(!exact_limit.eof_seen);
            assert_eq!(exact_limit.read_chunk_2047().expect("limit EOF"), None);
            assert!(exact_limit.eof_seen);
        }

        #[test]
        fn embedded_nul_is_consumed_but_not_visible() {
            let bytes = b"left\0hidden\nright\0ignored\n";
            let mut input = input(bytes);
            let first = input
                .read_chunk_2047()
                .expect("first chunk")
                .expect("first bytes");
            let second = input
                .read_chunk_2047()
                .expect("second chunk")
                .expect("second bytes");
            assert_eq!(first, b"left\0hidden\n");
            assert_eq!(second, b"right\0ignored\n");
            assert_eq!(c_visible(&first), b"left");
            assert_eq!(c_visible(&second), b"right");

            let case = run_case("nul", bytes, &["nul"]);
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert_eq!(case.stdout, b"9\n");
            assert!(case.stderr.is_empty());
            assert_eq!(output(&case, "xx00"), Some(b"leftright".as_slice()));
        }
    }

    mod numeric_splitting {
        use super::*;

        #[test]
        fn boundary_one() {
            let case = run_case("input", b"one\ntwo\n", &["input", "1"]);
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert_eq!(case.stdout, b"0\n8\n");
            assert!(case.stderr.is_empty());
            assert_eq!(output(&case, "xx00"), Some(b"".as_slice()));
            assert_eq!(output(&case, "xx01"), Some(b"one\ntwo\n".as_slice()));
        }

        #[test]
        fn multiple_absolute_boundaries() {
            let case = run_case("input", b"1\n2\n3\n4\n5\n6", &["input", "2", "4"]);
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert_eq!(case.stdout, b"2\n4\n5\n");
            assert!(case.stderr.is_empty());
            assert_eq!(output(&case, "xx00"), Some(b"1\n".as_slice()));
            assert_eq!(output(&case, "xx01"), Some(b"2\n3\n".as_slice()));
            assert_eq!(output(&case, "xx02"), Some(b"4\n5\n6".as_slice()));
        }

        #[test]
        fn repetitions_use_multiples() {
            let case = run_case("input", b"1\n2\n3\n4\n5\n6\n7", &["input", "2", "{2}"]);
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert_eq!(case.stdout, b"2\n4\n4\n3\n");
            assert!(case.stderr.is_empty());
            assert_eq!(output(&case, "xx00"), Some(b"1\n".as_slice()));
            assert_eq!(output(&case, "xx01"), Some(b"2\n3\n".as_slice()));
            assert_eq!(output(&case, "xx02"), Some(b"4\n5\n".as_slice()));
            assert_eq!(output(&case, "xx03"), Some(b"6\n7".as_slice()));
        }

        #[test]
        fn backward_target() {
            let case = run_case("input", b"1\n2\n3\n4\n", &["input", "3", "2"]);
            assert_eq!(case.status, ExitCode::FAILURE);
            assert_eq!(case.stdout, b"4\n");
            assert_eq!(case.stderr, b"main: 2: can't go backwards\n");
            assert_eq!(output(&case, "xx00"), None);
            assert_eq!(output(&case, "xx01"), None);
        }

        #[test]
        fn out_of_range_retains_partial_file_with_keep() {
            let case = run_case("input", b"one\ntwo\n", &["-k", "input", "4"]);
            assert_eq!(case.status, ExitCode::FAILURE);
            assert!(case.stdout.is_empty());
            assert_eq!(case.stderr, b"main: 4: out of range\n");
            assert_eq!(output(&case, "xx00"), Some(b"one\ntwo\n".as_slice()));
        }

        #[test]
        fn silent_mode() {
            let case = run_case("input", b"1\n2\n3", &["-s", "input", "2"]);
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert!(case.stdout.is_empty());
            assert!(case.stderr.is_empty());
            assert_eq!(output(&case, "xx00"), Some(b"1\n".as_slice()));
            assert_eq!(output(&case, "xx01"), Some(b"2\n3".as_slice()));
        }

        #[test]
        fn final_empty_file_edges() {
            let terminated = run_case("input", b"1\n", &["input", "2"]);
            assert_eq!(terminated.status, ExitCode::SUCCESS);
            assert_eq!(terminated.stdout, b"2\n0\n");
            assert_eq!(output(&terminated, "xx00"), Some(b"1\n".as_slice()));
            assert_eq!(output(&terminated, "xx01"), Some(b"".as_slice()));

            let unterminated = run_case("input", b"1", &["input", "2"]);
            assert_eq!(unterminated.status, ExitCode::SUCCESS);
            assert_eq!(unterminated.stdout, b"1\n");
            assert_eq!(output(&unterminated, "xx00"), Some(b"1".as_slice()));
            assert_eq!(output(&unterminated, "xx01"), None);

            let empty = run_case("empty", b"", &["empty"]);
            assert_eq!(empty.status, ExitCode::SUCCESS);
            assert_eq!(empty.stdout, b"0\n");
            assert_eq!(output(&empty, "xx00"), Some(b"".as_slice()));
        }

        #[test]
        fn file_count_cap() {
            let input = b"a\n".repeat(12);
            let case = run_case(
                "input",
                &input,
                &["-n", "1", "input", "1", "{20}", "ignored"],
            );
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert!(case.stderr.is_empty());

            let mut expected_stdout = b"0\n".to_vec();
            for _ in 0..8 {
                expected_stdout.extend_from_slice(b"2\n");
            }
            expected_stdout.extend_from_slice(b"8\n");
            assert_eq!(case.stdout, expected_stdout);

            assert_eq!(output(&case, "xx0"), Some(b"".as_slice()));
            for index in 1..=8 {
                assert_eq!(
                    output(&case, &format!("xx{index}")),
                    Some(b"a\n".as_slice())
                );
            }
            assert_eq!(output(&case, "xx9"), Some(b"a\na\na\na\n".as_slice()));
            assert_eq!(output(&case, "xx10"), None);
        }
    }

    mod overflow_state_machine {
        use super::*;

        fn splitter(
            fs: MockFileSystem,
            original_input: &[u8],
            lineno: i64,
        ) -> Csplit<MockFileSystem, Cursor<Vec<u8>>> {
            let mut splitter = Csplit::new(
                Config {
                    prefix: OsString::from("xx"),
                    sufflen: 2,
                    silent: false,
                    keep: false,
                },
                fs,
                CInput::new(Cursor::new(original_input.to_vec()), b"input".to_vec()),
                Box::new(MockRegexCompiler::default()),
            )
            .expect("splitter");
            splitter.lineno = lineno;
            splitter.currfile = OsString::from("xx00");
            splitter
        }

        fn output_with_bytes(
            fs: &mut MockFileSystem,
            path: Option<&str>,
            bytes: &[u8],
        ) -> Box<dyn OutputFile> {
            let mut output = match path {
                Some(path) => fs.create_output(OsStr::new(path)).expect("named output"),
                None => fs.temporary_output().expect("temporary output"),
            };
            output.write_all(bytes).expect("populate output");
            output
        }

        fn assert_io_error(error: AppError, expected_context: &[u8], expected_source: &str) {
            match error {
                AppError::Io { context, source } => {
                    assert_eq!(context, expected_context);
                    assert_eq!(source.to_string(), expected_source);
                }
                other => panic!("unexpected error: {other:?}"),
            }
        }

        fn assert_message(error: AppError, expected: &[u8]) {
            match error {
                AppError::Message(message) => assert_eq!(message, expected),
                other => panic!("unexpected error: {other:?}"),
            }
        }

        #[test]
        fn zero_and_negative_offsets() {
            let bytes = b"one\ntwo\nmatch\n";
            for (offset, path, expected_position, expected_replay) in [
                (0_i64, Some("xx00"), 8_u64, b"match\n".as_slice()),
                (-1_i64, None, 4_u64, b"two\nmatch\n".as_slice()),
            ] {
                let mut fs = MockFileSystem::default();
                let state = Rc::clone(&fs.state);
                let output = output_with_bytes(&mut fs, path, bytes);
                let mut splitter = splitter(fs, b"", 3);
                let count = offset
                    .unsigned_abs()
                    .checked_add(1)
                    .expect("representable offset");

                splitter
                    .toomuch(Some(output), count)
                    .expect("create overflow replay");

                assert_eq!(
                    splitter.lineno,
                    3 - i64::try_from(count).expect("small test count")
                );
                assert_eq!(
                    splitter
                        .overflow
                        .as_ref()
                        .expect("pending overflow")
                        .truncate_at,
                    expected_position
                );

                let mut replayed = Vec::new();
                while let Some(chunk) = splitter.get_line().expect("replay chunk") {
                    replayed.extend_from_slice(&chunk);
                }
                assert_eq!(replayed, expected_replay);

                if path.is_none() {
                    assert!(state
                        .borrow()
                        .operations
                        .contains(&MockOperation::TemporaryOutput));
                }
            }
        }

        #[test]
        fn scan_crosses_8192_byte_blocks() {
            const LINE_COUNT: usize = 200;
            const LINE_WIDTH: usize = 101;
            const REPLAY_COUNT: u64 = 100;

            let mut bytes = Vec::with_capacity(LINE_COUNT * LINE_WIDTH);
            for index in 0..LINE_COUNT {
                bytes.extend(std::iter::repeat_n(
                    b'a' + u8::try_from(index % 26).expect("alphabet index"),
                    LINE_WIDTH - 1,
                ));
                bytes.push(b'\n');
            }

            let mut fs = MockFileSystem::default();
            let state = Rc::clone(&fs.state);
            let output = output_with_bytes(&mut fs, Some("xx00"), &bytes);
            state.borrow_mut().operations.clear();
            let mut splitter = splitter(fs, b"", LINE_COUNT as i64);

            splitter
                .toomuch(Some(output), REPLAY_COUNT)
                .expect("multiblock reverse scan");

            let expected_position =
                u64::try_from((LINE_COUNT - REPLAY_COUNT as usize) * LINE_WIDTH)
                    .expect("expected position");
            assert_eq!(
                splitter
                    .overflow
                    .as_ref()
                    .expect("pending overflow")
                    .truncate_at,
                expected_position
            );
            assert_eq!(
                splitter.lineno,
                LINE_COUNT as i64 - i64::try_from(REPLAY_COUNT).expect("small test count")
            );
            assert!(
                state
                    .borrow()
                    .operations
                    .iter()
                    .filter(|operation| matches!(operation, MockOperation::Read))
                    .count()
                    >= 2
            );
        }

        #[test]
        fn insufficient_prior_newlines_rewinds_to_zero() {
            let mut fs = MockFileSystem::default();
            let output = output_with_bytes(&mut fs, None, b"first\nsecond\n");
            let mut splitter = splitter(fs, b"", 2);

            splitter
                .toomuch(Some(output), 5)
                .expect("rewind beyond available newlines");

            assert_eq!(splitter.lineno, -3);
            assert_eq!(
                splitter
                    .overflow
                    .as_ref()
                    .expect("pending overflow")
                    .truncate_at,
                0
            );
            assert_eq!(
                splitter.get_line().expect("first replay"),
                Some(b"first\n".to_vec())
            );
        }

        #[test]
        fn lineno_adjustment() {
            let mut fs = MockFileSystem::default();
            let output = output_with_bytes(&mut fs, None, b"one\ntwo\nthree\nfour\nfive\n");
            let mut splitter = splitter(fs, b"original\n", 25);

            splitter
                .toomuch(Some(output), 2)
                .expect("roll back two chunks");
            assert_eq!(splitter.lineno, 23);
            assert_eq!(
                splitter.get_line().expect("first replay"),
                Some(b"four\n".to_vec())
            );
            assert_eq!(splitter.lineno, 24);
            assert_eq!(
                splitter.get_line().expect("second replay"),
                Some(b"five\n".to_vec())
            );
            assert_eq!(splitter.lineno, 25);
            assert_eq!(
                splitter.get_line().expect("original input"),
                Some(b"original\n".to_vec())
            );
            assert_eq!(splitter.lineno, 26);
        }

        #[test]
        fn truncate_is_delayed() {
            let bytes = b"kept\nreplayed\n";
            let mut fs = MockFileSystem::default();
            let state = Rc::clone(&fs.state);
            let output = output_with_bytes(&mut fs, Some("xx00"), bytes);
            state.borrow_mut().operations.clear();
            let mut splitter = splitter(fs, b"", 2);

            splitter
                .toomuch(Some(output), 1)
                .expect("create pending overflow");

            assert_eq!(
                state.borrow().files.get(&OsString::from("xx00")),
                Some(&bytes.to_vec())
            );
            assert!(!state
                .borrow()
                .operations
                .iter()
                .any(|operation| matches!(operation, MockOperation::Truncate(_))));

            assert_eq!(
                splitter.get_line().expect("replayed line"),
                Some(b"replayed\n".to_vec())
            );
            assert_eq!(
                state.borrow().files.get(&OsString::from("xx00")),
                Some(&bytes.to_vec())
            );

            splitter
                .toomuch(None, 0)
                .expect("finalize pending overflow");
            assert_eq!(
                state.borrow().files.get(&OsString::from("xx00")),
                Some(&b"kept\n".to_vec())
            );
            assert_eq!(
                state
                    .borrow()
                    .operations
                    .iter()
                    .filter(|operation| matches!(operation, MockOperation::Truncate(5)))
                    .count(),
                1
            );
            assert!(splitter.overflow.is_none());
        }

        #[test]
        fn previous_overflow_is_finalized_first() {
            let mut fs = MockFileSystem::default();
            let state = Rc::clone(&fs.state);
            let previous = output_with_bytes(&mut fs, Some("xx00"), b"kept\ntail\n");
            let current = output_with_bytes(&mut fs, Some("xx01"), b"next\nmatch\n");
            let mut splitter = splitter(fs, b"", 2);
            splitter.overflow = Some(PendingOverflow {
                file: previous,
                truncate_at: 5,
            });
            state.borrow_mut().operations.clear();

            splitter
                .toomuch(Some(current), 1)
                .expect("replace pending overflow");

            let state = state.borrow();
            assert_eq!(
                state.files.get(&OsString::from("xx00")),
                Some(&b"kept\n".to_vec())
            );
            assert_eq!(
                &state.operations[..2],
                &[MockOperation::Flush, MockOperation::Truncate(5)]
            );
            assert!(matches!(state.operations.get(2), Some(MockOperation::Seek)));
            drop(state);

            assert_eq!(
                splitter
                    .overflow
                    .as_ref()
                    .expect("replacement overflow")
                    .truncate_at,
                5
            );
        }

        #[test]
        fn seek_read_flush_and_truncate_failures() {
            {
                let mut fs = MockFileSystem::default();
                let state = Rc::clone(&fs.state);
                let output = output_with_bytes(&mut fs, Some("xx00"), b"one\ntwo\n");
                state.borrow_mut().failures.seek = true;
                let mut splitter = splitter(fs, b"", 2);

                let error = splitter
                    .toomuch(Some(output), 1)
                    .expect_err("seek should fail");
                assert_message(error, b"xx00: can't seek");
                assert!(splitter.overflow.is_none());
            }

            {
                let mut fs = MockFileSystem::default();
                let state = Rc::clone(&fs.state);
                let output = output_with_bytes(&mut fs, Some("xx00"), b"one\ntwo\n");
                state.borrow_mut().failures.read = true;
                let mut splitter = splitter(fs, b"", 2);

                let error = splitter
                    .toomuch(Some(output), 1)
                    .expect_err("read should fail");
                assert_message(error, b"can't read overflowed output");
                assert!(splitter.overflow.is_none());
            }

            {
                let mut fs = MockFileSystem::default();
                let state = Rc::clone(&fs.state);
                let previous = output_with_bytes(&mut fs, Some("xx00"), b"kept\ntail\n");
                let mut splitter = splitter(fs, b"", 2);
                splitter.overflow = Some(PendingOverflow {
                    file: previous,
                    truncate_at: 5,
                });
                {
                    let mut state = state.borrow_mut();
                    state.operations.clear();
                    state.failures.flush = true;
                }

                let error = splitter.toomuch(None, 0).expect_err("flush should fail");
                assert_io_error(error, b"overflow", "mock flush failure");
                assert_eq!(state.borrow().operations, &[MockOperation::Flush]);
                assert!(splitter.overflow.is_none());
            }

            {
                let mut fs = MockFileSystem::default();
                let state = Rc::clone(&fs.state);
                let previous = output_with_bytes(&mut fs, Some("xx00"), b"kept\ntail\n");
                let mut splitter = splitter(fs, b"", 2);
                splitter.overflow = Some(PendingOverflow {
                    file: previous,
                    truncate_at: 5,
                });
                {
                    let mut state = state.borrow_mut();
                    state.operations.clear();
                    state.failures.truncate = true;
                }

                let error = splitter.toomuch(None, 0).expect_err("truncate should fail");
                assert_io_error(error, b"overflow", "mock truncate failure");
                assert_eq!(
                    state.borrow().operations,
                    &[MockOperation::Flush, MockOperation::Truncate(5)]
                );
                assert!(splitter.overflow.is_none());
            }
        }
    }

    mod regex_splitting {
        use super::*;

        fn matching(needle: &'static [u8]) -> MockRegexCompiler {
            MockRegexCompiler::matching(move |bytes| bytes == needle)
        }

        fn direct_splitter(
            input: &[u8],
            compiler: MockRegexCompiler,
        ) -> (
            Csplit<MockFileSystem, Cursor<Vec<u8>>>,
            Rc<RefCell<MockState>>,
        ) {
            let fs = MockFileSystem::default();
            let state = Rc::clone(&fs.state);
            let splitter = Csplit::new(
                Config {
                    prefix: OsString::from("xx"),
                    sufflen: 2,
                    silent: false,
                    keep: false,
                },
                fs,
                CInput::new(Cursor::new(input.to_vec()), b"input".to_vec()),
                Box::new(compiler),
            )
            .expect("splitter");
            (splitter, state)
        }

        #[test]
        fn first_chunk_is_not_matched() {
            let compiler = matching(b"first\n");
            let case = run_case_with_compiler(
                "input",
                b"first\nsecond\nthird",
                &["input", "/needle/"],
                compiler.clone(),
            );

            assert_eq!(case.status, ExitCode::FAILURE);
            assert_eq!(case.stderr, b"main: needle: no match\n");
            assert_eq!(&*compiler.compile_log.borrow(), &[b"needle".to_vec()]);
            assert_eq!(
                &*compiler.match_log.borrow(),
                &[b"second\n".to_vec(), b"third".to_vec()]
            );
            assert_eq!(output(&case, "xx00"), None);
        }

        #[test]
        fn slash_is_saved_and_percent_is_discarded() {
            let input = b"head\nbefore\nmatch\ntail\n";

            let slash = run_case_with_compiler(
                "input",
                input,
                &["input", "/needle/-1"],
                matching(b"match\n"),
            );
            assert_eq!(slash.status, ExitCode::SUCCESS);
            assert_eq!(slash.stdout, b"5\n18\n");
            assert!(slash.stderr.is_empty());
            assert_eq!(output(&slash, "xx00"), Some(b"head\n".as_slice()));
            assert_eq!(
                output(&slash, "xx01"),
                Some(b"before\nmatch\ntail\n".as_slice())
            );
            assert!(!slash
                .operations
                .iter()
                .any(|operation| matches!(operation, MockOperation::TemporaryOutput)));

            let percent = run_case_with_compiler(
                "input",
                input,
                &["input", "%needle%-1"],
                matching(b"match\n"),
            );
            assert_eq!(percent.status, ExitCode::SUCCESS);
            assert_eq!(percent.stdout, b"18\n");
            assert!(percent.stderr.is_empty());
            assert_eq!(
                output(&percent, "xx00"),
                Some(b"before\nmatch\ntail\n".as_slice())
            );
            assert_eq!(output(&percent, "xx01"), None);
            assert!(percent.operations.contains(&MockOperation::TemporaryOutput));
            assert_eq!(
                percent
                    .operations
                    .iter()
                    .filter(|operation| matches!(operation, MockOperation::CreateOutput(_)))
                    .count(),
                1
            );
        }

        #[test]
        fn no_match() {
            let compiler = MockRegexCompiler::default();
            let case = run_case_with_compiler(
                "input",
                b"one\ntwo\n",
                &["input", "/needle/"],
                compiler.clone(),
            );

            assert_eq!(case.status, ExitCode::FAILURE);
            assert!(case.stdout.is_empty());
            assert_eq!(case.stderr, b"main: needle: no match\n");
            assert_eq!(&*compiler.compile_log.borrow(), &[b"needle".to_vec()]);
            assert_eq!(&*compiler.match_log.borrow(), &[b"two\n".to_vec()]);
            assert_eq!(output(&case, "xx00"), None);
            assert!(case
                .operations
                .contains(&MockOperation::RemoveOutput(OsString::from("xx00"))));
        }

        #[test]
        fn offsets_zero_negative_one_positive_one_and_two() {
            let input = b"zero\none\nmatch\nafter\nlast";
            for (offset, left, right, stdout) in [
                (
                    "0",
                    b"zero\none\n".as_slice(),
                    b"match\nafter\nlast".as_slice(),
                    b"9\n16\n".as_slice(),
                ),
                (
                    "-1",
                    b"zero\n".as_slice(),
                    b"one\nmatch\nafter\nlast".as_slice(),
                    b"5\n20\n".as_slice(),
                ),
                (
                    "+1",
                    b"zero\none\nmatch\n".as_slice(),
                    b"after\nlast".as_slice(),
                    b"15\n10\n".as_slice(),
                ),
                (
                    "+2",
                    b"zero\none\nmatch\nafter\n".as_slice(),
                    b"last".as_slice(),
                    b"21\n4\n".as_slice(),
                ),
            ] {
                let expression = format!("/needle/{offset}");
                let case = run_case_with_compiler(
                    "input",
                    input,
                    &["input", &expression],
                    matching(b"match\n"),
                );

                assert_eq!(case.status, ExitCode::SUCCESS, "offset {offset}");
                assert_eq!(case.stdout, stdout, "offset {offset}");
                assert!(case.stderr.is_empty(), "offset {offset}");
                assert_eq!(output(&case, "xx00"), Some(left), "offset {offset}");
                assert_eq!(output(&case, "xx01"), Some(right), "offset {offset}");
                assert_eq!(output(&case, "xx02"), None, "offset {offset}");
            }

            let minimum = run_case_with_compiler(
                "input",
                b"head\nmatch\ntail\n",
                &["input", "/needle/-9223372036854775808"],
                matching(b"match\n"),
            );
            assert_eq!(minimum.status, ExitCode::SUCCESS);
            assert_eq!(minimum.stdout, b"0\n16\n");
            assert!(minimum.stderr.is_empty());
            assert_eq!(output(&minimum, "xx00"), Some(b"".as_slice()));
            assert_eq!(
                output(&minimum, "xx01"),
                Some(b"head\nmatch\ntail\n".as_slice())
            );
        }

        #[test]
        fn positive_offset_past_eof() {
            let beyond = run_case_with_compiler(
                "input",
                b"head\nmatch\ntail",
                &["input", "/needle/+9223372036854775807"],
                matching(b"match\n"),
            );
            assert_eq!(beyond.status, ExitCode::SUCCESS);
            assert_eq!(beyond.stdout, b"15\n");
            assert!(beyond.stderr.is_empty());
            assert_eq!(
                output(&beyond, "xx00"),
                Some(b"head\nmatch\ntail".as_slice())
            );
            assert_eq!(output(&beyond, "xx01"), None);

            let through = run_case_with_compiler(
                "input",
                b"head\nmatch\n",
                &["input", "/needle/+1"],
                matching(b"match\n"),
            );
            assert_eq!(through.status, ExitCode::SUCCESS);
            assert_eq!(through.stdout, b"11\n0\n");
            assert!(through.stderr.is_empty());
            assert_eq!(output(&through, "xx00"), Some(b"head\nmatch\n".as_slice()));
            assert_eq!(output(&through, "xx01"), Some(b"".as_slice()));
        }

        #[test]
        fn regex_repetitions() {
            let compiler = matching(b"match\n");
            let repeated = run_case_with_compiler(
                "input",
                b"start\nmatch\nbetween1\nmatch\nbetween2\nmatch\ntail\n",
                &["input", "/needle/", "{2}"],
                compiler.clone(),
            );
            assert_eq!(repeated.status, ExitCode::SUCCESS);
            assert_eq!(repeated.stdout, b"6\n15\n15\n11\n");
            assert!(repeated.stderr.is_empty());
            assert_eq!(output(&repeated, "xx00"), Some(b"start\n".as_slice()));
            assert_eq!(
                output(&repeated, "xx01"),
                Some(b"match\nbetween1\n".as_slice())
            );
            assert_eq!(
                output(&repeated, "xx02"),
                Some(b"match\nbetween2\n".as_slice())
            );
            assert_eq!(output(&repeated, "xx03"), Some(b"match\ntail\n".as_slice()));
            assert_eq!(
                &*compiler.compile_log.borrow(),
                &[b"needle".to_vec(), b"needle".to_vec(), b"needle".to_vec()]
            );
            assert_eq!(
                &*compiler.match_log.borrow(),
                &[
                    b"match\n".to_vec(),
                    b"between1\n".to_vec(),
                    b"match\n".to_vec(),
                    b"between2\n".to_vec(),
                    b"match\n".to_vec(),
                ]
            );

            let capacity_compiler = matching(b"m\n");
            let capacity = run_case_with_compiler(
                "input",
                b"start\nm\nx1\nm\nx2\nm\nx3\nm\nx4\nm\nx5\nm\nx6\nm\nx7\nm\nx8\nm\nx9\nm\nx10\nm\nx11\ntail\n",
                &["-n", "1", "input", "/needle/", "{20}"],
                capacity_compiler.clone(),
            );
            assert_eq!(capacity.status, ExitCode::SUCCESS);
            assert_eq!(capacity.stdout, b"6\n5\n5\n5\n5\n5\n5\n5\n5\n22\n");
            assert!(capacity.stderr.is_empty());
            assert_eq!(output(&capacity, "xx0"), Some(b"start\n".as_slice()));
            assert_eq!(output(&capacity, "xx8"), Some(b"m\nx8\n".as_slice()));
            assert_eq!(
                output(&capacity, "xx9"),
                Some(b"m\nx9\nm\nx10\nm\nx11\ntail\n".as_slice())
            );
            assert_eq!(output(&capacity, "xx10"), None);
            assert_eq!(capacity_compiler.compile_log.borrow().len(), 9);
            assert_eq!(
                capacity
                    .operations
                    .iter()
                    .filter(|operation| matches!(operation, MockOperation::CreateOutput(_)))
                    .count(),
                10
            );

            let discarded_compiler = matching(b"match\n");
            let discarded = run_case_with_compiler(
                "input",
                b"start\nmatch\nbetween1\nmatch\nbetween2\nmatch\ntail\n",
                &["input", "%needle%", "{2}"],
                discarded_compiler.clone(),
            );
            assert_eq!(discarded.status, ExitCode::SUCCESS);
            assert_eq!(discarded.stdout, b"11\n");
            assert!(discarded.stderr.is_empty());
            assert_eq!(
                output(&discarded, "xx00"),
                Some(b"match\ntail\n".as_slice())
            );
            assert_eq!(output(&discarded, "xx01"), None);
            assert_eq!(discarded_compiler.compile_log.borrow().len(), 3);
            assert_eq!(
                discarded
                    .operations
                    .iter()
                    .filter(|operation| matches!(operation, MockOperation::TemporaryOutput))
                    .count(),
                3
            );
            assert_eq!(
                discarded
                    .operations
                    .iter()
                    .filter(|operation| matches!(operation, MockOperation::CreateOutput(_)))
                    .count(),
                1
            );
        }

        #[test]
        fn malformed_closing_delimiter_and_line_quirk() {
            let escaped_compiler = MockRegexCompiler::default();
            let escaped = run_case_with_compiler(
                "input",
                b"one\ntwo\n",
                &["input", r"/body\/"],
                escaped_compiler.clone(),
            );
            assert_eq!(escaped.status, ExitCode::FAILURE);
            assert_eq!(
                escaped.stderr,
                br"main: /body\/: missing trailing /"
                    .iter()
                    .copied()
                    .chain([b'\n'])
                    .collect::<Vec<_>>()
            );
            assert!(escaped_compiler.compile_log.borrow().is_empty());
            assert_eq!(output(&escaped, "xx00"), None);

            let line_compiler = MockRegexCompiler::default();
            let line = run_case_with_compiler(
                "input",
                b"Line 1\nLine 2\n",
                &["input", "/Line"],
                line_compiler.clone(),
            );
            assert_eq!(line.status, ExitCode::FAILURE);
            assert_eq!(line.stderr, b"main: Line: bad offset\n");
            assert!(line_compiler.compile_log.borrow().is_empty());
            assert_eq!(output(&line, "xx00"), None);

            let bad_offset = run_case("input", b"one\ntwo\n", &["input", "/body/2junk"]);
            assert_eq!(bad_offset.status, ExitCode::FAILURE);
            assert_eq!(bad_offset.stderr, b"main: 2junk: bad offset\n");
            assert_eq!(output(&bad_offset, "xx00"), None);

            let bad_regex = run_case("input", b"one\ntwo\n", &["input", "/[/"]);
            assert_eq!(bad_regex.status, ExitCode::FAILURE);
            assert_eq!(bad_regex.stderr, b"main: [: bad regular expression\n");
            assert_eq!(output(&bad_regex, "xx00"), None);
        }

        #[test]
        fn slash_zero_offset_replays_matching_chunk() {
            let (mut splitter, state) =
                direct_splitter(b"head\nmatch\ntail\n", matching(b"match\n"));
            let mut stdout = Vec::new();

            splitter
                .do_rexp(b"/needle/", &mut stdout)
                .expect("zero-offset regex split");

            assert_eq!(stdout, b"5\n");
            assert_eq!(
                state.borrow().files.get(&OsString::from("xx00")),
                Some(&b"head\nmatch\n".to_vec())
            );
            assert_eq!(
                splitter
                    .overflow
                    .as_ref()
                    .expect("pending named overflow")
                    .truncate_at,
                5
            );
            assert!(!state
                .borrow()
                .operations
                .iter()
                .any(|operation| matches!(operation, MockOperation::Truncate(_))));
            assert_eq!(
                splitter.get_line().expect("replayed matching chunk"),
                Some(b"match\n".to_vec())
            );

            splitter
                .toomuch(None, 0)
                .expect("finalize pending named overflow");
            assert_eq!(
                state.borrow().files.get(&OsString::from("xx00")),
                Some(&b"head\n".to_vec())
            );
            assert!(splitter.overflow.is_none());
        }

        #[test]
        fn pending_named_file_behavior() {
            let (mut splitter, state) =
                direct_splitter(b"head\nmatch\nbetween\nmatch\ntail\n", matching(b"match\n"));
            let mut stdout = Vec::new();

            splitter
                .do_rexp(b"/needle/", &mut stdout)
                .expect("first zero-offset split");
            assert_eq!(
                state.borrow().files.get(&OsString::from("xx00")),
                Some(&b"head\nmatch\n".to_vec())
            );
            assert_eq!(
                splitter
                    .overflow
                    .as_ref()
                    .expect("pending first output")
                    .truncate_at,
                5
            );

            splitter
                .do_rexp(b"/needle/+1", &mut stdout)
                .expect("positive split finalizes prior overflow");
            assert!(splitter.overflow.is_none());
            assert_eq!(
                state.borrow().files.get(&OsString::from("xx00")),
                Some(&b"head\n".to_vec())
            );
            assert_eq!(
                state.borrow().files.get(&OsString::from("xx01")),
                Some(&b"match\nbetween\nmatch\n".to_vec())
            );
            assert_eq!(stdout, b"5\n20\n");

            {
                let state = state.borrow();
                let truncate = state
                    .operations
                    .iter()
                    .position(|operation| *operation == MockOperation::Truncate(5))
                    .expect("prior named output was truncated");
                let preceding = truncate.checked_sub(1).expect("flush precedes truncate");
                assert_eq!(state.operations.get(preceding), Some(&MockOperation::Flush));
                assert_eq!(
                    state.operations.get(truncate + 1),
                    Some(&MockOperation::Seek)
                );
            }

            splitter
                .copy_remainder(&mut stdout)
                .expect("copy final remainder");
            assert_eq!(stdout, b"5\n20\n5\n");
            assert_eq!(
                state.borrow().files.get(&OsString::from("xx02")),
                Some(&b"tail\n".to_vec())
            );
            assert!(splitter.overflow.is_none());
        }

        #[test]
        fn mock_regex_seam_logs_predicates_and_injects_compile_failures() {
            let compiler = MockRegexCompiler::matching(|bytes| bytes.starts_with(b"exact:"));
            let matcher = compiler
                .compile(b"raw\xffpattern")
                .expect("mock compile should succeed");
            assert!(matcher.is_match(b"exact: bytes"));
            assert!(!matcher.is_match(b"inexact"));
            assert_eq!(
                &*compiler.compile_log.borrow(),
                &[b"raw\xffpattern".to_vec()]
            );
            assert_eq!(
                &*compiler.match_log.borrow(),
                &[b"exact: bytes".to_vec(), b"inexact".to_vec()]
            );

            let failing = MockRegexCompiler::failing(b"body: bad regular expression");
            match failing.compile(b"body") {
                Err(AppError::Message(message)) => {
                    assert_eq!(message, b"body: bad regular expression")
                }
                _ => panic!("injected compile failure unexpectedly succeeded"),
            }
            assert_eq!(&*failing.compile_log.borrow(), &[b"body".to_vec()]);
            assert!(failing.match_log.borrow().is_empty());
        }
    }

    mod cleanup_and_errors {
        use super::*;

        #[test]
        fn default_cleanup_unlinks_outputs() {
            let case = run_case("input", b"one\ntwo\n", &["input", "4"]);
            assert_eq!(case.status, ExitCode::FAILURE);
            assert_eq!(case.stderr, b"main: 4: out of range\n");
            assert_eq!(output(&case, "xx00"), None);
            assert!(case
                .operations
                .contains(&MockOperation::RemoveOutput(OsString::from("xx00"))));
        }

        #[test]
        fn keep_retains_outputs() {
            let case = run_case("input", b"one\ntwo\n", &["-k", "input", "4"]);
            assert_eq!(case.status, ExitCode::FAILURE);
            assert_eq!(output(&case, "xx00"), Some(b"one\ntwo\n".as_slice()));
            assert!(!case
                .operations
                .iter()
                .any(|operation| matches!(operation, MockOperation::RemoveOutput(_))));
        }

        #[test]
        fn overwritten_file_is_removed() {
            let case = run_case_with_setup("input", b"one\n", &["input", "3"], |state| {
                state
                    .files
                    .insert(OsString::from("xx00"), b"pre-existing".to_vec());
            });
            assert_eq!(case.status, ExitCode::FAILURE);
            assert_eq!(output(&case, "xx00"), None);
            assert!(case
                .operations
                .contains(&MockOperation::CreateOutput(OsString::from("xx00"))));
            assert!(case
                .operations
                .contains(&MockOperation::RemoveOutput(OsString::from("xx00"))));
        }

        #[test]
        fn unlink_failure_is_ignored() {
            let case = run_case_with_setup("input", b"one\n", &["input", "3"], |state| {
                state.failures.remove_output = true
            });
            assert_eq!(case.status, ExitCode::FAILURE);
            assert_eq!(case.stderr, b"main: 3: out of range\n");
            assert_eq!(output(&case, "xx00"), Some(b"one\n".as_slice()));
            assert!(case
                .operations
                .contains(&MockOperation::RemoveOutput(OsString::from("xx00"))));
        }

        stub_test!(keep_retains_pending_untruncated_file);
        stub_test!(os_error_rendering);
        stub_test!(stderr_precedes_buffered_stdout_on_error);
    }

    mod released_seed_shapes {
        use super::*;

        #[test]
        fn regex_dot_metachar() {
            let case = run_case("dot", b"abc\naxc\na.c\ntest", &["dot", "/a.c/"]);
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert_eq!(case.stdout, b"4\n12\n");
            assert!(case.stderr.is_empty());
            assert_eq!(output(&case, "xx00"), Some(b"abc\n".as_slice()));
            assert_eq!(output(&case, "xx01"), Some(b"axc\na.c\ntest".as_slice()));
        }

        #[test]
        fn regex_missing_trailing() {
            let case = run_case("infile", b"Line 1\nLine 2\nLine 3", &["infile", "/Line"]);
            assert_eq!(case.status, ExitCode::FAILURE);
            assert_eq!(case.stderr, b"main: Line: bad offset\n");
            assert_eq!(output(&case, "xx00"), None);
        }

        #[test]
        fn whitespace_in_regex() {
            let case = run_case(
                "whitespace",
                b"no space\nhas space\nno\tspace\nend",
                &["whitespace", "/has space/"],
            );
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert_eq!(output(&case, "xx00"), Some(b"no space\n".as_slice()));
            assert_eq!(
                output(&case, "xx01"),
                Some(b"has space\nno\tspace\nend".as_slice())
            );
        }

        #[test]
        fn bad_line_number() {
            let case = run_case("infile", b"Line 1\n", &["infile", "-1"]);
            assert_eq!(case.status, ExitCode::FAILURE);
            assert_eq!(
                case.stderr,
                b"main: invalid option -- '1'\nusage: main [-ks] [-f prefix] [-n number] file args ...\n"
            );
        }

        #[test]
        fn negative_suffix_length() {
            let case = run_case("infile", b"Line 1\n", &["-n", "-1", "infile", "2"]);
            assert_eq!(case.status, ExitCode::FAILURE);
            assert_eq!(case.stderr, b"main: -1: bad suffix length\n");
        }

        #[test]
        fn invalid_repetition() {
            let case = run_case(
                "infile",
                b"Line 1\nLine 2\nLine 3",
                &["infile", "2", "{abc}"],
            );
            assert_eq!(case.status, ExitCode::FAILURE);
            assert_eq!(case.stderr, b"main: abc}: bad repetition count\n");
            assert_eq!(output(&case, "xx00"), None);
        }

        #[test]
        fn multiline_pattern_match() {
            let case = run_case(
                "multiline",
                b"start\nmiddle\nend pattern\nafter",
                &["multiline", "/end/"],
            );
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert_eq!(output(&case, "xx00"), Some(b"start\nmiddle\n".as_slice()));
            assert_eq!(
                output(&case, "xx01"),
                Some(b"end pattern\nafter".as_slice())
            );
        }

        #[test]
        fn alternation_in_regex() {
            let case = run_case(
                "alt",
                b"apple\nbanana\ncherry\ndate",
                &["alt", r"/apple\|cherry/"],
            );
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert_eq!(case.stdout, b"13\n11\n");
            assert!(case.stderr.is_empty());
            assert_eq!(output(&case, "xx00"), Some(b"apple\nbanana\n".as_slice()));
            assert_eq!(output(&case, "xx01"), Some(b"cherry\ndate".as_slice()));
            assert_eq!(output(&case, "xx02"), None);
        }

        #[test]
        fn regex_with_special_chars() {
            let case = run_case(
                "special",
                b"line [1]\nline (2)\nline {3}\nline .4.",
                &["special", r"/\[1\]/"],
            );
            assert_eq!(case.status, ExitCode::FAILURE);
            assert!(case.stdout.is_empty());
            assert_eq!(
                case.stderr,
                br"main: \[1\]: no match"
                    .iter()
                    .copied()
                    .chain([b'\n'])
                    .collect::<Vec<_>>()
            );
            assert_eq!(output(&case, "xx00"), None);
            assert_eq!(output(&case, "xx01"), None);
            assert!(case
                .operations
                .contains(&MockOperation::RemoveOutput(OsString::from("xx00"))));
        }

        #[test]
        fn suffix_overflow() {
            let case = run_case("infile", b"Line 1\nLine 2", &["-n", "20", "infile", "2"]);
            assert_eq!(case.status, ExitCode::FAILURE);
            assert_eq!(case.stderr, b"main: 20: suffix too long (limit 18)\n");
        }

        #[test]
        fn positive_offset_regex() {
            let case = run_case(
                "infile",
                b"Line 1\nLine 2\nLine 3\nLine 4\nLine 5",
                &["infile", "/Line 2/1"],
            );
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert_eq!(output(&case, "xx00"), Some(b"Line 1\nLine 2\n".as_slice()));
            assert_eq!(
                output(&case, "xx01"),
                Some(b"Line 3\nLine 4\nLine 5".as_slice())
            );
        }

        #[test]
        fn regex_plus_quantifier() {
            let case = run_case("plus", b"a\naa\naaa\ntest", &["plus", "/a+/"]);
            assert_eq!(case.status, ExitCode::FAILURE);
            assert!(case.stdout.is_empty());
            assert_eq!(case.stderr, b"main: a+: no match\n");
            assert_eq!(output(&case, "xx00"), None);
            assert_eq!(output(&case, "xx01"), None);
            assert!(case
                .operations
                .contains(&MockOperation::RemoveOutput(OsString::from("xx00"))));
        }

        #[test]
        fn multiple_patterns_line() {
            let case = run_case(
                "multi",
                b"Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6",
                &["multi", "2", "4"],
            );
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert_eq!(output(&case, "xx00"), Some(b"Line 1\n".as_slice()));
            assert_eq!(output(&case, "xx01"), Some(b"Line 2\nLine 3\n".as_slice()));
            assert_eq!(
                output(&case, "xx02"),
                Some(b"Line 4\nLine 5\nLine 6".as_slice())
            );
        }

        #[test]
        fn regex_line_boundary() {
            let case = run_case(
                "boundary",
                b"start test\ntest middle\ntest\nend",
                &["boundary", "/^test$/"],
            );
            assert_eq!(case.status, ExitCode::FAILURE);
            assert!(case.stdout.is_empty());
            assert_eq!(case.stderr, b"main: ^test$: no match\n");
            assert_eq!(output(&case, "xx00"), None);
            assert_eq!(output(&case, "xx01"), None);
            assert!(case
                .operations
                .contains(&MockOperation::RemoveOutput(OsString::from("xx00"))));
        }

        #[test]
        fn single_line_file() {
            let case = run_case("single", b"Single line", &["single", "1"]);
            assert_eq!(case.status, ExitCode::SUCCESS);
            assert_eq!(case.stdout, b"0\n11\n");
            assert_eq!(output(&case, "xx00"), Some(b"".as_slice()));
            assert_eq!(output(&case, "xx01"), Some(b"Single line".as_slice()));
        }
    }
}
