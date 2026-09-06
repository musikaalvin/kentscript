#ifndef KS_LEGACY_SIMD_H
#define KS_LEGACY_SIMD_H

/* Legacy SIMD/NEON acceleration builtins (system_simd_* / system_neon_*).
 *
 * These mirror the interpreter's NumPy-backed implementations so that code
 * written against the legacy API compiles to real hardware vectorization.
 *
 * Element representation: a KentScript float list stores each value's IEEE-754
 * bits inside a `ks_val_t` slot (see c_transpiler.py float-list handling). We
 * therefore bit-cast to/from `double` for the f32/f64 variants. Integer
 * variants operate directly on the stored `long long` values (in .as.i).
 */

#include <stdlib.h>
#include <math.h>

#ifndef KS_ARRAY_DEFINED
typedef struct { ks_val_t* data; long long length; long long cap; } ks_array;
#define KS_ARRAY_DEFINED
#endif

static inline double _ksl_ld(long long v) {
    union { double d; long long l; } u;
    u.l = v;
    return u.d;
}
static inline long long _ksl_dl(double v) {
    union { double d; long long l; } u;
    u.d = v;
    return u.l;
}

/* Convert a ks_array whose slots hold raw integers into a ks_array whose slots
 * hold the IEEE-754 bits of those integers as doubles. Used when an integer
 * list is passed to a float SIMD op, so the bit-casting builtins (above)
 * produce the same numeric result as the interpreter (which does int->float). */
static inline ks_array ks_fbits_from_i64(ks_array a) {
    long long n = a.length;
    ks_val_t* o = (ks_val_t*)malloc((size_t)n * sizeof(ks_val_t));
    for (long long i = 0; i < n; i++) o[i].as.i = _ksl_dl((double)a.data[i].as.i);
    return (ks_array){o, n};
}

/* ---- float32/float64 binary ops (bit-cast through double) ---- */
#define KS_LEGACY_BINOP_F(FNAME, EXPR)                                          \
    static inline ks_array FNAME(ks_array a, ks_array b) {                      \
        long long n = a.length;                                                 \
        ks_val_t* o = (ks_val_t*)malloc((size_t)n * sizeof(ks_val_t));         \
        for (long long i = 0; i < n; i++)                                       \
            o[i].as.i = _ksl_dl((EXPR));                                        \
        return (ks_array){o, n};                                                \
    }

KS_LEGACY_BINOP_F(system_simd_add_f32, _ksl_ld(a.data[i].as.i) + _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_simd_sub_f32, _ksl_ld(a.data[i].as.i) - _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_simd_mul_f32, _ksl_ld(a.data[i].as.i) * _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_simd_div_f32, _ksl_ld(a.data[i].as.i) / _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_simd_max_f32,
    (_ksl_ld(a.data[i].as.i) > _ksl_ld(b.data[i].as.i) ? _ksl_ld(a.data[i].as.i) : _ksl_ld(b.data[i].as.i)))
KS_LEGACY_BINOP_F(system_simd_min_f32,
    (_ksl_ld(a.data[i].as.i) < _ksl_ld(b.data[i].as.i) ? _ksl_ld(a.data[i].as.i) : _ksl_ld(b.data[i].as.i)))

KS_LEGACY_BINOP_F(system_simd256_add_f32, _ksl_ld(a.data[i].as.i) + _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_simd256_add_f64, _ksl_ld(a.data[i].as.i) + _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_simd256_mul_f32, _ksl_ld(a.data[i].as.i) * _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_simd512_add_f32, _ksl_ld(a.data[i].as.i) + _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_simd512_add_f64, _ksl_ld(a.data[i].as.i) + _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_simd512_mul_f32, _ksl_ld(a.data[i].as.i) * _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_simd512_mul_f64, _ksl_ld(a.data[i].as.i) * _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_simd512_max_f32,
    (_ksl_ld(a.data[i].as.i) > _ksl_ld(b.data[i].as.i) ? _ksl_ld(a.data[i].as.i) : _ksl_ld(b.data[i].as.i)))
KS_LEGACY_BINOP_F(system_simd512_min_f32,
    (_ksl_ld(a.data[i].as.i) < _ksl_ld(b.data[i].as.i) ? _ksl_ld(a.data[i].as.i) : _ksl_ld(b.data[i].as.i)))

KS_LEGACY_BINOP_F(system_neon_add_f32, _ksl_ld(a.data[i].as.i) + _ksl_ld(b.data[i].as.i))
KS_LEGACY_BINOP_F(system_neon_mul_f32, _ksl_ld(a.data[i].as.i) * _ksl_ld(b.data[i].as.i))

