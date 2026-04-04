#!/usr/bin/env python3
"""
Simple tree-walk interpreter for KentScript - FIXED VERSION
Executes parsed AST directly without compilation
"""

import sys
from typing import Any, Dict, List, Optional

class InterpreterError(Exception):
    """Runtime error in interpreter"""
    pass


class IOPortAccessor:
    """Simulates Port I/O access: io[port]"""
    def __init__(self, ports: Dict[int, int]):
        self.ports = ports
    
    def __getitem__(self, port: int) -> int:
        """Read from I/O port"""
        return self.ports.get(port, 0)
    
    def __setitem__(self, port: int, value: int):
        """Write to I/O port"""
        self.ports[port] = value & 0xFF  # 8-bit value


class MSRAccessor:
    """Simulates MSR access: msr[reg]"""
    def __init__(self, regs: Dict[int, int]):
        self.regs = regs
    
    def __getitem__(self, reg: int) -> int:
        """Read MSR"""
        return self.regs.get(reg, 0)
    
    def __setitem__(self, reg: int, value: int):
        """Write MSR"""
        self.regs[reg] = value & 0xFFFFFFFFFFFFFFFF  # 64-bit value


class BoundMethod:
    """Represents a method bound to an object"""
    def __init__(self, obj: Any, method_name: str, interpreter):
        self.obj = obj
        self.method_name = method_name
        self.interpreter = interpreter
    
    def __call__(self, *args):
        """Call the method on the object"""
        # List methods
        if isinstance(self.obj, list):
            if self.method_name == 'append' or self.method_name == 'push':
                self.obj.append(args[0] if args else None)
                return None
            elif self.method_name == 'pop':
                return self.obj.pop() if self.obj else None
            elif self.method_name == 'insert':
                if len(args) >= 2:
                    self.obj.insert(args[0], args[1])
                return None
            elif self.method_name == 'remove':
                if args:
                    self.obj.remove(args[0])
                return None
            elif self.method_name == 'clear':
                self.obj.clear()
                return None
            elif self.method_name == 'extend':
                if args:
                    self.obj.extend(args[0])
                return None
            elif self.method_name == 'reverse':
                self.obj.reverse()
                return None
            elif self.method_name == 'sort':
                self.obj.sort()
                return None
        
        # Dict methods
        elif isinstance(self.obj, dict):
            if self.method_name == 'get':
                return self.obj.get(args[0], args[1] if len(args) > 1 else None)
            elif self.method_name == 'keys':
                return list(self.obj.keys())
            elif self.method_name == 'values':
                return list(self.obj.values())
            elif self.method_name == 'items':
                return list(self.obj.items())
            elif self.method_name == 'clear':
                self.obj.clear()
                return None
            elif self.method_name == 'pop':
                return self.obj.pop(args[0]) if args else None
        
        # String methods
        elif isinstance(self.obj, str):
            if self.method_name == 'upper':
                return self.obj.upper()
            elif self.method_name == 'lower':
                return self.obj.lower()
            elif self.method_name == 'split':
                return self.obj.split(args[0] if args else None)
            elif self.method_name == 'join':
                return self.obj.join(args[0] if args else [])
            elif self.method_name == 'replace':
                if len(args) >= 2:
                    return self.obj.replace(args[0], args[1])
                return self.obj
            elif self.method_name == 'strip':
                return self.obj.strip()
        
        raise InterpreterError(f"Unknown method '{self.method_name}' on {type(self.obj).__name__}")


