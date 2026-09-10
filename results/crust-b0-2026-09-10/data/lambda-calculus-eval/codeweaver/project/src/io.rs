use std::fs::{File, OpenOptions};
use std::io::{self, Read, Seek, Write};
use crate::common;
pub fn create_file(path: &str) -> io::Result<File> {
    File::create(path)
}
pub fn get_file(path: &str, mode: &str) -> io::Result<File> {
    let mut options = OpenOptions::new();
    if mode.contains('r') {
        options.read(true);
    }
    if mode.contains('w') {
        options.write(true).create(true).truncate(true);
    }
    if mode.contains('a') {
        options.append(true).create(true);
    }
    if mode.contains('+') {
        options.read(true).write(true);
    }
    options.open(path)
}
pub fn write_to_file(file: &mut File, content: &str) -> io::Result<()> {
    file.write_all(content.as_bytes())?;
    file.rewind()?;
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
    match file.read(&mut buf)? {
        0 => Ok(common::EOF_SENTINEL),
        _ => Ok(buf[0] as char),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Fixture-based: real temp files under std::env::temp_dir() (no tempfile crate,
    // no mocks -- the C original never abstracted FILE* behind an interface).

    fn temp_path(name: &str) -> String {
        std::env::temp_dir()
            .join(format!("lce_io_test_{}_{}", std::process::id(), name))
            .to_string_lossy()
            .into_owned()
    }

    #[test]
    fn test_create_write_get_roundtrip() {
        let path = temp_path("roundtrip");
        let mut file = create_file(&path).expect("create_file failed");
        write_to_file(&mut file, "hello world").expect("write_to_file failed");
        let mut read_file = get_file(&path, "r").expect("get_file failed");
        let mut contents = String::new();
        read_file.read_to_string(&mut contents).expect("read failed");
        assert_eq!(contents, "hello world");
        drop(read_file);
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn test_delete_file_then_get_file_errors() {
        let path = temp_path("delete");
        let file = create_file(&path).expect("create_file failed");
        drop(file);
        delete_file(&path).expect("delete_file failed");
        assert!(get_file(&path, "r").is_err());
    }

    #[test]
    fn test_next_reads_one_byte_and_advances_cursor() {
        let path = temp_path("next");
        let mut file = create_file(&path).expect("create_file failed");
        write_to_file(&mut file, "ab").expect("write_to_file failed");
        drop(file);
        let mut read_file = get_file(&path, "r").expect("get_file failed");
        let c1 = next(&mut read_file).expect("next failed");
        let c2 = next(&mut read_file).expect("next failed");
        assert_eq!(c1, 'a');
        assert_eq!(c2, 'b');
        let _ = std::fs::remove_file(&path);
    }
}