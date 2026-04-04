::
:: KentScript Real Syscall Test
:: Tests actual Linux kernel syscalls (getpid, open, write, close, etc)
::

import syscall;

::
:: Test 1: Get current process ID (getpid syscall)
::
print("=== Test 1: Process ID ===");
let pid = syscall.getpid();
print("Current PID: ", pid);

::
:: Test 2: Get thread ID (gettid syscall)
::
print("");
print("=== Test 2: Thread ID ===");
let tid = syscall.gettid();
print("Current TID: ", tid);

::
:: Test 3: Get current working directory (getcwd syscall)
::
print("");
print("=== Test 3: Current Directory ===");
let cwd = syscall.getcwd();
print("CWD: ", cwd);

::
:: Test 4: File operations (open, write, close syscalls)
::
print("");
print("=== Test 4: File Operations ===");

:: Open file for writing (real open syscall)
let testfile = "/tmp/kentscript_test.txt";
let fd = syscall.open(testfile, 0o666);
print("Opened file: ", testfile);
print("File descriptor: ", fd);

:: Write to file (real write syscall)
let message = "KentScript talks to Linux kernel!";
let bytes_written = syscall.write(fd, message);
print("Wrote ", bytes_written, " bytes");

:: Close file (real close syscall)
syscall.close(fd);
print("File closed");

::
:: Test 5: Get file information (stat syscall)
::
print("");
print("=== Test 5: File Stats ===");
let stats = syscall.stat(testfile);
print("File size: ", stats["size"]);
print("File mode: ", stats["mode"]);

::
:: Test 6: Memory allocation (real malloc/free)
::
print("");
print("=== Test 6: Real Memory ===");

unsafe {
    :: Allocate 256 bytes of REAL memory
    let mem = malloc(256);
    print("Allocated memory at: ", mem);
    
    :: Write data to memory
    write_string(mem, 0, "Hello Kernel!");
    
    :: Read it back
    let str = read_string(mem, 0);
    print("String from memory: ", str);
    
    :: Free memory
    free(mem);
    print("Memory freed");
};

::
:: Test 7: Basic arithmetic with syscall results
::
print("");
print("=== Test 7: Math with Syscalls ===");
let pid1 = syscall.getpid();
let pid2 = syscall.getpid();
print("PID + PID = ", pid1 + pid2);

::
:: Test 8: Directory operations
::
print("");
print("=== Test 8: Directory Info ===");
let home_dir = syscall.getcwd();
print("Home directory: ", home_dir);

::
:: Test 9: Chain multiple syscalls
::
print("");
print("=== Test 9: Syscall Chain ===");
print("Process ID: ", syscall.getpid());
print("Current Dir: ", syscall.getcwd());
print("Thread ID: ", syscall.gettid());

::
:: Test 10: Complete example - write to file and read back
::
print("");
print("=== Test 10: Full File Example ===");

let filename = "/tmp/ks_syscall_demo.txt";

:: Create and write
let out_fd = syscall.open(filename, 0o666);
print("Created: ", filename);

let content = "Line 1: KentScript\nLine 2: Real Syscalls\nLine 3: Direct Kernel Access";
syscall.write(out_fd, content);
print("Written ", len(content), " characters");
syscall.close(out_fd);

:: Read file info
let fstats = syscall.stat(filename);
print("File size: ", fstats["size"], " bytes");

print("");
print("=== All Tests Complete ===");
print("KentScript successfully called Linux kernel syscalls!");
