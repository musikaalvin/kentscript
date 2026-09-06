:: ============================================================
:: KentScript Error Module
:: ============================================================
:: Comprehensive error hierarchy for KentScript
:: Version: 1.0.0
:: Date: 2026-02-19
:: ============================================================

:: ============================================================
:: Base Error Class
:: ============================================================

class Error {
    func __init__(self, message, cause = none) {
        self.message = message;
        self.cause = cause;
        self.stack = _get_stack_trace();
        self.timestamp = time_time();
    }
    
    func to_string(self) {
        let result = "Error: " + self.message;
        if self.cause != none {
            result = result + "\nCaused by: " + str(self.cause);
        }
        return result;
    }
    
    func get_message(self) {
        return self.message;
    }
    
    func get_cause(self) {
        return self.cause;
    }
    
    func get_stack(self) {
        return self.stack;
    }
}

:: ============================================================
:: Standard Error Types
:: ============================================================

class RuntimeError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class SyntaxError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class TypeError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class ValueError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class NameError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class IndexError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class KeyError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class AttributeError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class IOError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class OSError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

:: ============================================================
:: Domain-Specific Errors
:: ============================================================

class MathError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class NetworkError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class SecurityError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class ValidationError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class PermissionError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class NotFoundError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class AlreadyExistsError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class TimeoutError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class ConnectionError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class ParseError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

class MemoryError extends Error {
    func __init__(self, message, cause = none) {
        super.__init__(message, cause);
    }
}

:: ============================================================
:: Error Handling Utilities
:: ============================================================

:: Get current stack trace
func _get_stack_trace() {
    let trace = [];
    
    let i = 0;
    while i < 10 {
        let info = debug_get_frame(i);
        if info == none {
            break;
        }
        trace.push(info);
        i = i + 1;
    }
    
    return trace;
}

:: Assert function (renamed: `assert` is a reserved statement keyword)
func ks_assert(condition, message) {
    if !condition {
        if message == none {
            message = "Assertion failed";
        }
        raise AssertionError(message);
    }
}

:: Assert equal
func assert_equal(actual, expected, message) {
    if actual != expected {
        let msg = message != none ? message : "Expected " + str(expected) + " but got " + str(actual);
        raise AssertionError(msg);
    }
}

:: Assert not equal
func assert_not_equal(actual, unexpected, message) {
    if actual == unexpected {
        let msg = message != none ? message : "Value should not be " + str(unexpected);
        raise AssertionError(msg);
    }
}

:: Assert true
func assert_true(value, message) {
    if !value {
        let msg = message != none ? message : "Expected true but got false";
        raise AssertionError(msg);
    }
}

:: Assert false
func assert_false(value, message) {
    if value {
        let msg = message != none ? message : "Expected false but got true";
        raise AssertionError(msg);
    }
}

:: Assert none
func assert_none(value, message) {
    if value != none {
        let msg = message != none ? message : "Expected none but got " + str(value);
        raise AssertionError(msg);
    }
}

:: Assert not none
func assert_not_none(value, message) {
    if value == none {
        let msg = message != none ? message : "Value cannot be none";
        raise AssertionError(msg);
    }
}

:: Check not null (alias for assert_not_none)
func check_not_null(value, name) {
    if value == none {
        raise ValidationError(name + " cannot be null");
    }
}

:: Check not empty
func check_not_empty(value, name) {
    if value == none || value == "" {
        raise ValidationError(name + " cannot be empty");
    }
}

:: ============================================================
:: Exception Handling Utilities
:: ============================================================

:: Try-catch wrapper
func try_catch(try_fn, catch_fn) {
    try {
        return try_fn();
    } catch e {
        if catch_fn != none {
            return catch_fn(e);
        }
        return none;
    }
}

:: Try-catch-finally wrapper
func try_catch_finally(try_fn, catch_fn, finally_fn) {
    let result;
    let error;
    
    try {
        result = try_fn();
    } catch e {
        error = e;
        if catch_fn != none {
            result = catch_fn(e);
        }
    }
    
    if finally_fn != none {
        finally_fn();
    }
    
    if error != none {
        raise error;
    }
    
    return result;
}

:: ============================================================
:: Error Context
:: ============================================================

let _error_context = {};

:: Set error context
func set_error_context(key, value) {
    _error_context[key] = value;
}

:: Get error context
func get_error_context(key) {
    return _error_context[key];
}

:: Clear error context
func clear_error_context() {
    _error_context = {};
}

:: ============================================================
:: Export All
:: ============================================================

export {
    :: Base class
    Error,
    
    :: Standard errors
    RuntimeError,
    SyntaxError,
    TypeError,
    ValueError,
    NameError,
    IndexError,
    KeyError,
    AttributeError,
    IOError,
    OSError,
    
    :: Domain-specific errors
    MathError,
    NetworkError,
    SecurityError,
    ValidationError,
    PermissionError,
    NotFoundError,
    AlreadyExistsError,
    TimeoutError,
    ConnectionError,
    ParseError,
    MemoryError,
    
    :: Assertion utilities
    assert,
    assert_equal,
    assert_not_equal,
    assert_true,
    assert_false,
    assert_none,
    assert_not_none,
    check_not_null,
    check_not_empty,
    
    :: Exception handling
    try_catch,
    try_catch_finally,
    
    :: Context
    set_error_context,
    get_error_context,
    clear_error_context
};
