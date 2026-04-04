# KentScript Language Server Protocol (LSP)

Language Server Protocol implementation for KentScript, providing IDE features in VSCode and other editors.

## Features

- ✅ **Syntax Highlighting** - Keywords, types, builtins
- ✅ **Auto-completion** - Keywords, types, functions
- ✅ **Hover Documentation** - Function signatures and descriptions
- ✅ **Diagnostics** - Real-time error checking
- ✅ **Unsafe Detection** - Warns about unsafe operations outside unsafe blocks
- ✅ **Semicolon Warnings** - Detects missing semicolons

## Installation

### 1. Install Dependencies
```bash
cd kentscript-lsp
npm install
```

### 2. Install VSCode Extension
```bash
cd ../vscode-kentscript
npm install
npm run compile
```

### 3. Install Extension in VSCode
```bash
code --install-extension vscode-kentscript-3.1.0.vsix
```

Or manually:
1. Open VSCode
2. Press `Ctrl+Shift+P`
3. Type "Install from VSIX"
4. Select `vscode-kentscript-3.1.0.vsix`

## Usage

1. Open any `.ks` file in VSCode
2. LSP will automatically start
3. Enjoy IDE features!

## Features in Detail

### Auto-completion
Type any keyword, type, or function name and get suggestions:
- Keywords: `let`, `const`, `func`, `unsafe`, etc.
- Types: `int`, `i64`, `str`, `bool`, etc.
- Builtins: `malloc`, `print`, `asm`, etc.

### Hover Documentation
Hover over any builtin function to see:
- Function signature
- Parameter types
- Return type
- Safety requirements

### Diagnostics
Real-time error checking:
- Missing semicolons
- Unsafe operations outside unsafe blocks
- Syntax errors

### Example

```kentscript
// Auto-complete suggests 'let'
let x = 42;

// Hover over 'malloc' shows documentation
unsafe {
    let ptr = malloc(1024);  // ✓ OK
}

malloc(1024);  // ✗ Error: requires unsafe block
```

## Configuration

Edit `.vscode/settings.json`:
```json
{
  "kentscript.lsp.enabled": true,
  "kentscript.lsp.trace.server": "verbose"
}
```

## Supported Editors

- ✅ VSCode
- ✅ VSCodium
- ✅ Any editor supporting LSP (Vim, Emacs, Sublime, etc.)

## Development

### Run LSP Server
```bash
node server.js --stdio
```

### Debug
```bash
node --inspect server.js --stdio
```

## Version

**3.1.0** - Stable

## License

MIT

## Author

pyLord (Musika Alvin) - Uganda
