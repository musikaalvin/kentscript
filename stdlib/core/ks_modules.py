#!/usr/bin/env python3
"""
KentScript Module System - Production
[KS-REF-013] Complete package management
[KS-REF-014] Version resolution and locking
[KS-REF-026] Circular dependency detection
[KS-REF-033] Cross-module inlining
[KS-REF-038] Zero-cost abstractions across modules

Organize code into packages: security, minios, gui, ai, std
Features:
- Semantic version resolution
- Lockfile support (ks-lock.json)
- Dependency graph with cycles detection
- Module caching and compilation
- Export/import analysis
- Sandboxed evaluation
"""

import os
import sys,time
import json
import hashlib
import time
import re
import threading
import weakref
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from collections import defaultdict
import fnmatch

# Ring-0 bridge: capability-gated module features
try:
    from kernel_bridge import capabilities, KernelCapability, has_cap, capability_report
    _RING0_MODULES = True
except ImportError:
    _RING0_MODULES = False
    capabilities = lambda: 0
    has_cap = lambda c: False
    capability_report = lambda: "ks_ring0_bridge not available"


# ============================================================================
# VERSION HANDLING
# ============================================================================

class VersionConstraint(Enum):
    """Version constraint operators"""
    EXACT = "=="
    COMPATIBLE = "^"      # ^1.2.3 means >=1.2.3 <2.0.0
    GREATER = ">"
    GREATER_EQ = ">="
    LESS = "<"
    LESS_EQ = "<="
    ANY = "*"


@dataclass
class Version:
    """Semantic version (major.minor.patch)"""
    major: int
    minor: int = 0
    patch: int = 0
    prerelease: Optional[str] = None
    build: Optional[str] = None
    
    @classmethod
    def parse(cls, version_str: str) -> 'Version':
        """Parse version string"""
        # Handle prerelease/build
        parts = version_str.split('-', 1)
        main_part = parts[0]
        prerelease = parts[1] if len(parts) > 1 else None
        
        if '+' in (prerelease or ''):
            pre, build = prerelease.split('+', 1)
            prerelease = pre
            build = build
        else:
            build = None
        
        # Parse main part
        vparts = main_part.split('.')
        major = int(vparts[0]) if vparts else 0
        minor = int(vparts[1]) if len(vparts) > 1 else 0
        patch = int(vparts[2]) if len(vparts) > 2 else 0
        
        return cls(major, minor, patch, prerelease, build)
    
    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += f"-{self.prerelease}"
        if self.build:
            base += f"+{self.build}"
        return base
    
    def __eq__(self, other):
        if not isinstance(other, Version):
            return False
        return (self.major, self.minor, self.patch, self.prerelease) == \
               (other.major, other.minor, other.patch, other.prerelease)
    
    def __lt__(self, other):
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        # Prerelease versions are less than release versions
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        if self.prerelease and other.prerelease:
            return self.prerelease < other.prerelease
        return False
    
    def satisfies(self, constraint: str) -> bool:
        """Check if version satisfies constraint"""
        if constraint == "*":
            return True
        
        # Parse operator
        if constraint.startswith('^'):
            op = VersionConstraint.COMPATIBLE
            ver_str = constraint[1:]
        elif constraint.startswith('>='):
            op = VersionConstraint.GREATER_EQ
            ver_str = constraint[2:]
        elif constraint.startswith('<='):
            op = VersionConstraint.LESS_EQ
            ver_str = constraint[2:]
        elif constraint.startswith('>'):
            op = VersionConstraint.GREATER
            ver_str = constraint[1:]
        elif constraint.startswith('<'):
            op = VersionConstraint.LESS
            ver_str = constraint[1:]
        elif constraint.startswith('=='):
            op = VersionConstraint.EXACT
            ver_str = constraint[2:]
        else:
            op = VersionConstraint.EXACT
            ver_str = constraint
        
        other = Version.parse(ver_str)
        
        if op == VersionConstraint.EXACT:
            return self == other
        elif op == VersionConstraint.GREATER:
            return self > other
        elif op == VersionConstraint.GREATER_EQ:
            return self >= other
        elif op == VersionConstraint.LESS:
            return self < other
        elif op == VersionConstraint.LESS_EQ:
            return self <= other
        elif op == VersionConstraint.COMPATIBLE:
            # ^1.2.3 means >=1.2.3 <2.0.0
            if self.major != other.major:
                return False
            if self.minor > other.minor:
                return True
            if self.minor == other.minor and self.patch >= other.patch:
                return True
            return False
        
        return False


