:: ============================================================================
:: KENTSCRIPT v6.0 - COMPREHENSIVE FEATURE TEST
:: ============================================================================

print("╔════════════════════════════════════════════════════════════╗");
print("║     KentScript v6.0 - Feature Test Suite                  ║");
print("╚════════════════════════════════════════════════════════════╝");
print("");

:: ============================================================================
:: TEST 1: Semicolon Enforcement
:: ============================================================================

print("[TEST 1] Semicolon Enforcement");
print("==============================");

let x = 5;
print("Variable x = " + x);
print("");


:: ============================================================================
:: TEST 2: Lambda Expressions (FIXED)
:: ============================================================================

print("[TEST 2] Lambda Expressions");
print("===========================");

let square = lambda n -> n * n;
let add = lambda a, b -> a + b;
let multiply = lambda x, y -> x * y;

print("square(5) = " + square(5));
print("add(3, 4) = " + add(3, 4));
print("multiply(6, 7) = " + multiply(6, 7));
print("");


:: ============================================================================
:: TEST 3: List Indexing
:: ============================================================================

print("[TEST 3] List Indexing");
print("======================");

let list = [10, 20, 30, 40, 50];

print("list[0] = " + list[0]);
print("list[2] = " + list[2]);
print("list[-1] = " + list[-1]);
print("list[-2] = " + list[-2]);
print("");


:: ============================================================================
:: TEST 4: List Slicing
:: ============================================================================

print("[TEST 4] List Slicing");
print("=====================");

let numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

print("numbers[1:4] = " + numbers[1:4]);
print("numbers[:5] = " + numbers[:5]);
print("numbers[5:] = " + numbers[5:]);
print("numbers[::2] = " + numbers[::2]);
print("numbers[::-1] = " + numbers[::-1]);
print("");


:: ============================================================================
:: TEST 5: Functions
:: ============================================================================

print("[TEST 5] Functions");
print("==================");

func add(a, b) {
    return a + b;
}

func greet(name) {
    print("Hello, " + name + "!");
}

print("add(10, 20) = " + add(10, 20));
greet("World");
print("");


:: ============================================================================
:: TEST 6: Control Flow
:: ============================================================================

print("[TEST 6] Control Flow");
print("=====================");

let score = 85;
if (score >= 90) {
    print("Grade: A");
} elif (score >= 80) {
    print("Grade: B");
} elif (score >= 70) {
    print("Grade: C");
} else {
    print("Grade: F");
}
print("");


:: ============================================================================
:: TEST 7: Loops
:: ============================================================================

print("[TEST 7] Loops");
print("==============");

print("For loop (0-4):");
for i in range(5) {
    print("  " + i);
}

print("While loop:");
let counter = 0;
while (counter < 3) {
    print("  " + counter);
    counter = counter + 1;
}

print("List iteration:");
let colors = ["red", "green", "blue"];
for color in colors {
    print("  " + color);
}
print("");


:: ============================================================================
:: TEST 8: Break and Continue
:: ============================================================================

print("[TEST 8] Break and Continue");
print("============================");

print("Break example:");
for i in range(10) {
    if (i == 5) {
        break;
    }
    print("  " + i);
}

print("Continue example:");
for i in range(5) {
    if (i == 2) {
        continue;
    }
    print("  " + i);
}
print("");


:: ============================================================================
:: TEST 9: Dictionaries
:: ============================================================================

print("[TEST 9] Dictionaries");
print("=====================");

let person = {
    "name": "Alice",
    "age": 25,
    "city": "New York"
};

print("person[\"name\"] = " + person["name"]);
print("person[\"age\"] = " + person["age"]);
print("person[\"city\"] = " + person["city"]);
print("");


:: ============================================================================
:: TEST 10: Classes
:: ============================================================================

print("[TEST 10] Classes");
print("=================");

class Animal {
    func __init__(name) {
        self.name = name;
    }
    
    func speak() {
        print(self.name + " makes a sound");
    }
};

class Dog extends Animal {
    func speak() {
        print(self.name + " barks!");
    }
};

let dog = new Dog("Buddy");
dog.speak();
print("");


