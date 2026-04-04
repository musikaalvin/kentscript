#!/usr/bin/env python3
"""
KentScript Unified Lexer - Python Implementation
Full-featured lexer for KentScript tokenization

NOTE: The canonical lexer is lexer_unified.ks (KentScript implementation)
This Python version provides the same functionality for bootstrapping
"""

from enum import IntEnum
from dataclasses import dataclass
from typing import List, Optional
import os
import sys

# Import error handler for nice error messages
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from error_handler import KSError


# Edit distance for typo detection
def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        return levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def suggest(text: str, candidates: list, max_dist: int = 1) -> Optional[str]:
    """Suggest a candidate with edit distance <= max_dist. Only for short identifiers."""
    if len(text) < 3 or len(text) > 10:
        return None  # Only check 3-10 char identifiers
    best = None
    best_dist = max_dist + 1
    for c in candidates:
        if abs(len(text) - len(c)) > 1:
            continue
        d = levenshtein(text, c)
        if d < best_dist:
            best_dist = d
            best = c
    return best if best_dist <= max_dist else None


# Token types - matches unified_lexer.ks exactly
class TokenType(IntEnum):
    # Special
    EOF = 0
    ERROR = 1
    COMMENT = 2

    # Core keywords (~38) — language syntax only, like Python's 35
    LET = 10
    CONST = 11
    MUT = 12
    FUNC = 13
    RETURN = 14
    IF = 15
    ELIF = 16
    ELSE = 17
    WHILE = 18
    FOR = 19
    IN = 20
    MATCH = 21
    CASE = 22
    DEFAULT = 23
    ENUM = 24
    STRUCT = 25
    CLASS = 26
    IMPORT = 27
    FROM = 28
    AS = 29
    BREAK = 30
    CONTINUE = 31
    TRY = 32
    EXCEPT = 33
    FINALLY = 34
    RAISE = 35
    ASYNC = 36
    AWAIT = 37
    YIELD = 38
    UNSAFE = 39
    SAFE = 40
    SELF = 41
    SUPER = 42
    EXTENDS = 43
    INTERFACE = 44
    TYPE = 45
    EXPORT = 46
    IMPLEMENTS = 47

    # Literals
    TRUE = 48
    FALSE = 49
    NONE = 50
    IDENTIFIER = 51
    NUMBER = 52
    STRING = 53
    STRING_LIT = 53  # Alias for STRING
    FSTRING = 54
    HEX_NUMBER = 55
    BIN_NUMBER = 56
    FLOAT_NUMBER = 57

    # Type names — kept as token types for parser compatibility,
    # but NOT in KEYWORDS dict so they lex as IDENTIFIER (like Python's int/str/bool)
    I8 = 200
    I16 = 201
    I32 = 202
    I64 = 203
    U8 = 204
    U16 = 205
    U32 = 206
    U64 = 207
    F32 = 208
    F64 = 209
    BOOL = 210
    STR = 211
    CHAR = 212
    VOID = 213
    INT = 214
    UINT = 215
    FLOAT = 216
    PTR = 217

    # Operators - Arithmetic
    PLUS = 58
    MINUS = 59
    STAR = 60
    MULTIPLY = 60  # Alias for STAR
    SLASH = 61
    DIVIDE = 61  # Alias for SLASH
    PERCENT = 62
    MODULO = 62  # Alias for PERCENT
    POWER = 63
    FLOOR_DIVIDE = 64

    # Operators - Assignment
    ASSIGN = 65
    PLUS_ASSIGN = 66
    MINUS_ASSIGN = 67
    STAR_ASSIGN = 68
    MULTIPLY_ASSIGN = 68  # Alias for STAR_ASSIGN
    SLASH_ASSIGN = 69
    DIVIDE_ASSIGN = 69  # Alias for SLASH_ASSIGN
    MODULO_ASSIGN = 70
    POWER_ASSIGN = 71
    BIT_AND_ASSIGN = 72
    BIT_OR_ASSIGN = 73
    BIT_XOR_ASSIGN = 74
    LSHIFT_ASSIGN = 75
    RSHIFT_ASSIGN = 76

    # Operators - Increment/Decrement
    PLUS_PLUS = 77
    MINUS_MINUS = 78

    # Operators - Comparison
    EQ = 79
    NE = 80
    LT = 81
    GT = 82
    LE = 83
    GE = 84

    # Operators - Logical
    AND = 85
    OR = 86
    NOT = 87

    # Operators - Bitwise
    BIT_AND = 88
    BIT_OR = 89
    BIT_XOR = 90
    BIT_NOT = 91
    LSHIFT = 92
    RSHIFT = 93

    # Punctuation
    LPAREN = 94
    RPAREN = 95
    LBRACE = 96
    RBRACE = 97
    LBRACKET = 98
    RBRACKET = 99
    SEMICOLON = 100
    COMMA = 101
    DOT = 102
    COLON = 103
    COLONCOLON = 104
    ARROW = 105
    FAT_ARROW = 106
    QUESTION = 107
    AT = 108
    BACKTICK = 109
    PIPE = 110
    INCLUSIVE_RANGE = 111
    ELLIPSIS = 112

    # Former keywords — kept as token types for parser compatibility,
    # but NOT in KEYWORDS so they lex as IDENTIFIER (Python-style)
    # These are now builtin functions, decorators, or stdlib modules
    NEW = 300
    CLS = 301
    RANGE = 302
    PRINT = 303
    THREAD = 304
    PUB = 305
    PRIV = 306
    GENFUNC = 307
    BORROW = 308
    RELEASE = 309
    MOVE = 310
    WITH = 311
    ASSERT = 312
    DEL = 313
    PASS = 314
    GLOBAL = 315
    NONLOCAL = 316
    UNION = 317
    DO = 318
    SWITCH = 319
    GOTO = 320
    SIZEOF = 321
    STATIC = 322
    INLINE = 323
    VOLATILE = 324
    ASM = 325
    MODULE = 326
    TO = 327  # for move x to y syntax
    LAMBDA = 327


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int


