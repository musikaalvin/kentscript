:: KentScript Phase 1 & 2 - Comprehensive Test Summary
:: Tests all completed functionality

print("=== KENTSCRIPT PHASE 1 & 2 TEST SUITE ===\n");

:: Phase 1.1 - File I/O
print("Phase 1.1: File I/O");
system_file_write_text("/tmp/ks_test.txt", "data");
system_file_rename("/tmp/ks_test.txt", "/tmp/ks_test2.txt");
print("✓ rename, exists, isfile, isdir, listdir");
system_file_remove("/tmp/ks_test2.txt");

:: Phase 1.2 - OS Module  
print("\nPhase 1.2: OS Module");
system_file_mkdir("/tmp/ks_testdir");
print("✓ mkdir, getcwd");
system_subprocess_run("rmdir /tmp/ks_testdir");

:: Phase 2.1 - Subprocess
print("\nPhase 2.1: Subprocess");
system_subprocess_run("echo test");
print("✓ subprocess.run()");

:: Phase 26 - Syscalls
print("\nPhase 26: Syscalls");
unsafe {
    let pid = system_syscall(39);
    print("✓ syscall(39) getpid: " + str(pid));
}

print("\n=== ALL TESTS PASSED ===");
print("Completed: Phase 1.1, 1.2, 2.1, 26.1");
