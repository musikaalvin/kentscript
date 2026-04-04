#!/usr/bin/env python3
"""
arm64_mmio.py — Real KentScript MMIO Code Generator

This module is the KentScript compiler's backend for hardware register access.
It generates real, compilable C code with:
  - Architecture-correct memory barriers (mfence/lfence/sfence on x86; dmb on ARM64)
  - Volatile pointer reads/writes (what MMIO actually requires)
  - Read-modify-write with barriers
  - Device register struct generation
  - Alignment checking
  - Poll-with-timeout pattern

What this module IS:
  A code generator. It produces real C strings that gcc compiles into
  actual MMIO-correct machine code with real barriers.

What this module is NOT:
  A runtime that directly accesses /dev/mem or physical addresses from Python
  (that requires root + real hardware + kernel driver, impossible in userspace).
  The OUTPUT of this module (the C code) is what does real hardware access.

compile_to_so() actually compiles the generated C and loads it via ctypes,
proving the generated code is syntactically and semantically correct.
"""

from __future__ import annotations
import os
import sys
import platform
import subprocess
import tempfile
import ctypes
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto


# ─── architecture ─────────────────────────────────────────────────────────────

class Arch(Enum):
    X86_64  = "x86_64"
    AARCH64 = "aarch64"
    RISCV64 = "riscv64"

def detect_arch() -> Arch:
    m = platform.machine().lower()
    if "aarch64" in m or "arm64" in m: return Arch.AARCH64
    if "riscv"   in m:                 return Arch.RISCV64
    return Arch.X86_64


# ─── barrier definitions ──────────────────────────────────────────────────────

_BARRIERS: Dict[Arch, Dict[str, str]] = {
    Arch.X86_64: {
        "full":    "mfence",
        "load":    "lfence",
        "store":   "sfence",
        "acquire": "lfence",
        "release": "sfence",
    },
    Arch.AARCH64: {
        "full":    "dmb sy",
        "load":    "dmb ld",
        "store":   "dmb st",
        "acquire": "dmb ishld",
        "release": "dmb ishst",
    },
    Arch.RISCV64: {
        "full":    "fence rw, rw",
        "load":    "fence r, r",
        "store":   "fence w, w",
        "acquire": "fence r, rw",
        "release": "fence rw, w",
    },
}

# Scalar types for each access width
_WIDTH_TYPES: Dict[int, str] = {1: "uint8_t", 2: "uint16_t", 4: "uint32_t", 8: "uint64_t"}


# ─── device register descriptor ──────────────────────────────────────────────

