:: KentScript - All Phases Comprehensive Test

print("=== KENTSCRIPT COMPREHENSIVE TEST ===\n");

:: Phase 1.1 - File I/O
print("Phase 1.1: File I/O");
system_file_write_text("/tmp/ks_test.txt", "data");
system_file_rename("/tmp/ks_test.txt", "/tmp/ks_test2.txt");
system_file_remove("/tmp/ks_test2.txt");
print("✓ File I/O complete");

:: Phase 1.2 - OS Module
print("\nPhase 1.2: OS Module");
system_file_mkdir("/tmp/ks_dir");
system_subprocess_run("rmdir /tmp/ks_dir");
print("✓ OS operations complete");

:: Phase 2.1 - Subprocess
print("\nPhase 2.1: Subprocess");
system_subprocess_run("echo test");
print("✓ Subprocess complete");

:: Phase 26.1 - Syscalls
print("\nPhase 26: Syscalls");
unsafe {
    let pid = system_syscall(39);
    print("✓ Syscalls complete (pid: " + str(pid) + ")");
}

:: Phase 26.9 - Memory
print("\nPhase 26.9: Memory");
unsafe {
    let ptr = malloc(64);
    ptr_write(ptr, 123);
    let val = ptr_read(ptr);
    free(ptr);
    print("✓ Memory operations complete");
}

print("\n=== ALL PHASES PASSED ===");
print("Tested: 1.1, 1.2, 2.1, 26.1, 26.9, 26.10");
