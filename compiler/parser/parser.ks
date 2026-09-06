::
:: KentScript Bootstrap Compiler — Stage 2: Parser
:: Written entirely in KentScript.
:: Converts a token stream into an Abstract Syntax Tree (AST).
::
:: Part of the KentScript self-hosting bootstrap chain:
::   lexer.ks  → parser.ks → codegen.ks → bootstrap.ks
::
:: [KS-BOOT-002]
::

from lexer import (
    TK_EOF, TK_ERROR, TK_INT, TK_FLOAT, TK_HEX, TK_BIN,
    TK_STRING, TK_FSTRING, TK_IDENT, TK_BOOL, TK_NONE,
    TK_LET, TK_CONST, TK_MUT, TK_IF, TK_ELIF, TK_ELSE,
    TK_WHILE, TK_FOR, TK_IN, TK_FUNC, TK_FN, TK_RETURN,
    TK_CLASS, TK_NEW, TK_SELF, TK_SUPER, TK_EXTENDS,
    TK_IMPORT, TK_FROM, TK_AS, TK_TRY, TK_EXCEPT,
    TK_FINALLY, TK_RAISE, TK_MATCH, TK_CASE, TK_DEFAULT,
    TK_BREAK, TK_CONTINUE, TK_ASYNC, TK_AWAIT, TK_YIELD,
    TK_TYPE, TK_INTERFACE, TK_ENUM, TK_UNSAFE, TK_SAFE,
    TK_BORROW, TK_RELEASE, TK_MOVE, TK_THREAD, TK_EXPORT,
    TK_PRINT, TK_AND, TK_OR, TK_NOT, TK_IS,
    TK_PLUS, TK_MINUS, TK_STAR, TK_SLASH, TK_PERCENT,
    TK_POWER, TK_AMPERSAND, TK_PIPE_OP, TK_CARET, TK_TILDE,
    TK_LSHIFT, TK_RSHIFT, TK_EQ, TK_NEQ, TK_LT, TK_GT,
    TK_LE, TK_GE, TK_ASSIGN, TK_PLUS_EQ, TK_MINUS_EQ,
    TK_STAR_EQ, TK_SLASH_EQ, TK_PIPE, TK_ARROW, TK_FAT_ARROW,
    TK_COLON, TK_DCOLON, TK_SEMICOLON, TK_COMMA, TK_DOT,
    TK_DOTDOT, TK_AT, TK_QUESTION, TK_BANG,
    TK_LPAREN, TK_RPAREN, TK_LBRACE, TK_RBRACE,
    TK_LBRACKET, TK_RBRACKET,
)

:: ─── AST node helpers ───────────────────────────────────────────────────────
:: We represent every node as a plain dict with a "kind" key.
:: This keeps the parser pure KentScript without needing dataclasses.

func node(kind: str, data: dict) -> dict {
    data["kind"] = kind
    return data
}

:: ─── Parser class ────────────────────────────────────────────────────────────

class Parser {
    func __init__(self, tokens: list, source: str, filename: str) {
        self.tokens   = tokens
        self.source   = source
        self.filename = filename
        self.pos      = 0
        self.errors   = []
    }

    :: ── token navigation ──

    func cur(self) -> dict {
        if self.pos < len(self.tokens) { return self.tokens[self.pos] }
        return self.tokens[len(self.tokens) - 1]  ## EOF sentinel
    }

    func peek_kind(self) -> str {
        return self.cur().kind
    }

    func at(self, kind: str) -> bool {
        return self.peek_kind() == kind
    }

    func at_any(self, kinds: list) -> bool {
        let k: str = self.peek_kind()
        for kk in kinds {
            if k == kk { return true }
        }
        return false
    }

    func advance(self) -> dict {
        let t: dict = self.cur()
        if not self.at(TK_EOF) { self.pos = self.pos + 1 }
        return t
    }

    func expect(self, kind: str) -> dict {
        if self.at(kind) { return self.advance() }
        let t: dict = self.cur()
        self.error(f"Expected {kind} but got {t.kind} ('{t.value}')", t)
        return t
    }