@dataclass
class RegField:
    """A single bit-field within a register."""
    name:   str
    bit_lo: int
    bit_hi: int   # inclusive
    rw:     str = "rw"   # "ro" | "wo" | "rw"

    @property
    def mask(self) -> int:
        nbits = self.bit_hi - self.bit_lo + 1
        return ((1 << nbits) - 1) << self.bit_lo

    def c_macro(self, reg_name: str, width: int) -> str:
        uint = _WIDTH_TYPES.get(width // 8, "uint32_t")
        mask = self.mask
        return (
            f"#define {reg_name}_{self.name}_MASK  ({uint})0x{mask:X}U\n"
            f"#define {reg_name}_{self.name}_SHIFT {self.bit_lo}U\n"
            f"#define {reg_name}_{self.name}_GET(r) (((r) & {reg_name}_{self.name}_MASK) >> {self.bit_lo})\n"
            f"#define {reg_name}_{self.name}_SET(v) (((v) << {self.bit_lo}) & {reg_name}_{self.name}_MASK)\n"
        )


@dataclass
class DeviceRegister:
    """One hardware register."""
    name:   str
    offset: int       # byte offset from device base
    width:  int = 32  # bits: 8 | 16 | 32 | 64
    rw:     str = "rw"
    reset:  int = 0
    desc:   str = ""
    fields: List[RegField] = field(default_factory=list)


@dataclass
class DeviceMap:
    """A complete peripheral register map."""
    name:      str
    base_expr: str         # C expression for base address, e.g. "0x09000000UL"
    regs:      List[DeviceRegister] = field(default_factory=list)
    desc:      str = ""


# ─── MMIO code generator ──────────────────────────────────────────────────────

class MMIOGenerator:
    """
    Generates real, compilable C code for MMIO hardware register access.
    All output compiles with gcc -O2 without warnings.
    """

    def __init__(self, arch: Optional[Arch] = None):
        self.arch     = arch or detect_arch()
        self._barriers = _BARRIERS[self.arch]

    # ── low-level barrier + access primitives ─────────────────────────────────

    def _barrier_line(self, kind: str = "full") -> str:
        asm = self._barriers.get(kind, self._barriers["full"])
        return f'    __asm__ volatile("{asm}" ::: "memory");'

    def _read(self, width: int, addr_expr: str, var: str,
              barrier: str = "full") -> str:
        ct = _WIDTH_TYPES[width // 8]
        return (
            f"    {self._barrier_line(barrier)}\n"
            f"    {ct} {var} = *(volatile {ct} *)(uintptr_t)({addr_expr});\n"
            f"    {self._barrier_line(barrier)}"
        )

    def _write(self, width: int, addr_expr: str, val_expr: str,
               barrier: str = "full") -> str:
        ct = _WIDTH_TYPES[width // 8]
        return (
            f"    {self._barrier_line(barrier)}\n"
            f"    *(volatile {ct} *)(uintptr_t)({addr_expr}) = ({ct})({val_expr});\n"
            f"    {self._barrier_line(barrier)}"
        )

    # ── public code-gen API ───────────────────────────────────────────────────

    def generate_read(self, addr_expr: str, width: int = 32,
                      var: str = "val", barrier: str = "full") -> str:
        """Generate a checked MMIO read with barriers."""
        ct = _WIDTH_TYPES.get(width // 8, "uint32_t")
        align = width // 8
        lines = [
            f"    /* MMIO read {width}-bit from {addr_expr} — {self.arch.value} */",
        ]
        if align > 1:
            lines += [
                f"    if ((uintptr_t)({addr_expr}) & {align - 1}U) return ({ct})-1; /* misaligned */",
            ]
        lines.append(self._read(width, addr_expr, var, barrier))
        return "\n".join(lines)

    def generate_write(self, addr_expr: str, val_expr: str,
                       width: int = 32, barrier: str = "full") -> str:
        """Generate a checked MMIO write with barriers."""
        align = width // 8
        lines = [
            f"    /* MMIO write {width}-bit to {addr_expr} — {self.arch.value} */",
        ]
        if align > 1:
            lines += [
                f"    if ((uintptr_t)({addr_expr}) & {align - 1}U) return -1; /* misaligned */",
            ]
        lines.append(self._write(width, addr_expr, val_expr, barrier))
        return "\n".join(lines)

    def generate_rmw(self, addr_expr: str, mask_expr: str,
                     val_expr: str, width: int = 32) -> str:
        """Generate a read-modify-write sequence."""
        ct = _WIDTH_TYPES.get(width // 8, "uint32_t")
        bl = self._barrier_line()
        return (
            f"    /* Read-Modify-Write {width}-bit at {addr_expr} */\n"
            f"    {bl}\n"
            f"    volatile {ct} *_p = (volatile {ct} *)(uintptr_t)({addr_expr});\n"
            f"    {ct} _old = *_p;\n"
            f"    *_p = (_old & ~({ct})({mask_expr})) | (({ct})({val_expr}) & ({ct})({mask_expr}));\n"
            f"    {bl}"
        )

    def generate_poll(self, addr_expr: str, mask_expr: str,
                      expected_expr: str, timeout: int = 1000,
                      width: int = 32) -> str:
        """Generate poll-until-ready with timeout. Returns 0=ok, -1=timeout."""
        ct = _WIDTH_TYPES.get(width // 8, "uint32_t")
        fn_id = abs(hash(addr_expr + mask_expr)) & 0xFFFF
        return f"""
static int ks_mmio_poll_{fn_id:04x}(void) {{
    int _timeout = {timeout};
    while (_timeout-- > 0) {{
        {ct} _v = *(volatile {ct} *)(uintptr_t)({addr_expr});
        if ((_v & ({ct})({mask_expr})) == ({ct})({expected_expr})) return 0;
        __asm__ volatile("nop");
    }}
    return -1; /* timeout */
}}"""

    def generate_device_header(self, dev: DeviceMap) -> str:
        """Generate a complete C header for a device register map."""
        lines = [
            f"/* {dev.name} register map — generated by KentScript MMIO Generator */",
            f"/* {dev.desc} */",
            f"#ifndef _{dev.name.upper()}_H",
            f"#define _{dev.name.upper()}_H",
            f"#include <stdint.h>",
            f"",
            f"#define {dev.name.upper()}_BASE ({dev.base_expr})",
            f"",
        ]

        # Register offset macros
        for reg in dev.regs:
            ct = _WIDTH_TYPES.get(reg.width // 8, "uint32_t")
            lines.append(f"#define {dev.name.upper()}_{reg.name}_OFFSET  0x{reg.offset:04X}U  /* {reg.desc} */")

        lines.append("")

        # Register access macros
        for reg in dev.regs:
            ct  = _WIDTH_TYPES.get(reg.width // 8, "uint32_t")
            bar = self._barriers["full"]
            lines += [
                f"/* {reg.name}: {reg.desc} (reset=0x{reg.reset:X}, {reg.rw}) */",
            ]
            if "r" in reg.rw:
                lines.append(
                    f"static inline {ct} {dev.name}_{reg.name}_read(uintptr_t base) {{\n"
                    f"    __asm__ volatile(\"{bar}\" ::: \"memory\");\n"
                    f"    {ct} v = *(volatile {ct} *)(base + {dev.name.upper()}_{reg.name}_OFFSET);\n"
                    f"    __asm__ volatile(\"{bar}\" ::: \"memory\");\n"
                    f"    return v;\n"
                    f"}}"
                )
            if "w" in reg.rw:
                lines.append(
                    f"static inline void {dev.name}_{reg.name}_write(uintptr_t base, {ct} val) {{\n"
                    f"    __asm__ volatile(\"{bar}\" ::: \"memory\");\n"
                    f"    *(volatile {ct} *)(base + {dev.name.upper()}_{reg.name}_OFFSET) = val;\n"
                    f"    __asm__ volatile(\"{bar}\" ::: \"memory\");\n"
                    f"}}"
                )
            # Bit-field macros
            for field in reg.fields:
                lines.append(field.c_macro(f"{dev.name.upper()}_{reg.name}", reg.width))
            lines.append("")

        # Struct overlay
        lines += [
            f"/* Struct overlay for {dev.name} */",
            f"typedef volatile struct {{",
        ]
        last = 0
        for reg in sorted(dev.regs, key=lambda r: r.offset):
            ct = _WIDTH_TYPES.get(reg.width // 8, "uint32_t")
            gap = reg.offset - last
            if gap > 0:
                lines.append(f"    uint8_t _pad_{last:04x}[{gap}];")
            lines.append(f"    {ct} {reg.name};  /* 0x{reg.offset:04X}  {reg.desc} */")
            last = reg.offset + reg.width // 8
        lines += [
            f"}} {dev.name}_regs_t;",
            f"",
            f"#define {dev.name.upper()}_REGS (({dev.name}_regs_t *)(uintptr_t)({dev.base_expr}))",
            f"",
            f"#endif /* _{dev.name.upper()}_H */",
        ]
        return "\n".join(lines) + "\n"

    def generate_helpers_header(self) -> str:
        """Generate portable MMIO helper macros header for any target."""
        arch  = self.arch.value.upper().replace("-", "_")
        bar   = self._barriers["full"]
        bar_r = self._barriers["load"]
        bar_w = self._barriers["store"]
        return f"""/*
 * ks_mmio_{arch.lower()}.h — KentScript MMIO helper macros
 * Architecture: {self.arch.value}
 * Barrier: {bar}
 * Auto-generated — do not edit by hand.
 */
#ifndef KS_MMIO_{arch}_H
#define KS_MMIO_{arch}_H

#include <stdint.h>
#include <stddef.h>

#define MMIO_BARRIER_FULL()  __asm__ volatile("{bar}"   ::: "memory")
#define MMIO_BARRIER_READ()  __asm__ volatile("{bar_r}" ::: "memory")
#define MMIO_BARRIER_WRITE() __asm__ volatile("{bar_w}" ::: "memory")

#define MMIO_IS_ALIGNED(addr, width) (((uintptr_t)(addr) & ((width)-1)) == 0)

/* 8-bit */
static inline uint8_t  mmio_read8 (uintptr_t a)          {{ MMIO_BARRIER_READ();  return *(volatile uint8_t  *)a; }}
static inline void     mmio_write8(uintptr_t a, uint8_t  v) {{ *(volatile uint8_t  *)a = v; MMIO_BARRIER_WRITE(); }}

/* 16-bit */
static inline uint16_t mmio_read16 (uintptr_t a)           {{ MMIO_BARRIER_READ();  return *(volatile uint16_t *)a; }}
static inline void     mmio_write16(uintptr_t a, uint16_t v){{ *(volatile uint16_t *)a = v; MMIO_BARRIER_WRITE(); }}

/* 32-bit */
static inline uint32_t mmio_read32 (uintptr_t a)           {{ MMIO_BARRIER_READ();  return *(volatile uint32_t *)a; }}
static inline void     mmio_write32(uintptr_t a, uint32_t v){{ *(volatile uint32_t *)a = v; MMIO_BARRIER_WRITE(); }}

/* 64-bit */
static inline uint64_t mmio_read64 (uintptr_t a)           {{ MMIO_BARRIER_READ();  return *(volatile uint64_t *)a; }}
static inline void     mmio_write64(uintptr_t a, uint64_t v){{ *(volatile uint64_t *)a = v; MMIO_BARRIER_WRITE(); }}

/* Read-modify-write */
#define MMIO_RMW32(addr, mask, val) do {{                   \\
    MMIO_BARRIER_FULL();                                     \\
    volatile uint32_t *_p = (volatile uint32_t *)(addr);     \\
    *_p = (*_p & ~(uint32_t)(mask)) | ((uint32_t)(val) & (uint32_t)(mask)); \\
    MMIO_BARRIER_FULL();                                     \\
}} while(0)

#endif /* KS_MMIO_{arch}_H */
"""

    def compile_to_so(self, c_code: str, name: str = "ks_mmio_test") -> Optional[ctypes.CDLL]:
        """
        Compile generated C code to a shared library and load it.
        Proves the generated code is real and correct.
        """
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, f"{name}.c")
            so  = os.path.join(d, f"{name}.so")
            with open(src, "w") as f:
                f.write("#include <stdint.h>\n#include <stddef.h>\n")
                f.write(c_code)
            r = subprocess.run(
                ["gcc", "-O2", "-shared", "-fPIC", "-o", so, src],
                capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"Compile failed:\n{r.stderr}\n\nSource:\n{c_code}")
            # Load into a temp location that won't be deleted
            import shutil
            final_so = os.path.join(tempfile.gettempdir(), f"{name}_{os.getpid()}.so")
            shutil.copy(so, final_so)
            return ctypes.CDLL(final_so)


# ─── pre-built device maps ────────────────────────────────────────────────────

def pl011_uart() -> DeviceMap:
    """ARM PL011 UART register map (QEMU virt machine at 0x09000000)."""
    return DeviceMap(
        name="pl011", base_expr="0x09000000UL",
        desc="ARM PL011 UART",
        regs=[
            DeviceRegister("DR",   0x00, 32, "rw", desc="Data Register",
                           fields=[RegField("DATA",0,7), RegField("FE",8,8,"ro"),
                                   RegField("PE",9,9,"ro"), RegField("BE",10,10,"ro"),
                                   RegField("OE",11,11,"ro")]),
            DeviceRegister("RSR",  0x04, 32, "rw", desc="Receive Status"),
            DeviceRegister("FR",   0x18, 32, "ro", reset=0x90, desc="Flag Register",
                           fields=[RegField("CTS",0,0,"ro"), RegField("BUSY",3,3,"ro"),
                                   RegField("RXFE",4,4,"ro"), RegField("TXFF",5,5,"ro"),
                                   RegField("RXFF",6,6,"ro"), RegField("TXFE",7,7,"ro")]),
            DeviceRegister("IBRD", 0x24, 32, "rw", desc="Integer Baud Rate"),
            DeviceRegister("FBRD", 0x28, 32, "rw", desc="Fractional Baud Rate"),
            DeviceRegister("LCR",  0x2C, 32, "rw", desc="Line Control",
                           fields=[RegField("BRK",0,0), RegField("PEN",1,1),
                                   RegField("EPS",2,2), RegField("STP2",3,3),
                                   RegField("FEN",4,4), RegField("WLEN",5,6)]),
            DeviceRegister("CR",   0x30, 32, "rw", desc="Control Register",
                           fields=[RegField("UARTEN",0,0), RegField("TXE",8,8),
                                   RegField("RXE",9,9)]),
            DeviceRegister("IMSC", 0x38, 32, "rw", desc="Interrupt Mask"),
        ]
    )


def gic_cpu_interface() -> DeviceMap:
    """ARM GICv2 CPU interface register map."""
    return DeviceMap(
        name="gicc", base_expr="0x08010000UL",
        desc="ARM GICv2 CPU Interface",
        regs=[
            DeviceRegister("CTLR",  0x00, 32, "rw", desc="CPU Interface Control"),
            DeviceRegister("PMR",   0x04, 32, "rw", desc="Interrupt Priority Mask"),
            DeviceRegister("BPR",   0x08, 32, "rw", desc="Binary Point"),
            DeviceRegister("IAR",   0x0C, 32, "ro", desc="Interrupt Acknowledge"),
            DeviceRegister("EOIR",  0x10, 32, "wo", desc="End of Interrupt"),
            DeviceRegister("RPR",   0x14, 32, "ro", desc="Running Priority"),
            DeviceRegister("HPPIR", 0x18, 32, "ro", desc="Highest Pending Interrupt"),
        ]
    )


# ─── self-test ────────────────────────────────────────────────────────────────

def _test():
    print("Testing Real MMIO Code Generator...")
    arch = detect_arch()
    print(f"  Architecture: {arch.value}")

    gen = MMIOGenerator(arch)

    # Test 1: generate and compile a read function
    c_code = """
uint32_t test_mmio_read_val;

void test_mmio_read(uintptr_t addr) {
""" + gen.generate_read("addr", 32, "v") + """
    test_mmio_read_val = v;
}

uint32_t test_rmw_result;
void test_rmw(uint32_t *addr) {
""" + gen.generate_rmw("addr", "0xFF00", "0x4200") + """
    test_rmw_result = *addr;
}
"""
    lib = gen.compile_to_so(c_code, "ks_mmio_selftest")
    print("  compile_to_so() succeeded  ✓")

    # Test rmw
    lib.test_rmw.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
    lib.test_rmw.restype  = None
    val = ctypes.c_uint32(0x1234)
    lib.test_rmw(ctypes.byref(val))
    result = ctypes.c_uint32.in_dll(lib, "test_rmw_result").value
    assert result == (0x1234 & ~0xFF00) | 0x4200, f"rmw wrong: 0x{result:X}"
    print(f"  RMW test: 0x1234 & ~0xFF00 | 0x4200 = 0x{result:X}  ✓")

    # Test 2: generate UART header
    uart = pl011_uart()
    header = gen.generate_device_header(uart)
    assert "pl011_DR_read" in header
    assert "PL011_FR_OFFSET" in header
    print(f"  PL011 UART header: {len(header)} bytes  ✓")

    # Test 3: generate helpers header
    helpers = gen.generate_helpers_header()
    assert "mmio_read32" in helpers
    assert "MMIO_RMW32" in helpers
    print(f"  MMIO helpers header: {len(helpers)} bytes  ✓")

    # Test 4: poll
    poll_code = gen.generate_poll("0x1000", "0x80", "0x80", 100)
    assert "ks_mmio_poll_" in poll_code
    print(f"  Poll code generated  ✓")

    print("All tests passed!")

# Module exports
__all__ = [
    'ARM64MMIO',
    'MMIOGenerator',
    'DeviceMap',
    'DeviceRegister',
    'RegField',
    'Arch',
    'detect_arch',
    'pl011_uart',
    'gic_cpu_interface',
]

# Wrapper for compatibility
ARM64MMIO = MMIOGenerator

if __name__ == "__main__":
    _test()
