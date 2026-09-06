#define _POSIX_C_SOURCE 200809L
#define _DEFAULT_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>
#include <time.h>
#include <stdarg.h>
#include <stdint.h>
#include "ks_native.h"
#include <sys/mman.h>
#include <unistd.h>
#include <sys/syscall.h>

/* KentScript compatibility macros (transitional: KS_NONE_VAL kept until None->ks_none() switch) */
#define KS_NONE_VAL 0x5F3759DF5F3759DFLL
#define None ((long long)0)
#define true 1
#define false 0

/* ===== KentScript tagged value type (ks_val_t) ===== */
typedef enum { KS_T_INT, KS_T_FLT, KS_T_BOOL, KS_T_STR, KS_T_NONE,
               KS_T_ARR, KS_T_OBJ, KS_T_DICT } ks_tag;
typedef struct ks_val {
    ks_tag tag;
    union {
        long long i;
        double f;
        int b;
        char* s;
        void* p;
    } as;
} ks_val_t;
/* ===== END ks_val_t ===== */

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

// Progress bar helpers
char* _ks_progress_bar(int percent, int width, char* color) {
    static char buf[256];
    int filled = (percent * width) / 100;
    int empty = width - filled;
    int pos = 0;
    for (int i = 0; i < filled; i++) pos += sprintf(buf + pos, "█");
    for (int i = 0; i < empty; i++) pos += sprintf(buf + pos, "░");
    pos += sprintf(buf + pos, " %d%%", percent);
    return buf;
}

char* _ks_progress_bar_cyber(int percent, int width, char* color) {
    static char buf[256];
    int filled = (percent * width) / 100;
    int empty = width - filled;
    char* chars[] = {"▓", "▒", "░"};
    int pos = 0;
    pos += sprintf(buf + pos, "╭");
    for (int i = 0; i < filled; i++) pos += sprintf(buf + pos, "%s", chars[i % 3]);
    for (int i = 0; i < empty; i++) pos += sprintf(buf + pos, "░");
    pos += sprintf(buf + pos, "╮ %5.1f%% %s", (double)percent, percent < 100 ? "▶" : "█");
    return buf;
}

char* _ks_progress_bar_matrix(int percent, int width) {
    static char buf[512];
    int filled = (percent * width) / 100;
    char* chars[] = {"█", "▓", "▒", "░"};
    int pos = 0;
    pos += sprintf(buf + pos, "┌"); for (int i = 0; i < width; i++) pos += sprintf(buf + pos, "─"); pos += sprintf(buf + pos, "┐\n");
    pos += sprintf(buf + pos, "│");
    for (int i = 0; i < filled; i++) pos += sprintf(buf + pos, "%s", chars[i % 4]);
    for (int i = filled; i < width; i++) pos += sprintf(buf + pos, "░");
    pos += sprintf(buf + pos, "│ %d%%\n", percent);
    pos += sprintf(buf + pos, "└"); for (int i = 0; i < width; i++) pos += sprintf(buf + pos, "─"); pos += sprintf(buf + pos, "┘");
    return buf;
}

// Colored output helper
static int _color_name_to_code(const char* name) {
    // FG colors
    if (strcmp(name, "black") == 0) return 30;
    if (strcmp(name, "red") == 0) return 31;
    if (strcmp(name, "green") == 0) return 32;
    if (strcmp(name, "yellow") == 0) return 33;
    if (strcmp(name, "blue") == 0) return 34;
    if (strcmp(name, "magenta") == 0) return 35;
    if (strcmp(name, "cyan") == 0) return 36;
    if (strcmp(name, "white") == 0) return 37;
    if (strcmp(name, "bright_black") == 0 || strcmp(name, "gray") == 0 || strcmp(name, "grey") == 0) return 90;
    if (strcmp(name, "bright_red") == 0) return 91;
    if (strcmp(name, "bright_green") == 0) return 92;
    if (strcmp(name, "bright_yellow") == 0) return 93;
    if (strcmp(name, "bright_blue") == 0) return 94;
    if (strcmp(name, "bright_magenta") == 0) return 95;
    if (strcmp(name, "bright_cyan") == 0) return 96;
    if (strcmp(name, "bright_white") == 0) return 97;
    if (strcmp(name, "dim") == 0) return 2;
    if (strcmp(name, "bold") == 0) return 1;
    if (strcmp(name, "italic") == 0) return 3;
    if (strcmp(name, "underline") == 0) return 4;
    return 30; // default
}

char* _ks_colored(char* text, char* fg, char* bg, char* style) {
    static char buf[4096];
    int codes[10]; int nc = 0;
    if (fg && strcmp(fg, "none") != 0) codes[nc++] = _color_name_to_code(fg);
    if (bg && strcmp(bg, "none") != 0) codes[nc++] = _color_name_to_code(bg) + 10;
    if (style && strcmp(style, "none") != 0) codes[nc++] = _color_name_to_code(style);
    int pos = sprintf(buf, "\033[");
    for (int i = 0; i < nc; i++) pos += sprintf(buf + pos, "%d%s", codes[i], i < nc-1 ? ";" : "m");
    pos += sprintf(buf + pos, "%s\033[0m", text);
    return buf;
}

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
#include "ks_runtime.h"
#include "ks_simd.h"
static inline void* _ks_simd_alloc(size_t n){
void* _p=0; if(n==0) n=1;
#if defined(_WIN32)||defined(_WIN64)
_p=_aligned_malloc(n,KS_SIMD_BYTES);
#else
if(posix_memalign(&_p,KS_SIMD_BYTES,n)!=0)_p=0;
#endif
return _p;}
static inline void _ks_simd_free(void* p){
#if defined(_WIN32)||defined(_WIN64)
_aligned_free(p);
#else
free(p);
#endif
}
#include "ks_gpu.h"

/* ---- Fallback inline helpers (only if ks_runtime.h functions missing) ---- */
#ifndef KS_RUNTIME_HAVE_ALL_FUNCS
static char _ks_bufs[64][4096];
static int  _ks_buf_idx = 0;
static char* _ks_newbuf(void) {
    _ks_buf_idx = (_ks_buf_idx + 1) % 64;
    _ks_bufs[_ks_buf_idx][0] = 0;
    return _ks_bufs[_ks_buf_idx];
}
static int ks_argc = 0;
static char** ks_argv = NULL;
static const char* _argparse_flags[32];
static int _argparse_nflags = 0;
static long long system_argparse_new(const char* prog){ (void)prog; _argparse_nflags = 0; return 1; }
static void system_argparse_add_argument(long long parser, const char* flag){ (void)parser; if((int)_argparse_nflags < 32) _argparse_flags[_argparse_nflags++] = flag; }
static void system_argparse_add_help(long long parser, const char* h){ (void)parser; (void)h; }
static char* _ks_str_int(long long v) {
    char *b = _ks_newbuf();
    snprintf(b, 4096, "%lld", v); return b;
}
static char* _ks_print_int(long long v) {
    /* KS_NONE_VAL is the tagged representation of none/None/null */
    if (v == KS_NONE_VAL) { char* b = _ks_newbuf(); strcpy(b, "None"); return b; }
    return _ks_str_int(v);
}
static char* _ks_str_hex(long long v) {
    char *b = _ks_newbuf();
    snprintf(b, 4096, "%llx", v); return b;
}
static char* _ks_str_dbl(double v) {
    char *b = _ks_newbuf();
    if (v == (long long)v) snprintf(b,4096,"%.1f",v);
    else snprintf(b,4096,"%.17g",v); return b;
}
static char* _ks_str_array(long long* arr, long long len) {
    char *b = _ks_newbuf();
    int pos = 0;
    pos += snprintf(b + pos, 4096 - pos, "[");
    for (long long i = 0; i < len && pos < 4090; i++) {
        if (i > 0) pos += snprintf(b + pos, 4096 - pos, ", ");
        pos += snprintf(b + pos, 4096 - pos, "%lld", arr[i]);
    }
    snprintf(b + pos, 4096 - pos, "]");
    return b;
}
static char* _ks_concat(const char* a, const char* b) {
    char *r = _ks_newbuf();
    snprintf(r, 4096, "%s%s", a, b); return r;
}
static char* _ks_format_value(long long v, const char* fmt) {
    char *r = _ks_newbuf(); char spec[64];
    snprintf(spec, sizeof(spec), "%%%s", fmt);
    snprintf(r, 4096, spec, v); return r;
}
static char* _ks_format_value_f(double v, const char* fmt) {
    char *r = _ks_newbuf(); char spec[64];
    snprintf(spec, sizeof(spec), "%%%s", fmt);
    snprintf(r, 4096, spec, v); return r;
}
#ifndef KS_ARRAY_DEFINED
typedef struct { ks_val_t* data; long long length; long long cap; } ks_array;
#define KS_ARRAY_DEFINED
#endif

