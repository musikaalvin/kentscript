:: cache - In-memory cache with TTL support
::
:: Usage:
::   import cache;
::   let c = cache.Cache(100, 60);
::   c.set("key", "value");
::   let val = c.get("key");

class Cache {
    func __init__(self, maxsize, ttl) {
        if maxsize == none { maxsize = 100; }
        if ttl == none { ttl = 60; }
        self._store = {};
        self._ttls = {};
        self._maxsize = maxsize;
        self._default_ttl = ttl;
        self._hits = 0;
        self._misses = 0;
    }

    func get(self, key) {
        let now = system_time();
        if key in self._store {
            let expiry = self._ttls[key];
            if expiry == none || now < expiry {
                self._hits = self._hits + 1;
                return self._store[key];
            }
            self._remove(key);
        }
        self._misses = self._misses + 1;
        return none;
    }

    func set(self, key, value, ttl_override) {
        if ttl_override == none { ttl_override = self._default_ttl; }
        let keys = self._store.keys();
        if self._maxsize > 0 && len(keys) >= self._maxsize {
            self._evict_one();
        }
        self._store[key] = value;
        if ttl_override > 0 {
            self._ttls[key] = system_time() + ttl_override;
        } else {
            self._ttls[key] = none;
        }
    }

    func has(self, key) {
        if key in self._store {
            let expiry = self._ttls[key];
            if expiry == none || system_time() < expiry {
                return true;
            }
            self._remove(key);
        }
        return false;
    }

    func delete(self, key) {
        self._remove(key);
    }

    func clear(self) {
        self._store = {};
        self._ttls = {};
        self._hits = 0;
        self._misses = 0;
    }

    func size(self) {
        return len(self._store.keys());
    }

    func keys(self) {
        return self._store.keys();
    }

    func stats(self) {
        return {"hits": self._hits, "misses": self._misses, "size": self.size(), "maxsize": self._maxsize, "default_ttl": self._default_ttl};
    }

    func _remove(self, key) {
        if key in self._store {
            self._store.pop(key);
        }
        if key in self._ttls {
            self._ttls.pop(key);
        }
    }

    func _evict_one(self) {
        let keys = self._store.keys();
        if len(keys) > 0 {
            self._remove(keys[0]);
        }
    }
}

export { Cache };
