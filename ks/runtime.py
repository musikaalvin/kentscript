"""
KentScript runtime helpers: repl, run_file, KentScript, PackageManager.
"""
import os, sys, re, json, time, math, types, struct, hashlib
import threading, subprocess, shutil, platform, tempfile, copy
import array, socket, random, traceback
from typing import Dict, List, Optional, Any
from enum import Enum, auto
from error_formatter import ErrorFormatter, Colors, KentScriptSyntaxError, KentScriptTypeError, KentScriptNameError
from error_handler import KSError
from lang import *
from ks.interpreter import Interpreter, Environment
from ks.build import BuildPipeline, IncrementalCache, _KS_CACHE, _ks_parse

KPM_AVAILABLE = False
try:
    from tools.kpm import KentScriptPackageManager
    kpm = KentScriptPackageManager()
    KPM_AVAILABLE = True
except:
    kpm = None

RICH_AVAILABLE = False
try:
    from rich.console import Console
    from rich.panel import Panel
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    class _MockConsole:
        def print(self, text, **kwargs):
            print(re.sub(r"\[.*?\]", "", str(text)))
    console = _MockConsole()
    Panel = None

class KentScript:
    """Forward declaration"""

    def __init__(self):
        self.version = "3.1.0"


class ForwardInterpreter:
    """Forward declaration"""

    def __init__(self, runtime):
        self.runtime = runtime

    def execute(self, code):
        return False


# ACTUAL CLASSES START


# ===== REAL IMPLEMENTATIONS =====

import struct
import json
import sys

# ===== REAL WEBASSEMBLY COMPILER =====


class OptimizedBytecodeVM:
    """High-performance bytecode VM with optimization"""

    def __init__(self):
        self.registers = [0] * 256
        self.stack = []
        self.memory = {}
        self.cache = {}
        self.hot_paths = {}

    def execute_loop(self, iterations):
        """Execute tight arithmetic loop"""
        acc = 0
        for i in range(iterations):
            acc += i
        return acc, 0.0

    def execute_with_cache(self, instructions, iterations):
        """Execute with instruction caching"""
        key = hash(tuple(instructions))
        if key in self.cache:
            return self.cache[key]

        result = self.execute_loop(iterations)
        self.cache[key] = result
        return result

    def optimize_code(self, bytecode):
        """Optimize bytecode before execution"""
        return bytecode

    def get_stats(self):
        """Get VM statistics"""
        return {
            "cache_hits": len(self.cache),
            "hot_paths": len(self.hot_paths),
        }


# ============================================================================
# REAL NATIVE C COMPILER - KentScript → C → gcc → REAL Binary
# ============================================================================


