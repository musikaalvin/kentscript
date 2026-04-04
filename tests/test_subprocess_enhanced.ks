:: Test Phase 2.1 - Subprocess Enhanced

print("Test: subprocess.run() with options");
let result = system_subprocess_run("echo test", shell=true, capture_output=true);
if result.returncode == 0 {
    print("✓ subprocess.run() works - stdout: " + result.stdout);
}

print("\nTest: subprocess.check_call()");
let check = system_subprocess_check_call("echo check_call", shell=true);
if check.success {
    print("✓ subprocess.check_call() works");
}

print("\nTest: subprocess.check_output()");
let output = system_subprocess_check_output("echo check_output", shell=true);
if output.success {
    print("✓ subprocess.check_output() works - " + output.stdout);
}

print("\nTest: subprocess.getstatusoutput()");
let status = system_subprocess_getstatusoutput("echo status");
if status.status == 0 {
    print("✓ subprocess.getstatusoutput() works - status: " + str(status.status));
}

print("\n=== Phase 2.1 Subprocess Complete ===");
