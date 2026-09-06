#!/usr/bin/env python3
"""
Hardware Discovery - Cross-platform hardware detection
Detects CPU, memory, PCI devices, peripherals on:
- Windows (via WinAPI, registry, WMI)
- macOS (via IOKit, sysctl)
- Linux (via /proc, /sys, device-tree)
- Android (via /proc, /sys, proprietary HALs)
- BSD (via sysctl, /dev/mem)

Ring-0 access attempted where possible, falls back to safe queries
"""

import os
import sys
import platform
import subprocess
import struct
import re
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field

# Ring-0 bridge: real capability detection and physical memory access
try:
    from kernel_bridge import (capabilities, KernelCapability, has_cap,
                                  phys_mem, msr, port_io,
                                  read_iomem, read_ioports,
                                  can_exec_jit)
    _RING0_INTRINSICS = True
except ImportError:
    _RING0_INTRINSICS = False
    capabilities = lambda: 0
    has_cap = lambda c: False
    phys_mem = None
    msr = None
    port_io = None
    read_iomem = lambda: {}
    read_ioports = lambda: {}


class OS(Enum):
    """Supported operating systems"""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    ANDROID = "android"
    BSD = "bsd"
    UNKNOWN = "unknown"
    
    @staticmethod
    def detect() -> 'OS':
        """Detect current operating system.
        Handles Termux, Kali-chroot-on-Android, and proot/chroot environments.
        """
        if sys.platform == 'win32':
            return OS.WINDOWS
        elif sys.platform == 'darwin':
            return OS.MACOS
        elif sys.platform.startswith('linux'):
            # Android indicators (works even inside chroot/proot/Termux)
            android_hints = [
                '/system/build.prop',
                '/system/bin/sh',
                '/system/framework',
                '/data/data/com.termux',          # Termux native
                '/data/adb',                       # Magisk / ADB
                '/proc/sys/kernel/sched_boost',    # Android scheduler
            ]
            for hint in android_hints:
                if os.path.exists(hint):
                    return OS.ANDROID

            # Check /proc/version for Android kernel string
            try:
                with open('/proc/version', 'r') as f:
                    pv = f.read().lower()
                if 'android' in pv:
                    return OS.ANDROID
            except Exception:
                pass

            # Check kernel cmdline for androidboot
            try:
                with open('/proc/cmdline', 'r') as f:
                    if 'androidboot' in f.read():
                        return OS.ANDROID
            except Exception:
                pass

            # Check getprop availability (Termux / Android)
            try:
                r = subprocess.run(['getprop', 'ro.build.version.release'],
                                   capture_output=True, text=True, timeout=2)
                if r.returncode == 0 and r.stdout.strip():
                    return OS.ANDROID
            except Exception:
                pass

            return OS.LINUX
        elif sys.platform.startswith(('freebsd', 'openbsd', 'netbsd')):
            return OS.BSD
        return OS.UNKNOWN


class Arch(Enum):
    """CPU architectures"""
    X86 = "x86"
    X86_64 = "x86_64"
    ARM = "arm"
    ARM64 = "arm64"
    RISCV = "riscv"
    POWERPC = "powerpc"
    UNKNOWN = "unknown"
    
    @staticmethod
    def detect() -> 'Arch':
        """Detect CPU architecture"""
        machine = platform.machine().lower()
        
        if machine in ('x86_64', 'amd64'):
            return Arch.X86_64
        elif machine in ('i386', 'i686', 'x86'):
            return Arch.X86
        elif machine in ('aarch64', 'arm64'):
            return Arch.ARM64
        elif machine.startswith('arm'):
            return Arch.ARM
        elif machine.startswith('riscv'):
            return Arch.RISCV
        elif machine.startswith(('ppc', 'power')):
            return Arch.POWERPC
        return Arch.UNKNOWN


@dataclass
class CPUInfo:
    """CPU information"""
    vendor: str = ""
    model: str = ""
    cores: int = 0
    threads: int = 0
    features: List[str] = field(default_factory=list)
    frequency_mhz: float = 0.0
    cache_size: Dict[str, int] = field(default_factory=dict)  # L1, L2, L3 in KB
    soc: str = ""  # SoC name (Android/embedded)


@dataclass
class MemoryInfo:
    """Memory information"""
    total_bytes: int = 0
    free_bytes: int = 0
    available_bytes: int = 0
    page_size: int = 4096
    numa_nodes: int = 1


@dataclass
class PCIeDevice:
    """PCIe device information"""
    bus: int
    device: int
    func: int
    vendor_id: int
    device_id: int
    class_code: int
    subsystem_vendor: Optional[int] = None
    subsystem_device: Optional[int] = None
    driver: Optional[str] = None
    mmio_bars: List[Tuple[int, int]] = field(default_factory=list)  # (address, size)
    description: str = ""


@dataclass
class USBDevice:
    """USB device information"""
    bus: int
    address: int
    vendor_id: int
    product_id: int
    class_code: int
    manufacturer: str = ""
    product: str = ""
    speed: str = ""
    description: str = ""


@dataclass
class Peripheral:
    """Generic peripheral at physical address"""
    name: str
    phys_base: int
    size: int
    description: str = ""
    driver: Optional[str] = None


