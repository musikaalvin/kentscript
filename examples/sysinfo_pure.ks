:: System Info Gatherer — Pure KentScript (no subprocess)
:: Usage: kentscript run sysinfo_pure.ks

print("=== System Information Gatherer ===\n");

:: Platform / kernel (native platform module)
let uname = system_platform_uname();

print("--- Kernel ---");
print(f"OS:       {uname['system']}");
print(f"Node:     {uname['node']}");
print(f"Release:  {uname['release']}");
print(f"Version:  {uname['version']}");
print(f"Machine:  {uname['machine']}");

:: Process & user identity
print("\n--- Identity ---");
print(f"PID:  {system_os_getpid()}");
print(f"PPID: {system_os_getppid()}");
print(f"UID:  {system_os_getuid()}");
print(f"GID:  {system_os_getgid()}");
print(f"CWD:  {system_file_getcwd()}");

:: Environment variables
print("\n--- Environment ---");
print(f"USER:  {system_os_getenv('USER', 'unknown')}");
print(f"HOME:  {system_os_getenv('HOME', 'unknown')}");
print(f"SHELL: {system_os_getenv('SHELL', 'unknown')}");
print(f"LANG:  {system_os_getenv('LANG', 'unknown')}");

:: Network
print("\n--- Network ---");
let hostname = system_socket_gethostname();
print(f"Hostname: {hostname}");
let ip = system_socket_gethostbyname(hostname);
print(f"IP:       {ip}");

:: CPU & memory
print("\n--- Resources ---");
print(f"CPU cores: {system_cpu_count()}");
let mem = system_virtual_memory();
print(f"RAM total: {mem['total'] / 1073741824} GB");
print(f"RAM avail: {mem['available'] / 1073741824} GB");
print(f"RAM used:  {mem['percent']}%");

:: Disk
print("\n--- Disk (/) ---");
let disk = system_disk_usage("/");
print(f"Total: {disk['total'] / 1073741824} GB");
print(f"Used:  {disk['used'] / 1073741824} GB");
print(f"Free:  {disk['free'] / 1073741824} GB");
print(f"Use%:  {disk['percent']}%");

:: Uptime & load
print("\n--- Uptime ---");
let up_secs = system_uptime();
let up_mins = up_secs / 60;
let up_hrs  = up_mins / 60;
let up_days = up_hrs / 24;
print(f"Uptime: {up_days} days, {up_hrs % 24} hrs, {up_mins % 60} min");
let load = system_load_average();
print(f"Load:   {load[0]}, {load[1]}, {load[2]}");

:: Timestamp
print("\n--- Report ---");
let timestamp = system_time_strftime("%Y-%m-%d %H:%M:%S");
print(f"Generated: {timestamp}");

:: Save report
let report = "/tmp/sysinfo_report.txt";
let lines = "System Information Report\n";
lines = lines + f"Generated: {timestamp}\n";
lines = lines + f"Hostname:  {hostname}\n";
lines = lines + f"IP:        {ip}\n";
lines = lines + f"OS:        {uname['system']} {uname['release']}\n";
lines = lines + f"Machine:   {uname['machine']}\n";
lines = lines + f"CPU cores: {system_cpu_count()}\n";
lines = lines + f"RAM:       {mem['total'] / 1073741824} GB  (used {mem['percent']}%)\n";
lines = lines + f"Disk /:    {disk['total'] / 1073741824} GB  (used {disk['percent']}%)\n";
lines = lines + f"UID:       {system_os_getuid()}\n";
lines = lines + f"PID:       {system_os_getpid()}\n";
system_file_write_text(report, lines);
print(f"Report saved to: {report}");
