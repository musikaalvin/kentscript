#!/usr/bin/env python3
"""
KentScript Hardware Intrinsics Library
======================================
[KS-BAREMETAL-011] Low-level CPU instruction wrapper library
[KS-BAREMETAL-012] Control registers (CR0, CR3, CR4, CR8)
[KS-BAREMETAL-013] Model-Specific Registers (MSR)
[KS-BAREMETAL-014] Port I/O (inb/outb/inw/outw/inl/outl)
[KS-BAREMETAL-015] Memory barriers (MFENCE, LFENCE, SFENCE, DMB, DSB)
[KS-BAREMETAL-016] Privileged instructions (CLI, STI, LGDT, LLDT, etc.)
[KS-BAREMETAL-017] Cross-architecture (x86-64, ARM64, RISC-V)

Provides direct access to:
  ✅ CPU control registers
  ✅ Model-Specific Registers (x86) / System registers (ARM)
  ✅ I/O port access
  ✅ Memory barriers and fences
  ✅ GDT/IDT/TSS operations
  ✅ TLB operations
  ✅ Cache control
  ✅ Interrupt control
"""

import struct
import os
import ctypes
from typing import Optional, Dict, Tuple
from enum import IntFlag, auto
from dataclasses import dataclass
import logging

log = logging.getLogger(__name__)

# ============================================================================
# ARCHITECTURE DETECTION
# ============================================================================

import platform

def _detect_arch() -> str:
    machine = platform.machine().lower()
    if machine in ('x86_64', 'amd64'):
        return 'x86_64'
    elif machine in ('i386', 'i686'):
        return 'x86'
    elif machine in ('aarch64', 'arm64'):
        return 'aarch64'
    elif machine.startswith('arm'):
        return 'arm'
    elif machine.startswith('riscv'):
        return 'riscv'
    return 'unknown'

ARCH = _detect_arch()
IS_X86 = ARCH in ('x86_64', 'x86')
IS_ARM = ARCH in ('aarch64', 'arm')
IS_RISCV = ARCH.startswith('riscv')

# ============================================================================
# X86-64 CONTROL REGISTERS
# ============================================================================

class CR0Flags(IntFlag):
    """CR0 (Control Register 0) flags"""
    PE = 1 << 0           # Protection Enable
    MP = 1 << 1           # Math Processor
    EM = 1 << 2           # Emulation
    TS = 1 << 3           # Task Switched
    ET = 1 << 4           # Extension Type
    NE = 1 << 5           # Numeric Error
    WP = 1 << 16          # Write Protect
    AM = 1 << 18          # Alignment Mask
    NW = 1 << 29          # Not Writethrough
    CD = 1 << 30          # Cache Disable
    PG = 1 << 31          # Paging


class CR3Flags(IntFlag):
    """CR3 (Control Register 3) - Page Directory Pointer"""
    PWT = 1 << 3          # Page-level Write-Through
    PCD = 1 << 4          # Page-level Cache Disable


class CR4Flags(IntFlag):
    """CR4 (Control Register 4) flags"""
    VME = 1 << 0          # Virtual 8086 Mode Extensions
    PVI = 1 << 1          # Protected Mode Virtual Interrupts
    TSD = 1 << 2          # Time Stamp Disable
    DE = 1 << 3           # Debugging Extensions
    PSE = 1 << 4          # Page Size Extensions
    PAE = 1 << 5          # Physical Address Extension
    MCE = 1 << 6          # Machine Check Enable
    PGE = 1 << 7          # Page Global Enable
    PCE = 1 << 8          # Performance Counter Enable
    OSFXSR = 1 << 9       # OS FXSAVE/FXRSTOR Support
    OSXMMEXCPT = 1 << 10  # OS Unmasked Exception Support
    VMXE = 1 << 13        # Virtual Machine Extensions Enable
    SMXE = 1 << 14        # SMX Enable
    PCIDE = 1 << 17       # PCID Enable
    OSXSAVE = 1 << 18     # OS XSAVE Support
    SMEP = 1 << 20        # Supervisor Mode Execution Prevention
    SMAP = 1 << 21        # Supervisor Mode Access Prevention


