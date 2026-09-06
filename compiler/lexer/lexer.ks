::
:: KentScript Unified Lexer - Complete Implementation
:: Single source of truth for tokenization
:: Full feature parity with lexer.py
::

:: ─── Token Types ────────────────────────────────────────────────────────────

const TK_EOF = "EOF"
const TK_ERROR = "ERROR"
const TK_COMMENT = "COMMENT"

:: Keywords
const TK_LET = "LET"
const TK_CONST = "CONST"
const TK_MUT = "MUT"
const TK_FUNC = "FUNC"
const TK_RETURN = "RETURN"
const TK_IF = "IF"
const TK_ELIF = "ELIF"
const TK_ELSE = "ELSE"
const TK_WHILE = "WHILE"
const TK_FOR = "FOR"
const TK_IN = "IN"
const TK_MATCH = "MATCH"
const TK_CASE = "CASE"
const TK_DEFAULT = "DEFAULT"
const TK_ENUM = "ENUM"
const TK_STRUCT = "STRUCT"
const TK_CLASS = "CLASS"
const TK_IMPORT = "IMPORT"
const TK_FROM = "FROM"
const TK_AS = "AS"
const TK_BREAK = "BREAK"
const TK_CONTINUE = "CONTINUE"
const TK_TRY = "TRY"
const TK_EXCEPT = "EXCEPT"
const TK_RAISE = "RAISE"
const TK_ASYNC = "ASYNC"
const TK_AWAIT = "AWAIT"
const TK_YIELD = "YIELD"
const TK_EXPORT = "EXPORT"
const TK_MODULE = "MODULE"
const TK_MOVE = "MOVE"
const TK_BORROW = "BORROW"
const TK_RELEASE = "RELEASE"
const TK_UNSAFE = "UNSAFE"
const TK_SAFE = "SAFE"
const TK_NEW = "NEW"
const TK_SELF = "SELF"
const TK_SUPER = "SUPER"
const TK_EXTENDS = "EXTENDS"
const TK_INTERFACE = "INTERFACE"
const TK_TYPE = "TYPE"
const TK_THREAD = "THREAD"
const TK_PRINT = "PRINT"
const TK_RANGE = "RANGE"
const TK_CLS = "CLS"
const TK_FINALLY = "FINALLY"
const TK_PUB = "PUB"
const TK_PRIV = "PRIV"
const TK_GENFUNC = "GENFUNC"

:: Type keywords
const TK_I8 = "I8"
const TK_I16 = "I16"
const TK_I32 = "I32"
const TK_I64 = "I64"
const TK_U8 = "U8"
const TK_U16 = "U16"
const TK_U32 = "U32"
const TK_U64 = "U64"
const TK_F32 = "F32"
const TK_F64 = "F64"
const TK_BOOL = "BOOL"
const TK_STR = "STR"
const TK_CHAR = "CHAR"
const TK_VOID = "VOID"

:: Literals
const TK_TRUE = "TRUE"
const TK_FALSE = "FALSE"
const TK_NONE = "NONE"
const TK_IDENTIFIER = "IDENTIFIER"
const TK_NUMBER = "NUMBER"
const TK_STRING = "STRING"
const TK_STRING_LIT = "STRING_LIT"
const TK_FSTRING = "FSTRING"
const TK_HEX_NUMBER = "HEX_NUMBER"
const TK_BIN_NUMBER = "BIN_NUMBER"
const TK_FLOAT_NUMBER = "FLOAT_NUMBER"

:: Type prefixes
const TK_I = "I"
const TK_U = "U"

:: Operators - Arithmetic
const TK_PLUS = "PLUS"
const TK_MINUS = "MINUS"
const TK_STAR = "STAR"
const TK_MULTIPLY = "MULTIPLY"
const TK_SLASH = "SLASH"
const TK_DIVIDE = "DIVIDE"
const TK_PERCENT = "PERCENT"
const TK_MODULO = "MODULO"
const TK_POWER = "POWER"
const TK_FLOOR_DIVIDE = "FLOOR_DIVIDE"

