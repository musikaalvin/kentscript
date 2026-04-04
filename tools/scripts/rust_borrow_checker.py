#!/usr/bin/env python3
"""
KentScript Smart Borrow Checker
Adapted for Python-style reference semantics with optional Rust-style checking
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum

class BorrowType(Enum):
    IMMUTABLE = "immutable"
    MUTABLE = "mutable"

@dataclass
class Lifetime:
    name: str
    scope_depth: int
    children: List['Lifetime'] = field(default_factory=list)

@dataclass
class Borrow:
    borrow_type: BorrowType
    scope_depth: int
    line: int

@dataclass
class Variable:
    name: str
    owner_lifetime: Lifetime
    is_moved: bool = False
    moved_at: Optional[int] = None
    borrows: List[Borrow] = field(default_factory=list)
    is_mutable: bool = True
    is_explicit_move: bool = False  # Only track explicit move() calls

class SmartBorrowChecker:
    """
    Smart borrow checker for KentScript
    
    Adapted for Python-style semantics:
    - Assignment is COPY/REFERENCE by default (like Python)
    - Only explicit move() transfers ownership
    - Explicit &x and &mut x syntax for borrows
    - Catches real errors, not false positives
    
    Rules enforced:
    1. Explicit move() invalidates source
    2. Cannot use after explicit move()
    3. Explicit &mut x conflicts with other borrows
    4. Multiple &x allowed (immutable borrows)
    5. Cannot mutate while explicitly borrowed immutably
    """
    
    def __init__(self, strict_mode=False):
        self.strict_mode = strict_mode  # False = Python semantics, True = Rust semantics
        self.scope_depth = 0
        self.lifetime_counter = 0
        self.scope_stack: List[Lifetime] = []
        self.variables: Dict[str, Variable] = {}
        self.errors: List[str] = []
        
    def push_scope(self) -> Lifetime:
        """Enter a new scope"""
        self.scope_depth += 1
        lt = Lifetime(f"'s{self.lifetime_counter}", self.scope_depth)
        self.lifetime_counter += 1
        if self.scope_stack:
            self.scope_stack[-1].children.append(lt)
        self.scope_stack.append(lt)
        return lt
    
    def pop_scope(self):
        """Exit scope and drop variables"""
        if not self.scope_stack:
            return
        lt = self.scope_stack.pop()
        self.scope_depth -= 1
        
        # Drop all variables owned by this scope
        to_drop = [name for name, var in self.variables.items()
                   if var.owner_lifetime.name == lt.name]
        for name in to_drop:
            del self.variables[name]
    
    def current_lifetime(self) -> Lifetime:
        """Get current lifetime"""
        if self.scope_stack:
            return self.scope_stack[-1]
        return Lifetime("'global", 0)
    
    def declare(self, name: str, is_mutable: bool = True, line: int = 0):
        """Declare a new variable (let x = ...)"""
        # Allow shadowing in Python mode
        self.variables[name] = Variable(
            name=name,
            owner_lifetime=self.current_lifetime(),
            is_mutable=is_mutable
        )
    
    def explicit_move(self, name: str, line: int = 0):
        """Explicit move() call - transfers ownership"""
        if name not in self.variables:
            self.error(f"Cannot move undeclared variable '{name}'", line)
            return
        
        var = self.variables[name]
        
        # Check if already moved
        if var.is_moved and var.is_explicit_move:
            self.error(
                f"Use-after-move: '{name}' was explicitly moved at line {var.moved_at}",
                line
            )
            return
        
        # Check if borrowed
        if var.borrows:
            self.error(
                f"Cannot move '{name}' while it has {len(var.borrows)} active borrow(s)",
                line
            )
            return
        
        # Mark as explicitly moved
        var.is_moved = True
        var.is_explicit_move = True
        var.moved_at = line
    
    def use_var(self, name: str, line: int = 0):
        """Use/read a variable"""
        if name not in self.variables:
            return
        
        var = self.variables[name]
        
        # Only error on explicit moves
        if var.is_moved and var.is_explicit_move:
            self.error(
                f"Use-after-move: '{name}' was explicitly moved at line {var.moved_at}. "
                f"Use move() only when you want Rust-style ownership transfer.",
                line
            )
    
    def explicit_borrow_immutable(self, name: str, line: int = 0):
        """Explicit &x syntax"""
        if name not in self.variables:
            self.error(f"Cannot borrow undeclared variable '{name}'", line)
            return
        
        var = self.variables[name]
        
        if var.is_moved and var.is_explicit_move:
            self.error(
                f"Borrow-after-move: '{name}' was explicitly moved at line {var.moved_at}",
                line
            )
            return
        
        # Check for mutable borrows
        mutable_borrows = [b for b in var.borrows if b.borrow_type == BorrowType.MUTABLE]
        if mutable_borrows:
            self.error(
                f"Cannot create immutable borrow &{name}: "
                f"already has active mutable borrow &mut {name}",
                line
            )
            return
        
        var.borrows.append(Borrow(BorrowType.IMMUTABLE, self.scope_depth, line))
    
    def explicit_borrow_mutable(self, name: str, line: int = 0):
        """Explicit &mut x syntax"""
        if name not in self.variables:
            self.error(f"Cannot mutably borrow undeclared variable '{name}'", line)
            return
        
        var = self.variables[name]
        
        if var.is_moved and var.is_explicit_move:
            self.error(
                f"Borrow-after-move: '{name}' was explicitly moved at line {var.moved_at}",
                line
            )
            return
        
        # Check for any existing borrows
        if var.borrows:
            borrow_type = var.borrows[0].borrow_type.value
            self.error(
                f"Cannot create mutable borrow &mut {name}: "
                f"already has {len(var.borrows)} active {borrow_type} borrow(s)",
                line
            )
            return
        
        var.borrows.append(Borrow(BorrowType.MUTABLE, self.scope_depth, line))
    
    def release_borrow(self, name: str):
        """Release most recent borrow"""
        if name in self.variables and self.variables[name].borrows:
            self.variables[name].borrows.pop()
    
    def mutate_while_borrowed(self, name: str, line: int = 0):
        """Check mutation while explicitly borrowed"""
        if name not in self.variables:
            return
        
        var = self.variables[name]
        
        # Only check if explicitly borrowed
        immutable_borrows = [b for b in var.borrows 
                            if b.borrow_type == BorrowType.IMMUTABLE]
        if immutable_borrows:
            self.error(
                f"Cannot mutate '{name}': has {len(immutable_borrows)} "
                f"active immutable borrow(s) (&{name})",
                line
            )
    
    def error(self, msg: str, line: int):
        """Record an error"""
        self.errors.append(f"Line {line}: {msg}")
    
    def check_and_report(self) -> bool:
        """Check if there are errors and report them"""
        if not self.errors:
            return True
        
        print("\n" + "="*70)
        print(f"🦀 BORROW CHECKER — {len(self.errors)} issue(s) found")
        print("="*70)
        for i, error in enumerate(self.errors, 1):
            print(f"  {i}. {error}")
        print("="*70)
        print("Tip: KentScript uses Python-style references by default.")
        print("     Use explicit move(), &x, &mut x for Rust-style ownership.")
        print("="*70 + "\n")
        return False

# Global instance
_borrow_checker = SmartBorrowChecker(strict_mode=False)

def get_borrow_checker() -> SmartBorrowChecker:
    """Get global borrow checker instance"""
    return _borrow_checker

def reset_borrow_checker():
    """Reset borrow checker for new file"""
    global _borrow_checker
    _borrow_checker = SmartBorrowChecker(strict_mode=False)
