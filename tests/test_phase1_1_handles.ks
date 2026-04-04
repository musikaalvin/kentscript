:: Test Phase 1.1 - File I/O (file handles)

:: Test file_open/read/write/close
print("Test: file_open/read/write/close");
let handle = system_file_open("/tmp/test_handle.txt", "w");
system_file_write(handle, "test data");
system_file_close(handle);

handle = system_file_open("/tmp/test_handle.txt", "r");
let data = system_file_read(handle, -1);
system_file_close(handle);

if data == "test data" {
    print("✓ file_open/read/write/close work");
} else {
    print("✗ failed");
}
system_file_remove("/tmp/test_handle.txt");

print("\n=== Phase 1.1 Complete ===");
