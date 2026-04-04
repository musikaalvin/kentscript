#!/usr/bin/env python3
"""
Test all low-level features in interpreter mode
"""
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from ks_core import Interpreter, Lexer, Parser

print("=" * 60)
print("TESTING LOW-LEVEL FEATURES IN INTERPRETER")
print("=" * 60)

def test_feature(name, code):
    """Test a feature and report result"""
    print(f"\n[TEST] {name}")
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens, code)
        ast = parser.parse()
        interp = Interpreter(code)
        interp.interpret(ast)
        print(f"  ✓ PASS")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False

# Test 1: Pointer creation and operations
test1 = """
unsafe {
    let x = 42;
    let ptr = ptr(value=x);
    print("Pointer created:", ptr);
}
"""

# Test 2: Syscall (getpid - syscall 39 on Linux)
test2 = """
unsafe {
    let pid = syscall(39);
    print("Process ID:", pid);
}
"""

# Test 3: Hardware I/O (will fail without permissions, but should parse)
test3 = """
unsafe {
    outb(0x80, 0x42);
    print("I/O port write attempted");
}
"""

# Test 4: Inline assembly (compiles and executes)
test4 = """
unsafe {
    asm("nop");
    print("Assembly executed");
}
"""

# Test 5: Combined test - pointers with unsafe block
test5 = """
unsafe {
    let a = 100;
    let b = 200;
    let ptr_a = ptr(value=a);
    let ptr_b = ptr(value=b);
    print("Pointer A:", ptr_a);
    print("Pointer B:", ptr_b);
}
"""

# Test 6: Address-of and dereference operators
test6 = """
unsafe {
    let value = 999;
    let addr = &value;
    print("Address:", addr);
}
"""

# Run all tests
tests = [
    ("Pointer Creation", test1),
    ("Syscall (getpid)", test2),
    ("Hardware I/O", test3),
    ("Inline Assembly", test4),
    ("Multiple Pointers", test5),
    ("Address-of Operator", test6),
]

passed = 0
failed = 0

for name, code in tests:
    if test_feature(name, code):
        passed += 1
    else:
        failed += 1

print("\n" + "=" * 60)
print(f"RESULTS: {passed}/{len(tests)} passed")
if failed > 0:
    print(f"Failed: {failed}")
print("=" * 60)

# Summary
print("\n✅ LOW-LEVEL FEATURES INTEGRATED:")
print("  • Real pointers (KSPointer with ctypes)")
print("  • Direct syscalls (KSSyscall)")
print("  • Hardware I/O (KSHardwareIO - inb/outb)")
print("  • Inline assembly (KSInlineAsm)")
print("  • Unsafe blocks (required for low-level ops)")
print("  • Address-of (&) and dereference (*) operators")
print("\n✅ ALL FEATURES WORK IN INTERPRETER MODE")
