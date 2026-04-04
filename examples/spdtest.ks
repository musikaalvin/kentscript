:: test_benchmark.ks
import time;
let start = time.time();
let i = 0;
while i < 1000000 {
    i = i + 1;
}
let end = time.time();
print("Loop finished!");
print("Final value of i (should be 1,000,000):");
print(i);
print("Time taken (seconds):");
print(end - start);