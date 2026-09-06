#!/usr/bin/env python3
"""
KentScript Binary Builder
Builds self-extracting installers for Linux, macOS, and Windows.
Usage:
    python3 build_binary.py              # Build for current platform
    python3 build_binary.py --platform linux   # Force Linux build
    python3 build_binary.py --platform macos   # Force macOS build
    python3 build_binary.py --platform windows # Force Windows build
    python3 build_binary.py --all        # Build all available platforms
"""
import argparse
import base64
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

VERSION = "3.1.0"
REPO_URL = "https://github.com/musikaalvin/kentscript"
BINARY_URL = f"{REPO_URL}/raw/main/kentscript"
MANIFEST_URL = f"{REPO_URL}/raw/main/manifest.json"

SHELL_HEADER = r'''#!/usr/bin/env bash
# ⚡ KentScript v{version} — Self-Extracting Binary
set -e
SCRIPT_PATH="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)/$(basename "${{BASH_SOURCE[0]}}")"
CACHE_DIR="${{HOME}}/.cache/kentscript"
KS_VERSION="{version}"
# The runtime cache dir is unique per build ({build_id} = payload hash), so a
# freshly built binary self-extracts once and later runs of the same binary
# reuse the cache — no boot noise on every launch.
KS_RUNTIME_DIR="${{CACHE_DIR}}/v{version}-{build_id}"

# Fast version query — answered in bash before Python starts
if [ "$1" = "--ks-version" ]; then echo "$KS_VERSION"; exit 0; fi

RED='\033[31m' GREEN='\033[32m' CYAN='\033[36m' BOLD='\033[1m' R='\033[0m'
header() {{ echo -e "\n${{BOLD}}${{CYAN}}════════════════════════════════════════${{R}}\n${{BOLD}}${{CYAN}}⚡ $*${{R}}\n${{BOLD}}${{CYAN}}════════════════════════════════════════${{R}}\n"; }}
progress_bar() {{
    local c=$1 w=50 pct=$(($1*100/$2)) f=$(($1*50/$2)) e=$((50-f))
    printf "\r["; printf "%${{f}}s"|tr ' ' '='; printf "%${{e}}s"|tr ' ' ' '; printf "] %d%%" "$pct"
}}

# Extract the runtime only on first install (first run for this version).
# On later runs the cache already exists, so we skip extraction — no boot noise.
# If the cache exists but is unusable (e.g. it was first created by root after a
# sudo install/run, leaving every file root-owned), repair it automatically so
# the lang keeps running for the normal user without a manual
# `sudo chown -R "$USER" ~/.cache/kentscript`.
ks_extract() {{
    PS=$(awk '/^__PAYLOAD__/{{print NR;exit}}' "$SCRIPT_PATH")
    [ -z "$PS" ] && {{ echo -e "${{RED}}✗ Corrupted binary${{R}}"; exit 1; }}
    # Announce the one-time extraction only on an interactive terminal so
    # captured output (e.g. the built-in IDE) never shows raw ANSI codes.
    if [ -t 1 ]; then
        echo -e "${{CYAN}}ℹ${{R}} Preparing KentScript runtime…"
    fi
    tail -n +$(($PS+1)) "$SCRIPT_PATH" | base64 -d | tar -xzf - -C "$1"
}}

cache_ok=0
if [ -d "$KS_RUNTIME_DIR" ] && [ -r "$KS_RUNTIME_DIR"/main.py ] \
   && [ -O "$KS_RUNTIME_DIR" ] && [ -w "$KS_RUNTIME_DIR" ]; then
    cache_ok=1
fi

# A root-owned cache is common after a sudo run — chown it back to the current
# user (direct when allowed, else via non-interactive sudo). Never let a broken
# cache silently brick the lang.
if [ "$cache_ok" != "1" ] && [ -e "$KS_RUNTIME_DIR" ]; then
    uid_now="$(id -u)"; gid_now="$(id -g)"
    {{ chown -R "$uid_now:$gid_now" "$CACHE_DIR" 2>/dev/null; }} \
        || {{ sudo -n chown -R "$uid_now:$gid_now" "$CACHE_DIR" 2>/dev/null; }} || true
    if [ -d "$KS_RUNTIME_DIR" ] && [ -r "$KS_RUNTIME_DIR"/main.py ] \
       && [ -O "$KS_RUNTIME_DIR" ] && [ -w "$KS_RUNTIME_DIR" ]; then
        cache_ok=1
    fi
fi

if [ "$cache_ok" != "1" ]; then
    mkdir -p "$CACHE_DIR" 2>/dev/null || true
    uid_now="${{uid_now:-$(id -u)}}"
    # Ownership could not be repaired and the canonical path belongs to another
    # user (or the cache dir itself is root-owned) — fall back to a user-private
    # copy so the lang still runs, instead of failing on every launch.
    use_private=0
    if [ -e "$KS_RUNTIME_DIR" ] && {{ [ ! -O "$KS_RUNTIME_DIR" ] || [ ! -w "$KS_RUNTIME_DIR" ]; }}; then
        use_private=1
    fi
    if [ -d "$CACHE_DIR" ] && [ ! -w "$CACHE_DIR" ]; then
        use_private=1
    fi
    if [ "$use_private" = "1" ]; then
        if [ -t 1 ]; then
            echo -e "${{CYAN}}ℹ${{R}} Runtime cache owned by another user — using a private copy…"
        fi
        KS_CACHE_PRIVATE="$CACHE_DIR-uid$uid_now"
        mkdir -p "$KS_CACHE_PRIVATE" 2>/dev/null || true
        KS_RUNTIME_DIR="$KS_CACHE_PRIVATE/v{version}-{build_id}"
    fi
    # Fresh install, or existing cache is corrupt/incomplete (main.py missing).
    if [ ! -d "$KS_RUNTIME_DIR" ] || [ ! -e "$KS_RUNTIME_DIR"/main.py ]; then
        if [ ! -d "$KS_RUNTIME_DIR" ] && ! mkdir -p "$KS_RUNTIME_DIR"; then
            echo -e "${{RED}}✗ Cannot prepare runtime cache (${{KS_RUNTIME_DIR}})${{R}}" >&2
            exit 1
        fi
        ks_extract "$KS_RUNTIME_DIR"
        if [ ! -e "$KS_RUNTIME_DIR"/main.py ]; then
            echo -e "${{RED}}✗ Failed to prepare runtime cache${{R}}" >&2
            exit 1
        fi
    fi
fi

export KS_RUNTIME_DIR
export PYTHONPATH="$KS_RUNTIME_DIR:${{PYTHONPATH:-}}"
exec python3 "$KS_RUNTIME_DIR/main.py" "$@"

__PAYLOAD__
'''

