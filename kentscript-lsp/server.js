#!/usr/bin/env node
'use strict';

const {
    createConnection, TextDocuments, ProposedFeatures,
    CompletionItemKind, DiagnosticSeverity, SymbolKind,
    TextDocumentSyncKind, SymbolTag, SemanticTokensRequest,
    InlayHintRequest, InlayHintResolveRequest,
    CallHierarchyPrepareRequest, CallHierarchyIncomingCallsRequest, CallHierarchyOutgoingCallsRequest,
    TypeHierarchyPrepareRequest, TypeHierarchySupertypesRequest, TypeHierarchySubtypesRequest,
    FoldingRangeRequest, CodeLensRequest, CodeLensResolveRequest,
    DocumentLinkRequest, DocumentLinkResolveRequest,
    SelectionRangeRequest, LinkedEditingRangeRequest, InlineValueRequest,
    PrepareRenameRequest
} = require('vscode-languageserver/node');
const { TextDocument } = require('vscode-languageserver-textdocument');
const { execFile, execFileSync } = require('child_process');
const path = require('path');

const connection = createConnection(ProposedFeatures.all);
const documents = new TextDocuments(TextDocument);

const ANALYZER = path.join(__dirname, 'analyze.py');
const LANGDATA = path.join(__dirname, 'langdata.py');

// ══════════════════════════════════════════════════════════════════════════════
// KentScript Language Data (synced with actual lexer/parser/interpreter)
// ══════════════════════════════════════════════════════════════════════════════

// Actual keywords from compiler/lexer/lexer.py KEYWORDS dict (69 keywords)
// (overridden at startup from langdata.py when available)
let KEYWORDS = [
    'and', 'as', 'asm', 'assert', 'async', 'await', 'borrow', 'break',
    'case', 'catch', 'class', 'const', 'continue', 'default', 'del', 'do',
    'elif', 'else', 'enum', 'except', 'export', 'extends', 'false', 'finally',
    'for', 'from', 'func', 'global', 'goto', 'if', 'impl', 'implements',
    'import', 'in', 'inline', 'interface', 'lambda', 'let', 'match', 'module',
    'move', 'mut', 'new', 'none', 'nonlocal', 'not', 'or', 'pass',
    'raise', 'release', 'return', 'safe', 'self', 'sizeof', 'static', 'struct',
    'super', 'switch', 'to', 'trait', 'true', 'try', 'type', 'union',
    'unsafe', 'volatile', 'while', 'with', 'yield',
];

// Actual types from codegen/c_transpiler.py and parser
let TYPES = [
    'i8', 'i16', 'i32', 'i64', 'i128', 'u8', 'u16', 'u32', 'u64', 'u128',
    'f16', 'f32', 'f64', 'f128', 'int', 'uint', 'float', 'bool', 'str', 'string',
    'char', 'void', 'ptr', 'any', 'isize', 'usize',
];

// Stdlib modules (func <mod>.<fn>) - populated from langdata.py at startup
let MODULES = {};

