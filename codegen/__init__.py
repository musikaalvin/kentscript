"""
KentScript Code Generation Package

This package contains code generators for different backends:
- c_transpiler.py: C code generation
- llvm_backend.py: LLVM IR generation (future)
"""

from codegen.c_transpiler import CTranspiler

__all__ = ['CTranspiler']
