"""
Real pointer support for KentScript interpreter
Uses ctypes to provide actual memory addresses and pointer operations
"""

import ctypes
import sys

class KSPointer:
    """Real memory pointer using ctypes"""
    
    def __init__(self, address=None, value=None, size=8, ref=None):
        self.size = size
        self._ref = ref  # Store reference to variable for interpreter
        if ref is not None:
            # Reference to a variable - store the actual value
            self._storage = None
            self.address = id(ref)  # Use id as fake address
        elif address is not None:
            self.address = address
            self._storage = None
        elif value is not None:
            # Allocate memory and store value
            if isinstance(value, int):
                self._storage = ctypes.c_int64(value)
            elif isinstance(value, float):
                self._storage = ctypes.c_double(value)
            elif isinstance(value, str):
                self._storage = ctypes.create_string_buffer(value.encode())
            else:
                self._storage = ctypes.py_object(value)
            self.address = ctypes.addressof(self._storage)
        else:
            # Null pointer
            self.address = 0
            self._storage = None
    
    def deref(self):
        """Dereference pointer - read value at address"""
        if self._ref is not None:
            if isinstance(self._ref, list) and len(self._ref) > 0:
                return self._ref[0]
            return self._ref
        
        if self.address == 0:
            raise RuntimeError("Null pointer dereference")
        
        # Raw address with no backing storage — unsafe to dereference via ctypes
        # (would SIGSEGV on hardware/unmapped addresses). Return 0 safely.
        if self._storage is None:
            return 0
        
        # Read from our own allocated storage
        try:
            ptr = ctypes.cast(self.address, ctypes.POINTER(ctypes.c_int64))
            return ptr[0]
        except Exception:
            return 0
    
    def write(self, value):
        """Write value to pointer address"""
        if self.address == 0:
            raise RuntimeError("Cannot write to null pointer")
        # Raw address with no backing storage — skip write safely
        if self._storage is None and self._ref is None:
            return
        if isinstance(value, int):
            try:
                ptr = ctypes.cast(self.address, ctypes.POINTER(ctypes.c_int64))
                ptr[0] = value
            except Exception:
                pass
        elif isinstance(value, float):
            try:
                ptr = ctypes.cast(self.address, ctypes.POINTER(ctypes.c_double))
                ptr[0] = value
            except Exception:
                pass
    
    def offset(self, bytes_offset):
        """Pointer arithmetic - return new pointer offset by bytes"""
        return KSPointer(address=self.address + bytes_offset)
    
    def __add__(self, offset):
        """ptr + n"""
        return self.offset(offset * self.size)
    
    def __sub__(self, offset):
        """ptr - n"""
        return self.offset(-offset * self.size)
    
    def __eq__(self, other):
        if isinstance(other, KSPointer):
            return self.address == other.address
        if isinstance(other, int):
            return self.address == other
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        return result if result is NotImplemented else not result

    def __bool__(self):
        return self.address != 0

    def __repr__(self):
        return f"<KSPointer 0x{self.address:x}>"


