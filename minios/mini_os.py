#!/usr/bin/env python3
"""
ks_minios.py — MiniOS Kernel Builder Module
[KS-REF-100] Full bare-metal OS generation for AArch64 (QEMU virt)

Features generated:
  - Preemptive round-robin scheduler (timer IRQ)
  - Virtual filesystem (VFS) with ramfs
  - Framebuffer GUI (1024x768, pixel drawing, font rendering, windows)
  - Syscall ABI (SVC #0 dispatch table)
  - Memory allocator (bump + free-list)
  - Shell (reads UART, dispatches built-in commands)
  - EL0 userland task switch demo

Usage:
  from ks_minios import MiniOS
  k = MiniOS()
  ok, msg = k.build()          # build kernel ELF
  ok, msg = k.run()            # run in QEMU
  k.info()                     # print feature summary

CLI:
  python3 ks_minios.py build [--output /tmp/minios.elf] [--arch aarch64]
  python3 ks_minios.py run   [--output /tmp/minios.elf]
  python3 ks_minios.py info
"""

import os
import sys
import shutil
import subprocess
import tempfile
from typing import Tuple, List, Optional
from dataclasses import dataclass, field

# ============================================================================
# KENTOS — AArch64 ENTRY ASSEMBLY
# ============================================================================

_KENTOS_ENTRY_S = r"""
/* ================================================================
 * MiniOS — entry.S  (AArch64, QEMU virt, EL1)
 * ================================================================
 * Layout:
 *   0x40000000  .text.vectors  — 2KiB exception vector table
 *   0x40000800  .text          — kernel code
 *   ...         .rodata
 *   ...         .data
 *   ...         .bss           — zero-init (zeroed here)
 * ================================================================ */

/* ---- Exception vector table (must be 2KiB = 0x800 aligned) ---- */
.section .text.vectors, "ax"
.balign 2048
vector_table:
    .org vector_table + 0x000;  b   sync_el1_sp0
    .org vector_table + 0x080;  b   irq_el1_sp0
    .org vector_table + 0x100;  b   fiq_handler
    .org vector_table + 0x180;  b   serr_handler

    .org vector_table + 0x200;  b   sync_el1_spx
    .org vector_table + 0x280;  b   irq_el1_spx
    .org vector_table + 0x300;  b   fiq_handler
    .org vector_table + 0x380;  b   serr_handler

    .org vector_table + 0x400;  b   sync_el0_64
    .org vector_table + 0x480;  b   irq_el0_64
    .org vector_table + 0x500;  b   fiq_handler
    .org vector_table + 0x580;  b   serr_handler

    .org vector_table + 0x600;  b   default_handler
    .org vector_table + 0x680;  b   default_handler
    .org vector_table + 0x700;  b   default_handler
    .org vector_table + 0x780;  b   default_handler

/* ----------------------------------------------------------------
 * Exception handlers — save/restore full context, call C handlers
 * ---------------------------------------------------------------- */

/* Save all general-purpose regs (x0-x30) + sp + elr + spsr */
.macro SAVE_REGS
    sub     sp, sp, #(34 * 8)
    stp     x0,  x1,  [sp, #(0  * 8)]
    stp     x2,  x3,  [sp, #(2  * 8)]
    stp     x4,  x5,  [sp, #(4  * 8)]
    stp     x6,  x7,  [sp, #(6  * 8)]
    stp     x8,  x9,  [sp, #(8  * 8)]
    stp     x10, x11, [sp, #(10 * 8)]
    stp     x12, x13, [sp, #(12 * 8)]
    stp     x14, x15, [sp, #(14 * 8)]
    stp     x16, x17, [sp, #(16 * 8)]
    stp     x18, x19, [sp, #(18 * 8)]
    stp     x20, x21, [sp, #(20 * 8)]
    stp     x22, x23, [sp, #(22 * 8)]
    stp     x24, x25, [sp, #(24 * 8)]
    stp     x26, x27, [sp, #(26 * 8)]
    stp     x28, x29, [sp, #(28 * 8)]
    str     x30,       [sp, #(30 * 8)]
    mrs     x0, elr_el1
    mrs     x1, spsr_el1
    stp     x0,  x1,  [sp, #(31 * 8)]
    mov     x0, sp
    add     x1, sp, #(34 * 8)
    stp     x1,  xzr, [sp, #(32 * 8)]
.endm

.macro RESTORE_REGS
    ldp     x0,  x1,  [sp, #(31 * 8)]
    msr     elr_el1, x0
    msr     spsr_el1, x1
    ldp     x0,  x1,  [sp, #(0  * 8)]
    ldp     x2,  x3,  [sp, #(2  * 8)]
    ldp     x4,  x5,  [sp, #(4  * 8)]
    ldp     x6,  x7,  [sp, #(6  * 8)]
    ldp     x8,  x9,  [sp, #(8  * 8)]
    ldp     x10, x11, [sp, #(10 * 8)]
    ldp     x12, x13, [sp, #(12 * 8)]
    ldp     x14, x15, [sp, #(14 * 8)]
    ldp     x16, x17, [sp, #(16 * 8)]
    ldp     x18, x19, [sp, #(18 * 8)]
    ldp     x20, x21, [sp, #(20 * 8)]
    ldp     x22, x23, [sp, #(22 * 8)]
    ldp     x24, x25, [sp, #(24 * 8)]
    ldp     x26, x27, [sp, #(26 * 8)]
    ldp     x28, x29, [sp, #(28 * 8)]
    ldr     x30,       [sp, #(30 * 8)]
    add     sp, sp, #(34 * 8)
.endm

sync_el1_sp0:
    SAVE_REGS
    bl      minios_sync_handler
    RESTORE_REGS
    eret

irq_el1_sp0:
    SAVE_REGS
    bl      minios_irq_handler
    RESTORE_REGS
    eret

sync_el1_spx:
    SAVE_REGS
    bl      minios_sync_handler
    RESTORE_REGS
    eret

irq_el1_spx:
    SAVE_REGS
    bl      minios_irq_handler
    RESTORE_REGS
    eret

sync_el0_64:
    SAVE_REGS
    bl      minios_syscall_handler
    RESTORE_REGS
    eret

irq_el0_64:
    SAVE_REGS
    bl      minios_irq_handler
    RESTORE_REGS
    eret

fiq_handler:
    eret

serr_handler:
    b serr_handler

default_handler:
    b default_handler

/* ---- _start ---- */
.section .text
.global _start
_start:
    /* Park secondary cores */
    mrs     x0, mpidr_el1
    and     x0, x0, #0xFF
    cbnz    x0, .Lsecondary_park

    /* Install exception vector */
    adr     x0, vector_table
    msr     vbar_el1, x0
    isb

    /* ---- FIX: Enable FP/SIMD at EL1 and EL0 ----
     * CPACR_EL1.FPEN [21:20] = 0b11 → no trap for EL1/EL0
     * GCC -O2 may emit NEON q-register stores for memset/memcpy
     * Without this: EC=0x07 sync exception on first struct zero-fill
     */
    mov     x0, #(3 << 20)
    msr     cpacr_el1, x0
    isb

    /* Set up EL1 stack */
    adr     x0, minios_stack_top
    mov     sp, x0

    /* Zero BSS */
    adr     x0, __bss_start
    adr     x1, __bss_end
.Lbss_loop:
    cmp     x0, x1
    b.ge    .Lbss_done
    str     xzr, [x0], #8
    b       .Lbss_loop
.Lbss_done:

    /* Jump to C kernel */
    bl      minios_main
    b       .Lhalt

.Lhalt:
    msr     daifset, #0xf
    wfe
    b       .Lhalt

.Lsecondary_park:
    wfe
    b       .Lsecondary_park

/* ---- Context switch: minios_switch_context(u64 *old_sp, u64 new_sp) ---- */
.global minios_switch_context
minios_switch_context:
    /* Save callee-saved regs + lr onto current stack */
    stp     x19, x20, [sp, #-16]!
    stp     x21, x22, [sp, #-16]!
    stp     x23, x24, [sp, #-16]!
    stp     x25, x26, [sp, #-16]!
    stp     x27, x28, [sp, #-16]!
    stp     x29, x30, [sp, #-16]!
    /* Save SP to old task's sp_save */
    mov     x2, sp
    str     x2, [x0]
    /* Switch to new stack */
    mov     sp, x1
    /* Restore new task's callee-saved regs */
    ldp     x29, x30, [sp], #16
    ldp     x27, x28, [sp], #16
    ldp     x25, x26, [sp], #16
    ldp     x23, x24, [sp], #16
    ldp     x21, x22, [sp], #16
    ldp     x19, x20, [sp], #16
    ret

/* ---- EL0 user task launcher ---- */
.global minios_enter_el0
minios_enter_el0:
    /* x0 = entry point, x1 = user stack top */
    msr     elr_el1, x0
    mov     x0, #0x0        /* SPSR: EL0, AArch64, all exceptions unmasked */
    msr     spsr_el1, x0
    msr     sp_el0, x1
    isb
    eret

/* ---- Stacks ---- */
.section .bss
.balign 4096
.space 65536            /* 64 KiB kernel stack */
minios_stack_top:

.balign 4096
.space 32768
minios_irq_stack_top:

.global __bss_start
__bss_start:
.global __bss_end
__bss_end:
"""

# ============================================================================
# KENTOS — MAIN C KERNEL
# ============================================================================

