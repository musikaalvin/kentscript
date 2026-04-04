:: argparse - Command-line argument parsing

class ArgumentParser {
    func __init__(self, prog, description, epilog) {
        self.prog = prog;
        self.description = description;
        self.epilog = epilog;
        self.arguments = [];
        self.positionals = [];
        self.optionals = [];
    }
    
    func add_argument(self, ...names) {
        let arg = {
            "names": names,
            "help": none,
            "default": none,
            "required": false,
            "action": "store",
            "type": "str",
            "choices": none,
            "nargs": none,
            "dest": none
        };
        
        :: Determine if positional or optional
        let is_optional = false;
        for name in names {
            if name.startsWith("-") {
                is_optional = true;
                break;
            }
        }
        
        if is_optional {
            self.optionals.push(arg);
        } else {
            self.positionals.push(arg);
        }
        
        self.arguments.push(arg);
        return ArgumentAdder(arg);
    }
    
    func parse_args(self, args) {
        if args == none {
            args = get_argv();
        }
        
        let result = Namespace();
        let i = 0;
        let positional_index = 0;
        
        :: Set defaults
        for arg in self.arguments {
            let dest = arg.dest != none ? arg.dest : self._get_dest(arg);
            if arg.default != none {
                result[dest] = arg.default;
            } else if arg.action == "store_true" || arg.action == "store_false" {
                result[dest] = arg.action == "store_false";
            }
        }
        
        :: Parse arguments
        while i < args.length {
            let current = args[i];
            
            if current.startsWith("-") {
                :: Optional argument
                let arg = self._find_optional(current);
                if arg == none {
                    raise f"Unknown argument: {current}";
                }
                
                let dest = arg.dest != none ? arg.dest : self._get_dest(arg);
                
                if arg.action == "store_true" {
                    result[dest] = true;
                    i = i + 1;
                } else if arg.action == "store_false" {
                    result[dest] = false;
                    i = i + 1;
                } else if arg.action == "store" {
                    i = i + 1;
                    if i >= args.length {
                        raise f"Argument {current} requires a value";
                    }
                    result[dest] = self._convert_type(args[i], arg.type);
                    i = i + 1;
                }
            } else {
                :: Positional argument
                if positional_index >= self.positionals.length {
                    raise f"Too many positional arguments";
                }
                
                let arg = self.positionals[positional_index];
                let dest = arg.dest != none ? arg.dest : self._get_dest(arg);
                result[dest] = self._convert_type(current, arg.type);
                positional_index = positional_index + 1;
                i = i + 1;
            }
        }
        
        :: Check required arguments
        for arg in self.arguments {
            if arg.required {
                let dest = arg.dest != none ? arg.dest : self._get_dest(arg);
                if result[dest] == none {
                    raise f"Required argument missing: {arg.names[0]}";
                }
            }
        }
        
        return result;
    }
    
    func _find_optional(self, name) {
        for arg in self.optionals {
            for arg_name in arg.names {
                if arg_name == name {
                    return arg;
                }
            }
        }
        return none;
    }
    
    func _get_dest(self, arg) {
        for name in arg.names {
            if name.startsWith("--") {
                return name.substring(2).replace("-", "_");
            }
        }
        for name in arg.names {
            if name.startsWith("-") {
                return name.substring(1);
            }
        }
        return arg.names[0];
    }
    
    func _convert_type(self, value, type) {
        if type == "int" {
            return parseInt(value);
        } else if type == "float" {
            return parseFloat(value);
        } else if type == "bool" {
            return value == "true" || value == "1";
        }
        return value;
    }
    
    func print_help(self) {
        if self.description != none {
            print(self.description);
            print("");
        }
        
        print("Positional arguments:");
        for arg in self.positionals {
            let names = arg.names.join(", ");
            let help = arg.help != none ? arg.help : "";
            print(f"  {names:20s} {help}");
        }
        
        print("");
        print("Optional arguments:");
        for arg in self.optionals {
            let names = arg.names.join(", ");
            let help = arg.help != none ? arg.help : "";
            print(f"  {names:20s} {help}");
        }
        
        if self.epilog != none {
            print("");
            print(self.epilog);
        }
    }
}

class ArgumentAdder {
    func __init__(self, arg) {
        self.arg = arg;
    }
    
    func help(self, text) {
        self.arg.help = text;
        return self;
    }
    
    func default(self, value) {
        self.arg.default = value;
        return self;
    }
    
    func required(self, value) {
        self.arg.required = value;
        return self;
    }
    
    func action(self, value) {
        self.arg.action = value;
        return self;
    }
    
    func type(self, value) {
        self.arg.type = value;
        return self;
    }
    
    func dest(self, value) {
        self.arg.dest = value;
        return self;
    }
}

class Namespace {
    func __init__(self) {}
}

func get_argv() {
    return system_get_argv();
}

func system_get_argv() {
    return ["program", "arg1", "arg2"];
}

export {
    ArgumentParser, Namespace
};
