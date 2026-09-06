:: os - Operating System Interface
:: Security Hardened Version
:: Added path traversal / command injection protection (ported from os.ks.backup)

import security as ksecurity;

let _os_safe_mode = true;
let _os_allowed_dirs = [];

:: Set safe mode (enabled by default)
func set_safe_mode(enabled) {
    _os_safe_mode = enabled;
}

:: Set allowed directories for file operations
func set_allowed_dirs(dirs) {
    _os_allowed_dirs = dirs;
}

:: Validate path against security rules
func _validate_path(path, operation) {
    if path == none || path == "" {
        raise "SecurityError: " + operation + ": Path cannot be empty";
    }

    if _os_safe_mode {
        let normalized = path.replace("\\", "/");

        if normalized.startswith("/") && !normalized.startswith("/home/") && !normalized.startswith("/tmp/") {
            raise "SecurityError: " + operation + ": Absolute paths not allowed in safe mode";
        }

        if normalized.contains("../") {
            raise "SecurityError: " + operation + ": Path traversal detected: " + path;
        }

        if _os_allowed_dirs.length > 0 {
            let is_allowed = false;
            for dir in _os_allowed_dirs {
                if normalized.startswith(dir) {
                    is_allowed = true;
                    break;
                }
            }
            if !is_allowed {
                raise "SecurityError: " + operation + ": Path not in allowed directories";
            }
        }
    }

    return path;
}

:: Validate path for read operations
func _validate_read_path(path) {
    return _validate_path(path, "read");
}

:: Validate path for write operations
func _validate_write_path(path) {
    return _validate_path(path, "write");
}

:: Validate path for delete operations
func _validate_delete_path(path) {
    return _validate_path(path, "delete");
}

func name() {
    return os_name();
}

func environ() {
    return os_environ();
}

func getenv(key, default) {
    if key == none || key == "" {
        raise "ValidationError: Environment variable key cannot be empty";
    }
    let env = environ();
    return env[key] != none ? env[key] : default;
}

func putenv(key, value) {
    if key == none || key == "" {
        raise "ValidationError: Environment variable key cannot be empty";
    }
    os_putenv(key, value);
}

func unsetenv(key) {
    if key == none || key == "" {
        raise "ValidationError: Environment variable key cannot be empty";
    }
    os_unsetenv(key);
}

func getcwd() {
    return os_getcwd();
}

func chdir(path) {
    if path == none || path == "" {
        raise "ValidationError: Path cannot be empty";
    }
    let safe_path = _validate_path(path, "chdir");
    os_chdir(safe_path);
}

func listdir(path) {
    if path == none { path = "."; }
    let safe_path = _validate_read_path(path);
    return os_listdir(safe_path);
}

func mkdir(path, mode) {
    if path == none || path == "" {
        raise "ValidationError: Path cannot be empty";
    }
    let safe_path = _validate_write_path(path);
    if mode == none { mode = 0o755; }
    os_mkdir(safe_path, mode);
}

func makedirs(path, mode, exist_ok) {
    if path == none || path == "" {
        raise "ValidationError: Path cannot be empty";
    }
    let safe_path = _validate_write_path(path);
    if mode == none { mode = 0o755; }
    if exist_ok == none { exist_ok = false; }

    if exists(safe_path) {
        if exist_ok { return; }
        raise "IOError: Directory already exists: " + safe_path;
    }

    let parts = safe_path.split("/");
    let current = "";

    for part in parts {
        if part == "" { continue; }
        current = current + "/" + part;
        if !exists(current) {
            mkdir(current, mode);
        }
    }
}

func rmdir(path) {
    if path == none || path == "" {
        raise "ValidationError: Path cannot be empty";
    }
    let safe_path = _validate_delete_path(path);
    os_rmdir(safe_path);
}

func remove(path) {
    if path == none || path == "" {
        raise "ValidationError: Path cannot be empty";
    }
    let safe_path = _validate_delete_path(path);

    if !exists(safe_path) {
        raise "IOError: File does not exist: " + safe_path;
    }

    os_remove(safe_path);
}

func rename(src, dst) {
    if src == none || src == "" {
        raise "ValidationError: Source path cannot be empty";
    }
    if dst == none || dst == "" {
        raise "ValidationError: Destination path cannot be empty";
    }
    let safe_src = _validate_write_path(src);
    let safe_dst = _validate_write_path(dst);
    os_rename(safe_src, safe_dst);
}

func stat(path) {
    if path == none || path == "" {
        raise "ValidationError: Path cannot be empty";
    }
    let safe_path = _validate_read_path(path);
    return os_stat(safe_path);
}

func lstat(path) {
    if path == none || path == "" {
        raise "ValidationError: Path cannot be empty";
    }
    let safe_path = _validate_read_path(path);
    return os_lstat(safe_path);
}

func chmod(path, mode) {
    if path == none || path == "" {
        raise "ValidationError: Path cannot be empty";
    }
    let safe_path = _validate_write_path(path);
    os_chmod(safe_path, mode);
}

func chown(path, uid, gid) {
    if path == none || path == "" {
        raise "ValidationError: Path cannot be empty";
    }
    let safe_path = _validate_write_path(path);
    os_chown(safe_path, uid, gid);
}

