use std::fs::{File, OpenOptions};
use std::io::{self, Write};
use std::io::{Read, Seek, SeekFrom};

pub fn create_file(path: &str) -> io::Result<File> {
    File::create(path)
}
pub fn get_file(path: &str, mode: &str) -> io::Result<File> {
    match mode {
        "r" => File::open(path),
        "w" => File::create(path),
        _ => OpenOptions::new().read(true).write(true).open(path),
    }
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
        Ok(1) => Ok(buf[0] as char),
        Ok(_) => Ok('\u{0}'),
        Err(e) => Err(e),
    }
}
