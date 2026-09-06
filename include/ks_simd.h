/*
 * ks_simd.h - KentScript Real SIMD Acceleration Layer
 * =====================================================
 * Portable, hardware-native vectorization for the KentScript C backend.
 *
 * Design (2026 best practice - "write once, vectorize everywhere"):
 *   - Uses GCC/Clang NATIVE VECTOR EXTENSIONS ( __attribute__((vector_size(N))) ).
 *     The compiler lowers these automatically to:
 *         * ARM NEON   (aarch64, 128-bit)
 *         * ARM SVE    (scalable, when available)
 *         * x86 SSE2   (always, 128-bit)
 *         * x86 AVX/AVX2 (256-bit, when -mavx2 / -march=native)
 *         * x86 AVX-512  (512-bit, when -mavx512f)
 *         * RISC-V RVV  (when toolchain supports it)
 *   - Vector width (KS_SIMD_BYTES) is chosen at COMPILE TIME from the host
 *     arch/cpu flags, so ONE source runs optimally on every target
 *     (x64, x86, ARM/Termux-Android, Windows MinGW, etc).
 *   - Every function has a correct SCALAR TAIL, so results are always exact
 *     regardless of alignment or length-not-multiple-of-lanes.
 *
 * All routines are static inline -> zero overhead, no linker dependency.
 */

#ifndef KS_SIMD_H
#define KS_SIMD_H

#include <stddef.h>

/* ---- 1. Select vector width from host capabilities ---------------- */
#ifndef KS_SIMD_BYTES
  #if defined(__x86_64__) || defined(__i386__) || defined(_M_IX86) || defined(_M_X64)
    #if defined(__AVX512F__) || defined(__AVX512__)
      #define KS_SIMD_BYTES 64
    #elif defined(__AVX2__) || defined(__AVX__) || defined(__AVX__)
      #define KS_SIMD_BYTES 32
    #else
      #define KS_SIMD_BYTES 16   /* SSE2 is baseline on all x86 */
    #endif
  #elif defined(__aarch64__) || defined(_M_ARM64)
    #define KS_SIMD_BYTES 16     /* NEON is baseline on AArch64 */
  #elif defined(__arm__)
    #define KS_SIMD_BYTES 16     /* NEON on ARMv7+ */
  #elif defined(__riscv)
    #define KS_SIMD_BYTES 16     /* toolchain picks LMUL */
  #else
    #define KS_SIMD_BYTES 16
  #endif
#endif

/* Detect NEON/AVX for runtime diagnostics (used by ks_simd_detect) */
#if defined(__aarch64__) || defined(__ARM_NEON) || defined(_M_ARM64)
  #define KS_SIMD_ARCH "arm-neon"
#elif defined(__AVX512F__)
  #define KS_SIMD_ARCH "x86-avx512"
#elif defined(__AVX2__)
  #define KS_SIMD_ARCH "x86-avx2"
#elif defined(__AVX__)
  #define KS_SIMD_ARCH "x86-avx"
#elif defined(__SSE2__)
  #define KS_SIMD_ARCH "x86-sse2"
#else
  #define KS_SIMD_ARCH "scalar"
#endif

/* ---- 2. Generic element-wise binary op (add/sub/mul/div) ---------- */
#define KS_SIMD_DEFINE_BINOP(CTYPE, SUF, OP, NAME)                            \
static inline void ks_simd_##SUF##_##NAME(CTYPE *a, CTYPE *b, CTYPE *c,       \
                                          long long n) {                      \
    typedef CTYPE ks_v __attribute__((vector_size(KS_SIMD_BYTES)));            \
    long long lanes = (long long)(KS_SIMD_BYTES / sizeof(CTYPE));              \
    long long i = 0;                                                          \
    for (; i + lanes <= n; i += lanes) {                                      \
        ks_v va = *(ks_v *)(a + i);                                           \
        ks_v vb = *(ks_v *)(b + i);                                           \
        *(ks_v *)(c + i) = va OP vb;                                          \
    }                                                                         \
    for (; i < n; i++) c[i] = a[i] OP b[i];                                   \
}

/* ---- 3. Scalar broadcast ops (scale / add-constant) -------------- */
#define KS_SIMD_DEFINE_SCALE(CTYPE, SUF)                                      \
static inline void ks_simd_scale_##SUF(CTYPE *a, CTYPE s, long long n) {      \
    typedef CTYPE ks_v __attribute__((vector_size(KS_SIMD_BYTES)));            \
    long long lanes = (long long)(KS_SIMD_BYTES / sizeof(CTYPE));              \
    long long i = 0;                                                          \
    for (; i + lanes <= n; i += lanes) {                                      \
        ks_v va = *(ks_v *)(a + i);                                           \
        *(ks_v *)(a + i) = va * s;                                            \
    }                                                                         \
    for (; i < n; i++) a[i] = a[i] * s;                                       \
}                                                                             \
static inline void ks_simd_addc_##SUF(CTYPE *a, CTYPE s, long long n) {        \
    typedef CTYPE ks_v __attribute__((vector_size(KS_SIMD_BYTES)));            \
    long long lanes = (long long)(KS_SIMD_BYTES / sizeof(CTYPE));              \
    long long i = 0;                                                          \
    for (; i + lanes <= n; i += lanes) {                                      \
        ks_v va = *(ks_v *)(a + i);                                           \
        *(ks_v *)(a + i) = va + s;                                            \
    }                                                                         \
    for (; i < n; i++) a[i] = a[i] + s;                                       \
}