func link(src, dst) {
    if src == none || src == "" {
        raise "ValidationError: Source path cannot be empty";
    }
    if dst == none || dst == "" {
        raise "ValidationError: Destination path cannot be empty";
    }
    let safe_src = _validate_read_path(src);
    let safe_dst = _validate_write_path(dst);
    os_link(safe_src, safe_dst);
}

func symlink(src, dst) {
    if src == none || src == "" {
        raise "ValidationError: Source path cannot be empty";
    }
    if dst == none || dst == "" {
        raise "ValidationError: Destination path cannot be empty";
    }
    let safe_src = _validate_read_path(src);
    let safe_dst = _validate_write_path(dst);
    os_symlink(safe_src, safe_dst);
}

func readlink(path) {
    if path == none || path == "" {
        raise "ValidationError: Path cannot be empty";
    }
    let safe_path = _validate_read_path(path);
    return os_readlink(safe_path);
}

func exists(path) {
    if path == none || path == "" {
        return false;
    }
    let safe_path = _validate_read_path(path);
    return os_exists(safe_path);
}

func isfile(path) {
    if path == none || path == "" {
        return false;
    }
    let safe_path = _validate_read_path(path);
    return os_isfile(safe_path);
}

func isdir(path) {
    if path == none || path == "" {
        return false;
    }
    let safe_path = _validate_read_path(path);
    return os_isdir(safe_path);
}

func islink(path) {
    if path == none || path == "" {
        return false;
    }
    let safe_path = _validate_read_path(path);
    return os_islink(safe_path);
}

func getpid() {
    return os_getpid();
}

func getppid() {
    return os_getppid();
}

func getuid() {
    return os_getuid();
}

func getgid() {
    return os_getgid();
}

func kill(pid, signal) {
    if pid == none || pid <= 0 {
        raise "ValidationError: Invalid process ID";
    }
    if signal == none { signal = 15; }
    os_kill(pid, signal);
}

func system(command) {
    if command == none || command == "" {
        raise "ValidationError: Command cannot be empty";
    }

    if _os_safe_mode {
        if command.contains(";") || command.contains("&&") || command.contains("||") {
            raise "SecurityError: Potential command injection detected";
        }
        if command.contains("|") || command.contains("`") {
            raise "SecurityError: Potential command injection detected";
        }
        if command.contains("$(") || command.contains("${") {
            raise "SecurityError: Potential command injection detected";
        }
    }

    return os_system(command);
}

func popen(command, mode) {
    if command == none || command == "" {
        raise "ValidationError: Command cannot be empty";
    }

    if _os_safe_mode {
        if command.contains(";") || command.contains("&&") || command.contains("||") {
            raise "SecurityError: Potential command injection detected";
        }
    }

    if mode == none { mode = "r"; }
    return os_popen(command, mode);
}

func walk(top, visited) {
    if top == none || top == "" {
        raise "ValidationError: Path cannot be empty";
    }
    let safe_top = _validate_read_path(top);

    if visited == none { visited = {}; }

    :: Prevent infinite recursion from circular symlinks
    if visited[safe_top] {
        return [];
    }
    visited[safe_top] = true;

    let dirs = [];
    let files = [];

    for entry in listdir(safe_top) {
        let path = safe_top + "/" + entry;
        if isdir(path) {
            dirs.push(entry);
        } else {
            files.push(entry);
        }
    }

    let result = [[safe_top, dirs, files]];

    for dir in dirs {
        let subpath = safe_top + "/" + dir;
        let sub_result = walk(subpath, visited);
        for item in sub_result {
            result.push(item);
        }
    }

    return result;
}

:: Runtime interface (these are provided by the runtime)
func os_name() { return "posix"; }
func os_environ() { return {"PATH": "/usr/bin", "HOME": "/home/user"}; }
func os_putenv(key, value) { }
func os_unsetenv(key) { }
func os_getcwd() { return "/home/user"; }
func os_chdir(path) { }
func os_listdir(path) { return ["file1.txt", "file2.txt"]; }
func os_mkdir(path, mode) { }
func os_rmdir(path) { }
func os_remove(path) { }
func os_rename(src, dst) { }
func os_stat(path) { return {"size": 1024, "mtime": 1709640000}; }
func os_lstat(path) { return os_stat(path); }
func os_chmod(path, mode) { }
func os_chown(path, uid, gid) { }
func os_link(src, dst) { }
func os_symlink(src, dst) { }
func os_readlink(path) { return path; }
func os_exists(path) { return true; }
func os_isfile(path) { return true; }
func os_isdir(path) { return false; }
func os_islink(path) { return false; }
func os_getpid() { return 1234; }
func os_getppid() { return 1; }
func os_getuid() { return 1000; }
func os_getgid() { return 1000; }
func os_kill(pid, signal) { }
func os_system(command) { return 0; }
func os_popen(command, mode) { return none; }

export {
    set_safe_mode, set_allowed_dirs,
    name, environ, getenv, putenv, unsetenv,
    getcwd, chdir, listdir, mkdir, makedirs, rmdir,
    remove, rename, stat, lstat, chmod, chown,
    link, symlink, readlink,
    exists, isfile, isdir, islink,
    getpid, getppid, getuid, getgid, kill,
    system, popen, walk
};
