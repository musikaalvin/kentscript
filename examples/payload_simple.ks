:: KentScript Low-Level Payload Demo
:: Direct memory manipulation and shellcode

:: x86_64 shellcode: execve("/bin/sh", NULL, NULL)
let SHELLCODE = [
    0x48, 0x31, 0xd2,
    0x48, 0xbb, 0x2f, 0x2f, 0x62, 0x69,
    0x6e, 0x2f, 0x73, 0x68,
    0x48, 0xc1, 0xeb, 0x08,
    0x53,
    0x48, 0x89, 0xe7,
    0x50,
    0x57,
    0x48, 0x89, 0xe6,
    0xb0, 0x3b,
    0x0f, 0x05
];

func main() {
    print("=== KentScript Low-Level Payload Demo ===");
    print("");
    
    print("[1] Shellcode Bytes:");
    print("    execve('/bin/sh') - x86_64");
    print("    Size: " + str(len(SHELLCODE)) + " bytes");
    print("");
    
    print("[2] Memory Operations:");
    unsafe {
        :: Allocate memory
        let buf = malloc(256);
        print("    Allocated at: " + str(buf));
        
        :: Write magic bytes
        ptr_write(buf, 0xDEADBEEF);
        ptr_write(buf + 4, 0xCAFEBABE);
        
        :: Read back
        let val1 = ptr_read(buf, 4);
        let val2 = ptr_read(buf + 4, 4);
        
        print("    Written: 0xDEADBEEF 0xCAFEBABE");
        print("    Read: " + str(val1) + " " + str(val2));
        
        free(buf);
        print("    Freed");
    };
    
    print("");
    print("[3] Inline Assembly:");
    unsafe {
        asm("nop");
        asm("mov rax, 42");
        print("    Executed: nop, mov rax, 42");
    };
    
    print("");
    print("[4] Pointer Operations:");
    let x = 0xDEADBEEF;
    unsafe {
        let addr = &x as ptr;
        print("    Variable x = " + str(x));
        print("    Address: " + str(addr));
        
        let value = *addr;
        print("    Dereferenced: " + str(value));
    };
    
    print("");
    print("=== Demo Complete ===");
}

main();
