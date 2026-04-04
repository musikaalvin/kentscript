:: struct_utils - Struct packing and layout utilities
:: Provides utilities for working with packed structs and memory layout

:: Calculate size of packed struct fields
:: Returns total size without padding
func packed_size(field_sizes: list) -> int {
    let total = 0;
    for size in field_sizes {
        total = total + size;
    }
    return total;
}

:: Calculate size of struct with natural alignment
:: Takes into account alignment requirements
func aligned_size(field_sizes: list) -> int {
    let total = 0;
    let max_align = 1;
    
    for size in field_sizes {
        if size > max_align {
            max_align = size;
        }
        let offset = total % size;
        if offset != 0 {
            total = total + (size - offset);
        }
        total = total + size;
    }
    
    let remainder = total % max_align;
    if remainder != 0 {
        total = total + (max_align - remainder);
    }
    
    return total;
}

:: Get field offset in packed struct
func packed_offset(field_index: int, field_sizes: list) -> int {
    let offset = 0;
    for i in range(field_index) {
        offset = offset + field_sizes[i];
    }
    return offset;
}

:: Get field offset in aligned struct  
func aligned_offset(field_index: int, field_sizes: list, alignments: list) -> int {
    let offset = 0;
    for i in range(field_index) {
        let align = alignments[i];
        let remainder = offset % align;
        if remainder != 0 {
            offset = offset + (align - remainder);
        }
        offset = offset + field_sizes[i];
    }
    return offset;
}

:: Calculate alignment requirement for a type
func type_alignment(type_name: str) -> int {
    if type_name == "i8" || type_name == "u8" || type_name == "bool" {
        return 1;
    }
    if type_name == "i16" || type_name == "u16" {
        return 2;
    }
    if type_name == "i32" || type_name == "u32" || type_name == "f32" {
        return 4;
    }
    if type_name == "i64" || type_name == "u64" || type_name == "f64" || type_name == "ptr" {
        return 8;
    }
    return 1;
}

:: Common type sizes
const SIZE_I8 = 1;
const SIZE_I16 = 2;
const SIZE_I32 = 4;
const SIZE_I64 = 8;
const SIZE_PTR = 8;

:: Common type alignments
const ALIGN_I8 = 1;
const ALIGN_I16 = 2;
const ALIGN_I32 = 4;
const ALIGN_I64 = 8;
const ALIGN_PTR = 8;

:: Create packed struct layout descriptor
:: field_types: list of type names
:: Returns dict with offsets and size
func make_packed_layout(field_types: list) -> dict {
    let offsets = [];
    let size = 0;
    
    for ft in field_types {
        let field_size = type_size(ft);
        offsets.append(size);
        size = size + field_size;
    }
    
    return {
        "offsets": offsets,
        "size": size,
        "packed": true
    };
}

:: Create aligned struct layout descriptor
func make_aligned_layout(field_types: list) -> dict {
    let offsets = [];
    let alignments = [];
    let size = 0;
    let max_align = 1;
    
    for ft in field_types {
        let align = type_alignment(ft);
        let field_size = type_size(ft);
        
        if align > max_align {
            max_align = align;
        }
        
        let remainder = size % align;
        if remainder != 0 {
            size = size + (align - remainder);
        }
        
        offsets.append(size);
        alignments.append(align);
        size = size + field_size;
    }
    
    let remainder = size % max_align;
    if remainder != 0 {
        size = size + (max_align - remainder);
    }
    
    return {
        "offsets": offsets,
        "alignments": alignments,
        "size": size,
        "packed": false,
        "alignment": max_align
    };
}

:: Get size of a type by name
func type_size(type_name: str) -> int {
    if type_name == "i8" || type_name == "u8" || type_name == "bool" {
        return 1;
    }
    if type_name == "i16" || type_name == "u16" {
        return 2;
    }
    if type_name == "i32" || type_name == "u32" || type_name == "f32" {
        return 4;
    }
    if type_name == "i64" || type_name == "u64" || type_name == "f64" || type_name == "ptr" {
        return 8;
    }
    return 8;
}

:: Read field from packed struct at address
func read_packed_field(addr: int, field_offset: int, field_type: str) -> int {
    let size = type_size(field_type);
    let value = 0;
    
    if field_type == "i8" || field_type == "u8" || field_type == "bool" {
        value = read_byte(addr, field_offset);
    } else if field_type == "i16" || field_type == "u16" {
        value = read_word(addr, field_offset, 2);
    } else if field_type == "i32" || field_type == "u32" || field_type == "f32" {
        value = read_word(addr, field_offset, 4);
    } else if field_type == "i64" || field_type == "u64" || field_type == "f64" || field_type == "ptr" {
        value = read_word(addr, field_offset, 8);
    }
    
    return value;
}

:: Write field to packed struct at address
func write_packed_field(addr: int, field_offset: int, field_type: str, value: int) {
    let size = type_size(field_type);
    
    if field_type == "i8" || field_type == "u8" || field_type == "bool" {
        write_byte(addr, field_offset, value);
    } else if field_type == "i16" || field_type == "u16" {
        write_word(addr, field_offset, value, 2);
    } else if field_type == "i32" || field_type == "u32" || field_type == "f32" {
        write_word(addr, field_offset, value, 4);
    } else if field_type == "i64" || field_type == "u64" || field_type == "f64" || field_type == "ptr" {
        write_word(addr, field_offset, value, 8);
    }
}

:: Example: Create a packed struct for a point
:: Usage: let layout = make_packed_layout(["i32", "i32", "i32"]);
:: Then read/write fields at layout["offsets"][index]
