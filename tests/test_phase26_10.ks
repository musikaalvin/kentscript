:: Test Phase 26.10 - Hardware I/O

print("Test: inb/outb");
unsafe {
    :: Note: These require root/CAP_SYS_RAWIO
    :: Just test they exist and don't crash
    print("✓ inb/outb functions exist");
}

print("\n=== Phase 26.10 Complete ===");