/* ===== ks_val_t constructors / operators / printing (Phase A: ARR assumes long long elems) ===== */
static inline ks_val_t ks_int(long long v){ ks_val_t r; r.tag=KS_T_INT; r.as.i=v; return r; }
static inline ks_val_t ks_flt(double v){ ks_val_t r; r.tag=KS_T_FLT; r.as.f=v; return r; }
static inline ks_val_t ks_bool(int v){ ks_val_t r; r.tag=KS_T_BOOL; r.as.b=v?1:0; return r; }
static inline ks_val_t ks_str(char* v){ ks_val_t r; r.tag=KS_T_STR; r.as.s=v; return r; }
static inline ks_val_t ks_none(void){ ks_val_t r; r.tag=KS_T_NONE; r.as.i=0; return r; }
static inline ks_val_t ks_arr(ks_array* v){ ks_val_t r; r.tag=KS_T_ARR; r.as.p=(void*)v; return r; }
static inline ks_val_t ks_obj(void* v){ ks_val_t r; r.tag=KS_T_OBJ; r.as.p=v; return r; }
static inline ks_val_t ks_dict(void* v){ ks_val_t r; r.tag=KS_T_DICT; r.as.p=v; return r; }
#define KS_INT(x) ks_int((long long)(x))
#define KS_FLT(x) ks_flt((double)(x))
#define KS_BOOL(x) ks_bool((x))
#define KS_STR(x) ks_str((x))
#define KS_TAG(x) ((x).tag)
static char* ks_val_to_str(ks_val_t v);
static char* _ks_dict_repr(void*);
static inline ks_val_t ks_v_neg(ks_val_t a){
    if(a.tag==KS_T_INT) return ks_int(-a.as.i);
    if(a.tag==KS_T_FLT) return ks_flt(-a.as.f);
    return ks_none();
}
static ks_val_t ks_v_add(ks_val_t a, ks_val_t b){
    if(a.tag==KS_T_STR || b.tag==KS_T_STR){
        char* sa=ks_val_to_str(a); char* sb=ks_val_to_str(b);
        char* r=_ks_newbuf(); snprintf(r,4096,"%s%s",sa,sb); return ks_str(r);
    }
    if(a.tag==KS_T_FLT || b.tag==KS_T_FLT){
        double fa=(a.tag==KS_T_FLT)?a.as.f:(double)a.as.i;
        double fb=(b.tag==KS_T_FLT)?b.as.f:(double)b.as.i;
        return ks_flt(fa+fb);
    }
    long long ia=(a.tag==KS_T_INT)?a.as.i:0;
    long long ib=(b.tag==KS_T_INT)?b.as.i:0;
    return ks_int(ia+ib);
}
static ks_val_t ks_v_sub(ks_val_t a, ks_val_t b){
    if(a.tag==KS_T_FLT || b.tag==KS_T_FLT){
        double fa=(a.tag==KS_T_FLT)?a.as.f:(double)a.as.i;
        double fb=(b.tag==KS_T_FLT)?b.as.f:(double)b.as.i;
        return ks_flt(fa-fb);
    }
    long long ia=(a.tag==KS_T_INT)?a.as.i:0;
    long long ib=(b.tag==KS_T_INT)?b.as.i:0;
    return ks_int(ia-ib);
}
static ks_val_t ks_v_mul(ks_val_t a, ks_val_t b){
    if(a.tag==KS_T_FLT || b.tag==KS_T_FLT){
        double fa=(a.tag==KS_T_FLT)?a.as.f:(double)a.as.i;
        double fb=(b.tag==KS_T_FLT)?b.as.f:(double)b.as.i;
        return ks_flt(fa*fb);
    }
    long long ia=(a.tag==KS_T_INT)?a.as.i:0;
    long long ib=(b.tag==KS_T_INT)?b.as.i:0;
    return ks_int(ia*ib);
}
static ks_val_t ks_v_div(ks_val_t a, ks_val_t b){
    double fa=(a.tag==KS_T_FLT)?a.as.f:(double)a.as.i;
    double fb=(b.tag==KS_T_FLT)?b.as.f:(double)b.as.i;
    return ks_flt(fa/fb);
}
static ks_val_t ks_v_mod(ks_val_t a, ks_val_t b){
    long long ia=(a.tag==KS_T_INT)?a.as.i:0;
    long long ib=(b.tag==KS_T_INT)?b.as.i:0;
    if(ib==0) return ks_none();
    return ks_int(ia % ib);
}
static ks_val_t ks_v_pow(ks_val_t a, ks_val_t b){
    if(a.tag==KS_T_INT && b.tag==KS_T_INT){
        long long base=a.as.i, exp=b.as.i, result=1;
        if(exp<0) return ks_flt(pow((double)base,(double)exp));
        while(exp>0){ if(exp&1) result*=base; base*=base; exp>>=1; }
        return ks_int(result);
    }
    double fa=(a.tag==KS_T_FLT)?a.as.f:(double)a.as.i;
    double fb=(b.tag==KS_T_FLT)?b.as.f:(double)b.as.i;
    return ks_flt(pow(fa,fb));
}
static ks_val_t ks_v_eq(ks_val_t a, ks_val_t b){
    if(a.tag==KS_T_STR && b.tag==KS_T_STR) return ks_bool(strcmp(a.as.s,b.as.s)==0);
    if(a.tag==KS_T_FLT || b.tag==KS_T_FLT){
        double fa=(a.tag==KS_T_FLT)?a.as.f:(double)a.as.i;
        double fb=(b.tag==KS_T_FLT)?b.as.f:(double)b.as.i;
        return ks_bool(fa==fb);
    }
    if(a.tag==KS_T_BOOL || b.tag==KS_T_BOOL) return ks_bool(a.as.b==b.as.b);
    if(a.tag==KS_T_NONE || b.tag==KS_T_NONE) return ks_bool(a.tag==KS_T_NONE && b.tag==KS_T_NONE);
    long long ia=(a.tag==KS_T_INT)?a.as.i:0;
    long long ib=(b.tag==KS_T_INT)?b.as.i:0;
    return ks_bool(ia==ib);
}
static ks_val_t ks_v_lt(ks_val_t a, ks_val_t b){
    if(a.tag==KS_T_STR && b.tag==KS_T_STR) return ks_bool(strcmp(a.as.s,b.as.s)<0);
    if(a.tag==KS_T_FLT || b.tag==KS_T_FLT){
        double fa=(a.tag==KS_T_FLT)?a.as.f:(double)a.as.i;
        double fb=(b.tag==KS_T_FLT)?b.as.f:(double)b.as.i;
        return ks_bool(fa<fb);
    }
    long long ia=(a.tag==KS_T_INT)?a.as.i:0;
    long long ib=(b.tag==KS_T_INT)?b.as.i:0;
    return ks_bool(ia<ib);
}
static int ks_v_cmp(ks_val_t a, ks_val_t b){
    int _an=(a.tag==KS_T_NONE), _bn=(b.tag==KS_T_NONE);
    if(_an || _bn) return _an-_bn;
    if(a.tag==KS_T_STR && b.tag==KS_T_STR) return strcmp(a.as.s,b.as.s);
    if(a.tag==KS_T_FLT || b.tag==KS_T_FLT){
        double fa=(a.tag==KS_T_FLT)?a.as.f:(double)a.as.i;
        double fb=(b.tag==KS_T_FLT)?b.as.f:(double)b.as.i;
        if(fa<fb) return -1; if(fa>fb) return 1; return 0;
    }
    long long ia=(a.tag==KS_T_INT)?a.as.i:0;
    long long ib=(b.tag==KS_T_INT)?b.as.i:0;
    if(ia<ib) return -1; if(ia>ib) return 1; return 0;
}
static inline double ks_v_f(ks_val_t a){
    if(a.tag==KS_T_FLT) return a.as.f;
    if(a.tag==KS_T_INT) return (double)a.as.i;
    return 0.0;
}
static inline long long ks_v_i(ks_val_t a){
    if(a.tag==KS_T_INT) return a.as.i;
    if(a.tag==KS_T_BOOL) return a.as.b?1:0;
    if(a.tag==KS_T_FLT) return (long long)a.as.f;
    return 0;
}
static int ks_v_bool(ks_val_t v){
    switch(v.tag){
        case KS_T_INT: return v.as.i!=0;
        case KS_T_FLT: return v.as.f!=0.0;
        case KS_T_BOOL: return v.as.b!=0;
        case KS_T_STR: return v.as.s!=0 && v.as.s[0]!=0;
        case KS_T_NONE: return 0;
        case KS_T_ARR: return ((ks_array*)v.as.p)->length>0;
        case KS_T_OBJ: return v.as.p!=0;
        case KS_T_DICT: return v.as.p!=0;
    }
    return 0;
}
static char* _ks_fmt_d(double d){
    char* r=_ks_newbuf(); int prec;
    for (prec=15; prec<=17; prec++) {
        snprintf(r,64,"%.*g",prec,d);
        if (strtod(r,NULL)==d) break;
    }
    return r;
}
static char* ks_val_to_str(ks_val_t v){
    switch(v.tag){
        case KS_T_INT: { char* r=_ks_newbuf(); snprintf(r,64,"%lld",v.as.i); return r; }
        case KS_T_FLT: { char* r=_ks_newbuf(); double d=v.as.f; if(d==(long long)d && d < 1e15 && d > -1e15) snprintf(r,64,"%.1f",d); else return _ks_fmt_d(d); return r; }
        case KS_T_BOOL: return v.as.b? (char*)"True" : (char*)"False";
        case KS_T_STR: return v.as.s? v.as.s : (char*)"";
        case KS_T_NONE: return (char*)"None";
        case KS_T_ARR: {
            ks_array* a=(ks_array*)v.as.p; char* r=_ks_newbuf(); int pos=0;
            pos+=sprintf(r+pos,"[");
            for(long long _k=0; _k<a->length; _k++){
                if(_k) pos+=sprintf(r+pos,", ");
                char* _e=ks_val_to_str(a->data[_k]);
                pos+=sprintf(r+pos,"%s",_e);
            }
            pos+=sprintf(r+pos,"]"); return r;
        }
        case KS_T_OBJ: { char* r=_ks_newbuf(); snprintf(r,64,"<object %p>",v.as.p); return r; }
        case KS_T_DICT: return _ks_dict_repr(v.as.p);
    }
    return (char*)"";
}
static void ks_val_print(ks_val_t v){ char* s=ks_val_to_str(v); printf("%s", s); }
static char* _ks_json_str(const char* s){
    char* r=_ks_newbuf(); int i=0, p=0; r[p++]='\"';
    while (s[i] && p < 4088) {
        if (s[i] == '\"') { r[p++]='\\'; r[p++]='\"'; }
        else if (s[i] == '\\' && p < 4087) { r[p++]='\\'; r[p++]='\\'; }
        else { r[p++]=s[i]; }
        i++;
    }
    r[p++]='\"'; r[p]=0; return r;
}
static char* _ks_json_stringify(ks_val_t v){
    if (v.tag==KS_T_STR) return _ks_json_str(v.as.s);
    if (v.tag==KS_T_BOOL) return (char*)(v.as.b ? "true" : "false");
    if (v.tag==KS_T_INT) { char* r=_ks_newbuf(); snprintf(r,64,"%lld",v.as.i); return r; }
    if (v.tag==KS_T_FLT) { char* r=_ks_newbuf(); double d=v.as.f; if(d==(long long)d && d < 1e15 && d > -1e15) snprintf(r,64,"%.1f",d); else snprintf(r,64,"%.14g",d); return r; }
    if (v.tag==KS_T_NONE) return (char*)"null";
    if (v.tag==KS_T_ARR) {
        ks_array* a=(ks_array*)v.as.p; char* r=_ks_newbuf(); int pos=0;
        pos += sprintf(r+pos,"[");
        for (long long k=0; k<a->length; k++) {
            if (k) pos += sprintf(r+pos,", ");
            char* e=_ks_json_stringify(a->data[k]);
            pos += sprintf(r+pos,"%s", e ? e : (char*)"null");
        }
        pos += sprintf(r+pos,"]"); r[pos]=0; return r;
    }
    return (char*)"null";
}
static long long _ks_array_contains(ks_array a, ks_val_t needle){
    for (long long i=0; i<a.length; i++) if (ks_v_cmp(a.data[i], needle)==0) return 1;
    return 0;
}
/* ===== END ks_val_t helpers ===== */
#include "ks_legacy_simd.h"
#include "ks_os.h"
static char* _ks_colorize(const char* code, const char* s){
    char* r=_ks_newbuf(); snprintf(r, 4096, "\x1b[%sm%s\x1b[0m", code, s); return r;
}
/* String methods */
static char* _ks_str_upper(const char* s) {
    char *r = _ks_newbuf(); int i = 0;
    while (s[i] && i < 4095) { r[i] = toupper(s[i]); i++; }
    r[i] = 0; return r;
}
static char* _ks_str_lower(const char* s) {
    char *r = _ks_newbuf(); int i = 0;
    while (s[i] && i < 4095) { r[i] = tolower(s[i]); i++; }
    r[i] = 0; return r;
}
static char* _ks_str_strip(const char* s) {
    while (*s && isspace(*s)) s++;
    const char *e = s + strlen(s) - 1;
    while (e > s && isspace(*e)) e--;
    char *r = _ks_newbuf(); int len = e - s + 1;
    if (len > 0) { memcpy(r, s, len); r[len] = 0; } else r[0] = 0;
    return r;
}
static char* _ks_str_replace(const char* s, const char* old, const char* new_s) {
    char *r = _ks_newbuf(); const char *p = s; int rlen = 0;
    int olen = strlen(old), nlen = strlen(new_s);
    while (*p && rlen < 4090) {
        if (strncmp(p, old, olen) == 0) {
            memcpy(r+rlen, new_s, nlen); rlen += nlen; p += olen;
        } else { r[rlen++] = *p++; }
    }
    r[rlen] = 0; return r;
}
static char* _ks_str_find(const char* s, const char* needle) {
    const char* p = strstr(s, needle);
    if (!p) return "-1";
    char *r = _ks_newbuf(); snprintf(r, 32, "%lld", (long long)(p - s)); return r;
}
static long long _ks_find_idx(const char* s, const char* needle) {
    const char* p = strstr(s, needle);
    return p ? (long long)(p - s) : -1;
}
static char* _ks_str_trim(const char* s) {
    while (*s != 0 && (*s == ' ' || *s == '\t' || *s == '\r' || *s == '\n')) s++;
    long long n = (long long)strlen(s);
    while (n > 0 && (s[n-1] == ' ' || s[n-1] == '\t' || s[n-1] == '\r' || s[n-1] == '\n')) n--;
    char *r = _ks_newbuf(); memcpy(r, s, n); r[n] = 0; return r;
}
static char* _ks_str_substring(const char* s, long long start, long long end) {
    long long len = strlen(s);
    if (start < 0) start = 0; if (end > len) end = len;
    char *r = _ks_newbuf(); long long n = end - start;
    if (n > 0) { memcpy(r, s+start, n); r[n] = 0; } else r[0] = 0;
    return r;
}
static int _ks_str_endswith(const char* s, const char* suffix) {
    long long sl = strlen(s), el = strlen(suffix);
    return sl >= el && strcmp(s + sl - el, suffix) == 0;
}
static ks_array _ks_str_split(const char* s, const char* sep) {
    long long cap = 16, count = 0;
    ks_val_t* parts = (ks_val_t*)malloc(cap * sizeof(ks_val_t));
    int seplen = strlen(sep); const char* p = s;
    while (*p) {
        const char* found = strstr(p, sep);
        if (!found) found = p + strlen(p);
        long long n = found - p;
        char* part = (char*)malloc(n + 1); memcpy(part, p, n); part[n] = 0;
        if (count >= cap) { cap *= 2; parts = (ks_val_t*)realloc(parts, cap * sizeof(ks_val_t)); }
        parts[count].tag = KS_T_STR; parts[count].as.s = part; count++;
        p = *found ? found + seplen : found;
    }
    ks_array arr; arr.data = parts; arr.length = count; return arr;
}
static void _ks_array_append(ks_array* arr, ks_val_t val) {
    long long need = arr->length + 1;
    if (need > arr->cap) {
        long long nc = arr->cap ? arr->cap * 2 : (arr->length > 0 ? arr->length * 2 : 16);
        if (nc < need) nc = need;
        ks_val_t* new_data; if (arr->cap == 0 && arr->data) {
            new_data = (ks_val_t*)malloc(nc * sizeof(ks_val_t));
            if (new_data) memcpy(new_data, arr->data, arr->length * sizeof(ks_val_t));
        } else { new_data = (ks_val_t*)realloc(arr->data, nc * sizeof(ks_val_t)); }
        if (new_data) { arr->data = new_data; arr->cap = nc; }
    }
    arr->data[arr->length] = val;
    arr->length++;
}
static ks_val_t _ks_array_pop(ks_array* arr) {
    if (arr->length == 0) return ks_none();
    ks_val_t val = arr->data[arr->length - 1];
    arr->length--; return val;
}
static void _ks_array_unshift(ks_array* arr, ks_val_t val) {
    long long need = arr->length + 1;
    if (need > arr->cap) {
        long long nc = arr->cap ? arr->cap * 2 : (arr->length > 0 ? arr->length * 2 : 16);
        if (nc < need) nc = need;
        ks_val_t* new_data; if (arr->cap == 0 && arr->data) {
            new_data = (ks_val_t*)malloc(nc * sizeof(ks_val_t));
            if (new_data) memcpy(new_data, arr->data, arr->length * sizeof(ks_val_t));
        } else { new_data = (ks_val_t*)realloc(arr->data, nc * sizeof(ks_val_t)); }
        if (new_data) { arr->data = new_data; arr->cap = nc; }
    }
    for (long long _u = arr->length; _u > 0; _u--) arr->data[_u] = arr->data[_u-1];
    arr->data[0] = val; arr->length++;
}
static ks_val_t _ks_array_shift(ks_array* arr) {
    if (arr->length == 0) return ks_none();
    ks_val_t val = arr->data[0];
    for (long long _s = 0; _s < arr->length - 1; _s++) arr->data[_s] = arr->data[_s+1];
    arr->length--; return val;
}
static ks_val_t ks_array_get(ks_array arr, ks_val_t idx);
static void _ks_array_append(ks_array* arr, ks_val_t val);
static ks_array _ks_slice(ks_array a, ks_val_t start, ks_val_t end, ks_val_t step) {
    ks_array r = {NULL, 0};
    long long n = a.length;
    long long s = start.as.i, e = end.as.i, st = step.as.i;
    if (st == 0) st = 1;
    if (s < 0) s += n; if (s < 0) s = 0;
    if (e < 0) e += n; if (e > n) e = n;
    if (st > 0) {
        for (long long i = s; i < e; i += st)
            _ks_array_append(&r, ks_array_get(a, ks_int(i)));
    } else {
        if (e < 0) e = -1;
        for (long long i = s; i > e; i += st)
            _ks_array_append(&r, ks_array_get(a, ks_int(i)));
    }
    return r;
}
static char* _ks_str_join(const char* sep, ks_array arr) {
    char *r = _ks_newbuf(); int pos = 0;
    for (long long i = 0; i < arr.length && pos < 4090; i++) {
        if (i > 0) { int sl = strlen(sep); memcpy(r+pos, sep, sl); pos += sl; }
        const char* s = (arr.data[i].tag==KS_T_STR)? arr.data[i].as.s : "";
        int sl = strlen(s); memcpy(r+pos, s, sl); pos += sl;
    }
    r[pos] = 0; return r;
}
/* Missing standard library functions */
static long long _ks_len(const char* s) {
    return (long long)strlen(s);
}
static long long _ks_ord(const char* s) {
    return s[0] ? (long long)(unsigned char)s[0] : 0;
}
static char* _ks_chr(long long code) {
    char *r = _ks_newbuf();
    if (code >= 0 && code <= 255) { r[0] = (char)code; r[1] = 0; }
    else { r[0] = 0; }
    return r;
}
static long long _ks_contains(const char* haystack, const char* needle) {
    return strstr(haystack, needle) != NULL ? 1 : 0;
}
static char* _ks_str_at(const char* s, long long index) {
    long long len = strlen(s);
    if (index < 0 || index >= len) return "";
    char *r = _ks_newbuf();
    r[0] = s[index]; r[1] = 0;
    return r;
}
static char* _ks_type(long long v) {
    return "unknown";
}
/* Dict hash table - simple implementation */
typedef struct _ks_dict_node {
    char* key;
    union { long long i; char* s; };
    int is_str;
    struct _ks_dict_node* next;
} _ks_dict_node;
typedef struct { _ks_dict_node* buckets[32]; long long nkeys; const char* keys[64]; } _ks_dict;
static unsigned int _ks_hash(const char* s) {
    unsigned int h = 5381; int c;
    while ((c = *s++)) h = ((h << 5) + h) + c;
    return h % 32;
}
static _ks_dict* _ks_dict_new(void) {
    _ks_dict* d = malloc(sizeof(_ks_dict));
    memset(d, 0, sizeof(_ks_dict));
    return d;
}
static void _ks_dict_set(_ks_dict* d, const char* key, long long val, int is_str) {
    unsigned int h = _ks_hash(key);
    _ks_dict_node* n = d->buckets[h];
    while (n) { if (strcmp(n->key, key) == 0) { n->i = val; n->is_str = is_str; return; } n = n->next; }
    n = malloc(sizeof(_ks_dict_node));
    n->key = strdup(key);
    n->i = val; n->is_str = is_str;
    n->next = d->buckets[h];
    d->buckets[h] = n;
    if (d->nkeys < 64) d->keys[d->nkeys++] = n->key;
}
static long long _ks_dict_get(_ks_dict* d, const char* key, int* found) {
    unsigned int h = _ks_hash(key);
    _ks_dict_node* n = d->buckets[h];
    while (n) { if (strcmp(n->key, key) == 0) { *found = 1; return n->i; } n = n->next; }
    *found = 0; return 0;
}
/* Simple dict get that returns 0 if not found */
static long long _ks_dict_get_simple(_ks_dict* d, const char* key) {
    int found;
    return _ks_dict_get(d, key, &found);
}
static char* _ks_dict_to_str(_ks_dict* d, const char* key) {
    unsigned int h = _ks_hash(key);
    _ks_dict_node* n = d->buckets[h];
    while (n) { if (!strcmp(n->key, key)) break; n = n->next; }
    if (n && n->is_str) return (char*)n->i;
    char* b = _ks_newbuf(); if (n) snprintf(b, 4096, "%lld", n->i); else b[0] = 0; return b;
}
static int _ks_dict_contains(_ks_dict* d, const char* key) {
    unsigned int h = _ks_hash(key);
    _ks_dict_node* n = d->buckets[h];
    while (n) { if (strcmp(n->key, key) == 0) { return 1; } n = n->next; }
    return 0;
}
/* Dict get that returns string value */
static char* _ks_dict_get_str(_ks_dict* d, const char* key) {
    unsigned int h = _ks_hash(key);
    _ks_dict_node* n = d->buckets[h];
    while (n) {
        if (strcmp(n->key, key) == 0) {
            if (n->is_str) return (char*)n->i;
            return "";
        }
        n = n->next;
    }
    return "";
}
/* Dict attribute read: returns the stored string, or NULL if the
   key is absent / not a string (maps to '== none'). */
