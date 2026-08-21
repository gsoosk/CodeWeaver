#![forbid(unsafe_code)]
#![allow(dead_code)]

use std::cmp::Ordering;
use std::ffi::{OsStr, OsString};
use std::fs::Metadata;
use std::io::{self, Write};
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::{FileTypeExt, MetadataExt};
use std::path::Path;

use nix::unistd::{self, AccessFlags};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Token {
    Eoi,
    FilRd,
    FilWr,
    FilEx,
    FilExist,
    FilReg,
    FilDir,
    FilCdev,
    FilBdev,
    FilFifo,
    FilSock,
    FilSym,
    FilGz,
    FilTt,
    FilSuid,
    FilSgid,
    FilSticky,
    FilNt,
    FilOt,
    FilEq,
    FilUid,
    FilGid,
    StrEz,
    StrNz,
    StrEq,
    StrNe,
    StrLt,
    StrGt,
    IntEq,
    IntNe,
    IntGe,
    IntGt,
    IntLe,
    IntLt,
    UnaryNot,
    BooleanAnd,
    BooleanOr,
    LeftParen,
    RightParen,
    Operand,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum TokenType {
    UnOp,
    BinOp,
    BooleanUnOp,
    BooleanBinOp,
    Paren,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct TOp {
    text: &'static [u8],
    token: Token,
    kind: TokenType,
}

const OPS: &[TOp] = &[
    TOp {
        text: b"-r",
        token: Token::FilRd,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-w",
        token: Token::FilWr,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-x",
        token: Token::FilEx,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-e",
        token: Token::FilExist,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-f",
        token: Token::FilReg,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-d",
        token: Token::FilDir,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-c",
        token: Token::FilCdev,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-b",
        token: Token::FilBdev,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-p",
        token: Token::FilFifo,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-u",
        token: Token::FilSuid,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-g",
        token: Token::FilSgid,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-k",
        token: Token::FilSticky,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-s",
        token: Token::FilGz,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-t",
        token: Token::FilTt,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-z",
        token: Token::StrEz,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-n",
        token: Token::StrNz,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-h",
        token: Token::FilSym,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-O",
        token: Token::FilUid,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-G",
        token: Token::FilGid,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-L",
        token: Token::FilSym,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"-S",
        token: Token::FilSock,
        kind: TokenType::UnOp,
    },
    TOp {
        text: b"=",
        token: Token::StrEq,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"!=",
        token: Token::StrNe,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"<",
        token: Token::StrLt,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b">",
        token: Token::StrGt,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"-eq",
        token: Token::IntEq,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"-ne",
        token: Token::IntNe,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"-ge",
        token: Token::IntGe,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"-gt",
        token: Token::IntGt,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"-le",
        token: Token::IntLe,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"-lt",
        token: Token::IntLt,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"-nt",
        token: Token::FilNt,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"-ot",
        token: Token::FilOt,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"-ef",
        token: Token::FilEq,
        kind: TokenType::BinOp,
    },
    TOp {
        text: b"!",
        token: Token::UnaryNot,
        kind: TokenType::BooleanUnOp,
    },
    TOp {
        text: b"-a",
        token: Token::BooleanAnd,
        kind: TokenType::BooleanBinOp,
    },
    TOp {
        text: b"-o",
        token: Token::BooleanOr,
        kind: TokenType::BooleanBinOp,
    },
    TOp {
        text: b"(",
        token: Token::LeftParen,
        kind: TokenType::Paren,
    },
    TOp {
        text: b")",
        token: Token::RightParen,
        kind: TokenType::Paren,
    },
];

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
enum AccessMode {
    Exists,
    Read,
    Write,
    Execute,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FileKind {
    Regular,
    Directory,
    CharacterDevice,
    BlockDevice,
    Fifo,
    Socket,
    Symlink,
    Other,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct FileStat {
    kind: FileKind,
    mode: u32,
    size: u64,
    uid: u32,
    gid: u32,
    mtime_secs: i64,
    device: u64,
    inode: u64,
}

trait Runtime {
    fn stat(&self, path: &OsStr) -> io::Result<FileStat>;
    fn lstat(&self, path: &OsStr) -> io::Result<FileStat>;
    fn access(&self, path: &OsStr, mode: AccessMode) -> io::Result<()>;
    fn isatty(&self, fd: i32) -> io::Result<bool>;
    fn effective_uid(&self) -> u32;
    fn effective_gid(&self) -> u32;
}

#[derive(Clone, Copy, Debug, Default)]
struct RealRuntime;

impl Runtime for RealRuntime {
    fn stat(&self, path: &OsStr) -> io::Result<FileStat> {
        std::fs::metadata(Path::new(path)).map(file_stat)
    }

    fn lstat(&self, path: &OsStr) -> io::Result<FileStat> {
        std::fs::symlink_metadata(Path::new(path)).map(file_stat)
    }

    fn access(&self, path: &OsStr, mode: AccessMode) -> io::Result<()> {
        let flags = match mode {
            AccessMode::Exists => AccessFlags::F_OK,
            AccessMode::Read => AccessFlags::R_OK,
            AccessMode::Write => AccessFlags::W_OK,
            AccessMode::Execute => AccessFlags::X_OK,
        };
        unistd::access(Path::new(path), flags).map_err(nix_error)
    }

    fn isatty(&self, fd: i32) -> io::Result<bool> {
        unistd::isatty(fd).map_err(nix_error)
    }

    fn effective_uid(&self) -> u32 {
        unistd::geteuid().as_raw()
    }

    fn effective_gid(&self) -> u32 {
        unistd::getegid().as_raw()
    }
}

fn nix_error(error: nix::errno::Errno) -> io::Error {
    io::Error::from_raw_os_error(error as i32)
}

fn file_stat(metadata: Metadata) -> FileStat {
    let file_type = metadata.file_type();
    let kind = if file_type.is_file() {
        FileKind::Regular
    } else if file_type.is_dir() {
        FileKind::Directory
    } else if file_type.is_char_device() {
        FileKind::CharacterDevice
    } else if file_type.is_block_device() {
        FileKind::BlockDevice
    } else if file_type.is_fifo() {
        FileKind::Fifo
    } else if file_type.is_socket() {
        FileKind::Socket
    } else if file_type.is_symlink() {
        FileKind::Symlink
    } else {
        FileKind::Other
    };

    FileStat {
        kind,
        mode: metadata.mode(),
        size: metadata.size(),
        uid: metadata.uid(),
        gid: metadata.gid(),
        mtime_secs: metadata.mtime(),
        device: metadata.dev(),
        inode: metadata.ino(),
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Diagnostic {
    payload: Vec<u8>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct NumberSlice<'a> {
    sign: i8,
    digits: &'a [u8],
}

struct Parser<'a, R: Runtime + ?Sized> {
    operands: &'a [OsString],
    index: usize,
    current_op: Option<&'static TOp>,
    runtime: &'a R,
}

impl<'a, R: Runtime + ?Sized> Parser<'a, R> {
    fn new(operands: &'a [OsString], runtime: &'a R) -> Self {
        Self {
            operands,
            index: 0,
            current_op: None,
            runtime,
        }
    }

    fn t_lex(&mut self, operand: Option<&OsStr>) -> Token {
        let op = operand.and_then(lookup_op);
        self.current_op = op;
        match (operand, op) {
            (None, _) => Token::Eoi,
            (Some(_), Some(op)) => op.token,
            (Some(_), None) => Token::Operand,
        }
    }

    fn t_lex_type(&self, operand: Option<&OsStr>) -> Option<TokenType> {
        operand.and_then(lookup_op).map(|op| op.kind)
    }

    fn lex_at(&mut self, index: usize) -> Token {
        let op = self
            .operands
            .get(index)
            .and_then(|value| lookup_op(value.as_os_str()));
        self.current_op = op;
        match (self.operands.get(index), op) {
            (None, _) => Token::Eoi,
            (Some(_), Some(op)) => op.token,
            (Some(_), None) => Token::Operand,
        }
    }

    fn advance_and_lex(&mut self) -> Token {
        self.index += 1;
        self.lex_at(self.index)
    }

    fn oexpr(&mut self, token: Token) -> Result<bool, Diagnostic> {
        let left = self.aexpr(token)?;
        if self.advance_and_lex() == Token::BooleanOr {
            let token = self.advance_and_lex();
            let right = self.oexpr(token)?;
            Ok(right || left)
        } else {
            self.index -= 1;
            Ok(left)
        }
    }

    fn aexpr(&mut self, token: Token) -> Result<bool, Diagnostic> {
        let left = self.nexpr(token)?;
        if self.advance_and_lex() == Token::BooleanAnd {
            let token = self.advance_and_lex();
            let right = self.aexpr(token)?;
            Ok(right && left)
        } else {
            self.index -= 1;
            Ok(left)
        }
    }

    fn nexpr(&mut self, token: Token) -> Result<bool, Diagnostic> {
        if token == Token::UnaryNot {
            let token = self.advance_and_lex();
            return Ok(!self.nexpr(token)?);
        }
        self.primary(token)
    }

    fn primary(&mut self, token: Token) -> Result<bool, Diagnostic> {
        if token == Token::Eoi {
            return Err(syntax(None, b"argument expected"));
        }

        if token == Token::LeftParen {
            let token = self.advance_and_lex();
            let result = self.oexpr(token)?;
            if self.advance_and_lex() != Token::RightParen {
                return Err(syntax(None, b"closing paren expected"));
            }
            return Ok(result);
        }

        if self.t_lex_type(self.operands.get(self.index + 1).map(OsString::as_os_str))
            == Some(TokenType::BinOp)
        {
            self.lex_at(self.index + 1);
            if self.current_op.map(|op| op.kind) == Some(TokenType::BinOp) {
                return self.binop();
            }
        }

        if let Some(op) = self.current_op.filter(|op| op.kind == TokenType::UnOp) {
            self.index += 1;
            let operand = self
                .operands
                .get(self.index)
                .ok_or_else(|| syntax(Some(op.text), b"argument expected"))?;
            let bytes = operand.as_os_str().as_bytes();
            return match token {
                Token::StrEz => Ok(bytes.is_empty()),
                Token::StrNz => Ok(!bytes.is_empty()),
                Token::FilTt => {
                    let fd = getn(bytes)?;
                    Ok(self.runtime.isatty(fd).unwrap_or(false))
                }
                _ => Ok(filstat(self.runtime, operand.as_os_str(), token)),
            };
        }

        let operand = self
            .operands
            .get(self.index)
            .ok_or_else(|| syntax(None, b"argument expected"))?;
        Ok(!operand.as_os_str().as_bytes().is_empty())
    }

    fn binop(&mut self) -> Result<bool, Diagnostic> {
        let left = self
            .operands
            .get(self.index)
            .cloned()
            .ok_or_else(|| syntax(None, b"argument expected"))?;

        self.index += 1;
        let operator_value = self
            .operands
            .get(self.index)
            .cloned()
            .ok_or_else(|| syntax(None, b"not a binary operator"))?;
        self.lex_at(self.index);
        let op = self.current_op;

        self.index += 1;
        let right = self.operands.get(self.index).cloned().ok_or_else(|| {
            syntax(
                op.map(|value| value.text)
                    .or(Some(operator_value.as_os_str().as_bytes())),
                b"argument expected",
            )
        })?;

        let op = op.ok_or_else(|| {
            syntax(
                Some(operator_value.as_os_str().as_bytes()),
                b"not a binary operator",
            )
        })?;
        let left_bytes = left.as_os_str().as_bytes();
        let right_bytes = right.as_os_str().as_bytes();
        let result = match op.token {
            Token::StrEq => left_bytes == right_bytes,
            Token::StrNe => left_bytes != right_bytes,
            Token::StrLt => left_bytes < right_bytes,
            Token::StrGt => left_bytes > right_bytes,
            Token::IntEq => intcmp(left_bytes, right_bytes)? == Ordering::Equal,
            Token::IntNe => intcmp(left_bytes, right_bytes)? != Ordering::Equal,
            Token::IntGe => intcmp(left_bytes, right_bytes)? != Ordering::Less,
            Token::IntGt => intcmp(left_bytes, right_bytes)? == Ordering::Greater,
            Token::IntLe => intcmp(left_bytes, right_bytes)? != Ordering::Greater,
            Token::IntLt => intcmp(left_bytes, right_bytes)? == Ordering::Less,
            Token::FilNt => newerf(self.runtime, left.as_os_str(), right.as_os_str()),
            Token::FilOt => olderf(self.runtime, left.as_os_str(), right.as_os_str()),
            Token::FilEq => equalf(self.runtime, left.as_os_str(), right.as_os_str()),
            _ => return Err(syntax(Some(op.text), b"not a binary operator")),
        };
        Ok(result)
    }
}

fn lookup_op(operand: &OsStr) -> Option<&'static TOp> {
    let bytes = operand.as_bytes();
    OPS.iter().find(|op| op.text == bytes)
}

fn program_basename(argv0: &OsStr) -> &[u8] {
    let bytes = argv0.as_bytes();
    bytes
        .iter()
        .rposition(|byte| *byte == b'/')
        .map_or(bytes, |position| &bytes[position + 1..])
}

fn syntax(subject: Option<&[u8]>, message: &[u8]) -> Diagnostic {
    let mut payload = Vec::new();
    if let Some(subject) = subject.filter(|subject| !subject.is_empty()) {
        payload.extend_from_slice(subject);
        payload.extend_from_slice(b": ");
    }
    payload.extend_from_slice(message);
    Diagnostic { payload }
}

fn direct_diagnostic(subject: &[u8], message: &[u8]) -> Diagnostic {
    let mut payload = Vec::with_capacity(subject.len() + message.len() + 2);
    payload.extend_from_slice(subject);
    payload.extend_from_slice(b": ");
    payload.extend_from_slice(message);
    Diagnostic { payload }
}

fn format_diagnostic(program_name: &[u8], diagnostic: &Diagnostic) -> Vec<u8> {
    let mut record = Vec::with_capacity(program_name.len() + diagnostic.payload.len() + 3);
    record.extend_from_slice(program_name);
    record.extend_from_slice(b": ");
    record.extend_from_slice(&diagnostic.payload);
    record.push(b'\n');
    record
}

fn is_c_whitespace(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
}

fn getnstr(value: &[u8]) -> Result<NumberSlice<'_>, Diagnostic> {
    let mut position = 0;
    while value
        .get(position)
        .is_some_and(|byte| is_c_whitespace(*byte))
    {
        position += 1;
    }

    let mut sign = 1;
    match value.get(position) {
        Some(b'-') => {
            sign = -1;
            position += 1;
        }
        Some(b'+') => position += 1,
        _ => {}
    }

    while value.get(position) == Some(&b'0')
        && value.get(position + 1).is_some_and(u8::is_ascii_digit)
    {
        position += 1;
    }
    if value.get(position) == Some(&b'0') {
        sign = 1;
    }

    let start = position;
    while value.get(position).is_some_and(u8::is_ascii_digit) {
        position += 1;
    }
    let end = position;

    while value
        .get(position)
        .is_some_and(|byte| is_c_whitespace(*byte))
    {
        position += 1;
    }

    if position != value.len() || start == value.len() {
        return Err(direct_diagnostic(value, b"invalid"));
    }

    Ok(NumberSlice {
        sign,
        digits: &value[start..end],
    })
}

fn intcmp(left: &[u8], right: &[u8]) -> Result<Ordering, Diagnostic> {
    let left = getnstr(left)?;
    let right = getnstr(right)?;

    if left.sign != right.sign {
        return Ok(left.sign.cmp(&right.sign));
    }

    let magnitude = left
        .digits
        .len()
        .cmp(&right.digits.len())
        .then_with(|| left.digits.cmp(right.digits));
    Ok(if left.sign < 0 {
        magnitude.reverse()
    } else {
        magnitude
    })
}

fn getn(value: &[u8]) -> Result<i32, Diagnostic> {
    let number = getnstr(value)?;
    if number.sign != 1 {
        return Err(direct_diagnostic(value, b"too small"));
    }
    if number.digits.len() >= 32 {
        return Err(direct_diagnostic(value, b"too large"));
    }
    if number.digits.is_empty() {
        return Err(direct_diagnostic(value, b"invalid"));
    }

    let mut result = 0_i32;
    for digit in number.digits {
        result = result
            .checked_mul(10)
            .and_then(|value| value.checked_add(i32::from(*digit - b'0')))
            .ok_or_else(|| direct_diagnostic(value, b"too large"))?;
    }
    Ok(result)
}

fn filstat<R: Runtime + ?Sized>(runtime: &R, path: &OsStr, mode: Token) -> bool {
    if mode == Token::FilSym {
        return runtime
            .lstat(path)
            .is_ok_and(|stat| stat.kind == FileKind::Symlink);
    }

    let Ok(stat) = runtime.stat(path) else {
        return false;
    };

    match mode {
        Token::FilRd => runtime.access(path, AccessMode::Read).is_ok(),
        Token::FilWr => runtime.access(path, AccessMode::Write).is_ok(),
        Token::FilEx => runtime.access(path, AccessMode::Execute).is_ok(),
        Token::FilExist => runtime.access(path, AccessMode::Exists).is_ok(),
        Token::FilReg => stat.kind == FileKind::Regular,
        Token::FilDir => stat.kind == FileKind::Directory,
        Token::FilCdev => stat.kind == FileKind::CharacterDevice,
        Token::FilBdev => stat.kind == FileKind::BlockDevice,
        Token::FilFifo | Token::FilSock => stat.kind == FileKind::Fifo,
        Token::FilSuid => stat.mode & 0o4000 != 0,
        Token::FilSgid => stat.mode & 0o2000 != 0,
        Token::FilSticky => stat.mode & 0o1000 != 0,
        Token::FilGz => stat.size > 0,
        Token::FilUid => stat.uid == runtime.effective_uid(),
        Token::FilGid => stat.gid == runtime.effective_gid(),
        _ => true,
    }
}

fn newerf<R: Runtime + ?Sized>(runtime: &R, left: &OsStr, right: &OsStr) -> bool {
    let Ok(left) = runtime.stat(left) else {
        return false;
    };
    let Ok(right) = runtime.stat(right) else {
        return false;
    };
    left.mtime_secs > right.mtime_secs
}

fn olderf<R: Runtime + ?Sized>(runtime: &R, left: &OsStr, right: &OsStr) -> bool {
    let Ok(left) = runtime.stat(left) else {
        return false;
    };
    let Ok(right) = runtime.stat(right) else {
        return false;
    };
    left.mtime_secs < right.mtime_secs
}

fn equalf<R: Runtime + ?Sized>(runtime: &R, left: &OsStr, right: &OsStr) -> bool {
    let Ok(left) = runtime.stat(left) else {
        return false;
    };
    let Ok(right) = runtime.stat(right) else {
        return false;
    };
    left.device == right.device && left.inode == right.inode
}

fn evaluate<R: Runtime + ?Sized>(argv: &[OsString], runtime: &R) -> Result<bool, Diagnostic> {
    let Some(argv0) = argv.first() else {
        return Ok(false);
    };

    let mut end = argv.len();
    if program_basename(argv0.as_os_str()) == b"[" {
        if end < 2 || argv[end - 1].as_os_str().as_bytes() != b"]" {
            return Err(syntax(None, b"missing ]"));
        }
        end -= 1;
    }

    let operands = &argv[1..end];
    match operands.len() {
        0 => return Ok(false),
        1 => return Ok(!operands[0].as_os_str().as_bytes().is_empty()),
        2 if operands[0].as_os_str().as_bytes() == b"!" => {
            return Ok(operands[1].as_os_str().as_bytes().is_empty());
        }
        3 if operands[0].as_os_str().as_bytes() != b"!"
            && lookup_op(operands[1].as_os_str()).is_some_and(|op| op.kind == TokenType::BinOp) =>
        {
            let mut parser = Parser::new(operands, runtime);
            return parser.binop();
        }
        4 if operands[0].as_os_str().as_bytes() == b"!"
            && lookup_op(operands[2].as_os_str()).is_some_and(|op| op.kind == TokenType::BinOp) =>
        {
            let mut parser = Parser::new(&operands[1..], runtime);
            return Ok(!parser.binop()?);
        }
        _ => {}
    }

    let mut parser = Parser::new(operands, runtime);
    let token = parser.lex_at(0);
    let result = parser.oexpr(token)?;

    if parser.index < operands.len() && parser.index + 1 < operands.len() {
        return Err(syntax(
            Some(operands[parser.index + 1].as_os_str().as_bytes()),
            b"unknown operand",
        ));
    }
    Ok(result)
}

fn finish<W: Write>(program_name: &[u8], outcome: Result<bool, Diagnostic>, stderr: &mut W) -> i32 {
    match outcome {
        Ok(true) => 0,
        Ok(false) => 1,
        Err(diagnostic) => {
            let _ = stderr.write_all(&format_diagnostic(program_name, &diagnostic));
            2
        }
    }
}

fn run_with<R: Runtime + ?Sized, W: Write>(argv: &[OsString], runtime: &R, stderr: &mut W) -> i32 {
    let program_name = argv
        .first()
        .map(|value| program_basename(value.as_os_str()))
        .unwrap_or_default();
    finish(program_name, evaluate(argv, runtime), stderr)
}

fn translated_main() -> i32 {
    let argv: Vec<OsString> = std::env::args_os().collect();
    let runtime = RealRuntime;
    let stderr = io::stderr();
    run_with(&argv, &runtime, &mut stderr.lock())
}

fn main() {
    std::process::exit(translated_main());
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;
    use std::collections::BTreeMap;
    use std::os::unix::ffi::OsStringExt;

    #[derive(Clone, Debug)]
    enum FakeResult<T> {
        Value(T),
        Error(io::ErrorKind),
    }

    #[derive(Clone, Debug, Eq, PartialEq)]
    enum RuntimeCall {
        Stat(Vec<u8>),
        Lstat(Vec<u8>),
        Access(Vec<u8>, AccessMode),
        Isatty(i32),
        EffectiveUid,
        EffectiveGid,
    }

    #[derive(Debug, Default)]
    struct FakeRuntime {
        stats: BTreeMap<Vec<u8>, FakeResult<FileStat>>,
        lstats: BTreeMap<Vec<u8>, FakeResult<FileStat>>,
        access_results: BTreeMap<(Vec<u8>, AccessMode), FakeResult<()>>,
        tty_results: BTreeMap<i32, FakeResult<bool>>,
        effective_uid: u32,
        effective_gid: u32,
        calls: RefCell<Vec<RuntimeCall>>,
    }

    impl Runtime for FakeRuntime {
        fn stat(&self, path: &OsStr) -> io::Result<FileStat> {
            let path = path.as_bytes().to_vec();
            self.calls
                .borrow_mut()
                .push(RuntimeCall::Stat(path.clone()));
            configured_result(self.stats.get(&path))
        }

        fn lstat(&self, path: &OsStr) -> io::Result<FileStat> {
            let path = path.as_bytes().to_vec();
            self.calls
                .borrow_mut()
                .push(RuntimeCall::Lstat(path.clone()));
            configured_result(self.lstats.get(&path))
        }

        fn access(&self, path: &OsStr, mode: AccessMode) -> io::Result<()> {
            let path = path.as_bytes().to_vec();
            self.calls
                .borrow_mut()
                .push(RuntimeCall::Access(path.clone(), mode));
            configured_result(self.access_results.get(&(path, mode)))
        }

        fn isatty(&self, fd: i32) -> io::Result<bool> {
            self.calls.borrow_mut().push(RuntimeCall::Isatty(fd));
            configured_result(self.tty_results.get(&fd))
        }

        fn effective_uid(&self) -> u32 {
            self.calls.borrow_mut().push(RuntimeCall::EffectiveUid);
            self.effective_uid
        }

        fn effective_gid(&self) -> u32 {
            self.calls.borrow_mut().push(RuntimeCall::EffectiveGid);
            self.effective_gid
        }
    }

    fn configured_result<T: Clone>(result: Option<&FakeResult<T>>) -> io::Result<T> {
        match result {
            Some(FakeResult::Value(value)) => Ok(value.clone()),
            Some(FakeResult::Error(kind)) => Err(io::Error::from(*kind)),
            None => Err(io::Error::from(io::ErrorKind::NotFound)),
        }
    }

    fn os(bytes: &[u8]) -> OsString {
        OsString::from_vec(bytes.to_vec())
    }

    fn sample_stat(kind: FileKind) -> FileStat {
        FileStat {
            kind,
            mode: 0,
            size: 0,
            uid: 10,
            gid: 20,
            mtime_secs: 100,
            device: 30,
            inode: 40,
        }
    }

    macro_rules! raw_argv {
        ($($value:expr),* $(,)?) => {
            vec![$(os($value)),*]
        };
    }

    mod lexer_table {
        use super::*;

        #[test]
        fn ops_table_matches_source() {
            let expected: &[(&[u8], Token, TokenType)] = &[
                (b"-r", Token::FilRd, TokenType::UnOp),
                (b"-w", Token::FilWr, TokenType::UnOp),
                (b"-x", Token::FilEx, TokenType::UnOp),
                (b"-e", Token::FilExist, TokenType::UnOp),
                (b"-f", Token::FilReg, TokenType::UnOp),
                (b"-d", Token::FilDir, TokenType::UnOp),
                (b"-c", Token::FilCdev, TokenType::UnOp),
                (b"-b", Token::FilBdev, TokenType::UnOp),
                (b"-p", Token::FilFifo, TokenType::UnOp),
                (b"-u", Token::FilSuid, TokenType::UnOp),
                (b"-g", Token::FilSgid, TokenType::UnOp),
                (b"-k", Token::FilSticky, TokenType::UnOp),
                (b"-s", Token::FilGz, TokenType::UnOp),
                (b"-t", Token::FilTt, TokenType::UnOp),
                (b"-z", Token::StrEz, TokenType::UnOp),
                (b"-n", Token::StrNz, TokenType::UnOp),
                (b"-h", Token::FilSym, TokenType::UnOp),
                (b"-O", Token::FilUid, TokenType::UnOp),
                (b"-G", Token::FilGid, TokenType::UnOp),
                (b"-L", Token::FilSym, TokenType::UnOp),
                (b"-S", Token::FilSock, TokenType::UnOp),
                (b"=", Token::StrEq, TokenType::BinOp),
                (b"!=", Token::StrNe, TokenType::BinOp),
                (b"<", Token::StrLt, TokenType::BinOp),
                (b">", Token::StrGt, TokenType::BinOp),
                (b"-eq", Token::IntEq, TokenType::BinOp),
                (b"-ne", Token::IntNe, TokenType::BinOp),
                (b"-ge", Token::IntGe, TokenType::BinOp),
                (b"-gt", Token::IntGt, TokenType::BinOp),
                (b"-le", Token::IntLe, TokenType::BinOp),
                (b"-lt", Token::IntLt, TokenType::BinOp),
                (b"-nt", Token::FilNt, TokenType::BinOp),
                (b"-ot", Token::FilOt, TokenType::BinOp),
                (b"-ef", Token::FilEq, TokenType::BinOp),
                (b"!", Token::UnaryNot, TokenType::BooleanUnOp),
                (b"-a", Token::BooleanAnd, TokenType::BooleanBinOp),
                (b"-o", Token::BooleanOr, TokenType::BooleanBinOp),
                (b"(", Token::LeftParen, TokenType::Paren),
                (b")", Token::RightParen, TokenType::Paren),
            ];

            assert_eq!(OPS.len(), expected.len());
            let runtime = FakeRuntime::default();
            let mut parser = Parser::new(&[], &runtime);
            for (actual, &(text, token, kind)) in OPS.iter().zip(expected) {
                assert_eq!(
                    (actual.text, actual.token, actual.kind),
                    (text, token, kind)
                );

                let value = os(text);
                assert_eq!(lookup_op(value.as_os_str()), Some(actual));
                assert_eq!(parser.t_lex(Some(value.as_os_str())), token);
                assert_eq!(parser.current_op, Some(actual));
                assert_eq!(parser.t_lex_type(Some(value.as_os_str())), Some(kind));
                assert_eq!(parser.current_op, Some(actual));
            }
        }

        #[test]
        fn unknown_operand_eoi_and_case_sensitivity() {
            let runtime = FakeRuntime::default();
            let mut parser = Parser::new(&[], &runtime);
            let unknown: &[&[u8]] = &[
                b"", b"-N", b"-R", b"-oO", b"-EQ", b"==", b"[", b"]", b"operand", b"\xff",
            ];

            for value in unknown {
                let value = os(value);
                assert_eq!(lookup_op(value.as_os_str()), None);
                assert_eq!(parser.t_lex(Some(value.as_os_str())), Token::Operand);
                assert_eq!(parser.current_op, None);
                assert_eq!(parser.t_lex_type(Some(value.as_os_str())), None);
                assert_eq!(parser.current_op, None);
            }

            let recognized = os(b"-n");
            let unknown = os(b"-N");
            assert_eq!(parser.t_lex(Some(recognized.as_os_str())), Token::StrNz);
            let current_op = parser.current_op;
            assert_eq!(parser.t_lex_type(Some(unknown.as_os_str())), None);
            assert_eq!(parser.current_op, current_op);

            assert_eq!(parser.t_lex(None), Token::Eoi);
            assert_eq!(parser.current_op, None);
            assert_eq!(parser.t_lex_type(None), None);
            assert_eq!(parser.current_op, None);
        }

        #[test]
        fn operator_looking_binary_operands_remain_operands() {
            let runtime = FakeRuntime::default();
            let cases = [
                (raw_argv![b"test", b"-n", b"=", b"-n"], Ok(true)),
                (raw_argv![b"test", b"-z", b"!=", b"-n"], Ok(true)),
                (raw_argv![b"test", b"(", b"=", b"("], Ok(true)),
                (
                    raw_argv![b"test", b"(", b"-n", b"=", b"-n", b"-a", b"-z", b"!=", b"-n", b")"],
                    Ok(true),
                ),
            ];

            for (argv, expected) in cases {
                assert_eq!(evaluate(&argv, &runtime), expected, "argv: {argv:?}");
            }
            assert!(runtime.calls.borrow().is_empty());
        }
    }

    mod arity_parser {
        use super::*;

        #[test]
        fn zero_one_and_two_operand_special_cases() {
            let runtime = FakeRuntime::default();
            let cases = [
                (raw_argv![b"test"], Ok(false)),
                (raw_argv![b"test", b""], Ok(false)),
                (raw_argv![b"test", b"value"], Ok(true)),
                (raw_argv![b"test", b"-n"], Ok(true)),
                (raw_argv![b"test", b"!"], Ok(true)),
                (raw_argv![b"test", b"\xff"], Ok(true)),
                (raw_argv![b"test", b"!", b""], Ok(true)),
                (raw_argv![b"test", b"!", b"value"], Ok(false)),
                (raw_argv![b"test", b"!", b"!"], Ok(false)),
            ];

            for (argv, expected) in cases {
                assert_eq!(evaluate(&argv, &runtime), expected, "argv: {argv:?}");
            }

            assert_eq!(
                evaluate(&raw_argv![b"test", b"!x", b"value"], &runtime),
                Err(syntax(Some(b"value"), b"unknown operand"))
            );
            assert!(runtime.calls.borrow().is_empty());
        }

        #[test]
        fn three_and_four_operand_binary_special_cases() {
            let runtime = FakeRuntime::default();
            let cases = vec![
                (raw_argv![b"test", b"-n", b"=", b"-n"], Ok(true)),
                (raw_argv![b"test", b"(", b"=", b"("], Ok(true)),
                (raw_argv![b"test", b"-z", b"!=", b"-n"], Ok(true)),
                (
                    raw_argv![b"test", b"left", b"bogus", b"right"],
                    Err(syntax(Some(b"bogus"), b"unknown operand")),
                ),
                (
                    raw_argv![b"test", b"!", b"=", b"="],
                    Err(syntax(Some(b"="), b"argument expected")),
                ),
                (raw_argv![b"test", b"", b"-a", b"right"], Ok(false)),
                (raw_argv![b"test", b"!", b"x", b"=", b"x"], Ok(false)),
                (raw_argv![b"test", b"!", b"x", b"!=", b"x"], Ok(true)),
                (raw_argv![b"test", b"!", b"(", b"=", b"("], Ok(false)),
                (
                    raw_argv![b"test", b"x", b"=", b"x", b"extra"],
                    Err(syntax(Some(b"extra"), b"unknown operand")),
                ),
                (raw_argv![b"test", b"!", b"", b"-o", b""], Ok(true)),
            ];

            for (argv, expected) in cases {
                assert_eq!(evaluate(&argv, &runtime), expected, "argv: {argv:?}");
            }
            assert!(runtime.calls.borrow().is_empty());
        }

        #[test]
        fn precedence_parentheses_negation_and_cursor() {
            let runtime = FakeRuntime::default();
            let cases = [
                (raw_argv![b"test", b"x", b"-o", b"", b"-a", b""], Ok(true)),
                (raw_argv![b"test", b"", b"-a", b"x", b"-o", b"y"], Ok(true)),
                (raw_argv![b"test", b"x", b"-a", b"", b"-o", b""], Ok(false)),
                (raw_argv![b"test", b"!", b"!", b"x"], Ok(true)),
                (raw_argv![b"test", b"!", b"!", b""], Ok(false)),
                (
                    raw_argv![b"test", b"!", b"(", b"x", b"-a", b"(", b"", b"-o", b"y", b")", b")"],
                    Ok(false),
                ),
                (
                    raw_argv![b"test", b"(", b"x", b"-o", b"", b")", b"-a", b""],
                    Ok(false),
                ),
            ];

            for (argv, expected) in cases {
                assert_eq!(evaluate(&argv, &runtime), expected, "argv: {argv:?}");
            }

            let operands = raw_argv![b"(", b"x", b"=", b"x", b")", b"-a", b"!", b"", b"-o", b""];
            let mut parser = Parser::new(&operands, &runtime);
            let token = parser.lex_at(0);
            assert_eq!(parser.oexpr(token), Ok(true));
            assert_eq!(parser.index, operands.len() - 1);
            assert!(runtime.calls.borrow().is_empty());
        }

        #[test]
        fn logical_operators_evaluate_both_sides() {
            let mut runtime = FakeRuntime::default();
            runtime.tty_results.insert(7, FakeResult::Value(false));
            runtime.tty_results.insert(8, FakeResult::Value(true));

            assert_eq!(
                evaluate(
                    &raw_argv![b"test", b"x", b"=", b"x", b"-o", b"-t", b"7"],
                    &runtime
                ),
                Ok(true)
            );
            assert_eq!(
                runtime.calls.replace(Vec::new()),
                vec![RuntimeCall::Isatty(7)]
            );

            assert_eq!(
                evaluate(
                    &raw_argv![b"test", b"x", b"!=", b"x", b"-a", b"-t", b"8"],
                    &runtime
                ),
                Ok(false)
            );
            assert_eq!(
                runtime.calls.replace(Vec::new()),
                vec![RuntimeCall::Isatty(8)]
            );

            let error_cases = vec![
                (
                    raw_argv![b"test", b"x", b"=", b"x", b"-o", b"bad", b"-eq", b"1"],
                    direct_diagnostic(b"bad", b"invalid"),
                ),
                (
                    raw_argv![b"test", b"x", b"!=", b"x", b"-a", b"bad", b"-eq", b"1"],
                    direct_diagnostic(b"bad", b"invalid"),
                ),
                (
                    raw_argv![b"test", b"x", b"=", b"x", b"-o", b"-t", b"-1"],
                    direct_diagnostic(b"-1", b"too small"),
                ),
                (
                    raw_argv![b"test", b"x", b"!=", b"x", b"-a", b"-t", b"2147483648"],
                    direct_diagnostic(b"2147483648", b"too large"),
                ),
            ];
            for (argv, expected) in error_cases {
                assert_eq!(evaluate(&argv, &runtime), Err(expected), "argv: {argv:?}");
            }
            assert!(runtime.calls.borrow().is_empty());
        }

        #[test]
        fn missing_arguments_parentheses_and_unknown_operands() {
            let runtime = FakeRuntime::default();
            let cases = vec![
                (
                    raw_argv![b"test", b"x", b"="],
                    syntax(Some(b"="), b"argument expected"),
                ),
                (
                    raw_argv![b"test", b"x", b"-a", b"-n"],
                    syntax(Some(b"-n"), b"argument expected"),
                ),
                (
                    raw_argv![b"test", b"x", b"-a"],
                    syntax(None, b"argument expected"),
                ),
                (
                    raw_argv![b"test", b"!", b"!", b"!"],
                    syntax(None, b"argument expected"),
                ),
                (
                    raw_argv![b"test", b"(", b"!"],
                    syntax(None, b"argument expected"),
                ),
                (
                    raw_argv![b"test", b"(", b"x"],
                    syntax(None, b"closing paren expected"),
                ),
                (
                    raw_argv![b"test", b"(", b")"],
                    syntax(None, b"closing paren expected"),
                ),
                (
                    raw_argv![b"test", b"(", b"-n", b")"],
                    syntax(None, b"closing paren expected"),
                ),
                (
                    raw_argv![b"test", b"(", b"x", b")", b"extra"],
                    syntax(Some(b"extra"), b"unknown operand"),
                ),
                (
                    raw_argv![b"test", b"x", b"y"],
                    syntax(Some(b"y"), b"unknown operand"),
                ),
                (
                    raw_argv![b"test", b"x", b""],
                    syntax(None, b"unknown operand"),
                ),
                (
                    raw_argv![b"test", b"x", b")"],
                    syntax(Some(b")"), b"unknown operand"),
                ),
            ];

            for (argv, expected) in cases {
                assert_eq!(evaluate(&argv, &runtime), Err(expected), "argv: {argv:?}");
            }
            assert!(runtime.calls.borrow().is_empty());
        }
    }

    mod bytes_diagnostics {
        use super::*;

        #[test]
        fn non_utf8_operands_paths_and_string_ordering() {
            let runtime = FakeRuntime::default();
            let cases = [
                (raw_argv![b"test", b"\xff"], Ok(true)),
                (raw_argv![b"test", b"\xff", b"=", b"\xff"], Ok(true)),
                (raw_argv![b"test", b"\xff", b"!=", b"\xfe"], Ok(true)),
                (raw_argv![b"test", b"\x80", b">", b"\x7f"], Ok(true)),
                (raw_argv![b"test", b"\xfe", b"<", b"\xff"], Ok(true)),
                (raw_argv![b"test", b"\xff", b"<", b"\xfe"], Ok(false)),
                (raw_argv![b"test", b"a", b"<", b"a\xff"], Ok(true)),
                (raw_argv![b"test", b"a\xff", b">", b"a"], Ok(true)),
                (raw_argv![b"test", b"-n", b"\xff"], Ok(true)),
            ];

            for (argv, expected) in cases {
                assert_eq!(evaluate(&argv, &runtime), expected, "argv: {argv:?}");
            }

            assert_eq!(
                evaluate(&raw_argv![b"test", b"\xff", b"-eq", b"1"], &runtime),
                Err(direct_diagnostic(b"\xff", b"invalid"))
            );

            let mut stderr = Vec::new();
            assert_eq!(
                run_with(
                    &raw_argv![b"/tmp/pr\xfeog", b"\xff", b"-eq", b"1"],
                    &runtime,
                    &mut stderr
                ),
                2
            );
            assert_eq!(stderr, b"pr\xfeog: \xff: invalid\n");
            assert!(runtime.calls.borrow().is_empty());
        }

        #[test]
        fn raw_program_basename_and_bracket_alias() {
            let basename_cases: &[(&[u8], &[u8])] = &[
                (b"test", b"test"),
                (b"./main", b"main"),
                (b"/usr/local/bin/test", b"test"),
                (b"[", b"["),
                (b"/tmp/[", b"["),
                (b"two//components", b"components"),
                (b"trailing/", b""),
                (b"/", b""),
                (b"", b""),
                (b"/tmp/\xff", b"\xff"),
            ];
            for (argv0, expected) in basename_cases {
                let argv0 = os(argv0);
                assert_eq!(program_basename(argv0.as_os_str()), *expected);
            }

            let runtime = FakeRuntime::default();
            let valid_cases = [
                (raw_argv![b"[", b"]"], 1),
                (raw_argv![b"[", b"value", b"]"], 0),
                (raw_argv![b"/tmp/[", b"", b"]"], 1),
                (raw_argv![b"[", b"\xff", b"]"], 0),
                (raw_argv![b"[", b"]", b"]"], 0),
                (raw_argv![b"/tmp/[/", b"]"], 0),
                (raw_argv![b"not[", b"]"], 0),
            ];
            for (argv, expected_status) in valid_cases {
                let mut stderr = Vec::new();
                assert_eq!(
                    run_with(&argv, &runtime, &mut stderr),
                    expected_status,
                    "argv: {argv:?}"
                );
                assert!(stderr.is_empty(), "argv: {argv:?}");
            }

            let missing_cases = [
                raw_argv![b"["],
                raw_argv![b"[", b"value"],
                raw_argv![b"./[", b"]x"],
            ];
            for argv in missing_cases {
                let mut stderr = Vec::new();
                assert_eq!(run_with(&argv, &runtime, &mut stderr), 2);
                assert_eq!(stderr, b"[: missing ]\n", "argv: {argv:?}");
            }
            assert!(runtime.calls.borrow().is_empty());
        }

        #[test]
        fn every_diagnostic_has_exact_bytes_newline_and_status() {
            let cases = vec![
                (
                    b"test".to_vec(),
                    syntax(None, b"missing ]"),
                    b"test: missing ]\n".to_vec(),
                ),
                (
                    b"test".to_vec(),
                    syntax(None, b"argument expected"),
                    b"test: argument expected\n".to_vec(),
                ),
                (
                    b"test".to_vec(),
                    syntax(Some(b"-n"), b"argument expected"),
                    b"test: -n: argument expected\n".to_vec(),
                ),
                (
                    b"test".to_vec(),
                    syntax(None, b"closing paren expected"),
                    b"test: closing paren expected\n".to_vec(),
                ),
                (
                    b"test".to_vec(),
                    syntax(Some(b"extra"), b"unknown operand"),
                    b"test: extra: unknown operand\n".to_vec(),
                ),
                (
                    b"test".to_vec(),
                    syntax(Some(b""), b"unknown operand"),
                    b"test: unknown operand\n".to_vec(),
                ),
                (
                    b"test".to_vec(),
                    direct_diagnostic(b"12x", b"invalid"),
                    b"test: 12x: invalid\n".to_vec(),
                ),
                (
                    b"test".to_vec(),
                    direct_diagnostic(b"", b"invalid"),
                    b"test: : invalid\n".to_vec(),
                ),
                (
                    b"test".to_vec(),
                    direct_diagnostic(b"-1", b"too small"),
                    b"test: -1: too small\n".to_vec(),
                ),
                (
                    b"test".to_vec(),
                    direct_diagnostic(b"2147483648", b"too large"),
                    b"test: 2147483648: too large\n".to_vec(),
                ),
                (
                    b"test".to_vec(),
                    syntax(Some(b"-a"), b"not a binary operator"),
                    b"test: -a: not a binary operator\n".to_vec(),
                ),
                (
                    b"te\xfest".to_vec(),
                    syntax(Some(b"\xff"), b"unknown operand"),
                    b"te\xfest: \xff: unknown operand\n".to_vec(),
                ),
                (
                    Vec::new(),
                    syntax(None, b"argument expected"),
                    b": argument expected\n".to_vec(),
                ),
            ];

            for (program_name, diagnostic, expected) in cases {
                let mut stderr = Vec::new();
                assert_eq!(finish(&program_name, Err(diagnostic), &mut stderr), 2);
                assert_eq!(stderr, expected);
            }
        }
    }

    mod integers {
        use super::*;

        #[test]
        fn getnstr_accepts_source_number_syntax() {
            let cases: &[(&[u8], i8, &[u8])] = &[
                (b"0", 1, b"0"),
                (b"+0", 1, b"0"),
                (b"-0", 1, b"0"),
                (b"000000", 1, b"0"),
                (b"-000000", 1, b"0"),
                (b"1", 1, b"1"),
                (b"+1", 1, b"1"),
                (b"-1", -1, b"1"),
                (b"000123", 1, b"123"),
                (b"-000123", -1, b"123"),
                (b"000100", 1, b"100"),
                (b" 12", 1, b"12"),
                (b"\t12", 1, b"12"),
                (b"\n12", 1, b"12"),
                (b"\r12", 1, b"12"),
                (b"\x0b12", 1, b"12"),
                (b"\x0c12", 1, b"12"),
                (b"12 ", 1, b"12"),
                (b"12\t", 1, b"12"),
                (b"12\n", 1, b"12"),
                (b"12\r", 1, b"12"),
                (b"12\x0b", 1, b"12"),
                (b"12\x0c", 1, b"12"),
                (b" \t\n\r\x0b\x0c-00012\x0c\x0b\r\n\t ", -1, b"12"),
                (
                    b"+999999999999999999999999999999999999999999999",
                    1,
                    b"999999999999999999999999999999999999999999999",
                ),
            ];

            for &(value, sign, digits) in cases {
                assert_eq!(
                    getnstr(value),
                    Ok(NumberSlice { sign, digits }),
                    "value: {value:?}"
                );
            }

            // The source checks the pre-whitespace pointer rather than digit length.
            assert_eq!(
                getnstr(b"+ \t"),
                Ok(NumberSlice {
                    sign: 1,
                    digits: b""
                })
            );
            assert_eq!(
                getnstr(b"- \t"),
                Ok(NumberSlice {
                    sign: -1,
                    digits: b""
                })
            );
        }

        #[test]
        fn getnstr_rejects_every_invalid_form() {
            let invalid: &[&[u8]] = &[
                b"",
                b" ",
                b"\t\n\r\x0b\x0c",
                b"+",
                b"-",
                b"++1",
                b"--1",
                b"+-1",
                b"-+1",
                b"x",
                b"x1",
                b"1x",
                b"0x10",
                b"1 2",
                b"+ 1",
                b"- 1",
                b"1 +",
                b"1 \t x",
                b"\x801",
                b"1\x80",
                b"\xc2\xa01",
            ];

            for value in invalid {
                assert_eq!(
                    getnstr(value),
                    Err(direct_diagnostic(value, b"invalid")),
                    "value: {value:?}"
                );
            }
        }

        #[test]
        fn intcmp_handles_arbitrary_precision_and_all_relations() {
            let comparisons: &[(&[u8], &[u8], Ordering)] = &[
                (b"0", b"-0", Ordering::Equal),
                (b"+000", b"0000", Ordering::Equal),
                (b" \t+0012\r", b"12", Ordering::Equal),
                (b"-1", b"0", Ordering::Less),
                (b"1", b"-1", Ordering::Greater),
                (b"99", b"100", Ordering::Less),
                (b"100", b"99", Ordering::Greater),
                (b"900", b"800", Ordering::Greater),
                (b"-900", b"-800", Ordering::Less),
                (b"-800", b"-900", Ordering::Greater),
                (
                    b"10000000000000000000000000000000000000000",
                    b"9999999999999999999999999999999999999999",
                    Ordering::Greater,
                ),
                (
                    b"-10000000000000000000000000000000000000000",
                    b"-9999999999999999999999999999999999999999",
                    Ordering::Less,
                ),
                (
                    b"12345678901234567890123456789012345678901234567890",
                    b"12345678901234567890123456789012345678901234567890",
                    Ordering::Equal,
                ),
                (b"+ ", b"0", Ordering::Less),
                (b"- ", b"-1", Ordering::Greater),
            ];

            for &(left, right, expected) in comparisons {
                assert_eq!(
                    intcmp(left, right),
                    Ok(expected),
                    "left: {left:?}, right: {right:?}"
                );
            }

            assert_eq!(
                intcmp(b"bad", b"also-bad"),
                Err(direct_diagnostic(b"bad", b"invalid"))
            );
            assert_eq!(
                intcmp(b"1", b"bad"),
                Err(direct_diagnostic(b"bad", b"invalid"))
            );

            let runtime = FakeRuntime::default();
            let relations: &[(&[u8], &[u8], &[u8], bool)] = &[
                (b"0007", b"-eq", b"+7", true),
                (b"7", b"-eq", b"8", false),
                (b"7", b"-ne", b"8", true),
                (b"7", b"-ne", b"0007", false),
                (b"8", b"-ge", b"8", true),
                (b"7", b"-ge", b"8", false),
                (
                    b"10000000000000000000000000000000000000000",
                    b"-gt",
                    b"9999999999999999999999999999999999999999",
                    true,
                ),
                (b"-2", b"-gt", b"-1", false),
                (b"-2", b"-le", b"-1", true),
                (b"2", b"-le", b"1", false),
                (b"-2", b"-lt", b"-1", true),
                (b"2", b"-lt", b"1", false),
            ];

            for &(left, operator, right, expected) in relations {
                let argv = vec![os(b"test"), os(left), os(operator), os(right)];
                assert_eq!(evaluate(&argv, &runtime), Ok(expected), "argv: {argv:?}");
            }
            assert!(runtime.calls.borrow().is_empty());
        }

        #[test]
        fn getn_enforces_descriptor_bounds() {
            let valid: &[(&[u8], i32)] = &[
                (b"0", 0),
                (b"+0", 0),
                (b"-0", 0),
                (b"000000000000000000000000000000000000000000000", 0),
                (b"000000000000000000000000000000000000000000001", 1),
                (b"  +00042\t", 42),
                (b"2147483647", i32::MAX),
                (b"000000000000000000000000000000002147483647", i32::MAX),
            ];
            for &(value, expected) in valid {
                assert_eq!(getn(value), Ok(expected), "value: {value:?}");
            }

            let invalid: &[(&[u8], &[u8])] = &[
                (b"", b"invalid"),
                (b" ", b"invalid"),
                (b"+", b"invalid"),
                (b"-", b"invalid"),
                (b"+ \t", b"invalid"),
                (b"- \t", b"too small"),
                (b"-1", b"too small"),
                (b"-999999999999999999999999999999999999999999", b"too small"),
                (b"2147483648", b"too large"),
                (b"9999999999999999999999999999999", b"too large"),
                (
                    b"999999999999999999999999999999999999999999999999999999",
                    b"too large",
                ),
                (b"1x", b"invalid"),
                (b"\xff", b"invalid"),
            ];
            for &(value, message) in invalid {
                assert_eq!(
                    getn(value),
                    Err(direct_diagnostic(value, message)),
                    "value: {value:?}"
                );
            }

            let runtime = FakeRuntime::default();
            assert_eq!(
                evaluate(&raw_argv![b"test", b"-t", b"-1"], &runtime),
                Err(direct_diagnostic(b"-1", b"too small"))
            );
            assert_eq!(
                evaluate(&raw_argv![b"test", b"-t", b"2147483648"], &runtime),
                Err(direct_diagnostic(b"2147483648", b"too large"))
            );
            assert!(runtime.calls.borrow().is_empty());
        }

        #[test]
        fn tty_results_and_errors_use_the_runtime_boundary() {
            let mut runtime = FakeRuntime::default();
            runtime.tty_results.insert(0, FakeResult::Value(true));
            runtime.tty_results.insert(1, FakeResult::Value(false));
            runtime
                .tty_results
                .insert(9, FakeResult::Error(io::ErrorKind::NotFound));

            let cases: &[(&[u8], bool)] = &[(b"0", true), (b"+0001", false), (b"9", false)];
            for &(descriptor, expected) in cases {
                assert_eq!(
                    evaluate(&raw_argv![b"test", b"-t", descriptor], &runtime),
                    Ok(expected),
                    "descriptor: {descriptor:?}"
                );
            }

            assert_eq!(
                runtime.calls.into_inner(),
                vec![
                    RuntimeCall::Isatty(0),
                    RuntimeCall::Isatty(1),
                    RuntimeCall::Isatty(9),
                ]
            );
        }
    }

    mod file_predicates {
        use super::*;

        #[test]
        fn stat_lstat_symlink_and_failure_paths() {
            let mut runtime = FakeRuntime::default();
            runtime.stats.insert(
                b"link\xff".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Regular)),
            );
            runtime.lstats.insert(
                b"link\xff".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Symlink)),
            );
            runtime.lstats.insert(
                b"dangling".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Symlink)),
            );
            runtime.lstats.insert(
                b"ordinary".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Regular)),
            );
            runtime.lstats.insert(
                b"unreadable".to_vec(),
                FakeResult::Error(io::ErrorKind::PermissionDenied),
            );

            assert!(filstat(
                &runtime,
                os(b"link\xff").as_os_str(),
                Token::FilReg
            ));
            assert!(filstat(
                &runtime,
                os(b"link\xff").as_os_str(),
                Token::FilSym
            ));
            assert!(filstat(&runtime, OsStr::new("dangling"), Token::FilSym));
            assert!(!filstat(&runtime, OsStr::new("dangling"), Token::FilExist));
            assert!(!filstat(&runtime, OsStr::new("ordinary"), Token::FilSym));
            assert!(!filstat(&runtime, OsStr::new("unreadable"), Token::FilSym));
            assert!(!filstat(&runtime, OsStr::new("missing"), Token::FilReg));

            assert_eq!(
                runtime.calls.into_inner(),
                vec![
                    RuntimeCall::Stat(b"link\xff".to_vec()),
                    RuntimeCall::Lstat(b"link\xff".to_vec()),
                    RuntimeCall::Lstat(b"dangling".to_vec()),
                    RuntimeCall::Stat(b"dangling".to_vec()),
                    RuntimeCall::Lstat(b"ordinary".to_vec()),
                    RuntimeCall::Lstat(b"unreadable".to_vec()),
                    RuntimeCall::Stat(b"missing".to_vec()),
                ]
            );
        }

        #[test]
        fn access_modes_and_call_order() {
            let mut runtime = FakeRuntime::default();
            runtime.stats.insert(
                b"file".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Regular)),
            );
            runtime
                .access_results
                .insert((b"file".to_vec(), AccessMode::Read), FakeResult::Value(()));
            runtime.access_results.insert(
                (b"file".to_vec(), AccessMode::Write),
                FakeResult::Error(io::ErrorKind::PermissionDenied),
            );
            runtime.access_results.insert(
                (b"file".to_vec(), AccessMode::Execute),
                FakeResult::Value(()),
            );
            runtime.access_results.insert(
                (b"file".to_vec(), AccessMode::Exists),
                FakeResult::Error(io::ErrorKind::NotFound),
            );
            runtime.access_results.insert(
                (b"missing".to_vec(), AccessMode::Read),
                FakeResult::Value(()),
            );

            let cases = [
                (Token::FilRd, true),
                (Token::FilWr, false),
                (Token::FilEx, true),
                (Token::FilExist, false),
            ];
            for (token, expected) in cases {
                assert_eq!(
                    filstat(&runtime, OsStr::new("file"), token),
                    expected,
                    "token: {token:?}"
                );
            }
            assert!(!filstat(&runtime, OsStr::new("missing"), Token::FilRd));

            assert_eq!(
                runtime.calls.into_inner(),
                vec![
                    RuntimeCall::Stat(b"file".to_vec()),
                    RuntimeCall::Access(b"file".to_vec(), AccessMode::Read),
                    RuntimeCall::Stat(b"file".to_vec()),
                    RuntimeCall::Access(b"file".to_vec(), AccessMode::Write),
                    RuntimeCall::Stat(b"file".to_vec()),
                    RuntimeCall::Access(b"file".to_vec(), AccessMode::Execute),
                    RuntimeCall::Stat(b"file".to_vec()),
                    RuntimeCall::Access(b"file".to_vec(), AccessMode::Exists),
                    RuntimeCall::Stat(b"missing".to_vec()),
                ]
            );
        }

        #[test]
        fn every_file_kind_and_source_socket_quirk() {
            let mut runtime = FakeRuntime::default();
            let kinds: &[(&[u8], FileKind)] = &[
                (b"regular", FileKind::Regular),
                (b"directory", FileKind::Directory),
                (b"character", FileKind::CharacterDevice),
                (b"block", FileKind::BlockDevice),
                (b"fifo", FileKind::Fifo),
                (b"socket", FileKind::Socket),
                (b"symlink", FileKind::Symlink),
                (b"other", FileKind::Other),
            ];
            for &(path, kind) in kinds {
                runtime
                    .stats
                    .insert(path.to_vec(), FakeResult::Value(sample_stat(kind)));
            }

            let predicates = [
                Token::FilReg,
                Token::FilDir,
                Token::FilCdev,
                Token::FilBdev,
                Token::FilFifo,
                Token::FilSock,
            ];
            for &(path, kind) in kinds {
                for predicate in predicates {
                    let expected = matches!(
                        (predicate, kind),
                        (Token::FilReg, FileKind::Regular)
                            | (Token::FilDir, FileKind::Directory)
                            | (Token::FilCdev, FileKind::CharacterDevice)
                            | (Token::FilBdev, FileKind::BlockDevice)
                            | (Token::FilFifo, FileKind::Fifo)
                            | (Token::FilSock, FileKind::Fifo)
                    );
                    assert_eq!(
                        filstat(&runtime, os(path).as_os_str(), predicate),
                        expected,
                        "path: {path:?}, kind: {kind:?}, predicate: {predicate:?}"
                    );
                }
            }

            assert!(
                filstat(&runtime, OsStr::new("fifo"), Token::FilSock),
                "the source implements -S as a FIFO test"
            );
            assert!(
                !filstat(&runtime, OsStr::new("socket"), Token::FilSock),
                "the source does not recognize sockets for -S"
            );
            assert!(runtime
                .calls
                .borrow()
                .iter()
                .all(|call| matches!(call, RuntimeCall::Stat(_))));
        }

        #[test]
        fn mode_size_and_effective_ownership_predicates() {
            let mut runtime = FakeRuntime {
                effective_uid: 42,
                effective_gid: 84,
                ..FakeRuntime::default()
            };

            let mut all_bits = sample_stat(FileKind::Regular);
            all_bits.mode = 0o7000;
            runtime
                .stats
                .insert(b"all-bits".to_vec(), FakeResult::Value(all_bits));

            let mut no_special_bits = sample_stat(FileKind::Regular);
            no_special_bits.mode = 0o0777;
            runtime.stats.insert(
                b"no-special-bits".to_vec(),
                FakeResult::Value(no_special_bits),
            );

            let mut nonempty_directory = sample_stat(FileKind::Directory);
            nonempty_directory.size = 1;
            runtime.stats.insert(
                b"nonempty-directory".to_vec(),
                FakeResult::Value(nonempty_directory),
            );
            runtime.stats.insert(
                b"empty".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Regular)),
            );

            let mut owned = sample_stat(FileKind::Regular);
            owned.uid = 42;
            owned.gid = 84;
            runtime
                .stats
                .insert(b"owned".to_vec(), FakeResult::Value(owned));

            let mut foreign = sample_stat(FileKind::Regular);
            foreign.uid = 43;
            foreign.gid = 85;
            runtime
                .stats
                .insert(b"foreign".to_vec(), FakeResult::Value(foreign));

            for token in [Token::FilSuid, Token::FilSgid, Token::FilSticky] {
                assert!(filstat(&runtime, OsStr::new("all-bits"), token));
                assert!(!filstat(&runtime, OsStr::new("no-special-bits"), token));
            }
            assert!(filstat(
                &runtime,
                OsStr::new("nonempty-directory"),
                Token::FilGz
            ));
            assert!(!filstat(&runtime, OsStr::new("empty"), Token::FilGz));

            runtime.calls.replace(Vec::new());
            assert!(filstat(&runtime, OsStr::new("owned"), Token::FilUid));
            assert!(!filstat(&runtime, OsStr::new("foreign"), Token::FilUid));
            assert!(filstat(&runtime, OsStr::new("owned"), Token::FilGid));
            assert!(!filstat(&runtime, OsStr::new("foreign"), Token::FilGid));
            assert!(!filstat(&runtime, OsStr::new("missing"), Token::FilUid));
            assert!(!filstat(&runtime, OsStr::new("missing"), Token::FilGid));

            assert_eq!(
                runtime.calls.into_inner(),
                vec![
                    RuntimeCall::Stat(b"owned".to_vec()),
                    RuntimeCall::EffectiveUid,
                    RuntimeCall::Stat(b"foreign".to_vec()),
                    RuntimeCall::EffectiveUid,
                    RuntimeCall::Stat(b"owned".to_vec()),
                    RuntimeCall::EffectiveGid,
                    RuntimeCall::Stat(b"foreign".to_vec()),
                    RuntimeCall::EffectiveGid,
                    RuntimeCall::Stat(b"missing".to_vec()),
                    RuntimeCall::Stat(b"missing".to_vec()),
                ]
            );
        }

        #[test]
        fn mtime_comparison_uses_whole_seconds() {
            let mut runtime = FakeRuntime::default();
            let mut old = sample_stat(FileKind::Regular);
            old.mtime_secs = 100;
            runtime
                .stats
                .insert(b"old".to_vec(), FakeResult::Value(old.clone()));

            let mut new = old.clone();
            new.mtime_secs = 101;
            runtime
                .stats
                .insert(b"new".to_vec(), FakeResult::Value(new));

            // FileStat deliberately has no subsecond field; only this second value participates.
            let mut same_second = old;
            same_second.mode = 0o7777;
            same_second.size = 999;
            same_second.device = 999;
            same_second.inode = 999;
            runtime
                .stats
                .insert(b"same-second".to_vec(), FakeResult::Value(same_second));

            assert_eq!(
                evaluate(&raw_argv![b"test", b"new", b"-nt", b"old"], &runtime),
                Ok(true)
            );
            assert_eq!(
                evaluate(&raw_argv![b"test", b"old", b"-nt", b"new"], &runtime),
                Ok(false)
            );
            assert_eq!(
                evaluate(&raw_argv![b"test", b"old", b"-ot", b"new"], &runtime),
                Ok(true)
            );
            assert_eq!(
                evaluate(&raw_argv![b"test", b"new", b"-ot", b"old"], &runtime),
                Ok(false)
            );
            assert_eq!(
                evaluate(
                    &raw_argv![b"test", b"old", b"-nt", b"same-second"],
                    &runtime
                ),
                Ok(false)
            );
            assert_eq!(
                evaluate(
                    &raw_argv![b"test", b"old", b"-ot", b"same-second"],
                    &runtime
                ),
                Ok(false)
            );

            runtime.calls.replace(Vec::new());
            assert!(!newerf(
                &runtime,
                OsStr::new("missing-left"),
                OsStr::new("old")
            ));
            assert!(!olderf(
                &runtime,
                OsStr::new("old"),
                OsStr::new("missing-right")
            ));
            assert_eq!(
                runtime.calls.into_inner(),
                vec![
                    RuntimeCall::Stat(b"missing-left".to_vec()),
                    RuntimeCall::Stat(b"old".to_vec()),
                    RuntimeCall::Stat(b"missing-right".to_vec()),
                ]
            );
        }

        #[test]
        fn file_identity_uses_device_and_inode() {
            let mut runtime = FakeRuntime::default();
            let mut left = sample_stat(FileKind::Regular);
            left.device = 7;
            left.inode = 11;
            runtime
                .stats
                .insert(b"left".to_vec(), FakeResult::Value(left.clone()));

            let mut same = sample_stat(FileKind::Directory);
            same.device = 7;
            same.inode = 11;
            same.mtime_secs = 999;
            runtime
                .stats
                .insert(b"same".to_vec(), FakeResult::Value(same));

            let mut other_device = left.clone();
            other_device.device = 8;
            runtime
                .stats
                .insert(b"other-device".to_vec(), FakeResult::Value(other_device));

            let mut other_inode = left;
            other_inode.inode = 12;
            runtime
                .stats
                .insert(b"other-inode".to_vec(), FakeResult::Value(other_inode));

            assert_eq!(
                evaluate(&raw_argv![b"test", b"left", b"-ef", b"same"], &runtime),
                Ok(true)
            );
            assert_eq!(
                evaluate(
                    &raw_argv![b"test", b"left", b"-ef", b"other-device"],
                    &runtime
                ),
                Ok(false)
            );
            assert_eq!(
                evaluate(
                    &raw_argv![b"test", b"left", b"-ef", b"other-inode"],
                    &runtime
                ),
                Ok(false)
            );

            runtime.calls.replace(Vec::new());
            assert!(!equalf(
                &runtime,
                OsStr::new("missing-left"),
                OsStr::new("left")
            ));
            assert!(!equalf(
                &runtime,
                OsStr::new("left"),
                OsStr::new("missing-right")
            ));
            assert_eq!(
                runtime.calls.into_inner(),
                vec![
                    RuntimeCall::Stat(b"missing-left".to_vec()),
                    RuntimeCall::Stat(b"left".to_vec()),
                    RuntimeCall::Stat(b"missing-right".to_vec()),
                ]
            );
        }
    }

    mod top_level {
        use super::*;

        #[test]
        fn outcomes_map_to_zero_one_and_two() {
            let runtime = FakeRuntime::default();
            let cases: &[(Vec<OsString>, i32, &[u8])] = &[
                (raw_argv![b"test", b"value"], 0, b""),
                (raw_argv![b"test"], 1, b""),
                (raw_argv![b"./[", b"value"], 2, b"[: missing ]\n"),
            ];

            for (argv, expected_status, expected_stderr) in cases {
                let mut stderr = Vec::new();
                assert_eq!(
                    run_with(argv, &runtime, &mut stderr),
                    *expected_status,
                    "argv: {argv:?}"
                );
                assert_eq!(stderr, *expected_stderr, "argv: {argv:?}");
            }
            assert!(runtime.calls.borrow().is_empty());
        }

        #[test]
        fn ordinary_runtime_failures_are_silent() {
            let mut runtime = FakeRuntime::default();
            runtime.stats.insert(
                b"denied".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Regular)),
            );
            runtime.access_results.insert(
                (b"denied".to_vec(), AccessMode::Read),
                FakeResult::Error(io::ErrorKind::PermissionDenied),
            );

            let cases = [
                raw_argv![b"test", b"-f", b"missing"],
                raw_argv![b"test", b"-h", b"missing-link"],
                raw_argv![b"test", b"-r", b"denied"],
                raw_argv![b"test", b"-t", b"9"],
                raw_argv![b"test", b"missing-left", b"-nt", b"missing-right"],
            ];
            for argv in cases {
                let mut stderr = Vec::new();
                assert_eq!(run_with(&argv, &runtime, &mut stderr), 1, "argv: {argv:?}");
                assert!(stderr.is_empty(), "argv: {argv:?}");
            }

            assert_eq!(
                runtime.calls.into_inner(),
                vec![
                    RuntimeCall::Stat(b"missing".to_vec()),
                    RuntimeCall::Lstat(b"missing-link".to_vec()),
                    RuntimeCall::Stat(b"denied".to_vec()),
                    RuntimeCall::Access(b"denied".to_vec(), AccessMode::Read),
                    RuntimeCall::Isatty(9),
                    RuntimeCall::Stat(b"missing-left".to_vec()),
                ]
            );
        }

        #[test]
        fn logical_evaluation_does_not_skip_runtime_calls() {
            let mut runtime = FakeRuntime::default();
            runtime.stats.insert(
                b"file".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Regular)),
            );
            runtime.stats.insert(
                b"directory".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Directory)),
            );

            assert_eq!(
                evaluate(
                    &raw_argv![b"test", b"-f", b"directory", b"-a", b"-f", b"file"],
                    &runtime
                ),
                Ok(false)
            );
            assert_eq!(
                runtime.calls.replace(Vec::new()),
                vec![
                    RuntimeCall::Stat(b"directory".to_vec()),
                    RuntimeCall::Stat(b"file".to_vec()),
                ]
            );

            assert_eq!(
                evaluate(
                    &raw_argv![b"test", b"-f", b"file", b"-o", b"-f", b"missing"],
                    &runtime
                ),
                Ok(true)
            );
            assert_eq!(
                runtime.calls.into_inner(),
                vec![
                    RuntimeCall::Stat(b"file".to_vec()),
                    RuntimeCall::Stat(b"missing".to_vec()),
                ]
            );
        }

        #[test]
        fn process_contract_writes_only_fatal_stderr() {
            #[derive(Default)]
            struct RejectingWriter {
                write_attempts: usize,
            }

            impl Write for RejectingWriter {
                fn write(&mut self, _buffer: &[u8]) -> io::Result<usize> {
                    self.write_attempts += 1;
                    Err(io::Error::from(io::ErrorKind::BrokenPipe))
                }

                fn flush(&mut self) -> io::Result<()> {
                    Ok(())
                }
            }

            let runtime = FakeRuntime::default();
            let mut stderr = RejectingWriter::default();
            assert_eq!(
                run_with(&raw_argv![b"test", b"value"], &runtime, &mut stderr),
                0
            );
            assert_eq!(run_with(&raw_argv![b"test", b""], &runtime, &mut stderr), 1);
            assert_eq!(stderr.write_attempts, 0);

            assert_eq!(
                run_with(&raw_argv![b"[", b"value"], &runtime, &mut stderr),
                2
            );
            assert_eq!(stderr.write_attempts, 1);
            assert!(runtime.calls.borrow().is_empty());
        }
    }

    mod repair_regressions {
        use super::*;

        fn runtime() -> FakeRuntime {
            let mut runtime = FakeRuntime::default();
            runtime.stats.insert(
                b"file".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Regular)),
            );
            runtime.stats.insert(
                b"dir".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Directory)),
            );
            runtime.stats.insert(
                b"locked".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Regular)),
            );
            runtime.lstats.insert(
                b"file".to_vec(),
                FakeResult::Value(sample_stat(FileKind::Regular)),
            );
            runtime
                .access_results
                .insert((b"file".to_vec(), AccessMode::Read), FakeResult::Value(()));
            runtime.tty_results.insert(1, FakeResult::Value(false));

            let mut new = sample_stat(FileKind::Regular);
            new.mtime_secs = 20;
            runtime
                .stats
                .insert(b"new".to_vec(), FakeResult::Value(new));
            let mut old = sample_stat(FileKind::Regular);
            old.mtime_secs = 10;
            runtime
                .stats
                .insert(b"old".to_vec(), FakeResult::Value(old));
            runtime
        }

        fn assert_silent_status(argv: Vec<OsString>, expected: i32) {
            let mut stderr = Vec::new();
            assert_eq!(run_with(&argv, &runtime(), &mut stderr), expected);
            assert!(stderr.is_empty());
        }

        #[test]
        fn large_numbers() {
            assert_silent_status(raw_argv![b"test", b"1000000", b"-gt", b"999999"], 0);
        }

        #[test]
        fn directory_not_regular_file() {
            assert_silent_status(raw_argv![b"test", b"-f", b"dir"], 1);
        }

        #[test]
        fn terminal_test_fd1() {
            assert_silent_status(raw_argv![b"test", b"-t", b"1"], 1);
        }

        #[test]
        fn single_empty_string() {
            assert_silent_status(raw_argv![b"test", b""], 1);
        }

        #[test]
        fn complex_parentheses_with_and() {
            assert_silent_status(
                raw_argv![b"test", b"(", b"-f", b"file", b"-a", b"-r", b"file", b")"],
                0,
            );
        }

        #[test]
        fn or_operation_true() {
            assert_silent_status(
                raw_argv![b"test", b"-f", b"file", b"-o", b"-f", b"missing"],
                0,
            );
        }

        #[test]
        fn regular_file_not_symlink() {
            assert_silent_status(raw_argv![b"test", b"-h", b"file"], 1);
        }

        #[test]
        fn non_readable_file_test() {
            assert_silent_status(raw_argv![b"test", b"-r", b"locked"], 1);
        }

        #[test]
        fn empty_string_with_n() {
            assert_silent_status(raw_argv![b"test", b"-n", b""], 1);
        }

        #[test]
        fn setuid_bit_test_regular_file() {
            assert_silent_status(raw_argv![b"test", b"-u", b"file"], 1);
        }

        #[test]
        fn string_inequality() {
            assert_silent_status(raw_argv![b"test", b"hello", b"!=", b"world"], 0);
        }

        #[test]
        fn string_greater_than() {
            assert_silent_status(raw_argv![b"test", b"def", b">", b"abc"], 0);
        }

        #[test]
        fn or_operation_false() {
            assert_silent_status(
                raw_argv![b"test", b"-f", b"missing-a", b"-o", b"-f", b"missing-b"],
                1,
            );
        }

        #[test]
        fn regular_file_not_char_device() {
            assert_silent_status(raw_argv![b"test", b"-c", b"file"], 1);
        }

        #[test]
        fn newer_than_test() {
            assert_silent_status(raw_argv![b"test", b"new", b"-nt", b"old"], 0);
        }

        #[test]
        fn operator_table_and_integer_normalization_match_source() {
            assert_eq!(OPS.len(), 39);
            assert_eq!(
                lookup_op(OsStr::new("-n")).map(|op| (op.token, op.kind)),
                Some((Token::StrNz, TokenType::UnOp))
            );
            assert_eq!(
                lookup_op(OsStr::new("!=")).map(|op| (op.token, op.kind)),
                Some((Token::StrNe, TokenType::BinOp))
            );
            assert_eq!(
                getnstr(b" \t-00012\r\n"),
                Ok(NumberSlice {
                    sign: -1,
                    digits: b"12"
                })
            );
            assert_eq!(intcmp(b"-000", b"+0"), Ok(Ordering::Equal));
            assert_eq!(
                intcmp(
                    b"100000000000000000000000000000000000000",
                    b"99999999999999999999999999999999999999"
                ),
                Ok(Ordering::Greater)
            );
        }

        #[test]
        fn logical_operators_evaluate_both_runtime_sides() {
            let runtime = runtime();
            assert_eq!(
                evaluate(
                    &raw_argv![b"test", b"-f", b"file", b"-o", b"-f", b"missing"],
                    &runtime
                ),
                Ok(true)
            );
            assert_eq!(
                runtime.calls.into_inner(),
                vec![
                    RuntimeCall::Stat(b"file".to_vec()),
                    RuntimeCall::Stat(b"missing".to_vec())
                ]
            );
        }

        #[test]
        fn runtime_seams_preserve_lstat_and_access_order() {
            let runtime = runtime();
            assert!(!filstat(&runtime, OsStr::new("file"), Token::FilSym));
            assert_eq!(
                runtime.calls.replace(Vec::new()),
                vec![RuntimeCall::Lstat(b"file".to_vec())]
            );
            assert!(filstat(&runtime, OsStr::new("file"), Token::FilRd));
            assert_eq!(
                runtime.calls.into_inner(),
                vec![
                    RuntimeCall::Stat(b"file".to_vec()),
                    RuntimeCall::Access(b"file".to_vec(), AccessMode::Read)
                ]
            );
        }

        #[test]
        fn fatal_diagnostics_are_exact_but_boolean_false_is_silent() {
            let runtime = runtime();
            let mut stderr = Vec::new();
            assert_eq!(
                run_with(
                    &raw_argv![b"./test", b"bad", b"-eq", b"1"],
                    &runtime,
                    &mut stderr
                ),
                2
            );
            assert_eq!(stderr, b"test: bad: invalid\n");

            stderr.clear();
            assert_eq!(
                run_with(
                    &raw_argv![b"./test", b"-f", b"missing"],
                    &runtime,
                    &mut stderr
                ),
                1
            );
            assert!(stderr.is_empty());
        }
    }
}
