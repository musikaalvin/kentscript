:: encoding - Encoding and decoding utilities
:: Base64, hex, URL encoding, etc.

:: ─── Base64 ─────────────────────────────────────────────────────────────────

const BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

func b64encode(data) {
    let result = "";
    let i = 0;
    
    while i < data.length {
        let b1 = data[i];
        let b2 = i + 1 < data.length ? data[i + 1] : 0;
        let b3 = i + 2 < data.length ? data[i + 2] : 0;
        
        let n = (b1 << 16) | (b2 << 8) | b3;
        
        result = result + BASE64_CHARS[(n >> 18) & 63];
        result = result + BASE64_CHARS[(n >> 12) & 63];
        result = result + (i + 1 < data.length ? BASE64_CHARS[(n >> 6) & 63] : "=");
        result = result + (i + 2 < data.length ? BASE64_CHARS[n & 63] : "=");
        
        i = i + 3;
    }
    
    return result;
}

func b64decode(s) {
    let result = [];
    let i = 0;
    
    while i < s.length {
        let c1 = BASE64_CHARS.indexOf(s[i]);
        let c2 = BASE64_CHARS.indexOf(s[i + 1]);
        let c3 = s[i + 2] != "=" ? BASE64_CHARS.indexOf(s[i + 2]) : 0;
        let c4 = s[i + 3] != "=" ? BASE64_CHARS.indexOf(s[i + 3]) : 0;
        
        let n = (c1 << 18) | (c2 << 12) | (c3 << 6) | c4;
        
        result.push((n >> 16) & 255);
        if s[i + 2] != "=" {
            result.push((n >> 8) & 255);
        }
        if s[i + 3] != "=" {
            result.push(n & 255);
        }
        
        i = i + 4;
    }
    
    return result;
}

:: ─── Hex Encoding ──────────────────────────────────────────────────────────

func hexencode(data) {
    let result = "";
    for byte in data {
        let hex = byte.toString(16);
        if hex.length == 1 {
            hex = "0" + hex;
        }
        result = result + hex;
    }
    return result;
}

func hexdecode(s) {
    let result = [];
    for i in range(0, s.length, 2) {
        let hex = s.substring(i, i + 2);
        result.push(parseInt(hex, 16));
    }
    return result;
}

:: ─── URL Encoding ──────────────────────────────────────────────────────────

func urlencode(s) {
    let result = "";
    for i in 0..s.length {
        let char = s[i];
        let code = s.charCodeAt(i);
        
        if (code >= 48 && code <= 57) || (code >= 65 && code <= 90) || 
           (code >= 97 && code <= 122) || char == "-" || char == "_" || 
           char == "." || char == "~" {
            result = result + char;
        } else {
            result = result + "%" + code.toString(16).toUpperCase().padStart(2, "0");
        }
    }
    return result;
}

func urldecode(s) {
    let result = "";
    let i = 0;
    
    while i < s.length {
        if s[i] == "%" {
            let hex = s.substring(i + 1, i + 3);
            result = result + String.fromCharCode(parseInt(hex, 16));
            i = i + 3;
        } else if s[i] == "+" {
            result = result + " ";
            i = i + 1;
        } else {
            result = result + s[i];
            i = i + 1;
        }
    }
    
    return result;
}

:: ─── HTML Encoding ─────────────────────────────────────────────────────────

func html_escape(s) {
    return s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;");
}

func html_unescape(s) {
    return s.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#x27;", "'");
}

:: ─── Binary/ASCII ──────────────────────────────────────────────────────────

func bin2hex(data) {
    return hexencode(data);
}

func hex2bin(s) {
    return hexdecode(s);
}

func ascii_encode(s) {
    let result = [];
    for i in 0..s.length {
        result.push(s.charCodeAt(i));
    }
    return result;
}

func ascii_decode(data) {
    let result = "";
    for byte in data {
        result = result + String.fromCharCode(byte);
    }
    return result;
}

:: ─── UTF-8 ─────────────────────────────────────────────────────────────────

func utf8_encode(s) {
    let result = [];
    for i in 0..s.length {
        let code = s.charCodeAt(i);
        
        if code < 128 {
            result.push(code);
        } else if code < 2048 {
            result.push(192 | (code >> 6));
            result.push(128 | (code & 63));
        } else if code < 65536 {
            result.push(224 | (code >> 12));
            result.push(128 | ((code >> 6) & 63));
            result.push(128 | (code & 63));
        } else {
            result.push(240 | (code >> 18));
            result.push(128 | ((code >> 12) & 63));
            result.push(128 | ((code >> 6) & 63));
            result.push(128 | (code & 63));
        }
    }
    return result;
}

func utf8_decode(data) {
    let result = "";
    let i = 0;
    
    while i < data.length {
        let byte = data[i];
        
        if byte < 128 {
            result = result + String.fromCharCode(byte);
            i = i + 1;
        } else if byte < 224 {
            let code = ((byte & 31) << 6) | (data[i + 1] & 63);
            result = result + String.fromCharCode(code);
            i = i + 2;
        } else if byte < 240 {
            let code = ((byte & 15) << 12) | ((data[i + 1] & 63) << 6) | (data[i + 2] & 63);
            result = result + String.fromCharCode(code);
            i = i + 3;
        } else {
            let code = ((byte & 7) << 18) | ((data[i + 1] & 63) << 12) | 
                      ((data[i + 2] & 63) << 6) | (data[i + 3] & 63);
            result = result + String.fromCharCode(code);
            i = i + 4;
        }
    }
    
    return result;
}

:: ─── ROT13 ─────────────────────────────────────────────────────────────────

func rot13(s) {
    let result = "";
    for i in 0..s.length {
        let code = s.charCodeAt(i);
        
        if code >= 65 && code <= 90 {
            result = result + String.fromCharCode(((code - 65 + 13) % 26) + 65);
        } else if code >= 97 && code <= 122 {
            result = result + String.fromCharCode(((code - 97 + 13) % 26) + 97);
        } else {
            result = result + s[i];
        }
    }
    return result;
}

:: ─── Quoted-Printable ──────────────────────────────────────────────────────

func quopri_encode(data) {
    let result = "";
    let line_len = 0;
    
    for byte in data {
        if byte == 10 {
            result = result + "\n";
            line_len = 0;
        } else if byte == 13 {
            continue;
        } else if (byte >= 33 && byte <= 126 && byte != 61) {
            result = result + String.fromCharCode(byte);
            line_len = line_len + 1;
        } else {
            let hex = "=" + byte.toString(16).toUpperCase().padStart(2, "0");
            result = result + hex;
            line_len = line_len + 3;
        }
        
        if line_len >= 75 {
            result = result + "=\n";
            line_len = 0;
        }
    }
    
    return result;
}

export {
    b64encode, b64decode,
    hexencode, hexdecode,
    urlencode, urldecode,
    html_escape, html_unescape,
    bin2hex, hex2bin,
    ascii_encode, ascii_decode,
    utf8_encode, utf8_decode,
    rot13, quopri_encode
};
