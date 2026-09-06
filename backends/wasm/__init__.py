"""
WebAssembly Backend for KentScript.

Modules:
    wasm_transpiler   — KentScript AST → WAT (WebAssembly Text Format)
    wasm_runtime      — WASM runtime support (WASI, allocator, print, string ops)
    wasm_backend      — Full build pipeline: transpile → WAT → wat2wasm → .wasm

Usage:
    from backends.wasm.wasm_backend import WasmBackend
    backend = WasmBackend()
    wat, wasm_path = backend.transpile("input.ks")
    backend.run(wasm_path)
"""

from backends.wasm.wasm_transpiler import WasmTranspiler
from backends.wasm.wasm_runtime import WasmRuntime
from backends.wasm.wasm_backend import WasmBackend

__all__ = ["WasmTranspiler", "WasmRuntime", "WasmBackend"]
