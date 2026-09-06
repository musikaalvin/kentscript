#!/usr/bin/env python3
"""
KentScript language-data generator for the LSP.

Emits a single JSON document describing the language surface
(keywords, types, builtins, stdlib modules + their functions) derived
*from the real compiler/stdlib* so the editor stays in sync as the
language grows.  Run once at LSP startup:

    python3 langdata.py  ->  JSON on stdout

Everything degrades gracefully: if the real lexer can't be imported we
fall back to a curated snapshot so the server still works.
"""
import sys, os, re, json

# ── Locate the KentScript root (same logic as analyze.py) ───────────────────
possible_roots = [
    os.environ.get('KENTSCRIPT_ROOT'),
    os.path.join(os.path.dirname(__file__), '..'),
    '/home/pylord/Desktop/KentScript',
    os.path.expanduser('~/Desktop/KentScript'),
]
ks_root = None
for r in possible_roots:
    if r and os.path.isdir(os.path.join(r, 'compiler')):
        ks_root = r
        break
if ks_root is None:
    ks_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, ks_root)

# ── Keywords (authoritative: from the real lexer) ───────────────────────────
KEYWORDS = []
try:
    from compiler.lexer.lexer import KEYWORDS as _KW
    KEYWORDS = sorted(_KW.keys())
except Exception:
    KEYWORDS = [
        'and', 'as', 'assert', 'async', 'await', 'break', 'catch', 'case',
        'class', 'const', 'continue', 'default', 'del', 'do', 'elif', 'else',
        'enum', 'except', 'export', 'extends', 'false', 'finally', 'for',
        'from', 'func', 'global', 'goto', 'if', 'implements', 'import', 'in',
        'inline', 'interface', 'lambda', 'let', 'match', 'module', 'move',
        'mut', 'new', 'none', 'nonlocal', 'not', 'or', 'pass', 'raise',
        'return', 'safe', 'self', 'static', 'struct', 'super', 'switch',
        'trait', 'true', 'try', 'type', 'union', 'unsafe', 'volatile',
        'while', 'with', 'yield', 'sizeof', 'impl', 'to', 'borrow', 'release',
    ]

# ── Types ───────────────────────────────────────────────────────────────────
TYPES = [
    'i8', 'i16', 'i32', 'i64', 'i128',
    'u8', 'u16', 'u32', 'u64', 'u128',
    'f16', 'f32', 'f64', 'f128',
    'isize', 'usize',
    'int', 'uint', 'float', 'bool', 'str', 'string', 'char',
    'void', 'ptr', 'any',
]