:: Operators - Assignment
const TK_ASSIGN = "ASSIGN"
const TK_PLUS_ASSIGN = "PLUS_ASSIGN"
const TK_MINUS_ASSIGN = "MINUS_ASSIGN"
const TK_STAR_ASSIGN = "STAR_ASSIGN"
const TK_MULTIPLY_ASSIGN = "MULTIPLY_ASSIGN"
const TK_SLASH_ASSIGN = "SLASH_ASSIGN"
const TK_DIVIDE_ASSIGN = "DIVIDE_ASSIGN"
const TK_MODULO_ASSIGN = "MODULO_ASSIGN"
const TK_POWER_ASSIGN = "POWER_ASSIGN"

:: Operators - Comparison
const TK_EQ = "EQ"
const TK_NE = "NE"
const TK_LT = "LT"
const TK_GT = "GT"
const TK_LE = "LE"
const TK_GE = "GE"

:: Operators - Logical
const TK_AND = "AND"
const TK_OR = "OR"
const TK_NOT = "NOT"

:: Operators - Bitwise
const TK_BIT_AND = "BIT_AND"
const TK_BIT_OR = "BIT_OR"
const TK_BIT_XOR = "BIT_XOR"
const TK_BIT_NOT = "BIT_NOT"
const TK_LSHIFT = "LSHIFT"
const TK_RSHIFT = "RSHIFT"

:: Punctuation
const TK_LPAREN = "LPAREN"
const TK_RPAREN = "RPAREN"
const TK_LBRACE = "LBRACE"
const TK_RBRACE = "RBRACE"
const TK_LBRACKET = "LBRACKET"
const TK_RBRACKET = "RBRACKET"
const TK_SEMICOLON = "SEMICOLON"
const TK_COMMA = "COMMA"
const TK_DOT = "DOT"
const TK_COLON = "COLON"
const TK_COLONCOLON = "COLONCOLON"
const TK_ARROW = "ARROW"
const TK_FAT_ARROW = "FAT_ARROW"
const TK_QUESTION = "QUESTION"
const TK_AT = "AT"
const TK_BACKTICK = "BACKTICK"
const TK_PIPE = "PIPE"
const TK_INCLUSIVE_RANGE = "INCLUSIVE_RANGE"

:: ─── Keyword Mapping ─────────────────────────────────────────────────────────

let KEYWORDS: dict = {
    "let": TK_LET, "const": TK_CONST, "mut": TK_MUT,
    "func": TK_FUNC, "return": TK_RETURN, "if": TK_IF,
    "elif": TK_ELIF, "else": TK_ELSE, "while": TK_WHILE,
    "for": TK_FOR, "in": TK_IN, "match": TK_MATCH,
    "case": TK_CASE, "default": TK_DEFAULT, "enum": TK_ENUM,
    "struct": TK_STRUCT, "class": TK_CLASS, "import": TK_IMPORT,
    "from": TK_FROM, "as": TK_AS, "break": TK_BREAK,
    "continue": TK_CONTINUE, "try": TK_TRY, "except": TK_EXCEPT,
    "raise": TK_RAISE, "async": TK_ASYNC, "await": TK_AWAIT,
    "yield": TK_YIELD, "export": TK_EXPORT, "module": TK_MODULE,
    "move": TK_MOVE, "borrow": TK_BORROW, "release": TK_RELEASE,
    "unsafe": TK_UNSAFE, "safe": TK_SAFE, "new": TK_NEW,
    "self": TK_SELF, "super": TK_SUPER, "extends": TK_EXTENDS,
    "interface": TK_INTERFACE, "type": TK_TYPE, "thread": TK_THREAD,
    "print": TK_PRINT, "range": TK_RANGE, "cls": TK_CLS,
    "finally": TK_FINALLY, "pub": TK_PUB, "priv": TK_PRIV,
    "true": TK_TRUE, "false": TK_FALSE, "none": TK_NONE,
    "i8": TK_I8, "i16": TK_I16, "i32": TK_I32, "i64": TK_I64,
    "u8": TK_U8, "u16": TK_U16, "u32": TK_U32, "u64": TK_U64,
    "f32": TK_F32, "f64": TK_F64, "bool": TK_BOOL,
    "str": TK_STR, "char": TK_CHAR, "void": TK_VOID,
}

