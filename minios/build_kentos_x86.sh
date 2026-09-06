#!/usr/bin/env bash
# ============================================================================
# build_kentos_x86.sh — KentScript x86-64 Kernel Build Script
#
# Produces a real bootable raw disk image: os.img
# Boots under:  qemu-system-x86_64 -drive format=raw,file=os.img -m 128M
# Boots under:  VirtualBox (raw disk) / real hardware via dd to USB
#
# Requirements:
#   nasm      — for boot.asm  (apt install nasm)
#   gcc       — cross or native x86-64  (apt install gcc)
#   ld        — GNU linker    (comes with binutils)
#   qemu-system-x86_64 (optional, for run target)
#
# Usage:
#   bash build_kentos_x86.sh          # build only
#   bash build_kentos_x86.sh run      # build + run in QEMU
#   bash build_kentos_x86.sh clean    # remove build artifacts
# ============================================================================

set -e

# ── Colour output ─────────────────────────────────────────────────────────────
R='\033[0m'; BOLD='\033[1m'
GREEN='\033[92m'; CYAN='\033[96m'; YELLOW='\033[93m'; RED='\033[91m'
ok()   { echo -e "  ${GREEN}✔${R}  $*"; }
info() { echo -e "  ${CYAN}ℹ${R}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${R}  $*"; }
err()  { echo -e "  ${RED}✘${R}  $*"; exit 1; }
hdr()  { echo -e "\n${BOLD}${CYAN}══ $* ══${R}"; }

# ── Configuration ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build_x86"
DIST_DIR="${SCRIPT_DIR}/dist_x86"

BOOT_ASM="${SCRIPT_DIR}/boot.asm"
LINKER_LD="${SCRIPT_DIR}/linker_x86.ld"
OUTPUT_IMG="${DIST_DIR}/kentos_x86.img"
OUTPUT_ELF="${DIST_DIR}/kentos_x86.elf"
OUTPUT_MAP="${DIST_DIR}/kentos_x86.map"

# Kernel C/asm sources (all freestanding, no libc)
KERNEL_SRCS=(
    "${SCRIPT_DIR}/ks_runtime.c"
    "${SCRIPT_DIR}/gdt.c"
    "${SCRIPT_DIR}/idt.c"
    "${SCRIPT_DIR}/scheduler.c"
    "${SCRIPT_DIR}/vmem.c"
    "${SCRIPT_DIR}/syscall_dispatch.c"
    "${SCRIPT_DIR}/ks_slab.c"
    "${SCRIPT_DIR}/kmain.c"          # Kernel entry — generated below if missing
)
KERNEL_ASM_SRCS=(
    "${SCRIPT_DIR}/ks_isr_stubs.S"
)

# Compiler flags — freestanding, no stdlib, no CRT, real hardware
CC="${CC:-gcc}"
CFLAGS=(
    -ffreestanding          # No stdlib assumptions
    -fno-stack-protector    # No SSP (no libc __stack_chk_fail)
    -fno-pic                # No PIC for kernel
    -fno-asynchronous-unwind-tables
    -nostdlib               # No standard libraries
    -nostdinc               # No standard includes (we use our own headers)
    -I"${SCRIPT_DIR}"       # Our headers: ks_runtime.h, ks_platform.h, etc.
    -mno-red-zone           # Disable red zone (mandatory for kernel interrupt handlers)
    -mcmodel=kernel         # Kernel code model (high addresses, no PIC)
    -O2                     # Optimise (safe for kernel)
    -Wall -Wextra
    -std=gnu11
)
LDFLAGS=(
    -T "${LINKER_LD}"
    -Map="${OUTPUT_MAP}"
    --no-undefined
)

# ── Helper: check required tools ──────────────────────────────────────────────
check_tools() {
    hdr "Checking Tools"
    local missing=0
    for tool in nasm gcc ld objcopy; do
        if command -v "$tool" &>/dev/null; then
            ok "$tool: $(command -v "$tool")"
        else
            warn "$tool not found"
            missing=1
        fi
    done
    [ $missing -eq 1 ] && err "Install missing tools: sudo apt install nasm gcc binutils"
}

# ── Generate linker script if missing ────────────────────────────────────────
gen_linker_script() {
    cat > "${LINKER_LD}" << 'LDEOF'
/* KentScript x86-64 Kernel Linker Script
 * Kernel loads at 1MB physical = 0x100000
 * Boot sector identity-maps first 1GB with 2MB pages
 */
OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)
ENTRY(kmain)

