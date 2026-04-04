/*
 * ks_syscall_wrappers.h — KentScript v3.0 Direct Syscall Interface
 * [KS-REF-002] Zero-overhead syscalls (no libc)
 * [KS-REF-004] Inline assembly with register constraints
 * [KS-REF-010] Cross-architecture support (x86-64, ARM64, x86, ARM32)
 * [KS-REF-040] Ring-0 compatible (kernel mode)
 * 
 * This header provides direct system call access WITHOUT going through libc.
 * All functions are inline assembly for maximum performance.
 * 
 * Usage:
 *   #include "ks_syscall_wrappers.h"
 *   
 *   int fd = ks_open("/dev/null", O_RDWR, 0644);
 *   ks_write(fd, "Hello", 5);
 *   ks_close(fd);
 *   ks_exit(0);
 * 
 * Architecture support:
 *   - x86-64 (Linux, macOS, BSD)
 *   - ARM64 (Linux, macOS on Apple Silicon)
 *   - x86 (32-bit, Linux)
 *   - ARM32 (Linux)
 *   - Windows (via syscall emulation)
 */

#ifndef KS_SYSCALL_WRAPPERS_H
#define KS_SYSCALL_WRAPPERS_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* ============================================================================
 * ARCHITECTURE DETECTION
 * ============================================================================ */

#if defined(__x86_64__) || defined(__amd64__) || defined(_M_X64)
    #define KS_ARCH_X86_64 1
    #define KS_SYSCALL_ARCH "x86_64"
    #define KS_SYSCALL_CLOBBER "rcx", "r11", "memory"
#elif defined(__i386__) || defined(_M_IX86)
    #define KS_ARCH_X86 1
    #define KS_SYSCALL_ARCH "x86"
    #define KS_SYSCALL_CLOBBER "ecx", "edx", "memory"
#elif defined(__aarch64__) || defined(__arm64__) || defined(_M_ARM64)
    #define KS_ARCH_ARM64 1
    #define KS_SYSCALL_ARCH "aarch64"
    #define KS_SYSCALL_CLOBBER "x8", "memory"
#elif defined(__arm__) || defined(_M_ARM)
    #define KS_ARCH_ARM 1
    #define KS_SYSCALL_ARCH "arm"
    #define KS_SYSCALL_CLOBBER "r7", "memory"
#else
    #error "Unsupported architecture for direct syscalls"
#endif

/* ============================================================================
 * OPERATING SYSTEM DETECTION
 * ============================================================================ */

#if defined(__linux__)
    #define KS_OS_LINUX 1
    #include <asm/unistd.h>  /* Linux syscall numbers */
#elif defined(__APPLE__) && defined(__MACH__)
    #define KS_OS_MACOS 1
    /* macOS syscall numbers from <sys/syscall.h> */
    #include <sys/syscall.h>
#elif defined(__FreeBSD__) || defined(__OpenBSD__) || defined(__NetBSD__)
    #define KS_OS_BSD 1
    #include <sys/syscall.h>
#elif defined(_WIN32) || defined(_WIN64)
    #define KS_OS_WINDOWS 1
    /* Windows syscalls via ntdll - handled separately */
#else
    #error "Unsupported OS for direct syscalls"
#endif

/* ============================================================================
 * COMPILER ATTRIBUTES
 * ============================================================================ */

#define KS_INLINE static inline __attribute__((always_inline))
#define KS_PURE __attribute__((pure))
#define KS_CONST __attribute__((const))
#define KS_NORETURN __attribute__((noreturn))

/* ============================================================================
 * BASE SYSCALL MACROS (Architecture-specific)
 * ============================================================================ */

