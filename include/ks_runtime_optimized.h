/*
 * ⚡ KentScript Zero-Overhead Runtime v3.0 Enhanced
 * Complete cross-platform systems programming runtime
 * Real slab allocator, futex sync, NUMA-aware, Ring-0 capable
 */

#ifndef KS_RUNTIME_H
#define KS_RUNTIME_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* ============================================================================
 * ARCHITECTURE DETECTION - ENHANCED
 * ========================================================================== */

#if defined(__x86_64__) || defined(__amd64__) || defined(_M_X64)
    #define KS_ARCH_X86_64 1
    #define KS_SYSCALL_ARCH "x86_64"
    #define KS_CACHE_LINE 64
#elif defined(__aarch64__) || defined(__arm64__) || defined(_M_ARM64)
    #define KS_ARCH_AARCH64 1
    #define KS_SYSCALL_ARCH "aarch64"
    #define KS_CACHE_LINE 64
#elif defined(__i386__) || defined(_M_IX86)
    #define KS_ARCH_X86 1
    #define KS_SYSCALL_ARCH "x86"
    #define KS_CACHE_LINE 64
#elif defined(__arm__) || defined(_M_ARM)
    #define KS_ARCH_ARM 1
    #define KS_SYSCALL_ARCH "arm"
    #define KS_CACHE_LINE 32
#else
    #error "Unsupported architecture - KentScript requires x86, x86-64, ARM, or ARM64"
#endif

/* OS Detection */
#if defined(__linux__)
    #define KS_OS_LINUX 1
    #define KS_OS_NAME "linux"
#elif defined(__APPLE__) && defined(__MACH__)
    #define KS_OS_MACOS 1
    #define KS_OS_NAME "macos"
#elif defined(_WIN32) || defined(_WIN64)
    #define KS_OS_WINDOWS 1
    #define KS_OS_NAME "windows"
    #ifndef WIN32_LEAN_AND_MEAN
        #define WIN32_LEAN_AND_MEAN
    #endif
    #include <windows.h>
#elif defined(__FreeBSD__) || defined(__OpenBSD__) || defined(__NetBSD__)
    #define KS_OS_BSD 1
    #define KS_OS_NAME "bsd"
#else
    #error "Unsupported OS - KentScript requires Linux, macOS, Windows, or BSD"
#endif

/* CPU feature detection */
#if defined(KS_ARCH_X86_64) || defined(KS_ARCH_X86)
    static inline void ks_cpuid(int code, uint32_t* a, uint32_t* b, uint32_t* c, uint32_t* d) {
        __asm__ volatile("cpuid"
            : "=a"(*a), "=b"(*b), "=c"(*c), "=d"(*d)
            : "a"(code), "c"(0));
    }
    
    #define KS_HAVE_CPUID 1
#endif

/* ============================================================================
 * COMPILER BUILTINS & ATTRIBUTES - ENHANCED
 * ========================================================================== */

#define LIKELY(x)      __builtin_expect(!!(x), 1)
#define UNLIKELY(x)    __builtin_expect(!!(x), 0)
#define ALIGNED(n)     __attribute__((aligned(n)))
#define RESTRICT       __restrict
#define INLINE         inline __attribute__((always_inline))
#define NOINLINE       __attribute__((noinline))
#define HOT            __attribute__((hot))
#define COLD           __attribute__((cold))
#define PURE           __attribute__((pure))
#define CONST          __attribute__((const))
#define PACKED         __attribute__((packed))
#define USED           __attribute__((used))
#define WEAK           __attribute__((weak))
#define NORETURN       __attribute__((noreturn))
#define SECTION(s)     __attribute__((section(s)))
#define FORCE_INLINE   __attribute__((always_inline)) inline

/* ============================================================================
 * MEMORY ALLOCATION - REAL SLAB ALLOCATOR (not just bump)
 * O(1) allocation/deallocation, cache-friendly, deterministic
 * Supports multiple size classes, free lists, and NUMA awareness
 * ========================================================================== */

#define KS_SLAB_MIN_SIZE    8
#define KS_SLAB_MAX_SIZE    4096
#define KS_SLAB_SIZE_CLASSES 10  /* 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096 */
#define KS_SLABS_PER_CLASS  64
#define KS_SLAB_PAGE_SIZE   4096
#define KS_CACHE_LINE_SIZE  64

/* Size class configuration */
static const size_t ks_slab_sizes[KS_SLAB_SIZE_CLASSES] = {
    8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096
};

/* Per-slab metadata */
typedef struct KSSlab {
    struct KSSlab* next;                    /* Next slab in free list */
    struct KSSlab* prev;                    /* Previous slab in free list */
    uint8_t*       memory;                   /* Slab memory region */
    size_t         obj_size;                  /* Size of each object */
    uint32_t       free_count;                 /* Number of free objects */
    uint32_t       total_objects;               /* Total objects in slab */
    uint32_t       first_free;                  /* Index of first free object */
    uint32_t       magic;                       /* Magic number for validation */
    ALIGNED(KS_CACHE_LINE_SIZE) uint8_t bitmap[];  /* Free bitmap (variable size) */
} KSSlab;

