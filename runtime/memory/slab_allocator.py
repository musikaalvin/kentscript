#!/usr/bin/env python3
"""
slab_allocator.py — Real KentScript Slab Allocator

Thin Python wrapper around ks_slab.so — a genuine mmap-backed slab allocator
written in C. This replaces the old pure-Python simulation.

The shared library (ks_slab.so) is built from ks_slab.c:
    gcc -O3 -shared -fPIC -o ks_slab.so ks_slab.c -lpthread

Features (real, in C):
  - 14 size classes: 8 B → 64 KB — O(1) alloc/free
  - mmap-backed slabs with MADV_DONTNEED on empty slab
  - 64-byte cache-line alignment throughout
  - Thread-safe: per-pool pthread mutexes
  - Real memory barriers: mfence (x86_64) / dmb ish (ARM64)
  - Large allocations (> 64 KB): direct anonymous mmap with header
  - ks_write8/32/64 / ks_read8/32/64: volatile pointer R/W with barriers
"""

import os
import sys
import ctypes
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any

# ─── locate and build the shared library ─────────────────────────────────────

_HERE = Path(__file__).parent.resolve()
_SO   = _HERE / "ks_slab.so"
_SRC  = _HERE / "ks_slab.c"

def _build_so() -> bool:
    """Compile ks_slab.c → ks_slab.so if needed."""
    if not _SRC.exists():
        return False
    if _SO.exists() and _SO.stat().st_mtime >= _SRC.stat().st_mtime:
        return True
    cmd = ["gcc", "-O3", "-shared", "-fPIC",
           "-o", str(_SO), str(_SRC), "-lpthread"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[slab_allocator] Build failed:\n{result.stderr}", file=sys.stderr)
        return False
    return True

_lib: Optional[ctypes.CDLL] = None
_lib_lock = threading.Lock()

def _load_lib() -> Optional[ctypes.CDLL]:
    global _lib
    if _lib is not None:
        return _lib
    with _lib_lock:
        if _lib is not None:
            return _lib
        if not _build_so():
            return None
        try:
            lib = ctypes.CDLL(str(_SO))
        except OSError as e:
            print(f"[slab_allocator] Cannot load {_SO}: {e}", file=sys.stderr)
            return None

        # ── set argtypes / restypes ──────────────────────────────────────────
        c_u64 = ctypes.c_uint64
        c_u32 = ctypes.c_uint32
        c_u8  = ctypes.c_uint8
        c_i64 = ctypes.c_int64
        c_int = ctypes.c_int
        c_sz  = ctypes.c_size_t
        c_void= None

        lib.ks_malloc.argtypes   = [c_u64];          lib.ks_malloc.restype   = c_u64
        lib.ks_calloc.argtypes   = [c_u64];          lib.ks_calloc.restype   = c_u64
        lib.ks_free.argtypes     = [c_u64];          lib.ks_free.restype     = c_i64
        lib.ks_realloc.argtypes  = [c_u64, c_u64];  lib.ks_realloc.restype  = c_u64
        lib.ks_memset.argtypes   = [c_u64, c_int, c_u64]; lib.ks_memset.restype = c_void
        lib.ks_memcpy.argtypes   = [c_u64, c_u64, c_u64]; lib.ks_memcpy.restype = c_void
        lib.ks_memmove.argtypes  = [c_u64, c_u64, c_u64]; lib.ks_memmove.restype= c_void
        lib.ks_write8.argtypes   = [c_u64, c_u8];   lib.ks_write8.restype   = c_void
        lib.ks_read8.argtypes    = [c_u64];          lib.ks_read8.restype    = c_u8
        lib.ks_write32.argtypes  = [c_u64, c_u32];  lib.ks_write32.restype  = c_void
        lib.ks_read32.argtypes   = [c_u64];          lib.ks_read32.restype   = c_u32
        lib.ks_write64.argtypes  = [c_u64, c_u64];  lib.ks_write64.restype  = c_void
        lib.ks_read64.argtypes   = [c_u64];          lib.ks_read64.restype   = c_u64
        lib.ks_barrier.argtypes  = [];               lib.ks_barrier.restype  = c_void
        lib.ks_stats_json.argtypes = [ctypes.c_char_p, c_sz]
        lib.ks_stats_json.restype  = c_void
        lib.ks_destroy.argtypes  = [];               lib.ks_destroy.restype  = c_void

        _lib = lib
        return _lib


# ─── Pointer64 — 64-bit address wrapper ──────────────────────────────────────

class Pointer64:
    """64-bit pointer returned by the slab allocator."""
    __slots__ = ("_addr",)

    def __init__(self, addr: int):
        if addr < 0 or addr > 0xFFFFFFFFFFFFFFFF:
            raise ValueError(f"Address out of 64-bit range: {addr}")
        self._addr = addr

    @property
    def addr(self) -> int:
        return self._addr

    def __add__(self, n: int) -> "Pointer64":
        return Pointer64(self._addr + n)

    def __sub__(self, n: int) -> "Pointer64":
        result = self._addr - n
        if result < 0:
            raise OverflowError(f"Pointer underflow: {self} - {n}")
        return Pointer64(result)

    def __int__(self)    -> int:  return self._addr
    def __bool__(self)   -> bool: return self._addr != 0
    def __eq__(self, o)  -> bool: return self._addr == (int(o) if not isinstance(o, int) else o)
    def __hash__(self)   -> int:  return hash(self._addr)
    def __repr__(self)   -> str:  return f"Ptr64(0x{self._addr:x})"

    def is_null(self) -> bool:
        return self._addr == 0

    def is_aligned(self, align: int) -> bool:
        return (self._addr & (align - 1)) == 0

    def align_up(self, align: int) -> "Pointer64":
        return Pointer64((self._addr + align - 1) & ~(align - 1))


# ─── SlabAllocator — main Python API ─────────────────────────────────────────

class SlabAllocator:
    """
    Real mmap-backed slab allocator. All allocation is done by ks_slab.so
    (compiled C), not Python. This class provides a convenient Python API.
    """

    _FALLBACK_AVAILABLE = False   # set True if .so load fails (pure fallback)

    def __init__(self):
        self._lib = _load_lib()
        if self._lib is None:
            print("[SlabAllocator] WARNING: C library unavailable — no allocation possible",
                  file=sys.stderr)
        self._stats_buf = ctypes.create_string_buffer(512)

    # ── core operations ──────────────────────────────────────────────────────

    def malloc(self, size: int, numa_node: int = -1) -> Pointer64:
        """Allocate `size` bytes. Returns Pointer64 (addr=0 on failure)."""
        if self._lib is None or size <= 0:
            return Pointer64(0)
        addr = self._lib.ks_malloc(size)
        return Pointer64(addr)

    def calloc(self, size: int) -> Pointer64:
        """Allocate zero-initialised `size` bytes."""
        if self._lib is None or size <= 0:
            return Pointer64(0)
        return Pointer64(self._lib.ks_calloc(size))

    def free(self, ptr) -> bool:
        """Free a previously allocated pointer. Returns True on success."""
        if self._lib is None:
            return False
        addr = int(ptr) if isinstance(ptr, Pointer64) else int(ptr)
        return self._lib.ks_free(addr) == 0

    def realloc(self, ptr, new_size: int) -> Pointer64:
        """Reallocate to new_size. Returns new Pointer64."""
        if self._lib is None:
            return Pointer64(0)
        addr = int(ptr) if isinstance(ptr, Pointer64) else int(ptr)
        return Pointer64(self._lib.ks_realloc(addr, new_size))

    def memset(self, ptr, val: int, length: int):
        """Fill `length` bytes at ptr with `val`."""
        if self._lib:
            self._lib.ks_memset(int(ptr), val, length)

    def memcpy(self, dst, src, length: int):
        """Copy `length` bytes from src to dst."""
        if self._lib:
            self._lib.ks_memcpy(int(dst), int(src), length)

    def memmove(self, dst, src, length: int):
        """Move `length` bytes from src to dst (handles overlap)."""
        if self._lib:
            self._lib.ks_memmove(int(dst), int(src), length)

    # ── typed memory access (with hardware barriers) ─────────────────────────

    def write8(self, ptr, val: int):
        if self._lib: self._lib.ks_write8(int(ptr), val & 0xFF)

    def read8(self, ptr) -> int:
        return self._lib.ks_read8(int(ptr)) if self._lib else 0

    def write32(self, ptr, val: int):
        if self._lib: self._lib.ks_write32(int(ptr), val & 0xFFFFFFFF)

    def read32(self, ptr) -> int:
        return self._lib.ks_read32(int(ptr)) if self._lib else 0

    def write64(self, ptr, val: int):
        if self._lib: self._lib.ks_write64(int(ptr), val & 0xFFFFFFFFFFFFFFFF)

    def read64(self, ptr) -> int:
        return self._lib.ks_read64(int(ptr)) if self._lib else 0

    def barrier(self):
        """Full hardware memory barrier (mfence / dmb ish)."""
        if self._lib: self._lib.ks_barrier()

    # ── stats / lifecycle ─────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return allocation statistics from the C library."""
        if self._lib is None:
            return {"error": "C library not loaded"}
        self._lib.ks_stats_json(self._stats_buf, 512)
        import json
        try:
            return json.loads(self._stats_buf.value.decode())
        except Exception:
            return {"raw": self._stats_buf.value.decode()}

    def destroy(self):
        """Release all slabs back to the OS."""
        if self._lib:
            self._lib.ks_destroy()

    def __del__(self):
        pass  # ks_destroy is explicit; don't auto-destroy on GC


# ─── global convenience functions ────────────────────────────────────────────

_GLOBAL: Optional[SlabAllocator] = None
_GLOBAL_LOCK = threading.Lock()

def get_global_allocator() -> SlabAllocator:
    global _GLOBAL
    if _GLOBAL is None:
        with _GLOBAL_LOCK:
            if _GLOBAL is None:
                _GLOBAL = SlabAllocator()
    return _GLOBAL

def ks_malloc(size: int) -> Pointer64:
    return get_global_allocator().malloc(size)

def ks_calloc(size: int) -> Pointer64:
    return get_global_allocator().calloc(size)

def ks_free(ptr) -> bool:
    return get_global_allocator().free(ptr)

def ks_realloc(ptr, new_size: int) -> Pointer64:
    return get_global_allocator().realloc(ptr, new_size)

def ks_malloc_stats() -> Dict[str, Any]:
    return get_global_allocator().get_stats()


# ─── self-test ───────────────────────────────────────────────────────────────

def _test():
    print("Testing Real SlabAllocator (ks_slab.so) ...")
    a = SlabAllocator()

    # Basic allocation
    p = a.malloc(64)
    assert p and not p.is_null(), "malloc(64) failed"
    assert p.is_aligned(8), "not 8-byte aligned"
    print(f"  malloc(64)   -> {p}")

    # Write / read back
    a.write64(p, 0xCAFEBABE_DEADBEEF)
    v = a.read64(p)
    assert v == 0xCAFEBABE_DEADBEEF, f"read back mismatch: 0x{v:x}"
    print(f"  write/read64 -> 0x{v:x}  ✓")

    # Free
    assert a.free(p), "free failed"
    print(f"  free         -> ok  ✓")

    # Calloc (must be zeroed)
    p2 = a.calloc(128)
    assert not p2.is_null()
    v2 = a.read64(p2)
    assert v2 == 0, f"calloc not zeroed: 0x{v2:x}"
    print(f"  calloc(128)  -> zeroed  ✓")
    a.free(p2)

    # Realloc
    p3 = a.malloc(32)
    a.write32(p3, 0xABCD1234)
    p4 = a.realloc(p3, 256)
    assert not p4.is_null()
    v4 = a.read32(p4)
    assert v4 == 0xABCD1234, f"realloc data lost: 0x{v4:x}"
    print(f"  realloc      -> data preserved  ✓")
    a.free(p4)

    # Large allocation (> 64 KB)
    pl = a.malloc(200_000)
    assert not pl.is_null()
    print(f"  malloc(200K) -> {pl}  ✓")
    a.free(pl)

    # Stats
    stats = a.get_stats()
    print(f"  stats        -> {stats}")

    # Barrier
    a.barrier()
    print(f"  barrier()    -> ok  ✓")

    print("All tests passed!")

if __name__ == "__main__":
    _test()
