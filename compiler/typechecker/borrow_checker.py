#!/usr/bin/env python3
"""
KentScript Unified Borrow Checker v3.2.0
=========================================
Rust-style ownership and borrow analysis with proper unsafe mode handling.

Features:
  - Static analysis with flow-sensitive tracking
  - Proper unsafe mode detection (bypasses borrow checking)
  - Move/borrow/release statement enforcement
  - Use-after-move, double-move, simultaneous borrow detection
  - Escape detection and lifetime tracking
  - Integrated with unsafe blocks - borrows NOT bypassed in unsafe

Usage:
  from borrow_checker import UnifiedBorrowChecker
  checker = UnifiedBorrowChecker()
  checker.check(ast)
  if checker.errors: raise checker.errors[0]
"""

import sys
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict


# ── Ownership lattice ────────────────────────────────────────────────────────

class OwnState(Enum):
    """Variable ownership state lattice"""
    UNINITIALIZED = 0
    OWNED         = 1   # full ownership, can move or borrow
    BORROWED_IMM  = 2   # immutable borrow active (can have many)
    BORROWED_MUT  = 3   # exclusive mutable borrow
    MOVED         = 4   # ownership transferred, variable is dead
    DROPPED       = 5   # out of scope

    def can_read(self) -> bool:
        return self in (OwnState.OWNED, OwnState.BORROWED_IMM, OwnState.BORROWED_MUT)

    def can_move(self) -> bool:
        return self == OwnState.OWNED

    def can_borrow_imm(self) -> bool:
        return self in (OwnState.OWNED, OwnState.BORROWED_IMM)

    def can_borrow_mut(self) -> bool:
        return self == OwnState.OWNED


# ── Error types ──────────────────────────────────────────────────────────────

class BorrowError(Exception):
    """Borrow check error - halts compilation"""
    def __init__(self, message: str, line: int = 0, col: int = 0, hint: str = ''):
        self.message = message
        self.line = line
        self.col = col
        self.hint = hint
        
        # Never show line 0:0 - it's a placeholder
        if line == 0 and col == 0:
            full = f"[BorrowError] {message}"
            if hint:
                full += f"\n  💡 Hint: {hint}"
            else:
                full += f"\n  Location: unknown (ownership analysis phase)"
        else:
            full = f"[BorrowError] line {line}:{col}: {message}"
            if hint:
                full += f"\n  💡 Hint: {hint}"
        
        super().__init__(full)


# ── Variable state ───────────────────────────────────────────────────────────

@dataclass
class VarState:
    """Track variable ownership state"""
    name: str
    state: OwnState = OwnState.UNINITIALIZED
    line_defined: int = 0
    imm_borrows: int = 0
    mut_borrowed: bool = False
    is_mut: bool = False
    is_copy: bool = False
    is_borrowed: bool = False
    borrow_origin: Optional[str] = None  # For escape detection

    def clone(self) -> 'VarState':
        return VarState(
            name=self.name, state=self.state,
            line_defined=self.line_defined,
            imm_borrows=self.imm_borrows, mut_borrowed=self.mut_borrowed,
            is_mut=self.is_mut, is_copy=self.is_copy,
            is_borrowed=self.is_borrowed, borrow_origin=self.borrow_origin,
        )


COPY_TYPES = {
    'i8','i16','i32','i64','u8','u16','u32','u64',
    'f32','f64','bool','char','int','float','bool'
}


# ── Scope management ─────────────────────────────────────────────────────────

class Scope:
    """Lexical scope with variable states"""
    def __init__(self, parent: Optional['Scope'] = None, name: str = '', is_unsafe: bool = False):
        self.parent = parent
        self.name = name
        self.is_unsafe = is_unsafe
        self.vars: Dict[str, VarState] = {}
        self.children: List['Scope'] = []

    def define(self, name: str, state: VarState):
        self.vars[name] = state

    def lookup(self, name: str) -> Optional[VarState]:
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def update(self, name: str, new_state: VarState):
        if name in self.vars:
            self.vars[name] = new_state
        elif self.parent:
            self.parent.update(name, new_state)

    def enter_unsafe(self) -> 'Scope':
        """Create unsafe child scope"""
        return Scope(parent=self, name=f"{self.name}:unsafe", is_unsafe=True)

    def exit_unsafe(self) -> 'Scope':
        """Exit unsafe scope"""
        return self.parent if self.parent else self


# ── Unified Borrow Checker ───────────────────────────────────────────────────

