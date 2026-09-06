#!/usr/bin/env bash
# KentScript v3.1.0 macOS Installer
# Supports Intel (x86_64) and Apple Silicon (arm64)
set -e

VERSION="3.1.0"
CACHE_DIR="$HOME/.cache/kentscript"
INSTALL_DIR="/usr/local/bin"

# Detect architecture
ARCH="$(uname -m)"
if [ "$ARCH" = "arm64" ]; then
    ARCH_LABEL="Apple Silicon (arm64)"
else
    ARCH_LABEL="Intel (x86_64)"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ⚡  KentScript v$VERSION Installer (macOS $ARCH_LABEL)"
echo "═══════════════════════════════════════════════════════"
echo ""

# Clean old cache versions
if [ -d "$CACHE_DIR" ]; then
    for old in "$CACHE_DIR"/v*; do
        [ -d "$old" ] && [ "$(basename "$old")" != "v$VERSION" ] && {
            echo "  Removing old cache: $(basename "$old")"
            rm -rf "$old"
        }
    done
fi

# Check dependencies
echo "Checking dependencies..."
command -v python3 &>/dev/null || {
    echo "Python 3 required. Install with Homebrew:"
    echo "  brew install python3"
    exit 1
}
echo "  ✔ Python $(python3 --version 2>&1 | awk '{print $2}')"

command -v gcc &>/dev/null || command -v clang &>/dev/null || {
    echo "C compiler required. Install Xcode Command Line Tools:"
    echo "  xcode-select --install"
    exit 1
}
echo "  ✔ C compiler found"

# Download binary
mkdir -p "$INSTALL_DIR" 2>/dev/null || true
# Don't leave the runtime cache root-owned when this script is run via sudo:
# the binary then fails to self-extract for the normal user on first run.
if [ "$(id -u)" = "0" ] && [ -n "${SUDO_UID:-}" ]; then
    mkdir -p "$CACHE_DIR" 2>/dev/null || true
    chown -R "$SUDO_UID:$(id -g "$SUDO_UID" 2>/dev/null || echo "$SUDO_UID")" "$CACHE_DIR" 2>/dev/null || true
fi

echo ""
echo "Downloading KentScript..."
    curl -fL --progress-bar -o "$INSTALL_DIR/kentscript" \
    "https://github.com/musikaalvin/kentscript/raw/main/kentscript"
chmod +x "$INSTALL_DIR/kentscript"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✔  Installed: $INSTALL_DIR/kentscript"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "  Quick start:"
echo "    kentscript run file.ks"
echo "    kentscript build file.ks -O3"
echo "    kentscript"
echo ""
echo "  Docs: https://github.com/musikaalvin/kentscript"
echo ""