/* Per-size-class allocator */
typedef struct {
    KSSlab* partial_slabs;                   /* Partially used slabs */
    KSSlab* full_slabs;                       /* Completely full slabs */
    KSSlab* empty_slabs;                       /* Empty slabs */
    size_t  obj_size;                          /* Size of objects in this class */
    uint32_t objs_per_slab;                    /* Objects per slab */
    uint32_t slab_bitmap_size;                  /* Size of bitmap in bytes */
    uint32_t active_slabs;                      /* Number of active slabs */
    uint32_t total_allocated;                   /* Total allocated objects */
    uint32_t total_freed;                        /* Total freed objects */
} KSSlabClass;

/* NUMA node information */
typedef struct {
    uint32_t node_id;
    uint32_t cpu_count;
    uintptr_t base_addr;
    size_t    memory_size;
} KSNumaNode;

/* Main allocator structure - cache-line aligned to prevent false sharing */
typedef struct ALIGNED(KS_CACHE_LINE_SIZE) {
    KSSlabClass classes[KS_SLAB_SIZE_CLASSES];
    void*       (*mmap_func)(size_t, int);     /* Custom mmap for testing */
    void        (*munmap_func)(void*, size_t);  /* Custom munmap */
    uint32_t    numa_node_count;
    KSNumaNode  numa_nodes[8];                   /* Max 8 NUMA nodes */
    uint64_t    total_memory;
    uint64_t    used_memory;
    uint64_t    peak_memory;
    uint32_t    slab_magic;                      /* Magic for validation */
    uint32_t    initialized;
} KSAllocator;

/* Global allocator instance */
extern KSAllocator ks_global_allocator;

/* Allocator API */
void ks_allocator_init(void);
void ks_allocator_init_numa(void);
void* ks_malloc(size_t size);
void* ks_malloc_numa(size_t size, int node);
void* ks_calloc(size_t nmemb, size_t size);
void* ks_realloc(void* ptr, size_t size);
void ks_free(void* ptr);
void ks_allocator_stats(uint64_t* total, uint64_t* used, uint64_t* peak);
void ks_allocator_dump(void);

/* ============================================================================
 * THREAD SYNCHRONIZATION - FUTEX-BASED (Linux) + SRW (Windows) + ulock (macOS)
 * ========================================================================== */

typedef enum {
    KS_LOCK_UNLOCKED = 0,
    KS_LOCK_LOCKED = 1,
    KS_LOCK_CONTENDED = 2
} KSLockState;

/* Futex-based mutex (Linux) - 4 bytes, cache-line aligned */
typedef struct ALIGNED(KS_CACHE_LINE_SIZE) {
    volatile int32_t state;
    volatile int32_t owner;
    volatile uint32_t waiters;
    uint8_t _pad[KS_CACHE_LINE_SIZE - 3 * sizeof(int32_t)];
} KSMutex;

/* Reader-writer lock */
typedef struct ALIGNED(KS_CACHE_LINE_SIZE) {
    volatile int32_t readers;
    volatile int32_t writer;
    volatile uint32_t waiters_read;
    volatile uint32_t waiters_write;
    uint8_t _pad[KS_CACHE_LINE_SIZE - 4 * sizeof(int32_t)];
} KSRWLock;

/* Condition variable */
typedef struct ALIGNED(KS_CACHE_LINE_SIZE) {
    volatile uint32_t waiters;
    uint8_t _pad[KS_CACHE_LINE_SIZE - sizeof(uint32_t)];
} KSCond;

/* Semaphore */
typedef struct ALIGNED(KS_CACHE_LINE_SIZE) {
    volatile int32_t count;
    volatile uint32_t waiters;
    uint8_t _pad[KS_CACHE_LINE_SIZE - 2 * sizeof(int32_t)];
} KSSem;

/* Barrier */
typedef struct {
    volatile uint32_t count;
    volatile uint32_t total;
    volatile uint32_t phase;
    KSCond cond;
    KSMutex mutex;
} KSBarrier;

/* Mutex API */
void ks_mutex_init(KSMutex* mutex);
void ks_mutex_lock(KSMutex* mutex);
int ks_mutex_trylock(KSMutex* mutex);
void ks_mutex_unlock(KSMutex* mutex);
void ks_mutex_destroy(KSMutex* mutex);

/* RWLock API */
void ks_rwlock_init(KSRWLock* rwlock);
void ks_rwlock_rdlock(KSRWLock* rwlock);
void ks_rwlock_wrlock(KSRWLock* rwlock);
int ks_rwlock_tryrdlock(KSRWLock* rwlock);
int ks_rwlock_trywrlock(KSRWLock* rwlock);
void ks_rwlock_rdunlock(KSRWLock* rwlock);
void ks_rwlock_wrunlock(KSRWLock* rwlock);

/* Condition variable API */
void ks_cond_init(KSCond* cond);
void ks_cond_wait(KSCond* cond, KSMutex* mutex);
int ks_cond_timedwait(KSCond* cond, KSMutex* mutex, uint64_t timeout_ns);
void ks_cond_signal(KSCond* cond);
void ks_cond_broadcast(KSCond* cond);

/* Semaphore API */
void ks_sem_init(KSSem* sem, int initial);
void ks_sem_wait(KSSem* sem);
int ks_sem_trywait(KSSem* sem);
void ks_sem_post(KSSem* sem);
int ks_sem_value(KSSem* sem);

/* Barrier API */
void ks_barrier_init(KSBarrier* barrier, uint32_t count);
void ks_barrier_wait(KSBarrier* barrier);

