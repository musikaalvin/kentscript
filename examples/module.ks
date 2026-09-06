MODULE_TYPE = "auxiliary";

import "network";

class PortScanner {
    func init() {
        self.info = {
            "Name": "Advanced Port Scanner",
            "Description": "Fast port scanner with service detection",
            "Author": "pyLord",
            "Version": "2.0",
            "Options": {
                "TARGET": ["127.0.0.1", true, "Target IP address or hostname"],
                "PORTS": ["1-1024", true, "Ports to scan (e.g., 80,443 or 1-1000)"],
                "TIMEOUT": ["1", false, "Connection timeout in seconds"],
                "THREADS": ["50", false, "Number of threads"],
                "SCAN_TYPE": ["connect", false, "Scan type: connect/banner"],
                "VERBOSE": ["false", false, "Show all attempts (true/false)"],
                "OUTPUT": ["", false, "Save results to file"]
            }
        };
        self.open_ports = [];
        self.scanned_count = 0;
        self.total_ports = 0;
    }

    func get_help() {
        return "Advanced Port Scanner\n=====================\nScans for open TCP ports with service detection.\n\nRequired:\n  set TARGET <ip_or_hostname>\n  set PORTS <port_range>\n\nPort formats:\n  Single port: 80\n  Multiple: 80,443,8080\n  Range: 1-1000\n  Common: common (scans top 1000 ports)\n  All: 1-65535";
    }

    func _parse_ports(port_str) {
        ports = [];
        common_ports = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5900, 8080, 8443];

        if (port_str.to_lower() == "common") {
            return common_ports;
        };

        parts = port_str.split(",");
        for part in parts {
            part = part.trim();
            if (part.contains("-")) {
                range_parts = part.split("-");
                start = int(range_parts[0]);
                end = int(range_parts[1]);
                let i = start;
                while (i <= end) {
                    ports.push(i);
                    i = i + 1;
                };
            } else {
                ports.push(int(part));
            };
        };

        ports.sort();
        return ports;
    }

    func _get_service_name(port) {
        common_services = {
            21: "FTP", 
            22: "SSH", 
            23: "Telnet", 
            25: "SMTP", 
            53: "DNS",
            80: "HTTP", 
            110: "POP3", 
            111: "RPC", 
            135: "MSRPC", 
            139: "NetBIOS",
            143: "IMAP", 
            443: "HTTPS", 
            445: "SMB", 
            993: "IMAPS", 
            995: "POP3S",
            1723: "PPTP", 
            3306: "MySQL", 
            3389: "RDP", 
            5900: "VNC",
            8080: "HTTP-Proxy", 
            8443: "HTTPS-Alt"
        };
        return common_services[port];
    }

    func _scan_port(target, port, timeout) {
        try {
            sock = network.Socket(network.AF_INET, network.SOCK_STREAM);
            sock.settimeout(timeout);
            sock.connect((target, port));
            sock.close();
            service = self._get_service_name(port);
            if (service == none) {
                service = "Unknown";
            };
            return [true, service];
        } catch e {
            return [false, ""];
        };
    }

    func execute() {
        target = self.info["Options"]["TARGET"][0];
        port_str = self.info["Options"]["PORTS"][0];
        timeout = int(self.info["Options"]["TIMEOUT"][0]);
        verbose = self.info["Options"]["VERBOSE"][0].to_lower() == "true";
        output_file = self.info["Options"]["OUTPUT"][0];

        ports = self._parse_ports(port_str);
        if (ports.length == 0) {
            return "[-] No valid ports specified";
        };

        self.total_ports = ports.length;

        print("[+] Starting port scan on " + target);
        print("[+] Ports to scan: " + str(self.total_ports));
        print("[+] Timeout: " + str(timeout) + "s");

        self.open_ports = [];
        self.scanned_count = 0;

        for port in ports {
            result = self._scan_port(target, port, timeout);
            if (result[0]) {
                self.open_ports.push([port, result[1]]);
                print("[+] Port " + str(port) + "/tcp OPEN - " + result[1]);
            } else if (verbose) {
                print("[-] Port " + str(port) + "/tcp closed");
            };
            self.scanned_count = self.scanned_count + 1;
        };

        if (output_file != "") {
            file = open(output_file, "w");
            file.write("Port scan results for " + target + "\n");
            file.write("Open ports: " + str(self.open_ports.length) + "\n\n");
            for item in self.open_ports {
                file.write(str(item[0]) + "/tcp - " + item[1] + "\n");
            };
            file.close();
        };

        return "[+] Scan completed. Open ports found: " + str(self.open_ports.length);
    }
}

scanner = new PortScanner();
print(scanner.get_help());
print("");
print(scanner.execute());
