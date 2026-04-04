"""
KentScript v3.1.0 - Unified Modular Package
[KS-REF-000] Production systems programming language toolkit
All 888+ classes organized with JIT, syscalls, modules, bootloader
Fully standalone - no external monolith dependency

Features:
- Multi-tier JIT compilation (hotspot tracing)
- Direct syscall interface (Ring 0/3)
- Complete module system with versioning
- Bare-metal bootloader generator (x86-64, ARM64, RISC-V)
- Slab allocator with NUMA support
- Zero-overhead C runtime
- SIMD vectorization (AVX-512, NEON, SVE)
- Ring 0 kernel module generation

Usage:
    import kentscript
    kentscript.version          # Get version
    kentscript.jit.compile()    # Use JIT
    kentscript.syscall.write()  # Direct syscall
    kentscript.bootloader.generate()  # Create bootable kernel
"""

import sys
import os
import platform
import importlib
import warnings
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path

# ============================================================================
# Version Information
# ============================================================================

__version__ = "3.1.0"
__version_info__ = (3, 0, 0)
__codename__ = "Bare Metal"
__build__ = "production"
__author__ = "KentScript Team"
__license__ = "GPL-3.0"

# ============================================================================
# Platform Detection
# ============================================================================

class PlatformInfo:
    """Detect and store platform information"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        self.processor = platform.processor()
        self.python_version = platform.python_version()
        self.python_implementation = platform.python_implementation()
        self.is_64bit = sys.maxsize > 2**32
        
        # Architecture detection
        self.is_x86_64 = 'x86_64' in self.machine or 'amd64' in self.machine
        self.is_aarch64 = 'aarch64' in self.machine or 'arm64' in self.machine
        self.is_arm = self.machine.startswith('arm')
        self.is_riscv64 = 'riscv64' in self.machine
        self.is_powerpc = 'ppc' in self.machine
        
        # OS detection
        self.is_linux = self.system == 'linux'
        self.is_macos = self.system == 'darwin'
        self.is_windows = self.system == 'windows'
        self.is_bsd = self.system in ('freebsd', 'openbsd', 'netbsd')
        
        # Capabilities
        self.has_mmap = hasattr(sys.modules.get('mmap', None), 'mmap')
        self.has_ctypes = 'ctypes' in sys.modules
        
    def __repr__(self) -> str:
        return f"Platform({self.system}/{self.machine})"

_PLATFORM = PlatformInfo()

# ============================================================================
# Lazy Loader - Import only when used
# ============================================================================

class LazyLoader:
    """
    Lazily import modules only when accessed.
    This prevents loading everything at import time.
    """
    
    def __init__(self, module_name: str, attr_name: str = None):
        self.module_name = module_name
        self.attr_name = attr_name
        self._module = None
        self._loaded = False
    
    def __getattr__(self, name: str):
        if not self._loaded:
            self._load()
        return getattr(self._module, name)
    
    def __call__(self, *args, **kwargs):
        if not self._loaded:
            self._load()
        return self._module(*args, **kwargs)
    
    def _load(self):
        """Actually import the module"""
        try:
            if self.attr_name:
                # Import specific attribute from module
                module = importlib.import_module(self.module_name)
                self._module = getattr(module, self.attr_name)
            else:
                # Import whole module
                self._module = importlib.import_module(self.module_name)
            self._loaded = True
        except ImportError as e:
            # Create placeholder that raises helpful error on use
            class MissingModule:
                def __getattr__(self, name):
                    raise ImportError(
                        f"Module '{self.module_name}' not available. "
                        f"Install with: pip install kentscript[full]"
                    )
                def __call__(self, *args, **kwargs):
                    raise ImportError(
                        f"Module '{self.module_name}' not available. "
                        f"Install with: pip install kentscript[full]"
                    )
            self._module = MissingModule()
            self._loaded = True
    
    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "lazy"
        return f"<LazyLoader {self.module_name} ({status})>"


# ============================================================================
# Core Module (ks_core) - Always loaded
# ============================================================================

try:
    from ks_core import *
    _CORE_AVAILABLE = True
except ImportError as e:
    _CORE_AVAILABLE = False
    _CORE_ERROR = str(e)
    warnings.warn(f"ks_core not available: {e}. Some features will be missing.")


# ============================================================================
# Subsystem Status Tracking
# ============================================================================

@dataclass
class SubsystemInfo:
    """Information about a subsystem"""
    name: str
    available: bool
    version: Optional[str] = None
    error: Optional[str] = None
    platform_support: List[str] = None
    
    def __post_init__(self):
        if self.platform_support is None:
            self.platform_support = []


# ============================================================================
# JIT Subsystem - Lazy Loaded
# ============================================================================

class JITSubsystem:
    """JIT compilation subsystem"""
    
    def __init__(self):
        self._KentScriptJIT = LazyLoader('ks_jit', 'KentScriptJIT')
        self._KentJITEngine = LazyLoader('ks_jit', 'KentJITEngine')
        self._JITIntegration = LazyLoader('ks_jit', 'JITIntegration')
        self._available = None
        self._check()
    
    def _check(self):
        """Check if JIT is available"""
        if self._available is not None:
            return self._available
        
        try:
            # Try to import and check platform
            from jit_engine import is_available
            self._available = is_available()
        except ImportError:
            self._available = False
        
        return self._available
    
    @property
    def KentScriptJIT(self):
        return self._KentScriptJIT
    
    @property
    def KentJITEngine(self):
        return self._KentJITEngine
    
    @property
    def JITIntegration(self):
        return self._JITIntegration
    
    @property
    def available(self) -> bool:
        return self._check()
    
    @property
    def info(self) -> SubsystemInfo:
        return SubsystemInfo(
            name="JIT",
            available=self.available,
            version="1.0",
            platform_support=['x86_64', 'aarch64'] if self.available else []
        )
    
    def __repr__(self) -> str:
        return f"<JITSubsystem available={self.available}>"


# ============================================================================
# Syscall Subsystem - Lazy Loaded
# ============================================================================

class SyscallSubsystem:
    """Direct syscall subsystem"""
    
    def __init__(self):
        self._KSyscall = LazyLoader('ks_syscall', 'KSyscall')
        self._LinuxSyscalls = LazyLoader('ks_syscall', 'LinuxSyscalls')
        self._available = None
        self._check()
    
    def _check(self):
        """Check if syscall module is available"""
        if self._available is not None:
            return self._available
        
        try:
            from ks_syscall import is_available
            self._available = is_available()
        except ImportError:
            self._available = False
        
        return self._available
    
    @property
    def KSyscall(self):
        return self._KSyscall
    
    @property
    def LinuxSyscalls(self):
        return self._LinuxSyscalls
    
    @property
    def available(self) -> bool:
        return self._check()
    
    @property
    def info(self) -> SubsystemInfo:
        return SubsystemInfo(
            name="Syscall",
            available=self.available,
            version="1.0",
            platform_support=['linux', 'freebsd'] if self.available else []
        )
    
    def __repr__(self) -> str:
        return f"<SyscallSubsystem available={self.available}>"


# ============================================================================
# Module System Subsystem - Lazy Loaded
# ============================================================================

class ModulesSubsystem:
    """Module system for package management"""
    
    def __init__(self):
        self._ModuleSystem = LazyLoader('ks_modules', 'ModuleSystem')
        self._Module = LazyLoader('ks_modules', 'Module')
        self._available = None
        self._check()
    
    def _check(self):
        """Check if module system is available"""
        if self._available is not None:
            return self._available
        
        try:
            from ks_modules import ModuleSystem
            self._available = True
        except ImportError:
            self._available = False
        
        return self._available
    
    @property
    def ModuleSystem(self):
        return self._ModuleSystem
    
    @property
    def Module(self):
        return self._Module
    
    @property
    def available(self) -> bool:
        return self._check()
    
    @property
    def info(self) -> SubsystemInfo:
        return SubsystemInfo(
            name="Modules",
            available=self.available,
            version="1.0",
            platform_support=['all']
        )
    
    def __repr__(self) -> str:
        return f"<ModulesSubsystem available={self.available}>"


# ============================================================================
# Bootloader Subsystem - Lazy Loaded
# ============================================================================

class BootloaderSubsystem:
    """Bare-metal bootloader generation"""
    
    def __init__(self):
        self._BaremetalBootloader = LazyLoader('ks_bootloader', 'BaremetalBootloader')
        self._ProtectedMode = LazyLoader('ks_bootloader', 'ProtectedMode')
        self._available = None
        self._check()
    
    def _check(self):
        """Check if bootloader module is available"""
        if self._available is not None:
            return self._available
        
        try:
            from ks_bootloader import BaremetalBootloader
            self._available = True
        except ImportError:
            self._available = False
        
        return self._available
    
    @property
    def BaremetalBootloader(self):
        return self._BaremetalBootloader
    
    @property
    def ProtectedMode(self):
        return self._ProtectedMode
    
    @property
    def available(self) -> bool:
        return self._check()
    
    @property
    def info(self) -> SubsystemInfo:
        return SubsystemInfo(
            name="Bootloader",
            available=self.available,
            version="1.0",
            platform_support=['x86_64', 'aarch64', 'riscv64'] if self.available else []
        )
    
    def __repr__(self) -> str:
        return f"<BootloaderSubsystem available={self.available}>"


# ============================================================================
# Runtime Subsystem - Lazy Loaded
# ============================================================================

class RuntimeSubsystem:
    """Runtime components (slab allocator, etc.)"""
    
    def __init__(self):
        self._SlabAllocator = LazyLoader('ks_runtime', 'SlabAllocator')
        self._HybridAllocator = LazyLoader('ks_runtime', 'HybridAllocator')
        self._MemoryPage = LazyLoader('ks_runtime', 'MemoryPage')
        self._available = None
        self._check()
    
    def _check(self):
        """Check if runtime module is available"""
        if self._available is not None:
            return self._available
        
        try:
            from ks_runtime import SlabAllocator
            self._available = True
        except ImportError:
            self._available = False
        
        return self._available
    
    @property
    def SlabAllocator(self):
        return self._SlabAllocator
    
    @property
    def HybridAllocator(self):
        return self._HybridAllocator
    
    @property
    def MemoryPage(self):
        return self._MemoryPage
    
    @property
    def available(self) -> bool:
        return self._check()
    
    def __repr__(self) -> str:
        return f"<RuntimeSubsystem available={self.available}>"


# ============================================================================
# Main Package Object
# ============================================================================

class KentScriptPackage:
    """
    Main package object with all subsystems lazily loaded.
    Use this to access all KentScript functionality.
    """
    
    def __init__(self):
        # Version info
        self.version = __version__
        self.version_info = __version_info__
        self.codename = __codename__
        self.build = __build__
        
        # Platform info
        self.platform = _PLATFORM
        
        # Subsystems
        self.jit = JITSubsystem()
        self.syscall = SyscallSubsystem()
        self.modules = ModulesSubsystem()
        self.bootloader = BootloaderSubsystem()
        self.runtime = RuntimeSubsystem()
        
        # Core functionality (if available)
        self.core_available = _CORE_AVAILABLE
        if not _CORE_AVAILABLE:
            self._core_error = _CORE_ERROR
    
    def info(self) -> Dict[str, Any]:
        """Get complete package information"""
        return {
            'version': self.version,
            'version_info': self.version_info,
            'codename': self.codename,
            'build': self.build,
            'platform': {
                'system': self.platform.system,
                'machine': self.platform.machine,
                'python': self.platform.python_version,
            },
            'subsystems': {
                'jit': self.jit.info.__dict__,
                'syscall': self.syscall.info.__dict__,
                'modules': self.modules.info.__dict__,
                'bootloader': self.bootloader.info.__dict__,
                'runtime': self.runtime.info.__dict__ if self.runtime.available else None,
            },
            'core_available': self.core_available,
        }
    
    def summary(self) -> str:
        """Print package summary"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"KentScript v{self.version} ({self.codename})")
        lines.append("=" * 70)
        lines.append(f"Platform: {self.platform.system}/{self.platform.machine}")
        lines.append(f"Python: {self.platform.python_version}")
        lines.append("")
        lines.append("Subsystems:")
        
        for name, sub in [
            ("JIT", self.jit),
            ("Syscall", self.syscall),
            ("Modules", self.modules),
            ("Bootloader", self.bootloader),
            ("Runtime", self.runtime),
        ]:
            status = "✓" if sub.available else "✗"
            lines.append(f"  {status} {name}")
        
        if not self.core_available:
            lines.append("")
            lines.append(f"⚠️  Core module not available: {getattr(self, '_core_error', 'unknown')}")
        
        lines.append("=" * 70)
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return f"<KentScript v{self.version} ({self.platform.system})>"


