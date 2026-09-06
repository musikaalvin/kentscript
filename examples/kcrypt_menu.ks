:: kcrypt_menu.ks - Interactive file encryption/decryption menu using kcrypt
::
:: This program demonstrates the kcrypt library by providing a menu-driven
:: interface for encrypting and decrypting files using XChaCha20-Poly1305 AEAD.
::
:: Usage: python3 kentscript.py examples/kcrypt_menu.ks

import kcrypt;
import fileio;
import colors;

func main() {
    while true {
        print_menu();
        let choice = input("Enter choice (1-5): ");

        if choice == "1" {
            encrypt_file_interactive();
        } elif choice == "2" {
            decrypt_file_interactive();
        } elif choice == "3" {
            generate_key_interactive();
        } elif choice == "4" {
            print_banner();
        } elif choice == "5" {
            print(colors.green + "Goodbye!" + colors.reset);
            break;
        } else {
            print(colors.red + "Invalid choice. Please enter 1-5." + colors.reset);
        }
        println("");
    }
}

func print_menu() {
    println(colors.bold + "=== kcrypt File Encryption Menu ===" + colors.reset);
    println("1. " + colors.green + "Encrypt" + colors.reset + " a file (.kcrypt extension)");
    println("2. " + colors.blue + "Decrypt" + colors.reset + " a .kcrypt file");
    println("3. " + colors.yellow + "Generate" + colors.reset + " a new random key");
    println("4. " + colors.cyan + "View" + colors.reset + " banner");
    println("5. " + colors.red + "Exit" + colors.reset);
}

func print_banner() {
    println(colors.bold + colors.green +
"
  __  __     _     _    ___     ___
 |  \\/  |___| |__ | |  | _ )___| _ \\
 | |\\/| / -_) '_ \\| |__| _ / -_)   /
 |_|  |\\___|_.__/|____|___\\___|_|_\\
  XChaCha20-Poly1305 AEAD Encryption
"
+ colors.reset);
}

func encrypt_file_interactive() {
    let filepath = input("Enter file path to encrypt: ");

    :: Check if file exists
    if not fileio.exists(filepath) {
        print(colors.red + "Error: File not found: " + filepath + colors.reset);
        return;
    }

    :: Read key
    let key_input = input("Enter your encryption key (or type 'gen' for new key): ");

    let key;
    if key_input == "gen" {
        key = kcrypt.random_key(32);
        let key_path = filepath + ".key";
        fileio.write_text(key_path, key);
        println(colors.green + "New key saved to: " + key_path + colors.reset);
    } else {
        key = key_input;
    }

    :: Encrypt the file (automatically appends .kcrypt extension)
    let enc_path = kcrypt.encrypt_file(filepath, key);
    println(colors.green + "File encrypted successfully!" + colors.reset);
    println("  Output: " + enc_path);
    println("  Encrypted size: " + str(len(enc_path)) + " (path length)");
}

func decrypt_file_interactive() {
    let filepath = input("Enter .kcrypt file path to decrypt: ");

    :: Check if file exists
    if not fileio.exists(filepath) {
        print(colors.red + "Error: File not found: " + filepath + colors.reset);
        return;
    }

    let key = input("Enter your decryption key: ");

    :: Attempt decryption
    :: If the key is wrong or file is corrupted, this will raise an error
    let dec_data = kcrypt.decrypt_file(filepath, key);

    if dec_data != "" {
        println(colors.green + "File decrypted successfully!" + colors.reset);
        println("  Decrypted " + str(len(dec_data)) + " bytes");

        :: Show preview
        if len(dec_data) <= 200 {
            println("  --- Content preview ---");
            println(dec_data);
            println("  --- End preview ---");
        } else {
            println("  Preview: " + dec_data[:200] + "...");
        }
    }
}

func generate_key_interactive() {
    let length_str = input("Key length in bytes (default 32): ");
    let length = 32;

    :: Try to parse length
    if length_str != "" {
        let ok = false;
        let parsed = 0;

        :: Manual check: try int conversion
        if len(length_str) > 0 {
            let i = 0;
            let is_num = true;
            while i < len(length_str) {
                let c = length_str[i];
                if c < "0" or c > "9" {
                    is_num = false;
                    break;
                }
                i = i + 1;
            }
            if is_num {
                parsed = int(length_str);
                if parsed >= 16 {
                    length = parsed;
                }
            }
        }
    }

    let key = kcrypt.random_key(length);
    println(colors.green + "Generated key: " + key + colors.reset);

    :: Offer to save
    let save = input("Save to key file? (y/n): ");
    if save == "y" or save == "Y" {
        let path = input("File path (default: key.kcrypt.key): ");
        if path == "" {
            path = "key.kcrypt.key";
        }
        fileio.write_text(path, key);
        println(colors.green + "Key saved to: " + path + colors.reset);
    }
}

:: Entry point
main();
