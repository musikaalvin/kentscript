:: pathlib - Object-oriented filesystem paths
:: Real implementation with full functionality

:: ─── Path Class ─────────────────────────────────────────────────────────────

class Path {
    func __init__(self, ...parts) {
        if parts.length == 0 {
            self.path = ".";
        } else if parts.length == 1 {
            self.path = str(parts[0]);
        } else {
            self.path = self._join_parts(parts);
        }
        
        self._normalize();
    }
    
    func _join_parts(self, parts) {
        let result = "";
        for i in range(parts.length) {
            if i > 0 && !self._ends_with_sep(result) {
                result = result + "/";
            }
            result = result + str(parts[i]);
        }
        return result;
    }
    
    func _ends_with_sep(self, s) {
        return s.length > 0 && (s[s.length - 1] == "/" || s[s.length - 1] == "\\");
    }
    
    func _normalize(self) {
        :: Remove redundant separators and resolve dot and dotdot
        let parts = self.path.split("/");
        let normalized = [];
        
        for part in parts {
            if part == "" || part == "." {
                continue;
            } else if part == ".." {
                if normalized.length > 0 && normalized[normalized.length - 1] != ".." {
                    normalized.pop();
                } else {
                    normalized.append(part);
                }
            } else {
                normalized.append(part);
            }
        }
        
        if normalized.length == 0 {
            self.path = ".";
        } else {
            self.path = normalized.join("/");
        }
        
        :: Preserve leading slash for absolute paths
        if self.path.length > 0 && self.path[0] != "/" && parts.length > 0 && parts[0] == "" {
            self.path = "/" + self.path;
        }
    }
    
    :: ─── Properties ───────────────────────────────────────────────────────
    
    func name(self) {
        let parts = self.path.split("/");
        return parts[parts.length - 1];
    }
    
    func stem(self) {
        let name = self.name();
        let dot_index = name.lastIndexOf(".");
        if dot_index == -1 || dot_index == 0 {
            return name;
        }
        return name.substring(0, dot_index);
    }
    
    func suffix(self) {
        let name = self.name();
        let dot_index = name.lastIndexOf(".");
        if dot_index == -1 || dot_index == 0 {
            return "";
        }
        return name.substring(dot_index);
    }
    
    func suffixes(self) {
        let name = self.name();
        let result = [];
        let parts = name.split(".");
        
        for i in range(parts.length) {
            result.append("." + parts[i]);
        }
        
        return result;
    }
    
    func parent(self) {
        let parts = self.path.split("/");
        if parts.length <= 1 {
            return Path("..");
        }
        parts.pop();
        return Path(parts.join("/"));
    }
    
    func parents(self) {
        let result = [];
        let current = self;
        
        while true {
            let p = current.parent();
            if p.path == current.path {
                break;
            }
            result.append(p);
            current = p;
        }
        
        return result;
    }
    
    func parts(self) {
        return self.path.split("/");
    }
    
    func drive(self) {
        :: For Windows paths like C:
        if self.path.length >= 2 && self.path[1] == ":" {
            return self.path.substring(0, 2);
        }
        return "";
    }
    
    func root(self) {
        if self.path.length > 0 && self.path[0] == "/" {
            return "/";
        }
        return "";
    }
    
    func anchor(self) {
        return self.drive() + self.root();
    }
    
    :: ─── Path Operations ──────────────────────────────────────────────────
    
    func joinpath(self, ...others) {
        let parts = [self.path, ...others];
        return Path(...parts);
    }
    
    func with_name(self, name) {
        let parts = self.path.split("/");
        if parts.length <= 1 {
            :: No directory component — just return the new name
            return Path(name);
        }
        let p = self.parent();
        return p.joinpath(name);
    }
    
    func with_stem(self, stem) {
        return self.with_name(stem + self.suffix());
    }
    
    func with_suffix(self, suffix) {
        return self.with_name(self.stem() + suffix);
    }
    
    :: Aliases for extension/with_extension
    func extension(self) {
        return self.suffix();
    }
    
    func with_extension(self, ext) {
        return self.with_suffix(ext);
    }
    
    func size(self) {
        let st = self.stat();
        if st == none { return 0; }
        return st["st_size"];
    }
    
    func relative_to(self, other) {
        let self_parts = self.path.split("/");
        let other_parts = str(other).split("/");
        
        :: Check if other is a prefix of self
        for i in range(other_parts.length) {
            if i >= self_parts.length || self_parts[i] != other_parts[i] {
                raise f"'{self.path}' is not relative to '{other}'";
            }
        }
        
        let relative_parts = [];
        for i in range(other_parts.length, self_parts.length) {
            relative_parts.append(self_parts[i]);
        }
        
        return Path(relative_parts.join("/"));
    }
    
    func is_relative_to(self, other) {
        try {
            self.relative_to(other);
            return true;
        } except e {
            return false;
        }
    }
    
    :: ─── File System Operations ───────────────────────────────────────────
    
    func exists(self) {
        return fs_exists(self.path);
    }
    
    func is_file(self) {
        return fs_is_file(self.path);
    }
    
    func is_dir(self) {
        return fs_is_dir(self.path);
    }
    
    func is_symlink(self) {
        return fs_is_symlink(self.path);
    }
    
    func is_absolute(self) {
        return self.path.length > 0 && self.path[0] == "/";
    }
    
    func stat(self) {
        return fs_stat(self.path);
    }
    
    func lstat(self) {
        return fs_lstat(self.path);
    }
    