// Actual builtins from ks/interpreter.py (builtin_* functions)
// (overridden at startup from langdata.py when available)
let BUILTINS = {
    // Output / conversion
    'print':      { sig: 'func print(*args)',                           doc: 'Print to stdout' },
    'println':    { sig: 'func println(*args)',                          doc: 'Print line with newline' },
    'input':      { sig: 'func input(prompt="") -> str',               doc: 'Read from stdin' },
    'str':        { sig: 'func str(obj, base?) -> str',                 doc: 'Convert to string' },
    'int':        { sig: 'func int(obj) -> int',                       doc: 'Convert to integer' },
    'float':      { sig: 'func float(obj) -> float',                   doc: 'Convert to float' },
    'bool':       { sig: 'func bool(obj) -> bool',                     doc: 'Convert to boolean' },
    'type':       { sig: 'func type(obj) -> str',                      doc: 'Get type name' },
    'format_value': { sig: 'func format_value(obj, fmt?) -> str',       doc: 'Format value with specifier' },
    'format':     { sig: 'func format(fmt, *args) -> str',             doc: 'Format string (printf-style)' },
    
    // Collections
    'len':        { sig: 'func len(obj) -> int',                       doc: 'Get length of object' },
    'list':       { sig: 'func list(*args) -> list',                   doc: 'Create list' },
    'dict':       { sig: 'func dict(**kwargs) -> dict',                doc: 'Create dictionary' },
    'range':      { sig: 'func range(start, stop?, step?) -> list',   doc: 'Create range sequence' },
    'append':     { sig: 'func append(list, item)',                    doc: 'Append to list' },
    'push':       { sig: 'func push(list, item)',                      doc: 'Push to list' },
    'pop':        { sig: 'func pop(list) -> any',                      doc: 'Pop last element' },
    'sort':       { sig: 'func sort(list, reverse=false)',             doc: 'Sort list in place' },
    'reverse':    { sig: 'func reverse(list)',                         doc: 'Reverse list' },
    'contains':   { sig: 'func contains(container, item) -> bool',     doc: 'Membership test' },
    'keys':       { sig: 'func keys(dict) -> list',                    doc: 'Dict keys' },
    'values':     { sig: 'func values(dict) -> list',                  doc: 'Dict values' },
    'items':      { sig: 'func items(dict) -> list',                   doc: 'Dict items' },
    
    // Iteration
    'map':        { sig: 'func map(fn, iterable) -> list',             doc: 'Map function over iterable' },
    'filter':     { sig: 'func filter(fn, iterable) -> list',         doc: 'Filter iterable' },
    'reduce':     { sig: 'func reduce(fn, iterable, initial?) -> any', doc: 'Reduce iterable' },
    'enumerate':  { sig: 'func enumerate(iterable, start=0) -> list',  doc: 'Enumerate with index' },
    'zip':        { sig: 'func zip(*iterables) -> list',              doc: 'Zip iterables' },
    'reversed':   { sig: 'func reversed(iterable) -> list',            doc: 'Reverse iterable' },
    'sorted':     { sig: 'func sorted(iterable, reverse=false) -> list', doc: 'Sort iterable' },
    'sum':        { sig: 'func sum(iterable, start=0) -> num',        doc: 'Sum iterable' },
    'min':        { sig: 'func min(*args) -> num',                    doc: 'Minimum value' },
    'max':        { sig: 'func max(*args) -> num',                    doc: 'Maximum value' },
    'all':        { sig: 'func all(iterable) -> bool',                doc: 'Check all true' },
    'any':        { sig: 'func any(iterable) -> bool',                doc: 'Check any true' },
    
    // String
    'split':      { sig: 'func split(str, sep?) -> list',             doc: 'Split string' },
    'join':       { sig: 'func join(str, parts) -> str',              doc: 'Join parts' },
    'trim':       { sig: 'func trim(str) -> str',                     doc: 'Trim whitespace' },
    'upper':      { sig: 'func upper(str) -> str',                    doc: 'Uppercase' },
    'lower':      { sig: 'func lower(str) -> str',                    doc: 'Lowercase' },
    'replace':    { sig: 'func replace(str, old, new) -> str',        doc: 'Replace substring' },
    'startswith': { sig: 'func startswith(str, prefix) -> bool',      doc: 'Prefix test' },
    'endswith':   { sig: 'func endswith(str, suffix) -> bool',        doc: 'Suffix test' },
    
    // Math
    'abs':        { sig: 'func abs(x) -> num',                        doc: 'Absolute value' },
    'pow':        { sig: 'func pow(x, y) -> num',                    doc: 'Power (x^y)' },
    'sqrt':       { sig: 'func sqrt(x) -> float',                    doc: 'Square root' },
    'floor':      { sig: 'func floor(x) -> float',                   doc: 'Floor' },
    'ceil':       { sig: 'func ceil(x) -> float',                    doc: 'Ceiling' },
    'round':      { sig: 'func round(x, n=0) -> float',              doc: 'Round' },
    'sin':        { sig: 'func sin(x) -> float',                      doc: 'Sine' },
    'cos':        { sig: 'func cos(x) -> float',                      doc: 'Cosine' },
    'tan':        { sig: 'func tan(x) -> float',                      doc: 'Tangent' },
    'asin':       { sig: 'func asin(x) -> float',                     doc: 'Arc sine' },
    'acos':       { sig: 'func acos(x) -> float',                     doc: 'Arc cosine' },
    'atan':       { sig: 'func atan(x) -> float',                     doc: 'Arc tangent' },
    'atan2':      { sig: 'func atan2(y, x) -> float',                 doc: 'Two-arg arc tangent' },
    'hypot':      { sig: 'func hypot(x, y) -> float',                 doc: 'Hypotenuse' },
    'exp':        { sig: 'func exp(x) -> float',                       doc: 'Exponential' },
    'log':        { sig: 'func log(x, base?) -> float',              doc: 'Logarithm' },
    'log10':      { sig: 'func log10(x) -> float',                    doc: 'Base-10 log' },
    'log2':       { sig: 'func log2(x) -> float',                     doc: 'Base-2 log' },
    'sign':       { sig: 'func sign(x) -> int',                       doc: 'Sign of x' },
    'clamp':      { sig: 'func clamp(x, lo, hi)',                     doc: 'Clamp to range' },
    'cbrt':       { sig: 'func cbrt(x) -> float',                     doc: 'Cube root' },
    
    // Numeric conversion
    'hex':        { sig: 'func hex(x) -> str',                        doc: 'Hex string' },
    'bin':        { sig: 'func bin(x) -> str',                        doc: 'Binary string' },
    'oct':        { sig: 'func oct(x) -> str',                        doc: 'Octal string' },
    'chr':        { sig: 'func chr(x) -> str',                        doc: 'Int to char' },
    'ord':        { sig: 'func ord(c) -> int',                        doc: 'Char to int' },
    'sizeof':     { sig: 'func sizeof(type) -> int',                  doc: 'Size of type in bytes' },
    'type_of':    { sig: 'func type_of(obj) -> str',                  doc: 'Type name of object' },
    
    // Error / control
    'panic':      { sig: 'func panic(msg)',                           doc: 'Abort with panic' },
    'assert':     { sig: 'func assert(cond, msg?)',                  doc: 'Assert condition' },
    'assert_eq':  { sig: 'func assert_eq(a, b)',                     doc: 'Assert equality' },
    'assert_ne':  { sig: 'func assert_ne(a, b)',                     doc: 'Assert inequality' },
    'assert_true':{ sig: 'func assert_true(cond)',                    doc: 'Assert true' },
    'assert_false':{ sig: 'func assert_false(cond)',                  doc: 'Assert false' },
    'dbg':        { sig: 'func dbg(obj)',                             doc: 'Debug print' },
    'exit':       { sig: 'func exit(code=0)',                         doc: 'Exit process' },
    
    // Filesystem / IO
    'open':       { sig: 'func open(path, mode="r") -> file',        doc: 'Open file' },
    'close':      { sig: 'func close(file)',                          doc: 'Close file' },
    'read':       { sig: 'func read(file, n?) -> str',               doc: 'Read from file' },
    'write':      { sig: 'func write(file, data)',                    doc: 'Write to file' },
    'read_file':  { sig: 'func read_file(path) -> str',              doc: 'Read entire file' },
    'write_file': { sig: 'func write_file(path, data)',               doc: 'Write entire file' },
    'seek':       { sig: 'func seek(file, offset, whence=0)',        doc: 'Seek in file' },
    'tell':       { sig: 'func tell(file) -> int',                    doc: 'Tell file position' },
    'stat':       { sig: 'func stat(path) -> dict',                   doc: 'File status' },
    'getcwd':     { sig: 'func getcwd() -> str',                      doc: 'Current working directory' },
    'makedirs':   { sig: 'func makedirs(path, exist_ok=false)',       doc: 'Create dirs recursively' },
    'remove':     { sig: 'func remove(path)',                         doc: 'Remove file' },
    'rename':     { sig: 'func rename(src, dst)',                     doc: 'Rename path' },
    'getenv':     { sig: 'func getenv(name, default?) -> str',       doc: 'Get environment variable' },
    'uuid':       { sig: 'func uuid() -> str',                        doc: 'Generate UUID' },
    'sleep':      { sig: 'func sleep(seconds)',                       doc: 'Sleep seconds' },
    'system':     { sig: 'func system(cmd) -> int',                   doc: 'Run shell command' },
    'spawn':      { sig: 'func spawn(fn, args...)',                   doc: 'Spawn thread' },
    'hash':       { sig: 'func hash(obj) -> int',                     doc: 'Hash object' },
    'random':     { sig: 'func random() -> float',                    doc: 'Random float [0,1)' },
    'copy':       { sig: 'func copy(obj) -> obj',                     doc: 'Shallow copy' },
    'new':        { sig: 'func new(type) -> obj',                     doc: 'Create new instance' },
    
    // FFI
    'ffi_load':   { sig: 'func ffi_load(lib) -> handle',             doc: 'Load shared library' },
    'ffi_call':   { sig: 'func ffi_call(handle, func, args) -> any', doc: 'Call foreign function' },
    
    // Memory (unsafe)
    'ptr':        { sig: 'func ptr(addr) -> ptr',                     doc: 'Create pointer', unsafe: true },
    'ptr_read':   { sig: 'func ptr_read(addr, size=8) -> num',        doc: 'Read from pointer', unsafe: true },
    'ptr_write':  { sig: 'func ptr_write(addr, value, size=8)',        doc: 'Write to pointer', unsafe: true },
    'malloc':     { sig: 'func malloc(size) -> ptr',                  doc: 'Allocate memory', unsafe: true },
    'free':       { sig: 'func free(ptr)',                             doc: 'Free memory', unsafe: true },
    'alloca':     { sig: 'func alloca(size) -> ptr',                  doc: 'Stack allocate', unsafe: true },
    'memcpy':     { sig: 'func memcpy(dest, src, size)',              doc: 'Copy memory', unsafe: true },
    'memset':     { sig: 'func memset(ptr, value, size)',             doc: 'Set memory', unsafe: true },
    'memmove':    { sig: 'func memmove(dest, src, size)',             doc: 'Move memory', unsafe: true },
    'calloc':     { sig: 'func calloc(count, size) -> ptr',           doc: 'Allocate zeroed memory', unsafe: true },
    'realloc':    { sig: 'func realloc(ptr, size) -> ptr',            doc: 'Reallocate memory', unsafe: true },
    'call_ptr':   { sig: 'func call_ptr(ptr, *args) -> any',         doc: 'Call function pointer', unsafe: true },
    'dma_transfer': { sig: 'func dma_transfer(src, dest, size)',      doc: 'DMA transfer', unsafe: true },
    
    // Atomic (unsafe)
    'atomic_add': { sig: 'func atomic_add(addr, value) -> num',       doc: 'Atomic add', unsafe: true },
    'atomic_sub': { sig: 'func atomic_sub(addr, value) -> num',       doc: 'Atomic subtract', unsafe: true },
    'atomic_cas': { sig: 'func atomic_cas(addr, old, new) -> bool',  doc: 'Compare and swap', unsafe: true },
    'atomic_swap':{ sig: 'func atomic_swap(addr, new) -> num',        doc: 'Atomic swap', unsafe: true },
    'atomic_load':{ sig: 'func atomic_load(addr) -> num',             doc: 'Atomic load', unsafe: true },
    'atomic_store':{ sig: 'func atomic_store(addr, value)',           doc: 'Atomic store', unsafe: true },
    
    // I/O ports (unsafe)
    'inb':        { sig: 'func inb(port) -> int',                     doc: 'Read port byte', unsafe: true },
    'outb':       { sig: 'func outb(port, value)',                    doc: 'Write port byte', unsafe: true },
    'inw':        { sig: 'func inw(port) -> int',                     doc: 'Read port word', unsafe: true },
    'outw':       { sig: 'func outw(port, value)',                    doc: 'Write port word', unsafe: true },
    'inl':        { sig: 'func inl(port) -> int',                     doc: 'Read port dword', unsafe: true },
    'outl':       { sig: 'func outl(port, value)',                    doc: 'Write port dword', unsafe: true },
    
    // CPU (unsafe)
    'rdtsc':      { sig: 'func rdtsc() -> int',                       doc: 'Read timestamp counter', unsafe: true },
    'cpuid':      { sig: 'func cpuid(leaf) -> int',                   doc: 'CPUID instruction', unsafe: true },
    'syscall':    { sig: 'func syscall(num, *args) -> int',           doc: 'System call', unsafe: true },
    'asm':        { sig: 'func asm(code)',                             doc: 'Inline assembly', unsafe: true },
    'cli':        { sig: 'func cli()',                                 doc: 'Disable interrupts', unsafe: true },
    'sti':        { sig: 'func sti()',                                 doc: 'Enable interrupts', unsafe: true },
    'hlt':        { sig: 'func hlt()',                                 doc: 'Halt CPU', unsafe: true },
    'pause':      { sig: 'func pause()',                               doc: 'Pause CPU', unsafe: true },
    
    // Borrow checker
    'borrow':     { sig: 'func borrow(name, mutable=false)',           doc: 'Borrow variable' },
    'release':    { sig: 'func release(name)',                         doc: 'Release borrow' },
    'move':       { sig: 'func move(name, target_env)',                doc: 'Move variable' },
    
    // Other
    'ternary':    { sig: 'func ternary(condition, then_val, else_val) -> any', doc: 'Ternary operator' },
    'unwrap':     { sig: 'func unwrap(opt) -> any',                   doc: 'Unwrap option' },
    'channel':    { sig: 'func channel() -> handle',                  doc: 'Create channel' },
    'send':       { sig: 'func send(ch, val)',                         doc: 'Send on channel' },
    'recv':       { sig: 'func recv(ch) -> any',                      doc: 'Receive from channel' },
    'lock':       { sig: 'func lock(handle)',                          doc: 'Acquire lock' },
    'unlock':     { sig: 'func unlock(handle)',                        doc: 'Release lock' },
    'range_new':  { sig: 'func range_new(start, stop, step) -> range', doc: 'Create range object' },
    'to_string':  { sig: 'func to_string(obj) -> str',                doc: 'Convert to string' },
    'uuid4':      { sig: 'func uuid4() -> str',                       doc: 'Generate UUID v4' },
};