    func consume(self, kind: str) -> bool {
        if self.at(kind) { self.advance(); return true }
        return false
    }

    func optional_semicolon(self) {
        self.consume(TK_SEMICOLON)
    }

    func error(self, msg: str, tok: dict) {
        let loc: str = f"{self.filename}:{tok.line}:{tok.col}"
        self.errors.append(f"{loc}: parse error: {msg}")
    }

    :: ── top-level ──

    func parse_program(self) -> dict {
        let stmts: list = []
        while not self.at(TK_EOF) {
            let s = self.parse_statement()
            if s != none { stmts.append(s) }
        }
        return node("Program", {"body": stmts})
    }

    :: ── statements ──

    func parse_statement(self) -> dict {
        let k: str = self.peek_kind()

        if k == TK_LET or k == TK_CONST or k == TK_MUT {
            return self.parse_let()
        }
        if k == TK_IF      { return self.parse_if() }
        if k == TK_WHILE   { return self.parse_while() }
        if k == TK_FOR     { return self.parse_for() }
        if k == TK_FUNC or k == TK_FN { return self.parse_func(false) }
        if k == TK_ASYNC   { return self.parse_async_func() }
        if k == TK_CLASS   { return self.parse_class() }
        if k == TK_RETURN  { return self.parse_return() }
        if k == TK_YIELD   { return self.parse_yield() }
        if k == TK_BREAK   { self.advance(); self.optional_semicolon(); return node("Break", {}) }
        if k == TK_CONTINUE { self.advance(); self.optional_semicolon(); return node("Continue", {}) }
        if k == TK_IMPORT  { return self.parse_import() }
        if k == TK_FROM    { return self.parse_from_import() }
        if k == TK_TRY     { return self.parse_try() }
        if k == TK_RAISE   { return self.parse_raise() }
        if k == TK_MATCH   { return self.parse_match() }
        if k == TK_UNSAFE  { return self.parse_unsafe() }
        if k == TK_SAFE    { return self.parse_safe() }
        if k == TK_BORROW  { return self.parse_borrow() }
        if k == TK_RELEASE { return self.parse_release() }
        if k == TK_MOVE    { return self.parse_move() }
        if k == TK_TYPE    { return self.parse_type_alias() }
        if k == TK_INTERFACE { return self.parse_interface() }
        if k == TK_ENUM    { return self.parse_enum() }
        if k == TK_AT      { return self.parse_decorated() }
        if k == TK_PRINT   { return self.parse_print_stmt() }
        if k == TK_EXPORT  { self.advance(); return self.parse_statement() }
        if k == TK_THREAD  { return self.parse_thread() }

        :: expression statement
        let expr = self.parse_expression()
        self.optional_semicolon()
        return node("ExprStmt", {"expr": expr})
    }

    :: ── let / const ──

    func parse_let(self) -> dict {
        let is_const: bool = self.at(TK_CONST)
        let is_mut:   bool = self.at(TK_MUT)
        self.advance()

        let name_tok: dict = self.expect(TK_IDENT)
        let name: str = name_tok.value
        let type_hint = none

        if self.consume(TK_COLON) {
            type_hint = self.parse_type_expr()
        }

        let value = none
        if self.consume(TK_ASSIGN) {
            value = self.parse_expression()
        }

        self.optional_semicolon()
        return node("LetDecl", {
            "name": name, "type_hint": type_hint,
            "value": value, "is_const": is_const, "is_mut": is_mut,
        })
    }

    :: ── type expressions ──

    func parse_type_expr(self) -> str {
        let buf: str = ""
        :: collect type tokens: idents, [], |, <, >
        let t: dict = self.advance()
        buf = buf + t.value
        :: optional generic: i.e. List<i32>
        if self.at(TK_LT) {
            buf = buf + self.advance().value
            buf = buf + self.parse_type_expr()
            self.expect(TK_GT)
            buf = buf + ">"
        }
        :: optional array/pointer: str[]
        while self.at(TK_LBRACKET) and self.peek_kind() == TK_RBRACKET {
            buf = buf + "[]"
            self.advance(); self.advance()
        }
        :: union: str | int
        if self.at(TK_PIPE_OP) {
            buf = buf + " | "
            self.advance()
            buf = buf + self.parse_type_expr()
        }
        return buf
    }

