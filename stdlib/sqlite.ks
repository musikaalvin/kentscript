:: sqlite - SQLite database interface
::
:: Usage:
::   import sqlite;
::   let db = sqlite.open("my.db");
::   db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)");
::   db.execute("INSERT INTO users (name) VALUES (?)", ["Alice"]);
::   let rows = db.query("SELECT * FROM users");
::   db.close();

import system;

class Connection {
    func __init__(self, database) {
        self.database = database;
        self.handle = system_database_sqlite_connect(database);
        self._closed = false;
    }

    func cursor(self) {
        let h = system_database_sqlite_cursor(self.handle);
        return Cursor(self.handle, h);
    }

    func execute(self, sql, params) {
        if params == none { params = []; }
        let cur = system_database_sqlite_execute(self.handle, sql, params);
        self.lastrowid = system_database_sqlite_lastrowid(cur);
    }

    func executemany(self, sql, params_list) {
        system_database_sqlite_executemany(self.handle, sql, params_list);
    }

    func execute_script(self, script) {
        system_database_sqlite_execute_script(self.handle, script);
    }

    func query(self, sql, params) {
        if params == none { params = []; }
        let cur = self.cursor();
        cur.execute(sql, params);
        return cur.fetchall();
    }

    func query_one(self, sql, params) {
        if params == none { params = []; }
        let cur = self.cursor();
        cur.execute(sql, params);
        return cur.fetchone();
    }

    func query_val(self, sql, params) {
        let row = self.query_one(sql, params);
        if row == none { return none; }
        if type(row) == "list" and len(row) > 0 { return row[0]; }
        return row;
    }

    func query_many(self, sql, params, size) {
        if params == none { params = []; }
        let cur = self.cursor();
        cur.execute(sql, params);
        return cur.fetchmany(size);
    }

    func commit(self) {
        system_database_sqlite_commit(self.handle);
    }

    func rollback(self) {
        system_database_sqlite_rollback(self.handle);
    }

    func row_factory(self, enabled) {
        system_database_sqlite_row_factory(self.handle, enabled);
    }

    func last_insert_id(self) {
        return system_database_sqlite_lastrowid(self.handle);
    }

    func close(self) {
        if not self._closed {
            system_database_sqlite_close(self.handle);
            self._closed = true;
        }
    }

    func __del__(self) {
        self.close();
    }
}

class Cursor {
    func __init__(self, conn_handle, cursor_handle) {
        self.conn_handle = conn_handle;
        self.handle = cursor_handle;
        self.results = [];
        self.rowcount = 0;
        self.description = none;
    }

    func execute(self, sql, params) {
        if params == none { params = []; }
        let result = system_database_sqlite_execute(self.conn_handle, sql, params);
        self.handle = result;
        self.description = system_database_sqlite_description(result);
        self.rowcount = system_database_sqlite_rowcount(result);
    }

    func executemany(self, sql, params_list) {
        self.rowcount = 0;
        for params in params_list {
            self.execute(sql, params);
            self.rowcount = self.rowcount + 1;
        }
    }

    func fetchone(self) {
        return system_database_sqlite_fetchone(self.handle);
    }

    func fetchall(self) {
        return system_database_sqlite_fetchall(self.handle);
    }

    func fetchmany(self, size) {
        if size == none { size = 10; }
        return system_database_sqlite_fetchmany(self.handle, size);
    }

    func close(self) {
        self.handle = none;
    }
}

func open(database) {
    return Connection(database);
}

func connect(database) {
    return Connection(database);
}

func in_memory() {
    return Connection(":memory:");
}

export { Connection, Cursor, open, connect, in_memory };