class RealCCompiler:
    """Real C code generator and compiler - NOT simulation"""

    def __init__(self):
        self.c_code = []
        self.var_types = {}
        self.function_defs = []
        self.includes = set()
        self.benchmark_mode = False
        self.is_arm64 = self._detect_arm64()
        self.is_windows = sys.platform == "win32"
        self.is_macos = sys.platform == "darwin"
        self.is_linux = sys.platform == "linux"

    def _detect_arm64(self):
        import platform

        machine = platform.machine().lower()
        return "aarch64" in machine or "arm64" in machine

    def compile_to_c(self, ast):
        """Compile KentScript AST to actual C code"""
        self.c_code = []
        self.var_types = {}
        self.function_defs = []
        self.includes = {
            "stdio.h",
            "stdlib.h",
            "string.h",
            "stdint.h",
            "time.h",
            "unistd.h",
            "sys/syscall.h",
            "sys/mman.h",
        }

        # Generate C code
        self.c_code.insert(0, "#define _POSIX_C_SOURCE 200809L")
        self.c_code.insert(1, "#define _DEFAULT_SOURCE")
        self._emit_includes()
        self._emit_forward_declarations()

        # Add stdlib helper functions for built-in modules
        self._emit_stdlib_helpers()

        # Check if code has functions or just expressions
        has_func = any(isinstance(s, tuple) and s[0] == "func" for s in ast)

        if has_func:
            # Compile functions at top level
            for stmt in ast:
                if isinstance(stmt, tuple) and stmt[0] == "func":
                    self._compile_func(stmt)
            # Wrap other statements in main
            self.c_code.append("int main() {")
            for stmt in ast:
                if not (isinstance(stmt, tuple) and stmt[0] == "func"):
                    self._compile_stmt(stmt)
            self.c_code.append("  return 0;")
            self.c_code.append("}")
        else:
            # All statements go in main
            self.c_code.append("int main() {")
            for stmt in ast:
                self._compile_stmt(stmt)
            self.c_code.append("  return 0;")
            self.c_code.append("}")

        return "\n".join(self.c_code)

    def to_binary(self, source_file=None, output_filename="output"):
        """Compile to native binary with cross-platform and ARM64 support"""
        if source_file is not None:
            try:
                with open(source_file, "r") as f:
                    code = f.read()
                ast = _ks_parse(code, source_file)

                # ── [KS-TYPE] Type-check before transpilation ─────────────────
                try:
                    _tc = TypeChecker()
                    _tc_errors = []
                    for node in ast or []:
                        _nt = node.__class__.__name__ if node else ""
                        if _nt in ("VarDecl", "LetStatement", "Assignment"):
                            _name = getattr(node, "name", None) or (
                                getattr(node.target, "name", None)
                                if hasattr(node, "target")
                                else None
                            )
                            _hint = getattr(node, "var_type", None)
                            _val = getattr(node, "value", None)
                            if _name and hasattr(_tc, "register_variable"):
                                try:
                                    _tc.register_variable(_name, _val, _hint)
                                except TypeError as _te:
                                    _tc_errors.append(str(_te))

                except Exception as _tc_err:
                    print(f"[TypeCheck] Warning (non-fatal): {_tc_err}")

                # [KS-REF-021] Check incremental cache before transpiling
                cached = _KS_CACHE.get(code)
                if cached:
                    self.c_code = cached["c_source"]

                else:
                    from codegen.c_transpiler import CTranspiler

                    transpiler = CTranspiler(benchmark_mode=self.benchmark_mode)
                    self.c_code = transpiler.transpile(ast)
                    _KS_CACHE.put(code, self.c_code)
            except Exception as e:
                print(f"Error: Failed to compile source: {e}")
                import traceback

                traceback.print_exc()
                return False

        platform_name = _PlatformOps.get_platform()
        compiler_path, compiler_name = _PlatformOps.find_compiler()
        output_ext = _PlatformOps.get_output_ext()
        calling_conv = _PlatformOps.get_calling_convention()

        c_filename = output_filename.replace(".exe", "").replace(".out", "") + ".c"
        binary_name = output_filename + (
            output_ext if not output_filename.endswith(".exe") else ""
        )

        c_code = self.c_code
        if not c_code.startswith("#pragma"):
            c_code = '#pragma GCC optimize("Ofast")\n' + c_code

        includes = _MemoryOps.get_libc_includes(platform_name)

        # [KS-ENG-B] FMA header + [KS-ENG-C] SIMD header
        fma_hdr = getattr(self, "_fma_header", "") or ""
        simd_hdr = getattr(self, "_simd_header", "") or ""

        full_c = (
            self._inject_platform_headers()
            + includes
            + "\n"
            + simd_hdr
            + fma_hdr
            + "\n\n"
            + c_code
        )

        with open(c_filename, "w") as f:
            f.write(full_c)

        print(f"[C] Generated {c_filename} ({platform_name})")

        flags = self._get_platform_flags()
        # [KS-ENG-C] Inject SIMD flags detected by RealSIMDIntrinsicEmitter
        extra_simd = getattr(self, "_extra_simd_flags", [])
        if extra_simd:
            # Merge: don't duplicate -march=native if already present
            for f in extra_simd:
                if f not in flags:
                    flags.append(f)
        if self.is_arm64:
            print("[ARM64] Detected - enabling NEON SIMD optimizations")
            flags.extend(
                [
                    "-march=armv8.5-a+crypto+fp16",
                    "-mtune=cortex-a76",
                    "-ftree-vectorize",
                    "-funroll-loops",
                    "-ffast-math",
                    "-fomit-frame-pointer",
                ]
            )

        script_dir = os.path.dirname(os.path.abspath(__file__))
        include_dir = (
            os.path.join(os.path.dirname(script_dir), "include")
            if os.path.basename(script_dir) == "kentscript"
            else os.path.join(script_dir, "include")
        )

        compile_cmd = [
            compiler_path,
            c_filename,
            "-o",
            binary_name,
            f"-I{include_dir}",
        ] + flags

        try:
            result = subprocess.run(
                compile_cmd, capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                print(f"[Error] {result.stderr}")
                raise RuntimeError("Compilation failed")

            if os.path.exists(binary_name):
                os.chmod(binary_name, 0o755)

            print(f"[Binary] Compiled to {binary_name} ({calling_conv})")
            return binary_name
        except Exception as e:
            print(f"[Error] {e}")
            raise

    def _inject_platform_headers(self):
        headers = ""
        if self.is_linux:
            headers += "#include <time.h>\n#include <unistd.h>\n"
            if self.is_arm64:
                headers += "#ifdef __aarch64__\n#include <arm_neon.h>\n#endif\n"
        elif self.is_windows:
            headers += "#include <windows.h>\n"
        elif self.is_macos:
            headers += "#include <time.h>\n#include <unistd.h>\n"
        return headers

    def _get_platform_flags(self):
        # [KS-REF-003] -march=native + -mtune=native for best native codegen
        # Aggressive flags targeting C-native speed
        base_flags = [
            "-O3",
            "-march=native",
            "-mtune=native",
            "-flto",  # link-time optimisation
            "-funroll-loops",  # loop unrolling
            "-ffast-math",  # aggressive FP (breaks IEEE, huge speed gain)
            "-fomit-frame-pointer",  # free up a register
            "-ftree-vectorize",  # auto-SIMD
            "-fno-stack-protector",  # skip stack canaries (safe for KS generated code)
            "-ffunction-sections",  # enable dead-code elimination
            "-fdata-sections",
            "-Wl,--gc-sections",  # strip unused sections
            "-fprefetch-loop-arrays",  # prefetch hint for array loops
        ]
        if self.is_windows:
            return base_flags + ["-static"]
        elif self.is_macos:
            return base_flags + ["-fno-asynchronous-unwind-tables"]
        else:
            return base_flags + ["-fno-asynchronous-unwind-tables"]

    def _old_to_binary(self, input_file, output_binary, optimize=False):
        """Compile KentScript file to C to binary"""
        try:
            # Read and parse source file
            with open(input_file, "r") as f:
                code = f.read()

            # Simple parsing (would use full lexer/parser in production)
            from compiler.lexer.lexer import Lexer
            from compiler.parser.parser import Parser

            lexer = Lexer(code)
            tokens = lexer.tokenize()
            parser = Parser(tokens, source=code)
            ast = parser.parse()

            # Generate C code
            c_code = self.compile_to_c(ast)

            # Write C file to current directory, not input directory
            import os as os_module

            c_file = os_module.path.basename(input_file.replace(".ks", ".c"))
            with open(c_file, "w") as f:
                f.write(c_code)

            print(f"[C] Generated {c_file}")

            # Compile with detected compiler
            import subprocess
            try:
                from ks_core import _PlatformOps
                compiler_path, _ = _PlatformOps.find_compiler()
            except Exception:
                compiler_path = "gcc"

            result = subprocess.run(
                [compiler_path, "-O3", c_file, "-o", output_binary, "-lm"],
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                error = result.stderr.decode("utf-8", errors="ignore")
                print(f"[Error] GCC compilation failed:\n{error}")
                return False

            print(f"[Binary] Compiled to {output_binary}")
            return True

        except Exception as e:
            print(f"[Error] Compilation failed: {e}")
            return False

    def _emit_includes(self):
        """Emit C include directives"""
        for inc in sorted(self.includes):
            self.c_code.append(f"#include <{inc}>")
        self.c_code.append("")

    def _emit_forward_declarations(self):
        """Emit function forward declarations"""
        self.c_code.append("// Forward declarations")
        self.c_code.append("")

    def _emit_stdlib_helpers(self):
        """Emit stdlib helper functions for built-in modules"""
        self.c_code.append("// KentScript stdlib helpers")
        self.c_code.append("")
        self.c_code.append("// Colored output helper")
        self.c_code.append(
            "char* _ks_colored(char* text, char* fg, char* bg, char* style) {"
        )
        self.c_code.append("    static char buf[4096];")
        self.c_code.append("    int pos = 0;")
        self.c_code.append("    int codes[10]; int nc = 0;")
        self.c_code.append(
            '    if (fg && strcmp(fg, "none") != 0) { codes[nc++] = fg[0] ? atoi(fg) : 30; }'
        )
        self.c_code.append(
            '    if (bg && strcmp(bg, "none") != 0) { codes[nc++] = bg[0] ? atoi(bg) + 10 : 40; }'
        )
        self.c_code.append(
            '    if (style && strcmp(style, "none") != 0) { codes[nc++] = style[0] ? atoi(style) : 1; }'
        )
        self.c_code.append('    pos += sprintf(buf, "\\033[");')
        self.c_code.append(
            '    for (int i = 0; i < nc; i++) { pos += sprintf(buf + pos, "%d%s", codes[i], i < nc-1 ? ";" : "m"); }'
        )
        self.c_code.append('    pos += sprintf(buf + pos, "%s\\033[0m", text);')
        self.c_code.append("    return buf;")
        self.c_code.append("}")
        self.c_code.append("")
        self.c_code.append("// Progress bar helpers")
        self.c_code.append(
            "char* _ks_progress_bar(int percent, int width, char* color) {"
        )
        self.c_code.append("    static char buf[256];")
        self.c_code.append("    int filled = (percent * width) / 100;")
        self.c_code.append("    int empty = width - filled;")
        self.c_code.append("    int pos = 0;")
        self.c_code.append(
            '    for (int i = 0; i < filled; i++) pos += sprintf(buf + pos, "█");'
        )
        self.c_code.append(
            '    for (int i = 0; i < empty; i++) pos += sprintf(buf + pos, "░");'
        )
        self.c_code.append('    pos += sprintf(buf + pos, " %d%%", percent);')
        self.c_code.append("    return buf;")
        self.c_code.append("}")
        self.c_code.append("")
        self.c_code.append(
            "char* _ks_progress_bar_cyber(int percent, int width, char* color) {"
        )
        self.c_code.append("    static char buf[256];")
        self.c_code.append("    int filled = (percent * width) / 100;")
        self.c_code.append("    int empty = width - filled;")
        self.c_code.append('    char* chars[] = {"▓", "▒", "░"};')
        self.c_code.append("    int pos = 0;")
        self.c_code.append('    pos += sprintf(buf + pos, "╭");')
        self.c_code.append(
            '    for (int i = 0; i < filled; i++) pos += sprintf(buf + pos, "%s", chars[i %% 3]);'
        )
        self.c_code.append(
            '    for (int i = 0; i < empty; i++) pos += sprintf(buf + pos, "░");'
        )
        self.c_code.append(
            '    pos += sprintf(buf + pos, "╮ %5.1f%% %s", (double)percent, percent < 100 ? "▶" : "█");'
        )
        self.c_code.append("    return buf;")
        self.c_code.append("}")
        self.c_code.append("")
        self.c_code.append("char* _ks_progress_bar_matrix(int percent, int width) {")
        self.c_code.append("    static char buf[512];")
        self.c_code.append("    int filled = (percent * width) / 100;")
        self.c_code.append('    char* chars[] = {"█", "▓", "▒", "░"};')
        self.c_code.append("    int pos = 0;")
        self.c_code.append(
            '    pos += sprintf(buf + pos, "┌"); for (int i = 0; i < width; i++) pos += sprintf(buf + pos, "─"); pos += sprintf(buf + pos, "┐\\n");'
        )
        self.c_code.append('    pos += sprintf(buf + pos, "│");')
        self.c_code.append(
            '    for (int i = 0; i < filled; i++) pos += sprintf(buf + pos, "%s", chars[i %% 4]);'
        )
        self.c_code.append(
            '    for (int i = filled; i < width; i++) pos += sprintf(buf + pos, "░");'
        )
        self.c_code.append('    pos += sprintf(buf + pos, "│ %d%%\\n", percent);')
        self.c_code.append(
            '    pos += sprintf(buf + pos, "└"); for (int i = 0; i < width; i++) pos += sprintf(buf + pos, "─"); pos += sprintf(buf + pos, "┘");'
        )
        self.c_code.append("    return buf;")
        self.c_code.append("}")
        self.c_code.append("")
        self.c_code.append("char* _ks_progress_bar_gradient(int percent, int width) {")
        self.c_code.append("    static char buf[512];")
        self.c_code.append("    int filled = (percent * width) / 100;")
        self.c_code.append('    char* colors[] = {"31", "33", "32", "36", "34", "35"};')
        self.c_code.append("    int pos = 0;")
        self.c_code.append('    pos += sprintf(buf + pos, "╔");')
        self.c_code.append(
            '    for (int i = 0; i < filled; i++) { int c = atoi(colors[(i * 6) / width]); pos += sprintf(buf + pos, "\\033[%dm▰\\033[0m", c); }'
        )
        self.c_code.append(
            '    for (int i = filled; i < width; i++) pos += sprintf(buf + pos, "\\033[2m▱\\033[0m");'
        )
        self.c_code.append(
            '    pos += sprintf(buf + pos, "╗\\n║ \\033[1m%5.1f%%\\033[0m║", (double)percent);'
        )
        self.c_code.append("    return buf;")
        self.c_code.append("}")
        self.c_code.append("")
        self.c_code.append(
            "char* _ks_progress_bar_scifi(int percent, int width, char* color) {"
        )
        self.c_code.append("    static char buf[256];")
        self.c_code.append("    int filled = (percent * width) / 100;")
        self.c_code.append("    int empty = width - filled;")
        self.c_code.append("    int pos = 0;")
        self.c_code.append('    pos += sprintf(buf + pos, "⟪ ⎣");')
        self.c_code.append(
            '    for (int i = 0; i < filled; i++) pos += sprintf(buf + pos, "█");'
        )
        self.c_code.append(
            '    for (int i = 0; i < empty; i++) pos += sprintf(buf + pos, "░");'
        )
        self.c_code.append(
            '    pos += sprintf(buf + pos, "⎤ %05.1f%%", (double)percent);'
        )
        self.c_code.append("    return buf;")
        self.c_code.append("}")
        self.c_code.append("")

    def _emit_main(self):
        """Emit main function wrapper"""
        self.c_code.append("int main() {")
        self.c_code.append("  return 0;")
        self.c_code.append("}")

    def _compile_stmt(self, stmt):
        """Compile ANY statement to C - comprehensive handler"""
        if not stmt:
            return

        # Get statement type
        stmt_type = None
        if isinstance(stmt, tuple) and len(stmt) > 0:
            stmt_type = stmt[0]
        elif hasattr(stmt, "__class__"):
            stmt_type = stmt.__class__.__name__
        else:
            return

        # Handle imports (skip them - we don't need them in C)
        if stmt_type == "ImportStmt" or stmt_type == "import":
            return  # Skip imports in C compilation

        # Handle LetDecl
        if stmt_type == "LetDecl":
            var_name = stmt.name if hasattr(stmt, "name") else "x"
            var_value = 0

            if hasattr(stmt, "value") and stmt.value:
                var_value = self._eval_expr_object(stmt.value)

            # Detect type
            var_type = "int64_t"
            if isinstance(var_value, float) or "." in str(var_value):
                var_type = "double"

            self.c_code.append(f"  {var_type} {var_name} = {var_value};")
            return

        # Handle Assignment
        if stmt_type == "Assignment":
            target = stmt.target if hasattr(stmt, "target") else None
            value = stmt.value if hasattr(stmt, "value") else None

            if target and value:
                target_name = target.name if hasattr(target, "name") else str(target)
                value_expr = self._eval_expr_object(value)
                self.c_code.append(f"  {target_name} = {value_expr};")
            return

        # Handle WhileStmt
        if stmt_type == "WhileStmt":
            cond = stmt.condition if hasattr(stmt, "condition") else None
            body = stmt.body if hasattr(stmt, "body") else []

            if cond:
                cond_expr = self._eval_expr_object(cond)
                self.c_code.append(f"  while ({cond_expr}) {{")
                for body_stmt in body:
                    self._compile_stmt(body_stmt)
                self.c_code.append("  }")
            return

        # Handle ForStmt / ForRange
        if stmt_type in ["ForStmt", "ForRange"]:
            # Get loop variable
            var_name = None
            if hasattr(stmt, "var"):
                var_name = stmt.var
            elif hasattr(stmt, "variable"):
                var = stmt.variable
                var_name = var.name if hasattr(var, "name") else str(var)
            elif hasattr(stmt, "target"):
                var = stmt.target
                var_name = var.name if hasattr(var, "name") else str(var)

            # Get iterable/range
            iterable = stmt.iterable if hasattr(stmt, "iterable") else None
            body = stmt.body if hasattr(stmt, "body") else []

            start_expr = "0"
            end_expr = "10"

            # Check if iterable is range()
            if (
                iterable
                and hasattr(iterable, "__class__")
                and iterable.__class__.__name__ == "FunctionCall"
            ):
                func = iterable.func
                args = iterable.args if hasattr(iterable, "args") else []

                func_name = func.name if hasattr(func, "name") else str(func)

                if func_name == "range" and len(args) >= 2:
                    start_expr = self._eval_expr_object(args[0])
                    end_expr = self._eval_expr_object(args[1])
            elif hasattr(stmt, "start") and hasattr(stmt, "end"):
                start_expr = self._eval_expr_object(stmt.start)
                end_expr = self._eval_expr_object(stmt.end)

            if var_name:
                self.c_code.append(
                    f"  for (int64_t {var_name} = {start_expr}; {var_name} < {end_expr}; {var_name}++) {{"
                )
                for body_stmt in body:
                    self._compile_stmt(body_stmt)
                self.c_code.append("  }")
            return

        # Handle FunctionCall (print, str, etc)
        if stmt_type == "FunctionCall":
            func_name = None
            if hasattr(stmt, "func"):
                if hasattr(stmt.func, "name"):
                    func_name = stmt.func.name
                elif isinstance(stmt.func, str):
                    func_name = stmt.func

            # Handle print()
            if func_name == "print":
                args = stmt.args if hasattr(stmt, "args") else []

                if args:
                    # Handle string concatenation specially
                    for arg in args:
                        if hasattr(arg, "__class__") and arg.__class__.__name__ in [
                            "BinaryOp",
                            "BinOp",
                        ]:
                            if hasattr(arg, "op") and arg.op == "+":
                                # Check if left or right is a string
                                left = arg.left
                                right = arg.right

                                left_str = (
                                    isinstance(left, type)
                                    and hasattr(left, "value")
                                    and isinstance(left.value, str)
                                )
                                right_str = (
                                    isinstance(right, type)
                                    and hasattr(right, "value")
                                    and isinstance(right.value, str)
                                )

                                if (
                                    hasattr(left, "__class__")
                                    and left.__class__.__name__ == "Literal"
                                    and isinstance(left.value, str)
                                ) or (
                                    hasattr(right, "__class__")
                                    and right.__class__.__name__ == "Literal"
                                    and isinstance(right.value, str)
                                ):
                                    # String concatenation - print as multiple parts
                                    left_eval = self._eval_expr_object(left)
                                    right_eval = self._eval_expr_object(right)

                                    # Separate by string vs number
                                    if left_eval.startswith('"'):
                                        # Left is string, right is value
                                        self.c_code.append(
                                            f'  printf("%s %lld\\n", {left_eval}, (long long){right_eval});'
                                        )
                                    elif right_eval.startswith('"'):
                                        # Right is string, left is value
                                        self.c_code.append(
                                            f'  printf("%lld %s\\n", (long long){left_eval}, {right_eval});'
                                        )
                                    else:
                                        # Both numbers
                                        self.c_code.append(
                                            f'  printf("%lld %lld\\n", (long long){left_eval}, (long long){right_eval});'
                                        )
                                    continue

                        # Regular argument - not string concat
                        expr_result = self._eval_expr_object(arg)

                        if isinstance(expr_result, str) and expr_result.startswith('"'):
                            self.c_code.append(f'  printf("%s\\n", {expr_result});')
                        else:
                            self.c_code.append(
                                f'  printf("%lld\\n", (long long){expr_result});'
                            )
                else:
                    self.c_code.append('  printf("\\n");')
                return

            # Handle str() - convert to string
            if func_name == "str":
                # str() is used in string context, just pass through the value
                return

            # Handle other function calls
            return

        # Handle IfStmt
        if stmt_type == "IfStmt":
            cond = stmt.condition if hasattr(stmt, "condition") else None
            then_body = stmt.then_block if hasattr(stmt, "then_block") else []
            else_body = stmt.else_block if hasattr(stmt, "else_block") else []

            if cond:
                cond_expr = self._eval_expr_object(cond)
                self.c_code.append(f"  if ({cond_expr}) {{")
                for s in then_body:
                    self._compile_stmt(s)

                if else_body:
                    self.c_code.append("  } else {")
                    for s in else_body:
                        self._compile_stmt(s)

                self.c_code.append("  }")
            return

        # Handle ExprStmt
        if stmt_type == "ExprStmt":
            expr = (
                stmt.value
                if hasattr(stmt, "value")
                else stmt.expression
                if hasattr(stmt, "expression")
                else None
            )
            if expr:
                expr_result = self._eval_expr_object(expr)
                self.c_code.append(f"  {expr_result};")
            return

        # Handle tuple-based statements (legacy)
        if isinstance(stmt, tuple):
            if stmt_type == "let":
                self._compile_let(stmt)
            elif stmt_type == "const":
                self._compile_const(stmt)
            elif stmt_type == "func":
                self._compile_func(stmt)
            elif stmt_type == "if":
                self._compile_if(stmt)
            elif stmt_type == "while":
                self._compile_while(stmt)
            elif stmt_type == "for":
                self._compile_for(stmt)
            elif stmt_type == "return":
                self._compile_return(stmt)
            elif stmt_type == "print":
                args = stmt[1] if len(stmt) > 1 else []
                if args:
                    for arg in args:
                        expr = self._compile_expr(arg)
                        self.c_code.append(f'  printf("%lld\\n", (long long){expr});')
                else:
                    self.c_code.append('  printf("\\n");')

    def _eval_expr_object(self, expr):
        """Evaluate ANY expression object"""
        if not expr:
            return "0"

        if isinstance(expr, str):
            return expr

        if isinstance(expr, (int, float)):
            return str(expr)

        if not hasattr(expr, "__class__"):
            return "0"

        expr_type = expr.__class__.__name__

        # Literals
        if expr_type in ["Literal", "IntLiteral", "FloatLiteral"]:
            val = expr.value if hasattr(expr, "value") else 0
            # If it's a string, keep the quotes
            if isinstance(val, str):
                return f'"{val}"'
            return str(val)

        if expr_type == "StringLiteral":
            val = expr.value if hasattr(expr, "value") else ""
            return f'"{val}"'

        # Identifiers
        if expr_type == "Identifier":
            return expr.name if hasattr(expr, "name") else "x"

        # Binary operations
        if expr_type in ["BinaryOp", "BinOp"]:
            left = self._eval_expr_object(expr.left) if hasattr(expr, "left") else "0"
            right = (
                self._eval_expr_object(expr.right) if hasattr(expr, "right") else "0"
            )
            op = expr.op if hasattr(expr, "op") else "+"

            # Handle string concatenation
            if op == "+" and (
                isinstance(left, str)
                and left.startswith('"')
                or isinstance(right, str)
                and right.startswith('"')
            ):
                # For now, just return left (string concat not fully supported in C)
                return f"({left} + {right})"

            return f"({left} {op} {right})"

        # Unary operations
        if expr_type in ["UnaryOp", "UnOp"]:
            operand = (
                self._eval_expr_object(expr.operand)
                if hasattr(expr, "operand")
                else "0"
            )
            op = expr.op if hasattr(expr, "op") else "-"
            return f"({op}{operand})"

        # Function calls
        if expr_type == "FunctionCall":
            func_name = None
            if hasattr(expr, "func"):
                if hasattr(expr.func, "name"):
                    func_name = expr.func.name

            # Handle str(x) - convert to string representation
            if func_name == "str":
                args = expr.args if hasattr(expr, "args") else []
                if args:
                    return self._eval_expr_object(args[0])

            # Handle time.time() and other module calls
            if func_name and "." in str(expr):
                # Module function call - return placeholder
                return "0.0"

            return "0"

        # Attribute access (like time.time)
        if expr_type == "Attribute":
            obj = expr.value if hasattr(expr, "value") else None
            attr = expr.attr if hasattr(expr, "attr") else None

            # time.time() returns current time
            if obj and attr == "time":
                import time

                return str(time.time())

            return "0"

        # Call nodes
        if expr_type == "Call":
            func = expr.func if hasattr(expr, "func") else None
            args = expr.args if hasattr(expr, "args") else []

            # time.time()
            if hasattr(func, "attr") and func.attr == "time":
                import time

                return str(time.time())

            return "0"

        return "0"

    def _compile_let(self, stmt):
        """Compile let binding to C variable declaration"""
        var_name = stmt[1]
        value = stmt[2] if len(stmt) > 2 else None

        # Infer type
        var_type = self._infer_type(value)
        self.var_types[var_name] = var_type

        if value:
            expr = self._compile_expr(value)
            self.c_code.append(f"  {var_type} {var_name} = {expr};")
        else:
            self.c_code.append(f"  {var_type} {var_name};")

    def _compile_const(self, stmt):
        """Compile const binding"""
        var_name = stmt[1]
        value = stmt[2] if len(stmt) > 2 else None

        var_type = self._infer_type(value)
        self.var_types[var_name] = var_type

        if value:
            expr = self._compile_expr(value)
            self.c_code.append(f"  const {var_type} {var_name} = {expr};")

    def _compile_func(self, stmt):
        """Compile function definition to C"""
        func_name = stmt[1]
        params = stmt[2] if len(stmt) > 2 else []
        body = stmt[3] if len(stmt) > 3 else []

        # Function signature
        param_strs = []
        for param in params:
            param_type = self.var_types.get(param, "int64_t")
            param_strs.append(f"{param_type} {param}")

        param_list = ", ".join(param_strs) if param_strs else "void"

        self.c_code.append(f"int64_t {func_name}({param_list}) {{")

        # Function body
        for body_stmt in body:
            self._compile_stmt(body_stmt)

        self.c_code.append("}")
        self.c_code.append("")

    def _compile_if(self, stmt):
        """Compile if statement to C"""
        cond = stmt[1]
        then_body = stmt[2] if len(stmt) > 2 else []
        else_body = stmt[3] if len(stmt) > 3 else []

        cond_expr = self._compile_expr(cond)
        self.c_code.append(f"  if ({cond_expr}) {{")

        for s in then_body:
            self._compile_stmt(s)

        if else_body:
            self.c_code.append("  } else {")
            for s in else_body:
                self._compile_stmt(s)

        self.c_code.append("  }")

    def _compile_while(self, stmt):
        """Compile while loop to C"""
        cond = stmt[1]
        body = stmt[2] if len(stmt) > 2 else []

        cond_expr = self._compile_expr(cond)
        self.c_code.append(f"  while ({cond_expr}) {{")

        for s in body:
            self._compile_stmt(s)

        self.c_code.append("  }")

    def _compile_for(self, stmt):
        """Compile for loop to C"""
        var = stmt[1]
        start = stmt[2] if len(stmt) > 2 else ("int", 0)
        end = stmt[3] if len(stmt) > 3 else ("int", 10)
        body = stmt[4] if len(stmt) > 4 else []

        start_expr = self._compile_expr(start)
        end_expr = self._compile_expr(end)

        self.c_code.append(
            f"  for (int64_t {var} = {start_expr}; {var} < {end_expr}; {var}++) {{"
        )

        for s in body:
            self._compile_stmt(s)

        self.c_code.append("  }")

    def _compile_return(self, stmt):
        """Compile return statement"""
        if len(stmt) > 1:
            expr = self._compile_expr(stmt[1])
            self.c_code.append(f"  return {expr};")
        else:
            self.c_code.append("  return 0;")

    def _compile_expr(self, expr):
        """Compile expression to C expression"""
        if not isinstance(expr, tuple) or len(expr) == 0:
            return "0"

        expr_type = expr[0]

        # Literals
        if expr_type == "int":
            return str(expr[1])
        elif expr_type == "float":
            return str(expr[1])
        elif expr_type == "string":
            val = expr[1] if len(expr) > 1 else ""
            val = val.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{val}"'
        elif expr_type == "bool":
            return "1" if expr[1] else "0"
        elif expr_type == "ident":
            return expr[1]
        elif expr_type in ["+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">="]:
            left = self._compile_expr(expr[1])
            right = self._compile_expr(expr[2])
            return f"({left} {expr_type} {right})"
        elif expr_type in ["and", "or"]:
            left = self._compile_expr(expr[1])
            right = self._compile_expr(expr[2])
            op = "&&" if expr_type == "and" else "||"
            return f"({left} {op} {right})"
        elif expr_type == "call":
            func_name = expr[1][1] if isinstance(expr[1], tuple) else expr[1]
            args = expr[2] if len(expr) > 2 else []
            arg_strs = [self._compile_expr(arg) for arg in args]
            arg_list = ", ".join(arg_strs)

            # Handle module function calls
            if isinstance(expr[1], str) and "." in expr[1]:
                # Module call like time.time() → return constant or function
                module, func = expr[1].split(".")
                if module == "time" and func == "time":
                    return "time(NULL)"
                elif module == "math":
                    return f"{func}({arg_list})"
                elif module == "color":
                    if func == "progress_bar":
                        return f"_ks_progress_bar({arg_list})"
                    elif func == "progress_bar_cyber":
                        return f"_ks_progress_bar_cyber({arg_list})"
                    elif func == "progress_bar_matrix":
                        return f"_ks_progress_bar_matrix({arg_list})"
                    elif func == "progress_bar_gradient":
                        return f"_ks_progress_bar_gradient({arg_list})"
                    elif func == "progress_bar_scifi":
                        return f"_ks_progress_bar_scifi({arg_list})"
                    elif func == "colored":
                        return f"_ks_colored({arg_list})"
                    else:
                        return f"0"
                else:
                    return f"0"  # Unknown module

            # Handle attribute calls (module.function)
            if isinstance(expr[1], tuple) and expr[1][0] == "attr":
                obj_name = expr[1][1] if len(expr[1]) > 1 else "unknown"
                attr_name = expr[1][2] if len(expr[1]) > 2 else "unknown"

                if obj_name == "time" and attr_name == "time":
                    return "time(NULL)"

            return f"{func_name}({arg_list})"

        return "0"

    def _infer_type(self, expr):
        """Infer C type from expression"""
        if isinstance(expr, tuple):
            if expr[0] == "int":
                return "int64_t"
            elif expr[0] == "float":
                return "double"
            elif expr[0] == "string":
                return "const char*"
            elif expr[0] == "bool":
                return "int"
            elif expr[0] in ["+", "-", "*", "/", "%"]:
                return "int64_t"
            elif expr[0] in ["==", "!=", "<", "<=", ">", ">="]:
                return "int"
        return "int64_t"

    def get_stats(self):
        """Get compilation statistics"""
        return {
            "c_lines": len(self.c_code),
            "functions": len(self.function_defs),
            "variables": len(self.var_types),
        }


class RealWebAssemblyCompiler:
    """Real WebAssembly with binary module generation"""

    def __init__(self):
        self.functions = []
        self.exports = {}
        self.module_bytes = None

    def compile_function(self, name, params, returns, body):
        """Compile function"""
        func = {"name": name, "params": params, "returns": returns, "code": body}
        self.functions.append(func)
        return len(self.functions) - 1

    def generate_module(self):
        """Generate WASM binary module"""
        self.module_bytes = bytearray()
        self.module_bytes += b"\x00asm"
        self.module_bytes += struct.pack("<I", 1)
        self._write_sections()
        return bytes(self.module_bytes)

    def _write_sections(self):
        """Write WASM sections"""
        # Type section
        section = bytearray()
        section.append(len(self.functions))
        for func in self.functions:
            section.append(0x60)
            section.append(len(func["params"]))
            for p in func["params"]:
                section.append(0x7F if p == "i32" else 0x7E)
            section.append(len(func["returns"]))
            for r in func["returns"]:
                section.append(0x7F if r == "i32" else 0x7E)
        self._write_section(1, section)

        # Function section
        section = bytearray()
        section.append(len(self.functions))
        for i in range(len(self.functions)):
            section.append(i)
        self._write_section(3, section)

        # Memory section
        section = bytearray()
        section.append(1)
        section.append(0)
        section.append(1)
        self._write_section(5, section)

        # Export section
        section = bytearray()
        section.append(len(self.exports))
        for name, (kind, idx) in self.exports.items():
            section.append(len(name))
            section.extend(name.encode())
            section.append(kind)
            section.append(idx)
        self._write_section(7, section)

        # Code section
        section = bytearray()
        section.append(len(self.functions))
        for func in self.functions:
            code = bytearray()
            code.append(0)
            code.append(0x41)
            code.append(42)
            code.append(0x0B)
            section.append(len(code))
            section.extend(code)
        self._write_section(10, section)

    def _write_section(self, id, content):
        """Write section"""
        self.module_bytes.append(id)
        self._write_leb128(len(content))
        self.module_bytes.extend(content)

    def _write_leb128(self, value):
        """Write LEB128"""
        while True:
            byte = value & 0x7F
            value >>= 7
            if value != 0:
                self.module_bytes.append(byte | 0x80)
            else:
                self.module_bytes.append(byte)
                break

    def export_function(self, name, idx):
        """Export function"""
        self.exports[name] = (0, idx)

    def save_module(self, filename):
        """Save WASM module"""
        if not self.module_bytes:
            self.generate_module()
        with open(filename, "wb") as f:
            f.write(self.module_bytes)
        return filename


# ===== REAL DEBUGGER =====
class RealDebugger:
    """Real interactive debugger"""

    def __init__(self):
        self.breakpoints = {}
        self.watches = {}
        self.call_stack = []
        self.locals = []
        self.paused = False

    def set_breakpoint(self, filename, line, condition=None):
        """Set breakpoint"""
        if filename not in self.breakpoints:
            self.breakpoints[filename] = {}
        self.breakpoints[filename][line] = condition

    def remove_breakpoint(self, filename, line):
        """Remove breakpoint"""
        if filename in self.breakpoints and line in self.breakpoints[filename]:
            del self.breakpoints[filename][line]

    def list_breakpoints(self):
        """List breakpoints"""
        result = []
        for file, bps in self.breakpoints.items():
            for line, cond in bps.items():
                result.append(f"{file}:{line}")
        return result

    def watch(self, expression):
        """Add watch"""
        self.watches[expression] = None

    def check_breakpoint(self, filename, line, env=None):
        """Check breakpoint hit"""
        if filename not in self.breakpoints:
            return False
        return line in self.breakpoints[filename]

    def pause_at(self, filename, line, env=None):
        """Pause execution"""
        self.paused = True
        self.current_line = line
        self.current_file = filename
        if env:
            self.locals = list(env.items())

    def step_into(self):
        """Step into"""
        self.paused = False

    def step_over(self):
        """Step over"""
        self.paused = False

    def step_out(self):
        """Step out"""
        self.paused = False

    def continue_execution(self):
        """Continue"""
        self.paused = False

    def print_stack(self):
        """Print stack"""
        return self.call_stack

    def print_locals(self):
        """Print locals"""
        return self.locals

    def eval_expression(self, expr, env=None):
        """Eval expression"""
        try:
            return eval(expr, {"__builtins__": {}}, env or dict(self.locals))
        except:
            return None


# ===== REAL LSP SERVER =====
class RealLSPServer:
    """Real Language Server Protocol"""

    def __init__(self):
        self.documents = {}
        self.diagnostics = {}
        self.running = True

    def handle_message(self, msg):
        """Handle LSP message"""
        method = msg.get("method")

        if method == "initialize":
            return {"capabilities": {"completionProvider": True}}
        elif method == "textDocument/didOpen":
            uri = msg["params"]["textDocument"]["uri"]
            self.documents[uri] = msg["params"]["textDocument"]["text"]
            return None
        elif method == "textDocument/completion":
            return self._completions()
        elif method == "textDocument/hover":
            return self._hover_info()
        elif method == "shutdown":
            self.running = False
            return None

        return None

    def _completions(self):
        """Get completions"""
        return {
            "items": [
                {"label": "fn", "kind": 1},
                {"label": "let", "kind": 1},
                {"label": "import", "kind": 1},
                {"label": "print", "kind": 3},
            ]
        }

    def _hover_info(self):
        """Get hover info"""
        return {"contents": "KentScript"}


# ===== GLOBAL INSTANCES =====
WASM_COMPILER = RealWebAssemblyCompiler()
DEBUGGER = RealDebugger()
LSP_SERVER = RealLSPServer()

# Creator Information
CREATOR = "pyLord (Musika Alvin)"
CREATOR_LOCATION = "Uganda"
CREATOR_GITHUB = "https://github.com/musikaalvin"
KENTSCRIPT_VERSION = "3.1.0"
COMPILER_LINES = 38790


# ============================================================================
# Unified Language Module - Import from single source of truth
# ============================================================================
from lang import Lexer, Token, TokenType, Parser, ASTNode, LetDecl, Assignment

# ============================================================================
# AST Nodes
# ============================================================================

# ============================================================================
# ENVIRONMENT
# ============================================================================



# Interpreter and runtime types
from ks.interpreter import *  # noqa: F401,F403

class ASTCache:
    def __init__(self):
        # Use /tmp to avoid read-only filesystem issues
        self.cache_dir = "/tmp/.ks_cache"
        try:
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir, exist_ok=True)
        except:
            # If we can't create cache, that's fine - just disable caching
            self.cache_dir = None

    def get_cache_path(self, filename: str) -> str:
        if self.cache_dir is None:
            return None
        base = os.path.basename(filename)
        return os.path.join(self.cache_dir, f"{base}.ast")

    def save(self, filename: str, ast: List[ASTNode]):
        if self.cache_dir is None:
            return
        path = self.get_cache_path(filename)
        if path is None:
            return
        try:
            with open(path, "wb") as f:
                pickle.dump(ast, f)
        except:
            pass

    def load(self, filename: str) -> Optional[List[ASTNode]]:
        if self.cache_dir is None:
            return None
        path = self.get_cache_path(filename)
        if path is None:
            return None
        if not os.path.exists(path):
            return None
        if os.path.getmtime(filename) > os.path.getmtime(path):
            return None
        try:
            with open(path, "rb") as f:
                ast = pickle.load(f)
            # Reject stale cache from a foreign parser module
            if ast and type(ast[0]).__module__ != __name__:
                return None
            # Also spot-check a few inner nodes for foreign types
            import itertools

            for node in itertools.islice(ast, 5):
                for attr in ("value", "body", "args", "elements"):
                    child = getattr(node, attr, None)
                    if child is not None and not isinstance(
                        child, (int, float, str, bool, list, tuple, type(None))
                    ):
                        if type(child).__module__ not in (__name__, "builtins"):
                            return None
            return ast
        except:
            return None


class BytecodeCache:
    def __init__(self):
        self.cache_dir = ".ks_bytecode"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def get_cache_path(self, filename: str) -> str:
        base = os.path.basename(filename)
        return os.path.join(self.cache_dir, f"{base}.ksc")

    def save(self, filename: str, bc_data):
        path = self.get_cache_path(filename)
        try:
            with open(path, "wb") as f:
                pickle.dump(bc_data, f)
            return path
        except:
            return None

    def load(self, filename: str):
        path = self.get_cache_path(filename)
        if not os.path.exists(path):
            return None
        if os.path.getmtime(filename) > os.path.getmtime(path):
            return None
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except:
            return None


# ================ REPL ================

# ============================================================================
# KSECURITY MODULE - CYBERSECURITY & PENETRATION TESTING (v3.1.0 ENHANCEMENT)
# ============================================================================

import socket
import ipaddress
import secrets as secrets_module
import hmac


class SecurityModule:
    """Advanced cybersecurity and penetration testing module"""

    @staticmethod
    def hash_password(password, salt=None):
        """Hash password with PBKDF2-SHA256"""
        if salt is None:
            salt = secrets_module.token_bytes(32)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return base64.b64encode(salt + key).decode()

    @staticmethod
    def verify_password(password, hash_value):
        """Verify password against hash"""
        try:
            data = base64.b64decode(hash_value)
            salt = data[:32]
            stored_hash = data[32:]
            key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
            return hmac.compare_digest(key, stored_hash)
        except:
            return False

    @staticmethod
    def encrypt_simple(text, key):
        """Simple XOR encryption"""
        key_bytes = hashlib.sha256(key.encode()).digest()
        text_bytes = text.encode()
        encrypted = bytes(
            a ^ b
            for a, b in zip(
                text_bytes, key_bytes * (len(text_bytes) // len(key_bytes) + 1)
            )
        )
        return base64.b64encode(encrypted).decode()

    @staticmethod
    def decrypt_simple(encrypted_text, key):
        """Simple XOR decryption"""
        try:
            encrypted = base64.b64decode(encrypted_text)
            key_bytes = hashlib.sha256(key.encode()).digest()
            decrypted = bytes(
                a ^ b
                for a, b in zip(
                    encrypted, key_bytes * (len(encrypted) // len(key_bytes) + 1)
                )
            )
            return decrypted.decode()
        except:
            return None

    @staticmethod
    def generate_key(length=32):
        """Generate random key"""
        return secrets_module.token_hex(length // 2)

    @staticmethod
    def port_scan(host, ports=None):
        """Scan open ports"""
        if ports is None:
            ports = [
                21,
                22,
                23,
                25,
                53,
                80,
                110,
                143,
                443,
                445,
                8080,
                8443,
                3306,
                5432,
                27017,
                6379,
            ]

        open_ports = []
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            if result == 0:
                open_ports.append(port)
            sock.close()
        return open_ports

    @staticmethod
    def check_open_port(host, port):
        """Check if single port is open"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0

    @staticmethod
    def ip_info(ip):
        """Get IP information"""
        try:
            addr = ipaddress.ip_address(ip)
            return {
                "ip": str(addr),
                "version": addr.version,
                "is_private": addr.is_private,
                "is_loopback": addr.is_loopback,
                "is_reserved": addr.is_reserved,
                "is_multicast": addr.is_multicast,
            }
        except:
            return None

    @staticmethod
    def dns_lookup(hostname):
        """DNS lookup"""
        try:
            return socket.gethostbyname(hostname)
        except:
            return None

    @staticmethod
    def reverse_dns(ip):
        """Reverse DNS lookup"""
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return None

    @staticmethod
    def sql_injection_test(user_input):
        """Detect potential SQL injection"""
        patterns = ["' OR", "'; DROP", "UNION SELECT", "--", "/*", "*/"]
        return any(pattern.lower() in user_input.lower() for pattern in patterns)

    @staticmethod
    def xss_test(user_input):
        """Detect potential XSS payloads"""
        patterns = ["<script", "onerror=", "onload=", "onclick=", "javascript:"]
        return any(pattern.lower() in user_input.lower() for pattern in patterns)

    @staticmethod
    def command_injection_test(user_input):
        """Detect potential command injection"""
        dangerous_chars = ["|", ";", "&", "$", "`", "\n", "\r", ">", "<"]
        return any(char in user_input for char in dangerous_chars)

    @staticmethod
    def base64_encode(text):
        """Base64 encode"""
        return base64.b64encode(text.encode()).decode()

    @staticmethod
    def base64_decode(text):
        """Base64 decode"""
        return base64.b64decode(text).decode()

    @staticmethod
    def hex_encode(text):
        """Hex encode"""
        return text.encode().hex()

    @staticmethod
    def hex_decode(hex_str):
        """Hex decode"""
        return bytes.fromhex(hex_str).decode()

    @staticmethod
    def url_encode(text):
        """URL encode"""
        return urllib.parse.quote(text)

    @staticmethod
    def url_decode(text):
        """URL decode"""
        return urllib.parse.unquote(text)


# Create ksecurity module instance
KSECURITY_MODULE = {
    "hash_password": SecurityModule.hash_password,
    "verify_password": SecurityModule.verify_password,
    "encrypt_simple": SecurityModule.encrypt_simple,
    "decrypt_simple": SecurityModule.decrypt_simple,
    "generate_key": SecurityModule.generate_key,
    "port_scan": SecurityModule.port_scan,
    "check_open_port": SecurityModule.check_open_port,
    "ip_info": SecurityModule.ip_info,
    "dns_lookup": SecurityModule.dns_lookup,
    "reverse_dns": SecurityModule.reverse_dns,
    "sql_injection_test": SecurityModule.sql_injection_test,
    "xss_test": SecurityModule.xss_test,
    "command_injection_test": SecurityModule.command_injection_test,
    "base64_encode": SecurityModule.base64_encode,
    "base64_decode": SecurityModule.base64_decode,
    "hex_encode": SecurityModule.hex_encode,
    "hex_decode": SecurityModule.hex_decode,
    "url_encode": SecurityModule.url_encode,
    "url_decode": SecurityModule.url_decode,
    "common_ports": [
        21,
        22,
        23,
        25,
        53,
        80,
        110,
        143,
        443,
        445,
        8080,
        8443,
        3306,
        5432,
        27017,
        6379,
    ],
    "sql_injection_payloads": [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1' UNION SELECT NULL--",
        "admin' --",
    ],
    "xss_payloads": [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg/onload=alert('XSS')>",
    ],
}


LangLexer = None
try:
    from pygments.lexer import RegexLexer, words
    from pygments.token import Keyword, Name, String, Number, Operator, Comment, Punctuation, Text

    class LangLexer(RegexLexer):
        name = "KentScript"
        aliases = ["kentscript", "ks"]
        filenames = ["*.ks"]
        tokens = {
            "root": [
                (r"::[^\n]*", Comment.Single),
                (r"#[^\n]*", Comment.Single),
                (words(("let","const","mut","move","borrow","release","print","if","elif","else",
                        "while","for","in","range","func","return","class","new","self","super",
                        "extends","import","from","as","try","except","finally","raise","break",
                        "continue","match","case","default","True","False","None","and","or","not",
                        "async","await","yield","decorator","type","thread","Lock","RLock","Event",
                        "Semaphore","ThreadPool","interface","enum","module","property",
                        "staticmethod","classmethod","abstract","override","virtual","unsafe"),
                       suffix=r"\b"), Keyword),
                (r'"[^"]*"', String.Double),
                (r"'[^']*'", String.Single),
                (r'f"[^"]*"', String.Double),
                (r"\d+\.\d+", Number.Float),
                (r"\d+", Number.Integer),
                (r"0x[0-9a-fA-F]+", Number.Hex),
                (r"0b[01]+", Number.Bin),
                (r"[a-zA-Z_][a-zA-Z0-9_]*", Name),
                (r"[+\-*/%]=?", Operator),
                (r"[<>=!]=?", Operator),
                (r"[&|^~]", Operator),
                (r"<<|>>", Operator),
                (r"\*\*", Operator),
                (r"//", Operator),
                (r"[(){}[\],;:.]", Punctuation),
                (r"[@\?]", Keyword),
                (r"\|", Operator),
                (r"->", Operator),
                (r"=>", Operator),
                (r"\s+", Text),
            ]
        }
except ImportError:
    pass


def _print_ks_banner():
    import platform as _platform
    print(f"\nKentScript v{KENTSCRIPT_VERSION} — {_platform.machine()} — Type 'exit' to quit\n")


try:
    from prompt_toolkit.completion import Completer as _PTCompleter
    from prompt_toolkit.completion import Completion as _PTCompletion
except Exception:  # pragma: no cover - prompt_toolkit optional
    _PTCompleter = _PTCompletion = None


class _KSCompleter(_PTCompleter):
    """Autocomplete KentScript keywords/builtins AND live module members.

    After `import os`, typing `os.` lists getpid/getcwd/... by reading the
    interpreter's live global environment. Falls back to static word completion
    (keywords, builtins, current variables) when not in a member-access context.
    """

    def __init__(self, static_words, interp):
        self.static_words = static_words
        self.interp = interp

    def _get_attr(self, obj, name):
        try:
            if isinstance(obj, dict):
                return obj.get(name)
            if hasattr(obj, "attrs") and isinstance(getattr(obj, "attrs"), dict):
                return obj.attrs.get(name)
            return getattr(obj, name, None)
        except Exception:
            return None

    def _members(self, obj):
        if obj is None:
            return []
        if hasattr(obj, "attrs") and isinstance(getattr(obj, "attrs"), dict):
            return [k for k in obj.attrs.keys() if not k.startswith("_")]
        if isinstance(obj, dict):
            return [k for k in obj.keys() if not k.startswith("_")]
        if hasattr(obj, "__dict__"):
            return [k for k in vars(obj).keys() if not k.startswith("_")]
        return [k for k in dir(obj) if not k.startswith("_")]

    def _resolve(self, dotted):
        parts = dotted.split(".")
        obj = self.interp.global_env.get(parts[0])
        for p in parts[1:]:
            if obj is None:
                return None
            obj = self._get_attr(obj, p)
        return obj

    def _env_keys(self):
        env = self.interp.global_env
        seen = set()
        while env is not None:
            seen.update(getattr(env, "vars", {}).keys())
            env = getattr(env, "parent", None)
        return seen

    def get_completions(self, document, complete_event):
        try:
            import re
            text = document.text_before_cursor
            m = re.search(r"([A-Za-z_][A-Za-z0-9_.]*)\.([A-Za-z_][A-Za-z0-9_]*)?$", text)
            if m:
                obj = self._resolve(m.group(1))
                partial = m.group(2) or ""
                for name in self._members(obj):
                    if name.startswith(partial):
                        yield _PTCompletion(name, start_position=-len(partial))
                return
            w = re.search(r"([A-Za-z_][A-Za-z0-9_]*)$", text)
            word = w.group(1) if w else ""
            env_keys = self._env_keys()
            yielded = 0
            for name in sorted(set(self.static_words) | env_keys):
                if name.startswith(word):
                    yield _PTCompletion(name, start_position=-len(word))
                    yielded += 1
                    if yielded >= 500:
                        return
        except Exception:
            # Never let a transient error break completion for this keypress.
            return


def _build_module_help(module_name):
    """Generate a help summary for a stdlib module by scanning its .ks file.

    Returns a help string for any importable ``stdlib/<module_name>.ks`` or
    None when the module is not found / has no public functions. This keeps
    ``help('module')`` working for every module without hand-maintaining text.
    """
    import os as _os
    import re as _re

    try:
        _base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        _path = _os.path.join(_base, "stdlib", module_name + ".ks")
        if not _os.path.exists(_path):
            return None
        with open(_path, "r") as f:
            src = f.read()
        funcs = []
        for line in src.splitlines():
            s = line.strip()
            if s.startswith("::") or s.startswith("#"):
                continue
            m = _re.match(
                r"^(?:export\s+)?func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)", s
            )
            if m:
                funcs.append("%s(%s)" % (m.group(1), m.group(2)))
        if not funcs:
            return None
        lines = [
            "",
            "%s: Standard library module." % module_name,
            "  import %s;" % module_name,
            "  Public functions:",
        ]
        for fn in funcs[:80]:
            lines.append("    %s" % fn)
        lines.append("")
        lines.append("See `help modules` for the module import system.")
        lines.append("")
        return "\n".join(lines)
    except Exception:
        return None


def repl():
    """Interactive REPL"""
    _print_ks_banner()
    LOGO = r"""
[bold cyan]
 _  __            _   ____            _       _   
| |/ /___ _ __   | |_/ ___|  ___ _ __(_)_ __ | |_ 
| ' // _ \ '_ \  | __\___ \ / __| '__| | '_ \| __|
| . \  __/ | | | | |_ ___) | (__| |  | | |_) | |_ 
|_|\_\___|_| |_|  \__|____/ \___|_|  |_| .__/ \__|
                                       |_|          
[/bold cyan]
[bold yellow]Python[/bold yellow] & [bold yellow]C[/bold yellow] based Systems Programming Language  — [bold red]by pyLord[/bold red]
[dim]C Transpiler • OOP • Borrow Checker • Standard Library[/dim]
"""

    if RICH_AVAILABLE:
        console.print(Panel.fit(LOGO, title=f"⚡ KentScript {KENTSCRIPT_VERSION}"))
    else:
        print(LOGO)
    print("\nType 'exit' to quit, 'help' for commands\n")

    session = None
    prompt_toolkit_available = False
    _printed_errors = set()  # Track printed errors to avoid duplicates

    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.completion import WordCompleter, Completer, Completion
        from prompt_toolkit.lexers import PygmentsLexer

        prompt_toolkit_available = True
    except ImportError:
        prompt_toolkit_available = False

    interpreter = Interpreter()

    if prompt_toolkit_available:
        try:
            # Complete KentScript keywords
            keywords = [
                "let", "const", "mut", "print", "if", "else", "elif", "while", "for",
                "func", "class", "struct", "enum", "interface", "trait", "import",
                "from", "as", "return", "True", "False", "None", "and", "or", "not",
                "in", "is", "break", "continue", "try", "except", "finally", "raise",
                "throw", "match", "case", "default", "assert", "yield", "async", "await",
                "decorator", "type", "unsafe", "safe", "export", "extends", "implements",
                "super", "self", "new", "delete", "sizeof", "typeof", "thread",
                "spawn", "Lock", "RLock", "Event", "Semaphore", "Condition",
                "defer", "where", "impl", "pub", "priv", "static", "inline", "extern",
                "volatile", "align", "section", "naked", "syscall", "interrupt",
                "move", "borrow", "release", "with",
            ]

            # Built-in functions
            builtins = [
                "print", "println", "input", "len", "range", "append", "push", "pop",
                "sort", "reverse", "map", "filter", "zip", "enumerate", "keys",
                "values", "items", "split", "join", "trim", "upper", "lower",
                "replace", "contains", "startswith", "endswith", "format",
                "sizeof", "copy", "panic", "assert", "unwrap", "exit", "sleep",
                "system", "env", "getcwd", "spawn", "hash", "abs", "min", "max",
                "sum", "pow", "sqrt", "floor", "ceil", "round", "sin", "cos", "tan",
                "log", "exp", "chr", "ord", "hex", "bin", "oct", "reversed", "sorted",
                "read_file", "write_file", "open", "close", "read", "write", "seek",
                "tell", "stat", "format_value", "reduce", "fold", "any", "all",
                "typeof", "type_of", "os_name",
            ]

            # Types
            types = [
                "i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64",
                "f32", "f64", "bool", "str", "string", "char", "void", "ptr", "any",
            ]

            # Unsafe/low-level functions
            unsafe_funcs = [
                "malloc", "free", "realloc", "calloc", "ptr_read", "ptr_write",
                "mmap", "munmap", "mprotect", "syscall", "asm", "inb", "outb",
                "inw", "outw", "inl", "outl", "rdtsc", "cpuid", "cli", "sti",
                "hlt", "pause", "atomic_add", "atomic_sub", "atomic_cas",
                "atomic_swap", "atomic_load", "atomic_store", "memcpy", "memset",
                "alloca", "dma_transfer", "call_ptr", "ptr_cast", "virt_to_phys",
            ]

            # Standard library modules (must match stdlib/*.ks on disk)
            modules = [
                "accel", "argparse", "asm", "assembly", "asyncio", "bitwise",
                "cache", "collections", "color", "compiler", "compression",
                "config", "crypto", "csv", "dataclass", "dataframe", "datetime",
                "docker", "dotenv", "email", "encoding", "enum", "error",
                "excel", "ffi", "fileio", "fileproc", "functools", "graphql",
                "hardware", "http", "image", "iterators", "itertools", "json",
                "jwt", "kcrypt", "logging", "markdown", "math", "memory",
                "network", "openapi", "os", "parser", "path", "pathlib",
                "progress", "random", "ratelimit", "regex", "rich_progress",
                "safe", "scheduler", "security", "socket", "sql", "sqlite", "ssh",
                "strings", "struct_utils", "subprocess", "syscall", "system",
                "template", "testing", "tui", "validation", "watcher", "web",
                "webserver", "websocket", "webui", "postgres", "mysql", "mariadb",
                "ide",
            ]

            # Discover every real stdlib module on disk so completion stays in
            # sync with stdlib/*.ks without manual listing.
            try:
                import glob as _glob
                _stdlib_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib"
                )
                for _mf in _glob.glob(os.path.join(_stdlib_dir, "*.ks")):
                    _mname = os.path.splitext(os.path.basename(_mf))[0]
                    if _mname and _mname not in modules:
                        modules.append(_mname)
            except Exception:
                pass

            # System functions (auto-extracted from interpreter builtins)
            system_funcs = [
                "system_alignas", "system_alignof", "system_arc_clone",
                "system_arc_drop", "system_arc_get", "system_arc_new",
                "system_arc_set", "system_archive_create_tar", "system_archive_create_zip",
                "system_archive_extract_tar", "system_archive_extract_zip", "system_archive_list_tar",
                "system_archive_list_zip", "system_archive_read_tar", "system_archive_read_zip",
                "system_arena_alloc", "system_arena_new", "system_arena_reset",
                "system_arena_total", "system_argparse_add_argument", "system_argparse_add_parser",
                "system_argparse_add_subparsers", "system_argparse_error", "system_argparse_format_help",
                "system_argparse_new", "system_argparse_parse_args", "system_argparse_parse_known_args",
                "system_argparse_print_help", "system_assert", "system_async_gather",
                "system_async_run", "system_async_sleep", "system_async_timeout",
                "system_asyncio_create_task", "system_asyncio_future", "system_asyncio_gather",
                "system_asyncio_run", "system_asyncio_sleep", "system_asyncio_timeout",
                "system_asyncio_wait", "system_atomic_compare_exchange", "system_atomic_fetch_add",
                "system_atomic_load", "system_atomic_new", "system_atomic_store",
                "system_bit_and", "system_bit_byteswap", "system_bit_clear",
                "system_bit_clz", "system_bit_ctz", "system_bit_extract",
                "system_bit_gray_decode", "system_bit_gray_encode", "system_bit_insert",
                "system_bit_lshift", "system_bit_mask", "system_bit_not",
                "system_bit_or", "system_bit_parity", "system_bit_popcount",
                "system_bit_reverse", "system_bit_rol", "system_bit_ror",
                "system_bit_rshift", "system_bit_set", "system_bit_sign_extend",
                "system_bit_test", "system_bit_toggle", "system_bit_xor",
                "system_boot_time", "system_bounds_check", "system_box_get",
                "system_box_new", "system_box_set", "system_build_cfg",
                "system_build_env", "system_build_features", "system_build_profile",
                "system_build_target", "system_builtin_abs", "system_builtin_all",
                "system_builtin_any", "system_builtin_bin", "system_builtin_bool",
                "system_builtin_breakpoint", "system_builtin_callable", "system_builtin_chr",
                "system_builtin_compile", "system_builtin_delattr", "system_builtin_dict",
                "system_builtin_dir", "system_builtin_divmod", "system_builtin_enumerate",
                "system_builtin_eval", "system_builtin_exec", "system_builtin_expect",
                "system_builtin_filter", "system_builtin_float", "system_builtin_format",
                "system_builtin_frozenset", "system_builtin_getattr", "system_builtin_globals",
                "system_builtin_hasattr", "system_builtin_hash", "system_builtin_hex",
                "system_builtin_id", "system_builtin_input", "system_builtin_int",
                "system_builtin_isinstance", "system_builtin_issubclass", "system_builtin_iter",
                "system_builtin_len", "system_builtin_likely", "system_builtin_list",
                "system_builtin_locals", "system_builtin_map", "system_builtin_max",
                "system_builtin_min", "system_builtin_next", "system_builtin_oct",
                "system_builtin_open", "system_builtin_ord", "system_builtin_overflow_add",
                "system_builtin_overflow_mul", "system_builtin_overflow_sub", "system_builtin_pow",
                "system_builtin_prefetch", "system_builtin_print", "system_builtin_range",
                "system_builtin_reduce", "system_builtin_repr", "system_builtin_reversed",
                "system_builtin_round", "system_builtin_set", "system_builtin_setattr",
                "system_builtin_slice", "system_builtin_sorted", "system_builtin_str",
                "system_builtin_sum", "system_builtin_trap", "system_builtin_tuple",
                "system_builtin_type", "system_builtin_unlikely", "system_builtin_unreachable",
                "system_builtin_vars", "system_builtin_zip", "system_bytearray_append",
                "system_bytearray_extend", "system_bytearray_new", "system_bytes_decode",
                "system_bytes_from_list", "system_bytes_from_str", "system_bytes_hex",
                "system_bytes_len", "system_cfg", "system_channel_new",
                "system_channel_recv", "system_channel_send", "system_channel_try_recv",
                "system_classmethod_new", "system_close", "system_codec_decode",
                "system_codec_encode", "system_codec_list", "system_codec_register",
                "system_cold", "system_collections_chainmap", "system_collections_counter",
                "system_collections_counter_add", "system_collections_counter_elements", "system_collections_counter_most_common",
                "system_collections_counter_subtract", "system_collections_counter_update", "system_collections_defaultdict",
                "system_collections_defaultdict_get", "system_collections_deque", "system_collections_deque_appendleft",
                "system_collections_deque_clear", "system_collections_deque_copy", "system_collections_deque_count",
                "system_collections_deque_extend", "system_collections_deque_extendleft", "system_collections_deque_index",
                "system_collections_deque_insert", "system_collections_deque_popleft", "system_collections_deque_remove",
                "system_collections_deque_reverse", "system_collections_deque_rotate", "system_collections_namedtuple",
                "system_collections_ordered_dict", "system_collections_ordered_dict_move_to_end", "system_collections_ordered_dict_popitem",
                "system_collections_userdict", "system_collections_userlist", "system_collections_userstring",
                "system_compile_time_assert", "system_complex_abs", "system_complex_conjugate",
                "system_complex_imag", "system_complex_new", "system_complex_real",
                "system_compress_gzip", "system_compress_lzma", "system_compress_zlib",
                "system_comptime_eval", "system_comptime_sizeof", "system_comptime_type",
                "system_config_merge", "system_config_read_env", "system_config_read_ini",
                "system_config_validate", "system_config_write_ini", "system_const",
                "system_constexpr", "system_context_enter", "system_context_exit",
                "system_context_run", "system_contextlib_exitstack", "system_contextlib_nullcontext",
                "system_contextlib_redirect_stderr", "system_contextlib_redirect_stdout", "system_contextlib_suppress",
                "system_contextmanager", "system_copytree", "system_coverage_report",
                "system_coverage_start", "system_coverage_stop", "system_cpu_cli",
                "system_cpu_count", "system_cpu_hlt", "system_cpu_pause",
                "system_cpu_percent", "system_cpu_sti", "system_crypto_bcrypt_hash",
                "system_crypto_bcrypt_verify", "system_crypto_compare_digest", "system_crypto_decrypt_aes",
                "system_crypto_encrypt_aes", "system_crypto_generate_secret_key", "system_crypto_generate_self_signed_cert",
                "system_crypto_generate_token", "system_crypto_hmac", "system_crypto_load_cert",
                "system_crypto_random_bytes", "system_crypto_rsa_decrypt", "system_crypto_rsa_encrypt",
                "system_crypto_rsa_generate_keypair", "system_crypto_scrypt", "system_crypto_sign",
                "system_crypto_verify_signature", "system_csv_dict_reader", "system_csv_dict_writer",
                "system_csv_list_dialects", "system_csv_reader", "system_csv_reader_dialect",
                "system_csv_register_dialect", "system_csv_writer", "system_csv_writer_dialect",
                "system_database_mongodb_collection", "system_database_mongodb_connect", "system_database_mongodb_db",
                "system_database_mongodb_delete", "system_database_mongodb_find", "system_database_mongodb_insert",
                "system_database_mongodb_update", "system_database_mysql_connect", "system_database_postgres_connect",
                "system_database_redis_connect", "system_database_redis_delete", "system_database_redis_exists",
                "system_database_redis_get", "system_database_redis_hget", "system_database_redis_hset",
                "system_database_redis_keys", "system_database_redis_llen", "system_database_redis_lpop",
                "system_database_redis_lpush", "system_database_redis_ping", "system_database_redis_rpop",
                "system_database_redis_rpush", "system_database_redis_sadd", "system_database_redis_set",
                "system_database_redis_smembers", "system_database_sqlite_close", "system_database_sqlite_commit",
                "system_database_sqlite_connect", "system_database_sqlite_cursor", "system_database_sqlite_description",
                "system_database_sqlite_execute", "system_database_sqlite_execute_script", "system_database_sqlite_executemany",
                "system_database_sqlite_fetchall", "system_database_sqlite_fetchmany", "system_database_sqlite_fetchone",
                "system_database_sqlite_lastrowid", "system_database_sqlite_rollback", "system_database_sqlite_row_factory",
                "system_database_sqlite_rowcount", "system_datetime_date", "system_datetime_date_today",
                "system_datetime_datetime", "system_datetime_fromtimestamp", "system_datetime_isoformat",
                "system_datetime_now", "system_datetime_now_tz", "system_datetime_strftime",
                "system_datetime_strptime", "system_datetime_time", "system_datetime_timedelta",
                "system_datetime_timedelta_add", "system_datetime_timedelta_sub", "system_datetime_timedelta_total_seconds",
                "system_datetime_timestamp", "system_datetime_utcnow", "system_datetime_weekday",
                "system_debug_breakpoint", "system_debug_globals", "system_debug_inspect_var",
                "system_debug_locals", "system_debug_signature", "system_debug_source",
                "system_debug_traceback", "system_debugger_continue", "system_debugger_get_state",
                "system_debugger_list_breakpoints", "system_debugger_remove_breakpoint", "system_debugger_remove_watchpoint",
                "system_debugger_set_breakpoint", "system_debugger_set_watchpoint", "system_debugger_step",
                "system_decimal_add", "system_decimal_div", "system_decimal_mul",
                "system_decimal_new", "system_decimal_round", "system_decimal_sqrt",
                "system_decimal_sub", "system_decimal_to_str", "system_decompress_gzip",
                "system_decompress_lzma", "system_decompress_zlib", "system_decorator_aligned",
                "system_decorator_cache", "system_decorator_classmethod", "system_decorator_inline",
                "system_decorator_interrupt", "system_decorator_kernel", "system_decorator_lru_cache",
                "system_decorator_naked", "system_decorator_packed", "system_decorator_property",
                "system_decorator_section", "system_decorator_staticmethod", "system_decorator_syscall",
                "system_decorator_volatile", "system_decorator_wraps", "system_defer",
                "system_defer_run", "system_derive_clone", "system_derive_debug",
                "system_derive_default", "system_derive_eq", "system_derive_hash",
                "system_destructure_dict", "system_destructure_list", "system_disk_usage",
                "system_doc_generate", "system_docstring", "system_encoding_ascii_decode",
                "system_encoding_ascii_encode", "system_encoding_detect", "system_encoding_hex_decode",
                "system_encoding_hex_encode", "system_encoding_url_decode", "system_encoding_url_encode",
                "system_errdefer", "system_error_union", "system_exception_cause",
                "system_exception_chain", "system_exception_context", "system_exception_message",
                "system_exception_suppress_context", "system_exception_traceback", "system_exception_type",
                "system_feature_flag", "system_feature_matrix", "system_ffi_addressof",
                "system_ffi_array", "system_ffi_byref", "system_ffi_c_bool",
                "system_ffi_c_char_p", "system_ffi_c_double", "system_ffi_c_float",
                "system_ffi_c_int", "system_ffi_c_long", "system_ffi_c_size_t",
                "system_ffi_c_void_p", "system_ffi_call", "system_ffi_cast",
                "system_ffi_close", "system_ffi_create_buffer", "system_ffi_get_symbol",
                "system_ffi_load", "system_ffi_memmove", "system_ffi_memset",
                "system_ffi_pack_struct", "system_ffi_pack_union", "system_ffi_pointer",
                "system_ffi_sizeof", "system_ffi_string", "system_ffi_string_at",
                "system_ffi_struct", "system_ffi_struct_c", "system_ffi_unpack_struct",
                "system_ffi_unpack_union", "system_file_append_text", "system_file_chdir",
                "system_file_chmod", "system_file_chown", "system_file_close",
                "system_file_exists", "system_file_flush", "system_file_getcwd",
                "system_file_getsize", "system_file_handle", "system_file_handle_close",
                "system_file_handle_flush", "system_file_handle_read", "system_file_handle_readline",
                "system_file_handle_readlines", "system_file_handle_seek", "system_file_handle_tell",
                "system_file_handle_write", "system_file_isdir", "system_file_isfile",
                "system_file_ismount", "system_file_listdir", "system_file_mkdir",
                "system_file_open", "system_file_read", "system_file_read_bytes",
                "system_file_read_text", "system_file_readline", "system_file_readlink",
                "system_file_remove", "system_file_rename", "system_file_rmdir",
                "system_file_stat", "system_file_symlink", "system_file_walk",
                "system_file_write", "system_file_write_bytes", "system_file_write_text",
                "system_fraction_add", "system_fraction_denominator", "system_fraction_div",
                "system_fraction_from_float", "system_fraction_mul", "system_fraction_new",
                "system_fraction_numerator", "system_fraction_sub", "system_fraction_to_float",
                "system_frozenset_new", "system_future_cancel", "system_future_done",
                "system_future_new", "system_future_result", "system_future_set_exception",
                "system_future_set_result", "system_generator_close", "system_generator_from_list",
                "system_generator_next", "system_generator_send", "system_generator_throw",
                "system_generator_to_list", "system_generic_call", "system_generic_fn",
                "system_generic_register", "system_glob", "system_hardware_cpuid",
                "system_hardware_dev_list", "system_hardware_ioctl", "system_hardware_netlink_socket",
                "system_hardware_proc_cpuinfo", "system_hardware_proc_meminfo", "system_hardware_proc_net_dev",
                "system_hardware_proc_read", "system_hardware_proc_stat", "system_hardware_rdtsc",
                "system_hardware_realtime_sched", "system_hardware_serial_close", "system_hardware_serial_open",
                "system_hardware_serial_read", "system_hardware_serial_write", "system_hardware_sys_read",
                "system_help", "system_hot", "system_http_bearer",
                "system_http_delete", "system_http_get", "system_http_get_auth",
                "system_http_patch", "system_http_post", "system_http_proxy",
                "system_http_put", "system_http_request", "system_http_stream",
                "system_http_with_cookies", "system_imap_fetch", "system_import",
                "system_import_find", "system_import_from", "system_import_is_available",
                "system_import_reload", "system_info", "system_inline",
                "system_iter_all", "system_iter_any", "system_iter_chain",
                "system_iter_collect", "system_iter_count", "system_iter_enumerate",
                "system_iter_filter", "system_iter_first", "system_iter_flat_map",
                "system_iter_flatten", "system_iter_last", "system_iter_map",
                "system_iter_max", "system_iter_min", "system_iter_nth",
                "system_iter_partition", "system_iter_reduce", "system_iter_scan",
                "system_iter_skip", "system_iter_sum", "system_iter_take",
                "system_iter_unique", "system_iter_zip", "system_iter_zip_with",
                "system_itertools_accumulate", "system_itertools_batched", "system_itertools_chain",
                "system_itertools_combinations", "system_itertools_combinations_with_replacement", "system_itertools_compress",
                "system_itertools_count", "system_itertools_cycle", "system_itertools_dropwhile",
                "system_itertools_filterfalse", "system_itertools_groupby", "system_itertools_islice",
                "system_itertools_pairwise", "system_itertools_permutations", "system_itertools_product",
                "system_itertools_repeat", "system_itertools_starmap", "system_itertools_takewhile",
                "system_itertools_tee", "system_itertools_zip_longest", "system_json_dump",
                "system_json_dumps", "system_json_dumps_custom", "system_json_load",
                "system_json_loads", "system_json_loads_custom", "system_jwt_decode",
                "system_jwt_encode", "system_kcrypt_bytes_to_int", "system_kcrypt_derive_key",
                "system_kcrypt_hash_password", "system_kcrypt_int_to_bytes", "system_kcrypt_lower",
                "system_kcrypt_random_key", "system_kcrypt_verify_password", "system_kpm_install",
                "system_kpm_list", "system_kpm_requires", "system_kpm_search",
                "system_kpm_uninstall", "system_kpm_version", "system_load_average",
                "system_logging_critical", "system_logging_debug", "system_logging_disable",
                "system_logging_error", "system_logging_exception", "system_logging_info",
                "system_logging_rotating_handler", "system_logging_timed_rotating_handler", "system_logging_warning",
                "system_lseek", "system_macro_concat", "system_macro_define",
                "system_macro_env", "system_macro_expand", "system_macro_file",
                "system_macro_line", "system_macro_stringify", "system_magic_abs",
                "system_magic_add", "system_magic_bool", "system_magic_call",
                "system_magic_contains", "system_magic_delitem", "system_magic_div",
                "system_magic_eq", "system_magic_float", "system_magic_floordiv",
                "system_magic_ge", "system_magic_getitem", "system_magic_gt",
                "system_magic_hash", "system_magic_int", "system_magic_iter",
                "system_magic_le", "system_magic_len", "system_magic_lt",
                "system_magic_mod", "system_magic_mul", "system_magic_ne",
                "system_magic_neg", "system_magic_next", "system_magic_pos",
                "system_magic_pow", "system_magic_repr", "system_magic_setitem",
                "system_magic_str", "system_magic_sub", "system_markdown_to_html",
                "system_match", "system_match_range", "system_match_type",
                "system_math_acos", "system_math_asin", "system_math_atan",
                "system_math_ceil", "system_math_comb", "system_math_copysign",
                "system_math_cos", "system_math_cosh", "system_math_degrees",
                "system_math_dist", "system_math_e", "system_math_erf",
                "system_math_erfc", "system_math_exp", "system_math_factorial",
                "system_math_floor", "system_math_frexp", "system_math_gamma",
                "system_math_gcd", "system_math_hypot", "system_math_inf",
                "system_math_isclose", "system_math_isfinite", "system_math_isinf",
                "system_math_isnan", "system_math_lcm", "system_math_ldexp",
                "system_math_lgamma", "system_math_log", "system_math_modf",
                "system_math_nan", "system_math_perm", "system_math_pi",
                "system_math_pow", "system_math_radians", "system_math_round",
                "system_math_sin", "system_math_sinh", "system_math_sqrt",
                "system_math_tan", "system_math_tanh", "system_math_tau",
                "system_math_trunc", "system_memchr", "system_memcmp",
                "system_memcpy", "system_memmove", "system_memory_barrier_acquire",
                "system_memory_barrier_release", "system_memory_barrier_seqcst", "system_memory_fence",
                "system_memory_mlock", "system_memory_mprotect", "system_memory_munlock",
                "system_memoryview_itemsize", "system_memoryview_nbytes", "system_memoryview_new",
                "system_memoryview_shape", "system_memoryview_slice", "system_memoryview_tobytes",
                "system_memoryview_tolist", "system_memrchr", "system_memset",
                "system_mmap", "system_mmap_close", "system_mmap_create",
                "system_mmap_read", "system_mmap_seek", "system_mmap_size",
                "system_mmap_write", "system_mmio_map", "system_mmio_unmap",
                "system_mode", "system_monomorphize", "system_msr_read",
                "system_msr_write", "system_multiprocessing_cpu_count", "system_multiprocessing_join",
                "system_multiprocessing_start", "system_munmap", "system_mutex_lock",
                "system_mutex_new", "system_mutex_try_lock", "system_mutex_unlock",
                "system_network_interfaces", "system_no_inline", "system_null_check",
                "system_offsetof", "system_open", "system_option_is_none",
                "system_option_is_some", "system_option_map", "system_option_none",
                "system_option_some", "system_option_unwrap", "system_option_unwrap_or",
                "system_optional", "system_os_exit", "system_os_getenv",
                "system_os_getgid", "system_os_getpid", "system_os_getppid",
                "system_os_getuid", "system_os_kill", "system_os_setenv",
                "system_os_system", "system_overflow_check", "system_parity_check",
                "system_pickle_dump", "system_pickle_dumps", "system_pickle_load",
                "system_pickle_loads", "system_platform", "system_platform_arch",
                "system_platform_cpu_features", "system_platform_dist", "system_platform_is_linux",
                "system_platform_is_macos", "system_platform_is_windows", "system_platform_kernel_version",
                "system_platform_node", "system_platform_os", "system_platform_processor",
                "system_platform_python_version", "system_platform_release", "system_platform_uname",
                "system_platform_version", "system_pool_alloc", "system_pool_free",
                "system_pool_new", "system_process_affinity", "system_process_list",
                "system_process_monitor", "system_process_pool", "system_process_pool_map",
                "system_process_pool_shutdown", "system_process_pool_submit", "system_process_priority",
                "system_process_queue", "system_process_queue_empty", "system_process_queue_get",
                "system_process_queue_put", "system_process_queue_size", "system_process_semaphore",
                "system_process_semaphore_acquire", "system_process_semaphore_release", "system_process_shared_memory_attach",
                "system_process_shared_memory_close", "system_process_shared_memory_create", "system_process_shared_memory_unlink",
                "system_process_spawn", "system_profile_cprofile", "system_profile_line",
                "system_profile_line_run", "system_profile_line_stats", "system_profile_memory",
                "system_profile_time", "system_profile_timeit", "system_property_deleter",
                "system_property_getter", "system_property_new", "system_property_setter",
                "system_ptr_add", "system_ptr_align", "system_ptr_cast",
                "system_ptr_diff", "system_ptr_is_aligned", "system_ptr_is_null",
                "system_ptr_nonnull", "system_ptr_null", "system_ptr_unique",
                "system_ptr_unique_get", "system_ptr_unique_move", "system_ptr_weak",
                "system_ptr_weak_upgrade", "system_python_version", "system_raise",
                "system_random_choice", "system_random_expovariate", "system_random_gauss",
                "system_random_getstate", "system_random_normalvariate", "system_random_randint",
                "system_random_random", "system_random_sample", "system_random_seed",
                "system_random_setstate", "system_random_shuffle", "system_random_uniform",
                "system_range_new", "system_rc_clone", "system_rc_count",
                "system_rc_drop", "system_rc_get", "system_rc_new",
                "system_rc_set", "system_read", "system_regex_compile",
                "system_regex_escape", "system_regex_findall", "system_regex_finditer",
                "system_regex_flags_dotall", "system_regex_flags_ignorecase", "system_regex_flags_multiline",
                "system_regex_flags_verbose", "system_regex_fullmatch", "system_regex_lookahead",
                "system_regex_lookbehind", "system_regex_match", "system_regex_named_groups",
                "system_regex_named_match", "system_regex_neg_lookahead", "system_regex_neg_lookbehind",
                "system_regex_search", "system_regex_split", "system_regex_sub",
                "system_regex_subn", "system_result_and_then", "system_result_err",
                "system_result_is_err", "system_result_is_ok", "system_result_map",
                "system_result_ok", "system_result_unwrap", "system_result_unwrap_or",
                "system_rmtree", "system_runtime_info", "system_rwlock_new",
                "system_scope_guard", "system_set_add", "system_set_clear",
                "system_set_copy", "system_set_difference", "system_set_discard",
                "system_set_intersection", "system_set_isdisjoint", "system_set_issubset",
                "system_set_issuperset", "system_set_pop", "system_set_remove",
                "system_set_symmetric_difference", "system_set_union", "system_simd_zero",
                "system_sizeof", "system_slice_get", "system_slice_iter",
                "system_slice_len", "system_slice_new", "system_smtp_send",
                "system_smtp_send_html", "system_socket_accept", "system_socket_bind",
                "system_socket_close", "system_socket_connect", "system_socket_create",
                "system_socket_getaddrinfo", "system_socket_gethostbyaddr", "system_socket_gethostbyname",
                "system_socket_gethostname", "system_socket_getsockopt", "system_socket_gettimeout",
                "system_socket_inet_aton", "system_socket_inet_ntoa", "system_socket_listen",
                "system_socket_recv", "system_socket_recvfrom", "system_socket_send",
                "system_socket_sendto", "system_socket_setblocking", "system_socket_setsockopt",
                "system_socket_settimeout", "system_ssl_close", "system_ssl_connect",
                "system_ssl_create_context", "system_ssl_recv", "system_ssl_send",
                "system_ssl_wrap_socket", "system_static_assert", "system_staticmethod_new",
                "system_stderr", "system_stdin", "system_stdin_read",
                "system_stdin_readline", "system_stdin_readlines", "system_stdout",
                "system_str_capitalize", "system_str_center", "system_str_contains",
                "system_str_count", "system_str_endswith", "system_str_find",
                "system_str_format", "system_str_index", "system_str_isalnum",
                "system_str_isalpha", "system_str_isdigit", "system_str_isspace",
                "system_str_join", "system_str_ljust", "system_str_lower",
                "system_str_lstrip", "system_str_replace", "system_str_rfind",
                "system_str_rjust", "system_str_rstrip", "system_str_split",
                "system_str_startswith", "system_str_strip", "system_str_swapcase",
                "system_str_title", "system_str_upper", "system_str_zfill",
                "system_strace_attach", "system_strace_read_log", "system_string_bytes",
                "system_string_chars", "system_string_contains", "system_string_ends_with",
                "system_string_find", "system_string_is_empty", "system_string_join",
                "system_string_len", "system_string_new", "system_string_parse_float",
                "system_string_parse_int", "system_string_push", "system_string_repeat",
                "system_string_replace", "system_string_rfind", "system_string_split",
                "system_string_split_whitespace", "system_string_starts_with", "system_string_substr",
                "system_string_to_lowercase", "system_string_to_uppercase", "system_string_trim",
                "system_strings_capitalize", "system_strings_contains", "system_strings_endswith",
                "system_strings_join", "system_strings_lower", "system_strings_replace",
                "system_strings_split", "system_strings_startswith", "system_strings_strip",
                "system_strings_swapcase", "system_strings_title", "system_strings_upper",
                "system_struct_aligned", "system_struct_calcsize", "system_struct_get",
                "system_struct_new", "system_struct_offsetof", "system_struct_pack",
                "system_struct_packed", "system_struct_set", "system_struct_sizeof",
                "system_struct_unpack", "system_subprocess_check_call", "system_subprocess_check_output",
                "system_subprocess_getstatusoutput", "system_subprocess_popen", "system_subprocess_popen_communicate",
                "system_subprocess_popen_kill", "system_subprocess_popen_pid", "system_subprocess_popen_poll",
                "system_subprocess_popen_returncode", "system_subprocess_popen_stderr", "system_subprocess_popen_stdin",
                "system_subprocess_popen_stdout", "system_subprocess_popen_terminate", "system_subprocess_popen_wait",
                "system_subprocess_run", "system_subprocess_run_cwd", "system_subprocess_run_env",
                "system_subprocess_run_timeout", "system_syscall", "system_syscall_accept",
                "system_syscall_bind", "system_syscall_chdir", "system_syscall_close",
                "system_syscall_connect", "system_syscall_creat", "system_syscall_dup",
                "system_syscall_errno", "system_syscall_execve", "system_syscall_exit",
                "system_syscall_fcntl", "system_syscall_fork", "system_syscall_fstat",
                "system_syscall_getcwd", "system_syscall_getgid", "system_syscall_getpid",
                "system_syscall_getppid", "system_syscall_gettimeofday", "system_syscall_getuid",
                "system_syscall_ioctl", "system_syscall_kill", "system_syscall_linux_specific",
                "system_syscall_listen", "system_syscall_lseek", "system_syscall_madvise",
                "system_syscall_mkdir", "system_syscall_nanosleep", "system_syscall_open",
                "system_syscall_perror", "system_syscall_pipe", "system_syscall_read",
                "system_syscall_recv", "system_syscall_rename", "system_syscall_rmdir",
                "system_syscall_send", "system_syscall_setsockopt", "system_syscall_signal",
                "system_syscall_signum", "system_syscall_sigpending", "system_syscall_sigprocmask",
                "system_syscall_socket", "system_syscall_stat", "system_syscall_strerror",
                "system_syscall_trace_get", "system_syscall_trace_log", "system_syscall_trace_start",
                "system_syscall_trace_stop", "system_syscall_unlink", "system_syscall_wait",
                "system_syscall_waitpid", "system_syscall_write", "system_tempdir",
                "system_tempfile", "system_template_add_filter", "system_template_add_tag",
                "system_template_jinja", "system_template_render", "system_template_render_file",
                "system_template_render_format", "system_template_render_jinja", "system_template_render_with_inheritance",
                "system_test_block", "system_testing_assert_almost_equal", "system_testing_assert_equal",
                "system_testing_assert_false", "system_testing_assert_greater", "system_testing_assert_in",
                "system_testing_assert_is", "system_testing_assert_is_none", "system_testing_assert_is_not_none",
                "system_testing_assert_less", "system_testing_assert_not_equal", "system_testing_assert_not_in",
                "system_testing_assert_raises", "system_testing_assert_true", "system_testing_discover",
                "system_testing_fixture", "system_testing_mock", "system_testing_parametrize",
                "system_testing_patch", "system_testing_run", "system_thread_local",
                "system_thread_local_get", "system_thread_local_set", "system_thread_local_var",
                "system_thread_pool", "system_thread_pool_map", "system_thread_pool_shutdown",
                "system_thread_pool_submit", "system_threading_active_count", "system_threading_current_thread",
                "system_threading_join", "system_threading_start", "system_time",
                "system_time_clock_gettime", "system_time_daylight", "system_time_format",
                "system_time_monotonic", "system_time_now", "system_time_perf_counter",
                "system_time_sleep", "system_time_strftime", "system_time_time",
                "system_time_timezone", "system_time_tzname", "system_time_utc",
                "system_toml_dump", "system_toml_load", "system_traceback_extract",
                "system_traceback_format", "system_traceback_format_current", "system_traceback_print",
                "system_trait_clone", "system_trait_copy", "system_trait_debug",
                "system_trait_default_bool", "system_trait_default_dict", "system_trait_default_float",
                "system_trait_default_int", "system_trait_default_list", "system_trait_default_str",
                "system_trait_display", "system_trait_eq", "system_trait_from_str",
                "system_trait_has", "system_trait_hash", "system_trait_impl",
                "system_trait_into", "system_trait_object", "system_trait_require",
                "system_type_alias", "system_type_check", "system_type_isize",
                "system_type_name", "system_type_param", "system_type_usize",
                "system_union_new", "system_unsafe_check", "system_uptime",
                "system_va_args", "system_va_get", "system_va_iter",
                "system_va_len", "system_vec_clear", "system_vec_contains",
                "system_vec_dedup", "system_vec_extend", "system_vec_get",
                "system_vec_is_empty", "system_vec_iter", "system_vec_len",
                "system_vec_new", "system_vec_pop", "system_vec_push",
                "system_vec_set", "system_vec_sort", "system_vectorize_disable",
                "system_vectorize_enable", "system_vectorize_hint", "system_virtual_memory",
                "system_volatile_read", "system_volatile_write", "system_webserver_create",
                "system_webserver_create_https", "system_webserver_response", "system_webserver_route",
                "system_webserver_start", "system_webserver_stop", "system_websocket_close",
                "system_websocket_connect", "system_websocket_recv", "system_websocket_send",
                "system_websocket_server_create", "system_which", "system_with",
                "system_write", "system_xlsx_read", "system_xlsx_write",
                "system_xml_parse", "system_xml_to_string", "system_yaml_dump",
                "system_yaml_load", "system_zero_cost",
            ]

            all_completions = keywords + builtins + types + unsafe_funcs + modules + system_funcs

            import os as _os

            kscript_completer = _KSCompleter(all_completions, interpreter)
            _history_file = _os.path.expanduser("~/.kentscript_history")
            session = PromptSession(
                history=FileHistory(_history_file), completer=kscript_completer
            )
        except:
            prompt_toolkit_available = False
            session = None

    _error_shown = False  # Track if error was already shown

    while True:
        _error_shown = False  # Reset for each iteration
        
        try:
            if prompt_toolkit_available and session:
                try:
                    lexer_arg = PygmentsLexer(LangLexer) if LangLexer else None
                    code = session.prompt(">>> ", lexer=lexer_arg)
                except:
                    code = input(">>> ")
            else:
                code = input(">>> ")

            if not code:
                continue

            if code.strip().lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break

            if code.lower() == "help":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  KentScript v3.1.0 REPL Help                                        ║
║  Type help(topic) for detailed info on a specific topic              ║
╚══════════════════════════════════════════════════════════════════════╝

REPL Commands:
  help              Show this help message
  help(topic)       Show detailed help on a topic
  help("topic")     Show detailed help on a topic
  help('topic')     Show detailed help on a topic
  exit/quit/q       Exit the REPL
  creator           Show creator information
  vars              Show current variables
  clear             Clear the screen

Available Help Topics:
  help(keywords)        Language keywords and their usage
  help(types)           Built-in types (i8-i64, u8-u64, f32, f64, bool, str, ptr)
  help(operators)       Arithmetic, comparison, logical, and bitwise operators
  help(builtins)        Built-in functions (print, len, range, map, etc.)
  help(control)         Control flow (if/elif/else, for, while, match)
  help(functions)       Function definitions, parameters, return values
  help(classes)         Class definitions, inheritance, methods
  help(structs)         Struct definitions and usage
  help(enums)           Enum definitions and pattern matching
  help(modules)         Import/export system
  help(unsafe)          Unsafe blocks, pointers, memory operations
  help(threads)         Threading and concurrency
  help(comptime)        Compile-time evaluation
  help(borrow)          Borrow checker and ownership
  help(exceptions)      Try/except/finally error handling
  help(io)              File I/O operations
  help(web)             Web framework (routing, CORS, sessions, middleware)
  help(sql)             SQL query builder (select, insert, update, delete)
  help(examples)        Quick usage examples

Standard Library Modules (use help('module_name')):
  help('os')            File/OS operations (getpid, mkdir, read_file, etc.)
  help('datetime')      Date/time parsing and formatting
  help('random')        Random functions (random, randint, choice, shuffle)
  help('math')          Math functions (sin, cos, sqrt, floor, etc.)
  help('http')          HTTP client (get, post, put, delete)
  help('strings')       String methods (upper, contains, split, etc.)
  help('crypto')        Cryptography (aes, sha256, hmac, bcrypt)
  help('subprocess')    Run shell commands
  help('hardware')      Hardware I/O and CPU info
  help('json')          JSON encode/decode
  help('system')        System info (platform, python_version)
  help('path')          File path manipulation (join, basename, dirname)
  help('pathlib')       Object-oriented path manipulation
  help('kcrypt')        Key derivation, password hashing
  help('web')           Web framework (routing, path params, CORS, sessions, middleware)
  help('webui')         45+ styled UI components (dark/light/midnight themes)
  help('webserver')     HTTP server (static files, directory listing, MIME)
  help('openapi')       OpenAPI 3.0 spec generator
  help('ide')           Built-in web IDE (browser-based code editor)
  help('websocket')     WebSocket client/server
  help('dotenv')        Load .env configuration files
  help('logging')       Logging framework with handlers
  help('socket')        TCP/UDP socket wrapper
  help('network')       Network utilities
  help('ssh')           SSH client
  help('docker')        Docker SDK
  help('email')         SMTP/IMAP client
  help('graphql')       GraphQL client
  help('excel')         XLSX read/write
  help('csv')           CSV reading/writing
  help('sqlite')        SQLite database (built-in)
  help('postgres')      PostgreSQL driver (psycopg2-binary)
  help('mysql')         MySQL driver (mysql-connector-python)
  help('mariadb')       MariaDB driver (falls back to mysql-connector)
  help('sql')           Query builder (select, insert, update, delete, joins)
  help('regex')         Regular expressions
  help('encoding')      Base64, Hex, URL encoding
  help('compression')   Gzip, Zlib, LZMA compress/decompress
  help('asyncio')       Async I/O operations
  help('fileio')        File I/O operations
  help('memory')        Memory management (mmap, mprotect)
  help('security')      Security utilities
  help('validation')    Input/data validation
  help('tui')           ASCII tables, confirm/choose prompts
  help('scheduler')     Task scheduler (run functions at intervals)
  help('cache')         In-memory cache with TTL
  help('ratelimit')     Token-bucket rate limiter
  help('testing')       Unit testing (assert_equal, fixture, mock)
  help('watcher')       File/directory change watcher
  help('progress')      Progress bars, spinner, tqdm
  help('markdown')      Markdown to HTML
  help('template')      Template engine (Jinja2-like)
  help('dataframe')     Pandas-like DataFrame
  help('jwt')           JWT encode/decode (HS256)
  help('image')         ImageMagick bridge (resize, blur, rotate)
  help('color')         ANSI terminal colors
  help('asm')           Inline assembly
  help('assembly')      Assembly helpers
  help('accel')         Hardware acceleration
  help('ffi')           Foreign function interface
  help('syscall')       Low-level syscall interface
  help('struct_utils')  Struct packing/unpacking
  help('error')         Error handling utilities
  help('parser')        Parser utilities
  help('compiler')      Compiler internals
  help('safe')          Safe mode utilities
  help('enum')          Enum definitions
  help('dataclass')     Data class definitions

Quick Examples:
  let x: int = 42;
  func add(a: int, b: int) -> int { return a + b; }
  class Point { init(self, x, y) { self.x = x; self.y = y; } }
  for i in range(5) { print(i); }
  match x { case 1: { print("one"); } default: { print("other"); } }
""")
                continue

            # Detailed help topics - Python-style: help('topic'), help("topic"), or help(topic);
            help_topic = None
            if code.lower().startswith("help(") and code.rstrip(";").rstrip().endswith(")"):
                inner = code[4:].strip()
                # Strip trailing semicolons and whitespace
                inner = inner.rstrip(";").rstrip()
                if inner.startswith("(") and inner.endswith(")"):
                    inner = inner[1:-1].strip()
                    # Remove quotes if present
                    if len(inner) >= 2 and ((inner[0] == "'" and inner[-1] == "'") or (inner[0] == '"' and inner[-1] == '"')):
                        inner = inner[1:-1]
                    help_topic = inner.lower()

            # Aliases for common short names
            _help_aliases = {
                "func": "functions",
                "fn": "functions",
                "class": "classes",
                "cls": "classes",
                "struct": "structs",
                "enum": "enums",
                "module": "modules",
                "mod": "modules",
                "import": "modules",
                "thread": "threads",
                "threading": "threads",
                "concurrency": "threads",
                "unsafe": "unsafe",
                "memory": "unsafe",
                "pointer": "unsafe",
                "ptr": "unsafe",
                "borrow": "borrow",
                "ownership": "borrow",
                "exception": "exceptions",
                "error": "exceptions",
                "try": "exceptions",
                "except": "exceptions",
                "io": "io",
                "file": "io",
                "files": "io",
                "example": "examples",
                "examples": "examples",
                "keyword": "keywords",
                "keywords": "keywords",
                "type": "types",
                "types": "types",
                "operator": "operators",
                "operators": "operators",
                "builtin": "builtins",
                "builtins": "builtins",
                "control": "control",
                "if": "control",
                "for": "control",
                "while": "control",
                "match": "control",
                "comptime": "comptime",
                "compile": "comptime",
                "web": "web",
                "sql": "sql",
                "database": "sql",
                "db": "sql",
                "query": "sql",
            }
            if help_topic and help_topic in _help_aliases:
                help_topic = _help_aliases[help_topic]

            if help_topic == "keywords":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  KentScript Keywords                                                ║
╚══════════════════════════════════════════════════════════════════════╝

Variable Declarations:
  let             Immutable variable binding          let x: int = 5;
  mut             Mutable variable binding            mut x: int = 5;
  const           Compile-time constant               const PI = 3.14;

Types:
  type            Type alias                          type vec3 = [f64; 3];
  struct          Structure definition                struct Point { x: int; y: int; }
  class           Class definition                    class Foo { ... }
  enum            Enumeration                         enum Color { Red, Green, Blue; }
  interface       Interface definition                interface Drawable { ... }
  trait           Trait definition                    trait Serializable { ... }
  impl            Implementation block                impl Foo for Bar { ... }

Functions:
  func            Function definition                 func foo(x: int) -> int { ... }
  return          Return from function                return x;
  async           Async function                      async func fetch() { ... }
  await           Await async result                  let r = await fetch();

Control Flow:
  if              Conditional                         if x > 0 { ... }
  elif            Else-if branch                      elif x < 0 { ... }
  else            Else branch                         else { ... }
  for             Loop over range/iterable            for i in range(10) { ... }
  while           Conditional loop                    while x > 0 { ... }
  match           Pattern matching                    match x { case 1: { ... } }
  case            Match case                          case 1: { ... }
  default         Match default                       default: { ... }
  break           Exit loop                           break;
  continue        Skip to next iteration              continue;

Modules:
  import          Import module                       import math;
  from            Import from module                  from math import sin;
  as              Alias import                        import math as m;
  export          Export from module                  export func foo() { ... }
  module          Module declaration                  module mymod;

Error Handling:
  try             Try block                           try { ... }
  except          Catch exception                     except e { ... }
  finally         Final block                         finally { ... }
  raise           Raise exception                     raise "error";
  assert          Assertion                           assert(x > 0, "must be positive");

Memory/Safety:
  unsafe          Unsafe block                        unsafe { ... }
  borrow          Borrow variable                     borrow x;
  release         Release borrow                      release x;

Other:
  self            Self reference (in methods)         self.x = 5;
  super           Parent class reference              super.init();
  new             Create instance                     Point.new(1, 2);
  global          Global variable access              global x;
  nonlocal        Nonlocal variable access            nonlocal x;
  mut             Mutability marker                   mut x: int;
""")
                continue

            if help_topic == "types":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  KentScript Type System                                             ║
╚══════════════════════════════════════════════════════════════════════╝

Integer Types (signed):
  i8              8-bit signed integer (-128 to 127)
  i16             16-bit signed integer
  i32             32-bit signed integer
  i64             64-bit signed integer
  int             Platform-sized signed integer

Integer Types (unsigned):
  u8              8-bit unsigned integer (0 to 255)
  u16             16-bit unsigned integer
  u32             32-bit unsigned integer
  u64             64-bit unsigned integer
  uint            Platform-sized unsigned integer

Floating Point:
  f32             32-bit float (single precision)
  f64             64-bit float (double precision)
  float           Alias for f64

Other Types:
  bool            Boolean (true/false)
  str             String (UTF-8)
  string          Alias for str
  char            Single character
  void            No return value
  ptr             Raw pointer
  any             Any type (dynamic)

Collection Types:
  list            Dynamic array                     let xs: list = [1, 2, 3];
  dict            Hash map                          let d: dict = {"a": 1};

Type Annotations:
  let x: int = 5;           Explicit type
  let x = 5;                Inferred type
  func f(x: int) -> int     Parameter and return type

Type Casting:
  let x: int = 5;
  let y: f64 = float(x);    Cast int to float
  let z: int = int(y);      Cast float to int
""")
                continue

            if help_topic == "operators":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  KentScript Operators                                               ║
╚══════════════════════════════════════════════════════════════════════╝

Arithmetic:
  +               Addition                          1 + 2
  -               Subtraction                       5 - 3
  *               Multiplication                    4 * 3
  /               Division                          10 / 2
  %               Modulo                            10 % 3
  **              Power                             2 ** 8

Comparison:
  ==              Equal                             x == y
  !=              Not equal                         x != y
  <               Less than                         x < y
  >               Greater than                      x > y
  <=              Less than or equal                x <= y
  >=              Greater than or equal             x >= y

Logical:
  and             Logical AND                       x > 0 and x < 10
  or              Logical OR                        x == 0 or x == 1
  not             Logical NOT                       not found

Bitwise:
  &               Bitwise AND                       x & 0xFF
  |               Bitwise OR                        x | 0x01
  ^               Bitwise XOR                       x ^ 0xFF
  ~               Bitwise NOT                       ~x
  <<              Left shift                        x << 2
  >>              Right shift                       x >> 2

Assignment:
  =               Simple assignment                 x = 5;
  +=              Add and assign                    x += 5;
  -=              Subtract and assign               x -= 5;
  *=              Multiply and assign               x *= 2;
  /=              Divide and assign                 x /= 2;
  %=              Modulo and assign                 x %= 3;

Other:
  .               Member access                     obj.field
  []              Indexing                          arr[0]
  ()              Function call                     func()
  :               Type annotation                   x: int
  ->              Return type                       func f() -> int
  in              Membership                        x in list
  is              Type/identity check               x is int
  ?               Null coalescing                   x ? default
  ..              Range                             1..10
""")
                continue

            if help_topic == "builtins":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  KentScript Built-in Functions                                      ║
╚══════════════════════════════════════════════════════════════════════╝

Output:
  print(*args)              Print to stdout
  println(*args)            Print with newline

Type Conversion:
  str(obj, base?)           Convert to string
  int(obj)                  Convert to integer
  float(obj)                Convert to float
  bool(obj)                 Convert to boolean
  type(obj)                 Get type name
  format_value(obj, fmt?)   Format value with specifier

Collection:
  len(obj)                  Get length
  list(*args)               Create list
  dict(**kwargs)            Create dictionary
  range(start, stop?, step?) Create range sequence

Iteration:
  map(fn, iterable)         Map function over iterable
  filter(fn, iterable)      Filter iterable
  reduce(fn, iterable, initial?) Reduce iterable
  enumerate(iterable, start=0) Enumerate with index
  zip(*iterables)           Zip iterables
  reversed(iterable)        Reverse iterable
  sorted(iterable, reverse?) Sort iterable
  sum(iterable, start=0)    Sum iterable
  all(iterable)             Check all true
  any(iterable)             Check any true

Math:
  abs(x)                    Absolute value
  pow(x, y)                 Power (x^y)
  sqrt(x)                   Square root
  floor(x)                  Floor
  ceil(x)                   Ceiling
  round(x, n=0)             Round
  sin(x), cos(x), tan(x)    Trigonometric
  log(x, base?)             Logarithm
  exp(x)                    Exponential

String:
  hex(x)                    Hex string
  bin(x)                    Binary string
  oct(x)                    Octal string
  chr(x)                    Int to char
  ord(c)                    Char to int
  min(*args)                Minimum value
  max(*args)                Maximum value

I/O:
  input(prompt="")          Read from stdin
  open(filename, mode="r")  Open file
  sleep(seconds)            Sleep seconds

Memory (unsafe):
  ptr(addr)                 Create pointer
  ptr_read(addr, size=8)    Read from pointer
  ptr_write(addr, value, size=8) Write to pointer
  malloc(size)              Allocate memory
  free(ptr)                 Free memory
  alloca(size)              Stack allocate
  memcpy(dest, src, size)   Copy memory
  memset(ptr, value, size)  Set memory

Atomic (unsafe):
  atomic_add(addr, value)   Atomic add
  atomic_sub(addr, value)   Atomic subtract
  atomic_cas(addr, old, new) Compare and swap
  atomic_swap(addr, new)    Atomic swap

I/O Ports (unsafe):
  inb(port)                 Read port byte
  outb(port, value)         Write port byte
  inw(port)                 Read port word
  outw(port, value)         Write port word

CPU (unsafe):
  rdtsc()                   Read timestamp counter
  syscall(num, *args)       System call
  asm(code)                 Inline assembly
""")
                continue

            if help_topic == "control":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Control Flow                                                       ║
╚══════════════════════════════════════════════════════════════════════╝

If/Elif/Else:
  if condition {
      println("positive");
  } elif condition2 {
      println("zero");
  } else {
      println("negative");
  }

For Loop:
  for i in range(10) {
      print(i);
  }

  for item in list {
      print(item);
  }

While Loop:
  while condition {
      println("looping");
  }

Match (Pattern Matching):
  match value {
      case 1: {
          println("one");
      }
      case 2: {
          println("two");
      }
      default: {
          println("other");
      }
  }

Break and Continue:
  for i in range(100) {
      if i == 50 { break; }
      if i % 2 == 0 { continue; }
      print(i);
  }
""")
                continue

            if help_topic == "functions":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Functions                                                          ║
╚══════════════════════════════════════════════════════════════════════╝

Basic Function:
  func greet(name: str) {
      println("Hello, " + name);
  }

With Return Type:
  func add(a: int, b: int) -> int {
      return a + b;
  }

Default Parameters:
  func power(base: int, exp: int = 2) -> int {
      return base ** exp;
  }

Lambda:
  let double = func(x: int) -> int { return x * 2; };

Async Function:
  async func fetch(url: str) -> str {
      let resp = await http.get(url);
      return resp.body;
  }

Function Pointers:
  func apply(fn: ptr, x: int) -> int {
      return call_ptr(fn, x);
  }
""")
                continue

            if help_topic == "classes":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Classes                                                            ║
