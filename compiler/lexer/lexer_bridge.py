#!/usr/bin/env python3
"""
KentScript Lexer Bridge
Attempts to use the native KentScript lexer (lexer_unified.ks)
Falls back to Python implementation if unavailable
"""

import os
import sys

# Try to use KentScript native lexer
_USE_KS_LEXER = os.environ.get('KS_USE_NATIVE_LEXER', '1') == '1'
_ks_lexer_available = False

if _USE_KS_LEXER:
    try:
        # Import KentScript runtime to execute .ks files
        from ks_core import Interpreter
        
        # Load the unified lexer
        lexer_path = os.path.join(os.path.dirname(__file__), 'lexer_unified.ks')
        if os.path.exists(lexer_path):
            _ks_interp = Interpreter()
            with open(lexer_path, 'r') as f:
                _ks_interp.run(f.read())
            _ks_lexer_available = True
            print("[*] Using native KentScript lexer (lexer_unified.ks)")
    except Exception as e:
        print(f"[!] Failed to load KentScript lexer: {e}")
        print("[*] Falling back to Python lexer")

# Import Python lexer as fallback
from compiler.lexer.lexer import Lexer as PyLexer, Token, TokenType

class Lexer:
    """
    Unified lexer interface
    Uses KentScript native lexer when available, Python fallback otherwise
    """
    def __init__(self, source: str):
        self.source = source
        self._py_lexer = PyLexer(source)
    
    def tokenize(self):
        """Tokenize source code"""
        if _ks_lexer_available:
            try:
                # Call KentScript lexer
                result = _ks_interp.call_function('lex', [self.source])
                # Convert KS tokens to Python Token objects
                return self._convert_ks_tokens(result)
            except Exception as e:
                print(f"[!] KS lexer failed: {e}, using Python fallback")
        
        # Use Python lexer
        return self._py_lexer.tokenize()
    
    def _convert_ks_tokens(self, ks_tokens):
        """Convert KentScript tokens to Python Token objects"""
        py_tokens = []
        for kt in ks_tokens:
            # Map KS token to Python Token
            token_type = self._map_token_type(kt.kind)
            py_tokens.append(Token(token_type, kt.value, kt.line, kt.col))
        return py_tokens
    
    def _map_token_type(self, ks_type: str):
        """Map KentScript token type string to Python TokenType enum"""
        # Direct mapping from string to enum
        return getattr(TokenType, ks_type, TokenType.ERROR)

# Export the same interface as lexer.py
__all__ = ['Lexer', 'Token', 'TokenType']
