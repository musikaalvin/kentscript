#!/usr/bin/env python3
"""
memory.py — KentScript Real Memory Management

Wraps ks_runtime.so and ks_slab.so — both real C shared libraries —
to provide KentScript's memory subsystem.

Real operations:
  - mmap/munmap (anonymous pages, executable pages)
  - Slab allocator (O(1), 14 size classes, 8 B → 64 KB)
  - Atomic operations (seq_cst: __atomic_fetch_add, CAS, etc.)
  - Memory barriers (mfence/lfence/sfence on x86; dmb on ARM64)
  - Lock-free SPSC ring buffer
  - Thread-safe hash map (FNV-1a, open-addressing)
"""

import os
import sys
import ctypes
import subprocess
import threading
from pathlib import Path
from typing import Optional, Any, Dict

# ─── shared library loading ───────────────────────────────────────────────────

_HERE = Path(__file__).parent.resolve()

def _load(name: str, src: str, extra_flags: list = None) -> Optional[ctypes.CDLL]:
    so  = _HERE / f"{name}.so"
    src_path = _HERE / src
    if not src_path.exists():
        return None
    if not so.exists() or so.stat().st_mtime < src_path.stat().st_mtime:
        flags = ["-O3", "-shared", "-fPIC", "-o", str(so), str(src_path)]
        flags += (extra_flags or [])
        r = subprocess.run(["gcc"] + flags, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[memory] Build of {name}.so failed:\n{r.stderr}", file=sys.stderr)
            return None
    try:
        return ctypes.CDLL(str(so))
    except OSError as e:
        print(f"[memory] Cannot load {so}: {e}", file=sys.stderr)
        return None


_rt  = _load("ks_runtime", "ks_runtime.c", ["-lpthread", "-lm"])
_slab = _load("ks_slab",    "ks_slab.c",    ["-lpthread"])

def _setup(lib, specs):
    """Set argtypes/restypes from a list of (name, restype, argtypes)."""
    if lib is None:
        return
    for name, restype, argtypes in specs:
        try:
            fn = getattr(lib, name)
            fn.restype  = restype
            fn.argtypes = argtypes
        except AttributeError:
            pass

c_u64 = ctypes.c_uint64
c_u32 = ctypes.c_uint32
c_u8  = ctypes.c_uint8
c_i64 = ctypes.c_int64
c_int = ctypes.c_int
c_sz  = ctypes.c_size_t
c_dbl = ctypes.c_double
c_str = ctypes.c_char_p
c_vp  = ctypes.c_void_p
c_bool= ctypes.c_bool

_setup(_rt, [
    ("ks_mmap_anon",    c_vp,  [c_sz]),
    ("ks_munmap",       c_int, [c_vp, c_sz]),
    ("ks_mmap_exec",    c_vp,  [c_sz]),
    ("ks_mprotect",     c_int, [c_vp, c_sz, c_int]),
    ("ks_fast_zero",    None,  [c_vp, c_sz]),
    ("ks_fast_copy",    None,  [c_vp, c_vp, c_sz]),
    ("ks_fast_move",    None,  [c_vp, c_vp, c_sz]),
    ("ks_atomic_add",   c_i64, [ctypes.POINTER(c_i64), c_i64]),
    ("ks_atomic_sub",   c_i64, [ctypes.POINTER(c_i64), c_i64]),
    ("ks_atomic_load",  c_i64, [ctypes.POINTER(c_i64)]),
    ("ks_atomic_store", None,  [ctypes.POINTER(c_i64), c_i64]),
    ("ks_atomic_cas",   c_bool,[ctypes.POINTER(c_i64), c_i64, c_i64]),
    ("ks_atomic_exchange",c_i64,[ctypes.POINTER(c_i64), c_i64]),
    ("ks_full_barrier", None,  []),
    ("ks_read_barrier", None,  []),
    ("ks_write_barrier",None,  []),
    ("ks_time_ns",      c_i64, []),
    ("ks_time_us",      c_i64, []),
    ("ks_time_ms",      c_i64, []),
    ("ks_sleep_ns",     None,  [c_i64]),
    ("ks_sleep_us",     None,  [c_i64]),
    ("ks_sleep_ms",     None,  [c_i64]),
    ("ks_sqrt",         c_dbl, [c_dbl]),
    ("ks_pow",          c_dbl, [c_dbl, c_dbl]),
    ("ks_fabs",         c_dbl, [c_dbl]),
    ("ks_floor",        c_dbl, [c_dbl]),
    ("ks_ceil",         c_dbl, [c_dbl]),
    ("ks_round",        c_dbl, [c_dbl]),
    ("ks_log",          c_dbl, [c_dbl]),
    ("ks_exp",          c_dbl, [c_dbl]),
    ("ks_popcount64",   c_int, [c_u64]),
    ("ks_clz64",        c_int, [c_u64]),
    ("ks_ctz64",        c_int, [c_u64]),
    ("ks_isqrt",        c_u64, [c_u64]),
    ("ks_sort_i64",     None,  [ctypes.POINTER(c_i64), c_sz]),
    ("ks_sort_f64",     None,  [ctypes.POINTER(c_dbl), c_sz]),
    ("ks_bsearch_i64",  c_i64, [ctypes.POINTER(c_i64), c_sz, c_i64]),
    ("ks_strlen",       c_sz,  [c_str]),
    ("ks_strcmp",       c_int, [c_str, c_str]),
    ("ks_strdup",       c_str, [c_str]),
    ("ks_str_find",     c_i64, [c_str, c_str]),
    ("ks_str_replace",  c_str, [c_str, c_str, c_str]),
    ("ks_str_to_i64",   c_i64, [c_str, c_int]),
    ("ks_str_to_f64",   c_dbl, [c_str]),
    ("ks_i64_to_str",   c_int, [c_i64, ctypes.c_char_p, c_sz]),
    ("ks_f64_to_str",   c_int, [c_dbl, ctypes.c_char_p, c_sz]),
    ("ks_map_new",      c_vp,  [c_sz]),
    ("ks_map_free",     None,  [c_vp]),
    ("ks_map_set",      None,  [c_vp, c_str, c_vp]),
    ("ks_map_get",      c_vp,  [c_vp, c_str]),
    ("ks_map_size",     c_sz,  [c_vp]),
    ("ks_ring_new",     c_vp,  [c_sz]),
    ("ks_ring_free",    None,  [c_vp]),
    ("ks_ring_push",    c_bool,[c_vp, c_vp]),
    ("ks_ring_pop",     c_bool,[c_vp, ctypes.POINTER(c_vp)]),
    ("ks_runtime_info", None,  [ctypes.c_char_p, c_sz]),
    ("ks_page_size",    ctypes.c_long, []),
    ("ks_cpu_count",    ctypes.c_long, []),
])

_setup(_slab, [
    ("ks_malloc",      c_u64, [c_u64]),
    ("ks_calloc",      c_u64, [c_u64]),
    ("ks_free",        c_i64, [c_u64]),
    ("ks_realloc",     c_u64, [c_u64, c_u64]),
    ("ks_memset",      None,  [c_u64, c_int, c_u64]),
    ("ks_memcpy",      None,  [c_u64, c_u64, c_u64]),
    ("ks_write8",      None,  [c_u64, c_u8]),
    ("ks_read8",       c_u8,  [c_u64]),
    ("ks_write32",     None,  [c_u64, c_u32]),
    ("ks_read32",      c_u32, [c_u64]),
    ("ks_write64",     None,  [c_u64, c_u64]),
    ("ks_read64",      c_u64, [c_u64]),
    ("ks_barrier",     None,  []),
    ("ks_stats_json",  None,  [ctypes.c_char_p, c_sz]),
    ("ks_destroy",     None,  []),
])


# ─── public Python API ────────────────────────────────────────────────────────

_available = _rt is not None or _slab is not None


# ── mmap ─────────────────────────────────────────────────────────────────────

def mmap_anon(size: int) -> int:
    """Allocate anonymous private memory. Returns address or 0."""
    if _rt is None: return 0
    p = _rt.ks_mmap_anon(size)
    return p or 0

def munmap(addr: int, size: int) -> int:
    """Release mmap'd memory."""
    return _rt.ks_munmap(addr, size) if _rt else -1

def mmap_exec(size: int) -> int:
    """Allocate RWX memory (for JIT code)."""
    if _rt is None: return 0
    return _rt.ks_mmap_exec(size) or 0


# ── slab alloc ────────────────────────────────────────────────────────────────

def malloc(size: int) -> int:
    """Slab-allocate size bytes. Returns address or 0."""
    return _slab.ks_malloc(size) if _slab else 0

def calloc(size: int) -> int:
    """Slab-allocate zeroed size bytes."""
    return _slab.ks_calloc(size) if _slab else 0

def free(addr: int) -> bool:
    """Free slab-allocated address."""
    return (_slab.ks_free(addr) == 0) if _slab else False

def realloc(addr: int, new_size: int) -> int:
    """Reallocate to new_size. Returns new address."""
    return _slab.ks_realloc(addr, new_size) if _slab else 0

def write8(addr: int, val: int):  _slab and _slab.ks_write8(addr, val & 0xFF)
def read8 (addr: int) -> int:     return _slab.ks_read8(addr)  if _slab else 0
def write32(addr: int, val: int): _slab and _slab.ks_write32(addr, val & 0xFFFFFFFF)
def read32 (addr: int) -> int:    return _slab.ks_read32(addr) if _slab else 0
def write64(addr: int, val: int): _slab and _slab.ks_write64(addr, val & 0xFFFFFFFFFFFFFFFF)
def read64 (addr: int) -> int:    return _slab.ks_read64(addr) if _slab else 0


# ── barriers ──────────────────────────────────────────────────────────────────

def barrier():       _slab and _slab.ks_barrier()
def full_barrier():  _rt   and _rt.ks_full_barrier()
def read_barrier():  _rt   and _rt.ks_read_barrier()
def write_barrier(): _rt   and _rt.ks_write_barrier()


# ── atomics ───────────────────────────────────────────────────────────────────

class AtomicI64:
    """A 64-bit integer with hardware atomic operations (seq_cst)."""
    def __init__(self, init: int = 0):
        self._cell = (c_i64 * 1)(init)

    def load(self) -> int:
        return _rt.ks_atomic_load(self._cell) if _rt else self._cell[0]

    def store(self, val: int):
        if _rt: _rt.ks_atomic_store(self._cell, val)
        else:   self._cell[0] = val

    def add(self, val: int) -> int:
        return _rt.ks_atomic_add(self._cell, val) if _rt else self._cell[0]

    def sub(self, val: int) -> int:
        return _rt.ks_atomic_sub(self._cell, val) if _rt else self._cell[0]

    def cas(self, expected: int, desired: int) -> bool:
        return bool(_rt.ks_atomic_cas(self._cell, expected, desired)) if _rt else False

    def exchange(self, val: int) -> int:
        return _rt.ks_atomic_exchange(self._cell, val) if _rt else self._cell[0]

    def __int__(self): return self.load()
    def __repr__(self): return f"AtomicI64({self.load()})"


# ── time ──────────────────────────────────────────────────────────────────────

def time_ns() -> int:  return _rt.ks_time_ns() if _rt else 0
def time_us() -> int:  return _rt.ks_time_us() if _rt else 0
def time_ms() -> int:  return _rt.ks_time_ms() if _rt else 0

def sleep_us(us: int): _rt and _rt.ks_sleep_us(us)
def sleep_ms(ms: int): _rt and _rt.ks_sleep_ms(ms)


# ── math ──────────────────────────────────────────────────────────────────────

def ks_sqrt(x: float) -> float:  return _rt.ks_sqrt(x)  if _rt else x**0.5
def ks_pow (x: float, y: float) -> float: return _rt.ks_pow(x,y) if _rt else x**y
def ks_isqrt(n: int) -> int:     return _rt.ks_isqrt(n) if _rt else int(n**0.5)
def ks_popcount(x: int) -> int:  return _rt.ks_popcount64(x) if _rt else bin(x).count('1')


# ── sort / search ─────────────────────────────────────────────────────────────

def sort_i64(lst: list) -> list:
    n   = len(lst)
    arr = (c_i64 * n)(*lst)
    if _rt: _rt.ks_sort_i64(arr, n)
    return list(arr)

def bsearch_i64(lst: list, key: int) -> int:
    n   = len(lst)
    arr = (c_i64 * n)(*lst)
    return _rt.ks_bsearch_i64(arr, n, key) if _rt else -1


# ── ring buffer ───────────────────────────────────────────────────────────────

class RingBuffer:
    """Lock-free SPSC ring buffer backed by ks_runtime.c."""
    def __init__(self, cap: int = 64):
        self._ptr = _rt.ks_ring_new(cap) if _rt else None

    def push(self, item_addr: int) -> bool:
        return bool(_rt.ks_ring_push(self._ptr, item_addr)) if self._ptr else False

    def pop(self) -> Optional[int]:
        if not self._ptr: return None
        out = c_vp(0)
        ok  = _rt.ks_ring_pop(self._ptr, ctypes.byref(out))
        return out.value if ok else None

    def __del__(self):
        if self._ptr and _rt:
            _rt.ks_ring_free(self._ptr)


# ── stats ─────────────────────────────────────────────────────────────────────

def slab_stats() -> Dict[str, Any]:
    if not _slab: return {"error": "slab library not loaded"}
    buf = ctypes.create_string_buffer(512)
    _slab.ks_stats_json(buf, 512)
    import json
    try:    return json.loads(buf.value.decode())
    except: return {"raw": buf.value.decode()}

def runtime_info() -> str:
    if not _rt: return "KentScript runtime not loaded"
    buf = ctypes.create_string_buffer(256)
    _rt.ks_runtime_info(buf, 256)
    return buf.value.decode()

def page_size() -> int:
    return _rt.ks_page_size() if _rt else 4096

def cpu_count() -> int:
    return _rt.ks_cpu_count() if _rt else 1


# ─── self-test ────────────────────────────────────────────────────────────────

def _test():
    print("Testing KentScript Memory Module...")
    print(f"  {runtime_info()}")
    print(f"  page_size={page_size()} cpu_count={cpu_count()}")

    # mmap
    addr = mmap_anon(4096)
    assert addr != 0
    print(f"  mmap_anon(4096) = 0x{addr:x}  ✓")
    munmap(addr, 4096)

    # slab
    p = malloc(64)
    assert p != 0
    write64(p, 0xDEADCAFE)
    v = read64(p)
    assert v == 0xDEADCAFE, f"0x{v:x}"
    free(p)
    print(f"  slab malloc/write64/read64/free  ✓")

    # atomics
    a = AtomicI64(0)
    a.add(10); a.add(5)
    assert int(a) == 15
    ok = a.cas(15, 42)
    assert ok and int(a) == 42
    print(f"  AtomicI64 add/cas = {int(a)}  ✓")

    # barriers
    barrier(); full_barrier(); read_barrier(); write_barrier()
    print(f"  barriers  ✓")

    # sort
    sorted_lst = sort_i64([5, 3, 1, 4, 2])
    assert sorted_lst == [1, 2, 3, 4, 5]
    print(f"  sort_i64([5,3,1,4,2]) = {sorted_lst}  ✓")

    # bsearch
    idx = bsearch_i64([1, 2, 3, 4, 5], 3)
    assert idx == 2
    print(f"  bsearch_i64(..., 3) = {idx}  ✓")

    # math
    assert abs(ks_sqrt(2.0) - 1.41421356) < 1e-6
    assert ks_isqrt(144) == 12
    print(f"  sqrt(2)={ks_sqrt(2.0):.6f}  isqrt(144)={ks_isqrt(144)}  ✓")

    # time
    t1 = time_ns(); t2 = time_ns()
    assert t2 >= t1
    print(f"  time_ns = {t1}  ✓")

    # stats
    stats = slab_stats()
    print(f"  slab stats = {stats}")

    print("All tests passed!")


if __name__ == "__main__":
    _test()