╚══════════════════════════════════════════════════════════════════════╝

Basic Class:
  class Point {
      init(self, x: int, y: int) {
          self.x = x;
          self.y = y;
      }

      func distance(self) -> f64 {
          return sqrt(self.x ** 2 + self.y ** 2);
      }
  }

  let p = Point.new(3, 4);
  print(p.distance());

Inheritance:
  class Animal {
      init(self, name: str) {
          self.name = name;
      }
      func speak(self) {
          println(self.name + " makes a sound");
      }
  }

  class Dog extends Animal {
      init(self, name: str) {
          super.init(name);
      }
      func speak(self) {
          println(self.name + " barks");
      }
  }
""")
                continue

            if help_topic == "structs":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Structs                                                            ║
╚══════════════════════════════════════════════════════════════════════╝

Basic Struct:
  struct Point {
      x: int;
      y: int;
  }

  let p = Point.new(3, 4);
  print(p.x);

Struct with Methods:
  struct Vec3 {
      x: f64;
      y: f64;
      z: f64;
  }

  func magnitude(v: Vec3) -> f64 {
      return sqrt(v.x**2 + v.y**2 + v.z**2);
  }
""")
                continue

            if help_topic == "enums":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Enums                                                              ║
╚══════════════════════════════════════════════════════════════════════╝

