:: Test Operators

print("Test: Comparison operators");
if 5 > 3 {
    print("✓ > works");
}
if 3 < 5 {
    print("✓ < works");
}
if 5 >= 5 {
    print("✓ >= works");
}
if 3 <= 3 {
    print("✓ <= works");
}
if 5 == 5 {
    print("✓ == works");
}
if 5 != 3 {
    print("✓ != works");
}

print("\nTest: Logical operators");
if true and true {
    print("✓ and works");
}
if true or false {
    print("✓ or works");
}
if not false {
    print("✓ not works");
}

print("\n=== Operators Complete ===");
