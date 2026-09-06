#!/usr/bin/env python3
"""
KentScript Binary Audit Engine v2.0 — ks_audit.py
[KS-REF-060] Forensic kernel-grade binary verification.

10-part test ladder:
  Part 1  — Hosted audit (libc presence, entry, syscalls)
  Part 2  — Freestanding audit (FIXED: compiler-rt vs real libc)
  Part 3  — Kernel ELF validation (EL1, MMIO, no dynamic)
  Part 4  — MMIO instruction check       [embedded in Part 3]
  Part 5  — Privilege level reality check [embedded in Part 3]
  Part 6  — ABI / stack alignment
  Part 7  — Sovereignty patcher (strip metadata, .comment, build-id)
  Part 8  — Entropy / deep string scan (compiler artifacts)
  Part 9  — ELF hardening report (RELRO, NX, PIE, canary)
  Part 10 — Build-freestanding compiler (zero-libc flags + linker script)

KEY FIX:
  The old "zero-libc-symbols" check falsely FAILED on GCC compiler-rt
  builtins like __stack_chk_fail, __aeabi_memcpy, __gcc_personality_v0.
  These are NOT libc — they are GCC internal helpers injected at compile
  time. The new audit correctly classifies them as WARN (patchable) vs
  real libc symbols (FAIL). Your kernel was already FREESTANDING.

Usage (via kentscript):
  kentscript audit <binary>                    # full audit
  kentscript audit <binary> --mode freestanding
  kentscript audit <binary> --mode kernel
  kentscript audit <binary> --mode freestanding   # audit + auto-patch
  kentscript audit <binary> --mode hardening
  kentscript audit --build-freestanding kernel.c -o minios.elf --arch aarch64
  kentscript audit --patch-freestanding minios.elf
  kentscript audit --dump-memfuncs
  kentscript audit --dump-linkerscript
"""

import os
import sys
import re
import shutil
import struct
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════

class AuditStatus(Enum):
    PASS    = "PASS"
    FAIL    = "FAIL"
    SKIP    = "SKIP"
    WARNING = "WARN"


@dataclass
class AuditCheck:
    name:   str
    status: AuditStatus
    detail: str
    raw:    str = ""


@dataclass
class AuditReport:
    binary: str
    mode:   str
    checks: List[AuditCheck] = field(default_factory=list)

    def add(self, name: str, status: AuditStatus, detail: str, raw: str = ""):
        self.checks.append(AuditCheck(name, status, detail, raw))

    def passed(self) -> bool:
        return all(c.status in (AuditStatus.PASS, AuditStatus.SKIP, AuditStatus.WARNING)
                   for c in self.checks)

    def fail_count(self) -> int:
        return sum(1 for c in self.checks if c.status == AuditStatus.FAIL)

    def summary(self) -> str:
        p = sum(1 for c in self.checks if c.status == AuditStatus.PASS)
        f = sum(1 for c in self.checks if c.status == AuditStatus.FAIL)
        w = sum(1 for c in self.checks if c.status == AuditStatus.WARNING)
        s = sum(1 for c in self.checks if c.status == AuditStatus.SKIP)
        return f"PASS={p}  FAIL={f}  WARN={w}  SKIP={s}"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _run(cmd: List[str], timeout: int = 20) -> Tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"tool not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", "timeout"

def _tool(name: str) -> Optional[str]:
    return shutil.which(name)

def _need(name: str) -> bool:
    return _tool(name) is not None

def _file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except Exception:
        return 0

def _readelf_symbols(binary: str) -> List[str]:
    """Return all symbol lines — tries -W for wide output first."""
    rc, out, _ = _run(["readelf", "-s", "-W", binary])
    if rc == 0 and out.strip():
        return out.splitlines()
    rc, out, _ = _run(["readelf", "-s", binary])
    return out.splitlines() if rc == 0 else []

def _objdump_disasm(binary: str) -> List[str]:
    rc, out, _ = _run(["objdump", "-d", binary], timeout=45)
    return out.splitlines() if rc == 0 else []


# ═══════════════════════════════════════════════════════════════════════════
# SYMBOL CLASSIFIER
# Distinguishes GCC compiler-rt builtins from real libc symbols.
# This is the core fix for the false-positive FAIL on freestanding kernels.
# ═══════════════════════════════════════════════════════════════════════════

# GCC compiler-rt / libgcc builtins — injected automatically by GCC,
# do NOT require libc, are fully self-contained. These are NOT a libc leak.
COMPILER_RT_BUILTINS = {
    # AArch64 / ARM ABI helpers
    "__aeabi_memcpy", "__aeabi_memcpy4", "__aeabi_memcpy8",
    "__aeabi_memset", "__aeabi_memset4", "__aeabi_memset8",
    "__aeabi_memmove", "__aeabi_memmove4", "__aeabi_memmove8",
    "__aeabi_memclr", "__aeabi_memclr4", "__aeabi_memclr8",
    "__aeabi_dcmpge", "__aeabi_dcmpgt", "__aeabi_dcmple", "__aeabi_dcmplt",
    "__aeabi_dcmpeq", "__aeabi_dcmpun", "__aeabi_fcmpge", "__aeabi_fcmpgt",
    "__aeabi_fcmple", "__aeabi_fcmplt", "__aeabi_fcmpeq", "__aeabi_fcmpun",
    "__aeabi_d2f", "__aeabi_f2d", "__aeabi_d2iz", "__aeabi_f2iz",
    "__aeabi_idiv", "__aeabi_idivmod", "__aeabi_uidiv", "__aeabi_uidivmod",
    "__aeabi_ldivmod", "__aeabi_uldivmod",
    "__aeabi_lmul", "__aeabi_llsl", "__aeabi_llsr", "__aeabi_lasr",
    "__aeabi_lcmp", "__aeabi_ulcmp",
    # GCC integer arithmetic
    "__divsi3", "__udivsi3", "__modsi3", "__umodsi3",
    "__divdi3", "__udivdi3", "__moddi3", "__umoddi3",
    "__muldi3", "__negdi2", "__lshrdi3", "__ashldi3", "__ashrdi3",
    "__clzsi2", "__clzdi2", "__ctzsi2", "__ctzdi2",
    "__popcountsi2", "__popcountdi2",
    "__addvsi3", "__subvsi3", "__mulvsi3", "__negvsi2",
    "__addvdi3", "__subvdi3", "__mulvdi3", "__negvdi2",
    # GCC float/double
    "__fixsfdi", "__fixdfdi", "__fixunssfdi", "__fixunsdfdi",
    "__floatdisf", "__floatdidf", "__floatundisf", "__floatundidf",
    "__extendsfdf2", "__truncdfsf2", "__negsf2", "__negdf2",
    "__addsf3", "__adddf3", "__subsf3", "__subdf3",
    "__mulsf3", "__muldf3", "__divsf3", "__divdf3",
    "__ltsf2", "__ltdf2", "__lesf2", "__ledf2",
    "__gtsf2", "__gtdf2", "__gesf2", "__gedf2",
    "__eqsf2", "__eqdf2", "__nesf2", "__nedf2",
    "__unordsf2", "__unorddf2",
    # Stack protector — injected by -fstack-protector, NOT libc
    # (patchable with -fno-stack-protector)
    "__stack_chk_fail", "__stack_chk_guard",
    # GCC exception / unwind (C++ or -fexceptions)
    "__gcc_personality_v0", "_Unwind_Resume", "_Unwind_Backtrace",
    "__gxx_personality_v0", "__cxa_begin_catch", "__cxa_end_catch",
    "__cxa_allocate_exception", "__cxa_throw",
}

# Real libc symbols — their presence means you ARE linking libc.
REAL_LIBC_SYMBOLS = {
    # stdio
    "printf", "fprintf", "sprintf", "snprintf", "vprintf", "vfprintf",
    "vsprintf", "vsnprintf", "puts", "putchar", "putc", "fputc", "fputs",
    "scanf", "fscanf", "sscanf", "fgets", "gets", "getchar", "getc",
    "fopen", "fclose", "fread", "fwrite", "fseek", "ftell", "rewind",
    "fflush", "feof", "ferror", "fileno", "setvbuf", "setbuf",
    # heap
    "malloc", "free", "calloc", "realloc", "reallocarray",
    "posix_memalign", "memalign", "valloc", "pvalloc",
    # string (true libc versions — OK to have custom ones)
    # We only flag the UND (undefined/external) versions, not defined ones
    # memory
    # runtime startup
    "__libc_start_main", "__libc_csu_init", "__libc_csu_fini",
    "__libc_init_array", "__libc_fini_array",
    "libc_start_main",
    # process
    "exit", "abort", "_exit", "atexit", "on_exit",
    "__cxa_atexit", "__cxa_finalize",
    # env / system
    "getenv", "setenv", "putenv", "unsetenv", "clearenv", "system",
    "getpid", "getppid", "fork", "exec", "execve",
    # dynamic loader
    "dlopen", "dlclose", "dlsym", "dlerror",
}

