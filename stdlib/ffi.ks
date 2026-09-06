:: ffi - Foreign Function Interface
:: Call C libraries from KentScript

class CLibrary {
    func __init__(self, path) {
        self.path = path;
        self.handle = ffi_load(path);
    }
    
    func get_function(self, name, argtypes, restype) {
        return CFunction(self.handle, name, argtypes, restype);
    }
    
    func close(self) {
        if self.handle != none {
            ffi_close(self.handle);
            self.handle = none;
        }
    }
}

class CFunction {
    func __init__(self, lib_handle, name, argtypes, restype) {
        self.lib_handle = lib_handle;
        self.name = name;
        self.argtypes = argtypes;
        self.restype = restype;
        self.func_ptr = ffi_get_symbol(lib_handle, name);
    }
    
    func call(self, ...args) {
        return ffi_call(self.func_ptr, args, self.argtypes, self.restype);
    }
    
    func __call__(self, ...args) {
        return self.call(...args);
    }
}

:: C type definitions
const c_void = "void";
const c_int = "int";
const c_uint = "uint";
const c_long = "long";
const c_ulong = "ulong";
const c_float = "float";
const c_double = "double";
const c_char = "char";
const c_char_p = "char*";
const c_void_p = "void*";
const c_bool = "bool";
const c_int8 = "int8";
const c_uint8 = "uint8";
const c_int16 = "int16";
const c_uint16 = "uint16";
const c_int32 = "int32";
const c_uint32 = "uint32";
const c_int64 = "int64";
const c_uint64 = "uint64";

func CDLL(path) {
    return CLibrary(path);
}

func cast(obj, typ) {
    return ffi_cast(obj, typ);
}

func sizeof(typ) {
    return ffi_sizeof(typ);
}

func addressof(obj) {
    return ffi_addressof(obj);
}

func pointer(obj) {
    return ffi_pointer(obj);
}

func string_at(addr, size) {
    return ffi_string_at(addr, size);
}

func memmove(dst, src, count) {
    ffi_memmove(dst, src, count);
}

func memset(dst, value, count) {
    ffi_memset(dst, value, count);
}

class Structure {
    func __init__(self) {
        self._fields_ = [];
    }
    
    func pack(self) {
        return ffi_pack_struct(self, self._fields_);
    }
    
    func unpack(self, data) {
        return ffi_unpack_struct(data, self._fields_);
    }
}

class Union {
    func __init__(self) {
        self._fields_ = [];
    }
    
    func pack(self) {
        return ffi_pack_union(self, self._fields_);
    }
    
    func unpack(self, data) {
        return ffi_unpack_union(data, self._fields_);
    }
}

func create_string_buffer(init, size) {
    if size == none {
        size = init.length + 1;
    }
    return ffi_create_buffer(size, init);
}

func create_unicode_buffer(init, size) {
    if size == none {
        size = init.length + 1;
    }
    return ffi_create_buffer(size * 2, init);
}

:: Runtime interface
func ffi_load(path) { return system_ffi_load(path); }
func ffi_close(handle) { system_ffi_close(handle); }
func ffi_get_symbol(handle, name) { return system_ffi_get_symbol(handle, name); }
func ffi_call(func_ptr, args, argtypes, restype) { return system_ffi_call(func_ptr, args, argtypes, restype); }
func ffi_cast(obj, typ) { return system_ffi_cast(obj, typ); }
func ffi_sizeof(typ) { return system_ffi_sizeof(typ); }
func ffi_addressof(obj) { return system_ffi_addressof(obj); }
func ffi_pointer(obj) { return system_ffi_pointer(obj); }
func ffi_string_at(addr, size) { return system_ffi_string_at(addr, size); }
func ffi_memmove(dst, src, count) { system_ffi_memmove(dst, src, count); }
func ffi_memset(dst, value, count) { system_ffi_memset(dst, value, count); }
func ffi_pack_struct(obj, fields) { return system_ffi_pack_struct(obj, fields); }
func ffi_unpack_struct(data, fields) { return system_ffi_unpack_struct(data, fields); }
func ffi_pack_union(obj, fields) { return system_ffi_pack_union(obj, fields); }
func ffi_unpack_union(data, fields) { return system_ffi_unpack_union(data, fields); }
func ffi_create_buffer(size, init) { return system_ffi_create_buffer(size, init); }

export {
    CLibrary, CFunction, Structure, Union,
    CDLL, cast, sizeof, addressof, pointer,
    string_at, memmove, memset,
    create_string_buffer, create_unicode_buffer,
    c_void, c_int, c_uint, c_long, c_ulong,
    c_float, c_double, c_char, c_char_p, c_void_p,
    c_bool, c_int8, c_uint8, c_int16, c_uint16,
    c_int32, c_uint32, c_int64, c_uint64
};
