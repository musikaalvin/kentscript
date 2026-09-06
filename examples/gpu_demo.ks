:: KentScript Real GPU demo (OpenCL backend; auto SIMD fallback when no GPU)
print("=== KentScript Real GPU ===");
let gname = gpu.name();
print("gpu name: " + gname);
print("gpu available: " + str(gpu.available()));
print("cuda available: " + str(gpu.cuda_available()));
print("cuda name: " + str(gpu.cuda_name()));

let n = 1024;
let a = gpu.alloc_f32(n);
let b = gpu.alloc_f32(n);
let c = gpu.alloc_f32(n);

for i in range(0, n) {
    gpu.set_f32(a, i, 1.5);
    gpu.set_f32(b, i, 2.5);
}

gpu.add_f32(a, b, c, n);
gpu.scale_f32(c, 2.0, n);

let c0 = gpu.get_f32(c, 0);
let csum = gpu.sum_f32(c, n);
print("c[0] = " + str(c0));
print("sum  = " + str(csum));
print("exp c[0]=8.0 sum=8192.0");

gpu.free_f32(a); gpu.free_f32(b); gpu.free_f32(c);
print("=== done ===");
