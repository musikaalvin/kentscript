:: itertools - Iterator building blocks
:: Real implementation with full functionality

:: ─── Basic Iterators ────────────────────────────────────────────────────────

func map(fn, iterable) {
    let result = [];
    for item in iterable {
        result.push(fn(item));
    }
    return result;
}

func filter(predicate, iterable) {
    let result = [];
    for item in iterable {
        if predicate(item) {
            result.push(item);
        }
    }
    return result;
}

func reduce(fn, iterable, initial) {
    let accumulator = initial;
    for item in iterable {
        accumulator = fn(accumulator, item);
    }
    return accumulator;
}

func zip(iter1, iter2) {
    let result = [];
    let len = min(iter1.length, iter2.length);
    for i in 0..len {
        result.push([iter1[i], iter2[i]]);
    }
    return result;
}

func enumerate(iterable, start) {
    if start == none {
        start = 0;
    }
    let result = [];
    let index = start;
    for item in iterable {
        result.push([index, item]);
        index = index + 1;
    }
    return result;
}

func range(start, stop, step) {
    if stop == none {
        stop = start;
        start = 0;
    }
    if step == none {
        step = 1;
    }
    
    let result = [];
    if step > 0 {
        let i = start;
        while i < stop {
            result.push(i);
            i = i + step;
        }
    } else {
        let i = start;
        while i > stop {
            result.push(i);
            i = i + step;
        }
    }
    return result;
}

:: ─── Infinite Iterators ────────────────────────────────────────────────────

func count(start, step) {
    if start == none { start = 0; }
    if step == none { step = 1; }
    
    return func*() {
        let n = start;
        while true {
            yield n;
            n = n + step;
        }
    };
}

func cycle(iterable) {
    return func*() {
        while true {
            for item in iterable {
                yield item;
            }
        }
    };
}

func repeat(value, times) {
    if times == none {
        return func*() {
            while true {
                yield value;
            }
        };
    } else {
        return func*() {
            for i in 0..times {
                yield value;
            }
        };
    }
}

:: ─── Combinatoric Iterators ────────────────────────────────────────────────

func product(iter1, iter2) {
    let result = [];
    for a in iter1 {
        for b in iter2 {
            result.push([a, b]);
        }
    }
    return result;
}

func permutations(iterable, r) {
    let pool = iterable;
    let n = pool.length;
    
    if r == none {
        r = n;
    }
    
    if r > n {
        return [];
    }
    
    let result = [];
    let indices = range(0, n, 1);
    let cycles = range(n, n - r, -1);
    
    :: Generate first permutation
    let perm = [];
    for i in 0..r {
        perm.push(pool[indices[i]]);
    }
    result.push(perm);
    
    :: Generate remaining permutations
    while true {
        let done = true;
        for i in range(r - 1, -1, -1) {
            cycles[i] = cycles[i] - 1;
            if cycles[i] == 0 {
                :: Rotate indices
                let temp = indices[i];
                for j in range(i, n - 1, 1) {
                    indices[j] = indices[j + 1];
                }
                indices[n - 1] = temp;
                cycles[i] = n - i;
            } else {
                :: Swap
                let j = n - cycles[i];
                let temp = indices[i];
                indices[i] = indices[j];
                indices[j] = temp;
                
                let perm = [];
                for k in 0..r {
                    perm.push(pool[indices[k]]);
                }
                result.push(perm);
                done = false;
                break;
            }
        }
        if done {
            break;
        }
    }
    
    return result;
}

func combinations(iterable, r) {
    let pool = iterable;
    let n = pool.length;
    
    if r > n {
        return [];
    }
    
    let result = [];
    let indices = range(0, r, 1);
    
    :: Generate first combination
    let comb = [];
    for i in indices {
        comb.push(pool[i]);
    }
    result.push(comb);
    
    :: Generate remaining combinations
    while true {
        let done = true;
        for i in range(r - 1, -1, -1) {
            if indices[i] != i + n - r {
                indices[i] = indices[i] + 1;
                for j in range(i + 1, r, 1) {
                    indices[j] = indices[j - 1] + 1;
                }
                
                let comb = [];
                for k in indices {
                    comb.push(pool[k]);
                }
                result.push(comb);
                done = false;
                break;
            }
        }
        if done {
            break;
        }
    }
    
    return result;
}

func combinations_with_replacement(iterable, r) {
    let pool = iterable;
    let n = pool.length;
    
    if n == 0 && r > 0 {
        return [];
    }
    
    let result = [];
    let indices = [];
    for i in 0..r {
        indices.push(0);
    }
    
    while true {
        let comb = [];
        for i in indices {
            comb.push(pool[i]);
        }
        result.push(comb);
        
        :: Increment indices
        let done = true;
        for i in range(r - 1, -1, -1) {
            if indices[i] != n - 1 {
                indices[i] = indices[i] + 1;
                for j in range(i + 1, r, 1) {
                    indices[j] = indices[i];
                }
                done = false;
                break;
            }
        }
        
        if done {
            break;
        }
    }
    
    return result;
}

:: ─── Terminating Iterators ─────────────────────────────────────────────────

func chain(iter1, iter2) {
    let result = [];
    for item in iter1 {
        result.push(item);
    }
    for item in iter2 {
        result.push(item);
    }
    return result;
}

func chain_from_iterable(iterables) {
    let result = [];
    for iterable in iterables {
        for item in iterable {
            result.push(item);
        }
    }
    return result;
}

