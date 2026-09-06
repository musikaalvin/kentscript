MODULE_TYPE = "postexploit"

import zipfile
import threading
import time
import os
import queue
from collections import OrderedDict

class ModuleClass:
    def __init__(self):
        self.info = {
            'Name': 'Zip Password Cracker',
            'Description': 'Multi-threaded brute force attack on password-protected ZIP archives',
            'Author': 'KentScript',
            'Rank': 'normal',
            'Platform': 'Windows/Linux/macOS',
            'Date Released': '2025-03-24',
            'Note': 'For legitimate password recovery only. Always ensure you have permission.',
            'Options': OrderedDict([
                ('ZIP_FILE', ('', True, 'Path to password-protected ZIP file')),
                ('WORDLIST', ('', True, 'Path to password wordlist file')),
                ('THREADS', ('4', False, 'Number of concurrent threads (1-16)')),
                ('TIMEOUT', ('300', False, 'Maximum time to run in seconds')),
                ('OUTPUT_DIR', ('extracted', False, 'Directory to extract files to if successful')),
                ('VERBOSE', ('false', False, 'Show each password attempt (true/false)'))
            ])
        }
        self.found_password = None
        self.tried_passwords = 0
        self.running = False
        self.password_queue = queue.Queue()
        self.lock = threading.Lock()
    
    def logo(self):
        """Display module banner"""
        banner = """
╔══════════════════════════════════════════════╗
║            ZIP Password Cracker              ║
║         Multi-threaded Brute Force           ║
╚══════════════════════════════════════════════╝
        """
        print(banner)
    
    def help(self):
        """Display usage information"""
        help_text = """
Usage:
  set ZIP_FILE /path/to/encrypted.zip
  set WORDLIST /path/to/passwords.txt
  set THREADS 8                    (optional, default: 4)
  set TIMEOUT 600                  (optional, default: 300 seconds)
  set OUTPUT_DIR extracted_files   (optional, default: 'extracted')
  set VERBOSE true                 (optional, show attempts)
  run

Example:
  set ZIP_FILE confidential.zip
  set WORDLIST /usr/share/wordlists/rockyou.txt
  set THREADS 8
  run

Features:
  - Multi-threaded for speed
  - Real-time progress display
  - Automatic extraction on success
  - Configurable timeout
  - Resume capability (planned)
        """
        print(help_text)
    
    def test_zip_file(self, zip_path):
        """Test if file is a valid ZIP and encrypted"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Check if any file in archive is encrypted
                for file_info in zip_ref.infolist():
                    if file_info.flag_bits & 0x1:
                        return True, "Encrypted ZIP detected"
                return False, "ZIP file is not password protected"
        except zipfile.BadZipFile:
            return False, "Not a valid ZIP file"
        except Exception as e:
            return False, f"Error testing ZIP: {str(e)}"
    
    def try_password(self, zip_path, password, verbose=False):
        """Try to extract a test file with given password"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Try to read the first file in archive
                file_list = zip_ref.namelist()
                if not file_list:
                    return False
                
                # Try to read a small chunk from first file
                test_file = file_list[0]
                with zip_ref.open(test_file, pwd=password.encode()) as test_stream:
                    test_stream.read(1)  # Just read 1 byte to test
                
                if verbose:
                    print(f"[*] Testing: {password}")
                return True
        except (RuntimeError, zipfile.BadZipFile, Exception) as e:
            # Specifically ignore password errors, re-raise others
            if "password" not in str(e).lower() and "decryption" not in str(e).lower():
                if verbose:
                    print(f"[!] Error with password '{password}': {str(e)[:50]}")
            return False
    
    def worker_thread(self, zip_path, result_event, verbose=False):
        """Worker thread function for trying passwords"""
        while self.running and not result_event.is_set():
            try:
                password = self.password_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            with self.lock:
                self.tried_passwords += 1
            
            if self.try_password(zip_path, password, verbose):
                self.found_password = password
                result_event.set()
                break
            
            self.password_queue.task_done()
    
    def load_wordlist(self, wordlist_path, max_passwords=1000000):
        """Load passwords from wordlist file with progress"""
        passwords = []
        try:
            file_size = os.path.getsize(wordlist_path)
            print(f"[*] Wordlist size: {file_size:,} bytes")
            
            # Try to estimate number of lines
            with open(wordlist_path, 'rb') as f:
                # Sample first 1MB to estimate
                sample = f.read(min(1024*1024, file_size))
                line_count_estimate = sample.count(b'\n') * (file_size / len(sample))
                print(f"[*] Estimated passwords: {int(line_count_estimate):,}")
            
            # Load passwords
            print(f"[*] Loading wordlist...")
            loaded = 0
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    password = line.strip()
                    if password and len(password) <= 100:  # Reasonable length limit
                        passwords.append(password)
                        loaded += 1
                        if loaded >= max_passwords:
                            print(f"[!] Limiting to first {max_passwords:,} passwords")
                            break
            
            print(f"[+] Loaded {len(passwords):,} passwords")
            return passwords
            
        except MemoryError:
            print(f"[-] Wordlist too large! Try a smaller wordlist")
            return []
        except Exception as e:
            print(f"[-] Error loading wordlist: {e}")
            return []
    
    def display_progress(self, start_time, total_passwords, interval=5):
        """Display progress while cracking"""
        last_display = time.time() - interval  # Force immediate first display
        
        while self.running and not self.found_password:
            current_time = time.time()
            if current_time - last_display >= interval:
                elapsed = current_time - start_time
                tried = self.tried_passwords
                
                if tried > 0 and elapsed > 0:
                    speed = tried / elapsed
                    remaining = (total_passwords - tried) / speed if speed > 0 else 0
                    percent = (tried / total_passwords * 100) if total_passwords > 0 else 0
                    
                    print(f"\r[*] Progress: {tried:,}/{total_passwords:,} ({percent:.1f}%) | "
                          f"Speed: {speed:.1f}/sec | "
                          f"Elapsed: {elapsed:.0f}s | "
                          f"ETA: {remaining:.0f}s", end='', flush=True)
                
                last_display = current_time
            
            time.sleep(0.1)
        
        print()  # New line after progress
    
    def execute(self):
        """Execute the ZIP password brute force attack"""
        # Get configuration
        zip_path = self.info['Options']['ZIP_FILE'][0]
        wordlist_path = self.info['Options']['WORDLIST'][0]
        num_threads = int(self.info['Options']['THREADS'][0])
        timeout = int(self.info['Options']['TIMEOUT'][0])
        output_dir = self.info['Options']['OUTPUT_DIR'][0]
        verbose = self.info['Options']['VERBOSE'][0].lower() == 'true'
        
        # Validate inputs
        if not zip_path or not wordlist_path:
            return "[-] Error: ZIP_FILE and WORDLIST must be set!"
        
        if not os.path.exists(zip_path):
            return f"[-] Error: ZIP file not found: {zip_path}"
        
        if not os.path.exists(wordlist_path):
            return f"[-] Error: Wordlist file not found: {wordlist_path}"
        
        # Validate thread count
        if num_threads < 1 or num_threads > 16:
            return "[-] Error: THREADS must be between 1 and 16"
        
        # Show banner
        self.logo()
        
        # Test ZIP file
        print(f"[*] Testing ZIP file: {zip_path}")
        is_encrypted, message = self.test_zip_file(zip_path)
        if not is_encrypted:
            return f"[-] {message}"
        print(f"[+] {message}")
        
        # Load wordlist
        passwords = self.load_wordlist(wordlist_path)
        if not passwords:
            return "[-] No valid passwords loaded from wordlist"
        
        # Initialize
        self.found_password = None
        self.tried_passwords = 0
        self.running = True
        
        # Fill queue with passwords
        for password in passwords:
            self.password_queue.put(password)
        
        total_passwords = len(passwords)
        
        # Display attack info
        print(f"\n[*] Starting brute force attack")
        print(f"[*] Target: {os.path.basename(zip_path)}")
        print(f"[*] Total passwords: {total_passwords:,}")
        print(f"[*] Threads: {num_threads}")
        print(f"[*] Timeout: {timeout} seconds")
        print(f"[*] Verbose: {verbose}")
        print("-" * 50)
        
        # Create event to signal completion
        result_event = threading.Event()
        
        # Start worker threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(
                target=self.worker_thread,
                args=(zip_path, result_event, verbose),
                name=f"Worker-{i+1}"
            )
            thread.daemon = True
            threads.append(thread)
            thread.start()
        
        # Start progress display thread
        start_time = time.time()
        progress_thread = threading.Thread(
            target=self.display_progress,
            args=(start_time, total_passwords)
        )
        progress_thread.daemon = True
        progress_thread.start()
        
        # Wait for result or timeout
        try:
            result_event.wait(timeout)
        except KeyboardInterrupt:
            print("\n\n[!] Interrupted by user")
            self.running = False
            return "[*] Attack interrupted"
        
        # Stop all threads
        self.running = False
        
        # Wait for threads to finish
        for thread in threads:
            thread.join(timeout=1)
        
        progress_thread.join(timeout=1)
        
        # Calculate statistics
        elapsed_time = time.time() - start_time
        speed = self.tried_passwords / elapsed_time if elapsed_time > 0 else 0
        
        # Prepare results
        result = []
        result.append("\n" + "=" * 50)
        
        if self.found_password:
            result.append("[+] PASSWORD CRACKED SUCCESSFULLY!")
            result.append(f"[+] Password: \033[92m{self.found_password}\033[0m")
            
            # Try to extract files
            try:
                os.makedirs(output_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(path=output_dir, pwd=self.found_password.encode())
                
                # List extracted files
                extracted_files = os.listdir(output_dir)
                result.append(f"[+] Extracted {len(extracted_files)} files to: {output_dir}/")
                
                if len(extracted_files) <= 10:  # Don't list too many files
                    for file in extracted_files[:10]:
                        result.append(f"    - {file}")
                    if len(extracted_files) > 10:
                        result.append(f"    ... and {len(extracted_files) - 10} more")
            except Exception as e:
                result.append(f"[!] Could not extract files: {e}")
        else:
            result.append("[-] PASSWORD NOT FOUND")
            if elapsed_time >= timeout:
                result.append("[-] Timeout reached before completing wordlist")
        
        # Statistics
        result.append("\n[+] Statistics:")
        result.append(f"    Passwords tried: {self.tried_passwords:,}/{total_passwords:,}")
        result.append(f"    Time elapsed: {elapsed_time:.2f} seconds")
        result.append(f"    Speed: {speed:.1f} passwords/second")
        
        if self.tried_passwords < total_passwords and not self.found_password:
            percent_complete = (self.tried_passwords / total_passwords) * 100
            result.append(f"    Progress: {percent_complete:.1f}% complete")
            result.append(f"    Remaining: {total_passwords - self.tried_passwords:,} passwords")
        
        result.append("\n[+] Recommendations:")
        if not self.found_password:
            result.append("    1. Try a larger/more targeted wordlist")
            result.append("    2. Increase timeout value")
            result.append("    3. Use password mutation rules (planned feature)")
        
        return "\n".join(result)

# For standalone testing
if __name__ == "__main__":
    module = ModuleClass()
    
    # Test configuration
    test_config = {
        'ZIP_FILE': 'test.zip',  # Change to a real test file
        'WORDLIST': 'passwords.txt',  # Create a small test wordlist
        'THREADS': '2',
        'TIMEOUT': '10',
        'OUTPUT_DIR': 'test_extracted',
        'VERBOSE': 'true'
    }
    
    # Update module options
    for key, value in test_config.items():
        if key in module.info['Options']:
            module.info['Options'][key] = (value, module.info['Options'][key][1], module.info['Options'][key][2])
    
    print("Test Mode - ZIP Password Cracker")
    print("Create a test.zip with password 'test123' and passwords.txt with that password")
    print("Or use with real files in your pyMetasploit framework")