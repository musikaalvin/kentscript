#!/usr/bin/env python3
"""
KentScript Interpreter Fallback
================================
Pure Python interpreter for architectures without JIT support.
Provides cross-platform compatibility for all CPUs.

Supports all architectures: x86, ARM, MIPS, PowerPC, SPARC, etc.
"""

import operator
from typing import Any, Dict, List, Callable
from dataclasses import dataclass

@dataclass
class InterpreterFunction:
    """Represents a function in the interpreter"""
    name: str
    bytecode: List[tuple]
    num_args: int
    
class BytecodeInterpreter:
    """
    Bytecode interpreter for unsupported architectures.
    Provides same functionality as JIT but via interpretation.
    """
    
    # Bytecode operations
    OP_CONST = 0
    OP_ADD = 1
    OP_SUB = 2
    OP_MUL = 3
    OP_DIV = 4
    OP_MOD = 5
    OP_LOAD_ARG = 6
    OP_RETURN = 7
    OP_CALL = 8
    OP_MEMCPY = 9
    
    def __init__(self):
        self.functions: Dict[str, InterpreterFunction] = {}
        self.available = True  # Always available
    
    def emit_const_return(self, name: str, value: int) -> Callable:
        """Emit a function that returns a constant"""
        bytecode = [
            (self.OP_CONST, value),
            (self.OP_RETURN,),
        ]
        
        func = InterpreterFunction(name, bytecode, 0)
        self.functions[name] = func
        
        def wrapper():
            return self._execute(func, [])
        
        return wrapper
    
    def emit_add(self, name: str) -> Callable:
        """Emit a function that adds two arguments"""
        bytecode = [
            (self.OP_LOAD_ARG, 0),
            (self.OP_LOAD_ARG, 1),
            (self.OP_ADD,),
            (self.OP_RETURN,),
        ]
        
        func = InterpreterFunction(name, bytecode, 2)
        self.functions[name] = func
        
        def wrapper(a, b):
            return self._execute(func, [a, b])
        
        return wrapper
    
    def emit_memcpy_kernel(self, name: str) -> Callable:
        """Emit a memcpy function"""
        def wrapper(dst, src, count):
            import ctypes
            # Use ctypes.memmove for cross-platform memcpy
            ctypes.memmove(dst, src, count)
        
        return wrapper
    
    def _execute(self, func: InterpreterFunction, args: List[Any]) -> Any:
        """Execute bytecode"""
        stack = []
        
        for instruction in func.bytecode:
            op = instruction[0]
            
            if op == self.OP_CONST:
                stack.append(instruction[1])
            
            elif op == self.OP_LOAD_ARG:
                arg_idx = instruction[1]
                stack.append(args[arg_idx])
            
            elif op == self.OP_ADD:
                b = stack.pop()
                a = stack.pop()
                stack.append(a + b)
            
            elif op == self.OP_SUB:
                b = stack.pop()
                a = stack.pop()
                stack.append(a - b)
            
            elif op == self.OP_MUL:
                b = stack.pop()
                a = stack.pop()
                stack.append(a * b)
            
            elif op == self.OP_DIV:
                b = stack.pop()
                a = stack.pop()
                stack.append(a // b if isinstance(a, int) else a / b)
            
            elif op == self.OP_MOD:
                b = stack.pop()
                a = stack.pop()
                stack.append(a % b)
            
            elif op == self.OP_RETURN:
                return stack.pop() if stack else None
        
        return None
    
    def get(self, name: str) -> Callable:
        """Get a previously emitted function"""
        func = self.functions.get(name)
        if not func:
            return None
        
        def wrapper(*args):
            return self._execute(func, list(args))
        
        return wrapper


# Singleton instance
_interpreter = None

def get_interpreter():
    """Get or create the global interpreter instance"""
    global _interpreter
    if _interpreter is None:
        _interpreter = BytecodeInterpreter()
    return _interpreter