static char* _ks_dict_attr(_ks_dict* d, const char* key) {
    if (!d) return NULL;
    unsigned int h = _ks_hash(key);
    _ks_dict_node* n = d->buckets[h];
    while (n) {
        if (strcmp(n->key, key) == 0) {
            if (n->is_str) return (char*)n->i;
            return NULL;
        }
        n = n->next;
    }
    return NULL;
}
static _ks_dict* system_argparse_parse_args(long long parser, long long arglist){ (void)parser; (void)arglist;
    /* Parity with the interpreter: the source passes parse_args(parser, [])
       unconditionally, so the real argv is never read. All flags are absent.
       Callers see args.flag == none and fall back to defaults. */
    return _ks_dict_new();
}
static char* _ks_json_dict(_ks_dict* d) {
    char* r = _ks_newbuf(); int pos = 0;
    pos += sprintf(r+pos, "{");
    for (long long k = 0; k < d->nkeys; k++) {
        const char* key = d->keys[k];
        unsigned int h = _ks_hash(key);
        _ks_dict_node* n = d->buckets[h];
        while (n && strcmp(n->key, key) != 0) n = n->next;
        if (k) pos += sprintf(r+pos, ", ");
        pos += sprintf(r+pos, "%s", _ks_json_str(key));
        pos += sprintf(r+pos, ": ");
        if (n && n->is_str) {
            pos += sprintf(r+pos, "%s", _ks_json_str((char*)n->i));
        } else if (n && n->i > 0 && n->i < 2147483647) {
            char buf[40]; snprintf(buf, sizeof(buf), "%lld", n->i); pos += sprintf(r+pos, "%s", buf);
        } else {
            long long got = _ks_dict_get(d, key, &(int){0});
            pos += sprintf(r+pos, "%lld", got);
        }
    }
    pos += sprintf(r+pos, "}"); r[pos] = 0; return r;
}
/* Helper to create and populate dict (1-6 args, handles varargs) */
static _ks_dict* _ks_dict_create(const char* k1, long long v1, int s1, const char* k2, long long v2, int s2, const char* k3, long long v3, int s3, const char* k4, long long v4, int s4, const char* k5, long long v5, int s5, const char* k6, long long v6, int s6) {
    _ks_dict* d = _ks_dict_new();
    if (k1) _ks_dict_set(d, k1, v1, s1);
    if (k2) _ks_dict_set(d, k2, v2, s2);
    if (k3) _ks_dict_set(d, k3, v3, s3);
    if (k4) _ks_dict_set(d, k4, v4, s4);
    if (k5) _ks_dict_set(d, k5, v5, s5);
    if (k6) _ks_dict_set(d, k6, v6, s6);
    return d;
}
/* Dict print keys */
static char* _ks_dict_print_keys(_ks_dict* d) {
    static char buf[4096]; int pos = 0;
    pos += snprintf(buf+pos, sizeof(buf)-pos, "[");
    int first = 1;
    for (int i = 0; i < (int)(sizeof(d->buckets)/sizeof(d->buckets[0])); i++) {
        _ks_dict_node* n = d->buckets[i];
        while (n) { if (!first) pos += snprintf(buf+pos, sizeof(buf)-pos, ", "); pos += snprintf(buf+pos, sizeof(buf)-pos, "\"%s\"", n->key); first = 0; n = n->next; }
    }
    snprintf(buf+pos, sizeof(buf)-pos, "]");
    return buf;
}
/* Dict print values */
static char* _ks_dict_print_values(_ks_dict* d) {
    static char buf[4096]; int pos = 0;
    pos += snprintf(buf+pos, sizeof(buf)-pos, "[");
    int first = 1;
    for (int i = 0; i < (int)(sizeof(d->buckets)/sizeof(d->buckets[0])); i++) {
        _ks_dict_node* n = d->buckets[i];
        while (n) { if (!first) pos += snprintf(buf+pos, sizeof(buf)-pos, ", "); if (n->is_str) pos += snprintf(buf+pos, sizeof(buf)-pos, "\"%s\"", (char*)n->i); else pos += snprintf(buf+pos, sizeof(buf)-pos, "%lld", n->i); first = 0; n = n->next; }
    }
    snprintf(buf+pos, sizeof(buf)-pos, "]");
    return buf;
}
/* [KS-REF-011] Monotonic ms timer */
static double ks_time_monotonic_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec*1000.0 + (double)ts.tv_nsec/1000000.0;
}
/* time.time() - returns seconds (like Python) */
static double ks_time_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec/1000000000.0;
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
static inline void* ks_malloc(ks_val_t size) { return malloc((size.tag==KS_T_INT)?(size_t)size.as.i:(size_t)0); }
static inline void ks_free_ptr(void* ptr) { free(ptr); }
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
/* Low-level runtime functions */
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
    }
}
static inline void* ks_ptr_cast(void* ptr) { return ptr; }
static inline uint64_t ks_ptr_deref(void* ptr) { return *(uint64_t*)ptr; }
static inline long ks_system_syscall(long n, long a1, long a2, long a3, long a4, long a5, long a6) {
    return syscall(n, a1, a2, a3, a4, a5, a6);
}
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
static inline uint64_t ks_volatile_read(volatile void* addr, int size) {
    return *(volatile uint64_t*)addr;
}
static inline void ks_volatile_write(volatile void* addr, uint64_t value, int size) {
    *(volatile uint64_t*)addr = value;
}
static inline void ks_memory_barrier() { __sync_synchronize(); }
static inline void ks_compiler_barrier() { __asm__ __volatile__("" ::: "memory"); }
/* ks_cache_flush provided by ks_runtime.h */
#if 0  /* disabled - use ks_runtime.h version */
static inline void ks_cache_flush(void* addr, size_t size) {
    __builtin___clear_cache((char*)addr, (char*)addr + size);
}
#endif
static inline void ks_cache_invalidate(void* addr, size_t size) {
    __builtin___clear_cache((char*)addr, (char*)addr + size);
}
static inline uint64_t ks_mmio_read(void* addr, int size) {
    return ks_volatile_read(addr, size);
}
static inline void ks_mmio_write(void* addr, uint64_t value, int size) {
    ks_volatile_write(addr, value, size);
}
#if defined(__x86_64__) || defined(__i386__)
static inline uint8_t ks_read_port(uint16_t port) {
    uint8_t value;
    __asm__ volatile("inb %1, %0" : "=a"(value) : "Nd"(port));
    return value;
}
static inline void ks_write_port(uint16_t port, uint8_t value) {
    __asm__ volatile("outb %0, %1" : : "a"(value), "Nd"(port));
}
static inline uint64_t ks_rdtsc() {
    uint32_t lo, hi;
    __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}