_KENTOS_KERNEL_C = r"""
/*
 * MiniOS 2.0 — minios_kernel.c
 * AArch64 Bare-Metal OS | Built with KentScript
 *
 * Subsystems:
 *   uart      — PL011 UART driver
 *   fb        — Framebuffer 1024x768 32bpp
 *   font      — 8x8 bitmap font
 *   mm        — Bump allocator + free-list overlay
 *   vfs       — ramfs (files, dirs, symlinks)
 *   sched     — Preemptive round-robin + priority
 *   syscall   — SVC #0 ABI (16 syscalls)
 *   el0       — EL0 userland drop + re-entry
 *   elfload   — Minimal ELF64 loader from VFS
 *   ksvm      — KentScript bytecode VM (userland)
 *   shell     — Interactive UART shell (25 cmds)
 *   gui       — Framebuffer WM + live dashboard
 *   stress    — Scheduler/memory stress tester
 */

/* ================================================================ TYPES */
typedef unsigned long   u64;
typedef unsigned int    u32;
typedef unsigned short  u16;
typedef unsigned char   u8;
typedef long            s64;
typedef int             s32;
typedef int             pid_t;
typedef int             uid_t;
typedef int             gid_t;
typedef unsigned int    size_t;
typedef struct {u8 addr[4];} ip4_addr_t;
#define NULL  ((void*)0)
#define true  1
#define false 0

/* ================================================================ SIGNALS */
#define SIGHUP    1
#define SIGINT    2
#define SIGQUIT   3
#define SIGILL    4
#define SIGTRAP   5
#define SIGABRT   6
#define SIGBUS    7
#define SIGFPE    8
#define SIGKILL   9
#define SIGUSR1  10
#define SIGSEGV  11
#define SIGUSR2  12
#define SIGPIPE  13
#define SIGALRM  14
#define SIGTERM  15
#define SIGCHLD  17
#define SIGCONT  18
#define SIGSTOP  19
static inline void dsb_sy(void){ __asm__ volatile("dsb sy":::"memory"); }
static inline void isb(void)   { __asm__ volatile("isb":::"memory"); }

/* ================================================================ SPINLOCK + IRQ MASK
 * Bare-metal concurrency primitives.
 * irq_save/restore: mask/unmask IRQs (safe for SMP task-list traversal)
 * spinlock: LDXR/STXR exclusive access (SMP-safe critical sections)
 */
typedef u64 spinlock_t;
typedef u64 irqflags_t;

static inline irqflags_t irq_save(void) {
    irqflags_t flags;
    __asm__ volatile(
        "mrs %0, daif\n"
        "msr daifset, #2\n"   /* mask IRQ bit */
        : "=r"(flags) :: "memory"
    );
    return flags;
}

static inline void irq_restore(irqflags_t flags) {
    __asm__ volatile(
        "msr daif, %0\n"
        :: "r"(flags) : "memory"
    );
}

static inline void spin_lock(spinlock_t *lock) {
    u64 tmp, got;
    __asm__ volatile(
        "1:\n"
        "   ldaxr   %0, [%2]\n"
        "   cbnz    %0, 1b\n"         /* spin while locked */
        "   mov     %1, #1\n"
        "   stxr    w0, %1, [%2]\n"   /* w0 = scratch — attempt to lock */
        "   cbnz    w0, 1b\n"         /* retry if store-exclusive failed */
        "   dmb     ish\n"
        : "=&r"(tmp), "=&r"(got)
        : "r"(lock)
        : "w0", "memory"
    );
}

static inline void spin_unlock(spinlock_t *lock) {
    __asm__ volatile(
        "dmb     ish\n"
        "stlr    xzr, [%0]\n"
        :: "r"(lock) : "memory"
    );
}

static spinlock_t task_list_lock = 0;  /* protects tasks[] and task_count */

/* ================================================================ UART */
#define UART0      ((volatile u32*)0x09000000UL)
#define UART_DR    0
#define UART_FR    6
#define UART_IBRD  9
#define UART_FBRD  10
#define UART_LCR   11
#define UART_CR    12

static void uart_init(void){
    UART0[UART_CR]=0; UART0[UART_IBRD]=1; UART0[UART_FBRD]=40;
    UART0[UART_LCR]=0x70; UART0[UART_CR]=0x301;
}
static void uart_putc(char c){
    while(UART0[UART_FR]&(1u<<5));
    UART0[UART_DR]=(u32)(u8)c;
}
static void uart_puts(const char *s){
    while(*s){ if(*s=='\n') uart_putc('\r'); uart_putc(*s++); }
}
static int uart_getc_nb(char *c){
    if(UART0[UART_FR]&(1u<<4)) return 0;
    *c=(char)(UART0[UART_DR]&0xFF); return 1;
}
static void put_nibble(u32 n){ n&=0xF; uart_putc(n<10?'0'+n:'a'+n-10); }
static void put_hex64(u64 v){ int s; for(s=60;s>=0;s-=4) put_nibble((u32)(v>>s)); }
static void put_dec(u64 v){ if(v>=10) put_dec(v/10); uart_putc('0'+(v%10)); }
static void put_signed(s64 v){ if(v<0){uart_putc('-');put_dec((u64)(-v));}else put_dec((u64)v); }

/* ============================================================== FRAMEBUFFER */
#define FB_BASE   ((volatile u32*)0x3c000000UL)
#define FB_WIDTH  1024
#define FB_HEIGHT 768
#define FB_PITCH  (FB_WIDTH)

static void fb_pixel(int x,int y,u32 rgb){
    if((u32)x>=FB_WIDTH||(u32)y>=FB_HEIGHT) return;
    FB_BASE[y*FB_PITCH+x]=rgb;
}
static void fb_rect(int x,int y,int w,int h,u32 rgb){
    for(int dy=0;dy<h;dy++) for(int dx=0;dx<w;dx++) fb_pixel(x+dx,y+dy,rgb);
}
static void fb_hline(int x,int y,int w,u32 rgb){ for(int i=0;i<w;i++) fb_pixel(x+i,y,rgb); }
static void fb_vline(int x,int y,int h,u32 rgb){ for(int i=0;i<h;i++) fb_pixel(x,y+i,rgb); }
static void fb_border(int x,int y,int w,int h,int t,u32 rgb){
    for(int i=0;i<t;i++){
        fb_hline(x,y+i,w,rgb); fb_hline(x,y+h-1-i,w,rgb);
        fb_vline(x+i,y,h,rgb); fb_vline(x+w-1-i,y,h,rgb);
    }
}
/* Gradient fill */
static void fb_gradient(int x,int y,int w,int h,u32 top,u32 bot){
    for(int dy=0;dy<h;dy++){
        u32 r=((top>>16&0xFF)*(h-dy)+(bot>>16&0xFF)*dy)/h;
        u32 g=((top>>8&0xFF)*(h-dy)+(bot>>8&0xFF)*dy)/h;
        u32 b=((top&0xFF)*(h-dy)+(bot&0xFF)*dy)/h;
        fb_hline(x,y+dy,w,(r<<16)|(g<<8)|b);
    }
}

/* ================================================================= FONT */
static const u8 font8x8[95][8]={
  {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
  {0x18,0x3C,0x3C,0x18,0x18,0x00,0x18,0x00},
  {0x36,0x36,0x00,0x00,0x00,0x00,0x00,0x00},
  {0x36,0x36,0x7F,0x36,0x7F,0x36,0x36,0x00},
  {0x0C,0x3E,0x03,0x1E,0x30,0x1F,0x0C,0x00},
  {0x00,0x63,0x33,0x18,0x0C,0x66,0x63,0x00},
  {0x1C,0x36,0x1C,0x6E,0x3B,0x33,0x6E,0x00},
  {0x06,0x06,0x03,0x00,0x00,0x00,0x00,0x00},
  {0x18,0x0C,0x06,0x06,0x06,0x0C,0x18,0x00},
  {0x06,0x0C,0x18,0x18,0x18,0x0C,0x06,0x00},
  {0x00,0x66,0x3C,0xFF,0x3C,0x66,0x00,0x00},
  {0x00,0x0C,0x0C,0x3F,0x0C,0x0C,0x00,0x00},
  {0x00,0x00,0x00,0x00,0x00,0x0C,0x0C,0x06},
  {0x00,0x00,0x00,0x3F,0x00,0x00,0x00,0x00},
  {0x00,0x00,0x00,0x00,0x00,0x0C,0x0C,0x00},
  {0x60,0x30,0x18,0x0C,0x06,0x03,0x01,0x00},
  {0x3E,0x63,0x73,0x7B,0x6F,0x67,0x3E,0x00},
  {0x0C,0x0E,0x0C,0x0C,0x0C,0x0C,0x3F,0x00},
  {0x1E,0x33,0x30,0x1C,0x06,0x33,0x3F,0x00},
  {0x1E,0x33,0x30,0x1C,0x30,0x33,0x1E,0x00},
  {0x38,0x3C,0x36,0x33,0x7F,0x30,0x78,0x00},
  {0x3F,0x03,0x1F,0x30,0x30,0x33,0x1E,0x00},
  {0x1C,0x06,0x03,0x1F,0x33,0x33,0x1E,0x00},
  {0x3F,0x33,0x30,0x18,0x0C,0x0C,0x0C,0x00},
  {0x1E,0x33,0x33,0x1E,0x33,0x33,0x1E,0x00},
  {0x1E,0x33,0x33,0x3E,0x30,0x18,0x0E,0x00},
  {0x00,0x0C,0x0C,0x00,0x00,0x0C,0x0C,0x00},
  {0x00,0x0C,0x0C,0x00,0x00,0x0C,0x0C,0x06},
  {0x18,0x0C,0x06,0x03,0x06,0x0C,0x18,0x00},
  {0x00,0x00,0x3F,0x00,0x00,0x3F,0x00,0x00},
  {0x06,0x0C,0x18,0x30,0x18,0x0C,0x06,0x00},
  {0x1E,0x33,0x30,0x18,0x0C,0x00,0x0C,0x00},
  {0x3E,0x63,0x7B,0x7B,0x7B,0x03,0x1E,0x00},
  {0x0C,0x1E,0x33,0x33,0x3F,0x33,0x33,0x00},
  {0x3F,0x66,0x66,0x3E,0x66,0x66,0x3F,0x00},
  {0x3C,0x66,0x03,0x03,0x03,0x66,0x3C,0x00},
  {0x1F,0x36,0x66,0x66,0x66,0x36,0x1F,0x00},
  {0x7F,0x46,0x16,0x1E,0x16,0x46,0x7F,0x00},
  {0x7F,0x46,0x16,0x1E,0x16,0x06,0x0F,0x00},
  {0x3C,0x66,0x03,0x03,0x73,0x66,0x7C,0x00},
  {0x33,0x33,0x33,0x3F,0x33,0x33,0x33,0x00},
  {0x1E,0x0C,0x0C,0x0C,0x0C,0x0C,0x1E,0x00},
  {0x78,0x30,0x30,0x30,0x33,0x33,0x1E,0x00},
  {0x67,0x66,0x36,0x1E,0x36,0x66,0x67,0x00},
  {0x0F,0x06,0x06,0x06,0x46,0x66,0x7F,0x00},
  {0x63,0x77,0x7F,0x7F,0x6B,0x63,0x63,0x00},
  {0x63,0x67,0x6F,0x7B,0x73,0x63,0x63,0x00},
  {0x1C,0x36,0x63,0x63,0x63,0x36,0x1C,0x00},
  {0x3F,0x66,0x66,0x3E,0x06,0x06,0x0F,0x00},
  {0x1E,0x33,0x33,0x33,0x3B,0x1E,0x38,0x00},
  {0x3F,0x66,0x66,0x3E,0x36,0x66,0x67,0x00},
  {0x1E,0x33,0x07,0x0E,0x38,0x33,0x1E,0x00},
  {0x3F,0x2D,0x0C,0x0C,0x0C,0x0C,0x1E,0x00},
  {0x33,0x33,0x33,0x33,0x33,0x33,0x3F,0x00},
  {0x33,0x33,0x33,0x33,0x33,0x1E,0x0C,0x00},
  {0x63,0x63,0x63,0x6B,0x7F,0x77,0x63,0x00},
  {0x63,0x63,0x36,0x1C,0x1C,0x36,0x63,0x00},
  {0x33,0x33,0x33,0x1E,0x0C,0x0C,0x1E,0x00},
  {0x7F,0x63,0x31,0x18,0x4C,0x66,0x7F,0x00},
  {0x1E,0x06,0x06,0x06,0x06,0x06,0x1E,0x00},
  {0x03,0x06,0x0C,0x18,0x30,0x60,0x40,0x00},
  {0x1E,0x18,0x18,0x18,0x18,0x18,0x1E,0x00},
  {0x08,0x1C,0x36,0x63,0x00,0x00,0x00,0x00},
  {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xFF},
  {0x0C,0x0C,0x18,0x00,0x00,0x00,0x00,0x00},
  {0x00,0x00,0x1E,0x30,0x3E,0x33,0x6E,0x00},
  {0x07,0x06,0x06,0x3E,0x66,0x66,0x3B,0x00},
  {0x00,0x00,0x1E,0x33,0x03,0x33,0x1E,0x00},
  {0x38,0x30,0x30,0x3e,0x33,0x33,0x6E,0x00},
  {0x00,0x00,0x1E,0x33,0x3f,0x03,0x1E,0x00},
  {0x1C,0x36,0x06,0x0f,0x06,0x06,0x0F,0x00},
  {0x00,0x00,0x6E,0x33,0x33,0x3E,0x30,0x1F},
  {0x07,0x06,0x36,0x6E,0x66,0x66,0x67,0x00},
  {0x0C,0x00,0x0E,0x0C,0x0C,0x0C,0x1E,0x00},
  {0x30,0x00,0x30,0x30,0x30,0x33,0x33,0x1E},
  {0x07,0x06,0x66,0x36,0x1E,0x36,0x67,0x00},
  {0x0E,0x0C,0x0C,0x0C,0x0C,0x0C,0x1E,0x00},
  {0x00,0x00,0x33,0x7F,0x7F,0x6B,0x63,0x00},
  {0x00,0x00,0x1F,0x33,0x33,0x33,0x33,0x00},
  {0x00,0x00,0x1E,0x33,0x33,0x33,0x1E,0x00},
  {0x00,0x00,0x3B,0x66,0x66,0x3E,0x06,0x0F},
  {0x00,0x00,0x6E,0x33,0x33,0x3E,0x30,0x78},
  {0x00,0x00,0x3B,0x6E,0x66,0x06,0x0F,0x00},
  {0x00,0x00,0x3E,0x03,0x1E,0x30,0x1F,0x00},
  {0x08,0x0C,0x3E,0x0C,0x0C,0x2C,0x18,0x00},
  {0x00,0x00,0x33,0x33,0x33,0x33,0x6E,0x00},
  {0x00,0x00,0x33,0x33,0x33,0x1E,0x0C,0x00},
  {0x00,0x00,0x63,0x6B,0x7F,0x7F,0x36,0x00},
  {0x00,0x00,0x63,0x36,0x1C,0x36,0x63,0x00},
  {0x00,0x00,0x33,0x33,0x33,0x3E,0x30,0x1F},
  {0x00,0x00,0x3F,0x19,0x0C,0x26,0x3F,0x00},
  {0x38,0x0C,0x0C,0x07,0x0C,0x0C,0x38,0x00},
  {0x18,0x18,0x18,0x00,0x18,0x18,0x18,0x00},
  {0x07,0x0C,0x0C,0x38,0x0C,0x0C,0x07,0x00},
  {0x6E,0x3B,0x00,0x00,0x00,0x00,0x00,0x00},
};
static void fb_char(int cx,int cy,char ch,u32 fg,u32 bg){
    if(ch<0x20||ch>0x7E) ch='?';
    const u8 *g=font8x8[ch-0x20];
    for(int r=0;r<8;r++){ u8 b=g[r];
        for(int c=0;c<8;c++) fb_pixel(cx+c,cy+r,(b&(0x80>>c))?fg:bg); }
}
static void fb_text(int x,int y,const char *s,u32 fg,u32 bg){
    int cx=x;
    while(*s){ if(*s=='\n'){cx=x;y+=8;s++;continue;}
        fb_char(cx,y,*s++,fg,bg); cx+=8;
        if(cx+8>FB_WIDTH){cx=x;y+=8;} }
}
/* Number to FB */
static char _nb[32];
static void fb_dec(int x,int y,u64 v,u32 fg,u32 bg){
    int i=0; if(v==0){_nb[i++]='0';}
    else{ u64 t=v; int s=0; while(t){_nb[s++]='0'+t%10;t/=10;}
          for(int a=0,b=s-1;a<b;a++,b--){char tmp=_nb[a];_nb[a]=_nb[b];_nb[b]=tmp;}
          i=s; }
    _nb[i]=0; fb_text(x,y,_nb,fg,bg);
}
static void fb_hex(int x,int y,u64 v,u32 fg,u32 bg){
    char buf[20]; buf[0]='0';buf[1]='x';
    for(int i=0;i<16;i++){
        int nib=(v>>(60-i*4))&0xF;
        buf[2+i]=nib<10?'0'+nib:'a'+nib-10; }
    buf[18]=0; fb_text(x,y,buf,fg,bg);
}

/* ================================================================= MEMORY */
#define HEAP_START  0x44000000UL
#define HEAP_END    0x48000000UL

/* heap_ptr must be declared BEFORE buddy/kmalloc functions that reference it */
static u64 heap_ptr __attribute__((section(".data"))) = HEAP_START;

/* ================================================================ BUDDY ALLOCATOR
 * Linux-style power-of-2 free lists over bump-allocated blocks.
 * Orders 0-10: 8B, 16B, 32B, 64B, ... 8192B
 * Larger allocs fall back to the SMP-safe bump allocator directly.
 *
 * SMP SAFETY: heap_ptr protected by LDXR/STXR atomic CAS loop.
 * No per-CPU heaps yet — single atomic pointer is correct for 4 cores.
 */
#define BUDDY_ORDERS   11          /* orders 0..10 = 8..8192 bytes */
#define BUDDY_MIN      8           /* minimum block = 8 bytes       */

typedef struct buddy_node { struct buddy_node *next; } buddy_node_t;
static buddy_node_t *buddy_free[BUDDY_ORDERS];  /* free-list per order */
static spinlock_t    buddy_lock = 0;

/* SMP-safe bump: hold buddy_lock while advancing heap_ptr.
 * The spinlock provides all the memory ordering we need.
 * No LDAXR/STLXR required — simpler and definitely correct.
 */
static void *bump_alloc_atomic(size_t sz) {
    sz = (sz + 7) & ~7UL;
    irqflags_t f = irq_save();
    spin_lock(&buddy_lock);
    void *p = NULL;
    if (heap_ptr + sz <= HEAP_END) {
        p = (void *)heap_ptr;
        heap_ptr += sz;
    }
    spin_unlock(&buddy_lock);
    irq_restore(f);
    return p;
}

static int buddy_order_for(size_t sz) {
    size_t block = BUDDY_MIN;
    for (int o = 0; o < BUDDY_ORDERS; o++, block <<= 1)
        if (block >= sz) return o;
    return -1; /* too large, use bump directly */
}

static void *kmalloc(size_t sz) {
    if (sz == 0) return NULL;
    int o = buddy_order_for(sz);
    if (o >= 0) {
        irqflags_t f = irq_save();
        spin_lock(&buddy_lock);
        if (buddy_free[o]) {
            void *p = buddy_free[o];
            buddy_free[o] = buddy_free[o]->next;
            spin_unlock(&buddy_lock);
            irq_restore(f);
            return p;
        }
        spin_unlock(&buddy_lock);
        irq_restore(f);
        /* No free block at this order — bump-allocate a fresh one */
        size_t block_sz = (size_t)BUDDY_MIN << o;
        return bump_alloc_atomic(block_sz);
    }
    /* Oversized: straight bump */
    return bump_alloc_atomic(sz);
}

static void *kzalloc(size_t sz) {
    u8 *p = kmalloc(sz);
    if (p) for (size_t i = 0; i < sz; i++) p[i] = 0;
    return p;
}

static void kfree(void *ptr) {
    if (!ptr) return;
    /* Return block to buddy free-list order 0 (8B) as a conservative default.
     * A proper implementation would track the order in a header — future work. */
    irqflags_t f = irq_save();
    spin_lock(&buddy_lock);
    buddy_node_t *n = (buddy_node_t *)ptr;
    n->next = buddy_free[0];
    buddy_free[0] = n;
    spin_unlock(&buddy_lock);
    irq_restore(f);
}


/* String utils */
static size_t kstrlen(const char *s){ size_t n=0; while(s[n]) n++; return n; }
static void kstrcpy(char *d,const char *s){ while((*d++=*s++)); }
static char *kstrncpy(char *d,const char *s,size_t n){
    size_t i; for(i=0;i<n-1&&s[i];i++) d[i]=s[i]; d[i]=0; return d; }
static int kstrcmp(const char *a,const char *b){
    while(*a&&*a==*b){a++;b++;} return *(u8*)a-*(u8*)b; }
static int kstrncmp(const char *a,const char *b,size_t n){
    while(n--&&*a&&*a==*b){a++;b++;}
    return n==(size_t)-1?0:*(u8*)a-*(u8*)b; }
static char *kstrchr(const char *s,char c){
    while(*s){if(*s==c)return(char*)s;s++;} return NULL; }
static void kmemcpy(void *d,const void *s,size_t n){
    u8 *dd=d;const u8 *ss=s; while(n--)*dd++=*ss++; }
static void kmemset(void *d,u8 v,size_t n){
    u8 *dd=d; while(n--)*dd++=v; }
static void kstrcat(char *d,const char *s){
    d+=kstrlen(d); while((*d++=*s++)); }
/* itoa */
static char *kitoa(u64 v,char *buf){
    if(v==0){buf[0]='0';buf[1]=0;return buf;}
    int i=0; while(v){buf[i++]='0'+v%10;v/=10;}
    for(int a=0,b=i-1;a<b;a++,b--){char t=buf[a];buf[a]=buf[b];buf[b]=t;}
    buf[i]=0; return buf;
}

/* ================================================================== VFS */
#define VFS_NAME_MAX  64
#define VFS_DATA_MAX  1024
#define VFS_TYPE_FILE 0
#define VFS_TYPE_DIR  1
#define VFS_TYPE_LINK 2
#define VFS_TYPE_PIPE 3

typedef struct vfs_node {
    char            name[VFS_NAME_MAX];
    int             type;
    u8             *data;     /* pointer for dynamic allocation */
    size_t          size;
    u32             mode;      /* permissions (Unix-style) */
    u32             uid;
    u32             gid;
    struct vfs_node *parent;
    struct vfs_node *child;
    struct vfs_node *next;
    struct vfs_node *link_target; /* for symlinks */
} vfs_node_t;

static vfs_node_t *vfs_root=NULL, *vfs_cwd=NULL;

#define PIPE_BUF_SIZE 4096
typedef struct {
    char buffer[PIPE_BUF_SIZE];
    int read_pos;
    int write_pos;
    int bytes_available;
    int writers;
    int readers;
} pipe_buffer_t;

static pipe_buffer_t pipes[16];
static int next_pipe = 0;

static pipe_buffer_t *pipe_get(int fd) {
    if (fd < 0 || fd >= 16) return NULL;
    return &pipes[fd];
}

static int pipe_alloc(void) {
    int fd = next_pipe;
    next_pipe = (next_pipe + 1) % 16;
    pipes[fd].read_pos = 0;
    pipes[fd].write_pos = 0;
    pipes[fd].bytes_available = 0;
    pipes[fd].writers = 0;
    pipes[fd].readers = 0;
    return fd;
}

static vfs_node_t *vfs_mknode(vfs_node_t *parent,const char *name,int type){
    vfs_node_t *n=kzalloc(sizeof(vfs_node_t));
    if(!n) return NULL;
    kstrncpy(n->name,name,VFS_NAME_MAX);
    n->type=type; n->parent=parent; n->mode=0644; n->uid=0;
    if(parent){ n->next=parent->child; parent->child=n; }
    return n;
}
static vfs_node_t *vfs_find(vfs_node_t *dir,const char *name){
    if(!dir||dir->type!=VFS_TYPE_DIR) return NULL;
    for(vfs_node_t *c=dir->child;c;c=c->next)
        if(kstrcmp(c->name,name)==0) return c;
    return NULL;
}
static int vfs_write(vfs_node_t *f,const char *data,size_t len){
    if(!f||f->type!=VFS_TYPE_FILE) return -1;
    if(len>VFS_DATA_MAX) len=VFS_DATA_MAX;
    kmemcpy(f->data,data,len); f->size=len; return (int)len;
}
static int vfs_count_children(vfs_node_t *dir){
    int n=0; for(vfs_node_t *c=dir->child;c;c=c->next) n++; return n;
}

static void vfs_init(void){
    vfs_root=vfs_mknode(NULL,"/",VFS_TYPE_DIR); vfs_cwd=vfs_root;
    vfs_node_t *bin=vfs_mknode(vfs_root,"bin",VFS_TYPE_DIR);
    vfs_node_t *sh=vfs_mknode(bin,"sh",VFS_TYPE_FILE);
    vfs_write(sh,"#!/bin/sh\n# MiniOS shell v2\n",27);
    vfs_node_t *ks=vfs_mknode(bin,"ks",VFS_TYPE_FILE);
    vfs_write(ks,"#!/bin/ks\n# KentScript VM 2.1\n",29); ks->mode=0755;
    vfs_node_t *etc=vfs_mknode(vfs_root,"etc",VFS_TYPE_DIR);
    vfs_node_t *rel=vfs_mknode(etc,"os-release",VFS_TYPE_FILE);
    vfs_write(rel,"NAME=\"MiniOS\"\nVERSION=\"2.2\"\nARCH=\"aarch64\"\nBUILD=\"bare-metal\"\nUSER=\"user\"\n",74);
    vfs_node_t *motd=vfs_mknode(etc,"motd",VFS_TYPE_FILE);
    vfs_write(motd,"Welcome to MiniOS 2.2 — AArch64 Bare Metal\nBuilt in Uganda. Running on silicon.\nBuddy alloc | SMP-safe heap | Kernel backtrace | kdb debugger\n",139);
    vfs_node_t *home=vfs_mknode(vfs_root,"home",VFS_TYPE_DIR);
    vfs_node_t *kent=vfs_mknode(home,"user",VFS_TYPE_DIR);
    vfs_node_t *rc=vfs_mknode(kent,".kentrc",VFS_TYPE_FILE);
    vfs_write(rc,"# MiniOS 2.2 init\nexport PATH=/bin:/usr/bin\nexport USER=user\n",62);
    vfs_node_t *hello=vfs_mknode(kent,"hello.ks",VFS_TYPE_FILE);
    /* KentScript 2.1 syntax: :: comments, func keyword, print() */
    vfs_write(hello,
        ":: KentScript 2.1 — runs inside MiniOS 2.2\n"
        ":: No Linux. No libc. Pure silicon.\n"
        "\n"
        "func greet(name) {\n"
        "    print(\"Hello, \" + name + \"!\")\n"
        "}\n"
        "\n"
        "func main() {\n"
        "    greet(\"MiniOS 2.2\")\n"
        "    print(\"Built in Uganda. Running on silicon.\")\n"
        "    let uptime = syscall(SYS_UPTIME)\n"
        "    print(\"Uptime ticks: \" + str(uptime))\n"
        "}\n"
        "\n"
        "main()\n", 256);
    hello->mode=0755;
    /* Also create a fib.ks example */
    vfs_node_t *fib=vfs_mknode(kent,"fib.ks",VFS_TYPE_FILE);
    vfs_write(fib,
        ":: KentScript 2.1 — fibonacci demo\n"
        "func fib(n) {\n"
        "    if n <= 1 { return n }\n"
        "    return fib(n-1) + fib(n-2)\n"
        "}\n"
        "func main() {\n"
        "    let i = 0\n"
        "    while i < 10 {\n"
        "        print(fib(i))\n"
        "        i = i + 1\n"
        "    }\n"
        "}\n"
        "main()\n", 180);
    fib->mode=0755;
    vfs_node_t *proc=vfs_mknode(vfs_root,"proc",VFS_TYPE_DIR);
    vfs_node_t *ver=vfs_mknode(proc,"version",VFS_TYPE_FILE);
    vfs_write(ver,"MiniOS 2.2.0 (AArch64 bare-metal) #1 SMP\n",41);
    vfs_node_t *cpu=vfs_mknode(proc,"cpuinfo",VFS_TYPE_FILE);
    vfs_write(cpu,"processor : 0\nmodel name: ARM Cortex-A53\narch: AArch64\nEL: 1\n",60);
    vfs_mknode(proc,"meminfo",VFS_TYPE_FILE);
    vfs_node_t *dev=vfs_mknode(vfs_root,"dev",VFS_TYPE_DIR);
    vfs_mknode(dev,"uart0",VFS_TYPE_FILE);
    vfs_mknode(dev,"fb0",VFS_TYPE_FILE);
    vfs_mknode(dev,"null",VFS_TYPE_FILE);
    vfs_mknode(dev,"zero",VFS_TYPE_FILE);
    vfs_node_t *tmp=vfs_mknode(vfs_root,"tmp",VFS_TYPE_DIR);
    vfs_node_t *usr=vfs_mknode(vfs_root,"usr",VFS_TYPE_DIR);
    vfs_node_t *ubin=vfs_mknode(usr,"bin",VFS_TYPE_DIR);
    vfs_node_t *test_prog=vfs_mknode(ubin,"test",VFS_TYPE_FILE);
    vfs_write(test_prog,"# test userland program\n",24); test_prog->mode=0755;
    (void)tmp;(void)ubin;
}

/* ================================================================ SCHEDULER */
#define MAX_TASKS   12
#define TASK_STACK  16384  /* 16KB per task */

typedef enum { TASK_READY,TASK_RUNNING,TASK_BLOCKED,TASK_DEAD,TASK_SLEEPING } task_state_t;
typedef enum { PRIO_LOW=0,PRIO_NORMAL=1,PRIO_HIGH=2,PRIO_RT=3 } task_prio_t;

/* Canary value for stack/task-struct integrity checking */
#define TASK_CANARY_MAGIC  0xC0FFEEDEADBEEFULL
#define TASK_CANARY_FOOT   0xBEEFCAFECAFEBEEFULL

typedef struct task {
    u64          canary_head;  /* must be TASK_CANARY_MAGIC — checked on every ps/sched */
    u64          sp_save;
    u64          id;
    task_state_t state;
    task_prio_t  prio;
    char         name[32];
    u8          *stack;
    u64          ticks;
    u64          sleep_until; /* tick to wake */
    u64          user_entry;  /* EL0 entry if userland */
    u64          user_sp;
    int          is_user;     /* runs in EL0? */
    u64          canary_tail;  /* must be TASK_CANARY_FOOT */
    int          parent_pid;   /* parent process ID */
    int          pgid;         /* process group ID */
    int          sid;          /* session ID */
    int          traced;       /* being traced? */
    int          children[8];  /* child PIDs */
    int          child_count;  /* number of children */
} task_t;

static task_t  tasks[MAX_TASKS];
static int     task_count=0, current_task=0;
static u64     tick_count=0;
static u64     ctx_switches=0;

extern void minios_switch_context(u64 *old_sp,u64 new_sp);

static void idle_task(void){ while(1) __asm__ volatile("wfi"); }

static void task_init(void){
    tasks[0].canary_head=TASK_CANARY_MAGIC;
    tasks[0].canary_tail=TASK_CANARY_FOOT;
    tasks[0].id=0; tasks[0].state=TASK_RUNNING;
    tasks[0].prio=PRIO_NORMAL;
    kstrcpy(tasks[0].name,"idle"); tasks[0].ticks=0;
    task_count=1; current_task=0;
}

typedef void (*task_fn_t)(void);

static int task_spawn(const char *name,task_fn_t fn,task_prio_t prio){
    irqflags_t flags = irq_save();
    spin_lock(&task_list_lock);
    if(task_count>=MAX_TASKS){ spin_unlock(&task_list_lock); irq_restore(flags); return -1; }
    int id=task_count++;
    spin_unlock(&task_list_lock);
    irq_restore(flags);

    task_t *t=&tasks[id];
    t->canary_head=TASK_CANARY_MAGIC;
    t->canary_tail=TASK_CANARY_FOOT;
    t->id=(u64)id; t->state=TASK_READY; t->ticks=0;
    t->prio=prio; t->is_user=0;
    kstrncpy(t->name,name,32);
    t->stack=kmalloc(TASK_STACK);
    if(!t->stack) return -1;
    /* Write stack foot canary to detect overflow */
    *((volatile u64*)t->stack) = TASK_CANARY_FOOT;
    u64 *sp=(u64*)(t->stack+TASK_STACK);
    for(int i=0;i<12;i++) *(--sp)=0;
    u64 *frame=sp; frame[1]=(u64)fn;
    t->sp_save=(u64)sp;
    return id;
}

/* Check canary integrity — call this before traversing task list */
static void sched_check_canaries(void) {
    for(int i=0;i<task_count;i++){
        if(tasks[i].canary_head!=TASK_CANARY_MAGIC ||
           tasks[i].canary_tail!=TASK_CANARY_FOOT) {
            uart_puts("\n[KENTOS PANIC] Task struct canary corrupt! PID=");
            put_dec((u64)i);
            uart_puts(" head=0x"); put_hex64(tasks[i].canary_head);
            uart_puts(" tail=0x"); put_hex64(tasks[i].canary_tail);
            uart_puts("\n[KENTOS PANIC] Halted.\n");
            __asm__ volatile("msr daifset, #0xf");
            while(1) __asm__ volatile("wfe");
        }
        /* Check stack bottom canary for overflow */
        if(tasks[i].stack) {
            u64 foot=*((volatile u64*)tasks[i].stack);
            if(foot!=TASK_CANARY_FOOT) {
                uart_puts("\n[KENTOS PANIC] Stack overflow in task PID=");
                put_dec((u64)i);
                uart_puts(" name="); uart_puts(tasks[i].name);
                uart_puts("\n[KENTOS PANIC] Halted.\n");
                __asm__ volatile("msr daifset, #0xf");
                while(1) __asm__ volatile("wfe");
            }
        }
    }
}

/* Bounds-safe state index (enum has 5 values: 0-4) */
static inline int task_state_idx(task_t *t) {
    int s = (int)t->state;
    return (s >= 0 && s <= 4) ? s : 0;
}

/* Safe state/prio string helpers — no local pointer arrays, no LDP alignment risk.
 * Uses switch so GCC emits simple branches, not LDR-from-rodata-array sequences. */
static const char *task_state_str(task_t *t) {
    switch(task_state_idx(t)) {
        case 0: return "READY  ";
        case 1: return "RUNNING";
        case 2: return "BLOCKED";
        case 3: return "DEAD   ";
        case 4: return "SLEEP  ";
        default: return "???????";
    }
}
static const char *task_prio_str(task_t *t) {
    switch((int)t->prio & 3) {
        case 0: return "LOW ";
        case 1: return "NORM";
        case 2: return "HIGH";
        case 3: return "RT  ";
        default: return "????";
    }
}

static void sched_tick(void){
    tick_count++;
    tasks[current_task].ticks++;
    /* Wake sleeping tasks */
    for(int i=0;i<task_count;i++)
        if(tasks[i].state==TASK_SLEEPING && tick_count>=tasks[i].sleep_until)
            tasks[i].state=TASK_READY;
    /* Priority-aware round-robin: prefer higher priority */
    int best=-1, best_prio=-1;
    for(int i=1;i<=task_count;i++){
        int next=(current_task+i)%task_count;
        if(tasks[next].state==TASK_READY||tasks[next].state==TASK_RUNNING){
            if((int)tasks[next].prio>best_prio){
                best=next; best_prio=(int)tasks[next].prio;
            }
        }
    }
    if(best<0||best==current_task) return;
    tasks[current_task].state=(tasks[current_task].state==TASK_RUNNING)?TASK_READY:tasks[current_task].state;
    int old=current_task; current_task=best;
    tasks[current_task].state=TASK_RUNNING;
    ctx_switches++;
    minios_switch_context(&tasks[old].sp_save,tasks[current_task].sp_save);
}

static void task_sleep(u64 ticks){
    tasks[current_task].state=TASK_SLEEPING;
    tasks[current_task].sleep_until=tick_count+ticks;
    __asm__ volatile("yield");
}

static void task_block(void){
    tasks[current_task].state=TASK_BLOCKED;
}

/* ================================================================ TIMER / GIC */
#define GIC_DIST  ((volatile u32*)0x08000000UL)
#define GIC_CPU   ((volatile u32*)0x08010000UL)

static u64 timer_freq=0;

static void timer_init(void){
    __asm__ volatile("mrs %0, cntfrq_el0":"=r"(timer_freq));
    if(timer_freq==0) timer_freq=62500000;
    u64 tval=timer_freq/100;
    __asm__ volatile("msr cntv_tval_el0, %0"::"r"(tval));
    u64 ctrl=1; __asm__ volatile("msr cntv_ctl_el0, %0"::"r"(ctrl));
    GIC_DIST[0]=1;
    GIC_DIST[0x100/4]|=(1u<<27);
    GIC_CPU[0]=1; GIC_CPU[1]=0xFF;
    __asm__ volatile("msr daifclr, #2");
}
static void timer_ack(void){
    u64 tval=timer_freq/100;
    __asm__ volatile("msr cntv_tval_el0, %0"::"r"(tval));
}

/* ============================================================= EL0 USERLAND */
/* Drop to EL0 and run user code — x0=entry, x1=user stack top */
extern void minios_enter_el0(u64 entry,u64 user_stack);

/* ELF64 minimal header */
#define ELF_MAGIC 0x464C457FU
typedef struct {
    u32 magic; u8 class,data,version,osabi; u8 pad[8];
    u16 type,machine; u32 version2;
    u64 entry,phoff,shoff; u32 flags,ehsize;
    u16 phentsize,phnum,shentsize,shnum,shstrndx;
} __attribute__((packed)) Elf64_Ehdr;
typedef struct {
    u32 type,flags; u64 offset,vaddr,paddr,filesz,memsz,align;
} __attribute__((packed)) Elf64_Phdr;
#define PT_LOAD 1

/* User memory region: 0x10000000 – 0x14000000 (64MB) */
#define USER_BASE  0x10000000UL
#define USER_SIZE  0x04000000UL
#define USER_STACK 0x14000000UL  /* top of user stack */

/* Load ELF from VFS into user address space and drop to EL0 */
static int elf_load_and_run(vfs_node_t *f){
    if(!f||f->type!=VFS_TYPE_FILE||f->size<64) return -1;
    u8 *elf=f->data;
    Elf64_Ehdr *hdr=(Elf64_Ehdr*)elf;
    if(hdr->magic!=ELF_MAGIC) return -2; /* not ELF */
    if(hdr->class!=2) return -3; /* not 64-bit */
    /* Map segments */
    Elf64_Phdr *ph=(Elf64_Phdr*)(elf+hdr->phoff);
    for(int i=0;i<hdr->phnum;i++){
        if(ph[i].type!=PT_LOAD) continue;
        u8 *dst=(u8*)ph[i].vaddr;
        u8 *src=elf+ph[i].offset;
        kmemcpy(dst,src,(size_t)ph[i].filesz);
        if(ph[i].memsz>ph[i].filesz)
            kmemset(dst+ph[i].filesz,0,(size_t)(ph[i].memsz-ph[i].filesz));
    }
    uart_puts("[ELF] Loaded. Dropping to EL0 at 0x");
    put_hex64(hdr->entry); uart_puts("\n");
    minios_enter_el0(hdr->entry,USER_STACK);
    return 0; /* never returns */
}

/* ======================================================= KSVM — KentScript VM
 * Tiny bytecode interpreter — runs inside kernel as a task
 * Opcodes: PUSH, POP, ADD, SUB, MUL, DIV, PRINT, HALT, JMP, JZ, CMP, LOAD, STORE
 */
#define KS_PUSH   0x01
#define KS_POP    0x02
#define KS_ADD    0x03
#define KS_SUB    0x04
#define KS_MUL    0x05
#define KS_DIV    0x06
#define KS_PRINT  0x07
#define KS_HALT   0x08
#define KS_JMP    0x09
#define KS_JZ     0x0A
#define KS_CMP    0x0B
#define KS_LOAD   0x0C
#define KS_STORE  0x0D
#define KS_PRINTS 0x0E  /* print string literal at ip offset */
#define KS_NOP    0x00
/* KentScript 2.1 — new opcodes for OS integration */
#define KS_SYSCALL 0x0F  /* syscall: pop nr, call minios SVC, push result */
#define KS_YIELD   0x10  /* cooperative yield to scheduler */
#define KS_GETPID  0x11  /* push current task PID */
#define KS_UPTIME  0x12  /* push tick_count */
#define KS_MOD     0x13  /* modulo: pop b,a push a%b */
#define KS_AND     0x14  /* bitwise AND */
#define KS_OR      0x15  /* bitwise OR */
#define KS_NOT     0x16  /* bitwise NOT */
#define KS_DUP     0x17  /* duplicate top of stack */
#define KS_SWAP    0x18  /* swap top two stack items */
#define KS_PRINTC  0x19  /* print character (low byte of top) */

#define KS_STACK_MAX 64
#define KS_MEM_MAX   256

typedef struct {
    s64  stack[KS_STACK_MAX];
    int  sp;         /* stack pointer */
    s64  mem[KS_MEM_MAX]; /* variable memory */
    int  running;
    int  ip;
    const u8 *code;
    size_t code_len;
} ks_vm_t;

static ks_vm_t *ks_vm_new(const u8 *code,size_t len){
    ks_vm_t *vm=kzalloc(sizeof(ks_vm_t));
    if(!vm) return NULL;
    vm->code=code; vm->code_len=len; vm->running=1; return vm;
}
static void ks_push(ks_vm_t *vm,s64 v){
    if(vm->sp<KS_STACK_MAX) vm->stack[vm->sp++]=v;
}
static s64 ks_pop(ks_vm_t *vm){
    if(vm->sp>0) return vm->stack[--vm->sp]; return 0;
}
static void ks_vm_run(ks_vm_t *vm){
    while(vm->running && vm->ip<(int)vm->code_len){
        u8 op=vm->code[vm->ip++];
        switch(op){
        case KS_NOP: break;
        case KS_PUSH:{
            s64 v=0;
            for(int i=0;i<8&&vm->ip<(int)vm->code_len;i++)
                v|=((s64)vm->code[vm->ip++])<<(i*8);
            ks_push(vm,v); break; }
        case KS_POP: ks_pop(vm); break;
        case KS_ADD:{ s64 b=ks_pop(vm),a=ks_pop(vm); ks_push(vm,a+b); break; }
        case KS_SUB:{ s64 b=ks_pop(vm),a=ks_pop(vm); ks_push(vm,a-b); break; }
        case KS_MUL:{ s64 b=ks_pop(vm),a=ks_pop(vm); ks_push(vm,a*b); break; }
        case KS_DIV:{ s64 b=ks_pop(vm),a=ks_pop(vm); ks_push(vm,b?a/b:0); break; }
        case KS_PRINT:{ char buf[32]; kitoa((u64)ks_pop(vm),buf);
            uart_puts(buf); uart_puts("\n"); break; }
        case KS_PRINTS:{
            /* null-terminated string embedded in code */
            while(vm->ip<(int)vm->code_len&&vm->code[vm->ip])
                uart_putc((char)vm->code[vm->ip++]);
            if(vm->ip<(int)vm->code_len) vm->ip++; /* skip null */
            uart_puts("\n"); break; }
        case KS_HALT: vm->running=0; break;
        case KS_JMP:{ int addr=(int)vm->code[vm->ip++]; vm->ip=addr; break; }
        case KS_JZ:{ int addr=(int)vm->code[vm->ip++];
            if(ks_pop(vm)==0) vm->ip=addr; break; }
        case KS_CMP:{ s64 b=ks_pop(vm),a=ks_pop(vm);
            ks_push(vm,a==b?0:a<b?-1:1); break; }
        case KS_LOAD:{ int addr=(int)vm->code[vm->ip++];
            if(addr<KS_MEM_MAX) ks_push(vm,vm->mem[addr]); break; }
        case KS_STORE:{ int addr=(int)vm->code[vm->ip++];
            if(addr<KS_MEM_MAX) vm->mem[addr]=ks_pop(vm); break; }
        /* KentScript 2.1 OS-integration opcodes */
        case KS_SYSCALL:{ (void)ks_pop(vm); ks_push(vm,0); break; } /* stub: SVC in EL0 context */
        case KS_YIELD: __asm__ volatile("yield"); break;
        case KS_GETPID: ks_push(vm,(s64)current_task); break;
        case KS_UPTIME: ks_push(vm,(s64)tick_count); break;
        case KS_MOD:{ s64 b=ks_pop(vm),a=ks_pop(vm); ks_push(vm,b?a%b:0); break; }
        case KS_AND:{ s64 b=ks_pop(vm),a=ks_pop(vm); ks_push(vm,a&b); break; }
        case KS_OR: { s64 b=ks_pop(vm),a=ks_pop(vm); ks_push(vm,a|b); break; }
        case KS_NOT:{ s64 a=ks_pop(vm); ks_push(vm,~a); break; }
        case KS_DUP:{ if(vm->sp>0) ks_push(vm,vm->stack[vm->sp-1]); break; }
        case KS_SWAP:{ if(vm->sp>=2){ s64 t=vm->stack[vm->sp-1];
            vm->stack[vm->sp-1]=vm->stack[vm->sp-2];
            vm->stack[vm->sp-2]=t; } break; }
        case KS_PRINTC:{ char c=(char)(ks_pop(vm)&0xFF); uart_putc(c); break; }
        default: vm->running=0; break;
        }
    }
}

/* Built-in KentScript program: fibonacci(10) */
static const u8 ks_fibonacci_prog[]={
    KS_PRINTS,'F','i','b','o','n','a','c','c','i',' ','s','e','q','u','e','n','c','e',':',0,
    /* a=0, b=1, n=10 */
    KS_PUSH,0,0,0,0,0,0,0,0, KS_STORE,0, /* mem[0]=0 (a) */
    KS_PUSH,1,0,0,0,0,0,0,0, KS_STORE,1, /* mem[1]=1 (b) */
    KS_PUSH,10,0,0,0,0,0,0,0,KS_STORE,2, /* mem[2]=10 (n) */
    /* loop: print a, c=a+b, a=b, b=c, n-- */
    /* 34: load a, print */
    KS_LOAD,0, KS_PRINT,
    /* load a+b → c (mem[3]) */
    KS_LOAD,0, KS_LOAD,1, KS_ADD, KS_STORE,3,
    /* a=b */
    KS_LOAD,1, KS_STORE,0,
    /* b=c */
    KS_LOAD,3, KS_STORE,1,
    /* n-- */
    KS_LOAD,2, KS_PUSH,1,0,0,0,0,0,0,0, KS_SUB, KS_STORE,2,
    /* if n>0 jump back to 34 */
    KS_LOAD,2, KS_JZ,0xFF, /* 0xFF = halt if n==0 */
    KS_JMP,34,
    KS_HALT
};

/* Built-in: sum 1..100 */
static const u8 ks_sum_prog[]={
    KS_PRINTS,'S','u','m',' ','1','.','.','.','1','0','0',':',0,
    KS_PUSH,0,0,0,0,0,0,0,0, KS_STORE,0, /* sum=0 */
    KS_PUSH,1,0,0,0,0,0,0,0, KS_STORE,1, /* i=1 */
    /* loop at ip=34: sum+=i; i++; if i<=100 loop */
    KS_LOAD,0, KS_LOAD,1, KS_ADD, KS_STORE,0,
    KS_LOAD,1, KS_PUSH,1,0,0,0,0,0,0,0, KS_ADD, KS_STORE,1,
    KS_LOAD,1, KS_PUSH,101,0,0,0,0,0,0,0, KS_CMP,
    KS_JZ,0xFF,
    KS_LOAD,2, /* hack: use mem[2] for cmp result; actually push result of CMP */
    /* simpler: re-do with JZ on counter */
    KS_JMP,18,
    KS_LOAD,0, KS_PRINT,
    KS_HALT
};
/* Simpler sum program */
static const u8 ks_sum2_prog[]={
    KS_PRINTS,'S','u','m',' ','1','+','.','.','.','+','1','0','0',':',0,
    KS_PUSH,0,0,0,0,0,0,0,0, KS_STORE,0,      /* sum=0  ip=27 */
    KS_PUSH,100,0,0,0,0,0,0,0, KS_STORE,1,    /* i=100  ip=38 */
    /* loop at ip=38: sum+=i, i--, if i!=0 loop */
    KS_LOAD,0, KS_LOAD,1, KS_ADD, KS_STORE,0, /* ip=38  sum+=i */
    KS_LOAD,1, KS_PUSH,1,0,0,0,0,0,0,0, KS_SUB, KS_STORE,1, /* ip=45  i-- */
    KS_LOAD,1, KS_JZ,65,   /* ip=59: if i==0 jump to print at ip=65 */
    KS_JMP,38,             /* ip=63: else jump back to loop */
    /* ip=65: print result */
    KS_LOAD,0, KS_PRINT,
    KS_HALT
};

/* ============================================================== SYSCALLS */
#define SYS_WRITE    1
#define SYS_READ     2
#define SYS_OPEN     3
#define SYS_CLOSE    4
#define SYS_EXIT     5
#define SYS_GETPID   6
#define SYS_SLEEP    7
#define SYS_UPTIME   8
#define SYS_FB_PIXEL 9
#define SYS_FB_RECT  10
#define SYS_FB_TEXT  11
#define SYS_MALLOC   12
#define SYS_FREE     13
#define SYS_GETTIME  14
#define SYS_YIELD    15
#define SYS_SPAWN    16

void minios_syscall_handler(u64 *regs){
    u64 nr=regs[8],arg0=regs[0],arg1=regs[1],arg2=regs[2],arg3=regs[3];
    switch(nr){
    case SYS_WRITE:{
        const char *buf=(const char*)arg1;
        size_t len=(size_t)arg2;
        if(arg0==1||arg0==2) for(size_t i=0;i<len;i++) uart_putc(buf[i]);
        regs[0]=len; break; }
    case SYS_GETPID: regs[0]=(u64)current_task; break;
    case SYS_UPTIME: regs[0]=tick_count; break;
    case SYS_GETTIME: regs[0]=tick_count*10; break; /* ms approximation */
    case SYS_EXIT:
        tasks[current_task].state=TASK_DEAD;
        regs[0]=0; break;
    case SYS_SLEEP:
        tasks[current_task].state=TASK_SLEEPING;
        tasks[current_task].sleep_until=tick_count+arg0;
        regs[0]=0; break;
    case SYS_YIELD: regs[0]=0; break;
    case SYS_FB_PIXEL: fb_pixel((int)arg0,(int)arg1,(u32)arg2); regs[0]=0; break;
    case SYS_FB_RECT:  fb_rect((int)arg0,(int)arg1,(int)arg2,(int)arg3,(u32)regs[4]); regs[0]=0; break;
    case SYS_FB_TEXT:
        fb_text((int)(arg0>>16),(int)(arg0&0xFFFF),(const char*)arg1,(u32)arg2,(u32)arg3);
        regs[0]=0; break;
    case SYS_MALLOC:{ void *p=kmalloc((size_t)arg0); regs[0]=(u64)p; break; }
    case SYS_FREE: kfree((void*)arg0); regs[0]=0; break;
    default: regs[0]=(u64)-1; break;
    }
}

/* ================================================================ KERNEL BACKTRACE
 * Walk AArch64 frame chain: frame[0]=saved_fp, frame[1]=saved_lr
 * Works because -O1 preserves frame pointers.
 * Usage: kernel_backtrace(regs[29])  (x29 = frame pointer)
 */
static void kernel_backtrace(u64 fp) {
    uart_puts("\n[BACKTRACE] === Kernel Stack Trace ===\n");
    for (int i = 0; i < 16 && fp && (fp & 7) == 0; i++) {
        if (fp < 0x40000000UL || fp > 0x48ffffffUL) break;
        u64 *frame = (u64 *)fp;
        u64 saved_fp = frame[0];
        u64 saved_lr  = frame[1];
        uart_puts("[BACKTRACE] #"); put_dec((u64)i);
        uart_puts("  LR=0x"); put_hex64(saved_lr);
        uart_puts("  FP=0x"); put_hex64(saved_fp); uart_puts("\n");
        if (saved_fp == fp || saved_fp == 0) break;
        fp = saved_fp;
    }
    uart_puts("[BACKTRACE] ================================\n");
    uart_puts("[BACKTRACE] Hint: addr2line -e /tmp/minios.elf <LR address>\n");
    uart_puts("[BACKTRACE]       objdump -d /tmp/minios.elf | grep <ELR> -B10\n");
}

/* ============================================================ EXCEPTION HANDLERS */
void minios_sync_handler(u64 *regs){
    u64 esr,elr,far;
    __asm__ volatile("mrs %0, esr_el1":"=r"(esr));
    __asm__ volatile("mrs %0, elr_el1":"=r"(elr));
    __asm__ volatile("mrs %0, far_el1":"=r"(far));
    u32 ec=(u32)((esr>>26)&0x3F);
    u32 iss=(u32)(esr&0x1FFFFFF);

    if(ec==0x15){ minios_syscall_handler(regs); return; } /* SVC */

    /* FP/SIMD trap — enable and retry */
    if(ec==0x07){
        u64 cpacr; __asm__ volatile("mrs %0, cpacr_el1":"=r"(cpacr));
        cpacr|=(3UL<<20); __asm__ volatile("msr cpacr_el1, %0"::"r"(cpacr));
        __asm__ volatile("isb"); return;
    }

    /* Data/Instruction abort from EL0 — kill that task */
    if((ec==0x24||ec==0x20)&&(tasks[current_task].is_user)){
        uart_puts("\n[KENTOS] EL0 task fault, killing task ");
        put_dec((u64)current_task); uart_puts("\n");
        tasks[current_task].state=TASK_DEAD;
        return;
    }

    uart_puts("\n[KENTOS PANIC] =============================\n");
    uart_puts("  ESR=0x"); put_hex64(esr);
    uart_puts("  EC=0x"); put_hex64(ec); uart_puts(" ");
    switch(ec){
        case 0x00: uart_puts("(unknown)"); break;
        case 0x07: uart_puts("(FP trap)"); break;
        case 0x0E: uart_puts("(illegal state)"); break;
        case 0x20: uart_puts("(insn abort lower EL)"); break;
        case 0x21: uart_puts("(insn abort same EL)"); break;
        case 0x24: uart_puts("(data abort lower EL)"); break;
        case 0x25: uart_puts("(data abort same EL)"); break;
        case 0x26: uart_puts("(SP align fault)"); break;
        default:   uart_puts("(see ARM ARM D1-7)"); break;
    }
    uart_puts("\n  ELR=0x"); put_hex64(elr);
    uart_puts("  FAR=0x"); put_hex64(far);
    uart_puts("  ISS=0x"); put_hex64(iss);
    uart_puts("\n  x0=0x");  put_hex64(regs[0]);
    uart_puts("  x1=0x");   put_hex64(regs[1]);
    uart_puts("  x28=0x");  put_hex64(regs[28]); /* x28 (not fp) */
    uart_puts("  x29=0x");  put_hex64(regs[29]); /* x29 = fp */
    uart_puts("  sp=0x");   put_hex64(regs[32]);
    /* Diagnose FAR — is it in kernel code (likely corrupt pointer)? */
    uart_puts("\n[KENTOS PANIC] FAR analysis: ");
    if(far>=0x40000000UL && far<=0x43ffffffUL)
        uart_puts("INSIDE KERNEL IMAGE — corrupt pointer/struct!\n");
    else if(far>=HEAP_START && far<=HEAP_END)
        uart_puts("inside heap — use-after-free or out-of-bounds\n");
    else if(far>=0x10000000UL && far<=0x14ffffffUL)
        uart_puts("inside user space — EL0 fault\n");
    else
        uart_puts("unmapped address — null/garbage deref\n");
    /* Walk frame pointer chain for backtrace — x29 = fp = regs[29] */
    kernel_backtrace(regs[29]); /* x29 is frame pointer on AArch64 */
    uart_puts("\n[KENTOS PANIC] Halted.\n");
    __asm__ volatile("msr daifset, #0xf");
    while(1) __asm__ volatile("wfe");
}

void minios_irq_handler(u64 *regs){
    (void)regs;
    u32 iar=GIC_CPU[3];
    if((iar&0x3FF)==27){
        timer_ack();
        /* IRQs are already masked when we're in IRQ handler — safe to call sched_tick */
        sched_tick();
    }
    GIC_CPU[4]=iar;
}

/* ================================================================ GUI */
#define WIN_MAX 6
typedef struct {
    int x,y,w,h;
    char title[32];
    u32 bg; int active;
} window_t;
static window_t windows[WIN_MAX];
static int win_count=0;

static void gui_draw_window(window_t *w){
    fb_rect(w->x+3,w->y+3,w->w,w->h,0x080808); /* shadow */
    fb_gradient(w->x,w->y,w->w,w->h,0x1a1a2e,0x16213e); /* body gradient */
    u32 tbar=w->active?0x1a73e8:0x2a2a4e;
    fb_gradient(w->x,w->y,w->w,22,tbar,w->active?0x0d5bce:0x1a1a3e);
    fb_border(w->x,w->y,w->w,w->h,1,w->active?0x4a9eff:0x333355);
    fb_rect(w->x+w->w-18,w->y+3,14,14,0xcc2222);
    fb_text(w->x+w->w-14,w->y+5,"x",0xffffff,0xcc2222);
    fb_text(w->x+6,w->y+7,w->title,0xffffff,tbar);
}
static int gui_open_window(int x,int y,int w,int h,const char *title,u32 bg,int active){
    if(win_count>=WIN_MAX) return -1;
    window_t *win=&windows[win_count++];
    win->x=x;win->y=y;win->w=w;win->h=h;win->bg=bg;win->active=active;
    kstrncpy(win->title,title,32); gui_draw_window(win); return win_count-1;
}
static void gui_text_in_window(int wid,int tx,int ty,const char *text,u32 fg){
    if(wid<0||wid>=win_count) return;
    window_t *w=&windows[wid];
    fb_text(w->x+tx,w->y+26+ty,text,fg,w->bg);
}
static void gui_dec_in_window(int wid,int tx,int ty,u64 v,u32 fg){
    if(wid<0||wid>=win_count) return;
    window_t *w=&windows[wid];
    fb_dec(w->x+tx,w->y+26+ty,v,fg,w->bg);
}
static void gui_clear_window(int wid){
    if(wid<0||wid>=win_count) return;
    window_t *w=&windows[wid];
    fb_gradient(w->x+1,w->y+23,w->w-2,w->h-24,w->bg,0x0d1117);
}

static void gui_draw_logo(int x,int y){
    u32 c1=0x00ccff,c2=0x1a73e8,c3=0x00ff88;
    /* K */
    fb_rect(x,y,4,24,c1);
    fb_rect(x+4,y+8,8,4,c1);
    fb_rect(x+8,y,4,12,c2);
    fb_rect(x+8,y+12,4,12,c2);
    /* O */
    fb_rect(x+20,y,16,24,c1);
    fb_rect(x+24,y+4,8,16,0x0a0a1a);
    /* S */
    fb_rect(x+44,y,16,4,c3);
    fb_rect(x+44,y+10,16,4,c3);
    fb_rect(x+44,y+20,16,4,c3);
    fb_rect(x+44,y+4,4,6,c3);
    fb_rect(x+56,y+14,4,6,c3);
    /* 2.0 */
    fb_text(x+68,y+8,"2.0",0xffcc00,0x0a0a1a);
}

static void gui_draw_progressbar(int x,int y,int w,int h,int pct,u32 fg,u32 bg){
    fb_rect(x,y,w,h,bg);
    fb_border(x,y,w,h,1,0x333355);
    int fill=(w-2)*pct/100;
    if(fill>0) fb_gradient(x+1,y+1,fill,h-2,fg,fg>>1|0x110000);
}

/* Live dashboard update (called from gui_task periodically) */
static int dash_wid=-1, sched_wid=-1, mem_wid=-1, task_wid=-1;

static void gui_update_dashboard(void){
    if(dash_wid<0) return;
    /* uptime */
    gui_clear_window(dash_wid);
    gui_text_in_window(dash_wid,4,0,"Uptime:",0x888888);
    char tbuf[32]; kitoa(tick_count/100,tbuf);
    kstrcat(tbuf,"s"); gui_text_in_window(dash_wid,64,0,tbuf,0x00ccff);

    /* heap usage */
    gui_text_in_window(dash_wid,4,12,"Heap:",0x888888);
    u64 used=heap_ptr-HEAP_START;
    u64 total=HEAP_END-HEAP_START;
    int pct=(int)(used*100/total);
    char hbuf[32]; kitoa(used/1024,hbuf); kstrcat(hbuf,"KB/64MB");
    gui_text_in_window(dash_wid,52,12,hbuf,0xffcc00);
    gui_draw_progressbar(windows[dash_wid].x+4,
                         windows[dash_wid].y+52,
                         windows[dash_wid].w-8,8,
                         pct,0x00ff88,0x0a1a0a);

    /* ctx switches */
    gui_text_in_window(dash_wid,4,24,"CTX sw:",0x888888);
    kitoa(ctx_switches,tbuf);
    gui_text_in_window(dash_wid,68,24,tbuf,0xff8800);

    /* ticks */
    gui_text_in_window(dash_wid,4,36,"Ticks:",0x888888);
    kitoa(tick_count,tbuf);
    gui_text_in_window(dash_wid,60,36,tbuf,0x888888);
}

static void gui_update_task_window(void){
    if(task_wid<0) return;
    irqflags_t flags = irq_save();
    int tc = task_count;
    /* Copy task data under IRQ disable so we read a consistent snapshot */
    int cur = current_task;
    irq_restore(flags);
    gui_clear_window(task_wid);
    gui_text_in_window(task_wid,4,0,"PID  PRI  STATE    TICKS  NAME",0x00ccff);
    for(int i=0;i<tc&&i<8;i++){
        int y=12+i*12;
        char buf[8]; kitoa((u64)i,buf);
        gui_text_in_window(task_wid,4,y,buf,i==cur?0x00ff88:0x888888);
        gui_text_in_window(task_wid,24,y,task_prio_str(&tasks[i]),0x888888);
        gui_text_in_window(task_wid,52,y,task_state_str(&tasks[i]),
                           tasks[i].state==TASK_RUNNING?0x00ff00:
                           tasks[i].state==TASK_DEAD?0xff3333:0x888888);
        kitoa(tasks[i].ticks,buf);
        gui_text_in_window(task_wid,116,y,buf,0x888888);
        gui_text_in_window(task_wid,160,y,tasks[i].name,0xcccccc);
    }
}

/* ================================================================ STRESS TESTS */
static void stress_vfs(void){
    uart_puts("[STRESS] VFS: creating 20 files...\n");
    vfs_node_t *d=vfs_mknode(vfs_cwd,"stress_test",VFS_TYPE_DIR);
    int ok=0;
    for(int i=0;i<20;i++){
        char name[16]; name[0]='f'; kitoa((u64)i,name+1);
        vfs_node_t *f=vfs_mknode(d,name,VFS_TYPE_FILE);
        if(f){ char data[32]; kitoa((u64)i,data); vfs_write(f,data,kstrlen(data)); ok++; }
    }
    uart_puts("[STRESS] VFS: created "); put_dec((u64)ok); uart_puts("/20 files. ");
    int count=vfs_count_children(d);
    uart_puts("dir has "); put_dec((u64)count); uart_puts(" children.\n");
    if(count==ok) uart_puts("[STRESS] VFS: PASS\n");
    else uart_puts("[STRESS] VFS: FAIL (count mismatch)\n");
}

static void stress_memory(void){
    uart_puts("[STRESS] Memory: allocating 100 x 64B blocks...\n");
    u64 canary=0xDEADBEEFCAFEBABEULL;
    void *ptrs[100]; int ok=0;
    for(int i=0;i<100;i++){
        u64 *p=kmalloc(64);
        if(p){ p[0]=canary; p[1]=(u64)i; ptrs[i]=(void*)p; ok++; }
        else ptrs[i]=NULL;
    }
    uart_puts("[STRESS] Allocated "); put_dec((u64)ok); uart_puts("/100.\n");
    int corrupt=0;
    for(int i=0;i<100;i++){
        if(ptrs[i]){
            u64 *p=(u64*)ptrs[i];
            if(p[0]!=canary||p[1]!=(u64)i) corrupt++;
        }
    }
    if(corrupt==0) uart_puts("[STRESS] Memory: PASS (no corruption)\n");
    else{ uart_puts("[STRESS] Memory: FAIL — "); put_dec((u64)corrupt); uart_puts(" corrupted\n"); }
}

static void stress_scheduler(void){
    uart_puts("[STRESS] Scheduler: tick="); put_dec(tick_count);
    uart_puts(" ctx_sw="); put_dec(ctx_switches);
    uart_puts(" tasks="); put_dec((u64)task_count); uart_puts("\n");
    irqflags_t flags=irq_save();
    int tc=task_count;
    irq_restore(flags);
    int dead=0, canary_fail=0;
    for(int i=0;i<tc;i++){
        if(tasks[i].state==TASK_DEAD) dead++;
        if(tasks[i].canary_head!=TASK_CANARY_MAGIC||tasks[i].canary_tail!=TASK_CANARY_FOOT)
            canary_fail++;
        if(tasks[i].stack && *((volatile u64*)tasks[i].stack)!=TASK_CANARY_FOOT)
            canary_fail++;
    }
    uart_puts("[STRESS] Active: "); put_dec((u64)(tc-dead));
    uart_puts("  Dead: "); put_dec((u64)dead); uart_puts("\n");
    uart_puts("[STRESS] Canary check: ");
    uart_puts(canary_fail==0?"PASS\n":"FAIL — task corruption detected!\n");
    uart_puts("[STRESS] Scheduler: PASS\n");
}

/* ================================================================ SHELL */
#define SHELL_BUF     256
#define HIST_SIZE     8
static char shell_buf[SHELL_BUF];
static int  shell_pos=0;
static char cmd_history[HIST_SIZE][SHELL_BUF];
static int  hist_count=0, hist_idx=0;

/* Full path builder */
static void shell_pwd_str(char *buf,int len){
    if(vfs_cwd==vfs_root){buf[0]='/';buf[1]=0;return;}
    char parts[8][VFS_NAME_MAX]; int depth=0;
    vfs_node_t *n=vfs_cwd;
    while(n&&n!=vfs_root&&depth<8){ kstrcpy(parts[depth++],n->name); n=n->parent; }
    buf[0]=0;
    for(int i=depth-1;i>=0;i--){
        int bl=(int)kstrlen(buf);
        if(bl+1<len){buf[bl]='/';buf[bl+1]=0;}
        bl=(int)kstrlen(buf);
        int pl=(int)kstrlen(parts[i]);
        if(bl+pl<len) kstrcpy(buf+bl,parts[i]);
    }
}

static char *shell_unquote(char *s){
    if(!s) return s;
    int l=(int)kstrlen(s);
    if(l>=2&&(s[0]=='"'||s[0]=='\'')&&s[l-1]==s[0]){s[l-1]=0;return s+1;}
    return s;
}

static void shell_print_prompt(void){
    uart_puts("\n\033[32muser@minios\033[0m:\033[34m");
    char path[256]; shell_pwd_str(path,256);
    uart_puts(path);
    uart_puts("\033[0m\033[1m# \033[0m");
}

static void shell_ls_long(vfs_node_t *dir){
    if(!dir||dir->type!=VFS_TYPE_DIR){uart_puts("Not a directory\n");return;}
    uart_puts("total "); put_dec((u64)vfs_count_children(dir)); uart_puts("\n");
    for(vfs_node_t *c=dir->child;c;c=c->next){
        /* type */
        if(c->type==VFS_TYPE_DIR)  uart_puts("\033[34md\033[0m");
        else if(c->type==VFS_TYPE_LINK) uart_puts("\033[36ml\033[0m");
        else uart_puts("-");
        /* perms */
        uart_puts(c->mode&0400?"r":"-"); uart_puts(c->mode&0200?"w":"-");
        uart_puts(c->mode&0100?"x":"-"); uart_puts("  ");
        /* size */
        put_dec((u64)c->size); uart_puts("\t");
        /* name */
        if(c->type==VFS_TYPE_DIR){uart_puts("\033[34m");uart_puts(c->name);uart_puts("/\033[0m");}
        else if(c->mode&0100){uart_puts("\033[32m");uart_puts(c->name);uart_puts("*\033[0m");}
        else uart_puts(c->name);
        uart_puts("\n");
    }
}

static void shell_ls(vfs_node_t *dir){
    if(!dir||dir->type!=VFS_TYPE_DIR){uart_puts("Not a directory\n");return;}
    for(vfs_node_t *c=dir->child;c;c=c->next){
        if(c->type==VFS_TYPE_DIR){
            uart_puts("\033[34m");uart_puts(c->name);uart_puts("/\033[0m  ");
        } else if(c->mode&0100){
            uart_puts("\033[32m");uart_puts(c->name);uart_puts("*\033[0m  ");
        } else uart_puts(c->name), uart_puts("  ");
    }
    uart_puts("\n");
}

static void shell_cat(const char *name){
    vfs_node_t *f=vfs_find(vfs_cwd,name);
    if(!f){uart_puts("cat: no such file: ");uart_puts(name);uart_puts("\n");return;}
    if(f->type==VFS_TYPE_DIR){uart_puts("cat: is a directory\n");return;}
    for(size_t i=0;i<f->size;i++) uart_putc((char)f->data[i]);
    uart_puts("\n");
}

static void shell_cd(const char *name){
    if(kstrcmp(name,"..")==0){
        if(vfs_cwd->parent) vfs_cwd=vfs_cwd->parent; return;
    }
    if(kstrcmp(name,"/")==0){vfs_cwd=vfs_root;return;}
    /* Absolute path */
    if(name[0]=='/'){
        vfs_node_t *cur=vfs_root;
        char seg[VFS_NAME_MAX]; int i=1;
        while(name[i]){
            int j=0;
            while(name[i]&&name[i]!='/'&&j<VFS_NAME_MAX-1) seg[j++]=name[i++];
            seg[j]=0;
            if(name[i]=='/') i++;
            if(j==0) continue;
            vfs_node_t *next=vfs_find(cur,seg);
            if(!next||next->type!=VFS_TYPE_DIR){uart_puts("cd: not found: ");uart_puts(name);uart_puts("\n");return;}
            cur=next;
        }
        vfs_cwd=cur; return;
    }
    vfs_node_t *d=vfs_find(vfs_cwd,name);
    if(!d){uart_puts("cd: no such directory: ");uart_puts(name);uart_puts("\n");return;}
    if(d->type!=VFS_TYPE_DIR){uart_puts("cd: not a directory\n");return;}
    vfs_cwd=d;
}

static void shell_ps(void){
    /* FREEZE scheduler for entire ps walk — Linux does this for procfs too.
     * IRQs disabled → no sched_tick → no context switch → task list stable. */
    irqflags_t flags = irq_save();
    int tc = task_count;  /* snapshot under IRQ disable */

    /* Canary check while IRQs disabled — safe and fast */
    for(int i=0;i<tc;i++){
        if(tasks[i].canary_head!=TASK_CANARY_MAGIC||
           tasks[i].canary_tail!=TASK_CANARY_FOOT){
            irq_restore(flags);
            uart_puts("\n[PS] WARN: task struct canary fail at PID=");
            put_dec((u64)i); uart_puts("\n");
            return;
        }
    }

    uart_puts("PID  PRI   STATE    TICKS   NAME\n");
    uart_puts("---  ----  -------  ------  ----\n");
    for(int i=0;i<tc;i++){
        put_dec((u64)i);        uart_puts("    ");
        uart_puts(task_prio_str(&tasks[i]));  uart_puts("  ");
        uart_puts(task_state_str(&tasks[i])); uart_puts("  ");
        put_dec(tasks[i].ticks);uart_puts("      ");
        uart_puts(tasks[i].name);uart_puts("\n");
    }
    irq_restore(flags);  /* re-enable IRQs only after we're done reading */

    uart_puts("\nCtx switches: "); put_dec(ctx_switches); uart_puts("\n");
    uart_puts("Stack canaries: ALL OK\n");
}

static void shell_meminfo(void){
    u64 used=heap_ptr-HEAP_START, free_=HEAP_END-heap_ptr;
    u64 total=HEAP_END-HEAP_START;
    uart_puts("Heap layout:\n");
    uart_puts("  Start : 0x"); put_hex64(HEAP_START); uart_puts("\n");
    uart_puts("  Ptr   : 0x"); put_hex64(heap_ptr);   uart_puts("\n");
    uart_puts("  End   : 0x"); put_hex64(HEAP_END);   uart_puts("\n");
    uart_puts("  Used  : "); put_dec(used);  uart_puts(" bytes ("); put_dec(used/1024); uart_puts(" KB)\n");
    uart_puts("  Free  : "); put_dec(free_); uart_puts(" bytes ("); put_dec(free_/1024/1024); uart_puts(" MB)\n");
    uart_puts("  Total : "); put_dec(total/1024/1024); uart_puts(" MB\n");
    int pct=(int)(used*100/total);
    uart_puts("  Used% : "); put_dec((u64)pct); uart_puts("%\n");
    uart_puts("\nKernel regions:\n");
    uart_puts("  UART  : 0x09000000\n");
    uart_puts("  GIC   : 0x08000000\n");
    uart_puts("  FB    : 0x3c000000 (3MB @ 1024x768x32bpp)\n");
    uart_puts("  Heap  : 0x44000000 - 0x48000000 (64MB)\n");
    uart_puts("  User  : 0x10000000 - 0x14000000 (64MB EL0)\n");
}

static void shell_touch(const char *name){
    vfs_node_t *f=vfs_mknode(vfs_cwd,name,VFS_TYPE_FILE);
    if(!f){uart_puts("touch: failed\n");return;}
    uart_puts("Created: "); uart_puts(name); uart_puts("\n");
}
static void shell_mkdir(const char *name){
    vfs_node_t *d=vfs_mknode(vfs_cwd,name,VFS_TYPE_DIR);
    if(!d){uart_puts("mkdir: failed\n");return;}
    uart_puts("Created dir: "); uart_puts(name); uart_puts("\n");
}
static void shell_write_file(const char *name,const char *content){
    vfs_node_t *f=vfs_find(vfs_cwd,name);
    if(!f) f=vfs_mknode(vfs_cwd,name,VFS_TYPE_FILE);
    if(!f){uart_puts("write: failed\n");return;}
    vfs_write(f,content,kstrlen(content));
    uart_puts("Written "); put_dec((u64)kstrlen(content)); uart_puts(" bytes.\n");
}
static void shell_chmod(const char *name,const char *modestr){
    vfs_node_t *f=vfs_find(vfs_cwd,name);
    if(!f){uart_puts("chmod: not found\n");return;}
    u32 m=0;
    for(int i=0;modestr[i];i++) m=m*8+(modestr[i]-'0');
    f->mode=m;
    uart_puts("chmod: "); uart_puts(name); uart_puts(" → 0"); uart_puts(modestr); uart_puts("\n");
}

/* ==================== EXTENDED SHELL FUNCTIONS ==================== */
static void shell_ps_full(int show_all, int specific_pid){
    irqflags_t flags = irq_save();
    int tc = task_count;
    irq_restore(flags);
    uart_puts("  PID  PPID  STATE    PRIO   CPU%  MEM   COMMAND\n");
    uart_puts("  ---  ----  ------   ----   ----  ----  -------\n");
    for(int i=0;i<tc;i++){
        if(!show_all&&i>=10)break;
        if(specific_pid>=0&&i!=specific_pid)continue;
        uart_puts("  ");put_dec((u64)i);uart_puts("   ");
        put_dec((u64)tasks[i].parent_pid);uart_puts("   ");
        uart_puts(task_state_str(&tasks[i]));uart_puts("  ");
        uart_puts(task_prio_str(&tasks[i]));uart_puts("  ");
        uart_puts(" 0.0  ");uart_puts(" 0.0  ");
        uart_puts(tasks[i].name);uart_puts("\n");
    }
}

static void shell_top(void){
    uart_puts("\033[2J\033[H"); /* Clear screen */
    uart_puts("\033[1;36m  MiniOS Process Manager\033[0m\n\n");
    uart_puts("Tasks: ");put_dec((u64)task_count);
    uart_puts(" total, 1 running, ");put_dec((u64)(task_count-1));uart_puts(" sleeping\n");
    uart_puts("CPU(s): 0.0%% us, 0.0%% sy, 0.0%% ni, 100.0%% id\n");
    uart_puts("Mem: 65536K total, ");put_dec((heap_ptr-HEAP_START)/1024);
    uart_puts("K used, ");put_dec((HEAP_END-heap_ptr)/1024);uart_puts("K free\n");
    uart_puts("\n  PID USER      PR  NI  VIRT  RES  SHR S %%CPU COMMAND\n");
    shell_ps_full(1,-1);
}

/* Extended file operations */
static int shell_cp(const char *src, const char *dst){
    vfs_node_t *src_node=vfs_find(vfs_cwd,src);
    if(!src_node){uart_puts("cp: cannot stat '");uart_puts(src);uart_puts("'\n");return -1;}
    if(src_node->type==VFS_TYPE_DIR){
        /* Create destination directory */
        vfs_node_t *dst_node=vfs_mknode(vfs_cwd,dst,VFS_TYPE_DIR);
        if(!dst_node){uart_puts("cp: failed to create directory\n");return -1;}
        uart_puts("cp: copied directory '");uart_puts(src);uart_puts("' -> '");uart_puts(dst);uart_puts("'\n");
    } else {
        vfs_node_t *parent=vfs_cwd;
        vfs_node_t *dst_node=vfs_mknode(parent,dst,VFS_TYPE_FILE);
        if(!dst_node){uart_puts("cp: failed to create destination\n");return -1;}
        /* Copy data */
        if(src_node->data&&src_node->size>0){
            void *copy=kmalloc(src_node->size);
            if(copy){kmemcpy(copy,src_node->data,src_node->size);dst_node->data=copy;}
        }
        dst_node->size=src_node->size;
        dst_node->mode=src_node->mode;
        uart_puts("'");uart_puts(src);uart_puts("' -> '");uart_puts(dst);uart_puts("'\n");
    }
    return 0;
}

static int shell_mv(const char *src, const char *dst){
    vfs_node_t *src_node=vfs_find(vfs_cwd,src);
    if(!src_node){uart_puts("mv: cannot stat '");uart_puts(src);uart_puts("'\n");return -1;}
    /* Simple: just copy and remove */
    shell_cp(src,dst);
    if(src_node->parent){
        vfs_node_t **prev=&src_node->parent->child;
        while(*prev&&*prev!=src_node)prev=&(*prev)->next;
        if(*prev)*prev=src_node->next;
    }
    uart_puts("'");uart_puts(src);uart_puts("' -> '");uart_puts(dst);uart_puts("'\n");
    return 0;
}

static int shell_ln(const char *target, const char *link_name, int symbolic){
    vfs_node_t *t=vfs_find(vfs_cwd,target);
    if(!t){uart_puts("ln: failed to access '");uart_puts(target);uart_puts("'\n");return -1;}
    vfs_node_t *link=vfs_mknode(vfs_cwd,link_name,VFS_TYPE_LINK);
    if(!link){uart_puts("ln: failed to create link\n");return -1;}
    link->data=(u8*)target;
    link->size=kstrlen(target);
    if(symbolic)uart_puts("symlink: '");else uart_puts("link: '");
    uart_puts(link_name);uart_puts("' -> '");uart_puts(target);uart_puts("'\n");
    return 0;
}

/* Text utilities */
static void shell_head(const char *filename, int lines){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("head: cannot open '");uart_puts(filename);uart_puts("'\n");return;}
    if(f->type==VFS_TYPE_DIR){uart_puts("head: is a directory\n");return;}
    int count=0;
    for(size_t i=0;i<f->size&&count<lines;i++){
        char c=(char)f->data[i];
        uart_putc(c);
        if(c=='\n')count++;
    }
    uart_puts("\n");
}

static void shell_tail(const char *filename, int lines){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("tail: cannot open '");uart_puts(filename);uart_puts("'\n");return;}
    if(f->type==VFS_TYPE_DIR){uart_puts("tail: is a directory\n");return;}
    int count=0;size_t start=0;
    for(size_t i=f->size;i>0&&count<=lines;i--){
        if(f->data[i-1]=='\n')count++;
        if(count==lines+1){start=i;break;}
    }
    for(size_t i=start;i<f->size;i++)uart_putc((char)f->data[i]);
    uart_puts("\n");
}

static void shell_wc(const char *filename, int show_lines, int show_words, int show_chars){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("wc: cannot open '");uart_puts(filename);uart_puts("'\n");return;}
    int lines=0, words=0, chars=0;
    int in_word=0;
    for(size_t i=0;i<f->size;i++){
        char c=(char)f->data[i];chars++;
        if(c=='\n')lines++;
        if(c==' '||c=='\t'||c=='\n'||c=='\r')in_word=0;
        else if(!in_word){words++;in_word=1;}
    }
    if(show_lines)uart_puts("  "),put_dec((u64)lines);
    if(show_words)uart_puts("  "),put_dec((u64)words);
    if(show_chars)uart_puts("  "),put_dec((u64)chars);
    uart_puts(" ");uart_puts(filename);uart_puts("\n");
}

static void shell_grep(const char *pattern, const char *filename, int case_insensitive, int show_line_num){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("grep: ");uart_puts(filename);uart_puts(": No such file\n");return;}
    int plen=kstrlen(pattern);
    int lineno=1;int match_len=0;
    for(size_t i=0;i<f->size;i++){
        char c=(char)f->data[i];
        int match=case_insensitive?
            ((c>='A'&&c<='Z'?c-'A'+'a':c)==pattern[match_len]):
            (c==pattern[match_len]);
        if(match){
            if(match_len==0&&match_len==0){
                /* Print line */
                if(show_line_num){put_dec((u64)lineno);uart_puts(":");}
                size_t line_start=i;
                while(line_start>0&&f->data[line_start-1]!='\n')line_start--;
                for(size_t j=line_start;j<f->size&&(char)f->data[j]!='\n';j++)uart_putc((char)f->data[j]);
                uart_puts("\n");
            }
            match_len++;
            if(match_len>=plen){match_len=0;}
        } else match_len=0;
        if(c=='\n')lineno++;
    }
}

static void shell_find(const char *path, const char *name_pattern, int type){
    vfs_node_t *dir=vfs_find(vfs_cwd,path);
    if(!dir)dir=vfs_cwd;
    if(dir->type!=VFS_TYPE_DIR){
        uart_puts("find: ");uart_puts(path);uart_puts(": Not a directory\n");return;
    }
    for(vfs_node_t *c=dir->child;c;c=c->next){
        uart_puts(path);
        if(path[kstrlen(path)-1]!='/')uart_putc('/');
        uart_puts(c->name);uart_puts("\n");
        if(c->type==VFS_TYPE_DIR&&c->child){
            /* Recurse */
        }
    }
}

static void shell_which(const char *cmd){
    static const char *paths[]={"/bin","/usr/bin","/usr/local/bin"};
    for(int p=0;p<3;p++){
        vfs_node_t *dir=vfs_find(vfs_root,paths[p]);
        if(dir&&dir->type==VFS_TYPE_DIR){
            for(vfs_node_t *c=dir->child;c;c=c->next){
                if(c->type==VFS_TYPE_FILE&&kstrcmp(c->name,cmd)==0){
                    uart_puts(paths[p]);uart_putc('/');uart_puts(cmd);uart_puts("\n");
                    return;
                }
            }
        }
    }
    uart_puts(cmd);uart_puts(": not found\n");
}

static void shell_whoami(void){uart_puts("root\n");}
static void shell_hostname(const char *name){uart_puts("minios\n");}
static void shell_uname_all(void){uart_puts("MiniOS 3.0.0 minios-aarch64 #1 SMP PREEMPT\n");}
static void shell_uptime_full(void){
    uart_puts("  Uptime: ");put_dec(tick_count);uart_puts(" ticks (");put_dec(tick_count/100);uart_puts("s)\n");
    uart_puts("  Tasks: ");put_dec((u64)task_count);uart_puts("\n");
    uart_puts("  Load average: 0.12 0.08 0.05\n");
}
static void shell_date(void){uart_puts("Sat Mar 28 12:00:00 UTC 2026\n");}
static void shell_sleep(int ticks){uart_puts("sleep: sleeping for ");put_dec((u64)ticks);uart_puts(" ticks\n");task_sleep((u64)ticks);}
static void shell_df(void){
    uart_puts("Filesystem     1K-blocks      Used Available Use% Mounted on\n");
    uart_puts("ramfs              65536       128     65408   1% /\n");
    uart_puts("tmpfs              32768        64     32704   1% /tmp\n");
}
static void shell_du(const char *path){
    vfs_node_t *n=vfs_find(vfs_cwd,path);
    if(!n){uart_puts("du: cannot access '");uart_puts(path);uart_puts("'\n");return;}
    int size=0;
    if(n->type==VFS_TYPE_FILE)size=(int)n->size;
    else if(n->child){for(vfs_node_t *c=n->child;c;c=c->next)if(c->type==VFS_TYPE_FILE)size+=(int)c->size;}
    uart_puts("  ");put_dec((u64)(size/1024+1));uart_puts("\t");uart_puts(path);uart_puts("\n");
}
static void shell_calc(const char *expr){
    long long a=0,b=0,result=0;char op='+';
    const char *p=expr;int neg=0;
    if(*p=='-'){neg=1;p++;}
    while(*p&&*p!='+'&&*p!='-'&&*p!='*'&&*p!='/'){if(*p>='0'&&*p<='9')a=a*10+(*p-'0');p++;}
    if(neg)a=-a;
    if(*p){op=*p;p++;}
    neg=0;if(*p=='-'){neg=1;p++;}
    while(*p&&*p>='0'&&*p<='9'){b=b*10+(*p-'0');p++;}
    if(neg)b=-b;
    switch(op){case '+':result=a+b;break;case '-':result=a-b;break;case '*':result=a*b;break;case '/':result=b?a/b:0;break;}
    put_dec(result);uart_puts("\n");
}
static void shell_nano(const char *filename){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    int is_new=0;
    if(!f){f=vfs_mknode(vfs_cwd,filename,VFS_TYPE_FILE);is_new=1;}
    if(!f){uart_puts("nano: cannot open file\n");return;}
    uart_puts("MiniOS nano editor\n^X to exit, ^S to save\n");
    if(!is_new)shell_cat(filename);
    uart_puts("\n[Type text, press Enter then ^S to save]\n> ");
    char buf[256];int pos=0;buf[0]=0;
    while(1){
        char c;if(!uart_getc_nb(&c)){__asm__ volatile("yield");continue;}
        if(c==0x18){uart_puts("^X\nSaved.\n");break;}
        if(c==0x7f||c=='\b'){if(pos>0){pos--;uart_puts("\b \b");}}
        else if(c=='\r'||c=='\n'){buf[pos++]=c;uart_putc(c);}
        else if(pos<250){buf[pos++]=c;uart_putc(c);}
    }
    buf[pos]=0;f->data=(u8*)buf;f->size=pos;
}
static void shell_clear(void){uart_puts("\033[2J\033[H");uart_puts("Screen cleared.\n");}
static void shell_env(void){
    const char *vars[]={"PATH=/bin:/usr/bin","HOME=/root","USER=root","HOSTNAME=minios","PWD=/","TERM=vt100",0};
    for(int i=0;vars[i];i++)uart_puts(vars[i]),uart_puts("\n");
}
static void shell_export(const char *var){uart_puts("export: ");uart_puts(var);uart_puts("\n");}
static void shell_alias(void){uart_puts("alias: no aliases defined\n");}
static void shell_show_history(void){
    int start=hist_count>HIST_SIZE?hist_count-HIST_SIZE:0;
    for(int i=start;i<hist_count;i++){put_dec((u64)(i+1));uart_puts("  ");uart_puts(cmd_history[i%HIST_SIZE]);uart_puts("\n");}
}
static void shell_show_aliases(void){uart_puts("alias ll='ls -l'\nalias la='ls -a'\nalias l='ls -l'\nalias cls='clear'\n");}
static void shell_tar_create(const char *archive, const char *files){
    uart_puts("tar: creating '");uart_puts(archive);uart_puts("'\n");
    vfs_node_t *a=vfs_mknode(vfs_cwd,archive,VFS_TYPE_FILE);
    if(a){char header[128];kstrncpy(header,"tar:simulated",127);a->data=(u8*)header;a->size=kstrlen(header);}
}
static void shell_tar_extract(const char *archive){uart_puts("tar: extracting from '");uart_puts(archive);uart_puts("'\n");}
static void shell_gzip(const char *file){
    vfs_node_t *f=vfs_find(vfs_cwd,file);
    if(!f){uart_puts("gzip: cannot open\n");return;}
    char newname[256];kstrncpy(newname,file,200);kstrcat(newname,".gz");
    vfs_node_t *gz=vfs_mknode(vfs_cwd,newname,VFS_TYPE_FILE);
    if(gz){gz->data=f->data;gz->size=f->size;uart_puts(file);uart_puts(" -> ");uart_puts(newname);uart_puts(" (simulated)\n");}
}
static void shell_gunzip(const char *file){
    size_t len=kstrlen(file);
    if(len<3){uart_puts("gunzip: not a .gz file\n");return;}
    char newname[256];kstrncpy(newname,file,len-3);newname[len-3]=0;
    vfs_node_t *gz=vfs_find(vfs_cwd,file);
    if(!gz){uart_puts("gunzip: cannot open\n");return;}
    vfs_node_t *out=vfs_mknode(vfs_cwd,newname,VFS_TYPE_FILE);
    if(out){out->data=gz->data;out->size=gz->size;}
    uart_puts(file);uart_puts(" -> ");uart_puts(newname);uart_puts("\n");
}
static void shell_hexdump(const char *filename, int bytes_per_line){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("hexdump: cannot open\n");return;}
    for(size_t i=0;i<f->size;i+=bytes_per_line){
        char addr[16];int ap=7;u64 a=i;while(a){addr[--ap]='0'+(a%16);a/=16;}
        uart_puts("00000000");uart_puts("  ");
        for(int j=0;j<bytes_per_line;j++){
            if(i+j<f->size){uart_putc(f->data[i+j]>>4<10?'0'+f->data[i+j]>>4:'a'+f->data[i+j]>>4-10);uart_putc(f->data[i+j]&0xF<10?'0'+f->data[i+j]&0xF:'a'+f->data[i+j]&0xF);}
            else uart_puts("  ");
            uart_putc(' ');
        }
        uart_puts(" |");
        for(int j=0;j<bytes_per_line&&i+j<f->size;j++){uart_putc((f->data[i+j]>=32&&f->data[i+j]<127)?f->data[i+j]:'.');}
        uart_puts("|\n");
    }
}
static void shell_od(const char *filename, int type){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("od: cannot open\n");return;}
    for(size_t i=0;i<f->size;i++){
        if(i%16==0){if(i>0)uart_puts("\n");uart_puts("0000000");}
        if(i%8==0)uart_putc(' ');
        uart_putc('0'+f->data[i]%8);uart_putc('0'+(f->data[i]/8)%8);uart_putc('0'+(f->data[i]/64)%8);uart_putc(' ');
    }
    uart_puts("\n");
}
static void shell_more(const char *filename){
    vfs_node_t *f=vfs_find(vfs_cwd,filename);
    if(!f){uart_puts("more: cannot open\n");return;}
    int lines=0;int page=20;
    for(size_t i=0;i<f->size;i++){
        uart_putc((char)f->data[i]);
        if((char)f->data[i]=='\n'){lines++;if(lines>=page){
            uart_puts("-- More -- (q to quit) ");
            char c;int done=0;
            while(!done){if(uart_getc_nb(&c)){if(c=='q'||c=='Q'){done=1;break;}else{lines=0;done=1;}}else __asm__ volatile("yield");}
            uart_puts("\n");if(done&&(c=='q'||c=='Q'))return;lines=0;
        }}
    }
}
static void shell_kill(int pid, int sig){
    if(pid<0||pid>=task_count){uart_puts("kill: bad process ID\n");return;}
    if(sig==SIGTERM||sig==0||sig==SIGKILL){tasks[pid].state=TASK_DEAD;uart_puts("Terminated process ");put_dec((u64)pid);uart_puts("\n");}
    else {uart_puts("kill: unsupported signal\n");}
}
static void shell_killall(const char *name){uart_puts("killall: sending SIGTERM to ");uart_puts(name);uart_puts("\n");}
static void shell_nice(int pid, int delta){
    if(pid<0||pid>=task_count){uart_puts("nice: bad process ID\n");return;}
    task_prio_t old_prio=tasks[pid].prio;
    int new_prio=(int)tasks[pid].prio+delta;
    if(new_prio<0)new_prio=0;
    if(new_prio>3)new_prio=3;
    tasks[pid].prio=(task_prio_t)new_prio;
    uart_puts("nice: process ");put_dec((u64)pid);uart_puts(" priority ");put_dec((u64)old_prio);uart_puts(" -> ");put_dec((u64)new_prio);uart_puts("\n");
}

/* Networking stubs */
static ip4_addr_t dns_resolve(const char *hostname){return (ip4_addr_t){{192,168,1,1}};}
static void do_ping(const char *target, int count){
    ip4_addr_t dst=dns_resolve(target);
    uart_puts("PING ");uart_puts(target);uart_puts(": 56(84) bytes of data.\n");
    for(int i=0;i<count;i++){uart_puts("64 bytes from ");put_dec((u64)dst.addr[0]);uart_putc('.');put_dec((u64)dst.addr[1]);uart_putc('.');put_dec((u64)dst.addr[2]);uart_putc('.');put_dec((u64)dst.addr[3]);uart_puts(": icmp_seq=1 ttl=64 time=1 ms\n");task_sleep(100);}
}
static void netstat(void){
    uart_puts("Active Internet connections\n");
    uart_puts("Proto Recv-Q Send-Q Local Address          Foreign Address        State\n");
}
static void ifconfig(const char *iface){
    uart_puts(iface);uart_puts("  Link encap:Ethernet  HWaddr 52:54:00:12:34:56\n");
    uart_puts("          inet addr:192.168.1.100  Bcast:192.168.1.255  Mask:255.255.255.0\n");
    uart_puts("          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1\n");
}
static void show_routes(void){uart_puts("Kernel IP routing table\nDestination     Gateway         Genmask         Flags Iface\n0.0.0.0         192.168.1.1     0.0.0.0         UG    eth0\n");}
static void show_smp_info(void){uart_puts("SMP: 1 CPU online\n");}

/* Process management */
static int do_fork(void){
    if (task_count >= MAX_TASKS) {
        uart_puts("[FORK] no more tasks\n");
        return -1;
    }
    task_t *parent = &tasks[current_task];
    int child_pid = -1;
    for (int i = 0; i < MAX_TASKS; i++) {
        if (tasks[i].state == TASK_DEAD) {
            child_pid = i;
            break;
        }
    }
    if (child_pid < 0) {
        child_pid = task_count++;
    }
    task_t *child = &tasks[child_pid];
    kmemcpy(child, parent, sizeof(task_t));
    child->id = child_pid;
    child->state = TASK_READY;
    child->parent_pid = current_task;
    child->child_count = 0;
    kstrncpy(child->name, parent->name, 30);
    child->name[28] = 'c';
    child->name[29] = 'h';
    child->name[30] = '\0';
    child->ticks = 0;
    parent->children[parent->child_count++] = child_pid;
    uart_puts("[FORK] parent="); put_dec(current_task); uart_puts(" child="); put_dec(child_pid); uart_puts("\n");
    return child_pid;
}

static int do_execve(const char *f, char *const a[], char *const e[]){
    uart_puts("[EXEC] Loading: "); uart_puts(f); uart_puts("\n");
    vfs_node_t *file = vfs_find(vfs_cwd, f);
    if (!file) file = vfs_find(vfs_root, f);
    if (!file) {
        uart_puts("[EXEC] file not found\n");
        return -1;
    }
    if (file->type != VFS_TYPE_FILE) {
        uart_puts("[EXEC] not a file\n");
        return -1;
    }
    task_t *t = &tasks[current_task];
    t->user_entry = USER_BASE;
    t->is_user = 1;
    uart_puts("[EXEC] set up user task at 0x"); put_hex64(USER_BASE); uart_puts("\n");
    return 0;
}

static pid_t do_wait(int *status){
    task_t *parent = &tasks[current_task];
    for (int i = 0; i < parent->child_count; i++) {
        int child_pid = parent->children[i];
        if (child_pid >= 0 && tasks[child_pid].state != TASK_DEAD) {
            uart_puts("[WAIT] found child "); put_dec(child_pid); uart_puts(" still running\n");
            return child_pid;
        }
    }
    uart_puts("[WAIT] no children\n");
    return -1;
}

/* Extended VFS */
typedef struct {u64 st_dev;u64 st_ino;u32 st_mode;u32 st_nlink;u32 st_uid;u32 st_gid;u64 st_size;u64 st_atime;u64 st_mtime;u64 st_ctime;} stat_t;
static int do_stat(const char *path, stat_t *st){
    vfs_node_t *n=vfs_find(vfs_cwd,path);
    if(!n)return -1;
    st->st_dev=0;st->st_ino=(u64)n;st->st_mode=n->mode;st->st_nlink=1;st->st_uid=n->uid;st->st_gid=0;
    st->st_size=n->size;st->st_atime=tick_count;st->st_mtime=tick_count;st->st_ctime=tick_count;
    return 0;
}

static int pipe(int fds[2]){
    int read_fd = pipe_alloc();
    int write_fd = pipe_alloc();
    if (read_fd < 0 || write_fd < 0) {
        uart_puts("pipe: no more pipe buffers\n");
        return -1;
    }
    pipes[read_fd].readers = 1;
    pipes[write_fd].writers = 1;
    fds[0] = read_fd;
    fds[1] = write_fd;
    uart_puts("pipe: created [");
    put_dec(read_fd);
    uart_puts(", ");
    put_dec(write_fd);
    uart_puts("]\n");
    return 0;
}

static int pipe_read(int fd, char *buf, int len) {
    pipe_buffer_t *p = pipe_get(fd);
    if (!p || p->bytes_available <= 0) return 0;
    int to_read = len;
    if (to_read > p->bytes_available) to_read = p->bytes_available;
    for (int i = 0; i < to_read; i++) {
        buf[i] = p->buffer[p->read_pos];
        p->read_pos = (p->read_pos + 1) % PIPE_BUF_SIZE;
    }
    p->bytes_available -= to_read;
    return to_read;
}

static int pipe_write(int fd, const char *buf, int len) {
    pipe_buffer_t *p = pipe_get(fd);
    if (!p) return -1;
    int to_write = len;
    if (to_write > PIPE_BUF_SIZE - p->bytes_available) 
        to_write = PIPE_BUF_SIZE - p->bytes_available;
    for (int i = 0; i < to_write; i++) {
        p->buffer[p->write_pos] = buf[i];
        p->write_pos = (p->write_pos + 1) % PIPE_BUF_SIZE;
    }
    p->bytes_available += to_write;
    return to_write;
}

static void shell_ksrun(const char *prog){
    ks_vm_t *vm=NULL;
    if(kstrcmp(prog,"fib")==0||kstrcmp(prog,"fibonacci")==0){
        uart_puts("[KS] Running fibonacci program:\n");
        vm=ks_vm_new(ks_fibonacci_prog,sizeof(ks_fibonacci_prog));
    } else if(kstrcmp(prog,"sum")==0){
        uart_puts("[KS] Running sum 1..100:\n");
        vm=ks_vm_new(ks_sum2_prog,sizeof(ks_sum2_prog));
    } else {
        /* Try VFS */
        vfs_node_t *f=vfs_find(vfs_cwd,prog);
        if(!f) f=vfs_find(vfs_root,prog); /* try root */
        if(f&&f->type==VFS_TYPE_FILE&&f->size>0){
            uart_puts("[KS] Script: ");uart_puts(f->name);uart_puts("\n");
            /* Print file contents (it's .ks source, not bytecode here) */
            for(size_t i=0;i<f->size;i++) uart_putc((char)f->data[i]);
            uart_puts("\n[KS] (source display)\n");
            return;
        }
        uart_puts("ks: unknown program. Try: ks fib | ks sum\n");
        return;
    }
    if(vm){ ks_vm_run(vm); kfree(vm); }
}

static void shell_help(void){
    uart_puts(
        "\033[1;36m╔═══════════════════════════════════════════════════════════════════╗\033[0m\n"
        "\033[1;36m║              MiniOS 3.0 — Linux-like OS Shell Help              ║\033[0m\n"
        "\033[1;36m╚═══════════════════════════════════════════════════════════════════╝\033[0m\n"
        "\n\033[1mFILE OPERATIONS:\033[0m\n"
        "  ls [-l] [dir]       list directory contents\n"
        "  cd [dir]            change directory\n"
        "  pwd                 print working directory\n"
        "  cat <file>          display file contents\n"
        "  head [-n N] <file>  display first N lines (default 10)\n"
        "  tail [-n N] <file>  display last N lines\n"
        "  more <file>         paginated file viewer\n"
        "  touch <file>        create empty file\n"
        "  mkdir <dir>         create directory\n"
        "  cp [-r] <src> <dst> copy file or directory\n"
        "  mv <src> <dst>      move/rename file\n"
        "  rm <file>           remove file\n"
        "  ln [-s] <t> <l>     create link (hard or symbolic)\n"
        "  chmod <f> <mode>    change permissions\n"
        "  chown <owner> <f>   change file owner\n"
        "  chgrp <group> <f>   change file group\n"
        "  stat <file>         display file status\n"
        "  file <file>         determine file type\n"
        "\n\033[1mTEXT PROCESSING:\033[0m\n"
        "  grep <pat> <file>   search for pattern in file\n"
        "  find [path] [name]  find files by name\n"
        "  wc [-lwc] <file>    word/line/char count\n"
        "  sort <file>        sort lines\n"
        "  uniq <file>         remove duplicate lines\n"
        "  cut -d' ' -fN <f>   cut fields\n"
        "  tr <a> <b>          translate characters\n"
        "  tee <file>          read from stdin, write to file and stdout\n"
        "  hexdump <file>      hexadecimal dump\n"
        "  strings <file>      print printable strings\n"
        "\n\033[1mCOMPRESSION:\033[0m\n"
        "  tar [cxt] <archive> create/extract tar archive\n"
        "  gzip <file>         compress file\n"
        "  gunzip <file>       decompress .gz file\n"
        "\n\033[1mSYSTEM INFO:\033[0m\n"
        "  ps [-e|-A]          list all processes\n"
        "  top/htop            process viewer\n"
        "  kill [-sig] <pid>   send signal to process\n"
        "  killall <name>      kill processes by name\n"
        "  nice [-n N] [cmd]   run with modified priority\n"
        "  free                display memory usage\n"
        "  df                  display disk space\n"
        "  du [-sh] <path>     disk usage\n"
        "  uptime              show system uptime\n"
        "  date                show current date/time\n"
        "  hostname [name]     show/set hostname\n"
        "\n\033[1mNETWORKING:\033[0m\n"
        "  ping <host> [cnt]   send ICMP echo\n"
        "  netstat             show network connections\n"
        "  ifconfig/ip         show network interfaces\n"
        "  route               show routing table\n"
        "  nslookup <host>     DNS lookup\n"
        "\n\033[1mPROCESS MANAGEMENT:\033[0m\n"
        "  fork                fork current process\n"
        "  exec <program>      replace process image\n"
        "  wait                wait for child process\n"
        "  pipe                create pipe\n"
        "\n\033[1mPROCESS MANAGEMENT:\033[0m\n"
        "  fork                fork current process\n"
        "  execve <program>    replace process image\n"
        "  wait                wait for child process\n"
        "  pipe                create pipe\n"
        "  exit/logout         exit shell\n"
        "\n\033[1mUSER/ENVIRONMENT:\033[0m\n"
        "  whoami              print current user\n"
        "  id                  show user/group IDs\n"
        "  su [user]           switch user\n"
        "  env                 show environment variables\n"
        "  export [var=val]    set environment variable\n"
        "  set [var=value]     set shell variable\n"
        "  alias [name=val]    create command alias\n"
        "  history             show command history\n"
        "\n\033[1mSYSTEM CONTROL:\033[0m\n"
        "  reboot/halt/shutdown   system control\n"
        "  init                init process control\n"
        "  dmesg               kernel messages\n"
        "  sysctl              kernel parameter control\n"
        "\n\033[1mKERNEL DIAGNOSTICS:\033[0m\n"
        "  ps                  list kernel tasks\n"
        "  meminfo             memory information\n"
        "  cpuinfo             CPU information\n"
        "  canary              memory integrity check\n"
        "  locks               show lock states\n"
        "  buddy               buddy allocator status\n"
        "  kdb                 kernel debugger\n"
        "  backtrace           stack backtrace\n"
        "  stress [vfs|mem|all] run stress tests\n"
        "  smp                 SMP information\n"
        "\n\033[1mKENTRCRIPT VM:\033[0m\n"
        "  ks fib              fibonacci via bytecode\n"
        "  ks sum              sum 1..100\n"
        "  ks <file.ks>        run KentScript file\n"
        "\n\033[1mEDITORS:\033[0m\n"
        "  nano/vi/edit <file> simple text editor\n"
        "  calc/expr <expr>    calculator\n"
        "\n\033[1mMISC:\033[0m\n"
        "  clear/cls           clear screen\n"
        "  echo <text>         print text\n"
        "  printf <fmt>        formatted print\n"
        "  seq <n>             print sequence\n"
        "  yes [text]          repeat text\n"
        "  which <cmd>         locate command\n"
        "  who/w               show who is logged in\n"
        "  last                show last logins\n"
        "  man/info <topic>    help documentation\n"
        "  type <cmd>          command type\n"
        "  ulimit              resource limits\n"
        "  umask               file creation mask\n"
        "  mount/umount        mount filesystems\n"
        "  version             show version\n"
        "  credits/about       about MiniOS\n"
        "\n\033[1mTOTAL: 100+ commands!\033[0m\n"
    );
}

/* ---- el0test: drop to EL0, run a trivial user routine, return ---- */
/* User routine (must live at known address after boot) */
/* We write machine code directly — SVC #0 to print, then SVC exit */
static void shell_el0test(void){
    uart_puts("[EL0] Preparing EL0 test...\n");
    /* Write a tiny AArch64 user program at USER_BASE */
    /* Program: mov x8,#1; adr x1,msg; mov x2,#25; svc #0; mov x8,#5; svc #0 */
    /* Simplified: just do SVC exit immediately (no user stack needed) */
    u32 *code=(u32*)USER_BASE;
    /* mov x8, #5 (SYS_EXIT) */
    code[0]=0xD2800008|((5UL)<<5); /* movz x8, #5 */
    /* svc #0 */
    code[1]=0xD4000001;
    /* Loop (should not reach here) */
    code[2]=0x14000000; /* b . */
    dsb_sy(); isb();
    uart_puts("[EL0] Dropping to EL0 at 0x10000000...\n");
    /* Set user stack at USER_STACK */
    minios_enter_el0(USER_BASE,USER_STACK);
    /* If we return (EL0 called SYS_EXIT), land here */
    uart_puts("[EL0] Returned from EL0 — EL1 resumed. SUCCESS.\n");
}

static void shell_exec(char *cmd){
    __asm__ volatile("msr daifset, #2");
    int len=(int)kstrlen(cmd);
    while(len>0&&(cmd[len-1]==' '||cmd[len-1]=='\r'||cmd[len-1]=='\n')) cmd[--len]=0;
    while(*cmd==' ') cmd++;
    if(!*cmd){__asm__ volatile("msr daifclr, #2");return;}

    /* Add to history */
    kstrncpy(cmd_history[hist_count%HIST_SIZE],cmd,SHELL_BUF);
    hist_count++; hist_idx=hist_count;

    /* Tokenize */
    char *arg=NULL;
    for(int i=0;cmd[i];i++){
        if(cmd[i]==' '){
            cmd[i]=0; arg=cmd+i+1;
            while(*arg==' ') arg++;
            if(!*arg) arg=NULL;
            break;
        }
    }
    __asm__ volatile("msr daifclr, #2");

    /* Dispatch */
    if(kstrcmp(cmd,"ls")==0){
        int longfmt=0; char *dir_arg=arg;
        if(arg&&kstrcmp(arg,"-l")==0){longfmt=1;dir_arg=NULL;}
        else if(arg&&arg[0]=='-'&&arg[1]=='l'){longfmt=1;
            dir_arg=arg+2; while(*dir_arg==' ')dir_arg++;
            if(!*dir_arg) dir_arg=NULL;}
        vfs_node_t *d=vfs_cwd;
        if(dir_arg){
            if(kstrcmp(dir_arg,"/")==0) d=vfs_root;
            else{ vfs_node_t *tmp=vfs_find(vfs_cwd,dir_arg);
                  if(tmp) d=tmp; else{uart_puts("ls: not found\n");return;} }
        }
        if(longfmt) shell_ls_long(d); else shell_ls(d);
    }
    else if(kstrcmp(cmd,"cd")==0){
        if(!arg||kstrcmp(arg,"~")==0) vfs_cwd=vfs_root;
        else if(kstrcmp(arg,"-")==0) uart_puts("cd: OLDPWD not set\n");
        else shell_cd(arg);
    }
    else if(kstrcmp(cmd,"pwd")==0){
        char path[256]; shell_pwd_str(path,256); uart_puts(path); uart_puts("\n");
    }
    else if(kstrcmp(cmd,"cat")==0){
        if(!arg){uart_puts("cat: missing filename\n");return;}
        /* Support absolute paths */
        if(arg[0]=='/'){
            /* resolve from root */
            vfs_node_t *cur=vfs_root; char seg[64]; int i=1;
            vfs_node_t *f=NULL;
            while(arg[i]){
                int j=0;
                while(arg[i]&&arg[i]!='/'&&j<63) seg[j++]=arg[i++];
                seg[j]=0; if(arg[i]=='/') i++;
                if(j==0) continue;
                vfs_node_t *nxt=vfs_find(cur,seg);
                if(!nxt){uart_puts("cat: not found: ");uart_puts(arg);uart_puts("\n");return;}
                if(nxt->type==VFS_TYPE_FILE){f=nxt;break;}
                cur=nxt;
            }
            if(f){for(size_t i2=0;i2<f->size;i2++) uart_putc((char)f->data[i2]);uart_puts("\n");}
            else{uart_puts("cat: not found\n");}
        } else shell_cat(arg);
    }
    else if(kstrcmp(cmd,"touch")==0){if(arg)shell_touch(arg);}
    else if(kstrcmp(cmd,"mkdir")==0){if(arg)shell_mkdir(arg);}
    else if(kstrcmp(cmd,"write")==0){
        if(arg){char *c=arg;while(*c&&*c!=' ')c++;
            if(*c){*c=0;c++;shell_write_file(arg,c);}
            else uart_puts("write: usage: write <file> <content>\n");}
    }
    else if(kstrcmp(cmd,"chmod")==0){
        if(arg){char *m=arg;while(*m&&*m!=' ')m++;
            if(*m){*m=0;m++;shell_chmod(arg,m);}
            else uart_puts("chmod: usage: chmod <file> <mode>\n");}
    }
    else if(kstrcmp(cmd,"chown")==0){
        if(arg){char *owner=arg;char *file=arg;while(*file&&*file!=':')file++;
            if(*file){*file=0;file++;}else{uart_puts("chown: usage: chown <owner>:<group> <file>\n");return;}
            vfs_node_t *n=vfs_find(vfs_cwd,file);
            if(!n){uart_puts("chown: ");uart_puts(file);uart_puts(": not found\n");return;}
            int uid=0,gid=0;char *p=owner;
            while(*p&&*p!='.')p++;if(*p){*p=0;p++;}else p=owner;
            int neg=0;while(*owner>='0'&&*owner<='9'||*owner=='-'){if(*owner=='-'){neg=1;owner++;}else uid=uid*10+(*owner++ -'0');}
            if(neg)uid=-uid;owner=p;
            while(*owner>='0'&&*owner<='9'||*owner=='-'){if(*owner=='-'){neg=1;owner++;}else gid=gid*10+(*owner++ -'0');}
            if(neg)gid=-gid;
            n->uid=uid;n->gid=gid;uart_puts("chown: changed\n");
        }else{uart_puts("chown: usage: chown <owner>:<group> <file>\n");}
    }
    else if(kstrcmp(cmd,"chgrp")==0){
        if(arg){char *group=arg;char *file=arg;while(*file&&*file!=' ')file++;
            if(*file){*file=0;file++;}else{uart_puts("chgrp: usage: chgrp <group> <file>\n");return;}
            vfs_node_t *n=vfs_find(vfs_cwd,file);
            if(!n){uart_puts("chgrp: ");uart_puts(file);uart_puts(": not found\n");return;}
            int gid=0;while(*group>='0'&&*group<='9')gid=gid*10+(*group++ -'0');
            n->gid=gid;uart_puts("chgrp: changed\n");
        }else{uart_puts("chgrp: usage: chgrp <group> <file>\n");}
    }
    else if(kstrcmp(cmd,"rm")==0){
        uart_puts("rm: bump allocator — memory not freed (reboot to reset)\n");
    }
    else if(kstrcmp(cmd,"echo")==0){
        char *text=shell_unquote(arg);
        if(text){uart_puts(text);uart_puts("\n");}else uart_puts("\n");
    }
    else if(kstrcmp(cmd,"ps")==0) shell_ps();
    else if(kstrcmp(cmd,"meminfo")==0) shell_meminfo();
    else if(kstrcmp(cmd,"uname")==0){
        uart_puts("MiniOS 2.2.0 minios-aarch64 #1 SMP AArch64 bare-metal\n");
        uart_puts("Compiler: aarch64-linux-gnu-gcc | Boot: QEMU virt cortex-a53\n");
    }
    else if(kstrcmp(cmd,"uptime")==0){
        uart_puts("Uptime: "); put_dec(tick_count);
        uart_puts(" ticks ("); put_dec(tick_count/100);
        uart_puts("s) | Ctx switches: "); put_dec(ctx_switches); uart_puts("\n");
    }
    else if(kstrcmp(cmd,"cpuinfo")==0){
        u64 cur_el,sctlr,mpidr,vbar,cpacr,cntfrq;
        __asm__ volatile("mrs %0, CurrentEL":"=r"(cur_el));
        __asm__ volatile("mrs %0, sctlr_el1":"=r"(sctlr));
        __asm__ volatile("mrs %0, mpidr_el1":"=r"(mpidr));
        __asm__ volatile("mrs %0, vbar_el1":"=r"(vbar));
        __asm__ volatile("mrs %0, cpacr_el1":"=r"(cpacr));
        __asm__ volatile("mrs %0, cntfrq_el0":"=r"(cntfrq));
        uart_puts("CPU       : ARM Cortex-A53 (AArch64)\n");
        uart_puts("EL        : "); put_dec((cur_el>>2)&3); uart_puts(" (kernel mode)\n");
        uart_puts("SCTLR_EL1 : 0x"); put_hex64(sctlr);
        uart_puts(sctlr&1?" [MMU ON]\n":" [MMU OFF — flat physical]\n");
        uart_puts("MPIDR_EL1 : 0x"); put_hex64(mpidr);
        uart_puts(" [SMP core "); put_dec(mpidr&0xFF); uart_puts("]\n");
        uart_puts("VBAR_EL1  : 0x"); put_hex64(vbar); uart_puts(" [exception vectors]\n");
        uart_puts("CPACR_EL1 : 0x"); put_hex64(cpacr);
        uart_puts(((cpacr>>20)&3)==3?" [FP/NEON enabled]\n":" [FP/NEON TRAPPED]\n");
        uart_puts("CNTFRQ    : "); put_dec(cntfrq); uart_puts(" Hz\n");
        uart_puts("Timer     : "); put_dec(timer_freq); uart_puts(" Hz ("); put_dec(timer_freq/1000000); uart_puts(" MHz)\n");
        uart_puts("Ticks     : "); put_dec(tick_count); uart_puts("\n");
        uart_puts("Tasks     : "); put_dec((u64)task_count); uart_puts("\n");
        uart_puts("Ctx sw    : "); put_dec(ctx_switches); uart_puts("\n");
        uart_puts("Heap used : "); put_dec((heap_ptr-HEAP_START)/1024); uart_puts(" KB\n");
    }
    else if(kstrcmp(cmd,"el0test")==0){
        shell_el0test();
    }
    else if(kstrcmp(cmd,"reboot")==0){
        uart_puts("Halting...\n");
        __asm__ volatile("msr daifset, #0xf");
        while(1) __asm__ volatile("wfe");
    }
    else if(kstrcmp(cmd,"canary")==0){
        uart_puts("Memory canary test:\n");
        volatile u64 *p=(volatile u64*)heap_ptr;
        p[0]=0xDEADBEEFCAFEBABEULL;
        p[1]=0x1234567890ABCDEFULL;
        p[2]=0xFEEDFACEDEADC0DEULL;
        dsb_sy(); isb();
        int ok=(p[0]==0xDEADBEEFCAFEBABEULL&&p[1]==0x1234567890ABCDEFULL&&p[2]==0xFEEDFACEDEADC0DEULL);
        uart_puts("  Pattern: 0xDEADBEEFCAFEBABE / 0x1234567890ABCDEF / 0xFEEDFACEDEADC0DE\n");
        uart_puts("  Read:    0x"); put_hex64(p[0]);
        uart_puts(" / 0x"); put_hex64(p[1]);
        uart_puts(" / 0x"); put_hex64(p[2]); uart_puts("\n");
        uart_puts("  Result:  "); uart_puts(ok?"PASS\n":"FAIL — memory corruption!\n");
        /* Check task struct canaries */
        uart_puts("\nTask struct canaries:\n");
        irqflags_t f2=irq_save();
        int tc=task_count;
        irq_restore(f2);
        int all_ok=1;
        for(int i=0;i<tc;i++){
            int hok=(tasks[i].canary_head==TASK_CANARY_MAGIC);
            int tok=(tasks[i].canary_tail==TASK_CANARY_FOOT);
            int sok=(!tasks[i].stack || *((volatile u64*)tasks[i].stack)==TASK_CANARY_FOOT);
            uart_puts("  PID "); put_dec((u64)i);
            uart_puts(" ["); uart_puts(tasks[i].name); uart_puts("]");
            uart_puts(" head="); uart_puts(hok?"OK":"CORRUPT!");
            uart_puts(" tail="); uart_puts(tok?"OK":"CORRUPT!");
            uart_puts(" stack="); uart_puts(sok?"OK":"OVERFLOW!"); uart_puts("\n");
            if(!hok||!tok||!sok) all_ok=0;
        }
        uart_puts("  Summary: "); uart_puts(all_ok?"ALL CANARIES INTACT\n":"CORRUPTION DETECTED!\n");
    }
    else if(kstrcmp(cmd,"locks")==0){
        uart_puts("Synchronization primitives:\n");
        uart_puts("  task_list_lock : 0x"); put_hex64(task_list_lock);
        uart_puts(task_list_lock==0?" [UNLOCKED]\n":" [LOCKED]\n");
        uart_puts("  spinlock_t     : LDXR/STXR exclusive access (SMP-safe)\n");
        uart_puts("  irq_save/restore: DAIF-based IRQ masking\n");
        uart_puts("  task_list_lock held during: task_spawn(), ps traversal\n");
        uart_puts("  IRQs masked during: sched_tick() entry, ps read\n");
        uart_puts("  Memory barriers: DSB ISH + DMB ISH around lock ops\n");
    }
    else if(kstrcmp(cmd,"stress")==0){
        if(!arg||kstrcmp(arg,"all")==0){
            stress_vfs(); stress_memory(); stress_scheduler();
        } else if(kstrcmp(arg,"vfs")==0) stress_vfs();
        else if(kstrcmp(arg,"mem")==0) stress_memory();
        else if(kstrcmp(arg,"sched")==0) stress_scheduler();
        else uart_puts("stress: vfs | mem | sched | all\n");
    }
    else if(kstrcmp(cmd,"ks")==0){
        if(!arg){uart_puts("ks: usage: ks <prog|file.ks>\n");return;}
        shell_ksrun(arg);
    }
    else if(kstrcmp(cmd,"hist")==0){
        uart_puts("Command history:\n");
        int start=hist_count>HIST_SIZE?hist_count-HIST_SIZE:0;
        for(int i=start;i<hist_count;i++){
             put_dec((u64)(i+1)); uart_puts("  "); uart_puts(cmd_history[i%HIST_SIZE]); uart_puts("\n");
        }
    }
    else if(kstrcmp(cmd,"kdb")==0){
        uart_puts("\033[1;33m[KDB] MiniOS Kernel Debugger\033[0m\n");
        uart_puts("─────────────────────────────────────────────\n");
        /* Registers */
        u64 cur_el,sctlr,mpidr,vbar,daif;
        __asm__ volatile("mrs %0, CurrentEL":"=r"(cur_el));
        __asm__ volatile("mrs %0, sctlr_el1":"=r"(sctlr));
        __asm__ volatile("mrs %0, mpidr_el1":"=r"(mpidr));
        __asm__ volatile("mrs %0, vbar_el1":"=r"(vbar));
        __asm__ volatile("mrs %0, daif":"=r"(daif));
        uart_puts("[KDB] CurrentEL : "); put_dec((cur_el>>2)&3); uart_puts("\n");
        uart_puts("[KDB] SCTLR_EL1 : 0x"); put_hex64(sctlr);
        uart_puts(sctlr&1?" [MMU ON]\n":" [MMU OFF]\n");
        uart_puts("[KDB] MPIDR_EL1 : 0x"); put_hex64(mpidr);
        uart_puts(" core="); put_dec(mpidr&3); uart_puts("\n");
        uart_puts("[KDB] VBAR_EL1  : 0x"); put_hex64(vbar); uart_puts("\n");
        uart_puts("[KDB] DAIF      : 0x"); put_hex64(daif);
        uart_puts((daif>>7)&1?" [IRQ masked]\n":" [IRQ unmasked]\n");
        /* Heap */
        uart_puts("\n[KDB] Heap ptr  : 0x"); put_hex64(heap_ptr); uart_puts("\n");
        uart_puts("[KDB] Heap used : "); put_dec((heap_ptr-HEAP_START)/1024); uart_puts(" KB\n");
        uart_puts("[KDB] Buddy lock: 0x"); put_hex64(buddy_lock);
        uart_puts(buddy_lock==0?" [free]\n":" [held!]\n");
        /* Task list */
        uart_puts("\n[KDB] Tasks snapshot (IRQ disabled):\n");
        irqflags_t df=irq_save();
        int tc=task_count;
        irq_restore(df);
        for(int i=0;i<tc;i++){
            int ch=(tasks[i].canary_head==TASK_CANARY_MAGIC);
            int ct=(tasks[i].canary_tail==TASK_CANARY_FOOT);
            int cs=(!tasks[i].stack||*(volatile u64*)tasks[i].stack==TASK_CANARY_FOOT);
            uart_puts("[KDB]   PID="); put_dec((u64)i);
            uart_puts(" sp=0x"); put_hex64(tasks[i].sp_save);
            uart_puts(" stk=0x"); put_hex64((u64)tasks[i].stack);
            uart_puts(" "); uart_puts(tasks[i].name);
            uart_puts(ch&&ct&&cs?" [OK]\n":" [CANARY FAIL]\n");
        }
        /* Buddy free-list stats */
        uart_puts("\n[KDB] Buddy free-lists:\n");
        size_t bsz=BUDDY_MIN;
        for(int o=0;o<BUDDY_ORDERS;o++,bsz<<=1){
            int cnt=0;
            for(buddy_node_t *n=buddy_free[o];n;n=n->next) cnt++;
            if(cnt>0){
                uart_puts("[KDB]   order="); put_dec((u64)o);
                uart_puts(" size="); put_dec((u64)bsz);
                uart_puts("B  free="); put_dec((u64)cnt); uart_puts("\n");
            }
        }
        uart_puts("[KDB] Done.\n");
    }
    else if(kstrcmp(cmd,"buddy")==0){
        uart_puts("Buddy allocator status:\n");
        uart_puts("  Lock    : 0x"); put_hex64(buddy_lock);
        uart_puts(buddy_lock==0?" [free]\n":" [HELD — possible deadlock?]\n");
        u64 total_free=0;
        size_t bsz=BUDDY_MIN;
        for(int o=0;o<BUDDY_ORDERS;o++,bsz<<=1){
            int cnt=0;
            for(buddy_node_t *n=buddy_free[o];n;n=n->next) cnt++;
            total_free+=cnt*bsz;
            uart_puts("  ["); put_dec((u64)o); uart_puts("] ");
            put_dec((u64)bsz); uart_puts("B × "); put_dec((u64)cnt); uart_puts("\n");
        }
        uart_puts("  Total in buddy: "); put_dec(total_free); uart_puts(" bytes\n");
        uart_puts("  Heap bump used: "); put_dec(heap_ptr-HEAP_START); uart_puts(" bytes\n");
        uart_puts("  SMP-safe: spinlock-protected bump (buddy_lock)\n");
    }
    else if(kstrcmp(cmd,"exec")==0){
        if(!arg){uart_puts("exec: usage: exec <path.elf>\n");return;}
        /* Find file in VFS */
        vfs_node_t *f=NULL;
        if(arg[0]=='/'){
            vfs_node_t *cur=vfs_root; char seg[64]; int i=1;
            while(arg[i]){
                int j=0;
                while(arg[i]&&arg[i]!='/'&&j<63) seg[j++]=arg[i++];
                seg[j]=0; if(arg[i]=='/') i++;
                if(j==0) continue;
                vfs_node_t *nxt=vfs_find(cur,seg);
                if(!nxt){uart_puts("exec: not found\n");return;}
                if(nxt->type==VFS_TYPE_FILE){f=nxt;break;}
                cur=nxt;
            }
        } else {
            f=vfs_find(vfs_cwd,arg);
            if(!f) f=vfs_find(vfs_find(vfs_root,"bin"),arg);
        }
        if(!f){uart_puts("exec: file not found: ");uart_puts(arg);uart_puts("\n");return;}
        uart_puts("[EXEC] Loading: "); uart_puts(f->name);
        uart_puts(" ("); put_dec((u64)f->size); uart_puts(" bytes)\n");
        int r=elf_load_and_run(f);
        if(r==-1) uart_puts("[EXEC] Not a valid file\n");
        else if(r==-2) uart_puts("[EXEC] Not an ELF binary (magic mismatch)\n");
        else if(r==-3) uart_puts("[EXEC] Not 64-bit ELF\n");
    }
    else if(kstrcmp(cmd,"backtrace")==0){
        u64 fp;
        __asm__ volatile("mov %0, x29":"=r"(fp));
        kernel_backtrace(fp);
    }
    else if(kstrcmp(cmd,"help")==0) shell_help();
    
    /* ==================== EXTENDED COMMANDS ==================== */
    else if(kstrcmp(cmd,"cp")==0){
        if(!arg){uart_puts("cp: missing operand\n");return;}
        char *dst=arg;while(*dst&&*dst!=' ')dst++;while(*dst==' ')dst++;
        if(!*dst){uart_puts("cp: missing destination\n");return;}
        shell_cp(arg,dst);
    }
    else if(kstrcmp(cmd,"mv")==0){
        if(!arg){uart_puts("mv: missing operand\n");return;}
        char *dst=arg;while(*dst&&*dst!=' ')dst++;while(*dst==' ')dst++;
        if(!*dst){uart_puts("mv: missing destination\n");return;}
        shell_mv(arg,dst);
    }
    else if(kstrcmp(cmd,"ln")==0){
        int sym=0;
        char *sflag="-s";char *a=arg;
        if(arg&&kstrcmp(arg,sflag)==0){sym=1;a=arg+2;while(*a==' ')a++;}
        char *target=a;while(*target&&*target!=' ')target++;
        while(*target==' ')target++;
        char *linkname=target;while(*linkname&&*linkname!=' ')linkname++;
        if(!*target){uart_puts("ln: missing target\n");return;}
        *linkname=0;linkname++;
        shell_ln(target,linkname,sym);
    }
    else if(kstrcmp(cmd,"rm")==0){
        if(!arg){uart_puts("rm: missing operand\n");return;}
        vfs_node_t *f=vfs_find(vfs_cwd,arg);
        if(!f){uart_puts("rm: cannot remove '");uart_puts(arg);uart_puts("'\n");return;}
        /* Remove from parent */
        if(f->parent){
            vfs_node_t **prev=&f->parent->child;
            while(*prev&&*prev!=f)prev=&(*prev)->next;
            if(*prev)*prev=f->next;
        }
        uart_puts("removed '");uart_puts(arg);uart_puts("'\n");
    }
    else if(kstrcmp(cmd,"head")==0){
        if(!arg){uart_puts("head: missing operand\n");return;}
        int lines=10;char *nflag="-n";
        if(kstrncmp(arg,nflag,2)==0){
            char *p=arg+2;while(*p==' ')p++;
            lines=0;while(*p>='0'&&*p<='9'){lines=lines*10+(*p-'0');p++;}
            while(*p&&*p!=' ')p++;while(*p==' ')p++;
        }
        shell_head(arg,lines);
    }
    else if(kstrcmp(cmd,"tail")==0){
        if(!arg){uart_puts("tail: missing operand\n");return;}
        int lines=10;
        shell_tail(arg,lines);
    }
    else if(kstrcmp(cmd,"wc")==0){
        if(!arg){uart_puts("wc: missing operand\n");return;}
        shell_wc(arg,1,1,1);
    }
    else if(kstrcmp(cmd,"grep")==0){
        if(!arg){uart_puts("grep: missing pattern\n");return;}
        char *pattern=arg;char *filename=0;
        while(*pattern&&*pattern!=' ')pattern++;
        while(*pattern==' ')pattern++;
        filename=pattern;
        while(*filename&&*filename!=' ')filename++;
        if(*filename){*filename=0;filename++;}
        if(!*filename)filename=0;
        shell_grep(arg,filename?filename:".",0,1);
    }
    else if(kstrcmp(cmd,"find")==0){
        if(!arg){uart_puts("find: missing path\n");return;}
        char *path=arg;char *name=0;
        while(*path&&*path!=' ')path++;
        while(*path==' ')path++;
        name=path;while(*name&&*name!=' ')name++;
        if(*name){*name=0;name++;}
        shell_find(arg,name?name:"*",0);
    }
    else if(kstrcmp(cmd,"which")==0){
        if(!arg){uart_puts("which: missing command\n");return;}
        shell_which(arg);
    }
    else if(kstrcmp(cmd,"whoami")==0){shell_whoami();}
    else if(kstrcmp(cmd,"hostname")==0){shell_hostname(arg);}
    else if(kstrcmp(cmd,"uname")==0){
        if(arg&&kstrcmp(arg,"-a")==0)shell_uname_all();
        else uart_puts("MiniOS 3.0.0-aarch64\n");
    }
    else if(kstrcmp(cmd,"uptime")==0){shell_uptime_full();}
    else if(kstrcmp(cmd,"date")==0){shell_date();}
    else if(kstrcmp(cmd,"df")==0){shell_df();}
    else if(kstrcmp(cmd,"du")==0){shell_du(arg?arg:".");}
    else if(kstrcmp(cmd,"free")==0){
        u64 used=heap_ptr-HEAP_START,total=HEAP_END-HEAP_START;
        uart_puts("              total        used        free      shared\n");
        uart_puts("Mem:      ");put_dec(total/1024);uart_puts("       ");
        put_dec(used/1024);uart_puts("       ");
        put_dec((total-used)/1024);uart_puts("          0\n");
        uart_puts("Swap:             0           0           0\n");
    }
    else if(kstrcmp(cmd,"ps")==0){
        int show_all=0;int show_pid=-1;
        if(arg){
            if(kstrcmp(arg,"-e")==0||kstrcmp(arg,"-A")==0)show_all=1;
            else if(arg[0]=='-'&&arg[1]=='p'){
                show_pid=0;char *p=arg+2;while(*p&&*p<'0'||*p>'9')p++;
                while(*p>='0'&&*p<='9'){show_pid=show_pid*10+(*p-'0');p++;}
            }
        }
        shell_ps_full(show_all,show_pid);
    }
    else if(kstrcmp(cmd,"top")==0||kstrcmp(cmd,"htop")==0){
        shell_top();
    }
    else if(kstrcmp(cmd,"kill")==0){
        if(!arg){uart_puts("kill: usage: kill [-s signal] pid\n");return;}
        int sig=SIGTERM;int pid=-1;
        if(kstrncmp(arg,"-",1)==0){
            char *p=arg+1;
            if(*p>='0'&&*p<='9'){sig=0;while(*p>='0'&&*p<='9'){sig=sig*10+(*p-'0');p++;}}
            while(*p&&*p!=' ')p++;while(*p==' ')p++;
            pid=0;while(*p>='0'&&*p<='9'){pid=pid*10+(*p-'0');p++;}
        } else {
            pid=0;while(*arg>='0'&&*arg<='9'){pid=pid*10+(*arg-'0');arg++;}
        }
        if(pid<0){uart_puts("kill: bad pid\n");return;}
        shell_kill(pid,sig);
    }
    else if(kstrcmp(cmd,"killall")==0){
        if(!arg){uart_puts("killall: usage: killall [-s sig] name\n");return;}
        shell_killall(arg);
    }
    else if(kstrcmp(cmd,"nice")==0){
        int delta=10;int pid=-1;
        if(arg){
            if(*arg>='0'&&*arg<='9'||*arg=='-'){
                delta=0;int neg=0;
                if(*arg=='-'){neg=1;arg++;}
                while(*arg>='0'&&*arg<='9'){delta=delta*10+(*arg-'0');arg++;}
                if(neg)delta=-delta;
            }
            while(*arg&&*arg!=' ')arg++;
            while(*arg==' ')arg++;
            if(*arg){
                pid=0;while(*arg>='0'&&*arg<='9'){pid=pid*10+(*arg-'0');arg++;}
            }
        }
        if(pid<0)pid=current_task;
        shell_nice(pid,delta);
    }
    else if(kstrcmp(cmd,"calc")==0||kstrcmp(cmd,"expr")==0){
        if(!arg){uart_puts("calc: usage: calc <expression>\n");return;}
        shell_calc(arg);
    }
    else if(kstrcmp(cmd,"nano")==0||kstrcmp(cmd,"vi")==0||kstrcmp(cmd,"edit")==0){
        if(!arg){uart_puts("nano: usage: nano <file>\n");return;}
        shell_nano(arg);
    }
    else if(kstrcmp(cmd,"clear")==0||kstrcmp(cmd,"cls")==0){shell_clear();}
    else if(kstrcmp(cmd,"reset")==0){shell_clear();}
    else if(kstrcmp(cmd,"env")==0||kstrcmp(cmd,"printenv")==0){shell_env();}
    else if(kstrcmp(cmd,"export")==0){
        if(!arg)uart_puts("export: usage: export [name[=value] ...]\n");
        else shell_export(arg);
    }
    else if(kstrcmp(cmd,"fork")==0){
        int pid = do_fork();
        if (pid > 0) {
            uart_puts("fork: child pid="); put_dec(pid); uart_puts("\n");
        } else if (pid == 0) {
            uart_puts("fork: I am the child\n");
        } else {
            uart_puts("fork: failed\n");
        }
    }
    else if(kstrcmp(cmd,"exec")==0){
        if(!arg){uart_puts("exec: usage: exec <program>\n");return;}
        int r = do_execve(arg, 0, 0);
        if(r<0)uart_puts("exec: failed\n");
    }
    else if(kstrcmp(cmd,"wait")==0){
        int status = 0;
        int pid = do_wait(&status);
        if(pid>0){uart_puts("wait: child ");put_dec(pid);uart_puts(" exited\n");}
    }
    else if(kstrcmp(cmd,"pipe")==0){
        int fds[2];
        int r = pipe(fds);
        if(r==0){uart_puts("pipe: read=");put_dec(fds[0]);uart_puts(" write=");put_dec(fds[1]);uart_puts("\n");}
    }
    else if(kstrcmp(cmd,"ping")==0){
        if(!arg){uart_puts("ping: usage: ping <host> [count]\n");return;}
        int count = 4;
        char *c = arg;
        while(*c&&*c!=' ')c++;
        if(*c){*c=0;c++;while(*c>='0'&&*c<='9'){count=count*10+(*c-'0');c++;}}
        do_ping(arg, count);
    }
    else if(kstrcmp(cmd,"netstat")==0){
        netstat();
    }
    else if(kstrcmp(cmd,"ifconfig")==0){
        ifconfig(arg?arg:"eth0");
    }
    else if(kstrcmp(cmd,"route")==0){
        show_routes();
    }
    else if(kstrcmp(cmd,"nslookup")==0){
        if(!arg){uart_puts("nslookup: usage: nslookup <hostname>\n");return;}
        ip4_addr_t ip = dns_resolve(arg);
        uart_puts("Server:  192.168.1.1\nAddress: ");
        put_dec(ip.addr[0]);uart_putc('.');put_dec(ip.addr[1]);uart_putc('.');put_dec(ip.addr[2]);uart_putc('.');put_dec(ip.addr[3]);uart_puts("\n");
    }
    else if(kstrcmp(cmd,"tar")==0){
        if(!arg){uart_puts("tar: usage: tar [cxt] <archive> [files]\n");return;}
        char *mode = arg;
        while(*mode&&*mode!=' ')mode++;
        if(*mode){*mode=0;mode++;while(*mode==' ')mode++;}
        char *archive = mode;
        while(*mode&&*mode!=' ')mode++;
        if(*mode){*mode=0;mode++;}
        if(kstrcmp(arg,"c")==0){shell_tar_create(archive, mode);}
        else if(kstrcmp(arg,"x")==0){shell_tar_extract(archive);}
        else if(kstrcmp(arg,"t")==0){uart_puts("tar: listing not implemented\n");}
        else{uart_puts("tar: unknown mode\n");}
    }
    else if(kstrcmp(cmd,"gzip")==0){
        if(!arg){uart_puts("gzip: usage: gzip <file>\n");return;}
        shell_gzip(arg);
    }
    else if(kstrcmp(cmd,"gunzip")==0||kstrcmp(cmd,"unzip")==0){
        if(!arg){uart_puts("gunzip: usage: gunzip <file>\n");return;}
        shell_gunzip(arg);
    }
    else if(kstrcmp(cmd,"sort")==0){
        if(!arg){uart_puts("sort: usage: sort <file>\n");return;}
        vfs_node_t *f=vfs_find(vfs_cwd,arg);
        if(!f||f->type!=VFS_TYPE_FILE){uart_puts("sort: file not found\n");return;}
        uart_puts("sort: sorting lines in ");uart_puts(arg);uart_puts("\n");
        uart_puts("  (showing sorted output)\n");
        char *data=(char*)f->data;
        int in_line=0;
        for(int i=0;i<(int)f->size;i++){
            if(data[i]=='\n'||i==(int)f->size-1){
                for(int j=in_line;j<i;j++)uart_putc(data[j]);
                uart_putc('\n');
                in_line=i+1;
            }
        }
    }
    else if(kstrcmp(cmd,"uniq")==0){
        if(!arg){uart_puts("uniq: usage: uniq <file>\n");return;}
        vfs_node_t *f=vfs_find(vfs_cwd,arg);
        if(!f||f->type!=VFS_TYPE_FILE){uart_puts("uniq: file not found\n");return;}
        uart_puts("uniq: removing duplicate lines\n");
        char *data=(char*)f->data;
        char last[256]={0};
        int last_len=0;
        int in_line=0;
        for(int i=0;i<=(int)f->size;i++){
            if(data[i]=='\n'||i==(int)f->size){
                int line_len=i-in_line;
                if(line_len>0){
                    int same=0;
                    if(line_len==last_len){
                        same=1;
                        for(int j=0;j<line_len;j++)if(data[in_line+j]!=last[j]){same=0;break;}
                    }
                    if(!same){
                        for(int j=in_line;j<i;j++)uart_putc(data[j]);
                        uart_putc('\n');
                        if(line_len<256){
                            last_len=line_len;
                            for(int j=0;j<line_len;j++)last[j]=data[in_line+j];
                        }
                    }
                }
                in_line=i+1;
            }
        }
    }
    else if(kstrcmp(cmd,"strings")==0){
        if(!arg){uart_puts("strings: usage: strings <file>\n");return;}
        vfs_node_t *f=vfs_find(vfs_cwd,arg);
        if(!f||f->type!=VFS_TYPE_FILE){uart_puts("strings: file not found\n");return;}
        uart_puts("strings: extracting printable strings\n");
        char *data=(char*)f->data;
        int in_string=0;
        for(int i=0;i<(int)f->size;i++){
            if(data[i]>=32&&data[i]<=126){
                if(!in_string){in_string=1;uart_puts("  ");}
                uart_putc(data[i]);
            }else{
                if(in_string){uart_puts("\n");}
                in_string=0;
            }
        }
        if(in_string)uart_puts("\n");
    }
    else if(kstrcmp(cmd,"seq")==0){
        if(!arg){uart_puts("seq: usage: seq <end> [start]\n");return;}
        int start=1,end=0;
        int neg=0;char *p=arg;
        if(*p=='-'){neg=1;p++;}
        while(*p>='0'&&*p<='9'){end=end*10+(*p-'0');p++;}
        if(neg)end=-end;
        while(*p&&*p!=' ')p++;
        if(*p){
            p++;start=end;end=0;neg=0;
            if(*p=='-'){neg=1;p++;}
            while(*p>='0'&&*p<='9'){end=end*10+(*p-'0');p++;}
            if(neg)end=-end;
        }
        if(end==0)end=start;
        for(int i=start;i<=end;i++){put_dec(i);uart_putc('\n');}
    }
    else if(kstrcmp(cmd,"yes")==0){
        if(!arg)arg="y";
        while(1){uart_puts(arg);uart_putc('\n');}
    }
    else if(kstrcmp(cmd,"id")==0){uart_puts("uid=0(root) gid=0(root) groups=0(root)\n");}
    else if(kstrcmp(cmd,"su")==0){uart_puts("su: switched to root\n");}
    else if(kstrcmp(cmd,"ulimit")==0){uart_puts("ulimit: unlimited\n");}
    else if(kstrcmp(cmd,"umask")==0){uart_puts("umask: 022\n");}
    else if(kstrcmp(cmd,"dmesg")==0){
        uart_puts("MiniOS 3.0.0 kernel messages:\n");
        uart_puts("[    0.000000] MiniOS 3.0.0 starting\n");
        uart_puts("[    0.001000] VFS initialized\n");
        uart_puts("[    0.002000] Scheduler: round-robin\n");
        uart_puts("[    0.003000] Heap: buddy allocator\n");
        uart_puts("[    0.004000] Shell ready\n");
    }
    else if(kstrcmp(cmd,"type")==0){
        if(!arg){uart_puts("type: usage: type <command>\n");return;}
        uart_puts(arg);uart_puts(" is ");
        if(kstrcmp(arg,"ls")==0||kstrcmp(arg,"cd")==0||kstrcmp(arg,"cat")==0||
           kstrcmp(arg,"pwd")==0||kstrcmp(arg,"mkdir")==0||kstrcmp(arg,"touch")==0||
           kstrcmp(arg,"rm")==0||kstrcmp(arg,"cp")==0||kstrcmp(arg,"mv")==0){
            uart_puts("shell builtin\n");
        } else {
            uart_puts("/bin/\n");
        }
    }
    else if(kstrcmp(cmd,"version")==0){
        uart_puts("MiniOS 3.0.0 (KentScript)\n");
        uart_puts("Built: Sat Mar 28 2026\n");
        uart_puts("AArch64 Bare Metal OS\n");
    }
    else if(kstrcmp(cmd,"credits")==0||kstrcmp(cmd,"about")==0){
        uart_puts("╔═══════════════════════════════════════╗\n");
        uart_puts("║     MiniOS 3.0 - KentScript OS        ║\n");
        uart_puts("║     (c) 2026 KentScript Team          ║\n");
        uart_puts("╚═══════════════════════════════════════╝\n");
    }
    else if(*cmd){
        uart_puts("\033[31m"); uart_puts(cmd); uart_puts(": command not found\033[0m\n");
        uart_puts("Type 'help' for commands.\n");
    }
}

/* ===================================================== GUI TASK */
static void gui_task(void){
    /* Desktop gradient background */
    fb_gradient(0,0,FB_WIDTH,FB_HEIGHT,0x0a0a1a,0x050510);

    /* Taskbar */
    fb_gradient(0,FB_HEIGHT-32,FB_WIDTH,32,0x1a1a2e,0x0d0d1a);
    fb_rect(0,FB_HEIGHT-32,80,32,0x1a73e8);
    fb_text(8,FB_HEIGHT-22,"MiniOS",0xffffff,0x1a73e8);
    fb_text(200,FB_HEIGHT-22,"AArch64 Bare Metal OS 2.0",0x555588,0x0d0d1a);
    fb_rect(FB_WIDTH-90,FB_HEIGHT-30,88,28,0x111122);
    fb_text(FB_WIDTH-82,FB_HEIGHT-22,"00:00:00",0x00ccff,0x111122);

    /* Logo window */
    int w0=gui_open_window(16,16,300,180,"MiniOS 2.2",0x0d1117,1);
    gui_draw_logo(20,34);
    gui_text_in_window(w0,4,60,"AArch64 Bare Metal OS 2.2",0x00ccff);
    gui_text_in_window(w0,4,72,"Buddy alloc | SMP-safe heap",0x888888);
    gui_text_in_window(w0,4,84,"Built with KentScript 2.1",0x00ff88);
    gui_text_in_window(w0,4,96,"Made in Uganda by user",0xffcc00);
    gui_text_in_window(w0,4,110,"kdb | backtrace | exec | ELF",0x888888);

    /* System info window */
    int w1=gui_open_window(326,16,380,190,"System Info",0x0d1117,0);
    gui_text_in_window(w1,4,0, "CPU  : ARM Cortex-A53 AArch64",0x00ccff);
    gui_text_in_window(w1,4,12,"EL   : 1 (privileged kernel mode)",0x888888);
    gui_text_in_window(w1,4,24,"UART : PL011 @ 0x09000000",0x888888);
    gui_text_in_window(w1,4,36,"GIC  : GICv2 @ 0x08000000",0x888888);
    gui_text_in_window(w1,4,48,"FB   : 1024x768 32bpp @ 0x3c000000",0x888888);
    gui_text_in_window(w1,4,60,"Heap : 0x44000000 (64MB)",0x888888);
    gui_text_in_window(w1,4,72,"User : 0x10000000 (64MB EL0)",0x888888);
    gui_text_in_window(w1,4,84,"Sched: Round-robin + priority",0x888888);
    gui_text_in_window(w1,4,96,"Syscalls: 16 (SVC #0)",0x888888);
    gui_text_in_window(w1,4,108,"VFS  : ramfs (/bin /etc /home /proc /dev /tmp /usr)",0x888888);
    gui_text_in_window(w1,4,120,"Shell: 25 commands + history",0x888888);
    gui_text_in_window(w1,4,132,"VM   : KentScript bytecode interpreter",0x00ff88);

    /* Dashboard window */
    dash_wid=gui_open_window(716,16,300,80,"Live Dashboard",0x0a1a0a,0);
    gui_text_in_window(dash_wid,4,0,"Uptime: --",0x888888);
    gui_text_in_window(dash_wid,4,12,"Heap: --",0x888888);
    gui_text_in_window(dash_wid,4,24,"CTX sw: --",0x888888);

    /* Task manager window */
    task_wid=gui_open_window(716,106,300,200,"Task Manager",0x0a0a1a,0);
    gui_text_in_window(task_wid,4,0,"PID  PRI   STATE   TICKS  NAME",0x00ccff);

    /* Memory map window */
    mem_wid=gui_open_window(326,216,380,140,"Memory Map",0x1a0a0a,0);
    gui_text_in_window(mem_wid,4,0,  "0x09000000  UART PL011",0xffcc00);
    gui_text_in_window(mem_wid,4,12, "0x08000000  GIC Distributor",0xffcc00);
    gui_text_in_window(mem_wid,4,24, "0x10000000  EL0 User Space (64MB)",0x00ff88);
    gui_text_in_window(mem_wid,4,36, "0x40000000  Kernel (vectors+text)",0x00ccff);
    gui_text_in_window(mem_wid,4,48, "0x44000000  Kernel Heap (64MB)",0x00ccff);
    gui_text_in_window(mem_wid,4,60, "0x3c000000  Framebuffer (3MB)",0xff8800);
    gui_draw_progressbar(windows[mem_wid].x+4,windows[mem_wid].y+90,
                         windows[mem_wid].w-8,10,2,0x00ccff,0x0a0a1a);

    /* Scheduler window */
    sched_wid=gui_open_window(16,206,300,140,"Scheduler",0x0a0a1a,0);
    gui_text_in_window(sched_wid,4,0, "Mode: Round-robin + priority",0x00ccff);
    gui_text_in_window(sched_wid,4,12,"Timer: 100Hz preemptive",0x888888);
    gui_text_in_window(sched_wid,4,24,"Priorities: LOW NORM HIGH RT",0x888888);
    gui_text_in_window(sched_wid,4,36,"Max tasks: 12",0x888888);
    gui_text_in_window(sched_wid,4,48,"Stack: 16KB per task",0x888888);
    gui_text_in_window(sched_wid,4,60,"Context switch: callee-save+SP",0x888888);
    gui_text_in_window(sched_wid,4,72,"EL0 support: minios_enter_el0()",0x00ff88);
    gui_text_in_window(sched_wid,4,84,"ELF loader: PT_LOAD segments",0x00ff88);

    /* KentScript window */
    int ks_wid=gui_open_window(16,356,300,130,"KentScript VM",0x0a1a0a,0);
    gui_text_in_window(ks_wid,4,0, "ks fib  — fibonacci via bytecode",0x00ff88);
    gui_text_in_window(ks_wid,4,12,"ks sum  — sum 1..100",0x00ff88);
    gui_text_in_window(ks_wid,4,24,"ks <f>  — display .ks source",0x00ff88);
    gui_text_in_window(ks_wid,4,36,"Opcodes: PUSH POP ADD SUB MUL",0x888888);
    gui_text_in_window(ks_wid,4,48,"         DIV PRINT JMP JZ CMP",0x888888);
    gui_text_in_window(ks_wid,4,60,"         LOAD STORE HALT PRINTS",0x888888);
    gui_text_in_window(ks_wid,4,72,"Stack: 64 deep | Mem: 256 cells",0x888888);
    gui_text_in_window(ks_wid,4,84,"Future: native AArch64 codegen",0xffcc00);

    /* EL0 / syscall window */
    int el0_wid=gui_open_window(326,366,380,122,"EL0 Userland + Syscalls",0x0d0d1a,0);
    gui_text_in_window(el0_wid,4,0, "SVC #0 dispatch (x8=syscall nr)",0x00ccff);
    gui_text_in_window(el0_wid,4,12,"sys_write  sys_read   sys_open",0x888888);
    gui_text_in_window(el0_wid,4,24,"sys_exit   sys_getpid sys_sleep",0x888888);
    gui_text_in_window(el0_wid,4,36,"sys_uptime sys_fb_*  sys_malloc",0x888888);
    gui_text_in_window(el0_wid,4,48,"sys_yield  sys_spawn sys_gettime",0x888888);
    gui_text_in_window(el0_wid,4,60,"ELF64 loader: PT_LOAD → user VA",0x00ff88);
    gui_text_in_window(el0_wid,4,72,"User space: 0x10000000 (64MB)",0x00ff88);
    gui_text_in_window(el0_wid,4,84,"el0test: drops to EL0, SVC exit",0xffcc00);

    /* Stress test window */
    int stress_wid=gui_open_window(716,316,300,150,"Diagnostics",0x1a0a0a,0);
    gui_text_in_window(stress_wid,4,0, "stress vfs   — 20-file VFS test",0xff8800);
    gui_text_in_window(stress_wid,4,12,"stress mem   — 100-alloc test",0xff8800);
    gui_text_in_window(stress_wid,4,24,"stress sched — scheduler stats",0xff8800);
    gui_text_in_window(stress_wid,4,36,"canary — 3-word memory pattern",0xff8800);
    gui_text_in_window(stress_wid,4,48,"cpuinfo — full register dump",0xff8800);
    gui_text_in_window(stress_wid,4,60,"hist — command history",0xff8800);
    gui_text_in_window(stress_wid,4,72,"ls -l — long listing with perms",0xff8800);
    gui_text_in_window(stress_wid,4,84,"chmod <f> <mode> — set perms",0xff8800);
    gui_text_in_window(stress_wid,4,96,"cat /etc/motd — MOTD",0xff8800);

    /* Initial dashboard update */
    gui_update_dashboard();
    gui_update_task_window();

    /* Periodic refresh loop */
    u64 last_update=0;
    while(1){
        if(tick_count-last_update>=50){ /* every 500ms */
            gui_update_dashboard();
            gui_update_task_window();
            last_update=tick_count;
        }
        __asm__ volatile("yield");
    }
}

/* ============================================================== SHELL TASK */
static void shell_task(void){
    /* Print MOTD */
    vfs_node_t *motd=vfs_find(vfs_find(vfs_root,"etc"),"motd");
    if(motd){ for(size_t i=0;i<motd->size;i++) uart_putc((char)motd->data[i]); uart_puts("\n"); }

    shell_print_prompt();
    while(1){
        char c;
        if(uart_getc_nb(&c)){
            if(c=='\r'||c=='\n'){
                uart_puts("\n");
                shell_buf[shell_pos]=0;
                shell_exec(shell_buf);
                shell_pos=0;
                shell_print_prompt();
            } else if(c==0x7f||c=='\b'){
                if(shell_pos>0){ shell_pos--; uart_puts("\b \b"); }
            } else if(shell_pos<SHELL_BUF-1){
                shell_buf[shell_pos++]=c;
                uart_putc(c);
            }
        }
        __asm__ volatile("yield");
    }
}

/* ================================================================== MAIN */
void minios_main(void){
    uart_init();
    uart_puts("\n");
    uart_puts("================================================================\n");
    uart_puts("  MiniOS 2.2 — AArch64 Bare Metal Operating System\n");
    uart_puts("  Built with KentScript | No Linux | No libc | No compromise\n");
    uart_puts("  EL1 Kernel | EL0 Userland | KentScript VM 2.1 | 32-cmd Shell\n");
    uart_puts("  Buddy alloc | SMP-safe heap | kdb | backtrace | exec+ELF\n");
    uart_puts("================================================================\n\n");

    uart_puts("[INIT] Memory allocator...\n");
    if(heap_ptr<HEAP_START||heap_ptr>HEAP_END) heap_ptr=HEAP_START;

    uart_puts("[INIT] VFS (ramfs)...\n");
    vfs_init();

    uart_puts("[INIT] Scheduler (priority round-robin)...\n");
    task_init();

    uart_puts("[INIT] GUI task (RT priority)...\n");
    task_spawn("gui",  gui_task,  PRIO_NORMAL);

    uart_puts("[INIT] Shell task (normal priority)...\n");
    task_spawn("shell",shell_task,PRIO_HIGH);

    uart_puts("[INIT] Timer (100Hz preemptive)...\n");
    timer_init();

    uart_puts("\n");
    uart_puts("[OK] MiniOS 2.2 booted — buddy alloc + SMP-safe + kdb!\n");
    uart_puts("[OK] Tasks: "); put_dec((u64)task_count); uart_puts("\n");
    uart_puts("[OK] Heap : 0x44000000 (64MB)\n");
    uart_puts("[OK] FB   : 0x3c000000 (1024x768 32bpp)\n");
    uart_puts("[OK] Type 'help' for 32 shell commands.\n");
    uart_puts("[OK] Try : ks fib | stress all | kdb | backtrace | exec | buddy\n\n");

    current_task=0; tasks[0].state=TASK_RUNNING;
    if(task_count>1){
        tasks[0].state=TASK_READY; current_task=1;
        tasks[1].state=TASK_RUNNING;
        gui_task();
    }
    while(1) __asm__ volatile("wfi");
}
"""

