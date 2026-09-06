#!/usr/bin/env python3
"""KentScript IDE Server — plain Python HTTP server, no dependencies."""
import http.server, json, os, subprocess, sys, urllib.parse, shutil, threading, re, logging, asyncio, pty

IDE_DIR = os.path.dirname(os.path.abspath(__file__))
IDE_STATIC = os.path.join(IDE_DIR, "ide")
LSP_DIR = os.path.join(os.path.dirname(IDE_DIR), "kentscript-lsp")
ROOT = os.environ.get("KENTSCRIPT_IDE_ROOT", os.getcwd())
KS_BIN = None

# The IDE terminal is plain text — strip ANSI/VT escape codes so colored
# output (progress bars, the color module, error formatter, …) never shows
# as raw garbage like "[35m" in the browser.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

def strip_ansi(text):
    if text is None:
        return ""
    return _ANSI_RE.sub("", text)

def find_kentscript():
    global KS_BIN
    if KS_BIN and os.path.isfile(KS_BIN): return KS_BIN
    repo_root = os.path.dirname(IDE_DIR)
    candidates = [
        os.path.join(repo_root, "dist", "kentscript"),
        os.path.join(repo_root, "kentscript"),
        os.path.join(ROOT, "dist", "kentscript"),
        os.path.join(ROOT, "kentscript"),
        shutil.which("kentscript") or "",
    ]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            KS_BIN = c
            break
    return KS_BIN

def ks_run(args):
    binary = find_kentscript()
    if binary is None:
        return {"stdout": "", "stderr": "kentscript binary not found", "returncode": 1}
    cmd = [binary] + args
    timeout = int(os.environ.get("KENTSCRIPT_RUN_TIMEOUT", "600"))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"stdout": strip_ansi(r.stdout), "stderr": strip_ansi(r.stderr), "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timed out", "returncode": 1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": 1}

def ks_run_code(code):
    return ks_run(["-c", code])

def ks_run_file(path, mode="interpreter"):
    if mode == "compiler":
        return ks_run(["build", path, "--run", "--quiet"])
    return ks_run(["run", path])

def terminal_exec(cmd, cwd):
    if not cmd:
        return {"stdout": "", "stderr": "", "returncode": 0, "cwd": cwd}
    full = "cd {} 2>/dev/null; {}; echo ___CWD___$(pwd)".format(cwd, cmd)
    try:
        r = subprocess.run(["bash", "-c", full], capture_output=True, text=True,
                           timeout=int(os.environ.get("KENTSCRIPT_RUN_TIMEOUT", "600")))
        out = r.stdout
        new_cwd = cwd
        marker = "___CWD___"
        idx = out.rfind(marker)
        if idx != -1:
            new_cwd = out[idx+9:].strip()
            last_nl = out.rfind("\n", 0, idx)
            if last_nl >= idx - 1:
                out = out[:last_nl]
        return {"stdout": strip_ansi(out), "stderr": strip_ansi(r.stderr), "returncode": r.returncode, "cwd": new_cwd}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timed out", "returncode": 1, "cwd": cwd}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": 1, "cwd": cwd}

def list_files(root, depth=0):
    if depth > 5 or not os.path.isdir(root): return []
    result = []
    skip = {".git", "__pycache__", "node_modules", ".DS_Store"}
    try:
        entries = sorted(os.listdir(root))
    except:
        return []
    for name in entries:
        if name.startswith(".") or name in skip: continue
        fp = os.path.join(root, name)
        is_dir = os.path.isdir(fp)
        entry = {"name": name, "path": fp, "is_dir": is_dir}
        if is_dir:
            entry["children"] = list_files(fp, depth+1)
        result.append(entry)
    return result

