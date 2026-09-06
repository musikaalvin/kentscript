:: strings - String manipulation utilities
:: Real implementation with full functionality

:: ─── Basic String Operations ───────────────────────────────────────────────

func split(s, delimiter, maxsplit) {
    if delimiter == none {
        delimiter = " ";
    }
    
    let result = [];
    let current = "";
    let splits = 0;
    let i = 0;
    
    while i < s.length {
        if maxsplit != none && splits >= maxsplit {
            current = current + s.substring(i);
            break;
        }
        
        let is_match = true;
        for j in 0..delimiter.length {
            if i + j >= s.length || s[i + j] != delimiter[j] {
                is_match = false;
                break;
            }
        }
        
        if is_match {
            result.push(current);
            current = "";
            i = i + delimiter.length;
            splits = splits + 1;
        } else {
            current = current + s[i];
            i = i + 1;
        }
    }
    
    if current.length > 0 || splits > 0 {
        result.push(current);
    }
    
    return result;
}

func join(separator, iterable) {
    let result = "";
    let first = true;
    
    for item in iterable {
        if !first {
            result = result + separator;
        }
        result = result + str(item);
        first = false;
    }
    
    return result;
}

func strip(s, chars) {
    if chars == none {
        chars = " \t\n\r";
    }
    
    let start = 0;
    let end = s.length;
    
    while start < end {
        let found = false;
        for c in chars {
            if s[start] == c {
                found = true;
                break;
            }
        }
        if !found { break; }
        start = start + 1;
    }
    
    while end > start {
        let found = false;
        for c in chars {
            if s[end - 1] == c {
                found = true;
                break;
            }
        }
        if !found { break; }
        end = end - 1;
    }
    
    return s.substring(start, end);
}

func lstrip(s, chars) {
    if chars == none {
        chars = " \t\n\r";
    }
    
    let start = 0;
    while start < s.length {
        let found = false;
        for c in chars {
            if s[start] == c {
                found = true;
                break;
            }
        }
        if !found { break; }
        start = start + 1;
    }
    
    return s.substring(start);
}

func rstrip(s, chars) {
    if chars == none {
        chars = " \t\n\r";
    }
    
    let end = s.length;
    while end > 0 {
        let found = false;
        for c in chars {
            if s[end - 1] == c {
                found = true;
                break;
            }
        }
        if !found { break; }
        end = end - 1;
    }
    
    return s.substring(0, end);
}

func replace(s, old, new_val, count) {
    let result = "";
    let i = 0;
    let replacements = 0;
    
    while i < s.length {
        if count != none && replacements >= count {
            result = result + s.substring(i);
            break;
        }
        
        let is_match = true;
        for j in 0..old.length {
            if i + j >= s.length || s[i + j] != old[j] {
                is_match = false;
                break;
            }
        }
        
        if is_match {
            result = result + new;
            i = i + old.length;
            replacements = replacements + 1;
        } else {
            result = result + s[i];
            i = i + 1;
        }
    }
    
    return result;
}

func upper(s) {
    let result = "";
    for i in 0..s.length {
        let code = s.charCodeAt(i);
        if code >= 97 && code <= 122 {
            result = result + String.fromCharCode(code - 32);
        } else {
            result = result + s[i];
        }
    }
    return result;
}

func lower(s) {
    let result = "";
    for i in 0..s.length {
        let code = s.charCodeAt(i);
        if code >= 65 && code <= 90 {
            result = result + String.fromCharCode(code + 32);
        } else {
            result = result + s[i];
        }
    }
    return result;
}

func capitalize(s) {
    if s.length == 0 {
        return s;
    }
    return upper(s.substring(0, 1)) + lower(s.substring(1));
}

func title(s) {
    let result = "";
    let capitalize_next = true;
    
    for i in 0..s.length {
        let char = s[i];
        if char == " " || char == "\t" || char == "\n" {
            result = result + char;
            capitalize_next = true;
        } else if capitalize_next {
            result = result + upper(char);
            capitalize_next = false;
        } else {
            result = result + lower(char);
        }
    }
    
    return result;
}

func swapcase(s) {
    let result = "";
    for i in 0..s.length {
        let code = s.charCodeAt(i);
        if code >= 65 && code <= 90 {
            result = result + String.fromCharCode(code + 32);
        } else if code >= 97 && code <= 122 {
            result = result + String.fromCharCode(code - 32);
        } else {
            result = result + s[i];
        }
    }
    return result;
}

:: ─── String Testing ────────────────────────────────────────────────────────

