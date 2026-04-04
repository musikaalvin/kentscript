:: Test Phase 7 - Cryptography

print("Test: Hash functions");
let md5 = system_crypto_md5("test");
if len(md5) == 32 {
    print("✓ md5 works");
}
let sha256 = system_crypto_sha256("test");
if len(sha256) == 64 {
    print("✓ sha256 works");
}
let blake = system_crypto_blake2b("test");
if len(blake) == 128 {
    print("✓ blake2b works");
}

print("\nTest: HMAC");
let hmac = system_crypto_hmac_sha256("key", "message");
if len(hmac) == 64 {
    print("✓ hmac_sha256 works");
}

print("\nTest: Random & Token");
let token = system_crypto_generate_token(16);
if len(token) > 0 {
    print("✓ generate_token works");
}
let uuid = system_crypto_uuid4();
if len(uuid) == 36 {
    print("✓ uuid4 works");
}

print("\nTest: PBKDF2");
let pbkdf2 = system_crypto_pbkdf2("password", "salt", 1000, 32, "sha256");
if len(pbkdf2) == 64 {
    print("✓ pbkdf2 works");
}

print("\n=== Phase 7 Cryptography Complete ===");
