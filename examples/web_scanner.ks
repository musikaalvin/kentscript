:: Web Directory Scanner - Path enumeration tool
:: Usage: python3 main.py run examples/web_scanner.ks --url http://target.com [--wordlist wordlist.txt]

import http;
import argparse;
import json;

let parser = system_argparse_new("KentScript Web Scanner v1.0");
system_argparse_add_argument(parser, "--url");
system_argparse_add_argument(parser, "--wordlist");
system_argparse_add_argument(parser, "--threads");
system_argparse_add_argument(parser, "--extensions");

let args = system_argparse_parse_args(parser, []);

if args.url == none {
    print("Usage: --url <target_url> [--wordlist paths.txt] [--extensions .php,.asp,.html]");
    print("");
    print("Example: --url http://example.com --wordlist /usr/share/wordlists/dirb/common.txt");
    system_os_exit(1);
}

let target_url = str(args.url);
let extensions = ".php,.html,.asp,.aspx,.jsp,.txt,.js,.cgi";

if args.extensions != none {
    extensions = str(args.extensions);
}

print(f"[*] KentScript Web Scanner v1.0");
print(f"[*] Target: {target_url}");
print(f"[*] Extensions: {extensions}");
print("");

:: Default common paths
let common_paths = [
    "/",
    "/admin",
    "/admin.php",
    "/administrator",
    "/login",
    "/login.php",
    "/wp-admin",
    "/wp-login.php",
    "/dashboard",
    "/cpanel",
    "/phpmyadmin",
    "/api",
    "/api/v1",
    "/api/v2",
    "/rest",
    "/graphql",
    "/server-status",
    "/.env",
    "/config",
    "/configuration",
    "/includes",
    "/uploads",
    "/images",
    "/backup",
    "/backups",
    "/database",
    "/sql",
    "/db",
    "/test",
    "/tests",
    "/debug",
    "/git",
    "/.git/config",
    "/svn",
    "/console",
    "/shell",
    "/terminal",
    "/webmin",
    "/manager",
    "/remote",
    "/file",
    "/files",
    "/documents",
    "/docs",
    "/readme",
    "/readme.md",
    "/robots.txt",
    "/sitemap.xml",
    "/crossdomain.xml",
    "/clientaccesspolicy.xml",
    "/security.txt",
    "/.well-known/security",
    "/.htaccess",
    "/.htpasswd"
];

let ext_list = system_string_split(extensions, ",");
let found_paths = [];
let checked = 0;
let total = len(common_paths);

if args.wordlist != none {
    let wordlist_content = system_file_read_text(str(args.wordlist));
    if wordlist_content != none {
        common_paths = system_string_split(wordlist_content, "\n");
        total = len(common_paths);
        print(f"[*] Loaded {total} paths from wordlist");
    }
}

print(f"[*] Scanning {total} paths...");
print("");

for path in common_paths {
    if str(path).len() == 0 {
        continue;
    }
    
    :: Try base path
    let url = target_url;
    if not str(path).starts_with("/") {
        url = url + "/" + path;
    } else {
        url = url + path;
    }
    
    let resp = http_get_safe(url);
    if resp != none {
        let status = resp.status;
        if status >= 200 and status < 400 {
            found_paths.append({"url": url, "status": status, "size": resp.size});
            print(f"[+] {status} - {url} ({resp.size} bytes)");
        } elif status >= 400 and status < 500 {
            :: Client error - path might exist but access denied
            if status == 401 or status == 403 {
                found_paths.append({"url": url, "status": status, "size": 0});
                print(f"[?] {status} - {url} (forbidden)");
            }
        }
    }
    
    :: Try with extensions
    for ext in ext_list {
        let ext_url = url + ext;
        let resp2 = http_get_safe(ext_url);
        if resp2 != none {
            let status2 = resp2.status;
            if status2 >= 200 and status2 < 400 {
                found_paths.append({"url": ext_url, "status": status2, "size": resp2.size});
                print(f"[+] {status2} - {ext_url} ({resp2.size} bytes)");
            }
        }
    }
    
    checked = checked + 1;
    if checked % 10 == 0 {
        print(f"[*] Progress: {checked}/{total}");
    }
}

print("");
print(f"[*] Scan Complete");
print(f"[*] Checked: {checked} paths");
print(f"[*] Found: {len(found_paths)} paths");
print("");

if len(found_paths) > 0 {
    print("=== Found Paths ===");
    for item in found_paths {
        print(f"  [{item["status"]}] {item["url"]}");
    }
}

func http_get_safe(url) {
    try {
        let resp = http.get(url, timeout=5);
        return resp;
    } except e {
        return none;
    }
}
