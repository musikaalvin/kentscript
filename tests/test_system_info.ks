:: Test Phase 9 - System Information

print("Test: CPU & Memory");
let cpu = system_cpu_count();
if cpu > 0 {
    print("✓ cpu_count() works: " + str(cpu) + " cores");
}
let mem = system_virtual_memory();
if mem != none and mem['total'] > 0 {
    print("✓ virtual_memory() works - total: " + str(mem['total']));
}

print("\nTest: Disk & Network");
let disk = system_disk_usage("/");
if disk != none and disk['total'] > 0 {
    print("✓ disk_usage() works - total: " + str(disk['total']));
}
let net = system_network_interfaces();
if net != none {
    print("✓ network_interfaces() works");
}

print("\nTest: Platform & Uptime");
let plat = system_platform();
if plat != none {
    print("✓ platform() works - " + plat['system']);
}
let uptime = system_uptime();
if uptime > 0 {
    print("✓ uptime() works: " + str(uptime) + " seconds");
}
let load = system_load_average();
if load != none {
    print("✓ load_average() works: " + str(load));
}

print("\n=== Phase 9 System Info Complete ===");
