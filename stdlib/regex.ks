:: regex - Regular expression support
:: Pattern matching and text processing

class Regex {
    func __init__(self, pattern, flags) {
        self.pattern = pattern;
        self.flags = flags != none ? flags : "";
        self.compiled = regex_compile(pattern, flags);
    }
    
    func match(self, text, pos) {
        if pos == none { pos = 0; }
        return regex_match(self.compiled, text, pos);
    }
    
    func search(self, text, pos) {
        if pos == none { pos = 0; }
        return regex_search(self.compiled, text, pos);
    }
    
    func findall(self, text) {
        return regex_findall(self.compiled, text);
    }
    
    func finditer(self, text) {
        return regex_finditer(self.compiled, text);
    }
    
    func sub(self, repl, text, count) {
        if count == none { count = 0; }
        return regex_sub(self.compiled, repl, text, count);
    }
    
    func split(self, text, maxsplit) {
        if maxsplit == none { maxsplit = 0; }
        return regex_split(self.compiled, text, maxsplit);
    }
}

class Match {
    func __init__(self, text, start, end, groups) {
        self.text = text;
        self.start_pos = start;
        self.end_pos = end;
        self.groups_data = groups;
    }
    
    func group(self, n) {
        if n == none { n = 0; }
        return self.groups_data[n];
    }
    
    func groups(self) {
        return self.groups_data.slice(1);
    }
    
    func start(self, n) {
        if n == none { n = 0; }
        return self.start_pos;
    }
    
    func end(self, n) {
        if n == none { n = 0; }
        return self.end_pos;
    }
    
    func span(self, n) {
        return [self.start(n), self.end(n)];
    }
}

func compile(pattern, flags) {
    return Regex(pattern, flags);
}

func match(pattern, text, flags) {
    let r = Regex(pattern, flags);
    return r.match(text);
}

func search(pattern, text, flags) {
    let r = Regex(pattern, flags);
    return r.search(text);
}

func findall(pattern, text, flags) {
    let r = Regex(pattern, flags);
    return r.findall(text);
}

func finditer(pattern, text, flags) {
    let r = Regex(pattern, flags);
    return r.finditer(text);
}

func sub(pattern, repl, text, count, flags) {
    let r = Regex(pattern, flags);
    return r.sub(repl, text, count);
}

func split(pattern, text, maxsplit, flags) {
    let r = Regex(pattern, flags);
    return r.split(text, maxsplit);
}

func escape(s) {
    let special = "\\^$.|?*+()[]{}";
    let result = "";
    for i in 0..s.length {
        if special.indexOf(s[i]) != -1 {
            result = result + "\\" + s[i];
        } else {
            result = result + s[i];
        }
    }
    return result;
}

:: Runtime interface
func regex_compile(pattern, flags) { return system_regex_compile(pattern, flags); }
func regex_match(compiled, text, pos) { return system_regex_match(compiled, text, pos); }
func regex_search(compiled, text, pos) { return system_regex_search(compiled, text, pos); }
func regex_findall(compiled, text) { return system_regex_findall(compiled, text); }
func regex_finditer(compiled, text) { return system_regex_finditer(compiled, text); }
func regex_sub(compiled, repl, text, count) { return system_regex_sub(compiled, repl, text, count); }
func regex_split(compiled, text, maxsplit) { return system_regex_split(compiled, text, maxsplit); }

export {
    Regex, Match,
    compile, match, search, findall, finditer, sub, split, escape
};