// ── Self-syncing language data ────────────────────────────────────────────────
// Pull keywords / types / builtins / stdlib modules straight from the real
// compiler + stdlib so the editor never drifts from the language.  Falls back
// to the curated tables above if Python/analyzer are unavailable.
(function loadLangData() {
    try {
        const out = execFileSync('python3', [LANGDATA], { timeout: 20000, encoding: 'utf8' });
        const data = JSON.parse(out);
        if (Array.isArray(data.keywords) && data.keywords.length) KEYWORDS = data.keywords;
        if (Array.isArray(data.types) && data.types.length) TYPES = data.types;
        if (data.builtins && typeof data.builtins === 'object') BUILTINS = data.builtins;
        if (data.modules && typeof data.modules === 'object') MODULES = data.modules;
        connection && connection.console && connection.console.log(
            `[kentscript] synced language data: ${KEYWORDS.length} keywords, ${TYPES.length} types, ${Object.keys(BUILTINS).length} builtins, ${Object.keys(MODULES).length} modules`
        );
    } catch (e) {
        if (connection && connection.console) {
            connection.console.log('[kentscript] using built-in language data (langdata.py unavailable): ' + e.message);
        }
    }
})();

// KentScript snippets (actual syntax)
const SNIPPETS = {
    'func': {
        label: 'Function',
        insertText: 'func ${1:name}(${2:params}) {\n\t$0\n}',
        documentation: 'Define a function'
    },
    'class': {
        label: 'Class',
        insertText: 'class ${1:ClassName} {\n\tfunc __init__(${2:self}) {\n\t\t$0\n\t}\n\n\tfunc method(${3:self}) {\n\t\t\n\t}\n}',
        documentation: 'Define a class'
    },
    'struct': {
        label: 'Struct',
        insertText: 'struct ${1:StructName} {\n\t$0\n}',
        documentation: 'Define a struct'
    },
    'enum': {
        label: 'Enum',
        insertText: 'enum ${1:EnumName} {\n\t${2:Variant1},\n\t${3:Variant2}\n}',
        documentation: 'Define an enum'
    },
    'if': {
        label: 'If statement',
        insertText: 'if ${1:condition} {\n\t$0\n}',
        documentation: 'If statement'
    },
    'elif': {
        label: 'Elif statement',
        insertText: 'elif ${1:condition} {\n\t$0\n}',
        documentation: 'Else if statement'
    },
    'else': {
        label: 'Else statement',
        insertText: 'else {\n\t$0\n}',
        documentation: 'Else statement'
    },
    'for': {
        label: 'For loop',
        insertText: 'for ${1:i} in range(${2:10}) {\n\t$0\n}',
        documentation: 'For loop with range'
    },
    'while': {
        label: 'While loop',
        insertText: 'while ${1:condition} {\n\t$0\n}',
        documentation: 'While loop'
    },
    'match': {
        label: 'Match expression',
        insertText: 'match ${1:expr} {\n\tcase ${2:value1}: {\n\t\t$0\n\t}\n\tcase ${3:value2}: {\n\t\t\n\t}\n\tdefault: {\n\t\t\n\t}\n}',
        documentation: 'Match expression (KentScript style)'
    },
    'try': {
        label: 'Try-except',
        insertText: 'try {\n\t$0\n} except ${1:e} {\n\t\n}',
        documentation: 'Try-except block'
    },
    'unsafe': {
        label: 'Unsafe block',
        insertText: 'unsafe {\n\t$0\n}',
        documentation: 'Unsafe block for systems programming'
    },
    'let': {
        label: 'Let declaration',
        insertText: 'let ${1:name} = ${2:value};',
        documentation: 'Immutable variable declaration'
    },
    'mut': {
        label: 'Mutable variable',
        insertText: 'mut ${1:name} = ${2:value};',
        documentation: 'Mutable variable declaration'
    },
    'const': {
        label: 'Const declaration',
        insertText: 'const ${1:name} = ${2:value};',
        documentation: 'Constant declaration'
    },
    'async': {
        label: 'Async function',
        insertText: 'async func ${1:name}(${2:params}) {\n\t$0\n}',
        documentation: 'Async function'
    },
    'class_method': {
        label: 'Class method',
        insertText: 'func ${1:method_name}(${2:self}) {\n\t$0\n}',
        documentation: 'Class method'
    },
    'return': {
        label: 'Return statement',
        insertText: 'return ${1:value};',
        documentation: 'Return value'
    },
    'import': {
        label: 'Import module',
        insertText: 'import ${1:module};',
        documentation: 'Import module'
    },
    'comprehension': {
        label: 'List comprehension',
        insertText: 'let ${1:result} = [${2:expr} for ${3:x} in ${4:iterable}];',
        documentation: 'List comprehension'
    },
    'comprehension_filter': {
        label: 'Filtered comprehension',
        insertText: 'let ${1:result} = [${2:expr} for ${3:x} in ${4:iterable} if ${5:cond}];',
        documentation: 'List comprehension with filter'
    },
    'trait': {
        label: 'Trait',
        insertText: 'trait ${1:TraitName} {\n\t${2:method_sig};\n}',
        documentation: 'Define a trait (interface)'
    },
    'impl': {
        label: 'Impl block',
        insertText: 'impl ${1:TypeName} for ${2:TraitName} {\n\tfunc ${3:method}(${4:self}) {\n\t\t$0\n\t}\n}',
        documentation: 'Implement a trait for a type'
    },
    'with': {
        label: 'With (resource) block',
        insertText: 'with ${1:resource} {\n\t$0\n}',
        documentation: 'Scoped resource management'
    },
    'lambda': {
        label: 'Lambda',
        insertText: 'let ${1:fn} = lambda (${2:args}) => ${3:expr};',
        documentation: 'Anonymous function'
    },
    'spawn': {
        label: 'Spawn (async)',
        insertText: 'spawn ${1:task}(${2:args});',
        documentation: 'Spawn concurrent task'
    },
    'module': {
        label: 'Module',
        insertText: 'module ${1:module_name} {\n\t$0\n}',
        documentation: 'Define a module'
    },
    'pragma': {
        label: 'Compiler pragma',
        insertText: '::pragma ${1:optimize}\n$0',
        documentation: 'Compiler hint'
    },
    'webui_dark': {
        label: 'WebUI Dark Theme',
        insertText: "import webui;\nlet t = webui.dark_theme();\n$0",
        documentation: 'Import webui with dark theme'
    },
    'websocket_server': {
        label: 'WebSocket Server',
        insertText: "import websocket;\nlet server = websocket.server('${1:0.0.0.0}', ${2:8080});\nserver.on_message(func(client, msg) {\n\t$0\n});\nserver.start();",
        documentation: 'WebSocket server setup'
    },
    'dotenv_load': {
        label: 'Load .env file',
        insertText: "import dotenv;\ndotenv.load('.env');\nlet ${1:key} = dotenv.get('${2:KEY}');\n$0",
        documentation: 'Load and use .env variables'
    },
    'tcp_socket': {
        label: 'TCP Socket Client',
        insertText: "import socket;\nlet s = socket.tcp();\ns.connect('${1:host}', ${2:80});\ns.send('${3:data}');\nlet data = s.recv(4096);\nprint(data);\ns.close();\n$0",
        documentation: 'TCP socket client'
    },
    'gui_toast': {
        label: 'GUI Toast Notification',
        insertText: "import gui;\nlet win = gui.create_window('${1:App}', 600, 500);\ngui.create_toast(win, '${2:Hello!}', 3000);\n$0",
        documentation: 'Create GUI with toast notification'
    },
    'ide_start': {
        label: 'Launch Built-in IDE',
        insertText: "import ide;\nide.start();\n$0",
        documentation: 'Launch the built-in web IDE on localhost:8000'
    },
    'ide_custom_port': {
        label: 'Launch IDE on Custom Port',
        insertText: "import ide;\nide.start_with_port(${1:3000});\n$0",
        documentation: 'Launch the built-in web IDE on a custom port'
    },
};