class HardwareDiscovery:
    """
    Cross-platform hardware discovery.
    Detects CPU, memory, PCIe, USB, and memory-mapped peripherals.
    Works on Windows, macOS, Linux, Android, BSD.
    
    Usage:
        hw = HardwareDiscovery()
        print(hw.report())
        
        # Get specific peripheral
        uart_base = hw.find_peripheral("uart")
        if uart_base:
            mmio_read(uart_base)
    """
    
    def __init__(self):
        self.os = OS.detect()
        self.arch = Arch.detect()
        self.cpu = CPUInfo()
        self.memory = MemoryInfo()
        self.pci_devices: List[PCIeDevice] = []
        self.usb_devices: List[USBDevice] = []
        self.peripherals: Dict[str, Peripheral] = {}
        self._initialized = False
        self._has_ring0 = self._check_ring0()
        
        # Platform-specific handlers
        self._init_platform()
    
    def _check_ring0(self) -> bool:
        """Check ring-0 / elevated access via multiple methods."""
        if _RING0_INTRINSICS:
            return has_cap(KernelCapability.EUID_ROOT) or has_cap(KernelCapability.CAP_SYS_ADMIN)

        if self.os == OS.WINDOWS:
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                return False

        # POSIX: try every reliable indicator
        try:
            if os.geteuid() == 0:
                return True
        except Exception:
            pass

        # CAP_SYS_ADMIN via /proc/self/status
        try:
            with open('/proc/self/status', 'r') as f:
                for line in f:
                    if line.startswith('CapEff:'):
                        capeff = int(line.split(':')[1].strip(), 16)
                        # Bit 21 = CAP_SYS_ADMIN
                        if capeff & (1 << 21):
                            return True
        except Exception:
            pass

        # Android root: check su binary and Magisk
        for p in ('/system/xbin/su', '/system/bin/su', '/sbin/su',
                  '/data/local/tmp/su', '/system/app/Superuser.apk',
                  '/data/adb/magisk', '/sbin/magiskd'):
            if os.path.exists(p):
                return True

        # Try writing to a privileged path as smoke test
        try:
            with open('/proc/sysrq-trigger', 'rb'):
                return True
        except Exception:
            pass

        # /proc/iomem readable = has kernel memory map access
        try:
            with open('/proc/iomem', 'r') as f:
                content_test = f.read(64)
            if content_test.strip():
                return True
        except Exception:
            pass

        # /dev/mem exists and is accessible
        try:
            fd = os.open('/dev/mem', os.O_RDONLY)
            os.close(fd)
            return True
        except Exception:
            pass

        # Termux: check if we're running as Android root (uid 0 in Android namespace)
        try:
            r = subprocess.run(['id'], capture_output=True, text=True, timeout=2)
            if 'uid=0' in r.stdout:
                return True
        except Exception:
            pass

        return False
    
    def _init_platform(self):
        """Initialize platform-specific detectors"""
        if self.os == OS.WINDOWS:
            self._init_windows()
        elif self.os == OS.MACOS:
            self._init_macos()
        elif self.os == OS.LINUX:
            self._init_linux()
        elif self.os == OS.ANDROID:
            self._init_android()
        elif self.os == OS.BSD:
            self._init_bsd()
        
        self._initialized = True
    
    def _init_windows(self):
        """Windows-specific initialization"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Get CPU info via Windows API
            self._get_windows_cpu()
            
            # Get memory info
            self._get_windows_memory()
            
            # Get PCI devices via SetupAPI
            self._get_windows_pci()
            
            # Get USB devices
            self._get_windows_usb()
            
        except Exception as e:
            print(f"[Windows] Error: {e}")
    
    def _get_windows_cpu(self):
        """Get CPU info on Windows"""
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            
            # Get number of processors
            system_info = ctypes.create_string_buffer(36)  # SYSTEM_INFO size
            kernel32.GetSystemInfo(system_info)
            
            # Parse SYSTEM_INFO (simplified)
            self.cpu.cores = int.from_bytes(system_info[8:12], 'little')
            
            # Get processor name from registry
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                 r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            self.cpu.model = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            self.cpu.vendor = winreg.QueryValueEx(key, "VendorIdentifier")[0]
            winreg.CloseKey(key)
            
            # Get CPU features via CPUID
            self.cpu.features = self._cpuid_windows()
            
        except Exception as e:
            print(f"Windows CPU detection failed: {e}")
    
    def _cpuid_windows(self) -> List[str]:
        """Execute CPUID instruction on Windows"""
        features = []
        try:
            import ctypes
            class CPUID(ctypes.Structure):
                _fields_ = [("eax", ctypes.c_uint), ("ebx", ctypes.c_uint),
                           ("ecx", ctypes.c_uint), ("edx", ctypes.c_uint)]
            
            cpuid = ctypes.windll.__cpuidex
            cpuid.argtypes = [ctypes.POINTER(CPUID), ctypes.c_uint, ctypes.c_uint]
            
            regs = CPUID()
            
            # Check for features (EAX=1)
            cpuid(ctypes.byref(regs), 1, 0)
            
            feature_map = {
                0: "SSE3", 1: "PCLMUL", 2: "DTES64", 3: "MONITOR",
                4: "DS-CPL", 5: "VMX", 6: "SMX", 7: "EIST",
                8: "TM2", 9: "SSSE3", 10: "CNXT-ID", 11: "SDBG",
                12: "FMA", 13: "CX16", 14: "XTPR", 15: "PDCM",
                16: "PCID", 17: "DCA", 18: "SSE4_1", 19: "SSE4_2",
                20: "X2APIC", 21: "MOVBE", 22: "POPCNT", 23: "TSC-DEADLINE",
                24: "AES", 25: "XSAVE", 26: "OSXSAVE", 27: "AVX",
            }
            
            for bit, name in feature_map.items():
                if regs.ecx & (1 << bit):
                    features.append(name)
            
        except:
            pass
        return features
    
    def _get_windows_memory(self):
        """Get memory info on Windows"""
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            
            if kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
                self.memory.total_bytes = mem.ullTotalPhys
                self.memory.available_bytes = mem.ullAvailPhys
        except:
            pass
    
    def _get_windows_pci(self):
        """Get PCI devices on Windows"""
        try:
            import winreg
            
            # PCI devices are in registry under
            # HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\PCI
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\PCI")
            
            i = 0
            while True:
                try:
                    dev_key_name = winreg.EnumKey(key, i)
                    dev_key = winreg.OpenKey(key, dev_key_name)
                    
                    # Parse PCI address from key name (VEN_xxxx&DEV_yyyy)
                    if 'VEN_' in dev_key_name and 'DEV_' in dev_key_name:
                        parts = dev_key_name.split('&')
                        for p in parts:
                            if p.startswith('VEN_'):
                                vendor = int(p[4:], 16)
                            elif p.startswith('DEV_'):
                                device = int(p[4:], 16)
                        
                        # Get hardware IDs
                        try:
                            hw_key = winreg.OpenKey(dev_key, r"Hardware")
                            hw_ids = winreg.QueryValueEx(hw_key, "HardwareID")[0]
                            winreg.CloseKey(hw_key)
                        except:
                            hw_ids = []
                        
                        self.pci_devices.append(PCIeDevice(
                            bus=0, device=0, func=0,
                            vendor_id=vendor,
                            device_id=device,
                            class_code=0,
                            driver=hw_ids[0] if hw_ids else None
                        ))
                    
                    winreg.CloseKey(dev_key)
                    i += 1
                except WindowsError:
                    break
            
            winreg.CloseKey(key)
        except:
            pass
    
    def _get_windows_usb(self):
        """Get USB devices on Windows"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\USB")
            
            i = 0
            while True:
                try:
                    dev_key_name = winreg.EnumKey(key, i)
                    dev_key = winreg.OpenKey(key, dev_key_name)
                    
                    # Parse VID/PID
                    if 'VID_' in dev_key_name and 'PID_' in dev_key_name:
                        parts = dev_key_name.split('&')
                        vid = pid = 0
                        for p in parts:
                            if p.startswith('VID_'):
                                vid = int(p[4:], 16)
                            elif p.startswith('PID_'):
                                pid = int(p[4:], 16)
                        
                        # Get device info
                        try:
                            dev_params = winreg.OpenKey(dev_key, "Device Parameters")
                            winreg.CloseKey(dev_params)
                        except:
                            pass
                        
                        self.usb_devices.append(USBDevice(
                            bus=0, address=0,
                            vendor_id=vid,
                            product_id=pid,
                            class_code=0
                        ))
                    
                    winreg.CloseKey(dev_key)
                    i += 1
                except WindowsError:
                    break
            winreg.CloseKey(key)
        except:
            pass
    
    def _init_macos(self):
        """macOS-specific initialization"""
        try:
            # Get CPU info via sysctl
            self._get_macos_sysctl()
            
            # Get IOKit devices
            self._get_macos_iokit()
            
        except Exception as e:
            print(f"[macOS] Error: {e}")
    
    def _get_macos_sysctl(self):
        """Get hardware info via sysctl on macOS"""
        try:
            import subprocess
            
            # CPU cores
            result = subprocess.run(['sysctl', '-n', 'hw.ncpu'], 
                                   capture_output=True, text=True)
            self.cpu.cores = int(result.stdout.strip())
            
            # CPU model
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'],
                                   capture_output=True, text=True)
            self.cpu.model = result.stdout.strip()
            
            # CPU features
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.features'],
                                   capture_output=True, text=True)
            self.cpu.features = result.stdout.strip().split()
            
            # Memory
            result = subprocess.run(['sysctl', '-n', 'hw.memsize'],
                                   capture_output=True, text=True)
            self.memory.total_bytes = int(result.stdout.strip())
            
        except:
            pass
    
    def _get_macos_iokit(self):
        """Get IOKit devices on macOS"""
        try:
            import subprocess
            
            # Use ioreg to get device tree
            result = subprocess.run(['ioreg', '-r', '-c', 'IOPlatformDevice'],
                                   capture_output=True, text=True)
            
            # Parse IOReg output for MMIO peripherals
            current_periph = None
            for line in result.stdout.split('\n'):
                if '+-o' in line:
                    # New device
                    name_match = re.search(r'<class ([^,]+)', line)
                    if name_match:
                        current_periph = name_match.group(1)
                
                elif '"reg"' in line and current_periph:
                    # MMIO region
                    reg_match = re.search(r'= <([0-9a-f]+)>', line.lower())
                    if reg_match:
                        reg_hex = reg_match.group(1)
                        # Parse Apple's device tree format
                        if len(reg_hex) >= 16:
                            addr = int(reg_hex[:16], 16)
                            size = int(reg_hex[16:], 16) if len(reg_hex) > 16 else 0x1000
                            self.peripherals[current_periph.lower()] = Peripheral(
                                name=current_periph.lower(),
                                phys_base=addr,
                                size=size,
                                description=f"IOKit device {current_periph}"
                            )
        except:
            pass
    
    def _init_linux(self):
        """Linux-specific initialization — also handles Kali/Termux chroot on Android."""
        try:
            # CPU info — ARM64 and x86 aware
            self._get_linux_cpu()

            # Memory info
            self._get_linux_memory()

            # PCI devices (lspci → sysfs → /proc fallback)
            self._get_linux_pci()

            # USB devices (lsusb → sysfs fallback)
            self._get_linux_usb()

            # Device tree peripherals (ARM SoC register map)
            self._get_linux_devicetree()

            # IOMEM region map
            self._get_linux_iomem()

            # Sysfs: platform devices, net, block, thermal, battery
            self._get_linux_sysfs()

            # On ARM or if running on top of Android kernel, also run Android extras
            # This catches Kali-chroot / proot / Termux environments
            if (self.arch in (Arch.ARM64, Arch.ARM)
                    or os.path.exists('/data/data/com.termux')
                    or os.path.exists('/system/build.prop')
                    or os.path.exists('/data/adb')):
                self._init_android_extras()

        except Exception as e:
            import traceback
            traceback.print_exc()

    def _init_android_extras(self):
        """Android/Termux extras — safe to call from Linux init on ARM devices."""
        import re as _re, subprocess as _sp

        # ── build.prop / getprop ──────────────────────────────────────
        props = {}
        for prop_file in ('/system/build.prop', '/vendor/build.prop',
                          '/odm/build.prop', '/product/build.prop'):
            try:
                with open(prop_file, 'r', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            k, _, v = line.partition('=')
                            props[k.strip()] = v.strip()
            except Exception:
                pass

        try:
            r = _sp.run(['getprop'], capture_output=True, text=True, timeout=3)
            for line in r.stdout.splitlines():
                m = _re.match(r'\[(.+?)\]:\s*\[(.+?)\]', line)
                if m:
                    props[m.group(1)] = m.group(2)
        except Exception:
            pass

        # Update CPU identity from Android props if still unknown
        soc_keys = ['ro.hardware', 'ro.soc.model', 'ro.product.board',
                    'ro.chipname', 'ro.board.platform']
        for k in soc_keys:
            if k in props and props[k]:
                self.cpu.soc = props[k]
                if not self.cpu.model or self.cpu.model.lower() in ('unknown', ''):
                    self.cpu.model = props[k]
                break

        brand_keys = ['ro.product.manufacturer', 'ro.product.brand',
                      'ro.product.vendor.manufacturer']
        for k in brand_keys:
            if k in props and props[k]:
                if not self.cpu.vendor or self.cpu.vendor.lower() == 'unknown':
                    self.cpu.vendor = props[k]
                break

        # Android version info
        if 'ro.build.version.release' in props:
            self.peripherals['android_version'] = Peripheral(
                name='android_version', phys_base=0, size=0,
                description=f"Android {props['ro.build.version.release']}"
                            + (f" ({props.get('ro.build.id', '')})" if 'ro.build.id' in props else '')
            )

        # Kernel from /proc/version
        try:
            with open('/proc/version', 'r') as f:
                kver = f.read().strip().split('(')[0].strip()
            self.peripherals['kernel'] = Peripheral(
                name='kernel', phys_base=0, size=0,
                description=f'Kernel: {kver}'
            )
        except Exception:
            pass

        # ── Android HAL devices ────────────────────────────────────────
        ANDROID_DEVS = {
            'ion':       '/dev/ion',
            'kgsl3d':    '/dev/kgsl-3d0',
            'binder':    '/dev/binder',
            'ashmem':    '/dev/ashmem',
            'hw_random': '/dev/hw_random',
            'pmsg':      '/dev/pmsg0',
            'qce':       '/dev/qce',
            'rmnet':     '/dev/rmnet_ctrl',
            'adsprpc':   '/dev/adsprpc-smd',
            'camera':    '/dev/video0',
        }
        for name, devpath in ANDROID_DEVS.items():
            if os.path.exists(devpath) and name not in self.peripherals:
                self.peripherals[name] = Peripheral(
                    name=name, phys_base=0, size=0,
                    description=f'Android HAL: {devpath}'
                )

        # ── Termux-specific: $PREFIX/var/run presence ──────────────────
        termux_home = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
        if os.path.exists(termux_home):
            self.peripherals['termux'] = Peripheral(
                name='termux', phys_base=0, size=0,
                description=f'Termux PREFIX: {termux_home}'
            )

        # ── /proc/iomem (needs root, but try anyway) ───────────────────
        if not any(p.phys_base > 0 for p in self.peripherals.values()):
            self._get_linux_iomem()
    
    def _get_linux_cpu(self):
        """Get CPU info from /proc/cpuinfo — handles both x86 and ARM64 formats."""
        # ── ARM implementer decode table ──────────────────────────────
        ARM_IMPLEMENTER = {
            0x41: 'ARM',  0x42: 'Broadcom', 0x43: 'Cavium',
            0x44: 'DEC',  0x46: 'Fujitsu',  0x48: 'HiSilicon',
            0x49: 'Infineon', 0x4d: 'Motorola', 0x4e: 'NVIDIA',
            0x50: 'APM',  0x51: 'Qualcomm', 0x53: 'Samsung',
            0x56: 'Marvell', 0x61: 'Apple', 0x69: 'Intel',
        }
        ARM_PART = {
            0xd03: 'Cortex-A53',  0xd04: 'Cortex-A35',
            0xd05: 'Cortex-A55',  0xd07: 'Cortex-A57',
            0xd08: 'Cortex-A72',  0xd09: 'Cortex-A73',
            0xd0a: 'Cortex-A75',  0xd0b: 'Cortex-A76',
            0xd0d: 'Cortex-A77',  0xd0e: 'Cortex-A76AE',
            0xd0f: 'AEM-v8',      0xd40: 'Neoverse-V1',
            0xd41: 'Cortex-A78',  0xd44: 'Cortex-X1',
            0xd46: 'Cortex-A510', 0xd47: 'Cortex-A710',
            0xd48: 'Cortex-X2',   0xd4b: 'Cortex-A78C',
            # Qualcomm Kryo/Krait
            0x800: 'Kryo-2xx-Gold', 0x801: 'Kryo-2xx-Silver',
            0x802: 'Kryo-3xx-Gold', 0x803: 'Kryo-3xx-Silver',
            0x804: 'Kryo-4xx-Gold', 0x805: 'Kryo-4xx-Silver',
            # Samsung Mongoose / Exynos
            0x001: 'Exynos-M1',   0x002: 'Exynos-M3',
            0x003: 'Exynos-M4',   0x004: 'Exynos-M5',
        }

        try:
            with open('/proc/cpuinfo', 'r') as f:
                text = f.read()
            lines = text.splitlines()
        except Exception:
            text, lines = '', []

        cores = set()
        arm_implementer = None
        arm_part = None
        hardware_field = None

        for line in lines:
            if ':' not in line:
                continue
            key, _, val = line.partition(':')
            key = key.strip().lower()
            val = val.strip()

            if key == 'processor':
                cores.add(val)
            elif key == 'model name' and val and val.lower() not in ('unknown', ''):
                self.cpu.model = val
            elif key == 'vendor_id' and val:
                self.cpu.vendor = val
            elif key in ('flags', 'features') and not self.cpu.features:
                self.cpu.features = val.split()
            elif key == 'cpu mhz':
                try:
                    self.cpu.frequency_mhz = float(val)
                except Exception:
                    pass
            # ARM-specific fields
            elif key == 'hardware':
                hardware_field = val
            elif key == 'cpu implementer':
                try:
                    arm_implementer = int(val, 16)
                except Exception:
                    pass
            elif key == 'cpu part':
                try:
                    arm_part = int(val, 16)
                except Exception:
                    pass
            elif key == 'cpu variant':
                pass  # could decode stepping later
            elif key == 'cpu architecture':
                pass

        self.cpu.cores = max(len(cores), 1)

        # ── ARM model synthesis ───────────────────────────────────────
        if arm_implementer is not None:
            vendor = ARM_IMPLEMENTER.get(arm_implementer, f'0x{arm_implementer:02x}')
            self.cpu.vendor = vendor
            if arm_part is not None:
                part_name = ARM_PART.get(arm_part, f'0x{arm_part:03x}')
                self.cpu.model = f'{vendor} {part_name}'
            elif not self.cpu.model or self.cpu.model.lower() == 'unknown':
                self.cpu.model = vendor + ' (ARM64)'

        # Hardware field gives SoC name on Android/embedded
        if hardware_field:
            self.cpu.soc = hardware_field

        # ── Frequency from cpufreq (reliable on Android) ─────────────
        if not self.cpu.frequency_mhz:
            for freq_path in (
                '/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq',
                '/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq',
            ):
                try:
                    with open(freq_path, 'r') as f:
                        self.cpu.frequency_mhz = int(f.read().strip()) / 1000.0
                    break
                except Exception:
                    pass

        # ── Core count from sysfs (most reliable) ─────────────────────
        try:
            cpu_path = '/sys/devices/system/cpu'
            if os.path.exists(cpu_path):
                cpu_dirs = [d for d in os.listdir(cpu_path)
                            if re.match(r'^cpu\d+$', d)]
                if cpu_dirs:
                    self.cpu.cores = len(cpu_dirs)
        except Exception:
            pass

        # ── Android: read build.prop for SoC / brand ─────────────────
        for prop_file in ('/system/build.prop', '/vendor/build.prop',
                          '/odm/build.prop', '/product/build.prop'):
            try:
                with open(prop_file, 'r', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('ro.hardware=') and not getattr(self.cpu, 'soc', None):
                            self.cpu.soc = line.split('=', 1)[1]
                        elif line.startswith('ro.product.board=') and (not self.cpu.model or self.cpu.model.lower() == 'unknown'):
                            self.cpu.model = line.split('=', 1)[1]
                        elif line.startswith('ro.chipname=') and not self.cpu.model:
                            self.cpu.model = line.split('=', 1)[1]
                        elif line.startswith('ro.soc.model=') and not self.cpu.model:
                            self.cpu.model = line.split('=', 1)[1]
                        elif line.startswith('ro.product.manufacturer=') and not self.cpu.vendor:
                            self.cpu.vendor = line.split('=', 1)[1]
            except Exception:
                pass

        # ── getprop fallback (Android) ────────────────────────────────
        try:
            r = subprocess.run(['getprop'], capture_output=True, text=True, timeout=2)
            for line in r.stdout.splitlines():
                m = re.match(r'\[(.+?)\]:\s*\[(.+?)\]', line)
                if m:
                    k, v = m.group(1), m.group(2)
                    if k == 'ro.hardware' and not getattr(self.cpu, 'soc', None):
                        self.cpu.soc = v
                    elif k in ('ro.product.board', 'ro.soc.model') and (not self.cpu.model or self.cpu.model.lower() == 'unknown'):
                        self.cpu.model = v
                    elif k == 'ro.product.manufacturer' and not self.cpu.vendor:
                        self.cpu.vendor = v
        except Exception:
            pass

        # ── Cache info from sysfs ─────────────────────────────────────
        for idx in ['index0', 'index1', 'index2', 'index3']:
            cache_path = f'/sys/devices/system/cpu/cpu0/cache/{idx}'
            if os.path.exists(cache_path):
                try:
                    with open(f'{cache_path}/level', 'r') as f:
                        level_num = f.read().strip()
                    with open(f'{cache_path}/size', 'r') as f:
                        size_str = f.read().strip()
                    size_kb = int(re.sub(r'[^0-9]', '', size_str))
                    self.cpu.cache_size[f'L{level_num}'] = size_kb
                except Exception:
                    pass

        # ── kernel cmdline: SoC hints ──────────────────────────────────
        try:
            with open('/proc/cmdline', 'r') as f:
                cmdline = f.read()
            m = re.search(r'androidboot\.hardware=(\S+)', cmdline)
            if m and not getattr(self.cpu, 'soc', None):
                self.cpu.soc = m.group(1)
        except Exception:
            pass
    
    def _get_linux_memory(self):
        """Get memory info from /proc/meminfo"""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemTotal' in line:
                        kb = int(line.split()[1])
                        self.memory.total_bytes = kb * 1024
                    elif 'MemAvailable' in line:
                        kb = int(line.split()[1])
                        self.memory.available_bytes = kb * 1024
                    elif 'MemFree' in line:
                        kb = int(line.split()[1])
                        self.memory.free_bytes = kb * 1024
        except:
            pass
    
    def _get_linux_pci(self):
        """Get PCI devices — tries lspci, then /sys/bus/pci, then /proc/bus/pci."""
        # Method 1: lspci -mm (machine-readable)
        try:
            r = subprocess.run(['lspci', '-mm'], capture_output=True, text=True, timeout=3)
            for line in r.stdout.splitlines():
                parts = line.split('"')
                # Format: "slot" "class" "vendor" "device" ...
                if len(parts) >= 8:
                    slot = parts[0].strip()
                    vendor_name = parts[4]
                    device_name = parts[6]
                    # get numeric IDs
                    r2 = subprocess.run(['lspci', '-n', '-s', slot],
                                        capture_output=True, text=True, timeout=2)
                    m = re.search(r'([0-9a-f]{4}):([0-9a-f]{4})', r2.stdout, re.I)
                    if m:
                        vid, did = int(m.group(1), 16), int(m.group(2), 16)
                        bus_parts = slot.split(':')
                        bus = int(bus_parts[0], 16) if bus_parts else 0
                        self.pci_devices.append(PCIeDevice(
                            bus=bus, device=0, func=0,
                            vendor_id=vid, device_id=did, class_code=0,
                            description=f'{vendor_name} {device_name}'.strip()
                        ))
            if self.pci_devices:
                return
        except Exception:
            pass

        # Method 2: lspci -n (numeric)
        try:
            r = subprocess.run(['lspci', '-n'], capture_output=True, text=True, timeout=3)
            for line in r.stdout.splitlines():
                # 00:00.0 0600: 8086:1234 (rev 01)
                m = re.match(r'([0-9a-f:\.]+)\s+([0-9a-f]+):\s+([0-9a-f]{4}):([0-9a-f]{4})', line, re.I)
                if m:
                    slot, cls, vid, did = m.groups()
                    bus_str = slot.split(':')[0] if ':' in slot else '0'
                    self.pci_devices.append(PCIeDevice(
                        bus=int(bus_str, 16), device=0, func=0,
                        vendor_id=int(vid, 16), device_id=int(did, 16),
                        class_code=int(cls, 16)
                    ))
            if self.pci_devices:
                return
        except Exception:
            pass

        # Method 3: /sys/bus/pci/devices (no lspci needed)
        try:
            pci_sysfs = '/sys/bus/pci/devices'
            if os.path.exists(pci_sysfs):
                for dev_dir in os.listdir(pci_sysfs):
                    dev_path = os.path.join(pci_sysfs, dev_dir)
                    try:
                        def _rdhex(name):
                            with open(os.path.join(dev_path, name)) as fh:
                                return int(fh.read().strip(), 16)
                        vid = _rdhex('vendor')
                        did = _rdhex('device')
                        cls = _rdhex('class') >> 8
                        # slot: 0000:00:00.0
                        parts = dev_dir.split(':')
                        bus = int(parts[1], 16) if len(parts) >= 3 else 0
                        self.pci_devices.append(PCIeDevice(
                            bus=bus, device=0, func=0,
                            vendor_id=vid, device_id=did, class_code=cls
                        ))
                    except Exception:
                        pass
            if self.pci_devices:
                return
        except Exception:
            pass

        # Method 4: /proc/bus/pci/devices
        try:
            with open('/proc/bus/pci/devices', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        bdf = int(parts[0], 16)
                        vd = int(parts[1], 16)
                        bus = (bdf >> 8) & 0xFF
                        dev = (bdf >> 3) & 0x1F
                        func = bdf & 0x7
                        vendor = (vd >> 16) & 0xFFFF
                        device = vd & 0xFFFF
                        self.pci_devices.append(PCIeDevice(
                            bus=bus, device=dev, func=func,
                            vendor_id=vendor, device_id=device, class_code=0
                        ))
        except Exception:
            pass

    def _get_linux_usb(self):
        """Get USB devices — tries lsusb, then /sys/bus/usb/devices."""
        # Method 1: lsusb
        try:
            r = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=3)
            for line in r.stdout.splitlines():
                m = re.search(r'Bus (\d+) Device (\d+): ID ([0-9a-f]+):([0-9a-f]+)\s*(.*)', line, re.I)
                if m:
                    bus, addr, vid, pid, desc = m.groups()
                    self.usb_devices.append(USBDevice(
                        bus=int(bus), address=int(addr),
                        vendor_id=int(vid, 16), product_id=int(pid, 16),
                        class_code=0, description=desc.strip()
                    ))
            if self.usb_devices:
                return
        except Exception:
            pass

        # Method 2: /sys/bus/usb/devices
        try:
            usb_path = '/sys/bus/usb/devices'
            if os.path.exists(usb_path):
                for dev in os.listdir(usb_path):
                    # Only enumerate real devices (not hubs/ports)
                    if ':' in dev:
                        continue
                    dev_path = os.path.join(usb_path, dev)
                    try:
                        def _rd(name):
                            with open(os.path.join(dev_path, name)) as fh:
                                return fh.read().strip()
                        bus = int(_rd('busnum'))
                        addr = int(_rd('devnum'))
                        vid = int(_rd('idVendor'), 16)
                        pid = int(_rd('idProduct'), 16)
                        try:
                            desc = _rd('product')
                        except Exception:
                            desc = _rd('manufacturer') if os.path.exists(
                                os.path.join(dev_path, 'manufacturer')) else ''
                        cls_str = _rd('bDeviceClass')
                        self.usb_devices.append(USBDevice(
                            bus=bus, address=addr,
                            vendor_id=vid, product_id=pid,
                            class_code=int(cls_str, 16),
                            description=desc
                        ))
                    except Exception:
                        pass
        except Exception:
            pass

    def _get_linux_devicetree(self):
        """Parse /proc/device-tree — handles both 32-bit and 64-bit cell sizes."""
        dt_path = '/proc/device-tree'
        if not os.path.exists(dt_path):
            return

        def read_cells(data, num_cells):
            """Read big-endian cell values (4 bytes each)."""
            cell_size = 4 * num_cells
            if len(data) < cell_size:
                return None
            value = 0
            for i in range(num_cells):
                value = (value << 32) | struct.unpack('>I', data[i*4:(i+1)*4])[0]
            return value

        def get_node_cells(path):
            """Get #address-cells and #size-cells for a node."""
            addr_cells = 1
            size_cells = 1
            try:
                ac_path = os.path.join(path, '#address-cells')
                if os.path.exists(ac_path):
                    with open(ac_path, 'rb') as f:
                        d = f.read()
                    if len(d) >= 4:
                        addr_cells = struct.unpack('>I', d[:4])[0]
            except Exception:
                pass
            try:
                sc_path = os.path.join(path, '#size-cells')
                if os.path.exists(sc_path):
                    with open(sc_path, 'rb') as f:
                        d = f.read()
                    if len(d) >= 4:
                        size_cells = struct.unpack('>I', d[:4])[0]
            except Exception:
                pass
            return addr_cells, size_cells

        def get_compatible(node_path):
            compat_path = os.path.join(node_path, 'compatible')
            if os.path.exists(compat_path):
                try:
                    with open(compat_path, 'rb') as f:
                        return f.read().decode('utf-8', errors='ignore').replace('', ', ').strip(', ')
                except Exception:
                    pass
            return ''

        def scan_dt_dir(path, parent_addr_cells=1, parent_size_cells=1, depth=0):
            if depth > 6:
                return
            try:
                ac, sc = get_node_cells(path)
            except Exception:
                ac, sc = parent_addr_cells, parent_size_cells

            try:
                items = os.listdir(path)
            except Exception:
                return

            for item in items:
                if item.startswith('.') or item in ('#address-cells', '#size-cells',
                                                     'compatible', 'reg', 'ranges',
                                                     'name', 'model', 'status'):
                    continue
                item_path = os.path.join(path, item)
                if not os.path.isdir(item_path):
                    continue

                reg_path = os.path.join(item_path, 'reg')
                compat = get_compatible(item_path)

                if os.path.exists(reg_path):
                    try:
                        with open(reg_path, 'rb') as f:
                            reg_data = f.read()

                        cell_size = (ac + sc) * 4
                        if len(reg_data) >= cell_size:
                            addr = read_cells(reg_data, ac)
                            size = read_cells(reg_data[ac*4:], sc) if sc > 0 else 0x1000
                            if addr is not None and addr > 0:
                                # Build a clean name from the node
                                name = item.split('@')[0].replace('-', '_').replace(',', '_')
                                if '@' in item:
                                    addr_suffix = item.split('@')[1][:8]
                                    full_name = f"{name}_{addr_suffix}"
                                else:
                                    full_name = name

                                self.peripherals[full_name] = Peripheral(
                                    name=full_name,
                                    phys_base=addr,
                                    size=size if size else 0x1000,
                                    description=compat or item
                                )
                    except Exception:
                        pass

                scan_dt_dir(item_path, ac, sc, depth + 1)

        # Read root address/size cells
        root_ac, root_sc = get_node_cells(dt_path)
        scan_dt_dir(dt_path, root_ac, root_sc)

    def _get_linux_iomem(self):
        """Parse /proc/iomem — comprehensive peripheral discovery."""
        KNOWN_PERIPHERALS = {
            'uart': 'serial', 'serial': 'serial', 'pl011': 'serial',
            'timer': 'timer', 'gic': 'interrupt-controller',
            'gpio': 'gpio', 'i2c': 'i2c', 'spi': 'spi',
            'usb': 'usb', 'pcie': 'pci', 'pci': 'pci',
            'emmc': 'storage', 'sdhci': 'storage', 'sdmmc': 'storage',
            'ethernet': 'net', 'eth': 'net',
            'gpu': 'gpu', 'display': 'display', 'hdmi': 'display', 'dsi': 'display',
            'dma': 'dma', 'watchdog': 'watchdog', 'wdt': 'watchdog',
            'rtc': 'rtc', 'pwm': 'pwm', 'adc': 'adc', 'dac': 'dac',
            'crypto': 'crypto', 'rng': 'rng', 'efuse': 'efuse',
            'pmic': 'power', 'clk': 'clock', 'ccu': 'clock',
        }
        try:
            with open('/proc/iomem', 'r') as f:
                for line in f:
                    # Only top-level (no leading spaces beyond indent) or all
                    parts = line.strip().split(' : ', 1)
                    if len(parts) < 2:
                        continue
                    range_part = parts[0].strip()
                    desc = parts[1].strip()

                    if '-' not in range_part:
                        continue
                    try:
                        start_str, end_str = range_part.split('-', 1)
                        start = int(start_str.strip(), 16)
                        end = int(end_str.strip(), 16)
                        size = end - start + 1
                    except Exception:
                        continue

                    if start == 0 or size == 0:
                        continue

                    # Build clean name from description
                    desc_lower = desc.lower()
                    # Try node-name after last dot: "fe201000.serial" -> "serial"
                    m = re.search(r'[0-9a-f]+\.([a-zA-Z0-9_]+)', desc)
                    if m:
                        name = m.group(1)
                    else:
                        # Use first word
                        name = re.sub(r'[^a-zA-Z0-9_]', '_', desc.split()[0]) if desc else f'mmio_{start:x}'

                    # Avoid duplicates by appending address suffix
                    base_name = name
                    suffix = f'_{start:x}'
                    final_name = base_name if base_name not in self.peripherals else base_name + suffix

                    # Tag known peripheral types
                    ptype = 'unknown'
                    for kw, pt in KNOWN_PERIPHERALS.items():
                        if kw in desc_lower or kw in name.lower():
                            ptype = pt
                            break

                    self.peripherals[final_name] = Peripheral(
                        name=final_name,
                        phys_base=start,
                        size=size,
                        description=f'{desc} [{ptype}]'
                    )
        except Exception:
            pass

    def _get_linux_sysfs(self):
        """Discover platform devices, net, block, thermal, battery from sysfs."""
        # ── Platform MMIO devices ─────────────────────────────────────
        platform_path = '/sys/bus/platform/devices'
        if os.path.exists(platform_path):
            for device in os.listdir(platform_path):
                dev_path = os.path.join(platform_path, device)
                resource_path = os.path.join(dev_path, 'resource')
                if os.path.exists(resource_path):
                    try:
                        with open(resource_path, 'r') as f:
                            lines = f.readlines()
                        # First non-zero resource line is MMIO base
                        for rline in lines:
                            parts = rline.strip().split()
                            if len(parts) >= 2:
                                start = int(parts[0], 16)
                                end_r = int(parts[1], 16)
                                if start and start != end_r:
                                    name = device.split('.')[0].replace('-', '_')
                                    if name not in self.peripherals:
                                        self.peripherals[name] = Peripheral(
                                            name=name,
                                            phys_base=start,
                                            size=end_r - start + 1,
                                            description=f'Platform: {device}'
                                        )
                                    break
                    except Exception:
                        pass

        # ── Network interfaces ─────────────────────────────────────────
        net_path = '/sys/class/net'
        if os.path.exists(net_path):
            for iface in os.listdir(net_path):
                iface_path = os.path.join(net_path, iface)
                try:
                    # Read MAC and speed
                    mac = ''
                    speed = ''
                    try:
                        with open(os.path.join(iface_path, 'address')) as f:
                            mac = f.read().strip()
                    except Exception:
                        pass
                    try:
                        with open(os.path.join(iface_path, 'speed')) as f:
                            speed = f.read().strip() + ' Mbps'
                    except Exception:
                        pass
                    desc = f'Net: {iface}'
                    if mac:
                        desc += f' MAC={mac}'
                    if speed and speed != '-1 Mbps':
                        desc += f' Speed={speed}'
                    key = f'net_{iface}'
                    self.peripherals[key] = Peripheral(
                        name=key, phys_base=0, size=0, description=desc
                    )
                except Exception:
                    pass

        # ── Block devices ─────────────────────────────────────────────
        block_path = '/sys/class/block'
        if os.path.exists(block_path):
            for blk in os.listdir(block_path):
                # Only physical disks (no partitions)
                if re.search(r'\d$', blk):
                    continue
                blk_path = os.path.join(block_path, blk)
                try:
                    size_bytes = 0
                    model_str = ''
                    try:
                        with open(os.path.join(blk_path, 'size')) as f:
                            sectors = int(f.read().strip())
                        size_bytes = sectors * 512
                    except Exception:
                        pass
                    for mf in (os.path.join(blk_path, 'device', 'model'),
                                os.path.join(blk_path, 'device', 'name')):
                        try:
                            with open(mf) as f:
                                model_str = f.read().strip()
                            break
                        except Exception:
                            pass
                    sz_gb = size_bytes / (1024**3)
                    desc = f'Block: {blk}'
                    if model_str:
                        desc += f' ({model_str})'
                    if size_bytes:
                        desc += f' {sz_gb:.1f}GB'
                    key = f'blk_{blk}'
                    self.peripherals[key] = Peripheral(
                        name=key, phys_base=0, size=size_bytes, description=desc
                    )
                except Exception:
                    pass

        # ── Thermal zones ─────────────────────────────────────────────
        thermal_path = '/sys/class/thermal'
        if os.path.exists(thermal_path):
            for zone in sorted(os.listdir(thermal_path)):
                if not zone.startswith('thermal_zone'):
                    continue
                zone_path = os.path.join(thermal_path, zone)
                try:
                    temp = 0
                    ztype = ''
                    try:
                        with open(os.path.join(zone_path, 'temp')) as f:
                            temp = int(f.read().strip()) / 1000.0
                    except Exception:
                        pass
                    try:
                        with open(os.path.join(zone_path, 'type')) as f:
                            ztype = f.read().strip()
                    except Exception:
                        pass
                    key = f'thermal_{zone[-1]}'
                    self.peripherals[key] = Peripheral(
                        name=key, phys_base=0, size=0,
                        description=f'Thermal: {ztype} {temp:.1f}°C'
                    )
                except Exception:
                    pass

        # ── Battery / power supply ────────────────────────────────────
        power_path = '/sys/class/power_supply'
        if os.path.exists(power_path):
            for ps in os.listdir(power_path):
                ps_path = os.path.join(power_path, ps)
                try:
                    info = {}
                    for attr in ('capacity', 'status', 'technology',
                                 'voltage_now', 'current_now', 'temp'):
                        try:
                            with open(os.path.join(ps_path, attr)) as f:
                                info[attr] = f.read().strip()
                        except Exception:
                            pass
                    parts = [f'{ps}']
                    if 'status' in info:
                        parts.append(info['status'])
                    if 'capacity' in info:
                        parts.append(f"{info['capacity']}%")
                    if 'voltage_now' in info:
                        v = int(info['voltage_now']) / 1_000_000
                        parts.append(f'{v:.2f}V')
                    if 'temp' in info:
                        t = int(info['temp']) / 10.0
                        parts.append(f'{t:.1f}°C')
                    key = f'psu_{ps}'
                    self.peripherals[key] = Peripheral(
                        name=key, phys_base=0, size=0,
                        description='Power: ' + ' '.join(parts)
                    )
                except Exception:
                    pass

        # ── GPU / DRM devices ─────────────────────────────────────────
        drm_path = '/sys/class/drm'
        if os.path.exists(drm_path):
            for drm_dev in os.listdir(drm_path):
                if not drm_dev.startswith('card'):
                    continue
                drm_p = os.path.join(drm_path, drm_dev)
                try:
                    vendor = ''
                    device_name = ''
                    for vf in (os.path.join(drm_p, 'device', 'vendor'),):
                        try:
                            with open(vf) as f:
                                vendor = f.read().strip()
                        except Exception:
                            pass
                    key = f'gpu_{drm_dev}'
                    self.peripherals[key] = Peripheral(
                        name=key, phys_base=0, size=0,
                        description=f'GPU: {drm_dev} vendor={vendor}'
                    )
                except Exception:
                    pass

    def _init_android(self):
        """Android/Termux/Kali-on-Android: full Linux init + Android extras."""
        self._init_linux()

        # ── build.prop / getprop for SoC identity ─────────────────────
        props = {}
        for prop_file in ('/system/build.prop', '/vendor/build.prop',
                          '/odm/build.prop', '/product/build.prop'):
            try:
                with open(prop_file, 'r', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            k, _, v = line.partition('=')
                            props[k.strip()] = v.strip()
            except Exception:
                pass

        # getprop is more reliable on live Android
        try:
            r = subprocess.run(['getprop'], capture_output=True, text=True, timeout=3)
            for line in r.stdout.splitlines():
                m = re.match(r'\[(.+?)\]:\s*\[(.+?)\]', line)
                if m:
                    props[m.group(1)] = m.group(2)
        except Exception:
            pass

        soc_keys = ['ro.hardware', 'ro.soc.model', 'ro.product.board',
                    'ro.chipname', 'ro.board.platform']
        for k in soc_keys:
            if k in props and props[k]:
                self.cpu.soc = props[k]
                if not self.cpu.model or self.cpu.model.lower() in ('unknown', ''):
                    self.cpu.model = props[k]
                break

        if not self.cpu.vendor or self.cpu.vendor.lower() == 'unknown':
            for k in ('ro.product.manufacturer', 'ro.product.brand'):
                if k in props:
                    self.cpu.vendor = props[k]
                    break

        # ── Android HAL peripherals from /dev + sysfs ─────────────────
        ANDROID_DEVS = {
            'ion': '/dev/ion',
            'kgsl3d': '/dev/kgsl-3d0',
            'binder': '/dev/binder',
            'ashmem': '/dev/ashmem',
            'pmsg': '/dev/pmsg0',
            'qce': '/dev/qce',         # Qualcomm crypto engine
            'rmnet': '/dev/rmnet_ctrl',
            'adsprpc': '/dev/adsprpc-smd',
            'camera': '/dev/video0',
        }
        for name, devpath in ANDROID_DEVS.items():
            if os.path.exists(devpath):
                if name not in self.peripherals:
                    self.peripherals[name] = Peripheral(
                        name=name, phys_base=0, size=0,
                        description=f'Android HAL: {devpath}'
                    )

        # ── Qualcomm RPM / SMEM ────────────────────────────────────────
        for smem_path in ('/sys/devices/qcom,msm-imem',
                          '/sys/bus/platform/devices/qcom,smem',
                          '/sys/bus/platform/devices/rpm_requests'):
            if os.path.exists(smem_path):
                name = os.path.basename(smem_path).replace(',', '_')
                self.peripherals[name] = Peripheral(
                    name=name, phys_base=0, size=0,
                    description=f'Qualcomm subsystem: {smem_path}'
                )

        # ── /sys/class/camera (if camera HAL exposed) ─────────────────
        cam_path = '/sys/class/camera'
        if os.path.exists(cam_path):
            for cam in os.listdir(cam_path):
                key = f'camera_{cam}'
                self.peripherals[key] = Peripheral(
                    name=key, phys_base=0, size=0,
                    description=f'Camera: {cam}'
                )

    def _init_bsd(self):
        """BSD-specific initialization"""
        try:
            # CPU info via sysctl
            import subprocess
            
            result = subprocess.run(['sysctl', '-n', 'hw.ncpu'],
                                   capture_output=True, text=True)
            self.cpu.cores = int(result.stdout.strip())
            
            result = subprocess.run(['sysctl', '-n', 'hw.model'],
                                   capture_output=True, text=True)
            self.cpu.model = result.stdout.strip()
            
            result = subprocess.run(['sysctl', '-n', 'hw.physmem'],
                                   capture_output=True, text=True)
            self.memory.total_bytes = int(result.stdout.strip())
            
        except:
            pass
    
    def find_peripheral(self, name: str) -> Optional[int]:
        """
        Find physical base address of a peripheral by name.
        
        Args:
            name: Peripheral name (e.g., 'uart', 'gpio', 'i2c')
        
        Returns:
            Physical address or None if not found
        """
        name_lower = name.lower()
        
        # Direct match
        if name_lower in self.peripherals:
            return self.peripherals[name_lower].phys_base
        
        # Partial match
        for p_name, periph in self.peripherals.items():
            if name_lower in p_name or name_lower in periph.description.lower():
                return periph.phys_base
        
        # Try platform-specific paths
        if self.os == OS.LINUX:
            # Try /proc/iomem scan
            addr = self._scan_iomem(name_lower)
            if addr:
                return addr
            
            # Try device tree
            addr = self._scan_devicetree(name_lower)
            if addr:
                return addr
        
        elif self.os == OS.MACOS:
            # Try IOKit
            addr = self._scan_iokit(name_lower)
            if addr:
                return addr
        
        elif self.os == OS.WINDOWS:
            # Try registry/ACPI
            addr = self._scan_acpi(name_lower)
            if addr:
                return addr
        
        return None
    
    def _scan_iomem(self, name: str) -> Optional[int]:
        """Scan /proc/iomem for peripheral"""
        try:
            with open('/proc/iomem', 'r') as f:
                for line in f:
                    if name in line.lower():
                        parts = line.split(':')
                        if '-' in parts[0]:
                            start = parts[0].split('-')[0].strip()
                            return int(start, 16)
        except:
            pass
        return None
    
    def _scan_devicetree(self, name: str) -> Optional[int]:
        """Scan device tree for peripheral"""
        dt_path = '/proc/device-tree'
        if not os.path.exists(dt_path):
            return None
        
        found_addr = None
        
        def search_dt(path):
            nonlocal found_addr
            try:
                for item in os.listdir(path):
                    if found_addr:
                        return
                    
                    item_path = os.path.join(path, item)
                    
                    # Check if name matches
                    if name in item.lower():
                        reg_path = os.path.join(item_path, 'reg')
                        if os.path.exists(reg_path):
                            with open(reg_path, 'rb') as f:
                                reg_data = f.read()
                                if len(reg_data) >= 8:
                                    found_addr = int.from_bytes(reg_data[:8], 'big')
                                    return
                    
                    # Recurse
                    if os.path.isdir(item_path):
                        search_dt(item_path)
            except:
                pass
        
        search_dt(dt_path)
        return found_addr
    
    def _scan_iokit(self, name: str) -> Optional[int]:
        """Scan IOKit for peripheral on macOS"""
        try:
            import subprocess
            result = subprocess.run(['ioreg', '-r', '-c', 'IOPlatformDevice'],
                                   capture_output=True, text=True)
            
            in_device = False
            for line in result.stdout.split('\n'):
                if name in line.lower():
                    in_device = True
                elif in_device and '"reg"' in line:
                    match = re.search(r'= <([0-9a-f]+)>', line.lower())
                    if match:
                        reg_hex = match.group(1)
                        if len(reg_hex) >= 16:
                            return int(reg_hex[:16], 16)
                    in_device = False
        except:
            pass
        return None
    
    def _scan_acpi(self, name: str) -> Optional[int]:
        """Scan ACPI for peripheral on Windows"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\RESOURCEMAP\System Resources\Physical Memory")
            
            i = 0
            while True:
                try:
                    val_name, val_data, val_type = winreg.EnumValue(key, i)
                    if name.lower() in val_name.lower():
                        # Parse memory range
                        if isinstance(val_data, bytes) and len(val_data) >= 16:
                            start = int.from_bytes(val_data[:8], 'little')
                            return start
                    i += 1
                except WindowsError:
                    break
            winreg.CloseKey(key)
        except:
            pass
        return None
    
    def get_report(self) -> str:
        """Full hardware discovery report with all available data."""
        BOLD = lambda s: s   # terminal formatting handled by caller
        lines = []
        SEP = '=' * 64

        lines += [SEP, '[HARDWARE] Full System Report', SEP]

        # ── Platform ───────────────────────────────────────────────────
        lines.append(f'  OS            : {self.os.value}')
        lines.append(f'  Architecture  : {self.arch.value}')
        ring0_status = '✓ (elevated / root)' if self._has_ring0 else '✗ (userland - run as root for full access)'
        lines.append(f'  Ring-0 Access : {ring0_status}')

        # Kernel info
        try:
            uname = os.uname()
            lines.append(f'  Kernel        : {uname.release}')
            lines.append(f'  Hostname      : {uname.nodename}')
        except Exception:
            pass

        # ── CPU ────────────────────────────────────────────────────────
        lines += ['', '  ── CPU ──────────────────────────────────────────────']
        lines.append(f'  Model         : {self.cpu.model or "Unknown"}')
        lines.append(f'  Vendor        : {self.cpu.vendor or "Unknown"}')
        soc = getattr(self.cpu, "soc", None)
        if soc:
            lines.append(f'  SoC           : {soc}')
        lines.append(f'  Cores         : {self.cpu.cores}')
        if self.cpu.frequency_mhz:
            lines.append(f'  Frequency     : {self.cpu.frequency_mhz:.0f} MHz ({self.cpu.frequency_mhz/1000:.2f} GHz)')

        if self.cpu.cache_size:
            cache_str = '  '.join(f'{k}={v}KB' for k, v in sorted(self.cpu.cache_size.items()))
            lines.append(f'  Cache         : {cache_str}')

        if self.cpu.features:
            feat_count = len(self.cpu.features)
            # Group notable features
            notable = [f for f in self.cpu.features if f in (
                'aes', 'sha1', 'sha2', 'sha512', 'crc32', 'crypto', 'fp', 'asimd',
                'sve', 'sve2', 'lse', 'atomics', 'rdm', 'dotprod', 'i8mm', 'bf16',
                'avx', 'avx2', 'avx512f', 'sse4_2', 'aes', 'pclmulqdq', 'neon',
                'vfpv4', 'vfpv3', 'half', 'fastmult', 'edsp',
            )]
            lines.append(f'  CPU Features  : {feat_count} total')
            if notable:
                lines.append(f'  Notable       : {" ".join(notable)}')
            # Print all features in wrapped lines
            feat_line = '  All Features  : '
            feat_str = ' '.join(self.cpu.features)
            # Wrap at 80 chars
            words = self.cpu.features
            cur_line = feat_line
            for w in words:
                if len(cur_line) + len(w) + 1 > 80:
                    lines.append(cur_line)
                    cur_line = '                  ' + w
                else:
                    cur_line += w + ' '
            if cur_line.strip():
                lines.append(cur_line)

        # ── Memory ────────────────────────────────────────────────────
        lines += ['', '  ── Memory ───────────────────────────────────────────']
        total_gb = self.memory.total_bytes / (1024**3)
        lines.append(f'  Total         : {total_gb:.2f} GB ({self.memory.total_bytes:,} bytes)')
        if self.memory.available_bytes:
            avail_mb = self.memory.available_bytes / (1024**2)
            used_mb = (self.memory.total_bytes - self.memory.available_bytes) / (1024**2)
            pct = (1 - self.memory.available_bytes / self.memory.total_bytes) * 100
            lines.append(f'  Available     : {avail_mb:.0f} MB')
            lines.append(f'  Used          : {used_mb:.0f} MB ({pct:.1f}%)')

        # Hugepage / swap info
        try:
            with open('/proc/meminfo', 'r') as f:
                minfo = {l.split(':')[0].strip(): l.split(':')[1].strip()
                         for l in f if ':' in l}
            if 'SwapTotal' in minfo:
                swap_kb = int(minfo['SwapTotal'].split()[0])
                swap_free_kb = int(minfo.get('SwapFree', '0 kB').split()[0])
                lines.append(f'  Swap          : {swap_kb//1024} MB total, {swap_free_kb//1024} MB free')
            if 'HugePages_Total' in minfo:
                hp_total = minfo['HugePages_Total'].strip()
                hp_size = minfo.get('Hugepagesize', 'unknown')
                lines.append(f'  HugePages     : {hp_total} x {hp_size}')
        except Exception:
            pass

        # ── PCI ───────────────────────────────────────────────────────
        lines += ['', f'  ── PCI Devices : {len(self.pci_devices)} ────────────────────────────']
        if self.pci_devices:
            PCI_CLASS = {
                0x0000: 'Unclassified',  0x0100: 'SCSI',   0x0101: 'IDE',
                0x0200: 'Ethernet',      0x0280: 'WiFi',   0x0300: 'VGA',
                0x0301: 'XGA',           0x0302: '3D/GPU', 0x0400: 'Multimedia',
                0x0600: 'Host Bridge',   0x0601: 'ISA Bridge', 0x0604: 'PCIe Bridge',
                0x0680: 'Bridge',        0x0700: 'Serial',  0x0c03: 'USB',
                0x0c04: 'Fibre Ch',      0x0c05: 'SMBus',  0x1000: 'Crypto',
            }
            for i, dev in enumerate(self.pci_devices[:16]):
                cls_name = PCI_CLASS.get(dev.class_code & 0xFFFF,
                           PCI_CLASS.get(dev.class_code & 0xFF00, f'Class {dev.class_code:04x}'))
                desc = getattr(dev, 'description', '') or ''
                lines.append(f'  [{i+1:2d}] {dev.vendor_id:04x}:{dev.device_id:04x}'
                             f'  bus={dev.bus:02x}:{dev.device:02x}.{dev.func}'
                             f'  {cls_name}'
                             + (f'  — {desc}' if desc else ''))
            if len(self.pci_devices) > 16:
                lines.append(f'  ... and {len(self.pci_devices)-16} more')

        # ── USB ───────────────────────────────────────────────────────
        lines += ['', f'  ── USB Devices : {len(self.usb_devices)} ────────────────────────────']
        if self.usb_devices:
            USB_CLASS = {0x01: 'Audio', 0x02: 'CDC', 0x03: 'HID', 0x05: 'Physical',
                         0x06: 'Image', 0x07: 'Printer', 0x08: 'Mass Storage',
                         0x09: 'Hub', 0x0a: 'CDC-Data', 0x0b: 'Smart Card',
                         0x0e: 'Video', 0x0f: 'Personal Health', 0xe0: 'Wireless',
                         0xfe: 'App-Specific', 0xff: 'Vendor-Specific'}
            for i, dev in enumerate(self.usb_devices[:12]):
                cls_name = USB_CLASS.get(dev.class_code, f'0x{dev.class_code:02x}')
                desc = getattr(dev, 'description', '') or ''
                lines.append(f'  [{i+1:2d}] {dev.vendor_id:04x}:{dev.product_id:04x}'
                             f'  bus={dev.bus:03d} addr={dev.address:03d}'
                             f'  {cls_name}'
                             + (f'  — {desc}' if desc else ''))
            if len(self.usb_devices) > 12:
                lines.append(f'  ... and {len(self.usb_devices)-12} more')

        # ── Peripherals ───────────────────────────────────────────────
        mmio_periph = {k: v for k, v in self.peripherals.items() if v.phys_base > 0}
        soft_periph = {k: v for k, v in self.peripherals.items() if v.phys_base == 0}

        lines += ['', f'  ── MMIO Peripherals : {len(mmio_periph)} ─────────────────────────']
        if mmio_periph:
            lines.append(f'  {"Name":<24} {"Base Address":>18} {"Size":>12}  Description')
            lines.append('  ' + '-' * 72)
            for name, p in sorted(mmio_periph.items(), key=lambda x: x[1].phys_base)[:30]:
                desc = p.description[:36] if p.description else ''
                lines.append(f'  {name:<24} {p.phys_base:#018x} {p.size:#12x}  {desc}')
            if len(mmio_periph) > 30:
                lines.append(f'  ... and {len(mmio_periph)-30} more MMIO regions')
        else:
            lines.append('  (none found — try running as root for /proc/iomem + device-tree access)')

        if soft_periph:
            lines += ['', f'  ── System Devices : {len(soft_periph)} ──────────────────────────']
            for name, p in sorted(soft_periph.items())[:20]:
                lines.append(f'  {name:<28} {p.description}')
            if len(soft_periph) > 20:
                lines.append(f'  ... and {len(soft_periph)-20} more')

        lines += ['', SEP]
        lines.append('  find_peripheral(name) → physical base address')
        lines.append('  ARM64MMIO.mmio_read(base + offset, size) → register value')
        if not self._has_ring0:
            lines.append('  ⚠  Run as root (sudo) for full /proc/iomem, device-tree and /dev/mem access')
        lines.append(SEP)

        return '\n'.join(lines)


# Module exports
__all__ = [
    'HardwareDiscovery',
    'OS',
    'Arch',
    'CPUInfo',
    'MemoryInfo',
    'PCIeDevice',
    'USBDevice',
    'Peripheral',
]


if __name__ == "__main__":
    hw = HardwareDiscovery()
    print(hw.get_report())
    
    # Example: find UART
    uart = hw.find_peripheral('uart')
    if uart:
        print(f"\nUART found at: {hex(uart)}")


# ============================================================================
# RING-0 PHYSICAL HARDWARE ACCESS METHODS
# Patches HardwareDiscovery with real physical memory / port I/O access.
# ============================================================================

def _hw_read_phys(self, phys_addr: int, length: int) -> bytes:
    """Read physical memory via /dev/mem (requires CAP_SYS_RAWIO)."""
    if not _RING0_INTRINSICS or phys_mem is None:
        raise PermissionError("ks_ring0_bridge not available")
    return phys_mem.read_phys(phys_addr, length)

def _hw_read_phys_u64(self, phys_addr: int) -> int:
    return struct.unpack_from("<Q", self.read_phys(phys_addr, 8))[0]

def _hw_read_phys_u32(self, phys_addr: int) -> int:
    return struct.unpack_from("<I", self.read_phys(phys_addr, 4))[0]

def _hw_read_msr(self, msr_num: int, cpu: int = 0) -> int:
    """Read x86-64 MSR via /dev/cpu/N/msr."""
    if not _RING0_INTRINSICS or msr is None:
        raise PermissionError("MSR access requires ks_ring0_bridge + root")
    from kernel_bridge import MSRAccess
    m = MSRAccess(cpu)
    return m.read(msr_num)

def _hw_write_msr(self, msr_num: int, value: int, cpu: int = 0):
    """Write x86-64 MSR via /dev/cpu/N/msr."""
    if not _RING0_INTRINSICS or msr is None:
        raise PermissionError("MSR access requires ks_ring0_bridge + root")
    from kernel_bridge import MSRAccess
    m = MSRAccess(cpu)
    m.write(msr_num, value)

def _hw_inb(self, port: int) -> int:
    """Read byte from x86 I/O port (requires root)."""
    if not _RING0_INTRINSICS or port_io is None:
        raise PermissionError("Port I/O requires ks_ring0_bridge + root + x86-64")
    return port_io.inb(port)

def _hw_outb(self, port: int, value: int):
    """Write byte to x86 I/O port (requires root)."""
    if not _RING0_INTRINSICS or port_io is None:
        raise PermissionError("Port I/O requires ks_ring0_bridge + root + x86-64")
    port_io.outb(port, value)

def _hw_get_ring0_caps(self) -> str:
    """Return a capability report from kernel_bridge."""
    if _RING0_INTRINSICS:
        from kernel_bridge import capability_report
        return capability_report()
    return "ks_ring0_bridge not available"

def _hw_get_iomem(self) -> dict:
    """Return parsed /proc/iomem as {region: phys_addr}."""
    return read_iomem()

def _hw_get_ioports(self) -> dict:
    """Return parsed /proc/ioports as {region: port}."""
    return read_ioports()

# Patch methods onto HardwareDiscovery
HardwareDiscovery.read_phys     = _hw_read_phys
HardwareDiscovery.read_phys_u64 = _hw_read_phys_u64
HardwareDiscovery.read_phys_u32 = _hw_read_phys_u32
HardwareDiscovery.read_msr      = _hw_read_msr
HardwareDiscovery.write_msr     = _hw_write_msr
HardwareDiscovery.inb           = _hw_inb
HardwareDiscovery.outb          = _hw_outb
HardwareDiscovery.get_ring0_caps = _hw_get_ring0_caps
HardwareDiscovery.get_iomem     = _hw_get_iomem
HardwareDiscovery.get_ioports   = _hw_get_ioports

# Module exports
__all__ = [
    'HardwareIntrinsics',
    'HardwareDiscovery',
    'CPUInfo',
    'MemoryInfo',
    'PCIeDevice',
    'USBDevice',
    'Peripheral',
    'OS',
    'Arch',
]

# Wrapper for compatibility
HardwareIntrinsics = HardwareDiscovery
