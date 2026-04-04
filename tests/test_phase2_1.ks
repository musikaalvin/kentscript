:: Test Phase 2.1 - Subprocess

print("Test: subprocess.run()");
let result = system_subprocess_run("echo test");
if result != none {
    print("✓ subprocess.run() works");
} else {
    print("✗ subprocess.run() failed");
}

print("\n=== Phase 2.1 Complete ===");