class SimpleInterpreter:
    """Tree-walk interpreter for KentScript AST"""
    
    def __init__(self):
        self.globals = {}
        self.locals_stack = [{}]
        self.functions = {}
        self.return_value = None
        self.should_return = False
        self.should_break = False
        self.should_continue = False
        # Hardware access simulation
        self.io_ports = {}  # Port I/O simulation
        self.msr_regs = {}  # MSR simulation
    
    def current_scope(self) -> Dict:
        """Get current variable scope"""
        return self.locals_stack[-1]
    
    def push_scope(self):
        """Enter new scope"""
        self.locals_stack.append({})
    
    def pop_scope(self):
        """Exit scope"""
        if len(self.locals_stack) > 1:
            self.locals_stack.pop()
    
    def get_variable(self, name: str) -> Any:
        """Get variable value, searching up scope chain"""
        # Check for special hardware access
        if name == 'io':
            return IOPortAccessor(self.io_ports)
        if name == 'msr':
            return MSRAccessor(self.msr_regs)
        
        for scope in reversed(self.locals_stack):
            if name in scope:
                return scope[name]
        if name in self.globals:
            return self.globals[name]
        raise InterpreterError(f"Undefined variable: {name}")
    
    def set_variable(self, name: str, value: Any):
        """Set variable in current scope"""
        self.current_scope()[name] = value
    
    def execute(self, ast: List) -> Any:
        """Execute program"""
        result = None
        try:
            for node in ast:
                result = self.execute_stmt(node)
                if self.should_return:
                    break
        except Exception as e:
            print(f"Runtime error: {e}", file=sys.stderr)
            raise
        return result
    
    def execute_stmt(self, stmt) -> Any:
        """Execute a statement"""
        if stmt is None:
            return None
        
        stmt_type = type(stmt).__name__
        
        # Variable declaration
        if stmt_type == 'LetDecl':
            value = self.evaluate(stmt.value) if stmt.value else None
            self.set_variable(stmt.name, value)
            return value
        
        # Assignment
        elif stmt_type == 'Assignment':
            value = self.evaluate(stmt.value)
            target_type = type(stmt.target).__name__
            
            if target_type == 'Identifier':
                self.set_variable(stmt.target.name, value)
            elif target_type == 'IndexAccess':
                # Handle arr[index] = value, io[port] = value, msr[reg] = value
                obj = self.evaluate(stmt.target.obj)
                index = self.evaluate(stmt.target.index)
                obj[index] = value
            elif target_type == 'MemberAccess':
                # Handle obj.field = value
                obj = self.evaluate(stmt.target.obj)
                setattr(obj, stmt.target.member, value)
            
            return value
        
        # If statement
        elif stmt_type == 'IfStmt':
            condition = self.evaluate(stmt.condition)
            if self._is_truthy(condition):
                for s in stmt.then_block:
                    self.execute_stmt(s)
                    if self.should_return or self.should_break:
                        break
            elif stmt.else_block:
                for s in stmt.else_block:
                    self.execute_stmt(s)
                    if self.should_return or self.should_break:
                        break
            return None
        
        # While loop
        elif stmt_type == 'WhileStmt':
            while self._is_truthy(self.evaluate(stmt.condition)):
                for s in stmt.body:
                    self.execute_stmt(s)
                    if self.should_return or self.should_break:
                        break
                if self.should_return or self.should_break:
                    break
                self.should_continue = False
            self.should_break = False
            return None
        
        # For loop
        elif stmt_type == 'ForStmt':
            iterable = self.evaluate(stmt.iterable)
            if isinstance(iterable, range):
                items = iterable
            elif isinstance(iterable, list):
                items = iterable
            else:
                raise InterpreterError(f"Cannot iterate over {type(iterable)}")
            
            for item in items:
                self.set_variable(stmt.var, item)
                for s in stmt.body:
                    self.execute_stmt(s)
                    if self.should_return or self.should_break:
                        break
                if self.should_return or self.should_break:
                    break
                self.should_continue = False
            self.should_break = False
            return None
        
        # Function definition
        elif stmt_type == 'FunctionDef':
            self.functions[stmt.name] = stmt
            return None
        
        # Return statement
        elif stmt_type == 'ReturnStmt':
            self.return_value = self.evaluate(stmt.value) if stmt.value else None
            self.should_return = True
            return self.return_value
        
        # Break statement
        elif stmt_type == 'BreakStmt':
            self.should_break = True
            return None
        
        # Continue statement
        elif stmt_type == 'ContinueStmt':
            self.should_continue = True
            return None
        
        # Function call or other expression used as statement
        else:
            return self.evaluate(stmt)
    
    def evaluate(self, expr) -> Any:
        """Evaluate an expression"""
        if expr is None:
            return None
        
        expr_type = type(expr).__name__
        
        # Literal
        if expr_type == 'Literal':
            return expr.value
        
        # List literal
        elif expr_type == 'ListLiteral':
            return [self.evaluate(elem) for elem in expr.elements]
        
        # Identifier
        elif expr_type == 'Identifier':
            return self.get_variable(expr.name)
        
        # Member access (for method calls)
        elif expr_type == 'MemberAccess':
            obj = self.evaluate(expr.obj)
            member = expr.member
            # Return a bound method wrapper
            return BoundMethod(obj, member, self)
        
        # Index access (array[index])
        elif expr_type == 'IndexAccess':
            obj = self.evaluate(expr.obj)
            index = self.evaluate(expr.index)
            return obj[index]
        
        # Binary operation
        elif expr_type == 'BinaryOp':
            left = self.evaluate(expr.left)
            right = self.evaluate(expr.right)
            
            op = expr.op
            if op == '+': return left + right
            elif op == '-': return left - right
            elif op == '*': return left * right
            elif op == '/':
                if right == 0:
                    raise RuntimeError("Division by zero")
                return left // right if isinstance(left, int) and isinstance(right, int) else left / right
            elif op == '%':
                if right == 0:
                    raise RuntimeError("Modulo by zero")
                return left % right
            elif op == '==': return left == right
            elif op == '!=': return left != right
            elif op == '<': return left < right
            elif op == '>': return left > right
            elif op == '<=': return left <= right
            elif op == '>=': return left >= right
            elif op == '&&' or op == 'and': return left and right
            elif op == '||' or op == 'or': return left or right
            elif op == '&': return left & right
            elif op == '|': return left | right
            elif op == '^': return left ^ right
            elif op == '<<': return left << right
            elif op == '>>': return left >> right
            elif op == '..': return range(left, right)
            elif op == '..=': return range(left, right + 1)
            else:
                raise InterpreterError(f"Unknown operator: {op}")
        
        # Unary operation
        elif expr_type == 'UnaryOp':
            operand = self.evaluate(expr.operand)
            op = expr.op
            if op == '-': return -operand
            elif op == '!': return not operand
            elif op == '~': return ~operand
            else:
                raise InterpreterError(f"Unknown unary operator: {op}")
        
        # Function call
        elif expr_type == 'FunctionCall':
            # Check if func is a MemberAccess (method call)
            func_type = type(expr.func).__name__
            
            if func_type == 'MemberAccess':
                # Method call - evaluate to get BoundMethod
                func = self.evaluate(expr.func)
                if isinstance(func, BoundMethod):
                    args = [self.evaluate(arg) for arg in expr.args]
                    return func(*args)
            
            # Regular function call - get function name
            if hasattr(expr.func, 'name'):
                func_name = expr.func.name
            elif isinstance(expr.func, str):
                func_name = expr.func
            else:
                func_name = str(expr.func)
            
            return self.call_function(func_name, expr.args)
        
        else:
            raise InterpreterError(f"Unknown expression type: {expr_type}")
    
    def call_function(self, name: str, args: List) -> Any:
        """Call a function"""
        # Built-in functions
        if name == 'print':
            values = [self.evaluate(arg) for arg in args]
            if values:
                print(*values)
            else:
                print()
            return None
        
        elif name == 'len':
            obj = self.evaluate(args[0])
            return len(obj)
        
        elif name == 'range':
            if len(args) == 1:
                return range(self.evaluate(args[0]))
            elif len(args) == 2:
                return range(self.evaluate(args[0]), self.evaluate(args[1]))
            elif len(args) == 3:
                return range(self.evaluate(args[0]), self.evaluate(args[1]), self.evaluate(args[2]))
            else:
                raise InterpreterError(f"range() takes 1-3 arguments, got {len(args)}")
        
        elif name == 'str':
            return str(self.evaluate(args[0]))
        
        elif name == 'int':
            return int(self.evaluate(args[0]))
        
        # User-defined functions
        elif name in self.functions:
            func_def = self.functions[name]
            
            # Evaluate arguments
            arg_values = [self.evaluate(arg) for arg in args]
            
            # Create new scope with parameters
            self.push_scope()
            try:
                for param, arg_val in zip(func_def.params, arg_values):
                    self.set_variable(param, arg_val)
                
                # Execute function body
                for stmt in func_def.body:
                    self.execute_stmt(stmt)
                    if self.should_return:
                        break
                
                # Return value if function returns
                result = self.return_value if self.should_return else None
                self.should_return = False
                self.return_value = None
                
                return result
            finally:
                self.pop_scope()
        
        else:
            raise InterpreterError(f"Undefined function: {name}")
    
    def _is_truthy(self, value: Any) -> bool:
        """Python truthiness"""
        if value is None or value is False:
            return False
        if value == 0 or value == "" or value == [] or value == {}:
            return False
        return True
