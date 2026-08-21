use std::cmp::Ordering;
use std::env;
use std::ffi::{OsStr, OsString};
use std::fs;
use std::io::{self, Write};
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::{FileTypeExt, MetadataExt};
use std::process::ExitCode;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Token {
    Eoi,
    FilRd,
    FilWr,
    FileX,
    FileXist,
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
    FilStck,
    FilNt,
    FilOt,
    FileEq,
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
    Unot,
    Band,
    Bor,
    Lparen,
    Rparen,
    Operand,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum TokenType {
    Unop,
    Binop,
    Bunop,
    Bbinop,
    Paren,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct TOp {
    op_text: &'static [u8],
    op_num: Token,
    op_type: TokenType,
}

static OPS: &[TOp] = &[
    TOp {
        op_text: b"-r",
        op_num: Token::FilRd,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-w",
        op_num: Token::FilWr,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-x",
        op_num: Token::FileX,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-e",
        op_num: Token::FileXist,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-f",
        op_num: Token::FilReg,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-d",
        op_num: Token::FilDir,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-c",
        op_num: Token::FilCdev,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-b",
        op_num: Token::FilBdev,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-p",
        op_num: Token::FilFifo,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-u",
        op_num: Token::FilSuid,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-g",
        op_num: Token::FilSgid,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-k",
        op_num: Token::FilStck,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-s",
        op_num: Token::FilGz,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-t",
        op_num: Token::FilTt,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-z",
        op_num: Token::StrEz,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-n",
        op_num: Token::StrNz,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-h",
        op_num: Token::FilSym,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-O",
        op_num: Token::FilUid,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-G",
        op_num: Token::FilGid,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-L",
        op_num: Token::FilSym,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"-S",
        op_num: Token::FilSock,
        op_type: TokenType::Unop,
    },
    TOp {
        op_text: b"=",
        op_num: Token::StrEq,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"!=",
        op_num: Token::StrNe,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"<",
        op_num: Token::StrLt,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b">",
        op_num: Token::StrGt,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"-eq",
        op_num: Token::IntEq,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"-ne",
        op_num: Token::IntNe,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"-ge",
        op_num: Token::IntGe,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"-gt",
        op_num: Token::IntGt,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"-le",
        op_num: Token::IntLe,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"-lt",
        op_num: Token::IntLt,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"-nt",
        op_num: Token::FilNt,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"-ot",
        op_num: Token::FilOt,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"-ef",
        op_num: Token::FileEq,
        op_type: TokenType::Binop,
    },
    TOp {
        op_text: b"!",
        op_num: Token::Unot,
        op_type: TokenType::Bunop,
    },
    TOp {
        op_text: b"-a",
        op_num: Token::Band,
        op_type: TokenType::Bbinop,
    },
    TOp {
        op_text: b"-o",
        op_num: Token::Bor,
        op_type: TokenType::Bbinop,
    },
    TOp {
        op_text: b"(",
        op_num: Token::Lparen,
        op_type: TokenType::Paren,
    },
    TOp {
        op_text: b")",
        op_num: Token::Rparen,
        op_type: TokenType::Paren,
    },
];

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
enum AccessMode {
    Read,
    Write,
    Execute,
    Exists,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FileKind {
    Regular,
    Directory,
    CharacterDevice,
    BlockDevice,
    Fifo,
    Symlink,
    Socket,
    Other,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct FileStat {
    kind: FileKind,
    mode: u32,
    size: u64,
    uid: u32,
    gid: u32,
    dev: u64,
    ino: u64,
    mtime: i64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum BoundaryError {
    Io(io::ErrorKind),
    Nix(nix::errno::Errno),
}

trait System {
    fn stat(&self, path: &OsStr) -> Result<FileStat, BoundaryError>;
    fn lstat(&self, path: &OsStr) -> Result<FileStat, BoundaryError>;
    fn access(&self, path: &OsStr, mode: AccessMode) -> Result<(), BoundaryError>;
    fn isatty(&self, fd: i32) -> Result<bool, BoundaryError>;
    fn effective_uid(&self) -> u32;
    fn effective_gid(&self) -> u32;
}

#[derive(Clone, Copy, Debug, Default)]
struct RealSystem;

fn file_stat(metadata: fs::Metadata) -> FileStat {
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
    } else if file_type.is_symlink() {
        FileKind::Symlink
    } else if file_type.is_socket() {
        FileKind::Socket
    } else {
        FileKind::Other
    };

    FileStat {
        kind,
        mode: metadata.mode(),
        size: metadata.size(),
        uid: metadata.uid(),
        gid: metadata.gid(),
        dev: metadata.dev(),
        ino: metadata.ino(),
        mtime: metadata.mtime(),
    }
}

impl System for RealSystem {
    fn stat(&self, path: &OsStr) -> Result<FileStat, BoundaryError> {
        fs::metadata(path)
            .map(file_stat)
            .map_err(|error| BoundaryError::Io(error.kind()))
    }

    fn lstat(&self, path: &OsStr) -> Result<FileStat, BoundaryError> {
        fs::symlink_metadata(path)
            .map(file_stat)
            .map_err(|error| BoundaryError::Io(error.kind()))
    }

    fn access(&self, path: &OsStr, mode: AccessMode) -> Result<(), BoundaryError> {
        let flags = match mode {
            AccessMode::Read => nix::unistd::AccessFlags::R_OK,
            AccessMode::Write => nix::unistd::AccessFlags::W_OK,
            AccessMode::Execute => nix::unistd::AccessFlags::X_OK,
            AccessMode::Exists => nix::unistd::AccessFlags::F_OK,
        };
        nix::unistd::access(path, flags).map_err(BoundaryError::Nix)
    }

    fn isatty(&self, fd: i32) -> Result<bool, BoundaryError> {
        nix::unistd::isatty(fd).map_err(BoundaryError::Nix)
    }

    fn effective_uid(&self) -> u32 {
        nix::unistd::geteuid().as_raw()
    }

    fn effective_gid(&self) -> u32 {
        nix::unistd::getegid().as_raw()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Diagnostic {
    subject: Option<Vec<u8>>,
    message: &'static [u8],
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct NormalizedNumber<'a> {
    sign: i8,
    digits: &'a [u8],
}

fn basename(arg0: &OsStr) -> &[u8] {
    let bytes = arg0.as_bytes();
    bytes
        .iter()
        .rposition(|byte| *byte == b'/')
        .map_or(bytes, |index| &bytes[index + 1..])
}

fn find_op(input: &[u8]) -> Option<&'static TOp> {
    OPS.iter().find(|op| op.op_text == input)
}

fn t_lex(input: Option<&[u8]>) -> Token {
    match input {
        Some(input) => find_op(input).map_or(Token::Operand, |op| op.op_num),
        None => Token::Eoi,
    }
}

fn t_lex_type(input: Option<&[u8]>) -> Option<TokenType> {
    input.and_then(find_op).map(|op| op.op_type)
}

fn syntax(subject: Option<&[u8]>, message: &'static [u8]) -> Diagnostic {
    Diagnostic {
        subject: subject.filter(|value| !value.is_empty()).map(Vec::from),
        message,
    }
}

fn is_c_whitespace(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | b'\x0b' | b'\x0c' | b'\r')
}

fn getnstr(input: &[u8]) -> Result<NormalizedNumber<'_>, Diagnostic> {
    let mut cursor = 0;
    while input.get(cursor).is_some_and(|byte| is_c_whitespace(*byte)) {
        cursor += 1;
    }

    let mut sign = 1;
    match input.get(cursor) {
        Some(b'-') => {
            sign = -1;
            cursor += 1;
        }
        Some(b'+') => cursor += 1,
        _ => {}
    }

    while cursor + 1 < input.len() && input[cursor] == b'0' && input[cursor + 1].is_ascii_digit() {
        cursor += 1;
    }
    if input.get(cursor) == Some(&b'0') {
        sign = 1;
    }

    let start = cursor;
    while input.get(cursor).is_some_and(|byte| byte.is_ascii_digit()) {
        cursor += 1;
    }
    let end = cursor;

    while input.get(cursor).is_some_and(|byte| is_c_whitespace(*byte)) {
        cursor += 1;
    }

    if cursor != input.len() || start == input.len() {
        return Err(Diagnostic {
            subject: Some(input.to_vec()),
            message: b"invalid",
        });
    }

    Ok(NormalizedNumber {
        sign,
        digits: &input[start..end],
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

fn getn(input: &[u8]) -> Result<i32, Diagnostic> {
    let number = getnstr(input)?;
    let error = |message: &'static [u8]| Diagnostic {
        subject: Some(input.to_vec()),
        message,
    };

    if number.sign != 1 {
        return Err(error(b"too small"));
    }
    if number.digits.len() >= 32 {
        return Err(error(b"too large"));
    }
    if number.digits.is_empty() {
        return Err(error(b"invalid"));
    }

    number.digits.iter().try_fold(0_i32, |value, digit| {
        value
            .checked_mul(10)
            .and_then(|value| value.checked_add(i32::from(*digit - b'0')))
            .ok_or_else(|| error(b"too large"))
    })
}

struct Parser<'a, S: ?Sized> {
    args: &'a [OsString],
    cursor: usize,
    system: &'a S,
}

impl<'a, S: System + ?Sized> Parser<'a, S> {
    fn new(args: &'a [OsString], system: &'a S) -> Self {
        Self {
            args,
            cursor: 0,
            system,
        }
    }

    fn current_bytes(&self) -> Option<&[u8]> {
        self.args
            .get(self.cursor)
            .map(|arg| arg.as_os_str().as_bytes())
    }

    fn lex_current(&self) -> Token {
        t_lex(self.current_bytes())
    }

    fn advance(&mut self) {
        self.cursor = self
            .cursor
            .checked_add(1)
            .expect("argument cursor overflow");
    }

    fn advance_and_lex(&mut self) -> Token {
        self.advance();
        self.lex_current()
    }

    fn retreat(&mut self) {
        self.cursor = self
            .cursor
            .checked_sub(1)
            .expect("argument cursor underflow");
    }

    fn oexpr(&mut self, token: Token) -> Result<bool, Diagnostic> {
        let result = self.aexpr(token)?;

        if self.advance_and_lex() == Token::Bor {
            let rhs_token = self.advance_and_lex();
            let rhs = self.oexpr(rhs_token)?;
            Ok(rhs || result)
        } else {
            self.retreat();
            Ok(result)
        }
    }

    fn aexpr(&mut self, token: Token) -> Result<bool, Diagnostic> {
        let result = self.nexpr(token)?;

        if self.advance_and_lex() == Token::Band {
            let rhs_token = self.advance_and_lex();
            let rhs = self.aexpr(rhs_token)?;
            Ok(rhs && result)
        } else {
            self.retreat();
            Ok(result)
        }
    }

    fn nexpr(&mut self, token: Token) -> Result<bool, Diagnostic> {
        if token == Token::Unot {
            let next = self.advance_and_lex();
            return Ok(!self.nexpr(next)?);
        }

        self.primary(token)
    }

    fn primary(&mut self, token: Token) -> Result<bool, Diagnostic> {
        if token == Token::Eoi {
            return Err(syntax(None, b"argument expected"));
        }

        if token == Token::Lparen {
            let nested = self.advance_and_lex();
            let result = self.oexpr(nested)?;

            if self.advance_and_lex() != Token::Rparen {
                return Err(syntax(None, b"closing paren expected"));
            }
            return Ok(result);
        }

        let next = self
            .cursor
            .checked_add(1)
            .and_then(|index| self.args.get(index))
            .map(|arg| arg.as_os_str().as_bytes());
        if t_lex_type(next) == Some(TokenType::Binop) {
            return self.binop();
        }

        let unary = self
            .current_bytes()
            .and_then(find_op)
            .filter(|op| op.op_type == TokenType::Unop);
        if let Some(operator) = unary {
            self.advance();
            let operand = self
                .args
                .get(self.cursor)
                .ok_or_else(|| syntax(Some(operator.op_text), b"argument expected"))?;
            let bytes = operand.as_os_str().as_bytes();

            return match token {
                Token::StrEz => Ok(bytes.is_empty()),
                Token::StrNz => Ok(!bytes.is_empty()),
                Token::FilTt => {
                    let fd = getn(bytes)?;
                    Ok(matches!(self.system.isatty(fd), Ok(true)))
                }
                _ => Ok(self.filstat(operand.as_os_str(), token)),
            };
        }

        Ok(self
            .current_bytes()
            .is_some_and(|operand| !operand.is_empty()))
    }

    fn binop(&mut self) -> Result<bool, Diagnostic> {
        let left = self
            .args
            .get(self.cursor)
            .ok_or_else(|| syntax(None, b"argument expected"))?;
        self.advance();

        let operator = self
            .args
            .get(self.cursor)
            .map(|value| value.as_os_str().as_bytes());
        let op = operator
            .and_then(find_op)
            .filter(|op| op.op_type == TokenType::Binop)
            .ok_or_else(|| syntax(operator, b"not a binary operator"))?;
        self.advance();

        let right = self
            .args
            .get(self.cursor)
            .ok_or_else(|| syntax(Some(op.op_text), b"argument expected"))?;
        let left_path = left.as_os_str();
        let right_path = right.as_os_str();
        let left = left_path.as_bytes();
        let right = right_path.as_bytes();

        match op.op_num {
            Token::StrEq => Ok(left == right),
            Token::StrNe => Ok(left != right),
            Token::StrLt => Ok(left < right),
            Token::StrGt => Ok(left > right),
            Token::IntEq => Ok(intcmp(left, right)? == Ordering::Equal),
            Token::IntNe => Ok(intcmp(left, right)? != Ordering::Equal),
            Token::IntGe => Ok(intcmp(left, right)? != Ordering::Less),
            Token::IntGt => Ok(intcmp(left, right)? == Ordering::Greater),
            Token::IntLe => Ok(intcmp(left, right)? != Ordering::Greater),
            Token::IntLt => Ok(intcmp(left, right)? == Ordering::Less),
            Token::FilNt => Ok(self.newerf(left_path, right_path)),
            Token::FilOt => Ok(self.olderf(left_path, right_path)),
            Token::FileEq => Ok(self.equalf(left_path, right_path)),
            _ => Err(syntax(Some(op.op_text), b"not a binary operator")),
        }
    }

    fn filstat(&self, path: &OsStr, mode: Token) -> bool {
        if mode == Token::FilSym {
            return self
                .system
                .lstat(path)
                .is_ok_and(|stat| stat.kind == FileKind::Symlink);
        }

        let stat = match self.system.stat(path) {
            Ok(stat) => stat,
            Err(_) => return false,
        };

        match mode {
            Token::FilRd => self.system.access(path, AccessMode::Read).is_ok(),
            Token::FilWr => self.system.access(path, AccessMode::Write).is_ok(),
            Token::FileX => self.system.access(path, AccessMode::Execute).is_ok(),
            Token::FileXist => self.system.access(path, AccessMode::Exists).is_ok(),
            Token::FilReg => stat.kind == FileKind::Regular,
            Token::FilDir => stat.kind == FileKind::Directory,
            Token::FilCdev => stat.kind == FileKind::CharacterDevice,
            Token::FilBdev => stat.kind == FileKind::BlockDevice,
            Token::FilFifo | Token::FilSock => stat.kind == FileKind::Fifo,
            Token::FilSuid => stat.mode & 0o4000 != 0,
            Token::FilSgid => stat.mode & 0o2000 != 0,
            Token::FilStck => stat.mode & 0o1000 != 0,
            Token::FilGz => stat.size > 0,
            Token::FilUid => stat.uid == self.system.effective_uid(),
            Token::FilGid => stat.gid == self.system.effective_gid(),
            _ => true,
        }
    }

    fn newerf(&self, left: &OsStr, right: &OsStr) -> bool {
        let left = match self.system.stat(left) {
            Ok(stat) => stat,
            Err(_) => return false,
        };
        let right = match self.system.stat(right) {
            Ok(stat) => stat,
            Err(_) => return false,
        };

        left.mtime > right.mtime
    }

    fn olderf(&self, left: &OsStr, right: &OsStr) -> bool {
        let left = match self.system.stat(left) {
            Ok(stat) => stat,
            Err(_) => return false,
        };
        let right = match self.system.stat(right) {
            Ok(stat) => stat,
            Err(_) => return false,
        };

        left.mtime < right.mtime
    }

    fn equalf(&self, left: &OsStr, right: &OsStr) -> bool {
        let left = match self.system.stat(left) {
            Ok(stat) => stat,
            Err(_) => return false,
        };
        let right = match self.system.stat(right) {
            Ok(stat) => stat,
            Err(_) => return false,
        };

        left.dev == right.dev && left.ino == right.ino
    }
}

fn run<S: System + ?Sized>(argv: &[OsString], system: &S) -> Result<bool, Diagnostic> {
    let expression_end = if argv
        .first()
        .is_some_and(|arg0| basename(arg0.as_os_str()) == b"[")
    {
        if argv
            .last()
            .is_none_or(|argument| argument.as_os_str().as_bytes() != b"]")
        {
            return Err(syntax(None, b"missing ]"));
        }
        argv.len() - 1
    } else {
        argv.len()
    };
    let args = argv.get(1..expression_end).unwrap_or(&[]);

    match args.len() {
        0 => return Ok(false),
        1 => return Ok(!args[0].as_os_str().as_bytes().is_empty()),
        2 if args[0].as_os_str().as_bytes() == b"!" => {
            return Ok(args[1].as_os_str().as_bytes().is_empty());
        }
        3 if args[0].as_os_str().as_bytes() != b"!"
            && t_lex_type(Some(args[1].as_os_str().as_bytes())) == Some(TokenType::Binop) =>
        {
            return Parser::new(args, system).binop();
        }
        4 if args[0].as_os_str().as_bytes() == b"!"
            && t_lex_type(Some(args[2].as_os_str().as_bytes())) == Some(TokenType::Binop) =>
        {
            let result = Parser::new(&args[1..], system).binop()?;
            return Ok(!result);
        }
        _ => {}
    }

    let mut parser = Parser::new(args, system);
    let first = parser.lex_current();
    let result = parser.oexpr(first)?;

    if let Some(extra) = parser
        .cursor
        .checked_add(1)
        .and_then(|index| args.get(index))
    {
        return Err(syntax(
            Some(extra.as_os_str().as_bytes()),
            b"unknown operand",
        ));
    }

    Ok(result)
}

fn write_diagnostic<W: Write>(
    writer: &mut W,
    program: &[u8],
    diagnostic: &Diagnostic,
) -> io::Result<()> {
    writer.write_all(program)?;
    writer.write_all(b": ")?;
    if let Some(subject) = &diagnostic.subject {
        writer.write_all(subject)?;
        writer.write_all(b": ")?;
    }
    writer.write_all(diagnostic.message)?;
    writer.write_all(b"\n")
}

fn finish_cli<W: Write>(program: &[u8], outcome: Result<bool, Diagnostic>, stderr: &mut W) -> u8 {
    match outcome {
        Ok(true) => 0,
        Ok(false) => 1,
        Err(diagnostic) => {
            let _ = write_diagnostic(stderr, program, &diagnostic);
            2
        }
    }
}

fn main() -> ExitCode {
    let argv: Vec<OsString> = env::args_os().collect();
    let system = RealSystem;
    let program = argv
        .first()
        .map(|arg| basename(arg.as_os_str()))
        .unwrap_or_default();
    let outcome = run(&argv, &system);
    let mut stderr = io::stderr().lock();

    ExitCode::from(finish_cli(program, outcome, &mut stderr))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;
    use std::collections::HashMap;
    use std::os::unix::ffi::OsStringExt;

    fn argv(values: &[&[u8]]) -> Vec<OsString> {
        values
            .iter()
            .map(|value| OsString::from_vec(value.to_vec()))
            .collect()
    }

    fn file_stat_with(kind: FileKind, mode: u32) -> FileStat {
        FileStat {
            kind,
            mode,
            size: 0,
            uid: 0,
            gid: 0,
            dev: 0,
            ino: 0,
            mtime: 0,
        }
    }

    #[derive(Clone, Debug, Eq, PartialEq)]
    enum SystemCall {
        Stat(OsString),
        Lstat(OsString),
        Access(OsString, AccessMode),
        Isatty(i32),
        EffectiveUid,
        EffectiveGid,
    }

    #[derive(Default)]
    struct FakeSystem {
        stats: HashMap<OsString, Result<FileStat, BoundaryError>>,
        lstats: HashMap<OsString, Result<FileStat, BoundaryError>>,
        accesses: HashMap<(OsString, AccessMode), Result<(), BoundaryError>>,
        ttys: HashMap<i32, Result<bool, BoundaryError>>,
        effective_uid: Option<u32>,
        effective_gid: Option<u32>,
        calls: RefCell<Vec<SystemCall>>,
    }

    impl FakeSystem {
        fn set_stat(&mut self, path: OsString, result: Result<FileStat, BoundaryError>) {
            self.stats.insert(path, result);
        }

        fn set_lstat(&mut self, path: OsString, result: Result<FileStat, BoundaryError>) {
            self.lstats.insert(path, result);
        }

        fn set_access(
            &mut self,
            path: OsString,
            mode: AccessMode,
            result: Result<(), BoundaryError>,
        ) {
            self.accesses.insert((path, mode), result);
        }

        fn set_tty(&mut self, fd: i32, result: Result<bool, BoundaryError>) {
            self.ttys.insert(fd, result);
        }

        fn set_effective_ids(&mut self, uid: u32, gid: u32) {
            self.effective_uid = Some(uid);
            self.effective_gid = Some(gid);
        }

        fn calls(&self) -> Vec<SystemCall> {
            self.calls.borrow().clone()
        }
    }

    impl System for FakeSystem {
        fn stat(&self, path: &OsStr) -> Result<FileStat, BoundaryError> {
            self.calls
                .borrow_mut()
                .push(SystemCall::Stat(path.to_os_string()));
            *self
                .stats
                .get(path)
                .expect("missing configured stat result")
        }

        fn lstat(&self, path: &OsStr) -> Result<FileStat, BoundaryError> {
            self.calls
                .borrow_mut()
                .push(SystemCall::Lstat(path.to_os_string()));
            *self
                .lstats
                .get(path)
                .expect("missing configured lstat result")
        }

        fn access(&self, path: &OsStr, mode: AccessMode) -> Result<(), BoundaryError> {
            self.calls
                .borrow_mut()
                .push(SystemCall::Access(path.to_os_string(), mode));
            *self
                .accesses
                .get(&(path.to_os_string(), mode))
                .expect("missing configured access result")
        }

        fn isatty(&self, fd: i32) -> Result<bool, BoundaryError> {
            self.calls.borrow_mut().push(SystemCall::Isatty(fd));
            *self
                .ttys
                .get(&fd)
                .expect("missing configured isatty result")
        }

        fn effective_uid(&self) -> u32 {
            self.calls.borrow_mut().push(SystemCall::EffectiveUid);
            self.effective_uid
                .expect("missing configured effective UID")
        }

        fn effective_gid(&self) -> u32 {
            self.calls.borrow_mut().push(SystemCall::EffectiveGid);
            self.effective_gid
                .expect("missing configured effective GID")
        }
    }

    mod lexer_operator_table {
        use super::*;

        #[test]
        fn recognizes_every_source_operator_and_rejects_other_spellings() {
            let expected: &[(&[u8], Token, TokenType)] = &[
                (b"-r", Token::FilRd, TokenType::Unop),
                (b"-w", Token::FilWr, TokenType::Unop),
                (b"-x", Token::FileX, TokenType::Unop),
                (b"-e", Token::FileXist, TokenType::Unop),
                (b"-f", Token::FilReg, TokenType::Unop),
                (b"-d", Token::FilDir, TokenType::Unop),
                (b"-c", Token::FilCdev, TokenType::Unop),
                (b"-b", Token::FilBdev, TokenType::Unop),
                (b"-p", Token::FilFifo, TokenType::Unop),
                (b"-u", Token::FilSuid, TokenType::Unop),
                (b"-g", Token::FilSgid, TokenType::Unop),
                (b"-k", Token::FilStck, TokenType::Unop),
                (b"-s", Token::FilGz, TokenType::Unop),
                (b"-t", Token::FilTt, TokenType::Unop),
                (b"-z", Token::StrEz, TokenType::Unop),
                (b"-n", Token::StrNz, TokenType::Unop),
                (b"-h", Token::FilSym, TokenType::Unop),
                (b"-O", Token::FilUid, TokenType::Unop),
                (b"-G", Token::FilGid, TokenType::Unop),
                (b"-L", Token::FilSym, TokenType::Unop),
                (b"-S", Token::FilSock, TokenType::Unop),
                (b"=", Token::StrEq, TokenType::Binop),
                (b"!=", Token::StrNe, TokenType::Binop),
                (b"<", Token::StrLt, TokenType::Binop),
                (b">", Token::StrGt, TokenType::Binop),
                (b"-eq", Token::IntEq, TokenType::Binop),
                (b"-ne", Token::IntNe, TokenType::Binop),
                (b"-ge", Token::IntGe, TokenType::Binop),
                (b"-gt", Token::IntGt, TokenType::Binop),
                (b"-le", Token::IntLe, TokenType::Binop),
                (b"-lt", Token::IntLt, TokenType::Binop),
                (b"-nt", Token::FilNt, TokenType::Binop),
                (b"-ot", Token::FilOt, TokenType::Binop),
                (b"-ef", Token::FileEq, TokenType::Binop),
                (b"!", Token::Unot, TokenType::Bunop),
                (b"-a", Token::Band, TokenType::Bbinop),
                (b"-o", Token::Bor, TokenType::Bbinop),
                (b"(", Token::Lparen, TokenType::Paren),
                (b")", Token::Rparen, TokenType::Paren),
            ];

            assert_eq!(OPS.len(), expected.len());
            for (actual, &(text, token, token_type)) in OPS.iter().zip(expected) {
                assert_eq!(
                    *actual,
                    TOp {
                        op_text: text,
                        op_num: token,
                        op_type: token_type,
                    }
                );
                assert_eq!(find_op(text), Some(actual));
                assert_eq!(t_lex(Some(text)), token);
                assert_eq!(t_lex_type(Some(text)), Some(token_type));
            }

            assert_eq!(t_lex(None), Token::Eoi);
            assert_eq!(t_lex_type(None), None);
            for operand in [b"".as_slice(), b"-Q", b"-E", b"-l", b"==", b"-o\0"] {
                assert_eq!(find_op(operand), None);
                assert_eq!(t_lex(Some(operand)), Token::Operand);
                assert_eq!(t_lex_type(Some(operand)), None);
            }

            assert_eq!(t_lex(Some(b"-e")), Token::FileXist);
            assert_eq!(t_lex(Some(b"-h")), Token::FilSym);
            assert_eq!(t_lex(Some(b"-L")), Token::FilSym);
            assert_eq!(t_lex(Some(b"-O")), Token::FilUid);
            assert_eq!(t_lex(Some(b"-o")), Token::Bor);
            assert_eq!(t_lex_type(Some(b"-O")), Some(TokenType::Unop));
            assert_eq!(t_lex_type(Some(b"-o")), Some(TokenType::Bbinop));
        }
    }

    mod argument_count_rules {
        use super::*;

        #[test]
        fn handles_zero_one_and_two_operand_special_cases() {
            let system = FakeSystem::default();

            assert_eq!(run(&argv(&[b"test"]), &system), Ok(false));
            assert_eq!(run(&argv(&[b"test", b""]), &system), Ok(false));
            assert_eq!(run(&argv(&[b"test", b"value"]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"test", b"-z"]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"test", b"!"]), &system), Ok(true));

            assert_eq!(run(&argv(&[b"test", b"!", b""]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"test", b"!", b"value"]), &system), Ok(false));
            assert_eq!(run(&argv(&[b"test", b"-z", b""]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"test", b"-n", b"value"]), &system), Ok(true));
        }

        #[test]
        fn routes_forced_binary_forms_before_general_parsing() {
            let system = FakeSystem::default();

            assert_eq!(
                run(&argv(&[b"test", b"hello", b"!=", b"world"]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"1000000", b"-gt", b"999999"]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"-n", b"=", b"-n"]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"!", b"same", b"=", b"same"]), &system),
                Ok(false)
            );
            assert_eq!(
                run(&argv(&[b"test", b"!", b"left", b"=", b"right"]), &system),
                Ok(true)
            );
            assert_eq!(run(&argv(&[b"test", b"(", b"=", b")"]), &system), Ok(false));
            assert_eq!(
                run(&argv(&[b"test", b"!", b"(", b"=", b")"]), &system),
                Ok(true)
            );
        }

        #[test]
        fn unmatched_forms_fall_through_to_the_general_parser() {
            let system = FakeSystem::default();

            assert_eq!(
                run(&argv(&[b"test", b"left", b"unknown", b"right"]), &system),
                Err(syntax(Some(b"unknown"), b"unknown operand"))
            );
            assert_eq!(
                run(
                    &argv(&[b"test", b"", b"-a", b"value", b"-o", b"value"]),
                    &system
                ),
                Ok(true)
            );
        }
    }

    mod parser {
        use super::*;

        #[test]
        fn applies_negation_boolean_precedence_and_parentheses() {
            let system = FakeSystem::default();

            assert_eq!(
                run(&argv(&[b"test", b"!", b"!", b"value"]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"", b"-a", b"", b"-o", b"value"]), &system),
                Ok(true)
            );
            assert_eq!(
                run(
                    &argv(&[b"test", b"(", b"", b"-o", b"value", b")", b"-a", b"value"]),
                    &system
                ),
                Ok(true)
            );
            assert_eq!(
                run(
                    &argv(&[b"test", b"left", b"=", b"left", b"-a", b"-z", b""]),
                    &system
                ),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"value", b"-o", b"", b"-a", b""]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"(value)", b"-a", b"value"]), &system),
                Ok(true)
            );
        }

        #[test]
        fn evaluates_a_recursive_rhs_before_combining_truth_values() {
            let system = FakeSystem::default();
            let invalid = Err(syntax(Some(b"bad"), b"invalid"));

            assert_eq!(
                run(
                    &argv(&[b"test", b"value", b"-o", b"bad", b"-eq", b"nope"]),
                    &system
                ),
                invalid
            );
            assert_eq!(
                run(
                    &argv(&[b"test", b"", b"-a", b"bad", b"-eq", b"nope"]),
                    &system
                ),
                invalid
            );
        }

        #[test]
        fn evaluates_both_boolean_sides_in_source_order() {
            let true_left = OsString::from("true-left");
            let true_right = OsString::from("true-right");
            let false_left = OsString::from("false-left");
            let false_right = OsString::from("false-right");
            let mut system = FakeSystem::default();
            system.set_stat(true_left.clone(), Ok(file_stat_with(FileKind::Regular, 0)));
            system.set_stat(true_right.clone(), Ok(file_stat_with(FileKind::Regular, 0)));
            system.set_stat(
                false_left.clone(),
                Ok(file_stat_with(FileKind::Directory, 0)),
            );
            system.set_stat(
                false_right.clone(),
                Ok(file_stat_with(FileKind::Regular, 0)),
            );

            assert_eq!(
                run(
                    &argv(&[b"test", b"-f", b"true-left", b"-o", b"-f", b"true-right",]),
                    &system
                ),
                Ok(true)
            );
            assert_eq!(
                run(
                    &argv(&[b"test", b"-f", b"false-left", b"-a", b"-f", b"false-right",]),
                    &system
                ),
                Ok(false)
            );
            assert_eq!(
                system.calls(),
                vec![
                    SystemCall::Stat(true_left),
                    SystemCall::Stat(true_right),
                    SystemCall::Stat(false_left),
                    SystemCall::Stat(false_right),
                ]
            );
        }

        #[test]
        fn preserves_cursor_position_through_parentheses_and_forced_binary_lookahead() {
            let system = FakeSystem::default();
            let expression = argv(&[
                b"(",
                b"-n",
                b"=",
                b"-n",
                b"-a",
                b"value",
                b")",
                b"first-extra",
                b"later",
            ]);
            let mut parser = Parser::new(&expression, &system);
            let first = parser.lex_current();

            assert_eq!(parser.oexpr(first), Ok(true));
            assert_eq!(parser.cursor, 6);
            assert_eq!(parser.current_bytes(), Some(b")".as_slice()));
            assert_eq!(
                run(
                    &argv(&[
                        b"test",
                        b"(",
                        b"-n",
                        b"=",
                        b"-n",
                        b"-a",
                        b"value",
                        b")",
                        b"first-extra",
                        b"later",
                    ]),
                    &system
                ),
                Err(syntax(Some(b"first-extra"), b"unknown operand"))
            );
        }

        #[test]
        fn reports_source_compatible_parser_failures() {
            let system = FakeSystem::default();

            assert_eq!(
                run(&argv(&[b"test", b"value", b"-a"]), &system),
                Err(syntax(None, b"argument expected"))
            );
            assert_eq!(
                run(&argv(&[b"test", b"value", b"-o"]), &system),
                Err(syntax(None, b"argument expected"))
            );
            assert_eq!(
                run(&argv(&[b"test", b"value", b"-a", b"!"]), &system),
                Err(syntax(None, b"argument expected"))
            );
            assert_eq!(
                run(&argv(&[b"test", b"value", b"-a", b"("]), &system),
                Err(syntax(None, b"argument expected"))
            );
            assert_eq!(
                run(&argv(&[b"test", b"value", b"-a", b"-z"]), &system),
                Err(syntax(Some(b"-z"), b"argument expected"))
            );
            assert_eq!(
                run(&argv(&[b"test", b"value", b"-eq"]), &system),
                Err(syntax(Some(b"-eq"), b"argument expected"))
            );
            assert_eq!(
                run(&argv(&[b"test", b"(", b"value"]), &system),
                Err(syntax(None, b"closing paren expected"))
            );
            assert_eq!(
                run(&argv(&[b"test", b"(", b"value", b"not-close"]), &system),
                Err(syntax(None, b"closing paren expected"))
            );
            assert_eq!(
                run(&argv(&[b"test", b"(", b")"]), &system),
                Err(syntax(None, b"closing paren expected"))
            );
            assert_eq!(
                run(&argv(&[b"test", b"value", b"-o", b"(", b"value"]), &system),
                Err(syntax(None, b"closing paren expected"))
            );
            assert_eq!(
                run(
                    &argv(&[b"test", b"value", b"first-extra", b"later"]),
                    &system
                ),
                Err(syntax(Some(b"first-extra"), b"unknown operand"))
            );

            let no_args = argv(&[]);
            let mut parser = Parser::new(&no_args, &system);
            assert_eq!(parser.binop(), Err(syntax(None, b"argument expected")));

            let invalid_binary = argv(&[b"left", b"not-an-op", b"right"]);
            let mut parser = Parser::new(&invalid_binary, &system);
            assert_eq!(
                parser.binop(),
                Err(syntax(Some(b"not-an-op"), b"not a binary operator"))
            );
        }
    }

    mod byte_strings {
        use super::*;

        #[test]
        fn evaluates_empty_nonempty_and_all_string_operators() {
            let system = FakeSystem::default();

            assert_eq!(run(&argv(&[b"test", b""]), &system), Ok(false));
            assert_eq!(run(&argv(&[b"test", b"bytes"]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"test", b"-z", b""]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"test", b"-z", b"x"]), &system), Ok(false));
            assert_eq!(run(&argv(&[b"test", b"-n", b""]), &system), Ok(false));
            assert_eq!(run(&argv(&[b"test", b"-n", b"x"]), &system), Ok(true));
            assert_eq!(
                run(&argv(&[b"test", b"same", b"=", b"same"]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"hello", b"!=", b"world"]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"prefix", b"<", b"prefix-z"]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"def", b">", b"abc"]), &system),
                Ok(true)
            );
        }

        #[test]
        fn preserves_non_utf8_and_operator_looking_operands() {
            let system = FakeSystem::default();

            assert_eq!(run(&argv(&[b"test", &[0xff, 0x80]]), &system), Ok(true));
            assert_eq!(
                run(
                    &argv(&[b"test", &[0xff, 0x80], b"=", &[0xff, 0x80]]),
                    &system
                ),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", &[0xff], b">", &[0xfe, 0xff]]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"-z", b"=", b"-z"]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"-o", b"!=", b"-a"]), &system),
                Ok(true)
            );
        }
    }

    mod numeric_comparison {
        use super::*;

        fn invalid_number(subject: &[u8]) -> Diagnostic {
            Diagnostic {
                subject: Some(subject.to_vec()),
                message: b"invalid",
            }
        }

        #[test]
        fn compares_normalized_arbitrary_size_decimals() {
            assert_eq!(intcmp(b"1000000", b"999999"), Ok(Ordering::Greater));
            assert_eq!(
                intcmp(
                    b"999999999999999999999999999999999999999999",
                    b"1000000000000000000000000000000000000000000"
                ),
                Ok(Ordering::Less)
            );
            assert_eq!(intcmp(b" -00042 \t", b"-42"), Ok(Ordering::Equal));
            assert_eq!(intcmp(b"\t\n\x0b\x0c\r 42\x0b", b"42"), Ok(Ordering::Equal));
            assert_eq!(intcmp(b"-43", b"-42"), Ok(Ordering::Less));
            assert_eq!(intcmp(b"-000", b"+0"), Ok(Ordering::Equal));
            assert_eq!(intcmp(b"+000000001", b"1"), Ok(Ordering::Equal));
            assert_eq!(
                intcmp(
                    b"-999999999999999999999999999999999999999999",
                    b"-1000000000000000000000000000000000000000000"
                ),
                Ok(Ordering::Greater)
            );
        }

        #[test]
        fn evaluates_every_integer_relation_through_the_parser() {
            let system = FakeSystem::default();
            let value: &[u8] = b"99999999999999999999999999999999999999999999999999";
            let same_value: &[u8] = b" +00099999999999999999999999999999999999999999999999999 \t";
            let larger: &[u8] = b"100000000000000000000000000000000000000000000000000";
            let cases: &[(&[u8], &[u8], &[u8], bool)] = &[
                (value, b"-eq", same_value, true),
                (value, b"-eq", larger, false),
                (value, b"-ne", larger, true),
                (value, b"-ne", same_value, false),
                (larger, b"-ge", value, true),
                (value, b"-ge", larger, false),
                (larger, b"-gt", value, true),
                (value, b"-gt", same_value, false),
                (value, b"-le", larger, true),
                (larger, b"-le", value, false),
                (value, b"-lt", larger, true),
                (value, b"-lt", same_value, false),
            ];

            for &(left, operator, right, expected) in cases {
                assert_eq!(
                    run(&argv(&[b"test", left, operator, right]), &system),
                    Ok(expected),
                    "{left:?} {operator:?} {right:?}"
                );
            }
        }

        #[test]
        fn preserves_invalid_inputs_and_signed_whitespace_quirk() {
            assert_eq!(getnstr(b"").unwrap_err(), invalid_number(b""));
            assert_eq!(getnstr(b"12x").unwrap_err(), invalid_number(b"12x"));
            assert_eq!(getnstr(b" \t").unwrap_err(), invalid_number(b" \t"));
            assert_eq!(getnstr(b"+").unwrap_err(), invalid_number(b"+"));
            assert_eq!(getnstr(b"-").unwrap_err(), invalid_number(b"-"));
            assert_eq!(getnstr(&[0xa0]).unwrap_err(), invalid_number(&[0xa0]));

            assert_eq!(
                getnstr(b"- "),
                Ok(NormalizedNumber {
                    sign: -1,
                    digits: b"",
                })
            );
            assert_eq!(
                getnstr(b"+ "),
                Ok(NormalizedNumber {
                    sign: 1,
                    digits: b"",
                })
            );
            assert_eq!(intcmp(b"- \t", b"+ \r"), Ok(Ordering::Less));
            assert_eq!(intcmp(b"- ", b"-\t"), Ok(Ordering::Equal));

            let system = FakeSystem::default();
            assert_eq!(
                run(&argv(&[b"test", b"", b"-eq", b"0"]), &system),
                Err(invalid_number(b""))
            );
            assert_eq!(
                run(&argv(&[b"test", b"0", b"-lt", b"12x"]), &system),
                Err(invalid_number(b"12x"))
            );
            assert_eq!(
                run(&argv(&[b"test", &[0xff], b"-ne", b"also-invalid"]), &system),
                Err(invalid_number(&[0xff]))
            );
        }
    }

    mod descriptor_parsing {
        use super::*;

        fn descriptor_error(subject: &[u8], message: &'static [u8]) -> Diagnostic {
            Diagnostic {
                subject: Some(subject.to_vec()),
                message,
            }
        }

        #[test]
        fn accepts_descriptor_bounds_and_normalized_zero() {
            assert_eq!(getn(b"0"), Ok(0));
            assert_eq!(getn(b"2147483647"), Ok(i32::MAX));
            assert_eq!(getn(b" \t+2147483647\r"), Ok(i32::MAX));
            assert_eq!(getn(b"-0"), Ok(0));
            assert_eq!(getn(b"-000000"), Ok(0));

            let thirty_two_zeroes = [b'0'; 32];
            assert_eq!(getn(&thirty_two_zeroes), Ok(0));
        }

        #[test]
        fn reports_exact_invalid_too_small_and_too_large_failures() {
            assert_eq!(getn(b""), Err(descriptor_error(b"", b"invalid")));
            assert_eq!(getn(b"+ "), Err(descriptor_error(b"+ ", b"invalid")));
            assert_eq!(getn(b"12x"), Err(descriptor_error(b"12x", b"invalid")));
            assert_eq!(getn(b"-1"), Err(descriptor_error(b"-1", b"too small")));
            assert_eq!(getn(b"- "), Err(descriptor_error(b"- ", b"too small")));
            assert_eq!(
                getn(b"2147483648"),
                Err(descriptor_error(b"2147483648", b"too large"))
            );

            let thirty_one_digits = [b'9'; 31];
            let thirty_two_digits = [b'9'; 32];
            assert_eq!(
                getn(&thirty_one_digits),
                Err(descriptor_error(&thirty_one_digits, b"too large"))
            );
            assert_eq!(
                getn(&thirty_two_digits),
                Err(descriptor_error(&thirty_two_digits, b"too large"))
            );
        }

        #[test]
        fn routes_valid_descriptors_and_maps_isatty_failures_to_false() {
            let mut system = FakeSystem::default();
            system.set_tty(0, Ok(true));
            system.set_tty(7, Ok(false));
            system.set_tty(9, Err(BoundaryError::Nix(nix::errno::Errno::EBADF)));

            assert_eq!(run(&argv(&[b"test", b"-t", b"-0"]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"test", b"-t", b"7"]), &system), Ok(false));
            assert_eq!(run(&argv(&[b"test", b"-t", b"9"]), &system), Ok(false));
            assert_eq!(
                system.calls(),
                vec![
                    SystemCall::Isatty(0),
                    SystemCall::Isatty(7),
                    SystemCall::Isatty(9),
                ]
            );
        }

        #[test]
        fn rejects_bad_descriptors_before_calling_isatty() {
            let system = FakeSystem::default();

            assert_eq!(
                run(&argv(&[b"test", b"-t", b"+ "]), &system),
                Err(descriptor_error(b"+ ", b"invalid"))
            );
            assert_eq!(
                run(&argv(&[b"test", b"-t", b"-2"]), &system),
                Err(descriptor_error(b"-2", b"too small"))
            );
            assert_eq!(
                run(&argv(&[b"test", b"-t", b"2147483648"]), &system),
                Err(descriptor_error(b"2147483648", b"too large"))
            );
            assert!(system.calls().is_empty());
        }
    }

    mod filesystem_unary_predicates {
        use super::*;

        #[test]
        fn evaluates_reported_file_type_and_mode_cases() {
            let directory = OsString::from("directory");
            let regular = OsString::from("regular");
            let character = OsString::from("character");
            let symlink = OsString::from("symlink");
            let setuid = OsString::from("setuid");
            let mut system = FakeSystem::default();
            system.set_stat(
                directory.clone(),
                Ok(file_stat_with(FileKind::Directory, 0o755)),
            );
            system.set_stat(
                regular.clone(),
                Ok(file_stat_with(FileKind::Regular, 0o644)),
            );
            system.set_stat(
                character.clone(),
                Ok(file_stat_with(FileKind::CharacterDevice, 0o600)),
            );
            system.set_stat(
                setuid.clone(),
                Ok(file_stat_with(FileKind::Regular, 0o4644)),
            );
            system.set_lstat(
                regular.clone(),
                Ok(file_stat_with(FileKind::Regular, 0o644)),
            );
            system.set_lstat(
                symlink.clone(),
                Ok(file_stat_with(FileKind::Symlink, 0o777)),
            );

            assert_eq!(
                run(&argv(&[b"test", b"-f", b"directory"]), &system),
                Ok(false)
            );
            assert_eq!(run(&argv(&[b"test", b"-f", b"regular"]), &system), Ok(true));
            assert_eq!(
                run(&argv(&[b"test", b"-c", b"regular"]), &system),
                Ok(false)
            );
            assert_eq!(
                run(&argv(&[b"test", b"-c", b"character"]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"-h", b"regular"]), &system),
                Ok(false)
            );
            assert_eq!(run(&argv(&[b"test", b"-L", b"symlink"]), &system), Ok(true));
            assert_eq!(
                run(&argv(&[b"test", b"-u", b"regular"]), &system),
                Ok(false)
            );
            assert_eq!(run(&argv(&[b"test", b"-u", b"setuid"]), &system), Ok(true));
        }

        #[test]
        fn maps_missing_metadata_and_failed_read_access_to_false() {
            let missing = OsString::from("missing");
            let unreadable = OsString::from("unreadable");
            let mut system = FakeSystem::default();
            system.set_stat(missing, Err(BoundaryError::Io(io::ErrorKind::NotFound)));
            system.set_stat(
                unreadable.clone(),
                Ok(file_stat_with(FileKind::Regular, 0o200)),
            );
            system.set_access(
                unreadable,
                AccessMode::Read,
                Err(BoundaryError::Nix(nix::errno::Errno::EACCES)),
            );

            assert_eq!(
                run(&argv(&[b"test", b"-f", b"missing"]), &system),
                Ok(false)
            );
            assert_eq!(
                run(&argv(&[b"test", b"-r", b"unreadable"]), &system),
                Ok(false)
            );
        }

        #[test]
        fn delegates_read_write_execute_and_exists_to_kernel_access_results() {
            let path = OsString::from("path");
            let mut system = FakeSystem::default();
            system.set_stat(path.clone(), Ok(file_stat_with(FileKind::Regular, 0o777)));
            system.set_access(path.clone(), AccessMode::Read, Ok(()));
            system.set_access(
                path.clone(),
                AccessMode::Write,
                Err(BoundaryError::Nix(nix::errno::Errno::EACCES)),
            );
            system.set_access(path.clone(), AccessMode::Execute, Ok(()));
            system.set_access(
                path.clone(),
                AccessMode::Exists,
                Err(BoundaryError::Nix(nix::errno::Errno::ENOENT)),
            );

            let cases: &[(&[u8], bool)] =
                &[(b"-r", true), (b"-w", false), (b"-x", true), (b"-e", false)];
            for &(operator, expected) in cases {
                assert_eq!(
                    run(&argv(&[b"test", operator, b"path"]), &system),
                    Ok(expected),
                    "{operator:?}"
                );
            }

            assert_eq!(
                system.calls(),
                vec![
                    SystemCall::Stat(path.clone()),
                    SystemCall::Access(path.clone(), AccessMode::Read),
                    SystemCall::Stat(path.clone()),
                    SystemCall::Access(path.clone(), AccessMode::Write),
                    SystemCall::Stat(path.clone()),
                    SystemCall::Access(path.clone(), AccessMode::Execute),
                    SystemCall::Stat(path.clone()),
                    SystemCall::Access(path, AccessMode::Exists),
                ]
            );
        }

        #[test]
        fn stops_all_access_predicates_when_followed_stat_fails() {
            let missing = OsString::from("missing-access-path");
            let mut system = FakeSystem::default();
            system.set_stat(
                missing.clone(),
                Err(BoundaryError::Io(io::ErrorKind::PermissionDenied)),
            );

            for operator in [b"-r".as_slice(), b"-w", b"-x", b"-e"] {
                assert_eq!(
                    run(&argv(&[b"test", operator, b"missing-access-path"]), &system),
                    Ok(false),
                    "{operator:?}"
                );
            }

            assert_eq!(
                system.calls(),
                vec![
                    SystemCall::Stat(missing.clone()),
                    SystemCall::Stat(missing.clone()),
                    SystemCall::Stat(missing.clone()),
                    SystemCall::Stat(missing),
                ]
            );
        }

        #[test]
        fn evaluates_all_file_kinds_and_preserves_the_fifo_socket_quirk() {
            let cases: &[(&[u8], FileKind, &[u8])] = &[
                (b"regular", FileKind::Regular, b"-f"),
                (b"directory", FileKind::Directory, b"-d"),
                (b"character", FileKind::CharacterDevice, b"-c"),
                (b"block", FileKind::BlockDevice, b"-b"),
                (b"fifo", FileKind::Fifo, b"-p"),
            ];
            let mut system = FakeSystem::default();

            for &(path, kind, _) in cases {
                system.set_stat(
                    OsString::from_vec(path.to_vec()),
                    Ok(file_stat_with(kind, 0)),
                );
            }
            system.set_stat(
                OsString::from("socket"),
                Ok(file_stat_with(FileKind::Socket, 0)),
            );

            for &(path, _, operator) in cases {
                assert_eq!(
                    run(&argv(&[b"test", operator, path]), &system),
                    Ok(true),
                    "{operator:?} {path:?}"
                );
            }
            assert_eq!(
                run(&argv(&[b"test", b"-d", b"regular"]), &system),
                Ok(false)
            );
            assert_eq!(run(&argv(&[b"test", b"-S", b"fifo"]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"test", b"-S", b"socket"]), &system), Ok(false));
        }

        #[test]
        fn follows_symlinks_except_for_h_and_l() {
            let link = OsString::from("link");
            let dangling = OsString::from("dangling");
            let ordinary = OsString::from("ordinary");
            let missing = OsString::from("missing");
            let mut system = FakeSystem::default();

            system.set_stat(link.clone(), Ok(file_stat_with(FileKind::Regular, 0o644)));
            system.set_lstat(link.clone(), Ok(file_stat_with(FileKind::Symlink, 0o777)));
            system.set_stat(
                dangling.clone(),
                Err(BoundaryError::Io(io::ErrorKind::NotFound)),
            );
            system.set_lstat(
                dangling.clone(),
                Ok(file_stat_with(FileKind::Symlink, 0o777)),
            );
            system.set_lstat(ordinary, Ok(file_stat_with(FileKind::Regular, 0o644)));
            system.set_lstat(missing, Err(BoundaryError::Io(io::ErrorKind::NotFound)));

            assert_eq!(run(&argv(&[b"test", b"-f", b"link"]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"test", b"-h", b"link"]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"test", b"-L", b"link"]), &system), Ok(true));
            assert_eq!(
                run(&argv(&[b"test", b"-f", b"dangling"]), &system),
                Ok(false)
            );
            assert_eq!(
                run(&argv(&[b"test", b"-h", b"dangling"]), &system),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"-L", b"ordinary"]), &system),
                Ok(false)
            );
            assert_eq!(
                run(&argv(&[b"test", b"-h", b"missing"]), &system),
                Ok(false)
            );
        }

        #[test]
        fn evaluates_mode_size_and_effective_identity_predicates() {
            let matching = OsString::from("matching");
            let plain = OsString::from("plain");
            let mut system = FakeSystem::default();
            let mut matching_stat = file_stat_with(FileKind::Regular, 0o7000);
            matching_stat.size = 1;
            matching_stat.uid = 1001;
            matching_stat.gid = 1002;
            let mut plain_stat = file_stat_with(FileKind::Regular, 0);
            plain_stat.uid = 2001;
            plain_stat.gid = 2002;

            system.set_stat(matching, Ok(matching_stat));
            system.set_stat(plain, Ok(plain_stat));
            system.set_effective_ids(1001, 1002);

            for operator in [b"-u".as_slice(), b"-g", b"-k", b"-s", b"-O", b"-G"] {
                assert_eq!(
                    run(&argv(&[b"test", operator, b"matching"]), &system),
                    Ok(true),
                    "{operator:?}"
                );
                assert_eq!(
                    run(&argv(&[b"test", operator, b"plain"]), &system),
                    Ok(false),
                    "{operator:?}"
                );
            }
        }

        #[test]
        fn maps_every_metadata_failure_to_false_before_identity_queries() {
            let missing = OsString::from("missing");
            let missing_link = OsString::from("missing-link");
            let mut system = FakeSystem::default();
            system.set_stat(
                missing,
                Err(BoundaryError::Io(io::ErrorKind::PermissionDenied)),
            );
            system.set_lstat(
                missing_link,
                Err(BoundaryError::Io(io::ErrorKind::NotFound)),
            );

            for operator in [
                b"-f".as_slice(),
                b"-d",
                b"-c",
                b"-b",
                b"-p",
                b"-S",
                b"-u",
                b"-g",
                b"-k",
                b"-s",
                b"-O",
                b"-G",
            ] {
                assert_eq!(
                    run(&argv(&[b"test", operator, b"missing"]), &system),
                    Ok(false),
                    "{operator:?}"
                );
            }
            for operator in [b"-h".as_slice(), b"-L"] {
                assert_eq!(
                    run(&argv(&[b"test", operator, b"missing-link"]), &system),
                    Ok(false),
                    "{operator:?}"
                );
            }

            assert!(!system
                .calls()
                .iter()
                .any(|call| matches!(call, SystemCall::EffectiveUid | SystemCall::EffectiveGid)));
        }
    }

    mod file_binary_predicates {
        use super::*;

        fn relation_stat(mtime: i64, dev: u64, ino: u64) -> FileStat {
            FileStat {
                kind: FileKind::Regular,
                mode: 0o644,
                size: 0,
                uid: 0,
                gid: 0,
                dev,
                ino,
                mtime,
            }
        }

        #[test]
        fn compares_only_whole_second_mtimes_and_requires_strict_ordering() {
            let mut system = FakeSystem::default();
            system.set_stat(OsString::from("older"), Ok(relation_stat(-2, 1, 10)));
            system.set_stat(OsString::from("newer"), Ok(relation_stat(3, 1, 11)));
            system.set_stat(
                OsString::from("same-second-left"),
                Ok(relation_stat(7, 2, 20)),
            );
            system.set_stat(
                OsString::from("same-second-right"),
                Ok(relation_stat(7, 3, 30)),
            );

            let cases: &[(&[u8], &[u8], &[u8], bool)] = &[
                (b"newer", b"-nt", b"older", true),
                (b"older", b"-nt", b"newer", false),
                (b"same-second-left", b"-nt", b"same-second-right", false),
                (b"older", b"-ot", b"newer", true),
                (b"newer", b"-ot", b"older", false),
                (b"same-second-left", b"-ot", b"same-second-right", false),
            ];

            for &(left, operator, right, expected) in cases {
                assert_eq!(
                    run(&argv(&[b"test", left, operator, right]), &system),
                    Ok(expected),
                    "{left:?} {operator:?} {right:?}"
                );
            }
        }

        #[test]
        fn compares_both_device_and_inode_for_file_identity() {
            let mut system = FakeSystem::default();
            system.set_stat(OsString::from("original"), Ok(relation_stat(-10, 40, 50)));
            system.set_stat(OsString::from("hard-link"), Ok(relation_stat(99, 40, 50)));
            system.set_stat(
                OsString::from("other-device"),
                Ok(relation_stat(-10, 41, 50)),
            );
            system.set_stat(
                OsString::from("other-inode"),
                Ok(relation_stat(-10, 40, 51)),
            );

            let cases: &[(&[u8], &[u8], bool)] = &[
                (b"original", b"hard-link", true),
                (b"original", b"other-device", false),
                (b"original", b"other-inode", false),
                (b"original", b"original", true),
            ];

            for &(left, right, expected) in cases {
                assert_eq!(
                    run(&argv(&[b"test", left, b"-ef", right]), &system),
                    Ok(expected),
                    "{left:?} -ef {right:?}"
                );
            }
        }

        #[test]
        fn maps_first_and_second_metadata_failures_to_false() {
            let first_failure = OsString::from("first-failure");
            let present = OsString::from("present");
            let second_failure = OsString::from("second-failure");
            let mut system = FakeSystem::default();
            system.set_stat(
                first_failure.clone(),
                Err(BoundaryError::Io(io::ErrorKind::NotFound)),
            );
            system.set_stat(present.clone(), Ok(relation_stat(1, 2, 3)));
            system.set_stat(
                second_failure.clone(),
                Err(BoundaryError::Io(io::ErrorKind::PermissionDenied)),
            );

            for operator in [b"-nt".as_slice(), b"-ot", b"-ef"] {
                assert_eq!(
                    run(
                        &argv(&[b"test", b"first-failure", operator, b"unconfigured"]),
                        &system
                    ),
                    Ok(false),
                    "first failure for {operator:?}"
                );
                assert_eq!(
                    run(
                        &argv(&[b"test", b"present", operator, b"second-failure"]),
                        &system
                    ),
                    Ok(false),
                    "second failure for {operator:?}"
                );
            }

            assert_eq!(
                system.calls(),
                vec![
                    SystemCall::Stat(first_failure.clone()),
                    SystemCall::Stat(present.clone()),
                    SystemCall::Stat(second_failure.clone()),
                    SystemCall::Stat(first_failure.clone()),
                    SystemCall::Stat(present.clone()),
                    SystemCall::Stat(second_failure.clone()),
                    SystemCall::Stat(first_failure),
                    SystemCall::Stat(present),
                    SystemCall::Stat(second_failure),
                ]
            );
        }
    }

    mod cli_diagnostics {
        use super::*;

        fn assert_error_outcome(
            program: &[u8],
            outcome: Result<bool, Diagnostic>,
            expected_diagnostic: Diagnostic,
            expected_stderr: &[u8],
        ) {
            assert_eq!(outcome.as_ref().unwrap_err(), &expected_diagnostic);

            let mut stderr = Vec::new();
            assert_eq!(finish_cli(program, outcome, &mut stderr), 2);
            assert_eq!(stderr, expected_stderr);
        }

        fn assert_run_error(
            values: &[&[u8]],
            expected_diagnostic: Diagnostic,
            expected_stderr: &[u8],
        ) {
            let arguments = argv(values);
            let program = arguments
                .first()
                .map(|arg| basename(arg.as_os_str()))
                .unwrap_or_default();
            let outcome = run(&arguments, &FakeSystem::default());
            assert_error_outcome(program, outcome, expected_diagnostic, expected_stderr);
        }

        #[test]
        fn derives_raw_basenames_without_unicode_conversion() {
            let cases: &[(&[u8], &[u8])] = &[
                (b"test", b"test"),
                (b"custom", b"custom"),
                (b"/usr/bin/test", b"test"),
                (b"relative/path/custom", b"custom"),
                (b"/tmp/\xfftest", b"\xfftest"),
                (b"/", b""),
                (b"trailing/", b""),
                (b"", b""),
            ];

            for &(input, expected) in cases {
                let input = OsString::from_vec(input.to_vec());
                assert_eq!(basename(input.as_os_str()), expected);
            }
        }

        #[test]
        fn applies_bracket_mode_only_to_an_exact_basename_and_removes_the_final_bracket() {
            let system = FakeSystem::default();

            assert_eq!(run(&argv(&[b"[", b"]"]), &system), Ok(false));
            assert_eq!(run(&argv(&[b"[", b"value", b"]"]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"/usr/bin/[", b"", b"]"]), &system), Ok(false));
            assert_eq!(
                run(
                    &argv(&[b"/usr/bin/[", b"left", b"=", b"left", b"]"]),
                    &system
                ),
                Ok(true)
            );

            let missing = Err(syntax(None, b"missing ]"));
            assert_eq!(run(&argv(&[b"["]), &system), missing);
            assert_eq!(run(&argv(&[b"[", b"value"]), &system), missing);
            assert_eq!(
                run(&argv(&[b"[", b"left", b"=", b"left"]), &system),
                missing
            );

            assert_eq!(run(&argv(&[b"test", b"]"]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"custom", b"value"]), &system), Ok(true));
            assert_eq!(
                run(&argv(&[b"/usr/bin/custom", b"value"]), &system),
                Ok(true)
            );
            assert_eq!(run(&argv(&[b"/tmp/\xff[", b"value"]), &system), Ok(true));
            assert!(system.calls().is_empty());
        }

        #[test]
        fn emits_every_source_diagnostic_shape_as_exact_raw_bytes() {
            assert_run_error(
                &[b"/usr/bin/[", b"value"],
                syntax(None, b"missing ]"),
                b"[: missing ]\n",
            );
            assert_run_error(
                &[b"test", b"!", b"!", b"!"],
                syntax(None, b"argument expected"),
                b"test: argument expected\n",
            );
            assert_run_error(
                &[b"custom", b"left", b"="],
                syntax(Some(b"="), b"argument expected"),
                b"custom: =: argument expected\n",
            );
            assert_run_error(
                &[b"/usr/bin/test", b"(", b"value"],
                syntax(None, b"closing paren expected"),
                b"test: closing paren expected\n",
            );
            assert_run_error(
                &[b"/tmp/\xfftest", b"left", b"\xfeextra"],
                syntax(Some(b"\xfeextra"), b"unknown operand"),
                b"\xfftest: \xfeextra: unknown operand\n",
            );
            assert_run_error(
                &[b"test", b"invalid-number", b"-eq", b"0"],
                Diagnostic {
                    subject: Some(b"invalid-number".to_vec()),
                    message: b"invalid",
                },
                b"test: invalid-number: invalid\n",
            );
            assert_run_error(
                &[b"test", b"-t", b"-1"],
                Diagnostic {
                    subject: Some(b"-1".to_vec()),
                    message: b"too small",
                },
                b"test: -1: too small\n",
            );
            assert_run_error(
                &[b"test", b"-t", b"2147483648"],
                Diagnostic {
                    subject: Some(b"2147483648".to_vec()),
                    message: b"too large",
                },
                b"test: 2147483648: too large\n",
            );

            let operands = argv(&[b"left", b"not-an-operator", b"right"]);
            let outcome = Parser::new(&operands, &FakeSystem::default()).binop();
            assert_error_outcome(
                b"defensive",
                outcome,
                syntax(Some(b"not-an-operator"), b"not a binary operator"),
                b"defensive: not-an-operator: not a binary operator\n",
            );
        }

        #[test]
        fn preserves_empty_and_non_utf8_diagnostic_subjects() {
            let mut stderr = Vec::new();
            write_diagnostic(
                &mut stderr,
                b"\xffprogram",
                &Diagnostic {
                    subject: Some(Vec::new()),
                    message: b"invalid",
                },
            )
            .unwrap();
            assert_eq!(stderr, b"\xffprogram: : invalid\n");

            stderr.clear();
            write_diagnostic(
                &mut stderr,
                b"test",
                &Diagnostic {
                    subject: Some(b"\xfe".to_vec()),
                    message: b"invalid",
                },
            )
            .unwrap();
            assert_eq!(stderr, b"test: \xfe: invalid\n");
            assert_eq!(syntax(Some(b""), b"argument expected").subject, None);
        }

        #[test]
        fn maps_semantic_results_to_statuses_without_success_output() {
            let system = FakeSystem::default();
            let cases: &[(&[&[u8]], u8)] = &[
                (&[b"test", b"value"], 0),
                (&[b"test", b""], 1),
                (&[b"test", b"left", b"unknown"], 2),
            ];

            for &(values, expected_status) in cases {
                let arguments = argv(values);
                let program = basename(arguments[0].as_os_str());
                let outcome = run(&arguments, &system);
                let mut stderr = Vec::new();
                let status = finish_cli(program, outcome, &mut stderr);

                assert_eq!(status, expected_status);
                if status == 2 {
                    assert_eq!(stderr, b"test: unknown: unknown operand\n");
                } else {
                    assert!(stderr.is_empty());
                }
            }
            assert!(system.calls().is_empty());
        }

        #[test]
        fn retains_error_status_when_stderr_write_fails() {
            struct FailingWriter;

            impl Write for FailingWriter {
                fn write(&mut self, _buffer: &[u8]) -> io::Result<usize> {
                    Err(io::Error::new(io::ErrorKind::BrokenPipe, "closed stderr"))
                }

                fn flush(&mut self) -> io::Result<()> {
                    Ok(())
                }
            }

            assert_eq!(
                finish_cli(
                    b"test",
                    Err(syntax(None, b"argument expected")),
                    &mut FailingWriter,
                ),
                2
            );
        }
    }

    mod boundary_sequencing {
        use super::*;

        #[test]
        fn queries_binary_paths_left_to_right_and_stops_after_a_failed_left_stat() {
            let left = OsString::from("binary-left");
            let right = OsString::from("binary-right");
            let missing = OsString::from("binary-missing");
            let mut system = FakeSystem::default();
            let mut left_stat = file_stat_with(FileKind::Regular, 0);
            left_stat.mtime = 2;
            let mut right_stat = file_stat_with(FileKind::Regular, 0);
            right_stat.mtime = 1;
            system.set_stat(left.clone(), Ok(left_stat));
            system.set_stat(right.clone(), Ok(right_stat));
            system.set_stat(
                missing.clone(),
                Err(BoundaryError::Io(io::ErrorKind::NotFound)),
            );

            assert_eq!(
                run(
                    &argv(&[b"test", b"binary-left", b"-nt", b"binary-right"]),
                    &system
                ),
                Ok(true)
            );
            assert_eq!(
                run(
                    &argv(&[b"test", b"binary-missing", b"-ef", b"unconfigured"]),
                    &system
                ),
                Ok(false)
            );
            assert_eq!(
                system.calls(),
                vec![
                    SystemCall::Stat(left),
                    SystemCall::Stat(right),
                    SystemCall::Stat(missing),
                ]
            );
        }

        #[test]
        fn preserves_stat_access_lstat_and_eager_boolean_order() {
            let readable = OsString::from("readable");
            let missing = OsString::from("missing");
            let mut system = FakeSystem::default();
            system.set_stat(
                readable.clone(),
                Ok(file_stat_with(FileKind::Regular, 0o644)),
            );
            system.set_access(readable.clone(), AccessMode::Read, Ok(()));
            system.set_lstat(
                readable.clone(),
                Ok(file_stat_with(FileKind::Regular, 0o644)),
            );
            system.set_stat(
                missing.clone(),
                Err(BoundaryError::Io(io::ErrorKind::NotFound)),
            );

            assert_eq!(
                run(
                    &argv(&[
                        b"test",
                        b"(",
                        b"-f",
                        b"readable",
                        b"-a",
                        b"-r",
                        b"readable",
                        b")",
                        b"-o",
                        b"-f",
                        b"missing",
                    ]),
                    &system,
                ),
                Ok(true)
            );
            assert_eq!(
                run(&argv(&[b"test", b"-h", b"readable"]), &system),
                Ok(false)
            );
            assert_eq!(
                system.calls(),
                vec![
                    SystemCall::Stat(readable.clone()),
                    SystemCall::Stat(readable.clone()),
                    SystemCall::Access(readable.clone(), AccessMode::Read),
                    SystemCall::Stat(missing),
                    SystemCall::Lstat(readable),
                ]
            );
        }

        #[test]
        fn places_identity_queries_after_stat_and_uses_only_lstat_for_links() {
            let owned = OsString::from("owned");
            let link = OsString::from("link");
            let missing = OsString::from("missing");
            let mut system = FakeSystem::default();
            let mut owned_stat = file_stat_with(FileKind::Regular, 0);
            owned_stat.uid = 42;
            owned_stat.gid = 84;
            system.set_stat(owned.clone(), Ok(owned_stat));
            system.set_stat(
                missing.clone(),
                Err(BoundaryError::Io(io::ErrorKind::NotFound)),
            );
            system.set_lstat(link.clone(), Ok(file_stat_with(FileKind::Symlink, 0o777)));
            system.set_effective_ids(42, 84);

            assert_eq!(run(&argv(&[b"test", b"-O", b"owned"]), &system), Ok(true));
            assert_eq!(run(&argv(&[b"test", b"-G", b"owned"]), &system), Ok(true));
            assert_eq!(
                run(&argv(&[b"test", b"-O", b"missing"]), &system),
                Ok(false)
            );
            assert_eq!(run(&argv(&[b"test", b"-h", b"link"]), &system), Ok(true));

            assert_eq!(
                system.calls(),
                vec![
                    SystemCall::Stat(owned.clone()),
                    SystemCall::EffectiveUid,
                    SystemCall::Stat(owned),
                    SystemCall::EffectiveGid,
                    SystemCall::Stat(missing),
                    SystemCall::Lstat(link),
                ]
            );
        }
    }
}
