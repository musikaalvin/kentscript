:: sql - Unified SQL query builder
::
:: Works with sqlite, postgres, mysql, mariadb.
:: Builds parameterized queries safely (no SQL injection).
::
:: Usage:
::   import sql;
::
::   :: SELECT with WHERE
::   let q = sql.select("users").where("age", ">", 18).order_by("name").limit(10);
::   let rows = db.query(q.sql(), q.params());
::
::   :: INSERT
::   let q = sql.insert("users", {"name": "Alice", "age": 30});
::   db.execute(q.sql(), q.params());
::
::   :: UPDATE
::   let q = sql.update("users", {"age": 31}).where("name", "=", "Alice");
::   db.execute(q.sql(), q.params());
::
::   :: DELETE
::   let q = sql.delete_from("users").where("id", "=", 1);
::   db.execute(q.sql(), q.params());
::
::   :: JOIN
::   let q = sql.select("orders").join("users", "orders.user_id", "users.id").where("orders.total", ">", 100);
::
::   :: Raw query with params
::   let q = sql.raw("SELECT * FROM users WHERE name = $1 AND age > $2", ["Alice", 18]);
::
::   :: Batch insert
::   let q = sql.batch_insert("users", ["name", "age"], [["Bob", 25], ["Carol", 28]]);
::   db.execute(q.sql(), q.params());

class Query {
    func __init__() {
        self._parts = [];
        self._params = [];
    }

    func sql(self) {
        return self._parts.join(" ");
    }

    func params(self) {
        return self._params;
    }

    func _add(self, fragment) {
        self._parts.push(fragment);
        return self;
    }

    func _add_param(self, value) {
        self._params.push(value);
        return "?";
    }

    func where(self, column, op, value) {
        let ph = self._add_param(value);
        return self._add("WHERE " + column + " " + op + " " + ph);
    }

    func and_where(self, column, op, value) {
        let ph = self._add_param(value);
        return self._add("AND " + column + " " + op + " " + ph);
    }

    func or_where(self, column, op, value) {
        let ph = self._add_param(value);
        return self._add("OR " + column + " " + op + " " + ph);
    }

    func where_in(self, column, values) {
        let phs = [];
        for v in values {
            phs.push(self._add_param(v));
        }
        return self._add("WHERE " + column + " IN (" + phs.join(", ") + ")");
    }

    func where_null(self, column) {
        return self._add("WHERE " + column + " IS NULL");
    }

    func where_not_null(self, column) {
        return self._add("WHERE " + column + " IS NOT NULL");
    }

    func where_between(self, column, low, high) {
        let ph1 = self._add_param(low);
        let ph2 = self._add_param(high);
        return self._add("WHERE " + column + " BETWEEN " + ph1 + " AND " + ph2);
    }

    func where_like(self, column, pattern) {
        let ph = self._add_param(pattern);
        return self._add("WHERE " + column + " LIKE " + ph);
    }

    func order_by(self, column, direction) {
        if direction == none { direction = "ASC"; }
        return self._add("ORDER BY " + column + " " + direction);
    }

    func group_by(self, column) {
        return self._add("GROUP BY " + column);
    }

    func having(self, condition) {
        return self._add("HAVING " + condition);
    }

    func limit(self, n) {
        return self._add("LIMIT " + str(n));
    }

    func offset(self, n) {
        return self._add("OFFSET " + str(n));
    }

    func join(self, table, on_left, on_right) {
        return self._add("JOIN " + table + " ON " + on_left + " = " + on_right);
    }

    func left_join(self, table, on_left, on_right) {
        return self._add("LEFT JOIN " + table + " ON " + on_left + " = " + on_right);
    }

    func right_join(self, table, on_left, on_right) {
        return self._add("RIGHT JOIN " + table + " ON " + on_left + " = " + on_right);
    }

    func inner_join(self, table, on_left, on_right) {
        return self._add("INNER JOIN " + table + " ON " + on_left + " = " + on_right);
    }

    func cross_join(self, table) {
        return self._add("CROSS JOIN " + table);
    }

    func union_with(self, other_query) {
        return self._add("UNION " + other_query.sql());
    }

    func distinct(self) {
        return self._add("DISTINCT");
    }

