# KentScript VSCode / VSCodium Extension

Official editor extension for the KentScript systems programming language
(`kentscript`). Provides syntax highlighting, a language server (completion,
hover, live diagnostics), and editor commands to run, build, and debug `.ks`
files.

## Features

### Syntax Highlighting
- Keywords, types, and builtins are generated from the **real compiler**
  (`kentscript-lsp/langdata.py` extracts them from `compiler/lexer/lexer.py`
  and the standard library), so the grammar never drifts from the language.
- Comments: `::` (line) and `/* */` (block)
- Strings: regular, single-quoted, and `f"..."` interpolated
- Numbers: decimal, hex (`0x`), binary (`0b`), octal (`0o`)
- Unsafe operations (`malloc`, `ptr_read`, `asm`, `mmio_read`, …) highlighted distinctly

### Language Server (LSP)
- **Completion** — keywords, types, builtins, code snippets, and module
  member completion (e.g. type `simd.` or `os.` to see that module's API).
- **Hover** — function signatures and documentation.
- **Diagnostics** — real-time errors and warnings as you type / on save.
- The server auto-discovers language data from the compiler and stdlib; no
  manual list to maintain.

### Editor Commands
Open the Command Palette (`Ctrl+Shift+P`) and type `KentScript`:
- `KentScript: Run` — `kentscript run <file>`
- `KentScript: Run with Arguments`
- `KentScript: Build (native)` — `kentscript build -O3`
- `KentScript: Build Release (PGO)` — `kentscript build --release -O3`
- `KentScript: Debug` — `kentscript debug <file>`
- `KentScript: System Info` — `kentscript info`
- `KentScript: Show Version`
- `KentScript: New File` — scaffold a `.ks` file
- `KentScript: Open Documentation`
- `KentScript: Restart Language Server`

### Keybindings
- `Ctrl+F5` — Run
- `Ctrl+Shift+B` — Build
- `F5` — Debug
- (macOS: `Cmd` instead of `Ctrl`)
- Right-click context menu in the editor and file explorer.

## Installation

The easiest path is the bundled installer:

```bash
./setup_vscodium.sh
```

This copies the extension (plus the `kentscript-lsp` server and its
`langdata.py`) into `~/.vscode-oss/extensions/pylord.vscode-kentscript-3.2.0`
and registers it. **No TypeScript build step is required** — the extension
ships as plain JavaScript (`extension.js`). If `vscode-languageclient` is
installed it is used automatically; otherwise a built-in minimal LSP client
is used, so IntelliSense works either way.

Manual build (optional):

```bash
cd vscode-kentscript
npm install
npm run compile   # produces out/extension.js (unused by default)
```

## Configuration

`.vscode/settings.json`:

```json
{
  "kentscript.executablePath": "kentscript",
  "kentscript.pythonPath": "python3",
  "kentscript.lspServerPath": "",
  "kentscript.lsp.enabled": true
}
```

- `executablePath` — the `kentscript` CLI wrapper (default: resolved from PATH).
- `pythonPath` — Python used by the LSP server to regenerate language data.
- `lspServerPath` — override path to `kentscript-lsp/server.js` (defaults to
  `../kentscript-lsp/server.js` next to the extension).
- `lsp.enabled` — toggle the language server.

## Requirements
- VSCodium / VSCode 1.75.0+
- The `kentscript` CLI on PATH (or set `kentscript.executablePath`)
- Python 3 (for the LSP server's language-data generation)

## Release Notes

### 3.2.0
- Extension rewritten as self-contained JavaScript (no build step needed).
- LSP language data auto-synced from the real compiler + stdlib via
  `langdata.py`.
- Module member completion (`simd.`, `os.`, `gpu.`, `math.`, …).
- Commands: Run, Run with Args, Build, Build Release, Debug, Info, Version,
  New File, Open Docs, Restart LSP.
- Grammar regenerated from the canonical keyword/type/builtin lists.

### 3.1.0
- Initial release: syntax highlighting, basic completion, hover, diagnostics.

## License
MIT — pyLord