// ══════════════════════════════════════════════════════════════════════════════
// Workspace state
// ══════════════════════════════════════════════════════════════════════════════

const workspaceState = {
    documents: new Map(),
    symbols: new Map()
};

function debounce(fn, ms) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}

function wordAt(line, ch) {
    let s = ch, e = ch;
    while (s > 0 && /\w/.test(line[s - 1])) s--;
    while (e < line.length && /\w/.test(line[e])) e++;
    return line.slice(s, e);
}

function runAnalyzer(text) {
    return new Promise(resolve => {
        const proc = execFile('python3', [ANALYZER], { timeout: 10000 }, (err, stdout) => {
            if (err || !stdout) {
                resolve({ diagnostics: [], symbols: [], typeInfo: {}, callGraph: [], imports: [] });
                return;
            }
            try { resolve(JSON.parse(stdout)); }
            catch { resolve({ diagnostics: [], symbols: [], typeInfo: {}, callGraph: [], imports: [] }); }
        });
        proc.stdin.write(text);
        proc.stdin.end();
    });
}

const analysisCache = new Map();

async function analyzeDocument(doc) {
    const uri = doc.uri;
    const text = doc.getText();
    const result = await runAnalyzer(text);
    workspaceState.documents.set(uri, { text, analysis: result, version: doc.version });
    workspaceState.symbols.set(uri, result.symbols || []);
    return result;
}

const debouncedAnalyze = debounce(async (doc) => { await analyzeDocument(doc); }, 300);

// ══════════════════════════════════════════════════════════════════════════════
// Semantic tokens
// ══════════════════════════════════════════════════════════════════════════════

