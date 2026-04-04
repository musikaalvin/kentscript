:: Test Phase 26 - Syscalls

print("Test: syscall(39) - getpid");
unsafe {
    let pid = system_syscall(39);
    if pid > 0 {
        print("✓ getpid works: " + str(pid));
    } else {
        print("✗ getpid failed");
    }
}

print("\nTest: syscall(82) - rename");
unsafe {
    system_file_write_text("/tmp/syscall_old.txt", "test");
    let ret = system_syscall(82, "/tmp/syscall_old.txt", "/tmp/syscall_new.txt");
    if system_file_exists("/tmp/syscall_new.txt") {
        print("✓ rename syscall works");
        system_file_remove("/tmp/syscall_new.txt");
    } else {
        print("✗ rename syscall failed: " + str(ret));
    }
}

print("\n=== Phase 26 Syscalls Complete ===");
