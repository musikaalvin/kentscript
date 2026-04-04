:: Test Phase 4.3: Itertools
print(system_itertools_chain([1,2], [3,4], [5]));
print(system_itertools_combinations([1,2,3], 2));
print(system_itertools_permutations([1,2,3], 2));
print(system_itertools_product([1,2], [3,4]));
print(system_itertools_accumulate([1,2,3,4,5]));
print(system_itertools_zip_longest([1,2,3], [4,5], fillvalue=0));
print(system_itertools_islice([1,2,3,4,5], 3));
print(system_itertools_takewhile(system_builtin_bool, [1,2,0,3]));
print(system_itertools_groupby([1,1,2,2,3]));
print(system_itertools_compress([1,2,3,4], [1,0,1,0]));

:: Test Phase 4.2: Collections extras
let d = system_collections_deque([1,2,3]);
system_collections_deque_appendleft(d, 0);
print(d);
system_collections_deque_rotate(d, 1);
print(d);

let c = system_collections_counter([1,1,2,3,3,3]);
print(system_collections_counter_most_common(c, 2));

:: Test Phase 5.3: Encoding extras
let b = system_encoding_utf8_encode("hello");
print(system_encoding_utf8_decode(b));

:: Test Phase 17: Testing
system_testing_assert_equal(1+1, 2);
system_testing_assert_true(5 > 3);
system_testing_assert_in(2, [1,2,3]);
system_testing_assert_almost_equal(3.14159, 3.14158, 4);
print("testing assertions passed");

:: Test Phase 19: Config
let cfg = system_config_merge({"a": 1}, {"b": 2}, {"c": 3});
print(cfg);

:: Test Phase 20: Templates
print(system_template_render("Hello $name!", {"name": "KentScript"}));
print(system_template_render_format("Hello {name}!", name="World"));

:: Test Phase 16.1: Debug
print(system_debug_inspect_var(42));

:: Test Phase 25: Docs
print(system_docstring(system_builtin_abs));

print("ALL PHASE 4.2/4.3/5.3/16/17/19/20/25 TESTS PASSED");