const TOKEN_TYPES = [
    'keyword', 'type', 'function', 'variable', 'string', 'number',
    'comment', 'operator', 'class', 'struct', 'enum', 'interface',
    'property', 'parameter', 'builtin', 'macro', 'attribute', 'decorator',
    'namespace', 'label'
];

function computeSemanticTokens(text, symbols) {
    const lines = text.split('\n');
    const tokens = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        
        // Comments (:: style)
        let match = line.match(/(::.*)$/);
        if (match) tokens.push({ line: i, start: match.index, length: match[1].length, type: TOKEN_TYPES.indexOf('comment') });
        
        // Strings
        const stringRegex = /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g;
        while ((match = stringRegex.exec(line)) !== null) {
            tokens.push({ line: i, start: match.index, length: match[1].length, type: TOKEN_TYPES.indexOf('string') });
        }
        
        // Numbers (including hex 0x, binary 0b)
        const numRegex = /\b(0x[0-9a-fA-F]+|0b[01]+|\d+\.?\d*)\b/g;
        while ((match = numRegex.exec(line)) !== null) {
            tokens.push({ line: i, start: match.index, length: match[1].length, type: TOKEN_TYPES.indexOf('number') });
        }
        
        // Keywords
        const kwRegex = new RegExp(`\\b(${KEYWORDS.join('|')})\\b`, 'g');
        while ((match = kwRegex.exec(line)) !== null) {
            tokens.push({ line: i, start: match.index, length: match[1].length, type: TOKEN_TYPES.indexOf('keyword') });
        }
        
        // Types
        const typeRegex = new RegExp(`\\b(${TYPES.join('|')})\\b`, 'g');
        while ((match = typeRegex.exec(line)) !== null) {
            tokens.push({ line: i, start: match.index, length: match[1].length, type: TOKEN_TYPES.indexOf('type') });
        }
        
        // Builtins
        const builtinRegex = new RegExp(`\\b(${Object.keys(BUILTINS).join('|')})\\b`, 'g');
        while ((match = builtinRegex.exec(line)) !== null) {
            tokens.push({ line: i, start: match.index, length: match[1].length, type: TOKEN_TYPES.indexOf('builtin') });
        }
    }
    
    return tokens.map(t => [t.line, t.start, t.length, t.type, 0]);
}

// ══════════════════════════════════════════════════════════════════════════════
// LSP Handlers
// ══════════════════════════════════════════════════════════════════════════════

async function validate(doc) {
    const result = await analyzeDocument(doc);
    
    const diags = (result.diagnostics || []).map(d => ({
        range: {
            start: { line: d.line, character: d.col || 0 },
            end: { line: d.line, character: (d.col || 0) + (d.length || 80) }
        },
        severity: d.severity === 1 ? DiagnosticSeverity.Error : DiagnosticSeverity.Warning,
        message: d.message,
        source: 'kentscript',
        code: d.code
    }));
    
    connection.sendDiagnostics({ uri: doc.uri, diagnostics: diags });
}

// ── Initialize ───────────────────────────────────────────────────────────────────

connection.onInitialize(() => ({
    capabilities: {
        textDocumentSync: TextDocumentSyncKind.Incremental,
        completionProvider: { resolveProvider: true, triggerCharacters: ['.', ':', ' ', '(', ',', '{', '['] },
        hoverProvider: true,
        definitionProvider: true,
        typeDefinitionProvider: true,
        implementationProvider: true,
        referencesProvider: true,
        documentSymbolProvider: { hierarchicalDocumentSymbolSupport: true },
        workspaceSymbolProvider: { resolveProvider: true },
        semanticTokensProvider: {
            legend: {
                tokenTypes: TOKEN_TYPES,
                tokenModifiers: ['declaration', 'definition', 'readonly', 'static', 'abstract', 'async', 'modification', 'documentation', 'default', 'const', 'deprecated']
            },
            full: true,
            incrementalSupport: true
        },
        inlayHintProvider: { resolveProvider: true },
        callHierarchyProvider: true,
        typeHierarchyProvider: true,
        signatureHelpProvider: { triggerCharacters: ['(', ','], retriggerCharacters: [','] },
        foldingRangeProvider: { rangeLimit: 10000, lineFoldingOnly: false },
        codeActionProvider: { resolveProvider: true, codeActionKinds: ['quickfix', 'refactor', 'source.organizeImports', 'source.fixAll', 'source.addMissingImports', 'source.generate'] },
        codeLensProvider: { resolveProvider: true },
        documentLinkProvider: { resolveProvider: true },
        selectionRangeProvider: true,
        linkedEditingRangeProvider: true,
        inlineValueProvider: true,
        documentFormattingProvider: true,
        documentRangeFormattingProvider: true,
        onTypeFormattingProvider: { firstTriggerCharacter: '\n', moreTriggerCharacter: ['{', '}', ';'] },
        renameProvider: { prepareProvider: true },
        executeCommandProvider: {
            commands: ['kentscript.applyFix', 'kentscript.applyRefactor', 'kentscript.generateCode', 'kentscript.organizeImports', 'kentscript.addImport', 'kentscript.extractFunction', 'kentscript.extractVariable']
        }
    },
    serverInfo: { name: 'KentScript LSP', version: '3.1.0' }
}));

documents.onDidOpen(e => validate(e.document));
documents.onDidChangeContent(e => debouncedAnalyze(e.document));
documents.onDidClose(e => {
    workspaceState.documents.delete(e.document.uri);
    workspaceState.symbols.delete(e.document.uri);
    connection.sendDiagnostics({ uri: e.document.uri, diagnostics: [] });
});
documents.onDidSave(e => validate(e.document));

// ── Completion ────────────────────────────────────────────────────────────────

