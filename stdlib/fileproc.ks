:: fileproc - AWK-style line-by-line file processing
::
:: Usage:
::   import fileproc;
::   fileproc.each_line("/tmp/data.txt", func(line, n) {
::       print(n + ": " + line);
::   });
::   let lines = fileproc.read_lines("/tmp/data.txt");

func _split_lines(content) {
    let lines = content.split(chr(10));
    if len(lines) > 0 and lines[len(lines) - 1] == "" {
        lines.pop();
    }
    return lines;
}

func read_lines(path) {
    return _split_lines(fs_read_text(path));
}

func each_line(path, callback) {
    let lines = _split_lines(fs_read_text(path));
    for i in range(len(lines)) {
        callback(lines[i], i + 1);
    }
}

func grep(path, pattern) {
    let lines = _split_lines(fs_read_text(path));
    let results = [];
    for i in range(len(lines)) {
        if lines[i].contains(pattern) {
            results.push({"line": i + 1, "text": lines[i]});
        }
    }
    return results;
}

func count_lines(path) {
    return len(_split_lines(fs_read_text(path)));
}

func first_line(path) {
    let lines = _split_lines(fs_read_text(path));
    if len(lines) == 0 { return none; }
    return lines[0];
}

func head(path, n) {
    if n == none { n = 10; }
    let lines = _split_lines(fs_read_text(path));
    let result = [];
    let limit = n;
    if limit > len(lines) { limit = len(lines); }
    for i in range(limit) {
        result.push(lines[i]);
    }
    return result;
}

export { read_lines, each_line, grep, count_lines, first_line, head };
