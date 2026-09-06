# KentScript Language Reference
## Complete Guide — v3.1.0

**Created: 19th February 2026** | **Version 3.1.0** | **By pyLord (Uganda)**

---

# About KentScript

## Language Overview

KentScript is a cross-platform systems programming language with a Python core engine, a C runtime, a standard library (77 modules), and an LSP server. It combines Python-like syntax with C-like low-level features, running on Linux, macOS, and Windows 7+ with native syscalls, inline assembly, and C transpilation on all three platforms.

## Author & Origin

- **Created by**: pyLord (Musika Alvin)
- **Location**: Uganda
- **Created on**: 19th February 2026
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
| C Transpiler | ✅ Working | Native binary compilation via gcc/clang (Linux, macOS, Windows) |
| REPL | ✅ Full | Interactive development |
| GUI | ⚠️ Partial | Requires tkinter; fallback no-op mode otherwise |
| Package Manager | ✅ | kpm/kxi for module management |
| Low-Level | ✅ | malloc, syscall, hardware I/O, unsafe blocks — cross-platform |
| SIMD / GPU | ✅ | Real NEON/AVX/AVX-512 vectorization + OpenCL/CUDA compute (CPU-SIMD fallback) |
| **Platform Support** | ✅ | **Linux, macOS, Windows** — syscalls, asm, C transpiler, memory all work on all three |

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
   8.5. [Interfaces & Traits](#85-interfaces--traits)
9. [Structs & Enums](#9-structs--enums)
10. [Pattern Matching](#10-pattern-matching)
11. [Error Handling](#11-error-handling)
12. [Collections](#12-collections)
13. [Comprehensions](#13-comprehensions)
14. [Lambdas & Higher-Order Functions](#14-lambdas--higher-order-functions)
15. [Async/Await](#15-asyncawait)
16. [Low-Level & Safe Blocks](#16-low-level--safe-blocks)
17. [Modules & Imports](#17-modules--imports)
18. [Standard Library - Built-in Functions](#18-standard-library---built-in-functions)
19. [System Functions](#19-system-functions)
20. [GUI Programming](#20-gui-programming)
21. [Common Errors & Troubleshooting](#21-common-errors--troubleshooting)
22. [REPL & Interactive Development](#22-repl--interactive-development)
23. [Built-in Web IDE](#23-built-in-web-ide)
24. [VSCodium IDE Extension](#24-vscodium-ide-extension)
25. [Package Manager (kpm)](#25-package-manager-kpm)
26. [Standard Library Modules](#26-standard-library-modules)
96.5. [Standard Library Modules — Additional Reference](#265-standard-library-modules--additional-reference)
27. [Platform & Tooling](#27-platform--tooling)
28. [Quick Reference](#28-quick-reference)
29. [Hardware Acceleration (SIMD / GPU)](#29-hardware-acceleration-simd--gpu)

---

# 1. Getting Started

## Installation

KentScript runs on **Linux**, **macOS**, and **Windows**. The `main` branch holds prebuilt installers; the `source` branch holds the full source.

### Linux / macOS (Recommended)

```bash
curl -fsSL https://github.com/musikaalvin/kentscript/raw/main/install.sh | bash
```

### Windows

**PowerShell (as Administrator):**
```powershell
# Windows 7/8/10/11 compatible (PowerShell 2.0+)
iex (New-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/musikaalvin/kentscript/main/windows/install.ps1')
```

**Or download from releases:**
Download `KentScript-Setup-3.1.0.exe` from [GitHub Releases](https://github.com/musikaalvin/kentscript/releases).

### Build from Source

```bash
git clone --branch source https://github.com/musikaalvin/kentscript.git
cd kentscript
pip install -r requirements-build.txt
python3 build_binary.py --all        # builds to dist/
```

 ## Running Programs

KentScript is a **compiled systems-programming language**. The `kentscript`
binary is the real entry point — all examples below use it directly.

```bash
# Run in interpreter mode (full stdlib, all features work)
kentscript run file.ks

# Compile to native binary
kentscript build file.ks -O3
./file

# Debug with breakpoints (repeat --break for multiple; --stop pauses before line 1)
kentscript debug file.ks --break 10
kentscript debug file.ks --break 3 --break 6 --stop

# At the (debug) prompt: s=step in, n=step over, c=continue,
# b <line>=set breakpoint, p <var>=print var, l=locals, bt=backtrace, q=quit
```

See `kentscript --help` for all available subcommands including kernel,
security, hardware, and audit tools.

### Interactive REPL & Consoles

KentScript ships a real **interactive environment**,
with **Tab-autocompletion** and **persistent command history**:

```bash
# KentScript language REPL — type code, Tab-completes modules/members,
# ↑/↓ recalls previous commands (history in ~/.kentscript_history)
kentscript

# KSecurity ethical pentest console — Tab-completes module paths
# (e.g. type `use au` → auxiliary/ai_assist, auxiliary/report), option
# names after `use <module>`, and subcommands after `show`; ↑/↓ recalls
# history across sessions (saved in ~/.ksecurity_history)
kentscript security
```

> The REPL and consoles use prompt-toolkit. History is persisted between
> sessions, so this behaves like a proper language shell (think `python`,
> `node`, or `irb`).


## Build Options

```bash
# Optimization levels
./kentscript build file.ks -O0    # No optimization
./kentscript build file.ks -O1    # Basic
./kentscript build file.ks -O2    # Standard (default, also default when omitted)
./kentscript build file.ks -O3    # Aggressive (recommended for performance)

# Keep generated C file
./kentscript build file.ks -O3 --keep-c

# Custom output name
./kentscript build file.ks -o myprogram
```

### Build caches & speed flags

The `build` pipeline has two transparent caches that make iterative
development fast, plus flags to bypass them when needed.

1. **Binary build cache** — On an unchanged rebuild the native binary is
   restored from `~/.cache/ks_bin/<sha256>.bin` (skipping both transpile *and*
   `gcc`). The cache key covers the source text, the `-O` level, and the
   mtimes of `codegen/c_transpiler.py`, `include/`, and `runtime/c/ks_runtime.a`,
   so any toolchain edit invalidates correctly. Expect ~1.1 s restores vs
   ~2.2 s cold builds (sieve benchmark).

2. **C-transpile cache** (`~/.cache/ks_cc/`) — The lex+parse+codegen step is
   cached by source hash + transpiler version, independently of gcc flags.
   It is reused whenever the binary cache is bypassed, e.g. `--no-cache` or
   `--release` (PGO, which always recompiles). This avoids re-parsing the
   source on every flag tweak. The win scales with program size.

```bash
# Profile-Guided Optimization build (two-pass, specialized hot paths)
./kentscript build file.ks --release

# Disable BOTH caches and rebuild from scratch (debug / reproducibility)
./kentscript build file.ks --no-cache

# Inspect the generated C without compiling
./kentscript build file.ks --keep-c      # emits build/<name>/<name>.c
```

> PGO (`--release`) builds always recompile (they are their own specialized
> artifact) and are **not** served from the binary cache, but they DO benefit
> from the C-transpile cache on repeat runs.

---

### Comprehension fast-path (runtime speed)

Range-based, filter-free comprehensions over a scalar element type are
transpiled with a **pre-sized, single-pass fill** instead of a per-element
`append` loop:

```ks
let sieve = [1 for i in range(N)]   # allocates once, fills directly
```

This eliminates ~2 million `append` calls for large arrays and is the main
runtime-speed lever for array-heavy code. Filtered, string, and iterable-source
comprehensions keep the general (correct) path.

> **Performance note (memory layout).** KentScript's generic `ks_array` stores
> 8-byte `long long` elements. Compute-bound numeric kernels (e.g. Sieve of
> Eratosthenes) therefore move ~8× more memory than an equivalent C program
> using a `char`/`bool` array, which is the dominant remaining gap after the
> fast-path (~3.5× vs hand-written C for the sieve). Closing that last gap would
> require a type-specialized (byte-packed / SoA) array representation — a larger,
> opt-in change, not enabled by default.

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

:: F-strings (interpolated strings)
let name = "KentScript";
let version = 3.1;
let msg = f"Hello, {name}! Version {version}";  :: "Hello, KentScript! Version 3.1"
let expr = f"2 + 2 = {2 + 2}";                   :: "2 + 2 = 4"

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

:: Increment/Decrement (prefix and postfix)
let x = 5;
x++;       :: postfix increment: x = 6
++x;       :: prefix increment: x = 7
x--;       :: postfix decrement: x = 6
--x;       :: prefix decrement: x = 5
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

## Floor Division
```kentscript
let result = 10 // 3;  :: 3 (integer division)
let neg = -10 // 3;    :: -4 (floor division)
```

## Range Operator
```kentscript
let r = 0..5;         :: range 0,1,2,3,4 (exclusive, not including 5)
let inc = 0..=5;      :: range 0,1,2,3,4,5 (inclusive range)
let arr = [1..10];    :: array from 1 to 9
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

## Do/While Loop

```kentscript
let count = 0;
do {
    print("Count: " + str(count));
    count = count + 1;
} while count < 5;
```

## With Statement

```kentscript
:: Automatic resource management
with file = open("data.txt", "r") {
    let content = read(file);
    print(content);
}  :: file automatically closed

:: With multiple resources
with f1 = open("a.txt", "r"), f2 = open("b.txt", "r") {
    :: use both files
}
```

## Assert Statement

```kentscript
let x = 5;
assert x > 0;         :: passes
assert x < 0;         :: raises AssertionError
assert x == 5, "x should be 5";  :: with message
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

## Switch Statement

```kentscript
let code = 2;
switch code {
    case 1: print("one");
    case 2: print("two");
    case 3: print("three");
    default: print("other");
}

:: Switch falls through by default; use break to prevent
switch code {
    case 1: { print("one"); break; }
    case 2: { print("two"); break; }
    default: { print("other"); }
}
```

## Pass Statement

```kentscript
:: No-op placeholder
if true {
    pass;  :: do nothing
}

func empty() {
    pass;  :: to be implemented later
}
```

## Del Statement

```kentscript
let x = 42;
del x;  :: remove variable

let arr = [1, 2, 3];
del arr[1];  :: remove element

let dict = {"a": 1, "b": 2};
del dict["a"];  :: remove key
```

## Global and Nonlocal

```kentscript
let x = 10;  :: global

func outer() {
    let x = 20;  :: shadows global
    
    func inner() {
        global x;     :: refers to global x
        nonlocal x;   :: refers to enclosing x (outer)
    }
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

## Decorators

```kentscript
:: Define a decorator
func log_call(func) {
    return (args...) -> {
        print("Calling function");
        let result = func(*args);
        print("Function done");
        return result;
    };
}

:: Apply decorator
@log_call
func greet(name) {
    return "Hello, " + name;
}

print(greet("Kent"));  :: logs before and after
```

## Generator Functions

```kentscript
:: Generator function with yield
func* count_to(n: i64) {
    let i = 0;
    while i < n {
        yield i;
        i = i + 1;
    }
}

let gen = count_to(3);
for val in gen {
    print(val);  :: 0, 1, 2
}
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

Constructors can be defined as either `init` or `__init__`:

```kentscript
class Point {
    func __init__(self, x: i64, y: i64) {
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

# 8.5. Interfaces & Traits

## Defining an Interface

```kentscript
interface Drawable {
    func draw(self) -> str;
    func get_area(self) -> f64;
}

interface Serializable {
    func to_json(self) -> str;
}
```

## Implementing an Interface

```kentscript
class Circle {
    func __init__(self, radius: f64) {
        self.radius = radius;
    }
    
    implements Drawable {
        func draw(self) -> str {
            return "Circle(r=" + str(self.radius) + ")";
        }
        
        func get_area(self) -> f64 {
            return 3.14159 * self.radius * self.radius;
        }
    }
    
    implements Serializable {
        func to_json(self) -> str {
            return '{"type": "circle", "radius": ' + str(self.radius) + '}';
        }
    }
}
```

## Traits (Alternative to Interfaces)

```kentscript
trait Printable {
    func print(self);
}

impl Printable for str {
    func print(self) {
        :: self is the string
        std_print(self);
    }
}

"Hello".print();  :: uses the trait implementation
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

## Union Types

```kentscript
:: Union - one field at a time (like C unions)
union Data {
    i: i64,
    f: f64,
    b: bool,
}

:: Access union fields (only one is valid at a time)
let d = Data { i: 42 };
print(d.i);  :: 42

d = Data { f: 3.14 };
print(d.f);  :: 3.14
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

:: Pipe style
let piped = numbers
    |> filter((x) -> x % 2 == 0)
    |> map((x) -> x * 10);
print(piped);  :: [20, 40]
```

---

# 15. Async/Await

## Basic Async Function

```kentscript
import time;

async func fetch_data(url: str) -> str {
    :: Simulated async operation
    time.sleep(1);
    return "Data from " + url;
}

async func main() {
    print("Starting fetch...");
    let result = await fetch_data("https://api.example.com");
    print("Got: " + result);
}

:: Run the async entry point
async.run(main);
```

## Multiple Async Operations

```kentscript
import time;

:: Define async tasks as separate functions
async func task1() -> str {
    time.sleep(1);
    return "result1";
}

async func task2() -> str {
    time.sleep(0.5);
    return "result2";
}

async func fetch_all() {
    let r1 = await task1();
    let r2 = await task2();
    print(r1 + ", " + r2);
}

:: Run the async entry point
async.run(fetch_all);
```

## Await with Error Handling

```kentscript
import http;

async func safe_fetch(url: str) -> str {
    try {
        let resp = await http.get(url);
        return resp.text;
    } catch Exception as e {
        return "Error: " + str(e);
    }
}

:: Run with error handling
async func main() {
    let result = await safe_fetch("https://httpbin.org/get");
    print(result);
}
async.run(main);
```

---

# 16. Low-Level & Safe Blocks

## Unsafe Blocks

Unsafe blocks allow direct memory manipulation, system calls, and hardware access.

```kentscript
unsafe {
    :: Low-level operations here
    :: No bounds checking, no safety guarantees
}
```

## Safe Blocks

Safe blocks restrict operations to memory-safe constructs only:

```kentscript
safe {
    :: Only safe operations allowed here
    :: Bounds checking, null pointer checks enabled
    let x = 42;
    print(x);
}
```

## Borrow / Release / Move

KentScript's optional borrow checker for compile-time memory safety:

```kentscript
:: Borrow a value (immutable reference)
let data = [1, 2, 3];
borrow data {
    print(len(data));  :: read-only access
}  :: borrow ends here

:: Release a resource
let ptr = malloc(64);
release ptr;  :: explicitly free

:: Move ownership
let source = "hello";
let target = move source;  :: source is now invalid
```

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

KentScript syscalls work cross-platform. On **Linux** they use libc. On **macOS** they use `libsystem_kernel` (deprecated but functional). On **Windows** they translate to `ntdll` Nt* functions. You use the same x86-64 Linux syscall numbers everywhere — the runtime translates automatically.

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

### Syscall Platform Support

| Syscall | Linux | macOS | Windows |
|---------|-------|-------|---------|
| read/write/open/close | ✅ | ✅ (libc→libsystem_kernel) | ✅ (NtReadFile/NtWriteFile/NtCreateFile/NtClose) |
| exit | ✅ | ✅ | ✅ (NtTerminateProcess) |
| fork/exec | ✅ | ✅ | ❌ (no equivalent — use CreateProcess) |
| mmap/munmap | ✅ | ✅ (197/73) | ✅ (NtAllocateVirtualMemory/NtFreeVirtualMemory) |
| getpid | ✅ | ✅ (20) | ✅ (NtQueryInformationProcess) |
| sleep | ✅ | ✅ (240) | ✅ (NtDelayExecution) |
| Port I/O | ✅ | ❌ (ARM, no I/O ports) | ❌ (no I/O ports) |

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

> **Platform-specific:** x86 only — uses I/O privilege level (iopl). Requires root. Not available on ARM (aarch64).

```kentscript
import hardware;

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

> **Platform-specific:** x86 only. Requires root and the `msr` kernel module (`modprobe msr`). Not available on ARM (aarch64).

```kentscript
unsafe {
    :: Read MSR - requires root + msr module
    :: Example: Read CPU frequency
    let msr = msr_read(0xCE);  :: IA32_PERF_STATUS
    print("MSR value: " + str(msr));
}
```

## Inline Assembly

Inline assembly works cross-platform. On Linux/macOS it uses `gcc`/`clang`. On Windows it uses `gcc` (MinGW) or `cl.exe`. The runtime auto-detects your compiler and architecture.

```kentscript
unsafe {
    :: Simple inline assembly
    asm("mov rax, 42");      :: x86-64 example
    asm("mov rbx, rax");
    asm("add rbx, 8");
}
```

### Assembly Platform Notes

| Platform | Compiler | Syntax | Notes |
|----------|----------|--------|-------|
| Linux x86-64 | gcc/clang | Intel | Full support |
| Linux ARM64 | gcc/clang | GCC asm | cpuid returns (0,0,0,0) |
| macOS ARM64 | clang | GCC asm | Apple Silicon native |
| macOS x86-64 | clang | Intel | Rosetta or native |
| Windows x86-64 | gcc (MinGW) | Intel | Full support |
| Windows ARM64 | — | — | Not yet supported |

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

## Export Statement

```kentscript
:: Export specific items from a module
export func public_function() {
    print("This is public");
}

:: Private function (not exported)
func internal_helper() {
    print("Internal use only");
}

const PUBLIC_CONST = 42;
```

## Type Aliases

```kentscript
:: Create type aliases
type Age = i64;
type Name = str;

let user_age: Age = 25;
let user_name: Name = "John";

type Callback = func(i64) -> bool;
type Point2D = (f64, f64);
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
let t = type(x);  :: "i64"

let s = "hello";
let t2 = type(s);  :: "str"

:: Check type
let is_int = type(x) == "i64";
let is_str = type(s) == "str";
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

:: Case conversion (method form)
print(s.upper());   :: HELLO WORLD
print(s.lower());   :: hello world
print(s.title());   :: Hello World
print(s.capitalize()); :: Hello world

:: Search (method form)
print(s.contains("World"));  :: true
print(s.startswith("Hello")); :: true
print(s.endswith("World"));  :: true

:: Find (method form)
print(s.find("World"));  :: 6 (position)

:: Replace (method form)
print(s.replace("World", "KentScript")); :: Hello KentScript

:: Split and Join (method form)
let words = s.split(" ");             :: ["Hello", "World"]
let joined = words.join("-");         :: "Hello-World"

:: Trim (method form)
let padded = "  hello  ";
print(padded.trim());  :: hello

:: Substring
print(s[0:5]);    :: Hello
print(s[6:]);     :: World

:: Also available via the string module
import string;
print(string.upper(s));
print(string.lower(s));
print(string.title(s));
print(string.capitalize(s));
print(string.contains(s, "World"));
print(string.replace(s, "World", "KS"));
print(string.trim(s));
print(string.split(s, " "));

:: Find a word across all lines in a file
let content = read_file("setup.py");
let lines = content.split("\n");
let word = "kentscript";
let line_num = 0;
for line in lines {
    line_num = line_num + 1;
    let col = line.find(word);
    if col != -1 {
        print("Line " + str(line_num) + ", column " + str(col));
    }
}
:: Output: Line 4, column 10
::          Line 11, column 13
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
:: Read entire file (standalone)
let content = read_file("data.txt");

:: Write file (standalone)
write_file("output.txt", "Hello World");

:: Open file for operations (methods)
let f = open("file.txt", "r");
let line = f.readline();
let data = f.read(1024);
f.close();

:: Write (methods)
let f = open("output.txt", "w");
f.write("New content");
f.close();

:: Append (methods)
let f = open("log.txt", "a");
f.write("New line\n");
f.close();
```

## Time Functions

```kentscript
import time;

:: Current timestamp
let now = time.time();

:: Format time
let formatted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now));
print(formatted);

:: Sleep (seconds)
time.sleep(1);  :: Sleep 1 second

:: Measure execution time
let start = time.time();
// ... some code ...
let elapsed = time.time() - start;
print("Elapsed: " + str(elapsed) + "s");
```

## Random Functions

```kentscript
import random;

:: Random float 0-1
let r = random.random();

:: Random integer (standalone, no import needed)
let n = randint(1, 100);

:: Choice from array
let items = ["a", "b", "c"];
let choice = random.choice(items);

:: Shuffle array (needs import)
mut arr = [1, 2, 3, 4, 5];
random.shuffle(arr);
```

---

# 19. System Functions

 These functions are available in the interpreter. For the C backend (compiled
 binaries), networking and subprocess compile to native C:

 - Networking: the `socket` module (`socket.tcp()`, `server.bind()`, `client.recv()`,
   etc.) and the low-level `system_socket_*` builtins both compile to real BSD sockets.
 - Subprocess: `subprocess.run_command(cmd, capture, check, shell)` and the low-level
   `ks_subprocess_run(cmd, shell, capture)` both compile to native C (`popen`).

 Both styles below are valid interpreted or compiled (`kentscript build file.ks`).

> **Native-compilation status (C backend):** the high-level stdlib modules
> (`socket.tcp()`, `server.bind()`, `client.recv()`, `subprocess.run_command` with
> `result.returncode`/`result.stdout`) **compile to a native binary** — the C backend
> routes them to real BSD sockets (`system_socket_*`) and `popen`
> (`ks_subprocess_run`). The example below is valid both interpreted and compiled.

## File Operations

```kentscript
import os;

:: Write/read text files
os.write_file("/tmp/test.txt", "Hello World");
let content = os.read_file("/tmp/test.txt");

:: Check existence, remove, rename
let exists = os.exists("/tmp/test.txt");
os.remove("/tmp/test.txt");
os.rename("/tmp/old.txt", "/tmp/new.txt");

:: Open file for read/write (methods)
let f = os.open_file("/tmp/data.txt", "r");
let data = f.read(1024);
f.close();

let f = os.open_file("/tmp/data.txt", "w");
f.write("content");
f.close();
```

## OS Functions

```kentscript
import os;

:: Process info
let pid = os.getpid();

:: Environment
let path = os.getenv("PATH");
os.putenv("MY_VAR", "value");

:: Directories
os.mkdir("/tmp/mydir", 0755);
os.rmdir("/tmp/mydir");
```

## Random Functions

```kentscript
import random;

let r = random.random();        :: float 0.0-1.0
let n = random.randint(1, 100); :: integer in range
random.seed(12345);             :: seed the generator
```

## Time Functions

```kentscript
import time;

let now = time.time();     :: Unix timestamp
time.sleep(1);             :: seconds
time.sleep(0.5);           :: half second
```

## Subprocess

```kentscript
import subprocess;

let result = subprocess.run("ls -la");
print("Exit code: " + str(result.returncode));
print("Output: " + result.stdout);
```

## HTTP Functions

```kentscript
import http;

:: GET request
let response = http.get("https://httpbin.org/get");
:: response is {status: code, body: "..."}

:: POST request
let post_resp = http.post(
    "https://httpbin.org/post", 
    "Content-Type: application/json",
    '{"key": "value"}'
);
```

## Encoding Functions

```kentscript
import crypto;

:: Base64 encode/decode
let encoded = crypto.base64_encode("Hello");
let decoded = crypto.base64_decode(encoded);

:: Hex encode/decode
let hex_enc = crypto.hex_encode("test");
let hex_dec = crypto.hex_decode(hex_enc);
```

## kcrypt Module — Advanced Encryption

The `kcrypt` module provides high-assurance XChaCha20-Poly1305 AEAD encryption via libsodium (PyNaCl). It offers authenticated encryption with associated data (AEAD), meaning the ciphertext can be verified for tampering before decryption.

**Dependencies:** Requires `pynacl` (`pip install pynacl`)

### File Extension Conventions

- `.kcrypt` - Encrypted file output
- `.kcrypt.key` - Key file (when saved separately)

### Basic Encryption/Decryption

```kentscript
import kcrypt;

:: Generate a random key
let key = kcrypt.random_key(32);

:: Encrypt data
let plaintext = "Secret message";
let encrypted = kcrypt.encrypt(plaintext, key);
print("Encrypted:", encrypted);

:: Decrypt data
let decrypted = kcrypt.decrypt(encrypted, key);
print("Decrypted:", decrypted);

:: Verify round-trip
assert(decrypted == plaintext);
```

### Password-Based Encryption

```kentscript
import kcrypt;

:: Derive a key from a password using scrypt
let derived_key = kcrypt.derive_key("mypassword", "random_salt", 32);

:: Encrypt with derived key
let enc = kcrypt.encrypt("secret data", derived_key);

:: Or use convenience functions (combines derivation + encryption)
let enc_pw = kcrypt.encrypt_with_password(
    "secret data", "mypassword", "random_salt"
);
let dec_pw = kcrypt.decrypt_with_password(
    enc_pw, "mypassword", "random_salt"
);
```

### Password Hashing (Argon2id)

`kcrypt` can hash passwords for safe storage and verification using **Argon2id**
(via libsodium). The hash is returned as a self-describing, branded string:

```
$kcrypt$<year>$pyLord$<cost>$<salt>$<payload>
```

- `<year>` &mdash; the **current calendar year**, read from the system clock at
  hash time (not hard-coded). A hash made in 2026 reads `$kcrypt$2026$...`, one
  made in 2027 reads `$kcrypt$2027$...`, and so on. Verification does **not**
  pin the year, so a token created in any year still verifies in later years.
- `<cost>` &mdash; 2-digit cost tier (`03`&ndash;`24`). Argon2id memory grows with
  cost (cost `8` &asymp; 8&nbsp;MiB, capped at 64&nbsp;MiB) and is hard-capped to
  avoid out-of-memory on constrained devices.
- `<salt>` &mdash; 16 random bytes, bcrypt-variant base64 (22 chars).
- `<payload>` &mdash; 24 derived bytes, bcrypt-variant base64 (32 chars).

This works in **both** execution modes &mdash; the interpreter
(`kentscript run`) uses PyNaCl, and the C-compiled binary (`kentscript build`)
uses a libsodium FFI wrapper. Both produce the exact same token format and can
verify each other's hashes (cross-mode compatible).

#### Basic usage

```kentscript
import kcrypt;

:: Hash a password (default cost is 8)
let h = kcrypt.hash_password("mysecret", 8);
println(h);   :: e.g. $kcrypt$2026$pyLord$08$....$........

:: Verify a login attempt
if kcrypt.verify_password(h, entered_password) {
    println("access granted");
} else {
    println("access denied");
}
```

#### Store the hash, verify on login

```kentscript
import kcrypt;

:: At signup: hash + persist the token (e.g. to a database / file)
let stored = kcrypt.hash_password("hunter2", 10);
save_to_db(username, stored);   :: store the $kcrypt$... string only

:: At login: never compare plaintext — verify the token
let entered = read_password();
if kcrypt.verify_password(stored, entered) {
    println("welcome back");
} else {
    println("invalid credentials");
}
```

#### Cross-mode example (interpreter vs compiled binary)

A hash produced by one engine verifies in the other, because both use the same
Argon2id parameters and branded format:

```kentscript
import kcrypt;

:: Run this with `kentscript run` OR compile it with `kentscript build` —
:: the output token is interchangeable between the two.
let h = kcrypt.hash_password("Secret123", 10);
println(h);
println(str(kcrypt.verify_password(h, "Secret123")));  :: 1 / True
println(str(kcrypt.verify_password(h, "wrong")));      :: 0 / False
```

Never store the plaintext password &mdash; store the `$kcrypt$...` string and call
`verify_password` on each login. The comparison is constant-time.

### Associated Data (AAD)

You can attach additional authenticated data that will be verified but not encrypted:

```kentscript
import kcrypt;

let key = kcrypt.random_key(32);
let enc = kcrypt.encrypt("plaintext", key, none, "user:alice,role:admin");
let dec = kcrypt.decrypt(enc, key, none, "user:alice,role:admin");
```

### File Encryption

```kentscript
import kcrypt;

let key = kcrypt.random_key(32);

:: Encrypt a file (creates .kcrypt file automatically)
let enc_path = kcrypt.encrypt_file("/path/to/file.txt", key);

:: Decrypt a .kcrypt file
let plaintext = kcrypt.decrypt_file(enc_path, key);
```

### Key Management

```kentscript
import kcrypt;
import fileio;

:: Generate and save a key
let key = kcrypt.random_key(32);
fileio.write_text("secret.key", key);

:: Load key from file
let loaded_key = fileio.read_text("secret.key");
```

### Interactive Menu Example

See `examples/kcrypt_menu.ks` for a complete menu-driven program that demonstrates:
- File encryption/decryption with interactive prompts
- Key generation and management
- File extension handling (`.kcrypt` convention)
- Color-coded terminal output

Run with: `kentscript run examples/kcrypt_menu.ks`

### API Reference

| Function | Arguments | Description |
|----------|-----------|-------------|
| `encrypt` | `(data, key, nonce, aad)` | Encrypt with XChaCha20-Poly1305 AEAD. Returns base64 ciphertext. |
| `decrypt` | `(data, key, nonce, aad)` | Decrypt ciphertext. Returns plaintext string. |
| `derive_key` | `(password, salt, length)` | Derive key from password using scrypt (N=16384, r=8, p=1). |
| `random_key` | `(length)` | Generate random key of specified byte length (default 32). |
| `encrypt_with_password` | `(data, password, salt, nonce, aad)` | Convenience: derive key from password, then encrypt. |
| `decrypt_with_password` | `(data, password, salt, aad)` | Convenience: derive key from password, then decrypt. |
| `encrypt_file` | `(filepath, key, title, subject, key_id)` | Encrypt a file with embedded metadata, saves to `.kcrypt`. |
| `decrypt_file` | `(filepath, key, save)` | Decrypt a `.kcrypt` file. Returns plaintext. |
| `read_kcrypt_file` | `(filepath)` | Read and parse a `.kcrypt` file, returns metadata + encrypted payload. |
| `build_metadata` | `(filepath, title, subject, key_id, status, extra)` | Build metadata JSON string for a kcrypt file. |
| `hexdump` | `(data, title)` | Generate hex dump lines (list of strings). |
| `hexdump_color` | `(data, title)` | Print colored hex dump to terminal. |
| `info` | `(filepath)` | Print metadata info about a `.kcrypt` file. |

**Default Extension:** `kcrypt.DEFAULT_EXTENSION` = `".kcrypt"`

**Constants:** `kcrypt.MAGIC` = `"KC1"` (magic header for file format)

### CLI Hex Viewer

KentScript provides a built-in hex viewer for `.kcrypt` files:

```bash
:: View encrypted file hex dump
kentscript -hx file.kcrypt
kentscript --hexdump file.kcrypt

:: View and decrypt with a key
kentscript -hx file.kcrypt "your-key-here"

:: Using the run subcommand
kentscript run -hx file.kcrypt
```

The hex viewer displays:
- **Metadata**: Title, timestamp, sizes, key ID, subject, status
- **Hex dump**: Offset, hex bytes, ASCII representation (colored)
- **Decrypted content** (if key provided): Styled output with colored sections

### File Format

.kcrypt files use a text-safe 3-line format:

```
KC1
{"title":"CONFIDENTIAL","subject":"...","timestamp":"...",...}
base64_encrypted_payload...
```

- Line 1: Magic header `KC1`
- Line 2: JSON metadata with title, subject, key_id, status, timestamp, tool, original_filename, original_size, encrypted_size
- Line 3: Base64-encoded XChaCha20-Poly1305 ciphertext

## String Functions

Use **method syntax** (no import needed):

```kentscript
let s = "Hello World";

print(s.contains("World"));      :: true
print(s.upper());                :: HELLO WORLD
print(s.lower());                :: hello world
print(s.startswith("Hello"));    :: true
print(s.endswith("World"));      :: true
print(s.replace("World", "KS")); :: Hello KS
```

Or via the `string` module:

```kentscript
import string;
print(string.contains(s, "World"));
print(string.upper(s));
print(string.lower(s));
print(string.replace(s, "World", "KS"));
```



## Package Manager (kpm)

```kentscript
kpm_install("httplib");

let packages = kpm_list();
print(packages);

let results = kpm_search("json");
print(results);

let version = kpm_version("httplib");
print(version);

let requires = kpm_requires("httplib");
print(requires);

kpm_uninstall("httplib");
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
import time;

let window = gui.create_window("Progress", 400, 100);

let progress = gui.create_progressbar(window, 0, 100);
gui.set_position(progress, 10, 10);

:: Update progress
for i in range(101) {
    gui.set_value(progress, i);
    gui.update();
    time.sleep(0.02);
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

### Hash Comment (use `::`)

**Error:**
```bash
$ ./kentscript run file.ks
error: [UnexpectedToken] '#' is not a comment in KentScript
  --> file.ks:1:1

   1 │ # hi
         ^

help:
  Use '::' for line comments → :: hi
```

**Fix:**
```kentscript
:: hi
print("hello");
```

### `fn` Keyword (use `func`)

**Error:**
```bash
$ ./kentscript run file.ks
error: [UnexpectedToken] KentScript uses 'func', not 'fn'
  --> file.ks:1:1

   1 │ fn main() {
         ^^

help:
  Replace 'fn' with 'func'
```

**Fix:**
```kentscript
func main() {
    print("hello");
}
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
import os;
if os.exists("data.txt") {
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
    :: ... use pointer ...
    free(ptr);  :: Always free!
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
    case 7: { "Sunday" }  :: Always add default or all cases
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
| `SyntaxError` | Invalid syntax (`#`, `fn`, etc.) | See help message for fix |
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
./kentscript
```

Or equivalently, just run `./kentscript` with no arguments.

### REPL Welcome Screen

```
╭─────────────────── ⚡ KentScript 3.1.0 ────────────────────╮
│                                                            │
│  _  __            _   ____            _       _            │
│ | |/ /___ _ __   | |_/ ___|  ___ _ __(_)_ __ | |_          │
│ | ' // _ \ '_ \  | __\___ \ / __| '__| | '_ \| __|         │
│ | . \  __/ | | | | |_ ___) | (__| |  | | |_) | |_          │
│ |_|\_\___|_| |_|  \__|____/ \___|_|  |_| .__/ \__|         │
│                                        |_|                 │
│                                                            │
│ Python & C based Systems Programming Language  — by pyLord │
│ C Transpiler • OOP • Borrow Checker • Standard Library     │
│                                                            │
╰────────────────────────────────────────────────────────────╯

Type 'exit' to quit, 'help' for commands
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
>>> let x = 5;
>>> let y = 10;
>>> x + y;
15

:: Functions
>>> func add(a, b) { return a + b; };
>>> add(3, 7);
10

:: Comments work
>>> /* this is a comment */
>>> :: this too
>>> /// documentation

:: All KentScript features work
>>> let arr = [1, 2, 3];
>>> arr.append(4);
>>> print(arr);
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

# 23. Built-in Web IDE

KentScript ships with a built-in web IDE that runs in your browser. Full-featured code editor with KentScript support, an interactive shell/REPL, and LSP-powered intelligence.

## Quick Start

```bash
kentscript ide                    # Launch on port 8000
kentscript ide --port 3000        # Custom port
kentscript ide --root ./myproject # Custom root directory
```

Or from KentScript code:
```ks
import ide;
ide.start();                     # Default port 8000
ide.start_with_port(3000);       # Custom port
```

Then open `http://localhost:8000` in your browser.

## Features

### Editor
- **Code Editor** — full-featured editor with KentScript syntax highlighting (Monarch grammar)
- **Dark & Light Themes** — toggle from the View menu or the title-bar button; the theme is applied consistently to every panel, tab, menu, sidebar, terminal, and the editor itself
- **Tab System** — multiple files open simultaneously, modified indicators
- **Find & Replace** — `Ctrl+F` find, `Ctrl+H` replace, `Ctrl+G` go to line
- **Minimap** — toggle from the View menu
- **Word Wrap** — toggle with `Alt+Z`
- **Zoom** — `Ctrl++` / `Ctrl+-` to adjust font size
- **Resizable Layout** — drag the splitter between the file tree and the editor, the divider above the bottom panel, and between editor groups. All splitters work with both mouse and touch (large invisible hit-area, visible grip). Hide the sidebar with the Explorer chevron or `Ctrl+B`
- **Popup dialogs** — the Open/Save, command palette, Go-to-Line, Settings and Keyboard-Shortcuts dialogs all close by tapping the dimmed backdrop or the ✕ button (not only `Escape`)

### Interactive Shell / REPL
- **Real kentscript binary** — runs the actual KentScript interpreter under the hood
- **State persists** — variables and functions survive across commands (like the cmdline REPL)
- **Command history** — up/down arrows recall previous commands (200 saved)
- **Multi-line input** — Shift+Enter for new lines, auto-growing textarea
- **Shortcuts** — `Ctrl+\`` focus shell, `Ctrl+L` clear, `Ctrl+C` clear input
- **Output display** — colored output (errors in red, success in green)

### LSP (Language Server Protocol)
- **Completion** — type-aware autocomplete for variables, functions, classes, modules
- **Hover** — mouse over any symbol to see its type and kind
- **Diagnostics** — real-time error underlines, Problems panel shows all issues
- **Powered by** `analyze.py` — the same analyzer used by the Node.js LSP server

### File Management
- **File Browser** — sidebar with folder tree, create/delete files and folders
- **Open File / Open Folder** — real OS navigation dialogs (`File ▸ Open File…` `Ctrl+O`, `File ▸ Open Folder…` `Ctrl+K Ctrl+O`); Open Folder imports the selected directory tree into the workspace
- **Save** — `Ctrl+S` save, `Ctrl+Shift+S` save all
- **Run** — `F5` run file, `F9` run selection, output in Output panel
- **Run & Debug** — start a real step-through debug session of the active file; output and prompts appear in the Debug Console

### Debugging (Run & Debug)
The IDE drives the **real KentScript debugger** (the same engine as `kentscript debug`), not a mock:
- **Set breakpoints** — click the editor gutter next to a line number; a red dot marks the breakpoint and it is sent to the debugger when the session starts.
- **Start / Stop** — the Debug Console has Start Debugging and Stop buttons; starting launches `kentscript debug` with the active file and your breakpoints.
- **Current line highlight** — the paused statement is highlighted inline in the editor as the program steps.
- **Debug Console prompt** — a live `(debug)` prompt streams the debugger's output; type the same commands as the CLI:
  - `s` / `step` — step into the next statement
  - `n` / `next` — step over the next statement
  - `c` / `continue` — resume until the next breakpoint or program end
  - `b <line>` / `break <line>` — set a breakpoint
  - `p <var>` / `print <var>` — print a variable's value
  - `l` / `locals` — list in-scope variables
  - `bt` — show the call stack
  - `q` / `quit` — end the session
- **Problems panel** — live diagnostics merged from the LSP and the server-side `analyze.py` analyzer (works even if the LSP WebSocket drops), with click-to-open on each issue.

### Responsive & Mobile
- **Mobile-friendly** — sidebar collapses to overlay on small screens
- **Touch support** — all resize handles work with touch gestures
- **State persistence** — panel sizes, shell history, font size saved to localStorage
- **Auto-collapse** — panels auto-collapse when dragged too small

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save current file |
| `Ctrl+Shift+S` | Save all files |
| `Ctrl+N` | New file |
| `Ctrl+O` | Open file |
| `Ctrl+W` | Close tab |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+J` | Toggle panel |
| `Ctrl+\`` | Focus shell |
| `Ctrl+F` | Find |
| `Ctrl+H` | Replace |
| `Ctrl+G` | Go to line |
| `Ctrl++` / `Ctrl+-` | Zoom in/out |
| `F5` | Run file |
| `F9` | Run selection |
| `Alt+Z` | Toggle word wrap |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/files` | List files in root directory |
| GET | `/api/read?path=...` | Read file contents |
| POST | `/api/save` | Save file (`{path, content}`) |
| POST | `/api/run` | Run `.ks` file (`{path}`) |
| POST | `/api/run_code` | Run code snippet (`{code}`) |
| POST | `/api/shell/exec` | Execute in shell REPL (`{code, history}`) |
| POST | `/api/lsp/complete` | LSP completion (`{code, line, column, prefix}`) |
| POST | `/api/lsp/hover` | LSP hover info (`{code, line, column}`) |
| POST | `/api/lsp/diagnose` | LSP diagnostics (`{code}`) |
| GET | `/api/builtins` | Built-in keywords/types/builtins list (offline completion source) |
| POST | `/api/analyze` | Server-side analyze (`{path, source}`) → diagnostics + symbols |
| POST | `/api/debug/start` | Start debug session (`{path, breakpoints}`) → `{session}` |
| POST | `/api/debug/command` | Send debugger command (`{session, cmd}`) |
| POST | `/api/debug/stop` | Stop debug session (`{session}`) |
| GET | `/api/debug/output?session=...` | Poll streamed debug output (`{output, running}`) |
| POST | `/api/newfile` | Create file (`{name}`) |
| POST | `/api/newfolder` | Create folder (`{name}`) |
| POST | `/api/delete` | Delete file/folder (`{path}`) |
| POST | `/api/change_root` | Change root directory (`{path}`) |
| GET | `/api/health` | Health check |

## Architecture

```
Browser (KentScript IDE + Shell / Debug Panels)
    ↕ HTTP REST APIs
stdlib/ide_server.py (Python HTTP server)
    ↕ subprocess.run / analysis
kentscript binary  ── run / -c / shell exec
                  ── debug  (real step-through debugger, --break lines)
analyze.py (kentscript-lsp: completion, hover, diagnostics)
```

The IDE frontend lives in `stdlib/ide/` (index.html, ide-app.js, ide.css) and is served by `stdlib/ide_server.py`, which also bridges the `kentscript-lsp` WebSocket (on `http_port + 1`) for completion/hover/diagnostics. The Diagnostics panel merges LSP messages with the server-side `analyze.py` analyzer via `/api/analyze`, and the Debug Console drives the real `kentscript debug` session through `/api/debug/*`. The shell panel accumulates commands and sends the full history to `kentscript -c` to preserve variable state across commands.

---

# 24. VSCodium IDE Extension

The official editor extension for KentScript lives in `vscode-kentscript/`
and is backed by the Language Server Protocol implementation in
`kentscript-lsp/`. It provides syntax highlighting, editor commands to
run/build/debug `.ks` files, and a language server (completion, hover, live
diagnostics).

## Installation

```bash
./setup_vscodium.sh
```

This copies the extension (plus the `kentscript-lsp` server and its
`langdata.py`) into `~/.vscode-oss/extensions/pylord.vscode-kentscript-3.2.0`
and registers it. **No TypeScript build step is required** — the extension
ships as plain JavaScript (`extension.js`). If `vscode-languageclient` is
installed it is used automatically; otherwise a built-in minimal LSP client
is used, so IntelliSense works either way.

## Editor Commands

Open the Command Palette (`Ctrl+Shift+P`) and type `KentScript`:

| Command | Description |
|---------|-------------|
| `KentScript: Run` | `kentscript run <file>` |
| `KentScript: Run with Arguments` | run with extra CLI args |
| `KentScript: Build (native)` | `kentscript build -O3` |
| `KentScript: Build Release (PGO)` | `kentscript build --release -O3` |
| `KentScript: Debug` | `kentscript debug <file>` |
| `KentScript: System Info` | `kentscript info` |
| `KentScript: Show Version` | print version |
| `KentScript: New File` | scaffold a `.ks` file |
| `KentScript: Open Documentation` | open this guide |
| `KentScript: Restart Language Server` | restart the LSP |

### Keybindings
- `Ctrl+F5` — Run
- `Ctrl+Shift+B` — Build
- `F5` — Debug
- (macOS: `Cmd` instead of `Ctrl`)
- Right-click context menu in the editor and file explorer.

## Language Server (LSP)

The server (`kentscript-lsp/server.js`) is started automatically when a
`.ks` file is opened.

### Self-syncing language data
`kentscript-lsp/langdata.py` extracts **keywords, types, builtins, and module
APIs** directly from the real compiler (`compiler/lexer/lexer.py`) and the
standard library, so completion and hover never drift from the language.
Re-run `python3 langdata.py` to regenerate the data. The grammar
(`vscode-kentscript/syntaxes/kentscript.tmLanguage.json`) is also generated
from this data.

### Features
- **Syntax Highlighting** — keywords, types, builtins, and unsafe operations
  (`malloc`, `ptr_read`, `asm`, `mmio_read`, …) highlighted distinctly.
- **Auto-completion** — keywords, types, builtins, code snippets, and module
  member completion (e.g. type `simd.` or `os.` to see that module's API).
  Works on both auto-trigger and manual `Ctrl+Space`.
- **Hover Documentation** — function signatures and descriptions.
- **Diagnostics** — real-time error checking: missing semicolons, unsafe
  operations used outside `unsafe` blocks, and syntax errors.
- **Unsafe Detection** — warns about low-level operations outside `unsafe`
  blocks.
- **Go to Definition** — `F12` jumps to a symbol's declaration.
- **Go to Type Definition** — jumps to a symbol's type/struct/class.
- **Go to Implementation** — jumps to implementations of an interface/trait.
- **Find References** — lists every usage of a symbol across the workspace.
- **Document Symbol & Workspace Symbol** — outline of the current file and
  workspace-wide symbol search.
- **Rename** — rename a symbol and update all references.
- **Document Formatting** — full-document, range, and on-type formatting.
- **Signature Help** — shows the active function signature and parameter while
  you type a call.
- **Code Action** — quick-fixes and refactors offered at the cursor.
- **Execute Command** — runs editor/extension commands exposed by the server.

> All of the above are provided by the built-in `kentscript-lsp/server.js`
> (no optional `vscode-languageclient` required). Completion, hover,
> diagnostics, definitions, references, formatting, signature help, code
> actions, and symbol search work out of the box.

### Example

```kentscript
// Auto-complete suggests 'let'
let x = 42;

// Hover over 'malloc' shows documentation
unsafe {
    let ptr = malloc(1024);  // ✓ OK
}

malloc(1024);  // ✗ Error: requires unsafe block
```

## Configuration

`.vscode/settings.json`:

```json
{
  "kentscript.executablePath": "kentscript",
  "kentscript.pythonPath": "python3",
  "kentscript.lspServerPath": "",
  "kentscript.lsp.enabled": true
}
```

- `executablePath` — the `kentscript` CLI wrapper (default: resolved from PATH).
- `pythonPath` — Python used by the LSP server to regenerate language data.
- `lspServerPath` — override path to `kentscript-lsp/server.js` (defaults to
  `../kentscript-lsp/server.js` next to the extension).
- `lsp.enabled` — toggle the language server.

## Supported Editors

- ✅ VSCode
- ✅ VSCodium
- ✅ Any editor supporting LSP (Vim, Emacs, Sublime, etc.)

## Development

Run the LSP server directly:

```bash
node kentscript-lsp/server.js --stdio
```

Debug:

```bash
node --inspect kentscript-lsp/server.js --stdio
```

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
python3 tools/kpm.py cache-clean
```

## Using kpm in Code

You can also use system functions for package management:

```kentscript
:: Install package from code
kpm_install("httplib");

:: List installed packages
let packages = kpm_list();
print(packages);

:: Search for packages
let results = kpm_search("json");
print(results);

:: Get package version
let version = kpm_version("httplib");
print(version);

:: Uninstall
kpm_uninstall("httplib");
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

## Installing from GitHub / Local

```bash
:: Link a local package for development
python3 tools/kpm.py link --path /path/to/mypackage --name mypackage

:: Unlink a package
python3 tools/kpm.py unlink mypackage
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
python3 tools/kpm.py cache-clean
```

---

# 26. Standard Library Modules

KentScript includes a comprehensive standard library with 77+ modules covering all major programming domains:

## Core Modules

| Module | Description |
|--------|-------------|
| `math` | Mathematical functions (sin, cos, sqrt, pow, pi, e) |
| `os` | Operating system interface (getcwd, listdir, path) |
| `time` | Time functions (time, sleep, strftime) — via stdlib/core/ks_time_module.py |
| `json` | JSON serialization/deserialization |
| `csv` | CSV reading/writing |
| `random` | Random number generation |
| `strings` | String manipulation utilities |
| `encoding` | Base64, Hex, URL encoding |
| `regex` | Regular expression matching, search, replace |
| `datetime` | Date/time parsing and formatting |

## Data & Collections

| Module | Description |
|--------|-------------|
| `collections` | Namedtuple, deque, Counter, defaultdict |
| `itertools` | Chain, zip, map, filter, reduce, permutations |
| `functools` | Partial, compose, memoize, wraps |
| `bitwise` | Bit manipulation utilities |
| `dataclass` | Data class decorator/utilities |
| `dataframe` | Pandas-like DataFrame with filter, sort, groupby, aggregate, select, CSV/JSON I/O |
| `cache` | In-memory cache with TTL eviction, get/set/delete/clear/stats |
| `ratelimit` | Token-bucket rate limiter with per-key buckets |
| `fileproc` | AWK-style file processing (read_lines, each_line, grep, head) |
| `jwt` | JWT encode/decode (HS256) |

## Network & Web

| Module | Description |
|--------|-------------|
| `http` | HTTP client (GET, POST, etc.) |
| `network` | Low-level network utilities |
| `webserver` | HTTP server with static file serving, directory listing, MIME detection, CORS, cache control |
| `asyncio` | Async I/O operations |
| `web` | Web framework — routing with path params (`:id`), middleware, CORS, sessions, file uploads, static serving, rate limiting, sub-routers |
| `webui` | Styled web UI components — 45+ components: hero, feature grid, pricing table, testimonial, timeline, steps, chart bar, breadcrumbs, team card, chat, login form, search bar, empty state, notification, star rating, tag list, kanban, stat grid, alert banner, footer bottom + navbar, card, button, input, textarea, table, alert, badge, modal, tabs, sidebar, form, dropdown, progress bar, tooltip, accordion, toast, pagination, footer, dropdown menu, code block, stat card, divider, avatar, toggle, skeleton. 3 themes (dark/light/midnight). No external CSS |
| `openapi` | OpenAPI 3.0 spec generator with path params, request/response schemas, markdown export |
| `ide` | Built-in web IDE — browser-based code editor with file browser, syntax highlighting (CodeMirror), run button, save/create/delete files, auto port retry. Launch with `kentscript ide` or `ide.start()` |
| `email` | SMTP/IMAP email client (send, send_html, fetch) |
| `ssh` | SSH client via subprocess (run, scp, shell) |
| `docker` | Docker SDK via CLI (ps, pull, run, stop, rm, logs, exec, compose) |
| `graphql` | GraphQL client (query, mutate over HTTP) |
| `socket` | TCP/UDP socket client and server (connect, bind, listen, accept, send, recv) |
| `websocket` | WebSocket client and server with message callbacks, broadcast, on_connect/disconnect |

## Database

| Module | Description |
|--------|-------------|
| `sqlite` | SQLite — connect, execute, query, query_one, query_val, executemany, transactions, in_memory() |
| `postgres` | PostgreSQL — connect, execute, query, executemany, copy_from, transactions (requires psycopg2-binary) |
| `mysql` | MySQL — connect, execute, query, executemany, last_insert_id, transactions (requires mysql-connector-python) |
| `mariadb` | MariaDB — connect, execute, query, executemany, transactions (falls back to mysql-connector) |
| `sql` | Query builder — select, insert, batch_insert, update, delete_from, joins, where, where_in, where_between, where_like, group_by, having, order_by, limit, offset, aggregates, create_table, truncate, drop. Works with all SQL backends |

## Cryptography & Security

| Module | Description |
|--------|-------------|
| `crypto` | MD5, SHA1, SHA256, SHA512, HMAC, PBKDF2, AES encrypt/decrypt |
| `kcrypt` | XChaCha20-Poly1305 AEAD encryption (requires PyNaCl) |
| `security` | Path validation, input sanitization, code signing, encryption |

## System & Hardware

| Module | Description |
|--------|-------------|
| `system` | System-level function wrappers |
| `hardware` | Hardware I/O port access, MMIO |
| `memory` | Memory management utilities |
| `syscall` | Direct syscall interface |
| `ffi` | Foreign function interface (C ABI) |
| `scheduler` | Task scheduler — run functions at intervals via background thread |
| `simd` | **Real CPU SIMD acceleration** — typed vector buffers; transpiles to NEON/AVX/AVX-512 |
| `gpu` | **Real GPGPU compute** — OpenCL backend (+ CUDA secondary) with automatic CPU-SIMD fallback |
| `accel` | Pythonistic SIMD/GPU wrappers (`vector_add`, `vector_scale`, `vector_dot`, `gpu_vector_add`) |

## File & Storage

| Module | Description |
|--------|-------------|
| `pathlib` | Object-oriented path manipulation |
| `compression` | Gzip, Zlib, BZ2, LZMA compress/decompress |
| `sqlite` | SQLite database connectivity |
| `config` | Configuration file handling (INI parser) |
| `dotenv` | Load .env files into environment (load, get, set, parse, save) |
| `excel` | XLSX read/write (zipfile+XML, no pip required) |

## Terminal & UI

| Module | Description |
|--------|-------------|
| `color` | ANSI terminal colors (named colors, 256-color, true color, gradient) |
| `tui` | Terminal UI — Table (ASCII renderer), confirm(), choose() prompts |
| `progress` | Progress bars, Spinner, Counter, tqdm |
| `rich_progress` | Rich-compatible progress bars (requires rich) |

## Development & Debugging

| Module | Description |
|--------|-------------|
| `logging` | Logging framework — levels, handlers, formatters, FileHandler, RotatingFileHandler, JsonFormatter |
| `testing` | Unit testing utilities (assert, test runner) |
| `argparse` | Command-line argument parsing |
| `template` | Template engine |
| `markdown` | Markdown-to-HTML conversion (stdlib regex-based) |
| `compiler` | Compiler utilities |
| `error` | Error handling utilities |
| `validation` | Input/data validation utilities |
| `parser` | Parsing utilities |

## Concurrency

| Module | Description |
|--------|-------------|
| `subprocess` | Subprocess execution, pipes |
| `asyncio` | Async/await concurrency |

## File System & I/O

| Module | Description |
|--------|-------------|
| `fileio` | File I/O utilities |
| `path` | Path manipulation utilities |
| `pathlib` | Object-oriented path manipulation |

## File Watching

| Module | Description |
|--------|-------------|
| `watcher` | Polling-based file/directory change watcher with callback |

## Image Processing

| Module | Description |
|--------|-------------|
| `image` | ImageMagick subprocess bridge — resize, thumbnail, grayscale, blur, rotate, crop, format, info |

## Low-Level & Assembly

| Module | Description |
|--------|-------------|
| `asm` | Assembly-level utilities |
| `safe` | Safe execution wrappers |
| `struct_utils` | Struct utility functions |

## Iteration

| Module | Description |
|--------|-------------|
| `iterators` | Iterator utilities |
| `itertools` | Chain, zip, map, filter, reduce, permutations |

## Core

| Module | Description |
|--------|-------------|
| `core/result_option` | Result/Option monad types |

## Import Example

```kentscript
import crypto;
let hash = crypto.sha256("hello");
print(hash);  :: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

import compression;
let compressed = compression.gzip_compress("data");
let decompressed = compression.gzip_decompress(compressed);


import sqlite;
let db = sqlite.open("test.db");
db.execute("CREATE TABLE IF NOT EXISTS users (id INT, name TEXT)");
db.execute("INSERT INTO users VALUES (1, 'Alice')");
let rows = db.query("SELECT * FROM users");

import tui;
tui.Table(["Name", "Age"], [["Alice", 30], ["Bob", 25]]).print();

import dataframe;
let df = dataframe.DataFrame([{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]);
print(df.filter(func(r) { return r["age"] > 25; }).to_json());

import email;
let r = email.send("smtp.example.com", 587, "user", "pass", "from@ex.com", ["to@ex.com"], "Subject", "Body");
print(r);

import markdown;
print(markdown.to_html("# Hello\n\n**bold** text"));

import excel;
excel.write("out.xlsx", [["Name", "Age"], ["Alice", 30], ["Bob", 25]]);

import scheduler;
let s = scheduler.Scheduler();
s.every(1.0, func() { print("tick\n"); });
s.start();
sleep(5);
s.stop();

import jwt;
let token = jwt.encode({"user": "admin", "role": "editor"}, "secret123");
print(jwt.decode(token, "secret123"));
```

## dotenv — Load .env Files

```kentscript
import dotenv;

:: Load .env file (parses KEY=VALUE, ignores # comments)
let loaded = dotenv.load(".env");
print(loaded);  :: 3  (number of vars loaded)

:: Access loaded values
let api_key = dotenv.get("API_KEY");
let db_host = dotenv.get("DB_HOST", "localhost");  :: with default

:: Set values programmatically
dotenv.set("DEBUG", "true");

:: Parse .env content from a string
let vars = dotenv.parse("API_KEY=abc123\nDB_PORT=5432");
print(vars["API_KEY"]);  :: abc123

:: Get all loaded vars
let all = dotenv.all();

:: Save current vars to a file
dotenv.save(".env.backup");
```

## webui — Styled Web UI Components

```kentscript
import webui;
import web;

let app = web.App();

app.get("/", func(req) {
    :: Create a themed dashboard page
    let t = webui.dark_theme();

    let content = [
        webui.navbar([
            {"text": "Dashboard", "url": "/"},
            {"text": "Users", "url": "/users"},
            {"text": "Settings", "url": "/settings"}
        ], "MyApp", t),

        :: Alert banner
        webui.alert("System is online", "success", t),

        :: Card with content
        webui.card("Total Users", "1,234", t),

        :: Data table
        webui.table(
            ["Name", "Email", "Role"],
            [
                ["Alice", "alice@example.com", "Admin"],
                ["Bob", "bob@example.com", "Editor"]
            ], t
        ),

        :: Buttons
        webui.button("Save", "/save", "primary", t) + " " +
        webui.button("Delete", "/delete", "danger", t),

        :: Form inputs
        webui.input("Enter your name", "text", "name", t) +
        webui.textarea("Write a message...", 4, "message", t),

        :: Tabs
        webui.tabs(
            ["Overview", "Details", "Logs"],
            [
                "<p>Summary goes here</p>",
                "<p>Detailed info goes here</p>",
                "<p>Recent activity goes here</p>"
            ], t
        ),

        :: Badge
        webui.badge("v3.1.0", "#3fb950", t),

        :: Modal dialog
        webui.modal("Confirm", "Are you sure?", "confirm-modal", t)
    ];

    return web.html(webui.page("Dashboard", t, content));
});

app.listen(8080);
```

**Available themes:** `dark_theme()`, `light_theme()`, `midnight_theme()`, `custom_theme({...})`

**Components (45+):** `hero`, `feature_grid`, `pricing_table`, `testimonial`, `timeline`, `steps`, `chart_bar`, `breadcrumbs`, `team_card`, `chat_bubble`, `chat`, `login_form`, `search_bar`, `empty_state`, `notification`, `star_rating`, `tag_list`, `kanban`, `stat_grid`, `alert_banner`, `footer_bottom` + `navbar`, `card`, `button`, `input`, `textarea`, `table`, `alert`, `badge`, `modal`, `tabs`, `sidebar`, `form`, `dropdown`, `progress_bar`, `tooltip`, `accordion`, `toast`, `pagination`, `footer`, `dropdown_menu`, `code_block`, `stat_card`, `divider`, `avatar`, `toggle`, `skeleton`, `page`, `page_from_string`

## sql — Query Builder

```kentscript
import sql, sqlite;

let db = sqlite.open("app.db");

:: SELECT with WHERE + ORDER BY + LIMIT
let q = sql.select("users", ["id", "name", "age"])
    .where("age", ">", 18)
    .order_by("name")
    .limit(10);
let rows = db.query(q.sql(), q.params());

:: INSERT
let q = sql.insert("users", {"name": "Alice", "age": 30});
db.execute(q.sql(), q.params());
db.commit();

:: UPDATE
let q = sql.update("users", {"age": 31}).where("name", "=", "Alice");
db.execute(q.sql(), q.params());

:: DELETE
let q = sql.delete_from("users").where("id", "=", 1);
db.execute(q.sql(), q.params());

:: JOIN
let q = sql.select("orders", ["orders.id", "users.name"])
    .join("users", "orders.user_id", "users.id")
    .where("orders.total", ">", 100);

:: Batch insert
let q = sql.batch_insert("users", ["name", "age"], [
    ["Bob", 25],
    ["Carol", 28],
    ["Dave", 35]
]);
db.execute(q.sql(), q.params());

:: Aggregates
let q = sql.select("orders").count("*").where("status", "=", "completed");

:: CREATE TABLE
let q = sql.create_table("users", [
    {"name": "id", "type": "INTEGER", "primary_key": true, "auto_increment": true},
    {"name": "name", "type": "TEXT", "not_null": true},
    {"name": "email", "type": "TEXT", "unique": true},
    {"name": "age", "type": "INTEGER"}
], true);
db.execute(q.sql(), q.params());

:: Raw query with params
let q = sql.raw("SELECT * FROM users WHERE name = ? AND age > ?", ["Alice", 18]);
let rows = db.query(q.sql(), q.params());

db.close();
```

## sqlite / postgres / mysql / mariadb — Database Drivers

```kentscript
:: SQLite (built-in, no dependencies)
import sqlite;
let db = sqlite.open("my.db");
db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)");
db.execute("INSERT INTO t (val) VALUES (?)", ["hello"]);
let row = db.query_one("SELECT * FROM t WHERE id = ?", [1]);
print(row);  :: [1, "hello"]
db.close();

:: SQLite in-memory
import sqlite;
let db = sqlite.in_memory();

:: PostgreSQL (requires: pip install psycopg2-binary)
import postgres;
let db = postgres.connect("localhost", 5432, "mydb", "user", "pass");
db.execute("CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT)");
db.execute("INSERT INTO users (name) VALUES ($1)", ["Alice"]);
let rows = db.query("SELECT * FROM users");
db.close();

:: MySQL (requires: pip install mysql-connector-python)
import mysql;
let db = mysql.connect("localhost", 3306, "mydb", "root", "pass");
db.execute("CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY, name TEXT)");
db.execute("INSERT INTO users (name) VALUES (?)", ["Alice"]);
let rows = db.query("SELECT * FROM users");
db.close();

:: MariaDB (requires: pip install mariadb, falls back to mysql-connector)
import mariadb;
let db = mariadb.connect("localhost", 3306, "mydb", "root", "pass");
db.execute("INSERT INTO users (name) VALUES (?)", ["Alice"]);
let rows = db.query("SELECT * FROM users");
db.close();
```

 ## socket — TCP/UDP Sockets
 
> **Compilation note:** the `socket` module shown below compiles to a native
> binary (real BSD sockets) — the same code runs interpreted or compiled
> (`kentscript build file.ks`). The example server and client above are fully
> self-contained and ready to copy/run.
 
 ```kentscript
 import socket;

:: ─── TCP Client ────────────────────────────────────────────────────────
let s = socket.tcp();
s.connect("example.com", 80);
s.send("GET / HTTP/1.1\r\nHost: example.com\r\n\r\n");
let data = s.recv(4096);
print(data);
s.close();

:: ─── TCP Server ────────────────────────────────────────────────────────
let srv = socket.tcp();
srv.set_reuseaddr();
srv.bind("0.0.0.0", 8080);
srv.listen(5);
print("Server listening on port 8080");

let result = srv.accept();
let client = result[0];
let addr = result[1];
print("Client connected from " + str(addr));

let msg = client.recv(1024);
client.send("Echo: " + msg);
client.close();
srv.close();

:: ─── UDP Client ────────────────────────────────────────────────────────
let udp = socket.udp();
udp.sendto("Hello UDP!", "127.0.0.1", 9000);
let result = udp.recvfrom(1024);
print(result[0]);  :: message
print(result[1]);  :: sender address
udp.close();

:: ─── DNS Lookup ────────────────────────────────────────────────────────
print(socket.gethostname());
print(socket.gethostbyname("example.com"));
```

## websocket — Real-Time WebSocket Communication

```kentscript
import websocket;

:: ─── WebSocket Client ──────────────────────────────────────────────────
let ws = websocket.connect("ws://localhost:8080");
ws.send("Hello server!");
let reply = ws.recv();
print(reply);
ws.close();

:: ─── WebSocket Server ──────────────────────────────────────────────────
let server = websocket.server("0.0.0.0", 8080);

server.on_connect(func(client, path) {
    print("Client connected: " + path);
});

server.on_message(func(client, msg) {
    print("Received: " + msg);
    client.send("Echo: " + msg);

    :: Broadcast to all clients
    server.broadcast("New message from someone");
});

server.on_disconnect(func(client) {
    print("Client disconnected");
});

server.start();
```

## logging — Enhanced Logging

```kentscript
import logging;

:: Basic setup
logging.basicConfig(level: logging.DEBUG);

:: Log messages
logging.info("Application started");
logging.warning("Disk space low");
logging.error("Failed to connect to database");

:: Custom logger
let log = logging.getLogger("myapp");
log.setLevel(logging.DEBUG);

:: File handler with rotation (10MB, keep 5 backups)
let fh = logging.RotatingFileHandler("app.log", 10 * 1024 * 1024, 5);
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"));
log.addHandler(fh);

:: JSON structured logging
let jh = logging.StreamHandler();
jh.setFormatter(logging.JsonFormatter());
log.addHandler(jh);

log.info("User logged in");
:: Output: {"timestamp": "2026-08-20T16:00:00", "level": "INFO", "logger": "myapp", "message": "User logged in"}
```

## Desktop GUI — New Widgets

```kentscript
import gui;

let win = gui.create_window("KentScript App", 600, 500);

:: Toast notification (auto-hides after 3 seconds)
gui.create_toast(win, "Welcome to KentScript!", 3000);

:: Status bar at the bottom
let status = gui.create_status_bar(win, "Ready");
gui.pack(status, side="bottom", fill="x");

:: Date picker with year/month/day spinboxes
let picker = gui.create_date_picker(win);
gui.pack(picker);
:: Later: let date = gui.get_date(picker);  :: "2026-08-20"

:: Right-click context menu
let menu = gui.create_context_menu(win, [
    {"text": "Copy", "command": func() { print("copy"); }},
    {"text": "Paste", "command": func() { print("paste"); }},
    "-",  :: separator
    {"text": "Select All"}
]);
:: Right-click binding:
gui.bind(win, "Button-3", func(e) { gui.show_context_menu(menu, e); });

:: Markdown viewer (renders # headings, ```code```, **bold**, - lists)
let md = gui.create_markdown_viewer(win, 60, 15);
gui.pack(md, fill="both", expand=true);
gui.render_markdown(md, "# Hello World\n\nThis is **bold** text.\n\n- Item 1\n- Item 2\n\n    code block here");

:: Theme support (apply dark/light/midnight to any widget tree)
gui.set_theme_recursive(win, "dark");
:: Available themes: "dark", "light", "midnight"
```

---

# 26.5 Standard Library Modules — Additional Reference

The modules below are shipped in `stdlib/` and imported by real `examples/*.ks`
programs. Each lists its public API and a usage sample. (For `dotenv`, `webui`,
`sql`, `socket`, `websocket`, `logging`, and GUI widgets, see the module
subsections earlier in §26.)

## argparse — Command-line argument parsing

```ks
import argparse;

let p = argparse.ArgumentParser("mytool");
p.add_argument("--name",  help="your name",        required=true);
p.add_argument("--count", type=int, default=1,     help="how many");
p.add_argument("-v",      action="store_true",     help="verbose");
let ns = p.parse_args();          :: Namespace with .name/.count/.v
println("hello", ns.name, "x", ns.count);
```

`ArgumentParser(prog)`, `.add_argument(name, help, type, default, required, action, choices)`, `.parse_args() -> Namespace`. Positional args use a bare name; flags use `--name` / `-x`. Use `argparse.get_argv()` to read raw `argv`.

## datetime — Dates, times, and formatting

```ks
import datetime;

let now = datetime.now();                 :: datetime object
println(datetime.format(now, "%Y-%m-%d %H:%M:%S"));
let later = datetime.add_days(now, 7);    :: +7 days
let ts    = datetime.to_timestamp(now);   :: epoch seconds
let dt    = datetime.fromtimestamp(ts);
datetime.is_leap_year(2024);              :: true
datetime.calculate_weekday(2024, 1, 1);  :: weekday name/index
```

Classes: `datetime`, `date`, `time`, `timedelta`. Functions: `now()`, `utcnow()`, `fromtimestamp(ts)`, `format(dt, fmt)`, `parse(s, fmt)`, `add_days(dt, n)`, `subtract_days(dt, n)`, `datetime_from_timestamp(ts)`, `datetime_to_timestamp(dt)`, `time_now()`, `time_now_utc()`, `sleep(sec)`, `is_leap_year(y)`, `days_in_month(y, m)`, `calculate_weekday(y, m, d)`.

## csv — Reading and writing CSV

```ks
import csv;

let w = csv.writer("out.csv", ",", "\"");
w.writerow(["name", "age"]);
w.writerow(["Ada", 36]);

let rows = csv.reader("out.csv");         :: list of rows
for row in rows { println(row); }

let d = csv.DictReader("out.csv");        :: rows as dicts by header
```

Classes: `Reader`, `Writer`, `DictReader`, `DictWriter`. Functions: `csv.reader(file, delimiter, quotechar)`, `csv.writer(file, delimiter, quotechar, quoting)`.

## color — Terminal colors and styles

```ks
import color;

println(color.red("error"));
println(color.bold_green("ok"));
println(color.underline("underline"));
println(color.rgb(255, 128, 0) + "orange" + color.RESET);
let g = color.gradient("fade", 255,0,0, 0,0,255);   :: multi-color gradient text
```

`colored(text, color, bg, attrs)`, convenience `red()/green()/.../bold_red()/...`,
style `bold()/dim()/italic()/underline()/blink()/reverse()`, `bg_red()/...`,
`rgb(r,g,b)`, `bg_rgb(r,g,b)`, `color256(code)`, `bg_color256(code)`, `gradient(text, r1,g1,b1, r2,g2,b2)`.

## regex — Regular expressions

```ks
import regex;

let m = regex.search(r"\d+", "abc123");
if m { println(m.group()); }              :: "123"

let nums = regex.findall(r"\d+", "a1 b22 c333");   :: ["1","22","333"]
let s    = regex.sub(r"\s+", "-", "a b  c");        :: "a-b-c"
```

`Regex` class and functions `compile(pattern, flags)`, `match`, `search`, `findall`,
`finditer`, `sub(repl, text, count)`, `split(text, maxsplit)`, `escape(s)`.
A `Match` exposes `.group()`, `.groups`, `.start`, `.end`, `.span`.

## network — Sockets (safe-mode aware)

```ks
import network;

let s = network.create_connection(("example.com", 80));
s.send("GET / HTTP/1.0\r\n\r\n");
let data = s.recv(1024);
s.close();

let server = network.create_server(("0.0.0.0", 8080));
```

`network` exposes `socket_create/bind/listen/accept/connect/send/recv/sendto/recvfrom/close/setsockopt/setblocking/settimeout`, `socket_getaddrinfo`, `gethostname`, `gethostbyname`, `inet_aton/inet_ntoa`, `htons/ntohs/htonl/ntohl`, and the `Socket` class (`create_connection`, `create_server`). `set_safe_mode(true)` + `set_allowed_hosts([...])` restrict outbound connections. Raises `ValidationError`/`SecurityError` on bad input.

## security — Validation, sanitization, crypto helpers, recon

```ks
import security;

security.is_valid_ip("8.8.8.8");          :: true
security.is_private_ip("192.168.0.1");    :: true
let h = security.hash_password("s3cret");
security.verify_password("s3cret", h);    :: true
security.sql_injection_test(user_input);  :: risk report
security.command_injection_test(arg);     :: risk report
let b = security.base64_encode("hi");     :: "aGk="
security.url_decode("%20");               :: " "
security.check_rate_limit("login:1.2.3.4", 5, 60);  :: false if over limit
security.check_open_port("host", 443);    :: port status
```

Functions: `is_safe_path`, `validate_path`, `is_safe_command`, `sanitize_command_arg`, `sanitize_string`, `sanitize_html`, `sanitize_sql`, `is_path_in_directory`, `is_safe_extension`, `is_dangerous_extension`, `is_valid_ip`, `is_private_ip`, `is_valid_port`, `is_valid_hostname`, `check_password_strength`, `generate_password`, `simple_hash`, `check_rate_limit`, `get_rate_limit_info`, `reset_rate_limit`, `xor_encrypt`, `hash_password`, `verify_password`, `encrypt_simple`/`decrypt_simple`, `generate_key`, `ip_info`, `check_open_port`, `dns_lookup`, `reverse_dns`, `check_ssl`, `get_headers`, `find_subdomains`, `sql_injection_test`, `command_injection_test`, `xss_test`, `base64_encode`/`base64_decode`, `hex_encode`/`hex_decode`, `url_encode`/`url_decode`.

## asyncio — Async/await runtime

```ks
import asyncio;

async func fetch(id) {
    await asyncio.sleep(0.1);
    return id;
}
let results = asyncio.run(asyncio.gather(fetch(1), fetch(2)));  :: [1,2]
```

Classes: `EventLoop`, `Task`, `Future`, `Queue`, `Lock`, `Semaphore`, `Event`.
Functions: `sleep`, `gather(...coros)`, `wait_for`, `shield`, `get_event_loop`, `set_event_loop`, `new_event_loop`, `run(coro)`, `create_task`, `call_later`.

## watcher — File-system watching

```ks
import watcher;

let w = watcher.FileWatcher();
w.watch(".", |ev| { println("changed:", ev.path, ev.type); });
w.start();
```

`FileWatcher` with `.watch(path, callback)`, `.start()`, `.stop()`.

## bitwise — Bit manipulation helpers

```ks
import bitwise;

bitwise.popcount(0b1011);     :: 3
bitwise.byte_swap(0x1234);    :: 0x3412
bitwise.bit_set(0b0001, 2);   :: 0b0101
bitwise.is_power_of_2(16);    :: true
```

`bit_and/or/xor/not/shl/shr/ushr/rol/ror`, `popcount`, `clz`, `ctz`, `bit_test/set/clear/toggle`, `bit_extract`, `bit_replace`, `bit_sign_extend`, `bit_zero_extend`, `byte_swap`, `bit_reverse`, `bit_mask`, `is_power_of_2`, `next_power_of_2`, `prev_power_of_2`, `swap`. (Equivalent `bit_*` builtins also exist — see §28.)

## cache — TTL cache

```ks
import cache;

let c = cache.Cache();
c.set("k", 42, ttl=60);
c.get("k");     :: 42
c.has("k");     :: true
```

`Cache` with `get`, `set(key, value, ttl)`, `has`, `delete`, `clear`.

## collections — Extra data structures

```ks
import collections;

let dq = collections.Deque();
dq.push_back(1); dq.push_front(2);
let cnt = collections.Counter(["a", "b", "a"]);   :: counts occurrences
let od  = collections.OrderedDict();
```

`Stack`, `Queue`, `Deque`, `OrderedDict`, `DefaultDict`, `Counter`, `ChainMap`, `Heap`, `ListNode`, `LinkedList`.

## config — Config file loading

```ks
import config;

let cfg = config.load_config("app.json", "json");
let cfg2 = config.load_config("app.ini", "ini");
```

`ConfigParser`, `JSONConfig`, `load_config(filename, format)`.

## functools — Higher-order function tools

```ks
import functools;

let inc = functools.partial(add, 1);     :: add(x, 1)
let cached = functools.memoize(expensive);
let comp = functools.compose(f, g);
```

`partial`, `partialmethod`, `compose`, `pipe`, `memoize`, `lru_cache`, `cached_property`, `curry`, `reduce`, `accumulate`, `wraps`, `singledispatch`, `throttle`, `debounce`, `delay`, `once`, `identity`, `flip`, `tryCatch`, `maybe`, `cond`, `tap`.

## image — Image processing (wraps system tools)

```ks
import image;

image.resize("in.png", "out.png", 128, 128);
image.grayscale("in.png", "gray.png");
image.crop("in.png", "c.png", 100, 100, 0, 0);
```

`convert`, `info`, `resize`, `thumbnail`, `format`, `grayscale`, `blur`, `rotate`, `crop`.

## pathlib — Object-oriented paths

```ks
import pathlib;

if pathlib.fs_exists("data") {
    let txt = pathlib.fs_read_text("data/in.txt");
    let items = pathlib.fs_listdir("data");
}
```

`Path` class and helpers `cwd()`, `home()`, `fs_exists`, `fs_is_file`, `fs_is_dir`, `fs_mkdir`, `fs_read_text`, `fs_write_text`, `fs_read_bytes`, `fs_write_bytes`, `fs_listdir`, `fs_walk`, `fs_rename`, `fs_remove`, `fs_symlink`.

## template — String templates

```ks
import template;

let out = template.render("Hello {{ name }}!", { name: "World" });
```

`Template` class, `render(template_string, context)`, `render_file(filename, context)`, `TemplateFilters`.

## testing — Lightweight test harness

```ks
import testing;

testing.test("adds", || { testing.assert_equal(1 + 1, 2); });
testing.test("truthy", || { testing.assert_true(1); });
```

`TestCase`, `test(name, fn)`, `assert_equal`, `assert_true`, `assert_false`.

## validation — Schema/value validation

```ks
import validation;

validation.validate_email("a@b.com");        :: ok
validation.validate_integer("42", 0, 200);   :: ok
```

`validate_string`, `validate_email`, `validate_url`, `validate_number`, `validate_integer`, `validate_array`, `validate_object`.

## ffi — Foreign-function interface

```ks
import ffi;

let lib = ffi.ffi_load("libc.so.6");
let sym = ffi.ffi_get_symbol(lib, "printf");
ffi.ffi_call(sym, ["hello\n"], ["ptr"], "i32");
```

`CLibrary`, `CFunction`, `CDLL(path)`, `ffi_load/close/get_symbol/call`, `cast`, `sizeof`, `addressof`, `pointer`, `string_at`, `memmove`, `memset`, `create_string_buffer`, `Structure`, `Union`.

## dataclass — Quick data classes

```ks
import dataclass;

let Point = dataclass.make("Point", ["x", "y"], { x: 0, y: 0 });
let p = Point(x = 1, y = 2);
```

`dataclass.make(name, field_names, defaults)` returns a class.

---

# 27. Platform & Tooling

KentScript runs on **Linux**, **macOS**, and **Windows** (including Windows 7+). The interpreter, C transpiler, inline assembly, and syscalls all work cross-platform. The build system auto-detects your platform, compiler, and architecture.

## Supported Platforms

| Feature | Linux x86-64 | Linux ARM64 | macOS x86-64 | macOS ARM64 | Windows 7+ (x86-64) |
|---------|:---:|:---:|:---:|:---:|:---:|
| Interpreter | ✅ | ✅ | ✅ | ✅ | ✅ |
| C Transpiler | ✅ | ✅ | ✅ | ✅ | ✅ |
| Syscalls | ✅ libc | ✅ libc | ✅ libsystem_kernel | ✅ libsystem_kernel | ✅ ntdll Nt* |
| Inline Assembly | ✅ Intel | ✅ ARM64 | ✅ Intel | ✅ ARM64 | ✅ Intel |
| Port I/O (inb/outb) | ✅ root | ❌ ARM | ❌ | ❌ | ❌ |
| MMIO | ✅ root | ✅ root | Returns 0 | Returns 0 | Returns 0 |
| MSR Access | ✅ root | ❌ ARM | ❌ | ❌ | ❌ |
| WASM Backend | ✅ | ✅ | ✅ | ✅ | ✅ |

## Compilation Backends

| Backend | Command | Output |
|---------|---------|--------|
| C Transpiler (gcc/clang) | `build` | Native binary (ELF on Linux, Mach-O on macOS, PE on Windows) |
| WASM Backend | `wasm build` | `.wasm` binary via wat2wasm |

## WASM Backend

The WASM backend (`backends/wasm/`) compiles KentScript source to WebAssembly via WAT (WebAssembly Text Format). It supports integer (i64), float (f64), and bool (i32) types, control flow, functions, recursion, print output via WASI, and pattern matching.

### Requirements

| Tool | Purpose | Install |
|------|---------|---------|
| `wat2wasm` | WAT → WASM binary conversion | [wabt](https://github.com/WebAssembly/wabt) (`apt install wabt`) |
| `wasmtime` | WASM runtime (recommended) | `curl https://wasmtime.dev/install.sh \| bash` |
| `node` | Alternative WASM runtime | `apt install nodejs` |

### Usage

```bash
# Compile .ks → .wasm binary
./kentscript wasm build file.ks

# Compile and run immediately
./kentscript wasm build file.ks --run

# Generate WAT text only (debug)
./kentscript wasm wat file.ks

# Run an existing .wasm binary
./kentscript wasm run file.wasm

# Check toolchain status
./kentscript wasm info
```

### Example

```kentscript
func add(a: int, b: int) -> int {
    return a + b;
}

func main() {
    let x = 42;
    let y = 58;
    let z = add(x, y);
    print(z);   :: 100
}
```

```bash
./kentscript wasm build examples/test_wasm.ks
./kentscript wasm run examples/test_wasm.wasm
# Output: 100
```

### Architecture

The WASM backend consists of three components:

| Component | File | Role |
|-----------|------|------|
| Transpiler | `backends/wasm/wasm_transpiler.py` | KentScript AST → WAT instructions |
| Runtime | `backends/wasm/wasm_runtime.py` | WASI imports, bump allocator, print helpers (i32/i64/f64), string ops, math helpers |
| Backend | `backends/wasm/wasm_backend.py` | Build pipeline: lex → parse → transpile → runtime + code → wat2wasm → .wasm |

The transpiler generates type-aware WAT: `int`/`uint` → `i64`/`u64`, `float` → `f64`, `bool`/`char` → `i32`. The runtime provides `$__ks_print_i32`, `$__ks_print_i64`, `$__ks_print_f64`, `$__ks_print_char`, allocator, and WASI polyfills. The backend wraps both into a single `(module ...)` and invokes `wat2wasm` for binary output.

### Supported Features

- ✅ Functions with typed parameters and return values
- ✅ `let` variables (i64, f64, bool, str)
- ✅ Arithmetic (`+`, `-`, `*`, `/`, `%`) with type dispatch
- ✅ Comparison (`==`, `!=`, `<`, `>`, `<=`, `>=`)
- ✅ If/elif/else, while, for loops
- ✅ `print`/`println` output via WASI
- ✅ Match statements
- ✅ Recursion
- ✅ WAT-only debug mode
- ✅ Strings (literals, concat, comparison, print via WASI)
- ✅ Classes (methods, `self` field access), structs (def, literal, field access), arrays (literal, get/set, len, append, pop), dicts (literal, get/set via hash table)
- ❌ C backend integration

## Bare-Metal & Kernel

- `minios` — Build and run a bare-metal OS kernel via QEMU
- `ring0` — Compile C to freestanding kernel ELF (x86-64, AArch64, RISC-V)
- `kernel-dev` — Generate kernel subsystem C files (GDT, IDT, scheduler, etc.)

> **Note:** Bare-metal/kernel features are Linux x86-64 only (require QEMU + cross-compilation tools).

## Platform Installers

KentScript ships prebuilt installers on the **`main`** branch. The **`source`** branch contains only source code and `build_binary.py`.

| Platform | Installer | Command |
|----------|-----------|---------|
| Linux | `install.sh` | `curl -fsSL https://github.com/musikaalvin/kentscript/raw/main/install.sh \| bash` |
| macOS | `install.sh` | Same as Linux (auto-detects architecture) |
| Windows | `install.ps1` | `iex (New-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/musikaalvin/kentscript/main/windows/install.ps1')` |
| Windows | `KentScript-Setup-3.1.0.exe` | Download from [Releases](https://github.com/musikaalvin/kentscript/releases) |

### Build All Platforms (from source)

```bash
git clone --branch source https://github.com/musikaalvin/kentscript.git
cd kentscript
python3 build_binary.py --all
```

Generates: `dist/kentscript` (Linux/macOS), `dist/windows/` (Windows), `dist/macos/` (macOS Homebrew), `dist/manifest.json`.

## Debugging & Analysis

- `debug` — Step-through debugger with breakpoints and variable inspection
- `audit` — 10-part forensic binary verification
- `privilege_report` — 9-level truth ladder from userland to bare metal (note: underscore, not hyphen)
- `hardware` — Hardware discovery, MMIO read, MSR access

## Security

- `security` — Ethical pentesting console (port scanning, OSINT, hash cracking, WiFi/SSH auditing, encryption, forensics)
- Modules include: ARP spoof detector, brute forcer, file crypter, hash cracker, WiFi cracker, ZIP brute forcer, GPT parser, dumper

---

# 28. Quick Reference

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
let, mut, const      :: Variables
func, return, yield  :: Functions
class, struct, enum, union  :: Types
interface, trait, implements, impl, extension  :: Interfaces & types
if, elif, else       :: Conditionals
while, for, in, do   :: Loops
match, case, switch, default  :: Pattern/switch matching
try, except, catch, finally, raise  :: Error handling
unsafe, safe         :: Low/safe-level blocks
import, export, from, as, module  :: Modules
async, await         :: Async
new, del, pass       :: Object lifecycle
global, nonlocal     :: Scope
with, assert         :: Resource mgmt / assertions
type                 :: Type aliases
borrow, release, move :: Memory safety
lambda               :: Lambda expressions
static, inline, volatile  :: Function/variable modifiers
asm, goto            :: Low-level (asm blocks, goto)
none                 :: Null/none literal
to                   :: Range/ownership syntax (0..5, move x to y)
sizeof               :: Size-of operator
```

## Types

```
i8, i16, i32, i64    :: Signed integers
u8, u16, u32, u64    :: Unsigned integers
f32, f64             :: Floating point
bool, str, char, ptr  :: Other types
int                  :: Alias for i64
uint                 :: Alias for u64
float                :: Alias for f64
string               :: Alias for str
void                 :: No return value
```

## Built-in Functions

```
Core:        print, println, input, len, range, map, filter, reduce
Type:        type, typeof, sizeof, str, int, float, bool, format_value
Math:        sum, min, max, sorted, reversed, abs, pow, sqrt, round,
             floor, ceil, sin, cos, tan, log, exp
Conversions: hex, bin, oct, chr, ord, enumerate, zip
Logic:       all, any
I/O:         open, read, write, close, read_file, write_file,
             write_string, read_string, memory_stats
Debug:       panic, dbg, assert_eq, assert_ne, assert_true, assert_false
Concurrency: thread, Lock, RLock, Event, Semaphore, ThreadPool
Decorators:  kernel, interrupt, syscall, naked, always_inline,
             aligned, section, volatile_mem, packed
Low-level:   malloc, free, memcpy, memset, ptr_read, ptr_write,
             syscall, asm, fn_ptr, call_ptr, bit_* helpers
Type names:  i8..i64, u8..u64, f32, f64, bool, str, char, void, int, uint, ptr
kpm:         kpm_install, kpm_uninstall, kpm_list, kpm_search, kpm_version
```

String/dict methods (no import needed):
```
s.upper(), s.lower(), s.title(), s.capitalize()
s.contains(), s.startswith(), s.endswith()
s.find(), s.replace(), s.split(), s.join()
s.trim(), s.strip()
d.keys(), d.values(), d.items()
arr.append(), arr.insert(), arr.remove(), arr.pop()
```

Common built-in usage samples:

```ks
// Conversions
hex(255)        :: "0xff"
bin(10)         :: "0b1010"
oct(8)          :: "0o10"
chr(65)         :: "A"
ord('A')        :: 65
enumerate([10, 20, 30])   :: [(0,10),(1,20),(2,30)]
zip([1,2],[3,4])          :: [(1,3),(2,4)]
all([true, 1, "x"])        :: true
any([0, none, 5])          :: true

// Debug / assertions
dbg(state)                 :: prints [dbg] <repr> and returns it
assert_eq(a, b)            :: throws AssertionError if a != b
assert_true(cond)          :: throws if cond is falsy
panic("boom")              :: throws RuntimeError

// Bit manipulation
bit_count(0b1011)          :: 3   (popcount)
bit_test(0b1000, 3)        :: 1
bit_set(0b0001, 2)         :: 0b0101
is_power_of_2(16)          :: true
next_power_of_2(1000)      :: 1024

// Function pointers (unsafe / FFI)
let p = fn_ptr(my_func)
call_ptr(p, [arg1, arg2])

// Spawn a thread
thread(|| { println("running"); })
```

Kernel / bare-metal decorators (documented in §16 / bare-metal sections):

```ks
@kernel
func kernel_main() { ... }

@interrupt(32)
func timer_handler() { ... }

@syscall(1)
func sys_write() { ... }

@packed
struct Header { magic: u32; flags: u16; }
```

## Modules (short form — no `system_` prefix)

```
import os;             os.getpid(), os.mkdir(), os.exists(), ...
import time;           time.time(), time.sleep()
import random;         random.random(), random.randint(), random.choice()
import http;           http.get(), http.post()
import subprocess;     subprocess.run()
import crypto;         crypto.base64_encode(), crypto.hex_encode()
import string;         string.upper(), string.contains(), ...
import sys;            sys.getpid(), sys.getenv()
import hardware;       hardware.read_port(), hardware.outb(), ...

kpm_install/list/search/version/uninstall  :: Package manager
```

## Unsafe Functions

```
malloc, free, calloc, realloc      :: Memory management
ptr_read, ptr_write                :: Pointer operations
read_byte, write_byte              :: Byte-level memory access
read_word, write_word              :: Word-level memory access
memcpy, memset, memmove            :: Memory operations
syscall                            :: Raw syscall (Linux/macOS/Windows)
rdtsc                              :: CPU timestamp counter (x86)
mmap, munmap                       :: Memory map/unmap (all platforms)
outb, outw, outl                   :: I/O port write
inb, inw, inl                      :: I/O port read
msr_read                           :: Read Model-Specific Register
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
- **Created:** 19th February 2026
- **Author:** pyLord (Musika Alvin) - Uganda
- **Language:** Python core (~72K) + C runtime (~6.4K) + KentScript stdlib (~19K) + JS LSP (~1.8K) = ~99K total
- **License:** MIT

## Releases & Updates

New versions are published on GitHub Releases:
- **Latest Release**: https://github.com/musikaalvin/kentscript/releases
- **Install Script**: https://raw.githubusercontent.com/musikaalvin/kentscript/main/install.sh

To update to the latest version:
```bash
curl -sL https://raw.githubusercontent.com/musikaalvin/kentscript/main/install.sh | bash
```

## Getting Help

```bash
./kentscript --help              :: CLI help
./kentscript run --help          :: Run options
./kentscript build --help        :: Build options
./kentscript                      :: Interactive REPL
```

---

# 29. Hardware Acceleration (SIMD / GPU)

KentScript ships with **real** vectorization and GPGPU compute — not stubs. The
same source adapts automatically to the target ISA, both in the interpreter
(NumPy-backed) and in native binaries (genuine vector/SIMD instructions).

## 28.1 Overview

| Backend | How it works | Notes |
|---------|--------------|-------|
| **CPU SIMD** (`simd`) | Portable compiler vector extensions in `ks_simd.h` emit **NEON** (ARM), **AVX / AVX2 / AVX-512** (x86), and similar on RISC-V/SVE | Verified to produce real vector instructions in the compiled binary (e.g. `fadd v0.4s` on ARM) |
| **GPU — OpenCL** (`gpu`) | Real OpenCL loaded at runtime via `dlopen` (no link-time GPU dependency), with an automatic **CPU-SIMD fallback** when no OpenCL platform exists | Most portable GPGPU path (NVIDIA/AMD/Intel/ARM Mali/Adreno/Apple) |
| **GPU — CUDA** (`gpu.cuda_*`) | Secondary backend via the CUDA Driver API + on-device PTX JIT, also `dlopen`-based | Activated only when a CUDA driver + GPU are present |
| **Interpreter** | Backed by **NumPy** when installed (genuine data-parallel SIMD); exact Python fallback otherwise | Legacy `system_simd_*` / `system_neon_*` builtins are also real and NumPy-backed |

The pipeline is: `Lexer → Parser → AST → C Transpiler → gcc`. `import simd`
and `import gpu` inject `ks_simd.h` / `ks_gpu.h` into the generated C, so the
SIMD/GPU calls become real hardware instructions in the binary.

## 28.2 The `simd` module (CPU vectorization)

Typed vector buffers are allocated with `simd.alloc_<kind>(n)` where `<kind>` is
one of `f32`, `f64`, `i32`, `i64`. Elements are accessed with `set_*` / `get_*`.

| Method | Description |
|--------|-------------|
| `alloc_f32(n)` … `alloc_i64(n)` | Allocate a typed vector buffer (returns a pointer in native, a NumPy array in the interpreter) |
| `free_f32(b)` … `free_i64(b)` | Free a buffer |
| `set_f32(b,i,v)` … `set_i64(b,i,v)` | Write element `i` |
| `get_f32(b,i)` … `get_i64(b,i)` | Read element `i` |
| `add_f32(a,b,c,n)` … `div_i64(a,b,c,n)` | Element-wise `c = a OP b` (real SIMD) |
| `scale_f32(b,s,n)` … `scale_i64(b,s,n)` | Multiply every element by scalar `s` |
| `addc_f32(b,c,n)` … `addc_i64(b,c,n)` | Add scalar `c` to every element |
| `fma_f32(a,b,c,n)` … `fma_i64(a,b,c,n)` | Fused multiply-add: `out = a*b + c` |
| `sum_f32(b,n)` … `sum_i64(b,n)` | Reduction sum (SIMD) |
| `dot_f32(a,b,n)` … `dot_i64(a,b,n)` | Dot product (SIMD reduction) |
| `arch()` | Target SIMD architecture name: `arm-neon`, `x86-avx2`, `x86-avx512`, … |
| `width()` | SIMD register width in bytes |

```kentscript
import simd;
let n = 1024;
let a = simd.alloc_f32(n);
let b = simd.alloc_f32(n);
let c = simd.alloc_f32(n);
for i in range(0, n) {
    simd.set_f32(a, i, 1.5);
    simd.set_f32(b, i, 2.5);
}
simd.add_f32(a, b, c, n);          :: c = a + b  (vectorized)
simd.scale_f32(c, 2.0, n);         :: c *= 2.0
print("arch: " + simd.arch());     :: arm-neon / x86-avx2 / x86-avx512 ...
print("sum:  " + str(simd.sum_f32(c, n)));
print("dot:  " + str(simd.dot_f32(a, b, n)));
simd.free_f32(a); simd.free_f32(b); simd.free_f32(c);
```

> **Note on `str()` and string returns:** `simd.arch()` and `gpu.name()`
> return strings. You can store them directly (`let a = simd.arch();`) or print
> them inside a concatenation (`print("arch: " + simd.arch());`). The
> transpiler resolves their string type automatically.

## 28.3 The `gpu` module (GPGPU compute)

Same typed-buffer model as `simd`. When a GPU/OpenCL platform is present the
`gpu.*` math ops run on the device; otherwise they transparently use the real
CPU-SIMD path. Use `gpu.available()` / `gpu.name()` (and `gpu.cuda_available()`
/ `gpu.cuda_name()`) to introspect.

| Method | Description |
|--------|-------------|
| `available()` | `1` if a GPU/OpenCL backend initialized, else `0` |
| `name()` | Device name, or `"cpu-fallback"` |
| `cuda_available()` | `1` if a CUDA driver + GPU is present |
| `cuda_name()` | CUDA device name, or `"cpu-fallback"` |
| `alloc_f32(n)` … `alloc_i64(n)` | Allocate buffer (pointer in native, NumPy array in interpreter) |
| `free_f32(b)` … `free_i64(b)` | Free buffer |
| `set_f32(b,i,v)` … `set_i64(b,i,v)` | Write element |
| `get_f32(b,i)` … `get_i64(b,i)` | Read element |
| `add_f32(a,b,c,n)` … `div_i64(a,b,c,n)` | Element-wise `c = a OP b` (GPU if present, else SIMD) |
| `scale_f32(b,s,n)` … `scale_i64(b,s,n)` | Scalar multiply |
| `sum_f32(b,n)` … `sum_i64(b,n)` | Reduction sum |
| `dot_f32(a,b,n)` … `dot_i64(a,b,n)` | Dot product |

```kentscript
import gpu;
print("gpu available: " + str(gpu.available()));
print("gpu name: " + gpu.name());
let n = 1024;
let a = gpu.alloc_f32(n);
let b = gpu.alloc_f32(n);
let c = gpu.alloc_f32(n);
for i in range(0, n) {
    gpu.set_f32(a, i, 1.5);
    gpu.set_f32(b, i, 2.5);
}
gpu.add_f32(a, b, c, n);            :: runs on GPU if present, else SIMD
print("c[0] = " + str(gpu.get_f32(c, 0)));
print("sum  = " + str(gpu.sum_f32(c, n)));
gpu.free_f32(a); gpu.free_f32(b); gpu.free_f32(c);
```

## 28.4 Pythonistic wrappers — `stdlib/accel.ks`

For a more Mojo-like feel, `import accel;` provides list-in / list-out helpers
built on the `simd` / `gpu` modules. These compile to self-contained C SIMD
helpers (`ks_accel_*` in `include/ks_legacy_simd.h`) in the native backend as
well, so `accel.*` works identically in both interpreter and compiled modes:

| Function | Description |
|----------|-------------|
| `accel.vector_add(a, b)` | Element-wise `a + b` → new list (real SIMD) |
| `accel.vector_scale(a, s)` | Element-wise `a * s` → new list |
| `accel.vector_dot(a, b)` | Dot product → scalar |
| `accel.gpu_vector_add(a, b)` | Element-wise `a + b` on the GPU (or SIMD fallback) |

```kentscript
import accel;
let c = accel.vector_add([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]);  :: [5.0, 7.0, 9.0]
let d = accel.vector_dot([1.0, 2.0], [3.0, 4.0]);            :: 11.0
```

> The native backend transpiles `accel.*` directly into `ks_accel_*`
> C SIMD helpers (with a CPU-SIMD code path mirroring the `gpu` fallback), so the
> high-level wrappers are fully supported in compiled binaries too.

## 28.5 Legacy SIMD builtins

The `system_simd_*` / `system_simd256_*` / `system_simd512_*` /
`system_neon_*` builtins are also real and NumPy-backed (e.g.
`system_simd_add_f32(a, b)`, `system_neon_add_u8(a, b)`,
`system_simd512_mul_f32(a, b)`). They compile to portable C via
`include/ks_legacy_simd.h` in the native backend (bit-stored IEEE-754 floats,
raw integer lists), with an exact Python fallback in the interpreter. They are
kept for low-level/historical use; prefer the `simd` / `gpu` modules for new
code.

## 28.6 Support matrix

| API | Interpreter | Native |
|-----|-------------|--------|
| `simd.*` (alloc/get/set/arith/sum/dot/arch/width) | ✅ | ✅ (real NEON/AVX/AVX-512) |
| `gpu.*` (OpenCL + CUDA + SIMD fallback) | ✅ | ✅ |
| `system_simd_*` / `system_neon_*` builtins | ✅ | ✅ (real — `ks_legacy_simd.h`) |
| `stdlib/accel.ks` high-level wrappers | ✅ | ✅ (`ks_accel_*` SIMD helpers) |

> **Note — float lists in the native backend:** numeric list literals containing
> floats are stored as bit-patterns (`struct`/`union` round-trip of IEEE-754
> doubles), so `let f = [1.5, 2.5, 3.25]; f[0]` reads back exactly `1.5`.
> Integer-list elements remain plain `long long`; string-list elements remain
> `char*`. This is an implementation detail of the C transpiler and is invisible
> at the language level.

### 28.7 The `os` module — security in both backends

`import os;` exposes a security-hardened OS interface (`stdlib/os.ks`). The
**same** safety policy that guards the interpreter also guards compiled
binaries:

* **Safe mode (on by default).** Absolute paths outside `/home/` and `/tmp/`
  are rejected, as are `..` traversals. Use `os.set_safe_mode(false)` to relax
  (mirrors the interpreter).
* **Command-injection guard.** `os.system` / `os.popen` reject `;`, `&&`,
  `||`, `|`, backtick, `$(` and `${`.

In the native backend the transpiler routes every `os.*` call through guarded
helpers in `include/ks_os.h` (`ks_os_*`), which mirror `stdlib/os.ks` and call
the real libc/POSIX functions. `os.write_file` / `os.read_file` /
`os.append_file` are also supported natively (they were previously no-ops in
compiled code).

> Because the C backend has no exception mechanism (the transpiler compiles
> `try/except` as best-effort no-op, by design), a rejected operation prints a
> `SecurityError:` message to stderr and **skips the OS action** (returning a
> safe default) instead of raising. The security guarantee — the dangerous
> operation is *blocked* — holds in both backends; only the control-flow
> differs (raise vs. block-and-continue).

| API | Interpreter | Native |
|-----|-------------|--------|
| `os.name/getcwd/getpid/getuid/getgid/environ` | ✅ | ✅ |
| `os.chdir/mkdir/makedirs/rmdir/remove/rename/stat` | ✅ | ✅ (guarded) |
| `os.exists/isfile/isdir/islink/readlink` | ✅ | ✅ (guarded) |
| `os.getenv/putenv/unsetenv` | ✅ | ✅ |
| `os.system/popen` | ✅ | ✅ (command-injection guarded) |
| `os.write_file/read_file/append_file` | ✅ | ✅ (guarded) |
| `os.set_safe_mode/set_allowed_dirs` | ✅ | ✅ |
| path-traversal + injection guards | ✅ | ✅ (`ks_os.h`) |

See `examples/os_files.ks` for a runnable demonstration that is byte-identical
in both interpreter and compiled modes.

See `examples/simd_demo.ks`, `examples/gpu_demo.ks`, and
`examples/regression_simd_gpu.ks` for runnable, self-checking demonstrations.
