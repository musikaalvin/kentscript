:: Test Phase 1.1 - File I/O operations
import fileio;

:: Test 1: file_rename()
print("Test 1: fileio.rename()");
fileio.write("/tmp/test_old.txt", "test content");
fileio.rename("/tmp/test_old.txt", "/tmp/test_new.txt");
if fileio.exists("/tmp/test_new.txt") {
    print("✓ fileio.rename() works");
} else {
    print("✗ fileio.rename() failed");
}
fileio.remove("/tmp/test_new.txt");

:: Test 2: file_listdir()
print("\nTest 2: fileio.listdir()");
let files = fileio.listdir("/tmp");
if files != none {
    print("✓ fileio.listdir() works - found " + str(len(files)) + " files");
} else {
    print("✗ fileio.listdir() failed");
}

:: Test 3: file_exists()
print("\nTest 3: fileio.exists()");
fileio.write("/tmp/test_exists.txt", "test");
if fileio.exists("/tmp/test_exists.txt") {
    print("✓ fileio.exists() works");
} else {
    print("✗ fileio.exists() failed");
}
fileio.remove("/tmp/test_exists.txt");

:: Test 4: file_isfile()
print("\nTest 4: fileio.isfile()");
fileio.write("/tmp/test_isfile.txt", "test");
if fileio.isfile("/tmp/test_isfile.txt") {
    print("✓ fileio.isfile() works");
} else {
    print("✗ fileio.isfile() failed");
}
fileio.remove("/tmp/test_isfile.txt");

:: Test 5: file_isdir()
print("\nTest 5: fileio.isdir()");
if fileio.isdir("/tmp") {
    print("✓ fileio.isdir() works");
} else {
    print("✗ fileio.isdir() failed");
}

print("\n=== Phase 1.1 Tests Complete ===");
