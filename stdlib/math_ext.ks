:: Standard Library Extensions for KentScript

func clamp(val, min_val, max_val) {
    if val < min_val { return min_val; }
    if val > max_val { return max_val; }
    return val;
}

func lerp(a, b, t) {
    return a + (b - a) * t;
}

func map_range(val, in_min, in_max, out_min, out_max) {
    return (val - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

func gcd(a, b) {
    while b != 0 {
        let temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}

func lcm(a, b) {
    return (a * b) / gcd(a, b);
}

func is_even(n) {
    return n % 2 == 0;
}

func is_odd(n) {
    return n % 2 != 0;
}
