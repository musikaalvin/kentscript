:: functools - Higher-order functions and operations on callable objects
:: Real implementation with full functionality

:: ─── Partial Application ────────────────────────────────────────────────────

func partial(fn, ...fixed_args) {
    return func(...args) {
        let all_args = [...fixed_args, ...args];
        return fn(...all_args);
    };
}

func partialmethod(fn, ...fixed_args) {
    return func(self, ...args) {
        let all_args = [self, ...fixed_args, ...args];
        return fn(...all_args);
    };
}

:: ─── Function Composition ──────────────────────────────────────────────────

func compose(...functions) {
    return func(x) {
        let result = x;
        for i in range(functions.length - 1, -1, -1) {
            result = functions[i](result);
        }
        return result;
    };
}

func pipe(...functions) {
    return func(x) {
        let result = x;
        for fn in functions {
            result = fn(result);
        }
        return result;
    };
}

:: ─── Memoization ───────────────────────────────────────────────────────────

func memoize(fn) {
    let cache = {};
    
    return func(...args) {
        let key = JSON.stringify(args);
        if cache[key] != none {
            return cache[key];
        }
        let result = fn(...args);
        cache[key] = result;
        return result;
    };
}

func lru_cache(maxsize) {
    if maxsize == none {
        maxsize = 128;
    }
    
    return func(fn) {
        let cache = {};
        let order = [];
        
        return func(...args) {
            let key = JSON.stringify(args);
            
            if cache[key] != none {
                :: Move to end (most recently used)
                let index = order.indexOf(key);
                if index != -1 {
                    order.splice(index, 1);
                }
                order.push(key);
                return cache[key];
            }
            
            let result = fn(...args);
            
            :: Add to cache
            cache[key] = result;
            order.push(key);
            
            :: Evict oldest if over limit
            if order.length > maxsize {
                let oldest = order.shift();
                delete cache[oldest];
            }
            
            return result;
        };
    };
}

func cached_property(fn) {
    let cache_key = "_cached_" + fn.name;
    
    return func(self) {
        if self[cache_key] == none {
            self[cache_key] = fn(self);
        }
        return self[cache_key];
    };
}

:: ─── Currying ──────────────────────────────────────────────────────────────

func curry(fn, arity) {
    if arity == none {
        arity = fn.length;
    }
    
    func curried(...args) {
        if args.length >= arity {
            return fn(...args);
        }
        return func(...more_args) {
            return curried(...args, ...more_args);
        };
    }
    
    return curried;
}

func uncurry(fn) {
    return func(...args) {
        let result = fn;
        for arg in args {
            result = result(arg);
        }
        return result;
    };
}

:: ─── Decorators ────────────────────────────────────────────────────────────

func wraps(wrapped) {
    return func(wrapper) {
        wrapper.name = wrapped.name;
        wrapper.__wrapped__ = wrapped;
        return wrapper;
    };
}

func total_ordering(cls) {
    :: Fills in missing comparison methods
    :: Requires __eq__ and one of __lt__, __le__, __gt__, __ge__
    
    if cls.__lt__ != none && cls.__eq__ != none {
        if cls.__le__ == none {
            cls.__le__ = func(self, other) {
                return self.__lt__(other) || self.__eq__(other);
            };
        }
        if cls.__gt__ == none {
            cls.__gt__ = func(self, other) {
                return !self.__le__(other);
            };
        }
        if cls.__ge__ == none {
            cls.__ge__ = func(self, other) {
                return !self.__lt__(other);
            };
        }
    }
    
    return cls;
}

func singledispatch(fn) {
    let registry = {};
    registry["default"] = fn;
    
    func dispatch(...args) {
        if args.length == 0 {
            return registry["default"](...args);
        }
        
        let arg_type = typeof(args[0]);
        if registry[arg_type] != none {
            return registry[arg_type](...args);
        }
        return registry["default"](...args);
    }
    
    dispatch.register = func(type, fn) {
        registry[type] = fn;
        return dispatch;
    };
    
    return dispatch;
}

:: ─── Reduction and Accumulation ────────────────────────────────────────────

func reduce(fn, iterable, initial) {
    let it = iter(iterable);
    let value;
    
    if initial == none {
        try {
            value = next(it);
        } except StopIteration {
            raise "reduce() of empty sequence with no initial value";
        }
    } else {
        value = initial;
    }
    
    for item in it {
        value = fn(value, item);
    }
    
    return value;
}

func accumulate(iterable, fn, initial) {
    if fn == none {
        fn = (a, b) => a + b;
    }
    
    let result = [];
    let total;
    
    if initial != none {
        total = initial;
        result.push(total);
    }
    
    for item in iterable {
        if total == none {
            total = item;
        } else {
            total = fn(total, item);
        }
        result.push(total);
    }
    
    return result;
}

:: ─── Comparison and Ordering ───────────────────────────────────────────────

func cmp_to_key(cmp_fn) {
    class K {
        func __init__(self, obj) {
            self.obj = obj;
        }
        
        func __lt__(self, other) {
            return cmp_fn(self.obj, other.obj) < 0;
        }
        
        func __gt__(self, other) {
            return cmp_fn(self.obj, other.obj) > 0;
        }
        
        func __eq__(self, other) {
            return cmp_fn(self.obj, other.obj) == 0;
        }
        
        func __le__(self, other) {
            return cmp_fn(self.obj, other.obj) <= 0;
        }
        
        func __ge__(self, other) {
            return cmp_fn(self.obj, other.obj) >= 0;
        }
    }
    
    return K;
}

