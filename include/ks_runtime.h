/* ============================================================================
 * ks_runtime.h - KentScript v3.1 MASTER RUNTIME HEADER
 * ========================================================================== */

#pragma once
#ifndef KS_RUNTIME_H
#define KS_RUNTIME_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ============================================================================
 * Per-file compiler optimization pragmas  (GCC / Clang) - disabled for portability
 * ========================================================================== */

/* ============================================================================
 * Memory barriers (architecture-specific)
 * ========================================================================== */
#ifdef __x86_64__
    #define KS_MB()  __asm__ volatile("mfence":::"memory")
    #define KS_RMB() __asm__ volatile("lfence":::"memory")
    #define KS_WMB() __asm__ volatile("sfence":::"memory")
#elif defined(__aarch64__)
    #define KS_MB()  __asm__ volatile("dmb ish":::"memory")
    #define KS_RMB() __asm__ volatile("dmb ishld":::"memory")
    #define KS_WMB() __asm__ volatile("dmb ishst":::"memory")
#else
    #define KS_MB()  __sync_synchronize()
    #define KS_RMB() __sync_synchronize()
    #define KS_WMB() __sync_synchronize()
#endif
#define KS_COMPILER_BARRIER() __asm__ volatile("":::"memory")

/* ============================================================================
 * Cache-line aligned types
 * ========================================================================== */
#define KS_CACHE_LINE 64
#define KS_PAGE_SIZE 4096

/* ============================================================================
 * Compact type aliases
 * ========================================================================== */
typedef uint8_t  u8;  typedef uint16_t u16;
typedef uint32_t u32; typedef uint64_t u64;
typedef int8_t   i8;  typedef int16_t  i16;
typedef int32_t  i32; typedef int64_t  i64;
typedef float    f32; typedef double   f64;

/* ============================================================================
 * Cache flush - define only if not already defined
 * ========================================================================== */
#ifndef KS_NO_CACHE_FLUSH
static inline void ks_cache_flush(void *addr, size_t size) {
#ifdef __x86_64__
    for (size_t i = 0; i < size; i += KS_CACHE_LINE)
        __asm__ volatile("clflush %0":"+m"(*(char*)((uintptr_t)addr+i)));
#endif
}
#endif

/* ============================================================================
 * Version
 * ========================================================================== */
#define KS_RUNTIME_VERSION "3.1.0"

/* ============================================================================
 * FILE OPERATIONS (system_file_*)
 * ========================================================================== */
long long system_file_stat(const char *path);
void system_file_write_text(const char *path, const char *content);
char* system_file_read_text(const char *path);
int system_file_remove(const char *path);
int system_file_rename(const char *oldpath, const char *newpath);
void* system_file_open(const char *path, const char *mode);
long long system_file_getsize(const char *path);
int system_file_close(void* f);
char* system_file_read_line(void* f);

/* ============================================================================
 * SUBPROCESS OPERATIONS
 * ========================================================================== */
int system_subprocess_run(const char *cmd, long long *exit_code);
int system_file_chmod(const char *path, long long mode);
int system_file_symlink(const char *target, const char *linkpath);
long long system_file_exists(const char *path);
char* system_file_readlink(const char *path);

/* ============================================================================
 * OS OPERATIONS (system_os_*)
 * ========================================================================== */
long long system_os_getppid(void);
long long system_os_getuid(void);
long long system_os_getgid(void);
char* system_os_getenv(const char *name, const char *default_val);
int system_os_setenv(const char *name, const char *value);
int system_os_unsetenv(const char *name);
long long system_os_getpid(void);
int system_os_kill(long long pid, long long sig);
int system_os_mkdir(const char *path, long long mode);
int system_os_rmdir(const char *path);
int system_os_rename(const char *oldpath, const char *newpath);

/* ============================================================================
 * RANDOM OPERATIONS (system_random_*)
 * ========================================================================== */
long long system_random_random(void);
long long system_random_randint(long long a, long long b);
double system_random_uniform(double a, double b);
long long system_random_choice(long long *arr, long long len);
void system_random_seed(long long seed);

/* ============================================================================
 * TIME OPERATIONS (system_time_*)
 * ========================================================================== */
double system_time_time(void);
void system_time_sleep(double seconds);

/* ============================================================================
 * COLLECTIONS OPERATIONS (system_collections_*)
 * ========================================================================== */
long long system_collections_deque(long long *items, long long num_items);
long long system_collections_counter(long long *items, long long num_items);
long long system_collections_ordered_dict(void);
long long system_collections_defaultdict(const char *factory);
long long system_collections_namedtuple(const char *name, long long *fields, long long num_fields);

/* ============================================================================
 * STRING OPERATIONS (system_strings_*)
 * ========================================================================== */
char* system_strings_join(long long *arr, long long len, const char *sep);
char* system_strings_split(const char *str, const char *sep);
int system_strings_contains(const char *s, const char *substr);
char* system_strings_upper(const char *s);
char* system_strings_lower(const char *s);
int system_strings_startswith(const char *s, const char *prefix);
int system_strings_endswith(const char *s, const char *suffix);
char* system_strings_replace(const char *s, const char *old, const char *repl);

/* ============================================================================
 * ENCODING OPERATIONS (system_encoding_*)
 * ========================================================================== */
char* system_encoding_base64_encode(const char *data);
char* system_encoding_base64_decode(const char *data);
char* system_encoding_hex_encode(const char *data);
char* system_encoding_hex_decode(const char *data);

/* ============================================================================
 * HTTP OPERATIONS (system_http_*)
 * ========================================================================== */
typedef struct {
    int status;
    char *body;
    char *error;
} ks_http_response;

ks_http_response* system_http_get(const char *url, const char *headers);
ks_http_response* system_http_post(const char *url, const char *headers, const char *body);
void system_http_response_free(ks_http_response *resp);

/* ============================================================================
 * SUBPROCESS OPERATIONS
 * ========================================================================== */
int system_subprocess_run(const char *cmd, long long *exit_code);

#endif /* KS_RUNTIME_H */
