:: os - Operating system interface
import security as ksecurity;

func name() {
    return os_name();
}

func environ() {
    return os_environ();
}

func getenv(key, default) {
    let env = environ();
    return env[key] != none ? env[key] : default;
}

func putenv(key, value) {
    os_putenv(key, value);
}

func unsetenv(key) {
    os_unsetenv(key);
}

func getcwd() {
    return os_getcwd();
}

func chdir(path) {
    os_chdir(path);
}

func listdir(path) {
    if path == none { path = "."; }
    return os_listdir(path);
}

func mkdir(path, mode) {
    if mode == none { mode = 0o755; }
    os_mkdir(path, mode);
}

func makedirs(path, mode, exist_ok) {
    if mode == none { mode = 0o755; }
    if exist_ok == none { exist_ok = false; }
    
    if os_exists(path) {
        if exist_ok { return; }
        raise "Directory already exists";
    }
    
    let parts = path.split("/");
    let current = "";
    
    for part in parts {
        if part == "" { continue; }
        current = current + "/" + part;
        if !os_exists(current) {
            mkdir(current, mode);
        }
    }
}

func rmdir(path) {
    os_rmdir(path);
}

func remove(path) {
    os_remove(path);
}

func rename(src, dst) {
    os_rename(src, dst);
}

func stat(path) {
    return os_stat(path);
}

func lstat(path) {
    return os_lstat(path);
}

func chmod(path, mode) {
    os_chmod(path, mode);
}

func chown(path, uid, gid) {
    os_chown(path, uid, gid);
}

func link(src, dst) {
    os_link(src, dst);
}

func symlink(src, dst) {
    os_symlink(src, dst);
}

func readlink(path) {
    return os_readlink(path);
}

func exists(path) {
    return os_exists(path);
}

func isfile(path) {
    return os_isfile(path);
}

func isdir(path) {
    return os_isdir(path);
}

func islink(path) {
    return os_islink(path);
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
    os_kill(pid, signal);
}

func system(command) {
    return os_system(command);
}

func popen(command, mode) {
    if mode == none { mode = "r"; }
    return os_popen(command, mode);
}

func walk(top, visited) {
    if visited == none { visited = {}; }
    
    :: Prevent infinite recursion from circular symlinks
    if visited[top] {
        return [];
    }
    visited[top] = true;
    
    let dirs = [];
    let files = [];
    
    for entry in listdir(top) {
        let path = top + "/" + entry;
        if isdir(path) {
            dirs.push(entry);
        } else {
            files.push(entry);
        }
    }
    
    let result = [[top, dirs, files]];
    
    for dir in dirs {
        let subpath = top + "/" + dir;
        let sub_result = walk(subpath, visited);
        for item in sub_result {
            result.push(item);
        }
    }
    
    return result;
}

:: Runtime interface
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
    name, environ, getenv, putenv, unsetenv,
    getcwd, chdir, listdir, mkdir, makedirs, rmdir,
    remove, rename, stat, lstat, chmod, chown,
    link, symlink, readlink,
    exists, isfile, isdir, islink,
    getpid, getppid, getuid, getgid, kill,
    system, popen, walk
};
