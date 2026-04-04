"""
KentScript Strict Mode Integration
Patches main entry points to use strict syntax checking
"""

import sys
import os

# Add KentScript to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compiler.lexer.lexer import Lexer, TokenType
from compiler.parser.parser import Parser
from compiler.strict_checker import StrictSyntaxChecker, KentScriptSyntaxError
from error_formatter import ErrorFormatter

# Global flag for strict mode
STRICT_MODE = os.environ.get('KS_STRICT', '1') == '1'

def parse_with_strict_checking(source_code, filename="<stdin>"):
    """
    Parse source code with strict syntax checking
    
    Args:
        source_code: Source code to parse
        filename: Source filename for error messages
    
    Returns:
        AST from parser
    
    Raises:
        KentScriptSyntaxError: On syntax violations
    """
    source_lines = source_code.splitlines() if source_code else []
    
    # Tokenize
    try:
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
    except SyntaxError as e:
        # Enhance lexer errors
        error_str = str(e)
        
        # Try to extract line/col
        import re
        match = re.search(r'Line (\d+).*Col(?:umn)? (\d+)', error_str)
        if match:
            line = int(match.group(1))
            col = int(match.group(2))
            msg = error_str.split(':')[1].strip() if ':' in error_str else error_str
            
            formatted = ErrorFormatter.syntax_error(
                msg,
                line=line,
                col=col,
                source_lines=source_lines,
                filename=filename
            )
            print(formatted, file=sys.stderr)
        else:
            print(ErrorFormatter.syntax_error(
                error_str,
                source_lines=source_lines,
                filename=filename
            ), file=sys.stderr)
        raise
    
    # Strict checking on tokens
    if STRICT_MODE:
        checker = StrictSyntaxChecker(source_code, filename)
        
        for i, token in enumerate(tokens):
            # Check for ERROR tokens
            if token.type == TokenType.ERROR:
                raise KentScriptSyntaxError(
                    f"Invalid token: {token.value}",
                    line=token.line,
                    col=token.column,
                    source_lines=source_lines,
                    filename=filename
                )
            
            # Check for invalid keywords
            if token.type == TokenType.IDENTIFIER and token.value == 'fn':
                raise KentScriptSyntaxError(
                    "Invalid keyword 'fn' - use 'func' instead",
                    line=token.line,
                    col=token.column,
                    source_lines=source_lines,
                    filename=filename,
                    hint="KentScript uses 'func' for function declarations"
                )
    
    # Parse
    try:
        parser = Parser(tokens, source_code)
        ast = parser.parse()
        return ast
    except SyntaxError as e:
        # Enhance parser errors
        error_str = str(e)
        
        import re
        match = re.search(r'line (\d+)', error_str)
        if match:
            line = int(match.group(1))
            msg = error_str.split('at line')[0].strip() if 'at line' in error_str else error_str
            
            formatted = ErrorFormatter.syntax_error(
                msg,
                line=line,
                source_lines=source_lines,
                filename=filename
            )
            print(formatted, file=sys.stderr)
        else:
            print(ErrorFormatter.syntax_error(
                error_str,
                source_lines=source_lines,
                filename=filename
            ), file=sys.stderr)
        raise


def enable_strict_mode():
    """Enable strict syntax checking globally"""
    global STRICT_MODE
    STRICT_MODE = True
    os.environ['KS_STRICT'] = '1'


def disable_strict_mode():
    """Disable strict syntax checking"""
    global STRICT_MODE
    STRICT_MODE = False
    os.environ['KS_STRICT'] = '0'


# Monkey-patch main entry points
def patch_main_module():
    """Patch main.py to use strict checking"""
    try:
        import main as main_module
        
        # Store original functions
        if not hasattr(main_module, '_original_lexer'):
            main_module._original_lexer = Lexer
            main_module._original_parser = Parser
        
        # Replace with strict versions
        def strict_lexer_wrapper(source):
            lexer = Lexer(source)
            tokens = lexer.tokenize()
            
            if STRICT_MODE:
                # Check tokens for errors
                for token in tokens:
                    if token.type == TokenType.ERROR:
                        raise SyntaxError(f"Invalid token at line {token.line}: {token.value}")
            
            return lexer
        
        # Note: We can't easily replace the classes, but we can provide helper functions
        main_module.parse_with_strict_checking = parse_with_strict_checking
        
    except ImportError:
        pass  # main module not loaded yet


# Auto-patch on import
if STRICT_MODE:
    patch_main_module()
