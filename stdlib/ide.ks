:: ide.ks — KentScript IDE Backend
::
:: Serves the Monaco Editor frontend and handles API requests.
:: Frontend lives in stdlib/ide/ (index.html, ide.css, ide.js).
::
:: Usage:
::   import ide;
::   ide.start();
::   ide.start_with_port(3000);

import web;
import os;
import subprocess;

let _ide_port = 8000;
let _ide_root = os.getenv("KENTSCRIPT_IDE_ROOT", ".");
let _ide_static_dir = none;

let _ks_binary = none;

func _find_kentscript() {
    :: Try which/where command
    try {
        let result = subprocess.run(["which", "kentscript"]);
        let path = result.stdout.strip();
        if path != "" and os.path.exists(path) {
            return path;
        }
    } catch(e) {}
    try {
        let result = subprocess.run(["where", "kentscript"]);
        let path = result.stdout.strip();
        if path != "" and os.path.exists(path) {
            return path;
        }
    } catch(e) {}

    :: Platform-specific search paths
    let home = os.getenv("HOME", "");
    let local = os.getenv("LOCALAPPDATA", "");

    let locations = [];

    :: Linux/macOS
    if home != "" {
        locations.push(home + "/.local/bin/kentscript");
    }
    locations.push("/usr/local/bin/kentscript");
    locations.push("/usr/bin/kentscript");

    :: Windows
    if local != "" {
        locations.push(local + "/KentScript/kentscript.exe");
    }

    for loc in locations {
        if os.path.exists(loc) {
            return loc;
        }
    }

    return none;
}

:: ─── File browser ────────────────────────────────────────────────────────────

func _ide_list_files(root, depth) {
    if depth == none { depth = 0; }
    if depth > 5 { return []; }
    if !os.path.exists(root) { return []; }

    let result = [];
    let entries = [];

    try {
        entries = os.listdir(root);
    } catch(e) {
        return [];
    }

    for name in entries {
        if name == "." or name == ".." { continue; }
        if name == ".git" or name == "__pycache__" or name == "node_modules" { continue; }
        if name.startswith(".") { continue; }

        let full_path = root + "/" + name;
        let is_dir = false;

        try {
            is_dir = os.path.isdir(full_path);
        } catch(e) {
            continue;
        }

        let entry = {"name": name, "path": full_path, "is_dir": is_dir};

        if is_dir {
            entry["children"] = _ide_list_files(full_path, depth + 1);
        }

        result.push(entry);
    }

    return result;
}

:: ─── Binary runner ───────────────────────────────────────────────────────────

func _ide_run_cmd(args) {
    if _ks_binary == none {
        _ks_binary = _find_kentscript();
    }
    if _ks_binary == none {
        return {"stdout": "", "stderr": "kentscript binary not found", "returncode": 1};
    }

    let cmd = [];
    if _ks_binary.contains("python3") {
        let parts = _ks_binary.split(" ");
        for p in parts { cmd.push(p); }
    } else {
        cmd.push(_ks_binary);
    }
    for a in args { cmd.push(a); }

    let result = subprocess.run(cmd);
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode};
}

func _ide_run_file(path) {
    return _ide_run_cmd(["run", path]);
}

func _ide_run_code(code) {
    return _ide_run_cmd(["-c", code]);
}

:: ─── Terminal exec (real bash) ───────────────────────────────────────────────
:: Runs arbitrary shell commands like VS Code's integrated terminal.

func _ide_terminal_exec(cmd, cwd) {
    if cmd == none or cmd == "" {
        return {"stdout": "", "stderr": "", "returncode": 0, "cwd": cwd};
    }

    :: Wrap with cd to track CWD, then get pwd after
    let bash_cmd = "cd " + cwd + " 2>/dev/null; " + cmd + "; echo \"___CWD___$(pwd)\"";

    subprocess.set_safe_mode(false);
    let result = subprocess.run(["bash", "-c", bash_cmd]);
    subprocess.set_safe_mode(true);

    :: Extract the CWD marker from stdout
    let stdout = result.stdout;
    let new_cwd = cwd;
    let marker = "___CWD___";
    let marker_idx = stdout.lastIndexOf(marker);
    if marker_idx != -1 {
        new_cwd = stdout.substring(marker_idx + 9);
        :: Remove the marker line from output
        let last_nl = stdout.lastIndexOf("\n");
        if last_nl != -1 and last_nl >= marker_idx - 1 {
            stdout = stdout.substring(0, last_nl);
        }
    }
    new_cwd = new_cwd.strip();

    return {"stdout": stdout, "stderr": result.stderr, "returncode": result.returncode, "cwd": new_cwd};
}