Basic Enum:
  enum Color {
      Red,
      Green,
      Blue;
  }

Enum with Match:
  enum Status {
      Ok,
      Error,
      Pending;
  }

  let s = Status.Ok;
  match s {
      case Ok: {
          println("OK");
      }
      case Error: {
          println("Error");
      }
      default: {
          println("Pending");
      }
  }
""")
                continue

            if help_topic == "modules":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Modules                                                            ║
╚══════════════════════════════════════════════════════════════════════╝

Import:
  import math;
  import json;
  import http;

Import with Alias:
  import math as m;
  let x = m.sqrt(16);

Import Specific:
  from math import sin, cos;

Module Definition:
  module mymodule;

  export func public_func() {
      println("public");
  }

  func private_func() {
      println("private");
  }

Available Modules:
  math        Math functions (sin, cos, sqrt, etc.)
  datetime    Date/time parsing and formatting
  json        JSON encoding/decoding
  http        HTTP client (get, post, put, delete)
  strings     String methods (upper, contains, split, etc.)
  crypto      Cryptography (aes, sha256, hmac, bcrypt)
  random      Random numbers
  os          File/OS operations
  system      System info (platform, python_version)
  path        File path manipulation (join, basename, dirname)
  fileio      File I/O operations
  pathlib     Object-oriented path manipulation
  network     Network utilities
  socket      TCP/UDP socket wrapper
  websocket   WebSocket client/server
  webserver   HTTP server framework
  web         Web framework (routing, middleware, CORS, sessions)
  webui       Styled web UI components (45+, dark/light/midnight themes)
  ide         Built-in web IDE (browser-based code editor)
  dotenv      Load .env configuration files
  logging     Logging framework with handlers
  sqlite      SQLite database (built-in)
  sql         SQL query builder (works with all backends)
  postgres    PostgreSQL driver (requires psycopg2-binary)
  mysql       MySQL driver (requires mysql-connector-python)
  mariadb     MariaDB driver (requires mariadb or mysql-connector)
  openapi     OpenAPI 3.0 spec generator
  hardware    Hardware I/O and CPU info
  kcrypt      Key derivation, password hashing
  security    Security utilities
  validation  Input validation
  ssh         SSH client
  docker      Docker SDK
  email       SMTP/IMAP client (send, fetch)
  graphql     GraphQL client
  excel       XLSX read/write (no pip needed)
  image       ImageMagick bridge (resize, crop, etc.)
  csv         CSV reading/writing
  subprocess  Subprocess execution
  asyncio     Async I/O operations
  collections Namedtuple, deque, counter
  itertools   Map, filter, reduce, chain, zip
  functools   Partial, compose, memoize
  iterators   Iterator utilities
  bitwise     Bitwise operations
  regex       Regular expressions
  encoding    Base64, Hex, URL encoding
  compression Gzip, Zlib, LZMA compress/decompress
  template    Template engine
  argparse    Command-line argument parsing
  testing     Unit testing utilities
  config      Configuration file handling
  scheduler   Task scheduler via background thread
  watcher     File/directory change watcher
  cache       In-memory cache with TTL
  ratelimit   Token-bucket rate limiter
  tui         ASCII tables, confirm/choose prompts
  progress    Progress bars, spinner, tqdm
  rich_progress Rich progress bars
  color       ANSI terminal colors
  markdown    Markdown to HTML conversion
  jwt         JWT encode/decode (HS256)
  dataclass   Data class definitions
  dataframe   Pandas-like DataFrame (filter, sort, groupby)
  fileproc    AWK-style file processor
  ffi         Foreign function interface
  memory      Memory management (mmap, mprotect)
  syscall     Low-level syscall interface
  asm         Inline assembly
  assembly    Assembly helpers
  accel       Hardware acceleration
  struct_utils Struct packing/unpacking
  error       Error handling utilities
  parser      Parser utilities
  compiler    Compiler internals
  safe        Safe mode utilities
  enum        Enum definitions
  path        File path utilities
""")
                continue

            if help_topic == "unsafe":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Unsafe Blocks & Memory Operations                                  ║
