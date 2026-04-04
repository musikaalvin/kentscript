#!/usr/bin/env python3
"""
KentScript System Installer
Installs KentScript and all support files system-wide
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    print("=" * 60)
    print("KentScript System Installer v3.1.0")
    print("=" * 60)
    
    # Determine installation paths
    if os.name == 'nt':
        install_dir = Path(os.environ.get('LOCALAPPDATA', 'C:\\Program Files')) / 'KentScript'
    else:
        install_dir = Path.home() / '.local' / 'share' / 'kentscript'
    
    print(f"\nInstalling to: {install_dir}")
    
    # Get source directory
    src_dir = Path(__file__).parent.resolve()
    
    # Create installation directory
    print("\n[1/5] Creating installation directory...")
    install_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy KentScript files
    print("[2/5] Copying KentScript files...")
    items_to_copy = [
        'main.py', 'ks_core.py', 'error_formatter.py', 'error_handler.py',
        'setup.py', 'compiler', 'runtime', 'stdlib', 'include', 'tools',
        'examples', 'docs', 'backends', 'codegen', 'archive', 'minios',
        'kentscript-lsp', 'vscode-kentscript'
    ]
    
    for item in items_to_copy:
        src_path = src_dir / item
        if src_path.exists():
            dst_path = install_dir / item
            if src_path.is_dir():
                if dst_path.exists():
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
                print(f"  Copied: {item}/")
            else:
                shutil.copy2(src_path, dst_path)
                print(f"  Copied: {item}")
    
    # Install LSP dependencies
    print("\n[2b/5] Installing LSP dependencies...")
    lsp_dir = install_dir / 'kentscript-lsp'
    if lsp_dir.exists():
        # Remove old node_modules to ensure clean install
        if (lsp_dir / 'node_modules').exists():
            shutil.rmtree(lsp_dir / 'node_modules')
        if (lsp_dir / 'package-lock.json').exists():
            (lsp_dir / 'package-lock.json').unlink()
        subprocess.run(['npm', 'install'], cwd=lsp_dir, capture_output=True)
        print("  LSP dependencies installed")
    
    # Install Python package
    print("\n[3/5] Installing Python package...")
    os.chdir(install_dir)
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '--user', '-e', '.'],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  Python package installed successfully")
    else:
        print(f"  Warning: {result.stderr}")
    
    # Create launcher scripts
    print("\n[4/5] Creating launcher scripts...")
    
    # Linux launcher
    if os.name != 'nt':
        bin_dir = Path.home() / '.local' / 'bin'
        bin_dir.mkdir(parents=True, exist_ok=True)
        
        launcher = bin_dir / 'kentscript'
        launcher.write_text(f'''#!/bin/bash
cd "{install_dir}"
exec python3 "{install_dir}/main.py" "$@"
''')
        launcher.chmod(0o755)
        print(f"  Created: {launcher}")
        
        # Also copy extension to codium
        ext_dir = Path.home() / '.local' / 'share' / 'codium' / 'extensions' / 'kentscript'
        ext_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove old extension if exists
        if ext_dir.exists():
            shutil.rmtree(ext_dir)
        
        # Copy extension
        shutil.copytree(install_dir / 'vscode-kentscript', ext_dir)
        
        # Fix extension paths - update server path
        ext_server_path = ext_dir / 'out' / 'extension.js'
        if ext_server_path.exists():
            content = ext_server_path.read_text()
            content = content.replace(
                "const serverModule = context.asAbsolutePath(path.join('..', 'kentscript-lsp', 'server.js'));",
                f"const serverModule = path.join('{install_dir}', 'kentscript-lsp', 'server.js');"
            )
            ext_server_path.write_text(content)
        
        # Install extension dependencies
        print("  Installing extension dependencies...")
        # Remove old node_modules to ensure clean install
        if (ext_dir / 'node_modules').exists():
            shutil.rmtree(ext_dir / 'node_modules')
        if (ext_dir / 'package-lock.json').exists():
            (ext_dir / 'package-lock.json').unlink()
        subprocess.run(['npm', 'install'], cwd=ext_dir, capture_output=True)
        
        print(f"  Copied extension to: {ext_dir}")
    
    # Create .desktop file for Linux
    if os.name != 'nt':
        print("\n[5/5] Creating desktop entry...")
        desktop_dir = Path.home() / '.local' / 'share' / 'applications'
        desktop_dir.mkdir(parents=True, exist_ok=True)
        
        desktop_file = desktop_dir / 'kentscript.desktop'
        desktop_file.write_text(f'''[Desktop Entry]
Name=KentScript
Comment=KentScript Programming Language
Exec={bin_dir}/kentscript %F
Icon=text-x-kentscript
Type=Application
Categories=Development;
MimeType=text/x-kentscript;
''')
        
        # Create mime type file
        mime_dir = Path.home() / '.local' / 'share' / 'mime' / 'packages'
        mime_dir.mkdir(parents=True, exist_ok=True)
        mime_file = mime_dir / 'kentscript.xml'
        mime_file.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="text/x-kentscript">
    <comment>KentScript source file</comment>
    <glob pattern="*.ks"/>
  </mime-type>
</mime-info>
''')
        
        print(f"  Created: {desktop_file}")
    
    print("\n" + "=" * 60)
    print("Installation complete!")
    print("=" * 60)
    print(f"\nTo use KentScript:")
    print(f"  - Command: kentscript")
    print(f"  - Or open a .ks file in Codium/VSCode")
    print(f"\nTo restart Codium and see the extension:")
    print(f"  - Close Codium completely")
    print(f"  - Open Codium again")
    print(f"  - Open any .ks file")

if __name__ == '__main__':
    main()