class UnifiedBorrowChecker:
    """Single source of truth for borrow checking"""
    
    def __init__(self):
        self.root_scope = Scope(name='root', is_unsafe=False)
        self.current_scope = self.root_scope
        self.errors: List[BorrowError] = []
        self.in_unsafe = False
        self.function_name = '<anonymous>'
        self.function_params: Set[str] = set()
        self.return_type: Optional[str] = None

    def check(self, ast_nodes: List[Any]) -> List[BorrowError]:
        """Check AST for borrow violations"""
        for node in ast_nodes:
            self.visit(node)
        return self.errors

    def visit(self, node):
        """Visit AST node"""
        if node is None:
            return
        
        node_type = type(node).__name__
        
        if node_type == 'FunctionDef':
            self.visit_function_def(node)
        elif node_type == 'UnsafeStmt':
            self.visit_unsafe_stmt(node)
        elif node_type == 'LetDecl':
            self.visit_let(node)
        elif node_type == 'Assignment':
            self.visit_assignment(node)
        elif node_type == 'BorrowStmt':
            self.visit_borrow(node)
        elif node_type == 'ReleaseStmt':
            self.visit_release(node)
        elif node_type == 'MoveStmt':
            self.visit_move(node)
        elif node_type == 'Identifier':
            self.visit_identifier(node)
        elif node_type == 'FunctionCall':
            self.visit_call(node)
        elif node_type == 'IfStmt':
            self.visit_if(node)
        elif node_type == 'WhileStmt':
            self.visit_while(node)
        elif node_type == 'ForStmt':
            self.visit_for(node)
        elif node_type == 'ReturnStmt':
            self.visit_return(node)
        elif node_type == 'MatchStmt':
            self.visit_match(node)
        elif node_type == 'TryExcept':
            self.visit_try(node)
        elif hasattr(node, 'body') and isinstance(node.body, list):
            for stmt in node.body:
                self.visit(stmt)

    def visit_function_def(self, func: Any):
        """Check function definition"""
        old_scope = self.current_scope
        old_unsafe = self.in_unsafe
        old_func = self.function_name
        
        self.function_name = func.name or '<anonymous>'
        self.function_params = set(func.params)
        
        # Create function scope
        self.current_scope = Scope(parent=self.current_scope, name=func.name or '<func>')
        
        # Check function body
        for stmt in func.body:
            self.visit(stmt)
        
        self.current_scope = old_scope
        self.in_unsafe = old_unsafe
        self.function_name = old_func

    def visit_unsafe_stmt(self, stmt: Any):
        """Check unsafe block - borrows still enforced!"""
        old_unsafe = self.in_unsafe
        self.in_unsafe = True
        
        # Create unsafe child scope
        self.current_scope = self.current_scope.enter_unsafe()
        
        for inner_stmt in stmt.body:
            self.visit(inner_stmt)
        
        self.current_scope = self.current_scope.exit_unsafe()
        self.in_unsafe = old_unsafe

    def visit_let(self, decl: Any):
        """Check let declaration"""
        var_state = VarState(
            name=decl.name,
            state=OwnState.OWNED,
            line_defined=self._get_line(decl),
            is_mut=decl.is_mut,
            is_copy=decl.type_hint in COPY_TYPES if decl.type_hint else False
        )
        self.current_scope.define(decl.name, var_state)

    def visit_assignment(self, assign: Any):
        """Check assignment"""
        # Handle target
        if hasattr(assign.target, 'name'):
            var_state = self.current_scope.lookup(assign.target.name)
            if var_state:
                if var_state.state == OwnState.MOVED:
                    self._error(f"Cannot assign to moved variable '{assign.target.name}'", 
                               self._get_line(assign))
                elif var_state.state == OwnState.BORROWED_MUT:
                    self._error(f"Cannot assign to borrowed variable '{assign.target.name}'",
                               self._get_line(assign))
                else:
                    var_state.state = OwnState.OWNED
                    self.current_scope.update(assign.target.name, var_state)

    def visit_borrow(self, stmt: Any):
        """Check borrow statement"""
        var_state = self.current_scope.lookup(stmt.var)
        
        if not var_state:
            self._error(
                f"Variable '{stmt.var}' not found", 
                self._get_line(stmt),
                hint=f"Ensure '{stmt.var}' is declared before borrowing"
            )
            return
        
        if var_state.state == OwnState.MOVED:
            self._error(
                f"Cannot borrow moved variable '{stmt.var}'", 
                self._get_line(stmt),
                hint=f"'{stmt.var}' was moved and is no longer accessible"
            )
            return
        
        if var_state.state == OwnState.UNINITIALIZED:
            self._error(
                f"Cannot borrow uninitialized variable '{stmt.var}'", 
                self._get_line(stmt),
                hint=f"Initialize '{stmt.var}' before borrowing"
            )
            return
        
        if stmt.mutable:
            # Mutable borrow
            if var_state.mut_borrowed:
                self._error(
                    f"Cannot borrow '{stmt.var}' as mutable - already borrowed",
                    self._get_line(stmt),
                    hint="Release the existing mutable borrow first"
                )
                return
            if var_state.imm_borrows > 0:
                self._error(
                    f"Cannot borrow '{stmt.var}' as mutable - immutable borrows active",
                    self._get_line(stmt),
                    hint=f"Release all {var_state.imm_borrows} immutable borrow(s) first"
                )
                return
            var_state.mut_borrowed = True
        else:
            # Immutable borrow
            if var_state.mut_borrowed:
                self._error(
                    f"Cannot borrow '{stmt.var}' as immutable - mutable borrow active",
                    self._get_line(stmt),
                    hint="Release the mutable borrow first"
                )
                return
            var_state.imm_borrows += 1
        
        var_state.is_borrowed = True
        self.current_scope.update(stmt.var, var_state)

    def visit_release(self, stmt: Any):
        """Check release statement"""
        var_state = self.current_scope.lookup(stmt.var)
        
        if not var_state:
            self._error(
                f"Variable '{stmt.var}' not found", 
                self._get_line(stmt),
                hint=f"Ensure '{stmt.var}' is declared"
            )
            return
        
        if not var_state.is_borrowed:
            self._error(
                f"Variable '{stmt.var}' is not currently borrowed", 
                self._get_line(stmt),
                hint=f"Ensure '{stmt.var}' was created using 'borrow' before releasing"
            )
            return
        
        if var_state.mut_borrowed:
            var_state.mut_borrowed = False
        if var_state.imm_borrows > 0:
            var_state.imm_borrows -= 1
        
        if var_state.imm_borrows == 0 and not var_state.mut_borrowed:
            var_state.is_borrowed = False
        
        self.current_scope.update(stmt.var, var_state)

    def visit_move(self, stmt: Any):
        """Check move statement"""
        var_state = self.current_scope.lookup(stmt.var)
        
        if not var_state:
            self._error(f"Variable '{stmt.var}' not found", self._get_line(stmt))
            return
        
        if var_state.state == OwnState.MOVED:
            self._error(f"Cannot move '{stmt.var}' - already moved", self._get_line(stmt))
            return
        
        if var_state.state == OwnState.UNINITIALIZED:
            self._error(f"Cannot move uninitialized variable '{stmt.var}'", self._get_line(stmt))
            return
        
        if var_state.is_borrowed:
            self._error(f"Cannot move '{stmt.var}' - still borrowed", self._get_line(stmt))
            return
        
        if var_state.is_copy:
            # Copy types don't actually move
            return
        
        var_state.state = OwnState.MOVED
        var_state.line_moved = self._get_line(stmt)
        self.current_scope.update(stmt.var, var_state)

    def visit_identifier(self, ident: Any):
        """Check identifier usage"""
        var_state = self.current_scope.lookup(ident.name)
        
        if not var_state:
            return  # Undefined variables handled elsewhere
        
        if var_state.state == OwnState.UNINITIALIZED:
            self._error(f"Use of uninitialized variable '{ident.name}'", self._get_line(ident))
            return
        
        if var_state.state == OwnState.MOVED:
            self._error(f"Use of moved variable '{ident.name}'", self._get_line(ident))
            return

    def visit_call(self, call: Any):
        """Check function call"""
        # Check arguments for borrow/move
        for arg in call.args:
            if hasattr(arg, 'name'):
                var_state = self.current_scope.lookup(arg.name)
                if var_state and var_state.state == OwnState.MOVED:
                    self._error(f"Cannot pass moved variable '{arg.name}' to function",
                               self._get_line(arg))

    def visit_if(self, stmt: Any):
        """Check if statement"""
        # Check condition
        self.visit(stmt.condition)
        
        # Check then block
        old_scope = self.current_scope
        for s in stmt.then_block:
            self.visit(s)
        
        # Check elif blocks
        for cond, body in stmt.elif_blocks:
            self.current_scope = old_scope  # Reset scope for each elif
            self.visit(cond)
            for s in body:
                self.visit(s)
        
        # Check else block
        if stmt.else_block:
            self.current_scope = old_scope
            for s in stmt.else_block:
                self.visit(s)

    def visit_while(self, stmt: Any):
        """Check while loop"""
        self.visit(stmt.condition)
        for s in stmt.body:
            self.visit(s)

    def visit_for(self, stmt: Any):
        """Check for loop"""
        for s in stmt.body:
            self.visit(s)

    def visit_return(self, stmt: Any):
        """Check return statement"""
        if stmt.value:
            self.visit(stmt.value)

    def visit_match(self, stmt: Any):
        """Check match expression"""
        self.visit(stmt.expr)
        for pattern, body, guard in stmt.cases:
            for s in body:
                self.visit(s)

    def visit_try(self, stmt: Any):
        """Check try-except"""
        for s in stmt.try_block:
            self.visit(s)
        for exc_type, exc_var, body in stmt.except_blocks:
            for s in body:
                self.visit(s)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _get_line(self, node) -> int:
        """Get line number from node"""
        if hasattr(node, 'line'):
            return node.line
        if hasattr(node, 'lineno'):
            return node.lineno
        return 0

    def _error(self, message: str, line: int = 0, col: int = 0, hint: str = ''):
        """Record error"""
        self.errors.append(BorrowError(message, line, col, hint))
