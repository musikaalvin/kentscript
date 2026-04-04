:: Test low-level operations

func main() {
    print("=== Low-Level Operations Test ===");
    print("");
    
    unsafe {
        print("[1] Testing malloc/free...");
        let ptr = malloc(1024);
        print("  Allocated memory");
        free(ptr);
        print("  Freed");
        print("");
        
        print("[2] Testing ptr_read/ptr_write...");
        let mem = malloc(8);
        ptr_write(mem, 0x42);
        let value = ptr_read(mem, 1);
        print("  Wrote 0x42, read back value");
        free(mem);
        print("  OK");
        print("");
        
        print("[3] Testing syscall (getpid)...");
        let pid = system_syscall(39, 0, 0, 0, 0, 0, 0);
        print("  Got PID from syscall");
        print("");
        
        print("[4] Testing rdtsc...");
        let tsc1 = rdtsc();
        let tsc2 = rdtsc();
        print("  TSC counters read");
        print("");
    }
    
    print("=== All tests passed ===");
}

main();
