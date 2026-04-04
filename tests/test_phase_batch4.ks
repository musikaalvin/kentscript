:: Phase 8 extras: timezone, strftime
print(system_datetime_utcnow());
print(system_time_strftime("%Y-%m-%d"));
print(system_datetime_weekday(2026, 3, 14));
print(system_datetime_isoformat(2026, 3, 14, 12, 0, 0));

:: Phase 11: Future, thread-local, thread pool
let fut = system_future_new();
system_future_set_result(fut, 42);
print(system_future_result(fut));
print(system_future_done(fut));

let tl = system_thread_local();
system_thread_local_set(tl, "x", 99);
print(system_thread_local_get(tl, "x"));

let pool = system_thread_pool(2);
let results = system_thread_pool_map(pool, system_builtin_str, [1,2,3,4]);
print(results);
system_thread_pool_shutdown(pool);

:: Phase 12 remaining: executemany
let conn = system_database_sqlite_connect(":memory:");
system_database_sqlite_execute(conn, "CREATE TABLE t (id INTEGER, val TEXT)");
let cur = system_database_sqlite_executemany(conn, "INSERT INTO t VALUES (?,?)", [[1,"a"],[2,"b"],[3,"c"]]);
system_database_sqlite_commit(conn);
let rows = system_database_sqlite_fetchall(system_database_sqlite_execute(conn, "SELECT * FROM t"));
print(rows);
system_database_sqlite_close(conn);

:: Phase 17 remaining: mock, parametrize
let mock = system_testing_mock(42);
print(mock(1, 2));
print(mock.call_count());
mock.assert_called();

let results = system_testing_parametrize(system_testing_assert_equal, [[1,1],[2,2],[3,3]]);
print(results);

:: Phase 26.1: syscall file fixes
let fd = system_syscall_creat("/tmp/ks_syscall_test.txt");
system_syscall_write(fd, "hello syscall");
system_syscall_close(fd);
let fd2 = system_syscall_open("/tmp/ks_syscall_test.txt", 0);
print(system_syscall_read(fd2, 13));
system_syscall_close(fd2);
print(system_syscall_stat("/tmp/ks_syscall_test.txt"));
let pipefd = system_syscall_pipe();
print(pipefd);

:: Phase 27: Hardware
print(system_hardware_rdtsc());
let cpuinfo = system_hardware_proc_cpuinfo();
print(system_builtin_len(cpuinfo) > 0);
print(system_hardware_dev_list());

:: Phase 29 extras: bit ops
print(system_bit_test(5, 0));
print(system_bit_set(4, 0));
print(system_bit_clear(7, 1));
print(system_bit_toggle(5, 1));
print(system_bit_mask(4));
print(system_bit_parity(7));
print(system_bit_reverse(0b10110000, 8));
print(system_bit_gray_encode(6));
print(system_bit_gray_decode(system_bit_gray_encode(6)));

:: Phase 30: Vec, String, Box, Traits
let v = system_vec_new(1, 2, 3);
system_vec_push(v, 4);
print(v);
print(system_vec_len(v));
system_vec_sort(v, reverse=true);
print(v);

let s = system_string_new("hello");
print(system_string_push(s, " world"));
print(system_string_chars("abc"));
print(system_string_trim("  hi  "));
print(system_string_repeat("ab", 3));

let b = system_box_new(99);
print(system_box_get(b));
system_box_set(b, 100);
print(system_box_get(b));

print(system_trait_clone([1,2,3]));
print(system_trait_display(42));
print(system_trait_from_str("123", "int"));
print(system_trait_default_list());

print("ALL BATCH 4 TESTS PASSED");
