:: Test os.walk()

print("Test: os.walk()");
system_file_mkdir("/tmp/ks_walk_test");
system_file_mkdir("/tmp/ks_walk_test/subdir");
system_file_write_text("/tmp/ks_walk_test/file1.txt", "test");
system_file_write_text("/tmp/ks_walk_test/subdir/file2.txt", "test");

let entries = [];
for item in system_file_walk("/tmp/ks_walk_test") {
    entries.append(item);
}

if len(entries) > 0 {
    print("✓ os.walk() works - found " + str(len(entries)) + " entries");
}

system_subprocess_run("rm -rf /tmp/ks_walk_test");

print("\n=== os.walk() Complete ===");