func compress(data, selectors) {
    let result = [];
    let len = min(data.length, selectors.length);
    for i in 0..len {
        if selectors[i] {
            result.push(data[i]);
        }
    }
    return result;
}

func dropwhile(predicate, iterable) {
    let result = [];
    let dropping = true;
    for item in iterable {
        if dropping {
            if !predicate(item) {
                dropping = false;
                result.push(item);
            }
        } else {
            result.push(item);
        }
    }
    return result;
}

func takewhile(predicate, iterable) {
    let result = [];
    for item in iterable {
        if predicate(item) {
            result.push(item);
        } else {
            break;
        }
    }
    return result;
}

func groupby(iterable, key) {
    if key == none {
        key = (x) => x;
    }
    
    let result = [];
    let current_key = none;
    let current_group = [];
    
    for item in iterable {
        let item_key = key(item);
        if current_key == none || item_key != current_key {
            if current_group.length > 0 {
                result.push([current_key, current_group]);
            }
            current_key = item_key;
            current_group = [item];
        } else {
            current_group.push(item);
        }
    }
    
    if current_group.length > 0 {
        result.push([current_key, current_group]);
    }
    
    return result;
}

func islice(iterable, start, stop, step) {
    if stop == none {
        stop = start;
        start = 0;
    }
    if step == none {
        step = 1;
    }
    
    let result = [];
    let index = 0;
    for item in iterable {
        if index >= stop {
            break;
        }
        if index >= start && (index - start) % step == 0 {
            result.push(item);
        }
        index = index + 1;
    }
    return result;
}

func starmap(fn, iterable) {
    let result = [];
    for args in iterable {
        result.push(fn(...args));
    }
    return result;
}

func tee(iterable, n) {
    if n == none {
        n = 2;
    }
    
    let result = [];
    for i in 0..n {
        result.push([...iterable]);
    }
    return result;
}

func zip_longest(iter1, iter2, fillvalue) {
    if fillvalue == none {
        fillvalue = none;
    }
    
    let result = [];
    let len = max(iter1.length, iter2.length);
    for i in 0..len {
        let a = i < iter1.length ? iter1[i] : fillvalue;
        let b = i < iter2.length ? iter2[i] : fillvalue;
        result.push([a, b]);
    }
    return result;
}

:: ─── Utility Functions ─────────────────────────────────────────────────────

func all(iterable) {
    for item in iterable {
        if !item {
            return false;
        }
    }
    return true;
}

func any(iterable) {
    for item in iterable {
        if item {
            return true;
        }
    }
    return false;
}

func sum(iterable, start) {
    if start == none {
        start = 0;
    }
    let total = start;
    for item in iterable {
        total = total + item;
    }
    return total;
}

func min(iterable) {
    if iterable.length == 0 {
        raise "min() arg is an empty sequence";
    }
    let minimum = iterable[0];
    for item in iterable {
        if item < minimum {
            minimum = item;
        }
    }
    return minimum;
}

func max(iterable) {
    if iterable.length == 0 {
        raise "max() arg is an empty sequence";
    }
    let maximum = iterable[0];
    for item in iterable {
        if item > maximum {
            maximum = item;
        }
    }
    return maximum;
}

func sorted(iterable, key, reverse) {
    if key == none {
        key = (x) => x;
    }
    if reverse == none {
        reverse = false;
    }
    
    let arr = [...iterable];
    
    :: Quicksort implementation
    func quicksort(arr, low, high) {
        if low < high {
            let pivot = partition(arr, low, high);
            quicksort(arr, low, pivot - 1);
            quicksort(arr, pivot + 1, high);
        }
    }
    
    func partition(arr, low, high) {
        let pivot = key(arr[high]);
        let i = low - 1;
        
        for j in low..high {
            let cmp = reverse ? key(arr[j]) > pivot : key(arr[j]) < pivot;
            if cmp {
                i = i + 1;
                let temp = arr[i];
                arr[i] = arr[j];
                arr[j] = temp;
            }
        }
        
        let temp = arr[i + 1];
        arr[i + 1] = arr[high];
        arr[high] = temp;
        
        return i + 1;
    }
    
    quicksort(arr, 0, arr.length - 1);
    return arr;
}

func reversed(iterable) {
    let result = [];
    for i in range(iterable.length - 1, -1, -1) {
        result.push(iterable[i]);
    }
    return result;
}

:: ─── Pairwise and Batching ─────────────────────────────────────────────────

func pairwise(iterable) {
    let result = [];
    for i in 0..(iterable.length - 1) {
        result.push([iterable[i], iterable[i + 1]]);
    }
    return result;
}

func batched(iterable, n) {
    let result = [];
    let batch = [];
    for item in iterable {
        batch.push(item);
        if batch.length == n {
            result.push(batch);
            batch = [];
        }
    }
    if batch.length > 0 {
        result.push(batch);
    }
    return result;
}

func flatten(iterable) {
    let result = [];
    for item in iterable {
        if typeof(item) == "list" {
            for subitem in item {
                result.push(subitem);
            }
        } else {
            result.push(item);
        }
    }
    return result;
}

func unique(iterable) {
    let seen = {};
    let result = [];
    for item in iterable {
        let key = str(item);
        if !seen[key] {
            seen[key] = true;
            result.push(item);
        }
    }
    return result;
}

func partition_by(predicate, iterable) {
    let true_items = [];
    let false_items = [];
    for item in iterable {
        if predicate(item) {
            true_items.push(item);
        } else {
            false_items.push(item);
        }
    }
    return [true_items, false_items];
}
