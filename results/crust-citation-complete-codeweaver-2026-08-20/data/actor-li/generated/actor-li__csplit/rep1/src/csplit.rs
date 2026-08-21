use std::ffi::OsStr;
use std::io::{self, SeekFrom, Write};
use std::os::unix::ffi::OsStrExt;

use crate::boundary::{
    FileSystem, InputStream, LineChunk, RegexCompiler, SplitStream, FGETS_CAPACITY,
    OVERFLOW_BLOCK_SIZE,
};
use crate::cli::{parse_repetition, strtol10, Invocation, Options};

const PATH_MAX: usize = 4096;

#[derive(Debug)]
pub enum CsplitError {
    Raw(Vec<u8>),
    Message {
        program: Option<Vec<u8>>,
        detail: Vec<u8>,
    },
    Os {
        program: Vec<u8>,
        context: Vec<u8>,
        source: io::Error,
    },
}

impl CsplitError {
    pub fn message(program: Vec<u8>, detail: Vec<u8>) -> Self {
        Self::Message {
            program: Some(program),
            detail,
        }
    }

    pub(crate) fn deferred_message(detail: Vec<u8>) -> Self {
        Self::Message {
            program: None,
            detail,
        }
    }

    fn raw(bytes: Vec<u8>) -> Self {
        Self::Raw(bytes)
    }

    fn os(program: Vec<u8>, context: Vec<u8>, source: io::Error) -> Self {
        Self::Os {
            program,
            context,
            source,
        }
    }

    fn with_program(mut self, program: &[u8]) -> Self {
        match &mut self {
            Self::Message {
                program: current @ None,
                ..
            } => *current = Some(program.to_vec()),
            _ => {}
        }
        self
    }

    pub const fn exit_status(&self) -> u8 {
        1
    }

    pub fn write_to(&self, writer: &mut dyn Write) -> io::Result<()> {
        match self {
            Self::Raw(bytes) => writer.write_all(bytes),
            Self::Message { program, detail } => {
                if let Some(program) = program {
                    writer.write_all(program)?;
                    writer.write_all(b": ")?;
                }
                writer.write_all(detail)?;
                writer.write_all(b"\n")
            }
            Self::Os {
                program,
                context,
                source,
            } => {
                writer.write_all(program)?;
                writer.write_all(b": ")?;
                writer.write_all(context)?;
                writer.write_all(b": ")?;
                writer.write_all(os_error_text(source).as_bytes())?;
                writer.write_all(b"\n")
            }
        }
    }
}

fn os_error_text(source: &io::Error) -> String {
    let mut text = source.to_string();
    if let Some(code) = source.raw_os_error() {
        let suffix = format!(" (os error {code})");
        if text.ends_with(&suffix) {
            text.truncate(text.len() - suffix.len());
        }
    }
    text
}

pub(crate) fn usage_bytes(program: &[u8]) -> Vec<u8> {
    let mut bytes = b"usage: ".to_vec();
    bytes.extend_from_slice(program);
    bytes.extend_from_slice(b" [-ks] [-f prefix] [-n number] file args ...\n");
    bytes
}

pub fn usage(program: &[u8]) -> CsplitError {
    CsplitError::raw(usage_bytes(program))
}

pub(crate) fn getopt_error(
    argv0: &[u8],
    progname: &[u8],
    option: u8,
    missing_argument: bool,
) -> CsplitError {
    let mut bytes = argv0.to_vec();
    if missing_argument {
        bytes.extend_from_slice(b": option requires an argument -- '");
    } else {
        bytes.extend_from_slice(b": invalid option -- '");
    }
    bytes.push(option);
    bytes.extend_from_slice(b"'\n");
    bytes.extend_from_slice(&usage_bytes(progname));
    CsplitError::raw(bytes)
}

pub struct Csplit<'a> {
    pub program: Vec<u8>,
    pub options: Options,
    pub lineno: i64,
    pub reps: i64,
    pub nfiles: i64,
    pub maxfiles: i64,
    pub currfile: Vec<u8>,
    pub infn: Vec<u8>,
    pub infile: Option<Box<dyn InputStream>>,
    infile_read_error: Option<io::Error>,
    pub overfile: Option<Box<dyn SplitStream>>,
    overfile_read_error: Option<io::Error>,
    pub truncofs: u64,
    pub doclean: bool,
    pub file_system: &'a mut dyn FileSystem,
    pub regex_compiler: &'a mut dyn RegexCompiler,
    pub stdout: &'a mut dyn Write,
}

impl<'a> Csplit<'a> {
    pub fn from_invocation(
        invocation: Invocation,
        file_system: &'a mut dyn FileSystem,
        regex_compiler: &'a mut dyn RegexCompiler,
        stdout: &'a mut dyn Write,
    ) -> Result<Self, CsplitError> {
        let Invocation {
            progname,
            options,
            input,
            ..
        } = invocation;

        let suffix_len = usize::try_from(options.sufflen).unwrap_or(usize::MAX);
        if options
            .prefix
            .len()
            .checked_add(suffix_len)
            .map_or(true, |length| length >= PATH_MAX)
        {
            return Err(CsplitError::message(progname, b"name too long".to_vec()));
        }

        let (infn, infile) = if input == b"-" {
            let infn = b"stdin".to_vec();
            let infile = file_system
                .stdin()
                .map_err(|source| CsplitError::os(progname.clone(), infn.clone(), source))?;
            (infn, infile)
        } else {
            let infile = file_system
                .open_input(OsStr::from_bytes(&input))
                .map_err(|source| CsplitError::os(progname.clone(), input.clone(), source))?;
            (input, infile)
        };

        let maxfiles =
            compute_maxfiles(options.sufflen).map_err(|error| error.with_program(&progname))?;
        let doclean = !options.kflag;

        Ok(Self {
            program: progname,
            options,
            lineno: 0,
            reps: 0,
            nfiles: 0,
            maxfiles,
            currfile: Vec::new(),
            infn,
            infile: Some(infile),
            infile_read_error: None,
            overfile: None,
            overfile_read_error: None,
            truncofs: 0,
            doclean,
            file_system,
            regex_compiler,
            stdout,
        })
    }

    fn numbered_name(&self, index: i64) -> Vec<u8> {
        let width = usize::try_from(self.options.sufflen).unwrap_or_default();
        let mut name = self.options.prefix.clone();
        name.extend_from_slice(format!("{index:0width$}").as_bytes());
        name
    }

    fn detail(&self, detail: Vec<u8>) -> CsplitError {
        CsplitError::message(self.program.clone(), detail)
    }

    fn os_error(&self, context: Vec<u8>, source: io::Error) -> CsplitError {
        CsplitError::os(self.program.clone(), context, source)
    }

    fn context_detail(&self, context: &[u8], suffix: &[u8]) -> CsplitError {
        let mut detail = context.to_vec();
        detail.extend_from_slice(suffix);
        self.detail(detail)
    }

    fn report(&mut self, position: u64) {
        if !self.options.sflag {
            let _ = writeln!(self.stdout, "{position}");
        }
    }

    pub fn execute(&mut self, expressions: &[Vec<u8>]) -> Result<(), CsplitError> {
        let mut index = 0;
        while self.nfiles < self.maxfiles - 1 && index < expressions.len() {
            let expression = &expressions[index];
            index += 1;

            if expressions
                .get(index)
                .and_then(|token| token.first())
                .copied()
                == Some(b'{')
            {
                self.reps = parse_repetition(&expressions[index])
                    .map_err(|error| error.with_program(&self.program))?;
                index += 1;
            } else {
                self.reps = 0;
            }

            match expression.first().copied() {
                Some(b'/' | b'%') => loop {
                    self.do_rexp(expression)?;
                    let previous = self.reps;
                    self.reps = self.reps.wrapping_sub(1);
                    if previous == 0 || self.nfiles >= self.maxfiles - 1 {
                        break;
                    }
                },
                Some(byte) if byte.is_ascii_digit() => self.do_lineno(expression)?,
                _ => {
                    let mut detail = expression.clone();
                    detail.extend_from_slice(b": unrecognised pattern");
                    return Err(self.detail(detail));
                }
            }
        }

        let input_eof = self.infile.as_ref().is_none_or(|input| input.eof());
        if !input_eof {
            let mut output = self.newfile()?;
            while let Some(line) = self.get_line()? {
                output.write_c_prefix(line.c_prefix());
            }
            let context = self.currfile.clone();
            let position = output
                .position()
                .map_err(|source| self.os_error(context.clone(), source))?;
            self.report(position);
            output
                .finish()
                .map_err(|source| self.os_error(context, source))?;
        }

        self.toomuch(None, 0)?;
        self.doclean = false;
        Ok(())
    }

    pub fn newfile(&mut self) -> Result<Box<dyn SplitStream>, CsplitError> {
        self.currfile = self.numbered_name(self.nfiles);
        let program = self.program.clone();
        let context = self.currfile.clone();
        let output = self
            .file_system
            .open_output(OsStr::from_bytes(&self.currfile))
            .map_err(|source| CsplitError::os(program, context, source))?;
        self.nfiles += 1;
        Ok(output)
    }