/* ---- integer binary ops (stored directly as long long in .as.i) ---- */
#define KS_LEGACY_BINOP_I(FNAME, OP)                                            \
    static inline ks_array FNAME(ks_array a, ks_array b) {                      \
        long long n = a.length;                                                 \
        ks_val_t* o = (ks_val_t*)malloc((size_t)n * sizeof(ks_val_t));         \
        for (long long i = 0; i < n; i++)                                       \
            o[i].as.i = a.data[i].as.i OP b.data[i].as.i;                       \
        return (ks_array){o, n};                                                \
    }

KS_LEGACY_BINOP_I(system_simd_add_i32, +)
KS_LEGACY_BINOP_I(system_simd_sub_i32, -)
KS_LEGACY_BINOP_I(system_simd_mul_i32, *)

/* ---- NEON unsigned widening adds (numpy uintN wrap semantics) ---- */
static inline ks_array system_neon_add_u8(ks_array a, ks_array b) {
    long long n = a.length;
    ks_val_t* o = (ks_val_t*)malloc((size_t)n * sizeof(ks_val_t));
    for (long long i = 0; i < n; i++)
        o[i].as.i = (long long)((unsigned char)((unsigned char)a.data[i].as.i + (unsigned char)b.data[i].as.i));
    return (ks_array){o, n};
}
static inline ks_array system_neon_add_u16(ks_array a, ks_array b) {
    long long n = a.length;
    ks_val_t* o = (ks_val_t*)malloc((size_t)n * sizeof(ks_val_t));
    for (long long i = 0; i < n; i++)
        o[i].as.i = (long long)((unsigned short)((unsigned short)a.data[i].as.i + (unsigned short)b.data[i].as.i));
    return (ks_array){o, n};
}
static inline ks_array system_neon_add_u32(ks_array a, ks_array b) {
    long long n = a.length;
    ks_val_t* o = (ks_val_t*)malloc((size_t)n * sizeof(ks_val_t));
    for (long long i = 0; i < n; i++)
        o[i].as.i = (long long)((unsigned int)((unsigned int)a.data[i].as.i + (unsigned int)b.data[i].as.i));
    return (ks_array){o, n};
}
static inline ks_array system_neon_mul_u32(ks_array a, ks_array b) {
    long long n = a.length;
    ks_val_t* o = (ks_val_t*)malloc((size_t)n * sizeof(ks_val_t));
    for (long long i = 0; i < n; i++)
        o[i].as.i = (long long)((unsigned int)((unsigned int)a.data[i].as.i * (unsigned int)b.data[i].as.i));
    return (ks_array){o, n};
}

/* ---- unary sqrt ---- */
#define KS_LEGACY_SQRT(FNAME)                                                   \
    static inline ks_array FNAME(ks_array a) {                                  \
        long long n = a.length;                                                 \
        ks_val_t* o = (ks_val_t*)malloc((size_t)n * sizeof(ks_val_t));         \
        for (long long i = 0; i < n; i++)                                       \
            o[i].as.i = _ksl_dl(sqrt(_ksl_ld(a.data[i].as.i)));                \
        return (ks_array){o, n};                                                \
    }

KS_LEGACY_SQRT(system_simd_sqrt_f32)
KS_LEGACY_SQRT(system_simd256_sqrt_f32)
KS_LEGACY_SQRT(system_simd512_sqrt_f32)
KS_LEGACY_SQRT(system_simd512_sqrt_f64)

/* ---- constructors ---- */
static inline ks_array system_simd_set1_f32(double val) {
    ks_val_t* o = (ks_val_t*)malloc(4 * sizeof(ks_val_t));
    long long bits = _ksl_dl(val);
    for (int i = 0; i < 4; i++) o[i].as.i = bits;
    return (ks_array){o, 4};
}
static inline ks_array system_simd_zero(void) {
    ks_val_t* o = (ks_val_t*)malloc(4 * sizeof(ks_val_t));
    for (int i = 0; i < 4; i++) o[i].as.i = _ksl_dl(0.0);
    return (ks_array){o, 4};
}
static inline ks_array system_simd_hadd_f32(ks_array a, ks_array b) {
    ks_val_t* o = (ks_val_t*)malloc(4 * sizeof(ks_val_t));
    o[0].as.i = _ksl_dl(_ksl_ld(a.data[0].as.i) + _ksl_ld(a.data[1].as.i));
    o[1].as.i = _ksl_dl(_ksl_ld(a.data[2].as.i) + _ksl_ld(a.data[3].as.i));
    o[2].as.i = _ksl_dl(_ksl_ld(b.data[0].as.i) + _ksl_ld(b.data[1].as.i));
    o[3].as.i = _ksl_dl(_ksl_ld(b.data[2].as.i) + _ksl_ld(b.data[3].as.i));
    return (ks_array){o, 4};
}

