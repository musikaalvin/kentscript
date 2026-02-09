# kentscript.py
"""
KentScript 2.0 - Enhanced Beautiful Scripting Language
With networking, advanced file I/O, list comprehensions, decorators, and more!
"""

import sys
import os
import re
import math
import random
import json
import time
import datetime
import socket
import urllib.request
import urllib.parse
import urllib.error
import hashlib
import base64
import csv
import importlib.util
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import atexit
import inspect

# ================ OPTIONAL IMPORTS ================
RICH_AVAILABLE = False
PROMPT_TOOLKIT_AVAILABLE = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table  
    from rich.markdown import Markdown
    from rich.traceback import install as install_rich_traceback
    RICH_AVAILABLE = True
    install_rich_traceback(show_locals=False)
    console = Console()
except ImportError:
    class MockConsole:
        def print(self, text, **kwargs):
            clean = re.sub(r'\[.*?\]', '', str(text))
            print(clean)
    console = MockConsole()

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.lexers import PygmentsLexer
    from prompt_toolkit.styles import Style
    from prompt_toolkit.completion import WordCompleter
    from pygments.lexer import RegexLexer, words
    from pygments.token import Keyword, Name, String, Number, Operator, Comment, Punctuation, Text
    PROMPT_TOOLKIT_AVAILABLE = True
    
    class KentScriptLexer(RegexLexer):
        name = 'KentScript'
        aliases = ['kentscript', 'ks']
        filenames = ['*.ks']
        
        tokens = {
            'root': [
                (r'::[^\n]*', Comment.Single),
                (r'#[^\n]*', Comment.Single),
                (words((
                    'let', 'const', 'output', 'print', 'if', 'elif', 'else',
                    'while', 'for', 'in', 'range', 'func', 'return', 'class',
                    'new', 'this', 'self', 'import', 'from', 'as', 'try',
                    'except', 'finally', 'break', 'continue', 'True', 'False',
                    'None', 'and', 'or', 'not', 'match', 'case', 'default',
                    'assert', 'del', 'global', 'yield', 'async', 'await',
                    'decorator', 'type', 'interface', 'enum', 'module'
                ), suffix=r'\b'), Keyword),
                (r'"[^"]*"', String.Double),
                (r"'[^']*'", String.Single),
                (r'f"[^"]*"', String.Double),
                (r'\d+\.\d+', Number.Float),
                (r'\d+', Number.Integer),
                (r'[a-zA-Z_][a-zA-Z0-9_]*', Name),
                (r'[+\-*/%]', Operator),
                (r'[<>=!]=?', Operator),
                (r'[(){}[\],;:.]', Punctuation),
                (r'\s+', Text),
            ]
        }
except ImportError:
    pass

# ================ TOKEN ENUM ================
class TokenType(Enum):
    # Keywords
    LET = auto()
    CONST = auto()
    OUTPUT = auto()
    PRINT = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    RANGE = auto()
    FUNC = auto()
    RETURN = auto()
    CLASS = auto()
    NEW = auto()
    THIS = auto()
    SELF = auto()
    IMPORT = auto()
    FROM = auto()
    AS = auto()
    TRY = auto()
    EXCEPT = auto()
    FINALLY = auto()
    BREAK = auto()
    CONTINUE = auto()
    TRUE = auto()
    FALSE = auto()
    NONE = auto()
    AND = auto()
    OR = auto()
    NOT_KEYWORD = auto()
    
    # Additional keywords
    MATCH = auto()
    CASE = auto()
    DEFAULT = auto()
    ASSERT = auto()
    DEL = auto()
    GLOBAL = auto()
    YIELD = auto()
    ASYNC = auto()
    AWAIT = auto()
    DECORATOR = auto()
    TYPE = auto()
    INTERFACE = auto()
    ENUM = auto()
    MODULE = auto()
    
    # Identifiers and literals
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    FSTRING = auto()
    
    # Operators
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    MODULO = auto()
    POWER = auto()
    ASSIGN = auto()
    PLUS_EQ = auto()
    MINUS_EQ = auto()
    MULT_EQ = auto()
    DIV_EQ = auto()
    MOD_EQ = auto()
    POWER_EQ = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    NOT_OP = auto()
    NOT_IN = auto()
    IS = auto()
    IS_NOT = auto()
    
    # Bitwise operators
    BIT_AND = auto()
    BIT_OR = auto()
    BIT_XOR = auto()
    BIT_NOT = auto()
    LSHIFT = auto()
    RSHIFT = auto()
    
    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    COLON = auto()
    SEMICOLON = auto()
    DOT = auto()
    ARROW = auto()
    ELLIPSIS = auto()
    AT = auto()
    
    # Special
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()
    COMMENT = auto()
    DOCSTRING = auto()

# Token type to string mapping
TOKEN_STRINGS = {
    TokenType.LET: "let", TokenType.CONST: "const", TokenType.OUTPUT: "output",
    TokenType.PRINT: "print", TokenType.IF: "if", TokenType.ELIF: "elif",
    TokenType.ELSE: "else", TokenType.WHILE: "while", TokenType.FOR: "for",
    TokenType.IN: "in", TokenType.RANGE: "range", TokenType.FUNC: "func",
    TokenType.RETURN: "return", TokenType.CLASS: "class", TokenType.NEW: "new",
    TokenType.THIS: "this", TokenType.SELF: "self", TokenType.IMPORT: "import",
    TokenType.FROM: "from", TokenType.AS: "as", TokenType.TRY: "try",
    TokenType.EXCEPT: "except", TokenType.FINALLY: "finally", TokenType.BREAK: "break",
    TokenType.CONTINUE: "continue", TokenType.TRUE: "True", TokenType.FALSE: "False",
    TokenType.NONE: "None", TokenType.AND: "and", TokenType.OR: "or",
    TokenType.NOT_KEYWORD: "not", TokenType.MATCH: "match", TokenType.CASE: "case",
    TokenType.DEFAULT: "default", TokenType.ASSERT: "assert", TokenType.DEL: "del",
    TokenType.GLOBAL: "global", TokenType.YIELD: "yield", TokenType.ASYNC: "async",
    TokenType.AWAIT: "await", TokenType.DECORATOR: "decorator", TokenType.TYPE: "type",
    TokenType.INTERFACE: "interface", TokenType.ENUM: "enum", TokenType.MODULE: "module",
    TokenType.PLUS: "+", TokenType.MINUS: "-", TokenType.MULTIPLY: "*",
    TokenType.DIVIDE: "/", TokenType.MODULO: "%", TokenType.POWER: "**",
    TokenType.ASSIGN: "=", TokenType.PLUS_EQ: "+=", TokenType.MINUS_EQ: "-=",
    TokenType.MULT_EQ: "*=", TokenType.DIV_EQ: "/=", TokenType.MOD_EQ: "%=",
    TokenType.POWER_EQ: "**=", TokenType.EQ: "==", TokenType.NE: "!=",
    TokenType.LT: "<", TokenType.GT: ">", TokenType.LE: "<=", TokenType.GE: ">=",
    TokenType.NOT_OP: "!", TokenType.NOT_IN: "not in", TokenType.IS: "is",
    TokenType.IS_NOT: "is not", TokenType.BIT_AND: "&", TokenType.BIT_OR: "|",
    TokenType.BIT_XOR: "^", TokenType.BIT_NOT: "~", TokenType.LSHIFT: "<<",
    TokenType.RSHIFT: ">>", TokenType.LPAREN: "(", TokenType.RPAREN: ")",
    TokenType.LBRACE: "{", TokenType.RBRACE: "}", TokenType.LBRACKET: "[",
    TokenType.RBRACKET: "]", TokenType.COMMA: ",", TokenType.COLON: ":",
    TokenType.SEMICOLON: ";", TokenType.DOT: ".", TokenType.ARROW: "->",
    TokenType.ELLIPSIS: "...", TokenType.AT: "@",
}

