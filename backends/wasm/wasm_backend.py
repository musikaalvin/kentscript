"""
WebAssembly Backend — Full Build Pipeline for KentScript.
[KS-WASM-020] Transpile -> WAT -> wat2wasm -> .wasm binary
[KS-WASM-021] Optional WASM execution via wasmtime/node/wasm3
[KS-WASM-022] Full integration with KentScript build pipeline

Usage:
    from backends.wasm.wasm_backend import WasmBackend
    backend = WasmBackend()
    wat, wasm_path = backend.compile("input.ks")
    backend.run(wasm_path)
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class WasmBackend:
    def __init__(self):
        self.project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.wat2wasm = self._find_tool("wat2wasm")
        self.wasm_run = self._find_wasm_runtime()
        self.temp_files: List[str] = []

    def _find_tool(self, name: str) -> Optional[str]:
        """Find a tool in PATH"""
        result = shutil.which(name)
        if result:
            return result

        common_paths = [
            "/usr/bin", "/usr/local/bin", "/opt/homebrew/bin",
            os.path.expanduser("~/.wasmtime/bin"),
            os.path.expanduser("~/.cargo/bin"),
        ]
        for p in common_paths:
            candidate = os.path.join(p, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    def _find_wasm_runtime(self) -> Optional[str]:
        """Find a WASM runtime for execution"""
        for runtime in ["wasmtime", "node", "wasm3", "wasmer", "iwasm"]:
            found = shutil.which(runtime)
            if found:
                return found
        return None

    def transpile(self, source_path: str, output_path: Optional[str] = None) -> Tuple[str, str]:
        """Transpile KentScript source to WAT and compile to WASM.

        Returns:
            (wat_code, wasm_path)
        """
        from compiler.lexer.lexer import Lexer
        from compiler.parser.parser import Parser
        from backends.wasm.wasm_transpiler import WasmTranspiler
        from backends.wasm.wasm_runtime import WasmRuntime

        with open(source_path, "r") as f:
            source = f.read()

        lexer = Lexer(source, filename=source_path)
        tokens = lexer.tokenize()

        parser = Parser(tokens, source, filename=source_path)
        ast = parser.parse()

        transpiler = WasmTranspiler()
        wat = transpiler.transpile(ast)

        runtime = WasmRuntime()
        runtime_code = runtime.generate()

        if output_path is None:
            base = os.path.splitext(source_path)[0]
            output_path = base + ".wasm"

        wat_path = output_path.replace(".wasm", ".wat")
        combined_wat = "(module\n" + runtime_code + "\n" + wat + "\n)"

        with open(wat_path, "w") as f:
            f.write(combined_wat)

        if self.wat2wasm:
            result = subprocess.run(
                [self.wat2wasm, wat_path, "-o", output_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                print(f"[WASM] wat2wasm error: {result.stderr}", file=sys.stderr)
                print(f"[WASM] WAT saved to {wat_path} for debugging", file=sys.stderr)
                return combined_wat, ""
        else:
            print(f"[WASM] wat2wasm not found. WAT saved to {wat_path}", file=sys.stderr)
            return combined_wat, ""

        # Remove WAT if WASM was generated successfully
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            try:
                os.remove(wat_path)
            except OSError:
                pass
            print(f"[WASM] Compiled: {output_path}")
        else:
            print(f"[WASM] Compilation failed. WAT saved to {wat_path}", file=sys.stderr)

        return combined_wat, output_path

    def compile_to_wat(self, source_path: str) -> Tuple[str, str]:
        """Compile KentScript to WAT only (no binary generation).

        Returns:
            (wat_code, wat_path)
        """
        from compiler.lexer.lexer import Lexer
        from compiler.parser.parser import Parser
        from backends.wasm.wasm_transpiler import WasmTranspiler
        from backends.wasm.wasm_runtime import WasmRuntime

        with open(source_path, "r") as f:
            source = f.read()

        lexer = Lexer(source, filename=source_path)
        tokens = lexer.tokenize()

        parser = Parser(tokens, source, filename=source_path)
        ast = parser.parse()

        transpiler = WasmTranspiler()
        wat = transpiler.transpile(ast)

        runtime = WasmRuntime()
        runtime_code = runtime.generate()

        wat_path = source_path.replace(".ks", ".wat")

        combined_wat = "(module\n" + runtime_code + "\n" + wat + "\n)"

        with open(wat_path, "w") as f:
            f.write(combined_wat)

        print(f"[WASM] WAT output: {wat_path}")
        return combined_wat, wat_path

    def run(self, wasm_path: str, runtime: Optional[str] = None) -> int:
        """Execute a .wasm binary using an available runtime.

        Args:
            wasm_path: Path to .wasm file
            runtime: Specific runtime to use (wasmtime, node, etc.)

        Returns:
            Exit code
        """
        if not os.path.isfile(wasm_path):
            print(f"[WASM] File not found: {wasm_path}", file=sys.stderr)
            return 1

        runner = runtime or self.wasm_run
        if not runner:
            print("[WASM] No WASM runtime found. Install wasmtime:", file=sys.stderr)
            print("  curl https://wasmtime.dev/install.sh | bash", file=sys.stderr)
            return 1

        runner_name = os.path.basename(runner)

        try:
            if runner_name == "wasmtime":
                result = subprocess.run(
                    [runner, "run", "--dir", ".", wasm_path],
                    timeout=30
                )
            elif runner_name == "node":
                js_wrapper = self._generate_node_wrapper(wasm_path)
                with tempfile.NamedTemporaryFile(suffix=".mjs", delete=False, mode="w") as f:
                    f.write(js_wrapper)
                    wrapper_path = f.name
                result = subprocess.run(
                    [runner, wrapper_path],
                    timeout=30
                )
                os.unlink(wrapper_path)
            elif runner_name in ("wasm3", "wasmer"):
                result = subprocess.run(
                    [runner, wasm_path],
                    timeout=30
                )
            elif runner_name == "iwasm":
                result = subprocess.run(
                    [runner, wasm_path],
                    timeout=30
                )
            else:
                result = subprocess.run(
                    [runner, wasm_path],
                    timeout=30
                )
            return result.returncode
        except subprocess.TimeoutExpired:
            print(f"[WASM] Execution timed out", file=sys.stderr)
            return 1
        except FileNotFoundError:
            print(f"[WASM] Runtime '{runner}' not found", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[WASM] Execution error: {e}", file=sys.stderr)
            return 1

    def _generate_node_wrapper(self, wasm_path: str) -> str:
        """Generate a Node.js wrapper to load and run the WASM module"""
        return f'''\
import fs from "fs";
import {{ WASI }} from "node:wasi";
import {{ argv, env }} from "node:process";

const wasi = new WASI({{
  version: "preview1",
  args: argv,
  env,
  preopens: {{ ".": "." }}
}});

const wasmBuffer = fs.readFileSync("{os.path.abspath(wasm_path)}");
const {{ instance }} = await WebAssembly.instantiate(wasmBuffer, {{
  wasi_unstable: wasi.wasiImport
}});

wasi.start(instance);
'''

    def list_runtimes(self) -> List[str]:
        """List available WASM runtimes"""
        available = []
        for rt in ["wasmtime", "node", "wasm3", "wasmer", "iwasm"]:
            found = shutil.which(rt)
            if found:
                available.append(f"{rt} ({found})")
        return available

    def cleanup(self):
        """Clean up temporary files"""
        for f in self.temp_files:
            try:
                if os.path.isfile(f):
                    os.remove(f)
            except OSError:
                pass
        self.temp_files = []

    def __del__(self):
        self.cleanup()
