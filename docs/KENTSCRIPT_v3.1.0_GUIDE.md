# KentScript Language Reference
## Complete Guide — v3.1.0

**Created: 1st March 2026** | **Version 3.1.0** | **By pyLord (Uganda)**

---

# About KentScript

## Language Overview

KentScript is a systems programming language written in Python (~161,000 lines). It combines Python-like syntax with C-like low-level features, making it ideal for both high-level application development and low-level systems programming.

## Author & Origin

- **Created by**: pyLord (Musika Alvin)
- **Location**: Uganda
- **Created on**: 1st March 2026
- **Version**: 3.1.0 (Codename: Baremetal)

## GitHub Repository

- **Main Repository**: https://github.com/musikaalvin/kentscript
- **Author Profile**: https://github.com/musikaalvin

## License

**MIT License** - Free to use, modify, and distribute.

## Goals & Philosophy

KentScript was created with these goals:
1. **Simplicity** - Python-like syntax that's easy to learn
2. **Power** - Low-level features like pointers, syscalls, inline assembly
3. **Safety** - Optional borrow checker and type system
4. **Performance** - Native compilation via C transpiler
5. **Accessibility** - No complex toolchain, runs on Python

## Features at a Glance

| Feature | Status | Description |
|---------|--------|-------------|
| Interpreter | ✅ Full | Complete stdlib support |
| C Transpiler | ✅ Working | Native binary compilation |
| REPL | ✅ Full | Interactive development |
| GUI | ✅ Interpreter | Built-in GUI toolkit |
| Package Manager | ✅ | kpm for module management |
| Low-Level | ✅ | malloc, syscall, hardware I/O |
| JIT | ✅ x86-64 | Hotspot compilation |

## Why KentScript?

- If you know Python → KentScript feels familiar with added systems features
- If you know C → KentScript gives you safer memory management
- If you know Rust → KentScript is simpler with similar low-level control
- If you know Go → KentScript has more flexible syntax

## Getting Help

- **Documentation**: This guide
- **REPL Help**: Type `help` in REPL
- **Version Info**: `./kentscript --version`
- **GitHub Issues**: Report bugs on GitHub

---

# Table of Contents

