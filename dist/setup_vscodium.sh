#!/bin/bash
set -e

REPO_URL="https://github.com/musikaalvin/kentscript"
EXT_VERSION="3.1.0"
EXT_DEST="$HOME/.vscode-oss/extensions/pylord.vscode-kentscript-$EXT_VERSION"
TMP_DIR=$(mktemp -d)

R='\033[0m'; BOLD='\033[1m'; DIM='\033[2m'
GREEN='\033[92m'; CYAN='\033[96m'; YELLOW='\033[93m'; RED='\033[91m'; WHITE='\033[97m'

log()  { echo -e "${GREEN}✔${R}  $*"; }
info() { echo -e "${CYAN}ℹ${R}  $*"; }
warn() { echo -e "${YELLOW}⚠${R}  $*"; }
err()  { echo -e "${RED}✘${R}  $*"; exit 1; }

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

echo ""
echo -e "${BOLD}${CYAN}════════════════════════════════════════${R}"
echo -e "${BOLD}${CYAN}  ⚡ KentScript VSCodium Extension v${EXT_VERSION}${R}"
echo -e "${BOLD}${CYAN}════════════════════════════════════════${R}"
echo ""

# ── Check dependencies ──────────────────────────────────────────────────────
command -v npm &>/dev/null || err "npm required: sudo apt install npm"
command -v node &>/dev/null || err "node required: sudo apt install nodejs"
command -v python3 &>/dev/null || err "python3 required: sudo apt install python3"

# ── Check VSCodium ──────────────────────────────────────────────────────────
if [ ! -d "$HOME/.vscode-oss" ]; then
    if [ -d "$HOME/.vscode" ]; then
        warn "VSCodium not found, but VSCode detected at ~/.vscode"
        echo -e "  ${YELLOW}This script is for VSCodium (open-source). For VSCode, install from marketplace.${R}"
        echo ""
        echo -ne "  Continue anyway? [y/N] "
        read -r ans
        [[ "$ans" =~ ^[Yy]$ ]] || exit 0
        EXT_DEST="$HOME/.vscode/extensions/pylord.vscode-kentscript-$EXT_VERSION"
    else
        err "VSCodium not found. Install: https://vscodium.com"
    fi
fi

# ── Detect source or download ───────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -d "$SCRIPT_DIR/vscode-kentscript" ] && [ -d "$SCRIPT_DIR/kentscript-lsp" ]; then
    info "Running from source repo — using local files"
    EXT_SRC="$SCRIPT_DIR/vscode-kentscript"
    LSP_SRC="$SCRIPT_DIR/kentscript-lsp"
    USE_LOCAL=true
