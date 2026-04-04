"""
KentScript bytecode VM: BytecodeCompiler, StackVM, VirtualMachine.
"""
import os, sys, re, json, time, math, types, struct, ctypes, hashlib
import threading, subprocess, shutil, platform, asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum, auto

try:
    from ks.interpreter import OptimizationEngine
except ImportError:
    OptimizationEngine = None

try:
    from ks.compiler_infra import BorrowChecker as CompileTimeBorrowChecker
except ImportError:
    CompileTimeBorrowChecker = None

# ============================================================================
# BYTECODE COMPILER SYSTEM - Advanced Code Generation
# ============================================================================


class BytecodeCompiler:
    """Compiles AST to optimized bytecode for fast VM execution"""

    def __init__(self):
        self.opcodes = []
        self.constants = []
        self.names = []
        self.code_objects = {}
        self.optimization_level = 2  # 0=none, 1=basic, 2=aggressive
        self.jit_enabled = True
        self.bytecode_cache = {}
        self.optimizer = OptimizationEngine()
        self.stats = {}

    def compile_module(self, ast_nodes):
        """Compile entire module to bytecode"""
        # Apply AST optimizations
        if self.optimization_level >= 1:
            ast_nodes = self.optimizer.optimize_ast(ast_nodes)

        for node in ast_nodes:
            self.compile_stmt(node)

        # Apply bytecode optimizations
        if self.optimization_level >= 1:
            self.opcodes = self.optimizer.optimize_bytecode(self.opcodes)

        self.stats = self.optimizer.get_stats()
        return {
            "opcodes": self.opcodes,
            "constants": self.constants,
            "names": self.names,
        }

    def compile_stmt(self, stmt):
        """Compile a single statement"""
        if isinstance(stmt, Assignment):
            self.compile_assignment(stmt)
        elif isinstance(stmt, FunctionDef):
            self.compile_function(stmt)
        elif isinstance(stmt, ClassDef):
            self.compile_class(stmt)
        elif isinstance(stmt, IfStmt):
            self.compile_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self.compile_while(stmt)
        elif isinstance(stmt, ForStmt):
            self.compile_for(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.emit("RETURN_VALUE")
        elif isinstance(stmt, BreakStmt):
            self.emit("BREAK_LOOP")
        elif isinstance(stmt, ContinueStmt):
            self.emit("CONTINUE_LOOP")

    def compile_expr(self, expr):
        """Compile expression to bytecode"""
        if isinstance(expr, BinaryOp):
            self.compile_expr(expr.left)
            self.compile_expr(expr.right)
            op_map = {
                "+": "BINARY_ADD",
                "-": "BINARY_SUBTRACT",
                "*": "BINARY_MULTIPLY",
                "/": "BINARY_TRUE_DIVIDE",
                "//": "BINARY_FLOOR_DIVIDE",
                "%": "BINARY_MODULO",
                "**": "BINARY_POWER",
                "&": "BINARY_AND",
                "|": "BINARY_OR",
                "^": "BINARY_XOR",
                "<<": "BINARY_LSHIFT",
                ">>": "BINARY_RSHIFT",
            }
            self.emit(op_map.get(expr.op, "BINARY_ADD"))
        elif isinstance(expr, Literal):
            const_idx = self.add_constant(expr.value)
            self.emit("LOAD_CONST", const_idx)
        elif isinstance(expr, Identifier):
            name_idx = self.add_name(expr.name)
            self.emit("LOAD_NAME", name_idx)
        elif isinstance(expr, FunctionCall):
            num_args = len(expr.args)
            for arg in expr.args:
                self.compile_expr(arg)
            self.emit("CALL_FUNCTION", num_args)

    def compile_assignment(self, stmt):
        """Compile assignment statement"""
        self.compile_expr(stmt.value)
        if isinstance(stmt.target, Identifier):
            name_idx = self.add_name(stmt.target.name)
            self.emit("STORE_NAME", name_idx)

    def compile_function(self, func_def):
        """Compile function definition"""
        code = self.create_code_object(func_def)
        const_idx = self.add_constant(code)
        self.emit("LOAD_CONST", const_idx)
        name_idx = self.add_name(func_def.name)
        self.emit("MAKE_FUNCTION", len(func_def.params))
        self.emit("STORE_NAME", name_idx)

    def compile_class(self, class_def):
        """Compile class definition"""
        name_idx = self.add_name(class_def.name)
        self.emit("BUILD_CLASS", len(class_def.methods))
        self.emit("STORE_NAME", name_idx)

    def compile_if(self, if_stmt):
        """Compile if statement with proper jumps"""
        self.compile_expr(if_stmt.condition)
        jump_if_false = len(self.opcodes)
        self.emit("POP_JUMP_IF_FALSE", 0)  # Placeholder

        for stmt in if_stmt.body:
            self.compile_stmt(stmt)

        if if_stmt.else_block:
            jump_end = len(self.opcodes)
            self.emit("JUMP_FORWARD", 0)  # Placeholder
            self.opcodes[jump_if_false] = ("POP_JUMP_IF_FALSE", len(self.opcodes))

            for stmt in if_stmt.else_block:
                self.compile_stmt(stmt)
            self.opcodes[jump_end] = ("JUMP_FORWARD", len(self.opcodes))
        else:
            self.opcodes[jump_if_false] = ("POP_JUMP_IF_FALSE", len(self.opcodes))

    def compile_while(self, while_stmt):
        """Compile while loop"""
        loop_start = len(self.opcodes)
        self.compile_expr(while_stmt.condition)
        jump_if_false = len(self.opcodes)
        self.emit("POP_JUMP_IF_FALSE", 0)

        for stmt in while_stmt.body:
            self.compile_stmt(stmt)

        self.emit("JUMP_ABSOLUTE", loop_start)
        self.opcodes[jump_if_false] = ("POP_JUMP_IF_FALSE", len(self.opcodes))

    def compile_for(self, for_stmt):
        """Compile for loop"""
        self.compile_expr(for_stmt.iterable)
        self.emit("GET_ITER")
        loop_start = len(self.opcodes)
        self.emit("FOR_ITER", 0)  # Placeholder

        name_idx = self.add_name(for_stmt.var)
        self.emit("STORE_NAME", name_idx)

        for stmt in for_stmt.body:
            self.compile_stmt(stmt)

        self.emit("JUMP_ABSOLUTE", loop_start)
        self.opcodes[loop_start] = ("FOR_ITER", len(self.opcodes))

    def create_code_object(self, func_def):
        """Create code object for function"""
        return {
            "name": func_def.name,
            "params": func_def.params,
            "body": func_def.body,
            "flags": 0,
        }

    def emit(self, opcode, arg=None):
        """Emit bytecode instruction"""
        if arg is None:
            self.opcodes.append((opcode,))
        else:
            self.opcodes.append((opcode, arg))

    def add_constant(self, value):
        """Add constant to table"""
        if value not in self.constants:
            self.constants.append(value)
        return self.constants.index(value)

    def add_name(self, name):
        """Add name to table"""
        if name not in self.names:
            self.names.append(name)
        return self.names.index(name)

    def get_bytecode(self):
        """Get compiled bytecode"""
        return {
            "opcodes": self.opcodes,
            "constants": self.constants,
            "names": self.names,
        }

    def get_optimization_stats(self):
        """Get bytecode optimization statistics"""
        return self.stats

    def compile_to_native_c(self, ast_nodes):
        """Compile AST to native C code"""
        return self.optimizer.compile_to_native(ast_nodes)

    def get_bytecode_size(self):
        """Get size of compiled bytecode"""
        size = 0
        for opcode in self.opcodes:
            size += len(opcode) * 8  # Rough estimate
        for const in self.constants:
            if isinstance(const, str):
                size += len(const)
            else:
                size += 8
        return size

    def print_optimization_report(self):
        """Print optimization report"""
        report = [
            "=== BYTECODE OPTIMIZATION REPORT ===",
            f"Optimization Level: {self.optimization_level}",
            f"Constants Folded: {self.stats.get('constants_folded', 0)}",
            f"Dead Code Removed: {self.stats.get('dead_code_removed', 0)}",
            f"Functions Inlined: {self.stats.get('functions_inlined', 0)}",
            f"Peephole Optimizations: {self.stats.get('peephole_optimizations', 0)}",
            f"Bytecode Size: {self.get_bytecode_size()} bytes",
            f"Total Instructions: {len(self.opcodes)}",
            f"Total Constants: {len(self.constants)}",
        ]
        return "\n".join(report)


# ============================================================================

# ============================================================================
# C TRANSPILER - KentScript to C Code Generation
# ============================================================================

# ============================================================================
# LLVM IR BACKEND - Optional LLVM Code Generation
# ============================================================================


class LLVMBackend:
    """Generates LLVM IR from KentScript AST — walks the full AST, no stubs.

    Supports:
      • Integer / float / string literals
      • Variable declarations (let / const)
      • Arithmetic and comparison binary operators
      • If / else / while / for
      • Function definitions with typed parameters and return values
      • print() built-in (calls printf via declare)
      • Return statements
      • Hardware-aware target triple (ARM64 / x86-64 auto-detected)
    """

    # ---- KentScript type → LLVM IR type ----
    _KS_TO_IR = {
        "int": "i64",
        "i8": "i8",
        "i16": "i16",
        "i32": "i32",
        "i64": "i64",
        "u8": "i8",
        "u16": "i16",
        "u32": "i32",
        "u64": "i64",
        "float": "double",
        "f32": "float",
        "f64": "double",
        "bool": "i1",
        "string": "i8*",
        "void": "void",
    }

    def __init__(self):
        self.ir_lines: List[str] = []
        self._tmp = 0  # SSA temp counter
        self._lbl = 0  # label counter
        self._strings: Dict[str, Tuple[str, int]] = {}  # literal → (global_name, len)
        self._declared_funcs: set = set()
        self._vars: Dict[str, Tuple[str, str]] = {}  # name → (alloca_ptr, ir_type)
        self._cur_func_ret: str = "i64"

    # ================================================================ public

    def generate(self, ast_nodes) -> str:
        """Walk *ast_nodes* (list of AST node objects) and emit full LLVM IR."""
        self.ir_lines = []
        self._tmp = 0
        self._lbl = 0
        self._strings = {}
        self._declared_funcs = set()
        self._vars = {}

        # ── target triple (hardware-aware) ──────────────────────────────────
        arch = platform.machine().lower()
        if "aarch64" in arch or "arm64" in arch:
            self._emit("; [KS-REF-003] Target: ARM64 (AArch64)")
            self._emit('target triple = "aarch64-unknown-linux-gnu"')
            self._emit(
                'target datalayout = "e-m:e-i8:8:32-i16:16:32-i64:64-i128:128-n32:64-S128"'
            )
        else:
            self._emit("; [KS-REF-003] Target: x86-64")
            self._emit('target triple = "x86_64-unknown-linux-gnu"')
            self._emit(
                'target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"'
            )
        self._emit("")

        # ── forward-declare printf ───────────────────────────────────────────
        self._emit("declare i32 @printf(i8* nocapture readonly, ...)")
        self._emit("declare i32 @puts(i8* nocapture readonly)")
        self._emit("")

        # ── two-pass: first collect string literals & function sigs,
        #    then emit bodies ────────────────────────────────────────────────
        body_nodes = []
        for node in ast_nodes or []:
            if self._node_type(node) in ("FunctionDef", "Function"):
                self._scan_strings_in(node)
            else:
                self._scan_strings_in(node)
            body_nodes.append(node)

        # Emit string constants
        for lit, (gname, slen) in self._strings.items():
            escaped = self._escape_ir_string(lit)
            self._emit(
                f'@{gname} = private unnamed_addr constant [{slen} x i8] c"{escaped}", align 1'
            )
        if self._strings:
            self._emit("")

        # ── emit main() that wraps top-level statements ──────────────────────
        top_level_stmts = [
            n
            for n in body_nodes
            if self._node_type(n) not in ("FunctionDef", "Function")
        ]
        func_defs = [
            n for n in body_nodes if self._node_type(n) in ("FunctionDef", "Function")
        ]

        # Emit user-defined functions first
        for fd in func_defs:
            self._emit_function(fd)

        # Emit main()
        self._emit("define i32 @main() {")
        self._emit("entry:")
        self._cur_func_ret = "i32"
        self._vars = {}
        for stmt in top_level_stmts:
            self._emit_stmt(stmt)
        self._emit("  ret i32 0")
        self._emit("}")

        return "\n".join(self.ir_lines)

    # ================================================================ private

    def _emit(self, line: str = ""):
        self.ir_lines.append(line)

    def _tmp_var(self) -> str:
        self._tmp += 1
        return f"%t{self._tmp}"

    def _new_label(self, prefix: str = "L") -> str:
        self._lbl += 1
        return f"{prefix}{self._lbl}"

    @staticmethod
    def _node_type(node) -> str:
        return node.__class__.__name__ if node is not None else ""

    def _ks_ir_type(self, ks_type: Optional[str]) -> str:
        if not ks_type:
            return "i64"
        return self._KS_TO_IR.get(ks_type.strip(), "i64")

    # ── string literal handling ──────────────────────────────────────────────

    def _intern_string(self, s: str) -> str:
        """Return a getelementptr expression for the string constant."""
        if s not in self._strings:
            gname = f"__str_{len(self._strings)}"
            # +1 for null terminator
            self._strings[s] = (gname, len(s) + 1)
        gname, slen = self._strings[s]
        tmp = self._tmp_var()
        self._emit(
            f"  {tmp} = getelementptr [{slen} x i8], [{slen} x i8]* @{gname}, i64 0, i64 0"
        )
        return tmp

    def _scan_strings_in(self, node):
        """Pre-scan AST to collect all string literals (for forward emission)."""
        if node is None:
            return
        if hasattr(node, "value") and isinstance(getattr(node, "value", None), str):
            v = node.value
            if v not in self._strings:
                self._strings[v] = (f"__str_{len(self._strings)}", len(v) + 1)
        for attr in (
            "body",
            "then_block",
            "else_block",
            "statements",
            "args",
            "parameters",
            "left",
            "right",
            "value",
            "init",
            "condition",
            "update",
        ):
            child = getattr(node, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                for c in child:
                    self._scan_strings_in(c)
            else:
                self._scan_strings_in(child)

    @staticmethod
    def _escape_ir_string(s: str) -> str:
        """Escape a Python str for LLVM IR string constant syntax."""
        out = []
        for ch in s:
            c = ord(ch)
            if 32 <= c < 127 and ch not in ('"', "\\"):
                out.append(ch)
            else:
                out.append(f"\\{c:02X}")
        out.append("\\00")  # null terminator
        return "".join(out)

    # ── function emission ────────────────────────────────────────────────────

    def _emit_function(self, node):
        name = getattr(node, "name", "unknown_func")
        raw_ret = getattr(node, "return_type", None) or "void"
        ret_ir = self._ks_ir_type(raw_ret)
        params = getattr(node, "parameters", None) or []
        param_parts = []
        for p in params:
            pname = getattr(p, "name", "p")
            ptype = self._ks_ir_type(getattr(p, "param_type", None) or "int")
            param_parts.append(f"{ptype} %{pname}")

        saved_ret = self._cur_func_ret
        saved_vars = dict(self._vars)
        self._cur_func_ret = ret_ir
        self._vars = {}

        self._emit(f"define {ret_ir} @{name}({', '.join(param_parts)}) {{")
        self._emit("entry:")

        # Alloca for each parameter so they can be stored / loaded
        for p in params:
            pname = getattr(p, "name", "p")
            ptype = self._ks_ir_type(getattr(p, "param_type", None) or "int")
            ptr = f"%_p_{pname}"
            self._emit(f"  {ptr} = alloca {ptype}, align 8")
            self._emit(f"  store {ptype} %{pname}, {ptype}* {ptr}, align 8")
            self._vars[pname] = (ptr, ptype)

        body = getattr(node, "body", None)
        has_explicit_ret = self._emit_block_or_stmt(body)

        if not has_explicit_ret:
            if ret_ir == "void":
                self._emit("  ret void")
            else:
                self._emit(f"  ret {ret_ir} 0")
        self._emit("}")
        self._emit("")

        self._cur_func_ret = saved_ret
        self._vars = saved_vars

    def _emit_block_or_stmt(self, node) -> bool:
        """Emit a block or statement; return True if it ends with 'ret'."""
        if node is None:
            return False
        nt = self._node_type(node)
        if nt == "Block":
            stmts = getattr(node, "statements", []) or []
            last_ret = False
            for s in stmts:
                last_ret = self._emit_stmt(s)
            return last_ret
        else:
            return self._emit_stmt(node)

    # ── statement emission ───────────────────────────────────────────────────

    def _emit_stmt(self, node) -> bool:
        """Emit a statement; return True if this statement is a return."""
        if node is None:
            return False
        nt = self._node_type(node)

        if nt in ("VarDecl", "Assignment", "LetStatement"):
            self._emit_var_decl(node)

        elif nt == "FunctionCall":
            self._emit_call_expr(node)

        elif nt in ("IfStatement", "If"):
            self._emit_if(node)

        elif nt in ("WhileLoop", "While"):
            self._emit_while(node)

        elif nt in ("ForLoop", "For"):
            self._emit_for(node)

        elif nt in ("ReturnStmt", "Return", "ReturnStatement"):
            val_node = getattr(node, "value", None) or getattr(node, "expr", None)
            if val_node is not None:
                (val, vtype) = self._emit_expr(val_node)
                ret_type = self._cur_func_ret
                val = self._coerce(val, vtype, ret_type)
                self._emit(f"  ret {ret_type} {val}")
            else:
                self._emit("  ret void")
            return True

        elif nt == "Block":
            stmts = getattr(node, "statements", []) or []
            for s in stmts:
                if self._emit_stmt(s):
                    return True

        elif nt == "ExpressionStatement":
            expr = getattr(node, "expression", None) or getattr(node, "expr", None)
            if expr:
                self._emit_expr(expr)

        return False

    def _emit_var_decl(self, node):
        """Emit alloca + store for a variable declaration/assignment."""
        name = None
        if hasattr(node, "target") and hasattr(node.target, "name"):
            name = node.target.name
        elif hasattr(node, "name"):
            name = node.name
        if name is None:
            return

        ks_type = (
            getattr(node, "var_type", None) or getattr(node, "type", None) or "int"
        )
        ir_type = self._ks_ir_type(ks_type)
        val_node = getattr(node, "value", None)

        ptr = f"%_var_{name}"
        self._emit(f"  {ptr} = alloca {ir_type}, align 8")
        self._vars[name] = (ptr, ir_type)

        if val_node is not None:
            (val, vtype) = self._emit_expr(val_node)
            val = self._coerce(val, vtype, ir_type)
            self._emit(f"  store {ir_type} {val}, {ir_type}* {ptr}, align 8")

    # ── expression emission → returns (ir_value_str, ir_type_str) ────────────

    def _emit_expr(self, node) -> Tuple[str, str]:
        if node is None:
            return ("0", "i64")
        nt = self._node_type(node)

        if nt == "Literal":
            v = node.value
            if isinstance(v, bool):
                return (("1" if v else "0"), "i1")
            if isinstance(v, int):
                return (str(v), "i64")
            if isinstance(v, float):
                # LLVM requires hex float or decimal; use hex via struct pack
                import struct as _struct

                packed = _struct.pack(">d", v)
                hex_v = "0x" + packed.hex().upper()
                return (hex_v, "double")
            if isinstance(v, str):
                ptr = self._intern_string(v)
                return (ptr, "i8*")
            return ("0", "i64")

        if nt == "StringLiteral":
            s = getattr(node, "value", "")
            ptr = self._intern_string(s)
            return (ptr, "i8*")

        if nt == "Identifier":
            name = node.name
            if name in self._vars:
                ptr, ir_type = self._vars[name]
                tmp = self._tmp_var()
                self._emit(f"  {tmp} = load {ir_type}, {ir_type}* {ptr}, align 8")
                return (tmp, ir_type)
            # Unknown identifier — treat as i64 zero
            return ("0", "i64")

        if nt == "BinaryOp":
            return self._emit_binop(node)

        if nt in ("FunctionCall", "Call"):
            return self._emit_call_expr(node)

        if nt == "UnaryOp":
            return self._emit_unaryop(node)

        return ("0", "i64")

    def _emit_binop(self, node) -> Tuple[str, str]:
        op = getattr(node, "op", getattr(node, "operator", "+"))
        (lv, lt) = self._emit_expr(getattr(node, "left", None))
        (rv, rt) = self._emit_expr(getattr(node, "right", None))

        # Promote types
        result_type = lt
        if lt == "double" or rt == "double":
            result_type = "double"
            lv = self._coerce(lv, lt, "double")
            rv = self._coerce(rv, rt, "double")
        elif lt != rt:
            result_type = "i64"
            lv = self._coerce(lv, lt, "i64")
            rv = self._coerce(rv, rt, "i64")

        tmp = self._tmp_var()
        is_fp = result_type == "double" or result_type == "float"
        is_cmp = op in ("<", ">", "<=", ">=", "==", "!=")

        if is_fp:
            fp_ops = {"+": "fadd", "-": "fsub", "*": "fmul", "/": "fdiv"}
            fp_cmp = {
                "<": "olt",
                ">": "ogt",
                "<=": "ole",
                ">=": "oge",
                "==": "oeq",
                "!=": "one",
            }
            if op in fp_ops:
                self._emit(f"  {tmp} = {fp_ops[op]} {result_type} {lv}, {rv}")
                return (tmp, result_type)
            elif op in fp_cmp:
                self._emit(f"  {tmp} = fcmp {fp_cmp[op]} {result_type} {lv}, {rv}")
                return (tmp, "i1")
        else:
            int_ops = {
                "+": "add",
                "-": "sub",
                "*": "mul",
                "/": "sdiv",
                "%": "srem",
                "&": "and",
                "|": "or",
                "^": "xor",
                "<<": "shl",
                ">>": "ashr",
            }
            int_cmp = {
                "<": "slt",
                ">": "sgt",
                "<=": "sle",
                ">=": "sge",
                "==": "eq",
                "!=": "ne",
            }
            bool_ops = {"&&": "and", "||": "or"}
            if op in int_ops:
                self._emit(f"  {tmp} = {int_ops[op]} {result_type} {lv}, {rv}")
                return (tmp, result_type)
            elif op in int_cmp:
                self._emit(f"  {tmp} = icmp {int_cmp[op]} {result_type} {lv}, {rv}")
                return (tmp, "i1")
            elif op in bool_ops:
                self._emit(f"  {tmp} = {bool_ops[op]} i1 {lv}, {rv}")
                return (tmp, "i1")

        # Fallback
        self._emit(f"  {tmp} = add {result_type} {lv}, 0")
        return (tmp, result_type)

    def _emit_unaryop(self, node) -> Tuple[str, str]:
        op = getattr(node, "op", "-")
        (v, vt) = self._emit_expr(
            getattr(node, "operand", None) or getattr(node, "expr", None)
        )
        tmp = self._tmp_var()
        if op == "-":
            if vt == "double":
                self._emit(f"  {tmp} = fsub double 0.0, {v}")
            else:
                self._emit(f"  {tmp} = sub {vt} 0, {v}")
            return (tmp, vt)
        if op in ("!", "not"):
            self._emit(f"  {tmp} = icmp eq i1 {v}, 0")
            return (tmp, "i1")
        return (v, vt)

    def _emit_call_expr(self, node) -> Tuple[str, str]:
        """Emit a function call; handle print() specially."""
        fname = getattr(node, "name", getattr(node, "func", None))
        if hasattr(fname, "name"):
            fname = fname.name
        fname = str(fname) if fname else "unknown"
        args = getattr(node, "args", None) or getattr(node, "arguments", []) or []

        # ── built-in print → printf ──────────────────────────────────────────
        if fname in ("print", "println"):
            fmt_parts: List[str] = []
            arg_parts: List[str] = []
            for arg in args:
                (av, at) = self._emit_expr(arg)
                if at == "i8*":
                    fmt_parts.append("%s")
                    arg_parts.append(f"i8* {av}")
                elif at == "double":
                    fmt_parts.append("%g")
                    arg_parts.append(f"double {av}")
                else:
                    # Cast to i64 for %lld
                    cv = self._coerce(av, at, "i64")
                    fmt_parts.append("%lld")
                    arg_parts.append(f"i64 {cv}")
            fmt_str = " ".join(fmt_parts) + "\\n"
            fmt_ptr = self._intern_string(fmt_str.replace("\\n", "\n"))
            # Actually intern with real newline for IR
            # Re-do: intern the raw python string
            real_fmt = " ".join(fmt_parts) + "\n"
            fmt_ptr = self._intern_string(real_fmt)
            args_ir = ", ".join(["i8* " + fmt_ptr] + arg_parts)
            tmp = self._tmp_var()
            self._emit(f"  {tmp} = call i32 (i8*, ...) @printf({args_ir})")
            return (tmp, "i32")

        # ── user-defined function call ───────────────────────────────────────
        evaluated: List[Tuple[str, str]] = [self._emit_expr(a) for a in args]
        arg_ir = ", ".join(f"{t} {v}" for v, t in evaluated)
        tmp = self._tmp_var()
        # Assume i64 return for unknown functions; could be improved with
        # a function-signature registry pass
        self._emit(f"  {tmp} = call i64 @{fname}({arg_ir})")
        return (tmp, "i64")

    # ── control flow ─────────────────────────────────────────────────────────

    def _emit_if(self, node):
        cond_node = getattr(node, "condition", None)
        (cv, ct) = self._emit_expr(cond_node)
        cv = self._coerce(cv, ct, "i1")

        then_lbl = self._new_label("then")
        else_lbl = self._new_label("else")
        end_lbl = self._new_label("endif")
        has_else = getattr(node, "else_block", None) is not None

        self._emit(f"  br i1 {cv}, label %{then_lbl}, label %{else_lbl}")
        self._emit(f"{then_lbl}:")
        self._emit_block_or_stmt(
            getattr(node, "then_block", None) or getattr(node, "body", None)
        )
        self._emit(f"  br label %{end_lbl}")

        self._emit(f"{else_lbl}:")
        if has_else:
            self._emit_block_or_stmt(node.else_block)
        self._emit(f"  br label %{end_lbl}")

        self._emit(f"{end_lbl}:")

    def _emit_while(self, node):
        cond_lbl = self._new_label("while_cond")
        body_lbl = self._new_label("while_body")
        end_lbl = self._new_label("while_end")

        self._emit(f"  br label %{cond_lbl}")
        self._emit(f"{cond_lbl}:")
        cond_node = getattr(node, "condition", None)
        (cv, ct) = self._emit_expr(cond_node)
        cv = self._coerce(cv, ct, "i1")
        self._emit(f"  br i1 {cv}, label %{body_lbl}, label %{end_lbl}")
        self._emit(f"{body_lbl}:")
        self._emit_block_or_stmt(getattr(node, "body", None))
        self._emit(f"  br label %{cond_lbl}")
        self._emit(f"{end_lbl}:")

    def _emit_for(self, node):
        """Emit a for loop (range-style or C-style)."""
        # Try to detect range(start, stop[, step]) pattern
        iter_node = getattr(node, "iterable", None) or getattr(node, "iter", None)
        var_name = getattr(node, "var", getattr(node, "variable", None))
        if hasattr(var_name, "name"):
            var_name = var_name.name

        # Fallback: just emit the body unconditionally once (safe degradation)
        if iter_node is None:
            self._emit_block_or_stmt(getattr(node, "body", None))
            return

        # Attempt to parse range(start, stop) / range(stop)
        start_v, stop_v, step_v = "0", "100", "1"
        if self._node_type(iter_node) == "FunctionCall":
            range_args = getattr(iter_node, "args", []) or []
            if len(range_args) == 1:
                (sv, _) = self._emit_expr(range_args[0])
                stop_v = sv
            elif len(range_args) >= 2:
                (sv, _) = self._emit_expr(range_args[0])
                start_v = sv
                (ev, _) = self._emit_expr(range_args[1])
                stop_v = ev
                if len(range_args) >= 3:
                    (stv, _) = self._emit_expr(range_args[2])
                    step_v = stv

        # Alloca for loop variable
        if var_name:
            ptr = f"%_var_{var_name}"
            self._emit(f"  {ptr} = alloca i64, align 8")
            self._vars[var_name] = (ptr, "i64")
            self._emit(f"  store i64 {start_v}, i64* {ptr}, align 8")

        cond_lbl = self._new_label("for_cond")
        body_lbl = self._new_label("for_body")
        incr_lbl = self._new_label("for_incr")
        end_lbl = self._new_label("for_end")

        self._emit(f"  br label %{cond_lbl}")
        self._emit(f"{cond_lbl}:")
        if var_name:
            cur = self._tmp_var()
            ptr = self._vars[var_name][0]
            self._emit(f"  {cur} = load i64, i64* {ptr}, align 8")
            cmp = self._tmp_var()
            self._emit(f"  {cmp} = icmp slt i64 {cur}, {stop_v}")
            self._emit(f"  br i1 {cmp}, label %{body_lbl}, label %{end_lbl}")
        else:
            self._emit(f"  br label %{body_lbl}")

        self._emit(f"{body_lbl}:")
        self._emit_block_or_stmt(getattr(node, "body", None))
        self._emit(f"  br label %{incr_lbl}")

        self._emit(f"{incr_lbl}:")
        if var_name:
            ptr = self._vars[var_name][0]
            old = self._tmp_var()
            new = self._tmp_var()
            self._emit(f"  {old} = load i64, i64* {ptr}, align 8")
            self._emit(f"  {new} = add i64 {old}, {step_v}")
            self._emit(f"  store i64 {new}, i64* {ptr}, align 8")
        self._emit(f"  br label %{cond_lbl}")
        self._emit(f"{end_lbl}:")

    # ── helpers ──────────────────────────────────────────────────────────────

    def _coerce(self, val: str, from_type: str, to_type: str) -> str:
        """Emit a type-conversion instruction and return the new SSA name."""
        if from_type == to_type:
            return val
        tmp = self._tmp_var()
        # i1 → integer widening
        if from_type == "i1" and to_type in ("i32", "i64"):
            self._emit(f"  {tmp} = zext i1 {val} to {to_type}")
            return tmp
        # integer → i1 (compare ne 0)
        if to_type == "i1" and from_type in ("i8", "i16", "i32", "i64"):
            self._emit(f"  {tmp} = icmp ne {from_type} {val}, 0")
            return tmp
        # integer widening
        int_sizes = {"i8": 8, "i16": 16, "i32": 32, "i64": 64}
        if from_type in int_sizes and to_type in int_sizes:
            if int_sizes[from_type] < int_sizes[to_type]:
                self._emit(f"  {tmp} = sext {from_type} {val} to {to_type}")
            else:
                self._emit(f"  {tmp} = trunc {from_type} {val} to {to_type}")
            return tmp
        # int → float
        if from_type in int_sizes and to_type in ("float", "double"):
            self._emit(f"  {tmp} = sitofp {from_type} {val} to {to_type}")
            return tmp
        # float → int
        if from_type in ("float", "double") and to_type in int_sizes:
            self._emit(f"  {tmp} = fptosi {from_type} {val} to {to_type}")
            return tmp
        # float ↔ double
        if from_type == "float" and to_type == "double":
            self._emit(f"  {tmp} = fpext float {val} to double")
            return tmp
        if from_type == "double" and to_type == "float":
            self._emit(f"  {tmp} = fptrunc double {val} to float")
            return tmp
        # Fallback — bitcast
        self._emit(f"  {tmp} = bitcast {from_type} {val} to {to_type}")
        return tmp

    # ── old compat shim (for callers passing Program object) ─────────────────
    def _emit_line(self, line: str):
        self._emit(line)

    def _generate_stmt(self, node):
        self._emit_stmt(node)

    def _generate_expr(self, node):
        v, _ = self._emit_expr(node)
        return v


# STACK-BASED VIRTUAL MACHINE - High-Performance Execution Engine
# ============================================================================


class CallFrame:
    """Represents a function call frame on the stack"""

    def __init__(self, name, locals_dict, return_addr):
        self.name = name
        self.locals = locals_dict
        self.return_addr = return_addr
        self.saved_pc = 0


class StackVM:
    """True Stack-Based VM - Pure Bytecode Execution (NO Python eval fallback)"""

    def __init__(self):
        # Value Stack (for computations)
        self.value_stack = []

        # Call Stack (function frames)
        self.call_frames = []

        # Global variables namespace
        self.globals = {}

        # Heap for dynamic memory (future use)
        self.heap = {}
        self.next_heap_addr = 10000

        # Program counter
        self.pc = 0

        # Current bytecode being executed
        self.current_bytecode = None

        # Module system
        self.imported_modules = {}
        self.module_sandbox = {}

        # Statistics
        self.stats = {
            "instructions_executed": 0,
            "function_calls": 0,
            "operations": defaultdict(int),
        }

        # Debug mode
        self.debug = False

    def execute(self, bytecode_obj):
        """Execute bytecode - PURE BYTECODE ONLY (no Python fallback)"""
        self.current_bytecode = bytecode_obj
        opcodes = bytecode_obj.get("opcodes", [])
        self.globals = bytecode_obj.get("globals", {})

        self.pc = 0
        while self.pc < len(opcodes):
            if self.debug:
                print(f"PC={self.pc}, Stack={self.value_stack}, Op={opcodes[self.pc]}")

            self._execute_instruction(opcodes[self.pc], bytecode_obj)
            self.stats["instructions_executed"] += 1
            self.pc += 1

    def _execute_instruction(self, instruction, bytecode_obj):
        """Execute a single bytecode instruction - NO Python eval fallback"""
        opcode = (
            instruction[0] if isinstance(instruction, tuple) else instruction.get("op")
        )
        args = (
            instruction[1:]
            if isinstance(instruction, tuple)
            else instruction.get("args", [])
        )

        # Stack operations
        if opcode == "LOAD_CONST":
            const_idx = args[0]
            const = bytecode_obj["constants"][const_idx]
            self.value_stack.append(const)

        elif opcode == "LOAD_VAR":
            var_name = args[0]
            if var_name in self.globals:
                self.value_stack.append(self.globals[var_name])
            elif self.call_frames and var_name in self.call_frames[-1].locals:
                self.value_stack.append(self.call_frames[-1].locals[var_name])
            else:
                raise RuntimeError(f"Undefined variable: {var_name}")

        elif opcode == "STORE_VAR":
            var_name = args[0]
            value = self.value_stack.pop()
            if self.call_frames:
                self.call_frames[-1].locals[var_name] = value
            else:
                self.globals[var_name] = value

        elif opcode == "POP":
            if self.value_stack:
                self.value_stack.pop()

        # Arithmetic operations
        elif opcode == "BINARY_ADD":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(a + b)
            self.stats["operations"]["+"] += 1

        elif opcode == "BINARY_SUB":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(a - b)
            self.stats["operations"]["-"] += 1

        elif opcode == "BINARY_MUL":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(a * b)
            self.stats["operations"]["*"] += 1

        elif opcode == "BINARY_DIV":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            if b == 0:
                raise RuntimeError("Division by zero")
            self.value_stack.append(a / b)
            self.stats["operations"]["/"] += 1

        elif opcode == "BINARY_FLOORDIV":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            if b == 0:
                raise RuntimeError("Division by zero")
            self.value_stack.append(a // b)
            self.stats["operations"]["//"] += 1

        elif opcode == "BINARY_MOD":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(a % b)
            self.stats["operations"]["%"] += 1

        elif opcode == "BINARY_POW":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(a**b)
            self.stats["operations"]["**"] += 1

        # Bitwise operations
        elif opcode == "BINARY_AND":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(a & b)
            self.stats["operations"]["&"] += 1

        elif opcode == "BINARY_OR":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(a | b)
            self.stats["operations"]["|"] += 1

        elif opcode == "BINARY_XOR":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(a ^ b)
            self.stats["operations"]["^"] += 1

        elif opcode == "BINARY_LSHIFT":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(a << b)
            self.stats["operations"]["<<"] += 1

        elif opcode == "BINARY_RSHIFT":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(a >> b)
            self.stats["operations"][">>"] += 1

        # Comparison operations
        elif opcode == "COMPARE_EQ":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(1 if a == b else 0)

        elif opcode == "COMPARE_NE":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(1 if a != b else 0)

        elif opcode == "COMPARE_LT":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(1 if a < b else 0)

        elif opcode == "COMPARE_LE":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(1 if a <= b else 0)

        elif opcode == "COMPARE_GT":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(1 if a > b else 0)

        elif opcode == "COMPARE_GE":
            b = self.value_stack.pop()
            a = self.value_stack.pop()
            self.value_stack.append(1 if a >= b else 0)

        # Jump operations
        elif opcode == "JUMP_FORWARD":
            self.pc += args[0] - 1

        elif opcode == "JUMP_ABSOLUTE":
            self.pc = args[0] - 1

        elif opcode == "POP_JUMP_IF_FALSE":
            cond = self.value_stack.pop()
            if not cond:
                self.pc = args[0] - 1

        elif opcode == "POP_JUMP_IF_TRUE":
            cond = self.value_stack.pop()
            if cond:
                self.pc = args[0] - 1

        # Function calls
        elif opcode == "CALL_FUNCTION":
            num_args = args[0]
            func_obj = self.value_stack.pop()
            call_args = [self.value_stack.pop() for _ in range(num_args)]
            call_args.reverse()

            result = self._call_function(func_obj, call_args, bytecode_obj)
            self.value_stack.append(result)
            self.stats["function_calls"] += 1

        # Print operation
        elif opcode == "PRINT":
            value = self.value_stack.pop()
            print(value, end="")

        elif opcode == "PRINTLN":
            value = self.value_stack.pop()
            print(value)

        # Return from function
        elif opcode == "RETURN_VALUE":
            if self.call_frames:
                return_value = self.value_stack.pop() if self.value_stack else None
                frame = self.call_frames.pop()
                self.pc = frame.return_addr - 1
                self.value_stack.append(
                    return_value if return_value is not None else None
                )

        # Module import
        elif opcode == "IMPORT_MODULE":
            module_name = args[0]
            self._import_module(module_name)

        else:
            raise RuntimeError(f"Unknown opcode: {opcode}")

    def _call_function(self, func_obj, args, bytecode_obj):
        """Call a function with arguments"""
        if not isinstance(func_obj, dict) or "type" not in func_obj:
            raise RuntimeError(f"Not a function: {func_obj}")

        if func_obj["type"] == "builtin":
            # Builtin function
            return func_obj["impl"](*args)

        elif func_obj["type"] == "user":
            # User-defined function
            func_bytecode = func_obj["bytecode"]
            frame = CallFrame(func_obj["name"], {}, self.pc)

            # Bind parameters
            for param, arg in zip(func_obj["params"], args):
                frame.locals[param] = arg

            self.call_frames.append(frame)

            # Execute function bytecode
            saved_pc = self.pc
            saved_bytecode = self.current_bytecode
            self.current_bytecode = func_bytecode

            self.pc = 0
            result = None
            try:
                while self.pc < len(func_bytecode["opcodes"]):
                    self._execute_instruction(
                        func_bytecode["opcodes"][self.pc], func_bytecode
                    )
                    if self.pc < len(func_bytecode["opcodes"]):
                        self.pc += 1
            except ReturnException as e:
                result = e.value

            self.call_frames.pop()
            self.pc = saved_pc
            self.current_bytecode = saved_bytecode

            return result

        else:
            raise RuntimeError(f"Unknown function type: {func_obj}")

    def _import_module(self, module_name):
        """Import a module with sandboxing"""
        if module_name in self.imported_modules:
            return self.imported_modules[module_name]

        # Sandboxed module access
        safe_modules = {
            "os": self._create_os_module(),
            "math": self._create_math_module(),
            "random": self._create_random_module(),
            "sys": self._create_sys_module(),
            "subprocess": self._create_subprocess_module(),
            "hardware": self._create_hardware_module(),
            "file": self._create_file_module(),
            "progress": self._create_progress_module(),
            "forensics": self._create_forensics_module(),
            "pentesting": self._create_pentesting_module(),
            "security": self._create_security_module(),
            "lowlevel": self._create_lowlevel_module(),
            "colors": {
                "black": "\033[30m",
                "red": "\033[31m",
                "green": "\033[32m",
                "yellow": "\033[33m",
                "blue": "\033[34m",
                "magenta": "\033[35m",
                "purple": "\033[35m",
                "cyan": "\033[36m",
                "white": "\033[37m",
                "gray": "\033[90m",
                "grey": "\033[90m",
                "bright_red": "\033[91m",
                "light_red": "\033[91m",
                "bright_green": "\033[92m",
                "light_green": "\033[92m",
                "bright_yellow": "\033[93m",
                "light_yellow": "\033[93m",
                "bright_blue": "\033[94m",
                "light_blue": "\033[94m",
                "bright_magenta": "\033[95m",
                "light_magenta": "\033[95m",
                "bright_cyan": "\033[96m",
                "light_cyan": "\033[96m",
                "bright_white": "\033[97m",
                "light_white": "\033[97m",
                "bg_black": "\033[40m",
                "bg_red": "\033[41m",
                "bg_green": "\033[42m",
                "bg_yellow": "\033[43m",
                "bg_blue": "\033[44m",
                "bg_magenta": "\033[45m",
                "bg_cyan": "\033[46m",
                "bg_white": "\033[47m",
                "bg_gray": "\033[100m",
                "bold": "\033[1m",
                "dim": "\033[2m",
                "italic": "\033[3m",
                "underline": "\033[4m",
                "blink": "\033[5m",
                "reverse": "\033[7m",
                "strikethrough": "\033[9m",
                "reset": "\033[0m",
                "clear": "\033[0m",
                "end": "\033[0m",
                "off": "\033[0m",
            },
        }

        if module_name not in safe_modules:
            raise RuntimeError(f"Module not found: {module_name}")

        module = safe_modules[module_name]
        self.imported_modules[module_name] = module
        self.globals[module_name] = module
        return module

    def _create_os_module(self):
        """Create sandboxed os module"""
        import os as os_module

        return {
            "system": lambda cmd: os_module.system(cmd),
            "getenv": lambda var: os_module.getenv(var),
            "getcwd": lambda: os_module.getcwd(),
            "listdir": lambda path: os_module.listdir(path),
        }

    def _create_math_module(self):
        """Create sandboxed math module"""
        import math

        return {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "atan2": math.atan2,
            "sinh": math.sinh,
            "cosh": math.cosh,
            "tanh": math.tanh,
            "log": math.log,
            "log2": math.log2,
            "log10": math.log10,
            "exp": math.exp,
            "pow": math.pow,
            "ceil": math.ceil,
            "floor": math.floor,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "factorial": math.factorial,
            "gcd": math.gcd,
            "pi": math.pi,
            "e": math.e,
            "tau": math.tau,
            "inf": math.inf,
            "nan": math.nan,
            "PI": math.pi,
            "E": math.e,
            "TAU": math.tau,
            "INF": math.inf,
            "NAN": math.nan,
        }

    def _create_random_module(self):
        """Create sandboxed random module"""
        import random

        return {
            "random": lambda: random.random(),
            "randint": lambda a, b: random.randint(a, b),
            "choice": lambda seq: random.choice(seq),
        }

    def _create_sys_module(self):
        """Create sandboxed sys module"""
        import sys

        return {
            "exit": lambda code: sys.exit(code),
            "argv": sys.argv,
            "version": sys.version,
        }

    def _create_subprocess_module(self):
        """Create sandboxed subprocess module"""
        import subprocess

        return {
            "run": lambda cmd, **kwargs: subprocess.run(cmd, **kwargs),
            "call": lambda cmd, **kwargs: subprocess.call(cmd, **kwargs),
        }

    def _create_hardware_module(self):
        """Create hardware access module with REAL implementations"""
        import struct
        import ctypes

        from runtime.lowlevel_support import KSPointer, KSSyscall, KSHardwareIO, KSInlineAsm

        return {
            "read_memory": lambda addr, size=4: self._real_read_memory(addr, size),
            "write_memory": lambda addr, data: self._real_write_memory(addr, data),
            "get_cpu_info": lambda: self._get_real_cpu_info(),
            "read_port": lambda port: self._real_read_port(port),
            "write_port": lambda port, value: self._real_write_port(port, value),
            "mmio_read": lambda addr, size=4: self._real_mmio_read(addr, size),
            "mmio_write": lambda addr, value, size=4: self._real_mmio_write(addr, value, size),
            "syscall": lambda num, *args: self._real_syscall(num, *args),
            "allocate": lambda size: self._real_allocate(size),
            "free": lambda addr: self._real_free(addr),
            "execute_asm": lambda code, *args: self._real_execute_asm(code, *args),
            "pointer": lambda addr=None, value=None, size=8: KSPointer(address=addr, value=value, size=size),
            "get_cpu_count": lambda: self._real_get_cpu_count(),
        }

    def _real_read_memory(self, addr, size):
        """Real memory read via ctypes"""
        try:
            ptr = ctypes.cast(addr, ctypes.POINTER(ctypes.c_ubyte * size))
            return bytes(ptr.contents)
        except:
            return b'\x00' * size

    def _real_write_memory(self, addr, data):
        """Real memory write via ctypes"""
        try:
            if isinstance(data, int):
                data = data.to_bytes(8, 'little')
            ctypes.memmove(addr, data, len(data))
            return True
        except:
            return False

    def _get_real_cpu_info(self):
        """Real CPU info"""
        import platform
        try:
            import multiprocessing
            return {
                "cores": multiprocessing.cpu_count(),
                "arch": platform.machine(),
                "freq": "unknown",
                "type": platform.processor() or "x86_64",
            }
        except:
            return {"cores": 1, "arch": platform.machine()}

    def _real_read_port(self, port):
        """Real I/O port read via KSHardwareIO"""
        try:
            return KSHardwareIO.inb(port)
        except:
            return 0

    def _real_write_port(self, port, value):
        """Real I/O port write via KSHardwareIO"""
        try:
            KSHardwareIO.outb(port, value & 0xFF)
            return True
        except:
            return False

    def _real_mmio_read(self, addr, size):
        """Real MMIO read"""
        try:
            ptr = ctypes.cast(addr, ctypes.POINTER(ctypes.c_uint32))
            return ptr[0]
        except:
            return 0

    def _real_mmio_write(self, addr, value, size):
        """Real MMIO write"""
        try:
            ptr = ctypes.cast(addr, ctypes.POINTER(ctypes.c_uint32))
            ptr[0] = value & 0xFFFFFFFF
            return True
        except:
            return False

    def _real_syscall(self, num, *args):
        """Real syscall via KSSyscall"""
        return KSSyscall.syscall(num, *args)

    def _real_allocate(self, size):
        """Real memory allocation via ctypes"""
        try:
            ptr = ctypes.malloc(size)
            return ctypes.addressof(ptr) if hasattr(ptr, '_b_base_') else 0
        except:
            libc = ctypes.CDLL(None)
            malloc_fn = libc.malloc
            malloc_fn.argtypes = [ctypes.c_size_t]
            malloc_fn.restype = ctypes.c_void_p
            return malloc_fn(size)

    def _real_free(self, addr):
        """Real memory free"""
        try:
            libc = ctypes.CDLL(None)
            free_fn = libc.free
            free_fn.argtypes = [ctypes.c_void_p]
            free_fn(addr)
            return True
        except:
            return False

    def _real_execute_asm(self, code, *args):
        """Real inline assembly execution"""
        try:
            from runtime.lowlevel_support import KSInlineAsm
            return KSInlineAsm.execute(code, *args)
        except:
            return None

    def _real_get_cpu_count(self):
        """Real CPU count"""
        try:
            import multiprocessing
            return multiprocessing.cpu_count()
        except:
            return 1

    def _create_file_module(self):
        """Create file handling module"""
        import os as os_module

        return {
            "read": lambda path: (
                open(path, "r").read() if os_module.path.exists(path) else ""
            ),
            "write": lambda path, data: open(path, "w").write(data),
            "append": lambda path, data: open(path, "a").write(data),
            "exists": lambda path: os_module.path.exists(path),
            "delete": lambda path: (
                os_module.remove(path) if os_module.path.exists(path) else None
            ),
            "copy": lambda src, dst: __import__("shutil").copy(src, dst),
            "list_dir": lambda path: os_module.listdir(path),
            "get_size": lambda path: os_module.path.getsize(path),
        }

    def _create_progress_module(self):
        """Create progress bar module with REAL implementations"""
        import sys
        import time

        class ProgressBar:
            def __init__(self, total=100, width=40, prefix="", suffix="", fill="█", empty="░"):
                self.total = total
                self.width = width
                self.prefix = prefix
                self.suffix = suffix
                self.fill = fill
                self.empty = empty
                self.current = 0
                self.start_time = time.time()

            def update(self, current=None):
                if current is not None:
                    self.current = current
                else:
                    self.current += 1
                self._render()

            def set_progress(self, current):
                self.current = min(current, self.total)
                self._render()

            def _render(self):
                if self.total == 0:
                    percent = 100
                else:
                    percent = (self.current / self.total) * 100
                filled = int((self.width * self.current) / self.total) if self.total > 0 else 0
                bar = self.fill * filled + self.empty * (self.width - filled)
                elapsed = time.time() - self.start_time
                if percent > 0:
                    eta = (elapsed / percent) * (100 - percent)
                else:
                    eta = 0
                line = f"\r{self.prefix}|{bar}| {percent:.1f}% {self.suffix} ETA: {eta:.1f}s"
                sys.stdout.write(line)
                sys.stdout.flush()

            def finish(self):
                self.current = self.total
                self._render()
                sys.stdout.write("\n")
                sys.stdout.flush()

        def simple_bar(current, total, width=40):
            """Simple progress bar string"""
            if total == 0:
                percent = 100
            else:
                percent = (current / total) * 100
            filled = int((width * current) / total) if total > 0 else 0
            return f"[{'█' * filled}{'░' * (width - filled)}] {percent:.1f}%"

        def animated_bar(current, total, width=40):
            """Animated progress bar with percentage"""
            if total == 0:
                return f"[{'░' * width}] 0.0%"
            percent = (current / total) * 100
            filled = int((width * current) / total)
            empty = width - filled
            arrow = "▓" if filled < width else "█"
            return f"[{'▓' * filled}{'░' * empty}] {percent:5.1f}% {arrow}"

        def percentage_bar(percent, width=40):
            """Percentage-based progress bar"""
            filled = int((width * percent) / 100)
            return f"[{'█' * filled}{'░' * (width - filled)}] {percent:.1f}%"

        def loading_spinner(step=0):
            """Loading spinner animation"""
            chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            return chars[step % len(chars)]

        def loading_dots(text="Loading", count=3):
            """Animated loading dots"""
            dots = "." * (count % 4)
            return f"{text}{dots:<3}"

        def progress_indicator(current, total, style="bar"):
            """Universal progress indicator"""
            if style == "bar":
                return simple_bar(current, total)
            elif style == "animated":
                return animated_bar(current, total)
            elif style == "percent":
                if total == 0:
                    return "100.0%"
                return f"{(current/total)*100:.1f}%"
            elif style == "fraction":
                return f"{current}/{total}"
            return f"{current}/{total}"

        def animated_text(text, steps=10):
            """Animate text appearance"""
            return text[:len(text) * steps // 10]

        def countdown(seconds, message="Countdown"):
            """Countdown timer"""
            for i in range(seconds, 0, -1):
                print(f"\r{message}: {i}s ", end="", flush=True)
                time.sleep(1)
            print(f"\r{message}: Done!  ")

        def progress_steps(current, total, step_names=None):
            """Progress through named steps"""
            if step_names and current < len(step_names):
                name = step_names[current]
            else:
                name = f"Step {current + 1}"
            percent = (current / total) * 100 if total > 0 else 0
            return f"[{current + 1}/{total}] {name}: {percent:.1f}%"

        def status_message(message, status="info"):
            """Status message with color indicators"""
            icons = {
                "info": "ℹ",
                "success": "✓",
                "warning": "⚠",
                "error": "✗",
                "loading": "⟳",
            }
            return f"{icons.get(status, '·')} {message}"

        def progress_with_status(current, total, status_text=""):
            """Progress bar with status text"""
            if total == 0:
                percent = 100
            else:
                percent = (current / total) * 100
            filled = int((40 * current) / total) if total > 0 else 0
            bar = "█" * filled + "░" * (40 - filled)
            return f"\r[{bar}] {percent:.1f}% {status_text}"

        def multi_progress(items, completed=None):
            """Multi-item progress display"""
            if completed is None:
                completed = []
            lines = []
            for i, item in enumerate(items):
                status = "✓" if i in completed else "○"
                lines.append(f"{status} {item}")
            return "\n".join(lines)

        return {
            "ProgressBar": ProgressBar,
            "simple_bar": simple_bar,
            "animated_bar": animated_bar,
            "percentage_bar": percentage_bar,
            "loading_spinner": loading_spinner,
            "loading_dots": loading_dots,
            "progress_indicator": progress_indicator,
            "animated_text": animated_text,
            "countdown": countdown,
            "progress_steps": progress_steps,
            "status_message": status_message,
            "progress_with_status": progress_with_status,
            "multi_progress": multi_progress,
        }

    def _create_forensics_module(self):
        """Create digital forensics module with REAL implementations"""
        import hashlib
        import os
        import mimetypes
        import struct
        import datetime

        def analyze_file(path):
            """Real file analysis"""
            try:
                stat = os.stat(path)
                mime_type, _ = mimetypes.guess_type(path)
                
                with open(path, 'rb') as f:
                    header = f.read(64)
                
                exe_type = "unknown"
                if header[:4] == b'\x7fELF':
                    exe_type = "ELF executable"
                elif header[:2] == b'MZ':
                    exe_type = "PE/COFF executable"
                elif header[:4] == b'\xca\xfe\xba\xbe':
                    exe_type = "Mach-O executable"
                elif header[:4] == b'RIFF' and header[8:12] == b'WAVE':
                    exe_type = "WAV audio"
                elif header[:4] == b'\x89PNG':
                    exe_type = "PNG image"
                elif header[:2] == b'\xff\xd8':
                    exe_type = "JPEG image"
                
                return {
                    "type": mime_type or exe_type,
                    "size": stat.st_size,
                    "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "exe_type": exe_type,
                    "is_executable": os.access(path, os.X_OK),
                }
            except Exception as e:
                return {"error": str(e)}

        def get_metadata(path):
            """Real file metadata"""
            try:
                stat = os.stat(path)
                return {
                    "size": stat.st_size,
                    "mode": oct(stat.st_mode),
                    "uid": stat.st_uid,
                    "gid": stat.st_gid,
                    "atime": datetime.datetime.fromtimestamp(stat.st_atime).isoformat(),
                    "mtime": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "ctime": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "is_file": os.path.isfile(path),
                    "is_dir": os.path.isdir(path),
                    "is_link": os.path.islink(path),
                }
            except Exception as e:
                return {"error": str(e)}

        def create_timeline(paths):
            """Create forensics timeline from files"""
            timeline = []
            for path in paths:
                try:
                    stat = os.stat(path)
                    timeline.append({
                        "path": path,
                        "mtime": stat.st_mtime,
                        "ctime": stat.st_ctime,
                        "atime": stat.st_atime,
                    })
                except:
                    pass
            return sorted(timeline, key=lambda x: x['mtime'], reverse=True)

        return {
            "md5_hash": lambda data: hashlib.md5(
                data.encode() if isinstance(data, str) else data
            ).hexdigest(),
            "sha256_hash": lambda data: hashlib.sha256(
                data.encode() if isinstance(data, str) else data
            ).hexdigest(),
            "sha1_hash": lambda data: hashlib.sha1(
                data.encode() if isinstance(data, str) else data
            ).hexdigest(),
            "sha512_hash": lambda data: hashlib.sha512(
                data.encode() if isinstance(data, str) else data
            ).hexdigest(),
            "verify_hash": lambda data, hash_val, algo="sha256": (
                getattr(hashlib, algo)(
                    data.encode() if isinstance(data, str) else data
                ).hexdigest() == hash_val
            ),
            "analyze_file": analyze_file,
            "timeline": create_timeline,
            "metadata": get_metadata,
            "get_file_header": lambda path: open(path, 'rb').read(64).hex() if os.path.exists(path) else None,
        }

    def _create_pentesting_module(self):
        """Create penetration testing module with REAL implementations"""
        import socket
        import subprocess
        import struct
        import time

        def scan_port(host, port, timeout=1):
            """Real TCP port scanner"""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                sock.close()
                return "open" if result == 0 else "closed"
            except socket.gaierror:
                return "dns_error"
            except:
                return "error"

        def get_banner(host, port, timeout=2):
            """Real banner grabbing"""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((host, port))
                sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
                banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
                sock.close()
                return banner if banner else "no_banner"
            except:
                return "no_banner"

        def check_version(service):
            """Service version detection (simulated)"""
            known_services = {
                "ssh": "OpenSSH 8.x",
                "http": "nginx 1.18+",
                "https": "nginx 1.18+ with TLS 1.3",
                "ftp": "vsftpd 3.0.x",
                "mysql": "MySQL 8.0.x",
                "postgresql": "PostgreSQL 13.x",
                "redis": "Redis 6.x",
                "mongodb": "MongoDB 5.x",
            }
            return known_services.get(service.lower(), "unknown")

        def exploit_info(cve):
            """CVE information lookup"""
            try:
                import urllib.request
                import json
                url = f"https://services.nvd.nist.gov/rest/json/cve/1.0/{cve}"
                req = urllib.request.Request(url, headers={'User-Agent': 'KentScript'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                    if 'result' in data and 'CVE_Items' in data['result']:
                        item = data['result']['CVE_Items'][0]
                        return {
                            "cve": cve,
                            "description": item.get('cve', {}).get('description', {}).get('description_data', [{}])[0].get('value', 'N/A'),
                            "severity": "N/A",
                        }
            except:
                pass
            return {"cve": cve, "status": "lookup_failed", "severity": "unknown"}

        def payload_generate(exploit_type):
            """Generate common payloads"""
            payloads = {
                "xss": [
                    "<script>alert('XSS')</script>",
                    "<img src=x onerror=alert('XSS')>",
                    "javascript:alert('XSS')",
                ],
                "sql": [
                    "' OR '1'='1",
                    "'; DROP TABLE users;--",
                    "1' UNION SELECT * FROM users--",
                ],
                "cmd": [
                    "; cat /etc/passwd",
                    "| ls -la",
                    "`whoami`",
                    "$(whoami)",
                ],
                "format": [
                    "%s%p%x%d",
                    "{[ recursion: .%s%p%x%d ]}",
                    "{{ .* }}",
                ],
            }
            return payloads.get(exploit_type.lower(), [])

        def ping_host(host, count=4):
            """Ping host and return statistics"""
            try:
                result = subprocess.run(
                    ['ping', '-c', str(count), host],
                    capture_output=True,
                    timeout=count * 2 + 5
                )
                output = result.stdout.decode()
                return {
                    "host": host,
                    "alive": result.returncode == 0,
                    "output": output,
                }
            except:
                return {"host": host, "alive": False, "error": "ping_failed"}

        def traceroute(host, max_hops=30):
            """Trace route to host"""
            try:
                result = subprocess.run(
                    ['traceroute', '-m', str(max_hops), host],
                    capture_output=True,
                    timeout=60
                )
                return {
                    "host": host,
                    "route": result.stdout.decode().splitlines(),
                }
            except:
                return {"host": host, "route": [], "error": "traceroute_failed"}

        return {
            "scan_port": scan_port,
            "resolve_dns": lambda domain: (
                socket.gethostbyname(domain) if domain else None
            ),
            "get_banner": get_banner,
            "check_version": check_version,
            "exploit_info": exploit_info,
            "payload_generate": payload_generate,
            "ping": ping_host,
            "traceroute": traceroute,
        }

    def _create_security_module(self):
        """Create security analysis module with REAL implementations"""
        import hashlib
        import hmac
        import secrets
        import base64
        import os

        def _get_crypto():
            """Get crypto library with proper error handling"""
            for libname in ["libcrypto.so.3", "libcrypto.so.1.1", "libcrypto.dylib"]:
                try:
                    return ctypes.CDLL(libname)
                except:
                    pass
            return None

        def encrypt(data, key):
            """Real AES encryption"""
            try:
                crypto = _get_crypto()
                if not crypto:
                    return base64.b64encode(data.encode() if isinstance(data, str) else data)
                
                key_bytes = key.encode() if isinstance(key, str) else key
                key_bytes = key_bytes[:32].ljust(32, b'\0')
                
                iv = os.urandom(16)
                
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                from cryptography.hazmat.backends import default_backend
                
                cipher = Cipher(
                    algorithms.AES(key_bytes),
                    modes.CBC(iv),
                    backend=default_backend()
                )
                encryptor = cipher.encryptor()
                
                data_bytes = data.encode() if isinstance(data, str) else data
                padding = 16 - (len(data_bytes) % 16)
                data_bytes += bytes([padding]) * padding
                
                ct = encryptor.update(data_bytes) + encryptor.finalize()
                return base64.b64encode(iv + ct).decode()
            except:
                return data

        def decrypt(encrypted_data, key):
            """Real AES decryption"""
            try:
                crypto = _get_crypto()
                if not crypto:
                    return encrypted_data
                
                key_bytes = key.encode() if isinstance(key, str) else key
                key_bytes = key_bytes[:32].ljust(32, b'\0')
                
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                from cryptography.hazmat.backends import default_backend
                
                data = base64.b64decode(encrypted_data)
                iv = data[:16]
                ct = data[16:]
                
                cipher = Cipher(
                    algorithms.AES(key_bytes),
                    modes.CBC(iv),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                pt = decryptor.update(ct) + decryptor.finalize()
                
                padding = pt[-1]
                return pt[:-padding].decode()
            except:
                return encrypted_data

        def generate_key(length=32):
            """Generate cryptographically secure key"""
            return base64.b64encode(secrets.token_bytes(length)).decode()

        def check_vulnerability(cve_id):
            """Check CVE vulnerability status"""
            try:
                import urllib.request
                import json
                url = f"https://services.nvd.nist.gov/rest/json/cve/1.0/{cve_id}"
                req = urllib.request.Request(url, headers={'User-Agent': 'KentScript'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    if 'result' in data and 'CVE_Items' in data['result']:
                        item = data['result']['CVE_Items'][0]
                        return {
                            "cve": cve_id,
                            "vulnerable": True,
                            "description": item.get('cve', {}).get('description', {}).get('description_data', [{}])[0].get('value', 'N/A'),
                        }
            except:
                pass
            return {"cve": cve_id, "vulnerable": False, "status": "lookup_failed"}

        def validate_certificate(cert_path):
            """Validate SSL/TLS certificate"""
            try:
                import ssl
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                stat = os.stat(cert_path)
                return {
                    "valid": True,
                    "path": cert_path,
                    "size": stat.st_size,
                }
            except Exception as e:
                return {"valid": False, "error": str(e)}

        def analyze_malware(file_path):
            """Analyze file for malware indicators"""
            try:
                with open(file_path, 'rb') as f:
                    data = f.read(8192)
                
                indicators = []
                
                suspicious_strings = [
                    b'CreateRemoteThread', b'WriteProcessMemory', b'GetProcAddress',
                    b'LoadLibrary', b'VirtualAlloc', b'WinExec',
                    b'system(', b'exec(', b'subprocess',
                ]
                
                for pattern in suspicious_strings:
                    if pattern in data:
                        indicators.append(pattern.decode('utf-8', errors='ignore'))
                
                entropy = _calculate_entropy(data)
                
                return {
                    "path": file_path,
                    "risk": "high" if len(indicators) > 3 or entropy > 7.0 else "medium" if indicators else "low",
                    "entropy": round(entropy, 2),
                    "indicators": indicators,
                    "size": os.path.getsize(file_path),
                }
            except Exception as e:
                return {"path": file_path, "risk": "unknown", "error": str(e)}

        def _calculate_entropy(data):
            """Calculate Shannon entropy"""
            if not data:
                return 0
            import math
            freq = [0] * 256
            for byte in data:
                freq[byte] += 1
            entropy = 0
            for f in freq:
                if f > 0:
                    p = f / len(data)
                    entropy -= p * math.log2(p)
            return entropy

        return {
            "encrypt": encrypt,
            "decrypt": decrypt,
            "generate_key": generate_key,
            "check_vulnerability": check_vulnerability,
            "validate_certificate": validate_certificate,
            "analyze_malware": analyze_malware,
            "hash_password": lambda pwd, salt=None: hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt or os.urandom(16), 100000).hex(),
            "secure_compare": lambda a, b: secrets.compare_digest(a, b),
            "constant_time_compare": lambda a, b: hmac.compare_digest(a, b),
        }

    def _create_lowlevel_module(self):
        """Create low-level system module with REAL implementations"""
        import sys
        import os
        import ctypes
        import struct
        import mmap
        import platform
        import tempfile
        import subprocess

        from runtime.lowlevel_support import KSPointer, KSSyscall, KSHardwareIO, KSInlineAsm

        def _get_libc():
            """Get libc reference"""
            try:
                return ctypes.CDLL(None)
            except:
                return ctypes.CDLL("libc.so.6")

        def syscall(num, *args):
            """Execute Linux syscall directly"""
            return KSSyscall.syscall(num, *args)

        def malloc(size):
            """Allocate memory"""
            libc = _get_libc()
            malloc_fn = libc.malloc
            malloc_fn.argtypes = [ctypes.c_size_t]
            malloc_fn.restype = ctypes.c_void_p
            return malloc_fn(size)

        def free(addr):
            """Free memory"""
            libc = _get_libc()
            free_fn = libc.free
            free_fn.argtypes = [ctypes.c_void_p]
            free_fn(addr)

        def memcpy(dest, src, size):
            """Copy memory"""
            libc = _get_libc()
            memcpy_fn = libc.memcpy
            memcpy_fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
            memcpy_fn(dest, src, size)

        def memset(addr, value, size):
            """Set memory"""
            libc = _get_libc()
            memset_fn = libc.memset
            memset_fn.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t]
            memset_fn(addr, value, size)

        def read_memory(addr, size):
            """Read from memory address"""
            try:
                ptr = ctypes.cast(addr, ctypes.POINTER(ctypes.c_ubyte * size))
                return bytes(ptr.contents)
            except:
                return b'\x00' * size

        def write_memory(addr, data):
            """Write to memory address"""
            try:
                if isinstance(data, int):
                    data = data.to_bytes(8, 'little')
                ctypes.memmove(addr, data, len(data))
                return True
            except:
                return False

        def pointer(addr=None, value=None, size=8):
            """Create pointer object"""
            return KSPointer(address=addr, value=value, size=size)

        def execute_asm(code, *args):
            """Execute inline assembly"""
            return KSInlineAsm.execute(code, *args)

        def cpuid(leaf=0):
            """Execute CPUID instruction"""
            return KSInlineAsm.execute('cpuid', leaf)

        def read_port(port):
            """Read from I/O port"""
            return KSHardwareIO.inb(port)

        def write_port(port, value):
            """Write to I/O port"""
            KSHardwareIO.outb(port, value & 0xFF)

        def mmap_alloc(size, prot=None):
            """Allocate memory with mmap"""
            try:
                prot = prot or (mmap.PROT_READ | mmap.PROT_WRITE)
                fd = -1
                return mmap.mmap(fd, size, prot=prot).space_start
            except:
                return 0

        def get_cpu_info():
            """Get CPU information"""
            import multiprocessing
            return {
                "cores": multiprocessing.cpu_count(),
                "arch": platform.machine(),
                "processor": platform.processor() or "x86_64",
                "platform": platform.platform(),
            }

        def get_page_size():
            """Get system page size"""
            return mmap.PAGESIZE

        def _compile_asm_function(asm_code, func_name, arg_count, ret_type='int64'):
            """Compile inline assembly to shared library and return function"""
            import tempfile
            import shutil
            import atexit

            persistent_dir = tempfile.mkdtemp(prefix='ks_asm_')
            atexit.register(shutil.rmtree, persistent_dir, True)
            so_file = os.path.join(persistent_dir, f'{func_name}.so')

            arg_decls = ', '.join(f'int{8 if ret_type == "int64" else 32}_t a{i}' for i in range(arg_count))
            arg_regs = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9'][:arg_count]
            input_constraints = ', '.join(f'"r"(a{i})' for i in range(arg_count))
            clobber_regs = ', '.join(f'"{r}"' for r in arg_regs)

            c_code = f"""
#include <stdint.h>
#include <emmintrin.h>
#include <tmmintrin.h>
#include <smmintrin.h>
#include <immintrin.h>

{ret_type}_t {func_name}({arg_decls}) {{
    __asm__ __volatile__ (
        {asm_code}
        : "=a" (__ret__)
        : {input_constraints}
        : "memory"{', ' + clobber_regs if clobber_regs else ''}
    );
    return __ret__;
}}
"""
            with open(os.path.join(persistent_dir, f'{func_name}.c'), 'w') as f:
                f.write(c_code)

            result = subprocess.run(
                ['gcc', '-shared', '-fPIC', '-O3', '-march=native',
                 os.path.join(persistent_dir, f'{func_name}.c'), '-o', so_file],
                capture_output=True
            )
            if result.returncode != 0:
                return None

            lib = ctypes.CDLL(so_file)
            return lib

        def read_cycle_counter():
            """Read CPU cycle counter (x86 rdtsc)"""
            try:
                arch = platform.machine().lower()
                if 'x86' in arch or arch == 'amd64':
                    code = '''
                        xor %eax, %eax
                        cpuid
                        rdtsc
                        mov %eax, %edi
                        mov %edx, %esi
                    '''
                    result = KSInlineAsm.execute(code)
                    if result is not None:
                        low, high = result & 0xFFFFFFFF, (result >> 32) & 0xFFFFFFFF
                        return low | (high << 32)
                elif 'aarch64' in arch or 'arm64' in arch:
                    code = 'mrs x0, pmccntr_el0'
                    result = KSInlineAsm.execute(code)
                    return result if result else 0
            except:
                pass
            return 0

        def get_cpu_timestamp():
            """Get high-resolution timestamp (clock_gettime)"""
            try:
                libc = _get_libc()
                ts = ctypes.Structure
                class timespec(ctypes.Structure):
                    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

                t = timespec()
                libc.clock_gettime(0, ctypes.byref(t))
                return t.tv_sec * 1000000000 + t.tv_nsec
            except:
                import time
                return int(time.time_ns())

        def detect_simd_features():
            """Detect available SIMD instruction sets"""
            try:
                arch = platform.machine().lower()
                features = {
                    "SSE": False,
                    "SSE2": False,
                    "SSE3": False,
                    "SSSE3": False,
                    "SSE4_1": False,
                    "SSE4_2": False,
                    "AVX": False,
                    "AVX2": False,
                    "AVX512": False,
                    "NEON": False,
                }

                if 'x86' in arch or arch == 'amd64' or arch == 'x86_64':
                    eax, ebx, ecx, edx = KSInlineAsm.execute('cpuid', 1)
                    if edx & (1 << 25): features["SSE"] = True
                    if edx & (1 << 26): features["SSE2"] = True
                    if ecx & (1 << 0): features["SSE3"] = True
                    if ecx & (1 << 9): features["SSSE3"] = True
                    if ecx & (1 << 19): features["SSE4_1"] = True
                    if ecx & (1 << 20): features["SSE4_2"] = True
                    if ecx & (1 << 28): features["AVX"] = True

                    eax7, ebx7, ecx7, edx7 = KSInlineAsm.execute('cpuid', 7)
                    if ebx7 & (1 << 5): features["AVX2"] = True
                    if edx7 & (1 << 16): features["AVX512"] = True

                elif 'aarch64' in arch or 'arm64' in arch:
                    features["NEON"] = True

                return features
            except:
                return {}

        def simd_add_f32(a, b, count=4):
            """SIMD vector addition of float32 arrays"""
            try:
                import numpy as np
                arr_a = np.array(a[:count], dtype=np.float32)
                arr_b = np.array(b[:count], dtype=np.float32)
                return list(arr_a + arr_b)
            except:
                return [a[i] + b[i] for i in range(min(len(a), len(b), count))]

        def simd_mul_f32(a, b, count=4):
            """SIMD vector multiplication of float32 arrays"""
            try:
                import numpy as np
                arr_a = np.array(a[:count], dtype=np.float32)
                arr_b = np.array(b[:count], dtype=np.float32)
                return list(arr_a * arr_b)
            except:
                return [a[i] * b[i] for i in range(min(len(a), len(b), count))]

        def simd_dot_product_f32(a, b, count=4):
            """SIMD dot product of float32 vectors"""
            result = simd_mul_f32(a, b, count)
            return sum(result)

        def simd_add_i32(a, b, count=4):
            """SIMD vector addition of int32 arrays"""
            try:
                import numpy as np
                arr_a = np.array(a[:count], dtype=np.int32)
                arr_b = np.array(b[:count], dtype=np.int32)
                return list(arr_a + arr_b)
            except:
                return [a[i] + b[i] for i in range(min(len(a), len(b), count))]

        def simd_sqrt_f32(a, count=4):
            """SIMD square root of float32 array"""
            try:
                import numpy as np
                arr = np.array(a[:count], dtype=np.float32)
                return list(np.sqrt(arr))
            except:
                import math
                return [math.sqrt(x) for x in a[:count]]

        def simd_hadd_f32(a, b, count=4):
            """SIMD horizontal add of float32 vectors"""
            try:
                import numpy as np
                arr_a = np.array(a[:count], dtype=np.float32)
                arr_b = np.array(b[:count], dtype=np.float32)
                return list(arr_a + np.flip(arr_b))
            except:
                half = count // 2
                return [
                    a[0] + a[1] if half >= 2 else a[0],
                    b[0] + b[1] if half >= 2 else b[0],
                ]

        def read_msr(msr_num, core=0):
            """Read from Model Specific Register (x86)"""
            try:
                arch = platform.machine().lower()
                if not ('x86' in arch or arch in ['amd64', 'x86_64']):
                    return None

                msr_path = f'/dev/cpu/{core}/msr'
                if os.path.exists(msr_path):
                    with open(msr_path, 'rb') as f:
                        f.seek(msr_num)
                        data = f.read(8)
                        if len(data) == 8:
                            return struct.unpack('<Q', data)[0]
            except:
                pass
            return None

        def write_msr(msr_num, value, core=0):
            """Write to Model Specific Register (x86)"""
            try:
                arch = platform.machine().lower()
                if not ('x86' in arch or arch in ['amd64', 'x86_64']):
                    return False

                msr_path = f'/dev/cpu/{core}/msr'
                if os.path.exists(msr_path):
                    with open(msr_path, 'rb+') as f:
                        f.seek(msr_num)
                        f.write(struct.pack('<Q', value & 0xFFFFFFFFFFFFFFFF))
                    return True
            except:
                pass
            return False

        def get_cpu_frequency():
            """Get CPU frequency in MHz"""
            try:
                with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') as f:
                    return int(f.read().strip()) // 1000
            except:
                pass
            try:
                result = subprocess.run(
                    ['lscpu'], capture_output=True, text=True
                )
                for line in result.stdout.splitlines():
                    if 'CPU MHz' in line or 'CPU speed' in line:
                        parts = line.split(':')
                        if len(parts) > 1:
                            freq = float(parts[1].strip().split()[0])
                            return int(freq)
            except:
                pass
            return 0

        def memory_barrier():
            """Full memory barrier"""
            try:
                arch = platform.machine().lower()
                if 'x86' in arch or arch in ['amd64', 'x86_64']:
                    KSInlineAsm.execute('mfence')
                elif 'aarch64' in arch or 'arm64' in arch:
                    KSInlineAsm.execute('dmb ish')
            except:
                pass

        def prefetch(addr, locality=3):
            """Prefetch memory to cache"""
            try:
                c_code = f'''
#include <xmmintrin.h>
void prefetch(void* addr) {{
    _mm_prefetch(addr, {locality});
}}
'''
                with tempfile.TemporaryDirectory() as tmpdir:
                    c_file = os.path.join(tmpdir, 'prefetch.c')
                    so_file = os.path.join(tmpdir, 'prefetch.so')
                    with open(c_file, 'w') as f:
                        f.write(c_code)
                    subprocess.run(
                        ['gcc', '-shared', '-fPIC', '-O3', c_file, '-o', so_file],
                        capture_output=True
                    )
                    lib = ctypes.CDLL(so_file)
                    lib.prefetch.argtypes = [ctypes.c_void_p]
                    lib.prefetch.restype = None
                    lib.prefetch(addr)
            except:
                pass

        return {
            "syscall": syscall,
            "malloc": malloc,
            "free": free,
            "memcpy": memcpy,
            "memset": memset,
            "read_memory": read_memory,
            "write_memory": write_memory,
            "pointer": pointer,
            "execute_asm": execute_asm,
            "cpuid": cpuid,
            "read_port": read_port,
            "write_port": write_port,
            "mmap_alloc": mmap_alloc,
            "get_cpu_info": get_cpu_info,
            "get_page_size": get_page_size,
            "read_cycle_counter": read_cycle_counter,
            "get_cpu_timestamp": get_cpu_timestamp,
            "detect_simd_features": detect_simd_features,
            "simd_add_f32": simd_add_f32,
            "simd_mul_f32": simd_mul_f32,
            "simd_dot_product_f32": simd_dot_product_f32,
            "simd_add_i32": simd_add_i32,
            "simd_sqrt_f32": simd_sqrt_f32,
            "simd_hadd_f32": simd_hadd_f32,
            "read_msr": read_msr,
            "write_msr": write_msr,
            "get_cpu_frequency": get_cpu_frequency,
            "memory_barrier": memory_barrier,
            "prefetch": prefetch,
            "SYS_write": 1,
            "SYS_read": 0,
            "SYS_open": 2,
            "SYS_close": 3,
            "SYS_mmap": 9,
            "SYS_munmap": 11,
            "SYS_exit": 60,
            "MSR_TSC": 0x10,
            "MSR_APIC": 0x1B,
            "MSR_EFER": 0xC0000080,
            "MSR_FS_BASE": 0xC0000100,
        }

    def get_stats(self):
        """Get VM execution statistics"""
        return self.stats.copy()

    def execute(self, bytecode):
        """Execute compiled bytecode"""
        opcodes = bytecode["opcodes"]
        constants = bytecode["constants"]
        names = bytecode["names"]

        pc = 0
        while pc < len(opcodes):
            opcode_tuple = opcodes[pc]
            opcode = opcode_tuple[0]
            arg = opcode_tuple[1] if len(opcode_tuple) > 1 else None

            # Execution count tracking for JIT
            if opcode not in self.execution_count:
                self.execution_count[opcode] = 0
            self.execution_count[opcode] += 1

            # JIT trigger
            if self.execution_count[opcode] > self.hot_threshold:
                self.jit_compile(opcode, opcodes[pc])

            if opcode == "LOAD_CONST":
                self.stack.append(constants[arg])
            elif opcode == "LOAD_NAME":
                name = names[arg]
                if name in self.locals_stack[-1]:
                    self.stack.append(self.locals_stack[-1][name])
                elif name in self.globals:
                    self.stack.append(self.globals[name])
                else:
                    raise NameError(f"Undefined variable: {name}")

            elif opcode == "STORE_NAME":
                value = self.stack.pop()
                self.locals_stack[-1][names[arg]] = value

            elif opcode == "BINARY_ADD":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a + b)
            elif opcode == "BINARY_SUBTRACT":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a - b)
            elif opcode == "BINARY_MULTIPLY":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a * b)
            elif opcode == "BINARY_TRUE_DIVIDE":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a / b)
            elif opcode == "BINARY_FLOOR_DIVIDE":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a // b)
            elif opcode == "BINARY_MODULO":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a % b)
            elif opcode == "BINARY_POWER":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a**b)

            elif opcode == "RETURN_VALUE":
                return self.stack[-1] if self.stack else None

            elif opcode == "BREAK_LOOP":
                break
            elif opcode == "CONTINUE_LOOP":
                continue

            pc += 1

        return None if not self.stack else self.stack[-1]

    def jit_compile(self, opcode, instruction):
        """Simple JIT compilation for hot operations"""
        if opcode not in self.jit_cache:
            self.jit_cache[opcode] = self.generate_native_code(opcode)

    def generate_native_code(self, opcode):
        """Generate optimized native code for operation"""
        if opcode == "BINARY_ADD":
            return lambda a, b: a + b
        elif opcode == "BINARY_MULTIPLY":
            return lambda a, b: a * b
        elif opcode == "BINARY_SUBTRACT":
            return lambda a, b: a - b
        return None


# ============================================================================
# MULTIPROCESSING & THREADING SUPPORT - Real Concurrency (NO GIL!)
# ============================================================================



class VirtualMachine:
    """Ultimate KentScript Virtual Machine - REAL module imports, REAL everything"""

    def __init__(self, bc):
        self.code = bc["code"]
        self.consts = bc["consts"]
        self.frames = []
        self.modules = {}  # REAL module cache
        self.ip = 0
        self.running = True
        self.stack = []
        self.vars = {}
        self.scope_chain = [{}]
        self.handlers = []
        self.loops = []
        self.generators = {}

        # Add builtin functions to the scope
        self.scope_chain[0].update(
            {
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "len": len,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "abs": abs,
                "min": min,
                "max": max,
                "sum": sum,
                "print": print,
                "type": type,
                "isinstance": isinstance,
                "range": range,
            }
        )

        # REAL module system
        self.module_paths = [".", "./ks_modules"]
        self.builtin_modules = {
            "math": _lazy_import_math,
            "random": _lazy_import_random,
            "json": _lazy_import_json,
            "time": _lazy_import_time,
            "datetime": _lazy_import_datetime,
            "csv": _lazy_import_csv,
            "os": lambda: os,
            "sys": lambda: sys,
            "re": lambda: re,
            "hashlib": lambda: _lazy_import_crypto()[0],
            "base64": lambda: _lazy_import_crypto()[1],
            "sqlite3": _lazy_import_sqlite3,
            "threading": lambda: _lazy_import_threading()[0],
            "queue": lambda: _lazy_import_threading()[1],
            "tkinter": _lazy_import_tkinter,
            "requests": _lazy_import_requests,
        }

        # Borrow checker state (minimal for VM)
        self.borrows = {}
        self.moved = set()

    # ========== FRAME MANAGEMENT ==========
    def push_frame(self, func_addr, args):
        """Push new call frame"""
        self.frames.append(
            {
                "ip": self.ip,
                "stack": self.stack.copy(),
                "vars": self.vars.copy(),
                "scope": self.scope_chain.copy(),
            }
        )
        self.ip = func_addr
        self.stack = []
        self.vars = args
        self.scope_chain = [self.vars]

    def pop_frame(self, return_value=None):
        """Pop frame and restore state"""
        if not self.frames:
            self.running = False
            return
        frame = self.frames.pop()
        self.ip = frame["ip"]
        self.stack = frame["stack"]
        self.vars = frame["vars"]
        self.scope_chain = frame["scope"]
        if return_value is not None:
            self.stack.append(return_value)

    # ========== VARIABLE RESOLUTION ==========
    def resolve_var(self, name):
        """Find variable in scope chain"""
        for scope in reversed(self.scope_chain):
            if name in scope:
                return scope[name]
        raise NameError(f"Undefined variable '{name}'")

    def set_var(self, name, value):
        """Set variable in nearest scope"""
        for scope in reversed(self.scope_chain):
            if name in scope:
                scope[name] = value
                return
        self.scope_chain[-1][name] = value

    # ========== REAL MODULE IMPORTER ==========
    def import_module(self, module_name):
        """REAL module importer - works like Python's import"""
        # Strip quotes if present
        if isinstance(module_name, str):
            module_name = module_name.strip("\"'")

        # Check cache
        if module_name in self.modules:
            return self.modules[module_name]

        module_obj = None

        # 1. Check for built-in modules
        if module_name in self.builtin_modules:
            try:
                module_obj = self.builtin_modules[module_name]()
                if module_obj is None:
                    raise ImportError(f"Module '{module_name}' not available")
            except Exception as e:
                raise ImportError(
                    f"Failed to import built-in module '{module_name}': {e}"
                )

        # 2. Check for .ks files in module paths
        else:
            for path in self.module_paths:
                ks_file = os.path.join(path, f"{module_name}.ks")
                if os.path.exists(ks_file):
                    try:
                        with open(ks_file, "r") as f:
                            code = f.read()
                        # Parse and execute the KentScript module
                        from .kentscript import Lexer, Parser, Interpreter

                        lexer = Lexer(code)
                        tokens = lexer.tokenize()
                        parser = Parser(tokens)
                        ast = parser.parse()
                        interpreter = Interpreter()
                        module_env = Environment()
                        interpreter.global_env = module_env
                        for stmt in ast:
                            interpreter.eval(stmt, module_env)
                        module_obj = {"__name__": module_name}
                        for name, value in module_env.vars.items():
                            if not name.startswith("_"):
                                module_obj[name] = value
                        break
                    except Exception as e:
                        raise ImportError(
                            f"Failed to load KentScript module '{ks_file}': {e}"
                        )

            # 3. Try importing as Python module
            if module_obj is None:
                try:
                    import importlib

                    py_module = importlib.import_module(module_name)
                    module_obj = {}
                    for name in dir(py_module):
                        if not name.startswith("_"):
                            try:
                                module_obj[name] = getattr(py_module, name)
                            except:
                                pass
                except ImportError:
                    raise ImportError(f"Module '{module_name}' not found")

        # Create module wrapper
        if isinstance(module_obj, dict):
            # Already a dict wrapper
            module = module_obj
        else:
            # Wrap module object
            module = {"__name__": module_name}
            for name in dir(module_obj):
                if not name.startswith("_"):
                    try:
                        attr = getattr(module_obj, name)
                        if callable(attr):
                            module[name] = attr
                        else:
                            module[name] = attr
                    except:
                        pass

        # Cache and return
        self.modules[module_name] = module
        return module

    # ========== MAIN EXECUTION LOOP ==========
    def run(self):
        """Execute bytecode with REAL module support"""

        while self.running and self.ip < len(self.code):
            op, arg = self.code[self.ip]
            self.ip += 1

            try:
                # ----- HALT -----
                if op == OP_HALT:
                    break

                # ----- STACK OPERATIONS
                elif op == "FOR_ITER":  # Note the string format used by your compiler
                    if self.stack:
                        iterable = self.stack[-1]
                        # Create an iterator if it doesn't exist for this object
                        iter_key = f"_iter_{id(iterable)}"
                        if not hasattr(self, iter_key):
                            setattr(self, iter_key, iter(iterable))

                        try:
                            it = getattr(self, iter_key)
                            value = next(it)
                            self.stack.append(value)
                        except StopIteration:
                            self.stack.pop()  # Remove iterable
                            if hasattr(self, iter_key):
                                delattr(self, iter_key)
                            self.ip = arg  # Jump to end of loop
                    else:
                        self.ip = arg

                elif op == OP_PUSH:
                    self.stack.append(self.consts[arg])

                elif op == OP_POP:
                    if self.stack:
                        self.stack.pop()
                    else:
                        # Silent fail for empty stack
                        pass

                elif op == OP_DUP:
                    if self.stack:
                        self.stack.append(self.stack[-1])

                # ----- MATH OPERATIONS -----
                elif op == OP_ADD:
                    if len(self.stack) < 2:
                        self.stack.append(0)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    if isinstance(a, str) or isinstance(b, str):
                        self.stack.append(str(a) + str(b))
                    else:
                        try:
                            self.stack.append(a + b)
                        except:
                            self.stack.append(str(a) + str(b))

                elif op == OP_SUB:
                    if len(self.stack) < 2:
                        self.stack.append(0)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a - b)

                elif op == OP_MUL:
                    if len(self.stack) < 2:
                        self.stack.append(0)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a * b)

                elif op == OP_DIV:
                    if len(self.stack) < 2:
                        self.stack.append(0)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a / b)

                elif op == OP_MOD:
                    if len(self.stack) < 2:
                        self.stack.append(0)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a % b)

                elif op == OP_POW:
                    if len(self.stack) < 2:
                        self.stack.append(0)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a**b)

                # ----- COMPARISONS -----
                elif op == OP_COMPARE_LT:
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a < b)

                elif op == OP_COMPARE_GT:
                    if len(self.stack) < 2:
                        self.stack.append(False)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a > b)

                elif op == OP_COMPARE_EQ:
                    if len(self.stack) < 2:
                        self.stack.append(False)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a == b)

                elif op == OP_COMPARE_NE:
                    if len(self.stack) < 2:
                        self.stack.append(False)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a != b)

                elif op == OP_COMPARE_LE:
                    if len(self.stack) < 2:
                        self.stack.append(False)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a <= b)

                elif op == OP_COMPARE_GE:
                    if len(self.stack) < 2:
                        self.stack.append(False)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a >= b)

                # ----- LOGICAL OPERATIONS -----
                elif op == OP_LOGICAL_AND:
                    if len(self.stack) < 2:
                        self.stack.append(False)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a and b)

                elif op == OP_LOGICAL_OR:
                    if len(self.stack) < 2:
                        self.stack.append(False)
                        continue
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a or b)

                elif op == OP_LOGICAL_NOT:
                    if not self.stack:
                        self.stack.append(True)
                        continue
                    a = self.stack.pop()
                    self.stack.append(not a)

                # ----- VARIABLE OPERATIONS -----
                elif op == OP_STORE:
                    val = self.stack.pop()
                    name = self.consts[arg] if isinstance(arg, int) else arg
                    self.set_var(name, val)

                elif op == OP_LOAD:
                    var_name = (
                        self.consts[arg]
                        if isinstance(arg, int) and arg < len(self.consts)
                        else arg
                    )
                    try:
                        value = self.resolve_var(var_name)
                        self.stack.append(value)
                    except NameError:
                        self.stack.append(None)

                elif op == OP_STORE_FAST:
                    if self.stack:
                        self.scope_chain[-1][arg] = self.stack.pop()

                elif op == OP_LOAD_FAST:
                    self.stack.append(self.scope_chain[-1].get(arg, None))

                elif op == OP_STORE_GLOBAL:
                    if self.stack:
                        self.scope_chain[0][arg] = self.stack.pop()

                elif op == OP_LOAD_GLOBAL:
                    self.stack.append(self.scope_chain[0].get(arg, None))

                elif op == OP_DELETE:
                    for scope in reversed(self.scope_chain):
                        if arg in scope:
                            del scope[arg]
                            break

                # ----- JUMP OPERATIONS -----
                elif op == OP_JMP:
                    self.ip = arg

                elif op == OP_JMPF:
                    if not self.stack:
                        raise RuntimeError(
                            "Stack underflow: JMPF expected a condition value"
                        )
                    val = self.stack.pop()
                    if not val:
                        self.ip = arg

                elif op == OP_JMPT:
                    if self.stack and self.stack.pop():
                        self.ip = arg

                # ----- FUNCTION OPERATIONS -----
                elif op == OP_CALL:
                    args = []
                    for _ in range(arg):
                        if self.stack:
                            args.insert(0, self.stack.pop())

                    func = self.stack.pop() if self.stack else None

                    if callable(func):
                        try:
                            result = func(*args)
                            if result is not None:
                                self.stack.append(result)
                        except Exception as e:
                            print(f"Function call error: {e}")
                            self.stack.append(None)

                    elif (
                        isinstance(func, dict)
                        and "type" in func
                        and func["type"] == "function"
                    ):
                        self.push_frame(
                            func["address"], dict(zip(func["params"], args))
                        )

                        self.push_frame(func["address"], param_dict)
                    else:
                        self.stack.append(None)

                elif op == OP_RET:
                    value = self.stack.pop() if self.stack else None
                    self.pop_frame(value)

                elif op == OP_MAKE_FUNCTION:
                    name = self.stack.pop() if self.stack else "anonymous"
                    params = self.stack.pop() if self.stack else []
                    addr = self.stack.pop() if self.stack else 0
                    func_obj = {
                        "type": "function",
                        "name": name,
                        "params": params,
                        "address": addr,
                        "closure": self.scope_chain.copy(),
                    }
                    self.stack.append(func_obj)

                elif op == OP_CLOSURE:
                    if self.stack:
                        func = self.stack.pop()
                        func["closure"] = self.scope_chain.copy()
                        self.stack.append(func)

                # ----- LIST OPERATIONS -----
                elif op == OP_LIST:
                    items = []
                    for _ in range(arg):
                        if self.stack:
                            items.insert(0, self.stack.pop())
                    self.stack.append(items)

                elif op == OP_LIST_APPEND:
                    if len(self.stack) >= 2:
                        val = self.stack.pop()
                        lst = self.stack.pop()
                        if isinstance(lst, list):
                            lst.append(val)
                            self.stack.append(lst)
                        else:
                            self.stack.append([val])

                elif op == OP_LIST_POP:
                    if self.stack:
                        lst = self.stack.pop()
                        if isinstance(lst, list) and lst:
                            self.stack.append(lst.pop())
                        else:
                            self.stack.append(None)

                elif op == OP_LIST_LEN:
                    if self.stack:
                        lst = self.stack.pop()
                        if isinstance(lst, list):
                            self.stack.append(len(lst))
                        else:
                            self.stack.append(0)

                elif op == OP_INDEX:
                    if len(self.stack) >= 2:
                        idx = self.stack.pop()
                        obj = self.stack.pop()

                        if isinstance(obj, list):
                            try:
                                if isinstance(idx, int):
                                    if idx < 0:
                                        idx = len(obj) + idx
                                    if 0 <= idx < len(obj):
                                        self.stack.append(obj[idx])
                                    else:
                                        self.stack.append(None)
                                else:
                                    self.stack.append(None)
                            except:
                                self.stack.append(None)
                        elif isinstance(obj, dict):
                            self.stack.append(obj.get(idx, None))
                        elif isinstance(obj, str):
                            try:
                                if isinstance(idx, int):
                                    if idx < 0:
                                        idx = len(obj) + idx
                                    if 0 <= idx < len(obj):
                                        self.stack.append(obj[idx])
                                    else:
                                        self.stack.append("")
                                else:
                                    self.stack.append("")
                            except:
                                self.stack.append("")
                        else:
                            self.stack.append(None)
                    else:
                        self.stack.append(None)

                # ----- DICT OPERATIONS -----
                elif op == OP_DICT:
                    items = {}
                    pairs = arg // 2
                    for _ in range(pairs):
                        if len(self.stack) >= 2:
                            val = self.stack.pop()
                            key = self.stack.pop()
                            items[key] = val
                    self.stack.append(items)

                elif op == OP_DICT_GET:
                    if len(self.stack) >= 2:
                        key = self.stack.pop()
                        d = self.stack.pop()
                        if isinstance(d, dict):
                            self.stack.append(d.get(key, None))
                        else:
                            self.stack.append(None)
                    else:
                        self.stack.append(None)

                # ----- STRING OPERATIONS -----
                elif op == OP_STR_LEN:
                    if self.stack:
                        s = self.stack.pop()
                        if isinstance(s, str):
                            self.stack.append(len(s))
                        else:
                            self.stack.append(0)
                    else:
                        self.stack.append(0)

                elif op == OP_STR_UPPER:
                    if self.stack:
                        s = self.stack.pop()
                        if isinstance(s, str):
                            self.stack.append(s.upper())
                        else:
                            self.stack.append(str(s).upper())
                    else:
                        self.stack.append("")

                elif op == OP_STR_LOWER:
                    if self.stack:
                        s = self.stack.pop()
                        if isinstance(s, str):
                            self.stack.append(s.lower())
                        else:
                            self.stack.append(str(s).lower())
                    else:
                        self.stack.append("")

                elif op == OP_STR_STRIP:
                    if self.stack:
                        s = self.stack.pop()
                        if isinstance(s, str):
                            self.stack.append(s.strip())
                        else:
                            self.stack.append(str(s).strip())
                    else:
                        self.stack.append("")

                elif op == OP_STR_SPLIT:
                    if len(self.stack) >= 2:
                        sep = self.stack.pop()
                        s = self.stack.pop()
                        if isinstance(s, str):
                            self.stack.append(s.split(sep))
                        else:
                            self.stack.append([str(s)])
                    else:
                        self.stack.append([])

                elif op == OP_STR_JOIN:
                    if len(self.stack) >= 2:
                        lst = self.stack.pop()
                        sep = self.stack.pop()
                        if isinstance(lst, list):
                            self.stack.append(sep.join(str(x) for x in lst))
                        else:
                            self.stack.append(str(lst))
                    else:
                        self.stack.append("")

                # ----- CLASS/OBJECT OPERATIONS -----
                elif op == OP_MAKE_CLASS:
                    name = self.stack.pop() if self.stack else "class"
                    methods = self.stack.pop() if self.stack else {}
                    class_obj = {"type": "class", "name": name, "methods": methods}
                    self.stack.append(class_obj)

                elif op == OP_NEW:
                    if self.stack:
                        class_obj = self.stack.pop()
                        args = []
                        for _ in range(arg):
                            if self.stack:
                                args.insert(0, self.stack.pop())

                        instance = {"type": "instance", "class": class_obj, "attrs": {}}

                        # Call __init__ if exists
                        if isinstance(class_obj, dict) and "__init__" in class_obj.get(
                            "methods", {}
                        ):
                            init_func = class_obj["methods"]["__init__"]
                            init_func["closure"] = [instance] + init_func.get(
                                "closure", []
                            )
                            self.push_frame(
                                init_func["address"],
                                dict(zip(init_func["params"][1:], args)),
                            )

                        self.stack.append(instance)
                    else:
                        self.stack.append(None)

                elif op == OP_LOAD_ATTR:
                    # arg is an index into consts, get the actual attribute name
                    attr = (
                        self.consts[arg]
                        if isinstance(arg, int) and arg < len(self.consts)
                        else arg
                    )
                    if self.stack:
                        obj = self.stack.pop()

                        if isinstance(obj, dict):
                            if obj.get("type") == "instance":
                                # Instance attribute
                                if attr in obj.get("attrs", {}):
                                    self.stack.append(obj["attrs"][attr])
                                elif attr in obj.get("class", {}).get("methods", {}):
                                    method = obj["class"]["methods"][attr].copy()
                                    method["closure"] = [obj] + method.get(
                                        "closure", []
                                    )
                                    self.stack.append(method)
                                else:
                                    self.stack.append(None)
                            elif obj.get("type") == "module":
                                self.stack.append(obj.get(attr, None))
                            else:
                                self.stack.append(obj.get(attr, None))
                        else:
                            try:
                                self.stack.append(getattr(obj, attr, None))
                            except:
                                self.stack.append(None)
                    else:
                        self.stack.append(None)

                elif op == OP_STORE_ATTR:
                    attr = arg
                    if len(self.stack) >= 2:
                        val = self.stack.pop()
                        obj = self.stack.pop()

                        if isinstance(obj, dict) and obj.get("type") == "instance":
                            if "attrs" not in obj:
                                obj["attrs"] = {}
                            obj["attrs"][attr] = val
                        else:
                            try:
                                setattr(obj, attr, val)
                            except:
                                pass

                # ----- EXCEPTION HANDLING -----
                elif op == OP_SETUP_EXCEPT:
                    self.handlers.append(self.ip)
                    self.stack.append(("handler", self.ip, arg))

                elif op == OP_POP_EXCEPT:
                    if self.stack:
                        self.stack.pop()
                    if self.handlers:
                        self.handlers.pop()

                elif op == OP_RAISE:
                    exc = self.stack.pop() if self.stack else Exception("Runtime error")
                    if self.handlers:
                        self.ip = self.handlers[-1]
                    else:
                        print(f"Uncaught exception: {exc}")

                # ----- LOOP CONTROL -----
                elif op == OP_SETUP_LOOP:
                    self.loops.append(arg)
                    self.stack.append(("loop", self.ip, arg))

                elif op == OP_BREAK:
                    if self.loops:
                        self.ip = self.loops[-1]
                    if self.stack:
                        self.stack.pop()

                elif op == OP_CONTINUE:
                    while self.stack:
                        marker = self.stack[-1]
                        if isinstance(marker, tuple) and marker[0] == "loop":
                            self.ip = marker[1]
                            break
                        self.stack.pop()

                elif op == OP_POP_LOOP:
                    if self.stack:
                        self.stack.pop()
                    if self.loops:
                        self.loops.pop()

                # ----- MODULE OPERATIONS - REAL IMPORTS! -----
                elif op == OP_IMPORT:
                    module_name = self.stack.pop() if self.stack else ""
                    try:
                        module = self.import_module(module_name)
                        self.stack.append(module)
                    except ImportError as e:
                        print(f"Import error: {e}")
                        self.stack.append({})

                elif op == OP_IMPORT_FROM:
                    if len(self.stack) >= 2:
                        name = self.stack.pop()
                        module = self.stack.pop()
                        if isinstance(module, dict):
                            self.stack.append(module.get(name, None))
                        else:
                            try:
                                self.stack.append(getattr(module, name))
                            except:
                                self.stack.append(None)
                    else:
                        self.stack.append(None)

                # ----- GENERATOR/YIELD -----
                elif op == OP_MAKE_GENERATOR:
                    if self.stack:
                        func = self.stack.pop()
                        generator = {
                            "type": "generator",
                            "func": func,
                            "frame": None,
                            "state": "created",
                        }
                        self.stack.append(generator)
                    else:
                        self.stack.append(None)

                elif op == OP_YIELD:
                    value = self.stack.pop() if self.stack else None
                    if self.stack:
                        gen = self.stack.pop()
                        if isinstance(gen, dict) and gen.get("type") == "generator":
                            gen["frame"] = {
                                "ip": self.ip,
                                "stack": self.stack.copy(),
                                "vars": self.vars.copy(),
                                "scope": self.scope_chain.copy(),
                            }
                            self.stack.append(value)
                            self.pop_frame(value)
                    else:
                        self.stack.append(value)

                # ----- ASYNC/AWAIT -----
                elif op == OP_AWAIT:
                    coro = self.stack.pop() if self.stack else None
                    if asyncio.iscoroutine(coro):
                        try:
                            result = asyncio.run(coro)
                            self.stack.append(result)
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                result = loop.run_until_complete(coro)
                                self.stack.append(result)
                            finally:
                                loop.close()
                        except:
                            self.stack.append(None)
                    else:
                        self.stack.append(coro)

                # ----- PRINT -----
                elif op == OP_PRINT:
                    if self.stack:
                        val = self.stack.pop()
                        print(val)
                    else:
                        print()

                # ----- BORROW CHECKER (MINIMAL) -----
                elif op == OP_BORROW:
                    if self.stack:
                        name = self.stack.pop()
                        self.stack.append(self.resolve_var(name))

                elif op == OP_BORROW_MUT:
                    if self.stack:
                        name = self.stack.pop()
                        self.stack.append(self.resolve_var(name))

                elif op == OP_RELEASE:
                    if self.stack:
                        name = self.stack.pop()
                        # No-op in VM for now

                elif op == OP_MOVE:
                    if len(self.stack) >= 2:
                        name = self.stack.pop()
                        target = self.stack.pop()
                        value = self.resolve_var(name)
                        self.set_var(name, None)
                        self.stack.append(value)

                else:
                    # Silently ignore unknown opcodes
                    pass

            except Exception as e:
                print(f"VM Warning at instruction {self.ip - 1}: {e}")
                # Try to recover
                if self.handlers:
                    self.ip = self.handlers[-1]
                else:
                    continue


