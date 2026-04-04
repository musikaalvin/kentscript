#!/usr/bin/env python3
"""
KentScript real semantic analyzer for LSP.
Uses the actual lexer+parser, then does scope/type analysis on the AST.
"""
import sys, json, os, re

# Try to find KentScript root - check multiple locations
possible_roots = [
    os.environ.get('KENTSCRIPT_ROOT'),  # Custom env var
    os.path.join(os.path.dirname(__file__), '..'),  # Relative to script (dev mode)
    '/home/pylord/Desktop/KentScript',  # Default install location
    os.path.expanduser('~/Desktop/KentScript'),
]

ks_root = None
for root in possible_roots:
    if root and os.path.isdir(os.path.join(root, 'compiler')):
        ks_root = root
        break

if ks_root:
    sys.path.insert(0, ks_root)
else:
    # Fallback - try relative path anyway
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Actual keywords from compiler/lexer/lexer.py KEYWORDS dict
KEYWORDS = {
    'and', 'as', 'async', 'await', 'break', 'case', 'class', 'const', 'continue',
    'default', 'elif', 'else', 'enum', 'except', 'export', 'extends', 'false',
    'finally', 'for', 'from', 'func', 'global', 'if', 'implements', 'import',
    'in', 'let', 'match', 'mut', 'new', 'none', 'nonlocal', 'not', 'or',
    'raise', 'return', 'self', 'struct', 'super', 'true', 'try', 'type', 'unsafe', 'while'
}

# Actual types from codegen/c_transpiler.py
TYPES = {
    'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64',
    'f32', 'f64', 'int', 'uint', 'float', 'bool', 'str', 'string',
    'char', 'void', 'ptr', 'any'
}

# Unsafe builtins from ks/interpreter.py
UNSAFE_BUILTINS = {
    'malloc', 'free', 'realloc', 'calloc', 'ptr_read', 'ptr_write',
    'mmap', 'munmap', 'mprotect', 'syscall', 'asm', 'inb', 'outb', 'inw', 'outw',
    'rdtsc', 'cpuid', 'cli', 'sti', 'hlt', 'pause',
    'atomic_add', 'atomic_sub', 'atomic_cas', 'atomic_swap',
    'read_byte', 'write_byte', 'read_word', 'write_word', 'read_string', 'write_string',
    'memcpy', 'memset', 'alloca', 'dma_transfer', 'call_ptr', 'ptr'
}

# Safe builtins from ks/interpreter.py
SAFE_BUILTINS = {
    'print', 'println', 'input', 'len', 'range', 'append', 'push', 'pop',
    'sort', 'reverse', 'map', 'filter', 'zip', 'enumerate', 'keys', 'values',
    'items', 'split', 'join', 'trim', 'upper', 'lower', 'replace', 'format',
    'contains', 'type_of', 'sizeof', 'copy', 'panic', 'assert', 'unwrap',
    'exit', 'sleep', 'system', 'env', 'getcwd', 'spawn', 'hash', 'encrypt',
    'decrypt', 'random', 'ffi_load', 'ffi_call', 'read_file', 'write_file',
    'open', 'close', 'read', 'write', 'seek', 'tell', 'stat',
    'abs', 'all', 'any', 'pow', 'sqrt', 'floor', 'ceil', 'round',
    'sin', 'cos', 'tan', 'log', 'exp', 'hex', 'bin', 'oct', 'chr', 'ord',
    'reversed', 'sorted', 'sum', 'min', 'max', 'list', 'dict', 'str', 'int', 'float', 'bool', 'type',
    'format_value', 'reduce', 'ternary', 'borrow', 'release', 'move'
}

ALL_BUILTINS = SAFE_BUILTINS | UNSAFE_BUILTINS


