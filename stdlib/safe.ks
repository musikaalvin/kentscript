:: safe - Safe wrappers around unsafe operations
:: Provides memory-safe alternatives to low-level operations

:: Safe malloc - returns null pointer (0) on failure instead of crashing
func safe_malloc(size: int) -> int {
    if size <= 0 {
        return 0;
    }
    let ptr = malloc(size);
    return ptr;
}

:: Safe free - only frees non-null pointers
func safe_free(ptr: int) {
    if ptr != 0 && ptr != null {
        free(ptr);
    }
}

:: Safe read - returns default value if address is invalid
func safe_read(addr: int, offset: int, size: int, default_val: int) -> int {
    if addr == 0 || addr == null {
        return default_val;
    }
    if offset < 0 {
        return default_val;
    }
    return read_word(addr, offset, size);
}

:: Safe write - returns false if address is invalid
func safe_write(addr: int, offset: int, size: int, value: int) -> bool {
    if addr == 0 || addr == null {
        return false;
    }
    if offset < 0 {
        return false;
    }
    write_word(addr, offset, value, size);
    return true;
}

:: Safe dereference - returns optional-like tuple (success, value)
func safe_deref(addr: int, size: int) -> (bool, int) {
    if addr == 0 || addr == null {
        return (false, 0);
    }
    let value = read_word(addr, 0, size);
    return (true, value);
}

:: Safe write value - returns success status
func safe_deref_write(addr: int, size: int, value: int) -> bool {
    if addr == 0 || addr == null {
        return false;
    }
    write_word(addr, 0, value, size);
    return true;
}

:: Bounds-checked array access
func array_get(arr: int, index: int, elem_size: int, len: int, default_val: int) -> int {
    if index < 0 || index >= len {
        return default_val;
    }
    let addr = arr + (index * elem_size);
    return safe_read(addr, 0, elem_size, default_val);
}

:: Bounds-checked array write
func array_set(arr: int, index: int, elem_size: int, len: int, value: int) -> bool {
    if index < 0 || index >= len {
        return false;
    }
    let addr = arr + (index * elem_size);
    return safe_write(addr, 0, elem_size, value);
}

:: Safe string length
func safe_strlen(addr: int, max_len: int) -> int {
    if addr == 0 || addr == null {
        return 0;
    }
    let len = 0;
    while len < max_len {
        let byte = read_byte(addr, len);
        if byte == 0 {
            return len;
        }
        len = len + 1;
    }
    return max_len;
}

:: Safe string copy with bounds checking
func safe_strcpy(dest: int, src: int, max_len: int) -> int {
    if dest == 0 || dest == null || src == 0 || src == null {
        return 0;
    }
    let len = safe_strlen(src, max_len);
    if len > 0 {
        memcpy(dest, 0, src, 0, len + 1);
    }
    return len;
}

:: Safe memset
func safe_memset(addr: int, value: int, size: int) -> bool {
    if addr == 0 || addr == null || size <= 0 {
        return false;
    }
    memset(addr, 0, value, size);
    return true;
}

:: Safe memcpy
func safe_memcpy(dest: int, src: int, size: int) -> bool {
    if dest == 0 || dest == null || src == 0 || src == null || size <= 0 {
        return false;
    }
    memcpy(dest, 0, src, 0, size);
    return true;
}

:: Safe pointer arithmetic with bounds
func safe_ptr_add(ptr: int, offset: int, max_addr: int) -> int {
    if ptr == 0 || ptr == null {
        return 0;
    }
    let result = ptr + offset;
    if max_addr > 0 && result > max_addr {
        return 0;
    }
    return result;
}

:: Check if pointer is in valid range
func ptr_in_range(ptr: int, start: int, end: int) -> bool {
    if ptr == 0 || ptr == null {
        return false;
    }
    return ptr >= start && ptr <= end;
}

:: Zero-safe null check
func is_null(ptr: int) -> bool {
    return ptr == 0 || ptr == null;
}

:: Non-null assertion (panics if null)
func expect_non_null(ptr: int, msg: str) -> int {
    if ptr == 0 || ptr == null {
        panic("Unexpected null pointer: " + msg);
    }
    return ptr;
}

:: Safe syscall wrapper
func safe_syscall(num: int, arg1: int, arg2: int, arg3: int, arg4: int, arg5: int, arg6: int) -> int {
    unsafe {
        return syscall(num, arg1, arg2, arg3, arg4, arg5, arg6);
    }
}
