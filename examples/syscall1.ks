import syscall;

:: Direct kernel interface
let fd = syscall.open("/dev/mem", 2);                  :: 2 = O_RDWR
syscall.write(fd, data, len(data));
syscall.read(fd, buffer, 1024);
syscall.close(fd);

:: Process control
let pid = syscall.fork();
if pid == 0 {
    syscall.execve("/bin/sh", ["sh"], null);
} else {
    syscall.wait(pid);
}
syscall.exit(0);