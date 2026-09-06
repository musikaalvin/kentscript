:: csv - CSV file reading and writing

class Reader {
    func __init__(self, file, delimiter, quotechar) {
        self.file = file;
        self.delimiter = delimiter != none ? delimiter : ",";
        self.quotechar = quotechar != none ? quotechar : '"';
    }
    
    func __iter__(self) {
        return self;
    }
    
    func __next__(self) {
        let line = self.file.readline();
        if line == none {
            raise StopIteration();
        }
        return self._parse_line(line);
    }
    
    func _parse_line(self, line) {
        let fields = [];
        let current = "";
        let in_quotes = false;
        let i = 0;
        
        while i < line.length {
            let char = line[i];
            
            if char == self.quotechar {
                if in_quotes && i + 1 < line.length && line[i + 1] == self.quotechar {
                    current = current + self.quotechar;
                    i = i + 2;
                    continue;
                }
                in_quotes = !in_quotes;
            } else if char == self.delimiter && !in_quotes {
                fields.push(current);
                current = "";
            } else if char != "\n" && char != "\r" {
                current = current + char;
            }
            
            i = i + 1;
        }
        
        fields.push(current);
        return fields;
    }
}

class Writer {
    func __init__(self, file, delimiter, quotechar, quoting) {
        self.file = file;
        self.delimiter = delimiter != none ? delimiter : ",";
        self.quotechar = quotechar != none ? quotechar : '"';
        self.quoting = quoting != none ? quoting : QUOTE_MINIMAL;
    }
    
    func writerow(self, row) {
        let fields = [];
        
        for field in row {
            fields.push(self._quote_field(str(field)));
        }
        
        self.file.write(fields.join(self.delimiter) + "\n");
    }
    
    func writerows(self, rows) {
        for row in rows {
            self.writerow(row);
        }
    }
    
    func _quote_field(self, field) {
        let needs_quote = false;
        
        if self.quoting == QUOTE_ALL {
            needs_quote = true;
        } else if self.quoting == QUOTE_MINIMAL {
            needs_quote = field.indexOf(self.delimiter) != -1 || 
                         field.indexOf(self.quotechar) != -1 ||
                         field.indexOf("\n") != -1;
        } else if self.quoting == QUOTE_NONNUMERIC {
            needs_quote = isNaN(parseFloat(field));
        }
        
        if needs_quote {
            let escaped = field.replace(self.quotechar, self.quotechar + self.quotechar);
            return self.quotechar + escaped + self.quotechar;
        }
        
        return field;
    }
}

class DictReader {
    func __init__(self, file, fieldnames, delimiter, quotechar) {
        self.reader = Reader(file, delimiter, quotechar);
        self.fieldnames = fieldnames;
        self.first_row = true;
    }
    
    func __iter__(self) {
        return self;
    }
    
    func __next__(self) {
        let row = self.reader.__next__();
        
        if self.first_row && self.fieldnames == none {
            self.fieldnames = row;
            self.first_row = false;
            row = self.reader.__next__();
        }
        
        let result = {};
        for i in 0..self.fieldnames.length {
            result[self.fieldnames[i]] = i < row.length ? row[i] : none;
        }
        
        return result;
    }
}

class DictWriter {
    func __init__(self, file, fieldnames, delimiter, quotechar) {
        self.writer = Writer(file, delimiter, quotechar);
        self.fieldnames = fieldnames;
    }
    
    func writeheader(self) {
        self.writer.writerow(self.fieldnames);
    }
    
    func writerow(self, row_dict) {
        let row = [];
        for field in self.fieldnames {
            row.push(row_dict[field] != none ? row_dict[field] : "");
        }
        self.writer.writerow(row);
    }
    
    func writerows(self, row_dicts) {
        for row_dict in row_dicts {
            self.writerow(row_dict);
        }
    }
}

const QUOTE_MINIMAL = 0;
const QUOTE_ALL = 1;
const QUOTE_NONNUMERIC = 2;
const QUOTE_NONE = 3;

func reader(file, delimiter, quotechar) {
    return Reader(file, delimiter, quotechar);
}

func writer(file, delimiter, quotechar, quoting) {
    return Writer(file, delimiter, quotechar, quoting);
}

class StopIteration {}

export {
    Reader, Writer, DictReader, DictWriter,
    reader, writer,
    QUOTE_MINIMAL, QUOTE_ALL, QUOTE_NONNUMERIC, QUOTE_NONE
};