# ================ LEXER ================
@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int
    filename: str = ""

class Lexer:
    def __init__(self, text: str, filename: str = ""):
        self.text = text
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.indent_stack = [0]
        self.tokens = []
        
    def tokenize(self):
        """Main tokenization method"""
        while self.pos < len(self.text):
            self._skip_whitespace()
            if self.pos >= len(self.text):
                break
            
            char = self.text[self.pos]
            
            # Comments
            if char == '#' or (char == ':' and self.pos + 1 < len(self.text) and self.text[self.pos + 1] == ':'):
                self._skip_comment()
                continue
            
            # Strings
            if char in ('"', "'"):
                self._read_string()
                continue
            
            # Numbers
            if char.isdigit() or (char == '.' and self.pos + 1 < len(self.text) and self.text[self.pos + 1].isdigit()):
                self._read_number()
                continue
            
            # Identifiers and keywords
            if char.isalpha() or char == '_':
                self._read_identifier()
                continue
            
            # Operators and delimiters
            token = self._read_operator()
            if token:
                self.tokens.append(token)
                continue
            
            # Newlines and indentation
            if char == '\n':
                self._handle_newline()
                continue
            
            # Unknown character
            if char not in ' \t\r':
                print(f"Warning: Skipping unknown character '{char}' at line {self.line}, col {self.col}")
            self.pos += 1
            self.col += 1
        
        # Add dedent tokens
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, None, self.line, self.col, self.filename))
        
        # Add EOF
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.col, self.filename))
        return self.tokens
    
    def _skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos].isspace() and self.text[self.pos] != '\n':
            self.pos += 1
            self.col += 1
    
    def _skip_comment(self):
        """Skip single-line comments starting with :: or #"""
        if self.text[self.pos] == ':':
            self.pos += 2
            self.col += 2
        else:
            self.pos += 1
            self.col += 1
        
        while self.pos < len(self.text) and self.text[self.pos] != '\n':
            self.pos += 1
            self.col += 1
    
    def _read_string(self):
        start_pos = self.pos
        start_line = self.line
        start_col = self.col
        delimiter = self.text[self.pos]
        self.pos += 1
        self.col += 1
        
        value = ""
        is_fstring = False
        
        # Check for f-string
        if delimiter == '"' and start_pos > 0 and self.text[start_pos-1] == 'f':
            is_fstring = True
        
        while self.pos < len(self.text):
            if self.text[self.pos] == '\\':
                self.pos += 1
                self.col += 1
                if self.pos < len(self.text):
                    if self.text[self.pos] == 'n':
                        value += '\n'
                    elif self.text[self.pos] == 't':
                        value += '\t'
                    elif self.text[self.pos] == 'r':
                        value += '\r'
                    elif self.text[self.pos] == delimiter:
                        value += delimiter
                    else:
                        value += self.text[self.pos]
                self.pos += 1
                self.col += 1
            elif self.text[self.pos] == '\n':
                self.line += 1
                self.col = 1
                self.pos += 1
                value += '\n'
            elif self.text[self.pos] == delimiter:
                self.pos += 1
                self.col += 1
                break
            else:
                value += self.text[self.pos]
                self.pos += 1
                self.col += 1
        
        token_type = TokenType.FSTRING if is_fstring else TokenType.STRING
        self.tokens.append(Token(token_type, value, start_line, start_col, self.filename))
    
    def _read_number(self):
        start_pos = self.pos
        start_line = self.line
        start_col = self.col
        
        # Read digits before decimal point
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.pos += 1
            self.col += 1
        
        # Check for decimal point
        if self.pos < len(self.text) and self.text[self.pos] == '.' and self.pos + 1 < len(self.text) and self.text[self.pos + 1].isdigit():
            self.pos += 1
            self.col += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
                self.col += 1
        
        value = self.text[start_pos:self.pos]
        number = float(value) if '.' in value else int(value)
        self.tokens.append(Token(TokenType.NUMBER, number, start_line, start_col, self.filename))
    
    def _read_identifier(self):
        start_pos = self.pos
        start_line = self.line
        start_col = self.col
        
        while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] == '_'):
            self.pos += 1
            self.col += 1
        
        value = self.text[start_pos:self.pos]
        
        # Check if it's a keyword
        keywords = {
            'let': TokenType.LET, 'const': TokenType.CONST, 'print': TokenType.PRINT,
            'output': TokenType.OUTPUT, 'if': TokenType.IF, 'elif': TokenType.ELIF,
            'else': TokenType.ELSE, 'while': TokenType.WHILE, 'for': TokenType.FOR,
            'in': TokenType.IN, 'range': TokenType.RANGE, 'func': TokenType.FUNC,
            'return': TokenType.RETURN, 'class': TokenType.CLASS, 'new': TokenType.NEW,
            'this': TokenType.THIS, 'self': TokenType.SELF, 'import': TokenType.IMPORT,
            'from': TokenType.FROM, 'as': TokenType.AS, 'try': TokenType.TRY,
            'except': TokenType.EXCEPT, 'finally': TokenType.FINALLY, 'break': TokenType.BREAK,
            'continue': TokenType.CONTINUE, 'True': TokenType.TRUE, 'False': TokenType.FALSE,
            'None': TokenType.NONE, 'and': TokenType.AND, 'or': TokenType.OR,
            'not': TokenType.NOT_KEYWORD, 'match': TokenType.MATCH, 'case': TokenType.CASE,
            'default': TokenType.DEFAULT, 'assert': TokenType.ASSERT, 'del': TokenType.DEL,
            'global': TokenType.GLOBAL, 'yield': TokenType.YIELD, 'async': TokenType.ASYNC,
            'await': TokenType.AWAIT, 'decorator': TokenType.DECORATOR, 'type': TokenType.TYPE,
            'interface': TokenType.INTERFACE, 'enum': TokenType.ENUM, 'module': TokenType.MODULE,
        }
        
        token_type = keywords.get(value, TokenType.IDENTIFIER)
        self.tokens.append(Token(token_type, value, start_line, start_col, self.filename))
    
    def _read_operator(self):
        start_line = self.line
        start_col = self.col
        char = self.text[self.pos]
        
        # Two-character operators
        if self.pos + 1 < len(self.text):
            two_char = self.text[self.pos:self.pos+2]
            operators = {
                '==': TokenType.EQ, '!=': TokenType.NE, '<=': TokenType.LE,
                '>=': TokenType.GE, '**': TokenType.POWER, '+=': TokenType.PLUS_EQ,
                '-=': TokenType.MINUS_EQ, '*=': TokenType.MULT_EQ, '/=': TokenType.DIV_EQ,
                '%=': TokenType.MOD_EQ, '<<': TokenType.LSHIFT, '>>': TokenType.RSHIFT,
                '->': TokenType.ARROW, '..': TokenType.ELLIPSIS, '**=': TokenType.POWER_EQ,
            }
            if two_char in operators:
                self.pos += 2
                self.col += 2
                return Token(operators[two_char], two_char, start_line, start_col, self.filename)
        
        # Single-character operators
        operators = {
            '+': TokenType.PLUS, '-': TokenType.MINUS, '*': TokenType.MULTIPLY,
            '/': TokenType.DIVIDE, '%': TokenType.MODULO, '=': TokenType.ASSIGN,
            '<': TokenType.LT, '>': TokenType.GT, '!': TokenType.NOT_OP,
            '&': TokenType.BIT_AND, '|': TokenType.BIT_OR, '^': TokenType.BIT_XOR,
            '~': TokenType.BIT_NOT, '(': TokenType.LPAREN, ')': TokenType.RPAREN,
            '{': TokenType.LBRACE, '}': TokenType.RBRACE, '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET, ',': TokenType.COMMA, ':': TokenType.COLON,
            ';': TokenType.SEMICOLON, '.': TokenType.DOT, '@': TokenType.AT,
        }
        
        if char in operators:
            self.pos += 1
            self.col += 1
            return Token(operators[char], char, start_line, start_col, self.filename)
        
        return None
    
    def _handle_newline(self):
        self.pos += 1
        self.line += 1
        self.col = 1

