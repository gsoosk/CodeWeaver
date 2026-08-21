use std::cmp::Ordering;
use std::env;
use std::ffi::{OsStr, OsString};
use std::fs::{self, Metadata};
use std::io::{self, Write};
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::{FileTypeExt, MetadataExt};
use std::path::Path;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Token {
    Eoi,
    Filrd,
    Filwr,
    Filex,
    Filexist,
    Filreg,
    Fildir,
    Filcdev,
    Filbdev,
    Filfifo,
    Filsock,
    Filsym,
    Filgz,
    Filtt,
    Filsuid,
    Filsgid,
    Filstck,
    Filnt,
    Filot,
    Fileq,
    Filuid,
    Filgid,
    Strez,
    Strnz,
    Streq,
    Strne,
    Strlt,
    Strgt,
    Inteq,
    Intne,
    Intge,
    Intgt,
    Intle,
    Intlt,
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
struct Op {
    text: &'static [u8],
    token: Token,
    kind: TokenType,
}

static OPS: &[Op] = &[
    Op {
        text: b"-r",
        token: Token::Filrd,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-w",
        token: Token::Filwr,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-x",
        token: Token::Filex,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-e",
        token: Token::Filexist,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-f",
        token: Token::Filreg,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-d",
        token: Token::Fildir,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-c",
        token: Token::Filcdev,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-b",
        token: Token::Filbdev,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-p",
        token: Token::Filfifo,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-u",
        token: Token::Filsuid,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-g",
        token: Token::Filsgid,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-k",
        token: Token::Filstck,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-s",
        token: Token::Filgz,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-t",
        token: Token::Filtt,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-z",
        token: Token::Strez,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-n",
        token: Token::Strnz,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-h",
        token: Token::Filsym,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-O",
        token: Token::Filuid,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-G",
        token: Token::Filgid,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-L",
        token: Token::Filsym,
        kind: TokenType::Unop,
    },
    Op {
        text: b"-S",
        token: Token::Filsock,
        kind: TokenType::Unop,
    },
    Op {
        text: b"=",
        token: Token::Streq,
        kind: TokenType::Binop,
    },
    Op {
        text: b"!=",
        token: Token::Strne,
        kind: TokenType::Binop,
    },
    Op {
        text: b"<",
        token: Token::Strlt,
        kind: TokenType::Binop,
    },
    Op {
        text: b">",
        token: Token::Strgt,
        kind: TokenType::Binop,
    },
    Op {
        text: b"-eq",
        token: Token::Inteq,
        kind: TokenType::Binop,
    },
    Op {
        text: b"-ne",
        token: Token::Intne,
        kind: TokenType::Binop,
    },
    Op {
        text: b"-ge",
        token: Token::Intge,
        kind: TokenType::Binop,
    },
    Op {
        text: b"-gt",
        token: Token::Intgt,
        kind: TokenType::Binop,
    },
    Op {
        text: b"-le",
        token: Token::Intle,
        kind: TokenType::Binop,
    },
    Op {
        text: b"-lt",
        token: Token::Intlt,
        kind: TokenType::Binop,
    },
    Op {
        text: b"-nt",
        token: Token::Filnt,
        kind: TokenType::Binop,
    },
    Op {
        text: b"-ot",
        token: Token::Filot,
        kind: TokenType::Binop,
    },
    Op {
        text: b"-ef",
        token: Token::Fileq,
        kind: TokenType::Binop,
    },
    Op {
        text: b"!",
        token: Token::Unot,
        kind: TokenType::Bunop,
    },
    Op {
        text: b"-a",
        token: Token::Band,
        kind: TokenType::Bbinop,
    },
    Op {
        text: b"-o",
        token: Token::Bor,
        kind: TokenType::Bbinop,
    },
    Op {
        text: b"(",
        token: Token::Lparen,
        kind: TokenType::Paren,
    },
    Op {
        text: b")",
        token: Token::Rparen,
        kind: TokenType::Paren,
    },
];

#[derive(Clone, Debug, Eq, PartialEq)]
struct CliError {
    field: Option<Vec<u8>>,
    message: &'static [u8],
}

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
    mtime_secs: i64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum SystemError {
    Unavailable,
}

trait System {
    fn stat(&self, path: &[u8]) -> Result<FileStat, SystemError>;
    fn lstat(&self, path: &[u8]) -> Result<FileStat, SystemError>;
    fn access(&self, path: &[u8], mode: AccessMode) -> Result<bool, SystemError>;
    fn isatty(&self, fd: i32) -> Result<bool, SystemError>;
    fn effective_uid(&self) -> u32;
    fn effective_gid(&self) -> u32;
}

struct RealSystem;

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
        mtime_secs: metadata.mtime(),
    }
}

impl System for RealSystem {
    fn stat(&self, path: &[u8]) -> Result<FileStat, SystemError> {
        fs::metadata(Path::new(OsStr::from_bytes(path)))
            .map(file_stat)
            .map_err(|_| SystemError::Unavailable)
    }

    fn lstat(&self, path: &[u8]) -> Result<FileStat, SystemError> {
        fs::symlink_metadata(Path::new(OsStr::from_bytes(path)))
            .map(file_stat)
            .map_err(|_| SystemError::Unavailable)
    }

    fn access(&self, path: &[u8], mode: AccessMode) -> Result<bool, SystemError> {
        use nix::unistd::AccessFlags;

        let flags = match mode {
            AccessMode::Read => AccessFlags::R_OK,
            AccessMode::Write => AccessFlags::W_OK,
            AccessMode::Execute => AccessFlags::X_OK,
            AccessMode::Exists => AccessFlags::F_OK,
        };
        nix::unistd::access(Path::new(OsStr::from_bytes(path)), flags)
            .map(|()| true)
            .map_err(|_| SystemError::Unavailable)
    }

    fn isatty(&self, fd: i32) -> Result<bool, SystemError> {
        nix::unistd::isatty(fd).map_err(|_| SystemError::Unavailable)
    }

    fn effective_uid(&self) -> u32 {
        nix::unistd::geteuid().as_raw()
    }

    fn effective_gid(&self) -> u32 {
        nix::unistd::getegid().as_raw()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct NumberView<'a> {
    sign: i8,
    digits: &'a [u8],
}

struct Parser<'args, 'system, S: System> {
    args: &'args [Vec<u8>],
    cursor: usize,
    last_op: Option<&'static Op>,
    system: &'system S,
}

fn find_op(argument: &[u8]) -> Option<&'static Op> {
    OPS.iter().find(|op| op.text == argument)
}

impl<'args, 'system, S: System> Parser<'args, 'system, S> {
    fn new(args: &'args [Vec<u8>], system: &'system S) -> Self {
        Self {
            args,
            cursor: 0,
            last_op: None,
            system,
        }
    }

    fn t_lex(&mut self, argument: Option<&[u8]>) -> Token {
        let op = argument.and_then(find_op);
        self.last_op = op;
        match (argument, op) {
            (None, _) => Token::Eoi,
            (Some(_), Some(op)) => op.token,
            (Some(_), None) => Token::Operand,
        }
    }

    fn t_lex_type(&self, argument: Option<&[u8]>) -> Option<TokenType> {
        argument.and_then(find_op).map(|op| op.kind)
    }

    fn current(&self) -> Option<&[u8]> {
        self.args.get(self.cursor).map(Vec::as_slice)
    }

    fn lookahead(&self) -> Option<&[u8]> {
        self.cursor
            .checked_add(1)
            .and_then(|index| self.args.get(index))
            .map(Vec::as_slice)
    }

    fn advance(&mut self) {
        if self.cursor < self.args.len() {
            self.cursor += 1;
        }
    }

    fn rewind(&mut self) {
        self.cursor = self.cursor.saturating_sub(1);
    }

