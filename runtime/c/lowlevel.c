#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdarg.h>
#include <stdint.h>

/* ===== HOOK 2: SIMD & Hardware Optimization Macros ===== */
#define RESTRICT __restrict
#define ALIGNED(n) __attribute__((aligned(n)))
#define ALIGNED_16 __attribute__((aligned(16)))
#define ALIGNED_32 __attribute__((aligned(32)))
#define HOT __attribute__((hot))
#define COLD __attribute__((cold))
#define INLINE __attribute__((always_inline)) inline
#define NORETURN __attribute__((noreturn))
#define LIKELY(x) __builtin_expect(!!(x), 1)
#define UNLIKELY(x) __builtin_expect(!!(x), 0)
/* ===== END HOOK 2 ===== */

/* ---- Hardware I/O Port Access (Cross-Platform: x86-64 & ARM64) ---- */
#if defined(__x86_64__) || defined(__i386__) || defined(_M_X64) || defined(_M_IX86)
  /* x86/x64: Uses I/O Ports (inb/outb) */
  static inline unsigned char inb(unsigned short port) {
      unsigned char rv;
      __asm__ __volatile__ ("inb %w1, %b0" : "=a" (rv) : "Nd" (port));
      return rv;
  }
  static inline unsigned short inw(unsigned short port) {
      unsigned short rv;
      __asm__ __volatile__ ("inw %w1, %w0" : "=a" (rv) : "Nd" (port));
      return rv;
  }
  static inline unsigned int inl(unsigned short port) {
      unsigned int rv;
      __asm__ __volatile__ ("inl %w1, %0" : "=a" (rv) : "Nd" (port));
      return rv;
  }
  static inline void outb(unsigned char value, unsigned short port) {
      __asm__ __volatile__ ("outb %b0, %w1" : : "a" (value), "Nd" (port));
  }
  static inline void outw(unsigned short value, unsigned short port) {
      __asm__ __volatile__ ("outw %w0, %w1" : : "a" (value), "Nd" (port));
  }
  static inline void outl(unsigned int value, unsigned short port) {
      __asm__ __volatile__ ("outl %0, %w1" : : "a" (value), "Nd" (port));
  }
#elif defined(__aarch64__) || defined(__arm__) || defined(_M_ARM64)
  /* ARM64/ARM: Uses Memory-Mapped I/O (MMIO) - NO port I/O */
  /* RTC is accessed via fixed MMIO address (e.g., 0x09010000) */
  static inline unsigned char inb(unsigned short port) {
      /* ARM has no port I/O - stub returns 0 */
      (void)port; /* suppress unused warning */
      return 0;
  }
  static inline unsigned short inw(unsigned short port) {
      (void)port;
      return 0;
  }
  static inline unsigned int inl(unsigned short port) {
      (void)port;
      return 0;
  }
  static inline void outb(unsigned char value, unsigned short port) {
      (void)value; (void)port;
  }
  static inline void outw(unsigned short value, unsigned short port) {
      (void)value; (void)port;
  }
  static inline void outl(unsigned int value, unsigned short port) {
      (void)value; (void)port;
  }
#else
  #error "Unsupported architecture. KentScript supports x86/x64 and ARM64."
#endif

#ifdef __aarch64__
#include <arm_neon.h>
static inline uint64_t read_cycle_counter(void) {
    uint64_t cycles;
    __asm__ __volatile__("mrs %0, pmccntr_el0" : "=r" (cycles));
    return cycles;
}
static inline void enable_cycle_counter(void) {
    uint64_t val;
    __asm__ __volatile__("mrs %0, pmcr_el0" : "=r" (val));
    val |= (1 << 0);
    __asm__ __volatile__("msr pmcr_el0, %0" : : "r" (val));
}
#else
static inline uint64_t read_cycle_counter(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}
static inline void enable_cycle_counter(void) {}
#endif

/* ---- Memory-Mapped I/O (MMIO) Helper Functions ---- */
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <sys/types.h>
#include <sys/stat.h>
#endif
static long long _ks_read_mmio(unsigned long addr, int size) {
    int fd = open("/dev/mem", O_RDONLY);
    if (fd < 0) return 0;
    unsigned long page_size = 4096;
    unsigned long page_addr = (addr / page_size) * page_size;
    unsigned long offset = addr - page_addr;
    void *map = mmap(NULL, page_size, PROT_READ, MAP_SHARED, fd, page_addr);
    if (map == MAP_FAILED) { close(fd); return 0; }
    long long result = 0;
    if (size == 1) {
        unsigned char *p = (unsigned char *)map + offset;
        result = (long long)*p;
    } else if (size == 2) {
        unsigned short *p = (unsigned short *)((unsigned char *)map + offset);
        result = (long long)*p;
    } else if (size == 4) {
        unsigned int *p = (unsigned int *)((unsigned char *)map + offset);
        result = (long long)*p;
    } else if (size == 8) {
        unsigned long long *p = (unsigned long long *)((unsigned char *)map + offset);
        result = (long long)*p;
    }
    munmap(map, page_size);
    close(fd);
    return result;
}
static void _ks_write_mmio(unsigned long addr, long long value, int size) {
    int fd = open("/dev/mem", O_RDWR);
    if (fd < 0) return;
    unsigned long page_size = 4096;
    unsigned long page_addr = (addr / page_size) * page_size;
    unsigned long offset = addr - page_addr;
    void *map = mmap(NULL, page_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, page_addr);
    if (map == MAP_FAILED) { close(fd); return; }
    if (size == 1) {
        unsigned char *p = (unsigned char *)map + offset;
        *p = (unsigned char)value;
    } else if (size == 2) {
        unsigned short *p = (unsigned short *)((unsigned char *)map + offset);
        *p = (unsigned short)value;
    } else if (size == 4) {
        unsigned int *p = (unsigned int *)((unsigned char *)map + offset);
        *p = (unsigned int)value;
    } else if (size == 8) {
        unsigned long long *p = (unsigned long long *)((unsigned char *)map + offset);
        *p = (unsigned long long)value;
    }
    munmap(map, page_size);
    close(fd);
}