# ================ AST NODES ================
@dataclass
class ASTNode:
    token: Optional[Token] = None

@dataclass
class NumberNode(ASTNode):
    value: Union[int, float] = 0

@dataclass
class StringNode(ASTNode):
    value: str = ""

@dataclass
class VariableNode(ASTNode):
    name: str = ""

@dataclass
class BinaryOpNode(ASTNode):
    left: ASTNode = None
    op: Token = None
    right: ASTNode = None

@dataclass
class UnaryOpNode(ASTNode):
    op: Token = None
    expr: ASTNode = None

@dataclass
class AssignmentNode(ASTNode):
    target: str = ""
    value: ASTNode = None

@dataclass
class IfNode(ASTNode):
    condition: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)
    elif_parts: List[tuple] = field(default_factory=list)
    else_body: List[ASTNode] = field(default_factory=list)

@dataclass
class WhileNode(ASTNode):
    condition: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class ForNode(ASTNode):
    var: str = ""
    iterable: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class FunctionNode(ASTNode):
    name: str = ""
    params: List[str] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class CallNode(ASTNode):
    func: ASTNode = None
    args: List[ASTNode] = field(default_factory=list)

@dataclass
class ClassNode(ASTNode):
    name: str = ""
    methods: Dict[str, ASTNode] = field(default_factory=dict)

@dataclass
class ImportNode(ASTNode):
    module: str = ""
    alias: str = ""
    imports: List[str] = field(default_factory=list)

@dataclass
class TryNode(ASTNode):
    body: List[ASTNode] = field(default_factory=list)
    except_clauses: List[tuple] = field(default_factory=list)
    else_body: List[ASTNode] = field(default_factory=list)
    finally_body: List[ASTNode] = field(default_factory=list)

@dataclass
class MatchNode(ASTNode):
    subject: ASTNode = None
    cases: List[tuple] = field(default_factory=list)

@dataclass
class ListComprehensionNode(ASTNode):
    expr: ASTNode = None
    var: str = ""
    iterable: ASTNode = None
    condition: Optional[ASTNode] = None

@dataclass
class DictComprehensionNode(ASTNode):
    key: ASTNode = None
    value: ASTNode = None
    var: str = ""
    iterable: ASTNode = None
    condition: Optional[ASTNode] = None

@dataclass
class DecoratorNode(ASTNode):
    name: str = ""
    args: List[ASTNode] = field(default_factory=list)
    target: ASTNode = None

@dataclass
class TypeHintNode(ASTNode):
    var: str = ""
    hint: str = ""
    value: Optional[ASTNode] = None

@dataclass
class AssertNode(ASTNode):
    condition: ASTNode = None
    message: Optional[ASTNode] = None

@dataclass
class AwaitNode(ASTNode):
    expr: ASTNode = None

