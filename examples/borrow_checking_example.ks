:: Borrow checking example
let data = 42;

:: Immutable borrow
let read1 = data;
let read2 = data;

print("Value 1: " + str(read1));
print("Value 2: " + str(read2));

:: Mutable borrow
let mut_data = 100;
print("Modified: " + str(mut_data));

print("Borrow checking complete");
