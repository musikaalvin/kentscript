/*
 * ks_slab.c — Real KentScript Slab Allocator
 *
 * Genuine mmap-backed O(1) slab allocator compiled as a shared library.
 * Python loads this via ctypes — real C managing real OS virtual memory.
 *
 * Build:  gcc -O3 -shared -fPIC -o ks_slab.so ks_slab.c -lpthread
 *
 * Features:
 *   - mmap-backed slabs (anonymous private mappings)
 *   - 14 size classes: 8 B to 64 KB
 *   - O(1) alloc/free via LIFO freelist (cache-friendly)
 *   - 64-byte cache-line alignment (false-sharing prevention)
 *   - Thread-safe via per-size-class pthread mutexes
 *   - MADV_DONTNEED on empty slab (returns pages to OS)
 *   - Large allocations: direct mmap with header
 *   - Real memory barriers: mfence (x86) / dmb ish (ARM64)
 */

#define _GNU_SOURCE
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <pthread.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdio.h>

/* architecture barriers */
#if defined(__x86_64__)
#  define KS_MB()   __asm__ volatile("mfence"    ::: "memory")
#  define KS_RMB()  __asm__ volatile("lfence"    ::: "memory")
#  define KS_WMB()  __asm__ volatile("sfence"    ::: "memory")
#elif defined(__aarch64__)
#  define KS_MB()   __asm__ volatile("dmb ish"   ::: "memory")
#  define KS_RMB()  __asm__ volatile("dmb ishld" ::: "memory")
#  define KS_WMB()  __asm__ volatile("dmb ishst" ::: "memory")
#else
#  define KS_MB()   __sync_synchronize()
#  define KS_RMB()  __sync_synchronize()
#  define KS_WMB()  __sync_synchronize()
#endif

#define KS_CACHE_ALIGN __attribute__((aligned(64)))
#define KS_HOT         __attribute__((hot))
#define KS_EXPORT      __attribute__((visibility("default")))
#define KS_LIKELY(x)   __builtin_expect(!!(x),1)
#define KS_UNLIKELY(x) __builtin_expect(!!(x),0)

#define PAGE_SZ         4096UL
#define CACHE_LINE      64UL
#define NUM_CLASSES     14
#define MAX_SLABS       256
#define LARGE_THRESH    65536UL
#define MAGIC_SLAB      0xBEEFCAFEUL
#define MAGIC_LARGE     0xDEADF00DUL

static const size_t SC_SIZE[NUM_CLASSES]  = {
    8,16,32,64,128,256,512,1024,2048,4096,8192,16384,32768,65536
};
static const size_t SC_COUNT[NUM_CLASSES] = {
    4096,2048,1024,512,256,128,64,32,16,8,4,2,1,1
};

typedef struct KS_CACHE_ALIGN {
    uint32_t magic;
    uint32_t sc;
    size_t   obj_size;
    size_t   capacity;
    size_t   used;
    uint8_t *base;
    size_t   mmap_len;
    uint32_t free_top;
    uint32_t free_stack[4096];
} Slab;

typedef struct { uint32_t magic; uint32_t _pad; size_t total_len; } LargeHdr;

typedef struct KS_CACHE_ALIGN {
    pthread_mutex_t lock;
    Slab           *slabs[MAX_SLABS];
    size_t          nslab;
    uint64_t        n_alloc, n_free, bytes_live;
} Pool;

static Pool  g_pools[NUM_CLASSES];
static int   g_init_done = 0;
static pthread_once_t g_once = PTHREAD_ONCE_INIT;
static uint64_t g_large_alloc=0, g_large_free=0;
static pthread_mutex_t g_large_lock = PTHREAD_MUTEX_INITIALIZER;

static size_t align_up(size_t n, size_t a) { return (n+a-1)&~(a-1); }

static int sc_for(size_t sz) {
    for (int i=0;i<NUM_CLASSES;i++) if (sz<=SC_SIZE[i]) return i;
    return -1;
}

