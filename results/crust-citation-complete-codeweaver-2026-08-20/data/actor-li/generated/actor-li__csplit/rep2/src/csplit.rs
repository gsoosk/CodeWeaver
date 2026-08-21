use std::ffi::{OsStr, OsString};
use std::io::{self, Cursor, Read, SeekFrom, Write};
use std::os::unix::ffi::{OsStrExt, OsStringExt};

use crate::bre::{Bre, Matcher};
use crate::cli::{finish_parse, parse_c_long, parse_head, Invocation, ParsedCli, ProgramNames};
use crate::split_io::{CChunk, CLineReader, Runtime, SplitFile, C_BUFSIZ};

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Options {
    pub(crate) prefix: Vec<u8>,
    pub(crate) sufflen: i64,
    pub(crate) sflag: bool,
    pub(crate) kflag: bool,
}

pub(crate) struct Streams<'a> {
    pub(crate) stdin: &'a mut dyn Read,
    pub(crate) stdout: &'a mut dyn Write,
    pub(crate) stderr: &'a mut dyn Write,
}

#[derive(Debug)]
pub(crate) enum DiagnosticPrefix {
    Invocation,
    Program,
}

#[derive(Debug)]
pub(crate) enum Diagnostic {
    Usage,
    Getopt {
        message: Vec<u8>,
        include_usage: bool,
    },
    Message {
        prefix: DiagnosticPrefix,
        argument: Option<Vec<u8>>,
        text: &'static str,
    },
    Os {
        prefix: DiagnosticPrefix,
        context: Vec<u8>,
        source: io::Error,
    },
}

#[derive(Debug)]
pub(crate) struct CsplitError {
    pub(crate) diagnostic: Diagnostic,
}

pub(crate) struct CsplitState<'a> {
    pub(crate) options: Options,
    pub(crate) lineno: i64,
    pub(crate) reps: i64,
    pub(crate) nfiles: i64,
    pub(crate) maxfiles: i64,
    pub(crate) currfile: OsString,
    pub(crate) infn: OsString,
    pub(crate) infile: CLineReader,
    pub(crate) overfile: Option<Box<dyn SplitFile>>,
    pub(crate) truncofs: u64,
    pub(crate) doclean: bool,
    runtime: &'a mut dyn Runtime,
    stdout: &'a mut dyn Write,
}

impl<'a> CsplitState<'a> {
    pub(crate) fn from_parsed(
        parsed: ParsedCli,
        infile: CLineReader,
        runtime: &'a mut dyn Runtime,
        stdout: &'a mut dyn Write,
    ) -> Self {
        let infn = if parsed.input.as_os_str().as_bytes() == b"-" {
            OsString::from("stdin")
        } else {
            parsed.input.clone()
        };
        let doclean = !parsed.options.kflag;
        Self {
            options: parsed.options,
            lineno: 0,
            reps: 0,
            nfiles: 0,
            maxfiles: parsed.maxfiles,
            currfile: OsString::new(),
            infn,
            infile,
            overfile: None,
            truncofs: 0,
            doclean,
            runtime,
            stdout,
        }
    }

    pub(crate) fn newfile(&mut self) -> Result<Box<dyn SplitFile>, CsplitError> {
        let width = self.options.sufflen as usize;
        let suffix = format!("{:0width$}", self.nfiles, width = width);
        let mut path = self.options.prefix.clone();
        path.extend_from_slice(suffix.as_bytes());
        self.currfile = OsString::from_vec(path);

        let file = self
            .runtime
            .create_split(&self.currfile)
            .map_err(|source| {
                self.os_error(self.currfile.as_os_str().as_bytes().to_vec(), source)
            })?;
        self.nfiles += 1;
        Ok(file)
    }

    pub(crate) fn cleanup(&mut self) {
        if !self.doclean {
            return;
        }

        for index in 0..self.nfiles {
            let suffix = format!("{:0width$}", index, width = self.options.sufflen as usize);
            let mut path = self.options.prefix.clone();
            path.extend_from_slice(suffix.as_bytes());
            let path = OsString::from_vec(path);
            let _ = self.runtime.remove_file(&path);
        }
    }

    pub(crate) fn get_line(&mut self) -> Result<Option<CChunk>, CsplitError> {
        let result = self
            .infile
            .get_line(self.overfile.as_deref_mut())
            .map_err(|source| CsplitError {
                diagnostic: Diagnostic::Os {
                    prefix: DiagnosticPrefix::Program,
                    context: self.infn.as_os_str().as_bytes().to_vec(),
                    source,
                },
            })?;
        if result.is_some() {
            self.lineno += 1;
        }
        Ok(result)
    }