/* ============================================================================
 * ATOMIC OPERATIONS - COMPREHENSIVE
 * ========================================================================== */

typedef volatile uint64_t ks_atomic64_t;
typedef volatile uint32_t ks_atomic32_t;

/* Atomic load/store with memory ordering */
#define KS_ORDER_RELAXED __ATOMIC_RELAXED
#define KS_ORDER_CONSUME __ATOMIC_CONSUME
#define KS_ORDER_ACQUIRE __ATOMIC_ACQUIRE
#define KS_ORDER_RELEASE __ATOMIC_RELEASE
#define KS_ORDER_ACQ_REL __ATOMIC_ACQ_REL
#define KS_ORDER_SEQ_CST __ATOMIC_SEQ_CST

/* 64-bit atomics */
FORCE_INLINE uint64_t ks_atomic_load(volatile uint64_t* ptr, int order) {
    return __atomic_load_n(ptr, order);
}

FORCE_INLINE void ks_atomic_store(volatile uint64_t* ptr, uint64_t val, int order) {
    __atomic_store_n(ptr, val, order);
}

FORCE_INLINE uint64_t ks_atomic_add(volatile uint64_t* ptr, uint64_t val, int order) {
    return __atomic_fetch_add(ptr, val, order);
}

FORCE_INLINE uint64_t ks_atomic_sub(volatile uint64_t* ptr, uint64_t val, int order) {
    return __atomic_fetch_sub(ptr, val, order);
}

FORCE_INLINE uint64_t ks_atomic_and(volatile uint64_t* ptr, uint64_t val, int order) {
    return __atomic_fetch_and(ptr, val, order);
}

FORCE_INLINE uint64_t ks_atomic_or(volatile uint64_t* ptr, uint64_t val, int order) {
    return __atomic_fetch_or(ptr, val, order);
}

FORCE_INLINE uint64_t ks_atomic_xor(volatile uint64_t* ptr, uint64_t val, int order) {
    return __atomic_fetch_xor(ptr, val, order);
}

FORCE_INLINE uint64_t ks_atomic_exchange(volatile uint64_t* ptr, uint64_t val, int order) {
    return __atomic_exchange_n(ptr, val, order);
}

FORCE_INLINE bool ks_atomic_cas(volatile uint64_t* ptr, uint64_t* expected, uint64_t desired, 
                                 int succ_order, int fail_order) {
    return __atomic_compare_exchange_n(ptr, expected, desired, false, 
                                      succ_order, fail_order);
}

/* 32-bit atomics (similar API) */
FORCE_INLINE uint32_t ks_atomic32_load(volatile uint32_t* ptr, int order) {
    return __atomic_load_n(ptr, order);
}

FORCE_INLINE void ks_atomic32_store(volatile uint32_t* ptr, uint32_t val, int order) {
    __atomic_store_n(ptr, val, order);
}

FORCE_INLINE uint32_t ks_atomic32_add(volatile uint32_t* ptr, uint32_t val, int order) {
    return __atomic_fetch_add(ptr, val, order);
}

/* ============================================================================
 * HARDWARE BARRIERS - ENHANCED
 * ========================================================================== */

/* Full memory barrier */
#ifdef KS_ARCH_X86_64
    #define KS_MB()   __asm__ volatile("mfence" ::: "memory")
    #define KS_RMB()  __asm__ volatile("lfence" ::: "memory")
    #define KS_WMB()  __asm__ volatile("sfence" ::: "memory")
    #define KS_COMPILER_BARRIER() __asm__ volatile("" ::: "memory")
#elif defined(KS_ARCH_AARCH64)
    #define KS_MB()   __asm__ volatile("dmb ish" ::: "memory")
    #define KS_RMB()  __asm__ volatile("dmb ishld" ::: "memory")
    #define KS_WMB()  __asm__ volatile("dmb ishst" ::: "memory")
    #define KS_COMPILER_BARRIER() __asm__ volatile("" ::: "memory")
#else
    #define KS_MB()   __sync_synchronize()
    #define KS_RMB()  __sync_synchronize()
    #define KS_WMB()  __sync_synchronize()
    #define KS_COMPILER_BARRIER() __asm__ volatile("" ::: "memory")
#endif

/* Acquire/Release semantics */
#define KS_ACQUIRE() KS_MB()
#define KS_RELEASE() KS_MB()

/* ============================================================================
 * DIRECT SYSCALLS - CROSS-PLATFORM
 * ========================================================================== */

#ifdef KS_ARCH_X86_64
    /* x86-64 syscall ABI */
    INLINE long ks_syscall6(long n, long a1, long a2, long a3, long a4, long a5, long a6) {
        long ret;
        __asm__ volatile (
            "mov %1, %%rax\n"
            "mov %2, %%rdi\n"
            "mov %3, %%rsi\n"
            "mov %4, %%rdx\n"
            "mov %5, %%r10\n"
            "mov %6, %%r8\n"
            "mov %7, %%r9\n"
            "syscall\n"
            "mov %%rax, %0\n"
            : "=r"(ret)
            : "r"(n), "r"(a1), "r"(a2), "r"(a3), "r"(a4), "r"(a5), "r"(a6)
            : "rax", "rdi", "rsi", "rdx", "r10", "r8", "r9", "rcx", "r11", "memory"
        );
        return ret;
    }

