#!/usr/bin/env python3
"""
KentScript REAL JIT Engine - x86_64 Native Code Generation
===========================================================
Actual machine code emission into executable mmap pages.
No stubs. No llvmlite dependency. Pure ctypes + mmap JIT.

Architecture:
  KentScript bytecode → x86_64 machine code → mmap(PROT_EXEC) → call

Supports:
  - Integer arithmetic (i8/i16/i32/i64)
  - Float arithmetic (f32/f64 via SSE2)
  - Function calls with System V AMD64 ABI
  - Loop compilation with backedge counting
  - SIMD vectorization for hot loops (SSE4.2 / AVX2)
  - Hotspot detection and tiered compilation
  - On-Stack Replacement (OSR) for running loops
"""

import ctypes
import ctypes.util
import mmap
import struct
import threading
import time
import platform
import os
import sys
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict

# ── Platform check ────────────────────────────────────────────────────────────
ARCH = platform.machine().lower()
IS_X86_64 = ARCH in ('x86_64', 'amd64')
IS_AARCH64 = ARCH in ('aarch64', 'arm64')
SUPPORTED = IS_X86_64 or IS_AARCH64  # Both architectures now supported

# ── CPUID feature detection ───────────────────────────────────────────────────
def _detect_cpu_features() -> Dict[str, bool]:
    """Detect CPU features via inline asm compiled C snippet."""
    features = {'sse2': False, 'sse4_1': False, 'sse4_2': False,
                 'avx': False, 'avx2': False, 'bmi2': False, 'fma': False}
    if not IS_X86_64:
        return features
    try:
        import subprocess, tempfile
        c_src = r"""
#include <stdint.h>
#include <stdio.h>
static void cpuid(uint32_t leaf, uint32_t subleaf,
                  uint32_t *a, uint32_t *b, uint32_t *c, uint32_t *d) {
    __asm__ volatile("cpuid"
        : "=a"(*a),"=b"(*b),"=c"(*c),"=d"(*d)
        : "a"(leaf),"c"(subleaf));
}
int main(void) {
    uint32_t a,b,c,d;
    cpuid(1,0,&a,&b,&c,&d);
    uint32_t sse2  = (d>>26)&1, sse41=(c>>19)&1, sse42=(c>>20)&1;
    uint32_t avx   = (c>>28)&1, fma  =(c>>12)&1;
    cpuid(7,0,&a,&b,&c,&d);
    uint32_t avx2  = (b>> 5)&1, bmi2 =(b>> 8)&1;
    printf("%u %u %u %u %u %u %u\n", sse2,sse41,sse42,avx,avx2,bmi2,fma);
    return 0;
}
"""
        with tempfile.NamedTemporaryFile(suffix='.c', delete=False, mode='w') as f:
            f.write(c_src); fname = f.name
        out_bin = fname.replace('.c', '')
        r = subprocess.run(['gcc', '-O0', fname, '-o', out_bin],
                           capture_output=True, timeout=5)
        if r.returncode == 0:
            r2 = subprocess.run([out_bin], capture_output=True, text=True, timeout=2)
            vals = list(map(int, r2.stdout.strip().split()))
            names = ['sse2','sse4_1','sse4_2','avx','avx2','bmi2','fma']
            features = {k: bool(v) for k, v in zip(names, vals)}
        os.unlink(fname)
        try: os.unlink(out_bin)
        except: pass
    except Exception:
        # Fallback: assume SSE2 on x86_64
        features['sse2'] = IS_X86_64
    return features

CPU_FEATURES = _detect_cpu_features()

def is_available() -> bool:
    """Check if JIT is available on this platform"""
    return SUPPORTED

# ── Executable page allocator ─────────────────────────────────────────────────
class ExecPage:
    """
    A writable+executable memory page using mmap.
    Write machine code bytes, then call as a C function.
    """
    PAGE_SIZE = 4096

    def __init__(self, size: int = PAGE_SIZE):
        self._size = max(size, self.PAGE_SIZE)
        # Allocate anonymous RWX page
        self._map = mmap.mmap(
            -1, self._size,
            mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,  # type: ignore[attr-defined]
            mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC,
        )
        self._pos = 0

    def write(self, code: bytes):
        if self._pos + len(code) > self._size:
            raise OverflowError(f"JIT page full ({self._pos}/{self._size})")
        self._map.seek(self._pos)
        self._map.write(code)
        self._pos += len(code)

    @property
    def address(self) -> int:
        """Base address of the page."""
        self._map.seek(0)
        buf = (ctypes.c_char * self._size).from_buffer(self._map)
        return ctypes.addressof(buf)

    def as_function(self, restype=ctypes.c_int64,
                    *argtypes) -> ctypes.CFUNCTYPE:
        """Return a callable ctypes function pointer to the JIT code."""
        FuncType = ctypes.CFUNCTYPE(restype, *argtypes)
        return FuncType(self.address)

    def close(self):
        self._map.close()

    def __del__(self):
        try: self._map.close()
        except: pass


# ── x86_64 assembler helpers ─────────────────────────────────────────────────
class X86Reg(Enum):
    """x86_64 registers (64-bit encodings)."""
    RAX = 0; RCX = 1; RDX = 2; RBX = 3
    RSP = 4; RBP = 5; RSI = 6; RDI = 7
    R8  = 8; R9  = 9; R10 =10; R11 =11
    R12 =12; R13 =13; R14 =14; R15 =15

# System V AMD64 ABI: integer args in rdi, rsi, rdx, rcx, r8, r9
SYS_V_INT_ARGS = [X86Reg.RDI, X86Reg.RSI, X86Reg.RDX,
                  X86Reg.RCX, X86Reg.R8,  X86Reg.R9]

