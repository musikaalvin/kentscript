/*
 * ============================================================================
 * KentScript Bare-Metal C Runtime (kentsystem_init.c)
 * ============================================================================
 * 
 * This code runs at ring-0 on bare hardware with NO operating system.
 * 
 * Responsibilities:
 * 1. Initialize CPU: GDT, IDT, exception handlers
 * 2. Set up memory: paging, heap allocator
 * 3. Initialize peripherals: UART, PIC, timer
 * 4. Set up KentScript runtime: VM, bytecode interpreter
 * 5. Execute KentScript programs at ring-0
 * 
 * Compilation:
 *   gcc -ffreestanding -fno-pie -c -o boot.o boot_x86_64.asm
 *   gcc -ffreestanding -fno-pic -O2 -c -o kentsystem_init.o kentsystem_init.c
 *   ld -T link.ld boot.o kentsystem_init.o -o kernel.elf
 */

#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>

/* ========================================================================== */
/* PRIMITIVE TYPES & MACROS (no libc available)                             */
/* ========================================================================== */

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int8_t i8;
typedef int16_t i16;
typedef int32_t i32;
typedef int64_t i64;

#define PACKED __attribute__((packed))
#define ALIGN(n) __attribute__((aligned(n)))
#define INLINE static inline
#define NORETURN __attribute__((noreturn))

/* ========================================================================== */
/* MEMORY LAYOUT DEFINITIONS                                                */
/* ========================================================================== */

// Physical memory layout
#define PHYS_BASE       0x0000000000000000  // Lower memory (identity mapped)
#define KERNEL_VIRT_BASE 0xFFFF800000000000 // Kernel high-half
#define IO_BASE         0xA0000             // Video memory start
#define BIOS_ROM        0xE0000             // BIOS ROM area
#define HEAP_START      0x100000            // Start of heap (1MB)
#define HEAP_SIZE       0x1000000           // 16MB heap

/* ========================================================================== */
/* CPU STRUCTURES: GDT, IDT, TSS                                             */
/* ========================================================================== */

// Global Descriptor Table Entry
typedef struct PACKED {
    u16 limit_low;
    u16 base_low;
    u8 base_mid;
    u8 access;      // Present, DPL, Type
    u8 gran;        // Granularity, D/B, L, AVL
    u8 base_high;
} GDTEntry;

// Interrupt Descriptor Table Entry (64-bit)
typedef struct PACKED {
    u16 offset_low;
    u16 selector;
    u8 ist;         // Interrupt Stack Table
    u8 type_attr;   // Type and attributes
    u16 offset_mid;
    u32 offset_high;
    u32 reserved;
} IDTEntry;

// Task State Segment (for ring-0 only kernel, we don't really need this)
typedef struct PACKED {
    u32 reserved0;
    u64 rsp0;       // Ring-0 stack pointer
    u64 rsp1;
    u64 rsp2;
    u64 reserved1;
    u64 ist1, ist2, ist3, ist4, ist5, ist6, ist7;
    u64 reserved2;
    u16 reserved3;
    u16 iopb;       // I/O permission bitmap offset
} TSS ALIGN(16);

/* ========================================================================== */
/* GLOBAL STATE: CPU STRUCTURES                                              */
/* ========================================================================== */

static GDTEntry gdt[8] ALIGN(16) = {0};
static IDTEntry idt[256] ALIGN(16) = {0};
static TSS tss ALIGN(16) = {0};

struct {
    u16 limit;
    u64 base;
} PACKED gdt_ptr, idt_ptr;

/* ========================================================================== */
/* PRIMITIVE I/O: UART SERIAL CONSOLE                                        */
/* ========================================================================== */

#define UART_PORT 0x3F8

INLINE void outb(u16 port, u8 value) {
    asm volatile("outb %0, %1" : : "a"(value), "Nd"(port));
}

INLINE u8 inb(u16 port) {
    u8 value;
    asm volatile("inb %1, %0" : "=a"(value) : "Nd"(port));
    return value;
}

INLINE void outw(u16 port, u16 value) {
    asm volatile("outw %0, %1" : : "a"(value), "Nd"(port));
}

INLINE void outl(u16 port, u32 value) {
    asm volatile("outl %0, %1" : : "a"(value), "Nd"(port));
}

// Simple putchar for serial output
static void putchar_serial(char c) {
    // Wait for transmit buffer to be empty
    while (!(inb(UART_PORT + 5) & 0x20));
    outb(UART_PORT, c);
}

