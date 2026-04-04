:: Test Phase 26.9 - Memory Operations

print("Test: malloc/free");
unsafe {
    let ptr = malloc(1024);
    if ptr != 0 {
        print("✓ malloc works");
        free(ptr);
        print("✓ free works");
    } else {
        print("✗ malloc failed");
    }
}

print("\nTest: ptr_read/ptr_write");
unsafe {
    let ptr = malloc(8);
    ptr_write(ptr, 42);
    let val = ptr_read(ptr);
    if val == 42 {
        print("✓ ptr_read/write work");
    } else {
        print("✗ ptr operations failed");
    }
    free(ptr);
}

print("\n=== Phase 26.9 Complete ===");