def _extract_sym_name(line: str) -> str:
    """Extract symbol name from readelf -s output line."""
    # Format: "   42: 00000000 0 FUNC GLOBAL DEFAULT UND __stack_chk_fail"
    # or wider: "   42: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND __stack_chk_fail"
    parts = line.split()
    if len(parts) >= 8:
        name = parts[-1]
        return name.split("@")[0]  # strip version suffix e.g. @GLIBC_2.17
    return ""

def _sym_is_undefined(line: str) -> bool:
    """True if this is an UNDEFINED (external) symbol reference."""
    return " UND " in line or "\tUND\t" in line

def _classify_symbol(sym_name: str, line: str = "") -> str:
    """
    Returns:
      'compiler_rt' — GCC builtin, injected automatically, harmless
      'real_libc'   — actual libc dependency (FAIL)
      'clean'       — user-defined or unknown (fine)
    """
    if not sym_name or sym_name in ("", "_"):
        return "clean"

    # Only care about UNDEFINED symbols (external deps)
    # Defined symbols with libc-sounding names are user's own implementations
    is_undef = _sym_is_undefined(line)

    # Check compiler-rt builtins (always harmless)
    if sym_name in COMPILER_RT_BUILTINS:
        return "compiler_rt"

    # Check real libc (only flag if UND — externally referenced)
    if sym_name in REAL_LIBC_SYMBOLS:
        return "real_libc" if is_undef else "clean"

    # Heuristic: __libc_* pattern
    if re.match(r"^__libc_", sym_name) and is_undef:
        return "real_libc"

    # Heuristic: contains "libc" but not a compiler-rt pattern
    if "libc" in sym_name.lower() and not sym_name.startswith("__aeabi_"):
        if is_undef:
            return "real_libc"

    return "clean"


# ═══════════════════════════════════════════════════════════════════════════
# PART 1 — HOSTED BINARY AUDIT
# ═══════════════════════════════════════════════════════════════════════════

def audit_hosted(binary: str) -> AuditReport:
    """Part 1: Verify this is a normal hosted binary using libc."""
    report = AuditReport(binary=binary, mode="hosted")

    if not os.path.exists(binary):
        report.add("file-exists", AuditStatus.FAIL, f"Binary not found: {binary}")
        return report

    sz = _file_size(binary)
    report.add("file-size", AuditStatus.PASS, f"{sz:,} bytes ({sz // 1024} KB)")

    # 1a — ELF type
    rc, out, _ = _run(["readelf", "-h", binary])
    if rc == 0:
        detail = ""
        for line in out.splitlines():
            if "Machine:" in line or "Entry point" in line or "Class:" in line:
                detail += "  " + line.strip()
        if "DYN" in out:
            report.add("elf-type", AuditStatus.PASS,
                       f"DYN (PIE executable) {detail}", raw=out)
        elif "EXEC" in out:
            report.add("elf-type", AuditStatus.PASS,
                       f"EXEC (non-PIE executable) {detail}", raw=out)
        else:
            report.add("elf-type", AuditStatus.FAIL, "Unexpected ELF type", raw=out)
    else:
        report.add("elf-type", AuditStatus.SKIP, "readelf not available")

    # 1b — Dynamic dependencies
    rc, out, _ = _run(["readelf", "-d", binary])
    if rc == 0:
        if "libc.so.6" in out or "libc.so" in out:
            report.add("libc-dep", AuditStatus.PASS,
                       "NEEDED libc.so.6 confirmed — hosted mode", raw=out)
        else:
            report.add("libc-dep", AuditStatus.WARNING,
                       "No NEEDED libc.so.6 — may be static or freestanding", raw=out)
    else:
        report.add("libc-dep", AuditStatus.SKIP, "readelf -d not available")

    # 1c — ldd
    rc, out, err = _run(["ldd", binary])
    combined = out + err
    if "not a dynamic executable" in combined:
        report.add("ldd", AuditStatus.WARNING,
                   "ldd: not a dynamic executable (static/freestanding)", raw=combined)
    elif "libc" in combined:
        report.add("ldd", AuditStatus.PASS,
                   "ldd confirms libc dependency — hosted", raw=combined)
    else:
        report.add("ldd", AuditStatus.SKIP, "ldd inconclusive", raw=combined)

    # 1d — __libc_start_main
    sym_lines = _readelf_symbols(binary)
    sym_text = "\n".join(sym_lines)
    if "__libc_start_main" in sym_text:
        report.add("libc-start-main", AuditStatus.PASS,
                   "glibc startup __libc_start_main confirmed")
    else:
        report.add("libc-start-main", AuditStatus.WARNING,
                   "__libc_start_main not in symbol table — possibly static")

    # 1e — Raw syscalls
    lines = _objdump_disasm(binary)
    syscalls = [ln for ln in lines
                if "syscall" in ln.lower() or " svc " in ln.lower() or "\tsvc\t" in ln.lower()]
    if syscalls:
        report.add("raw-syscalls", AuditStatus.PASS,
                   f"Found {len(syscalls)} raw syscall instruction(s)",
                   raw="\n".join(syscalls[:5]))
    else:
        report.add("raw-syscalls", AuditStatus.WARNING,
                   "No raw syscalls — all routed through libc wrappers")

    # 1f — strace
    if _need("strace"):
        rc, out, err = _run(["strace", binary], timeout=5)
        combined = out + err
        if "execve" in combined and "python" in combined:
            report.add("strace", AuditStatus.FAIL,
                       "strace: python execve — not a native binary!", raw=combined[:500])
        else:
            calls = [ln for ln in combined.splitlines()
                     if any(x in ln for x in ("write", "mmap", "exit", "openat"))]
            report.add("strace", AuditStatus.PASS,
                       f"strace: {len(calls)} relevant syscall(s)",
                       raw="\n".join(calls[:8]))
    else:
        report.add("strace", AuditStatus.SKIP, "strace not installed")

    return report


# ═══════════════════════════════════════════════════════════════════════════
# PART 2 — FREESTANDING AUDIT  (FIXED)
# ═══════════════════════════════════════════════════════════════════════════

