use std::fs::{File, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom, Write};

/// Sentinel value used to represent EOF / a failed read, mirroring the way
/// the original C code treats `fgetc`'s `EOF` (cast down to `char`).
pub const EOF_CHAR: char = '\0';

pub fn create_file(path: &str) -> io::Result<File> {
    OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .open(path)
}

pub fn get_file(path: &str, mode: &str) -> io::Result<File> {
    let mut opts = OpenOptions::new();
    match mode {
        "w" => {
            opts.write(true).create(true).truncate(true);
        }
        "a" => {
            opts.append(true).create(true);
        }
        "r+" => {
            opts.read(true).write(true);
        }
        _ => {
            opts.read(true);
        }
    }
    opts.open(path)
}

pub fn write_to_file(file: &mut File, content: &str) -> io::Result<()> {
    file.write_all(content.as_bytes())?;
    file.seek(SeekFrom::Start(0))?;
    Ok(())
}

pub fn delete_file(path: &str) -> io::Result<()> {
    std::fs::remove_file(path)
}

pub fn close_file(file: File) -> io::Result<()> {
    drop(file);
    Ok(())
}

pub fn next(file: &mut File) -> io::Result<char> {
    let mut buf = [0u8; 1];
    match file.read(&mut buf) {
        Ok(0) => Ok(EOF_CHAR),
        Ok(_) => Ok(buf[0] as char),
        Err(e) => Err(e),
    }
}
