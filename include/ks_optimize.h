/* ============================================================================
 * ks_optimize.h - Compiler Optimization Hints & Attributes
 * Include this for MAXIMUM SPEED
 * ========================================================================== */

#ifndef KS_OPTIMIZE_H
#define KS_OPTIMIZE_H

#include "ks_platform.h"

/* Force inlining */
#if defined(KS_COMPILER_CLANG) || defined(KS_COMPILER_GCC)
    #define KS_ALWAYS_INLINE __attribute__((always_inline)) inline
    #define KS_NEVER_INLINE  __attribute__((noinline))
    #define KS_HOT           __attribute__((hot))
    #define KS_COLD          __attribute__((cold))
#elif defined(KS_COMPILER_MSVC)
    #define KS_ALWAYS_INLINE __forceinline
    #define KS_NEVER_INLINE  __declspec(noinline)
    #define KS_HOT
    #define KS_COLD
#else
    #define KS_ALWAYS_INLINE inline
    #define KS_NEVER_INLINE
    #define KS_HOT
    #define KS_COLD
#endif

/* Branch prediction */
#if defined(KS_COMPILER_CLANG) || defined(KS_COMPILER_GCC)
    #define KS_LIKELY(x)   __builtin_expect(!!(x), 1)
    #define KS_UNLIKELY(x) __builtin_expect(!!(x), 0)
#else
    #define KS_LIKELY(x)   (x)
    #define KS_UNLIKELY(x) (x)
#endif

/* Restrict pointers */
#if defined(KS_COMPILER_CLANG) || defined(KS_COMPILER_GCC)
    #define KS_RESTRICT __restrict__
#elif defined(KS_COMPILER_MSVC)
    #define KS_RESTRICT __restrict
#else
    #define KS_RESTRICT
#endif

/* Alignment macros */
#define KS_CACHE_LINE_ALIGNED __attribute__((aligned(KS_CACHE_LINE)))
#define KS_PAGE_ALIGNED       __attribute__((aligned(KS_PAGE_SIZE)))
#define KS_ALIGNED(n)         __attribute__((aligned(n)))

#if defined(KS_ARCH_X86_64)
    #define KS_SIMD_ALIGNED        __attribute__((aligned(32)))   /* AVX */
    #define KS_SIMD_ALIGNED_AVX512 __attribute__((aligned(64)))
#elif defined(KS_ARCH_ARM64)
    #define KS_SIMD_ALIGNED __attribute__((aligned(16)))           /* NEON */
#else
    #define KS_SIMD_ALIGNED __attribute__((aligned(16)))
#endif

/* Prefetch */
#if defined(KS_COMPILER_CLANG) || defined(KS_COMPILER_GCC)
    #define KS_PREFETCH(addr)       __builtin_prefetch(addr, 0, 3)
    #define KS_PREFETCH_WRITE(addr) __builtin_prefetch(addr, 1, 3)
#else
    #define KS_PREFETCH(addr)       ((void)0)
    #define KS_PREFETCH_WRITE(addr) ((void)0)
#endif

/* Loop unrolling pragma */
#if defined(KS_COMPILER_CLANG) || defined(KS_COMPILER_GCC)
    #define KS_PRAGMA(x) _Pragma(#x)
    #define KS_UNROLL(n) KS_PRAGMA(GCC unroll n)
#elif defined(KS_COMPILER_MSVC)
    #define KS_UNROLL(n) __pragma(loop(unroll, n))
#else
    #define KS_UNROLL(n)
#endif

/* SIMD vector size */
#ifdef KS_ARCH_X86_64
    #if defined(__AVX512F__)
        #define KS_VECTOR_SIZE 64
        #define KS_VECTOR_TYPE __m512i
    #elif defined(__AVX2__)
        #define KS_VECTOR_SIZE 32
        #define KS_VECTOR_TYPE __m256i
    #elif defined(__SSE4_2__)
        #define KS_VECTOR_SIZE 16
        #define KS_VECTOR_TYPE __m128i
    #endif
#elif defined(KS_ARCH_ARM64)
    #define KS_VECTOR_SIZE 16
    #define KS_VECTOR_TYPE int64x2_t
#endif

#ifndef KS_VECTOR_SIZE
    #define KS_VECTOR_SIZE 1
    #define KS_VECTOR_TYPE uint64_t
#endif

/* Function attributes */
#if defined(KS_COMPILER_CLANG) || defined(KS_COMPILER_GCC)
    #define KS_PURE        __attribute__((pure))
    #define KS_CONST       __attribute__((const))
    #define KS_NOTHROW     __attribute__((nothrow))
    #define KS_NORETURN    __attribute__((noreturn))
    #define KS_MALLOC_ATTR __attribute__((malloc))
    #define KS_WARN_UNUSED __attribute__((warn_unused_result))
#else
    #define KS_PURE
    #define KS_CONST
    #define KS_NOTHROW
    #define KS_NORETURN
    #define KS_MALLOC_ATTR
    #define KS_WARN_UNUSED
#endif

#endif /* KS_OPTIMIZE_H */
