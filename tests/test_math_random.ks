:: Test Phase 13 - Math & Random

print("Test: Math functions");
let sqrt = system_math_sqrt(16);
if sqrt == 4 {
    print("✓ sqrt works");
}
let pow_val = system_math_pow(2, 3);
if pow_val == 8 {
    print("✓ pow works");
}
let sin_val = system_math_sin(0);
if sin_val == 0 {
    print("✓ sin works");
}
let cos_val = system_math_cos(0);
if cos_val == 1 {
    print("✓ cos works");
}
let log_val = system_math_log(10);
if log_val > 2 {
    print("✓ log works");
}
let fact = system_math_factorial(5);
if fact == 120 {
    print("✓ factorial works");
}
let gcd_val = system_math_gcd(12, 8);
if gcd_val == 4 {
    print("✓ gcd works");
}
let comb = system_math_comb(5, 2);
if comb == 10 {
    print("✓ comb works");
}
let pi = system_math_pi();
if pi > 3.14 and pi < 3.15 {
    print("✓ pi works");
}

print("\nTest: Random functions");
let rand = system_random_random();
if rand >= 0 and rand < 1 {
    print("✓ random works");
}
let randint = system_random_randint(1, 100);
if randint >= 1 and randint <= 100 {
    print("✓ randint works");
}
let choice = system_random_choice([1, 2, 3]);
if choice >= 1 and choice <= 3 {
    print("✓ choice works");
}
let uniform = system_random_uniform(0, 10);
if uniform >= 0 and uniform <= 10 {
    print("✓ uniform works");
}

print("\n=== Phase 13 Math & Random Complete ===");
