import sys
import os
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from compiler.parser.parser import (
    ASTNode, LetDecl, Assignment, IfStmt, WhileStmt, ForStmt, FunctionDef,
    ReturnStmt, ClassDef, StructDef, Field, ImportStmt, BreakStmt, ContinueStmt,
    RaiseStmt, MatchStmt, Literal, Identifier, BinaryOp, UnaryOp,
    FunctionCall, MemberAccess, IndexAccess, ListLiteral, DictLiteral,
    FStringLiteral, TupleLiteral, StructLiteral, UnsafeStmt,
    TypeAlias, LambdaExpr, Decorator, Cast,
)

WASM_TYPES = {
    "i32": "i32", "i64": "i64", "f32": "f32", "f64": "f64",
    "int": "i64", "uint": "u64", "i8": "i32", "i16": "i32",
    "u8": "i32", "u16": "i32", "u32": "i32", "u64": "i64",
    "float": "f64", "double": "f64", "bool": "i32", "char": "i32",
    "void": "", "string": "i32", "str": "i32", "ptr": "i32",
}

STRING_SLOT_SIZE = 256
STRING_DATA_BASE = 16


class WasmTranspiler:
    def __init__(self):
        self.code = []
        self.indent = 0
        self.func_idx = {}
        self.local_types: Dict[str, Dict[str, str]] = {}
        self.current_func = None
        self.current_params: List[str] = []
        self.string_literals: Dict[str, int] = {}
        self.string_data: List[Tuple[str, str]] = []
        self.string_counter = 0
        self.label_counter = 0
        self.global_vars: Dict[str, str] = {}
        self.struct_defs: Dict[str, List[Tuple[str, str]]] = {}
        self.struct_sizes: Dict[str, int] = {}
        self.loop_stack: List[str] = []
        self.has_string_ops = False
        self.exports: List[str] = []
        self.list_temp_count = 0
        self.dict_temp_count = 0
        self.struct_temp_count = 0
        self.ks_types: Dict[str, Dict[str, str]] = {}
        self.current_class = None
        self.class_fields: Dict[str, List[str]] = {}

    def emit(self, line: str = ""):
        indent = "  " * self.indent
        self.code.append(f"{indent}{line}")

    def emit_block(self, lines: List[str]):
        for line in lines:
            self.emit(line)

    def get_label(self, prefix: str = "L") -> str:
        lbl = f"{prefix}{self.label_counter}"
        self.label_counter += 1
        return lbl

    def alloc_string(self, s: str) -> str:
        name = f"__ks_str_{self.string_counter}"
        self.string_counter += 1
        self.string_data.append((name, s))
        self.has_string_ops = True
        return name

    def wasm_type(self, ks_type: Optional[str]) -> str:
        if ks_type is None:
            return ""
        return WASM_TYPES.get(ks_type, "i64")

    def escaped(self, s: str) -> str:
        r = []
        for ch in s:
            if ch == '"':
                r.append('\\"')
            elif ch == '\\':
                r.append('\\\\')
            elif ch == '\n':
                r.append('\\n')
            elif ch == '\t':
                r.append('\\t')
            elif ch == '\r':
                r.append('\\r')
            elif 32 <= ord(ch) < 127:
                r.append(ch)
            else:
                r.append(f'\\{ord(ch):02x}')
        return ''.join(r)

    def transpile(self, ast) -> str:
        self.code = []
        self.string_data = []
        self.string_counter = 0
        self.label_counter = 0

        if isinstance(ast, list):
            nodes = ast
        elif hasattr(ast, 'statements'):
            nodes = ast.statements
        else:
            nodes = [ast]

        self._collect_strings(nodes)
        for node in nodes:
            self._transpile_top_level(node)
        self._emit_string_data()
        self._emit_exports()
        return '\n'.join(self.code)

    def _declare_temp(self, name: str, wtype: str):
        if self.current_func:
            func_locals = self.local_types.setdefault(self.current_func, {})
            if name not in func_locals:
                func_locals[name] = wtype

    def _walk_all(self, nodes: List) -> List:
        result = []
        stack = list(nodes)
        while stack:
            n = stack.pop()
            if n is None:
                continue
            result.append(n)
            for attr in ('left', 'right', 'operand', 'expr', 'condition', 'value', 'target', 'obj', 'index', 'iterable', 'func', 'body'):
                val = getattr(n, attr, None)
                if isinstance(val, ASTNode):
                    stack.append(val)
                elif isinstance(val, list):
                    stack.extend(v for v in val if isinstance(v, ASTNode))
                elif isinstance(val, tuple):
                    stack.extend(v for v in val if isinstance(v, ASTNode))
        return result

    def _collect_strings(self, nodes: List):
        for n in self._walk_all(nodes):
            if isinstance(n, Literal) and isinstance(n.value, str) and n.value:
                if n.value not in self.string_literals:
                    self.alloc_string(n.value)
                    self.string_literals[n.value] = len(self.string_data) - 1

    def _has_main(self, nodes: List) -> bool:
        for n in nodes:
            if isinstance(n, FunctionDef) and n.name == "main":
                return True
        return False

    def _transpile_top_level(self, node: ASTNode):
        if isinstance(node, FunctionDef):
            self._transpile_function(node)
        elif isinstance(node, StructDef):
            self._transpile_struct(node)
        elif isinstance(node, ClassDef):
            self._transpile_class(node)
        elif isinstance(node, LetDecl):
            self._transpile_global_let(node)
        elif isinstance(node, ImportStmt):
            pass
        elif isinstance(node, TypeAlias):
            pass
        elif isinstance(node, Decorator):
            pass

    def _transpile_global_let(self, node: LetDecl):
        var_type = self.wasm_type(node.type_hint) or self._infer_let_type(node.value)
        gname = f"$g_{node.name}"
        self.global_vars[node.name] = gname
        if node.value is not None and isinstance(node.value, Literal):
            val = node.value.value
            if isinstance(val, bool):
                self.emit(f'(global {gname} (mut {var_type}) ({var_type}.const {"1" if val else "0"}))')
            elif isinstance(val, int):
                self.emit(f'(global {gname} (mut {var_type}) (i64.const {val}))')
            elif isinstance(val, float):
                self.emit(f'(global {gname} (mut {var_type}) (f64.const {val}))')
            else:
                self.emit(f'(global {gname} (mut {var_type}) ({var_type}.const 0))')
            return
        self.emit(f'(global {gname} (mut {var_type}) ({var_type}.const 0))')

    def _transpile_function(self, node: FunctionDef):
        self.current_func = node.name
        self.current_params = node.params
        self.local_types[node.name] = {}
        fn_name = f"${node.name}"

        ret_type = self.wasm_type(node.return_type) or ""
        param_types = []
        for p in node.params:
            pt = self.wasm_type(node.param_types.get(p, "")) or "i64"
            param_types.append(pt)
            self.local_types[node.name][p] = pt

        param_str = " ".join(f"(param ${p} {t})" for p, t in zip(node.params, param_types))
        ret_str = f"(result {ret_type})" if ret_type else ""

        self.emit()
        self.emit(f'(func {fn_name} {param_str} {ret_str}')
        self.exports.append(f'  (export "{node.name}" (func ${node.name}))')
        self.indent += 1

        local_vars = self._collect_local_vars(node)
        temp_vars = self._collect_temps(node)
        combined = {**local_vars, **temp_vars}
        for vname, vtype in combined.items():
            if vname not in node.params:
                wtype = self.wasm_type(vtype) or "i64"
                self.emit(f"(local ${vname} {wtype})")
                self.local_types[node.name][vname] = wtype

        self.loop_stack = []
        for stmt in node.body:
            self._transpile_stmt(stmt)

        if ret_type:
            self.emit(f'{ret_type}.const 0')
            self.emit('return')

        self.indent -= 1
        self.emit(')')

        if node.name == "main":
            self.emit()
            self.emit('(func $__ks_start (export "_start")')
            self.indent += 1
            self.emit('call $main')
            self.indent -= 1
            self.emit(')')

        self.current_func = None
        self.current_params = []

    def _collect_local_vars(self, node: FunctionDef) -> Dict[str, str]:
        result = {}
        for stmt in node.body:
            self._collect_vars_from(stmt, result)
        return result

    def _collect_temps(self, node: FunctionDef) -> Dict[str, str]:
        temps = {}
        list_idx = 0
        dict_idx = 0
        struct_idx = 0
        for n in self._walk_all(node.body):
            if isinstance(n, ListLiteral):
                temps[f"__list_{list_idx}"] = "i32"
                list_idx += 1
            elif isinstance(n, DictLiteral):
                temps[f"__dict_{dict_idx}"] = "i32"
                dict_idx += 1
            elif isinstance(n, StructLiteral):
                temps[f"__struct_{struct_idx}"] = "i32"
                struct_idx += 1
        return temps

    def _collect_vars_from(self, node: ASTNode, result: Dict[str, str]):
        if isinstance(node, LetDecl):
            vtype = node.type_hint or self._infer_let_type(node.value)
            result[node.name] = vtype
            if self.current_func:
                self.local_types.setdefault(self.current_func, {})[node.name] = vtype
        elif isinstance(node, ForStmt):
            result[node.var] = "i64"
        for attr in ('left', 'right', 'operand', 'expr', 'condition', 'value', 'target', 'obj', 'index', 'iterable', 'func', 'body'):
            val = getattr(node, attr, None)
            if isinstance(val, ASTNode):
                self._collect_vars_from(val, result)
            elif isinstance(val, list):
                for v in val:
                    if isinstance(v, ASTNode):
                        self._collect_vars_from(v, result)
            elif isinstance(val, tuple):
                for v in val:
                    if isinstance(v, ASTNode):
                        self._collect_vars_from(v, result)

    def _transpile_struct(self, node: StructDef):
        fields = [(f.name, f.field_type) for f in node.fields]
        self.struct_defs[node.name] = fields
        size = len(fields) * 8
        self.struct_sizes[node.name] = size

    def _transpile_class(self, node: ClassDef):
        self.current_class = node.name
        self.class_fields[node.name] = []
        fields_seen = set()
        for method in node.methods:
            for stmt in method.body:
                self._collect_self_fields(stmt, fields_seen)
        self.class_fields[node.name] = sorted(fields_seen)
        for method in node.methods:
            self._transpile_class_method(method)
        self.current_class = None

    def _collect_self_fields(self, node, fields: set):
        if isinstance(node, Assignment):
            if isinstance(node.target, MemberAccess) and isinstance(node.target.obj, Identifier) and node.target.obj.name == "self":
                fields.add(node.target.member)
        elif isinstance(node, MemberAccess):
            if isinstance(node.obj, Identifier) and node.obj.name == "self":
                fields.add(node.member)
        for attr in ('left', 'right', 'operand', 'expr', 'condition', 'value', 'target', 'obj', 'index', 'iterable', 'func'):
            val = getattr(node, attr, None)
            if isinstance(val, ASTNode):
                self._collect_self_fields(val, fields)
            elif isinstance(val, list):
                for v in val:
                    if isinstance(v, ASTNode):
                        self._collect_self_fields(v, fields)

    def _transpile_class_method(self, method: FunctionDef):
        class_name = self.current_class
        fields = self.class_fields.get(class_name, [])

        orig_params = method.params[:]
        if "self" not in method.params:
            method.params.insert(0, "self")
            method.param_types["self"] = "i32"

        self._transpile_function(method)
        method.params = orig_params

    def _transpile_stmt(self, node: ASTNode):
        if node is None:
            return
        if isinstance(node, LetDecl):
            self._transpile_let(node)
        elif isinstance(node, Assignment):
            self._transpile_assignment(node)
        elif isinstance(node, IfStmt):
            self._transpile_if(node)
        elif isinstance(node, WhileStmt):
            self._transpile_while(node)
        elif isinstance(node, ForStmt):
            self._transpile_for(node)
        elif isinstance(node, ReturnStmt):
            self._transpile_return(node)
        elif isinstance(node, FunctionCall):
            self._transpile_call_stmt(node)
        elif isinstance(node, BreakStmt):
            if self.loop_stack:
                self.emit(f'br ${self.loop_stack[-1]}')
        elif isinstance(node, ContinueStmt):
            if len(self.loop_stack) >= 2:
                self.emit(f'br ${self.loop_stack[-2]}')
        elif isinstance(node, UnsafeStmt):
            for s in node.body:
                self._transpile_stmt(s)
        elif isinstance(node, MatchStmt):
            self._transpile_match(node)
        elif isinstance(node, ImportStmt):
            pass
        elif isinstance(node, Decorator):
            pass

    def _transpile_let(self, node: LetDecl):
        vtype = self.wasm_type(node.type_hint) if node.type_hint else self._infer_let_type(node.value)
        vname = f"${node.name}"
        if self.current_func:
            self.local_types.setdefault(self.current_func, {})[node.name] = vtype
            ks_type = self._infer_ks_type(node.value)
            if ks_type:
                self.ks_types.setdefault(self.current_func, {})[node.name] = ks_type

        if node.value is not None:
            self._transpile_expr(node.value)
            self.emit(f'local.set {vname}')
        else:
            self.emit(f'{vtype}.const 0')
            self.emit(f'local.set {vname}')

    def _infer_let_type(self, value) -> str:
        if value is None:
            return "i64"
        if isinstance(value, Literal):
            if isinstance(value.value, str):
                return "i32" if value.value else "i64"
            if isinstance(value.value, bool):
                return "i32"
            if isinstance(value.value, float):
                return "f64"
            if isinstance(value.value, int):
                return "i64"
        if isinstance(value, (ListLiteral, DictLiteral, StructLiteral)):
            return "i32"
        if isinstance(value, Identifier):
            name = value.name
            if self.current_func and name in self.local_types.get(self.current_func, {}):
                return self.local_types[self.current_func][name]
        if isinstance(value, BinaryOp) and value.op == "+":
            if self._is_string_expr(value.left) or self._is_string_expr(value.right):
                return "i32"
            return "i64"
        if isinstance(value, FunctionCall):
            if isinstance(value.func, Identifier):
                fn = value.func.name
                if fn in ("len", "size", "length"):
                    return "i64"
                if fn in ("str", "int"):
                    return "i64"
                if fn == "float":
                    return "f64"
        return "i64"

    def _transpile_assignment(self, node: Assignment):
        if isinstance(node.target, Identifier):
            self._transpile_expr(node.value)
            self.emit(f'local.set ${node.target.name}')
        elif isinstance(node.target, IndexAccess):
            self._transpile_expr(node.target.obj)
            index_type = self._transpile_expr(node.target.index)
            obj_ks_type = ""
            if isinstance(node.target.obj, Identifier):
                obj_ks_type = self._infer_ks_type(node.target.obj)
            if obj_ks_type == "dict":
                if index_type == "i32":
                    self.emit('i64.extend_i32_u')
                self._transpile_expr(node.value)
                self.emit('call $__ks_dict_set')
            else:
                if index_type == "i64":
                    self.emit('i32.wrap_i64')
                self._transpile_expr(node.value)
                self.emit('call $__ks_list_set')
        elif isinstance(node.target, MemberAccess):
            self._transpile_struct_field_set(node.target)

    def _transpile_struct_field_set(self, node: MemberAccess):
        struct_name = None
        if isinstance(node.obj, Identifier):
            struct_name = node.obj.name
        if struct_name and struct_name in self.struct_defs:
            fields = self.struct_defs[struct_name]
            offsets = {f[0]: i * 8 for i, f in enumerate(fields)}
            field_offset = offsets.get(node.member, 0)
            self._transpile_expr(node.obj)
            self._transpile_expr(node.value)
            self.emit(f'i32.const {field_offset}')
            self.emit('call $__ks_struct_set')
        elif struct_name == "self" and self.current_class and node.member in self.class_fields.get(self.current_class, []):
            fields = self.class_fields[self.current_class]
            field_offset = fields.index(node.member) * 8
            self._transpile_expr(node.obj)
            self._transpile_expr(node.value)
            self.emit(f'i32.const {field_offset}')
            self.emit('call $__ks_struct_set')
        else:
            self._transpile_expr(node.obj)
            self._transpile_expr(node.value)
            self.emit('i64.store')

    def _transpile_if(self, node: IfStmt):
        end_label = self.get_label("endif")
        self._transpile_expr(node.condition)
        self.emit(f'if')
        self.indent += 1
        for stmt in node.then_block:
            self._transpile_stmt(stmt)
        self.indent -= 1

        if node.elif_blocks:
            for cond, block in node.elif_blocks:
                self.emit(f'else')
                self.indent += 1
                self._transpile_expr(cond)
                self.emit(f'if')
                self.indent += 1
                for s in block:
                    self._transpile_stmt(s)
                self.indent -= 1
                self.indent -= 1
            if node.else_block:
                self.emit(f'else')
                self.indent += 1
                for s in node.else_block:
                    self._transpile_stmt(s)
                self.indent -= 1
            for _ in node.elif_blocks:
                self.emit('end')
        elif node.else_block:
            self.emit(f'else')
            self.indent += 1
            for s in node.else_block:
                self._transpile_stmt(s)
            self.indent -= 1

        self.emit('end')

    def _transpile_while(self, node: WhileStmt):
        loop_label = self.get_label("loop")
        end_label = self.get_label("endloop")
        self.loop_stack.append(end_label)
        self.loop_stack.append(loop_label)

        self.emit(f'block ${end_label}')
        self.indent += 1
        self.emit(f'loop ${loop_label}')
        self.indent += 1

        self._transpile_expr(node.condition)
        self.emit('i32.eqz')
        self.emit(f'br_if ${end_label}')

        for stmt in node.body:
            self._transpile_stmt(stmt)

        self.emit(f'br ${loop_label}')
        self.indent -= 1
        self.emit('end')
        self.indent -= 1
        self.emit('end')

        self.loop_stack.pop()
        self.loop_stack.pop()

    def _transpile_for(self, node: ForStmt):
        vname = f"${node.var}"
        for_idx = self.label_counter
        self.label_counter += 1
        counter_tmp = f"$for_i_{for_idx}"
        limit_tmp = f"$for_n_{for_idx}"
        has_idx = f"$for_has_idx_{for_idx}"
        has_idx2 = f"$for_has_idx_{for_idx + 1}"
        self._declare_temp(counter_tmp[1:], "i64")
        self._declare_temp(limit_tmp[1:], "i64")

        is_range = False
        range_start = 0
        range_end = 0
        range_step = 1

        if isinstance(node.iterable, FunctionCall) and isinstance(node.iterable.func, Identifier) and node.iterable.func.name == "range":
            is_range = True
            args = node.iterable.args
            if len(args) == 1:
                range_start = 0
                if isinstance(args[0], Literal) and isinstance(args[0].value, int):
                    range_end = args[0].value
                else:
                    range_start = 0
                    range_end = 5
            elif len(args) == 2:
                if isinstance(args[0], Literal) and isinstance(args[0].value, int):
                    range_start = args[0].value
                else:
                    range_start = 0
                if isinstance(args[1], Literal) and isinstance(args[1].value, int):
                    range_end = args[1].value
                else:
                    range_end = 5
            elif len(args) >= 3:
                if isinstance(args[0], Literal) and isinstance(args[0].value, int):
                    range_start = args[0].value
                else:
                    range_start = 0
                if isinstance(args[1], Literal) and isinstance(args[1].value, int):
                    range_end = args[1].value
                else:
                    range_end = 5
                if isinstance(args[2], Literal) and isinstance(args[2].value, int):
                    range_step = args[2].value
                else:
                    range_step = 1

        if is_range:
            end_label = self.get_label("for_end")
            loop_label = self.get_label("for_loop")
            self.loop_stack.append(end_label)
            self.loop_stack.append(loop_label)

            self.emit(f'i64.const {range_start}')
            self.emit(f'local.set {counter_tmp}')

            self.emit(f'block ${end_label}')
            self.indent += 1
            self.emit(f'loop ${loop_label}')
            self.indent += 1

            self.emit(f'local.get {counter_tmp}')
            self.emit(f'i64.const {range_end}')
            self.emit(f'i64.ge_s')
            self.emit(f'br_if ${end_label}')

            self.emit(f'local.get {counter_tmp}')
            self.emit(f'local.set {vname}')

            for stmt in node.body:
                self._transpile_stmt(stmt)

            self.emit(f'local.get {counter_tmp}')
            self.emit(f'i64.const {range_step}')
            self.emit(f'i64.add')
            self.emit(f'local.set {counter_tmp}')
            self.emit(f'br ${loop_label}')
            self.indent -= 1
            self.emit('end')
            self.indent -= 1
            self.emit('end')

            self.loop_stack.pop()
            self.loop_stack.pop()
        else:
            list_tmp = f"$for_list_{for_idx}"
            list_len = f"$for_len_{for_idx}"
            list_i = f"$for_li_{for_idx}"
            self._declare_temp(list_tmp[1:], "i32")
            self._declare_temp(list_len[1:], "i32")
            self._declare_temp(list_i[1:], "i32")

            end_label = self.get_label("for_end")
            loop_label = self.get_label("for_loop")
            self.loop_stack.append(end_label)
            self.loop_stack.append(loop_label)

            self._transpile_expr(node.iterable)
            self.emit(f'local.set {list_tmp}')
            self.emit(f'local.get {list_tmp}')
            self.emit(f'call $__ks_list_len')
            self.emit(f'local.set {list_len}')
            self.emit(f'i32.const 0')
            self.emit(f'local.set {list_i}')

            self.emit(f'block ${end_label}')
            self.indent += 1
            self.emit(f'loop ${loop_label}')
            self.indent += 1

            self.emit(f'local.get {list_i}')
            self.emit(f'local.get {list_len}')
            self.emit(f'i32.ge_s')
            self.emit(f'br_if ${end_label}')

            self.emit(f'local.get {list_tmp}')
            self.emit(f'local.get {list_i}')
            self.emit(f'call $__ks_list_get')
            self.emit(f'local.set {vname}')

            for stmt in node.body:
                self._transpile_stmt(stmt)

            self.emit(f'local.get {list_i}')
            self.emit(f'i32.const 1')
            self.emit(f'i32.add')
            self.emit(f'local.set {list_i}')
            self.emit(f'br ${loop_label}')
            self.indent -= 1
            self.emit('end')
            self.indent -= 1
            self.emit('end')

            self.loop_stack.pop()
            self.loop_stack.pop()

    def _transpile_return(self, node: ReturnStmt):
        if node.value is not None:
            self._transpile_expr(node.value)
        self.emit('return')

    def _transpile_call_stmt(self, node: FunctionCall):
        self._transpile_expr(node)
        if isinstance(node.func, Identifier) and node.func.name in ('print', 'println'):
            pass

    def _transpile_match(self, node: MatchStmt):
        end_label = self.get_label("match_end")
        case_labels = [self.get_label("case") for _ in node.cases]
        match_idx = self.label_counter
        self.label_counter += 1
        match_val_tmp = f"$match_val_{match_idx}"
        match_str_tmp = f"$match_str_{match_idx}"
        self._declare_temp(match_val_tmp[1:], "i64")
        self._declare_temp(match_str_tmp[1:], "i32")

        self._transpile_expr(node.expr)

        for i, (pattern, body, guard) in enumerate(node.cases):
            if isinstance(pattern, Literal):
                val = pattern.value
                if isinstance(val, int):
                    self.emit(f'local.set {match_val_tmp}')
                    self.emit(f'local.get {match_val_tmp}')
                    self.emit(f'i64.const {val}')
                    self.emit('i64.eq')
                elif isinstance(val, str):
                    self.emit(f'local.set {match_str_tmp}')
                    self.emit(f'local.get {match_str_tmp}')
                    sidx = self.string_literals.get(val, -1)
                    if sidx >= 0:
                        offset = STRING_DATA_BASE + sidx * STRING_SLOT_SIZE
                        self.emit(f'i32.const {offset}')
                        self.emit('call $__ks_strcmp')
                        self.emit('i32.eqz')
                    else:
                        self.emit('drop')
                        self.emit('i32.const 0')
                else:
                    self.emit('drop')
                    self.emit('i32.const 0')
                self.emit(f'br_if ${case_labels[i]}')

            elif isinstance(pattern, Identifier) and pattern.name == '_':
                self.emit(f'br ${case_labels[i]}')

        for i, (pattern, body, guard) in enumerate(node.cases):
            self.emit(f'{case_labels[i]}:')
            for s in body:
                self._transpile_stmt(s)
            self.emit(f'br ${end_label}')

        if node.default:
            for s in node.default:
                self._transpile_stmt(s)

        self.emit(f'{end_label}:')

    def _transpile_expr(self, node: ASTNode) -> str:
        if node is None:
            self.emit('i64.const 0')
            return "i64"

        if isinstance(node, Literal):
            val = node.value
            if isinstance(val, bool):
                self.emit(f'i32.const {"1" if val else "0"}')
                return "i32"
            elif isinstance(val, int):
                self.emit(f'i64.const {val}')
                return "i64"
            elif isinstance(val, float):
                self.emit(f'f64.const {val}')
                return "f64"
            elif isinstance(val, str):
                return self._transpile_string_literal(val)
            return "i64"

        if isinstance(node, Identifier):
            return self._transpile_identifier(node)

        if isinstance(node, BinaryOp):
            return self._transpile_binary_op(node)

        if isinstance(node, UnaryOp):
            return self._transpile_unary_op(node)

        if isinstance(node, FunctionCall):
            return self._transpile_function_call(node)

        if isinstance(node, IndexAccess):
            return self._transpile_index_access(node)

        if isinstance(node, MemberAccess):
            return self._transpile_member_access(node)

        if isinstance(node, ListLiteral):
            return self._transpile_list_literal(node)

        if isinstance(node, DictLiteral):
            return self._transpile_dict_literal(node)

        if isinstance(node, StructLiteral):
            return self._transpile_struct_literal(node)

        if isinstance(node, TupleLiteral):
            return self._transpile_tuple_literal(node)

        if isinstance(node, FStringLiteral):
            return self._transpile_fstring(node)

        if isinstance(node, Cast):
            return self._transpile_cast(node)

        if isinstance(node, LambdaExpr):
            self.emit('i64.const 0')
            return "i64"

        self.emit('i64.const 0')
        return "i64"

    def _infer_ks_type(self, value) -> str:
        if value is None:
            return ""
        if isinstance(value, ListLiteral):
            return "list"
        if isinstance(value, DictLiteral):
            return "dict"
        if isinstance(value, StructLiteral):
            return f"struct:{value.name}" if value.name else "struct"
        if isinstance(value, Identifier):
            if self.current_func and value.name in self.ks_types.get(self.current_func, {}):
                return self.ks_types[self.current_func][value.name]
        return ""

    def _is_string_expr(self, node) -> bool:
        if isinstance(node, Literal) and isinstance(node.value, str):
            return bool(node.value)
        if isinstance(node, Identifier):
            name = node.name
            if self.current_func and name in self.local_types.get(self.current_func, {}):
                return self.local_types[self.current_func][name] == "i32"
            return False
        if isinstance(node, BinaryOp) and node.op == "+":
            return self._is_string_expr(node.left) or self._is_string_expr(node.right)
        return False

    def _transpile_string_literal(self, val: str) -> str:
        if not val:
            self.emit('i64.const 0')
            return "i64"
        sidx = self.string_literals.get(val, -1)
        if sidx >= 0:
            offset = STRING_DATA_BASE + sidx * STRING_SLOT_SIZE
            self.emit(f'i32.const {offset}')
        else:
            self.emit('i64.const 0')
            return "i64"
        return "i32"

    def _transpile_identifier(self, node: Identifier) -> str:
        name = node.name
        if name == "true":
            self.emit('i32.const 1')
            return "i32"
        if name == "false":
            self.emit('i32.const 0')
            return "i32"

        wtype = "i64"
        if self.current_func and name in self.local_types.get(self.current_func, {}):
            wtype = self.local_types[self.current_func][name]

        if self.current_func and name in self.local_types.get(self.current_func, {}):
            self.emit(f'local.get ${name}')
        elif name in self.global_vars:
            self.emit(f'global.get {self.global_vars[name]}')
        else:
            self.emit(f'local.get ${name}')
        return wtype

    def _transpile_binary_op(self, node: BinaryOp) -> str:
        left_type = self._transpile_expr(node.left)
        right_type = self._transpile_expr(node.right)
        op = node.op

        if op == "+" and left_type == "i32" and right_type == "i32":
            if self._is_string_expr(node.left) or self._is_string_expr(node.right):
                self.emit('call $__ks_str_concat')
                return "i32"
            self.emit('i32.add')
            return "i32"

        use_f64 = (left_type == "f64" or right_type == "f64")
        use_i64 = (left_type == "i64" or right_type == "i64") and not use_f64
        ts = "f64" if use_f64 else ("i64" if use_i64 else "i32")

        if op in ("+", "-", "*", "/", "%"):
            wasm_op = {
                "+": f"{ts}.add",
                "-": f"{ts}.sub",
                "*": f"{ts}.mul",
                "/": f"{ts}.div_u" if ts in ("i32", "i64") else f"{ts}.div",
                "%": f"{ts}.rem_u" if ts in ("i32", "i64") else "",
            }.get(op, "")
            if wasm_op:
                self.emit(wasm_op)
            return ts

        elif op in ("==", "!=", "<", ">", "<=", ">="):
            if op in ("==", "!=") and (self._is_string_expr(node.left) or self._is_string_expr(node.right)):
                self.emit('call $__ks_strcmp')
                if op == "!=":
                    self.emit('i32.const 0')
                    self.emit('i32.ne')
                else:
                    self.emit('i32.eqz')
                return "i32"
            cmp_map = {"==": "eq", "!=": "ne", "<": "lt_s", ">": "gt_s", "<=": "le_s", ">=": "ge_s"}
            cmp_op = cmp_map.get(op, "eq")
            self.emit(f'{ts}.{cmp_op}')
            return "i32"

        elif op in ("and", "or"):
            self.emit(f'i64.{op}')
            return "i32"

        elif op == "..":
            self.emit('i64.add')
            return "i64"

        return ts

    def _transpile_unary_op(self, node: UnaryOp) -> str:
        operand_type = self._transpile_expr(node.operand)
        if node.op == "-":
            self.emit(f'{operand_type}.const -1')
            self.emit(f'{operand_type}.mul')
            return operand_type
        elif node.op == "not":
            self.emit('i64.eqz')
            return "i32"
        return operand_type

    def _transpile_function_call(self, node: FunctionCall) -> str:
        func_name = ""
        if isinstance(node.func, Identifier):
            func_name = node.func.name
        elif isinstance(node.func, MemberAccess):
            self._transpile_expr(node.func.obj)
            func_name = node.func.member

        if func_name in ("print", "println"):
            if node.args:
                arg_type = self._transpile_expr(node.args[0])
                if arg_type == "i32":
                    self.emit('call $__ks_print_str_ptr')
                else:
                    self._emit_print(arg_type)
            if func_name == "println":
                self._emit_print_newline()
            return "void"

        if func_name in ("len", "length", "size"):
            if node.args:
                arg_type = self._transpile_expr(node.args[0])
                self.emit('call $__ks_list_len')
                if arg_type == "i32":
                    self.emit('i64.extend_i32_u')
            return "i64"

        if func_name == "range":
            if node.args:
                if len(node.args) == 1:
                    self._transpile_expr(node.args[0])
                elif len(node.args) == 2:
                    self._transpile_expr(node.args[0])
                    self._transpile_expr(node.args[1])
                else:
                    self._transpile_expr(node.args[0])
                    self._transpile_expr(node.args[1])
                    self._transpile_expr(node.args[2])
            return "i64"

        if func_name in ("int", "str", "float", "bool"):
            if node.args:
                self._transpile_expr(node.args[0])
            return "i64" if func_name in ("int", "str") else "f64"

        if func_name == "append" and node.args:
            self._transpile_expr(node.args[0])
            self._transpile_expr(node.args[1])
            self.emit('call $__ks_list_append')
            return "void"

        if func_name == "pop" and node.args:
            return self._transpile_list_pop(node)

        if func_name.startswith("__ks_import_"):
            import_name = func_name[12:]
            for arg in node.args:
                self._transpile_expr(arg)
            self.emit(f'call ${import_name}')
            return "i64"

        if func_name:
            for arg in node.args:
                self._transpile_expr(arg)
            self.emit(f'call ${func_name}')
            return self.wasm_type(
                getattr(getattr(node, 'func', None), 'return_type', None)
            ) or "i64"

        return "i64"

    def _transpile_list_pop(self, node: FunctionCall) -> str:
        self._declare_temp("pop_ptr", "i32")
        self._declare_temp("pop_idx", "i32")
        self._declare_temp("pop_val", "i64")
        self._transpile_expr(node.args[0])
        self.emit('local.set $pop_ptr')
        self.emit('local.get $pop_ptr')
        self.emit('call $__ks_list_len')
        self.emit('i32.const 1')
        self.emit('i32.sub')
        self.emit('local.set $pop_idx')
        self.emit('local.get $pop_ptr')
        self.emit('local.get $pop_idx')
        self.emit('call $__ks_list_get')
        self.emit('local.set $pop_val')
        self.emit('local.get $pop_ptr')
        self.emit('local.get $pop_idx')
        self.emit('i32.store')
        self.emit('local.get $pop_val')
        return "i64"

    def _emit_print(self, typ: str = "i64"):
        if typ == "f64":
            self.emit('call $__ks_print_f64')
        elif typ == "i64":
            self.emit('call $__ks_print_i64')
        else:
            self.emit('call $__ks_print_i32')

    def _emit_print_newline(self):
        self.emit('i32.const 10')
        self.emit('call $__ks_print_char')

    def _transpile_index_access(self, node: IndexAccess) -> str:
        obj_type = self._transpile_expr(node.obj)
        obj_ks_type = ""
        if isinstance(node.obj, Identifier):
            obj_ks_type = self._infer_ks_type(node.obj)
        index_type = self._transpile_expr(node.index)
        if obj_ks_type == "dict":
            if index_type == "i32":
                self.emit('i64.extend_i32_u')
            self.emit('call $__ks_dict_get')
        else:
            if index_type == "i64":
                self.emit('i32.wrap_i64')
            self.emit('call $__ks_list_get')
        return "i64"

    def _transpile_member_access(self, node: MemberAccess) -> str:
        struct_name = None
        if isinstance(node.obj, Identifier):
            struct_name = node.obj.name
        if struct_name and struct_name in self.struct_defs:
            fields = self.struct_defs[struct_name]
            offsets = {f[0]: i * 8 for i, f in enumerate(fields)}
            field_offset = offsets.get(node.member, 0)
            self._transpile_expr(node.obj)
            self.emit(f'i32.const {field_offset}')
            self.emit('call $__ks_struct_get')
            return "i64"
        if struct_name == "self" and self.current_class and node.member in self.class_fields.get(self.current_class, []):
            fields = self.class_fields[self.current_class]
            field_offset = fields.index(node.member) * 8
            self._transpile_expr(node.obj)
            self.emit(f'i32.const {field_offset}')
            self.emit('call $__ks_struct_get')
            return "i64"
        self._transpile_expr(node.obj)
        self.emit('i64.load')
        return "i64"

    def _transpile_list_literal(self, node: ListLiteral) -> str:
        count = len(node.elements)
        idx = self.list_temp_count
        self.list_temp_count += 1
        arr_label = f"$__list_{idx}"
        self._declare_temp(arr_label[1:], "i32")
        self.emit(f'i32.const {count}')
        self.emit('call $__ks_list_new')
        self.emit(f'local.set {arr_label}')
        for i, elem in enumerate(node.elements):
            self.emit(f'local.get {arr_label}')
            self.emit(f'i32.const {i}')
            self._transpile_expr(elem)
            self.emit('call $__ks_list_set')
        self.emit(f'local.get {arr_label}')
        return "i32"

    def _transpile_dict_literal(self, node: DictLiteral) -> str:
        cap = len(node.pairs) * 2
        idx = self.dict_temp_count
        self.dict_temp_count += 1
        tmp = f"$__dict_{idx}"
        self._declare_temp(tmp[1:], "i32")
        self.emit(f'i32.const {cap}')
        self.emit('call $__ks_dict_new')
        self.emit(f'local.set {tmp}')
        for key_node, val_node in node.pairs:
            self.emit(f'local.get {tmp}')
            self._transpile_expr(key_node)
            self._transpile_expr(val_node)
            self.emit('call $__ks_dict_set')
        self.emit(f'local.get {tmp}')
        return "i32"

    def _transpile_struct_literal(self, node: StructLiteral) -> str:
        size = 0
        fields = []
        if node.name in self.struct_defs:
            fields = self.struct_defs[node.name]
            size = len(fields) * 8
        else:
            size = len(node.fields) * 8

        idx = self.struct_temp_count
        self.struct_temp_count += 1
        tmp = f"$__struct_{idx}"
        self._declare_temp(tmp[1:], "i32")
        self.emit(f'i32.const {size}')
        self.emit('call $__ks_struct_new')
        self.emit(f'local.set {tmp}')

        field_map = {name: i * 8 for i, (name, _) in enumerate(fields)} if fields else {}
        for fname, fval in node.fields:
            offset = field_map.get(fname, 0)
            self.emit(f'local.get {tmp}')
            self.emit(f'i32.const {offset}')
            self._transpile_expr(fval)
            self.emit('call $__ks_struct_set')

        self.emit(f'local.get {tmp}')
        return "i32"

    def _transpile_tuple_literal(self, node: TupleLiteral) -> str:
        if node.elements:
            self._transpile_expr(node.elements[0])
        else:
            self.emit('i64.const 0')
        return "i64"

    def _transpile_fstring(self, node: FStringLiteral) -> str:
        self.emit('i64.const 0')
        return "i64"

    def _transpile_cast(self, node: Cast) -> str:
        self._transpile_expr(node.expr)
        return "i64"

    def _emit_string_data(self):
        if not self.string_data:
            return
        self.emit()
        self.emit(';; String data in linear memory')
        for i, (name, val) in enumerate(self.string_data):
            offset = STRING_DATA_BASE + i * STRING_SLOT_SIZE
            esc = self.escaped(val)
            self.emit(f'(data (i32.const {offset}) "{esc}\\00")')

    def _emit_exports(self):
        if self.exports:
            self.emit()
            self.emit(';; Function exports')
            for exp in self.exports:
                self.emit(exp)