MIME = {
    ".html": "text/html", ".js": "application/javascript", ".css": "text/css",
    ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
    ".ico": "image/x-icon", ".woff": "font/woff", ".woff2": "font/woff2"
}

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, filepath, ct):
        try:
            with open(filepath, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        except:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = dict(urllib.parse.parse_qsl(parsed.query))

        if path == "/":
            return self.send_static(os.path.join(IDE_STATIC, "index.html"), "text/html")
        if path == "/ide-app.js":
            return self.send_static(os.path.join(IDE_STATIC, "ide-app.js"), "application/javascript")
        if path == "/api/health":
            return self.send_json({"status": "ok", "version": "3.1.0", "root": ROOT})
        if path == "/api/files":
            root = qs.get("root", ROOT)
            return self.send_json(list_files(root))
        if path == "/api/builtins":
            return self.send_json(get_builtins())
        if path == "/api/debug/output":
            sid = qs.get("session", "")
            sess = debug_sessions.get(sid)
            if not sess:
                return self.send_json({"output": "", "running": False})
            out = sess["output"]
            sess["output"] = ""
            return self.send_json({"output": out, "running": sess["running"]})
        if path == "/api/read":
            p = qs.get("path", "")
            if not p: return self.send_json({"error": "No path"})
            if ".." in p: return self.send_json({"error": "Invalid path"})
            if not os.path.isfile(p): return self.send_json({"error": "File not found"})
            try:
                with open(p, "r") as f:
                    return self.send_json({"content": f.read()})
            except Exception as e:
                return self.send_json({"error": str(e)})

        static = os.path.join(IDE_STATIC, path.lstrip("/"))
        if os.path.isfile(static):
            ct = MIME.get(os.path.splitext(path)[1], "application/octet-stream")
            return self.send_static(static, ct)

        self.send_error(404)

    def do_POST(self):
        global ROOT
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        if path == "/api/save":
            p = data.get("path")
            c = data.get("content", "")
            if not p: return self.send_json({"error": "No path"})
            if ".." in p: return self.send_json({"error": "Invalid path"})
            d = os.path.dirname(p)
            if d and not os.path.exists(d):
                os.makedirs(d)
            with open(p, "w") as f:
                f.write(c)
            return self.send_json({"ok": True})
        if path == "/api/analyze":
            src = data.get("source", "")
            return self.send_json(ks_analyze_source(src))
        if path == "/api/debug/start":
            p = data.get("path", "")
            if ".." in p: return self.send_json({"error": "Invalid path"})
            bps = data.get("breakpoints", [])
            return self.send_json(ks_debug_start(p, bps))
        if path == "/api/debug/command":
            sid = data.get("session", "")
            sess = debug_sessions.get(sid)
            if not sess:
                return self.send_json({"error": "No such debug session"})
            cmd = data.get("cmd", "")
            try:
                sess["proc"].stdin.write(cmd + "\n")
                sess["proc"].stdin.flush()
            except Exception as e:
                return self.send_json({"error": str(e)})
            return self.send_json({"ok": True})
        if path == "/api/debug/stop":
            sid = data.get("session", "")
            sess = debug_sessions.get(sid)
            if sess:
                try:
                    sess["proc"].terminate()
                except Exception:
                    pass
                sess["running"] = False
            return self.send_json({"ok": True})
        if path == "/api/run":
            p = data.get("path")
            if not p: return self.send_json({"error": "No path"})
            return self.send_json(ks_run_file(p, mode=data.get("mode", "interpreter")))
        if path == "/api/run_code":
            code = data.get("code", "")
            if not code: return self.send_json({"error": "No code"})
            return self.send_json(ks_run_code(code))
        if path == "/api/terminal/exec":
            cmd = data.get("cmd", "")
            cwd = data.get("cwd", ROOT)
            return self.send_json(terminal_exec(cmd, cwd))
        if path == "/api/shell/exec":
            code = data.get("code", "")
            if not code: return self.send_json({"stdout": "", "stderr": "", "returncode": 0})
            return self.send_json(ks_run_code(code))
        if path == "/api/newfile":
            name = data.get("name", "")
            if not name: return self.send_json({"error": "No name"})
            if ".." in name or "/" in name: return self.send_json({"error": "Invalid name"})
            fp = os.path.join(ROOT, name)
            with open(fp, "w") as f: f.write("")
            return self.send_json({"ok": True, "path": fp})
        if path == "/api/newfolder":
            name = data.get("name", "")
            if not name: return self.send_json({"error": "No name"})
            if ".." in name or "/" in name: return self.send_json({"error": "Invalid name"})
            fp = os.path.join(ROOT, name)
            os.makedirs(fp, exist_ok=True)
            return self.send_json({"ok": True, "path": fp})
        if path == "/api/delete":
            p = data.get("path")
            if not p: return self.send_json({"error": "No path"})
            if ".." in p: return self.send_json({"error": "Invalid path"})
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
            return self.send_json({"ok": True})
        if path == "/api/change_root":
            p = data.get("path", "")
            if not p or not os.path.isdir(p):
                return self.send_json({"error": "Directory not found"})
            ROOT = os.path.abspath(p)
            return self.send_json({"ok": True, "root": ROOT})
        if path == "/api/rename":
            p    = data.get("path", "")
            name = data.get("new_name", "")
            if not p or not name:
                return self.send_json({"error": "Missing path or new_name"})
            if ".." in p or ".." in name or "/" in name or "\\" in name:
                return self.send_json({"error": "Invalid path or name"})
            if not os.path.exists(p):
                return self.send_json({"error": "Path not found"})
            new_path = os.path.join(os.path.dirname(p), name)
            os.rename(p, new_path)
            return self.send_json({"ok": True, "path": new_path})
        if path == "/api/move":
            src  = data.get("src", "")
            dest = data.get("dest", "")
            if not src or not dest:
                return self.send_json({"error": "Missing src or dest"})
            if ".." in src or ".." in dest:
                return self.send_json({"error": "Invalid path"})
            if not os.path.exists(src):
                return self.send_json({"error": "Source not found"})
            if not os.path.isdir(dest):
                return self.send_json({"error": "Destination must be a directory"})
            shutil.move(src, os.path.join(dest, os.path.basename(src)))
            return self.send_json({"ok": True})

        self.send_error(404)

def ks_analyze_source(src):
    """Run the real KentScript semantic analyzer (lexer+parser+scope/type
    check) on source text and return structured diagnostics + symbols.
    Used by the IDE for real-time error squiggles/Problems panel without
    depending on the WebSocket LSP bridge."""
    try:
        if LSP_DIR not in sys.path:
            sys.path.insert(0, LSP_DIR)
        from analyze import analyze as _analyze
        res = _analyze(src)
        return {"diagnostics": res.get("diagnostics", []), "symbols": res.get("symbols", [])}
    except Exception as e:
        return {"diagnostics": [{"line": 0, "col": 0, "severity": 1,
                                 "message": "Analyzer error: %s" % str(e)}],
                "symbols": []}


_ks_builtins_cache = None
def get_builtins():
    global _ks_builtins_cache
    if _ks_builtins_cache is not None:
        return _ks_builtins_cache
    try:
        if LSP_DIR not in sys.path:
            sys.path.insert(0, LSP_DIR)
        from analyze import KEYWORDS, TYPES, ALL_BUILTINS
        _ks_builtins_cache = {
            "keywords": sorted(KEYWORDS),
            "types": sorted(TYPES),
            "builtins": sorted(ALL_BUILTINS),
        }
    except Exception as e:
        _ks_builtins_cache = {"keywords": [], "types": [], "builtins": [], "error": str(e)}
    return _ks_builtins_cache


# ===== DEBUG SESSION MANAGER (drives `kentscript debug` as a subprocess) =====
debug_sessions = {}
_debug_seq = 0

def ks_debug_start(path, breakpoints):
    global _debug_seq
    bin_path = find_kentscript()
    if bin_path:
        cmd = [bin_path, "debug", path]
    else:
        main_py = os.path.join(os.path.dirname(IDE_DIR), "main.py")
        if os.path.isfile(main_py):
            cmd = [sys.executable, main_py, "debug", path]
        else:
            return {"error": "kentscript binary not found"}
    if not os.path.isfile(path):
        return {"error": "File not found: %s" % path}
    for b in (breakpoints or []):
        cmd += ["--break", str(int(b))]
    try:
        # A plain pipe is fine: the child debug handler forces line-buffering
        # (sys.stdout.reconfigure) so output streams per line instead of
        # blocking until process exit. PYTHONUNBUFFERED is belt-and-suspenders.
        _env = os.environ.copy()
        _env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1,
                                cwd=ROOT, env=_env)
    except Exception as e:
        return {"error": str(e)}
    _debug_seq += 1
    sid = "dbg%d" % _debug_seq
    sess = {"proc": proc, "output": "", "running": True}
    debug_sessions[sid] = sess

    def reader():
        try:
            for line in proc.stdout:
                sess["output"] += strip_ansi(line)
        except Exception:
            pass
        sess["running"] = False
        try:
            proc.stdout.close()
        except Exception:
            pass

    threading.Thread(target=reader, daemon=True).start()
    return {"session": sid}


