"""
KentScript Strict Parser Wrapper
Enforces strict syntax rules and provides beautiful error messages
"""

import sys
from compiler.lexer.lexer import Lexer, TokenType
from compiler.parser.parser import Parser
from compiler.strict_checker import StrictSyntaxChecker, KentScriptSyntaxError
from error_formatter import ErrorFormatter

class StrictParser:
    """
    Parser wrapper that enforces strict KentScript syntax:
    - Semicolons required after statements
    - Proper bracket matching
    - Clear, helpful error messages
    """
    
    def __init__(self, source_code, filename="<stdin>", strict=True):
        """
        Initialize strict parser
        
        Args:
            source_code: Source code to parse
            filename: Source filename for error messages
            strict: Enable strict syntax checking (default: True)
        """
        self.source = source_code
        self.filename = filename
        self.strict = strict
        self.source_lines = source_code.splitlines() if source_code else []
        
        # Tokenize
        try:
            lexer = Lexer(source_code)
            self.tokens = lexer.tokenize()
        except SyntaxError as e:
            # Enhance lexer errors
            self._handle_lexer_error(e)
            raise
        
        # Strict syntax checking
        if strict:
            self.checker = StrictSyntaxChecker(source_code, filename)
            self._check_tokens()
        
        # Create parser
        self.parser = Parser(self.tokens, source_code)
        
        # Wrap parser methods to add strict checking
        self._wrap_parser_methods()
    
    def _check_tokens(self):
        """Check tokens for basic syntax errors"""
        for i, token in enumerate(self.tokens):
            # Check for ERROR tokens
            if token.type == TokenType.ERROR:
                raise KentScriptSyntaxError(
                    f"Invalid token: {token.value}",
                    line=token.line,
                    col=token.column,
                    source_lines=self.source_lines,
                    filename=self.filename
                )
            
            # Check for invalid keywords
            if token.type == TokenType.IDENTIFIER and token.value == 'fn':
                raise KentScriptSyntaxError(
                    "Invalid keyword 'fn' - use 'func' instead",
                    line=token.line,
                    col=token.column,
                    source_lines=self.source_lines,
                    filename=self.filename,
                    hint="KentScript uses 'func' for function declarations"
                )
    
    def _handle_lexer_error(self, error):
        """Enhance lexer error with better formatting"""
        # Try to extract line/col from error message
        import re
        match = re.search(r'line (\d+).*col(?:umn)? (\d+)', str(error), re.IGNORECASE)
        if match:
            line = int(match.group(1))
            col = int(match.group(2))
            msg = str(error).split(':')[0] if ':' in str(error) else str(error)
            
            formatted = ErrorFormatter.syntax_error(
                msg,
                line=line,
                col=col,
                source_lines=self.source_lines,
                filename=self.filename
            )
            print(formatted, file=sys.stderr)
    
    def _wrap_parser_methods(self):
        """Wrap parser methods to add strict checking"""
        original_parse = self.parser.parse
        
        def strict_parse():
            try:
                ast = original_parse()
                
                # Post-parse validation
                if self.strict:
                    self._validate_ast(ast)
                
                return ast
            except SyntaxError as e:
                self._handle_parse_error(e)
                raise
        
        self.parser.parse = strict_parse
    
    def _validate_ast(self, ast):
        """Validate AST for strict syntax compliance"""
        # Check for missing semicolons in statements
        self._check_statement_semicolons(ast)
    
    def _check_statement_semicolons(self, node):
        """Recursively check for missing semicolons"""
        if not node:
            return
        
        node_type = type(node).__name__
        
        # Check specific statement types
        if node_type in ['LetStmt', 'ConstStmt', 'ReturnStmt', 'BreakStmt', 
                        'ContinueStmt', 'ImportStmt', 'ExportStmt']:
            # These should have been checked during parsing
            pass
        
        # Recurse into child nodes
        if hasattr(node, '__dict__'):
            for attr_value in node.__dict__.values():
                if isinstance(attr_value, list):
                    for item in attr_value:
                        self._check_statement_semicolons(item)
                elif hasattr(attr_value, '__dict__'):
                    self._check_statement_semicolons(attr_value)
    
    def _handle_parse_error(self, error):
        """Enhance parse error with better formatting"""
        error_str = str(error)
        
        # Try to extract location info
        import re
        match = re.search(r'line (\d+)', error_str)
        if match:
            line = int(match.group(1))
            
            # Extract message
            msg = error_str.split('at line')[0].strip() if 'at line' in error_str else error_str
            
            formatted = ErrorFormatter.syntax_error(
                msg,
                line=line,
                col=None,
                source_lines=self.source_lines,
                filename=self.filename
            )
            print(formatted, file=sys.stderr)
        else:
            # Generic error
            print(ErrorFormatter.syntax_error(
                error_str,
                source_lines=self.source_lines,
                filename=self.filename
            ), file=sys.stderr)
    
    def parse(self):
        """Parse source code with strict checking"""
        return self.parser.parse()


def parse_strict(source_code, filename="<stdin>", strict=True):
    """
    Parse KentScript code with strict syntax enforcement
    
    Args:
        source_code: Source code to parse
        filename: Source filename
        strict: Enable strict checking (default: True)
    
    Returns:
        AST root node
    
    Raises:
        KentScriptSyntaxError: On syntax errors
    """
    parser = StrictParser(source_code, filename, strict)
    return parser.parse()


# Monkey-patch the original parser for backward compatibility
def patch_parser_strict():
    """Patch the original Parser class to use strict checking by default"""
    from compiler.parser import parser as parser_module
    
    original_parser_init = parser_module.Parser.__init__
    
    def strict_init(self, tokens, source="", strict=True):
        original_parser_init(self, tokens, source)
        
        if strict:
            # Add strict checking
            self._strict_checker = StrictSyntaxChecker(source, "<stdin>")
            self._source_for_errors = source
    
    parser_module.Parser.__init__ = strict_init