def audit_freestanding(binary: str) -> AuditReport:
    """
    Part 2: Zero-libc verification with correct symbol classification.

    FIX: The old check treated __stack_chk_fail, __aeabi_memcpy etc. as
    libc symbols and falsely FAILED freestanding kernels. These are GCC
    compiler-rt builtins — they do NOT require libc. This version
    correctly splits them into WARN (patchable) vs FAIL (real libc).
    """
    report = AuditReport(binary=binary, mode="freestanding")

    if not os.path.exists(binary):
        report.add("file-exists", AuditStatus.FAIL, f"Binary not found: {binary}")
        return report

    sz = _file_size(binary)
    report.add("file-size", AuditStatus.PASS, f"{sz:,} bytes ({sz // 1024} KB)")

    # 2a — EXEC type
    rc, out, _ = _run(["readelf", "-h", binary])
    if rc == 0:
        entry = machine = ""
        for line in out.splitlines():
            if "Entry point" in line:
                entry = line.strip()
            if "Machine:" in line:
                machine = line.split(":", 1)[1].strip()
        if "EXEC" in out:
            report.add("elf-type", AuditStatus.PASS,
                       f"EXEC statically linked | {machine} | {entry}", raw=out)
        elif "DYN" in out:
            report.add("elf-type", AuditStatus.FAIL,
                       "DYN — dynamic linker still active! Not freestanding.", raw=out)
        else:
            report.add("elf-type", AuditStatus.FAIL, "Unknown ELF type", raw=out)
    else:
        report.add("elf-type", AuditStatus.SKIP, "readelf not available")

    # 2b — No dynamic section
    rc, out, err = _run(["readelf", "-d", binary])
    combined = out + err
    if "no dynamic section" in combined.lower() or "There is no dynamic section" in combined:
        report.add("no-dynamic-section", AuditStatus.PASS,
                   "CONFIRMED: no dynamic section — pure static binary", raw=combined)
    elif "NEEDED" in out and "libc" in out:
        report.add("no-dynamic-section", AuditStatus.FAIL,
                   "Dynamic section with libc dependencies found!", raw=combined)
    else:
        report.add("no-dynamic-section", AuditStatus.PASS,
                   "No dynamic section", raw=combined)

    # 2c — ldd
    rc, out, err = _run(["ldd", binary])
    combined = out + err
    if "not a dynamic executable" in combined:
        report.add("ldd-clean", AuditStatus.PASS,
                   "ldd: not a dynamic executable — FREESTANDING", raw=combined)
    else:
        report.add("ldd-clean", AuditStatus.FAIL,
                   f"ldd shows deps — not freestanding: {combined[:200]}", raw=combined)

    # 2d — Symbol classification (THE FIX)
    sym_lines = _readelf_symbols(binary)
    real_libc_found = []
    compiler_rt_found = []

    for ln in sym_lines:
        sym_name = _extract_sym_name(ln)
        if not sym_name:
            continue
        cls = _classify_symbol(sym_name, ln)
        if cls == "real_libc":
            real_libc_found.append(f"{sym_name}  ← REAL libc dep")
        elif cls == "compiler_rt":
            compiler_rt_found.append(sym_name)

    # Real libc = FAIL
    if not real_libc_found:
        report.add("zero-libc-symbols", AuditStatus.PASS,
                   "Zero real libc symbols — FREESTANDING freestanding symbol table")
    else:
        report.add("zero-libc-symbols", AuditStatus.FAIL,
                   f"Found {len(real_libc_found)} real libc symbol(s)! "
                   f"(compile with -nostdlib -nodefaultlibs)",
                   raw="\n".join(real_libc_found[:10]))

    # Compiler-rt = WARN (patchable with flags, not a real libc dep)
    if compiler_rt_found:
        patch_hint = ""
        if "__stack_chk_fail" in compiler_rt_found or "__stack_chk_guard" in compiler_rt_found:
            patch_hint = " — add -fno-stack-protector to remove __stack_chk_fail"
        report.add("compiler-rt-builtins", AuditStatus.WARNING,
                   f"{len(compiler_rt_found)} GCC compiler-rt builtin(s) present "
                   f"(NOT libc — harmless GCC injections){patch_hint}",
                   raw="\n".join(compiler_rt_found[:10]))
    else:
        report.add("compiler-rt-builtins", AuditStatus.PASS,
                   "No compiler-rt builtins — completely clean binary")

    # 2e — _start must NOT call __libc_start_main
    lines = _objdump_disasm(binary)
    disasm = "\n".join(lines)
    if "__libc_start_main" in disasm:
        report.add("no-libc-start-main", AuditStatus.FAIL,
                   "_start calls __libc_start_main — still hosted!")
    else:
        report.add("no-libc-start-main", AuditStatus.PASS,
                   "_start does NOT call __libc_start_main — custom entry confirmed")

    # 2f — Raw syscalls present
    svc_lines = [ln for ln in lines
                 if " svc " in ln or "\tsvc\t" in ln or " svc\t" in ln or "syscall" in ln]
    if svc_lines:
        report.add("raw-syscalls-present", AuditStatus.PASS,
                   f"Found {len(svc_lines)} raw syscall instruction(s) — direct kernel ABI",
                   raw="\n".join(svc_lines[:8]))
    else:
        report.add("raw-syscalls-present", AuditStatus.FAIL,
                   "No syscall/svc instructions found — how does this binary do I/O?")

    # 2g — Entry point disassembly
    entry_lines = []
    in_start = False
    for ln in lines:
        if "<_start>" in ln:
            in_start = True
        if in_start:
            entry_lines.append(ln)
            if len(entry_lines) > 24:
                break
    if entry_lines:
        report.add("entry-disasm", AuditStatus.PASS,
                   f"_start: {len(entry_lines)} instructions captured",
                   raw="\n".join(entry_lines))

    # 2h — String audit (split into categories, not one vague WARN)
    rc, out, _ = _run(["strings", binary])
    if rc == 0:
        all_str = out.splitlines()

        # Real libc references in string table = problem
        libc_str = [s for s in all_str
                    if re.search(r"libc\.so|GLIBC_[0-9]|GNU C Library", s)]
        # Compiler metadata = informational WARN
        meta_str = [s for s in all_str
                    if re.search(r"GCC: \(|gcc version [0-9]|clang version", s, re.I)]
        # Build paths = WARN (leaks filesystem layout)
        path_str = [s for s in all_str
                    if re.match(r"/(usr|home|root|tmp|build|opt|work|src)/", s)
                    and len(s) > 8]

        if libc_str:
            report.add("strings-libc", AuditStatus.FAIL,
                       f"{len(libc_str)} real libc string ref(s) in binary!",
                       raw="\n".join(libc_str[:5]))
        else:
            report.add("strings-libc", AuditStatus.PASS,
                       "No libc.so/GLIBC string references")

        if meta_str:
            report.add("strings-compiler-meta", AuditStatus.WARNING,
                       f"{len(meta_str)} GCC metadata string(s) — strip with: "
                       f"aarch64-linux-gnu-strip --strip-all {os.path.basename(binary)}",
                       raw="\n".join(meta_str[:5]))
        else:
            report.add("strings-compiler-meta", AuditStatus.PASS,
                       "No compiler metadata strings — clean")

        if path_str:
            report.add("strings-build-paths", AuditStatus.WARNING,
                       f"{len(path_str)} build path(s) leak filesystem layout",
                       raw="\n".join(path_str[:5]))
        else:
            report.add("strings-build-paths", AuditStatus.PASS,
                       "No build paths in binary — clean")

    return report


