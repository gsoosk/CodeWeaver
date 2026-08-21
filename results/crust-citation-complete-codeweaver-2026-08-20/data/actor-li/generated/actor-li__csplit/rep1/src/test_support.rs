use std::cell::RefCell;
use std::collections::{BTreeMap, VecDeque};
use std::ffi::OsStr;
use std::io::{self, Cursor, Read, Seek, SeekFrom, Write};
use std::os::unix::ffi::OsStrExt;
use std::rc::Rc;

use crate::boundary::{
    ChunkRead, FileSystem, InputStream, LineChunk, RegexCompileError, RegexCompiler, RegexMatcher,
    SplitStream,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MockOperation {
    OpenInput,
    Stdin,
    OpenOutput,
    Temporary,
    Remove,
    ReadInput,
    Write,
    Position,
    Seek,
    ReadOverflow,
    Flush,
    Truncate,
    Finish,
    CompileRegex,
    MatchRegex,
}

type SharedFiles = Rc<RefCell<BTreeMap<Vec<u8>, Vec<u8>>>>;

#[derive(Debug, Default)]
pub struct MockFileSystem {
    pub files: SharedFiles,
    pub stdin_bytes: Vec<u8>,
    pub removed: Vec<Vec<u8>>,
    pub calls: Vec<MockOperation>,
    pub failure: Option<MockOperation>,
    pub stream_failure: Option<MockOperation>,
}

impl MockFileSystem {
    pub fn put(&mut self, path: &[u8], contents: &[u8]) {
        self.files
            .borrow_mut()
            .insert(path.to_vec(), contents.to_vec());
    }

    pub fn get(&self, path: &[u8]) -> Option<Vec<u8>> {
        self.files.borrow().get(path).cloned()
    }

    fn fails(&self, operation: MockOperation) -> io::Result<()> {
        if self.failure == Some(operation) {
            Err(io::Error::other("mock operation failed"))
        } else {
            Ok(())
        }
    }
}

impl FileSystem for MockFileSystem {
    fn open_input(&mut self, path: &OsStr) -> io::Result<Box<dyn InputStream>> {
        self.calls.push(MockOperation::OpenInput);
        self.fails(MockOperation::OpenInput)?;
        let path = path.as_bytes();
        let bytes = self
            .files
            .borrow()
            .get(path)
            .cloned()
            .ok_or_else(|| io::Error::from_raw_os_error(2))?;
        Ok(Box::new(MockInputStream::from_bytes(bytes)))
    }

    fn stdin(&mut self) -> io::Result<Box<dyn InputStream>> {
        self.calls.push(MockOperation::Stdin);
        self.fails(MockOperation::Stdin)?;
        Ok(Box::new(MockInputStream::from_bytes(
            self.stdin_bytes.clone(),
        )))
    }

    fn open_output(&mut self, path: &OsStr) -> io::Result<Box<dyn SplitStream>> {
        self.calls.push(MockOperation::OpenOutput);
        self.fails(MockOperation::OpenOutput)?;
        let path = path.as_bytes().to_vec();
        self.files.borrow_mut().insert(path.clone(), Vec::new());
        Ok(Box::new(MockSplitStream::named(
            self.files.clone(),
            path,
            self.stream_failure,
        )))
    }

    fn temporary(&mut self) -> io::Result<Box<dyn SplitStream>> {
        self.calls.push(MockOperation::Temporary);
        self.fails(MockOperation::Temporary)?;
        Ok(Box::new(MockSplitStream {
            cursor: Cursor::new(Vec::new()),
            calls: Vec::new(),
            failure: self.stream_failure,
            scripted_read_errors: VecDeque::new(),
            sticky_write_error: false,
            files: None,
            path: None,
        }))
    }

    fn remove(&mut self, path: &OsStr) -> io::Result<()> {
        self.calls.push(MockOperation::Remove);
        self.removed.push(path.as_bytes().to_vec());
        self.fails(MockOperation::Remove)?;
        self.files.borrow_mut().remove(path.as_bytes());
        Ok(())
    }
}

#[derive(Debug, Default)]
pub struct MockInputStream {
    pub reads: VecDeque<ChunkRead>,
    pub bytes: Vec<u8>,
    pub position: usize,
    pub eof: bool,
    pub calls: Vec<MockOperation>,
    pub failure: Option<MockOperation>,
}

impl MockInputStream {
    pub fn from_bytes(bytes: Vec<u8>) -> Self {
        Self {
            bytes,
            ..Self::default()
        }
    }
}

impl InputStream for MockInputStream {
    fn read_chunk(&mut self, capacity: usize) -> ChunkRead {
        self.calls.push(MockOperation::ReadInput);
        if self.failure == Some(MockOperation::ReadInput) {
            return ChunkRead {
                chunk: None,
                eof: false,
                error: Some(io::Error::other("mock input failure")),
            };
        }
        if let Some(read) = self.reads.pop_front() {
            self.eof = read.eof;
            return read;
        }
        if self.position >= self.bytes.len() {
            self.eof = true;
            return ChunkRead {
                chunk: None,
                eof: true,
                error: None,
            };
        }

        let limit = capacity.saturating_sub(1);
        let available = &self.bytes[self.position..];
        let take = available.len().min(limit);
        let newline = available[..take].iter().position(|byte| *byte == b'\n');
        let amount = newline.map_or(take, |index| index + 1);
        let consumed = available[..amount].to_vec();
        self.position += amount;
        if newline.is_none() && self.position == self.bytes.len() && amount < limit {
            self.eof = true;
        }

        ChunkRead {
            chunk: Some(LineChunk { consumed }),
            eof: self.eof,
            error: None,
        }
    }

    fn eof(&self) -> bool {
        self.eof
    }
}

#[derive(Debug, Default)]
pub struct MockSplitStream {
    pub cursor: Cursor<Vec<u8>>,
    pub calls: Vec<MockOperation>,
    pub failure: Option<MockOperation>,
    pub scripted_read_errors: VecDeque<Option<io::Error>>,
    pub sticky_write_error: bool,
    files: Option<SharedFiles>,
    path: Option<Vec<u8>>,
}

impl MockSplitStream {
    fn named(files: SharedFiles, path: Vec<u8>, failure: Option<MockOperation>) -> Self {
        Self {
            cursor: Cursor::new(Vec::new()),
            calls: Vec::new(),
            files: Some(files),
            path: Some(path),
            failure,
            scripted_read_errors: VecDeque::new(),
            sticky_write_error: false,
        }
    }

    fn fails(&self, operation: MockOperation) -> io::Result<()> {
        if self.failure == Some(operation) {
            Err(io::Error::other("mock stream failure"))
        } else {
            Ok(())
        }
    }

    fn commit(&self) {
        if let (Some(files), Some(path)) = (&self.files, &self.path) {
            files
                .borrow_mut()
                .insert(path.clone(), self.cursor.get_ref().clone());
        }
    }
}

impl Drop for MockSplitStream {
    fn drop(&mut self) {
        self.commit();
    }
}

impl SplitStream for MockSplitStream {
    fn write_c_prefix(&mut self, bytes: &[u8]) {
        self.calls.push(MockOperation::Write);
        if self.failure == Some(MockOperation::Write) {
            self.sticky_write_error = true;
            return;
        }
        let end = bytes
            .iter()
            .position(|byte| *byte == 0)
            .unwrap_or(bytes.len());
        if self.cursor.write_all(&bytes[..end]).is_err() {
            self.sticky_write_error = true;
        }
        self.commit();
    }

    fn position(&mut self) -> io::Result<u64> {
        self.calls.push(MockOperation::Position);
        self.fails(MockOperation::Position)?;
        Ok(self.cursor.position())
    }

    fn seek(&mut self, from: SeekFrom) -> io::Result<u64> {
        self.calls.push(MockOperation::Seek);
        self.fails(MockOperation::Seek)?;
        self.cursor.seek(from)
    }

    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        self.calls.push(MockOperation::ReadOverflow);
        if let Some(Some(source)) = self.scripted_read_errors.pop_front() {
            return Err(source);
        }
        self.fails(MockOperation::ReadOverflow)?;
        self.cursor.read(buffer)
    }

    fn flush_checked(&mut self) -> io::Result<()> {
        self.calls.push(MockOperation::Flush);
        if self.sticky_write_error {
            return Err(io::Error::other("mock sticky write failure"));
        }
        self.fails(MockOperation::Flush)
    }

    fn set_len(&mut self, len: u64) -> io::Result<()> {
        self.calls.push(MockOperation::Truncate);
        self.fails(MockOperation::Truncate)?;
        let len = usize::try_from(len).map_err(|_| io::Error::other("mock length overflow"))?;
        self.cursor.get_mut().resize(len, 0);
        self.commit();
        Ok(())
    }

    fn finish(mut self: Box<Self>) -> io::Result<()> {
        self.calls.push(MockOperation::Finish);
        self.commit();
        if self.sticky_write_error {
            return Err(io::Error::other("mock sticky write failure"));
        }
        self.fails(MockOperation::Finish)
    }
}