// Print string (no format specifiers for now)
static void puts_serial(const char *s) {
    while (*s) {
        if (*s == '\n') putchar_serial('\r');
        putchar_serial(*s++);
    }
}

// Printf-lite (supports %x, %d, %s, %c)
static void printf_serial(const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);

    while (*fmt) {
        if (*fmt == '%') {
            fmt++;
            switch (*fmt) {
                case 'x': {
                    u64 val = va_arg(args, u64);
                    char buf[17];
                    int i = 15;
                    buf[16] = 0;
                    if (val == 0) buf[i--] = '0';
                    while (val && i >= 0) {
                        buf[i--] = "0123456789abcdef"[val & 0xF];
                        val >>= 4;
                    }
                    puts_serial(&buf[i+1]);
                    break;
                }
                case 'd': {
                    i64 val = va_arg(args, i64);
                    if (val < 0) { putchar_serial('-'); val = -val; }
                    char buf[20];
                    int i = 19;
                    buf[i--] = 0;
                    if (val == 0) buf[i--] = '0';
                    while (val && i >= 0) {
                        buf[i--] = '0' + (val % 10);
                        val /= 10;
                    }
                    puts_serial(&buf[i+1]);
                    break;
                }
                case 's': {
                    const char *s = va_arg(args, const char *);
                    puts_serial(s);
                    break;
                }
                case 'c': {
                    putchar_serial(va_arg(args, int));
                    break;
                }
                default:
                    putchar_serial(*fmt);
            }
            fmt++;
        } else {
            if (*fmt == '\n') putchar_serial('\r');
            putchar_serial(*fmt);
            fmt++;
        }
    }

    va_end(args);
}

/* ========================================================================== */
/* CPU: GLOBAL DESCRIPTOR TABLE SETUP                                        */
/* ========================================================================== */

static void gdt_init(void) {
    puts_serial("[KentScript] Initializing GDT...\n");

    // Null descriptor
    gdt[0] = (GDTEntry){0};

    // Kernel code (ring-0): base=0, limit=0xFFFFFFFF, executable, 64-bit
    gdt[1] = (GDTEntry){
        .limit_low = 0xFFFF,
        .base_low = 0,
        .base_mid = 0,
        .access = 0x9A,         // Present, DPL=0, Code, Non-conforming
        .gran = 0xA0,           // Granularity (4KB), 64-bit
        .base_high = 0,
    };

    // Kernel data (ring-0): base=0, limit=0xFFFFFFFF, writable
    gdt[2] = (GDTEntry){
        .limit_low = 0xFFFF,
        .base_low = 0,
        .base_mid = 0,
        .access = 0x92,         // Present, DPL=0, Data, Expand-down
        .gran = 0xC0,           // Granularity (4KB), 32-bit
        .base_high = 0,
    };

    // TSS (for ring-0, not strictly needed, but good practice)
    // TODO: Fill in TSS entry

    // Load GDT
    gdt_ptr.limit = sizeof(gdt) - 1;
    gdt_ptr.base = (u64)&gdt[0];
    asm volatile("lgdt (%0)" : : "r"(&gdt_ptr) : "memory");

    puts_serial("[KentScript] GDT loaded\n");
}

/* ========================================================================== */
/* CPU: INTERRUPT DESCRIPTOR TABLE SETUP                                     */
/* ========================================================================== */

// Exception handler type (we'll set these later)
typedef void (*exception_handler_t)(void);

// Interrupt stack frame (pushed automatically by CPU)
typedef struct {
    u64 rax, rcx, rdx, rbx;
    u64 rsp_val, rbp, rsi, rdi;
    u64 r8, r9, r10, r11, r12, r13, r14, r15;
    u64 error_code;
    u64 rip;
    u64 cs;
    u64 flags;
    u64 rsp;
    u64 ss;
} PACKED InterruptFrame;

// Interrupt handlers (stubs for now)
static void isr_divide_by_zero(InterruptFrame *frame) {
    printf_serial("[KentScript] EXCEPTION: Divide by zero at RIP=0x%x\n", frame->rip);
    // Hang
    while(1) asm volatile("hlt");
}