:: ─── Shell exec (KentScript REPL, independent) ─────────────────────────────
:: Each command runs independently - NO history accumulation.
:: This prevents cascading errors from previous commands.

func _ide_shell_exec(code) {
    if code == none or code == "" {
        return {"stdout": "", "stderr": "", "returncode": 0};
    }

    :: Run just the single command (with trailing semicolon to avoid parse issues)
    let cmd_to_run = code;
    let result = _ide_run_code(cmd_to_run);
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    };
}

:: ─── LSP helper — find analyze.py ─────────────────────────────────────────────

func _find_analyze_py() {
    let home = os.getenv("HOME", "");

    :: Try relative to binary
    if _ks_binary != none and !_ks_binary.contains("python3") {
        let bin_dir = os.path.dirname(_ks_binary);
        let candidate = bin_dir + "/../kentscript-lsp/analyze.py";
        if os.path.exists(candidate) {
            return os.path.abspath(candidate);
        }
    }

    :: Try relative to CWD
    let cwd = os.getcwd();
    let candidate = cwd + "/kentscript-lsp/analyze.py";
    if os.path.exists(candidate) {
        return candidate;
    }

    :: Try source repo locations
    if home != "" {
        let repo_path = home + "/kentscript_repo/kentscript-lsp/analyze.py";
        if os.path.exists(repo_path) {
            return repo_path;
        }
    }

    return none;
}

:: ─── Run analyze.py with code via temp file ─────────────────────────────────────
:: Since subprocess.run has no stdin support, we write code to a temp file
:: and pipe it to analyze.py via bash. We disable safe mode for this
:: since pipes are required.

func _run_analyze(code) {
    let analyze_py = _find_analyze_py();
    if analyze_py == none {
        return "";
    }

    let tmp_path = "/tmp/_ks_ide_analyze.ks";
    try {
        let f = open(tmp_path, "w");
        f.write(code);
        f.close();

        let cmd = ["bash", "-c", "cat " + tmp_path + " | python3 " + analyze_py];
        subprocess.set_safe_mode(false);
        let result = subprocess.run(cmd);
        subprocess.set_safe_mode(true);
        os.remove(tmp_path);
        return result.stdout;
    } catch(e) {
        subprocess.set_safe_mode(true);
        try { os.remove(tmp_path); } catch(x) {}
        return "";
    }
}

:: ─── Find static files directory ─────────────────────────────────────────────

func _find_static_dir() {
    :: Try via kentscript binary location
    if _ks_binary != none and !_ks_binary.contains("python3") {
        let bin_dir = os.path.dirname(_ks_binary);
        let candidate = bin_dir + "/../stdlib/ide";
        if os.path.exists(candidate + "/index.html") {
            return os.path.abspath(candidate);
        }
    }

    :: Try relative to current working directory
    let cwd = os.getcwd();
    let candidate = cwd + "/stdlib/ide";
    if os.path.exists(candidate + "/index.html") {
        return candidate;
    }

    :: Platform-specific search paths
    let home = os.getenv("HOME", "");
    let local = os.getenv("LOCALAPPDATA", "");

    :: Linux/macOS cache: ~/.cache/kentscript/v*/stdlib/ide/
    if home != "" {
        let cache_base = home + "/.cache/kentscript";
        if os.path.exists(cache_base) {
            let cache_entries = os.listdir(cache_base);
            for entry in cache_entries {
                let c = cache_base + "/" + entry + "/stdlib/ide";
                if os.path.exists(c + "/index.html") {
                    return c;
                }
            }
        }
        let linux_paths = [
            home + "/.local/share/kentscript/stdlib/ide"
        ];
        for p in linux_paths {
            if os.path.exists(p + "/index.html") {
                return p;
            }
        }
    }

    :: Linux system-wide
    let sys_paths = [
        "/usr/local/share/kentscript/stdlib/ide",
        "/usr/share/kentscript/stdlib/ide"
    ];
    for p in sys_paths {
        if os.path.exists(p + "/index.html") {
            return p;
        }
    }

    :: Windows cache: %LOCALAPPDATA%\KentScript\cache\v*\stdlib\ide\
    if local != "" {
        let win_cache = local + "/KentScript/cache";
        if os.path.exists(win_cache) {
            let cache_entries = os.listdir(win_cache);
            for entry in cache_entries {
                let c = win_cache + "/" + entry + "/stdlib/ide";
                if os.path.exists(c + "/index.html") {
                    return c;
                }
            }
        }
        let win_install = local + "/KentScript/stdlib/ide";
        if os.path.exists(win_install + "/index.html") {
            return win_install;
        }
    }

    :: macOS Application Support
    if home != "" {
        let mac_path = home + "/Library/Application Support/kentscript/stdlib/ide";
        if os.path.exists(mac_path + "/index.html") {
            return mac_path;
        }
    }

    return none;
}

