"""
KentScript Enhanced Data Type System
Full support for all Python types with performance optimizations
"""

from typing import Any, List, Dict, Set, Tuple, Optional, Union, Callable, Iterator
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict, Counter, deque
from enum import Enum, auto
import array
import weakref


# ============================================================================
# PRIMITIVE TYPES
# ============================================================================

class Integer:
    """Enhanced integer with arbitrary precision"""
    __slots__ = ('_value',)
    
    def __init__(self, value: Union[int, str]):
        if isinstance(value, str):
            self._value = int(value)
        else:
            self._value = int(value)
    
    @property
    def value(self) -> int:
        return self._value
    
    def __repr__(self) -> str:
        return str(self._value)


class Float:
    """Enhanced float with precision tracking"""
    __slots__ = ('_value', '_precision')
    
    def __init__(self, value: Union[float, str], precision: int = 15):
        self._precision = precision
        if isinstance(value, str):
            self._value = float(value)
        else:
            self._value = float(value)
    
    @property
    def value(self) -> float:
        return self._value
    
    def __repr__(self) -> str:
        return f"{self._value:.{self._precision}g}"


class String:
    """Enhanced string with encoding support"""
    __slots__ = ('_value', '_encoding')
    
    def __init__(self, value: str, encoding: str = 'utf-8'):
        self._value = value
        self._encoding = encoding
    
    @property
    def value(self) -> str:
        return self._value
    
    @property
    def length(self) -> int:
        return len(self._value)
    
    def encode(self, encoding: str = 'utf-8') -> bytes:
        return self._value.encode(encoding)
    
    def decode(self) -> str:
        return self._value
    
    def __repr__(self) -> str:
        return repr(self._value)


class Bool:
    """Enhanced boolean type"""
    
    def __init__(self, value: Any):
        self._value = bool(value)
    
    @property
    def value(self) -> bool:
        return self._value
    
    def __repr__(self) -> str:
        return str(self._value)


# ============================================================================
# CONTAINER TYPES
# ============================================================================

class LangList:
    """Optimized list with performance features"""
    __slots__ = ('_data', '_capacity', '_size')
    
    def __init__(self, items: List[Any] = None):
        self._capacity = 10
        self._size = 0
        self._data = [None] * self._capacity
        
        if items:
            for item in items:
                self.append(item)
    
    def append(self, item: Any) -> None:
        """Add item to end"""
        if self._size >= self._capacity:
            self._capacity *= 2
            new_data = [None] * self._capacity
            for i in range(self._size):
                new_data[i] = self._data[i]
            self._data = new_data
        
        self._data[self._size] = item
        self._size += 1
    
    def pop(self, index: int = -1) -> Any:
        """Remove and return item"""
        if self._size == 0:
            raise IndexError("pop from empty list")
        
        if index == -1:
            index = self._size - 1
        
        item = self._data[index]
        for i in range(index, self._size - 1):
            self._data[i] = self._data[i + 1]
        self._size -= 1
        return item
    
    def __getitem__(self, index: int) -> Any:
        if index < 0:
            index = self._size + index
        if index < 0 or index >= self._size:
            raise IndexError("list index out of range")
        return self._data[index]
    
    def __setitem__(self, index: int, value: Any) -> None:
        if index < 0:
            index = self._size + index
        if index < 0 or index >= self._size:
            raise IndexError("list assignment index out of range")
        self._data[index] = value
    
    def __len__(self) -> int:
        return self._size
    
    def __iter__(self):
        for i in range(self._size):
            yield self._data[i]
    
    def __repr__(self) -> str:
        items = [repr(self._data[i]) for i in range(self._size)]
        return f"[{', '.join(items)}]"


