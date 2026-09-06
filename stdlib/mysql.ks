:: mysql - MySQL database interface
::
:: Usage:
::   import mysql;
::   let db = mysql.connect("localhost", 3306, "mydb", "root", "pass");
::   db.execute("CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY, name TEXT)");
::   db.execute("INSERT INTO users (name) VALUES (?)", ["Alice"]);
::   let rows = db.query("SELECT * FROM users");
::   db.close();

import system;

class Connection {
    func __init__(self, host, port, database, user, password) {
        self.handle = system_database_mysql_connect(host, port, database, user, password);
        self._closed = false;
    }

    func execute(self, sql, params) {
        if params == none { params = []; }
        system_database_mysql_execute(self.handle, sql, params);
    }

    func executemany(self, sql, params_list) {
        system_database_mysql_executemany(self.handle, sql, params_list);
    }

    func query(self, sql, params) {
        if params == none { params = []; }
        let cur = system_database_mysql_execute(self.handle, sql, params);
        return system_database_mysql_fetchall(cur);
    }

    func query_one(self, sql, params) {
        if params == none { params = []; }
        let cur = system_database_mysql_execute(self.handle, sql, params);
        return system_database_mysql_fetchone(cur);
    }

    func query_val(self, sql, params) {
        let row = self.query_one(sql, params);
        if row == none { return none; }
        if type(row) == "list" and len(row) > 0 { return row[0]; }
        return row;
    }

    func query_many(self, sql, params, size) {
        if params == none { params = []; }
        let cur = system_database_mysql_execute(self.handle, sql, params);
        return system_database_mysql_fetchmany(cur, size);
    }

    func last_insert_id(self) {
        return system_database_mysql_lastrowid(self.handle);
    }

    func commit(self) {
        system_database_mysql_commit(self.handle);
    }

    func rollback(self) {
        system_database_mysql_rollback(self.handle);
    }

    func cursor(self) {
        let h = system_database_mysql_cursor(self.handle);
        return Cursor(h);
    }

    func close(self) {
        if not self._closed {
            system_database_mysql_close(self.handle);
            self._closed = true;
        }
    }

    func __del__(self) {
        self.close();
    }
}

class Cursor {
    func __init__(self, handle) {
        self.handle = handle;
    }

    func execute(self, sql, params) {
        if params == none { params = []; }
        self.handle = system_database_mysql_execute(self, sql, params);
    }

    func fetchone(self) {
        return system_database_mysql_fetchone(self.handle);
    }

    func fetchall(self) {
        return system_database_mysql_fetchall(self.handle);
    }

    func fetchmany(self, size) {
        if size == none { size = 10; }
        return system_database_mysql_fetchmany(self.handle, size);
    }

    func description(self) {
        return system_database_mysql_description(self.handle);
    }

    func rowcount(self) {
        return system_database_mysql_rowcount(self.handle);
    }

    func lastrowid(self) {
        return system_database_mysql_lastrowid(self.handle);
    }

    func close(self) {
        self.handle = none;
    }
}

func connect(host, port, database, user, password) {
    if host == none { host = "localhost"; }
    if port == none { port = 3306; }
    return Connection(host, port, database, user, password);
}

export { Connection, Cursor, connect };
