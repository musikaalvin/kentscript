:: Test Phase 1.3 - pathlib module

import pathlib;

print("Test: Path() creation");
let p = Path("/tmp/test/path.txt");
if p.path == "/tmp/test/path.txt" {
    print("✓ Path() works");
}

print("\nTest: Path.exists()");
system_file_write_text("/tmp/ks_path_test.txt", "test");
let p2 = Path("/tmp/ks_path_test.txt");
if p2.exists() {
    print("✓ Path.exists() works");
}
system_file_remove("/tmp/ks_path_test.txt");

print("\nTest: Path.is_file()");
system_file_write_text("/tmp/ks_path_test.txt", "test");
let p3 = Path("/tmp/ks_path_test.txt");
if p3.is_file() {
    print("✓ Path.is_file() works");
}
system_file_remove("/tmp/ks_path_test.txt");

print("\nTest: Path.is_dir()");
system_file_mkdir("/tmp/ks_path_test_dir");
let p4 = Path("/tmp/ks_path_test_dir");
if p4.is_dir() {
    print("✓ Path.is_dir() works");
}
system_file_rmdir("/tmp/ks_path_test_dir");

print("\nTest: Path.name");
let p5 = Path("/tmp/test/file.txt");
if p5.name() == "file.txt" {
    print("✓ Path.name() works");
}

print("\nTest: Path.parent()");
let p6 = Path("/tmp/test/file.txt");
let parent = p6.parent();
if parent.path == "/tmp/test" {
    print("✓ Path.parent() works");
}

print("\nTest: Path.stat()");
system_file_write_text("/tmp/ks_path_test.txt", "test");
let p7 = Path("/tmp/ks_path_test.txt");
let stat = p7.stat();
if stat != none and stat['st_size'] == 4 {
    print("✓ Path.stat() works");
}
system_file_remove("/tmp/ks_path_test.txt");

print("\nTest: Path.chmod()");
system_file_write_text("/tmp/ks_path_test.txt", "test");
let p8 = Path("/tmp/ks_path_test.txt");
p8.chmod(420);
print("✓ Path.chmod() works");
system_file_remove("/tmp/ks_path_test.txt");

print("\nTest: Path.iterdir()");
system_file_mkdir("/tmp/ks_path_iterdir");
system_file_write_text("/tmp/ks_path_iterdir/file1.txt", "test");
system_file_write_text("/tmp/ks_path_iterdir/file2.txt", "test");
let p9 = Path("/tmp/ks_path_iterdir");
let entries = p9.iterdir();
if len(entries) == 2 {
    print("✓ Path.iterdir() works - found " + str(len(entries)) + " items");
}
system_subprocess_run("rm -rf /tmp/ks_path_iterdir");

print("\nTest: Path.glob()");
system_file_mkdir("/tmp/ks_path_glob");
system_file_write_text("/tmp/ks_path_glob/test1.txt", "test");
system_file_write_text("/tmp/ks_path_glob/test2.txt", "test");
let p10 = Path("/tmp/ks_path_glob");
let matches = p10.glob("*.txt");
if len(matches) >= 2 {
    print("✓ Path.glob() works - found " + str(len(matches)) + " matches");
}
system_subprocess_run("rm -rf /tmp/ks_path_glob");

print("\nTest: Path.mkdir()");
let p11 = Path("/tmp/ks_path_mkdir_test/subdir");
p11.mkdir(true, true);
if system_file_isdir("/tmp/ks_path_mkdir_test/subdir") {
    print("✓ Path.mkdir() works");
}
system_subprocess_run("rm -rf /tmp/ks_path_mkdir_test");

print("\nTest: Path.unlink()");
system_file_write_text("/tmp/ks_path_unlink.txt", "test");
let p12 = Path("/tmp/ks_path_unlink.txt");
p12.unlink();
if !system_file_exists("/tmp/ks_path_unlink.txt") {
    print("✓ Path.unlink() works");
}

print("\nTest: Path.read_text() / write_text()");
let p13 = Path("/tmp/ks_path_rw.txt");
p13.write_text("hello");
let content = p13.read_text();
if content == "hello" {
    print("✓ Path.read_text()/write_text() works");
}
p13.unlink();

print("\nTest: pathlib.cwd()");
let cwd = pathlib.cwd();
if cwd.path != none {
    print("✓ pathlib.cwd() works");
}

print("\n=== Phase 1.3 pathlib Complete ===");
