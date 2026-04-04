:: KentScript Low-Level Features Demo
:: This file demonstrates all implemented low-level programming features

print("=== KentScript Low-Level Features Demo ===");
print("");

:: ============================================
:: 1. TYPE ALIASES
:: ============================================
print("1. Type Aliases:");
let count: int = 42;
let size: uint = 1024;
let ratio: float = 3.14159;
print(f"  int: {count}");
print(f"  uint: {size}");
print(f"  float: {ratio}");
print("");

:: ============================================
:: 2. F-STRING INTERPOLATION
:: ============================================
print("2. F-String Interpolation:");
let lang = "KentScript";
let year = 2024;
print(f"  {lang} was created in {year}");
print(f"  Expression: 2 + 2 = {2 + 2}");
print("");

:: ============================================
:: 3. TUPLE DESTRUCTURING
:: ============================================
print("3. Tuple Destructuring:");
let (x, y, z) = (100, 200, 300);
print(f"  x={x}, y={y}, z={z}");
let (a, b) = (10, 20);
print(f"  a={a}, b={b}");
print("");

:: ============================================
:: 4. ARRAYS
:: ============================================
print("4. Arrays:");
let numbers = [1, 2, 3, 4, 5];
print(f"  Array: {numbers}");
print(f"  First element: {numbers[0]}");
print(f"  Last element: {numbers[4]}");
print("");

:: ============================================
:: 5. LOW-LEVEL OPERATIONS (UNSAFE)
:: ============================================
print("5. Low-Level Operations (unsafe block):");

unsafe {
    :: Address-of operator
    print("  a) Address-of operator (&):");
    let value = 12345;
    let addr = &value as ptr;
    print(f"     value = {value}");
    print(f"     &value = {addr}");
    print("");
    
    :: Type casting
    print("  b) Type Casting (as):");
    let pi = 3.14159;
    let pi_int = pi as int;
    print(f"     {pi} as int = {pi_int}");
    
    let hex_val = 0xFF;
    let hex_ptr = hex_val as ptr;
    print(f"     0xFF as ptr = {hex_ptr}");
    print("");
    
    :: Pointer arithmetic (conceptual)
    print("  c) Pointer Values:");
    let base = 0x1000 as ptr;
    let offset = 0x100 as ptr;
    print(f"     Base address: {base}");
    print(f"     Offset: {offset}");
    print("");
    
    :: Assembly instructions
    print("  d) Inline Assembly:");
    asm("nop");
    print("     Executed: asm(\"nop\")");
    asm("mov eax, 0");
    print("     Executed: asm(\"mov eax, 0\")");
};

print("");

:: ============================================
:: 6. COMBINED EXAMPLE
:: ============================================
print("6. Combined Example:");
let data: int = 0xDEADBEEF;
print(f"  Original value: {data}");

unsafe {
    let data_addr = &data as ptr;
    print(f"  Address: {data_addr}");
    
    let as_float = data as float;
    print(f"  As float: {as_float}");
    
    let (high, low) = (data, data);
    print(f"  Split: high={high}, low={low}");
};

print("");
print("=== All Features Working! ===");
