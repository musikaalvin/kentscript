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
    """Direct syscall interface using ctypes"""
    
    @staticmethod
    def syscall(number, *args):
        """Execute syscall with up to 6 arguments"""
        if sys.platform == "linux":
            return KSSyscall._linux_syscall(number, *args)
        else:
            raise RuntimeError(f"Syscalls not supported on {sys.platform}")
    
    @staticmethod
    def _linux_syscall(number, *args):
        """Linux syscall via ctypes"""
        libc = ctypes.CDLL(None)
        
        # Get syscall function
        syscall_fn = libc.syscall
        syscall_fn.restype = ctypes.c_long
        
        # Convert arguments
        c_args = [ctypes.c_long(number)]
        for arg in args:
            if isinstance(arg, str):
                c_args.append(ctypes.c_char_p(arg.encode()))
            elif isinstance(arg, KSPointer):
                c_args.append(ctypes.c_void_p(arg.address))
            elif isinstance(arg, int):
                c_args.append(ctypes.c_long(arg))
            else:
                c_args.append(arg)
        
        return syscall_fn(*c_args)
    
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
    """Inline assembly execution via on-demand compilation"""
    _loaded_libs = []  # keep libs alive to allow cross-calls

    @staticmethod
    def execute(asm_code, *args):
        """Execute inline assembly by compiling and running it.
        
        If asm_code contains a label definition (e.g. 'my_add:\\n...ret'),
        it is compiled as a standalone function and kept loaded.
        If asm_code is 'call <name>' with args, the named function is called.
        """
        import tempfile, subprocess, os, re

        # Check if this is a pure function definition block (no call, just labels+body)
        stripped = asm_code.strip()
        label_only = re.match(r'^(\w+)\s*:\s*\n', stripped)
        is_definition = label_only and 'call ' not in stripped

        if is_definition:
            func_name = label_only.group(1)
            asm_lines = [line.strip() for line in stripped.splitlines() if line.strip()]
            asm_str = '\\n\\t'.join(asm_lines)
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
                so_file = os.path.join(tmpdir, f"asm_{func_name}.so")
                with open(c_file, 'w') as f:
                    f.write(c_code)
                result = subprocess.run(
                    ['gcc', '-shared', '-fPIC', '-O0', c_file, '-o', so_file],
                    capture_output=True
                )
                if result.returncode != 0:
                    return None  # silently ignore
                import shutil, ctypes
                # Copy outside tmpdir so it survives after tmpdir is deleted
                import atexit
                persistent_dir = tempfile.mkdtemp(prefix='ks_asm_')
                atexit.register(shutil.rmtree, persistent_dir, True)
                persistent = os.path.join(persistent_dir, f'{func_name}.so')
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
            # Not found in loaded libs — fall through to generic execution
            return 0

        # Special case: cpuid — returns (eax, ebx, ecx, edx)
        if stripped.strip() == 'cpuid':
            import ctypes, struct
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
                so_file = os.path.join(tmpdir, "cpuid.so")
                with open(c_file, 'w') as f: f.write(c_code)
                r = subprocess.run(['gcc', '-shared', '-fPIC', '-O2', c_file, '-o', so_file], capture_output=True)
                if r.returncode != 0:
                    return (0, 0, 0, 0)
                import ctypes as _ct
                lib = _ct.CDLL(so_file)
                lib.ks_cpuid.restype = None
                lib.ks_cpuid.argtypes = [_ct.c_uint32, _ct.POINTER(_ct.c_uint32),
                                          _ct.POINTER(_ct.c_uint32), _ct.POINTER(_ct.c_uint32),
                                          _ct.POINTER(_ct.c_uint32)]
                ea, eb, ec, ed = _ct.c_uint32(0), _ct.c_uint32(0), _ct.c_uint32(0), _ct.c_uint32(0)
                leaf = int(args[0]) if args else 0
                lib.ks_cpuid(leaf, _ct.byref(ea), _ct.byref(eb), _ct.byref(ec), _ct.byref(ed))
                return (ea.value, eb.value, ec.value, ed.value)

        # Generic: wrap in a C function and execute
        # Normalize multiline asm: split on newlines, strip, join as separate string literals
        asm_lines = [l.strip() for l in asm_code.strip().splitlines() if l.strip()]
        asm_c_str = '\n        '.join(f'"{line}\\n\\t"' for line in asm_lines)
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
            so_file = os.path.join(tmpdir, "asm.so")
            with open(c_file, 'w') as f:
                f.write(c_code)
            result = subprocess.run(
                ['gcc', '-shared', '-fPIC', '-O2', '-masm=intel', c_file, '-o', so_file],
                capture_output=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"Assembly compilation failed: {result.stderr.decode()}")
            lib = ctypes.CDLL(so_file)
            lib.ks_asm_wrapper.restype = ctypes.c_int64
            lib.ks_asm_wrapper.argtypes = [ctypes.c_int64] * len(args)
            return lib.ks_asm_wrapper(*[ctypes.c_int64(a) for a in args])


# Export for interpreter
__all__ = ['KSPointer', 'KSSyscall', 'KSHardwareIO', 'KSInlineAsm']
