:: Test Phase 21 built-ins
print(system_builtin_abs(-5));
print(system_builtin_all([1, 2, 3]));
print(system_builtin_any([0, 0, 1]));
print(system_builtin_bin(10));
print(system_builtin_hex(255));
print(system_builtin_chr(65));
print(system_builtin_ord("A"));
print(system_builtin_max(3, 1, 4, 1, 5));
print(system_builtin_min(3, 1, 4));
print(system_builtin_sum([1,2,3,4,5]));
print(system_builtin_sorted([3,1,2]));
print(system_builtin_reversed([1,2,3]));
print(system_builtin_range(5));
print(system_builtin_len([1,2,3]));
print(system_builtin_type(42));

:: Test regex
let m = system_regex_search("(\\d+)", "abc123def");
print(m);
print(system_regex_findall("\\d+", "a1b2c3"));
print(system_regex_sub("\\d", "X", "a1b2c3"));

:: Test set operations
let s = system_builtin_set([1,2,3,2,1]);
print(s);

:: Test platform
print(system_platform_os());
print(system_platform_arch());
print(system_platform_is_linux());

:: Test bytes
let b = system_bytes_from_str("hello");
print(system_bytes_decode(b));
print(system_bytes_hex(b));

:: Test complex
let c = system_complex_new(3, 4);
print(system_complex_abs(c));

:: Test argparse
let parser = system_argparse_new("Test program");
system_argparse_add_argument(parser, "--name");
let args = system_argparse_parse_args(parser, []);
print(args);

print("ALL PHASE 21 TESTS PASSED");