    :: ── if / elif / else ──

    func parse_if(self) -> dict {
        self.expect(TK_IF)
        let cond  = self.parse_expression()
        let then  = self.parse_block()
        let elifs: list = []
        let else_block = none

        while self.at(TK_ELIF) {
            self.advance()
            let ec = self.parse_expression()
            let eb = self.parse_block()
            elifs.append({"cond": ec, "body": eb})
        }

        if self.consume(TK_ELSE) {
            else_block = self.parse_block()
        }

        return node("If", {"cond": cond, "then": then, "elifs": elifs, "else": else_block})
    }

    :: ── while ──

    func parse_while(self) -> dict {
        self.expect(TK_WHILE)
        let cond = self.parse_expression()
        let body = self.parse_block()
        return node("While", {"cond": cond, "body": body})
    }

    :: ── for ──

    func parse_for(self) -> dict {
        self.expect(TK_FOR)
        let var_tok: dict = self.expect(TK_IDENT)
        self.expect(TK_IN)
        let iterable = self.parse_expression()
        let body = self.parse_block()
        return node("For", {"var": var_tok.value, "iterable": iterable, "body": body})
    }

    :: ── function ──

    func parse_func(self, is_async: bool) -> dict {
        if self.at(TK_FUNC) or self.at(TK_FN) { self.advance() }
        let name_tok: dict = self.expect(TK_IDENT)
        self.expect(TK_LPAREN)
        let params: list = self.parse_params()
        self.expect(TK_RPAREN)

        let return_type = none
        if self.consume(TK_ARROW) {
            return_type = self.parse_type_expr()
        }

        let body = self.parse_block()
        return node("FuncDef", {
            "name": name_tok.value, "params": params,
            "return_type": return_type, "body": body, "is_async": is_async,
        })
    }

    func parse_async_func(self) -> dict {
        self.expect(TK_ASYNC)
        return self.parse_func(true)
    }

    func parse_params(self) -> list {
        let params: list = []
        while not self.at(TK_RPAREN) and not self.at(TK_EOF) {
            let p: dict = {}
            let pname: dict = self.expect(TK_IDENT)
            p["name"] = pname.value
            if self.consume(TK_COLON) {
                p["type"] = self.parse_type_expr()
            }
            if self.consume(TK_ASSIGN) {
                p["default"] = self.parse_expression()
            }
            params.append(p)
            if not self.consume(TK_COMMA) { break }
        }
        return params
    }

    :: ── class ──

    func parse_class(self) -> dict {
        self.expect(TK_CLASS)
        let name_tok: dict = self.expect(TK_IDENT)
        let parent = none

        if self.consume(TK_EXTENDS) {
            parent = self.advance().value
        }

        self.expect(TK_LBRACE)
        let methods: list = []
        while not self.at(TK_RBRACE) and not self.at(TK_EOF) {
            if self.at(TK_FUNC) or self.at(TK_FN) or self.at(TK_ASYNC) {
                let is_async: bool = self.at(TK_ASYNC)
                if is_async { self.advance() }
                methods.append(self.parse_func(is_async))
            } else {
                :: class field
                let field_stmt = self.parse_statement()
                methods.append(field_stmt)
            }
        }
        self.expect(TK_RBRACE)

        return node("ClassDef", {"name": name_tok.value, "parent": parent, "methods": methods})
    }

    :: ── return ──

    func parse_return(self) -> dict {
        self.expect(TK_RETURN)
        let val = none
        if not self.at(TK_SEMICOLON) and not self.at(TK_RBRACE) and not self.at(TK_EOF) {
            val = self.parse_expression()
        }
        self.optional_semicolon()
        return node("Return", {"value": val})
    }

