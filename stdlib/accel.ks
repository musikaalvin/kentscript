:: ============================================================================
:: KentScript Acceleration Helpers  (stdlib/accel.ks)
:: ----------------------------------------------------------------------------
:: Pythonistic, Mojo-style wrappers over the real hardware `simd` / `gpu`
:: modules. These are convenience functions; the underlying `simd.*` /
:: `gpu.*` calls transpile to genuine NEON / AVX / AVX-512 / OpenCL / CUDA
:: kernels (with automatic CPU-SIMD fallback when no GPU is present).
::
:: Usage:
::     import accel;
::     let c = accel.vector_add([1.0,2.0,3.0], [4.0,5.0,6.0]);
::     let s = accel.vector_dot([1.0,2.0], [3.0,4.0]);
::     let g = accel.gpu_vector_add(a, b);   :: runs on GPU if available
:: ============================================================================

import simd;
import gpu;

:: Element-wise a + b  ->  new list (real SIMD)
func vector_add(a, b) {
    let n = len(a);
    let pa = simd.alloc_f32(n);
    let pb = simd.alloc_f32(n);
    let pc = simd.alloc_f32(n);
    for i in range(0, n) {
        simd.set_f32(pa, i, a[i]);
        simd.set_f32(pb, i, b[i]);
    }
    simd.add_f32(pa, pb, pc, n);
    let out = [];
    for i in range(0, n) {
        out = out + [simd.get_f32(pc, i)];
    }
    simd.free_f32(pa);
    simd.free_f32(pb);
    simd.free_f32(pc);
    return out;
}

:: Element-wise a * s  ->  new list (real SIMD)
func vector_scale(a, s) {
    let n = len(a);
    let pa = simd.alloc_f32(n);
    for i in range(0, n) {
        simd.set_f32(pa, i, a[i]);
    }
    simd.scale_f32(pa, s, n);
    let out = [];
    for i in range(0, n) {
        out = out + [simd.get_f32(pa, i)];
    }
    simd.free_f32(pa);
    return out;
}

:: Dot product a . b  ->  scalar (real SIMD reduction)
func vector_dot(a, b) {
    let n = len(a);
    let pa = simd.alloc_f32(n);
    let pb = simd.alloc_f32(n);
    for i in range(0, n) {
        simd.set_f32(pa, i, a[i]);
        simd.set_f32(pb, i, b[i]);
    }
    let d = simd.dot_f32(pa, pb, n);
    simd.free_f32(pa);
    simd.free_f32(pb);
    return d;
}

:: Element-wise a + b on the GPU (OpenCL / CUDA) when available,
:: otherwise transparently on the CPU SIMD path.
func gpu_vector_add(a, b) {
    let n = len(a);
    let pa = gpu.alloc_f32(n);
    let pb = gpu.alloc_f32(n);
    let pc = gpu.alloc_f32(n);
    for i in range(0, n) {
        gpu.set_f32(pa, i, a[i]);
        gpu.set_f32(pb, i, b[i]);
    }
    gpu.add_f32(pa, pb, pc, n);
    let out = [];
    for i in range(0, n) {
        out = out + [gpu.get_f32(pc, i)];
    }
    gpu.free_f32(pa);
    gpu.free_f32(pb);
    gpu.free_f32(pc);
    return out;
}
