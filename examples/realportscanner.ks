:: KentScript v5.0 Professional Port Scanner
:: Uses the network stdlib for clean API

import "network";

func scan(target, port, timeout) {
    try {
        :: Create a TCP socket
        sock = network.Socket(network.AF_INET, network.SOCK_STREAM);
        sock.settimeout(timeout);
        
        :: Attempt connection - raises exception on failure
        sock.connect((target, port));
        sock.close();
        
        :: If we get here, connection succeeded
        return true;
    } catch e {
        return false;
    };
}

host = "127.0.0.1";
common_ports = [21, 22, 80, 443, 3306, 8080];

print("--- Starting Scan on " + host + " ---");

for port in common_ports {
    if (scan(host, port, 1.0)) {
        print("[+] SUCCESS: Port " + str(port) + " is OPEN");
    } else {
        print("[-] FAILED: Port " + str(port) + " is CLOSED");
    };
};