:: ─── Function Utilities ────────────────────────────────────────────────────

func identity(x) {
    return x;
}

func constant(value) {
    return func(...args) {
        return value;
    };
}

func negate(predicate) {
    return func(...args) {
        return !predicate(...args);
    };
}

func complement(fn) {
    return negate(fn);
}

func flip(fn) {
    return func(a, b, ...rest) {
        return fn(b, a, ...rest);
    };
}

func once(fn) {
    let called = false;
    let result;
    
    return func(...args) {
        if !called {
            result = fn(...args);
            called = true;
        }
        return result;
    };
}

func throttle(fn, wait) {
    let last_call = 0;
    let last_result;
    
    return func(...args) {
        let now = Date.now();
        if now - last_call >= wait {
            last_result = fn(...args);
            last_call = now;
        }
        return last_result;
    };
}

func debounce(fn, wait) {
    let timeout;
    
    return func(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(func() {
            fn(...args);
        }, wait);
    };
}

func delay(fn, wait) {
    return func(...args) {
        setTimeout(func() {
            fn(...args);
        }, wait);
    };
}

func before(n, fn) {
    let count = 0;
    let result;
    
    return func(...args) {
        if count < n {
            result = fn(...args);
            count = count + 1;
        }
        return result;
    };
}

func after(n, fn) {
    let count = 0;
    
    return func(...args) {
        count = count + 1;
        if count >= n {
            return fn(...args);
        }
    };
}

:: ─── Function Chaining ─────────────────────────────────────────────────────

func chain_functions(...functions) {
    return func(x) {
        let result = x;
        for fn in functions {
            result = fn(result);
        }
        return result;
    };
}

func juxt(...functions) {
    return func(...args) {
        let results = [];
        for fn in functions {
            results.push(fn(...args));
        }
        return results;
    };
}

func apply(fn, args) {
    return fn(...args);
}

func apply_to(args) {
    return func(fn) {
        return fn(...args);
    };
}

:: ─── Predicate Combinators ─────────────────────────────────────────────────

func every_pred(...predicates) {
    return func(...args) {
        for pred in predicates {
            if !pred(...args) {
                return false;
            }
        }
        return true;
    };
}

func some_pred(...predicates) {
    return func(...args) {
        for pred in predicates {
            if pred(...args) {
                return true;
            }
        }
        return false;
    };
}

:: ─── Memoization Helpers ───────────────────────────────────────────────────

func cache_clear(memoized_fn) {
    if memoized_fn.cache != none {
        memoized_fn.cache = {};
    }
}

func cache_info(memoized_fn) {
    if memoized_fn.cache != none {
        return {
            "size": Object.keys(memoized_fn.cache).length,
            "maxsize": memoized_fn.maxsize
        };
    }
    return none;
}

:: ─── Utility Functions ─────────────────────────────────────────────────────

func update_wrapper(wrapper, wrapped) {
    wrapper.__wrapped__ = wrapped;
    wrapper.__name__ = wrapped.__name__;
    wrapper.__doc__ = wrapped.__doc__;
    return wrapper;
}

func get_wrapped(fn) {
    while fn.__wrapped__ != none {
        fn = fn.__wrapped__;
    }
    return fn;
}

:: ─── Functional Utilities ──────────────────────────────────────────────────

func tap(fn) {
    return func(x) {
        fn(x);
        return x;
    };
}

func tryCatch(fn, handler) {
    return func(...args) {
        try {
            return fn(...args);
        } except e {
            return handler(e, ...args);
        }
    };
}

func maybe(fn) {
    return func(...args) {
        for arg in args {
            if arg == none || arg == null {
                return none;
            }
        }
        return fn(...args);
    };
}

func defaultTo(default_value) {
    return func(value) {
        return value != none && value != null ? value : default_value;
    };
}

func when(predicate, fn) {
    return func(x) {
        return predicate(x) ? fn(x) : x;
    };
}

func unless(predicate, fn) {
    return func(x) {
        return !predicate(x) ? fn(x) : x;
    };
}

func cond(...pairs) {
    return func(x) {
        for pair in pairs {
            let [predicate, fn] = pair;
            if predicate(x) {
                return fn(x);
            }
        }
        return x;
    };
}

:: ─── Arity Manipulation ────────────────────────────────────────────────────

func unary(fn) {
    return func(a) {
        return fn(a);
    };
}

func binary(fn) {
    return func(a, b) {
        return fn(a, b);
    };
}

func nary(n, fn) {
    return func(...args) {
        return fn(...args.slice(0, n));
    };
}

func variadic(fn) {
    return func(...args) {
        return fn(args);
    };
}

:: ─── Export All ────────────────────────────────────────────────────────────

export {
    partial, partialmethod, compose, pipe,
    memoize, lru_cache, cached_property,
    curry, uncurry,
    wraps, total_ordering, singledispatch,
    reduce, accumulate,
    cmp_to_key,
    identity, constant, negate, complement, flip,
    once, throttle, debounce, delay, before, after,
    chain_functions, juxt, apply, apply_to,
    every_pred, some_pred,
    cache_clear, cache_info,
    update_wrapper, get_wrapped,
    tap, tryCatch, maybe, defaultTo, when, unless, cond,
    unary, binary, nary, variadic
};
