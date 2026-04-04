:: System Info Gatherer — Low-Level KentScript
:: Reads /proc and /sys directly via file descriptors, raw syscalls, unsafe buffers
:: No subprocess, no high-level system_* wrappers
:: Usage: kentscript run sysinfo_lowlevel.ks

import os;

print("=== System Info (Low-Level) ===\n");

:: ─── helpers ───────────────────────────────────────────────
:: Read an entire /proc or /sys file into a string via fd ops
func read_proc(path) {
    let fd = system_open(path, O_RDONLY);
    let data = system_read(fd, 8192);
    system_close(fd);
    return data;
}

:: Grab value after ": " in a single-line /proc entry
func parse_val(line) {
    let i = 0;
    let len_line = len(line);
    while i < len_line - 1 {
        if line[i] == ":" and line[i + 1] == " " {
            return line[i + 2:];
        };
        i = i + 1;
    };
    return line;
}

:: ─── 1. Process identity via syscall wrappers ──────────────
print("--- Process Identity (syscall wrappers) ---");
let pid  = system_os_getpid();
let ppid = system_os_getppid();
let uid  = system_os_getuid();
let gid  = system_os_getgid();
print(f"PID:  {pid}");
print(f"PPID: {ppid}");
print(f"UID:  {uid}");
print(f"GID:  {gid}");
let cwd = system_file_getcwd();
print(f"CWD:  {cwd}");

:: ─── 2. Kernel version from /proc/version ─────────────────
print("\n--- Kernel ---");
let version_raw = read_proc("/proc/version");
let version_line = version_raw[0:version_raw.find("\n")];
print(f"Version: {version_line}");

:: ─── 3. Uptime from /proc/uptime ──────────────────────────
print("\n--- Uptime (from /proc/uptime) ---");
let uptime_raw = read_proc("/proc/uptime");
let uptime_secs = float(uptime_raw[0:uptime_raw.find(" ")]);
let up_days  = uptime_secs / 86400;
let up_hrs   = (uptime_secs % 86400) / 3600;
let up_mins  = (uptime_secs % 3600) / 60;
print(f"Uptime: {up_days}d {up_hrs}h {up_mins}m  ({uptime_secs}s)");

:: ─── 4. Load average from /proc/loadavg ───────────────────
print("\n--- Load Average (from /proc/loadavg) ---");
let load_raw = read_proc("/proc/loadavg");
let load_parts = load_raw.split(" ");
print(f"1 min:  {load_parts[0]}");
print(f"5 min:  {load_parts[1]}");
print(f"15 min: {load_parts[2]}");
print(f"Tasks:  {load_parts[3]}");

:: ─── 5. Memory from /proc/meminfo ─────────────────────────
print("\n--- Memory (from /proc/meminfo) ---");
let mem_raw = read_proc("/proc/meminfo");
let mem_lines = mem_raw.split("\n");
let mem = {};
for line in mem_lines {
    if len(line) > 0 {
        let parts = line.split(":");
        if len(parts) >= 2 {
            let key = parts[0].strip();
            let val_str = parts[1].strip().split(" ")[0];
            mem[key] = float(val_str);
        };
    };
};
let mem_total = mem["MemTotal"] / 1024;
let mem_avail = mem["MemAvailable"] / 1024;
let mem_free  = mem["MemFree"] / 1024;
let mem_buffers = mem["Buffers"] / 1024;
let mem_cached  = mem["Cached"] / 1024;
let mem_used = mem_total - mem_avail;
print(f"Total:     {mem_total} MB");
print(f"Available: {mem_avail} MB");
print(f"Used:      {mem_used} MB");
print(f"Free:      {mem_free} MB");
print(f"Buffers:   {mem_buffers} MB");
print(f"Cached:    {mem_cached} MB");
let swap_total = mem["SwapTotal"] / 1024;
let swap_free  = mem["SwapFree"] / 1024;
print(f"Swap:      {swap_total - swap_free} / {swap_total} MB");

:: ─── 6. CPU info from /proc/cpuinfo ───────────────────────
print("\n--- CPU (from /proc/cpuinfo) ---");
let cpu_raw = read_proc("/proc/cpuinfo");
let cpu_lines = cpu_raw.split("\n");
let cpu_model = "";
let cpu_cores = 0;
let cpu_mhz   = "";
for line in cpu_lines {
    if line.startswith("model name") {
        cpu_model = parse_val(line);
    };
    if line.startswith("processor") {
        cpu_cores = cpu_cores + 1;
    };
    if line.startswith("cpu MHz") {
        cpu_mhz = parse_val(line);
    };
};
print(f"Model:  {cpu_model}");
print(f"Cores:  {cpu_cores}");
print(f"MHz:    {cpu_mhz}");