# ============================================================================
# Create singleton instance
# ============================================================================

_ks = KentScriptPackage()

# Export main package object
ks = _ks

# Also export subsystems directly for convenience
jit = _ks.jit
syscall = _ks.syscall
modules = _ks.modules
bootloader = _ks.bootloader
runtime = _ks.runtime

# ============================================================================
# Convenience imports (lazy)
# ============================================================================

# JIT
KentScriptJIT = jit.KentScriptJIT
KentJITEngine = jit.KentJITEngine
JITIntegration = jit.JITIntegration

# Syscall
KSyscall = syscall.KSyscall
LinuxSyscalls = syscall.LinuxSyscalls

# Modules
ModuleSystem = modules.ModuleSystem
Module = modules.Module

# Bootloader
BaremetalBootloader = bootloader.BaremetalBootloader
ProtectedMode = bootloader.ProtectedMode

# Runtime
SlabAllocator = runtime.SlabAllocator
HybridAllocator = runtime.HybridAllocator
MemoryPage = runtime.MemoryPage


# ============================================================================
# Utility Functions
# ============================================================================

def check_platform() -> Dict[str, bool]:
    """Check platform capabilities"""
    return {
        'x86_64': _PLATFORM.is_x86_64,
        'aarch64': _PLATFORM.is_aarch64,
        'arm': _PLATFORM.is_arm,
        'riscv64': _PLATFORM.is_riscv64,
        'linux': _PLATFORM.is_linux,
        'macos': _PLATFORM.is_macos,
        'windows': _PLATFORM.is_windows,
        'bsd': _PLATFORM.is_bsd,
        '64bit': _PLATFORM.is_64bit,
        'mmap': _PLATFORM.has_mmap,
        'ctypes': _PLATFORM.has_ctypes,
    }


