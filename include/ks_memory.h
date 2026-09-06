/* ============================================================================
 * ks_memory.h - Ultra-Fast Memory Operations
 * SIMD + cache-optimized memcpy / memset / memcmp
 * ========================================================================== */

#ifndef KS_MEMORY_H
#define KS_MEMORY_H

#include "ks_platform.h"
#include "ks_optimize.h"

KS_ALWAYS_INLINE static void *ks_memcpy_small(void *KS_RESTRICT dst, const void *KS_RESTRICT src, size_t n) {
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    switch (n) {
        case 0: return dst;
        case 1: *d = *s; return dst;
        case 2: *(uint16_t*)d = *(uint16_t*)s; return dst;
        case 4: *(uint32_t*)d = *(uint32_t*)s; return dst;
        case 8: *(uint64_t*)d = *(uint64_t*)s; return dst;
        default: {
            size_t words = n >> 3, i;
            for (i = 0; i < words; i++) ((uint64_t*)d)[i] = ((uint64_t*)s)[i];
            size_t rem = n & 7;
            d += i * 8; s += i * 8;
            for (i = 0; i < rem; i++) d[i] = s[i];
            return dst;
        }
    }
}

KS_ALWAYS_INLINE static void *ks_memcpy_fast(void *KS_RESTRICT dst, const void *KS_RESTRICT src, size_t n) {
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    if (KS_UNLIKELY(n < 256)) return ks_memcpy_small(dst, src, n);
    while (((uintptr_t)d & (KS_VECTOR_SIZE - 1)) && n >= 8) {
        *(uint64_t*)d = *(uint64_t*)s; d += 8; s += 8; n -= 8;
    }
#if KS_VECTOR_SIZE >= 16
    size_t vectors = n / KS_VECTOR_SIZE;
    for (size_t i = 0; i < vectors; i++) {
        *(KS_VECTOR_TYPE *)d = *(const KS_VECTOR_TYPE *)s;
        d += KS_VECTOR_SIZE; s += KS_VECTOR_SIZE;
    }
    n -= vectors * KS_VECTOR_SIZE;
#endif
    while (n >= 8) { *(uint64_t*)d = *(uint64_t*)s; d += 8; s += 8; n -= 8; }
    while (n--) *d++ = *s++;
    return dst;
}

KS_ALWAYS_INLINE static void *ks_memset_fast(void *dst, int c, size_t n) {
    uint8_t *d = (uint8_t *)dst;
    uint64_t v = (uint8_t)c;
    v |= v << 8; v |= v << 16; v |= v << 32;
    while (((uintptr_t)d & 7) && n) { *d++ = (uint8_t)c; n--; }
    size_t words = n >> 3;
    for (size_t i = 0; i < words; i++) ((uint64_t*)d)[i] = v;
    d += words * 8; n -= words * 8;
    while (n--) *d++ = (uint8_t)c;
    return dst;
}

KS_ALWAYS_INLINE static int ks_memcmp_fast(const void *a, const void *b, size_t n) {
    const uint8_t *pa = (const uint8_t *)a;
    const uint8_t *pb = (const uint8_t *)b;
    size_t words = n >> 3;
    for (size_t i = 0; i < words; i++) {
        uint64_t wa = ((const uint64_t*)pa)[i];
        uint64_t wb = ((const uint64_t*)pb)[i];
        if (wa != wb) {
            for (size_t j = 0; j < 8; j++)
                if (((uint8_t*)&wa)[j] != ((uint8_t*)&wb)[j])
                    return ((uint8_t*)&wa)[j] < ((uint8_t*)&wb)[j] ? -1 : 1;
        }
    }
    pa += words * 8; pb += words * 8; n -= words * 8;
    while (n--) { if (*pa != *pb) return *pa < *pb ? -1 : 1; pa++; pb++; }
    return 0;
}

#endif /* KS_MEMORY_H */
