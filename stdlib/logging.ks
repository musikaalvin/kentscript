:: logging - Logging framework
:: Full-featured logging with levels, handlers, and formatters

:: ─── Log Levels ─────────────────────────────────────────────────────────────

const DEBUG = 10;
const INFO = 20;
const WARNING = 30;
const ERROR = 40;
const CRITICAL = 50;

:: ─── Logger Class ───────────────────────────────────────────────────────────

class Logger {
    func __init__(self, name) {
        self.name = name;
        self.level = INFO;
        self.handlers = [];
        self.propagate = true;
        self.parent = none;
    }
    
    func setLevel(self, level) {
        self.level = level;
    }
    
    func addHandler(self, handler) {
        self.handlers.push(handler);
    }
    
    func removeHandler(self, handler) {
        let index = self.handlers.indexOf(handler);
        if index != -1 {
            self.handlers.splice(index, 1);
        }
    }
    
    func debug(self, msg, ...args) {
        self._log(DEBUG, msg, args);
    }
    
    func info(self, msg, ...args) {
        self._log(INFO, msg, args);
    }
    
    func warning(self, msg, ...args) {
        self._log(WARNING, msg, args);
    }
    
    func error(self, msg, ...args) {
        self._log(ERROR, msg, args);
    }
    
    func critical(self, msg, ...args) {
        self._log(CRITICAL, msg, args);
    }
    
    func exception(self, msg, ...args) {
        self.error(msg, ...args);
        :: TODO: Add stack trace
    }
    
    func _log(self, level, msg, args) {
        if level < self.level {
            return;
        }
        
        let record = LogRecord(self.name, level, msg, args);
        self._handle(record);
    }
    
    func _handle(self, record) {
        for handler in self.handlers {
            if record.level >= handler.level {
                handler.emit(record);
            }
        }
        
        if self.propagate && self.parent != none {
            self.parent._handle(record);
        }
    }
}

:: ─── Log Record ────────────────────────────────────────────────────────────

class LogRecord {
    func __init__(self, name, level, msg, args) {
        self.name = name;
        self.level = level;
        self.msg = msg;
        self.args = args;
        self.created = system_time_now();
        self.levelname = _getLevelName(level);
    }
    
    func getMessage(self) {
        if self.args.length > 0 {
            return format(self.msg, ...self.args);
        }
        return self.msg;
    }
}

:: ─── Handlers ──────────────────────────────────────────────────────────────

class Handler {
    func __init__(self) {
        self.level = DEBUG;
        self.formatter = none;
    }
    
    func setLevel(self, level) {
        self.level = level;
    }
    
    func setFormatter(self, formatter) {
        self.formatter = formatter;
    }
    
    func emit(self, record) {
        :: Override in subclasses
        raise "Not implemented";
    }
    
    func format(self, record) {
        if self.formatter != none {
            return self.formatter.format(record);
        }
        return record.getMessage();
    }
}

class StreamHandler extends Handler {
    func __init__(self, stream) {
        super.__init__();
        self.stream = stream != none ? stream : sys.stderr;
    }
    
    func emit(self, record) {
        let msg = self.format(record);
        self.stream.write(msg + "\n");
        self.stream.flush();
    }
}

class FileHandler extends Handler {
    func __init__(self, filename, mode) {
        super.__init__();
        self.filename = filename;
        self.mode = mode != none ? mode : "a";
        self.file = open(filename, self.mode);
    }
    
    func emit(self, record) {
        let msg = self.format(record);
        self.file.write(msg + "\n");
        self.file.flush();
    }
    
    func close(self) {
        if self.file != none {
            self.file.close();
            self.file = none;
        }
    }
}

class RotatingFileHandler extends FileHandler {
    func __init__(self, filename, maxBytes, backupCount) {
        super.__init__(filename, "a");
        self.maxBytes = maxBytes != none ? maxBytes : 0;
        self.backupCount = backupCount != none ? backupCount : 0;
    }
    
    func emit(self, record) {
        if self.maxBytes > 0 {
            let size = file_size(self.filename);
            if size >= self.maxBytes {
                self.doRollover();
            }
        }
        super.emit(record);
    }
    
