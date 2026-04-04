/* ============================================================================
 * ks_ring0.h - Ring 0 / Kernel Mode Primitives (PRODUCTION EDITION)
 * Replaces old ks_ring0.h — superset of previous + new syscall + MMIO
 * ========================================================================== */

#ifndef KS_RING0_H
#define KS_RING0_H

#include "ks_platform.h"
#include "ks_optimize.h"

#ifdef __KERNEL__
    #include <linux/kernel.h>
    #include <linux/module.h>
    #include <linux/init.h>
    #include <linux/slab.h>
    #include <linux/string.h>
    #include <linux/uaccess.h>
    #include <linux/io.h>
    #include <linux/fs.h>
    #include <linux/proc_fs.h>
    #include <linux/seq_file.h>
    #include <linux/interrupt.h>
    #include <linux/spinlock.h>
    #include <linux/mutex.h>
    #include <linux/sched.h>
    #include <linux/kthread.h>
    #include <linux/delay.h>
    #include <linux/random.h>
    #include <linux/time.h>
    #include <linux/mm.h>
    #include <linux/vmalloc.h>
    #include <asm/io.h>
    #include <asm/irq.h>
    #include <asm/atomic.h>
    #include <asm/barrier.h>
    #include <asm/msr.h>
    #include <asm/processor.h>
    #include <asm/page.h>
    #include <asm/unistd.h>
#else
    #include <stdint.h>
    #include <stddef.h>
    #include <string.h>
    #include <stdlib.h>
    #include <stdio.h>

    #define printk(fmt, ...) printf(fmt, ##__VA_ARGS__)
    #define KERN_INFO ""
    #define KERN_ERR  ""
    #define KERN_WARNING ""
    #define KERN_DEBUG ""

    #define GFP_KERNEL 0
    #define GFP_ATOMIC 0
    static inline void *kmalloc(size_t size, int flags) { return malloc(size); }
    static inline void  kfree(void *ptr) { free(ptr); }
    static inline void *kzalloc(size_t size, int flags) { return calloc(1, size); }
    static inline void *vmalloc(unsigned long size) { return malloc(size); }
    static inline void  vfree(void *ptr) { free(ptr); }

    typedef int spinlock_t;
    #define spin_lock_init(l)           do { *(l) = 0; } while(0)
    #define spin_lock(l)                do {} while(0)
    #define spin_unlock(l)              do {} while(0)
    #define spin_lock_irqsave(l, f)     do { f = 0; } while(0)
    #define spin_unlock_irqrestore(l,f) do {} while(0)

    typedef int mutex_t;
    #define mutex_init(m)   do { *(m) = 0; } while(0)
    #define mutex_lock(m)   do {} while(0)
    #define mutex_unlock(m) do {} while(0)

    struct task_struct { int pid; };
    #define kthread_run(fn, data, name) NULL
    #define kthread_stop(t) 0
    #define kthread_should_stop() 0

    #define module_init(x)       int main() { return x(); }
    #define module_exit(x)       void cleanup() { x(); }
    #define MODULE_LICENSE(x)
    #define MODULE_AUTHOR(x)
    #define MODULE_DESCRIPTION(x)

    #define mb()  __asm__ volatile("" ::: "memory")
    #define rmb() __asm__ volatile("" ::: "memory")
    #define wmb() __asm__ volatile("" ::: "memory")
#endif /* __KERNEL__ */

/* ============================================================================
 * ARM64 System Register Access (kept from previous ks_ring0.h)
 * ========================================================================== */
#ifdef KS_ARCH_ARM64
    #define KS_READ_SYSREG(reg) ({ uint64_t v; __asm__ volatile("mrs %0, " #reg : "=r"(v)); v; })
    #define KS_WRITE_SYSREG(reg, val) __asm__ volatile("msr " #reg ", %0" : : "r"(val))
#endif

/* ============================================================================
 * x86 Port I/O
 * ========================================================================== */
#ifdef KS_ARCH_X86_64
    static inline void     ks_outb(uint16_t p, uint8_t  v) { __asm__ volatile("outb %0,%1"::"a"(v),"Nd"(p)); }
    static inline uint8_t  ks_inb (uint16_t p)             { uint8_t  v; __asm__ volatile("inb %1,%0":"=a"(v):"Nd"(p)); return v; }
    static inline void     ks_outw(uint16_t p, uint16_t v) { __asm__ volatile("outw %0,%1"::"a"(v),"Nd"(p)); }
    static inline uint16_t ks_inw (uint16_t p)             { uint16_t v; __asm__ volatile("inw %1,%0":"=a"(v):"Nd"(p)); return v; }
    static inline void     ks_outl(uint16_t p, uint32_t v) { __asm__ volatile("outl %0,%1"::"a"(v),"Nd"(p)); }
    static inline uint32_t ks_inl (uint16_t p)             { uint32_t v; __asm__ volatile("inl %1,%0":"=a"(v):"Nd"(p)); return v; }
#endif

/* ============================================================================
 * MMIO
 * ========================================================================== */