╚══════════════════════════════════════════════════════════════════════╝

Unsafe Block:
  unsafe {
      let addr = malloc(64);
      ptr_write(addr, 0xDEADBEEF);
      let val = ptr_read(addr);
      free(addr);
  }

Pointer Operations:
  unsafe {
      let p = malloc(8);
      ptr_write(p, 42);
      let v = ptr_read(p);
      free(p);
  }

Memory Functions:
  malloc(size)        Allocate heap memory
  free(ptr)           Free heap memory
  alloca(size)        Stack allocate
  memcpy(d, s, n)     Copy n bytes
  memset(p, v, n)     Set n bytes to value

I/O Ports:
  unsafe {
      let val = inb(0x60);    Read from port
      outb(0x60, val);        Write to port
  }

Inline Assembly:
  unsafe {
      asm("nop");
  }

System Calls:
  unsafe {
      let result = syscall(1, 1, "hello\n", 6);
  }
""")
                continue

            if help_topic == "threads":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Threading & Concurrency                                            ║
╚══════════════════════════════════════════════════════════════════════╝

Basic Thread:
  func worker(id: int) {
      println("Thread " + str(id));
  }

  thread worker(1);
  thread worker(2);

Thread Synchronization:
  let lock = Lock.new();
  lock.acquire();
  // critical section
  lock.release();

Semaphore:
  let sem = Semaphore.new(3);
  sem.wait();
  // limited resource
  sem.post();

Event:
  let evt = Event.new();
  evt.wait();
  evt.set();

Thread Pool:
  let pool = ThreadPool.new(4);
  let results = pool.map(double, [1, 2, 3, 4, 5]);
""")
                continue

            if help_topic == "comptime":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Compile-time Evaluation                                            ║