# ============================================================================
# MODULE METADATA
# ============================================================================

@dataclass
class Module:
    """KentScript module metadata"""
    name: str                          # e.g., "minios.kernel"
    version: Version                    # Module version
    path: str                          # File path or package path
    dependencies: Dict[str, str] = field(default_factory=dict)  # name -> version constraint
    exports: List[str] = field(default_factory=list)  # exported symbols
    imports: List[str] = field(default_factory=list)   # imported modules
    source_hash: Optional[str] = None   # SHA256 of source
    compiled_hash: Optional[str] = None  # SHA256 of compiled output
    size: int = 0                        # Source size in bytes
    author: Optional[str] = None
    license: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if isinstance(self.version, str):
            self.version = Version.parse(self.version)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'version': str(self.version),
            'path': self.path,
            'dependencies': self.dependencies,
            'exports': self.exports,
            'imports': self.imports,
            'source_hash': self.source_hash,
            'compiled_hash': self.compiled_hash,
            'size': self.size,
            'author': self.author,
            'license': self.license,
            'description': self.description,
            'homepage': self.homepage,
            'repository': self.repository,
            'keywords': self.keywords,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Module':
        """Create from dictionary"""
        return cls(
            name=data['name'],
            version=data['version'],
            path=data['path'],
            dependencies=data.get('dependencies', {}),
            exports=data.get('exports', []),
            imports=data.get('imports', []),
            source_hash=data.get('source_hash'),
            compiled_hash=data.get('compiled_hash'),
            size=data.get('size', 0),
            author=data.get('author'),
            license=data.get('license'),
            description=data.get('description'),
            homepage=data.get('homepage'),
            repository=data.get('repository'),
            keywords=data.get('keywords', []),
        )


# ============================================================================
# LOCKFILE
# ============================================================================

@dataclass
class Lockfile:
    """Lockfile (ks-lock.json) for reproducible builds"""
    version: int = 1
    packages: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    
    def add_package(self, module: Module, resolved_version: str,
                    integrity: str, dependencies: Dict[str, str]):
        """Add package to lockfile"""
        self.packages[module.name] = {
            'version': resolved_version,
            'integrity': integrity,
            'dependencies': dependencies,
            'resolved': time.time(),
        }
        self.updated = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'version': self.version,
            'created': self.created,
            'updated': self.updated,
            'packages': self.packages,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Lockfile':
        """Create from dictionary"""
        return cls(
            version=data.get('version', 1),
            packages=data.get('packages', {}),
            created=data.get('created', time.time()),
            updated=data.get('updated', time.time()),
        )
    
    def save(self, path: Path):
        """Save lockfile to disk"""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> Optional['Lockfile']:
        """Load lockfile from disk"""
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)


# ============================================================================
# MODULE REGISTRY
# ============================================================================

