:: iterators - Iterator protocol and utilities
:: Provides iterator implementations for collections

:: Iterator trait definition
trait Iterator {
    func next() -> any;
    func has_next() -> bool;
}

:: IntoIterator trait - types that can be iterated
trait IntoIterator {
    func iter() -> Iterator;
}

:: Range iterator
class RangeIterator {
    let current: int;
    let end: int;
    let step: int;
    
    func new(start: int, end: int, step: int) {
        self.current = start;
        self.end = end;
        self.step = step;
    }
    
    func next() -> any {
        if self.has_next() {
            let val = self.current;
            self.current = self.current + self.step;
            return val;
        }
        return null;
    }
    
    func has_next() -> bool {
        if self.step > 0 {
            return self.current < self.end;
        } else {
            return self.current > self.end;
        }
    }
}

:: List iterator
class ListIterator {
    let index: int;
    let list: list;
    
    func new(list: list) {
        self.index = 0;
        self.list = list;
    }
    
    func next() -> any {
        if self.has_next() {
            let val = self.list[self.index];
            self.index = self.index + 1;
            return val;
        }
        return null;
    }
    
    func has_next() -> bool {
        return self.index < len(self.list);
    }
}

:: Dict iterator
class DictIterator {
    let keys: list;
    let index: int;
    
    func new(d: dict) {
        self.keys = keys(d);
        self.index = 0;
    }
    
    func next() -> any {
        if self.has_next() {
            let key = self.keys[self.index];
            self.index = self.index + 1;
            return key;
        }
        return null;
    }
    
    func has_next() -> bool {
        return self.index < len(self.keys);
    }
}

:: Enumerate iterator - yields (index, value) pairs
class EnumerateIterator {
    let iter: Iterator;
    let index: int;
    
    func new(iter: Iterator) {
        self.iter = iter;
        self.index = 0;
    }
    
    func next() -> any {
        if self.iter.has_next() {
            let val = self.iter.next();
            let result = (self.index, val);
            self.index = self.index + 1;
            return result;
        }
        return null;
    }
    
    func has_next() -> bool {
        return self.iter.has_next();
    }
}

:: Filter iterator - only yields items that match predicate
class FilterIterator {
    let iter: Iterator;
    let predicate: function;
    
    func new(iter: Iterator, predicate: function) {
        self.iter = iter;
        self.predicate = predicate;
    }
    
    func next() -> any {
        while self.iter.has_next() {
            let val = self.iter.next();
            if self.predicate(val) {
                return val;
            }
        }
        return null;
    }
    
    func has_next() -> bool {
        return self.iter.has_next();
    }
}

:: Map iterator - transform each element
class MapIterator {
    let iter: Iterator;
    let transform: function;
    
    func new(iter: Iterator, transform: function) {
        self.iter = iter;
        self.transform = transform;
    }
    
    func next() -> any {
        if self.iter.has_next() {
            let val = self.iter.next();
            return self.transform(val);
        }
        return null;
    }
    
    func has_next() -> bool {
        return self.iter.has_next();
    }
}

:: Take iterator - only yield first n elements
class TakeIterator {
    let iter: Iterator;
    let remaining: int;
    
    func new(iter: Iterator, n: int) {
        self.iter = iter;
        self.remaining = n;
    }
    
    func next() -> any {
        if self.remaining > 0 && self.iter.has_next() {
            self.remaining = self.remaining - 1;
            return self.iter.next();
        }
        return null;
    }
    
    func has_next() -> bool {
        return self.remaining > 0 && self.iter.has_next();
    }
}

:: Skip iterator - skip first n elements
class SkipIterator {
    let iter: Iterator;
    let to_skip: int;
    
    func new(iter: Iterator, n: int) {
        self.iter = iter;
        self.to_skip = n;
    }
    
    func next() -> any {
        while self.to_skip > 0 && self.iter.has_next() {
            self.iter.next();
            self.to_skip = self.to_skip - 1;
        }
        if self.iter.has_next() {
            return self.iter.next();
        }
        return null;
    }
    
    func has_next() -> bool {
        return self.iter.has_next();
    }
}

:: Chain iterator - iterate over multiple iterators
class ChainIterator {
    let iters: list;
    let index: int;
    let current: Iterator;
    
    func new(iters: list) {
        self.iters = iters;
        self.index = 0;
        self.current = null;
    }
    
    func next() -> any {
        while self.index < len(self.iters) {
            if self.current == null {
                self.current = self.iters[self.index];
            }
            if self.current.has_next() {
                return self.current.next();
            }
            self.index = self.index + 1;
            self.current = null;
        }
        return null;
    }
    
    func has_next() -> bool {
        return self.index < len(self.iters);
    }
}

:: Helper functions

:: Create range iterator
func range_iter(start: int, end: int, step: int) -> RangeIterator {
    return RangeIterator.new(start, end, step);
}

:: Create list iterator  
func iter(list: list) -> ListIterator {
    return ListIterator.new(list);
}

:: Create dict iterator
func iter_dict(d: dict) -> DictIterator {
    return DictIterator.new(d);
}

:: Create enumerate iterator
func enumerate(iter: Iterator) -> EnumerateIterator {
    return EnumerateIterator.new(iter);
}

:: Create filter iterator
func filter(iter: Iterator, predicate: function) -> FilterIterator {
    return FilterIterator.new(iter, predicate);
}

:: Create map iterator
func map(iter: Iterator, transform: function) -> MapIterator {
    return MapIterator.new(iter, transform);
}

:: Create take iterator
func take(iter: Iterator, n: int) -> TakeIterator {
    return TakeIterator.new(iter, n);
}

:: Create skip iterator
func skip(iter: Iterator, n: int) -> SkipIterator {
    return SkipIterator.new(iter, n);
}

:: Create chain iterator
func chain(iters: list) -> ChainIterator {
    return ChainIterator.new(iters);
}

:: Consume iterator into list
func collect(iter: Iterator) -> list {
    let result = [];
    while iter.has_next() {
        result.push(iter.next());
    }
    return result;
}

:: Count elements in iterator
func count(iter: Iterator) -> int {
    let c = 0;
    while iter.has_next() {
        iter.next();
        c = c + 1;
    }
    return c;
}

:: Find first element matching predicate
func find(iter: Iterator, predicate: function) -> any {
    while iter.has_next() {
        let val = iter.next();
        if predicate(val) {
            return val;
        }
    }
    return null;
}

:: Check if any element matches
func any(iter: Iterator, predicate: function) -> bool {
    while iter.has_next() {
        if predicate(iter.next()) {
            return true;
        }
    }
    return false;
}

:: Check if all elements match
func all(iter: Iterator, predicate: function) -> bool {
    while iter.has_next() {
        if !predicate(iter.next()) {
            return false;
        }
    }
    return true;
}

:: Fold/reduce iterator
func fold(iter: Iterator, initial: any, reducer: function) -> any {
    let acc = initial;
    while iter.has_next() {
        acc = reducer(acc, iter.next());
    }
    return acc;
}
