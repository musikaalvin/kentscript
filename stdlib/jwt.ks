:: jwt - JSON Web Tokens (HS256)
::
:: Usage:
::   import jwt;
::   let token = jwt.encode({"user": "admin"}, "mysecret");
::   let data = jwt.decode(token, "mysecret");

func encode(payload, secret, algorithm) {
    if algorithm == none { algorithm = "HS256"; }
    return system_jwt_encode(payload, secret, algorithm);
}

func decode(token, secret) {
    return system_jwt_decode(token, secret);
}

export { encode, decode };
