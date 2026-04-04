:: Test Control Flow & Functions

print("Test: Functions");
func add(a, b) {
    return a + b;
}
let result = add(5, 3);
if result == 8 {
    print("✓ functions work");
}

print("\nTest: Loops");
let sum = 0;
for i in range(5) {
    sum = sum + i;
}
if sum == 10 {
    print("✓ for loops work");
}

let count = 0;
while count < 3 {
    count = count + 1;
}
if count == 3 {
    print("✓ while loops work");
}

print("\nTest: Conditionals");
if true {
    print("✓ if works");
}

print("\n=== Control Flow Complete ===");
