#!/usr/bin/env python3
"""
KentScript v3.1 - Production Entry Point
[KS-REF-000] Main CLI with subcommands

Run with: kentscript [command] [options]

Commands:
  run <file.ks>         Interpret and run
  build <file.ks>       Transpile to C and compile with gcc
  ring0 <file.c>        Compile freestanding kernel ELF (requires gcc cross-compiler)
  ide                   Launch built-in web IDE (localhost:8000)
  repl                  Start interactive REPL
  version               Show version info
  help                  Show this help
"""

import sys
import os
import argparse
import importlib
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure the package directory is on the path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Install global exception handler for beautiful errors
from error_handler import KSError

sys.excepthook = KSError.wrap_exception

# Version information
__version__ = "3.1.0"
__codename__ = "Baremetal"
__build__ = "production"


# ============================================================================
# VERSION INFO
# ============================================================================


def print_version():
    """Print version information"""
    import platform as _plat, subprocess as _sp, shutil as _sh

    arch = _plat.machine()

    # Check for AArch64 cross-compiler
    aarch64_cc = _sh.which("aarch64-linux-gnu-gcc") or _sh.which(
        "aarch64-unknown-linux-gnu-gcc"
    )
    aarch64_status = (
        f"✓ {aarch64_cc}"
        if aarch64_cc
        else "✗ not found (install: apt install gcc-aarch64-linux-gnu)"
    )

    # Check for QEMU
    qemu = _sh.which("qemu-system-aarch64")
    qemu_status = (
        f"✓ {qemu}" if qemu else "✗ not found (install: apt install qemu-system-arm)"
    )

    print(f"""
KentScript {__version__} ({__codename__})
Platform: {sys.platform} ({arch})
Python: {sys.version.split()[0]}

Type 'kentscript --help' or 'kentscript run --help' for usage.
""")


# ============================================================================
# COMMAND HANDLERS
# ============================================================================


