import syscall;
let fd = syscall.open("/sdcard/mgs.txt", 0o666);
syscall.write(fd, "bursted 😹!");
syscall.close(fd);

let stats = syscall.stat("/sdcard/mgs.txt");
print("File size:", stats["size"]);