#elif defined(KS_ARCH_AARCH64)
    /* ARM64 syscall ABI */
    INLINE long ks_syscall6(long n, long a1, long a2, long a3, long a4, long a5, long a6) {
        long ret;
        register long x8 __asm__("x8") = n;
        register long x0 __asm__("x0") = a1;
        register long x1 __asm__("x1") = a2;
        register long x2 __asm__("x2") = a3;
        register long x3 __asm__("x3") = a4;
        register long x4 __asm__("x4") = a5;
        register long x5 __asm__("x5") = a6;
        
        __asm__ volatile (
            "svc #0\n"
            : "=r"(x0)
            : "r"(x0), "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5), "r"(x8)
            : "memory"
        );
        ret = x0;
        return ret;
    }

#elif defined(KS_OS_WINDOWS)
    /* Windows syscall via ntdll */
    INLINE long ks_syscall6(long n, long a1, long a2, long a3, long a4, long a5, long a6) {
        /* Windows syscalls are handled via ntdll */
        extern long __stdcall NtQuerySystemInformation(long, void*, long, long*);
        extern long __stdcall NtSetInformationFile(long, void*, void*, long, long);
        /* Implement specific syscalls as needed */
        return -1;
    }
#endif

/* Variadic wrappers */
INLINE long ks_syscall0(long n) {
    return ks_syscall6(n, 0, 0, 0, 0, 0, 0);
}

INLINE long ks_syscall1(long n, long a1) {
    return ks_syscall6(n, a1, 0, 0, 0, 0, 0);
}

INLINE long ks_syscall2(long n, long a1, long a2) {
    return ks_syscall6(n, a1, a2, 0, 0, 0, 0);
}

INLINE long ks_syscall3(long n, long a1, long a2, long a3) {
    return ks_syscall6(n, a1, a2, a3, 0, 0, 0);
}

INLINE long ks_syscall4(long n, long a1, long a2, long a3, long a4) {
    return ks_syscall6(n, a1, a2, a3, a4, 0, 0);
}

INLINE long ks_syscall5(long n, long a1, long a2, long a3, long a4, long a5) {
    return ks_syscall6(n, a1, a2, a3, a4, a5, 0);
}

/* ============================================================================
 * LINUX SYSCALL NUMBERS (x86-64)
 * ========================================================================== */