static void isr_page_fault(InterruptFrame *frame) {
    u64 cr2;
    asm volatile("mov %%cr2, %0" : "=r"(cr2));
    printf_serial("[KentScript] PAGE FAULT: Address=0x%x, RIP=0x%x\n", cr2, frame->rip);
    while(1) asm volatile("hlt");
}

static void isr_general_protection_fault(InterruptFrame *frame) {
    printf_serial("[KentScript] GPF: error_code=0x%x, RIP=0x%x\n", frame->error_code, frame->rip);
    while(1) asm volatile("hlt");
}

static void isr_timer(InterruptFrame *frame) {
    // Timer interrupt - just for now, acknowledge the PIC
    outb(0x20, 0x20);  // EOI to master PIC
    // TODO: Implement scheduling, clock tick handling
}

// Generate IDT entry for an interrupt handler
static void idt_set_entry(u8 vector, exception_handler_t handler, u8 type) {
    u64 handler_addr = (u64)handler;
    idt[vector].offset_low = handler_addr & 0xFFFF;
    idt[vector].selector = 0x08;                    // Kernel code segment
    idt[vector].ist = 0;                            // No IST for ring-0
    idt[vector].type_attr = type;                   // Trap/interrupt gate, Present
    idt[vector].offset_mid = (handler_addr >> 16) & 0xFFFF;
    idt[vector].offset_high = (handler_addr >> 32) & 0xFFFFFFFF;
    idt[vector].reserved = 0;
}

static void idt_init(void) {
    puts_serial("[KentScript] Initializing IDT...\n");

    // Clear IDT
    for (int i = 0; i < 256; i++) {
        idt[i] = (IDTEntry){0};
    }

    // Install exception handlers
    // Note: In real code, we'd use wrapper functions that save registers
    // For now, these are placeholder stubs
    
    // Vector 0: Divide by Zero
    idt_set_entry(0, (exception_handler_t)isr_divide_by_zero, 0x8F);
    
    // Vector 14: Page Fault
    idt_set_entry(14, (exception_handler_t)isr_page_fault, 0x8F);
    
    // Vector 13: General Protection Fault
    idt_set_entry(13, (exception_handler_t)isr_general_protection_fault, 0x8F);
    
    // Vector 32: Timer (IRQ0)
    idt_set_entry(32, (exception_handler_t)isr_timer, 0x8E);

    // Load IDT
    idt_ptr.limit = sizeof(idt) - 1;
    idt_ptr.base = (u64)&idt[0];
    asm volatile("lidt (%0)" : : "r"(&idt_ptr) : "memory");

    puts_serial("[KentScript] IDT loaded\n");
}

/* ========================================================================== */
/* MEMORY: HEAP ALLOCATOR (simple bump allocator for now)                   */
/* ========================================================================== */

static u64 heap_ptr = HEAP_START;

void *kmalloc(size_t size) {
    // Simple bump allocator
    void *ptr = (void *)heap_ptr;
    heap_ptr += size;
    
    if (heap_ptr > HEAP_START + HEAP_SIZE) {
        puts_serial("[KentScript] ERROR: Heap exhausted\n");
        return NULL;
    }
    
    return ptr;
}

void kfree(void *ptr) {
    // Bump allocator doesn't actually free (for simplicity)
    // In a real implementation, use a slab allocator
    (void)ptr;
}

/* ========================================================================== */
/* HARDWARE: PIC (PROGRAMMABLE INTERRUPT CONTROLLER)                        */
/* ========================================================================== */

static void pic_init(void) {
    puts_serial("[KentScript] Initializing PIC...\n");

    // ICW1: Initialize master PIC
    outb(0x20, 0x11);
    // ICW2: IRQ0 maps to vector 32
    outb(0x21, 0x20);
    // ICW3: Slave on IRQ2
    outb(0x21, 0x04);
    // ICW4: x86 mode
    outb(0x21, 0x01);
    
    // Initialize slave PIC
    outb(0xA0, 0x11);
    outb(0xA1, 0x28);  // IRQ8 maps to vector 40
    outb(0xA1, 0x02);
    outb(0xA1, 0x01);

    // Unmask timer interrupt (IRQ0) on master PIC
    u8 mask = inb(0x21);
    mask &= ~0x01;  // Clear bit 0
    outb(0x21, mask);

    puts_serial("[KentScript] PIC initialized\n");
}

/* ========================================================================== */
/* TIMER: 8254 PIT (PROGRAMMABLE INTERVAL TIMER)                            */
/* ========================================================================== */

