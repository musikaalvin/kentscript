:: Test Phase 5.1 - String Operations

print("Test: String operations");
let s = "hello world";
if s.contains("world") {
    print("✓ contains works");
}
let upper = s.upper();
if upper == "HELLO WORLD" {
    print("✓ upper works");
}
let parts = s.split(" ");
if len(parts) == 2 {
    print("✓ split works");
}

print("\n=== Phase 5.1 Complete ===");