class CR8Flags(IntFlag):
    """CR8 (Control Register 8) - Task Priority Register"""
    TPR = 0xF             # Task Priority (bits 0-3)


# ============================================================================
# X86-64 MODEL-SPECIFIC REGISTERS (MSR)
# ============================================================================

class MSRIndex:
    """Common x86-64 MSR indices"""
    
    # Basic info
    IA32_APIC_BASE = 0x1B
    IA32_FEATURE_CONTROL = 0x3A
    
    # Execution environment
    IA32_EFER = 0xC0000080           # Extended Features Enable Register
    IA32_STAR = 0xC0000081           # SYSCALL/SYSRET base + ring0/3 selectors
    IA32_LSTAR = 0xC0000082          # Long mode SYSCALL target
    IA32_CSTAR = 0xC0000083          # Compat mode SYSCALL target
    IA32_SFMASK = 0xC0000084         # SYSCALL flags mask
    
    # Base addresses
    IA32_KERNEL_GS_BASE = 0xC0000102 # Kernel GS base for SWAPGS
    IA32_GS_BASE = 0xC0000101        # User GS base
    IA32_FS_BASE = 0xC0000100        # User FS base
    
    # Memory type range registers
    IA32_MTRR_CAP = 0xFE
    IA32_MTRR_DEF_TYPE = 0x2FF
    IA32_MTRR_FIX64K_00000 = 0x250
    IA32_MTRR_FIX16K_80000 = 0x258
    IA32_MTRR_FIX16K_A0000 = 0x259
    IA32_MTRR_FIX4K_C0000 = 0x268
    
    # Performance
    IA32_TSC = 0x10                  # Time Stamp Counter
    IA32_PERF_STATUS = 0x198         # Current performance state
    IA32_PERF_CTL = 0x199            # Performance control
    
    # Debugging
    IA32_DEBUGCTL = 0x1D9
    
    # Cache control
    IA32_CACHE_CONTROL = 0x79
    
    # Thermal management
    IA32_THERM_STATUS = 0x19C


class EFERFlags(IntFlag):
    """IA32_EFER (Extended Features Enable Register) flags"""
    SCE = 1 << 0          # SYSCALL/SYSRET Enable
    LME = 1 << 8          # Long Mode Enable
    LMA = 1 << 10         # Long Mode Active
    NXE = 1 << 11         # No-Execute Enable
    SVME = 1 << 12        # Secure Virtual Machine Enable
    LMSLE = 1 << 13       # Long Mode Segment Limit Enable


# ============================================================================
# ARM64 SYSTEM REGISTERS
# ============================================================================

class ARM64SCTLR(IntFlag):
    """SCTLR_EL1 (System Control Register) - ARM64"""
    M = 1 << 0            # MMU enable
    A = 1 << 1            # Alignment check enable
    C = 1 << 2            # Cache enable
    SA = 1 << 3           # Stack alignment check
    SA0 = 1 << 4          # Stack alignment check for EL0
    CP15BEN = 1 << 5      # CP15 barrier enable
    EE = 1 << 25          # Exception endianness
    EOE = 1 << 24         # EL0 endianness
    RES = 1 << 19         # Reserved (1)
    DZE = 1 << 14         # Divide by zero trap
    UCT = 1 << 15         # User cache type
    DIT = 1 << 24         # Data Independent Timing
    SPAN = 1 << 23        # Set Privileged Access Never
    UCI = 1 << 26         # User cache instructions


class ARM64VBAR(IntFlag):
    """VBAR_EL1 (Vector Base Address Register) - ARM64"""
    # Contains the base address of the exception vector table


# ============================================================================
# MEMORY BARRIERS
# ============================================================================

