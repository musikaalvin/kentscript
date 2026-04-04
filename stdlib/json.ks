:: json - JSON encoding and decoding
:: Real implementation with full JSON support

:: ─── JSON Encoder ───────────────────────────────────────────────────────────

func dumps(obj, indent, sort_keys) {
    if indent == none {
        return _encode(obj, 0, false, sort_keys);
    } else {
        return _encode(obj, 0, true, sort_keys, indent);
    }
}

func _encode(obj, depth, pretty, sort_keys, indent_size) {
    if indent_size == none {
        indent_size = 2;
    }
    
    let t = typeof(obj);
    
    if obj == none || obj == null {
        return "null";
    } else if t == "boolean" {
        return obj ? "true" : "false";
    } else if t == "number" {
        if isNaN(obj) || !isFinite(obj) {
            return "null";
        }
        return str(obj);
    } else if t == "string" {
        return _encode_string(obj);
    } else if t == "array" {
        return _encode_array(obj, depth, pretty, sort_keys, indent_size);
    } else if t == "object" {
        return _encode_object(obj, depth, pretty, sort_keys, indent_size);
    } else {
        raise f"Object of type {t} is not JSON serializable";
    }
}

func _encode_string(s) {
    let result = '"';
    for i in 0..s.length {
        let char = s[i];
        if char == '"' {
            result = result + '\\"';
        } else if char == '\\' {
            result = result + '\\\\';
        } else if char == '\n' {
            result = result + '\\n';
        } else if char == '\r' {
            result = result + '\\r';
        } else if char == '\t' {
            result = result + '\\t';
        } else if char == '\b' {
            result = result + '\\b';
        } else if char == '\f' {
            result = result + '\\f';
        } else {
            result = result + char;
        }
    }
    return result + '"';
}

func _encode_array(arr, depth, pretty, sort_keys, indent_size) {
    if arr.length == 0 {
        return "[]";
    }
    
    let result = "[";
    let indent = pretty ? "\n" + " ".repeat((depth + 1) * indent_size) : "";
    let sep = pretty ? ",\n" + " ".repeat((depth + 1) * indent_size) : ",";
    
    if pretty {
        result = result + indent;
    }
    
    for i in 0..arr.length {
        if i > 0 {
            result = result + sep;
        }
        result = result + _encode(arr[i], depth + 1, pretty, sort_keys, indent_size);
    }
    
    if pretty {
        result = result + "\n" + " ".repeat(depth * indent_size);
    }
    
    return result + "]";
}

func _encode_object(obj, depth, pretty, sort_keys, indent_size) {
    let keys = Object.keys(obj);
    
    if keys.length == 0 {
        return "{}";
    }
    
    if sort_keys {
        keys.sort();
    }
    
    let result = "{";
    let indent = pretty ? "\n" + " ".repeat((depth + 1) * indent_size) : "";
    let sep = pretty ? ",\n" + " ".repeat((depth + 1) * indent_size) : ",";
    let colon = pretty ? ": " : ":";
    
    if pretty {
        result = result + indent;
    }
    
    let first = true;
    for key in keys {
        if !first {
            result = result + sep;
        }
        first = false;
        result = result + _encode_string(key) + colon + _encode(obj[key], depth + 1, pretty, sort_keys, indent_size);
    }
    
    if pretty {
        result = result + "\n" + " ".repeat(depth * indent_size);
    }
    
    return result + "}";
}

:: ─── JSON Decoder ───────────────────────────────────────────────────────────

func loads(s) {
    let parser = JSONParser(s);
    return parser.parse();
}

class JSONParser {
    func __init__(self, s) {
        self.s = s;
        self.pos = 0;
    }
    
    func parse(self) {
        self._skip_whitespace();
        let result = self._parse_value();
        self._skip_whitespace();
        if self.pos < self.s.length {
            raise f"Unexpected character at position {self.pos}";
        }
        return result;
    }
    
    func _parse_value(self) {
        self._skip_whitespace();
        
        if self.pos >= self.s.length {
            raise "Unexpected end of JSON";
        }
        
        let char = self.s[self.pos];
        
        if char == '"' {
            return self._parse_string();
        } else if char == '{' {
            return self._parse_object();
        } else if char == '[' {
            return self._parse_array();
        } else if char == 't' {
            return self._parse_true();
        } else if char == 'f' {
            return self._parse_false();
        } else if char == 'n' {
            return self._parse_null();
        } else if char == '-' || (char >= '0' && char <= '9') {
            return self._parse_number();
        } else {
            raise f"Unexpected character '{char}' at position {self.pos}";
        }
    }
    
