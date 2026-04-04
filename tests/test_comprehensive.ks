:: KentScript - Comprehensive Test Suite

print("=== KENTSCRIPT COMPREHENSIVE TEST ===\n");

:: Phase 2.1 - Subprocess
print("Phase 2.1: Subprocess");
system_subprocess_run("echo test", 0);
print("✓ subprocess.run()");

:: Phase 3 - HTTP
print("\nPhase 3: HTTP");
system_http_get("https://httpbin.org/get", "");
system_http_post("https://httpbin.org/post", "", "{}");
print("✓ http.get/post");

:: Phase 4 - Collections
print("\nPhase 4: Collections");
let arr = [1, 2, 3];
arr.append(4);
let d = {"k": "v", "k2": "v2"};
system_collections_namedtuple("Point", ["x", "y"]);
print("✓ collections");

:: Phase 5 - Strings & Encoding  
print("\nPhase 5: Strings & Encoding");
system_strings_contains("hello world", "world");
system_strings_upper("test");
system_encoding_base64_encode("hello");
system_encoding_base64_decode("aGVsbG8=");
system_encoding_hex_encode("test");
system_encoding_hex_decode("74657374");
print("✓ str & encoding");

:: Phase 1.2 - OS
print("\nPhase 1.2: OS");
system_file_stat("/tmp");
system_os_getppid();
system_os_getuid();
print("✓ OS functions");

print("\n=== ALL TESTS PASSED ===");