    pub(crate) fn toomuch(
        &mut self,
        mut ofp: Option<Box<dyn SplitFile>>,
        n: i64,
    ) -> Result<(), CsplitError> {
        if let Some(previous) = self.overfile.as_deref_mut() {
            previous.flush().map_err(overflow_error)?;
            previous.set_len(self.truncofs).map_err(overflow_error)?;
            previous.finalize().map_err(overflow_error)?;
            self.overfile = None;
        }

        if n == 0 {
            return Ok(());
        }

        let mut ofp = ofp
            .take()
            .expect("a nonzero replay count always has an output file");
        self.lineno -= n;
        let mut remaining = n;
        let mut buffer = [0_u8; C_BUFSIZ];
        let (nread, index) = loop {
            let current = ofp.seek(SeekFrom::Current(0)).map_err(|_| {
                self.message(
                    Some(self.currfile.as_os_str().as_bytes().to_vec()),
                    "can't seek",
                )
            })?;
            if current < C_BUFSIZ as u64 {
                ofp.seek(SeekFrom::Start(0)).map_err(|_| {
                    self.message(
                        Some(self.currfile.as_os_str().as_bytes().to_vec()),
                        "can't seek",
                    )
                })?;
            } else {
                ofp.seek(SeekFrom::Current(-(C_BUFSIZ as i64)))
                    .map_err(|_| {
                        self.message(
                            Some(self.currfile.as_os_str().as_bytes().to_vec()),
                            "can't seek",
                        )
                    })?;
            }
            let block_start = ofp.seek(SeekFrom::Current(0)).map_err(|_| {
                self.message(
                    Some(self.currfile.as_os_str().as_bytes().to_vec()),
                    "can't seek",
                )
            })?;

            let mut nread = 0;
            while nread < buffer.len() {
                match ofp.read(&mut buffer[nread..]) {
                    Ok(0) => break,
                    Ok(count) => nread += count,
                    Err(source) if source.kind() == io::ErrorKind::Interrupted => continue,
                    Err(_) => break,
                }
            }
            if nread == 0 {
                return Err(self.message(None, "can't read overflowed output"));
            }
            ofp.seek(SeekFrom::Current(-(nread as i64)))
                .map_err(|source| {
                    self.os_error(self.currfile.as_os_str().as_bytes().to_vec(), source)
                })?;

            let mut index = 1;
            while index <= nread {
                if buffer[nread - index] == b'\n' {
                    let before = remaining;
                    remaining -= 1;
                    if before == 0 {
                        break;
                    }
                }
                index += 1;
            }

            if block_start == 0 || remaining <= 0 {
                break (nread, index);
            }
        };

        let forward = nread as i64 - index as i64 + 1;
        ofp.seek(SeekFrom::Current(forward)).map_err(|source| {
            self.os_error(self.currfile.as_os_str().as_bytes().to_vec(), source)
        })?;
        self.truncofs = ofp.seek(SeekFrom::Current(0)).map_err(|source| {
            self.os_error(self.currfile.as_os_str().as_bytes().to_vec(), source)
        })?;
        self.overfile = Some(ofp);
        Ok(())
    }

