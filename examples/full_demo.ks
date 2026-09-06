:: KentScript Capabilities Demo (Compiler-compatible)
:: Run: kentscript full_demo.ks
:: Or: kentscript build full_demo.ks && ./full_demo

import time;
import math;
import random;

print("╔══════════════════════════════════════════╗");
print("║     KENTSCRIPT CAPABILITIES DEMO        ║");
print("╚══════════════════════════════════════════╝");
print("");

print("=== 1. BASIC TYPES ===");
let num = 42;
let flt = 3.14;
let greeting = "Hello";
let flag = true;
print("Integer: " + str(num));
print("Float: " + str(flt));
print("String: " + greeting);
print("Boolean: " + str(flag));
print("");

print("=== 2. FUNCTIONS ===");
let add = func(a, b) { return a + b; };
let multiply = func(a, b) { return a * b; };
print("add(3, 5) = " + str(add(3, 5)));
print("multiply(4, 7) = " + str(multiply(4, 7)));
print("");

print("=== 3. CONTROL FLOW ===");
let x = 5;
if x > 3 { print("x > 3 is true"); }

let sum = 0;
let i = 0;
while i < 10 { sum = sum + i; i = i + 1; }
print("While sum(0-9): " + str(sum));
print("");

print("=== 4. MATH ===");
print("sqrt(16): " + str(math.sqrt(16)));
print("sin(0): " + str(math.sin(0)));
print("pow(2, 8): " + str(math.pow(2, 8)));
print("abs(-42): " + str(math.abs(-42)));
print("");

print("=== 5. RANDOM ===");
print("random(): " + str(random.random()));
print("randint(1,100): " + str(random.randint(1, 100)));
print("");

print("=== 6. STRING OPS ===");
let s1 = "Hello";
let s2 = "World";
print("s1 + s2: " + s1 + " " + s2);
print("len(s1): " + str(len(s1)));
print("");

print("=== 7. BENCHMARK ===");
let start = time.time();
let result = 0;
let n = 0;
while n < 500000 {
    result = result + n * n - n / 2;
    n = n + 1;
}
let elapsed = time.time() - start;
print("Integer loop (500K): " + str(elapsed) + " seconds");
print("Result: " + str(result));
print("");

print("=== 8. RECURSION ===");
let fib = func(n) {
    if n <= 1 { return n; }
    return fib(n - 1) + fib(n - 2);
};
print("fib(10): " + str(fib(10)));
print("fib(12): " + str(fib(12)));
print("");

print("╔══════════════════════════════════════════╗");
print("║         ALL TESTS COMPLETE!             ║");
print("╚══════════════════════════════════════════╝");