    :: ── yield ──

    func parse_yield(self) -> dict {
        self.expect(TK_YIELD)
        let val = none
        if not self.at(TK_SEMICOLON) and not self.at(TK_EOF) {
            val = self.parse_expression()
        }
        self.optional_semicolon()
        return node("Yield", {"value": val})
    }

    :: ── import ──

    func parse_import(self) -> dict {
        self.expect(TK_IMPORT)
        let module: str = self.expect(TK_IDENT).value
        while self.consume(TK_DOT) {
            module = module + "." + self.expect(TK_IDENT).value
        }
        let alias = none
        if self.consume(TK_AS) {
            alias = self.expect(TK_IDENT).value
        }
        self.optional_semicolon()
        return node("Import", {"module": module, "alias": alias, "names": []})
    }

    func parse_from_import(self) -> dict {
        self.expect(TK_FROM)
        let module: str = self.expect(TK_IDENT).value
        while self.consume(TK_DOT) {
            module = module + "." + self.expect(TK_IDENT).value
        }
        self.expect(TK_IMPORT)
        let names: list = []
        if self.consume(TK_LPAREN) {
            while not self.at(TK_RPAREN) and not self.at(TK_EOF) {
                names.append(self.expect(TK_IDENT).value)
                self.consume(TK_COMMA)
            }
            self.expect(TK_RPAREN)
        } else {
            names.append(self.expect(TK_IDENT).value)
        }
        self.optional_semicolon()
        return node("Import", {"module": module, "alias": none, "names": names})
    }

    :: ── try / except ──

    func parse_try(self) -> dict {
        self.expect(TK_TRY)
        let try_body = self.parse_block()
        let excepts: list = []
        let finally_body = none

        while self.at(TK_EXCEPT) {
            self.advance()
            let exc_type = none
            let exc_name = none
            if not self.at(TK_LBRACE) {
                exc_type = self.expect(TK_IDENT).value
                if self.consume(TK_AS) {
                    exc_name = self.expect(TK_IDENT).value
                }
            }
            let exc_body = self.parse_block()
            excepts.append({"type": exc_type, "name": exc_name, "body": exc_body})
        }

        if self.consume(TK_FINALLY) {
            finally_body = self.parse_block()
        }

        return node("Try", {"body": try_body, "excepts": excepts, "finally": finally_body})
    }

    :: ── raise ──

    func parse_raise(self) -> dict {
        self.expect(TK_RAISE)
        let exc = none
        if not self.at(TK_SEMICOLON) and not self.at(TK_EOF) {
            exc = self.parse_expression()
        }
        self.optional_semicolon()
        return node("Raise", {"exc": exc})
    }

    :: ── match ──

    func parse_match(self) -> dict {
        self.expect(TK_MATCH)
        let subject = self.parse_expression()
        self.expect(TK_LBRACE)
        let cases: list = []
        let default_body = none

        while not self.at(TK_RBRACE) and not self.at(TK_EOF) {
            if self.consume(TK_DEFAULT) {
                self.consume(TK_COLON)
                default_body = self.parse_block()
            } else {
                self.expect(TK_CASE)
                let pattern = self.parse_expression()
                let guard = none
                if self.consume(TK_IF) {
                    guard = self.parse_expression()
                }
                self.consume(TK_COLON)
                let case_body = self.parse_block()
                cases.append({"pattern": pattern, "guard": guard, "body": case_body})
            }
        }

        self.expect(TK_RBRACE)
        return node("Match", {"subject": subject, "cases": cases, "default": default_body})
    }

    :: ── unsafe / safe blocks ──

    func parse_unsafe(self) -> dict {
        self.expect(TK_UNSAFE)
        return node("Unsafe", {"body": self.parse_block()})
    }

    func parse_safe(self) -> dict {
        self.expect(TK_SAFE)
        return node("Safe", {"body": self.parse_block()})
    }

    :: ── borrow / release / move ──