else
    info "Downloading from GitHub..."
    USE_LOCAL=false

    info "Fetching vscode-kentscript..."
    curl -sL "$REPO_URL/archive/refs/heads/source.zip" -o "$TMP_DIR/source.zip" 2>/dev/null || err "Download failed"
    cd "$TMP_DIR" && unzip -q source.zip 2>/dev/null || err "Unzip failed"
    SRC_DIR="$TMP_DIR/kentscript-source"
    # GitHub archives extract as repo-branchname
    mv "$TMP_DIR"/kentscript-* "$SRC_DIR" 2>/dev/null || mv "$TMP_DIR"/*/ "$SRC_DIR" 2>/dev/null || true

    EXT_SRC="$SRC_DIR/vscode-kentscript"
    LSP_SRC="$SRC_DIR/kentscript-lsp"

    [ -d "$EXT_SRC" ] || err "vscode-kentscript not found in downloaded source"
    [ -d "$LSP_SRC" ] || err "kentscript-lsp not found in downloaded source"
fi

# ── Step 1: Install npm deps ────────────────────────────────────────────────
echo -e "\n${BOLD}  Step 1/5:${R} Installing dependencies"
cd "$EXT_SRC" && npm install --silent 2>/dev/null && log "Extension deps installed"
cd "$LSP_SRC" && npm install --silent 2>/dev/null && log "LSP deps installed"

# ── Step 2: Compile TypeScript ──────────────────────────────────────────────
echo -e "\n${BOLD}  Step 2/5:${R} Building extension"
if [ -f "$EXT_SRC/node_modules/typescript/lib/tsc.js" ]; then
    node "$EXT_SRC/node_modules/typescript/lib/tsc.js" -p "$EXT_SRC/tsconfig.json" 2>/dev/null && log "TypeScript compiled" || warn "tsc skipped — using bundled extension.js"
else
    log "Using bundled extension.js (no tsc needed)"
fi

# ── Step 3: Copy files ──────────────────────────────────────────────────────
echo -e "\n${BOLD}  Step 3/5:${R} Installing to VSCodium"
rm -rf "$EXT_DEST"
mkdir -p "$EXT_DEST"
cp -r "$EXT_SRC"/. "$EXT_DEST/"

mkdir -p "$EXT_DEST/kentscript-lsp"
cp "$LSP_SRC/server.js" "$EXT_DEST/kentscript-lsp/"
cp "$LSP_SRC/analyze.py" "$EXT_DEST/kentscript-lsp/"
cp "$LSP_SRC/langdata.py" "$EXT_DEST/kentscript-lsp/"
cp "$LSP_SRC/package.json" "$EXT_DEST/kentscript-lsp/" 2>/dev/null || true
if [ -d "$LSP_SRC/node_modules" ]; then
    cp -r "$LSP_SRC/node_modules" "$EXT_DEST/kentscript-lsp/"
fi
log "Files installed to $EXT_DEST"

# ── Step 4: Install extension node_modules ──────────────────────────────────
echo -e "\n${BOLD}  Step 4/5:${R} Installing extension runtime deps"
cd "$EXT_DEST"
rm -rf node_modules package-lock.json
npm install --silent 2>/dev/null && log "Extension deps ready"

# ── Step 5: Fix permissions and register ────────────────────────────────────
echo -e "\n${BOLD}  Step 5/5:${R} Registering extension"
chmod -R o+rX "$EXT_DEST" 2>/dev/null || true
chmod -R g+rX "$EXT_DEST" 2>/dev/null || true
chmod +x "$EXT_DEST/kentscript-lsp/server.js" 2>/dev/null || true

python3 -c "
import json, os, time

ext_json_path = os.path.expanduser('$HOME/.vscode-oss/extensions/extensions.json')
if not os.path.exists(ext_json_path):
    alt = os.path.expanduser('$HOME/.vscode/extensions/extensions.json')
    if os.path.exists(alt):
        ext_json_path = alt
    else:
        os.makedirs(os.path.dirname(ext_json_path), exist_ok=True)

ext_id = 'pylord.vscode-kentscript'
ext_path = os.path.expanduser('$EXT_DEST')

extensions = []
if os.path.exists(ext_json_path):
    with open(ext_json_path) as f:
        extensions = json.load(f)

extensions = [e for e in extensions if e.get('identifier', {}).get('id') != ext_id]

extensions.append({
    'identifier': {'id': ext_id},
    'version': '$EXT_VERSION',
    'location': {
        '\$mid': 1,
        'fsPath': ext_path,
        'external': 'file://' + ext_path,
        'path': ext_path,
        'scheme': 'file'
    },
    'relativeLocation': 'pylord.vscode-kentscript-$EXT_VERSION',
    'metadata': {
        'installedTimestamp': int(time.time() * 1000),
        'pinned': False,
        'source': 'local',
        'publisherDisplayName': 'pyLord',
        'targetPlatform': 'universal',
        'updated': False,
        'private': False,
        'isPreReleaseVersion': False,
        'hasPrePreReleaseVersion': False
    }
})

with open(ext_json_path, 'w') as f:
    json.dump(extensions, f, indent=2)
print('    Extension registered')
"

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════${R}"
echo -e "${BOLD}${GREEN}  ✔  KentScript Extension Installed${R}"
echo -e "${GREEN}════════════════════════════════════════${R}"
echo ""
echo -e "  ${BOLD}Features:${R}"
echo -e "  ${CYAN}·${R}  LSP: completion, hover, live diagnostics"
echo -e "  ${CYAN}·${R}  Syntax: all 69 keywords, 26 types, 149 builtins, unsafe ops"
echo -e "  ${CYAN}·${R}  Commands: Run, Build, Debug, Info, Version, Restart LSP"
echo -e "  ${CYAN}·${R}  Keybindings: Ctrl+F5 (run), Ctrl+Shift+B (build), F5 (debug)"
echo ""
echo -e "  ${DIM}Restart VSCodium to activate.${R}"
echo ""
