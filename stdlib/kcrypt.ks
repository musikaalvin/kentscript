:: kcrypt - Advanced cryptographic module using Krypton (XChaCha20-Poly1305 AEAD)
::
:: This module wraps the system_kcrypt_* native functions for high-assurance
:: authenticated encryption with associated data (AEAD). It uses the
:: XChaCha20-Poly1305 IETF construction via libsodium (PyNaCl).
::
:: Password hashing: kcrypt also provides Argon2id-based password hashing with a
:: branded, self-describing $kcrypt$<year>$pyLord$<cost>$<salt>$<payload>$ string
::   <year> is the current calendar year (taken from the system clock)
:: (see hash_password / verify_password).
::
:: File extension convention: .kcrypt (encrypted file format)
:: File format: magic(6) + meta_len(4) + meta_json + encrypted_payload
:: File format: KC1\nmetadata_json\nencrypted_base64
::
:: CLI usage:
::   python kentscript.py -hx <file.kcrypt>           :: hex dump encrypted file
::   python kentscript.py -hx <file.kcrypt> <key>     :: decrypt and show plaintext
::   python kentscript.py --hexdump <file.kcrypt>     :: same as -hx (verbose)
::
:: Dependencies: pip install pynacl

:: ========================================================================
:: LOW-LEVEL ENCRYPTION PRIMITIVES
:: ========================================================================

:: Encrypt data using XChaCha20-Poly1305 AEAD.
:: Returns base64-encoded ciphertext (nonce + ciphertext + tag).
func encrypt(data, key, nonce, aad) {
    return system_kcrypt_xchacha20_encrypt(data, key, nonce, aad);
}

:: Decrypt data using XChaCha20-Poly1305 AEAD.
:: Returns plaintext as a string.
func decrypt(data, key, nonce, aad) {
    return system_kcrypt_xchacha20_decrypt(data, key, nonce, aad);
}

:: Derive a key from a password using scrypt (N=16384, r=8, p=1).
func derive_key(password, salt, length) {
    if length == none { length = 32; }
    return system_kcrypt_derive_key(password, salt, length);
}

:: Generate a random key suitable for XChaCha20-Poly1305.
func random_key(length) {
    if length == none { length = 32; }
    return system_kcrypt_random_key(length);
}

:: ========================================================================
:: PASSWORD HASHING (ARGON2ID, BRANDED $kcrypt$ FORMAT)
:: ========================================================================
::
:: Hash a password using Argon2id (via libsodium) and return a branded
:: string of the form:
::   $kcrypt$<year>$pyLord$<cost>$<salt>$<payload>
::   <year> is the current calendar year (from the system clock)
::   - <cost>    : 2-digit cost tier (03..24)
::   - <salt>    : 16 random bytes, bcrypt-variant base64 (22 chars)
::   - <payload> : 24 derived bytes, bcrypt-variant base64 (32 chars)
:: The actual Argon2id parameters (opslimit / memlimit) are derived from
:: the cost tier inside the native binding.
func hash_password(password, cost) {
    if cost == none { cost = 8; }
    return system_kcrypt_hash_password(password, cost);
}

:: Verify a password against a branded $kcrypt$ hash string.
:: Returns true if the password matches, false otherwise.
func verify_password(hash_str, password) {
    return system_kcrypt_verify_password(hash_str, password);
}

:: ========================================================================
:: CONVENIENCE ENCRYPTION (PASSWORD-BASED)
:: ========================================================================

:: Encrypt with a key derived from a password via scrypt.
func encrypt_with_password(data, password, salt, nonce, aad) {
    let derived_key = derive_key(password, salt, 32);
    return encrypt(data, derived_key, nonce, aad);
}

:: Decrypt with a key derived from a password via scrypt.
func decrypt_with_password(data, password, salt, aad) {
    let derived_key = derive_key(password, salt, 32);
    return decrypt(data, derived_key, none, aad);
}

:: ========================================================================
:: FILE FORMAT CONSTANTS
:: ========================================================================

:: Default file extension for kcrypt encrypted files
let DEFAULT_EXTENSION = ".kcrypt";

:: Magic bytes identifying kcrypt file format (3 bytes)
let MAGIC = "KC1";

:: ========================================================================
:: METADATA EMBEDDING
:: ========================================================================

