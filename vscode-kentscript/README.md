# KentScript VSCode Extension

Official VSCode extension for KentScript programming language.

## Features

### Syntax Highlighting
- Keywords: `let`, `const`, `func`, `unsafe`, etc.
- Types: `int`, `i64`, `str`, `bool`, etc.
- Comments: `::` and `/* */`
- Strings: Regular and f-strings
- Numbers: Decimal, hex, binary, octal

### Auto-completion
- Keywords
- Types
- Built-in functions
- Context-aware suggestions

### Hover Documentation
- Function signatures
- Type information
- Safety requirements

### Diagnostics
- Real-time error checking
- Missing semicolon warnings
- Unsafe operation detection

### Code Snippets
- `func` - Function declaration
- `unsafe` - Unsafe block
- `for` - For loop
- `if` - If statement

## Installation

### From VSIX
1. Download `vscode-kentscript-3.1.0.vsix`
2. Open VSCode
3. Press `Ctrl+Shift+P`
4. Type "Install from VSIX"
5. Select the downloaded file

### From Source
```bash
cd vscode-kentscript
npm install
npm run compile
code --install-extension .
```

## Usage

1. Open any `.ks` file
2. Extension activates automatically
3. Enjoy IDE features!

## Configuration

`.vscode/settings.json`:
```json
{
  "kentscript.lsp.enabled": true,
  "editor.formatOnSave": true,
  "editor.tabSize": 4
}
```

## Keyboard Shortcuts

- `Ctrl+Space` - Trigger completion
- `Ctrl+Shift+Space` - Trigger parameter hints
- `F12` - Go to definition
- `Shift+F12` - Find references

## Example

```kentscript
:: KentScript example with syntax highlighting
let x: int = 42;
let msg = f"Value: {x}";

func fibonacci(n: int) -> int {
    if n <= 1 {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}

unsafe {
    let ptr = malloc(1024);
    ptr_write(ptr, 0x42);
    free(ptr);
}
```

## Requirements

- VSCode 1.75.0 or higher
- Node.js 18.0.0 or higher (for LSP)

## Known Issues

None currently.

## Release Notes

### 3.1.0
- Initial release
- Syntax highlighting
- Auto-completion
- Hover documentation
- Diagnostics
- LSP integration

## License

MIT

## Author

pyLord (Musika Alvin) - Uganda