    func doRollover(self) {
        self.file.close();
        
        for i in range(self.backupCount - 1, 0, -1) {
            let sfn = f"{self.filename}.{i}";
            let dfn = f"{self.filename}.{i + 1}";
            if file_exists(sfn) {
                if file_exists(dfn) {
                    file_remove(dfn);
                }
                file_rename(sfn, dfn);
            }
        }
        
        let dfn = self.filename + ".1";
        if file_exists(dfn) {
            file_remove(dfn);
        }
        file_rename(self.filename, dfn);
        
        self.file = open(self.filename, "a");
    }
}

class NullHandler extends Handler {
    func emit(self, record) {
        :: Do nothing
    }
}

:: ─── Formatters ────────────────────────────────────────────────────────────

class Formatter {
    func __init__(self, fmt, datefmt) {
        self.fmt = fmt != none ? fmt : "%(levelname)s:%(name)s:%(message)s";
        self.datefmt = datefmt;
    }
    
    func format(self, record) {
        let s = self.fmt;
        
        s = s.replace("%(name)s", record.name);
        s = s.replace("%(levelname)s", record.levelname);
        s = s.replace("%(message)s", record.getMessage());
        s = s.replace("%(asctime)s", self.formatTime(record));
        
        return s;
    }
    
    func formatTime(self, record) {
        let dt = datetime.fromtimestamp(record.created);
        if self.datefmt != none {
            return dt.strftime(self.datefmt);
        }
        return dt.isoformat();
    }
}

class JsonFormatter extends Formatter {
    func __init__(self, datefmt) {
        super.__init__("", datefmt);
    }

    func format(self, record) {
        let obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        };
        return system_json_dumps(obj);
    }
}

:: ─── Logger Manager ────────────────────────────────────────────────────────

let _loggers = {};
let _root = Logger("root");
_root.setLevel(WARNING);

func getLogger(name) {
    if name == none {
        return _root;
    }
    
    if _loggers[name] != none {
        return _loggers[name];
    }
    
    let logger = Logger(name);
    _loggers[name] = logger;
    
    :: Set parent
    let parts = name.split(".");
    if parts.length > 1 {
        let parent_name = parts.slice(0, parts.length - 1).join(".");
        logger.parent = getLogger(parent_name);
    } else {
        logger.parent = _root;
    }
    
    return logger;
}

:: ─── Basic Configuration ───────────────────────────────────────────────────

func basicConfig(level, format, datefmt, filename, filemode) {
    let handler;
    
    if filename != none {
        handler = FileHandler(filename, filemode);
    } else {
        handler = StreamHandler();
    }
    
    if level != none {
        _root.setLevel(level);
        handler.setLevel(level);
    }
    
    if format != none || datefmt != none {
        let formatter = Formatter(format, datefmt);
        handler.setFormatter(formatter);
    }
    
    _root.addHandler(handler);
}

:: ─── Convenience Functions ─────────────────────────────────────────────────

func debug(msg, ...args) {
    _root.debug(msg, ...args);
}

func info(msg, ...args) {
    _root.info(msg, ...args);
}

func warning(msg, ...args) {
    _root.warning(msg, ...args);
}

func error(msg, ...args) {
    _root.error(msg, ...args);
}

func critical(msg, ...args) {
    _root.critical(msg, ...args);
}

func exception(msg, ...args) {
    _root.exception(msg, ...args);
}

:: ─── Helpers ───────────────────────────────────────────────────────────────

func _getLevelName(level) {
    if level == DEBUG { return "DEBUG"; }
    if level == INFO { return "INFO"; }
    if level == WARNING { return "WARNING"; }
    if level == ERROR { return "ERROR"; }
    if level == CRITICAL { return "CRITICAL"; }
    return f"Level {level}";
}

func format(template, ...args) {
    let result = template;
    for i in 0..args.length {
        result = result.replace("{" + str(i) + "}", str(args[i]));
    }
    return result;
}

:: ─── Snake_case Aliases ──────────────────────────────────────────────────────

func get_logger(name) {
    return getLogger(name);
}

func basic_config(level, format, datefmt, filename, filemode) {
    return basicConfig(level, format, datefmt, filename, filemode);
}

export {
    DEBUG, INFO, WARNING, ERROR, CRITICAL,
    Logger, Handler, StreamHandler, FileHandler, RotatingFileHandler, NullHandler,
    Formatter, JsonFormatter, LogRecord,
    getLogger, basicConfig, get_logger, basic_config,
    debug, info, warning, error, critical, exception
};
