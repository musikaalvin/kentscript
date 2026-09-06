:: KentScript Real SIMD demo
:: Portable, hardware-native vectorization (NEON on ARM, AVX/AVX2/AVX-512 on x86).
:: Works identically in interpreter (NumPy-backed) and compiled (ks_simd.h) modes.

print("=== KentScript Real SIMD ===");
print("arch: " + simd.arch());
let wbytes = simd.width();
print("simd width bytes: " + str(wbytes));

let n = 1024;

:: ---- float32 vector add ----
let a = simd.alloc_f32(n);
let b = simd.alloc_f32(n);
let c = simd.alloc_f32(n);

for i in range(0, n) {
    simd.set_f32(a, i, 1.5);
    simd.set_f32(b, i, 2.5);
}

simd.add_f32(a, b, c, n);
simd.scale_f32(c, 2.0, n);

let c0 = simd.get_f32(c, 0);
let csum = simd.sum_f32(c, n);
let cdot = simd.dot_f32(a, b, n);
print("c[0]  = " + str(c0));
print("sum   = " + str(csum));
print("dot   = " + str(cdot));
print("exp c[0]=8.0  sum=8192.0  dot=3840.0");

:: ---- int64 vector mul + dot ----
let x = simd.alloc_i64(n);
let y = simd.alloc_i64(n);
let z = simd.alloc_i64(n);

for i in range(0, n) {
    simd.set_i64(x, i, i);
    simd.set_i64(y, i, 2);
}

simd.mul_i64(x, y, z, n);
let z10 = simd.get_i64(z, 10);
let xyd = simd.dot_i64(x, y, n);
print("z[10] = " + str(z10));
print("dot   = " + str(xyd));

:: ---- fused multiply-add: w = x*y + z ----
let w = simd.alloc_i64(n);
simd.fma_i64(x, y, z, w, n);
let w7 = simd.get_i64(w, 7);
print("w[7]  = " + str(w7));

simd.free_f32(a); simd.free_f32(b); simd.free_f32(c);
simd.free_i64(x); simd.free_i64(y); simd.free_i64(z);
simd.free_i64(w);
print("=== done ===");
