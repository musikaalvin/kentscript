/* KentScript Core Lexer in C */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

typedef enum {
    TOK_EOF = 0,
    TOK_FUNC,
    TOK_LET,
    TOK_IF,
    TOK_WHILE,
    TOK_RETURN,
    TOK_IMPORT,
    TOK_IDENT,
    TOK_NUMBER,
    TOK_STRING,
    TOK_LPAREN,
    TOK_RPAREN,
    TOK_LBRACE,
    TOK_RBRACE,
    TOK_SEMICOLON,
    TOK_COLON,
    TOK_COMMA,
    TOK_PLUS,
    TOK_MINUS,
    TOK_STAR,
    TOK_SLASH,
    TOK_EQ,
    TOK_LT,
    TOK_GT,
    TOK_ARROW
} TokenType;

typedef struct {
    TokenType type;
    char *value;
    int line;
    int col;
} Token;

typedef struct {
    const char *source;
    int pos;
    int line;
    int col;
    Token *tokens;
    int token_count;
    int token_capacity;
} Lexer;

Lexer* lexer_new(const char *source) {
    Lexer *lex = malloc(sizeof(Lexer));
    lex->source = source;
    lex->pos = 0;
    lex->line = 1;
    lex->col = 1;
    lex->token_capacity = 1024;
    lex->token_count = 0;
    lex->tokens = malloc(sizeof(Token) * lex->token_capacity);
    return lex;
}

void lexer_add_token(Lexer *lex, TokenType type, const char *value) {
    if (lex->token_count >= lex->token_capacity) {
        lex->token_capacity *= 2;
        lex->tokens = realloc(lex->tokens, sizeof(Token) * lex->token_capacity);
    }
    
    Token tok;
    tok.type = type;
    tok.value = value ? strdup(value) : NULL;
    tok.line = lex->line;
    tok.col = lex->col;
    lex->tokens[lex->token_count++] = tok;
}

char lexer_peek(Lexer *lex) {
    if (lex->pos >= strlen(lex->source)) return '\0';
    return lex->source[lex->pos];
}

char lexer_advance(Lexer *lex) {
    if (lex->pos >= strlen(lex->source)) return '\0';
    char ch = lex->source[lex->pos++];
    if (ch == '\n') {
        lex->line++;
        lex->col = 1;
    } else {
        lex->col++;
    }
    return ch;
}

void lexer_skip_whitespace(Lexer *lex) {
    while (isspace(lexer_peek(lex))) {
        lexer_advance(lex);
    }
}

void lexer_skip_comment(Lexer *lex) {
    if (lexer_peek(lex) == ':' && lex->source[lex->pos + 1] == ':') {
        while (lexer_peek(lex) != '\n' && lexer_peek(lex) != '\0') {
            lexer_advance(lex);
        }
    }
}

char* lexer_read_identifier(Lexer *lex) {
    int start = lex->pos;
    while (isalnum(lexer_peek(lex)) || lexer_peek(lex) == '_') {
        lexer_advance(lex);
    }
    int len = lex->pos - start;
    char *ident = malloc(len + 1);
    strncpy(ident, lex->source + start, len);
    ident[len] = '\0';
    return ident;
}

char* lexer_read_number(Lexer *lex) {
    int start = lex->pos;
    while (isdigit(lexer_peek(lex))) {
        lexer_advance(lex);
    }
    int len = lex->pos - start;
    char *num = malloc(len + 1);
    strncpy(num, lex->source + start, len);
    num[len] = '\0';
    return num;
}

char* lexer_read_string(Lexer *lex) {
    lexer_advance(lex); // skip opening quote
    int start = lex->pos;
    while (lexer_peek(lex) != '"' && lexer_peek(lex) != '\0') {
        lexer_advance(lex);
    }
    int len = lex->pos - start;
    char *str = malloc(len + 1);
    strncpy(str, lex->source + start, len);
    str[len] = '\0';
    lexer_advance(lex); // skip closing quote
    return str;
}