static inline void ks_cpuid(uint32_t leaf, uint32_t* eax, uint32_t* ebx, uint32_t* ecx, uint32_t* edx) {
    __asm__ volatile("cpuid" : "=a"(*eax), "=b"(*ebx), "=c"(*ecx), "=d"(*edx) : "a"(leaf));
}
#else
static inline uint8_t ks_read_port(uint16_t port) { return 0; }
static inline void ks_write_port(uint16_t port, uint8_t value) {}
static inline uint64_t ks_rdtsc() { return 0; }
static inline void ks_cpuid(uint32_t leaf, uint32_t* eax, uint32_t* ebx, uint32_t* ecx, uint32_t* edx) {}
#endif
/* Array return type wrapper */
static inline ks_array ks_make_array(ks_val_t* data, long long len) {
    ks_array arr = {data, len};
    return arr;
}
static inline ks_val_t ks_array_get(ks_array arr, ks_val_t idx) {
    long long _i = (idx.tag==KS_T_INT)? idx.as.i : (long long)idx.as.f;
    if (_i < 0) _i += arr.length;
    if (_i < 0 || _i >= arr.length) return ks_none();
    return arr.data[_i];
}
static inline void ks_array_set(ks_array* restrict arr, ks_val_t idx, ks_val_t val) {
    long long _i = (idx.tag==KS_T_INT)? idx.as.i : (long long)idx.as.f;
    if (_i < 0) _i += arr->length;
    if (_i < 0 || _i >= arr->length) return;
    arr->data[_i] = val;
}
static inline long long ks_array_len(ks_array arr) {
    return arr.length;
}
static inline ks_val_t ks_sum(ks_array arr) {
    ks_val_t _t = ks_int(0);
    for (long long _i = 0; _i < arr.length; _i++) _t = ks_v_add(_t, arr.data[_i]);
    return _t;
}
#endif /* KS_RUNTIME_HAVE_ALL_FUNCS */
/* ===== HTTP/JSON/Socket stub implementations ===== */
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
typedef struct { long long status; char* body; } _ks_http_response_t;
static void _ks_http_free(_ks_http_response_t* r) {
    if (r->body) free(r->body);
    r->body = NULL;
    r->status = 0;
}
static _ks_http_response_t _ks_http_request(const char* method, const char* url, const char* headers, const char* body) {
    _ks_http_response_t resp = {0, NULL};
    if (!url || !*url) return resp;
    char url_copy[4096];
    strncpy(url_copy, url, sizeof(url_copy) - 1);
    url_copy[sizeof(url_copy) - 1] = 0;
    char* host_start = url_copy;
    char* path_start = NULL;
    int port = 80;
    if (strncmp(host_start, "http://", 7) == 0) host_start += 7;
    path_start = strchr(host_start, '/');
    if (path_start) {
        *path_start = 0;
        path_start++;
    } else {
        path_start = "";
    }
    char* colon = strchr(host_start, ':');
    if (colon) {
        *colon = 0;
        port = atoi(colon + 1);
        if (port <= 0) port = 80;
    }
    struct hostent* he = gethostbyname(host_start);
    if (!he) { resp.status = -1; return resp; }
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) { resp.status = -2; return resp; }
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    memcpy(&addr.sin_addr, he->h_addr_list[0], he->h_length);
    if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close(sock); resp.status = -3; return resp;
    }
    char req[8192];
    int req_len = snprintf(req, sizeof(req),
        "%s /%s HTTP/1.0\r\n"
        "Host: %s\r\n"
        "%s"
        "%s"
        "\r\n",
        method, path_start, host_start,
        (headers && *headers) ? headers : "",
        (body && *body) ? body : "");
    send(sock, req, req_len, 0);
    char buf[4096];
    int total = 0, cap = 4096;
    char* response = malloc(cap);
    if (!response) { close(sock); resp.status = -4; return resp; }
    response[0] = 0;
    int n;
    while ((n = recv(sock, buf, sizeof(buf) - 1, 0)) > 0) {
        buf[n] = 0;
        if (total + n >= cap) {
            cap *= 2;
            char* tmp = realloc(response, cap);
            if (!tmp) break;
            response = tmp;
        }
        memcpy(response + total, buf, n + 1);
        total += n;
    }
    close(sock);
    char* status_line = response;
    char* space = strchr(status_line, ' ');
    if (space) {
        resp.status = atol(space + 1);
        char* body_start = strstr(response, "\r\n\r\n");
        if (body_start) {
            body_start += 4;
            char* body_copy = strdup(body_start);
            free(response);
            resp.body = body_copy;
        } else {
            resp.body = response;
        }
    } else {
        resp.status = 0;
        resp.body = response;
    }
    return resp;
}
static _ks_http_response_t _ks_http_get(const char* url) { return _ks_http_request("GET", url, NULL, NULL); }
static _ks_http_response_t _ks_http_post(const char* url, const char* data) { return _ks_http_request("POST", url, "Content-Type: application/x-www-form-urlencoded\r\n", data); }
static ks_val_t _ks_json_loads(const char* s){
    _ks_dict* d = _ks_dict_new();
    const char* p = s;
    while (*p && *p != '{') p++;
    if (*p == '{') p++;
    while (*p && *p != '}') {
        while (*p && isspace(*p)) p++;
        if (*p == '}') break;
        char key[256]; int ki = 0;
        if (*p == '"') { p++; while (*p && *p != '"' && ki < 255) key[ki++] = *p++; if (*p == '"') p++; }
        key[ki] = 0;
        while (*p && *p != ':') p++;
        if (*p == ':') p++;
        while (*p && isspace(*p)) p++;
        long long val = 0; int is_str = 0;
        if (*p == '"') {
            char vbuf[2048]; int vi = 0; p++;
            while (*p && *p != '"' && vi < 2047) vbuf[vi++] = *p++;
            if (*p == '"') p++;
            vbuf[vi] = 0;
            val = (long long)(uintptr_t)strdup(vbuf); is_str = 1;
        } else if (strncmp(p, "true", 4) == 0) { val = 1; p += 4; }
        else if (strncmp(p, "false", 5) == 0) { val = 0; p += 5; }
        else if (strncmp(p, "null", 4) == 0) { val = 0; p += 4; }
        else { val = (long long)strtoll(p, (char**)&p, 10); }
        _ks_dict_set(d, key, val, is_str);
        while (*p && *p != ',' && *p != '}') p++;
        if (*p == ',') p++;
    }
    return ks_dict(d);
}
static char* _ks_dict_repr(void* p){
    _ks_dict* d = (_ks_dict*)p;
    char* r = _ks_newbuf(); int pos = 0;
    pos += sprintf(r+pos, "{");
    for (long long k = 0; k < d->nkeys; k++) {
        char* key = (char*)d->keys[k];
        if (k) pos += sprintf(r+pos, ", ");
        unsigned int h = _ks_hash(key);
        _ks_dict_node* n = d->buckets[h];
        while (n && strcmp(n->key, key) != 0) n = n->next;
        char* kv = key; char* ev;
        pos += sprintf(r+pos, "'%s': ", kv);
        if (n && n->is_str) {
            ev = (char*)n->i; pos += sprintf(r+pos, "'%s'", ev);
        } else if (n) {
            char buf[40]; snprintf(buf, sizeof(buf), "%lld", n->i); pos += sprintf(r+pos, "%s", buf);
        } else {
            pos += sprintf(r+pos, "%lld", _ks_dict_get_simple(d, key));
        }
    }
    pos += sprintf(r+pos, "}"); r[pos] = 0; return r;
}
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
static long long _ks_syscall_open(const char* path, long long mode){
    int fd = open(path, O_CREAT | O_RDWR, (mode_t)(mode ? mode : 0644));
    return (long long)fd;
}
static long long _ks_syscall_write(long long fd, const char* s){ return (long long)write((int)fd, s, strlen(s)); }
static long long _ks_syscall_close(long long fd){ return (long long)close((int)fd); }
static long long _ks_syscall_fsync(long long fd){ return (long long)fsync((int)fd); }
static long long _ks_syscall_getpid(void){ return (long long)getpid(); }
static _ks_dict* _ks_syscall_stat(const char* path){
    struct stat st; _ks_dict* d = _ks_dict_new();
    if (stat(path, &st) == 0) {
        _ks_dict_set(d, "size", (long long)st.st_size, 0);
        _ks_dict_set(d, "mode", (long long)st.st_mode, 0);
        _ks_dict_set(d, "mtime", (long long)st.st_mtime, 0);
    }
    return d;
}
#include <sys/utsname.h>
#include <sys/statvfs.h>
static _ks_dict* system_platform_uname(void) {
    struct utsname u; _ks_dict* d = _ks_dict_new();
    if (uname(&u) == 0) {
        _ks_dict_set(d, "system", (long long)(uintptr_t)strdup(u.sysname), 1);
        _ks_dict_set(d, "node", (long long)(uintptr_t)strdup(u.nodename), 1);
        _ks_dict_set(d, "release", (long long)(uintptr_t)strdup(u.release), 1);
        _ks_dict_set(d, "version", (long long)(uintptr_t)strdup(u.version), 1);
        _ks_dict_set(d, "machine", (long long)(uintptr_t)strdup(u.machine), 1);
    }
    return d;
}
static long long system_cpu_count(void) { return (long long)sysconf(_SC_NPROCESSORS_ONLN); }
long long system_os_getpid(void);
long long system_os_getppid(void);
long long system_os_getuid(void);
long long system_os_getgid(void);
char* system_file_getcwd(void){ char b[4096]; if (getcwd(b, sizeof(b))) return strdup(b); return strdup(""); }
static _ks_dict* system_virtual_memory(void) {
    _ks_dict* d = _ks_dict_new();
    long long total = 0, avail = 0;
    FILE* fp = fopen("/proc/meminfo", "r");
    if (fp) { char k[64]; long long v; char u[16];
        while (fscanf(fp, "%63s %lld %15s", k, &v, u) == 3) {
            if (!strcmp(k, "MemTotal:")) total = v * 1024;
            else if (!strcmp(k, "MemAvailable:")) avail = v * 1024;
        } fclose(fp); }
    _ks_dict_set(d, "total", total, 0);
    _ks_dict_set(d, "available", avail, 0);
    _ks_dict_set(d, "percent", total > 0 ? (total - avail) * 100 / total : 0, 0);
    return d;
}
static long long _ks_disk_total(const char* p){ struct statvfs sv; if (statvfs(p, &sv) == 0) return (long long)sv.f_blocks * (long long)sv.f_frsize; return 0; }
static long long _ks_disk_free(const char* p){ struct statvfs sv; if (statvfs(p, &sv) == 0) return (long long)sv.f_bavail * (long long)sv.f_frsize; return 0; }
static _ks_dict* system_disk_usage(char* p){
    _ks_dict* d = _ks_dict_new();
    long long t = _ks_disk_total(p), f = _ks_disk_free(p), used = t - f;
    _ks_dict_set(d, "total", t, 0); _ks_dict_set(d, "free", f, 0);
    _ks_dict_set(d, "used", used, 0);
    _ks_dict_set(d, "percent", t > 0 ? used * 100 / t : 0, 0);
    return d;
}
static double _ks_uptime_double(void){
    double up = 0.0; FILE* fp = fopen("/proc/uptime", "r");
    if (fp) { if (fscanf(fp, "%lf", &up) != 1) up = 0.0; fclose(fp); }
    return up;
}
static long long system_uptime(void){ return (long long)_ks_uptime_double(); }
static ks_array system_load_average(void){
    ks_val_t* v = (ks_val_t*)calloc(3, sizeof(ks_val_t));
    double a[3] = {0,0,0}; FILE* fp = fopen("/proc/loadavg", "r");
    if (fp) { if (fscanf(fp, "%lf %lf %lf", &a[0], &a[1], &a[2]) != 3) { a[0]=a[1]=a[2]=0; } fclose(fp); }
    v[0] = ks_flt(a[0]); v[1] = ks_flt(a[1]); v[2] = ks_flt(a[2]);
    return ks_make_array(v, 3);
}
static char* system_time_strftime(char* fmt){
    time_t t = time(NULL); struct tm tm; localtime_r(&t, &tm);
    char b[128]; if (strftime(b, sizeof(b), fmt, &tm) == 0) b[0] = 0; return strdup(b);
}
static char* system_time_format(ks_val_t ts, char* fmt){
    time_t t = (time_t)ts.as.f; struct tm tm; localtime_r(&t, &tm);
    char b[128]; if (strftime(b, sizeof(b), fmt, &tm) == 0) b[0] = 0; return strdup(b);
}
static char* _ks_substr(const char* s, ks_val_t start, ks_val_t end){
    return _ks_str_substring(s, start.as.i, end.as.i);
}
static long long ks_v_to_i(ks_val_t v){ return v.as.i; }
static ks_val_t _ks_starts_with(const char* s, const char* p){
    return ks_bool(p && s && strlen(p) <= strlen(s) && strncmp(s, p, strlen(p)) == 0);
}
static char* system_crypto_generate_token(long long n){
    const char* alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    if (n <= 0) n = 32; char* r = (char*)malloc((size_t)n + 1);
    for (long long i = 0; i < n; i++) r[i] = alphabet[rand() % 62]; r[n] = 0; return r;
}
static char* system_crypto_hmac(char* key, char* msg){ (void)key; (void)msg; return strdup(""); }
static char* system_crypto_encrypt_aes(char* data, char* key){ (void)key; return strdup(data); }
static char* system_crypto_decrypt_aes(char* data, char* key){ (void)key; return strdup(data); }
static char* system_crypto_sha256(char* data){
    (void)data; char* r = (char*)malloc(65);
    snprintf(r, 65, "%016lx%016lx", (unsigned long)rand(), (unsigned long)rand()); return r;
}
static char* system_crypto_sha512(char* data){
    (void)data; char* r = (char*)malloc(129);
    snprintf(r, 129, "%016lx%016lx%016lx%016lx", (unsigned long)rand(), (unsigned long)rand(), (unsigned long)rand(), (unsigned long)rand()); return r;
}
static char* system_crypto_md5(char* data){
    (void)data; char* r = (char*)malloc(33);
    snprintf(r, 33, "%016lx%016lx", (unsigned long)rand(), (unsigned long)rand()); return r;
}
static char* system_crypto_sha1(char* data){
    (void)data; char* r = (char*)malloc(41);
    snprintf(r, 41, "%016lx%08lx%08lx", (unsigned long)rand(), (unsigned long)rand(), (unsigned long)rand()); return r;
}
static void system_os_exit(ks_val_t code){ exit((int)ks_v_i(code)); }
static char* system_crypto_pbkdf2(char* password, char* salt, long long iter){
    (void)salt; (void)iter; (void)password; char* r = (char*)malloc(33);
    snprintf(r, 33, "%016lx", (unsigned long)rand()); return r;
}
static long long system_open(char* path, long long flags, ...){
    va_list ap; va_start(ap, flags); long long mode = va_arg(ap, long long); va_end(ap);
#if defined(_WIN32)||defined(_WIN64)
    int fd = _open(path, (int)flags, (int)mode);
#else
    int fd = open(path, (int)flags, (int)mode);
#endif
    return fd >= 0 ? fd : -1; }
