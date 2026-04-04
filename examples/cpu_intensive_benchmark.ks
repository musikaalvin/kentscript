import time;

let x = 1000000;  :: 1 million iterations
let start_time = time.time();

let result = 0;
let i = 0;

while i < x
{
    result = result + i * i - i / 2 + i % 3;
    i = i + 1;
}

let end_time = time.time();
let execution_time = end_time - start_time;

print("Result: " + str(result));
print("Time for " + str(x) + " iterations: " + str(execution_time) + " seconds");