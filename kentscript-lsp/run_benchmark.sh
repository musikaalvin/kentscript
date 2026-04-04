#!/bin/bash
# KentScript Performance Benchmark Suite
# Compares: KentScript (run/jit/build) vs Python vs C

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     KentScript Performance Benchmark - Fibonacci(30)      ║"
echo "╔════════════════════════════════════════════════════════════╝"
echo ""

# C baseline (gcc -O3)
echo "1. C (gcc -O3 -march=native) - BASELINE"
echo "   ----------------------------------------"
time ./bench_fib_c
echo ""

# KentScript compiled (transpiled to C then gcc)
echo "2. KentScript BUILD mode (→C→gcc -O3)"
echo "   ----------------------------------------"
time ./bench_fib
echo ""

# Python
echo "3. Python 3.13"
echo "   ----------------------------------------"
time python3 bench_fib.py
echo ""

# KentScript interpreter
echo "4. KentScript RUN mode (interpreter)"
echo "   ----------------------------------------"
time python3 main.py run bench_fib.ks 2>/dev/null
echo ""

# KentScript JIT
echo "5. KentScript JIT mode (hotspot detection)"
echo "   ----------------------------------------"
time python3 main.py jit bench_fib.ks 2>/dev/null | grep -E "^[0-9]|Total"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    Benchmark Complete                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
