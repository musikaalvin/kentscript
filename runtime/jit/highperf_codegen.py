#!/usr/bin/env python3
"""
HighPerfCCodegen: Professional C code generator with optimizations
- __restrict__ pointer qualifications (alias analysis)
- __builtin_assume_aligned(ptr, 16) for SIMD
- Direct ks_malloc binding to SlabAllocator
- Cross-platform (Linux, macOS, Windows)
- REAL memory barriers (no stubs)
- Architecture-specific SIMD intrinsics
"""

import platform
from typing import List, Dict, Optional, Tuple, Callable, Union
from enum import Enum


class CodegenError(Exception):
    """Raised on code generation errors"""
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg
        super().__init__(f"[CodegenError {code}] {msg}")


class Arch(Enum):
    """Supported architectures"""
    X86_64 = "x86_64"
    ARM64 = "arm64"
    AARCH64 = "aarch64"
    RISCV64 = "riscv64"
    UNKNOWN = "unknown"
    
    @staticmethod
    def detect() -> 'Arch':
        """Detect current architecture"""
        machine = platform.machine().lower()
        if machine in ('x86_64', 'amd64'):
            return Arch.X86_64
        elif machine in ('aarch64', 'arm64'):
            return Arch.ARM64
        elif machine.startswith('riscv'):
            return Arch.RISCV64
        return Arch.UNKNOWN


class OS(Enum):
    """Supported operating systems"""
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"
    ANDROID = "android"
    BSD = "bsd"
    UNKNOWN = "unknown"
    
    @staticmethod
    def detect() -> 'OS':
        """Detect current operating system"""
        sys_platform = platform.system().lower()
        if sys_platform == 'windows':
            return OS.WINDOWS
        elif sys_platform == 'darwin':
            return OS.MACOS
        elif sys_platform.startswith('linux'):
            # Check if Android
            import os
            if os.path.exists('/system/bin/sh'):
                return OS.ANDROID
            return OS.LINUX
        elif sys_platform.startswith(('freebsd', 'openbsd', 'netbsd')):
            return OS.BSD
        return OS.UNKNOWN