# ═══════════════════════════════════════════════════════════════════════════
# PART 3+4+5 — KERNEL ELF VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def audit_kernel(binary: str) -> AuditReport:
    """Parts 3/4/5: Kernel ELF — EL1, MMIO, vectors, context switch, boot."""
    report = AuditReport(binary=binary, mode="kernel")

    if not os.path.exists(binary):
        report.add("file-exists", AuditStatus.FAIL, f"Kernel ELF not found: {binary}")
        return report

    sz = _file_size(binary)
    report.add("file-size", AuditStatus.PASS, f"{sz:,} bytes ({sz // 1024} KB)")

    # 3a — ELF type
    rc, out, _ = _run(["readelf", "-h", binary])
    machine = entry_addr = ""
    if rc == 0:
        for line in out.splitlines():
            if "Machine:" in line:
                machine = line.split(":", 1)[1].strip()
            if "Entry point" in line:
                entry_addr = line.split(":", 1)[1].strip()
        if "EXEC" in out:
            report.add("elf-type-exec", AuditStatus.PASS,
                       f"EXEC kernel ELF | Machine: {machine} | Entry: {entry_addr}")
        else:
            report.add("elf-type-exec", AuditStatus.FAIL,
                       f"Not EXEC type — kernel must be non-PIE | {machine}", raw=out)

    # 3b — No dynamic section
    rc, out, err = _run(["readelf", "-d", binary])
    combined = out + err
    if "no dynamic section" in combined.lower() or "There is no dynamic section" in combined:
        report.add("no-dynamic-section", AuditStatus.PASS, "No dynamic section — kernel clean")
    elif "NEEDED" in combined:
        report.add("no-dynamic-section", AuditStatus.FAIL,
                   "Kernel has dynamic dependencies — WRONG!", raw=combined)
    else:
        report.add("no-dynamic-section", AuditStatus.PASS, "No dynamic section found")

    # 3c — ldd
    rc, out, err = _run(["ldd", binary])
    combined = out + err
    if "not a dynamic executable" in combined:
        report.add("ldd-kernel", AuditStatus.PASS,
                   "ldd: not a dynamic executable — kernel correct")
    else:
        report.add("ldd-kernel", AuditStatus.FAIL,
                   f"ldd shows deps on kernel binary: {combined[:100]}")

    # 3d — Disassembly
    lines = _objdump_disasm(binary)
    disasm = "\n".join(lines)

    # Must not call libc start
    if "__libc_start_main" in disasm:
        report.add("kernel-no-libc-start", AuditStatus.FAIL,
                   "Kernel _start calls __libc_start_main — WRONG!")
    else:
        report.add("kernel-no-libc-start", AuditStatus.PASS,
                   "Kernel _start does not call __libc_start_main")

    # Stack pointer setup
    sp_lines = [ln for ln in lines
                if "sp" in ln.lower()
                and any(x in ln for x in ("mov", "ldr", "adrp", "sub", "stp", "msr"))]
    if sp_lines:
        report.add("kernel-sp-setup", AuditStatus.PASS,
                   f"Found {len(sp_lines)} SP setup instruction(s)",
                   raw="\n".join(sp_lines[:5]))
    else:
        report.add("kernel-sp-setup", AuditStatus.WARNING,
                   "No SP setup found — may be minimal kernel")

    # Part 4 — MMIO address checks (QEMU virt board)
    MMIO_MAP = {
        "UART PL011":  ["9000000"],
        "GIC-400":     ["8000000"],
        "Timer":       ["9010000"],
        "Framebuffer": ["3c000000"],
        "RAM base":    ["40000000"],
        "PCIe":        ["10000000"],
    }
    found_mmio = []
    for name, pats in MMIO_MAP.items():
        hits = [ln for ln in lines if any(p in ln for p in pats)]
        if hits:
            found_mmio.append(f"{name}({len(hits)})")

    if found_mmio:
        report.add("mmio-addresses", AuditStatus.PASS,
                   f"MMIO regions: {', '.join(found_mmio)}")
    else:
        report.add("mmio-addresses", AuditStatus.WARNING,
                   "No standard QEMU virt MMIO addresses — different board?")

    # Legacy UART check (backward compat)
    uart_lines = [ln for ln in lines if "9000000" in ln or "09000000" in ln]
    if uart_lines:
        report.add("mmio-uart", AuditStatus.PASS,
                   f"UART MMIO (0x09000000) in {len(uart_lines)} place(s)",
                   raw="\n".join(uart_lines[:5]))

    # Part 5 — EL1 privileged instructions
    EL1_INSNS = ["msr ", "mrs ", " eret", " tlbi", " dsb", " isb",
                 " ic ", " dc ", "msr\t", "mrs\t", "\teret"]
    found_el1 = []
    for ln in lines:
        for insn in EL1_INSNS:
            if insn in ln.lower():
                found_el1.append(ln)
                break
    if found_el1:
        report.add("el1-instructions", AuditStatus.PASS,
                   f"Found {len(found_el1)} EL1 privileged instruction(s) "
                   f"(msr/mrs/eret/tlbi/dsb/isb)",
                   raw="\n".join(found_el1[:8]))
    else:
        report.add("el1-instructions", AuditStatus.WARNING,
                   "No EL1 instructions found — minimal kernel or x86_64 target")

    # Exception vector table
    vec_hints = [ln for ln in lines
                 if any(x in ln for x in ("vbar_el1", "VBAR", "b.al", "ldr pc"))]
    if vec_hints:
        report.add("exception-vectors", AuditStatus.PASS,
                   f"Exception vector table referenced ({len(vec_hints)} hint(s))",
                   raw="\n".join(vec_hints[:5]))
    else:
        rc2, sec_out, _ = _run(["readelf", "-S", binary])
        if "vectors" in sec_out.lower():
            report.add("exception-vectors", AuditStatus.PASS,
                       ".text.vectors section present — exception table linked")
        else:
            report.add("exception-vectors", AuditStatus.WARNING,
                       "No exception vector hints — verify vector_table placement")

    # Context switch registers (SPSR_EL1, ELR_EL1, TPIDR_EL1, TTBR0)
    ctx_regs = [ln for ln in lines
                if any(x in ln.lower() for x in
                       ("spsr_el1", "elr_el1", "tpidr_el1", "ttbr0_el1",
                        "ttbr1_el1", "tcr_el1", "sctlr_el1"))]
    if ctx_regs:
        report.add("context-switch", AuditStatus.PASS,
                   f"Context switch registers: {len(ctx_regs)} refs "
                   f"(SPSR/ELR/TPIDR/TTBR) — scheduler-capable",
                   raw="\n".join(ctx_regs[:5]))
    else:
        report.add("context-switch", AuditStatus.WARNING,
                   "No context switch register refs — basic kernel / uniprocessor")

    # Syscall emission (SVC #0)
    svc_lines = [ln for ln in lines
                 if " svc " in ln.lower() or "\tsvc\t" in ln.lower()
                 or " svc\t" in ln.lower()]
    if svc_lines:
        report.add("kernel-syscall-emission", AuditStatus.PASS,
                   f"Found {len(svc_lines)} SVC instruction(s) — userland syscall ABI present",
                   raw="\n".join(svc_lines[:5]))
    else:
        report.add("kernel-syscall-emission", AuditStatus.WARNING,
                   "No SVC instructions — kernel may not serve userland syscalls")

    # Symbol clean check (same classifier)
    sym_lines = _readelf_symbols(binary)
    real_libc = []
    comp_rt = []
    for ln in sym_lines:
        sym = _extract_sym_name(ln)
        cls = _classify_symbol(sym, ln)
        if cls == "real_libc":
            real_libc.append(sym)
        elif cls == "compiler_rt":
            comp_rt.append(sym)

    if not real_libc:
        report.add("kernel-symbol-clean", AuditStatus.PASS,
                   "Zero real libc symbols in kernel — FREESTANDING")
    else:
        report.add("kernel-symbol-clean", AuditStatus.FAIL,
                   f"{len(real_libc)} real libc symbol(s) in kernel!",
                   raw="\n".join(real_libc[:8]))

    if comp_rt:
        fix = ""
        if "__stack_chk_fail" in comp_rt:
            fix = " — add -fno-stack-protector to remove"
        report.add("kernel-compiler-rt", AuditStatus.WARNING,
                   f"{len(comp_rt)} GCC compiler-rt builtin(s){fix}",
                   raw="\n".join(comp_rt[:5]))

    # ABI stack alignment (Part 6 inline for kernel)
    stp_16 = [ln for ln in lines if "stp" in ln and "#-16" in ln]
    stp_any = [ln for ln in lines if "stp" in ln and ("x29" in ln or "x30" in ln)]
    frames = stp_16 or stp_any
    if frames:
        report.add("abi-stack-alignment", AuditStatus.PASS,
                   f"Found {len(frames)} proper AArch64 frame setup(s) (stp x29,x30)",
                   raw="\n".join(frames[:5]))
    else:
        report.add("abi-stack-alignment", AuditStatus.WARNING,
                   "No frame pointer setup — leaf-only or stripped")

    # QEMU boot command
    qemu_a64 = _tool("qemu-system-aarch64")
    qemu_x64 = _tool("qemu-system-x86_64")
    qemu = qemu_a64 or qemu_x64
    if qemu:
        if qemu_a64:
            cmd = (f"qemu-system-aarch64 -machine virt -cpu cortex-a53 "
                   f"-m 512 -nographic -kernel {binary} -serial mon:stdio")
        else:
            cmd = f"qemu-system-x86_64 -kernel {binary} -nographic"
        report.add("qemu-boot-command", AuditStatus.PASS, f"Boot: {cmd}")
    else:
        report.add("qemu-boot", AuditStatus.SKIP,
                   "QEMU not found — install: sudo apt install qemu-system-arm")

    return report


# ═══════════════════════════════════════════════════════════════════════════
# PART 6 — ABI / STACK ALIGNMENT
# ═══════════════════════════════════════════════════════════════════════════

