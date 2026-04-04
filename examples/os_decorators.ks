// KentScript OS-Level Decorators Demo
// This example demonstrates bare-metal kernel development features

// Kernel function - no libc dependencies, no inline
@kernel
func kernel_init() {
    print("Kernel initialized");
    return 0;
}

// Interrupt handler - marks function as ISR
@interrupt(0)
func timer_interrupt_handler() {
    print("Timer tick!");
    return;
}

// Syscall handler - system call implementation
@syscall(1)
func sys_write(fd: int, buf: ptr, count: int) -> int {
    return count;
}

// Naked function - no prologue/epilogue (for boot code)
@naked
func boot_jump() {
    asm("jmp kmain");
}

// Always inline function - always inline
@always_inline
func min(a: int, b: int) -> int {
    if a < b { return a; }
    return b;
}

// Aligned function - align to 16 bytes
@aligned(16)
func aligned_data_access(ptr: ptr) -> int {
    return ptr_read(ptr, 8);
}

// Section placement - ELF section
@section(".init")
func init_code() {
    print("Init section");
    return;
}

// Volatile memory access - no caching
@volatile_mem
func read_device_register(addr: int) -> int {
    return ptr_read(addr as ptr, 4);
}

// Packed struct - no padding
@packed
class PackedHeader {
    func __init__(sig: int, size: int) {
        self.sig = sig;
        self.size = size;
    }
}

// Kernel main
func main() {
    kernel_init();
    
    let header = PackedHeader(0xDEADBEEF, 256);
    println("Header sig: " + str(header.sig));
    
    let result = min(10, 20);
    println("min(10, 20) = " + str(result));
    
    println("OS decorators demo complete!");
    return 0;
}