    pub fn cleanup(&mut self) {
        if !self.doclean {
            return;
        }

        self.overfile.take();
        self.overfile_read_error = None;
        for index in 0..self.nfiles {
            let name = self.numbered_name(index);
            let _ = self.file_system.remove(OsStr::from_bytes(&name));
        }
    }

    pub fn get_line(&mut self) -> Result<Option<LineChunk>, CsplitError> {
        // ferror is sticky, but the source checks it only when fgets returns bytes.
        if let Some(output) = self.overfile.as_mut() {
            let mut consumed = Vec::with_capacity(FGETS_CAPACITY - 1);
            let mut partial_error = None;
            while consumed.len() < FGETS_CAPACITY - 1 {
                let mut byte = [0_u8; 1];
                match output.read(&mut byte) {
                    Ok(0) => break,
                    Ok(_) => {
                        consumed.push(byte[0]);
                        if byte[0] == b'\n' {
                            break;
                        }
                    }
                    Err(source) => {
                        partial_error = Some(source);
                        break;
                    }
                }
            }

            if let Some(source) = partial_error {
                self.overfile_read_error = Some(source);
            }
            if !consumed.is_empty() {
                if let Some(source) = self.overfile_read_error.take() {
                    return Err(self.os_error(self.infn.clone(), source));
                }
                self.lineno = self.lineno.wrapping_add(1);
                return Ok(Some(LineChunk { consumed }));
            }
        }

        let Some(input) = self.infile.as_mut() else {
            return Ok(None);
        };
        let read = input.read_chunk(FGETS_CAPACITY);
        if let Some(source) = read.error {
            self.infile_read_error = Some(source);
        }
        match read.chunk {
            Some(chunk) => {
                if let Some(source) = self.infile_read_error.take() {
                    return Err(self.os_error(self.infn.clone(), source));
                }
                self.lineno = self.lineno.wrapping_add(1);
                Ok(Some(chunk))
            }
            None => Ok(None),
        }
    }

    pub fn toomuch(
        &mut self,
        output: Option<Box<dyn SplitStream>>,
        lines: i64,
    ) -> Result<(), CsplitError> {
        if let Some(mut previous) = self.overfile.take() {
            self.overfile_read_error = None;
            previous
                .flush_checked()
                .map_err(|source| self.os_error(b"overflow".to_vec(), source))?;
            previous
                .set_len(self.truncofs)
                .map_err(|source| self.os_error(b"overflow".to_vec(), source))?;
            previous
                .finish()
                .map_err(|source| self.os_error(b"overflow".to_vec(), source))?;
        }

        if lines == 0 {
            return Ok(());
        }

        let Some(mut output) = output else {
            return Err(self.detail(b"can't read overflowed output".to_vec()));
        };
        self.lineno = self.lineno.wrapping_sub(lines);
        let mut lines_left = lines;
        let mut buffer = vec![0_u8; OVERFLOW_BLOCK_SIZE];

        let (final_read, final_reverse_index) = loop {
            let position = output
                .position()
                .map_err(|_| self.context_detail(&self.currfile, b": can't seek"))?;
            let seek = if position < OVERFLOW_BLOCK_SIZE as u64 {
                SeekFrom::Start(0)
            } else {
                SeekFrom::Current(-(OVERFLOW_BLOCK_SIZE as i64))
            };
            output
                .seek(seek)
                .map_err(|_| self.context_detail(&self.currfile, b": can't seek"))?;

            let read = output
                .read(&mut buffer)
                .map_err(|_| self.detail(b"can't read overflowed output".to_vec()))?;
            if read == 0 {
                return Err(self.detail(b"can't read overflowed output".to_vec()));
            }
            output
                .seek(SeekFrom::Current(-(read as i64)))
                .map_err(|source| self.os_error(self.currfile.clone(), source))?;

            let mut reverse_index = read + 1;
            for index in 1..=read {
                if buffer[read - index] == b'\n' {
                    let previous = lines_left;
                    lines_left = lines_left.wrapping_sub(1);
                    if previous == 0 {
                        reverse_index = index;
                        break;
                    }
                }
            }

            let at_start = output
                .position()
                .map_err(|_| self.context_detail(&self.currfile, b": can't seek"))?
                == 0;
            if at_start || lines_left <= 0 {
                break (read, reverse_index);
            }
        };

        let forward = final_read + 1 - final_reverse_index;
        output
            .seek(SeekFrom::Current(forward as i64))
            .map_err(|source| self.os_error(self.currfile.clone(), source))?;
        self.truncofs = output
            .position()
            .map_err(|source| self.os_error(self.currfile.clone(), source))?;
        self.overfile_read_error = None;
        self.overfile = Some(output);
        Ok(())
    }

    pub fn do_rexp(&mut self, expression: &[u8]) -> Result<(), CsplitError> {
        let delimiter = expression[0];
        let last = expression
            .iter()
            .rposition(|byte| *byte == delimiter)
            .unwrap_or(0);
        if last > 0 && expression[last - 1] == b'\\' {
            let mut detail = expression.to_vec();
            detail.extend_from_slice(b": missing trailing ");
            detail.push(delimiter);
            return Err(self.detail(detail));
        }

        let (pattern, offset_bytes) = if last == 0 {
            (&expression[1..], &expression[1..])
        } else {
            (&expression[1..last], &expression[last + 1..])
        };
        let offset = if offset_bytes.is_empty() {
            0
        } else {
            let parsed = strtol10(offset_bytes);
            if parsed.end != offset_bytes.len() || parsed.overflowed {
                let mut detail = offset_bytes.to_vec();
                detail.extend_from_slice(b": bad offset");
                return Err(self.detail(detail));
            }
            parsed.value
        };

        let mut matcher = self.regex_compiler.compile(pattern).map_err(|_| {
            let mut detail = pattern.to_vec();
            detail.extend_from_slice(b": bad regular expression");
            self.detail(detail)
        })?;

        let mut output = if delimiter == b'/' {
            self.newfile()?
        } else {
            let program = self.program.clone();
            self.file_system
                .temporary()
                .map_err(|source| CsplitError::os(program, b"tmpfile".to_vec(), source))?
        };

        let mut first = true;
        let mut matched = false;
        while let Some(line) = self.get_line()? {
            output.write_c_prefix(line.c_prefix());
            if !first && matcher.is_match(line.c_prefix()) {
                matched = true;
                break;
            }
            first = false;
        }

        if !matched {
            self.toomuch(None, 0)?;
            let mut detail = pattern.to_vec();
            detail.extend_from_slice(b": no match");
            return Err(self.detail(detail));
        }

        let written;
        if offset <= 0 {
            // Preserve the fixed 64-bit source's machine result for the two
            // extreme offsets instead of turning valid strtol values into errors.
            let rewind = 1_i64.wrapping_sub(offset);
            self.toomuch(Some(output), rewind)?;
            written = self.truncofs;
        } else {
            let mut remaining = offset;
            while {
                remaining -= 1;
                remaining > 0
            } {
                let Some(line) = self.get_line()? else {
                    break;
                };
                output.write_c_prefix(line.c_prefix());
            }
            self.toomuch(None, 0)?;
            let context = self.currfile.clone();
            written = output
                .position()
                .map_err(|source| self.os_error(context.clone(), source))?;
            output
                .finish()
                .map_err(|source| self.os_error(context, source))?;
        }

        if delimiter == b'/' {
            self.report(written);
        }
        Ok(())
    }

    pub fn do_lineno(&mut self, expression: &[u8]) -> Result<(), CsplitError> {
        let parsed = strtol10(expression);
        if parsed.value <= 0 || parsed.overflowed || parsed.end != expression.len() {
            let mut detail = expression.to_vec();
            detail.extend_from_slice(b": bad line number");
            return Err(self.detail(detail));
        }
        let target = parsed.value;
        let mut lastline = target;
        if lastline <= self.lineno {
            let mut detail = expression.to_vec();
            detail.extend_from_slice(b": can't go backwards");
            return Err(self.detail(detail));
        }

        while self.nfiles < self.maxfiles - 1 {
            let mut output = self.newfile()?;
            while self.lineno.wrapping_add(1) != lastline {
                let Some(line) = self.get_line()? else {
                    return Err(self.detail(format!("{lastline}: out of range").into_bytes()));
                };
                output.write_c_prefix(line.c_prefix());
            }

            let context = self.currfile.clone();
            let position = output
                .position()
                .map_err(|source| self.os_error(context.clone(), source))?;
            self.report(position);
            output
                .finish()
                .map_err(|source| self.os_error(context, source))?;

            let previous = self.reps;
            self.reps = self.reps.wrapping_sub(1);
            if previous == 0 {
                break;
            }
            lastline = lastline.wrapping_add(target);
        }
        Ok(())
    }
}