    fn lex_current(&mut self) -> Token {
        if self.cursor >= self.args.len() {
            self.last_op = None;
            return Token::Eoi;
        }

        let op = find_op(&self.args[self.cursor]);
        self.last_op = op;
        op.map_or(Token::Operand, |op| op.token)
    }

    fn oexpr(&mut self, token: Token) -> Result<bool, CliError> {
        let left = self.aexpr(token)?;
        self.advance();
        if self.lex_current() == Token::Bor {
            self.advance();
            let token = self.lex_current();
            let right = self.oexpr(token)?;
            Ok(right || left)
        } else {
            self.rewind();
            Ok(left)
        }
    }

    fn aexpr(&mut self, token: Token) -> Result<bool, CliError> {
        let left = self.nexpr(token)?;
        self.advance();
        if self.lex_current() == Token::Band {
            self.advance();
            let token = self.lex_current();
            let right = self.aexpr(token)?;
            Ok(right && left)
        } else {
            self.rewind();
            Ok(left)
        }
    }

    fn nexpr(&mut self, token: Token) -> Result<bool, CliError> {
        if token == Token::Unot {
            self.advance();
            let token = self.lex_current();
            return self.nexpr(token).map(|result| !result);
        }
        self.primary(token)
    }

    fn primary(&mut self, token: Token) -> Result<bool, CliError> {
        if token == Token::Eoi {
            return Err(syntax(None, b"argument expected"));
        }

        if token == Token::Lparen {
            self.advance();
            let token = self.lex_current();
            let result = self.oexpr(token)?;
            self.advance();
            if self.lex_current() != Token::Rparen {
                return Err(syntax(None, b"closing paren expected"));
            }
            return Ok(result);
        }

        if self.t_lex_type(self.lookahead()) == Some(TokenType::Binop) {
            self.last_op = self.lookahead().and_then(find_op);
            return self.binop();
        }

        if let Some(op) = self.last_op.filter(|op| op.kind == TokenType::Unop) {
            let op_text = op.text;
            self.advance();
            let operand = self
                .current()
                .ok_or_else(|| syntax(Some(op_text), b"argument expected"))?
                .to_vec();
            return match token {
                Token::Strez => Ok(operand.is_empty()),
                Token::Strnz => Ok(!operand.is_empty()),
                Token::Filtt => {
                    let fd = getn(&operand)?;
                    Ok(self.system.isatty(fd).unwrap_or(false))
                }
                _ => Ok(filstat(self.system, &operand, token)),
            };
        }

        Ok(self.current().is_some_and(|operand| !operand.is_empty()))
    }

    fn binop(&mut self) -> Result<bool, CliError> {
        let left = self
            .current()
            .ok_or_else(|| syntax(None, b"argument expected"))?
            .to_vec();

        self.advance();
        let token = self.lex_current();
        let op = self
            .last_op
            .ok_or_else(|| syntax(self.current(), b"not a binary operator"))?;
        self.advance();
        let right = self
            .current()
            .ok_or_else(|| syntax(Some(op.text), b"argument expected"))?
            .to_vec();

        match token {
            Token::Streq => Ok(left == right),
            Token::Strne => Ok(left != right),
            Token::Strlt => Ok(left < right),
            Token::Strgt => Ok(left > right),
            Token::Inteq => Ok(intcmp(&left, &right)? == Ordering::Equal),
            Token::Intne => Ok(intcmp(&left, &right)? != Ordering::Equal),
            Token::Intge => Ok(intcmp(&left, &right)? != Ordering::Less),
            Token::Intgt => Ok(intcmp(&left, &right)? == Ordering::Greater),
            Token::Intle => Ok(intcmp(&left, &right)? != Ordering::Greater),
            Token::Intlt => Ok(intcmp(&left, &right)? == Ordering::Less),
            Token::Filnt => Ok(newerf(self.system, &left, &right)),
            Token::Filot => Ok(olderf(self.system, &left, &right)),
            Token::Fileq => Ok(equalf(self.system, &left, &right)),
            _ => Err(syntax(Some(op.text), b"not a binary operator")),
        }
    }
}

fn syntax(operator: Option<&[u8]>, message: &'static [u8]) -> CliError {
    CliError {
        field: operator
            .filter(|operator| !operator.is_empty())
            .map(<[u8]>::to_vec),
        message,
    }
}

fn is_ascii_space(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | 0x0b | 0x0c | b'\r')
}

fn numeric_error(input: &[u8], message: &'static [u8]) -> CliError {
    CliError {
        field: Some(input.to_vec()),
        message,
    }
}

fn getnstr(input: &[u8]) -> Result<NumberView<'_>, CliError> {
    let mut index = 0;
    while input.get(index).is_some_and(|byte| is_ascii_space(*byte)) {
        index += 1;
    }

    let mut sign = 1;
    match input.get(index) {
        Some(b'-') => {
            sign = -1;
            index += 1;
        }
        Some(b'+') => index += 1,
        _ => {}
    }

    while input.get(index) == Some(&b'0')
        && input
            .get(index + 1)
            .is_some_and(|byte| byte.is_ascii_digit())
    {
        index += 1;
    }
    if input.get(index) == Some(&b'0') {
        sign = 1;
    }

    let start = index;
    while input.get(index).is_some_and(|byte| byte.is_ascii_digit()) {
        index += 1;
    }
    let end = index;

    while input.get(index).is_some_and(|byte| is_ascii_space(*byte)) {
        index += 1;
    }

    // The source tests whether `start` points at NUL, not whether a digit was
    // consumed, so a sign followed only by trailing whitespace reaches intcmp.
    if index != input.len() || start == input.len() {
        return Err(numeric_error(input, b"invalid"));
    }

    Ok(NumberView {
        sign,
        digits: &input[start..end],
    })
}

fn intcmp(left: &[u8], right: &[u8]) -> Result<Ordering, CliError> {
    let left = getnstr(left)?;
    let right = getnstr(right)?;

    if left.sign != right.sign {
        return Ok(left.sign.cmp(&right.sign));
    }

    let length_order = left.digits.len().cmp(&right.digits.len());
    if length_order != Ordering::Equal {
        return Ok(if left.sign < 0 {
            length_order.reverse()
        } else {
            length_order
        });
    }

    let digit_order = left.digits.cmp(right.digits);
    Ok(if left.sign < 0 {
        digit_order.reverse()
    } else {
        digit_order
    })
}

fn getn(input: &[u8]) -> Result<i32, CliError> {
    let number = getnstr(input)?;
    if number.sign != 1 {
        return Err(numeric_error(input, b"too small"));
    }
    if number.digits.len() >= 32 {
        return Err(numeric_error(input, b"too large"));
    }
    if number.digits.is_empty() {
        return Err(numeric_error(input, b"invalid"));
    }

    number
        .digits
        .iter()
        .try_fold(0_i32, |value, digit| {
            value
                .checked_mul(10)
                .and_then(|value| value.checked_add(i32::from(digit - b'0')))
        })
        .ok_or_else(|| numeric_error(input, b"too large"))
}

fn filstat<S: System>(system: &S, path: &[u8], mode: Token) -> bool {
    if mode == Token::Filsym {
        return system
            .lstat(path)
            .map(|stat| stat.kind == FileKind::Symlink)
            .unwrap_or(false);
    }

    let stat = match system.stat(path) {
        Ok(stat) => stat,
        Err(_) => return false,
    };

    match mode {
        Token::Filrd => system.access(path, AccessMode::Read).unwrap_or(false),
        Token::Filwr => system.access(path, AccessMode::Write).unwrap_or(false),
        Token::Filex => system.access(path, AccessMode::Execute).unwrap_or(false),
        Token::Filexist => system.access(path, AccessMode::Exists).unwrap_or(false),
        Token::Filreg => stat.kind == FileKind::Regular,
        Token::Fildir => stat.kind == FileKind::Directory,
        Token::Filcdev => stat.kind == FileKind::CharacterDevice,
        Token::Filbdev => stat.kind == FileKind::BlockDevice,
        Token::Filfifo | Token::Filsock => stat.kind == FileKind::Fifo,
        Token::Filsuid => stat.mode & 0o4000 != 0,
        Token::Filsgid => stat.mode & 0o2000 != 0,
        Token::Filstck => stat.mode & 0o1000 != 0,
        Token::Filgz => stat.size > 0,
        Token::Filuid => stat.uid == system.effective_uid(),
        Token::Filgid => stat.gid == system.effective_gid(),
        _ => true,
    }
}