    func parse_borrow(self) -> dict {
        self.expect(TK_BORROW)
        let is_mut: bool = self.consume(TK_MUT)
        let name: str = self.expect(TK_IDENT).value
        self.optional_semicolon()
        return node("Borrow", {"var": name, "mutable": is_mut})
    }

    func parse_release(self) -> dict {
        self.expect(TK_RELEASE)
        let name: str = self.expect(TK_IDENT).value
        self.optional_semicolon()
        return node("Release", {"var": name})
    }

    func parse_move(self) -> dict {
        self.expect(TK_MOVE)
        let name: str = self.expect(TK_IDENT).value
        self.expect(TK_ARROW)
        let target = self.parse_expression()
        self.optional_semicolon()
        return node("Move", {"var": name, "target": target})
    }

    :: ── type alias ──

    func parse_type_alias(self) -> dict {
        self.expect(TK_TYPE)
        let name: str = self.expect(TK_IDENT).value
        self.expect(TK_ASSIGN)
        let expr: str = self.parse_type_expr()
        self.optional_semicolon()
        return node("TypeAlias", {"name": name, "expr": expr})
    }

    :: ── interface ──

    func parse_interface(self) -> dict {
        self.expect(TK_INTERFACE)
        let name: str = self.expect(TK_IDENT).value
        let extends: list = []
        if self.consume(TK_EXTENDS) {
            extends.append(self.expect(TK_IDENT).value)
            while self.consume(TK_COMMA) {
                extends.append(self.expect(TK_IDENT).value)
            }
        }
        self.expect(TK_LBRACE)
        let sigs: list = []
        while not self.at(TK_RBRACE) and not self.at(TK_EOF) {
            if self.at(TK_FUNC) or self.at(TK_FN) {
                self.advance()
                let n: str = self.expect(TK_IDENT).value
                self.expect(TK_LPAREN)
                let ps: list = self.parse_params()
                self.expect(TK_RPAREN)
                let rt = none
                if self.consume(TK_ARROW) { rt = self.parse_type_expr() }
                self.optional_semicolon()
                sigs.append({"name": n, "params": ps, "return_type": rt})
            } else {
                self.advance()  ## skip unexpected token
            }
        }
        self.expect(TK_RBRACE)
        return node("Interface", {"name": name, "extends": extends, "signatures": sigs})
    }

    :: ── enum ──

    func parse_enum(self) -> dict {
        self.expect(TK_ENUM)
        let name: str = self.expect(TK_IDENT).value
        self.expect(TK_LBRACE)
        let variants: list = []
        while not self.at(TK_RBRACE) and not self.at(TK_EOF) {
            let vname: str = self.expect(TK_IDENT).value
            let vval = none
            if self.consume(TK_ASSIGN) { vval = self.parse_expression() }
            variants.append({"name": vname, "value": vval})
            self.consume(TK_COMMA)
        }
        self.expect(TK_RBRACE)
        return node("Enum", {"name": name, "variants": variants})
    }

    :: ── decorators ──

    func parse_decorated(self) -> dict {
        let decorators: list = []
        while self.at(TK_AT) {
            self.advance()
            let dec_name: str = self.expect(TK_IDENT).value
            let dec_args: list = []
            if self.consume(TK_LPAREN) {
                while not self.at(TK_RPAREN) and not self.at(TK_EOF) {
                    dec_args.append(self.parse_expression())
                    self.consume(TK_COMMA)
                }
                self.expect(TK_RPAREN)
            }
            decorators.append({"name": dec_name, "args": dec_args})
        }
        let inner = self.parse_statement()
        inner["decorators"] = decorators
        return inner
    }

    :: ── print ──

    func parse_print_stmt(self) -> dict {
        self.expect(TK_PRINT)
        self.expect(TK_LPAREN)
        let args: list = []
        while not self.at(TK_RPAREN) and not self.at(TK_EOF) {
            args.append(self.parse_expression())
            self.consume(TK_COMMA)
        }
        self.expect(TK_RPAREN)
        self.optional_semicolon()
        return node("Print", {"args": args})
    }

    :: ── thread ──

