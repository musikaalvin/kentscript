:: Hash Identifier Tool - Identify hash types
:: Usage: python3 main.py run examples/hash_identifier.ks <hash>

import argparse;
import regex;

let parser = system_argparse_new("KentScript Hash Identifier v1.0");
system_argparse_add_argument(parser, "hash");

let args = system_argparse_parse_args(parser, []);

let hash_input = "";

if hasattr(args, "hash") and args.hash != none {
    hash_input = str(args.hash);
} else {
    print("Usage: hash_identifier.ks <hash>");
    print("");
    print("Example: hash_identifier.ks 5f4dcc3b5aa765d61d8327deb882cf99");
    system_os_exit(1);
}

hash_input = hash_input.trim();
hash_input = hash_input.lower();

print(f"[*] KentScript Hash Identifier v1.0");
print(f"[*] Input: {hash_input}");
print("");

let hash_len = hash_input.len();
let is_hex = true;
for c in hash_input {
    if not ((c >= "0" and c <= "9") or (c >= "a" and c <= "f")) {
        is_hex = false;
    }
}

if not is_hex {
    print("[!] Invalid hash format - not hexadecimal");
    system_os_exit(1);
}

print(f"[*] Hash Length: {hash_len} characters");
print(f"[*] Format: Hexadecimal");
print("");

let possible_types = [];

if hash_len == 32 {
    possible_types.append({"type": "MD5", "confidence": "High", "info": "128-bit hash, commonly used for passwords"});
    possible_types.append({"type": "NTLM", "confidence": "High", "info": "Windows NT LAN Manager hash"});
    possible_types.append({"type": "MD4", "confidence": "Medium", "info": "Older 128-bit hash"});
    possible_types.append({"type": "RIPEMD-128", "confidence": "Low", "info": "Less common hash function"});
    possible_types.append({"type": "Haval-128", "confidence": "Low", "info": "Less common hash function"});
} elif hash_len == 40 {
    possible_types.append({"type": "SHA-1", "confidence": "High", "info": "160-bit hash, deprecated for security"});
    possible_types.append({"type": "RIPEMD-160", "confidence": "Medium", "info": "160-bit hash, used in Bitcoin"});
    possible_types.append({"type": "HAS-160", "confidence": "Low", "info": "Korean hash function"});
} elif hash_len == 56 {
    possible_types.append({"type": "SHA-224", "confidence": "High", "info": "224-bit hash (truncated SHA-256)"});
    possible_types.append({"type": "SHA3-224", "confidence": "High", "info": "224-bit SHA-3 variant"});
} elif hash_len == 64 {
    possible_types.append({"type": "SHA-256", "confidence": "High", "info": "256-bit hash, widely used"});
    possible_types.append({"type": "SHA3-256", "confidence": "High", "info": "256-bit SHA-3 variant"});
    possible_types.append({"type": "BLAKE2s-256", "confidence": "Medium", "info": "Modern hash function"});
    possible_types.append({"type": "Keccak-256", "confidence": "Medium", "info": "Original Keccak hash"});
    possible_types.append({"type": "Bitcoin Block Hash", "confidence": "Low", "info": "SHA-256 double hash"});
} elif hash_len == 96 {
    possible_types.append({"type": "SHA3-384", "confidence": "High", "info": "384-bit SHA-3 variant"});
    possible_types.append({"type": "SHA-384", "confidence": "High", "info": "384-bit hash (truncated SHA-512)"});
} elif hash_len == 128 {
    possible_types.append({"type": "SHA-512", "confidence": "High", "info": "512-bit hash, widely used"});
    possible_types.append({"type": "SHA3-512", "confidence": "High", "info": "512-bit SHA-3 variant"});
    possible_types.append({"type": "BLAKE2b-512", "confidence": "Medium", "info": "Modern hash function"});
    possible_types.append({"type": "Whirlpool", "confidence": "Medium", "info": "512-bit hash"});
    possible_types.append({"type": "Skein-512", "confidence": "Low", "info": "512-bit Skein hash"});
} elif hash_len == 56 {
    possible_types.append({"type": "Argon2", "confidence": "Low", "info": "Memory-hard hash, usually has $argon2$ prefix"});
} else {
    possible_types.append({"type": "Unknown", "confidence": "N/A", "info": f"Length {hash_len} doesn't match common hash lengths"});
}

:: Check for special prefixes
if str(hash_input).starts_with("$1$") {
    print("[*] Detected special prefix: md5crypt / Unix MD5");
    possible_types = [{"type": "md5crypt", "confidence": "Certain", "info": "Unix MD5 password hash"}];
} elif str(hash_input).starts_with("$2a$") or str(hash_input).starts_with("$2b$") {
    print("[*] Detected special prefix: bcrypt");
    possible_types = [{"type": "bcrypt", "confidence": "Certain", "info": "Blowfish-based password hash"}];
} elif str(hash_input).starts_with("$argon2") {
    print("[*] Detected special prefix: Argon2");
    possible_types = [{"type": "Argon2", "confidence": "Certain", "info": "Memory-hard password hash, winner of PHC"}];
} elif str(hash_input).starts_with("$6$") {
    print("[*] Detected special prefix: sha512crypt");
    possible_types = [{"type": "sha512crypt", "confidence": "Certain", "info": "Unix SHA-512 password hash"}];
} elif str(hash_input).starts_with("$5$") {
    print("[*] Detected special prefix: sha256crypt");
    possible_types = [{"type": "sha256crypt", "confidence": "Certain", "info": "Unix SHA-256 password hash"}];
} elif str(hash_input).starts_with("0x") {
    print("[*] Detected prefix: 0x (possibly SQL or other hex format)");
} elif str(hash_input).starts_with("{") {
    print("[*] Detected prefix: { (possibly Java, MongoDB, or other format)");
}

print("");
print("=== Possible Hash Types ===");
print("");

for ht in possible_types {
    print(f"[{ht["confidence"]}] {ht["type"]}");
    print(f"     Info: {ht["info"]}");
    print("");
}

:: Hash pattern analysis
print("=== Pattern Analysis ===");
print("");

:: Check if hash matches common patterns
let all_same = true;
let first_char = str(hash_input)[0];
for c in hash_input {
    if c != first_char {
        all_same = false;
    }
}

if all_same {
    print("[!] WARNING: All characters are the same!");
    print("    This is likely a padding or dummy hash.");
}

:: Check for common password hashes
let test_passwords = [
    {"password": "12345", "md5": "827ccb0eea8a706c4c34a16891f84e7b"},
    {"password": "password", "md5": "5f4dcc3b5aa765d61d8327deb882cf99"},
    {"password": "admin", "md5": "21232f297a57a5a743894a0e4a801fc3"},
    {"password": "letmein", "md5": "0d107d09f5bbe40cade3de5c71e9e9b7"},
    {"password": "1234567890", "md5": "01d0b51d8e8a7d8e1e3c8d6e4c9c7e4a"}
];

print("");
print("[*] Common hash check:");
for tp in test_passwords {
    if hash_input == tp["md5"] {
        print(f"[!] MATCH FOUND: This hash matches '{tp["password"]}'");
    }
}
