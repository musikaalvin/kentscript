import syscall;
let fd = syscall.open("/sdcard/msg.txt", 65, 0o666);
syscall.write(fd, "gotcha 😹!");
syscall.fsync(fd);
syscall.close(fd); 
let stats = syscall.stat("/sdcard/msg.txt");
print("File size:", stats["size"]);