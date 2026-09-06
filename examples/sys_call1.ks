import syscall;
let pid = syscall.getpid();
print("PID:", pid);

unsafe {
    let ptr = malloc(256);
    write_byte(ptr, 0, 65);
    print("Memory:", read_byte(ptr, 0));
    free(ptr);
};