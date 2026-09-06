:: bitwise - Bit manipulation operations
:: Provides comprehensive bit-level operations

:: Bitwise AND - returns 1 where both bits are 1
func bit_and(a: int, b: int) -> int {
    return bit_and(a, b);
}

:: Bitwise OR - returns 1 where either bit is 1
func bit_or(a: int, b: int) -> int {
    return bit_or(a, b);
}

:: Bitwise XOR - returns 1 where bits differ
func bit_xor(a: int, b: int) -> int {
    return bit_xor(a, b);
}

:: Bitwise NOT - inverts all bits
func bit_not(a: int) -> int {
    return bit_not(a);
}

:: Left shift - shifts bits left
func bit_shl(a: int, bits: int) -> int {
    return bit_shl(a, bits);
}

:: Right shift (arithmetic) - shifts bits right with sign extension
func bit_shr(a: int, bits: int) -> int {
    return bit_shr(a, bits);
}

:: Right shift (logical) - shifts bits right without sign extension
func bit_ushr(a: int, bits: int) -> int {
    return bit_ushr(a, bits);
}

:: Rotate left - rotates bits left
func bit_rol(a: int, bits: int, width: int) -> int {
    return bit_rol(a, bits, width);
}

:: Rotate right - rotates bits right
func bit_ror(a: int, bits: int, width: int) -> int {
    return bit_ror(a, bits, width);
}

:: Count set bits (population count)
func popcount(a: int) -> int {
    return bit_count(a);
}

:: Count leading zeros
func clz(a: int, width: int) -> int {
    return bit_clz(a, width);
}

:: Count trailing zeros
func ctz(a: int) -> int {
    return bit_ctz(a);
}

:: Test if bit is set
func bit_test(a: int, bit: int) -> bool {
    return bit_test(a, bit) == 1;
}

:: Set bit to 1
func bit_set(a: int, bit: int) -> int {
    return bit_set(a, bit);
}

:: Clear bit to 0
func bit_clear(a: int, bit: int) -> int {
    return bit_clear(a, bit);
}

:: Toggle bit
func bit_toggle(a: int, bit: int) -> int {
    return bit_toggle(a, bit);
}

:: Extract bits from position start for length bits
func bit_extract(a: int, start: int, length: int) -> int {
    return bit_extract(a, start, length);
}

:: Replace bits at position start for length bits with value
func bit_replace(a: int, start: int, length: int, value: int) -> int {
    return bit_replace(a, start, length, value);
}

:: Sign extend from from_width bits
func bit_sign_extend(a: int, from_width: int) -> int {
    return bit_sign_extend(a, from_width);
}

:: Zero extend from from_width bits
func bit_zero_extend(a: int, from_width: int) -> int {
    return bit_zero_extend(a, from_width);
}

:: Byte swap (little endian to big endian and vice versa)
func byte_swap(a: int) -> int {
    return bit_swap(a);
}

:: Reverse all bits
func bit_reverse(a: int) -> int {
    return bit_reverse(a);
}

:: Create mask with bits from start to end (inclusive) set
func bit_mask(start: int, end: int) -> int {
    let length = end - start + 1;
    return ((1 << length) - 1) << start;
}

:: Check if number is power of 2
func is_power_of_2(a: int) -> bool {
    if a <= 0 {
        return false;
    }
    return (a & (a - 1)) == 0;
}

:: Round up to next power of 2
func next_power_of_2(a: int) -> int {
    if a <= 1 {
        return 1;
    }
    a = a - 1;
    a = a | (a >> 1);
    a = a | (a >> 2);
    a = a | (a >> 4);
    a = a | (a >> 8);
    a = a | (a >> 16);
    a = a | (a >> 32);
    return a + 1;
}

:: Round down to previous power of 2
func prev_power_of_2(a: int) -> int {
    if a <= 1 {
        return 1;
    }
    a = a | (a >> 1);
    a = a | (a >> 2);
    a = a | (a >> 4);
    a = a | (a >> 8);
    a = a | (a >> 16);
    a = a | (a >> 32);
    return (a >> 1) + 1;
}

:: Swap two values without temporary variable
func swap(a: int, b: int) -> (int, int) {
    a = bit_xor(a, b);
    b = bit_xor(a, b);
    a = bit_xor(a, b);
    return (a, b);
}