connection.onCompletion(params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    
    const text = doc.getText();
    const lines = text.split('\n');
    const line = lines[params.position.line] || '';
    const before = line.slice(0, params.position.character);
    const prefix = (before.match(/\w+$/) || [''])[0].toLowerCase();
    const items = [];
    const triggerChar = params.context?.triggerCharacter;

    // Member access (e.g. "simd." or "x.") - works on both auto-trigger and manual Ctrl+Space
    const memberMatch = before.match(/(\w+)\.\s*$/);
    if (memberMatch) {
        const moduleName = memberMatch[1];
        // Module API (simd./gpu./os./math./system./json./...) - synced from stdlib
        if (MODULES[moduleName]) {
            return Object.entries(MODULES[moduleName]).map(([name, info]) => ({
                label: name,
                kind: CompletionItemKind.Method,
                detail: info.sig || `func ${moduleName}.${name}`,
                documentation: info.doc || `${moduleName} module function`,
                insertText: name + '('
            }));
        }
        // Generic container/string/builtin member suggestions
        return [
            { label: 'len', kind: CompletionItemKind.Property, detail: 'property: int', documentation: 'Get length' },
            { label: 'get', kind: CompletionItemKind.Method, detail: 'method: any', documentation: 'Get by index' },
            { label: 'set', kind: CompletionItemKind.Method, detail: 'method', documentation: 'Set by index' },
            { label: 'push', kind: CompletionItemKind.Method, detail: 'method', documentation: 'Push to list' },
            { label: 'pop', kind: CompletionItemKind.Method, detail: 'method', documentation: 'Pop from list' },
            { label: 'append', kind: CompletionItemKind.Method, detail: 'method', documentation: 'Append to list' },
            { label: 'keys', kind: CompletionItemKind.Method, detail: 'method: list', documentation: 'Get dict keys' },
            { label: 'values', kind: CompletionItemKind.Method, detail: 'method: list', documentation: 'Get dict values' },
            { label: 'items', kind: CompletionItemKind.Method, detail: 'method: list', documentation: 'Get dict items' },
            { label: 'upper', kind: CompletionItemKind.Method, detail: 'method: str', documentation: 'Convert to uppercase' },
            { label: 'lower', kind: CompletionItemKind.Method, detail: 'method: str', documentation: 'Convert to lowercase' },
            { label: 'split', kind: CompletionItemKind.Method, detail: 'method: list', documentation: 'Split string' },
            { label: 'join', kind: CompletionItemKind.Method, detail: 'method: str', documentation: 'Join parts' },
            { label: 'trim', kind: CompletionItemKind.Method, detail: 'method: str', documentation: 'Trim whitespace' },
            { label: 'contains', kind: CompletionItemKind.Method, detail: 'method: bool', documentation: 'Check contains' },
            { label: 'replace', kind: CompletionItemKind.Method, detail: 'method: str', documentation: 'Replace substring' },
            { label: 'startswith', kind: CompletionItemKind.Method, detail: 'method: bool', documentation: 'Check prefix' },
            { label: 'endswith', kind: CompletionItemKind.Method, detail: 'method: bool', documentation: 'Check suffix' },
            ];
        }

    if (triggerChar === ':' && /:\s*$/.test(before)) {
        return TYPES.map(t => ({ label: t, kind: CompletionItemKind.TypeParameter, detail: `type ${t}` }));
    }
    
    // Get symbols
    const docState = workspaceState.documents.get(params.textDocument.uri);
    const symbols = docState?.analysis?.symbols || [];
    
    // Snippets
    for (const [key, snip] of Object.entries(SNIPPETS)) {
        items.push({ label: snip.label, kind: CompletionItemKind.Snippet, detail: snip.documentation, insertText: snip.insertText, insertTextMode: 2 });
    }
    
    // Keywords
    for (const kw of KEYWORDS) items.push({ label: kw, kind: CompletionItemKind.Keyword, detail: 'keyword' });
    
    // Types
    for (const t of TYPES) items.push({ label: t, kind: CompletionItemKind.TypeParameter, detail: `type ${t}` });
    
    // Builtins
    for (const [name, b] of Object.entries(BUILTINS)) {
        items.push({
            label: name,
            kind: CompletionItemKind.Function,
            detail: b.sig,
            documentation: b.doc + (b.unsafe ? '\n\n⚠️ **unsafe** - must be inside unsafe { }' : ''),
            tags: b.unsafe ? [SymbolTag.Deprecated] : undefined
        });
    }
    
    // Module names (so `import kc` suggests `kcrypt`, `os`, ...)
    for (const modName of Object.keys(MODULES)) {
        items.push({ label: modName, kind: CompletionItemKind.Module, detail: `module ${modName}` });
    }

    // Local symbols
    for (const s of symbols) {
        const kind = s.kind === 'func' ? CompletionItemKind.Function :
                     s.kind === 'class' ? CompletionItemKind.Class :
                     s.kind === 'struct' ? CompletionItemKind.Struct :
                     s.kind === 'enum' ? CompletionItemKind.Enum : CompletionItemKind.Variable;
        items.push({ label: s.name, kind, detail: s.detail || s.kind });
    }
    
    return items.filter(item => !prefix || item.label.toLowerCase().startsWith(prefix)).slice(0, 100);
});

connection.onCompletionResolve(item => item);

// ── Hover ─────────────────────────────────────────────────────────────────────

connection.onHover(params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return null;
    
    const lines = doc.getText().split('\n');
    const word = wordAt(lines[params.position.line] || '', params.position.character);
    if (!word) return null;

    // Module member access (e.g. hovering `kcrypt.hash_password`)
    const hoverLine = lines[params.position.line] || '';
    const dotMatch = hoverLine.slice(0, params.position.character).match(/(\w+)\.(\w*)$/);
    if (dotMatch && MODULES[dotMatch[1]] && MODULES[dotMatch[1]][dotMatch[2]]) {
        const info = MODULES[dotMatch[1]][dotMatch[2]];
        return { contents: { kind: 'markdown', value: `\`\`\`kentscript\n${info.sig}\n\`\`\`\n\n${info.doc}` } };
    }

    if (BUILTINS[word]) {
        const b = BUILTINS[word];
        return { contents: { kind: 'markdown', value: `\`\`\`kentscript\n${b.sig}\n\`\`\`\n\n${b.doc}${b.unsafe ? '\n\n⚠️ **unsafe**' : ''}` } };
    }
    if (TYPES.includes(word)) return { contents: { kind: 'markdown', value: `\`\`\`kentscript\ntype ${word}\n\`\`\`` } };
    if (KEYWORDS.includes(word)) return { contents: { kind: 'markdown', value: `\`\`\`kentscript\n${word}\n\`\`\`\nKentScript keyword` } };
    
    const docState = workspaceState.documents.get(params.textDocument.uri);
    const symbols = docState?.analysis?.symbols || [];
    const sym = symbols.find(s => s.name === word);
    if (sym) return { contents: { kind: 'markdown', value: `\`\`\`kentscript\n${sym.detail || `${sym.kind} ${sym.name}`}\n\`\`\`` } };
    
    return null;
});

// ── Goto ─────────────────────────────────────────────────────────────────────

connection.onDefinition(params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return null;
    
    const lines = doc.getText().split('\n');
    const word = wordAt(lines[params.position.line] || '', params.position.character);
    if (!word) return null;
    
    const docState = workspaceState.documents.get(params.textDocument.uri);
    const symbols = docState?.analysis?.symbols || [];
    const sym = symbols.find(s => s.name === word);
    if (!sym) return null;
    
    return { uri: params.textDocument.uri, range: { start: { line: sym.line, character: 0 }, end: { line: sym.line, character: lines[sym.line]?.length || 0 } } };
});

connection.onTypeDefinition(params => connection.sendRequest('textDocument/definition', params));
connection.onImplementation(params => connection.sendRequest('textDocument/definition', params));

// ── References ─────────────────────────────────────────────────────────────

connection.onReferences(params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    
    const lines = doc.getText().split('\n');
    const word = wordAt(lines[params.position.line] || '', params.position.character);
    if (!word) return [];
    
    const refs = [];
    const re = new RegExp(`\\b${word}\\b`, 'g');
    lines.forEach((l, i) => {
        let m;
        while ((m = re.exec(l)) !== null) {
            refs.push({ uri: params.textDocument.uri, range: { start: { line: i, character: m.index }, end: { line: i, character: m.index + word.length } } });
        }
    });
    return refs;
});