static inline void     ks_mmio_write8 (volatile void *a, uint8_t  v) { mb(); *(volatile uint8_t *)a  = v; mb(); }
static inline uint8_t  ks_mmio_read8  (volatile void *a)             { mb(); uint8_t  v=*(volatile uint8_t *)a;  mb(); return v; }
static inline void     ks_mmio_write16(volatile void *a, uint16_t v) { mb(); *(volatile uint16_t*)a  = v; mb(); }
static inline uint16_t ks_mmio_read16 (volatile void *a)             { mb(); uint16_t v=*(volatile uint16_t*)a; mb(); return v; }
static inline void     ks_mmio_write32(volatile void *a, uint32_t v) { mb(); *(volatile uint32_t*)a  = v; mb(); }
static inline uint32_t ks_mmio_read32 (volatile void *a)             { mb(); uint32_t v=*(volatile uint32_t*)a; mb(); return v; }
static inline void     ks_mmio_write64(volatile void *a, uint64_t v) { mb(); *(volatile uint64_t*)a  = v; mb(); }
static inline uint64_t ks_mmio_read64 (volatile void *a)             { mb(); uint64_t v=*(volatile uint64_t*)a; mb(); return v; }

/* ============================================================================
 * Direct Syscalls (x86-64 Linux, bypass libc)
 * ========================================================================== */
#ifdef KS_ARCH_X86_64
    static inline long ks_syscall1(long n, long a1) {
        long r; __asm__ volatile("syscall":"=a"(r):"a"(n),"D"(a1):"rcx","r11","memory"); return r; }
    static inline long ks_syscall2(long n, long a1, long a2) {
        long r; __asm__ volatile("syscall":"=a"(r):"a"(n),"D"(a1),"S"(a2):"rcx","r11","memory"); return r; }
    static inline long ks_syscall3(long n, long a1, long a2, long a3) {
        long r; __asm__ volatile("syscall":"=a"(r):"a"(n),"D"(a1),"S"(a2),"d"(a3):"rcx","r11","memory"); return r; }
    static inline long ks_syscall4(long n, long a1, long a2, long a3, long a4) {
        long r; register long r10 __asm__("r10")=a4;
        __asm__ volatile("syscall":"=a"(r):"a"(n),"D"(a1),"S"(a2),"d"(a3),"r"(r10):"rcx","r11","memory"); return r; }
    static inline long ks_syscall6(long n, long a1, long a2, long a3, long a4, long a5, long a6) {
        long r; register long r10 __asm__("r10")=a4,r8 __asm__("r8")=a5,r9 __asm__("r9")=a6;
        __asm__ volatile("syscall":"=a"(r):"a"(n),"D"(a1),"S"(a2),"d"(a3),"r"(r10),"r"(r8),"r"(r9):"rcx","r11","memory"); return r; }
#endif

/* ============================================================================
 * Lock-Free Atomics
 * ========================================================================== */
static inline uint64_t ks_atomic_add(volatile uint64_t *p, uint64_t v)  { return __sync_fetch_and_add(p,v); }
static inline uint64_t ks_atomic_sub(volatile uint64_t *p, uint64_t v)  { return __sync_fetch_and_sub(p,v); }
static inline uint64_t ks_atomic_or (volatile uint64_t *p, uint64_t v)  { return __sync_fetch_and_or (p,v); }
static inline uint64_t ks_atomic_and(volatile uint64_t *p, uint64_t v)  { return __sync_fetch_and_and(p,v); }
static inline uint64_t ks_atomic_xor(volatile uint64_t *p, uint64_t v)  { return __sync_fetch_and_xor(p,v); }
static inline uint64_t ks_atomic_xchg(volatile uint64_t *p, uint64_t v) { return __sync_lock_test_and_set(p,v); }
static inline int ks_atomic_cas(volatile uint64_t *p, uint64_t e, uint64_t d) { return __sync_bool_compare_and_swap(p,e,d); }

/* ============================================================================
 * High-Precision Timer
 * ========================================================================== */
static inline uint64_t ks_rdtsc(void) {
#ifdef KS_ARCH_X86_64
    uint32_t lo, hi;
    __asm__ volatile("rdtsc":"=a"(lo),"=d"(hi)); return ((uint64_t)hi<<32)|lo;
#elif defined(KS_ARCH_ARM64)
    uint64_t v; __asm__ volatile("mrs %0, cntvct_el0":"=r"(v)); return v;
#else
    return 0;
#endif
}

/* ============================================================================
 * CPU Feature Detection (x86)
 * ========================================================================== */
static inline uint32_t ks_cpuid(uint32_t leaf, uint32_t *eax, uint32_t *ebx, uint32_t *ecx, uint32_t *edx) {
#ifdef KS_ARCH_X86_64
    __asm__ volatile("cpuid":"=a"(*eax),"=b"(*ebx),"=c"(*ecx),"=d"(*edx):"a"(leaf),"c"(0));
    return *eax;
#else
    *eax=*ebx=*ecx=*edx=0; return 0;
#endif
}

/* ============================================================================
 * MSR Access (kernel only)
 * ========================================================================== */
#if defined(__KERNEL__) && defined(KS_ARCH_X86_64)
    static inline uint64_t ks_rdmsr(uint32_t msr) {
        uint32_t lo,hi; __asm__ volatile("rdmsr":"=a"(lo),"=d"(hi):"c"(msr)); return ((uint64_t)hi<<32)|lo; }
    static inline void ks_wrmsr(uint32_t msr, uint64_t val) {
        __asm__ volatile("wrmsr"::"a"((uint32_t)val),"d"((uint32_t)(val>>32)),"c"(msr)); }
    static inline uint64_t ks_read_cr3(void) {
        uint64_t v; __asm__ volatile("mov %%cr3,%0":"=r"(v)); return v; }
    static inline void ks_invlpg(void *addr) {
        __asm__ volatile("invlpg (%0)"::"r"(addr):"memory"); }
#endif

#endif /* KS_RING0_H */