class LangDict:
    """Optimized dictionary with hash table"""
    __slots__ = ('_table', '_size', '_capacity')
    
    def __init__(self, items: Dict = None):
        self._capacity = 16
        self._size = 0
        self._table = [{} for _ in range(self._capacity)]
        
        if items:
            for key, value in items.items():
                self[key] = value
    
    def _hash(self, key: Any) -> int:
        """Compute hash for key"""
        return hash(key) % self._capacity
    
    def __setitem__(self, key: Any, value: Any) -> None:
        h = self._hash(key)
        bucket = self._table[h]
        
        if key not in bucket:
            self._size += 1
        
        bucket[key] = value
        
        # Resize if needed
        if self._size > self._capacity * 0.75:
            self._resize()
    
    def __getitem__(self, key: Any) -> Any:
        h = self._hash(key)
        bucket = self._table[h]
        
        if key not in bucket:
            raise KeyError(key)
        
        return bucket[key]
    
    def __contains__(self, key: Any) -> bool:
        h = self._hash(key)
        return key in self._table[h]
    
    def _resize(self) -> None:
        """Resize hash table"""
        old_table = self._table
        self._capacity *= 2
        self._table = [{} for _ in range(self._capacity)]
        self._size = 0
        
        for bucket in old_table:
            for key, value in bucket.items():
                self[key] = value
    
    def __len__(self) -> int:
        return self._size
    
    def keys(self):
        """Get all keys"""
        for bucket in self._table:
            yield from bucket.keys()
    
    def values(self):
        """Get all values"""
        for bucket in self._table:
            yield from bucket.values()
    
    def items(self):
        """Get all items"""
        for bucket in self._table:
            yield from bucket.items()
    
    def __iter__(self):
        return self.keys()
    
    def __repr__(self) -> str:
        items = [f"{repr(k)}: {repr(v)}" for k, v in self.items()]
        return f"{{{', '.join(items)}}}"


class LangSet:
    """Optimized set with hashing"""
    
    def __init__(self, items=None):
        self._dict = LangDict()
        if items:
            for item in items:
                self.add(item)
    
    def add(self, item: Any) -> None:
        """Add item to set"""
        self._dict[item] = True
    
    def remove(self, item: Any) -> None:
        """Remove item from set"""
        if item not in self._dict:
            raise KeyError(item)
        del self._dict[item]
    
    def __contains__(self, item: Any) -> bool:
        return item in self._dict
    
    def __len__(self) -> int:
        return len(self._dict)
    
    def __iter__(self):
        return iter(self._dict.keys())
    
    def union(self, other: 'LangSet') -> 'LangSet':
        """Union with another set"""
        result = LangSet(self)
        for item in other:
            result.add(item)
        return result
    
    def intersection(self, other: 'LangSet') -> 'LangSet':
        """Intersection with another set"""
        result = LangSet()
        for item in self:
            if item in other:
                result.add(item)
        return result
    
    def __repr__(self) -> str:
        items = [repr(item) for item in self]
        return f"{{{', '.join(items)}}}"


class LangTuple:
    """Immutable tuple"""
    __slots__ = ('_data', '_hash')
    
    def __init__(self, items=None):
        if items is None:
            self._data = ()
        else:
            self._data = tuple(items)
        self._hash = None
    
    def __getitem__(self, index: int) -> Any:
        return self._data[index]
    
    def __len__(self) -> int:
        return len(self._data)
    
    def __iter__(self):
        return iter(self._data)
    
    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash(self._data)
        return self._hash
    
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, LangTuple):
            return self._data == other._data
        return self._data == other
    
    def __repr__(self) -> str:
        items = [repr(item) for item in self._data]
        if len(items) == 1:
            return f"({items[0]},)"
        return f"({', '.join(items)})"


# ============================================================================
# ADVANCED CONTAINER TYPES
# ============================================================================

class LangDeque:
    """Double-ended queue for efficient operations"""
    
    def __init__(self, items=None):
        self._deque = deque(items or [])
    
    def append_left(self, item: Any) -> None:
        self._deque.appendleft(item)
    
    def append_right(self, item: Any) -> None:
        self._deque.append(item)
    
    def pop_left(self) -> Any:
        return self._deque.popleft()
    
    def pop_right(self) -> Any:
        return self._deque.pop()
    
    def __len__(self) -> int:
        return len(self._deque)
    
    def __iter__(self):
        return iter(self._deque)