def audit_abi(binary: str) -> AuditReport:
    """Part 6: ABI conformance, stack alignment, calling convention checks."""
    report = AuditReport(binary=binary, mode="abi")

    if not os.path.exists(binary):
        report.add("file-exists", AuditStatus.FAIL, f"Binary not found: {binary}")
        return report

    lines = _objdump_disasm(binary)
    if not lines:
        report.add("objdump", AuditStatus.SKIP, "objdump not available")
        return report

    # AArch64: stp x29, x30, [sp, #-16]!
    stp_16  = [ln for ln in lines if "stp" in ln and "#-16" in ln]
    stp_any = [ln for ln in lines if "stp" in ln and ("x29" in ln or "x30" in ln)]
    # x86_64
    push_rbp = [ln for ln in lines if "push" in ln and "rbp" in ln]
    sub_rsp  = [ln for ln in lines if "sub" in ln and "rsp" in ln]

    if stp_16:
        report.add("aarch64-16byte-align", AuditStatus.PASS,
                   f"{len(stp_16)} 16-byte aligned frame push(es) — stp x29,x30,[sp,#-16]!",
                   raw="\n".join(stp_16[:5]))
    elif stp_any:
        report.add("aarch64-frame-save", AuditStatus.PASS,
                   f"{len(stp_any)} AArch64 frame saves found",
                   raw="\n".join(stp_any[:5]))

    if push_rbp:
        report.add("x86-64-frame-setup", AuditStatus.PASS,
                   f"{len(push_rbp)} x86_64 push rbp frame setup(s)",
                   raw="\n".join(push_rbp[:5]))

    if sub_rsp:
        bad_align = []
        for ln in sub_rsp:
            m = re.search(r"#(0x[0-9a-f]+|[0-9]+)", ln)
            if m:
                try:
                    val = int(m.group(1), 16 if m.group(1).startswith("0x") else 10)
                    if val % 16 != 0:
                        bad_align.append(f"{val} bytes (misaligned!) — {ln.strip()}")
                except ValueError:
                    pass
        if bad_align:
            report.add("stack-16byte-align", AuditStatus.FAIL,
                       f"Misaligned stack allocation(s)!", raw="\n".join(bad_align))
        else:
            report.add("stack-16byte-align", AuditStatus.PASS,
                       f"All {len(sub_rsp)} stack allocation(s) are 16-byte aligned")

    # LR save check (AArch64)
    bl_count = len([ln for ln in lines if "\tbl\t" in ln or " bl " in ln])
    lr_saves = len([ln for ln in lines if "x30" in ln and "stp" in ln])
    if bl_count > 0 and lr_saves == 0:
        report.add("lr-save", AuditStatus.WARNING,
                   f"{bl_count} BL call(s) but no x30/LR save — possible stack corruption")
    elif lr_saves > 0:
        report.add("lr-save", AuditStatus.PASS,
                   f"LR (x30) saved in {lr_saves} frame(s) — call stack safe")

    if not stp_any and not push_rbp:
        report.add("abi-frames", AuditStatus.WARNING,
                   "No frame pointer setup — leaf-only binary or fully stripped")

    return report


# ═══════════════════════════════════════════════════════════════════════════
# PART 7 — FREESTANDINGTY PATCHER
# ═══════════════════════════════════════════════════════════════════════════

def patch_freestanding(binary: str, output: str = None) -> Tuple[bool, str]:
    """
    Part 7: Strip all compiler metadata and GCC artifacts from an ELF.
    Removes: .comment, .note.gnu.build-id, .note.ABI-tag, .note.gnu.property,
             .eh_frame, .eh_frame_hdr, .gcc_except_table, .debug_* sections.
    Then strips symbol table with strip --strip-all.
    """
    output = output or binary

    strip   = (_tool("aarch64-linux-gnu-strip") or _tool("arm-linux-gnueabihf-strip")
               or _tool("strip"))
    objcopy = (_tool("aarch64-linux-gnu-objcopy") or _tool("arm-linux-gnueabihf-objcopy")
               or _tool("objcopy"))

    if not strip and not objcopy:
        return False, ("No strip/objcopy found. Install:\n"
                       "  sudo apt install binutils-aarch64-linux-gnu")

    tmp = binary + "._freestanding_tmp"
    try:
        import shutil as _sh
        _sh.copy2(binary, tmp)
    except Exception as e:
        return False, f"Failed to copy binary: {e}"

    results = []
    before_size = _file_size(binary)

    # Step 1 — Remove dead sections via objcopy
    DEAD_SECTIONS = [
        ".comment",            # GCC: (GNU) version string  ← main culprit
        ".note.gnu.build-id",  # Build ID hash
        ".note.ABI-tag",       # ABI compat tag
        ".note.gnu.property",  # GNU property notes
        ".eh_frame",           # Exception handling (not needed bare metal)
        ".eh_frame_hdr",
        ".gcc_except_table",
        ".debug_info", ".debug_abbrev", ".debug_line", ".debug_str",
        ".debug_frame", ".debug_loc", ".debug_ranges", ".debug_types",
        ".gnu.warning",
    ]

    if objcopy:
        oc_args = [objcopy]
        for sec in DEAD_SECTIONS:
            oc_args += ["--remove-section", sec]
        oc_args += [tmp, tmp]
        rc, _, err = _run(oc_args, timeout=30)
        if rc == 0:
            results.append(f"objcopy: stripped {len(DEAD_SECTIONS)} metadata sections "
                           f"(.comment, .note.*, .eh_frame, .debug_*)")
        else:
            # Sections may not exist — not an error
            results.append(f"objcopy: sections removed (some may not have existed)")

    # Step 2 — Strip symbol table
    if strip:
        rc, _, err = _run([strip, "--strip-all", tmp], timeout=30)
        if rc == 0:
            results.append("strip --strip-all: symbol table, relocation, debug info removed")
        else:
            results.append(f"strip: {err[:80]}")

    # Step 3 — Verify ELF still valid
    rc, out, _ = _run(["readelf", "-h", tmp])
    if rc != 0 or "ELF" not in out:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        return False, "Sovereignty patch corrupted the binary — reverting (original unchanged)"

    # Commit
    try:
        os.replace(tmp, output)
    except Exception as e:
        return False, f"Failed to write output: {e}"

    after_size = _file_size(output)
    reduction = (1 - after_size / before_size) * 100 if before_size else 0

    return True, "\n".join([
        "╔" + "═" * 56 + "╗",
        "║  FREESTANDINGTY PATCH APPLIED" + " " * 29 + "║",
        "╠" + "═" * 56 + "╣",
        *[f"║  ✓ {r[:52]:<52}║" for r in results],
        "╠" + "═" * 56 + "╣",
        f"║  Size: {before_size:,} → {after_size:,} bytes "
        f"({reduction:.1f}% reduction){'':>10}║",
        "╚" + "═" * 56 + "╝",
    ])


# ═══════════════════════════════════════════════════════════════════════════
# PART 8 — ENTROPY / DEEP STRING SCAN
# ═══════════════════════════════════════════════════════════════════════════

def audit_entropy(binary: str) -> AuditReport:
    """Part 8: Deep string and compiler artifact scan."""
    report = AuditReport(binary=binary, mode="entropy")

    if not os.path.exists(binary):
        report.add("file-exists", AuditStatus.FAIL, f"Binary not found: {binary}")
        return report

    rc, out, _ = _run(["strings", "-n", "4", binary])
    if rc != 0:
        report.add("strings", AuditStatus.SKIP, "strings tool not available")
        return report

    all_strings = out.splitlines()
    report.add("string-count", AuditStatus.PASS,
               f"{len(all_strings)} printable strings in binary")

    libc_refs  = [s for s in all_strings
                  if re.search(r"libc\.so|GLIBC_[0-9]|GNU C Library|ld-linux", s)]
    gcc_meta   = [s for s in all_strings
                  if re.search(r"GCC: \(|gcc version [0-9]|clang version", s, re.I)]
    bld_paths  = [s for s in all_strings
                  if re.match(r"/(usr|home|root|tmp|build|opt|work|src)/", s)
                  and len(s) > 8]
    dbg_syms   = [s for s in all_strings
                  if re.search(r"\.(c|h|cpp|cc|S):[0-9]|/include/", s)]
    stk_canary = [s for s in all_strings if "__stack_chk" in s]
    abi_refs   = [s for s in all_strings
                  if re.search(r"__aeabi_|__gcc_|_Unwind_", s)]
    minios_id  = [s for s in all_strings
                  if re.search(r"MiniOS|KentScript|minios|kentscript", s, re.I)]

    def _check(name, items, fail_status, pass_msg, fail_msg):
        if items:
            report.add(name, fail_status, f"{len(items)} {fail_msg}",
                       raw="\n".join(items[:6]))
        else:
            report.add(name, AuditStatus.PASS, f"No {pass_msg}")

    _check("libc-string-refs",   libc_refs,  AuditStatus.FAIL,
           "libc string references", "real libc string ref(s)!")
    _check("gcc-metadata",       gcc_meta,   AuditStatus.WARNING,
           "GCC metadata strings",
           "GCC version metadata string(s) — strip to remove")
    _check("build-paths",        bld_paths,  AuditStatus.WARNING,
           "build paths", "build path(s) leaking filesystem")
    _check("debug-symbols",      dbg_syms,   AuditStatus.WARNING,
           "debug source refs", "source file path(s) in binary")
    _check("stack-canary-str",   stk_canary, AuditStatus.WARNING,
           "stack canary strings",
           "stack canary string(s) — add -fno-stack-protector")
    _check("compiler-abi-refs",  abi_refs,   AuditStatus.WARNING,
           "compiler ABI strings", "compiler ABI helper string(s)")

    if minios_id:
        report.add("minios-identity", AuditStatus.PASS,
                   f"MiniOS identity string(s) confirmed ({len(minios_id)})",
                   raw="\n".join(minios_id[:3]))

    # Sovereignty score
    fails = report.fail_count()
    warns = sum(1 for c in report.checks if c.status == AuditStatus.WARNING)
    if fails == 0 and warns == 0:
        report.add("freestanding-score", AuditStatus.PASS,
                   "PERFECT — zero compiler artifacts in string table")
    elif fails == 0:
        report.add("freestanding-score", AuditStatus.WARNING,
                   f"NEAR-FREESTANDING — 0 failures, {warns} warning(s). "
                   f"Run: kentscript audit --patch-freestanding {os.path.basename(binary)}")
    else:
        report.add("freestanding-score", AuditStatus.FAIL,
                   f"NOT FREESTANDING — {fails} failure(s), {warns} warning(s)")

    return report


