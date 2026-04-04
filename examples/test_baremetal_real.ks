import baremetal;

func main() {
    let tsc1 = baremetal.rdtsc();
    let addr = baremetal.alloc(4096);
    print("Allocated at: " + str(addr));

    baremetal.write64(addr, 0xDEADBEEFCAFEBABE);
    baremetal.write32(addr + 16, 0xBADC0FFE);
    baremetal.write8(addr + 20, 0xAB);

    let v64 = baremetal.read64(addr);
    let v32 = baremetal.read32(addr + 16);
    let v8  = baremetal.read8(addr + 20);

    baremetal.mfence();
    baremetal.clflush(addr);

    let tsc2 = baremetal.rdtsc();
    print("Cycles: " + str(tsc2 - tsc1));
}
main();