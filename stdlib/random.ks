:: random - Random number generation
:: Real implementation with multiple algorithms

:: ─── Random Number Generator ────────────────────────────────────────────────

class Random {
    func __init__(self, seed) {
        if seed != none {
            self.seed(seed);
        } else {
            self.seed(time_now());
        }
    }
    
    func seed(self, value) {
        self.state = value % 2147483647;
        if self.state <= 0 {
            self.state = self.state + 2147483646;
        }
    }
    
    func _next(self) {
        :: Linear congruential generator
        self.state = (self.state * 48271) % 2147483647;
        return self.state;
    }
    
    func random(self) {
        :: Return float in [0.0, 1.0)
        return self._next() / 2147483647.0;
    }
    
    func randint(self, a, b) {
        :: Return random integer in [a, b]
        return a + (self._next() % (b - a + 1));
    }
    
    func randrange(self, start, stop, step) {
        if stop == none {
            stop = start;
            start = 0;
        }
        if step == none {
            step = 1;
        }
        
        let width = stop - start;
        let n = (width + step - 1) / step;
        return start + self.randint(0, n - 1) * step;
    }
    
    func choice(self, seq) {
        if seq.length == 0 {
            raise "Cannot choose from empty sequence";
        }
        return seq[self.randint(0, seq.length - 1)];
    }
    
    func choices(self, population, weights, k) {
        if k == none {
            k = 1;
        }
        
        let result = [];
        
        if weights == none {
            for i in 0..k {
                result.push(self.choice(population));
            }
        } else {
            :: Weighted selection
            let total = 0;
            for w in weights {
                total = total + w;
            }
            
            for i in 0..k {
                let r = self.random() * total;
                let cumsum = 0;
                for j in 0..population.length {
                    cumsum = cumsum + weights[j];
                    if r < cumsum {
                        result.push(population[j]);
                        break;
                    }
                }
            }
        }
        
        return result;
    }
    
    func shuffle(self, seq) {
        :: Fisher-Yates shuffle
        for i in range(seq.length - 1, 0, -1) {
            let j = self.randint(0, i);
            let temp = seq[i];
            seq[i] = seq[j];
            seq[j] = temp;
        }
    }
    
    func sample(self, population, k) {
        if k > population.length {
            raise "Sample larger than population";
        }
        
        let result = [...population];
        self.shuffle(result);
        return result.slice(0, k);
    }
    
    func uniform(self, a, b) {
        :: Return random float in [a, b]
        return a + (b - a) * self.random();
    }
    
    func triangular(self, low, high, mode) {
        if low == none { low = 0.0; }
        if high == none { high = 1.0; }
        if mode == none { mode = (low + high) / 2.0; }
        
        let u = self.random();
        let c = (mode - low) / (high - low);
        
        if u < c {
            return low + sqrt(u * (high - low) * (mode - low));
        } else {
            return high - sqrt((1 - u) * (high - low) * (high - mode));
        }
    }
    
    func gauss(self, mu, sigma) {
        :: Box-Muller transform
        if mu == none { mu = 0.0; }
        if sigma == none { sigma = 1.0; }
        
        let u1 = self.random();
        let u2 = self.random();
        
        let z0 = sqrt(-2.0 * log(u1)) * cos(2.0 * PI * u2);
        return mu + z0 * sigma;
    }
    
    func normalvariate(self, mu, sigma) {
        return self.gauss(mu, sigma);
    }
    
    func lognormvariate(self, mu, sigma) {
        return exp(self.normalvariate(mu, sigma));
    }
    
    func expovariate(self, lambd) {
        :: Exponential distribution
        return -log(1.0 - self.random()) / lambd;
    }
    
    func vonmisesvariate(self, mu, kappa) {
        :: Von Mises distribution
        if kappa <= 0.000001 {
            return 2.0 * PI * self.random();
        }
        
        let a = 1.0 + sqrt(1.0 + 4.0 * kappa * kappa);
        let b = (a - sqrt(2.0 * a)) / (2.0 * kappa);
        let r = (1.0 + b * b) / (2.0 * b);
        
        while true {
            let u1 = self.random();
            let z = cos(PI * u1);
            let f = (1.0 + r * z) / (r + z);
            let c = kappa * (r - f);
            
            let u2 = self.random();
            if u2 < c * (2.0 - c) || u2 <= c * exp(1.0 - c) {
                let u3 = self.random();
                let theta = mu + (u3 < 0.5 ? 1 : -1) * acos(f);
                return theta % (2.0 * PI);
            }
        }
    }
    
    func paretovariate(self, alpha) {
        :: Pareto distribution
        let u = 1.0 - self.random();
        return 1.0 / pow(u, 1.0 / alpha);
    }
    
