/*
 * link.ld - Linker script for KentScript bare-metal kernel
 * 
 * Maps:
 *   Lower memory (0x0000 - 0x1FFFFF)  : For bootloader compatibility
 *   Kernel space (0xFFFF800000000000) : Where kernel code actually executes
 * 
 * Two-level page mapping allows GRUB to load at 0x100000,
 * but kernel executes at high virtual address.
 */

ENTRY(start_32bit)

SECTIONS {
    . = 0x100000;  /* Bootloader loads here */

    .boot BLOCK(4K) : AT(0x100000) {
        *(.multiboot)
        *(.text.boot)
    }

    .text BLOCK(4K) : {
        *(.text)
        *(.text.*)
    }

    .rodata BLOCK(4K) : {
        *(.rodata)
        *(.rodata.*)
    }

    .data BLOCK(4K) : {
        *(.data)
        *(.data.*)
    }

    .bss BLOCK(4K) : {
        bss_start = .;
        *(.bss)
        *(.bss.*)
        bss_end = .;
    }

    /DISCARD/ : {
        *(.note.GNU-stack)
        *(.gnu_debuglink)
        *(.gnu.lto_*)
    }
}
