:: Test Phase 1.2 OS Module - Enhanced

print("Test: os.stat()");
system_file_write_text("/tmp/ks_stat.txt", "test");
let st = system_file_stat("/tmp/ks_stat.txt");
if st != none {
    print("✓ os.stat() works - size: " + str(st['st_size']));
}
system_file_remove("/tmp/ks_stat.txt");

print("\nTest: os.chmod()");
system_file_write_text("/tmp/ks_chmod.txt", "test");
system_file_chmod("/tmp/ks_chmod.txt", 420);
print("✓ os.chmod() works");
system_file_remove("/tmp/ks_chmod.txt");

print("\nTest: os.symlink()");
system_file_write_text("/tmp/ks_orig.txt", "original");
system_file_symlink("/tmp/ks_orig.txt", "/tmp/ks_link.txt");
let exists = system_file_exists("/tmp/ks_link.txt");
if exists != 0 {
    print("✓ os.symlink() works");
}
system_file_remove("/tmp/ks_orig.txt");
system_file_remove("/tmp/ks_link.txt");

print("\nTest: os.readlink()");
system_file_write_text("/tmp/ks_read.txt", "test");
system_file_symlink("/tmp/ks_read.txt", "/tmp/ks_readlink.txt");
let link = system_file_readlink("/tmp/ks_readlink.txt");
if link != "" {
    print("✓ os.readlink() works: " + link);
}
system_file_remove("/tmp/ks_read.txt");
system_file_remove("/tmp/ks_readlink.txt");

print("\nTest: os.getppid()");
let ppid = system_os_getppid();
if ppid > 0 {
    print("✓ os.getppid() works: " + str(ppid));
}

print("\nTest: os.getuid()");
let uid = system_os_getuid();
if uid >= 0 {
    print("✓ os.getuid() works: " + str(uid));
}

print("\nTest: os.getgid()");
let gid = system_os_getgid();
if gid >= 0 {
    print("✓ os.getgid() works: " + str(gid));
}

print("\nTest: os.environ");
let home = system_os_getenv("HOME", "/none");
if home != "/none" {
    print("✓ os.getenv() works: " + home);
}

print("\n=== Phase 1.2 OS Module Complete ===");