pub fn compute_maxfiles(sufflen: i64) -> Result<i64, CsplitError> {
    let mut maxfiles = 1_i64;
    let mut index = 0_i64;
    while index < sufflen {
        if maxfiles > i64::MAX / 10 {
            return Err(CsplitError::deferred_message(
                format!("{sufflen}: suffix too long (limit {index})").into_bytes(),
            ));
        }
        maxfiles *= 10;
        index += 1;
    }
    Ok(maxfiles)
}

pub fn run(
    invocation: Invocation,
    file_system: &mut dyn FileSystem,
    regex_compiler: &mut dyn RegexCompiler,
    stdout: &mut dyn Write,
) -> Result<(), CsplitError> {
    let expressions = invocation.expressions.clone();
    let mut csplit = Csplit::from_invocation(invocation, file_system, regex_compiler, stdout)?;
    match csplit.execute(&expressions) {
        Ok(()) => Ok(()),
        Err(error) => {
            csplit.cleanup();
            Err(error)
        }
    }
}

#[cfg(test)]
mod tests {
    use std::collections::VecDeque;
    use std::ffi::OsString;
    use std::io::{self, Cursor};
    use std::os::unix::ffi::OsStringExt;

    use crate::boundary::{ChunkRead, LineChunk, PosixRegexCompiler};
    use crate::cli::{parse, Invocation, Options};
    use crate::test_support::{
        MockFileSystem, MockInputStream, MockOperation, MockRegexCompiler, MockSplitStream,
        MockWriter,
    };

    use super::{compute_maxfiles, run, Csplit, CsplitError};

    fn invocation(expressions: &[&[u8]]) -> Invocation {
        Invocation {
            argv0: b"csplit".to_vec(),
            progname: b"csplit".to_vec(),
            options: Options::default(),
            input: b"in".to_vec(),
            expressions: expressions.iter().map(|value| value.to_vec()).collect(),
        }
    }

    fn run_with_input(
        input: &[u8],
        expressions: &[&[u8]],
    ) -> (Result<(), super::CsplitError>, MockFileSystem, Vec<u8>) {
        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", input);
        let mut compiler = PosixRegexCompiler;
        let mut stdout = Vec::new();
        let result = run(
            invocation(expressions),
            &mut file_system,
            &mut compiler,
            &mut stdout,
        );
        (result, file_system, stdout)
    }

    fn run_core_case(
        input: &[u8],
        expressions: &[&[u8]],
        options: Options,
    ) -> (Result<(), super::CsplitError>, MockFileSystem, Vec<u8>) {
        let mut call = invocation(expressions);
        call.options = options;
        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", input);
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();
        let result = run(call, &mut file_system, &mut compiler, &mut stdout);
        (result, file_system, stdout)
    }

    fn run_regex_case(
        input: &[u8],
        expressions: &[&[u8]],
        scripts: &[&[bool]],
        options: Options,
    ) -> (
        Result<(), super::CsplitError>,
        MockFileSystem,
        MockRegexCompiler,
        Vec<u8>,
    ) {
        let mut call = invocation(expressions);
        call.options = options;
        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", input);
        let mut compiler = MockRegexCompiler {
            match_sequences: scripts
                .iter()
                .map(|script| script.iter().copied().collect())
                .collect(),
            ..MockRegexCompiler::default()
        };
        let mut stdout = Vec::new();
        let result = run(call, &mut file_system, &mut compiler, &mut stdout);
        (result, file_system, compiler, stdout)
    }

    fn toomuch_position(bytes: &[u8], lines: i64) -> (u64, i64) {
        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", b"");
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();
        let mut state = Csplit::from_invocation(
            invocation(&[]),
            &mut file_system,
            &mut compiler,
            &mut stdout,
        )
        .expect("create overflow state");
        state.currfile = b"xx00".to_vec();
        state.lineno = 20;
        let mut output = MockSplitStream::default();
        output.cursor = Cursor::new(bytes.to_vec());
        output.cursor.set_position(bytes.len() as u64);

        state
            .toomuch(Some(Box::new(output)), lines)
            .expect("rewind overflow");
        (state.truncofs, state.lineno)
    }

    fn get_line_steps(input: &[u8], count: usize) -> Vec<(Option<Vec<u8>>, bool, i64)> {
        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", input);
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();
        let mut state = Csplit::from_invocation(
            invocation(&[]),
            &mut file_system,
            &mut compiler,
            &mut stdout,
        )
        .expect("create splitter state");

        (0..count)
            .map(|_| {
                let chunk = state
                    .get_line()
                    .expect("read input chunk")
                    .map(|line| line.consumed);
                let eof = state.infile.as_ref().expect("input stream").eof();
                (chunk, eof, state.lineno)
            })
            .collect()
    }

    fn render(error: super::CsplitError) -> Vec<u8> {
        let mut bytes = Vec::new();
        error.write_to(&mut bytes).expect("render error");
        bytes
    }

    #[test]
    fn suffix_width_eighteen_succeeds() {
        assert_eq!(compute_maxfiles(18).unwrap(), 1_000_000_000_000_000_000);
    }

    #[test]
    fn suffix_width_nineteen_reports_limit_eighteen() {
        assert_eq!(
            render(compute_maxfiles(19).unwrap_err()),
            b"19: suffix too long (limit 18)\n"
        );
    }

    #[test]
    fn name_length_4095_and_4096() {
        let mut valid = invocation(&[]);
        valid.options.prefix = vec![b'x'; 4093];
        let mut valid_files = MockFileSystem::default();
        valid_files.put(b"in", b"");
        let mut valid_compiler = PosixRegexCompiler;
        let mut valid_stdout = Vec::new();
        {
            let state = Csplit::from_invocation(
                valid,
                &mut valid_files,
                &mut valid_compiler,
                &mut valid_stdout,
            )
            .expect("4095-byte output name bound should be accepted");
            assert_eq!(
                state.options.prefix.len() + state.options.sufflen as usize,
                4095
            );
        }
        assert_eq!(valid_files.calls, vec![MockOperation::OpenInput]);

        let mut invalid = invocation(&[]);
        invalid.options.prefix = vec![b'x'; 4094];
        let mut invalid_files = MockFileSystem::default();
        let mut invalid_compiler = PosixRegexCompiler;
        let mut invalid_stdout = Vec::new();
        let error = match Csplit::from_invocation(
            invalid,
            &mut invalid_files,
            &mut invalid_compiler,
            &mut invalid_stdout,
        ) {
            Ok(_) => panic!("4096-byte output name bound should be rejected"),
            Err(error) => error,
        };
        assert_eq!(render(error), b"csplit: name too long\n");
        assert!(invalid_files.calls.is_empty());
    }

    #[test]
    fn suffix_power_check_follows_input_open() {
        let mut overflow = invocation(&[]);
        overflow.options.sufflen = 19;
        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", b"");
        let mut compiler = PosixRegexCompiler;
        let mut stdout = Vec::new();

        let error =
            match Csplit::from_invocation(overflow, &mut file_system, &mut compiler, &mut stdout) {
                Ok(_) => panic!("suffix width 19 should be rejected"),
                Err(error) => error,
            };

        assert_eq!(render(error), b"csplit: 19: suffix too long (limit 18)\n");
        assert_eq!(file_system.calls, vec![MockOperation::OpenInput]);
    }

    #[test]
    fn input_selection_opens_named_file_or_stdin() {
        let mut named_files = MockFileSystem::default();
        named_files.put(b"in", b"contents");
        let mut named_compiler = PosixRegexCompiler;
        let mut named_stdout = Vec::new();
        {
            let state = Csplit::from_invocation(
                invocation(&[]),
                &mut named_files,
                &mut named_compiler,
                &mut named_stdout,
            )
            .expect("open named input");
            assert_eq!(state.infn, b"in");
        }
        assert_eq!(named_files.calls, vec![MockOperation::OpenInput]);

        let mut stdin_invocation = invocation(&[]);
        stdin_invocation.input = b"-".to_vec();
        let mut stdin_files = MockFileSystem {
            stdin_bytes: b"contents".to_vec(),
            ..MockFileSystem::default()
        };
        let mut stdin_compiler = PosixRegexCompiler;
        let mut stdin_stdout = Vec::new();
        {
            let state = Csplit::from_invocation(
                stdin_invocation,
                &mut stdin_files,
                &mut stdin_compiler,
                &mut stdin_stdout,
            )
            .expect("select stdin");
            assert_eq!(state.infn, b"stdin");
        }
        assert_eq!(stdin_files.calls, vec![MockOperation::Stdin]);
    }

    #[test]
    fn raw_non_utf8_argv_input_and_prefix_round_trip() {
        let input_name = b"input-\xff";
        let prefix = b"output-\xfe";
        let call = parse(
            vec![
                OsString::from_vec(b"csplit".to_vec()),
                OsString::from_vec(b"-f".to_vec()),
                OsString::from_vec(prefix.to_vec()),
                OsString::from_vec(input_name.to_vec()),
                OsString::from_vec(b"2".to_vec()),
            ],
            false,
        )
        .expect("parse raw paths");
        let mut file_system = MockFileSystem::default();
        file_system.put(input_name, b"\xff\nrest");
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();

        run(call, &mut file_system, &mut compiler, &mut stdout).expect("split raw path");

        let mut first_name = prefix.to_vec();
        first_name.extend_from_slice(b"00");
        let mut second_name = prefix.to_vec();
        second_name.extend_from_slice(b"01");
        assert_eq!(
            file_system.get(&first_name).as_deref(),
            Some(&b"\xff\n"[..])
        );
        assert_eq!(file_system.get(&second_name).as_deref(), Some(&b"rest"[..]));
        assert_eq!(stdout, b"2\n4\n");
    }