#ifdef KS_ARCH_X86_64
    #define SYS_read           0
    #define SYS_write          1
    #define SYS_open           2
    #define SYS_close          3
    #define SYS_stat           4
    #define SYS_fstat          5
    #define SYS_lstat          6
    #define SYS_poll           7
    #define SYS_lseek          8
    #define SYS_mmap           9
    #define SYS_mprotect       10
    #define SYS_munmap         11
    #define SYS_brk            12
    #define SYS_rt_sigaction   13
    #define SYS_rt_sigprocmask 14
    #define SYS_rt_sigreturn   15
    #define SYS_ioctl          16
    #define SYS_pread64        17
    #define SYS_pwrite64       18
    #define SYS_readv          19
    #define SYS_writev         20
    #define SYS_access         21
    #define SYS_pipe           22
    #define SYS_select         23
    #define SYS_sched_yield    24
    #define SYS_mremap         25
    #define SYS_msync          26
    #define SYS_mincore        27
    #define SYS_madvise        28
    #define SYS_shmget         29
    #define SYS_shmat          30
    #define SYS_shmctl         31
    #define SYS_dup            32
    #define SYS_dup2           33
    #define SYS_pause          34
    #define SYS_nanosleep      35
    #define SYS_getitimer      36
    #define SYS_alarm          37
    #define SYS_setitimer      38
    #define SYS_getpid         39
    #define SYS_sendfile       40
    #define SYS_socket         41
    #define SYS_connect        42
    #define SYS_accept         43
    #define SYS_sendto         44
    #define SYS_recvfrom       45
    #define SYS_sendmsg        46
    #define SYS_recvmsg        47
    #define SYS_shutdown       48
    #define SYS_bind           49
    #define SYS_listen         50
    #define SYS_getsockname    51
    #define SYS_getpeername    52
    #define SYS_socketpair     53
    #define SYS_setsockopt     54
    #define SYS_getsockopt     55
    #define SYS_clone          56
    #define SYS_fork           57
    #define SYS_vfork          58
    #define SYS_execve         59
    #define SYS_exit           60
    #define SYS_wait4          61
    #define SYS_kill           62
    #define SYS_uname          63
    #define SYS_semget         64
    #define SYS_semop          65
    #define SYS_semctl         66
    #define SYS_shmdt          67
    #define SYS_msgget         68
    #define SYS_msgsnd         69
    #define SYS_msgrcv         70
    #define SYS_msgctl         71
    #define SYS_fcntl          72
    #define SYS_flock          73
    #define SYS_fsync          74
    #define SYS_fdatasync      75
    #define SYS_truncate       76
    #define SYS_ftruncate      77
    #define SYS_getdents       78
    #define SYS_getcwd         79
    #define SYS_chdir          80
    #define SYS_fchdir         81
    #define SYS_rename         82
    #define SYS_mkdir          83
    #define SYS_rmdir          84
    #define SYS_creat          85
    #define SYS_link           86
    #define SYS_unlink         87
    #define SYS_symlink        88
    #define SYS_readlink       89
    #define SYS_chmod          90
    #define SYS_fchmod         91
    #define SYS_chown          92
    #define SYS_fchown         93
    #define SYS_lchown         94
    #define SYS_umask          95
    #define SYS_gettimeofday   96
    #define SYS_getrlimit      97
    #define SYS_getrusage      98
    #define SYS_sysinfo        99
    #define SYS_times          100
    #define SYS_ptrace         101
    #define SYS_getuid         102
    #define SYS_syslog         103
    #define SYS_getgid         104
    #define SYS_setuid         105
    #define SYS_setgid         106
    #define SYS_geteuid        107
    #define SYS_getegid        108
    #define SYS_setpgid        109
    #define SYS_getppid        110
    #define SYS_getpgrp        111
    #define SYS_setsid         112
    #define SYS_setreuid       113
    #define SYS_setregid       114
    #define SYS_getgroups      115
    #define SYS_setgroups      116
    #define SYS_setresuid      117
    #define SYS_getresuid      118
    #define SYS_setresgid      119
    #define SYS_getresgid      120
    #define SYS_getpgid        121
    #define SYS_setfsuid       122
    #define SYS_setfsgid       123
    #define SYS_getsid         124
    #define SYS_capget         125
    #define SYS_capset         126
    #define SYS_rt_sigpending  127
    #define SYS_rt_sigtimedwait 128
    #define SYS_rt_sigqueueinfo 129
    #define SYS_rt_sigsuspend  130
    #define SYS_sigaltstack    131
    #define SYS_utime          132
    #define SYS_mknod          133
    #define SYS_uselib         134
    #define SYS_personality    135
    #define SYS_ustat          136
    #define SYS_statfs         137
    #define SYS_fstatfs        138
    #define SYS_sysfs          139
    #define SYS_getpriority    140
    #define SYS_setpriority    141
    #define SYS_sched_setparam 142
    #define SYS_sched_getparam 143
    #define SYS_sched_setscheduler 144
    #define SYS_sched_getscheduler 145
    #define SYS_sched_yield    146
    #define SYS_sched_get_priority_max 147
    #define SYS_sched_get_priority_min 148
    #define SYS_sched_rr_get_interval 149
    #define SYS_mlock          150
    #define SYS_munlock        151
    #define SYS_mlockall       152
    #define SYS_munlockall     153
    #define SYS_vhangup        154
    #define SYS_modify_ldt     155
    #define SYS_pivot_root     156
    #define SYS__sysctl        157
    #define SYS_prctl          158
    #define SYS_arch_prctl     158
    #define SYS_adjtimex       159
    #define SYS_setrlimit      160
    #define SYS_chroot         161
    #define SYS_sync           162
    #define SYS_acct           163
    #define SYS_settimeofday   164
    #define SYS_mount          165
    #define SYS_umount2        166
    #define SYS_swapon         167
    #define SYS_swapoff        168
    #define SYS_reboot         169
    #define SYS_sethostname    170
    #define SYS_setdomainname  171
    #define SYS_iopl           172
    #define SYS_ioperm         173
    #define SYS_create_module  174
    #define SYS_init_module    175
    #define SYS_delete_module  176
    #define SYS_get_kernel_syms 177
    #define SYS_query_module   178
    #define SYS_quotactl       179
    #define SYS_nfsservctl     180
    #define SYS_getpmsg        181
    #define SYS_putpmsg        182
    #define SYS_afs_syscall    183
    #define SYS_tuxcall        184
    #define SYS_security       185
    #define SYS_gettid         186
    #define SYS_readahead      187
    #define SYS_setxattr       188
    #define SYS_lsetxattr      189
    #define SYS_fsetxattr      190
    #define SYS_getxattr       191
    #define SYS_lgetxattr      192
    #define SYS_fgetxattr      193
    #define SYS_listxattr      194
    #define SYS_llistxattr     195
    #define SYS_flistxattr     196
    #define SYS_removexattr    197
    #define SYS_lremovexattr   198
    #define SYS_fremovexattr   199
    #define SYS_tkill          200
    #define SYS_time           201
    #define SYS_futex          202
    #define SYS_sched_setaffinity 203
    #define SYS_sched_getaffinity 204
    #define SYS_set_thread_area 205
    #define SYS_io_setup        206
    #define SYS_io_destroy      207
    #define SYS_io_getevents    208
    #define SYS_io_submit       209
    #define SYS_io_cancel       210
    #define SYS_get_thread_area 211
    #define SYS_lookup_dcookie  212
    #define SYS_epoll_create    213
    #define SYS_epoll_ctl_old   214
    #define SYS_epoll_wait_old  215
    #define SYS_remap_file_pages 216
    #define SYS_getdents64      217
    #define SYS_set_tid_address 218
    #define SYS_restart_syscall 219
    #define SYS_semtimedop      220
    #define SYS_fadvise64       221
    #define SYS_timer_create    222
    #define SYS_timer_settime   223
    #define SYS_timer_gettime   224
    #define SYS_timer_getoverrun 225
    #define SYS_timer_delete    226
    #define SYS_clock_settime   227
    #define SYS_clock_gettime   228
    #define SYS_clock_getres    229
    #define SYS_clock_nanosleep 230
    #define SYS_exit_group      231
    #define SYS_epoll_wait      232
    #define SYS_epoll_ctl       233
    #define SYS_tgkill          234
    #define SYS_utimes          235
    #define SYS_vserver         236
    #define SYS_mbind           237
    #define SYS_set_mempolicy   238
    #define SYS_get_mempolicy   239
    #define SYS_mq_open         240
    #define SYS_mq_unlink       241
    #define SYS_mq_timedsend    242
    #define SYS_mq_timedreceive 243
    #define SYS_mq_notify       244
    #define SYS_mq_getsetattr   245
    #define SYS_kexec_load      246
    #define SYS_waitid          247
    #define SYS_add_key         248
    #define SYS_request_key     249
    #define SYS_keyctl          250
    #define SYS_ioprio_set      251
    #define SYS_ioprio_get      252
    #define SYS_inotify_init    253
    #define SYS_inotify_add_watch 254
    #define SYS_inotify_rm_watch 255
    #define SYS_migrate_pages   256
    #define SYS_openat          257
    #define SYS_mkdirat         258
    #define SYS_mknodat         259
    #define SYS_fchownat        260
    #define SYS_futimesat       261
    #define SYS_newfstatat      262
    #define SYS_unlinkat        263
    #define SYS_renameat        264
    #define SYS_linkat          265
    #define SYS_symlinkat       266
    #define SYS_readlinkat      267
    #define SYS_fchmodat        268
    #define SYS_faccessat       269
    #define SYS_pselect6        270
    #define SYS_ppoll           271
    #define SYS_unshare         272
    #define SYS_set_robust_list 273
    #define SYS_get_robust_list 274
    #define SYS_splice          275
    #define SYS_tee             276
    #define SYS_sync_file_range 277
    #define SYS_vmsplice        278
    #define SYS_move_pages      279
    #define SYS_utimensat       280
    #define SYS_epoll_pwait     281
    #define SYS_signalfd        282
    #define SYS_timerfd_create  283
    #define SYS_eventfd         284
    #define SYS_fallocate       285
    #define SYS_timerfd_settime 286
    #define SYS_timerfd_gettime 287
    #define SYS_accept4         288
    #define SYS_signalfd4       289
    #define SYS_eventfd2        290
    #define SYS_epoll_create1   291
    #define SYS_dup3            292
    #define SYS_pipe2           293
    #define SYS_inotify_init1   294
    #define SYS_preadv          295
    #define SYS_pwritev         296
    #define SYS_rt_tgsigqueueinfo 297
    #define SYS_perf_event_open 298
    #define SYS_recvmmsg        299
    #define SYS_fanotify_init   300
    #define SYS_fanotify_mark   301
    #define SYS_prlimit64       302
    #define SYS_name_to_handle_at 303
    #define SYS_open_by_handle_at 304
    #define SYS_clock_adjtime   305
    #define SYS_syncfs          306
    #define SYS_sendmmsg        307
    #define SYS_setns           308
    #define SYS_getcpu          309
    #define SYS_process_vm_readv 310
    #define SYS_process_vm_writev 311
    #define SYS_kcmp            312
    #define SYS_finit_module    313
    #define SYS_sched_setattr   314
    #define SYS_sched_getattr   315
    #define SYS_renameat2       316
    #define SYS_seccomp         317
    #define SYS_getrandom       318
    #define SYS_memfd_create    319
    #define SYS_kexec_file_load 320
    #define SYS_bpf             321
    #define SYS_execveat        322
    #define SYS_userfaultfd     323
    #define SYS_membarrier      324
    #define SYS_mlock2          325
    #define SYS_copy_file_range 326
    #define SYS_preadv2         327
    #define SYS_pwritev2        328
    #define SYS_pkey_mprotect   329
    #define SYS_pkey_alloc      330
    #define SYS_pkey_free       331
    #define SYS_statx           332
    #define SYS_io_pgetevents   333
    #define SYS_rseq            334
    #define SYS_pidfd_send_signal 424
    #define SYS_io_uring_setup  425
    #define SYS_io_uring_enter  426
    #define SYS_io_uring_register 427
    #define SYS_open_tree       428
    #define SYS_move_mount      429
    #define SYS_fsopen          430
    #define SYS_fsconfig        431
    #define SYS_fsmount         432
    #define SYS_fspick          433
    #define SYS_pidfd_open      434
    #define SYS_clone3          435
    #define SYS_close_range     436
    #define SYS_openat2         437
    #define SYS_pidfd_getfd     438
    #define SYS_faccessat2      439
    #define SYS_process_madvise 440
    #define SYS_epoll_pwait2    441
    #define SYS_mount_setattr   442
    #define SYS_quotactl_fd     443
    #define SYS_landlock_create_ruleset 444
    #define SYS_landlock_add_rule 445
    #define SYS_landlock_restrict_self 446
    #define SYS_memfd_secret    447
    #define SYS_process_mrelease 448
    #define SYS_futex_waitv     449
    #define SYS_set_mempolicy_home_node 450
