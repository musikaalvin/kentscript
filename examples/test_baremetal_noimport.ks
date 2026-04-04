func main() {
    let tsc1 = baremetal.rdtsc();
    let addr = baremetal.alloc(4096);
    print("Allocated at: " + str(addr));
    baremetal.write64(addr, 0xDEADBEEFCAFEBABE);
    let v64 = baremetal.read64(addr);
    print("Read: " + str(v64));
}
main();