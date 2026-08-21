use std::ffi::OsStr;
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::os::unix::fs::OpenOptionsExt;
use std::sync::atomic::{AtomicU64, Ordering};

pub(crate) const LINE_MAX: usize = 2048;
pub(crate) const CHUNK_MAX: usize = LINE_MAX - 1;
pub(crate) const C_BUFSIZ: usize = 8192;

pub(crate) trait SplitFile: Read + Write + Seek {
    fn write_ignored(&mut self, buffer: &[u8]);
    fn set_len(&mut self, _len: u64) -> io::Result<()>;
    fn finalize(&mut self) -> io::Result<()>;
}

pub(crate) trait Runtime {
    fn open_input(&mut self, _path: &OsStr) -> io::Result<Box<dyn Read>>;
    fn create_split(&mut self, _path: &OsStr) -> io::Result<Box<dyn SplitFile>>;
    fn create_temp(&mut self) -> io::Result<Box<dyn SplitFile>>;
    fn remove_file(&mut self, _path: &OsStr) -> io::Result<()>;
}

#[derive(Debug, Default)]
pub(crate) struct RealRuntime;

#[derive(Debug)]
struct RealSplitFile {
    file: File,
    deferred_write_error: Option<DeferredIoError>,
}

#[derive(Debug, Clone)]
pub(crate) struct DeferredIoError {
    kind: io::ErrorKind,
    raw_os_error: Option<i32>,
    message: String,
}

impl DeferredIoError {
    fn capture(error: io::Error) -> Self {
        Self {
            kind: error.kind(),
            raw_os_error: error.raw_os_error(),
            message: error.to_string(),
        }
    }

    fn to_error(&self) -> io::Error {
        match self.raw_os_error {
            Some(code) => io::Error::from_raw_os_error(code),
            None => io::Error::new(self.kind, self.message.clone()),
        }
    }
}

impl RealSplitFile {
    fn deferred_result(&self) -> io::Result<()> {
        match &self.deferred_write_error {
            Some(error) => Err(error.to_error()),
            None => Ok(()),
        }
    }
}

impl Read for RealSplitFile {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        self.file.read(buffer)
    }
}

impl Write for RealSplitFile {
    fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
        self.deferred_result()?;
        self.file.write(buffer)
    }

    fn flush(&mut self) -> io::Result<()> {
        self.deferred_result()?;
        self.file.flush()
    }
}

impl Seek for RealSplitFile {
    fn seek(&mut self, position: SeekFrom) -> io::Result<u64> {
        self.deferred_result()?;
        self.file.seek(position)
    }
}

impl SplitFile for RealSplitFile {
    fn write_ignored(&mut self, buffer: &[u8]) {
        if self.deferred_write_error.is_none() {
            if let Err(error) = self.file.write_all(buffer) {
                self.deferred_write_error = Some(DeferredIoError::capture(error));
            }
        }
    }

    fn set_len(&mut self, len: u64) -> io::Result<()> {
        self.deferred_result()?;
        self.file.set_len(len)
    }

    fn finalize(&mut self) -> io::Result<()> {
        self.deferred_result()?;
        self.file.flush()
    }
}

impl Runtime for RealRuntime {
    fn open_input(&mut self, path: &OsStr) -> io::Result<Box<dyn Read>> {
        File::open(path).map(|file| Box::new(file) as Box<dyn Read>)
    }

    fn create_split(&mut self, path: &OsStr) -> io::Result<Box<dyn SplitFile>> {
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(true)
            .open(path)?;
        Ok(Box::new(RealSplitFile {
            file,
            deferred_write_error: None,
        }))
    }

    fn create_temp(&mut self) -> io::Result<Box<dyn SplitFile>> {
        static COUNTER: AtomicU64 = AtomicU64::new(0);

        for _ in 0..128 {
            let serial = COUNTER.fetch_add(1, Ordering::Relaxed);
            let path =
                std::env::temp_dir().join(format!(".csplit.{}.{}", std::process::id(), serial));
            match OpenOptions::new()
                .read(true)
                .write(true)
                .create_new(true)
                .mode(0o600)
                .open(&path)
            {
                Ok(file) => {
                    fs::remove_file(&path)?;
                    return Ok(Box::new(RealSplitFile {
                        file,
                        deferred_write_error: None,
                    }));
                }
                Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
                Err(error) => return Err(error),
            }
        }

        Err(io::Error::new(
            io::ErrorKind::AlreadyExists,
            "unable to create temporary file",
        ))
    }

