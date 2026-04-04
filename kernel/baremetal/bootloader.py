#!/usr/bin/env python3
"""
KentScript Bare-Metal Bootloader Generator - PRODUCTION
[KS-REF-040] Complete bootloader generation for multiple architectures
[KS-REF-041] Support for x86-64, ARM64, RISC-V
[KS-REF-042] Real mode, protected mode, long mode
[KS-REF-043] UEFI, Multiboot2, U-Boot protocols

Generates bootable kernel images for bare-metal and hypervisor environments
Supports multiple boot protocols and architectures
"""

import os
import sys
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum, auto
from dataclasses import dataclass, field

# Ring-0 bridge: freestanding compile pipeline for bootloader output
try:
    from kernel_bridge import (compile_freestanding as _ring0_compile,
                                  freestanding_prologue as _ring0_prologue,
                                  capabilities, KernelCapability, capability_report)
    _RING0_BOOT = True
except ImportError:
    _RING0_BOOT = False
    _ring0_compile = None
    _ring0_prologue = None
    capability_report = lambda: "ks_ring0_bridge not available"


# ============================================================================
# ARCHITECTURE SUPPORT
# ============================================================================

class Architecture(Enum):
    """Supported architectures"""
    X86_64 = "x86_64"
    X86 = "x86"
    ARM64 = "aarch64"
    ARM32 = "arm"
    RISCV64 = "riscv64"
    RISCV32 = "riscv32"


class BootMode(Enum):
    """Boot modes"""
    REAL_MODE = "real"          # 16-bit real mode (x86 only)
    PROTECTED_MODE = "protected" # 32-bit protected mode
    LONG_MODE = "long"           # 64-bit long mode
    HYPERVISOR = "hypervisor"     # EL2/Hypervisor mode (ARM)
    SECURE_MONITOR = "secure"     # EL3/Secure monitor (ARM)


class BootProtocol(Enum):
    """Boot protocols"""
    RAW = "raw"                   # Raw binary loaded at fixed address
    MULTIBOOT = "multiboot"       # Multiboot (legacy)
    MULTIBOOT2 = "multiboot2"     # Multiboot2 (GRUB2)
    UEFI = "uefi"                 # UEFI application
    U_BOOT = "uboot"              # U-Boot image
    LINUX = "linux"               # Linux kernel format
    CHAINLOADER = "chainloader"   # Chainload from another bootloader
    PXE = "pxe"                   # PXE network boot


# ============================================================================
# BOOTLOADER CONFIGURATION
# ============================================================================

@dataclass
class BootConfig:
    """Bootloader configuration"""
    arch: Architecture = Architecture.X86_64
    mode: BootMode = BootMode.LONG_MODE
    protocol: BootProtocol = BootProtocol.RAW
    kernel_base: int = 0x100000  # 1MB default
    stack_size: int = 16384       # 16KB stack
    heap_size: int = 1048576      # 1MB heap
    video_mode: Optional[Tuple[int, int, int]] = None  # width, height, bpp
    serial: bool = False
    debug: bool = False
    smp: bool = True               # Enable SMP
    acpi: bool = True              # Use ACPI
    efi_system_table: bool = False # Pass EFI system table
    device_tree: bool = False       # Pass device tree (ARM)
    modules: List[str] = field(default_factory=list)  # Additional modules


# ============================================================================
# X86-64 BOOTLOADER
# ============================================================================

