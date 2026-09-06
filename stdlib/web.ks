:: web - Web framework
::
:: Usage:
::   import web;
::   let app = web.App();
::   app.get("/hello", func(req) {
::       return web.json({"message": "Hello"});
::   });
::   app.listen(8080);
::
:: Features: routing, path params, middleware, CORS, sessions,
::           file uploads, static serving, rate limiting, sub-routers

:: ─── Response helpers ──────────────────────────────────────────────────────

func json(data, status) {
    if status == none { status = 200; }
    return {"status": status, "body": system_json_dumps(data), "content_type": "application/json"};
}

func text(body, status) {
    if status == none { status = 200; }
    return {"status": status, "body": body, "content_type": "text/plain"};
}

func html(body, status) {
    if status == none { status = 200; }
    return {"status": status, "body": body, "content_type": "text/html"};
}

func redirect(url, status) {
    if status == none { status = 302; }
    return {"status": status, "body": "", "content_type": "text/plain", "headers": {"Location": url}};
}

func error(status, msg) {
    return {"status": status, "body": system_json_dumps({"error": msg}), "content_type": "application/json"};
}

func stream(body, content_type, status) {
    if status == none { status = 200; }
    if content_type == none { content_type = "application/octet-stream"; }
    return {"status": status, "body": body, "content_type": content_type};
}

:: ─── Request parsing ───────────────────────────────────────────────────────

func parse_query(path) {
    let query = {};
    let idx = path.find("?");
    if idx != -1 {
        let qs = path.substring(idx + 1);
        let pairs = qs.split("&");
        for i in range(len(pairs)) {
            let kv = pairs[i].split("=");
            if len(kv) == 2 {
                query[decode_uri(kv[0])] = decode_uri(kv[1]);
            } elif len(kv) == 1 {
                query[decode_uri(kv[0])] = "";
            }
        }
    }
    return query;
}

func _hex_val(c) {
    if c == "0" { return 0; }
    if c == "1" { return 1; }
    if c == "2" { return 2; }
    if c == "3" { return 3; }
    if c == "4" { return 4; }
    if c == "5" { return 5; }
    if c == "6" { return 6; }
    if c == "7" { return 7; }
    if c == "8" { return 8; }
    if c == "9" { return 9; }
    if c == "A" or c == "a" { return 10; }
    if c == "B" or c == "b" { return 11; }
    if c == "C" or c == "c" { return 12; }
    if c == "D" or c == "d" { return 13; }
    if c == "E" or c == "e" { return 14; }
    if c == "F" or c == "f" { return 15; }
    return 0;
}

func decode_uri(s) {
    let result = "";
    let i = 0;
    while i < len(s) {
        if s[i] == "%" and i + 2 < len(s) {
            let v1 = _hex_val(s[i + 1]);
            let v2 = _hex_val(s[i + 2]);
            result = result + chr(v1 * 16 + v2);
            i = i + 3;
        } elif s[i] == "+" {
            result = result + " ";
            i = i + 1;
        } else {
            result = result + s[i];
            i = i + 1;
        }
    }
    return result;
}