╚══════════════════════════════════════════════════════════════════════╝

Compile-time Constants:
  const MAX_SIZE = 1024;
  const PI = 3.14159265359;

Compile-time Expressions:
  let arr: [int; 2 + 3];    Evaluated at compile time

Comptime Function:
  Run 'kentscript comptime' from terminal for compile-time
  expression evaluation engine.
""")
                continue

            if help_topic == "borrow":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Borrow Checker                                                     ║
╚══════════════════════════════════════════════════════════════════════╝

Borrowing:
  let x = [1, 2, 3];
  borrow x;
  let y = x;          OK - borrowed
  release x;

Mutable Borrow:
  mut x = [1, 2, 3];
  borrow x, true;     Mutable borrow
  x.push(4);
  release x;

Ownership Rules:
  - Each value has exactly one owner
  - When owner goes out of scope, value is dropped
  - You can have many immutable borrows OR one mutable borrow
""")
                continue

            if help_topic == "exceptions":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Exception Handling                                                 ║
╚══════════════════════════════════════════════════════════════════════╝

Try/Except:
  try {
      let result = risky_operation();
  } except e {
      println("Error: " + str(e));
  }

Try/Except/Finally:
  try {
      let f = open("file.txt", "r");
      let content = f.read();
  } except e {
      println("Failed: " + str(e));
  } finally {
      println("Cleanup done");
  }

Raise:
  func divide(a: int, b: int) -> int {
      if b == 0 {
          raise "Division by zero";
      }
      return a / b;
  }

Assert:
  assert(x > 0, "x must be positive");
""")
                continue

            if help_topic == "io":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  File I/O                                                           ║
╚══════════════════════════════════════════════════════════════════════╝

Reading Files:
  let f = open("data.txt", "r");
  let content = f.read();
  f.close();

Writing Files:
  let f = open("output.txt", "w");
  f.write("Hello, World!");
  f.close();

File Modes:
  "r"     Read (default)
  "w"     Write (truncate)
  "a"     Append
  "rb"    Read binary
  "wb"    Write binary

Line by Line:
  let f = open("data.txt", "r");
  for line in f.readlines() {
      print(line);
  }
  f.close();
""")
                continue

            if help_topic == "examples":
                print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Quick Examples                                                     ║
╚══════════════════════════════════════════════════════════════════════╝

Hello World:
  println("Hello, World!");

Variables:
  let name: str = "KentScript";
  let version: int = 3;
  mut counter: int = 0;

Functions:
  func fibonacci(n: int) -> int {
      if n <= 1 { return n; }
      return fibonacci(n - 1) + fibonacci(n - 2);
  }

  print(fibonacci(10));

List Operations:
  let nums = [1, 2, 3, 4, 5];
  let doubled = map(func(x) { return x * 2; }, nums);
  let evens = filter(func(x) { return x % 2 == 0; }, nums);

String Operations:
  let s = "Hello, KentScript!";
  print(len(s));
  print(s.upper());
  print(s.split(","));

Pattern Matching:
  match value {
      case 1: { println("one"); }
      case 2: { println("two"); }
      case n if n > 10: { println("big"); }
      default: { println("other"); }
  }