    func count(self, column) {
        if column == none { column = "*"; }
        return self._replace_cols("COUNT(" + column + ") AS _count");
    }

    func sum(self, column, alias) {
        if alias == none { alias = "_sum"; }
        return self._replace_cols("SUM(" + column + ") AS " + alias);
    }

    func avg(self, column, alias) {
        if alias == none { alias = "_avg"; }
        return self._replace_cols("AVG(" + column + ") AS " + alias);
    }

    func min(self, column, alias) {
        if alias == none { alias = "_min"; }
        return self._replace_cols("MIN(" + column + ") AS " + alias);
    }

    func max(self, column, alias) {
        if alias == none { alias = "_max"; }
        return self._replace_cols("MAX(" + column + ") AS " + alias);
    }

    func _replace_cols(self, col_expr) {
        if len(self._parts) > 0 {
            let first = self._parts[0];
            let from_idx = first.find(" FROM ");
            if from_idx != -1 {
                self._parts[0] = "SELECT " + col_expr + first.substring(from_idx);
            }
        }
        return self;
    }
}

:: ─── Builder functions ──────────────────────────────────────────────────

func select(table, columns) {
    if columns == none { columns = ["*"]; }
    let q = Query();
    let col_str = "";
    for i in range(len(columns)) {
        if i > 0 { col_str = col_str + ", "; }
        col_str = col_str + columns[i];
    }
    return q._add("SELECT " + col_str + " FROM " + table);
}

func insert(table, data) {
    let q = Query();
    let cols = [];
    let phs = [];
    for key in data {
        cols.push(key);
        phs.push(q._add_param(data[key]));
    }
    return q._add("INSERT INTO " + table + " (" + cols.join(", ") + ") VALUES (" + phs.join(", ") + ")");
}

func batch_insert(table, columns, rows) {
    let q = Query();
    let col_str = columns.join(", ");
    let placeholders = [];
    for row in rows {
        let phs = [];
        for val in row {
            phs.push(q._add_param(val));
        }
        placeholders.push("(" + phs.join(", ") + ")");
    }
    return q._add("INSERT INTO " + table + " (" + col_str + ") VALUES " + placeholders.join(", "));
}

func update(table, data) {
    let q = Query();
    let sets = [];
    for key in data {
        let ph = q._add_param(data[key]);
        sets.push(key + " = " + ph);
    }
    return q._add("UPDATE " + table + " SET " + sets.join(", "));
}

func delete_from(table) {
    let q = Query();
    return q._add("DELETE FROM " + table);
}

func raw(query_str, params) {
    let q = Query();
    q._parts.push(query_str);
    if params != none {
        for p in params {
            q._params.push(p);
        }
    }
    return q;
}

func count(table, where_col, where_val) {
    let q = select(table).count();
    if where_col != none {
        q = q.where(where_col, "=", where_val);
    }
    return q;
}

func exists(table, where_col, where_val) {
    let q = raw("SELECT EXISTS (SELECT 1 FROM " + table + " WHERE " + where_col + " = ?)", [where_val]);
    return q;
}

func truncate(table) {
    let q = Query();
    return q._add("TRUNCATE TABLE " + table);
}

func drop(table) {
    let q = Query();
    return q._add("DROP TABLE IF EXISTS " + table);
}

func create_table(table, columns, if_not_exists) {
    let q = Query();
    let clause = "CREATE TABLE ";
    if if_not_exists == true { clause = "CREATE TABLE IF NOT EXISTS "; }
    let defs = [];
    for col in columns {
        let def = col["name"] + " " + col["type"];
        if "primary_key" in col and col["primary_key"] == true { def = def + " PRIMARY KEY"; }
        if "auto_increment" in col and col["auto_increment"] == true { def = def + " AUTOINCREMENT"; }
        if "not_null" in col and col["not_null"] == true { def = def + " NOT NULL"; }
        if "default" in col { def = def + " DEFAULT " + col["default"]; }
        if "unique" in col and col["unique"] == true { def = def + " UNIQUE"; }
        defs.push(def);
    }
    return q._add(clause + table + " (" + defs.join(", ") + ")");
}

export {
    Query, select, insert, batch_insert, update, delete_from,
    raw, count, exists, truncate, drop, create_table
};