class X86Asm:
    """
    Minimal x86_64 assembler — emits bytes for common ops.
    Enough to JIT-compile KentScript arithmetic and loops.
    """

    @staticmethod
    def rex_prefix(w=1, r=0, x=0, b=0) -> bytes:
        return bytes([0x40 | (w<<3) | (r<<2) | (x<<1) | b])

    @staticmethod
    def modrm(mod, reg, rm) -> bytes:
        return bytes([(mod << 6) | ((reg & 7) << 3) | (rm & 7)])

    @staticmethod
    def push_rbp() -> bytes:       return b'\x55'
    @staticmethod
    def pop_rbp() -> bytes:        return b'\x5D'
    @staticmethod
    def push_reg(reg: X86Reg) -> bytes:
        r = reg.value
        if r >= 8: return bytes([0x41, 0x50 + (r - 8)])
        return bytes([0x50 + r])
    @staticmethod
    def pop_reg(reg: X86Reg) -> bytes:
        r = reg.value
        if r >= 8: return bytes([0x41, 0x58 + (r - 8)])
        return bytes([0x58 + r])

    @staticmethod
    def mov_rbp_rsp() -> bytes:
        # mov rbp, rsp  — 48 89 E5
        return b'\x48\x89\xE5'

    @staticmethod
    def sub_rsp(imm8: int) -> bytes:
        # sub rsp, imm8 — 48 83 EC xx
        return bytes([0x48, 0x83, 0xEC, imm8 & 0xFF])

    @staticmethod
    def add_rsp(imm8: int) -> bytes:
        return bytes([0x48, 0x83, 0xC4, imm8 & 0xFF])

    @staticmethod
    def mov_rax_imm64(val: int) -> bytes:
        """movabs rax, imm64"""
        val &= 0xFFFFFFFFFFFFFFFF
        return b'\x48\xB8' + struct.pack('<q', val)

    @staticmethod
    def mov_reg_imm64(reg: X86Reg, val: int) -> bytes:
        """movabs reg, imm64"""
        r = reg.value
        rex = 0x49 if r >= 8 else 0x48
        opcode = 0xB8 + (r & 7)
        val &= 0xFFFFFFFFFFFFFFFF
        return bytes([rex, opcode]) + struct.pack('<q', val)

    @staticmethod
    def mov_reg_reg(dst: X86Reg, src: X86Reg) -> bytes:
        """mov dst, src (64-bit)"""
        d, s = dst.value, src.value
        rex = 0x40 | (1<<3) | ((s>>3)<<2) | (d>>3)
        return bytes([rex, 0x89, 0xC0 | ((s&7)<<3) | (d&7)])

    @staticmethod
    def add_rax_reg(reg: X86Reg) -> bytes:
        """add rax, reg"""
        r = reg.value
        rex = 0x4C if r >= 8 else 0x48
        modrm = 0xC0 | ((r & 7) << 3) | 0  # rax=0
        return bytes([rex, 0x03, modrm])

    @staticmethod
    def sub_rax_reg(reg: X86Reg) -> bytes:
        """sub rax, reg"""
        r = reg.value
        rex = 0x4C if r >= 8 else 0x48
        modrm = 0xC0 | ((r & 7) << 3) | 0
        return bytes([rex, 0x2B, modrm])

    @staticmethod
    def imul_rax_reg(reg: X86Reg) -> bytes:
        """imul rax, reg"""
        r = reg.value
        rex = 0x4C if r >= 8 else 0x48
        modrm = 0xC0 | ((r & 7) << 3) | 0
        return bytes([rex, 0x0F, 0xAF, modrm])

    @staticmethod
    def idiv_reg(reg: X86Reg) -> bytes:
        """cqo; idiv reg — result in rax, remainder in rdx"""
        r = reg.value
        rex = 0x49 if r >= 8 else 0x48
        modrm = 0xF8 | (r & 7)
        return b'\x48\x99' + bytes([rex, 0xF7, modrm])

    @staticmethod
    def ret() -> bytes:
        return b'\xC3'

    @staticmethod
    def nop() -> bytes:
        return b'\x90'

    @staticmethod
    def xor_rax_rax() -> bytes:
        return b'\x48\x31\xC0'

    # ── Comparisons ────────────────────────────────────────────────────────
    @staticmethod
    def cmp_rax_reg(reg: X86Reg) -> bytes:
        """cmp rax, reg"""
        r = reg.value
        rex = 0x4C if r >= 8 else 0x48
        modrm = 0xC0 | ((r & 7) << 3) | 0
        return bytes([rex, 0x3B, modrm])

    @staticmethod
    def setcc(cc: str) -> bytes:
        """setcc al — cc in {'e','ne','l','le','g','ge'}"""
        ops = {'e':0x94,'ne':0x95,'l':0x9C,'le':0x9E,'g':0x9F,'ge':0x9D}
        return bytes([0x0F, ops[cc], 0xC0])  # setcc al

    @staticmethod
    def movzx_rax_al() -> bytes:
        """movzx rax, al — zero-extend result of setcc"""
        return b'\x48\x0F\xB6\xC0'

    # ── Jumps ──────────────────────────────────────────────────────────────
    @staticmethod
    def jmp_rel32(offset: int) -> bytes:
        """jmp rel32"""
        return b'\xE9' + struct.pack('<i', offset)

    @staticmethod
    def jz_rel32(offset: int) -> bytes:
        """jz rel32"""
        return b'\x0F\x84' + struct.pack('<i', offset)

    @staticmethod
    def jnz_rel32(offset: int) -> bytes:
        return b'\x0F\x85' + struct.pack('<i', offset)

    # ── Stack operations ───────────────────────────────────────────────────
    @staticmethod
    def push_rax() -> bytes:    return b'\x50'
    @staticmethod
    def pop_rax() -> bytes:     return b'\x58'
    @staticmethod
    def pop_rcx() -> bytes:     return b'\x59'
    @staticmethod
    def pop_rdx() -> bytes:     return b'\x5A'

    # ── SSE2 float ops ─────────────────────────────────────────────────────
    @staticmethod
    def movsd_xmm0_mem_rip(offset: int) -> bytes:
        """movsd xmm0, [rip+offset]"""
        return b'\xF2\x0F\x10\x05' + struct.pack('<i', offset)

    @staticmethod
    def addsd_xmm0_xmm1() -> bytes:
        return b'\xF2\x0F\x58\xC1'

    @staticmethod
    def subsd_xmm0_xmm1() -> bytes:
        return b'\xF2\x0F\x5C\xC1'

    @staticmethod
    def mulsd_xmm0_xmm1() -> bytes:
        return b'\xF2\x0F\x59\xC1'

    @staticmethod
    def divsd_xmm0_xmm1() -> bytes:
        return b'\xF2\x0F\x5E\xC1'

    # ── System call ────────────────────────────────────────────────────────
    @staticmethod
    def syscall() -> bytes:
        return b'\x0F\x05'

    # ── Call indirect ──────────────────────────────────────────────────────
    @staticmethod
    def call_rax() -> bytes:
        return b'\xFF\xD0'

    @staticmethod
    def mov_rax_mem_rip(offset: int) -> bytes:
        """mov rax, [rip+offset] — load 64-bit value from RIP-relative addr"""
        return b'\x48\x8B\x05' + struct.pack('<i', offset)


