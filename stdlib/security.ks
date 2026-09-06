:: ============================================================
:: KentScript Security Module
:: ============================================================
:: Provides security utilities for hardening KentScript applications
:: Version: 1.0.0
:: Date: 2026-02-19
:: ============================================================

:: ============================================================
:: Path Validation
:: ============================================================

:: Check for path traversal attacks (../, absolute paths)
import error;

func is_safe_path(path) {
    if path == none || path == "" {
        return false;
    }
    
    if path.contains("../") {
        return false;
    }
    
    if path.contains("..\\") {
        return false;
    }
    
    return true;
}

:: Validate and normalize a path
func validate_path(path, base_dir) {
    if path == none || path == "" {
        raise new SecurityError("Path cannot be empty");
    }
    
    if !is_safe_path(path) {
        raise new SecurityError("Path traversal detected: " + path);
    }
    
    let normalized = path.replace("\\", "/");
    return normalized;
}

:: Resolve symbolic links and normalize path
func resolve_path(path) {
    if path == none || path == "" {
        return "";
    }
    return path;
}

:: ============================================================
:: Command Sanitization
:: ============================================================

:: Check for command injection attempts
func is_safe_command(command) {
    if command == none || command == "" {
        return false;
    }
    
    let dangerous_patterns = [
        ";",
        "&&",
        "||",
        "|",
        "`",
        "$(", 
        "\n",
        "\r",
        ">",
        ">>",
        "<",
        "<<"
    ];
    
    for pattern in dangerous_patterns {
        if command.contains(pattern) {
            return false;
        }
    }
    
    return true;
}

:: Sanitize command arguments
func sanitize_command_arg(arg) {
    if arg == none {
        return "";
    }
    
    let sanitized = str(arg);
    
    sanitized = sanitized.replace(";", "");
    sanitized = sanitized.replace("&", "");
    sanitized = sanitized.replace("|", "");
    sanitized = sanitized.replace("`", "");
    sanitized = sanitized.replace("$", "");
    sanitized = sanitized.replace("'", "");
    sanitized = sanitized.replace("\"", "");
    
    return sanitized;
}

:: Validate command against whitelist
func validate_command(command, allowed_commands) {
    if command == none || command == "" {
        raise new SecurityError("Command cannot be empty");
    }
    
    if allowed_commands != none {
        let base_cmd = command.split(" ")[0];
        if !allowed_commands.contains(base_cmd) {
            raise new SecurityError("Command not in whitelist: " + base_cmd);
        }
    }
    
    if !is_safe_command(command) {
        raise new SecurityError("Potential command injection detected: " + command);
    }
    
    return true;
}

:: ============================================================
:: Input Sanitization
:: ============================================================

:: Sanitize string input
func sanitize_string(input, max_length) {
    if input == none {
        return "";
    }
    
    let sanitized = str(input);
    
    if max_length != none && sanitized.length > max_length {
        sanitized = sanitized.slice(0, max_length);
    }
    
    return sanitized;
}

:: Remove dangerous characters from input
func sanitize_html(input) {
    if input == none {
        return "";
    }
    
    let sanitized = str(input);
    
    sanitized = sanitized.replace("&", "&amp;");
    sanitized = sanitized.replace("<", "&lt;");
    sanitized = sanitized.replace(">", "&gt;");
    sanitized = sanitized.replace("\"", "&quot;");
    sanitized = sanitized.replace("'", "&#x27;");
    sanitized = sanitized.replace("/", "&#x2F;");
    
    return sanitized;
}

:: Sanitize for SQL (basic - use parameterized queries instead)
func sanitize_sql(input) {
    if input == none {
        return "";
    }
    
    let sanitized = str(input);
    
    sanitized = sanitized.replace("'", "''");
    sanitized = sanitized.replace(";", "");
    sanitized = sanitized.replace("--", "");
    sanitized = sanitized.replace("/*", "");
    sanitized = sanitized.replace("*/", "");
    
    return sanitized;
}

:: ============================================================
:: File Security
:: ============================================================

:: Check if path is within allowed directories
func is_path_in_directory(path, allowed_dirs) {
    let normalized = path.replace("\\", "/");
    
    for dir in allowed_dirs {
        let dir_normalized = dir.replace("\\", "/");
        if normalized.startswith(dir_normalized + "/") || normalized == dir_normalized {
            return true;
        }
    }
    
    return false;
}

