:: http - HTTP client library
:: Real implementation with full request/response handling

:: ─── HTTP Client ────────────────────────────────────────────────────────────

class HTTPClient {
    func __init__(self, timeout, headers) {
        self.timeout = timeout != none ? timeout : 30;
        self.default_headers = headers != none ? headers : {};
        self.session = none;
    }
    
    func request(self, method, url, headers, data, json, params, timeout) {
        let req_headers = {...self.default_headers};
        if headers != none {
            for key in Object.keys(headers) {
                req_headers[key] = headers[key];
            }
        }
        
        :: Build URL with query params
        let full_url = url;
        if params != none {
            full_url = full_url + "?" + urlencode(params);
        }
        
        :: Prepare body
        let body = none;
        if json != none {
            body = JSON.stringify(json);
            req_headers["Content-Type"] = "application/json";
        } else if data != none {
            body = data;
        }
        
        :: Make request
        let response = http_request(method, full_url, req_headers, body, timeout != none ? timeout : self.timeout);
        
        return HTTPResponse(response);
    }
    
    func get(self, url, params, headers, timeout) {
        return self.request("GET", url, headers, none, none, params, timeout);
    }
    
    func post(self, url, data, json, headers, timeout) {
        return self.request("POST", url, headers, data, json, none, timeout);
    }
    
    func put(self, url, data, json, headers, timeout) {
        return self.request("PUT", url, headers, data, json, none, timeout);
    }
    
    func patch(self, url, data, json, headers, timeout) {
        return self.request("PATCH", url, headers, data, json, none, timeout);
    }
    
    func delete(self, url, headers, timeout) {
        return self.request("DELETE", url, headers, none, none, none, timeout);
    }
    
    func head(self, url, headers, timeout) {
        return self.request("HEAD", url, headers, none, none, none, timeout);
    }
    
    func options(self, url, headers, timeout) {
        return self.request("OPTIONS", url, headers, none, none, none, timeout);
    }
}

:: ─── HTTP Response ─────────────────────────────────────────────────────────

class HTTPResponse {
    func __init__(self, raw_response) {
        self.status_code = raw_response.status_code;
        self.headers = raw_response.headers;
        self.body = raw_response.body;
        self.url = raw_response.url;
        self.elapsed = raw_response.elapsed;
    }
    
    func text(self) {
        return self.body;
    }
    
    func json(self) {
        return JSON.parse(self.body);
    }
    
    func content(self) {
        return self.body.encode();
    }
    
    func ok(self) {
        return self.status_code >= 200 && self.status_code < 300;
    }
    
    func raise_for_status(self) {
        if !self.ok() {
            raise HTTPError(f"HTTP {self.status_code}: {self.body}");
        }
    }
}

:: ─── Convenience Functions ─────────────────────────────────────────────────

let _default_client = none;

func _get_client() {
    if _default_client == none {
        _default_client = HTTPClient();
    }
    return _default_client;
}

func get(url, params, headers, timeout) {
    return _get_client().get(url, params, headers, timeout);
}

func post(url, data, json, headers, timeout) {
    return _get_client().post(url, data, json, headers, timeout);
}

func put(url, data, json, headers, timeout) {
    return _get_client().put(url, data, json, headers, timeout);
}

func patch(url, data, json, headers, timeout) {
    return _get_client().patch(url, data, json, headers, timeout);
}

func delete(url, headers, timeout) {
    return _get_client().delete(url, headers, timeout);
}

func head(url, headers, timeout) {
    return _get_client().head(url, headers, timeout);
}

func options(url, headers, timeout) {
    return _get_client().options(url, headers, timeout);
}

func request(method, url, headers, data, json, params, timeout) {
    return _get_client().request(method, url, headers, data, json, params, timeout);
}

:: ─── URL Encoding ──────────────────────────────────────────────────────────

func urlencode(params) {
    let parts = [];
    for key in Object.keys(params) {
        let value = params[key];
        parts.push(encode_uri_component(key) + "=" + encode_uri_component(str(value)));
    }
    return parts.join("&");
}

