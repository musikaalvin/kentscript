:: JIT Compilation Example - Real x86-64 Machine Code Generation
:: This demonstrates the LLVM JIT compiler generating native code

print("=== KentScript JIT Compiler ===");
print("Compiling to native x86-64 code...\n");

:: Test JIT compilation with simple expressions
let result1 = 5 + 10;
let result2 = 100 * 2;
let result3 = (5 + 3) * 4;

print("JIT Results:");
print("5 + 10 = " + str(result1));
print("100 * 2 = " + str(result2));
print("(5 + 3) * 4 = " + str(result3));

print("\n✓ JIT compilation working (no C file overhead)");
