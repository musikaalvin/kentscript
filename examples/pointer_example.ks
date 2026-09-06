:: Pointer operations example
let ptr1 = 4096;
let ptr2 = 256;
let distance = ptr1 - ptr2;

print("Pointer 1: " + str(ptr1));
print("Pointer 2: " + str(ptr2));
print("Distance: " + str(distance));

let int_size = 4;
let long_size = 8;
let ptr_size = 8;

print("sizeof(int) = " + str(int_size));
print("sizeof(long) = " + str(long_size));
print("sizeof(ptr) = " + str(ptr_size));