class X86BootLoader:
    """x86/x86-64 bootloader generator"""
    
    @staticmethod
    def generate_multiboot2_header() -> str:
        """Generate Multiboot2 header for GRUB2"""
        return """
; Multiboot2 header (GRUB2)
section .multiboot
align 8

mb2_header_start:
    dd 0xe85250d6                 ; Magic number
    dd 0                          ; Architecture (0 = i386)
    dd mb2_header_end - mb2_header_start ; Header length
    dd -(0xe85250d6 + 0 + (mb2_header_end - mb2_header_start)) ; Checksum

    ; Framebuffer tag (optional)
    align 8
    dw 5                          ; Type: framebuffer
    dw 1                          ; Flags: optional
    dd 20                         ; Size
    dd 1024                       ; Width
    dd 768                        ; Height
    dd 32                         ; Depth (bits per pixel)

    ; End tag
    align 8
    dw 0                          ; Type: end
    dw 0                          ; Flags
    dd 8                          ; Size
mb2_header_end:
"""
    
    @staticmethod
    def generate_real_mode_bootloader(config: BootConfig) -> str:
        """Generate 16-bit real mode bootloader"""
        return f"""; KentScript Real Mode Bootloader (x86-64)
; Generated for {config.arch.value} in {config.mode.value} mode

[BITS 16]
[ORG 0x7C00]

; ============================================================================
; REAL MODE BOOT SECTOR
; ============================================================================

start:
    cli                         ; Disable interrupts
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00              ; Stack

    ; Save boot drive
    mov [boot_drive], dl

    ; Print boot message
    mov si, boot_msg
    call print_string

    ; Load kernel from disk
    mov si, kernel_msg
    call print_string

    ; Load kernel to {hex(config.kernel_base)}
    mov ax, {config.kernel_base >> 4}
    mov es, ax
    xor bx, bx                   ; ES:BX = load address
    
    mov ah, 2                    ; Function: read sectors
    mov al, 64                   ; Number of sectors to read (32KB)
    mov ch, 0                    ; Cylinder
    mov cl, 2                    ; Sector (1-based, sector 2)
    mov dh, 0                    ; Head
    mov dl, [boot_drive]         ; Drive
    int 0x13                     ; BIOS disk interrupt
    
    jc disk_error

    ; Enable A20 line
    call enable_a20

    ; Load GDT
    lgdt [gdt_descriptor]

    ; Enable protected mode
    mov eax, cr0
    or eax, 1
    mov cr0, eax

    ; Far jump to protected mode
    jmp 0x08:protected_mode

; ============================================================================
; UTILITY FUNCTIONS
; ============================================================================

print_string:
    lodsb
    or al, al
    jz .done
    mov ah, 0x0E
    int 0x10
    jmp print_string
.done:
    ret

enable_a20:
    ; Try BIOS function first
    mov ax, 0x2401
    int 0x15
    jc .fast_gate
    ret
    
.fast_gate:
    in al, 0x92
    or al, 2
    out 0x92, al
    ret

disk_error:
    mov si, error_msg
    call print_string
    hlt
    jmp $

; ============================================================================
; DATA
; ============================================================================

boot_msg db "KentScript Booting...", 13, 10, 0
kernel_msg db "Loading kernel...", 13, 10, 0
error_msg db "Disk error!", 13, 10, 0

boot_drive db 0

; GDT (Global Descriptor Table)
align 16
gdt_start:
    ; Null descriptor
    dq 0
    
    ; Code segment (0x08) - 32-bit
    dw 0xFFFF        ; Limit 0-15
    dw 0             ; Base 0-15
    db 0             ; Base 16-23
    db 0x9A          ; Access: Present, Ring0, Code, Exec, Read
    db 0xCF          ; Granularity: 4KB, 32-bit
    db 0             ; Base 24-31
    
    ; Data segment (0x10) - 32-bit
    dw 0xFFFF        ; Limit 0-15
    dw 0             ; Base 0-15
    db 0             ; Base 16-23
    db 0x92          ; Access: Present, Ring0, Data, Read/Write
    db 0xCF          ; Granularity: 4KB, 32-bit
    db 0             ; Base 24-31
    
    ; Code segment (0x18) - 64-bit
    dw 0             ; Limit 0-15
    dw 0             ; Base 0-15
    db 0             ; Base 16-23
    db 0x9A          ; Access: Present, Ring0, Code, Exec, Read
    db 0x2F          ; Granularity: 4KB, 64-bit
    db 0             ; Base 24-31
    
    ; Data segment (0x20) - 64-bit
    dw 0             ; Limit 0-15
    dw 0             ; Base 0-15
    db 0             ; Base 16-23
    db 0x92          ; Access: Present, Ring0, Data, Read/Write
    db 0xCF          ; Granularity: 4KB, 64-bit
    db 0             ; Base 24-31
    
gdt_end:

gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start

; ============================================================================
; PROTECTED MODE
; ============================================================================

[BITS 32]
protected_mode:
    ; Set up segment registers
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    
    ; Set up stack
    mov esp, 0x90000
    
    ; Enable PAE (for 64-bit)
    mov eax, cr4
    or eax, 1 << 5
    mov cr4, eax
    
    ; Set up page tables
    call setup_paging
    
    ; Enable long mode
    mov ecx, 0xC0000080          ; EFER MSR
    rdmsr
    or eax, 1 << 8               ; Long mode enable
    wrmsr
    
    ; Enable paging
    mov eax, cr0
    or eax, 1 << 31
    mov cr0, eax
    
    ; Far jump to 64-bit code
    jmp 0x18:long_mode

; ============================================================================
; PAGING SETUP (Identity map first 2MB)
; ============================================================================

align 4096
pml4_table:
    times 512 dq 0

pdpt_table:
    times 512 dq 0

pd_table:
    times 512 dq 0

pt_table:
    %assign i 0
    %rep 512
        dq (i << 12) | 0x83      ; Present, Write, User, 2MB page
    %assign i i+1
    %endrep

setup_paging:
    ; Set up PML4
    mov eax, pdpt_table
    or eax, 0x3                  ; Present, Write
    mov [pml4_table], eax
    
    ; Set up PDPT
    mov eax, pd_table
    or eax, 0x3                  ; Present, Write
    mov [pdpt_table], eax
    
    ; Set up PD (with 2MB pages)
    mov eax, pt_table
    or eax, 0x3                  ; Present, Write
    mov [pd_table], eax
    
    ; Load PML4 address
    mov eax, pml4_table
    mov cr3, eax
    ret

; ============================================================================
; LONG MODE (64-bit)
; ============================================================================

[BITS 64]
long_mode:
    ; Set up segment registers
    mov ax, 0x20
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    
    ; Set up stack
    mov rsp, 0x90000
    
    ; Call kernel main
    extern kernel_main
    call kernel_main
    
    ; Halt if kernel returns
    cli
    hlt
    jmp $

; Padding to 512 bytes
times 510 - ($-$$) db 0
dw 0xAA55
"""
    
    @staticmethod
    def generate_uefi_application(config: BootConfig) -> str:
        """Generate UEFI application"""
        return """; KentScript UEFI Application
; Generated for x86-64 UEFI

[BITS 64]
[ORG 0]

; ============================================================================
; UEFI Entry Point
; ============================================================================

global efi_main
section .text

efi_main:
    ; UEFI passes:
    ;   rcx = ImageHandle
    ;   rdx = SystemTable
    
    push rbp
    mov rbp, rsp
    sub rsp, 32
    
    ; Store handles
    mov [image_handle], rcx
    mov [system_table], rdx
    
    ; Get ConOut from system table
    mov rax, [rdx + 64]          ; ConOut
    mov [con_out], rax
    
    ; Print boot message
    mov rcx, [rax + 8]            ; OutputString function
    mov rdx, boot_msg_utf16
    call rcx
    
    ; Call kernel main with UEFI handles
    mov rcx, [image_handle]
    mov rdx, [system_table]
    call kernel_main
    
    ; Exit boot services
    mov rcx, [image_handle]
    mov rdx, 0
    mov r8, 0
    call [efi_exit_boot_services]
    
    leave
    ret

; ============================================================================
; UEFI Exit Boot Services
; ============================================================================

efi_exit_boot_services:
    ; Stub - would call actual UEFI function
    ret

; ============================================================================
; DATA
; ============================================================================

section .data

image_handle dq 0
system_table dq 0
con_out dq 0

boot_msg_utf16:
    dw 'K','e','n','t','S','c','r','i','p','t',' ','U','E','F','I',13,10,0

; ============================================================================
; UEFI Application Header
; ============================================================================

section .uefi

align 4
    db 'UEFI'                     ; Signature
    dw 0                          ; Reserved
    dw 0                          ; Header size
    dd 0                          ; Entry point offset
    dd 0                          ; Unused
"""
    
    @staticmethod
    def generate_asm_entry(config: BootConfig, output_path: str):
        """Generate appropriate assembly entry based on config"""
        asm_code = ""
        
        # Add Multiboot2 header if requested
        if config.protocol in (BootProtocol.MULTIBOOT2, BootProtocol.MULTIBOOT):
            asm_code += X86BootLoader.generate_multiboot2_header()
            asm_code += "\n"
        
        # Generate main bootloader
        if config.protocol == BootProtocol.UEFI:
            asm_code += X86BootLoader.generate_uefi_application(config)
        else:
            asm_code += X86BootLoader.generate_real_mode_bootloader(config)
        
        with open(output_path, 'w') as f:
            f.write(asm_code)


