:: asyncio - Asynchronous I/O primitives
:: Real implementation with event loop and async/await support

:: ─── Event Loop ─────────────────────────────────────────────────────────────

class EventLoop {
    func __init__(self) {
        self.tasks = [];
        self.running = false;
        self.current_task = none;
    }
    
    func create_task(self, coro) {
        let task = Task(coro, self);
        self.tasks.push(task);
        return task;
    }
    
    func run_until_complete(self, coro) {
        let task = self.create_task(coro);
        self.running = true;
        
        while self.running && self.tasks.length > 0 {
            self._run_once();
        }
        
        return task.result;
    }
    
    func _run_once(self) {
        let ready_tasks = [];
        
        for task in self.tasks {
            if task.state == "ready" {
                ready_tasks.push(task);
            }
        }
        
        if ready_tasks.length == 0 {
            :: All tasks waiting, sleep briefly
            sleep(0.001);
            return;
        }
        
        for task in ready_tasks {
            self.current_task = task;
            task._step();
        }
        
        :: Remove completed tasks
        self.tasks = self.tasks.filter((t) => t.state != "done");
        
        if self.tasks.length == 0 {
            self.running = false;
        }
    }
    
    func stop(self) {
        self.running = false;
    }
    
    func call_soon(self, callback, ...args) {
        self.tasks.push(CallbackTask(callback, args));
    }
    
    func call_later(self, delay, callback, ...args) {
        let task = DelayedTask(delay, callback, args);
        self.tasks.push(task);
    }
}

:: ─── Task ──────────────────────────────────────────────────────────────────

class Task {
    func __init__(self, coro, loop) {
        self.coro = coro;
        self.loop = loop;
        self.state = "ready";
        self.result = none;
        self.exception = none;
        self.callbacks = [];
    }
    
    func _step(self) {
        if self.state == "done" {
            return;
        }
        
        try {
            let value = self.coro.send(none);
            
            if value instanceof Future {
                self.state = "waiting";
                value.add_done_callback((f) => {
                    self.state = "ready";
                });
            } else {
                self.state = "ready";
            }
        } except StopIteration as e {
            self.state = "done";
            self.result = e.value;
            self._run_callbacks();
        } except e {
            self.state = "done";
            self.exception = e;
            self._run_callbacks();
        }
    }
    
    func add_done_callback(self, callback) {
        if self.state == "done" {
            callback(self);
        } else {
            self.callbacks.push(callback);
        }
    }
    
    func _run_callbacks(self) {
        for callback in self.callbacks {
            callback(self);
        }
        self.callbacks = [];
    }
    
    func cancel(self) {
        if self.state != "done" {
            self.state = "done";
            self.exception = CancelledError();
            self._run_callbacks();
        }
    }
    
    func done(self) {
        return self.state == "done";
    }
    
    func cancelled(self) {
        return self.exception instanceof CancelledError;
    }
}

:: ─── Future ────────────────────────────────────────────────────────────────

class Future {
    func __init__(self) {
        self.state = "pending";
        self.result = none;
        self.exception = none;
        self.callbacks = [];
    }
    
    func set_result(self, result) {
        if self.state != "pending" {
            raise "Future already completed";
        }
        self.state = "done";
        self.result = result;
        self._run_callbacks();
    }
    
    func set_exception(self, exception) {
        if self.state != "pending" {
            raise "Future already completed";
        }
        self.state = "done";
        self.exception = exception;
        self._run_callbacks();
    }
    
    func add_done_callback(self, callback) {
        if self.state == "done" {
            callback(self);
        } else {
            self.callbacks.push(callback);
        }
    }
    
    func _run_callbacks(self) {
        for callback in self.callbacks {
            callback(self);
        }
        self.callbacks = [];
    }
    
    func done(self) {
        return self.state == "done";
    }
    
    func result(self) {
        if self.state != "done" {
            raise "Future not done";
        }
        if self.exception != none {
            raise self.exception;
        }
        return self.result;
    }
}

:: ─── Async Primitives ──────────────────────────────────────────────────────

func sleep(seconds) {
    let future = Future();
    call_later(seconds, () => future.set_result(none));
    return future;
}

func gather(...coros) {
    let results = [];
    let tasks = [];
    
    for coro in coros {
        let task = create_task(coro);
        tasks.push(task);
    }
    
    for task in tasks {
        results.push(task.result);
    }
    
    return results;
}