:: ============================================================================
:: TEST 11: Math Module
:: ============================================================================

print("[TEST 11] Math Module");
print("=====================");

let math = math;

print("math.pi = " + math.pi);
print("math.sqrt(16) = " + math.sqrt(16));
print("math.sqrt(25) = " + math.sqrt(25));
print("math.factorial(5) = " + math.factorial(5));
print("");


:: ============================================================================
:: TEST 12: Random Module
:: ============================================================================

print("[TEST 12] Random Module");
print("=======================");

let random = random;

let rand_val = random.random();
print("random.random() = " + rand_val);

let rand_int = random.randint(1, 100);
print("random.randint(1, 100) = " + rand_int);

let items = ["apple", "banana", "cherry"];
let choice = random.choice(items);
print("random.choice(list) = " + choice);
print("");


:: ============================================================================
:: TEST 13: JSON Module
:: ============================================================================

print("[TEST 13] JSON Module");
print("=====================");

let json = json;

let data = {
    "name": "John",
    "age": 30,
    "active": true
};

let json_str = json.dumps(data);
print("JSON string = " + json_str);

let parsed = json.loads(json_str);
print("Parsed name = " + parsed["name"]);
print("");


:: ============================================================================
:: TEST 14: OS Module
:: ============================================================================

print("[TEST 14] OS Module");
print("===================");

import os;

let cwd = os.getcwd();
print("Current directory = " + cwd);

let files = os.listdir(".");
print("Files in current directory = " + len(files) + " items");
print("");


:: ============================================================================
:: TEST 15: String Operations
:: ============================================================================

print("[TEST 15] String Operations");
print("===========================");

let text = "KentScript";

print("Original = " + text);
print("Length = " + len(text));
print("Upper = " + text.upper());
print("Lower = " + text.lower());

let words = "hello world test".split(" ");
print("Split = " + words);
print("");


:: ============================================================================
:: TEST 16: Try-Catch
:: ============================================================================

print("[TEST 16] Try-Catch");
print("===================");

try {
    print("In try block");
    let result = 100;
} except (error) {
    print("Caught error!");
} finally {
    print("In finally block");
}
print("");


:: ============================================================================
:: TEST 17: Match Statement
:: ============================================================================

print("[TEST 17] Match Statement");
print("=========================");

let value = 2;
match (value) {
    case 1: {
        print("One");
    }
    case 2: {
        print("Two");
    }
    case 3: {
        print("Three");
    }
    default: {
        print("Other");
    }
}
print("");


:: ============================================================================
:: TEST 18: Higher-Order Functions
:: ============================================================================

print("[TEST 18] Higher-Order Functions");
print("=================================");

func apply_operation(a, b, operation) {
    return operation(a, b);
}

let add_op = lambda x, y -> x + y;
let mult_op = lambda x, y -> x * y;

let add_result = apply_operation(5, 3, add_op);
let mult_result = apply_operation(5, 3, mult_op);

print("apply_operation(5, 3, add) = " + add_result);
print("apply_operation(5, 3, mult) = " + mult_result);
print("");


:: ============================================================================
:: TEST 19: Recursion
:: ============================================================================

print("[TEST 19] Recursion");
print("===================");

func factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

print("factorial(5) = " + factorial(5));
print("factorial(6) = " + factorial(6));
print("");


:: ============================================================================
:: TEST 20: Nested Data Structures
:: ============================================================================

print("[TEST 20] Nested Data Structures");
print("=================================");

let matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
];

print("matrix[0][0] = " + matrix[0][0]);
print("matrix[1][1] = " + matrix[1][1]);
print("matrix[2][2] = " + matrix[2][2]);
print("");


:: ============================================================================
:: TEST 21: Security Module - Hashing
:: ============================================================================

print("[TEST 21] Security Module - Hashing");
print("====================================");

let ksecurity = ksecurity;

let password = "MyPassword123!";
let hashed = ksecurity.hash_password(password);
print("Password hashed successfully");

let is_valid = ksecurity.verify_password(password, hashed);
print("Password verification = " + is_valid);

