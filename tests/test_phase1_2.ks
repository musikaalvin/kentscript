:: Test Phase 1.2 - OS Module

:: Test os operations
print("Test: os.mkdir/rmdir");
system_file_mkdir("/tmp/test_dir");
if system_file_isdir("/tmp/test_dir") {
    print("✓ mkdir works");
} else {
    print("✗ mkdir failed");
}
system_file_rmdir("/tmp/test_dir");

print("\nTest: os.getcwd/chdir");
let cwd = system_file_getcwd();
if cwd != none {
    print("✓ getcwd works");
} else {
    print("✗ getcwd failed");
}

print("\n=== Phase 1.2 Complete ===");