    func parse_thread(self) -> dict {
        self.expect(TK_THREAD)
        let fn_expr = self.parse_expression()
        let args: list = []
        if self.consume(TK_LPAREN) {
            while not self.at(TK_RPAREN) and not self.at(TK_EOF) {
                args.append(self.parse_expression())
                self.consume(TK_COMMA)
            }
            self.expect(TK_RPAREN)
        }
        self.optional_semicolon()
        return node("Thread", {"func": fn_expr, "args": args})
    }

    :: ── block ──

    func parse_block(self) -> list {
        self.expect(TK_LBRACE)
        let stmts: list = []
        while not self.at(TK_RBRACE) and not self.at(TK_EOF) {
            let s = self.parse_statement()
            if s != none { stmts.append(s) }
        }
        self.expect(TK_RBRACE)
        return stmts
    }

    :: ── expressions (Pratt-style precedence climbing) ──

    func parse_expression(self) -> dict {
        return self.parse_assignment()
    }

    func parse_assignment(self) -> dict {
        let left = self.parse_ternary()
        let k: str = self.peek_kind()
        let compound: list = [TK_ASSIGN, TK_PLUS_EQ, TK_MINUS_EQ, TK_STAR_EQ, TK_SLASH_EQ]
        if k in compound {
            let op: str = self.advance().value
            let right = self.parse_assignment()
            return node("Assign", {"target": left, "op": op, "value": right})
        }
        return left
    }

    func parse_ternary(self) -> dict {
        let expr = self.parse_or()
        if self.consume(TK_IF) {
            let cond = self.parse_or()
            self.expect(TK_ELSE)
            let alt  = self.parse_ternary()
            return node("Ternary", {"then": expr, "cond": cond, "alt": alt})
        }
        return expr
    }

    func parse_or(self) -> dict {
        let left = self.parse_and()
        while self.at(TK_OR) {
            self.advance()
            let right = self.parse_and()
            left = node("BinOp", {"left": left, "op": "or", "right": right})
        }
        return left
    }

    func parse_and(self) -> dict {
        let left = self.parse_not()
        while self.at(TK_AND) {
            self.advance()
            let right = self.parse_not()
            left = node("BinOp", {"left": left, "op": "and", "right": right})
        }
        return left
    }

    func parse_not(self) -> dict {
        if self.at(TK_NOT) {
            self.advance()
            return node("UnaryOp", {"op": "not", "operand": self.parse_not()})
        }
        return self.parse_comparison()
    }

    func parse_comparison(self) -> dict {
        let left = self.parse_bitor()
        let cmp_ops: list = [TK_EQ, TK_NEQ, TK_LT, TK_GT, TK_LE, TK_GE, TK_IS, TK_IN]
        while self.at_any(cmp_ops) {
            let op: str = self.advance().value
            let right = self.parse_bitor()
            left = node("BinOp", {"left": left, "op": op, "right": right})
        }
        return left
    }

    func parse_bitor(self) -> dict {
        let left = self.parse_bitxor()
        while self.at(TK_PIPE_OP) {
            self.advance()
            let right = self.parse_bitxor()
            left = node("BinOp", {"left": left, "op": "|", "right": right})
        }
        return left
    }

    func parse_bitxor(self) -> dict {
        let left = self.parse_bitand()
        while self.at(TK_CARET) {
            self.advance()
            let right = self.parse_bitand()
            left = node("BinOp", {"left": left, "op": "^", "right": right})
        }
        return left
    }

    func parse_bitand(self) -> dict {
        let left = self.parse_shift()
        while self.at(TK_AMPERSAND) {
            self.advance()
            let right = self.parse_shift()
            left = node("BinOp", {"left": left, "op": "&", "right": right})
        }
        return left
    }

    func parse_shift(self) -> dict {
        let left = self.parse_additive()
        while self.at(TK_LSHIFT) or self.at(TK_RSHIFT) {
            let op: str = self.advance().value
            let right = self.parse_additive()
            left = node("BinOp", {"left": left, "op": op, "right": right})
        }
        return left
    }

