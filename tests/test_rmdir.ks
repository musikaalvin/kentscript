:: Test rmdir

print("Test: rmdir");
system_file_mkdir("/tmp/ks_test_rmdir");
system_file_rmdir("/tmp/ks_test_rmdir");
if not system_file_exists("/tmp/ks_test_rmdir") {
    print("✓ system_file_rmdir works");
}

print("\n=== rmdir Complete ===");