SECTIONS {
    . = 0x100000;               /* Load at 1MB */

    .text ALIGN(4096) : {
        *(.text.boot)           /* Boot critical code first */
        *(.text*)
        *(.rodata*)
    }

    .data ALIGN(4096) : {
        *(.data*)
    }

    .bss ALIGN(4096) : {
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        __bss_end = .;
    }

    . = ALIGN(4096);
    __kernel_end = .;

    /DISCARD/ : {
        *(.note*)
        *(.comment*)
        *(.eh_frame*)
    }
}
LDEOF
}

# ── Generate a minimal kmain.c if the user hasn't written one yet ─────────────
gen_kmain() {
    local kmain="${SCRIPT_DIR}/kmain.c"
    [ -f "$kmain" ] && return

    warn "kmain.c not found — generating minimal kernel entry"
    cat > "$kmain" << 'CEOF'
/*
 * kmain.c — KentScript x86-64 Kernel Entry Point
 *
 * This is where boot.asm jumps after setting up long mode.
 * Replace / extend this with your own kernel logic.
 */

#include "ks_runtime.h"

/* ── VGA text-mode output (80×25, base 0xB8000) ─────────────────────────── */
#define VGA_BASE ((volatile uint16_t *)0xB8000)
#define VGA_COLS 80
#define VGA_ROWS 25
#define VGA_WHITE_ON_BLACK 0x0F00

static int vga_row = 0, vga_col = 0;

static void vga_clear(void) {
    for (int i = 0; i < VGA_ROWS * VGA_COLS; i++)
        VGA_BASE[i] = VGA_WHITE_ON_BLACK | ' ';
    vga_row = 0; vga_col = 0;
}

static void vga_putc(char c) {
    if (c == '\n') { vga_row++; vga_col = 0; return; }
    if (vga_col >= VGA_COLS) { vga_row++; vga_col = 0; }
    if (vga_row >= VGA_ROWS) { vga_row = 0; }   /* wrap (simple) */
    VGA_BASE[vga_row * VGA_COLS + vga_col++] = VGA_WHITE_ON_BLACK | (uint8_t)c;
}

static void vga_print(const char *s) {
    while (*s) vga_putc(*s++);
}

static void vga_print_hex(uint64_t v) {
    const char *hex = "0123456789ABCDEF";
    vga_print("0x");
    for (int i = 60; i >= 0; i -= 4)
        vga_putc(hex[(v >> i) & 0xF]);
}

/* ── PIC remapping (so IRQs don't collide with CPU exceptions) ────────────── */
static void pic_remap(void) {
    /* Remap PIC1 to IRQ 32–39, PIC2 to IRQ 40–47 */
    ks_outb(0x20, 0x11); ks_outb(0xA0, 0x11);   /* Init command */
    ks_outb(0x21, 0x20); ks_outb(0xA1, 0x28);   /* Vector offsets */
    ks_outb(0x21, 0x04); ks_outb(0xA1, 0x02);   /* Cascade */
    ks_outb(0x21, 0x01); ks_outb(0xA1, 0x01);   /* 8086 mode */
    ks_outb(0x21, 0xFE); ks_outb(0xA1, 0xFF);   /* Mask all but IRQ0 (timer) */
}

/* ── PIT timer (IRQ0 → vector 32) at ~100Hz ──────────────────────────────── */
static volatile uint64_t ks_ticks = 0;

void ks_timer_handler(uint64_t vec, uint64_t ec, void *frame) {
    (void)vec; (void)ec; (void)frame;
    ks_ticks++;
    /* Acknowledge PIC */
    ks_outb(0x20, 0x20);
    /* Round-robin schedule */
    ks_schedule();
}

static void pit_init(uint32_t hz) {
    uint32_t divisor = 1193180 / hz;
    ks_outb(0x43, 0x36);                    /* Channel 0, lobyte/hibyte, mode 3 */
    ks_outb(0x40, (uint8_t)(divisor & 0xFF));
    ks_outb(0x40, (uint8_t)(divisor >> 8));
}

/* ── BSS zero-fill (linker provides __bss_start / __bss_end) ─────────────── */
extern uint8_t __bss_start, __bss_end;
static void zero_bss(void) {
    uint8_t *p = &__bss_start;
    while (p < &__bss_end) *p++ = 0;
}

/* ── Demo kernel task ────────────────────────────────────────────────────── */
static void demo_task(void) {
    uint64_t last = 0;
    while (1) {
        if (ks_ticks != last) {
            last = ks_ticks;
            /* Every 100 ticks (~1 second), print a dot */
            if (last % 100 == 0) vga_putc('.');
        }
        __asm__ volatile("hlt");
    }
}

/* ── ISR stubs table (from ks_isr_stubs.S) ──────────────────────────────── */
extern uint64_t ks_isr_table[256];

/* ── Kernel main ─────────────────────────────────────────────────────────── */
void kmain(void) {
    zero_bss();
    vga_clear();

    vga_print("╔══════════════════════════════════════════╗\n");
    vga_print("║     KentScript OS Kernel  v3.0           ║\n");
    vga_print("║     x86-64  |  Long Mode  |  Ring 0      ║\n");
    vga_print("╚══════════════════════════════════════════╝\n");
    vga_print("\n");

    /* GDT — uses existing ks_runtime stack (ks_runtime.h stack macros) */
    static uint8_t ring0_stack[65536] __attribute__((aligned(16)));
    vga_print("[1/6] GDT...");
    gdt_init(ring0_stack, sizeof(ring0_stack));
    vga_print(" OK\n");

    /* IDT — point every gate at the real ISR stubs */
    vga_print("[2/6] IDT...");
    idt_init();
    /* Now patch each gate with the real stub address from ks_isr_table */
    for (int i = 0; i < 256; i++)
        idt_set_gate((uint8_t)i, ks_isr_table[i], 0, 0);
    vga_print(" OK\n");

    /* PIC remapping */
    vga_print("[3/6] PIC...");
    pic_remap();
    vga_print(" OK\n");

    /* Scheduler */
    vga_print("[4/6] Scheduler...");
    ks_scheduler_init();
    vga_print(" OK\n");

    /* PIT timer at 100Hz */
    vga_print("[5/6] PIT timer...");
    idt_set_handler(32, ks_timer_handler);  /* IRQ0 → vector 32 */
    pit_init(100);
    vga_print(" OK\n");

    /* Syscall MSR */
    vga_print("[6/6] Syscall...");
    ks_syscall_init();
    vga_print(" OK\n\n");

    /* Create demo task */
    ks_task_create("demo", demo_task, 1);

    vga_print("All subsystems online. Enabling interrupts.\n");
    vga_print("Timer ticks: ");

    /* Enable interrupts — kernel is live */
    __asm__ volatile("sti");

    /* Idle loop — scheduler takes over on timer IRQ */
    while (1) {
        __asm__ volatile("hlt");
    }
}
CEOF
    ok "Generated kmain.c"
}

