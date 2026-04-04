:: File Integrity Checker - Monitor file changes
:: Usage: python3 main.py run file_monitor.ks

func hash_file(path) {
    if system_file_exists(path) {
        let content = system_file_read_text(path);
        return system_crypto_sha256(content);
    }
    return none;
}

func monitor_files(paths) {
    print("[*] File Integrity Monitor");
    print("[*] Creating baseline...\n");
    
    :: Create baseline
    let baseline = {};
    for path in paths {
        let hash = hash_file(path);
        if hash != none {
            baseline[path] = hash;
            print(f"  {path}: {hash}");
        }
    }
    
    print("\n[*] Baseline created. Checking for changes...\n");
    
    :: Check for changes
    let changes = 0;
    for path in paths {
        let current_hash = hash_file(path);
        if current_hash != none {
            if baseline[path] != current_hash {
                print(f"[!] MODIFIED: {path}");
                print(f"    Old: {baseline[path]}");
                print(f"    New: {current_hash}");
                changes = changes + 1;
            } else {
                print(f"[✓] OK: {path}");
            }
        } else {
            print(f"[!] DELETED: {path}");
            changes = changes + 1;
        }
    }
    
    print(f"\n[*] Total changes: {changes}");
}

:: Create test files
system_file_write_text("/tmp/test1.txt", "original content");
system_file_write_text("/tmp/test2.txt", "another file");

:: Monitor them
let files = ["/tmp/test1.txt", "/tmp/test2.txt"];
monitor_files(files);

:: Modify one
print("\n[*] Modifying test1.txt...\n");
system_file_write_text("/tmp/test1.txt", "MODIFIED CONTENT");

:: Check again
monitor_files(files);

:: Cleanup
system_file_remove("/tmp/test1.txt");
system_file_remove("/tmp/test2.txt");