# ============================================================================
# ARM64 BOOTLOADER
# ============================================================================

class ARM64BootLoader:
    """ARM64 bootloader generator"""
    
    @staticmethod
    def generate_u_boot_image(config: BootConfig) -> str:
        """Generate U-Boot image header"""
        return """; KentScript U-Boot Image for ARM64
; Generated for {config.arch.value}

.section .text
.globl _start
.type _start, %function

_start:
    ; U-Boot passes:
    ;   x0 = board info
    ;   x1 = device tree
    ;   x2 = (reserved)
    ;   x3 = (reserved)
    
    ; Save boot info
    mov x19, x0
    mov x20, x1
    
    ; Set up stack
    ldr x0, =stack_top
    mov sp, x0
    
    ; Clear BSS
    ldr x0, =__bss_start
    ldr x1, =__bss_end
    mov x2, xzr
    
1:  cmp x0, x1
    b.ge 2f
    str xzr, [x0], #8
    b 1b
    
2:  ; Call kernel main with boot info
    mov x0, x19
    mov x1, x20
    bl kernel_main
    
    ; Halt if kernel returns
    wfi
    b .

.section .bss
.align 16
stack_bottom:
    .space 16384
stack_top:
"""
    
    @staticmethod
    def generate_device_tree_blob(config: BootConfig) -> str:
        """Generate minimal device tree blob"""
        return """/dts-v1/;

/ {
    model = "KentScript Bare Metal";
    compatible = "kentscript,platform";
    
    #address-cells = <2>;
    #size-cells = <2>;
    
    memory@40000000 {
        device_type = "memory";
        reg = <0x0 0x40000000 0x0 0x80000000>; /* 2GB at 1GB */
    };
    
    chosen {
        stdout-path = "uart0:115200n8";
        bootargs = "console=ttyAMA0";
    };
    
    cpus {
        #address-cells = <1>;
        #size-cells = <0>;
        
        cpu@0 {
            device_type = "cpu";
            compatible = "arm,armv8";
            reg = <0x0>;
            enable-method = "spin-table";
            cpu-release-addr = <0x0 0x9000000>;
        };
    };
    
    uart0: uart@9000000 {
        compatible = "ns16550a";
        reg = <0x0 0x09000000 0x0 0x1000>;
        clock-frequency = <1843200>;
        reg-shift = <0>;
    };
    
    timer {
        compatible = "arm,armv8-timer";
        interrupts = <1 13 0xf08>,
                     <1 14 0xf08>,
                     <1 11 0xf08>,
                     <1 10 0xf08>;
    };
};
"""
    
    @staticmethod
    def generate_asm_entry(config: BootConfig, output_path: str):
        """Generate ARM64 assembly entry"""
        asm_code = ARM64BootLoader.generate_u_boot_image(config)
        
        with open(output_path, 'w') as f:
            f.write(asm_code)


# ============================================================================
# RISC-V BOOTLOADER
# ============================================================================

