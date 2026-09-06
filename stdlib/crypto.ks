:: crypto - Cryptographic functions

func md5(data) {
    return crypto_md5(data);
}

func sha1(data) {
    return crypto_sha1(data);
}

func sha256(data) {
    return crypto_sha256(data);
}

func sha512(data) {
    return crypto_sha512(data);
}

func hmac(key, message, algorithm) {
    if algorithm == none { algorithm = "sha256"; }
    return crypto_hmac(key, message, algorithm);
}

func pbkdf2(password, salt, iterations, keylen, algorithm) {
    if iterations == none { iterations = 100000; }
    if keylen == none { keylen = 32; }
    if algorithm == none { algorithm = "sha256"; }
    return crypto_pbkdf2(password, salt, iterations, keylen, algorithm);
}

func random_bytes(n) {
    return crypto_random_bytes(n);
}

func encrypt_aes(data, key, mode, iv) {
    if mode == none { mode = "CBC"; }
    return crypto_encrypt_aes(data, key, mode, iv);
}

func decrypt_aes(data, key, mode, iv) {
    if mode == none { mode = "CBC"; }
    return crypto_decrypt_aes(data, key, mode, iv);
}

func hash_password(password, salt) {
    if salt == none {
        salt = random_bytes(16);
    }
    return pbkdf2(password, salt, 100000, 32);
}

func verify_password(password, hash, salt) {
    let computed = hash_password(password, salt);
    return computed == hash;
}

:: Runtime interface
func crypto_md5(data) { return system_crypto_md5(data); }
func crypto_sha1(data) { return system_crypto_sha1(data); }
func crypto_sha256(data) { return system_crypto_sha256(data); }
func crypto_sha512(data) { return system_crypto_sha512(data); }
func crypto_hmac(key, message, algorithm) { return system_crypto_hmac(key, message, algorithm); }
func crypto_pbkdf2(password, salt, iterations, keylen, algorithm) { return system_crypto_pbkdf2(password, salt, iterations, keylen, algorithm); }
func crypto_random_bytes(n) { return system_crypto_random_bytes(n); }
func crypto_encrypt_aes(data, key, mode, iv) { return system_crypto_encrypt_aes(data, key, mode, iv); }
func crypto_decrypt_aes(data, key, mode, iv) { return system_crypto_decrypt_aes(data, key, mode, iv); }

export {
    md5, sha1, sha256, sha512,
    hmac, pbkdf2, random_bytes,
    encrypt_aes, decrypt_aes,
    hash_password, verify_password
};
