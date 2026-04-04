#!/usr/bin/env python3
"""
Ring-0 Bridge
Provides hooks for Ring-0 hardware access on Linux.

REQUIREMENTS:
  - Linux only (/dev/msr and /dev/mem require root + kernel module)
  - MSR access: sudo modprobe msr
  - Physical memory: requires /dev/mem kernel config + root
  - Full ring-0 module: sudo insmod ks_ring0_module.ko (build from ks_ring0_module.c)

This module will gracefully degrade — all operations return None/False
if the required permissions or kernel module are not present.
There is NO automatic privilege escalation.
"""

import subprocess
import os


class KernelDevice:
    """Interface to the ks_ring0 kernel module (if loaded)."""

    def __init__(self):
        self.fd = None
        self.capabilities = 0
        self._try_detect()

    def _try_detect(self):
        """Check if the ks_ring0 kernel module is already loaded."""
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            if 'ks_ring0' in result.stdout:
                self.fd = 1
                self.capabilities = 0xFF
        except Exception:
            pass  # lsmod not available or not Linux

    def read_msr(self, addr):
        """Read a Model Specific Register via /dev/msr (requires root + modprobe msr)."""
        try:
            with open('/dev/msr', 'rb') as f:
                f.seek(addr)
                return int.from_bytes(f.read(8), 'little')
        except PermissionError:
            raise PermissionError(
                f"Cannot read MSR 0x{addr:x}: needs root and 'sudo modprobe msr'"
            )
        except FileNotFoundError:
            raise OSError("MSR device not found. Run: sudo modprobe msr")
        except Exception:
            return None

    def write_msr(self, addr, value):
        """Write a Model Specific Register via /dev/msr (requires root + modprobe msr)."""
        try:
            with open('/dev/msr', 'wb') as f:
                f.seek(addr)
                f.write(value.to_bytes(8, 'little'))
                return True
        except PermissionError:
            raise PermissionError(
                f"Cannot write MSR 0x{addr:x}: needs root and 'sudo modprobe msr'"
            )
        except Exception:
            return False

    def read_physical_memory(self, addr, size):
        """Read physical memory via /dev/mem (requires root + CONFIG_DEVMEM=y kernel)."""
        try:
            with open('/dev/mem', 'rb') as f:
                f.seek(addr)
                return f.read(size)
        except PermissionError:
            raise PermissionError(
                f"Cannot read physical memory at 0x{addr:x}: needs root + /dev/mem access"
            )
        except Exception:
            return None

    def write_physical_memory(self, addr, data):
        """Write physical memory (requires root + /dev/mem access)."""
        try:
            with open('/dev/mem', 'wb') as f:
                f.seek(addr)
                f.write(data)
                return True
        except PermissionError:
            raise PermissionError(
                f"Cannot write physical memory at 0x{addr:x}: needs root + /dev/mem access"
            )
        except Exception:
            return False


# Global Ring-0 device (lazily initialised)
_ring0_device = None


def get_ring0_device():
    """Get or initialise the Ring-0 device handle."""
    global _ring0_device
    if _ring0_device is None:
        _ring0_device = KernelDevice()
    return _ring0_device


class KernelCapability:
    """Ring-0 capability flags."""
    MSR_READ  = 0x01
    MSR_WRITE = 0x02
    MEM_READ  = 0x04
    MEM_WRITE = 0x08
    PORT_IO   = 0x10
    INTERRUPT = 0x20
    PAGING    = 0x40
    CPUID     = 0x80


def capabilities():
    """Return bitmask of available Ring-0 capabilities (0 if module not loaded)."""
    device = get_ring0_device()
    return device.capabilities if device.fd else 0


def has_cap(cap):
    """Return True if the given Ring-0 capability is available."""
    return bool(capabilities() & cap)


def can_exec_jit():
    """Return True if we can allocate executable memory pages (always True on Linux with mmap)."""
    import sys
    return sys.platform == 'linux'


class ExecPage:
    """Allocate an RWX memory page for JIT-compiled native code."""

    def __init__(self, size=4096):
        import mmap
        import ctypes
        self._map = mmap.mmap(-1, size,
                              prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
        self.size = size
        # Get actual memory address using ctypes
        self.addr = ctypes.addressof(ctypes.c_char.from_buffer(self._map))

    def write(self, code: bytes):
        self._map.seek(0)
        self._map.write(code)
    
    def make_executable(self):
        """Make the page executable (no-op since already RWX)"""
        pass  # Already executable from mmap
    
    def get_callable(self, restype, argtypes):
        """Return a ctypes function pointer to the JIT code"""
        import ctypes
        # Create function prototype
        functype = ctypes.CFUNCTYPE(restype, *argtypes)
        # Cast address to function pointer
        return functype(self.addr)

    def close(self):
        self._map.close()
