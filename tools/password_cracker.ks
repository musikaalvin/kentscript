:: Password Cracker - Brute force MD5 hashes
:: Usage: python3 main.py run password_cracker.ks

func crack_password(target_hash, wordlist) {
    print(f"[*] Cracking hash: {target_hash}");
    print(f"[*] Using wordlist: {wordlist}\n");
    
    let attempts = 0;
    let found = false;
    
    :: Read wordlist
    if system_file_exists(wordlist) {
        let content = system_file_read_text(wordlist);
        let words = content.split("\n");
        
        for word in words {
            attempts = attempts + 1;
            let hash = system_crypto_md5(word);
            
            if hash == target_hash {
                print(f"[+] PASSWORD FOUND: {word}");
                print(f"[+] Attempts: {attempts}");
                found = true;
                break;
            }
            
            if attempts % 1000 == 0 {
                print(f"[*] Tried {attempts} passwords...");
            }
        }
    } else {
        print(f"[-] Wordlist not found: {wordlist}");
        return;
    }
    
    if !found {
        print(f"[-] Password not found after {attempts} attempts");
    }
}

:: Create sample wordlist
let wordlist = "/tmp/wordlist.txt";
system_file_write_text(wordlist, "password\n123456\nadmin\nletmein\nwelcome\nsecret\n");

:: Example: crack MD5 hash of "secret"
let target = "5ebe2294ecd0e0f08eab7690d2a6ee69";
crack_password(target, wordlist);

:: Cleanup
system_file_remove(wordlist);