    func parse_additive(self) -> dict {
        let left = self.parse_multiplicative()
        while self.at(TK_PLUS) or self.at(TK_MINUS) {
            let op: str = self.advance().value
            let right = self.parse_multiplicative()
            left = node("BinOp", {"left": left, "op": op, "right": right})
        }
        return left
    }

    func parse_multiplicative(self) -> dict {
        let left = self.parse_unary()
        while self.at_any([TK_STAR, TK_SLASH, TK_PERCENT]) {
            let op: str = self.advance().value
            let right = self.parse_unary()
            left = node("BinOp", {"left": left, "op": op, "right": right})
        }
        return left
    }

    func parse_unary(self) -> dict {
        if self.at(TK_MINUS) {
            self.advance()
            return node("UnaryOp", {"op": "-", "operand": self.parse_unary()})
        }
        if self.at(TK_TILDE) {
            self.advance()
            return node("UnaryOp", {"op": "~", "operand": self.parse_unary()})
        }
        if self.at(TK_BANG) {
            self.advance()
            return node("UnaryOp", {"op": "!", "operand": self.parse_unary()})
        }
        if self.at(TK_AWAIT) {
            self.advance()
            return node("Await", {"expr": self.parse_unary()})
        }
        return self.parse_power()
    }

    func parse_power(self) -> dict {
        let base = self.parse_postfix()
        if self.at(TK_POWER) {
            self.advance()
            let exp = self.parse_unary()  ## right-associative
            return node("BinOp", {"left": base, "op": "**", "right": exp})
        }
        return base
    }