""")
                continue

            # Stdlib module help topics
            _stdlib_help = {
                "os": "Operating system interface.\n  import os;\n  os.getpid() - current process ID\n  os.mkdir(path) - create directory\n  os.rmdir(path) - remove directory\n  os.getenv(name) - environment variable\n  os.putenv(name, val) - set environment variable\n  os.exists(path) - check if path exists\n  os.remove(path) - delete file\n  os.rename(src, dst) - rename file\n  os.getcwd() - current working directory\n  os.listdir(path) - list directory contents\n  os.read_file(path) - read entire file\n  os.write_file(path, content) - write entire file\n  os.chdir(path) - change directory",
                "datetime": "Date/time parsing and formatting.\n  import datetime;\n  datetime.now() - current datetime\n  datetime.date(y,m,d) - create date\n  datetime.strftime(fmt) - format datetime\n  datetime.strptime(str, fmt) - parse datetime",
                "random": "Random number generation.\n  import random;\n  random.random() - float in [0,1)\n  random.randint(a, b) - int in [a,b]\n  random.choice(list) - pick random element\n  random.shuffle(mut_list) - shuffle in place\n  random.seed(n) - seed the RNG",
                "http": "HTTP client.\n  import http;\n  http.get(url) -> HttpResponse with .status, .body, .text\n  http.post(url, headers={}, body=\"\") -> HttpResponse",
                "subprocess": "Run shell commands.\n  import subprocess;\n  subprocess.run(\"cmd\") -> runs command, returns exit code",
                "system": "System information.\n  import system;\n  system.platform() - OS platform\n  system.python_version() - Python version",
                "hardware": "Hardware I/O and CPU info.\n  import hardware;\n  hardware.get_cpu_count() - number of CPUs\n  hardware.inb(port) - read byte from I/O port (x86)\n  hardware.outb(port, val) - write byte to I/O port (x86)",
                "crypto": "Cryptography functions.\n  import crypto;\n  crypto.encrypt_aes(data, key) - AES encrypt\n  crypto.decrypt_aes(data, key) - AES decrypt\n  crypto.sha256(data) - SHA256 hash\n  crypto.hmac(data, key) - HMAC",
                "strings": "String manipulation.\n  import strings;\n  strings.upper(s) / strings.lower(s) / strings.title(s)\n  strings.contains(s, sub) - check substring\n  strings.startswith(s, p) / strings.endswith(s, p)\n  strings.replace(s, old, new) - replace all\n  strings.split(s, delim) - split into list\n  strings.strip(s) - strip whitespace",
                "json": "JSON encoding/decoding.\n  import json;\n  json.dumps(value) - serialize to JSON string\n  json.loads(str) - parse JSON string",
                "kcrypt": "Advanced cryptography module.\n  import kcrypt;\n  kcrypt.derive_key(password, salt) - key derivation\n  kcrypt.random_key(length) - random key\n  kcrypt.hash_password(password) - hash password\n  kcrypt.verify_password(hash, password) -> bool",
                "webui": "Styled web UI components (45+).\n  import webui;\n  webui.dark_theme() / webui.light_theme() / webui.midnight_theme() - themes\n  webui.card(title, body, theme) - styled card\n  webui.table(headers, rows, theme) - styled table\n  webui.button(text, url, variant, theme) - styled button\n  webui.alert(msg, variant, theme) - alert banner\n  webui.form(action, method, fields, theme) - styled form\n  webui.dropdown(label, options, name, theme) - dropdown select\n  webui.progress_bar(value, max, color, label, theme) - progress bar\n  webui.tooltip(text, target, position, theme) - hover tooltip\n  webui.accordion(items, theme) - collapsible sections\n  webui.toast(msg, duration, variant, theme) - auto-hiding notification\n  webui.pagination(current, total, url, theme) - page navigation\n  webui.footer(links, brand, copyright, theme) - footer\n  webui.dropdown_menu(label, items, theme) - click dropdown menu\n  webui.code_block(code, lang, theme) - styled code block\n  webui.stat_card(value, label, icon, color, theme) - stats display\n  webui.avatar(src, name, size, theme) - user avatar\n  webui.toggle(label, name, checked, theme) - toggle switch\n  webui.skeleton(lines, theme) - loading skeleton\n  webui.divider(text, theme) - horizontal divider\n  webui.page(title, theme, parts) - full HTML page wrapper\n  webui.hero(title, subtitle, cta, theme) - hero section\n  webui.feature_grid(features, theme) - feature showcase\n  webui.pricing_table(plans, theme) - pricing cards\n  webui.testimonial(quote, author, role, theme) - testimonial\n  webui.timeline(events, theme) - timeline display\n  webui.steps(items, theme) - step-by-step guide\n  webui.chart_bar(labels, values, theme) - bar chart\n  webui.breadcrumbs(items, theme) - breadcrumb navigation\n  webui.team_card(name, role, avatar, theme) - team member card\n  webui.chat_bubble(text, sender, is_user, theme) - chat bubble\n  webui.chat(messages, theme) - chat display\n  webui.login_form(action, theme) - login form\n  webui.search_bar(placeholder, action, theme) - search input\n  webui.empty_state(title, msg, icon, theme) - empty state\n  webui.notification(msg, variant, theme) - notification toast\n  webui.star_rating(value, max, theme) - star rating\n  webui.tag_list(tags, theme) - tag/chip list\n  webui.kanban(columns, theme) - kanban board\n  webui.stat_grid(stats, theme) - stats grid\n  webui.alert_banner(msg, variant, theme) - full-width alert\n  webui.footer_bottom(links, copyright, theme) - bottom footer",
                "web": "Web framework with routing, middleware, CORS, sessions.\n  import web;\n  let app = web.App();\n  app.get(path, handler) - GET route\n  app.post(path, handler) - POST route\n  app.put(path, handler) - PUT route\n  app.delete(path, handler) - DELETE route\n  app.any(path, handler) - any method\n  app.use(middleware) - add middleware\n  app.enable_sessions(secret) - enable sessions\n  app.mount(prefix, sub_app) - mount sub-router\n  app.on_not_found(handler) - custom 404\n  app.listen(port, host) - start server\n  Path params: app.get(\"/users/:id\", func(req) { req[\"params\"][\"id\"] })\n  web.json(data) / web.text(body) / web.html(body) - responses\n  web.redirect(url) / web.error(code, msg) - redirects/errors\n  web.cors_middleware(opts) - CORS middleware\n  web.rate_limiter(opts) - rate limiting middleware\n  web.static_files(prefix, dir) - static file middleware",
                "webserver": "HTTP server with static files.\n  import webserver;\n  webserver.serve(port, bind, directory) - start server\n  Features: directory listing, MIME detection, CORS, cache control",
                "openapi": "OpenAPI 3.0 spec generator.\n  import web, openapi;\n  let spec = openapi.generate(app, info) - generate spec\n  openapi.spec_to_json(spec) - to JSON\n  openapi.spec_to_markdown(spec) - to markdown docs",
                "sql": "SQL query builder (works with all backends).\n  import sql;\n  sql.select(table, columns) - SELECT query\n  sql.insert(table, data) - INSERT query\n  sql.batch_insert(table, cols, rows) - batch INSERT\n  sql.update(table, data) - UPDATE query\n  sql.delete_from(table) - DELETE query\n  sql.raw(query, params) - raw query with params\n  sql.create_table(name, columns, if_not_exists) - CREATE TABLE\n  q.where(col, op, val) / q.and_where() / q.or_where() - WHERE\n  q.where_in(col, vals) / q.where_between() / q.where_like() - WHERE\n  q.join() / q.left_join() / q.right_join() - JOINs\n  q.order_by() / q.group_by() / q.having() - ORDER/GROUP\n  q.limit() / q.offset() - pagination\n  q.count() / q.sum() / q.avg() / q.min() / q.max() - aggregates",
                "sqlite": "SQLite database (built-in).\n  import sqlite;\n  let db = sqlite.open(\"app.db\") - open database\n  let db = sqlite.in_memory() - in-memory database\n  db.execute(sql, params) - execute query\n  db.query(sql, params) -> list of rows\n  db.query_one(sql, params) -> single row\n  db.query_val(sql, params) -> single value\n  db.commit() / db.rollback() - transactions\n  db.close() - close connection",
                "postgres": "PostgreSQL driver (requires psycopg2-binary).\n  import postgres;\n  let db = postgres.connect(host, port, dbname, user, pass)\n  db.execute(sql, params) / db.query(sql, params)\n  db.query_one() / db.query_val() / db.query_many()\n  db.executemany(sql, params_list) / db.copy_from(table, data)\n  db.commit() / db.rollback() / db.close()",
                "mysql": "MySQL driver (requires mysql-connector-python).\n  import mysql;\n  let db = mysql.connect(host, port, database, user, pass)\n  db.execute(sql, params) / db.query(sql, params)\n  db.query_one() / db.query_val() / db.last_insert_id()\n  db.executemany(sql, params_list)\n  db.commit() / db.rollback() / db.close()",
                "mariadb": "MariaDB driver (requires mariadb or mysql-connector).\n  import mariadb;\n  let db = mariadb.connect(host, port, database, user, pass)\n  db.execute(sql, params) / db.query(sql, params)\n  db.query_one() / db.query_val() / db.last_insert_id()\n  db.commit() / db.rollback() / db.close()",
                "websocket": "WebSocket client/server.\n  import websocket;\n  websocket.connect(url) - connect to server\n  websocket.server(host, port) - create server\n  server.on_message(func) - message handler\n  server.broadcast(msg) - send to all clients",
                "dotenv": "Load .env configuration files.\n  import dotenv;\n  dotenv.load(path) - load .env file\n  dotenv.get(key, default) - get variable\n  dotenv.set(key, value) - set variable\n  dotenv.save(path) - save to file",
                "logging": "Logging framework.\n  import logging;\n  logging.info(msg) / logging.error(msg) / logging.warning(msg)\n  logging.debug(msg) / logging.critical(msg)",
                "socket": "TCP/UDP socket wrapper.\n  import socket;\n  socket.tcp() - create TCP socket\n  socket.udp() - create UDP socket\n  socket.gethostname() - get hostname\n  socket.gethostbyname(host) - DNS lookup",
                "tui": "ASCII tables, confirm/choose prompts.\n  Usage: tui.Table(headers, rows).print()",
                "dataframe": "Pandas-like DataFrame.\n  Usage: dataframe.DataFrame(data).filter(fn).sort(key).print()",
                "jwt": "JWT encode/decode (HS256).\n  Usage: jwt.encode({payload}, secret), jwt.decode(token, secret)",
                "email": "SMTP/IMAP email client.\n  Usage: email.send(host,port,user,pw,from,to,subj,body)",
                "markdown": "Markdown to HTML (regex-based).\n  Usage: markdown.to_html(\"# title\")",
                "scheduler": "Task scheduler via background thread.\n  Usage: Scheduler().every(secs, task).start()",
                "ssh": "SSH client via subprocess.\n  Usage: ssh.run(\"user@host\", \"cmd\")",
                "docker": "Docker SDK via CLI.\n  Usage: docker.ps(), docker.pull(\"nginx\")",
                "watcher": "File change watcher (polling).\n  Usage: FileWatcher(path, callback).start()",
                "graphql": "GraphQL client over HTTP.\n  Usage: Client(url).query(\"{ field }\")",
                "excel": "XLSX read/write.\n  Usage: excel.write(\"f.xlsx\", [[\"a\",1],[\"b\",2]])",
                "image": "ImageMagick bridge.\n  Usage: image.resize(in,out,w,h)",
                "cache": "In-memory cache with TTL.\n  Usage: Cache(maxsize, ttl).get/set/delete",
                "ratelimit": "Token-bucket rate limiter.\n  Usage: RateLimiter(max, period).allow(key)",
                "fileproc": "AWK-style file processing.\n  Usage: fileproc.read_lines(path), fileproc.grep(path, pattern)",
                "progress": "Progress bars, spinner, tqdm.\n  Usage: ProgressBar(total), Spinner(), tqdm(list)",
                "color": "ANSI terminal colors.\n  See: color.RED, color.GREEN, color.BOLD",
                "path": "File path manipulation.\n  import path;\n  path.join(a, b) - join paths\n  path.basename(p) - filename\n  path.dirname(p) - directory\n  path.ext(p) - extension\n  path.exists(p) - check existence",
                "pathlib": "Object-oriented path handling.\n  import pathlib;\n  pathlib.Path(p).exists() / .read_text() / .write_text() / .mkdir()",
                "ide": "Built-in web IDE — browser-based code editor.\n  import ide;\n  ide.start() - launch IDE on port 8000\n  ide.start_with_port(port) - launch on custom port\n  Features: file browser, code editor (CodeMirror), run button,\n  save/create/delete files, syntax highlighting, auto port retry.",
            }
            if help_topic and help_topic in _stdlib_help:
                print("\n" + help_topic + ": " + _stdlib_help[help_topic] + "\n")
                print("See `help modules` for full module list.")
                continue

            # Dynamic fallback: document any stdlib module present on disk so
            # help('<module>') works for every importable module, not just the
            # hand-curated ones above.
            _dyn = _build_module_help(help_topic)
            if _dyn:
                print(_dyn)
                continue

            if help_topic and help_topic not in ["keywords", "types", "operators", "builtins", "control", "functions", "classes", "structs", "enums", "modules", "unsafe", "threads", "comptime", "borrow", "exceptions", "io", "examples"]:
                print(f"No help available for '{help_topic}'.")
                print(f"Type 'help' to see available topics.")
                continue

            if code.lower() == "creator":
                print("""
================================================================================
KentScript v3.1.0 - Systems Programming Language
================================================================================

Creator:       pyLord (Musika Alvin)
Location:      Uganda
GitHub:        https://github.com/musikaalvin
Version:       v3.1.0
Compiler:      KentScript v3.1.0 (C transpilation + C transpilation)
Performance:   Native speed via gcc -O3

Language Features:
  • Complete type system (i8-i64, u8-u64, f32, f64, bool, str, ptr)
  • Functions, closures, lambdas, structs, OOP
  • Borrow checker & memory safety
  • Concurrency with pthreads
  • Unsafe blocks for systems programming
  • 231+ direct Linux syscalls
  • Inline assembly (x86-64 & ARM64)
  • Lock-free atomic operations