1. [Getting Started](#1-getting-started)
2. [Your First Program](#2-your-first-program)
3. [Variables & Constants](#3-variables--constants)
4. [Data Types](#4-data-types)
5. [Operators](#5-operators)
6. [Control Flow](#6-control-flow)
7. [Functions](#7-functions)
8. [Classes & Objects](#8-classes--objects)
9. [Structs & Enums](#9-structs--enums)
10. [Pattern Matching](#10-pattern-matching)
11. [Error Handling](#11-error-handling)
12. [Collections](#12-collections)
13. [Comprehensions](#13-comprehensions)
14. [Lambdas & Higher-Order Functions](#14-lambdas--higher-order-functions)
15. [Async/Await](#15-asyncawait)
16. [Unsafe Blocks - Low-Level Programming](#16-unsafe-blocks---low-level-programming)
17. [Modules & Imports](#17-modules--imports)
18. [Standard Library - Built-in Functions](#18-standard-library---built-in-functions)
19. [System Functions - C Runtime](#19-system-functions---c-runtime)
20. [GUI Programming](#20-gui-programming)
21. [Common Errors & Troubleshooting](#21-common-errors--troubleshooting)
22. [REPL & Interactive Development](#22-repl--interactive-development)
23. [VSCodium IDE Extension](#23-vscodium-ide-extension)
24. [Quick Reference](#24-quick-reference)

---

# 1. Getting Started

## Installation

```bash
# Install optional dependencies for full functionality
pip install -r requirements-build.txt

# Make executable
chmod +x kentscript

# Verify installation
./kentscript --version
```

## Running Programs

KentScript has multiple execution modes:

```bash
# Interpreter mode (full stdlib, all features work)
./kentscript run file.ks

# Compile to native binary (limited stdlib, low-level features work)
./kentscript build file.ks -O3
./binary_name

# Interactive REPL
./kentscript repl

# Debug mode
./kentscript debug file.ks

# JIT mode
./kentscript jit file.ks
```

## Build Options

```bash
# Optimization levels
./kentscript build file.ks -O0    # No optimization
./kentscript build file.ks -O1    # Basic
./kentscript build file.ks -O2    # Standard (default)
./kentscript build file.ks -O3    # Aggressive (recommended)

# Keep generated C file
./kentscript build file.ks -O3 --keep-c

# Custom output name
./kentscript build file.ks -o myprogram
```

---

# 2. Your First Program

```kentscript
:: Hello World program
:: KentScript v3.1.0

func main() {
    print("Hello, World!");
}

main();
```

**Save as:** `hello.ks`

**Run:** `./kentscript run hello.ks`

## Program Structure

Every KentScript program can have:
- Comments (:: or /* */)
- Import statements
- Function definitions
- Class/struct/enum definitions
- Main entry point

---

# 3. Variables & Constants

## Variable Declaration

```kentscript
:: Immutable variable - cannot be reassigned
let name = "KentScript";
let version = 3.1;
let count = 42;

:: Mutable variable - can be reassigned
mut counter = 0;
counter = counter + 1;  :: counter is now 1

:: Constants - compile-time values
const PI = 3.14159;
const MAX_CONNECTIONS = 1000;
const API_URL = "https://api.example.com";
```

## Type Annotations

```kentscript
:: Explicit type annotations
let age: i64 = 25;
let price: f64 = 19.99;
let is_active: bool = true;
let name: str = "KentScript";
let char_code: char = 'A';

:: Mutable with type
mut data: ptr = 0;
mut buffer: str = "";
```

---

# 4. Data Types

## Primitive Types

### Signed Integers
```kentscript
let i8_val: i8 = 127;
let i16_val: i16 = 32767;
let i32_val: i32 = 2147483647;
let i64_val: i64 = 9223372036854775807;

:: Type alias
let int = 42;  :: defaults to i64
```

### Unsigned Integers
```kentscript
let u8_val: u8 = 255;
let u16_val: u16 = 65535;
let u32_val: u32 = 4294967295;
let u64_val: u64 = 18446744073709551615;

:: Type alias
let uint = 42;  :: defaults to u64
```

### Floating Point
```kentscript
let f32_val: f32 = 3.14159;
let f64_val: f64 = 3.141592653589793;

:: Type alias
let float = 3.14;   :: defaults to f64
let double = 3.14;  :: f64
```

### Other Types
```kentscript
:: Boolean
let true_val: bool = true;
let false_val: bool = false;

:: String
let str_val: str = "Hello";
let string_val: string = "World";

:: Character
let char_val: char = 'A';
let char_byte: char = '\x41';

:: Pointer
let ptr_val: ptr = 0x1000;
let null_ptr: ptr = null;

:: Void (for functions that return nothing)
let result: void;

:: Any (dynamic type)
let any_val: any = 42;
any_val = "now a string";
```

## Type Conversion

```kentscript
let n = 42;
let s = str(n);           :: "42"
let i = int("123");       :: 123
let f = float("3.14");    :: 3.14
let b = bool(1);          :: true
let c = char(65);         :: 'A'
```

---

# 5. Operators

## Arithmetic Operators
```kentscript
let a = 10 + 5;    :: Addition: 15
let b = 10 - 5;    :: Subtraction: 5
let c = 10 * 5;    :: Multiplication: 50
let d = 10 / 5;    :: Division: 2
let e = 10 % 3;    :: Modulo: 1

:: Unary
let f = -10;       :: Negative: -10
let g = +5;        :: Positive: 5

:: Increment/Decrement (in unsafe or expressions)
let x = 5;
:: x++ or ++x not supported, use:
x = x + 1;
```

## Enhanced Assignment
```kentscript
let num = 10;
num += 5;    :: num = 15
num -= 3;    :: num = 12
num *= 2;    :: num = 24
num /= 4;    :: num = 6
num %= 5;    :: num = 1
```

## Comparison Operators
```kentscript
let eq = 10 == 10;    :: true
let ne = 10 != 5;     :: true
let lt = 10 < 20;     :: true
let gt = 10 > 5;      :: true
let le = 10 <= 10;    :: true
let ge = 10 >= 10;    :: true
```

## Logical Operators
```kentscript
let and_result = true and false;   :: false
let or_result = true or false;     :: true
let not_result = not true;         :: false

:: Short-circuit
let result = (x > 0) and (10 / x > 2);  :: safe division
```

## Bitwise Operators
```kentscript
let and = 0b1100 & 0b1010;   :: 0b1000 (8)
let or = 0b1100 | 0b1010;    :: 0b1110 (14)
let xor = 0b1100 ^ 0b1010;   :: 0b0110 (6)
let not = ~0b1100;           :: ...11110011

let shl = 0b1100 << 2;       :: 0b110000 (48)
let shr = 0b1100 >> 2;       :: 0b11 (3)
```

## Ternary Operator
```kentscript
let age = 18;
let status = age >= 18 ? "Adult" : "Minor";

let result = x > 0 ? x : -x;  :: absolute value
```

## Range Operator
```kentscript
let r = 0..5;        :: range 0,1,2,3,4 (not including 5)
let arr = [1..10];   :: array from 1 to 9
```

---

# 6. Control Flow

## If/Elif/Else

```kentscript
let score = 85;

if score >= 90 {
    print("Grade: A");
} elif score >= 80 {
    print("Grade: B");
} elif score >= 70 {
    print("Grade: C");
} else {
    print("Grade: F");
}
```

## While Loop

```kentscript
let count = 0;

while count < 5 {
    print("Count: " + str(count));
    count = count + 1;
}
```

## For Loop

```kentscript
:: Simple range
for i in range(5) {
    print(i);  :: 0,1,2,3,4
}

:: Range with start and end
for i in range(2, 6) {
    print(i);  :: 2,3,4,5
}

:: Range with step
for i in range(0, 10, 2) {
    print(i);  :: 0,2,4,6,8
}

:: Iterate over array
let arr = [10, 20, 30];
for val in arr {
    print(val);
}

:: With index
for i, val in arr {
    print("Index " + str(i) + ": " + str(val));
}
```

## Break and Continue

```kentscript
let i = 0;
while true {
    i = i + 1;
    if i == 3 {
        continue;  :: skip iteration
    }
    if i > 5 {
        break;     :: exit loop
    }
    print(i);
}
:: Prints: 1, 2, 4, 5
```

## Match (Pattern Matching)

```kentscript
let day = 3;

let day_name = match day {
    case 1: { "Monday" }
    case 2: { "Tuesday" }
    case 3: { "Wednesday" }
    case 4: { "Thursday" }
    case 5: { "Friday" }
    case 6: { "Saturday" }
    case 7: { "Sunday" }
    default: { "Invalid" }
};
print(day_name);  :: Wednesday
```

### Match with Multiple Conditions
```kentscript
let status = 404;

let message = match status {
    case 200: { "OK" }
    case 201: { "Created" }
    case 204: { "No Content" }
    case 400: { "Bad Request" }
    case 401: { "Unauthorized" }
    case 403: { "Forbidden" }
    case 404: { "Not Found" }
    case 500: { "Internal Server Error" }
    default: { "Unknown Status: " + str(status) }
};
```

### Match on Different Types
```kentscript
:: Match on string
let cmd = "start";

match cmd {
    case "start": { print("Starting..."); }
    case "stop": { print("Stopping..."); }
    case "restart": { print("Restarting..."); }
    default: { print("Unknown command"); }
}
```

---

# 7. Functions

## Basic Function

```kentscript
func greet(name) {
    return "Hello, " + name + "!";
}

print(greet("KentScript"));  :: Hello, KentScript!
```

## Function with Type Annotations

```kentscript
func add(a: i64, b: i64) -> i64 {
    return a + b;
}

func divide(a: f64, b: f64) -> f64 {
    if b == 0.0 {
        return 0.0;
    }
    return a / b;
}
```

## Multiple Return Values

```kentscript
func divmod(a: i64, b: i64) -> (i64, i64) {
    return (a / b, a % b);
}

let (quotient, remainder) = divmod(10, 3);
print(quotient);   :: 3
print(remainder); :: 1
```

## Default Parameters

```kentscript
func greet(name: str = "World") -> str {
    return "Hello, " + name + "!";
}

print(greet());         :: Hello, World!
print(greet("Kent"));  :: Hello, Kent!
```

## Variadic Functions

```kentscript
func sum(*args) -> i64 {
    let total = 0;
    for n in args {
        total = total + n;
    }
    return total;
}

print(sum(1, 2, 3));       :: 6
print(sum(1, 2, 3, 4, 5)); :: 15
```

## Recursion

```kentscript
func factorial(n: i64) -> i64 {
    if n <= 1 {
        return 1;
    }
    return n * factorial(n - 1);
}

print(factorial(5));  :: 120
```

## Nested Functions

```kentscript
func outer(x: i64) -> i64 {
    func inner(y: i64) -> i64 {
        return y * 2;
    }
    return inner(x) + 1;
}

print(outer(5));  :: 11
```

## Lambda Functions

```kentscript
let double = func(x: i64) -> i64 { return x * 2; };
print(double(5));  :: 10
```

---

# 8. Classes & Objects

## Basic Class

```kentscript
class Calculator {
    :: Constructor
    func init() {
        self.value = 0;
    }
    
    :: Instance method
    func add(self, n: i64) {
        self.value = self.value + n;
    }
    
    :: Getter method
    func get_value(self) -> i64 {
        return self.value;
    }
    
    :: Setter method  
    func set_value(self, n: i64) {
        self.value = n;
    }
}

let calc = Calculator();
calc.add(10);
calc.add(5);
print(calc.get_value());  :: 15
```

## Class with Init Parameters

```kentscript
class Point {
    func init(self, x: i64, y: i64) {
        self.x = x;
        self.y = y;
    }
    
    func distance(self) -> i64 {
        return self.x * self.x + self.y * self.y;
    }
    
    func to_string(self) -> str {
        return "Point(" + str(self.x) + ", " + str(self.y) + ")";
    }
}

let p = Point(3, 4);
print(p.distance());   :: 25
print(p.to_string()); :: Point(3, 4)
```

## Class with Inheritance

```kentscript
class Animal {
    func init(self, name: str) {
        self.name = name;
    }
    
    func speak(self) -> str {
        return "...";
    }
}

class Dog < Animal {
    func speak(self) -> str {
        return self.name + " says Woof!";
    }
}

class Cat < Animal {
    func speak(self) -> str {
        return self.name + " says Meow!";
    }
}

let dog = Dog("Buddy");
let cat = Cat("Whiskers");

print(dog.speak());  :: Buddy says Woof!
print(cat.speak());  :: Whiskers says Meow!
```

## Class Methods and Static Methods

```kentscript
class Math {
    :: Static method (no self)
    static func square(x: i64) -> i64 {
        return x * x;
    }
    
    static func abs(x: i64) -> i64 {
        if x < 0 {
            return -x;
        }
        return x;
    }
}

print(Math.square(5));  :: 25
print(Math.abs(-10));   :: 10
```

## Class Variables

```kentscript
class Counter {
    :: Class variable (shared by all instances)
    static mut count = 0;
    
    func init() {
        Counter.count = Counter.count + 1;
    }
}

let c1 = Counter();
let c2 = Counter();
let c3 = Counter();
print(Counter.count);  :: 3
```

---

# 9. Structs & Enums

## Struct Definition

```kentscript
struct Point {
    x: i64,
    y: i64,
}

struct Rectangle {
    origin: Point,
    width: i64,
    height: i64,
}

:: Create instance
let p = Point { x: 10, y: 20 };
print(p.x);  :: 10
print(p.y);  :: 20

:: Nested struct
let rect = Rectangle {
    origin: Point { x: 0, y: 0 },
    width: 100,
    height: 50
};
print(rect.width);  :: 100
```

## Enum Definition

```kentscript
enum Color {
    Red,
    Green,
    Blue,
    Yellow,
}

let c = Color.Red;

:: Use in match
match c {
    case Color.Red: { print("Red"); }
    case Color.Green: { print("Green"); }
    case Color.Blue: { print("Blue"); }
    case Color.Yellow: { print("Yellow"); }
}

:: Enum with values
enum HTTPStatus {
    OK = 200,
    NotFound = 404,
    ServerError = 500,
}

let status = HTTPStatus.OK;
print(status == HTTPStatus.OK);  :: true
```

## Enum with Methods

```kentscript
enum Result {
    Success,
    Error,
}

struct MyResult {
    status: Result,
    message: str,
}

func process() -> MyResult {
    let success = true;
    if success {
        return MyResult { status: Result.Success, message: "Done" };
    } else {
        return MyResult { status: Result.Error, message: "Failed" };
    }
}

let r = process();
match r.status {
    case Result.Success: { print("Success: " + r.message); }
    case Result.Error: { print("Error: " + r.message); }
}
```

---

# 10. Pattern Matching

## Basic Match

```kentscript
let value = 2;

match value {
    case 1: { print("one"); }
    case 2: { print("two"); }
    case 3: { print("three"); }
    default: { print("other"); }
}
```

## Match with Guards

```kentscript
let num = 15;

match num {
    case n if n < 0: { print("negative"); }
    case n if n == 0: { print("zero"); }
    case n if n > 0 and n < 10: { print("small positive"); }
    case n if n >= 10: { print("large positive"); }
}
```

## Match on Collections

```kentscript
let pair = (10, "hello");

match pair {
    case (a, b): { print(str(a) + ": " + b); }
}

let data = {"type": "user", "name": "John"};

match data {
    case {"type": "user", "name": n}: { print("User: " + n); }
    case {"type": "admin", "name": n}: { print("Admin: " + n); }
    default: { print("Unknown"); }
}
```

## Match Expression (Return Value)

```kentscript
func get_description(code: i64) -> str {
    return match code {
        case 200: { "OK - Success" }
        case 201: { "Created" }
        case 204: { "No Content" }
        case 400: { "Bad Request" }
        case 401: { "Unauthorized" }
        case 403: { "Forbidden" }
        case 404: { "Not Found" }
        case 500: { "Internal Server Error" }
        default: { "Unknown status code: " + str(code) }
    };
}
```

---

# 11. Error Handling

## Try/Except/Finally

```kentscript
print("=== Error Handling ===");

:: Basic try/except
try {
    let result = 10 / 0;
} except Exception as e {
    print("Caught: " + str(e));
}

:: Multiple except blocks
try {
    let arr = [1, 2, 3];
    let val = arr[10];  :: IndexError
} except IndexError as e {
    print("Index error: " + str(e));
} except Exception as e {
    print("Other error: " + str(e));
}

:: Finally block (always executes)
try {
    print("Try block");
} except {
    print("Exception caught");
} finally {
    print("Finally - cleanup here");
}
```

## Raise/Throw Custom Errors

```kentscript
func validate_age(age: i64) {
    if age < 0 {
        raise "Age cannot be negative";
    }
    if age > 150 {
        raise "Age is unrealistic";
    }
    print("Valid age: " + str(age));
}

try {
    validate_age(-5);
} catch Error as e {
    print("Validation failed: " + str(e));
}
```

## Working with Result Type

```kentscript
func safe_divide(a: f64, b: f64) -> f64 {
    if b == 0.0 {
        return 0.0;  :: Or could raise error
    }
    return a / b;
}

let result = safe_divide(10.0, 0.0);
if result == 0.0 {
    print("Division by zero handled");
}
```

---

# 12. Collections

## Arrays

```kentscript
:: Create array
let arr = [1, 2, 3, 4, 5];

:: Access elements
print(arr[0]);     :: 1
print(arr[4]);     :: 5
print(arr[-1]);    :: 5 (last element)
print(arr[-2]);    :: 4 (second to last)

:: Array length
print(len(arr));   :: 5

:: Modify array
arr.append(6);
arr.insert(0, 0);
arr.remove(3);
let popped = arr.pop();

:: Slicing
let slice = arr[1:4];    :: [2, 3, 4]
let first_three = arr[:3]; :: [1, 2, 3]
let last_two = arr[-2:];  :: [4, 5]
```

## Dictionaries

```kentscript
:: Create dictionary
let person = {
    "name": "John",
    "age": 30,
    "city": "NYC"
};

:: Access values
print(person["name"]);  :: John
print(person["age"]);    :: 30

:: Modify
person["age"] = 31;
person["email"] = "john@example.com";

:: Delete
person.delete("city");

:: Check key exists
if "name" in person {
    print("Name exists");
}

:: Get keys and values
let keys_arr = keys(person);
let values_arr = values(person);
let items_arr = items(person);
```

## Tuples

```kentscript
:: Create tuple
let t = (1, "hello", true);

:: Access
print(t[0]);    :: 1
print(t[1]);    :: hello

:: Tuple unpacking
let (a, b, c) = t;
print(a);  :: 1
print(b);  :: hello

:: Return multiple values from function
func get_stats() -> (i64, i64, f64) {
    return (100, 5, 2.5);
}

let (min, max, avg) = get_stats();
```

---

# 13. Comprehensions

## List Comprehension

```kentscript
:: Basic - square numbers
let squares = [x ** 2 for x in range(10)];
print(squares);  :: [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

:: With filter - even numbers
let evens = [x for x in range(20) if x % 2 == 0];
print(evens);    :: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

:: Complex - double even, triple odd
let transformed = [x * 2 if x % 2 == 0 else x * 3 for x in range(5)];
print(transformed); :: [0, 3, 4, 9, 8]

:: Nested comprehension
let matrix = [[i * j for j in range(3)] for i in range(3)];
print(matrix);  :: [[0,0,0], [0,1,2], [0,2,4]]
```

## Dict Comprehension

```kentscript
:: Basic
let squares_dict = {x: x ** 2 for x in range(5)};
print(squares_dict);  :: {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}

:: From array of tuples
let pairs = [("a", 1), ("b", 2), ("c", 3)];
let dict_from_pairs = {k: v for (k, v) in pairs};
print(dict_from_pairs);  :: {"a": 1, "b": 2, "c": 3}

:: Filter
let data = {"a": 1, "b": 2, "c": 3, "d": 4};
let filtered = {k: v for (k, v) in data if v > 2};
print(filtered);  :: {"c": 3, "d": 4}
```

---

# 14. Lambdas & Higher-Order Functions

## Lambda Functions

```kentscript
:: Basic lambda
let double = (x) -> x * 2;
print(double(5));  :: 10

:: Multi-argument
let add = (a, b) -> a + b;
print(add(3, 7));  :: 10

:: With type hints
let multiply = (a: i64, b: i64) -> i64 -> a * b;
```

## Map

```kentscript
let numbers = [1, 2, 3, 4, 5];

:: Double all numbers
let doubled = map((x) -> x * 2, numbers);
print(doubled);  :: [2, 4, 6, 8, 10]

:: Using lambda with index
let with_index = map((i, x) -> i + x, numbers);
print(with_index);  :: [1, 3, 5, 7, 9]
```

## Filter

```kentscript
let numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

:: Keep only even
let evens = filter((x) -> x % 2 == 0, numbers);
print(evens);  :: [2, 4, 6, 8, 10]

:: Greater than 5
let large = filter((x) -> x > 5, numbers);
print(large);  :: [6, 7, 8, 9, 10]
```

## Reduce

```kentscript
let numbers = [1, 2, 3, 4, 5];

:: Sum all
let sum = reduce((a, b) -> a + b, numbers, 0);
print(sum);  :: 15

:: Product
let product = reduce((a, b) -> a * b, numbers, 1);
print(product);  :: 120

:: Max value
let max_val = reduce((a, b) -> a > b ? a : b, numbers, 0);
print(max_val);  :: 5
```

## Chaining

```kentscript
let numbers = [1, 2, 3, 4, 5];

:: Filter then map
let result = map((x) -> x * 2, filter((x) -> x > 2, numbers));
print(result);  :: [6, 8, 10]

:: Pipe style (if supported)
let piped = numbers
    |> filter((x) -> x % 2 == 0)
    |> map((x) -> x * 10);
print(piped);  :: [20, 40]
```

---

# 15. Async/Await

## Basic Async Function

```kentscript
async func fetch_data(url: str) -> str {
    :: Simulated async operation
    system_time_sleep(1);
    return "Data from " + url;
}

async func main() {
    print("Starting fetch...");
    let result = await fetch_data("https://api.example.com");
    print("Got: " + result);
}
```

## Multiple Async Operations

```kentscript
async func fetch_all() {
    :: Fetch multiple URLs concurrently
    let task1 = async { system_time_sleep(1); return "result1"; };
    let task2 = async { system_time_sleep(0.5); return "result2"; };
    
    let r1 = await task1;
    let r2 = await task2;
    
    print(r1 + ", " + r2);
}
```

## Await with Error Handling

```kentscript
async func safe_fetch(url: str) -> str {
    try {
        let result = await system_http_get(url, "");
        return result;
    } catch Exception as e {
        return "Error: " + str(e);
    }
}
```

---

# 16. Unsafe Blocks - Low-Level Programming

Unsafe blocks allow direct memory manipulation, system calls, and hardware access.

## Memory Allocation

```kentscript
unsafe {
    :: Allocate 64 bytes
    let ptr = malloc(64);
    
    :: Check allocation succeeded
    if ptr == 0 {
        print("Allocation failed!");
        return;
    }
    
    :: Write data (pointer, value, size_in_bytes)
    ptr_write(ptr, 0xDEADBEEF, 8);     :: Write 8 bytes
    ptr_write(ptr, 42, 1);              :: Write 1 byte
    
    :: Read data
    let val8 = ptr_read(ptr, 8);         :: Read 8 bytes
    let val1 = ptr_read(ptr, 1);        :: Read 1 byte
    
    :: Free memory
    free(ptr);
    print("Memory operations complete");
}
```

## System Calls

```kentscript
unsafe {
    :: getpid - get process ID (syscall 39)
    let pid = syscall(39, 0, 0, 0, 0, 0, 0);
    print("Process ID: " + str(pid));
    
    :: getppid - get parent PID (syscall 110)
    let ppid = syscall(110, 0, 0, 0, 0, 0, 0);
    print("Parent PID: " + str(ppid));
    
    :: Write to stdout (syscall 1)
    let msg = "Hello from syscall!\n";
    syscall(1, 1, msg, len(msg), 0, 0, 0);
    
    :: getuid (syscall 102)
    let uid = syscall(102, 0, 0, 0, 0, 0, 0);
    print("User ID: " + str(uid));
}
```

## Timestamp Counter (RDTSC)

```kentscript
unsafe {
    :: Read CPU timestamp counter
    let tsc_start = rdtsc();
    
    :: Do some work
    let sum = 0;
    for i in range(1000000) {
        sum = sum + i;
    }
    
    let tsc_end = rdtsc();
    print("Cycles for loop: " + str(tsc_end - tsc_start));
}
```

## Hardware I/O Ports

```kentscript
unsafe {
    :: x86 I/O port operations
    :: outb - write byte to port
    :: inb - read byte from port
    
    :: Serial port (COM1) example
    let port = 0x3F8;
    
    :: Set DLAB to access baud rate divisor
    hardware.outb(port + 4, 0x80);  :: Line Control Register
    hardware.outb(port + 0, 0x0C);  :: Divisor LSB (9600 baud)
    hardware.outb(port + 1, 0x00);  :: Divisor MSB
    
    :: Set 8-N-1 (8 data bits, no parity, 1 stop bit)
    hardware.outb(port + 4, 0x03);
    
    :: Enable FIFO
    hardware.outb(port + 2, 0xC7);
    
    :: Write character 'A'
    hardware.outb(port, 0x41);
}
```

## Reading MSR (Model Specific Registers)

```kentscript
unsafe {
    :: Read MSR - requires root
    :: Example: Read CPU frequency
    let msr = msr_read(0xCE);  :: IA32_PERF_STATUS
    print("MSR value: " + str(msr));
}
```

## Inline Assembly (if supported)

```kentscript
unsafe {
    :: Simple inline assembly
    asm("mov rax, 42");
    asm("mov rbx, rax");
    asm("add rbx, 8");
}
```

## Memory Region Operations

```kentscript
unsafe {
    :: mmap - map memory region
    let size = 4096;
    let flags = MAP_ANONYMOUS | MAP_PRIVATE;
    let prot = PROT_READ | PROT_WRITE;
    
    let mem = mmap(0, size, prot, flags, -1, 0);
    
    if mem != -1 {
        :: Use mapped memory
        ptr_write(mem, 0x12345678, 4);
        
        :: Unmap
        munmap(mem, size);
    }
}
```

---

# 17. Modules & Imports

## Import Standard Modules

```kentscript
:: Import entire module
import os;
import math;
import time;
import json;

:: Use module functions
let cwd = os.getcwd();
let pi = math.pi;
let timestamp = time.time();
let data = json.loads('{"key": "value"}');
```

## Import Specific Functions

```kentscript
:: Import specific items from module
from os import getcwd, listdir;
from math import sqrt, sin, cos;

let files = listdir(".");
let root = sqrt(2);
```

## Import Alias

```kentscript
import os as operating_system;
import json as json_parser;

let path = operating_system.path.join("dir", "file.txt");
```

## Custom Modules

```kentscript
:: In mymodule.ks
func greet(name: str) -> str {
    return "Hello, " + name + "!";
}

const VERSION = "1.0";

:: In main.ks
import mymodule;

print(mymodule.greet("World"));
print(mymodule.VERSION);
```

---

# 18. Standard Library - Built-in Functions

## Output Functions

```kentscript
:: Print with newline
print("Hello");
print("A", "B", "C");  :: A B C

:: Print with custom separator
print("a", "b", sep=" - ");  :: a - b

:: Print without newline
print("No newline", end="");

:: Format output
println("Formatted: " + str(42));
```

## Input Functions

```kentscript
:: Get user input
let name = input("Enter your name: ");
print("Hello, " + name);

:: Input with default
let age_str = input("Age: ");
let age = int(age_str);
```

## Type Functions

```kentscript
:: Get type of value
let x = 42;
let t = type_of(x);  :: "i64"

let s = "hello";
let t2 = type_of(s);  :: "str"

:: Check type
let is_int = type_of(x) == "i64";
let is_str = type_of(s) == "str";
```

## Collection Functions

```kentscript
let arr = [3, 1, 4, 1, 5, 9];

:: Length
print(len(arr));  :: 6

:: Check if empty
if len(arr) > 0 {
    print("Not empty");
}

:: Get sum, min, max
let total = sum(arr);
let minimum = min(arr);
let maximum = max(arr);

:: Sorted (returns new array)
let sorted_arr = sorted(arr);

:: Reversed (returns new array)
let reversed_arr = reversed(arr);

:: Contains
let has_5 = 5 in arr;  :: true
```

## String Functions

```kentscript
let s = "Hello World";

:: Case conversion
print(upper(s));   :: HELLO WORLD
print(lower(s));   :: hello world
print(title(s));   :: Hello World
print(capitalize(s)); :: Hello world

:: Search
print(contains(s, "World"));  :: true
print(startswith(s, "Hello")); :: true
print(endswith(s, "World"));  :: true

:: Find
print(s.find("World"));  :: 6 (position)

:: Replace
print(replace(s, "World", "KentScript")); :: Hello KentScript

:: Split and Join
let words = split(s, " ");  :: ["Hello", "World"]
let joined = join(["a", "b", "c"], "-");  :: "a-b-c"

:: Trim
let padded = "  hello  ";
print(trim(padded));  :: hello

:: Substring
print(s[0:5]);    :: Hello
print(s[6:]);     :: World
```

## Math Functions

```kentscript
let x = -5;
let f = 3.14;

:: Absolute value
print(abs(x));      :: 5

:: Round
print(round(f));    :: 3
print(round(f, 1)); :: 3.1

:: Floor/Ceiling
print(floor(f));   :: 3
print(ceil(f));    :: 4

:: Power and roots
print(pow(2, 3));   :: 8.0
print(sqrt(16));    :: 4.0

:: Trigonometry (radians)
print(sin(0));      :: 0.0
print(cos(0));      :: 1.0
print(tan(0));      :: 0.0

:: Constants
print(math.pi);     :: 3.14159...
print(math.e);      :: 2.71828...
```

## File I/O Functions

```kentscript
:: Read entire file
let content = read_file("data.txt");

:: Write file
write_file("output.txt", "Hello World");

:: Open file for operations
let f = open("file.txt", "r");
let line = readline(f);
let data = read(f, 1024);
close(f);

:: Write
let f = open("output.txt", "w");
write(f, "New content");
close(f);

:: Append
let f = open("log.txt", "a");
write(f, "New line\n");
close(f);
```

## Time Functions

```kentscript
:: Current timestamp
let now = time();

:: Format time
let formatted = time_format(now, "%Y-%m-%d %H:%M:%S");
print(formatted);

:: Sleep (seconds)
system_time_sleep(1);  :: Sleep 1 second

:: Measure execution time
let start = time();
// ... some code ...
let elapsed = time() - start;
print("Elapsed: " + str(elapsed) + "s");
```

## Random Functions

```kentscript
:: Random float 0-1
let r = random();

:: Random integer
let n = randint(1, 100);

:: Random from range with step
let even = randint(0, 100, 2);

:: Choice from array
let items = ["a", "b", "c"];
let choice = choice(items);

:: Shuffle array
mut arr = [1, 2, 3, 4, 5];
shuffle(arr);
```

---

# 19. System Functions - C Runtime

These functions are available in compiled binaries (via C transpiler).

## File Operations

```kentscript
:: Write text to file
system_file_write_text("/tmp/test.txt", "Hello World");

:: Read text from file  
let content = system_file_read_text("/tmp/test.txt");

:: Check if file exists
let exists = system_file_exists("/tmp/test.txt");

:: Get file stats
let stat = system_file_stat("/tmp/test.txt");

:: Remove file
system_file_remove("/tmp/test.txt");

:: Rename file
system_file_rename("/tmp/old.txt", "/tmp/new.txt");

:: Open file (returns file handle)
let fd = system_file_open("/tmp/data.txt", "r");

:: Read/write via file handle
let data = system_file_read(fd, 1024);
system_file_write(fd, "content");
system_file_close(fd);
```

## OS Functions

```kentscript
:: Process info
let pid = system_os_getpid();
let ppid = system_os_getppid();
let uid = system_os_getuid();
let gid = system_os_getgid();

:: Get environment variable
let path = system_os_getenv("PATH");

:: Set environment variable
system_os_setenv("MY_VAR", "value");

:: Kill process
system_os_kill(pid, 9);  :: SIGKILL

:: Create/remove directory
system_os_mkdir("/tmp/mydir", 0755);
system_os_rmdir("/tmp/mydir");
```

## Random Functions

```kentscript
:: Random float 0.0-1.0
let r = system_random_random();

:: Random integer in range
let n = system_random_randint(1, 100);

:: Seed random generator
system_random_seed(12345);
```

## Time Functions

```kentscript
:: Current Unix timestamp
let now = system_time_time();

:: Sleep (seconds)
system_time_sleep(1);
system_time_sleep(0.5);  :: half second
```

## Subprocess

```kentscript
let exit_code = 0;
system_subprocess_run("ls -la", exit_code);
print("Exit code: " + str(exit_code));

:: Run and capture output
let result = system_subprocess_run("echo test", 0);
```

## HTTP Functions

```kentscript
:: GET request
let response = system_http_get("https://httpbin.org/get", "");
:: response is {status: code, body: "..."}

:: POST request
let post_resp = system_http_post(
    "https://httpbin.org/post", 
    "Content-Type: application/json",
    '{"key": "value"}'
);
```

## Encoding Functions

```kentscript
:: Base64 encode/decode
let encoded = system_encoding_base64_encode("Hello");
let decoded = system_encoding_base64_decode(encoded);

:: Hex encode/decode
let hex_enc = system_encoding_hex_encode("test");
let hex_dec = system_encoding_hex_decode(hex_enc);
```

## String Functions

```kentscript
let s = "Hello World";

:: Contains
let has = system_strings_contains(s, "World");  :: 1 (true)

:: Case conversion
let upper = system_strings_upper(s);   :: "HELLO WORLD"
let lower = system_strings_lower(s);   :: "hello world"

:: Starts/Ends with
let starts = system_strings_startswith(s, "Hello");  :: 1
let ends = system_strings_endswith(s, "World");    :: 1

:: Replace
let new_str = system_strings_replace(s, "World", "KentScript");
```

## Collections

```kentscript
:: Create namedtuple
let Point = system_collections_namedtuple("Point", ["x", "y"]);
let p = Point(10, 20);
print(p.x);  :: 10

:: Create deque
let dq = system_collections_deque([1, 2, 3]);

:: Create counter
let cnt = system_collections_counter(["a", "b", "a", "c", "a"]);
```

## Package Manager (kpm)

```kentscript
:: Install package
system_kpm_install("httplib");

:: List installed packages
let packages = system_kpm_list();
print(packages);

:: Search packages
let results = system_kpm_search("json");
print(results);

:: Get package version
let version = system_kpm_version("httplib");
print(version);

:: Get package requirements
let requires = system_kpm_requires("httplib");
print(requires);

:: Uninstall package
system_kpm_uninstall("httplib");
```

---

# 20. GUI Programming

KentScript has built-in GUI capabilities (interpreter mode only).

## Basic Window

```kentscript
import gui;

:: Create window
let window = gui.create_window("My App", 800, 600);

:: Set window properties
gui.set_title(window, "KentScript GUI");
gui.set_size(window, 1024, 768);
gui.set_position(window, 100, 100);

:: Show window
gui.show(window);

:: Main event loop
gui.mainloop(window);
```

## Labels

```kentscript
import gui;

let window = gui.create_window("Labels", 400, 200);

let label = gui.create_label(window, "Hello, World!");
gui.set_position(label, 10, 10);

let bold_label = gui.create_label(window, "Bold Text");
gui.set_font(bold_label, "Arial", 14, "bold");

gui.mainloop(window);
```

## Buttons

```kentscript
import gui;

let window = gui.create_window("Buttons", 300, 200);

:: Create button with callback
let button = gui.create_button(window, "Click Me", lambda: {
    gui.message_box("Alert", "Button clicked!", "info");
});

gui.set_position(button, 50, 50);

gui.mainloop(window);
```

## Text Entry

```kentscript
import gui;

let window = gui.create_window("Input", 400, 300);

let label = gui.create_label(window, "Enter name:");
gui.set_position(label, 10, 10);

let entry = gui.create_entry(window);
gui.set_position(entry, 10, 40);
gui.set_placeholder(entry, "Your name...");

let submit = gui.create_button(window, "Submit", lambda: {
    let name = gui.get_text(entry);
    gui.message_box("Welcome", "Hello, " + name + "!", "info");
});

gui.set_position(submit, 10, 80);

gui.mainloop(window);
```

## Checkboxes and Radio Buttons

```kentscript
import gui;

let window = gui.create_window("Options", 300, 200);

:: Checkbox
let checkbox = gui.create_checkbox(window, "I agree");
gui.set_position(checkbox, 10, 10);

let is_checked = gui.get_checked(checkbox);

:: Radio buttons (use same group)
let rb1 = gui.create_radio(window, "Option 1", "group1");
let rb2 = gui.create_radio(window, "Option 2", "group1");
gui.set_position(rb1, 10, 50);
gui.set_position(rb2, 10, 80);

gui.mainloop(window);
```

## Lists

```kentscript
import gui;

let window = gui.create_window("List", 300, 400);

let items = ["Apple", "Banana", "Orange", "Mango"];
let listbox = gui.create_listbox(window, items);
gui.set_position(listbox, 10, 10);

:: Get selected item
let selected = gui.get_selected(listbox);

gui.mainloop(window);
```

## Progress Bar

```kentscript
import gui;

let window = gui.create_window("Progress", 400, 100);

let progress = gui.create_progressbar(window, 0, 100);
gui.set_position(progress, 10, 10);

:: Update progress
for i in range(101) {
    gui.set_value(progress, i);
    gui.update();
    system_time_sleep(0.02);
}

gui.mainloop(window);
```

## Menus

```kentscript
import gui;

let window = gui.create_window("Menus", 400, 300);

:: Create menu bar
let menubar = gui.create_menu(window);

:: Add menus
let file_menu = gui.create_menu_item(menubar, "File");
let edit_menu = gui.create_menu_item(menubar, "Edit");
let help_menu = gui.create_menu_item(menubar, "Help");

:: Add menu items
let open_item = gui.create_menu_item(file_menu, "Open", lambda: {
    print("Open clicked");
});
let save_item = gui.create_menu_item(file_menu, "Save", lambda: {
    print("Save clicked");
});
let exit_item = gui.create_menu_item(file_menu, "Exit", lambda: {
    gui.quit(window);
});

gui.mainloop(window);
```

## Dialogs

```kentscript
import gui;

:: Message box
gui.message_box("Title", "Message", "info");      :: info icon
gui.message_box("Warning", "Be careful!", "warning");  :: warning
gui.message_box("Error", "Something went wrong", "error"); :: error

:: Input dialog
let name = gui.input_dialog("Enter Name", "What is your name?");

:: File dialog
let file = gui.file_dialog("Open File", "*.txt");

:: Color picker
let color = gui.color_dialog();
```

## Canvas (Drawing)

```kentscript
import gui;

let window = gui.create_window("Canvas", 500, 500);
let canvas = gui.create_canvas(window, 0, 0, 500, 500);

:: Draw shapes
gui.draw_line(canvas, 0, 0, 500, 500, "black");
gui.draw_rect(canvas, 10, 10, 100, 50, "blue", 2);
gui.draw_ellipse(canvas, 200, 200, 100, 50, "red", 1);

:: Draw text
gui.draw_text(canvas, "Hello", 50, 50, "Arial", 16);

gui.mainloop(window);
```

---

# 21. Common Errors & Troubleshooting

KentScript provides detailed error messages to help you debug issues. Here are common errors and how to fix them.

## Syntax Errors

### Missing Semicolon

**Error:**
```bash
$ ./kentscript run file.ks
error: [UnexpectedToken] Missing ';' at end of statement
  --> file.ks:3:20

   1 │ let x = 5
   2 │ print(x)
                ^^^

help:
  1. Add ';' after statements
  2. print(x);
```

**Fix:**
```kentscript
let x = 5;
print(x);
```

### Missing Braces

**Error:**
```bash
$ ./kentscript run file.ks
error: [UnexpectedToken] Expected '{' but got 'print'
  --> file.ks:2:5

   1 │ if x > 5
   2 │     print("big")
           ^^^^^

help:
  1. Add '{' after condition
```

**Fix:**
```kentscript
if x > 5 {
    print("big");
}
```

### Unclosed String

**Error:**
```bash
$ ./kentscript run file.ks
error: [UnexpectedToken] Unclosed string
  --> file.ks:1:12

   1 │ let s = "Hello;
                ^^^^^^^^

help:
  1. Add closing '"' to terminate the string
```

**Fix:**
```kentscript
let s = "Hello";
```

### Unclosed Block Comment

**Error:**
```bash
$ ./kentscript run file.ks
error: [UnexpectedToken] Unclosed block comment
  --> file.ks:1:1

   1 │ /* This comment is not closed
                 ^^^

help:
  1. Add */ to close
```

**Fix:**
```kentscript
/* This is a closed comment */
```

## Type Errors

### Type Mismatch

**Error:**
```bash
$ ./kentscript run file.ks
error: [TypeError] Cannot assign 'str' to type 'i64'
  --> file.ks:1:18

   1 │ let x: i64 = "hello";
                      ^^^^^^

help:
  1. Use compatible type
  2. let x: str = "hello";
```

**Fix:**
```kentscript
let x: str = "hello";
```

### Wrong Array Index Type

**Error:**
```bash
$ ./kentscript run file.ks
error: [TypeError] Array index must be integer, got 'str'
  --> file.ks:2:10

   1 │ let arr = [1, 2, 3];
   2 │ let x = arr["key"];
                 ^^^^^^

help:
  1. Use integer index: arr[0]
```

**Fix:**
```kentscript
let x = arr[0];
```

### Function Argument Type Mismatch

**Error:**
```bash
$ ./kentscript run file.ks
error: [TypeError] Expected 'i64' but got 'str' for parameter 'a'
  --> file.ks:4:5

   1 │ func add(a: i64, b: i64) -> i64 { return a + b; }
   2 │
   3 │ let result = add("hello", 5);
   4 │              ^^^
```

**Fix:**
```kentscript
let result = add(10, 5);
```

## Runtime Errors

### Division by Zero

**Error:**
```bash
$ ./kentscript run file.ks
error: [ZeroDivisionError] division by zero
  --> file.ks:1:20

   1 │ let result = 10 / 0;
                       ^^^
```

**Fix:**
```kentscript
let divisor = 0;
if divisor != 0 {
    let result = 10 / divisor;
} else {
    print("Cannot divide by zero");
}
```

### Index Out of Bounds

**Error:**
```bash
$ ./kentscript run file.ks
error: [IndexError] Index 10 out of range for array of size 3
  --> file.ks:2:10

   1 │ let arr = [1, 2, 3];
   2 │ let x = arr[10];
```

**Fix:**
```kentscript
let arr = [1, 2, 3];
if len(arr) > 10 {
    let x = arr[10];
}
```

### Key Not Found in Dictionary

**Error:**
```bash
$ ./kentscript run file.ks
error: [KeyError] Key 'age' not found in dictionary
  --> file.ks:2:15

   1 │ let data = {"name": "John"};
   2 │ let age = data["age"];
```

**Fix:**
```kentscript
let data = {"name": "John"};
if "age" in data {
    let age = data["age"];
}
```

### Null Pointer Access

**Error:**
```bash
$ ./kentscript run file.ks
error: [NullPointerError] Cannot dereference null pointer
  --> file.ks:2:5

   1 │ let ptr = null;
   2 │ let val = ptr + 5;
```

**Fix:**
```kentscript
let ptr = null;
if ptr != null {
    let val = ptr + 5;
}
```

### File Not Found

**Error:**
```bash
$ ./kentscript run file.ks
error: [FileNotFoundError] [Errno 2] No such file or directory: 'data.txt'
  --> file.ks:1:25

   1 │ let content = read_file("data.txt");
```

**Fix:**
```kentscript
if system_file_exists("data.txt") {
    let content = read_file("data.txt");
} else {
    print("File not found");
}
```

## Undefined Name Errors

### Using Undeclared Variable

**Error:**
```bash
$ ./kentscript run file.ks
error: [NameError] name 'undefined_var' is not defined
  --> file.ks:1:1

   1 │ print(undefined_var);
        ^^^^^^^^^^^^^^^^
```

**Fix:**
```kentscript
let undefined_var = "Hello";
print(undefined_var);
```

### Calling Undefined Function

**Error:**
```bash
$ ./kentscript run file.ks
error: [NameError] function 'my_func' is not defined
  --> file.ks:2:1

   1 │ func greet() { return "hi"; }
   2 │ my_func();
        ^^^^^^^
```

**Fix:**
```kentscript
func greet() { return "hi"; }
greet();
```

## Unsafe Block Errors

### Invalid Pointer

**Error:**
```bash
$ ./kentscript run file.ks
error: [MemoryError] Invalid memory access at address 0x0
  --> file.ks:3:5

   1 │ unsafe {
   2 │     let ptr = null;
   3 │     ptr_write(ptr, 42, 1);
```

**Fix:**
```kentscript
unsafe {
    let ptr = malloc(64);
    if ptr != null {
        ptr_write(ptr, 42, 1);
        free(ptr);
    }
}
```

### Memory Leak Warning

**Warning:**
```bash
$ ./kentscript run file.ks
warning: [MemoryWarning] Possible memory leak - allocated memory not freed
  --> file.ks:2:5
```

**Fix:**
```kentscript
unsafe {
    let ptr = malloc(100);
    // ... use pointer ...
    free(ptr);  // Always free!
}
```

## Pattern Matching Errors

### Non-Exhaustive Match

**Warning (not an error):**
```bash
$ ./kentscript run file.ks
warning: [MatchWarning] Pattern match is not exhaustive - some cases not handled
```

**Fix:**
```kentscript
let day = 7;
let name = match day {
    case 1: { "Monday" }
    case 2: { "Tuesday" }
    case 3: { "Wednesday" }
    case 4: { "Thursday" }
    case 5: { "Friday" }
    case 6: { "Saturday" }
    case 7: { "Sunday" }  // Always add default or all cases
};
```

### Invalid Match Expression

**Error:**
```bash
$ ./kentscript run file.ks
error: [MatchError] Match expression must return same type in all cases
```

## Error Code Reference

| Error Code | Meaning | Solution |
|-----------|---------|----------|
| `UnexpectedToken` | Syntax error | Check syntax and punctuation |
| `MissingSemicolon` | Statement not ended with `;` | Add `;` at end |
| `TypeError` | Type mismatch | Use correct type |
| `NameError` | Undefined name | Declare before use |
| `IndexError` | Array index out of range | Check index bounds |
| `KeyError` | Dict key not found | Use `in` to check first |
| `FileNotFoundError` | File doesn't exist | Check file path |
| `ZeroDivisionError` | Division by zero | Check divisor before divide |
| `NullPointerError` | Using null pointer | Check pointer before use |
| `MemoryError` | Invalid memory access | Validate pointers |
| `PermissionError` | No permission | Check file permissions |
| `OverflowError` | Number too large | Use larger type (i64) |

## Getting Help with Errors

Use the `help` command in REPL:
```kentscript
>>> help errors
```

Or use the error message's help section - KentScript shows helpful suggestions for fixing each error.

---

# 22. REPL & Interactive Development

## Starting REPL

```bash
./kentscript repl
```

## REPL Commands

```kentscript
>>> help              :: Show help
>>> exit              :: Exit REPL
>>> creator           :: Show creator info
>>> vars              :: Show current variables
>>> clear             :: Clear screen
```

## Working in REPL

```kentscript
:: Variables
>>> let x = 5
>>> let y = 10
>>> x + y
15

:: Functions
>>> func add(a, b) { return a + b; }
>>> add(3, 7)
10

:: Comments work
>>> /* this is a comment */
>>> :: this too
>>> /// documentation

:: All KentScript features work
>>> let arr = [1, 2, 3]
>>> arr.append(4)
>>> print(arr)
[1, 2, 3, 4]
```

## Autocomplete

Press Tab for autocomplete on:
- Keywords
- Built-in functions
- Types
- Unsafe functions
- System functions

---

# 23. VSCodium IDE Extension

## Installation

```bash
./setup_vscodium.sh
```

## Features

### Commands (Ctrl+Shift+P)

```
kentscript.run         - Run current file
kentscript.build       - Build to native binary
kentscript.debug       - Debug current file
kentscript.repl        - Start REPL
kentscript.restartLSP  - Restart language server
```

### LSP Features
- **IntelliSense** - Autocomplete
- **Go to Definition** - Navigate code
- **Rename Symbol** - Refactor
- **Diagnostics** - Error highlighting
- **Semantic Highlighting** - Colorful tokens
- **Code Folding** - Collapse regions

### Editor Integration
- Run/Build/Debug buttons in title bar
- Right-click context menu
- Syntax highlighting for .ks files

---

# 25. Package Manager (kpm)

KentScript includes a built-in package manager called **kpm** for managing external libraries and modules.

## Using kpm in REPL

In the REPL, you can manage packages directly:

```kentscript
:: Install a package
>>> kpm install httplib

:: List installed packages
>>> kpm list

:: Search for packages
>>> kpm search json

:: Uninstall a package
>>> kpm uninstall httplib

:: Get package info
>>> kpm info httplib
```

## Using kpm from Command Line

```bash
:: Install package
python3 tools/kpm.py install <package>
python3 tools/kpm.py install <package> --version 1.0.0
python3 tools/kpm.py install <package> --url https://github.com/user/repo

:: Uninstall package
python3 tools/kpm.py uninstall <package>

:: Update package
python3 tools/kpm.py update <package>

:: List installed packages
python3 tools/kpm.py list

:: Search registry
python3 tools/kpm.py search <query>

:: Get package info
python3 tools/kpm.py info <package>

:: Clear cache
python3 tools/kpm.py clean
```

## Using kpm in Code

You can also use system functions for package management:

```kentscript
:: Install package from code
system_kpm_install("httplib");

:: List installed packages
let packages = system_kpm_list();
print(packages);

:: Search for packages
let results = system_kpm_search("json");
print(results);

:: Get package version
let version = system_kpm_version("httplib");
print(version);

:: Uninstall
system_kpm_uninstall("httplib");
```

## Package Structure

A KentScript package should have:

```
mypackage/
├── kpm.json           :: Package manifest
├── package.ks         :: Main entry point
├── utils.ks           :: Additional modules
└── README.md          :: Documentation
```

## Package Manifest (kpm.json)

```json
{
    "name": "httplib",
    "version": "1.0.0",
    "description": "HTTP client library",
    "author": "pyLord",
    "entry": "package.ks",
    "dependencies": {
        "json": ">=1.0.0"
    },
    "keywords": ["http", "network", "web"],
    "license": "MIT"
}
```

## Installing from GitHub

```bash
:: Install directly from GitHub repository
python3 tools/kpm.py install mypackage --url https://github.com/username/kentscript-mypackage

:: Install from specific branch
python3 tools/kpm.py install mypackage --url https://github.com/username/kentscript-mypackage --branch main

:: Install from local path
python3 tools/kpm.py install mypackage --path /path/to/local/package
```

## Custom Registry

```bash
:: Use custom registry
python3 tools/kpm.py install package --registry https://my-registry.example.com

:: Set default registry
export KPM_REGISTRY=https://my-registry.example.com
```

## Local/Development Packages

```bash
:: Link local package for development
python3 tools/kpm.py link --path /path/to/package --name mydev

:: Unlink package
python3 tools/kpm.py unlink mydev
```

## Package Cache

```bash
:: Cache location
~/.cache/kentscript/    (Linux/macOS)
%LOCALAPPDATA%\ks_cache\  (Windows)

:: Clean cache
python3 tools/kpm.py clean
```

---

# 26. Quick Reference

## File Extension
```
.ks  - KentScript source file
```

## Basic Program Template

```kentscript
:: Program name
:: Description

import ...;

func main() {
    :: Your code here
}

main();
```

## Keywords

```
let, mut, const   :: Variables
func, return      :: Functions
class, struct, enum  :: Types
if, elif, else   :: Conditionals
while, for, in   :: Loops
match, case      :: Pattern matching
try, except, finally, raise  :: Error handling
unsafe           :: Low-level operations
import, export   :: Modules
async, await     :: Async
```

## Types

```
i8, i16, i32, i64    :: Signed integers
u8, u16, u32, u64    :: Unsigned integers
f32, f64             :: Floating point
bool, str, char, ptr  :: Other types
```

## Built-in Functions

```
print, input, len, range, map, filter, reduce
type_of, sizeof, str, int, float, bool
sum, min, max, sorted, reversed, keys, values, items
split, join, upper, lower, replace, trim, contains
abs, pow, sqrt, round, floor, ceil, sin, cos, tan
open, read, write, close
time, sleep, random
```

## System Functions

```
system_file_*    :: File operations
system_os_*      :: OS operations
system_time_*    :: Time functions
system_random_*  :: Random functions
system_http_*    :: HTTP requests
system_encoding_*:: Encoding
system_strings_* :: String operations
system_subprocess_run :: Run commands
```

## Comment Syntax

```kentscript
:: Single line comment

/// Documentation comment

/* Multi-line
   comment */
```

---

## Version Info

- **KentScript v3.1.0**
- **Created:** 1st March 2026
- **Author:** pyLord (Musika Alvin) - Uganda
- **Language:** Python-based (~161,000 lines)
- **License:** MIT

## Getting Help

```bash
./kentscript --help              :: CLI help
./kentscript run --help          :: Run options
./kentscript build --help        :: Build options
./kentscript repl                :: Interactive help
```