    pub(crate) fn do_rexp(&mut self, expr: &[u8]) -> Result<(), CsplitError> {
        let delimiter = expr[0];
        let delimiter_index = expr
            .iter()
            .rposition(|byte| *byte == delimiter)
            .unwrap_or(0);
        if delimiter_index > 0 && expr[delimiter_index - 1] == b'\\' {
            return Err(self.message(
                Some(expr.to_vec()),
                if delimiter == b'/' {
                    "missing trailing /"
                } else {
                    "missing trailing %"
                },
            ));
        }

        let regex_bytes = if delimiter_index == 0 {
            &[][..]
        } else {
            &expr[1..delimiter_index]
        };
        let offset_bytes = &expr[delimiter_index + 1..];
        let offset = if offset_bytes.is_empty() {
            0
        } else {
            let parsed = parse_c_long(offset_bytes);
            if parsed.end != offset_bytes.len() || parsed.overflowed {
                return Err(self.message(Some(offset_bytes.to_vec()), "bad offset"));
            }
            parsed.value
        };

        let matcher = Bre::compile(regex_bytes)
            .map_err(|_| self.message(Some(regex_bytes.to_vec()), "bad regular expression"))?;
        let mut output = if delimiter == b'/' {
            self.newfile()?
        } else {
            self.runtime.create_temp().map_err(|source| CsplitError {
                diagnostic: Diagnostic::Os {
                    prefix: DiagnosticPrefix::Program,
                    context: b"tmpfile".to_vec(),
                    source,
                },
            })?
        };

        let mut first = true;
        let matched = loop {
            let Some(chunk) = self.get_line()? else {
                break false;
            };
            output.write_ignored(&chunk.visible);
            if !first
                && matcher
                    .is_match(&chunk.visible)
                    .map_err(|_| self.message(Some(regex_bytes.to_vec()), "no match"))?
            {
                break true;
            }
            first = false;
        };

        if !matched {
            self.toomuch(None, 0)?;
            return Err(self.message(Some(regex_bytes.to_vec()), "no match"));
        }

        let written = if offset <= 0 {
            let replay = offset
                .checked_neg()
                .and_then(|value| value.checked_add(1))
                .ok_or_else(|| self.message(Some(offset_bytes.to_vec()), "bad offset"))?;
            self.toomuch(Some(output), replay)?;
            self.truncofs
        } else {
            let mut remaining = offset;
            remaining -= 1;
            while remaining > 0 {
                let Some(chunk) = self.get_line()? else {
                    break;
                };
                output.write_ignored(&chunk.visible);
                remaining -= 1;
            }
            self.toomuch(None, 0)?;
            let written = output.seek(SeekFrom::Current(0)).map_err(|source| {
                self.os_error(self.currfile.as_os_str().as_bytes().to_vec(), source)
            })?;
            output.finalize().map_err(|source| {
                self.os_error(self.currfile.as_os_str().as_bytes().to_vec(), source)
            })?;
            written
        };

        if !self.options.sflag && delimiter == b'/' {
            let _ = writeln!(self.stdout, "{written}");
        }
        Ok(())
    }

    pub(crate) fn do_lineno(&mut self, expr: &[u8]) -> Result<(), CsplitError> {
        let parsed = parse_c_long(expr);
        if parsed.value <= 0 || parsed.end != expr.len() || parsed.overflowed {
            return Err(self.message(Some(expr.to_vec()), "bad line number"));
        }
        let target = parsed.value;
        let mut lastline = target;
        if lastline <= self.lineno {
            return Err(self.message(Some(expr.to_vec()), "can't go backwards"));
        }

        while self.nfiles < self.maxfiles - 1 {
            let mut output = self.newfile()?;
            while self.lineno + 1 != lastline {
                let Some(chunk) = self.get_line()? else {
                    return Err(
                        self.message(Some(lastline.to_string().into_bytes()), "out of range")
                    );
                };
                output.write_ignored(&chunk.visible);
            }
            let written = output.seek(SeekFrom::Current(0)).map_err(|source| {
                self.os_error(self.currfile.as_os_str().as_bytes().to_vec(), source)
            })?;
            if !self.options.sflag {
                let _ = writeln!(self.stdout, "{written}");
            }
            output.finalize().map_err(|source| {
                self.os_error(self.currfile.as_os_str().as_bytes().to_vec(), source)
            })?;

            let previous_reps = self.reps;
            self.reps -= 1;
            if previous_reps == 0 {
                break;
            }
            lastline = lastline
                .checked_add(target)
                .ok_or_else(|| self.message(Some(expr.to_vec()), "bad line number"))?;
        }
        Ok(())
    }

    pub(crate) fn copy_remainder(&mut self) -> Result<(), CsplitError> {
        if self.infile.original_eof() {
            return Ok(());
        }

        let mut output = self.newfile()?;
        while let Some(chunk) = self.get_line()? {
            output.write_ignored(&chunk.visible);
        }
        let written = output.seek(SeekFrom::Current(0)).map_err(|source| {
            self.os_error(self.currfile.as_os_str().as_bytes().to_vec(), source)
        })?;
        if !self.options.sflag {
            let _ = writeln!(self.stdout, "{written}");
        }
        output.finalize().map_err(|source| {
            self.os_error(self.currfile.as_os_str().as_bytes().to_vec(), source)
        })?;
        Ok(())
    }

    pub(crate) fn execute(
        &mut self,
        patterns: &[crate::cli::PatternOperand],
    ) -> Result<(), CsplitError> {
        for pattern in patterns {
            if self.nfiles >= self.maxfiles - 1 {
                break;
            }
            self.reps = pattern.reps;
            match pattern.expr.first() {
                Some(b'/' | b'%') => loop {
                    self.do_rexp(&pattern.expr)?;
                    let previous_reps = self.reps;
                    self.reps -= 1;
                    if previous_reps == 0 || self.nfiles >= self.maxfiles - 1 {
                        break;
                    }
                },
                Some(byte) if byte.is_ascii_digit() => self.do_lineno(&pattern.expr)?,
                _ => return Err(self.message(Some(pattern.expr.clone()), "unrecognised pattern")),
            }
        }

        self.copy_remainder()?;
        self.toomuch(None, 0)?;
        self.doclean = false;
        Ok(())
    }

