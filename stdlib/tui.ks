:: tui - Terminal UI kit (Table, Confirm, Choose)
::
:: Usage:
::   import tui;
::   tui.Table(["Name", "Age"], [["Alice", 30], ["Bob", 25]]).print();
::   if tui.confirm("Continue?") { print("yes"); }

:: ─── Table ─────────────────────────────────────────────────────────────────

class Table {
    func __init__(self, headers, rows) {
        self.headers = headers;
        self.rows = rows;
    }

    func _col_widths(self) {
        let n = len(self.headers);
        let widths = [];
        for i in range(n) { widths.push(len(str(self.headers[i]))); }
        for i in range(len(self.rows)) {
            for j in range(n) {
                let val = str(self.rows[i][j]);
                if len(val) > widths[j] { widths[j] = len(val); }
            }
        }
        return widths;
    }

    func _line(self, widths) {
        let parts = [];
        for i in range(len(widths)) { parts.push("-" * widths[i]); }
        return "+-" + parts.join("-+-") + "-+";
    }

    func _render_row(self, row, widths) {
        let parts = [];
        for i in range(len(widths)) {
            let val = str(row[i]);
            parts.push(val.ljust(widths[i]));
        }
        return "| " + parts.join(" | ") + " |";
    }

    func print(self) {
        let widths = self._col_widths();
        let sep = self._line(widths);
        println(sep);
        println(self._render_row(self.headers, widths));
        println(sep);
        for i in range(len(self.rows)) {
            println(self._render_row(self.rows[i], widths));
        }
        println(sep);
    }
}

:: ─── Confirm / Choose ──────────────────────────────────────────────────────

func confirm(prompt) {
    system_write(2, prompt + " [y/N] ");
    let input = system_stdin_readline();
    let trimmed = input.strip();
    return trimmed == "y" or trimmed == "Y" or trimmed == "yes" or trimmed == "Yes";
}

func choose(prompt, options) {
    system_write(2, prompt + "\n");
    for i in range(len(options)) {
        system_write(2, "  " + str(i + 1) + ". " + options[i] + "\n");
    }
    system_write(2, "Enter number (1-" + str(len(options)) + "): ");
    let input = system_stdin_readline();
    let n = int(input.strip());
    if n >= 1 and n <= len(options) {
        return n - 1;
    }
    return 0;
}

export { Table, confirm, choose };
