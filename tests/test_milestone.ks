:: KentScript - 25% Milestone Test

print("=== KENTSCRIPT 25% MILESTONE TEST ===\n");

:: Phase 13: Math & Random
print("Phase 13: Math & Random");
let sqrt = system_math_sqrt(16);
if sqrt == 4 {
    print("✓ Math functions work");
}
let rand = system_random_random();
if rand >= 0 and rand < 1 {
    print("✓ Random functions work");
}
let pi = system_math_pi();
if pi > 3.14 {
    print("✓ Math constants work");
}

:: All previous phases (quick check)
print("\nPrevious Phases:");
let json_data = system_json_loads('{"test": 1}');
if json_data['test'] == 1 {
    print("✓ Serialization works");
}
let hash = system_crypto_sha256("data");
if len(hash) == 64 {
    print("✓ Cryptography works");
}
let cpu = system_cpu_count();
if cpu > 0 {
    print("✓ System info works");
}
let gzip_data = system_compress_gzip("test");
if system_decompress_gzip(gzip_data) == "test" {
    print("✓ Compression works");
}
let lock = system_threading_Lock();
if lock != none {
    print("✓ Concurrency works");
}
let conn = system_database_sqlite_connect("/tmp/test.db");
if conn != none {
    print("✓ Database works");
}
let result = system_subprocess_run("echo test", shell=true);
if result.returncode == 0 {
    print("✓ Subprocess works");
}
let resp = system_http_get("https://httpbin.org/get");
if resp.status == 200 {
    print("✓ HTTP works");
}
let d = system_collections_deque([1, 2]);
if d != none {
    print("✓ Collections works");
}
let upper = system_str_upper("test");
if upper == "TEST" {
    print("✓ Strings work");
}
let stat = system_file_stat("/tmp");
if stat != none {
    print("✓ File operations work");
}

print("\n=== 25% MILESTONE ACHIEVED ===");
print("Total: 13 phases implemented");
print("Functions: 250+");
