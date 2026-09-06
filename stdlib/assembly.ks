:: asm - High-level inline assembly interface

:: Execute inline assembly
func exec(code: str) {
    unsafe {
        asm(code);
    }
}

:: Common x86-64 operations
func nop() {
    unsafe { asm("nop"); }
}

func pause() {
    unsafe { asm("pause"); }
}

func cpuid() -> dict {
    unsafe {
        let eax = 0;
        let ebx = 0;
        let ecx = 0;
        let edx = 0;
        asm("cpuid" : "=a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx) : "a"(0));
        return {"eax": eax, "ebx": ebx, "ecx": ecx, "edx": edx};
    }
}

func rdtsc() -> int {
    unsafe {
        let low = 0;
        let high = 0;
        asm("rdtsc" : "=a"(low), "=d"(high));
        return (high << 32) | low;
    }
}

func cli() {
    unsafe { asm("cli"); }
}

func sti() {
    unsafe { asm("sti"); }
}

func hlt() {
    unsafe { asm("hlt"); }
}

:: Memory barriers
func mfence() {
    unsafe { asm("mfence"); }
}

func lfence() {
    unsafe { asm("lfence"); }
}

func sfence() {
    unsafe { asm("sfence"); }
}

:: Atomic operations
func xchg(ptr: ptr, value: int) -> int {
    unsafe {
        let old = 0;
        asm("xchg %0, %1" : "=r"(old), "+m"(*ptr) : "0"(value));
        return old;
    }
}

func cmpxchg(ptr: ptr, expected: int, desired: int) -> int {
    unsafe {
        let old = expected;
        asm("lock cmpxchg %2, %1" : "=a"(old), "+m"(*ptr) : "r"(desired), "0"(old));
        return old;
    }
}

:: ARM64 operations
func arm_nop() {
    unsafe { asm("nop"); }
}

func arm_yield() {
    unsafe { asm("yield"); }
}

func arm_wfe() {
    unsafe { asm("wfe"); }
}

func arm_wfi() {
    unsafe { asm("wfi"); }
}

func arm_dmb() {
    unsafe { asm("dmb sy"); }
}

func arm_dsb() {
    unsafe { asm("dsb sy"); }
}

func arm_isb() {
    unsafe { asm("isb"); }
}

export {
    exec, nop, pause, cpuid, rdtsc,
    cli, sti, hlt,
    mfence, lfence, sfence,
    xchg, cmpxchg,
    arm_nop, arm_yield, arm_wfe, arm_wfi,
    arm_dmb, arm_dsb, arm_isb
};
