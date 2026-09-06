:: collections - Container datatypes
:: Real implementations with full functionality

:: ─── Stack (LIFO) ───────────────────────────────────────────────────────────

class Stack {
    func __init__(self) {
        self.items = [];
    }
    
    func push(self, item) {
        self.items.push(item);
    }
    
    func pop(self) {
        if self.is_empty() {
            raise "Stack is empty";
        }
        return self.items.pop();
    }
    
    func peek(self) {
        if self.is_empty() {
            raise "Stack is empty";
        }
        return self.items[self.items.length - 1];
    }
    
    func is_empty(self) {
        return self.items.length == 0;
    }
    
    func size(self) {
        return self.items.length;
    }
    
    func clear(self) {
        self.items = [];
    }
    
    func to_list(self) {
        return [...self.items];
    }
}

:: ─── Queue (FIFO) ──────────────────────────────────────────────────────────

class Queue {
    func __init__(self) {
        self.items = [];
    }
    
    func enqueue(self, item) {
        self.items.push(item);
    }
    
    func dequeue(self) {
        if self.is_empty() {
            raise "Queue is empty";
        }
        return self.items.shift();
    }
    
    func front(self) {
        if self.is_empty() {
            raise "Queue is empty";
        }
        return self.items[0];
    }
    
    func is_empty(self) {
        return self.items.length == 0;
    }
    
    func size(self) {
        return self.items.length;
    }
    
    func clear(self) {
        self.items = [];
    }
    
    func to_list(self) {
        return [...self.items];
    }
}

:: ─── Deque (Double-ended queue) ────────────────────────────────────────────

class Deque {
    func __init__(self, iterable) {
        if iterable != none {
            self.items = [...iterable];
        } else {
            self.items = [];
        }
    }
    
    func append(self, item) {
        self.items.push(item);
    }
    
    func appendleft(self, item) {
        self.items.unshift(item);
    }

    func append_left(self, item) { return self.appendleft(item); }

    func popleft(self) {
        if self.is_empty() {
            raise "Deque is empty";
        }
        return self.items.shift();
    }

    func pop_left(self) { return self.popleft(); }

    func pop(self) {
        if self.is_empty() {
            raise "Deque is empty";
        }
        return self.items.pop();
    }
    
    func extend(self, iterable) {
        for item in iterable {
            self.items.push(item);
        }
    }
    
    func extendleft(self, iterable) {
        for item in iterable {
            self.items.unshift(item);
        }
    }
    
    func rotate(self, n) {
        if n == none {
            n = 1;
        }
        
        let len = self.items.length;
        if len == 0 {
            return;
        }
        
        n = n % len;
        if n < 0 {
            n = n + len;
        }
        
        for i in 0..n {
            let item = self.items.pop();
            self.items.unshift(item);
        }
    }
    
    func reverse(self) {
        self.items.reverse();
    }
    
    func clear(self) {
        self.items = [];
    }
    
    func is_empty(self) {
        return self.items.length == 0;
    }
    
    func size(self) {
        return self.items.length;
    }
    
    func to_list(self) {
        return [...self.items];
    }
}

:: ─── OrderedDict ───────────────────────────────────────────────────────────

class OrderedDict {
    func __init__(self) {
        self.keys = [];
        self.values = {};
    }
    
    func __setitem__(self, key, value) {
        self.set(key, value);
    }
    
    func __getitem__(self, key) {
        return self.values[key];
    }
    
    func set(self, key, value) {
        if !self.values[key] {
            self.keys.push(key);
        }
        self.values[key] = value;
    }
    
    func get(self, key, default) {
        if self.values[key] != none {
            return self.values[key];
        }
        return default;
    }
    
    func has(self, key) {
        return self.values[key] != none;
    }
    
    func delete(self, key) {
        if self.values[key] != none {
            delete self.values[key];
            let index = self.keys.indexOf(key);
            if index != -1 {
                self.keys.splice(index, 1);
            }
        }
    }
    
    func pop(self, key, default) {
        if self.values[key] != none {
            let value = self.values[key];
            self.delete(key);
            return value;
        }
        return default;
    }
    
    func popitem(self, last) {
        if last == none {
            last = true;
        }
        
        if self.keys.length == 0 {
            raise "OrderedDict is empty";
        }
        
        let key;
        if last {
            key = self.keys.pop();
        } else {
            key = self.keys.shift();
        }
        
        let value = self.values[key];
        delete self.values[key];
        return [key, value];
    }
    