fn newerf<S: System>(system: &S, left: &[u8], right: &[u8]) -> bool {
    let left = match system.stat(left) {
        Ok(stat) => stat,
        Err(_) => return false,
    };
    let right = match system.stat(right) {
        Ok(stat) => stat,
        Err(_) => return false,
    };
    left.mtime_secs > right.mtime_secs
}

fn olderf<S: System>(system: &S, left: &[u8], right: &[u8]) -> bool {
    let left = match system.stat(left) {
        Ok(stat) => stat,
        Err(_) => return false,
    };
    let right = match system.stat(right) {
        Ok(stat) => stat,
        Err(_) => return false,
    };
    left.mtime_secs < right.mtime_secs
}

fn equalf<S: System>(system: &S, left: &[u8], right: &[u8]) -> bool {
    let left = match system.stat(left) {
        Ok(stat) => stat,
        Err(_) => return false,
    };
    let right = match system.stat(right) {
        Ok(stat) => stat,
        Err(_) => return false,
    };
    left.dev == right.dev && left.ino == right.ino
}

fn short_program_name(argv0: &[u8]) -> &[u8] {
    argv0.rsplit(|byte| *byte == b'/').next().unwrap_or(argv0)
}

fn run<S: System>(args: &[OsString], system: &S) -> Result<bool, CliError> {
    let raw_args: Vec<Vec<u8>> = args
        .iter()
        .map(|argument| argument.as_os_str().as_bytes().to_vec())
        .collect();
    let program_name = raw_args
        .first()
        .map_or(&[][..], |argument| short_program_name(argument));
    let mut expression = raw_args.get(1..).unwrap_or(&[]);

    if program_name == b"[" {
        if expression.last().map(Vec::as_slice) != Some(&b"]"[..]) {
            return Err(syntax(None, b"missing ]"));
        }
        expression = &expression[..expression.len() - 1];
    }

    match expression.len() {
        0 => return Ok(false),
        1 => return Ok(!expression[0].is_empty()),
        2 if expression[0] == b"!" => return Ok(expression[1].is_empty()),
        3 if expression[0] != b"!" => {
            if find_op(&expression[1]).is_some_and(|op| op.kind == TokenType::Binop) {
                let mut parser = Parser::new(expression, system);
                return parser.binop();
            }
        }
        4 if expression[0] == b"!" => {
            if find_op(&expression[2]).is_some_and(|op| op.kind == TokenType::Binop) {
                let mut parser = Parser::new(expression, system);
                parser.cursor = 1;
                return parser.binop().map(|result| !result);
            }
        }
        _ => {}
    }

    let mut parser = Parser::new(expression, system);
    let token = parser.t_lex(expression.first().map(Vec::as_slice));
    let result = parser.oexpr(token)?;
    if parser.current().is_some() {
        parser.advance();
        if let Some(argument) = parser.current() {
            return Err(syntax(Some(argument), b"unknown operand"));
        }
    }
    Ok(result)
}

fn write_diagnostic<W: Write>(
    writer: &mut W,
    program_name: &[u8],
    error: &CliError,
) -> io::Result<()> {
    let mut line = Vec::new();
    line.extend_from_slice(program_name);
    line.extend_from_slice(b": ");
    if let Some(field) = &error.field {
        line.extend_from_slice(field);
        line.extend_from_slice(b": ");
    }
    line.extend_from_slice(error.message);
    line.push(b'\n');
    writer.write_all(&line)
}

fn finish_result<W: Write>(
    result: Result<bool, CliError>,
    program_name: &[u8],
    stderr: &mut W,
) -> i32 {
    match result {
        Ok(true) => 0,
        Ok(false) => 1,
        Err(error) => {
            let _ = write_diagnostic(stderr, program_name, &error);
            2
        }
    }
}