:: Validate file extension
func is_safe_extension(filename, allowed_extensions) {
    if filename == none || filename == "" {
        return false;
    }
    
    if allowed_extensions == none || allowed_extensions.length == 0 {
        return true;
    }
    
    let lower_name = filename.to_lower();
    
    for ext in allowed_extensions {
        let ext_lower = ext.to_lower();
        if ext_lower.startswith(".") {
            if lower_name.endswith(ext_lower) {
                return true;
            }
        } else {
            if lower_name.endswith("." + ext_lower) {
                return true;
            }
        }
    }
    
    return false;
}

:: Block dangerous file extensions
func is_dangerous_extension(filename) {
    let dangerous = [
        ".exe", ".bat", ".cmd", ".com", ".msi", ".dll",
        ".sh", ".bash", ".zsh", ".fish",
        ".ps1", ".bat", ".cmd",
        ".jar", ".class", ".py", ".rb", ".php", ".pl",
        ".html", ".htm", ".js", ".css", ".svg",
        ".xml", ".xsl", ".xslt",
        ".conf", ".config", ".ini", ".yaml", ".yml",
        ".pem", ".key", ".crt", ".cer",
        ".sql", ".db", ".sqlite",
        ".zip", ".tar", ".gz", ".rar", ".7z"
    ];
    
    return !is_safe_extension(filename, dangerous);
}

:: ============================================================
:: Network Security
:: ============================================================

:: Validate IP address
func is_valid_ip(ip) {
    if ip == none || ip == "" {
        return false;
    }
    
    let parts = ip.split(".");
    if parts.length != 4 {
        return false;
    }
    
    for part in parts {
        let num = system_builtin_int(part);
        if num == 0 && part != "0" || num < 0 || num > 255 {
            return false;
        }
    }
    
    return true;
}

:: Check if IP is private
func is_private_ip(ip) {
    if !is_valid_ip(ip) {
        return false;
    }
    
    let parts = ip.split(".").map(lambda x: system_builtin_int(x));
    
    if parts[0] == 10 {
        return true;
    }
    
    if parts[0] == 172 && parts[1] >= 16 && parts[1] <= 31 {
        return true;
    }
    
    if parts[0] == 192 && parts[1] == 168 {
        return true;
    }
    
    if parts[0] == 127 {
        return true;
    }
    
    return false;
}

:: Validate port number
func is_valid_port(port) {
    if port == none {
        return false;
    }
    
    let num = system_builtin_int(port);
    if num == none {
        return false;
    }
    
    return num >= 1 && num <= 65535;
}

:: Validate hostname
func is_valid_hostname(hostname) {
    if hostname == none || hostname == "" {
        return false;
    }
    
    if hostname.length > 253 {
        return false;
    }
    
    let labels = hostname.split(".");
    
    for label in labels {
        if label.length == 0 || label.length > 63 {
            return false;
        }
        
        if !label.match("^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$") {
            return false;
        }
    }
    
    return true;
}

:: ============================================================
:: Password Security
:: ============================================================

:: Check password strength
func check_password_strength(password) {
    if password == none || password == "" {
        return {"valid": false, "score": 0, "issues": ["Password cannot be empty"]};
    }
    
    let issues = [];
    let score = 0;
    
    if password.length >= 8 {
        score = score + 1;
    } else {
        issues.push("Password should be at least 8 characters");
    }
    
    if password.length >= 12 {
        score = score + 1;
    }
    
    if password.match("[a-z]") {
        score = score + 1;
    } else {
        issues.push("Password should contain lowercase letters");
    }
    
    if password.match("[A-Z]") {
        score = score + 1;
    } else {
        issues.push("Password should contain uppercase letters");
    }
    
    if password.match("[0-9]") {
        score = score + 1;
    } else {
        issues.push("Password should contain numbers");
    }
    
    if password.match("[!@#$%^&*(),.?\":{}|<>]") {
        score = score + 1;
    } else {
        issues.push("Password should contain special characters");
    }
    
    return {
        "valid": score >= 4,
        "score": score,
        "issues": issues
    };
}

:: Generate random password
func generate_password(length, options) {
    if length == none {
        length = 16;
    }
    
    let use_lower = options != none && options["lower"] != false;
    let use_upper = options != none && options["upper"] != false;
    let use_numbers = options != none && options["numbers"] != false;
    let use_special = options != none && options["special"] != false;
    
    let chars = "";
    let required = [];
    
    if use_lower {
        chars = chars + "abcdefghijklmnopqrstuvwxyz";
        required.push("abcdefghijklmnopqrstuvwxyz");
    }
    if use_upper {
        chars = chars + "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        required.push("ABCDEFGHIJKLMNOPQRSTUVWXYZ");
    }
    if use_numbers {
        chars = chars + "0123456789";
        required.push("0123456789");
    }
    if use_special {
        chars = chars + "!@#$%^&*()_+-=[]{}|;:,.<>?";
        required.push("!@#$%^&*()_+-=[]{}|;:,.<>?");
    }
    
    if chars == "" {
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    }
    
    let password = "";
    
    for req in required {
        if password.length < length {
            password = password + req[system_builtin_int(math_floor(math_random() * req.length))];
        }
    }
    
    while password.length < length {
        password = password + chars[system_builtin_int(math_floor(math_random() * chars.length))];
    }
    
    return password;
}

