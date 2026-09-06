:: KentScript Basics - Python-style Syntax
:: This file demonstrates features with clean Python-style syntax

print("=== KentScript Basics ===");

print("\n--- Variables ---");

let x = 42;
let pi = 3.14159;
let name = "KentScript";
let is_true = true;

print("x = " + str(x));
print("pi = " + str(pi));
print("is_true = " + str(is_true));

print("\n--- Functions ---");

func add(a, b) {
    return a + b;
}

func factorial(n) {
    if n <= 1 {
        return 1;
    }
    return n * factorial(n - 1);
}

print("add(5, 3) = " + str(add(5, 3)));
print("factorial(5) = " + str(factorial(5)));

print("\n--- Control Flow ---");

let test_val = 10;
if test_val > 0 {
    print("test_val is positive");
} elif test_val < 0 {
    print("test_val is negative");
} else {
    print("test_val is zero");
}

let i = 0;
while i < 3 {
    print("while loop: " + str(i));
    i = i + 1;
}

print("for loop:");
for j in range(0, 3) {
    print("  j = " + str(j));
}

print("\n--- Classes (Python-style) ---");

class Calculator {
    func init() {
        self.value = 0;
    }
    
    func add(self, n) {
        self.value = self.value + n;
    }
    
    func get_value(self) {
        return self.value;
    }
}

calc = Calculator();
calc.add(5);
calc.add(3);
result = calc.get_value();
print("Calculator result: " + str(result));

print("\n--- Pattern Matching ---");

func http_status(code) {
    return match code {
        case 200: {
            return "OK";
        }
        case 404: {
            return "Not Found";
        }
        case 500: {
            return "Server Error";
        }
        default: {
            return "Unknown";
        }
    };
}

print("200: " + http_status(200));
print("404: " + http_status(404));
print("999: " + http_status(999));

print("\n--- Unsafe/Memory Operations ---");

unsafe {
    let ptr = malloc(64);
    print("Allocated memory at: " + str(ptr));
    ptr_write(ptr, 0xDEADBEEF);
    let val = ptr_read(ptr, 8);
    print("Value written: 0xDEADBEEF");
    print("Value read: 0x" + str(val, 16));
    free(ptr);
    print("Memory freed");
}

print("\n=== All Examples Completed ===");