# ── Clean ─────────────────────────────────────────────────────────────────────
do_clean() {
    hdr "Cleaning"
    rm -rf "${BUILD_DIR}" "${DIST_DIR}"
    rm -f "${SCRIPT_DIR}/linker_x86.ld" "${SCRIPT_DIR}/kmain.c"
    ok "Clean complete"
}

# ── Build ─────────────────────────────────────────────────────────────────────
do_build() {
    hdr "KentScript x86-64 Kernel Build"
    mkdir -p "${BUILD_DIR}" "${DIST_DIR}"

    # Generate support files if needed
    gen_linker_script && ok "Linker script ready"
    gen_kmain

    # ── Step 1: Assemble boot sector ──────────────────────────────────────
    info "Assembling boot sector..."
    nasm -f bin "${BOOT_ASM}" -o "${BUILD_DIR}/boot.bin" \
        -l "${BUILD_DIR}/boot.lst"
    BOOT_SIZE=$(wc -c < "${BUILD_DIR}/boot.bin")
    [ "$BOOT_SIZE" -ne 512 ] && err "boot.bin is ${BOOT_SIZE} bytes, expected 512"
    ok "boot.bin — ${BOOT_SIZE} bytes ✔"

    # ── Step 2: Assemble ISR stubs ────────────────────────────────────────
    info "Assembling ISR stubs..."
    gcc -c "${KERNEL_ASM_SRCS[0]}" -o "${BUILD_DIR}/ks_isr_stubs.o" \
        -ffreestanding -nostdlib
    ok "ks_isr_stubs.o"

    # ── Step 3: Compile kernel C sources ──────────────────────────────────
    KERNEL_OBJS=("${BUILD_DIR}/ks_isr_stubs.o")
    for src in "${KERNEL_SRCS[@]}"; do
        [ -f "$src" ] || { warn "Skipping missing: $(basename "$src")"; continue; }
        obj="${BUILD_DIR}/$(basename "${src%.c}").o"
        info "Compiling $(basename "$src")..."
        "${CC}" "${CFLAGS[@]}" -c "$src" -o "$obj"
        KERNEL_OBJS+=("$obj")
        ok "$(basename "$obj")"
    done

    # ── Step 4: Link kernel ELF ───────────────────────────────────────────
    info "Linking kernel ELF..."
    ld "${LDFLAGS[@]}" "${KERNEL_OBJS[@]}" -o "${OUTPUT_ELF}"
    ok "kentos_x86.elf"

    # ── Step 5: Extract flat binary ───────────────────────────────────────
    info "Extracting flat binary..."
    objcopy -O binary "${OUTPUT_ELF}" "${BUILD_DIR}/kernel.bin"
    KERN_SIZE=$(wc -c < "${BUILD_DIR}/kernel.bin")
    ok "kernel.bin — ${KERN_SIZE} bytes"

    # Pad kernel.bin to next 512-byte boundary
    PAD=$(( 512 - (KERN_SIZE % 512) ))
    [ $PAD -ne 512 ] && dd if=/dev/zero bs=1 count="$PAD" \
        >> "${BUILD_DIR}/kernel.bin" 2>/dev/null

    # ── Step 6: Combine into disk image ──────────────────────────────────
    info "Building disk image..."
    cat "${BUILD_DIR}/boot.bin" "${BUILD_DIR}/kernel.bin" > "${OUTPUT_IMG}"
    IMG_SIZE=$(wc -c < "${OUTPUT_IMG}")
    ok "kentos_x86.img — ${IMG_SIZE} bytes"

    # ── Summary ───────────────────────────────────────────────────────────
    echo ""
    echo -e "  ${BOLD}${GREEN}╔══════════════════════════════════════════╗${R}"
    echo -e "  ${BOLD}${GREEN}║   ✔  KentScript x86-64 Kernel Built      ║${R}"
    echo -e "  ${BOLD}${GREEN}╚══════════════════════════════════════════╝${R}"
    echo ""
    echo -e "  Output:  ${CYAN}${OUTPUT_IMG}${R}"
    echo -e "  ELF:     ${CYAN}${OUTPUT_ELF}${R}"
    echo -e "  Map:     ${CYAN}${OUTPUT_MAP}${R}"
    echo ""
    echo -e "  ${BOLD}Run in QEMU:${R}"
    echo -e "    ${CYAN}qemu-system-x86_64 -drive format=raw,file=${OUTPUT_IMG} -m 128M${R}"
    echo ""
    echo -e "  ${BOLD}Run with serial console:${R}"
    echo -e "    ${CYAN}qemu-system-x86_64 -drive format=raw,file=${OUTPUT_IMG} -m 128M -nographic${R}"
    echo ""
    echo -e "  ${BOLD}Write to USB (bare metal boot):${R}"
    echo -e "    ${CYAN}sudo dd if=${OUTPUT_IMG} of=/dev/sdX bs=512 conv=fsync${R}"
    echo ""
}

# ── Run ───────────────────────────────────────────────────────────────────────
do_run() {
    [ -f "${OUTPUT_IMG}" ] || do_build
    hdr "Booting KentScript x86-64 in QEMU"
    if ! command -v qemu-system-x86_64 &>/dev/null; then
        err "qemu-system-x86_64 not found. Install: sudo apt install qemu-system-x86"
    fi
    info "Press Ctrl+A X to exit QEMU"
    echo ""
    qemu-system-x86_64 \
        -drive format=raw,file="${OUTPUT_IMG}" \
        -m 128M \
        -no-reboot \
        -d int,cpu_reset 2>/dev/null \
        -monitor stdio \
        || true
}

# ── Entry point ───────────────────────────────────────────────────────────────
case "${1:-build}" in
    build)  check_tools; do_build ;;
    run)    check_tools; do_build; do_run ;;
    clean)  do_clean ;;
    *)      echo "Usage: $0 [build|run|clean]"; exit 1 ;;
esac