#endif

/* ============================================================================
 * HIGH-LEVEL SYSCALL WRAPPERS
 * ========================================================================== */

/* File operations */
INLINE long ks_open(const char* path, int flags, int mode) {
    return ks_syscall3(SYS_open, (long)path, flags, mode);
}

INLINE long ks_close(int fd) {
    return ks_syscall1(SYS_close, fd);
}

INLINE long ks_read(int fd, void* buf, size_t count) {
    return ks_syscall3(SYS_read, fd, (long)buf, count);
}

INLINE long ks_write(int fd, const void* buf, size_t count) {
    return ks_syscall3(SYS_write, fd, (long)buf, count);
}

/* Memory operations */
INLINE void* ks_mmap(void* addr, size_t length, int prot, int flags, int fd, off_t offset) {
    return (void*)ks_syscall6(SYS_mmap, (long)addr, length, prot, flags, fd, offset);
}

INLINE long ks_munmap(void* addr, size_t length) {
    return ks_syscall2(SYS_munmap, (long)addr, length);
}

INLINE long ks_mprotect(void* addr, size_t length, int prot) {
    return ks_syscall3(SYS_mprotect, (long)addr, length, prot);
}

/* Process operations */
INLINE NORETURN void ks_exit(int code) {
    ks_syscall1(SYS_exit, code);
    __builtin_unreachable();
}

