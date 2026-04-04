import memory;
let addr = memory.alloc(64);
print("memory.alloc address: " + str(addr));
if addr != 0 {
    memory.write(addr, 0xDEADBEEF);
    let val = memory.read(addr);
    print("Read back: " + str(val));
    memory.free(addr);
}