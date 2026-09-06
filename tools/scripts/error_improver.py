#!/usr/bin/env python3
"""
KentScript Error Message Improver
Translates misleading error messages to helpful ones
"""

# Token name translations
TOKEN_TRANSLATIONS = {
    'IDENTIFIER': 'variable name',
    'LPAREN': "'('",
    'RPAREN': "')'",
    'LBRACE': "'{'",
    'RBRACE': "'}'",
    'LBRACKET': "'['",
    'RBRACKET': "']'",
    'SEMICOLON': "';'",
    'COMMA': "','",
    'COLON': "':'",
    'ASSIGN': "'='",
    'PLUS': "'+'",
    'MINUS': "'-'",
    'STAR': "'*'",
    'SLASH': "'/'",
    'PERCENT': "'%'",
    'EQ': "'=='",
    'NE': "'!='",
    'LT': "'<'",
    'GT': "'>'",
    'LE': "'<='",
    'GE': "'>='",
    'AND': "'and'",
    'OR': "'or'",
    'NOT': "'not'",
    'IF': "'if'",
    'ELSE': "'else'",
    'WHILE': "'while'",
    'FOR': "'for'",
    'FUNC': "'func'",
    'CLASS': "'class'",
    'RETURN': "'return'",
    'IMPORT': "'import'",
    'LET': "'let'",
    'CONST': "'const'",
}

def improve_error_message(error_msg):
    """Improve error message readability"""
    
    # Translate token names
    for token, readable in TOKEN_TRANSLATIONS.items():
        error_msg = error_msg.replace(f"'{token}'", readable)
        error_msg = error_msg.replace(f"Expected {token}", f"Expected {readable}")
        error_msg = error_msg.replace(f"found {token}", f"found {readable}")
    
    # Common patterns
    improvements = {
        "Expected ';' at end of statement": "Missing semicolon at end of line",
        "Expected ')' but found ';'": "Unclosed parenthesis - add ')' before ';'",
        "Expected ']' but found ';'": "Unclosed bracket - add ']' before ';'",
        "Expected '}' but found 'EOF'": "Unclosed brace - missing '}'",
        "Expected variable name but found NUMBER": "Variable names cannot start with numbers",
        "Expected variable name but found STRING": "Variable names must be identifiers, not strings",
    }
    
    for pattern, improvement in improvements.items():
        if pattern.lower() in error_msg.lower():
            error_msg = improvement
            break
    
    return error_msg

def get_context_hint(expected, found, line_content=""):
    """Get context-specific hint"""
    
    # Semicolon hints
    if 'semicolon' in expected.lower() or "';'" in expected:
        return "Add ';' at the end of the statement"
    
    # Parenthesis hints
    if "')')" in expected and "';'" in found:
        return "Close the parenthesis with ')' before the semicolon"
    
    # Bracket hints
    if "']'" in expected:
        return "Close the array or index with ']'"
    
    # Brace hints
    if "'}'" in expected:
        return "Close the block with '}'"
    
    # Variable name hints
    if 'variable name' in expected.lower():
        if found and found[0].isdigit():
            return "Variable names cannot start with numbers. Try: 'var" + found + "'"
        if found in ['if', 'else', 'while', 'for', 'func', 'class', 'return', 'match']:
            return f"'{found}' is a reserved keyword. Use a different name."
    
    # Import hints
    if 'import' in line_content.lower():
        return "Import syntax: 'import module;' or 'import mod1, mod2;' or 'import {mod1, mod2};'"
    
    return "Check the syntax and try again"

# Example usage
if __name__ == '__main__':
    test_errors = [
        "Expected 'SEMICOLON' at end of statement",
        "Expected 'RPAREN', but found 'SEMICOLON'",
        "Expected 'IDENTIFIER', but found 'NUMBER'",
        "Expected 'RBRACKET', but found 'SEMICOLON'",
    ]
    
    print("Error Message Improvements:\n")
    for error in test_errors:
        improved = improve_error_message(error)
        print(f"Before: {error}")
        print(f"After:  {improved}")
        print()