# ================ PARSER ================
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[0] if tokens else None
    
    def parse(self):
        statements = []
        while self.current_token.type != TokenType.EOF:
            stmt = self.statement()
            if stmt:
                statements.append(stmt)
        return statements
    
    def advance(self):
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
            self.current_token = self.tokens[self.pos]
    
    def peek(self, offset=1):
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return None
    
    def expect(self, token_type: TokenType):
        if self.current_token.type != token_type:
            raise SyntaxError(f"Expected {token_type}, got {self.current_token.type} at line {self.current_token.line}, col {self.current_token.column}")
        token = self.current_token
        self.advance()
        return token
    
    def statement(self):
        if self.current_token.type == TokenType.EOF:
            return None
        
        if self.current_token.type == TokenType.LET:
            return self.variable_declaration()
        elif self.current_token.type == TokenType.CONST:
            return self.const_declaration()
        elif self.current_token.type == TokenType.TYPE:
            return self.type_hint()
        elif self.current_token.type == TokenType.IF:
            return self.if_statement()
        elif self.current_token.type == TokenType.WHILE:
            return self.while_statement()
        elif self.current_token.type == TokenType.FOR:
            return self.for_statement()
        elif self.current_token.type == TokenType.FUNC:
            return self.function_definition()
        elif self.current_token.type == TokenType.CLASS:
            return self.class_definition()
        elif self.current_token.type == TokenType.RETURN:
            return self.return_statement()
        elif self.current_token.type == TokenType.IMPORT:
            return self.import_statement()
        elif self.current_token.type == TokenType.TRY:
            return self.try_statement()
        elif self.current_token.type == TokenType.MATCH:
            return self.match_statement()
        elif self.current_token.type == TokenType.ASSERT:
            return self.assert_statement()
        elif self.current_token.type == TokenType.DECORATOR:
            return self.decorator_definition()
        elif self.current_token.type == TokenType.PRINT:
            return self.print_statement()
        else:
            return self.expression_statement()
    
    def variable_declaration(self):
        self.advance()  # skip 'let'
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.ASSIGN)
        value = self.expression()
        return AssignmentNode(token=Token(TokenType.LET, 'let', 0, 0), target=name, value=value)
    
    def const_declaration(self):
        self.advance()  # skip 'const'
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.ASSIGN)
        value = self.expression()
        return AssignmentNode(token=Token(TokenType.CONST, 'const', 0, 0), target=name, value=value)
    
    def type_hint(self):
        self.advance()  # skip 'type'
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COLON)
        hint = self.expect(TokenType.IDENTIFIER).value
        
        value = None
        if self.current_token.type == TokenType.ASSIGN:
            self.advance()
            value = self.expression()
        
        return TypeHintNode(var=name, hint=hint, value=value)
    
    def if_statement(self):
        self.advance()  # skip 'if'
        condition = self.expression()
        self.expect(TokenType.LBRACE)
        body = self.block()
        self.expect(TokenType.RBRACE)
        
        elif_parts = []
        while self.current_token.type == TokenType.ELIF:
            self.advance()
            elif_cond = self.expression()
            self.expect(TokenType.LBRACE)
            elif_body = self.block()
            self.expect(TokenType.RBRACE)
            elif_parts.append((elif_cond, elif_body))
        
        else_body = []
        if self.current_token.type == TokenType.ELSE:
            self.advance()
            self.expect(TokenType.LBRACE)
            else_body = self.block()
            self.expect(TokenType.RBRACE)
        
        return IfNode(condition=condition, body=body, elif_parts=elif_parts, else_body=else_body)
    
    def while_statement(self):
        self.advance()  # skip 'while'
        condition = self.expression()
        self.expect(TokenType.LBRACE)
        body = self.block()
        self.expect(TokenType.RBRACE)
        return WhileNode(condition=condition, body=body)
    
    def for_statement(self):
        self.advance()  # skip 'for'
        var = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.IN)
        iterable = self.expression()
        self.expect(TokenType.LBRACE)
        body = self.block()
        self.expect(TokenType.RBRACE)
        return ForNode(var=var, iterable=iterable, body=body)
    
    def function_definition(self):
        self.advance()  # skip 'func'
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LPAREN)
        
        params = []
        while self.current_token.type != TokenType.RPAREN:
            params.append(self.expect(TokenType.IDENTIFIER).value)
            if self.current_token.type == TokenType.COMMA:
                self.advance()
        
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.LBRACE)
        body = self.block()
        self.expect(TokenType.RBRACE)
        
        return FunctionNode(name=name, params=params, body=body)
    
    def class_definition(self):
        self.advance()  # skip 'class'
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LBRACE)
        
        methods = {}
        while self.current_token.type != TokenType.RBRACE:
            if self.current_token.type == TokenType.FUNC:
                func_node = self.function_definition()
                methods[func_node.name] = func_node
            else:
                self.advance()
        
        self.expect(TokenType.RBRACE)
        return ClassNode(name=name, methods=methods)
    
    def return_statement(self):
        self.advance()  # skip 'return'
        value = None
        if self.current_token.type not in (TokenType.SEMICOLON, TokenType.NEWLINE, TokenType.EOF, TokenType.RBRACE):
            value = self.expression()
        
        # Create a special return node that carries the value
        node = ASTNode(token=Token(TokenType.RETURN, 'return', 0, 0))
        node.value = value
        return node
    
    def import_statement(self):
        self.advance()  # skip 'import'
        module = self.expect(TokenType.STRING).value
        
        alias = module
        if self.current_token.type == TokenType.AS:
            self.advance()
            alias = self.expect(TokenType.IDENTIFIER).value
        
        return ImportNode(module=module, alias=alias)
    
    def try_statement(self):
        self.advance()  # skip 'try'
        self.expect(TokenType.LBRACE)
        body = self.block()
        self.expect(TokenType.RBRACE)
        
        except_clauses = []
        while self.current_token.type == TokenType.EXCEPT:
            self.advance()
            exc_type = None
            exc_name = None
            
            if self.current_token.type == TokenType.IDENTIFIER:
                exc_type = self.current_token.value
                self.advance()
                
                if self.current_token.type == TokenType.AS:
                    self.advance()
                    exc_name = self.expect(TokenType.IDENTIFIER).value
            
            self.expect(TokenType.LBRACE)
            exc_body = self.block()
            self.expect(TokenType.RBRACE)
            except_clauses.append((exc_type, exc_name, exc_body))
        
        else_body = []
        if self.current_token.type == TokenType.ELSE:
            self.advance()
            self.expect(TokenType.LBRACE)
            else_body = self.block()
            self.expect(TokenType.RBRACE)
        
        finally_body = []
        if self.current_token.type == TokenType.FINALLY:
            self.advance()
            self.expect(TokenType.LBRACE)
            finally_body = self.block()
            self.expect(TokenType.RBRACE)
        
        return TryNode(body=body, except_clauses=except_clauses, else_body=else_body, finally_body=finally_body)
    
    def match_statement(self):
        self.advance()  # skip 'match'
        subject = self.expression()
        self.expect(TokenType.LBRACE)
        
        cases = []
        while self.current_token.type == TokenType.CASE:
            self.advance()
            pattern = self.primary()
            
            guard = None
            if self.current_token.type == TokenType.IF:
                self.advance()
                guard = self.expression()
            
            self.expect(TokenType.LBRACE)
            case_body = self.block()
            self.expect(TokenType.RBRACE)
            cases.append((pattern, guard, case_body))
        
        self.expect(TokenType.RBRACE)
        return MatchNode(subject=subject, cases=cases)
    
    def assert_statement(self):
        self.advance()  # skip 'assert'
        condition = self.expression()
        
        message = None
        if self.current_token.type == TokenType.COMMA:
            self.advance()
            message = self.expression()
        
        return AssertNode(condition=condition, message=message)
    
    def decorator_definition(self):
        self.advance()  # skip 'decorator'
        name = self.expect(TokenType.IDENTIFIER).value
        
        args = []
        if self.current_token.type == TokenType.LPAREN:
            self.advance()
            while self.current_token.type != TokenType.RPAREN:
                args.append(self.expression())
                if self.current_token.type == TokenType.COMMA:
                    self.advance()
            self.expect(TokenType.RPAREN)
        
        # Parse the target (function or class)
        target = self.statement()
        
        return DecoratorNode(name=name, args=args, target=target)
    
    def print_statement(self):
        self.advance()  # skip 'print'
        self.expect(TokenType.LPAREN)
        value = self.expression()
        self.expect(TokenType.RPAREN)
        
        call_node = CallNode(func=VariableNode(name='print'), args=[value])
        return call_node
    
    def expression_statement(self):
        expr = self.expression()
        return expr
    
    def expression(self):
        return self.logical_or()
    
    def logical_or(self):
        left = self.logical_and()
        
        while self.current_token.type == TokenType.OR:
            op = self.current_token
            self.advance()
            right = self.logical_and()
            left = BinaryOpNode(left=left, op=op, right=right)
        
        return left
    
    def logical_and(self):
        left = self.comparison()
        
        while self.current_token.type == TokenType.AND:
            op = self.current_token
            self.advance()
            right = self.comparison()
            left = BinaryOpNode(left=left, op=op, right=right)
        
        return left
    
    def comparison(self):
        left = self.bitwise_or()
        
        while self.current_token.type in (TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE):
            op = self.current_token
            self.advance()
            right = self.bitwise_or()
            left = BinaryOpNode(left=left, op=op, right=right)
        
        return left
    
    def bitwise_or(self):
        left = self.bitwise_xor()
        
        while self.current_token.type == TokenType.BIT_OR:
            op = self.current_token
            self.advance()
            right = self.bitwise_xor()
            left = BinaryOpNode(left=left, op=op, right=right)
        
        return left
    
    def bitwise_xor(self):
        left = self.bitwise_and()
        
        while self.current_token.type == TokenType.BIT_XOR:
            op = self.current_token
            self.advance()
            right = self.bitwise_and()
            left = BinaryOpNode(left=left, op=op, right=right)
        
        return left
    
    def bitwise_and(self):
        left = self.shift()
        
        while self.current_token.type == TokenType.BIT_AND:
            op = self.current_token
            self.advance()
            right = self.shift()
            left = BinaryOpNode(left=left, op=op, right=right)
        
        return left
    
    def shift(self):
        left = self.additive()
        
        while self.current_token.type in (TokenType.LSHIFT, TokenType.RSHIFT):
            op = self.current_token
            self.advance()
            right = self.additive()
            left = BinaryOpNode(left=left, op=op, right=right)
        
        return left
    
    def additive(self):
        left = self.multiplicative()
        
        while self.current_token.type in (TokenType.PLUS, TokenType.MINUS):
            op = self.current_token
            self.advance()
            right = self.multiplicative()
            left = BinaryOpNode(left=left, op=op, right=right)
        
        return left
    
    def multiplicative(self):
        left = self.unary()
        
        while self.current_token.type in (TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op = self.current_token
            self.advance()
            right = self.unary()
            left = BinaryOpNode(left=left, op=op, right=right)
        
        return left
    
    def unary(self):
        if self.current_token.type in (TokenType.NOT_KEYWORD, TokenType.NOT_OP, TokenType.MINUS, TokenType.BIT_NOT):
            op = self.current_token
            self.advance()
            expr = self.unary()
            return UnaryOpNode(op=op, expr=expr)
        
        return self.power()
    
    def power(self):
        left = self.postfix()
        
        if self.current_token.type == TokenType.POWER:
            op = self.current_token
            self.advance()
            right = self.power()
            left = BinaryOpNode(left=left, op=op, right=right)
        
        return left
    
    def postfix(self):
        left = self.primary()
        
        while True:
            if self.current_token.type == TokenType.LPAREN:
                self.advance()
                args = []
                while self.current_token.type != TokenType.RPAREN:
                    args.append(self.expression())
                    if self.current_token.type == TokenType.COMMA:
                        self.advance()
                self.expect(TokenType.RPAREN)
                left = CallNode(func=left, args=args)
            
            elif self.current_token.type == TokenType.DOT:
                self.advance()
                attr = self.expect(TokenType.IDENTIFIER).value
                left = BinaryOpNode(left=left, op=Token(TokenType.DOT, '.', 0, 0), right=VariableNode(name=attr))
            
            elif self.current_token.type == TokenType.LBRACKET:
                self.advance()
                index = self.expression()
                self.expect(TokenType.RBRACKET)
                left = CallNode(func=VariableNode(name='__getitem__'), args=[left, index])
            
            else:
                break
        
        return left
    
    def primary(self):
        if self.current_token.type == TokenType.NUMBER:
            value = self.current_token.value
            self.advance()
            return NumberNode(value=value)
        
        elif self.current_token.type == TokenType.STRING:
            value = self.current_token.value
            self.advance()
            return StringNode(value=value)
        
        elif self.current_token.type == TokenType.FSTRING:
            value = self.current_token.value
            self.advance()
            return StringNode(value=value)
        
        elif self.current_token.type == TokenType.TRUE:
            self.advance()
            return NumberNode(value=True)
        
        elif self.current_token.type == TokenType.FALSE:
            self.advance()
            return NumberNode(value=False)
        
        elif self.current_token.type == TokenType.NONE:
            self.advance()
            return NumberNode(value=None)
        
        elif self.current_token.type in (TokenType.IDENTIFIER, TokenType.RANGE, TokenType.SELF, TokenType.THIS):
            # Handle IDENTIFIER, RANGE, SELF, THIS keywords
            if self.current_token.type == TokenType.RANGE:
                name = 'range'
            elif self.current_token.type == TokenType.SELF:
                name = 'self'
            elif self.current_token.type == TokenType.THIS:
                name = 'this'
            else:
                name = self.current_token.value
            self.advance()
            return VariableNode(name=name)
        
        elif self.current_token.type == TokenType.LPAREN:
            self.advance()
            expr = self.expression()
            self.expect(TokenType.RPAREN)
            return expr
        
        elif self.current_token.type == TokenType.LBRACKET:
            return self.list_literal()
        
        elif self.current_token.type == TokenType.LBRACE:
            return self.dict_literal()
        
        elif self.current_token.type == TokenType.NEW:
            return self.new_expression()
        
        else:
            raise SyntaxError(f"Unexpected token: {self.current_token.type} at line {self.current_token.line}")
    
    def list_literal(self):
        self.advance()  # skip '['
        
        if self.current_token.type == TokenType.RBRACKET:
            self.advance()
            return CallNode(func=VariableNode(name='list'), args=[])
        
        first_expr = self.postfix()  # Use postfix to avoid FOR parsing
        
        # Check for list comprehension
        if self.current_token.type == TokenType.FOR:
            self.advance()
            var = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.IN)
            iterable = self.additive()  # Parse the iterable without FOR confusion
            
            condition = None
            if self.current_token.type == TokenType.IF:
                self.advance()
                condition = self.comparison()
            
            self.expect(TokenType.RBRACKET)
            return ListComprehensionNode(expr=first_expr, var=var, iterable=iterable, condition=condition)
        
        # Regular list
        elements = [first_expr]
        while self.current_token.type == TokenType.COMMA:
            self.advance()
            if self.current_token.type == TokenType.RBRACKET:
                break
            elements.append(self.postfix())
        
        self.expect(TokenType.RBRACKET)
        return CallNode(func=VariableNode(name='list'), args=elements)
    
    def dict_literal(self):
        self.advance()  # skip '{'
        
        if self.current_token.type == TokenType.RBRACE:
            self.advance()
            return CallNode(func=VariableNode(name='dict'), args=[])
        
        # For now, simple dict support
        pairs = []
        while self.current_token.type != TokenType.RBRACE:
            key = self.expression()
            self.expect(TokenType.COLON)
            value = self.expression()
            pairs.append((key, value))
            
            if self.current_token.type == TokenType.COMMA:
                self.advance()
            elif self.current_token.type != TokenType.RBRACE:
                break
        
        self.expect(TokenType.RBRACE)
        return CallNode(func=VariableNode(name='dict'), args=[pairs])
    
    def new_expression(self):
        self.advance()  # skip 'new'
        class_name = self.expect(TokenType.IDENTIFIER).value
        
        args = []
        if self.current_token.type == TokenType.LPAREN:
            self.advance()
            while self.current_token.type != TokenType.RPAREN:
                args.append(self.expression())
                if self.current_token.type == TokenType.COMMA:
                    self.advance()
            self.expect(TokenType.RPAREN)
        
        return CallNode(func=VariableNode(name=class_name), args=args)
    
    def block(self):
        statements = []
        while self.current_token.type != TokenType.RBRACE and self.current_token.type != TokenType.EOF:
            stmt = self.statement()
            if stmt:
                statements.append(stmt)
        return statements