    func _parse_string(self) {
        self.pos = self.pos + 1;  :: Skip opening quote
        let result = "";
        
        while self.pos < self.s.length {
            let char = self.s[self.pos];
            
            if char == '"' {
                self.pos = self.pos + 1;
                return result;
            } else if char == '\\' {
                self.pos = self.pos + 1;
                if self.pos >= self.s.length {
                    raise "Unterminated string";
                }
                
                let escape = self.s[self.pos];
                if escape == '"' {
                    result = result + '"';
                } else if escape == '\\' {
                    result = result + '\\';
                } else if escape == '/' {
                    result = result + '/';
                } else if escape == 'n' {
                    result = result + '\n';
                } else if escape == 'r' {
                    result = result + '\r';
                } else if escape == 't' {
                    result = result + '\t';
                } else if escape == 'b' {
                    result = result + '\b';
                } else if escape == 'f' {
                    result = result + '\f';
                } else if escape == 'u' {
                    :: Unicode escape
                    self.pos = self.pos + 1;
                    let hex = self.s.substring(self.pos, self.pos + 4);
                    result = result + String.fromCharCode(parseInt(hex, 16));
                    self.pos = self.pos + 3;
                } else {
                    raise f"Invalid escape sequence \\{escape}";
                }
                self.pos = self.pos + 1;
            } else {
                result = result + char;
                self.pos = self.pos + 1;
            }
        }
        
        raise "Unterminated string";
    }
    
    func _parse_number(self) {
        let start = self.pos;
        
        if self.s[self.pos] == '-' {
            self.pos = self.pos + 1;
        }
        
        if self.pos >= self.s.length || !(self.s[self.pos] >= '0' && self.s[self.pos] <= '9') {
            raise "Invalid number";
        }
        
        if self.s[self.pos] == '0' {
            self.pos = self.pos + 1;
        } else {
            while self.pos < self.s.length && self.s[self.pos] >= '0' && self.s[self.pos] <= '9' {
                self.pos = self.pos + 1;
            }
        }
        
        if self.pos < self.s.length && self.s[self.pos] == '.' {
            self.pos = self.pos + 1;
            while self.pos < self.s.length && self.s[self.pos] >= '0' && self.s[self.pos] <= '9' {
                self.pos = self.pos + 1;
            }
        }
        
        if self.pos < self.s.length && (self.s[self.pos] == 'e' || self.s[self.pos] == 'E') {
            self.pos = self.pos + 1;
            if self.pos < self.s.length && (self.s[self.pos] == '+' || self.s[self.pos] == '-') {
                self.pos = self.pos + 1;
            }
            while self.pos < self.s.length && self.s[self.pos] >= '0' && self.s[self.pos] <= '9' {
                self.pos = self.pos + 1;
            }
        }
        
        return parseFloat(self.s.substring(start, self.pos));
    }
    
    func _parse_object(self) {
        self.pos = self.pos + 1;  :: Skip {
        self._skip_whitespace();
        
        let obj = {};
        
        if self.pos < self.s.length && self.s[self.pos] == '}' {
            self.pos = self.pos + 1;
            return obj;
        }
        
        while true {
            self._skip_whitespace();
            
            if self.pos >= self.s.length || self.s[self.pos] != '"' {
                raise "Expected string key";
            }
            
            let key = self._parse_string();
            self._skip_whitespace();
            
            if self.pos >= self.s.length || self.s[self.pos] != ':' {
                raise "Expected ':'";
            }
            self.pos = self.pos + 1;
            
            let value = self._parse_value();
            obj[key] = value;
            
            self._skip_whitespace();
            
            if self.pos >= self.s.length {
                raise "Unterminated object";
            }
            
            if self.s[self.pos] == '}' {
                self.pos = self.pos + 1;
                return obj;
            } else if self.s[self.pos] == ',' {
                self.pos = self.pos + 1;
            } else {
                raise "Expected ',' or '}'";
            }
        }
    }
    
    func _parse_array(self) {
        self.pos = self.pos + 1;  :: Skip [
        self._skip_whitespace();
        
        let arr = [];
        
        if self.pos < self.s.length && self.s[self.pos] == ']' {
            self.pos = self.pos + 1;
            return arr;
        }
        
        while true {
            arr.push(self._parse_value());
            self._skip_whitespace();
            
            if self.pos >= self.s.length {
                raise "Unterminated array";
            }
            
            if self.s[self.pos] == ']' {
                self.pos = self.pos + 1;
                return arr;
            } else if self.s[self.pos] == ',' {
                self.pos = self.pos + 1;
            } else {
                raise "Expected ',' or ']'";
            }
        }
    }
    
    func _parse_true(self) {
        if self.s.substring(self.pos, self.pos + 4) == "true" {
            self.pos = self.pos + 4;
            return true;
        }
        raise "Invalid literal";
    }
    
    func _parse_false(self) {
        if self.s.substring(self.pos, self.pos + 5) == "false" {
            self.pos = self.pos + 5;
            return false;
        }
        raise "Invalid literal";
    }
    
    func _parse_null(self) {
        if self.s.substring(self.pos, self.pos + 4) == "null" {
            self.pos = self.pos + 4;
            return null;
        }
        raise "Invalid literal";
    }
    
    func _skip_whitespace(self) {
        while self.pos < self.s.length {
            let char = self.s[self.pos];
            if char == ' ' || char == '\t' || char == '\n' || char == '\r' {
                self.pos = self.pos + 1;
            } else {
                break;
            }
        }
    }
}

:: ─── File I/O ──────────────────────────────────────────────────────────────

func dump(obj, fp, indent, sort_keys) {
    let s = dumps(obj, indent, sort_keys);
    fp.write(s);
}

func load(fp) {
    let s = fp.read();
    return loads(s);
}

:: ─── Export ────────────────────────────────────────────────────────────────

export {
    dumps, loads, dump, load
};