class LangCounter:
    """Counter for counting hashable objects"""
    
    def __init__(self, items=None):
        self._counter = Counter(items or [])
    
    def count(self, item: Any) -> int:
        """Get count of item"""
        return self._counter[item]
    
    def most_common(self, n: int = None) -> List[Tuple]:
        """Get most common items"""
        return self._counter.most_common(n)
    
    def __len__(self) -> int:
        return len(self._counter)
    
    def __repr__(self) -> str:
        return repr(self._counter)


class Matrix:
    """2D matrix type for numerical computing"""
    
    def __init__(self, rows: int, cols: int, initial: float = 0.0):
        self.rows = rows
        self.cols = cols
        self._data = [[initial for _ in range(cols)] for _ in range(rows)]
    
    def __getitem__(self, idx: Tuple[int, int]) -> float:
        row, col = idx
        return self._data[row][col]
    
    def __setitem__(self, idx: Tuple[int, int], value: float) -> None:
        row, col = idx
        self._data[row][col] = value
    
    def transpose(self) -> 'Matrix':
        """Transpose the matrix"""
        result = Matrix(self.cols, self.rows)
        for i in range(self.rows):
            for j in range(self.cols):
                result[j, i] = self._data[i][j]
        return result
    
    def __repr__(self) -> str:
        lines = []
        for row in self._data:
            lines.append("  " + "  ".join(f"{x:8.2f}" for x in row))
        return "Matrix(\n" + "\n".join(lines) + "\n)"


# ============================================================================
# TYPE CONVERSIONS
# ============================================================================

class TypeConverter:
    """Convert between types efficiently"""
    
    @staticmethod
    def to_int(value: Any) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            return int(value)
        if isinstance(value, bool):
            return 1 if value else 0
        raise TypeError(f"Cannot convert {type(value)} to int")
    
    @staticmethod
    def to_float(value: Any) -> float:
        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return float(value)
        if isinstance(value, str):
            return float(value)
        raise TypeError(f"Cannot convert {type(value)} to float")
    
    @staticmethod
    def to_str(value: Any) -> str:
        return str(value)
    
    @staticmethod
    def to_bool(value: Any) -> bool:
        return bool(value)
    
    @staticmethod
    def to_list(value: Any) -> List:
        if isinstance(value, list):
            return value
        if isinstance(value, (tuple, set)):
            return list(value)
        if isinstance(value, dict):
            return list(value.values())
        return [value]


# ============================================================================
# TYPE ANNOTATIONS
# ============================================================================

@dataclass
class TypeInfo:
    """Type information for type checking"""
    name: str
    base_type: type
    is_nullable: bool = False
    is_array: bool = False
    element_type: Optional['TypeInfo'] = None
    
    def matches(self, value: Any) -> bool:
        """Check if value matches type"""
        if self.is_nullable and value is None:
            return True
        
        if self.is_array:
            if not isinstance(value, (list, tuple)):
                return False
            if self.element_type:
                return all(self.element_type.matches(item) for item in value)
            return True
        
        return isinstance(value, self.base_type)


def create_type(name: str, base_type: type, nullable: bool = False) -> TypeInfo:
    """Create a type descriptor"""
    return TypeInfo(name, base_type, nullable)


def create_array_type(element_type: TypeInfo) -> TypeInfo:
    """Create an array type"""
    return TypeInfo(f"Array[{element_type.name}]", list, 
                   is_array=True, element_type=element_type)


# ============================================================================
# GENERIC TYPES
# ============================================================================

class Generic:
    """Generic type parameter"""
    
    def __init__(self, name: str):
        self.name = name
    
    def __repr__(self) -> str:
        return self.name


class GenericType:
    """Generic class implementation"""
    
    def __init__(self, base_type: type, type_params: List[TypeInfo]):
        self.base_type = base_type
        self.type_params = type_params
    
    def __repr__(self) -> str:
        params = ", ".join(p.name for p in self.type_params)
        return f"{self.base_type.__name__}[{params}]"
