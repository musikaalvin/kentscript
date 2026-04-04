:: memory - High-level memory management with low-level power

:: Allocate memory
func alloc(size: int) -> int {
    return system_malloc(size);
}

:: Free memory
func free(address: int) {
    system_free(address);
}

:: Copy memory
func copy(dest: int, src: int, size: int) {
    system_memcpy(dest, src, size);
}

:: Set memory
func set(address: int, value: int, size: int) {
    system_memset(address, value, size);
}

:: Compare memory
func compare(addr1: int, addr2: int, size: int) -> int {
    return system_memcmp(addr1, addr2, size);
}

:: Create pointer from address
func ptr_from(address: int) -> int {
    return address;
}

:: Get pointer address
func ptr_addr(address: int) -> int {
    return address;
}

:: Read from pointer
func read(address: int) -> int {
    return read_word(address, 0, 8);
}

:: Write to pointer
func write(address: int, value: int) {
    write_word(address, 0, value, 8);
}

:: Pointer arithmetic
func ptr_add(address: int, offset: int) -> int {
    return address + offset;
}

func ptr_sub(address: int, offset: int) -> int {
    return address - offset;
}

:: Safe pointer operations
func safe_read(address: int, default_value: int) -> int {
    if address == 0 {
        return default_value;
    }
    return read(address);
}

func safe_write(address: int, value: int) -> bool {
    if address == 0 {
        return false;
    }
    write(address, value);
    return true;
}

:: Runtime interface - works in both interpreter and compiler
func system_malloc(size: int) -> int {
    return malloc(size);
}

func system_free(address: int) {
    free(address);
}

func system_memcpy(dest: int, src: int, size: int) {
    memcpy(dest, 0, src, 0, size);
}

func system_memset(address: int, value: int, size: int) {
    memset(address, 0, value, size);
}

func system_memcmp(addr1: int, addr2: int, size: int) -> int {
    :: Simple byte-by-byte comparison
    for i in range(size) {
        let b1 = read_byte(addr1, i);
        let b2 = read_byte(addr2, i);
        if b1 != b2 {
            return b1 - b2;
        }
    }
    return 0;
}