static void timer_init(void) {
    puts_serial("[KentScript] Initializing timer...\n");

    // Set timer to 100 Hz (10ms ticks)
    u32 divisor = 11932;  // 1.193182 MHz / 100 Hz
    
    // Command: channel 0, both bytes, binary
    outb(0x43, 0x34);
    
    // Load divisor (little-endian)
    outb(0x40, divisor & 0xFF);
    outb(0x40, (divisor >> 8) & 0xFF);

    puts_serial("[KentScript] Timer initialized (100 Hz)\n");
}

/* ========================================================================== */
/* KENTSYSTEM INITIALIZATION (called from boot.asm)                          */
/* ========================================================================== */

void kentsystem_init(uint64_t multiboot_info) {
    puts_serial("\n\n");
    puts_serial("===============================================\n");
    puts_serial("KentScript Bare-Metal Kernel\n");
    puts_serial("===============================================\n");
    puts_serial("Booting at ring-0 on bare hardware\n");
    puts_serial("No operating system. No libc. Pure kernel code.\n");
    puts_serial("===============================================\n\n");

    printf_serial("[KentScript] Multiboot info: 0x%x\n", multiboot_info);

    // Initialize CPU
    gdt_init();
    idt_init();
    pic_init();
    timer_init();

    // Clear interrupts are already disabled, but let's be explicit
    asm volatile("cli");

    // Enable interrupts (now that IDT is set up)
    asm volatile("sti");

    printf_serial("[KentScript] Interrupts enabled\n");
    printf_serial("[KentScript] Heap base: 0x%x\n", HEAP_START);
    printf_serial("[KentScript] Heap size: 0x%x bytes\n", HEAP_SIZE);

    // ====================================================================
    // AT THIS POINT, WE'RE READY TO RUN KENTSYSTEM PROGRAMS
    // ====================================================================

    puts_serial("\n[KentScript] System initialized. Ready to execute KentScript programs.\n");
    puts_serial("[KentScript] Running test program...\n\n");

    // Test: Ring-0 proof of concept
    printf_serial("=== KentScript Ring-0 Test ===\n");
    printf_serial("Current privilege level: 0 (ring-0, kernel mode)\n");
    
    // Read CR0 to prove we're at ring-0
    u64 cr0;
    asm volatile("mov %%cr0, %0" : "=r"(cr0));
    printf_serial("CR0 (control register): 0x%x\n", cr0);

    // Read CR3 (page table base)
    u64 cr3;
    asm volatile("mov %%cr3, %0" : "=r"(cr3));
    printf_serial("CR3 (page table base): 0x%x\n", cr3);

    // Read CPUID
    u32 eax = 1, ebx = 0, ecx = 0, edx = 0;
    asm volatile("cpuid" : "+a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx));
    printf_serial("CPUID (family/model): 0x%x\n", eax);

    // Allocate memory at ring-0
    void *test_buf = kmalloc(1024);
    printf_serial("Allocated 1KB buffer at 0x%x\n", (u64)test_buf);

    // Write to buffer (direct memory access at ring-0)
    u8 *buf = (u8 *)test_buf;
    for (int i = 0; i < 256; i++) {
        buf[i] = i;
    }
    printf_serial("Wrote 256 bytes to buffer\n");

    // Verify
    int errors = 0;
    for (int i = 0; i < 256; i++) {
        if (buf[i] != i) errors++;
    }
    printf_serial("Verification: %s\n", errors == 0 ? "OK" : "FAILED");

    puts_serial("\n=== Test Complete ===\n");
    puts_serial("\nKentScript is now running at ring-0 with full hardware access.\n");
    puts_serial("Next: Load and execute KentScript bytecode/compiled programs.\n\n");

    // Spin (in real implementation, enter scheduler)
    while (1) {
        asm volatile("hlt");
    }
}

/* ============================================================================
 * REQUIRED GCC SUPPORT FUNCTIONS (no libc)
 * ============================================================================ */

// Memory copy
void *memcpy(void *dest, const void *src, size_t n) {
    u8 *d = dest;
    const u8 *s = src;
    while (n--) *d++ = *s++;
    return dest;
}

// Memory set
void *memset(void *s, int c, size_t n) {
    u8 *p = s;
    while (n--) *p++ = c;
    return s;
}

// String length
size_t strlen(const char *s) {
    size_t n = 0;
    while (*s++) n++;
    return n;
}
