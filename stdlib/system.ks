:: system - System information and control

func platform() {
    return system_platform();
}

func machine() {
    return system_machine();
}

func processor() {
    return system_processor();
}

func architecture() {
    return system_architecture();
}

func hostname() {
    return system_hostname();
}

func username() {
    return system_username();
}

func home_directory() {
    return system_home_directory();
}

func cpu_count() {
    return system_cpu_count();
}

func total_memory() {
    return system_total_memory();
}

func available_memory() {
    return system_available_memory();
}

func used_memory() {
    return system_used_memory();
}

func memory_percent() {
    let total = total_memory();
    let used = used_memory();
    return (used * 100.0) / total;
}

func cpu_percent(interval) {
    if interval == none { interval = 1.0; }
    return system_cpu_percent(interval);
}

func cpu_times() {
    return system_cpu_times();
}

func cpu_stats() {
    return system_cpu_stats();
}

func disk_usage(path) {
    return system_disk_usage(path);
}

func disk_partitions() {
    return system_disk_partitions();
}

func network_interfaces() {
    return system_network_interfaces();
}

func network_stats() {
    return system_network_stats();
}

func boot_time() {
    return system_boot_time();
}

func uptime() {
    return time_now() - boot_time();
}

func load_average() {
    return system_load_average();
}

func process_list() {
    return system_process_list();
}

func process_info(pid) {
    return system_process_info(pid);
}

func kill_process(pid, signal) {
    if signal == none { signal = 15; }
    system_kill_process(pid, signal);
}

func environment() {
    return system_environment();
}

func getenv(key, default) {
    let env = environment();
    return env[key] != none ? env[key] : default;
}

func setenv(key, value) {
    system_setenv(key, value);
}

func unsetenv(key) {
    system_unsetenv(key);
}

func current_process_id() {
    return system_current_process_id();
}

func parent_process_id() {
    return system_parent_process_id();
}

func exit(code) {
    if code == none { code = 0; }
    system_exit(code);
}

func abort() {
    system_abort();
}

func sleep(seconds) {
    system_sleep(seconds);
}

func time_now() {
    return system_time_now();
}

:: Runtime interface
func system_platform() { return "linux"; }
func system_machine() { return "x86_64"; }
func system_processor() { return "Intel"; }
func system_architecture() { return ["64bit", "ELF"]; }
func system_hostname() { return "localhost"; }
func system_username() { return "user"; }
func system_home_directory() { return "/home/user"; }
func system_cpu_count() { return 4; }
func system_total_memory() { return 8589934592; }
func system_available_memory() { return 4294967296; }
func system_used_memory() { return 4294967296; }
func system_cpu_percent(interval) { return 25.0; }
func system_cpu_times() { return {"user": 1000, "system": 500, "idle": 3500}; }
func system_cpu_stats() { return {"ctx_switches": 10000, "interrupts": 5000}; }
func system_disk_usage(path) { return {"total": 1000000000, "used": 500000000, "free": 500000000}; }
func system_disk_partitions() { return [{"device": "/dev/sda1", "mountpoint": "/", "fstype": "ext4"}]; }
func system_network_interfaces() { return {"eth0": {"ip": "192.168.1.100", "mac": "00:11:22:33:44:55"}}; }
func system_network_stats() { return {"bytes_sent": 1000000, "bytes_recv": 2000000}; }
func system_boot_time() { return 1709000000; }
func system_load_average() { return [1.5, 1.2, 1.0]; }
func system_process_list() { return [1, 2, 3, 4, 5]; }
func system_process_info(pid) { return {"pid": pid, "name": "process", "status": "running"}; }
func system_kill_process(pid, signal) { }
func system_environment() { return {"PATH": "/usr/bin", "HOME": "/home/user"}; }
func system_setenv(key, value) { }
func system_unsetenv(key) { }
func system_current_process_id() { return 1234; }
func system_parent_process_id() { return 1; }
func system_exit(code) { }
func system_abort() { }
func system_sleep(seconds) { }
func system_time_now() { return 1709640000; }

export {
    platform, machine, processor, architecture,
    hostname, username, home_directory,
    cpu_count, total_memory, available_memory, used_memory, memory_percent,
    cpu_percent, cpu_times, cpu_stats,
    disk_usage, disk_partitions,
    network_interfaces, network_stats,
    boot_time, uptime, load_average,
    process_list, process_info, kill_process,
    environment, getenv, setenv, unsetenv,
    current_process_id, parent_process_id,
    exit, abort, sleep, time_now
};