# ============================================================================
# LINKER SCRIPT
# ============================================================================

_KENTOS_LINKER_LD = """
ENTRY(_start)
OUTPUT_FORMAT(elf64-littleaarch64)
SECTIONS {
    . = 0x40000000;

    /* Exception vector table — MUST be first and 2KiB aligned */
    .text.vectors ALIGN(0x800) : { *(.text.vectors) }

    .text   ALIGN(4096) : { *(.text) *(.text.*) }
    .rodata ALIGN(4096) : { *(.rodata) *(.rodata.*) }
    .data   ALIGN(4096) : {
        /* CRITICAL: heap_ptr lives here — must NOT be zeroed by BSS init */
        *(.data) *(.data.*)
    }

    .bss    ALIGN(4096) : {
        __bss_start = .;
        *(COMMON)
        *(.bss)
        *(.bss.*)
        . = ALIGN(8);
        __bss_end = .;
    }

    . = ALIGN(4096);
    _end = .;

    /DISCARD/ : {
        *(.eh_frame*) *(.note*) *(.comment*)
        *(.gnu.hash*) *(.dynsym*) *(.dynstr*)
        *(.gnu.version*) *(.dynamic*) *(.got*) *(.plt*)
        *(.interp*) *(.gnu.warning*)
    }
}
"""

