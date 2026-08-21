use std::cell::RefCell;
use std::collections::BTreeMap;
use std::ffi::OsString;
use std::io::{Cursor, ErrorKind, Seek, SeekFrom, Write};
use std::rc::Rc;

use super::mock::{FailurePoint, MockRuntime, MockSplitFile};
use super::{CLineReader, SplitFile, CHUNK_MAX, C_BUFSIZ};
use crate::cli::{parse, Invocation};
use crate::csplit::CsplitState;

fn reader(bytes: Vec<u8>) -> CLineReader {
    CLineReader::new(Box::new(Cursor::new(bytes)))
}

#[test]
fn empty_input() {
    let mut reader = reader(Vec::new());
    assert!(reader.get_line(None).unwrap().is_none());
    assert!(reader.original_eof());
}

#[test]
fn lf_terminated_eof() {
    let mut reader = reader(b"line\n".to_vec());
    assert_eq!(reader.get_line(None).unwrap().unwrap().visible, b"line\n");
    assert!(!reader.original_eof());
    assert!(reader.get_line(None).unwrap().is_none());
    assert!(reader.original_eof());
}

#[test]
fn unterminated_eof() {
    let mut reader = reader(b"line".to_vec());
    assert_eq!(reader.get_line(None).unwrap().unwrap().visible, b"line");
    assert!(reader.original_eof());
}

#[test]
fn chunk_length_2046() {
    let mut input = vec![b'a'; 2046];
    input.push(b'\n');
    let mut reader = reader(input);
    assert_eq!(reader.get_line(None).unwrap().unwrap().consumed, 2047);
}

#[test]
fn chunk_length_2047() {
    let mut reader = reader(vec![b'a'; CHUNK_MAX]);
    let chunk = reader.get_line(None).unwrap().unwrap();
    assert_eq!(chunk.consumed, CHUNK_MAX);
    assert!(!reader.original_eof());
}

#[test]
fn chunk_length_2048() {
    let mut reader = reader(vec![b'a'; CHUNK_MAX + 1]);
    assert_eq!(reader.get_line(None).unwrap().unwrap().consumed, CHUNK_MAX);
    assert_eq!(reader.get_line(None).unwrap().unwrap().consumed, 1);
    assert!(reader.original_eof());
}

#[test]
fn long_logical_lines() {
    let mut reader = reader(vec![b'a'; CHUNK_MAX * 2 + 1]);
    assert_eq!(reader.get_line(None).unwrap().unwrap().consumed, CHUNK_MAX);
    assert_eq!(reader.get_line(None).unwrap().unwrap().consumed, CHUNK_MAX);
    assert_eq!(reader.get_line(None).unwrap().unwrap().consumed, 1);
}

#[test]
fn embedded_nul_consumption() {
    let mut reader = reader(b"ab\0discarded\nnext".to_vec());
    let first = reader.get_line(None).unwrap().unwrap();
    assert_eq!(first.consumed, 13);
    assert_eq!(reader.get_line(None).unwrap().unwrap().visible, b"next");
}

#[test]
fn embedded_nul_visibility() {
    let mut reader = reader(b"ab\0discarded\n".to_vec());
    assert_eq!(reader.get_line(None).unwrap().unwrap().visible, b"ab");
}

#[test]
fn overflow_eof_falls_back_to_input() {
    let bytes = Rc::new(RefCell::new(b"replayed\n".to_vec()));
    let mut overflow = MockSplitFile {
        bytes,
        position: 0,
        failures: BTreeMap::new(),
        deferred_write_error: None,
    };
    let mut reader = reader(b"original\n".to_vec());
    assert_eq!(
        reader
            .get_line(Some(&mut overflow))
            .unwrap()
            .unwrap()
            .visible,
        b"replayed\n"
    );
    assert_eq!(
        reader
            .get_line(Some(&mut overflow))
            .unwrap()
            .unwrap()
            .visible,
        b"original\n"
    );
}

#[test]
fn reverse_lf_scan_across_8192_byte_block() {
    let mut output_bytes = b"zero\none\n".to_vec();
    output_bytes.extend(std::iter::repeat_n(b'x', C_BUFSIZ));
    output_bytes.extend_from_slice(b"match\n");
    let bytes = Rc::new(RefCell::new(output_bytes));
    let position = bytes.borrow().len() as u64;
    let output = MockSplitFile {
        position,
        bytes,
        failures: BTreeMap::new(),
        deferred_write_error: None,
    };

    let parsed = parse(&Invocation {
        argv: vec![OsString::from("main"), OsString::from("input")],
        posixly_correct: false,
    })
    .unwrap();
    let mut runtime = MockRuntime::default();
    let mut stdout = Vec::new();
    let mut state = CsplitState::from_parsed(parsed, reader(Vec::new()), &mut runtime, &mut stdout);
    state.currfile = OsString::from("xx00");
    state.lineno = 3;

    state.toomuch(Some(Box::new(output)), 2).unwrap();

    assert_eq!(state.truncofs, 5);
    assert_eq!(state.lineno, 1);
    assert_eq!(state.get_line().unwrap().unwrap().visible, b"one\n");
    assert_eq!(state.lineno, 2);
}

#[test]
fn deferred_errors() {
    let bytes = Rc::new(RefCell::new(Vec::new()));
    let mut failures = BTreeMap::new();
    failures.insert(FailurePoint::Write, ErrorKind::BrokenPipe);
    let mut output = MockSplitFile {
        bytes: bytes.clone(),
        position: 0,
        failures,
        deferred_write_error: None,
    };

    output.write_ignored(b"not written");

    assert!(bytes.borrow().is_empty());
    assert_eq!(output.flush().unwrap_err().kind(), ErrorKind::BrokenPipe);
    assert_eq!(
        output.seek(SeekFrom::Current(0)).unwrap_err().kind(),
        ErrorKind::BrokenPipe
    );
    assert_eq!(output.set_len(0).unwrap_err().kind(), ErrorKind::BrokenPipe);
    assert_eq!(output.finalize().unwrap_err().kind(), ErrorKind::BrokenPipe);
}