/* ---- load/store (translated to ks_array copy semantics) ---- */
static inline ks_array system_simd_load_f32(ks_array ptr) {
    long long n = ptr.length < 4 ? ptr.length : 4;
    ks_val_t* o = (ks_val_t*)malloc(4 * sizeof(ks_val_t));
    for (long long i = 0; i < 4; i++)
        o[i].as.i = (i < n) ? ptr.data[i].as.i : _ksl_dl(0.0);
    return (ks_array){o, 4};
}
static inline ks_array system_simd_store_f32(ks_array ptr, ks_array v) {
    long long n = (ptr.length < v.length) ? ptr.length : v.length;
    for (long long i = 0; i < n; i++) ptr.data[i].as.i = v.data[i].as.i;
    return ptr;
}

/* ---- accel.* convenience wrappers (mirror stdlib/accel.ks) ---- */
/* All take ks_array (bit-stored float lists) and return a ks_array whose
 * elements are bit-stored floats, so result[i] reads back correctly. */

static inline ks_array ks_accel_vector_add(ks_array a, ks_array b) {
    long long n = a.length;
    float* pa = (float*)malloc((size_t)n * sizeof(float));
    float* pb = (float*)malloc((size_t)n * sizeof(float));
    float* pc = (float*)malloc((size_t)n * sizeof(float));
    for (long long i = 0; i < n; i++) {
        pa[i] = (float)_ksl_ld(a.data[i].as.i);
        pb[i] = (float)_ksl_ld(b.data[i].as.i);
    }
    for (long long i = 0; i < n; i++) pc[i] = pa[i] + pb[i];
    ks_val_t* o = (ks_val_t*)malloc((size_t)n * sizeof(ks_val_t));
    for (long long i = 0; i < n; i++) o[i].as.i = _ksl_dl((double)pc[i]);
    free(pa); free(pb); free((void*)pc);
    return (ks_array){o, n};
}
static inline ks_array ks_accel_vector_scale(ks_array a, double s) {
    long long n = a.length;
    float* pa = (float*)malloc((size_t)n * sizeof(float));
    for (long long i = 0; i < n; i++) pa[i] = (float)_ksl_ld(a.data[i].as.i);
    for (long long i = 0; i < n; i++) pa[i] = (float)((double)pa[i] * s);
    ks_val_t* o = (ks_val_t*)malloc((size_t)n * sizeof(ks_val_t));
    for (long long i = 0; i < n; i++) o[i].as.i = _ksl_dl((double)pa[i]);
    free(pa);
    return (ks_array){o, n};
}
static inline double ks_accel_vector_dot(ks_array a, ks_array b) {
    long long n = a.length;
    float* pa = (float*)malloc((size_t)n * sizeof(float));
    float* pb = (float*)malloc((size_t)n * sizeof(float));
    for (long long i = 0; i < n; i++) {
        pa[i] = (float)_ksl_ld(a.data[i].as.i);
        pb[i] = (float)_ksl_ld(b.data[i].as.i);
    }
    double total = 0.0;
    for (long long i = 0; i < n; i++) total += (double)pa[i] * (double)pb[i];
    free(pa); free(pb);
    return total;
}
static inline ks_array ks_accel_gpu_vector_add(ks_array a, ks_array b) {
    /* Mirrors gpu.* which dispatches to OpenCL/CUDA when present and
     * transparently falls back to CPU SIMD otherwise (see ks_gpu.h). */
    long long n = a.length;
    float* pa = (float*)malloc((size_t)n * sizeof(float));
    float* pb = (float*)malloc((size_t)n * sizeof(float));
    float* pc = (float*)malloc((size_t)n * sizeof(float));
    for (long long i = 0; i < n; i++) {
        pa[i] = (float)_ksl_ld(a.data[i].as.i);
        pb[i] = (float)_ksl_ld(b.data[i].as.i);
    }
    for (long long i = 0; i < n; i++) pc[i] = pa[i] + pb[i];
    ks_val_t* o = (ks_val_t*)malloc((size_t)n * sizeof(ks_val_t));
    for (long long i = 0; i < n; i++) o[i].as.i = _ksl_dl((double)pc[i]);
    free(pa); free(pb); free((void*)pc);
    return (ks_array){o, n};
}

#endif /* KS_LEGACY_SIMD_H */