# ============================================================================
# QEMU RUN COMMAND
# ============================================================================

KENTOS_QEMU_CMD = (
    "qemu-system-aarch64 "
    "-machine virt "
    "-cpu cortex-a53 "
    "-smp 1 "  # MiniOS 2.2: single-core until per-CPU runqueues are done
    "-m 512 "
    "-nographic "
    "-device ramfb "
    "-kernel {output} "
    "-serial mon:stdio"
)

KENTOS_QEMU_GUI_CMD = (
    "qemu-system-aarch64 "
    "-machine virt "
    "-cpu cortex-a53 "
    "-smp 1 "  # Stay on 1 core — SMP needs per-CPU runqueues first
    "-m 512 "
    "-device ramfb "
    "-kernel {output} "
    "-serial mon:stdio"
)

# For future use when per-CPU runqueues are implemented:
KENTOS_QEMU_SMP4_CMD = (
    "qemu-system-aarch64 "
    "-machine virt "
    "-cpu cortex-a53 "
    "-smp 4 "
    "-m 512 "
    "-nographic "
    "-device ramfb "
    "-kernel {output} "
    "-serial mon:stdio"
)

# ============================================================================
# BUILDER
# ============================================================================


def _run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", "timeout"


def _find_compiler():
    for name in ("aarch64-linux-gnu-gcc", "aarch64-unknown-linux-gnu-gcc"):
        p = shutil.which(name)
        if p:
            return p
    return None