    #[test]
    fn stdin_consumes_nul_tails_but_writes_only_c_prefixes() {
        let mut call = invocation(&[b"2"]);
        call.input = b"-".to_vec();
        let mut file_system = MockFileSystem {
            stdin_bytes: b"\xff\0hidden\nz".to_vec(),
            ..MockFileSystem::default()
        };
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();

        run(call, &mut file_system, &mut compiler, &mut stdout).expect("split stdin bytes");

        assert_eq!(file_system.get(b"xx00").as_deref(), Some(&b"\xff"[..]));
        assert_eq!(file_system.get(b"xx01").as_deref(), Some(&b"z"[..]));
        assert_eq!(stdout, b"1\n1\n");
        assert_eq!(
            file_system.calls,
            vec![
                MockOperation::Stdin,
                MockOperation::OpenOutput,
                MockOperation::OpenOutput,
            ]
        );
    }

    #[test]
    fn empty_input_creates_empty_output_without_expressions() {
        let (result, file_system, stdout) = run_core_case(b"", &[], Options::default());

        result.expect("empty input should produce the initial output");
        assert_eq!(file_system.get(b"xx00").as_deref(), Some(&b""[..]));
        assert_eq!(stdout, b"0\n");
        assert_eq!(
            file_system.calls,
            vec![MockOperation::OpenInput, MockOperation::OpenOutput]
        );
        assert!(file_system.removed.is_empty());

        let (split, split_files, split_stdout) = run_core_case(b"", &[b"1"], Options::default());
        split.expect("line one on empty input");
        assert_eq!(split_files.get(b"xx00").as_deref(), Some(&b""[..]));
        assert_eq!(split_files.get(b"xx01").as_deref(), Some(&b""[..]));
        assert_eq!(split_stdout, b"0\n0\n");
    }

    #[test]
    fn newline_and_unterminated_eof_timing() {
        assert_eq!(get_line_steps(b"", 1), vec![(None, true, 0)]);
        assert_eq!(
            get_line_steps(b"x", 2),
            vec![(Some(b"x".to_vec()), true, 1), (None, true, 1),]
        );
        assert_eq!(
            get_line_steps(b"x\n", 2),
            vec![(Some(b"x\n".to_vec()), false, 1), (None, true, 1),]
        );

        let (unterminated, unterminated_files, unterminated_stdout) =
            run_core_case(b"x", &[b"2"], Options::default());
        unterminated.expect("unterminated split");
        assert_eq!(unterminated_files.get(b"xx00").as_deref(), Some(&b"x"[..]));
        assert_eq!(unterminated_files.get(b"xx01"), None);
        assert_eq!(unterminated_stdout, b"1\n");

        let (terminated, terminated_files, terminated_stdout) =
            run_core_case(b"x\n", &[b"2"], Options::default());
        terminated.expect("newline-terminated split");
        assert_eq!(terminated_files.get(b"xx00").as_deref(), Some(&b"x\n"[..]));
        assert_eq!(terminated_files.get(b"xx01").as_deref(), Some(&b""[..]));
        assert_eq!(terminated_stdout, b"2\n0\n");
    }

    #[test]
    fn chunks_at_2047_2048_and_4094_bytes() {
        let bytes_2047 = vec![b'a'; 2047];
        assert_eq!(
            get_line_steps(&bytes_2047, 2),
            vec![(Some(bytes_2047.clone()), false, 1), (None, true, 1),]
        );

        let bytes_2048 = vec![b'b'; 2048];
        assert_eq!(
            get_line_steps(&bytes_2048, 3),
            vec![
                (Some(vec![b'b'; 2047]), false, 1),
                (Some(vec![b'b']), true, 2),
                (None, true, 2),
            ]
        );

        let bytes_4094 = vec![b'c'; 4094];
        assert_eq!(
            get_line_steps(&bytes_4094, 3),
            vec![
                (Some(vec![b'c'; 2047]), false, 1),
                (Some(vec![b'c'; 2047]), false, 2),
                (None, true, 2),
            ]
        );
    }

    #[test]
    fn embedded_nul_consumes_but_does_not_write_tail() {
        let (result, file_system, stdout) =
            run_core_case(b"ab\0ignored\ncd\0tail", &[], Options::default());

        result.expect("NUL-bearing input should split");
        assert_eq!(file_system.get(b"xx00").as_deref(), Some(&b"abcd"[..]));
        assert_eq!(stdout, b"4\n");
    }

    #[test]
    fn long_chunks_and_embedded_nul_match_as_c_strings() {
        let mut input = vec![b'a'; super::FGETS_CAPACITY - 1];
        input.extend_from_slice(b"b\0needle\nneedle\nlast");
        let (result, file_system, stdout) = run_with_input(&input, &[b"/needle/+1"]);

        result.expect("split long NUL-bearing stream");
        let mut first = vec![b'a'; super::FGETS_CAPACITY - 1];
        first.extend_from_slice(b"bneedle\n");
        assert_eq!(file_system.get(b"xx00").as_deref(), Some(first.as_slice()));
        assert_eq!(file_system.get(b"xx01").as_deref(), Some(&b"last"[..]));
        assert_eq!(stdout, b"2055\n4\n");
    }

    #[test]
    fn original_input_eof_alone_controls_final_overflow_copy() {
        let (unterminated, unterminated_files, _, unterminated_stdout) =
            run_regex_case(b"a\nm", &[b"/m/0"], &[&[true]], Options::default());
        unterminated.expect("split at unterminated final chunk");
        assert_eq!(unterminated_files.get(b"xx00").as_deref(), Some(&b""[..]));
        assert!(unterminated_files.get(b"xx01").is_none());
        assert_eq!(unterminated_stdout, b"0\n");

        let (terminated, terminated_files, _, terminated_stdout) =
            run_regex_case(b"a\nm\n", &[b"/m/0"], &[&[true]], Options::default());
        terminated.expect("split at terminated final chunk");
        assert_eq!(terminated_files.get(b"xx00").as_deref(), Some(&b"a\n"[..]));
        assert_eq!(terminated_files.get(b"xx01").as_deref(), Some(&b"m\n"[..]));
        assert_eq!(terminated_stdout, b"2\n2\n");
    }

    #[test]
    fn overflow_exhaustion_switches_to_input_in_same_call() {
        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", b"input\n");
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();
        let mut state = Csplit::from_invocation(
            invocation(&[]),
            &mut file_system,
            &mut compiler,
            &mut stdout,
        )
        .expect("create splitter state");
        let mut overflow = MockSplitStream::default();
        overflow.cursor = Cursor::new(b"exhausted".to_vec());
        overflow.cursor.set_position(b"exhausted".len() as u64);
        state.overfile = Some(Box::new(overflow));

        let chunk = state
            .get_line()
            .expect("switch from overflow to input")
            .expect("input chunk");

        assert_eq!(chunk.consumed, b"input\n");
        assert_eq!(state.lineno, 1);
        assert!(state.overfile.is_some());
    }

    #[test]
    fn immediate_and_partial_read_errors_follow_fgets_order() {
        let mut immediate_files = MockFileSystem::default();
        immediate_files.put(b"in", b"unused");
        let mut immediate_compiler = MockRegexCompiler::default();
        let mut immediate_stdout = Vec::new();
        let mut immediate = Csplit::from_invocation(
            invocation(&[]),
            &mut immediate_files,
            &mut immediate_compiler,
            &mut immediate_stdout,
        )
        .expect("create immediate-error state");
        let mut immediate_input = MockInputStream::default();
        immediate_input.reads = VecDeque::from([ChunkRead {
            chunk: None,
            eof: false,
            error: Some(io::Error::other("immediate read failure")),
        }]);
        immediate.infile = Some(Box::new(immediate_input));

        assert!(immediate
            .get_line()
            .expect("immediate fgets failure is treated as EOF")
            .is_none());
        assert_eq!(immediate.lineno, 0);

        let mut partial_files = MockFileSystem::default();
        partial_files.put(b"in", b"unused");
        let mut partial_compiler = MockRegexCompiler::default();
        let mut partial_stdout = Vec::new();
        let mut partial = Csplit::from_invocation(
            invocation(&[]),
            &mut partial_files,
            &mut partial_compiler,
            &mut partial_stdout,
        )
        .expect("create partial-error state");
        let mut partial_input = MockInputStream::default();
        partial_input.reads = VecDeque::from([ChunkRead {
            chunk: Some(LineChunk {
                consumed: b"partial".to_vec(),
            }),
            eof: false,
            error: Some(io::Error::other("partial read failure")),
        }]);
        partial.infile = Some(Box::new(partial_input));

        let error = partial.get_line().unwrap_err();
        assert_eq!(render(error), b"csplit: in: partial read failure\n");
        assert_eq!(partial.lineno, 0);

        let mut sticky_files = MockFileSystem::default();
        sticky_files.put(b"in", b"unused");
        let mut sticky_compiler = MockRegexCompiler::default();
        let mut sticky_stdout = Vec::new();
        let mut sticky = Csplit::from_invocation(
            invocation(&[]),
            &mut sticky_files,
            &mut sticky_compiler,
            &mut sticky_stdout,
        )
        .expect("create sticky-error state");
        let mut sticky_input = MockInputStream::default();
        sticky_input.reads = VecDeque::from([
            ChunkRead {
                chunk: None,
                eof: false,
                error: Some(io::Error::other("transient input failure")),
            },
            ChunkRead {
                chunk: Some(LineChunk {
                    consumed: b"recovered\n".to_vec(),
                }),
                eof: false,
                error: None,
            },
        ]);
        sticky.infile = Some(Box::new(sticky_input));

        assert!(sticky
            .get_line()
            .expect("an immediate error is initially treated as EOF")
            .is_none());
        assert_eq!(
            render(sticky.get_line().unwrap_err()),
            b"csplit: in: transient input failure\n"
        );
        assert_eq!(sticky.lineno, 0);
    }