    fn remove_file(&mut self, path: &OsStr) -> io::Result<()> {
        fs::remove_file(path)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct CChunk {
    pub(crate) visible: Vec<u8>,
    pub(crate) consumed: usize,
    pub(crate) ended_with_lf: bool,
}

pub(crate) struct CLineReader {
    infile: Box<dyn Read>,
    original_eof: bool,
    buffer: [u8; LINE_MAX],
}

impl CLineReader {
    pub(crate) fn new(infile: Box<dyn Read>) -> Self {
        Self {
            infile,
            original_eof: false,
            buffer: [0; LINE_MAX],
        }
    }

    pub(crate) fn get_line(
        &mut self,
        mut overfile: Option<&mut (dyn SplitFile + '_)>,
    ) -> io::Result<Option<CChunk>> {
        if let Some(source) = overfile.as_deref_mut() {
            if let Some((chunk, _)) = read_chunk(source, &mut self.buffer)? {
                return Ok(Some(chunk));
            }
        }

        let chunk = read_chunk(self.infile.as_mut(), &mut self.buffer)?;
        if let Some((chunk, saw_eof)) = chunk {
            self.original_eof |= saw_eof;
            Ok(Some(chunk))
        } else {
            self.original_eof = true;
            Ok(None)
        }
    }

    pub(crate) fn original_eof(&self) -> bool {
        self.original_eof
    }
}

fn read_chunk(
    source: &mut dyn Read,
    buffer: &mut [u8; LINE_MAX],
) -> io::Result<Option<(CChunk, bool)>> {
    let mut consumed = 0;
    let mut saw_eof = false;

    while consumed < CHUNK_MAX {
        match source.read(&mut buffer[consumed..consumed + 1]) {
            Ok(0) => {
                saw_eof = true;
                break;
            }
            Ok(1) => {
                consumed += 1;
                if buffer[consumed - 1] == b'\n' {
                    break;
                }
            }
            Ok(_) => unreachable!("single-byte read returned more than one byte"),
            Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
            Err(error) => return Err(error),
        }
    }

    if consumed == 0 {
        return Ok(None);
    }

    let visible_len = buffer[..consumed]
        .iter()
        .position(|byte| *byte == 0)
        .unwrap_or(consumed);
    Ok(Some((
        CChunk {
            visible: buffer[..visible_len].to_vec(),
            consumed,
            ended_with_lf: buffer[consumed - 1] == b'\n',
        },
        saw_eof,
    )))
}

#[cfg(test)]
pub(crate) mod mock {
    use std::cell::RefCell;
    use std::collections::BTreeMap;
    use std::io::{self, ErrorKind, Read, Seek, SeekFrom, Write};
    use std::rc::Rc;

    use super::{DeferredIoError, Runtime, SplitFile};
    use std::ffi::OsStr;
    use std::os::unix::ffi::OsStrExt;

    #[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
    pub(crate) enum FailurePoint {
        OpenInput,
        CreateSplit,
        CreateTemp,
        Read,
        Write,
        Seek,
        Flush,
        Truncate,
        Finalize,
        Remove,
    }

    #[derive(Debug, Default)]
    pub(crate) struct MockRuntime {
        pub(crate) files: BTreeMap<Vec<u8>, Rc<RefCell<Vec<u8>>>>,
        pub(crate) create_order: Vec<Vec<u8>>,
        pub(crate) remove_order: Vec<Vec<u8>>,
        pub(crate) failures: BTreeMap<FailurePoint, ErrorKind>,
    }

    #[derive(Debug, Default)]
    pub(crate) struct MockSplitFile {
        pub(crate) bytes: Rc<RefCell<Vec<u8>>>,
        pub(crate) position: u64,
        pub(crate) failures: BTreeMap<FailurePoint, ErrorKind>,
        pub(crate) deferred_write_error: Option<DeferredIoError>,
    }

    impl MockSplitFile {
        fn deferred_result(&self) -> io::Result<()> {
            match &self.deferred_write_error {
                Some(error) => Err(error.to_error()),
                None => Ok(()),
            }
        }
    }

    impl Read for MockSplitFile {
        fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
            fail_if_requested(&self.failures, FailurePoint::Read)?;
            let bytes = self.bytes.borrow();
            let start = usize::try_from(self.position)
                .map_err(|_| io::Error::new(ErrorKind::InvalidInput, "position overflow"))?;
            if start >= bytes.len() {
                return Ok(0);
            }
            let count = buffer.len().min(bytes.len() - start);
            buffer[..count].copy_from_slice(&bytes[start..start + count]);
            self.position += count as u64;
            Ok(count)
        }
    }

    impl Write for MockSplitFile {
        fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
            self.deferred_result()?;
            fail_if_requested(&self.failures, FailurePoint::Write)?;
            let start = usize::try_from(self.position)
                .map_err(|_| io::Error::new(ErrorKind::InvalidInput, "position overflow"))?;
            let end = start
                .checked_add(buffer.len())
                .ok_or_else(|| io::Error::new(ErrorKind::InvalidInput, "position overflow"))?;
            let mut bytes = self.bytes.borrow_mut();
            if bytes.len() < end {
                bytes.resize(end, 0);
            }
            bytes[start..end].copy_from_slice(buffer);
            self.position = end as u64;
            Ok(buffer.len())
        }

        fn flush(&mut self) -> io::Result<()> {
            self.deferred_result()?;
            fail_if_requested(&self.failures, FailurePoint::Flush)
        }
    }

    impl Seek for MockSplitFile {
        fn seek(&mut self, position: SeekFrom) -> io::Result<u64> {
            self.deferred_result()?;
            fail_if_requested(&self.failures, FailurePoint::Seek)?;
            let len = self.bytes.borrow().len() as i128;
            let next = match position {
                SeekFrom::Start(position) => i128::from(position),
                SeekFrom::End(offset) => len + i128::from(offset),
                SeekFrom::Current(offset) => i128::from(self.position) + i128::from(offset),
            };
            if !(0..=i128::from(u64::MAX)).contains(&next) {
                return Err(io::Error::new(ErrorKind::InvalidInput, "invalid seek"));
            }
            self.position = next as u64;
            Ok(self.position)
        }
    }

    impl SplitFile for MockSplitFile {
        fn write_ignored(&mut self, buffer: &[u8]) {
            if self.deferred_write_error.is_none() {
                if let Err(error) = self.write_all(buffer) {
                    self.deferred_write_error = Some(DeferredIoError::capture(error));
                }
            }
        }

        fn set_len(&mut self, len: u64) -> io::Result<()> {
            self.deferred_result()?;
            fail_if_requested(&self.failures, FailurePoint::Truncate)?;
            let len = usize::try_from(len)
                .map_err(|_| io::Error::new(ErrorKind::InvalidInput, "length overflow"))?;
            self.bytes.borrow_mut().resize(len, 0);
            Ok(())
        }

        fn finalize(&mut self) -> io::Result<()> {
            self.deferred_result()?;
            fail_if_requested(&self.failures, FailurePoint::Finalize)
        }
    }

    impl Runtime for MockRuntime {
        fn open_input(&mut self, path: &OsStr) -> io::Result<Box<dyn Read>> {
            fail_if_requested(&self.failures, FailurePoint::OpenInput)?;
            let bytes = self
                .files
                .get(path.as_bytes())
                .cloned()
                .ok_or_else(|| io::Error::new(ErrorKind::NotFound, "not found"))?;
            Ok(Box::new(MockSplitFile {
                bytes,
                position: 0,
                failures: self.failures.clone(),
                deferred_write_error: None,
            }))
        }

        fn create_split(&mut self, path: &OsStr) -> io::Result<Box<dyn SplitFile>> {
            let key = path.as_bytes().to_vec();
            self.create_order.push(key.clone());
            fail_if_requested(&self.failures, FailurePoint::CreateSplit)?;
            let bytes = self
                .files
                .entry(key)
                .or_insert_with(|| Rc::new(RefCell::new(Vec::new())))
                .clone();
            bytes.borrow_mut().clear();
            Ok(Box::new(MockSplitFile {
                bytes,
                position: 0,
                failures: self.failures.clone(),
                deferred_write_error: None,
            }))
        }

        fn create_temp(&mut self) -> io::Result<Box<dyn SplitFile>> {
            fail_if_requested(&self.failures, FailurePoint::CreateTemp)?;
            Ok(Box::new(MockSplitFile {
                bytes: Rc::new(RefCell::new(Vec::new())),
                position: 0,
                failures: self.failures.clone(),
                deferred_write_error: None,
            }))
        }

        fn remove_file(&mut self, path: &OsStr) -> io::Result<()> {
            let key = path.as_bytes().to_vec();
            self.remove_order.push(key.clone());
            fail_if_requested(&self.failures, FailurePoint::Remove)?;
            self.files.remove(&key);
            Ok(())
        }
    }

    fn fail_if_requested(
        failures: &BTreeMap<FailurePoint, ErrorKind>,
        point: FailurePoint,
    ) -> io::Result<()> {
        match failures.get(&point) {
            Some(kind) => Err(io::Error::from(*kind)),
            None => Ok(()),
        }
    }
}

#[cfg(test)]
#[path = "split_io/tests.rs"]
mod tests;