def require_subsystem(name: str):
    """Decorator to require a subsystem"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            sub = getattr(_ks, name, None)
            if sub and not sub.available:
                raise ImportError(
                    f"Subsystem '{name}' is required but not available. "
                    f"Install with: pip install kentscript[{name}]"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# Command-line entry point
# ============================================================================

def main():
    """Command-line entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="KentScript v3.1.0")
    parser.add_argument('--version', '-v', action='store_true', help='Show version')
    parser.add_argument('--info', action='store_true', help='Show system info')
    parser.add_argument('--check', action='store_true', help='Check platform')
    
    args = parser.parse_args()
    
    if args.version:
        print(f"KentScript v{__version__} ({__codename__})")
    
    elif args.info:
        print(ks.summary())
    
    elif args.check:
        caps = check_platform()
        print("Platform capabilities:")
        for k, v in caps.items():
            print(f"  {k}: {'✓' if v else '✗'}")
    
    else:
        parser.print_help()


# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    # Main package
    'ks',
    
    # Version info
    '__version__',
    '__version_info__',
    '__codename__',
    '__build__',
    
    # Subsystems
    'jit',
    'syscall',
    'modules',
    'bootloader',
    'runtime',
    
    # JIT
    'KentScriptJIT',
    'KentJITEngine',
    'JITIntegration',
    
    # Syscall
    'KSyscall',
    'LinuxSyscalls',
    
    # Modules
    'ModuleSystem',
    'Module',
    
    # Bootloader
    'BaremetalBootloader',
    'ProtectedMode',
    
    # Runtime
    'SlabAllocator',
    'HybridAllocator',
    'MemoryPage',
    
    # Utilities
    'check_platform',
    'require_subsystem',
    'PlatformInfo',
]

# ============================================================================
# Package initialization
# ============================================================================

# Print version on import if debug
if os.environ.get('KS_DEBUG'):
    print(f"[KentScript] v{__version__} loaded", file=sys.stderr)
    print(f"[KentScript] Platform: {_PLATFORM}", file=sys.stderr)
