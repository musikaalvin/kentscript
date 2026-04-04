import baremetal;
print("Testing baremetal module...");
let tsc = baremetal.rdtsc();
print("rdtsc: " + str(tsc));
let addr = baremetal.alloc(4096);
print("Allocated at: " + str(addr));
if addr != 0 {
    baremetal.write64(addr, 0xDEADBEEFCAFEBABE);
    let val = baremetal.read64(addr);
    print("Read back: " + str(val));
    baremetal.free(addr);
    print("Freed");
}
print("Done.");