# KentScript

A compiled systems-programming language with C transpilation, low-level
capabilities, and a full standard library. **Runs on Linux, macOS, and Windows 7+.**

## Quick Start

```bash
# Run a program
kentscript run program.ks

# Compile to a native binary
kentscript build program.ks -O3
./program

# Start the interactive REPL
kentscript

# Start the KSecurity pentest console
kentscript security
```

## Installation

### Prebuilt Installers (from `main` branch)

```bash
# Linux / macOS — one-liner
curl -fsSL https://github.com/musikaalvin/kentscript/raw/main/install.sh | bash

# Windows 7/8/10/11 (PowerShell 2.0+, as Administrator)
iex (New-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/musikaalvin/kentscript/main/windows/install.ps1')
```

Or grab the binary directly:

```bash
curl -fsSL -o kentscript https://github.com/musikaalvin/kentscript/raw/main/kentscript
chmod +x kentscript
sudo mv kentscript /usr/local/bin/
```

### Build from Source (this branch)

```bash
git clone --branch source https://github.com/musikaalvin/kentscript.git
cd kentscript
pip install -r requirements-build.txt
python3 build_binary.py --all        # builds to dist/
python3 build_binary.py              # build for current platform only
```

### VSCodium Extension

```bash
# After installing the binary:
bash setup_vscodium.sh    # auto-downloads from GitHub if not in source repo
```

Features: LSP completion, hover, live diagnostics, syntax highlighting (69 keywords, 26 types, 149 builtins), Run/Build/Debug commands.

### Branch Layout

| Branch | Contents |
|--------|----------|
| `main` | Installers & distribution: `kentscript` binary, `install.sh`, `setup_vscodium.sh`, `windows/`, `macos/`, `LICENSE`, `README.md` |
| `source` | Full source code, `build_binary.py`, compiler, runtime, stdlib, docs |

## Documentation

- [Full Guide (v3.1.0)](DOCS/KENTSCRIPT_v3.1.0_GUIDE.md)

## Platform Support

| Feature | Linux | macOS | Windows 7+ |
|---------|-------|-------|------------|
| Interpreter | ✅ | ✅ | ✅ |
| C Transpiler | ✅ (gcc/clang) | ✅ (clang) | ✅ (gcc/cl.exe) |
| Syscalls | ✅ (libc) | ✅ (libsystem_kernel) | ✅ (ntdll Nt*) |
| Inline Assembly | ✅ (x86-64/ARM64) | ✅ (ARM64/x86-64) | ✅ (x86-64) |
| Hardware I/O | ✅ (root) | N/A (ARM) | N/A |
| MMIO | ✅ (root) | Returns 0 | Returns 0 |
| WASM Backend | ✅ | ✅ | ✅ |

## Features

- **Two execution modes**: interpreter (full stdlib) or native compilation (low-level)
- **Cross-platform**: Linux, macOS, Windows — syscalls, asm, C transpiler all work
- **Pattern matching**: expressive match/case statements
- **Classes & OOP**: full object-oriented programming
- **Async/await**: built-in concurrency
- **Low-level features**: unsafe blocks, pointers, inline assembly, raw syscalls
- **Standard library**: 70+ modules — math, file I/O, networking, crypto, hardware
- **KSecurity**: built-in pentest console with module registry and autocomplete
- **Editors**: VSCodium extension with syntax highlighting + LSP (completion, hover, diagnostics)

## Example

```kentscript
:: Pattern matching
match x {
    case 1: { print("one"); }
    case 2: { print("two"); }
    default: { print("other"); }
}

:: Cross-platform syscall
unsafe {
    let pid = syscall(39, 0, 0, 0, 0, 0, 0);
    print("PID: " + str(pid));
}

:: Classes
class Point {
    init(self, x, y) {
        self.x = x;
        self.y = y;
    }
}
```

## Mode Comparison

| Feature | Interpreter | Native |
|---------|-------------|--------|
| Full stdlib | ✅ | ✅ |
| Classes/OOP | ✅ | ✅ |
| Pattern matching | ✅ | ✅ |
| Unsafe/pointer | ✅ | ✅ |
| Inline assembly | ✅ | ✅ |
| Syscalls | ✅ (all platforms) | ✅ (all platforms) |

## Version

KentScript v3.1.0 — by pyLord

## License

MIT — see [LICENSE](LICENSE).
