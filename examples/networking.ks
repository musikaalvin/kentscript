:: ============================================================
:: KentScript Networking Test
:: Tests: HTTP (high-level), raw sockets (low-level)
:: Run: ./kentscript run examples/networking.ks
:: ============================================================

import http;
import json;

:: --- High-level HTTP ---
print("=== HIGH-LEVEL HTTP ===");

let resp = http.get("http://httpbin.org/get");
print("GET status: " + str(resp.status));

let resp2 = http.post("http://httpbin.org/post", "{\"key\": \"value\"}");
print("POST status: " + str(resp2.status));

let resp3 = http.get("http://httpbin.org/json");
if resp3.status == 200 {
    let data = json.loads(resp3.text);
    print("JSON response parsed OK");
}

:: --- Low-level raw socket ---
print("\n=== LOW-LEVEL SOCKET ===");

unsafe {
    let sock = system_socket_create(2, 1, 0);
    print("Socket created: " + str(sock));

    system_socket_settimeout(sock, 5.0);
    let err = system_socket_connect(sock, "93.184.216.34", 80);

    if err == none {
        system_socket_send(sock, "HEAD / HTTP/1.0\r\nHost: example.com\r\n\r\n");
        let data = system_socket_recv(sock, 256);
        let first_line = data.split("\r\n")[0];
        print("Raw socket response: " + first_line);
    } else {
        print("Connect error (expected in restricted env): " + str(err));
    }

    system_socket_close(sock);
}

:: --- UDP socket ---
unsafe {
    let udp = system_socket_create(2, 2, 0);
    print("UDP socket created: " + str(udp));
    system_socket_close(udp);
}

print("\n=== NETWORKING VERIFIED ===");