def analyze(source):
    diags = []
    symbols = []

    # --- Lex ---
    try:
        from compiler.lexer.lexer import Lexer
        tokens = Lexer(source, filename='<lsp>').tokenize()
    except Exception as e:
        diags.append({'line': 0, 'col': 0, 'severity': 1, 'message': f'Lex error: {e}'})
        return {'diagnostics': diags, 'symbols': symbols}

    # --- Parse ---
    ast_nodes = []
    try:
        from compiler.parser.parser import Parser
        result = Parser(tokens, source).parse()
        ast_nodes = result if isinstance(result, list) else (getattr(result, 'body', None) or [])
    except Exception as e:
        msg = str(e)
        m = re.search(r'line\s+(\d+)', msg, re.I)
        line = int(m.group(1)) - 1 if m else 0
        diags.append({'line': line, 'col': 0, 'severity': 1, 'message': f'Parse error: {msg}'})
        return {'diagnostics': diags, 'symbols': symbols}

    # --- Scope-based semantic analysis ---
    scopes = [{'__builtins__': ALL_BUILTINS}]
    
    def push(): scopes.append({})
    def pop(): scopes.pop()
    
    def declare(name, info):
        scopes[-1][name] = info
    
    def lookup(name):
        for s in reversed(scopes):
            if name in s:
                return s[name]
        return None
    
    def err(line, col, msg, sev=1):
        diags.append({'line': max(0, line - 1), 'col': col, 'severity': sev, 'message': msg})
    
    def warn(line, col, msg):
        err(line, col, msg, sev=2)
    
    def node_line(node):
        return getattr(node, 'line', 1) or 1
    
    def check_expr(node):
        if node is None: return None
        t = type(node).__name__
        
        if t == 'Identifier':
            name = getattr(node, 'name', None) or getattr(node, 'value', None)
            if name and lookup(name) is None and name not in KEYWORDS and name not in ALL_BUILTINS:
                err(node_line(node), 0, f"Undefined name '{name}'")
            return None
        
        if t == 'FunctionCall':
            fname = None
            callee = getattr(node, 'func', None) or getattr(node, 'name', None) or getattr(node, 'callee', None)
            if isinstance(callee, str):
                fname = callee
            elif callee is not None:
                fname = getattr(callee, 'name', None) or getattr(callee, 'value', None)
            
            if fname:
                info = lookup(fname)
                if info is None and fname not in ALL_BUILTINS:
                    err(node_line(node), 0, f"Call to undefined function '{fname}'")
            
            # Recurse into args
            for attr in ('args', 'arguments'):
                args = getattr(node, attr, None) or []
                for a in args:
                    check_expr(a)
            return None
        
        if t == 'BinaryOp':
            lt = check_expr(getattr(node, 'left', None))
            rt = check_expr(getattr(node, 'right', None))
            return lt  # simplified
        
        if t == 'ReturnStmt':
            val = getattr(node, 'value', None) or getattr(node, 'expr', None)
            return check_expr(val)
        
        # recurse into children
        for attr in ('value', 'expr', 'left', 'right', 'condition', 'body', 'then_body', 'else_body', 'elements', 'items', 'args'):
            child = getattr(node, attr, None)
            if isinstance(child, list):
                for c in child: check_expr(c)
            elif child is not None and hasattr(child, '__class__'):
                check_expr(child)
        return None
    
    def check_stmt(node):
        if node is None: return
        t = type(node).__name__
        
        if t == 'FunctionDef':
            params = getattr(node, 'params', []) or []
            param_types = getattr(node, 'param_types', {}) or {}
            ret = str(getattr(node, 'return_type', 'void') or 'void')
            param_list = []
            for p in params:
                pname = p if isinstance(p, str) else getattr(p, 'name', str(p))
                param_list.append(pname)
            declare(node.name, {'kind': 'func', 'params': param_list, 'ret': ret, 'line': node_line(node)})
            symbols.append({'name': node.name, 'kind': 'func',
                'detail': f'func {node.name}({", ".join(param_list)}) -> {ret}',
                'line': max(0, node_line(node) - 1)})
            push()
            for p in params:
                pname = p if isinstance(p, str) else getattr(p, 'name', str(p))
                ptype = param_types.get(pname, 'any') if isinstance(param_types, dict) else 'any'
                declare(pname, {'kind': 'var', 'type': str(ptype)})
            for s in (getattr(node, 'body', []) or []):
                check_stmt(s)
            pop()
        
        elif t == 'ClassDef':
            declare(node.name, {'kind': 'class', 'line': node_line(node)})
            symbols.append({'name': node.name, 'kind': 'class', 'line': max(0, node_line(node) - 1)})
            push()
            for m in (getattr(node, 'methods', []) or []):
                check_stmt(m)
            pop()
        
        elif t == 'StructDef':
            declare(node.name, {'kind': 'struct', 'line': node_line(node)})
            symbols.append({'name': node.name, 'kind': 'struct', 'line': max(0, node_line(node) - 1)})
        
        elif t == 'EnumDef':
            declare(node.name, {'kind': 'enum', 'line': node_line(node)})
            symbols.append({'name': node.name, 'kind': 'enum', 'line': max(0, node_line(node) - 1)})
        
        elif t in ('LetDecl', 'VarDecl', 'ConstDecl'):
            vtype = str(getattr(node, 'type_hint', None) or getattr(node, 'type_annotation', None) or 'auto')
            val = getattr(node, 'value', None)
            if vtype not in ('auto', 'any', 'None') and vtype not in TYPES:
                if lookup(vtype) is None:
                    err(node_line(node), 0, f"Unknown type '{vtype}'")
            declare(node.name, {'kind': 'var', 'type': vtype, 'line': node_line(node)})
            symbols.append({'name': node.name, 'kind': 'var', 'type': vtype, 'line': max(0, node_line(node) - 1)})
            if val is not None:
                check_expr(val)
        
        elif t == 'IfStmt':
            check_expr(getattr(node, 'condition', None))
            push()
            for s in (getattr(node, 'then_body', None) or getattr(node, 'body', []) or []):
                check_stmt(s)
            pop()
            push()
            for s in (getattr(node, 'else_body', []) or []):
                check_stmt(s)
            pop()
        
        elif t in ('WhileStmt', 'ForStmt', 'LoopStmt'):
            check_expr(getattr(node, 'condition', None))
            push()
            for s in (getattr(node, 'body', []) or []):
                check_stmt(s)
            pop()
        
        elif t == 'MatchStmt':
            check_expr(getattr(node, 'expr', None))
            push()
            for case_val, case_body in getattr(node, 'cases', []):
                for s in (case_body or []):
                    check_stmt(s)
            pop()
            if getattr(node, 'default', None):
                push()
                for s in node.default:
                    check_stmt(s)
                pop()
        
        elif t == 'ReturnStmt':
            check_expr(getattr(node, 'value', None) or getattr(node, 'expr', None))
        
        elif t == 'UnsafeBlock':
            push()
            for s in (getattr(node, 'body', []) or []):
                check_stmt(s)
            pop()
        
        elif t == 'TryExcept':
            push()
            for s in (getattr(node, 'body', []) or []):
                check_stmt(s)
            pop()
            push()
            for s in (getattr(node, 'handler', []) or getattr(node, 'except_body', []) or []):
                check_stmt(s)
            pop()
        
        else:
            check_expr(node)
            for attr in ('body', 'statements', 'children', 'block'):
                child = getattr(node, attr, None)
                if isinstance(child, list):
                    for c in child: check_stmt(c)
    
    # First pass: collect top-level names
    for node in ast_nodes:
        t = type(node).__name__
        if t == 'FunctionDef':
            params = getattr(node, 'params', []) or []
            param_types = getattr(node, 'param_types', {}) or {}
            ret = str(getattr(node, 'return_type', 'void') or 'void')
            param_list = [p if isinstance(p, str) else getattr(p, 'name', str(p)) for p in params]
            declare(node.name, {'kind': 'func', 'params': param_list, 'ret': ret, 'line': node_line(node)})
        elif t in ('ClassDef', 'StructDef', 'EnumDef'):
            name = getattr(node, 'name', None)
            if name:
                declare(name, {'kind': t.replace('Def', '').lower(), 'line': node_line(node)})
    
    # Second pass: full analysis
    for node in ast_nodes:
        check_stmt(node)
    
    # Unsafe check - verify unsafe builtins are inside unsafe blocks
    unsafe_depth = 0
    for tok in tokens:
        val = str(tok.value)
        if val == 'unsafe':
            unsafe_depth += 1
        elif val == '}':
            unsafe_depth = max(0, unsafe_depth - 1)
        elif val in UNSAFE_BUILTINS and unsafe_depth == 0:
            diags.append({
                'line': tok.line - 1,
                'col': tok.column - 1,
                'severity': 2,
                'message': f"'{val}' is unsafe - must be inside unsafe {{ }}"
            })
    
    return {'diagnostics': diags, 'symbols': symbols}


if __name__ == '__main__':
    print(json.dumps(analyze(sys.stdin.read())))
