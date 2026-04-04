"""
KentScript Strict Syntax Checker
Enforces strict syntax rules:
- Semicolons required after statements
- Proper bracket matching
- No missing tokens
- Clear error messages
"""

from compiler.lexer.lexer import TokenType
from error_formatter import ErrorFormatter
import sys

class StrictSyntaxChecker:
    """Enforces strict syntax rules during parsing"""
    
    # Statements that MUST end with semicolon
    SEMICOLON_REQUIRED = {
        'let', 'const', 'return', 'break', 'continue',
        'import', 'from', 'export', 'raise', 'yield'
    }
    
    # Tokens that open blocks (don't need semicolons)
    BLOCK_OPENERS = {
        TokenType.LBRACE, TokenType.IF, TokenType.WHILE, 
        TokenType.FOR, TokenType.FUNC, TokenType.CLASS,
        TokenType.STRUCT, TokenType.ENUM, TokenType.MATCH,
        TokenType.TRY, TokenType.UNSAFE
    }
    
    def __init__(self, source_code, filename="<stdin>"):
        self.source = source_code
        self.source_lines = source_code.splitlines() if source_code else []
        self.filename = filename
        self.errors = []
    
    def check_semicolon(self, stmt_type, token, next_token):
        """
        Check if semicolon is required after statement
        
        Args:
            stmt_type: Type of statement (let, return, etc.)
            token: Last token of the statement
            next_token: Next token after statement
        
        Returns:
            True if valid, False if error
        """
        if stmt_type in self.SEMICOLON_REQUIRED:
            if next_token.type != TokenType.SEMICOLON:
                self.errors.append(
                    ErrorFormatter.syntax_error(
                        f"Missing semicolon after '{stmt_type}' statement",
                        line=token.line,
                        col=token.column,
                        source_lines=self.source_lines,
                        filename=self.filename,
                        hint=f"Add semicolon: {stmt_type} ... ;"
                    )
                )
                return False
        return True
    
    def check_expression_semicolon(self, token, next_token, in_block=True):
        """
        Check if expression statement needs semicolon
        
        Args:
            token: Last token of expression
            next_token: Next token
            in_block: Whether we're inside a block
        """
        if not in_block:
            return True
        
        # Expression statements need semicolons unless followed by }
        if next_token.type not in {TokenType.RBRACE, TokenType.EOF, TokenType.SEMICOLON}:
            # Check if this looks like an expression statement
            if token.type in {TokenType.IDENTIFIER, TokenType.RPAREN, TokenType.RBRACKET, 
                             TokenType.NUMBER, TokenType.STRING, TokenType.TRUE, TokenType.FALSE}:
                self.errors.append(
                    ErrorFormatter.syntax_error(
                        "Missing semicolon after expression statement",
                        line=token.line,
                        col=token.column,
                        source_lines=self.source_lines,
                        filename=self.filename,
                        hint="Add semicolon after the expression"
                    )
                )
                return False
        return True
    
    def check_bracket_match(self, open_token, close_token, expected_close):
        """
        Check if brackets match correctly
        
        Args:
            open_token: Opening bracket token
            close_token: Closing bracket token (or None if missing)
            expected_close: Expected closing bracket type
        """
        if close_token is None:
            bracket_map = {
                TokenType.LPAREN: ')',
                TokenType.LBRACE: '}',
                TokenType.LBRACKET: ']'
            }
            self.errors.append(
                ErrorFormatter.syntax_error(
                    f"Unclosed '{bracket_map.get(open_token.type, '?')}' - missing closing bracket",
                    line=open_token.line,
                    col=open_token.column,
                    source_lines=self.source_lines,
                    filename=self.filename,
                    hint=f"Add closing '{bracket_map.get(open_token.type, '?')}'"
                )
            )
            return False
        
        if close_token.type != expected_close:
            self.errors.append(
                ErrorFormatter.syntax_error(
                    f"Mismatched brackets: expected '{expected_close.name}', got '{close_token.type.name}'",
                    line=close_token.line,
                    col=close_token.column,
                    source_lines=self.source_lines,
                    filename=self.filename,
                    hint="Check bracket pairing"
                )
            )
            return False
        
        return True
    
    def check_unexpected_token(self, token, expected=None, context=None):
        """
        Report unexpected token error
        
        Args:
            token: The unexpected token
            expected: What was expected (string or list)
            context: Context where error occurred
        """
        msg = f"Unexpected token '{token.value or token.type.name}'"
        
        if expected:
            if isinstance(expected, list):
                expected_str = ", ".join(str(e) for e in expected)
                msg += f" - expected one of: {expected_str}"
            else:
                msg += f" - expected {expected}"
        
        if context:
            msg += f" in {context}"
        
        self.errors.append(
            ErrorFormatter.syntax_error(
                msg,
                line=token.line,
                col=token.column,
                source_lines=self.source_lines,
                filename=self.filename
            )
        )
    
    def check_invalid_keyword(self, token, valid_keywords=None):
        """Check for invalid or misused keywords"""
        if token.value == 'fn':
            self.errors.append(
                ErrorFormatter.syntax_error(
                    "Invalid keyword 'fn' - KentScript uses 'func' for functions",
                    line=token.line,
                    col=token.column,
                    source_lines=self.source_lines,
                    filename=self.filename,
                    hint="Use 'func' instead of 'fn'"
                )
            )
            return False
        
        return True
    
    def check_unterminated_string(self, token):
        """Check for unterminated string literals"""
        if token.type == TokenType.ERROR and "unterminated" in str(token.value).lower():
            self.errors.append(
                ErrorFormatter.syntax_error(
                    "Unterminated string literal",
                    line=token.line,
                    col=token.column,
                    source_lines=self.source_lines,
                    filename=self.filename,
                    hint="Add closing quote"
                )
            )
            return False
        return True
    
    def has_errors(self):
        """Check if any errors were found"""
        return len(self.errors) > 0
    
    def print_errors(self):
        """Print all accumulated errors"""
        for error in self.errors:
            print(error, file=sys.stderr)
    
    def raise_if_errors(self):
        """Raise exception if errors found"""
        if self.has_errors():
            self.print_errors()
            raise SyntaxError(f"Found {len(self.errors)} syntax error(s)")


class KentScriptSyntaxError(SyntaxError):
    """Enhanced syntax error with source context"""
    
    def __init__(self, message, line=None, col=None, source_lines=None, filename=None, hint=None):
        self.message = message
        self.line = line
        self.col = col
        self.source_lines = source_lines
        self.filename = filename
        self.hint = hint
        
        # Format the error
        formatted = ErrorFormatter.syntax_error(
            message, line, col, source_lines, filename, hint
        )
        super().__init__(formatted)
    
    def __str__(self):
        return ErrorFormatter.syntax_error(
            self.message, self.line, self.col, 
            self.source_lines, self.filename, self.hint
        )


# Convenience function for strict checking
def enforce_strict_syntax(tokens, source_code, filename="<stdin>"):
    """
    Enforce strict syntax rules on token stream
    
    Args:
        tokens: List of tokens from lexer
        source_code: Original source code
        filename: Source filename
    
    Raises:
        KentScriptSyntaxError: If syntax violations found
    """
    checker = StrictSyntaxChecker(source_code, filename)
    
    # Basic checks on token stream
    for i, token in enumerate(tokens):
        # Check for error tokens
        if token.type == TokenType.ERROR:
            checker.check_unterminated_string(token)
        
        # Check for invalid keywords
        if token.type == TokenType.IDENTIFIER:
            checker.check_invalid_keyword(token)
    
    # Raise if any errors found
    checker.raise_if_errors()
    
    return checker