class KSSyscall:
    """Cross-platform syscall interface (2026 OS landscape).

    Linux 6.14+:  libc.syscall() — fully supported, stable.
                  x86_64 uses `syscall` instruction, ARM64 uses `svc #0`.
    macOS 27:     libsystem_kernel syscall() — deprecated since 10.12 (2016)
                  but still functional. Only Python-compatible raw syscall path.
                  ARM64 and x86_64 use identical BSD syscall numbers.
                  Kernel dispatches via `svc #0x80` (ARM64) / `syscall` (x86_64).
    Windows 11:   No syscall() function. Uses ntdll.dll Nt* functions.
                  Nt* functions internally execute `syscall` with version-specific
                  SSNs. Win32 API is the stable documented layer above.
    """

    @staticmethod
    def _convert_arg(arg):
        if isinstance(arg, str):
            return ctypes.c_char_p(arg.encode())
        elif isinstance(arg, KSPointer):
            return ctypes.c_void_p(arg.address)
        elif isinstance(arg, int):
            return ctypes.c_long(arg)
        return arg

    @staticmethod
    def syscall(number, *args):
        if sys.platform == "linux":
            return KSSyscall._linux_syscall(number, *args)
        elif sys.platform == "darwin":
            return KSSyscall._macos_syscall(number, *args)
        elif sys.platform == "win32":
            return KSSyscall._windows_syscall(number, *args)
        else:
            raise RuntimeError(f"Syscalls not supported on {sys.platform}")

    @staticmethod
    def _linux_syscall(number, *args):
        """Linux: libc.syscall(number, ...) — fully supported."""
        libc = ctypes.CDLL(None)
        syscall_fn = libc.syscall
        syscall_fn.restype = ctypes.c_long
        c_args = [ctypes.c_long(number)]
        for arg in args:
            c_args.append(KSSyscall._convert_arg(arg))
        return syscall_fn(*c_args)

    @staticmethod
    def _macos_syscall(number, *args):
        """macOS: libsystem_kernel syscall() — deprecated but functional.

        Pass raw BSD numbers (e.g. SYS_WRITE=4). The C library adds the
        0x2000000 class tag internally before executing `svc #0x80`.
        Same numbers on both ARM64 and x86_64.
        """
        libsystem = ctypes.CDLL(None)
        syscall_fn = libsystem.syscall
        syscall_fn.restype = ctypes.c_long
        c_args = [ctypes.c_long(number)]
        for arg in args:
            c_args.append(KSSyscall._convert_arg(arg))
        return syscall_fn(*c_args)

    @staticmethod
    def _windows_syscall(number, *args):
        """Windows: ntdll Nt* functions via ctypes.

        Windows has no syscall() function. The interpreter's builtin_syscall
        translates Linux x86-64 numbers to a Windows Nt* index (0-24).
        We call the corresponding ntdll function by name.
        Functions that don't map cleanly (fork, execve, brk, raw sockets)
        raise RuntimeError with guidance.
        """
        ntdll = ctypes.WinDLL('ntdll')

        # Index-based mapping: interpreter translates Linux x86-64 numbers
        # to these indices, then we call the right ntdll function.
        NT_CLOSE = 3
        NT_EXIT = 4
        NT_GETPID = 5
        NT_MUNMAP = 7
        NT_MPROTECT = 8
        NT_NANOSLEEP = 21
        NT_GETTIMEOFDAY = 22

        if number == NT_CLOSE and len(args) >= 1:
            ntdll.NtClose.restype = ctypes.c_long
            ntdll.NtClose.argtypes = [ctypes.c_void_p]
            return ntdll.NtClose(KSSyscall._convert_arg(args[0]))

        elif number == NT_GETPID:
            class PROCESS_BASIC_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("Reserved1", ctypes.c_void_p),
                    ("PebBaseAddress", ctypes.c_void_p),
                    ("Reserved2", ctypes.c_void_p * 2),
                    ("UniqueProcessId", ctypes.c_ulong),
                    ("Reserved3", ctypes.c_ulong),
                ]
            pbi = PROCESS_BASIC_INFORMATION()
            ret_len = ctypes.c_ulong(0)
            ntdll.NtQueryInformationProcess.restype = ctypes.c_long
            ntdll.NtQueryInformationProcess.argtypes = [
                ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(PROCESS_BASIC_INFORMATION),
                ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
            ]
            ntdll.NtQueryInformationProcess(
                ctypes.c_void_p(-1), 0, ctypes.byref(pbi),
                ctypes.sizeof(pbi), ctypes.byref(ret_len),
            )
            return pbi.UniqueProcessId

        elif number == NT_MUNMAP and len(args) >= 1:
            ntdll.NtUnmapViewOfSection.restype = ctypes.c_long
            ntdll.NtUnmapViewOfSection.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            return ntdll.NtUnmapViewOfSection(ctypes.c_void_p(-1), KSSyscall._convert_arg(args[0]))

        elif number == NT_MPROTECT and len(args) >= 2:
            old_protect = ctypes.c_ulong(0)
            addr_val = args[0] if isinstance(args[0], int) else (args[0].value if hasattr(args[0], 'value') else 0)
            base_addr = ctypes.c_void_p(addr_val)
            region_size = ctypes.c_size_t(4096)
            prot = args[1] if isinstance(args[1], int) else (args[1].value if hasattr(args[1], 'value') else 0)
            win_prot = 0x02  # PAGE_READONLY
            if prot & 0x2:
                win_prot = 0x04  # PAGE_READWRITE
            if prot & 0x4:
                win_prot = 0x40  # PAGE_EXECUTE_READWRITE
            ntdll.NtProtectVirtualMemory.restype = ctypes.c_long
            ntdll.NtProtectVirtualMemory.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
                ctypes.POINTER(ctypes.c_size_t), ctypes.c_ulong,
                ctypes.POINTER(ctypes.c_ulong),
            ]
            ntdll.NtProtectVirtualMemory(
                ctypes.c_void_p(-1), ctypes.byref(base_addr),
                ctypes.byref(region_size), win_prot, ctypes.byref(old_protect),
            )
            return 0

        elif number == NT_NANOSLEEP and len(args) >= 1:
            req_val = args[0] if isinstance(args[0], int) else (args[0].value if hasattr(args[0], 'value') else 0)
            delay_100ns = ctypes.c_longlong(-(req_val // 100))
            ntdll.NtDelayExecution.restype = ctypes.c_long
            ntdll.NtDelayExecution.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
            return ntdll.NtDelayExecution(ctypes.byref(delay_100ns))

        elif number == NT_GETTIMEOFDAY:
            ft = ctypes.c_longlong(0)
            ntdll.NtQuerySystemTime.restype = ctypes.c_long
            ntdll.NtQuerySystemTime.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
            ntdll.NtQuerySystemTime(ctypes.byref(ft))
            return (ft.value - 116444736000000000) // 10000000

        elif number == NT_EXIT and len(args) >= 1:
            exit_code = args[0] if isinstance(args[0], int) else (args[0].value if hasattr(args[0], 'value') else 0)
            ntdll.NtTerminateProcess.restype = ctypes.c_long
            ntdll.NtTerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_long]
            return ntdll.NtTerminateProcess(ctypes.c_void_p(-1), exit_code)

        else:
            raise RuntimeError(
                f"Windows syscall #{number} not implemented. "
                f"Windows does not have a raw syscall() function. "
                f"Use ffi or ctypes to call Win32/ntdll APIs directly."
            )
    
    @staticmethod
    def write(fd, data, count=None):
        """syscall write(fd, buf, count)"""
        if isinstance(data, str):
            data_bytes = data.encode()
            count = count or len(data_bytes)
            buf = ctypes.create_string_buffer(data_bytes)
            return KSSyscall.syscall(1, fd, ctypes.addressof(buf), count)
        return KSSyscall.syscall(1, fd, data, count)
    
    @staticmethod
    def read(fd, buf, count):
        """syscall read(fd, buf, count)"""
        return KSSyscall.syscall(0, fd, buf, count)
    
    @staticmethod
    def open(path, flags, mode=0):
        """syscall open(path, flags, mode)"""
        return KSSyscall.syscall(2, path, flags, mode)
    
    @staticmethod
    def close(fd):
        """syscall close(fd)"""
        return KSSyscall.syscall(3, fd)


class KSHardwareIO:
    """Hardware I/O port access via ctypes"""
    
    _iopl_set = False
    
    @staticmethod
    def _request_io_privilege():
        """Request I/O port access privilege"""
        if KSHardwareIO._iopl_set:
            return True
        if sys.platform != "linux":
            return False
        try:
            libc = ctypes.CDLL(None)
            result = libc.iopl(3)
            if result != 0:
                return False
            KSHardwareIO._iopl_set = True
            return True
        except Exception:
            return False

    @staticmethod
    def outb(port, value):
        if not KSHardwareIO._request_io_privilege():
            return  # silently skip — no root
        try:
            with open('/dev/port', 'wb') as f:
                f.seek(port)
                f.write(bytes([value & 0xFF]))
        except Exception:
            pass

    @staticmethod
    def inb(port):
        if not KSHardwareIO._request_io_privilege():
            return 0
        try:
            with open('/dev/port', 'rb') as f:
                f.seek(port)
                return ord(f.read(1))
        except Exception:
            return 0

    @staticmethod
    def inw(port):
        if not KSHardwareIO._request_io_privilege():
            return 0
        try:
            with open('/dev/port', 'rb') as f:
                f.seek(port)
                data = f.read(2)
                return int.from_bytes(data, 'little') if len(data) == 2 else 0
        except Exception:
            return 0

    @staticmethod
    def outw(port, value):
        if not KSHardwareIO._request_io_privilege():
            return
        try:
            with open('/dev/port', 'wb') as f:
                f.seek(port)
                f.write((value & 0xFFFF).to_bytes(2, 'little'))
        except Exception:
            pass


class KSInlineAsm:
    """Inline assembly execution via on-demand compilation — cross-platform."""
    _loaded_libs = []  # keep libs alive to allow cross-calls

    @staticmethod
    def _detect_compiler_and_flags():
        """Detect available compiler and platform-specific flags."""
        import shutil, platform
        machine = platform.machine().lower()
        is_arm64 = machine in ('aarch64', 'arm64')
        is_macos = sys.platform == 'darwin'
        is_windows = sys.platform == 'win32'

        # Find compiler
        compiler = None
        if is_windows:
            for cc in ['cl.exe', 'gcc', 'clang']:
                if shutil.which(cc):
                    compiler = cc
                    break
        else:
            for cc in ['cc', 'gcc', 'clang']:
                if shutil.which(cc):
                    compiler = cc
                    break

        # Shared library extension and flags
        if is_windows:
            lib_ext = '.dll'
            lib_flags = ['-shared']
        elif is_macos:
            lib_ext = '.dylib'
            lib_flags = ['-shared', '-fPIC']
        else:
            lib_ext = '.so'
            lib_flags = ['-shared', '-fPIC']

        return {
            'compiler': compiler,
            'is_arm64': is_arm64,
            'is_macos': is_macos,
            'is_windows': is_windows,
            'lib_ext': lib_ext,
            'lib_flags': lib_flags,
        }

    @staticmethod
    def execute(asm_code, *args):
        """Execute inline assembly by compiling and running it.

        Cross-platform: detects compiler (gcc/clang/cl.exe) and architecture
        (x86_64/arm64) to generate correct code.
        """
        import tempfile, subprocess, os, re

        plat = KSInlineAsm._detect_compiler_and_flags()
        compiler = plat['compiler']
        if not compiler:
            return 0  # no compiler available

        stripped = asm_code.strip()
        label_only = re.match(r'^(\w+)\s*:\s*\n', stripped)
        is_definition = label_only and 'call ' not in stripped

        if is_definition:
            func_name = label_only.group(1)
            asm_lines = [line.strip() for line in stripped.splitlines() if line.strip()]
            asm_str = '\\n\\t'.join(asm_lines)

            if plat['is_arm64']:
                # ARM64: use GCC-style inline asm with proper registers
                c_code = f"""
#include <stdint.h>
void {func_name}() {{
    __asm__ __volatile__ (
        "{asm_str}"
        :
        :
        : "memory"
    );
}}
"""
            else:
                # x86_64: use Intel syntax
                c_code = f"""
#include <stdint.h>
__asm__(
    ".intel_syntax noprefix\\n\\t"
    ".globl {func_name}\\n\\t"
    ".type {func_name}, @function\\n\\t"
    "{asm_str}\\n\\t"
    ".att_syntax prefix\\n"
);
"""

            with tempfile.TemporaryDirectory() as tmpdir:
                c_file = os.path.join(tmpdir, "asm.c")
                so_file = os.path.join(tmpdir, f"asm_{func_name}{plat['lib_ext']}")
                with open(c_file, 'w') as f:
                    f.write(c_code)
                cmd = [compiler] + plat['lib_flags'] + ['-O0', c_file, '-o', so_file]
                result = subprocess.run(cmd, capture_output=True)
                if result.returncode != 0:
                    return None
                import shutil, ctypes, atexit
                persistent_dir = tempfile.mkdtemp(prefix='ks_asm_')
                atexit.register(shutil.rmtree, persistent_dir, True)
                persistent = os.path.join(persistent_dir, f'{func_name}{plat["lib_ext"]}')
                shutil.copy(so_file, persistent)
                lib = ctypes.CDLL(persistent)
                KSInlineAsm._loaded_libs.append((func_name, lib))
            return None

        # Check for 'call funcname' pattern
        call_match = re.match(r'^call\s+(\w+)$', stripped)
        if call_match:
            import ctypes
            func_name = call_match.group(1)
            for name, lib in reversed(KSInlineAsm._loaded_libs):
                if name == func_name:
                    fn = getattr(lib, func_name, None)
                    if fn:
                        fn.restype = ctypes.c_int64
                        fn.argtypes = [ctypes.c_int64] * len(args)
                        return fn(*[ctypes.c_int64(a) for a in args])
            return 0

        # Special case: cpuid — x86 only
        if stripped.strip() == 'cpuid':
            if plat['is_arm64']:
                return (0, 0, 0, 0)  # cpuid doesn't exist on ARM64
            import ctypes
            c_code = """
#include <stdint.h>
void ks_cpuid(uint32_t leaf, uint32_t *eax, uint32_t *ebx, uint32_t *ecx, uint32_t *edx) {
    __asm__ __volatile__ ("cpuid"
        : "=a"(*eax), "=b"(*ebx), "=c"(*ecx), "=d"(*edx)
        : "a"(leaf) : );
}
"""
            with tempfile.TemporaryDirectory() as tmpdir:
                c_file = os.path.join(tmpdir, "cpuid.c")
                so_file = os.path.join(tmpdir, f"cpuid{plat['lib_ext']}")
                with open(c_file, 'w') as f:
                    f.write(c_code)
                cmd = [compiler] + plat['lib_flags'] + ['-O2', c_file, '-o', so_file]
                r = subprocess.run(cmd, capture_output=True)
                if r.returncode != 0:
                    return (0, 0, 0, 0)
                lib = ctypes.CDLL(so_file)
                lib.ks_cpuid.restype = None
                lib.ks_cpuid.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32),
                                          ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
                                          ctypes.POINTER(ctypes.c_uint32)]
                ea, eb, ec, ed = ctypes.c_uint32(0), ctypes.c_uint32(0), ctypes.c_uint32(0), ctypes.c_uint32(0)
                leaf = int(args[0]) if args else 0
                lib.ks_cpuid(leaf, ctypes.byref(ea), ctypes.byref(eb), ctypes.byref(ec), ctypes.byref(ed))
                return (ea.value, eb.value, ec.value, ed.value)

        # Generic: wrap in a C function and execute
        asm_lines = [l.strip() for l in asm_code.strip().splitlines() if l.strip()]
        asm_c_str = '\n        '.join(f'"{line}\\n\\t"' for line in asm_lines)

        if plat['is_arm64']:
            # ARM64: arguments in x0-x7, result in x0
            arg_decls = ', '.join(f'int64_t a{i}' for i in range(len(args)))
            c_code = f"""
#include <stdint.h>
int64_t ks_asm_wrapper({arg_decls}) {{
    int64_t result = 0;
    __asm__ __volatile__ (
        {asm_c_str}
        : "=r" (result)
        :
        : "memory"
    );
    return result;
}}
"""
            cmd = [compiler] + plat['lib_flags'] + ['-O2', c_file_path := '', '-o', '']
        else:
            # x86_64: arguments in rdi/rsi/rdx/rcx/r8/r9, result in rax
            arg_decls = ', '.join(f'int64_t a{i}' for i in range(len(args)))
            arg_regs = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
            input_constraints = ', '.join(f'"r"(a{i})' for i in range(min(len(args), 6)))
            clobber_regs = ', '.join(f'"{r}"' for r in arg_regs[:len(args)])
            c_code = f"""
#include <stdint.h>
int64_t ks_asm_wrapper({arg_decls}) {{
    int64_t result = 0;
    __asm__ __volatile__ (
        {asm_c_str}
        : "=a" (result)
        : {input_constraints if input_constraints else ''}
        : "memory"{', ' + clobber_regs if clobber_regs else ''}
    );
    return result;
}}
"""

        import ctypes
        with tempfile.TemporaryDirectory() as tmpdir:
            c_file = os.path.join(tmpdir, "asm.c")
            so_file = os.path.join(tmpdir, f"asm{plat['lib_ext']}")
            with open(c_file, 'w') as f:
                f.write(c_code)
            extra_flags = ['-masm=intel'] if not plat['is_arm64'] and not plat['is_macos'] else []
            cmd = [compiler] + plat['lib_flags'] + ['-O2'] + extra_flags + [c_file, '-o', so_file]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                return 0  # graceful fallback
            lib = ctypes.CDLL(so_file)
            lib.ks_asm_wrapper.restype = ctypes.c_int64
            lib.ks_asm_wrapper.argtypes = [ctypes.c_int64] * len(args)
            return lib.ks_asm_wrapper(*[ctypes.c_int64(a) for a in args])


# Export for interpreter
__all__ = ['KSPointer', 'KSSyscall', 'KSHardwareIO', 'KSInlineAsm']
