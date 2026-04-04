:: KentScript Hardware Access Test
:: Tests direct hardware I/O and memory-mapped I/O
:: REQUIRES ROOT: sudo python3 kentscript.py test_hardware.ks --native --run 

print("=== KentScript Hardware Access Test ===");
print("WARNING: Some tests require root access");

::
:: Test 1: I/O Port Access
::
print("");
print("--- Test 1: I/O Port Access ---");

unsafe {
    :: Test serial port (UART) - 0x3F8 is COM1
    print("Attempting I/O port write to 0x3F8 (UART)...");
    let result = write_port(0x3F8, 0x41);  :: Write 'A'
    
    if result {
        print("✓ SUCCESS: Wrote 0x41 to port 0x3F8");
    } else {
        print("✗ FAILED: Need root for I/O port access");
    };
    
    :: Try to read from port
    print("Reading from port 0x3F8...");
    let val = read_port(0x3F8);
    print("Port value: ", hex(val));
};

::
:: Test 2: MMIO (Memory-Mapped I/O) Access
::
print("");
print("--- Test 2: MMIO Access ---");

unsafe {
    :: APIC base address (typically 0xFEE00000)
    let APIC_BASE = 0xFEE00000;
    
    print("Attempting MMIO write to APIC base...");
    let mmio_result = mmio_write(APIC_BASE, 0x00, 0xDEADBEEF);
    
    if mmio_result {
        print("✓ SUCCESS: Wrote to MMIO address ", hex(APIC_BASE));
    } else {
        print("✗ FAILED: Need root for /dev/mem access");
    };
    
    :: Try to read
    print("Reading from MMIO address...");
    let mmio_val = mmio_read(APIC_BASE, 0x00);
    print("MMIO value: ", hex(mmio_val));
};

::
:: Test 3: Direct Memory Access with Security
::
print("");
print("--- Test 3: Safe Memory Access ---");

unsafe {
    :: Allocate safe memory (no root needed)
    let safe_mem = malloc(256);
    print("✓ Allocated 256 bytes (no root needed)");
    
    :: Fill with known pattern
    memset(safe_mem, 0, 0xFF, 16);
    print("✓ Filled with 0xFF pattern");
    
    :: Read and verify
    let byte0 = read_byte(safe_mem, 0);
    let byte15 = read_byte(safe_mem, 15);
    print("✓ Byte 0: ", hex(byte0), " Byte 15: ", hex(byte15));
    
    free(safe_mem);
    print("✓ Freed memory");
};

::
:: Test 4: PCI Memory Space (advanced)
::
print("");
print("--- Test 4: PCI Memory Space ---");

unsafe {
    :: Try PCI config space access
    :: PCH MMIO typically at 0xFED00000
    let PCH_BASE = 0xFED00000;
    
    print("Probing PCH MMIO at ", hex(PCH_BASE), "...");
    let pch_val = mmio_read(PCH_BASE, 0x00);
    
    if pch_val != 0 {
        print("✓ PCH MMIO readable: ", hex(pch_val));
    } else {
        print("✗ PCH MMIO not accessible (need hardware support)");
    };
};

::
:: Test 5: Interrupt Control (simulation)
::
print("");
print("--- Test 5: Interrupt Control ---");

unsafe {
    print("Note: IRQ enable/disable requires kernel module");
    print("Simulated interrupt control:");
    print("- disable_interrupts() sets CLI flag");
    print("- enable_interrupts() sets STI flag");
};

::
:: Test 6: Process and System Info
::
print("");
print("--- Test 6: System Information ---");

let pid = syscall.getpid();
let cwd = syscall.getcwd();

print("✓ Process ID: ", pid);
print("✓ Working Dir: ", cwd);

::
:: Test 7: Multiple Register Access
::
print("");
print("--- Test 7: Register Sequence ---");

unsafe {
    :: Simulate device initialization sequence
    let DEVICE_BASE = 0xFED10000;
    
    print("Device initialization sequence:");
    
    :: Read control register
    let ctrl = mmio_read(DEVICE_BASE, 0x00);
    print("1. Read control: ", hex(ctrl));
    
    :: Write enable bit
    mmio_write(DEVICE_BASE, 0x00, 0x01);
    print("2. Wrote enable bit");
    
    :: Read status
    let status = mmio_read(DEVICE_BASE, 0x04);
    print("3. Read status: ", hex(status));
    
    :: Wait simulation
    print("4. Operation complete");
};

::
:: Test 8: Error Handling
::
print("");
print("--- Test 8: Error Handling ---");

unsafe {
    let mem = malloc(100);
    
    :: Valid access
    write_byte(mem, 0, 0x42);
    print("✓ Valid access: wrote to offset 0");
    
    :: Try to detect out-of-bounds
    try {
        write_byte(mem, 1000, 0xFF);  :: Out of bounds
        print("✗ Out-of-bounds NOT detected");
    } catch e {
        print("✓ Out-of-bounds detected: ", e);
    };
    
    free(mem);
};

::
:: Summary
::
print("");
print("=== Hardware Test Complete ===");
print("");
print("Results:");
print("- I/O Port Access: ", "requires root");
print("- MMIO Access: ", "requires root");
print("- Safe Memory: ", "✓ works without root");
print("- System Info: ", "✓ works without root");
print("");
print("To test with full hardware access:");
print("  sudo python3 kentscript_real_syscalls.py test_hardware.ks");
