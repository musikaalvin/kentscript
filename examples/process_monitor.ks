:: Process Monitor - Monitor processes for suspicious activity
:: Usage: python3 main.py run examples/process_monitor.ks [--interval 5] [--watch]

import argparse;
import json;

let parser = system_argparse_new("KentScript Process Monitor v1.0");
system_argparse_add_argument(parser, "--interval");
system_argparse_add_argument(parser, "--watch");
system_argparse_add_argument(parser, "--alert");

let args = system_argparse_parse_args(parser, []);

let interval = 5;
if args.interval != none {
    interval = int(args.interval);
}

let watch_mode = args.watch != none;
let alert_mode = args.alert != none;

print(f"[*] KentScript Process Monitor v1.0");
print(f"[*] Interval: {interval}s");
print(f"[*] Watch Mode: {watch_mode}");
print("");

:: Suspicious process names
let suspicious_names = [
    "nc", "netcat", "ncat",
    "msf", "metasploit",
    "nikto", "nmap", "hydra",
    "john", "johnny",
    "hashcat", "crack",
    "tcpdump", "wireshark",
    "ettercap", "dsniff",
    "sqlmap", "burp",
    "nikto", "dirb", "gobuster",
    "masscan", "zmap",
    "responder", "impacket",
    "mimikatz", "pwdump",
    "backdoor", "rootkit"
];

:: Suspicious command patterns
let suspicious_patterns = [
    "/dev/tcp/",
    ">&/dev/",
    "0>&1",
    "base64 -d",
    "nc -l",
    "mkfifo",
    "/tmp/",
    "/dev/shm/",
    "chmod +x",
    ".ssh/authorized_keys",
    ".bash_history",
    "/etc/passwd",
    "/etc/shadow"
];

:: Get all processes
func get_processes() {
    let processes = [];
    
    try {
        :: Read /proc filesystem
        let proc_dir = "/proc";
        let entries = system_file_listdir(proc_dir);
        
        for entry in entries {
            let pid = int(entry);
            if pid > 0 {
                let process = get_process_info(pid);
                if process != none {
                    processes.append(process);
                }
            }
        }
    } except e {
        :: Fallback to system info
        let info = system_lowlevel_get_processes_info();
        if info != none {
            for proc in info {
                processes.append(proc);
            }
        }
    }
    
    return processes;
}

func get_process_info(pid) {
    let info = {
        "pid": pid,
        "name": "",
        "cmdline": "",
        "user": "",
        "status": ""
    };
    
    try {
        :: Read process name
        let name_file = f"/proc/{pid}/comm";
        let comm = system_file_read_text(name_file);
        if comm != none {
            info["name"] = str(comm).trim();
        }
        
        :: Read command line
        let cmdline_file = f"/proc/{pid}/cmdline";
        let cmdline = system_file_read_text(cmdline_file);
        if cmdline != none {
            info["cmdline"] = str(cmdline).replace("\x00", " ").trim();
        }
        
        :: Read status
        let status_file = f"/proc/{pid}/status";
        let status = system_file_read_text(status_file);
        if status != none {
            let lines = system_string_split(status, "\n");
            for line in lines {
                if str(line).starts_with("Uid:") {
                    let parts = system_string_split(line, " ");
                    if len(parts) > 1 {
                        info["user"] = parts[1];
                    }
                }
                if str(line).starts_with("State:") {
                    let parts = system_string_split(line, " ");
                    if len(parts) > 1 {
                        info["status"] = parts[1];
                    }
                }
            }
        }
    } except e {
        return none;
    }
    
    return info;
}

func check_suspicious(process) {
    let alerts = [];
    let name = str(process["name"]).lower();
    let cmdline = str(process["cmdline"]).lower();
    
    :: Check suspicious names
    for sus in suspicious_names {
        if str(name).find(sus) >= 0 {
            alerts.append(f"Suspicious name: {sus}");
        }
    }
    
    :: Check suspicious patterns in command line
    for pattern in suspicious_patterns {
        if cmdline.find(pattern) >= 0 {
            alerts.append(f"Suspicious pattern: {pattern}");
        }
    }
    
    :: Check for network connections
    let net_conns = check_network_connections(process["pid"]);
    if len(net_conns) > 0 {
        alerts.append(f"Network connections: {len(net_conns)}");
    }
    
    return alerts;
}

func check_network_connections(pid) {
    let conns = [];
    
    try {
        let tcp_file = f"/proc/{pid}/net/tcp";
        let tcp_content = system_file_read_text(tcp_file);
        if tcp_content != none {
            let lines = system_string_split(tcp_content, "\n");
            :: Skip header
            for i in range(1, lines.len()) {
                let line = lines[i];
                if str(line).len() > 0 {
                    conns.append(line);
                }
            }
        }
    } except e {
        :: Ignore errors
    }
    
    return conns;
}

func print_process(process, alerts) {
    let status_icon = "[+]";
    if len(alerts) > 0 {
        status_icon = "[!]";
    }
    
    print(f"{status_icon} PID: {process["pid"]} | Name: {process["name"]} | User: {process["user"]}");
    
    if len(alerts) > 0 {
        for alert in alerts {
            print(f"    [!] {alert}");
        }
    }
    
    if process["cmdline"].len() > 0 {
        let cmd_short = str(process["cmdline"]).substr(0, 80);
        if str(process["cmdline"]).len() > 80 {
            cmd_short = cmd_short + "...";
        }
        print(f"    CMD: {cmd_short}");
    }
}

func print_header() {
    print("");
    print("=== Process Snapshot ===");
    print(f"Time: {system_time_format(system_time_now(), \"%Y-%m-%d %H:%M:%S\")}");
    print(f"System: {system_platform_os()} {system_platform_arch()}");
    print("");
}

:: Main monitoring loop
let run_count = 0;

func do_scan() {
    run_count = run_count + 1;
    print_header();
    
    let processes = get_processes();
    print(f"Total Processes: {len(processes)}");
    print("");
    
    let suspicious_count = 0;
    let alert_count = 0;
    
    print("--- Suspicious Processes ---");
    
    for proc in processes {
        let alerts = check_suspicious(proc);
        if len(alerts) > 0 {
            suspicious_count = suspicious_count + 1;
            alert_count = alert_count + len(alerts);
            print_process(proc, alerts);
        }
    }
    
    if suspicious_count == 0 {
        print("[*] No suspicious processes detected");
    }
    
    print("");
    print(f"[*] Summary: {suspicious_count} suspicious processes, {alert_count} total alerts");
    
    if alert_mode and alert_count > 0 {
        print("");
        print("[!] ALERT: Suspicious activity detected!");
    }
}

:: Initial scan
do_scan();

:: Continuous monitoring if watch mode
if watch_mode {
    print("");
    print(f"[*] Entering watch mode (Ctrl+C to stop)");
    print("");
    
    while true {
        system_time_sleep(interval);
        do_scan();
    }
}