    #[test]
    fn overflow_read_error_stays_sticky_after_switching_to_input() {
        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", b"input\n");
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();
        let mut state = Csplit::from_invocation(
            invocation(&[]),
            &mut file_system,
            &mut compiler,
            &mut stdout,
        )
        .expect("create overflow error state");
        let mut overflow = MockSplitStream::default();
        overflow.cursor = Cursor::new(b"replay\n".to_vec());
        overflow
            .scripted_read_errors
            .push_back(Some(io::Error::other("transient overflow failure")));
        state.overfile = Some(Box::new(overflow));

        assert_eq!(
            state
                .get_line()
                .expect("switch to input after immediate overflow error")
                .expect("input chunk")
                .consumed,
            b"input\n"
        );
        assert_eq!(state.lineno, 1);
        assert_eq!(
            render(state.get_line().unwrap_err()),
            b"csplit: in: transient overflow failure\n"
        );
        assert_eq!(state.lineno, 1);
    }

    #[test]
    fn immediate_read_failure_is_silent_eof_during_final_copy() {
        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", b"unused");
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();
        {
            let mut state = Csplit::from_invocation(
                invocation(&[]),
                &mut file_system,
                &mut compiler,
                &mut stdout,
            )
            .expect("create final-copy state");
            let mut input = MockInputStream::default();
            input.reads = VecDeque::from([ChunkRead {
                chunk: None,
                eof: false,
                error: Some(io::Error::other("ignored immediate failure")),
            }]);
            state.infile = Some(Box::new(input));

            state
                .execute(&[])
                .expect("source treats an immediate fgets error as EOF");
        }

        assert_eq!(file_system.get(b"xx00").as_deref(), Some(&b""[..]));
        assert_eq!(stdout, b"0\n");
        assert!(file_system.removed.is_empty());
    }

    #[test]
    fn newfile_zero_padding_and_raw_prefixes() {
        let raw_name = b"\xff/nested-000";
        let mut raw_call = invocation(&[]);
        raw_call.options.prefix = b"\xff/nested-".to_vec();
        raw_call.options.sufflen = 3;
        let mut raw_files = MockFileSystem::default();
        raw_files.put(b"in", b"");
        raw_files.put(raw_name, b"preexisting");
        let mut raw_compiler = MockRegexCompiler::default();
        let mut raw_stdout = Vec::new();
        {
            let mut state = Csplit::from_invocation(
                raw_call,
                &mut raw_files,
                &mut raw_compiler,
                &mut raw_stdout,
            )
            .expect("create raw-prefix state");
            let output = state.newfile().expect("create raw-prefix output");
            assert_eq!(state.currfile, raw_name);
            assert_eq!(state.nfiles, 1);
            output.finish().expect("finish raw-prefix output");
        }
        assert_eq!(raw_files.get(raw_name).as_deref(), Some(&b""[..]));

        let mut empty_call = invocation(&[]);
        empty_call.options.prefix.clear();
        let mut empty_files = MockFileSystem::default();
        empty_files.put(b"in", b"");
        let mut empty_compiler = MockRegexCompiler::default();
        let mut empty_stdout = Vec::new();
        {
            let mut state = Csplit::from_invocation(
                empty_call,
                &mut empty_files,
                &mut empty_compiler,
                &mut empty_stdout,
            )
            .expect("create empty-prefix state");
            state
                .newfile()
                .expect("create empty-prefix output")
                .finish()
                .expect("finish empty-prefix output");
            assert_eq!(state.currfile, b"00");
        }
        assert_eq!(empty_files.get(b"00").as_deref(), Some(&b""[..]));
    }

    #[test]
    fn create_failure_does_not_increment_nfiles() {
        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", b"");
        file_system.failure = Some(MockOperation::OpenOutput);
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();
        let mut state = Csplit::from_invocation(
            invocation(&[]),
            &mut file_system,
            &mut compiler,
            &mut stdout,
        )
        .expect("create splitter state");

        let error = match state.newfile() {
            Ok(_) => panic!("output creation should fail"),
            Err(error) => error,
        };

        assert_eq!(state.currfile, b"xx00");
        assert_eq!(state.nfiles, 0);
        assert_eq!(render(error), b"csplit: xx00: mock operation failed\n");
    }

    #[test]
    fn cleanup_removes_all_counted_outputs_unless_kflag() {
        let mut cleanup_files = MockFileSystem::default();
        cleanup_files.put(b"in", b"");
        let mut cleanup_compiler = MockRegexCompiler::default();
        let mut cleanup_stdout = Vec::new();
        {
            let mut state = Csplit::from_invocation(
                invocation(&[]),
                &mut cleanup_files,
                &mut cleanup_compiler,
                &mut cleanup_stdout,
            )
            .expect("create cleanup state");
            for contents in [b"first".as_slice(), b"second".as_slice()] {
                let mut output = state.newfile().expect("create counted output");
                output.write_c_prefix(contents);
                output.finish().expect("finish counted output");
            }
            state.cleanup();
        }
        assert_eq!(
            cleanup_files.removed,
            vec![b"xx00".to_vec(), b"xx01".to_vec()]
        );
        assert_eq!(cleanup_files.get(b"xx00"), None);
        assert_eq!(cleanup_files.get(b"xx01"), None);

        let mut keep_call = invocation(&[]);
        keep_call.options.kflag = true;
        let mut keep_files = MockFileSystem::default();
        keep_files.put(b"in", b"");
        let mut keep_compiler = MockRegexCompiler::default();
        let mut keep_stdout = Vec::new();
        {
            let mut state = Csplit::from_invocation(
                keep_call,
                &mut keep_files,
                &mut keep_compiler,
                &mut keep_stdout,
            )
            .expect("create keep state");
            state
                .newfile()
                .expect("create kept output")
                .finish()
                .expect("finish kept output");
            state.cleanup();
        }
        assert!(keep_files.removed.is_empty());
        assert_eq!(keep_files.get(b"xx00").as_deref(), Some(&b""[..]));

        let mut failed_remove_files = MockFileSystem::default();
        failed_remove_files.put(b"in", b"");
        failed_remove_files.failure = Some(MockOperation::Remove);
        let mut failed_remove_compiler = MockRegexCompiler::default();
        let mut failed_remove_stdout = Vec::new();
        {
            let mut state = Csplit::from_invocation(
                invocation(&[]),
                &mut failed_remove_files,
                &mut failed_remove_compiler,
                &mut failed_remove_stdout,
            )
            .expect("create failed-remove state");
            state
                .newfile()
                .expect("create output before remove failure")
                .finish()
                .expect("finish output before remove failure");
            state.cleanup();
        }
        assert_eq!(failed_remove_files.removed, vec![b"xx00".to_vec()]);
        assert_eq!(failed_remove_files.get(b"xx00").as_deref(), Some(&b""[..]));
    }

    #[test]
    fn repetition_lookahead_precedes_pattern_validation() {
        let (result, file_system, _) = run_with_input(b"contents\n", &[b"bogus", b"{abc}"]);
        assert_eq!(
            render(result.unwrap_err()),
            b"csplit: abc}: bad repetition count\n"
        );
        assert_eq!(file_system.calls, vec![MockOperation::OpenInput]);
    }

    #[test]
    fn usage_uses_basename() {
        let error = parse(
            vec![OsString::from_vec(b"../bin/renamed-csplit".to_vec())],
            false,
        )
        .unwrap_err();
        assert_eq!(error.exit_status(), 1);
        assert_eq!(
            render(error),
            b"usage: renamed-csplit [-ks] [-f prefix] [-n number] file args ...\n"
        );
    }

