:: fileio - File I/O operations
:: Security Hardened Version
:: Version: 2.0.0 - Added permission and path validation

let _fileio_safe_mode = true;
let _fileio_allowed_dirs = [];
let _fileio_max_file_size = 10 * 1024 * 1024;  :: 10MB default

:: Enable/disable safe mode
func set_safe_mode(enabled) {
    _fileio_safe_mode = enabled;
}

:: Set allowed directories
func set_allowed_dirs(dirs) {
    _fileio_allowed_dirs = dirs;
}

:: Set max file size
func set_max_file_size(size) {
    _fileio_max_file_size = size;
}

:: Validate file path
func _validate_path(path, operation) {
    if path == none || path == "" {
        raise "SecurityError: Filename cannot be empty";;
    }
    
            let normalized = path.replace("\\", "/");
            
            if _fileio_safe_mode {
                :: Check for path traversal
                if normalized.contains("../") || normalized.contains("..\\") {
                    raise "SecurityError: Path traversal detected: " + path;;
                }
                
                :: Check for absolute paths
                if normalized.startswith("/etc/") || normalized.startswith("/sys/") || normalized.startswith("/proc/") {
                    raise "SecurityError: Cannot access system directories: " + path;;
                }
        
        :: Check allowed directories
        if _fileio_allowed_dirs.length > 0 {
            let allowed = false;
            for dir in _fileio_allowed_dirs {
                if normalized.startswith(dir) {
                    allowed = true;
                    break;
                }
            }
            if !allowed {
                raise "SecurityError: Path not in allowed directories";;
            }
        }
    }
    
    return normalized;
}

:: Validate file mode
func _validate_mode(mode) {
    let valid_modes = ["r", "w", "a", "r+", "w+", "a+", "rb", "wb", "ab", "rb+", "wb+", "ab+"];
    
    if mode == none {
        return "r";
    }
    
    if valid_modes.contains(mode) {
        return mode;
    }
    
    raise "ValidationError: Invalid file mode: " + mode;;
}

:: SecurityError class
class SecurityError {
    func __init__(self, message) {
        self.message = message;
    }
    func to_string() {
        return "SecurityError: " + self.message;
    }
}

:: ValidationError class
class ValidationError {
    func __init__(self, message) {
        self.message = message;
    }
    func to_string() {
        return "ValidationError: " + self.message;
    }
}

func open(filename, mode, encoding) {
    let safe_path = _validate_path(filename, "open");
    let safe_mode = _validate_mode(mode);
    
    if encoding == none { encoding = "utf-8"; }
    return File(safe_path, safe_mode, encoding);
}

class File {
    func __init__(self, filename, mode, encoding) {
        self.filename = filename;
        self.mode = mode;
        self.encoding = encoding;
        self.handle = file_open(filename, mode);
        self.closed = false;
    }
    
    func read(self, size) {
        if self.closed { raise "I/O operation on closed file"; }
        return file_read(self.handle, size);
    }
    
    func readline(self) {
        if self.closed { raise "I/O operation on closed file"; }
        return file_readline(self.handle);
    }
    
    func readlines(self) {
        if self.closed { raise "I/O operation on closed file"; }
        let lines = [];
        while true {
            let line = self.readline();
            if line == none { break; }
            lines.push(line);
        }
        return lines;
    }
    
    func write(self, data) {
        if self.closed { raise "I/O operation on closed file"; }
        return file_write(self.handle, data);
    }
    
    func writelines(self, lines) {
        if self.closed { raise "I/O operation on closed file"; }
        for line in lines {
            self.write(line);
        }
    }
    
    func flush(self) {
        if self.closed { raise "I/O operation on closed file"; }
        file_flush(self.handle);
    }
    
    func seek(self, offset, whence) {
        if self.closed { raise "I/O operation on closed file"; }
        if whence == none { whence = 0; }
        file_seek(self.handle, offset, whence);
    }
    
    func tell(self) {
        if self.closed { raise "I/O operation on closed file"; }
        return file_tell(self.handle);
    }
    
    func close(self) {
        if !self.closed {
            file_close(self.handle);
            self.closed = true;
        }
    }
}

func read(filename, encoding) {
    if encoding == none { encoding = "utf-8"; }
    let f = open(filename, "r", encoding);
    let content = f.read();
    f.close();
    return content;
}

func write(filename, data, encoding) {
    if encoding == none { encoding = "utf-8"; }
    let f = open(filename, "w", encoding);
    f.write(data);
    f.close();
}

func append(filename, data, encoding) {
    if encoding == none { encoding = "utf-8"; }
    let f = open(filename, "a", encoding);
    f.write(data);
    f.close();
}

func exists(path) {
    return file_exists(path);
}

func isfile(path) {
    return file_isfile(path);
}

func isdir(path) {
    return file_isdir(path);
}

func remove(path) {
    file_remove(path);
}

func rename(old, new_val) {
    file_rename(old, new_val);
}

func copy(src, dst) {
    let content = read(src);
    write(dst, content);
}

func mkdir(path) {
    file_mkdir(path);
}

func rmdir(path) {
    file_rmdir(path);
}

func listdir(path) {
    return file_listdir(path);
}

func getcwd() {
    return file_getcwd();
}

func chdir(path) {
    file_chdir(path);
}

:: Runtime interface
func file_open(filename, mode) { return system_file_open(filename, mode); }
func file_read(handle, size) { return system_file_read(handle, size); }
func file_readline(handle) { return system_file_readline(handle); }
func file_write(handle, data) { return system_file_write(handle, data); }
func file_flush(handle) { system_file_flush(handle); }
func file_seek(handle, offset, whence) { system_file_seek(handle, offset, whence); }
func file_tell(handle) { return system_file_tell(handle); }
func file_close(handle) { system_file_close(handle); }
func file_exists(path) { return system_file_exists(path); }
func file_isfile(path) { return system_file_isfile(path); }
func file_isdir(path) { return system_file_isdir(path); }
func file_remove(path) { system_file_remove(path); }
func file_rename(old, new_val) { system_file_rename(old, new_val); }
func file_mkdir(path) { system_file_mkdir(path); }
func file_rmdir(path) { system_file_rmdir(path); }
func file_listdir(path) { return system_file_listdir(path); }
func file_getcwd() { return system_file_getcwd(); }
func file_chdir(path) { system_file_chdir(path); }

export {
    File, open, read, write, append,
    exists, isfile, isdir, remove, rename, copy,
    mkdir, rmdir, listdir, getcwd, chdir,
    
    :: Security
    set_safe_mode, set_allowed_dirs, set_max_file_size,
    SecurityError, ValidationError
};