func startswith(s, prefix) {
    if prefix.length > s.length {
        return false;
    }
    for i in 0..prefix.length {
        if s[i] != prefix[i] {
            return false;
        }
    }
    return true;
}

func endswith(s, suffix) {
    if suffix.length > s.length {
        return false;
    }
    let offset = s.length - suffix.length;
    for i in 0..suffix.length {
        if s[offset + i] != suffix[i] {
            return false;
        }
    }
    return true;
}

func contains(s, substring) {
    return find(s, substring) != -1;
}

func isalpha(s) {
    if s.length == 0 { return false; }
    for i in 0..s.length {
        let code = s.charCodeAt(i);
        if !((code >= 65 && code <= 90) || (code >= 97 && code <= 122)) {
            return false;
        }
    }
    return true;
}

func isdigit(s) {
    if s.length == 0 { return false; }
    for i in 0..s.length {
        let code = s.charCodeAt(i);
        if !(code >= 48 && code <= 57) {
            return false;
        }
    }
    return true;
}

func isalnum(s) {
    if s.length == 0 { return false; }
    for i in 0..s.length {
        let code = s.charCodeAt(i);
        if !((code >= 48 && code <= 57) || (code >= 65 && code <= 90) || (code >= 97 && code <= 122)) {
            return false;
        }
    }
    return true;
}

func isspace(s) {
    if s.length == 0 { return false; }
    for i in 0..s.length {
        let char = s[i];
        if char != " " && char != "\t" && char != "\n" && char != "\r" {
            return false;
        }
    }
    return true;
}

func isupper(s) {
    let has_cased = false;
    for i in 0..s.length {
        let code = s.charCodeAt(i);
        if code >= 97 && code <= 122 {
            return false;
        }
        if code >= 65 && code <= 90 {
            has_cased = true;
        }
    }
    return has_cased;
}

func islower(s) {
    let has_cased = false;
    for i in 0..s.length {
        let code = s.charCodeAt(i);
        if code >= 65 && code <= 90 {
            return false;
        }
        if code >= 97 && code <= 122 {
            has_cased = true;
        }
    }
    return has_cased;
}

:: ─── String Formatting ─────────────────────────────────────────────────────

func format(template, ...args) {
    let result = template;
    
    for i in 0..args.length {
        let placeholder = "{" + str(i) + "}";
        result = replace(result, placeholder, str(args[i]));
    }
    
    return result;
}

func center(s, width, fillchar) {
    if fillchar == none {
        fillchar = " ";
    }
    
    if s.length >= width {
        return s;
    }
    
    let total_padding = width - s.length;
    let left_padding = total_padding / 2;
    let right_padding = total_padding - left_padding;
    
    return repeat_char(fillchar, left_padding) + s + repeat_char(fillchar, right_padding);
}

func ljust(s, width, fillchar) {
    if fillchar == none {
        fillchar = " ";
    }
    
    if s.length >= width {
        return s;
    }
    
    return s + repeat_char(fillchar, width - s.length);
}

func rjust(s, width, fillchar) {
    if fillchar == none {
        fillchar = " ";
    }
    
    if s.length >= width {
        return s;
    }
    
    return repeat_char(fillchar, width - s.length) + s;
}

func zfill(s, width) {
    if s.length >= width {
        return s;
    }
    
    let sign = "";
    let start = 0;
    
    if s.length > 0 && (s[0] == "+" || s[0] == "-") {
        sign = s[0];
        start = 1;
    }
    
    return sign + repeat_char("0", width - s.length) + s.substring(start);
}

func repeat_char(char, count) {
    let result = "";
    for i in 0..count {
        result = result + char;
    }
    return result;
}

:: ─── String Searching ──────────────────────────────────────────────────────

func find(s, substring) {
    for i in 0..(s.length - substring.length + 1) {
        let is_match = true;
        for j in 0..substring.length {
            if s[i + j] != substring[j] {
                is_match = false;
                break;
            }
        }
        if is_match {
            return i;
        }
    }
    return -1;
}

func rfind(s, substring) {
    for i in range(s.length - substring.length, -1, -1) {
        let is_match = true;
        for j in 0..substring.length {
            if s[i + j] != substring[j] {
                is_match = false;
                break;
            }
        }
        if is_match {
            return i;
        }
    }
    return -1;
}

func count(s, substring) {
    let count = 0;
    let i = 0;
    
    while i <= s.length - substring.length {
        let is_match = true;
        for j in 0..substring.length {
            if s[i + j] != substring[j] {
                is_match = false;
                break;
            }
        }
        if is_match {
            count = count + 1;
            i = i + substring.length;
        } else {
            i = i + 1;
        }
    }
    
    return count;
}

