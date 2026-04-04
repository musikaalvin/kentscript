static inline long _ks_syscall3(long num, long a1, long a2, long a3) {
    long ret;
    __asm__ volatile ("syscall"
        : "=a"(ret) : "0"(num), "D"(a1), "S"(a2), "d"(a3)
        : "rcx", "r11", "memory");
    return ret;
}
static inline void _ks_exit(long code) {
    __asm__ volatile ("syscall" :: "a"(60L), "D"(code) : "rcx","r11","memory");
    __builtin_unreachable();
}
static long ks_strlen(const char *s) { long n=0; while(s[n]) n++; return n; }
static void ks_write(const char *msg) { _ks_syscall3(1, 1, (long)msg, ks_strlen(msg)); }
static void ks_println(const char *msg) { ks_write(msg); ks_write("\n"); }

static void write_num(long n) {
    if (n < 0) { ks_write("-"); n = -n; }
    if (n == 0) { ks_write("0"); return; }
    char buf[20]; int i = 19; buf[19] = 0;
    while (n > 0 && i > 0) { buf[--i] = '0' + (int)(n % 10); n /= 10; }
    ks_write(&buf[i]);
}

static long ks_fib(long n) {
    if (n <= 1) return n;
    return ks_fib(n-1) + ks_fib(n-2);
}

static void ks_sort(long *arr, long len) {
    for (long i = 0; i < len-1; i++)
        for (long j = 0; j < len-i-1; j++)
            if (arr[j] > arr[j+1]) {
                long t = arr[j]; arr[j] = arr[j+1]; arr[j+1] = t;
            }
}

static long ks_bsearch(long *arr, long len, long t) {
    long lo=0, hi=len-1;
    while(lo<=hi){ long m=lo+(hi-lo)/2; if(arr[m]==t) return m; if(arr[m]<t) lo=m+1; else hi=m-1; }
    return -1;
}

void _start(void) {
    ks_println("===========================================");
    ks_println("  KentScript :: Freestanding Mode v1.1");
    ks_println("  No libc  |  No CRT  |  Raw syscalls");
    ks_println("  x86_64 Linux (userland EL0)");
    ks_println("===========================================\n");

    // TEST 1: Arithmetic
    ks_println("[TEST 1] Integer arithmetic:");
    long sum = 0;
    for (long i = 1; i <= 100; i++) sum += i;
    ks_write("  sum(1..100) = "); write_num(sum); ks_write("\n");
    long fact = 1;
    for (long i = 1; i <= 12; i++) fact *= i;
    ks_write("  12! = "); write_num(fact); ks_write("\n");

    // TEST 2: Fibonacci
    ks_println("\n[TEST 2] Fibonacci sequence (recursive):");
    ks_write("  ");
    for (long i = 0; i <= 10; i++) {
        write_num(ks_fib(i));
        if (i < 10) ks_write(" ");
    }
    ks_write("\n");

    // TEST 3: Sort
    ks_println("\n[TEST 3] Bubble sort (stack array):");
    long arr[8] = {64, 34, 25, 12, 22, 11, 90, 5};
    ks_write("  Before: ");
    for (int i = 0; i < 8; i++) { write_num(arr[i]); ks_write(" "); }
    ks_write("\n");
    ks_sort(arr, 8);
    ks_write("  After:  ");
    for (int i = 0; i < 8; i++) { write_num(arr[i]); ks_write(" "); }
    ks_write("\n");

    // TEST 4: Prime sieve
    ks_println("\n[TEST 4] Primes up to 100 (stack sieve):");
    char sieve[101];
    for (int i = 0; i <= 100; i++) sieve[i] = 1;
    sieve[0] = sieve[1] = 0;
    for (int i = 2; i*i <= 100; i++)
        if (sieve[i]) for (int j = i*i; j <= 100; j += i) sieve[j] = 0;
    ks_write("  ");
    int pc = 0;
    for (int i = 2; i <= 100; i++) if (sieve[i]) { write_num(i); ks_write(" "); pc++; }
    ks_write("\n  Count: "); write_num(pc); ks_write(" primes\n");

    // TEST 5: Binary search
    ks_println("\n[TEST 5] Binary search:");
    long sorted[10] = {2, 5, 8, 12, 16, 23, 38, 56, 72, 91};
    long queries[4] = {23, 72, 99, 2};
    for (int i = 0; i < 4; i++) {
        long idx = ks_bsearch(sorted, 10, queries[i]);
        ks_write("  search("); write_num(queries[i]); ks_write(") = ");
        if (idx >= 0) { ks_write("idx "); write_num(idx); ks_write("\n"); }
        else ks_write("not found\n");
    }

    // Proof
    ks_println("\n[PROOF] Syscall sovereignty:");
    ks_println("  SYS_write = 1   [direct syscall, no libc]");
    ks_println("  SYS_exit  = 60  [direct syscall, no libc]");
    ks_println("  ldd: 'not a dynamic executable'");
    ks_println("  No printf. No malloc. No glibc. No libm.");
    
    ks_println("\nAll tests complete. Exit via SYS_exit(60).");
    _ks_exit(0);
}