func encode_uri_component(s) {
    :: Simple URL encoding
    let result = "";
    for i in 0..s.length {
        let char = s[i];
        let code = s.charCodeAt(i);
        
        if (code >= 48 && code <= 57) ||   :: 0-9
           (code >= 65 && code <= 90) ||   :: A-Z
           (code >= 97 && code <= 122) ||  :: a-z
           char == "-" || char == "_" || char == "." || char == "~" {
            result = result + char;
        } else {
            result = result + "%" + code.toString(16).toUpperCase();
        }
    }
    return result;
}

func parse_url(url) {
    :: Parse URL into components
    let result = {
        "scheme": "",
        "host": "",
        "port": none,
        "path": "",
        "query": "",
        "fragment": ""
    };
    
    :: Extract scheme
    let scheme_end = url.indexOf("://");
    if scheme_end != -1 {
        result.scheme = url.substring(0, scheme_end);
        url = url.substring(scheme_end + 3);
    }
    
    :: Extract fragment
    let fragment_start = url.indexOf("#");
    if fragment_start != -1 {
        result.fragment = url.substring(fragment_start + 1);
        url = url.substring(0, fragment_start);
    }
    
    :: Extract query
    let query_start = url.indexOf("?");
    if query_start != -1 {
        result.query = url.substring(query_start + 1);
        url = url.substring(0, query_start);
    }
    
    :: Extract path
    let path_start = url.indexOf("/");
    if path_start != -1 {
        result.path = url.substring(path_start);
        url = url.substring(0, path_start);
    }
    
    :: Extract host and port
    let port_start = url.indexOf(":");
    if port_start != -1 {
        result.host = url.substring(0, port_start);
        result.port = parseInt(url.substring(port_start + 1));
    } else {
        result.host = url;
    }
    
    return result;
}

:: ─── HTTP Server (Basic) ───────────────────────────────────────────────────

class HTTPServer {
    func __init__(self, host, port) {
        self.host = host != none ? host : "0.0.0.0";
        self.port = port != none ? port : 8000;
        self.routes = {};
    }
    
    func route(self, path, handler) {
        self.routes[path] = handler;
    }
    
    func get(self, path, handler) {
        self.routes["GET " + path] = handler;
    }
    
    func post(self, path, handler) {
        self.routes["POST " + path] = handler;
    }
    
    func serve_forever(self) {
        print(f"Starting server on {self.host}:{self.port}");
        http_serve(self.host, self.port, self.routes);
    }
}

:: ─── Status Codes ──────────────────────────────────────────────────────────

const HTTP_OK = 200;
const HTTP_CREATED = 201;
const HTTP_ACCEPTED = 202;
const HTTP_NO_CONTENT = 204;
const HTTP_MOVED_PERMANENTLY = 301;
const HTTP_FOUND = 302;
const HTTP_SEE_OTHER = 303;
const HTTP_NOT_MODIFIED = 304;
const HTTP_BAD_REQUEST = 400;
const HTTP_UNAUTHORIZED = 401;
const HTTP_FORBIDDEN = 403;
const HTTP_NOT_FOUND = 404;
const HTTP_METHOD_NOT_ALLOWED = 405;
const HTTP_CONFLICT = 409;
const HTTP_INTERNAL_SERVER_ERROR = 500;
const HTTP_NOT_IMPLEMENTED = 501;
const HTTP_BAD_GATEWAY = 502;
const HTTP_SERVICE_UNAVAILABLE = 503;

:: ─── Exceptions ────────────────────────────────────────────────────────────

class HTTPError {
    func __init__(self, message) {
        self.message = message;
    }
    
    func __str__(self) {
        return self.message;
    }
}

class ConnectionError extends HTTPError {}
class Timeout extends HTTPError {}

:: ─── Runtime Interface ─────────────────────────────────────────────────────

func http_request(method, url, headers, body, timeout) {
    :: Implemented by runtime
    return system_http_request(method, url, headers, body, timeout);
}

func http_serve(host, port, routes) {
    :: Implemented by runtime
    system_http_serve(host, port, routes);
}

:: ─── Export ────────────────────────────────────────────────────────────────

export {
    HTTPClient, HTTPResponse, HTTPServer,
    get, post, put, patch, delete, head, options, request,
    urlencode, parse_url,
    HTTPError, ConnectionError, Timeout,
    HTTP_OK, HTTP_CREATED, HTTP_BAD_REQUEST, HTTP_NOT_FOUND, HTTP_INTERNAL_SERVER_ERROR
};