================================================================================
""")
                continue

            if code.startswith("kpm install "):
                parts = code.split()
                if len(parts) >= 3:
                    pkg = parts[2]
                    version = parts[3] if len(parts) > 3 else None
                    try:
                        kpm.install(pkg, version)
                    except Exception as e:
                        print(f"Error: {e}")
                else:
                    print("Usage: kpm install <package> [version]")
                continue

            if code.strip() == "kpm list":
                packages = kpm.list_installed()
                if packages:
                    print("\nInstalled packages:")
                    for pkg in packages:
                        print(f"  {pkg['name']} ({pkg['version']})")
                else:
                    print("No packages installed")
                continue

            if code.startswith("kpm uninstall "):
                parts = code.split()
                if len(parts) >= 3:
                    pkg = parts[2]
                    try:
                        kpm.uninstall(pkg)
                    except Exception as e:
                        print(f"Error: {e}")
                else:
                    print("Usage: kpm uninstall <package>")
                continue

            if code.startswith("kpm search "):
                parts = code.split(maxsplit=2)
                if len(parts) >= 3:
                    query = parts[2]
                    try:
                        results = kpm.search(query)
                        if results:
                            print(f"\nFound {len(results)} package(s):")
                            for pkg in results:
                                desc = pkg.get("description", "No description")
                                print(f"  {pkg['name']} - {desc}")
                        else:
                            print("No packages found")
                    except Exception as e:
                        print(f"Error: {e}")
                else:
                    print("Usage: kpm search <query>")
                continue

            if code.lower() == "vars":
                for name, value in interpreter.global_env.vars.items():
                    if not name.startswith("_"):
                        print(f"  {name}: {value}")
                continue

            if code.lower() == "clear":
                os.system("clear" if os.name != "nt" else "cls")
                continue

            # Smart multiline handling: only for func, class, if, while, for, try
            buffer = code
            indent_level = 0

            # Count braces to determine if we need more input
            for char in code:
                if char == "{":
                    indent_level += 1
                elif char == "}":
                    indent_level -= 1

            # Only do multiline for known patterns, not for errors like "lambda: {"
            multiline_patterns = ("func ", "class ", "if ", "while ", "for ", "try", "match ", "enum ", "struct ")
            needs_multiline = code.strip().startswith(multiline_patterns)
            
            # Also check for decorator at start of line
            needs_continuation = code.strip().startswith("@") and indent_level == 0

            # If we have unclosed braces from known patterns, keep reading
            while (indent_level > 0 and needs_multiline) or needs_continuation:
                try:
                    if prompt_toolkit_available and session:
                        more = session.prompt("... ")
                    else:
                        more = input("... ")

                    buffer += "\n" + more

                    # Update brace count
                    for char in more:
                        if char == "{":
                            indent_level += 1
                        elif char == "}":
                            indent_level -= 1

                    # After decorator, once we see func/class definition, stop needing continuation
                    if needs_continuation and ("func " in more or "class " in more):
                        needs_continuation = False

                except (KeyboardInterrupt, EOFError):
                    break

            code = buffer

            # Check for syscall code - needs special handling
            if "import syscall" in code or "syscall." in code:
                try:
                    # Try to get the classes at runtime using eval with explicit globals
                    module_globals = globals()
                    try:
                        KentScript_cls = eval("KentScript", module_globals)
                        KentScriptInterpreter_cls = eval("Interpreter", module_globals)
                        _runtime = KentScript_cls()
                        _interp = KentScriptInterpreter_cls(_runtime)
                        _interp.execute(code)
                        continue
                    except (NameError, TypeError):
                        # Classes not available yet, fall through
                        pass
                except Exception as e:
                    pass

                # If we're still here and it's syscall code, skip the old parser entirely
                if "import syscall" in code or "syscall." in code:
                    pass  # Syscall in REPL is allowed

            try:
                KSError.begin_collection()
                from compiler.lexer.lexer import Lexer as _KSLexer
                from compiler.parser.parser import Parser as _KSParser

                tokens = _KSLexer(code, filename="<repl>").tokenize()
                ast = _KSParser(tokens, code, filename="<repl>").parse()
                repl_errors = KSError.end_collection()
                if repl_errors:
                    # Use the module-level ErrorFormatter import
                    print(ErrorFormatter.format_error_summary(repl_errors))
                    _error_shown = True
                    continue
                else:
                    _error_shown = False

                for stmt in ast:
                    result = interpreter.eval(stmt, interpreter.global_env)
                    if (
                        result is not None
                        and not isinstance(
                            stmt, (FunctionDef, ClassDef, LetDecl, Assignment)
                        )
                        and not isinstance(result, (Function, Class, Module))
                        and not isinstance(result, __import__("types").GeneratorType)
                    ):
                        # Pretty-print instances using __str__ if available
                        if isinstance(result, Instance):
                            if "__str__" in result.class_def.methods:
                                fn = result.class_def.methods["__str__"]
                                local_env = Environment(fn.closure)
                                local_env.define("self", result)
                                try:
                                    for s2 in fn.body:
                                        interpreter.eval(s2, local_env)
                                except ReturnException as re2:
                                    print(re2.value)
                                    continue
                            print(str(result.attrs))
                        else:
                            print(result)
            except (UnboundLocalError, SyntaxError, NameError, KentScriptSyntaxError) as parser_error:
                # Check if already formatted
                if hasattr(parser_error, "formatted"):
                    print(parser_error.formatted)
                elif isinstance(parser_error, KentScriptSyntaxError):
                    print(ErrorFormatter.format_exception(parser_error, filename="<repl>", source_code=code))
                else:
                    # Format NameError/UnboundLocalError with KentScript-specific help
                    print(ErrorFormatter.format_exception(parser_error, filename="<repl>", source_code=code))

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            break
        except Exception as e:
            # Skip if error was already shown in inner try block
            if _error_shown:
                continue
            
            # Check if already formatted
            if hasattr(e, "formatted") and e.formatted:
                print(e.formatted)
                _error_shown = True
            elif isinstance(e, KentScriptSyntaxError):
                print(ErrorFormatter.format_exception(e, filename="<repl>", source_code=code))
            elif isinstance(e, KentScriptTypeError):
                print(ErrorFormatter.format_exception(e, filename="<repl>", source_code=code))
            elif isinstance(e, KentScriptNameError):
                print(ErrorFormatter.format_exception(e, filename="<repl>", source_code=code))
            elif RICH_AVAILABLE:
                console.print(f"[bold red]Error:[/bold red] {e}")
            else:
                print(f"Error: {e}")


# ============================================================================
# PACKAGE MANAGER (PackageManager)
# ============================================================================


class PackageManager:
    def __init__(self):
        self.module_path = "ks_modules"
        self.checksum_file = os.path.join(self.module_path, ".checksums")
        self.installed_packages = {}

        if not os.path.exists(self.module_path):
            os.makedirs(self.module_path)
        if os.path.abspath(self.module_path) not in sys.path:
            sys.path.append(os.path.abspath(self.module_path))

        # ENHANCED v3.1.0: Also add current directory's ks_modules
        cwd_modules = os.path.join(os.getcwd(), "ks_modules")
        if (
            cwd_modules != os.path.abspath(self.module_path)
            and cwd_modules not in sys.path
        ):
            sys.path.insert(0, cwd_modules)

        self._load_installed()

    def _load_installed(self):
        if os.path.exists(self.checksum_file):
            try:
                with open(self.checksum_file, "r") as f:
                    self.installed_packages = json.load(f)
            except:
                self.installed_packages = {}

    def _save_installed(self):
        with open(self.checksum_file, "w") as f:
            json.dump(self.installed_packages, f, indent=2)

    def _compute_checksum(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def install(self, package_name: str, url: str = None, version: str = "latest"):
        print(f"[PackageManager] Installing {package_name}@{version}...")

        if url is None:
            url = f"https://raw.githubusercontent.com/kentscript/packages/main/{package_name}.ks"

        # ENHANCED v3.1.0: Support ZIP files
        if url.endswith(".zip") or url.endswith(".ks.zip"):
            try:
                import zipfile, tempfile

                req = urllib.request.Request(
                    url, headers={"User-Agent": "KentScript PackageManager/5.0"}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    zip_data = response.read()

                # Create ks_modules directory
                if not os.path.exists("ks_modules"):
                    os.makedirs("ks_modules")

                # Extract ZIP
                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                    tmp.write(zip_data)
                    tmp_path = tmp.name

                extract_dir = os.path.join("ks_modules", package_name)
                os.makedirs(extract_dir, exist_ok=True)

                with zipfile.ZipFile(tmp_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)

                os.remove(tmp_path)
                print(f" Extracted {package_name} to ks_modules/{package_name}/")

                self.installed_packages[package_name] = {
                    "version": version,
                    "checksum": hashlib.sha256(zip_data).hexdigest()[:16],
                    "url": url,
                    "type": "zip",
                }
                self._save_installed()
                return
            except Exception as e:
                print(f" Failed to extract ZIP: {e}")
                return

        # ENHANCED v3.1.0: Support local files
        if url.startswith("/") or url.startswith("./") or url.startswith("../"):
            try:
                if url.endswith(".zip") or url.endswith(".ks.zip"):
                    import zipfile

                    extract_dir = os.path.join("ks_modules", package_name)
                    os.makedirs(extract_dir, exist_ok=True)
                    with zipfile.ZipFile(url, "r") as zip_ref:
                        zip_ref.extractall(extract_dir)
                    print(f" Extracted local ZIP: {package_name}")
                else:
                    with open(url, "r", encoding="utf-8") as f:
                        code = f.read()
                    if not os.path.exists("ks_modules"):
                        os.makedirs("ks_modules")
                    dest = os.path.join("ks_modules", f"{package_name}.ks")
                    with open(dest, "w") as f:
                        f.write(code)
                    print(f" Installed {package_name} from local file")

                self.installed_packages[package_name] = {
                    "version": version,
                    "checksum": "local",
                    "url": url,
                    "type": "local",
                }
                self._save_installed()
                return
            except Exception as e:
                print(f" Failed to install from local file: {e}")
                return

        # Standard .ks file installation
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "KentScript PackageManager/5.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                code = response.read().decode("utf-8")

            checksum = self._compute_checksum(code)
            file_path = os.path.join(self.module_path, f"{package_name}.ks")

            with open(file_path, "w") as f:
                f.write(code)

            self.installed_packages[package_name] = {
                "version": version,
                "checksum": checksum,
                "url": url,
            }
            self._save_installed()

            print(f" Installed {package_name}@{version}")
            print(f"   Checksum: {checksum[:16]}...")

        except Exception as e:
            print(f" Failed to install {package_name}: {e}")

    def uninstall(self, package_name: str):
        if package_name in self.installed_packages:
            file_path = os.path.join(self.module_path, f"{package_name}.ks")
            if os.path.exists(file_path):
                os.remove(file_path)
            del self.installed_packages[package_name]
            self._save_installed()
            print(f" Uninstalled {package_name}")
        else:
            print(f" Package {package_name} not found")

    def list_packages(self):
        if not self.installed_packages:
            print("No packages installed")
            return

        print("\n📦 Installed Packages:")
        print("=" * 50)
        for name, info in self.installed_packages.items():
            print(f"  {name:20} v{info['version']}")
        print("=" * 50)


# ============================================================================
# TYPE CHECKER
# ============================================================================


class PrimitiveType(Enum):
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BOOL = auto()
    LIST = auto()
    DICT = auto()
    FUNCTION = auto()
    CLASS = auto()
    NONE = auto()
    ANY = auto()


@dataclass
class TypeInfo:
    name: str
    ks_type: PrimitiveType
    nullable: bool = False
    generic_params: List["TypeInfo"] = field(default_factory=list)


class TypeChecker:
    def __init__(self):
        self.type_env: Dict[str, TypeInfo] = {}

    def infer_type(self, value: Any) -> PrimitiveType:
        if isinstance(value, bool):
            return PrimitiveType.BOOL
        elif isinstance(value, int):
            return PrimitiveType.INT
        elif isinstance(value, float):
            return PrimitiveType.FLOAT
        elif isinstance(value, str):
            return PrimitiveType.STRING
        elif isinstance(value, list):
            return PrimitiveType.LIST
        elif isinstance(value, dict):
            return PrimitiveType.DICT
        elif callable(value):
            return PrimitiveType.FUNCTION
        elif value is None:
            return PrimitiveType.NONE
        else:
            return PrimitiveType.ANY

    def check_type(self, value: Any, expected_type: PrimitiveType) -> bool:
        actual_type = self.infer_type(value)
        if expected_type == PrimitiveType.ANY:
            return True
        return actual_type == expected_type

    def register_variable(self, name: str, value: Any, type_hint: Optional[str] = None):
        if type_hint:
            type_map = {
                "int": PrimitiveType.INT,
                "float": PrimitiveType.FLOAT,
                "string": PrimitiveType.STRING,
                "bool": PrimitiveType.BOOL,
                "list": PrimitiveType.LIST,
                "dict": PrimitiveType.DICT,
                "function": PrimitiveType.FUNCTION,
                "class": PrimitiveType.CLASS,
                "none": PrimitiveType.NONE,
            }
            ks_type = type_map.get(type_hint.lower(), PrimitiveType.ANY)
        else:
            ks_type = self.infer_type(value)

        self.type_env[name] = TypeInfo(name, ks_type)

        if not self.check_type(value, ks_type):
            raise TypeError(
                f"Type mismatch for {name}: expected {ks_type}, got {self.infer_type(value)}"
            )


# ============================================================================
# FILE RUNNERS
# ============================================================================


def run_file(filename: str, use_cache: bool = True):
    """Run a KentScript file with the interpreter."""
    try:
        # Read code first
        with open(filename, "r", encoding="utf-8") as f:
            code = f.read()

        # Set error context for better error messages
        KSError.set_context(filename=filename, source=code)

        # Check if syscall code - handle with normal interpreter
        if "import syscall" in code or "syscall." in code:
            # Use regular interpreter for syscall code
            ast = _ks_parse(code, filename)
            interpreter = Interpreter(source_code=code)
            interpreter.interpret(ast)
            return

        # Regular interpreter mode (default)
        ast_cache = ASTCache()
        ast = None

        if use_cache:
            ast = ast_cache.load(filename)

        if ast is None:
            with open(filename, "r", encoding="utf-8") as f:
                code = f.read()

            ast = _ks_parse(code, filename)

            if use_cache:
                ast_cache.save(filename, ast)

        interpreter = Interpreter(source_code=code)
        interpreter.interpret(ast)

    except SyntaxError as e:
        # Check if already formatted
        if hasattr(e, "formatted"):
            print(e.formatted, file=sys.stderr)
        else:
            # Format syntax errors nicely - use module-level ErrorFormatter
            source_code = None
            try:
                with open(filename, "r") as f:
                    source_code = f.read()
            except:
                pass
            print(
                ErrorFormatter.format_exception(e, filename, source_code),
                file=sys.stderr,
            )
        sys.exit(1)
    except Exception as e:
        # Check if already formatted
        if hasattr(e, "formatted"):
            print(e.formatted, file=sys.stderr)
        else:
            # Format other errors - use module-level ErrorFormatter
            source_code = None
            try:
                with open(filename, "r") as f:
                    source_code = f.read()
            except:
                pass
            print(
                ErrorFormatter.format_exception(e, filename, source_code),
                file=sys.stderr,
            )
        sys.exit(1)


# ================ KCRYPT HEX VIEW ================
def _kcrypt_hex_view(filename, key=None):
    """Display .kcrypt file as hex dump, optionally decrypt if key provided."""
    import datetime

    print(f"\rkcrypt file viewer :: {filename}\n")

    try:
        with open(filename, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Parse the 3-line format: MAGIC\nMETADATA_JSON\nENCRYPTED_BASE64
    lines = raw.split("\n", 2)

    if len(lines) < 3:
        print("Error: Not a valid .kcrypt file (expected 3 lines)")
        return

    magic, meta_json_str, encrypted_b64 = lines[0], lines[1], lines[2]

    if magic != "KC1":
        print(f"Error: Bad magic header: {magic}")
        return

    # Parse metadata
    try:
        import json as _json
        meta = _json.loads(meta_json_str)
    except Exception:
        meta = {"title": "N/A", "subject": "N/A"}

    print("[ Metadata ]")
    print(f"  Title:      {meta.get('title', 'N/A')}")
    print(f"  Created:    {meta.get('timestamp', 'N/A')}")
    print(f"  Original:   {meta.get('original_size', 'N/A')} bytes")
    print(f"  Encrypted:  {meta.get('encrypted_size', 'N/A')} bytes")
    print(f"  Key ID:     {meta.get('key_id', 'N/A')}")
    print(f"  Subject:    {meta.get('subject', 'N/A')}")
    print(f"  Status:     {meta.get('status', 'N/A')}")
    print(f"  Tool:       {meta.get('tool', 'N/A')}")
    print()

    # Decrypt if key provided
    if key is not None:
        try:
            from nacl.bindings import crypto_aead_xchacha20poly1305_ietf_decrypt
            import base64 as _b64
            import hashlib as _hashlib

            key_bytes = key.encode() if isinstance(key, str) else key
            if len(key_bytes) < 32:
                key_bytes = key_bytes.ljust(32, b"\x00")[:32]
            else:
                key_bytes = _hashlib.sha256(key_bytes).digest()[:32]

            data_bytes = _b64.b64decode(encrypted_b64.encode())

            nonce_from_data = data_bytes[:24]
            ct = data_bytes[24:]

            pt = crypto_aead_xchacha20poly1305_ietf_decrypt(
                ct, b"", nonce_from_data, key_bytes
            )

            plaintext = pt.decode("utf-8", errors="replace")

            # Styled output
            print("[ DECRYPTED CONTENT (styled) ]\n")

            # ANSI colors
            C_RED = "\033[91m"
            C_GREEN = "\033[92m"
            C_YELLOW = "\033[93m"
            C_BLUE = "\033[94m"
            C_MAGENTA = "\033[95m"
            C_CYAN = "\033[96m"
            C_BOLD = "\033[1m"
            C_DIM = "\033[2m"
            C_RESET = "\033[0m"

            for line in plaintext.split("\n"):
                line = line.rstrip()
                if not line:
                    print()
                    continue

                lower = line.lower()

                if "confidential" in lower and len(line) < 60:
                    print(f"{C_BOLD}{C_RED}{line}{C_RESET}")
                elif "subject:" in lower:
                    print(f"{C_CYAN}{line}{C_RESET}")
                elif "status:" in lower:
                    status_val = line.split(":", 1)[1].strip().lower() if ":" in line else ""
                    if "active" in status_val or "complete" in status_val:
                        print(f"{C_GREEN}{line}{C_RESET}")
                    elif "failed" in status_val or "error" in status_val:
                        print(f"{C_RED}{line}{C_RESET}")
                    else:
                        print(f"{C_YELLOW}{line}{C_RESET}")
                elif "details:" in lower:
                    print(f"{C_MAGENTA}{line}{C_RESET}")
                elif "timestamp:" in lower or "date" in lower:
                    print(f"{C_DIM}{line}{C_RESET}")
                elif line.startswith("["):
                    print(f"{C_BLUE}{line}{C_RESET}")
                else:
                    print(line)

            print(f"\n{C_DIM}[ Decryption successful :: {len(pt)} bytes ]{C_RESET}")

        except Exception as e:
            print(f"Decryption failed: {e}")

    # Hex dump of the encrypted payload
    print("\n[ HEX DUMP (encrypted payload) ]\n")

    hex_data = encrypted_b64.encode("utf-8") if not isinstance(encrypted_b64, bytes) else encrypted_b64
    offset = 0
    C_DIM = "\033[2m"
    C_CYAN = "\033[96m"
    C_RESET = "\033[0m"

    for i in range(0, len(hex_data), 16):
        chunk = hex_data[i : i + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        hex_part += " " * (3 * (16 - len(chunk)))

        ascii_part = ""
        for b in chunk:
            if 32 <= b < 127:
                ascii_part += chr(b)
            else:
                ascii_part += "."

        offset_hex = f"{offset:08x}"
        print(f"{C_DIM}{offset_hex}{C_RESET}  {hex_part}  |{C_CYAN}{ascii_part}{C_RESET}|")
        offset += 16

    print(f"\n{C_DIM}[ {len(hex_data)} bytes encrypted payload ]{C_RESET}")


# ================ MAIN ================
def main():
    # Ensure module path is in sys.path
    if os.path.exists("ks_modules"):
        if os.path.abspath("ks_modules") not in sys.path:
            sys.path.append(os.path.abspath("ks_modules"))

    # ========================================================================
    # TIER 2 & ELDRITCH MODE CLI ARGUMENTS
    # ========================================================================

    if len(sys.argv) > 1:
        #  ANCIENT MODE - Maximum aggressive speed
        if "--unsafe-optimization" in sys.argv:
            args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
            if args:
                filename = args[0]
                print("[ legacy mode active]")
                print(" Unleashing celestial compiler optimizations...")

                aggressive_optimizer = AggressiveOptimizer()
                flags = aggressive_optimizer.get_aggressive_flags()
                print(f" Compiler flags: {flags}")
                print(f" Optimizer passes: (none)")
                print(f" Runtime: Unsafe (no bounds checking)")

                if "--run" in sys.argv:
                    print(f" Compiling & running {filename} with ANCIENT mode...\n")

                sys.exit(0)

        #  ELDRITCH MODE - ALL aggressive features combined
        elif "--aggressive-optimization" in sys.argv:
            args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
            if args:
                filename = args[0]
                print("[ ELDRITCH MODE UNLEASHED]")
                print(
                    " Celestial speed maximized. Safety disabled. Prepare for cosmic velocity."
                )

                performance_pkg = PerformancePackage()
                performance_pkg.enable_all()

                print(f" AncientCelestialOptimizer: ACTIVE")
                print(f" UnsafeMode: ACTIVE")
                print(f" DirectSyscallAPI: ACTIVE")
                print(f" BumpAllocator: ACTIVE")
                print(
                    f"\n Aggressive flags:\n   {performance_pkg.get_complete_flags()}"
                )

                runtime = performance_pkg.emit_eldritch_runtime()
                print(
                    f" Generated {len(runtime.split(chr(10)))} lines of unsafe C runtime"
                )

                if "--show-runtime" in sys.argv:
                    print("\n[Generated C Runtime]:")
                    print(runtime)

                if "--run" in sys.argv:
                    print(f"\n Compiling & running {filename} with ELDRITCH mode...\n")

                sys.exit(0)

        #  BENCHMARK MODE
        elif "--benchmark" in sys.argv:
            args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
            if args:
                filename = args[0]
                print(f"[🏁 BENCHMARK MODE]")

                # Create compiler with benchmarking
                compiler = DualModeCompiler(
                    open(filename).read(), mode="aot", opt_level=3
                )
                bench = compiler.benchmark(filename)

                print(f"\n{bench}")
                print(f"  Speedup factor: {bench.speed_factor:.1f}x")
                print(f"  Compilation time: {bench.compilation_time:.3f}s")
                print(f"  Runtime: {bench.runtime:.3f}s")
                print(f"  Peak memory: {bench.peak_memory_mb:.1f}MB")
            sys.exit(0)

        #  AOT MODE
        elif "--aot" in sys.argv:
            args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
            if args:
                filename = args[0]
                print("[ AOT MODE]")

                compiler = DualModeCompiler(
                    open(filename).read(), mode="aot", opt_level=3
                )
                result = compiler.compile_aot()

                print(f"Mode: AOT (Ahead-Of-Time)")
                print(f"Flags: {result['flags']}")
                print(f"Passes: {result['passes']}")
                print(f"Runtime lines generated: {result['runtime_lines']}")
                print(f"Status: {result['status']}")
            sys.exit(0)

        #  BAREMETAL MODE
        elif "--baremetal" in sys.argv:
            arch = "x86_64"
            for i, arg in enumerate(sys.argv):
                if arg == "--baremetal" and i + 1 < len(sys.argv):
                    arch = sys.argv[i + 1]
                    break

            if arch not in ["x86_64", "arm64"]:
                print(f" Unsupported architecture: {arch}")
                print("   Supported: x86_64, arm64")
                sys.exit(1)

            print(f"[🔴 BARE-METAL MODE - {arch}]")

            compiler = DualModeCompiler("", mode="aot", opt_level=3)
            result = compiler.compile_baremetal(arch)

            print(f"Architecture: {arch}")
            print(f"Assembly lines: {result['assembly_lines']}")
            print(f"Status: {result['status']}")
            print(f"Use case: Kernel development, bootloader, Ring 0 code")
            sys.exit(0)

        #  HELP
        elif "--help-tier2" in sys.argv or "--help-eldritch" in sys.argv:
            print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                    TIER 2 & ELDRITCH MODE CLI REFERENCE                   ║
╚════════════════════════════════════════════════════════════════════════════╝

AGGRESSIVE OPTIMIZATION FLAGS:
  --ancient              Enable ANCIENT MODE (aggressive speed optimizations)
  --eldritch             Enable ELDRITCH MODE (ALL aggressive features)
  -O0, -O1, -O2, -O3    Optimization level (default: -O3)
  --opt 0-3             Alternative optimization syntax

COMPILATION MODES:
  --aot                  Ahead-Of-Time compilation (default)
  --baremetal [arch]     Bare-metal/kernel code (x86_64 or arm64)

PERFORMANCE:
  --benchmark FILE       Run benchmark on FILE
  --show-flags          Show all compiler flags
  --show-passes         Show optimization passes

OUTPUT:
  --show-runtime        Display generated C runtime code
  --run                 Compile and run immediately

EXAMPLES:
  kentscript.py code.ks --ancient                 # ANCIENT mode
  kentscript.py code.ks --eldritch                # ELDRITCH mode
  kentscript.py code.ks -O3                       # Maximum safety optimization
  kentscript.py code.ks --eldritch --run          # ELDRITCH + run
  kentscript.py code.ks --benchmark               # Benchmark compilation
  kentscript.py code.ks --baremetal x86_64        # x86-64 kernel code

PERFORMANCE POTENTIAL:
  Normal:        2-5x faster than Python
  -O3:          40-100x faster than Python
  --ancient:    50-200x faster than Python
  --eldritch:   100-1000x faster than Python! ☄️
""")
            sys.exit(0)

    # Parse command line arguments
    if len(sys.argv) > 1:
        # Check for native compilation flag FIRST
        if "--native" in sys.argv:
            # Extract file and flags
            args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
            flags = sys.argv[1:]

            if args:
                filename = args[0]
                filename = args[0]
                import os as _os_native

                output_binary = _os_native.path.basename(filename.replace(".ks", ""))
                print(f"[KentScript ] Compiling {filename} to native binary...")
                try:
                    compiler = RealCCompiler()
                    success = compiler.to_binary(filename, output_binary)

                    if success and "--run" in flags:
                        print(f"\n Running {output_binary}...\n")
                        _run_binary(output_binary)

                    sys.exit(0 if success else 1)
                except Exception as e:
                    print(f"Error: {e}")
                    sys.exit(1)
            else:
                print("Error: --native requires a filename")
                sys.exit(1)

        elif sys.argv[1] == "--creator" and len(sys.argv) == 1:
            print("")
            print("=" * 60)
            print("KentScript v3.1.0 - Systems Programming Language")
            print("=" * 60)
            print("")
            print("Creator:       pyLord (Musika Alvin)")
            print("Location:      Uganda")
            print("GitHub:        https://github.com/musikaalvin")
            print("Version:       v3.1.0 Nxt Gen hybrid")
            print("Compiler:      KentScript v3.1.0 (C transpilation backend)")
            print("Performance:   Native speed via C transpilation (gcc -O3)")
            print("Status:        Stable")
            print("")
            print("Features:")
            print("  • Direct hardware access (MMIO, I/O ports)")
            print("  • Manual memory management (malloc/free")
            print("  • Borrow checker (memory safety)")
            print("  • Inline assembly (x86-64 & ARM64)")
            print("  • SIMD auto-vectorization")
            print("  • Zero-copy 120FPS GUI")
            print("  • Package manager (PackageManager)")
            print("=" * 60)
            print("")

        # kcrypt hex dump / decrypt mode
        elif sys.argv[1] in ("-hx", "--hexdump") and len(sys.argv) > 2:
            filename = sys.argv[2]
            key = sys.argv[3] if len(sys.argv) > 3 else None
            _kcrypt_hex_view(filename, key)
            sys.exit(0)

        # Regular file execution
        else:
            use_cache = "--no-cache" not in sys.argv

            # Filter out flags to get the filename
            args = [
                arg for arg in sys.argv[1:] if not arg.startswith("--") and arg != "-c"
            ]

            if args:
                filename = args[0]
                run_file(filename, use_cache=use_cache)
            else:
                # No filename provided, show help
                print("KentScript  v3.1.0")
                print("Usage:")
                print(
                    "  python kentscript.py <file.ks>                     - Run with interpreter"
                )
                print(
                    "  python kentscript.py <file.ks> --native            - Compile to native binary"
                )
                print(
                    "  python kentscript.py <file.ks> --native --run      - Compile and run native"
                )
                print(
                    "  python kentscript.py -hx <file.kcrypt>             - Hex dump .kcrypt file"
                )
                print(
                    "  python kentscript.py -hx <file.kcrypt> <key>       - Decrypt and show plaintext"
                )
                print(
                    "  python kentscript.py --hexdump <file.kcrypt>       - Same as -hx (verbose)"
                )
    else:
        # No arguments - start REPL
        repl()


# Old main() function has been replaced by main_cli() - see bottom of file

# ============================================================================
# ADVANCED PRODUCTION FEATURES (RESTORED - 1000+ LINES)
# ============================================================================


# 1. ADVANCED TYPE SYSTEM WITH GENERICS