// ── Symbols ───────────────────────────────────────────────────────────────────

connection.onDocumentSymbol(params => {
    const docState = workspaceState.documents.get(params.textDocument.uri);
    const symbols = docState?.analysis?.symbols || [];
    
    return symbols.map(s => {
        const kind = s.kind === 'func' ? SymbolKind.Function :
                     s.kind === 'class' ? SymbolKind.Class :
                     s.kind === 'struct' ? SymbolKind.Struct :
                     s.kind === 'enum' ? SymbolKind.Enum : SymbolKind.Variable;
        return { name: s.name, kind, detail: s.detail, range: { start: { line: s.line, character: 0 }, end: { line: s.line, character: 100 } }, selectionRange: { start: { line: s.line, character: 0 }, end: { line: s.line, character: s.name.length } } };
    });
});

connection.onWorkspaceSymbol(params => {
    const results = [];
    for (const [uri, doc] of documents.entries()) {
        const docState = workspaceState.documents.get(uri);
        const symbols = docState?.analysis?.symbols || [];
        for (const s of symbols) {
            if (s.name.toLowerCase().includes(params.query.toLowerCase())) {
                results.push({ name: s.name, kind: SymbolKind.Function, location: { uri, range: { start: { line: s.line, character: 0 }, end: { line: s.line, character: 100 } } }, containerName: '' });
            }
        }
    }
    return results;
});

// ── Semantic tokens ──────────────────────────────────────────────────────────

connection.onRequest(SemanticTokensRequest.method, params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return { data: [] };
    const docState = workspaceState.documents.get(params.textDocument.uri);
    return { data: computeSemanticTokens(doc.getText(), docState?.analysis?.symbols || []) };
});

// ── Inlay hints ─────────────────────────────────────────────────────────────

connection.onRequest(InlayHintRequest.method, params => {
    return [];
});

connection.onRequest(InlayHintResolveRequest.method, hint => hint);

// ── Call hierarchy ───────────────────────────────────────────────────────────

connection.onRequest(CallHierarchyPrepareRequest.method, async params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    const lines = doc.getText().split('\n');
    const word = wordAt(lines[params.position.line] || '', params.position.character);
    if (!word) return [];
    
    const docState = workspaceState.documents.get(params.textDocument.uri);
    const symbols = docState?.analysis?.symbols || [];
    const sym = symbols.find(s => s.name === word);
    if (!sym) return [];
    
    return [{ name: sym.name, kind: sym.kind === 'func' ? 12 : 13, uri: params.textDocument.uri, range: { start: { line: sym.line, character: 0 }, end: { line: sym.line, character: lines[sym.line]?.length || 0 } }, selectionRange: { start: { line: sym.line, character: 0 }, end: { line: sym.line, character: sym.name.length } } }];
});

connection.onRequest(CallHierarchyIncomingCallsRequest.method, () => []);
connection.onRequest(CallHierarchyOutgoingCallsRequest.method, () => []);

// ── Type hierarchy ───────────────────────────────────────────────────────────

connection.onRequest(TypeHierarchyPrepareRequest.method, async params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    const lines = doc.getText().split('\n');
    const word = wordAt(lines[params.position.line] || '', params.position.character);
    if (!word) return [];
    
    const docState = workspaceState.documents.get(params.textDocument.uri);
    const symbols = docState?.analysis?.symbols || [];
    const sym = symbols.find(s => s.name === word && ['class', 'struct', 'enum'].includes(s.kind));
    if (!sym) return [];
    
    return [{ name: sym.name, kind: sym.kind === 'class' ? 5 : 22, uri: params.textDocument.uri, range: { start: { line: sym.line, character: 0 }, end: { line: sym.line, character: lines[sym.line]?.length || 0 } }, selectionRange: { start: { line: sym.line, character: 0 }, end: { line: sym.line, character: sym.name.length } } }];
});

connection.onRequest(TypeHierarchySupertypesRequest.method, () => []);
connection.onRequest(TypeHierarchySubtypesRequest.method, () => []);

// ── Signature help ───────────────────────────────────────────────────────────

connection.onSignatureHelp(params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return null;
    
    const lines = doc.getText().split('\n');
    const before = (lines[params.position.line] || '').slice(0, params.position.character);
    const m = before.match(/(\w+)\s*\(([^)]*)$/);
    if (!m) return null;
    
    const funcName = m[1];
    const builtin = BUILTINS[funcName];
    if (!builtin) return null;
    
    const sigMatch = builtin.sig.match(/func\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*(\w+))?/);
    if (!sigMatch) return null;
    
    const [, name, paramsStr] = sigMatch;
    const paramsList = paramsStr.split(',').filter(p => p.trim()).map((p, i) => ({ label: p.trim().split(/\s*:\s*/)[0] || `param${i}`, documentation: '' }));
    
    return { signatures: [{ label: builtin.sig, documentation: builtin.doc, parameters: paramsList }], activeSignature: 0, activeParameter: Math.min((m[2].split(',').length - 1) || 0, paramsList.length - 1) };
});

// ── Folding ───────────────────────────────────────────────────────────────────

connection.onRequest(FoldingRangeRequest.method, params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    
    const lines = doc.getText().split('\n');
    const ranges = [];
    const stack = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const openBraces = (line.match(/\{/g) || []).length;
        const closeBraces = (line.match(/\}/g) || []).length;
        
        for (let j = 0; j < openBraces; j++) stack.push({ line: i, type: 'block' });
        for (let j = 0; j < closeBraces && stack.length; j++) {
            const start = stack.pop();
            if (i > start.line) ranges.push({ startLine: start.line, endLine: i, kind: 'region' });
        }
    }
    return ranges;
});

// ── Code actions ───────────────────────────────────────────────────────────────

connection.onCodeAction(params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    
    const text = doc.getText();
    const lines = text.split('\n');
    const actions = [];
    
    for (const d of params.context.diagnostics || []) {
        const lineText = lines[d.range.start.line] || '';
        
        if (d.message.includes('Undefined name')) {
            const match = d.message.match(/Undefined name '(\w+)'/);
            if (match) {
                actions.push({ title: `Create local variable '${match[1]}'`, kind: 'quickfix', edit: { changes: { [params.textDocument.uri]: [{ range: { start: { line: d.range.start.line, character: 0 }, end: { line: d.range.start.line, character: lineText.length } }, newText: `let ${match[1]} = \n${lineText}` }] } } });
            }
        }
        
        if (d.message.includes('unsafe') && !lineText.includes('unsafe')) {
            actions.push({ title: 'Wrap in unsafe { }', kind: 'quickfix', edit: { changes: { [params.textDocument.uri]: [{ range: { start: { line: d.range.start.line, character: 0 }, end: { line: d.range.start.line, character: lineText.length } }, newText: `unsafe { ${lineText.trim()} }` }] } } });
        }
    }
    
    actions.push({ title: 'Organize Imports', kind: 'source.organizeImports', command: { command: 'kentscript.organizeImports', title: 'Organize Imports' } });
    
    if (params.range.start.line !== params.range.end.line) {
        actions.push({ title: 'Extract to Function', kind: 'refactor.function', command: { command: 'kentscript.extractFunction', title: 'Extract Function' } });
    }
    
    return actions;
});

