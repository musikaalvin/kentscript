import hardware;

func read_rtc_register(reg_num) {
    :: Write register address to port 0x70
    hardware.write_port(112, reg_num);
    :: Read data from port 0x71
    let value = hardware.read_port(113);
    return value;
};

func get_seconds() {
    return read_rtc_register(0);
};

func get_minutes() {
    return read_rtc_register(2);
};

func get_hours() {
    return read_rtc_register(4);
};

func get_day() {
    return read_rtc_register(7);
};

func get_month() {
    return read_rtc_register(8);
};

func get_year() {
    return read_rtc_register(9);
};

print("╔═══════════════════════════════════════════╗");
print("║  KentScript CMOS RTC Clock Reader v1.0   ║");
print("║  Reading RTC via I/O Ports 0x70/0x71     ║");
print("╚═══════════════════════════════════════════╝");
print("═══════════════════════════════════════════");
print("CMOS RTC TIME & DATE");
print("═══════════════════════════════════════════");

let s = get_seconds();
let m = get_minutes();
let h = get_hours();

print("Time: " + str(h) + ":" + str(m) + ":" + str(s));

let d = get_day();
let mo = get_month();
let y = get_year();

print("Date: " + str(mo) + "/" + str(d) + "/" + str(y));

print("═══════════════════════════════════════════");
print("✓ RTC Read Complete");
print("═══════════════════════════════════════════");