static long long system_close(long long fd){ (void)fd; return 0; }
static char* system_read(long long fd, long long n){
    if (fd < 0) return strdup("");
    if (n < 0) n = 0; if (n > 65536) n = 65536;
    char* buf = (char*)malloc((size_t)n + 1); ssize_t r = read((int)fd, buf, (size_t)n);
    if (r < 0) r = 0; buf[r] = 0; return buf;
}
static long long system_write(long long fd, char* data, long long n, ...){
    if (fd < 0 || !data) return -1; return (long long)write((int)fd, data, (size_t)(n > 0 ? n : strlen(data)));
}
static _ks_dict* system_network_interfaces(void){
    _ks_dict* d = _ks_dict_new();
    char b[256]; gethostname(b, sizeof(b));
    _ks_dict_set(d, "name", (long long)(uintptr_t)strdup(b), 1);
    _ks_dict_set(d, "ip", (long long)(uintptr_t)strdup(b[0] ? b : "127.0.0.1"), 1);
    return d;
}
#define _ks_outb(port, val) __asm__ __volatile__("outb %0, %1" : : "a"((uint8_t)(val)), "Nd"((uint16_t)(port)))
static void _ks_write_port(long long port, long long value){ _ks_outb((uint16_t)(port), (uint8_t)(value)); }
static long long _ks_get_cpu_count(void){ return system_cpu_count(); }
static void _ks_wrap_socket(long long fd){ (void)fd; }
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <fcntl.h>
typedef struct { int fd; } _ks_socket_t;
static _ks_socket_t* _ks_sock_unwrap(ks_val_t v) {
    if (v.tag == KS_T_OBJ && v.as.p) return (_ks_socket_t*)v.as.p;
    return NULL;
}
static long long _ks_addr_host_port(ks_array addr, char* out, int* port) {
    if (addr.data && addr.length >= 2) {
        if (addr.data[0].tag == KS_T_STR) snprintf(out, 256, "%s", addr.data[0].as.s);
        else if (addr.data[0].tag == KS_T_INT) snprintf(out, 256, "%lld", addr.data[0].as.i);
        *port = (int)addr.data[1].as.i; return 1;
    }
    return 0;
}
static ks_val_t ks_val_array_get(ks_val_t v, ks_val_t idx) {
    if (v.tag == KS_T_ARR && v.as.p) {
        ks_array* a = (ks_array*)v.as.p;
        long long i = (idx.tag == KS_T_FLT) ? (long long)idx.as.f : idx.as.i;
        if (i < 0) i += a->length;
        if (i >= 0 && i < (long long)a->length) return a->data[i];
    }
    return ks_none();
}
static struct sockaddr_in _ks_sock_resolve(const char* host, int port) {
    struct sockaddr_in a; memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET; a.sin_port = htons(port);
    if (inet_pton(AF_INET, host, &a.sin_addr) <= 0) {
        struct hostent* he = gethostbyname(host);
        if (he) memcpy(&a.sin_addr, he->h_addr_list[0], he->h_length);
    }
    return a;
}
static double _ks_as_f(ks_val_t v) { return (v.tag == KS_T_FLT) ? v.as.f : (double)v.as.i; }
static long long _ks_as_i(ks_val_t v) { return (v.tag == KS_T_FLT) ? (long long)v.as.f : v.as.i; }
static char* ks_v_str(ks_val_t v) { return (v.tag == KS_T_STR) ? v.as.s : (char*)""; }
static ks_val_t system_socket_create(ks_val_t domain, ks_val_t type, ks_val_t proto) {
    _ks_socket_t* s = (_ks_socket_t*)malloc(sizeof(_ks_socket_t));
    s->fd = socket((int)_ks_as_i(domain), (int)_ks_as_i(type), (int)_ks_as_i(proto));
    if (s->fd < 0) { free(s); return ks_none(); }
    return ks_obj(s);
}
static ks_val_t system_socket_setsockopt(ks_val_t sock, ks_val_t level, ks_val_t opt, ks_val_t val) {
    _ks_socket_t* s = _ks_sock_unwrap(sock); if (!s) return ks_none();
    int v = (int)_ks_as_i(val); setsockopt(s->fd, (int)_ks_as_i(level), (int)_ks_as_i(opt), &v, sizeof(v)); return ks_none();
}
static ks_val_t system_socket_bind(ks_val_t sock, ks_val_t host, ks_val_t port) {
    _ks_socket_t* s = _ks_sock_unwrap(sock); if (!s) return ks_none();
    struct sockaddr_in a = _ks_sock_resolve(ks_v_str(host), (int)_ks_as_i(port));
    bind(s->fd, (struct sockaddr*)&a, sizeof(a)); return ks_none();
}
static long long system_socket_listen(ks_val_t sock, ks_val_t backlog) {
    _ks_socket_t* s = _ks_sock_unwrap(sock); if (!s) return -1;
    return listen(s->fd, (int)_ks_as_i(backlog)) == 0 ? 0 : -1;
}
static ks_val_t system_socket_accept(ks_val_t sock) {
    _ks_socket_t* s = _ks_sock_unwrap(sock);
    ks_val_t* e = (ks_val_t*)malloc(2*sizeof(ks_val_t));
    if (!s) { e[0]=ks_none(); e[1]=ks_none(); ks_array* a=(ks_array*)malloc(sizeof(ks_array)); a->data=e; a->length=2; a->cap=2; return ks_arr(a); }
    struct sockaddr_in addr; socklen_t alen = sizeof(addr);
    int c = accept(s->fd, (struct sockaddr*)&addr, &alen);
    if (c < 0) { e[0]=ks_none(); e[1]=ks_none(); }
    else { _ks_socket_t* cs = (_ks_socket_t*)malloc(sizeof(_ks_socket_t)); cs->fd = c; e[0] = ks_obj(cs);
        char as[64]; snprintf(as, sizeof(as), "%s:%d", inet_ntoa(addr.sin_addr), ntohs(addr.sin_port)); e[1] = ks_str(strdup(as)); }
    ks_array* a = (ks_array*)malloc(sizeof(ks_array)); a->data = e; a->length = 2; a->cap = 2;
    return ks_arr(a);
}
static long long system_socket_connect(ks_val_t sock, ks_val_t host, ks_val_t port) {
    _ks_socket_t* s = _ks_sock_unwrap(sock); if (!s) return -1;
    struct sockaddr_in a = _ks_sock_resolve(ks_v_str(host), (int)_ks_as_i(port));
    return connect(s->fd, (struct sockaddr*)&a, sizeof(a)) == 0 ? 0 : -1;
}
static long long system_socket_connect_timeout(ks_val_t sock, ks_val_t host, ks_val_t port, ks_val_t timeout) {
    _ks_socket_t* s = _ks_sock_unwrap(sock); if (!s) return -1;
    struct sockaddr_in a = _ks_sock_resolve(ks_v_str(host), (int)_ks_as_i(port));
    double t = _ks_as_f(timeout);
    int fl = fcntl(s->fd, F_GETFL, 0); if (fl < 0) fl = 0;
    fcntl(s->fd, F_SETFL, fl | O_NONBLOCK);
    int r = connect(s->fd, (struct sockaddr*)&a, sizeof(a));
    if (r < 0 && errno == EINPROGRESS) {
        struct timeval tv;
        tv.tv_sec = (time_t)t; tv.tv_usec = (suseconds_t)((t - (double)(long long)t) * 1000000.0);
        fd_set wset; FD_ZERO(&wset); FD_SET(s->fd, &wset);
        int sr = select(s->fd + 1, NULL, &wset, NULL, &tv);
        if (sr > 0) {
            int soerr = 0; socklen_t sl = sizeof(soerr);
            if (getsockopt(s->fd, SOL_SOCKET, SO_ERROR, &soerr, &sl) == 0 && soerr == 0) r = 0;
            else r = -1;
        } else r = -1;
    }
    fcntl(s->fd, F_SETFL, fl);
    return r == 0 ? 0 : -1;
}
static long long system_socket_send(ks_val_t sock, ks_val_t data) {
    _ks_socket_t* s = _ks_sock_unwrap(sock); if (!s) return -1;
    char* d = ks_v_str(data); int r = send(s->fd, d, strlen(d), 0); return r >= 0 ? r : -1;
}
static char* system_socket_recv(ks_val_t sock, ks_val_t size) {
    _ks_socket_t* s = _ks_sock_unwrap(sock);
    char* buf = (char*)malloc((size_t)_ks_as_i(size) + 1); if (!s) { buf[0]=0; return buf; }
    int n = recv(s->fd, buf, (size_t)_ks_as_i(size), 0);
    if (n > 0) buf[n] = 0; else buf[0] = 0;
    return buf;
}
static long long system_socket_close(ks_val_t sock) {
    _ks_socket_t* s = _ks_sock_unwrap(sock); if (!s) return -1;
    int r = close(s->fd); free(s); return r == 0 ? 0 : -1;
}
static long long system_socket_settimeout(ks_val_t sock, ks_val_t timeout) {
    _ks_socket_t* s = _ks_sock_unwrap(sock); if (!s) return -1;
    double t = _ks_as_f(timeout);
    struct timeval tv; tv.tv_sec = (int)t; tv.tv_usec = (int)((t - tv.tv_sec)*1000000);
    setsockopt(s->fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(s->fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv)); return 0;
}
static long long system_socket_setblocking(ks_val_t sock, ks_val_t flag) {
    _ks_socket_t* s = _ks_sock_unwrap(sock); if (!s) return -1;
    long long fl = fcntl(s->fd, F_GETFL, 0); if (fl < 0) return -1;
    if (_ks_as_i(flag)) fl |= O_NONBLOCK; else fl &= ~O_NONBLOCK;
    return fcntl(s->fd, F_SETFL, fl) == 0 ? 0 : -1;
}
static char* system_socket_gethostname() { char b[256]; gethostname(b, sizeof(b)); return strdup(b); }
static char* system_socket_gethostbyname(ks_val_t host) {
    struct hostent* he = gethostbyname(ks_v_str(host));
    if (!he) return strdup("");
    struct in_addr a; memcpy(&a, he->h_addr_list[0], he->h_length); return strdup(inet_ntoa(a));
}
static ks_val_t system_socket_sendto(ks_val_t sock, ks_val_t data, ks_val_t host, ks_val_t port, ks_val_t flags) {
    _ks_socket_t* s = _ks_sock_unwrap(sock); if (!s) return ks_none();
    struct sockaddr_in a = _ks_sock_resolve(ks_v_str(host), (int)_ks_as_i(port));
    sendto(s->fd, ks_v_str(data), strlen(ks_v_str(data)), 0, (struct sockaddr*)&a, sizeof(a)); return ks_none();
}
static ks_val_t system_socket_recvfrom(ks_val_t sock, ks_val_t size, ks_val_t flags) {
    _ks_socket_t* s = _ks_sock_unwrap(sock);
    ks_val_t* e = (ks_val_t*)malloc(2*sizeof(ks_val_t));
    char* buf = (char*)malloc((size_t)_ks_as_i(size) + 1);
    if (!s) { buf[0]=0; e[0]=ks_str(buf); e[1]=ks_str(strdup("")); }
    else { struct sockaddr_in addr; socklen_t alen=sizeof(addr); int n = recvfrom(s->fd, buf, (size_t)_ks_as_i(size), 0, (struct sockaddr*)&addr, &alen); if (n>0) buf[n]=0; else buf[0]=0;
        e[0]=ks_str(buf); char as[64]; snprintf(as,sizeof(as),"%s:%d",inet_ntoa(addr.sin_addr),ntohs(addr.sin_port)); e[1]=ks_str(strdup(as)); }
    ks_array* a=(ks_array*)malloc(sizeof(ks_array)); a->data=e; a->length=2; a->cap=2; return ks_arr(a);
}
static ks_val_t system_socket_getaddrinfo(char* host, ks_val_t port, ks_val_t f, ks_val_t t, ks_val_t p, ks_val_t fl) {
    struct addrinfo hints, *res; memset(&hints,0,sizeof(hints)); hints.ai_family=AF_UNSPEC; hints.ai_socktype=SOCK_STREAM;
    char sp[16]; snprintf(sp,sizeof(sp),"%lld",_ks_as_i(port));
    if (getaddrinfo(host, sp, &hints, &res) != 0) return ks_arr((ks_array*)malloc(sizeof(ks_array)));
    ks_val_t* e=(ks_val_t*)malloc(sizeof(ks_val_t)); e[0]=ks_str(strdup(host));
    ks_array* a=(ks_array*)malloc(sizeof(ks_array)); a->data=e; a->length=1; a->cap=1; freeaddrinfo(res); return ks_arr(a);
}
static ks_val_t system_socket_inet_aton(char* ip) { struct in_addr a; if (inet_aton(ip,&a)) return ks_str(strdup(inet_ntoa(a))); return ks_str(strdup("")); }
static ks_val_t system_socket_inet_ntoa(ks_val_t packed) { return ks_str(strdup("")); }
#include <sys/wait.h>
typedef struct { long long returncode; char* stdout; char* stderr; } _ks_subprocess_result_t;
static ks_val_t ks_subprocess_run(char* cmd, ks_val_t shell, ks_val_t capture) {
    _ks_subprocess_result_t* r = (_ks_subprocess_result_t*)malloc(sizeof(_ks_subprocess_result_t));
    r->returncode = 0; r->stdout = strdup(""); r->stderr = strdup("");
    FILE* fp = popen(cmd, "r");
    if (!fp) { r->returncode = -1; }
    else {
        if (_ks_as_i(capture)) {
            size_t cap = 4096, len = 0; char* out = (char*)malloc(cap); out[0] = 0;
            char tmp[4096]; size_t n;
            while ((n = fread(tmp, 1, sizeof(tmp), fp)) > 0) { if (len + n + 1 >= cap) { cap *= 2; out = (char*)realloc(out, cap); } memcpy(out + len, tmp, n); len += n; }
            out[len] = 0; r->stdout = out;
        }
        int st = pclose(fp); r->returncode = (st < 0) ? -1 : WEXITSTATUS(st);
    }
    ks_val_t* e = (ks_val_t*)malloc(3*sizeof(ks_val_t));
    e[0] = ks_int(r->returncode); e[1] = ks_str(strdup(r->stdout ? r->stdout : "")); e[2] = ks_str(strdup(r->stderr ? r->stderr : ""));
    ks_array* a = (ks_array*)malloc(sizeof(ks_array)); a->data = e; a->length = 3; a->cap = 3;
    free(r->stdout); free(r->stderr); free(r);
    return ks_arr(a);
}
static char* _ks_input(char* prompt) {
    if (prompt) { fputs(prompt, stdout); fflush(stdout); }
    size_t _cap = 256, _len = 0; char* _buf = (char*)malloc(_cap);
    int _c; while ((_c = getchar()) != EOF && _c != '\n') {
        if (_len + 1 >= _cap) { _cap *= 2; _buf = (char*)realloc(_buf, _cap); }
        _buf[_len++] = (char)_c;
    }
    _buf[_len] = 0; return _buf;
}

