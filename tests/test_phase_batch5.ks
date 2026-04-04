:: Phase 29.2: Struct & Union
let s = system_struct_new({"x": "c_int", "y": "c_int"});
system_struct_set(s, "x", 10);
system_struct_set(s, "y", 20);
print(system_struct_get(s, "x"));
print(system_struct_sizeof(s));
print(system_sizeof(42));
print(system_alignof("c_int"));

:: Phase 29.8: Preprocessor-like
print(system_cfg("linux"));
print(system_cfg("x86_64"));
let C = system_const("MAX", 100);
print(C);
print(system_constexpr(system_builtin_abs, -5));

:: Phase 29.10: Compiler intrinsics
print(system_builtin_likely(true));
print(system_builtin_overflow_add(2147483647, 1));
print(system_builtin_overflow_mul(100, 200));

:: Phase 29.12: Type system
print(system_type_i8(300));
print(system_type_u32(-1));
print(system_type_check(42, "int"));
print(system_type_check("hi", "str"));
print(system_type_name([1,2,3]));
print(system_comptime_sizeof("i32"));
print(system_comptime_sizeof("f64"));

:: Phase 30.2: Rc/Arc/Slice/Arena
let rc = system_rc_new(42);
let rc2 = system_rc_clone(rc);
print(system_rc_count(rc));
print(system_rc_get(rc));
system_rc_drop(rc2);
print(system_rc_count(rc));

let sl = system_slice_new([1,2,3,4,5], 1, 4);
print(sl);
print(system_slice_len(sl));

let arena = system_arena_new();
let buf = system_arena_alloc(arena, 64);
print(system_arena_total(arena));
system_arena_reset(arena);
print(system_arena_total(arena));

:: Phase 30.3: Smart pointers
let u = system_ptr_unique(99);
print(system_ptr_unique_get(u));
let val = system_ptr_unique_move(u);
print(val);
print(system_ptr_nonnull(42));

:: Phase 30.10: Pattern matching
let result = system_match(3, [[1, "one"], [2, "two"], [3, "three"], ["_", "other"]]);
print(result);
let r2 = system_match_range(15, [[[0,10], "low"], [[11,20], "mid"], [[21,100], "high"]]);
print(r2);
let parts = system_destructure_list([1,2,3,4,5], 2);
print(parts);

:: Phase 30.11: Trait system
print(system_trait_has(42, "Display"));

:: Phase 30.12: Generics
let gfn = system_generic_fn(system_builtin_str);
print(system_generic_call(gfn, 42));

:: Phase 30.13: Macros
let m = system_macro_define("double", system_builtin_abs);
print(system_macro_stringify([1,2,3]));
print(system_macro_concat("hello", " ", "world"));
print(system_macro_env("HOME"));

:: Phase 31: Safety checks
print(system_bounds_check([1,2,3], 1));
print(system_overflow_check(127, 8, true));
print(system_unsafe_check("ptr_read"));
print(system_unsafe_check("print"));

:: Phase 31.4: Build system
print(system_build_profile());
print(system_build_target());
print(system_mode());

:: Phase 32: Language parity
print(system_comptime_eval("2 ** 10"));
print(system_comptime_type(3.14));
let r = system_error_union(system_builtin_int, "42");
print(system_result_unwrap(r));
let opt = system_optional(42);
print(system_option_is_some(opt));
let opt2 = system_optional(0);
print(system_option_is_none(opt2));
print(system_test_block("test1", func() { return system_builtin_bool(true); }));

:: Phase 33: Parity
print(system_mode());
let info = system_runtime_info();
print(info);
let fm = system_feature_matrix();
print(fm);

print("ALL BATCH 5 TESTS PASSED");
