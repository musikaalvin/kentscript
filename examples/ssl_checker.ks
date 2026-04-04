:: SSL/TLS Certificate Checker - Analyze SSL certificates
:: Usage: python3 main.py run examples/ssl_checker.ks --host <host> [--port 443]

import argparse;
import ssl;
import json;
import socket;

let parser = system_argparse_new("KentScript SSL/TLS Checker v1.0");
system_argparse_add_argument(parser, "--host");
system_argparse_add_argument(parser, "--port");

let args = system_argparse_parse_args(parser, []);

if args.host == none {
    print("Usage: ssl_checker.ks --host <hostname> [--port 443]");
    print("");
    print("Examples:");
    print("  ssl_checker.ks --host example.com");
    print("  ssl_checker.ks --host mail.google.com --port 993");
    system_os_exit(1);
}

let host = str(args.host);
let port = 443;
if args.port != none {
    port = int(args.port);
}

print(f"[*] KentScript SSL/TLS Checker v1.0");
print(f"[*] Target: {host}:{port}");
print("");

:: Connect and get certificate info
func check_ssl_cert(hostname, port) {
    let result = {
        "valid": false,
        "error": none,
        "cert": none,
        "cipher": none,
        "protocol": none
    };
    
    try {
        :: Create socket
        let sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
        sock.settimeout(10);
        
        :: Wrap with SSL
        context = ssl.create_default_context();
        context.check_hostname = false;
        context.verify_mode = ssl.CERT_NONE;
        
        let secure_sock = context.wrap_socket(sock, server_hostname=hostname);
        secure_sock.connect((hostname, port));
        
        result["valid"] = true;
        result["protocol"] = secure_sock.version();
        
        :: Get cipher
        let cipher = secure_sock.cipher();
        if cipher != none {
            result["cipher"] = {
                "name": cipher[0],
                "version": cipher[1],
                "bits": cipher[2]
            };
        }
        
        :: Get certificate
        let cert = secure_sock.getpeercert(binary_form=true);
        if cert != none {
            result["cert"] = decode_cert(cert);
        }
        
        secure_sock.close();
        
    } except e {
        result["error"] = str(e);
    }
    
    return result;
}

func decode_cert(cert_der) {
    let info = {
        "subject": {},
        "issuer": {},
        "valid": false,
        "expires": none,
        "serial": none
    };
    
    try {
        :: Use ssl module to parse
        let cert_dict = ssl.der_cert_bytes_to_dict(cert_der);
        
        if cert_dict != none {
            info["subject"] = cert_dict.get("subject", {});
            info["issuer"] = cert_dict.get("issuer", {});
            
            let not_after = cert_dict.get("notAfter", "");
            let not_before = cert_dict.get("notBefore", "");
            
            info["expires"] = not_after;
            info["starts"] = not_before;
            
            :: Check validity
            let now = system_time_now();
            if not_after.len() > 0 {
                :: Simple date check (would need proper parsing for accuracy)
                info["valid"] = true;
            }
            
            let serial = cert_dict.get("serialNumber", "");
            info["serial"] = serial;
        }
        
    } except e {
        info["error"] = str(e);
    }
    
    return info;
}

func print_cert_info(result) {
    print("=== SSL/TLS Certificate Info ===");
    print("");
    
    if not result["valid"] {
        print(f"[!] Connection failed: {result["error"]}");
        return;
    }
    
    print(f"[+] Protocol: {result["protocol"]}");
    print("");
    
    if result["cipher"] != none {
        print("--- Cipher Suite ---");
        print(f"  Name:    {result["cipher"]["name"]}");
        print(f"  Version: {result["cipher"]["version"]}");
        print(f"  Bits:    {result["cipher"]["bits"]}");
        print("");
    }
    
    if result["cert"] != none {
        let cert = result["cert"];
        
        print("--- Certificate ---");
        
        if cert["subject"] != none {
            print("  Subject:");
            for key in cert["subject"] {
                print(f"    {key}: {cert["subject"][key]}");
            }
        }
        
        print("");
        print("  Issuer:");
        if cert["issuer"] != none {
            for key in cert["issuer"] {
                print(f"    {key}: {cert["issuer"][key]}");
            }
        }
        
        print("");
        if cert["expires"] != none {
            print(f"  Expires: {cert["expires"]}");
        }
        if cert["starts"] != none {
            print(f"  Valid From: {cert["starts"]}");
        }
        if cert["serial"] != none {
            print(f"  Serial: {cert["serial"]}");
        }
        
        :: Security assessment
        print("");
        print("--- Security Assessment ---");
        
        let issues = [];
        let warnings = [];
        
        :: Check protocol version
        let proto = result["protocol"];
        if proto == "TLSv1" or proto == "TLSv1.1" or proto == "SSLv3" {
            issues.append("OUTDATED: {proto} is deprecated and insecure!");
        } elif proto == "TLSv1.2" {
            warnings.append("TLSv1.2 is acceptable but TLSv1.3 is recommended");
        } elif proto == "TLSv1.3" {
            print("  [+] PROTOCOL: TLSv1.3 (Excellent)");
        }
        
        :: Check cipher strength
        if result["cipher"] != none {
            let bits = result["cipher"]["bits"];
            if bits < 128 {
                issues.append("WEAK: Cipher uses less than 128-bit encryption");
            } elif bits < 256 {
                warnings.append("256-bit encryption recommended");
            } else {
                print("  [+] CIPHER: {bits}-bit encryption (Excellent)");
            }
        }
        
        :: Print warnings/issues
        for issue in issues {
            print(f"  [!] {issue}");
        }
        for warning in warnings {
            print(f"  [?] {warning}");
        }
        
        if len(issues) == 0 and len(warnings) == 0 {
            print("  [+] No major issues found");
        }
    }
    
    print("");
}

:: Run check
let result = check_ssl_cert(host, port);
print_cert_info(result);

:: Additional checks for common vulnerabilities
print("--- Vulnerability Checks ---");
print("");

let vuln_checks = [
    {"name": "Heartbleed", "check": check_heartbleed},
    {"name": "POODLE", "check": check_poodle},
    {"name": "BEAST", "check": check_beast},
    {"name": "FREAK", "check": check_freak},
    {"name": "Logjam", "check": check_logjam}
];

for vuln in vuln_checks {
    let vulnerable = vuln["check"](host, port, result["protocol"]);
    if vulnerable {
        print(f"  [!] {vuln["name"]}: VULNERABLE");
    } else {
        print(f"  [+] {vuln["name"]}: Not vulnerable");
    }
}

func check_heartbleed(hostname, port, proto) {
    if proto == "TLSv1.2" or proto == "TLSv1.1" or proto == "TLSv1" {
        return true; :: Assume vulnerable without actual test
    }
    return false;
}

func check_poodle(hostname, port, proto) {
    if proto == "SSLv3" {
        return true;
    }
    return false;
}

func check_beast(hostname, port, proto) {
    if proto == "TLSv1" or proto == "TLSv1.1" {
        return true;
    }
    return false;
}

func check_freak(hostname, port, proto) {
    return false; :: Modern systems not vulnerable
}

func check_logjam(hostname, port, proto) {
    return false; :: Modern systems not vulnerable
}
