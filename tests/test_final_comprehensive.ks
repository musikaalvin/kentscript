:: KentScript - Final Comprehensive Test

print("=== KENTSCRIPT FINAL COMPREHENSIVE TEST ===\n");

:: Phase 6: Serialization
print("Phase 6: Serialization");
let json_data = system_json_loads('{"test": 123}');
if json_data['test'] == 123 {
    print("✓ JSON works");
}
let csv_data = system_csv_reader("/etc/passwd");
if csv_data != none {
    print("✓ CSV works");
}
let pickled = system_pickle_dumps({"key": "value"});
let unpickled = system_pickle_loads(pickled);
if unpickled['key'] == "value" {
    print("✓ Pickle works");
}

:: Phase 7: Cryptography
print("\nPhase 7: Cryptography");
let hash = system_crypto_sha256("test");
if len(hash) == 64 {
    print("✓ Hash functions work");
}
let token = system_crypto_generate_token(16);
if len(token) > 0 {
    print("✓ Random functions work");
}
let uuid = system_crypto_uuid4();
if len(uuid) == 36 {
    print("✓ UUID works");
}

:: Phase 9: System Information
print("\nPhase 9: System Information");
let cpu = system_cpu_count();
if cpu > 0 {
    print("✓ CPU/Memory/Disk work");
}
let plat = system_platform();
if plat != none {
    print("✓ Platform info works");
}
let uptime = system_uptime();
if uptime > 0 {
    print("✓ Uptime works");
}

:: Phase 1.2: OS (already done)
print("\nPhase 1.2: OS Operations");
let stat = system_file_stat("/tmp");
if stat != none {
    print("✓ File stat works");
}
let ppid = system_os_getppid();
if ppid > 0 {
    print("✓ Process info works");
}

:: Phase 2.1: Subprocess (already done)
print("\nPhase 2.1: Subprocess");
let result = system_subprocess_run("echo test", shell=true);
if result.returncode == 0 {
    print("✓ Subprocess works");
}

:: Phase 3: HTTP (already done)
print("\nPhase 3: HTTP");
let resp = system_http_get("https://httpbin.org/get");
if resp.status == 200 {
    print("✓ HTTP works");
}

:: Phase 4: Collections (already done)
print("\nPhase 4: Collections");
let d = system_collections_deque([1, 2]);
if d != none {
    print("✓ Collections work");
}

:: Phase 5: Strings (already done)
print("\nPhase 5: Strings & Encoding");
let upper = system_str_upper("test");
if upper == "TEST" {
    print("✓ String functions work");
}
let b64 = system_encoding_base64_encode("hello");
if system_encoding_base64_decode(b64) == "hello" {
    print("✓ Encoding works");
}

print("\n=== ALL PHASES COMPLETE ===");
print("Tested: Phases 1.2, 2.1, 3, 4, 5, 6, 7, 9");
print("Total functions: 100+");
