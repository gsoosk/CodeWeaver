use std::borrow::Cow;
use std::env;
use std::ffi::{OsStr, OsString};
use std::fs::File;
use std::io::{self, Read};

#[cfg(unix)]
use std::os::unix::ffi::OsStrExt;

pub(crate) trait FileSource {
    fn open(&self, path: &OsStr) -> io::Result<Box<dyn Read>>;
}

pub(crate) struct RealFileSource;

impl FileSource for RealFileSource {
    fn open(&self, path: &OsStr) -> io::Result<Box<dyn Read>> {
        File::open(path).map(|file| Box::new(file) as Box<dyn Read>)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ProcessContext {
    pub(crate) argv: Vec<OsString>,
    pub(crate) posixly_correct: bool,
    pub(crate) lc_all: Option<OsString>,
    pub(crate) lc_ctype: Option<OsString>,
    pub(crate) lang: Option<OsString>,
}

impl ProcessContext {
    pub(crate) fn capture() -> Self {
        Self {
            argv: env::args_os().collect(),
            posixly_correct: env::var_os("POSIXLY_CORRECT").is_some(),
            lc_all: env::var_os("LC_ALL"),
            lc_ctype: env::var_os("LC_CTYPE"),
            lang: env::var_os("LANG"),
        }
    }

    #[cfg(test)]
    pub(crate) fn fixture(argv: Vec<OsString>) -> Self {
        Self {
            argv,
            posixly_correct: false,
            lc_all: None,
            lc_ctype: None,
            lang: None,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ProgramNames {
    pub(crate) raw_argv0: Vec<u8>,
    pub(crate) progname: Vec<u8>,
}

pub(crate) fn os_str_bytes(value: &OsStr) -> Cow<'_, [u8]> {
    #[cfg(unix)]
    {
        Cow::Borrowed(value.as_bytes())
    }
    #[cfg(not(unix))]
    {
        Cow::Owned(value.to_string_lossy().into_owned().into_bytes())
    }
}

pub(crate) fn program_names(context: &ProcessContext) -> ProgramNames {
    let raw_argv0 = context
        .argv
        .first()
        .map(|value| os_str_bytes(value).into_owned())
        .unwrap_or_else(|| b"fmt".to_vec());
    let progname = raw_argv0
        .iter()
        .rposition(|byte| *byte == b'/')
        .map_or_else(
            || raw_argv0.clone(),
            |index| raw_argv0[index + 1..].to_vec(),
        );

    ProgramNames {
        raw_argv0,
        progname,
    }
}

pub(crate) fn os_error_text(error: &io::Error) -> Vec<u8> {
    let mut text = error.to_string().into_bytes();
    if let Some(code) = error.raw_os_error() {
        let suffix = format!(" (os error {code})").into_bytes();
        if text.ends_with(&suffix) {
            text.truncate(text.len() - suffix.len());
        }
    }
    text
}

#[cfg(test)]
mod test_support {
    use super::FileSource;
    use std::cell::RefCell;
    use std::collections::BTreeMap;
    use std::ffi::{OsStr, OsString};
    use std::io::{self, Cursor, Read, Write};

    #[derive(Clone, Debug)]
    enum MockEntry {
        Bytes(Vec<u8>),
        RawOsError(i32),
        ReadError {
            bytes: Vec<u8>,
            fail_after: usize,
            raw_os_error: i32,
        },
    }

    #[derive(Debug, Default)]
    pub(crate) struct MockFileSource {
        entries: RefCell<BTreeMap<OsString, MockEntry>>,
        open_order: RefCell<Vec<OsString>>,
    }

    impl MockFileSource {
        pub(crate) fn new() -> Self {
            Self::default()
        }

        pub(crate) fn insert_file(&self, path: OsString, bytes: Vec<u8>) {
            self.entries
                .borrow_mut()
                .insert(path, MockEntry::Bytes(bytes));
        }

        pub(crate) fn insert_error(&self, path: OsString, raw_os_error: i32) {
            self.entries
                .borrow_mut()
                .insert(path, MockEntry::RawOsError(raw_os_error));
        }

        pub(crate) fn insert_read_error(
            &self,
            path: OsString,
            bytes: Vec<u8>,
            fail_after: usize,
            raw_os_error: i32,
        ) {
            self.entries.borrow_mut().insert(
                path,
                MockEntry::ReadError {
                    bytes,
                    fail_after,
                    raw_os_error,
                },
            );
        }

        pub(crate) fn open_order(&self) -> Vec<OsString> {
            self.open_order.borrow().clone()
        }
    }

    impl FileSource for MockFileSource {
        fn open(&self, path: &OsStr) -> io::Result<Box<dyn Read>> {
            self.open_order.borrow_mut().push(path.to_os_string());
            match self.entries.borrow().get(&path.to_os_string()).cloned() {
                Some(MockEntry::Bytes(bytes)) => Ok(Box::new(Cursor::new(bytes))),
                Some(MockEntry::RawOsError(code)) => Err(io::Error::from_raw_os_error(code)),
                Some(MockEntry::ReadError {
                    bytes,
                    fail_after,
                    raw_os_error,
                }) => Ok(Box::new(FaultingReader::new(
                    bytes,
                    fail_after,
                    raw_os_error,
                ))),
                None => Err(io::Error::from_raw_os_error(2)),
            }
        }
    }

    #[derive(Debug)]
    pub(crate) struct FaultingReader {
        bytes: Vec<u8>,
        position: usize,
        fail_after: usize,
        raw_os_error: i32,
        failed: bool,
    }

    impl FaultingReader {
        pub(crate) fn new(bytes: Vec<u8>, fail_after: usize, raw_os_error: i32) -> Self {
            Self {
                bytes,
                position: 0,
                fail_after,
                raw_os_error,
                failed: false,
            }
        }
    }

    impl Read for FaultingReader {
        fn read(&mut self, output: &mut [u8]) -> io::Result<usize> {
            if output.is_empty() {
                return Ok(0);
            }
            if !self.failed && self.position >= self.fail_after {
                self.failed = true;
                self.position = self.bytes.len();
                return Err(io::Error::from_raw_os_error(self.raw_os_error));
            }
            if self.position >= self.bytes.len() {
                return Ok(0);
            }

            let end = self
                .position
                .saturating_add(output.len())
                .min(self.fail_after)
                .min(self.bytes.len());
            let count = end - self.position;
            output[..count].copy_from_slice(&self.bytes[self.position..end]);
            self.position = end;
            Ok(count)
        }
    }

    #[derive(Debug)]
    pub(crate) struct FaultingWriter {
        bytes: Vec<u8>,
        fail_after: usize,
        raw_os_error: i32,
    }

    impl FaultingWriter {
        pub(crate) fn new(fail_after: usize, raw_os_error: i32) -> Self {
            Self {
                bytes: Vec::new(),
                fail_after,
                raw_os_error,
            }
        }

        pub(crate) fn bytes(&self) -> &[u8] {
            &self.bytes
        }
    }

    impl Write for FaultingWriter {
        fn write(&mut self, input: &[u8]) -> io::Result<usize> {
            if input.is_empty() {
                return Ok(0);
            }
            if self.bytes.len() >= self.fail_after {
                return Err(io::Error::from_raw_os_error(self.raw_os_error));
            }
            let count = input
                .len()
                .min(self.fail_after.saturating_sub(self.bytes.len()));
            self.bytes.extend_from_slice(&input[..count]);
            Ok(count)
        }

        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }
}

#[cfg(test)]
pub(crate) use test_support::{FaultingReader, FaultingWriter, MockFileSource};

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::OsString;
    use std::io::{self, Read, Write};

    #[cfg(unix)]
    use std::os::unix::ffi::OsStringExt;

    #[test]
    fn process_context_fixture_does_not_mutate_environment() {
        let argv = vec![OsString::from("fmt"), OsString::from("-c")];
        let context = ProcessContext::fixture(argv.clone());

        assert_eq!(context.argv, argv);
        assert!(!context.posixly_correct);
        assert_eq!(context.lc_all, None);
        assert_eq!(context.lc_ctype, None);
        assert_eq!(context.lang, None);
    }

    #[cfg(unix)]
    #[test]
    fn program_names_preserve_raw_argv0_and_basename() {
        let raw_argv0 = b"relative/path/f\xffmt".to_vec();
        let context = ProcessContext::fixture(vec![OsString::from_vec(raw_argv0.clone())]);

        assert_eq!(
            program_names(&context),
            ProgramNames {
                raw_argv0,
                progname: b"f\xffmt".to_vec(),
            }
        );
    }

    #[test]
    fn program_names_fall_back_to_fmt_without_argv0() {
        let context = ProcessContext::fixture(Vec::new());

        assert_eq!(
            program_names(&context),
            ProgramNames {
                raw_argv0: b"fmt".to_vec(),
                progname: b"fmt".to_vec(),
            }
        );
    }

    #[test]
    fn os_error_text_removes_rust_numeric_suffix() {
        let error = io::Error::from_raw_os_error(2);

        assert_eq!(os_error_text(&error), b"No such file or directory");
    }

    #[test]
    fn mock_file_source_returns_raw_bytes() {
        #[cfg(unix)]
        let path = OsString::from_vec(b"raw-\xff-name".to_vec());
        #[cfg(not(unix))]
        let path = OsString::from("raw-name");
        let expected = b"\0raw\xffbytes\n".to_vec();
        let files = MockFileSource::new();
        files.insert_file(path.clone(), expected.clone());

        let mut stream = files.open(&path).unwrap();
        let mut actual = Vec::new();
        stream.read_to_end(&mut actual).unwrap();

        assert_eq!(actual, expected);
    }

    #[test]
    fn mock_file_source_injects_raw_os_errors() {
        let path = OsString::from("denied");
        let files = MockFileSource::new();
        files.insert_error(path.clone(), 13);

        let error = match files.open(&path) {
            Ok(_) => panic!("injected open unexpectedly succeeded"),
            Err(error) => error,
        };

        assert_eq!(error.raw_os_error(), Some(13));
    }

    #[test]
    fn mock_file_source_records_open_order() {
        let first = OsString::from("first");
        let missing = OsString::from("missing");
        let last = OsString::from("last");
        let files = MockFileSource::new();
        files.insert_file(first.clone(), Vec::new());
        files.insert_error(last.clone(), 5);

        assert!(files.open(&first).is_ok());
        assert!(files.open(&missing).is_err());
        assert!(files.open(&last).is_err());
        assert_eq!(files.open_order(), [first, missing, last]);
    }

    #[test]
    fn faulting_reader_returns_partial_bytes_then_one_error() {
        let mut reader = FaultingReader::new(b"abcdef".to_vec(), 3, 5);
        let mut empty = [];
        assert_eq!(reader.read(&mut empty).unwrap(), 0);

        let mut output = [0; 8];
        let count = reader.read(&mut output).unwrap();
        assert_eq!(&output[..count], b"abc");

        let error = reader.read(&mut output).unwrap_err();
        assert_eq!(error.raw_os_error(), Some(5));
        assert_eq!(reader.read(&mut output).unwrap(), 0);

        let mut past_eof = FaultingReader::new(b"xy".to_vec(), 3, 5);
        assert_eq!(past_eof.read(&mut output).unwrap(), 2);
        assert_eq!(past_eof.read(&mut output).unwrap(), 0);
    }

    #[test]
    fn faulting_writer_stops_at_selected_byte_count() {
        let mut writer = FaultingWriter::new(4, 28);

        let error = writer.write_all(b"abcdef").unwrap_err();
        assert_eq!(error.raw_os_error(), Some(28));
        assert_eq!(writer.bytes(), b"abcd");
        assert_eq!(writer.write(&[]).unwrap(), 0);
        assert_eq!(writer.write(b"x").unwrap_err().raw_os_error(), Some(28));
        assert_eq!(writer.bytes(), b"abcd");
    }
}