:: ============================================================
:: Hashing
:: ============================================================

:: Simple hash function (not cryptographically secure - use crypto.ks for real hashing)
func simple_hash(input) {
    let str_input = str(input);
    let hash = 0;
    
    for i in range(str_input.length) {
        let char = str_input.char_code_at(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    
    return hash;
}

:: ============================================================
:: Rate Limiting
:: ============================================================

let _rate_limit_store = {};

:: Check rate limit
func check_rate_limit(key, max_requests, window_seconds) {
    if key == none || key == "" {
        return true;
    }
    
    let now = system_time_now();
    
    if _rate_limit_store[key] == none {
        _rate_limit_store[key] = {
            "count": 1,
            "reset": now + window_seconds
        };
        return true;
    }
    
    let record = _rate_limit_store[key];
    
    if now > record["reset"] {
        record["count"] = 1;
        record["reset"] = now + window_seconds;
        return true;
    }
    
    if record["count"] >= max_requests {
        return false;
    }
    
    record["count"] = record["count"] + 1;
    return true;
}

:: Get rate limit info
func get_rate_limit_info(key) {
    if key == none || _rate_limit_store[key] == none {
        return none;
    }
    
    return _rate_limit_store[key];
}

:: Reset rate limit
func reset_rate_limit(key) {
    if key != none && _rate_limit_store[key] != none {
        _rate_limit_store[key] = none;
    }
}

:: ============================================================
:: Encryption Helpers (basic)
:: ============================================================

:: XOR encrypt/decrypt (simple - not secure)
func xor_encrypt(data, key) {
    let data_str = str(data);
    let key_str = str(key);
    let result = "";
    
    for i in range(data_str.length) {
        let char_code = data_str.char_code_at(i);
        let key_char = key_str[i % key_str.length];
        let encrypted = char_code ^ key_char.char_code_at(0);
        result = result + chr(encrypted);
    }
    
    return result;
}

:: ============================================================
:: Password Hashing (PBKDF2-SHA256)
:: ============================================================

func hash_password(password) {
    let salt_bytes = system_crypto_random_bytes(32);
    let salt = system_crypto_pbkdf2(password, salt_bytes, 100000, 32);
    return salt_bytes + ":" + salt;
}

func verify_password(password, stored_hash) {
    let parts = stored_hash.split(":");
    if parts.length != 2 {
        return false;
    }
    let salt = parts[0];
    let expected_hash = parts[1];
    let computed_hash = system_crypto_pbkdf2(password, salt, 100000, 32);
    return computed_hash == expected_hash;
}

:: ============================================================
:: Simple Encryption/Decryption (XOR-based)
:: ============================================================

func encrypt_simple(plaintext, key) {
    let result = "";
    let key_len = key.length;
    
    for i in range(plaintext.length) {
        let char_code = ord(plaintext[i]);
        let key_char = key[i % key_len];
        let key_code = ord(key_char);
        let encrypted = char_code ^ key_code;
        let hex_str = str(system_builtin_hex(encrypted));
        if hex_str.length > 2 {
            hex_str = hex_str.substring(2);
        }
        if hex_str.length == 1 {
            hex_str = "0" + hex_str;
        }
        result = result + hex_str;
    }
    
    return result;
}

func decrypt_simple(encrypted, key) {
    let result = "";
    let key_len = key.length;
    let i = 0;
    let pos = 0;
    
    while pos < encrypted.length {
        if pos + 2 > encrypted.length {
            break;
        }
        let hex_byte = encrypted.substring(pos, pos + 2);
        let char_code = system_builtin_int(hex_byte, 16);
        let key_char = key[i % key_len];
        let key_code = ord(key_char);
        let decrypted = char_code ^ key_code;
        result = result + chr(decrypted);
        pos = pos + 2;
        i = i + 1;
    }
    
    return result;
}

:: ============================================================
:: Key Generation
:: ============================================================

func generate_key(length) {
    return system_crypto_random_bytes(length);
}

:: ============================================================
:: IP Address Analysis
:: ============================================================

func ip_info(ip) {
    if ip == none || ip == "" {
        return none;
    }
    
    let version = "Unknown";
    if is_valid_ip(ip) {
        version = "IPv4";
    } else if ip.contains(":") {
        version = "IPv6";
    }
    
    let is_private = is_private_ip(ip);
    let is_loopback = ip == "127.0.0.1" || ip == "::1" || ip.substring(0, 4) == "127.";
    let first_byte = system_builtin_int(ip.split(".")[0]);
    let is_multicast = first_byte >= 224 && first_byte <= 239;
    
    return {
        "version": version,
        "is_private": is_private ? "true" : "false",
        "is_loopback": is_loopback ? "true" : "false",
        "is_multicast": is_multicast ? "true" : "false"
    };
}

:: ============================================================
:: Port Scanning
:: ============================================================

func check_open_port(host, port, timeout) {
    if timeout == none {
        timeout = 1.0;
    }
    
    try {
        let sock = system_socket_create(2, 1, 0);
        system_socket_settimeout(sock, timeout);
        let result = system_socket_connect(sock, host, port);
        system_socket_close(sock);
        return result == 0 || result == none;
    } except (e) {
        return false;
    }
}

:: ============================================================
:: DNS Operations
:: ============================================================

func dns_lookup(hostname) {
    try {
        return system_socket_gethostbyname(hostname);
    } except (e) {
        return none;
    }
}

func reverse_dns(ip) {
    try {
        return system_socket_gethostbyaddr(ip);
    } except (e) {
        return none;
    }
}

:: ============================================================
:: SSL Certificate Information
:: ============================================================

func check_ssl(host, port) {
    try {
        let ctx = system_ssl_create_context(2);
        let sock = system_ssl_connect(ctx, host, port);
        let cert = system_ssl_socket_getpeercert(sock);
        system_ssl_close(sock);
        
        if cert != none {
            return {
                "subject": str(cert),
                "issuer": "SSL Certificate"
            };
        }
        return none;
    } except (e) {
        return none;
    }
}

:: ============================================================
:: HTTP Headers
:: ============================================================

func get_headers(url) {
    try {
        let response = system_http_request("HEAD", url, none, none, 5);
        if response != none && response["error"] == none {
            return response["headers"];
        }
        return none;
    } except (e) {
        return none;
    }
}

:: ============================================================
:: Subdomain Enumeration
:: ============================================================

let _common_subdomains = [
    "www", "mail", "ftp", "admin", "blog", "dev", "test", "api",
    "secure", "shop", "pay", "cdn", "static", "assets", "images",
    "video", "media", "download", "upload", "app", "mobile", "m",
    "staging", "demo", "beta", "alpha", "git", "svn", "ci", "jenkins"
];

func find_subdomains(domain) {
    let results = [];
    
    for subdomain in _common_subdomains {
        let hostname = subdomain + "." + domain;
        
        try {
            let addr = system_socket_gethostbyname(hostname);
            results.push([hostname, addr]);
    } except (e) {
        }
    }
    
    return results;
}

:: ============================================================
:: Injection Detection
:: ============================================================

func sql_injection_test(input) {
    let patterns = [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "' OR '1'='1' /*",
        "'; DROP TABLE",
        "'; DELETE FROM",
        "' UNION SELECT",
        "' UNION ALL SELECT",
        "1=1",
        "1' ORDER BY",
        "admin' --",
        "admin' #"
    ];
    
    let lower_input = input.to_lower();
    
    for pattern in patterns {
        if lower_input.contains(pattern.to_lower()) {
            return true;
        }
    }
    
    return false;
}

func command_injection_test(input) {
    let patterns = [
        ";",
        "&&",
        "||",
        "|",
        "`",
        "$(", 
        "${",
        "\n",
        "\r",
        ">",
        ">>",
        "<"
    ];
    
    for pattern in patterns {
        if input.contains(pattern) {
            return true;
        }
    }
    
    return false;
}

func xss_test(input) {
    let patterns = [
        "<script",
        "</script>",
        "javascript:",
        "onerror=",
        "onload=",
        "onclick=",
        "onmouseover=",
        "alert(",
        "eval(",
        "document.cookie",
        "<img",
        "<iframe",
        "<svg"
    ];
    
    let lower_input = input.to_lower();
    
    for pattern in patterns {
        if lower_input.contains(pattern.to_lower()) {
            return true;
        }
    }
    
    return false;
}

:: ============================================================
:: Encoding/Decoding
:: ============================================================

func base64_encode(text) {
    return system_crypto_base64_encode(text);
}

func base64_decode(text) {
    return system_crypto_base64_decode(text);
}

func hex_encode(text) {
    let result = "";
    for i in range(text.length) {
        result = result + system_builtin_hex(ord(text[i]));
    }
    return result;
}

func url_encode(text) {
    let encoded = "";
    for i in range(text.length) {
        let c = text[i];
        if (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.' || c == '~' {
            encoded = encoded + c;
        } else {
            let hex_val = system_builtin_hex(ord(c));
            encoded = encoded + "%" + hex_val.substring(2).to_upper();
        }
    }
    return encoded;
}

func url_decode(text) {
    let result = "";
    let i = 0;
    while i < text.length {
        let c = text[i];
        if c == '%' && i + 2 < text.length {
            let hex = text.substring(i + 1, i + 3);
            if hex.length == 2 {
                let char_code = system_builtin_int(hex, 16);
                result = result + chr(char_code);
                i = i + 3;
            } else {
                result = result + c;
                i = i + 1;
            }
        } else if c == '+' {
            result = result + " ";
            i = i + 1;
        } else {
            result = result + c;
            i = i + 1;
        }
    }
    return result;
}

:: ============================================================
:: Wordlists and Payloads
:: ============================================================

let common_ports = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
    993, 995, 1723, 3306, 3389, 5900, 8080, 8443
];

let common_passwords = [
    "123456", "password", "12345678", "qwerty", "123456789",
    "12345", "1234", "111111", "1234567", "dragon",
    "123123", "baseball", "abc123", "football", "monkey",
    "letmein", "shadow", "master", "666666", "qwertyuiop"
];

let sql_injection_payloads = [
    "' OR '1'='1",
    "' OR '1'='1' --",
    "' OR '1'='1' /*",
    "'; DROP TABLE users; --",
    "1' ORDER BY 1--",
    "' UNION SELECT NULL--",
    "admin' --",
    "1' AND '1'='1",
    "'; EXEC xp_cmdshell",
    "1; SELECT * FROM"
];

let xss_payloads = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "<svg/onload=alert('XSS')>",
    "javascript:alert('XSS')",
    "<iframe src=javascript:alert('XSS')>",
    "<body onload=alert('XSS')>",
    "<input onfocus=alert('XSS') autofocus>",
    "'-alert('XSS')-'",
    "\"><script>alert('XSS')</script>"
];

