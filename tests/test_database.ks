:: Test Phase 12 - Database

print("Test: SQLite");
let conn = system_database_sqlite_connect("/tmp/test.db");
if conn != none {
    print("✓ sqlite.connect() works");
    system_database_sqlite_execute(conn, "CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)");
    system_database_sqlite_execute(conn, "INSERT INTO test (name) VALUES (?)", ["test"]);
    let cursor = system_database_sqlite_execute(conn, "SELECT * FROM test");
    let row = system_database_sqlite_fetchone(cursor);
    if row != none {
        print("✓ sqlite execute/fetch works");
    }
    system_database_sqlite_close(conn);
}

print("\n=== Phase 12 Database Complete ===");
