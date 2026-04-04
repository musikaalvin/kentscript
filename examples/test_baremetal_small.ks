import baremetal;
print("Testing baremetal with small allocation...");
let addr = baremetal.alloc(64);
print("Allocated at: " + str(addr));
if addr != 0 {
    baremetal.write64(addr, 0xDEADBEEFCAFEBABE);
    baremetal.write32(addr + 8, 0xBADC0FFE);
    baremetal.write8(addr + 12, 0xAB);
    let v64 = baremetal.read64(addr);
    let v32 = baremetal.read32(addr + 8);
    let v8 = baremetal.read8(addr + 12);
    print("read64: " + str(v64));
    print("read32: " + str(v32));
    print("read8: " + str(v8));
    baremetal.free(addr);
    print("Freed");
} else {
    print("Allocation failed");
}