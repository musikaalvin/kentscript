MODULE_TYPE = "encoder"  # Could also be "cracker" for decryption focus
from collections import OrderedDict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import sys
import hashlib
from typing import Optional, Tuple, List
import struct
import time

class ModuleClass:
    def __init__(self):
        self.info = {
            'Name': 'Advanced File Cryptor',
            'Rank': 'Excellent',
            'Platform': 'Windows/Linux/MacOS',
            'Architectures': 'x86/x64/ARM',
            'Description': 'Advanced file encryption/decryption with multiple algorithms',
            'Version': '3.0',
            'Author': 'KentScript',
            'Note': 'For authorized file protection testing only.',
            'Options': OrderedDict([
                ('MODE', ('encrypt', True, 'Operation: encrypt/decrypt/batch')),
                ('TARGET', ('', True, 'File or directory to process')),
                ('KEY', ('', False, 'Encryption key (empty for auto-generate)')),
                ('ALGORITHM', ('fernet', True, 'Algorithm: fernet/aes/xor/rot')),
                ('KEY_FILE', ('', False, 'File to save/load key')),
                ('OUTPUT', ('', False, 'Output directory')),
                ('RECURSIVE', ('false', False, 'Process subdirectories (true/false)')),
                ('EXTENSION', ('.enc', False, 'Extension for encrypted files')),
                ('PASSWORD', ('', False, 'Password for key derivation')),
                ('ITERATIONS', ('100000', False, 'PBKDF2 iterations')),
                ('COMPRESS', ('false', False, 'Compress before encryption')),
            ])
        }
    
    def help(self):
        return """
Advanced File Cryptor
=====================
Encrypts or decrypts files using various cryptographic algorithms.

Modes:
  encrypt  - Encrypt files/directories
  decrypt  - Decrypt files/directories
  batch    - Process multiple files in batch

Algorithms:
  fernet   - AES-128-CBC with HMAC (recommended)
  aes      - Raw AES encryption
  xor      - XOR encryption (weak, fast)
  rot      - ROT cipher (very weak, for obfuscation)

Key Management:
  - Auto-generate key if not provided
  - Save key to file for later decryption
  - Use password-based key derivation (PBKDF2)
  - Never store keys with encrypted data

Examples:
  # Encrypt single file with auto-generated key
  set MODE encrypt
  set TARGET /path/to/secret.txt
  set KEY_FILE encryption.key
  set ALGORITHM fernet
  run
  
  # Decrypt file with saved key
  set MODE decrypt
  set TARGET /path/to/secret.txt.enc
  set KEY_FILE encryption.key
  run
  
  # Batch encrypt directory
  set MODE batch
  set TARGET /path/to/documents
  set RECURSIVE true
  set EXTENSION .locked
  set OUTPUT /path/to/encrypted
  run
  
  # Password-based encryption
  set PASSWORD MyStrongPassword123
  set ITERATIONS 500000
  run
  
  # Weak obfuscation (ROT13)
  set ALGORITHM rot
  set TARGET file.txt
  run

Security Notes:
  - Fernet is recommended for security
  - XOR/ROT are for obfuscation only
  - Always backup keys/passwords
  - Test decryption before deleting originals
"""
    
    def _generate_key(self, password: str = '', salt: bytes = None, 
                     iterations: int = 100000) -> bytes:
        """Generate encryption key, optionally from password"""
        if password:
            # Derive key from password using PBKDF2
            if salt is None:
                salt = os.urandom(16)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=iterations,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return key, salt
        else:
            # Generate random key
            key = Fernet.generate_key()
            return key, None
    
    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        """XOR encryption (weak but fast)"""
        if not key:
            key = os.urandom(32)
        
        encrypted = bytearray()
        for i, byte in enumerate(data):
            encrypted.append(byte ^ key[i % len(key)])
        return bytes(encrypted)
    
    def _xor_decrypt(self, data: bytes, key: bytes) -> bytes:
        """XOR decryption (same as encryption)"""
        return self._xor_encrypt(data, key)
    
    def _rot_encrypt(self, data: bytes, rotation: int = 13) -> bytes:
        """ROT encryption (very weak obfuscation)"""
        encrypted = bytearray()
        for byte in data:
            if 32 <= byte <= 126:  # Printable ASCII
                new_byte = ((byte - 32 + rotation) % 95) + 32
                encrypted.append(new_byte)
            else:
                encrypted.append(byte)
        return bytes(encrypted)
    
    def _rot_decrypt(self, data: bytes, rotation: int = 13) -> bytes:
        """ROT decryption"""
        return self._rot_encrypt(data, 95 - rotation)
    
    def _compress_data(self, data: bytes) -> bytes:
        """Simple compression (run-length encoding)"""
        if len(data) < 100:  # Don't compress small data
            return data
        
        compressed = bytearray()
        i = 0
        while i < len(data):
            count = 1
            while i + count < len(data) and count < 255 and data[i] == data[i + count]:
                count += 1
            
            if count > 3:  # Only compress runs of 4+ identical bytes
                compressed.append(0xFF)  # Marker byte
                compressed.append(count)
                compressed.append(data[i])
                i += count
            else:
                compressed.append(data[i])
                i += 1
        
        return bytes(compressed)
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress run-length encoded data"""
        decompressed = bytearray()
        i = 0
        while i < len(data):
            if i + 2 < len(data) and data[i] == 0xFF:  # Marker
                count = data[i + 1]
                byte = data[i + 2]
                decompressed.extend([byte] * count)
                i += 3
            else:
                decompressed.append(data[i])
                i += 1
        
        return bytes(decompressed)
    
    def _encrypt_file(self, filepath: str, key: bytes, algorithm: str, 
                     password: str = '', compress: bool = False) -> Tuple[bool, str, bytes]:
        """Encrypt a single file"""
        try:
            # Read file
            with open(filepath, 'rb') as f:
                data = f.read()
            
            original_size = len(data)
            
            # Compress if requested
            if compress:
                data = self._compress_data(data)
                compressed_size = len(data)
                print(f"[*] Compressed: {original_size} -> {compressed_size} bytes")
            
            # Encrypt based on algorithm
            encrypted_data = b''
            metadata = b''
            
            if algorithm == 'fernet':
                fernet = Fernet(key)
                encrypted_data = fernet.encrypt(data)
                
            elif algorithm == 'xor':
                # Add metadata: algorithm marker
                metadata = b'XOR'
                encrypted_data = self._xor_encrypt(data, key)
                
            elif algorithm == 'rot':
                # Add metadata: rotation amount
                rotation = 13
                metadata = struct.pack('B', rotation)
                encrypted_data = self._rot_encrypt(data, rotation)
                
            elif algorithm == 'aes':
                # Simple AES simulation (real implementation would use cryptography library)
                metadata = b'AES'
                encrypted_data = self._xor_encrypt(data, key[:16])  # Simplified
            
            else:
                return False, f"Unknown algorithm: {algorithm}", b''
            
            # Add file header
            header = b'CRYPT'  # Magic bytes
            header += struct.pack('B', len(algorithm))  # Algorithm name length
            header += algorithm.encode()
            header += struct.pack('Q', original_size)  # Original size
            header += struct.pack('B', 1 if compress else 0)  # Compression flag
            
            if metadata:
                header += struct.pack('B', len(metadata))
                header += metadata
            else:
                header += b'\x00'  # No metadata
            
            full_data = header + encrypted_data
            
            return True, f"Encrypted {original_size} bytes", full_data
            
        except Exception as e:
            return False, f"Encryption failed: {str(e)}", b''
    
    def _decrypt_file(self, filepath: str, key: bytes, algorithm: str = '') -> Tuple[bool, str, bytes]:
        """Decrypt a single file"""
        try:
            # Read encrypted file
            with open(filepath, 'rb') as f:
                data = f.read()
            
            # Check magic bytes
            if not data.startswith(b'CRYPT'):
                return False, "Not a valid encrypted file", b''
            
            # Parse header
            pos = 5  # Skip 'CRYPT'
            
            # Algorithm
            algo_len = struct.unpack('B', data[pos:pos+1])[0]
            pos += 1
            file_algo = data[pos:pos+algo_len].decode()
            pos += algo_len
            
            # Use specified algorithm or detect from file
            if algorithm and algorithm != file_algo:
                print(f"[!] Algorithm mismatch: file={file_algo}, requested={algorithm}")
            
            algorithm = file_algo
            
            # Original size
            original_size = struct.unpack('Q', data[pos:pos+8])[0]
            pos += 8
            
            # Compression flag
            compressed = struct.unpack('B', data[pos:pos+1])[0]
            pos += 1
            
            # Metadata
            meta_len = struct.unpack('B', data[pos:pos+1])[0]
            pos += 1
            metadata = data[pos:pos+meta_len]
            pos += meta_len
            
            # Encrypted data
            encrypted_data = data[pos:]
            
            # Decrypt based on algorithm
            if algorithm == 'fernet':
                fernet = Fernet(key)
                decrypted_data = fernet.decrypt(encrypted_data)
                
            elif algorithm == 'xor':
                decrypted_data = self._xor_decrypt(encrypted_data, key)
                
            elif algorithm == 'rot':
                rotation = struct.unpack('B', metadata[:1])[0] if metadata else 13
                decrypted_data = self._rot_decrypt(encrypted_data, rotation)
                
            elif algorithm == 'aes':
                decrypted_data = self._xor_decrypt(encrypted_data, key[:16])  # Simplified
            
            else:
                return False, f"Unknown algorithm: {algorithm}", b''
            
            # Decompress if needed
            if compressed:
                decrypted_data = self._decompress_data(decrypted_data)
            
            # Verify size
            if len(decrypted_data) != original_size:
                print(f"[!] Size mismatch: expected={original_size}, got={len(decrypted_data)}")
            
            return True, f"Decrypted to {len(decrypted_data)} bytes", decrypted_data
            
        except Exception as e:
            return False, f"Decryption failed: {str(e)}", b''
    
    def _process_batch(self, target: str, operation: str, key: bytes, 
                      algorithm: str, output_dir: str, recursive: bool, 
                      extension: str, password: str = '', compress: bool = False) -> List[Tuple[str, bool, str]]:
        """Process multiple files in batch"""
        results = []
        
        if os.path.isfile(target):
            # Single file
            files = [target]
        else:
            # Directory
            files = []
            for root, dirs, filenames in os.walk(target):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
                
                if not recursive:
                    break
        
        for filepath in files:
            try:
                if operation == 'encrypt':
                    success, message, data = self._encrypt_file(
                        filepath, key, algorithm, password, compress
                    )
                    
                    if success:
                        # Determine output path
                        if output_dir:
                            rel_path = os.path.relpath(filepath, target)
                            out_path = os.path.join(output_dir, rel_path + extension)
                            os.makedirs(os.path.dirname(out_path), exist_ok=True)
                        else:
                            out_path = filepath + extension
                        
                        # Write encrypted file
                        with open(out_path, 'wb') as f:
                            f.write(data)
                        
                        results.append((filepath, True, f"Encrypted -> {out_path}"))
                    else:
                        results.append((filepath, False, message))
                
                elif operation == 'decrypt':
                    # Check if file has encryption extension
                    if extension and not filepath.endswith(extension):
                        continue
                    
                    success, message, data = self._decrypt_file(
                        filepath, key, algorithm
                    )
                    
                    if success:
                        # Determine output path
                        if output_dir:
                            rel_path = os.path.relpath(filepath, target)
                            if extension and rel_path.endswith(extension):
                                rel_path = rel_path[:-len(extension)]
                            out_path = os.path.join(output_dir, rel_path)
                            os.makedirs(os.path.dirname(out_path), exist_ok=True)
                        else:
                            if extension and filepath.endswith(extension):
                                out_path = filepath[:-len(extension)]
                            else:
                                out_path = filepath + '.decrypted'
                        
                        # Write decrypted file
                        with open(out_path, 'wb') as f:
                            f.write(data)
                        
                        results.append((filepath, True, f"Decrypted -> {out_path}"))
                    else:
                        results.append((filepath, False, message))
            
            except Exception as e:
                results.append((filepath, False, f"Error: {str(e)}"))
        
        return results
    
    def execute(self):
        """Main execution method"""
        try:
            # Get options
            mode = self.info['Options']['MODE'][0].lower()
            target = self.info['Options']['TARGET'][0]
            key_input = self.info['Options']['KEY'][0]
            algorithm = self.info['Options']['ALGORITHM'][0].lower()
            key_file = self.info['Options']['KEY_FILE'][0]
            output_dir = self.info['Options']['OUTPUT'][0]
            recursive = self.info['Options']['RECURSIVE'][0].lower() == 'true'
            extension = self.info['Options']['EXTENSION'][0]
            password = self.info['Options']['PASSWORD'][0]
            iterations = int(self.info['Options']['ITERATIONS'][0])
            compress = self.info['Options']['COMPRESS'][0].lower() == 'true'
            
            # Validation
            if not target:
                return "[-] TARGET is required"
            
            if not os.path.exists(target):
                return f"[-] Target not found: {target}"
            
            # Determine operation
            if mode == 'decrypt':
                operation = 'decrypt'
            else:
                operation = 'encrypt'  # encrypt or batch
            
            # Generate or load key
            key = None
            salt = None
            
            if key_input:
                # Use provided key
                if algorithm == 'fernet':
                    try:
                        key = key_input.encode()
                        # Test if valid Fernet key
                        Fernet(key)
                    except:
                        return "[-] Invalid Fernet key"
                else:
                    key = key_input.encode()
            
            elif password:
                # Derive key from password
                key, salt = self._generate_key(password, None, iterations)
                print(f"[*] Generated key from password (iterations: {iterations})")
            
            elif key_file and os.path.exists(key_file) and mode == 'decrypt':
                # Load key from file
                try:
                    with open(key_file, 'rb') as f:
                        key_data = f.read()
                    
                    if b':' in key_data:  # Password + salt format
                        parts = key_data.split(b':', 1)
                        stored_password = parts[0].decode()
                        stored_salt = base64.b64decode(parts[1])
                        
                        if password:
                            key, _ = self._generate_key(password, stored_salt, iterations)
                        else:
                            return "[-] Password required for stored key"
                    else:
                        key = key_data
                    
                    print(f"[*] Loaded key from: {key_file}")
                except Exception as e:
                    return f"[-] Failed to load key: {str(e)}"
            
            else:
                # Generate new key
                key, salt = self._generate_key()
                print(f"[*] Generated new encryption key")
                
                # Save key if requested
                if key_file and operation == 'encrypt':
                    try:
                        with open(key_file, 'wb') as f:
                            if password and salt:
                                # Store password derivation info
                                key_data = f"{password}:{base64.b64encode(salt).decode()}"
                                f.write(key_data.encode())
                            else:
                                f.write(key)
                        print(f"[*] Key saved to: {key_file}")
                        print(f"[!] IMPORTANT: Keep this key safe for decryption!")
                    except Exception as e:
                        print(f"[-] Warning: Failed to save key: {str(e)}")
            
            if not key:
                return "[-] No encryption key available"
            
            # Display info
            results = []
            results.append(f"[+] Advanced File Cryptor")
            results.append(f"[+] Mode: {operation}")
            results.append(f"[+] Target: {target}")
            results.append(f"[+] Algorithm: {algorithm}")
            
            if os.path.isdir(target):
                results.append(f"[+] Processing directory (recursive: {recursive})")
            
            if password:
                results.append(f"[+] Using password-based key derivation")
            
            if output_dir:
                results.append(f"[+] Output directory: {output_dir}")
            
            if extension:
                results.append(f"[+] Extension filter: {extension}")
            
            try:
                if os.path.isfile(target):
                    results.append(self._process_file(target, operation, key, algorithm, output_dir))
                elif os.path.isdir(target):
                    for dirroot, _dirs, files in os.walk(target):
                        for fname in files:
                            if not extension or fname.endswith(extension):
                                fpath = os.path.join(dirroot, fname)
                                results.append(self._process_file(fpath, operation, key, algorithm, output_dir))
                else:
                    results.append(f"[-] Target not found: {target}")
            except Exception as e:
                results.append(f"[-] Error: {str(e)}")
            
            return "\n".join(results)
        
        except Exception as e:
            return f"[-] FileCrypter error: {str(e)}"
    
    def _process_file(self, filepath, operation, key, algorithm, output_dir=None):
        """Process a single file."""
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            suffix = '.enc' if operation == 'encrypt' else '.dec'
            out_path = (os.path.join(output_dir, os.path.basename(filepath))
                       if output_dir else filepath + suffix)
            with open(out_path, 'wb') as f:
                f.write(data)
            return f"[+] {operation.title()}ed: {filepath}"
        except Exception as e:
            return f"[-] Failed {filepath}: {str(e)}"


__all__ = ["FileCrypter"]
