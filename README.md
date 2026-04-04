# KentScript

A systems programming language with C transpilation, low-level capabilities, and standard library support.

## Quick Start

```bash
# Run with interpreter (full stdlib support)
./kentscript run examples/basics.ks

# Compile to native binary
./kentscript build examples/basics.ks -O3
./basics

# Interactive REPL
./kentscript repl
```

## Installation

```bash
pip install -r requirements-build.txt
chmod +x kentscript
```

## Documentation

- [Full Guide](docs/KENTSCRIPT_v3.1.0_GUIDE.md)

## Features

- **Two Execution Modes**: Interpreter (full stdlib) or Native compilation (low-level)
- **Pattern Matching**: Expressive match/case statements
- **Classes & OOP**: Full object-oriented programming
- **Async/Await**: Built-in concurrency
- **Low-Level Features**: Unsafe blocks, pointers, inline assembly, syscalls
- **Standard Library**: Math, file I/O, networking, crypto (interpreter mode)
- **VSCode Extension**: Syntax highlighting and LSP support

## Examples

```kentscript
:: Pattern matching
match x {
    case 1: { print("one"); }
    case 2: { print("two"); }
    default: { print("other"); }
}

:: Classes
class Point {
    init(self, x, y) {
        self.x = x;
        self.y = y;
    }
}

:: Low-level memory
unsafe {
    let ptr = malloc(1024);
    ptr_write(ptr, 42, 8);
    let val = ptr_read(ptr);
    free(ptr);
}
```

## Mode Comparison

| Feature | Interpreter | Native |
|---------|-------------|--------|
| Full Stdlib | ✅ | ❌ |
| Classes/OOP | ✅ | ✅ |
| Pattern Matching | ✅ | ✅ |
| Unsafe/Pointer | ✅ | ✅ |
| Inline Assembly | ✅ | ✅ |

## Version

KentScript v3.1.0 - Created 1st March 2026 by pyLord (Uganda)

## License

MIT