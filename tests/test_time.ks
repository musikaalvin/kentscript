:: Test Time Functions

print("Test: Time functions");
let t1 = system_time();
if t1 > 0 {
    print("✓ system_time works: " + str(t1));
}

let t2 = system_time_monotonic();
if t2 > 0 {
    print("✓ system_time_monotonic works");
}

let t3 = system_time_perf_counter();
if t3 > 0 {
    print("✓ system_time_perf_counter works");
}

print("\n=== Time Functions Complete ===");