fn main() {
    let args: Vec<OsString> = env::args_os().collect();
    let program_name = args
        .first()
        .map(|argument| short_program_name(argument.as_os_str().as_bytes()).to_vec())
        .unwrap_or_default();
    let result = run(&args, &RealSystem);
    let stderr = io::stderr();
    let mut stderr = stderr.lock();
    let status = finish_result(result, &program_name, &mut stderr);
    std::process::exit(status);
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;
    use std::collections::HashMap;
    use std::os::unix::ffi::OsStringExt;

    #[derive(Clone, Debug, Eq, PartialEq)]
    enum MockCall {
        Stat(Vec<u8>),
        Lstat(Vec<u8>),
        Access(Vec<u8>, AccessMode),
        Isatty(i32),
        EffectiveUid,
        EffectiveGid,
    }

    #[derive(Default)]
    struct MockSystem {
        stat_results: HashMap<Vec<u8>, Result<FileStat, SystemError>>,
        lstat_results: HashMap<Vec<u8>, Result<FileStat, SystemError>>,
        access_results: HashMap<(Vec<u8>, AccessMode), Result<bool, SystemError>>,
        isatty_results: HashMap<i32, Result<bool, SystemError>>,
        effective_uid: u32,
        effective_gid: u32,
        calls: RefCell<Vec<MockCall>>,
    }

    impl System for MockSystem {
        fn stat(&self, path: &[u8]) -> Result<FileStat, SystemError> {
            self.calls.borrow_mut().push(MockCall::Stat(path.to_vec()));
            self.stat_results
                .get(path)
                .copied()
                .unwrap_or(Err(SystemError::Unavailable))
        }

        fn lstat(&self, path: &[u8]) -> Result<FileStat, SystemError> {
            self.calls.borrow_mut().push(MockCall::Lstat(path.to_vec()));
            self.lstat_results
                .get(path)
                .copied()
                .unwrap_or(Err(SystemError::Unavailable))
        }

        fn access(&self, path: &[u8], mode: AccessMode) -> Result<bool, SystemError> {
            self.calls
                .borrow_mut()
                .push(MockCall::Access(path.to_vec(), mode));
            self.access_results
                .get(&(path.to_vec(), mode))
                .copied()
                .unwrap_or(Err(SystemError::Unavailable))
        }

        fn isatty(&self, fd: i32) -> Result<bool, SystemError> {
            self.calls.borrow_mut().push(MockCall::Isatty(fd));
            self.isatty_results
                .get(&fd)
                .copied()
                .unwrap_or(Err(SystemError::Unavailable))
        }

        fn effective_uid(&self) -> u32 {
            self.calls.borrow_mut().push(MockCall::EffectiveUid);
            self.effective_uid
        }

        fn effective_gid(&self) -> u32 {
            self.calls.borrow_mut().push(MockCall::EffectiveGid);
            self.effective_gid
        }
    }

    fn os_args(arguments: &[&[u8]]) -> Vec<OsString> {
        arguments
            .iter()
            .map(|argument| OsString::from_vec(argument.to_vec()))
            .collect()
    }

    fn run_bytes(system: &MockSystem, arguments: &[&[u8]]) -> Result<bool, CliError> {
        run(&os_args(arguments), system)
    }

    fn stat(kind: FileKind) -> FileStat {
        FileStat {
            kind,
            mode: 0,
            size: 0,
            uid: 1000,
            gid: 1000,
            dev: 1,
            ino: 1,
            mtime_secs: 0,
        }
    }

    #[test]
    fn mockable_seam_skeleton_compiles() {
        let _ = MockSystem::default();
    }

    mod ops_and_lexing {
        use super::*;

        #[test]
        fn recognizes_the_complete_operator_table_in_source_order() {
            let expected: &[(&[u8], Token, TokenType)] = &[
                (b"-r", Token::Filrd, TokenType::Unop),
                (b"-w", Token::Filwr, TokenType::Unop),
                (b"-x", Token::Filex, TokenType::Unop),
                (b"-e", Token::Filexist, TokenType::Unop),
                (b"-f", Token::Filreg, TokenType::Unop),
                (b"-d", Token::Fildir, TokenType::Unop),
                (b"-c", Token::Filcdev, TokenType::Unop),
                (b"-b", Token::Filbdev, TokenType::Unop),
                (b"-p", Token::Filfifo, TokenType::Unop),
                (b"-u", Token::Filsuid, TokenType::Unop),
                (b"-g", Token::Filsgid, TokenType::Unop),
                (b"-k", Token::Filstck, TokenType::Unop),
                (b"-s", Token::Filgz, TokenType::Unop),
                (b"-t", Token::Filtt, TokenType::Unop),
                (b"-z", Token::Strez, TokenType::Unop),
                (b"-n", Token::Strnz, TokenType::Unop),
                (b"-h", Token::Filsym, TokenType::Unop),
                (b"-O", Token::Filuid, TokenType::Unop),
                (b"-G", Token::Filgid, TokenType::Unop),
                (b"-L", Token::Filsym, TokenType::Unop),
                (b"-S", Token::Filsock, TokenType::Unop),
                (b"=", Token::Streq, TokenType::Binop),
                (b"!=", Token::Strne, TokenType::Binop),
                (b"<", Token::Strlt, TokenType::Binop),
                (b">", Token::Strgt, TokenType::Binop),
                (b"-eq", Token::Inteq, TokenType::Binop),
                (b"-ne", Token::Intne, TokenType::Binop),
                (b"-ge", Token::Intge, TokenType::Binop),
                (b"-gt", Token::Intgt, TokenType::Binop),
                (b"-le", Token::Intle, TokenType::Binop),
                (b"-lt", Token::Intlt, TokenType::Binop),
                (b"-nt", Token::Filnt, TokenType::Binop),
                (b"-ot", Token::Filot, TokenType::Binop),
                (b"-ef", Token::Fileq, TokenType::Binop),
                (b"!", Token::Unot, TokenType::Bunop),
                (b"-a", Token::Band, TokenType::Bbinop),
                (b"-o", Token::Bor, TokenType::Bbinop),
                (b"(", Token::Lparen, TokenType::Paren),
                (b")", Token::Rparen, TokenType::Paren),
            ];
            let system = MockSystem::default();
            let arguments = Vec::new();
            let mut parser = Parser::new(&arguments, &system);

            assert_eq!(OPS.len(), expected.len());
            for (op, &(text, token, kind)) in OPS.iter().zip(expected) {
                assert_eq!((op.text, op.token, op.kind), (text, token, kind));
                assert_eq!(parser.t_lex(Some(text)), token);
                assert_eq!(parser.last_op, Some(op));
                assert_eq!(parser.t_lex_type(Some(text)), Some(kind));
            }
        }

        #[test]
        fn handles_eoi_and_unknown_operands_without_mutating_lookahead_state() {
            let system = MockSystem::default();
            let arguments = Vec::new();
            let mut parser = Parser::new(&arguments, &system);

            assert_eq!(parser.t_lex(Some(b"-n")), Token::Strnz);
            let unary = parser.last_op;
            assert_eq!(parser.t_lex_type(Some(b"=")), Some(TokenType::Binop));
            assert_eq!(parser.t_lex_type(Some(b"-unknown")), None);
            assert_eq!(parser.t_lex_type(None), None);
            assert_eq!(parser.last_op, unary);

            for operand in [b"-unknown".as_slice(), b"==", b"[", &[0xff][..]] {
                assert_eq!(parser.t_lex(Some(operand)), Token::Operand);
                assert_eq!(parser.last_op, None);
            }
            assert_eq!(parser.t_lex(None), Token::Eoi);
            assert_eq!(parser.last_op, None);
        }
    }

    mod cli_cardinality {
        use super::*;

        #[test]
        fn handles_empty_singleton_and_negated_singleton_expressions() {
            let system = MockSystem::default();

            assert!(!run_bytes(&system, &[b"test"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b""]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"value"]).unwrap());
            assert!(run_bytes(&system, &[b"test", &[0xff]]).unwrap());
            for op in OPS {
                assert!(
                    run_bytes(&system, &[b"test", op.text]).unwrap(),
                    "singleton operator {:?}",
                    op.text
                );
            }

            assert!(run_bytes(&system, &[b"test", b"!", b""]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"!", b"value"]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"-z", b""]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"-z", b"value"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"-n", b""]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"-n", b"value"]).unwrap());
        }

        #[test]
        fn dispatches_recognized_binary_and_negated_binary_expressions() {
            let system = MockSystem::default();

            assert!(run_bytes(&system, &[b"test", b"hello", b"!=", b"world"]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"def", b">", b"abc"]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"1000000", b"-gt", b"999999"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"!", b"1000000", b"-gt", b"999999"],).unwrap());
            assert!(run_bytes(&system, &[b"test", b"!!", b"=", b"!!"]).unwrap());
        }

        #[test]
        fn sends_non_binary_cardinality_cases_through_the_expression_parser() {
            let system = MockSystem::default();

            assert!(run_bytes(&system, &[b"test", b"left", b"-a", b"right"]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"!", b"-n", b""]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"!", b"!", b"-n", b""]).unwrap());
            assert_eq!(
                run_bytes(&system, &[b"test", b"left", b"-unknown", b"right"]),
                Err(CliError {
                    field: Some(b"-unknown".to_vec()),
                    message: b"unknown operand",
                })
            );
        }
    }

    mod bracket_and_program_name {
        use super::*;

        #[test]
        fn derives_the_raw_basename_and_removes_a_valid_closing_bracket() {
            let system = MockSystem::default();

            assert_eq!(short_program_name(b"/usr/bin/test"), b"test");
            assert_eq!(short_program_name(b"/tmp/["), b"[");
            assert_eq!(short_program_name(b"/tmp/\xfftest"), b"\xfftest");
            assert!(!run_bytes(&system, &[b"[", b"]"]).unwrap());
            assert!(!run_bytes(&system, &[b"/tmp/[", b"", b"]"]).unwrap());
            assert!(run_bytes(&system, &[b"/tmp/[", b"value", b"]"]).unwrap());
            assert!(run_bytes(&system, &[b"[", b"!", b"]"]).unwrap());
            assert!(run_bytes(&system, &[b"[", b"!", b"", b"]"]).unwrap());
            assert!(run_bytes(&system, &[b"/tmp/\xff[", b"value"]).unwrap());
        }

        #[test]
        fn reports_a_missing_closing_bracket_before_expression_parsing() {
            let system = MockSystem::default();

            for arguments in [
                &[b"[".as_slice()][..],
                &[b"[".as_slice(), b"value"][..],
                &[b"[".as_slice(), b"value", b""][..],
                &[b"[".as_slice(), b"value", b"]]"][..],
                &[b"[".as_slice(), b"]", b"value"][..],
            ] {
                assert_eq!(
                    run_bytes(&system, arguments),
                    Err(CliError {
                        field: None,
                        message: b"missing ]",
                    })
                );
            }
        }

        #[test]
        fn renders_exact_bracket_and_raw_program_name_diagnostics() {
            let system = MockSystem::default();
            let error = run_bytes(&system, &[b"/tmp/[", b"value"]).unwrap_err();
            let mut output = Vec::new();
            write_diagnostic(&mut output, b"[", &error).unwrap();
            assert_eq!(output, b"[: missing ]\n");

            let arguments = os_args(&[b"/tmp/\xfftest", b"value", b"-a"]);
            let error = run(&arguments, &system).unwrap_err();
            let program_name = short_program_name(arguments[0].as_os_str().as_bytes());
            let mut output = Vec::new();
            write_diagnostic(&mut output, program_name, &error).unwrap();
            assert_eq!(output, b"\xfftest: argument expected\n");
        }
    }

    mod parser_grammar {
        use super::*;

        #[test]
        fn applies_not_then_and_then_or_precedence() {
            let system = MockSystem::default();

            assert!(run_bytes(&system, &[b"test", b"value", b"-o", b"", b"-a", b""],).unwrap());
            assert!(
                run_bytes(&system, &[b"test", b"", b"-a", b"value", b"-o", b"value"],).unwrap()
            );
            assert!(run_bytes(&system, &[b"test", b"!", b"!", b"value"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"!", b"!", b"!", b"value"]).unwrap());
        }

        #[test]
        fn handles_nested_parentheses_and_negation() {
            let system = MockSystem::default();

            assert!(run_bytes(
                &system,
                &[b"test", b"(", b"(", b"value", b")", b"-a", b"(", b"!", b"", b")", b")",],
            )
            .unwrap());
            assert!(run_bytes(
                &system,
                &[b"test", b"!", b"(", b"!", b"(", b"value", b")", b")"],
            )
            .unwrap());
        }

        #[test]
        fn gives_binary_lookahead_priority_over_unary_interpretation() {
            let system = MockSystem::default();

            assert!(run_bytes(&system, &[b"test", b"-n", b"=", b"-n", b"-a", b"value"],).unwrap());
            assert!(run_bytes(&system, &[b"test", b"value", b"-a", b"-z", b"=", b"-z"],).unwrap());
        }

        #[test]
        fn evaluates_parenthesized_and_and_both_or_branches() {
            let mut system = MockSystem::default();
            let file = b"file".to_vec();
            system
                .stat_results
                .insert(file.clone(), Ok(stat(FileKind::Regular)));
            system
                .access_results
                .insert((file.clone(), AccessMode::Read), Ok(true));

            assert!(run_bytes(
                &system,
                &[b"test", b"(", b"-f", b"file", b"-a", b"-r", b"file", b")",],
            )
            .unwrap());
            assert_eq!(
                *system.calls.borrow(),
                vec![
                    MockCall::Stat(file.clone()),
                    MockCall::Stat(file.clone()),
                    MockCall::Access(file.clone(), AccessMode::Read),
                ]
            );

            system.calls.borrow_mut().clear();
            assert!(run_bytes(
                &system,
                &[b"test", b"-f", b"file", b"-o", b"-f", b"missing"],
            )
            .unwrap());
            assert_eq!(
                *system.calls.borrow(),
                vec![MockCall::Stat(file), MockCall::Stat(b"missing".to_vec())]
            );

            system.calls.borrow_mut().clear();
            assert!(!run_bytes(
                &system,
                &[b"test", b"-f", b"missing-left", b"-a", b"-f", b"file",],
            )
            .unwrap());
            assert_eq!(
                *system.calls.borrow(),
                vec![
                    MockCall::Stat(b"missing-left".to_vec()),
                    MockCall::Stat(b"file".to_vec()),
                ]
            );
        }

        #[test]
        fn boolean_operators_eagerly_report_right_side_numeric_errors() {
            let system = MockSystem::default();

            assert!(!run_bytes(
                &system,
                &[b"test", b"-f", b"missing-a", b"-o", b"-f", b"missing-b",],
            )
            .unwrap());
            assert_eq!(
                run_bytes(&system, &[b"test", b"", b"-a", b"1", b"-eq", b"invalid"],),
                Err(CliError {
                    field: Some(b"invalid".to_vec()),
                    message: b"invalid",
                })
            );
            assert_eq!(
                run_bytes(
                    &system,
                    &[b"test", b"value", b"-o", b"1", b"-eq", b"invalid"],
                ),
                Err(CliError {
                    field: Some(b"invalid".to_vec()),
                    message: b"invalid",
                })
            );
        }

        #[test]
        fn reports_exact_missing_operand_and_parenthesis_errors() {
            let system = MockSystem::default();

            for (arguments, expected) in [
                (
                    &[b"test".as_slice(), b"value", b"-a"][..],
                    CliError {
                        field: None,
                        message: b"argument expected",
                    },
                ),
                (
                    &[b"test".as_slice(), b"value", b"-a", b"-n"][..],
                    CliError {
                        field: Some(b"-n".to_vec()),
                        message: b"argument expected",
                    },
                ),
                (
                    &[b"test".as_slice(), b"value", b"="][..],
                    CliError {
                        field: Some(b"=".to_vec()),
                        message: b"argument expected",
                    },
                ),
                (
                    &[b"test".as_slice(), b"(", b"value"][..],
                    CliError {
                        field: None,
                        message: b"closing paren expected",
                    },
                ),
            ] {
                assert_eq!(run_bytes(&system, arguments), Err(expected));
            }

            let arguments = vec![b"left".to_vec(), b"-a".to_vec(), b"right".to_vec()];
            let mut parser = Parser::new(&arguments, &system);
            assert_eq!(
                parser.binop(),
                Err(CliError {
                    field: Some(b"-a".to_vec()),
                    message: b"not a binary operator",
                })
            );
        }

        #[test]
        fn reports_the_first_trailing_operand_selected_by_the_source_cursor() {
            let system = MockSystem::default();

            assert_eq!(
                run_bytes(&system, &[b"test", b"a", b"b", b"c", b"d"]),
                Err(CliError {
                    field: Some(b"b".to_vec()),
                    message: b"unknown operand",
                })
            );
            assert_eq!(
                run_bytes(&system, &[b"test", b"value", b"=", b"value", b"tail"]),
                Err(CliError {
                    field: Some(b"tail".to_vec()),
                    message: b"unknown operand",
                })
            );
            assert_eq!(
                run_bytes(&system, &[b"test", b"-n", b"value", b"tail"]),
                Err(CliError {
                    field: Some(b"tail".to_vec()),
                    message: b"unknown operand",
                })
            );
            assert_eq!(
                run_bytes(&system, &[b"test", b"value", b""]),
                Err(CliError {
                    field: None,
                    message: b"unknown operand",
                })
            );
        }
    }

    mod string_comparison {
        use super::*;

        #[test]
        fn evaluates_all_string_operators_over_empty_and_ascii_operands() {
            let system = MockSystem::default();

            for (left, operator, right, expected) in [
                (b"".as_slice(), b"=".as_slice(), b"".as_slice(), true),
                (b"".as_slice(), b"!=".as_slice(), b"x".as_slice(), true),
                (b"abc".as_slice(), b"=".as_slice(), b"abc".as_slice(), true),
                (
                    b"abc".as_slice(),
                    b"!=".as_slice(),
                    b"abc".as_slice(),
                    false,
                ),
                (b"a".as_slice(), b"<".as_slice(), b"aa".as_slice(), true),
                (b"b".as_slice(), b">".as_slice(), b"aa".as_slice(), true),
                (b"abc".as_slice(), b"<".as_slice(), b"abc".as_slice(), false),
                (b"abc".as_slice(), b">".as_slice(), b"abc".as_slice(), false),
            ] {
                assert_eq!(
                    run_bytes(&system, &[b"test", left, operator, right]).unwrap(),
                    expected
                );
            }
        }

        #[test]
        fn compares_strings_as_unsigned_non_utf8_bytes() {
            let system = MockSystem::default();
            let high = &[0xff][..];
            let low = &[0xfe][..];

            assert!(run_bytes(&system, &[b"test", high, b">", low]).unwrap());
            assert!(run_bytes(&system, &[b"test", high, b"=", high]).unwrap());
            assert!(run_bytes(&system, &[b"test", high, b"!=", low]).unwrap());
            assert!(!run_bytes(&system, &[b"test", high, b"<", low]).unwrap());
        }
    }

    mod integer_comparison {
        use super::*;

        #[test]
        fn compares_canonical_arbitrary_length_signed_integers() {
            assert_eq!(intcmp(b"1000000", b"999999"), Ok(Ordering::Greater));
            assert_eq!(
                intcmp(b"\t\n\x0b\x0c\r +00042\t", b"42"),
                Ok(Ordering::Equal)
            );
            assert_eq!(intcmp(b"-000", b"+0"), Ok(Ordering::Equal));
            assert_eq!(
                intcmp(
                    b"999999999999999999999999999999999999",
                    b"1000000000000000000000000000000000000",
                ),
                Ok(Ordering::Less)
            );
            assert_eq!(intcmp(b"-1000", b"-999"), Ok(Ordering::Less));
            assert_eq!(
                intcmp(
                    b"-999999999999999999999999999999999999",
                    b"-1000000000000000000000000000000000000",
                ),
                Ok(Ordering::Greater)
            );
        }

        #[test]
        fn preserves_the_sources_sign_followed_by_whitespace_comparison_quirk() {
            assert_eq!(
                getnstr(b"+ \t"),
                Ok(NumberView {
                    sign: 1,
                    digits: b"",
                })
            );
            assert_eq!(
                getnstr(b"- \n"),
                Ok(NumberView {
                    sign: -1,
                    digits: b"",
                })
            );
            assert_eq!(intcmp(b"+ ", b"0"), Ok(Ordering::Less));
            assert_eq!(intcmp(b"- ", b"-0"), Ok(Ordering::Less));
        }

        #[test]
        fn evaluates_every_integer_binary_operator() {
            let system = MockSystem::default();
            for (left, operator, right, expected) in [
                (b"10".as_slice(), b"-eq".as_slice(), b"010".as_slice(), true),
                (b"10".as_slice(), b"-eq".as_slice(), b"11".as_slice(), false),
                (b"10".as_slice(), b"-ne".as_slice(), b"11".as_slice(), true),
                (
                    b"10".as_slice(),
                    b"-ne".as_slice(),
                    b"010".as_slice(),
                    false,
                ),
                (b"10".as_slice(), b"-ge".as_slice(), b"10".as_slice(), true),
                (b"9".as_slice(), b"-ge".as_slice(), b"10".as_slice(), false),
                (b"11".as_slice(), b"-gt".as_slice(), b"10".as_slice(), true),
                (b"10".as_slice(), b"-gt".as_slice(), b"10".as_slice(), false),
                (
                    b"-11".as_slice(),
                    b"-le".as_slice(),
                    b"-10".as_slice(),
                    true,
                ),
                (b"11".as_slice(), b"-le".as_slice(), b"10".as_slice(), false),
                (
                    b"-11".as_slice(),
                    b"-lt".as_slice(),
                    b"-10".as_slice(),
                    true,
                ),
                (b"10".as_slice(), b"-lt".as_slice(), b"10".as_slice(), false),
            ] {
                assert_eq!(
                    run_bytes(&system, &[b"test", left, operator, right]).unwrap(),
                    expected,
                    "{left:?} {operator:?} {right:?}"
                );
            }
        }

        #[test]
        fn preserves_the_original_field_on_invalid_numbers() {
            for input in [
                b"".as_slice(),
                b"+",
                b"-",
                b" \t\n\x0b\x0c\r",
                b"1x",
                b"- 1",
                b"1 2",
                &[b'1', 0xff],
            ] {
                assert_eq!(
                    getnstr(input),
                    Err(CliError {
                        field: Some(input.to_vec()),
                        message: b"invalid",
                    })
                );
            }

            assert_eq!(
                intcmp(b"left-error", b"right-error"),
                Err(CliError {
                    field: Some(b"left-error".to_vec()),
                    message: b"invalid",
                })
            );
            assert_eq!(
                intcmp(b"1", b"right-error"),
                Err(CliError {
                    field: Some(b"right-error".to_vec()),
                    message: b"invalid",
                })
            );
        }

        #[test]
        fn renders_exact_raw_numeric_diagnostics() {
            let system = MockSystem::default();
            let invalid = &[b'1', 0xff][..];
            let error = run_bytes(&system, &[b"test", b"0", b"-eq", invalid]).unwrap_err();
            let mut output = Vec::new();
            write_diagnostic(&mut output, b"test", &error).unwrap();
            assert_eq!(output, b"test: 1\xff: invalid\n");

            let error = run_bytes(&system, &[b"test", b"", b"-eq", b"0"]).unwrap_err();
            let mut output = Vec::new();
            write_diagnostic(&mut output, b"test", &error).unwrap();
            assert_eq!(output, b"test: : invalid\n");
        }
    }

    mod terminal_descriptor {
        use super::*;

        fn assert_numeric_error(input: &[u8], message: &'static [u8]) {
            assert_eq!(getn(input), Err(numeric_error(input, message)));
        }

        #[test]
        fn invokes_isatty_for_valid_boundaries_and_maps_observation_results() {
            let mut system = MockSystem::default();
            system.isatty_results.insert(0, Ok(true));
            system.isatty_results.insert(1, Ok(false));
            system
                .isatty_results
                .insert(2, Err(SystemError::Unavailable));
            system.isatty_results.insert(i32::MAX, Ok(true));

            assert!(run_bytes(&system, &[b"test", b"-t", b"0"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"-t", b"1"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"-t", b"2"]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"-t", b"2147483647"]).unwrap());
            assert_eq!(
                *system.calls.borrow(),
                vec![
                    MockCall::Isatty(0),
                    MockCall::Isatty(1),
                    MockCall::Isatty(2),
                    MockCall::Isatty(i32::MAX),
                ]
            );
        }

        #[test]
        fn accepts_canonical_zero_and_huge_discarded_leading_zeroes() {
            const PADDED_MAX: &[u8] = b"000000000000000000000000000000000000000000000002147483647";

            assert_eq!(getn(b"0"), Ok(0));
            assert_eq!(getn(b"-000000"), Ok(0));
            assert_eq!(getn(b"2147483647"), Ok(i32::MAX));
            assert_eq!(getn(PADDED_MAX), Ok(i32::MAX));

            let mut system = MockSystem::default();
            system.isatty_results.insert(0, Ok(true));
            system.isatty_results.insert(i32::MAX, Ok(true));
            assert!(run_bytes(&system, &[b"test", b"-t", b"-000000"]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"-t", PADDED_MAX]).unwrap());
            assert_eq!(
                *system.calls.borrow(),
                vec![MockCall::Isatty(0), MockCall::Isatty(i32::MAX)]
            );
        }

        #[test]
        fn classifies_invalid_and_out_of_range_descriptors_in_source_order() {
            let thirty_one_digits = [b'1'; 31];
            let thirty_two_digits = [b'1'; 32];

            for invalid in [
                b"".as_slice(),
                b"+".as_slice(),
                b"-".as_slice(),
                b" \t\r\n".as_slice(),
                b"+ 1".as_slice(),
                b"1x".as_slice(),
                &[b'1', 0xff],
            ] {
                assert_numeric_error(invalid, b"invalid");
            }
            assert_numeric_error(b"+ \t", b"invalid");
            assert_numeric_error(b"- \t", b"too small");
            assert_numeric_error(b"-1", b"too small");
            assert_numeric_error(b"-11111111111111111111111111111111", b"too small");
            assert_numeric_error(b"2147483648", b"too large");
            assert_numeric_error(&thirty_one_digits, b"too large");
            assert_numeric_error(&thirty_two_digits, b"too large");
        }

        #[test]
        fn parse_errors_preserve_the_field_and_do_not_call_isatty() {
            let system = MockSystem::default();
            for (input, message) in [
                (b"bad".as_slice(), b"invalid".as_slice()),
                (b"-1".as_slice(), b"too small".as_slice()),
                (b"2147483648".as_slice(), b"too large".as_slice()),
            ] {
                assert_eq!(
                    run_bytes(&system, &[b"test", b"-t", input]),
                    Err(CliError {
                        field: Some(input.to_vec()),
                        message,
                    })
                );
            }
            assert!(system.calls.borrow().is_empty());
        }
    }

    mod unary_file_predicates {
        use super::*;

        #[test]
        fn checks_every_access_mode_after_stat_and_maps_all_failures_to_false() {
            for (operator, access_mode) in [
                (b"-r".as_slice(), AccessMode::Read),
                (b"-w".as_slice(), AccessMode::Write),
                (b"-x".as_slice(), AccessMode::Execute),
                (b"-e".as_slice(), AccessMode::Exists),
            ] {
                for (observation, expected) in [
                    (Ok(true), true),
                    (Ok(false), false),
                    (Err(SystemError::Unavailable), false),
                ] {
                    let mut system = MockSystem::default();
                    system
                        .stat_results
                        .insert(b"entry".to_vec(), Ok(stat(FileKind::Regular)));
                    system
                        .access_results
                        .insert((b"entry".to_vec(), access_mode), observation);

                    assert_eq!(
                        run_bytes(&system, &[b"test", operator, b"entry"]).unwrap(),
                        expected
                    );
                    assert_eq!(
                        *system.calls.borrow(),
                        vec![
                            MockCall::Stat(b"entry".to_vec()),
                            MockCall::Access(b"entry".to_vec(), access_mode),
                        ]
                    );
                }

                let system = MockSystem::default();
                assert!(!run_bytes(&system, &[b"test", operator, b"missing"]).unwrap());
                assert_eq!(
                    *system.calls.borrow(),
                    vec![MockCall::Stat(b"missing".to_vec())]
                );
            }
        }

        #[test]
        fn recognizes_each_followed_file_kind_and_preserves_the_fifo_socket_quirk() {
            for (operator, kind) in [
                (b"-f".as_slice(), FileKind::Regular),
                (b"-d".as_slice(), FileKind::Directory),
                (b"-c".as_slice(), FileKind::CharacterDevice),
                (b"-b".as_slice(), FileKind::BlockDevice),
                (b"-p".as_slice(), FileKind::Fifo),
                (b"-S".as_slice(), FileKind::Fifo),
            ] {
                let mut system = MockSystem::default();
                system
                    .stat_results
                    .insert(b"matching".to_vec(), Ok(stat(kind)));
                system
                    .stat_results
                    .insert(b"other".to_vec(), Ok(stat(FileKind::Other)));

                assert!(run_bytes(&system, &[b"test", operator, b"matching"]).unwrap());
                assert!(!run_bytes(&system, &[b"test", operator, b"other"]).unwrap());
                assert_eq!(
                    *system.calls.borrow(),
                    vec![
                        MockCall::Stat(b"matching".to_vec()),
                        MockCall::Stat(b"other".to_vec()),
                    ]
                );
            }

            let mut system = MockSystem::default();
            system
                .stat_results
                .insert(b"fifo".to_vec(), Ok(stat(FileKind::Fifo)));
            system
                .stat_results
                .insert(b"socket".to_vec(), Ok(stat(FileKind::Socket)));
            assert!(run_bytes(&system, &[b"test", b"-p", b"fifo"]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"-S", b"fifo"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"-S", b"socket"]).unwrap());
        }

        #[test]
        fn follows_links_for_stat_but_uses_only_lstat_for_h_and_l() {
            let mut system = MockSystem::default();
            system
                .stat_results
                .insert(b"link".to_vec(), Ok(stat(FileKind::Regular)));
            system
                .lstat_results
                .insert(b"link".to_vec(), Ok(stat(FileKind::Symlink)));
            system
                .lstat_results
                .insert(b"dangling".to_vec(), Ok(stat(FileKind::Symlink)));
            system
                .lstat_results
                .insert(b"regular".to_vec(), Ok(stat(FileKind::Regular)));

            assert!(run_bytes(&system, &[b"test", b"-f", b"link"]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"-h", b"link"]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"-L", b"dangling"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"-f", b"dangling"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"-h", b"regular"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"-L", b"missing"]).unwrap());
            assert_eq!(
                *system.calls.borrow(),
                vec![
                    MockCall::Stat(b"link".to_vec()),
                    MockCall::Lstat(b"link".to_vec()),
                    MockCall::Lstat(b"dangling".to_vec()),
                    MockCall::Stat(b"dangling".to_vec()),
                    MockCall::Lstat(b"regular".to_vec()),
                    MockCall::Lstat(b"missing".to_vec()),
                ]
            );
        }

        #[test]
        fn checks_setid_sticky_and_size_metadata() {
            for (operator, bit) in [
                (b"-u".as_slice(), 0o4000),
                (b"-g".as_slice(), 0o2000),
                (b"-k".as_slice(), 0o1000),
            ] {
                let mut with_bit = stat(FileKind::Regular);
                with_bit.mode = bit;
                let without_bit = stat(FileKind::Regular);
                let mut system = MockSystem::default();
                system.stat_results.insert(b"set".to_vec(), Ok(with_bit));
                system
                    .stat_results
                    .insert(b"clear".to_vec(), Ok(without_bit));

                assert!(run_bytes(&system, &[b"test", operator, b"set"]).unwrap());
                assert!(!run_bytes(&system, &[b"test", operator, b"clear"]).unwrap());
            }

            let mut nonempty = stat(FileKind::Regular);
            nonempty.size = 1;
            let empty = stat(FileKind::Regular);
            let mut system = MockSystem::default();
            system
                .stat_results
                .insert(b"nonempty".to_vec(), Ok(nonempty));
            system.stat_results.insert(b"empty".to_vec(), Ok(empty));
            assert!(run_bytes(&system, &[b"test", b"-s", b"nonempty"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"-s", b"empty"]).unwrap());
        }

        #[test]
        fn compares_ownership_with_effective_ids_after_stat() {
            let mut owned = stat(FileKind::Regular);
            owned.uid = 42;
            owned.gid = 84;
            let mut foreign = owned;
            foreign.uid = 43;
            foreign.gid = 85;

            let mut system = MockSystem {
                effective_uid: 42,
                effective_gid: 84,
                ..MockSystem::default()
            };
            system.stat_results.insert(b"owned".to_vec(), Ok(owned));
            system.stat_results.insert(b"foreign".to_vec(), Ok(foreign));

            assert!(run_bytes(&system, &[b"test", b"-O", b"owned"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"-O", b"foreign"]).unwrap());
            assert!(run_bytes(&system, &[b"test", b"-G", b"owned"]).unwrap());
            assert!(!run_bytes(&system, &[b"test", b"-G", b"foreign"]).unwrap());
            assert_eq!(
                *system.calls.borrow(),
                vec![
                    MockCall::Stat(b"owned".to_vec()),
                    MockCall::EffectiveUid,
                    MockCall::Stat(b"foreign".to_vec()),
                    MockCall::EffectiveUid,
                    MockCall::Stat(b"owned".to_vec()),
                    MockCall::EffectiveGid,
                    MockCall::Stat(b"foreign".to_vec()),
                    MockCall::EffectiveGid,
                ]
            );
        }

        #[test]
        fn every_ordinary_file_predicate_stops_after_failed_stat() {
            for operator in [
                b"-r".as_slice(),
                b"-w".as_slice(),
                b"-x".as_slice(),
                b"-e".as_slice(),
                b"-f".as_slice(),
                b"-d".as_slice(),
                b"-c".as_slice(),
                b"-b".as_slice(),
                b"-p".as_slice(),
                b"-S".as_slice(),
                b"-u".as_slice(),
                b"-g".as_slice(),
                b"-k".as_slice(),
                b"-s".as_slice(),
                b"-O".as_slice(),
                b"-G".as_slice(),
            ] {
                let system = MockSystem::default();
                assert!(!run_bytes(&system, &[b"test", operator, b"missing"]).unwrap());
                assert_eq!(
                    *system.calls.borrow(),
                    vec![MockCall::Stat(b"missing".to_vec())],
                    "{operator:?}"
                );
            }
        }
    }

    mod file_relations {
        use super::*;

        fn assert_relation(
            system: &MockSystem,
            left: &[u8],
            operator: &[u8],
            right: &[u8],
            expected: bool,
        ) {
            system.calls.borrow_mut().clear();
            assert_eq!(
                run_bytes(system, &[b"test", left, operator, right]).unwrap(),
                expected
            );
            assert_eq!(
                *system.calls.borrow(),
                vec![
                    MockCall::Stat(left.to_vec()),
                    MockCall::Stat(right.to_vec()),
                ]
            );
        }

        #[test]
        fn compares_mtimes_strictly_at_whole_second_resolution() {
            let mut system = MockSystem::default();
            let mut new = stat(FileKind::Regular);
            new.mtime_secs = 20;
            let mut old = stat(FileKind::Regular);
            old.mtime_secs = 10;
            let mut same_second = stat(FileKind::Directory);
            same_second.mtime_secs = 20;
            same_second.mode = 0o7777;
            same_second.size = 99;
            same_second.ino = 999;
            system.stat_results.insert(b"new".to_vec(), Ok(new));
            system.stat_results.insert(b"old".to_vec(), Ok(old));
            system
                .stat_results
                .insert(b"same-second".to_vec(), Ok(same_second));

            assert_relation(&system, b"new", b"-nt", b"old", true);
            assert_relation(&system, b"old", b"-nt", b"new", false);
            assert_relation(&system, b"old", b"-ot", b"new", true);
            assert_relation(&system, b"new", b"-ot", b"old", false);

            // Distinct snapshots in the same second remain equal for time
            // predicates because FileStat deliberately carries no nanoseconds.
            assert_relation(&system, b"new", b"-nt", b"same-second", false);
            assert_relation(&system, b"new", b"-ot", b"same-second", false);
        }

        #[test]
        fn compares_only_device_and_inode_for_file_identity() {
            let mut system = MockSystem::default();
            let mut left = stat(FileKind::Regular);
            left.dev = 9;
            left.ino = 42;
            left.mtime_secs = 10;
            let mut same = stat(FileKind::Directory);
            same.dev = 9;
            same.ino = 42;
            same.mtime_secs = 999;
            let mut different_device = left;
            different_device.dev = 10;
            let mut different_inode = left;
            different_inode.ino = 43;
            system.stat_results.insert(b"left".to_vec(), Ok(left));
            system.stat_results.insert(b"same".to_vec(), Ok(same));
            system
                .stat_results
                .insert(b"different-device".to_vec(), Ok(different_device));
            system
                .stat_results
                .insert(b"different-inode".to_vec(), Ok(different_inode));

            assert_relation(&system, b"left", b"-ef", b"same", true);
            assert_relation(&system, b"left", b"-ef", b"different-device", false);
            assert_relation(&system, b"left", b"-ef", b"different-inode", false);
        }

        #[test]
        fn returns_false_in_source_lookup_order_when_either_stat_fails() {
            for operator in [b"-nt".as_slice(), b"-ot".as_slice(), b"-ef".as_slice()] {
                let first_failure = MockSystem::default();
                assert!(!run_bytes(
                    &first_failure,
                    &[b"test", b"missing-left", operator, b"right"],
                )
                .unwrap());
                assert_eq!(
                    *first_failure.calls.borrow(),
                    vec![MockCall::Stat(b"missing-left".to_vec())]
                );

                let mut second_failure = MockSystem::default();
                second_failure
                    .stat_results
                    .insert(b"left".to_vec(), Ok(stat(FileKind::Regular)));
                assert!(!run_bytes(
                    &second_failure,
                    &[b"test", b"left", operator, b"missing-right"],
                )
                .unwrap());
                assert_eq!(
                    *second_failure.calls.borrow(),
                    vec![
                        MockCall::Stat(b"left".to_vec()),
                        MockCall::Stat(b"missing-right".to_vec()),
                    ]
                );
            }
        }
    }

    mod process_contract {
        use super::*;

        fn invoke(system: &MockSystem, arguments: &[&[u8]]) -> (i32, Vec<u8>, Vec<u8>) {
            let arguments = os_args(arguments);
            let program_name = arguments
                .first()
                .map(|argument| short_program_name(argument.as_os_str().as_bytes()))
                .unwrap_or_default();
            let stdout = Vec::new();
            let mut stderr = Vec::new();
            let status = finish_result(run(&arguments, system), program_name, &mut stderr);
            (status, stdout, stderr)
        }

        #[test]
        fn maps_true_and_false_to_silent_zero_and_one_statuses() {
            let system = MockSystem::default();

            assert_eq!(
                invoke(&system, &[b"test", b"value"]),
                (0, Vec::new(), Vec::new())
            );
            assert_eq!(
                invoke(&system, &[b"test", b""]),
                (1, Vec::new(), Vec::new())
            );
        }

        #[test]
        fn maps_every_fixed_error_family_to_status_two_and_exact_stderr() {
            let system = MockSystem::default();
            let cases: &[(&[&[u8]], &[u8])] = &[
                (&[b"[", b"value"], b"[: missing ]\n"),
                (&[b"test", b"value", b"-a"], b"test: argument expected\n"),
                (
                    &[b"test", b"(", b"value"],
                    b"test: closing paren expected\n",
                ),
                (
                    &[b"test", b"left", b"-unknown", b"right"],
                    b"test: -unknown: unknown operand\n",
                ),
                (
                    &[b"test", b"left-error", b"-eq", b"0"],
                    b"test: left-error: invalid\n",
                ),
                (&[b"test", b"-t", b"-1"], b"test: -1: too small\n"),
                (
                    &[b"test", b"-t", b"2147483648"],
                    b"test: 2147483648: too large\n",
                ),
            ];

            for (arguments, expected_stderr) in cases {
                assert_eq!(
                    invoke(&system, arguments),
                    (2, Vec::new(), expected_stderr.to_vec()),
                    "{arguments:?}"
                );
            }

            let arguments = vec![b"left".to_vec(), b"-a".to_vec(), b"right".to_vec()];
            let mut parser = Parser::new(&arguments, &system);
            let mut stderr = Vec::new();
            assert_eq!(finish_result(parser.binop(), b"test", &mut stderr), 2);
            assert_eq!(stderr, b"test: -a: not a binary operator\n");
        }

        #[test]
        fn distinguishes_optional_empty_syntax_fields_from_mandatory_numeric_fields() {
            let system = MockSystem::default();

            assert_eq!(
                invoke(&system, &[b"test", b"value", b""]),
                (2, Vec::new(), b"test: unknown operand\n".to_vec())
            );
            assert_eq!(
                invoke(&system, &[b"test", b"", b"-eq", b"0"]),
                (2, Vec::new(), b"test: : invalid\n".to_vec())
            );
        }

        #[test]
        fn preserves_raw_non_utf8_program_and_operand_bytes() {
            let system = MockSystem::default();
            let invalid = &[b'1', 0xff][..];

            assert_eq!(
                invoke(&system, &[b"/tmp/\xfeprog", b"0", b"-eq", invalid]),
                (2, Vec::new(), b"\xfeprog: 1\xff: invalid\n".to_vec())
            );
        }

        struct FailingWriter;

        impl Write for FailingWriter {
            fn write(&mut self, _buffer: &[u8]) -> io::Result<usize> {
                Err(io::Error::new(
                    io::ErrorKind::BrokenPipe,
                    "stderr unavailable",
                ))
            }

            fn flush(&mut self) -> io::Result<()> {
                Ok(())
            }
        }

        #[test]
        fn keeps_status_two_when_stderr_cannot_be_written() {
            let mut stderr = FailingWriter;
            assert_eq!(
                finish_result(
                    Err(syntax(None, b"argument expected")),
                    b"test",
                    &mut stderr,
                ),
                2
            );
        }
    }
}
