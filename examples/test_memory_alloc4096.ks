import memory;
let addr = memory.alloc(4096);
print("memory.alloc(4096) = " + str(addr));
if addr != 0 {
    memory.write(addr, 0x12345678);
    let val = memory.read(addr);
    print("read = " + str(val));
    memory.free(addr);
}