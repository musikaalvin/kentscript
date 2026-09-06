:: excel - Excel xlsx reader/writer
::
:: Usage:
::   import excel;
::   let r = excel.read("data.xlsx");
::   if r["success"] { print(r["data"]); }
::
::   excel.write("out.xlsx", [["Name", "Age"], ["Alice", 30], ["Bob", 25]]);

func read(path, sheet) {
    if sheet == none { sheet = 0; }
    return system_xlsx_read(path, sheet);
}

func write(path, data, sheet_name) {
    if sheet_name == none { sheet_name = "Sheet1"; }
    return system_xlsx_write(path, data, sheet_name);
}

export { read, write };
