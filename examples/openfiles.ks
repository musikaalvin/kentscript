:: No conditionals version
import syscall;

let fd = syscall.open("/home/pylord/Documents/apikeys.txt", 0);

:: Read regardless
let data = syscall.read(fd, 4096);

:: Print result
print(data);

:: Clean up
syscall.close(fd);