    func parse_postfix(self) -> dict {
        let expr = self.parse_primary()
        while true {
            if self.at(TK_DOT) {
                self.advance()
                let member: str = self.advance().value
                expr = node("Member", {"obj": expr, "member": member})
            } elif self.at(TK_LBRACKET) {
                self.advance()
                if self.at(TK_COLON) {
                    :: slice [:stop]
                    self.advance()
                    let stop = self.parse_expression()
                    self.expect(TK_RBRACKET)
                    expr = node("Slice", {"obj": expr, "start": none, "stop": stop, "step": none})
                } else {
                    let idx = self.parse_expression()
                    if self.consume(TK_COLON) {
                        let stop = self.parse_expression()
                        self.expect(TK_RBRACKET)
                        expr = node("Slice", {"obj": expr, "start": idx, "stop": stop, "step": none})
                    } else {
                        self.expect(TK_RBRACKET)
                        expr = node("Index", {"obj": expr, "index": idx})
                    }
                }
            } elif self.at(TK_LPAREN) {
                :: function call
                self.advance()
                let args: list = []
                let kwargs: dict = {}
                while not self.at(TK_RPAREN) and not self.at(TK_EOF) {
                    :: keyword arg?
                    if self.at(TK_IDENT) and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].kind == TK_ASSIGN {
                        let kname: str = self.advance().value
                        self.advance()  ## consume =
                        kwargs[kname] = self.parse_expression()
                    } else {
                        args.append(self.parse_expression())
                    }
                    if not self.consume(TK_COMMA) { break }
                }
                self.expect(TK_RPAREN)
                expr = node("Call", {"func": expr, "args": args, "kwargs": kwargs})
            } elif self.at(TK_PIPE) {
                :: pipe operator |>
                self.advance()
                let fn_expr = self.parse_primary()
                expr = node("Call", {"func": fn_expr, "args": [expr], "kwargs": {}})
            } else {
                break
            }
        }
        return expr
    }

    :: ── primary expressions ──

    func parse_primary(self) -> dict {
        let k: str = self.peek_kind()
        let t: dict = self.cur()

        if k == TK_INT   { self.advance(); return node("Literal", {"type": "int",   "value": t.value}) }
        if k == TK_FLOAT { self.advance(); return node("Literal", {"type": "float", "value": t.value}) }
        if k == TK_HEX   { self.advance(); return node("Literal", {"type": "hex",   "value": t.value}) }
        if k == TK_BIN   { self.advance(); return node("Literal", {"type": "bin",   "value": t.value}) }
        if k == TK_STRING   { self.advance(); return node("Literal", {"type": "str",    "value": t.value}) }
        if k == TK_FSTRING  { self.advance(); return node("FString", {"raw": t.value}) }
        if k == TK_BOOL  { self.advance(); return node("Literal", {"type": "bool", "value": t.value}) }
        if k == TK_NONE  { self.advance(); return node("Literal", {"type": "none", "value": none}) }

        if k == TK_IDENT {
            self.advance()
            return node("Ident", {"name": t.value})
        }

        if k == TK_SELF  { self.advance(); return node("Ident", {"name": "self"}) }
        if k == TK_SUPER { self.advance(); return node("Ident", {"name": "super"}) }
        if k == TK_NEW   {
            self.advance()
            let cls_name: str = self.expect(TK_IDENT).value
            self.expect(TK_LPAREN)
            let args: list = []
            while not self.at(TK_RPAREN) and not self.at(TK_EOF) {
                args.append(self.parse_expression())
                self.consume(TK_COMMA)
            }
            self.expect(TK_RPAREN)
            return node("New", {"class": cls_name, "args": args})
        }

        if k == TK_LPAREN {
            self.advance()
            let expr = self.parse_expression()
            self.expect(TK_RPAREN)
            return expr
        }

        if k == TK_LBRACKET {
            :: list literal or list comprehension
            self.advance()
            if self.at(TK_RBRACKET) { self.advance(); return node("List", {"elements": []}) }
            let first = self.parse_expression()
            if self.consume(TK_FOR) {
                :: list comprehension [expr for var in iterable if cond]
                let var_name: str = self.expect(TK_IDENT).value
                self.expect(TK_IN)
                let iter = self.parse_expression()
                let cond = none
                if self.consume(TK_IF) { cond = self.parse_expression() }
                self.expect(TK_RBRACKET)
                return node("ListComp", {"expr": first, "var": var_name, "iter": iter, "cond": cond})
            }
            let elems: list = [first]
            while self.consume(TK_COMMA) and not self.at(TK_RBRACKET) {
                elems.append(self.parse_expression())
            }
            self.expect(TK_RBRACKET)
            return node("List", {"elements": elems})
        }

        if k == TK_LBRACE {
            :: dict or set literal
            self.advance()
            if self.at(TK_RBRACE) { self.advance(); return node("Dict", {"pairs": []}) }
            let fkey = self.parse_expression()
            if self.consume(TK_COLON) {
                :: dict
                let fval = self.parse_expression()
                let pairs: list = [[fkey, fval]]
                while self.consume(TK_COMMA) and not self.at(TK_RBRACE) {
                    let dk = self.parse_expression()
                    self.expect(TK_COLON)
                    let dv = self.parse_expression()
                    pairs.append([dk, dv])
                }
                self.expect(TK_RBRACE)
                return node("Dict", {"pairs": pairs})
            }
            :: set
            let set_elems: list = [fkey]
            while self.consume(TK_COMMA) and not self.at(TK_RBRACE) {
                set_elems.append(self.parse_expression())
            }
            self.expect(TK_RBRACE)
            return node("Set", {"elements": set_elems})
        }

        :: lambda: (params) => expr
        if k == TK_FAT_ARROW {
            :: edge case: standalone =>
            self.advance()
            let lbody = self.parse_expression()
            return node("Lambda", {"params": [], "body": lbody})
        }

        :: fallthrough — unknown token
        self.error(f"Unexpected token in expression: {t.kind} ('{t.value}')", t)
        self.advance()
        return node("Error", {"token": t.value})
    }
}

:: ─── Public API ─────────────────────────────────────────────────────────────

func parse(tokens: list, source: str, filename: str) -> dict {
    let p: Parser = new Parser(tokens, source, filename)
    let ast = p.parse_program()
    return {
        "ast":    ast,
        "errors": p.errors,
    }
}
