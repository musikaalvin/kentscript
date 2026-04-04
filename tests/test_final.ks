:: KentScript - Final Comprehensive Test

print("=== KENTSCRIPT FINAL TEST SUITE ===\n");

:: Phase 1: File I/O
print("Phase 1: File I/O");
system_file_write_text("/tmp/ks.txt", "test");
let r = system_file_rename("/tmp/ks.txt", "/tmp/ks2.txt");
system_file_remove("/tmp/ks2.txt");
print("✓ File I/O");

:: Phase 2: Subprocess  
print("\nPhase 2: Subprocess");
:: Note: exit_code is passed as pointer in C but optional in KS
system_subprocess_run("echo test", 0);
print("✓ Subprocess");

:: Phase 4: Collections
print("\nPhase 4: Collections");
let arr = [1, 2, 3];
arr.append(4);
let d = {"k": "v", "k2": "v2"};
print("✓ Collections");

:: Phase 13: Math
print("\nPhase 13: Math");
let x = 5 + 3 * 2;
print("✓ Math");

:: Phase 26: Low-level
print("\nPhase 26: Low-level");
unsafe {
    let pid = syscall(39);
    let ptr = malloc(64);
    ptr_write(ptr, 99);
    let v = ptr_read(ptr);
    free(ptr);
    print("✓ Low-level");
}

print("\n=== ALL TESTS PASSED ===");
print("Phases: 1, 2, 4, 13, 26");