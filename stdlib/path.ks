:: path - Path manipulation utilities

func join(...parts) {
    let result = "";
    for i in 0..parts.length {
        if i > 0 && !result.endsWith("/") {
            result = result + "/";
        }
        result = result + parts[i];
    }
    return normalize(result);
}

func split(path) {
    let last_slash = path.lastIndexOf("/");
    if last_slash == -1 {
        return ["", path];
    }
    return [path.substring(0, last_slash), path.substring(last_slash + 1)];
}

func dirname(path) {
    return split(path)[0];
}

func basename(path) {
    return split(path)[1];
}

func splitext(path) {
    let base = basename(path);
    let dot = base.lastIndexOf(".");
    if dot == -1 || dot == 0 {
        return [path, ""];
    }
    let ext_start = path.lastIndexOf(".");
    return [path.substring(0, ext_start), path.substring(ext_start)];
}

func normalize(path) {
    let parts = path.split("/");
    let result = [];
    
    for part in parts {
        if part == "" || part == "." {
            continue;
        } else if part == ".." {
            if result.length > 0 && result[result.length - 1] != ".." {
                result.pop();
            } else {
                result.push(part);
            }
        } else {
            result.push(part);
        }
    }
    
    let normalized = result.join("/");
    if path.startsWith("/") {
        normalized = "/" + normalized;
    }
    return normalized.length > 0 ? normalized : ".";
}

func abspath(path) {
    if isabs(path) {
        return normalize(path);
    }
    return normalize(join(getcwd(), path));
}

func relpath(path, start) {
    if start == none { start = getcwd(); }
    
    let abs_path = abspath(path);
    let abs_start = abspath(start);
    
    let path_parts = abs_path.split("/");
    let start_parts = abs_start.split("/");
    
    :: Find common prefix
    let common = 0;
    let min_len = min(path_parts.length, start_parts.length);
    for i in 0..min_len {
        if path_parts[i] == start_parts[i] {
            common = common + 1;
        } else {
            break;
        }
    }
    
    :: Build relative path
    let result = [];
    for i in common..start_parts.length {
        result.push("..");
    }
    for i in common..path_parts.length {
        result.push(path_parts[i]);
    }
    
    return result.length > 0 ? result.join("/") : ".";
}

func isabs(path) {
    return path.startsWith("/");
}

func exists(path) {
    return path_exists(path);
}

func isfile(path) {
    return path_isfile(path);
}

func isdir(path) {
    return path_isdir(path);
}

func islink(path) {
    return path_islink(path);
}

func getsize(path) {
    return path_getsize(path);
}

func getmtime(path) {
    return path_getmtime(path);
}

func getatime(path) {
    return path_getatime(path);
}

func getctime(path) {
    return path_getctime(path);
}

func expanduser(path) {
    if path.startsWith("~") {
        return path_home() + path.substring(1);
    }
    return path;
}

func expandvars(path) {
    let result = path;
    let env = path_environ();
    
    for key in Object.keys(env) {
        result = result.replace("$" + key, env[key]);
        result = result.replace("${" + key + "}", env[key]);
    }
    
    return result;
}

func min(a, b) {
    return a < b ? a : b;
}

func getcwd() {
    return path_getcwd();
}

:: Runtime interface
func path_exists(path) { return system_path_exists(path); }
func path_isfile(path) { return system_path_isfile(path); }
func path_isdir(path) { return system_path_isdir(path); }
func path_islink(path) { return system_path_islink(path); }
func path_getsize(path) { return system_path_getsize(path); }
func path_getmtime(path) { return system_path_getmtime(path); }
func path_getatime(path) { return system_path_getatime(path); }
func path_getctime(path) { return system_path_getctime(path); }
func path_home() { return system_path_home(); }
func path_environ() { return system_path_environ(); }
func path_getcwd() { return system_path_getcwd(); }

export {
    join, split, dirname, basename, splitext,
    normalize, abspath, relpath, isabs,
    exists, isfile, isdir, islink,
    getsize, getmtime, getatime, getctime,
    expanduser, expandvars
};
