:: Test Phase 8, 14, 29 - DateTime, Bit Ops, Memory

print("Test: DateTime");
let now = system_datetime_now();
if now['year'] > 2020 {
    print("✓ datetime.now() works - " + str(now['year']));
}
let today = system_datetime_date_today();
if today['year'] > 2020 {
    print("✓ date.today() works");
}
let td = system_datetime_timedelta(days=1);
if td != none {
    print("✓ timedelta works");
}

print("\nTest: Bit Operations");
let and_val = system_bit_and(5, 3);
if and_val == 1 {
    print("✓ bit_and works");
}
let or_val = system_bit_or(5, 3);
if or_val == 7 {
    print("✓ bit_or works");
}
let xor_val = system_bit_xor(5, 3);
if xor_val == 6 {
    print("✓ bit_xor works");
}
let not_val = system_bit_not(0);
if not_val == -1 {
    print("✓ bit_not works");
}
let lshift = system_bit_lshift(1, 4);
if lshift == 16 {
    print("✓ bit_lshift works");
}
let rshift = system_bit_rshift(16, 4);
if rshift == 1 {
    print("✓ bit_rshift works");
}
let popcount = system_bit_popcount(15);
if popcount == 4 {
    print("✓ bit_popcount works");
}
let rol = system_bit_rol(0b0001, 3, 8);
if rol == 0b1000 {
    print("✓ bit_rol works");
}
let ror = system_bit_ror(0b1000, 3, 8);
if ror == 0b0001 {
    print("✓ bit_ror works");
}

print("\nTest: Struct");
let packed = system_struct_pack("i", 42);
if len(packed) == 8 {
    print("✓ struct_pack works");
}
let unpacked = system_struct_unpack("i", packed);
if unpacked[0] == 42 {
    print("✓ struct_unpack works");
}
let size = system_struct_calcsize("i");
if size == 4 {
    print("✓ struct_calcsize works");
}

print("\n=== Phase 8, 14, 29 Complete ===");