# Keyword mapping — ~38 essential keywords (Python has 35)
# Everything else is a builtin function or stdlib module
KEYWORDS = {
    # Declarations
    "let": TokenType.LET,
    "const": TokenType.CONST,
    "mut": TokenType.MUT,
    "func": TokenType.FUNC,
    "new": TokenType.NEW,
    "return": TokenType.RETURN,
    # Control flow
    "if": TokenType.IF,
    "elif": TokenType.ELIF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "to": TokenType.TO,  # for move x to y syntax
    # Pattern matching
    "match": TokenType.MATCH,
    "case": TokenType.CASE,
    "default": TokenType.DEFAULT,
    # Loop control
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    # Error handling
    "try": TokenType.TRY,
    "except": TokenType.EXCEPT,
    "catch": TokenType.EXCEPT,  # catch is alias for except
    "finally": TokenType.FINALLY,
    "raise": TokenType.RAISE,
    "move": TokenType.MOVE,  # for move x to y syntax
    "borrow": TokenType.BORROW,  # for borrow x syntax
    "release": TokenType.RELEASE,  # for release x syntax
    # Modules
    "import": TokenType.IMPORT,
    "from": TokenType.FROM,
    "as": TokenType.AS,
    "export": TokenType.EXPORT,
    # OOP
    "class": TokenType.CLASS,
    "struct": TokenType.STRUCT,
    "enum": TokenType.ENUM,
    "interface": TokenType.INTERFACE,
    "extends": TokenType.EXTENDS,
    "implements": TokenType.IMPLEMENTS,
    # Type system
    "type": TokenType.TYPE,
    # Async
    "async": TokenType.ASYNC,
    "await": TokenType.AWAIT,
    # Generators
    "yield": TokenType.YIELD,
    "lambda": TokenType.LAMBDA,
    # Memory safety
    "unsafe": TokenType.UNSAFE,
    "safe": TokenType.SAFE,
    # Self reference
    "self": TokenType.SELF,
    "super": TokenType.SUPER,
    # Logical operators
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    # Literals
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "none": TokenType.NONE,
}


