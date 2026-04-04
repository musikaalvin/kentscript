#!/usr/bin/env python3
"""
KentScript Type System - Type definitions and checking
"""

from enum import Enum, auto
from typing import Dict, Optional, List, Any


class BaseType(Enum):
    # Primitive types
    I8 = auto()
    I16 = auto()
    I32 = auto()
    I64 = auto()
    U8 = auto()
    U16 = auto()
    U32 = auto()
    U64 = auto()
    F32 = auto()
    F64 = auto()
    BOOL = auto()
    CHAR = auto()
    VOID = auto()

    # Compound types
    STRING = auto()
    ARRAY = auto()
    POINTER = auto()
    FUNCTION = auto()
    STRUCT = auto()
    ENUM = auto()
    TRAIT = auto()
    TUPLE = auto()
    UNKNOWN = auto()


class TypeDescriptor:
    """Represents a type in KentScript"""

    def __init__(self, base: BaseType, name: str = "", nullable: bool = False):
        self.base = base
        self.name = name
        self.nullable = nullable
        self.size = self._calculate_size()

    def _calculate_size(self) -> int:
        """Calculate type size in bytes"""
        size_map = {
            BaseType.I8: 1,
            BaseType.I16: 2,
            BaseType.I32: 4,
            BaseType.I64: 8,
            BaseType.U8: 1,
            BaseType.U16: 2,
            BaseType.U32: 4,
            BaseType.U64: 8,
            BaseType.F32: 4,
            BaseType.F64: 8,
            BaseType.BOOL: 1,
            BaseType.CHAR: 1,
            BaseType.VOID: 0,
            BaseType.POINTER: 8,  # 64-bit pointer
            BaseType.STRING: 16,  # ptr + len
        }
        return size_map.get(self.base, 0)

    def __eq__(self, other):
        if not isinstance(other, TypeDescriptor):
            return False
        return self.base == other.base and self.name == other.name

    def __hash__(self):
        return hash((self.base, self.name))

    def __str__(self):
        if self.name:
            return self.name
        return self.base.name.lower()

    def is_numeric(self) -> bool:
        return self.base in [
            BaseType.I8,
            BaseType.I16,
            BaseType.I32,
            BaseType.I64,
            BaseType.U8,
            BaseType.U16,
            BaseType.U32,
            BaseType.U64,
            BaseType.F32,
            BaseType.F64,
        ]

    def is_integer(self) -> bool:
        return self.base in [
            BaseType.I8,
            BaseType.I16,
            BaseType.I32,
            BaseType.I64,
            BaseType.U8,
            BaseType.U16,
            BaseType.U32,
            BaseType.U64,
        ]

    def is_floating(self) -> bool:
        return self.base in [BaseType.F32, BaseType.F64]

    def is_signed(self) -> bool:
        return self.base in [BaseType.I8, BaseType.I16, BaseType.I32, BaseType.I64]

    def is_unsigned(self) -> bool:
        return self.base in [BaseType.U8, BaseType.U16, BaseType.U32, BaseType.U64]


class PointerType(TypeDescriptor):
    """Pointer type (e.g., i32*)"""

    def __init__(self, pointee: TypeDescriptor):
        super().__init__(BaseType.POINTER, f"{pointee}*")
        self.pointee = pointee


class ArrayType(TypeDescriptor):
    """Array type (e.g., i32[10])"""

    def __init__(self, element_type: TypeDescriptor, size: Optional[int] = None):
        super().__init__(
            BaseType.ARRAY,
            f"{element_type}[]" if not size else f"{element_type}[{size}]",
        )
        self.element_type = element_type
        self.size = size


class FunctionType(TypeDescriptor):
    """Function type (e.g., (i32, i32) -> i32)"""

    def __init__(self, param_types: List[TypeDescriptor], return_type: TypeDescriptor):
        params_str = ", ".join(str(t) for t in param_types)
        super().__init__(BaseType.FUNCTION, f"({params_str}) -> {return_type}")
        self.param_types = param_types
        self.return_type = return_type


