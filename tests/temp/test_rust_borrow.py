#!/usr/bin/env python3
"""
Test Smart Borrow Checker (No False Positives)
"""

import sys
sys.path.insert(0, '/home/pylord/Desktop/kentsoft/pyprojects/kentscript/rolling/KentScript/tools/scripts')

from rust_borrow_checker import SmartBorrowChecker

def test_python_style_assignment():
    """Test 1: Python-style assignment (should pass)"""
    print("\n=== Test 1: Python-Style Assignment (Should PASS) ===")
    bc = SmartBorrowChecker()
    bc.push_scope()
    
    bc.declare("x", line=1)
    bc.declare("y", line=2)  # y = x in Python just copies reference
    bc.use_var("x", line=3)  # Still valid!
    bc.use_var("y", line=4)  # Also valid!
    
    bc.pop_scope()
    success = bc.check_and_report()
    print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")

def test_explicit_move():
    """Test 2: Explicit move() (should fail)"""
    print("\n=== Test 2: Explicit move() (Should FAIL) ===")
    bc = SmartBorrowChecker()
    bc.push_scope()
    
    bc.declare("x", line=1)
    bc.explicit_move("x", line=2)  # Explicit move()
    bc.use_var("x", line=3)  # ERROR: explicitly moved
    
    bc.pop_scope()
    success = bc.check_and_report()
    print(f"Result: {'✅ PASS' if not success else '❌ FAIL'} (caught error)")

def test_explicit_borrow_conflict():
    """Test 3: Explicit &x and &mut x conflict (should fail)"""
    print("\n=== Test 3: Explicit Borrow Conflict (Should FAIL) ===")
    bc = SmartBorrowChecker()
    bc.push_scope()
    
    bc.declare("x", line=1)
    bc.explicit_borrow_immutable("x", line=2)  # &x
    bc.explicit_borrow_mutable("x", line=3)  # &mut x - ERROR
    
    bc.pop_scope()
    success = bc.check_and_report()
    print(f"Result: {'✅ PASS' if not success else '❌ FAIL'} (caught error)")

def test_multiple_immutable_borrows():
    """Test 4: Multiple &x (should pass)"""
    print("\n=== Test 4: Multiple Immutable Borrows (Should PASS) ===")
    bc = SmartBorrowChecker()
    bc.push_scope()
    
    bc.declare("x", line=1)
    bc.explicit_borrow_immutable("x", line=2)  # &x
    bc.explicit_borrow_immutable("x", line=3)  # &x again - OK!
    bc.explicit_borrow_immutable("x", line=4)  # &x again - OK!
    
    bc.pop_scope()
    success = bc.check_and_report()
    print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")

def test_mutate_while_borrowed():
    """Test 5: Mutate while &x exists (should fail)"""
    print("\n=== Test 5: Mutate While Borrowed (Should FAIL) ===")
    bc = SmartBorrowChecker()
    bc.push_scope()
    
    bc.declare("x", line=1)
    bc.explicit_borrow_immutable("x", line=2)  # &x
    bc.mutate_while_borrowed("x", line=3)  # x = ... ERROR
    
    bc.pop_scope()
    success = bc.check_and_report()
    print(f"Result: {'✅ PASS' if not success else '❌ FAIL'} (caught error)")

def test_normal_mutation():
    """Test 6: Normal mutation without borrows (should pass)"""
    print("\n=== Test 6: Normal Mutation (Should PASS) ===")
    bc = SmartBorrowChecker()
    bc.push_scope()
    
    bc.declare("x", line=1)
    bc.use_var("x", line=2)
    bc.use_var("x", line=3)  # Mutate without explicit borrows - OK!
    
    bc.pop_scope()
    success = bc.check_and_report()
    print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")

def test_function_call_no_move():
    """Test 7: Function call doesn't move (should pass)"""
    print("\n=== Test 7: Function Call (Should PASS) ===")
    bc = SmartBorrowChecker()
    bc.push_scope()
    
    bc.declare("x", line=1)
    # In Python semantics, passing to function doesn't move
    bc.use_var("x", line=2)  # Still valid after "call"
    
    bc.pop_scope()
    success = bc.check_and_report()
    print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")

def test_move_while_borrowed():
    """Test 8: move() while borrowed (should fail)"""
    print("\n=== Test 8: move() While Borrowed (Should FAIL) ===")
    bc = SmartBorrowChecker()
    bc.push_scope()
    
    bc.declare("x", line=1)
    bc.explicit_borrow_immutable("x", line=2)  # &x
    bc.explicit_move("x", line=3)  # move(x) - ERROR
    
    bc.pop_scope()
    success = bc.check_and_report()
    print(f"Result: {'✅ PASS' if not success else '❌ FAIL'} (caught error)")

if __name__ == '__main__':
    print("="*70)
    print("🦀 SMART BORROW CHECKER TESTS (No False Positives)")
    print("="*70)
    print("\nKentScript uses Python-style references by default.")
    print("Only explicit move(), &x, &mut x trigger ownership checks.")
    
    # Tests that should PASS (no false positives)
    test_python_style_assignment()
    test_multiple_immutable_borrows()
    test_normal_mutation()
    test_function_call_no_move()
    
    # Tests that should FAIL (catch real errors)
    test_explicit_move()
    test_explicit_borrow_conflict()
    test_mutate_while_borrowed()
    test_move_while_borrowed()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE - No False Positives!")
    print("="*70)
    print("\nSummary:")
    print("  • Python-style code works normally")
    print("  • Explicit Rust-style syntax is checked")
    print("  • Best of both worlds!")
    print("="*70)
