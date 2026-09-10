use std::fs::{File, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom, Write};

pub fn create_file(path: &str) -> io::Result<File> {
    OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .open(path)
        .map_err(|e| {
            eprintln!("ERROR: Could not create file {}\n", path);
            e
        })
}

pub fn get_file(path: &str, mode: &str) -> io::Result<File> {
    let mut opts = OpenOptions::new();
    match mode {
        "r" => {
            opts.read(true);
        }
        "w" => {
            opts.write(true).create(true).truncate(true);
        }
        "a" => {
            opts.append(true).create(true);
        }
        "r+" => {
            opts.read(true).write(true);
        }
        "w+" => {
            opts.read(true).write(true).create(true).truncate(true);
        }
        "a+" => {
            opts.read(true).append(true).create(true);
        }
        _ => {
            opts.read(true).write(true).create(true);
        }
    }
    opts.open(path).map_err(|e| {
        eprintln!("ERROR: Could not open file {}\n", path);
        e
    })
}

pub fn write_to_file(file: &mut File, content: &str) -> io::Result<()> {
    file.write_all(content.as_bytes()).map_err(|e| {
        eprintln!("ERROR: could not write to file at {}:{}\n", file!(), line!());
        e
    })?;
    file.seek(SeekFrom::Start(0)).map(|_| ())
}

pub fn delete_file(path: &str) -> io::Result<()> {
    std::fs::remove_file(path).map_err(|e| {
        eprintln!("ERROR: could not delete to file at {}:{}\n", file!(), line!());
        e
    })
}

pub fn close_file(file: File) -> io::Result<()> {
    drop(file);
    Ok(())
}

pub fn next(file: &mut File) -> io::Result<char> {
    let mut buf = [0u8; 1];
    let bytes_read = file.read(&mut buf)?;
    if bytes_read == 0 {
        // Mimic C's fgetc returning EOF (-1) cast to char
        Ok(0xFFu8 as char)
    } else {
        Ok(buf[0] as char)
    }
}