class HighPerfCCodegen:
    """
    Generate optimized C code with performance directives.
    Cross-platform with architecture-specific optimizations.
    """
    
    def __init__(self, target_arch: Optional[str] = None, target_os: Optional[str] = None):
        self.buffer: List[str] = []
        self.indent_level = 0
        self.target_arch = target_arch or Arch.detect().value
        self.target_os = target_os or OS.detect().value
        self.string_literals: Dict[str, str] = {}
        self.string_counter = 0
    
    def emit_line(self, code: str = ""):
        """Emit code line with indentation"""
        if code:
            self.buffer.append("  " * self.indent_level + code)
        else:
            self.buffer.append("")
    
    def _new_string_literal(self, s: str) -> str:
        """Create new string literal and return its name"""
        name = f"_ks_str_{self.string_counter}"
        self.string_counter += 1
        self.string_literals[name] = s
        return name
    
    def _escape_string(self, s: str) -> str:
        """Escape string for C"""
        return (s.replace('\\', '\\\\')
                 .replace('"', '\\"')
                 .replace('\n', '\\n')
                 .replace('\r', '\\r')
                 .replace('\t', '\\t'))
    
    def emit_header(self):
        """Emit C header with optimization directives and SIMD support"""
        # Standard headers
        self.emit_line("#include <stdint.h>")
        self.emit_line("#include <stddef.h>")
        self.emit_line("#include <stdlib.h>")
        self.emit_line("#include <string.h>")
        self.emit_line("#include <stdbool.h>")
        
        # Platform-specific headers
        if self.target_os == 'windows':
            self.emit_line("#include <windows.h>")
        else:
            self.emit_line("#include <unistd.h>")
            self.emit_line("#include <sys/mman.h>")
        
        # SIMD headers based on architecture
        if self.target_arch in ('x86_64', 'amd64'):
            self.emit_line("#include <immintrin.h>  // AVX-512, AVX2, SSE")
        elif self.target_arch in ('arm64', 'aarch64'):
            self.emit_line("#include <arm_neon.h>   // ARM NEON SIMD intrinsics")
        elif self.target_arch == 'riscv64':
            self.emit_line("#include <riscv_vector.h>  // RISC-V Vector extension")
        
        self.emit_line()
        
        # Compiler pragmas
        if self.target_os in ('linux', 'macos', 'android', 'bsd'):
            self.emit_line('#ifdef __GNUC__')
            self.emit_line('#pragma GCC optimize("O3")')
            if self.target_arch in ('x86_64', 'amd64'):
                self.emit_line('#pragma GCC target("avx512f,avx512cd,avx2,bmi2,lzcnt,popcnt")')
            elif self.target_arch in ('arm64', 'aarch64'):
                self.emit_line('#pragma GCC target("arch=armv8.2-a+fp16+simd")')
            self.emit_line('#endif')
        
        self.emit_line()
        
        # Performance macros
        self.emit_line("/* Performance optimization macros */")
        self.emit_line("#ifndef RESTRICT")
        self.emit_line("#define RESTRICT __restrict")
        self.emit_line("#endif")
        self.emit_line("")
        self.emit_line("#ifndef ALIGNED")
        self.emit_line("#define ALIGNED(n) __attribute__((aligned(n)))")
        self.emit_line("#endif")
        self.emit_line("")
        self.emit_line("#ifndef LIKELY")
        self.emit_line("#define LIKELY(x) __builtin_expect(!!(x), 1)")
        self.emit_line("#endif")
        self.emit_line("")
        self.emit_line("#ifndef UNLIKELY")
        self.emit_line("#define UNLIKELY(x) __builtin_expect(!!(x), 0)")
        self.emit_line("#endif")
        self.emit_line()
        
        # Type definitions
        self.emit_line("/* Type definitions */")
        self.emit_line("typedef int8_t   i8;")
        self.emit_line("typedef int16_t  i16;")
        self.emit_line("typedef int32_t  i32;")
        self.emit_line("typedef int64_t  i64;")
        self.emit_line("typedef uint8_t  u8;")
        self.emit_line("typedef uint16_t u16;")
        self.emit_line("typedef uint32_t u32;")
        self.emit_line("typedef uint64_t u64;")
        self.emit_line("typedef float    f32;")
        self.emit_line("typedef double   f64;")
        self.emit_line()
    
    def emit_slab_allocator_api(self):
        """Emit SlabAllocator C API"""
        self.emit_line("/* SlabAllocator API */")
        self.emit_line("extern void* ks_malloc(size_t size);")
        self.emit_line("extern void  ks_free(void* ptr);")
        self.emit_line("extern void* ks_calloc(size_t nmemb, size_t size);")
        self.emit_line("extern void* ks_realloc(void* ptr, size_t new_sz);")
        self.emit_line()
    
    def emit_syscall_api(self):
        """Emit syscall wrappers for ring-0 access"""
        self.emit_line("/* Direct syscall API (ring-0) */")
        
        if self.target_arch in ('x86_64', 'amd64'):
            self.emit_line("static inline long ks_syscall6(long n, long a1, long a2, long a3,")
            self.emit_line("                                long a4, long a5, long a6) {")
            self.emit_line("    long ret;")
            self.emit_line("    __asm__ volatile (")
            self.emit_line("        \"syscall\"")
            self.emit_line("        : \"=a\"(ret)")
            self.emit_line("        : \"a\"(n), \"D\"(a1), \"S\"(a2), \"d\"(a3),")
            self.emit_line("          \"r\"(a4), \"r\"(a5), \"r\"(a6)")
            self.emit_line("        : \"memory\", \"rcx\", \"r11\");")
            self.emit_line("    return ret;")
            self.emit_line("}")
        elif self.target_arch in ('arm64', 'aarch64'):
            self.emit_line("static inline long ks_syscall6(long n, long a1, long a2, long a3,")
            self.emit_line("                                long a4, long a5, long a6) {")
            self.emit_line("    register long x8 __asm__(\"x8\") = n;")
            self.emit_line("    register long x0 __asm__(\"x0\") = a1;")
            self.emit_line("    register long x1 __asm__(\"x1\") = a2;")
            self.emit_line("    register long x2 __asm__(\"x2\") = a3;")
            self.emit_line("    register long x3 __asm__(\"x3\") = a4;")
            self.emit_line("    register long x4 __asm__(\"x4\") = a5;")
            self.emit_line("    register long x5 __asm__(\"x5\") = a6;")
            self.emit_line("    __asm__ volatile (")
            self.emit_line("        \"svc #0\"")
            self.emit_line("        : \"=r\"(x0)")
            self.emit_line("        : \"r\"(x8), \"r\"(x0), \"r\"(x1), \"r\"(x2),")
            self.emit_line("          \"r\"(x3), \"r\"(x4), \"r\"(x5)")
            self.emit_line("        : \"memory\", \"cc\");")
            self.emit_line("    return x0;")
            self.emit_line("}")
        else:
            self.emit_line("static inline long ks_syscall6(long n, long a1, long a2, long a3,")
            self.emit_line("                                long a4, long a5, long a6) {")
            self.emit_line("    /* Fallback - syscall not directly supported */")
            self.emit_line("    (void)n; (void)a1; (void)a2; (void)a3; (void)a4; (void)a5; (void)a6;")
            self.emit_line("    return -1;")
            self.emit_line("}")
        
        self.emit_line("")
        self.emit_line("#define ks_syscall0(n) ks_syscall6(n,0,0,0,0,0,0)")
        self.emit_line("#define ks_syscall1(n,a1) ks_syscall6(n,a1,0,0,0,0,0)")
        self.emit_line("#define ks_syscall2(n,a1,a2) ks_syscall6(n,a1,a2,0,0,0,0)")
        self.emit_line("#define ks_syscall3(n,a1,a2,a3) ks_syscall6(n,a1,a2,a3,0,0,0)")
        self.emit_line("#define ks_syscall4(n,a1,a2,a3,a4) ks_syscall6(n,a1,a2,a3,a4,0,0)")
        self.emit_line("#define ks_syscall5(n,a1,a2,a3,a4,a5) ks_syscall6(n,a1,a2,a3,a4,a5,0)")
        self.emit_line()
    
    def emit_mmio_api(self):
        """Emit MMIO C API with proper barriers"""
        self.emit_line("/* MMIO API with barriers */")
        
        # Read functions
        self.emit_line("static inline u8 ks_mmio_read8(volatile void* addr) {")
        self.emit_line("    u8 val;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    val = *(volatile u8*)addr;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    return val;")
        self.emit_line("}")
        self.emit_line("")
        
        self.emit_line("static inline u16 ks_mmio_read16(volatile void* addr) {")
        self.emit_line("    u16 val;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    val = *(volatile u16*)addr;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    return val;")
        self.emit_line("}")
        self.emit_line("")
        
        self.emit_line("static inline u32 ks_mmio_read32(volatile void* addr) {")
        self.emit_line("    u32 val;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    val = *(volatile u32*)addr;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    return val;")
        self.emit_line("}")
        self.emit_line("")
        
        self.emit_line("static inline u64 ks_mmio_read64(volatile void* addr) {")
        self.emit_line("    u64 val;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    val = *(volatile u64*)addr;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    return val;")
        self.emit_line("}")
        self.emit_line("")
        
        # Write functions
        self.emit_line("static inline void ks_mmio_write8(volatile void* addr, u8 val) {")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    *(volatile u8*)addr = val;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("}")
        self.emit_line("")
        
        self.emit_line("static inline void ks_mmio_write16(volatile void* addr, u16 val) {")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    *(volatile u16*)addr = val;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("}")
        self.emit_line("")
        
        self.emit_line("static inline void ks_mmio_write32(volatile void* addr, u32 val) {")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    *(volatile u32*)addr = val;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("}")
        self.emit_line("")
        
        self.emit_line("static inline void ks_mmio_write64(volatile void* addr, u64 val) {")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("    *(volatile u64*)addr = val;")
        self.emit_line("    ks_memory_barrier();")
        self.emit_line("}")
        self.emit_line("")
    
    def emit_barrier(self):
        """Emit platform-appropriate memory barrier (REAL)"""
        self.emit_line("/* Memory barrier */")
        self.emit_line("static inline void ks_memory_barrier(void) {")
        
        if self.target_arch in ('arm64', 'aarch64'):
            self.emit_line("#ifdef __aarch64__")
            self.emit_line("    __asm__ volatile(\"dmb sy\" ::: \"memory\");")
            self.emit_line("#endif")
        elif self.target_arch in ('x86_64', 'amd64'):
            self.emit_line("#ifdef __x86_64__")
            self.emit_line("    __asm__ volatile(\"mfence\" ::: \"memory\");")
            self.emit_line("#endif")
        else:
            self.emit_line("    /* Generic barrier */")
            self.emit_line("    __sync_synchronize();")
        
        self.emit_line("}")
        self.emit_line("")
    
    def emit_function_with_restrict(self, func_name: str, return_type: str,
                                   params: List[Tuple[str, str]]) -> int:
        """
        Emit function signature with __restrict__ pointers.
        Returns: indent level
        """
        restrict_params = []
        for ptype, pname in params:
            if '*' in ptype:
                # Add __restrict__ to pointers
                ptype = ptype.replace('*', '* RESTRICT')
            restrict_params.append((ptype, pname))
        
        param_str = ", ".join(f"{ptype} {pname}" for ptype, pname in restrict_params)
        self.emit_line(f"{return_type} {func_name}({param_str}) {{")
        self.indent_level += 1
        return self.indent_level
    
    def emit_assume_aligned(self, var_name: str, alignment: int = 16):
        """Emit alignment hint for SIMD"""
        self.emit_line(f"{var_name} = (void*)__builtin_assume_aligned({var_name}, {alignment});")
    
    def emit_restrict_copy(self, src: str, dst: str, size: str):
        """Emit optimized memcpy with restrict hints"""
        self.emit_line(f"memcpy({dst}, {src}, {size});")
    
    def emit_malloc(self, var_name: str, size_expr: str):
        """Emit ks_malloc call"""
        self.emit_line(f"void* {var_name} = ks_malloc({size_expr});")
        self.emit_line(f"if (UNLIKELY(!{var_name})) {{ return; }}")
    
    def emit_free(self, var_name: str):
        """Emit ks_free call"""
        self.emit_line(f"ks_free({var_name});")
        self.emit_line(f"{var_name} = NULL;")
    
    def emit_mmio_read(self, var_name: str, addr_expr: str, size: int = 4):
        """Emit MMIO read"""
        if size == 1:
            self.emit_line(f"u8 {var_name} = ks_mmio_read8((volatile void*)({addr_expr}));")
        elif size == 2:
            self.emit_line(f"u16 {var_name} = ks_mmio_read16((volatile void*)({addr_expr}));")
        elif size == 4:
            self.emit_line(f"u32 {var_name} = ks_mmio_read32((volatile void*)({addr_expr}));")
        elif size == 8:
            self.emit_line(f"u64 {var_name} = ks_mmio_read64((volatile void*)({addr_expr}));")
    
    def emit_mmio_write(self, addr_expr: str, value_expr: str, size: int = 4):
        """Emit MMIO write"""
        if size == 1:
            self.emit_line(f"ks_mmio_write8((volatile void*)({addr_expr}), (u8)({value_expr}));")
        elif size == 2:
            self.emit_line(f"ks_mmio_write16((volatile void*)({addr_expr}), (u16)({value_expr}));")
        elif size == 4:
            self.emit_line(f"ks_mmio_write32((volatile void*)({addr_expr}), (u32)({value_expr}));")
        elif size == 8:
            self.emit_line(f"ks_mmio_write64((volatile void*)({addr_expr}), (u64)({value_expr}));")
    
    def emit_vectorizable_loop(self, var_name: str, start: str, end: str, 
                               step: str = "1", body_fn: Callable = None):
        """Emit loop with vectorization hint"""
        self.emit_line("#ifdef _OPENMP")
        self.emit_line("#pragma omp simd")
        self.emit_line("#endif")
        
        if step == "1":
            self.emit_line(f"for (i32 {var_name} = {start}; {var_name} < {end}; {var_name}++) {{")
        else:
            self.emit_line(f"for (i32 {var_name} = {start}; {var_name} < {end}; {var_name} += {step}) {{")
        
        self.indent_level += 1
        
        if body_fn:
            body_fn(var_name)
        else:
            self.emit_line(f"    /* loop body */")
        
        self.indent_level -= 1
        self.emit_line("}")
    
    def emit_simd_intrinsic(self, intrinsic: str, args: List[str]) -> str:
        """Emit SIMD intrinsic call"""
        if self.target_arch in ('x86_64', 'amd64'):
            return f"{intrinsic}({', '.join(args)});"
        elif self.target_arch in ('arm64', 'aarch64'):
            return f"{intrinsic}({', '.join(args)});"
        return f"/* SIMD not available */"
    
    def emit_inline_asm(self, asm_template: str, outputs: str = "", 
                       inputs: str = "", clobbers: str = "memory"):
        """Emit inline assembly with constraints"""
        if outputs or inputs:
            self.emit_line(f'__asm__ __volatile__("{asm_template}"'
                          f' : {outputs} : {inputs} : "{clobbers}");')
        else:
            self.emit_line(f'__asm__ __volatile__("{asm_template}" : : : "{clobbers}");')
    
    def emit_string_literal(self, s: str) -> str:
        """Emit a string literal and return its name"""
        name = self._new_string_literal(s)
        return name
    
    def get_code(self) -> str:
        """Get generated C code"""
        # Add string literals at the top
        if self.string_literals:
            literals = []
            for name, value in self.string_literals.items():
                escaped = self._escape_string(value)
                literals.append(f'static const char {name}[] = "{escaped}";')
            return '\n'.join(literals) + '\n\n' + '\n'.join(self.buffer)
        return '\n'.join(self.buffer)
    
    def clear(self):
        """Clear buffer"""
        self.buffer = []
        self.indent_level = 0
        self.string_literals.clear()
        self.string_counter = 0


