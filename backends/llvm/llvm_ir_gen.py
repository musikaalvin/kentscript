#!/usr/bin/env python3
"""
LLVM IR Code Generator for KentScript
Generates real LLVM IR from AST nodes
"""

from typing import Dict, List, Optional, Any, Tuple

class LLVMIRGenerator:
    """Generate LLVM IR from KentScript AST"""
    
    def __init__(self):
        self.ir_lines: List[str] = []
        self.temp_counter = 0
        self.label_counter = 0
        self.string_counter = 0
        self.local_vars: Dict[str, Tuple[str, str]] = {}
        self.func_sigs: Dict[str, Tuple[str, List[str]]] = {}
        self._loop_stack: List[Tuple[str, str]] = []
    
    def emit(self, line: str = ""):
        self.ir_lines.append(line)
    
    def temp(self) -> str:
        t = f"%t{self.temp_counter}"
        self.temp_counter += 1
        return t
    
    def label(self) -> str:
        l = f"L{self.label_counter}"
        self.label_counter += 1
        return l
    
    def str_name(self) -> str:
        s = f"@.str.{self.string_counter}"
        self.string_counter += 1
        return s
    
    def llvm_type(self, ks_type: str) -> str:
        m = {
            'i8': 'i8', 'i16': 'i16', 'i32': 'i32', 'i64': 'i64',
            'u8': 'i8', 'u16': 'i16', 'u32': 'i32', 'u64': 'i64',
            'f32': 'float', 'f64': 'double', 'bool': 'i1', 'void': 'void',
            'int': 'i64', 'uint': 'i64', 'float': 'double', 'double': 'double',
            'string': 'i8*', 'str': 'i8*', 'char': 'i8',
        }
        if not ks_type:
            return 'i64'
        if ks_type.startswith('*'):
            inner = ks_type[1:].strip()
            if inner.startswith('mut '):
                inner = inner[4:].strip()
            return self.llvm_type(inner) + '*'
        if ks_type.startswith('[') and ks_type.endswith(']'):
            inner = ks_type[1:-1].strip()
            if ';' in inner:
                elem, size = inner.split(';', 1)
                return f"[{size.strip()} x {self.llvm_type(elem.strip())}]"
            return self.llvm_type(inner) + '*'
        return m.get(ks_type, 'i64')
    
    def ks_value(self, val, vtype: str) -> str:
        if vtype in ('float', 'double'):
            return f"{float(val)}"
        if vtype == 'i1':
            return 'true' if val else 'false'
        return str(int(val))
    
    def generate_header(self):
        self.emit('; ModuleID = \'kentscript\'')
        self.emit('source_filename = "kentscript"')
        self.emit('target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"')
        self.emit('target triple = "x86_64-unknown-linux-gnu"')
        self.emit('')
        self.emit('; Declare printf')
        self.emit('declare i32 @printf(i8*, ...)')
        self.emit('')
    
    def gen_string_const(self, s: str) -> str:
        name = self.str_name()
        escaped = s.replace('\\', '\\5C').replace('"', '\\00')
        self.emit(f'{name} = private unnamed_addr constant [{len(s)+1} x i8] c"{escaped}\\00", align 1')
        return name
    
    def generate(self, ast) -> str:
        self.generate_header()
        
        # First pass: collect string literals and function signatures
        for node in ast:
            cls = node.__class__.__name__
            if cls == 'FunctionDef':
                ret = self.llvm_type(getattr(node, 'return_type', None) or 'void')
                params = []
                for p in getattr(node, 'params', []):
                    pname = p if isinstance(p, str) else getattr(p, 'name', p)
                    ptype = 'i64'
                    if hasattr(p, 'type_annotation') and p.type_annotation:
                        ptype = self.llvm_type(p.type_annotation)
                    params.append(ptype)
                self.func_sigs[node.name] = (ret, params)
        
        # Second pass: generate functions
        for node in ast:
            cls = node.__class__.__name__
            if cls == 'FunctionDef':
                self.gen_function(node)
        
        return "\n".join(self.ir_lines)
    
    def gen_function(self, func):
        ret = self.func_sigs.get(func.name, ('i64', []))[0]
        params_list = self.func_sigs.get(func.name, ('i64', []))[1]
        
        param_strs = []
        self.local_vars.clear()
        for i, p in enumerate(getattr(func, 'params', [])):
            pname = p if isinstance(p, str) else getattr(p, 'name', p)
            ptype = params_list[i] if i < len(params_list) else 'i64'
            param_strs.append(f"{ptype} %{pname}")
            self.local_vars[pname] = (f"%{pname}", ptype)
        
        params_str = ', '.join(param_strs)
        self.emit(f'define {ret} @{func.name}({params_str}) {{')
        self.emit('entry:')
        
        for stmt in getattr(func, 'body', []):
            self.gen_stmt(stmt)
        
        if ret == 'void':
            self.emit('  ret void')
        self.emit('}')
        self.emit('')
    
    def gen_stmt(self, stmt):
        cls = stmt.__class__.__name__
        
        if cls == 'LetDecl':
            self.gen_let(stmt)
        elif cls == 'Assignment':
            self.gen_assign(stmt)
        elif cls == 'ReturnStmt':
            self.gen_return(stmt)
        elif cls == 'IfStmt':
            self.gen_if(stmt)
        elif cls == 'WhileStmt':
            self.gen_while(stmt)
        elif cls == 'ForStmt':
            self.gen_for(stmt)
        elif cls == 'FunctionCall':
            self.gen_call(stmt)
        elif cls == 'BreakStmt':
            if self._loop_stack:
                self.emit(f'  br label %{self._loop_stack[-1][1]}')
        elif cls == 'ContinueStmt':
            if self._loop_stack:
                self.emit(f'  br label %{self._loop_stack[-1][0]}')
        elif cls == 'MatchStmt':
            self.gen_match(stmt)
        elif cls == 'UnsafeStmt':
            for s in getattr(stmt, 'body', []):
                self.gen_stmt(s)
    
    def gen_let(self, stmt):
        name = getattr(stmt, 'name', 'tmp')
        vtype = self.llvm_type(getattr(stmt, 'type_annotation', None) or 'i64')
        ptr = self.temp()
        self.emit(f'  {ptr} = alloca {vtype}')
        if hasattr(stmt, 'value') and stmt.value:
            val, vt = self.gen_expr(stmt.value)
            self.emit(f'  store {vt} {val}, {vtype}* {ptr}')
        self.local_vars[name] = (ptr, vtype)
    
    def gen_assign(self, stmt):
        target = getattr(stmt, 'target', None)
        if target and target.__class__.__name__ == 'Identifier':
            name = target.name
            if name in self.local_vars:
                ptr, vtype = self.local_vars[name]
                val, vt = self.gen_expr(stmt.value)
                self.emit(f'  store {vt} {val}, {vtype}* {ptr}')
    
    def gen_return(self, stmt):
        if hasattr(stmt, 'value') and stmt.value:
            val, vt = self.gen_expr(stmt.value)
            self.emit(f'  ret {vt} {val}')
        else:
            self.emit('  ret void')
    
    def gen_if(self, stmt):
        cond, _ = self.gen_expr(stmt.condition)
        then_lbl = self.label()
        else_lbl = self.label() if getattr(stmt, 'else_block', None) else None
        end_lbl = self.label()
        
        if else_lbl:
            self.emit(f'  br i1 {cond}, label %{then_lbl}, label %{else_lbl}')
        else:
            self.emit(f'  br i1 {cond}, label %{then_lbl}, label %{end_lbl}')
        
        self.emit(f'{then_lbl}:')
        for s in getattr(stmt, 'then_block', []):
            self.gen_stmt(s)
        self.emit(f'  br label %{end_lbl}')
        
        if else_lbl:
            self.emit(f'{else_lbl}:')
            for s in stmt.else_block:
                self.gen_stmt(s)
            self.emit(f'  br label %{end_lbl}')
        
        self.emit(f'{end_lbl}:')
    
    def gen_while(self, stmt):
        cond_lbl = self.label()
        body_lbl = self.label()
        end_lbl = self.label()
        self._loop_stack.append((body_lbl, end_lbl))
        
        self.emit(f'  br label %{cond_lbl}')
        self.emit(f'{cond_lbl}:')
        cond, _ = self.gen_expr(stmt.condition)
        self.emit(f'  br i1 {cond}, label %{body_lbl}, label %{end_lbl}')
        self.emit(f'{body_lbl}:')
        for s in getattr(stmt, 'body', []):
            self.gen_stmt(s)
        self.emit(f'  br label %{cond_lbl}')
        self.emit(f'{end_lbl}:')
        self._loop_stack.pop()
    
    def gen_for(self, stmt):
        iterable = getattr(stmt, 'iterable', None)
        var = getattr(stmt, 'var', 'i')
        
        if (iterable and iterable.__class__.__name__ == 'FunctionCall' and
            hasattr(iterable, 'func') and iterable.func.__class__.__name__ == 'Identifier' and
            iterable.func.name == 'range'):
            args = getattr(iterable, 'args', [])
            if len(args) == 1:
                start_v = '0'
                end_v, _ = self.gen_expr(args[0])
            elif len(args) == 2:
                start_v, _ = self.gen_expr(args[0])
                end_v, _ = self.gen_expr(args[1])
            else:
                start_v = '0'
                end_v = '10'
        else:
            start_v = '0'
            end_v = '10'
        
        ptr = self.temp()
        self.emit(f'  {ptr} = alloca i64')
        self.emit(f'  store i64 {start_v}, i64* {ptr}')
        self.local_vars[var] = (ptr, 'i64')
        
        cond_lbl = self.label()
        body_lbl = self.label()
        end_lbl = self.label()
        self._loop_stack.append((body_lbl, end_lbl))
        
        self.emit(f'  br label %{cond_lbl}')
        self.emit(f'{cond_lbl}:')
        cur = self.temp()
        self.emit(f'  {cur} = load i64, i64* {ptr}')
        cnd = self.temp()
        self.emit(f'  {cnd} = icmp slt i64 {cur}, {end_v}')
        self.emit(f'  br i1 {cnd}, label %{body_lbl}, label %{end_lbl}')
        self.emit(f'{body_lbl}:')
        for s in getattr(stmt, 'body', []):
            self.gen_stmt(s)
        nxt = self.temp()
        self.emit(f'  {nxt} = add i64 {cur}, 1')
        self.emit(f'  store i64 {nxt}, i64* {ptr}')
        self.emit(f'  br label %{cond_lbl}')
        self.emit(f'{end_lbl}:')
        self._loop_stack.pop()
    
    def gen_match(self, stmt):
        target, ttype = self.gen_expr(stmt.target)
        cases = getattr(stmt, 'cases', [])
        default = getattr(stmt, 'default', None)
        
        all_int = all(
            c.pattern.__class__.__name__ == 'NumberLiteral'
            for c in cases
        )
        
        if all_int:
            switch_lbl = self.label()
            end_lbl = self.label()
            self.emit(f'  switch {ttype} {target}, label %{end_lbl} [')
            case_lbls = []
            for c in cases:
                lbl = self.label()
                case_lbls.append(lbl)
                val, _ = self.gen_expr(c.pattern)
                self.emit(f'    {ttype} {val}, label %{lbl}')
            self.emit(f'  ]')
            
            for i, c in enumerate(cases):
                self.emit(f'{case_lbls[i]}:')
                for s in getattr(c, 'body', []):
                    self.gen_stmt(s)
                self.emit(f'  br label %{end_lbl}')
            if default:
                self.emit(f'{end_lbl}:')
                for s in default:
                    self.gen_stmt(s)
                self.emit(f'  br label %{self.label()}')
            else:
                self.emit(f'{end_lbl}:')
        else:
            end_lbl = self.label()
            for i, c in enumerate(cases):
                then_lbl = self.label()
                pat, _ = self.gen_expr(c.pattern)
                cmp = self.temp()
                self.emit(f'  {cmp} = icmp eq {ttype} {target}, {pat}')
                self.emit(f'  br i1 {cmp}, label %{then_lbl}, label %{end_lbl}')
                self.emit(f'{then_lbl}:')
                for s in getattr(c, 'body', []):
                    self.gen_stmt(s)
                self.emit(f'  br label %{end_lbl}')
                self.emit(f'{end_lbl}:')
            if default:
                for s in default:
                    self.gen_stmt(s)
    
    def gen_call(self, stmt):
        self.gen_expr(stmt)
    
    def gen_expr(self, expr) -> Tuple[str, str]:
        cls = expr.__class__.__name__
        
        if cls == 'NumberLiteral':
            val = getattr(expr, 'value', 0)
            return str(int(val)), 'i64'
        elif cls == 'StringLiteral':
            val = getattr(expr, 'value', '')
            sname = self.gen_string_const(val)
            ptr = self.temp()
            self.emit(f'  {ptr} = getelementptr [{len(val)+1} x i8], [{len(val)+1} x i8]* {sname}, i64 0, i64 0')
            return ptr, 'i8*'
        elif cls == 'BoolLiteral':
            val = 'true' if getattr(expr, 'value', False) else 'false'
            return val, 'i1'
        elif cls == 'Identifier':
            name = expr.name
            if name in self.local_vars:
                ptr, vtype = self.local_vars[name]
                tmp = self.temp()
                self.emit(f'  {tmp} = load {vtype}, {vtype}* {ptr}')
                return tmp, vtype
            return f'%{name}', 'i64'
        elif cls == 'BinaryOp':
            return self.gen_binop(expr)
        elif cls == 'UnaryOp':
            return self.gen_unary(expr)
        elif cls == 'FunctionCall':
            return self.gen_fncall(expr)
        else:
            return '0', 'i64'
    
    def gen_binop(self, expr) -> Tuple[str, str]:
        left, lt = self.gen_expr(expr.left)
        right, rt = self.gen_expr(expr.right)
        op = getattr(expr, 'op', '+')
        result = self.temp()
        
        int_ops = {'+', '-', '*', '/', '%', '&', '|', '^', '<<', '>>'}
        cmp_ops = {'==': 'eq', '!=': 'ne', '<': 'slt', '<=': 'sle', '>': 'sgt', '>=': 'sge'}
        logic_ops = {'&&': 'and', '||': 'or'}
        
        if op in cmp_ops:
            self.emit(f'  {result} = icmp {cmp_ops[op]} {lt} {left}, {right}')
            return result, 'i1'
        elif op in logic_ops:
            self.emit(f'  {result} = {logic_ops[op]} {lt} {left}, {right}')
            return result, lt
        elif op == '+':
            self.emit(f'  {result} = add {lt} {left}, {right}')
        elif op == '-':
            self.emit(f'  {result} = sub {lt} {left}, {right}')
        elif op == '*':
            self.emit(f'  {result} = mul {lt} {left}, {right}')
        elif op == '/':
            self.emit(f'  {result} = sdiv {lt} {left}, {right}')
        elif op == '%':
            self.emit(f'  {result} = srem {lt} {left}, {right}')
        elif op == '&':
            self.emit(f'  {result} = and {lt} {left}, {right}')
        elif op == '|':
            self.emit(f'  {result} = or {lt} {left}, {right}')
        elif op == '^':
            self.emit(f'  {result} = xor {lt} {left}, {right}')
        elif op == '<<':
            self.emit(f'  {result} = shl {lt} {left}, {right}')
        elif op == '>>':
            self.emit(f'  {result} = lshr {lt} {left}, {right}')
        else:
            self.emit(f'  {result} = add {lt} {left}, {right}')
        return result, lt
    
    def gen_unary(self, expr) -> Tuple[str, str]:
        val, vt = self.gen_expr(expr.operand)
        op = getattr(expr, 'op', '-')
        result = self.temp()
        if op == '-':
            self.emit(f'  {result} = sub {vt} 0, {val}')
        elif op == '!':
            self.emit(f'  {result} = xor {vt} {val}, 1')
        elif op == '~':
            self.emit(f'  {result} = xor {vt} {val}, -1')
        else:
            return val, vt
        return result, vt
    
    def gen_fncall(self, expr) -> Tuple[str, str]:
        func_name = ''
        if hasattr(expr, 'func'):
            f = expr.func
            if hasattr(f, 'name'):
                func_name = f.name
            elif f.__class__.__name__ == 'Identifier':
                func_name = f.name
        
        args = getattr(expr, 'args', [])
        arg_strs = []
        for a in args:
            v, t = self.gen_expr(a)
            arg_strs.append(f'{t} {v}')
        args_str = ', '.join(arg_strs)
        
        if func_name == 'print':
            fmt = self.gen_string_const('%lld\\n')
            fmt_ptr = self.temp()
            self.emit(f'  {fmt_ptr} = getelementptr [6 x i8], [6 x i8]* {fmt}, i64 0, i64 0')
            if args:
                v, _ = self.gen_expr(args[0])
                self.emit(f'  call i32 (i8*, ...) @printf(i8* {fmt_ptr}, i64 {v})')
            else:
                self.emit(f'  call i32 (i8*, ...) @printf(i8* {fmt_ptr})')
            return '0', 'i32'
        
        sig = self.func_sigs.get(func_name, ('i64', []))
        ret_type = sig[0]
        if ret_type == 'void':
            self.emit(f'  call void @{func_name}({args_str})')
            return '0', 'void'
        else:
            result = self.temp()
            self.emit(f'  {result} = call {ret_type} @{func_name}({args_str})')
            return result, ret_type


def generate_llvm_ir(ast) -> str:
    """Public interface for LLVM IR generation"""
    generator = LLVMIRGenerator()
    return generator.generate(ast)