INLINE long ks_getpid(void) {
    return ks_syscall0(SYS_getpid);
}

INLINE long ks_gettid(void) {
    return ks_syscall0(SYS_gettid);
}

/* Time operations */
INLINE long ks_clock_gettime(int clk_id, struct timespec* tp) {
    return ks_syscall2(SYS_clock_gettime, clk_id, (long)tp);
}

/* Random numbers */
INLINE long ks_getrandom(void* buf, size_t buflen, unsigned int flags) {
    return ks_syscall3(SYS_getrandom, (long)buf, buflen, flags);
}

/* ============================================================================
 * MEMORY OPERATIONS - OPTIMIZED
 * ========================================================================== */

/* Optimized memcpy for small sizes */
INLINE void* ks_memcpy_small(void* RESTRICT dst, const void* RESTRICT src, size_t n) {
    uint8_t* d = (uint8_t*)dst;
    const uint8_t* s = (const uint8_t*)src;
    
    /* 8-byte aligned fast path */
    if (n >= 8 && ((uintptr_t)d & 7) == 0 && ((uintptr_t)s & 7) == 0) {
        while (n >= 8) {
            *(uint64_t*)d = *(const uint64_t*)s;
            d += 8; s += 8; n -= 8;
        }
    }
    
    /* Remainder */
    while (n--) *d++ = *s++;
    return dst;
}

/* General memcpy - auto-vectorized by compiler */
INLINE void* ks_memcpy(void* RESTRICT dst, const void* RESTRICT src, size_t n) {
    return __builtin_memcpy(dst, src, n);
}

/* Optimized memset */
INLINE void* ks_memset(void* dst, int c, size_t n) {
    return __builtin_memset(dst, c, n);
}

/* Optimized memcmp */
INLINE int ks_memcmp(const void* a, const void* b, size_t n) {
    return __builtin_memcmp(a, b, n);
}

/* Move memory (handles overlap) */
INLINE void* ks_memmove(void* dst, const void* src, size_t n) {
    return __builtin_memmove(dst, src, n);
}

/* ============================================================================
 * STRING OPERATIONS - OPTIMIZED
 * ========================================================================== */

INLINE size_t ks_strlen(const char* s) {
    return __builtin_strlen(s);
}

INLINE char* ks_strcpy(char* RESTRICT dst, const char* RESTRICT src) {
    return __builtin_strcpy(dst, src);
}

INLINE int ks_strcmp(const char* a, const char* b) {
    return __builtin_strcmp(a, b);
}

/* ============================================================================
 * HARDWARE PERFORMANCE COUNTERS
 * ========================================================================== */

#ifdef KS_ARCH_X86_64
    /* Read time-stamp counter */
    INLINE uint64_t ks_rdtsc(void) {
        uint32_t lo, hi;
        __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));
        return ((uint64_t)hi << 32) | lo;
    }
    
    /* Read performance counter */
    INLINE uint64_t ks_rdpmc(uint32_t counter) {
        uint32_t lo, hi;
        __asm__ volatile("rdpmc" : "=a"(lo), "=d"(hi) : "c"(counter));
        return ((uint64_t)hi << 32) | lo;
    }
#elif defined(KS_ARCH_AARCH64)
    /* Read cycle counter on ARM64 */
    INLINE uint64_t ks_rdtsc(void) {
        uint64_t val;
        __asm__ volatile("mrs %0, pmccntr_el0" : "=r"(val));
        return val;
    }
#else
    INLINE uint64_t ks_rdtsc(void) {
        return 0;
    }
#endif

/* ============================================================================
 * CPU FEATURE DETECTION
 * ========================================================================== */

