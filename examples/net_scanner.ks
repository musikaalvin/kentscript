:: Network Port Scanner - Professional security tool
:: Usage: python3 main.py run examples/net_scanner.ks [target] [start_port] [end_port]

import argparse;
import network;
import json;

let parser = system_argparse_new("KentScript Network Scanner v1.0");
system_argparse_add_argument(parser, "--target");
system_argparse_add_argument(parser, "--start");
system_argparse_add_argument(parser, "--end");
system_argparse_add_argument(parser, "--timeout");
system_argparse_add_argument(parser, "--threads");

let args = system_argparse_parse_args(parser, []);

let target = "127.0.0.1";
let start_port = 1;
let end_port = 1024;
let timeout = 0.5;
let max_threads = 50;

if hasattr(args, "target") {
    target = args.target;
}
if hasattr(args, "start") {
    start_port = int(args.start);
}
if hasattr(args, "end") {
    end_port = int(args.end);
}
if hasattr(args, "timeout") {
    timeout = float(args.timeout);
}

print(f"[*] KentScript Network Scanner");
print(f"[*] Target: {target}");
print(f"[*] Ports: {start_port} - {end_port}");
print(f"[*] Timeout: {timeout}s");
print("");

:: Common services
let services = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    1521: "Oracle",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    6379: "Redis",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
    27017: "MongoDB"
};

let open_ports = [];
let closed_ports = 0;
let filtered_ports = 0;

print("[*] Scanning...");

for port in range(start_port, end_port + 1) {
    let sock = network.socket_create(network.AF_INET, network.SOCK_STREAM, 0);
    if sock == none {
        continue;
    }
    
    :: Try to connect with timeout
    let result = network.socket_connect_timeout(sock, target, port, timeout);
    
    if result == 0 {
        let service = "unknown";
        if services[port] != none {
            service = services[port];
        }
        
        let banner = "";
        if port == 22 {
            banner = try_read_banner(sock, timeout);
        } elif port == 80 or port == 8080 {
            network.socket_send(sock, "HEAD / HTTP/1.0\r\n\r\n", 0);
            banner = try_read_banner(sock, timeout);
        } elif port == 443 or port == 8443 {
            banner = try_read_banner(sock, timeout);
        }
        
        let port_info = {
            "port": port,
            "service": service,
            "banner": banner
        };
        open_ports.append(port_info);
        print(f"[+] Port {port}/tcp OPEN - {service} {banner}");
    } else {
        closed_ports = closed_ports + 1;
    }
    
    network.socket_close(sock);
}

print("");
print(f"[*] Scan Complete");
print(f"[*] Open Ports: {len(open_ports)}");
print(f"[*] Closed Ports: {closed_ports}");
print("");

if len(open_ports) > 0 {
    print("=== Open Ports Summary ===");
    for info in open_ports {
        print(f"  {info["port"]}/tcp - {info["service"]}");
    }
}

func try_read_banner(sock, timeout) {
    return "";
}