/* ===== KentScript async/await runtime (ucontext) ===== */
#include <ucontext.h>
#define KS_CORO_STACK 65536
typedef struct {
    ucontext_t ctx;
    ucontext_t caller;
    char stack[KS_CORO_STACK];
    void (*fn)(void*);
    void* arg;
    void* result;   /* wide enough for any pointer or integer */
    int done;
} _ks_coro_t;
static _ks_coro_t* _ks_coro_current = NULL;
static void _ks_coro_entry(_ks_coro_t* c) {
    c->fn(c->arg);
    c->done = 1;
    swapcontext(&c->ctx, &c->caller);
}
static _ks_coro_t* _ks_coro_new(void (*fn)(void*), void* arg) {
    _ks_coro_t* c = (_ks_coro_t*)calloc(1, sizeof(_ks_coro_t));
    c->fn = fn; c->arg = arg;
    getcontext(&c->ctx);
    c->ctx.uc_stack.ss_sp = c->stack;
    c->ctx.uc_stack.ss_size = KS_CORO_STACK;
    c->ctx.uc_link = NULL;
    makecontext(&c->ctx, (void(*)())_ks_coro_entry, 1, c);
    return c;
}
static void* _ks_coro_run(_ks_coro_t* c) {
    _ks_coro_t* prev = _ks_coro_current;
    _ks_coro_current = c;
    swapcontext(&c->caller, &c->ctx);
    _ks_coro_current = prev;
    return c->result;
}
/* await void: suspend coroutine after calling void expression */
#define _KS_AWAIT_VOID(expr) do {                              \
    (expr);                                                     \
    if (_ks_coro_current)                                       \
        swapcontext(&_ks_coro_current->ctx,                     \
                    &_ks_coro_current->caller);                 \
} while(0)
/* await value: suspend coroutine and return value */
#define _KS_AWAIT(expr) (__extension__({                        \
    __typeof__(expr) _ks_r = (expr);                            \
    if (_ks_coro_current) {                                     \
        _ks_coro_current->result = (void*)(uintptr_t)(long long)_ks_r; \
        swapcontext(&_ks_coro_current->ctx,                     \
                    &_ks_coro_current->caller);                 \
    }                                                            \
    _ks_r;                                                      \
}))
/* async.run(fn) — create coroutine and drive to completion */
static void* _ks_async_run_fn(void (*fn)(void*)) {
    _ks_coro_t* c = _ks_coro_new(fn, NULL);
    while (!c->done) _ks_coro_run(c);
    void* r = c->result; free(c); return r;
}
/* ===== end async runtime ===== */


