:: Log Analyzer - Parse and analyze system logs
:: Usage: python3 main.py run log_analyzer.ks

func analyze_log(logfile) {
    print(f"[*] Analyzing: {logfile}\n");
    
    if !system_file_exists(logfile) {
        print("[-] Log file not found");
        return;
    }
    
    let content = system_file_read_text(logfile);
    let lines = content.split("\n");
    
    let stats = {
        "total": 0,
        "errors": 0,
        "warnings": 0,
        "failed_logins": 0,
        "ips": {}
    };
    
    for line in lines {
        if line == "" { continue; }
        stats["total"] = stats["total"] + 1;
        
        :: Count errors
        if line.contains("ERROR") or line.contains("error") {
            stats["errors"] = stats["errors"] + 1;
        }
        
        :: Count warnings
        if line.contains("WARNING") or line.contains("warning") {
            stats["warnings"] = stats["warnings"] + 1;
        }
        
        :: Failed login attempts
        if line.contains("Failed password") or line.contains("authentication failure") {
            stats["failed_logins"] = stats["failed_logins"] + 1;
        }
    }
    
    :: Print results
    print("=== Log Analysis Results ===");
    print(f"Total lines: {stats['total']}");
    print(f"Errors: {stats['errors']}");
    print(f"Warnings: {stats['warnings']}");
    print(f"Failed logins: {stats['failed_logins']}");
    
    if stats["errors"] > 0 {
        print("\n[!] High error count detected!");
    }
    if stats["failed_logins"] > 5 {
        print("[!] Possible brute force attack!");
    }
}

:: Create sample log
let logfile = "/tmp/sample.log";
let log_content = "2026-03-06 10:00:01 INFO: System started
2026-03-06 10:00:15 WARNING: High memory usage
2026-03-06 10:01:23 ERROR: Connection timeout
2026-03-06 10:02:45 INFO: User login successful
2026-03-06 10:03:12 ERROR: Failed password for admin
2026-03-06 10:03:15 ERROR: Failed password for admin
2026-03-06 10:03:18 ERROR: Failed password for admin
2026-03-06 10:04:00 INFO: Service restarted
2026-03-06 10:05:30 WARNING: Disk space low
2026-03-06 10:06:45 ERROR: Database connection failed";

system_file_write_text(logfile, log_content);

:: Analyze
analyze_log(logfile);

:: Cleanup
system_file_remove(logfile);