func encode_uri(s) {
    let result = "";
    let hex_chars = "0123456789ABCDEF";
    let i = 0;
    while i < len(s) {
        let c = s[i];
        if (c >= "A" and c <= "Z") or (c >= "a" and c <= "z") or (c >= "0" and c <= "9") or c == "-" or c == "_" or c == "." or c == "~" {
            result = result + c;
        } elif c == " " {
            result = result + "+";
        } else {
            let code = ord(c);
            let hi = hex_chars[code // 16];
            let lo = hex_chars[code % 16];
            result = result + "%" + hi + lo;
        }
        i = i + 1;
    }
    return result;
}

func parse_body(req) {
    let headers = req["headers"];
    let ct = "";
    if "Content-Type" in headers {
        ct = headers["Content-Type"];
    }
    if ct.contains("application/json") and req["body"] != "" {
        return system_json_loads(req["body"]);
    }
    if ct.contains("application/x-www-form-urlencoded") and req["body"] != "" {
        let form = {};
        let pairs = req["body"].split("&");
        for i in range(len(pairs)) {
            let kv = pairs[i].split("=");
            if len(kv) == 2 {
                form[decode_uri(kv[0])] = decode_uri(kv[1]);
            }
        }
        return form;
    }
    if ct.contains("multipart/form-data") and req["body"] != "" {
        return parse_multipart(req["body"], ct);
    }
    return none;
}

func parse_multipart(body, content_type) {
    let result = {};
    let boundary = "";
    let idx = content_type.find("boundary=");
    if idx != -1 {
        boundary = content_type.substring(idx + 9);
    }
    if boundary == "" { return result; }

    let parts = body.split("--" + boundary);
    for i in range(len(parts)) {
        let part = parts[i];
        if part == "" or part == "--" { continue; }
        let header_end = part.find("\r\n\r\n");
        if header_end == -1 { header_end = part.find("\n\n"); }
        if header_end == -1 { continue; }
        let headers = part.substring(0, header_end);
        let content = part.substring(header_end + 4);
        if content.length() > 2 {
            content = content.substring(0, content.length() - 2);
        }
        let name = "";
        let filename = "";
        let hlines = headers.split("\n");
        for j in range(len(hlines)) {
            let h = hlines[j];
            if h.contains("Content-Disposition") {
                let ni = h.find("name=\"");
                if ni != -1 {
                    let start = ni + 6;
                    let end = h.find("\"", start);
                    if end != -1 { name = h.substring(start, end); }
                }
                let fi = h.find("filename=\"");
                if fi != -1 {
                    let start = fi + 10;
                    let end = h.find("\"", start);
                    if end != -1 { filename = h.substring(start, end); }
                }
            }
        }
        if name != "" {
            if filename != "" {
                result[name] = {"filename": filename, "content": content, "size": len(content)};
            } else {
                result[name] = content;
            }
        }
    }
    return result;
}

func parse_cookies(req) {
    let cookies = {};
    let headers = req["headers"];
    if "Cookie" in headers {
        let raw = headers["Cookie"];
        let pairs = raw.split(";");
        for i in range(len(pairs)) {
            let kv = pairs[i].trim().split("=");
            if len(kv) == 2 {
                cookies[kv[0].trim()] = kv[1].trim();
            }
        }
    }
    return cookies;
}

func clean_path(raw) {
    let idx = raw.find("?");
    if idx != -1 { return raw.substring(0, idx); }
    return raw;
}

:: ─── Path parameter matching ───────────────────────────────────────────────

func _match_route(pattern, actual) {
    let pattern_parts = pattern.split("/");
    let actual_parts = actual.split("/");
    if len(pattern_parts) != len(actual_parts) { return none; }
    let params = {};
    for i in range(len(pattern_parts)) {
        let pp = pattern_parts[i];
        let ap = actual_parts[i];
        if pp.length() > 0 and pp[0] == ":" {
            params[pp.substring(1)] = ap;
        } elif pp != ap {
            return none;
        }
    }
    return params;
}

:: ─── CORS middleware ───────────────────────────────────────────────────────

func cors_middleware(opts) {
    if opts == none { opts = {}; }
    let allow_origin = "*";
    let allow_methods = "GET, POST, PUT, DELETE, PATCH, OPTIONS";
    let allow_headers = "Content-Type, Authorization, X-Requested-With";
    let max_age = "86400";
    if "origin" in opts { allow_origin = opts["origin"]; }
    if "methods" in opts { allow_methods = opts["methods"]; }
    if "headers" in opts { allow_headers = opts["headers"]; }
    if "max_age" in opts { max_age = str(opts["max_age"]); }

    return func(req) {
        if req["method"] == "OPTIONS" {
            return {"__cors_preflight": true, "headers": {
                "Access-Control-Allow-Origin": allow_origin,
                "Access-Control-Allow-Methods": allow_methods,
                "Access-Control-Allow-Headers": allow_headers,
                "Access-Control-Max-Age": max_age
            }};
        }
        return true;
    };
}

:: ─── Rate limiter ──────────────────────────────────────────────────────────

func rate_limiter(opts) {
    if opts == none { opts = {}; }
    let max_requests = 100;
    let window_seconds = 60;
    if "max" in opts { max_requests = opts["max"]; }
    if "window" in opts { window_seconds = opts["window"]; }
    let clients = {};

    return func(req) {
        let ip = "unknown";
        if "X-Forwarded-For" in req["headers"] {
            ip = req["headers"]["X-Forwarded-For"];
        }
        let now = system_time();
        if not (ip in clients) { clients[ip] = []; }
        let timestamps = clients[ip];
        let clean = [];
        for i in range(len(timestamps)) {
            if now - timestamps[i] < window_seconds {
                clean.push(timestamps[i]);
            }
        }
        clients[ip] = clean;
        if len(clean) >= max_requests {
            return {"__rate_limited": true, "retry_after": window_seconds};
        }
        clean.push(now);
        return true;
    };
}

:: ─── Static file serving middleware ────────────────────────────────────────

func static_files(url_prefix, directory) {
    if url_prefix == none { url_prefix = "/static"; }
    if directory == none { directory = "."; }

    let mime_types = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".pdf": "application/pdf",
        ".zip": "application/zip",
        ".txt": "text/plain",
        ".xml": "application/xml",
        ".mp3": "audio/mpeg",
        ".mp4": "video/mp4",
        ".webm": "video/webm"
    };

    return func(req) {
        let path = req["clean_path"];
        if not path.startswith(url_prefix + "/") { return true; }
        let file_path = path.substring(len(url_prefix));
        if file_path == "" { file_path = "/index.html"; }
        if file_path.contains("..") { return error(403, "Forbidden"); }
        let ext = ".";
        let dot = file_path.rfind(".");
        if dot != -1 { ext = file_path.substring(dot); }
        let mime = "text/plain";
        if ext in mime_types { mime = mime_types[ext]; }
        try {
            let f = open(directory + file_path, "r");
            let content = f.read();
            f.close();
            return {"status": 200, "body": content, "content_type": mime};
        } catch(e) {
            return error(404, "Not found: " + file_path);
        }
    };
}