/* ---- KentScript runtime [KS-REF-020] ----                   */
/* Standalone build: helpers defined inline below.               */
/* Production build: #include "ks_runtime.h" + link ks_runtime.a */
#ifndef KS_RUNTIME_H
static char _ks_bufs[64][4096];
static int  _ks_buf_idx = 0;
static char* _ks_newbuf(void) {
    _ks_buf_idx = (_ks_buf_idx + 1) % 64;
    _ks_bufs[_ks_buf_idx][0] = 0;
    return _ks_bufs[_ks_buf_idx];
}
static char* _ks_str_int(long long v) {
    char *b = _ks_newbuf();
    snprintf(b, 4096, "%lld", v); return b;
}
static char* _ks_str_dbl(double v) {
    char *b = _ks_newbuf();
    if (v == (long long)v) snprintf(b,4096,"%.1f",v);
    else snprintf(b,4096,"%g",v); return b;
}
static char* _ks_concat(const char* a, const char* b) {
    char *r = _ks_newbuf();
    snprintf(r, 4096, "%s%s", a, b); return r;
}
/* [KS-REF-011] Monotonic ms timer */
static double ks_time_monotonic_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec*1000.0 + (double)ts.tv_nsec/1000000.0;
}
/* [KS-REF-001] i64 array — calloc fallback (no mmap slab in standalone) */
static long long* ks_alloc_i64(long long n) {
    return (long long*)calloc((size_t)n, sizeof(long long));
}
/* [KS-REF-008] Memory barriers */
#if defined(__aarch64__) || defined(__arm__)
#  define KS_BARRIER() __asm__ volatile("dmb ish" ::: "memory")
#elif defined(__x86_64__) || defined(__i386__)
#  define KS_BARRIER() __asm__ volatile("mfence" ::: "memory")
#else
#  define KS_BARRIER() __sync_synchronize()
#endif
#define ks_free free
/* [KS-REF-001] Memory access builtins */
static void write_byte(void* ptr, long long offset, long long val) {
    ((unsigned char*)ptr)[offset] = (unsigned char)val;
}
static long long read_byte(void* ptr, long long offset) {
    return (long long)((unsigned char*)ptr)[offset];
}
static void write_word(void* ptr, long long off, long long val, int sz) {
    if(sz==8) *(uint64_t*)((char*)ptr+off)=(uint64_t)val;
    else if(sz==4) *(uint32_t*)((char*)ptr+off)=(uint32_t)val;
    else *(uint16_t*)((char*)ptr+off)=(uint16_t)val;
}
static long long read_word(void* ptr, long long off, int sz) {
    if(sz==8) return (long long)*(uint64_t*)((char*)ptr+off);
    else if(sz==4) return (long long)*(uint32_t*)((char*)ptr+off);
    return (long long)*(uint16_t*)((char*)ptr+off);
}
/* Hardware access functions */
#if defined(__x86_64__) || defined(__i386__)
static inline uint8_t _ks_io_read(uint16_t port) {
    uint8_t val;
    __asm__ volatile("inb %1, %0" : "=a"(val) : "Nd"(port));
    return val;
}
static inline void _ks_io_write(uint16_t port, uint8_t val) {
    __asm__ volatile("outb %0, %1" :: "a"(val), "Nd"(port));
}
static inline uint64_t _ks_msr_read(uint32_t msr) {
    uint32_t lo, hi;
    __asm__ volatile("rdmsr" : "=a"(lo), "=d"(hi) : "c"(msr));
    return ((uint64_t)hi << 32) | lo;
}
static inline void _ks_msr_write(uint32_t msr, uint64_t val) {
    uint32_t lo = val & 0xFFFFFFFF;
    uint32_t hi = val >> 32;
    __asm__ volatile("wrmsr" :: "a"(lo), "d"(hi), "c"(msr));
}
#elif defined(__aarch64__) || defined(__arm__)
static inline uint32_t _ks_io_read(uint64_t addr) {
    return *(volatile uint32_t*)addr;
}
static inline void _ks_io_write(uint64_t addr, uint32_t val) {
    *(volatile uint32_t*)addr = val;
}
static inline uint64_t _ks_msr_read(uint32_t reg) {
    uint64_t val;
    __asm__ volatile("mrs %0, s3_0_c0_c0_0" : "=r"(val));
    return val;
}
static inline void _ks_msr_write(uint32_t reg, uint64_t val) {
    __asm__ volatile("msr s3_0_c0_c0_0, %0" :: "r"(val));
}
#else
static inline uint32_t _ks_io_read(uint64_t addr) { return 0; }
static inline void _ks_io_write(uint64_t addr, uint32_t val) {}
static inline uint64_t _ks_msr_read(uint32_t reg) { return 0; }
static inline void _ks_msr_write(uint32_t reg, uint64_t val) {}
#endif
#endif /* KS_RUNTIME_H */

long long test_hardware(void);

long long test_hardware(void) {
    char* port_val = port_in(_ks_str_int(1016));
    port_out(_ks_str_int(1016), _ks_str_int(65));
    char* cr3 = read_cr3();
    return cr3;
    return 0LL;
}

int main(void) {
    return 0;
}