# ── Builtins (curated, comprehensive) ───────────────────────────────────────
# Merged from the interpreter builtin table + the unsafe/memory/IO surface.
BUILTINS = {
    # Output / conversion
    'print':      {'sig': 'func print(*args)', 'doc': 'Print to stdout'},
    'println':    {'sig': 'func println(*args)', 'doc': 'Print line with newline'},
    'input':      {'sig': 'func input(prompt="") -> str', 'doc': 'Read from stdin'},
    'str':        {'sig': 'func str(obj, base?) -> str', 'doc': 'Convert to string'},
    'int':        {'sig': 'func int(obj) -> int', 'doc': 'Convert to integer'},
    'float':      {'sig': 'func float(obj) -> float', 'doc': 'Convert to float'},
    'bool':       {'sig': 'func bool(obj) -> bool', 'doc': 'Convert to boolean'},
    'char':       {'sig': 'func char(obj) -> char', 'doc': 'Convert to char'},
    'type':       {'sig': 'func type(obj) -> str', 'doc': 'Get type name'},
    'format':     {'sig': 'func format(fmt, *args) -> str', 'doc': 'Format string (printf-style)'},
    'format_value': {'sig': 'func format_value(obj, fmt?) -> str', 'doc': 'Format value with specifier'},
    # Collections
    'len':        {'sig': 'func len(obj) -> int', 'doc': 'Get length of object'},
    'list':       {'sig': 'func list(*args) -> list', 'doc': 'Create list'},
    'dict':       {'sig': 'func dict(**kwargs) -> dict', 'doc': 'Create dictionary'},
    'range':      {'sig': 'func range(start, stop?, step?) -> list', 'doc': 'Create range sequence'},
    'append':     {'sig': 'func append(list, item)', 'doc': 'Append to list'},
    'push':       {'sig': 'func push(list, item)', 'doc': 'Push to list (alias of append)'},
    'pop':        {'sig': 'func pop(list) -> any', 'doc': 'Pop last element'},
    'sort':       {'sig': 'func sort(list, reverse=false)', 'doc': 'Sort list in place'},
    'reverse':    {'sig': 'func reverse(list)', 'doc': 'Reverse list'},
    'map':        {'sig': 'func map(fn, iterable) -> list', 'doc': 'Map function over iterable'},
    'filter':     {'sig': 'func filter(fn, iterable) -> list', 'doc': 'Filter iterable'},
    'reduce':     {'sig': 'func reduce(fn, iterable, initial?) -> any', 'doc': 'Reduce iterable'},
    'enumerate':  {'sig': 'func enumerate(iterable, start=0) -> list', 'doc': 'Enumerate with index'},
    'zip':        {'sig': 'func zip(*iterables) -> list', 'doc': 'Zip iterables'},
    'reversed':   {'sig': 'func reversed(iterable) -> list', 'doc': 'Reverse iterable'},
    'sorted':     {'sig': 'func sorted(iterable, reverse=false) -> list', 'doc': 'Sort iterable'},
    'sum':        {'sig': 'func sum(iterable, start=0) -> num', 'doc': 'Sum iterable'},
    'min':        {'sig': 'func min(*args) -> num', 'doc': 'Minimum value'},
    'max':        {'sig': 'func max(*args) -> num', 'doc': 'Maximum value'},
    'all':        {'sig': 'func all(iterable) -> bool', 'doc': 'True if all elements truthy'},
    'any':        {'sig': 'func any(iterable) -> bool', 'doc': 'True if any element truthy'},
    'keys':       {'sig': 'func keys(dict) -> list', 'doc': 'Dict keys'},
    'values':     {'sig': 'func values(dict) -> list', 'doc': 'Dict values'},
    'items':      {'sig': 'func items(dict) -> list', 'doc': 'Dict items (pairs)'},
    'contains':   {'sig': 'func contains(container, item) -> bool', 'doc': 'Membership test'},
    # String
    'split':      {'sig': 'func split(str, sep?) -> list', 'doc': 'Split string'},
    'join':       {'sig': 'func join(str, parts) -> str', 'doc': 'Join parts with separator'},
    'trim':       {'sig': 'func trim(str) -> str', 'doc': 'Trim whitespace'},
    'upper':      {'sig': 'func upper(str) -> str', 'doc': 'Uppercase'},
    'lower':      {'sig': 'func lower(str) -> str', 'doc': 'Lowercase'},
    'replace':    {'sig': 'func replace(str, old, new) -> str', 'doc': 'Replace substring'},
    'startswith': {'sig': 'func startswith(str, prefix) -> bool', 'doc': 'Prefix test'},
    'endswith':   {'sig': 'func endswith(str, suffix) -> bool', 'doc': 'Suffix test'},
    # Math
    'abs':        {'sig': 'func abs(x) -> num', 'doc': 'Absolute value'},
    'pow':        {'sig': 'func pow(x, y) -> num', 'doc': 'Power (x^y)'},
    'sqrt':       {'sig': 'func sqrt(x) -> float', 'doc': 'Square root'},
    'floor':      {'sig': 'func floor(x) -> float', 'doc': 'Floor'},
    'ceil':       {'sig': 'func ceil(x) -> float', 'doc': 'Ceiling'},
    'round':      {'sig': 'func round(x, n=0) -> float', 'doc': 'Round'},
    'sin':        {'sig': 'func sin(x) -> float', 'doc': 'Sine'},
    'cos':        {'sig': 'func cos(x) -> float', 'doc': 'Cosine'},
    'tan':        {'sig': 'func tan(x) -> float', 'doc': 'Tangent'},
    'asin':       {'sig': 'func asin(x) -> float', 'doc': 'Arc sine'},
    'acos':       {'sig': 'func acos(x) -> float', 'doc': 'Arc cosine'},
    'atan':       {'sig': 'func atan(x) -> float', 'doc': 'Arc tangent'},
    'atan2':      {'sig': 'func atan2(y, x) -> float', 'doc': 'Two-arg arc tangent'},
    'hypot':      {'sig': 'func hypot(x, y) -> float', 'doc': 'Hypotenuse'},
    'exp':        {'sig': 'func exp(x) -> float', 'doc': 'Exponential'},
    'log':        {'sig': 'func log(x, base?) -> float', 'doc': 'Logarithm'},
    'log10':      {'sig': 'func log10(x) -> float', 'doc': 'Base-10 log'},
    'log2':       {'sig': 'func log2(x) -> float', 'doc': 'Base-2 log'},
    'sign':       {'sig': 'func sign(x) -> int', 'doc': 'Sign of x'},
    'clamp':      {'sig': 'func clamp(x, lo, hi)', 'doc': 'Clamp to range'},
    'cbrt':       {'sig': 'func cbrt(x) -> float', 'doc': 'Cube root'},
    # Numeric / string conversion
    'hex':        {'sig': 'func hex(x) -> str', 'doc': 'Hex string'},
    'bin':        {'sig': 'func bin(x) -> str', 'doc': 'Binary string'},
    'oct':        {'sig': 'func oct(x) -> str', 'doc': 'Octal string'},
    'chr':        {'sig': 'func chr(x) -> str', 'doc': 'Int to char'},
    'ord':        {'sig': 'func ord(c) -> int', 'doc': 'Char to int'},
    'sizeof':     {'sig': 'func sizeof(type) -> int', 'doc': 'Size of type in bytes'},
    'type_of':    {'sig': 'func type_of(obj) -> str', 'doc': 'Type name of object'},
    # Error / control
    'panic':      {'sig': 'func panic(msg)', 'doc': 'Abort with panic'},
    'assert':     {'sig': 'func assert(cond, msg?)', 'doc': 'Assert condition'},
    'exit':       {'sig': 'func exit(code=0)', 'doc': 'Exit process'},
    # Filesystem / IO
    'open':       {'sig': 'func open(path, mode="r") -> file', 'doc': 'Open file'},
    'close':      {'sig': 'func close(file)', 'doc': 'Close file'},
    'read':       {'sig': 'func read(file, n?) -> str', 'doc': 'Read from file'},
    'write':      {'sig': 'func write(file, data)', 'doc': 'Write to file'},
    'read_file':  {'sig': 'func read_file(path) -> str', 'doc': 'Read entire file'},
    'write_file': {'sig': 'func write_file(path, data)', 'doc': 'Write entire file'},
    'seek':       {'sig': 'func seek(file, offset, whence=0)', 'doc': 'Seek in file'},
    'tell':       {'sig': 'func tell(file) -> int', 'doc': 'Tell file position'},
    'stat':       {'sig': 'func stat(path) -> dict', 'doc': 'File status'},
    'getcwd':     {'sig': 'func getcwd() -> str', 'doc': 'Current working directory'},
    'makedirs':   {'sig': 'func makedirs(path, exist_ok=false)', 'doc': 'Create dirs recursively'},
    'remove':     {'sig': 'func remove(path)', 'doc': 'Remove file'},
    'rename':     {'sig': 'func rename(src, dst)', 'doc': 'Rename path'},
    # Process / env
    'system':     {'sig': 'func system(cmd) -> int', 'doc': 'Run shell command'},
    'spawn':      {'sig': 'func spawn(cmd, args?) -> int', 'doc': 'Spawn process'},
    'env':        {'sig': 'func env() -> dict', 'doc': 'Environment variables'},
    'getenv':     {'sig': 'func getenv(key, default?) -> str', 'doc': 'Get env var'},
    'sleep':      {'sig': 'func sleep(seconds)', 'doc': 'Sleep'},
    'random':     {'sig': 'func random() -> float', 'doc': 'Random float [0,1)'},
    'hash':       {'sig': 'func hash(obj) -> int', 'doc': 'Hash value'},
    'uuid':       {'sig': 'func uuid() -> str', 'doc': 'Generate UUID'},
    # Crypto / FFI
    'encrypt':    {'sig': 'func encrypt(data, key) -> str', 'doc': 'Encrypt data'},
    'decrypt':    {'sig': 'func decrypt(data, key) -> str', 'doc': 'Decrypt data'},
    'ffi_load':   {'sig': 'func ffi_load(lib) -> handle', 'doc': 'Load shared library'},
    'ffi_call':   {'sig': 'func ffi_call(handle, sym, *args)', 'doc': 'Call FFI symbol'},
    # Concurrency / misc
    'spawn_thread': {'sig': 'func spawn_thread(fn) -> handle', 'doc': 'Spawn thread'},
    'lock':       {'sig': 'func lock(handle)', 'doc': 'Acquire lock'},
    'unlock':     {'sig': 'func unlock(handle)', 'doc': 'Release lock'},
    'channel':    {'sig': 'func channel() -> handle', 'doc': 'Create channel'},
    'send':       {'sig': 'func send(ch, val)', 'doc': 'Send on channel'},
    'recv':       {'sig': 'func recv(ch) -> any', 'doc': 'Receive from channel'},
    'ternary':    {'sig': 'func ternary(c, t, e) -> any', 'doc': 'Ternary operator'},
    'copy':       {'sig': 'func copy(obj) -> obj', 'doc': 'Shallow copy'},
    'unwrap':     {'sig': 'func unwrap(opt) -> any', 'doc': 'Unwrap option'},
    # Borrow checker
    'borrow':     {'sig': 'func borrow(name, mutable=false)', 'doc': 'Borrow variable'},
    'release':    {'sig': 'func release(name)', 'doc': 'Release borrow'},
    'move':       {'sig': 'func move(name, target)', 'doc': 'Move variable'},
    # Unsafe / memory (require `unsafe { }`)
    'ptr':        {'sig': 'func ptr(addr) -> ptr', 'doc': 'Create pointer', 'unsafe': True},
    'ptr_read':   {'sig': 'func ptr_read(addr, size=8) -> num', 'doc': 'Read from pointer', 'unsafe': True},
    'ptr_write':  {'sig': 'func ptr_write(addr, value, size=8)', 'doc': 'Write to pointer', 'unsafe': True},
    'malloc':     {'sig': 'func malloc(size) -> ptr', 'doc': 'Allocate memory', 'unsafe': True},
    'free':       {'sig': 'func free(ptr)', 'doc': 'Free memory', 'unsafe': True},
    'calloc':     {'sig': 'func calloc(n, size) -> ptr', 'doc': 'Zero-alloc memory', 'unsafe': True},
    'realloc':    {'sig': 'func realloc(ptr, size) -> ptr', 'doc': 'Reallocate memory', 'unsafe': True},
    'alloca':     {'sig': 'func alloca(size) -> ptr', 'doc': 'Stack allocate', 'unsafe': True},
    'memcpy':     {'sig': 'func memcpy(dest, src, size)', 'doc': 'Copy memory', 'unsafe': True},
    'memset':     {'sig': 'func memset(ptr, value, size)', 'doc': 'Set memory', 'unsafe': True},
    'mmap':       {'sig': 'func mmap(addr, len, prot, flags, fd, off) -> ptr', 'doc': 'Map memory', 'unsafe': True},
    'munmap':     {'sig': 'func munmap(ptr, len)', 'doc': 'Unmap memory', 'unsafe': True},
    'mprotect':   {'sig': 'func mprotect(ptr, len, prot)', 'doc': 'Protect memory', 'unsafe': True},
    'atomic_add': {'sig': 'func atomic_add(addr, value) -> num', 'doc': 'Atomic add', 'unsafe': True},
    'atomic_sub': {'sig': 'func atomic_sub(addr, value) -> num', 'doc': 'Atomic subtract', 'unsafe': True},
    'atomic_cas': {'sig': 'func atomic_cas(addr, old, new) -> bool', 'doc': 'Compare and swap', 'unsafe': True},
    'atomic_swap': {'sig': 'func atomic_swap(addr, new) -> num', 'doc': 'Atomic swap', 'unsafe': True},
    'read_byte':  {'sig': 'func read_byte(addr) -> int', 'doc': 'Read byte', 'unsafe': True},
    'write_byte': {'sig': 'func write_byte(addr, value)', 'doc': 'Write byte', 'unsafe': True},
    'read_word':  {'sig': 'func read_word(addr, offset, size) -> num', 'doc': 'Read word', 'unsafe': True},
    'write_word': {'sig': 'func write_word(addr, offset, value, size)', 'doc': 'Write word', 'unsafe': True},
    'read_string': {'sig': 'func read_string(addr) -> str', 'doc': 'Read string', 'unsafe': True},
    'write_string': {'sig': 'func write_string(addr, str)', 'doc': 'Write string', 'unsafe': True},
    'dma_transfer': {'sig': 'func dma_transfer(src, dest, size)', 'doc': 'DMA transfer', 'unsafe': True},
    'inb':        {'sig': 'func inb(port) -> int', 'doc': 'Read port byte', 'unsafe': True},
    'outb':       {'sig': 'func outb(port, value)', 'doc': 'Write port byte', 'unsafe': True},
    'inw':        {'sig': 'func inw(port) -> int', 'doc': 'Read port word', 'unsafe': True},
    'outw':       {'sig': 'func outw(port, value)', 'doc': 'Write port word', 'unsafe': True},
    'rdtsc':      {'sig': 'func rdtsc() -> int', 'doc': 'Read timestamp counter', 'unsafe': True},
    'cpuid':      {'sig': 'func cpuid(leaf) -> list', 'doc': 'CPUID', 'unsafe': True},
    'cli':        {'sig': 'func cli()', 'doc': 'Clear interrupts', 'unsafe': True},
    'sti':        {'sig': 'func sti()', 'doc': 'Set interrupts', 'unsafe': True},
    'hlt':        {'sig': 'func hlt()', 'doc': 'Halt CPU', 'unsafe': True},
    'pause':      {'sig': 'func pause()', 'doc': 'PAUSE instruction', 'unsafe': True},
    'syscall':    {'sig': 'func syscall(num, *args) -> int', 'doc': 'System call', 'unsafe': True},
    'asm':        {'sig': 'func asm(code)', 'doc': 'Inline assembly', 'unsafe': True},
    'call_ptr':   {'sig': 'func call_ptr(ptr, *args) -> any', 'doc': 'Call function pointer', 'unsafe': True},
}

