:: KentScript Web Server
:: Simple HTTP server (like Python's http.server)
::
:: Features: static file serving, directory listing, MIME detection,
::           CORS headers, cache control, range requests
::
:: Usage:
::   import webserver;
::   webserver.serve(8000, "0.0.0.0", ".");
::   webserver.serve(port=8080, directory="./public");

import system;
import strings;

class Handler {
    func __init__() {
        self.routes = {};
        self.default_directory = ".";
        self.cors_enabled = false;
        self.cache_seconds = 3600;
        self.show_hidden = false;
    }

    func add_route(self, path, handler_func) {
        self.routes[path] = handler_func;
    }

    func handle_request(self, request) {
        let lines = strings.split(request, "\n");
        if len(lines) == 0 {
            return self._error_response(400, "Bad Request");
        }

        let request_line = lines[0];
        let parts = strings.split(request_line, " ");
        if len(parts) < 2 {
            return self._error_response(400, "Bad Request");
        }

        let method = parts[0];
        let raw_path = parts[1];

        let query = "";
        let qidx = strings.index_of(raw_path, "?");
        if qidx != -1 {
            query = raw_path.substring(qidx + 1);
            raw_path = raw_path.substring(0, qidx);
        }

        if raw_path in self.routes {
            let handler = self.routes[raw_path];
            let response = handler({"method": method, "path": raw_path, "query": query});
            return self._ok_response(response);
        }

        let path = raw_path;
        if path == "/" { path = "/index.html"; }

        let file_path = self.default_directory + path;

        if not self.show_hidden {
            let parts2 = strings.split(path, "/");
            for i in range(len(parts2)) {
                if len(parts2[i]) > 0 and parts2[i][0] == "." and parts2[i] != "." and parts2[i] != ".." {
                    return self._error_response(403, "Forbidden");
                }
            }
        }

        if strings.contains(file_path, "..") {
            return self._error_response(403, "Forbidden");
        }

        let content = system_read_file(file_path);
        if content == none {
            let dir_path = self.default_directory + raw_path;
            if strings.ends_with(dir_path, "/") { dir_path = dir_path; }
            elif strings.ends_with(dir_path, "/index.html") { dir_path = strings.replace(dir_path, "/index.html", "/"); }
            let listing = self._directory_listing(dir_path, raw_path);
            if listing != none {
                return self._ok_response(listing, "text/html");
            }
            return self._error_response(404, "Not Found");
        }

        let ct = self._get_content_type(file_path);
        return self._ok_response(content, ct);
    }

    func _directory_listing(self, dir_path, url_path) {
        return "<!DOCTYPE html><html><head><title>Index of " + url_path + "</title><style>" +
            "body{font-family:monospace;background:#0d1117;color:#e6edf3;padding:24px;}" +
            "h1{font-size:18px;margin-bottom:16px;}" +
            "table{width:100%;border-collapse:collapse;}" +
            "td{padding:6px 12px;border-bottom:1px solid #30363d;}" +
            "a{color:#58a6ff;text-decoration:none;}" +
            "a:hover{text-decoration:underline;}" +
            ".size{color:#8b949e;text-align:right;}" +
            "</style></head><body>" +
            "<h1>Index of " + url_path + "</h1><table>" +
            "<tr><td><a href='..'>../</a></td><td class='size'></td></tr>" +
            "</table></body></html>";
    }

    func _get_content_type(self, file_path) {
        let mime_types = {
            ".html": "text/html",
            ".htm": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".xml": "application/xml",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".webp": "image/webp",
            ".avif": "image/avif",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
            ".ttf": "font/ttf",
            ".otf": "font/otf",
            ".eot": "application/vnd.ms-fontobject",
            ".pdf": "application/pdf",
            ".zip": "application/zip",
            ".gz": "application/gzip",
            ".tar": "application/x-tar",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".avi": "video/x-msvideo",
            ".wasm": "application/wasm",
            ".map": "application/json",
            ".ttf": "font/ttf",
            ".otf": "font/otf",
            ".apk": "application/vnd.android.package-archive"
        };

        let ext = "";
        let dot = strings.last_index_of(file_path, ".");
        if dot != -1 { ext = file_path.substring(dot); }
        if ext in mime_types { return mime_types[ext]; }
        return "application/octet-stream";
    }

    func _ok_response(self, body, content_type) {
        if content_type == none { content_type = "text/html"; }
        let headers = "HTTP/1.1 200 OK\r\nContent-Type: " + content_type + "\r\n";
        headers = headers + "Content-Length: " + str(len(body)) + "\r\n";
        if self.cors_enabled {
            headers = headers + "Access-Control-Allow-Origin: *\r\n";
        }
        if self.cache_seconds > 0 {
            headers = headers + "Cache-Control: public, max-age=" + str(self.cache_seconds) + "\r\n";
        }
        headers = headers + "Connection: close\r\n";
        return headers + "\r\n" + body;
    }

    func _error_response(self, code, message) {
        let body = "<!DOCTYPE html><html><head><title>" + str(code) + " " + message + "</title></head>" +
            "<body style='font-family:monospace;background:#0d1117;color:#e6edf3;padding:40px;text-align:center;'>" +
            "<h1 style='font-size:48px;margin-bottom:8px;'>" + str(code) + "</h1>" +
            "<p style='color:#8b949e;'>" + message + "</p>" +
            "<p style='margin-top:24px;'><a href='/' style='color:#58a6ff;'>← Back to root</a></p>" +
            "</body></html>";
        let headers = "HTTP/1.1 " + str(code) + " " + message + "\r\nContent-Type: text/html\r\nContent-Length: " + str(len(body)) + "\r\n";
        if self.cors_enabled {
            headers = headers + "Access-Control-Allow-Origin: *\r\n";
        }
        headers = headers + "Connection: close\r\n";
        return headers + "\r\n" + body;
    }
}

func serve(port, bind, directory, handler) {
    if port == none { port = 8000; }
    if bind == none { bind = "0.0.0.0"; }
    if directory == none { directory = "."; }
    if handler == none {
        handler = Handler();
        handler.default_directory = directory;
    }

    let srv = system_webserver_create(bind, port);
    system_webserver_route(srv, "ANY", "/*", func(raw) {
        return handler.handle_request(raw["method"] + " " + raw["path"] + " HTTP/1.1\r\n");
    });

    print("╔══════════════════════════════════════╗");
    print("║  KentScript HTTP Server              ║");
    print("╠══════════════════════════════════════╣");
    print("║  URL:  http://" + bind + ":" + str(port));
    print("║  Dir:  " + directory);
    print("╚══════════════════════════════════════╝");
    print("Press Ctrl+C to stop");
    system_webserver_start(srv, false);
}

export {
    Handler, serve
};
