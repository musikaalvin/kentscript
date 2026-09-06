:: stdlib_demo.ks - Examples for new stdlib modules
::
:: Run: python3 main.py examples/stdlib_demo.ks

import tui;
import dataframe;
import markdown;
import jwt;
import scheduler;
import watcher;

:: ─── Table ─────────────────────────────────────────────────────────────────

println("=== Table ===");
let table = tui.Table(
    ["Command", "Description"],
    [
        ["import tui", "ASCII tables"],
        ["import dataframe", "Data analysis"],
        ["import markdown", "Markdown to HTML"],
        ["import jwt", "JWT tokens"],
    ]
);
table.print();

:: ─── DataFrame ─────────────────────────────────────────────────────────────

println("\n=== DataFrame ===");
let df = dataframe.DataFrame([
    {"name": "Alice", "dept": "Engineering", "salary": 120000},
    {"name": "Bob", "dept": "Marketing", "salary": 90000},
    {"name": "Charlie", "dept": "Engineering", "salary": 135000},
    {"name": "Diana", "dept": "Finance", "salary": 110000},
], ["name", "dept", "salary"]);

println("Engineers:");
df.filter(func(r) { return r["dept"] == "Engineering"; }).print();

let total = df.aggregate("salary", "sum");
println("Total salary: " + str(total));

let groups = df.groupby("dept");
let keys = groups.keys();
for i in range(len(keys)) {
    println(str(groups[keys[i]].shape()[0]) + " people in " + keys[i]);
}

println("Sorted by salary ascending:");
df.sort("salary", true).print();

:: ─── Markdown ──────────────────────────────────────────────────────────────

println("\n=== Markdown ===");
let html = markdown.to_html("# Hello\n\nThis is **bold** and `code`.\n\n- Item 1\n- Item 2");
println(html);

:: ─── JWT ──────────────────────────────────────────────────────────────────

println("\n=== JWT ===");
let token = jwt.encode({"user": "admin", "role": "editor"}, "my-secret-key");
println("Token: " + token);
let decoded = jwt.decode(token, "my-secret-key");
println("Decoded: " + str(decoded));

:: ─── Scheduler ────────────────────────────────────────────────────────────

println("\n=== Scheduler ===");
let s = scheduler.Scheduler();
let tick_count = 0;
s.every(0.1, func() {
    tick_count = tick_count + 1;
});
s.start();
sleep(0.45);
s.stop();
println("Ticked " + str(tick_count) + " times in ~0.45s (expect ~4)");

:: ─── File Watcher ─────────────────────────────────────────────────────────

println("\n=== File Watcher (polling) ===");
let w = watcher.FileWatcher("/tmp", func(path) {
    println("Changed: " + path);
}, 0.5);
println("Watcher created for /tmp (interval: 0.5s)");

:: ─── Data Pipeline ────────────────────────────────────────────────────────

println("\n=== Data Pipeline ===");
:: Load from JSON, filter, sort, export
let data = [
    {"product": "Widget", "price": 9.99, "stock": 42},
    {"product": "Gadget", "price": 24.99, "stock": 15},
    {"product": "Doohickey", "price": 4.99, "stock": 100},
    {"product": "Thingamajig", "price": 49.99, "stock": 8},
];
let inventory = dataframe.DataFrame(data, ["product", "price", "stock"]);
println("Low stock (<= 15):");
inventory.filter(func(r) { return r["stock"] <= 15; }).print();
println("Cheapest items first:");
inventory.sort("price", true).print();
println("JSON export:");
println(inventory.to_json());