class CommandHandler:
    """Handle CLI commands with proper error handling"""

    @staticmethod
    def run(args: argparse.Namespace):
        """Run a KentScript file"""
        try:
            from ks_core import run_file
            from error_handler import KSError

            run_file(
                args.file, use_cache=not args.no_cache
            )
        except ImportError as e:
            from error_handler import KSError

            KSError.print_exception(e, filename=args.file)
            sys.exit(1)
        except FileNotFoundError:
            from error_formatter import ErrorFormatter

            print(
                ErrorFormatter.format_error(
                    "FileNotFoundError", f"File not found: {args.file}"
                )
            )
            sys.exit(1)
        except (
            SyntaxError,
            TypeError,
            NameError,
            RuntimeError,
            AttributeError,
            IndexError,
            KeyError,
            ValueError,
        ) as e:
            from error_handler import KSError

            # Check if already formatted
            if hasattr(e, "formatted"):
                print(e.formatted, file=sys.stderr)
            else:
                # Load source for context
                source = None
                try:
                    with open(args.file, "r") as f:
                        source = f.read()
                except:
                    pass
                KSError.print_exception(e, filename=args.file, source=source)
            sys.exit(1)
        except Exception as e:
            from error_handler import KSError

            KSError.print_exception(e, filename=args.file)
            if args.debug:
                traceback.print_exc()
            sys.exit(1)

    @staticmethod
    def run_command(code: str):
        """Run KentScript code from command line (-c flag, like python -c)"""
        try:
            from compiler.lexer.lexer import Lexer
            from compiler.parser.parser import Parser
            from ks.interpreter import Interpreter
            from error_formatter import ErrorFormatter

            lexer = Lexer(code, filename="<command>")
            tokens = lexer.tokenize()
            parser = Parser(tokens, code, filename="<command>")
            ast = parser.parse()

            interpreter = Interpreter(source_code=code)
            interpreter.interpret(ast)
        except SyntaxError as e:
            if hasattr(e, "formatted"):
                print(e.formatted, file=sys.stderr)
            else:
                print(ErrorFormatter.format_exception(e, "<command>", code), file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            if hasattr(e, "formatted"):
                print(e.formatted, file=sys.stderr)
            else:
                from error_formatter import format_exception
                print(format_exception(e, "<command>", code), file=sys.stderr)
            sys.exit(1)

    @staticmethod
    def build(args: argparse.Namespace):
        """Build KentScript to native binary"""
        # Validate file exists before attempting any processing
        if not os.path.exists(args.file):
            from error_formatter import ErrorFormatter
            print(
                ErrorFormatter.format_error(
                    "FileNotFoundError", f"File not found: {args.file}", filename=args.file
                ),
                file=sys.stderr,
            )
            sys.exit(1)

        # C transpiler path
        try:
            from ks_core import BuildPipeline
            from error_formatter import ErrorFormatter

            pipeline = BuildPipeline(args.file)
            output_format = "binary"
            if args.keep_c:
                output_format = "c"
            success = pipeline.build(
                output_format=output_format,
                optimization=f"O{args.opt}",
                no_cache=getattr(args, "no_cache", False),
                pgo=getattr(args, "release", False),
                quiet=getattr(args, "quiet", False),
            )
            if not success:
                sys.exit(1)
            # Run the binary if --run flag is set
            if getattr(args, 'run', False):
                import subprocess
                binary_path = pipeline.output_binary
                try:
                    result = subprocess.run([binary_path])
                    sys.exit(result.returncode)
                except FileNotFoundError:
                    print(f"Error: Binary not found at {binary_path}", file=sys.stderr)
                    sys.exit(1)
        except ImportError as e:
            from error_formatter import ErrorFormatter

            print(
                ErrorFormatter.format_error(
                    "ImportError", f"Could not import ks_core: {e}"
                )
            )
            sys.exit(1)
        except FileNotFoundError as e:
            from error_formatter import ErrorFormatter

            print(
                ErrorFormatter.format_error(
                    "FileNotFoundError", f"File not found: {args.file}"
                )
            )
            sys.exit(1)
        except SyntaxError as e:
            from error_handler import KSError

            # Check if already formatted
            if hasattr(e, "formatted"):
                print(e.formatted, file=sys.stderr)
            else:
                source_lines = None
                try:
                    with open(args.file, "r") as f:
                        source_lines = f.read()
                except:
                    pass
                from error_formatter import ErrorFormatter

                print(
                    ErrorFormatter.syntax_error(
                        str(e),
                        line=getattr(e, "lineno", None),
                        col=getattr(e, "offset", None),
                        source_lines=source_lines,
                        filename=args.file,
                    ),
                    file=sys.stderr,
                )
            sys.exit(1)
        except Exception as e:
            from error_handler import KSError

            # Check if already formatted
            if hasattr(e, "formatted"):
                print(e.formatted, file=sys.stderr)
            else:
                from error_formatter import ErrorFormatter

                print(
                    ErrorFormatter.format_error(
                        type(e).__name__, str(e), filename=args.file
                    ),
                    file=sys.stderr,
                )
            # Always print traceback for debugging
            traceback.print_exc()
            sys.exit(1)

    @staticmethod
    def ring0(args: argparse.Namespace):
        """Compile C to Ring 0 kernel — uses real freestanding GCC pipeline"""
        try:
            from kernel.ring0.kernel_backend import KernelBackend, ExecutionMode

            # Map mode
            mode_map = {
                "bare": ExecutionMode.BARE_METAL,
                "freestanding": ExecutionMode.FREESTANDING,
                "hypervisor": ExecutionMode.HYPERVISOR,
                "secure": ExecutionMode.SECURE_MONITOR,
            }
            mode = mode_map.get(args.mode, ExecutionMode.BARE_METAL)

            # Read source
            with open(args.file, "r") as f:
                source = f.read()

            # Determine output
            output = args.output or args.file.replace(".c", ".elf")

            # Compile with KernelBackend (uses toolchain detection)
            backend = KernelBackend(arch=args.arch, mode=mode, boot_protocol=args.boot)

            try:
                binary = backend.compile_ring0(
                    source, output, extra_flags=args.extra_flags
                )
                print(f"✓ Compiled to {binary}")
                if args.run:
                    print(f"\nBoot command: {backend.get_boot_command(binary)}")
            except Exception as ring0_err:
                # Fallback: use the real FreestandingCompiler
                print(
                    f"[ring0] Primary pipeline failed ({ring0_err}), using FreestandingCompiler..."
                )
                import os as _os, sys as _sys

                _bm_path = _os.path.join(
                    _os.path.dirname(_os.path.abspath(__file__)),
                    "kernel",
                    "baremetal",
                    "freestanding.py",
                )
                import importlib.util as _ilu

                _bm_spec = _ilu.spec_from_file_location("freestanding", _bm_path)
                _bm_mod = _ilu.module_from_spec(_bm_spec)
                _bm_spec.loader.exec_module(_bm_mod)
                compiler = _bm_mod.FreestandingCompiler(arch=args.arch or "x86_64")
                ok, msg = compiler.compile_ks_to_baremetal(source, output)
                print(msg)
                if ok and args.run:
                    qemu = compiler._builder.generate_qemu_command(output)
                    print(f"\nBoot command: {qemu}")
                elif not ok:
                    sys.exit(1)

        except ImportError:
            # ring0_extension not present: use FreestandingCompiler directly
            try:
                with open(args.file, "r") as f:
                    source = f.read()
                output = args.output or args.file.replace(".c", ".elf")
                import os as _os

                _bm_path = _os.path.join(
                    _os.path.dirname(_os.path.abspath(__file__)),
                    "kernel",
                    "baremetal",
                    "freestanding.py",
                )
                import importlib.util as _ilu

                _bm_spec = _ilu.spec_from_file_location("freestanding", _bm_path)
                _bm_mod = _ilu.module_from_spec(_bm_spec)
                _bm_spec.loader.exec_module(_bm_mod)
                compiler = _bm_mod.FreestandingCompiler(
                    arch=getattr(args, "arch", "x86_64") or "x86_64"
                )
                ok, msg = compiler.compile_ks_to_baremetal(source, output)
                print(msg)
                if not ok:
                    sys.exit(1)
                if getattr(args, "run", False):
                    qemu = compiler._builder.generate_qemu_command(output)
                    print(f"\nBoot command: {qemu}")
            except Exception as e2:
                print(f"[ERROR] {e2}")
                sys.exit(1)
        except FileNotFoundError:
            print(f"[ERROR] File not found: {args.file}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] {e}")
            if args.debug:
                traceback.print_exc()
            sys.exit(1)

    @staticmethod
    def kernel_dev(args: argparse.Namespace):
        """Generate kernel subsystem C files (GDT, IDT, scheduler, vmem, syscalls)."""
        try:
            from kernel.ring0.ks_kernel_dev import install as kd_install

            dest = args.output or "minios_output"
            os.makedirs(dest, exist_ok=True)
            kd_install(dest)

        except ImportError as e:
            print(f"[ERROR] ks_kernel_dev not available: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] {e}")
            if args.debug:
                traceback.print_exc()
            sys.exit(1)

    @staticmethod
    def audit(args: argparse.Namespace):
        """Audit a binary — 10-part forensic verification (v2.0, compiler-rt aware)"""
        try:
            import tools.debug.ks_audit as _ka

            mode = getattr(args, "audit_mode", "full")
            verbose = getattr(args, "verbose", False)

            # ── Utility / build commands (no binary required) ─────────────
            if getattr(args, "dump_memfuncs", False):
                print(_ka.FREESTANDING_MEMFUNCS_C)
                return

            if getattr(args, "dump_linkerscript", False):
                print(_ka.FREESTANDING_LINKER_AARCH64)
                return

            if getattr(args, "build_freestanding", None):
                src = args.build_freestanding
                out = getattr(args, "output", None) or src.replace(
                    ".c", "_freestanding.elf"
                )
                arch = getattr(args, "arch", "aarch64")
                opt = getattr(args, "opt", "O2")
                ok, msg = _ka.build_freestanding(src, out, arch, opt)
                print(msg)
                if ok:
                    print("\nRunning freestandingty audit on result...")
                    _ka.run_full_audit(out, verbose, freestanding_mode=False)
                sys.exit(0 if ok else 1)

            if getattr(args, "patch_freestanding", None):
                binary_in = args.patch_freestanding
                out = getattr(args, "output", None) or binary_in
                ok, msg = _ka.patch_freestanding(binary_in, out)
                print(msg)
                sys.exit(0 if ok else 1)

            # ── Normal audit ──────────────────────────────────────────────
            binary = getattr(args, "file", None)
            if not binary:
                print("[ERROR] No binary specified. Usage: kentscript audit <binary>")
                sys.exit(1)

            dispatch = {
                "hosted": lambda: print(
                    _ka.render_report(_ka.audit_hosted(binary), verbose)
                ),
                "freestanding": lambda: print(
                    _ka.render_report(_ka.audit_freestanding(binary), verbose)
                ),
                "kernel": lambda: print(
                    _ka.render_report(_ka.audit_kernel(binary), verbose)
                ),
                "abi": lambda: print(_ka.render_report(_ka.audit_abi(binary), verbose)),
                "entropy": lambda: print(
                    _ka.render_report(_ka.audit_entropy(binary), verbose)
                ),
                "hardening": lambda: print(
                    _ka.render_report(_ka.audit_hardening(binary), verbose)
                ),
                "freestanding": lambda: _ka.run_full_audit(
                    binary, verbose, freestanding_mode=True
                ),
                "full": lambda: _ka.run_full_audit(
                    binary, verbose, freestanding_mode=False
                ),
            }
            dispatch.get(mode, dispatch["full"])()

        except ImportError as e:
            print(f"[ERROR] ks_audit not available: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] {e}")
            if getattr(args, "debug", False):
                import traceback

                traceback.print_exc()
            sys.exit(1)

    @staticmethod
    def privilege_report(args: argparse.Namespace):
        """Run the 9-level truth ladder: from normal process to bare metal"""
        try:
            from tools.debug.privilege_report import (
                PrivilegeLevelReport,
                level0_process_check,
                level1_raw_syscall,
                level2_mmu,
                level3_physical_memory,
                level4_kernel_elf,
                level5_mmio,
                level6_privilege,
                level7_page_tables,
                level8_interrupts,
                level9_no_linux,
                build_kernel,
                render_ladder,
                build_aarch64_10test_kernel,
                run_aarch64_10test_suite,
            )

            kernel = getattr(args, "kernel", None)
            verbose = getattr(args, "verbose", False)
            cmd = getattr(args, "tl_command", "run")

            if cmd == "test10":
                output = getattr(args, "output", "/tmp/ks_aarch64_10test.elf")
                verbose = getattr(args, "verbose", False)
                report = run_aarch64_10test_suite(output, verbose=verbose)
                print(report)
                import sys as _sys

                _sys.exit(0)

            if cmd == "build-kernel":
                output = (
                    getattr(args, "output", "/tmp/ks_kernel.elf")
                    or "/tmp/ks_kernel.elf"
                )
                arch_arg = getattr(args, "arch", "auto") or "auto"
                print(f"Building bare-metal kernel → {output}  [arch={arch_arg}]")
                ok, msg = build_kernel(output, arch=arch_arg)
                print(msg)
                import sys as _sys

                _sys.exit(0 if ok else 1)

            if cmd == "binary" and getattr(args, "file", None):
                kernel = args.file

            ladder = PrivilegeLevelReport()
            print("\nRunning KentScript Truth Ladder (9 levels)...\n")

            level0_process_check(ladder)
            level1_raw_syscall(ladder)
            level2_mmu(ladder)
            level3_physical_memory(ladder)
            if kernel:
                level4_kernel_elf(ladder, kernel)
                level5_mmio(ladder, kernel)
            level6_privilege(ladder, kernel)
            if kernel:
                level7_page_tables(ladder, kernel)
                level8_interrupts(ladder, kernel)
                level9_no_linux(ladder, kernel)

            print(render_ladder(ladder, verbose))

        except ImportError as e:
            print(f"[ERROR] ks_privilege_report not available: {e}")
            import sys as _sys

            _sys.exit(1)
        except Exception as e:
            print(f"[ERROR] {e}")
            if getattr(args, "debug", False):
                import traceback as _tb

                _tb.print_exc()
            import sys as _sys

            _sys.exit(1)

    @staticmethod
    def repl(args: argparse.Namespace):
        """Start interactive REPL"""
        try:
            from ks_core import repl
            from error_formatter import ErrorFormatter

            repl()
        except ImportError as e:
            from error_formatter import ErrorFormatter, info

            print(
                ErrorFormatter.format_error(
                    "ImportError", f"Could not import ks_core: {e}"
                )
            )
            print(info("Falling back to simple REPL..."))
            # Simple fallback REPL
            while True:
                try:
                    line = input(">>> ")
                    if line.strip() in ("exit", "quit"):
                        break
                    print(f"echo: {line}")
                except (KeyboardInterrupt, EOFError):
                    break
        except Exception as e:
            from error_formatter import ErrorFormatter

            print(ErrorFormatter.format_exception(e))
            sys.exit(1)

    @staticmethod
    def info(args: argparse.Namespace):
        """Show system information"""
        print_version()

        # Check available components
        _base = os.path.dirname(os.path.abspath(__file__))
        _comp_paths = {
            "ks_core": "ks_core.py",
            "kernel_backend": "kernel/ring0/kernel_backend.py",
            "mmio_generator": "kernel/drivers/arm64_mmio.py",
            "c_transpiler": "codegen/c_transpiler.py",
            "slab_allocator": "runtime/memory/slab_allocator.py",
        }
        components = {}
        for comp, rel in _comp_paths.items():
            if rel is None:
                try:
                    importlib.import_module(comp)
                    components[comp] = True
                except ImportError:
                    components[comp] = False
            else:
                components[comp] = os.path.isfile(os.path.join(_base, rel))

        print("\nComponents:")
        for comp, available in components.items():
            status = "✓" if available else "✗"
            print(f"  {status} {comp}")

        # Architecture info
        import platform

        print(f"\nArchitecture: {platform.machine()}")
        print(f"OS: {platform.system()} {platform.release()}")

        # Python info
        print(f"Python: {sys.version.split()[0]}")

        # C compiler info
        import subprocess

        for compiler in ["gcc", "clang", "zig"]:
            try:
                result = subprocess.run(
                    [compiler, "--version"], capture_output=True, text=True, timeout=1
                )
                if result.returncode == 0:
                    first_line = result.stdout.split("\n")[0]
                    print(f"{compiler}: {first_line[:60]}")
                    break
            except:
                continue

    @staticmethod
    def ide(args: argparse.Namespace):
        """Launch the built-in web IDE"""
        import subprocess

        _base = os.path.dirname(os.path.abspath(__file__))
        _server_py = os.path.join(_base, "stdlib", "ide_server.py")

        if not os.path.isfile(_server_py):
            print("[ERROR] stdlib/ide_server.py not found. Cannot launch IDE.")
            sys.exit(1)

        env = os.environ.copy()
        env["KENTSCRIPT_IDE_ROOT"] = os.path.abspath(args.root)
        env["KENTSCRIPT_IDE_PORT"] = str(args.port)

        print(f"  Launching KentScript IDE on port {args.port}...")
        print(f"  Root: {os.path.abspath(args.root)}")
        print(f"  Open: http://localhost:{args.port}")
        print()
        try:
            subprocess.run([sys.executable, _server_py], env=env)
        except KeyboardInterrupt:
            print("\n  IDE stopped.")

    @staticmethod
    # =========================================================================
    # KENTOS — MiniOS bare-metal OS builder
    # =========================================================================
    @staticmethod
    def minios(args: argparse.Namespace):
        """Build / run / inspect the MiniOS bare-metal OS kernel."""
        try:
            # minios/ subfolder lives next to main.py
            sys.path.insert(0, os.path.join(SCRIPT_DIR, "minios"))
            from mini_os import MiniOS, MiniOSConfig
        except ImportError as e:
            print(f"[ERROR] Could not import mini_os: {e}")
            print("Make sure minios/mini_os.py exists in your KentScript folder.")
            sys.exit(1)

        cfg = MiniOSConfig(output=getattr(args, "output", "/tmp/minios.elf"))
        k = MiniOS(cfg)

        cmd = getattr(args, "minios_cmd", "info")
        if cmd == "info":
            k.info()
        elif cmd == "build":
            ok, msg = k.build()
            print(msg)
            sys.exit(0 if ok else 1)
        elif cmd == "run":
            ok, msg = k.run(gui=False)
            if not ok:
                print(msg)
                sys.exit(1)
        elif cmd == "run-gui":
            ok, msg = k.run(gui=True)
            if not ok:
                print(msg)
                sys.exit(1)
        else:
            print(f"[MiniOS] Unknown sub-command: {cmd}")
            sys.exit(1)

    @staticmethod
    def debug(args: argparse.Namespace):
        """Debug KentScript file with step-by-step execution"""
        try:
            from compiler.lexer.lexer import Lexer
            from compiler.parser.parser import Parser
            from ks.interpreter import Interpreter
            from runtime.debug.ks_debugger import KentScriptDebugger, DebuggerQuit

            # Force line-buffered stdout so a streamed (piped/pty) debug
            # session flushes each print instead of blocking until exit.
            try:
                sys.stdout.reconfigure(line_buffering=True)
            except Exception:
                pass

            if not os.path.exists(args.file):
                print(f"[ERROR] File not found: {args.file}")
                sys.exit(1)

            with open(args.file, "r") as f:
                source = f.read()

            # Parse breakpoints from --break/-b args
            breakpoints = args.breakpoint or []

            debugger = KentScriptDebugger(
                source=source,
                filename=args.file,
                stop_on_entry=args.stop,
                breakpoint_lines=breakpoints,
                max_steps=args.steps or 0,
                inspect_vars=args.vars or [],
            )

            interpreter = Interpreter(source_code=source)
            interpreter.debugger = debugger

            print(f"[DEBUG] Starting: {args.file}")
            if breakpoints:
                print(f"[DEBUG] Breakpoints at lines: {breakpoints}")
            print("[DEBUG] Type 'help' for debugger commands\n")

            lexer = Lexer(source, auto_insert_semicolons=True)
            tokens = lexer.tokenize()
            ast = Parser(tokens).parse()
            if ast:
                try:
                    interpreter.interpret(ast)
                    print("\n[DEBUG] Program finished.")
                except DebuggerQuit:
                    print("\n[DEBUG] Debug session ended.")

        except ImportError as e:
            print(f"[ERROR] Could not import debugger: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] {e}")
            if getattr(args, "debug", False):
                traceback.print_exc()
            sys.exit(1)

    # =========================================================================
    # WASM — WebAssembly compilation and execution
    # =========================================================================
    @staticmethod
    def wasm(args: argparse.Namespace):
        """WebAssembly pipeline: build, wat, run, info"""
        try:
            from backends.wasm.wasm_backend import WasmBackend
        except ImportError as e:
            print(f"[ERROR] WASM backend not available: {e}")
            print("Make sure backends/wasm/ directory is complete.")
            sys.exit(1)

        backend = WasmBackend()
        cmd = getattr(args, "wasm_cmd", "info")

        if cmd == "build":
            filepath = getattr(args, "file", "")
            if not filepath or not os.path.exists(filepath):
                print(f"[ERROR] File not found: {filepath}")
                sys.exit(1)
            output = getattr(args, "output", None)
            if output is None:
                output = filepath.replace(".ks", ".wasm")
            wat, wasm_path = backend.transpile(filepath, output)
            if getattr(args, "run", False) and wasm_path:
                sys.exit(backend.run(wasm_path))
            elif not wasm_path:
                print("[WASM] Compilation failed", file=sys.stderr)
                sys.exit(1)

        elif cmd == "wat":
            filepath = getattr(args, "file", "")
            if not filepath or not os.path.exists(filepath):
                print(f"[ERROR] File not found: {filepath}")
                sys.exit(1)
            backend.compile_to_wat(filepath)

        elif cmd == "run":
            filepath = getattr(args, "file", "")
            if not filepath or not os.path.exists(filepath):
                print(f"[ERROR] File not found: {filepath}")
                sys.exit(1)
            runtime = getattr(args, "runtime", None)
            sys.exit(backend.run(filepath, runtime))

        else:
            print("=== WASM Toolchain Status ===")
            print()
            print(f"  wat2wasm:     {backend.wat2wasm or 'NOT FOUND (install wabt)'}")
            print(f"  Runtime:      {backend.wasm_run or 'NOT FOUND (install wasmtime)'}")
            print()
            if backend.wasm_run:
                print("  Available runtimes:")
                for rt in backend.list_runtimes():
                    print(f"    - {rt}")
            print()
            print("  Usage:")
            print("    ./kentscript wasm build file.ks          # .ks -> .wasm")
            print("    ./kentscript wasm build file.ks --run    # .ks -> .wasm -> run")
            print("    ./kentscript wasm wat file.ks            # .ks -> .wat (text)")
            print("    ./kentscript wasm run file.wasm          # run .wasm")
            print("    ./kentscript wasm info                   # this status")
            print()
            print("  Install tools:")
            print("    wat2wasm:  https://github.com/WebAssembly/wabt")
            print("    wasmtime:  curl https://wasmtime.dev/install.sh | bash")
            print("    node:      apt install nodejs")

    # =========================================================================
    # HARDWARE — hardware intrinsics / discovery
    # =========================================================================
    @staticmethod
    def hardware(args: argparse.Namespace):
        """Hardware discovery, MMIO, MSR, and intrinsics shell."""
        try:
            from kernel.drivers.hardware_intrinsics import HardwareDiscovery
        except ImportError as e:
            print(f"[ERROR] Could not import hardware_intrinsics: {e}")
            sys.exit(1)

        hw = HardwareDiscovery()
        hw_cmd = getattr(args, "hw_cmd", "info")
        if hw_cmd == "info":
            try:
                print(hw.get_report())
            except AttributeError:
                print(f"[Hardware] OS: {getattr(hw, 'os', 'unknown')}")
                for p in getattr(hw, "peripherals", []):
                    print(
                        f"  {getattr(p, 'name', '?')} @ 0x{getattr(p, 'base_address', 0):x}"
                    )
        elif hw_cmd == "peripheral":
            name = getattr(args, "name", None)
            if not name:
                print("[ERROR] Provide peripheral name: hardware peripheral <name>")
                sys.exit(1)
            base = hw.find_peripheral(name)
            if base is None:
                print(f"[HW] Peripheral '{name}' not found.")
            else:
                print(f"[HW] {name} → 0x{base:016x}")
        elif hw_cmd == "msr":
            msr = int(getattr(args, "msr_num", "0"), 16)
            try:
                val = hw._hw_read_msr(msr)
                print(f"[HW] MSR 0x{msr:x} → 0x{val:016x}")
            except Exception as e:
                print(f"[HW ERROR] {e}")
                sys.exit(1)

    @staticmethod
    def security(args: argparse.Namespace):
        """Launch KSecurity ethical pentesting console."""
        try:
            sys.path.insert(0, SCRIPT_DIR)
            from ksecurity.ks_security_engine import KSecurityEngine, SecurityConsole
        except ImportError as e:
            print(f"[ERROR] KSecurity unavailable: {e}")
            sys.exit(1)

        engine = KSecurityEngine()

        # Non-interactive quick modes
        if getattr(args, "list", False):
            print(engine.show("modules"))
            return

        if getattr(args, "scan", None):
            engine.use("scanner/ports")
            engine.set("RHOST", args.scan)
            engine.set("PORTS", getattr(args, "ports", "common"))
            engine._consent_given = True
            print(engine.run())
            return

        if getattr(args, "recon", None):
            engine.use("recon/osint")
            engine.set("TARGET", args.recon)
            print(engine.run())
            return

        if getattr(args, "netaudit", False):
            engine.use("defensive/netaudit")
            print(engine.run())
            return

        # Module shortcut
        if getattr(args, "module", ""):
            result = engine.use(args.module)
            print(result)
            if "loaded" in result:
                # Drop into interactive console with module pre-loaded
                SecurityConsole(engine).run()
            return

        # Default: interactive console
        SecurityConsole(engine).run()

# ============================================================================
# MAIN CLI
# ============================================================================


def main():
    """Main entry point with argument parsing"""

    # ── Redirect "kentscript --help <cmd>" → "kentscript <cmd> --help" ──
    _subcommands = {
        "run", "build", "ring0", "kernel-dev", "info", "debug", "audit",
        "privilege_report", "minios", "hardware", "wasm", "security", "ide",
    }
    argv = sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        help_idx = next(
            i for i, a in enumerate(argv) if a in ("--help", "-h")
        )
        # Find first non-flag arg after --help
        for j in range(help_idx + 1, len(argv)):
            if argv[j] in _subcommands:
                # Rewrite argv: move subcommand before --help
                sys.argv = [sys.argv[0]] + [argv[j], "--help"]
                break

    parser = argparse.ArgumentParser(
        prog="kentscript",
        description="KentScript v3.1.0 - Systems Programming Language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
KentScript is a compiled systems-programming language.
The 'kentscript' binary is the real entry point — examples use it directly.

Examples:
  kentscript run program.ks
  kentscript build program.ks -O3
  kentscript ring0 kernel.c --arch aarch64 --mode bare
  kentscript info
  kentscript debug file.ks --break 10
  kentscript -c 'print("hello from KentScript")'

Interactive environments (with Tab-autocomplete + command history):
  kentscript                 Start the KentScript REPL
  kentscript ide             Launch built-in web IDE on localhost:8000
  kentscript security        Start the KSecurity pentest console
        """,
    )

    parser.add_argument(
        "--version", "-v", action="store_true", help="Show version information"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument(
        "-c",
        "--command",
        dest="ks_command",
        help="Run KentScript code from command line (like python -c)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # ========================================================================
    # RUN command
    # ========================================================================
    run_parser = subparsers.add_parser("run", help="Compile and run KentScript file")
    run_parser.add_argument("file", help="KentScript source file (.ks)")
    run_parser.add_argument(
        "--no-cache", action="store_true", help="Disable AST caching"
    )
    run_parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    # ========================================================================
    # BUILD command
    # ========================================================================
    build_parser = subparsers.add_parser("build", help="Compile to native binary")
    build_parser.add_argument("file", help="KentScript source file (.ks)")
    build_parser.add_argument(
        "-O",
        "--opt",
        choices=["0", "1", "2", "3"],
        default="2",
        help="Optimization level (default: 2)",
    )
    build_parser.add_argument(
        "--keep-c", action="store_true", help="Keep generated C file"
    )
    build_parser.add_argument("--output", "-o", help="Output binary name")
    build_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    build_parser.add_argument(
        "--no-cache", action="store_true", help="Disable build + transpile caches (always rebuild)"
    )
    build_parser.add_argument("--run", "-r", action="store_true", help="Run the binary after building")
    build_parser.add_argument(
        "--quiet", action="store_true", help="Suppress build progress output (only program output/errors)"
    )
    build_parser.add_argument(
        "--release",
        action="store_true",
        help="Release build: enable Profile-Guided Optimization (PGO) on top of LTO",
    )

    # ========================================================================
    # RING0 command
    # ========================================================================
    ring0_parser = subparsers.add_parser("ring0", help="Compile to Ring 0 kernel")
    ring0_parser.add_argument("file", help="C source file")
    ring0_parser.add_argument(
        "--arch",
        choices=["x86_64", "aarch64", "riscv64"],
        default="x86_64",
        help="Target architecture",
    )
    ring0_parser.add_argument(
        "--mode",
        choices=["bare", "freestanding", "hypervisor", "secure"],
        default="bare",
        help="Execution mode",
    )
    ring0_parser.add_argument(
        "--boot",
        choices=["raw", "multiboot2", "uboot", "efi"],
        default="raw",
        help="Boot protocol",
    )
    ring0_parser.add_argument("--output", "-o", help="Output file")
    ring0_parser.add_argument(
        "--run", action="store_true", help="Show QEMU boot command"
    )
    ring0_parser.add_argument("--extra-flags", help="Extra compiler flags")

    # ========================================================================
    # KERNEL-DEV command — Kernel Dev Mode: generate kernel subsystems
    # ========================================================================
    kdev_parser = subparsers.add_parser(
        "kernel-dev",
        help="Kernel Dev Mode — generate GDT/IDT/scheduler/vmem/syscall C files",
    )
    kdev_parser.add_argument(
        "--output",
        "-o",
        default="minios_output",
        help="Output directory for kernel source files",
    )
    kdev_parser.set_defaults(func=CommandHandler.kernel_dev)

    # ========================================================================
    # INFO command
    # ========================================================================
    info_parser = subparsers.add_parser("info", help="Show system information")

    # ========================================================================
    # IDE command — launch built-in web IDE
    # ========================================================================
    ide_parser = subparsers.add_parser(
        "ide",
        help="Launch built-in web IDE (browser-based code editor on localhost:8000)",
    )
    ide_parser.add_argument(
        "--port", "-p", type=int, default=8000, help="Port to listen on (default: 8000)"
    )
    ide_parser.add_argument(
        "--root", "-r", default=".", help="Project root directory (default: cwd)"
    )
    ide_parser.set_defaults(func=CommandHandler.ide)

    # ========================================================================
    # DEBUG command
    # ========================================================================
    debug_parser = subparsers.add_parser("debug", help="Debug KentScript file")
    debug_parser.add_argument("file", help="KentScript source file (.ks)")
    debug_parser.add_argument(
        "--stop", "-s", action="store_true", help="Stop at entry point"
    )
    debug_parser.add_argument(
        "--break",
        "-b",
        dest="breakpoint",
        action="append",
        type=int,
        help="Breakpoint at line",
    )
    debug_parser.add_argument("--steps", type=int, help="Max steps before stopping")
    debug_parser.add_argument(
        "--vars", "-v", dest="vars", action="append", help="Variables to inspect"
    )

    # ========================================================================
    # TEST command
    # ========================================================================
    # Audit subparser
    audit_parser = subparsers.add_parser(
        "audit",
        help="Forensic binary audit v2.0 — 10-part test ladder + freestandingty tools",
    )
    audit_parser.add_argument("file", nargs="?", help="Binary to audit")
    audit_parser.add_argument(
        "--mode",
        dest="audit_mode",
        choices=[
            "full",
            "hosted",
            "freestanding",
            "kernel",
            "abi",
            "entropy",
            "hardening",
            "freestanding",
        ],
        default="full",
        help="Audit mode (default: full)",
    )
    audit_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show raw tool output in reports"
    )
    audit_parser.add_argument(
        "--arch",
        choices=["x86_64", "aarch64"],
        default="aarch64",
        help="Target arch for build ops",
    )
    audit_parser.add_argument(
        "--opt", default="O2", help="Optimization level: O0 O1 O2 O3 Os"
    )
    audit_parser.add_argument(
        "-o", "--output", default=None, help="Output path for build/patch operations"
    )
    audit_parser.add_argument(
        "--build-freestanding",
        metavar="SOURCE",
        dest="build_freestanding",
        help="Compile SOURCE to freestanding bare-metal ELF",
    )
    audit_parser.add_argument(
        "--patch-freestanding",
        metavar="BINARY",
        dest="patch_freestanding",
        help="Strip all compiler metadata from BINARY",
    )
    audit_parser.add_argument(
        "--dump-memfuncs",
        action="store_true",
        dest="dump_memfuncs",
        help="Print freestanding memcpy/memset/strlen C source",
    )
    audit_parser.add_argument(
        "--dump-linkerscript",
        action="store_true",
        dest="dump_linkerscript",
        help="Print AArch64 freestanding linker script",
    )

    # privilege_report subparser
    tl_parser = subparsers.add_parser(
        "privilege_report", help="9-level truth ladder: userland to bare metal"
    )
    tl_sub = tl_parser.add_subparsers(dest="tl_command")
    tl_run_p = tl_sub.add_parser("run", help="Run all levels on this process")
    tl_run_p.add_argument("--kernel", help="Path to kernel.elf for L4-L9 tests")
    tl_run_p.add_argument("-v", "--verbose", action="store_true")
    tl_bin_p = tl_sub.add_parser("binary", help="Audit a binary ELF (L4-L9)")
    tl_bin_p.add_argument("file", help="Binary to audit")
    tl_bin_p.add_argument("-v", "--verbose", action="store_true")
    tl_bk_p = tl_sub.add_parser(
        "build-kernel", help="Build a bare-metal demo kernel.elf"
    )
    tl_bk_p.add_argument("--output", default="/tmp/ks_kernel.elf")
    tl_bk_p.add_argument(
        "--arch",
        choices=["auto", "x86", "x86_64", "aarch64", "riscv64", "all"],
        default="auto",
        help='Target arch (default: auto). Use "all" for every arch.',
    )
    tl_t10_p = tl_sub.add_parser(
        "test10", help="Build + verify all 10 AArch64 hardcore conditions"
    )
    tl_t10_p.add_argument(
        "--output",
        default="/tmp/ks_aarch64_10test.elf",
        help="Output ELF path (built if missing)",
    )
    tl_t10_p.add_argument("-v", "--verbose", action="store_true")
    tl_parser.set_defaults(tl_command="run")

    # ========================================================================
    # KENTOS command — MiniOS bare-metal OS builder
    # ========================================================================
    minios_parser = subparsers.add_parser(
        "minios", help="MiniOS bare-metal OS builder (AArch64 QEMU-virt)"
    )
    minios_sub = minios_parser.add_subparsers(dest="minios_cmd")
    minios_sub.add_parser("info", help="Show MiniOS feature summary")
    minios_build_p = minios_sub.add_parser("build", help="Compile MiniOS ELF")
    minios_build_p.add_argument(
        "--output",
        "-o",
        default="/tmp/minios.elf",
        help="Output ELF path (default: /tmp/minios.elf)",
    )
    minios_run_p = minios_sub.add_parser("run", help="Boot MiniOS in QEMU")
    minios_run_p.add_argument("--output", "-o", default="/tmp/minios.elf")
    minios_gui_p = minios_sub.add_parser(
        "run-gui", help="Boot MiniOS in QEMU (display)"
    )
    minios_gui_p.add_argument("--output", "-o", default="/tmp/minios.elf")
    minios_parser.set_defaults(minios_cmd="info", output="/tmp/minios.elf")

    # ========================================================================
    # HARDWARE command — hardware discovery & MMIO/MSR access
    # ========================================================================
    hw_parser = subparsers.add_parser(
        "hardware", help="Hardware discovery, MMIO read, MSR access"
    )
    hw_sub = hw_parser.add_subparsers(dest="hw_cmd")
    hw_sub.add_parser("info", help="Print hardware discovery report (default)")
    hw_per_p = hw_sub.add_parser("peripheral", help="Resolve a peripheral base address")
    hw_per_p.add_argument("name", help="Peripheral name (e.g. uart, gpio)")
    hw_msr_p = hw_sub.add_parser("msr", help="Read an MSR register (root only)")
    hw_msr_p.add_argument("msr_num", help="MSR number in hex (e.g. 0x1b)")
    hw_parser.set_defaults(hw_cmd="info")

    # ========================================================================
    # WASM command — WebAssembly compilation and execution
    # ========================================================================
    wasm_parser = subparsers.add_parser(
        "wasm",
        help="WebAssembly — compile KentScript to .wasm and execute",
    )
    wasm_sub = wasm_parser.add_subparsers(dest="wasm_cmd")

    wasm_build_p = wasm_sub.add_parser("build", help="Compile .ks to .wasm binary")
    wasm_build_p.add_argument("file", help="KentScript source file (.ks)")
    wasm_build_p.add_argument("--output", "-o", help="Output .wasm file")
    wasm_build_p.add_argument("--run", "-r", action="store_true", help="Run after build")

    wasm_wat_p = wasm_sub.add_parser("wat", help="Compile .ks to WAT text format only")
    wasm_wat_p.add_argument("file", help="KentScript source file (.ks)")
    wasm_wat_p.add_argument("--output", "-o", help="Output .wat file")

    wasm_run_p = wasm_sub.add_parser("run", help="Run a .wasm binary")
    wasm_run_p.add_argument("file", help=".wasm binary to execute")
    wasm_run_p.add_argument("--runtime", help="Runtime to use (wasmtime, node, wasm3, etc.)")

    wasm_info_p = wasm_sub.add_parser("info", help="Show WASM toolchain status")
    wasm_parser.set_defaults(wasm_cmd="info")

    # ========================================================================
    # SECURITY command — KSecurity ethical pentesting console
    # ========================================================================
    sec_parser = subparsers.add_parser(
        "security",
        help="KSecurity — Ethical Cybersecurity & Penetration Testing Console "
        "(interactive: Tab-autocompletes modules/options, ↑/↓ recalls history)",
    )
    sec_parser.add_argument(
        "--module", "-m", default="", help="Load a module directly (e.g. scanner/ports)"
    )
    sec_parser.add_argument(
        "--scan", metavar="HOST", help="Quick port scan: --scan <host>"
    )
    sec_parser.add_argument(
        "--ports", default="common", help="Port spec for --scan (default: common)"
    )
    sec_parser.add_argument(
        "--recon", metavar="TARGET", help="Quick OSINT recon: --recon <target>"
    )
    sec_parser.add_argument(
        "--netaudit", action="store_true", help="Run local network audit"
    )
    sec_parser.add_argument(
        "--list", action="store_true", help="List all available security modules"
    )

    # ========================================================================
    # Parse arguments
    # ========================================================================
    args = parser.parse_args()

    # Handle version flag
    if args.version:
        print_version()
        return 0

    # Handle -c / --command (inline code execution)
    if args.ks_command:
        CommandHandler.run_command(args.ks_command)
        return 0

    # Handle no command — launch REPL (same as running with no arguments)
    if not args.command:
        repl_args = argparse.Namespace(
            command="repl", debug=getattr(args, "debug", False)
        )
        CommandHandler.repl(repl_args)
        return 0

    # Set debug environment variable
    if args.debug:
        os.environ["KS_DEBUG"] = "1"

    # Dispatch to handler
    handler_map = {
        "run": CommandHandler.run,
        "build": CommandHandler.build,
        "ring0": CommandHandler.ring0,
        "audit": CommandHandler.audit,
        "privilege_report": CommandHandler.privilege_report,
        "info": CommandHandler.info,
        "debug": CommandHandler.debug,
        "wasm": CommandHandler.wasm,
        "minios": CommandHandler.minios,
        "hardware": CommandHandler.hardware,
        "kernel-dev": CommandHandler.kernel_dev,
        "security": CommandHandler.security,
        "ide": CommandHandler.ide,
    }

    handler = handler_map.get(args.command)
    if handler:
        try:
            handler(args)
            return 0
        except KeyboardInterrupt:
            print("\nInterrupted")
            return 130
        except Exception as e:
            print(f"\n[ERROR] {e}")
            if args.debug:
                traceback.print_exc()
            return 1
    else:
        print(f"Unknown command: {args.command}")
        return 1


# ============================================================================
# FALLBACK FOR SIMPLE COMMANDS (compatibility with old style)
# ============================================================================


def simple_main():
    """
    Handle the natural CLI syntax:
        kentscript file.ks [flags]

    Supported flags (forwarded to ks_core.main_cli()):
        --compile           Transpile .ks → C, compile to binary
        --run               Compile then execute (default when no flag given)
        --native            Compile + run via C transpilation
        --benchmark         Benchmark mode (-O3 + volatile + asm barriers)
        --unsafe-optimization / --aggressive-optimization
        -O0 / -O1 / -O2 / -O3    GCC optimisation level (default -O2)
        --output / -o NAME  Output binary name
        --debug             Verbose debug output

    Old-style aliases still work:
        --ring0 / --freestanding
        --version / -v
    """
    args = sys.argv[1:]

    if not args:
        # REPL mode
        old_args = argparse.Namespace(command="repl", debug=False)
        CommandHandler.repl(old_args)
        return

    # ── version ──────────────────────────────────────────────────────────────
    if args[0] in ("--version", "-v"):
        print_version()
        return

    # ── ring0 / freestanding (old style) ─────────────────────────────────────
    if args[0] in ("--ring0", "--freestanding"):
        old_args = argparse.Namespace(
            command="ring0",
            file=args[1] if len(args) > 1 else None,
            arch="x86_64",
            mode="bare" if args[0] == "--ring0" else "freestanding",
            boot="raw",
            output=None,
            run=False,
            extra_flags=None,
            debug=False,
        )
        CommandHandler.ring0(old_args)
        return

    # ── -c / --command (inline code) ─────────────────────────────────────────
    if args[0] in ("-c", "--command") and len(args) > 1:
        CommandHandler.run_command(args[1])
        return

    # ── file.ks [flags] ───────────────────────────────────────────────────────
    ks_file = args[0]
    if not os.path.isfile(ks_file):
        print(f"[ERROR] File not found: {ks_file}")
        sys.exit(1)

    remaining = args[1:]

    # Parse flags
    compile_mode = False
    run_mode = False
    native_mode = False
    benchmark_mode = False
    unsafe_opt = False
    aggressive_opt = False
    debug = False
    cache_clear = False
    opt_level = "2"  # default

    i = 0
    while i < len(remaining):
        f = remaining[i]
        if f == "--compile":
            compile_mode = True
        elif f == "--run":
            run_mode = True
        elif f == "--native":
            native_mode = True

        elif f == "--benchmark":
            benchmark_mode = True
        elif f == "--unsafe-optimization":
            unsafe_opt = True
        elif f == "--aggressive-optimization":
            aggressive_opt = True
        elif f == "--debug":
            debug = True
        elif f == "--cache-clear":
            cache_clear = True
        elif f in ("-O0", "-O1", "-O2", "-O3"):
            opt_level = f[2]
        elif f == "-O" and i + 1 < len(remaining) and remaining[i + 1] in "0123":
            i += 1
            opt_level = remaining[i]
        i += 1

    # Auto-clear cache when compiling to binary (ensures fresh compilation)
    if cache_clear or native_mode:
        try:
            from ks_core import _KS_CACHE

            _KS_CACHE.clear()
        except:
            pass
            opt_level = remaining[i]
        i += 1

    # Auto-clear cache when compiling to binary (ensures fresh compilation)
    if cache_clear or native_mode:
        try:
            from ks_core import _KS_CACHE

            _KS_CACHE.clear()
        except:
            pass

    # ── Build sys.argv for ks_core.main_cli() ────────────────────────────────
    # ks_core uses:  file [--compile] [--run] [--native] [-O LEVEL] ...
    # IMPORTANT: -O flag takes a SEPARATE argument: '-O', '2'  (not '-O2')
    new_argv = [sys.argv[0], ks_file]

    # Determine execution mode:
    # - Default (no flags): use interpreter directly (fastest for development)
    # - --compile: transpile to C only
    # - --native: compile to binary and run
    # - --run: compile to binary and run (explicit)
    explicit_compile = compile_mode or native_mode

    if explicit_compile:
        # Explicit compilation requested - use main_cli path
        if compile_mode:
            new_argv.append("--compile")
        if native_mode:
            # --native always runs after compiling (for convenience)
            new_argv.append("--native")
            new_argv.append("--run")
        elif run_mode:
            new_argv.append("--run")
        new_argv += ["-O", opt_level]
    else:
        # No explicit compilation - use interpreter directly (fastest)
        # This matches the behavior of: python main.py run file.ks
        pass

    if benchmark_mode:
        new_argv.append("--benchmark")
    if unsafe_opt:
        new_argv.append("--unsafe-optimization")
    if aggressive_opt:
        new_argv.append("--aggressive-optimization")
    if debug:
        new_argv.append("--debug")

    sys.argv = new_argv

    if not explicit_compile:
        # Use interpreter directly (fastest for development)
        try:
            from ks_core import run_file

            run_file(ks_file, use_cache=True)
        except ImportError as e:
            print(f"[ERROR] Could not import ks_core: {e}")
            sys.exit(1)
    else:
        # Use main_cli for compilation modes
        try:
            from ks_core import main_cli

            main_cli()
        except ImportError as e:
            print(f"[ERROR] Could not import ks_core: {e}")
            sys.exit(1)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Intercept installer-managed flags that should never reach argparse.
    if len(sys.argv) > 1 and sys.argv[1] in (
        "--update",
        "--uninstall",
        "--update-check",
    ):
        action = sys.argv[1]
        print(f"\n⚡ KentScript v{__version__}")
        print(f"\n'{action}' is handled by the installer, not the runtime.")
        print(f"  Run:  bash install.sh {action}\n")
        sys.exit(0)

    # Detect "file-first" style: kentscript file.ks [flags...]
    # Any argv[1] that ends with .ks (or is a file that exists) goes to simple_main
    # so ALL flags are properly parsed rather than silently dropped.
    KNOWN_SUBCOMMANDS = {
        "run",
        "build",
        "ring0",
        "info",
        "debug",
        "audit",
        "privilege_report",
        "kernel-dev",
        "minios",
        "hardware",
        "security",
        "ide",
        "--version",
        "-v",
        "--help",
        "-h",
        "--debug",
        "-c",
        "--command",
    }

    if len(sys.argv) > 1:
        first = sys.argv[1]
        # Route to simple_main if:
        #   - first arg ends with .ks, OR
        #   - first arg is a file that exists (e.g. no extension), OR
        #   - first arg is a known old-style flag (--compile, --run, --native, -O*)
        is_ks_file = (
            first.endswith(".ks")
            or (os.path.isfile(first) and first not in KNOWN_SUBCOMMANDS)
            or first
            in (
                "--compile",
                "--run",
                "--native",
                "--benchmark",
                "--unsafe-optimization",
                "--aggressive-optimization",
                "-O0",
                "-O1",
                "-O2",
                "-O3",
                "--ring0",
                "--freestanding",
                "-c",
                "--command",
            )
        )
        if is_ks_file and first not in KNOWN_SUBCOMMANDS:
            simple_main()
        else:
            sys.exit(main())
    else:
        simple_main()  # no args → REPL