    #[test]
    fn empty_basename_still_gets_err_style_prefix() {
        let error = CsplitError::message(Vec::new(), b"bad value".to_vec());
        assert_eq!(render(error), b": bad value\n");
    }

    #[test]
    fn multiple_absolute_line_splits() {
        let (result, file_system, stdout) =
            run_with_input(b"Line 1\nLine 2\nLine 3\nLine 4\n", &[b"2", b"4"]);
        result.expect("line split");
        assert_eq!(file_system.get(b"xx00").as_deref(), Some(&b"Line 1\n"[..]));
        assert_eq!(
            file_system.get(b"xx01").as_deref(),
            Some(&b"Line 2\nLine 3\n"[..])
        );
        assert_eq!(file_system.get(b"xx02").as_deref(), Some(&b"Line 4\n"[..]));
        assert_eq!(stdout, b"7\n14\n7\n");
    }

    #[test]
    fn target_one_preserves_unterminated_remainder() {
        let (result, file_system, stdout) = run_with_input(b"Single line", &[b"1"]);
        result.expect("line split");
        assert_eq!(file_system.get(b"xx00").as_deref(), Some(&b""[..]));
        assert_eq!(
            file_system.get(b"xx01").as_deref(),
            Some(&b"Single line"[..])
        );
        assert_eq!(stdout, b"0\n11\n");
    }

    #[test]
    fn line_repetition_advances_by_original_target() {
        let (result, file_system, stdout) = run_core_case(
            b"1\n2\n3\n4\n5\n6\n7\n8\n",
            &[b"2", b"{2}"],
            Options::default(),
        );

        result.expect("repeated line split");
        assert_eq!(file_system.get(b"xx00").as_deref(), Some(&b"1\n"[..]));
        assert_eq!(file_system.get(b"xx01").as_deref(), Some(&b"2\n3\n"[..]));
        assert_eq!(file_system.get(b"xx02").as_deref(), Some(&b"4\n5\n"[..]));
        assert_eq!(file_system.get(b"xx03").as_deref(), Some(&b"6\n7\n8\n"[..]));
        assert_eq!(stdout, b"2\n4\n4\n6\n");
    }

    #[test]
    fn backward_and_out_of_range_errors() {
        let (backward, backward_files, backward_stdout) =
            run_core_case(b"1\n2\n3\n", &[b"3", b"2"], Options::default());
        assert_eq!(
            render(backward.unwrap_err()),
            b"csplit: 2: can't go backwards\n"
        );
        assert_eq!(backward_stdout, b"4\n");
        assert_eq!(backward_files.get(b"xx00"), None);
        assert_eq!(backward_files.removed, vec![b"xx00".to_vec()]);

        let mut keep = Options::default();
        keep.kflag = true;
        let (out_of_range, range_files, range_stdout) = run_core_case(b"1\n", &[b"3"], keep);
        assert_eq!(
            render(out_of_range.unwrap_err()),
            b"csplit: 3: out of range\n"
        );
        assert!(range_stdout.is_empty());
        assert!(range_files.removed.is_empty());
        assert_eq!(range_files.get(b"xx00").as_deref(), Some(&b"1\n"[..]));
    }

    #[test]
    fn silent_and_broken_stdout() {
        let mut silent = Options::default();
        silent.sflag = true;
        let (silent_result, silent_files, silent_stdout) =
            run_core_case(b"first\nsecond\n", &[b"2"], silent);
        silent_result.expect("silent split");
        assert!(silent_stdout.is_empty());
        assert_eq!(silent_files.get(b"xx00").as_deref(), Some(&b"first\n"[..]));
        assert_eq!(silent_files.get(b"xx01").as_deref(), Some(&b"second\n"[..]));

        let mut broken_files = MockFileSystem::default();
        broken_files.put(b"in", b"contents");
        let mut broken_compiler = MockRegexCompiler::default();
        let mut broken_stdout = MockWriter {
            fail: true,
            ..MockWriter::default()
        };
        let broken_result = run(
            invocation(&[]),
            &mut broken_files,
            &mut broken_compiler,
            &mut broken_stdout,
        );
        broken_result.expect("stdout errors are unchecked");
        assert_eq!(broken_files.get(b"xx00").as_deref(), Some(&b"contents"[..]));
        assert!(broken_stdout.bytes.is_empty());
    }

    #[test]
    fn suffix_reservation_leaves_the_final_output_slot() {
        let mut options = Options::default();
        options.sufflen = 1;
        let (result, file_system, stdout) = run_core_case(
            b"1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n",
            &[b"1", b"{20}", b"bogus"],
            options,
        );

        result.expect("suffix capacity should stop before the reserved final slot");
        assert_eq!(file_system.get(b"xx0").as_deref(), Some(&b""[..]));
        assert_eq!(file_system.get(b"xx1").as_deref(), Some(&b"1\n"[..]));
        assert_eq!(file_system.get(b"xx8").as_deref(), Some(&b"8\n"[..]));
        assert_eq!(
            file_system.get(b"xx9").as_deref(),
            Some(&b"9\n10\n11\n12\n"[..])
        );
        assert_eq!(file_system.get(b"xx10"), None);
        assert_eq!(stdout, b"0\n2\n2\n2\n2\n2\n2\n2\n2\n11\n");
    }

    #[test]
    fn checked_finalization_errors_trigger_ordinary_cleanup() {
        let mut file_system = MockFileSystem {
            stream_failure: Some(MockOperation::Finish),
            ..MockFileSystem::default()
        };
        file_system.put(b"in", b"data");
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();

        let error = run(
            invocation(&[]),
            &mut file_system,
            &mut compiler,
            &mut stdout,
        )
        .unwrap_err();

        assert_eq!(render(error), b"csplit: xx00: mock stream failure\n");
        assert_eq!(stdout, b"4\n");
        assert_eq!(file_system.removed, vec![b"xx00".to_vec()]);
        assert_eq!(file_system.get(b"xx00"), None);
    }

    #[test]
    fn regex_missing_trailing_uses_bad_offset_quirk() {
        let (result, _, _) = run_with_input(b"Line 1\nLine 2\n", &[b"/Line"]);
        assert_eq!(render(result.unwrap_err()), b"csplit: Line: bad offset\n");

        let (empty, empty_files, empty_stdout) = run_with_input(b"first\nsecond\nlast\n", &[b"/"]);
        empty.expect("opening delimiter alone is an empty BRE");
        assert_eq!(empty_files.get(b"xx00").as_deref(), Some(&b"first\n"[..]));
        assert_eq!(
            empty_files.get(b"xx01").as_deref(),
            Some(&b"second\nlast\n"[..])
        );
        assert_eq!(empty_stdout, b"6\n12\n");
    }

    #[test]
    fn regex_last_delimiter_and_one_backslash_rule() {
        let (result, file_system, compiler, _) = run_regex_case(
            b"first\na/b\nlast\n",
            &[b"/a/b/"],
            &[&[true]],
            Options::default(),
        );
        result.expect("final delimiter should terminate the BRE");
        assert_eq!(compiler.patterns, vec![b"a/b".to_vec()]);
        assert_eq!(file_system.get(b"xx00").as_deref(), Some(&b"first\n"[..]));

        for expression in [br"/abc\/".as_slice(), br"/abc\\/".as_slice()] {
            let (result, files, _) = run_with_input(b"first\nabc\n", &[expression]);
            let mut expected = b"csplit: ".to_vec();
            expected.extend_from_slice(expression);
            expected.extend_from_slice(b": missing trailing /\n");
            assert_eq!(render(result.unwrap_err()), expected);
            assert!(files.get(b"xx00").is_none());
        }
    }

    #[test]
    fn regex_bad_signed_and_overflow_offsets() {
        for (expression, offset) in [
            (b"/x/+".as_slice(), b"+".as_slice()),
            (b"/x/-".as_slice(), b"-".as_slice()),
            (b"/x/2tail".as_slice(), b"2tail".as_slice()),
            (
                b"/x/9223372036854775808".as_slice(),
                b"9223372036854775808".as_slice(),
            ),
            (
                b"/x/-9223372036854775809".as_slice(),
                b"-9223372036854775809".as_slice(),
            ),
        ] {
            let (result, files, _) = run_with_input(b"first\nx\n", &[expression]);
            let mut expected = b"csplit: ".to_vec();
            expected.extend_from_slice(offset);
            expected.extend_from_slice(b": bad offset\n");
            assert_eq!(render(result.unwrap_err()), expected);
            assert!(files.get(b"xx00").is_none());
        }

        let (result, files, compiler, _) = run_regex_case(
            b"first\nx\nlast\n",
            &[b"/x/ \t+1"],
            &[&[true]],
            Options::default(),
        );
        result.expect("signed offset with C whitespace");
        assert_eq!(compiler.patterns, vec![b"x".to_vec()]);
        assert_eq!(files.get(b"xx00").as_deref(), Some(&b"first\nx\n"[..]));
    }

