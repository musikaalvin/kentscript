import syscall;

let fd = syscall.open("/dev/tty", 1);
let msg = "Hello";
let bytes = syscall.write(fd, msg, len(msg));
syscall.close(fd);