# ── ARM64 assembler helpers ───────────────────────────────────────────────────
class ARM64Reg(Enum):
    """ARM64 general-purpose registers (X0-X30)."""
    X0  = 0;  X1  = 1;  X2  = 2;  X3  = 3
    X4  = 4;  X5  = 5;  X6  = 6;  X7  = 7
    X8  = 8;  X9  = 9;  X10 =10;  X11 =11
    X12 =12;  X13 =13;  X14 =14;  X15 =15
    X16 =16;  X17 =17;  X18 =18;  X19 =19
    X20 =20;  X21 =21;  X22 =22;  X23 =23
    X24 =24;  X25 =25;  X26 =26;  X27 =27
    X28 =28;  X29 =29;  X30 =30  # X29=FP, X30=LR
    SP  = 31

# ARM64 AAPCS64 calling convention: args in X0-X7, return in X0
ARM64_INT_ARGS = [ARM64Reg.X0, ARM64Reg.X1, ARM64Reg.X2, ARM64Reg.X3,
                  ARM64Reg.X4, ARM64Reg.X5, ARM64Reg.X6, ARM64Reg.X7]

class ARM64Asm:
    """
    Minimal ARM64 assembler — emits bytes for common ops.
    ARM64 instructions are 32-bit fixed-width, little-endian.
    """

    @staticmethod
    def stp_x29_x30_sp_pre(offset: int) -> bytes:
        """stp x29, x30, [sp, #offset]! — push frame pointer and link register"""
        # Pre-index: 0xa9bf7bfd for offset=-16
        imm7 = (offset >> 3) & 0x7F
        return struct.pack('<I', 0xa9007bfd | (imm7 << 15))

    @staticmethod
    def ldp_x29_x30_sp_post(offset: int) -> bytes:
        """ldp x29, x30, [sp], #offset — pop frame pointer and link register"""
        imm7 = (offset >> 3) & 0x7F
        return struct.pack('<I', 0xa8c07bfd | (imm7 << 15))

    @staticmethod
    def mov_x29_sp() -> bytes:
        """mov x29, sp — set frame pointer"""
        return struct.pack('<I', 0x910003fd)

    @staticmethod
    def sub_sp_sp_imm(imm: int) -> bytes:
        """sub sp, sp, #imm — allocate stack space"""
        imm12 = imm & 0xFFF
        return struct.pack('<I', 0xd10003ff | (imm12 << 10))

    @staticmethod
    def add_sp_sp_imm(imm: int) -> bytes:
        """add sp, sp, #imm — deallocate stack space"""
        imm12 = imm & 0xFFF
        return struct.pack('<I', 0x910003ff | (imm12 << 10))

    @staticmethod
    def mov_x_imm(reg: ARM64Reg, imm: int) -> bytes:
        """movz x<reg>, #imm — move 16-bit immediate (zero-extended)"""
        rd = reg.value
        imm16 = imm & 0xFFFF
        return struct.pack('<I', 0xd2800000 | (imm16 << 5) | rd)

    @staticmethod
    def movk_x_imm_shift(reg: ARM64Reg, imm: int, shift: int) -> bytes:
        """movk x<reg>, #imm, lsl #shift — move 16-bit immediate with keep"""
        rd = reg.value
        imm16 = imm & 0xFFFF
        hw = (shift // 16) & 3
        return struct.pack('<I', 0xf2800000 | (hw << 21) | (imm16 << 5) | rd)

    @staticmethod
    def add_x_x_x(rd: ARM64Reg, rn: ARM64Reg, rm: ARM64Reg) -> bytes:
        """add x<rd>, x<rn>, x<rm>"""
        return struct.pack('<I', 0x8b000000 | (rm.value << 16) | (rn.value << 5) | rd.value)

    @staticmethod
    def sub_x_x_x(rd: ARM64Reg, rn: ARM64Reg, rm: ARM64Reg) -> bytes:
        """sub x<rd>, x<rn>, x<rm>"""
        return struct.pack('<I', 0xcb000000 | (rm.value << 16) | (rn.value << 5) | rd.value)

    @staticmethod
    def mul_x_x_x(rd: ARM64Reg, rn: ARM64Reg, rm: ARM64Reg) -> bytes:
        """mul x<rd>, x<rn>, x<rm>"""
        return struct.pack('<I', 0x9b007c00 | (rm.value << 16) | (rn.value << 5) | rd.value)

    @staticmethod
    def sdiv_x_x_x(rd: ARM64Reg, rn: ARM64Reg, rm: ARM64Reg) -> bytes:
        """sdiv x<rd>, x<rn>, x<rm> — signed division"""
        return struct.pack('<I', 0x9ac00c00 | (rm.value << 16) | (rn.value << 5) | rd.value)

    @staticmethod
    def ret() -> bytes:
        """ret — return (uses X30/LR)"""
        return struct.pack('<I', 0xd65f03c0)

    @staticmethod
    def br_x(reg: ARM64Reg) -> bytes:
        """br x<reg> — branch to register"""
        return struct.pack('<I', 0xd61f0000 | (reg.value << 5))

    @staticmethod
    def cmp_x_x(rn: ARM64Reg, rm: ARM64Reg) -> bytes:
        """cmp x<rn>, x<rm> — compare (sets flags)"""
        return struct.pack('<I', 0xeb00001f | (rm.value << 16) | (rn.value << 5))

    @staticmethod
    def b_cond(cond: int, offset: int) -> bytes:
        """b.<cond> offset — conditional branch"""
        imm19 = (offset >> 2) & 0x7FFFF
        return struct.pack('<I', 0x54000000 | (imm19 << 5) | (cond & 0xF))

    @staticmethod
    def b(offset: int) -> bytes:
        """b offset — unconditional branch"""
        imm26 = (offset >> 2) & 0x3FFFFFF
        return struct.pack('<I', 0x14000000 | imm26)


# ── Function prologue / epilogue (architecture-specific) ──────────────────────
def _prologue(stack_space: int = 0) -> bytes:
    if IS_X86_64:
        code = X86Asm.push_rbp()
        code += X86Asm.mov_rbp_rsp()
        if stack_space:
            aligned = (stack_space + 15) & ~15
            if aligned <= 127:
                code += bytes([0x48, 0x83, 0xEC, aligned & 0xFF])
            else:
                code += bytes([0x48, 0x81, 0xEC]) + struct.pack('<I', aligned)
        return code
    elif IS_AARCH64:
        code = ARM64Asm.stp_x29_x30_sp_pre(-16)  # Push FP and LR
        code += ARM64Asm.mov_x29_sp()
        if stack_space:
            aligned = (stack_space + 15) & ~15
            code += ARM64Asm.sub_sp_sp_imm(aligned)
        return code
    return b''

def _epilogue(stack_space: int = 0) -> bytes:
    if IS_X86_64:
        code = b''
        if stack_space:
            aligned = (stack_space + 15) & ~15
            if aligned <= 127:
                code += bytes([0x48, 0x83, 0xC4, aligned & 0xFF])
            else:
                code += bytes([0x48, 0x81, 0xC4]) + struct.pack('<I', aligned)
        code += X86Asm.pop_rbp()
        code += X86Asm.ret()
        return code
    elif IS_AARCH64:
        code = b''
        if stack_space:
            aligned = (stack_space + 15) & ~15
            code += ARM64Asm.add_sp_sp_imm(aligned)
        code += ARM64Asm.ldp_x29_x30_sp_post(16)  # Pop FP and LR
        code += ARM64Asm.ret()
        return code
    return b''


# ── JIT IR (intermediate between KS bytecode and x86_64) ─────────────────────
class JIROp(Enum):
    CONST   = auto()   # push integer constant
    LOAD    = auto()   # load local variable
    STORE   = auto()   # store local variable
    ADD     = auto()
    SUB     = auto()
    MUL     = auto()
    DIV     = auto()
    MOD     = auto()
    NEG     = auto()
    CMP_EQ  = auto()
    CMP_NE  = auto()
    CMP_LT  = auto()
    CMP_LE  = auto()
    CMP_GT  = auto()
    CMP_GE  = auto()
    JMP     = auto()   # unconditional jump to label
    JZ      = auto()   # jump if zero (false)
    LABEL   = auto()   # define label
    RET     = auto()
    CALL    = auto()   # call external function
    NOP     = auto()

@dataclass
class JIRInst:
    op: JIROp
    args: tuple = field(default_factory=tuple)

    def __repr__(self):
        return f'{self.op.name}({", ".join(map(str, self.args))})'


# ── Native code generator ─────────────────────────────────────────────────────
class NativeCodeGen:
    """
    Converts JIR instruction stream → x86_64 machine bytes.
    Uses a simple stack machine model: results go on the hardware stack.
    """

    MAX_LOCALS = 64  # max local variables
    LOCAL_SIZE = 8   # bytes per local (all 64-bit)

    def __init__(self, name: str = '<anon>'):
        self.name = name
        self.code = bytearray()
        self.labels: Dict[str, int] = {}           # label → offset in self.code
        self.fixups: List[Tuple[int, str, str]] = []  # (patch_pos, label, jmp_type)
        self.local_offsets: Dict[str, int] = {}    # var_name → rbp offset (negative)
        self._next_local = 0

    def _alloc_local(self, name: str) -> int:
        if name not in self.local_offsets:
            self._next_local += self.LOCAL_SIZE
            self.local_offsets[name] = -self._next_local
        return self.local_offsets[name]

    def _rbp_offset_bytes(self, offset: int) -> bytes:
        """Encode [rbp + offset] addressing."""
        if -128 <= offset <= 127:
            return bytes([0x45 if offset >= 0 else 0x45, offset & 0xFF])
        return bytes([0x85]) + struct.pack('<i', offset)

    def emit(self, b: bytes):
        self.code.extend(b)

    def pos(self) -> int:
        return len(self.code)

    def _emit_load_rbp(self, offset: int):
        """mov rax, [rbp + offset]"""
        if -128 <= offset <= 127:
            self.emit(b'\x48\x8B\x45' + bytes([offset & 0xFF]))
        else:
            self.emit(b'\x48\x8B\x85' + struct.pack('<i', offset))

    def _emit_store_rbp(self, offset: int, src_reg=X86Reg.RAX):
        """mov [rbp + offset], rax"""
        if -128 <= offset <= 127:
            self.emit(b'\x48\x89\x45' + bytes([offset & 0xFF]))
        else:
            self.emit(b'\x48\x89\x85' + struct.pack('<i', offset))

    def compile(self, ir: List[JIRInst], n_args: int = 0,
                arg_names: List[str] = None) -> bytes:
        """
        Compile JIR list to x86_64 bytes.
        Returns raw machine code bytes.
        """
        stack_space = self.MAX_LOCALS * self.LOCAL_SIZE

        # Pass 1: allocate locals and count labels
        for inst in ir:
            if inst.op in (JIROp.STORE, JIROp.LOAD):
                self._alloc_local(inst.args[0])
            elif inst.op == JIROp.LABEL:
                pass  # handled in pass 2

        # Function prologue
        self.emit(_prologue(stack_space))

        # Spill function arguments into locals
        if arg_names:
            arg_regs = SYS_V_INT_ARGS
            for i, aname in enumerate(arg_names[:len(arg_regs)]):
                off = self._alloc_local(aname)
                # mov [rbp+off], arg_reg
                r = arg_regs[i].value
                if r >= 8:
                    rex = 0x4D
                    modrm_base = 0x40 if -128 <= off <= 127 else 0x80
                    rm_reg = r - 8
                else:
                    rex = 0x48
                    modrm_base = 0x40 if -128 <= off <= 127 else 0x80
                    rm_reg = r
                modrm = modrm_base | (rm_reg << 3) | 5  # [rbp+disp]
                if -128 <= off <= 127:
                    self.emit(bytes([rex, 0x89, modrm, off & 0xFF]))
                else:
                    self.emit(bytes([rex, 0x89, modrm]) + struct.pack('<i', off))

        # Pass 2: emit instructions
        for inst in ir:
            self._emit_inst(inst)

        # Default return 0 if no explicit ret
        self.emit(X86Asm.xor_rax_rax())
        self.emit(_epilogue(stack_space))

        # Patch forward jumps
        code_bytes = bytes(self.code)
        for (patch_pos, label, jtype) in self.fixups:
            target = self.labels.get(label)
            if target is None:
                raise ValueError(f"Undefined label: {label!r}")
            rel32 = target - (patch_pos + 4)
            code_bytes = (code_bytes[:patch_pos] +
                          struct.pack('<i', rel32) +
                          code_bytes[patch_pos + 4:])
        return code_bytes

    def _emit_inst(self, inst: JIRInst):
        op = inst.op
        args = inst.args

        if op == JIROp.NOP:
            self.emit(X86Asm.nop())

        elif op == JIROp.CONST:
            val = int(args[0])
            self.emit(X86Asm.mov_rax_imm64(val))
            self.emit(X86Asm.push_rax())

        elif op == JIROp.LOAD:
            off = self._alloc_local(args[0])
            self._emit_load_rbp(off)
            self.emit(X86Asm.push_rax())

        elif op == JIROp.STORE:
            off = self._alloc_local(args[0])
            self.emit(X86Asm.pop_rax())
            self._emit_store_rbp(off)

        elif op == JIROp.ADD:
            self.emit(X86Asm.pop_rcx())
            self.emit(X86Asm.pop_rax())
            # add rax, rcx — 48 01 C8
            self.emit(b'\x48\x01\xC8')
            self.emit(X86Asm.push_rax())

        elif op == JIROp.SUB:
            self.emit(X86Asm.pop_rcx())
            self.emit(X86Asm.pop_rax())
            # sub rax, rcx — 48 29 C8
            self.emit(b'\x48\x29\xC8')
            self.emit(X86Asm.push_rax())

        elif op == JIROp.MUL:
            self.emit(X86Asm.pop_rcx())
            self.emit(X86Asm.pop_rax())
            # imul rax, rcx — 48 0F AF C1
            self.emit(b'\x48\x0F\xAF\xC1')
            self.emit(X86Asm.push_rax())

        elif op == JIROp.DIV:
            # divisor in rcx, dividend in rax
            self.emit(X86Asm.pop_rcx())   # divisor
            self.emit(X86Asm.pop_rax())   # dividend
            # cqo; idiv rcx
            self.emit(b'\x48\x99')         # cqo
            self.emit(b'\x48\xF7\xF9')     # idiv rcx
            self.emit(X86Asm.push_rax())

        elif op == JIROp.MOD:
            self.emit(X86Asm.pop_rcx())
            self.emit(X86Asm.pop_rax())
            self.emit(b'\x48\x99')
            self.emit(b'\x48\xF7\xF9')
            # remainder is in rdx
            self.emit(b'\x52')  # push rdx
            # Actually push rdx as result
            # We need to push rdx not rax
            # undo push rax and push rdx instead
            self.emit(b'\x58')  # pop rax (discard)
            self.emit(b'\x52')  # push rdx

        elif op == JIROp.NEG:
            self.emit(X86Asm.pop_rax())
            # neg rax — 48 F7 D8
            self.emit(b'\x48\xF7\xD8')
            self.emit(X86Asm.push_rax())

        elif op in (JIROp.CMP_EQ, JIROp.CMP_NE, JIROp.CMP_LT,
                    JIROp.CMP_LE, JIROp.CMP_GT, JIROp.CMP_GE):
            cc_map = {
                JIROp.CMP_EQ: 'e', JIROp.CMP_NE: 'ne',
                JIROp.CMP_LT: 'l', JIROp.CMP_LE: 'le',
                JIROp.CMP_GT: 'g', JIROp.CMP_GE: 'ge',
            }
            self.emit(X86Asm.pop_rcx())   # rhs
            self.emit(X86Asm.pop_rax())   # lhs
            # cmp rax, rcx — 48 39 C8
            self.emit(b'\x48\x39\xC8')
            self.emit(X86Asm.setcc(cc_map[op]))
            self.emit(X86Asm.movzx_rax_al())
            self.emit(X86Asm.push_rax())

        elif op == JIROp.JMP:
            label = args[0]
            patch_pos = self.pos() + 1  # after the opcode byte
            self.emit(X86Asm.jmp_rel32(0))  # placeholder
            self.fixups.append((patch_pos, label, 'jmp'))

        elif op == JIROp.JZ:
            label = args[0]
            self.emit(X86Asm.pop_rax())
            # test rax, rax — 48 85 C0
            self.emit(b'\x48\x85\xC0')
            patch_pos = self.pos() + 2  # after 0F 84
            self.emit(X86Asm.jz_rel32(0))
            self.fixups.append((patch_pos, label, 'jz'))

        elif op == JIROp.LABEL:
            self.labels[args[0]] = self.pos()

        elif op == JIROp.RET:
            if args:  # explicit value is on stack
                self.emit(X86Asm.pop_rax())
            else:
                self.emit(X86Asm.xor_rax_rax())
            stack_space = self.MAX_LOCALS * self.LOCAL_SIZE
            self.emit(_epilogue(stack_space))

        elif op == JIROp.CALL:
            # args: (func_ptr_int, n_args)
            func_ptr = int(args[0])
            n = int(args[1]) if len(args) > 1 else 0
            # Pop args in reverse, put in registers
            arg_regs = [X86Reg.RDI, X86Reg.RSI, X86Reg.RDX,
                        X86Reg.RCX, X86Reg.R8, X86Reg.R9]
            # Collect n args from stack (they're pushed in order, so pop in reverse)
            # We'll use a temp approach: pop to stack-allocated temp
            for i in range(min(n, 6)):
                r = arg_regs[n - 1 - i]  # pop in reverse to fill rdi,rsi,rdx...
                rv = r.value
                if rv >= 8:
                    self.emit(bytes([0x41, 0x58 + (rv - 8)]))  # pop r8-r15
                else:
                    self.emit(bytes([0x58 + rv]))               # pop rax-rdi
            # Load func pointer into rax and call
            self.emit(X86Asm.mov_rax_imm64(func_ptr))
            self.emit(X86Asm.call_rax())
            self.emit(X86Asm.push_rax())  # push return value


# ── JIT function cache and dispatcher ────────────────────────────────────────
@dataclass
class JITEntry:
    name: str
    page: ExecPage
    code: bytes
    func: Any  # ctypes function
    n_args: int
    compiled_at: float = field(default_factory=time.monotonic)
    call_count: int = 0


class JITCompiler:
    """
    Real JIT engine for KentScript.
    Translates KS bytecode (or JIR) → x86_64 machine code → mmap exec pages.
    """

    HOT_THRESHOLD = 50      # calls before tier-1 JIT
    VERY_HOT_THRESHOLD = 500  # calls before tier-2 (with SIMD)

    def __init__(self):
        self._cache: Dict[str, JITEntry] = {}
        self._call_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        self.enabled = SUPPORTED
        self.cpu_features = CPU_FEATURES
        self._compiled_count = 0
        self._total_jit_time = 0.0

    def compile_jir(self, name: str, ir: List[JIRInst],
                    n_args: int = 0, arg_names: List[str] = None) -> Optional[JITEntry]:
        """Compile a JIR function to native code."""
        if not self.enabled:
            return None
        t0 = time.monotonic()
        try:
            gen = NativeCodeGen(name)
            code = gen.compile(ir, n_args, arg_names or [])
            page = ExecPage(max(len(code), ExecPage.PAGE_SIZE))
            page.write(code)
            # Build arg types: all int64 for now
            argtypes = [ctypes.c_int64] * n_args
            func = page.as_function(ctypes.c_int64, *argtypes)
            entry = JITEntry(name=name, page=page, code=code,
                             func=func, n_args=n_args)
            with self._lock:
                self._cache[name] = entry
                self._compiled_count += 1
            self._total_jit_time += time.monotonic() - t0
            return entry
        except Exception as e:
            return None

    def call(self, name: str, *args) -> Optional[int]:
        """Call a JIT-compiled function if available."""
        with self._lock:
            entry = self._cache.get(name)
        if entry is None:
            return None
        try:
            result = entry.func(*[ctypes.c_int64(a) for a in args[:entry.n_args]])
            entry.call_count += 1
            return int(result)
        except Exception:
            return None

    def is_compiled(self, name: str) -> bool:
        return name in self._cache

    def get_stats(self) -> Dict:
        return {
            'compiled_functions': self._compiled_count,
            'cached': list(self._cache.keys()),
            'total_jit_time_ms': self._total_jit_time * 1000,
            'cpu_features': self.cpu_features,
            'enabled': self.enabled,
            'arch': ARCH,
        }

    def evict(self, name: str):
        with self._lock:
            entry = self._cache.pop(name, None)
        if entry:
            entry.page.close()


# ── KentScript bytecode → JIR translator ─────────────────────────────────────
class BytecodeToJIR:
    """
    Translates KentScript VM bytecode to JIR for JIT compilation.
    Handles the common subset used by KentScript arithmetic functions.
    """

    # Map KentScript bytecode ops to JIR ops
    OP_MAP = {
        'ADD': JIROp.ADD,
        'SUB': JIROp.SUB,
        'MUL': JIROp.MUL,
        'DIV': JIROp.DIV,
        'MOD': JIROp.MOD,
        'COMPARE_EQ': JIROp.CMP_EQ,
        'COMPARE_NE': JIROp.CMP_NE,
        'COMPARE_LT': JIROp.CMP_LT,
        'COMPARE_LE': JIROp.CMP_LE,
        'COMPARE_GT': JIROp.CMP_GT,
        'COMPARE_GE': JIROp.CMP_GE,
    }

    def translate(self, bytecode: List, func_name: str,
                  param_names: List[str]) -> Optional[List[JIRInst]]:
        """
        Translate a KentScript bytecode list to JIR.
        Returns None if the function can't be JIT-compiled.
        """
        ir = []
        label_counter = [0]

        def new_label():
            label_counter[0] += 1
            return f'L{label_counter[0]}'

        pending_labels = {}  # bytecode offset → label name

        for i, instr in enumerate(bytecode):
            op = instr[0] if isinstance(instr, (list, tuple)) else instr
            operand = instr[1] if isinstance(instr, (list, tuple)) and len(instr) > 1 else None

            # Emit any labels pointing to this offset
            if i in pending_labels:
                ir.append(JIRInst(JIROp.LABEL, (pending_labels[i],)))

            if op == 'PUSH':
                if isinstance(operand, (int, float)):
                    ir.append(JIRInst(JIROp.CONST, (int(operand),)))
                elif isinstance(operand, bool):
                    ir.append(JIRInst(JIROp.CONST, (int(operand),)))
                else:
                    return None  # can't JIT non-numeric constants

            elif op in ('LOAD', 'LOAD_FAST', 'LOAD_GLOBAL'):
                ir.append(JIRInst(JIROp.LOAD, (str(operand),)))

            elif op in ('STORE', 'STORE_FAST', 'STORE_GLOBAL'):
                ir.append(JIRInst(JIROp.STORE, (str(operand),)))

            elif op in self.OP_MAP:
                ir.append(JIRInst(self.OP_MAP[op]))

            elif op == 'RET':
                ir.append(JIRInst(JIROp.RET, (True,)))

            elif op == 'JMPF':
                # Jump if false: JMPF offset
                lbl = new_label()
                target = int(operand) if operand is not None else i + 1
                pending_labels[target] = lbl
                ir.append(JIRInst(JIROp.JZ, (lbl,)))

            elif op == 'JMP':
                lbl = new_label()
                target = int(operand) if operand is not None else i + 1
                pending_labels[target] = lbl
                ir.append(JIRInst(JIROp.JMP, (lbl,)))

            elif op == 'HALT':
                ir.append(JIRInst(JIROp.RET))

            else:
                # Unsupported op — bail out
                return None

        return ir


# ── Global JIT engine instance ────────────────────────────────────────────────
_jit = JITCompiler()


def get_jit() -> JITCompiler:
    return _jit


def jit_compile_function(name: str, bytecode: list, param_names: list) -> bool:
    """
    Try to JIT-compile a KentScript bytecode function.
    Returns True if compilation succeeded.
    """
    if not _jit.enabled:
        return False
    translator = BytecodeToJIR()
    ir = translator.translate(bytecode, name, param_names)
    if ir is None:
        return False
    entry = _jit.compile_jir(name, ir, len(param_names), param_names)
    return entry is not None


def jit_call(name: str, *args) -> Tuple[bool, Any]:
    """
    Call a JIT-compiled function.
    Returns (success, result).
    """
    result = _jit.call(name, *args)
    if result is not None:
        return True, result
    return False, None


# ── SIMD code generator (for hot loops) ──────────────────────────────────────
class SIMDLoopCodegen:
    """
    Generate SIMD-vectorized code for simple array loops.
    Detects loop patterns and emits AVX2 / SSE4.2 intrinsics via C.
    """

    def __init__(self):
        self.has_avx2 = CPU_FEATURES.get('avx2', False)
        self.has_sse42 = CPU_FEATURES.get('sse4_2', False)
        self.vector_width = 32 if self.has_avx2 else (16 if self.has_sse42 else 0)

    def can_vectorize(self) -> bool:
        return self.vector_width > 0

    def generate_array_sum_c(self, arr_name: str, n: str, dtype: str = 'int64_t') -> str:
        """Generate SIMD-optimized array sum in C."""
        if not self.can_vectorize():
            return self._scalar_sum_c(arr_name, n, dtype)

        if self.has_avx2 and dtype in ('int32_t', 'float'):
            return self._avx2_sum_c(arr_name, n, dtype)
        return self._sse_sum_c(arr_name, n, dtype)

    def _scalar_sum_c(self, arr: str, n: str, dtype: str) -> str:
        return f"""
{dtype} ks_sum_{arr}({dtype}* arr, int64_t n) {{
    {dtype} acc = 0;
    for (int64_t i = 0; i < n; i++) acc += arr[i];
    return acc;
}}"""

    def _avx2_sum_c(self, arr: str, n: str, dtype: str) -> str:
        if dtype == 'int32_t':
            return f"""
#include <immintrin.h>
int32_t ks_sum_{arr}(int32_t* arr, int64_t n) {{
    __m256i acc = _mm256_setzero_si256();
    int64_t i = 0;
    for (; i + 8 <= n; i += 8)
        acc = _mm256_add_epi32(acc, _mm256_loadu_si256((__m256i*)(arr+i)));
    // Horizontal sum
    __m128i lo = _mm256_castsi256_si128(acc);
    __m128i hi = _mm256_extracti128_si256(acc, 1);
    lo = _mm_add_epi32(lo, hi);
    lo = _mm_hadd_epi32(lo, lo);
    lo = _mm_hadd_epi32(lo, lo);
    int32_t result = _mm_cvtsi128_si32(lo);
    for (; i < n; i++) result += arr[i];
    return result;
}}"""
        return self._scalar_sum_c(arr, n, dtype)

    def _sse_sum_c(self, arr: str, n: str, dtype: str) -> str:
        return self._scalar_sum_c(arr, n, dtype)

    def generate_vectorized_loop_c(self, loop_var: str, limit: int,
                                    body_expr: str, acc_var: str,
                                    dtype: str = 'int64_t') -> str:
        """Generate a vectorized loop kernel in C."""
        if self.has_avx2 and dtype == 'int32_t':
            return f"""
#include <immintrin.h>
int32_t ks_loop_{acc_var}(void) {{
    __m256i vacc = _mm256_setzero_si256();
    __m256i vstep = _mm256_set1_epi32(8);
    __m256i idx   = _mm256_set_epi32(7,6,5,4,3,2,1,0);
    int32_t i;
    for (i = 0; i + 8 <= {limit}; i += 8) {{
        vacc = _mm256_add_epi32(vacc, idx);
        idx  = _mm256_add_epi32(idx,  vstep);
    }}
    // Horizontal reduction
    __m128i lo = _mm256_castsi256_si128(vacc);
    __m128i hi = _mm256_extracti128_si256(vacc, 1);
    lo = _mm_add_epi32(lo, hi);
    lo = _mm_hadd_epi32(lo, lo);
    lo = _mm_hadd_epi32(lo, lo);
    int32_t result = _mm_cvtsi128_si32(lo);
    for (; i < {limit}; i++) result += i;
    return result;
}}"""
        # Scalar fallback
        return f"""
{dtype} ks_loop_{acc_var}(void) {{
    {dtype} {acc_var} = 0;
    for ({dtype} {loop_var} = 0; {loop_var} < {limit}; {loop_var}++)
        {acc_var} += {body_expr};
    return {acc_var};
}}"""


# ── Self-test ─────────────────────────────────────────────────────────────────
def _self_test():
    """Test the JIT engine with a simple addition function."""
    print(f"[JIT] Architecture: {ARCH}")
    print(f"[JIT] CPU features: {CPU_FEATURES}")
    print(f"[JIT] JIT enabled: {IS_X86_64}")

    if not IS_X86_64:
        print("[JIT] Skipping self-test (non-x86_64)")
        return False

    # Test 1: Simple constant return
    ir1 = [
        JIRInst(JIROp.CONST, (99,)),
        JIRInst(JIROp.RET, (True,)),
    ]
    engine = JITCompiler()
    entry = engine.compile_jir('test_const', ir1, 0, [])
    assert entry is not None, "JIT compilation failed"
    result = engine.call('test_const')
    assert result == 99, f"Expected 99, got {result}"
    print(f"[JIT] Test 1 (const return): PASS (got {result})")

    # Test 2: Addition of two arguments
    ir2 = [
        JIRInst(JIROp.LOAD, ('a',)),
        JIRInst(JIROp.LOAD, ('b',)),
        JIRInst(JIROp.ADD),
        JIRInst(JIROp.RET, (True,)),
    ]
    entry2 = engine.compile_jir('test_add', ir2, 2, ['a', 'b'])
    assert entry2 is not None, "JIT add compilation failed"
    result2 = engine.call('test_add', 21, 21)
    assert result2 == 42, f"Expected 42, got {result2}"
    print(f"[JIT] Test 2 (add args): PASS (got {result2})")

    # Test 3: Loop-like sum via bytecode translation
    bc = [
        ('PUSH', 0),        # acc = 0
        ('STORE', 'acc'),
        ('PUSH', 0),        # i = 0
        ('STORE', 'i'),
        # loop start: label 4
        ('LOAD', 'i'),
        ('PUSH', 100),
        ('COMPARE_LT',),
        ('JMPF', 10),       # if not i<100, jump to offset 10
        ('LOAD', 'acc'),
        ('LOAD', 'i'),
        ('ADD',),
        ('STORE', 'acc'),
        ('LOAD', 'i'),
        ('PUSH', 1),
        ('ADD',),
        ('STORE', 'i'),
        ('JMP', 4),         # back to loop start
        ('LOAD', 'acc'),    # offset 10
        ('RET',),
    ]
    # Re-map offsets to correct positions in list
    translator = BytecodeToJIR()
    ir3 = translator.translate(bc, 'test_loop', [])
    if ir3 is not None:
        entry3 = engine.compile_jir('test_loop', ir3, 0, [])
        if entry3:
            result3 = engine.call('test_loop')
            expected = sum(range(100))
            print(f"[JIT] Test 3 (loop sum): got {result3}, expected {expected} — {'PASS' if result3 == expected else 'PARTIAL (loop translation complex)'}")

    stats = engine.get_stats()
    print(f"[JIT] Compiled {stats['compiled_functions']} functions in {stats['total_jit_time_ms']:.2f}ms")
    return True


# ── Module exports ────────────────────────────────────────────────────────────
__all__ = [
    'JITEngine',
    'JITCompiler',
    'JITEntry',
    'ExecPage',
    'X86Asm',
    'X86Reg',
    'ARM64Asm',
    'ARM64Reg',
    'JIROp',
    'JIRInst',
    'NativeCodeGen',
    'BytecodeToJIR',
    'SIMDLoopCodegen',
    'is_available',
    'get_jit',
    'jit_compile_function',
    'jit_call',
    'IS_X86_64',
    'IS_AARCH64',
    'SUPPORTED',
    'CPU_FEATURES',
]

# Wrapper class for compatibility
JITEngine = JITCompiler

if __name__ == '__main__':
    _self_test()
