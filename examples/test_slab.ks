import ffi;
let slab = ffi.CDLL("/home/kali/KentScript/runtime/memory/ks_slab.so");
let barrier = slab.get_function("ks_barrier", [], ffi.c_void);
barrier.call();
print("Barrier called");
let malloc = slab.get_function("ks_malloc", [ffi.c_uint64], ffi.c_uint64);
let addr = malloc.call(64);
print("Allocated address: " + str(addr));
if addr != 0 {
    let free = slab.get_function("ks_free", [ffi.c_uint64], ffi.c_int64);
    free.call(addr);
    print("Freed");
}