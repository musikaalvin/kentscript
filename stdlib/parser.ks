:: KentScript Parser - written in KentScript
:: Self-hosting parser component

let NODE_FUNC: int = 1;
let NODE_LET: int = 2;
let NODE_IF: int = 3;
let NODE_WHILE: int = 4;
let NODE_RETURN: int = 5;
let NODE_CALL: int = 6;
let NODE_BINOP: int = 7;
let NODE_NUMBER: int = 8;
let NODE_IDENT: int = 9;

let current_token: int = 0;
let token_count: int = 0;

func peek_token() -> int {
    return current_token;
}

func advance_token() {
    current_token = current_token + 1;
}

func parse_number() -> int {
    let node: int = NODE_NUMBER;
    advance_token();
    return node;
}

func parse_ident() -> int {
    let node: int = NODE_IDENT;
    advance_token();
    return node;
}

func parse_primary() -> int {
    let tok: int = peek_token();
    
    if tok == 0 {
        return parse_number();
    }
    
    return parse_ident();
}

func parse_binop() -> int {
    let left: int = parse_primary();
    let op: int = peek_token();
    advance_token();
    let right: int = parse_primary();
    
    return NODE_BINOP;
}

func parse_expr() -> int {
    return parse_binop();
}

func parse_let() -> int {
    advance_token();
    let name: int = parse_ident();
    advance_token();
    let value: int = parse_expr();
    
    return NODE_LET;
}

func parse_func() -> int {
    advance_token();
    let name: int = parse_ident();
    advance_token();
    
    :: Parse parameters
    advance_token();
    
    :: Parse body
    let body: int = parse_expr();
    
    return NODE_FUNC;
}

func parse_if() -> int {
    advance_token();
    let condition: int = parse_expr();
    let then_branch: int = parse_expr();
    
    return NODE_IF;
}

func parse_while() -> int {
    advance_token();
    let condition: int = parse_expr();
    let body: int = parse_expr();
    
    return NODE_WHILE;
}

func parse_return() -> int {
    advance_token();
    let value: int = parse_expr();
    
    return NODE_RETURN;
}

func parse_statement() -> int {
    let tok: int = peek_token();
    
    if tok == 1 {
        return parse_func();
    }
    if tok == 2 {
        return parse_let();
    }
    if tok == 3 {
        return parse_if();
    }
    if tok == 4 {
        return parse_while();
    }
    if tok == 5 {
        return parse_return();
    }
    
    return parse_expr();
}

func parse_program() -> int {
    let ast: int = 0;
    
    while current_token < token_count {
        let stmt: int = parse_statement();
        ast = ast + 1;
    }
    
    return ast;
}

func init_parser(tokens: int, count: int) {
    current_token = 0;
    token_count = count;
}
