import time;
let sum = 0;
let i = 0;
let iterations = 1000000; :: Start with 1 million to be safe
let start = time.time();

print("Starting Real VM Stress Test...");

while i < iterations {
    sum = sum + i;
    i = i + 1;
}

let end = time.time();
print("Real Sum: " + str(sum));
print("Execution Time: " + str(end - start));
