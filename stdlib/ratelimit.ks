:: ratelimit - Token bucket rate limiter
::
:: Usage:
::   import ratelimit;
::   let rl = ratelimit.RateLimiter(10, 1);
::   if rl.allow("api_key") { print("go"); }

class RateLimiter {
    func __init__(self, max_calls, period_seconds) {
        if max_calls == none { max_calls = 10; }
        if period_seconds == none { period_seconds = 1; }
        self._max_calls = max_calls;
        self._period = period_seconds;
        self._buckets = {};
    }

    func allow(self, key) {
        let now = system_time();
        let bucket = self._get_bucket(key);
        if bucket == none {
            self._buckets[key] = {"tokens": self._max_calls - 1, "reset_at": now + self._period};
            return true;
        }
        if now >= bucket["reset_at"] {
            bucket["tokens"] = self._max_calls - 1;
            bucket["reset_at"] = now + self._period;
            return true;
        }
        if bucket["tokens"] > 0 {
            bucket["tokens"] = bucket["tokens"] - 1;
            return true;
        }
        return false;
    }

    func remaining(self, key) {
        let bucket = self._get_bucket(key);
        if bucket == none { return self._max_calls; }
        let now = system_time();
        if now >= bucket["reset_at"] { return self._max_calls; }
        return bucket["tokens"];
    }

    func reset(self, key) {
        if key in self._buckets {
            self._buckets.pop(key);
        }
    }

    func reset_all(self) {
        self._buckets = {};
    }

    func _get_bucket(self, key) {
        if key in self._buckets {
            return self._buckets[key];
        }
        return none;
    }
}

export { RateLimiter };