:: ─── Token Class ────────────────────────────────────────────────────────────

class Token {
    func __init__(self, kind: str, value, line: i32, col: i32) {
        self.kind = kind
        self.value = value
        self.line = line
        self.col = col
    }
}

:: ─── Lexer Class ────────────────────────────────────────────────────────────

class Lexer {
    func __init__(self, source: str) {
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []
    }

    func at_end(self) -> bool {
        return self.pos >= len(self.source)
    }

    func peek(self) -> str {
        if self.at_end() { return "\0" }
        return self.source[self.pos]
    }

    func peek_ahead(self, offset: i32) -> str {
        let idx: i32 = self.pos + offset
        if idx >= len(self.source) { return "\0" }
        return self.source[idx]
    }

    func advance(self) -> str {
        let ch: str = self.source[self.pos]
        self.pos = self.pos + 1
        if ch == "\n" {
            self.line = self.line + 1
            self.col = 1
        } else {
            self.col = self.col + 1
        }
        return ch
    }

    func skip_whitespace(self) {
        while not self.at_end() {
            let ch: str = self.peek()
            if ch == " " or ch == "\t" or ch == "\r" or ch == "\n" {
                self.advance()
            } elif ch == ":" and self.peek_ahead(1) == ":" {
                self.skip_line_comment()
            } elif ch == "/" and self.peek_ahead(1) == "/" and self.peek_ahead(2) == "/" {
                self.skip_line_comment()
            } elif ch == "/" and self.peek_ahead(1) == "*" {
                self.skip_block_comment()
            } else {
                break
            }
        }
    }

    func skip_line_comment(self) {
        while self.peek() == ":" or self.peek() == "/" {
            self.advance()
        }
        while self.peek() != "\n" and not self.at_end() {
            self.advance()
        }
    }

    func skip_block_comment(self) {
        self.advance()
        self.advance()
        while not self.at_end() {
            if self.peek() == "*" and self.peek_ahead(1) == "/" {
                self.advance()
                self.advance()
                return
            }
            self.advance()
        }
    }

    func read_identifier(self) {
        let start_line: i32 = self.line
        let start_col: i32 = self.col
        let value: str = ""

        while not self.at_end() {
            let ch: str = self.peek()
            if ch.isalnum() or ch == "_" {
                value = value + self.advance()
            } else {
                break
            }
        }

        if value == "func" and self.peek() == "*" {
            value = value + self.advance()
            self.tokens.append(new Token(TK_GENFUNC, value, start_line, start_col))
            return
        }

        if value == "fn" {
            self.tokens.append(new Token(TK_ERROR, "Invalid keyword 'fn'. Use 'func'", start_line, start_col))
            return
        }

        let token_type: str = KEYWORDS.get(value, TK_IDENTIFIER)
        self.tokens.append(new Token(token_type, value, start_line, start_col))
    }

    func read_number(self) {
        let start_line: i32 = self.line
        let start_col: i32 = self.col
        let value: str = ""

        if self.peek() == "0" and (self.peek_ahead(1) == "x" or self.peek_ahead(1) == "X") {
            value = value + self.advance()
            value = value + self.advance()
            while not self.at_end() {
                let ch: str = self.peek()
                if ch.isdigit() or (ch >= "a" and ch <= "f") or (ch >= "A" and ch <= "F") {
                    value = value + self.advance()
                } else {
                    break
                }
            }
            self.tokens.append(new Token(TK_HEX_NUMBER, value, start_line, start_col))
            return
        }

        if self.peek() == "0" and (self.peek_ahead(1) == "b" or self.peek_ahead(1) == "B") {
            value = value + self.advance()
            value = value + self.advance()
            while not self.at_end() {
                let ch: str = self.peek()
                if ch == "0" or ch == "1" {
                    value = value + self.advance()
                } else {
                    break
                }
            }
            self.tokens.append(new Token(TK_BIN_NUMBER, value, start_line, start_col))
            return
        }

        while not self.at_end() and self.peek().isdigit() {
            value = value + self.advance()
        }

        if self.peek() == "." and self.peek_ahead(1).isdigit() {
            value = value + self.advance()
            while not self.at_end() and self.peek().isdigit() {
                value = value + self.advance()
            }
            self.tokens.append(new Token(TK_FLOAT_NUMBER, value, start_line, start_col))
            return
        }

        self.tokens.append(new Token(TK_NUMBER, value, start_line, start_col))
    }

