:: ============================================================================
:: KENTSCRIPT v6.0 - CYBERSECURITY & PENTESTING EXAMPLES
:: ============================================================================

import security as ksecurity;

print("╔════════════════════════════════════════════════════════════╗");
print("║    KentScript Security & Pentesting Module Examples       ║");
print("╚════════════════════════════════════════════════════════════╝");
print("");

:: ============================================================================
:: 1. PASSWORD HASHING AND VERIFICATION
:: ============================================================================

print("[*] Password Hashing & Verification");
print("=====================================");

let password = "MySecurePassword123!";
let hashed = ksecurity.hash_password(password);
print("Original password:");
print(password);
print("");
print("Hashed (PBKDF2-SHA256):");
print(hashed);
print("");

let is_valid = ksecurity.verify_password(password, hashed);
print("Verification result:");
print(is_valid);
print("");

let wrong_password = "WrongPassword";
let wrong_check = ksecurity.verify_password(wrong_password, hashed);
print("Verifying wrong password:");
print(wrong_check);
print("");


:: ============================================================================
:: 2. ENCRYPTION AND DECRYPTION
:: ============================================================================

print("[*] Simple Encryption & Decryption");
print("===================================");

let key = "my-secret-key";
let plaintext = "Confidential Message";

let encrypted = ksecurity.encrypt_simple(plaintext, key);
print("Plaintext:");
print(plaintext);
print("");
print("Encrypted:");
print(encrypted);
print("");

let decrypted = ksecurity.decrypt_simple(encrypted, key);
print("Decrypted:");
print(decrypted);
print("");


:: ============================================================================
:: 3. CRYPTOGRAPHIC KEY GENERATION
:: ============================================================================

print("[*] Secure Key Generation");
print("==========================");

let key1 = ksecurity.generate_key(32);
let key2 = ksecurity.generate_key(64);

print("32-byte key (hex):");
print(key1);
print("");
print("64-byte key (hex):");
print(key2);
print("");


:: ============================================================================
:: 4. IP ADDRESS ANALYSIS
:: ============================================================================

print("[*] IP Address Analysis");
print("========================");

let test_ips = ["192.168.1.1", "8.8.8.8", "127.0.0.1", "224.0.0.1"];

for ip in test_ips {
    let info = ksecurity.ip_info(ip);
    if (info != none) {
        print("IP: " + ip);
        print("  Version: " + info["version"]);
        print("  Is Private: " + info["is_private"]);
        print("  Is Loopback: " + info["is_loopback"]);
        print("  Is Multicast: " + info["is_multicast"]);
        print("");
    };
};


:: ============================================================================
:: 5. SIMPLE PORT SCANNING
:: ============================================================================

print("[*] Port Scanning");
print("==================");

let target = "127.0.0.1";
print("Scanning common ports on " + target + ":");

let common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 3306, 5432];
let open_ports = [];

for port in common_ports {
    if (ksecurity.check_open_port(target, port)) {
        open_ports.append(port);
        print("  Port " + port + ": OPEN");
    };
};

print("Open ports found:");
print(open_ports);
print("");


:: ============================================================================
:: 6. DNS OPERATIONS
:: ============================================================================

print("[*] DNS Lookup & Reverse DNS");
print("============================");

let hostname = "google.com";
let ip = ksecurity.dns_lookup(hostname);
print("DNS lookup for " + hostname + ":");
print(ip);
print("");

:: Reverse DNS
let reverse_host = ksecurity.reverse_dns("8.8.8.8");
if (reverse_host != none) {
    print("Reverse DNS for 8.8.8.8:");
    print(reverse_host);
    print("");
};


:: ============================================================================
:: 7. SSL/TLS CERTIFICATE CHECKING
:: ============================================================================

print("[*] SSL/TLS Certificate Information");
print("====================================");

let cert_info = ksecurity.check_ssl("google.com", 443);
if (cert_info != none) {
    print("SSL certificate for google.com:");
    print("Subject:");
    print(cert_info["subject"]);
    print("");
    print("Issuer:");
    print(cert_info["issuer"]);
    print("");
};


:: ============================================================================
:: 8. HTTP HEADERS ENUMERATION
:: ============================================================================

print("[*] HTTP Headers Enumeration");
print("=============================");

let headers = ksecurity.get_headers("http://example.com");
if (headers != none) {
    print("HTTP Headers for example.com:");
    for header in headers {
        print("  " + header + ": " + headers[header]);
    };
    print("");
};


:: ============================================================================
:: 9. SUBDOMAIN ENUMERATION
:: ============================================================================

print("[*] Subdomain Enumeration");
print("==========================");

let domain = "example.com";
let subdomains = ksecurity.find_subdomains(domain);
print("Found subdomains for " + domain + ":");
for subdomain_pair in subdomains {
    print("  " + subdomain_pair[0] + " -> " + subdomain_pair[1]);
};
print("");


:: ============================================================================
:: 10. INJECTION DETECTION
:: ============================================================================

print("[*] Injection Vulnerability Testing");
print("====================================");

:: SQL Injection Detection
print("SQL Injection Detection:");
let sql_tests = [
    "SELECT * FROM users WHERE id = 1",
    "SELECT * FROM users WHERE id = 1' OR '1'='1",
    "SELECT * FROM users; DROP TABLE users; --"
];

