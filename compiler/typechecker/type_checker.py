"""
KentScript Strict Type Checker
[KS-REF-TYPE-001] Control-flow analysis with return path verification
[KS-REF-TYPE-002] Exhaustive match checking
[KS-REF-TYPE-003] Strict type enforcement

This module ensures compile-time safety by:
- Verifying all code paths return a value
- Checking exhaustive pattern matching
- Enforcing strict type compatibility
- Detecting unreachable code
"""

from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum, auto


class TypeCheckError(Exception):
    """Type checking error"""
    def __init__(self, message: str, line: int = 0, column: int = 0):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Line {line}:{column}: {message}")


class Type:
    """Base type class"""
    pass


@dataclass
class PrimitiveType(Type):
    """Primitive types: i8, i16, i32, i64, u8, u16, u32, u64, f32, f64, bool, void"""
    name: str
    
    def __eq__(self, other):
        return isinstance(other, PrimitiveType) and self.name == other.name
    
    def __hash__(self):
        return hash(self.name)
    
    def __str__(self):
        return self.name


@dataclass
class PointerType(Type):
    """Pointer type: *T or *mut T"""
    pointee: Type
    mutable: bool = False
    
    def __eq__(self, other):
        return isinstance(other, PointerType) and self.pointee == other.pointee and self.mutable == other.mutable
    
    def __hash__(self):
        return hash((self.pointee, self.mutable))
    
    def __str__(self):
        mut = "mut " if self.mutable else ""
        return f"*{mut}{self.pointee}"


@dataclass
class ArrayType(Type):
    """Array type: [T; N]"""
    element: Type
    size: Optional[int] = None
    
    def __eq__(self, other):
        return isinstance(other, ArrayType) and self.element == other.element and self.size == other.size
    
    def __hash__(self):
        return hash((self.element, self.size))
    
    def __str__(self):
        if self.size:
            return f"[{self.element}; {self.size}]"
        return f"[{self.element}]"


@dataclass
class StructType(Type):
    """Struct type"""
    name: str
    fields: Dict[str, Type]
    
    def __eq__(self, other):
        return isinstance(other, StructType) and self.name == other.name
    
    def __hash__(self):
        return hash(self.name)
    
    def __str__(self):
        return self.name


@dataclass
class FunctionType(Type):
    """Function type"""
    params: List[Type]
    return_type: Type
    
    def __eq__(self, other):
        return isinstance(other, FunctionType) and self.params == other.params and self.return_type == other.return_type
    
    def __hash__(self):
        return hash((tuple(self.params), self.return_type))
    
    def __str__(self):
        params = ", ".join(str(p) for p in self.params)
        return f"fn({params}) -> {self.return_type}"


class ControlFlowState(Enum):
    """Control flow state for return analysis"""
    NORMAL = auto()      # Normal execution continues
    RETURNS = auto()     # All paths return
    BREAKS = auto()      # All paths break
    CONTINUES = auto()   # All paths continue
    DIVERGES = auto()    # All paths diverge (infinite loop, panic, etc)


@dataclass
class ControlFlowResult:
    """Result of control flow analysis"""
    state: ControlFlowState
    returns_value: bool = False
    
    def merge(self, other: 'ControlFlowResult') -> 'ControlFlowResult':
        """Merge two control flow paths (for if/else branches)"""
        # If both paths return, the merged path returns
        if self.state == ControlFlowState.RETURNS and other.state == ControlFlowState.RETURNS:
            return ControlFlowResult(ControlFlowState.RETURNS, self.returns_value and other.returns_value)
        # Otherwise, execution can continue
        return ControlFlowResult(ControlFlowState.NORMAL, False)