    fn message(&self, argument: Option<Vec<u8>>, text: &'static str) -> CsplitError {
        CsplitError {
            diagnostic: Diagnostic::Message {
                prefix: DiagnosticPrefix::Program,
                argument,
                text,
            },
        }
    }

    fn os_error(&self, context: Vec<u8>, source: io::Error) -> CsplitError {
        CsplitError {
            diagnostic: Diagnostic::Os {
                prefix: DiagnosticPrefix::Program,
                context,
                source,
            },
        }
    }
}

fn overflow_error(source: io::Error) -> CsplitError {
    CsplitError {
        diagnostic: Diagnostic::Os {
            prefix: DiagnosticPrefix::Program,
            context: b"overflow".to_vec(),
            source,
        },
    }
}

pub(crate) fn run(
    invocation: &Invocation,
    streams: &mut Streams<'_>,
    runtime: &mut dyn Runtime,
) -> Result<(), CsplitError> {
    let head = parse_head(invocation)?;
    let input_name = head.input.clone();
    let (parsed, input): (ParsedCli, Box<dyn Read>) = if input_name.as_os_str().as_bytes() == b"-" {
        let parsed = finish_parse(head)?;
        let mut bytes = Vec::new();
        streams
            .stdin
            .read_to_end(&mut bytes)
            .map_err(|source| CsplitError {
                diagnostic: Diagnostic::Os {
                    prefix: DiagnosticPrefix::Program,
                    context: b"stdin".to_vec(),
                    source,
                },
            })?;
        (parsed, Box::new(Cursor::new(bytes)))
    } else {
        let input = runtime
            .open_input(&input_name)
            .map_err(|source| CsplitError {
                diagnostic: Diagnostic::Os {
                    prefix: DiagnosticPrefix::Program,
                    context: input_name.as_os_str().as_bytes().to_vec(),
                    source,
                },
            })?;
        let parsed = finish_parse(head)?;
        (parsed, input)
    };
    let patterns = parsed.patterns.clone();

    let reader = CLineReader::new(input);
    let mut state = CsplitState::from_parsed(parsed, reader, runtime, streams.stdout);
    let result = state.execute(&patterns);
    if result.is_err() {
        state.cleanup();
    }
    result
}

pub(crate) fn render_diagnostic(
    error: &CsplitError,
    names: &ProgramNames,
    stderr: &mut dyn Write,
) -> io::Result<()> {
    match &error.diagnostic {
        Diagnostic::Usage => stderr.write_all(&crate::cli::usage(&names.basename)),
        Diagnostic::Getopt {
            message,
            include_usage,
        } => {
            write_prefixed(stderr, &names.invocation, None, message)?;
            if *include_usage {
                stderr.write_all(&crate::cli::usage(&names.basename))?;
            }
            Ok(())
        }
        Diagnostic::Message {
            prefix,
            argument,
            text,
        } => {
            let name = diagnostic_name(names, prefix);
            write_prefixed(stderr, name, argument.as_deref(), text.as_bytes())
        }
        Diagnostic::Os {
            prefix,
            context,
            source,
        } => {
            let name = diagnostic_name(names, prefix);
            let os_text = source.to_string();
            let mut message = context.clone();
            message.extend_from_slice(b": ");
            message.extend_from_slice(os_text.as_bytes());
            write_prefixed(stderr, name, None, &message)
        }
    }
}

fn diagnostic_name<'a>(names: &'a ProgramNames, prefix: &DiagnosticPrefix) -> &'a OsStr {
    match prefix {
        DiagnosticPrefix::Invocation => &names.invocation,
        DiagnosticPrefix::Program => &names.basename,
    }
}

fn write_prefixed(
    stderr: &mut dyn Write,
    name: &OsStr,
    argument: Option<&[u8]>,
    message: &[u8],
) -> io::Result<()> {
    stderr.write_all(name.as_bytes())?;
    stderr.write_all(b": ")?;
    if let Some(argument) = argument {
        stderr.write_all(argument)?;
        stderr.write_all(b": ")?;
    }
    stderr.write_all(message)?;
    stderr.write_all(b"\n")
}

#[cfg(test)]
#[path = "csplit/tests.rs"]
mod tests;