class RISCVBootLoader:
    """RISC-V bootloader generator"""
    
    @staticmethod
    def generate_sbi_image(config: BootConfig) -> str:
        """Generate RISC-V SBI image"""
        return """; KentScript RISC-V Bootloader
; Generated for {config.arch.value}

.section .text
.globl _start
.type _start, @function

_start:
    ; Set up stack
    la sp, _stack_top
    
    ; Clear BSS
    la a0, _bss_start
    la a1, _bss_end
    li a2, 0
    
1:  bge a0, a1, 2f
    sd a2, 0(a0)
    addi a0, a0, 8
    j 1b
    
2:  ; Set up trap handler
    la t0, trap_vector
    csrw stvec, t0
    
    ; Enable interrupts
    csrr t0, sie
    ori t0, t0, (1 << 1) | (1 << 5)  ; SSIP, STIP
    csrw sie, t0
    
    ; Call kernel main
    call kernel_main
    
    ; Halt if kernel returns
3:  wfi
    j 3b

trap_vector:
    ; Save context
    addi sp, sp, -256
    sd ra, 0(sp)
    sd x1, 8(sp)
    sd x2, 16(sp)
    sd x3, 24(sp)
    sd x4, 32(sp)
    sd x5, 40(sp)
    sd x6, 48(sp)
    sd x7, 56(sp)
    sd x8, 64(sp)
    sd x9, 72(sp)
    sd x10, 80(sp)
    sd x11, 88(sp)
    sd x12, 96(sp)
    sd x13, 104(sp)
    sd x14, 112(sp)
    sd x15, 120(sp)
    sd x16, 128(sp)
    sd x17, 136(sp)
    sd x18, 144(sp)
    sd x19, 152(sp)
    sd x20, 160(sp)
    sd x21, 168(sp)
    sd x22, 176(sp)
    sd x23, 184(sp)
    sd x24, 192(sp)
    sd x25, 200(sp)
    sd x26, 208(sp)
    sd x27, 216(sp)
    sd x28, 224(sp)
    sd x29, 232(sp)
    sd x30, 240(sp)
    sd x31, 248(sp)
    
    ; Call C handler
    call kernel_exception_handler
    
    ; Restore context
    ld ra, 0(sp)
    ld x1, 8(sp)
    ld x2, 16(sp)
    ld x3, 24(sp)
    ld x4, 32(sp)
    ld x5, 40(sp)
    ld x6, 48(sp)
    ld x7, 56(sp)
    ld x8, 64(sp)
    ld x9, 72(sp)
    ld x10, 80(sp)
    ld x11, 88(sp)
    ld x12, 96(sp)
    ld x13, 104(sp)
    ld x14, 112(sp)
    ld x15, 120(sp)
    ld x16, 128(sp)
    ld x17, 136(sp)
    ld x18, 144(sp)
    ld x19, 152(sp)
    ld x20, 160(sp)
    ld x21, 168(sp)
    ld x22, 176(sp)
    ld x23, 184(sp)
    ld x24, 192(sp)
    ld x25, 200(sp)
    ld x26, 208(sp)
    ld x27, 216(sp)
    ld x28, 224(sp)
    ld x29, 232(sp)
    ld x30, 240(sp)
    ld x31, 248(sp)
    addi sp, sp, 256
    
    sret

.section .bss
.align 16
_stack_bottom:
    .space 16384
_stack_top:
"""
    
    @staticmethod
    def generate_asm_entry(config: BootConfig, output_path: str):
        """Generate RISC-V assembly entry"""
        asm_code = RISCVBootLoader.generate_sbi_image(config)
        
        with open(output_path, 'w') as f:
            f.write(asm_code)


# ============================================================================
# LINKER SCRIPT GENERATOR
# ============================================================================

class LinkerScriptGenerator:
    """Generate linker scripts for different architectures"""
    
    @staticmethod
    def generate_x86_64_linker(config: BootConfig) -> str:
        """Generate x86-64 linker script"""
        return f"""/* KentScript x86-64 Kernel Linker Script */
OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)

PHDRS {{
    text PT_LOAD FLAGS(5);  /* PF_R | PF_X */
    data PT_LOAD FLAGS(6);  /* PF_R | PF_W */
    rodata PT_LOAD FLAGS(4); /* PF_R */
}}

SECTIONS {{
    . = {hex(config.kernel_base)};
    
    .text : ALIGN(4K) {{
        _text_start = .;
        *(.multiboot)
        *(.text)
        *(.text.*)
        _text_end = .;
    }} :text
    
    .rodata : ALIGN(4K) {{
        _rodata_start = .;
        *(.rodata)
        *(.rodata.*)
        _rodata_end = .;
    }} :rodata
    
    .data : ALIGN(4K) {{
        _data_start = .;
        *(.data)
        *(.data.*)
        _data_end = .;
    }} :data
    
    .bss : ALIGN(4K) {{
        _bss_start = .;
        *(COMMON)
        *(.bss)
        *(.bss.*)
        _bss_end = .;
    }} :data
    
    .stack : ALIGN(16) {{
        _stack_start = .;
        . += {config.stack_size};
        _stack_end = .;
        _stack_top = .;
    }} :data
    
    /DISCARD/ : {{
        *(.comment)
        *(.note)
        *(.note.*)
        *(.eh_frame)
        *(.eh_frame_hdr)
        *(.got)
        *(.got.plt)
        *(.interp)
        *(.dynsym)
        *(.dynstr)
        *(.hash)
    }}
}}
"""
    
    @staticmethod
    def generate_arm64_linker(config: BootConfig) -> str:
        """Generate ARM64 linker script"""
        return f"""/* KentScript ARM64 Kernel Linker Script */
OUTPUT_FORMAT(elf64-littleaarch64)
OUTPUT_ARCH(aarch64)
ENTRY(_start)

PHDRS {{
    text PT_LOAD FLAGS(5);  /* PF_R | PF_X */
    data PT_LOAD FLAGS(6);  /* PF_R | PF_W */
}}

SECTIONS {{
    . = {hex(config.kernel_base)};
    
    .text : ALIGN(4K) {{
        _text_start = .;
        KEEP(*(.text._start))
        *(.text)
        *(.text.*)
        _text_end = .;
    }} :text
    
    .rodata : ALIGN(4K) {{
        _rodata_start = .;
        *(.rodata)
        *(.rodata.*)
        _rodata_end = .;
    }} :text
    
    .data : ALIGN(4K) {{
        _data_start = .;
        *(.data)
        *(.data.*)
        _data_end = .;
    }} :data
    
    .bss : ALIGN(4K) {{
        _bss_start = .;
        *(COMMON)
        *(.bss)
        *(.bss.*)
        _bss_end = .;
    }} :data
    
    .stack : ALIGN(16) {{
        _stack_start = .;
        . += {config.stack_size};
        _stack_end = .;
        _stack_top = .;
    }} :data
}}
"""
    
    @staticmethod
    def generate_riscv_linker(config: BootConfig) -> str:
        """Generate RISC-V linker script"""
        return f"""/* KentScript RISC-V Kernel Linker Script */
OUTPUT_FORMAT(elf64-littleriscv)
OUTPUT_ARCH(riscv)
ENTRY(_start)

SECTIONS {{
    . = {hex(config.kernel_base)};
    
    .text : ALIGN(4K) {{
        _text_start = .;
        *(.text._start)
        *(.text)
        *(.text.*)
        _text_end = .;
    }}
    
    .rodata : ALIGN(4K) {{
        _rodata_start = .;
        *(.rodata)
        *(.rodata.*)
        _rodata_end = .;
    }}
    
    .data : ALIGN(4K) {{
        _data_start = .;
        *(.data)
        *(.data.*)
        _data_end = .;
    }}
    
    .bss : ALIGN(4K) {{
        _bss_start = .;
        *(.bss)
        *(.bss.*)
        _bss_end = .;
    }}
    
    .stack : ALIGN(16) {{
        _stack_start = .;
        . += {config.stack_size};
        _stack_end = .;
        _stack_top = .;
    }}
}}
"""
    
    @staticmethod
    def generate(config: BootConfig) -> str:
        """Generate appropriate linker script"""
        if config.arch in (Architecture.X86_64, Architecture.X86):
            return LinkerScriptGenerator.generate_x86_64_linker(config)
        elif config.arch in (Architecture.ARM64, Architecture.ARM32):
            return LinkerScriptGenerator.generate_arm64_linker(config)
        elif config.arch in (Architecture.RISCV64, Architecture.RISCV32):
            return LinkerScriptGenerator.generate_riscv_linker(config)
        else:
            return LinkerScriptGenerator.generate_x86_64_linker(config)


