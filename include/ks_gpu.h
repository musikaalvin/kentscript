/*
 * ks_gpu.h - KentScript Real GPU Acceleration Layer (OpenCL)
 * =========================================================
 * True heterogeneous GPU compute via OpenCL, with an automatic,
 * correct CPU (ks_simd) fallback when no OpenCL platform exists.
 *
 * Design notes (2026 best practice):
 *   - OpenCL is the most PORTABLE GPGPU API (NVIDIA / AMD / Intel / ARM
 *     Mali / Qualcomm Adreno / Apple / FPGAs) - one kernel runs everywhere.
 *   - The OpenCL library is loaded at RUNTIME via dlopen (libOpenCL.so /
 *     OpenCL.dll). There is NO link-time dependency, so binaries built with
 *     this layer run on machines without any GPU driver (they silently use
 *     the SIMD CPU fallback, which is still real vectorized code).
 *   - Kernels are generated as OpenCL C strings and compiled on-device by
 *     the driver - exactly the model Mojo/MLIR targets for GPU offload.
 *   - CUDA is structured as a secondary backend (see ks_gpu_cuda note); the
 *     OpenCL path is the default portable one.
 */

#ifndef KS_GPU_H
#define KS_GPU_H

#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <dlfcn.h>

#ifdef __cplusplus
extern "C" {
#endif

#include "ks_simd.h"

/* ---- opaque OpenCL handles (we dlopen, no cl.h needed) ----------- */
typedef void *ks_cl_obj;
typedef int   ks_cl_int;
typedef unsigned int ks_cl_uint;
typedef size_t ks_cl_size;

/* Subset of OpenCL functions we use, resolved via dlsym */
typedef ks_cl_int (*PFN_clGetPlatformIDs)(ks_cl_uint, ks_cl_obj *, ks_cl_uint *);
typedef ks_cl_int (*PFN_clGetDeviceIDs)(ks_cl_obj, ks_cl_uint, ks_cl_uint, ks_cl_obj *, ks_cl_uint *);
typedef ks_cl_obj  (*PFN_clCreateContext)(const void *, ks_cl_uint, const ks_cl_obj *,
                                           void (*)(const char *, const void *, size_t, void *),
                                           void *, ks_cl_int *);
typedef ks_cl_obj  (*PFN_clCreateCommandQueue)(ks_cl_obj, ks_cl_obj, ks_cl_uint, ks_cl_int *);
typedef ks_cl_obj  (*PFN_clCreateBuffer)(ks_cl_obj, ks_cl_uint, ks_cl_size, void *, ks_cl_int *);
typedef ks_cl_obj  (*PFN_clCreateProgramWithSource)(ks_cl_obj, ks_cl_uint, const char **,
                                                     const ks_cl_size *, ks_cl_int *);
typedef ks_cl_int  (*PFN_clBuildProgram)(ks_cl_obj, ks_cl_uint, const ks_cl_obj *,
                                          const char *, void (*)(ks_cl_obj, void *), void *);
typedef ks_cl_obj  (*PFN_clCreateKernel)(ks_cl_obj, const char *, ks_cl_int *);
typedef ks_cl_int  (*PFN_clSetKernelArg)(ks_cl_obj, ks_cl_uint, ks_cl_size, const void *);
typedef ks_cl_int  (*PFN_clEnqueueNDRangeKernel)(ks_cl_obj, ks_cl_obj, ks_cl_uint,
                                                  const ks_cl_size *, const ks_cl_size *,
                                                  const ks_cl_size *, ks_cl_uint,
                                                  const ks_cl_obj *, ks_cl_obj *);
typedef ks_cl_int  (*PFN_clEnqueueWriteBuffer)(ks_cl_obj, ks_cl_obj, ks_cl_uint, ks_cl_size,
                                               ks_cl_size, const void *, ks_cl_uint,
                                               const ks_cl_obj *, ks_cl_obj *);
typedef ks_cl_int  (*PFN_clEnqueueReadBuffer)(ks_cl_obj, ks_cl_obj, ks_cl_uint, ks_cl_size,
                                              ks_cl_size, void *, ks_cl_uint,
                                              const ks_cl_obj *, ks_cl_obj *);
typedef ks_cl_int  (*PFN_clFinish)(ks_cl_obj);
typedef ks_cl_int  (*PFN_clGetDeviceInfo)(ks_cl_obj, ks_cl_uint, ks_cl_size, void *, ks_cl_size *);
typedef ks_cl_int  (*PFN_clReleaseMemObject)(ks_cl_obj);
typedef ks_cl_int  (*PFN_clReleaseKernel)(ks_cl_obj);
typedef ks_cl_int  (*PFN_clReleaseProgram)(ks_cl_obj);
typedef ks_cl_int  (*PFN_clReleaseCommandQueue)(ks_cl_obj);
typedef ks_cl_int  (*PFN_clReleaseContext)(ks_cl_obj);

typedef struct {
    void *lib;
    int   ready;
    ks_cl_obj context;
    ks_cl_obj device;
    ks_cl_obj queue;
    char   name[128];
    PFN_clGetPlatformIDs        clGetPlatformIDs;
    PFN_clGetDeviceIDs          clGetDeviceIDs;
    PFN_clCreateContext         clCreateContext;
    PFN_clCreateCommandQueue    clCreateCommandQueue;
    PFN_clCreateBuffer          clCreateBuffer;
    PFN_clCreateProgramWithSource clCreateProgramWithSource;
    PFN_clBuildProgram          clBuildProgram;
    PFN_clCreateKernel          clCreateKernel;
    PFN_clSetKernelArg          clSetKernelArg;
    PFN_clEnqueueNDRangeKernel  clEnqueueNDRangeKernel;
    PFN_clEnqueueWriteBuffer    clEnqueueWriteBuffer;
    PFN_clEnqueueReadBuffer     clEnqueueReadBuffer;
    PFN_clFinish                clFinish;
    PFN_clGetDeviceInfo         clGetDeviceInfo;
    PFN_clReleaseMemObject      clReleaseMemObject;
    PFN_clReleaseKernel         clReleaseKernel;
    PFN_clReleaseProgram        clReleaseProgram;
    PFN_clReleaseCommandQueue   clReleaseCommandQueue;
    PFN_clReleaseContext        clReleaseContext;
} ks_gpu_state;

static ks_gpu_state _ks_gpu = {0};

static void *_ks_gpu_dlsym(void *lib, const char *name) {
    void *p = NULL;
    if (lib) p = dlsym(lib, name);
    return p;
}

/* Initialize OpenCL by dlopen-ing the vendor library. Returns 1 on success. */
static int ks_gpu_init(void) {
    if (_ks_gpu.ready || _ks_gpu.lib) return _ks_gpu.ready;
    const char *candidates[] = {
        "libOpenCL.so.1", "libOpenCL.so", "OpenCL.dll", "libOpenCL.dylib", NULL
    };
    void *lib = NULL;
    for (int i = 0; candidates[i]; i++) {
        lib = dlopen(candidates[i], RTLD_LAZY);
        if (lib) break;
    }
    if (!lib) { _ks_gpu.ready = 0; return 0; }
    _ks_gpu.lib = lib;

    _ks_gpu.clGetPlatformIDs = (PFN_clGetPlatformIDs)_ks_gpu_dlsym(lib, "clGetPlatformIDs");
    _ks_gpu.clGetDeviceIDs = (PFN_clGetDeviceIDs)_ks_gpu_dlsym(lib, "clGetDeviceIDs");
    _ks_gpu.clCreateContext = (PFN_clCreateContext)_ks_gpu_dlsym(lib, "clCreateContext");
    _ks_gpu.clCreateCommandQueue = (PFN_clCreateCommandQueue)_ks_gpu_dlsym(lib, "clCreateCommandQueue");
    _ks_gpu.clCreateBuffer = (PFN_clCreateBuffer)_ks_gpu_dlsym(lib, "clCreateBuffer");
    _ks_gpu.clCreateProgramWithSource = (PFN_clCreateProgramWithSource)_ks_gpu_dlsym(lib, "clCreateProgramWithSource");
    _ks_gpu.clBuildProgram = (PFN_clBuildProgram)_ks_gpu_dlsym(lib, "clBuildProgram");
    _ks_gpu.clCreateKernel = (PFN_clCreateKernel)_ks_gpu_dlsym(lib, "clCreateKernel");
    _ks_gpu.clSetKernelArg = (PFN_clSetKernelArg)_ks_gpu_dlsym(lib, "clSetKernelArg");
    _ks_gpu.clEnqueueNDRangeKernel = (PFN_clEnqueueNDRangeKernel)_ks_gpu_dlsym(lib, "clEnqueueNDRangeKernel");
    _ks_gpu.clEnqueueWriteBuffer = (PFN_clEnqueueWriteBuffer)_ks_gpu_dlsym(lib, "clEnqueueWriteBuffer");
    _ks_gpu.clEnqueueReadBuffer = (PFN_clEnqueueReadBuffer)_ks_gpu_dlsym(lib, "clEnqueueReadBuffer");
    _ks_gpu.clFinish = (PFN_clFinish)_ks_gpu_dlsym(lib, "clFinish");
    _ks_gpu.clGetDeviceInfo = (PFN_clGetDeviceInfo)_ks_gpu_dlsym(lib, "clGetDeviceInfo");
    _ks_gpu.clReleaseMemObject = (PFN_clReleaseMemObject)_ks_gpu_dlsym(lib, "clReleaseMemObject");
    _ks_gpu.clReleaseKernel = (PFN_clReleaseKernel)_ks_gpu_dlsym(lib, "clReleaseKernel");
    _ks_gpu.clReleaseProgram = (PFN_clReleaseProgram)_ks_gpu_dlsym(lib, "clReleaseProgram");
    _ks_gpu.clReleaseCommandQueue = (PFN_clReleaseCommandQueue)_ks_gpu_dlsym(lib, "clReleaseCommandQueue");
    _ks_gpu.clReleaseContext = (PFN_clReleaseContext)_ks_gpu_dlsym(lib, "clReleaseContext");

    if (!_ks_gpu.clGetPlatformIDs || !_ks_gpu.clGetDeviceIDs || !_ks_gpu.clCreateContext) {
        _ks_gpu.ready = 0; return 0;
    }

    ks_cl_uint num = 0;
    ks_cl_obj platform = NULL;
    if (_ks_gpu.clGetPlatformIDs(1, &platform, &num) != 0 || num == 0) { _ks_gpu.ready = 0; return 0; }

    ks_cl_uint devnum = 0;
    ks_cl_obj dev = NULL;
    /* CL_DEVICE_TYPE_GPU = 1 << 2 = 4 */
    if (_ks_gpu.clGetDeviceIDs(platform, 4, 1, &dev, &devnum) != 0 || devnum == 0) {
        /* fall back to any device (CPU/accelerator) */
        if (_ks_gpu.clGetDeviceIDs(platform, 0 /*CL_DEVICE_TYPE_ALL*/, 1, &dev, &devnum) != 0
            || devnum == 0) { _ks_gpu.ready = 0; return 0; }
    }
    _ks_gpu.device = dev;

    ks_cl_int err = 0;
    _ks_gpu.context = _ks_gpu.clCreateContext(NULL, 1, &dev, NULL, NULL, &err);
    if (!_ks_gpu.context) { _ks_gpu.ready = 0; return 0; }
    _ks_gpu.queue = _ks_gpu.clCreateCommandQueue(_ks_gpu.context, dev, 0, &err);
    if (!_ks_gpu.queue) { _ks_gpu.ready = 0; return 0; }

    memset(_ks_gpu.name, 0, sizeof(_ks_gpu.name));
    if (_ks_gpu.clGetDeviceInfo) {
        /* CL_DEVICE_NAME = 0x102B */
        _ks_gpu.clGetDeviceInfo(dev, 0x102B, sizeof(_ks_gpu.name) - 1, _ks_gpu.name, NULL);
    }
    if (_ks_gpu.name[0] == 0) strcpy(_ks_gpu.name, "opencl-device");

    _ks_gpu.ready = 1;
    return 1;
}

static int ks_gpu_supported(void) { return ks_gpu_init(); }
static const char *ks_gpu_name(void) {
    if (!ks_gpu_init()) return "cpu-fallback";
    return _ks_gpu.name;
}

/*
 * Generic 1D element-wise binary op on the GPU.
 * Runs an OpenCL kernel `c[i] = a[i] OP b[i]` where OP is "+","-","*","/".
 * Automatically falls back to the real ks_simd CPU path when no GPU exists.
 */
/* CL enum shortcuts (kept local to avoid needing cl.h) */
#define KS_CL_MEM_READ_WRITE  (1 << 2)
#define KS_CL_MEM_READ_ONLY   (1 << 0)
#define KS_CL_MEM_WRITE_ONLY  (1 << 1)
#define KS_CL_TRUE            1

static int _ks_gpu_run_binop(const char *op, void *a, void *b, void *c, long n, int is_float) {
    if (!ks_gpu_init()) return 0;
    ks_cl_int err = 0;
    ks_cl_size bytes = (ks_cl_size)(n * (is_float ? sizeof(float) : sizeof(long long)));
    const char *typ = is_float ? "float" : "long";
    char src[256];
    snprintf(src, sizeof(src),
             "__kernel void k(__global %s* a,__global %s* b,__global %s* c){"
             "int i=get_global_id(0);c[i]=a[i]%s b[i];}",
             typ, typ, typ, op);
    const char *srcp = src;

    ks_cl_obj a_buf = _ks_gpu.clCreateBuffer(_ks_gpu.context, KS_CL_MEM_READ_WRITE, bytes, NULL, &err);
    ks_cl_obj b_buf = _ks_gpu.clCreateBuffer(_ks_gpu.context, KS_CL_MEM_READ_ONLY,  bytes, NULL, &err);
    ks_cl_obj c_buf = _ks_gpu.clCreateBuffer(_ks_gpu.context, KS_CL_MEM_WRITE_ONLY, bytes, NULL, &err);
    if (!a_buf || !b_buf || !c_buf) return 0;

    _ks_gpu.clEnqueueWriteBuffer(_ks_gpu.queue, a_buf, KS_CL_TRUE, 0, bytes, a, 0, NULL, NULL);
    _ks_gpu.clEnqueueWriteBuffer(_ks_gpu.queue, b_buf, KS_CL_TRUE, 0, bytes, b, 0, NULL, NULL);

    ks_cl_obj prog = _ks_gpu.clCreateProgramWithSource(_ks_gpu.context, 1, &srcp, NULL, &err);
    if (!prog) { _ks_gpu.clReleaseMemObject(a_buf); _ks_gpu.clReleaseMemObject(b_buf);
                 _ks_gpu.clReleaseMemObject(c_buf); return 0; }
    if (_ks_gpu.clBuildProgram(prog, 1, &_ks_gpu.device, NULL, NULL, NULL) != 0) {
        _ks_gpu.clReleaseProgram(prog); _ks_gpu.clReleaseMemObject(a_buf);
        _ks_gpu.clReleaseMemObject(b_buf); _ks_gpu.clReleaseMemObject(c_buf); return 0;
    }
    ks_cl_obj kern = _ks_gpu.clCreateKernel(prog, "k", &err);
    if (!kern) { _ks_gpu.clReleaseProgram(prog); _ks_gpu.clReleaseMemObject(a_buf);
                 _ks_gpu.clReleaseMemObject(b_buf); _ks_gpu.clReleaseMemObject(c_buf); return 0; }

    _ks_gpu.clSetKernelArg(kern, 0, sizeof(ks_cl_obj), &a_buf);
    _ks_gpu.clSetKernelArg(kern, 1, sizeof(ks_cl_obj), &b_buf);
    _ks_gpu.clSetKernelArg(kern, 2, sizeof(ks_cl_obj), &c_buf);

    ks_cl_size gsz = (ks_cl_size)n;
    _ks_gpu.clEnqueueNDRangeKernel(_ks_gpu.queue, kern, 1, NULL, &gsz, NULL, 0, NULL, NULL);
    _ks_gpu.clEnqueueReadBuffer(_ks_gpu.queue, c_buf, KS_CL_TRUE, 0, bytes, c, 0, NULL, NULL);
    _ks_gpu.clFinish(_ks_gpu.queue);

    _ks_gpu.clReleaseKernel(kern);
    _ks_gpu.clReleaseProgram(prog);
    _ks_gpu.clReleaseMemObject(a_buf);
    _ks_gpu.clReleaseMemObject(b_buf);
    _ks_gpu.clReleaseMemObject(c_buf);
    return 1;
}

/* ===========================================================================
 * CUDA backend (SECONDARY).
 * Loaded at runtime via libcuda.so (Driver API) and JIT-compiles a PTX kernel
 * on the device - the same "no link-time dependency, compile-on-device" model
 * as the OpenCL path. Activated only when a CUDA driver + GPU are present;
 * otherwise returns 0 and the caller falls back to OpenCL, then to the real
 * ks_simd CPU path. This keeps a single source building everywhere.
 * =========================================================================== */
typedef int    CUresult;
typedef int    CUdevice;
typedef void  *CUcontext;
typedef void  *CUmodule;
typedef void  *CUfunction;
typedef void  *CUdeviceptr;
typedef void  *CUstream;

typedef CUresult (*PFN_cuInit)(unsigned int);
typedef CUresult (*PFN_cuDeviceGet)(CUdevice *, int);
typedef CUresult (*PFN_cuCtxCreate)(CUcontext *, unsigned int, CUdevice);
typedef CUresult (*PFN_cuModuleLoadData)(CUmodule *, const char *);
typedef CUresult (*PFN_cuModuleGetFunction)(CUfunction *, CUmodule, const char *);
typedef CUresult (*PFN_cuMemAlloc)(CUdeviceptr *, size_t);
typedef CUresult (*PFN_cuMemcpyHtoD)(CUdeviceptr, const void *, size_t);
typedef CUresult (*PFN_cuMemcpyDtoH)(void *, CUdeviceptr, size_t);
typedef CUresult (*PFN_cuLaunchKernel)(CUfunction, unsigned int, unsigned int, unsigned int,
                                       unsigned int, unsigned int, unsigned int,
                                       unsigned int, CUstream, void **, void **);
typedef CUresult (*PFN_cuMemFree)(CUdeviceptr);
typedef CUresult (*PFN_cuModuleUnload)(CUmodule);
typedef CUresult (*PFN_cuCtxDestroy)(CUcontext);

typedef struct {
    void *lib;
    int   ready;
    CUdevice   device;
    CUcontext  context;
    PFN_cuInit              cuInit;
    PFN_cuDeviceGet         cuDeviceGet;
    PFN_cuCtxCreate         cuCtxCreate;
    PFN_cuModuleLoadData    cuModuleLoadData;
    PFN_cuModuleGetFunction cuModuleGetFunction;
    PFN_cuMemAlloc          cuMemAlloc;
    PFN_cuMemcpyHtoD        cuMemcpyHtoD;
    PFN_cuMemcpyDtoH        cuMemcpyDtoH;
    PFN_cuLaunchKernel      cuLaunchKernel;
    PFN_cuMemFree           cuMemFree;
    PFN_cuModuleUnload      cuModuleUnload;
    PFN_cuCtxDestroy        cuCtxDestroy;
} ks_cuda_state;

static ks_cuda_state _ks_cuda = {0};

static int ks_gpu_cuda_init(void) {
    if (_ks_cuda.ready || _ks_cuda.lib) return _ks_cuda.ready;
    const char *cands[] = {"libcuda.so.1", "libcuda.so", "nvcuda.dll", NULL};
    void *lib = NULL;
    for (int i = 0; cands[i]; i++) { lib = dlopen(cands[i], RTLD_LAZY); if (lib) break; }
    if (!lib) { _ks_cuda.ready = 0; return 0; }
    _ks_cuda.lib = lib;
#define DLSYM_CUDA(n) (PFN_##n)_ks_gpu_dlsym(lib, #n)
    _ks_cuda.cuInit            = DLSYM_CUDA(cuInit);
    _ks_cuda.cuDeviceGet       = DLSYM_CUDA(cuDeviceGet);
    _ks_cuda.cuCtxCreate       = DLSYM_CUDA(cuCtxCreate);
    _ks_cuda.cuModuleLoadData  = DLSYM_CUDA(cuModuleLoadData);
    _ks_cuda.cuModuleGetFunction = DLSYM_CUDA(cuModuleGetFunction);
    _ks_cuda.cuMemAlloc        = DLSYM_CUDA(cuMemAlloc);
    _ks_cuda.cuMemcpyHtoD      = DLSYM_CUDA(cuMemcpyHtoD);
    _ks_cuda.cuMemcpyDtoH      = DLSYM_CUDA(cuMemcpyDtoH);
    _ks_cuda.cuLaunchKernel    = DLSYM_CUDA(cuLaunchKernel);
    _ks_cuda.cuMemFree         = DLSYM_CUDA(cuMemFree);
    _ks_cuda.cuModuleUnload    = DLSYM_CUDA(cuModuleUnload);
    _ks_cuda.cuCtxDestroy      = DLSYM_CUDA(cuCtxDestroy);
#undef DLSYM_CUDA
    if (!_ks_cuda.cuInit || !_ks_cuda.cuDeviceGet || !_ks_cuda.cuCtxCreate) { _ks_cuda.ready = 0; return 0; }
    if (_ks_cuda.cuInit(0) != 0) { _ks_cuda.ready = 0; return 0; }
    CUdevice dev = 0;
    if (_ks_cuda.cuDeviceGet(&dev, 0) != 0) { _ks_cuda.ready = 0; return 0; }
    CUcontext ctx = NULL;
    if (_ks_cuda.cuCtxCreate(&ctx, 0, dev) != 0) { _ks_cuda.ready = 0; return 0; }
    _ks_cuda.device = dev;
    _ks_cuda.context = ctx;
    _ks_cuda.ready = 1;
    return 1;
}

static int ks_gpu_cuda_supported(void) { return ks_gpu_cuda_init(); }
static const char *ks_gpu_cuda_name(void) { return ks_gpu_cuda_init() ? "cuda-device" : "cpu-fallback"; }

/* Build a PTX kernel string for c[i] = a[i] OP b[i]. op in "+","-","*","/". */
static const char *_ks_cuda_ptx(const char *op, int is_float, char *buf, size_t sz) {
    const char *ld, *st, *alu, *shift;
    if (is_float) {
        ld = "ld.global.f32"; st = "st.global.f32";
        if (op[0]=='-') alu = "sub.f32";
        else if (op[0]=='*') alu = "mul.f32";
        else if (op[0]=='/') alu = "div.f32";
        else alu = "add.f32";
        shift = "shl.b64 %off, %off, 2";
    } else {
        ld = "ld.global.u64"; st = "st.global.u64";
        if (op[0]=='-') alu = "sub.u64";
        else if (op[0]=='*') alu = "mul.u64";
        else if (op[0]=='/') alu = "div.u64";
        else alu = "add.u64";
        shift = "shl.b64 %off, %off, 3";
    }
    snprintf(buf, sz,
        ".version 6.0\n.target sm_35\n.address_size 64\n"
        ".visible .entry vecbinop(.param .u64 a,.param .u64 b,.param .u64 c,.param .u32 n){"
        ".reg .u32 %tid_x,%nt,%bid_x,%idx,%nn;"
        ".reg .u64 %a,%b,%c,%off,%va,%vb,%vc;"
        "mov.u32 %tid_x, %tid.x; mov.u32 %nt, %ntid.x; mov.u32 %bid_x, %ctaid.x;"
        "mad.lo.u32 %idx, %bid_x, %nt, %tid_x;"
        "ld.param.u64 %a, [a]; ld.param.u64 %b, [b]; ld.param.u64 %c, [c]; ld.param.u32 %nn, [n];"
        "setp.ge.u32 %p_done, %idx, %nn; @%p_done bra L_done;"
        "cvt.u64.u32 %off, %idx; %s;"
        "add.u64 %a, %a, %off; add.u64 %b, %b, %off; add.u64 %c, %c, %off;"
        "%s %va, [%a]; %s %vb, [%b]; %s %vc, %va, %vb; %s [%c], %vc;"
        "L_done: ret; }",
        shift, ld, ld, alu, st);
    return buf;
}

static int _ks_gpu_cuda_run_binop(const char *op, void *a, void *b, void *c, long n, int is_float) {
    if (!ks_gpu_cuda_init()) return 0;
    size_t bytes = (size_t)n * (is_float ? 4 : 8);
    char ptx[1024];
    _ks_cuda_ptx(op, is_float, ptx, sizeof(ptx));
    CUmodule mod = NULL;
    if (_ks_cuda.cuModuleLoadData(&mod, ptx) != 0 || !mod) return 0;
    CUfunction fn = NULL;
    if (_ks_cuda.cuModuleGetFunction(&fn, mod, "vecbinop") != 0 || !fn) { _ks_cuda.cuModuleUnload(mod); return 0; }
    CUdeviceptr d_a = NULL, d_b = NULL, d_c = NULL;
    if (_ks_cuda.cuMemAlloc(&d_a, bytes) != 0 || _ks_cuda.cuMemAlloc(&d_b, bytes) != 0 ||
        _ks_cuda.cuMemAlloc(&d_c, bytes) != 0) goto cleanup;
    _ks_cuda.cuMemcpyHtoD(d_a, a, bytes);
    _ks_cuda.cuMemcpyHtoD(d_b, b, bytes);
    unsigned int threads = 256;
    unsigned int blocks = (unsigned int)((n + (long)threads - 1) / threads);
    CUdeviceptr da = d_a, db = d_b, dc = d_c;
    unsigned int nn = (unsigned int)n;
    void *args[4] = { &da, &db, &dc, &nn };
    if (_ks_cuda.cuLaunchKernel(fn, blocks, 1, 1, threads, 1, 1, 0, NULL, args, NULL) != 0) goto cleanup;
    _ks_cuda.cuMemcpyDtoH(c, d_c, bytes);
    _ks_cuda.cuMemFree(d_a); _ks_cuda.cuMemFree(d_b); _ks_cuda.cuMemFree(d_c);
    _ks_cuda.cuModuleUnload(mod);
    return 1;
cleanup:
    if (d_a) _ks_cuda.cuMemFree(d_a);
    if (d_b) _ks_cuda.cuMemFree(d_b);
    if (d_c) _ks_cuda.cuMemFree(d_c);
    _ks_cuda.cuModuleUnload(mod);
    return 0;
}

static int ks_gpu_cuda_f32_binop(const char *op, float *a, float *b, float *c, long n) {
    return _ks_gpu_cuda_run_binop(op, a, b, c, n, 1);
}
static int ks_gpu_cuda_i64_binop(const char *op, long long *a, long long *b, long long *c, long n) {
    return _ks_gpu_cuda_run_binop(op, a, b, c, n, 0);
}

static void ks_gpu_f32_binop(const char *op, float *a, float *b, float *c, long n) {
    if (ks_gpu_supported() && _ks_gpu_run_binop(op, a, b, c, n, 1)) return;
    if (ks_gpu_cuda_f32_binop(op, a, b, c, n)) return;
    if (op && op[0] == '-') ks_simd_f32_bin_sub(a, b, c, n);
    else if (op && op[0] == '*') ks_simd_f32_bin_mul(a, b, c, n);
    else if (op && op[0] == '/') ks_simd_f32_bin_div(a, b, c, n);
    else ks_simd_f32_bin_add(a, b, c, n);
}

static void ks_gpu_i64_binop(const char *op, long long *a, long long *b, long long *c, long n) {
    if (ks_gpu_supported() && _ks_gpu_run_binop(op, a, b, c, n, 0)) return;
    if (ks_gpu_cuda_i64_binop(op, a, b, c, n)) return;
    if (op && op[0] == '-') ks_simd_i64_bin_sub(a, b, c, n);
    else if (op && op[0] == '*') ks_simd_i64_bin_mul(a, b, c, n);
    else if (op && op[0] == '/') ks_simd_i64_bin_div(a, b, c, n);
    else ks_simd_i64_bin_add(a, b, c, n);
}

static void ks_gpu_f32_scale(float *a, float s, long n) {
    if (!ks_gpu_init()) { ks_simd_scale_f32(a, s, n); return; }
    ks_simd_scale_f32(a, s, n);
}

static float ks_gpu_f32_sum(float *a, long n) {
    /* reductions keep the SIMD (CPU) path for correctness/portability */
    return ks_simd_sum_f32(a, n);
}

#ifdef __cplusplus
}
#endif

#endif /* KS_GPU_H */
