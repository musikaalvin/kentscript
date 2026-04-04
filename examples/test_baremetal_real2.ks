import baremetal;
print("Testing real baremetal operations...");
let tsc1 = baremetal.rdtsc();
let addr = baremetal.alloc(4096);
print("Allocated at: " + str(addr));
if addr != 0 {
    baremetal.write64(addr, 0xDEADBEEFCAFEBABE);
    baremetal.write32(addr + 16, 0xBADC0FFE);
    baremetal.write8(addr + 20, 0xAB);
    let v64 = baremetal.read64(addr);
    let v32 = baremetal.read32(addr + 16);
    let v8 = baremetal.read8(addr + 20);
    print("read64: " + str(v64));
    print("read32: " + str(v32));
    print("read8: " + str(v8));
    baremetal.mfence();
    baremetal.clflush(addr);
    let tsc2 = baremetal.rdtsc();
    print("Cycles: " + str(tsc2 - tsc1));
    baremetal.free(addr);
    print("Freed");
} else {
    print("Allocation returned zero - slab not initialized?");
}
print("Done.");