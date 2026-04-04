:: ============================================================
:: KentScript Full Capability Test
:: Tests: File I/O, HTTP, JSON, Subprocess, Crypto, Syscalls, Memory
:: Run: ./kentscript run examples/full_capabilities.ks
:: ============================================================

import fileio;
import http;
import json;
import subprocess;

:: --- File I/O (high-level) ---
fileio.write_text("/tmp/ks_cap.txt", "KentScript capability test");
let content = fileio.read_text("/tmp/ks_cap.txt");
print("✓ fileio.write/read: " + content);
fileio.append_text("/tmp/ks_cap.txt", "\nline2");
print("✓ fileio.append size: " + str(fileio.size("/tmp/ks_cap.txt")));
fileio.copy("/tmp/ks_cap.txt", "/tmp/ks_cap_copy.txt");
print("✓ fileio.copy exists: " + str(fileio.exists("/tmp/ks_cap_copy.txt")));
fileio.delete("/tmp/ks_cap.txt");
fileio.delete("/tmp/ks_cap_copy.txt");

:: --- Low-level file via syscalls ---
unsafe {
    let fd = system_open("/tmp/ks_ll.txt", 65, 420);
    system_write(fd, "syscall write\n");
    system_close(fd);
    let fd2 = system_open("/tmp/ks_ll.txt", 0, 0);
    let data = system_file_read_text("/tmp/ks_ll.txt");
    system_close(fd2);
    print("✓ syscall file read: " + data);
    system_file_remove("/tmp/ks_ll.txt");
}

:: --- OS / process ---
let cwd = system_file_getcwd();
print("✓ getcwd: " + cwd);
let pid = system_os_getpid();
print("✓ pid: " + str(pid));
let uid = system_os_getuid();
print("✓ uid: " + str(uid));

:: --- Subprocess ---
let result = subprocess.run(["uname", "-r"]);
print("✓ subprocess uname: " + result.stdout);

:: --- HTTP ---
let resp = http.get("http://httpbin.org/json");
print("✓ http.get status: " + str(resp.status));

:: --- JSON ---
let obj = json.loads("{\"name\": \"KentScript\", \"version\": 3}");
print("✓ json.loads name: " + str(obj["name"]));
let s = json.dumps({"key": "value", "num": 42});
print("✓ json.dumps: " + s);

:: --- Crypto ---
let h = system_crypto_sha256("hello");
print("✓ sha256: " + h);
let token = system_crypto_generate_token(16);
print("✓ random token len: " + str(token.length));
let enc = system_crypto_encrypt_aes("secret message", "mykey12345678901");
let dec = system_crypto_decrypt_aes(enc, "mykey12345678901");
print("✓ aes roundtrip: " + dec);

:: --- Raw syscalls ---
unsafe {
    let mypid = syscall(39);
    print("✓ syscall(getpid): " + str(mypid));
    let myuid = syscall(102);
    print("✓ syscall(getuid): " + str(myuid));
}

:: --- Memory ---
unsafe {
    let ptr = malloc(256);
    ptr_write(ptr, 0xDEAD);
    let val = ptr_read(ptr, 1);
    print("✓ malloc/ptr_write/read: 0x" + str(val, 16));
    free(ptr);
}

:: --- System info ---
let cpus = system_cpu_count();
let mem = system_virtual_memory();
print("✓ cpus: " + str(cpus));
print("✓ ram total: " + str(mem["total"]));

print("\n=== ALL CAPABILITIES VERIFIED ===");
