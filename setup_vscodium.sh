#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_SRC="$SCRIPT_DIR/vscode-kentscript"
LSP_SRC="$SCRIPT_DIR/kentscript-lsp"
EXT_DEST="$HOME/.vscode-oss/extensions/pylord.vscode-kentscript-3.2.0"

echo "==> Installing KentScript VSCodium extension v3.2.0..."

# 1. Install npm deps
echo "  -> Installing extension deps..."
cd "$EXT_SRC" && npm install --silent 2>/dev/null
echo "  -> Installing LSP deps..."
cd "$LSP_SRC" && npm install --silent 2>/dev/null

# 2. Make LSP server executable
echo "  -> Fixing LSP server permissions..."
chmod +x "$LSP_SRC/server.js" 2>/dev/null || true

# 3. Compile TypeScript extension
echo "  -> Compiling TypeScript extension..."
node "$EXT_SRC/node_modules/typescript/lib/tsc.js" -p "$EXT_SRC/tsconfig.json"

# 4. Clean destination and copy files
echo "  -> Installing to VSCodium..."
rm -rf "$EXT_DEST"
mkdir -p "$EXT_DEST"
cp -r "$EXT_SRC"/. "$EXT_DEST/"

# Copy LSP server next to the extension
mkdir -p "$EXT_DEST/kentscript-lsp"
cp -r "$LSP_SRC/server.js" "$EXT_DEST/kentscript-lsp/"
cp -r "$LSP_SRC/analyze.py" "$EXT_DEST/kentscript-lsp/"
if [ -d "$LSP_SRC/node_modules" ]; then
    cp -r "$LSP_SRC/node_modules" "$EXT_DEST/kentscript-lsp/"
fi

# 5. Reinstall node_modules fresh (ensures all transitive deps are complete)
echo "  -> Installing extension dependencies..."
cd "$EXT_DEST"
rm -rf node_modules package-lock.json
npm install --silent 2>/dev/null

# 6. Fix file permissions so VSCodium can read everything
echo "  -> Fixing permissions..."
chmod -R o+rX "$EXT_DEST" 2>/dev/null || true
chmod -R g+rX "$EXT_DEST" 2>/dev/null || true

# 7. Register extension in VSCodium's extensions.json
echo "  -> Registering extension in VSCodium..."
python3 -c "
import json, os, time

ext_json_path = os.path.expanduser('$HOME/.vscode-oss/extensions/extensions.json')
ext_id = 'pylord.vscode-kentscript'
ext_version = '3.2.0'
ext_rel = 'pylord.vscode-kentscript-3.2.0'
ext_path = os.path.expanduser('$EXT_DEST')

if os.path.exists(ext_json_path):
    with open(ext_json_path) as f:
        extensions = json.load(f)
else:
    extensions = []

# Remove old entry if exists
extensions = [e for e in extensions if e.get('identifier', {}).get('id') != ext_id]

extensions.append({
    'identifier': {'id': ext_id},
    'version': ext_version,
    'location': {
        '\$mid': 1,
        'fsPath': ext_path,
        'external': 'file://' + ext_path,
        'path': ext_path,
        'scheme': 'file'
    },
    'relativeLocation': ext_rel,
    'metadata': {
        'installedTimestamp': int(time.time() * 1000),
        'pinned': False,
        'source': 'local',
        'publisherDisplayName': 'pyLord',
        'targetPlatform': 'universal',
        'updated': False,
        'private': False,
        'isPreReleaseVersion': False,
        'hasPreReleaseVersion': False
    }
})

with open(ext_json_path, 'w') as f:
    json.dump(extensions, f, indent=2)
print('    Extension registered')
"

echo ""
echo "==> Done! Restart VSCodium."
echo "    - All 30+ commands available in Ctrl+Shift+P"
echo "    - Run/Build/Debug buttons in editor title bar"
echo "    - Right-click context menu with all run options"
echo "    - LSP: IntelliSense, go-to-definition, rename, diagnostics"
echo "    - LSP: Semantic highlighting, folding, code actions"
echo "    - Auto-discovers KentScript binary from project/workspace"
