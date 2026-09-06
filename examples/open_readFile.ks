:: File reader with emoji support
import syscall;

let fd = syscall.open("/sdcard/msg.txt", 0);
let data = syscall.read(fd, 4096);

:: Print as string (should display emoji if terminal supports UTF-8)
print(data);

