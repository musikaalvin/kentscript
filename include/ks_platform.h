/* ============================================================================
 * ks_platform.h - Architecture & Platform Detection
 * Include this FIRST in every generated C file
 * ========================================================================== */

#ifndef KS_PLATFORM_H
#define KS_PLATFORM_H

/* Architecture Detection */
#if defined(__x86_64__) || defined(__amd64__) || defined(_M_X64)
    #define KS_ARCH_X86_64 1
    #define KS_ARCH "x86_64"
    #define KS_CACHE_LINE 64
    #define KS_PAGE_SIZE 4096
    #define KS_HAS_RDTSC 1
    #define KS_HAS_CPUID 1
#elif defined(__aarch64__) || defined(__arm64__) || defined(_M_ARM64)
    #define KS_ARCH_ARM64 1
    #define KS_ARCH "aarch64"
    #define KS_CACHE_LINE 64
    #define KS_PAGE_SIZE 4096
    #define KS_HAS_CNTVCT 1
#elif defined(__arm__) || defined(_M_ARM)
    #define KS_ARCH_ARM32 1
    #define KS_ARCH "arm"
    #define KS_CACHE_LINE 32
    #define KS_PAGE_SIZE 4096
#elif defined(__riscv) && __riscv_xlen == 64
    #define KS_ARCH_RISCV64 1
    #define KS_ARCH "riscv64"
    #define KS_CACHE_LINE 64
    #define KS_PAGE_SIZE 4096
#elif defined(__powerpc64__) || defined(__ppc64__)
    #define KS_ARCH_PPC64 1
    #define KS_ARCH "ppc64"
    #define KS_CACHE_LINE 128
    #define KS_PAGE_SIZE 65536
#else
    #error "Unsupported architecture for KentScript"
#endif

/* OS Detection */
#if defined(__linux__)
    #define KS_OS_LINUX 1
    #define KS_OS "linux"
#elif defined(__APPLE__) && defined(__MACH__)
    #define KS_OS_MACOS 1
    #define KS_OS "macos"
#elif defined(_WIN32) || defined(_WIN64)
    #define KS_OS_WINDOWS 1
    #define KS_OS "windows"
#elif defined(__FreeBSD__) || defined(__OpenBSD__) || defined(__NetBSD__)
    #define KS_OS_BSD 1
    #define KS_OS "bsd"
#else
    #define KS_OS "unknown"
#endif

/* Compiler Detection */
#if defined(__clang__)
    #define KS_COMPILER_CLANG 1
    #define KS_COMPILER "clang"
    #define KS_COMPILER_VERSION __clang_version__
#elif defined(__GNUC__) || defined(__GNUG__)
    #define KS_COMPILER_GCC 1
    #define KS_COMPILER "gcc"
    #define KS_COMPILER_VERSION __VERSION__
#elif defined(_MSC_VER)
    #define KS_COMPILER_MSVC 1
    #define KS_COMPILER "msvc"
    #define KS_COMPILER_VERSION _MSC_VER
#endif

/* Ring Level Detection */
#ifdef __KERNEL__
    #define KS_RING_LEVEL 0
    #define KS_RING "ring0"
#else
    #define KS_RING_LEVEL 3
    #define KS_RING "ring3"
#endif

/* CPU pause/spin-wait hint */
#if defined(KS_ARCH_X86_64)
    #define KS_PAUSE() __asm__ volatile("pause" ::: "memory")
#elif defined(KS_ARCH_ARM64)
    #define KS_PAUSE() __asm__ volatile("yield" ::: "memory")
#else
    #define KS_PAUSE() do {} while(0)
#endif

#endif /* KS_PLATFORM_H */
