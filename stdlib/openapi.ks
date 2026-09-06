:: openapi - OpenAPI 3.0 spec generator from web.App routes
::
:: Generates full OpenAPI 3.0 specs with path parameters,
:: request/response schemas, security, and tags.
::
:: Usage:
::   import web, openapi;
::   let app = web.App();
::   app.get("/users/:id", func(req) {
::       return web.json({"id": req["params"]["id"]});
::   });
::   let spec = openapi.generate(app, {
::       "title": "My API",
::       "version": "1.0.0",
::       "description": "A sample API"
::   });
::   print(system_json_dumps(spec, 2));

:: ─── Schema inference ──────────────────────────────────────────────────────

func _infer_schema(value) {
    if value == none { return {"type": "string", "nullable": true}; }
    let t = type(value);
    if t == "int" { return {"type": "integer"}; }
    elif t == "float" { return {"type": "number"}; }
    elif t == "bool" { return {"type": "boolean"}; }
    elif t == "string" {
        let s = str(value);
        if len(s) == 0 { return {"type": "string"}; }
        if s.startswith("@") { return {"type": "string", "format": "email"}; }
        if s.startswith("http://") or s.startswith("https://") { return {"type": "string", "format": "uri"}; }
        if len(s) == 10 and s[4] == "-" and s[7] == "-" { return {"type": "string", "format": "date"}; }
        return {"type": "string"};
    }
    elif t == "list" {
        if len(value) == 0 { return {"type": "array", "items": {"type": "string"}}; }
        return {"type": "array", "items": _infer_schema(value[0])};
    }
    elif t == "dict" {
        let props = {};
        let required = [];
        for key in value {
            props[key] = _infer_schema(value[key]);
            required.push(key);
        }
        return {"type": "object", "properties": props, "required": required};
    }
    return {"type": "string"};
}

:: ─── Path parameter extraction ────────────────────────────────────────────

func _extract_path_params(path_pattern) {
    let params = {};
    let parts = path_pattern.split("/");
    for i in range(len(parts)) {
        if len(parts[i]) > 0 and parts[i][0] == ":" {
            let name = parts[i].substring(1);
            params[name] = {"type": "string", "description": "Path parameter: " + name};
        }
    }
    return params;
}

:: ─── HTTP method tags ─────────────────────────────────────────────────────

func _method_tag(method) {
    if method == "GET" { return "Read"; }
    elif method == "POST" { return "Create"; }
    elif method == "PUT" { return "Update"; }
    elif method == "DELETE" { return "Delete"; }
    elif method == "PATCH" { return "Patch"; }
    return "Other";
}

:: ─── Main generator ───────────────────────────────────────────────────────

func generate(app, info) {
    if info == none { info = {"title": "API", "version": "1.0.0"}; }

    let paths = {};
    let tags_used = {};

    for i in range(len(app._routes)) {
        let r = app._routes[i];
        let method = r["method"].lower();
        let path = r["path"];
        let tag = _method_tag(r["method"]);
        tags_used[tag] = true;

        let path_params = _extract_path_params(path);

        let op = {
            "summary": _generate_summary(r["method"], path),
            "tags": [tag],
            "parameters": [],
            "responses": {
                "200": {"description": "Success"},
                "400": {"description": "Bad Request"},
                "404": {"description": "Not Found"},
                "500": {"description": "Internal Server Error"}
            }
        };

        let param_names = {};
        for pname in path_params {
            op["parameters"].push({
                "name": pname,
                "in": "path",
                "required": true,
                "schema": {"type": "string"},
                "description": path_params[pname]["description"]
            });
            param_names[pname] = true;
        }

        if method == "get" or method == "delete" {
            op["parameters"].push({
                "name": "page",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 1},
                "description": "Page number"
            });
            op["parameters"].push({
                "name": "limit",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 20},
                "description": "Items per page"
            });
        }

        if method == "post" or method == "put" or method == "patch" {
            op["requestBody"] = {
                "required": true,
                "content": {
                    "application/json": {
                        "schema": {"type": "object"}
                    }
                }
            };
            op["responses"]["422"] = {"description": "Validation Error"};
        }

        if method == "delete" {
            op["responses"]["204"] = {"description": "Deleted"};
        }

        if not (path in paths) { paths[path] = {}; }
        paths[path][method] = op;
    }

    let tags = [];
    for tag in tags_used {
        tags.push({"name": tag, "description": "Operations for " + tag});
    }

    let spec = {
        "openapi": "3.0.0",
        "info": {
            "title": info["title"],
            "version": info["version"],
            "description": "description" in info ? info["description"] : ""
        },
        "servers": [
            {"url": "server" in info ? info["server"] : "http://localhost:8080", "description": "Development server"}
        ],
        "tags": tags,
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    };

    if "security" in info {
        spec["security"] = [info["security"]];
    }

    return spec;
}

func _generate_summary(method, path) {
    let resource = path;
    if resource.startswith("/") { resource = resource.substring(1); }
    let parts = resource.split("/");
    let name = "";
    for p in parts {
        if len(p) > 0 and p[0] != ":" {
            name = p;
            break;
        }
    }
    if name == "" { name = "resource"; }

    if method == "GET" {
        if path.contains(":") { return "Get " + name + " by ID"; }
        return "List " + name + "s";
    }
    elif method == "POST" { return "Create " + name; }
    elif method == "PUT" { return "Update " + name; }
    elif method == "PATCH" { return "Patch " + name; }
    elif method == "DELETE" { return "Delete " + name; }
    return method + " " + name;
}

:: ─── Helpers ───────────────────────────────────────────────────────────────

func spec_to_json(spec) {
    return system_json_dumps(spec, 2);
}

func spec_to_markdown(spec) {
    let md = "# " + spec["info"]["title"] + "\n\n";
    md = md + "Version: " + spec["info"]["version"] + "\n\n";
    if spec["info"]["description"] != "" {
        md = md + spec["info"]["description"] + "\n\n";
    }

    let tag_groups = {};
    for path in spec["paths"] {
        for method in spec["paths"][path] {
            let op = spec["paths"][path][method];
            let tag = "Other";
            if "tags" in op and len(op["tags"]) > 0 { tag = op["tags"][0]; }
            if not (tag in tag_groups) { tag_groups[tag] = []; }
            tag_groups[tag].push({"method": method.upper(), "path": path, "op": op});
        }
    }

    for tag in tag_groups {
        md = md + "## " + tag + "\n\n";
        let ops = tag_groups[tag];
        for op_entry in ops {
            md = md + "### " + op_entry["method"] + " `" + op_entry["path"] + "`\n\n";
            md = md + op_entry["op"]["summary"] + "\n\n";
            if "parameters" in op_entry["op"] and len(op_entry["op"]["parameters"]) > 0 {
                md = md + "**Parameters:**\n\n";
                md = md + "| Name | In | Required | Type | Description |\n";
                md = md + "|------|-----|----------|------|-------------|\n";
                for p in op_entry["op"]["parameters"] {
                    let req_str = p["required"] ? "Yes" : "No";
                    let ptype = "schema" in p ? p["schema"]["type"] : "string";
                    md = md + "| " + p["name"] + " | " + p["in"] + " | " + req_str + " | " + ptype + " | " + p["description"] + " |\n";
                }
                md = md + "\n";
            }
            md = md + "**Responses:**\n\n";
            for code in op_entry["op"]["responses"] {
                md = md + "- `" + code + "` " + op_entry["op"]["responses"][code]["description"] + "\n";
            }
            md = md + "\n---\n\n";
        }
    }

    return md;
}

export { generate, spec_to_json, spec_to_markdown, _infer_schema };
