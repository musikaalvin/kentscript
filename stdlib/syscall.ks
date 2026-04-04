:: syscall - High-level syscall interface

:: File operations
func open(path, flags, mode) {
    return system_syscall(2, path, flags, mode);
}

func close(fd) {
    return system_syscall(3, fd);
}

func read(fd, buf, count) {
    return system_syscall(0, fd, buf, count);
}

func write(fd, data, count) {
    if type(data) == "str" {
        return system_syscall(1, fd, data, count);
    }
    return system_syscall(0, fd, data, count);
}

:: Process operations
func exit(code) {
    system_syscall(60, code);
}

func fork() {
    return system_syscall(57);
}

func getpid() {
    return system_syscall(39);
}

func getppid() {
    return system_syscall(110);
}

func execve(path, argv, envp) {
    return system_syscall(59, path, argv, envp);
}

func wait4(pid, status, options) {
    return system_syscall(61, pid, status, options, 0);
}

:: Memory operations
func mmap(addr, length, prot, flags, fd, offset) {
    return system_syscall(9, addr, length, prot, flags, fd, offset) as ptr;
}

func munmap(addr, length) {
    return system_syscall(11, addr, length);
}

func mprotect(addr, length, prot) {
    return system_syscall(10, addr, length, prot);
}

func brk(addr) {
    return system_syscall(12, addr) as ptr;
}

:: File system operations
func stat(path, statbuf) {
    return system_syscall(4, path, statbuf);
}

func lseek(fd, offset, whence) {
    return system_syscall(8, fd, offset, whence);
}

func mkdir(path, mode) {
    return system_syscall(83, path, mode);
}

func rmdir(path) {
    return system_syscall(84, path);
}

func unlink(path) {
    return system_syscall(87, path);
}

func rename(oldpath, newpath) {
    return system_syscall(82, oldpath, newpath);
}

func chmod(path, mode) {
    return system_syscall(90, path, mode);
}

func chown(path, uid, gid) {
    return system_syscall(92, path, uid, gid);
}

:: Network operations
func socket(domain, type, protocol) {
    return system_syscall(41, domain, type, protocol);
}

func bind(sockfd, addr, addrlen) {
    return system_syscall(49, sockfd, addr, addrlen);
}

func listen(sockfd, backlog) {
    return system_syscall(50, sockfd, backlog);
}

func accept(sockfd, addr, addrlen) {
    return system_syscall(43, sockfd, addr, addrlen);
}

func connect(sockfd, addr, addrlen) {
    return system_syscall(42, sockfd, addr, addrlen);
}

func send(sockfd, buf, len, flags) {
    return system_syscall(44, sockfd, buf, len, flags);
}

func recv(sockfd, buf, len, flags) {
    return system_syscall(45, sockfd, buf, len, flags);
}

:: Time operations
func time() {
    return system_syscall(201, 0);
}

func nanosleep(req, rem) {
    return system_syscall(35, req, rem);
}

func gettimeofday(tv, tz) {
    return system_syscall(96, tv, tz);
}

:: Signal operations
func kill(pid, sig) {
    return system_syscall(62, pid, sig);
}

func signal(signum, handler) {
    return system_syscall(48, signum, handler) as ptr;
}

:: Generic syscall
func call(number, ...args) {
    return system_syscall(number, ...args);
}

:: Constants
const O_RDONLY = 0;
const O_WRONLY = 1;
const O_RDWR = 2;
const O_CREAT = 64;
const O_TRUNC = 512;
const O_APPEND = 1024;

const PROT_READ = 1;
const PROT_WRITE = 2;
const PROT_EXEC = 4;

const MAP_SHARED = 1;
const MAP_PRIVATE = 2;
const MAP_ANONYMOUS = 32;

const SEEK_SET = 0;
const SEEK_CUR = 1;
const SEEK_END = 2;

:: Runtime interface - works in both interpreter and compiler
func system_syscall(number, ...args) {
    return syscall(number, ...args);
}

export {
    open, close, read, write,
    exit, fork, getpid, getppid, execve, wait4,
    mmap, munmap, mprotect, brk,
    stat, lseek, mkdir, rmdir, unlink, rename, chmod, chown,
    socket, bind, listen, accept, connect, send, recv,
    time, nanosleep, gettimeofday,
    kill, signal,
    call,
    O_RDONLY, O_WRONLY, O_RDWR, O_CREAT, O_TRUNC, O_APPEND,
    PROT_READ, PROT_WRITE, PROT_EXEC,
    MAP_SHARED, MAP_PRIVATE, MAP_ANONYMOUS,
    SEEK_SET, SEEK_CUR, SEEK_END
};