# ── Stdlib modules (scanned from stdlib/*.ks) ───────────────────────────────
MODULES = {}


def _scan_module(path, mod):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            src = f.read()
    except OSError:
        return
    funcs = {}
    # top-level `func name(params)` or `export func name(params)`
    for m in re.finditer(r'^(?:export\s+)?func\s+(\w+)\s*\(([^)]*)\)', src, re.M):
        name, params = m.group(1), m.group(2).strip()
        funcs[name] = {
            'sig': f'func {name}({params})',
            'doc': f'{mod} module function',
        }
    # also `func name(params) {` without closing paren on same line fallback
    for m in re.finditer(r'^(?:export\s+)?func\s+(\w+)\s*\(([^)]*)$', src, re.M):
        name, params = m.group(1), m.group(2).strip()
        if name not in funcs:
            funcs[name] = {'sig': f'func {name}({params})', 'doc': f'{mod} module function'}
    if funcs:
        MODULES[mod] = funcs


stdlib_dir = os.path.join(ks_root, 'stdlib')
if os.path.isdir(stdlib_dir):
    for fn in sorted(os.listdir(stdlib_dir)):
        if not fn.endswith('.ks') or fn == '__init__.py':
            continue
        mod = fn[:-3]
        _scan_module(os.path.join(stdlib_dir, fn), mod)