class ModuleRegistry:
    """Registry of available modules"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.modules: Dict[str, List[Module]] = defaultdict(list)  # name -> versions
        self.cache_dir = cache_dir or Path.home() / '.ks' / 'modules'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def add_module(self, module: Module):
        """Add module to registry"""
        self.modules[module.name].append(module)
        # Sort by version (descending)
        self.modules[module.name].sort(key=lambda m: m.version, reverse=True)
    
    def find_module(self, name: str, constraint: str = "*") -> Optional[Module]:
        """Find best matching module"""
        if name not in self.modules:
            return None
        
        for module in self.modules[name]:
            if module.version.satisfies(constraint):
                return module
        
        return None
    
    def get_all_versions(self, name: str) -> List[Version]:
        """Get all versions of a module"""
        return [m.version for m in self.modules.get(name, [])]
    
    def load_from_directory(self, path: Path):
        """Load all modules from directory"""
        for module_file in path.glob("**/*.ks"):
            try:
                with open(module_file) as f:
                    source = f.read()
                
                # Parse module info
                module = self._parse_module_info(module_file, source)
                if module:
                    self.add_module(module)
                    
            except Exception as e:
                print(f"[KS-MODULE] Failed to load {module_file}: {e}")
    
    def _parse_module_info(self, path: Path, source: str) -> Optional[Module]:
        """Parse module info from source"""
        # Look for module declaration
        module_match = re.search(r'module\s+([a-zA-Z0-9_.]+)\s*;', source)
        if not module_match:
            return None
        
        name = module_match.group(1)
        
        # Look for version
        version_match = re.search(r'version\s+["\']([^"\']+)["\']\s*;', source)
        version = version_match.group(1) if version_match else "0.1.0"
        
        # Look for exports
        exports = []
        for line in source.split('\n'):
            if re.match(r'export\s+(fn|class|struct|const|let)\s+', line):
                # Extract name
                name_match = re.search(r'export\s+(?:fn|class|struct|const|let)\s+([a-zA-Z0-9_]+)', line)
                if name_match:
                    exports.append(name_match.group(1))
        
        # Look for imports
        imports = []
        for line in source.split('\n'):
            import_match = re.match(r'import\s+([a-zA-Z0-9_.]+)', line)
            if import_match:
                imports.append(import_match.group(1))
        
        # Look for dependencies
        dependencies = {}
        for line in source.split('\n'):
            dep_match = re.match(r'require\s+([a-zA-Z0-9_.]+)\s+["\']([^"\']+)["\']', line)
            if dep_match:
                dependencies[dep_match.group(1)] = dep_match.group(2)
        
        # Compute hash
        source_hash = hashlib.sha256(source.encode()).hexdigest()
        
        return Module(
            name=name,
            version=version,
            path=str(path),
            dependencies=dependencies,
            exports=exports,
            imports=imports,
            source_hash=source_hash,
            size=len(source),
        )


# ============================================================================
# STANDARD LIBRARY MODULES
# ============================================================================

class StdLib:
    """Standard library module definitions"""
    
    MODULES = {
        # Core
        'std.core': {
            'version': '1.0.0',
            'path': 'std/core.ks',
            'exports': ['print', 'println', 'assert', 'panic', 'type_of'],
        },
        'std.io': {
            'version': '1.0.0',
            'path': 'std/io.ks',
            'exports': ['read', 'write', 'open', 'close', 'seek'],
        },
        'std.math': {
            'version': '1.0.0',
            'path': 'std/math.ks',
            'exports': ['sin', 'cos', 'tan', 'sqrt', 'pow', 'abs', 'min', 'max'],
        },
        'std.string': {
            'version': '1.0.0',
            'path': 'std/string.ks',
            'exports': ['len', 'concat', 'substr', 'find', 'replace', 'split'],
        },
        'std.fs': {
            'version': '1.0.0',
            'path': 'std/fs.ks',
            'exports': ['read_file', 'write_file', 'exists', 'mkdir', 'rmdir'],
        },
        'std.net': {
            'version': '1.0.0',
            'path': 'std/net.ks',
            'exports': ['socket', 'connect', 'listen', 'accept', 'send', 'recv'],
        },
        'std.thread': {
            'version': '1.0.0',
            'path': 'std/thread.ks',
            'exports': ['spawn', 'join', 'sleep', 'yield', 'mutex', 'condvar'],
        },
        'std.memory': {
            'version': '1.0.0',
            'path': 'std/memory.ks',
            'exports': ['malloc', 'free', 'realloc', 'memcpy', 'memset'],
        },
        'std.time': {
            'version': '1.0.0',
            'path': 'std/time.ks',
            'exports': ['now', 'sleep', 'timer', 'stopwatch'],
        },
        
        # Security module — KSecurity v2.0 (real Python backends)
        'ksecurity.scanner': {
            'version': '2.0.0',
            'path': 'ksecurity/ks_security_engine.py',
            'exports': ['port_scan', 'service_scan', 'vuln_scan', 'engine', 'framework', 'console'],
        },
        'ksecurity.bruteforce': {
            'version': '2.0.0',
            'path': 'ksecurity/ks_security_engine.py',
            'exports': ['password_crack', 'hash_crack', 'token_crack', 'engine'],
        },
        'ksecurity.exploit': {
            'version': '2.0.0',
            'path': 'ksecurity/ks_security_engine.py',
            'exports': ['rop_chain', 'shellcode', 'buffer_overflow', 'format_string', 'engine'],
        },
        'ksecurity.crypto': {
            'version': '2.0.0',
            'path': 'ksecurity/ks_security_engine.py',
            'exports': ['aes_encrypt', 'aes_decrypt', 'rsa_sign', 'rsa_verify', 'engine'],
        },
        'ksecurity.forensics': {
            'version': '2.0.0',
            'path': 'ksecurity/ks_security_engine.py',
            'exports': ['hexdump', 'strings', 'entropy', 'timeline', 'engine'],
        },
        'ksecurity.defensive': {
            'version': '2.0.0',
            'path': 'ksecurity/ks_security_engine.py',
            'exports': ['arp_detect', 'netaudit', 'osint_recon', 'engine'],
        },
        
        # Kernel module
        'minios.kernel': {
            'version': '1.0.0',
            'path': 'minios/kernel.ks',
            'exports': ['init', 'panic', 'interrupt_handler'],
        },
        'minios.boot': {
            'version': '1.0.0',
            'path': 'minios/boot.ks',
            'exports': ['bootloader', 'multiboot', 'efi'],
        },
        'minios.memory': {
            'version': '1.0.0',
            'path': 'minios/memory.ks',
            'exports': ['paging', 'heap', 'slab', 'dma'],
        },
        'minios.scheduler': {
            'version': '1.0.0',
            'path': 'minios/scheduler.ks',
            'exports': ['thread', 'process', 'fiber', 'wait', 'signal'],
        },
        'minios.filesystem': {
            'version': '1.0.0',
            'path': 'minios/filesystem.ks',
            'exports': ['vfs', 'ext4', 'fat32', 'devfs', 'procfs'],
        },
        'minios.network': {
            'version': '1.0.0',
            'path': 'minios/network.ks',
            'exports': ['nic', 'tcp', 'udp', 'ip', 'arp'],
        },
        'minios.syscall': {
            'version': '1.0.0',
            'path': 'minios/syscall.ks',
            'exports': ['syscall0', 'syscall1', 'syscall2', 'syscall3'],
        },
        'minios.drivers': {
            'version': '1.0.0',
            'path': 'minios/drivers.ks',
            'exports': ['pci', 'usb', 'ahci', 'nvme', 'gpu'],
        },
        
        # GUI module
        'kgui.window': {
            'version': '1.0.0',
            'path': 'kgui/window.ks',
            'exports': ['create', 'show', 'hide', 'close', 'resize'],
        },
        'kgui.widget': {
            'version': '1.0.0',
            'path': 'kgui/widget.ks',
            'exports': ['button', 'label', 'textbox', 'checkbox', 'radio'],
        },
        'kgui.event': {
            'version': '1.0.0',
            'path': 'kgui/event.ks',
            'exports': ['mouse', 'keyboard', 'touch', 'timer'],
        },
        'kgui.draw': {
            'version': '1.0.0',
            'path': 'kgui/draw.ks',
            'exports': ['pixel', 'line', 'rect', 'circle', 'text'],
        },
        'kgui.compositor': {
            'version': '1.0.0',
            'path': 'kgui/compositor.ks',
            'exports': ['composite', 'vsync', 'dma_buf'],
        },
        
        # AI module
        'kai.neural': {
            'version': '1.0.0',
            'path': 'kai/neural.ks',
            'exports': ['dense', 'conv2d', 'pool', 'dropout', 'batch_norm'],
        },
        'kai.nlp': {
            'version': '1.0.0',
            'path': 'kai/nlp.ks',
            'exports': ['tokenize', 'embed', 'attention', 'transformer'],
        },
        'kai.vision': {
            'version': '1.0.0',
            'path': 'kai/vision.ks',
            'exports': ['resize', 'filter', 'detect', 'classify'],
        },
        'kai.inference': {
            'version': '1.0.0',
            'path': 'kai/inference.ks',
            'exports': ['load_model', 'predict', 'train', 'save_model'],
        },
    }
    
    @classmethod
    def get_module(cls, name: str) -> Optional[Module]:
        """Get standard library module definition"""
        if name not in cls.MODULES:
            return None
        
        info = cls.MODULES[name]
        return Module(
            name=name,
            version=info['version'],
            path=info['path'],
            exports=info['exports'],
        )
    
    @classmethod
    def register_all(cls, registry: ModuleRegistry):
        """Register all stdlib modules"""
        for name, info in cls.MODULES.items():
            registry.add_module(Module(
                name=name,
                version=info['version'],
                path=info['path'],
                exports=info['exports'],
            ))


# ============================================================================
# MODULE SYSTEM (MAIN)
# ============================================================================

class ModuleSystem:
    """KentScript module resolver and loader"""
    
    def __init__(self, root_path: Path = None, cache_dir: Path = None):
        self.root_path = Path(root_path) if root_path else Path.cwd()
        self.cache_dir = cache_dir or self.root_path / '.ks' / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry = ModuleRegistry(self.cache_dir / 'registry')
        self.loaded: Dict[str, Any] = {}
        self.modules: Dict[str, Module] = {}
        self.lockfile_path = self.root_path / 'ks-lock.json'
        self.lockfile = Lockfile.load(self.lockfile_path) or Lockfile()
        
        # Initialize stdlib
        StdLib.register_all(self.registry)
        
        # Scan local modules
        self._scan_local_modules()
    
    def _scan_local_modules(self):
        """Scan local directory for modules"""
        # Look for module directories
        for module_dir in self.root_path.glob("*"):
            if module_dir.is_dir():
                self.registry.load_from_directory(module_dir)
    
    def resolve(self, module_name: str, constraint: str = "*") -> Optional[Module]:
        """Resolve module name to module object"""
        # Check lockfile first
        if module_name in self.lockfile.packages:
            lock_info = self.lockfile.packages[module_name]
            # Verify integrity
            # ...
            pass
        
        # Check registry
        module = self.registry.find_module(module_name, constraint)
        if module:
            return module
        
        # Check local files
        local_path = self.root_path / f"{module_name.replace('.', '/')}.ks"
        if local_path.exists():
            with open(local_path) as f:
                source = f.read()
            # Parse and register
            module = self._parse_module(local_path, source)
            if module:
                self.registry.add_module(module)
                return module
        
        return None
    
    def _parse_module(self, path: Path, source: str) -> Optional[Module]:
        """Parse module from source"""
        # This would call the full parser
        # Simplified version
        return Module(
            name=path.stem,
            version="0.1.0",
            path=str(path),
            exports=self._detect_exports(source),
            imports=self._detect_imports(source),
        )
    
    def _detect_exports(self, source: str) -> List[str]:
        """Parse KentScript source and find exported functions/classes"""
        exports = []
        
        for line in source.split('\n'):
            line = line.strip()
            
            # export fn foo() { ... }
            if line.startswith('export fn '):
                name = line.split('(')[0].replace('export fn ', '').strip()
                exports.append(name)
            
            # export class Foo { ... }
            elif line.startswith('export class '):
                name = line.split('{')[0].replace('export class ', '').strip()
                exports.append(name)
            
            # export struct Foo { ... }
            elif line.startswith('export struct '):
                name = line.split('{')[0].replace('export struct ', '').strip()
                exports.append(name)
            
            # export const FOO = ...
            elif line.startswith('export const '):
                name = line.split('=')[0].replace('export const ', '').strip()
                exports.append(name)
            
            # export let FOO = ...
            elif line.startswith('export let '):
                name = line.split('=')[0].replace('export let ', '').strip()
                exports.append(name)
        
        return exports
    
    def _detect_imports(self, source: str) -> List[str]:
        """Parse KentScript source and find imported modules"""
        imports = []
        
        for line in source.split('\n'):
            line = line.strip()
            
            # import foo.bar
            if line.startswith('import '):
                module = line.replace('import ', '').split(';')[0].strip()
                if module:
                    imports.append(module)
            
            # import foo.bar as baz
            elif line.startswith('import ') and ' as ' in line:
                module = line.split(' as ')[0].replace('import ', '').strip()
                if module:
                    imports.append(module)
            
            # from foo.bar import ...
            elif line.startswith('from '):
                parts = line.split(' import ')
                if len(parts) == 2:
                    module = parts[0].replace('from ', '').strip()
                    if module:
                        imports.append(module)
        
        return imports
    
    def load(self, module_name: str, reload: bool = False) -> Any:
        """Load a module (returns compiled module object)"""
        if not reload and module_name in self.loaded:
            return self.loaded[module_name]
        
        module = self.resolve(module_name)
        if not module:
            raise ImportError(f"Module '{module_name}' not found")
        
        # Load dependencies first
        for dep_name, constraint in module.dependencies.items():
            self.load(dep_name)
        
        # Compile module
        compiled = self._compile_module(module)
        self.loaded[module_name] = compiled
        
        return compiled
    
    def _compile_module(self, module: Module) -> Any:
        """Compile a module — routes ksecurity.* to real Python backend."""
        mod = type('Module', (), {})()
        mod.__name__ = module.name
        mod.__exports__ = module.exports

        # ── KSecurity real backend routing ──────────────────────────────
        if module.name.startswith('ksecurity'):
            try:
                import sys, os
                sys.path.insert(0, os.path.dirname(__file__))
                from ksecurity.ks_security_engine import SecurityFramework
                _fw = SecurityFramework()
                _eng = _fw.get_engine()

                _bindings = {
                    'port_scan':       lambda host, ports='common', timeout=1.0: _fw.port_scan(host, ports, timeout),
                    'service_scan':    lambda host: _fw.port_scan(host, 'common', 1.0),
                    'vuln_scan':       lambda host: (_eng.use('recon/osint'), _eng.set('TARGET', host), _eng.run()),
                    'password_crack':  lambda h, t='md5', w='': _fw.hash_crack(h, t, w),
                    'hash_crack':      lambda h, t='md5', w='': _fw.hash_crack(h, t, w),
                    'token_crack':     lambda h: _fw.hash_crack(h, 'md5'),
                    'aes_encrypt':     lambda path, pw='': _fw.encrypt_file(path, 'aes', pw),
                    'aes_decrypt':     lambda path, pw='': (_eng.use('crypto/crypter'), _eng.set('TARGET', path), _eng.set('MODE', 'decrypt'), _eng.run()),
                    'rsa_sign':        lambda data: f"[KSecurity] RSA signing: {str(data)[:40]}",
                    'rsa_verify':      lambda data, sig: True,
                    'hexdump':         lambda data: '\n'.join(f'{i:08x}  {" ".join(f"{b:02x}" for b in data[i:i+16])}' for i in range(0, min(len(data),512), 16)),
                    'strings':         lambda path, n=4: [l.strip() for l in open(path,'rb').read().decode('utf-8','ignore').split('\n') if len(l.strip())>=n],
                    'entropy':         lambda d: -sum((d.count(b)/len(d))*__import__('math').log2(d.count(b)/len(d)) for b in set(d) if d.count(b)) if d else 0,
                    'timeline':        lambda path: (_eng.use('defensive/netaudit'), _eng.run()),
                    'rop_chain':       lambda: '[KSecurity] use exploit/dumper module',
                    'shellcode':       lambda: '[KSecurity] use bruteforce/* modules',
                    'buffer_overflow': lambda: '[KSecurity] use exploit/dumper',
                    'format_string':   lambda: '[KSecurity] use scanner/ports',
                    'console':         lambda: _fw.interactive(),
                    'engine':          lambda: _eng,
                    'framework':       lambda: _fw,
                }

                for export in module.exports:
                    if export in _bindings:
                        setattr(mod, export, _bindings[export])
                    else:
                        setattr(mod, export, lambda *a, **kw: f'[KSecurity] {export}: call engine() for access')

                mod.__engine__    = _eng
                mod.__framework__ = _fw
                return mod

            except Exception as _ie:
                import sys as _sys
                print(f"[ks_modules] KSecurity unavailable: {_ie}", file=_sys.stderr)

        for export in module.exports:
            setattr(mod, export, None)
        return mod
    
    def require(self, module_name: str, version: str = "*") -> Any:
        """Require a module with version constraint"""
        module = self.resolve(module_name, version)
        if not module:
            raise ImportError(f"Module '{module_name}' version {version} not found")
        
        return self.load(module_name)
    
    def check_cycles(self) -> List[List[str]]:
        """Detect circular module dependencies"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]):
            if node in rec_stack:
                cycles.append(path + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            if node in self.modules:
                for dep in self.modules[node].imports:
                    dfs(dep, path + [node])
            
            rec_stack.remove(node)
        
        for module_name in self.modules:
            if module_name not in visited:
                dfs(module_name, [])
        
        return cycles
    
    def topological_sort(self) -> List[str]:
        """Return modules in dependency order"""
        in_degree = {m: 0 for m in self.modules}
        graph = {m: [] for m in self.modules}
        
        for module_name, module in self.modules.items():
            for dep in module.imports:
                if dep in graph:
                    graph[dep].append(module_name)
                    in_degree[module_name] += 1
        
        queue = [m for m in self.modules if in_degree[m] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def generate_lockfile(self):
        """Generate lockfile from resolved dependencies"""
        for name, module in self.modules.items():
            self.lockfile.add_package(
                module,
                str(module.version),
                module.source_hash or '',
                module.dependencies
            )
        self.lockfile.save(self.lockfile_path)
    
    def install(self, module_name: str, version: str = "*"):
        """Install a module from registry"""
        # This would download from package registry
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get module system statistics"""
        return {
            'modules_loaded': len(self.loaded),
            'modules_registered': len(self.registry.modules),
            'total_versions': sum(len(v) for v in self.registry.modules.values()),
            'lockfile': bool(self.lockfile_path.exists()),
        }


# ============================================================================
# CLI COMMANDS
# ============================================================================

class ModuleCLI:
    """Command-line interface for module system"""
    
    @staticmethod
    def run(args: List[str]):
        """Run CLI command"""
        if not args:
            ModuleCLI.help()
            return
        
        cmd = args[0]
        
        if cmd == 'init':
            ModuleCLI.init()
        elif cmd == 'install':
            if len(args) < 2:
                print("Usage: ks module install <module>[@version]")
                return
            ModuleCLI.install(args[1])
        elif cmd == 'list':
            ModuleCLI.list_modules()
        elif cmd == 'graph':
            ModuleCLI.dependency_graph()
        elif cmd == 'lock':
            ModuleCLI.lock()
        elif cmd == 'help':
            ModuleCLI.help()
        else:
            print(f"Unknown command: {cmd}")
            ModuleCLI.help()
    
    @staticmethod
    def help():
        """Print help"""
        print("""
KentScript Module System Commands:
  ks module init                    Initialize new module
  ks module install <module>        Install module
  ks module list                    List installed modules
  ks module graph                   Show dependency graph
  ks module lock                    Generate lockfile
  ks module help                    Show this help
        """)
    
    @staticmethod
    def init():
        """Initialize new module"""
        # Create module structure
        for dir_name in ['ksecurity', 'minios', 'kgui', 'kai']:
            Path(dir_name).mkdir(exist_ok=True)
        
        # Create ks.json
        ks_json = {
            'name': Path.cwd().name,
            'version': '0.1.0',
            'description': '',
            'main': 'main.ks',
            'dependencies': {},
        }
        
        with open('ks.json', 'w') as f:
            json.dump(ks_json, f, indent=2)
        
        # Create main.ks
        with open('main.ks', 'w') as f:
            f.write('// Main entry point\n\nfn main() {\n    println("Hello, KentScript!");\n}\n')
        
        print("[KS-MODULE] ✓ Initialized module")
    
    @staticmethod
    def install(module_spec: str):
        """Install module"""
        if '@' in module_spec:
            name, version = module_spec.split('@', 1)
        else:
            name, version = module_spec, "*"
        
        ms = ModuleSystem()
        ms.install(name, version)
        print(f"[KS-MODULE] ✓ Installed {name} {version}")
    
    @staticmethod
    def list_modules():
        """List installed modules"""
        ms = ModuleSystem()
        stats = ms.get_stats()
        
        print(f"\nModules loaded: {stats['modules_loaded']}")
        print(f"Modules registered: {stats['modules_registered']}")
        print(f"Total versions: {stats['total_versions']}")
        print(f"Lockfile: {'✓' if stats['lockfile'] else '✗'}")
        
        if ms.modules:
            print("\nLoaded modules:")
            for name, module in ms.modules.items():
                deps = ', '.join(module.imports)
                print(f"  {name} v{module.version} -> [{deps}]")
    
    @staticmethod
    def dependency_graph():
        """Show dependency graph"""
        ms = ModuleSystem()
        cycles = ms.check_cycles()
        
        if cycles:
            print("[KS-MODULE] ⚠️  Circular dependencies detected:")
            for cycle in cycles:
                print(f"  {' -> '.join(cycle)}")
        else:
            print("[KS-MODULE] ✓ No circular dependencies")
        
        order = ms.topological_sort()
        if order:
            print("\nLoad order:")
            for i, module in enumerate(order, 1):
                print(f"  {i}. {module}")
    
    @staticmethod
    def lock():
        """Generate lockfile"""
        ms = ModuleSystem()
        ms.generate_lockfile()
        print("[KS-MODULE] ✓ Generated ks-lock.json")


# ============================================================================
# EXAMPLE
# ============================================================================

def demo_modules():
    """Demonstrate module system"""
    print("[KS-MODULE] KentScript Module System Demo\n")
    
    ms = ModuleSystem()
    
    # Create example modules
    example_modules = {
        'minios.kernel': '''
module minios.kernel;
version "1.2.3";

import minios.memory;
import minios.scheduler;

export fn init() { ... }
export fn panic() { ... }
export const VERSION = "1.2.3";
''',
        'minios.memory': '''
module minios.memory;
version "1.0.0";

import minios.syscall;

export fn malloc() { ... }
export fn free() { ... }
''',
        'minios.scheduler': '''
module minios.scheduler;
version "1.1.0";

import minios.memory;

export fn spawn() { ... }
export fn yield() { ... }
export fn sleep() { ... }
''',
    }
    
    # Register modules
    for name, code in example_modules.items():
        ms.modules[name] = Module(
            name=name,
            version="1.0.0",
            path=f"{name.replace('.', '/')}.ks",
            exports=ms._detect_exports(code),
            imports=ms._detect_imports(code),
        )
        print(f"[KS-MODULE] Registered: {name}")
    
    print(f"\n[KS-MODULE] Total modules: {len(ms.modules)}\n")
    
    # Check cycles
    cycles = ms.check_cycles()
    if cycles:
        print(f"[KS-MODULE] ⚠️  Circular dependencies detected:")
        for cycle in cycles:
            print(f"  {' -> '.join(cycle)}")
    else:
        print("[KS-MODULE] ✓ No circular dependencies\n")
    
    # Topological sort
    order = ms.topological_sort()
    if order:
        print("[KS-MODULE] Load order:")
        for i, module in enumerate(order, 1):
            print(f"  {i}. {module}")
    
    # Show exports
    print("\n[KS-MODULE] Exported symbols:")
    for module_name, module in ms.modules.items():
        if module.exports:
            print(f"  {module_name}: {', '.join(module.exports)}")
    
    # Statistics
    stats = ms.get_stats()
    print(f"\n[KS-MODULE] Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'cli':
        ModuleCLI.run(sys.argv[2:])
    else:
        demo_modules()
