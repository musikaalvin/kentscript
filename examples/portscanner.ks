import "network" as net;
import "crypto" as cry

let target = "192.168.1.1"
let ports = [21, 22, 80, 443]

print("--- Scanning Target: " + target + " ---")

for p in ports {
    let result = net.scan(target, p); #:: High-level bridge to Python socket
    if result == "Open" {
        print("[+] Found Open Port: " + p)
    }
}
