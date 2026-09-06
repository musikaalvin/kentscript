:: math - Mathematical functions
:: Full implementation with trigonometry, logarithms, etc.

const PI = 3.141592653589793;
const E = 2.718281828459045;
const TAU = 6.283185307179586;
const INF = 1.0 / 0.0;
const NAN = 0.0 / 0.0;

:: ─── Basic Functions ────────────────────────────────────────────────────────

func abs(x) {
    return x < 0 ? -x : x;
}

func sign(x) {
    if x > 0 { return 1; }
    if x < 0 { return -1; }
    return 0;
}

func min(...args) {
    let minimum = args[0];
    for val in args {
        if val < minimum {
            minimum = val;
        }
    }
    return minimum;
}

func max(...args) {
    let maximum = args[0];
    for val in args {
        if val > maximum {
            maximum = val;
        }
    }
    return maximum;
}

func clamp(x, min_val, max_val) {
    if x < min_val { return min_val; }
    if x > max_val { return max_val; }
    return x;
}

:: ─── Power and Roots ────────────────────────────────────────────────────────

func pow(x, y) {
    return x ** y;
}

func sqrt(x) {
    if x < 0 { return NAN; }
    if x == 0 { return 0; }
    
    let guess = x / 2.0;
    let epsilon = 0.000001;
    
    while abs(guess * guess - x) > epsilon {
        guess = (guess + x / guess) / 2.0;
    }
    
    return guess;
}

func cbrt(x) {
    let sign = x < 0 ? -1 : 1;
    x = abs(x);
    
    let guess = x / 3.0;
    let epsilon = 0.000001;
    
    while abs(guess * guess * guess - x) > epsilon {
        guess = (2.0 * guess + x / (guess * guess)) / 3.0;
    }
    
    return sign * guess;
}

func hypot(x, y) {
    return sqrt(x * x + y * y);
}

:: ─── Exponential and Logarithmic ───────────────────────────────────────────

func exp(x) {
    let sum = 1.0;
    let term = 1.0;
    
    for n in 1..100 {
        term = term * x / n;
        sum = sum + term;
        if abs(term) < 0.000001 {
            break;
        }
    }
    
    return sum;
}

func log(x, base) {
    if x <= 0 { return NAN; }
    if x == 1 { return 0; }
    
    :: Natural log using Newton's method
    let guess = 0.0;
    let epsilon = 0.000001;
    
    for i in 0..100 {
        let eg = exp(guess);
        let diff = eg - x;
        if abs(diff) < epsilon {
            break;
        }
        guess = guess - diff / eg;
    }
    
    if base != none && base != E {
        return guess / log(base);
    }
    
    return guess;
}

func log10(x) {
    return log(x, 10);
}

func log2(x) {
    return log(x, 2);
}

func log1p(x) {
    return log(1 + x);
}

func expm1(x) {
    return exp(x) - 1;
}

:: ─── Trigonometric ─────────────────────────────────────────────────────────

func sin(x) {
    :: Normalize to [-PI, PI]
    x = x % (2 * PI);
    if x > PI { x = x - 2 * PI; }
    if x < -PI { x = x + 2 * PI; }
    
    :: Taylor series
    let sum = 0.0;
    let term = x;
    
    for n in 0..20 {
        sum = sum + term;
        term = -term * x * x / ((2 * n + 2) * (2 * n + 3));
        if abs(term) < 0.000001 {
            break;
        }
    }
    
    return sum;
}

func cos(x) {
    return sin(x + PI / 2);
}

func tan(x) {
    let c = cos(x);
    if abs(c) < 0.000001 {
        return INF;
    }
    return sin(x) / c;
}

func asin(x) {
    if x < -1 || x > 1 { return NAN; }
    if x == 1 { return PI / 2; }
    if x == -1 { return -PI / 2; }
    
    :: Newton's method
    let guess = x;
    for i in 0..20 {
        let s = sin(guess);
        let c = cos(guess);
        if abs(c) < 0.000001 { break; }
        guess = guess - (s - x) / c;
    }
    
    return guess;
}

func acos(x) {
    return PI / 2 - asin(x);
}

func atan(x) {
    if abs(x) > 1 {
        return sign(x) * PI / 2 - atan(1 / x);
    }
    
    :: Taylor series
    let sum = 0.0;
    let term = x;
    
    for n in 0..50 {
        sum = sum + term;
        term = -term * x * x * (2 * n + 1) / (2 * n + 3);
        if abs(term) < 0.000001 {
            break;
        }
    }
    
    return sum;
}

func atan2(y, x) {
    if x > 0 {
        return atan(y / x);
    } else if x < 0 && y >= 0 {
        return atan(y / x) + PI;
    } else if x < 0 && y < 0 {
        return atan(y / x) - PI;
    } else if x == 0 && y > 0 {
        return PI / 2;
    } else if x == 0 && y < 0 {
        return -PI / 2;
    }
    return NAN;
}

:: ─── Hyperbolic ────────────────────────────────────────────────────────────

func sinh(x) {
    return (exp(x) - exp(-x)) / 2;
}