:: ─── Session store ─────────────────────────────────────────────────────────

class SessionStore {
    func __init__(self, secret) {
        self._sessions = {};
        self._secret = "default_secret";
        if secret != none { self._secret = secret; }
    }

    func get(self, sid) {
        if sid in self._sessions {
            let s = self._sessions[sid];
            if system_time() - s["_created"] < 3600 {
                return s;
            }
            del self._sessions[sid];
        }
        return {};
    }

    func create(self) {
        let sid = str(system_time()) + str(len(self._sessions));
        self._sessions[sid] = {"_created": system_time()};
        return sid;
    }

    func set(self, sid, key, value) {
        if sid not in self._sessions {
            self._sessions[sid] = {"_created": system_time()};
        }
        self._sessions[sid][key] = value;
    }

    func destroy(self, sid) {
        if sid in self._sessions {
            del self._sessions[sid];
        }
    }
}

:: ─── App ───────────────────────────────────────────────────────────────────

class App {
    func __init__(self) {
        self._routes = [];
        self._middleware = [];
        self._sessions = none;
        self._not_found_handler = none;
    }

    func use(self, fn) {
        self._middleware.push(fn);
    }

    func _add_route(self, method, path, handler) {
        self._routes.push({"method": method, "path": path, "handler": handler});
    }

    func get(self, path, handler) { self._add_route("GET", path, handler); }
    func post(self, path, handler) { self._add_route("POST", path, handler); }
    func put(self, path, handler) { self._add_route("PUT", path, handler); }
    func delete(self, path, handler) { self._add_route("DELETE", path, handler); }
    func patch(self, path, handler) { self._add_route("PATCH", path, handler); }
    func options(self, path, handler) { self._add_route("OPTIONS", path, handler); }
    func head(self, path, handler) { self._add_route("HEAD", path, handler); }
    func any(self, path, handler) { self._add_route("ANY", path, handler); }

    func on_not_found(self, handler) {
        self._not_found_handler = handler;
    }

