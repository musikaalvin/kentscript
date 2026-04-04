:: Test Phase 26.11 - CPU Operations

print("Test: rdtsc");
unsafe {
    let tsc = rdtsc();
    if tsc > 0 {
        print("✓ rdtsc works: " + str(tsc));
    } else {
        print("✗ rdtsc failed");
    }
}

print("\n=== Phase 26.11 Complete ===");