PYINSTALLER_SPEC = r'''# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('stdlib', 'stdlib'),
        ('compiler', 'compiler'),
        ('runtime', 'runtime'),
        ('include', 'include'),
    ],
    hiddenimports=[
        'ks', 'ks.build', 'ks.runtime', 'ks.interpreter',
        'ks.compiler_infra', 'ks.type_system', 'ks.kernel_os',
        'error_formatter', 'error_handler', 'lang',
        'compiler.lexer.lexer', 'compiler.parser.parser',
        'codegen.c_transpiler',
        'runtime.lowlevel_support',
        'runtime.memory.slab_allocator',
        'runtime.memory.memory',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', '_tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='kentscript',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='kentscript',
)
'''

INNO_SETUP = r'''; KentScript Installer for Windows
; Supports Windows 7, 8, 8.1, 10, 11
; Requires Inno Setup 5+ or 6+ to compile: https://jrsoftware.org/isdl.php

#define MyAppName "KentScript"
#define MyAppVersion "<<VER>>"
#define MyAppPublisher "pyLord"
#define MyAppURL "https://github.com/musikaalvin/kentscript"
#define MyAppExeName "kentscript.exe"

[Setup]
AppId={{"A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
AppPublisherURL={{#MyAppURL}}
DefaultDirName={{autopf}}\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
OutputDir=dist
OutputBaseFilename=KentScript-Setup-{{#MyAppVersion}}
Compression=lzma
SolidCompression=yes
ChangesEnvironment=yes
PrivilegesRequired=admin
SetupIconFile=kentscript.ico
UninstallDisplayIcon={{app}}\{{#MyAppExeName}}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
Name: "addtopath"; Description: "Add to PATH"; GroupDescription: "System:"

[Files]
Source: "dist\kentscript\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\{{#MyAppName}}"; Filename: "{{app}}\{{#MyAppExeName}}"
Name: "{{group}}\{{cm:UninstallProgram,{{#MyAppName}}}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\{{#MyAppName}}"; Filename: "{{app}}\{{#MyAppExeName}}"; Tasks: desktopicon

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{{olddata}};{{app}}"; Tasks: addtopath; Check: NeedsAddPath('{{app}}')

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

[Run]
Filename: "{{app}}\{{#MyAppExeName}}"; Description: "Launch {{#MyAppName}}"; Flags: nowait postinstall skipifsilent
'''