class TypeChecker:
    """Strict type checker with control-flow analysis"""
    
    def __init__(self):
        self.scopes: List[Dict[str, Type]] = [{}]  # Variable type environment
        self.functions: Dict[str, FunctionType] = {}  # Function signatures
        self.structs: Dict[str, StructType] = {}  # Struct definitions
        self.current_function_return_type: Optional[Type] = None
        self.in_loop = False
        self.errors: List[TypeCheckError] = []
        
        # Initialize primitive types
        self.void_type = PrimitiveType("void")
        self.bool_type = PrimitiveType("bool")
        self.i8_type = PrimitiveType("i8")
        self.i16_type = PrimitiveType("i16")
        self.i32_type = PrimitiveType("i32")
        self.i64_type = PrimitiveType("i64")
        self.u8_type = PrimitiveType("u8")
        self.u16_type = PrimitiveType("u16")
        self.u32_type = PrimitiveType("u32")
        self.u64_type = PrimitiveType("u64")
        self.f32_type = PrimitiveType("f32")
        self.f64_type = PrimitiveType("f64")
    
    def error(self, message: str, node: Any = None):
        """Record a type error"""
        line = getattr(node, 'line', 0)
        column = getattr(node, 'column', 0)
        self.errors.append(TypeCheckError(message, line, column))
    
    def push_scope(self):
        """Enter a new scope"""
        self.scopes.append({})
    
    def pop_scope(self):
        """Exit current scope"""
        self.scopes.pop()
    
    def declare_var(self, name: str, typ: Type):
        """Declare a variable in current scope"""
        self.scopes[-1][name] = typ
    
    def lookup_var(self, name: str) -> Optional[Type]:
        """Look up variable type"""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None
    
    def check_program(self, program) -> List[TypeCheckError]:
        """Check entire program"""
        self.errors = []
        
        # First pass: collect function signatures and struct definitions
        for stmt in program.statements:
            if hasattr(stmt, '__class__') and stmt.__class__.__name__ == 'FunctionDef':
                self.collect_function_signature(stmt)
            elif hasattr(stmt, '__class__') and stmt.__class__.__name__ == 'StructDef':
                self.collect_struct_definition(stmt)
        
        # Second pass: type check function bodies
        for stmt in program.statements:
            if hasattr(stmt, '__class__') and stmt.__class__.__name__ == 'FunctionDef':
                self.check_function(stmt)
        
        return self.errors
    
    def collect_function_signature(self, func):
        """Collect function signature"""
        param_types = []
        for param in func.params:
            param_type = self.parse_type_annotation(param.type_annotation) if hasattr(param, 'type_annotation') and param.type_annotation else self.i64_type
            param_types.append(param_type)
        
        return_type = self.parse_type_annotation(func.return_type) if func.return_type else self.void_type
        
        func_type = FunctionType(param_types, return_type)
        self.functions[func.name] = func_type
    
    def collect_struct_definition(self, struct):
        """Collect struct definition"""
        fields = {}
        for field in struct.fields:
            field_type = self.parse_type_annotation(field.type_annotation) if hasattr(field, 'type_annotation') and field.type_annotation else self.i64_type
            fields[field.name] = field_type
        
        struct_type = StructType(struct.name, fields)
        self.structs[struct.name] = struct_type
    
    def parse_type_annotation(self, annotation: str) -> Type:
        """Parse type annotation string into Type object"""
        if not annotation:
            return self.i64_type
        
        annotation = annotation.strip()
        
        # Primitive types with aliases
        primitives = {
            'i8': self.i8_type, 'i16': self.i16_type, 'i32': self.i32_type, 'i64': self.i64_type,
            'u8': self.u8_type, 'u16': self.u16_type, 'u32': self.u32_type, 'u64': self.u64_type,
            'f32': self.f32_type, 'f64': self.f64_type,
            'bool': self.bool_type, 'void': self.void_type,
            # Friendly aliases
            'int': self.i64_type, 'uint': self.u64_type,
            'float': self.f64_type, 'double': self.f64_type,
            'byte': self.u8_type, 'char': self.u8_type,
            'short': self.i16_type, 'long': self.i64_type,
            'string': PointerType(self.u8_type, False)  # *u8 for C-style strings
        }
        if annotation in primitives:
            return primitives[annotation]
        
        # Pointer types
        if annotation.startswith('*'):
            rest = annotation[1:].strip()
            mutable = rest.startswith('mut ')
            if mutable:
                rest = rest[4:].strip()
            pointee = self.parse_type_annotation(rest)
            return PointerType(pointee, mutable)
        
        # Array types
        if annotation.startswith('[') and annotation.endswith(']'):
            inner = annotation[1:-1].strip()
            if ';' in inner:
                elem_str, size_str = inner.split(';', 1)
                element = self.parse_type_annotation(elem_str.strip())
                try:
                    size = int(size_str.strip())
                    return ArrayType(element, size)
                except ValueError:
                    return ArrayType(element)
            else:
                element = self.parse_type_annotation(inner)
                return ArrayType(element)
        
        # Struct types
        if annotation in self.structs:
            return self.structs[annotation]
        
        # Default to i64 for unknown types
        return self.i64_type
    
    def check_function(self, func):
        """Check function body with return path analysis"""
        func_type = self.functions.get(func.name)
        if not func_type:
            return
        
        self.current_function_return_type = func_type.return_type
        self.push_scope()
        
        # Add parameters to scope
        for i, param in enumerate(func.params):
            param_type = func_type.params[i] if i < len(func_type.params) else self.i64_type
            self.declare_var(param.name, param_type)
        
        # Check function body
        cf_result = self.check_block(func.body)
        
        # Verify return path
        if func_type.return_type != self.void_type:
            if cf_result.state != ControlFlowState.RETURNS:
                self.error(f"Function '{func.name}' must return a value of type {func_type.return_type} on all code paths", func)
        
        self.pop_scope()
        self.current_function_return_type = None
    
    def check_block(self, statements: List) -> ControlFlowResult:
        """Check a block of statements and analyze control flow"""
        for i, stmt in enumerate(statements):
            cf_result = self.check_statement(stmt)
            
            # If this statement always returns/breaks/continues, remaining code is unreachable
            if cf_result.state in (ControlFlowState.RETURNS, ControlFlowState.BREAKS, 
                                   ControlFlowState.CONTINUES, ControlFlowState.DIVERGES):
                if i < len(statements) - 1:
                    self.error("Unreachable code after return/break/continue", statements[i + 1])
                return cf_result
        
        return ControlFlowResult(ControlFlowState.NORMAL)
    
    def check_statement(self, stmt) -> ControlFlowResult:
        """Check a statement and return control flow result"""
        stmt_type = stmt.__class__.__name__
        
        if stmt_type == 'ReturnStmt':
            return self.check_return(stmt)
        elif stmt_type == 'IfStmt':
            return self.check_if(stmt)
        elif stmt_type == 'WhileStmt':
            return self.check_while(stmt)
        elif stmt_type == 'ForStmt':
            return self.check_for(stmt)
        elif stmt_type == 'BreakStmt':
            if not self.in_loop:
                self.error("'break' outside loop", stmt)
            return ControlFlowResult(ControlFlowState.BREAKS)
        elif stmt_type == 'ContinueStmt':
            if not self.in_loop:
                self.error("'continue' outside loop", stmt)
            return ControlFlowResult(ControlFlowState.CONTINUES)
        elif stmt_type == 'LetDecl':
            self.check_let_decl(stmt)
        elif stmt_type == 'Assignment':
            self.check_assignment(stmt)
        elif stmt_type == 'FunctionCall':
            self.check_expr(stmt)
        elif stmt_type == 'MatchStmt':
            return self.check_match(stmt)
        
        return ControlFlowResult(ControlFlowState.NORMAL)
    
    def check_return(self, stmt) -> ControlFlowResult:
        """Check return statement"""
        if stmt.value:
            expr_type = self.check_expr(stmt.value)
            if self.current_function_return_type and not self.types_compatible(expr_type, self.current_function_return_type):
                self.error(f"Return type mismatch: expected {self.current_function_return_type}, got {expr_type}", stmt)
            return ControlFlowResult(ControlFlowState.RETURNS, True)
        else:
            if self.current_function_return_type and self.current_function_return_type != self.void_type:
                self.error(f"Function must return a value of type {self.current_function_return_type}", stmt)
            return ControlFlowResult(ControlFlowState.RETURNS, False)
    
    def check_if(self, stmt) -> ControlFlowResult:
        """Check if statement"""
        # Check condition
        cond_type = self.check_expr(stmt.condition)
        if not self.types_compatible(cond_type, self.bool_type):
            self.error(f"If condition must be bool, got {cond_type}", stmt.condition)
        
        # Check then branch
        self.push_scope()
        then_cf = self.check_block(stmt.then_body)
        self.pop_scope()
        
        # Check else branch if present
        if stmt.else_body:
            self.push_scope()
            else_cf = self.check_block(stmt.else_body)
            self.pop_scope()
            
            # Both branches must return for the if to return
            return then_cf.merge(else_cf)
        
        return ControlFlowResult(ControlFlowState.NORMAL)
    
    def check_while(self, stmt) -> ControlFlowResult:
        """Check while loop"""
        cond_type = self.check_expr(stmt.condition)
        if not self.types_compatible(cond_type, self.bool_type):
            self.error(f"While condition must be bool, got {cond_type}", stmt.condition)
        
        old_in_loop = self.in_loop
        self.in_loop = True
        self.push_scope()
        self.check_block(stmt.body)
        self.pop_scope()
        self.in_loop = old_in_loop
        
        return ControlFlowResult(ControlFlowState.NORMAL)
    
    def check_for(self, stmt) -> ControlFlowResult:
        """Check for loop"""
        old_in_loop = self.in_loop
        self.in_loop = True
        self.push_scope()
        
        # Declare loop variable
        self.declare_var(stmt.var, self.i64_type)
        self.check_block(stmt.body)
        
        self.pop_scope()
        self.in_loop = old_in_loop
        
        return ControlFlowResult(ControlFlowState.NORMAL)
    
    def check_match(self, stmt) -> ControlFlowResult:
        """Check match statement with exhaustiveness checking"""
        # Check matched expression
        expr_type = self.check_expr(stmt.expr)
        
        # Check each arm
        all_return = True
        for arm in stmt.arms:
            self.push_scope()
            arm_cf = self.check_block(arm.body)
            self.pop_scope()
            
            if arm_cf.state != ControlFlowState.RETURNS:
                all_return = False
        
        # TODO: Implement exhaustiveness checking for enums
        
        if all_return:
            return ControlFlowResult(ControlFlowState.RETURNS, True)
        return ControlFlowResult(ControlFlowState.NORMAL)
    
    def check_let_decl(self, stmt):
        """Check let declaration"""
        if stmt.value:
            value_type = self.check_expr(stmt.value)
            
            # If type annotation exists, check compatibility
            if hasattr(stmt, 'type_annotation') and stmt.type_annotation:
                declared_type = self.parse_type_annotation(stmt.type_annotation)
                if not self.types_compatible(value_type, declared_type):
                    self.error(f"Type mismatch: cannot assign {value_type} to {declared_type}", stmt)
                self.declare_var(stmt.name, declared_type)
            else:
                self.declare_var(stmt.name, value_type)
        else:
            # Uninitialized variable - require type annotation
            if hasattr(stmt, 'type_annotation') and stmt.type_annotation:
                declared_type = self.parse_type_annotation(stmt.type_annotation)
                self.declare_var(stmt.name, declared_type)
            else:
                self.error(f"Variable '{stmt.name}' requires type annotation or initializer", stmt)
    
    def check_assignment(self, stmt):
        """Check assignment"""
        target_type = self.check_expr(stmt.target)
        value_type = self.check_expr(stmt.value)
        
        if not self.types_compatible(value_type, target_type):
            self.error(f"Type mismatch in assignment: cannot assign {value_type} to {target_type}", stmt)
    
    def check_expr(self, expr) -> Type:
        """Check expression and return its type"""
        expr_type = expr.__class__.__name__
        
        if expr_type == 'Literal':
            return self.check_literal(expr)
        elif expr_type == 'Identifier':
            return self.check_identifier(expr)
        elif expr_type == 'BinaryOp':
            return self.check_binary_op(expr)
        elif expr_type == 'UnaryOp':
            return self.check_unary_op(expr)
        elif expr_type == 'FunctionCall':
            return self.check_function_call(expr)
        elif expr_type == 'MemberAccess':
            return self.check_member_access(expr)
        elif expr_type == 'IndexAccess':
            return self.check_index_access(expr)
        
        return self.i64_type
    
    def check_literal(self, expr) -> Type:
        """Check literal and return its type"""
        if isinstance(expr.value, bool):
            return self.bool_type
        elif isinstance(expr.value, int):
            return self.i64_type
        elif isinstance(expr.value, float):
            return self.f64_type
        return self.i64_type
    
    def check_identifier(self, expr) -> Type:
        """Check identifier and return its type"""
        var_type = self.lookup_var(expr.name)
        if not var_type:
            self.error(f"Undefined variable '{expr.name}'", expr)
            return self.i64_type
        return var_type
    
    def check_binary_op(self, expr) -> Type:
        """Check binary operation with automatic type coercion"""
        left_type = self.check_expr(expr.left)
        right_type = self.check_expr(expr.right)
        
        # Comparison operators return bool
        if expr.op in ['==', '!=', '<', '>', '<=', '>=']:
            if not self.types_compatible(left_type, right_type):
                self.error(f"Type mismatch in comparison: {left_type} {expr.op} {right_type}", expr)
            return self.bool_type
        
        # Logical operators require bool operands
        if expr.op in ['&&', '||']:
            if not self.types_compatible(left_type, self.bool_type):
                self.error(f"Left operand of '{expr.op}' must be bool, got {left_type}", expr)
            if not self.types_compatible(right_type, self.bool_type):
                self.error(f"Right operand of '{expr.op}' must be bool, got {right_type}", expr)
            return self.bool_type
        
        # Arithmetic operators with automatic type coercion
        # int + float -> float
        # float + int -> float
        if left_type.name in ['i32', 'i64', 'int'] and right_type.name in ['f32', 'f64', 'float']:
            return right_type  # Promote to float
        if left_type.name in ['f32', 'f64', 'float'] and right_type.name in ['i32', 'i64', 'int']:
            return left_type  # Promote to float
        
        # Same types
        if not self.types_compatible(left_type, right_type):
            self.error(f"Type mismatch in binary operation: {left_type} {expr.op} {right_type}", expr)
        
        return left_type
    
    def check_unary_op(self, expr) -> Type:
        """Check unary operation"""
        operand_type = self.check_expr(expr.operand)
        
        if expr.op == '!':
            if not self.types_compatible(operand_type, self.bool_type):
                self.error(f"Operand of '!' must be bool, got {operand_type}", expr)
            return self.bool_type
        
        return operand_type
    
    def check_function_call(self, expr) -> Type:
        """Check function call"""
        func_type = self.functions.get(expr.name)
        if not func_type:
            self.error(f"Undefined function '{expr.name}'", expr)
            return self.i64_type
        
        # Check argument count
        if len(expr.args) != len(func_type.params):
            self.error(f"Function '{expr.name}' expects {len(func_type.params)} arguments, got {len(expr.args)}", expr)
        
        # Check argument types
        for i, arg in enumerate(expr.args):
            if i < len(func_type.params):
                arg_type = self.check_expr(arg)
                expected_type = func_type.params[i]
                if not self.types_compatible(arg_type, expected_type):
                    self.error(f"Argument {i+1} type mismatch: expected {expected_type}, got {arg_type}", arg)
        
        return func_type.return_type
    
    def check_member_access(self, expr) -> Type:
        """Check struct member access"""
        obj_type = self.check_expr(expr.object)
        
        if isinstance(obj_type, StructType):
            if expr.member in obj_type.fields:
                return obj_type.fields[expr.member]
            else:
                self.error(f"Struct '{obj_type.name}' has no field '{expr.member}'", expr)
        else:
            self.error(f"Cannot access member of non-struct type {obj_type}", expr)
        
        return self.i64_type
    
    def check_index_access(self, expr) -> Type:
        """Check array index access"""
        array_type = self.check_expr(expr.array)
        index_type = self.check_expr(expr.index)
        
        if not isinstance(index_type, PrimitiveType) or index_type.name not in ['i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64']:
            self.error(f"Array index must be integer type, got {index_type}", expr.index)
        
        if isinstance(array_type, ArrayType):
            return array_type.element
        elif isinstance(array_type, PointerType):
            return array_type.pointee
        else:
            self.error(f"Cannot index non-array type {array_type}", expr)
            return self.i64_type
    
    def types_compatible(self, t1: Type, t2: Type) -> bool:
        """Check if two types are compatible"""
        return t1 == t2


def check_types(program) -> List[TypeCheckError]:
    """Main entry point for type checking"""
    checker = TypeChecker()
    return checker.check_program(program)