#[derive(Debug, Default)]
pub struct MockRegexCompiler {
    pub matches: VecDeque<bool>,
    pub match_sequences: VecDeque<VecDeque<bool>>,
    pub patterns: Vec<Vec<u8>>,
    pub matched_subjects: Rc<RefCell<Vec<Vec<u8>>>>,
    pub calls: Vec<MockOperation>,
    pub failure: Option<MockOperation>,
}

impl RegexCompiler for MockRegexCompiler {
    fn compile(&mut self, pattern: &[u8]) -> Result<Box<dyn RegexMatcher>, RegexCompileError> {
        self.calls.push(MockOperation::CompileRegex);
        self.patterns.push(pattern.to_vec());
        if self.failure == Some(MockOperation::CompileRegex) {
            return Err(RegexCompileError);
        }
        let matches = self
            .match_sequences
            .pop_front()
            .unwrap_or_else(|| std::mem::take(&mut self.matches));
        Ok(Box::new(MockRegexMatcher {
            matches,
            matched_subjects: self.matched_subjects.clone(),
            failure: self.failure,
            calls: Vec::new(),
        }))
    }
}

#[derive(Debug, Default)]
pub struct MockRegexMatcher {
    pub matches: VecDeque<bool>,
    pub matched_subjects: Rc<RefCell<Vec<Vec<u8>>>>,
    pub calls: Vec<MockOperation>,
    pub failure: Option<MockOperation>,
}

impl RegexMatcher for MockRegexMatcher {
    fn is_match(&mut self, subject: &[u8]) -> bool {
        self.calls.push(MockOperation::MatchRegex);
        self.matched_subjects.borrow_mut().push(subject.to_vec());
        if self.failure == Some(MockOperation::MatchRegex) {
            return false;
        }
        self.matches.pop_front().unwrap_or(false)
    }
}

#[derive(Debug, Default)]
pub struct MockWriter {
    pub bytes: Vec<u8>,
    pub fail: bool,
}

impl Write for MockWriter {
    fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
        if self.fail {
            return Err(io::Error::other("mock writer failure"));
        }
        self.bytes.extend_from_slice(buffer);
        Ok(buffer.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        if self.fail {
            Err(io::Error::other("mock writer failure"))
        } else {
            Ok(())
        }
    }
}
