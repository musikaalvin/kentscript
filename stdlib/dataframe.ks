:: dataframe - Data analysis toolkit (pandas-like)
::
:: Usage:
::   import dataframe;
::   let df = dataframe.DataFrame([{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]);
::   df.filter(func(r) { return r["age"] > 25; }).print();

class DataFrame {
    func __init__(self, data, columns) {
        if data == none { data = []; }
        self.data = data;
        if columns == none and len(data) > 0 {
            columns = data[0].keys();
        }
        self.columns = columns;
        if self.columns == none { self.columns = []; }
    }

    func from_csv(path) {
        let lines = fs_read_text(path).split(chr(10));
        while len(lines) > 0 and lines[len(lines) - 1] == "" { lines.pop(); }
        if len(lines) < 2 { return DataFrame([], []); }
        let headers = lines[0].split(",");
        let rows = [];
        for i in range(1, len(lines)) {
            let vals = lines[i].split(",");
            let row = {};
            for j in range(len(headers)) {
                if j < len(vals) {
                    row[headers[j].strip()] = vals[j].strip();
                } else {
                    row[headers[j].strip()] = "";
                }
            }
            rows.push(row);
        }
        return DataFrame(rows, headers);
    }

    func from_json(path) {
        let content = fs_read_text(path);
        let data = system_json_loads(content);
        let cols = [];
        if len(data) > 0 { cols = data[0].keys(); }
        return DataFrame(data, cols);
    }

    func shape(self) {
        return [len(self.data), len(self.columns)];
    }

    func head(self, n) {
        if n == none { n = 5; }
        let limit = n;
        if limit > len(self.data) { limit = len(self.data); }
        let rows = [];
        for i in range(limit) { rows.push(self.data[i]); }
        return DataFrame(rows, self.columns);
    }

    func tail(self, n) {
        if n == none { n = 5; }
        let start = len(self.data) - n;
        if start < 0 { start = 0; }
        let rows = [];
        for i in range(start, len(self.data)) { rows.push(self.data[i]); }
        return DataFrame(rows, self.columns);
    }

    func filter(self, predicate) {
        let rows = [];
        for i in range(len(self.data)) {
            if predicate(self.data[i]) {
                rows.push(self.data[i]);
            }
        }
        return DataFrame(rows, self.columns);
    }

    func sort(self, key, ascending) {
        if ascending == none { ascending = true; }
        let rows = [];
        for i in range(len(self.data)) { rows.push(self.data[i]); }
        let n = len(rows);
        for i in range(n) {
            for j in range(i + 1, n) {
                let a = rows[i][key];
                let b = rows[j][key];
                let swap = false;
                if ascending {
                    if a > b { swap = true; }
                } else {
                    if a < b { swap = true; }
                }
                if swap {
                    let tmp = rows[i];
                    rows[i] = rows[j];
                    rows[j] = tmp;
                }
            }
        }
        return DataFrame(rows, self.columns);
    }

    func select(self, cols) {
        let rows = [];
        for i in range(len(self.data)) {
            let row = {};
            for j in range(len(cols)) {
                if cols[j] in self.data[i] {
                    row[cols[j]] = self.data[i][cols[j]];
                }
            }
            rows.push(row);
        }
        return DataFrame(rows, cols);
    }

    func aggregate(self, column, op) {
        let vals = [];
        for i in range(len(self.data)) {
            let v = self.data[i][column];
            vals.push(v);
        }
        if op == "sum" {
            let total = 0;
            for i in range(len(vals)) { total = total + vals[i]; }
            return total;
        } elif op == "mean" or op == "avg" {
            let total = 0;
            for i in range(len(vals)) { total = total + vals[i]; }
            if len(vals) > 0 { return total / len(vals); }
            return 0;
        } elif op == "min" {
            if len(vals) == 0 { return none; }
            let m = vals[0];
            for i in range(1, len(vals)) { if vals[i] < m { m = vals[i]; } }
            return m;
        } elif op == "max" {
            if len(vals) == 0 { return none; }
            let m = vals[0];
            for i in range(1, len(vals)) { if vals[i] > m { m = vals[i]; } }
            return m;
        } elif op == "count" {
            return len(vals);
        }
        return none;
    }

    func groupby(self, key) {
        let groups = {};
        for i in range(len(self.data)) {
            let val = self.data[i][key];
            if not (val in groups) { groups[val] = []; }
            groups[val].push(self.data[i]);
        }
        let result = {};
        let keys = groups.keys();
        for i in range(len(keys)) {
            let k = keys[i];
            result[k] = DataFrame(groups[k], self.columns);
        }
        return result;
    }

    func to_csv(self, path) {
        let lines = [self.columns.join(",")];
        for i in range(len(self.data)) {
            let row = [];
            for j in range(len(self.columns)) {
                row.push(str(self.data[i][self.columns[j]]));
            }
            lines.push(row.join(","));
        }
        fs_write_text(path, lines.join(chr(10)));
    }

    func to_json(self) {
        return system_json_dumps(self.data);
    }

    func print(self) {
        let headers = self.columns;
        let widths = [];
        for i in range(len(headers)) { widths.push(len(str(headers[i]))); }
        for i in range(len(self.data)) {
            for j in range(len(headers)) {
                let val = str(self.data[i][headers[j]]);
                if len(val) > widths[j] { widths[j] = len(val); }
            }
        }
        let sep = "+-";
        for i in range(len(widths)) {
            if i > 0 { sep = sep + "-+-"; }
            sep = sep + "-" * widths[i];
        }
        sep = sep + "-+";

        func render_row(vals) {
            let parts = [];
            for i in range(len(widths)) {
                parts.push(str(vals[i]).ljust(widths[i]));
            }
            return "| " + parts.join(" | ") + " |";
        }

        println(sep);
        println(render_row(headers));
        println(sep);
        for i in range(len(self.data)) {
            let vals = [];
            for j in range(len(headers)) {
                vals.push(self.data[i][headers[j]]);
            }
            println(render_row(vals));
        }
        println(sep);
    }
}

export { DataFrame };