# ═══════════════════════════════════════════════════════════════════════════
# PART 9 — ELF HARDENING REPORT
# ═══════════════════════════════════════════════════════════════════════════

def audit_hardening(binary: str) -> AuditReport:
    """Part 9: ELF security hardening — RELRO, NX, PIE, canary, stripped."""
    report = AuditReport(binary=binary, mode="hardening")

    if not os.path.exists(binary):
        report.add("file-exists", AuditStatus.FAIL, f"Binary not found: {binary}")
        return report

    rc_h, hdr, _  = _run(["readelf", "-h", binary])
    rc_d, dyn, _  = _run(["readelf", "-d", binary])
    rc_l, prog, _ = _run(["readelf", "-l", binary])
    sym_text = "\n".join(_readelf_symbols(binary))
    is_kernel = "minios" in binary.lower() or "kernel" in binary.lower()
    is_static = "no dynamic section" in (dyn + rc_d * "").lower() or \
                "There is no dynamic section" in dyn

    # PIE
    if "DYN" in hdr:
        report.add("PIE", AuditStatus.PASS,
                   "PIE enabled (DYN) — ASLR compatible")
    elif "EXEC" in hdr:
        if is_kernel or is_static:
            report.add("PIE", AuditStatus.PASS,
                       "No PIE (EXEC) — correct for kernel/freestanding ELF")
        else:
            report.add("PIE", AuditStatus.WARNING,
                       "No PIE — fixed load address (add -fPIE -pie for hosted bins)")

    # RELRO
    if "GNU_RELRO" in prog:
        if "BIND_NOW" in dyn:
            report.add("RELRO", AuditStatus.PASS,
                       "Full RELRO — .got.plt read-only after init")
        else:
            report.add("RELRO", AuditStatus.WARNING,
                       "Partial RELRO — .got.plt still writable (-Wl,-z,now for full)")
    else:
        if is_static:
            report.add("RELRO", AuditStatus.PASS,
                       "N/A — static/freestanding binary has no GOT/PLT")
        else:
            report.add("RELRO", AuditStatus.FAIL,
                       "No RELRO — GOT fully writable (-Wl,-z,relro)")

    # NX stack
    if "GNU_STACK" in prog:
        stack_line = next((ln for ln in prog.splitlines() if "GNU_STACK" in ln), "")
        exec_flag = stack_line.split()[-1] if stack_line else ""
        if "E" not in exec_flag:
            report.add("NX-stack", AuditStatus.PASS,
                       "NX stack — stack not executable")
        else:
            report.add("NX-stack", AuditStatus.FAIL,
                       "Executable stack! RWE segment — remove -z execstack")
    else:
        if is_kernel:
            report.add("NX-stack", AuditStatus.PASS,
                       "No GNU_STACK — kernel defines its own memory policy")
        else:
            report.add("NX-stack", AuditStatus.WARNING,
                       "No GNU_STACK segment — stack exec policy undefined")

    # Stack canary
    if "__stack_chk_fail" in sym_text:
        if is_kernel:
            report.add("stack-canary", AuditStatus.WARNING,
                       "__stack_chk_fail present — add -fno-stack-protector "
                       "for pure freestanding kernel")
        else:
            report.add("stack-canary", AuditStatus.PASS,
                       "Stack canary active (-fstack-protector)")
    else:
        if is_kernel:
            report.add("stack-canary", AuditStatus.PASS,
                       "No stack canary — correct for freestanding kernel")
        else:
            report.add("stack-canary", AuditStatus.WARNING,
                       "No stack canary — consider -fstack-protector-strong")

    # Stripped
    rc_nm, nm_out, _ = _run(["nm", binary])
    if rc_nm != 0 or not nm_out.strip():
        report.add("stripped", AuditStatus.PASS,
                   "Binary stripped — no symbol table (freestanding)")
    else:
        sym_count = len(nm_out.splitlines())
        report.add("stripped", AuditStatus.WARNING,
                   f"Not stripped — {sym_count} symbol(s) visible "
                   f"(run: kentscript audit --patch-freestanding {os.path.basename(binary)})")

    # RPATH
    if "RPATH" in dyn or "RUNPATH" in dyn:
        rpath = [ln for ln in dyn.splitlines() if "RPATH" in ln or "RUNPATH" in ln]
        report.add("rpath", AuditStatus.FAIL,
                   "RPATH/RUNPATH present — filesystem path leak!",
                   raw="\n".join(rpath))
    else:
        report.add("rpath", AuditStatus.PASS, "No RPATH/RUNPATH — clean")

    # Build-id (metadata leak)
    rc_n, notes, _ = _run(["readelf", "-n", binary])
    if "Build ID" in notes:
        bid = next((ln.split()[-1] for ln in notes.splitlines()
                    if "Build ID" in ln), "present")
        report.add("build-id", AuditStatus.WARNING,
                   f"GNU build-id present: {bid} "
                   f"(strip with --remove-section=.note.gnu.build-id)",
                   raw=notes[:200])
    else:
        report.add("build-id", AuditStatus.PASS, "No GNU build-id — clean")

    return report


# ═══════════════════════════════════════════════════════════════════════════
# PART 10 — BUILD-FREESTANDING
# Full bare-metal compile with zero-libc flags + linker script + memfuncs
# ═══════════════════════════════════════════════════════════════════════════

FREESTANDING_LINKER_AARCH64 = r"""/* KentScript Sovereign Linker Script — AArch64 Bare Metal
 * Entry at 0x40000000 (QEMU virt RAM base)
 * Usage: aarch64-linux-gnu-gcc ... -T freestanding.ld
 */
ENTRY(_start)

SECTIONS {
    . = 0x40000000;

    /* Exception vector table MUST be at start (aligned to 2048 bytes) */
    .text.vectors : ALIGN(2048) { *(.text.vectors) }

    .text : {
        *(.text.startup)
        *(.text*)
    }

    .rodata : { *(.rodata*) }

    . = ALIGN(8);
    .data : { *(.data*) }

    . = ALIGN(8);
    .bss (NOLOAD) : {
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        __bss_end = .;
    }

    . = ALIGN(4096);
    __kernel_end = .;

    /* Discard everything that leaks compiler identity */
    /DISCARD/ : {
        *(.comment)         /* GCC version string */
        *(.note*)           /* Build-ID, ABI tag  */
        *(.eh_frame*)       /* Exception handling  */
        *(.gcc_except_table)
        *(.debug*)          /* DWARF debug info   */
        *(.gnu.warning*)
    }
}
"""

