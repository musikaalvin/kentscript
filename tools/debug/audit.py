import os
import re
from pathlib import Path

# Audit all components
py_files = list(Path('.').glob('*.py'))

print("=" * 80)
print("KENTSCRIPT BARE-METAL AUDIT")
print("=" * 80)

# 1. Check for inline assembly support
print("\n[1] INLINE ASSEMBLY SUPPORT")
for f in py_files:
    content = f.read_text()
    if 'inline' in content.lower() and 'asm' in content.lower():
        print(f"  ✓ {f.name}: has mention of inline asm")
        # Extract relevant lines
        for i, line in enumerate(content.split('\n')):
            if 'inline' in line.lower() and 'asm' in line.lower():
                print(f"    L{i}: {line.strip()[:80]}")

# 2. Check for volatile support
print("\n[2] VOLATILE/DEVICE MEMORY SEMANTICS")
for f in py_files:
    content = f.read_text()
    if 'volatile' in content.lower():
        print(f"  ✓ {f.name}: mentions volatile")

# 3. Check for physical memory access
print("\n[3] PHYSICAL MEMORY ACCESS")
phys_mem_found = False
for f in py_files:
    content = f.read_text()
    if 'physical' in content.lower() or 'phys' in content.lower():
        print(f"  ~ {f.name}: mentions physical")
        phys_mem_found = True

if not phys_mem_found:
    print("  ✗ NO TRUE PHYSICAL MEMORY ACCESS FOUND")

# 4. Check for MMIO
print("\n[4] MMIO (MEMORY-MAPPED I/O)")
for f in py_files:
    content = f.read_text()
    if 'mmio' in content.lower():
        print(f"  ~ {f.name}")

# 5. Check for port I/O
print("\n[5] PORT I/O (inb/outb/inw/outw)")
for f in py_files:
    content = f.read_text()
    if any(x in content.lower() for x in ['inb', 'outb', 'inw', 'outw', 'port_io']):
        print(f"  ~ {f.name}")

# 6. Check for MSR access
print("\n[6] MSR (Model-Specific Register) ACCESS")
for f in py_files:
    content = f.read_text()
    if 'msr' in content.lower():
        print(f"  ~ {f.name}")
        msr_lines = [l for l in content.split('\n') if 'msr' in l.lower()]
        for line in msr_lines[:2]:
            print(f"    {line.strip()[:80]}")

# 7. Check for control register access
print("\n[7] CONTROL REGISTERS (cr0, cr3, cr4, etc)")
for f in py_files:
    content = f.read_text()
    if any(x in content.lower() for x in ['cr0', 'cr3', 'cr4', 'control_register']):
        print(f"  ~ {f.name}")

# 8. Check for privileged instruction support
print("\n[8] PRIVILEGED INSTRUCTIONS (cli, sti, lgdt, lldt, etc)")
for f in py_files:
    content = f.read_text()
    if any(x in content for x in ['cli', 'sti', 'lgdt', 'lldt', 'hlt', 'wrmsr', 'rdmsr']):
        print(f"  ~ {f.name}")

# 9. Check language syntax
print("\n[9] LANGUAGE SYNTAX SUPPORT")
for f in ['parser.py', 'lexer.py']:
    if Path(f).exists():
        content = Path(f).read_text()
        # Look for keyword support
        keywords = ['@asm', '@volatile', '@inline', '@noopt', '@barrier']
        found = {kw: kw in content for kw in keywords}
        for kw, present in found.items():
            status = "✓" if present else "✗"
            print(f"  {status} {kw}")

print("\n" + "=" * 80)