    func move_to_end(self, key, last) {
        if last == none {
            last = true;
        }
        
        if !self.has(key) {
            raise "Key not found";
        }
        
        let index = self.keys.indexOf(key);
        self.keys.splice(index, 1);
        
        if last {
            self.keys.push(key);
        } else {
            self.keys.unshift(key);
        }
    }
    
    func clear(self) {
        self.keys = [];
        self.values = {};
    }
    
    func size(self) {
        return self.keys.length;
    }
    
    func items(self) {
        let result = [];
        for key in self.keys {
            result.push([key, self.values[key]]);
        }
        return result;
    }
    
    func keys_list(self) {
        return [...self.keys];
    }
    
    func values_list(self) {
        let result = [];
        for key in self.keys {
            result.push(self.values[key]);
        }
        return result;
    }
}

:: ─── DefaultDict ───────────────────────────────────────────────────────────

class DefaultDict {
    func __init__(self, default_factory) {
        self.default_factory = default_factory;
        self.data = {};
    }
    
    func get(self, key) {
        if self.data[key] == none {
            if self.default_factory != none {
                self.data[key] = self.default_factory();
            }
        }
        return self.data[key];
    }
    
    func set(self, key, value) {
        self.data[key] = value;
    }
    
    func has(self, key) {
        return self.data[key] != none;
    }
    
    func delete(self, key) {
        delete self.data[key];
    }
    
    func keys(self) {
        return Object.keys(self.data);
    }
    
    func values(self) {
        return Object.values(self.data);
    }
    
    func items(self) {
        let result = [];
        for key in Object.keys(self.data) {
            result.push([key, self.data[key]]);
        }
        return result;
    }
    
    func clear(self) {
        self.data = {};
    }
    
    func size(self) {
        return Object.keys(self.data).length;
    }
}

:: ─── Counter ───────────────────────────────────────────────────────────────

class Counter {
    func __init__(self, iterable) {
        self.counts = {};
        
        if iterable != none {
            for item in iterable {
                self.increment(item);
            }
        }
    }
    
    func increment(self, item, count) {
        if count == none {
            count = 1;
        }
        
        let key = str(item);
        if self.counts[key] == none {
            self.counts[key] = 0;
        }
        self.counts[key] = self.counts[key] + count;
    }
    
    func decrement(self, item, count) {
        if count == none {
            count = 1;
        }
        self.increment(item, -count);
    }
    
    func get(self, item) {
        let key = str(item);
        return self.counts[key] != none ? self.counts[key] : 0;
    }
    
    func most_common(self, n) {
        let items = [];
        for key in Object.keys(self.counts) {
            items.push([key, self.counts[key]]);
        }
        
        :: Sort by count descending
        items.sort((a, b) => b[1] - a[1]);
        
        if n != none {
            return items.slice(0, n);
        }
        return items;
    }
    
    func elements(self) {
        let result = [];
        for key in Object.keys(self.counts) {
            let count = self.counts[key];
            for i in 0..count {
                result.push(key);
            }
        }
        return result;
    }
    
    func total(self) {
        let sum = 0;
        for key in Object.keys(self.counts) {
            sum = sum + self.counts[key];
        }
        return sum;
    }
    
    func clear(self) {
        self.counts = {};
    }
    
    func update(self, iterable) {
        for item in iterable {
            self.increment(item);
        }
    }
    
    func subtract(self, iterable) {
        for item in iterable {
            self.decrement(item);
        }
    }
}

:: ─── ChainMap ──────────────────────────────────────────────────────────────

class ChainMap {
    func __init__(self, ...maps) {
        self.maps = maps.length > 0 ? maps : [{}];
    }
    
    func get(self, key, default) {
        for map in self.maps {
            if map[key] != none {
                return map[key];
            }
        }
        return default;
    }
    
    func set(self, key, value) {
        self.maps[0][key] = value;
    }
    
    func delete(self, key) {
        if self.maps[0][key] != none {
            delete self.maps[0][key];
        } else {
            raise "Key not found in first mapping";
        }
    }
    
    func has(self, key) {
        for map in self.maps {
            if map[key] != none {
                return true;
            }
        }
        return false;
    }
    
    func keys(self) {
        let seen = {};
        let result = [];
        for map in self.maps {
            for key in Object.keys(map) {
                if !seen[key] {
                    seen[key] = true;
                    result.push(key);
                }
            }
        }
        return result;
    }
    
