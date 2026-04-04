# Build KentScript Windows Installer

import subprocess
import os
import shutil

# Clean previous builds
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

# Build standalone executable
cmd = [
    'pyinstaller',
    'main.py',
    '--name=kentscript',
    '--onedir',
    '--console',
    '--add-data=stdlib:stdlib',
    '--add-data=compiler:compiler',
    '--add-data=runtime:runtime',
    '--add-data=include:include',
    '--hidden-import=ks_core',
    '--hidden-import=error_formatter',
    '--hidden-import=error_handler',
    '--collect-all=compiler',
    '--collect-all=runtime',
    '--collect-all=stdlib',
]

subprocess.run(cmd)

print("\n✓ Executable built: dist/kentscript.exe")
print("\nNext steps:")
print("1. Install Inno Setup: https://jrsoftware.org/isdl.php")
print("2. Open installer.iss in Inno Setup")
print("3. Click Build → Compile")
print("4. Installer will be in dist/KentScript-Setup-1.0.0.exe")
