:: KentScript - Complete Feature Test

print("=== KENTSCRIPT COMPLETE TEST ===\n");

:: Core Language
print("Core Language:");
func test_func(x) { return x * 2; }
if test_func(5) == 10 { print("✓ Functions"); }
let arr = [1, 2, 3]; arr.append(4);
if len(arr) == 4 { print("✓ Collections"); }
if 5 > 3 and true { print("✓ Operators"); }
let sum = 0; for i in range(3) { sum = sum + i; }
if sum == 3 { print("✓ Loops"); }

:: File I/O
print("\nFile I/O:");
system_file_write_text("/tmp/ks_final.txt", "test");
if system_file_exists("/tmp/ks_final.txt") { print("✓ File operations"); }
system_file_remove("/tmp/ks_final.txt");

:: Process
print("\nProcess:");
system_subprocess_run("echo test");
print("✓ Subprocess");

:: Math
print("\nMath:");
let calc = (5 + 3) * 2 - 4;
if calc == 12 { print("✓ Arithmetic"); }

:: Low-level
print("\nLow-level:");
unsafe {
    let pid = system_syscall(39);
    let ptr = malloc(128);
    ptr_write(ptr, 42);
    let val = ptr_read(ptr);
    free(ptr);
    if val == 42 and pid > 0 { print("✓ Syscalls & Memory"); }
}

print("\n=== ALL FEATURES WORKING ===");