:: ─── Start server ────────────────────────────────────────────────────────────

func start() {
    start_with_port(8000);
}

func start_with_port(port) {
    _ide_port = port;
    _ks_binary = _find_kentscript();

    :: Find the stdlib/ide directory at runtime
    _ide_static_dir = _find_static_dir();
    if _ide_static_dir == none {
        print("ERROR: Cannot find IDE frontend files (stdlib/ide/).");
        print("Make sure kentscript is installed correctly.");
        return;
    }

    let app = web.App();

    :: Serve index.html at root
    app.get("/", func(req) {
        try {
            let f = open(_ide_static_dir + "/index.html", "r");
            let content = f.read();
            f.close();
            return web.html(content);
        } catch(e) {
            return web.error(404, "IDE frontend not found");
        }
    });

    :: Serve ide-app.js
    app.get("/ide-app.js", func(req) {
        try {
            let f = open(_ide_static_dir + "/ide-app.js", "r");
            let content = f.read();
            f.close();
            return {"status": 200, "body": content, "content_type": "application/javascript"};
        } catch(e) {
            return web.error(404, "IDE file not found");
        }
    });

    :: ── API: file browser ──
    app.get("/api/files", func(req) {
        let root = _ide_root;
        if "query" in req and "root" in req["query"] {
            root = req["query"]["root"];
        }
        return web.json(_ide_list_files(root, 0));
    });

    :: ── API: read file ──
    app.get("/api/read", func(req) {
        let path = "";
        if "query" in req and "path" in req["query"] {
            path = req["query"]["path"];
        }
        if path == "" {
            return web.json({"error": "No path specified"});
        }
        if path.contains("..") {
            return web.json({"error": "Invalid path"});
        }
        if !os.path.exists(path) {
            return web.json({"error": "File not found"});
        }
        let f = open(path, "r");
        let content = f.read();
        f.close();
        return web.json({"content": content});
    });

    :: ── API: save file ──
    app.post("/api/save", func(req) {
        let data = req["parsed_body"];
        let path = data["path"];
        let content = data["content"];
        if path == none {
            return web.json({"error": "No path"});
        }
        if path.contains("..") {
            return web.json({"error": "Invalid path"});
        }
        let dir = os.path.dirname(path);
        if dir != "" and !os.path.exists(dir) {
            os.makedirs(dir);
        }
        let f = open(path, "w");
        f.write(content);
        f.close();
        return web.json({"ok": true});
    });

    :: ── API: run file ──
    app.post("/api/run", func(req) {
        let data = req["parsed_body"];
        let path = data["path"];
        if path == none {
            return web.json({"error": "No path"});
        }
        if path.contains("..") {
            return web.json({"error": "Invalid path"});
        }
        return web.json(_ide_run_file(path));
    });

    :: ── API: run code snippet ──
    app.post("/api/run_code", func(req) {
        let data = req["parsed_body"];
        let code = data["code"];
        if code == none or code == "" {
            return web.json({"error": "No code"});
        }
        return web.json(_ide_run_code(code));
    });

    :: ── API: terminal exec (real bash shell) ──
    :: Runs arbitrary shell commands, tracks CWD.
    :: Accepts {cmd: string, cwd: string}
    app.post("/api/terminal/exec", func(req) {
        let data = req["parsed_body"];
        let cmd = data["cmd"];
        let cwd = _ide_root;
        if "cwd" in data and data["cwd"] != none and data["cwd"] != "" {
            cwd = data["cwd"];
        }
        return web.json(_ide_terminal_exec(cmd, cwd));
    });

    :: ── API: shell exec (KentScript REPL) ──
    :: Runs a single KentScript code snippet independently (no history cascade).
    :: Accepts {code: string}
    app.post("/api/shell/exec", func(req) {
        let data = req["parsed_body"];
        let code = data["code"];
        if code == none or code == "" {
            return web.json({"stdout": "", "stderr": "", "returncode": 0});
        }
        return web.json(_ide_shell_exec(code));
    });

    :: ── API: LSP complete ──
    :: POST {code: string, line: int, column: int, prefix: string}
    :: Returns completion items from the analyzer
    app.post("/api/lsp/complete", func(req) {
        let data = req["parsed_body"];
        let code = data["code"];
        if code == none { code = ""; }
        let line = 0;
        if "line" in data { line = data["line"]; }
        let col = 0;
        if "column" in data { col = data["column"]; }
        let prefix = "";
        if "prefix" in data { prefix = data["prefix"]; }

        :: Run analyze.py on the code
        try {
            let output = _run_analyze(code).strip();
            if output == "" {
                return web.json({"items": []});
            }

            :: Parse the JSON output to extract symbols for completion
            :: analyze.py returns {diagnostics: [...], symbols: [{name, kind, type, line}, ...]}
            let items = [];
            let symbols_start = output.indexOf('"symbols"');
            if symbols_start == -1 {
                return web.json({"items": items});
            }

            :: Extract symbol names and kinds using simple string parsing
            let search_from = symbols_start;
            while true {
                let name_idx = output.indexOf('"name":', search_from);
                if name_idx == -1 { break; }
                let kind_idx = output.indexOf('"kind":', name_idx);
                if kind_idx == -1 { break; }

                :: Extract name
                let name_start = output.indexOf('"', name_idx + 7) + 1;
                let name_end = output.indexOf('"', name_start);
                let sym_name = output.substring(name_start, name_end);

                :: Extract kind
                let kind_start = output.indexOf('"', kind_idx + 7) + 1;
                let kind_end = output.indexOf('"', kind_start);
                let sym_kind = output.substring(kind_start, kind_end);

                :: Filter by prefix if provided
                if prefix == "" or sym_name.startswith(prefix) {
                    let kind_map = {"var": "Variable", "func": "Function", "class": "Class",
                                   "module": "Module", "const": "Constant", "param": "Variable",
                                   "struct": "Struct", "enum": "Enum", "trait": "Trait",
                                   "interface": "Interface"};
                    let completion_kind = 1;
                    if sym_kind in kind_map {
                        let mk = kind_map[sym_kind];
                        if mk == "Function" { completion_kind = 3; }
                        else if mk == "Variable" { completion_kind = 6; }
                        else if mk == "Class" { completion_kind = 7; }
                        else if mk == "Module" { completion_kind = 9; }
                        else if mk == "Constant" { completion_kind = 14; }
                        else if mk == "Struct" { completion_kind = 22; }
                        else if mk == "Enum" { completion_kind = 13; }
                        else if mk == "Trait" { completion_kind = 8; }
                        else if mk == "Interface" { completion_kind = 7; }
                    }
                    items.push({
                        "label": sym_name,
                        "kind": completion_kind,
                        "detail": sym_kind
                    });
                }

                search_from = kind_end;
                if search_from > output.length() { break; }
            }

            return web.json({"items": items});
        } catch(e) {
            return web.json({"items": [], "error": str(e)});
        }
    });

    :: ── API: LSP hover ──
    :: POST {code: string, line: int, column: int}
    :: Returns hover information for the symbol at the given position
    app.post("/api/lsp/hover", func(req) {
        let data = req["parsed_body"];
        let code = data["code"];
        if code == none { code = ""; }
        let line = 0;
        if "line" in data { line = data["line"]; }

        try {
            let output = _run_analyze(code).strip();
            if output == "" {
                return web.json({"contents": ""});
            }

            :: Find symbol at the given line
            let symbols_start = output.indexOf('"symbols"');
            if symbols_start == -1 {
                return web.json({"contents": ""});
            }

            let search_from = symbols_start;
            while true {
                let name_idx = output.indexOf('"name":', search_from);
                if name_idx == -1 { break; }
                let line_idx = output.indexOf('"line":', name_idx);
                if line_idx == -1 { break; }
                let kind_idx = output.indexOf('"kind":', name_idx);
                let type_idx = output.indexOf('"type":', kind_idx);

                :: Extract line number
                let ln_start = line_idx + 7;
                while ln_start < output.length() and output.substring(ln_start, ln_start + 1) == " " {
                    ln_start = ln_start + 1;
                }
                let ln_end = ln_start;
                while ln_end < output.length() and output.substring(ln_end, ln_end + 1) >= "0" and output.substring(ln_end, ln_end + 1) <= "9" {
                    ln_end = ln_end + 1;
                }
                let sym_line = 0;
                if ln_end > ln_start {
                    sym_line = int(output.substring(ln_start, ln_end));
                }

                :: Extract name
                let name_start = output.indexOf('"', name_idx + 7) + 1;
                let name_end = output.indexOf('"', name_start);
                let sym_name = output.substring(name_start, name_end);

                :: Extract kind
                let kind_start = output.indexOf('"', kind_idx + 7) + 1;
                let kind_end = output.indexOf('"', kind_start);
                let sym_kind = output.substring(kind_start, kind_end);

                :: Extract type
                let sym_type = "";
                if type_idx != -1 and type_idx < name_idx + 200 {
                    let type_start = output.indexOf('"', type_idx + 7) + 1;
                    let type_end = output.indexOf('"', type_start);
                    if type_end > type_start {
                        sym_type = output.substring(type_start, type_end);
                    }
                }

                if sym_line == line {
                    let hover_text = "**" + sym_name + "** (" + sym_kind + ")";
                    if sym_type != "" and sym_type != "auto" {
                        hover_text = hover_text + " : `" + sym_type + "`";
                    }
                    return web.json({"contents": hover_text});
                }

                search_from = kind_end;
                if search_from > output.length() { break; }
            }

            return web.json({"contents": ""});
        } catch(e) {
            return web.json({"contents": "", "error": str(e)});
        }
    });

    :: ── API: LSP diagnostics ──
    :: POST {code: string}
    :: Returns diagnostics (errors/warnings) for the given code
    app.post("/api/lsp/diagnose", func(req) {
        let data = req["parsed_body"];
        let code = data["code"];
        if code == none { code = ""; }

        try {
            let output = _run_analyze(code).strip();
            if output == "" {
                return web.json({"diagnostics": []});
            }

            :: Extract diagnostics array
            let diag_start = output.indexOf('"diagnostics"');
            if diag_start == -1 {
                return web.json({"diagnostics": []});
            }

            :: Find the diagnostics array content
            let bracket_start = output.indexOf("[", diag_start);
            if bracket_start == -1 {
                return web.json({"diagnostics": []});
            }

            :: Find matching closing bracket
            let depth = 0;
            let arr_end = bracket_start;
            for i in range(bracket_start, output.length()) {
                let ch = output.substring(i, i + 1);
                if ch == "[" { depth = depth + 1; }
                if ch == "]" { depth = depth - 1; }
                if depth == 0 {
                    arr_end = i + 1;
                    break;
                }
            }

            let diag_json = output.substring(bracket_start, arr_end);

            :: If diagnostics is empty, return early
            if diag_json == "[]" {
                return web.json({"diagnostics": []});
            }

            :: Parse individual diagnostics
            let diagnostics = [];
            let search_from = 0;
            while true {
                let msg_idx = diag_json.indexOf('"message":', search_from);
                if msg_idx == -1 { break; }
                let line_idx = diag_json.indexOf('"line":', msg_idx);
                if line_idx == -1 { break; }
                let sev_idx = diag_json.indexOf('"severity":', line_idx);

                :: Extract message
                let msg_start = diag_json.indexOf('"', msg_idx + 10) + 1;
                let msg_end = diag_json.indexOf('"', msg_start);
                let msg = diag_json.substring(msg_start, msg_end);

                :: Extract line
                let ln_start = line_idx + 7;
                while ln_start < diag_json.length() and diag_json.substring(ln_start, ln_start + 1) == " " {
                    ln_start = ln_start + 1;
                }
                let ln_end = ln_start;
                while ln_end < diag_json.length() and diag_json.substring(ln_end, ln_end + 1) >= "0" and diag_json.substring(ln_end, ln_end + 1) <= "9" {
                    ln_end = ln_end + 1;
                }
                let err_line = 0;
                if ln_end > ln_start {
                    err_line = int(diag_json.substring(ln_start, ln_end));
                }

                :: Extract severity (1=Error, 2=Warning, 3=Info, 4=Hint)
                let severity = 1;
                if sev_idx != -1 {
                    let sv_start = sev_idx + 11;
                    while sv_start < diag_json.length() and diag_json.substring(sv_start, sv_start + 1) == " " {
                        sv_start = sv_start + 1;
                    }
                    let sv_end = sv_start;
                    while sv_end < diag_json.length() and diag_json.substring(sv_end, sv_end + 1) >= "0" and diag_json.substring(sv_end, sv_end + 1) <= "9" {
                        sv_end = sv_end + 1;
                    }
                    if sv_end > sv_start {
                        severity = int(diag_json.substring(sv_start, sv_end));
                    }
                }

                diagnostics.push({
                    "message": msg,
                    "line": err_line,
                    "severity": severity
                });

                search_from = msg_end;
                if search_from >= diag_json.length() { break; }
            }

            return web.json({"diagnostics": diagnostics});
        } catch(e) {
            return web.json({"diagnostics": [], "error": str(e)});
        }
    });

    :: ── API: new file ──
    app.post("/api/newfile", func(req) {
        let data = req["parsed_body"];
        let name = data["name"];
        if name == none or name == "" {
            return web.json({"error": "No name"});
        }
        if name.contains("..") or name.contains("/") {
            return web.json({"error": "Invalid name"});
        }
        let path = _ide_root + "/" + name;
        let f = open(path, "w");
        f.write("");
        f.close();
        return web.json({"ok": true, "path": path});
    });

    :: ── API: new folder ──
    app.post("/api/newfolder", func(req) {
        let data = req["parsed_body"];
        let name = data["name"];
        if name == none or name == "" {
            return web.json({"error": "No name"});
        }
        if name.contains("..") or name.contains("/") {
            return web.json({"error": "Invalid name"});
        }
        let path = _ide_root + "/" + name;
        os.makedirs(path);
        return web.json({"ok": true, "path": path});
    });

    :: ── API: delete file/folder ──
    app.post("/api/delete", func(req) {
        let data = req["parsed_body"];
        let path = data["path"];
        if path == none {
            return web.json({"error": "No path"});
        }
        if path.contains("..") {
            return web.json({"error": "Invalid path"});
        }
        if os.path.isdir(path) {
            os.rmdir(path);
        } else {
            os.remove(path);
        }
        return web.json({"ok": true});
    });

    :: ── API: change root ──
    app.post("/api/change_root", func(req) {
        let data = req["parsed_body"];
        let path = data["path"];
        if path == none or path == "" {
            return web.json({"error": "No path"});
        }
        if !os.path.exists(path) {
            return web.json({"error": "Directory not found"});
        }
        _ide_root = path;
        return web.json({"ok": true, "root": path});
    });

    :: ── API: health ──
    app.get("/api/health", func(req) {
        return web.json({"status": "ok", "version": "3.1.0", "root": _ide_root});
    });

    print("");
    print("  KentScript IDE v3.1.0");
    print("  ─────────────────────────────────────");
    print("  Open: http://localhost:" + str(port));
    print("  Root: " + os.path.abspath(_ide_root));
    if _ks_binary != none {
        print("  Binary: " + _ks_binary);
    } else {
        print("  Warning: kentscript binary not found");
    }
    print("  Press Ctrl+C to stop");
    print("");

    let current_port = port;
    for attempt in range(50) {
        try {
            app.listen(current_port);
            return;
        } catch(e) {
            let msg = str(e);
            if msg.contains("Address already in use") or msg.contains("EADDRINUSE") {
                current_port = current_port + 1;
                if attempt == 0 {
                    print("  Port " + str(port) + " busy, using " + str(current_port) + "...");
                }
            } else {
                print("  Server error: " + msg);
                return;
            }
        }
    }
    print("  Could not find an available port after 50 attempts.");
}

export {start, start_with_port};
