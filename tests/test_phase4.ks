:: Test Phase 4 - Collections

print("Test: List operations");
let arr = [1, 2, 3];
if len(arr) == 3 {
    print("✓ list creation works");
}
arr.append(4);
if len(arr) == 4 {
    print("✓ list append works");
}

print("\nTest: Dict operations");
let d = {"key": "value"};
if d["key"] == "value" {
    print("✓ dict access works");
}

print("\n=== Phase 4 Complete ===");