    func values(self) {
        let result = [];
        for key in self.keys() {
            result.push(self.get(key));
        }
        return result;
    }
    
    func items(self) {
        let result = [];
        for key in self.keys() {
            result.push([key, self.get(key)]);
        }
        return result;
    }
    
    func new_child(self, m) {
        if m == none {
            m = {};
        }
        return ChainMap(m, ...self.maps);
    }
    
    func parents(self) {
        return ChainMap(...self.maps.slice(1));
    }
}

:: ─── Heap (Priority Queue) ─────────────────────────────────────────────────

class Heap {
    func __init__(self, compare) {
        self.items = [];
        self.compare = compare != none ? compare : (a, b) => a - b;
    }
    
    func push(self, item) {
        self.items.push(item);
        self._sift_up(self.items.length - 1);
    }
    
    func pop(self) {
        if self.is_empty() {
            raise "Heap is empty";
        }
        
        let result = self.items[0];
        let last = self.items.pop();
        
        if self.items.length > 0 {
            self.items[0] = last;
            self._sift_down(0);
        }
        
        return result;
    }
    
    func peek(self) {
        if self.is_empty() {
            raise "Heap is empty";
        }
        return self.items[0];
    }
    
    func _sift_up(self, index) {
        while index > 0 {
            let parent = (index - 1) >> 1;
            if self.compare(self.items[index], self.items[parent]) < 0 {
                let temp = self.items[index];
                self.items[index] = self.items[parent];
                self.items[parent] = temp;
                index = parent;
            } else {
                break;
            }
        }
    }
    
    func _sift_down(self, index) {
        let len = self.items.length;
        while true {
            let smallest = index;
            let left = 2 * index + 1;
            let right = 2 * index + 2;
            
            if left < len && self.compare(self.items[left], self.items[smallest]) < 0 {
                smallest = left;
            }
            
            if right < len && self.compare(self.items[right], self.items[smallest]) < 0 {
                smallest = right;
            }
            
            if smallest != index {
                let temp = self.items[index];
                self.items[index] = self.items[smallest];
                self.items[smallest] = temp;
                index = smallest;
            } else {
                break;
            }
        }
    }
    
    func is_empty(self) {
        return self.items.length == 0;
    }
    
    func size(self) {
        return self.items.length;
    }
    
    func clear(self) {
        self.items = [];
    }
}

:: ─── LinkedList ────────────────────────────────────────────────────────────

class ListNode {
    func __init__(self, value) {
        self.value = value;
        self.next = none;
        self.prev = none;
    }
}

class LinkedList {
    func __init__(self) {
        self.head = none;
        self.tail = none;
        self.length = 0;
    }
    
    func append(self, value) {
        let node = ListNode(value);
        
        if self.head == none {
            self.head = node;
            self.tail = node;
        } else {
            self.tail.next = node;
            node.prev = self.tail;
            self.tail = node;
        }
        
        self.length = self.length + 1;
    }
    
    func prepend(self, value) {
        let node = ListNode(value);
        
        if self.head == none {
            self.head = node;
            self.tail = node;
        } else {
            node.next = self.head;
            self.head.prev = node;
            self.head = node;
        }
        
        self.length = self.length + 1;
    }
    
    func get(self, index) {
        if index < 0 || index >= self.length {
            raise "Index out of bounds";
        }
        
        let current = self.head;
        for i in 0..index {
            current = current.next;
        }
        
        return current.value;
    }
    
    func remove(self, value) {
        let current = self.head;
        
        while current != none {
            if current.value == value {
                if current.prev != none {
                    current.prev.next = current.next;
                } else {
                    self.head = current.next;
                }
                
                if current.next != none {
                    current.next.prev = current.prev;
                } else {
                    self.tail = current.prev;
                }
                
                self.length = self.length - 1;
                return true;
            }
            current = current.next;
        }
        
        return false;
    }
    
    func to_list(self) {
        let result = [];
        let current = self.head;
        while current != none {
            result.push(current.value);
            current = current.next;
        }
        return result;
    }
    
    func size(self) {
        return self.length;
    }
    
    func is_empty(self) {
        return self.length == 0;
    }
    
    func clear(self) {
        self.head = none;
        self.tail = none;
        self.length = 0;
    }
}

:: ─── Export All ────────────────────────────────────────────────────────────

export {
    Stack, Queue, Deque, OrderedDict, DefaultDict,
    Counter, ChainMap, Heap, LinkedList, ListNode
};