# ================ BUILT-IN MODULES ================
class Module:
    def __init__(self, name: str, attrs: Dict[str, Any] = None):
        self.name = name
        self.attrs = attrs or {}
    
    def get(self, attr_name: str):
        return self.attrs.get(attr_name)

def create_math_module():
    return Module('math', {
        'pi': math.pi,
        'e': math.e,
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
        'floor': math.floor,
        'ceil': math.ceil,
    })

def create_time_module():
    return Module('time', {
        'time': time.time,
        'sleep': time.sleep,
        'datetime': datetime.datetime,
    })

def create_json_module():
    return Module('json', {
        'dumps': json.dumps,
        'loads': json.loads,
    })

def create_regex_module():
    """New regex module for pattern matching"""
    return Module('regex', {
        'match': lambda pattern, text: re.match(pattern, text) is not None,
        'search': lambda pattern, text: re.search(pattern, text) is not None,
        'findall': re.findall,
        'sub': re.sub,
    })

def create_network_module():
    """New networking module"""
    class NetworkModule:
        @staticmethod
        def http_get(url, timeout=5):
            try:
                with urllib.request.urlopen(url, timeout=timeout) as response:
                    return response.read().decode('utf-8')
            except Exception as e:
                return f"Error: {str(e)}"
        
        @staticmethod
        def http_post(url, data, timeout=5):
            try:
                data_bytes = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=data_bytes)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read().decode('utf-8')
            except Exception as e:
                return f"Error: {str(e)}"
        
        @staticmethod
        def socket_connect(host, port, timeout=5):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((host, port))
                return sock
            except Exception as e:
                return f"Error: {str(e)}"
    
    return Module('network', {
        'http_get': NetworkModule.http_get,
        'http_post': NetworkModule.http_post,
        'socket_connect': NetworkModule.socket_connect,
    })