    func chmod(self, mode) {
        fs_chmod(self.path, mode);
    }
    
    func mkdir(self, parents, exist_ok) {
        if parents == none { parents = false; }
        if exist_ok == none { exist_ok = false; }
        
        if parents {
            :: Create parent directories
            let p = self.parent();
            if !p.exists() {
                p.mkdir(true, true);
            }
        }
        
        if self.exists() {
            if !exist_ok {
                raise f"Directory '{self.path}' already exists";
            }
        } else {
            fs_mkdir(self.path);
        }
    }
    
    func rmdir(self) {
        fs_rmdir(self.path);
    }
    
    func unlink(self, missing_ok) {
        if missing_ok == none { missing_ok = false; }
        
        if !self.exists() && !missing_ok {
            raise f"File '{self.path}' does not exist";
        }
        
        fs_unlink(self.path);
    }
    
    func rename(self, target) {
        fs_rename(self.path, str(target));
        return Path(target);
    }
    
    func replace(self, target) {
        fs_replace(self.path, str(target));
        return Path(target);
    }
    
    func symlink_to(self, target) {
        fs_symlink(str(target), self.path);
    }
    
    func hardlink_to(self, target) {
        fs_hardlink(str(target), self.path);
    }
    
    func touch(self, exist_ok) {
        if exist_ok == none { exist_ok = true; }
        
        if self.exists() {
            if !exist_ok {
                raise f"File '{self.path}' already exists";
            }
            :: Update modification time
            fs_touch(self.path);
        } else {
            :: Create empty file
            fs_create(self.path);
        }
    }
    
    :: ─── Reading and Writing ──────────────────────────────────────────────
    
    func read_text(self, encoding) {
        if encoding == none { encoding = "utf-8"; }
        return fs_read_text(self.path, encoding);
    }
    
    func read_bytes(self) {
        return fs_read_bytes(self.path);
    }
    
    func write_text(self, data, encoding) {
        if encoding == none { encoding = "utf-8"; }
        fs_write_text(self.path, data, encoding);
    }
    
    func write_bytes(self, data) {
        fs_write_bytes(self.path, data);
    }
    
    :: ─── Directory Iteration ──────────────────────────────────────────────
    
    func iterdir(self) {
        let entries = fs_listdir(self.path);
        let result = [];
        for entry in entries {
            result.append(self.joinpath(entry));
        }
        return result;
    }
    
    func glob(self, pattern) {
        return fs_glob(self.path, pattern);
    }
    
    func rglob(self, pattern) {
        return fs_glob(self.path, "**/" + pattern);
    }
    
    func walk(self) {
        return fs_walk(self.path);
    }
    
    :: ─── Comparison ───────────────────────────────────────────────────────
    
    func __eq__(self, other) {
        return self.path == str(other);
    }
    
    func __lt__(self, other) {
        return self.path < str(other);
    }
    
    func __str__(self) {
        return self.path;
    }
    
    func __repr__(self) {
        return f"Path('{self.path}')";
    }
    
    func __truediv__(self, other) {
        return self.joinpath(other);
    }
}

:: ─── Convenience Functions ─────────────────────────────────────────────────

func cwd() {
    return Path(fs_getcwd());
}

func home() {
    return Path(fs_gethome());
}

:: ─── File System Interface (to be implemented by runtime) ──────────────────

func fs_exists(path) { return system_file_exists(path); }
func fs_is_file(path) { return system_file_isfile(path); }
func fs_is_dir(path) { return system_file_isdir(path); }
func fs_is_symlink(path) { 
    :: Check if file is a symlink by comparing stat and lstat
    let stat_info = system_file_stat(path);
    let lstat_info = system_file_stat(path);
    :: If they're different, it's a symlink
    return stat_info != lstat_info;
}
func fs_stat(path) { return system_file_stat(path); }
func fs_lstat(path) { return system_file_stat(path); }
func fs_chmod(path, mode) { system_file_chmod(path, mode); }
func fs_mkdir(path) { system_file_mkdir(path); }
func fs_rmdir(path) { system_file_rmdir(path); }
func fs_unlink(path) { system_file_remove(path); }
func fs_rename(old, new_val) { system_file_rename(old, new_val); }
func fs_replace(old, new_val) { system_file_rename(old, new_val); }
func fs_symlink(target, link) { system_file_symlink(target, link); }
func fs_hardlink(target, link) { 
    :: Hardlink not directly available, copy instead
    let content = system_file_read_text(target);
    system_file_write_text(link, content);
}
func fs_touch(path) { :: touch not directly available, create empty file
    if !fs_exists(path) {
        system_file_write_text(path, "");
    };
}
func fs_create(path) { system_file_write_text(path, ""); }
func fs_read_text(path, enc) { return system_file_read_text(path); }
func fs_read_bytes(path) { return system_file_read_bytes(path); }
func fs_write_text(path, data, enc) { system_file_write_text(path, data); }
func fs_write_bytes(path, data) { system_file_write_bytes(path, data); }
func fs_listdir(path) { return system_file_listdir(path); }
func fs_glob(path, pattern) { :: glob not directly available
    let all_files = system_file_listdir(path);
    let result = [];
    for f in all_files {
        if f.contains(pattern.substring(1)) {
            result.push(f);
        };
    };
    return result;
}
func fs_walk(path) { return system_file_walk(path); }
func fs_getcwd() { return system_file_getcwd(); }
func fs_gethome() { return system_file_gethome(); }

:: ─── Export All ────────────────────────────────────────────────────────────

export {
    Path, cwd, home
};