class StructType(TypeDescriptor):
    """Struct type with fields"""

    def __init__(self, name: str, fields: Dict[str, TypeDescriptor]):
        super().__init__(BaseType.STRUCT, name)
        self.fields = fields
        self.field_order = list(fields.keys())


class EnumType(TypeDescriptor):
    """Enum type with variants"""

    def __init__(self, name: str, variants: List[str]):
        super().__init__(BaseType.ENUM, name)
        self.variants = variants


class TypeRegistry:
    """Manages all types in the program"""

    def __init__(self):
        # Built-in primitive types
        self.types: Dict[str, TypeDescriptor] = {
            "i8": TypeDescriptor(BaseType.I8, "i8"),
            "i16": TypeDescriptor(BaseType.I16, "i16"),
            "i32": TypeDescriptor(BaseType.I32, "i32"),
            "i64": TypeDescriptor(BaseType.I64, "i64"),
            "u8": TypeDescriptor(BaseType.U8, "u8"),
            "u16": TypeDescriptor(BaseType.U16, "u16"),
            "u32": TypeDescriptor(BaseType.U32, "u32"),
            "u64": TypeDescriptor(BaseType.U64, "u64"),
            "f32": TypeDescriptor(BaseType.F32, "f32"),
            "f64": TypeDescriptor(BaseType.F64, "f64"),
            "bool": TypeDescriptor(BaseType.BOOL, "bool"),
            "char": TypeDescriptor(BaseType.CHAR, "char"),
            "str": TypeDescriptor(BaseType.STRING, "str"),
            "void": TypeDescriptor(BaseType.VOID, "void"),
        }

    def register(self, name: str, kent_type: TypeDescriptor):
        """Register a type"""
        self.types[name] = kent_type

    def lookup(self, name: str) -> Optional[TypeDescriptor]:
        """Look up a type by name"""
        return self.types.get(name)

    def resolve_type_string(self, type_str: str) -> Optional[TypeDescriptor]:
        """Resolve a type from a string like 'i32*' or 'i32[10]'"""
        # Remove whitespace
        type_str = type_str.strip()

        # Handle pointer types
        if type_str.endswith("*"):
            base_name = type_str[:-1].strip()
            base_type = self.lookup(base_name)
            if base_type:
                return PointerType(base_type)

        # Handle array types
        if "[" in type_str and "]" in type_str:
            bracket_idx = type_str.index("[")
            base_name = type_str[:bracket_idx].strip()
            size_str = type_str[bracket_idx + 1 : -1]
            base_type = self.lookup(base_name)
            if base_type:
                size = int(size_str) if size_str.isdigit() else None
                return ArrayType(base_type, size)

        # Direct lookup
        return self.lookup(type_str)

    def get_all_types(self) -> Dict[str, TypeDescriptor]:
        """Get all registered types"""
        return self.types.copy()


class TypeChecker:
    """Type checking and validation"""

    def __init__(self, registry: TypeRegistry):
        self.registry = registry

    def is_compatible(self, from_type: TypeDescriptor, to_type: TypeDescriptor) -> bool:
        """Check if from_type can be converted to to_type"""
        if from_type == to_type:
            return True

        # Numeric type compatibility
        if from_type.is_numeric() and to_type.is_numeric():
            # Allow numeric conversions with possible narrowing
            return True

        # Allow pointer conversions
        if isinstance(from_type, PointerType) and isinstance(to_type, PointerType):
            return self.is_compatible(from_type.pointee, to_type.pointee)

        return False

    def unify_types(
        self, type1: TypeDescriptor, type2: TypeDescriptor
    ) -> Optional[TypeDescriptor]:
        """Find a common type for two types"""
        if type1 == type2:
            return type1

        # Numeric type unification
        if type1.is_numeric() and type2.is_numeric():
            # Unify to larger type
            size_map = {
                BaseType.I8: 1,
                BaseType.I16: 2,
                BaseType.I32: 4,
                BaseType.I64: 8,
                BaseType.U8: 1,
                BaseType.U16: 2,
                BaseType.U32: 4,
                BaseType.U64: 8,
                BaseType.F32: 4,
                BaseType.F64: 8,
            }

            # If one is floating point, prefer floating
            if type1.is_floating() or type2.is_floating():
                if type1.is_floating():
                    return type1 if type1.size >= type2.size else type2
                return type2

            # Otherwise prefer larger integer type
            size1 = size_map.get(type1.base, 0)
            size2 = size_map.get(type2.base, 0)
            return type1 if size1 >= size2 else type2

        return None


