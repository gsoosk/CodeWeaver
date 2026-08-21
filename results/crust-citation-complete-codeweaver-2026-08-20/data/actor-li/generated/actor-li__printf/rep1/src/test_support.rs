use std::cell::RefCell;
use std::io::{self, Write};
use std::rc::Rc;

#[derive(Debug, Default)]
pub(crate) struct MockWriter {
    pub(crate) bytes: Vec<u8>,
    pub(crate) flush_count: usize,
}

impl Write for MockWriter {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.bytes.extend_from_slice(bytes);
        Ok(bytes.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        self.flush_count += 1;
        Ok(())
    }
}

#[derive(Debug)]
pub(crate) struct FailAfterWriter {
    pub(crate) fail_after: usize,
    pub(crate) written: usize,
    pub(crate) bytes: Vec<u8>,
    fail_flush: bool,
}

impl FailAfterWriter {
    pub(crate) fn new(fail_after: usize) -> Self {
        Self {
            fail_after,
            written: 0,
            bytes: Vec::new(),
            fail_flush: false,
        }
    }

    pub(crate) fn failing_flush() -> Self {
        Self {
            fail_after: usize::MAX,
            written: 0,
            bytes: Vec::new(),
            fail_flush: true,
        }
    }
}

impl Write for FailAfterWriter {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        if bytes.is_empty() {
            return Ok(0);
        }
        if self.written >= self.fail_after {
            return Err(io::Error::new(
                io::ErrorKind::BrokenPipe,
                "configured write failure",
            ));
        }

        let count = bytes.len().min(self.fail_after - self.written);
        self.bytes.extend_from_slice(&bytes[..count]);
        self.written += count;
        Ok(count)
    }

    fn flush(&mut self) -> io::Result<()> {
        if self.fail_flush {
            Err(io::Error::new(
                io::ErrorKind::BrokenPipe,
                "configured flush failure",
            ))
        } else {
            Ok(())
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Stream {
    Stdout,
    Stderr,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum WriterEvent {
    Write { stream: Stream, bytes: Vec<u8> },
    Flush { stream: Stream },
}

#[derive(Debug, Clone)]
pub(crate) struct RecordingWriter {
    pub(crate) stream: Stream,
    pub(crate) events: Rc<RefCell<Vec<WriterEvent>>>,
}

impl RecordingWriter {
    pub(crate) fn new(stream: Stream) -> Self {
        Self {
            stream,
            events: Rc::new(RefCell::new(Vec::new())),
        }
    }

    pub(crate) fn with_events(stream: Stream, events: Rc<RefCell<Vec<WriterEvent>>>) -> Self {
        Self { stream, events }
    }
}

impl Write for RecordingWriter {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.events.borrow_mut().push(WriterEvent::Write {
            stream: self.stream,
            bytes: bytes.to_vec(),
        });
        Ok(bytes.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        self.events.borrow_mut().push(WriterEvent::Flush {
            stream: self.stream,
        });
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{FailAfterWriter, MockWriter, RecordingWriter, Stream, WriterEvent};
    use std::io::{ErrorKind, Write};

    #[test]
    fn mock_writer_captures_raw_bytes_and_flushes() {
        let mut writer = MockWriter::default();
        writer.write_all(b"\0\xff").unwrap();
        writer.flush().unwrap();

        assert_eq!(writer.bytes, b"\0\xff");
        assert_eq!(writer.flush_count, 1);
    }

    #[test]
    fn fail_after_writer_stops_at_the_exact_boundary() {
        let mut immediate = FailAfterWriter::new(0);
        assert_eq!(
            immediate.write_all(b"x").unwrap_err().kind(),
            ErrorKind::BrokenPipe
        );
        assert!(immediate.bytes.is_empty());

        let mut partial = FailAfterWriter::new(3);
        assert_eq!(partial.write(b"abcde").unwrap(), 3);
        assert_eq!(
            partial.write_all(b"de").unwrap_err().kind(),
            ErrorKind::BrokenPipe
        );
        assert_eq!(partial.bytes, b"abc");
    }

    #[test]
    fn fail_after_writer_exposes_flush_failures() {
        let mut writer = FailAfterWriter::failing_flush();
        writer.write_all(b"captured").unwrap();

        assert_eq!(writer.flush().unwrap_err().kind(), ErrorKind::BrokenPipe);
        assert_eq!(writer.bytes, b"captured");
    }

    #[test]
    fn recording_writers_share_cross_stream_ordering() {
        let mut stdout = RecordingWriter::new(Stream::Stdout);
        let events = stdout.events.clone();
        let mut stderr = RecordingWriter::with_events(Stream::Stderr, events.clone());

        stdout.write_all(b"out").unwrap();
        stderr.write_all(b"err").unwrap();
        stderr.flush().unwrap();

        assert_eq!(
            *events.borrow(),
            vec![
                WriterEvent::Write {
                    stream: Stream::Stdout,
                    bytes: b"out".to_vec(),
                },
                WriterEvent::Write {
                    stream: Stream::Stderr,
                    bytes: b"err".to_vec(),
                },
                WriterEvent::Flush {
                    stream: Stream::Stderr,
                },
            ]
        );
    }
}