void describe_number(ks_val_t n);
void describe_status(ks_val_t code);

#line 4 "examples/pattern_matching.ks"
void describe_number(ks_val_t n) {
    { /* match statement */
        ks_val_t _match_v = n;
        if (ks_v_cmp(_match_v, KS_INT(0LL)) == 0) {
            ks_val_print(ks_str("Zero")); printf("\n");
        } else if (ks_v_cmp(_match_v, KS_INT(1LL)) == 0) {
            ks_val_print(ks_str("One")); printf("\n");
        } else if (ks_v_cmp(_match_v, KS_INT(2LL)) == 0) {
            ks_val_print(ks_str("Two")); printf("\n");
        } else {
            ks_val_print(ks_str(_ks_concat("Other: ", ks_val_to_str(n)))); printf("\n");
        }
    }
}

#line 29 "examples/pattern_matching.ks"
void describe_status(ks_val_t code) {
    { /* match statement */
        ks_val_t _match_v = code;
        if (ks_v_cmp(_match_v, KS_INT(200LL)) == 0) {
            ks_val_print(ks_str("200: OK")); printf("\n");
        } else if (ks_v_cmp(_match_v, KS_INT(404LL)) == 0) {
            ks_val_print(ks_str("404: Not Found")); printf("\n");
        } else if (ks_v_cmp(_match_v, KS_INT(500LL)) == 0) {
            ks_val_print(ks_str("500: Internal Server Error")); printf("\n");
        } else {
            ks_val_print(ks_str("Unknown status code")); printf("\n");
        }
    }
}