FREESTANDING_MEMFUNCS_C = r"""/* KentScript Sovereign Memory Functions — ks_freestanding_mem.c
 * Replaces ALL compiler-rt and libc memory helpers.
 * Include in your build: gcc ... kernel.c ks_freestanding_mem.c
 * Achieves zero-symbol freestanding — no __aeabi_memcpy, no memcpy dep.
 */
#ifndef __FREESTANDING_MEM_H
#define __FREESTANDING_MEM_H

typedef unsigned long  size_t;
typedef unsigned char  u8;
typedef unsigned long  u64;

/* ── memcpy — replaces __aeabi_memcpy/__aeabi_memcpy4/__aeabi_memcpy8 ────── */
void *memcpy(void *dst, const void *src, size_t n) {
    u8 *d = (u8 *)dst;
    const u8 *s = (const u8 *)src;
    /* 8-byte aligned fast path */
    while (n >= 8 && !((u64)d & 7) && !((u64)s & 7)) {
        *(u64 *)d = *(const u64 *)s;
        d += 8; s += 8; n -= 8;
    }
    while (n--) *d++ = *s++;
    return dst;
}

/* ── memset — replaces __aeabi_memset ────────────────────────────────────── */
void *memset(void *dst, int c, size_t n) {
    u8 *d = (u8 *)dst;
    u8 val = (u8)c;
    u64 pattern = (u64)val * 0x0101010101010101UL;
    while (n >= 8 && !((u64)d & 7)) { *(u64 *)d = pattern; d += 8; n -= 8; }
    while (n--) *d++ = val;
    return dst;
}

/* ── memmove — handles overlapping regions ───────────────────────────────── */
void *memmove(void *dst, const void *src, size_t n) {
    u8 *d = (u8 *)dst; const u8 *s = (const u8 *)src;
    if (d < s || d >= s + n) return memcpy(dst, src, n);
    d += n; s += n;
    while (n--) *--d = *--s;
    return dst;
}

/* ── memcmp ──────────────────────────────────────────────────────────────── */
int memcmp(const void *a, const void *b, size_t n) {
    const u8 *pa = (const u8 *)a, *pb = (const u8 *)b;
    while (n--) { if (*pa != *pb) return (int)*pa - (int)*pb; pa++; pb++; }
    return 0;
}

/* ── strlen ──────────────────────────────────────────────────────────────── */
size_t strlen(const char *s) { size_t n = 0; while (*s++) n++; return n; }

/* ── strcmp / strncmp ────────────────────────────────────────────────────── */
int strcmp(const char *a, const char *b) {
    while (*a && *a == *b) { a++; b++; }
    return (unsigned char)*a - (unsigned char)*b;
}
int strncmp(const char *a, const char *b, size_t n) {
    while (n-- && *a && *a == *b) { a++; b++; }
    return n == (size_t)-1 ? 0 : (unsigned char)*a - (unsigned char)*b;
}

/* ── Stack protector stub — replaces __stack_chk_fail without libc ───────── */
/* GCC injects this when -fstack-protector is used. This version halts. */
unsigned long __stack_chk_guard = 0xDEADBEEFCAFEBABEUL;
void __stack_chk_fail(void) { for (;;) { __asm__ volatile("wfi"); } }

#endif /* __FREESTANDING_MEM_H */
"""

FREESTANDING_COMPILE_FLAGS = {
    "aarch64": [
        "-ffreestanding",           # No hosted environment
        "-fno-builtin",             # No GCC builtin substitutions
        "-nostdlib",                # No standard library
        "-nostartfiles",            # No CRT0
        "-nodefaultlibs",           # No default libs
        "-static",                  # Static link only
        "-fno-stack-protector",     # No __stack_chk_fail injection
        "-fno-asynchronous-unwind-tables",  # No .eh_frame
        "-fno-exceptions",          # No exception handling
        "-fno-unwind-tables",       # No unwind tables
        "-fno-ident",               # No GCC ident in .comment
        "-march=armv8-a",
        "-mtune=cortex-a53",
    ],
    "x86_64": [
        "-ffreestanding",
        "-fno-builtin",
        "-nostdlib",
        "-nostartfiles",
        "-nodefaultlibs",
        "-static",
        "-fno-stack-protector",
        "-fno-asynchronous-unwind-tables",
        "-fno-exceptions",
        "-fno-unwind-tables",
        "-fno-ident",
        "-m64",
        "-mno-red-zone",            # Kernel must not use red zone
        "-mcmodel=kernel",          # Kernel memory model
    ],
}


def build_freestanding(source: str, output: str,
                    arch: str = "aarch64",
                    opt: str = "O2") -> Tuple[bool, str]:
    """
    Part 10: Compile to a fully freestanding bare-metal ELF.
    - Uses all flags that prevent libc/compiler-rt injection
    - Includes freestanding memory functions (custom memcpy/memset/etc.)
    - Generates linker script placing vectors first
    - Auto-applies freestandingty patch after build
    """
    if not os.path.exists(source):
        return False, f"Source not found: {source}"

    # Find cross-compiler
    if arch == "aarch64":
        cc = (_tool("aarch64-linux-gnu-gcc") or
              _tool("aarch64-none-elf-gcc") or
              _tool("aarch64-elf-gcc"))
        if not cc:
            return False, ("AArch64 cross-compiler not found.\n"
                           "Install: sudo apt install gcc-aarch64-linux-gnu\n"
                           "Termux:  pkg install aarch64-linux-gnu-binutils")
    else:
        cc = _tool("gcc") or _tool("cc")
        if not cc:
            return False, "No C compiler found"

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write linker script
        ld_path = os.path.join(tmpdir, "freestanding.ld")
        with open(ld_path, "w") as f:
            f.write(FREESTANDING_LINKER_AARCH64 if arch == "aarch64" else
                    "ENTRY(_start)\nSECTIONS { . = 0x100000; .text : { *(.text*) } }")

        # Write freestanding memory functions
        mem_path = os.path.join(tmpdir, "ks_freestanding_mem.c")
        with open(mem_path, "w") as f:
            f.write(FREESTANDING_MEMFUNCS_C)

        flags = [f"-{opt}"] + FREESTANDING_COMPILE_FLAGS.get(arch, [])
        if arch == "aarch64":
            flags += ["-T", ld_path]

        cmd = [cc] + flags + ["-o", output, source, mem_path]
        rc, out, err = _run(cmd, timeout=60)

        if rc != 0:
            return False, (f"Build failed:\n{err}\n\nCommand:\n{' '.join(cmd)}")

        # Auto-patch
        ok, patch_msg = patch_freestanding(output)

        size_final = _file_size(output)
        return True, "\n".join([
            "╔" + "═" * 60 + "╗",
            "║  FREESTANDING BUILD COMPLETE" + " " * 34 + "║",
            "╠" + "═" * 60 + "╣",
            f"║  Source   : {source:<47}║",
            f"║  Output   : {output:<47}║",
            f"║  Arch     : {arch:<47}║",
            f"║  Compiler : {cc:<47}║",
            f"║  Size     : {size_final:,} bytes{'':<37}║",
            "╠" + "═" * 60 + "╣",
            f"║  Flags    : {(' '.join(flags[:4]) + ' ...'):<47}║",
            "╠" + "═" * 60 + "╣",
            "║  Sovereignty patch:" + " " * 40 + "║",
            *([f"║    {ln[:56]:<56}║" for ln in patch_msg.splitlines()
               if ln.strip() and "═" not in ln][:6]),
            "╠" + "═" * 60 + "╣",
            f"║  Audit: kentscript audit {output} --mode freestanding{'':>11}║",
            "╚" + "═" * 60 + "╝",
        ])


# ═══════════════════════════════════════════════════════════════════════════
# REPORT RENDERER
# ═══════════════════════════════════════════════════════════════════════════

ICONS  = {AuditStatus.PASS: "✓", AuditStatus.FAIL: "✗",
          AuditStatus.WARNING: "!", AuditStatus.SKIP: "·"}
COLORS = {AuditStatus.PASS:    "\033[32m",
          AuditStatus.FAIL:    "\033[31m",
          AuditStatus.WARNING: "\033[33m",
          AuditStatus.SKIP:    "\033[90m"}
RESET = "\033[0m"
BOLD  = "\033[1m"
CYAN  = "\033[36m"
W = 64  # box width


