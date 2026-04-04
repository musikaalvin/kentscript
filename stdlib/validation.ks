:: ============================================================
:: KentScript Validation Module
:: ============================================================
:: Input validation framework for KentScript
:: Version: 1.2.0 - Fixed short-circuit bugs
:: Date: 2026-03-30
:: ============================================================

import regex;

func _err(msg, field) {
    if field != none {
        raise "ValidationError[" + field + "]: " + msg;
    }
    raise "ValidationError: " + msg;
}

func validate_string(input, min_len, max_len, pattern, name) {
    if name == none { name = "Input"; }
    
    if input == none {
        _err(name + " cannot be null", name);
    }
    
    if typeof(input) != "str" {
        _err(name + " must be a string", name);
    }
    
    if input == "" {
        _err(name + " cannot be empty", name);
    }
    
    if min_len != none {
        if input.length < min_len {
            _err(name + " must be at least " + str(min_len) + " chars", name);
        }
    }
    
    if max_len != none {
        if input.length > max_len {
            _err(name + " must be at most " + str(max_len) + " chars", name);
        }
    }
    
    if pattern != none {
        let result = regex.match(pattern, input);
        if result == none {
            _err(name + " does not match required pattern", name);
        }
    }
    
    return true;
}

func validate_email(input, name) {
    if name == none { name = "Email"; }
    
    validate_string(input, none, none, none, name);
    
    let email_pattern = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$";
    let result = regex.match(email_pattern, input);
    if result == none {
        _err(name + " must be a valid email address", name);
    }
    
    return true;
}

func validate_url(input, name) {
    if name == none { name = "URL"; }
    
    validate_string(input, none, none, none, name);
    
    let url_pattern = "^https?://[a-zA-Z0-9.-]+(?:/[a-zA-Z0-9._~:/?#\\[\\]@!$&'()*+,;=-]*)?$";
    let result = regex.match(url_pattern, input);
    if result == none {
        _err(name + " must be a valid URL", name);
    }
    
    return true;
}

func validate_number(input, min_val, max_val, name) {
    if name == none { name = "Input"; }
    
    if input == none {
        _err(name + " cannot be null", name);
    }
    
    let num = system_builtin_float(input);
    if num == none {
        _err(name + " must be a valid number", name);
    }
    
    if min_val != none {
        if num < min_val {
            _err(name + " must be at least " + str(min_val), name);
        }
    }
    
    if max_val != none {
        if num > max_val {
            _err(name + " must be at most " + str(max_val), name);
        }
    }
    
    return true;
}

func validate_integer(input, min_val, max_val, name) {
    if name == none { name = "Input"; }
    
    if input == none {
        _err(name + " cannot be null", name);
    }
    
    let num = system_builtin_int(input);
    if num == 0 && input != "0" {
        _err(name + " must be a valid integer", name);
    }
    
    if min_val != none {
        if num < min_val {
            _err(name + " must be at least " + str(min_val), name);
        }
    }
    
    if max_val != none {
        if num > max_val {
            _err(name + " must be at most " + str(max_val), name);
        }
    }
    
    return true;
}

func validate_array(input, min_len, max_len, validator, name) {
    if name == none { name = "Input"; }
    
    if input == none {
        _err(name + " cannot be null", name);
    }
    
    if typeof(input) != "list" {
        _err(name + " must be an array", name);
    }
    
    if min_len != none {
        if input.length < min_len {
            _err(name + " must have at least " + str(min_len) + " items", name);
        }
    }
    
    if max_len != none {
        if input.length > max_len {
            _err(name + " must have at most " + str(max_len) + " items", name);
        }
    }
    
    if validator != none {
        for i in range(input.length) {
            validator(input[i], name + "[" + str(i) + "]");
        }
    }
    
    return true;
}

func validate_object(input, schema, name) {
    if name == none { name = "Input"; }
    
    if input == none {
        _err(name + " cannot be null", name);
    }
    
    if typeof(input) != "dict" {
        _err(name + " must be an object", name);
    }
    
    if schema != none {
        let keys = input.keys();
        for key in keys(schema) {
            let required = schema[key]["required"];
            let val_type = schema[key]["type"];
            
            if required {
                if input[key] == none {
                    _err(name + "." + key + " is required", name + "." + key);
                }
            }
            
            if input[key] != none && val_type != none {
                let actual_type = typeof(input[key]);
                if actual_type != val_type {
                    _err(name + "." + key + " must be type " + val_type, name + "." + key);
                }
            }
        }
    }
    
    return true;
}

export {
    validate_string,
    validate_email,
    validate_url,
    validate_number,
    validate_integer,
    validate_array,
    validate_object
};
