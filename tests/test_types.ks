:: Test Type System

print("Test: Basic types");
let i = 42;
let f = 3.14;
let s = "hello";
let b = true;
let n = none;

if type(i) == "int" {
    print("✓ int type works");
}
if type(s) == "str" {
    print("✓ str type works");
}
if type(b) == "bool" {
    print("✓ bool type works");
}

print("\n=== Types Complete ===");