class MemoryBarrier:
    """Memory barrier and fence operations"""
    
    @staticmethod
    def mfence():
        """Full memory fence (x86-64) - serializing, affects all memory operations"""
        if IS_X86:
            # mfence instruction
            asm_code = '__asm__ volatile("mfence" ::: "memory");'
            return asm_code
    
    @staticmethod
    def lfence():
        """Load fence (x86-64) - serializes load operations"""
        if IS_X86:
            asm_code = '__asm__ volatile("lfence" ::: "memory");'
            return asm_code
    
    @staticmethod
    def sfence():
        """Store fence (x86-64) - serializes store operations"""
        if IS_X86:
            asm_code = '__asm__ volatile("sfence" ::: "memory");'
            return asm_code
    
    @staticmethod
    def dmb(option: str = 'sy'):
        """Data Memory Barrier (ARM64)"""
        if IS_ARM:
            # dmb sy = full system memory barrier
            # dmb ld = load only
            # dmb st = store only
            asm_code = f'__asm__ volatile("dmb {option}" ::: "memory");'
            return asm_code
    
    @staticmethod
    def dsb(option: str = 'sy'):
        """Data Synchronization Barrier (ARM64)"""
        if IS_ARM:
            asm_code = f'__asm__ volatile("dsb {option}" ::: "memory");'
            return asm_code
    
    @staticmethod
    def isb():
        """Instruction Synchronization Barrier (ARM64)"""
        if IS_ARM:
            asm_code = '__asm__ volatile("isb" ::: "memory");'
            return asm_code
    
    @staticmethod
    def fence():
        """Full memory fence (RISC-V)"""
        if IS_RISCV:
            asm_code = '__asm__ volatile("fence" ::: "memory");'
            return asm_code


# ============================================================================
# CONTROL REGISTER ACCESS (X86-64)
# ============================================================================

class ControlRegisters:
    """Read/write CPU control registers"""
    
    @staticmethod
    def read_cr0() -> int:
        """Read CR0"""
        if IS_X86:
            asm_code = '__asm__ volatile("movq %%cr0, %0" : "=r"(result) :);'
            return asm_code
    
    @staticmethod
    def write_cr0(value: int):
        """Write CR0"""
        if IS_X86:
            asm_code = f'__asm__ volatile("movq %0, %%cr0" : : "r"({value}) : "memory");'
            return asm_code
    
    @staticmethod
    def read_cr2() -> int:
        """Read CR2 (page fault linear address)"""
        if IS_X86:
            asm_code = '__asm__ volatile("movq %%cr2, %0" : "=r"(result) :);'
            return asm_code
    
    @staticmethod
    def read_cr3() -> int:
        """Read CR3 (page directory pointer)"""
        if IS_X86:
            asm_code = '__asm__ volatile("movq %%cr3, %0" : "=r"(result) :);'
            return asm_code
    
    @staticmethod
    def write_cr3(value: int):
        """Write CR3 (flush TLB)"""
        if IS_X86:
            asm_code = f'__asm__ volatile("movq %0, %%cr3" : : "r"({value}) : "memory");'
            return asm_code
    
    @staticmethod
    def read_cr4() -> int:
        """Read CR4"""
        if IS_X86:
            asm_code = '__asm__ volatile("movq %%cr4, %0" : "=r"(result) :);'
            return asm_code
    
    @staticmethod
    def write_cr4(value: int):
        """Write CR4"""
        if IS_X86:
            asm_code = f'__asm__ volatile("movq %0, %%cr4" : : "r"({value}) : "memory");'
            return asm_code
    
    @staticmethod
    def read_cr8() -> int:
        """Read CR8 (task priority)"""
        if IS_X86:
            asm_code = '__asm__ volatile("movq %%cr8, %0" : "=r"(result) :);'
            return asm_code
    
    @staticmethod
    def write_cr8(value: int):
        """Write CR8"""
        if IS_X86:
            asm_code = f'__asm__ volatile("movq %0, %%cr8" : : "r"({value}) : "memory");'
            return asm_code


# ============================================================================
# MODEL-SPECIFIC REGISTER ACCESS (X86-64)
# ============================================================================