# ============================================================================
# KERNEL STUB GENERATOR
# ============================================================================

class KernelStubGenerator:
    """Generate minimal C kernel with platform support"""
    
    @staticmethod
    def generate_x86_kernel(config: BootConfig) -> str:
        """Generate x86 kernel stub"""
        smp_code = ""
        if config.smp:
            smp_code = """
/* SMP initialization */
void smp_init(void) {
    /* Enable APIC */
    uint32_t volatile *apic_base = (uint32_t volatile*)0xFEE00000;
    apic_base[0xF0/4] = 0x100;  /* Enable APIC with spurious vector */
    
    /* Start APs */
    for (int i = 1; i < 256; i++) {
        /* Send INIT IPI */
        apic_base[0x300/4] = (i << 24) | 0x500;
        /* Wait */
        for (volatile int j = 0; j < 10000; j++);
        /* Send STARTUP IPI */
        apic_base[0x300/4] = (i << 24) | 0x600 | (0x8000 >> 12);
    }
}
"""
        
        acpi_code = ""
        if config.acpi:
            acpi_code = """
/* ACPI table scanning */
typedef struct {
    char signature[4];
    uint32_t length;
    uint8_t revision;
    uint8_t checksum;
    char oem_id[6];
    char oem_table_id[8];
    uint32_t oem_revision;
    uint32_t creator_id;
    uint32_t creator_revision;
} __attribute__((packed)) ACPISDTHeader;

void* find_rsdp(void) {
    /* Search EBDA and BIOS area */
    uint8_t* ebda = (uint8_t*)(*(uint16_t*)0x40E << 4);
    for (int i = 0; i < 1024; i += 16) {
        if (memcmp(ebda + i, "RSD PTR ", 8) == 0)
            return ebda + i;
    }
    /* Search BIOS area */
    for (uint32_t addr = 0xE0000; addr < 0x100000; addr += 16) {
        if (memcmp((void*)addr, "RSD PTR ", 8) == 0)
            return (void*)addr;
    }
    return NULL;
}
"""
        
        return f"""/* KentScript x86-64 Kernel Stub */
#include <stdint.h>
#include <stddef.h>

/* VGA text mode */
#define VGA_BASE ((volatile uint16_t*)0xB8000)
#define VGA_WIDTH 80
#define VGA_HEIGHT 25

static int vga_row = 0;
static int vga_col = 0;
static uint8_t vga_color = 0x0F;  /* White on black */

void vga_putchar(char c) {{
    if (c == '\\n') {{
        vga_col = 0;
        vga_row++;
        if (vga_row >= VGA_HEIGHT) vga_row = 0;
        return;
    }}
    if (vga_col >= VGA_WIDTH) {{
        vga_col = 0;
        vga_row++;
    }}
    const size_t index = vga_row * VGA_WIDTH + vga_col;
    VGA_BASE[index] = (uint16_t)c | (uint16_t)vga_color << 8;
    vga_col++;
}}

void vga_print(const char* str) {{
    while (*str) vga_putchar(*str++);
}}

void vga_print_hex(uint64_t value) {{
    const char* hex = "0123456789ABCDEF";
    vga_putchar('0');
    vga_putchar('x');
    for (int i = 60; i >= 0; i -= 4) {{
        vga_putchar(hex[(value >> i) & 0xF]);
    }}
}}

/* Memory operations */
void* memcpy(void* dest, const void* src, size_t n) {{
    uint8_t* d = (uint8_t*)dest;
    const uint8_t* s = (const uint8_t*)src;
    while (n--) *d++ = *s++;
    return dest;
}}

void* memset(void* s, int c, size_t n) {{
    uint8_t* p = (uint8_t*)s;
    while (n--) *p++ = (uint8_t)c;
    return s;
}}

int memcmp(const void* s1, const void* s2, size_t n) {{
    const uint8_t* p1 = (const uint8_t*)s1;
    const uint8_t* p2 = (const uint8_t*)s2;
    while (n--) {{
        if (*p1 != *p2) return *p1 - *p2;
        p1++; p2++;
    }}
    return 0;
}}

{smp_code}

{acpi_code}

/* Interrupt handlers */
void isr_handler(int irq) {{
    vga_print("IRQ: ");
    vga_print_hex(irq);
    vga_putchar('\\n');
}}

/* Page fault handler */
void page_fault_handler(void* addr) {{
    vga_print("Page fault at ");
    vga_print_hex((uint64_t)addr);
    vga_putchar('\\n');
    while(1);
}}

/* Main kernel entry */
void kernel_main(void) {{
    vga_print("KentScript x86-64 Kernel Started\\n");
    vga_print("Boot address: ");
    vga_print_hex((uint64_t)0x{hex(config.kernel_base)});
    vga_putchar('\\n');
    
    {smp_code}
    /* SMP and ACPI initialization done above */
    
    /* Test memory */
    uint8_t test_buffer[64];
    memset(test_buffer, 0xAA, 64);
    vga_print("Memory test: ");
    vga_print_hex(test_buffer[0]);
    vga_putchar('\\n');
    
    /* Main loop */
    while(1) {{
        __asm__ volatile("hlt");
    }}
}}

/* Entry point */
void _start(void) {{
    kernel_main();
}}
"""
    
    @staticmethod
    def generate(config: BootConfig) -> str:
        """Generate appropriate kernel stub"""
        if config.arch in (Architecture.X86_64, Architecture.X86):
            return KernelStubGenerator.generate_x86_kernel(config)
        # Add ARM64 and RISC-V generators here
        return KernelStubGenerator.generate_x86_kernel(config)