typedef struct {
    union {
        struct {
            uint32_t sse3 : 1;
            uint32_t pclmulqdq : 1;
            uint32_t dtes64 : 1;
            uint32_t monitor : 1;
            uint32_t ds_cpl : 1;
            uint32_t vmx : 1;
            uint32_t smx : 1;
            uint32_t est : 1;
            uint32_t tm2 : 1;
            uint32_t ssse3 : 1;
            uint32_t cnxt_id : 1;
            uint32_t sdbg : 1;
            uint32_t fma : 1;
            uint32_t cx16 : 1;
            uint32_t xtpr : 1;
            uint32_t pdcm : 1;
            uint32_t reserved : 1;
            uint32_t pcid : 1;
            uint32_t dca : 1;
            uint32_t sse4_1 : 1;
            uint32_t sse4_2 : 1;
            uint32_t x2apic : 1;
            uint32_t movbe : 1;
            uint32_t popcnt : 1;
            uint32_t tsc_deadline : 1;
            uint32_t aes : 1;
            uint32_t xsave : 1;
            uint32_t osxsave : 1;
            uint32_t avx : 1;
            uint32_t f16c : 1;
            uint32_t rdrnd : 1;
            uint32_t hypervisor : 1;
        };
        uint32_t raw;
    } ecx;
    
    union {
        struct {
            uint32_t fpu : 1;
            uint32_t vme : 1;
            uint32_t de : 1;
            uint32_t pse : 1;
            uint32_t tsc : 1;
            uint32_t msr : 1;
            uint32_t pae : 1;
            uint32_t mce : 1;
            uint32_t cx8 : 1;
            uint32_t apic : 1;
            uint32_t reserved : 1;
            uint32_t sep : 1;
            uint32_t mtrr : 1;
            uint32_t pge : 1;
            uint32_t mca : 1;
            uint32_t cmov : 1;
            uint32_t pat : 1;
            uint32_t pse36 : 1;
            uint32_t psn : 1;
            uint32_t clfsh : 1;
            uint32_t nx : 1;
            uint32_t ds : 1;
            uint32_t acpi : 1;
            uint32_t mmx : 1;
            uint32_t fxsr : 1;
            uint32_t sse : 1;
            uint32_t sse2 : 1;
            uint32_t ss : 1;
            uint32_t htt : 1;
            uint32_t tm : 1;
            uint32_t ia64 : 1;
            uint32_t pbe : 1;
        };
        uint32_t raw;
    } edx;
    
    uint32_t ebx;
    uint32_t eax;
} KSCPUFeatures;

KSCPUFeatures ks_cpu_features;

void ks_detect_cpu_features(void);

/* ============================================================================
 * CACHE-LINE ALIGNED STRUCTURES
 * ========================================================================== */

typedef struct ALIGNED(64) {
    volatile uint64_t value;
    uint8_t _pad[64 - sizeof(uint64_t)];
} KSCacheLineAligned64;

typedef struct ALIGNED(64) {
    volatile uint32_t lock;
    uint8_t _pad[64 - sizeof(uint32_t)];
} KSSpinlock;

typedef struct ALIGNED(64) {
    uint64_t producer;
    uint64_t consumer;
    uint64_t size;
    uint64_t mask;
    uint8_t* buffer;
    uint8_t _pad[64 - 5 * sizeof(uint64_t)];
} KSCacheLineAlignedQueue;

/* ============================================================================
 * SPINLOCK - SIMPLE BUT FAST
 * ========================================================================== */

INLINE void ks_spinlock_lock(KSSpinlock* lock) {
    while (__sync_lock_test_and_set(&lock->lock, 1)) {
        while (lock->lock) {
            __asm__ volatile("pause" ::: "memory");
        }
    }
}

INLINE int ks_spinlock_trylock(KSSpinlock* lock) {
    return !__sync_lock_test_and_set(&lock->lock, 1);
}

INLINE void ks_spinlock_unlock(KSSpinlock* lock) {
    __sync_lock_release(&lock->lock);
}

/* ============================================================================
 * LOGGING - MINIMAL OVERHEAD
 * ========================================================================== */

INLINE void ks_print_i64(int64_t x) {
    char buf[32];
    int len = 0;
    uint64_t n = (x < 0) ? -x : x;
    
    if (x < 0) buf[len++] = '-';
    
    uint64_t divisor = 1;
    while (divisor <= n / 10) divisor *= 10;
    
    while (divisor > 0) {
        buf[len++] = (char)('0' + (n / divisor));
        n %= divisor;
        divisor /= 10;
    }
    
    ks_write(1, buf, len);
}

INLINE void ks_print_u64(uint64_t n) {
    char buf[32];
    int len = 0;
    uint64_t divisor = 1;
    
    while (divisor <= n / 10) divisor *= 10;
    
    while (divisor > 0) {
        buf[len++] = (char)('0' + (n / divisor));
        n %= divisor;
        divisor /= 10;
    }
    
    ks_write(1, buf, len);
}

INLINE void ks_print_hex(uint64_t n) {
    const char hex[] = "0123456789abcdef";
    char buf[18] = "0x";
    int i = 16;
    
    for (int j = 0; j < 16; j++) {
        buf[2 + j] = hex[(n >> ((15 - j) * 4)) & 0xF];
    }
    
    ks_write(1, buf, 18);
}

INLINE void ks_print_str(const char* s) {
    size_t len = ks_strlen(s);
    ks_write(1, s, len);
}

INLINE void ks_println_str(const char* s) {
    ks_print_str(s);
    ks_write(1, "\n", 1);
}

/* ============================================================================
 * ERROR HANDLING
 * ========================================================================== */

#define KS_OK         0
#define KS_ERROR     -1
#define KS_AGAIN     -2
#define KS_NOMEM     -3
#define KS_INVAL     -4
#define KS_EXIST     -5
#define KS_NOENT     -6
#define KS_BUSY      -7
#define KS_TIMEDOUT  -8
#define KS_CANCELED  -9

typedef int ks_error_t;

/* ============================================================================
 * INITIALIZATION
 * ========================================================================== */

void ks_runtime_init(void);
void ks_runtime_shutdown(void);

#endif /* KS_RUNTIME_H */