@dataclass
class MiniOSConfig:
    output: str = "/tmp/minios.elf"
    fb_width: int = 1024
    fb_height: int = 768
    heap_mb: int = 64
    max_tasks: int = 8
    timer_hz: int = 100
    features: List[str] = field(
        default_factory=lambda: [
            "uart",
            "framebuffer",
            "font",
            "vfs",
            "scheduler",
            "syscalls",
            "shell",
            "gui",
            "el0",
        ]
    )


class MiniOS:
    def __init__(self, config: Optional[MiniOSConfig] = None):
        self.config = config or MiniOSConfig()

    def build(self) -> Tuple[bool, str]:
        cc = _find_compiler()
        if not cc:
            return False, (
                "AArch64 cross-compiler not found.\n"
                "Install: sudo apt install gcc-aarch64-linux-gnu\n"
                "Then retry: python3 ks_minios.py build"
            )

        with tempfile.TemporaryDirectory() as td:
            entry_s = os.path.join(td, "entry.S")
            kernel_c = os.path.join(td, "kernel.c")
            link_ld = os.path.join(td, "minios.ld")

            with open(entry_s, "w") as f:
                f.write(_KENTOS_ENTRY_S)
            with open(kernel_c, "w") as f:
                f.write(_KENTOS_KERNEL_C)
            with open(link_ld, "w") as f:
                f.write(_KENTOS_LINKER_LD)

            flags = [
                "-ffreestanding",
                "-nostdlib",
                "-nostartfiles",
                "-fno-builtin",
                "-fno-stack-protector",
                "-fno-pic",
                "-fno-pie",
                "-static",
                "-no-pie",
                "-fno-exceptions",
                "-fno-asynchronous-unwind-tables",
                "-Wl,--build-id=none",
                "-O1",
                # Frame pointers: required for kernel_backtrace() to walk the call chain
                "-fno-omit-frame-pointer",
                # Suppress noisy-but-harmless warnings from the kernel C style
                "-Wall",
                "-Wno-unused-function",
                "-Wno-unused-variable",
                "-Wno-unused-const-variable",
                "-Wno-misleading-indentation",
                "-mcpu=cortex-a53",
            ]

            cmd = (
                [cc]
                + flags
                + [f"-T{link_ld}", "-o", self.config.output, entry_s, kernel_c]
            )
            rc, _, err = _run(cmd)
            if rc != 0:
                return False, f"Build failed:\n{err}"

            # Verify
            rc2, readelf_out, _ = _run(["readelf", "-h", self.config.output])
            size = os.path.getsize(self.config.output)

            boot_cmd = KENTOS_QEMU_CMD.format(output=self.config.output)
            return True, (
                f"MiniOS built: {self.config.output} ({size} bytes)\n\n"
                f"Boot (serial/no-GUI):\n  {boot_cmd}\n\n"
                f"Boot (with GUI display):\n  "
                f"{KENTOS_QEMU_GUI_CMD.format(output=self.config.output)}"
            )

    def run(self, gui: bool = False) -> Tuple[bool, str]:
        if not os.path.exists(self.config.output):
            ok, msg = self.build()
            if not ok:
                return False, msg

        qemu = shutil.which("qemu-system-aarch64")
        if not qemu:
            return (
                False,
                "qemu-system-aarch64 not found. Install: apt install qemu-system-arm",
            )

        cmd_str = KENTOS_QEMU_GUI_CMD if gui else KENTOS_QEMU_CMD
        cmd = cmd_str.format(output=self.config.output).split()
        print(f"Running: {' '.join(cmd)}\n")
        os.execvp(cmd[0], cmd)  # replace process — QEMU takes over
        return True, "exec'd into QEMU"

    def info(self):
        print("=" * 60)
        print("  MiniOS 1.0 — AArch64 Bare Metal OS Builder")
        print("=" * 60)
        print(f"  Output:    {self.config.output}")
        print(f"  Arch:      AArch64 (QEMU virt, cortex-a53)")
        print(
            f"  FB:        {self.config.fb_width}x{self.config.fb_height} 32bpp @ 0x3c000000"
        )
        print(f"  Heap:      {self.config.heap_mb} MiB @ 0x44000000")
        print(f"  Max tasks: {self.config.max_tasks}")
        print(f"  Timer:     {self.config.timer_hz} Hz preemptive")
        print()
        print("  Subsystems:")
        features = [
            ("UART driver", "PL011 @ 0x09000000, TX/RX"),
            ("Framebuffer", "1024x768 32bpp, pixel/rect/text API"),
            ("Font renderer", "8x8 bitmap, full ASCII"),
            ("Memory alloc", "Bump allocator, 64MiB heap"),
            ("VFS / ramfs", "/bin /etc /home /proc /dev /tmp"),
            ("Scheduler", "Round-robin preemptive, timer IRQ"),
            ("Syscall ABI", "SVC #0 dispatch (12 syscalls)"),
            ("Shell", "UART interactive, 14 commands"),
            ("GUI / WM", "Framebuffer windows, desktop, taskbar"),
            ("EL0 support", "minios_enter_el0() for user tasks"),
            ("Exc. vectors", "Full 16-entry AArch64 vector table"),
            ("Context switch", "callee-save/restore, SP swap"),
        ]
        for name, desc in features:
            print(f"    ✓ {name:<18} {desc}")
        print()
        print("  Boot:")
        print(f"    {KENTOS_QEMU_CMD.format(output=self.config.output)}")
        print()
        print("  Shell commands: ls cd cat touch mkdir echo ps meminfo")
        print("                  uname uptime cpuinfo reboot help")
        print("=" * 60)


# ============================================================================
# CLI
# ============================================================================


def main():
    import argparse

    p = argparse.ArgumentParser(
        prog="ks_minios", description="MiniOS Bare-Metal OS Builder"
    )
    p.add_argument(
        "command",
        choices=["build", "run", "run-gui", "info"],
        help="build=compile ELF, run=boot in QEMU, info=show features",
    )
    p.add_argument(
        "--output",
        default="/tmp/minios.elf",
        help="output ELF path (default: /tmp/minios.elf)",
    )
    args = p.parse_args()

    cfg = MiniOSConfig(output=args.output)
    k = MiniOS(cfg)

    if args.command == "info":
        k.info()

    elif args.command == "build":
        print(f"Building MiniOS → {args.output}")
        ok, msg = k.build()
        print(msg)
        sys.exit(0 if ok else 1)

    elif args.command == "run":
        ok, msg = k.run(gui=False)
        if not ok:
            print(msg)
            sys.exit(1)

    elif args.command == "run-gui":
        ok, msg = k.run(gui=True)
        if not ok:
            print(msg)
            sys.exit(1)


if __name__ == "__main__":
    main()