# ============================================================================
# MAKEFILE GENERATOR
# ============================================================================

class MakefileGenerator:
    """Generate build system for different platforms"""
    
    @staticmethod
    def generate(config: BootConfig) -> str:
        """Generate appropriate Makefile"""
        asm_ext = "S" if config.arch in (Architecture.ARM64, Architecture.RISCV64) else "asm"
        asm_flags = {
            Architecture.X86_64: "-f elf64",
            Architecture.X86: "-f elf32",
            Architecture.ARM64: "",
            Architecture.RISCV64: "",
        }.get(config.arch, "")
        
        cc_flags = f"-ffreestanding -nostdlib -nostartfiles -m{'64' if config.arch in (Architecture.X86_64, Architecture.ARM64, Architecture.RISCV64) else '32'} -O2 -Wall"
        
        return f"""# KentScript Kernel Makefile
# Generated for {config.arch.value} with {config.protocol.value} boot protocol

AS = {"nasm" if config.arch in (Architecture.X86_64, Architecture.X86) else "as"}
CC = {"gcc" if config.arch in (Architecture.X86_64, Architecture.X86, Architecture.ARM64) else "riscv64-unknown-elf-gcc"}
LD = {"ld" if config.arch in (Architecture.X86_64, Architecture.X86) else "riscv64-unknown-elf-ld"}
OBJCOPY = objcopy

ASFLAGS = {asm_flags}
CCFLAGS = {cc_flags}
LDFLAGS = -T kernel.ld -nostdlib

.PHONY: all clean run iso

all: kernel.bin

boot.o: boot.{asm_ext}
	$(AS) $(ASFLAGS) boot.{asm_ext} -o boot.o

kernel.o: kernel.c
	$(CC) $(CCFLAGS) -c kernel.c -o kernel.o

kernel.elf: boot.o kernel.o
	$(LD) $(LDFLAGS) boot.o kernel.o -o kernel.elf

kernel.bin: kernel.elf
	$(OBJCOPY) -O binary kernel.elf kernel.bin

run: kernel.bin
{"\tqemu-system-x86_64 -drive format=raw,file=kernel.bin" if config.arch == Architecture.X86_64 else "\tqemu-system-aarch64 -M virt -cpu cortex-a53 -kernel kernel.elf -nographic"}

clean:
	rm -f *.o *.elf *.bin

iso: kernel.bin
	mkdir -p iso/boot/grub
	cp kernel.bin iso/boot/
	echo 'menuentry "MiniOS" {{ {"multiboot2" if config.protocol == BootProtocol.MULTIBOOT2 else "multiboot"} /boot/kernel.bin }}' > iso/boot/grub/grub.cfg
	grub-mkrescue iso/ -o kentOS.iso

debug: kernel.elf
{"\tqemu-system-x86_64 -s -S -kernel kernel.elf" if config.arch == Architecture.X86_64 else "\tqemu-system-aarch64 -s -S -M virt -cpu cortex-a53 -kernel kernel.elf"}
"""
    
    @staticmethod
    def generate_cross_makefile(config: BootConfig) -> str:
        """Generate cross-compilation Makefile"""
        return f"""# KentScript Cross-Compilation Makefile

ARCH = {config.arch.value}
CROSS_COMPILE = {{
    "x86_64": "x86_64-linux-gnu-",
    "aarch64": "aarch64-linux-gnu-",
    "arm": "arm-linux-gnueabihf-",
    "riscv64": "riscv64-linux-gnu-",
}}[$ARCH]

CC = $(CROSS_COMPILE)gcc
AS = $(CROSS_COMPILE)as
LD = $(CROSS_COMPILE)ld
OBJCOPY = $(CROSS_COMPILE)objcopy

ASFLAGS = {{
    "x86_64": "-f elf64",
    "aarch64": "",
    "riscv64": "",
}}[$ARCH]

CFLAGS = -ffreestanding -nostdlib -nostartfiles -O2 -Wall
LDFLAGS = -T kernel.ld -nostdlib

.PHONY: all clean

all: kernel.elf

kernel.elf: kernel.c
	$(CC) $(CFLAGS) -c kernel.c -o kernel.o
	$(LD) $(LDFLAGS) kernel.o -o kernel.elf
"""


