:: Test Phase 5 - Strings & Encoding

print("Test: String contains");
let s = "hello world";
if system_str_contains(s, "world") {
    print("✓ str.contains() works");
}

print("\nTest: String startswith/endswith");
if system_str_startswith(s, "hello") and system_str_endswith(s, "world") {
    print("✓ str.startswith()/endswith() work");
}

print("\nTest: String split/join");
let parts = system_str_split("a,b,c", ",");
let joined = system_str_join(parts, "-");
if joined == "a-b-c" {
    print("✓ str.split()/join() work");
}

print("\nTest: String strip");
let trimmed = system_str_strip("  test  ");
if trimmed == "test" {
    print("✓ str.strip() works");
}

print("\nTest: String replace");
let replaced = system_str_replace("foo bar", "bar", "baz");
if replaced == "foo baz" {
    print("✓ str.replace() works");
}

print("\nTest: String case");
if system_str_upper("test") == "TEST" and system_str_lower("TEST") == "test" {
    print("✓ str.upper()/lower() work");
}

print("\nTest: base64 encode/decode");
let enc = system_encoding_base64_encode("hello");
let dec = system_encoding_base64_decode(enc);
if dec == "hello" {
    print("✓ base64 encode/decode work");
}

print("\nTest: hex encode/decode");
let hex_enc = system_encoding_hex_encode("test");
let hex_dec = system_encoding_hex_decode(hex_enc);
if hex_dec == "test" {
    print("✓ hex encode/decode work");
}

print("\nTest: url encode/decode");
let url_enc = system_encoding_url_encode("hello world");
let url_dec = system_encoding_url_decode(url_enc);
if url_dec == "hello world" {
    print("✓ url encode/decode work");
}

print("\n=== Phase 5 Strings & Encoding Complete ===");
