:: KentScript - Copy & Paste Examples

All examples below can be copied directly and saved as `.ks` files

---

::# MINIMAL TEST (copy & run immediately)

```kentscript
import syscall;
let pid = syscall.getpid();
print("PID:", pid);

unsafe {
    let ptr = malloc(256);
    write_byte(ptr, 0, 65);
    print("Memory:", read_byte(ptr, 0));
    free(ptr);
};
```

**To use:**
1. Copy code above (select from ``` to ```)
2. Create file: `nano test.ks`
3. Paste code
4. Save: Ctrl+X, Y, Enter
5. Run: `python3 kentscript_real_syscalls.py test.ks`

---

::# QUICK MEMORY TEST

```kentscript
unsafe {
    let ptr = malloc(512);
    
    :: Write values
    write_byte(ptr, 0, 0x41);
    write_byte(ptr, 1, 0x42);
    write_byte(ptr, 2, 0x43);
    
    :: Read back
    let a = read_byte(ptr, 0);
    let b = read_byte(ptr, 1);
    let c = read_byte(ptr, 2);
    
    print("Values:", a, b, c);
    
    free(ptr);
};
```

---

::# QUICK FILE TEST

```kentscript
let fd = syscall.open("/tmp/test.txt", 0o666);
syscall.write(fd, "Hello from KentScript!");
syscall.close(fd);

let stats = syscall.stat("/tmp/test.txt");
print("File size:", stats["size"]);
```

---

::# QUICK STRING TEST

```kentscript
unsafe {
    let mem = malloc(256);
    
    write_string(mem, 0, "KentScript");
    write_string(mem, 20, "Rocks!");
    
    let s1 = read_string(mem, 0);
    let s2 = read_string(mem, 20);
    
    print(s1, " ", s2);
    
    free(mem);
};
```

---

::# QUICK HARDWARE TEST

```kentscript
unsafe {
    :: I/O port (needs root)
    let result = write_port(0x3F8, 0x41);
    print("Port write:", result);
    
    :: MMIO (needs root)
    mmio_write(0xFED00000, 0, 0xDEAD);
    let val = mmio_read(0xFED00000, 0);
    print("MMIO:", val);
};
```

---

::# QUICK SYSCALL TEST

```kentscript
print("PID:", syscall.getpid());
print("TID:", syscall.gettid());
print("CWD:", syscall.getcwd());

let fd = syscall.open("/tmp/ks_test.txt", 0o666);
print("FD:", fd);
syscall.close(fd);
```

---

::# QUICK MATH TEST

```kentscript
let p1 = syscall.getpid();
let p2 = syscall.getpid();

let sum = p1 + p2;
let prod = p1 * 2;
let div = p1 / 2;

print("Sum:", sum);
print("Product:", prod);
print("Division:", div);
```

---

::# QUICK LOOP TEST

```kentscript
print("Counting to 10:");
for i in range(11) {
    print(i);
};

print("Memory pattern:");
unsafe {
    let ptr = malloc(100);
    for j in range(10) {
        write_byte(ptr, j, j * 10);
    };
    for j in range(10) {
        print(read_byte(ptr, j));
    };
    free(ptr);
};
```

---

::# QUICK FUNCTION TEST

```kentscript
func add(a, b) {
    return a + b;
};

func multiply(x, y) {
    return x * y;
};

print("5 + 3 =", add(5, 3));
print("5 * 3 =", multiply(5, 3));
```

---

::# QUICK IF TEST

```kentscript
let x = 10;
let y = 5;

if x > y {
    print("x is greater");
};

if x == y {
    print("x equals y");
} else {
    print("x does not equal y");
};
```

---

::# QUICK BLOCK OPS TEST

```kentscript
unsafe {
    let src = malloc(256);
    let dst = malloc(256);
    
    :: Fill source
    memset(src, 0, 0xAA, 32);
    print("Filled src with 0xAA");
    
    :: Copy
    memcpy(dst, 0, src, 0, 32);
    print("Copied 32 bytes");
    
    :: Verify
    let val = read_byte(dst, 0);
    print("Verify:", val);
    
    free(src);
    free(dst);
};
```

---

::# QUICK WORD TEST

```kentscript
unsafe {
    let ptr = malloc(256);
    
    :: Write 32-bit words
    write_word(ptr, 0, 0xDEADBEEF, 4);
    write_word(ptr, 4, 0xCAFEBABE, 4);
    
    :: Read back
    let w1 = read_word(ptr, 0, 4);
    let w2 = read_word(ptr, 4, 4);
    
    print("Word1:", w1);
    print("Word2:", w2);
    
    free(ptr);
};
```

---

::# COPY-PASTE ONE-LINERS

Run one command to create and execute test:

```bash
python3 kentscript_real_syscalls.py << 'EOF'
print("Hello from KentScript!");
let pid = syscall.getpid();
print("PID:", pid);
unsafe {
    let x = malloc(100);
    write_byte(x, 0, 42);
    print("Memory test:", read_byte(x, 0));
    free(x);
};
EOF
```

---

::# FASTEST WAY TO TEST

1. **Create test.ks**
```bash
cat > test.ks << 'EOF'
print("Testing KentScript!");
let pid = syscall.getpid();
print("PID:", pid);
unsafe {
    let ptr = malloc(256);
    write_string(ptr, 0, "Works!");
    print(read_string(ptr, 0));
    free(ptr);
};
EOF
```

2. **Run it**
```bash
python3 kentscript_real_syscalls.py test.ks
```

Done! 🚀

---

::# ALL LANGUAGE FEATURES

::## Variables
```kentscript
let x = 5;
let name = "Alice";
let list = [1, 2, 3];
let dict = {"key": "value"};
```

::## Functions
```kentscript
func add(a, b) {
    return a + b;
};

let result = add(10, 20);
```

::## Comments
```kentscript
:: This is a comment
:: Everything after :: is ignored
```

::## Control Flow
```kentscript
if x > 5 {
    print("x is big");
};

for i in range(10) {
    print(i);
};

while x < 100 {
    x = x + 1;
};
```

::## Memory (Unsafe)
```kentscript
unsafe {
    let ptr = malloc(256);
    write_byte(ptr, 0, 65);
    let val = read_byte(ptr, 0);
    free(ptr);
};
```

::## System Calls
```kentscript
let pid = syscall.getpid();
let cwd = syscall.getcwd();
let fd = syscall.open("/tmp/test", 0o666);
syscall.close(fd);
```

---

::# RUNNING TESTS

**Simple (memory & basic syscalls):**
```bash
python3 kentscript_real_syscalls.py test.ks
```

**With root (hardware access):**
```bash
sudo python3 kentscript_real_syscalls.py test.ks
```

**Show syscalls (educational):**
```bash
strace -e trace=open,read,write,mmap python3 kentscript_real_syscalls.py test.ks
```

---

That's it! Copy any example, save as `.ks`, run with `python3 kentscript_real_syscalls.py yourfile.ks` ✅
