:: Unsafe blocks in KentScript by pyLord
:: run using python3 kentscript.py unsafe_syscall.ks --native --run 

unsafe {
    :: Raw memory operations
    let buffer = malloc(1024);
    
    :: Write bytes
    write_byte(buffer, 0, 72);    :: 'H'
    write_byte(buffer, 1, 105);   :: 'i'
    write_byte(buffer, 2, 0);     :: null
    
    :: Read bytes
    let c1 = read_byte(buffer, 0);
    let c2 = read_byte(buffer, 1);
    
    print("Characters: " + str(c1) + " " + str(c2));
    
    :: Hardware access
    write_port(0x3F8, 65);        :: Write to serial port
    let port_val = read_port(0x3F8);
    
    :: Memory-mapped I/O
    let mmio_addr = 0x80000000;
    write_mmio(mmio_addr, 0x12345678);
    let mmio_val = read_mmio(mmio_addr);
    
    print("MMIO value: " + str(mmio_val));
    
    :: Cleanup
    free(buffer);
}

print("Unsafe block complete");
