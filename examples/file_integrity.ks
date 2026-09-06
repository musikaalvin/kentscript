:: File Integrity Checker - Monitor files for changes
:: Usage: python3 main.py run examples/file_integrity.ks --scan <path> [--baseline <file>] [--check]

import argparse;
import crypto;
import json;
import os;

let parser = system_argparse_new("KentScript File Integrity Checker v1.0");
system_argparse_add_argument(parser, "--scan");
system_argparse_add_argument(parser, "--baseline");
system_argparse_add_argument(parser, "--check");
system_argparse_add_argument(parser, "--watch");

let args = system_argparse_parse_args(parser, []);

if args.scan == none {
    print("Usage: file_integrity.ks --scan <path> [--baseline baseline.json] [--check] [--watch]");
    print("");
    print("Commands:");
    print("  --scan <path>   : Scan directory and create baseline");
    print("  --baseline <f>   : Use baseline file (default: baseline.json)");
    print("  --check          : Check files against baseline");
    print("  --watch          : Continuous monitoring mode");
    system_os_exit(1);
}

let target_path = str(args.scan);
let baseline_file = "baseline.json";
if args.baseline != none {
    baseline_file = str(args.baseline);
}

let check_mode = args.check != none;
let watch_mode = args.watch != none;

print(f"[*] KentScript File Integrity Checker v1.0");
print(f"[*] Target: {target_path}");
print(f"[*] Baseline: {baseline_file}");
print("");

:: Calculate file hash
func hash_file(filepath) {
    try {
        let content = system_file_read_bytes(filepath);
        if content == none {
            return none;
        }
        let hex_str = system_bytes_hex(content);
        return system_crypto_sha256(hex_str);
    } except e {
        return none;
    }
}

:: Get file metadata
func get_file_meta(filepath) {
    let meta = {};
    
    try {
        let stat = system_file_stat(filepath);
        if stat != none {
            meta["size"] = stat.size;
            meta["mtime"] = stat.mtime;
            meta["mode"] = stat.mode;
        }
        
        let hash = hash_file(filepath);
        meta["hash"] = hash;
        
    } except e {
        return none;
    }
    
    return meta;
}

:: Scan directory recursively
func scan_directory(path) {
    let results = {};
    
    print(f"[*] Scanning {path}...");
    
    let entries = system_file_walk(path, true);
    
    if entries == none {
        print("[!] Could not scan directory");
        system_os_exit(1);
    }
    
    let count = 0;
    let errors = 0;
    
    for entry in entries {
        if entry.is_file {
            let rel_path = entry.path;
            if str(path).len() < str(entry.path).len() {
                rel_path = str(entry.path).substr(str(path).len());
                if str(rel_path).starts_with("/") {
                    rel_path = str(rel_path).substr(1);
                }
            }
            
            let meta = get_file_meta(entry.path);
            if meta != none {
                results[rel_path] = meta;
                count = count + 1;
                
                if count % 50 == 0 {
                    print(f"[*] Scanned {count} files...");
                }
            } else {
                errors = errors + 1;
            }
        }
    }
    
    print(f"[*] Scan complete: {count} files, {errors} errors");
    
    return results;
}

:: Save baseline
func save_baseline(data, filename) {
    let json_str = json.dumps(data, pretty=true);
    system_file_write_text(filename, json_str);
    print(f"[*] Baseline saved to {filename}");
}

:: Load baseline
func load_baseline(filename) {
    try {
        let content = system_file_read_text(filename);
        if content == none {
            return none;
        }
        return json.loads(content);
    } except e {
        print(f"[!] Error loading baseline: {e}");
        return none;
    }
}

:: Check files against baseline
func check_integrity(current, baseline) {
    let changes = {
        "added": [],
        "removed": [],
        "modified": [],
        "unchanged": []
    };
    
    let current_paths = current.keys();
    let baseline_paths = baseline.keys();
    
    :: Check for added and modified files
    for path in current_paths {
        if not baseline.contains_key(path) {
            changes["added"].append(path);
            print(f"[+] ADDED: {path}");
        } else {
            let current_hash = current[path]["hash"];
            let baseline_hash = baseline[path]["hash"];
            
            if current_hash != baseline_hash {
                changes["modified"].append(path);
                print(f"[!] MODIFIED: {path}");
                print(f"    Old: {baseline_hash}");
                print(f"    New: {current_hash}");
            } else {
                changes["unchanged"].append(path);
            }
        }
    }
    
    :: Check for removed files
    for path in baseline_paths {
        if not current.contains_key(path) {
            changes["removed"].append(path);
            print(f"[-] REMOVED: {path}");
        }
    }
    
    return changes;
}

:: Main logic
if check_mode {
    :: Load baseline and check
    print("[*] Loading baseline...");
    let baseline = load_baseline(baseline_file);
    
    if baseline == none {
        print(f"[!] Could not load baseline from {baseline_file}");
        print("[*] Run without --check first to create a baseline");
        system_os_exit(1);
    }
    
    print("[*] Scanning current state...");
    let current = scan_directory(target_path);
    
    print("");
    print("[*] Checking integrity...");
    print("");
    
    let changes = check_integrity(current, baseline);
    
    print("");
    print("=== Integrity Check Summary ===");
    print(f"[+] Added:   {len(changes["added"])}");
    print(f"[-] Removed: {len(changes["removed"])}");
    print(f"[!] Modified: {len(changes["modified"])}");
    print(f"[=] Unchanged: {len(changes["unchanged"])}");
    
    if len(changes["modified"]) > 0 or len(changes["added"]) > 0 or len(changes["removed"]) > 0 {
        print("");
        print("[!] WARNING: File integrity violations detected!");
        
        :: Save change report
        let report = {
            "timestamp": system_time_format(system_time_now(), "%Y-%m-%d %H:%M:%S"),
            "baseline": baseline_file,
            "path": target_path,
            "changes": changes
        };
        
        let report_file = "integrity_report_" + system_time_format(system_time_now(), "%Y%m%d_%H%M%S") + ".json";
        save_baseline(report, report_file);
        print(f"[*] Report saved to {report_file}");
    }
    
} elif watch_mode {
    :: Watch mode - continuous monitoring
    print("[*] Loading baseline...");
    let baseline = load_baseline(baseline_file);
    
    if baseline == none {
        print(f"[!] Could not load baseline");
        system_os_exit(1);
    }
    
    print("[*] Entering watch mode (Ctrl+C to stop)");
    
    let last_check = system_time_now();
    
    while true {
        system_time_sleep(60);
        
        print("");
        print("[*] Checking for changes...");
        
        let current = scan_directory(target_path);
        let changes = check_integrity(current, baseline);
        
        if len(changes["modified"]) > 0 or len(changes["added"]) > 0 or len(changes["removed"]) > 0 {
            print("");
            print("[!] CHANGES DETECTED!");
            
            :: Alert
            print("");
            print("=== Change Alert ===");
            print(f"Time: {system_time_format(system_time_now(), \"%Y-%m-%d %H:%M:%S\")}");
            print(f"[+] Added:   {len(changes["added"])}");
            print(f"[-] Removed: {len(changes["removed"])}");
            print(f"[!] Modified: {len(changes["modified"])}");
        }
        
        last_check = system_time_now();
    }
    
} else {
    :: Create baseline
    print("[*] Scanning and creating baseline...");
    let data = scan_directory(target_path);
    
    save_baseline(data, baseline_file);
    
    print("");
    print("[*] Baseline created successfully");
    print("[*] To check integrity later:");
    print(f"    --scan {target_path} --baseline {baseline_file} --check");
}
