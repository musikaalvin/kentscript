#!/usr/bin/env python3
"""
KentScript → MiniOS Builder
Builds OS components written in KentScript syntax into MiniOS

Usage:
    python3 build_minios_ks.py          # Build default kernel
    python3 build_minios_ks.py --help   # Show options
"""

import os
import sys
import subprocess
import tempfile
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

KERNEL_KS_SOURCE = r"""
:: MiniOS Kernel written in KentScript syntax
:: This demonstrates self-hosting OS

:: Memory allocation
func kmalloc(size) {
    return malloc(size);
}

:: String length
func kstrlen(s) {
    let i = 0;
    while i < s.len() {
        if s[i] == 0 { return i; }
        i = i + 1;
    }
    return 0;
}

:: UART output
func uart_putc(c) {
    let uart = 0x09000000 as *i32;
    :: Poll TX ready
    while (uart[6] & 32) != 0 { }
    uart[0] = c;
}

func uart_puts(msg) {
    let i = 0;
    while i < msg.len() {
        if msg[i] == 10 { uart_putc(13); }
        uart_putc(msg[i]);
        i = i + 1;
    }
}

:: Task structure
struct Task {
    id: i32,
    name: string,
    state: string,
    ticks: i32,
    stack: *i32
}

:: Scheduler
let tasks = [];
let current_task = 0;

func scheduler_init() {
    tasks = [];
    current_task = 0;
}

func scheduler_add(name) {
    let t = new Task();
    t.name = name;
    t.state = "READY";
    t.ticks = 0;
    tasks.push(t);
    return tasks.len() - 1;
}

func scheduler_tick() {
    let n = tasks.len();
    if n <= 1 { return; }
    current_task = current_task + 1;
    if current_task >= n { current_task = 1; }
    tasks[current_task].ticks = tasks[current_task].ticks + 1;
}

:: VFS node
struct VFSNode {
    name: string,
    node_type: string,
    data: string,
    size: i32,
    parent: *VFSNode,
    child: *VFSNode
}

let vfs_root = 0;

func vfs_init() {
    vfs_root = new VFSNode();
    vfs_root.name = "/";
    vfs_root.node_type = "dir";
    
    let bin = new VFSNode();
    bin.name = "bin";
    bin.node_type = "dir";
    bin.parent = vfs_root;
    vfs_root.child = bin;
    
    let sh = new VFSNode();
    sh.name = "sh";
    sh.node_type = "file";
    sh.data = "#!/bin/sh\necho 'MiniOS Shell'\n";
    sh.size = sh.data.len();
    sh.parent = bin;
    bin.child = sh;
}

:: Main kernel entry
func minios_main() {
    uart_puts("=== MiniOS (KentScript) ===\n");
    uart_puts("Kernel written in KentScript\n");
    uart_puts("============================\n");
    
    scheduler_init();
    scheduler_add("idle");
    scheduler_add("init");
    scheduler_add("shell");
    
    uart_puts("Tasks: ");
    uart_puts(str(tasks.len()));
    uart_puts("\n");
    
    scheduler_tick();
    scheduler_tick();
    
    uart_puts("Scheduler ticks OK\n");
    vfs_init();
    uart_puts("VFS initialized\n");
    uart_puts("\nMiniOS KentScript ready!\n");
}

minios_main();
"""


def build_to_c(ks_source, output_c):
    """Compile KentScript to C"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ks", delete=False) as f:
        f.write(ks_source)
        ks_file = f.name

    try:
        result = subprocess.run(
            [sys.executable, "main.py", "build", ks_file, "--keep-c", "-O2"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )

        base_name = os.path.basename(ks_file)
        c_file = os.path.join(SCRIPT_DIR, base_name.replace(".ks", ".c"))
        if os.path.exists(c_file):
            shutil.move(c_file, output_c)
            print(f"✓ Generated: {output_c}")
            return True
        else:
            print(
                f"✗ C generation failed: stdout={result.stdout}, stderr={result.stderr}"
            )
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        if os.path.exists(ks_file):
            os.unlink(ks_file)


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║    KentScript → MiniOS Build System                        ║")
    print("║    Build OS components in KentScript syntax                 ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    output_c = os.path.join(SCRIPT_DIR, "minios", "kentscript_kernel.c")

    print("Step 1: Compiling KentScript kernel to C...")
    if build_to_c(KERNEL_KS_SOURCE, output_c):
        print()
        print("Step 2: Kernel C code generated!")
        print()
        print("The KentScript kernel can now be:")
        print("  • Linked into MiniOS kernel image")
        print("  • Compiled for AArch64 bare-metal")
        print("  • Run in QEMU or on real hardware")
        print()
        print(f"Output: {output_c}")
        print()
        print("To build full MiniOS with KentScript kernel:")
        print("  python3 main.py minios build")
    else:
        print("✗ Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