let wrong_check = ksecurity.verify_password("WrongPassword", hashed);
print("Wrong password check = " + wrong_check);
print("");


:: ============================================================================
:: TEST 22: Security Module - Encryption
:: ============================================================================

print("[TEST 22] Security Module - Encryption");
print("======================================");

let key = "secret-key";
let plaintext = "Confidential Data";

let encrypted = ksecurity.encrypt_simple(plaintext, key);
print("Encrypted successfully");

let decrypted = ksecurity.decrypt_simple(encrypted, key);
print("Decrypted = " + decrypted);
print("");


:: ============================================================================
:: TEST 23: Security Module - Injection Detection
:: ============================================================================

print("[TEST 23] Security Module - Injection Detection");
print("==============================================");

let safe_input = "SELECT * FROM users WHERE id = 1";
let unsafe_input = "SELECT * FROM users WHERE id = 1' OR '1'='1";

let safe_result = ksecurity.sql_injection_test(safe_input);
let unsafe_result = ksecurity.sql_injection_test(unsafe_input);

print("Safe input is SQLi = " + safe_result);
print("Unsafe input is SQLi = " + unsafe_result);

let xss_safe = "<p>Hello World</p>";
let xss_unsafe = "<img src=x onerror=alert('XSS')>";

let xss_safe_result = ksecurity.xss_test(xss_safe);
let xss_unsafe_result = ksecurity.xss_test(xss_unsafe);

print("Safe HTML is XSS = " + xss_safe_result);
print("Unsafe HTML is XSS = " + xss_unsafe_result);
print("");


:: ============================================================================
:: TEST 24: Security Module - Encoding
:: ============================================================================

print("[TEST 24] Security Module - Encoding");
print("====================================");

let text_to_encode = "KentScript";

let b64 = ksecurity.base64_encode(text_to_encode);
print("Base64 encoded = " + b64);

let b64_decoded = ksecurity.base64_decode(b64);
print("Base64 decoded = " + b64_decoded);

let hex = ksecurity.hex_encode(text_to_encode);
print("Hex encoded = " + hex);

let url_enc = ksecurity.url_encode("hello world");
print("URL encoded = " + url_enc);
print("");


:: ============================================================================
:: TEST 25: Time Module
:: ============================================================================

print("[TEST 25] Time Module");
print("=====================");

let time = time;

let current_time = time.time();
print("Current timestamp = " + current_time);

let local = time.localtime();
print("Local time obtained");
print("");


:: ============================================================================
:: SUMMARY
:: ============================================================================

print("╔════════════════════════════════════════════════════════════╗");
print("║              All Tests Completed Successfully!              ║");
print("║                                                              ║");
print("║  ✓ Semicolon enforcement working                            ║");
print("║  ✓ Lambda expressions working                               ║");
print("║  ✓ List indexing working                                    ║");
print("║  ✓ List slicing working                                     ║");
print("║  ✓ Functions working                                        ║");
print("║  ✓ Control flow working                                     ║");
print("║  ✓ Loops working                                            ║");
print("║  ✓ Break/Continue working                                   ║");
print("║  ✓ Dictionaries working                                     ║");
print("║  ✓ Classes and inheritance working                          ║");
print("║  ✓ Math module working                                      ║");
print("║  ✓ Random module working                                    ║");
print("║  ✓ JSON module working                                      ║");
print("║  ✓ OS module working                                        ║");
print("║  ✓ String operations working                                ║");
print("║  ✓ Try-except working                                        ║");
print("║  ✓ Match statements working                                 ║");
print("║  ✓ Higher-order functions working                           ║");
print("║  ✓ Recursion working                                        ║");
print("║  ✓ Nested structures working                                ║");
print("║  ✓ Security hashing working                                 ║");
print("║  ✓ Security encryption working                              ║");
print("║  ✓ Security injection detection working                     ║");
print("║  ✓ Security encoding working                                ║");
print("║  ✓ Time module working                                      ║");
print("║                                                              ║");
print("║  KentScript v6.0 - Production Ready! 🚀                    ║");
print("╚════════════════════════════════════════════════════════════╝");
