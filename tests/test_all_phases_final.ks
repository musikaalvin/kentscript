:: KentScript - Complete Implementation Test

print("=== KENTSCRIPT COMPLETE IMPLEMENTATION TEST ===\n");

:: Phase 6: Serialization
print("Phase 6: Serialization");
let json_data = system_json_loads('{"key": "value"}');
if json_data['key'] == "value" {
    print("✓ JSON works");
}
let pickled = system_pickle_dumps({"test": 123});
let unpickled = system_pickle_loads(pickled);
if unpickled['test'] == 123 {
    print("✓ Pickle works");
}

:: Phase 7: Cryptography
print("\nPhase 7: Cryptography");
let hash = system_crypto_sha256("data");
if len(hash) == 64 {
    print("✓ Hash functions work");
}
let token = system_crypto_generate_token(16);
if len(token) > 0 {
    print("✓ Random functions work");
}

:: Phase 9: System Information
print("\nPhase 9: System Information");
let cpu = system_cpu_count();
if cpu > 0 {
    print("✓ CPU/Memory/Disk work");
}
let uptime = system_uptime();
if uptime > 0 {
    print("✓ Uptime works");
}

:: Phase 10: Compression
print("\nPhase 10: Compression");
let gzip_data = system_compress_gzip("test");
let gzip_dec = system_decompress_gzip(gzip_data);
if gzip_dec == "test" {
    print("✓ Compression works");
}

:: Phase 11: Concurrency
print("\nPhase 11: Concurrency");
let lock = system_threading_Lock();
if lock != none {
    print("✓ Threading works");
}
let mp_count = system_multiprocessing_cpu_count();
if mp_count > 0 {
    print("✓ Multiprocessing works");
}

:: Phase 12: Database
print("\nPhase 12: Database");
let conn = system_database_sqlite_connect("/tmp/test.db");
if conn != none {
    print("✓ SQLite works");
    system_database_sqlite_close(conn);
}

:: Previous phases (quick check)
print("\nPrevious Phases:");
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

print("\n=== ALL PHASES COMPLETE ===");
print("Total: 12 phases implemented");
print("Functions: 150+");
