/*
 * Low-level C runtime support for KentScript transpiled code
 * Provides: syscalls, memory operations, inline assembly support
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/mman.h>
#include <unistd.h>
#include <sys/syscall.h>

// Memory operations
static inline void* ks_malloc(size_t size) {
    return malloc(size);
}

static inline void ks_free(void* ptr) {
    free(ptr);
}

static inline void* ks_mmap(void* addr, size_t length, int prot, int flags, int fd, off_t offset) {
    return mmap(addr, length, prot, flags, fd, offset);
}

static inline int ks_munmap(void* addr, size_t length) {
    return munmap(addr, length);
}

// Pointer operations
static inline uint64_t ks_ptr_read(void* addr, int size) {
    switch(size) {
        case 1: return *(uint8_t*)addr;
        case 2: return *(uint16_t*)addr;
        case 4: return *(uint32_t*)addr;
        case 8: return *(uint64_t*)addr;
        default: return *(uint64_t*)addr;
    }
}

static inline void ks_ptr_write(void* addr, uint64_t value, int size) {
    switch(size) {
        case 1: *(uint8_t*)addr = (uint8_t)value; break;
        case 2: *(uint16_t*)addr = (uint16_t)value; break;
        case 4: *(uint32_t*)addr = (uint32_t)value; break;
        case 8: *(uint64_t*)addr = value; break;
        default: *(uint64_t*)addr = value; break;
    }
}

static inline void* ks_ptr_cast(void* ptr) {
    return ptr;
}

static inline uint64_t ks_ptr_deref(void* ptr) {
    return *(uint64_t*)ptr;
}

// Syscall wrapper
static inline long ks_syscall(long number, long arg1, long arg2, long arg3, long arg4, long arg5, long arg6) {
    return syscall(number, arg1, arg2, arg3, arg4, arg5, arg6);
}

static inline long ks_system_syscall(long number, long arg1, long arg2, long arg3, long arg4, long arg5, long arg6) {
    return syscall(number, arg1, arg2, arg3, arg4, arg5, arg6);
}

// Atomic operations
static inline uint64_t ks_atomic_load(void* addr, int size) {
    return __atomic_load_n((uint64_t*)addr, __ATOMIC_SEQ_CST);
}

static inline void ks_atomic_store(void* addr, uint64_t value, int size) {
    __atomic_store_n((uint64_t*)addr, value, __ATOMIC_SEQ_CST);
}

static inline uint64_t ks_atomic_add(void* addr, uint64_t value, int size) {
    return __atomic_add_fetch((uint64_t*)addr, value, __ATOMIC_SEQ_CST);
}

static inline uint64_t ks_atomic_cas(void* addr, uint64_t expected, uint64_t desired, int size) {
    __atomic_compare_exchange_n((uint64_t*)addr, &expected, desired, 0, __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST);
    return expected;
}

// Volatile operations
static inline uint64_t ks_volatile_read(volatile void* addr, int size) {
    return *(volatile uint64_t*)addr;
}

static inline void ks_volatile_write(volatile void* addr, uint64_t value, int size) {
    *(volatile uint64_t*)addr = value;
}

// Memory barriers
static inline void ks_memory_barrier() {
    __sync_synchronize();
}

static inline void ks_compiler_barrier() {
    __asm__ __volatile__("" ::: "memory");
}

// Cache operations
static inline void ks_cache_flush(void* addr, size_t size) {
    __builtin___clear_cache((char*)addr, (char*)addr + size);
}

static inline void ks_cache_invalidate(void* addr, size_t size) {
    __builtin___clear_cache((char*)addr, (char*)addr + size);
}

// MMIO operations
static inline uint64_t ks_mmio_read(void* addr, int size) {
    return ks_volatile_read(addr, size);
}

static inline void ks_mmio_write(void* addr, uint64_t value, int size) {
    ks_volatile_write(addr, value, size);
}

// Port I/O (x86/x86_64 only)
#if defined(__x86_64__) || defined(__i386__)
static inline uint8_t ks_read_port(uint16_t port) {
    uint8_t value;
    __asm__ volatile("inb %1, %0" : "=a"(value) : "Nd"(port));
    return value;
}

static inline void ks_write_port(uint16_t port, uint8_t value) {
    __asm__ volatile("outb %0, %1" : : "a"(value), "Nd"(port));
}
#else
static inline uint8_t ks_read_port(uint16_t port) { return 0; }
static inline void ks_write_port(uint16_t port, uint8_t value) {}
#endif

// CPU intrinsics
#if defined(__x86_64__) || defined(__i386__)
static inline uint64_t ks_rdtsc() {
    uint32_t lo, hi;
    __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

static inline void ks_cpuid(uint32_t leaf, uint32_t* eax, uint32_t* ebx, uint32_t* ecx, uint32_t* edx) {
    __asm__ volatile("cpuid" : "=a"(*eax), "=b"(*ebx), "=c"(*ecx), "=d"(*edx) : "a"(leaf));
}
#else
static inline uint64_t ks_rdtsc() { return 0; }
static inline void ks_cpuid(uint32_t leaf, uint32_t* eax, uint32_t* ebx, uint32_t* ecx, uint32_t* edx) {}
#endif

// MSR operations (requires root)
static inline uint64_t ks_rdmsr(uint32_t msr) {
#if defined(__x86_64__) || defined(__i386__)
    uint32_t lo, hi;
    __asm__ volatile("rdmsr" : "=a"(lo), "=d"(hi) : "c"(msr));
    return ((uint64_t)hi << 32) | lo;
#else
    return 0;
#endif
}

static inline void ks_wrmsr(uint32_t msr, uint64_t value) {
#if defined(__x86_64__) || defined(__i386__)
    uint32_t lo = value & 0xFFFFFFFF;
    uint32_t hi = value >> 32;
    __asm__ volatile("wrmsr" : : "c"(msr), "a"(lo), "d"(hi));
#endif
}

// Inline assembly support
#define ks_asm(code) __asm__ volatile(code)

// Helper for executing shellcode
typedef void (*shellcode_func_t)(void);

static inline void ks_execute_shellcode(void* addr) {
    shellcode_func_t func = (shellcode_func_t)addr;
    func();
}