    func weibullvariate(self, alpha, beta) {
        :: Weibull distribution
        let u = 1.0 - self.random();
        return alpha * pow(-log(u), 1.0 / beta);
    }
    
    func betavariate(self, alpha, beta) {
        :: Beta distribution (simplified)
        let y1 = self.gammavariate(alpha, 1.0);
        let y2 = self.gammavariate(beta, 1.0);
        return y1 / (y1 + y2);
    }
    
    func gammavariate(self, alpha, beta) {
        :: Gamma distribution (Marsaglia and Tsang method)
        if alpha <= 0.0 || beta <= 0.0 {
            raise "alpha and beta must be positive";
        }
        
        if alpha > 1.0 {
            let d = alpha - 1.0 / 3.0;
            let c = 1.0 / sqrt(9.0 * d);
            
            while true {
                let x = self.gauss(0.0, 1.0);
                let v = 1.0 + c * x;
                
                if v <= 0.0 {
                    continue;
                }
                
                v = v * v * v;
                let u = self.random();
                
                if u < 1.0 - 0.0331 * x * x * x * x {
                    return d * v / beta;
                }
                
                if log(u) < 0.5 * x * x + d * (1.0 - v + log(v)) {
                    return d * v / beta;
                }
            }
        } else if alpha == 1.0 {
            return self.expovariate(1.0 / beta);
        } else {
            let u = self.random();
            return self.gammavariate(1.0 + alpha, beta) * pow(u, 1.0 / alpha);
        }
    }
}

:: ─── Global Random Instance ────────────────────────────────────────────────

let _inst = Random();

func seed(value) {
    _inst.seed(value);
}

func random() {
    return _inst.random();
}

func randint(a, b) {
    return _inst.randint(a, b);
}

func randrange(start, stop, step) {
    return _inst.randrange(start, stop, step);
}

func choice(seq) {
    return _inst.choice(seq);
}

func choices(population, weights, k) {
    return _inst.choices(population, weights, k);
}

func shuffle(seq) {
    _inst.shuffle(seq);
}

func sample(population, k) {
    return _inst.sample(population, k);
}

func uniform(a, b) {
    return _inst.uniform(a, b);
}

func triangular(low, high, mode) {
    return _inst.triangular(low, high, mode);
}

func gauss(mu, sigma) {
    return _inst.gauss(mu, sigma);
}

func normalvariate(mu, sigma) {
    return _inst.normalvariate(mu, sigma);
}

func lognormvariate(mu, sigma) {
    return _inst.lognormvariate(mu, sigma);
}

func expovariate(lambd) {
    return _inst.expovariate(lambd);
}

func vonmisesvariate(mu, kappa) {
    return _inst.vonmisesvariate(mu, kappa);
}

func paretovariate(alpha) {
    return _inst.paretovariate(alpha);
}

func weibullvariate(alpha, beta) {
    return _inst.weibullvariate(alpha, beta);
}

func betavariate(alpha, beta) {
    return _inst.betavariate(alpha, beta);
}

func gammavariate(alpha, beta) {
    return _inst.gammavariate(alpha, beta);
}

:: ─── Utility Functions ─────────────────────────────────────────────────────

func getrandbits(k) {
    :: Return random integer with k random bits
    let result = 0;
    for i in 0..k {
        result = (result << 1) | _inst.randint(0, 1);
    }
    return result;
}

func randbytes(n) {
    :: Return n random bytes
    let result = [];
    for i in 0..n {
        result.push(_inst.randint(0, 255));
    }
    return result;
}

:: ─── Math Functions (helpers) ──────────────────────────────────────────────

const PI = 3.141592653589793;

func sqrt(x) { return x ** 0.5; }
func log(x) { return Math.log(x); }
func exp(x) { return Math.exp(x); }
func cos(x) { return Math.cos(x); }
func sin(x) { return Math.sin(x); }
func acos(x) { return Math.acos(x); }
func pow(x, y) { return x ** y; }
func time_now() { return system_time_now(); }

:: ─── Convenience Functions ─────────────────────────────────────────────────

func int(a, b) {
    return randint(a, b);
}

func float(a, b) {
    return uniform(a, b);
}

:: ─── Export ────────────────────────────────────────────────────────────────

export {
    Random,
    seed, random, randint, randrange,
    choice, choices, shuffle, sample,
    uniform, triangular, gauss, normalvariate,
    lognormvariate, expovariate, vonmisesvariate,
    paretovariate, weibullvariate, betavariate, gammavariate,
    getrandbits, randbytes,
    int, float
};
