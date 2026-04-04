:: Phase 13.3: Decimal & Fractions
let d = system_decimal_new(1.1);
let d2 = system_decimal_new(2.2);
print(system_decimal_to_str(system_decimal_add(d, d2)));
let f = system_fraction_new(1, 3);
let f2 = system_fraction_new(1, 6);
let fsum = system_fraction_add(f, f2);
print(system_fraction_numerator(fsum));
print(system_fraction_denominator(fsum));
print(system_math_gamma(5));
print(system_math_erf(1));

:: Phase 14: Syscall wrappers
print(system_syscall_getpid());
print(system_syscall_getcwd());
print(system_syscall_strerror(2));

:: Phase 15: FFI
let libc = system_ffi_load("libc.so.6");
print(system_ffi_sizeof("c_int"));
let arr = system_ffi_array("c_int", 5);
print(arr);

:: Phase 22: Magic methods
print(system_magic_add(3, 4));
print(system_magic_eq(5, 5));
print(system_magic_len([1,2,3]));
print(system_magic_contains([1,2,3], 2));
print(system_magic_str(42));

:: Phase 23: Generators & context managers
let gen = system_generator_from_list([1,2,3,4,5]);
print(system_generator_next(gen));
print(system_generator_next(gen));
print(system_generator_to_list(gen));

:: Phase 24: Import system
print(system_import_is_available("json"));
print(system_import_is_available("nonexistent_xyz"));
let math_mod = system_import("math");
print(system_import_from("math", "pi"));
print(system_kpm_version("pip"));

:: Phase 30.4: Result / Option
let ok = system_result_ok(42);
print(system_result_is_ok(ok));
print(system_result_unwrap(ok));
let err = system_result_err("something failed");
print(system_result_is_err(err));
print(system_result_unwrap_or(err, 0));

let some = system_option_some(99);
print(system_option_is_some(some));
print(system_option_unwrap(some));
let opt_none = system_option_none();
print(system_option_is_none(opt_none));
print(system_option_unwrap_or(opt_none, -1));

:: Phase 30.5: Iterator abstractions
print(system_iter_map([1,2,3,4], system_builtin_str));
print(system_iter_filter([1,2,3,4,5,6], system_builtin_bool));
print(system_iter_take([1,2,3,4,5], 3));
print(system_iter_skip([1,2,3,4,5], 2));
print(system_iter_unique([1,2,2,3,3,3]));
print(system_iter_partition([1,2,3,4,5,6], system_builtin_bool));
print(system_iter_first([10,20,30]));
print(system_iter_last([10,20,30]));
print(system_iter_sum([1,2,3,4,5]));

:: Phase 30.8: Concurrency primitives
let m = system_mutex_new();
system_mutex_lock(m);
print(system_mutex_try_lock(m));
system_mutex_unlock(m);
print(system_mutex_try_lock(m));
system_mutex_unlock(m);

let a = system_atomic_new(0);
system_atomic_store(a, 10);
print(system_atomic_load(a));
print(system_atomic_fetch_add(a, 5));
print(system_atomic_load(a));
print(system_atomic_compare_exchange(a, 15, 100));
print(system_atomic_load(a));

:: Phase 30.6: RAII file handle
let fh = system_file_handle("/tmp/ks_test_raii.txt", "w");
system_file_handle_write(fh, "hello raii");
system_file_handle_close(fh);
let fh2 = system_file_handle("/tmp/ks_test_raii.txt", "r");
print(system_file_handle_read(fh2));
system_file_handle_close(fh2);

print("ALL PHASE 13.3/14/15/22/23/24/30 TESTS PASSED");
