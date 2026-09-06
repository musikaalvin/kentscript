:: hardware - High-level hardware I/O interface

:: Port I/O operations - delegate to builtins directly
:: On x86: actual in/out instructions; on aarch64: returns 0 (no port I/O)
func outb(port, value) { unsafe { _builtin_outb(port, value); } }
func inb(port) { unsafe { return _builtin_inb(port); } }
func outw(port, value) { unsafe { _builtin_outw(port, value); } }
func inw(port) { unsafe { return _builtin_inw(port); } }
func outl(port, value) { unsafe { _builtin_outl(port, value); } }
func inl(port) { unsafe { return _builtin_inl(port); } }

:: MSR (Model Specific Register) operations
func rdmsr(msr) {
    unsafe {
        return system_rdmsr(msr);
    }
}

func wrmsr(msr, value) {
    unsafe {
        system_wrmsr(msr, value);
    }
}

:: Control register operations
func read_cr0() {
    unsafe {
        let value = 0;
        asm("mov %%cr0, %0" : "=r"(value));
        return value;
    }
}

func write_cr0(value) {
    unsafe {
        asm("mov %0, %%cr0" :: "r"(value));
    }
}

func read_cr2() {
    unsafe {
        let value = 0;
        asm("mov %%cr2, %0" : "=r"(value));
        return value;
    }
}

func read_cr3() {
    unsafe {
        let value = 0;
        asm("mov %%cr3, %0" : "=r"(value));
        return value;
    }
}

func write_cr3(value) {
    unsafe {
        asm("mov %0, %%cr3" :: "r"(value));
    }
}

func read_cr4() {
    unsafe {
        let value = 0;
        asm("mov %%cr4, %0" : "=r"(value));
        return value;
    }
}

func write_cr4(value) {
    unsafe {
        asm("mov %0, %%cr4" :: "r"(value));
    }
}

:: Common hardware devices

:: Serial port (COM1)
const SERIAL_COM1 = 0x3F8;
const SERIAL_COM2 = 0x2F8;

func serial_init(port) {
    outb(port + 1, 0x00);  :: Disable interrupts
    outb(port + 3, 0x80);  :: Enable DLAB
    outb(port + 0, 0x03);  :: Divisor low (38400 baud)
    outb(port + 1, 0x00);  :: Divisor high
    outb(port + 3, 0x03);  :: 8N1
    outb(port + 2, 0xC7);  :: Enable FIFO
    outb(port + 4, 0x0B);  :: Enable IRQs
}

func serial_write(port, c) {
    while (inb(port + 5) & 0x20) == 0 {}
    outb(port, c);
}

func serial_read(port) {
    while (inb(port + 5) & 0x01) == 0 {}
    return inb(port);
}

:: PCI configuration
func pci_config_read(bus, slot, func, offset) {
    let address = (bus << 16) | (slot << 11) | (func << 8) | (offset & 0xFC) | 0x80000000;
    outl(0xCF8, address);
    return inl(0xCFC);
}

func pci_config_write(bus, slot, func, offset, value) {
    let address = (bus << 16) | (slot << 11) | (func << 8) | (offset & 0xFC) | 0x80000000;
    outl(0xCF8, address);
    outl(0xCFC, value);
}

:: PIT (Programmable Interval Timer)
const PIT_CHANNEL0 = 0x40;
const PIT_COMMAND = 0x43;

func pit_set_frequency(hz) {
    let divisor = 1193180 / hz;
    outb(PIT_COMMAND, 0x36);
    outb(PIT_CHANNEL0, divisor & 0xFF);
    outb(PIT_CHANNEL0, (divisor >> 8) & 0xFF);
}

:: PIC (Programmable Interrupt Controller)
const PIC1_COMMAND = 0x20;
const PIC1_DATA = 0x21;
const PIC2_COMMAND = 0xA0;
const PIC2_DATA = 0xA1;

func pic_remap(offset1, offset2) {
    outb(PIC1_COMMAND, 0x11);
    outb(PIC2_COMMAND, 0x11);
    outb(PIC1_DATA, offset1);
    outb(PIC2_DATA, offset2);
    outb(PIC1_DATA, 4);
    outb(PIC2_DATA, 2);
    outb(PIC1_DATA, 0x01);
    outb(PIC2_DATA, 0x01);
    outb(PIC1_DATA, 0x0);
    outb(PIC2_DATA, 0x0);
}

func pic_send_eoi(irq) {
    if irq >= 8 {
        outb(PIC2_COMMAND, 0x20);
    }
    outb(PIC1_COMMAND, 0x20);
}

:: VGA text mode
const VGA_MEMORY = 0xB8000;
const VGA_WIDTH = 80;
const VGA_HEIGHT = 25;

func vga_write(x, y, c, color) {
    let offset = (y * VGA_WIDTH + x) * 2;
    let ptr = (VGA_MEMORY + offset) as ptr;
    *ptr = c | (color << 8);
}

func vga_clear(color) {
    for y in range(VGA_HEIGHT) {
        for x in range(VGA_WIDTH) {
            vga_write(x, y, 32, color);
        }
    }
}

:: Runtime interface
func system_rdmsr(msr) {
    unsafe {
        let lo = 0;
        let hi = 0;
        asm("rdmsr" : "=a"(lo), "=d"(hi) : "c"(msr));
        return lo | (hi << 32);
    }
}
func system_wrmsr(msr, value) {
    unsafe {
        asm("wrmsr" :: "a"(value & 0xFFFFFFFF), "d"((value >> 32) & 0xFFFFFFFF), "c"(msr));
    }
}

export {
    outb, inb, outw, inw, outl, inl,
    rdmsr, wrmsr,
    read_cr0, write_cr0, read_cr2, read_cr3, write_cr3, read_cr4, write_cr4,
    SERIAL_COM1, SERIAL_COM2,
    serial_init, serial_write, serial_read,
    pci_config_read, pci_config_write,
    PIT_CHANNEL0, PIT_COMMAND, pit_set_frequency,
    PIC1_COMMAND, PIC1_DATA, PIC2_COMMAND, PIC2_DATA,
    pic_remap, pic_send_eoi,
    VGA_MEMORY, VGA_WIDTH, VGA_HEIGHT,
    vga_write, vga_clear
};
