MODULE_TYPE = "cracker"
from collections import OrderedDict
import hashlib
import os
import sys
import time
import threading
import itertools
import string
from typing import List, Dict, Tuple, Optional
import json

class ModuleClass:
    def __init__(self):
        self.info = {
            'Name': 'AdvancedHashCracker',
            'Rank': 'Excellent',
            'Platform': 'Windows/Linux/MacOS',
            'Architectures': 'x86/x64 (GPU acceleration with hashcat)',
            'Description': 'Advanced hash cracking with multiple algorithms, rules, masks, and hashcat integration',
            'Version': '2.0',
            'Author': 'KentScript',
            'Options': OrderedDict([
                ('MODE', ('dictionary', True, 'Mode: dictionary/mask/hybrid/bruteforce/rainbow')),
                ('HASH', ('', True, 'Hash to crack (or first hash if file)')),
                ('HASH_TYPE', ('md5', True, 'Hash type: md5/sha1/sha256/ntlm/bcrypt/etc')),
                ('WORDLIST', ('/usr/share/wordlists/rockyou.txt', False, 'Wordlist path')),
                ('RULES', ('', False, 'Rules file for word mangling')),
                ('MASK', ('?l?l?l?l?l?l', False, 'Mask pattern (?l=lower, ?u=upper, ?d=digit, ?s=special)')),
                ('MIN_LEN', ('1', False, 'Minimum password length')),
                ('MAX_LEN', ('8', False, 'Maximum password length')),
                ('CHARSET', ('lower', False, 'Charset: lower/upper/digit/alnum/all')),
                ('THREADS', ('4', False, 'Number of threads')),
                ('OUTPUT', ('', False, 'Save results to file')),
                ('USE_HASHCAT', ('false', False, 'Use hashcat if available (true/false)')),
                ('HASH_FILE', ('', False, 'File containing multiple hashes')),
            ])
        }
        self.found_passwords = {}
        self.attempts = 0
        self.start_time = 0
        self.lock = threading.Lock()
    
    def help(self):
        return """
Advanced Hash Cracker
=====================
Cracks hashes using multiple methods and algorithms.

Required:
  set HASH <hash_value>
  set HASH_TYPE <algorithm>

Modes:
  dictionary   - Use wordlist (fastest)
  mask         - Use mask pattern (e.g., ?l?l?d?d?d)
  bruteforce   - Brute-force all combinations
  hybrid       - Dictionary + mask/bruteforce
  rainbow      - Use precomputed rainbow tables

Mask patterns:
  ?l = lowercase letters [a-z]
  ?u = uppercase letters [A-Z]
  ?d = digits [0-9]
  ?s = special characters [!@#$%^&*()]
  ?a = all printable ASCII
  ?h = hex characters [0-9a-f]
  ?H = hex characters [0-9A-F]

Examples:
  # Dictionary attack on MD5
  set HASH 5f4dcc3b5aa765d61d8327deb882cf99
  set HASH_TYPE md5
  set WORDLIST /usr/share/wordlists/rockyou.txt
  set MODE dictionary
  run
  
  # Mask attack on SHA256
  set HASH a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3
  set HASH_TYPE sha256
  set MASK ?l?l?l?d?d?d
  set MODE mask
  run
  
  # Brute-force NTLM hash
  set HASH 209c6174da490caeb422f3fa5a7ae634
  set HASH_TYPE ntlm
  set CHARSET alnum
  set MIN_LEN 4
  set MAX_LEN 6
  set THREADS 8
  set MODE bruteforce
  run
  
  # Use hashcat if available
  set USE_HASHCAT true
  set OUTPUT /tmp/cracked.txt
  run
"""
    
    def _hash_functions(self) -> Dict:
        """Map hash types to hashing functions"""
        return {
            'md5': lambda x: hashlib.md5(x.encode()).hexdigest(),
            'sha1': lambda x: hashlib.sha1(x.encode()).hexdigest(),
            'sha256': lambda x: hashlib.sha256(x.encode()).hexdigest(),
            'sha512': lambda x: hashlib.sha512(x.encode()).hexdigest(),
            'ntlm': lambda x: hashlib.new('md4', x.encode('utf-16le')).hexdigest(),
            'md4': lambda x: hashlib.new('md4', x.encode()).hexdigest(),
        }
    
    def _get_charset(self, charset_name: str) -> str:
        """Get character set based on name"""
        charsets = {
            'lower': string.ascii_lowercase,
            'upper': string.ascii_uppercase,
            'digit': string.digits,
            'alnum': string.ascii_letters + string.digits,
            'all': string.ascii_letters + string.digits + string.punctuation,
            'hex': '0123456789abcdef',
            'hex_upper': '0123456789ABCDEF',
        }
        return charsets.get(charset_name.lower(), string.ascii_lowercase)
    
    def _expand_mask(self, mask: str) -> str:
        """Expand mask pattern to character set"""
        mask_map = {
            '?l': string.ascii_lowercase,
            '?u': string.ascii_uppercase,
            '?d': string.digits,
            '?s': string.punctuation,
            '?a': string.ascii_letters + string.digits + string.punctuation,
            '?h': '0123456789abcdef',
            '?H': '0123456789ABCDEF',
        }
        
        result = []
        i = 0
        while i < len(mask):
            if mask[i] == '?' and i + 1 < len(mask):
                char_type = mask[i:i+2]
                if char_type in mask_map:
                    result.append(mask_map[char_type])
                    i += 2
                    continue
            result.append(mask[i])
            i += 1
        
        return ''.join(result)
    
    def _check_hashcat(self) -> bool:
        """Check if hashcat is available"""
        try:
            import subprocess
            result = subprocess.run(['hashcat', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def _run_hashcat(self, mode: str, target_hash: str, hash_type: str, 
                    wordlist: str = '', mask: str = '', rules: str = '',
                    output_file: str = '') -> str:
        """Run hashcat command"""
        try:
            import subprocess
            
            # Map hash types to hashcat mode numbers
            hashcat_modes = {
                'md5': '0',
                'sha1': '100',
                'sha256': '1400',
                'sha512': '1700',
                'ntlm': '1000',
                'md4': '900',
            }
            
            mode_num = hashcat_modes.get(hash_type.lower(), '0')
            
            # Build command
            cmd = ['hashcat', '-m', mode_num, '--potfile-disable']
            
            if output_file:
                cmd.extend(['--outfile', output_file])
            
            if mode == 'dictionary':
                cmd.extend(['-a', '0', target_hash, wordlist])
                if rules and os.path.exists(rules):
                    cmd.extend(['-r', rules])
            
            elif mode == 'mask':
                cmd.extend(['-a', '3', target_hash, mask])
            
            elif mode == 'bruteforce':
                # Convert charset to mask
                charset = self.info['Options']['CHARSET'][0]
                min_len = int(self.info['Options']['MIN_LEN'][0])
                max_len = int(self.info['Options']['MAX_LEN'][0])
                
                for length in range(min_len, max_len + 1):
                    mask_pattern = '?a' * length
                    cmd = ['hashcat', '-m', mode_num, '-a', '3', target_hash, mask_pattern]
                    
                    print(f"[*] Trying length {length}...")
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        return f"[+] Hashcat found password (length {length})"
            
            elif mode == 'hybrid':
                if wordlist and mask:
                    cmd.extend(['-a', '6', target_hash, wordlist, mask])
            
            # Run hashcat
            print(f"[*] Running hashcat command...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse output for found password
                for line in result.stdout.split('\n'):
                    if target_hash in line and ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            password = parts[-1]
                            return f"[+] Hashcat cracked: {password}"
            
            return f"[*] Hashcat completed. Check output: {output_file if output_file else 'screen'}"
            
        except Exception as e:
            return f"[-] Hashcat error: {str(e)}"
    
    def _dictionary_attack(self, target_hash: str, hash_func, wordlist_path: str, 
                          rules_path: str = '', threads: int = 4) -> Optional[str]:
        """Dictionary attack"""
        if not os.path.exists(wordlist_path):
            return None
        
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                wordlist = [line.strip() for line in f]
            
            # Apply rules if specified
            if rules_path and os.path.exists(rules_path):
                wordlist = self._apply_rules(wordlist, rules_path)
            
            # Multi-threaded cracking
            chunk_size = max(1, len(wordlist) // threads)
            word_chunks = [wordlist[i:i + chunk_size] for i in range(0, len(wordlist), chunk_size)]
            
            found_password = [None]
            
            def worker(words):
                for word in words:
                    with self.lock:
                        self.attempts += 1
                    
                    if hash_func(word) == target_hash:
                        with self.lock:
                            found_password[0] = word
                        return
            
            # Start worker threads
            thread_list = []
            for chunk in word_chunks:
                t = threading.Thread(target=worker, args=(chunk,))
                t.start()
                thread_list.append(t)
            
            # Wait for completion or found password
            while found_password[0] is None and any(t.is_alive() for t in thread_list):
                time.sleep(0.1)
                # Show progress
                if self.attempts % 10000 == 0:
                    print(f"[*] Attempts: {self.attempts}")
            
            # Terminate threads
            for t in thread_list:
                if t.is_alive():
                    t.join(timeout=0.1)
            
            return found_password[0]
            
        except Exception as e:
            print(f"[-] Dictionary attack error: {e}")
            return None
    
    def _mask_attack(self, target_hash: str, hash_func, mask: str) -> Optional[str]:
        """Mask/pattern attack"""
        try:
            charset = self._expand_mask(mask)
            
            # Estimate total combinations
            total = len(charset) ** len(mask.replace('?', ''))
            if total > 10000000:  # 10 million
                print(f"[!] Warning: {total:,} combinations may take a while")
            
            # Generate combinations
            for combo in itertools.product(charset, repeat=len(mask.replace('?', ''))):
                password = ''.join(combo)
                self.attempts += 1
                
                if hash_func(password) == target_hash:
                    return password
                
                # Progress
                if self.attempts % 10000 == 0:
                    print(f"[*] Attempts: {self.attempts}")
            
            return None
            
        except Exception as e:
            print(f"[-] Mask attack error: {e}")
            return None
    
    def _bruteforce_attack(self, target_hash: str, hash_func, min_len: int, 
                          max_len: int, charset: str) -> Optional[str]:
        """Brute-force attack"""
        try:
            for length in range(min_len, max_len + 1):
                print(f"[*] Trying length {length}...")
                
                for combo in itertools.product(charset, repeat=length):
                    password = ''.join(combo)
                    self.attempts += 1
                    
                    if hash_func(password) == target_hash:
                        return password
                    
                    # Progress
                    if self.attempts % 10000 == 0:
                        print(f"[*] Attempts: {self.attempts}")
            
            return None
            
        except Exception as e:
            print(f"[-] Brute-force error: {e}")
            return None
    
    def _apply_rules(self, wordlist: List[str], rules_path: str) -> List[str]:
        """Apply rule transformations to wordlist"""
        rules = []
        try:
            with open(rules_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        rules.append(line)
            
            # Apply simple rules
            enhanced = []
            for word in wordlist:
                enhanced.append(word)
                for rule in rules[:10]:  # Limit rules for performance
                    if rule == 'l':  # Lowercase
                        enhanced.append(word.lower())
                    elif rule == 'u':  # Uppercase
                        enhanced.append(word.upper())
                    elif rule == 'c':  # Capitalize
                        enhanced.append(word.capitalize())
                    elif rule.startswith('$'):  # Append character
                        enhanced.append(word + rule[1:])
                    elif rule.startswith('^'):  # Prepend character
                        enhanced.append(rule[1:] + word)
            
            return list(set(enhanced))  # Remove duplicates
            
        except:
            return wordlist
    
    def execute(self):
        """Main execution method"""
        try:
            # Get options
            mode = self.info['Options']['MODE'][0].lower()
            target_hash = self.info['Options']['HASH'][0].strip()
            hash_type = self.info['Options']['HASH_TYPE'][0].lower()
            wordlist = self.info['Options']['WORDLIST'][0]
            rules = self.info['Options']['RULES'][0]
            mask = self.info['Options']['MASK'][0]
            min_len = int(self.info['Options']['MIN_LEN'][0])
            max_len = int(self.info['Options']['MAX_LEN'][0])
            charset_name = self.info['Options']['CHARSET'][0]
            threads = int(self.info['Options']['THREADS'][0])
            output_file = self.info['Options']['OUTPUT'][0]
            use_hashcat = self.info['Options']['USE_HASHCAT'][0].lower() == 'true'
            hash_file = self.info['Options']['HASH_FILE'][0]
            
            # Validate hash
            if not target_hash and not hash_file:
                return "[-] No hash or hash file specified"
            
            # Get hash function
            hash_funcs = self._hash_functions()
            if hash_type not in hash_funcs:
                return f"[-] Unsupported hash type: {hash_type}. Supported: {', '.join(hash_funcs.keys())}"
            
            hash_func = hash_funcs[hash_type]
            
            # Display info
            results = []
            results.append(f"[+] Advanced Hash Cracker")
            results.append(f"[+] Target: {target_hash[:20]}..." if len(target_hash) > 20 else f"[+] Target: {target_hash}")
            results.append(f"[+] Hash type: {hash_type}")
            results.append(f"[+] Mode: {mode}")
            
            # Check hashcat if requested
            if use_hashcat and self._check_hashcat():
                results.append("[+] Hashcat detected, using for cracking...")
                hashcat_result = self._run_hashcat(mode, target_hash, hash_type, 
                                                  wordlist, mask, rules, output_file)
                return "\n".join(results) + "\n" + hashcat_result
            
            # Start timer
            self.start_time = time.time()
            self.attempts = 0
            self.found_passwords = {}
            
            # Choose attack method
            password = None
            
            if mode == 'dictionary':
                if not wordlist:
                    return "[-] Wordlist required for dictionary mode"
                
                results.append(f"[+] Wordlist: {wordlist}")
                if rules:
                    results.append(f"[+] Rules: {rules}")
                
                password = self._dictionary_attack(target_hash, hash_func, wordlist, rules, threads)
            
            elif mode == 'mask':
                if not mask:
                    return "[-] Mask required for mask mode"
                
                results.append(f"[+] Mask: {mask}")
                results.append(f"[+] Expanded: {self._expand_mask(mask)}")
                
                password = self._mask_attack(target_hash, hash_func, mask)
            
            elif mode == 'bruteforce':
                charset = self._get_charset(charset_name)
                results.append(f"[+] Charset: {charset_name} ({len(charset)} chars)")
                results.append(f"[+] Length: {min_len}-{max_len}")
                
                password = self._bruteforce_attack(target_hash, hash_func, min_len, max_len, charset)
            
            elif mode == 'hybrid':
                if not wordlist or not mask:
                    return "[-] Both wordlist and mask required for hybrid mode"
                
                # Simple hybrid: dictionary + mask suffix
                results.append(f"[+] Hybrid attack: dictionary + mask")
                password = self._hybrid_attack(target_hash, hash_func, wordlist, mask)
            
            else:
                return f"[-] Unknown mode: {mode}"
            
            # Calculate elapsed time
            elapsed = time.time() - self.start_time
            
            # Report results
            results.append(f"\n{'='*60}")
            results.append(f"[+] Crack time: {elapsed:.2f} seconds")
            results.append(f"[+] Total attempts: {self.attempts:,}")
            results.append(f"[+] Speed: {self.attempts/elapsed:,.0f} hashes/sec" if elapsed > 0 else "")
            
            if password:
                results.append(f"\n[+] CRACKED: {password}")
                self.found_passwords[target_hash] = password
                
                # Save to file if requested
                if output_file:
                    try:
                        with open(output_file, 'a') as f:
                            f.write(f"{target_hash}:{password}\n")
                        results.append(f"[+] Saved to: {output_file}")
                    except Exception as e:
                        results.append(f"[-] Failed to save: {e}")
            else:
                results.append(f"\n[-] Password not found")
            
            return "\n".join(results)
            
        except KeyboardInterrupt:
            elapsed = time.time() - self.start_time if self.start_time > 0 else 0
            return f"\n[!] Cracking interrupted after {elapsed:.1f}s\n[!] Attempts: {self.attempts:,}"
        except Exception as e:
            return f"[-] Cracking failed: {str(e)}"

# Test when run directly
if __name__ == "__main__":
    module = ModuleClass()
    print(module.execute())