    func enable_sessions(self, secret) {
        self._sessions = SessionStore(secret);
    }

    func _find_handler(self, method, path) {
        for i in range(len(self._routes)) {
            let r = self._routes[i];
            if r["method"] == method or r["method"] == "ANY" {
                let params = _match_route(r["path"], path);
                if params != none {
                    return {"handler": r["handler"], "params": params};
                }
            }
        }
        return none;
    }

    func _handle(self, raw) {
        let req = raw;
        if not ("query" in req) { req["query"] = {}; }
        req["parsed_body"] = parse_body(req);
        req["clean_path"] = clean_path(req["path"]);
        req["cookies"] = parse_cookies(req);
        req["params"] = {};

        if self._sessions != none {
            let sid = "";
            if "ks_session" in req["cookies"] {
                sid = req["cookies"]["ks_session"];
            }
            req["session"] = self._sessions.get(sid);
            if sid == "" or req["session"] == {} {
                sid = self._sessions.create();
                req["session_id"] = sid;
                req["session"] = self._sessions.get(sid);
            } else {
                req["session_id"] = sid;
            }
        }

        for i in range(len(self._middleware)) {
            let mw = self._middleware[i];
            let result = mw(req);
            if result == false {
                return error(403, "Forbidden");
            }
            if type(result) == "dict" {
                if "__cors_preflight" in result {
                    let resp = {"status": 204, "body": "", "content_type": "text/plain"};
                    if "headers" in result { resp["headers"] = result["headers"]; }
                    return resp;
                }
                if "__rate_limited" in result {
                    let resp = error(429, "Too many requests");
                    resp["headers"] = {"Retry-After": str(result["retry_after"])};
                    return resp;
                }
            }
        }

        let found = self._find_handler(req["method"], req["clean_path"]);
        if found == none {
            if self._not_found_handler != none {
                return self._not_found_handler(req);
            }
            return error(404, "Not found: " + req["clean_path"]);
        }
        req["params"] = found["params"];
        let resp = found["handler"](req);

        if self._sessions != none {
            if "session_id" in req {
                if not ("headers" in resp) { resp["headers"] = {}; }
                resp["headers"]["Set-Cookie"] = "ks_session=" + req["session_id"] + "; Path=/; HttpOnly";
            }
        }
        return resp;
    }

    func mount(self, prefix, sub_app) {
        for i in range(len(sub_app._routes)) {
            let r = sub_app._routes[i];
            let full_path = prefix + r["path"];
            self._add_route(r["method"], full_path, r["handler"]);
        }
    }

    func listen(self, port, host) {
        if port == none { port = 8080; }
        if host == none { host = "0.0.0.0"; }
        let srv = system_webserver_create(host, port);
        for i in range(len(self._routes)) {
            let r = self._routes[i];
            system_webserver_route(srv, r["method"], r["path"], func(raw) {
                return self._handle(raw);
            });
        }
        print("Listening on http://" + host + ":" + str(port));
        system_webserver_start(srv, false);
    }
}

:: ─── Router (sub-router for grouping) ─────────────────────────────────────

class Router {
    func __init__() {
        self._routes = [];
    }

    func get(self, path, handler) { self._routes.push({"method": "GET", "path": path, "handler": handler}); }
    func post(self, path, handler) { self._routes.push({"method": "POST", "path": path, "handler": handler}); }
    func put(self, path, handler) { self._routes.push({"method": "PUT", "path": path, "handler": handler}); }
    func delete(self, path, handler) { self._routes.push({"method": "DELETE", "path": path, "handler": handler}); }
    func patch(self, path, handler) { self._routes.push({"method": "PATCH", "path": path, "handler": handler}); }
    func any(self, path, handler) { self._routes.push({"method": "ANY", "path": path, "handler": handler}); }
}

export {
    App, Router, SessionStore,
    json, text, html, stream, redirect, error,
    cors_middleware, rate_limiter, static_files,
    parse_query, decode_uri, encode_uri, parse_body, parse_cookies, parse_multipart,
    clean_path, _match_route
};
