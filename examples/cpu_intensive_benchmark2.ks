:: cpu_intensive_benchmark.ks
import time;

let start = time.time();
let sum = 0.0;

for i in range(0, 1000000) {
    sum = sum + (i * i) / 3.0;
}

let end = time.time();
print("Native Result: " + str(sum));
print("Native Time: " + str(end - start) + " ms");
