:: postgres - PostgreSQL database interface
::
:: Usage:
::   import postgres;
::   let db = postgres.connect("localhost", 5432, "mydb", "user", "pass");
::   db.execute("CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT)");
::   db.execute("INSERT INTO users (name) VALUES ($1)", ["Alice"]);
::   let rows = db.query("SELECT * FROM users");
::   db.close();

import system;

class Connection {
    func __init__(self, host, port, dbname, user, password) {
        self.handle = system_database_postgres_connect(host, port, dbname, user, password);
        self._closed = false;
    }

    func execute(self, sql, params) {
        if params == none { params = []; }
        system_database_postgres_execute(self.handle, sql, params);
    }

    func executemany(self, sql, params_list) {
        system_database_postgres_executemany(self.handle, sql, params_list);
    }

    func copy_from(self, table, data, sep) {
        if sep == none { sep = "\t"; }
        return system_database_postgres_copy_from(self.handle, table, data, sep);
    }

    func query(self, sql, params) {
        if params == none { params = []; }
        let cur = system_database_postgres_execute(self.handle, sql, params);
        return system_database_postgres_fetchall(cur);
    }

    func query_one(self, sql, params) {
        if params == none { params = []; }
        let cur = system_database_postgres_execute(self.handle, sql, params);
        return system_database_postgres_fetchone(cur);
    }

    func query_val(self, sql, params) {
        let row = self.query_one(sql, params);
        if row == none { return none; }
        if type(row) == "list" and len(row) > 0 { return row[0]; }
        return row;
    }

    func query_many(self, sql, params, size) {
        if params == none { params = []; }
        let cur = system_database_postgres_execute(self.handle, sql, params);
        return system_database_postgres_fetchmany(cur, size);
    }

    func commit(self) {
        system_database_postgres_commit(self.handle);
    }

    func rollback(self) {
        system_database_postgres_rollback(self.handle);
    }

    func cursor(self) {
        let h = system_database_postgres_cursor(self.handle);
        return Cursor(h);
    }

    func close(self) {
        if not self._closed {
            system_database_postgres_close(self.handle);
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
        self.handle = system_database_postgres_execute(self, sql, params);
    }

    func fetchone(self) {
        return system_database_postgres_fetchone(self.handle);
    }

    func fetchall(self) {
        return system_database_postgres_fetchall(self.handle);
    }

    func fetchmany(self, size) {
        if size == none { size = 10; }
        return system_database_postgres_fetchmany(self.handle, size);
    }

    func description(self) {
        return system_database_postgres_description(self.handle);
    }

    func rowcount(self) {
        return system_database_postgres_rowcount(self.handle);
    }

    func close(self) {
        self.handle = none;
    }
}

func connect(host, port, dbname, user, password) {
    if host == none { host = "localhost"; }
    if port == none { port = 5432; }
    return Connection(host, port, dbname, user, password);
}

export { Connection, Cursor, connect };