:: Build a metadata JSON string for a kcrypt file.
:: @param filepath  - original file path being encrypted
:: @param title     - title for the encrypted file
:: @param subject   - subject or description
:: @param key_id    - optional key identifier / fingerprint
:: @param status    - encryption status (default: "encrypted")
:: @param extra     - optional extra key-value pairs
func build_metadata(filepath, title, subject, key_id, status, extra) {
    import json;

    let now = system_time_now();

    :: Default values
    if title == none or title == "" {
        title = "Encrypted by kcrypt";
    }
    if subject == none {
        subject = filepath;
    }
    if key_id == none {
        key_id = "none";
    }
    if status == none {
        status = "encrypted";
    }

    :: Build timestamp string
    let ts = str(now.year) + "-";
    if now.month < 10 { ts = ts + "0"; }
    ts = ts + str(now.month) + "-";
    if now.day < 10 { ts = ts + "0"; }
    ts = ts + str(now.day) + " ";
    if now.hour < 10 { ts = ts + "0"; }
    ts = ts + str(now.hour) + ":";
    if now.minute < 10 { ts = ts + "0"; }
    ts = ts + str(now.minute) + ":";
    if now.second < 10 { ts = ts + "0"; }
    ts = ts + str(now.second);

    :: Build metadata dict
    let meta = {
        "title": title,
        "subject": subject,
        "key_id": key_id,
        "status": status,
        "timestamp": ts,
        "tool": "kcrypt v1.0",
        "original_filename": filepath,
        "original_size": "pending",
    };

    :: Merge extra metadata if provided
    if extra != none {
        for k, v in extra {
            meta[k] = v;
        }
    }

    return json.dumps(meta);
}

:: ========================================================================
:: ENCRYPTED FILE FORMAT
:: ========================================================================

:: .kcrypt file format (text-safe):
::   Line 1: KC1                         (magic header)
::   Line 2: {"metadata_json"...}        (metadata JSON)
::   Line 3: base64_encrypted_payload    (XChaCha20-Poly1305 ciphertext)

:: Write a .kcrypt file with embedded metadata.
:: @param filepath   - path to plaintext file
:: @param key        - encryption key
:: @param title      - optional title for the metadata
:: @param subject    - optional subject
:: @param key_id     - optional key identifier
func encrypt_file(filepath, key, title, subject, key_id) {
    import fileio;
    import json;

    :: Read the plaintext
    let data = fileio.read_text(filepath);
    let plaintext_size = len(data);

    :: Build metadata
    let meta_json = build_metadata(filepath, title, subject, key_id, "encrypted", none);

    :: Encrypt the payload (already base64-encoded by system_kcrypt_xchacha20_encrypt)
    let encrypted = encrypt(data, key);

    :: Update metadata with actual sizes
    let meta = json.loads(meta_json);
    meta["encrypted_size"] = len(encrypted);
    meta["original_size"] = plaintext_size;
    meta_json = json.dumps(meta);

    :: Write 3-line text file
    let out_path = filepath + DEFAULT_EXTENSION;
    let output = MAGIC + "\n" + meta_json + "\n" + encrypted;
    fileio.write_text(out_path, output);

    return out_path;
}

:: Read a .kcrypt file and extract metadata.
:: Returns a dict with "metadata" and "encrypted" keys.
:: @param filepath - path to .kcrypt file
func read_kcrypt_file(filepath) {
    import fileio;
    import json;

    let raw = fileio.read_text(filepath);

    :: Find newlines to split the 3 parts
    let first_nl = -1;
    let second_nl = -1;
    for i in 0..len(raw) {
        if raw[i] == "\n" {
            if first_nl == -1 {
                first_nl = i;
            } else if second_nl == -1 {
                second_nl = i;
                break;
            }
        }
    }

    if first_nl == -1 or second_nl == -1 {
        return {"error": "Not a valid .kcrypt file (missing headers)"};
    }

    let magic = raw[0:first_nl];
    let meta_json = raw[first_nl + 1 : second_nl];
    let encrypted = raw[second_nl + 1 :];

    :: Verify magic
    if magic != MAGIC {
        return {"error": "Not a valid .kcrypt file (bad magic: " + magic + ")"};
    }

    let meta = json.loads(meta_json);

    return {
        "metadata": meta,
        "encrypted": encrypted,
        "total_size": len(raw),
    };
}

:: Decrypt a .kcrypt file and optionally save the output.
:: @param filepath - path to .kcrypt file
:: @param key      - decryption key
:: @param save     - if true, write decrypted file to disk (default: true)
func decrypt_file(filepath, key, save) {
    import fileio;

    if save == none { save = true; }

    let result = read_kcrypt_file(filepath);
    if "error" in result {
        print("Error: " + result["error"]);
        return "";
    }

    let meta = result.metadata;
    let encrypted = result.encrypted;

    :: Decrypt
    let decrypted = decrypt(encrypted, key);

    :: Optionally save to disk
    if save {
        let out_path = filepath;
        if len(filepath) > len(DEFAULT_EXTENSION) and filepath[len(filepath) - len(DEFAULT_EXTENSION):] == DEFAULT_EXTENSION {
            out_path = filepath[0:len(filepath) - len(DEFAULT_EXTENSION)];
        }
        fileio.write_text(out_path + ".dec", decrypted);
    }

    return decrypted;
}

:: ========================================================================
:: HEX DUMP UTILITIES
:: ========================================================================

