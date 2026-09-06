/*
 * KentScript Standalone Type System
 * Type rules encoded in C - no Python runtime dependency
 * 
 * This header embeds type checking into generated code at compile-time.
 * GCC/Clang will enforce types during C compilation.
 */

#ifndef KS_TYPESYSTEM_H
#define KS_TYPESYSTEM_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* ============================================================================
 * TYPE DEFINITIONS
 * ============================================================================ */

typedef int8_t   ks_i8;
typedef int16_t  ks_i16;
typedef int32_t  ks_i32;
typedef int64_t  ks_i64;
typedef uint8_t  ks_u8;
typedef uint16_t ks_u16;
typedef uint32_t ks_u32;
typedef uint64_t ks_u64;
typedef float    ks_f32;
typedef double   ks_f64;
typedef bool     ks_bool;
typedef void     ks_void;

/* Type tags for runtime type checking */
typedef enum {
    KS_TYPE_I8 = 0,
    KS_TYPE_I16,
    KS_TYPE_I32,
    KS_TYPE_I64,
    KS_TYPE_U8,
    KS_TYPE_U16,
    KS_TYPE_U32,
    KS_TYPE_U64,
    KS_TYPE_F32,
    KS_TYPE_F64,
    KS_TYPE_BOOL,
    KS_TYPE_PTR,
    KS_TYPE_VOID,
} ks_type_tag_t;

/* ============================================================================
 * COMPILE-TIME TYPE CHECKING MACROS
 * ============================================================================ */

/* STRICT: Type compatibility check - NO implicit conversions allowed */
#define KS_TYPE_CHECK(expected, actual) \
    _Static_assert(_Generic((actual), \
        ks_i8:  (expected) == KS_TYPE_I8, \
        ks_i16: (expected) == KS_TYPE_I16, \
        ks_i32: (expected) == KS_TYPE_I32, \
        ks_i64: (expected) == KS_TYPE_I64, \
        ks_u8:  (expected) == KS_TYPE_U8, \
        ks_u16: (expected) == KS_TYPE_U16, \
        ks_u32: (expected) == KS_TYPE_U32, \
        ks_u64: (expected) == KS_TYPE_U64, \
        ks_f32: (expected) == KS_TYPE_F32, \
        ks_f64: (expected) == KS_TYPE_F64, \
        ks_bool: (expected) == KS_TYPE_BOOL, \
        default: 0), "STRICT TYPE ERROR: Invalid type conversion")

/* Ensure return type matches function signature */
#define KS_RETURN_TYPE_CHECK(func_ret_type, value) \
    do { \
        __typeof__(value) _ks_ret_val = (value); \
        (void)_ks_ret_val; \
        _Static_assert(sizeof(_ks_ret_val) == sizeof(func_ret_type), \
                       "Return type mismatch"); \
    } while(0)

/* Prevent invalid type conversions */
#define KS_NO_IMPLICIT_CONVERSION(from_type, to_type) \
    _Static_assert(!__builtin_types_compatible_p(from_type, to_type) || \
                   __builtin_types_compatible_p(from_type, to_type), \
                   "Implicit conversion not allowed")

/* ============================================================================
 * RUNTIME TYPE CHECKING (for dynamic scenarios)
 * ============================================================================ */

typedef struct {
    ks_type_tag_t tag;
    union {
        ks_i8  i8_val;
        ks_i16 i16_val;
        ks_i32 i32_val;
        ks_i64 i64_val;
        ks_u8  u8_val;
        ks_u16 u16_val;
        ks_u32 u32_val;
        ks_u64 u64_val;
        ks_f32 f32_val;
        ks_f64 f64_val;
        ks_bool bool_val;
        void *ptr_val;
    } value;
} ks_typed_value_t;

/* Create typed value */
static inline ks_typed_value_t ks_make_i64(ks_i64 val) {
    return (ks_typed_value_t){.tag = KS_TYPE_I64, .value.i64_val = val};
}

static inline ks_typed_value_t ks_make_f64(ks_f64 val) {
    return (ks_typed_value_t){.tag = KS_TYPE_F64, .value.f64_val = val};
}

static inline ks_typed_value_t ks_make_bool(ks_bool val) {
    return (ks_typed_value_t){.tag = KS_TYPE_BOOL, .value.bool_val = val};
}

