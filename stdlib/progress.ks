:: progress - Progress bars and indicators

class ProgressBar {
    func __init__(self, total, desc, width, unit) {
        self.total = total;
        self.desc = desc != none ? desc : "";
        self.width = width != none ? width : 50;
        self.unit = unit != none ? unit : "it";
        self.current = 0;
        self.start_time = time_now();
    }
    
    func update(self, n) {
        if n == none { n = 1; }
        self.current = self.current + n;
        self._display();
    }
    
    func _display(self) {
        let percent = (self.current * 100.0) / self.total;
        let filled = int((self.current * self.width) / self.total);
        let bar = "#".repeat(filled) + "-".repeat(self.width - filled);
        
        let elapsed = time_now() - self.start_time;
        let rate = self.current / elapsed;
        let remaining = (self.total - self.current) / rate;
        
        let line = f"\r{self.desc} |{bar}| {percent:.1f}% {self.current}/{self.total} [{elapsed:.1f}s<{remaining:.1f}s, {rate:.2f}{self.unit}/s]";
        print_no_newline(line);
        
        if self.current >= self.total {
            print("");
        }
    }
    
    func close(self) {
        if self.current < self.total {
            self.current = self.total;
            self._display();
        }
    }
}

func tqdm(iterable, desc, total, unit) {
    if total == none {
        total = iterable.length;
    }
    
    let bar = ProgressBar(total, desc, 50, unit);
    
    let result = [];
    for item in iterable {
        result.push(item);
        bar.update(1);
    }
    
    bar.close();
    return result;
}

class Spinner {
    func __init__(self, desc) {
        self.desc = desc != none ? desc : "Loading";
        self.frames = ["|", "/", "-", "\\"];
        self.current_frame = 0;
        self.running = false;
    }
    
    func start(self) {
        self.running = true;
        self._spin();
    }
    
    func _spin(self) {
        while self.running {
            let frame = self.frames[self.current_frame];
            print_no_newline(f"\r{self.desc} {frame}");
            self.current_frame = (self.current_frame + 1) % self.frames.length;
            sleep(0.1);
        }
    }
    
    func stop(self) {
        self.running = false;
        print("\r" + " ".repeat(self.desc.length + 10));
    }
}

class Counter {
    func __init__(self, desc) {
        self.desc = desc != none ? desc : "Count";
        self.count = 0;
        self.start_time = time_now();
    }
    
    func update(self, n) {
        if n == none { n = 1; }
        self.count = self.count + n;
        self._display();
    }
    
    func _display(self) {
        let elapsed = time_now() - self.start_time;
        let rate = self.count / elapsed;
        print_no_newline(f"\r{self.desc}: {self.count} [{elapsed:.1f}s, {rate:.2f}/s]");
    }
    
    func close(self) {
        self._display();
        print("");
    }
}

func print_no_newline(text) {
    system_print_no_newline(text);
}

func time_now() {
    return system_time_now();
}

func sleep(seconds) {
    system_sleep(seconds);
}

func int(x) {
    return Math.floor(x);
}

:: Runtime interface
func system_print_no_newline(text) { }
func system_time_now() { return 1709640000; }
func system_sleep(seconds) { }

export {
    ProgressBar, Spinner, Counter, tqdm
};