void lexer_tokenize(Lexer *lex) {
    while (lexer_peek(lex) != '\0') {
        lexer_skip_whitespace(lex);
        lexer_skip_comment(lex);
        
        char ch = lexer_peek(lex);
        
        if (ch == '\0') break;
        
        if (isalpha(ch) || ch == '_') {
            char *ident = lexer_read_identifier(lex);
            
            if (strcmp(ident, "func") == 0) lexer_add_token(lex, TOK_FUNC, ident);
            else if (strcmp(ident, "let") == 0) lexer_add_token(lex, TOK_LET, ident);
            else if (strcmp(ident, "if") == 0) lexer_add_token(lex, TOK_IF, ident);
            else if (strcmp(ident, "while") == 0) lexer_add_token(lex, TOK_WHILE, ident);
            else if (strcmp(ident, "return") == 0) lexer_add_token(lex, TOK_RETURN, ident);
            else if (strcmp(ident, "import") == 0) lexer_add_token(lex, TOK_IMPORT, ident);
            else lexer_add_token(lex, TOK_IDENT, ident);
            
            free(ident);
        }
        else if (isdigit(ch)) {
            char *num = lexer_read_number(lex);
            lexer_add_token(lex, TOK_NUMBER, num);
            free(num);
        }
        else if (ch == '"') {
            char *str = lexer_read_string(lex);
            lexer_add_token(lex, TOK_STRING, str);
            free(str);
        }
        else if (ch == '(') { lexer_advance(lex); lexer_add_token(lex, TOK_LPAREN, "("); }
        else if (ch == ')') { lexer_advance(lex); lexer_add_token(lex, TOK_RPAREN, ")"); }
        else if (ch == '{') { lexer_advance(lex); lexer_add_token(lex, TOK_LBRACE, "{"); }
        else if (ch == '}') { lexer_advance(lex); lexer_add_token(lex, TOK_RBRACE, "}"); }
        else if (ch == ';') { lexer_advance(lex); lexer_add_token(lex, TOK_SEMICOLON, ";"); }
        else if (ch == ':') { lexer_advance(lex); lexer_add_token(lex, TOK_COLON, ":"); }
        else if (ch == ',') { lexer_advance(lex); lexer_add_token(lex, TOK_COMMA, ","); }
        else if (ch == '+') { lexer_advance(lex); lexer_add_token(lex, TOK_PLUS, "+"); }
        else if (ch == '-') {
            lexer_advance(lex);
            if (lexer_peek(lex) == '>') {
                lexer_advance(lex);
                lexer_add_token(lex, TOK_ARROW, "->");
            } else {
                lexer_add_token(lex, TOK_MINUS, "-");
            }
        }
        else if (ch == '*') { lexer_advance(lex); lexer_add_token(lex, TOK_STAR, "*"); }
        else if (ch == '/') { lexer_advance(lex); lexer_add_token(lex, TOK_SLASH, "/"); }
        else if (ch == '=') { lexer_advance(lex); lexer_add_token(lex, TOK_EQ, "="); }
        else if (ch == '<') { lexer_advance(lex); lexer_add_token(lex, TOK_LT, "<"); }
        else if (ch == '>') { lexer_advance(lex); lexer_add_token(lex, TOK_GT, ">"); }
        else {
            lexer_advance(lex);
        }
    }
    
    lexer_add_token(lex, TOK_EOF, NULL);
}

void lexer_free(Lexer *lex) {
    for (int i = 0; i < lex->token_count; i++) {
        if (lex->tokens[i].value) free(lex->tokens[i].value);
    }
    free(lex->tokens);
    free(lex);
}

int lexer_get_token_count(Lexer *lex) {
    return lex->token_count;
}

#ifdef TEST_LEXER
int main() {
    const char *source = "func add(a: int, b: int) -> int { return a + b; }";
    Lexer *lex = lexer_new(source);
    lexer_tokenize(lex);
    
    printf("Tokens: %d\n", lex->token_count);
    for (int i = 0; i < lex->token_count; i++) {
        printf("  [%d] Type=%d Value='%s' Line=%d Col=%d\n",
               i, lex->tokens[i].type, 
               lex->tokens[i].value ? lex->tokens[i].value : "(null)",
               lex->tokens[i].line, lex->tokens[i].col);
    }
    
    lexer_free(lex);
    return 0;
}
#endif