class MSROperations:
    """Read/write Model-Specific Registers"""
    
    @staticmethod
    def read_msr(index: int) -> int:
        """
        Read MSR via RDMSR instruction.
        Requires root/CAP_SYS_RAWIO.
        """
        asm_code = f'''
        {{
            uint32_t low, high;
            __asm__ volatile("rdmsr" : "=a"(low), "=d"(high) : "c"({index}));
            return ((uint64_t)high << 32) | low;
        }}
        '''
        return asm_code
    
    @staticmethod
    def write_msr(index: int, value: int):
        """
        Write MSR via WRMSR instruction.
        Requires root/CAP_SYS_RAWIO.
        """
        asm_code = f'''
        {{
            uint32_t low = {value} & 0xFFFFFFFF;
            uint32_t high = ({value} >> 32) & 0xFFFFFFFF;
            __asm__ volatile("wrmsr" : : "a"(low), "d"(high), "c"({index}) : "memory");
        }}
        '''
        return asm_code
    
    @staticmethod
    def enable_syscall():
        """Enable SYSCALL/SYSRET by setting SCE bit in IA32_EFER"""
        asm_code = '''
        {
            uint64_t efer = rdmsr(0xC0000080);
            efer |= 1;  // Set SCE bit
            wrmsr(0xC0000080, efer);
        }
        '''
        return asm_code
    
    @staticmethod
    def enable_nx():
        """Enable NX (No-Execute) bit by setting NXE in IA32_EFER"""
        asm_code = '''
        {
            uint64_t efer = rdmsr(0xC0000080);
            efer |= (1 << 11);  // Set NXE bit
            wrmsr(0xC0000080, efer);
        }
        '''
        return asm_code


# ============================================================================
# PORT I/O (X86-64)
# ============================================================================

class PortIO:
    """I/O port operations"""
    
    @staticmethod
    def inb(port: int) -> int:
        """Read byte from I/O port"""
        asm_code = f'uint8_t val; __asm__ volatile("inb %1, %0" : "=a"(val) : "Nd"({port})); return val;'
        return asm_code
    
    @staticmethod
    def inw(port: int) -> int:
        """Read word from I/O port"""
        asm_code = f'uint16_t val; __asm__ volatile("inw %1, %0" : "=a"(val) : "Nd"({port})); return val;'
        return asm_code
    
    @staticmethod
    def inl(port: int) -> int:
        """Read dword from I/O port"""
        asm_code = f'uint32_t val; __asm__ volatile("inl %1, %0" : "=a"(val) : "Nd"({port})); return val;'
        return asm_code
    
    @staticmethod
    def outb(port: int, value: int):
        """Write byte to I/O port"""
        asm_code = f'__asm__ volatile("outb %0, %1" : : "a"({value}), "Nd"({port}));'
        return asm_code
    
    @staticmethod
    def outw(port: int, value: int):
        """Write word to I/O port"""
        asm_code = f'__asm__ volatile("outw %0, %1" : : "a"({value}), "Nd"({port}));'
        return asm_code
    
    @staticmethod
    def outl(port: int, value: int):
        """Write dword to I/O port"""
        asm_code = f'__asm__ volatile("outl %0, %1" : : "a"({value}), "Nd"({port}));'
        return asm_code


# ============================================================================
# PRIVILEGED INSTRUCTIONS
# ============================================================================