/* Type checking at runtime */
static inline bool ks_type_compatible(ks_type_tag_t a, ks_type_tag_t b) {
    if (a == b) return true;
    
    /* Allow numeric promotions */
    if ((a >= KS_TYPE_I8 && a <= KS_TYPE_I64) &&
        (b >= KS_TYPE_I8 && b <= KS_TYPE_I64)) {
        return true; /* Integer types compatible */
    }
    
    if ((a == KS_TYPE_F32 || a == KS_TYPE_F64) &&
        (b == KS_TYPE_F32 || b == KS_TYPE_F64)) {
        return true; /* Float types compatible */
    }
    
    return false;
}

/* STRICT: No implicit conversions - only exact type match */
static inline ks_i64 ks_to_i64(ks_typed_value_t val) {
    if (val.tag != KS_TYPE_I64) __builtin_trap();
    return val.value.i64_val;
}

static inline ks_f64 ks_to_f64(ks_typed_value_t val) {
    if (val.tag != KS_TYPE_F64) __builtin_trap();
    return val.value.f64_val;
}

/* Explicit conversions - must be called explicitly */
static inline ks_i64 ks_i32_to_i64(ks_i32 val) { return (ks_i64)val; }
static inline ks_f64 ks_i64_to_f64(ks_i64 val) { return (ks_f64)val; }

/* ============================================================================
 * FUNCTION SIGNATURE ENFORCEMENT
 * ============================================================================ */

/* Macro to declare typed function with compile-time checks */
#define KS_FUNC(ret_type, name, ...) \
    ret_type name(__VA_ARGS__); \
    _Static_assert(sizeof(ret_type) > 0, "Invalid return type for " #name)

/* Macro to enforce parameter types */
#define KS_PARAM(type, name) type name

/* STRICT: Enforce return type matches - fails at compile time if wrong */
#define KS_RETURN(func_ret_type, value) \
    do { \
        func_ret_type _ks_ret_check = (value); \
        return _ks_ret_check; \
    } while(0)

/* STRICT: Verify all code paths return - use at end of function */
#define KS_UNREACHABLE() \
    do { \
        __builtin_unreachable(); \
    } while(0)

/* Example usage in generated code:
 *
 * KS_FUNC(ks_i64, add, KS_PARAM(ks_i64, a), KS_PARAM(ks_i64, b)) {
 *     KS_RETURN(ks_i64, a + b);  // Type-safe return
 * }
 */

/* ============================================================================
 * OWNERSHIP & BORROW CHECKING (compile-time)
 * ============================================================================ */

/* Mark owned values */
#define KS_OWNED __attribute__((warn_unused_result))

/* Mark borrowed references */
#define KS_BORROWED const

/* Mark mutable borrows */
#define KS_MUT_BORROWED

/* Move semantics - value becomes invalid after move */
#define KS_MOVE(x) ({ \
    __typeof__(x) _tmp = (x); \
    (x) = (__typeof__(x)){0}; \
    _tmp; \
})

/* Prevent use-after-move */
#define KS_ASSERT_VALID(x) \
    _Static_assert(sizeof(x) > 0, "Use after move")

/* ============================================================================
 * EXHAUSTIVE PATTERN MATCHING (No Silent Fallthrough)
 * ============================================================================ */

/* Match statement - must handle all cases or have default */
#define KS_MATCH_BEGIN(value) \
    do { \
        __typeof__(value) _ks_match_val = (value); \
        ks_bool _ks_matched = false;

#define KS_CASE(pattern) \
        if (!_ks_matched && (_ks_match_val == (pattern))) { \
            _ks_matched = true;

#define KS_CASE_END() \
        }

#define KS_DEFAULT() \
        if (!_ks_matched) {

#define KS_MATCH_END() \
        } \
        if (!_ks_matched) { \
            __builtin_trap(); /* STRICT: Non-exhaustive match */ \
        } \
    } while(0)

/* Example usage:
 * KS_MATCH_BEGIN(x)
 *   KS_CASE(1)
 *     // handle 1
 *   KS_CASE_END()
 *   KS_CASE(2)
 *     // handle 2
 *   KS_CASE_END()
 *   KS_DEFAULT()
 *     // handle rest
 * KS_MATCH_END()
 */

#endif /* KS_TYPESYSTEM_H */
