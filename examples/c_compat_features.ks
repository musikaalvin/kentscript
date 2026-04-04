:: KentScript with Full C Compatibility
:: All C features available directly in KentScript

:: C-style function declarations (already supported)
func add(a: i32, b: i32) -> i32 {
    return a + b;
}

:: C-style pointers (add support)
unsafe {
let x: i32 = 0;
let ptr: *i32 = &x;
let value: i32 = *ptr;
}

:: C-style arrays (add support)
let arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
let matrix = [[1,2,3], [4,5,6], [7,8,9]];

:: C-style structs (add support)
struct Point {
    x: i32,
    y: i32
}

:: C-style enums (add support)
enum Color {
    RED = 0,
    GREEN = 1,
    BLUE = 2
}

:: C-style typedef (add support)

:: C-style for loops (add support)
for i in range(0, 10) {
    print(i);
}

:: C-style switch (add support)
let x: i32 = 1;
switch (x) {
    case 1: print("one");
    case 2: print("two");
    default: print("other");
}



:: Inline C code (add support) - SKIPPED: c_code block not implemented

:: C-style casting
let x: i32 = 42;
let y: i32 = 27;  :: Using integer for bitwise operations

:: C-style operators (all supported)
let a: i32 = x & y;   :: bitwise AND
let b: i32 = x | y;   :: bitwise OR
let c: i32 = x ^ y;   :: bitwise XOR
let d: i32 = ~x;      :: bitwise NOT
let e: i32 = x << 2;  :: left shift
let f: i32 = x >> 2;  :: right shift;

:: C-style compound assignments
x += 1;
x -= 1;
x *= 2;
x = x // 2;  :: integer division
x %= 3;
x &= 0xFF;
x |= 0x01;
x ^= 0xFF;
x <<= 1;
x >>= 1;

:: C-style increment/decrement
x++;

:: C-style ternary
let max: i32 = (a > b) ? a : b;

:: C-style sizeof
let size: i32 = sizeof(i32);
let arr_size: i32 = sizeof(arr);


:: C-style character literals
let ch: char = 'A';
let newline: char = '\n';

:: C-style function pointers
:: Not yet implemented - disabled
:: let result: i32 = func_ptr(10, 20);


:: C-style inline assembly (already supported)
unsafe {
    asm("mov rax, 42");
}