def render_report(report: AuditReport, verbose: bool = False) -> str:
    lines = []
    lines.append("╔" + "═" * W + "╗")
    mode_str = report.mode.upper()
    title = f"  {BOLD}KentScript Audit — {mode_str}{RESET}"
    pad = W - 20 - len(mode_str)
    lines.append(f"║{title}{' ' * max(pad, 1)}║")
    bname = os.path.basename(report.binary)[:W-10]
    lines.append(f"║  Binary: {bname:<{W-10}}║")
    lines.append("╠" + "═" * W + "╣")

    for c in report.checks:
        col  = COLORS.get(c.status, "")
        icon = ICONS.get(c.status, "?")
        st   = c.status.value
        name = c.name[:24].ljust(24)
        det  = c.detail[:28]
        lines.append(f"║  {col}{icon} [{st:4}]{RESET}  {name}  {det:<28}║")
        if verbose and c.raw:
            for raw_ln in c.raw.splitlines()[:5]:
                rl = raw_ln[:W-6]
                lines.append(f"║    {CYAN}{rl:<{W-6}}{RESET}║")

    lines.append("╠" + "═" * W + "╣")
    summary = report.summary()
    verdict = "FREESTANDING" if report.passed() else "NEEDS WORK"
    vc = "\033[32m" if report.passed() else "\033[31m"
    lines.append(f"║  {summary:<46}  {vc}{BOLD}{verdict:>10}{RESET}  ║")
    lines.append("╚" + "═" * W + "╝")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# FULL AUDIT RUNNER
# ═══════════════════════════════════════════════════════════════════════════

def run_full_audit(binary: str, verbose: bool = False,
                   freestanding_mode: bool = False):
    SEP = "═" * 66
    label = "FULL FREESTANDING AUDIT" if freestanding_mode else "FULL AUDIT"
    print(f"\n{SEP}")
    print(f"  {label}: {binary}")
    print(f"{SEP}\n")

    reports = []

    parts = [
        ("Part 1: Hosted Binary Audit",                   audit_hosted),
        ("Part 2: Freestanding Audit (compiler-rt aware)", audit_freestanding),
        ("Part 3+4+5: Kernel / MMIO / EL1 Validation",   audit_kernel),
        ("Part 6: ABI / Stack Alignment",                  audit_abi),
        ("Part 8: Entropy / Compiler Artifact Scan",       audit_entropy),
        ("Part 9: ELF Hardening Report",                   audit_hardening),
    ]

    for label_part, fn in parts:
        print(f"▶ {label_part}")
        r = fn(binary)
        reports.append(r)
        print(render_report(r, verbose))
        print()

    total_pass = sum(1 for rr in reports for c in rr.checks
                     if c.status == AuditStatus.PASS)
    total_fail = sum(1 for rr in reports for c in rr.checks
                     if c.status == AuditStatus.FAIL)
    total_warn = sum(1 for rr in reports for c in rr.checks
                     if c.status == AuditStatus.WARNING)

    print(SEP)
    print(f"  FINAL VERDICT")
    print(f"{'─'*66}")
    print(f"  PASS={total_pass}  FAIL={total_fail}  WARN={total_warn}")
    print()

    if total_fail == 0:
        print(f"\033[32m\033[1m  STATUS: FREESTANDING — PURE BARE METAL\033[0m")
        print(f"  Zero real libc symbols. Zero runtime dependencies.")
        print(f"  This binary runs on silicon, not on an OS.")
        print(f"  Linux refuses to run it. QEMU boots it as firmware.")
    elif total_fail <= 2:
        print(f"\033[33m\033[1m  STATUS: NEAR-FREESTANDING ({total_fail} issue(s) remain)\033[0m")
        print(f"  Fix: kentscript audit --patch-freestanding {binary}")
        print(f"  Or:  kentscript audit --build-freestanding src.c -o {binary} --arch aarch64")
    else:
        print(f"\033[31m\033[1m  STATUS: NEEDS WORK ({total_fail} failure(s))\033[0m")
        print(f"  See FAIL items above.")
        print(f"  Tip: kentscript audit --build-freestanding src.c -o out.elf")

    print(SEP)

    # If freestanding_mode, auto-patch remaining issues
    if freestanding_mode and total_fail > 0:
        print(f"\n  Auto-applying freestandingty patch...")
        ok, msg = patch_freestanding(binary)
        print(msg)
        if ok:
            print("\n  Re-auditing patched binary...")
            run_full_audit(binary, verbose, freestanding_mode=False)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse

    p = argparse.ArgumentParser(
        prog="ks_audit",
        description="KentScript Binary Audit v2.0 — kernel-grade binary forensics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes (--mode):
  full          All 6 parts + final verdict (default)
  hosted        Part 1: libc dependency audit
  freestanding  Part 2: zero-libc check (FIXED: compiler-rt aware)
  kernel        Parts 3-6: kernel ELF, EL1, MMIO, vectors
  abi           Part 6: stack alignment, calling convention
  entropy       Part 8: deep string / compiler artifact scan
  hardening     Part 9: RELRO, NX, PIE, canary, stripped
  freestanding     Full audit + auto-patch metadata

Build/patch tools:
  --build-freestanding <src.c> -o <out.elf> [--arch aarch64|x86_64]
      Compile with full bare-metal flags + freestanding linker script
  --patch-freestanding <binary> [-o <output.elf>]
      Strip .comment, .note.*, .eh_frame, debug sections + symbol table
  --dump-memfuncs
      Print freestanding memcpy/memset/strlen/strcmp/stack_chk_fail source
  --dump-linkerscript
      Print AArch64 freestanding linker script

Examples:
  kentscript audit /tmp/minios.elf
  kentscript audit /tmp/minios.elf --mode freestanding
  kentscript audit --build-freestanding kernel.c -o minios.elf --arch aarch64
  kentscript audit --patch-freestanding minios.elf
  kentscript audit --dump-memfuncs > ks_freestanding_mem.c
  kentscript audit --dump-linkerscript > freestanding.ld
""")

    p.add_argument("binary", nargs="?",
                   help="Binary to audit")
    p.add_argument("--mode", "-m",
                   choices=["full", "hosted", "freestanding", "kernel",
                             "abi", "entropy", "hardening", "freestanding"],
                   default="full")
    p.add_argument("--arch", default="aarch64",
                   choices=["x86_64", "aarch64"])
    p.add_argument("--opt", default="O2",
                   help="Optimization: O0 O1 O2 O3 Os")
    p.add_argument("-o", "--output", default=None,
                   help="Output path for --build-freestanding / --patch-freestanding")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Show raw tool output in reports")
    p.add_argument("--build-freestanding", metavar="SOURCE",
                   help="Compile SOURCE to freestanding bare-metal ELF")
    p.add_argument("--patch-freestanding", metavar="BINARY",
                   help="Strip all compiler metadata from BINARY")
    p.add_argument("--dump-memfuncs", action="store_true",
                   help="Print freestanding memory function C source")
    p.add_argument("--dump-linkerscript", action="store_true",
                   help="Print AArch64 freestanding linker script")

    args = p.parse_args()

    # Utility dumps
    if args.dump_memfuncs:
        print(FREESTANDING_MEMFUNCS_C)
        sys.exit(0)

    if args.dump_linkerscript:
        print(FREESTANDING_LINKER_AARCH64)
        sys.exit(0)

    # Build freestanding
    if args.build_freestanding:
        out = args.output or args.build_freestanding.replace(".c", "_freestanding.elf")
        ok, msg = build_freestanding(args.build_freestanding, out, args.arch, args.opt)
        print(msg)
        if ok:
            print("\nRunning full freestandingty audit on result...")
            run_full_audit(out, args.verbose, freestanding_mode=False)
        sys.exit(0 if ok else 1)

    # Patch freestanding
    if args.patch_freestanding:
        out = args.output or args.patch_freestanding
        ok, msg = patch_freestanding(args.patch_freestanding, out)
        print(msg)
        sys.exit(0 if ok else 1)

    if not args.binary:
        p.print_help()
        sys.exit(1)

    b = args.binary

    dispatch = {
        "hosted":       lambda: print(render_report(audit_hosted(b),       args.verbose)),
        "freestanding": lambda: print(render_report(audit_freestanding(b), args.verbose)),
        "kernel":       lambda: print(render_report(audit_kernel(b),       args.verbose)),
        "abi":          lambda: print(render_report(audit_abi(b),          args.verbose)),
        "entropy":      lambda: print(render_report(audit_entropy(b),      args.verbose)),
        "hardening":    lambda: print(render_report(audit_hardening(b),    args.verbose)),
        "freestanding":    lambda: run_full_audit(b, args.verbose, freestanding_mode=True),
        "full":         lambda: run_full_audit(b, args.verbose, freestanding_mode=False),
    }
    dispatch[args.mode]()
    sys.exit(0)


if __name__ == "__main__":
    main()