:: ============================================================
:: Exports
:: ============================================================

:: Path security
let validate_path = validate_path;
let is_safe_path = is_safe_path;
let resolve_path = resolve_path;

:: Command security
let is_safe_command = is_safe_command;
let sanitize_command_arg = sanitize_command_arg;
let validate_command = validate_command;

:: Input sanitization
let sanitize_string = sanitize_string;
let sanitize_html = sanitize_html;
let sanitize_sql = sanitize_sql;

:: File security
let is_path_in_directory = is_path_in_directory;
let is_safe_extension = is_safe_extension;
let is_dangerous_extension = is_dangerous_extension;

:: Network security
let is_valid_ip = is_valid_ip;
let is_private_ip = is_private_ip;
let is_valid_port = is_valid_port;
let is_valid_hostname = is_valid_hostname;

:: Password security
let check_password_strength = check_password_strength;
let generate_password = generate_password;

:: Hashing
let simple_hash = simple_hash;

:: Rate limiting
let check_rate_limit = check_rate_limit;
let get_rate_limit_info = get_rate_limit_info;
let reset_rate_limit = reset_rate_limit;

:: Encryption
let xor_encrypt = xor_encrypt;

:: Password Hashing
let hash_password = hash_password;
let verify_password = verify_password;

:: Simple Encryption
let encrypt_simple = encrypt_simple;
let decrypt_simple = decrypt_simple;

:: Key Generation
let generate_key = generate_key;

:: IP Analysis
let ip_info = ip_info;

:: Port Scanning
let check_open_port = check_open_port;

:: DNS Operations
let dns_lookup = dns_lookup;
let reverse_dns = reverse_dns;

:: SSL
let check_ssl = check_ssl;

:: HTTP Headers
let get_headers = get_headers;

:: Subdomain Enumeration
let find_subdomains = find_subdomains;

:: Injection Detection
let sql_injection_test = sql_injection_test;
let command_injection_test = command_injection_test;
let xss_test = xss_test;

:: Encoding/Decoding
let base64_encode = base64_encode;
let base64_decode = base64_decode;
let hex_encode = hex_encode;
let url_encode = url_encode;
let url_decode = url_decode;

:: Wordlists
let common_ports = common_ports;
let common_passwords = common_passwords;
let sql_injection_payloads = sql_injection_payloads;
let xss_payloads = xss_payloads;
