:: ============================================================
:: KentScript Security Tools Demo
:: Real security tool patterns: port scanner, hash checker,
:: file integrity monitor, process inspector
:: Run: ./kentscript run examples/security_tools.ks
:: ============================================================

import fileio;
import subprocess;
import json;

:: --- 1. Port Scanner ---
print("=== PORT SCANNER ===");

func scan_port(host: str, port: int) -> bool {
    unsafe {
        let sock = system_socket_create(2, 1, 0);
        system_socket_settimeout(sock, 0.5);
        let err = system_socket_connect(sock, host, port);
        system_socket_close(sock);
        return err == none;
    }
}

let target = "127.0.0.1";
let ports = [22, 80, 443, 3306, 5432, 6379, 8080];
print("Scanning " + target + "...");
for port in ports {
    if scan_port(target, port) {
        print("  [OPEN] " + target + ":" + str(port));
    }
}
print("Scan done.");

:: --- 2. File Integrity Checker ---
print("\n=== FILE INTEGRITY CHECKER ===");

func hash_file(path: str) -> str {
    let content = fileio.read_text(path);
    return system_crypto_sha256(content);
}

:: Create test files
fileio.write_text("/tmp/ks_file1.txt", "original content");
fileio.write_text("/tmp/ks_file2.txt", "original content");
fileio.write_text("/tmp/ks_file3.txt", "tampered content!");

let files = ["/tmp/ks_file1.txt", "/tmp/ks_file2.txt", "/tmp/ks_file3.txt"];
let baseline = hash_file("/tmp/ks_file1.txt");
print("Baseline hash: " + baseline);

for f in files {
    let h = hash_file(f);
    if h == baseline {
        print("  [OK]      " + f);
    } else {
        print("  [TAMPERED] " + f);
    }
}

fileio.delete("/tmp/ks_file1.txt");
fileio.delete("/tmp/ks_file2.txt");
fileio.delete("/tmp/ks_file3.txt");

:: --- 3. Process Inspector ---
print("\n=== PROCESS INSPECTOR ===");

let ps = subprocess.run(["ps", "aux", "--no-headers"]);
let lines = ps.stdout.split("\n");
print("Total processes: " + str(lines.length));

:: Find processes by name
let result = subprocess.run(["pgrep", "-l", "python"]);
if result.returncode == 0 {
    print("Python processes:\n" + result.stdout);
}

:: --- 4. Crypto Operations ---
print("\n=== CRYPTO OPERATIONS ===");

let password = "mysecretpassword";
let salt = "randomsalt123";

let sha256_hash = system_crypto_sha256(password);
print("SHA256: " + sha256_hash);

let sha512_hash = system_crypto_sha512(password);
print("SHA512: " + sha512_hash);

let hmac = system_crypto_hmac(password, salt);
print("HMAC-SHA256: " + hmac);

let pbkdf2 = system_crypto_pbkdf2(password, salt, 10000);
print("PBKDF2: " + pbkdf2);

let token = system_crypto_generate_token(32);
print("Secure token: " + token);

:: --- 5. Low-level syscall inspection ---
print("\n=== SYSCALL INSPECTION ===");

unsafe {
    let pid  = syscall(39);
    let ppid = syscall(110);
    let uid  = syscall(102);
    let gid  = syscall(104);
    print("PID=" + str(pid) + " PPID=" + str(ppid) + " UID=" + str(uid) + " GID=" + str(gid));
}

print("\n=== SECURITY TOOLS VERIFIED ===");