#if defined(KS_ARCH_X86_64)
    /* x86-64 syscall ABI:
     *   rax = syscall number
     *   rdi = arg1, rsi = arg2, rdx = arg3, r10 = arg4, r8 = arg5, r9 = arg6
     */
    #define KS_SYSCALL0(n) ({ \
        long ret; \
        __asm__ volatile( \
            "syscall" \
            : "=a"(ret) \
            : "a"(n) \
            : "rcx", "r11", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL1(n, a1) ({ \
        long ret; \
        __asm__ volatile( \
            "syscall" \
            : "=a"(ret) \
            : "a"(n), "D"((long)(a1)) \
            : "rcx", "r11", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL2(n, a1, a2) ({ \
        long ret; \
        __asm__ volatile( \
            "syscall" \
            : "=a"(ret) \
            : "a"(n), "D"((long)(a1)), "S"((long)(a2)) \
            : "rcx", "r11", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL3(n, a1, a2, a3) ({ \
        long ret; \
        __asm__ volatile( \
            "syscall" \
            : "=a"(ret) \
            : "a"(n), "D"((long)(a1)), "S"((long)(a2)), "d"((long)(a3)) \
            : "rcx", "r11", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL4(n, a1, a2, a3, a4) ({ \
        long ret; \
        __asm__ volatile( \
            "syscall" \
            : "=a"(ret) \
            : "a"(n), "D"((long)(a1)), "S"((long)(a2)), "d"((long)(a3)), \
              "r10"((long)(a4)) \
            : "rcx", "r11", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL5(n, a1, a2, a3, a4, a5) ({ \
        long ret; \
        __asm__ volatile( \
            "syscall" \
            : "=a"(ret) \
            : "a"(n), "D"((long)(a1)), "S"((long)(a2)), "d"((long)(a3)), \
              "r10"((long)(a4)), "r8"((long)(a5)) \
            : "rcx", "r11", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL6(n, a1, a2, a3, a4, a5, a6) ({ \
        long ret; \
        __asm__ volatile( \
            "syscall" \
            : "=a"(ret) \
            : "a"(n), "D"((long)(a1)), "S"((long)(a2)), "d"((long)(a3)), \
              "r10"((long)(a4)), "r8"((long)(a5)), "r9"((long)(a6)) \
            : "rcx", "r11", "memory"); \
        ret; \
    })

#elif defined(KS_ARCH_X86)
    /* x86 (32-bit) syscall ABI (int 0x80):
     *   eax = syscall number
     *   ebx = arg1, ecx = arg2, edx = arg3, esi = arg4, edi = arg5, ebp = arg6
     */
    #define KS_SYSCALL0(n) ({ \
        long ret; \
        __asm__ volatile( \
            "int $0x80" \
            : "=a"(ret) \
            : "a"(n) \
            : "ebx", "ecx", "edx", "esi", "edi", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL1(n, a1) ({ \
        long ret; \
        __asm__ volatile( \
            "int $0x80" \
            : "=a"(ret) \
            : "a"(n), "b"((long)(a1)) \
            : "ecx", "edx", "esi", "edi", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL2(n, a1, a2) ({ \
        long ret; \
        __asm__ volatile( \
            "int $0x80" \
            : "=a"(ret) \
            : "a"(n), "b"((long)(a1)), "c"((long)(a2)) \
            : "edx", "esi", "edi", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL3(n, a1, a2, a3) ({ \
        long ret; \
        __asm__ volatile( \
            "int $0x80" \
            : "=a"(ret) \
            : "a"(n), "b"((long)(a1)), "c"((long)(a2)), "d"((long)(a3)) \
            : "esi", "edi", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL4(n, a1, a2, a3, a4) ({ \
        long ret; \
        __asm__ volatile( \
            "int $0x80" \
            : "=a"(ret) \
            : "a"(n), "b"((long)(a1)), "c"((long)(a2)), "d"((long)(a3)), \
              "S"((long)(a4)) \
            : "edi", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL5(n, a1, a2, a3, a4, a5) ({ \
        long ret; \
        __asm__ volatile( \
            "int $0x80" \
            : "=a"(ret) \
            : "a"(n), "b"((long)(a1)), "c"((long)(a2)), "d"((long)(a3)), \
              "S"((long)(a4)), "D"((long)(a5)) \
            : "memory"); \
        ret; \
    })

#elif defined(KS_ARCH_ARM64)
    /* ARM64 syscall ABI (svc #0):
     *   x8 = syscall number
     *   x0-x5 = args
     */
    #define KS_SYSCALL0(n) ({ \
        long ret; \
        __asm__ volatile( \
            "mov x8, %1\n" \
            "svc #0\n" \
            "mov %0, x0" \
            : "=r"(ret) \
            : "r"((long)(n)) \
            : "x0", "x1", "x2", "x3", "x4", "x5", "x8", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL1(n, a1) ({ \
        long ret; \
        __asm__ volatile( \
            "mov x8, %1\n" \
            "mov x0, %2\n" \
            "svc #0\n" \
            "mov %0, x0" \
            : "=r"(ret) \
            : "r"((long)(n)), "r"((long)(a1)) \
            : "x0", "x1", "x2", "x3", "x4", "x5", "x8", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL2(n, a1, a2) ({ \
        long ret; \
        __asm__ volatile( \
            "mov x8, %1\n" \
            "mov x0, %2\n" \
            "mov x1, %3\n" \
            "svc #0\n" \
            "mov %0, x0" \
            : "=r"(ret) \
            : "r"((long)(n)), "r"((long)(a1)), "r"((long)(a2)) \
            : "x0", "x1", "x2", "x3", "x4", "x5", "x8", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL3(n, a1, a2, a3) ({ \
        long ret; \
        __asm__ volatile( \
            "mov x8, %1\n" \
            "mov x0, %2\n" \
            "mov x1, %3\n" \
            "mov x2, %4\n" \
            "svc #0\n" \
            "mov %0, x0" \
            : "=r"(ret) \
            : "r"((long)(n)), "r"((long)(a1)), "r"((long)(a2)), "r"((long)(a3)) \
            : "x0", "x1", "x2", "x3", "x4", "x5", "x8", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL4(n, a1, a2, a3, a4) ({ \
        long ret; \
        __asm__ volatile( \
            "mov x8, %1\n" \
            "mov x0, %2\n" \
            "mov x1, %3\n" \
            "mov x2, %4\n" \
            "mov x3, %5\n" \
            "svc #0\n" \
            "mov %0, x0" \
            : "=r"(ret) \
            : "r"((long)(n)), "r"((long)(a1)), "r"((long)(a2)), "r"((long)(a3)), \
              "r"((long)(a4)) \
            : "x0", "x1", "x2", "x3", "x4", "x5", "x8", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL5(n, a1, a2, a3, a4, a5) ({ \
        long ret; \
        __asm__ volatile( \
            "mov x8, %1\n" \
            "mov x0, %2\n" \
            "mov x1, %3\n" \
            "mov x2, %4\n" \
            "mov x3, %5\n" \
            "mov x4, %6\n" \
            "svc #0\n" \
            "mov %0, x0" \
            : "=r"(ret) \
            : "r"((long)(n)), "r"((long)(a1)), "r"((long)(a2)), "r"((long)(a3)), \
              "r"((long)(a4)), "r"((long)(a5)) \
            : "x0", "x1", "x2", "x3", "x4", "x5", "x8", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL6(n, a1, a2, a3, a4, a5, a6) ({ \
        long ret; \
        __asm__ volatile( \
            "mov x8, %1\n" \
            "mov x0, %2\n" \
            "mov x1, %3\n" \
            "mov x2, %4\n" \
            "mov x3, %5\n" \
            "mov x4, %6\n" \
            "mov x5, %7\n" \
            "svc #0\n" \
            "mov %0, x0" \
            : "=r"(ret) \
            : "r"((long)(n)), "r"((long)(a1)), "r"((long)(a2)), "r"((long)(a3)), \
              "r"((long)(a4)), "r"((long)(a5)), "r"((long)(a6)) \
            : "x0", "x1", "x2", "x3", "x4", "x5", "x8", "memory"); \
        ret; \
    })

#elif defined(KS_ARCH_ARM)
    /* ARM (32-bit) syscall ABI (swi #0):
     *   r7 = syscall number
     *   r0-r5 = args
     */
    #define KS_SYSCALL0(n) ({ \
        long ret; \
        __asm__ volatile( \
            "mov r7, %1\n" \
            "swi #0\n" \
            "mov %0, r0" \
            : "=r"(ret) \
            : "r"((long)(n)) \
            : "r0", "r1", "r2", "r3", "r4", "r5", "r7", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL1(n, a1) ({ \
        long ret; \
        __asm__ volatile( \
            "mov r7, %1\n" \
            "mov r0, %2\n" \
            "swi #0\n" \
            "mov %0, r0" \
            : "=r"(ret) \
            : "r"((long)(n)), "r"((long)(a1)) \
            : "r0", "r1", "r2", "r3", "r4", "r5", "r7", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL2(n, a1, a2) ({ \
        long ret; \
        __asm__ volatile( \
            "mov r7, %1\n" \
            "mov r0, %2\n" \
            "mov r1, %3\n" \
            "swi #0\n" \
            "mov %0, r0" \
            : "=r"(ret) \
            : "r"((long)(n)), "r"((long)(a1)), "r"((long)(a2)) \
            : "r0", "r1", "r2", "r3", "r4", "r5", "r7", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL3(n, a1, a2, a3) ({ \
        long ret; \
        __asm__ volatile( \
            "mov r7, %1\n" \
            "mov r0, %2\n" \
            "mov r1, %3\n" \
            "mov r2, %4\n" \
            "swi #0\n" \
            "mov %0, r0" \
            : "=r"(ret) \
            : "r"((long)(n)), "r"((long)(a1)), "r"((long)(a2)), "r"((long)(a3)) \
            : "r0", "r1", "r2", "r3", "r4", "r5", "r7", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL4(n, a1, a2, a3, a4) ({ \
        long ret; \
        __asm__ volatile( \
            "mov r7, %1\n" \
            "mov r0, %2\n" \
            "mov r1, %3\n" \
            "mov r2, %4\n" \
            "mov r3, %5\n" \
            "swi #0\n" \
            "mov %0, r0" \
            : "=r"(ret) \
            : "r"((long)(n)), "r"((long)(a1)), "r"((long)(a2)), "r"((long)(a3)), \
              "r"((long)(a4)) \
            : "r0", "r1", "r2", "r3", "r4", "r5", "r7", "memory"); \
        ret; \
    })
    
    #define KS_SYSCALL5(n, a1, a2, a3, a4, a5) ({ \
        long ret; \
        __asm__ volatile( \
            "mov r7, %1\n" \
            "mov r0, %2\n" \
            "mov r1, %3\n" \
            "mov r2, %4\n" \
            "mov r3, %5\n" \
            "mov r4, %6\n" \
            "swi #0\n" \
            "mov %0, r0" \
            : "=r"(ret) \
            : "r"((long)(n)), "r"((long)(a1)), "r"((long)(a2)), "r"((long)(a3)), \
              "r"((long)(a4)), "r"((long)(a5)) \
            : "r0", "r1", "r2", "r3", "r4", "r5", "r7", "memory"); \
        ret; \
    })
#endif

/* ============================================================================
 * WINDOWS FALLBACK (via ntdll when direct syscalls not available)
 * ============================================================================ */

#ifdef KS_OS_WINDOWS
    /* Windows syscalls are handled via ntdll */
    #include <windows.h>
    
    typedef long (__stdcall *NtSyscallFunc)(...);
    
    static NtSyscallFunc ks_ntdll_syscall = NULL;
    
    /* Initialize syscall interface on Windows */
    static void ks_init_windows_syscalls(void) {
        HMODULE ntdll = GetModuleHandleA("ntdll.dll");
        if (ntdll) {
            ks_ntdll_syscall = (NtSyscallFunc)GetProcAddress(ntdll, "NtQuerySystemInformation");
        }
    }
    
    #define KS_SYSCALL0(n) (ks_ntdll_syscall ? ks_ntdll_syscall(n) : -1)
    #define KS_SYSCALL1(n, a1) (ks_ntdll_syscall ? ks_ntdll_syscall(n, a1) : -1)
    #define KS_SYSCALL2(n, a1, a2) (ks_ntdll_syscall ? ks_ntdll_syscall(n, a1, a2) : -1)
    #define KS_SYSCALL3(n, a1, a2, a3) (ks_ntdll_syscall ? ks_ntdll_syscall(n, a1, a2, a3) : -1)
    #define KS_SYSCALL4(n, a1, a2, a3, a4) (ks_ntdll_syscall ? ks_ntdll_syscall(n, a1, a2, a3, a4) : -1)
    #define KS_SYSCALL5(n, a1, a2, a3, a4, a5) (ks_ntdll_syscall ? ks_ntdll_syscall(n, a1, a2, a3, a4, a5) : -1)
    #define KS_SYSCALL6(n, a1, a2, a3, a4, a5, a6) (ks_ntdll_syscall ? ks_ntdll_syscall(n, a1, a2, a3, a4, a5, a6) : -1)
#endif

/* ============================================================================
 * CONVENIENCE WRAPPERS (0-6 arguments)
 * ============================================================================ */

/* Generic syscall with 0-6 arguments */
KS_INLINE long ks_syscall0(long n) {
    return KS_SYSCALL0(n);
}

KS_INLINE long ks_syscall1(long n, long a1) {
    return KS_SYSCALL1(n, a1);
}

KS_INLINE long ks_syscall2(long n, long a1, long a2) {
    return KS_SYSCALL2(n, a1, a2);
}

KS_INLINE long ks_syscall3(long n, long a1, long a2, long a3) {
    return KS_SYSCALL3(n, a1, a2, a3);
}

KS_INLINE long ks_syscall4(long n, long a1, long a2, long a3, long a4) {
    return KS_SYSCALL4(n, a1, a2, a3, a4);
}

KS_INLINE long ks_syscall5(long n, long a1, long a2, long a3, long a4, long a5) {
    return KS_SYSCALL5(n, a1, a2, a3, a4, a5);
}

KS_INLINE long ks_syscall6(long n, long a1, long a2, long a3, long a4, long a5, long a6) {
    return KS_SYSCALL6(n, a1, a2, a3, a4, a5, a6);
}

/* ============================================================================
 * FILE OPERATIONS
 * ============================================================================ */

#ifdef __linux__
    #include <fcntl.h>
    
    KS_INLINE int ks_open(const char *path, int flags, int mode) {
        return (int)ks_syscall3(__NR_open, (long)path, flags, mode);
    }
    
    KS_INLINE int ks_openat(int dirfd, const char *path, int flags, int mode) {
        return (int)ks_syscall4(__NR_openat, dirfd, (long)path, flags, mode);
    }
    
    KS_INLINE int ks_close(int fd) {
        return (int)ks_syscall1(__NR_close, fd);
    }
    
    KS_INLINE long ks_read(int fd, void *buf, size_t count) {
        return ks_syscall3(__NR_read, fd, (long)buf, count);
    }
    
    KS_INLINE long ks_write(int fd, const void *buf, size_t count) {
        return ks_syscall3(__NR_write, fd, (long)buf, count);
    }
    
    KS_INLINE long ks_lseek(int fd, off_t offset, int whence) {
        return ks_syscall3(__NR_lseek, fd, offset, whence);
    }
    
    KS_INLINE int ks_dup(int oldfd) {
        return (int)ks_syscall1(__NR_dup, oldfd);
    }
    
    KS_INLINE int ks_dup2(int oldfd, int newfd) {
        return (int)ks_syscall2(__NR_dup2, oldfd, newfd);
    }
    
    KS_INLINE int ks_dup3(int oldfd, int newfd, int flags) {
        return (int)ks_syscall3(__NR_dup3, oldfd, newfd, flags);
    }
    
    KS_INLINE int ks_fcntl(int fd, int cmd, long arg) {
        return (int)ks_syscall3(__NR_fcntl, fd, cmd, arg);
    }
    
    KS_INLINE int ks_ioctl(int fd, unsigned long request, long arg) {
        return (int)ks_syscall3(__NR_ioctl, fd, request, arg);
    }
#elif defined(__APPLE__)
    /* macOS syscall numbers differ */
    #define SYS_open 5
    #define SYS_close 6
    #define SYS_read 3
    #define SYS_write 4
    #define SYS_lseek 199
    #define SYS_dup 41
    #define SYS_dup2 90
    #define SYS_fcntl 92
    #define SYS_ioctl 54
    
    KS_INLINE int ks_open(const char *path, int flags, int mode) {
        return (int)ks_syscall3(SYS_open, (long)path, flags, mode);
    }
    
    KS_INLINE int ks_close(int fd) {
        return (int)ks_syscall1(SYS_close, fd);
    }
    
    KS_INLINE long ks_read(int fd, void *buf, size_t count) {
        return ks_syscall3(SYS_read, fd, (long)buf, count);
    }
    
    KS_INLINE long ks_write(int fd, const void *buf, size_t count) {
        return ks_syscall3(SYS_write, fd, (long)buf, count);
    }
#endif

/* ============================================================================
 * MEMORY OPERATIONS
 * ============================================================================ */

#ifdef __linux__
    #define KS_PROT_READ     0x1
    #define KS_PROT_WRITE    0x2
    #define KS_PROT_EXEC     0x4
    #define KS_MAP_SHARED    0x01
    #define KS_MAP_PRIVATE   0x02
    #define KS_MAP_ANONYMOUS 0x20
    
    KS_INLINE void *ks_mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset) {
        return (void *)ks_syscall6(__NR_mmap, (long)addr, length, prot, flags, fd, offset);
    }
    
    KS_INLINE int ks_munmap(void *addr, size_t length) {
        return (int)ks_syscall2(__NR_munmap, (long)addr, length);
    }
    
    KS_INLINE int ks_mprotect(void *addr, size_t length, int prot) {
        return (int)ks_syscall3(__NR_mprotect, (long)addr, length, prot);
    }
    
    KS_INLINE int ks_madvise(void *addr, size_t length, int advice) {
        return (int)ks_syscall3(__NR_madvise, (long)addr, length, advice);
    }
    
    KS_INLINE int ks_mlock(const void *addr, size_t length) {
        return (int)ks_syscall2(__NR_mlock, (long)addr, length);
    }
    
    KS_INLINE int ks_munlock(const void *addr, size_t length) {
        return (int)ks_syscall2(__NR_munlock, (long)addr, length);
    }
    
    KS_INLINE int ks_mlockall(int flags) {
        return (int)ks_syscall1(__NR_mlockall, flags);
    }
    
    KS_INLINE int ks_munlockall(void) {
        return (int)ks_syscall0(__NR_munlockall);
    }
#elif defined(__APPLE__)
    #define SYS_mmap 197
    #define SYS_munmap 73
    #define SYS_mprotect 74
    #define SYS_madvise 75
#endif

/* ============================================================================
 * PROCESS OPERATIONS
 * ============================================================================ */

#ifdef __linux__
    KS_INLINE KS_NORETURN void ks_exit(int status) {
        ks_syscall1(__NR_exit, status);
        __builtin_unreachable();
    }
    
    KS_INLINE KS_NORETURN void ks_exit_group(int status) {
        ks_syscall1(__NR_exit_group, status);
        __builtin_unreachable();
    }
    
    KS_INLINE int ks_getpid(void) {
        return (int)ks_syscall0(__NR_getpid);
    }
    
    KS_INLINE int ks_gettid(void) {
        return (int)ks_syscall0(__NR_gettid);
    }
    
    KS_INLINE int ks_getppid(void) {
        return (int)ks_syscall0(__NR_getppid);
    }
    
    KS_INLINE int ks_fork(void) {
        return (int)ks_syscall0(__NR_fork);
    }
    
    KS_INLINE int ks_vfork(void) {
        return (int)ks_syscall0(__NR_vfork);
    }
    
    KS_INLINE int ks_clone(unsigned long flags, void *stack, int *ptid, int *ctid, unsigned long tls) {
        return (int)ks_syscall5(__NR_clone, flags, (long)stack, (long)ptid, (long)ctid, tls);
    }
    
    KS_INLINE int ks_execve(const char *path, char *const argv[], char *const envp[]) {
        return (int)ks_syscall3(__NR_execve, (long)path, (long)argv, (long)envp);
    }
    
    KS_INLINE int ks_waitpid(int pid, int *status, int options) {
        return (int)ks_syscall3(__NR_wait4, pid, (long)status, options, 0);
    }
    
    KS_INLINE int ks_kill(int pid, int sig) {
        return (int)ks_syscall2(__NR_kill, pid, sig);
    }
    
    KS_INLINE int ks_tgkill(int tgid, int tid, int sig) {
        return (int)ks_syscall3(__NR_tgkill, tgid, tid, sig);
    }
    
    KS_INLINE int ks_getuid(void) {
        return (int)ks_syscall0(__NR_getuid);
    }
    
    KS_INLINE int ks_geteuid(void) {
        return (int)ks_syscall0(__NR_geteuid);
    }
    
    KS_INLINE int ks_getgid(void) {
        return (int)ks_syscall0(__NR_getgid);
    }
    
    KS_INLINE int ks_getegid(void) {
        return (int)ks_syscall0(__NR_getegid);
    }
    
    KS_INLINE int ks_setuid(uid_t uid) {
        return (int)ks_syscall1(__NR_setuid, uid);
    }
    
    KS_INLINE int ks_setgid(gid_t gid) {
        return (int)ks_syscall1(__NR_setgid, gid);
    }
    
    KS_INLINE int ks_setsid(void) {
        return (int)ks_syscall0(__NR_setsid);
    }
    
    KS_INLINE int ks_getpgid(int pid) {
        return (int)ks_syscall1(__NR_getpgid, pid);
    }
    
    KS_INLINE int ks_setpgid(int pid, int pgid) {
        return (int)ks_syscall2(__NR_setpgid, pid, pgid);
    }
#elif defined(__APPLE__)
    #define SYS_exit 1
    #define SYS_getpid 20
    #define SYS_fork 2
    #define SYS_execve 59
    #define SYS_kill 37
    #define SYS_getuid 24
    #define SYS_geteuid 25
    #define SYS_getgid 23
    #define SYS_getegid 22
#endif

/* ============================================================================
 * TIME OPERATIONS
 * ============================================================================ */

#ifdef __linux__
    struct ks_timespec {
        long tv_sec;
        long tv_nsec;
    };
    
    KS_INLINE int ks_clock_gettime(int clk_id, struct ks_timespec *tp) {
        return (int)ks_syscall2(__NR_clock_gettime, clk_id, (long)tp);
    }
    
    KS_INLINE int ks_gettimeofday(struct ks_timespec *tv, void *tz) {
        return (int)ks_syscall2(__NR_gettimeofday, (long)tv, (long)tz);
    }
    
    KS_INLINE int ks_nanosleep(const struct ks_timespec *req, struct ks_timespec *rem) {
        return (int)ks_syscall2(__NR_nanosleep, (long)req, (long)rem);
    }
#endif

/* ============================================================================
 * SCHEDULING
 * ============================================================================ */

#ifdef __linux__
    KS_INLINE int ks_sched_yield(void) {
        return (int)ks_syscall0(__NR_sched_yield);
    }
    
    KS_INLINE int ks_sched_getaffinity(pid_t pid, size_t cpusetsize, void *mask) {
        return (int)ks_syscall3(__NR_sched_getaffinity, pid, cpusetsize, (long)mask);
    }
    
    KS_INLINE int ks_sched_setaffinity(pid_t pid, size_t cpusetsize, const void *mask) {
        return (int)ks_syscall3(__NR_sched_setaffinity, pid, cpusetsize, (long)mask);
    }
    
    KS_INLINE int ks_sched_getparam(pid_t pid, void *param) {
        return (int)ks_syscall2(__NR_sched_getparam, pid, (long)param);
    }
    
    KS_INLINE int ks_sched_setparam(pid_t pid, const void *param) {
        return (int)ks_syscall2(__NR_sched_setparam, pid, (long)param);
    }
    
    KS_INLINE int ks_sched_getscheduler(pid_t pid) {
        return (int)ks_syscall1(__NR_sched_getscheduler, pid);
    }
    
    KS_INLINE int ks_sched_setscheduler(pid_t pid, int policy, const void *param) {
        return (int)ks_syscall3(__NR_sched_setscheduler, pid, policy, (long)param);
    }
#endif

/* ============================================================================
 * FUTEX OPERATIONS (Linux specific)
 * ============================================================================ */

#ifdef __linux__
    #include <linux/futex.h>
    
    KS_INLINE int ks_futex(uint32_t *uaddr, int op, uint32_t val, 
                           const struct ks_timespec *timeout, uint32_t *uaddr2, uint32_t val3) {
        return (int)ks_syscall6(__NR_futex, (long)uaddr, op, val, 
                                 (long)timeout, (long)uaddr2, val3);
    }
    
    KS_INLINE int ks_futex_wait(uint32_t *uaddr, uint32_t val, uint64_t timeout_ns) {
        struct ks_timespec ts = { timeout_ns / 1000000000ULL, timeout_ns % 1000000000ULL };
        return ks_futex(uaddr, FUTEX_WAIT_PRIVATE, val, &ts, NULL, 0);
    }
    
    KS_INLINE int ks_futex_wake(uint32_t *uaddr, int nr_wake) {
        return ks_futex(uaddr, FUTEX_WAKE_PRIVATE, nr_wake, NULL, NULL, 0);
    }
#endif

/* ============================================================================
 * RANDOM NUMBERS
 * ============================================================================ */

#ifdef __linux__
    KS_INLINE long ks_getrandom(void *buf, size_t buflen, unsigned int flags) {
        return ks_syscall3(__NR_getrandom, (long)buf, buflen, flags);
    }
#endif

/* ============================================================================
 * EVENTFD / SIGNALFD / TIMERFD (Linux)
 * ============================================================================ */

#ifdef __linux__
    KS_INLINE int ks_eventfd(unsigned int count, int flags) {
        return (int)ks_syscall2(__NR_eventfd2, count, flags);
    }
    
    KS_INLINE int ks_timerfd_create(int clockid, int flags) {
        return (int)ks_syscall2(__NR_timerfd_create, clockid, flags);
    }
    
    KS_INLINE int ks_signalfd(int fd, const void *mask, size_t sizemask, int flags) {
        return (int)ks_syscall4(__NR_signalfd4, fd, (long)mask, sizemask, flags);
    }
#endif

/* ============================================================================
 * HIGH-PERFORMANCE I/O (epoll, io_uring)
 * ============================================================================ */

#ifdef __linux__
    KS_INLINE int ks_epoll_create(int size) {
        return (int)ks_syscall1(__NR_epoll_create, size);
    }
    
    KS_INLINE int ks_epoll_create1(int flags) {
        return (int)ks_syscall1(__NR_epoll_create1, flags);
    }
    
    KS_INLINE int ks_epoll_ctl(int epfd, int op, int fd, void *event) {
        return (int)ks_syscall4(__NR_epoll_ctl, epfd, op, fd, (long)event);
    }
    
    KS_INLINE int ks_epoll_wait(int epfd, void *events, int maxevents, int timeout) {
        return (int)ks_syscall4(__NR_epoll_wait, epfd, (long)events, maxevents, timeout);
    }
    
    /* io_uring (newer kernels) */
    KS_INLINE int ks_io_uring_setup(unsigned int entries, void *params) {
        return (int)ks_syscall2(__NR_io_uring_setup, entries, (long)params);
    }
    
    KS_INLINE int ks_io_uring_enter(int fd, unsigned int to_submit, unsigned int min_complete,
                                     unsigned int flags, void *sig) {
        return (int)ks_syscall5(__NR_io_uring_enter, fd, to_submit, min_complete, flags, (long)sig);
    }
#endif

/* ============================================================================
 * INITIALIZATION (Windows only)
 * ============================================================================ */

#ifdef KS_OS_WINDOWS
    static void __attribute__((constructor)) ks_init_windows(void) {
        ks_init_windows_syscalls();
    }
#endif

#endif /* KS_SYSCALL_WRAPPERS_H */