// ── Code lens ────────────────────────────────────────────────────────────────

connection.onRequest(CodeLensRequest.method, params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    
    const docState = workspaceState.documents.get(params.textDocument.uri);
    const symbols = docState?.analysis?.symbols || [];
    const lenses = [];
    
    for (const sym of symbols) {
        if (sym.name.startsWith('test_')) {
            lenses.push({ range: { start: { line: sym.line, character: 0 }, end: { line: sym.line, character: 10 } }, command: { command: 'kentscript.run', title: '▶ Run Test', arguments: [params.textDocument.uri, sym.name] } });
        }
    }
    return lenses;
});

connection.onRequest(CodeLensResolveRequest.method, lens => lens);

// ── Document links ───────────────────────────────────────────────────────────

connection.onRequest(DocumentLinkRequest.method, params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    
    const text = doc.getText();
    const links = [];
    const importRegex = /import\s+["']([^"']+)["']/g;
    let match;
    
    while ((match = importRegex.exec(text)) !== null) {
        const line = text.substring(0, match.index).split('\n').length - 1;
        const lineText = text.split('\n')[line];
        const start = lineText.indexOf(match[1]);
        links.push({ range: { start: { line, character: start }, end: { line, character: start + match[1].length } }, target: `file://${match[1]}.ks`, tooltip: `Open ${match[1]}` });
    }
    return links;
});

connection.onRequest(DocumentLinkResolveRequest.method, link => link);

// ── Selection range ───────────────────────────────────────────────────────────

connection.onRequest(SelectionRangeRequest.method, params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    
    const text = doc.getText();
    const lines = text.split('\n');
    const pos = params.position;
    const line = lines[pos.line];
    const ranges = [];
    
    const wordMatch = line.substring(0, pos.character).match(/\w+$/);
    if (wordMatch) ranges.push({ start: { line: pos.line, character: pos.character - wordMatch[0].length }, end: { line: pos.line, character: pos.character } });
    
    ranges.push({ start: { line: pos.line, character: 0 }, end: { line: pos.line, character: line.length } });
    
    return ranges;
});

// ── Linked editing ───────────────────────────────────────────────────────────

connection.onRequest(LinkedEditingRangeRequest.method, params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return null;
    
    const lines = doc.getText().split('\n');
    const word = wordAt(lines[params.position.line] || '', params.position.character);
    if (!word) return null;
    
    const ranges = [];
    lines.forEach((l, i) => {
        const re = new RegExp(`\\b${word}\\b`, 'g');
        let m;
        while ((m = re.exec(l)) !== null) ranges.push({ start: { line: i, character: m.index }, end: { line: i, character: m.index + word.length } });
    });
    
    return { ranges };
});

// ── Inline values ─────────────────────────────────────────────────────────────

connection.onRequest(InlineValueRequest.method, params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    
    const text = doc.getText();
    const lines = text.split('\n');
    const values = [];
    
    for (let i = 0; i < lines.length; i++) {
        const match = lines[i].match(/(let|const|mut)\s+(\w+)\s*=\s*(.+)/);
        if (match) {
            const value = match[3].trim();
            if (!value.includes('func') && !value.includes('=>')) {
                values.push({ range: { start: { line: i, character: 0 }, end: { line: i, character: lines[i].length } }, value, variableName: match[2] });
            }
        }
    }
    return values;
});

// ── Formatting ────────────────────────────────────────────────────────────────

connection.onDocumentFormatting(params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    
    const text = doc.getText();
    const lines = text.split('\n');
    const edits = [];
    const indent = ' '.repeat(params.options.tabSize || 4);
    let currentIndent = '';
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trimEnd();
        
        if (line.endsWith('{') || line.startsWith('case ') || line.startsWith('default:')) {
            edits.push({ range: { start: { line: i, character: 0 }, end: { line: i, character: line.length } }, newText: currentIndent + line });
            currentIndent += indent;
        } else if (line === '}' || line.startsWith('elif ') || line.startsWith('else')) {
            currentIndent = currentIndent.slice(0, -indent.length);
            edits.push({ range: { start: { line: i, character: 0 }, end: { line: i, character: line.length } }, newText: currentIndent + line });
        } else if (line.length > 0 && !line.startsWith(currentIndent) && !line.startsWith(' ') && !line.startsWith('#')) {
            edits.push({ range: { start: { line: i, character: 0 }, end: { line: i, character: line.length } }, newText: currentIndent + line });
        }
    }
    return edits;
});

connection.onDocumentRangeFormatting(params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return [];
    return [];
});

connection.onDocumentOnTypeFormatting(params => {
    return [];
});

// ── Rename ───────────────────────────────────────────────────────────────────

connection.onRenameRequest(params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return null;
    
    const text = doc.getText();
    const lines = text.split('\n');
    const word = wordAt(lines[params.position.line] || '', params.position.character);
    if (!word) return null;
    
    const changes = {};
    const uri = params.textDocument.uri;
    const edits = [];
    const re = new RegExp(`\\b${word}\\b`, 'g');
    
    lines.forEach((l, i) => {
        let m;
        while ((m = re.exec(l)) !== null) edits.push({ range: { start: { line: i, character: m.index }, end: { line: i, character: m.index + word.length } }, newText: params.newName });
    });
    
    changes[uri] = edits;
    return { changes };
});

connection.onRequest(PrepareRenameRequest.method, params => {
    const doc = documents.get(params.textDocument.uri);
    if (!doc) return null;
    
    const lines = doc.getText().split('\n');
    const word = wordAt(lines[params.position.line] || '', params.position.character);
    if (!word || KEYWORDS.includes(word) || TYPES.includes(word)) return null;
    
    return { range: { start: { line: params.position.line, character: params.position.character - word.length }, end: { line: params.position.line, character: params.position.character } }, placeholder: word };
});

// ── Execute command ──────────────────────────────────────────────────────────

connection.onExecuteCommand(async params => {
    const { command, arguments: args } = params;
    
    switch (command) {
        case 'kentscript.organizeImports': return { success: true };
        case 'kentscript.addImport': {
            const [uri, module] = args;
            const doc = documents.get(uri);
            if (!doc) return null;
            const text = doc.getText();
            const lines = text.split('\n');
            const insertIdx = lines.findIndex(l => !l.trim() || l.startsWith('import '));
            return { changes: { [uri]: [{ range: { start: { line: Math.max(0, insertIdx), character: 0 }, end: { line: Math.max(0, insertIdx), character: 0 } }, newText: `import ${module};\n` }] } };
        }
        case 'kentscript.extractFunction':
        case 'kentscript.extractVariable': return { success: true };
        default: return null;
    }
});

// ── Start ───────────────────────────────────────────────────────────────────

documents.listen(connection);
connection.listen();
connection.console.log('KentScript LSP initialized (synced with actual lexer/parser)');
