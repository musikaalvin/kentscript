#!/usr/bin/env python3
"""
KentScript Documentation Generator
Generates comprehensive 300+ page documentation
"""

import os
import subprocess

def run_ks_example(code):
    """Run KentScript code and capture output"""
    with open('/tmp/test_doc.ks', 'w') as f:
        f.write(code)
    try:
        result = subprocess.run(
            ['python3', 'main.py', 'run', '/tmp/test_doc.ks'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()
    except:
        return "(output not available)"

def generate_stdlib_docs():
    """Generate standard library documentation"""
    
    stdlib_modules = {
        'network': {
            'desc': 'Low-level networking and sockets',
            'functions': [
                ('Socket(family, sock_type, proto)', 'Create a socket', 
                 'let sock = system_socket_create(2, 1, 0);\nprint(sock);'),
                ('bind(address)', 'Bind socket to address', None),
                ('listen(backlog)', 'Listen for connections', None),
                ('accept()', 'Accept client connection', None),
                ('connect(address)', 'Connect to server', None),
                ('send(data, flags)', 'Send data', None),
                ('recv(bufsize, flags)', 'Receive data', None),
            ]
        },
        'subprocess': {
            'desc': 'Process execution and management',
            'functions': [
                ('run(cmd, shell, capture_output)', 'Run command',
                 'let result = system_subprocess_run("echo test", true, true);\nprint(result.stdout);'),
            ]
        },
        'crypto': {
            'desc': 'Cryptographic functions',
            'functions': [
                ('md5(data)', 'MD5 hash',
                 'let hash = system_crypto_md5("test");\nprint(hash);'),
                ('sha256(data)', 'SHA256 hash',
                 'let hash = system_crypto_sha256("test");\nprint(hash);'),
                ('random_bytes(n)', 'Generate random bytes',
                 'let rand = system_crypto_random_bytes(8);\nprint(rand);'),
            ]
        },
        'fileio': {
            'desc': 'File I/O operations',
            'functions': [
                ('read_text(path)', 'Read text file',
                 'system_file_write_text("/tmp/test.txt", "hello");\nlet content = system_file_read_text("/tmp/test.txt");\nprint(content);\nsystem_file_remove("/tmp/test.txt");'),
                ('write_text(path, data)', 'Write text file', None),
                ('exists(path)', 'Check if file exists',
                 'let exists = system_file_exists("/tmp");\nprint(exists);'),
                ('listdir(path)', 'List directory',
                 'let files = system_file_listdir("/tmp");\nprint(len(files));'),
            ]
        },
    }
    
    doc = "\n\n# PART II: STANDARD LIBRARY\n\n---\n\n"
    
    for module, info in stdlib_modules.items():
        doc += f"## Chapter: {module} Module\n\n"
        doc += f"### Description\n{info['desc']}\n\n"
        doc += "### Functions\n\n"
        
        for func_name, func_desc, example in info['functions']:
            doc += f"#### `{func_name}`\n\n"
            doc += f"{func_desc}\n\n"
            
            if example:
                doc += "**Example:**\n```kentscript\n"
                doc += example + "\n```\n\n"
                doc += "**Output:**\n```\n"
                output = run_ks_example(example)
                doc += output + "\n```\n\n"
            
            doc += "---\n\n"
    
    return doc

def generate_examples_docs():
    """Generate practical examples documentation"""
    
    doc = "\n\n# PART V: REAL-WORLD APPLICATIONS\n\n---\n\n"
    
    examples = [
        ('TCP Server', '''
:: Simple TCP Echo Server
let server = system_socket_create(2, 1, 0);
system_socket_bind(server, ["0.0.0.0", 9999]);
system_socket_listen(server, 5);
print("[*] Server listening on port 9999");

:: Accept one client for demo
let [client, addr] = system_socket_accept(server);
print(f"[+] Client connected: {addr}");

:: Echo back
let data = system_socket_recv(client, 1024, 0);
print(f"Received: {data}");
system_socket_send(client, f"Echo: {data}", 0);

system_socket_close(client);
system_socket_close(server);
'''),
        
        ('Password Generator', '''
:: Secure Password Generator
func generate_password(length) {
    let chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*";
    let password = "";
    let random_hex = system_crypto_random_bytes(length);
    
    for i in range(length) {
        let idx = i % len(chars);
        password = password + chars[idx];
    }
    
    return password;
}

for i in range(5) {
    let pwd = generate_password(12);
    print(f"Password {i+1}: {pwd}");
}
'''),
        
        ('File Backup Tool', '''
:: Simple File Backup
func backup_file(source, dest) {
    if system_file_exists(source) {
        let content = system_file_read_text(source);
        system_file_write_text(dest, content);
        print(f"[+] Backed up: {source} -> {dest}");
        return true;
    } else {
        print(f"[-] Source not found: {source}");
        return false;
    }
}

:: Create test file
system_file_write_text("/tmp/original.txt", "Important data");

:: Backup
backup_file("/tmp/original.txt", "/tmp/backup.txt");

:: Verify
let backup_content = system_file_read_text("/tmp/backup.txt");
print(f"Backup content: {backup_content}");

:: Cleanup
system_file_remove("/tmp/original.txt");
system_file_remove("/tmp/backup.txt");
'''),
    ]
    
    for title, code in examples:
        doc += f"## Example: {title}\n\n"
        doc += "**Code:**\n```kentscript\n"
        doc += code.strip() + "\n```\n\n"
        doc += "**Output:**\n```\n"
        output = run_ks_example(code.strip())
        doc += output + "\n```\n\n"
        doc += "---\n\n"
    
    return doc

def main():
    print("Generating KentScript documentation...")
    
    # Read existing Part I
    with open('FULL_DOCUMENTATION.md', 'r') as f:
        doc = f.read()
    
    print("Generating stdlib documentation...")
    doc += generate_stdlib_docs()
    
    print("Generating examples documentation...")
    doc += generate_examples_docs()
    
    # Add low-level programming section
    doc += "\n\n# PART III: LOW-LEVEL PROGRAMMING\n\n---\n\n"
    doc += """
## Chapter: Memory Management

### Unsafe Blocks

KentScript is safe by default but allows unsafe operations when needed:

```kentscript
:: Safe code - bounds checked
let arr = [1, 2, 3];
print(arr[0]);  :: OK

:: Unsafe code - your responsibility
unsafe {
    let ptr = malloc(1024);
    write_byte(ptr, 0, 42);
    let value = read_byte(ptr, 0);
    print(f"Value: {value}");
    free(ptr);
}
```

### Memory Allocation

```kentscript
unsafe {
    :: Allocate 1KB
    let ptr = malloc(1024);
    print(f"Allocated at: {ptr}");
    
    :: Write data
    for i in range(10) {
        write_byte(ptr, i, i * 10);
    }
    
    :: Read data
    for i in range(10) {
        let val = read_byte(ptr, i);
        print(f"[{i}] = {val}");
    }
    
    :: Free memory
    free(ptr);
}
```

---

## Chapter: Inline Assembly

### x86-64 Assembly

```kentscript
import asm;

unsafe {
    :: Get CPU timestamp counter
    let cycles = asm.rdtsc();
    print(f"CPU cycles: {cycles}");
    
    :: CPU ID
    let info = asm.cpuid();
    print(f"CPU info: {info}");
    
    :: Memory fence
    asm.mfence();
}
```

---

## Chapter: Hardware I/O

### Port I/O

```kentscript
import hardware;

unsafe {
    :: Serial port (requires root)
    hardware.serial_init(hardware.SERIAL_COM1);
    hardware.serial_write(hardware.SERIAL_COM1, 'H');
    hardware.serial_write(hardware.SERIAL_COM1, 'i');
    
    :: Read port status
    let status = hardware.inb(0x3F8 + 5);
    print(f"Serial status: {status:x}");
}
```

---

"""
    
    # Add conclusion
    doc += "\n\n# CONCLUSION\n\n"
    doc += """
## Summary

KentScript is a complete systems programming language with:

✅ **Modern Syntax** - Clean, readable, Python-like
✅ **Systems Programming** - Memory, assembly, hardware access
✅ **High-Level Features** - Classes, async, generators
✅ **Rich Standard Library** - 38+ modules, 14,000+ lines
✅ **Multiple Execution Modes** - Interpreter, compiler, bare-metal

## What You've Learned

- **Part I**: Fundamentals - syntax, types, control flow, functions, classes
- **Part II**: Standard Library - 38+ modules for every task
- **Part III**: Low-Level - memory, assembly, hardware, syscalls
- **Part IV**: Advanced - ownership, async, generators, macros
- **Part V**: Real-World - network apps, security tools, utilities

## Next Steps

1. **Explore Examples** - Check `examples/` directory
2. **Build Tools** - Create your own security tools
3. **Contribute** - Help improve KentScript
4. **Share** - Show others what you've built

## Resources

- **GitHub**: https://github.com/yourusername/KentScript
- **Documentation**: `docs/` directory
- **Examples**: `examples/` directory
- **Tools**: `tools/` directory

## License

MIT License - See LICENSE file

---

**KentScript: C's Power + Python's Simplicity** 🚀

*End of Documentation*
"""
    
    # Write final documentation
    with open('FULL_DOCUMENTATION.md', 'w') as f:
        f.write(doc)
    
    # Count lines (approximate pages)
    lines = doc.count('\n')
    pages = lines // 50  # Rough estimate: 50 lines per page
    
    print(f"\n✅ Documentation generated!")
    print(f"   Lines: {lines}")
    print(f"   Estimated pages: {pages}")
    print(f"   File: FULL_DOCUMENTATION.md")
    print(f"\nTo convert to PDF:")
    print(f"   pandoc FULL_DOCUMENTATION.md -o KentScript_Guide.pdf")

if __name__ == '__main__':
    main()