:: Generate a hex dump string of binary data.
:: Returns a list of lines: "00000000  41 42 43 44  |ABCD|"
func hexdump(data, title) {
    let lines = [];

    if title != none and title != "" {
        lines.append("");
        lines.append("== " + title + " ==");
        lines.append("");
    }

    let hex_chars = "0123456789abcdef";

    :: Process 16 bytes at a time
    let i = 0;
    let data_len = len(data);
    while i < data_len {
        let chunk = data[i : i + 16];
        let chunk_len = len(chunk);

        :: Offset
        let offset = "";
        let o = i;
        for _ in 0..8 {
            let idx = o % 16;
            offset = hex_chars.substring(idx, idx + 1) + offset;
            o = o // 16;
        }

        :: Hex part
        let hex_part = "";
        for j in 0..16 {
            if j < chunk_len {
                let byte = chunk.charCodeAt(j);
                let hi = hex_chars.substring(byte // 16, byte // 16 + 1);
                let lo = hex_chars.substring(byte % 16, byte % 16 + 1);
                if j > 0 { hex_part = hex_part + " "; }
                hex_part = hex_part + hi + lo;
            } else {
                if j > 0 { hex_part = hex_part + " "; }
                hex_part = hex_part + "  ";
            }
            :: Add separator at byte 8
            if j == 7 {
                hex_part = hex_part + " ";
            }
        }

        :: ASCII part
        let ascii_part = "";
        for j in 0..chunk_len {
            let byte = chunk.charCodeAt(j);
            if byte >= 32 and byte < 127 {
                ascii_part = ascii_part + chr(byte);
            } else {
                ascii_part = ascii_part + ".";
            }
        }

        lines.append(offset + "  " + hex_part + "  |" + ascii_part + "|");
        i = i + 16;
    }

    return lines;
}

:: Print a hex dump with colors (requires colors module).
func hexdump_color(data, title) {
    import colors;

    :: Get raw lines without title (hexdump adds title to lines)
    let lines = hexdump(data, "");

    if title != none and title != "" {
        println(colors.bold + colors.cyan + "== " + title + " ==" + colors.reset);
        println("");
    }

    for line in lines {
        :: Color the offset (dim)
        let offset_end = 8;
        let hex_start = 10;
        let first_pipe = -1;

        :: Find the FIRST pipe position for ASCII part
        let k = 0;
        while k < len(line) {
            if line[k] == "|" and first_pipe == -1 {
                first_pipe = k;
            }
            k = k + 1;
        }

        if first_pipe >= 0 {
            :: Find the LAST pipe position
            let last_pipe = len(line) - 1;
            let ascii_part = line.substring(first_pipe + 1, last_pipe);
            let hex_part = line.substring(hex_start, first_pipe);
            let offset_part = line.substring(0, offset_end);

            :: Highlight confidential/subject/status lines in ASCII
            let ascii_lower = lower(ascii_part);
            let ascii_colored = ascii_part;

            if ascii_part != "" {
                :: Color based on content
                if ascii_part != "" {
                    ascii_colored = colors.green + ascii_part + colors.reset;
                }
            }

            println(
                colors.dim + offset_part + colors.reset +
                "  " + hex_part +
                "  |" + ascii_colored + "|"
            );
        } else {
            println(line);
        }
    }
}

:: ========================================================================
:: DISPLAY / INFO
:: ========================================================================

:: Print info about a .kcrypt file (metadata only, no decryption).
func info(filepath) {
    import json;

    let result = read_kcrypt_file(filepath);
    if "error" in result {
        print("Error: " + result["error"]);
        return;
    }

    let meta = result.metadata;
    let total = result.total_size;

    println("== kcrypt file info ==");
    println("  File:            " + filepath);
    println("  Total size:      " + str(total) + " bytes");
    println("  Original size:   " + str(meta.original_size) + " bytes");
    println("  Encrypted size:  " + str(meta.encrypted_size) + " bytes");
    println("  Title:           " + meta.title);
    println("  Subject:         " + meta.subject);
    println("  Key ID:          " + meta.key_id);
    println("  Status:          " + meta.status);
    println("  Timestamp:       " + meta.timestamp);
    println("  Tool:            " + meta.tool);
    println("  Original file:   " + meta.original_filename);
}

:: ========================================================================
:: EXPORTS
:: ========================================================================

export {
    :: Primitives
    encrypt,
    decrypt,
    derive_key,
    random_key,

    :: Password hashing (Argon2id)
    hash_password,
    verify_password,

    :: Password convenience
    encrypt_with_password,
    decrypt_with_password,

    :: File operations
    encrypt_file,
    decrypt_file,
    read_kcrypt_file,

    :: Metadata
    build_metadata,

    :: Hex dump
    hexdump,
    hexdump_color,

    :: Info
    info,

    :: Constants
    DEFAULT_EXTENSION,
    MAGIC,
};
