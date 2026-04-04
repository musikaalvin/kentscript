:: KentScript Web Server
:: Simple HTTP server (like Python's http.server)
::
:: Usage:
::   import webserver;
::   webserver.serve();
::   webserver.serve(port=8080, directory=".");

import system;
import strings;

class Handler {
    func __init__(self) {
        self.routes = {};
        self.default_directory = ".";
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
        let path = parts[1];

        if path in self.routes {
            let handler = self.routes[path];
            let response = handler({"method": method, "path": path});
            return self._ok_response(response);
        }

        return self._serve_static(path);
    }

    func _serve_static(self, path) {
        if path == "/" {
            path = "/index.html";
        }

        let file_path = self.default_directory + path;

        if strings.contains(file_path, "..") {
            return self._error_response(403, "Forbidden");
        }

        return self._error_response(404, "Not Found");
    }

    func _get_content_type(self, file_path) {
        if strings.ends_with(file_path, ".html") {
            return "text/html";
        } elif strings.ends_with(file_path, ".css") {
            return "text/css";
        } elif strings.ends_with(file_path, ".js") {
            return "application/javascript";
        } elif strings.ends_with(file_path, ".json") {
            return "application/json";
        } else {
            return "text/plain";
        }
    }

    func _ok_response(self, body, content_type) {
        if content_type == none { content_type = "text/html"; }
        return "HTTP/1.1 200 OK\r\nContent-Type: " + content_type + "\r\n\r\n" + body;
    }

    func _error_response(self, code, message) {
        let body = "<html><body><h1>" + str(code) + " " + message + "</h1></body></html>";
        return "HTTP/1.1 " + str(code) + " " + message + "\r\nContent-Type: text/html\r\n\r\n" + body;
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

    print("Starting KentScript HTTP server on http://" + bind + ":" + str(port));
    print("Serving directory: " + directory);
    print("Press Ctrl+C to stop");
}

export {
    Handler, serve
};
