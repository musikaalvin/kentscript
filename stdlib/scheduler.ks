:: scheduler - Task scheduling (cron-like)
::
:: Usage:
::   import scheduler;
::   let s = scheduler.Scheduler();
::   s.every(1.0, func() { print("tick\\n"); });
::   s.start();
::   s.stop();

class Scheduler {
    func __init__(self) {
        self._tasks = [];
        self._running = false;
        self._thread = none;
    }

    func every(self, interval, task) {
        self._tasks.push({"interval": interval, "task": task});
    }

    func start(self) {
        self._running = true;
        self._thread = system_threading_Thread(self._run_loop);
        system_threading_start(self._thread);
    }

    func _run_loop(self) {
        while self._running {
            let i = 0;
            while i < len(self._tasks) {
                self._tasks[i]["task"]();
                i = i + 1;
            }
            sleep(self._tasks[0]["interval"]);
        }
    }

    func stop(self) {
        self._running = false;
        if self._thread != none {
            system_threading_join(self._thread);
            self._thread = none;
        }
    }
}

export { Scheduler };