    #[test]
    fn extreme_negative_offsets_follow_fixed_source_wrapping() {
        for expression in [
            b"/m/-9223372036854775807".as_slice(),
            b"/m/-9223372036854775808".as_slice(),
        ] {
            let (result, files, compiler, stdout) =
                run_regex_case(b"a\nm\nz\n", &[expression], &[&[true]], Options::default());

            result.expect("extreme slash offset should remain a valid signed offset");
            assert_eq!(compiler.patterns, vec![b"m".to_vec()]);
            assert_eq!(files.get(b"xx00").as_deref(), Some(&b""[..]));
            assert_eq!(files.get(b"xx01").as_deref(), Some(&b"a\nm\nz\n"[..]));
            assert_eq!(stdout, b"0\n6\n");
        }

        for expression in [
            b"%m%-9223372036854775807".as_slice(),
            b"%m%-9223372036854775808".as_slice(),
        ] {
            let (result, files, compiler, stdout) =
                run_regex_case(b"a\nm\nz\n", &[expression], &[&[true]], Options::default());

            result.expect("extreme percent offset should remain a valid signed offset");
            assert_eq!(compiler.patterns, vec![b"m".to_vec()]);
            assert_eq!(files.get(b"xx00").as_deref(), Some(&b"a\nm\nz\n"[..]));
            assert!(files.get(b"xx01").is_none());
            assert_eq!(stdout, b"6\n");
        }
    }

    #[test]
    fn malformed_regex_has_generic_diagnostic_before_output_creation() {
        let (result, file_system, _) = run_with_input(b"first\nsecond\n", &[b"/[/"]);
        assert_eq!(
            render(result.unwrap_err()),
            b"csplit: [: bad regular expression\n"
        );
        assert_eq!(file_system.calls, vec![MockOperation::OpenInput]);
        assert!(file_system.removed.is_empty());
    }

    #[test]
    fn first_chunk_is_not_matched_and_matching_is_per_chunk() {
        let (result, file_system, compiler, stdout) = run_regex_case(
            b"first\nsecond\nmatch\nlast\n",
            &[b"/x/"],
            &[&[false, true]],
            Options::default(),
        );
        result.expect("scripted regex split");
        assert_eq!(
            compiler.matched_subjects.borrow().as_slice(),
            &[b"second\n".to_vec(), b"match\n".to_vec()]
        );
        assert_eq!(
            file_system.get(b"xx00").as_deref(),
            Some(&b"first\nsecond\n"[..])
        );
        assert_eq!(
            file_system.get(b"xx01").as_deref(),
            Some(&b"match\nlast\n"[..])
        );
        assert_eq!(stdout, b"13\n11\n");
    }

    #[test]
    fn first_chunk_is_not_matched_and_cleanup_runs() {
        let (result, file_system, _) = run_with_input(b"line [1]\nline (2)\n", &[br"/\[1\]/"]);
        assert_eq!(render(result.unwrap_err()), b"csplit: \\[1\\]: no match\n");
        assert_eq!(file_system.get(b"xx00"), None);
        assert_eq!(file_system.removed, vec![b"xx00".to_vec()]);

        let mut keep = Options::default();
        keep.kflag = true;
        let (kept, kept_files, _, _) =
            run_regex_case(b"first\nsecond\n", &[b"/missing/"], &[&[false]], keep);
        assert_eq!(render(kept.unwrap_err()), b"csplit: missing: no match\n");
        assert_eq!(
            kept_files.get(b"xx00").as_deref(),
            Some(&b"first\nsecond\n"[..])
        );
        assert!(kept_files.removed.is_empty());
    }

    #[test]
    fn bre_no_match_diagnostics_remove_every_partial_output() {
        for (input, expression, expected) in [
            (
                b"a\naa\naaa\n".as_slice(),
                b"/a+/".as_slice(),
                b"csplit: a+: no match\n".as_slice(),
            ),
            (
                b"header\ntest\n".as_slice(),
                b"/^test$/".as_slice(),
                b"csplit: ^test$: no match\n".as_slice(),
            ),
        ] {
            let (result, file_system, stdout) = run_with_input(input, &[expression]);
            assert_eq!(render(result.unwrap_err()), expected);
            assert_eq!(stdout, b"");
            assert_eq!(file_system.get(b"xx00"), None);
            assert_eq!(file_system.removed, vec![b"xx00".to_vec()]);
        }

        let (result, file_system, stdout) = run_with_input(b"a\nb\nc\n", &[b"2", b"/missing/"]);
        assert_eq!(render(result.unwrap_err()), b"csplit: missing: no match\n");
        assert_eq!(stdout, b"2\n");
        assert_eq!(file_system.get(b"xx00"), None);
        assert_eq!(file_system.get(b"xx01"), None);
        assert_eq!(
            file_system.removed,
            vec![b"xx00".to_vec(), b"xx01".to_vec()]
        );
    }

    #[test]
    fn escaped_bre_alternation_splits_with_the_real_adapter() {
        let (result, file_system, stdout) =
            run_with_input(b"header\ncherry\nrest\n", &[br"/apple\|cherry/"]);
        result.expect("escaped BRE alternation should match");
        assert_eq!(file_system.get(b"xx00").as_deref(), Some(&b"header\n"[..]));
        assert_eq!(
            file_system.get(b"xx01").as_deref(),
            Some(&b"cherry\nrest\n"[..])
        );
        assert_eq!(stdout, b"7\n12\n");
        assert!(file_system.removed.is_empty());
    }

    #[test]
    fn slash_and_percent_output_behavior() {
        let (slash, slash_files, _, slash_stdout) =
            run_regex_case(b"a\nm\nz\n", &[b"/m/"], &[&[true]], Options::default());
        slash.expect("slash split");
        assert_eq!(slash_files.get(b"xx00").as_deref(), Some(&b"a\n"[..]));
        assert_eq!(slash_files.get(b"xx01").as_deref(), Some(&b"m\nz\n"[..]));
        assert_eq!(slash_stdout, b"2\n4\n");

        let (percent, percent_files, _, percent_stdout) =
            run_regex_case(b"a\nm\nz\n", &[b"%m%"], &[&[true]], Options::default());
        percent.expect("percent split");
        assert_eq!(percent_files.get(b"xx00").as_deref(), Some(&b"m\nz\n"[..]));
        assert!(percent_files.get(b"xx01").is_none());
        assert_eq!(percent_stdout, b"4\n");
        assert_eq!(
            percent_files
                .calls
                .iter()
                .filter(|call| **call == MockOperation::Temporary)
                .count(),
            1
        );
    }

    #[test]
    fn percent_offsets_discard_through_the_selected_boundary() {
        let (negative, negative_files, _, negative_stdout) = run_regex_case(
            b"a\nb\nm\nz\n",
            &[b"%m%-1"],
            &[&[false, true]],
            Options::default(),
        );
        negative.expect("negative percent offset");
        assert_eq!(
            negative_files.get(b"xx00").as_deref(),
            Some(&b"b\nm\nz\n"[..])
        );
        assert!(negative_files.get(b"xx01").is_none());
        assert_eq!(negative_stdout, b"6\n");

        let (positive, positive_files, _, positive_stdout) =
            run_regex_case(b"a\nm\nz\nq\n", &[b"%m%+2"], &[&[true]], Options::default());
        positive.expect("positive percent offset");
        assert_eq!(positive_files.get(b"xx00").as_deref(), Some(&b"q\n"[..]));
        assert!(positive_files.get(b"xx01").is_none());
        assert_eq!(positive_stdout, b"2\n");
    }

    #[test]
    fn zero_negative_and_positive_offsets() {
        let (zero, zero_files, _, zero_stdout) =
            run_regex_case(b"a\nm\nz\n", &[b"/m/0"], &[&[true]], Options::default());
        zero.expect("zero offset");
        assert_eq!(zero_files.get(b"xx00").as_deref(), Some(&b"a\n"[..]));
        assert_eq!(zero_files.get(b"xx01").as_deref(), Some(&b"m\nz\n"[..]));
        assert_eq!(zero_stdout, b"2\n4\n");

        let (negative, negative_files, _, negative_stdout) = run_regex_case(
            b"a\nb\nm\nz\n",
            &[b"/m/-1"],
            &[&[false, true]],
            Options::default(),
        );
        negative.expect("negative offset");
        assert_eq!(negative_files.get(b"xx00").as_deref(), Some(&b"a\n"[..]));
        assert_eq!(
            negative_files.get(b"xx01").as_deref(),
            Some(&b"b\nm\nz\n"[..])
        );
        assert_eq!(negative_stdout, b"2\n6\n");

        let (positive, positive_files, _, positive_stdout) =
            run_regex_case(b"a\nm\nz\nq\n", &[b"/m/+2"], &[&[true]], Options::default());
        positive.expect("positive offset");
        assert_eq!(
            positive_files.get(b"xx00").as_deref(),
            Some(&b"a\nm\nz\n"[..])
        );
        assert_eq!(positive_files.get(b"xx01").as_deref(), Some(&b"q\n"[..]));
        assert_eq!(positive_stdout, b"6\n2\n");
    }