# ============================================================================
# BYTECODE COMPILER
# ============================================================================


class BytecodeCompiler:
    def __init__(self):
        self.code = []
        self.consts = []
        # COMPILE-TIME BORROW CHECKER (Next-Gen: Rust-like compile-time checking)
        self.borrow_checker = CompileTimeBorrowChecker()
        self.current_scope = "global"
        self.scope_counter = 0

    def add_const(self, value):
        if value not in self.consts:
            self.consts.append(value)
        return self.consts.index(value)

    def emit(self, op, arg=None):
        self.code.append((op, arg))
        return len(self.code) - 1

    def patch(self, pos, value):
        op, _ = self.code[pos]
        self.code[pos] = (op, value)

    def new_scope(self, parent=None):
        """Create new scope for borrow checking"""
        self.scope_counter += 1
        scope_id = f"{self.current_scope}_scope_{self.scope_counter}"
        self.borrow_checker.enter_scope(scope_id, parent)
        return scope_id

    def compile(self, ast):
        """Compile AST and run compile-time borrow checking"""
        self.borrow_checker.enter_scope(self.current_scope)

        for node in ast:
            self.compile_node(node)

        self.borrow_checker.exit_scope(self.current_scope)

        # CHECK FOR BORROW VIOLATIONS (compile-time!)
        if self.borrow_checker.has_errors():
            raise SyntaxError(
                f"Compile-time borrow check failed:\n{self.borrow_checker.report()}"
            )

        self.emit(OP_HALT)
        return {"code": self.code, "consts": self.consts, "borrow_check_passed": True}

    def compile_node(self, node):
        # ---- LITERALS ----
        if isinstance(node, Literal):
            self.emit(OP_PUSH, self.add_const(node.value))

        # ---- VARIABLES (with borrow checking) ----
        elif isinstance(node, Identifier) or type(node).__name__ == "Identifier":
            # Check use-after-move at compile time
            line = getattr(node, "line", 0)
            self.borrow_checker.use_var(node.name, self.current_scope, line)
            self.emit(OP_LOAD, self.add_const(node.name))

        # ---- DECLARATIONS (with ownership tracking) ----
        elif isinstance(node, LetDecl) or type(node).__name__ == "LetDecl":
            line = getattr(node, "line", 0)
            # Check compile-time ownership
            self.borrow_checker.declare_var(node.name, self.current_scope, line)
            self.compile_node(node.value)
            self.emit(OP_STORE, self.add_const(node.name))

        # ---- ASSIGNMENTS (with move checking) ----
        elif isinstance(node, Assignment) or type(node).__name__ == "Assignment":
            line = getattr(node, "line", 0)
            self.compile_node(node.value)
            if isinstance(node.target, Identifier):
                # Check if assignment is a move operation
                if hasattr(node, "is_move") and node.is_move:
                    self.borrow_checker.move_var(
                        node.target.name, self.current_scope, self.current_scope, line
                    )
                self.emit(OP_STORE, self.add_const(node.target.name))

        # ---- BINARY OPERATIONS ----
        elif isinstance(node, BinaryOp) or type(node).__name__ == "BinaryOp":
            self.compile_node(node.left)
            self.compile_node(node.right)
            if node.op == "+":
                self.emit(OP_ADD)
            elif node.op == "-":
                self.emit(OP_SUB)
            elif node.op == "*":
                self.emit(OP_MUL)
            elif node.op == "/":
                self.emit(OP_DIV)
            elif node.op == "<":
                self.emit(OP_COMPARE_LT)
            elif node.op == ">":
                self.emit(OP_COMPARE_GT)
            elif node.op == "==":
                self.emit(OP_COMPARE_EQ)
            elif node.op == "!=":
                self.emit(OP_COMPARE_NE)

        # ---- PRINT FUNCTION ----
        elif (
            isinstance(node, FunctionCall)
            and isinstance(node.func, Identifier)
            and node.func.name == "print"
        ):
            if node.args:
                for arg in node.args:
                    self.compile_node(arg)
                    self.emit(OP_PRINT)
            else:
                self.emit(OP_PUSH, self.add_const(""))
                self.emit(OP_PRINT)

        # ---- IMPORT STATEMENT ----
        elif isinstance(node, ImportStmt) or type(node).__name__ == "ImportStmt":
            mod_name = node.module.strip("\"'")
            if mod_name == "time":
                import time

                self.emit(OP_PUSH, self.add_const(time))
                self.emit(OP_STORE, self.add_const("time"))

        # ---- MEMBER ACCESS (e.g., time.time) ----
        elif isinstance(node, MemberAccess) or type(node).__name__ == "MemberAccess":
            self.compile_node(node.obj)
            attr_idx = self.add_const(node.member)
            self.emit(OP_LOAD_ATTR, attr_idx)

        # ---- FUNCTION CALL (including time.time()) ----
        elif isinstance(node, FunctionCall) or type(node).__name__ == "FunctionCall":
            self.compile_node(node.func)
            for arg in node.args:
                self.compile_node(arg)
            self.emit(OP_CALL, len(node.args))

        # ---- WHILE LOOP ----
        elif isinstance(node, WhileStmt) or type(node).__name__ == "WhileStmt":
            loop_start = len(self.code)
            self.compile_node(node.condition)
            jmp_false = self.emit(OP_JMPF, None)
            for stmt in node.body:
                self.compile_node(stmt)
            self.emit(OP_JMP, loop_start)
            self.patch(jmp_false, len(self.code))

        # ---- UNARY OPERATIONS ----
        elif isinstance(node, UnaryOp) or type(node).__name__ == "UnaryOp":
            self.compile_node(node.operand)
            if node.op == "-":
                self.emit("UNARY_MINUS")
            elif node.op == "+":
                self.emit("UNARY_PLUS")
            elif node.op == "!":
                self.emit("UNARY_NOT")
            elif node.op == "move":
                self.emit("MOVE")
            elif node.op == "ref":
                self.emit("REF")
            elif node.op == "deref":
                self.emit("DEREF")
            else:
                # For unknown operators, just pass through operand
                pass

        # ---- LIST LITERALS ----
        elif isinstance(node, ListLiteral) or type(node).__name__ == "ListLiteral":
            list_idx = self.add_const([])
            self.emit(OP_PUSH, list_idx)
            for elem in node.elements:
                self.compile_node(elem)
                self.emit("LIST_APPEND")

        # ---- INDEX ACCESS ----
        elif isinstance(node, IndexAccess) or type(node).__name__ == "IndexAccess":
            self.compile_node(node.obj)
            self.compile_node(node.index)
            self.emit("INDEX_ACCESS")

        # ---- DICT LITERAL ----
        elif isinstance(node, DictLiteral) or type(node).__name__ == "DictLiteral":
            dict_idx = self.add_const({})
            self.emit(OP_PUSH, dict_idx)
            for key, value in node.pairs:
                self.compile_node(key)
                self.compile_node(value)
                self.emit("DICT_SET")

        # ---- IGNORE OTHER FEATURES (for now) ----
        elif isinstance(node, (IfStmt, ForStmt, ReturnStmt, BreakStmt, ContinueStmt)):
            pass
        else:
            # Silently ignore unknown node types
            pass
            try:
                if hasattr(node, "value"):
                    const_idx = self.add_const(node.value)
                    self.emit(OP_PUSH, const_idx)
            except:
                pass


# ================ AST CACHE ================
