:: Test Phase 1.1 - File I/O operations (Direct system calls)

:: Test 1: system_file_rename()
print("Test 1: system_file_rename()");
system_file_write_text("/tmp/test_old.txt", "test content");
system_file_rename("/tmp/test_old.txt", "/tmp/test_new.txt");
if system_file_exists("/tmp/test_new.txt") {
    print("✓ system_file_rename() works");
} else {
    print("✗ system_file_rename() failed");
}
system_file_remove("/tmp/test_new.txt");

:: Test 2: system_file_listdir()
print("\nTest 2: system_file_listdir()");
let files = system_file_listdir("/tmp");
if files != none {
    print("✓ system_file_listdir() works");
} else {
    print("✗ system_file_listdir() failed");
}

:: Test 3: system_file_exists()
print("\nTest 3: system_file_exists()");
system_file_write_text("/tmp/test_exists.txt", "test");
if system_file_exists("/tmp/test_exists.txt") {
    print("✓ system_file_exists() works");
} else {
    print("✗ system_file_exists() failed");
}
system_file_remove("/tmp/test_exists.txt");

:: Test 4: system_file_isfile()
print("\nTest 4: system_file_isfile()");
system_file_write_text("/tmp/test_isfile.txt", "test");
if system_file_isfile("/tmp/test_isfile.txt") {
    print("✓ system_file_isfile() works");
} else {
    print("✗ system_file_isfile() failed");
}
system_file_remove("/tmp/test_isfile.txt");

:: Test 5: system_file_isdir()
print("\nTest 5: system_file_isdir()");
if system_file_isdir("/tmp") {
    print("✓ system_file_isdir() works");
} else {
    print("✗ system_file_isdir() failed");
}

print("\n=== Phase 1.1 File I/O Tests Complete ===");