:: ─── 7. Disk info from /proc/diskstats + statvfs ──────────
print("\n--- Disk (from /proc/diskstats) ---");
let disk_raw = read_proc("/proc/diskstats");
let disk_lines = disk_raw.split("\n");
for line in disk_lines {
    if line.contains("sda") or line.contains("vda") or line.contains("nvme0n1") {
        let parts = line.split(" ");
        :: filter empty strings from split
        let filtered = [];
        for p in parts {
            if len(p) > 0 {
                filtered.append(p);
            };
        };
        if len(filtered) >= 14 {
            print(f"  Device: {filtered[2]}");
            print(f"    Reads completed:  {filtered[3]}");
            print(f"    Writes completed: {filtered[7]}");
            print(f"    Sectors read:     {filtered[5]}");
            print(f"    Sectors written:  {filtered[9]}");
        };
    };
};

:: Root filesystem usage via system_disk_usage
let disk = system_disk_usage("/");
print(f"\n  Root / usage:");
print(f"    Total: {disk['total'] / 1073741824} GB");
print(f"    Free:  {disk['free'] / 1073741824} GB");
print(f"    Used:  {disk['percent']}%");

:: ─── 8. Network from /sys/class/net ───────────────────────
print("\n--- Network (from /sys/class/net) ---");
let ifaces = system_network_interfaces();
for name in ifaces.keys() {
    if name != "lo" {
        let addrs = ifaces[name];
        :: Read MAC from /sys
        let mac_path = f"/sys/class/net/{name}/address";
        let mac = "unknown";
        let mac_fd = system_open(mac_path, O_RDONLY);
        if mac_fd >= 0 {
            mac = system_read(mac_fd, 32).strip();
            system_close(mac_fd);
        };
        :: Read operstate
        let state_path = f"/sys/class/net/{name}/operstate";
        let state = "?";
        let s_fd = system_open(state_path, O_RDONLY);
        if s_fd >= 0 {
            state = system_read(s_fd, 16).strip();
            system_close(s_fd);
        };
        print(f"  {name}  [{state}]  mac={mac}");
        for a in addrs {
            print(f"    addr: {a}");
        };
    };
};

:: ─── 9. OS release from /etc/os-release ───────────────────
print("\n--- OS Release (from /etc/os-release) ---");
let osrel_raw = read_proc("/etc/os-release");
let osrel_lines = osrel_raw.split("\n");
for line in osrel_lines {
    if line.startswith("PRETTY_NAME") or line.startswith("NAME=") or line.startswith("VERSION=") {
        print(f"  {parse_val(line)}");
    };
};

:: ─── 10. Hostname via /proc/sys/kernel ────────────────────
print("\n--- Hostname (from /proc/sys/kernel/hostname) ---");
let hostname_raw = read_proc("/proc/sys/kernel/hostname");
let hostname = hostname_raw.strip();
print(f"Hostname: {hostname}");

:: ─── 11. File descriptors in use (from /proc/self/fd) ────
print("\n--- Open File Descriptors (from /proc/self/fd) ---");
let fd_count = 0;
let fd_entries = os.listdir("/proc/self/fd");
fd_count = len(fd_entries);
print(f"Open FDs: {fd_count}");

:: ─── 12. Raw memory stats from unsafe allocator ──────────
print("\n--- Unsafe Allocator Stats ---");
unsafe {
    let stats = memory_stats();
    print(f"Allocations: {stats}");
};

:: ─── 13. Timestamp and save report ────────────────────────
print("\n--- Report ---");
let timestamp = system_time_strftime("%Y-%m-%d %H:%M:%S");
print(f"Generated: {timestamp}");

let report = "/tmp/sysinfo_lowlevel_report.txt";
let report_content = "Low-Level System Information Report\n";
report_content = report_content + f"Generated: {timestamp}\n";
report_content = report_content + f"Hostname:  {hostname}\n";
report_content = report_content + f"PID:       {pid}\n";
report_content = report_content + f"PPID:      {ppid}\n";
report_content = report_content + f"UID:       {uid}\n";
report_content = report_content + f"GID:       {gid}\n";
report_content = report_content + f"CWD:       {cwd}\n";
report_content = report_content + f"Kernel:    {version_line}\n";
report_content = report_content + f"CPU:       {cpu_model} x{cpu_cores} @ {cpu_mhz} MHz\n";
report_content = report_content + f"Memory:    {mem_used} / {mem_total} MB used\n";
report_content = report_content + f"Swap:      {swap_total - swap_free} / {swap_total} MB\n";
report_content = report_content + f"Uptime:    {up_days}d {up_hrs}h {up_mins}m\n";
report_content = report_content + f"Load:      {load_parts[0]} {load_parts[1]} {load_parts[2]}\n";
system_file_write_text(report, report_content);
print(f"Report saved to: {report}");