func cosh(x) {
    return (exp(x) + exp(-x)) / 2;
}

func tanh(x) {
    let e2x = exp(2 * x);
    return (e2x - 1) / (e2x + 1);
}

func asinh(x) {
    return log(x + sqrt(x * x + 1));
}

func acosh(x) {
    if x < 1 { return NAN; }
    return log(x + sqrt(x * x - 1));
}

func atanh(x) {
    if abs(x) >= 1 { return NAN; }
    return 0.5 * log((1 + x) / (1 - x));
}

:: ─── Rounding ──────────────────────────────────────────────────────────────

func floor(x) {
    let i = int(x);
    return x < i ? i - 1 : i;
}

func ceil(x) {
    let i = int(x);
    return x > i ? i + 1 : i;
}

func trunc(x) {
    return int(x);
}

func round(x, ndigits) {
    if ndigits == none {
        return floor(x + 0.5);
    }
    
    let multiplier = 10 ** ndigits;
    return floor(x * multiplier + 0.5) / multiplier;
}

:: ─── Number Theory ─────────────────────────────────────────────────────────

func factorial(n) {
    if n < 0 { return NAN; }
    if n == 0 || n == 1 { return 1; }
    
    let result = 1;
    for i in 2..=n {
        result = result * i;
    }
    return result;
}

func gcd(a, b) {
    a = abs(int(a));
    b = abs(int(b));
    
    while b != 0 {
        let temp = b;
        b = a % b;
        a = temp;
    }
    
    return a;
}

func lcm(a, b) {
    if a == 0 || b == 0 { return 0; }
    return abs(a * b) / gcd(a, b);
}

func is_prime(n) {
    n = int(n);
    if n < 2 { return false; }
    if n == 2 { return true; }
    if n % 2 == 0 { return false; }
    
    let limit = int(sqrt(n));
    for i in range(3, limit + 1, 2) {
        if n % i == 0 {
            return false;
        }
    }
    
    return true;
}

func comb(n, k) {
    if k > n { return 0; }
    if k == 0 || k == n { return 1; }
    
    k = min(k, n - k);
    let result = 1;
    
    for i in 0..k {
        result = result * (n - i) / (i + 1);
    }
    
    return int(result);
}

func perm(n, k) {
    if k > n { return 0; }
    
    let result = 1;
    for i in 0..k {
        result = result * (n - i);
    }
    
    return int(result);
}

:: ─── Special Functions ─────────────────────────────────────────────────────

func gamma(x) {
    :: Stirling's approximation
    if x < 0.5 {
        return PI / (sin(PI * x) * gamma(1 - x));
    }
    
    x = x - 1;
    let a = 0.99999999999980993;
    let coeffs = [676.5203681218851, -1259.1392167224028,
                  771.32342877765313, -176.61502916214059,
                  12.507343278686905, -0.13857109526572012,
                  9.9843695780195716e-6, 1.5056327351493116e-7];
    
    for i in 0..8 {
        a = a + coeffs[i] / (x + i + 1);
    }
    
    let t = x + 7.5;
    return sqrt(2 * PI) * pow(t, x + 0.5) * exp(-t) * a;
}

func erf(x) {
    :: Error function approximation
    let sign = x < 0 ? -1 : 1;
    x = abs(x);
    
    let a1 = 0.254829592;
    let a2 = -0.284496736;
    let a3 = 1.421413741;
    let a4 = -1.453152027;
    let a5 = 1.061405429;
    let p = 0.3275911;
    
    let t = 1.0 / (1.0 + p * x);
    let y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * exp(-x * x);
    
    return sign * y;
}

func erfc(x) {
    return 1 - erf(x);
}

:: ─── Utilities ─────────────────────────────────────────────────────────────

func degrees(x) {
    return x * 180 / PI;
}

func radians(x) {
    return x * PI / 180;
}

func isnan(x) {
    return x != x;
}

func isinf(x) {
    return x == INF || x == -INF;
}

func isfinite(x) {
    return !isnan(x) && !isinf(x);
}

func copysign(x, y) {
    return abs(x) * sign(y);
}

func fmod(x, y) {
    return x - trunc(x / y) * y;
}

func remainder(x, y) {
    return x - round(x / y) * y;
}

func fsum(iterable) {
    let sum = 0.0;
    for val in iterable {
        sum = sum + val;
    }
    return sum;
}

func prod(iterable, start) {
    let product = start != none ? start : 1;
    for val in iterable {
        product = product * val;
    }
    return product;
}

export {
    PI, E, TAU, INF, NAN,
    abs, sign, min, max, clamp,
    pow, sqrt, cbrt, hypot,
    exp, log, log10, log2, log1p, expm1,
    sin, cos, tan, asin, acos, atan, atan2,
    sinh, cosh, tanh, asinh, acosh, atanh,
    floor, ceil, trunc, round,
    factorial, gcd, lcm, is_prime, comb, perm,
    gamma, erf, erfc,
    degrees, radians, isnan, isinf, isfinite,
    copysign, fmod, remainder, fsum, prod
};
