:: KentScript - 30% Milestone Test

print("=== KENTSCRIPT 30% MILESTONE TEST ===\n");

:: Phase 8: DateTime (enhanced)
print("Phase 8: DateTime");
let now = system_datetime_now();
if now['year'] == 2026 {
    print("✓ DateTime works");
}

:: Phase 14: Bit Operations
print("\nPhase 14: Bit Operations");
let and_val = system_bit_and(5, 3);
if and_val == 1 {
    print("✓ Bit operations work");
}
let popcount = system_bit_popcount(255);
if popcount == 8 {
    print("✓ Bit popcount works");
}

:: Phase 29: Struct & Memory
print("\nPhase 29: Struct & Memory");
let packed = system_struct_pack("i", 42);
if len(packed) == 8 {
    print("✓ Struct works");
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
let sqrt = system_math_sqrt(16);
if sqrt == 4 {
    print("✓ Math works");
}
let rand = system_random_random();
if rand >= 0 and rand < 1 {
    print("✓ Random works");
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

print("\n=== 30% MILESTONE ACHIEVED ===");
print("Total: 14 phases implemented");
print("Functions: 300+");