    func read_string(self) {
        let start_line: i32 = self.line
        let start_col: i32 = self.col
        self.advance()
        let value: str = ""

        while not self.at_end() {
            let ch: str = self.peek()
            if ch == "\"" {
                self.advance()
                self.tokens.append(new Token(TK_STRING, value, start_line, start_col))
                return
            }
            if ch == "\\" and not self.at_end() {
                self.advance()
                let esc: str = self.peek()
                if esc == "n" { value = value + "\n"; self.advance() }
                elif esc == "t" { value = value + "\t"; self.advance() }
                elif esc == "r" { value = value + "\r"; self.advance() }
                elif esc == "0" { value = value + "\0"; self.advance() }
                elif esc == "\\" { value = value + "\\"; self.advance() }
                elif esc == "\"" { value = value + "\""; self.advance() }
                else {
                    value = value + "\\" + esc
                    self.advance()
                }
            } else {
                value = value + self.advance()
            }
        }
        self.tokens.append(new Token(TK_ERROR, "Unterminated string", start_line, start_col))
    }

    func read_operator(self) {
        let start_line: i32 = self.line
        let start_col: i32 = self.col
        let ch: str = self.peek()

        if ch == "=" and self.peek_ahead(1) == "=" {
            self.advance(); self.advance()
            self.tokens.append(new Token(TK_EQ, "==", start_line, start_col))
            return
        }
        if ch == "!" and self.peek_ahead(1) == "=" {
            self.advance(); self.advance()
            self.tokens.append(new Token(TK_NE, "!=", start_line, start_col))
            return
        }
        if ch == "<" and self.peek_ahead(1) == "=" {
            self.advance(); self.advance()
            self.tokens.append(new Token(TK_LE, "<=", start_line, start_col))
            return
        }
        if ch == ">" and self.peek_ahead(1) == "=" {
            self.advance(); self.advance()
            self.tokens.append(new Token(TK_GE, ">=", start_line, start_col))
            return
        }
        if ch == "<" and self.peek_ahead(1) == "<" {
            self.advance(); self.advance()
            self.tokens.append(new Token(TK_LSHIFT, "<<", start_line, start_col))
            return
        }
        if ch == ">" and self.peek_ahead(1) == ">" {
            self.advance(); self.advance()
            self.tokens.append(new Token(TK_RSHIFT, ">>", start_line, start_col))
            return
        }
        if ch == "&" and self.peek_ahead(1) == "&" {
            self.advance(); self.advance()
            self.tokens.append(new Token(TK_AND, "&&", start_line, start_col))
            return
        }
        if ch == "|" and self.peek_ahead(1) == "|" {
            self.advance(); self.advance()
            self.tokens.append(new Token(TK_OR, "||", start_line, start_col))
            return
        }
        if ch == "-" and self.peek_ahead(1) == ">" {
            self.advance(); self.advance()
            self.tokens.append(new Token(TK_ARROW, "->", start_line, start_col))
            return
        }
        if ch == "=" and self.peek_ahead(1) == ">" {
            self.advance(); self.advance()
            self.tokens.append(new Token(TK_FAT_ARROW, "=>", start_line, start_col))
            return
        }
        if ch == "/" and self.peek_ahead(1) == "/" {
            self.tokens.append(new Token(TK_ERROR, "Invalid comment '//'. Use '::' or '///'", start_line, start_col))
            return
        }

        self.advance()
        if ch == "+" { self.tokens.append(new Token(TK_PLUS, "+", start_line, start_col)) }
        elif ch == "-" { self.tokens.append(new Token(TK_MINUS, "-", start_line, start_col)) }
        elif ch == "*" { self.tokens.append(new Token(TK_STAR, "*", start_line, start_col)) }
        elif ch == "/" { self.tokens.append(new Token(TK_SLASH, "/", start_line, start_col)) }
        elif ch == "%" { self.tokens.append(new Token(TK_PERCENT, "%", start_line, start_col)) }
        elif ch == "^" { self.tokens.append(new Token(TK_BIT_XOR, "^", start_line, start_col)) }
        elif ch == "&" { self.tokens.append(new Token(TK_BIT_AND, "&", start_line, start_col)) }
        elif ch == "|" { self.tokens.append(new Token(TK_PIPE, "|", start_line, start_col)) }
        elif ch == "~" { self.tokens.append(new Token(TK_BIT_NOT, "~", start_line, start_col)) }
        elif ch == "!" { self.tokens.append(new Token(TK_NOT, "!", start_line, start_col)) }
        elif ch == "<" { self.tokens.append(new Token(TK_LT, "<", start_line, start_col)) }
        elif ch == ">" { self.tokens.append(new Token(TK_GT, ">", start_line, start_col)) }
        elif ch == "=" { self.tokens.append(new Token(TK_ASSIGN, "=", start_line, start_col)) }
        elif ch == "." { self.tokens.append(new Token(TK_DOT, ".", start_line, start_col)) }
        elif ch == "," { self.tokens.append(new Token(TK_COMMA, ",", start_line, start_col)) }
        elif ch == ";" { self.tokens.append(new Token(TK_SEMICOLON, ";", start_line, start_col)) }
        elif ch == ":" {
            if self.peek() == ":" {
                self.advance()
                self.tokens.append(new Token(TK_COLONCOLON, "::", start_line, start_col))
            } else {
                self.tokens.append(new Token(TK_COLON, ":", start_line, start_col))
            }
        }
        elif ch == "(" { self.tokens.append(new Token(TK_LPAREN, "(", start_line, start_col)) }
        elif ch == ")" { self.tokens.append(new Token(TK_RPAREN, ")", start_line, start_col)) }
        elif ch == "{" { self.tokens.append(new Token(TK_LBRACE, "{", start_line, start_col)) }
        elif ch == "}" { self.tokens.append(new Token(TK_RBRACE, "}", start_line, start_col)) }
        elif ch == "[" { self.tokens.append(new Token(TK_LBRACKET, "[", start_line, start_col)) }
        elif ch == "]" { self.tokens.append(new Token(TK_RBRACKET, "]", start_line, start_col)) }
        elif ch == "?" { self.tokens.append(new Token(TK_QUESTION, "?", start_line, start_col)) }
        elif ch == "@" { self.tokens.append(new Token(TK_AT, "@", start_line, start_col)) }
        elif ch == "`" { self.tokens.append(new Token(TK_BACKTICK, "`", start_line, start_col)) }
        else { self.tokens.append(new Token(TK_ERROR, ch, start_line, start_col)) }
    }

    func tokenize(self) -> list {
        while not self.at_end() {
            self.skip_whitespace()
            if self.at_end() { break }

            let ch: str = self.peek()

            if ch.isalpha() or ch == "_" {
                self.read_identifier()
            } elif ch.isdigit() {
                self.read_number()
            } elif ch == "\"" {
                self.read_string()
            } else {
                self.read_operator()
            }
        }

        self.tokens.append(new Token(TK_EOF, "", self.line, self.col))
        return self.tokens
    }
}

:: ─── Public API ─────────────────────────────────────────────────────────────

func lex(source: str) -> list {
    let lexer: Lexer = new Lexer(source)
    return lexer.tokenize()
}
