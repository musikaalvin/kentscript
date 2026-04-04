:: Simple pathlib test

import pathlib;

print("Test: Path creation");
let p = Path("/tmp/test.txt");
print("✓ Path created");

print("\nTest: Path exists");
system_file_write_text("/tmp/ks_simple.txt", "test");
let p2 = Path("/tmp/ks_simple.txt");
if p2.exists() {
    print("✓ Path.exists() works");
}
system_file_remove("/tmp/ks_simple.txt");

print("\n=== Simple Test Complete ===");
