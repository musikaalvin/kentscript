:: sqlite - SQLite database interface

class Connection {
    func __init__(self, database) {
        self.database = database;
        self.handle = sqlite_open(database);
    }
    
    func cursor(self) {
        return Cursor(self.handle);
    }
    
    func execute(self, sql, params) {
        let cur = self.cursor();
        cur.execute(sql, params);
        return cur;
    }
    
    func executemany(self, sql, params_list) {
        let cur = self.cursor();
        cur.executemany(sql, params_list);
        return cur;
    }
    
    func commit(self) {
        sqlite_commit(self.handle);
    }
    
    func rollback(self) {
        sqlite_rollback(self.handle);
    }
    
    func close(self) {
        if self.handle != none {
            sqlite_close(self.handle);
            self.handle = none;
        }
    }
}

class Cursor {
    func __init__(self, conn_handle) {
        self.conn_handle = conn_handle;
        self.stmt = none;
        self.results = [];
        self.rowcount = 0;
        self.lastrowid = 0;
    }
    
    func execute(self, sql, params) {
        if params == none { params = []; }
        self.stmt = sqlite_prepare(self.conn_handle, sql);
        sqlite_bind_params(self.stmt, params);
        self.results = sqlite_execute(self.stmt);
        self.rowcount = self.results.length;
        self.lastrowid = sqlite_last_insert_rowid(self.conn_handle);
    }
    
    func executemany(self, sql, params_list) {
        self.rowcount = 0;
        for params in params_list {
            self.execute(sql, params);
            self.rowcount = self.rowcount + 1;
        }
    }
    
    func fetchone(self) {
        if self.results.length > 0 {
            return self.results.shift();
        }
        return none;
    }
    
    func fetchall(self) {
        let all = [...self.results];
        self.results = [];
        return all;
    }
    
    func fetchmany(self, size) {
        if size == none { size = 1; }
        let result = [];
        for i in 0..size {
            if self.results.length == 0 { break; }
            result.push(self.results.shift());
        }
        return result;
    }
    
    func close(self) {
        if self.stmt != none {
            sqlite_finalize(self.stmt);
            self.stmt = none;
        }
    }
}

func connect(database) {
    return Connection(database);
}

:: Runtime interface
func sqlite_open(database) { return system_sqlite_open(database); }
func sqlite_close(handle) { system_sqlite_close(handle); }
func sqlite_prepare(handle, sql) { return system_sqlite_prepare(handle, sql); }
func sqlite_bind_params(stmt, params) { system_sqlite_bind_params(stmt, params); }
func sqlite_execute(stmt) { return system_sqlite_execute(stmt); }
func sqlite_finalize(stmt) { system_sqlite_finalize(stmt); }
func sqlite_commit(handle) { system_sqlite_commit(handle); }
func sqlite_rollback(handle) { system_sqlite_rollback(handle); }
func sqlite_last_insert_rowid(handle) { return system_sqlite_last_insert_rowid(handle); }

export {
    Connection, Cursor, connect
};
