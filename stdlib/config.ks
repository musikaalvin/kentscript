:: config - Configuration file handling
:: Supports INI, JSON, YAML formats

class ConfigParser {
    func __init__(self) {
        self.sections = {};
        self.defaults = {};
    }
    
    func read(self, filename) {
        let content = file_read_all(filename);
        self._parse_ini(content);
    }
    
    func _parse_ini(self, content) {
        let lines = content.split("\n");
        let current_section = "DEFAULT";
        
        for line in lines {
            line = line.trim();
            
            if line.length == 0 || line.startsWith(";") || line.startsWith("#") {
                continue;
            }
            
            if line.startsWith("[") && line.endsWith("]") {
                current_section = line.substring(1, line.length - 1);
                if self.sections[current_section] == none {
                    self.sections[current_section] = {};
                }
            } else if line.indexOf("=") != -1 {
                let parts = line.split("=");
                let key = parts[0].trim();
                let value = parts[1].trim();
                
                if current_section == "DEFAULT" {
                    self.defaults[key] = value;
                } else {
                    self.sections[current_section][key] = value;
                }
            }
        }
    }
    
    func get(self, section, option, fallback) {
        if self.sections[section] != none && self.sections[section][option] != none {
            return self.sections[section][option];
        }
        if self.defaults[option] != none {
            return self.defaults[option];
        }
        return fallback;
    }
    
    func getint(self, section, option, fallback) {
        let value = self.get(section, option, fallback);
        return parseInt(value);
    }
    
    func getfloat(self, section, option, fallback) {
        let value = self.get(section, option, fallback);
        return parseFloat(value);
    }
    
    func getboolean(self, section, option, fallback) {
        let value = self.get(section, option, fallback);
        return value == "true" || value == "1" || value == "yes";
    }
    
    func set(self, section, option, value) {
        if self.sections[section] == none {
            self.sections[section] = {};
        }
        self.sections[section][option] = str(value);
    }
    
    func has_section(self, section) {
        return self.sections[section] != none;
    }
    
    func has_option(self, section, option) {
        return self.sections[section] != none && self.sections[section][option] != none;
    }
    
    func sections(self) {
        return Object.keys(self.sections);
    }
    
    func options(self, section) {
        if self.sections[section] != none {
            return Object.keys(self.sections[section]);
        }
        return [];
    }
    
    func write(self, filename) {
        let content = "";
        
        if Object.keys(self.defaults).length > 0 {
            content = content + "[DEFAULT]\n";
            for key in Object.keys(self.defaults) {
                content = content + key + " = " + self.defaults[key] + "\n";
            }
            content = content + "\n";
        }
        
        for section in Object.keys(self.sections) {
            content = content + "[" + section + "]\n";
            for key in Object.keys(self.sections[section]) {
                content = content + key + " = " + self.sections[section][key] + "\n";
            }
            content = content + "\n";
        }
        
        file_write_all(filename, content);
    }
}

class JSONConfig {
    func __init__(self) {
        self.data = {};
    }
    
    func load(self, filename) {
        let content = file_read_all(filename);
        self.data = JSON.parse(content);
    }
    
    func save(self, filename) {
        let content = JSON.stringify(self.data, none, 2);
        file_write_all(filename, content);
    }
    
    func get(self, key, default) {
        let parts = key.split(".");
        let value = self.data;
        
        for part in parts {
            if value == none { return default; }
            value = value[part];
        }
        
        return value != none ? value : default;
    }
    
    func set(self, key, value) {
        let parts = key.split(".");
        let obj = self.data;
        
        for i in 0..(parts.length - 1) {
            if obj[parts[i]] == none {
                obj[parts[i]] = {};
            }
            obj = obj[parts[i]];
        }
        
        obj[parts[parts.length - 1]] = value;
    }
}

func load_config(filename, format) {
    if format == none {
        if filename.endsWith(".json") {
            format = "json";
        } else if filename.endsWith(".ini") || filename.endsWith(".cfg") {
            format = "ini";
        } else {
            format = "ini";
        }
    }
    
    if format == "json" {
        let config = JSONConfig();
        config.load(filename);
        return config;
    } else {
        let config = ConfigParser();
        config.read(filename);
        return config;
    }
}

func file_read_all(filename) { return system_file_read_all(filename); }
func file_write_all(filename, content) { system_file_write_all(filename, content); }

export {
    ConfigParser, JSONConfig, load_config
};
