:: watcher - File/directory change watcher (polling-based)
::
:: Usage:
::   import watcher;
::   let w = watcher.FileWatcher("/path/to/dir", func(path) { print(path + " changed\n"); });
::   w.start();
::   sleep(10);
::   w.stop();

class FileWatcher {
    func __init__(self, path, callback, interval) {
        if interval == none { interval = 1.0; }
        self._path = path;
        self._callback = callback;
        self._interval = interval;
        self._mtimes = {};
        self._running = false;
        self._thread = none;
        self._scan();
    }

    func _mtime(self, fp) {
        let s = fs_stat(fp);
        return s["st_mtime"];
    }

    func _scan(self) {
        let is_dir = fs_is_dir(self._path);
        if is_dir {
            let files = fs_listdir(self._path);
            for i in range(len(files)) {
                let fp = self._path + "/" + files[i];
                if fs_exists(fp) and fs_is_file(fp) {
                    self._mtimes[fp] = self._mtime(fp);
                }
            }
        } else {
            if fs_exists(self._path) {
                self._mtimes[self._path] = self._mtime(self._path);
            }
        }
    }

    func start(self) {
        self._running = true;
        self._thread = system_threading_Thread(self._poll_loop);
        system_threading_start(self._thread);
    }

    func _poll_loop(self) {
        while self._running {
            sleep(self._interval);
            let is_dir = fs_is_dir(self._path);
            if is_dir {
                let files = fs_listdir(self._path);
                for i in range(len(files)) {
                    let fp = self._path + "/" + files[i];
                    if fs_exists(fp) and fs_is_file(fp) {
                        let mtime = self._mtime(fp);
                        if fp in self._mtimes and self._mtimes[fp] != mtime {
                            self._mtimes[fp] = mtime;
                            self._callback(fp);
                        } elif not (fp in self._mtimes) {
                            self._mtimes[fp] = mtime;
                            self._callback(fp);
                        }
                    }
                }
            } else {
                if fs_exists(self._path) {
                    let mtime = self._mtime(self._path);
                    if self._path in self._mtimes and self._mtimes[self._path] != mtime {
                        self._mtimes[self._path] = mtime;
                        self._callback(self._path);
                    }
                } else {
                    if self._path in self._mtimes {
                        self._mtimes.delete(self._path);
                        self._callback(self._path);
                    }
                }
            }
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

export { FileWatcher };