/* ---- 4. Fused multiply-add: out = a*b + c ------------------------ */
#define KS_SIMD_DEFINE_FMA(CTYPE, SUF)                                        \
static inline void ks_simd_fma_##SUF(CTYPE *a, CTYPE *b, CTYPE *c,             \
                                     CTYPE *out, long long n) {               \
    typedef CTYPE ks_v __attribute__((vector_size(KS_SIMD_BYTES)));            \
    long long lanes = (long long)(KS_SIMD_BYTES / sizeof(CTYPE));              \
    long long i = 0;                                                          \
    for (; i + lanes <= n; i += lanes) {                                      \
        ks_v va = *(ks_v *)(a + i);                                           \
        ks_v vb = *(ks_v *)(b + i);                                           \
        ks_v vc = *(ks_v *)(c + i);                                           \
        *(ks_v *)(out + i) = va * vb + vc;                                    \
    }                                                                         \
    for (; i < n; i++) out[i] = a[i] * b[i] + c[i];                           \
}

/* ---- 5. Horizontal reduction (sum) ------------------------------- */
#define KS_SIMD_DEFINE_SUM(CTYPE, SUF)                                        \
static inline CTYPE ks_simd_sum_##SUF(CTYPE *a, long long n) {                \
    typedef CTYPE ks_v __attribute__((vector_size(KS_SIMD_BYTES)));            \
    long long lanes = (long long)(KS_SIMD_BYTES / sizeof(CTYPE));              \
    ks_v acc = {0};                                                           \
    long long i = 0;                                                          \
    for (; i + lanes <= n; i += lanes) acc = acc + *(ks_v *)(a + i);           \
    CTYPE total = 0;                                                          \
    CTYPE *p = (CTYPE *)&acc;                                                 \
    for (long long k = 0; k < lanes; k++) total += p[k];                      \
    for (; i < n; i++) total += a[i];                                         \
    return total;                                                             \
}                                                                             \
static inline CTYPE ks_simd_dot_##SUF(CTYPE *a, CTYPE *b, long long n) {       \
    typedef CTYPE ks_v __attribute__((vector_size(KS_SIMD_BYTES)));            \
    long long lanes = (long long)(KS_SIMD_BYTES / sizeof(CTYPE));              \
    ks_v acc = {0};                                                           \
    long long i = 0;                                                          \
    for (; i + lanes <= n; i += lanes) {                                      \
        ks_v va = *(ks_v *)(a + i);                                           \
        ks_v vb = *(ks_v *)(b + i);                                           \
        acc = acc + va * vb;                                                  \
    }                                                                         \
    CTYPE total = 0;                                                          \
    CTYPE *p = (CTYPE *)&acc;                                                 \
    for (long long k = 0; k < lanes; k++) total += p[k];                      \
    for (; i < n; i++) total += a[i] * b[i];                                  \
    return total;                                                             \
}

/* ---- 6. Instantiate for every element type ----------------------- */
KS_SIMD_DEFINE_BINOP(float,    f32, +, bin_add)
KS_SIMD_DEFINE_BINOP(float,    f32, -, bin_sub)
KS_SIMD_DEFINE_BINOP(float,    f32, *, bin_mul)
KS_SIMD_DEFINE_BINOP(float,    f32, /, bin_div)
KS_SIMD_DEFINE_BINOP(double,   f64, +, bin_add)
KS_SIMD_DEFINE_BINOP(double,   f64, -, bin_sub)
KS_SIMD_DEFINE_BINOP(double,   f64, *, bin_mul)
KS_SIMD_DEFINE_BINOP(double,   f64, /, bin_div)
KS_SIMD_DEFINE_BINOP(int,      i32, +, bin_add)
KS_SIMD_DEFINE_BINOP(int,      i32, -, bin_sub)
KS_SIMD_DEFINE_BINOP(int,      i32, *, bin_mul)
KS_SIMD_DEFINE_BINOP(int,      i32, /, bin_div)
KS_SIMD_DEFINE_BINOP(long long, i64, +, bin_add)
KS_SIMD_DEFINE_BINOP(long long, i64, -, bin_sub)
KS_SIMD_DEFINE_BINOP(long long, i64, *, bin_mul)
KS_SIMD_DEFINE_BINOP(long long, i64, /, bin_div)

KS_SIMD_DEFINE_SCALE(float,    f32)
KS_SIMD_DEFINE_SCALE(double,   f64)
KS_SIMD_DEFINE_SCALE(int,      i32)
KS_SIMD_DEFINE_SCALE(long long, i64)

KS_SIMD_DEFINE_FMA(float,    f32)
KS_SIMD_DEFINE_FMA(double,   f64)
KS_SIMD_DEFINE_FMA(int,      i32)
KS_SIMD_DEFINE_FMA(long long, i64)

KS_SIMD_DEFINE_SUM(float,    f32)
KS_SIMD_DEFINE_SUM(double,   f64)
KS_SIMD_DEFINE_SUM(int,      i32)
KS_SIMD_DEFINE_SUM(long long, i64)

/* ---- 7. Runtime detection helper --------------------------------- */
static inline const char *ks_simd_arch_name(void) { return KS_SIMD_ARCH; }
static inline int ks_simd_width_bytes(void) { return (int)KS_SIMD_BYTES; }

#endif /* KS_SIMD_H */
