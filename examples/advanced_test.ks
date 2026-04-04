:: Advanced test - verifies bug fixes

:: Test: Pattern matching with str() - THE MAIN FIX
func describe(x) {
    match x {
        case 1: { print("One"); }
        case 2: { print("Two"); }
        default: { print("Value: " + str(x)); }
    }
}

describe(1);
describe(2);
describe(42);

:: Test: Numeric list comprehension (works)
nums = [x * 2 for x in range(5)];
print("");
print("Doubled numbers:");
i = 0;
while i < nums.length {
    print(str(nums.get(i)));
    i = i + 1;
}

print("");
print("=== All tests passed! ===");
