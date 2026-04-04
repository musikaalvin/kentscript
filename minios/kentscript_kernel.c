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
#include <sys/mman.h>
#include <unistd.h>
#include <sys/syscall.h>

/* KentScript compatibility macros */
#define None ((long long)0)
#define true 1
#define false 0

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

/* ---- Fallback inline helpers (only if ks_runtime.h functions missing) ---- */
#ifndef KS_RUNTIME_HAVE_ALL_FUNCS
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
static char* _ks_str_hex(long long v) {
    char *b = _ks_newbuf();
    snprintf(b, 4096, "%llx", v); return b;
}
static char* _ks_str_dbl(double v) {
    char *b = _ks_newbuf();
    if (v == (long long)v) snprintf(b,4096,"%.1f",v);
    else snprintf(b,4096,"%g",v); return b;
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
typedef struct { long long* data; long long length; } ks_array;
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
    long long** parts = (long long**)malloc(cap * sizeof(long long*));
    int seplen = strlen(sep); const char* p = s;
    while (*p) {
        const char* found = strstr(p, sep);
        if (!found) found = p + strlen(p);
        long long n = found - p;
        char* part = (char*)malloc(n + 1); memcpy(part, p, n); part[n] = 0;
        if (count >= cap) { cap *= 2; parts = (long long**)realloc(parts, cap * sizeof(long long*)); }
        parts[count++] = (long long*)part;
        p = *found ? found + seplen : found;
    }
    ks_array arr; arr.data = (long long*)parts; arr.length = count; return arr;
}
static void _ks_array_append(ks_array* arr, long long val) {
    long long* new_data = (long long*)malloc((arr->length + 1) * sizeof(long long));
    if (arr->data) memcpy(new_data, arr->data, arr->length * sizeof(long long));
    new_data[arr->length] = val;
    arr->data = new_data; arr->length++;
}
static long long _ks_array_pop(ks_array* arr) {
    if (arr->length == 0) return 0;
    long long val = arr->data[arr->length - 1];
    arr->length--; return val;
}
static char* _ks_str_join(const char* sep, ks_array arr) {
    char *r = _ks_newbuf(); int pos = 0;
    for (long long i = 0; i < arr.length && pos < 4090; i++) {
        if (i > 0) { int sl = strlen(sep); memcpy(r+pos, sep, sl); pos += sl; }
        const char* s = (const char*)arr.data[i];
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
typedef struct { _ks_dict_node* buckets[32]; } _ks_dict;
static unsigned int _ks_hash(const char* s) {
    unsigned int h = 5381; int c;
    while ((c = *s++)) h = ((h << 5) + h) + c;
    return h % 32;
}
static _ks_dict* _ks_dict_new(void) {
    _ks_dict* d = malloc(sizeof(_ks_dict));
    memset(d->buckets, 0, sizeof(d->buckets));
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
/* Helper to create and populate dict */
static _ks_dict* _ks_dict_create(const char* k1, long long v1, int s1, const char* k2, long long v2, int s2) {
    _ks_dict* d = _ks_dict_new();
    _ks_dict_set(d, k1, v1, s1);
    _ks_dict_set(d, k2, v2, s2);
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
static inline void* ks_malloc(size_t size) { return malloc(size); }
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
static inline ks_array ks_make_array(long long* data, long long len) {
    ks_array arr = {data, len};
    return arr;
}
static inline long long ks_array_get(ks_array arr, long long idx) {
    return arr.data[idx];
}
static inline long long ks_array_len(ks_array arr) {
    return arr.length;
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
typedef struct { long long status; char* text; } _ks_http_response_t;
static _ks_http_response_t _ks_http_get(const char* url) { _ks_http_response_t r = {0, ""}; return r; }
static _ks_http_response_t _ks_http_post(const char* url, const char* data) { _ks_http_response_t r = {0, ""}; return r; }
static long long _ks_json_loads(const char* json_str) { return 0; }
static long long ks_system_socket_create(int domain, int type, int protocol) {
    int sock = socket(domain, type, protocol);
    return sock >= 0 ? (long long)sock : -1;
}
static long long ks_system_socket_settimeout(long long sock, double timeout) {
    struct timeval tv;
    tv.tv_sec = (int)timeout;
    tv.tv_usec = (int)((timeout - tv.tv_sec) * 1000000);
    setsockopt((int)sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt((int)sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
    return 0;
}
static long long ks_system_socket_connect(long long sock, const char* host, int port) {
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    if (inet_pton(AF_INET, host, &addr.sin_addr) <= 0) {
        struct hostent* he = gethostbyname(host);
        if (!he) return -1;
        memcpy(&addr.sin_addr, he->h_addr_list[0], he->h_length);
    }
    return connect((int)sock, (struct sockaddr*)&addr, sizeof(addr)) == 0 ? 0 : -1;
}
static long long ks_system_socket_send(long long sock, const char* data) {
    int result = send((int)sock, data, strlen(data), 0);
    return result >= 0 ? result : -1;
}
static char* ks_system_socket_recv(long long sock, int size) {
    char* buffer = (char*)malloc(size + 1);
    if (!buffer) return NULL;
    int n = recv((int)sock, buffer, size, 0);
    if (n > 0) buffer[n] = 0;
    else buffer[0] = 0;
    return buffer;
}
static long long ks_system_socket_close(long long sock) {
    return close((int)sock) == 0 ? 0 : -1;
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


typedef struct {
    long long id;
    char* name;
    char* state;
    long long ticks;
    long long stack;
} Task;

typedef struct {
    char* name;
    char* node_type;
    char* data;
    long long size;
    long long parent;
    long long child;
} VFSNode;

long long kmalloc(long long size);
long long kstrlen(ks_array s);
void uart_putc(long long c);
void uart_puts(ks_array msg);
void scheduler_init(void);
double scheduler_add(long long name);
void scheduler_tick(void);
void vfs_init(void);
void minios_main(void);

long long* tasks = NULL; /* list not fully supported */
long long current_task = 0;
long long vfs_root = 0;

long long kmalloc(long long size) {
    return ks_malloc(size);
    return 0LL;
}

long long kstrlen(ks_array s) {
    long long i = 0;
    while ((i < ks_array_len(s))) {
        if (__builtin_expect(((ks_array_get(s, i) == 0)), 0)) {
            return i;
        }
        i = (i + 1);
    }
    return 0;
    return 0LL;
}

void uart_putc(long long c) {
    long long uart = ((*i32)0x09000000);
    while (((_ks_dict_get_simple(uart, 6) & 32) != 0)) {
    }
    (uart)[0] = c;
}

void uart_puts(ks_array msg) {
    long long i = 0;
    while ((i < ks_array_len(msg))) {
        if ((ks_array_get(msg, i) == 10)) {
            uart_putc(13);
        }
        uart_putc(ks_array_get(msg, i));
        i = (i + 1);
    }
}

void scheduler_init(void) {
    ks_array tasks = { .data = NULL, .length = 0 };
    current_task = 0;
}

double scheduler_add(long long name) {
    long long t = __new_Task__();
    /* member access: t.name = name */
    /* member access: t.state = "READY" */
    /* member access: t.ticks = 0 */
    _ks_push(tasks, t);
    return (ks_array_len(tasks) - 1);
    return 0.0;
}

void scheduler_tick(void) {
    long long n = ks_array_len(tasks);
    if ((n <= 1)) {
        return;
    }
    current_task = (current_task + 1);
    if ((current_task >= n)) {
        current_task = 1;
    }
    /* member access: tasks[current_task].ticks = _ks_concat(0  /* tasks[current_task].ticks */, _ks_str_int(1)) */
}

void vfs_init(void) {
    vfs_root = __new_VFSNode__();
    /* member access: vfs_root.name = "/" */
    /* member access: vfs_root.node_type = "dir" */
    long long bin = __new_VFSNode__();
    /* member access: bin.name = "bin" */
    /* member access: bin.node_type = "dir" */
    /* member access: bin.parent = vfs_root */
    /* member access: vfs_root.child = bin */
    long long sh = __new_VFSNode__();
    /* member access: sh.name = "sh" */
    /* member access: sh.node_type = "file" */
    /* member access: sh.data = "#!/bin/sh\necho 'MiniOS Shell'\n" */
    /* member access: sh.size = ks_array_len(0  /* sh.data */) */
    /* member access: sh.parent = bin */
    /* member access: bin.child = sh */
}

void minios_main(void) {
    uart_puts("=== MiniOS (KentScript) ===\n");
    uart_puts("Kernel written in KentScript\n");
    uart_puts("============================\n");
    scheduler_init();
    scheduler_add("idle");
    scheduler_add("init");
    scheduler_add("shell");
    uart_puts("Tasks: ");
    uart_puts(ks_array_len(tasks));
    uart_puts("\n");
    scheduler_tick();
    scheduler_tick();
    uart_puts("Scheduler ticks OK\n");
    vfs_init();
    uart_puts("VFS initialized\n");
    uart_puts("\nMiniOS KentScript ready!\n");
}

int main(void) {
    /* struct Task */
    typedef struct {
        i32 id;
        string name;
        string state;
        i32 ticks;
        *i32 stack;
    } Task_t;
    /* struct VFSNode */
    typedef struct {
        string name;
        string node_type;
        string data;
        i32 size;
        *VFSNode parent;
        *VFSNode child;
    } VFSNode_t;
    minios_main();
    return 0;
}