:: ─── String Partitioning ───────────────────────────────────────────────────

func partition(s, separator) {
    let pos = find(s, separator);
    if pos == -1 {
        return [s, "", ""];
    }
    return [s.substring(0, pos), separator, s.substring(pos + separator.length)];
}

func rpartition(s, separator) {
    let pos = rfind(s, separator);
    if pos == -1 {
        return ["", "", s];
    }
    return [s.substring(0, pos), separator, s.substring(pos + separator.length)];
}

func splitlines(s) {
    let result = [];
    let current = "";
    
    for i in 0..s.length {
        let char = s[i];
        
        if char == "\n" {
            result.push(current);
            current = "";
        } else if char == "\r" {
            result.push(current);
            current = "";
            if i + 1 < s.length && s[i + 1] == "\n" {
                i = i + 1;
            }
        } else {
            current = current + char;
        }
    }
    
    if current.length > 0 {
        result.push(current);
    }
    
    return result;
}

:: ─── String Utilities ──────────────────────────────────────────────────────

func reverse(s) {
    let result = "";
    for i in range(s.length - 1, -1, -1) {
        result = result + s[i];
    }
    return result;
}

func remove_prefix(s, prefix) {
    if startswith(s, prefix) {
        return s.substring(prefix.length);
    }
    return s;
}

func remove_suffix(s, suffix) {
    if endswith(s, suffix) {
        return s.substring(0, s.length - suffix.length);
    }
    return s;
}

func truncate(s, length, suffix) {
    if suffix == none {
        suffix = "...";
    }
    
    if s.length <= length {
        return s;
    }
    
    return s.substring(0, length - suffix.length) + suffix;
}

func wrap(s, width) {
    let lines = [];
    let words = split(s, " ");
    let current_line = "";
    
    for word in words {
        if current_line.length + word.length + 1 <= width {
            if current_line.length > 0 {
                current_line = current_line + " ";
            }
            current_line = current_line + word;
        } else {
            if current_line.length > 0 {
                lines.push(current_line);
            }
            current_line = word;
        }
    }
    
    if current_line.length > 0 {
        lines.push(current_line);
    }
    
    return lines;
}

func dedent(s) {
    let lines = splitlines(s);
    
    :: Find minimum indentation
    let min_indent = none;
    for line in lines {
        let trimmed = strip(line);
        if trimmed.length == 0 {
            continue;
        }
        
        let indent = 0;
        for i in 0..line.length {
            if line[i] == " " || line[i] == "\t" {
                indent = indent + 1;
            } else {
                break;
            }
        }
        
        if min_indent == none || indent < min_indent {
            min_indent = indent;
        }
    }
    
    if min_indent == none || min_indent == 0 {
        return s;
    }
    
    :: Remove minimum indentation from all lines
    let result = [];
    for line in lines {
        if line.length >= min_indent {
            result.push(line.substring(min_indent));
        } else {
            result.push(line);
        }
    }
    
    return join("\n", result);
}

func levenshtein(s1, s2) {
    let m = s1.length;
    let n = s2.length;
    
    :: Create distance matrix
    let d = [];
    for i in 0..=m {
        d.push([]);
        for j in 0..=n {
            d[i].push(0);
        }
    }
    
    :: Initialize first column and row
    for i in 0..=m {
        d[i][0] = i;
    }
    for j in 0..=n {
        d[0][j] = j;
    }
    
    :: Fill matrix
    for i in 1..=m {
        for j in 1..=n {
            let cost = s1[i - 1] == s2[j - 1] ? 0 : 1;
            d[i][j] = min([
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + cost
            ]);
        }
    }
    
    return d[m][n];
}

func min(arr) {
    let minimum = arr[0];
    for item in arr {
        if item < minimum {
            minimum = item;
        }
    }
    return minimum;
}

export {
    split, join, strip, lstrip, rstrip, replace,
    upper, lower, capitalize, title, swapcase,
    startswith, endswith, contains,
    isalpha, isdigit, isalnum, isspace, isupper, islower,
    format, center, ljust, rjust, zfill,
    find, rfind, count,
    partition, rpartition, splitlines,
    reverse, remove_prefix, remove_suffix, truncate, wrap, dedent,
    levenshtein
};

:: Aliases expected by doc examples
func trim(s) { return strip(s, none); }
func substring(s, start, end) { return s[start:end]; }
func starts_with(s, prefix) { return startswith(s, prefix); }
func ends_with(s, suffix) { return endswith(s, suffix); }