INSTALL_PS1 = r'''# KentScript v<<VER>> Installer for Windows
# Supports Windows 7, 8, 8.1, 10, 11
# Compatible with PowerShell 2.0+ (Windows 7 default)
# Run as Administrator: right-click -> Run with PowerShell

$Version = "<<VER>>"
$InstallDir = "$env:LOCALAPPDATA\KentScript"
$CacheDir = "$env:LOCALAPPDATA\KentScript\cache"
$BinaryUrl = "https://github.com/musikaalvin/kentscript/raw/main/kentscript-windows.exe"

Write-Host ""
Write-Host "============================================="
Write-Host "  KentScript v$Version Installer (Windows)"
Write-Host "============================================="
Write-Host ""

# Clean old cache versions
if (Test-Path $CacheDir) {
    Get-ChildItem $CacheDir -Directory -Filter "v*" | Where-Object { $_.Name -ne "v$Version" } | ForEach-Object {
        Write-Host "  Removing old cache: $($_.Name)"
        Remove-Item $_.FullName -Recurse -Force
    }
}

# Create install directory
Write-Host "[1/3] Creating install directory..."
if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}
Write-Host "  OK: $InstallDir"

# Download binary
Write-Host "[2/3] Downloading KentScript..."
$ExePath = Join-Path $InstallDir "kentscript.exe"
try {
    # Enable TLS 1.2 for GitHub (may fail on very old .NET, that's OK)
    try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

    $WebClient = New-Object System.Net.WebClient
    $WebClient.DownloadFile($BinaryUrl, $ExePath)
    $Size = (Get-Item $ExePath).Length
    Write-Host "  OK: Downloaded ($Size bytes)"
} catch {
    Write-Host "  FAILED: Download failed"
    Write-Host ""
    Write-Host "  Build from source instead:"
    Write-Host "    git clone --branch source https://github.com/musikaalvin/kentscript.git"
    Write-Host "    cd kentscript"
    Write-Host "    pip install pyinstaller"
    Write-Host "    python build_binary.py --platform windows"
    exit 1
}

# Add to PATH
Write-Host "[3/3] Adding to PATH..."
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$CurrentPath;$InstallDir", "User")
    Write-Host "  OK: Added to user PATH"
} else {
    Write-Host "  OK: Already in PATH"
}

Write-Host ""
Write-Host "============================================="
Write-Host "  KentScript v$Version installed!"
Write-Host "============================================="
Write-Host ""
Write-Host "  Restart your terminal, then:"
Write-Host "    kentscript run file.ks"
Write-Host "    kentscript build file.ks -O3"
Write-Host "    kentscript"
Write-Host ""
Write-Host "  Docs: https://github.com/musikaalvin/kentscript"
Write-Host ""
'''


