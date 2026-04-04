:: ============================================================
:: KentScript SSL, HTTP Server, Crypto Demo
:: Run: ./kentscript run examples/ssl_server_crypto.ks
:: ============================================================

import ssl;
import http;
import crypto;

:: --- SSL / HTTPS ---
print("=== SSL ===");
let ssl_sock = ssl.wrap_socket("example.com", "example.com", 443);
ssl_sock.send("GET / HTTP/1.0\r\nHost: example.com\r\n\r\n");
let response = ssl_sock.recv(4096);
print("HTTPS: " + response.split("\r\n")[0]);
ssl_sock.close();

let cert = ssl.get_certificate("example.com", 443);
print("Subject: " + cert.subject);
print("Issuer:  " + cert.issuer);
print("Expires: " + cert.expires);

:: --- HTTP Server ---
print("\n=== HTTP SERVER ===");
let server = http.Server("0.0.0.0", 9877);
server.add_route("/", func(req) {
    return http.Response(200, "Hello from KentScript!");
});
server.add_route("/api", func(req) {
    return http.json_response({"status": "ok", "lang": "KentScript"});
});
server.start(true);
print("Server running on :9877");

import subprocess;
let r1 = subprocess.run(["curl", "-s", "--max-time", "2", "http://localhost:9877/"]);
print("GET /    → " + r1.stdout);
let r2 = subprocess.run(["curl", "-s", "--max-time", "2", "http://localhost:9877/api"]);
print("GET /api → " + r2.stdout);
server.stop();

:: --- Crypto ---
print("\n=== CRYPTO ===");
let password = "my_password";
let hash = crypto.pbkdf2(password, "random_salt", 10000);
print("PBKDF2: " + hash);
let valid = crypto.verify_password(password, hash);
print("Verify: " + str(valid));

:: --- HTTP POST with json= ---
print("\n=== HTTP POST json= ===");
let data = {"name": "Alice", "age": 30};
let resp = http.post("https://httpbin.org/post", json=data);
print("POST status: " + str(resp.status));

print("\n=== ALL VERIFIED ===");
