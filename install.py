"""
KentScript Windows Installer
Run this on Windows: python install.py
"""
import os
import sys
import shutil
import winreg
from pathlib import Path

def main():
    print("=" * 60)
    print("KentScript Installer v1.0.0")
    print("=" * 60)
    
    # Get install directory
    default_dir = r"C:\Program Files\KentScript"
    install_dir = input(f"\nInstall directory [{default_dir}]: ").strip() or default_dir
    install_path = Path(install_dir)
    
    # Create directory
    print(f"\n[1/4] Creating directory: {install_path}")
    install_path.mkdir(parents=True, exist_ok=True)
    
    # Copy files
    print("[2/4] Copying files...")
    src = Path(__file__).parent
    for item in ['main.py', 'ks_core.py', 'error_formatter.py', 'error_handler.py',
                 'compiler', 'runtime', 'stdlib', 'include', 'tools', 'examples', 'docs']:
        src_path = src / item
        if src_path.exists():
            dst_path = install_path / item
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)
    
    # Create launcher
    print("[3/4] Creating launcher...")
    launcher = install_path / "kentscript.bat"
    launcher.write_text(f'@echo off\npython "{install_path}\\main.py" %*\n')
    
    # Add to PATH
    print("[4/4] Adding to PATH...")
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_ALL_ACCESS)
        path, _ = winreg.QueryValueEx(key, 'Path')
        if str(install_path) not in path:
            new_path = f"{path};{install_path}"
            winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
        winreg.CloseKey(key)
        print("✓ Added to PATH")
    except Exception as e:
        print(f"⚠ Could not add to PATH: {e}")
        print(f"  Manually add: {install_path}")
    
    print("\n" + "=" * 60)
    print("✓ Installation complete!")
    print("=" * 60)
    print(f"\nInstalled to: {install_path}")
    print("\nUsage:")
    print("  kentscript run myfile.ks")
    print("  kentscript build myfile.ks")
    print("  kentscript  (REPL)")
    print("\nRestart your terminal for PATH changes to take effect.")

if __name__ == '__main__':
    if sys.platform != 'win32':
        print("This installer is for Windows only.")
        print("On Linux/Mac, use: ./kentscript or python3 main.py")
        sys.exit(1)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled.")
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)