class RealCCompiler:
    """
    High-performance C compiler backend.
    Compiles KentScript AST to optimized C code.
    Cross-platform with architecture-specific optimizations.
    """
    
    def __init__(self, target_arch: Optional[str] = None, target_os: Optional[str] = None):
        self.codegen = HighPerfCCodegen(target_arch, target_os)
        self.target_arch = target_arch or Arch.detect().value
        self.target_os = target_os or OS.detect().value
    
    def compile_ast(self, ast_nodes: List[Dict]) -> str:
        """
        Compile AST to C code.
        Returns: C source code
        Raises: CodegenError on failure
        """
        try:
            # Emit headers and APIs
            self.codegen.emit_header()
            self.codegen.emit_barrier()
            self.codegen.emit_slab_allocator_api()
            self.codegen.emit_syscall_api()
            self.codegen.emit_mmio_api()
            self.codegen.emit_line()
            
            # Compile each node
            for node in ast_nodes:
                self._compile_node(node)
            
            # Main entry if not provided
            if not self._has_main(ast_nodes):
                self.codegen.emit_line("int main(int argc, char** argv) {")
                self.codegen.indent_level += 1
                self.codegen.emit_line("(void)argc; (void)argv;")
                self.codegen.emit_line("return 0;")
                self.codegen.indent_level -= 1
                self.codegen.emit_line("}")
            
            return self.codegen.get_code()
        
        except Exception as e:
            raise CodegenError(-1, f"Compilation failed: {e}")
    
    def _has_main(self, ast_nodes: List[Dict]) -> bool:
        """Check if AST already has a main function"""
        for node in ast_nodes:
            if node.get('type') == 'function' and node.get('name') == 'main':
                return True
        return False
    
    def _compile_node(self, node: Dict):
        """Compile single AST node"""
        node_type = node.get('type')
        
        if node_type == 'function':
            self._compile_function(node)
        elif node_type == 'struct':
            self._compile_struct(node)
        elif node_type == 'assignment':
            self._compile_assignment(node)
        elif node_type == 'if':
            self._compile_if(node)
        elif node_type == 'while':
            self._compile_while(node)
        elif node_type == 'for':
            self._compile_for(node)
        elif node_type == 'return':
            self._compile_return(node)
    
    def _compile_function(self, node: Dict):
        """Compile function"""
        func_name = node.get('name', 'unknown')
        return_type = node.get('return_type', 'void')
        params = node.get('params', [])
        body = node.get('body', [])
        
        # Convert params to list of (type, name)
        param_list = []
        for i, p in enumerate(params):
            ptype = p.get('type', 'void*') if isinstance(p, dict) else 'void*'
            pname = p.get('name', f'arg{i}') if isinstance(p, dict) else f'arg{i}'
            param_list.append((ptype, pname))
        
        self.codegen.emit_line()
        self.codegen.emit_function_with_restrict(func_name, return_type, param_list)
        
        for stmt in body:
            self._compile_statement(stmt)
        
        # Add default return if needed
        last_stmt = body[-1] if body else None
        if not last_stmt or last_stmt.get('type') != 'return':
            if return_type == 'void':
                self.codegen.emit_line("return;")
            elif return_type in ('int', 'i32', 'i64'):
                self.codegen.emit_line("return 0;")
        
        self.codegen.indent_level -= 1
        self.codegen.emit_line("}")
    
    def _compile_statement(self, stmt: Dict):
        """Compile statement"""
        stmt_type = stmt.get('type')
        
        if stmt_type == 'malloc':
            var_name = stmt.get('var', 'buf')
            size = stmt.get('size', '1024')
            self.codegen.emit_malloc(var_name, str(size))
        
        elif stmt_type == 'free':
            var_name = stmt.get('var', 'buf')
            self.codegen.emit_free(var_name)
        
        elif stmt_type == 'mmio_read':
            var_name = stmt.get('var', 'val')
            addr = stmt.get('addr', '0')
            size = stmt.get('size', 4)
            self.codegen.emit_mmio_read(var_name, str(addr), size)
        
        elif stmt_type == 'mmio_write':
            addr = stmt.get('addr', '0')
            value = stmt.get('value', '0')
            size = stmt.get('size', 4)
            self.codegen.emit_mmio_write(str(addr), str(value), size)
        
        elif stmt_type == 'barrier':
            self.codegen.emit_line("ks_memory_barrier();")
        
        elif stmt_type == 'syscall':
            self._compile_syscall(stmt)
        
        elif stmt_type == 'print':
            self._compile_print(stmt)
        
        elif stmt_type == 'asm':
            asm_code = stmt.get('code', 'nop')
            outputs = stmt.get('outputs', '')
            inputs = stmt.get('inputs', '')
            self.codegen.emit_inline_asm(asm_code, outputs, inputs)
    
    def _compile_syscall(self, stmt: Dict):
        """Compile syscall statement"""
        num = stmt.get('number', '0')
        args = stmt.get('args', [])
        result_var = stmt.get('result', 'ret')
        
        if len(args) == 0:
            self.codegen.emit_line(f"long {result_var} = ks_syscall0({num});")
        elif len(args) == 1:
            self.codegen.emit_line(f"long {result_var} = ks_syscall1({num}, {args[0]});")
        elif len(args) == 2:
            self.codegen.emit_line(f"long {result_var} = ks_syscall2({num}, {args[0]}, {args[1]});")
        elif len(args) == 3:
            self.codegen.emit_line(f"long {result_var} = ks_syscall3({num}, {args[0]}, {args[1]}, {args[2]});")
        else:
            args_str = ', '.join(str(a) for a in args[:6])
            self.codegen.emit_line(f"long {result_var} = ks_syscall6({num}, {args_str});")
    
    def _compile_print(self, stmt: Dict):
        """Compile print statement"""
        args = stmt.get('args', [])
        if not args:
            self.codegen.emit_line('printf("\\n");')
            return
        
        formats = []
        values = []
        for arg in args:
            if arg.startswith('"'):
                formats.append('%s')
                values.append(arg)
            else:
                formats.append('%lld')
                values.append(f'(long long)({arg})')
        
        format_str = ' '.join(formats) + '\\n'
        format_var = self.codegen.emit_string_literal(format_str)
        self.codegen.emit_line(f'printf({format_var}, {", ".join(values)});')
    
    def _compile_struct(self, node: Dict):
        """Compile struct"""
        name = node.get('name', 'struct_t')
        fields = node.get('fields', [])
        
        self.codegen.emit_line(f"typedef struct {{")
        self.codegen.indent_level += 1
        
        for field in fields:
            ftype = field.get('type', 'void*')
            fname = field.get('name', 'field')
            self.codegen.emit_line(f"{ftype} {fname};")
        
        self.codegen.indent_level -= 1
        self.codegen.emit_line(f"}} {name};")
        self.codegen.emit_line()
    
    def _compile_assignment(self, node: Dict):
        """Compile assignment"""
        target = node.get('target', 'x')
        value = node.get('value', '0')
        self.codegen.emit_line(f"{target} = {value};")
    
    def _compile_if(self, node: Dict):
        """Compile if statement"""
        cond = node.get('condition', '0')
        then_block = node.get('then', [])
        else_block = node.get('else', [])
        
        self.codegen.emit_line(f"if ({cond}) {{")
        self.codegen.indent_level += 1
        for stmt in then_block:
            self._compile_statement(stmt)
        self.codegen.indent_level -= 1
        
        if else_block:
            self.codegen.emit_line("} else {")
            self.codegen.indent_level += 1
            for stmt in else_block:
                self._compile_statement(stmt)
            self.codegen.indent_level -= 1
        
        self.codegen.emit_line("}")
    
    def _compile_while(self, node: Dict):
        """Compile while loop"""
        cond = node.get('condition', '1')
        body = node.get('body', [])
        
        self.codegen.emit_line(f"while ({cond}) {{")
        self.codegen.indent_level += 1
        for stmt in body:
            self._compile_statement(stmt)
        self.codegen.indent_level -= 1
        self.codegen.emit_line("}")
    
    def _compile_for(self, node: Dict):
        """Compile for loop"""
        init = node.get('init', 'int i = 0')
        cond = node.get('condition', 'i < 10')
        inc = node.get('increment', 'i++')
        body = node.get('body', [])
        
        self.codegen.emit_line(f"for ({init}; {cond}; {inc}) {{")
        self.codegen.indent_level += 1
        for stmt in body:
            self._compile_statement(stmt)
        self.codegen.indent_level -= 1
        self.codegen.emit_line("}")
    
    def _compile_return(self, node: Dict):
        """Compile return statement"""
        value = node.get('value')
        if value is not None:
            self.codegen.emit_line(f"return {value};")
        else:
            self.codegen.emit_line("return;")


# Module exports
__all__ = [
    'HighPerfCCodegen',
    'RealCCompiler',
    'CodegenError',
    'Arch',
    'OS',
]


if __name__ == "__main__":
    print("[CODGEN] High-Performance C Code Generator")
    print("=" * 60)
    print(f"Target: {Arch.detect().value} on {OS.detect().value}")
    
    # Test codegen
    codegen = HighPerfCCodegen()
    codegen.emit_header()
    codegen.emit_barrier()
    codegen.emit_slab_allocator_api()
    codegen.emit_mmio_api()
    
    print("\nGenerated header:")
    print("-" * 40)
    print(codegen.get_code()[:500] + "...")
    print("=" * 60)
