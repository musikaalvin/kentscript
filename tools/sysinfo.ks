:: System Info Gatherer - Collect system information
:: Usage: python3 main.py run sysinfo.ks

print("=== System Information Gatherer ===\n");

:: Basic info
print("--- Basic Info ---");
print(f"Hostname: {system_socket_gethostname()}");
print(f"PID: {system_os_getpid()}");
print(f"CWD: {system_file_getcwd()}");

:: Environment
print("\n--- Environment ---");
print(f"USER: {system_os_getenv('USER', 'unknown')}");
print(f"HOME: {system_os_getenv('HOME', 'unknown')}");
print(f"SHELL: {system_os_getenv('SHELL', 'unknown')}");
print(f"PATH: {system_os_getenv('PATH', 'unknown')}");

:: System commands
print("\n--- System Info ---");
let uname = system_subprocess_run("uname -a", true, true);
print(f"Kernel: {uname.stdout}");

let uptime = system_subprocess_run("uptime", true, true);
print(f"Uptime: {uptime.stdout}");

let whoami = system_subprocess_run("whoami", true, true);
print(f"User: {whoami.stdout}");

:: Network info
print("\n--- Network Info ---");
let ip = system_subprocess_run("hostname -I", true, true);
print(f"IP: {ip.stdout}");

:: Disk usage
print("--- Disk Usage ---");
let df = system_subprocess_run("df -h / | tail -1", true, true);
print(f"Root: {df.stdout}");

:: Save report
let report = "/tmp/sysinfo_report.txt";
let timestamp = system_subprocess_run("date", true, true).stdout;
let report_content = f"System Information Report
Generated: {timestamp}
Hostname: {system_socket_gethostname()}
User: {whoami.stdout}
Kernel: {uname.stdout}";

system_file_write_text(report, report_content);
print(f"\n[+] Report saved to: {report}");
