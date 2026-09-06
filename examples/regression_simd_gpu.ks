:: Regression test: real SIMD + GPU (falls back to SIMD when no GPU)
import simd;
import gpu;

let n = 16;
let a = simd.alloc_f32(n);
let b = simd.alloc_f32(n);
let c = simd.alloc_f32(n);
for i in range(0, n) {
    simd.set_f32(a, i, 2.0);
    simd.set_f32(b, i, 3.0);
}

:: SIMD add: c = a + b = 5.0
simd.add_f32(a, b, c, n);
let addok = 1;
for i in range(0, n) {
    if (simd.get_f32(c, i) != 5.0) { addok = 0; }
}
let addres = "FAIL";
if (addok == 1) { addres = "PASS"; }
print("simd add   : " + addres);

:: SIMD sum: 16 * 5.0 = 80.0
let s = simd.sum_f32(c, n);
let sumres = "FAIL";
if (s == 80.0) { sumres = "PASS"; }
print("simd sum   : " + str(s) + " " + sumres);

:: SIMD dot: sum(a*b) = 16 * 6.0 = 96.0
let d = simd.dot_f32(a, b, n);
let dotres = "FAIL";
if (d == 96.0) { dotres = "PASS"; }
print("simd dot   : " + str(d) + " " + dotres);

:: GPU path (auto OpenCL/CUDA, else SIMD fallback)
let g = gpu.available();
print("gpu avail  : " + str(g));
gpu.add_f32(a, b, c, n);
let gpuc0 = gpu.get_f32(c, 0);
let gpuok = "FAIL";
if (gpuc0 == 5.0) { gpuok = "PASS"; }
print("gpu add c0 : " + str(gpuc0) + " " + gpuok);

simd.free_f32(a);
simd.free_f32(b);
simd.free_f32(c);
print("=== regression done ===");