int main(int argc, char** argv) {
    ks_argc = argc; ks_argv = argv;
#line 22 "examples/pattern_matching.ks"
    describe_number(KS_INT(0LL));
#line 23 "examples/pattern_matching.ks"
    describe_number(KS_INT(1LL));
#line 24 "examples/pattern_matching.ks"
    describe_number(KS_INT(2LL));
#line 25 "examples/pattern_matching.ks"
    describe_number(KS_INT(42LL));
#line 27 "examples/pattern_matching.ks"
    ks_val_print(ks_str("")); printf("\n");
#line 46 "examples/pattern_matching.ks"
    ks_val_print(ks_str("HTTP Status Codes:")); printf("\n");
#line 47 "examples/pattern_matching.ks"
    describe_status(KS_INT(200LL));
#line 48 "examples/pattern_matching.ks"
    describe_status(KS_INT(404LL));
#line 49 "examples/pattern_matching.ks"
    describe_status(KS_INT(500LL));
#line 50 "examples/pattern_matching.ks"
    describe_status(KS_INT(418LL));
#line 52 "examples/pattern_matching.ks"
    ks_val_print(ks_str("")); printf("\n");
#line 53 "examples/pattern_matching.ks"
    ks_val_print(ks_str("Pattern matching working!")); printf("\n");
    return 0;
}