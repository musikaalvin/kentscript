import syscall;
unsafe {
    let ptr = malloc(512);
    
    :: Write values
    write_byte(ptr, 0, 0x41);
    write_byte(ptr, 1, 0x42);
    write_byte(ptr, 2, 0x43);
    
    :: Read back
    let a = read_byte(ptr, 0);
    let b = read_byte(ptr, 1);
    let c = read_byte(ptr, 2);
    
    print("Values:", a, b, c);
    
    free(ptr);
};