# Global type registry
_type_registry = TypeRegistry()
_type_checker = TypeChecker(_type_registry)


def get_type_registry() -> TypeRegistry:
    return _type_registry


def get_type_checker() -> TypeChecker:
    return _type_checker


def reset_types():
    global _type_registry, _type_checker
    _type_registry = TypeRegistry()
    _type_checker = TypeChecker(_type_registry)


#!/usr/bin/env python3
"""
KentScript Symbol Table - Manages scopes and symbols
"""

from typing import Dict, Optional, List, Any


class Symbol:
    def __init__(
        self,
        name: str,
        symbol_type: str,
        scope_level: int,
        is_mutable: bool = False,
        value: Any = None,
    ):
        self.name = name
        self.symbol_type = symbol_type  # 'var', 'function', 'type', etc.
        self.scope_level = scope_level
        self.is_mutable = is_mutable
        self.value = value
        self.defined = False


class SymbolTable:
    def __init__(self):
        self.scopes: List[Dict[str, Symbol]] = [{}]  # Start with global scope
        self.scope_level = 0
        self.builtin_symbols = {
            "print": Symbol("print", "function", 0),
            "len": Symbol("len", "function", 0),
            "range": Symbol("range", "function", 0),
            "input": Symbol("input", "function", 0),
            "int": Symbol("int", "type", 0),
            "float": Symbol("float", "type", 0),
            "str": Symbol("str", "type", 0),
            "bool": Symbol("bool", "type", 0),
            "list": Symbol("list", "type", 0),
            "dict": Symbol("dict", "type", 0),
            "set": Symbol("set", "type", 0),
        }
        # Add builtins to global scope
        for name, symbol in self.builtin_symbols.items():
            self.scopes[0][name] = symbol

    def enter_scope(self):
        """Enter a new scope"""
        self.scopes.append({})
        self.scope_level += 1

    def exit_scope(self):
        """Exit current scope"""
        if self.scope_level > 0:
            self.scopes.pop()
            self.scope_level -= 1

    def define(
        self, name: str, symbol_type: str, is_mutable: bool = False, value: Any = None
    ) -> Symbol:
        """Define a new symbol in current scope"""
        symbol = Symbol(name, symbol_type, self.scope_level, is_mutable, value)
        symbol.defined = True
        self.scopes[self.scope_level][name] = symbol
        return symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up a symbol in current and parent scopes"""
        for i in range(len(self.scopes) - 1, -1, -1):
            if name in self.scopes[i]:
                return self.scopes[i][name]
        return None

    def lookup_in_current(self, name: str) -> Optional[Symbol]:
        """Look up a symbol only in current scope"""
        if name in self.scopes[self.scope_level]:
            return self.scopes[self.scope_level][name]
        return None

    def update(self, name: str, value: Any) -> bool:
        """Update a symbol's value"""
        symbol = self.lookup(name)
        if symbol:
            symbol.value = value
            return True
        return False

    def is_defined(self, name: str) -> bool:
        """Check if symbol is defined"""
        return self.lookup(name) is not None

    def dump_scope(self) -> Dict[str, Symbol]:
        """Get current scope"""
        return self.scopes[self.scope_level] if self.scopes else {}

    def dump_all_scopes(self) -> List[Dict[str, Symbol]]:
        """Get all scopes"""
        return self.scopes


# Global symbol table
_global_symbol_table = SymbolTable()


def get_symbol_table() -> SymbolTable:
    return _global_symbol_table


def reset_symbol_table():
    global _global_symbol_table
    _global_symbol_table = SymbolTable()


#!/usr/bin/env python3
"""
KentScript AST - Abstract Syntax Tree node definitions
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from enum import Enum, auto