    #[test]
    fn regex_positive_offset_retains_match_and_tolerates_early_eof() {
        let (result, file_system, _) =
            run_with_input(b"Line 1\nLine 2\nLine 3\nLine 4\nLine 5", &[b"/Line 2/1"]);
        result.expect("regex split");
        assert_eq!(
            file_system.get(b"xx00").as_deref(),
            Some(&b"Line 1\nLine 2\n"[..])
        );
        assert_eq!(
            file_system.get(b"xx01").as_deref(),
            Some(&b"Line 3\nLine 4\nLine 5"[..])
        );

        let (early, early_files, _, early_stdout) =
            run_regex_case(b"a\nm", &[b"/m/+20"], &[&[true]], Options::default());
        early.expect("positive offset may reach EOF");
        assert_eq!(early_files.get(b"xx00").as_deref(), Some(&b"a\nm"[..]));
        assert!(early_files.get(b"xx01").is_none());
        assert_eq!(early_stdout, b"3\n");
    }

    #[test]
    fn regex_repetition_and_capacity() {
        let (repeated, files, compiler, stdout) = run_regex_case(
            b"a\nb\nc\nd\nend\n",
            &[b"/x/", b"{2}"],
            &[&[true], &[true], &[true]],
            Options::default(),
        );
        repeated.expect("repeat regex count plus one times");
        assert_eq!(compiler.patterns, vec![b"x".to_vec(); 3]);
        assert_eq!(files.get(b"xx00").as_deref(), Some(&b"a\n"[..]));
        assert_eq!(files.get(b"xx01").as_deref(), Some(&b"b\n"[..]));
        assert_eq!(files.get(b"xx02").as_deref(), Some(&b"c\n"[..]));
        assert_eq!(files.get(b"xx03").as_deref(), Some(&b"d\nend\n"[..]));
        assert_eq!(stdout, b"2\n2\n2\n6\n");

        let scripts = vec![vec![true]; 21];
        let script_refs: Vec<&[bool]> = scripts.iter().map(Vec::as_slice).collect();
        let mut one_digit = Options::default();
        one_digit.sufflen = 1;
        let (limited, limited_files, limited_compiler, _) = run_regex_case(
            b"1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n",
            &[b"/x/", b"{20}"],
            &script_refs,
            one_digit,
        );
        limited.expect("named regex repetition reserves the final suffix");
        assert_eq!(limited_compiler.patterns.len(), 9);
        assert!(limited_files.get(b"xx9").is_some());
        assert!(limited_files.get(b"xx10").is_none());

        let (discarded, percent_files, percent_compiler, percent_stdout) = run_regex_case(
            b"a\nb\nc\nd\nend\n",
            &[b"%x%", b"{2}"],
            &[&[true], &[true], &[true]],
            Options::default(),
        );
        discarded.expect("percent repetitions do not consume named capacity");
        assert_eq!(percent_compiler.patterns.len(), 3);
        assert_eq!(
            percent_files.get(b"xx00").as_deref(),
            Some(&b"d\nend\n"[..])
        );
        assert!(percent_files.get(b"xx01").is_none());
        assert_eq!(percent_stdout, b"6\n");
    }

    #[test]
    fn toomuch_boundary_matrix() {
        assert_eq!(toomuch_position(b"a\nb\nc\n", 1), (4, 19));
        assert_eq!(toomuch_position(b"a\nb\nc\n", 2), (2, 18));
        assert_eq!(toomuch_position(b"a\nb\nc\n", 3), (0, 17));
        assert_eq!(toomuch_position(b"a\nb\nc", 1), (2, 19));

        let mut exact_block = vec![b'x'; super::OVERFLOW_BLOCK_SIZE];
        *exact_block.last_mut().expect("nonempty block") = b'\n';
        assert_eq!(toomuch_position(&exact_block, 1), (0, 19));

        let mut crossing = b"a\n".to_vec();
        crossing.extend(std::iter::repeat_n(b'x', super::OVERFLOW_BLOCK_SIZE - 2));
        crossing.extend_from_slice(b"b\n");
        assert_eq!(crossing.len(), super::OVERFLOW_BLOCK_SIZE + 2);
        assert_eq!(
            toomuch_position(&crossing, 1),
            (2, 19),
            "the exact source scan stops at the prior 8192-byte boundary"
        );
    }

    #[test]
    fn toomuch_finalizes_prior_overflow_at_recorded_offset() {
        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", b"");
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();
        {
            let mut state = Csplit::from_invocation(
                invocation(&[]),
                &mut file_system,
                &mut compiler,
                &mut stdout,
            )
            .expect("create overflow state");
            state.lineno = 3;
            let mut output = state.newfile().expect("create overflow output");
            output.write_c_prefix(b"a\nb\nc\n");
            state.toomuch(Some(output), 1).expect("install overflow");
            assert_eq!(state.truncofs, 4);
            state.toomuch(None, 0).expect("finalize overflow");
        }
        assert_eq!(file_system.get(b"xx00").as_deref(), Some(&b"a\nb\n"[..]));
    }

    #[test]
    fn toomuch_replays_across_an_8192_byte_scan_then_truncates() {
        let mut crossing = b"a\n".to_vec();
        crossing.extend(std::iter::repeat_n(b'x', super::OVERFLOW_BLOCK_SIZE - 2));
        crossing.extend_from_slice(b"b\n");

        let mut file_system = MockFileSystem::default();
        file_system.put(b"in", b"tail\n");
        let mut compiler = MockRegexCompiler::default();
        let mut stdout = Vec::new();
        {
            let mut state = Csplit::from_invocation(
                invocation(&[]),
                &mut file_system,
                &mut compiler,
                &mut stdout,
            )
            .expect("create overflow state");
            state.lineno = 10;
            let mut output = state.newfile().expect("create overflow output");
            output.write_c_prefix(&crossing);

            state
                .toomuch(Some(output), 1)
                .expect("install crossing overflow");
            assert_eq!(state.truncofs, 2);

            let mut replayed = Vec::new();
            while let Some(line) = state.get_line().expect("read replayed chunk") {
                replayed.extend_from_slice(line.c_prefix());
            }
            let mut expected = crossing[2..].to_vec();
            expected.extend_from_slice(b"tail\n");
            assert_eq!(replayed, expected);
            assert_eq!(state.lineno, 15);

            state.toomuch(None, 0).expect("finalize crossing overflow");
        }
        assert_eq!(file_system.get(b"xx00").as_deref(), Some(&b"a\n"[..]));
    }

    #[test]
    fn overflow_truncation_is_deferred_until_finalization() {
        let mut options = Options::default();
        options.kflag = true;
        let (result, files, _, stdout) =
            run_regex_case(b"a\nm\nz\n", &[b"/m/0", b"bogus"], &[&[true]], options);

        assert_eq!(
            render(result.unwrap_err()),
            b"csplit: bogus: unrecognised pattern\n"
        );
        assert_eq!(stdout, b"2\n");
        assert_eq!(
            files.get(b"xx00").as_deref(),
            Some(&b"a\nm\n"[..]),
            "the overflow file is not truncated merely when its split is reported"
        );
        assert!(files.removed.is_empty());
    }

    #[test]
    fn toomuch_error_context_matrix() {
        for operation in [
            MockOperation::Flush,
            MockOperation::Truncate,
            MockOperation::Finish,
        ] {
            let mut file_system = MockFileSystem::default();
            file_system.put(b"in", b"");
            let mut compiler = MockRegexCompiler::default();
            let mut stdout = Vec::new();
            let mut state = Csplit::from_invocation(
                invocation(&[]),
                &mut file_system,
                &mut compiler,
                &mut stdout,
            )
            .expect("create prior-overflow state");
            let mut previous = MockSplitStream::default();
            previous.failure = Some(operation);
            previous.cursor = Cursor::new(b"a\n".to_vec());
            state.overfile = Some(Box::new(previous));
            state.truncofs = 0;

            assert_eq!(
                render(state.toomuch(None, 0).unwrap_err()),
                b"csplit: overflow: mock stream failure\n"
            );
        }

        for (operation, expected) in [
            (
                MockOperation::Position,
                b"csplit: xx00: can't seek\n".as_slice(),
            ),
            (
                MockOperation::Seek,
                b"csplit: xx00: can't seek\n".as_slice(),
            ),
            (
                MockOperation::ReadOverflow,
                b"csplit: can't read overflowed output\n".as_slice(),
            ),
        ] {
            let mut file_system = MockFileSystem::default();
            file_system.put(b"in", b"");
            let mut compiler = MockRegexCompiler::default();
            let mut stdout = Vec::new();
            let mut state = Csplit::from_invocation(
                invocation(&[]),
                &mut file_system,
                &mut compiler,
                &mut stdout,
            )
            .expect("create current-overflow state");
            state.currfile = b"xx00".to_vec();
            let mut output = MockSplitStream::default();
            output.failure = Some(operation);
            output.cursor = Cursor::new(b"a\nb\n".to_vec());
            output.cursor.set_position(4);

            assert_eq!(
                render(state.toomuch(Some(Box::new(output)), 1).unwrap_err()),
                expected
            );
        }
    }
}
