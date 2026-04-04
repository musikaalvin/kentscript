"""
KentScript C Transpiler

Transpiles KentScript AST to C code with optimizations.
Supports: pointers, type casting, atomics, SIMD, inline assembly, bare metal.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass
import sys
import os

# Add parent directory to path for ks_core imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ks_core import (
    StackAllocationAnalyzer,
    RestrictPointerInjector,
    BranchPredictionOptimizer,
    InterruptHandlerAttribute,
    LLVMOptimizer,
    NativeRuntimeEmitter,
    CompilationMode,
)


# Decorators that are no-ops in C (OOP/Python-specific concepts)
_NOOP_DECORATORS = frozenset(
    {
        "staticmethod",
        "classmethod",
        "property",
        "abstractmethod",
        "override",
        "dataclass",
        "cached_property",
        "final",
        "virtual",
        "slots",
        "frozen",
        "total_ordering",
        # [KS-OS-001] OS-level decorators (handled specially, not as wrappers)
        "kernel",
        "interrupt",
        "syscall",
        "naked",
        "always_inline",
        "aligned",
        "section",
        "volatile_mem",
        "packed",
    }
)

# KentScript stdlib module → C #include directives
_IMPORT_MAP = {
    "math": ["#include <math.h>"],
    "thread": ["#include <pthread.h>"],
    "threads": ["#include <pthread.h>"],
    "regex": ["#include <regex.h>"],
    "net": [
        "#include <sys/socket.h>",
        "#include <netinet/in.h>",
        "#include <arpa/inet.h>",
    ],
    "network": [
        "#include <sys/socket.h>",
        "#include <netinet/in.h>",
        "#include <arpa/inet.h>",
    ],
    "socket": [
        "#include <sys/socket.h>",
        "#include <netinet/in.h>",
        "#include <arpa/inet.h>",
    ],
    "json": [],  # no direct C equivalent
    "os": [],  # already included via unistd.h
    "sys": [],
    "time": [],  # already included via time.h
    "random": [],  # already included via stdlib.h
    "string": [],  # already included via string.h
    "fileio": [],  # already included via stdio.h
    "path": [],  # already included via stdio.h
    "io": [],
    "crypto": ["#include <openssl/sha.h>", "#include <openssl/md5.h>"],
    "hash": ["#include <openssl/sha.h>"],
    "signal": ["#include <signal.h>"],
    "process": ["#include <sys/wait.h>"],
    "atomic": ["#include <stdatomic.h>"],
    "simd": [
        "#ifdef __aarch64__\n#include <arm_neon.h>\n#else\n#include <immintrin.h>\n#endif"
    ],
}


class CTranspiler:
    """
    Transpiles KentScript AST to C code.
    Handles: let/const, functions, if/else, while, for, return,
             print, f-strings, arithmetic, comparison, string ops,
             nested functions, and more.
    BENCHMARK MODE: Adds volatile and asm barriers for honest measurements.
    """

    def __init__(self, benchmark_mode=False):
        self.code_lines = []
        self.indent_level = 0
        self.string_vars = set()  # vars known to be strings
        self.numeric_vars = set()  # vars known to be numeric
        self.bool_vars = set()  # vars known to be bools
        self.func_return_types = {}  # func name -> 'int'|'double'|'str'|'void'
        self.declared_vars = {}  # name -> C type
        self._str_buf_count = 0  # unique string buffer IDs
        self._label_count = 0
        self.benchmark_mode = benchmark_mode
        self.class_names = set()  # names of defined classes for constructor lookup
        self.class_instance_types = {}  # class name -> C type for instances
        self.current_class_context = None  # Current class being transpiled
        self._in_method_body = False  # Flag for transpiling method body
        self._enum_names = set()  # names of defined enums for member access
        self._source_filename = None  # Original .ks filename for #line directives
        self._source_lines = None  # Original source lines for #line directives

        # [KS-REF-037] Low-level optimization framework
        self.stack_allocator = StackAllocationAnalyzer()
        self.restrict_injector = RestrictPointerInjector()
        self.branch_optimizer = BranchPredictionOptimizer()
        self.interrupt_handlers: Dict[str, InterruptHandlerAttribute] = {}
        self.pgo_profile: Optional[Dict] = None
        self.enable_optimizations = True

        # [KS-REF-038] GameChanger optimizations
        self.llvm_optimizer = LLVMOptimizer(optimization_level=3)
        self.native_runtime = NativeRuntimeEmitter()
        self.static_types = {}  # var -> PrimitiveType
        self.bare_metal_mode = False
        self.compilation_mode = CompilationMode.AOT

    # ------------------------------------------------------------------ helpers

    def _collect_free_vars(self, body_nodes, params):
        """Return list of (name, c_type) for variables captured from outer scope."""
        param_set = set(params)
        free = {}
        all_vars = dict(getattr(self, "_global_types", {}))
        all_vars.update(self.declared_vars)

        def _walk(node):
            if node is None:
                return
            cls = node.__class__.__name__
            if cls == "Identifier":
                n = node.name
                if (
                    n not in param_set
                    and n in all_vars
                    and n not in free
                    and n not in ("NULL", "true", "false", "None", "none")
                ):
                    free[n] = all_vars[n]
            for attr in vars(node).values() if hasattr(node, "__dict__") else []:
                if isinstance(attr, list):
                    for item in attr:
                        if hasattr(item, "__class__") and hasattr(item, "__dict__"):
                            _walk(item)
                elif hasattr(attr, "__dict__"):
                    _walk(attr)

        for n in body_nodes if isinstance(body_nodes, list) else [body_nodes]:
            _walk(n)
        return list(free.items())

    def _emit_closure(self, func_name, fn_params, free_vars, body_emit_fn, ret_type="long long"):
        """
        Emit a closure: heap-allocated env struct with pointer fields so mutations
        to captured vars are visible through the pointer (by-reference capture).

        Emits:
          typedef struct { T* name; ... } _cls_func_name;
          static _cls_func_name func_name_env;
          static R func_name_inner(_cls_func_name* _cls, params...) { *_cls->name ... }
          static R func_name(params...) { return func_name_inner(&func_name_env, params); }
        """
        struct_name = f"_cls_{func_name}"
        # Struct stores pointers to captured vars (by-reference)
        self._emit(f"typedef struct {{")
        for vn, vt in free_vars:
            self._emit(f"    {vt}* {vn};  /* captured by ref */")
        self._emit(f"}} {struct_name};")
        self._emit(f"static {struct_name} {func_name}_env;")
        # Inner function: dereferences pointers
        cls_params = f"{struct_name}* _cls" + (
            "".join(f", long long {p}" for p in fn_params)
        )
        self._emit(f"static {ret_type} {func_name}_inner({cls_params}) {{")
        self.indent_level += 1
        for vn, vt in free_vars:
            self._emit(f"{vt}* {vn} = _cls->{vn};  /* ptr to outer var */")
            # Make the captured var accessible as a value via a local alias
            self._emit(f"#define {vn} (*{vn})")
        body_emit_fn()
        for vn, _ in free_vars:
            self._emit(f"#undef {vn}")
        # Return appropriate zero value based on type
        if ret_type == "char*":
            self._emit('return "";')
        elif ret_type == "double":
            self._emit("return 0.0;")
        else:
            self._emit("return 0LL;")
        self.indent_level -= 1
        self._emit("}")
        # Wrapper with original signature
        wrap_params = ", ".join(f"long long {p}" for p in fn_params) or "void"
        wrap_args = ", ".join(fn_params)
        self._emit(f"static {ret_type} {func_name}({wrap_params}) {{")
        self._emit(
            f"    return {func_name}_inner(&{func_name}_env{', ' + wrap_args if wrap_args else ''});"
        )
        self._emit(f"}}")
        self._emit()

    def _collect_lambdas(self, nodes):
        """Pre-pass to collect all lambda expressions and anonymous functions"""
        for node in nodes:
            self._collect_lambdas_from_node(node)

    def _collect_lambdas_from_node(self, node):
        """Recursively collect lambdas and anonymous FunctionDef nodes from a node"""
        if node is None:
            return

        cls = node.__class__.__name__

        if cls == "LambdaExpr":
            lambda_id = len(self._lambda_funcs)
            func_name = f"_ks_lambda_{lambda_id}"
            params_str = ", ".join(f"long long {p}" for p in node.params)
            # Store placeholder - will fill body later
            self._lambda_funcs.append(
                (func_name, params_str, node.body, len(node.params))
            )
            # Recursively collect from body
            self._collect_lambdas_from_node(node.body)
        elif cls == "ReturnStmt":
            # Check if returning an anonymous function
            if hasattr(node, "value") and node.value is not None:
                val = node.value
                if val.__class__.__name__ == "FunctionDef":
                    anon_id = len(self._lambda_funcs)
                    fn_name = getattr(val, "name", None) or f"_ks_anon_{anon_id}"
                    if not fn_name or fn_name.startswith("__lambda_"):
                        fn_name = f"_ks_anon_{anon_id}"
                    params = [p for p in (val.params or []) if p != "self"]
                    params_str = ", ".join(f"long long {p}" for p in params)
                    self._lambda_funcs.append((fn_name, params_str, val, len(params)))
                    # Store the resolved name on the node for later lookup
                    val._resolved_anon_name = fn_name
                else:
                    self._collect_lambdas_from_node(val)
        elif cls == "LetDecl":
            if hasattr(node, "value") and node.value is not None:
                val = node.value
                if val.__class__.__name__ == "FunctionDef":
                    anon_id = len(self._lambda_funcs)
                    fn_name = getattr(val, "name", None) or f"_ks_anon_{anon_id}"
                    if not fn_name or fn_name.startswith("__lambda_"):
                        fn_name = f"_ks_anon_{anon_id}"
                    params = [p for p in (val.params or []) if p != "self"]
                    params_str = ", ".join(f"long long {p}" for p in params)
                    self._lambda_funcs.append((fn_name, params_str, val, len(params)))
                    val._resolved_anon_name = fn_name
                else:
                    self._collect_lambdas_from_node(val)
        elif cls == "Assignment":
            if hasattr(node, "value"):
                self._collect_lambdas_from_node(node.value)
        elif cls == "FunctionDef":
            if hasattr(node, "body"):
                for stmt in node.body:
                    self._collect_lambdas_from_node(stmt)
        elif cls == "BinaryOp":
            self._collect_lambdas_from_node(node.left)
            self._collect_lambdas_from_node(node.right)
        elif cls == "UnaryOp":
            self._collect_lambdas_from_node(node.operand)
        elif cls == "IfStmt":
            for stmt in getattr(node, "then_block", None) or []:
                self._collect_lambdas_from_node(stmt)
            for stmt in getattr(node, "else_block", None) or []:
                self._collect_lambdas_from_node(stmt)
        elif cls == "WhileStmt":
            for stmt in getattr(node, "body", None) or []:
                self._collect_lambdas_from_node(stmt)
        elif cls == "ForStmt":
            for stmt in getattr(node, "body", None) or []:
                self._collect_lambdas_from_node(stmt)

    def _indent(self):
        return "    " * self.indent_level

    def _emit(self, line=""):
        if line:
            self.code_lines.append(self._indent() + line)
        else:
            self.code_lines.append("")

    def _emit_line_directive(self, ks_line, ks_filename=None):
        """Emit a #line directive to map C code back to KentScript source."""
        if ks_line and ks_line > 0:
            fname = ks_filename or self._source_filename or "input.ks"
            self.code_lines.append(f'#line {ks_line} "{fname}"')

    def _new_strbuf(self):
        self._str_buf_count += 1
        return f"_ks_str_{self._str_buf_count}"

    def _escape_c_string(self, s):
        """Escape a Python string for use in a C string literal."""
        return (
            s.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )

    def _safe_c_name(self, name):
        """Convert KentScript variable name to safe C identifier, avoiding C stdlib conflicts."""
        # C stdlib function names that would conflict
        reserved = {
            "stat",
            "printf",
            "scanf",
            "malloc",
            "free",
            "calloc",
            "realloc",
            "memcpy",
            "memmove",
            "memset",
            "memcmp",
            "strlen",
            "strcpy",
            "strncpy",
            "strcat",
            "strncat",
            "strcmp",
            "strncmp",
            "strchr",
            "strrchr",
            "abs",
            "labs",
            "div",
            "ldiv",
            "rand",
            "srand",
            "exit",
            "atexit",
            "system",
            "getenv",
            "setenv",
            "unsetenv",
            "time",
            "clock",
            "localtime",
            "open",
            "close",
            "read",
            "write",
            "lseek",
            "stat",
            "fstat",
            "unlink",
            "fork",
            "exec",
            "wait",
            "pipe",
            "signal",
            "raise",
            "assert",
        }
        if name in reserved:
            return f"ks_{name}"
        return name

    # ------------------------------------------------------------------ top level

    def transpile(self, ast_nodes, source_filename=None, source_code=None):
        """Transpile a list of AST nodes to a complete C program."""
        self._source_filename = source_filename
        if source_code:
            self._source_lines = source_code.splitlines() if isinstance(source_code, str) else source_code
        self.code_lines = []
        self.indent_level = 0

        # First pass: collect all lambda expressions
        self._lambda_funcs = []
        self._collect_lambdas(ast_nodes)

        # --- Preamble ---
        self._emit("#define _POSIX_C_SOURCE 200809L")
        self._emit("#define _DEFAULT_SOURCE")
        self._emit("#include <stdio.h>")
        self._emit("#include <stdlib.h>")
        self._emit("#include <string.h>")
        self._emit("#include <ctype.h>")
        self._emit("#include <math.h>")
        self._emit("#include <time.h>")
        self._emit("#include <stdarg.h>")
        self._emit("#include <stdint.h>")
        self._emit("#include <sys/mman.h>")
        self._emit("#include <unistd.h>")
        self._emit("#include <sys/syscall.h>")
        self._emit()
        self._emit("/* KentScript compatibility macros */")
        self._emit("#define None ((long long)0)")
        self._emit("#define true 1")
        self._emit("#define false 0")

        # --- Emit #includes and global variable declarations for imported stdlib modules ---
        _emitted_includes = {
            # Already in standard preamble — don't re-emit
            "#include <stdio.h>",
            "#include <stdlib.h>",
            "#include <string.h>",
            "#include <ctype.h>",
            "#include <math.h>",
            "#include <time.h>",
            "#include <stdarg.h>",
            "#include <stdint.h>",
            "#include <sys/mman.h>",
            "#include <unistd.h>",
            "#include <sys/syscall.h>",
        }
        _emitted_module_vars = set()
        _GLOBAL_MODULE_VARS = {
            "http": "long long _ks_http_mod = 0;",
            "json": "long long _ks_json_mod = 0;",
            "fileio": "void* _ks_fileio_mod = 0;",
            "path": "void* _ks_path_mod = 0;",
            "network": "void* _ks_network_mod = 0;",
            "subprocess": "void* _ks_subprocess_mod = 0;",
            "syscall": "void* _ks_syscall_mod = 0;",
            "math": "void* _ks_math_mod = 0;",
            "os": "void* _ks_os_mod = 0;",
            "random": "void* _ks_random_mod = 0;",
            "time": "void* _ks_time_mod = 0;",
        }
        for node in ast_nodes:
            if node.__class__.__name__ == "ImportStmt":
                mod = node.module.split(".")[0].lower()
                for inc in _IMPORT_MAP.get(mod, []):
                    if inc not in _emitted_includes:
                        self._emit(inc)
                        _emitted_includes.add(inc)
                # Emit global variable declaration for known stdlib modules
                if mod in _GLOBAL_MODULE_VARS and mod not in _emitted_module_vars:
                    self._emit(_GLOBAL_MODULE_VARS[mod])
                    _emitted_module_vars.add(mod)

        self._emit()
        self._emit("/* ===== HOOK 2: SIMD & Hardware Optimization Macros ===== */")
        self._emit("#define RESTRICT __restrict")
        self._emit("#define ALIGNED(n) __attribute__((aligned(n)))")
        self._emit("#define ALIGNED_16 __attribute__((aligned(16)))")
        self._emit("#define ALIGNED_32 __attribute__((aligned(32)))")
        self._emit("#define HOT __attribute__((hot))")
        self._emit("#define COLD __attribute__((cold))")
        self._emit("#define INLINE __attribute__((always_inline)) inline")
        self._emit("#define NORETURN __attribute__((noreturn))")
        self._emit("#define LIKELY(x) __builtin_expect(!!(x), 1)")
        self._emit("#define UNLIKELY(x) __builtin_expect(!!(x), 0)")
        self._emit("/* ===== END HOOK 2 ===== */")
        self._emit()
        self._emit("// Progress bar helpers")
        self._emit("char* _ks_progress_bar(int percent, int width, char* color) {")
        self._emit("    static char buf[256];")
        self._emit("    int filled = (percent * width) / 100;")
        self._emit("    int empty = width - filled;")
        self._emit("    int pos = 0;")
        self._emit(
            '    for (int i = 0; i < filled; i++) pos += sprintf(buf + pos, "█");'
        )
        self._emit(
            '    for (int i = 0; i < empty; i++) pos += sprintf(buf + pos, "░");'
        )
        self._emit('    pos += sprintf(buf + pos, " %d%%", percent);')
        self._emit("    return buf;")
        self._emit("}")
        self._emit()
        self._emit(
            "char* _ks_progress_bar_cyber(int percent, int width, char* color) {"
        )
        self._emit("    static char buf[256];")
        self._emit("    int filled = (percent * width) / 100;")
        self._emit("    int empty = width - filled;")
        self._emit('    char* chars[] = {"▓", "▒", "░"};')
        self._emit("    int pos = 0;")
        self._emit('    pos += sprintf(buf + pos, "╭");')
        self._emit(
            '    for (int i = 0; i < filled; i++) pos += sprintf(buf + pos, "%s", chars[i % 3]);'
        )
        self._emit(
            '    for (int i = 0; i < empty; i++) pos += sprintf(buf + pos, "░");'
        )
        self._emit(
            '    pos += sprintf(buf + pos, "╮ %5.1f%% %s", (double)percent, percent < 100 ? "▶" : "█");'
        )
        self._emit("    return buf;")
        self._emit("}")
        self._emit()
        self._emit("char* _ks_progress_bar_matrix(int percent, int width) {")
        self._emit("    static char buf[512];")
        self._emit("    int filled = (percent * width) / 100;")
        self._emit('    char* chars[] = {"█", "▓", "▒", "░"};')
        self._emit("    int pos = 0;")
        self._emit(
            '    pos += sprintf(buf + pos, "┌"); for (int i = 0; i < width; i++) pos += sprintf(buf + pos, "─"); pos += sprintf(buf + pos, "┐\\n");'
        )
        self._emit('    pos += sprintf(buf + pos, "│");')
        self._emit(
            '    for (int i = 0; i < filled; i++) pos += sprintf(buf + pos, "%s", chars[i % 4]);'
        )
        self._emit(
            '    for (int i = filled; i < width; i++) pos += sprintf(buf + pos, "░");'
        )
        self._emit('    pos += sprintf(buf + pos, "│ %d%%\\n", percent);')
        self._emit(
            '    pos += sprintf(buf + pos, "└"); for (int i = 0; i < width; i++) pos += sprintf(buf + pos, "─"); pos += sprintf(buf + pos, "┘");'
        )
        self._emit("    return buf;")
        self._emit("}")
        self._emit()
        self._emit("// Colored output helper")
        self._emit("static int _color_name_to_code(const char* name) {")
        self._emit("    // FG colors")
        self._emit('    if (strcmp(name, "black") == 0) return 30;')
        self._emit('    if (strcmp(name, "red") == 0) return 31;')
        self._emit('    if (strcmp(name, "green") == 0) return 32;')
        self._emit('    if (strcmp(name, "yellow") == 0) return 33;')
        self._emit('    if (strcmp(name, "blue") == 0) return 34;')
        self._emit('    if (strcmp(name, "magenta") == 0) return 35;')
        self._emit('    if (strcmp(name, "cyan") == 0) return 36;')
        self._emit('    if (strcmp(name, "white") == 0) return 37;')
        self._emit(
            '    if (strcmp(name, "bright_black") == 0 || strcmp(name, "gray") == 0 || strcmp(name, "grey") == 0) return 90;'
        )
        self._emit('    if (strcmp(name, "bright_red") == 0) return 91;')
        self._emit('    if (strcmp(name, "bright_green") == 0) return 92;')
        self._emit('    if (strcmp(name, "bright_yellow") == 0) return 93;')
        self._emit('    if (strcmp(name, "bright_blue") == 0) return 94;')
        self._emit('    if (strcmp(name, "bright_magenta") == 0) return 95;')
        self._emit('    if (strcmp(name, "bright_cyan") == 0) return 96;')
        self._emit('    if (strcmp(name, "bright_white") == 0) return 97;')
        self._emit('    if (strcmp(name, "dim") == 0) return 2;')
        self._emit('    if (strcmp(name, "bold") == 0) return 1;')
        self._emit('    if (strcmp(name, "italic") == 0) return 3;')
        self._emit('    if (strcmp(name, "underline") == 0) return 4;')
        self._emit("    return 30; // default")
        self._emit("}")
        self._emit()
        self._emit("char* _ks_colored(char* text, char* fg, char* bg, char* style) {")
        self._emit("    static char buf[4096];")
        self._emit("    int codes[10]; int nc = 0;")
        self._emit(
            '    if (fg && strcmp(fg, "none") != 0) codes[nc++] = _color_name_to_code(fg);'
        )
        self._emit(
            '    if (bg && strcmp(bg, "none") != 0) codes[nc++] = _color_name_to_code(bg) + 10;'
        )
        self._emit(
            '    if (style && strcmp(style, "none") != 0) codes[nc++] = _color_name_to_code(style);'
        )
        self._emit('    int pos = sprintf(buf, "\\033[");')
        self._emit(
            '    for (int i = 0; i < nc; i++) pos += sprintf(buf + pos, "%d%s", codes[i], i < nc-1 ? ";" : "m");'
        )
        self._emit('    pos += sprintf(buf + pos, "%s\\033[0m", text);')
        self._emit("    return buf;")
        self._emit("}")
        self._emit()
        self._emit(
            "/* ---- Hardware I/O Port Access (Cross-Platform: x86-64 & ARM64) ---- */"
        )
        self._emit(
            "#if defined(__x86_64__) || defined(__i386__) || defined(_M_X64) || defined(_M_IX86)"
        )
        self._emit("  /* x86/x64: Uses I/O Ports (inb/outb) */")
        self._emit("  static inline unsigned char inb(unsigned short port) {")
        self._emit("      unsigned char rv;")
        self._emit(
            '      __asm__ __volatile__ ("inb %w1, %b0" : "=a" (rv) : "Nd" (port));'
        )
        self._emit("      return rv;")
        self._emit("  }")
        self._emit("  static inline unsigned short inw(unsigned short port) {")
        self._emit("      unsigned short rv;")
        self._emit(
            '      __asm__ __volatile__ ("inw %w1, %w0" : "=a" (rv) : "Nd" (port));'
        )
        self._emit("      return rv;")
        self._emit("  }")
        self._emit("  static inline unsigned int inl(unsigned short port) {")
        self._emit("      unsigned int rv;")
        self._emit(
            '      __asm__ __volatile__ ("inl %w1, %0" : "=a" (rv) : "Nd" (port));'
        )
        self._emit("      return rv;")
        self._emit("  }")
        self._emit(
            "  static inline void outb(unsigned char value, unsigned short port) {"
        )
        self._emit(
            '      __asm__ __volatile__ ("outb %b0, %w1" : : "a" (value), "Nd" (port));'
        )
        self._emit("  }")
        self._emit(
            "  static inline void outw(unsigned short value, unsigned short port) {"
        )
        self._emit(
            '      __asm__ __volatile__ ("outw %w0, %w1" : : "a" (value), "Nd" (port));'
        )
        self._emit("  }")
        self._emit(
            "  static inline void outl(unsigned int value, unsigned short port) {"
        )
        self._emit(
            '      __asm__ __volatile__ ("outl %0, %w1" : : "a" (value), "Nd" (port));'
        )
        self._emit("  }")
        self._emit(
            "#elif defined(__aarch64__) || defined(__arm__) || defined(_M_ARM64)"
        )
        self._emit("  /* ARM64/ARM: Uses Memory-Mapped I/O (MMIO) - NO port I/O */")
        self._emit("  /* RTC is accessed via fixed MMIO address (e.g., 0x09010000) */")
        self._emit("  static inline unsigned char inb(unsigned short port) {")
        self._emit("      /* ARM has no port I/O - stub returns 0 */")
        self._emit("      (void)port; /* suppress unused warning */")
        self._emit("      return 0;")
        self._emit("  }")
        self._emit("  static inline unsigned short inw(unsigned short port) {")
        self._emit("      (void)port;")
        self._emit("      return 0;")
        self._emit("  }")
        self._emit("  static inline unsigned int inl(unsigned short port) {")
        self._emit("      (void)port;")
        self._emit("      return 0;")
        self._emit("  }")
        self._emit(
            "  static inline void outb(unsigned char value, unsigned short port) {"
        )
        self._emit("      (void)value; (void)port;")
        self._emit("  }")
        self._emit(
            "  static inline void outw(unsigned short value, unsigned short port) {"
        )
        self._emit("      (void)value; (void)port;")
        self._emit("  }")
        self._emit(
            "  static inline void outl(unsigned int value, unsigned short port) {"
        )
        self._emit("      (void)value; (void)port;")
        self._emit("  }")
        self._emit("#else")
        self._emit(
            '  #error "Unsupported architecture. KentScript supports x86/x64 and ARM64."'
        )
        self._emit("#endif")
        self._emit()
        self._emit("#ifdef __aarch64__")
        self._emit("#include <arm_neon.h>")
        self._emit("static inline uint64_t read_cycle_counter(void) {")
        self._emit("    uint64_t cycles;")
        self._emit('    __asm__ __volatile__("mrs %0, pmccntr_el0" : "=r" (cycles));')
        self._emit("    return cycles;")
        self._emit("}")
        self._emit("static inline void enable_cycle_counter(void) {")
        self._emit("    uint64_t val;")
        self._emit('    __asm__ __volatile__("mrs %0, pmcr_el0" : "=r" (val));')
        self._emit("    val |= (1 << 0);")
        self._emit('    __asm__ __volatile__("msr pmcr_el0, %0" : : "r" (val));')
        self._emit("}")
        self._emit("#else")
        self._emit("static inline uint64_t read_cycle_counter(void) {")
        self._emit("    struct timespec ts;")
        self._emit("    clock_gettime(CLOCK_MONOTONIC, &ts);")
        self._emit("    return ts.tv_sec * 1000000000ULL + ts.tv_nsec;")
        self._emit("}")
        self._emit("static inline void enable_cycle_counter(void) {}")
        self._emit("#endif")
        self._emit()
        self._emit("/* ---- Memory-Mapped I/O (MMIO) Helper Functions ---- */")
        self._emit("#include <fcntl.h>")
        self._emit("#include <unistd.h>")
        self._emit("#include <sys/mman.h>")
        self._emit("#ifdef _WIN32")
        self._emit("#include <windows.h>")
        self._emit("#else")
        self._emit("#include <sys/types.h>")
        self._emit("#include <sys/stat.h>")
        self._emit("#endif")
        self._emit("static long long _ks_read_mmio(unsigned long addr, int size) {")
        self._emit('    int fd = open("/dev/mem", O_RDONLY);')
        self._emit("    if (fd < 0) return 0;")
        self._emit("    unsigned long page_size = 4096;")
        self._emit("    unsigned long page_addr = (addr / page_size) * page_size;")
        self._emit("    unsigned long offset = addr - page_addr;")
        self._emit(
            "    void *map = mmap(NULL, page_size, PROT_READ, MAP_SHARED, fd, page_addr);"
        )
        self._emit("    if (map == MAP_FAILED) { close(fd); return 0; }")
        self._emit("    long long result = 0;")
        self._emit("    if (size == 1) {")
        self._emit("        unsigned char *p = (unsigned char *)map + offset;")
        self._emit("        result = (long long)*p;")
        self._emit("    } else if (size == 2) {")
        self._emit(
            "        unsigned short *p = (unsigned short *)((unsigned char *)map + offset);"
        )
        self._emit("        result = (long long)*p;")
        self._emit("    } else if (size == 4) {")
        self._emit(
            "        unsigned int *p = (unsigned int *)((unsigned char *)map + offset);"
        )
        self._emit("        result = (long long)*p;")
        self._emit("    } else if (size == 8) {")
        self._emit(
            "        unsigned long long *p = (unsigned long long *)((unsigned char *)map + offset);"
        )
        self._emit("        result = (long long)*p;")
        self._emit("    }")
        self._emit("    munmap(map, page_size);")
        self._emit("    close(fd);")
        self._emit("    return result;")
        self._emit("}")
        self._emit(
            "static void _ks_write_mmio(unsigned long addr, long long value, int size) {"
        )
        self._emit('    int fd = open("/dev/mem", O_RDWR);')
        self._emit("    if (fd < 0) return;")
        self._emit("    unsigned long page_size = 4096;")
        self._emit("    unsigned long page_addr = (addr / page_size) * page_size;")
        self._emit("    unsigned long offset = addr - page_addr;")
        self._emit(
            "    void *map = mmap(NULL, page_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, page_addr);"
        )
        self._emit("    if (map == MAP_FAILED) { close(fd); return; }")
        self._emit("    if (size == 1) {")
        self._emit("        unsigned char *p = (unsigned char *)map + offset;")
        self._emit("        *p = (unsigned char)value;")
        self._emit("    } else if (size == 2) {")
        self._emit(
            "        unsigned short *p = (unsigned short *)((unsigned char *)map + offset);"
        )
        self._emit("        *p = (unsigned short)value;")
        self._emit("    } else if (size == 4) {")
        self._emit(
            "        unsigned int *p = (unsigned int *)((unsigned char *)map + offset);"
        )
        self._emit("        *p = (unsigned int)value;")
        self._emit("    } else if (size == 8) {")
        self._emit(
            "        unsigned long long *p = (unsigned long long *)((unsigned char *)map + offset);"
        )
        self._emit("        *p = (unsigned long long)value;")
        self._emit("    }")
        self._emit("    munmap(map, page_size);")
        self._emit("    close(fd);")
        self._emit("}")
        self._emit()
        self._emit("/* ---- KentScript runtime [KS-REF-020] ----                   */")
        # Include ks_runtime.h for full function declarations
        self._emit('#include "ks_runtime.h"')
        self._emit()
        self._emit(
            "/* ---- Fallback inline helpers (only if ks_runtime.h functions missing) ---- */"
        )
        self._emit("#ifndef KS_RUNTIME_HAVE_ALL_FUNCS")
        self._emit("static char _ks_bufs[64][4096];")
        self._emit("static int  _ks_buf_idx = 0;")
        self._emit("static char* _ks_newbuf(void) {")
        self._emit("    _ks_buf_idx = (_ks_buf_idx + 1) % 64;")
        self._emit("    _ks_bufs[_ks_buf_idx][0] = 0;")
        self._emit("    return _ks_bufs[_ks_buf_idx];")
        self._emit("}")
        self._emit("static char* _ks_str_int(long long v) {")
        self._emit("    char *b = _ks_newbuf();")
        self._emit('    snprintf(b, 4096, "%lld", v); return b;')
        self._emit("}")
        self._emit("static char* _ks_str_hex(long long v) {")
        self._emit("    char *b = _ks_newbuf();")
        self._emit('    snprintf(b, 4096, "%llx", v); return b;')
        self._emit("}")
        self._emit("static char* _ks_str_dbl(double v) {")
        self._emit("    char *b = _ks_newbuf();")
        self._emit('    if (v == (long long)v) snprintf(b,4096,"%.1f",v);')
        self._emit('    else snprintf(b,4096,"%g",v); return b;')
        self._emit("}")
        self._emit("static char* _ks_str_array(long long* arr, long long len) {")
        self._emit("    char *b = _ks_newbuf();")
        self._emit("    int pos = 0;")
        self._emit('    pos += snprintf(b + pos, 4096 - pos, "[");')
        self._emit("    for (long long i = 0; i < len && pos < 4090; i++) {")
        self._emit('        if (i > 0) pos += snprintf(b + pos, 4096 - pos, ", ");')
        self._emit('        pos += snprintf(b + pos, 4096 - pos, "%lld", arr[i]);')
        self._emit("    }")
        self._emit('    snprintf(b + pos, 4096 - pos, "]");')
        self._emit("    return b;")
        self._emit("}")
        self._emit("static char* _ks_concat(const char* a, const char* b) {")
        self._emit("    char *r = _ks_newbuf();")
        self._emit('    snprintf(r, 4096, "%s%s", a, b); return r;')
        self._emit("}")
        self._emit("static char* _ks_format_value(long long v, const char* fmt) {")
        self._emit("    char *r = _ks_newbuf(); char spec[64];")
        self._emit('    snprintf(spec, sizeof(spec), "%%%s", fmt);')
        self._emit("    snprintf(r, 4096, spec, v); return r;")
        self._emit("}")
        self._emit("static char* _ks_format_value_f(double v, const char* fmt) {")
        self._emit("    char *r = _ks_newbuf(); char spec[64];")
        self._emit('    snprintf(spec, sizeof(spec), "%%%s", fmt);')
        self._emit("    snprintf(r, 4096, spec, v); return r;")
        self._emit("}")
        # Forward-declare ks_array so string functions can use it
        self._emit("typedef struct { long long* data; long long length; } ks_array;")
        self._emit("/* String methods */")
        self._emit("static char* _ks_str_upper(const char* s) {")
        self._emit("    char *r = _ks_newbuf(); int i = 0;")
        self._emit("    while (s[i] && i < 4095) { r[i] = toupper(s[i]); i++; }")
        self._emit("    r[i] = 0; return r;")
        self._emit("}")
        self._emit("static char* _ks_str_lower(const char* s) {")
        self._emit("    char *r = _ks_newbuf(); int i = 0;")
        self._emit("    while (s[i] && i < 4095) { r[i] = tolower(s[i]); i++; }")
        self._emit("    r[i] = 0; return r;")
        self._emit("}")
        self._emit("static char* _ks_str_strip(const char* s) {")
        self._emit("    while (*s && isspace(*s)) s++;")
        self._emit("    const char *e = s + strlen(s) - 1;")
        self._emit("    while (e > s && isspace(*e)) e--;")
        self._emit("    char *r = _ks_newbuf(); int len = e - s + 1;")
        self._emit("    if (len > 0) { memcpy(r, s, len); r[len] = 0; } else r[0] = 0;")
        self._emit("    return r;")
        self._emit("}")
        self._emit(
            "static char* _ks_str_replace(const char* s, const char* old, const char* new_s) {"
        )
        self._emit("    char *r = _ks_newbuf(); const char *p = s; int rlen = 0;")
        self._emit("    int olen = strlen(old), nlen = strlen(new_s);")
        self._emit("    while (*p && rlen < 4090) {")
        self._emit("        if (strncmp(p, old, olen) == 0) {")
        self._emit("            memcpy(r+rlen, new_s, nlen); rlen += nlen; p += olen;")
        self._emit("        } else { r[rlen++] = *p++; }")
        self._emit("    }")
        self._emit("    r[rlen] = 0; return r;")
        self._emit("}")
        self._emit("static char* _ks_str_find(const char* s, const char* needle) {")
        self._emit("    const char* p = strstr(s, needle);")
        self._emit('    if (!p) return "-1";')
        self._emit(
            '    char *r = _ks_newbuf(); snprintf(r, 32, "%lld", (long long)(p - s)); return r;'
        )
        self._emit("}")
        self._emit(
            "static char* _ks_str_substring(const char* s, long long start, long long end) {"
        )
        self._emit("    long long len = strlen(s);")
        self._emit("    if (start < 0) start = 0; if (end > len) end = len;")
        self._emit("    char *r = _ks_newbuf(); long long n = end - start;")
        self._emit("    if (n > 0) { memcpy(r, s+start, n); r[n] = 0; } else r[0] = 0;")
        self._emit("    return r;")
        self._emit("}")
        self._emit("static int _ks_str_endswith(const char* s, const char* suffix) {")
        self._emit("    long long sl = strlen(s), el = strlen(suffix);")
        self._emit("    return sl >= el && strcmp(s + sl - el, suffix) == 0;")
        self._emit("}")
        # ks_array split: returns a ks_array of char* parts
        self._emit("static ks_array _ks_str_split(const char* s, const char* sep) {")
        self._emit("    long long cap = 16, count = 0;")
        self._emit(
            "    long long** parts = (long long**)malloc(cap * sizeof(long long*));"
        )
        self._emit("    int seplen = strlen(sep); const char* p = s;")
        self._emit("    while (*p) {")
        self._emit("        const char* found = strstr(p, sep);")
        self._emit("        if (!found) found = p + strlen(p);")
        self._emit("        long long n = found - p;")
        self._emit(
            "        char* part = (char*)malloc(n + 1); memcpy(part, p, n); part[n] = 0;"
        )
        self._emit(
            "        if (count >= cap) { cap *= 2; parts = (long long**)realloc(parts, cap * sizeof(long long*)); }"
        )
        self._emit("        parts[count++] = (long long*)part;")
        self._emit("        p = *found ? found + seplen : found;")
        self._emit("    }")
        self._emit(
            "    ks_array arr; arr.data = (long long*)parts; arr.length = count; return arr;"
        )
        self._emit("}")
        self._emit("static void _ks_array_append(ks_array* arr, long long val) {")
        self._emit(
            "    long long* new_data = (long long*)malloc((arr->length + 1) * sizeof(long long));"
        )
        self._emit(
            "    if (arr->data) memcpy(new_data, arr->data, arr->length * sizeof(long long));"
        )
        self._emit("    new_data[arr->length] = val;")
        self._emit("    arr->data = new_data; arr->length++;")
        self._emit("}")
        self._emit("static long long _ks_array_pop(ks_array* arr) {")
        self._emit("    if (arr->length == 0) return 0;")
        self._emit("    long long val = arr->data[arr->length - 1];")
        self._emit("    arr->length--; return val;")
        self._emit("}")
        self._emit("static char* _ks_str_join(const char* sep, ks_array arr) {")
        self._emit("    char *r = _ks_newbuf(); int pos = 0;")
        self._emit("    for (long long i = 0; i < arr.length && pos < 4090; i++) {")
        self._emit(
            "        if (i > 0) { int sl = strlen(sep); memcpy(r+pos, sep, sl); pos += sl; }"
        )
        self._emit("        const char* s = (const char*)arr.data[i];")
        self._emit("        int sl = strlen(s); memcpy(r+pos, s, sl); pos += sl;")
        self._emit("    }")
        self._emit("    r[pos] = 0; return r;")
        self._emit("}")

        # Add missing standard library functions
        self._emit("/* Missing standard library functions */")
        self._emit("static long long _ks_len(const char* s) {")
        self._emit("    return (long long)strlen(s);")
        self._emit("}")
        self._emit("static long long _ks_ord(const char* s) {")
        self._emit("    return s[0] ? (long long)(unsigned char)s[0] : 0;")
        self._emit("}")
        self._emit("static char* _ks_chr(long long code) {")
        self._emit("    char *r = _ks_newbuf();")
        self._emit("    if (code >= 0 && code <= 255) { r[0] = (char)code; r[1] = 0; }")
        self._emit("    else { r[0] = 0; }")
        self._emit("    return r;")
        self._emit("}")
        self._emit(
            "static long long _ks_contains(const char* haystack, const char* needle) {"
        )
        self._emit("    return strstr(haystack, needle) != NULL ? 1 : 0;")
        self._emit("}")
        self._emit("static char* _ks_str_at(const char* s, long long index) {")
        self._emit("    long long len = strlen(s);")
        self._emit('    if (index < 0 || index >= len) return "";')
        self._emit("    char *r = _ks_newbuf();")
        self._emit("    r[0] = s[index]; r[1] = 0;")
        self._emit("    return r;")
        self._emit("}")
        self._emit("static char* _ks_type(long long v) {")
        self._emit('    return "unknown";')
        self._emit("}")

        self._emit("/* Dict hash table - simple implementation */")
        self._emit("typedef struct _ks_dict_node {")
        self._emit("    char* key;")
        self._emit("    union { long long i; char* s; };")
        self._emit("    int is_str;")
        self._emit("    struct _ks_dict_node* next;")
        self._emit("} _ks_dict_node;")
        self._emit("typedef struct { _ks_dict_node* buckets[32]; } _ks_dict;")
        self._emit("static unsigned int _ks_hash(const char* s) {")
        self._emit("    unsigned int h = 5381; int c;")
        self._emit("    while ((c = *s++)) h = ((h << 5) + h) + c;")
        self._emit("    return h % 32;")
        self._emit("}")
        self._emit("static _ks_dict* _ks_dict_new(void) {")
        self._emit("    _ks_dict* d = malloc(sizeof(_ks_dict));")
        self._emit("    memset(d->buckets, 0, sizeof(d->buckets));")
        self._emit("    return d;")
        self._emit("}")
        self._emit(
            "static void _ks_dict_set(_ks_dict* d, const char* key, long long val, int is_str) {"
        )
        self._emit("    unsigned int h = _ks_hash(key);")
        self._emit("    _ks_dict_node* n = d->buckets[h];")
        self._emit(
            "    while (n) { if (strcmp(n->key, key) == 0) { n->i = val; n->is_str = is_str; return; } n = n->next; }"
        )
        self._emit("    n = malloc(sizeof(_ks_dict_node));")
        self._emit("    n->key = strdup(key);")
        self._emit("    n->i = val; n->is_str = is_str;")
        self._emit("    n->next = d->buckets[h];")
        self._emit("    d->buckets[h] = n;")
        self._emit("}")
        self._emit(
            "static long long _ks_dict_get(_ks_dict* d, const char* key, int* found) {"
        )
        self._emit("    unsigned int h = _ks_hash(key);")
        self._emit("    _ks_dict_node* n = d->buckets[h];")
        self._emit(
            "    while (n) { if (strcmp(n->key, key) == 0) { *found = 1; return n->i; } n = n->next; }"
        )
        self._emit("    *found = 0; return 0;")
        self._emit("}")
        self._emit("/* Simple dict get that returns 0 if not found */")
        self._emit(
            "static long long _ks_dict_get_simple(_ks_dict* d, const char* key) {"
        )
        self._emit("    int found;")
        self._emit("    return _ks_dict_get(d, key, &found);")
        self._emit("}")
        self._emit("static int _ks_dict_contains(_ks_dict* d, const char* key) {")
        self._emit("    unsigned int h = _ks_hash(key);")
        self._emit("    _ks_dict_node* n = d->buckets[h];")
        self._emit(
            "    while (n) { if (strcmp(n->key, key) == 0) { return 1; } n = n->next; }"
        )
        self._emit("    return 0;")
        self._emit("}")
        self._emit("/* Dict get that returns string value */")
        self._emit("static char* _ks_dict_get_str(_ks_dict* d, const char* key) {")
        self._emit("    unsigned int h = _ks_hash(key);")
        self._emit("    _ks_dict_node* n = d->buckets[h];")
        self._emit("    while (n) {")
        self._emit("        if (strcmp(n->key, key) == 0) {")
        self._emit("            if (n->is_str) return (char*)n->i;")
        self._emit('            return "";')
        self._emit("        }")
        self._emit("        n = n->next;")
        self._emit("    }")
        self._emit('    return "";')
        self._emit("}")
        self._emit("/* Helper to create and populate dict (1-6 args, handles varargs) */")
        self._emit(
            "static _ks_dict* _ks_dict_create(const char* k1, long long v1, int s1, const char* k2, long long v2, int s2, const char* k3, long long v3, int s3, const char* k4, long long v4, int s4, const char* k5, long long v5, int s5, const char* k6, long long v6, int s6) {"
        )
        self._emit("    _ks_dict* d = _ks_dict_new();")
        self._emit("    if (k1) _ks_dict_set(d, k1, v1, s1);")
        self._emit("    if (k2) _ks_dict_set(d, k2, v2, s2);")
        self._emit("    if (k3) _ks_dict_set(d, k3, v3, s3);")
        self._emit("    if (k4) _ks_dict_set(d, k4, v4, s4);")
        self._emit("    if (k5) _ks_dict_set(d, k5, v5, s5);")
        self._emit("    if (k6) _ks_dict_set(d, k6, v6, s6);")
        self._emit("    return d;")
        self._emit("}")
        self._emit("/* Dict print keys */")
        self._emit("static char* _ks_dict_print_keys(_ks_dict* d) {")
        self._emit("    static char buf[4096]; int pos = 0;")
        self._emit('    pos += snprintf(buf+pos, sizeof(buf)-pos, "[");')
        self._emit("    int first = 1;")
        self._emit(
            "    for (int i = 0; i < (int)(sizeof(d->buckets)/sizeof(d->buckets[0])); i++) {"
        )
        self._emit("        _ks_dict_node* n = d->buckets[i];")
        self._emit(
            '        while (n) { if (!first) pos += snprintf(buf+pos, sizeof(buf)-pos, ", "); pos += snprintf(buf+pos, sizeof(buf)-pos, "\\"%s\\"", n->key); first = 0; n = n->next; }'
        )
        self._emit("    }")
        self._emit('    snprintf(buf+pos, sizeof(buf)-pos, "]");')
        self._emit("    return buf;")
        self._emit("}")
        self._emit("/* Dict print values */")
        self._emit("static char* _ks_dict_print_values(_ks_dict* d) {")
        self._emit("    static char buf[4096]; int pos = 0;")
        self._emit('    pos += snprintf(buf+pos, sizeof(buf)-pos, "[");')
        self._emit("    int first = 1;")
        self._emit(
            "    for (int i = 0; i < (int)(sizeof(d->buckets)/sizeof(d->buckets[0])); i++) {"
        )
        self._emit("        _ks_dict_node* n = d->buckets[i];")
        self._emit(
            '        while (n) { if (!first) pos += snprintf(buf+pos, sizeof(buf)-pos, ", "); if (n->is_str) pos += snprintf(buf+pos, sizeof(buf)-pos, "\\"%s\\"", (char*)n->i); else pos += snprintf(buf+pos, sizeof(buf)-pos, "%lld", n->i); first = 0; n = n->next; }'
        )
        self._emit("    }")
        self._emit('    snprintf(buf+pos, sizeof(buf)-pos, "]");')
        self._emit("    return buf;")
        self._emit("}")
        self._emit("/* [KS-REF-011] Monotonic ms timer */")
        self._emit("static double ks_time_monotonic_ms(void) {")
        self._emit("    struct timespec ts;")
        self._emit("    clock_gettime(CLOCK_MONOTONIC, &ts);")
        self._emit(
            "    return (double)ts.tv_sec*1000.0 + (double)ts.tv_nsec/1000000.0;"
        )
        self._emit("}")
        self._emit("/* time.time() - returns seconds (like Python) */")
        self._emit("static double ks_time_seconds(void) {")
        self._emit("    struct timespec ts;")
        self._emit("    clock_gettime(CLOCK_MONOTONIC, &ts);")
        self._emit("    return (double)ts.tv_sec + (double)ts.tv_nsec/1000000000.0;")
        self._emit("}")
        self._emit(
            "/* [KS-REF-001] i64 array — calloc fallback (no mmap slab in standalone) */"
        )
        self._emit("static long long* ks_alloc_i64(long long n) {")
        self._emit("    return (long long*)calloc((size_t)n, sizeof(long long));")
        self._emit("}")
        self._emit("/* [KS-REF-008] Memory barriers */")
        self._emit("#if defined(__aarch64__) || defined(__arm__)")
        self._emit('#  define KS_BARRIER() __asm__ volatile("dmb ish" ::: "memory")')
        self._emit("#elif defined(__x86_64__) || defined(__i386__)")
        self._emit('#  define KS_BARRIER() __asm__ volatile("mfence" ::: "memory")')
        self._emit("#else")
        self._emit("#  define KS_BARRIER() __sync_synchronize()")
        self._emit("#endif")
        self._emit("#define ks_free free")
        self._emit("/* [KS-REF-001] Memory access builtins */")
        self._emit(
            "static inline void* ks_malloc(size_t size) { return malloc(size); }"
        )
        self._emit("static inline void ks_free_ptr(void* ptr) { free(ptr); }")
        self._emit(
            "static void write_byte(void* ptr, long long offset, long long val) {"
        )
        self._emit("    ((unsigned char*)ptr)[offset] = (unsigned char)val;")
        self._emit("}")
        self._emit("static long long read_byte(void* ptr, long long offset) {")
        self._emit("    return (long long)((unsigned char*)ptr)[offset];")
        self._emit("}")
        self._emit(
            "static void write_word(void* ptr, long long off, long long val, int sz) {"
        )
        self._emit("    if(sz==8) *(uint64_t*)((char*)ptr+off)=(uint64_t)val;")
        self._emit("    else if(sz==4) *(uint32_t*)((char*)ptr+off)=(uint32_t)val;")
        self._emit("    else *(uint16_t*)((char*)ptr+off)=(uint16_t)val;")
        self._emit("}")
        self._emit("static long long read_word(void* ptr, long long off, int sz) {")
        self._emit("    if(sz==8) return (long long)*(uint64_t*)((char*)ptr+off);")
        self._emit("    else if(sz==4) return (long long)*(uint32_t*)((char*)ptr+off);")
        self._emit("    return (long long)*(uint16_t*)((char*)ptr+off);")
        self._emit("}")
        self._emit("/* Hardware access functions */")
        self._emit("#if defined(__x86_64__) || defined(__i386__)")
        self._emit("static inline uint8_t _ks_io_read(uint16_t port) {")
        self._emit("    uint8_t val;")
        self._emit('    __asm__ volatile("inb %1, %0" : "=a"(val) : "Nd"(port));')
        self._emit("    return val;")
        self._emit("}")
        self._emit("static inline void _ks_io_write(uint16_t port, uint8_t val) {")
        self._emit('    __asm__ volatile("outb %0, %1" :: "a"(val), "Nd"(port));')
        self._emit("}")
        self._emit("static inline uint64_t _ks_msr_read(uint32_t msr) {")
        self._emit("    uint32_t lo, hi;")
        self._emit('    __asm__ volatile("rdmsr" : "=a"(lo), "=d"(hi) : "c"(msr));')
        self._emit("    return ((uint64_t)hi << 32) | lo;")
        self._emit("}")
        self._emit("static inline void _ks_msr_write(uint32_t msr, uint64_t val) {")
        self._emit("    uint32_t lo = val & 0xFFFFFFFF;")
        self._emit("    uint32_t hi = val >> 32;")
        self._emit('    __asm__ volatile("wrmsr" :: "a"(lo), "d"(hi), "c"(msr));')
        self._emit("}")
        self._emit("#elif defined(__aarch64__) || defined(__arm__)")
        self._emit("static inline uint32_t _ks_io_read(uint64_t addr) {")
        self._emit("    return *(volatile uint32_t*)addr;")
        self._emit("}")
        self._emit("static inline void _ks_io_write(uint64_t addr, uint32_t val) {")
        self._emit("    *(volatile uint32_t*)addr = val;")
        self._emit("}")
        self._emit("static inline uint64_t _ks_msr_read(uint32_t reg) {")
        self._emit("    uint64_t val;")
        self._emit('    __asm__ volatile("mrs %0, s3_0_c0_c0_0" : "=r"(val));')
        self._emit("    return val;")
        self._emit("}")
        self._emit("static inline void _ks_msr_write(uint32_t reg, uint64_t val) {")
        self._emit('    __asm__ volatile("msr s3_0_c0_c0_0, %0" :: "r"(val));')
        self._emit("}")
        self._emit("#else")
        self._emit("static inline uint32_t _ks_io_read(uint64_t addr) { return 0; }")
        self._emit("static inline void _ks_io_write(uint64_t addr, uint32_t val) {}")
        self._emit("static inline uint64_t _ks_msr_read(uint32_t reg) { return 0; }")
        self._emit("static inline void _ks_msr_write(uint32_t reg, uint64_t val) {}")
        self._emit("#endif")

        # Add comprehensive lowlevel runtime functions
        self._emit("/* Low-level runtime functions */")
        self._emit("static inline uint64_t ks_ptr_read(void* addr, int size) {")
        self._emit("    switch(size) {")
        self._emit("        case 1: return *(uint8_t*)addr;")
        self._emit("        case 2: return *(uint16_t*)addr;")
        self._emit("        case 4: return *(uint32_t*)addr;")
        self._emit("        case 8: return *(uint64_t*)addr;")
        self._emit("        default: return *(uint64_t*)addr;")
        self._emit("    }")
        self._emit("}")
        self._emit(
            "static inline void ks_ptr_write(void* addr, uint64_t value, int size) {"
        )
        self._emit("    switch(size) {")
        self._emit("        case 1: *(uint8_t*)addr = (uint8_t)value; break;")
        self._emit("        case 2: *(uint16_t*)addr = (uint16_t)value; break;")
        self._emit("        case 4: *(uint32_t*)addr = (uint32_t)value; break;")
        self._emit("        case 8: *(uint64_t*)addr = value; break;")
        self._emit("    }")
        self._emit("}")
        self._emit("static inline void* ks_ptr_cast(void* ptr) { return ptr; }")
        self._emit(
            "static inline uint64_t ks_ptr_deref(void* ptr) { return *(uint64_t*)ptr; }"
        )
        self._emit(
            "static inline long ks_system_syscall(long n, long a1, long a2, long a3, long a4, long a5, long a6) {"
        )
        self._emit("    return syscall(n, a1, a2, a3, a4, a5, a6);")
        self._emit("}")
        self._emit("static inline uint64_t ks_atomic_load(void* addr, int size) {")
        self._emit("    return __atomic_load_n((uint64_t*)addr, __ATOMIC_SEQ_CST);")
        self._emit("}")
        self._emit(
            "static inline void ks_atomic_store(void* addr, uint64_t value, int size) {"
        )
        self._emit("    __atomic_store_n((uint64_t*)addr, value, __ATOMIC_SEQ_CST);")
        self._emit("}")
        self._emit(
            "static inline uint64_t ks_atomic_add(void* addr, uint64_t value, int size) {"
        )
        self._emit(
            "    return __atomic_add_fetch((uint64_t*)addr, value, __ATOMIC_SEQ_CST);"
        )
        self._emit("}")
        self._emit(
            "static inline uint64_t ks_atomic_cas(void* addr, uint64_t expected, uint64_t desired, int size) {"
        )
        self._emit(
            "    __atomic_compare_exchange_n((uint64_t*)addr, &expected, desired, 0, __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST);"
        )
        self._emit("    return expected;")
        self._emit("}")
        self._emit(
            "static inline uint64_t ks_volatile_read(volatile void* addr, int size) {"
        )
        self._emit("    return *(volatile uint64_t*)addr;")
        self._emit("}")
        self._emit(
            "static inline void ks_volatile_write(volatile void* addr, uint64_t value, int size) {"
        )
        self._emit("    *(volatile uint64_t*)addr = value;")
        self._emit("}")
        self._emit("static inline void ks_memory_barrier() { __sync_synchronize(); }")
        self._emit(
            'static inline void ks_compiler_barrier() { __asm__ __volatile__("" ::: "memory"); }'
        )
        self._emit("/* ks_cache_flush provided by ks_runtime.h */")
        self._emit("#if 0  /* disabled - use ks_runtime.h version */")
        self._emit("static inline void ks_cache_flush(void* addr, size_t size) {")
        self._emit("    __builtin___clear_cache((char*)addr, (char*)addr + size);")
        self._emit("}")
        self._emit("#endif")
        self._emit("static inline void ks_cache_invalidate(void* addr, size_t size) {")
        self._emit("    __builtin___clear_cache((char*)addr, (char*)addr + size);")
        self._emit("}")
        self._emit("static inline uint64_t ks_mmio_read(void* addr, int size) {")
        self._emit("    return ks_volatile_read(addr, size);")
        self._emit("}")
        self._emit(
            "static inline void ks_mmio_write(void* addr, uint64_t value, int size) {"
        )
        self._emit("    ks_volatile_write(addr, value, size);")
        self._emit("}")
        self._emit("#if defined(__x86_64__) || defined(__i386__)")
        self._emit("static inline uint8_t ks_read_port(uint16_t port) {")
        self._emit("    uint8_t value;")
        self._emit('    __asm__ volatile("inb %1, %0" : "=a"(value) : "Nd"(port));')
        self._emit("    return value;")
        self._emit("}")
        self._emit("static inline void ks_write_port(uint16_t port, uint8_t value) {")
        self._emit('    __asm__ volatile("outb %0, %1" : : "a"(value), "Nd"(port));')
        self._emit("}")
        self._emit("static inline uint64_t ks_rdtsc() {")
        self._emit("    uint32_t lo, hi;")
        self._emit('    __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));')
        self._emit("    return ((uint64_t)hi << 32) | lo;")
        self._emit("}")
        self._emit(
            "static inline void ks_cpuid(uint32_t leaf, uint32_t* eax, uint32_t* ebx, uint32_t* ecx, uint32_t* edx) {"
        )
        self._emit(
            '    __asm__ volatile("cpuid" : "=a"(*eax), "=b"(*ebx), "=c"(*ecx), "=d"(*edx) : "a"(leaf));'
        )
        self._emit("}")
        self._emit("#else")
        self._emit("static inline uint8_t ks_read_port(uint16_t port) { return 0; }")
        self._emit("static inline void ks_write_port(uint16_t port, uint8_t value) {}")
        self._emit("static inline uint64_t ks_rdtsc() { return 0; }")
        self._emit(
            "static inline void ks_cpuid(uint32_t leaf, uint32_t* eax, uint32_t* ebx, uint32_t* ecx, uint32_t* edx) {}"
        )
        self._emit("#endif")

        # Add array return type support
        self._emit("/* Array return type wrapper */")
        self._emit(
            "static inline ks_array ks_make_array(long long* data, long long len) {"
        )
        self._emit("    ks_array arr = {data, len};")
        self._emit("    return arr;")
        self._emit("}")
        self._emit(
            "static inline long long ks_array_get(ks_array arr, long long idx) {"
        )
        self._emit("    return arr.data[idx];")
        self._emit("}")
        self._emit("static inline long long ks_array_len(ks_array arr) {")
        self._emit("    return arr.length;")
        self._emit("}")

        self._emit("#endif /* KS_RUNTIME_HAVE_ALL_FUNCS */")

        # Emit stub implementations for http, json, and system_socket functions
        self._emit("/* ===== HTTP/JSON/Socket stub implementations ===== */")
        self._emit("#include <sys/socket.h>")
        self._emit("#include <netinet/in.h>")
        self._emit("#include <arpa/inet.h>")
        self._emit("#include <netdb.h>")
        self._emit("#include <errno.h>")
        self._emit("#include <fcntl.h>")
        self._emit("#include <unistd.h>")
        self._emit(
            "typedef struct { long long status; char* text; } _ks_http_response_t;"
        )
        self._emit(
            "static _ks_http_response_t _ks_http_get(const char* url) { "
            '_ks_http_response_t r = {0, ""}; return r; }'
        )
        self._emit(
            "static _ks_http_response_t _ks_http_post(const char* url, const char* data) { "
            '_ks_http_response_t r = {0, ""}; return r; }'
        )
        self._emit(
            "static long long _ks_json_loads(const char* json_str) { return 0; }"
        )
        self._emit(
            "static long long ks_system_socket_create(int domain, int type, int protocol) {"
        )
        self._emit("    int sock = socket(domain, type, protocol);")
        self._emit("    return sock >= 0 ? (long long)sock : -1;")
        self._emit("}")
        self._emit(
            "static long long ks_system_socket_settimeout(long long sock, double timeout) {"
        )
        self._emit("    struct timeval tv;")
        self._emit("    tv.tv_sec = (int)timeout;")
        self._emit("    tv.tv_usec = (int)((timeout - tv.tv_sec) * 1000000);")
        self._emit(
            "    setsockopt((int)sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));"
        )
        self._emit(
            "    setsockopt((int)sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));"
        )
        self._emit("    return 0;")
        self._emit("}")
        self._emit(
            "static long long ks_system_socket_connect(long long sock, const char* host, int port) {"
        )
        self._emit("    struct sockaddr_in addr;")
        self._emit("    memset(&addr, 0, sizeof(addr));")
        self._emit("    addr.sin_family = AF_INET;")
        self._emit("    addr.sin_port = htons(port);")
        self._emit("    if (inet_pton(AF_INET, host, &addr.sin_addr) <= 0) {")
        self._emit("        struct hostent* he = gethostbyname(host);")
        self._emit("        if (!he) return -1;")
        self._emit("        memcpy(&addr.sin_addr, he->h_addr_list[0], he->h_length);")
        self._emit("    }")
        self._emit(
            "    return connect((int)sock, (struct sockaddr*)&addr, sizeof(addr)) == 0 ? 0 : -1;"
        )
        self._emit("}")
        self._emit(
            "static long long ks_system_socket_send(long long sock, const char* data) {"
        )
        self._emit("    int result = send((int)sock, data, strlen(data), 0);")
        self._emit("    return result >= 0 ? result : -1;")
        self._emit("}")
        self._emit("static char* ks_system_socket_recv(long long sock, int size) {")
        self._emit("    char* buffer = (char*)malloc(size + 1);")
        self._emit("    if (!buffer) return NULL;")
        self._emit("    int n = recv((int)sock, buffer, size, 0);")
        self._emit("    if (n > 0) buffer[n] = 0;")
        self._emit("    else buffer[0] = 0;")
        self._emit("    return buffer;")
        self._emit("}")
        self._emit("static long long ks_system_socket_close(long long sock) {")
        self._emit("    return close((int)sock) == 0 ? 0 : -1;")
        self._emit("}")

        # ---- Async/await coroutine runtime (ucontext-based) ----
        self._emit("")
        self._emit("/* ===== KentScript async/await runtime (ucontext) ===== */")
        self._emit("#include <ucontext.h>")
        self._emit("#define KS_CORO_STACK 65536")
        self._emit("typedef struct {")
        self._emit("    ucontext_t ctx;")
        self._emit("    ucontext_t caller;")
        self._emit("    char stack[KS_CORO_STACK];")
        self._emit("    void (*fn)(void*);")
        self._emit("    void* arg;")
        self._emit("    void* result;   /* wide enough for any pointer or integer */")
        self._emit("    int done;")
        self._emit("} _ks_coro_t;")
        self._emit("static _ks_coro_t* _ks_coro_current = NULL;")
        self._emit("static void _ks_coro_entry(_ks_coro_t* c) {")
        self._emit("    c->fn(c->arg);")
        self._emit("    c->done = 1;")
        self._emit("    swapcontext(&c->ctx, &c->caller);")
        self._emit("}")
        self._emit("static _ks_coro_t* _ks_coro_new(void (*fn)(void*), void* arg) {")
        self._emit("    _ks_coro_t* c = (_ks_coro_t*)calloc(1, sizeof(_ks_coro_t));")
        self._emit("    c->fn = fn; c->arg = arg;")
        self._emit("    getcontext(&c->ctx);")
        self._emit("    c->ctx.uc_stack.ss_sp = c->stack;")
        self._emit("    c->ctx.uc_stack.ss_size = KS_CORO_STACK;")
        self._emit("    c->ctx.uc_link = NULL;")
        self._emit("    makecontext(&c->ctx, (void(*)())_ks_coro_entry, 1, c);")
        self._emit("    return c;")
        self._emit("}")
        self._emit("static void* _ks_coro_run(_ks_coro_t* c) {")
        self._emit("    _ks_coro_t* prev = _ks_coro_current;")
        self._emit("    _ks_coro_current = c;")
        self._emit("    swapcontext(&c->caller, &c->ctx);")
        self._emit("    _ks_coro_current = prev;")
        self._emit("    return c->result;")
        self._emit("}")
        # _KS_AWAIT: two variants — void (for void-returning calls) and value.
        self._emit("/* await void: suspend coroutine after calling void expression */")
        self._emit("#define _KS_AWAIT_VOID(expr) do {                              \\")
        self._emit("    (expr);                                                     \\")
        self._emit("    if (_ks_coro_current)                                       \\")
        self._emit("        swapcontext(&_ks_coro_current->ctx,                     \\")
        self._emit("                    &_ks_coro_current->caller);                 \\")
        self._emit("} while(0)")
        self._emit("/* await value: suspend coroutine and return value */")
        self._emit("#define _KS_AWAIT(expr) (__extension__({                        \\")
        self._emit("    __typeof__(expr) _ks_r = (expr);                            \\")
        self._emit("    if (_ks_coro_current) {                                     \\")
        self._emit(
            "        _ks_coro_current->result = (void*)(uintptr_t)(long long)_ks_r; \\"
        )
        self._emit("        swapcontext(&_ks_coro_current->ctx,                     \\")
        self._emit("                    &_ks_coro_current->caller);                 \\")
        self._emit(
            "    }                                                            \\"
        )
        self._emit("    _ks_r;                                                      \\")
        self._emit("}))")
        self._emit("/* async.run(fn) — create coroutine and drive to completion */")
        self._emit("static void* _ks_async_run_fn(void (*fn)(void*)) {")
        self._emit("    _ks_coro_t* c = _ks_coro_new(fn, NULL);")
        self._emit("    while (!c->done) _ks_coro_run(c);")
        self._emit("    void* r = c->result; free(c); return r;")
        self._emit("}")
        self._emit("/* ===== end async runtime ===== */")
        self._emit("")

        self._emit()

        # Pre-populate return types for built-in functions
        self.func_return_types.update(
            {
                "read_byte": "long long",
                "read_word": "long long",
                "write_byte": "void",
                "write_word": "void",
                "malloc": "void*",
                "alloc": "void*",
                "calloc": "void*",
                "free": "void",
                "strlen": "long long",
                "_ks_http_get": "_ks_http_response_t",
                "_ks_http_post": "_ks_http_response_t",
                "_ks_json_loads": "long long",
            }
        )
        # --- Collect & emit forward declarations for user functions ---
        _c_type_map_fwd = {
            "int": "long long",
            "i64": "long long",
            "i32": "long long",
            "float": "double",
            "f64": "double",
            "f32": "double",
            "double": "double",
            "string": "char*",
            "str": "char*",
            "bool": "long long",
            "void": "void",
        }

        # --- Emit struct definitions (before enums and functions) ---
        struct_nodes = [n for n in ast_nodes if n.__class__.__name__ == "StructDef"]
        for struct_node in struct_nodes:
            self._emit(f"typedef struct {{")
            self.indent_level += 1
            for field in struct_node.fields:
                field_name = field.name if hasattr(field, "name") else field[0]
                field_type = (
                    field.field_type
                    if hasattr(field, "field_type")
                    else (field[1] if len(field) > 1 else "int")
                )
                c_type = _c_type_map_fwd.get(field_type, "long long")
                self._emit(f"{c_type} {field_name};")
            self.indent_level -= 1
            self._emit(f"}} {struct_node.name};")
            self._emit()

        # --- Emit enum definitions (before functions) ---
        self._enum_names = set()
        self._enum_members = set()
        enum_nodes = [n for n in ast_nodes if n.__class__.__name__ == "EnumDef"]
        for enum_node in enum_nodes:
            self._enum_names.add(enum_node.name)
            self._emit(f"typedef enum {{")
            self.indent_level += 1
            has_values = any(
                isinstance(v, tuple) and v[1] is not None for v in enum_node.variants
            )
            for i, variant in enumerate(enum_node.variants):
                comma = "," if i < len(enum_node.variants) - 1 else ""
                if isinstance(variant, tuple):
                    name, value, data = (
                        variant[0],
                        variant[1],
                        variant[2] if len(variant) > 2 else None,
                    )
                    if value is not None:
                        self._emit(f"{enum_node.name}_{name} = {value}{comma}")
                    else:
                        self._emit(f"{enum_node.name}_{name}{comma}")
                    self._enum_members.add(f"{enum_node.name}_{name}")
                    self.numeric_vars.add(f"{enum_node.name}_{name}")
                else:
                    self._emit(f"{enum_node.name}_{variant}{comma}")
                    self._enum_members.add(f"{enum_node.name}_{variant}")
                    self.numeric_vars.add(f"{enum_node.name}_{variant}")
            self.indent_level -= 1
            self._emit(f"}} {enum_node.name};")
            self._emit()

        # --- Pre-populate class names before forward declarations ---
        # This ensures functions can reference class types before class definitions are emitted
        class_nodes = [n for n in ast_nodes if n.__class__.__name__ == "ClassDef"]
        for node in class_nodes:
            if not hasattr(self, 'class_names'):
                self.class_names = set()
            if not hasattr(self, 'class_instance_types'):
                self.class_instance_types = {}
            self.class_names.add(node.name)
            self.class_instance_types[node.name] = f"{node.name}_t*"

        func_nodes = [n for n in ast_nodes if n.__class__.__name__ == "FunctionDef"]
        for fn in func_nodes:
            # Generator functions always return ks_array
            if getattr(fn, "is_generator", False):
                ret = "ks_array"
            else:
                ret = self._infer_func_return_type(fn) or "void"
            if ret == "func_ptr":
                ret = "void*"
            self.func_return_types[fn.name] = ret
            pm = getattr(fn, "param_types", {}) or {}

            # Use the same type inference logic as in _transpile_function
            def _param_c_type_fwd(p):
                kt = pm.get(p, None)
                if kt is not None:
                    return _c_type_map_fwd.get(kt, "char*")

                # Analyze parameter usage in function body to infer type
                body = getattr(fn, "body", []) or []
                body_str = "\n".join(str(stmt) for stmt in body)
                
                import re
                
                # Check for numeric match cases FIRST - this is a strong indicator of numeric param
                if re.search(r"Literal\(value=[0-9]+\)", body_str):
                    return "long long"
                
                # Check if param is converted to string via str(param) - this indicates NUMERIC
                # Use regex to match name='str' followed by args containing name='p'
                if re.search(rf"name='str'.*name='{p}'", body_str, re.DOTALL):
                    # Check if there's also string concat with literals (f-string)
                    has_string_concat = (
                        "BinaryOp" in body_str 
                        and "op='+'" in body_str
                        and (
                            "Literal(value='" in body_str
                            or 'Literal(value="' in body_str
                        )
                    )
                    if has_string_concat:
                        return "char*"
                    return "long long"
                
                # Check for string operations - parameter is used as string
                has_string_op = (
                    "split" in body_str 
                    or "to_lower" in body_str
                    or "to_upper" in body_str
                    or "_ks_concat" in body_str 
                    or "FStringLiteral" in body_str
                )
                
                # If string operations, use char*
                if has_string_op:
                    return "char*"
                
                # Default to long long
                return "long long"
                
                # Check for string operations - parameter is used as string
                has_string_op = (
                    "split" in body_str 
                    or "to_lower" in body_str
                    or "to_upper" in body_str
                    or "_ks_concat" in body_str 
                    or "FStringLiteral" in body_str
                )
                
                # Check for numeric match cases - parameter is numeric
                if re.search(r"Literal\(value=[0-9]+\)", body_str):
                    return "long long"
                
                # If string operations, use char*
                if has_string_op:
                    return "char*"
                
                # Default to long long
                return "long long"
                
                # Check for numeric match cases - parameter is numeric
                import re
                if re.search(rf"Literal\(value=[0-9]+\)", body_str):
                    return "long long"
                
                # If string operations, use char*
                if has_string_op:
                    return "char*"
                
                # Default to long long
                return "long long"

            if fn.params:
                params_c = ", ".join(f"{_param_c_type_fwd(p)} {p}" for p in fn.params)
            else:
                params_c = "void"
            # Skip forward-declaring 'main' — it conflicts with our int main(void) entry point
            if fn.name == "main":
                continue
            self._emit(f"{ret} {fn.name}({params_c});")
        if func_nodes:
            self._emit()

        # --- Emit class definitions (before main, before functions) ---
        class_nodes = [n for n in ast_nodes if n.__class__.__name__ == "ClassDef"]
        for node in class_nodes:
            self._transpile_class(node)
            self._emit()

        # --- Pre-populate _global_types (for closure capture detection only, NOT declared_vars) ---
        _g_type_map = {
            "int": "long long",
            "i64": "long long",
            "i32": "long long",
            "float": "double",
            "f64": "double",
            "double": "double",
            "string": "char*",
            "str": "char*",
            "bool": "long long",
        }
        self._global_types = {}
        for _gn in ast_nodes:
            if _gn.__class__.__name__ == "LetDecl":
                _hint = getattr(_gn, "type_hint", None)
                if _hint:
                    self._global_types[_gn.name] = _g_type_map.get(_hint, "long long")
                elif _gn.value and _gn.value.__class__.__name__ == "Literal":
                    v = _gn.value.value
                    if isinstance(v, str):
                        self._global_types[_gn.name] = "char*"
                    elif isinstance(v, float):
                        self._global_types[_gn.name] = "double"
                    else:
                        self._global_types[_gn.name] = "long long"
                else:
                    self._global_types[_gn.name] = "long long"

        # --- Emit lambda functions (before globals) ---
        if hasattr(self, "_lambda_funcs") and self._lambda_funcs:
            # NOTE: No forward declarations for lambdas — closure structs may change the signature
            # and lambdas are always defined before they're called (same translation unit).

            for func_name, params_str, body_node, param_count in self._lambda_funcs:
                # Save declared_vars so lambda emission doesn't pollute parent scope
                saved_declared = dict(self.declared_vars)
                saved_string_vars = set(self.string_vars)
                saved_numeric_vars = set(self.numeric_vars)
                # Handle FunctionDef nodes (anonymous functions returned as values)
                if body_node.__class__.__name__ == "FunctionDef":
                    fn = body_node
                    fn_params = [p for p in (fn.params or []) if p != "self"]
                    free_vars = self._collect_free_vars(fn.body or [], fn_params)
                    if free_vars:

                        def _body():
                            self.declared_vars = {p: "long long" for p in fn_params}
                            for vn, vt in free_vars:
                                self.declared_vars[vn] = vt
                            for stmt in fn.body or []:
                                self._transpile_stmt(stmt)

                        self._emit_closure(func_name, fn_params, free_vars, _body)
                    else:
                        fn_params_str = ", ".join(f"long long {p}" for p in fn_params)
                        self._emit(
                            f"static long long {func_name}({fn_params_str or 'void'}) {{"
                        )
                        self.indent_level += 1
                        self.declared_vars = {p: "long long" for p in fn_params}
                        for stmt in fn.body or []:
                            self._transpile_stmt(stmt)
                        self._emit("return 0LL;")
                        self.indent_level -= 1
                        self._emit("}")
                        self._emit()
                else:
                    # LambdaExpr body
                    lam_params = params_str.split(", ") if params_str else []
                    lam_param_names = [p.split()[-1] for p in lam_params if p]
                    free_vars = self._collect_free_vars(body_node, lam_param_names)
                    # Infer return type from body expression
                    ret_type = "char*" if self._is_string_node(body_node) else "long long"
                    if free_vars:

                        def _lam_body():
                            body_expr = self._transpile_expr(body_node)
                            self._emit(f"return {body_expr};")

                        self._emit_closure(
                            func_name, lam_param_names, free_vars, _lam_body, ret_type
                        )
                    else:
                        self._emit(
                            f"static long long {func_name}({params_str or 'void'}) {{"
                        )
                        self.indent_level += 1
                        body_expr = self._transpile_expr(body_node)
                        self._emit(f"return {body_expr};")
                        self.indent_level -= 1
                        self._emit("}")
                        self._emit()
                # Restore scope
                self.declared_vars = saved_declared
                self.string_vars = saved_string_vars
                self.numeric_vars = saved_numeric_vars

        # --- Emit global variables (before main, before functions) ---
        # Only treat LetDecl as global if it appears before any executable statements
        global_let_nodes = []
        other_nodes = []
        seen_executable = False

        for node in ast_nodes:
            node_type = node.__class__.__name__
            if node_type in ("FunctionDef", "ClassDef"):
                # Functions and classes don't count as executable statements
                continue
            elif node_type == "LetDecl":
                if not seen_executable:
                    global_let_nodes.append(node)
                else:
                    other_nodes.append(node)
            elif node_type in (
                "ForStmt",
                "WhileStmt",
                "IfStmt",
                "Print",
                "ExprStmt",
                "Assignment",
                "FunctionCall",
            ):
                seen_executable = True
                other_nodes.append(node)
            else:
                other_nodes.append(node)

        for node in global_let_nodes:
            self._transpile_global_decl(node)
        if global_let_nodes:
            self._emit()

        # --- Emit function definitions (before main) ---
        has_user_main = any(
            n.__class__.__name__ == "FunctionDef" and n.name == "main"
            for n in ast_nodes
        )
        for node in ast_nodes:
            if node.__class__.__name__ == "FunctionDef":
                ks_line = getattr(node, "line", None) or getattr(node, "lineno", None)
                if ks_line:
                    self._emit_line_directive(ks_line)
                self._transpile_function(node)
                self._emit()
            # other_nodes already collected above

        # --- Emit deferred global initializations ---
        has_lc = (
            hasattr(self, "_deferred_global_lc_inits")
            and self._deferred_global_lc_inits
        )
        if (
            hasattr(self, "_deferred_global_inits") and self._deferred_global_inits
        ) or has_lc:
            self._emit("void _ks_init_globals(void) {")
            self.indent_level += 1
            if hasattr(self, "_deferred_global_inits") and self._deferred_global_inits:
                for var_name, init_val in self._deferred_global_inits:
                    self._emit(f"{var_name} = {init_val};")
            if has_lc:
                for var_name, lc_node in self._deferred_global_lc_inits:
                    tmp = self._transpile_expr(lc_node)
                    self._emit(f"{var_name} = {tmp};")
            self.indent_level -= 1
            self._emit("}")
            self._emit()

        # --- int main(void) entry point ---
        self._emit("int main(void) {")
        self.indent_level += 1
        # Call deferred global initializations first
        if (
            hasattr(self, "_deferred_global_inits") and self._deferred_global_inits
        ) or (
            hasattr(self, "_deferred_global_lc_inits")
            and self._deferred_global_lc_inits
        ):
            self._emit("_ks_init_globals();")
        if has_user_main:
            # User defined their own main() — renamed to ks_user_main to avoid C conflict
            self._emit("ks_user_main();")
            self._emit("return 0;")
        else:
            for node in other_nodes:
                ks_line = getattr(node, "line", None) or getattr(node, "lineno", None)
                # For FunctionCall, the line is often on the func Identifier
                if not ks_line:
                    func_attr = getattr(node, "func", None)
                    if func_attr:
                        ks_line = getattr(func_attr, "line", None) or getattr(func_attr, "lineno", None)
                if ks_line:
                    self._emit_line_directive(ks_line)
                self._transpile_stmt(node)
            self._emit("return 0;")
        self.indent_level -= 1
        self._emit("}")

        return "\n".join(self.code_lines)

    # ------------------------------------------------------------------ functions

    def _transpile_global_decl(self, node):
        """Handle global let declarations - emit as C global variables."""
        name = self._safe_c_name(node.name)  # Convert to safe C name
        name_orig = node.name
        val_node = node.value
        explicit_type = getattr(node, "type_hint", None)

        # Special case: FunctionDef with _resolved_anon_name → global function pointer
        if val_node and val_node.__class__.__name__ == "FunctionDef":
            resolved = getattr(val_node, "_resolved_anon_name", None)
            if resolved:
                param_count = len(val_node.params or [])
                params_sig = ", ".join(["long long"] * param_count)
                self._emit(f"long long (*{name})({params_sig});")
                self.declared_vars[name] = f"long long (*)({params_sig})"
                fn_params = [p for p in (val_node.params or []) if p != "self"]
                free_vars = self._collect_free_vars(val_node.body or [], fn_params)
                if not hasattr(self, "_deferred_global_inits"):
                    self._deferred_global_inits = []
                self._deferred_global_inits.append(
                    (name, f"(long long(*)({params_sig})){resolved}")
                )
                if free_vars:
                    for vn, vt in free_vars:
                        self._deferred_global_inits.append(
                            (f"{resolved}_env.{vn}", f"&{vn}")
                        )
                return
        if explicit_type in ("bool", "BOOL"):
            self.bool_vars.add(name)
            self.numeric_vars.add(name)
            self.declared_vars[name] = "long long"
            raw = self._transpile_expr(val_node) if val_node else "0"
            self._emit(f"long long {name} = {raw};")
            return
        elif explicit_type in ("str", "string"):
            self.string_vars.add(name)
            self.declared_vars[name] = "char*"
            raw = self._transpile_expr(val_node) if val_node else "NULL"
            self._emit(f"char* {name} = {raw};")
            return

        # If already declared, re-declare as a local shadow if inside a block, else assign
        if name in self.declared_vars:
            if val_node:
                raw = self._transpile_expr(val_node)
                if self.indent_level > 0:
                    # Inside a function/block: emit a new local declaration (C allows shadowing)
                    existing_type = self.declared_vars[name]
                    self._emit(f"{existing_type} {name} = {raw};")
                else:
                    if not hasattr(self, "_deferred_global_inits"):
                        self._deferred_global_inits = []
                    self._deferred_global_inits.append((name, raw))
            return

        # Special case: ListComprehension — emit as ks_array built by a loop
        if val_node and val_node.__class__.__name__ == "ListComprehension":
            lc = val_node
            tmp = f"_lc_{name}_{self._label_count}"
            self._label_count += 1
            iter_expr = self._transpile_expr(lc.iterable)
            loop_var = lc.var
            # Declare result array
            self._emit(f"ks_array {name} = {{NULL, 0}};")
            self.declared_vars[name] = "ks_array"
            # Determine iteration: ks_array or range
            iter_node = lc.iterable
            iter_cls = iter_node.__class__.__name__
            if (
                iter_cls == "FunctionCall"
                and getattr(iter_node, "func", None)
                and getattr(iter_node.func, "name", "") == "range"
            ):
                rargs = iter_node.args
                if len(rargs) == 1:
                    start_c, stop_c = "0", self._transpile_expr(rargs[0])
                else:
                    start_c, stop_c = (
                        self._transpile_expr(rargs[0]),
                        self._transpile_expr(rargs[1]),
                    )
                self._emit(
                    f"for (long long {loop_var} = {start_c}; {loop_var} < {stop_c}; {loop_var}++) {{"
                )
            else:
                self._emit(
                    f"for (long long _i_{tmp} = 0; _i_{tmp} < {iter_expr}.length; _i_{tmp}++) {{"
                )
                self._emit(f"    long long {loop_var} = {iter_expr}.data[_i_{tmp}];")
            # Condition filter
            if lc.condition:
                cond_c = self._transpile_expr(lc.condition)
                self._emit(f"    if ({cond_c}) {{")
            elem_c = self._transpile_expr(lc.expr)
            # Handle string elements properly - cast to void* instead of long long
            if self._is_string_node(lc.expr):
                self._emit(f"    _ks_array_append(&{name}, (void*)(char*){elem_c});")
            else:
                self._emit(f"    _ks_array_append(&{name}, (long long)({elem_c}));")
            if lc.condition:
                self._emit("    }")
            self._emit("}")
            return

        # Special case: Check if value is a class constructor call (ClassName(...) or ClassName.new(...))
        if val_node and val_node.__class__.__name__ == "FunctionCall":
            fn = val_node.func
            class_name = None
            if fn.__class__.__name__ == "Identifier" and fn.name in self.class_names:
                class_name = fn.name
            elif (
                fn.__class__.__name__ == "MemberAccess"
                and hasattr(fn, "obj")
                and hasattr(fn.obj, "name")
                and fn.obj.name in self.class_names
                and getattr(fn, "member", None) == "new"
            ):
                class_name = fn.obj.name
            if class_name:
                ctype = self.class_instance_types.get(class_name, f"{class_name}_t*")
                raw = self._transpile_expr(val_node)
                self._emit(f"{ctype} {name};")
                self.declared_vars[name] = ctype
                if not hasattr(self, "_deferred_global_inits"):
                    self._deferred_global_inits = []
                self._deferred_global_inits.append((name, raw))
                return

        # Special case: ListLiteral — emit as ks_array struct
        if val_node and val_node.__class__.__name__ == "ListLiteral":
            elems = val_node.elements if hasattr(val_node, "elements") else []
            # Check if all elements are literals with a value (numeric or hex string)
            all_have_value = all(hasattr(e, "value") for e in elems)
            if elems and all_have_value:
                # Check if elements are strings
                all_strings = all(
                    isinstance(getattr(e, "value", None), str) for e in elems
                )
                if all_strings:
                    vals = ", ".join(f'(long long)"{e.value}"' for e in elems)
                else:
                    vals = ", ".join(str(e.value) for e in elems)
                # Create a static array to hold the data
                arr_name = f"_arr_{name}"
                self._emit(f"static long long {arr_name}[] = {{{vals}}};")
                # Create ks_array struct
                self._emit(
                    f"ks_array {name} = {{ .data = {arr_name}, .length = {len(elems)} }};"
                )
                self.declared_vars[name] = "ks_array"
            else:
                # Mixed/complex list — fallback to NULL pointer
                self._emit(f"long long* {name} = NULL; /* list not fully supported */")
                self.declared_vars[name] = "long long*"
                self.numeric_vars.add(name)
            return

        # For other global variables, check if initialization is constant
        if val_node:
            # Check for lambda expression first
            if val_node.__class__.__name__ == "LambdaExpr":
                param_count = len(val_node.params)
                params_sig = ", ".join(["long long"] * param_count)
                raw = self._transpile_expr(val_node)
                self._emit(f"long long (*{name})({params_sig});")
                self.declared_vars[name] = f"long long (*)({params_sig})"
                # Defer initialization
                if not hasattr(self, "_deferred_global_inits"):
                    self._deferred_global_inits = []
                self._deferred_global_inits.append((name, raw))
                return

            # Special case: ListComprehension — must be initialized inside a function
            if val_node.__class__.__name__ == "ListComprehension":
                self._emit(f"ks_array {name} = {{NULL, 0}};")
                self.declared_vars[name] = "ks_array"
                if not hasattr(self, "_deferred_global_lc_inits"):
                    self._deferred_global_lc_inits = []
                self._deferred_global_lc_inits.append((name, val_node))
                return

            raw = self._transpile_expr(val_node)

            # Check if this is a borrow expression - needs pointer type
            is_borrow = (
                val_node.__class__.__name__ == "UnaryOp"
                and getattr(val_node, "op", None) == "borrow"
            )

            # Check if initializer is non-constant (references other variables)
            is_non_constant = self._is_non_constant_global_init(val_node)

            # Check for struct literal
            if val_node.__class__.__name__ == "StructLiteral":
                struct_type = val_node.name
                if is_non_constant:
                    self._emit(f"{struct_type} {name};")
                    self.declared_vars[name] = struct_type
                    if not hasattr(self, "_deferred_global_inits"):
                        self._deferred_global_inits = []
                    self._deferred_global_inits.append((name, raw))
                else:
                    self._emit(f"{struct_type} {name} = {raw};")
                    self.declared_vars[name] = struct_type
                return

            # Infer type from value
            if val_node.__class__.__name__ == "Literal":
                lit_val = getattr(val_node, "value", None)
                if isinstance(lit_val, float):
                    self._emit(f"double {name} = {raw};")
                    self.declared_vars[name] = "double"
                elif isinstance(lit_val, str):
                    # Check for hex/bin/oct literals - treat as integers
                    if lit_val.startswith(("0x", "0X", "0b", "0B", "0o", "0O")):
                        self._emit(f"long long {name} = {raw};")
                        self.declared_vars[name] = "long long"
                        self.numeric_vars.add(name)
                    else:
                        self._emit(f"char* {name} = {raw};")
                        self.declared_vars[name] = "char*"
                        self.string_vars.add(name)
                else:
                    self._emit(f"long long {name} = {raw};")
                    self.declared_vars[name] = "long long"
                    self.numeric_vars.add(name)
            elif is_non_constant:
                # Non-constant initializer - declare without init, defer to _ks_init_globals()
                # Check if it's a string expression
                is_dict = val_node.__class__.__name__ == "DictLiteral"

                # Check if it's a function call with known return type
                if val_node.__class__.__name__ == "FunctionCall":
                    fn_node = val_node.func
                    if (
                        fn_node.__class__.__name__ == "Identifier"
                        and fn_node.name in self.func_return_types
                    ):
                        c_type = self.func_return_types[fn_node.name]
                        self._emit(f"{c_type} {name};")
                        self.declared_vars[name] = c_type
                        if c_type == "char*":
                            self.string_vars.add(name)
                        if not hasattr(self, "_deferred_global_inits"):
                            self._deferred_global_inits = []
                        self._deferred_global_inits.append((name, raw))
                        return
                    # Check for time.time() or time.monotonic_ms() - returns double
                    if fn_node.__class__.__name__ == "MemberAccess":
                        obj = getattr(fn_node, "obj", None)
                        member = getattr(fn_node, "member", None)
                        if (
                            obj
                            and hasattr(obj, "name")
                            and obj.name == "time"
                            and member in ("time", "monotonic_ms", "monotonic")
                        ):
                            self._emit(f"double {name};")
                            self.declared_vars[name] = "double"
                            if not hasattr(self, "_deferred_global_inits"):
                                self._deferred_global_inits = []
                            # Use ks_time_seconds() instead of _ks_time(time)
                            if member == "time":
                                init_val = "ks_time_seconds()"
                            else:
                                init_val = "ks_time_monotonic_ms()"
                            self._deferred_global_inits.append((name, init_val))
                            return

                # Use explicit type if provided
                if explicit_type:
                    if explicit_type == "ptr":
                        c_type = "long long*"
                    elif explicit_type in ("i8", "u8"):
                        c_type = "char"
                    elif explicit_type in ("i16", "u16"):
                        c_type = "short"
                    elif explicit_type in ("i32", "u32"):
                        c_type = "int"
                    elif explicit_type in ("i64", "u64", "int", "uint"):
                        c_type = "long long"
                    elif explicit_type in ("f32"):
                        c_type = "float"
                    elif explicit_type in ("f64", "float"):
                        c_type = "double"
                    elif explicit_type == "str":
                        c_type = "char*"
                    else:
                        c_type = explicit_type
                elif is_dict:
                    c_type = "_ks_dict*"
                elif self._is_string_node(val_node):
                    c_type = "char*"
                    self.string_vars.add(name)
                else:
                    c_type = "long long*" if is_borrow else "long long"
                    self.numeric_vars.add(name)

                self._emit(f"{c_type} {name};")
                self.declared_vars[name] = c_type
                # Store for deferred initialization
                if not hasattr(self, "_deferred_global_inits"):
                    self._deferred_global_inits = []
                self._deferred_global_inits.append((name, raw))
            else:
                # Default to long long for expressions
                c_type = "long long*" if is_borrow else "long long"
                self._emit(f"{c_type} {name} = {raw};")
                self.declared_vars[name] = c_type
                self.numeric_vars.add(name)
        else:
            # No initialization - default to 0
            self._emit(f"long long {name} = 0;")
            self.declared_vars[name] = "long long"
            self.numeric_vars.add(name)

    def _is_non_constant_global_init(self, node):
        """Check if a node represents a non-constant initializer for C globals."""
        if node is None:
            return False
        cls = node.__class__.__name__
        # Literals are constant
        if cls == "Literal":
            return False
        # Identifiers reference variables (non-constant)
        if cls == "Identifier":
            return True
        # UnaryOp with borrow/move always references variables
        if cls == "UnaryOp":
            op = getattr(node, "op", None)
            if op in ("borrow", "move"):
                return True
            # Check operand
            operand = getattr(node, "operand", None) or getattr(node, "expr", None)
            return self._is_non_constant_global_init(operand)
        # BinaryOp - check both sides
        if cls == "BinaryOp":
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)
            return self._is_non_constant_global_init(
                left
            ) or self._is_non_constant_global_init(right)
        # Function calls are non-constant
        if cls == "FunctionCall":
            return True
        # Default: assume non-constant
        return True

    def _infer_func_return_type(self, node):
        """Infer whether function returns double, long long, char*, ks_array, or void."""
        # First: honour the explicit return-type annotation from the parser
        explicit = getattr(node, "return_type", None)
        if explicit:
            mapping = {
                "int": "long long",
                "i64": "long long",
                "i32": "long long",
                "float": "double",
                "f64": "double",
                "f32": "double",
                "double": "double",
                "string": "char*",
                "str": "char*",
                "bool": "long long",
                "void": "void",
            }
            if explicit in mapping:
                return mapping[explicit]

        # Helper to recursively find ReturnStmt in all nested structures
        def _find_returns(stmts):
            for stmt in stmts:
                if stmt.__class__.__name__ == "ReturnStmt" and stmt.value is not None:
                    yield stmt
                # Also check inside UnsafeStmt
                if stmt.__class__.__name__ == "UnsafeStmt":
                    if hasattr(stmt, "body"):
                        yield from _find_returns(stmt.body)
                # Check other compound statements that might contain returns
                if hasattr(stmt, "body"):
                    if isinstance(stmt.body, list):
                        yield from _find_returns(stmt.body)
                if hasattr(stmt, "then_body"):
                    if isinstance(stmt.then_body, list):
                        yield from _find_returns(stmt.then_body)
                if hasattr(stmt, "else_body"):
                    if isinstance(stmt.else_body, list):
                        yield from _find_returns(stmt.else_body)
                if hasattr(stmt, "cases"):
                    for case in stmt.cases:
                        if hasattr(case, "body"):
                            yield from _find_returns(case.body)
                        elif isinstance(case, (list, tuple)) and len(case) > 1:
                            body = case[1]
                            if isinstance(body, list):
                                yield from _find_returns(body)
                # Also check default case
                if hasattr(stmt, "default") and stmt.default:
                    yield from _find_returns(stmt.default)

        # Check if function returns an array (ListLiteral)
        for ret in _find_returns(node.body):
            v = ret.value
            if v.__class__.__name__ == "ListLiteral":
                return "ks_array"
            # Check if function returns an anonymous function (FunctionDef)
            if v.__class__.__name__ == "FunctionDef":
                return "func_ptr"

        # Fallback: heuristic scan of return statements
        has_return_with_value = False
        for ret in _find_returns(node.body):
            has_return_with_value = True
            v = ret.value
            if v.__class__.__name__ == "FunctionCall":
                fn = v.func
                if fn.__class__.__name__ == "MemberAccess":
                    if (
                        hasattr(fn.obj, "name")
                        and fn.obj.name == "time"
                        and fn.member in ("time", "monotonic_ms", "monotonic")
                    ):
                        return "double"
            if v.__class__.__name__ == "BinaryOp":
                return "double"
            if v.__class__.__name__ == "Literal" and isinstance(
                getattr(v, "value", None), float
            ):
                return "double"
            if v.__class__.__name__ == "Literal" and isinstance(
                getattr(v, "value", None), str
            ):
                return "char*"
            if v.__class__.__name__ == "Literal" and isinstance(
                getattr(v, "value", None), int
            ):
                return "long long"
            # If returning identifier (like 'dest') assume long long
            if v.__class__.__name__ == "Identifier":
                # Check if function has any LetDecl with ListLiteral - if so, assume ks_array return
                def _find_let_with_list(stmts):
                    for stmt in stmts:
                        if stmt.__class__.__name__ == "LetDecl":
                            if (
                                hasattr(stmt, "value")
                                and stmt.value.__class__.__name__ == "ListLiteral"
                            ):
                                return True
                        # Check inside UnsafeStmt
                        if stmt.__class__.__name__ == "UnsafeStmt":
                            if hasattr(stmt, "body") and _find_let_with_list(stmt.body):
                                return True
                        # Check other compound statements
                        for attr in ["body", "then_body", "else_body"]:
                            if hasattr(stmt, attr):
                                val = getattr(stmt, attr)
                                if isinstance(val, list) and _find_let_with_list(val):
                                    return True
                        if hasattr(stmt, "cases"):
                            for case in stmt.cases:
                                if hasattr(case, "body") and _find_let_with_list(
                                    case.body
                                ):
                                    return True
                    return False

                if _find_let_with_list(node.body):
                    return "ks_array"
                return "long long"
        # If function has ReturnStmt with value but we couldn't infer type, assume long long
        if has_return_with_value:
            return "long long"
        return None

    def _transpile_function(self, node):
        """Emit a C function for a KentScript func definition."""
        # --- Generator: override return type to ks_array ---
        is_generator = getattr(node, "is_generator", False)
        is_async = getattr(node, "is_async", False)
        if is_generator:
            ret_type = "ks_array"
        else:
            # Detect return type
            ret_type = self._infer_func_return_type(node) or "void"
        # Map internal type names to C types
        if ret_type == "func_ptr":
            ret_type = "void*"
        self.func_return_types[node.name] = ret_type

        # --- Decorators ---
        decorators = getattr(node, "decorators", []) or []
        active_decorators = [d for d in decorators if d not in _NOOP_DECORATORS]
        # If there are active (user-defined) decorators, emit function with _impl suffix
        # and a global function pointer that applies the decorator.
        original_name = node.name
        if active_decorators:
            node.name = f"_ks_impl_{original_name}"

        # Build parameter list using param_types when available
        param_type_map = getattr(node, "param_types", {}) or {}
        _c_type_map = {
            "int": "long long",
            "i64": "long long",
            "i32": "long long",
            "float": "double",
            "f64": "double",
            "f32": "double",
            "double": "double",
            "string": "char*",
            "str": "char*",
            "bool": "long long",
        }

        def _param_c_type(p):
            kt = param_type_map.get(p, None)
            if kt is not None:
                return _c_type_map.get(kt, "char*")

            # Analyze parameter usage in function body to infer type
            body = getattr(node, "body", []) or []

            def _analyze_param_usage(stmts, param):
                string_usage = False
                numeric_usage = False
                array_usage = False

                def _check_node(n):
                    nonlocal string_usage, numeric_usage, array_usage
                    if hasattr(n, "__dict__"):
                        for attr_name, attr_val in n.__dict__.items():
                            if (
                                attr_name == "body"
                                and n.__class__.__name__ == "UnsafeStmt"
                            ):
                                # UnsafeStmt.body is a list of statements
                                for stmt in attr_val:
                                    _check_node(stmt)
                            elif (
                                attr_name == "args"
                                and n.__class__.__name__ == "FunctionCall"
                            ):
                                # Function arguments also contain expressions to check
                                for arg in attr_val:
                                    _check_node(arg)
                            elif isinstance(attr_val, list):
                                for item in attr_val:
                                    _check_node(item)
                            else:
                                _check_node(attr_val)

                    # Check if this node involves the parameter
                    node_str = str(n)
                    if param in node_str:
                        # Check for str(param) - conversion TO string suggests NUMERIC parameter
                        # This catches patterns like: FunctionCall(func=Identifier(name='str'...), args=[Identifier(name='n'...)]
                        cls_name = n.__class__.__name__ if hasattr(n, '__class__') else ''
                        if cls_name == 'FunctionCall':
                            func = getattr(n, 'func', None)
                            if func and hasattr(func, 'name') and func.name == 'str':
                                args = getattr(n, 'args', [])
                                for arg in args:
                                    if hasattr(arg, 'name') and arg.name == param:
                                        numeric_usage = True
                                        break
                        # Also check string representation for str(param) pattern
                        str_pattern = f"str({param})"
                        if str_pattern in node_str:
                            numeric_usage = True
                        # Check if this is str() call - if so, mark param as numeric
                        if f"name='str'" in node_str and f"name='{param}'" in node_str:
                            numeric_usage = True
                        # Check for string operations (f-strings, concat helpers)
                        if (
                            "FStringLiteral" in node_str
                            or 'f"' in node_str
                            or "f'" in node_str
                            or "_ks_concat" in node_str
                        ):
                            string_usage = True
                        # Detect f-string interpolation: BinaryOp with + mixing string Literals and str() calls
                        if (
                            "BinaryOp" in node_str
                            and "op='+'" in node_str
                            and "Literal(value=" in node_str
                        ):
                            string_usage = True
                        # Check for string concatenation: BinaryOp with + where one side is a string literal
                        # BUT only if str(param) is NOT being used - str(param) means param is numeric!
                        if (
                            "BinaryOp" in node_str
                            and "op='+'" in node_str
                            and (
                                "Literal(value='" in node_str
                                or 'Literal(value="' in node_str
                            )
                        ):
                            # Check if this BinaryOp contains str(param) - if so, don't mark as string usage
                            if f"name='str'" not in node_str:
                                string_usage = True
                        # Check for arithmetic operations
                        if any(
                            op in node_str for op in ["+", "-", "*", "/", "%", "**"]
                        ):
                            # If it's not string concatenation, it's numeric
                            if not ("str(" in node_str or '"' in node_str):
                                numeric_usage = True
                        # Check for array usage
                        try:
                            cls = n.__class__.__name__
                            if cls == "ForStmt":
                                iter_obj = getattr(n, "iterable", None)
                                if (
                                    iter_obj
                                    and hasattr(iter_obj, "__class__")
                                    and iter_obj.__class__.__name__ == "Identifier"
                                    and hasattr(iter_obj, "name")
                                    and iter_obj.name == param
                                ):
                                    array_usage = True
                            elif cls == "IndexAccess":
                                obj = getattr(n, "obj", None)
                                if (
                                    obj
                                    and hasattr(obj, "__class__")
                                    and obj.__class__.__name__ == "Identifier"
                                    and hasattr(obj, "name")
                                    and obj.name == param
                                ):
                                    array_usage = True
                        except Exception:
                            pass

                for stmt in stmts:
                    _check_node(stmt)
                return string_usage, numeric_usage, array_usage

            import re
            
            body_str = "\n".join(str(stmt) for stmt in body)
            
            # Check for numeric match cases FIRST - this is a strong indicator of numeric param
            if re.search(r"Literal\(value=[0-9]+\)", body_str):
                return "long long"
            
            # Check if param is converted to string via str(param) - this indicates NUMERIC
            # Use regex to match name='str' followed by args containing name='p'
            if re.search(rf"name='str'.*name='{p}'", body_str, re.DOTALL):
                # Check if there's also string concat with literals (f-string)
                has_string_concat = (
                    "BinaryOp" in body_str 
                    and "op='+'" in body_str
                    and (
                        "Literal(value='" in body_str
                        or 'Literal(value="' in body_str
                    )
                )
                if has_string_concat:
                    return "char*"
                return "long long"
            
            # Check for string operations - parameter is used as string
            has_string_op = (
                "split" in body_str 
                or "to_lower" in body_str
                or "to_upper" in body_str
                or "_ks_concat" in body_str 
                or "FStringLiteral" in body_str
            )
            
            # If string operations, use char*
            if has_string_op:
                return "char*"
            # Default to long long
            return "long long"

        # [KS-OS-001] OS-level decorator attributes
        os_attrs = []
        bare_metal_attrs = []
        decorator_args = getattr(node, "decorator_args", {}) or {}

        # Collect OS-level decorators from the full decorator list
        decorators = getattr(node, "decorators", []) or []
        os_decorators = [
            d
            for d in decorators
            if d
            in (
                "kernel",
                "interrupt",
                "syscall",
                "naked",
                "always_inline",
                "aligned",
                "section",
                "volatile_mem",
                "packed",
            )
        ]

        for dec in os_decorators:
            if dec == "kernel":
                os_attrs.append("__attribute__((noinline))")
                bare_metal_attrs.append("#define KS_KERNEL 1")
            elif dec == "interrupt":
                os_attrs.append("__attribute__((interrupt))")
            elif dec == "naked":
                os_attrs.append("__attribute__((naked))")
            elif dec == "always_inline":
                os_attrs.append("__attribute__((always_inline)) static")
            elif dec == "aligned":
                align_args = decorator_args.get("aligned", [])
                if align_args:
                    align_val = getattr(align_args[0], "value", align_args[0])
                    os_attrs.append(f"__attribute__((aligned({align_val})))")
                else:
                    os_attrs.append("__attribute__((aligned(16)))")
            elif dec == "section":
                section_args = decorator_args.get("section", [])
                if section_args:
                    section_name = getattr(section_args[0], "value", section_args[0])
                    os_attrs.append(f'__attribute__((section("{section_name}")))')
                else:
                    os_attrs.append('__attribute__((section(".kernel_text")))')
            elif dec == "volatile_mem":
                os_attrs.append("volatile")
            elif dec == "syscall":
                os_attrs.append("__attribute__((syscall))")

        # [KS-REF-037] RESTRICT pointer injection
        if node.params and self.enable_optimizations:
            params_list = []
            for p in node.params:
                if p.startswith("*"):
                    # Variadic: use C variadic syntax
                    params_list.append("...")
                    break
                c_type = _param_c_type(p)
                if "*" not in c_type:
                    if c_type == "char*":
                        qualified = self.restrict_injector.register_pointer(
                            p, "char*", escapes=False, has_alias=False
                        )
                    else:
                        qualified = f"{c_type} {p}"
                else:
                    qualified = self.restrict_injector.register_pointer(
                        p, c_type, escapes=False, has_alias=False
                    )
                params_list.append(qualified)
            params_c = ", ".join(params_list) if params_list else "void"
        else:
            if node.params:
                parts = []
                for p in node.params:
                    if p.startswith("*"):
                        parts.append("...")
                        break
                    parts.append(f"{_param_c_type(p)} {p}")
                params_c = ", ".join(parts)
            else:
                params_c = "void"

        # Build function declaration with OS-level attributes
        func_prefix = ""
        if os_attrs:
            func_prefix = " ".join(os_attrs) + " "
        elif bare_metal_attrs:
            for attr in bare_metal_attrs:
                self._emit(attr)

        if node.name != "main":
            self._emit(f"{func_prefix}{ret_type} {node.name}({params_c}) {{")
        else:
            self._emit(f"{func_prefix}{ret_type} ks_user_main({params_c}) {{")
        self.indent_level += 1
        # Save declared_vars state BEFORE adding params (for proper scoping)
        old_declared = dict(self.declared_vars)
        # Save and restore string/numeric var state
        old_svars = set(self.string_vars)
        old_nvars = set(self.numeric_vars)
        # Add function parameters AFTER saving old state (so params don't leak to next function)
        for p in node.params:
            pt = _param_c_type(p)
            # Register parameter type in declared_vars for later use (e.g., array iteration)
            self.declared_vars[p] = pt
            # Track simple types for quick string/numeric classification
            if pt in ("double", "long long"):
                self.numeric_vars.add(p)
            elif pt == "char*":
                self.string_vars.add(p)
            # ks_array and other types are not added to these sets

        # Generator: declare result array at top of body
        if is_generator:
            self._emit("ks_array _gen_result = {NULL, 0};")

        for stmt in node.body:
            self._transpile_stmt(stmt)

        # Generator: return collected array
        if is_generator:
            self._emit("return _gen_result;")
        else:
            # Ensure function always returns something (unless void)
            if ret_type == "double":
                self._emit("return 0.0;")
            elif ret_type == "long long":
                self._emit("return 0LL;")
            elif ret_type == "char*":
                self._emit('return "";')
            # void: no default return needed
        self.indent_level -= 1
        self._emit("}")
        self.string_vars = old_svars
        self.numeric_vars = old_nvars
        self.declared_vars = old_declared

        # --- Emit decorator wrapper (function pointer) ---
        if active_decorators:
            # Restore original name on node
            node.name = original_name
            # Build param signature for function pointer type
            param_types_sig = (
                ", ".join(_param_c_type(p) for p in node.params)
                if node.params
                else "void"
            )
            impl_name = f"_ks_impl_{original_name}"
            # Apply decorators right-to-left (innermost first)
            wrapped = f"(void*){impl_name}"
            for dec in reversed(active_decorators):
                wrapped = f"(void*){dec}({wrapped})"
            self._emit(f"/* decorator(s): {', '.join(active_decorators)} */")
            self._emit(
                f"{ret_type} (*{original_name})({param_types_sig}) = "
                f"({ret_type}(*)({param_types_sig})){wrapped};"
            )
            # Register the function pointer type
            self.func_return_types[original_name] = ret_type
        else:
            node.name = original_name

        # --- Emit async coroutine entry wrapper ---
        if is_async and not active_decorators:
            # Only emit a no-arg coroutine wrapper (for use with async.run())
            # Async functions with args are called directly via await
            if not node.params:
                self._emit(f"static void _ks_coro_{original_name}(void* _arg) {{")
                self._emit(f"    (void)_arg;")
                self._emit(f"    {original_name}();")
                self._emit(f"}}")

    # ------------------------------------------------------------------ statements

    def _transpile_stmt(self, node):
        cls = node.__class__.__name__

        if cls in ("LetDecl", "Assignment"):
            # Quick fix: check function return type for LetDecl before calling _transpile_decl
            if cls == "LetDecl" and hasattr(node, "value") and node.value:
                val = node.value
                # Handle await expressions
                if val.__class__.__name__ == "AsyncAwait":
                    val = val.expr
                # Handle Cast expressions - infer type from cast target
                if val.__class__.__name__ == "Cast":
                    target_type = getattr(val, "target_type", None)
                    if target_type == "ptr":
                        raw = self._transpile_expr(node.value)
                        name = node.name
                        if name not in self.declared_vars:
                            self._emit(f"void* {name} = {raw};")
                            self.declared_vars[name] = "void*"
                            return
                if val.__class__.__name__ == "FunctionCall":
                    if hasattr(val, "func") and hasattr(val.func, "name"):
                        fname = val.func.name
                        if fname in self.func_return_types:
                            ret_type = self.func_return_types[fname]
                            raw = self._transpile_expr(node.value)
                            name = node.name
                            if name not in self.declared_vars:
                                self._emit(f"{ret_type} {name} = {raw};")
                                self.declared_vars[name] = ret_type
                                if ret_type == "char*":
                                    self.string_vars.add(name)
                            else:
                                self._emit(f"{name} = {raw};")
                            return
            self._transpile_decl(node)

        elif cls == "FunctionCall":
            self._transpile_call_stmt(node)

        elif cls == "FunctionDef":
            # Nested function — emit inline (C doesn't support nested funcs natively,
            # so we use a forward declaration approach with a static local via __attribute__)
            # For simplicity we hoist it: emit as a static helper before use.
            # Since we already hoisted top-level ones, just emit a C func here.
            self._transpile_function(node)

        elif cls == "ReturnStmt":
            if node.value is not None:
                # Check if returning a ListLiteral (array)
                if node.value.__class__.__name__ == "ListLiteral":
                    elems = (
                        node.value.elements if hasattr(node.value, "elements") else []
                    )
                    # For dynamic arrays, use calloc and initialize at runtime
                    arr_name = f"_ret_arr_{self._label_count}"
                    self._label_count += 1
                    arr_ptr = arr_name + "_ptr"
                    self._emit(
                        f"long long* {arr_ptr} = (long long*)calloc({len(elems)}, sizeof(long long));"
                    )
                    # Initialize each element with runtime values
                    for i, elem in enumerate(elems):
                        elem_expr = self._transpile_expr(elem)
                        self._emit(f"{arr_ptr}[{i}] = {elem_expr};")
                    # Return wrapped array
                    self._emit(f"return ks_make_array({arr_ptr}, {len(elems)});")
                else:
                    val = self._transpile_expr(node.value)
                    self._emit(f"return {val};")
            else:
                self._emit("return;")

        elif cls == "YieldStmt":
            # Generator yield: append value to _gen_result array
            if node.value is not None:
                val = self._transpile_expr(node.value)
                self._emit(f"_ks_array_append(&_gen_result, (long long)({val}));")
            elif node.from_iter is not None:
                fi = node.from_iter
                fi_cls = fi.__class__.__name__
                # yield from range(n) or range(a,b)
                if (
                    fi_cls == "FunctionCall"
                    and hasattr(fi, "func")
                    and getattr(fi.func, "name", "") == "range"
                ):
                    rargs = fi.args
                    if len(rargs) == 1:
                        sc, ec = "0", self._transpile_expr(rargs[0])
                    else:
                        sc, ec = (
                            self._transpile_expr(rargs[0]),
                            self._transpile_expr(rargs[1]),
                        )
                    tmp = f"_yf_{self._label_count}"
                    self._label_count += 1
                    self._emit(f"for (long long {tmp} = {sc}; {tmp} < {ec}; {tmp}++)")
                    self._emit(f"    _ks_array_append(&_gen_result, {tmp});")
                # yield from string → yield each char as long long
                elif (
                    (fi_cls == "Identifier" and fi.name in self.string_vars)
                    or fi_cls == "Literal"
                    and isinstance(getattr(fi, "value", None), str)
                ):
                    iter_c = self._transpile_expr(fi)
                    tmp = f"_yf_{self._label_count}"
                    self._label_count += 1
                    self._emit(f"{{ const char* {tmp} = {iter_c};")
                    self._emit(
                        f"  for (long long _i_{tmp} = 0; {tmp}[_i_{tmp}]; _i_{tmp}++)"
                    )
                    self._emit(
                        f"    _ks_array_append(&_gen_result, (long long)(unsigned char){tmp}[_i_{tmp}]); }}"
                    )
                else:
                    # yield from ks_array or unknown iterable
                    iter_c = self._transpile_expr(fi)
                    tmp = f"_yf_{self._label_count}"
                    self._label_count += 1
                    # Check if it's a known ks_array variable
                    var_name = getattr(fi, "name", None)
                    if (
                        var_name
                        and var_name in self.declared_vars
                        and self.declared_vars[var_name] == "ks_array"
                    ):
                        self._emit(f"{{ ks_array {tmp} = {iter_c};")
                    else:
                        self._emit(f"{{ ks_array {tmp} = (ks_array)({iter_c});")
                    self._emit(
                        f"  for (long long _i_{tmp} = 0; _i_{tmp} < {tmp}.length; _i_{tmp}++)"
                    )
                    self._emit(
                        f"    _ks_array_append(&_gen_result, {tmp}.data[_i_{tmp}]); }}"
                    )

        elif cls == "IfStmt":
            cond = self._transpile_cond(node.condition)

            # [KS-REF-037] Branch prediction optimization
            if self.enable_optimizations:
                then_stmts = (
                    [str(s) for s in node.then_block] if node.then_block else []
                )
                wrapped_cond, kind = self.branch_optimizer.analyze_if_statement(
                    cond, then_stmts
                )
                if kind == "error_check":
                    # Error checking branch is unlikely
                    self._emit(f"if ({wrapped_cond}) {{")
                else:
                    # Normal execution path
                    self._emit(f"if ({cond}) {{")
            else:
                self._emit(f"if ({cond}) {{")

            self.indent_level += 1
            for s in node.then_block:
                self._transpile_stmt(s)
            self.indent_level -= 1
            if node.elif_blocks:
                for elif_cond, elif_body in node.elif_blocks:
                    ec = self._transpile_cond(elif_cond)
                    self._emit(f"}} else if ({ec}) {{")
                    self.indent_level += 1
                    for s in elif_body:
                        self._transpile_stmt(s)
                    self.indent_level -= 1
            if node.else_block:
                self._emit("} else {")
                self.indent_level += 1
                for s in node.else_block:
                    self._transpile_stmt(s)
                self.indent_level -= 1
            self._emit("}")

        elif cls == "WhileStmt":
            cond = self._transpile_cond(node.condition)
            self._emit(f"while ({cond}) {{")
            self.indent_level += 1
            # Add asm barrier at loop start in benchmark mode
            if self.benchmark_mode:
                self._emit(
                    'asm volatile("" : : : "memory");  /* Prevent loop removal */'
                )
            for s in node.body:
                self._transpile_stmt(s)
            # Add asm barrier at loop end in benchmark mode
            if self.benchmark_mode:
                self._emit('asm volatile("" : : : "memory");  /* Force completion */')
            self.indent_level -= 1
            self._emit("}")

        elif cls == "ForStmt":
            # for i in range(n) { ... } or for ch in string { ... }
            var = node.var
            iter_expr = node.iterable
            # Check if it's a range() call
            if (
                iter_expr.__class__.__name__ == "FunctionCall"
                and iter_expr.func.__class__.__name__ == "Identifier"
                and iter_expr.func.name == "range"
            ):
                args = iter_expr.args
                if len(args) == 1:
                    end_v = self._transpile_expr(args[0])
                    self._emit(
                        f"for (long long {var} = 0; {var} < {end_v}; {var}++) {{"
                    )
                elif len(args) == 2:
                    start_v = self._transpile_expr(args[0])
                    end_v = self._transpile_expr(args[1])
                    self._emit(
                        f"for (long long {var} = {start_v}; {var} < {end_v}; {var}++) {{"
                    )
                elif len(args) == 3:
                    start_v = self._transpile_expr(args[0])
                    end_v = self._transpile_expr(args[1])
                    step_v = self._transpile_expr(args[2])
                    # Detect negative literal step to use correct comparison
                    step_node = args[2]
                    is_neg = (
                        step_node.__class__.__name__ == "UnaryOp"
                        and getattr(step_node, "op", "") == "-"
                    ) or (
                        step_node.__class__.__name__ == "Literal"
                        and isinstance(getattr(step_node, "value", None), (int, float))
                        and step_node.value < 0
                    )
                    cmp_op = ">" if is_neg else "<"
                    self._emit(
                        f"for (long long {var} = {start_v}; {var} {cmp_op} {end_v}; {var} += {step_v}) {{"
                    )
                else:
                    self._emit(f"for (long long {var} = 0; {var} < 10; {var}++) {{")
            else:
                # Collection iteration: for item in collection
                # Generate: for (int _i = 0; _i < collection_length; _i++) { item = collection[_i]; ... }
                iter_val = self._transpile_expr(iter_expr)
                iter_type = iter_expr.__class__.__name__

                # For strings: iterate over characters
                if iter_type == "StringLiteral" or "str" in str(iter_val).lower():
                    idx_var = f"_idx_{var}"
                    self._emit(
                        f"for (long long {idx_var} = 0; {iter_val}[{idx_var}] != '\\0'; {idx_var}++) {{"
                    )
                    self.indent_level += 1
                    self._emit(f"char {var} = {iter_val}[{idx_var}];")
                    for s in node.body:
                        self._transpile_stmt(s)
                    self.indent_level -= 1
                    self._emit("}")
                    return
                else:
                    # Generic collection: check if it's an array or string
                    idx_var = f"_idx_{var}"
                    # Check if it's an identifier (variable)
                    if iter_type == "Identifier":
                        var_name = iter_expr.name
                        # Check if it's a ks_array (first-class array)
                        if (
                            var_name in self.declared_vars
                            and self.declared_vars[var_name] == "ks_array"
                        ):
                            iter_tmp = f"_iter_{idx_var}"
                            self._emit(f"ks_array {iter_tmp} = {iter_val};")
                            self._emit(
                                f"for (long long {idx_var} = 0; {idx_var} < {iter_tmp}.length; {idx_var}++) {{"
                            )
                            self.indent_level += 1
                            self._emit(
                                f"long long {var} = ks_array_get({iter_tmp}, {idx_var});"
                            )
                        # Check if it's a string variable
                        elif var_name in self.string_vars or (
                            var_name in self.declared_vars
                            and "char*" in str(self.declared_vars[var_name])
                        ):
                            # String iteration
                            self._emit(
                                f"for (long long {idx_var} = 0; {iter_val}[{idx_var}] != '\\0'; {idx_var}++) {{"
                            )
                            self.indent_level += 1
                            self._emit(f"char {var} = {iter_val}[{idx_var}];")
                        else:
                            # Raw array pointer - try to find stored length variable
                            len_var = f"{var_name}__len"
                            if len_var in self.declared_vars:
                                array_len = len_var  # use the variable
                            else:
                                array_len = "5"  # fallback
                            self._emit(
                                f"for (long long {idx_var} = 0; {idx_var} < {array_len}; {idx_var}++) {{"
                            )
                            self.indent_level += 1
                            self._emit(f"long long {var} = {iter_val}[{idx_var}];")

                        for s in node.body:
                            self._transpile_stmt(s)
                        self.indent_level -= 1
                        self._emit("}")
                        return
                    else:
                        # Generic expression collection: evaluate into a temp ks_array
                        iter_tmp = f"_iter_expr_{self._label_count}"
                        self._label_count += 1
                        self._emit(f"ks_array {iter_tmp} = (ks_array)({iter_val});")
                        self._emit(
                            f"for (long long {idx_var} = 0; {idx_var} < {iter_tmp}.length; {idx_var}++) {{"
                        )
                        self.indent_level += 1
                        self._emit(
                            f"long long {var} = ks_array_get({iter_tmp}, {idx_var});"
                        )
                        for s in node.body:
                            self._transpile_stmt(s)
                        self.indent_level -= 1
                        self._emit("}")
                        return
            self.indent_level += 1
            # Inside loop body, var is an integer
            for s in node.body:
                self._transpile_stmt(s)
            self.indent_level -= 1
            self._emit("}")

        elif cls == "BreakStmt":
            self._emit("break;")

        elif cls == "ContinueStmt":
            self._emit("continue;")

        elif cls in ("ImportStmt",):
            pass  # No-op at C level (headers already emitted in preamble)

        elif cls == "AsyncAwait":
            # await expr as a statement — use void variant to avoid __typeof__(void) error
            inner = self._transpile_expr(node.expr)
            # Check if the awaited expression returns void
            inner_node = node.expr
            inner_cls = inner_node.__class__.__name__
            is_void = False
            if inner_cls == "FunctionCall" and hasattr(inner_node, "func"):
                fn = inner_node.func
                fname = getattr(fn, "name", None)
                if fname and self.func_return_types.get(fname) == "void":
                    is_void = True
                elif fname and fname not in self.func_return_types:
                    is_void = True  # unknown → assume void for safety
            if is_void:
                self._emit(f"_KS_AWAIT_VOID({inner});")
            else:
                self._emit(f"(void)_KS_AWAIT({inner});")

        elif cls in ("TryExcept",):
            # Emit try body unconditionally (C has no exceptions; best-effort)
            self._emit("{ /* try */")
            self.indent_level += 1
            for s in node.try_block if hasattr(node, "try_block") else []:
                self._transpile_stmt(s)
            self.indent_level -= 1
            self._emit("} /* end try */")
            # Emit except blocks as guarded dead-code so the body is at least compiled
            for exc_type, exc_var, except_body in (
                getattr(node, "except_blocks", None) or []
            ):
                self._emit("if (0) { /* except */")
                self.indent_level += 1
                for s in except_body:
                    self._transpile_stmt(s)
                self.indent_level -= 1
                self._emit("}")
            # Always emit finally block — it runs unconditionally
            for s in getattr(node, "finally_block", None) or []:
                self._transpile_stmt(s)

        elif cls == "WithStmt":
            # with ctx as var { body }
            # Emit: __enter__, body, __exit__ (best-effort; no exception routing in C)
            ctx_c = self._transpile_expr(node.context_expr)
            tmp = f"_with_ctx_{self._label_count}"
            self._label_count += 1
            self._emit(f"{{ /* with */")
            self.indent_level += 1
            self._emit(f"void* {tmp} = (void*)({ctx_c});")
            if node.var:
                self._emit(f"void* {node.var} = {tmp};")
            for s in node.body:
                self._transpile_stmt(s)
            self.indent_level -= 1
            self._emit("} /* end with */")

        elif cls in ("UnsafeBlock", "UnsafeStmt"):
            # Emit unsafe block contents with braces for proper scoping
            self._emit("/* unsafe block */")
            self._emit("{")
            self.indent_level += 1
            body = getattr(node, "body", [])
            for s in body:
                self._transpile_stmt(s)
            self.indent_level -= 1
            self._emit("}")

        elif cls == "AssemblyBlock":
            # Emit inline assembly
            code = getattr(node, "code", "")
            self._emit(f'__asm__ __volatile__("{code}");')

        elif cls == "ClassDef":
            self._transpile_class(node)

        elif cls == "MatchStmt":
            # Pattern matching: match value { pattern => body, ... }
            value = self._transpile_expr(node.expr)
            cases = node.cases if hasattr(node, "cases") else []

            # Use switch statement for simple integer/enum matches
            has_default = any(
                hasattr(c, "pattern")
                and (c.pattern == "_" or getattr(c.pattern, "name", None) == "_")
                for c in cases
            )

            self._emit(f"{{ /* match statement */")
            self.indent_level += 1
            self._emit(f"long long _match_val = (long long)({value});")
            self._emit(f"char* _match_str = (char*)({value});")

            first = True
            for case in cases:
                pattern = case.pattern if hasattr(case, "pattern") else case[0]
                body = case.body if hasattr(case, "body") else case[1]

                # Check if pattern is wildcard
                is_wildcard = (
                    pattern == "_"
                    or (hasattr(pattern, "name") and pattern.name == "_")
                    or (isinstance(pattern, str) and pattern == "_")
                )

                if is_wildcard:
                    # Default case
                    if not first:
                        self._emit("} else {")
                    else:
                        self._emit("{")
                    self.indent_level += 1
                    if isinstance(body, list):
                        for stmt in body:
                            self._transpile_stmt(stmt)
                    else:
                        self._transpile_stmt(body)
                    self.indent_level -= 1
                else:
                    # Specific pattern — use strcmp for string literals, == for others
                    pattern_val = self._transpile_expr(pattern)
                    is_str_pat = pattern.__class__.__name__ == "Literal" and isinstance(
                        getattr(pattern, "value", None), str
                    )
                    if is_str_pat:
                        cond = f"strcmp(_match_str, {pattern_val}) == 0"
                    else:
                        cond = f"_match_val == {pattern_val}"
                    if first:
                        self._emit(f"if ({cond}) {{")
                        first = False
                    else:
                        self._emit(f"}} else if ({cond}) {{")
                    self.indent_level += 1
                    if isinstance(body, list):
                        for stmt in body:
                            self._transpile_stmt(stmt)
                    else:
                        self._transpile_stmt(body)
                    self.indent_level -= 1

            # Emit default case from node.default
            default_body = getattr(node, "default", None)
            if default_body:
                if not first:
                    self._emit("} else {")
                else:
                    self._emit("{")
                self.indent_level += 1
                for stmt in default_body:
                    self._transpile_stmt(stmt)
                self.indent_level -= 1

            if not first or default_body:  # Close the if chain
                self._emit("}")
            self.indent_level -= 1
            self._emit("}")

        elif cls == "AssertStmt":
            cond = self._transpile_expr(node.condition)
            msg = ""
            if hasattr(node, "message") and node.message:
                msg = self._transpile_expr(node.message)
                self._emit(
                    f'if (!({cond})) {{ fprintf(stderr, "Assertion failed: %s\\n", {msg}); abort(); }}'
                )
            else:
                self._emit(
                    f'if (!({cond})) {{ fprintf(stderr, "Assertion failed\\n"); abort(); }}'
                )

        elif cls == "RaiseStmt":
            msg = ""
            if hasattr(node, "exception") and node.exception:
                msg = self._transpile_expr(node.exception)
                self._emit(f'fprintf(stderr, "Exception: %s\\n", {msg}); exit(1);')
            else:
                self._emit('fprintf(stderr, "Exception raised\\n"); exit(1);')

        elif cls == "DelStmt":
            target = getattr(node, "target", None)
            if target:
                t_name = target.name if hasattr(target, "name") else str(target)
                if t_name in self.declared_vars:
                    c_type = self.declared_vars[t_name]
                    if c_type in ("long long", "int", "double", "float"):
                        self._emit(f"{t_name} = 0;  /* deleted */")
                    elif "char*" in str(c_type):
                        self._emit(f"{t_name} = NULL;  /* deleted */")
                    else:
                        self._emit(
                            f"memset(&{t_name}, 0, sizeof({t_name}));  /* deleted */"
                        )

        elif cls == "EnumDef":
            pass  # Enums are handled in preamble (before functions)

        elif cls == "StructDef":
            struct_name = node.name
            self._emit(f"/* struct {struct_name} */")
            self._emit(f"typedef struct {{")
            fields = getattr(node, "fields", [])
            for field in fields:
                field_name = getattr(field, "name", None)
                field_type = getattr(field, "field_type", "long long")
                if field_name:
                    self._emit(f"    {field_type} {field_name};")
            self._emit(f"}} {struct_name}_t;")

        elif cls == "UnionDef":
            union_name = node.name
            self._emit(f"/* union {union_name} */")
            self._emit(f"typedef union {{")
            fields = getattr(node, "fields", [])
            for field in fields:
                field_name = getattr(field, "name", None)
                field_type = getattr(field, "field_type", "long long")
                if field_name:
                    self._emit(f"    {field_type} {field_name};")
            self._emit(f"}} {union_name}_t;")

        elif cls == "TypeAlias":
            alias_name = getattr(node, "name", "unknown_t")
            target_type = getattr(node, "target_type", "long long")
            self._emit(f"typedef {target_type} {alias_name};")

        elif cls == "PassStmt":
            self._emit(";  /* pass */")

        elif cls == "GlobalStmt":
            vars = getattr(node, "vars", [])
            for v in vars:
                vname = (
                    v
                    if isinstance(v, str)
                    else (v.name if hasattr(v, "name") else str(v))
                )
                self.declared_vars[vname] = self.declared_vars.get(vname, "long long")

        elif cls == "NonlocalStmt":
            vars = getattr(node, "vars", [])
            for v in vars:
                vname = (
                    v
                    if isinstance(v, str)
                    else (v.name if hasattr(v, "name") else str(v))
                )
                pass  # C doesn't have nonlocal; variable lookup handles it

        elif cls == "InterfaceDef":
            iface_name = node.name
            self._emit(
                f"/* interface {iface_name} - C has no interfaces, using struct */"
            )
            self._emit(f"typedef struct {{ void* _vtable; }} {iface_name}_t;")

        elif cls == "DoWhileStmt":
            self._emit("{ /* do-while */")
            self.indent_level += 1
            for s in node.body:
                self._transpile_stmt(s)
            cond = self._transpile_cond(node.condition)
            self._emit(f"}} while ({cond});")
            self.indent_level -= 1

        elif cls == "SwitchStmt":
            value = self._transpile_expr(node.expr)
            self._emit(f"{{ /* switch */")
            self.indent_level += 1
            self._emit(f"long long _sw_val = (long long)({value});")
            cases = getattr(node, "cases", [])
            for case in cases:
                pattern = getattr(case, "pattern", None)
                body = getattr(case, "body", [])
                if pattern is None:
                    pattern = case[0] if isinstance(case, tuple) else None
                    body = case[1] if isinstance(case, tuple) else body
                if pattern == "default" or (
                    hasattr(pattern, "name") and pattern.name == "default"
                ):
                    self._emit("default:")
                    self.indent_level += 1
                    for s in body:
                        self._transpile_stmt(s)
                    self._emit("break;")
                    self.indent_level -= 1
                else:
                    pattern_val = self._transpile_expr(pattern)
                    self._emit(f"case {pattern_val}:")
                    self.indent_level += 1
                    for s in body:
                        self._transpile_stmt(s)
                    self._emit("break;")
                    self.indent_level -= 1
            self._emit("}")
            self.indent_level -= 1
            self._emit("}")

        elif cls == "ThreadStmt":
            body = getattr(node, "body", [])
            func_name = (
                getattr(node, "func_name", None) or f"_thread_func_{self._label_count}"
            )
            self._label_count += 1
            self._emit(f"/* thread start */")
            self._emit(
                f"{{ pthread_t _th; pthread_create(&_th, NULL, (void*(*)(void*)){func_name}, NULL); }}"
            )

        elif cls == "SizeofExpr":
            expr_type = getattr(node, "expr_type", None)
            if expr_type:
                self._emit(f"sizeof({expr_type})")
            else:
                self._emit("sizeof(long long)")

        elif cls == "InlineAsmStmt":
            code = getattr(node, "code", "")
            is_volatile = getattr(node, "volatile", False)
            prefix = "__asm__ __volatile__" if is_volatile else "__asm__"
            self._emit(f'{prefix}("{code}");')

        elif cls == "StaticAssertStmt":
            cond = self._transpile_expr(node.condition)
            msg = getattr(node, "message", "") or "static assertion failed"
            self._emit(f'/* static_assert({cond}, "{msg}") */')
            self._emit(
                f"typedef char static_assert_{self._label_count} [(cond) ? 1 : -1];"
            )
            self._label_count += 1

        elif cls == "SafeStmt":
            body = getattr(node, "body", [])
            self._emit("{ /* safe block */")
            self.indent_level += 1
            for s in body:
                self._transpile_stmt(s)
            self.indent_level -= 1
            self._emit("}")

        elif cls == "BorrowStmt":
            target = getattr(node, "target", None)
            if target:
                t_name = target.name if hasattr(target, "name") else str(target)
                self._emit(f"/* borrow {t_name} - no-op in C */")

        elif cls == "ReleaseStmt":
            target = getattr(node, "target", None)
            if target:
                t_name = target.name if hasattr(target, "name") else str(target)
                self._emit(f"/* release {t_name} - no-op in C */")

        elif cls == "MoveStmt":
            target = getattr(node, "target", None)
            if target:
                t_name = target.name if hasattr(target, "name") else str(target)
                self._emit(f"/* move {t_name} - no-op in C */")

        elif cls == "ScopeResolution":
            namespace = getattr(node, "namespace", "")
            member = getattr(node, "member", "")
            self._emit(f"{namespace}_{member}")

        elif cls == "PointerDeref":
            ptr = self._transpile_expr(node.ptr)
            self._emit(f"(*({ptr}))")

        else:
            pass  # Unknown node type - silently ignore

    def _transpile_class(self, node):
        """Emit a C struct + constructor for a KentScript class."""
        cname = node.name
        methods = getattr(node, "methods", []) or []
        parent = getattr(node, "parent", None)
        decorators = getattr(node, "decorators", []) or []

        # [KS-OS-001] Check for packed decorator
        is_packed = "packed" in decorators

        # Collect all fields set in __init__ or __init__
        init_method = None
        other_methods = []
        for m in methods:
            if hasattr(m, "name") and (m.name == "__init__" or m.name == "init"):
                init_method = m
            else:
                other_methods.append(m)

        # Emit struct
        self._emit(f"/* class {cname}{' extends ' + parent if parent else ''} */")
        if is_packed:
            self._emit(f"typedef struct __attribute__((packed)) {{")
        else:
            self._emit(f"typedef struct {{")
        self._emit(f"    char* __class__;")
        # Inheritance: embed parent struct as first field for struct-embedding inheritance
        if parent and parent in self.class_names:
            self._emit(f"    {parent}_t __parent__;  /* inherited from {parent} */")
        # Emit some generic fields - use void* map approach
        self._emit(f"    void* __attrs__[64];")
        self._emit(f"    char* __attr_names__[64];")
        self._emit(f"    int __attr_is_str__[64];  /* 1=char*, 0=long long */")
        self._emit(f"    int __attr_count__;")
        self._emit(f"}} {cname}_t;")
        self._emit("")

        # Emit constructor
        params = []
        if init_method and hasattr(init_method, "params"):
            params = [p for p in init_method.params if p != "self"]

        _ctor_type_map = {
            "int": "long long",
            "i64": "long long",
            "i32": "long long",
            "float": "double",
            "f64": "double",
            "f32": "double",
            "double": "double",
            "string": "char*",
            "str": "char*",
            "bool": "long long",
        }
        _init_ptypes = (
            getattr(init_method, "param_types", {}) or {} if init_method else {}
        )

        def _ctor_param_type(p):
            kt = _init_ptypes.get(p)
            return _ctor_type_map.get(kt, "long long") if kt else "long long"

        param_str = (
            ", ".join(f"{_ctor_param_type(p)} {p}" for p in params)
            if params
            else "void"
        )
        self._emit(f"static {cname}_t* __new_{cname}__({param_str}) {{")
        self._emit(f"    {cname}_t* self = ({cname}_t*)malloc(sizeof({cname}_t));")
        self._emit(f'    self->__class__ = "{cname}";')
        self._emit(f"    self->__attr_count__ = 0;")
        self._emit(
            f"    memset(self->__attr_is_str__, 0, sizeof(self->__attr_is_str__));"
        )
        # Inheritance: call parent constructor to initialise parent fields
        if parent and parent in self.class_names:
            self._emit(f"    /* inherit from {parent} */")
            self._emit(f"    memset(&self->__parent__, 0, sizeof({parent}_t));")
            self._emit(f'    self->__parent__.__class__ = "{parent}";')

        # Parse __init__ body to set attributes
        if init_method and hasattr(init_method, "body"):
            attr_index = 0
            for stmt in init_method.body:
                if (
                    hasattr(stmt, "__class__")
                    and stmt.__class__.__name__ == "Assignment"
                    and hasattr(stmt, "target")
                    and hasattr(stmt.target, "__class__")
                    and stmt.target.__class__.__name__ == "MemberAccess"
                    and hasattr(stmt.target, "obj")
                    and hasattr(stmt.target.obj, "name")
                    and stmt.target.obj.name == "self"
                ):
                    attr_name = stmt.target.member
                    for i, p in enumerate(params):
                        if p == attr_name:
                            p_ctype = _ctor_param_type(p)
                            is_str = 1 if p_ctype == "char*" else 0
                            self._emit(
                                f'    self->__attr_names__[{attr_index}] = "{attr_name}";'
                            )
                            if is_str:
                                self._emit(
                                    f"    self->__attrs__[{attr_index}] = (void*){p};"
                                )
                            else:
                                self._emit(
                                    f"    self->__attrs__[{attr_index}] = (void*)(uintptr_t)(long long)({p});"
                                )
                            self._emit(
                                f"    self->__attr_is_str__[{attr_index}] = {is_str};"
                            )
                            self._emit(f"    self->__attr_count__ = {attr_index + 1};")
                            attr_index += 1
                            break

        self._emit(f"    return self;")
        self._emit(f"}}")
        self._emit("")

        # Emit method accessor helper (with parent fallback for inherited classes)
        self._emit(
            f"static char* __get_{cname}_attr__({cname}_t* self, const char* name) {{"
        )
        self._emit(f"    for (int i = 0; i < self->__attr_count__; i++) {{")
        self._emit(f"        if (strcmp(self->__attr_names__[i], name) == 0) {{")
        self._emit(
            f"            if (self->__attr_is_str__[i]) return (char*)self->__attrs__[i];"
        )
        self._emit(f"            /* numeric: convert to string */")
        self._emit(f"            static char _nb[64];")
        self._emit(
            f'            snprintf(_nb, sizeof(_nb), "%lld", (long long)(uintptr_t)self->__attrs__[i]);'
        )
        self._emit(f"            return _nb;")
        self._emit(f"        }}")
        self._emit(f"    }}")
        if parent and parent in self.class_names:
            self._emit(f"    return __get_{parent}_attr__(&self->__parent__, name);")
        else:
            self._emit(f'    return "";')
        self._emit(f"}}")
        self._emit("")

        # Emit numeric getter helper
        self._emit(
            f"static long long __get_{cname}_attr_num__({cname}_t* self, const char* name) {{"
        )
        self._emit(f"    for (int i = 0; i < self->__attr_count__; i++) {{")
        self._emit(f"        if (strcmp(self->__attr_names__[i], name) == 0) {{")
        self._emit(f"            return (long long)(uintptr_t)self->__attrs__[i];")
        self._emit(f"        }}")
        self._emit(f"    }}")
        self._emit(f"    return 0;")
        self._emit(f"}}")
        self._emit("")

        # Emit method setter helper
        self._emit(
            f"static void __set_{cname}_attr__({cname}_t* self, const char* name, long long value) {{"
        )
        self._emit(f"    for (int i = 0; i < self->__attr_count__; i++) {{")
        self._emit(f"        if (strcmp(self->__attr_names__[i], name) == 0) {{")
        self._emit(f"            self->__attrs__[i] = (void*)(uintptr_t)value;")
        self._emit(f"            self->__attr_is_str__[i] = 0;")
        self._emit(f"            return;")
        self._emit(f"        }}")
        self._emit(f"    }}")
        self._emit(f"    /* Add new attribute if not found */")
        self._emit(f"    if (self->__attr_count__ < 64) {{")
        self._emit(
            f"        self->__attr_names__[self->__attr_count__] = strdup(name);"
        )
        self._emit(
            f"        self->__attrs__[self->__attr_count__] = (void*)(uintptr_t)value;"
        )
        self._emit(f"        self->__attr_is_str__[self->__attr_count__] = 0;")
        self._emit(f"        self->__attr_count__++;")
        self._emit(f"    }}")
        self._emit(f"}}")
        self._emit("")

        # Emit other methods
        for m in other_methods:
            if hasattr(m, "name") and hasattr(m, "params"):
                mparams = [p for p in m.params if p != "self"]
                mparam_str = f"{cname}_t* self" + (
                    "".join(f", long long {p}" for p in mparams)
                )

                # Set context for return type detection
                old_context = self.current_class_context
                self.current_class_context = cname

                # Detect return type from method body
                return_type = "void"
                body = getattr(m, "body", []) or []
                for s in body:
                    if s.__class__.__name__ == "ReturnStmt" and s.value:
                        # Check if return value is a string
                        if self._is_string_node(s.value):
                            return_type = "char*"
                        else:
                            return_type = "long long"
                        break

                self.current_class_context = old_context
                self._in_method_body = True
                self._emit(
                    f"static {return_type} __method_{cname}_{m.name}__({mparam_str}) {{"
                )
                self.indent_level += 1
                # Set context for body transpilation
                self.current_class_context = cname
                # Try to transpile body
                for s in body:
                    self._transpile_stmt(s)
                self.indent_level -= 1
                self._emit(f"}}")
                self.current_class_context = None
                self._in_method_body = False
                self._emit("")

        # Register class constructor return type
        self.func_return_types["__new_" + cname + "__"] = cname + "_t*"
        # Track class name for constructor calls
        self.class_names.add(cname)
        # Track class instance types (for variable declarations)
        self.class_instance_types[cname] = cname + "_t*"

        # Inheritance: emit forwarding stubs for parent methods not overridden in child
        if parent and parent in self.class_names:
            self._emit(
                f"/* {cname} inherits from {parent} — parent attrs accessible via __parent__ field */"
            )
            self._emit("")

    def _emit_decl_or_assign(
        self, c_type, name, raw, is_let_decl=False, update_declared=True
    ):
        """Emit a variable declaration or assignment. For let statements, always emit a declaration."""
        if is_let_decl or name not in self.declared_vars:
            self._emit(f"{c_type} {name} = {raw};")
            if update_declared or name not in self.declared_vars:
                self.declared_vars[name] = c_type
        else:
            self._emit(f"{name} = {raw};")

    def _transpile_decl(self, node):
        """Handle let x = expr and x = expr (assignment)."""
        _kt_to_c = {
            "int": "long long",
            "i64": "long long",
            "i32": "long long",
            "float": "double",
            "f64": "double",
            "f32": "double",
            "double": "double",
            "string": "char*",
            "str": "char*",
            "bool": "long long",
        }
        cls = node.__class__.__name__
        is_let_decl = cls == "LetDecl"
        if is_let_decl:
            name = self._safe_c_name(node.name)  # Convert to safe C name
            name_orig = node.name  # Keep original for lookup
            val_node = node.value
            explicit_type = getattr(node, "type_hint", None)
        else:  # Assignment
            if hasattr(node.target, "name"):
                name = self._safe_c_name(node.target.name)
                name_orig = node.target.name
            elif node.target.__class__.__name__ == "IndexAccess":
                # arr[idx] = value OR io[port] = value OR msr[reg] = value OR dict[key] = value
                tgt = node.target
                obj = tgt.obj

                # Check for hardware access
                obj_name = None
                if hasattr(obj, "name"):
                    obj_name = obj.name

                # Also convert obj_name for IndexAccess
                obj_name = self._safe_c_name(obj_name) if obj_name else obj_name

                if obj_name == "io":
                    # Port I/O write
                    idx = self._transpile_expr(tgt.index)
                    rhs = self._transpile_expr(node.value)
                    self._emit(f"_ks_io_write({idx}, {rhs});")
                    return
                elif obj_name == "msr":
                    # MSR write
                    idx = self._transpile_expr(tgt.index)
                    rhs = self._transpile_expr(node.value)
                    self._emit(f"_ks_msr_write({idx}, {rhs});")
                    return

                # Check if this is a dictionary assignment
                elif obj_name and obj_name in self.declared_vars:
                    var_type = self.declared_vars[obj_name]
                    if var_type == "_ks_dict*":
                        # Dictionary assignment: _ks_dict_set(dict, key, value, is_string)
                        dict_obj = self._transpile_expr(obj)
                        key = self._transpile_expr(tgt.index)
                        value = self._transpile_expr(node.value)

                        # Determine if value is string and cast to long long if needed
                        if self._is_string_node(node.value):
                            value = f"(long long)(uintptr_t){value}"
                        is_str = "1" if self._is_string_node(node.value) else "0"

                        self._emit(
                            f"_ks_dict_set({dict_obj}, {key}, {value}, {is_str});"
                        )
                        return

                # Normal array assignment
                arr = self._transpile_expr(obj)
                idx = self._transpile_expr(tgt.index)
                rhs = self._transpile_expr(node.value)
                self._emit(f"({arr})[{idx}] = {rhs};")
                return
            elif node.target.__class__.__name__ == "MemberAccess":
                # self.attr = value or obj.attr = value
                tgt = node.target
                obj = tgt.obj
                member = tgt.member
                rhs = self._transpile_expr(node.value)

                # Check if this is a class instance attribute
                if hasattr(obj, "name") and obj.name in self.class_names:
                    # Class instance attribute: call setter or use __attrs__ array
                    class_name = obj.name
                    # For class instances passed as parameters, use __set_attr__ helper
                    if hasattr(tgt, "_is_self") or (
                        getattr(self, "_in_method_body", False)
                        and self.current_class_context
                    ):
                        # Inside a method, use the self pointer
                        self._emit(
                            f'__set_{class_name}_attr__(self, "{member}", {rhs});'
                        )
                    else:
                        # Store in a temporary and use the setter
                        obj_c = self._transpile_expr(obj)
                        self._emit(
                            f'__set_{class_name}_attr__({obj_c}, "{member}", {rhs});'
                        )
                    return
                elif (
                    hasattr(obj, "name")
                    and obj.name == "self"
                    and self.current_class_context
                ):
                    # Inside a method with self.attr = value
                    class_name = self.current_class_context
                    self._emit(f'__set_{class_name}_attr__(self, "{member}", {rhs});')
                    return
                else:
                    # For non-class MemberAccess, emit as pointer dereference or ignore
                    obj_c = self._transpile_expr(obj)
                    self._emit(f"/* member access: {obj_c}.{member} = {rhs} */")
                    return
            else:
                return  # complex LHS — skip
            val_node = node.value
            explicit_type = None

        # Special case: UnaryOp borrow/move — check if source is a pointer type
        if val_node.__class__.__name__ == "UnaryOp" and val_node.op in (
            "borrow",
            "move",
            "borrow_mut",
        ):
            src_node = val_node.operand
            src_name = (
                src_node.name if src_node.__class__.__name__ == "Identifier" else None
            )
            if src_name and src_name in self.declared_vars:
                src_type = self.declared_vars[src_name]
                # ks_array, char*, and pointer types work with borrow
                if src_type in ("ks_array", "char*", "long long*", "double*", "char**"):
                    # Source is array/pointer — borrow keeps same pointer type
                    if name not in self.declared_vars:
                        self._emit(f"{src_type} {name} = {src_name};")
                        self.declared_vars[name] = src_type
                    else:
                        self._emit(f"{name} = {src_name};")
                    if src_type == "char*":
                        self.string_vars.add(name)
                    else:
                        self.numeric_vars.add(name)
                    return

        # Special case: ListLiteral — emit as a static C array
        if val_node.__class__.__name__ == "ListLiteral":
            elems = val_node.elements if hasattr(val_node, "elements") else []
            # Check if all elements are literals with a value (numeric or hex string)
            all_have_value = all(hasattr(e, "value") for e in elems)
            if elems and all_have_value:
                # Check if elements are strings
                all_strings = all(
                    isinstance(getattr(e, "value", None), str) for e in elems
                )
                if all_strings:
                    vals = ", ".join(f'(long long)"{e.value}"' for e in elems)
                else:
                    vals = ", ".join(str(e.value) for e in elems)
                # Create a static array to hold the data
                arr_name = f"_arr_{name}"
                self._emit(f"static long long {arr_name}[] = {{{vals}}};")
                # Create ks_array struct
                self._emit(
                    f"ks_array {name} = {{ .data = {arr_name}, .length = {len(elems)} }};"
                )
                self.declared_vars[name] = "ks_array"
            else:
                # Empty or mixed list — use ks_array
                self._emit(f"ks_array {name} = {{ .data = NULL, .length = 0 }};")
                self.declared_vars[name] = "ks_array"
            return

        # Special case: FunctionDef as value (anonymous func / lambda assigned to var)
        if val_node.__class__.__name__ == "FunctionDef":
            # If already emitted as a closure lambda, just reference it
            resolved = getattr(val_node, "_resolved_anon_name", None)
            if resolved:
                param_count = len(val_node.params or [])
                params_sig = ", ".join(["long long"] * param_count)
                if name not in self.declared_vars:
                    self._emit(
                        f"long long (*{name})({params_sig}) = (long long(*)({params_sig})){resolved};"
                    )
                    self.declared_vars[name] = f"long long (*)({params_sig})"
                else:
                    self._emit(f"{name} = (long long(*)({params_sig})){resolved};")
                # Point closure env to outer vars by address (by-reference capture)
                fn_params = [p for p in (val_node.params or []) if p != "self"]
                free_vars = self._collect_free_vars(val_node.body or [], fn_params)
                if free_vars:
                    for vn, vt in free_vars:
                        self._emit(f"{resolved}_env.{vn} = &{vn};")
                return
            func_name = (
                val_node.name
                if val_node.name and not val_node.name.startswith("__lambda_")
                else f"_ks_fn_{name}"
            )
            val_node.name = func_name
            self._transpile_function(val_node)
            param_count = len(val_node.params)
            params_sig = ", ".join(["long long"] * param_count)
            if name not in self.declared_vars:
                self._emit(f"long long (*{name})({params_sig}) = {func_name};")
                self.declared_vars[name] = f"long long (*)({params_sig})"
            else:
                self._emit(f"{name} = {func_name};")
            return

        # Special case: MatchStmt as value — emit match block writing into a temp then assign
        if val_node.__class__.__name__ == "MatchStmt":
            tmp = f"_match_result_{self._label_count}"
            self._label_count += 1
            if name not in self.declared_vars:
                self._emit(f"char* {name} = NULL;")
                self.declared_vars[name] = "char*"
                self.string_vars.add(name)
            self._emit(f"char* {tmp} = NULL;")
            match_val = self._transpile_expr(val_node.expr)
            self._emit(f"{{ long long _mv = {match_val};")
            self.indent_level += 1
            cases = val_node.cases if hasattr(val_node, "cases") else []
            first = True
            for case in cases:
                pattern = case.pattern if hasattr(case, "pattern") else case[0]
                body = case.body if hasattr(case, "body") else case[1]
                is_wildcard = pattern == "_" or (
                    hasattr(pattern, "name") and pattern.name == "_"
                )
                body_expr = (
                    body[0]
                    if isinstance(body, list) and len(body) == 1
                    else (body if not isinstance(body, list) else None)
                )
                result_c = self._transpile_expr(body_expr) if body_expr else "NULL"
                if is_wildcard:
                    kw = "else {" if not first else "{"
                    self._emit(kw)
                else:
                    pv = self._transpile_expr(pattern)
                    kw = (
                        f"if (_mv == {pv}) {{"
                        if first
                        else f"}} else if (_mv == {pv}) {{"
                    )
                    self._emit(kw)
                    first = False
                self.indent_level += 1
                self._emit(f"{tmp} = {result_c};")
                self.indent_level -= 1
            if not first:
                self._emit("}")
            self.indent_level -= 1
            self._emit("}")
            self._emit(f"{name} = {tmp};")
            return

        raw = self._transpile_expr(val_node)

        # Special case: Check if value is a class constructor call
        # Check if value is a class constructor call (ClassName(...) or ClassName.new(...))
        _ctor_class = None
        if val_node.__class__.__name__ == "FunctionCall":
            fn = val_node.func
            if fn.__class__.__name__ == "Identifier" and fn.name in self.class_names:
                _ctor_class = fn.name
            elif (
                fn.__class__.__name__ == "MemberAccess"
                and hasattr(fn, "obj")
                and hasattr(fn.obj, "name")
                and fn.obj.name in self.class_names
                and getattr(fn, "member", None) == "new"
            ):
                _ctor_class = fn.obj.name
        is_class_ctor = _ctor_class is not None

        if is_class_ctor:
            ctype = self.class_instance_types.get(_ctor_class, f"{_ctor_class}_t*")
            if name not in self.declared_vars:
                self._emit(f"{ctype} {name} = {raw};")
                self.declared_vars[name] = ctype
            else:
                self._emit(f"{name} = {raw};")
            return

        # Special case: Check if value is a string-returning system function
        string_funcs = (
            "system_os_getenv",
            "system_file_readlink",
            "system_strings_join",
            "system_strings_split",
            "system_socket_recv",
        )
        is_string_call = (
            val_node.__class__.__name__ == "FunctionCall"
            and hasattr(val_node.func, "name")
            and val_node.func.name in string_funcs
        )

        if is_string_call:
            if is_let_decl or name not in self.declared_vars:
                self._emit(f"char* {name} = {raw};")
                self.declared_vars[name] = "char*"
            else:
                self._emit(f"{name} = {raw};")
            return

        # Special case: address-of operator (&) returns pointer
        if val_node.__class__.__name__ == "UnaryOp" and val_node.op == "&":
            if name not in self.declared_vars:
                self._emit(f"void* {name} = {raw};")
                self.declared_vars[name] = "void*"
            else:
                self._emit(f"{name} = {raw};")
            self.numeric_vars.add(name)
            return

        # Special case: dereference operator (*) returns value
        if (
            val_node.__class__.__name__ == "UnaryOp" and val_node.op == "*"
        ) or val_node.__class__.__name__ == "PointerDeref":
            if name not in self.declared_vars:
                self._emit(f"long long {name} = {raw};")
                self.declared_vars[name] = "long long"
            else:
                self._emit(f"{name} = {raw};")
            self.numeric_vars.add(name)
            return

        # Special case: syscall() returns long
        if val_node.__class__.__name__ == "FunctionCall":
            func_name = None
            is_module_call = False
            module_name = None
            method_name = None

            if hasattr(val_node, "func"):
                if hasattr(val_node.func, "name"):
                    func_name = val_node.func.name
                    # IMMEDIATE CHECK: if we know return type, use it
                    if func_name in self.func_return_types:
                        ret_type = self.func_return_types[func_name]
                        if is_let_decl or name not in self.declared_vars:
                            self._emit(f"{ret_type} {name} = {raw};")
                            self.declared_vars[name] = ret_type
                            if ret_type == "char*":
                                self.string_vars.add(name)
                        else:
                            self._emit(f"{name} = {raw};")
                        return
                elif val_node.func.__class__.__name__ == "MemberAccess":
                    is_module_call = True
                    if hasattr(val_node.func, "obj") and hasattr(
                        val_node.func.obj, "name"
                    ):
                        module_name = val_node.func.obj.name
                        # Check if it's a ClassName.new(...) call
                        if (
                            module_name in self.class_names
                            and getattr(val_node.func, "member", None) == "new"
                        ):
                            ctype = self.class_instance_types.get(
                                module_name, f"{module_name}_t*"
                            )
                            raw = self._transpile_expr(val_node)
                            if is_let_decl or name not in self.declared_vars:
                                self._emit(f"{ctype} {name} = {raw};")
                                self.declared_vars[name] = ctype
                            else:
                                self._emit(f"{name} = {raw};")
                            return
                    if hasattr(val_node.func, "member"):
                        method_name = val_node.func.member

            # Functions that return numeric types (not strings)
            numeric_funcs = {
                "syscall",
                "system_syscall",
                "malloc",
                "ptr_read",
                "ptr_cast",
                "ptr_deref",
                "atomic_load",
                "atomic_add",
                "atomic_cas",
                "volatile_read",
                "mmio_read",
                "read_port",
                "rdtsc",
                "rdmsr",
                "int",
                "len",
                "ord",
                "clock_ms",
                "inject_shellcode",
                "execute_shellcode",
            }

            # Functions that return pointers
            pointer_funcs = {"malloc", "ptr_cast", "alloc"}

            # Functions that return arrays
            array_funcs = {
                "generate_reverse_shell",
                "create_bind_shell",
                "arbitrary_read",
            }

            # Check if it's a module call that returns a pointer
            if is_module_call and module_name == "baremetal" and method_name == "alloc":
                c_type = "void*"
                if is_let_decl or name not in self.declared_vars:
                    self._emit(f"{c_type} {name} = {raw};")
                    self.declared_vars[name] = c_type
                else:
                    self._emit(f"{name} = {raw};")
                return

            # Handle module function calls (baremetal.xxx, hardware.xxx, etc.)
            if is_module_call:
                # Modules that return struct-like objects (accessed via .member)
                _struct_return_modules = {
                    "subprocess": {"run", "popen"},
                    "fileio": {"open", "stat"},
                    "os": {"stat", "lstat"},
                    "pathlib": {"Path"},
                    "http": {"get", "post"},
                }
                _struct_methods = _struct_return_modules.get(module_name, set())
                if method_name in _struct_methods:
                    c_type = "_ks_http_response_t"
                elif module_name == "baremetal" and method_name in ("alloc",):
                    c_type = "void*"
                elif module_name == "time" and method_name in (
                    "time",
                    "monotonic_ms",
                    "monotonic",
                ):
                    c_type = "double"
                else:
                    c_type = "long long"

                if is_let_decl or name not in self.declared_vars:
                    self._emit(f"{c_type} {name} = {raw};")
                    self.declared_vars[name] = c_type
                else:
                    self._emit(f"{name} = {raw};")
                if c_type != "void*":
                    self.numeric_vars.add(name)
                return

            if func_name in numeric_funcs:
                if func_name in pointer_funcs:
                    c_type = "void*"
                else:
                    c_type = "long long"

                if name not in self.declared_vars:
                    self._emit(f"{c_type} {name} = {raw};")
                    self.declared_vars[name] = c_type
                else:
                    self._emit(f"{name} = {raw};")
                self.numeric_vars.add(name)
                return
            elif func_name in array_funcs or (
                func_name in self.func_return_types
                and self.func_return_types[func_name] == "ks_array"
            ):
                # Function returns array
                if is_let_decl or name not in self.declared_vars:
                    self._emit(f"ks_array {name} = {raw};")
                    self.declared_vars[name] = "ks_array"
                else:
                    self._emit(f"{name} = {raw};")
                self.numeric_vars.add(name)
                return
            # Always declare the variable (even if name exists from params)
            # This is because function params shouldn't shadow local declarations
            # For LetDecl, always emit a new declaration (to support shadowing in nested scopes)
            if is_let_decl or name not in self.declared_vars:
                self._emit(f"long long {name} = {raw};")
                self.declared_vars[name] = "long long"
            else:
                self._emit(f"{name} = {raw};")
            self.numeric_vars.add(name)
            return

        # Special case: ptr() returns void*
        if (
            val_node.__class__.__name__ == "FunctionCall"
            and hasattr(val_node.func, "name")
            and val_node.func.name == "ptr"
        ):
            if name not in self.declared_vars:
                self._emit(f"void* {name} = {raw};")
                self.declared_vars[name] = "void*"
            else:
                self._emit(f"{name} = {raw};")
            self.numeric_vars.add(name)
            return

        # Special case: list comprehension — emit as ks_array built by a loop
        if val_node.__class__.__name__ == "ListComprehension":
            lc = val_node
            tmp = f"_lc_{name}_{self._label_count}"
            self._label_count += 1
            iter_expr = self._transpile_expr(lc.iterable)
            loop_var = lc.var
            # Declare result array
            self._emit(f"ks_array {name} = {{NULL, 0}};")
            self.declared_vars[name] = "ks_array"
            # Determine iteration: ks_array or range
            iter_node = lc.iterable
            iter_cls = iter_node.__class__.__name__
            if (
                iter_cls == "FunctionCall"
                and getattr(iter_node, "func", None)
                and getattr(iter_node.func, "name", "") == "range"
            ):
                # range(start, stop) or range(stop)
                rargs = iter_node.args
                if len(rargs) == 1:
                    start_c, stop_c = "0", self._transpile_expr(rargs[0])
                else:
                    start_c, stop_c = (
                        self._transpile_expr(rargs[0]),
                        self._transpile_expr(rargs[1]),
                    )
                self._emit(
                    f"for (long long {loop_var} = {start_c}; {loop_var} < {stop_c}; {loop_var}++) {{"
                )
            elif (
                iter_cls == "Identifier"
                and iter_expr in self.declared_vars
                and self.declared_vars[iter_expr] == "ks_array"
            ):
                self._emit(
                    f"for (long long _i_{tmp} = 0; _i_{tmp} < {iter_expr}.length; _i_{tmp}++) {{"
                )
                self._emit(f"    long long {loop_var} = {iter_expr}.data[_i_{tmp}];")
            else:
                # Assume ks_array
                self._emit(
                    f"for (long long _i_{tmp} = 0; _i_{tmp} < {iter_expr}.length; _i_{tmp}++) {{"
                )
                self._emit(f"    long long {loop_var} = {iter_expr}.data[_i_{tmp}];")
            # Condition filter
            if lc.condition:
                cond_c = self._transpile_expr(lc.condition)
                self._emit(f"    if ({cond_c}) {{")
            elem_c = self._transpile_expr(lc.expr)
            # Handle string elements properly - cast to void* instead of long long
            if self._is_string_node(lc.expr):
                self._emit(f"    _ks_array_append(&{name}, (void*)(char*){elem_c});")
            else:
                self._emit(f"    _ks_array_append(&{name}, (long long)({elem_c}));")
            if lc.condition:
                self._emit("    }")
            self._emit("}")
            return

        # Special case: struct literal
        if val_node.__class__.__name__ == "StructLiteral":
            struct_type = val_node.name
            # If this is a known class name, use the _t* pointer type and constructor
            if struct_type in self.class_names:
                ctype = self.class_instance_types.get(struct_type, f"{struct_type}_t*")
                ctor = f"__new_{struct_type}__()"
                if name not in self.declared_vars:
                    self._emit(f"{ctype} {name} = {ctor};")
                    self.declared_vars[name] = ctype
                else:
                    self._emit(f"{name} = {ctor};")
                return
            if name not in self.declared_vars:
                self._emit(f"{struct_type} {name} = {raw};")
                self.declared_vars[name] = struct_type
            else:
                self._emit(f"{name} = {raw};")
            return

        # Special case: FunctionDef as value (anonymous func / lambda assigned to var)
        if val_node.__class__.__name__ == "FunctionDef":
            # If already emitted as a closure lambda, just reference it
            resolved = getattr(val_node, "_resolved_anon_name", None)
            if resolved:
                param_count = len(val_node.params or [])
                params_sig = ", ".join(["long long"] * param_count)
                if name not in self.declared_vars:
                    self._emit(
                        f"long long (*{name})({params_sig}) = (long long(*)({params_sig})){resolved};"
                    )
                    self.declared_vars[name] = f"long long (*)({params_sig})"
                else:
                    self._emit(f"{name} = (long long(*)({params_sig})){resolved};")
                # Point closure env to outer vars by address (by-reference capture)
                fn_params = [p for p in (val_node.params or []) if p != "self"]
                free_vars = self._collect_free_vars(val_node.body or [], fn_params)
                if free_vars:
                    for vn, vt in free_vars:
                        self._emit(f"{resolved}_env.{vn} = &{vn};")
                return
            func_name = (
                val_node.name
                if val_node.name and not val_node.name.startswith("__lambda_")
                else f"_ks_fn_{name}"
            )
            val_node.name = func_name
            self._transpile_function(val_node)
            param_count = len(val_node.params)
            params_sig = ", ".join(["long long"] * param_count)
            if name not in self.declared_vars:
                self._emit(f"long long (*{name})({params_sig}) = {func_name};")
                self.declared_vars[name] = f"long long (*)({params_sig})"
            else:
                self._emit(f"{name} = {func_name};")
            return

        # Special case: MatchStmt as value — emit match block writing into a temp then assign
        if val_node.__class__.__name__ == "MatchStmt":
            tmp = f"_match_result_{self._label_count}"
            self._label_count += 1
            if name not in self.declared_vars:
                self._emit(f"char* {name} = NULL;")
                self.declared_vars[name] = "char*"
                self.string_vars.add(name)
            self._emit(f"char* {tmp} = NULL;")
            match_val = self._transpile_expr(val_node.expr)
            self._emit(f"{{ long long _mv = {match_val};")
            self.indent_level += 1
            cases = val_node.cases if hasattr(val_node, "cases") else []
            first = True
            for case in cases:
                pattern = case.pattern if hasattr(case, "pattern") else case[0]
                body = case.body if hasattr(case, "body") else case[1]
                is_wildcard = pattern == "_" or (
                    hasattr(pattern, "name") and pattern.name == "_"
                )
                # body is either a list of stmts or a single expr
                body_expr = None
                if isinstance(body, list) and len(body) == 1:
                    body_expr = body[0]
                elif not isinstance(body, list):
                    body_expr = body
                result_c = (
                    self._transpile_expr(body_expr)
                    if body_expr and body_expr.__class__.__name__ != "list"
                    else "NULL"
                )
                if is_wildcard:
                    kw = "else {" if not first else "{"
                    self._emit(kw)
                else:
                    pv = self._transpile_expr(pattern)
                    kw = (
                        f"if (_mv == {pv}) {{"
                        if first
                        else f"}} else if (_mv == {pv}) {{"
                    )
                    self._emit(kw)
                    first = False
                self.indent_level += 1
                self._emit(f"{tmp} = {result_c};")
                self.indent_level -= 1
            if not first:
                self._emit("}")
            self.indent_level -= 1
            self._emit("}")
            self._emit(f"{name} = {tmp};")
            return

        # Special case: Lambda expression - function pointer
        if val_node.__class__.__name__ == "LambdaExpr":
            param_count = len(val_node.params)
            params_sig = ", ".join(["long long"] * param_count)
            if name not in self.declared_vars:
                self._emit(f"long long (*{name})({params_sig}) = {raw};")
                self.declared_vars[name] = f"long long (*)({params_sig})"
            else:
                self._emit(f"{name} = {raw};")
            return

        # Special case: borrow <var> — reference to source variable
        # If source is a known array/pointer, declare as pointer too
        if val_node.__class__.__name__ == "BorrowStmt":
            src = val_node.var
            if src in self.declared_vars and self.declared_vars[src] in (
                "long long*",
                "char**",
            ):
                c_type = self.declared_vars[src]
                if name not in self.declared_vars:
                    self._emit(f"{c_type} {name} = {raw};")
                    self.declared_vars[name] = c_type
                else:
                    self._emit(f"{name} = {raw};")
            else:
                # Borrow of a scalar or unknown — emit as long long alias
                if name not in self.declared_vars:
                    self._emit(f"long long {name} = {raw};")
                    self.declared_vars[name] = "long long"
                else:
                    self._emit(f"{name} = {raw};")
            self.numeric_vars.add(name)
            return

        # Special case: move <var> to <name>
        if val_node.__class__.__name__ == "MoveStmt":
            src = val_node.var
            if src in self.declared_vars:
                c_type = self.declared_vars[src]
                if name not in self.declared_vars:
                    self._emit(f"{c_type} {name} = {src};")
                    self.declared_vars[name] = c_type
                else:
                    self._emit(f"{name} = {src};")
                if c_type == "char*":
                    self.string_vars.add(name)
                else:
                    self.numeric_vars.add(name)
            else:
                if name not in self.declared_vars:
                    self._emit(f"long long {name} = {src};")
                    self.declared_vars[name] = "long long"
                    self.numeric_vars.add(name)
                else:
                    self._emit(f"{name} = {src};")
            return

        # Special case: alloc_i64 -> long long* array
        if (
            val_node.__class__.__name__ == "FunctionCall"
            and val_node.func.__class__.__name__ == "Identifier"
            and val_node.func.name == "alloc_i64"
        ):
            if name not in self.declared_vars:
                self._emit(f"long long* {name} = {raw};")
                self.declared_vars[name] = "long long*"
            else:
                self._emit(f"{name} = {raw};")
            self.numeric_vars.add(name)
            return

        # Special case: malloc/alloc -> void*
        if (
            val_node.__class__.__name__ == "FunctionCall"
            and val_node.func.__class__.__name__ == "Identifier"
            and val_node.func.name in ("malloc", "alloc", "calloc", "realloc")
        ):
            if name not in self.declared_vars:
                self._emit(f"void* {name} = {raw};")
                self.declared_vars[name] = "void*"
            else:
                self._emit(f"{name} = {raw};")
            self.numeric_vars.add(name)
            return

        # If explicit type hint present, use it directly
        if explicit_type:
            # Map explicit type to C type
            c_type = _kt_to_c.get(explicit_type, explicit_type)
            volatile = "volatile " if self.benchmark_mode else ""
            if c_type == "char*" or explicit_type in ("str", "string"):
                self.string_vars.add(name)
                self.numeric_vars.discard(name)
                str_val = self._to_string_expr(val_node, raw)
                if name not in self.declared_vars:
                    self._emit(f"char* {name} = {str_val};")
                    self.declared_vars[name] = "char*"
                else:
                    self._emit(f"{name} = {str_val};")
            elif explicit_type in ("bool", "BOOL"):
                # Track as bool
                self.bool_vars.add(name)
                self.numeric_vars.add(name)
                self.string_vars.discard(name)
                if name not in self.declared_vars:
                    self._emit(f"{volatile}long long {name} = ({raw});")
                    self.declared_vars[name] = "long long"
                else:
                    self._emit(f"{name} = ({raw});")
            elif c_type in _kt_to_c.values():
                self.numeric_vars.add(name)
                self.string_vars.discard(name)
                if name not in self.declared_vars:
                    self._emit(f"{volatile}{c_type} {name} = ({c_type})({raw});")
                    self.declared_vars[name] = c_type
                else:
                    self._emit(f"{name} = ({c_type})({raw});")
            else:
                # Unknown type, just emit as long long
                self.numeric_vars.add(name)
                if name not in self.declared_vars:
                    self._emit(f"{volatile}long long {name} = ({raw});")
                    self.declared_vars[name] = "long long"
                else:
                    self._emit(f"{name} = ({raw});")
            return

        # Determine if this is a numeric or string assignment
        is_numeric = self._is_numeric_operation(val_node)
        is_string = self._is_string_node(val_node)
        is_dict = val_node.__class__.__name__ == "DictLiteral"

        # Check if it's a function call that returns a numeric value
        if val_node.__class__.__name__ == "FunctionCall" and hasattr(
            val_node.func, "name"
        ):
            func_name = val_node.func.name
            # Functions that return integers/booleans
            if func_name in ("len", "ord", "contains", "int"):
                is_numeric = True
                is_string = False
            # Functions that return strings
            elif func_name in ("chr", "str", "_ks_concat"):
                is_string = True
                is_numeric = False

        # Detect if the value is or involves a double (float literal, double func call)
        def _is_double_value(n):
            c = n.__class__.__name__
            if c == "Literal" and isinstance(getattr(n, "value", None), float):
                return True
            if (
                c == "FunctionCall"
                and hasattr(n.func, "name")
                and n.func.name in self.func_return_types
            ):
                return self.func_return_types[n.func.name] == "double"
            if c == "FunctionCall" and n.func.__class__.__name__ == "MemberAccess":
                member = n.func.member
                if member in ("monotonic_ms", "monotonic", "time"):
                    return True
            if c == "BinaryOp":
                return _is_double_value(n.left) or _is_double_value(n.right)
            if c == "Identifier" and n.name in self.declared_vars:
                return self.declared_vars[n.name] == "double"
            return False

        is_double = _is_double_value(val_node)

        # Track the variable type
        if is_numeric or is_double:
            self.numeric_vars.add(name)
            if name in self.string_vars:
                self.string_vars.discard(name)
            volatile = "volatile " if self.benchmark_mode else ""

            # Check for explicit type hint
            if explicit_type:
                if explicit_type == "ptr":
                    c_type = "long long*"
                elif explicit_type in ("i8", "u8"):
                    c_type = "char"
                elif explicit_type in ("i16", "u16"):
                    c_type = "short"
                elif explicit_type in ("i32", "u32"):
                    c_type = "int"
                elif explicit_type in ("i64", "u64", "int", "uint"):
                    c_type = "long long"
                elif explicit_type in ("f32"):
                    c_type = "float"
                elif explicit_type in ("f64", "float"):
                    c_type = "double"
                elif explicit_type == "str":
                    c_type = "char*"
                else:
                    c_type = explicit_type  # Custom type
            elif is_double:
                c_type = "double"
            else:
                c_type = "long long"

            if name not in self.declared_vars:
                self._emit(f"{volatile}{c_type} {name} = {raw};")
                self.declared_vars[name] = c_type
            else:
                self._emit(f"{name} = {raw};")
        elif is_dict:
            if name not in self.declared_vars:
                self._emit(f"_ks_dict* {name} = {raw};")
                self.declared_vars[name] = "_ks_dict*"
            else:
                self._emit(f"{name} = {raw};")
        elif is_string:
            self.string_vars.add(name)
            if name in self.numeric_vars:
                self.numeric_vars.discard(name)
            str_val = self._to_string_expr(val_node, raw)
            if name not in self.declared_vars:
                self._emit(f"char* {name} = {str_val};")
                self.declared_vars[name] = "char*"
            else:
                self._emit(f"{name} = {str_val};")
        else:
            # Default to numeric if unclear
            self.numeric_vars.add(name)
            if name in self.string_vars:
                self.string_vars.discard(name)
            volatile = "volatile " if self.benchmark_mode else ""

            # Last check: if value is a function call, check return type
            if val_node and val_node.__class__.__name__ == "FunctionCall":
                if hasattr(val_node, "func") and hasattr(val_node.func, "name"):
                    fname = val_node.func.name
                    if fname in self.func_return_types:
                        ret_type = self.func_return_types[fname]
                        if name not in self.declared_vars:
                            self._emit(f"{ret_type} {name} = {raw};")
                            self.declared_vars[name] = ret_type
                        else:
                            self._emit(f"{name} = {raw};")
                        return

            if name not in self.declared_vars:
                self._emit(f"{volatile}long long {name} = {raw};")
                self.declared_vars[name] = "long long"
            else:
                self._emit(f"{name} = {raw};")

    def _transpile_call_stmt(self, node):
        """Emit a function call as a statement."""
        if node.func.__class__.__name__ == "Identifier":
            fname = node.func.name
            if fname == "print":
                self._transpile_print(node.args)
                return
            # Handle low-level functions that need special treatment
            if fname == "free" and node.args:
                ptr_expr = self._transpile_expr(node.args[0])
                self._emit(f"free((void*){ptr_expr});")
                return
            if fname == "write_word" and len(node.args) >= 4:
                ptr_expr = f"(void*){self._transpile_expr(node.args[0])}"
                rest_args = ", ".join(self._transpile_expr(a) for a in node.args[1:])
                self._emit(f"write_word({ptr_expr}, {rest_args});")
                return
            if fname == "write_byte" and len(node.args) >= 3:
                ptr_expr = f"(void*){self._transpile_expr(node.args[0])}"
                rest_args = ", ".join(self._transpile_expr(a) for a in node.args[1:])
                self._emit(f"write_byte({ptr_expr}, {rest_args});")
                return
            if fname == "memcpy" and len(node.args) >= 5:
                dest = f"(void*){self._transpile_expr(node.args[0])}"
                d_off = self._transpile_expr(node.args[1])
                src = f"(void*){self._transpile_expr(node.args[2])}"
                s_off = self._transpile_expr(node.args[3])
                size = self._transpile_expr(node.args[4])
                self._emit(
                    f"memcpy((char*){dest}+{d_off}, (char*){src}+{s_off}, {size});"
                )
                return
            if fname == "memset" and len(node.args) >= 4:
                ptr = f"(void*){self._transpile_expr(node.args[0])}"
                offset = self._transpile_expr(node.args[1])
                value = self._transpile_expr(node.args[2])
                size = self._transpile_expr(node.args[3])
                self._emit(f"memset((char*){ptr}+{offset}, {value}, {size});")
                return
        # Generic call
        expr = self._transpile_expr(node)
        self._emit(f"{expr};")

    def _get_expr_type(self, node):
        """Get the type of an expression: 'int', 'double', 'string', or 'unknown'."""
        cls = node.__class__.__name__

        if cls == "Literal":
            v = getattr(node, "value", None)
            if isinstance(v, bool):
                return "int"
            if isinstance(v, int):
                return "int"
            if isinstance(v, float):
                return "double"
            if isinstance(v, str):
                return "string"

        if cls == "Identifier":
            name = getattr(node, "name", None)
            if name in self.declared_vars:
                vtype = self.declared_vars[name]
                if vtype in ("int", "long", "long long", "int64_t", "int32_t"):
                    return "int"
                if vtype in ("double", "float"):
                    return "double"
                if vtype in ("char*", "string"):
                    return "string"
                if vtype in ("ks_array",):
                    return "array"
            # Unknown variable - default to int (most common)
            return "int"

        if cls == "BinaryOp":
            left_type = self._get_expr_type(node.left)
            right_type = self._get_expr_type(node.right)
            # String concatenation (+ on strings) returns string
            if left_type == "string" or right_type == "string":
                return "string"
            if left_type == "double" or right_type == "double":
                return "double"
            return "int"

        if cls == "FunctionCall":
            fn = getattr(node, "func", None)
            if fn and hasattr(fn, "name"):
                ret_type = self.func_return_types.get(fn.name)
                if ret_type:
                    if ret_type in ("double", "float"):
                        return "double"
                    if ret_type in ("int", "long", "long long"):
                        return "int"
                    if ret_type in ("char*", "string"):
                        return "string"

        if cls == "MemberAccess":
            # Class instance attribute access → __get_X_attr__ returns char*
            obj_name = getattr(node.obj, "name", None)
            if obj_name and obj_name in self.declared_vars:
                vtype = self.declared_vars[obj_name]
                if "_t*" in vtype:
                    return "string"  # getter always returns char*
            # .length is always int
            if node.member == "length":
                return "int"

        if cls == "AsyncAwait":
            return self._get_expr_type(node.expr)

        # Unknown - default to int for print
        return "int"

    def _transpile_print(self, args):
        """Emit printf for a KentScript print() call."""
        if not args:
            self._emit('printf("\\n");')
            return

        # Build format string and arguments based on actual types
        fmt_parts = []
        expr_parts = []
        for arg in args:
            c_expr = self._transpile_expr(arg)
            typ = self._get_expr_type(arg)
            if typ == "int":
                fmt_parts.append("%lld")
                expr_parts.append(f"(long long){c_expr}")
            elif typ == "double":
                fmt_parts.append("%g")
                expr_parts.append(f"(double){c_expr}")
            elif typ == "string":
                fmt_parts.append("%s")
                expr_parts.append(c_expr)
            elif typ == "array":
                # Arrays - just print the raw value (aggregate)
                # Use a simpler approach - just print as pointer
                fmt_parts.append("%s")
                expr_parts.append(f"\"[array]\"")
            else:
                # Default: treat as string
                fmt_parts.append("%s")
                expr_parts.append(c_expr)

        fmt = "".join(fmt_parts) + "\\n"
        exprs = ", ".join(expr_parts)
        self._emit(f'printf("{fmt}", {exprs});')

    # ------------------------------------------------------------------ expressions

    def _transpile_expr(self, node):
        """
        Transpile an expression to a C expression string.
        Returns a C expression that may be string, int, or double.
        """
        cls = node.__class__.__name__

        if cls == "LambdaExpr":
            # Find the lambda ID from pre-collected list
            for i, (func_name, _, body_node, _) in enumerate(self._lambda_funcs):
                if body_node is node.body:
                    return f"&{func_name}"
            # Fallback (shouldn't happen if collection worked)
            return "&_ks_lambda_unknown"

        if cls == "FunctionDef":
            # Anonymous function used as expression (e.g. returned from a function)
            # Use pre-resolved name if available (set during _collect_lambdas_from_node)
            if hasattr(node, "_resolved_anon_name"):
                return node._resolved_anon_name
            # Fallback: assign a new name and register
            anon_id = len(self._lambda_funcs)
            func_name = getattr(node, "name", None) or f"_ks_anon_{anon_id}"
            if not func_name or func_name.startswith("__lambda_"):
                func_name = f"_ks_anon_{anon_id}"
            params = [p for p in (node.params or []) if p != "self"]
            params_str = ", ".join(f"long long {p}" for p in params)
            self._lambda_funcs.append((func_name, params_str, node, len(params)))
            node._resolved_anon_name = func_name
            return func_name

        if cls == "Literal":
            v = node.value
            if v is None:
                return "0"
            if isinstance(v, bool):
                return "1" if v else "0"
            if isinstance(v, int):
                return str(v)
            if isinstance(v, float):
                return repr(v)
            if isinstance(v, str):
                if v.startswith("0x") or v.startswith("0X"):
                    return v
                elif v.startswith("0b") or v.startswith("0B"):
                    return str(int(v, 2))
                elif v.startswith("0o") or v.startswith("0O"):
                    return str(int(v, 8))
                escaped = self._escape_c_string(v)
                return f'"{escaped}"'
            return "0"

        elif cls == "Identifier":
            # Handle special identifiers
            if node.name in ("None", "none", "null"):
                return "NULL"
            elif node.name in ("True", "true"):
                return "1"
            elif node.name in ("False", "false"):
                return "0"
            return node.name

        elif cls == "AsyncAwait":
            # await expr → _KS_AWAIT(expr)
            inner = self._transpile_expr(node.expr)
            return f"_KS_AWAIT({inner})"

        elif cls == "ListComprehension":
            # Inline list comprehension: emit as a compound statement expression (GCC extension)
            # For simplicity, generate a named temp and return it
            tmp = f"_lc_tmp_{self._label_count}"
            self._label_count += 1
            lc = node
            iter_expr = self._transpile_expr(lc.iterable)
            loop_var = lc.var
            self._emit(f"ks_array {tmp} = {{NULL, 0}};")
            self.declared_vars[tmp] = "ks_array"
            iter_node = lc.iterable
            iter_cls = iter_node.__class__.__name__
            if (
                iter_cls == "FunctionCall"
                and getattr(iter_node, "func", None)
                and getattr(iter_node.func, "name", "") == "range"
            ):
                rargs = iter_node.args
                if len(rargs) == 1:
                    start_c, stop_c = "0", self._transpile_expr(rargs[0])
                else:
                    start_c, stop_c = (
                        self._transpile_expr(rargs[0]),
                        self._transpile_expr(rargs[1]),
                    )
                self._emit(
                    f"for (long long {loop_var} = {start_c}; {loop_var} < {stop_c}; {loop_var}++) {{"
                )
            else:
                self._emit(
                    f"for (long long _i_{tmp} = 0; _i_{tmp} < {iter_expr}.length; _i_{tmp}++) {{"
                )
                self._emit(f"    long long {loop_var} = {iter_expr}.data[_i_{tmp}];")
            if lc.condition:
                cond_c = self._transpile_expr(lc.condition)
                self._emit(f"    if ({cond_c}) {{")
            elem_c = self._transpile_expr(lc.expr)
            # Handle string elements properly - cast to void* instead of long long
            if self._is_string_node(lc.expr):
                self._emit(f"    _ks_array_append(&{tmp}, (void*)(char*){elem_c});")
            else:
                self._emit(f"    _ks_array_append(&{tmp}, (long long)({elem_c}));")
            if lc.condition:
                self._emit("    }")
            self._emit("}")
            return tmp

        elif cls == "DictComprehension":
            tmp = f"_dc_tmp_{self._label_count}"
            self._label_count += 1
            self._emit(f"ks_dict* {tmp} = _ks_dict_new();")
            self.declared_vars[tmp] = "ks_dict*"
            iter_node = node.iterable
            iter_cls = iter_node.__class__.__name__
            loop_var = node.var
            if (
                iter_cls == "FunctionCall"
                and getattr(iter_node, "func", None)
                and getattr(iter_node.func, "name", "") == "range"
            ):
                rargs = iter_node.args
                start_c = "0" if len(rargs) == 1 else self._transpile_expr(rargs[0])
                stop_c = self._transpile_expr(rargs[0] if len(rargs) == 1 else rargs[1])
                self._emit(
                    f"for (long long {loop_var} = {start_c}; {loop_var} < {stop_c}; {loop_var}++) {{"
                )
            else:
                iter_c = self._transpile_expr(iter_node)
                self._emit(
                    f"for (long long _i_{tmp} = 0; _i_{tmp} < {iter_c}.length; _i_{tmp}++) {{"
                )
                self._emit(f"    long long {loop_var} = {iter_c}.data[_i_{tmp}];")
            if node.condition:
                cond_c = self._transpile_expr(node.condition)
                self._emit(f"    if ({cond_c}) {{")
            key_c = self._transpile_expr(node.key)
            val_c = self._transpile_expr(node.value)
            # Handle non-string keys by converting to string representation
            if not self._is_string_node(node.key):
                # Numeric key - convert to string
                self._emit(f"    char _dk_buf_{tmp}[32]; sprintf(_dk_buf_{tmp}, \"%lld\", (long long){key_c});")
                key_c = f"_dk_buf_{tmp}"
                self._emit(f"    _ks_dict_set({tmp}, {key_c}, (void*)(long long)({val_c}), 0);")
            else:
                self._emit(f"    _ks_dict_set({tmp}, (char*){key_c}, (void*)(long long)({val_c}), 1);")
            if node.condition:
                self._emit("    }")
            self._emit("}")
            return tmp

        elif cls == "SetComprehension":
            # Represent as ks_array (same as SetLiteral)
            tmp = f"_sc_tmp_{self._label_count}"
            self._label_count += 1
            self._emit(f"ks_array {tmp} = {{NULL, 0}};")
            self.declared_vars[tmp] = "ks_array"
            iter_node = node.iterable
            iter_cls = iter_node.__class__.__name__
            loop_var = node.var
            if (
                iter_cls == "FunctionCall"
                and getattr(iter_node, "func", None)
                and getattr(iter_node.func, "name", "") == "range"
            ):
                rargs = iter_node.args
                start_c = "0" if len(rargs) == 1 else self._transpile_expr(rargs[0])
                stop_c = self._transpile_expr(rargs[0] if len(rargs) == 1 else rargs[1])
                self._emit(
                    f"for (long long {loop_var} = {start_c}; {loop_var} < {stop_c}; {loop_var}++) {{"
                )
            else:
                iter_c = self._transpile_expr(iter_node)
                self._emit(
                    f"for (long long _i_{tmp} = 0; _i_{tmp} < {iter_c}.length; _i_{tmp}++) {{"
                )
                self._emit(f"    long long {loop_var} = {iter_c}.data[_i_{tmp}];")
            if node.condition:
                cond_c = self._transpile_expr(node.condition)
                self._emit(f"    if ({cond_c}) {{")
            elem_c = self._transpile_expr(node.expr)
            self._emit(f"    _ks_array_append(&{tmp}, (long long)({elem_c}));")
            if node.condition:
                self._emit("    }")
            self._emit("}")
            return tmp

        elif cls == "FStringLiteral":
            return self._transpile_fstring(node)

        elif cls == "BinaryOp":
            return self._transpile_binop(node)

        elif cls == "UnaryOp":
            operand_node = node.operand
            operand = self._transpile_expr(operand_node)
            if node.op == "-":
                return f"(-{operand})"
            if node.op in ("!", "not"):
                return f"(!{operand})"
            if node.op == "&":
                # Check if operand is a Cast to ptr
                if (
                    operand_node.__class__.__name__ == "Cast"
                    and getattr(operand_node, "target_type", None) == "ptr"
                ):
                    # &x as ptr: transpile as (void*)&x
                    # First transpile the inner x (without the cast)
                    inner = self._transpile_expr(operand_node.expr)
                    return f"((void*)(&{inner}))"
                # Address-of operator
                return f"(&{operand})"
            if node.op == "*":
                # Dereference operator
                return f"(*{operand})"
            if node.op == "borrow":
                # borrow x -> &x for scalars, but just x for arrays (array name decays to pointer)
                # Check if operand is an array
                if operand_node.__class__.__name__ == "Identifier":
                    var_name = operand_node.name
                    if var_name in self.declared_vars and self.declared_vars[
                        var_name
                    ].endswith("*"):
                        # Already a pointer type (array) - no & needed
                        return operand
                # Scalar - need address-of
                return f"(&{operand})"
            if node.op == "move":
                # move x -> x (just the value, ownership handled by borrow checker)
                return operand
            return operand

        elif cls == "PointerDeref":
            # Pointer dereference: *expr
            expr = self._transpile_expr(node.expr)
            # Dereferencing void* requires a cast to a concrete type
            return f"(*(long long*)({expr}))"

        elif cls == "Cast":
            # Type casting: expr as type
            inner_expr = self._transpile_expr(node.expr)
            target_type = node.target_type

            # Map KentScript types to C types
            c_type_map = {
                "ptr": "void*",
                "i8": "char",
                "u8": "unsigned char",
                "i16": "short",
                "u16": "unsigned short",
                "i32": "int",
                "u32": "unsigned int",
                "i64": "long long",
                "u64": "unsigned long long",
                "int": "long long",
                "uint": "unsigned long long",
                "f32": "float",
                "f64": "double",
                "float": "double",
                "str": "char*",
                "bool": "int",
            }

            c_type = c_type_map.get(target_type, target_type)
            # For ptr cast, use uintptr_t as intermediate
            if target_type == "ptr":
                # Check if this is being used with address-of: &x as ptr -> &x
                # The UnaryOp handler will add the &, so just return the cast
                return f"((void*)(uintptr_t){inner_expr})"
            return f"(({c_type}){inner_expr})"

        elif cls == "FunctionCall":
            return self._transpile_call_expr(node)

        elif cls == "MemberAccess":
            # e.g. colors.red or point.x
            obj = self._transpile_expr(node.obj)
            member = node.member

            # .length on a FunctionCall result (e.g. str.split(" ").length)
            if member == "length" and node.obj.__class__.__name__ == "FunctionCall":
                # The function call likely returns a ks_array
                return f"({obj}).length"

            # Check if object is 'self' in a class method
            if (
                hasattr(node.obj, "name")
                and node.obj.name == "self"
                and self.current_class_context
            ):
                # In a class method, self.x -> __get_Class_attr_num__(self, "x")
                getter = f"__get_{self.current_class_context}_attr_num__"
                return f'{getter}(self, "{member}")'

            # Check if object is a class instance (pointer type)
            if hasattr(node.obj, "name") and node.obj.name in self.declared_vars:
                var_type = self.declared_vars[node.obj.name]
                # If it's a pointer to a known class instance, use the getter function
                if "_t*" in var_type:
                    # Extract class name from type (e.g., Point_t* -> Point)
                    class_name = var_type.replace("_t*", "").strip()
                    if class_name in self.class_names:
                        getter = f"__get_{class_name}_attr_num__"
                        return f'{getter}({obj}, "{member}")'
                # Handle _ks_http_response_t struct (returned by http.get/post)
                elif var_type == "_ks_http_response_t":
                    return f"{obj}.{member}"

            # Dict methods (property-style access, no args)
            if member == "keys":
                return f"0  /* dict.keys() not fully supported in C */"
            elif member == "values":
                return f"0  /* dict.values() not fully supported in C */"
            elif member in (
                "get",
                "contains",
                "startswith",
                "endswith",
                "replace",
                "split",
                "append",
            ):
                # These require args — only reachable as a property reference, not a call
                return f"0  /* {member} requires args, use as method call */"

            # Array/string .length property
            if member == "length":
                obj_name = getattr(node.obj, "name", None)
                if obj_name and obj_name in self.declared_vars:
                    var_type = self.declared_vars[obj_name]
                    if var_type == "ks_array":
                        return f"{obj}.length"
                    elif var_type == "char*":
                        return f"(long long)strlen({obj})"
                # Fallback: try ks_array .length
                return f"{obj}.length"

            # String methods on char* variables
            obj_name = getattr(node.obj, "name", None)
            if (
                obj_name
                and obj_name in self.declared_vars
                and self.declared_vars[obj_name] == "char*"
            ):
                if member == "upper":
                    return f"_ks_str_upper({obj})"
                elif member == "lower":
                    return f"_ks_str_lower({obj})"
                elif member == "split":
                    return f'_ks_str_split({obj}, " ")'
                elif member == "trim":
                    return f"_ks_str_trim({obj})"
                elif member in ("startswith", "endswith", "contains", "replace"):
                    # These need args — handled in _transpile_call_expr
                    return f"0  /* {member} requires args */"

            # Check if this is an enum member access (Enum.member)
            if hasattr(node.obj, "name") and node.obj.name:
                enum_name = node.obj.name
                # Check if this is a known enum name
                if hasattr(self, "_enum_names") and enum_name in self._enum_names:
                    return f"{enum_name}_{member}"

            return f"0  /* {obj}.{member} */"

        elif cls == "IndexAccess":
            # array[index] access OR io[port] OR msr[reg]
            obj = node.obj

            # Check for hardware access
            obj_name = None
            if hasattr(obj, "name"):
                obj_name = obj.name

            if obj_name == "io":
                # Port I/O read
                idx = self._transpile_expr(node.index)
                return f"_ks_io_read({idx})"
            elif obj_name == "msr":
                # MSR read
                idx = self._transpile_expr(node.index)
                return f"_ks_msr_read({idx})"

            # Check if it's a ks_array
            if obj_name and obj_name in self.declared_vars:
                var_type = self.declared_vars[obj_name]
                if var_type == "ks_array":
                    arr = self._transpile_expr(obj)
                    idx = self._transpile_expr(node.index)
                    # Handle negative index: check for UnaryOp with '-'
                    is_negative = False
                    neg_value = None
                    if (
                        node.index.__class__.__name__ == "UnaryOp"
                        and getattr(node.index, "op", None) == "-"
                    ):
                        is_negative = True
                        # Get the positive value
                        if hasattr(node.index.operand, "value"):
                            neg_value = node.index.operand.value
                    elif (
                        hasattr(node.index, "value")
                        and isinstance(node.index.value, int)
                        and node.index.value < 0
                    ):
                        is_negative = True
                        neg_value = node.index.value

                    if is_negative and neg_value is not None:
                        idx = f"({arr}.length - {abs(neg_value)})"
                    return f"ks_array_get({arr}, {idx})"
                # Also check for dynamic ks_array (contains *)
                elif "*" in var_type and "ks_array" in var_type:
                    arr = self._transpile_expr(obj)
                    idx = self._transpile_expr(node.index)
                    # Handle negative index: convert to length + index
                    if (
                        hasattr(node.index, "value")
                        and isinstance(node.index.value, int)
                        and node.index.value < 0
                    ):
                        idx = f"({arr}.length + {node.index.value})"
                    return f"ks_array_get({arr}, {idx})"
                # Check if it's a dict
                elif var_type == "_ks_dict*":
                    arr = self._transpile_expr(obj)
                    idx = self._transpile_expr(node.index)
                    # Return as char* using _ks_dict_get_str for proper string handling
                    return f"_ks_dict_get_str({arr}, {idx})"

            # Check if it's an array or dict
            arr = self._transpile_expr(obj)
            idx = self._transpile_expr(node.index)

            # Check if it's a FunctionCall whose func is a MemberAccess that returns ks_array (e.g., split())
            # This MUST come before the name check
            if obj.__class__.__name__ == "FunctionCall" and hasattr(obj, "func"):
                if obj.func.__class__.__name__ == "MemberAccess":
                    member = getattr(obj.func, "member", None)
                    if member == "split":
                        return f"ks_array_get({arr}, {idx})"

            # If the object is an identifier, check if it's an array or string
            if hasattr(obj, "name") and obj.name in self.declared_vars:
                var_type = self.declared_vars[obj.name]
                # If it's an array type (contains [] or *), use direct indexing
                if "[]" in str(var_type) or "*" in str(var_type):
                    return f"{arr}[{idx}]"
                # If it's a string type, use string indexing
                elif "char*" in str(var_type) or obj.name in self.string_vars:
                    return f"_ks_str_at({arr}, {idx})"

            # Check if the object is a string literal or string expression
            if obj.__class__.__name__ == "Literal" and isinstance(obj.value, str):
                return f"_ks_str_at({arr}, {idx})"

            # Check if object is in string_vars (this should catch most string variables)
            if hasattr(obj, "name") and obj.name in self.string_vars:
                return f"_ks_str_at({arr}, {idx})"

            # For any identifier that we're not sure about, assume it's a string if it looks like one
            if hasattr(obj, "name"):
                # If the variable name suggests it's text-related, treat as string
                var_name = obj.name.lower()
                if any(
                    word in var_name
                    for word in ["text", "str", "word", "sentence", "name", "message"]
                ):
                    return f"_ks_str_at({arr}, {idx})"

            # Default to dict access
            return f"_ks_dict_get_simple({arr}, {idx})"

        elif cls == "ListLiteral":
            # Generate C array literal: {elem1, elem2, ...}
            if not node.elements:
                return "{}"
            elem_strs = [self._transpile_expr(e) for e in node.elements]
            return "{" + ", ".join(elem_strs) + "}"

        elif cls == "SetLiteral":
            # Represent a set as a ks_array (unique values not enforced in C)
            tmp = f"_set_tmp_{self._label_count}"
            self._label_count += 1
            self._emit(f"ks_array {tmp} = {{NULL, 0}};")
            self.declared_vars[tmp] = "ks_array"
            for elem in node.elements:
                elem_c = self._transpile_expr(elem)
                self._emit(f"_ks_array_append(&{tmp}, (long long)({elem_c}));")
            return tmp

        elif cls == "DictLiteral":
            # Create dict and populate with key-value pairs
            pairs = node.pairs if hasattr(node, "pairs") else []
            if not pairs:
                return "_ks_dict_new()"
            # Use helper function for up to 6 pairs - pad with NULLs
            if len(pairs) <= 6:
                args = []
                for key_node, value_node in pairs:
                    key = self._transpile_expr(key_node)
                    val_raw = self._transpile_expr(value_node)
                    # Check if value is a string
                    val_is_str = isinstance(getattr(value_node, "value", None), str)
                    if val_is_str:
                        val = f"(long long)(uintptr_t){val_raw}"
                    else:
                        val = val_raw
                    key_is_str = isinstance(getattr(key_node, "value", None), str)
                    args.append(f"{key}, {val}, {1 if val_is_str else 0}")
                # Pad to 6 pairs (18 arguments)
                num_pairs = len(pairs)
                for i in range(num_pairs, 6):
                    args.append("0, 0, 0")
                return f"_ks_dict_create({', '.join(args)})"
            # For more pairs, use compound literal with statement expression
            if not hasattr(self, "temp_counter"):
                self.temp_counter = 0
            self.temp_counter += 1
            temp_var = f"_tmp_dict_{self.temp_counter}"
            code_parts = [f"_ks_dict* {temp_var} = _ks_dict_new()"]
            for key_node, value_node in pairs:
                key = self._transpile_expr(key_node)
                val_raw = self._transpile_expr(value_node)
                val_is_str = isinstance(getattr(value_node, "value", None), str)
                if val_is_str:
                    val = f"(long long)(uintptr_t){val_raw}"
                else:
                    val = val_raw
                key_is_str = isinstance(getattr(key_node, "value", None), str)
                code_parts.append(
                    f"_ks_dict_set({temp_var}, {key}, {val}, {1 if val_is_str else 0})"
                )
            code_parts.append(temp_var)
            # Use GCC statement expression: ({ stmt1; stmt2; result; })
            return f"({{ {'; '.join(code_parts)}; }})"

        elif cls == "StructLiteral":
            # Struct initialization: Point { x: 10, y: 20 }
            struct_name = node.name if hasattr(node, "name") else "struct"
            fields = node.fields if hasattr(node, "fields") else []
            field_inits = []
            for field in fields:
                if isinstance(field, tuple):
                    field_name, field_value = field
                    val = self._transpile_expr(field_value)
                    field_inits.append(f".{field_name} = {val}")
                elif hasattr(field, "name") and hasattr(field, "value"):
                    val = self._transpile_expr(field.value)
                    field_inits.append(f".{field.name} = {val}")
            return f"({struct_name}){{{', '.join(field_inits)}}}"

        elif cls == "BorrowStmt":
            # `borrow data` used as expression - returns reference to the variable
            return node.var

        elif cls == "MoveStmt":
            # `move x to y` used as expression - returns the source var
            return node.var

        elif cls == "SliceAccess":
            # array[start:end] - extract a slice as ks_array
            obj = self._transpile_expr(node.obj)
            start_idx = "0"
            end_idx = f"{obj}.length"
            if hasattr(node, "start") and node.start is not None:
                start_idx = self._transpile_expr(node.start)
            if hasattr(node, "end") and node.end is not None:
                end_idx = self._transpile_expr(node.end)
            tmp = f"_slice_tmp_{self._label_count}"
            self._label_count += 1
            self._emit(f"ks_array {tmp} = _ks_slice({obj}, {start_idx}, {end_idx});")
            self.declared_vars[tmp] = "ks_array"
            return tmp

        elif cls == "TupleLiteral":
            # Represent tuple as ks_array (C has no tuples)
            tmp = f"_tuple_tmp_{self._label_count}"
            self._label_count += 1
            self._emit(f"ks_array {tmp} = {{NULL, 0}};")
            self.declared_vars[tmp] = "ks_array"
            for elem in node.elements:
                elem_c = self._transpile_expr(elem)
                self._emit(f"_ks_array_append(&{tmp}, (long long)({elem_c}));")
            return tmp

        elif cls == "SizeofExpr":
            expr_type = getattr(node, "expr_type", None)
            if expr_type:
                return f"sizeof({expr_type})"
            elif hasattr(node, "expr") and node.expr:
                inner = self._transpile_expr(node.expr)
                return f"sizeof({inner})"
            return "sizeof(long long)"

        elif cls == "ScopeResolution":
            # Namespace::member - emit as namespace_member
            namespace = getattr(node, "namespace", "")
            member = getattr(node, "member", "")
            return f"{namespace}_{member}"

    def _transpile_fstring(self, node):
        """Build a C expression that concatenates fstring parts into a string."""
        # Collect all parts as string C-expressions
        part_exprs = []
        for part in node.parts:
            raw = self._transpile_expr(part)
            s = self._to_string_expr(part, raw)
            part_exprs.append(s)

        if not part_exprs:
            return '""'
        if len(part_exprs) == 1:
            return part_exprs[0]

        # Chain _ks_concat calls
        result = part_exprs[0]
        for pe in part_exprs[1:]:
            result = f"_ks_concat({result}, {pe})"
        return result

    def _transpile_binop(self, node):
        """Transpile a binary operation."""
        op = node.op
        left_raw = self._transpile_expr(node.left)
        right_raw = self._transpile_expr(node.right)

        # Numeric operations ALWAYS stay numeric
        if op in ("*", "/", "%", "-", "<<", ">>", "&", "|", "^"):
            return f"({left_raw} {op} {right_raw})"

        if op == "//":
            return f"((long long)({left_raw}) / (long long)({right_raw}))"

        if op == "**":
            return f"(long long)pow((double)({left_raw}), (double)({right_raw}))"

        # For + operator, check if it's string concat or numeric add
        if op == "+":
            left_is_str = self._is_string_node(node.left)
            right_is_str = self._is_string_node(node.right)
            left_is_numeric = self._is_numeric_operation(node.left)
            right_is_numeric = self._is_numeric_operation(node.right)

            # If either side is a string, do string concatenation (convert numerics to strings first)
            if left_is_str or right_is_str:
                ls = self._to_string_expr(node.left, left_raw)
                rs = self._to_string_expr(node.right, right_raw)
                return f"_ks_concat({ls}, {rs})"
            # Both sides are numeric
            return f"({left_raw} + {right_raw})"

        # Arithmetic operations
        if op in ("+", "-", "*", "/", "%"):
            return f"({left_raw} {op} {right_raw})"

        # Comparison / logical operations
        if op in ("<", ">", "<=", ">=", "==", "!=", "and", "or", "&&", "||"):
            c_op = {"and": "&&", "or": "||"}.get(op, op)
            return f"({left_raw} {c_op} {right_raw})"

        return f"({left_raw} {op} {right_raw})"

    def _transpile_list_literal_for_arg(self, node):
        """Convert a ListLiteral to a C array and length for function arguments."""
        if not hasattr(node, "elements") or not node.elements:
            return "(long long*)NULL", "0"

        elems = node.elements

        if not hasattr(self, "_list_arg_counter"):
            self._list_arg_counter = 0
        self._list_arg_counter += 1
        arr_name = f"_list_arg_{self._list_arg_counter}"

        # Check if all elements are literals with a value
        all_have_value = all(hasattr(e, "value") for e in elems)

        if all_have_value:
            # Handle numeric and string values
            vals = []
            for e in elems:
                if isinstance(e.value, str):
                    # It's a string - convert to C string literal
                    vals.append(f'(long long)"{e.value}"')
                else:
                    # It's a number
                    vals.append(str(e.value))
            vals_str = ", ".join(vals)
            self._emit(f"static long long {arr_name}[] = {{{vals_str}}};")
        else:
            # For complex expressions, use NULL
            self._emit(f"static long long {arr_name}[] = {{0}}; /* complex list */")

        return f"{arr_name}", str(len(elems))

    def _transpile_call_expr(self, node):
        """Transpile a function call as an expression."""
        # Handle class instance method calls (obj.method(args) -> __method_Class_method__(obj, args))
        if node.func.__class__.__name__ == "MemberAccess":
            obj = node.func.obj
            member = node.func.member

            # async.run(func) → drive coroutine to completion
            if (
                obj.__class__.__name__ == "Identifier"
                and obj.name == "async"
                and member == "run"
            ):
                if node.args:
                    fn_expr = self._transpile_expr(node.args[0])
                    # Use _ks_coro_ wrapper if available, else cast directly
                    fn_name = getattr(node.args[0], "name", None)
                    coro_fn = (
                        f"_ks_coro_{fn_name}"
                        if fn_name
                        else f"(void(*)(void*)){fn_expr}"
                    )
                    return f"_ks_async_run_fn({coro_fn})"
                return "0"

            # Check if object is a class name (ClassName.new(...) or ClassName.method(...))
            if obj.__class__.__name__ == "Identifier" and obj.name in self.class_names:
                class_name = obj.name
                if member == "new":
                    # Class constructor: Point.new(x, y) -> __new_Point__(x, y)
                    ctor_name = f"__new_{class_name}__"
                    args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                    return f"{ctor_name}({args_c})"
                else:
                    # Static class method call
                    method_name = f"__method_{class_name}_{member}__"
                    args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                    return f"{method_name}({args_c})"

            # Check if object is a class instance
            if obj.__class__.__name__ == "Identifier" and hasattr(obj, "name"):
                obj_name = obj.name
                if obj_name in self.declared_vars:
                    var_type = self.declared_vars[obj_name]
                    if "_t*" in var_type:
                        # It's a class instance - call the method
                        class_name = var_type.replace("_t*", "").strip()
                        if class_name in self.class_names:
                            method_name = f"__method_{class_name}_{member}__"
                            obj_expr = self._transpile_expr(obj)
                            args_list = [obj_expr]
                            for a in node.args:
                                args_list.append(self._transpile_expr(a))
                            args_c = ", ".join(args_list)
                            return f"{method_name}({args_c})"

            # Not a class method - handle common member method calls with args here
            obj_expr = self._transpile_expr(obj)
            args_c_list = [self._transpile_expr(a) for a in node.args]

            # Handle specific known modules BEFORE generic dict/string methods
            if obj.__class__.__name__ == "Identifier":
                if obj.name == "http":
                    if member == "get":
                        args_c = ", ".join(args_c_list)
                        return f"_ks_http_get({args_c})"
                    elif member == "post":
                        if len(args_c_list) >= 2:
                            url = args_c_list[0]
                            data = args_c_list[1]
                            return f"_ks_http_post({url}, {data})"
                        elif len(args_c_list) == 1:
                            url = args_c_list[0]
                            return f'_ks_http_post({url}, "")'
                        else:
                            return f'_ks_http_post("", "")'
                elif obj.name == "json":
                    if member == "loads" and args_c_list:
                        json_str = args_c_list[0]
                        return f"_ks_json_loads({json_str})"

            # Array methods - check if object is a ks_array
            if hasattr(obj, "name") and obj.name in self.declared_vars:
                var_type = self.declared_vars[obj.name]
                if var_type == "ks_array":
                    if member == "get" and args_c_list:
                        return f"ks_array_get({obj_expr}, {args_c_list[0]})"
                    elif member == "len" and not args_c_list:
                        return f"ks_array_len({obj_expr})"
                    elif member == "append" and args_c_list:
                        # Handle string elements properly
                        if self._is_string_node(node.args[0]):
                            return f"_ks_array_append(&{obj_expr}, (void*)(char*){args_c_list[0]})"
                        else:
                            return f"_ks_array_append(&{obj_expr}, (long long)({args_c_list[0]}))"

            # dict methods
            if member == "get" and args_c_list:
                return f"_ks_dict_get_simple({obj_expr}, {args_c_list[0]})"
            if member == "contains" and args_c_list:
                return f"_ks_dict_contains({obj_expr}, {args_c_list[0]})"
            # string methods
            if member == "startswith" and args_c_list:
                return f"(strncmp({obj_expr}, {args_c_list[0]}, strlen({args_c_list[0]})) == 0)"
            if member == "endswith" and args_c_list:
                return f"_ks_str_endswith({obj_expr}, {args_c_list[0]})"
            if member == "contains" and args_c_list:
                return f"(strstr({obj_expr}, {args_c_list[0]}) != NULL)"
            if member == "replace" and len(args_c_list) >= 2:
                return (
                    f"_ks_str_replace({obj_expr}, {args_c_list[0]}, {args_c_list[1]})"
                )
            if member == "split":
                sep = args_c_list[0] if args_c_list else '" "'
                return f"_ks_str_split({obj_expr}, {sep})"
            if member == "append" and args_c_list:
                return f"_ks_array_append(&{obj_expr}, (long long)({args_c_list[0]}))"
            if member == "len" and not args_c_list:
                obj_name = getattr(obj, "name", None)
                if obj_name and obj_name in self.declared_vars:
                    if self.declared_vars[obj_name] == "char*":
                        return f"(long long)strlen({obj_expr})"
                return f"ks_array_len({obj_expr})"

            # Get obj_name for special cases
            obj_name = getattr(obj, "name", None) if obj.__class__.__name__ == "Identifier" else None

            # Generic fallback: obj.method(args)
            # BUT first check for special cases like time.* functions
            if obj_name == "time":
                if member == "time":
                    return "ks_time_seconds()"
                elif member in ("monotonic_ms", "monotonic"):
                    return "ks_time_monotonic_ms()"
            
            # Handle string method calls that were missed earlier
            if member in ("upper", "lower", "trim", "split", "replace", "startswith", 
                        "endswith", "contains", "find", "substring", "join", "strip",
                        "to_upper", "to_lower"):
                if member == "to_upper":
                    return f"_ks_str_upper({obj_expr})"
                elif member == "to_lower":
                    return f"_ks_str_lower({obj_expr})"
            
            # Handle known module function calls (fileio, path, etc.)
            if obj_name in ("fileio", "path", "network", "subprocess", "math", "os", "random", "time"):
                # These are handled elsewhere - skip the generic _ks_ fallback
                pass  # Let it fall through to ModuleMemberAccess handler
            else:
                args_joined = ", ".join([obj_expr] + args_c_list)
                return f"_ks_{member}({args_joined})"

        if node.func.__class__.__name__ == "Identifier":
            fname = node.func.name

            # Handle class constructor calls (ClassName(args) -> __new_ClassName__(args))
            if fname in self.class_names:
                ctor_name = "__new_" + fname + "__"
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                return f"{ctor_name}({args_c})"

            # Handle system_* functions that return strings
            if fname.startswith("system_"):
                # Functions that return char*
                if fname in ("system_os_getenv", "system_file_readlink"):
                    args_list = []
                    for a in node.args:
                        if a.__class__.__name__ == "ListLiteral":
                            arr, length = self._transpile_list_literal_for_arg(a)
                            args_list.append(arr)
                            args_list.append(length)
                        else:
                            args_list.append(self._transpile_expr(a))
                    args_c = ", ".join(args_list)
                    return f"{fname}({args_c})"
                # Functions that take list arguments (deque, counter)
                if fname in ("system_collections_deque", "system_collections_counter"):
                    args_list = []
                    for a in node.args:
                        if a.__class__.__name__ == "ListLiteral":
                            arr, length = self._transpile_list_literal_for_arg(a)
                            args_list.append(arr)
                            args_list.append(length)
                        else:
                            args_list.append(self._transpile_expr(a))
                    args_c = ", ".join(args_list)
                    return f"{fname}({args_c})"
                # defaultdict - takes a factory string
                if fname == "system_collections_defaultdict":
                    args_list = []
                    for a in node.args:
                        if a.__class__.__name__ == "Identifier":
                            # Identifier like 'list' - convert to string
                            args_list.append(f'"{a.name}"')
                        else:
                            args_list.append(self._transpile_expr(a))
                    args_c = ", ".join(args_list)
                    return f"{fname}({args_c})"
                # namedtuple - takes name string and field list
                if fname == "system_collections_namedtuple":
                    args_list = []
                    for i, a in enumerate(node.args):
                        if i == 0:
                            # First arg is the name string
                            args_list.append(self._transpile_expr(a))
                        elif a.__class__.__name__ == "ListLiteral":
                            # Second arg is list of field names
                            arr, length = self._transpile_list_literal_for_arg(a)
                            args_list.append(arr)
                            args_list.append(length)
                        else:
                            args_list.append(self._transpile_expr(a))
                    args_c = ", ".join(args_list)
                    return f"{fname}({args_c})"
                # Other system_* functions - no ks_ prefix needed
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                return f"{fname}({args_c})"

            # Handle system_str_* string functions
            if fname.startswith("system_str_"):
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                return f"{fname}({args_c})"

            # Handle system_encoding_* functions
            if fname.startswith("system_encoding_"):
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                return f"{fname}({args_c})"

            # Handle system_http_* functions
            if fname.startswith("system_http_"):
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                return f"{fname}({args_c})"

            # Handle system_subprocess_check_call
            if fname == "system_subprocess_check_call":
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                return f"system_subprocess_run({args_c}, 0)"

            if fname == "print":
                self._transpile_print(node.args)
                return '""'

            if fname in (
                "progress_bar",
                "progress_bar_cyber",
                "progress_bar_matrix",
                "progress_bar_gradient",
                "progress_bar_scifi",
                "colored",
            ):
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                return f"_ks_{fname}({args_c})"

            if fname == "format_value":
                if len(node.args) >= 2:
                    val_raw = self._transpile_expr(node.args[0])
                    fmt_raw = self._transpile_expr(node.args[1])
                    # Use float version if format spec contains f/e/g
                    fmt_str = getattr(node.args[1], "value", "")
                    if any(c in str(fmt_str) for c in ("f", "e", "g", "E", "G")):
                        return f"_ks_format_value_f((double)({val_raw}), {fmt_raw})"
                    return f"_ks_format_value((long long)({val_raw}), {fmt_raw})"
                return '""'

            if fname == "str":
                if node.args:
                    raw = self._transpile_expr(node.args[0])
                    # Check if there's a base argument (for hex/bin/oct formatting)
                    if len(node.args) > 1:
                        base_node = node.args[1]
                        if hasattr(base_node, "value") and base_node.value == 16:
                            # Hex formatting - cast to long long first if needed
                            return f"_ks_str_hex((long long){raw})"
                        # For other bases, just convert to string normally
                    return self._to_string_expr(node.args[0], raw)
                return '""'

            if fname == "int":
                if node.args:
                    raw = self._transpile_expr(node.args[0])
                    return f"atoll({raw})"
                return "0"

            if fname == "float":
                if node.args:
                    raw = self._transpile_expr(node.args[0])
                    return f"atof({raw})"
                return "0.0"

            if fname == "len":
                if node.args:
                    arg = node.args[0]
                    raw = self._transpile_expr(arg)
                    # Check if it's a ks_array
                    if arg.__class__.__name__ == "Identifier":
                        var_name = arg.name
                        if var_name in self.declared_vars:
                            var_type = self.declared_vars[var_name]
                            if var_type == "ks_array":
                                return f"ks_array_len({raw})"
                            # Check if it's a global array with stored length
                            len_var = f"{var_name}__len"
                            if len_var in self.declared_vars:
                                return self.declared_vars[len_var]
                    # Otherwise assume string
                    return f"_ks_len({raw})"
                return "0"

            if fname == "type":
                if node.args:
                    arg = node.args[0]
                    raw = self._transpile_expr(arg)
                    # Check for bool literal
                    if hasattr(arg, "value") and isinstance(arg.value, bool):
                        return '"bool"'
                    if arg.__class__.__name__ == "Identifier":
                        var_name = arg.name
                        if var_name in self.declared_vars:
                            var_type = self.declared_vars[var_name]
                            if var_type == "char*":
                                return '"str"'
                            elif var_type in ("long long", "int"):
                                # Check if it's actually a bool variable
                                if var_name in self.bool_vars:
                                    return '"bool"'
                                return '"int"'
                            elif var_type == "double":
                                return '"float"'
                            elif var_type == "ks_array":
                                return '"list"'
                            elif "*" in var_type and var_type != "void*":
                                return '"object"'
                    # Check for numeric literal
                    if hasattr(arg, "value") and isinstance(arg.value, (int, float)):
                        if isinstance(arg.value, float):
                            return '"float"'
                        return '"int"'
                    # Check for string literal
                    if hasattr(arg, "value") and isinstance(arg.value, str):
                        return '"str"'
                    return f"_ks_type({raw})"
                return '"unknown"'

            # Low-level memory operations
            if fname == "malloc":
                if node.args:
                    size = self._transpile_expr(node.args[0])
                    return f"ks_malloc({size})"
                return "NULL"

            if fname == "free":
                if node.args:
                    ptr = self._transpile_expr(node.args[0])
                    return f"(ks_free({ptr}), 0)"
                return "0"

            if fname == "ptr_read":
                if len(node.args) >= 1:
                    addr = self._transpile_expr(node.args[0])
                    size = (
                        self._transpile_expr(node.args[1])
                        if len(node.args) > 1
                        else "8"
                    )
                    return f"ks_ptr_read((void*){addr}, {size})"
                return "0"

            if fname == "ptr_write":
                if len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    size = (
                        self._transpile_expr(node.args[2])
                        if len(node.args) > 2
                        else "1"
                    )
                    return f"(ks_ptr_write((void*){addr}, {value}, {size}), 0)"
                return "0"

            if fname == "ptr_cast":
                if node.args:
                    ptr = self._transpile_expr(node.args[0])
                    return f"ks_ptr_cast({ptr})"
                return "NULL"

            if fname == "ptr_deref":
                if node.args:
                    ptr = self._transpile_expr(node.args[0])
                    return f"ks_ptr_deref({ptr})"
                return "0"

            # Syscall operations
            if fname in ("syscall", "system_syscall"):
                args = [self._transpile_expr(arg) for arg in node.args]
                while len(args) < 7:
                    args.append("0")
                return f"ks_system_syscall({', '.join(args[:7])})"

            # Atomic operations
            if fname == "atomic_load":
                if len(node.args) >= 1:
                    addr = self._transpile_expr(node.args[0])
                    size = (
                        self._transpile_expr(node.args[1])
                        if len(node.args) > 1
                        else "8"
                    )
                    return f"ks_atomic_load((void*){addr}, {size})"
                return "0"

            if fname == "atomic_store":
                if len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    size = (
                        self._transpile_expr(node.args[2])
                        if len(node.args) > 2
                        else "8"
                    )
                    return f"(ks_atomic_store((void*){addr}, {value}, {size}), 0)"
                return "0"

            if fname == "atomic_add":
                if len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    size = (
                        self._transpile_expr(node.args[2])
                        if len(node.args) > 2
                        else "8"
                    )
                    return f"ks_atomic_add((void*){addr}, {value}, {size})"
                return "0"

            if fname == "atomic_cas":
                if len(node.args) >= 3:
                    addr = self._transpile_expr(node.args[0])
                    expected = self._transpile_expr(node.args[1])
                    desired = self._transpile_expr(node.args[2])
                    size = (
                        self._transpile_expr(node.args[3])
                        if len(node.args) > 3
                        else "8"
                    )
                    return (
                        f"ks_atomic_cas((void*){addr}, {expected}, {desired}, {size})"
                    )
                return "0"

            # Volatile operations
            if fname == "volatile_read":
                if len(node.args) >= 1:
                    addr = self._transpile_expr(node.args[0])
                    size = (
                        self._transpile_expr(node.args[1])
                        if len(node.args) > 1
                        else "8"
                    )
                    return f"ks_volatile_read((void*){addr}, {size})"
                return "0"

            if fname == "volatile_write":
                if len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    size = (
                        self._transpile_expr(node.args[2])
                        if len(node.args) > 2
                        else "8"
                    )
                    return f"(ks_volatile_write((void*){addr}, {value}, {size}), 0)"
                return "0"

            # Memory barriers
            if fname == "memory_barrier":
                return "(ks_memory_barrier(), 0)"

            if fname == "compiler_barrier":
                return "(ks_compiler_barrier(), 0)"

            # Cache operations
            if fname == "cache_flush":
                if len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    size = self._transpile_expr(node.args[1])
                    return f"(ks_cache_flush((void*){addr}, {size}), 0)"
                return "0"

            if fname == "cache_invalidate":
                if len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    size = self._transpile_expr(node.args[1])
                    return f"(ks_cache_invalidate((void*){addr}, {size}), 0)"
                return "0"

            # MMIO operations
            if fname == "mmio_read":
                if len(node.args) >= 1:
                    addr = self._transpile_expr(node.args[0])
                    size = (
                        self._transpile_expr(node.args[1])
                        if len(node.args) > 1
                        else "8"
                    )
                    return f"ks_mmio_read((void*){addr}, {size})"
                return "0"

            if fname == "mmio_write":
                if len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    size = (
                        self._transpile_expr(node.args[2])
                        if len(node.args) > 2
                        else "8"
                    )
                    return f"(ks_mmio_write((void*){addr}, {value}, {size}), 0)"
                return "0"

            # Port I/O
            if fname == "read_port":
                if node.args:
                    port = self._transpile_expr(node.args[0])
                    return f"ks_read_port({port})"
                return "0"

            if fname == "write_port":
                if len(node.args) >= 2:
                    port = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    return f"(ks_write_port({port}, {value}), 0)"
                return "0"

            # CPU intrinsics
            if fname == "rdtsc":
                return "ks_rdtsc()"

            if fname == "cpuid":
                if len(node.args) >= 5:
                    leaf = self._transpile_expr(node.args[0])
                    eax = self._transpile_expr(node.args[1])
                    ebx = self._transpile_expr(node.args[2])
                    ecx = self._transpile_expr(node.args[3])
                    edx = self._transpile_expr(node.args[4])
                    return f"(ks_cpuid({leaf}, &{eax}, &{ebx}, &{ecx}, &{edx}), 0)"
                return "0"

            # Add missing standard library functions
            if fname == "ord":
                if node.args:
                    raw = self._transpile_expr(node.args[0])
                    return f"_ks_ord({raw})"
                return "0"

            if fname == "chr":
                if node.args:
                    raw = self._transpile_expr(node.args[0])
                    return f"_ks_chr({raw})"
                return '""'

            if fname == "contains":
                if len(node.args) >= 2:
                    haystack = self._transpile_expr(node.args[0])
                    needle = self._transpile_expr(node.args[1])
                    return f"_ks_contains({haystack}, {needle})"
                return "0"

            if fname == "range":
                return "0"

            # clock_ms() - wall-clock time in milliseconds (double)
            if fname == "clock_ms":
                return "ks_time_monotonic_ms()"

            # Special handling for alloc_i64 - allocate i64 array
            if fname == "alloc_i64":
                if node.args:
                    n = self._transpile_expr(node.args[0])

                    # [KS-REF-037] Stack allocation optimization
                    if self.enable_optimizations:
                        strategy = self.stack_allocator.analyze_var_lifetime(
                            var_name="array_alloc",
                            size_expr=n,
                            escapes_function=False,  # Most arrays don't escape
                        )

                        if strategy == MemoryAllocationStrategy.STACK_ALLOCA:
                            # 0-cycle stack allocation
                            return (
                                f"(long long*)__builtin_alloca({n} * sizeof(long long))"
                            )
                        elif strategy == MemoryAllocationStrategy.STACK_VLA:
                            # ~1 cycle, VLA style (but safe - no compound literal)
                            # Use a temporary variable declaration instead
                            return f"(long long*)ks_alloc_i64({n})"

                    return f"ks_alloc_i64({n})"
                return "ks_alloc_i64(0)"

            # free() - direct passthrough
            if fname == "free":
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                return f"(ks_free({args_c}), 0)"

            # SIMD operations (basic wrappers - actual SIMD requires intrinsics)
            if fname == "simd_add" and len(node.args) >= 2:
                a = self._transpile_expr(node.args[0])
                b = self._transpile_expr(node.args[1])
                # For now, fallback to scalar (proper SIMD needs vector types)
                return f"({a} + {b})"

            if fname == "simd_mul" and len(node.args) >= 2:
                a = self._transpile_expr(node.args[0])
                b = self._transpile_expr(node.args[1])
                return f"({a} * {b})"

            # Special handling for built-in functions
            if fname in {
                "malloc",
                "alloc",
                "write_byte",
                "read_byte",
                "write_word",
                "read_word",
                "abs",
                "round",
                "min",
                "max",
                "sum",
                "len",
                "ord",
                "syscall",
                "ptr",
                "asm",
                "inb",
                "outb",
                "inw",
                "outw",
                "inl",
                "outl",
                "memcpy",
                "memset",
                "free",
                "calloc",
                "realloc",
            }:
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)

                # Map KentScript names to C names
                if fname == "alloc":
                    return f"(long long)malloc({args_c})"
                elif fname == "malloc":
                    return f"(long long)malloc({args_c})"
                elif fname == "free":
                    return f"free((void*){args_c})"
                elif fname == "read_word":
                    # Cast first arg to void*
                    if node.args:
                        ptr_expr = f"(void*){self._transpile_expr(node.args[0])}"
                        rest_args = ", ".join(
                            self._transpile_expr(a) for a in node.args[1:]
                        )
                        return f"read_word({ptr_expr}, {rest_args})"
                    return f"read_word({args_c})"
                elif fname == "write_word":
                    # Cast first arg to void*
                    if node.args:
                        ptr_expr = f"(void*){self._transpile_expr(node.args[0])}"
                        rest_args = ", ".join(
                            self._transpile_expr(a) for a in node.args[1:]
                        )
                        return f"(write_word({ptr_expr}, {rest_args}), 0)"
                    return f"(write_word({args_c}), 0)"
                elif fname == "read_byte":
                    if node.args:
                        ptr_expr = f"(void*){self._transpile_expr(node.args[0])}"
                        rest_args = ", ".join(
                            self._transpile_expr(a) for a in node.args[1:]
                        )
                        return f"read_byte({ptr_expr}, {rest_args})"
                    return f"read_byte({args_c})"
                elif fname == "write_byte":
                    if node.args:
                        ptr_expr = f"(void*){self._transpile_expr(node.args[0])}"
                        rest_args = ", ".join(
                            self._transpile_expr(a) for a in node.args[1:]
                        )
                        return f"(write_byte({ptr_expr}, {rest_args}), 0)"
                    return f"(write_byte({args_c}), 0)"
                elif fname == "memcpy":
                    # memcpy(dest, d_off, src, s_off, size)
                    if len(node.args) >= 5:
                        dest = f"(void*){self._transpile_expr(node.args[0])}"
                        d_off = self._transpile_expr(node.args[1])
                        src = f"(void*){self._transpile_expr(node.args[2])}"
                        s_off = self._transpile_expr(node.args[3])
                        size = self._transpile_expr(node.args[4])
                        return f"(memcpy((char*){dest}+{d_off}, (char*){src}+{s_off}, {size}), 0)"
                    return f"(memcpy({args_c}), 0)"
                elif fname == "memset":
                    # memset(ptr, offset, value, size)
                    if len(node.args) >= 4:
                        ptr = f"(void*){self._transpile_expr(node.args[0])}"
                        offset = self._transpile_expr(node.args[1])
                        value = self._transpile_expr(node.args[2])
                        size = self._transpile_expr(node.args[3])
                        return f"(memset((char*){ptr}+{offset}, {value}, {size}), 0)"
                    return f"(memset({args_c}), 0)"
                elif fname == "asm":
                    # Inline assembly - just emit as comment in expression context
                    return "0  /* asm() */"
                elif fname == "syscall":
                    # Direct syscall - use syscall() function
                    return f"syscall({args_c})"
                else:
                    return f"{fname}({args_c})"
            elif fname in self.func_return_types:
                # User-defined function - pass args as numeric if possible
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)
            elif fname in self.declared_vars:
                vtype = self.declared_vars[fname]
                # Check if it's a function pointer (lambda or closure)
                # Skip for known module names - they go to MemberAccess handler
                if vtype == "void*" and fname not in ("fileio", "path", "network", "subprocess", "math", "os", "random", "time"):
                    # Function pointer - pass raw args
                    args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                    # Build function pointer call
                    param_count = len(node.args)
                    params_sig = (
                        ", ".join(["long long"] * param_count)
                        if param_count > 0
                        else "void"
                    )
                    return f"((long long (*)({params_sig})){fname})({args_c})"
                else:
                    # Not a function pointer - pass args as-is
                    args_c = ", ".join(self._transpile_expr(a) for a in node.args)
            else:
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)
            return f"{fname}({args_c})"

        # Module function call (e.g., hardware.read_port())
        if node.func.__class__.__name__ == "MemberAccess":
            obj = node.func.obj
            member = node.func.member

            # Handle time module FIRST - before other checks
            if obj.__class__.__name__ == "Identifier" and obj.name == "time":
                if member == "time":
                    return "ks_time_seconds()"
                elif member in ("monotonic_ms", "monotonic"):
                    return "ks_time_monotonic_ms()"

            # Handle string method calls (str.split(), str.upper(), etc.)
            obj_expr = self._transpile_expr(obj)
            obj_is_str = (
                obj.__class__.__name__ == "Identifier"
                and obj.name in self.declared_vars
                and self.declared_vars[obj.name] == "char*"
            ) or (
                obj.__class__.__name__ == "Literal"
                and isinstance(getattr(obj, "value", None), str)
            )
            
            # Handle known module function calls FIRST (fileio, path, etc.)
            if obj.__class__.__name__ == "Identifier" and obj.name in ("fileio", "path", "network", "subprocess", "math", "os", "random", "time"):
                # These are handled elsewhere - skip string check and fall through to module handlers
                pass
            elif obj_is_str or self._is_string_node(obj):
                if member == "split":
                    sep = self._transpile_expr(node.args[0]) if node.args else '" "'
                    return f"_ks_str_split({obj_expr}, {sep})"
                elif member == "upper":
                    return f"_ks_str_upper({obj_expr})"
                elif member == "lower":
                    return f"_ks_str_lower({obj_expr})"
                elif member == "trim":
                    return f"_ks_str_trim({obj_expr})"
                elif member == "replace" and len(node.args) >= 2:
                    old = self._transpile_expr(node.args[0])
                    new = self._transpile_expr(node.args[1])
                    return f"_ks_str_replace({obj_expr}, {old}, {new})"
                elif member == "startswith" and node.args:
                    prefix = self._transpile_expr(node.args[0])
                    return f"(strncmp({obj_expr}, {prefix}, strlen({prefix})) == 0)"
                elif member == "endswith" and node.args:
                    suffix = self._transpile_expr(node.args[0])
                    return f"_ks_str_endswith({obj_expr}, {suffix})"
                elif member == "contains" and node.args:
                    needle = self._transpile_expr(node.args[0])
                    return f"(strstr({obj_expr}, {needle}) != NULL ? 1 : 0)"
                elif member == "find" and node.args:
                    needle = self._transpile_expr(node.args[0])
                    return f"_ks_str_find({obj_expr}, {needle})"
                elif member == "substring" and len(node.args) >= 2:
                    start = self._transpile_expr(node.args[0])
                    end = self._transpile_expr(node.args[1])
                    return f"_ks_str_substring({obj_expr}, {start}, {end})"
                elif member == "join" and node.args:
                    arr = self._transpile_expr(node.args[0])
                    return f"_ks_str_join({obj_expr}, {arr})"

            # Handle array method calls
            obj_is_arr = (
                obj.__class__.__name__ == "Identifier"
                and obj.name in self.declared_vars
                and self.declared_vars[obj.name] == "ks_array"
            )
            if obj_is_arr:
                if member == "len":
                    return f"ks_array_len({obj_expr})"
                elif member == "append" and node.args:
                    val = self._transpile_expr(node.args[0])
                    return f"(_ks_array_append(&{obj_expr}, {val}), 0)"
                elif member == "pop":
                    return f"_ks_array_pop(&{obj_expr})"
                elif member == "join" and node.args:
                    sep = self._transpile_expr(node.args[0])
                    return f"_ks_array_join({obj_expr}, {sep})"

            # Handle hardware I/O port access
            if obj.__class__.__name__ == "Identifier" and obj.name == "hardware":
                if member == "read_port" and node.args:
                    port = self._transpile_expr(node.args[0])
                    # Return as string representation of the value
                    return f"_ks_str_int((long long)inb((unsigned short){port}))"

                elif member == "write_port" and len(node.args) >= 2:
                    port = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    self._emit(
                        f"outb((unsigned char)(long long){value}, (unsigned short){port});"
                    )
                    return '""'

                elif member == "request_io_privilege":
                    return '""'

                elif member == "request_dma_buffer":
                    return '""'

            # Handle baremetal module functions (low-level hardware access)
            if obj.__class__.__name__ == "Identifier" and obj.name == "baremetal":
                # Memory operations: read8, read16, read32, read64, read_memory
                if member in ("read8", "read_memory") and node.args:
                    addr = self._transpile_expr(node.args[0])
                    return f"ks_ptr_read((void*){addr}, 8)"
                elif member == "read16" and node.args:
                    addr = self._transpile_expr(node.args[0])
                    return f"ks_ptr_read((void*){addr}, 2)"
                elif member == "read32" and node.args:
                    addr = self._transpile_expr(node.args[0])
                    return f"ks_ptr_read((void*){addr}, 4)"
                elif member == "read64" and node.args:
                    addr = self._transpile_expr(node.args[0])
                    return f"ks_ptr_read((void*){addr}, 8)"
                # Memory write operations: write8, write16, write32, write64, write_memory
                elif member in ("write8", "write_memory") and len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    return f"(ks_ptr_write((void*){addr}, {value}, 1), 0)"
                elif member == "write16" and len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    return f"(ks_ptr_write((void*){addr}, {value}, 2), 0)"
                elif member == "write32" and len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    return f"(ks_ptr_write((void*){addr}, {value}, 4), 0)"
                elif member == "write64" and len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    return f"(ks_ptr_write((void*){addr}, {value}, 8), 0)"
                # Port I/O
                elif member in ("inb", "read_port") and node.args:
                    port = self._transpile_expr(node.args[0])
                    return f"ks_read_port((unsigned short){port})"
                elif member in ("outb", "write_port") and len(node.args) >= 2:
                    port = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    return f"(ks_write_port((unsigned short){port}, (unsigned char){value}), 0)"
                elif member == "port_available":
                    return "1"
                # RDTSC
                elif member in ("rdtsc", "read_tsc"):
                    return "ks_rdtsc()"
                # CPUID
                elif member == "cpuid" and node.args:
                    leaf = self._transpile_expr(node.args[0])
                    return f"(ks_cpuid({leaf}, &eax, &ebx, &ecx, &edx), ebx)"
                # Memory allocation
                elif member == "alloc" and node.args:
                    size = self._transpile_expr(node.args[0])
                    return f"ks_malloc((size_t){size})"
                # Cache control
                elif member == "clflush" and node.args:
                    addr = self._transpile_expr(node.args[0])
                    return f"(ks_cache_flush((void*){addr}, 64), 0)"
                elif member == "mfence":
                    return "(ks_memory_barrier(), 0)"
                elif member == "lfence":
                    return "(ks_compiler_barrier(), 0)"
                elif member == "sfence":
                    return "(ks_memory_barrier(), 0)"
                # MSR operations
                elif member == "rdmsr" and node.args:
                    msr = self._transpile_expr(node.args[0])
                    return f"_ks_msr_read({msr})"
                elif member == "wrmsr" and len(node.args) >= 2:
                    msr = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    return f"(_ks_msr_write({msr}, {value}), 0)"
                elif member == "msr_available":
                    return "0"
                # MMIO operations
                elif member == "mmio_read" and node.args:
                    addr = self._transpile_expr(node.args[0])
                    return f"ks_mmio_read((void*){addr}, 8)"
                elif member == "mmio_write" and len(node.args) >= 2:
                    addr = self._transpile_expr(node.args[0])
                    value = self._transpile_expr(node.args[1])
                    return f"(ks_mmio_write((void*){addr}, {value}, 8), 0)"

            # Handle time.time() and time.monotonic_ms()
            if obj.__class__.__name__ == "Identifier" and obj.name == "time":
                if member in ("time", "now"):
                    # time.time() returns seconds (like Python)
                    return "ks_time_seconds()"
                elif member in ("monotonic_ms", "monotonic"):
                    # time.monotonic_ms() returns milliseconds
                    return "ks_time_monotonic_ms()"

            # Handle math functions
            if obj.__class__.__name__ == "Identifier" and obj.name == "math":
                args_c = ", ".join(self._transpile_expr(a) for a in node.args)
                return f"{member}({args_c})"

            # Handle random module functions
            if obj.__class__.__name__ == "Identifier" and obj.name == "random":
                if member == "random":
                    return "system_random_random()"
                elif member == "randint" and len(node.args) >= 2:
                    a = self._transpile_expr(node.args[0])
                    b = self._transpile_expr(node.args[1])
                    return f"system_random_randint({a}, {b})"

            # Handle os module functions
            if obj.__class__.__name__ == "Identifier" and obj.name == "os":
                if member == "getenv" and node.args:
                    arg = self._transpile_expr(node.args[0])
                    default_val = (
                        self._transpile_expr(node.args[1])
                        if len(node.args) > 1
                        else '""'
                    )
                    return f"system_os_getenv({arg}, {default_val})"
                elif member == "getppid":
                    return "system_os_getppid()"
                elif member == "getuid":
                    return "system_os_getuid()"
                elif member == "getgid":
                    return "system_os_getgid()"
                elif member == "getpid":
                    return "system_os_getpid()"
                elif member == "mkdir" and node.args:
                    path = self._transpile_expr(node.args[0])
                    mode = (
                        self._transpile_expr(node.args[1])
                        if len(node.args) > 1
                        else "0755"
                    )
                    return f"system_os_mkdir({path}, {mode})"
                elif member == "rmdir" and node.args:
                    path = self._transpile_expr(node.args[0])
                    return f"system_os_rmdir({path})"
                elif member == "rename" and len(node.args) >= 2:
                    oldp = self._transpile_expr(node.args[0])
                    newp = self._transpile_expr(node.args[1])
                    return f"system_os_rename({oldp}, {newp})"
                elif member == "kill" and len(node.args) >= 2:
                    pid = self._transpile_expr(node.args[0])
                    sig = self._transpile_expr(node.args[1])
                    return f"system_os_kill({pid}, {sig})"

            # Handle random module functions
            if obj.__class__.__name__ == "Identifier" and obj.name == "random":
                if member == "random":
                    return "system_random_random()"
                elif member == "randint" and len(node.args) >= 2:
                    a = self._transpile_expr(node.args[0])
                    b = self._transpile_expr(node.args[1])
                    return f"system_random_randint({a}, {b})"
                elif member == "uniform" and len(node.args) >= 2:
                    a = self._transpile_expr(node.args[0])
                    b = self._transpile_expr(node.args[1])
                    return f"system_random_uniform({a}, {b})"
                elif member == "choice" and node.args:
                    # For now, just return a random number since proper array handling is complex
                    return "system_random_random()"
                elif member == "seed" and node.args:
                    seed = self._transpile_expr(node.args[0])
                    return f"system_random_seed({seed})"

            # Handle subprocess module functions
            if obj.__class__.__name__ == "Identifier" and obj.name == "subprocess":
                if member == "run" and node.args:
                    cmd = self._transpile_expr(node.args[0])
                    return f"system_subprocess_run({cmd}, 0)"

            # Handle fileio module functions
            if obj.__class__.__name__ == "Identifier" and obj.name == "fileio":
                if member == "exists" and node.args:
                    path = self._transpile_expr(node.args[0])
                    return f"system_file_exists({path})"
                elif member == "stat" and node.args:
                    path = self._transpile_expr(node.args[0])
                    return f"system_file_stat({path})"
                elif member == "remove" and node.args:
                    path = self._transpile_expr(node.args[0])
                    return f"system_file_remove({path})"
                elif member == "chmod" and len(node.args) >= 2:
                    path = self._transpile_expr(node.args[0])
                    mode = self._transpile_expr(node.args[1])
                    return f"system_file_chmod({path}, {mode})"
                elif member == "symlink" and len(node.args) >= 2:
                    target = self._transpile_expr(node.args[0])
                    link = self._transpile_expr(node.args[1])
                    return f"system_file_symlink({target}, {link})"
                elif member == "readlink" and node.args:
                    path = self._transpile_expr(node.args[0])
                    return f"system_file_readlink({path})"
                elif member in ("write", "write_text") and len(node.args) >= 2:
                    path = self._transpile_expr(node.args[0])
                    content = self._transpile_expr(node.args[1])
                    return f"(system_file_write_text({path}, {content}), 0)"
                elif member in ("read", "read_text") and node.args:
                    path = self._transpile_expr(node.args[0])
                    return f"system_file_read_text({path})"
                elif member == "open" and node.args:
                    path = self._transpile_expr(node.args[0])
                    mode = self._transpile_expr(node.args[1]) if len(node.args) > 1 else '"r"'
                    return f"system_file_open({path}, {mode})"

            # Handle path module functions
            if obj.__class__.__name__ == "Identifier" and obj.name == "path":
                if member == "getsize" and node.args:
                    path = self._transpile_expr(node.args[0])
                    return f"system_file_getsize({path})"
                elif member == "exists" and node.args:
                    path = self._transpile_expr(node.args[0])
                    return f"system_file_exists({path})"

            # Handle time module functions
            if obj.__class__.__name__ == "Identifier" and obj.name == "time":
                if member == "time":
                    return "system_time_time()"
                elif member == "sleep" and node.args:
                    secs = self._transpile_expr(node.args[0])
                    return f"(system_time_sleep({secs}), 0)"

            # Handle string methods
            obj_c = self._transpile_expr(obj)
            if member == "upper":
                return f"_ks_str_upper({obj_c})"
            elif member == "lower":
                return f"_ks_str_lower({obj_c})"
            elif member == "strip":
                return f"_ks_str_strip({obj_c})"

            # Handle dict methods
            if member == "get":
                if node.args:
                    key = self._transpile_expr(node.args[0])
                    return f"_ks_dict_get_simple({obj_c}, {key})"
            elif member == "contains":
                if node.args:
                    key = self._transpile_expr(node.args[0])
                    return f"_ks_dict_contains({obj_c}, {key})"
                return f'_ks_dict_contains({obj_c}, "")'
            elif member == "keys":
                return f"_ks_dict_print_keys({obj_c})"
            elif member == "values":
                return f"_ks_dict_print_values({obj_c})"

            return "0"

        # Lambda / complex callee
        func_expr = self._transpile_expr(node.func)
        return f"({func_expr})()"

    def _transpile_cond(self, node):
        """Transpile a condition expression to a C boolean expression."""
        cls = node.__class__.__name__

        if cls == "BinaryOp" and node.op in ("<", ">", "<=", ">=", "!="):
            left = self._transpile_expr(node.left)
            right = self._transpile_expr(node.right)
            left_s = self._is_string_node(node.left)
            right_s = self._is_string_node(node.right)
            if left_s or right_s:
                # String comparison via strcmp
                ls = self._to_string_expr(node.left, left)
                rs = self._to_string_expr(node.right, right)
                cmp_map = {
                    "<": "<0",
                    ">": ">0",
                    "<=": "<=0",
                    ">=": ">=0",
                    "==": "==0",
                    "!=": "!=0",
                }
                return f"(strcmp({ls}, {rs}) {cmp_map[node.op]})"
            return f"({left} {node.op} {right})"

        if cls == "BinaryOp" and node.op == "==":
            left = self._transpile_expr(node.left)
            right = self._transpile_expr(node.right)
            left_s = self._is_string_node(node.left)
            right_s = self._is_string_node(node.right)
            if left_s or right_s:
                ls = self._to_string_expr(node.left, left)
                rs = self._to_string_expr(node.right, right)
                return f"(strcmp({ls}, {rs}) == 0)"
            return f"({left} == {right})"

        raw = self._transpile_expr(node)
        if self._is_string_node(node):
            return f"(strlen({raw}) > 0)"
        return raw

    # ------------------------------------------------------------------ type helpers

    def _is_string_node(self, node):
        """Check if a node should be treated as a string."""
        try:
            cls = node.__class__.__name__
            if cls == "Literal" and isinstance(getattr(node, "value", None), str):
                return True
            if cls == "Identifier":
                # Check if it's a declared variable of type char*
                if node.name in self.declared_vars:
                    return self.declared_vars[node.name] == "char*"
                # Also check func_return_types for functions returning strings
                if node.name in self.func_return_types:
                    return self.func_return_types[node.name] == "char*"
                return False
            if cls == "BinaryOp" and node.op == "+":
                left_s = self._is_string_node(node.left)
                right_s = self._is_string_node(node.right)
                return left_s or right_s
            if cls == "FunctionCall":
                fn = node.func
                if fn.__class__.__name__ == "Identifier":
                    fname = fn.name
                    if fname in self.func_return_types:
                        return self.func_return_types[fname] == "char*"
                    if node.func.__class__.__name__ == "MemberAccess":
                        obj = node.func.obj
                        if hasattr(obj, "name") and obj.name == "time":
                            return False
            if cls == "IndexAccess":
                return True
        except:
            pass
        return False

    def _is_numeric_operation(self, node):
        """Check if this node is definitely a numeric operation"""
        cls = node.__class__.__name__
        if cls == "Literal":
            return isinstance(node.value, (int, float))
        if cls == "Identifier":
            return node.name in self.numeric_vars
        if cls == "BinaryOp":
            # These operations ALWAYS return numbers
            if node.op in ("*", "/", "%", "-", "//", "**", "<<", ">>", "&", "|", "^"):
                return True
            # Check both sides
            left_is_num = self._is_numeric_operation(node.left)
            right_is_num = self._is_numeric_operation(node.right)
            if node.op == "+":
                # + with both numeric is numeric
                return left_is_num or right_is_num
        if cls == "FunctionCall":
            if node.func.__class__.__name__ == "Identifier":
                fname = node.func.name
                if fname in (
                    "int",
                    "float",
                    "len",
                    "ord",
                    "abs",
                    "round",
                    "min",
                    "max",
                    "sum",
                    "clock_ms",
                ):
                    return True
                if fname in self.func_return_types:
                    return self.func_return_types[fname] in ("double", "long long")
            if node.func.__class__.__name__ == "MemberAccess":
                obj = node.func.obj
                if hasattr(obj, "name") and obj.name == "time":
                    return True
        if cls == "IndexAccess":
            return True
        return False

    def _to_string_expr(self, node, c_expr):
        """
        Given an AST node and its C expression, return a C expression that is char*.
        If the node is already a string, return as-is.
        Otherwise wrap with _ks_str_int() / _ks_str_dbl().
        """
        if self._is_string_node(node):
            return c_expr

        # Check if it's dict access (returns char*)
        cls = node.__class__.__name__
        if cls == "IndexAccess":
            obj = node.obj
            if hasattr(obj, "name") and obj.name in self.declared_vars:
                if self.declared_vars[obj.name] == "_ks_dict*":
                    return c_expr  # Already a char*

        # .length always returns a number
        if cls == "MemberAccess" and node.member == "length":
            return f"_ks_str_int({c_expr})"

        if cls == "Literal":
            v = node.value
            if isinstance(v, float):
                return f"_ks_str_dbl({c_expr})"
            if isinstance(v, bool):
                return f'({c_expr} ? "True" : "False")'
            if isinstance(v, int):
                return f"_ks_str_int({c_expr})"
            return c_expr

        def _node_is_double(n):
            c = n.__class__.__name__
            if c == "Literal" and isinstance(getattr(n, "value", None), float):
                return True
            if c == "Identifier":
                return self.declared_vars.get(n.name) == "double"
            if c == "FunctionCall":
                fn = n.func
                if (
                    fn.__class__.__name__ == "Identifier"
                    and fn.name in self.func_return_types
                ):
                    return self.func_return_types[fn.name] == "double"
                if fn.__class__.__name__ == "MemberAccess":
                    if hasattr(fn.obj, "name") and fn.obj.name == "time":
                        return True
            if c == "BinaryOp":
                return _node_is_double(n.left) or _node_is_double(n.right)
            return False

        if cls == "BinaryOp":
            if node.op in ("<", ">", "<=", ">=", "==", "!=", "and", "or"):
                return f'({c_expr} ? "True" : "False")'
            if _node_is_double(node):
                return f"_ks_str_dbl({c_expr})"
            if node.op in ("+", "-", "*", "/", "%", "**"):
                return f"_ks_str_int({c_expr})"

        if cls == "IndexAccess":
            # Dict access returns long long, convert to string
            return f"_ks_str_int({c_expr})"

        if cls == "Identifier":
            if node.name in self.declared_vars:
                var_type = self.declared_vars[node.name]
                if var_type == "double":
                    return f"_ks_str_dbl({c_expr})"
                elif var_type == "char*":
                    return c_expr
                # Check if it's an array type (raw pointer with known length or ks_array)
                elif var_type == "ks_array":
                    # Use ks_array fields: .data and .length
                    return f"_ks_str_array({c_expr}.data, {c_expr}.length)"
                elif var_type == "void*":
                    # Pointer type - cast to uintptr_t before converting
                    return f"_ks_str_hex((long long)(uintptr_t){c_expr})"
                elif "long long*" in str(var_type) or "[]" in str(var_type):
                    len_var = f"{node.name}__len"
                    if len_var in self.declared_vars:
                        array_len = self.declared_vars[len_var]
                        return f"_ks_str_array({c_expr}, {array_len})"
                    return '"[array]"'
                else:
                    if node.name in self.bool_vars:
                        return f'({c_expr} ? "True" : "False")'
                    return f"_ks_str_int({c_expr})"
            # If it's a known bool var, convert to True/False
            if node.name in self.bool_vars:
                return f'({c_expr} ? "True" : "False")'
            # If it's a known numeric var, convert to string
            if node.name in self.numeric_vars:
                return f"_ks_str_int({c_expr})"
            # If it's a known string var, return as-is
            if node.name in self.string_vars:
                return c_expr
            # Default: assume numeric and convert
            return f"_ks_str_int({c_expr})"

        if cls == "MemberAccess":
            # Struct member access - convert to string
            return f"_ks_str_int({c_expr})"

        if cls == "FunctionCall":
            if node.func.__class__.__name__ == "Identifier":
                fname = node.func.name
                if fname in ("int", "len", "read_word", "read_byte"):
                    return f"_ks_str_int({c_expr})"
                if fname == "float":
                    return f"_ks_str_dbl({c_expr})"
                if fname in self.func_return_types:
                    ret_type = self.func_return_types[fname]
                    if ret_type == "double":
                        return f"_ks_str_dbl({c_expr})"
                    elif ret_type == "long long":
                        return f"_ks_str_int({c_expr})"
                # Variable holding a function pointer (void*) - result is long long
                if fname in self.declared_vars and self.declared_vars[fname] == "void*":
                    return f"_ks_str_int({c_expr})"
            elif node.func.__class__.__name__ == "MemberAccess":
                obj = node.func.obj
                member = node.func.member
                if obj.__class__.__name__ == "Identifier":
                    if obj.name == "time":
                        return f"_ks_str_dbl({c_expr})"
                    if obj.name == "math":
                        return f"_ks_str_dbl({c_expr})"
                    if member == "contains":
                        return f'({c_expr} ? "true" : "false")'
                    if member in ("keys", "values"):
                        return c_expr  # returns char*
                    # Array/list methods that return long long
                    if member in ("len", "length", "size", "count", "index", "find"):
                        return f"_ks_str_int({c_expr})"
            return c_expr  # assume returns char*

        # Default: treat as integer
        return f"_ks_str_int({c_expr})"