# ── Curated SIMD / GPU module API (transpiled to C, not in stdlib .ks) ──────
def _add_vec(mod, kinds):
    for kind in kinds:
        for op in ('alloc', 'free', 'get', 'set', 'add', 'sub', 'mul', 'div',
                   'scale', 'addc', 'fma', 'sum', 'dot'):
            n = f'{op}_{kind}'
            MODULES.setdefault(mod, {})[n] = {
                'sig': f'func {mod}.{n}(...)',
                'doc': f'{mod.upper()} {op} on {kind} vectors',
            }


_add_vec('simd', ('f32', 'f64', 'i32', 'i64'))
_add_vec('gpu', ('f32', 'f64', 'i32', 'i64'))
MODULES.setdefault('simd', {})['arch'] = {'sig': 'func simd.arch() -> str', 'doc': 'SIMD architecture name'}
MODULES.setdefault('simd', {})['width'] = {'sig': 'func simd.width() -> int', 'doc': 'SIMD register width (bytes)'}
MODULES.setdefault('gpu', {})['available'] = {'sig': 'func gpu.available() -> bool', 'doc': 'GPU available?'}
MODULES.setdefault('gpu', {})['name'] = {'sig': 'func gpu.name() -> str', 'doc': 'GPU name'}
MODULES.setdefault('gpu', {})['cuda_available'] = {'sig': 'func gpu.cuda_available() -> bool', 'doc': 'CUDA available?'}
MODULES.setdefault('gpu', {})['cuda_name'] = {'sig': 'func gpu.cuda_name() -> str', 'doc': 'CUDA device name'}

print(json.dumps({
    'keywords': KEYWORDS,
    'types': TYPES,
    'builtins': BUILTINS,
    'modules': MODULES,
}))