def create_file_module():
    """Enhanced file I/O module"""
    class FileModule:
        @staticmethod
        def read(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"Error: {str(e)}"
        
        @staticmethod
        def write(path, content):
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(str(content))
                return True
            except Exception as e:
                return f"Error: {str(e)}"
        
        @staticmethod
        def append(path, content):
            try:
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(str(content))
                return True
            except Exception as e:
                return f"Error: {str(e)}"
        
        @staticmethod
        def exists(path):
            return os.path.exists(path)
        
        @staticmethod
        def delete(path):
            try:
                os.remove(path)
                return True
            except Exception as e:
                return f"Error: {str(e)}"
        
        @staticmethod
        def read_json(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                return f"Error: {str(e)}"
        
        @staticmethod
        def write_json(path, data):
            try:
                with open(path, 'w') as f:
                    json.dump(data, f, indent=2)
                return True
            except Exception as e:
                return f"Error: {str(e)}"
        
        @staticmethod
        def read_csv(path):
            try:
                with open(path, 'r') as f:
                    reader = csv.reader(f)
                    return list(reader)
            except Exception as e:
                return f"Error: {str(e)}"
        
        @staticmethod
        def write_csv(path, data):
            try:
                with open(path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(data)
                return True
            except Exception as e:
                return f"Error: {str(e)}"
    
    return Module('file', {
        'read': FileModule.read,
        'write': FileModule.write,
        'append': FileModule.append,
        'exists': FileModule.exists,
        'delete': FileModule.delete,
        'read_json': FileModule.read_json,
        'write_json': FileModule.write_json,
        'read_csv': FileModule.read_csv,
        'write_csv': FileModule.write_csv,
    })

def create_crypto_module():
    """New cryptography module"""
    class CryptoModule:
        @staticmethod
        def md5(text):
            return hashlib.md5(str(text).encode()).hexdigest()
        
        @staticmethod
        def sha256(text):
            return hashlib.sha256(str(text).encode()).hexdigest()
        
        @staticmethod
        def base64_encode(text):
            return base64.b64encode(str(text).encode()).decode()
        
        @staticmethod
        def base64_decode(text):
            try:
                return base64.b64decode(str(text).encode()).decode()
            except:
                return "Error: Invalid base64"
    
    return Module('crypto', {
        'md5': CryptoModule.md5,
        'sha256': CryptoModule.sha256,
        'base64_encode': CryptoModule.base64_encode,
        'base64_decode': CryptoModule.base64_decode,
    })

# ================ INTERPRETER ================
class BreakException(Exception):
    pass

class ContinueException(Exception):
    pass

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value

class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.vars = {}
    
    def define(self, name: str, value: Any, is_const: bool = False):
        self.vars[name] = {'value': value, 'const': is_const}
    
    def get(self, name: str):
        if name in self.vars:
            return self.vars[name]['value']
        elif self.parent:
            return self.parent.get(name)
        else:
            raise NameError(f"Undefined variable: {name}")
    
    def set(self, name: str, value: Any):
        if name in self.vars:
            if self.vars[name]['const']:
                raise RuntimeError(f"Cannot modify constant: {name}")
            self.vars[name]['value'] = value
        elif self.parent:
            self.parent.set(name, value)
        else:
            self.vars[name] = {'value': value, 'const': False}
    
    def get_all(self):
        result = dict(self.vars)
        if self.parent:
            result.update(self.parent.get_all())
        return {k: v['value'] for k, v in result.items()}

class Function:
    def __init__(self, name: str, params: List[str], body: List[ASTNode], closure: Environment):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure
    
    def __call__(self, *args):
        env = Environment(parent=self.closure)
        for i, param in enumerate(self.params):
            env.define(param, args[i] if i < len(args) else None, False)
        
        interpreter = Interpreter()
        interpreter.env = env
        
        try:
            for stmt in self.body:
                interpreter.visit(stmt)
        except ReturnException as e:
            return e.value
        
        return None

class Class:
    def __init__(self, name: str, methods: Dict[str, Function]):
        self.name = name
        self.methods = methods
    
    def __call__(self, *args):
        instance = Instance(self)
        if '__init__' in self.methods:
            init_func = self.methods['__init__']
            init_func(instance, *args)
        return instance

class Instance:
    def __init__(self, klass: Class):
        self.klass = klass
        self.attrs = {}
    
    def get_attr(self, name: str):
        if name in self.attrs:
            return self.attrs[name]
        if name in self.klass.methods:
            method = self.klass.methods[name]
            return lambda *args: method(self, *args)
        raise AttributeError(f"'{self.klass.name}' object has no attribute '{name}'")
    
    def set_attr(self, name: str, value: Any):
        self.attrs[name] = value

class Interpreter:
    def __init__(self):
        self.env = Environment()
        self.modules = {}
        self.loop_stack = []
        self.decorators = {}
        self._define_builtins()
    
    def _define_builtins(self):
        # Built-in functions
        self.env.define('print', self._builtin_print, False)
        self.env.define('len', len, False)
        self.env.define('range', range, False)
        self.env.define('list', list, False)
        self.env.define('dict', dict, False)
        self.env.define('str', str, False)
        self.env.define('int', int, False)
        self.env.define('float', float, False)
        self.env.define('bool', bool, False)
        self.env.define('sum', sum, False)
        self.env.define('min', min, False)
        self.env.define('max', max, False)
        self.env.define('abs', abs, False)
        self.env.define('round', round, False)
        self.env.define('sorted', sorted, False)
        self.env.define('reversed', reversed, False)
        self.env.define('enumerate', enumerate, False)
        self.env.define('zip', zip, False)
        self.env.define('map', map, False)
        self.env.define('filter', filter, False)
        self.env.define('type', type, False)
        self.env.define('isinstance', isinstance, False)
        self.env.define('callable', callable, False)
        self.env.define('input', input, False)
        self.env.define('open', open, False)
        self.env.define('exit', sys.exit, False)
        self.env.define('random', random.random, False)
        self.env.define('random_int', random.randint, False)
        self.env.define('random_choice', random.choice, False)
    
    def _builtin_print(self, *args):
        if RICH_AVAILABLE:
            for arg in args:
                console.print(str(arg))
        else:
            for arg in args:
                print(arg)
        return None
    
    def interpret(self, statements: List[ASTNode]):
        try:
            for stmt in statements:
                self.visit(stmt)
            return True
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[bold red]Runtime error:[/bold red] {e}")
            else:
                print(f"Runtime error: {e}")
            return False
    
    def visit(self, node):
        if node is None:
            return None
        
        node_type = type(node).__name__
        
        if node_type == 'NumberNode':
            return node.value
        
        elif node_type == 'StringNode':
            return node.value
        
        elif node_type == 'VariableNode':
            return self.env.get(node.name)
        
        elif node_type == 'BinaryOpNode':
            left = self.visit(node.left)
            
            # For DOT operator, don't evaluate right side as a variable
            if node.op.type == TokenType.DOT:
                attr_name = node.right.name if isinstance(node.right, VariableNode) else str(node.right)
                
                if isinstance(left, Instance):
                    return left.get_attr(attr_name)
                elif isinstance(left, dict):
                    return left.get(attr_name)
                elif isinstance(left, Module):
                    result = left.get(attr_name)
                    return result
                else:
                    return getattr(left, attr_name, None)
            
            # For other operators, evaluate right side
            right = self.visit(node.right)
            op = node.op.type
            
            if op == TokenType.PLUS:
                return left + right
            elif op == TokenType.MINUS:
                return left - right
            elif op == TokenType.MULTIPLY:
                return left * right
            elif op == TokenType.DIVIDE:
                return left / right
            elif op == TokenType.MODULO:
                return left % right
            elif op == TokenType.POWER:
                return left ** right
            elif op == TokenType.EQ:
                return left == right
            elif op == TokenType.NE:
                return left != right
            elif op == TokenType.LT:
                return left < right
            elif op == TokenType.GT:
                return left > right
            elif op == TokenType.LE:
                return left <= right
            elif op == TokenType.GE:
                return left >= right
            elif op == TokenType.AND:
                return left and right
            elif op == TokenType.OR:
                return left or right
            elif op == TokenType.BIT_AND:
                return left & right
            elif op == TokenType.BIT_OR:
                return left | right
            elif op == TokenType.BIT_XOR:
                return left ^ right
            elif op == TokenType.LSHIFT:
                return left << right
            elif op == TokenType.RSHIFT:
                return left >> right
        
        elif node_type == 'UnaryOpNode':
            expr = self.visit(node.expr)
            op = node.op.type
            
            if op == TokenType.MINUS:
                return -expr
            elif op == TokenType.NOT_KEYWORD or op == TokenType.NOT_OP:
                return not expr
            elif op == TokenType.BIT_NOT:
                return ~expr
        
        elif node_type == 'AssignmentNode':
            value = self.visit(node.value)
            is_const = node.token and node.token.type == TokenType.CONST
            self.env.define(node.target, value, is_const)
            return value
        
        elif node_type == 'IfNode':
            condition = self.visit(node.condition)
            if condition:
                for stmt in node.body:
                    self.visit(stmt)
            else:
                for elif_cond, elif_body in node.elif_parts:
                    if self.visit(elif_cond):
                        for stmt in elif_body:
                            self.visit(stmt)
                        return None
                
                for stmt in node.else_body:
                    self.visit(stmt)
        
        elif node_type == 'WhileNode':
            self.loop_stack.append('while')
            try:
                while self.visit(node.condition):
                    try:
                        for stmt in node.body:
                            self.visit(stmt)
                    except ContinueException:
                        continue
                    except BreakException:
                        break
            finally:
                self.loop_stack.pop()
        
        elif node_type == 'ForNode':
            self.loop_stack.append('for')
            try:
                iterable = self.visit(node.iterable)
                for value in iterable:
                    self.env.define(node.var, value, False)
                    try:
                        for stmt in node.body:
                            self.visit(stmt)
                    except ContinueException:
                        continue
                    except BreakException:
                        break
            finally:
                self.loop_stack.pop()
        
        elif node_type == 'FunctionNode':
            func = Function(node.name, node.params, node.body, self.env)
            self.env.define(node.name, func, False)
        
        elif node_type == 'CallNode':
            func = self.visit(node.func)
            args = [self.visit(arg) for arg in node.args]
            
            # Special handling for built-in constructors
            if isinstance(node.func, VariableNode):
                if node.func.name == 'list' and len(args) > 0 and not isinstance(args[0], list):
                    return args  # Convert multiple args to a list
                elif node.func.name == 'dict' and len(args) > 0:
                    result = {}
                    for pair in args[0]:
                        k = self.visit(pair[0])
                        v = self.visit(pair[1])
                        result[k] = v
                    return result
            
            if callable(func):
                return func(*args)
            else:
                raise TypeError(f"'{type(func).__name__}' object is not callable")
        
        elif node_type == 'ClassNode':
            methods = {}
            for name, method_node in node.methods.items():
                func = Function(name, method_node.params, method_node.body, self.env)
                methods[name] = func
            
            klass = Class(node.name, methods)
            self.env.define(node.name, klass, False)
        
        elif node_type == 'ListComprehensionNode':
            result = []
            iterable = self.visit(node.iterable)
            for value in iterable:
                self.env.define(node.var, value, False)
                if node.condition is None or self.visit(node.condition):
                    result.append(self.visit(node.expr))
            return result
        
        elif node_type == 'TypeHintNode':
            value = self.visit(node.value) if node.value else None
            self.env.define(node.var, value, False)
        
        elif node_type == 'ImportNode':
            module_name = node.module
            
            # Load built-in modules
            if module_name == 'math':
                module = create_math_module()
            elif module_name == 'time':
                module = create_time_module()
            elif module_name == 'json':
                module = create_json_module()
            elif module_name == 'regex':
                module = create_regex_module()
            elif module_name == 'network':
                module = create_network_module()
            elif module_name == 'file':
                module = create_file_module()
            elif module_name == 'crypto':
                module = create_crypto_module()
            else:
                raise ImportError(f"Unknown module: {module_name}")
            
            self.modules[node.alias] = module
            self.env.define(node.alias, module, False)
        
        elif node_type == 'TryNode':
            try:
                for stmt in node.body:
                    self.visit(stmt)
            except Exception as e:
                caught = False
                for exc_type, exc_name, body in node.except_clauses:
                    if exc_type is None or exc_type == type(e).__name__ or exc_type == 'Exception':
                        caught = True
                        if exc_name:
                            self.env.define(exc_name, str(e), False)
                        
                        for stmt in body:
                            self.visit(stmt)
                        break
                
                if not caught:
                    raise e
            else:
                for stmt in node.else_body:
                    self.visit(stmt)
            finally:
                for stmt in node.finally_body:
                    self.visit(stmt)
        
        elif node_type == 'MatchNode':
            subject = self.visit(node.subject)
            matched = False
            
            for pattern, guard, body in node.cases:
                pattern_value = self.visit(pattern) if not isinstance(pattern, VariableNode) or pattern.name != '_' else None
                
                if pattern_value is not None and subject != pattern_value:
                    continue
                
                if guard:
                    guard_result = self.visit(guard)
                    if not guard_result:
                        continue
                
                matched = True
                for stmt in body:
                    self.visit(stmt)
                break
        
        elif node_type == 'AssertNode':
            condition = self.visit(node.condition)
            if not condition:
                message = self.visit(node.message) if node.message else "Assertion failed"
                raise AssertionError(str(message))
        
        elif node_type == 'DecoratorNode':
            # Simple decorator support
            decorator_func = self.env.get(node.name)
            target_func = self.visit(node.target)
            
            decorator_args = [self.visit(arg) for arg in node.args]
            self.decorators[node.name] = (decorator_func, decorator_args, target_func)
        
        elif node_type == 'ASTNode':
            if node.token and node.token.type == TokenType.BREAK:
                if not self.loop_stack:
                    raise SyntaxError("'break' outside loop")
                raise BreakException()
            elif node.token and node.token.type == TokenType.CONTINUE:
                if not self.loop_stack:
                    raise SyntaxError("'continue' outside loop")
                raise ContinueException()
            elif node.token and node.token.type == TokenType.RETURN:
                value = self.visit(node.value) if hasattr(node, 'value') and node.value else None
                raise ReturnException(value)
        
        return None

# ================ MAIN INTERFACE ================
def run_code(code, filename=""):
    """Run KentScript code"""
    try:
        lexer = Lexer(code, filename)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        interpreter = Interpreter()
        success = interpreter.interpret(ast)
        
        return success
        
    except SyntaxError as e:
        if RICH_AVAILABLE:
            console.print(f"[bold red]Syntax error:[/bold red] {e}")
        else:
            print(f"Syntax error: {e}")
        return False
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"[bold red]Error:[/bold red] {e}")
        else:
            print(f"Error: {e}")
        return False

def run_file(filename):
    """Run a KentScript file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
        
        if RICH_AVAILABLE:
            console.print(f"[bold cyan]Running {filename}...[/bold cyan]")
        else:
            print(f"Running {filename}...")
        
        return run_code(code, filename)
        
    except FileNotFoundError:
        if RICH_AVAILABLE:
            console.print(f"[bold red]File not found:[/bold red] {filename}")
        else:
            print(f"File not found: {filename}")
        return False
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"[bold red]Error:[/bold red] {e}")
        else:
            print(f"Error: {e}")
        return False

def repl():
    """Interactive REPL"""
    LOGO = r"""
[bold cyan]
 _  __            _   ____            _       _   
| |/ /___ _ __   | |_/ ___|  ___ _ __(_)_ __ | |_ 
| ' // _ \ '_ \  | __\___ \ / __| '__| | '_ \| __|
| . \  __/ | | | | |_ ___) | (__| |  | | |_) | |_ 
|_|\_\___|_| |_|  \__|____/ \___|_|  |_| .__/ \__|
                                       |_|          
[/bold cyan]
[bold yellow]Python[/bold yellow]/[bold yellow]clang[/bold yellow] based Scripting Language  — [bold red]By pyLord[/bold red]
"""
   
    console.print(Panel.fit(LOGO, title="KentScript v0.1"))
    print("Type 'exit' to quit, 'help' for commands\n")
    session = PromptSession(history=FileHistory(".kentscript_history"))
    
    kscript_completer = WordCompleter([
        'let', 'const', 'print', 'if', 'else', 'elif', 'while', 'for', 'func',
        'class', 'import', 'from', 'as', 'return', 'True', 'False', 'None',
        'and', 'or', 'not', 'in', 'is', 'break', 'continue', 'try', 'except',
        'finally', 'match', 'case', 'assert', 'yield', 'async', 'await',
        'decorator', 'type', 'interface', 'enum'
    ]) if PROMPT_TOOLKIT_AVAILABLE else None
    
    if PROMPT_TOOLKIT_AVAILABLE:
        session = PromptSession(
            history=FileHistory('.kentscript_history'),
            completer=kscript_completer
        )
    
    interpreter = Interpreter()
    
    while True:
        try:
            if PROMPT_TOOLKIT_AVAILABLE:
                code = session.prompt('>>> ', lexer=PygmentsLexer(KentScriptLexer))
            else:
                code = input('>>> ')
            
            if code.strip().lower() in ('exit', 'quit', 'q'):
                print("Goodbye!")
                break
            
            if code.strip().lower() == 'help':
                print("""
KentScript 2.0 - Commands:
  exit, quit, q  - Exit REPL
  help           - Show this help
  vars           - Show all variables
  funcs          - Show all functions
  classes        - Show all classes
  modules        - Show loaded modules
  clear          - Clear screen
  reset          - Reset interpreter state
                """)
                continue
            
            if code.strip().lower() == 'vars':
                print("\nVariables:")
                for name, value in interpreter.env.get_all().items():
                    if not callable(value) and not isinstance(value, (Class, Function, Module)):
                        print(f"  {name}: {repr(value)}")
                continue
            
            if code.strip().lower() == 'funcs':
                print("\nFunctions:")
                for name, value in interpreter.env.get_all().items():
                    if callable(value) or isinstance(value, Function):
                        print(f"  {name}")
                continue
            
            if code.strip().lower() == 'classes':
                print("\nClasses:")
                for name, value in interpreter.env.get_all().items():
                    if isinstance(value, Class):
                        print(f"  {name}")
                continue
            
            if code.strip().lower() == 'modules':
                print("\nLoaded modules:")
                for name in interpreter.modules:
                    print(f"  {name}")
                continue
            
            if code.strip().lower() == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
            
            if code.strip().lower() == 'reset':
                interpreter = Interpreter()
                print("Interpreter reset.")
                continue
            
            if not code.strip():
                continue
            
            run_code(code)
            
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        repl()

if __name__ == "__main__":
    main()
