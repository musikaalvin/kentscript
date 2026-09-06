/*
 * ks_native.h — Forward declarations for KentScript native (system_*) functions
 * used by the C-transpiled (build) backend.
 *
 * The C transpiler emits raw calls to these symbols (e.g.
 * system_kcrypt_hash_password(...)) without knowing their signatures, so we
 * declare them here and #include this header in every generated program. This
 * prevents the C compiler from assuming an `int` return type, which would
 * corrupt 64-bit pointers/values on 64-bit targets (x86-64 / aarch64).
 *
 * Signatures MUST match the definitions in runtime/c/ks_runtime.c.
 */
#ifndef KS_NATIVE_H
#define KS_NATIVE_H

#ifdef __cplusplus
extern "C" {
#endif

/* kcrypt — XChaCha20-Poly1305 AEAD (libsodium) */
char* system_kcrypt_xchacha20_encrypt(const char* data, const char* key,
                                      const char* nonce, const char* aad);
char* system_kcrypt_xchacha20_decrypt(const char* data, const char* key,
                                      const char* nonce, const char* aad);
char* system_kcrypt_derive_key(const char* password, const char* salt,
                               long long length);
char* system_kcrypt_random_key(long long length);
char* system_kcrypt_int_to_bytes(long long n);
long long system_kcrypt_bytes_to_int(const char* b);
char* system_kcrypt_lower(const char* s);

/* kcrypt — Argon2id password hashing (branded $kcrypt$2026$pyLord$... format) */
char* system_kcrypt_hash_password(const char* password, long long cost);
long long system_kcrypt_verify_password(const char* hash, const char* password);

#ifdef __cplusplus
}
#endif

#endif /* KS_NATIVE_H */
