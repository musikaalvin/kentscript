:: Test Phase 3 - HTTP Client

print("Test: http.get()");
let response = system_http_get("https://httpbin.org/get");
if response.status == 200 {
    print("✓ http.get() works - status: " + str(response.status));
} else {
    if response.error {
        print("⚠ http.get() error (network): " + response.error);
    }
}

print("\nTest: http.post()");
let post = system_http_post("https://httpbin.org/post", none, {"key": "value"});
if post.status == 200 {
    print("✓ http.post() works - status: " + str(post.status));
} else {
    if post.error {
        print("⚠ http.post() error (network): " + post.error);
    }
}

print("\n=== Phase 3 HTTP Complete ===");
