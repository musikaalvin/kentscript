:: Hash Cracker Tool - MD5/SHA1/SHA256 Password Cracker
:: Usage: python3 main.py run examples/hash_cracker.ks --hash <hash> --wordlist <wordlist.txt>

import crypto;
import argparse;

let parser = system_argparse_new("KentScript Hash Cracker v1.0");
system_argparse_add_argument(parser, "--hash");
system_argparse_add_argument(parser, "--wordlist");
system_argparse_add_argument(parser, "--type");

let args = system_argparse_parse_args(parser, []);

if args.hash == none or args.wordlist == none {
    print("Usage: --hash <hash> --wordlist <wordlist.txt> [--type md5|sha1|sha256]");
    print("");
    print("Example: --hash 5f4dcc3b5aa765d61d8327deb882cf99 --wordlist passwords.txt --type md5");
    system_os_exit(1);
}

let target_hash = str(args.hash).lower();
let wordlist_file = args.wordlist;
let hash_type = "md5";

if args.type != none {
    hash_type = str(args.type).lower();
}

print(f"[*] KentScript Hash Cracker v1.0");
print(f"[*] Target Hash: {target_hash}");
print(f"[*] Hash Type: {hash_type}");
print(f"[*] Wordlist: {wordlist_file}");
print("");

:: Read wordlist
let wordlist_content = system_file_read_text(wordlist_file);
if wordlist_content == none {
    print(f"[!] Could not read wordlist: {wordlist_file}");
    system_os_exit(1);
}

let passwords = system_string_split(wordlist_content, "\n");
print(f"[*] Loaded {len(passwords)} passwords");
print("[*] Starting attack...");
print("");

let start_time = system_time_monotonic();
let checked = 0;

for password in passwords {
    if str(password).len() == 0 {
        continue;
    }
    
    let hash = "";
    
    if hash_type == "md5" {
        hash = system_crypto_md5(password);
    } elif hash_type == "sha1" {
        hash = system_crypto_sha1(password);
    } elif hash_type == "sha256" {
        hash = system_crypto_sha256(password);
    } elif hash_type == "sha512" {
        hash = system_crypto_sha512(password);
    } else {
        :: Try all types
        let md5_hash = system_crypto_md5(password);
        let sha1_hash = system_crypto_sha1(password);
        let sha256_hash = system_crypto_sha256(password);
        
        if md5_hash == target_hash {
            print(f"[+] FOUND! [{hash_type}]");
            print(f"[+] Password: {password}");
            let elapsed = system_time_monotonic() - start_time;
            print(f"[*] Time: {elapsed}s");
            system_os_exit(0);
        }
        if sha1_hash == target_hash {
            print(f"[+] FOUND! [sha1]");
            print(f"[+] Password: {password}");
            let elapsed = system_time_monotonic() - start_time;
            print(f"[*] Time: {elapsed}s");
            system_os_exit(0);
        }
        if sha256_hash == target_hash {
            print(f"[+] FOUND! [sha256]");
            print(f"[+] Password: {password}");
            let elapsed = system_time_monotonic() - start_time;
            print(f"[*] Time: {elapsed}s");
            system_os_exit(0);
        }
        
        checked = checked + 1;
        if checked % 100 == 0 {
            print(f"[*] Progress: {checked}/{len(passwords)}...");
        }
        continue;
    }
    
    hash = str(hash).lower();
    
    if hash == target_hash {
        print("");
        print(f"[+] ===== PASSWORD FOUND =====");
        print(f"[+] Hash Type: {hash_type}");
        print(f"[+] Password: {password}");
        print(f"[+] Hash: {hash}");
        let elapsed = system_time_monotonic() - start_time;
        print(f"[*] Time: {elapsed}s");
        print(f"[*] Checked: {checked + 1} passwords");
        system_os_exit(0);
    }
    
    checked = checked + 1;
    if checked % 100 == 0 {
        print(f"[*] Progress: {checked}/{len(passwords)}...");
    }
}

let elapsed = system_time_monotonic() - start_time;
print("");
print(f"[!] Password not found in wordlist");
print(f"[*] Checked: {checked} passwords");
print(f"[*] Time: {elapsed}s");