def get_version():
    return VERSION


def get_repo_root():
    return Path(__file__).parent.resolve()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_payload(repo_root, tmp_dir):
    """Create tar.gz payload of source tree."""
    payload = tmp_dir / "payload.tar.gz"
    exclude = {".git", "__pycache__", "payload.tar.gz", "build", "dist",
               "*.pyc", ".DS_Store", "node_modules", "web-ide",
               "web-ide-src", ".opencode", "Cargo.lock", "target",
               "*.o", "*.so", "*.dylib", "kentscript"}
    def _filter(ti):
        # Skip the built binary itself and any cached bytecode (recursively),
        # otherwise the payload packs the previous binary into itself and balloons.
        if ti.name == "kentscript" or ti.name.endswith(".pyc") or "/__pycache__" in ti.name:
            return None
        return ti
    with tarfile.open(payload, "w:gz") as tar:
        for item in sorted(repo_root.iterdir()):
            if item.name in exclude:
                continue
            tar.add(item, arcname=item.name, filter=_filter)
    return payload


def build_linux(repo_root, output_dir):
    """Build Linux/macOS self-extracting bash binary."""
    print(f"\n{'='*60}")
    print(f"  Building Linux/macOS installer (v{VERSION})")
    print(f"{'='*60}\n")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        payload = make_payload(repo_root, tmp)
        payload_b64 = tmp / "payload_b64.txt"
        subprocess.run(["base64", str(payload)], stdout=open(payload_b64, "w"), check=True)

        build_id = sha256_file(payload)[:8]
        header = SHELL_HEADER.format(version=VERSION, build_id=build_id)
        out = output_dir / "kentscript"
        with open(out, "w") as f:
            f.write(header)
            with open(payload_b64) as pf:
                f.write(pf.read())
        out.chmod(0o755)

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"  ✔ Built: {out} ({size_mb:.1f} MB)")
    print(f"  ✔ SHA256: {sha256_file(out)[:16]}...")

    bundle_dist(repo_root, output_dir)
    return out


# Root files that should live in dist/ (the distributable bundle) rather than
# the repo root. Moved there by the build so dist/ is self-contained.
DIST_BUNDLE = ["macos", "windows", "install.sh", "kentscript", "LICENSE",
               "manifest.json", "README.md", "setup_vscodium.sh", "version.txt"]
# The build itself already writes these into dist/ with correct content — never
# let a (possibly stale) root copy clobber them; just drop the root copy.
BUILD_PRODUCED = {"kentscript", "manifest.json"}


def _move_into(src, dst):
    if os.path.isdir(src) and os.path.isdir(dst):
        for name in os.listdir(src):
            _move_into(os.path.join(src, name), os.path.join(dst, name))
        try:
            os.rmdir(src)
        except OSError:
            pass
    else:
        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        shutil.move(src, dst)


def bundle_dist(repo_root, output_dir):
    """Move the distributable support files from repo root into dist/."""
    print(f"\n  Bundling distributable files into dist/")
    for name in DIST_BUNDLE:
        src = repo_root / name
        if not src.exists():
            continue
        dst = output_dir / name
        if name in BUILD_PRODUCED and dst.exists():
            if src.is_dir():
                shutil.rmtree(src)
            else:
                os.remove(src)
            print(f"  → dist/{name} (build output kept; root copy removed)")
            continue
        _move_into(str(src), str(dst))
        print(f"  → dist/{name}")