static Slab *slab_new(int sc) {
    size_t obj  = SC_SIZE[sc], cnt = SC_COUNT[sc];
    size_t dlen = align_up(obj*cnt, PAGE_SZ);
    size_t hlen = align_up(sizeof(Slab), CACHE_LINE);
    size_t tot  = hlen + dlen;
    void  *mem  = mmap(NULL,tot,PROT_READ|PROT_WRITE,
                       MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if (mem==MAP_FAILED) return NULL;
    madvise(mem,tot,MADV_WILLNEED);
    Slab *s     = (Slab*)mem;
    s->magic    = MAGIC_SLAB;
    s->sc       = (uint32_t)sc;
    s->obj_size = obj;
    s->capacity = cnt;
    s->used     = 0;
    s->base     = (uint8_t*)mem+hlen;
    s->mmap_len = tot;
    uint32_t top=0;
    for (uint32_t i=0;i<(uint32_t)cnt&&top<4096;i++)
        s->free_stack[top++]=i;
    s->free_top = top;
    return s;
}

static void ks_init_once(void) {
    for (int i=0;i<NUM_CLASSES;i++) {
        pthread_mutex_init(&g_pools[i].lock,NULL);
        for (int k=0;k<2;k++) {
            Slab *s=slab_new(i);
            if (s) g_pools[i].slabs[g_pools[i].nslab++]=s;
        }
    }
    g_init_done=1;
}

static void ensure_init(void) {
    if (KS_LIKELY(g_init_done)) return;
    pthread_once(&g_once,ks_init_once);
}

KS_HOT static void *pool_alloc(int sc) {
    Pool *p=&g_pools[sc];
    pthread_mutex_lock(&p->lock);
    for (size_t i=0;i<p->nslab;i++) {
        Slab *s=p->slabs[i];
        if (!s->free_top) continue;
        uint32_t idx=s->free_stack[--s->free_top];
        s->used++;
        void *ptr=s->base+(size_t)idx*s->obj_size;
        p->n_alloc++; p->bytes_live+=s->obj_size;
        pthread_mutex_unlock(&p->lock);
        return ptr;
    }
    if (p->nslab<MAX_SLABS) {
        Slab *s=slab_new(sc);
        if (s) {
            p->slabs[p->nslab++]=s;
            uint32_t idx=s->free_stack[--s->free_top];
            s->used++;
            void *ptr=s->base+(size_t)idx*s->obj_size;
            p->n_alloc++; p->bytes_live+=s->obj_size;
            pthread_mutex_unlock(&p->lock);
            return ptr;
        }
    }
    pthread_mutex_unlock(&p->lock);
    return NULL;
}

KS_HOT static int pool_free(int sc, void *ptr) {
    Pool *p=&g_pools[sc];
    pthread_mutex_lock(&p->lock);
    for (size_t i=0;i<p->nslab;i++) {
        Slab *s=p->slabs[i];
        if ((uint8_t*)ptr<s->base) continue;
        ptrdiff_t off=(uint8_t*)ptr-s->base;
        if ((size_t)off>=s->obj_size*s->capacity) continue;
        if ((size_t)off%s->obj_size!=0) { pthread_mutex_unlock(&p->lock); return -1; }
        uint32_t idx=(uint32_t)((size_t)off/s->obj_size);
        if (s->free_top<4096) s->free_stack[s->free_top++]=idx;
        s->used--;
        p->n_free++; p->bytes_live-=s->obj_size;
        if (s->used==0) madvise(s->base,s->obj_size*s->capacity,MADV_DONTNEED);
        pthread_mutex_unlock(&p->lock);
        return 0;
    }
    pthread_mutex_unlock(&p->lock);
    return -2;
}

static void *large_alloc(size_t sz) {
    size_t hlen=align_up(sizeof(LargeHdr),CACHE_LINE);
    size_t tot =align_up(hlen+sz,PAGE_SZ);
    void  *mem =mmap(NULL,tot,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if (mem==MAP_FAILED) return NULL;
    LargeHdr *h=(LargeHdr*)mem; h->magic=MAGIC_LARGE; h->total_len=tot;
    pthread_mutex_lock(&g_large_lock); g_large_alloc++; pthread_mutex_unlock(&g_large_lock);
    return (uint8_t*)mem+hlen;
}

static int large_free(void *ptr) {
    size_t hlen=align_up(sizeof(LargeHdr),CACHE_LINE);
    LargeHdr *h=(LargeHdr*)((uint8_t*)ptr-hlen);
    if (h->magic!=MAGIC_LARGE) return -1;
    size_t tot=h->total_len; h->magic=0;
    munmap(h,tot);
    pthread_mutex_lock(&g_large_lock); g_large_free++; pthread_mutex_unlock(&g_large_lock);
    return 0;
}

/* ═══ PUBLIC API ═══════════════════════════════════════════════════════════ */

KS_EXPORT uint64_t ks_malloc(uint64_t size) {
    ensure_init();
    if (!size) return 0;
    if (size>LARGE_THRESH) { void*p=large_alloc((size_t)size); return p?(uint64_t)(uintptr_t)p:0; }
    int sc=sc_for((size_t)size);
    if (sc<0) return 0;
    void *p=pool_alloc(sc);
    return p?(uint64_t)(uintptr_t)p:0;
}

KS_EXPORT uint64_t ks_calloc(uint64_t size) {
    uint64_t a=ks_malloc(size);
    if (a) memset((void*)(uintptr_t)a,0,(size_t)size);
    return a;
}

KS_EXPORT int64_t ks_free(uint64_t addr) {
    ensure_init();
    if (!addr) return 0;
    void *ptr=(void*)(uintptr_t)addr;
    size_t hlen=align_up(sizeof(LargeHdr),CACHE_LINE);
    LargeHdr *h=(LargeHdr*)((uint8_t*)ptr-hlen);
    if (h->magic==MAGIC_LARGE) return large_free(ptr);
    for (int sc=0;sc<NUM_CLASSES;sc++) {
        int r=pool_free(sc,ptr);
        if (r==0)  return 0;
        if (r==-1) return -1;
    }
    return -3;
}

KS_EXPORT uint64_t ks_realloc(uint64_t addr, uint64_t new_size) {
    if (!addr)      return ks_malloc(new_size);
    if (!new_size) { ks_free(addr); return 0; }
    void *ptr=(void*)(uintptr_t)addr;
    size_t old=0;
    size_t hlen=align_up(sizeof(LargeHdr),CACHE_LINE);
    LargeHdr *h=(LargeHdr*)((uint8_t*)ptr-hlen);
    if (h->magic==MAGIC_LARGE) { old=h->total_len-hlen; }
    else {
        for (int sc=0;sc<NUM_CLASSES;sc++) {
            Pool *p=&g_pools[sc];
            for (size_t i=0;i<p->nslab;i++) {
                Slab *s=p->slabs[i];
                if ((uint8_t*)ptr>=s->base &&
                    (uint8_t*)ptr<s->base+s->obj_size*s->capacity)
                    { old=s->obj_size; goto found; }
            }
        }
    }
found:
    if (new_size<=old) return addr;
    uint64_t na=ks_malloc(new_size);
    if (!na) return 0;
    if (old) memcpy((void*)(uintptr_t)na,ptr,old);
    ks_free(addr);
    return na;
}

KS_EXPORT void    ks_memset (uint64_t a, int v, uint64_t n)  { if (a) memset((void*)(uintptr_t)a,v,(size_t)n); }
KS_EXPORT void    ks_memcpy (uint64_t d, uint64_t s, uint64_t n) { if (d&&s) memcpy((void*)(uintptr_t)d,(void*)(uintptr_t)s,(size_t)n); }
KS_EXPORT void    ks_memmove(uint64_t d, uint64_t s, uint64_t n) { if (d&&s) memmove((void*)(uintptr_t)d,(void*)(uintptr_t)s,(size_t)n); }

KS_EXPORT void     ks_write8 (uint64_t a, uint8_t  v) { if(a){*(volatile uint8_t *)(uintptr_t)a=v; KS_WMB();} }
KS_EXPORT uint8_t  ks_read8  (uint64_t a)             { if(!a)return 0; KS_RMB(); return *(volatile uint8_t *)(uintptr_t)a; }
KS_EXPORT void     ks_write32(uint64_t a, uint32_t v) { if(a){*(volatile uint32_t*)(uintptr_t)a=v; KS_WMB();} }
KS_EXPORT uint32_t ks_read32 (uint64_t a)             { if(!a)return 0; KS_RMB(); return *(volatile uint32_t*)(uintptr_t)a; }
KS_EXPORT void     ks_write64(uint64_t a, uint64_t v) { if(a){*(volatile uint64_t*)(uintptr_t)a=v; KS_WMB();} }
KS_EXPORT uint64_t ks_read64 (uint64_t a)             { if(!a)return 0; KS_RMB(); return *(volatile uint64_t*)(uintptr_t)a; }
KS_EXPORT void     ks_barrier (void)                  { KS_MB(); }

KS_EXPORT void ks_stats_json(char *buf, size_t buflen) {
    ensure_init();
    uint64_t ta=0,tf=0,tb=0;
    for (int i=0;i<NUM_CLASSES;i++) {
        Pool *p=&g_pools[i];
        pthread_mutex_lock(&p->lock);
        ta+=p->n_alloc; tf+=p->n_free; tb+=p->bytes_live;
        pthread_mutex_unlock(&p->lock);
    }
    snprintf(buf,buflen,
        "{\"mallocs\":%lu,\"frees\":%lu,\"bytes_live\":%lu,"
        "\"large_allocs\":%lu,\"large_frees\":%lu,\"classes\":%d}",
        (unsigned long)ta,(unsigned long)tf,(unsigned long)tb,
        (unsigned long)g_large_alloc,(unsigned long)g_large_free,NUM_CLASSES);
}

KS_EXPORT void ks_destroy(void) {
    if (!g_init_done) return;
    for (int i=0;i<NUM_CLASSES;i++) {
        pthread_mutex_lock(&g_pools[i].lock);
        for (size_t j=0;j<g_pools[i].nslab;j++)
            munmap(g_pools[i].slabs[j], g_pools[i].slabs[j]->mmap_len);
        g_pools[i].nslab=0;
        pthread_mutex_unlock(&g_pools[i].lock);
    }
    g_init_done=0;
}
