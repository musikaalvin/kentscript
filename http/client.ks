# HTTP Client Module for KentScript

func http_get(url) {
    return system_http_request("GET", url, "", {});
}

func http_post(url, data) {
    return system_http_request("POST", url, data, {});
}

func http_put(url, data) {
    return system_http_request("PUT", url, data, {});
}

func http_delete(url) {
    return system_http_request("DELETE", url, "", {});
}