def build_windows_installer(repo_root, output_dir):
    """Build Windows PyInstaller bundle + Inno Setup script."""
    print(f"\n{'='*60}")
    print(f"  Building Windows installer (v{VERSION})")
    print(f"{'='*60}\n")

    win_dir = output_dir / "windows"
    win_dir.mkdir(parents=True, exist_ok=True)

    # Write PyInstaller spec
    spec_path = repo_root / "kentscript.spec"
    spec_path.write_text(PYINSTALLER_SPEC)
    print(f"  ✔ Wrote kentscript.spec")

    # Write Inno Setup script
    iss_path = win_dir / "kentscript.iss"
    iss_path.write_text(INNO_SETUP.replace("<<VER>>", VERSION))
    print(f"  ✔ Wrote windows/kentscript.iss")

    # Write PowerShell installer
    ps1_path = win_dir / "install.ps1"
    ps1_path.write_text(INSTALL_PS1.replace("<<VER>>", VERSION))
    ps1_path.chmod(0o755)
    print(f"  ✔ Wrote windows/install.ps1")

    # Write Windows batch launcher
    bat_path = repo_root / "kentscript.bat"
    bat_path.write_text('@echo off\npython "%~dp0\\main.py" %*\n')
    print(f"  ✔ Wrote kentscript.bat")

    # Try to build with PyInstaller if available
    pyinstaller_ok = False
    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            pyinstaller_ok = True
    except Exception:
        pass

    if pyinstaller_ok:
        print("\n  Building PyInstaller bundle...")
        build_dir = repo_root / "build"
        dist_dir = repo_root / "dist"
        if build_dir.exists():
            shutil.rmtree(build_dir)
        if dist_dir.exists():
            shutil.rmtree(dist_dir)

        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", str(spec_path),
             "--distpath", str(dist_dir), "--workpath", str(build_dir),
             "--noconfirm"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            exe_path = dist_dir / "kentscript" / "kentscript.exe"
            if exe_path.exists():
                dest = output_dir / "kentscript-windows.exe"
                shutil.copy2(exe_path, dest)
                print(f"  ✔ Built: {dest} ({dest.stat().st_size / (1024*1024):.1f} MB)")
            else:
                print(f"  ⚠ PyInstaller ran but exe not found at {exe_path}")
        else:
            print(f"  ⚠ PyInstaller failed (run on Windows for best results)")
            print(f"    Error: {result.stderr[:200]}")
    else:
        print("  ℹ PyInstaller not available — spec + ISS files generated")
        print("    To build on Windows:")
        print("      pip install pyinstaller")
        print("      pyinstaller kentscript.spec")
        print("    Then compile installer.iss with Inno Setup")

    return win_dir


def build_macos_installer(repo_root, output_dir):
    """Build macOS .pkg installer script."""
    print(f"\n{'='*60}")
    print(f"  Building macOS installer (v{VERSION})")
    print(f"{'='*60}\n")

    mac_dir = output_dir / "macos"
    mac_dir.mkdir(parents=True, exist_ok=True)

    # macOS install script (uses Homebrew-style approach)
    install_mac = mac_dir / "install.sh"
    install_mac.write_text(f'''#!/usr/bin/env bash
# KentScript v{VERSION} macOS Installer
# Supports Intel (x86_64) and Apple Silicon (arm64)
set -e

VERSION="{VERSION}"
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
        [ -d "$old" ] && [ "$(basename "$old")" != "v$VERSION" ] && {{
            echo "  Removing old cache: $(basename "$old")"
            rm -rf "$old"
        }}
    done
fi

# Check dependencies
echo "Checking dependencies..."
command -v python3 &>/dev/null || {{
    echo "Python 3 required. Install with Homebrew:"
    echo "  brew install python3"
    exit 1
}}
echo "  ✔ Python $(python3 --version 2>&1 | awk '{{print $2}}')"

command -v gcc &>/dev/null || command -v clang &>/dev/null || {{
    echo "C compiler required. Install Xcode Command Line Tools:"
    echo "  xcode-select --install"
    exit 1
}}
echo "  ✔ C compiler found"

# Download binary
mkdir -p "$INSTALL_DIR" 2>/dev/null || true
# Don't leave the runtime cache root-owned when this script is run via sudo:
# the binary then fails to self-extract for the normal user on first run.
if [ "$(id -u)" = "0" ] && [ -n "${{SUDO_UID:-}}" ]; then
    mkdir -p "$CACHE_DIR" 2>/dev/null || true
    chown -R "$SUDO_UID:$(id -g "$SUDO_UID" 2>/dev/null || echo "$SUDO_UID")" "$CACHE_DIR" 2>/dev/null || true
fi

echo ""
echo "Downloading KentScript..."
    curl -fL --progress-bar -o "$INSTALL_DIR/kentscript" \\
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
''')
    install_mac.chmod(0o755)
    print(f"  ✔ Wrote macos/install.sh")

    # Homebrew formula (optional)
    formula = mac_dir / "kentscript.rb"
    formula.write_text(f'''class Kentscript < Formula
  desc "Systems programming language with C transpilation"
  homepage "{REPO_URL}"
  version "{VERSION}"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
      url "{BINARY_URL}"
    else
      url "{BINARY_URL}"
    end
  end

  def install
    bin.install "kentscript"
  end

  test do
    system "kentscript", "--ks-version"
  end
end
''')
    print(f"  ✔ Wrote macos/kentscript.rb (Homebrew formula)")

    return mac_dir