for test in sql_tests {
    let is_vulnerable = ksecurity.sql_injection_test(test);
    print("  Input: " + test);
    print("  Vulnerable: " + str(is_vulnerable));
    print("");
};

:: Command Injection Detection
print("Command Injection Detection:");
let cmd_tests = [
    "ls -la",
    "ls -la | grep .txt",
    "rm -rf /; echo 'hacked'"
];

for test in cmd_tests {
    let is_vulnerable = ksecurity.command_injection_test(test);
    print("  Input: " + test);
    print("  Vulnerable: " + str(is_vulnerable));
    print("");
};

:: XSS Detection
print("XSS Injection Detection:");
let xss_tests = [
    "<p>Hello World</p>",
    "<img src=x onerror=alert('XSS')>",
    "<script>alert('XSS')</script>"
];

for test in xss_tests {
    let is_vulnerable = ksecurity.xss_test(test);
    print("  Input: " + test);
    print("  Vulnerable: " + str(is_vulnerable));
    print("");
};


:: ============================================================================
:: 11. ENCODING/DECODING OPERATIONS
:: ============================================================================

print("[*] Encoding/Decoding");
print("=====================");

let text = "KentScript Security";

let base64_encoded = ksecurity.base64_encode(text);
print("Original: " + text);
print("Base64 encoded: " + base64_encoded);
print("");

let base64_decoded = ksecurity.base64_decode(base64_encoded);
print("Base64 decoded: " + base64_decoded);
print("");

let hex_encoded = ksecurity.hex_encode(text);
print("Hex encoded: " + hex_encoded);
print("");

let url_encoded = ksecurity.url_encode(text);
print("URL encoded: " + url_encoded);
print("");

let url_decoded = ksecurity.url_decode(url_encoded);
print("URL decoded: " + url_decoded);
print("");


:: ============================================================================
:: 12. COMMON WORDLISTS
:: ============================================================================

print("[*] Common Wordlists & Payloads");
print("================================");

print("Common Ports:");
print(ksecurity.common_ports);
print("");

print("Common Passwords:");
print(ksecurity.common_passwords);
print("");

print("SQL Injection Payloads:");
print(ksecurity.sql_injection_payloads);
print("");

print("XSS Payloads:");
print(ksecurity.xss_payloads);
print("");


:: ============================================================================
:: 13. PRACTICAL SECURITY UTILITY: PASSWORD STRENGTH CHECKER
:: ============================================================================

print("[*] Password Strength Checker");
print("=============================");

func check_password_strength(password) {
    let strength = 0;
    let feedback = [];
    
    if (len(password) >= 8) {
        strength = strength + 1;
    } else {
        feedback.append("Password too short (min 8 chars)");
    };
    
    let has_upper = false;
    let has_lower = false;
    let has_digit = false;
    let has_special = false;
    
    for c in password {
        if (c >= 'A' && c <= 'Z') {
            has_upper = true;
        };
        if (c >= 'a' && c <= 'z') {
            has_lower = true;
        };
        if (c >= '0' && c <= '9') {
            has_digit = true;
        };
        if (c == '!' || c == '@' || c == '#' || c == '$') {
            has_special = true;
        };
    };
    
    if (has_upper) { strength = strength + 1; } else { feedback.append("Missing uppercase"); };
    if (has_lower) { strength = strength + 1; } else { feedback.append("Missing lowercase"); };
    if (has_digit) { strength = strength + 1; } else { feedback.append("Missing numbers"); };
    if (has_special) { strength = strength + 1; } else { feedback.append("Missing special chars"); };
    
    let strength_text = "";
    if (strength < 2) { strength_text = "Very Weak"; };
    if (strength >= 2 && strength < 3) { strength_text = "Weak"; };
    if (strength >= 3 && strength < 4) { strength_text = "Fair"; };
    if (strength >= 4 && strength < 5) { strength_text = "Good"; };
    if (strength >= 5) { strength_text = "Excellent"; };
    
    return {
        "strength": strength_text,
        "score": strength,
        "feedback": feedback
    };
};

let pwd1 = "abc";
let pwd2 = "MyPass123!";
let pwd3 = "SuperSecure@Pass123!";

print("Password: " + pwd1);
print(check_password_strength(pwd1));
print("");

print("Password: " + pwd2);
print(check_password_strength(pwd2));
print("");

print("Password: " + pwd3);
print(check_password_strength(pwd3));
print("");


:: ============================================================================
:: 14. CREDENTIAL VALIDATION SYSTEM
:: ============================================================================

print("[*] Credential Validation System");
print("=================================");

let users_db = {
    "admin": "admin_hash_here",
    "user1": "user1_hash_here"
};

func validate_credentials(username, password) {
    if (username in users_db) {
        return true;
    } else {
        return false;
    };
};

print("Checking user 'admin':");
print(validate_credentials("admin", "anypass"));
print("");

print("Checking user 'hacker':");
print(validate_credentials("hacker", "anypass"));
print("");


print("╔════════════════════════════════════════════════════════════╗");
print("║         Security Examples Complete                         ║");
print("║  Use responsibly and only on systems you have permission  ║");
print("╚════════════════════════════════════════════════════════════╝");
