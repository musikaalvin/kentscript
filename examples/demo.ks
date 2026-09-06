:: KentScript Basic Demo
:: This example demonstrates features that work in native compilation mode

print("=== KentScript Basics ===");
print("Pattern matching, functions, control flow, and unsafe operations");

print("\n--- Functions ---");

func add(a, b) {
    return a + b;
}

func multiply(a, b) {
    return a * b;
}

print("add(5, 3) = " + str(add(5, 3)));
print("multiply(4, 7) = " + str(multiply(4, 7)));

print("\n--- Control Flow ---");

let x = 10;
if x > 0 {
    print("x is positive");
} elif x < 0 {
    print("x is negative");
} else {
    print("x is zero");
}

print("\n--- Pattern Matching ---");

func describe_number(n) {
    match n {
        case 90: {
            print("Grade 90: A");
        }
        case 80: {
            print("Grade 80: B");
        }
        case 70: {
            print("Grade 70: C");
        }
        default: {
            print("Grade: F");
        }
    }
}

describe_number(90);
describe_number(85);
describe_number(72);
describe_number(50);

print("\n--- Unsafe/Memory Operations ---");

unsafe {
    let ptr = malloc(64);
    print("Allocated 64 bytes at: " + str(ptr));
    ptr_write(ptr, 0xDEADBEEF);
    let val = ptr_read(ptr, 8);
    print("Read value: 0x" + str(val, 16));
    free(ptr);
    print("Memory freed");
}

print("\n=== Demo Complete ===");