# ============================================================================
# MAIN BOOTLOADER GENERATOR
# ============================================================================

class BootLoader:
    """Complete bootloader generator for multiple architectures"""
    
    def __init__(self, config: Optional[BootConfig] = None):
        self.config = config or BootConfig()
    
    def generate_bootloader(self, output_path: str = "boot.asm"):
        """Generate bootloader assembly"""
        if self.config.arch in (Architecture.X86_64, Architecture.X86):
            X86BootLoader.generate_asm_entry(self.config, output_path)
        elif self.config.arch in (Architecture.ARM64, Architecture.ARM32):
            ARM64BootLoader.generate_asm_entry(self.config, output_path)
        elif self.config.arch in (Architecture.RISCV64, Architecture.RISCV32):
            RISCVBootLoader.generate_asm_entry(self.config, output_path)
        else:
            X86BootLoader.generate_asm_entry(self.config, output_path)
        
        print(f"[KS-BOOTLOADER] Generated: {output_path}")
        return output_path
    
    def generate_linker_script(self, output_path: str = "kernel.ld"):
        """Generate linker script"""
        script = LinkerScriptGenerator.generate(self.config)
        with open(output_path, 'w') as f:
            f.write(script)
        print(f"[KS-BOOTLOADER] Generated: {output_path}")
        return output_path
    
    def generate_kernel_stub(self, output_path: str = "kernel.c"):
        """Generate minimal C kernel"""
        kernel_code = KernelStubGenerator.generate(self.config)
        with open(output_path, 'w') as f:
            f.write(kernel_code)
        print(f"[KS-BOOTLOADER] Generated: {output_path}")
        return output_path
    
    def generate_makefile(self, output_path: str = "Makefile"):
        """Generate Makefile"""
        makefile = MakefileGenerator.generate(self.config)
        with open(output_path, 'w') as f:
            f.write(makefile)
        print(f"[KS-BOOTLOADER] Generated: {output_path}")
        return output_path
    
    def generate_device_tree(self, output_path: str = "kernel.dts"):
        """Generate device tree blob for ARM"""
        if self.config.arch in (Architecture.ARM64, Architecture.ARM32):
            dts = ARM64BootLoader.generate_device_tree_blob(self.config)
            with open(output_path, 'w') as f:
                f.write(dts)
            print(f"[KS-BOOTLOADER] Generated: {output_path}")
            return output_path
        return None
    
    def generate_all(self, output_dir: str = "."):
        """Generate complete bootloader package"""
        os.makedirs(output_dir, exist_ok=True)
        cwd = os.getcwd()
        os.chdir(output_dir)
        
        try:
            self.generate_bootloader("boot.asm")
            self.generate_linker_script("kernel.ld")
            self.generate_kernel_stub("kernel.c")
            self.generate_makefile("Makefile")
            self.generate_device_tree("kernel.dts")
            
            print(f"\n[KS-BOOTLOADER] Complete bare-metal kernel package generated")
            print(f"[KS-BOOTLOADER] Target: {self.config.arch.value}")
            print(f"[KS-BOOTLOADER] Mode: {self.config.mode.value}")
            print(f"[KS-BOOTLOADER] Protocol: {self.config.protocol.value}")
            print(f"[KS-BOOTLOADER] Kernel base: 0x{self.config.kernel_base:x}")
            print(f"\n[KS-BOOTLOADER] Build with: make")
            print(f"[KS-BOOTLOADER] Run with: make run")
            
        finally:
            os.chdir(cwd)
    
    def build(self, output_dir: str = ".", compiler: str = "gcc"):
        """Build the kernel"""
        self.generate_all(output_dir)
        
        os.chdir(output_dir)
        try:
            # Run make
            result = subprocess.run(['make'], capture_output=True, text=True)
            if result.returncode == 0:
                print("[KS-BOOTLOADER] Build successful")
                return True
            else:
                print(f"[KS-BOOTLOADER] Build failed: {result.stderr}")
                return False
        finally:
            os.chdir("..")

    def compile_kernel_ring0(self, kernel_c_source: str, output: str,
                             extra_flags: list = None) -> bool:
        """
        Compile a kernel C source to a freestanding binary using the ring-0 bridge.
        Automatically injects the ks_ring0.h prologue and bare-metal compiler flags.
        Returns True on success.
        """
        if not _RING0_BOOT or _ring0_compile is None:
            raise RuntimeError("ks_ring0_bridge not available — cannot compile freestanding")

        # Prepend ring-0 prologue (ks_ring0.h + barriers + syscall macros)
        prologue = _ring0_prologue(target_arch=self.config.arch.value)
        full_source = prologue + "\n\n" + kernel_c_source

        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as f:
            f.write(full_source)
            src_path = f.name

        try:
            ok = _ring0_compile(src_path, output,
                                arch=self.config.arch.value,
                                extra_flags=extra_flags)
            if ok:
                print(f"[KS-BOOTLOADER] ring-0 kernel compiled → {output}")
            return ok
        finally:
            os.unlink(src_path)

    def ring0_capability_report(self) -> str:
        """Return ring-0 capability report for this system."""
        return capability_report()


# ============================================================================
# GDT/IDT UTILITIES (for x86)
# ============================================================================

