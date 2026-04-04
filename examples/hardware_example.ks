:: Hardware Access Example - Bare-Metal I/O
:: This demonstrates real hardware access capabilities

:: Get system hardware info (no root needed)
let cpu_count = hardware.get_cpu_count();
let page_size = hardware.get_page_size();
let kernel = hardware.get_kernel_version();

print("=== Hardware Information ===");
print("CPUs: " + str(cpu_count));
print("Page Size: " + str(page_size) + " bytes");
print("Kernel: " + kernel);

:: Get detailed CPU information
let cpu_info = hardware.get_cpu_info();
print("\n=== CPU Details ===");
print(str(cpu_info));

:: Get memory information
let mem = hardware.get_memory_info();
print("\n=== Memory Info ===");
print(str(mem));

:: Get thermal information (if available)
let thermal = hardware.get_thermal();
print("\n=== Thermal Info ===");
print(str(thermal));

:: Get network statistics
let net = hardware.get_network_stats();
print("\n=== Network Stats ===");
print(str(net));

:: Get disk statistics
let disk = hardware.get_disk_stats();
print("\n=== Disk Stats ===");
print(str(disk));

:: I/O Port example (requires root)
:: Uncomment to use if running as root:
:: hardware.init_hardware_perms();
:: let port_value = hardware.inb(0x60);
:: print("Keyboard port (0x60): " + str(port_value));

print("\n✓ Hardware info module loaded successfully");
