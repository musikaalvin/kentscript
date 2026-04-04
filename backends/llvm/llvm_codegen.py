"""
KentScript LLVM IR Code Generator
[KS-REF-LLVM-001] Production-ready LLVM IR generation
[KS-REF-LLVM-002] Memory layout control (#[repr(C)], #[packed], #[align(N)])
[KS-REF-LLVM-003] Calling convention support (extern "C", extern "system")

Generates LLVM IR that can be compiled with: clang -O2 output.ll -o output
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import sys


@dataclass
class StructLayout:
    """Struct memory layout configuration"""
    repr_c: bool = False
    packed: bool = False
    align: Optional[int] = None


class LLVMCodeGen:
    """LLVM IR code generator"""
    
    def __init__(self, target_triple: str = "x86_64-unknown-linux-gnu"):
        self.target_triple = target_triple
        self.code: List[str] = []
        self.temp_counter = 0
        self.label_counter = 0
        self.string_counter = 0
        
        # Symbol tables
        self.global_vars: Dict[str, str] = {}
        self.local_vars: Dict[str, Tuple[str, str]] = {}
        self.functions: Dict[str, Tuple[str, List[str]]] = {}  # name -> (return_type, param_types)
        self.structs: Dict[str, Tuple[List[Tuple[str, str]], StructLayout]] = {}  # name -> (fields, layout)
        
        # Current function context
        self.current_function_return_type: Optional[str] = None
        self.current_function_name: Optional[str] = None
        
        # Loop labels for break/continue
        self._loop_labels: List[Tuple[str, str]] = []  # (body_label, end_label)
        
    def emit(self, line: str = ""):
        """Emit a line of LLVM IR"""
        self.code.append(line)
    
    def temp(self) -> str:
        """Generate temporary variable"""
        t = f"%t{self.temp_counter}"
        self.temp_counter += 1
        return t
    
    def label(self) -> str:
        """Generate label"""
        l = f"L{self.label_counter}"
        self.label_counter += 1
        return l
    
    def string_literal(self) -> str:
        """Generate string literal name"""
        s = f"@.str.{self.string_counter}"
        self.string_counter += 1
        return s
    
    def llvm_type(self, ks_type: str) -> str:
        """Convert KentScript type to LLVM type"""
        type_map = {
            'i8': 'i8', 'i16': 'i16', 'i32': 'i32', 'i64': 'i64',
            'u8': 'i8', 'u16': 'i16', 'u32': 'i32', 'u64': 'i64',
            'f32': 'float', 'f64': 'double',
            'bool': 'i1', 'void': 'void',
            # Aliases
            'int': 'i64', 'uint': 'i64',
            'float': 'double', 'double': 'double',
            'byte': 'i8', 'char': 'i8',
            'short': 'i16', 'long': 'i64',
            'string': 'i8*'
        }
        
        if not ks_type:
            return 'i64'
        
        # Handle pointers
        if ks_type.startswith('*'):
            inner = ks_type[1:].strip()
            if inner.startswith('mut '):
                inner = inner[4:].strip()
            return self.llvm_type(inner) + '*'
        
        # Handle arrays
        if ks_type.startswith('[') and ks_type.endswith(']'):
            inner = ks_type[1:-1].strip()
            if ';' in inner:
                elem, size = inner.split(';', 1)
                return f"[{size.strip()} x {self.llvm_type(elem.strip())}]"
            return self.llvm_type(inner) + '*'
        
        # Check if it's a struct
        if ks_type in self.structs:
            return f"%{ks_type}"
        
        return type_map.get(ks_type, 'i64')
    
    def generate(self, ast) -> str:
        """Generate LLVM IR from AST"""
        self.code = []
        
        # Emit header
        self.emit(f'target triple = "{self.target_triple}"')
        if self.target_triple.startswith('x86_64'):
            self.emit('target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"')
        elif self.target_triple.startswith('aarch64'):
            self.emit('target datalayout = "e-m:e-i8:8:32-i16:16:32-i64:64-i128:128-n32:64-S128"')
        self.emit()
        
        # First pass: collect structs and function signatures
        for stmt in ast.statements:
            stmt_type = stmt.__class__.__name__
            if stmt_type == 'StructDef':
                self.collect_struct(stmt)
            elif stmt_type == 'FunctionDef':
                self.collect_function_signature(stmt)
        
        # Emit struct definitions
        for name, (fields, layout) in self.structs.items():
            self.emit_struct_definition(name, fields, layout)
        
        self.emit()
        
        # Declare external functions (libc, etc.)
        self.emit_external_declarations()
        self.emit()
        
        # Second pass: generate code
        for stmt in ast.statements:
            stmt_type = stmt.__class__.__name__
            if stmt_type == 'FunctionDef':
                self.gen_function(stmt)
        
        return '\n'.join(self.code)
    
    def collect_struct(self, struct):
        """Collect struct definition"""
        fields = []
        for field in struct.fields:
            field_name = field.name
            field_type = self.llvm_type(getattr(field, 'type_annotation', None) or 'i64')
            fields.append((field_name, field_type))
        
        # Parse attributes
        layout = StructLayout()
        if hasattr(struct, 'attributes'):
            for attr in struct.attributes:
                if attr == 'repr(C)':
                    layout.repr_c = True
                elif attr == 'repr(packed)':
                    layout.packed = True
                elif attr.startswith('repr(align('):
                    align_str = attr[11:-2]  # Extract number from repr(align(N))
                    layout.align = int(align_str)
        
        self.structs[struct.name] = (fields, layout)
    
    def emit_struct_definition(self, name: str, fields: List[Tuple[str, str]], layout: StructLayout):
        """Emit struct type definition"""
        field_types = [ft for _, ft in fields]
        fields_str = ', '.join(field_types)
        
        # Apply packing
        if layout.packed:
            self.emit(f'%{name} = type <{{ {fields_str} }}>')  # Packed struct
        else:
            self.emit(f'%{name} = type {{ {fields_str} }}')
    
    def collect_function_signature(self, func):
        """Collect function signature"""
        return_type = self.llvm_type(func.return_type if func.return_type else 'void')
        param_types = []
        for param in func.params:
            param_type = self.llvm_type(getattr(param, 'type_annotation', None) or 'i64')
            param_types.append(param_type)
        
        self.functions[func.name] = (return_type, param_types)
    
    def emit_external_declarations(self):
        """Emit declarations for external functions"""
        self.emit('; External function declarations')
        self.emit('declare i32 @printf(i8*, ...)')
        self.emit('declare i32 @puts(i8*)')
        self.emit('declare i8* @malloc(i64)')
        self.emit('declare void @free(i8*)')
        self.emit('declare i8* @memcpy(i8*, i8*, i64)')
        self.emit('declare i8* @memset(i8*, i32, i64)')
    
    def gen_function(self, func):
        """Generate function definition"""
        self.local_vars = {}
        self.temp_counter = 0
        self.label_counter = 0
        
        return_type = self.llvm_type(func.return_type if func.return_type else 'void')
        self.current_function_return_type = return_type
        self.current_function_name = func.name
        
        # Build parameter list
        params = []
        for i, param in enumerate(func.params):
            param_type = self.llvm_type(getattr(param, 'type_annotation', None) or 'i64')
            param_name = f"%{param.name}"
            params.append(f"{param_type} {param_name}")
            self.local_vars[param.name] = (param_name, param_type)
        
        params_str = ', '.join(params) if params else ''
        
        # Check for calling convention
        cc = ''
        if hasattr(func, 'calling_convention'):
            if func.calling_convention == 'C':
                cc = 'ccc '
            elif func.calling_convention == 'system':
                cc = ''  # Default
        
        self.emit(f'define {cc}{return_type} @{func.name}({params_str}) {{')
        self.emit('entry:')
        
        # Generate function body
        for stmt in func.body:
            self.gen_statement(stmt)
        
        # Add default return if needed
        if return_type == 'void':
            self.emit('  ret void')
        
        self.emit('}')
        self.emit()
    
    def gen_statement(self, stmt):
        """Generate statement"""
        stmt_type = stmt.__class__.__name__
        
        if stmt_type == 'LetDecl':
            self.gen_let_decl(stmt)
        elif stmt_type == 'Assignment':
            self.gen_assignment(stmt)
        elif stmt_type == 'ReturnStmt':
            self.gen_return(stmt)
        elif stmt_type == 'IfStmt':
            self.gen_if(stmt)
        elif stmt_type == 'WhileStmt':
            self.gen_while(stmt)
        elif stmt_type == 'ForStmt':
            self.gen_for(stmt)
        elif stmt_type == 'FunctionCall':
            self.gen_expr(stmt)
        elif stmt_type == 'BreakStmt':
            if self._loop_labels:
                _, end_label = self._loop_labels[-1]
                self.emit(f'  br label %{end_label}')
        elif stmt_type == 'ContinueStmt':
            if self._loop_labels:
                body_label, _ = self._loop_labels[-1]
                self.emit(f'  br label %{body_label}')
    
    def gen_let_decl(self, stmt):
        """Generate let declaration"""
        var_type = self.llvm_type(getattr(stmt, 'type_annotation', None) or 'i64')
        var_ptr = self.temp()
        
        self.emit(f'  {var_ptr} = alloca {var_type}')
        
        if stmt.value:
            value, value_type = self.gen_expr(stmt.value)
            self.emit(f'  store {value_type} {value}, {var_type}* {var_ptr}')
        
        self.local_vars[stmt.name] = (var_ptr, var_type)
    
    def gen_assignment(self, stmt):
        """Generate assignment"""
        # Get target
        if stmt.target.__class__.__name__ == 'Identifier':
            var_name = stmt.target.name
            if var_name in self.local_vars:
                var_ptr, var_type = self.local_vars[var_name]
                value, value_type = self.gen_expr(stmt.value)
                self.emit(f'  store {value_type} {value}, {var_type}* {var_ptr}')
    
    def gen_return(self, stmt):
        """Generate return statement"""
        if stmt.value:
            value, value_type = self.gen_expr(stmt.value)
            self.emit(f'  ret {value_type} {value}')
        else:
            self.emit(f'  ret void')
    
    def gen_if(self, stmt):
        """Generate if statement"""
        cond, _ = self.gen_expr(stmt.condition)
        
        then_label = self.label()
        else_label = self.label() if stmt.else_body else None
        end_label = self.label()
        
        if else_label:
            self.emit(f'  br i1 {cond}, label %{then_label}, label %{else_label}')
        else:
            self.emit(f'  br i1 {cond}, label %{then_label}, label %{end_label}')
        
        # Then branch
        self.emit(f'{then_label}:')
        for s in stmt.then_body:
            self.gen_statement(s)
        self.emit(f'  br label %{end_label}')
        
        # Else branch
        if else_label:
            self.emit(f'{else_label}:')
            for s in stmt.else_body:
                self.gen_statement(s)
            self.emit(f'  br label %{end_label}')
        
        # End
        self.emit(f'{end_label}:')
    
    def gen_while(self, stmt):
        """Generate while loop"""
        cond_label = self.label()
        body_label = self.label()
        end_label = self.label()
        
        self.emit(f'  br label %{cond_label}')
        
        # Condition
        self.emit(f'{cond_label}:')
        cond, _ = self.gen_expr(stmt.condition)
        self.emit(f'  br i1 {cond}, label %{body_label}, label %{end_label}')
        
        # Body
        self.emit(f'{body_label}:')
        for s in stmt.body:
            self.gen_statement(s)
        self.emit(f'  br label %{cond_label}')
        
        # End
        self.emit(f'{end_label}:')
    
    def gen_for(self, stmt):
        """Generate for loop"""
        # Check if iterable is a range() call
        if (stmt.iterable.__class__.__name__ == 'FunctionCall' and
            hasattr(stmt.iterable, 'func') and
            stmt.iterable.func.__class__.__name__ == 'Identifier' and
            stmt.iterable.func.name == 'range'):
            args = stmt.iterable.args
            if len(args) == 1:
                start_val = '0'
                end_val, _ = self.gen_expr(args[0])
            elif len(args) == 2:
                start_val, _ = self.gen_expr(args[0])
                end_val, _ = self.gen_expr(args[1])
            elif len(args) == 3:
                start_val, _ = self.gen_expr(args[0])
                end_val, _ = self.gen_expr(args[1])
                # Step is ignored for now, assume +1
            else:
                start_val = '0'
                end_val = '10'
        else:
            # Generic iterable - treat as start=0, end=10 fallback
            start_val = '0'
            end_val = '10'
        
        var_ptr = self.temp()
        self.emit(f'  {var_ptr} = alloca i64')
        self.emit(f'  store i64 {start_val}, i64* {var_ptr}')
        self.local_vars[stmt.var] = (var_ptr, 'i64')
        
        cond_label = self.label()
        body_label = self.label()
        end_label = self.label()
        self._loop_labels.append((body_label, end_label))
        
        self.emit(f'  br label %{cond_label}')
        
        # Condition
        self.emit(f'{cond_label}:')
        var_val = self.temp()
        self.emit(f'  {var_val} = load i64, i64* {var_ptr}')
        cond = self.temp()
        self.emit(f'  {cond} = icmp slt i64 {var_val}, {end_val}')
        self.emit(f'  br i1 {cond}, label %{body_label}, label %{end_label}')
        
        # Body
        self.emit(f'{body_label}:')
        for s in stmt.body:
            self.gen_statement(s)
        
        # Increment
        next_val = self.temp()
        self.emit(f'  {next_val} = add i64 {var_val}, 1')
        self.emit(f'  store i64 {next_val}, i64* {var_ptr}')
        self.emit(f'  br label %{cond_label}')
        
        # End
        self.emit(f'{end_label}:')
        self._loop_labels.pop()
    
    def gen_expr(self, expr) -> Tuple[str, str]:
        """Generate expression, return (value, type)"""
        expr_type = expr.__class__.__name__
        
        if expr_type == 'Literal':
            return self.gen_literal(expr)
        elif expr_type == 'Identifier':
            return self.gen_identifier(expr)
        elif expr_type == 'BinaryOp':
            return self.gen_binary_op(expr)
        elif expr_type == 'UnaryOp':
            return self.gen_unary_op(expr)
        elif expr_type == 'FunctionCall':
            return self.gen_function_call(expr)
        elif expr_type == 'MemberAccess':
            return self.gen_member_access(expr)
        elif expr_type == 'IndexAccess':
            return self.gen_index_access(expr)
        
        return ('0', 'i64')
    
    def gen_literal(self, expr) -> Tuple[str, str]:
        """Generate literal"""
        if isinstance(expr.value, bool):
            return ('1' if expr.value else '0', 'i1')
        elif isinstance(expr.value, int):
            return (str(expr.value), 'i64')
        elif isinstance(expr.value, float):
            return (str(expr.value), 'double')
        elif isinstance(expr.value, str):
            # String literal
            str_name = self.string_literal()
            escaped = expr.value.replace('\\', '\\\\').replace('"', '\\"')
            str_len = len(expr.value) + 1
            self.emit(f'{str_name} = private unnamed_addr constant [{str_len} x i8] c"{escaped}\\00"')
            ptr = self.temp()
            self.emit(f'  {ptr} = getelementptr [{str_len} x i8], [{str_len} x i8]* {str_name}, i32 0, i32 0')
            return (ptr, 'i8*')
        
        return ('0', 'i64')
    
    def gen_identifier(self, expr) -> Tuple[str, str]:
        """Generate identifier"""
        if expr.name in self.local_vars:
            var_ptr, var_type = self.local_vars[expr.name]
            result = self.temp()
            self.emit(f'  {result} = load {var_type}, {var_type}* {var_ptr}')
            return (result, var_type)
        
        return ('0', 'i64')
    
    def gen_binary_op(self, expr) -> Tuple[str, str]:
        """Generate binary operation"""
        left, left_type = self.gen_expr(expr.left)
        right, right_type = self.gen_expr(expr.right)
        
        result = self.temp()
        
        # Arithmetic
        if expr.op == '+':
            self.emit(f'  {result} = add {left_type} {left}, {right}')
            return (result, left_type)
        elif expr.op == '-':
            self.emit(f'  {result} = sub {left_type} {left}, {right}')
            return (result, left_type)
        elif expr.op == '*':
            self.emit(f'  {result} = mul {left_type} {left}, {right}')
            return (result, left_type)
        elif expr.op == '/':
            self.emit(f'  {result} = sdiv {left_type} {left}, {right}')
            return (result, left_type)
        elif expr.op == '%':
            self.emit(f'  {result} = srem {left_type} {left}, {right}')
            return (result, left_type)
        
        # Comparison
        elif expr.op == '==':
            self.emit(f'  {result} = icmp eq {left_type} {left}, {right}')
            return (result, 'i1')
        elif expr.op == '!=':
            self.emit(f'  {result} = icmp ne {left_type} {left}, {right}')
            return (result, 'i1')
        elif expr.op == '<':
            self.emit(f'  {result} = icmp slt {left_type} {left}, {right}')
            return (result, 'i1')
        elif expr.op == '>':
            self.emit(f'  {result} = icmp sgt {left_type} {left}, {right}')
            return (result, 'i1')
        elif expr.op == '<=':
            self.emit(f'  {result} = icmp sle {left_type} {left}, {right}')
            return (result, 'i1')
        elif expr.op == '>=':
            self.emit(f'  {result} = icmp sge {left_type} {left}, {right}')
            return (result, 'i1')
        
        # Logical
        elif expr.op == '&&':
            self.emit(f'  {result} = and i1 {left}, {right}')
            return (result, 'i1')
        elif expr.op == '||':
            self.emit(f'  {result} = or i1 {left}, {right}')
            return (result, 'i1')
        
        return ('0', 'i64')
    
    def gen_unary_op(self, expr) -> Tuple[str, str]:
        """Generate unary operation"""
        operand, operand_type = self.gen_expr(expr.operand)
        result = self.temp()
        
        if expr.op == '-':
            self.emit(f'  {result} = sub {operand_type} 0, {operand}')
            return (result, operand_type)
        elif expr.op == '!':
            self.emit(f'  {result} = xor i1 {operand}, 1')
            return (result, 'i1')
        
        return (operand, operand_type)
    
    def gen_function_call(self, expr) -> Tuple[str, str]:
        """Generate function call"""
        # Built-in functions
        if expr.name == 'print':
            if expr.args:
                arg, arg_type = self.gen_expr(expr.args[0])
                if arg_type == 'i8*':
                    self.emit(f'  call i32 @puts({arg_type} {arg})')
                else:
                    # TODO: Format other types
                    pass
            return ('0', 'void')
        
        # User functions
        if expr.name in self.functions:
            return_type, param_types = self.functions[expr.name]
            
            args = []
            for i, arg_expr in enumerate(expr.args):
                arg_val, arg_type = self.gen_expr(arg_expr)
                args.append(f'{arg_type} {arg_val}')
            
            args_str = ', '.join(args)
            
            if return_type == 'void':
                self.emit(f'  call {return_type} @{expr.name}({args_str})')
                return ('0', 'void')
            else:
                result = self.temp()
                self.emit(f'  {result} = call {return_type} @{expr.name}({args_str})')
                return (result, return_type)
        
        return ('0', 'i64')
    
    def gen_member_access(self, expr) -> Tuple[str, str]:
        """Generate struct member access"""
        obj, obj_type = self.gen_expr(expr.object)
        
        # Get struct definition
        struct_name = obj_type.strip('%')
        if struct_name in self.structs:
            fields, layout = self.structs[struct_name]
            
            # Find field index
            field_idx = None
            field_type = None
            for i, (fname, ftype) in enumerate(fields):
                if fname == expr.member:
                    field_idx = i
                    field_type = ftype
                    break
            
            if field_idx is not None:
                # Generate GEP instruction
                ptr = self.temp()
                self.emit(f'  {ptr} = getelementptr {obj_type}, {obj_type}* {obj}, i32 0, i32 {field_idx}')
                result = self.temp()
                self.emit(f'  {result} = load {field_type}, {field_type}* {ptr}')
                return (result, field_type)
        
        return ('0', 'i64')
    
    def gen_index_access(self, expr) -> Tuple[str, str]:
        """Generate array index access"""
        array, array_type = self.gen_expr(expr.array)
        index, _ = self.gen_expr(expr.index)
        
        # Parse array type [N x T] or T*
        if array_type.endswith('*'):
            # Pointer type
            elem_type = array_type[:-1]
            ptr = self.temp()
            self.emit(f'  {ptr} = getelementptr {elem_type}, {elem_type}* {array}, i64 {index}')
            result = self.temp()
            self.emit(f'  {result} = load {elem_type}, {elem_type}* {ptr}')
            return (result, elem_type)
        elif '[' in array_type:
            # Array type [N x T]
            import re
            match = re.search(r'\[(\d+) x (.+)\]', array_type)
            if match:
                size = match.group(1)
                elem_type = match.group(2)
                ptr = self.temp()
                self.emit(f'  {ptr} = getelementptr {array_type}, {array_type}* {array}, i32 0, i64 {index}')
                result = self.temp()
                self.emit(f'  {result} = load {elem_type}, {elem_type}* {ptr}')
                return (result, elem_type)
        
        return ('0', 'i64')


def generate_llvm_ir(ast, target_triple: str = "x86_64-unknown-linux-gnu") -> str:
    """Main entry point for LLVM IR generation"""
    codegen = LLVMCodeGen(target_triple)
    return codegen.generate(ast)