def build_all(repo_root, output_dir):
    """Build for all platforms."""
    results = {}
    results["linux"] = build_linux(repo_root, output_dir)
    results["macos"] = build_macos_installer(repo_root, output_dir)
    results["windows"] = build_windows_installer(repo_root, output_dir)
    return results


def main():
    parser = argparse.ArgumentParser(description="KentScript Binary Builder")
    parser.add_argument("--platform", choices=["linux", "macos", "windows"],
                        help="Target platform (default: current)")
    parser.add_argument("--all", action="store_true",
                        help="Build for all platforms")
    parser.add_argument("--output", "-o", default=None,
                        help="Output directory (default: dist/)")
    args = parser.parse_args()

    repo_root = get_repo_root()
    output_dir = Path(args.output) if args.output else repo_root / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"KentScript v{VERSION} Binary Builder")
    print(f"Source: {repo_root}")
    print(f"Output: {output_dir}")

    if args.all:
        results = build_all(repo_root, output_dir)
    elif args.platform:
        if args.platform == "linux":
            results = {"linux": build_linux(repo_root, output_dir)}
        elif args.platform == "macos":
            results = {"macos": build_macos_installer(repo_root, output_dir)}
        elif args.platform == "windows":
            results = {"windows": build_windows_installer(repo_root, output_dir)}
    else:
        # Auto-detect current platform
        system = platform.system().lower()
        if system == "linux":
            results = {"linux": build_linux(repo_root, output_dir)}
        elif system == "darwin":
            results = {"macos": build_macos_installer(repo_root, output_dir)}
        elif system == "windows":
            results = {"windows": build_windows_installer(repo_root, output_dir)}
        else:
            print(f"Unsupported platform: {system}")
            sys.exit(1)

    # Write manifest
    manifest = {
        "version": VERSION,
        "build_date": __import__("datetime").datetime.now().strftime("%Y-%m-%d"),
        "name": "KentScript",
        "platforms": {}
    }
    for plat, path in results.items():
        if path.exists() and path.is_file():
            manifest["platforms"][plat] = {
                "file": path.name,
                "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
                "sha256": sha256_file(path),
            }
        elif path.exists() and path.is_dir():
            manifest["platforms"][plat] = {
                "directory": str(path.relative_to(output_dir)),
            }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=4))
    print(f"\n  ✔ Manifest: {manifest_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Build complete — v{VERSION}")
    print(f"{'='*60}")
    for plat in results:
        print(f"  {plat:10s} → {output_dir / ('kentscript' if plat == 'linux' else plat)}")
    print(f"\n  Next: git add dist/ && git push origin main")
    print()


if __name__ == "__main__":
    main()