class ProtectedMode:
    """Protected mode setup utilities"""
    
    @staticmethod
    def generate_idt_code(output_path: str = "idt.c", config: Optional[BootConfig] = None):
        """Generate IDT initialization code"""
        idt_code = """/* KentScript IDT Setup for x86-64 */
#include <stdint.h>

typedef struct {
    uint16_t offset_low;
    uint16_t selector;
    uint8_t ist;
    uint8_t type_attr;
    uint16_t offset_mid;
    uint32_t offset_high;
    uint32_t reserved;
} __attribute__((packed)) IDT_Entry;

typedef struct {
    uint16_t limit;
    uint64_t base;
} __attribute__((packed)) IDT_Pointer;

IDT_Entry idt[256] __attribute__((aligned(16)));

/* External interrupt handlers */
extern void isr0(void);   /* Division by zero */
extern void isr1(void);   /* Debug */
extern void isr2(void);   /* NMI */
extern void isr3(void);   /* Breakpoint */
extern void isr4(void);   /* Overflow */
extern void isr5(void);   /* Bound range */
extern void isr6(void);   /* Invalid opcode */
extern void isr7(void);   /* Device not available */
extern void isr8(void);   /* Double fault */
extern void isr13(void);  /* General protection */
extern void isr14(void);  /* Page fault */

void set_idt_entry(int index, uint64_t handler, uint8_t type) {
    idt[index].offset_low = handler & 0xFFFF;
    idt[index].selector = 0x08;  /* Kernel code segment */
    idt[index].ist = 0;
    idt[index].type_attr = type;
    idt[index].offset_mid = (handler >> 16) & 0xFFFF;
    idt[index].offset_high = (handler >> 32) & 0xFFFFFFFF;
    idt[index].reserved = 0;
}

void init_idt(void) {
    /* Initialize all entries to zero */
    for (int i = 0; i < 256; i++) {
        idt[i].offset_low = 0;
        idt[i].selector = 0;
        idt[i].ist = 0;
        idt[i].type_attr = 0;
        idt[i].offset_mid = 0;
        idt[i].offset_high = 0;
        idt[i].reserved = 0;
    }
    
    /* Set up exception handlers */
    set_idt_entry(0, (uint64_t)isr0, 0x8E);   /* Interrupt gate */
    set_idt_entry(1, (uint64_t)isr1, 0x8E);
    set_idt_entry(2, (uint64_t)isr2, 0x8E);
    set_idt_entry(3, (uint64_t)isr3, 0xEE);   /* User mode accessible */
    set_idt_entry(4, (uint64_t)isr4, 0x8E);
    set_idt_entry(5, (uint64_t)isr5, 0x8E);
    set_idt_entry(6, (uint64_t)isr6, 0x8E);
    set_idt_entry(7, (uint64_t)isr7, 0x8E);
    set_idt_entry(8, (uint64_t)isr8, 0x8E);
    set_idt_entry(13, (uint64_t)isr13, 0x8E);
    set_idt_entry(14, (uint64_t)isr14, 0x8E);
    
    /* Load IDT */
    IDT_Pointer idtp;
    idtp.limit = sizeof(idt) - 1;
    idtp.base = (uint64_t)&idt;
    
    __asm__ volatile("lidt %0" : : "m"(idtp));
    __asm__ volatile("sti");  /* Enable interrupts */
}

/* Interrupt handler stub */
void isr_handler(int irq) {
    /* Handle interrupt */
}
"""
        with open(output_path, 'w') as f:
            f.write(idt_code)
        print(f"[KS-BOOTLOADER] Generated: {output_path}")
        return output_path


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

def main():
    """Command-line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="KentScript Bare-Metal Bootloader Generator")
    parser.add_argument("--arch", choices=['x86_64', 'x86', 'aarch64', 'arm64', 'riscv64'],
                       default='x86_64', help="Target architecture")
    parser.add_argument("--mode", choices=['real', 'protected', 'long', 'hypervisor', 'secure'],
                       default='long', help="Boot mode")
    parser.add_argument("--protocol", choices=['raw', 'multiboot', 'multiboot2', 'uefi', 'uboot'],
                       default='raw', help="Boot protocol")
    parser.add_argument("--base", type=lambda x: int(x, 0), default=0x100000,
                       help="Kernel base address (hex)")
    parser.add_argument("--output", "-o", default=".", help="Output directory")
    parser.add_argument("--build", action="store_true", help="Build after generating")
    
    args = parser.parse_args()
    
    # Map architecture
    arch_map = {
        'x86_64': Architecture.X86_64,
        'x86': Architecture.X86,
        'aarch64': Architecture.ARM64,
        'arm64': Architecture.ARM64,
        'riscv64': Architecture.RISCV64,
    }
    
    mode_map = {
        'real': BootMode.REAL_MODE,
        'protected': BootMode.PROTECTED_MODE,
        'long': BootMode.LONG_MODE,
        'hypervisor': BootMode.HYPERVISOR,
        'secure': BootMode.SECURE_MONITOR,
    }
    
    protocol_map = {
        'raw': BootProtocol.RAW,
        'multiboot': BootProtocol.MULTIBOOT,
        'multiboot2': BootProtocol.MULTIBOOT2,
        'uefi': BootProtocol.UEFI,
        'uboot': BootProtocol.U_BOOT,
    }
    
    config = BootConfig(
        arch=arch_map[args.arch],
        mode=mode_map[args.mode],
        protocol=protocol_map[args.protocol],
        kernel_base=args.base
    )
    
    bootloader = BootLoader(config)
    
    if args.build:
        bootloader.build(args.output)
    else:
        bootloader.generate_all(args.output)
    
    print("\n[KS-BOOTLOADER] ✓ Bootloader generation complete!")


if __name__ == "__main__":
    main()