class Lexer:
    def __init__(
        self, source: str, auto_insert_semicolons: bool = False, filename: str = None
    ):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.auto_insert_semicolons = auto_insert_semicolons
        self.last_token: Optional[Token] = None
        self.filename = filename
        # Set error context
        KSError.set_context(filename=filename, source=source)

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            self._skip_whitespace()
            if self.pos >= len(self.source):
                break

            # Check for :: - distinguish between comment and scope resolution
            if self._peek() == ":" and self._peek(1) == ":":
                # If last token was an identifier, closing bracket/paren, or string, it's scope resolution
                if self.last_token and self.last_token.type in (
                    TokenType.IDENTIFIER,
                    TokenType.RPAREN,
                    TokenType.RBRACKET,
                    TokenType.LBRACKET,
                    TokenType.COLON,
                    TokenType.STRING_LIT,
                    TokenType.STRING,
                ):
                    # This is scope resolution or slice notation - continue to normal tokenization
                    pass
                else:
                    # This is a comment
                    self._skip_line_comment()
                    continue

            # Check for /// doc comments
            if self._peek() == "/" and self._peek(1) == "/" and self._peek(2) == "/":
                self._skip_line_comment()
                continue

            # Check for /* block comments
            if self._peek() == "/" and self._peek(1) == "*":
                self._skip_block_comment()
                continue

            ch = self._peek()
            if ch.isalpha() or ch == "_":
                # Check for f-string
                if ch == "f" and self._peek(1) == '"':
                    self._read_fstring()
                else:
                    self._read_identifier()
            elif ch.isdigit():
                self._read_number()
            elif ch == '"' or ch == "'":
                self._read_string()
            elif ch == "`":
                self._read_backtick()
            else:
                self._read_operator()

            # Auto-insert semicolon if needed
            if self.auto_insert_semicolons:
                self._auto_insert_semicolon()

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens

    def _auto_insert_semicolon(self):
        """Auto-insert semicolon before newline if statement-ending token preceded it."""
        if not self.last_token:
            return
        stmt_enders = (
            TokenType.NUMBER,
            TokenType.STRING,
            TokenType.IDENTIFIER,
            TokenType.TRUE,
            TokenType.FALSE,
            TokenType.NONE,
            TokenType.RPAREN,
            TokenType.RBRACE,
            TokenType.RBRACKET,
        )
        if self.last_token.type in stmt_enders and self._peek() == "\n":
            self.tokens.append(Token(TokenType.SEMICOLON, ";", self.line, self.column))

    def _peek(self, offset=0) -> str:
        pos = self.pos + offset
        return self.source[pos] if pos < len(self.source) else "\0"

    def _advance(self) -> str:
        if self.pos >= len(self.source):
            return "\0"
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _skip_whitespace(self):
        while self._peek() in " \t\r\n":
            self._advance()

    def _skip_line_comment(self):
        # Skip :: or ///
        while self._peek() == ":" or self._peek() == "/":
            self._advance()
        while self._peek() != "\n" and self._peek() != "\0":
            self._advance()

    def _skip_block_comment(self):
        self._advance()  # /
        self._advance()  # *
        while self.pos < len(self.source):
            if self._peek() == "*" and self._peek(1) == "/":
                self._advance()  # *
                self._advance()  # /
                return
            self._advance()
        KSError.syntax_error(
            "Unclosed block comment",
            line=self.line,
            col=self.column,
            hint="Add */ to close",
        )
        return  # recover

    def _read_identifier(self):
        start_line, start_col = self.line, self.column
        value = ""
        while self._peek().isalnum() or self._peek() == "_":
            value += self._advance()

        # Check for func* (generator function)
        if value == "func" and self._peek() == "*":
            value += self._advance()
            token = Token(TokenType.GENFUNC, value, start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return

        token_type = KEYWORDS.get(value, TokenType.IDENTIFIER)

        token = Token(token_type, value, start_line, start_col)
        self.tokens.append(token)
        self.last_token = token

    def _read_number(self):
        start_line, start_col = self.line, self.column
        value = ""

        # Hex numbers
        if self._peek() == "0" and self._peek(1) in "xX":
            value += self._advance()  # 0
            value += self._advance()  # x
            while self._peek().isdigit() or self._peek() in "abcdefABCDEF":
                value += self._advance()
            token = Token(TokenType.HEX_NUMBER, value, start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return

        # Binary numbers
        if self._peek() == "0" and self._peek(1) in "bB":
            value += self._advance()  # 0
            value += self._advance()  # b
            while self._peek() in "01":
                value += self._advance()
            token = Token(TokenType.BIN_NUMBER, value, start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return

        # Octal numbers (0o755)
        if self._peek() == "0" and self._peek(1) in "oO":
            value += self._advance()  # 0
            value += self._advance()  # o
            while self._peek() in "01234567":
                value += self._advance()
            token = Token(TokenType.NUMBER, int(value, 8), start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return

        # Regular number
        while self._peek().isdigit():
            value += self._advance()

        # Float with decimal point
        if self._peek() == "." and self._peek(1).isdigit():
            value += self._advance()
            while self._peek().isdigit():
                value += self._advance()

        # Scientific notation: e+6, e-6, E3, etc.
        if self._peek() in "eE":
            value += self._advance()
            if self._peek() in "+-":
                value += self._advance()
            while self._peek().isdigit():
                value += self._advance()
            token = Token(TokenType.FLOAT_NUMBER, value, start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return

        if "." in value:
            token = Token(TokenType.FLOAT_NUMBER, value, start_line, start_col)
        else:
            token = Token(TokenType.NUMBER, value, start_line, start_col)
        self.tokens.append(token)
        self.last_token = token

    def _read_string(self):
        start_line, start_col = self.line, self.column
        quote_char = self._peek()  # " or '
        self._advance()
        value = ""

        while self._peek() != quote_char and self._peek() != "\0":
            if self._peek() == "\\" and self._peek(1) != "\0":
                self._advance()  # consume backslash
                escape_char = self._peek()
                escape_map = {
                    "n": "\n",
                    "t": "\t",
                    "r": "\r",
                    "\\": "\\",
                    "'": "'",
                    '"': '"',
                    "0": "\0",
                    "a": "\a",
                    "b": "\b",
                    "f": "\f",
                    "v": "\v",
                }
                if escape_char == "x":
                    # Handle hex escape sequence \xHH
                    self._advance()  # consume 'x'
                    hex_digits = ""
                    for _ in range(2):
                        if self._peek() and self._peek() in "0123456789abcdefABCDEF":
                            hex_digits += self._advance()
                        else:
                            break
                    if hex_digits:
                        value += chr(int(hex_digits, 16))
                    else:
                        # No valid hex digits, keep as-is
                        value += "\\x"
                elif escape_char in escape_map:
                    value += escape_map[escape_char]
                    self._advance()  # consume the escaped character
                else:
                    # Unknown escape sequence, keep as-is
                    value += "\\"
                    value += escape_char
                    self._advance()
            else:
                value += self._advance()

        # Check for unterminated string
        if self._peek() == "\0":
            KSError.syntax_error(
                "Unterminated string literal",
                line=self.line,
                col=self.column,
                hint=f"Add a closing {quote_char} to terminate the string",
                start_line=start_line,
                start_col=start_col,
            )
            return  # recover: skip this token and continue

        self._advance()  # closing quote
        token = Token(TokenType.STRING, value, start_line, start_col)
        self.tokens.append(token)
        self.last_token = token

    def _read_fstring(self):
        start_line, start_col = self.line, self.column
        self._advance()  # f
        self._advance()  # "
        parts = []
        current = ""

        while self._peek() != '"' and self._peek() != "\0":
            if self._peek() == "{":
                if current:
                    parts.append(("str", current))
                    current = ""
                self._advance()  # {
                expr = ""
                brace_depth = 1
                while brace_depth > 0 and self._peek() != "\0":
                    if self._peek() == "{":
                        brace_depth += 1
                    elif self._peek() == "}":
                        brace_depth -= 1
                        if brace_depth == 0:
                            break
                    expr += self._advance()
                self._advance()  # }
                parts.append(("expr", expr))
            elif self._peek() == "\\" and self._peek(1) != "\0":
                self._advance()  # consume backslash
                escape_char = self._peek()
                escape_map = {
                    "n": "\n",
                    "t": "\t",
                    "r": "\r",
                    "\\": "\\",
                    "'": "'",
                    '"': '"',
                    "0": "\0",
                    "a": "\a",
                    "b": "\b",
                    "f": "\f",
                    "v": "\v",
                }
                if escape_char == "x":
                    # Handle hex escape sequence \xHH
                    self._advance()  # consume 'x'
                    hex_digits = ""
                    for _ in range(2):
                        if self._peek() and self._peek() in "0123456789abcdefABCDEF":
                            hex_digits += self._advance()
                        else:
                            break
                    if hex_digits:
                        current += chr(int(hex_digits, 16))
                    else:
                        # No valid hex digits, keep as-is
                        current += "\\x"
                elif escape_char in escape_map:
                    current += escape_map[escape_char]
                    self._advance()  # consume the escaped character
                else:
                    # Unknown escape sequence, keep as-is
                    current += "\\"
                    current += escape_char
                    self._advance()
            else:
                current += self._advance()

        if current:
            parts.append(("str", current))

        self._advance()  # "
        token = Token(TokenType.FSTRING, parts, start_line, start_col)
        self.tokens.append(token)
        self.last_token = token

    def _read_backtick(self):
        """Read backtick command execution string."""
        start_line, start_col = self.line, self.column
        self._advance()  # `
        value = ""

        while self._peek() != "`" and self._peek() != "\0":
            if self._peek() == "\\" and self._peek(1) != "\0":
                self._advance()
                value += self._advance()
            else:
                value += self._advance()

        # Check for unterminated backtick string
        if self._peek() == "\0":
            KSError.syntax_error(
                "Unterminated backtick command string",
                line=self.line,
                col=self.column,
                hint="Add a closing ` to terminate the command string",
                start_line=start_line,
                start_col=start_col,
            )
            return  # recover: skip this token and continue

        self._advance()  # closing `
        token = Token(TokenType.BACKTICK, value, start_line, start_col)
        self.tokens.append(token)
        self.last_token = token

    def _read_operator(self):
        start_line, start_col = self.line, self.column
        ch = self._peek()

        # Two-character operators
        if ch == "=" and self._peek(1) == "=":
            self._advance()
            self._advance()
            token = Token(TokenType.EQ, "==", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return
        if ch == "!" and self._peek(1) == "=":
            self._advance()
            self._advance()
            token = Token(TokenType.NE, "!=", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return
        if ch == "<" and self._peek(1) == "=":
            self._advance()
            self._advance()
            token = Token(TokenType.LE, "<=", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return
        if ch == ">" and self._peek(1) == "=":
            self._advance()
            self._advance()
            token = Token(TokenType.GE, ">=", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return
        if ch == "<" and self._peek(1) == "<":
            self._advance()
            if self._peek(1) == "=":
                self._advance()
                self._advance()
                token = Token(TokenType.LSHIFT_ASSIGN, "<<=", start_line, start_col)
            else:
                self._advance()
                token = Token(TokenType.LSHIFT, "<<", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return
        if ch == ">" and self._peek(1) == ">":
            self._advance()
            if self._peek(1) == "=":
                self._advance()
                self._advance()
                token = Token(TokenType.RSHIFT_ASSIGN, ">>=", start_line, start_col)
            else:
                self._advance()
                token = Token(TokenType.RSHIFT, ">>", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return
        if ch == "&" and self._peek(1) == "&":
            self._advance()
            self._advance()
            token = Token(TokenType.AND, "&&", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return
        if ch == "|" and self._peek(1) == "|":
            self._advance()
            self._advance()
            token = Token(TokenType.OR, "||", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return
        if ch == "-" and self._peek(1) == ">":
            self._advance()
            self._advance()
            token = Token(TokenType.ARROW, "->", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return
        if ch == "=" and self._peek(1) == ">":
            self._advance()
            self._advance()
            token = Token(TokenType.FAT_ARROW, "=>", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return
        if ch == "." and self._peek(1) == ".":
            self._advance()
            self._advance()
            if self._peek() == ".":
                self._advance()
                token = Token(TokenType.ELLIPSIS, "...", start_line, start_col)
            elif self._peek() == "=":
                self._advance()
                token = Token(TokenType.INCLUSIVE_RANGE, "..=", start_line, start_col)
            else:
                token = Token(TokenType.RANGE, "..", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return
        if ch == ":" and self._peek(1) == ":":
            self._advance()
            self._advance()
            token = Token(TokenType.COLONCOLON, "::", start_line, start_col)
            self.tokens.append(token)
            self.last_token = token
            return

        # Single-character operators
        self._advance()
        if ch == "+":
            if self._peek() == "=":
                self._advance()
                token = Token(TokenType.PLUS_ASSIGN, "+=", start_line, start_col)
            elif self._peek() == "+":
                self._advance()
                token = Token(TokenType.PLUS_PLUS, "++", start_line, start_col)
            else:
                token = Token(TokenType.PLUS, "+", start_line, start_col)
        elif ch == "-":
            if self._peek() == "=":
                self._advance()
                token = Token(TokenType.MINUS_ASSIGN, "-=", start_line, start_col)
            elif self._peek() == "-":
                self._advance()
                token = Token(TokenType.MINUS_MINUS, "--", start_line, start_col)
            else:
                token = Token(TokenType.MINUS, "-", start_line, start_col)
        elif ch == "*":
            if self._peek() == "*":
                self._advance()
                token = Token(TokenType.POWER, "**", start_line, start_col)
            elif self._peek() == "=":
                self._advance()
                token = Token(TokenType.STAR_ASSIGN, "*=", start_line, start_col)
            else:
                token = Token(TokenType.STAR, "*", start_line, start_col)
        elif ch == "/":
            if self._peek() == "=":
                self._advance()
                token = Token(TokenType.SLASH_ASSIGN, "/=", start_line, start_col)
            elif self._peek() == "/":
                self._advance()
                token = Token(TokenType.FLOOR_DIVIDE, "//", start_line, start_col)
            else:
                token = Token(TokenType.SLASH, "/", start_line, start_col)
        elif ch == "%":
            if self._peek() == "=":
                self._advance()
                token = Token(TokenType.MODULO_ASSIGN, "%=", start_line, start_col)
            else:
                token = Token(TokenType.PERCENT, "%", start_line, start_col)
        elif ch == "^":
            if self._peek() == "=":
                self._advance()
                token = Token(TokenType.BIT_XOR_ASSIGN, "^=", start_line, start_col)
            else:
                token = Token(TokenType.BIT_XOR, "^", start_line, start_col)
        elif ch == "&":
            if self._peek() == "=":
                self._advance()
                token = Token(TokenType.BIT_AND_ASSIGN, "&=", start_line, start_col)
            else:
                token = Token(TokenType.BIT_AND, "&", start_line, start_col)
        elif ch == "|":
            if self._peek() == "=":
                self._advance()
                token = Token(TokenType.BIT_OR_ASSIGN, "|=", start_line, start_col)
            else:
                token = Token(TokenType.BIT_OR, "|", start_line, start_col)
        elif ch == "~":
            token = Token(TokenType.BIT_NOT, "~", start_line, start_col)
        elif ch == "!":
            token = Token(TokenType.NOT, "!", start_line, start_col)
        elif ch == "<":
            if self._peek(1) == "<":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    token = Token(TokenType.LSHIFT_ASSIGN, "<<=", start_line, start_col)
                else:
                    token = Token(TokenType.LSHIFT, "<<", start_line, start_col)
            elif self._peek() == "=":
                self._advance()
                token = Token(TokenType.LE, "<=", start_line, start_col)
            else:
                token = Token(TokenType.LT, "<", start_line, start_col)
        elif ch == ">":
            if self._peek(1) == ">":
                self._advance()
                if self._peek(1) == "=":
                    self._advance()
                    token = Token(TokenType.RSHIFT_ASSIGN, ">>=", start_line, start_col)
                else:
                    token = Token(TokenType.RSHIFT, ">>", start_line, start_col)
            elif self._peek() == "=":
                self._advance()
                token = Token(TokenType.GE, ">=", start_line, start_col)
            else:
                token = Token(TokenType.GT, ">", start_line, start_col)
        elif ch == "=":
            token = Token(TokenType.ASSIGN, "=", start_line, start_col)
        elif ch == ".":
            token = Token(TokenType.DOT, ".", start_line, start_col)
        elif ch == ",":
            token = Token(TokenType.COMMA, ",", start_line, start_col)
        elif ch == ";":
            token = Token(TokenType.SEMICOLON, ";", start_line, start_col)
        elif ch == ":":
            if self._peek() == ":":
                self._advance()
                token = Token(TokenType.COLONCOLON, "::", start_line, start_col)
            else:
                token = Token(TokenType.COLON, ":", start_line, start_col)
        elif ch == "(":
            token = Token(TokenType.LPAREN, "(", start_line, start_col)
        elif ch == ")":
            token = Token(TokenType.RPAREN, ")", start_line, start_col)
        elif ch == "{":
            token = Token(TokenType.LBRACE, "{", start_line, start_col)
        elif ch == "}":
            token = Token(TokenType.RBRACE, "}", start_line, start_col)
        elif ch == "[":
            token = Token(TokenType.LBRACKET, "[", start_line, start_col)
        elif ch == "]":
            token = Token(TokenType.RBRACKET, "]", start_line, start_col)
        elif ch == "?":
            token = Token(TokenType.QUESTION, "?", start_line, start_col)
        elif ch == "@":
            token = Token(TokenType.AT, "@", start_line, start_col)
        else:
            token = Token(TokenType.ERROR, ch, start_line, start_col)
        self.tokens.append(token)
        self.last_token = token