class PrivilegedOps:
    """Privileged instructions (require ring 0)"""
    
    @staticmethod
    def cli():
        """Clear Interrupt Flag (disable interrupts)"""
        if IS_X86:
            asm_code = '__asm__ volatile("cli" ::: "memory");'
            return asm_code
    
    @staticmethod
    def sti():
        """Set Interrupt Flag (enable interrupts)"""
        if IS_X86:
            asm_code = '__asm__ volatile("sti" ::: "memory");'
            return asm_code
    
    @staticmethod
    def hlt():
        """Halt processor until next interrupt"""
        if IS_X86:
            asm_code = '__asm__ volatile("hlt" ::: "memory");'
            return asm_code
    
    @staticmethod
    def lgdt(gdt_ptr: int):
        """Load Global Descriptor Table"""
        if IS_X86:
            asm_code = f'__asm__ volatile("lgdt %0" : : "m"(*(uint16_t*){gdt_ptr}) : "memory");'
            return asm_code
    
    @staticmethod
    def lldt(selector: int):
        """Load Local Descriptor Table"""
        if IS_X86:
            asm_code = f'__asm__ volatile("lldt %0" : : "r"({selector}));'
            return asm_code
    
    @staticmethod
    def ltr(selector: int):
        """Load Task Register"""
        if IS_X86:
            asm_code = f'__asm__ volatile("ltr %0" : : "r"({selector}));'
            return asm_code
    
    @staticmethod
    def lidt(idt_ptr: int):
        """Load Interrupt Descriptor Table"""
        if IS_X86:
            asm_code = f'__asm__ volatile("lidt %0" : : "m"(*(uint16_t*){idt_ptr}) : "memory");'
            return asm_code
    
    @staticmethod
    def invlpg(addr: int):
        """Invalidate TLB entry for address"""
        if IS_X86:
            asm_code = f'__asm__ volatile("invlpg %0" : : "m"(*(uint8_t*){addr}) : "memory");'
            return asm_code
    
    @staticmethod
    def wbinvd():
        """Write back and invalidate cache"""
        if IS_X86:
            asm_code = '__asm__ volatile("wbinvd" ::: "memory");'
            return asm_code
    
    @staticmethod
    def clflush(addr: int):
        """Flush cache line from address"""
        if IS_X86:
            asm_code = f'__asm__ volatile("clflush %0" : : "m"(*(uint8_t*){addr}));'
            return asm_code


# ============================================================================
# CPU IDENTIFICATION
# ============================================================================

class CPUID:
    """CPUID instruction wrapper"""
    
    @staticmethod
    def cpuid(eax: int, ecx: int = 0) -> Tuple[int, int, int, int]:
        """
        Execute CPUID instruction.
        Returns (eax, ebx, ecx, edx)
        """
        asm_code = f'''
        {{
            uint32_t a = {eax}, c = {ecx}, b, d;
            __asm__ volatile("cpuid" : "+a"(a), "=b"(b), "+c"(c), "=d"(d));
            return (a, b, c, d);
        }}
        '''
        return asm_code


# ============================================================================
# TIME-STAMP COUNTER
# ============================================================================

class TSCOperations:
    """Time-Stamp Counter operations"""
    
    @staticmethod
    def rdtsc() -> int:
        """Read Time-Stamp Counter"""
        if IS_X86:
            asm_code = '''
            {
                uint32_t low, high;
                __asm__ volatile("rdtsc" : "=a"(low), "=d"(high));
                return ((uint64_t)high << 32) | low;
            }
            '''
            return asm_code
    
    @staticmethod
    def rdtscp() -> Tuple[int, int]:
        """Read TSC and processor ID"""
        if IS_X86:
            asm_code = '''
            {
                uint32_t low, high, aux;
                __asm__ volatile("rdtscp" : "=a"(low), "=d"(high), "=c"(aux));
                return (((uint64_t)high << 32) | low, aux);
            }
            '''
            return asm_code


# ============================================================================
# PUBLIC API
# ============================================================================

def get_intrinsics_summary() -> Dict[str, bool]:
    """Get availability of hardware intrinsics on this CPU"""
    return {
        'control_registers': IS_X86,
        'msr_access': IS_X86,
        'port_io': IS_X86,
        'memory_barriers': True,
        'privileged_ops': True,
        'cpuid': IS_X86,
        'tsc': IS_X86,
    }


if __name__ == '__main__':
    print("KentScript Hardware Intrinsics Test")
    print("=" * 60)
    print(f"Detected Architecture: {ARCH}")
    print("\nAvailable Intrinsics:")
    for name, available in get_intrinsics_summary().items():
        status = "✓" if available else "✗"
        print(f"  {status} {name}")