def start_lsp_bridge(http_port):
    """WebSocket bridge to the KentScript LSP (node kentscript-lsp/server.js
    --stdio). Each browser tab gets its own LSP process (isolated state), just
    like VS Code. Browser <-> WS <-> (JSON-RPC) <-> node LSP stdio."""
    LSP_DIR = os.path.join(os.path.dirname(IDE_DIR), "kentscript-lsp")
    if not os.path.isfile(os.path.join(LSP_DIR, "server.js")):
        print("  [LSP] kentscript-lsp/server.js not found — language features off")
        return
    lsp_port = http_port + 1

    async def _relay(ws):
        try:
            proc = await asyncio.create_subprocess_exec(
                "node", os.path.join(LSP_DIR, "server.js"), "--stdio",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, cwd=LSP_DIR)
        except Exception as e:
            print("  [LSP] spawn failed:", e)
            return

        async def to_ws():
            buf = b""
            while True:
                data = await proc.stdout.read(65536)
                if not data:
                    break
                buf += data
                while True:
                    i = buf.find(b"\r\n\r\n")
                    if i == -1:
                        break
                    m = re.search(rb"Content-Length: (\d+)", buf[:i])
                    if not m:
                        buf = buf[i + 4:]
                        continue
                    cl = int(m.group(1))
                    if len(buf) < i + 4 + cl:
                        break
                    body = buf[i + 4:i + 4 + cl]
                    buf = buf[i + 4 + cl:]
                    try:
                        await ws.send(body.decode("utf-8"))
                    except Exception:
                        return

        async def from_ws():
            async for message in ws:
                data = message.encode("utf-8") if isinstance(message, str) else bytes(message)
                try:
                    proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(data) + data)
                    await proc.stdin.drain()
                except Exception:
                    return

        async def err_pump():
            async for line in proc.stderr:
                sys.stderr.write("  [LSP] " + line.decode("utf-8", "replace"))

        try:
            await asyncio.gather(to_ws(), from_ws(), err_pump())
        except Exception:
            pass
        finally:
            try:
                proc.terminate()
            except Exception:
                pass

    async def _serve():
        import websockets
        async with websockets.serve(_relay, "0.0.0.0", lsp_port):
            print("  [LSP] bridge listening on ws://0.0.0.0:{}".format(lsp_port))
            await asyncio.Future()

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_serve())
        except Exception as e:
            print("  [LSP] bridge error:", e)

    threading.Thread(target=_run, daemon=True).start()


def main():
    global ROOT
    port = int(os.environ.get("KENTSCRIPT_IDE_PORT", "8000"))
    ROOT = os.environ.get("KENTSCRIPT_IDE_ROOT", os.getcwd())

    for attempt in range(50):
        try:
            server = http.server.HTTPServer(("0.0.0.0", port + attempt), Handler)
            if attempt > 0:
                print("  Port {} busy, using {}...".format(port, port + attempt))
            print("")
            print("  KentScript IDE v3.1.0")
            print("  " + "-" * 38)
            print("  Open: http://localhost:{}".format(port + attempt))
            print("  Root: {}".format(os.path.abspath(ROOT)))
            bin_path = find_kentscript()
            if bin_path:
                print("  Binary: {}".format(bin_path))
            else:
                print("  Warning: kentscript binary not found")
            print("  Press Ctrl+C to stop")
            print("")
            start_lsp_bridge(port + attempt)
            server.serve_forever()
        except OSError as e:
            if "Address already in use" in str(e):
                continue
            raise
        except KeyboardInterrupt:
            print("\n  IDE stopped.")
            return
    print("  Could not find an available port.")

if __name__ == "__main__":
    main()
