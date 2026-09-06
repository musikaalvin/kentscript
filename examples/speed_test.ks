const CPU_ITERS = 10000000;
const MEM_ITERS = 1000000;
const FLOAT_ITERS = 10000000;

func now_ms() {
    return system_time_monotonic();
}

print("==============================");
print("⚡ KENTSCRIPT HONEST BENCHMARK");
print("==============================");

:: CPU
let start = now_ms();
let cpu_result = 0;
let i = 0;
while i < CPU_ITERS {
    cpu_result = cpu_result + i * i;
    i = i + 1;
};
let cpu_time = now_ms() - start;
print("CPU:      " + str(cpu_time) + " ms (" + str(cpu_result) + ")");

:: MEMORY
start = now_ms();
let arr = alloc_i64(MEM_ITERS);
let j = 0;
while j < MEM_ITERS {
    arr[j] = j;
    j = j + 1;
};
j = 0;
while j < MEM_ITERS {
    arr[j] = arr[j] * 2;
    j = j + 1;
};
let mem_result = arr[MEM_ITERS - 1];
free(arr);
let mem_time = now_ms() - start;
print("Memory:   " + str(mem_time) + " ms (" + str(mem_result) + ")");

:: FLOAT
start = now_ms();
let float_result = 0.0;
let k = 0;
while k < FLOAT_ITERS {
    let x = k * 0.001;
    float_result = float_result + x * x;
    k = k + 1;
};
let float_time = now_ms() - start;
print("Float:    " + str(float_time) + " ms (" + str(float_result) + ")");

let total = cpu_time + mem_time + float_time;
print("------------------------------");
print("TOTAL:    " + str(total) + " ms");