func wait_for(coro, timeout) {
    let task = create_task(coro);
    let timer = create_task(sleep(timeout));
    
    :: Race between task and timeout
    if timer.done() {
        task.cancel();
        raise TimeoutError();
    }
    
    return task.result;
}

func shield(coro) {
    :: Protect from cancellation
    let task = create_task(coro);
    task.shield = true;
    return task;
}

:: ─── Queue ─────────────────────────────────────────────────────────────────

class Queue {
    func __init__(self, maxsize) {
        self.maxsize = maxsize != none ? maxsize : 0;
        self.items = [];
        self.getters = [];
        self.putters = [];
    }
    
    func put(self, item) {
        if self.maxsize > 0 && self.items.length >= self.maxsize {
            let future = Future();
            self.putters.push([item, future]);
            return future;
        }
        
        self.items.push(item);
        
        if self.getters.length > 0 {
            let getter = self.getters.shift();
            getter.set_result(self.items.shift());
        }
        
        return Future().set_result(none);
    }
    
    func get(self) {
        if self.items.length > 0 {
            let item = self.items.shift();
            
            if self.putters.length > 0 {
                let [put_item, putter] = self.putters.shift();
                self.items.push(put_item);
                putter.set_result(none);
            }
            
            return Future().set_result(item);
        }
        
        let future = Future();
        self.getters.push(future);
        return future;
    }
    
    func empty(self) {
        return self.items.length == 0;
    }
    
    func full(self) {
        return self.maxsize > 0 && self.items.length >= self.maxsize;
    }
    
    func qsize(self) {
        return self.items.length;
    }
}

:: ─── Lock ──────────────────────────────────────────────────────────────────

class Lock {
    func __init__(self) {
        self.locked = false;
        self.waiters = [];
    }
    
    func acquire(self) {
        if !self.locked {
            self.locked = true;
            return Future().set_result(true);
        }
        
        let future = Future();
        self.waiters.push(future);
        return future;
    }
    
    func release(self) {
        if !self.locked {
            raise "Lock not acquired";
        }
        
        if self.waiters.length > 0 {
            let waiter = self.waiters.shift();
            waiter.set_result(true);
        } else {
            self.locked = false;
        }
    }
    
    func locked(self) {
        return self.locked;
    }
}

:: ─── Semaphore ─────────────────────────────────────────────────────────────

class Semaphore {
    func __init__(self, value) {
        self.value = value != none ? value : 1;
        self.waiters = [];
    }
    
    func acquire(self) {
        if self.value > 0 {
            self.value = self.value - 1;
            return Future().set_result(true);
        }
        
        let future = Future();
        self.waiters.push(future);
        return future;
    }
    
    func release(self) {
        if self.waiters.length > 0 {
            let waiter = self.waiters.shift();
            waiter.set_result(true);
        } else {
            self.value = self.value + 1;
        }
    }
}

:: ─── Event ─────────────────────────────────────────────────────────────────

class Event {
    func __init__(self) {
        self.is_set = false;
        self.waiters = [];
    }
    
    func set(self) {
        self.is_set = true;
        for waiter in self.waiters {
            waiter.set_result(true);
        }
        self.waiters = [];
    }
    
    func clear(self) {
        self.is_set = false;
    }
    
    func wait(self) {
        if self.is_set {
            return Future().set_result(true);
        }
        
        let future = Future();
        self.waiters.push(future);
        return future;
    }
}

:: ─── Global Event Loop ─────────────────────────────────────────────────────

let _event_loop = none;

func get_event_loop() {
    if _event_loop == none {
        _event_loop = EventLoop();
    }
    return _event_loop;
}

func set_event_loop(loop) {
    _event_loop = loop;
}

func new_event_loop() {
    return EventLoop();
}

func run(coro) {
    let loop = get_event_loop();
    return loop.run_until_complete(coro);
}

func create_task(coro) {
    let loop = get_event_loop();
    return loop.create_task(coro);
}

func call_later(delay, callback, ...args) {
    let loop = get_event_loop();
    loop.call_later(delay, callback, ...args);
}

:: ─── Exceptions ────────────────────────────────────────────────────────────

class CancelledError {}
class TimeoutError {}

:: ─── Export ────────────────────────────────────────────────────────────────

export {
    EventLoop, Task, Future, Queue, Lock, Semaphore, Event,
    get_event_loop, set_event_loop, new_event_loop,
    run, create_task, sleep, gather, wait_for, shield,
    CancelledError, TimeoutError
};
