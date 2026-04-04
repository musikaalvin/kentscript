MODULE_TYPE = "defensive"
from collections import OrderedDict
import os
import sys
import subprocess
import time
import re

class ModuleClass:
    def __init__(self):
        self.info = {
            'Name': 'ARP Spoof Detector',
            'Description': 'Detects ARP spoofing attacks using arpwatch or manual detection',
            'Author': 'KentScript',
            'Options': OrderedDict([
                ('METHOD', ('arpwatch', True, 'Detection method: arpwatch/basic/arp-scan')),
                ('INTERFACE', ('eth0', True, 'Network interface')),
                ('DURATION', ('30', True, 'Duration in seconds')),
                ('ALERT_FILE', ('/tmp/arp_alerts.log', False, 'File to save alerts'))
            ])
        }
    
    def execute(self):
        method = self.info['Options']['METHOD'][0]
        interface = self.info['Options']['INTERFACE'][0]
        duration = int(self.info['Options']['DURATION'][0])
        alert_file = self.info['Options']['ALERT_FILE'][0]
        
        # Check if interface exists
        if not self._interface_exists(interface):
            return f"[-] Interface {interface} not found"
        
        if method == 'arpwatch':
            return self._arpwatch_detection(interface, duration, alert_file)
        elif method == 'basic':
            return self._basic_detection(interface, duration, alert_file)
        elif method == 'arp-scan':
            return self._arp_scan_detection(interface, duration, alert_file)
        else:
            return f"[-] Unknown method: {method}"
    
    def _interface_exists(self, interface):
        """Check if network interface exists"""
        if os.name == 'posix':
            return os.path.exists(f'/sys/class/net/{interface}')
        return True  # Skip check for Windows
    
    def _arpwatch_detection(self, interface, duration, alert_file):
        """Use arpwatch tool (most reliable)"""
        try:
            # Check if arpwatch is installed
            result = subprocess.run(['which', 'arpwatch'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                return "[-] arpwatch not installed. Install with: sudo apt install arpwatch"
            
            result = []
            result.append(f"[+] Starting arpwatch on {interface}")
            result.append(f"[+] Duration: {duration} seconds")
            result.append(f"[+] Alerts will be saved to: {alert_file}")
            
            # Clean old alert file
            if os.path.exists(alert_file):
                os.remove(alert_file)
            
            # Start arpwatch in background
            cmd = f"arpwatch -i {interface} -f {alert_file}"
            proc = subprocess.Popen(cmd, shell=True, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
            
            # Monitor for duration
            start_time = time.time()
            alerts_found = []
            
            try:
                while time.time() - start_time < duration:
                    time.sleep(2)
                    
                    # Check alert file
                    if os.path.exists(alert_file):
                        with open(alert_file, 'r') as f:
                            new_alerts = f.readlines()[-5:]  # Last 5 alerts
                            for alert in new_alerts:
                                if alert.strip() and alert not in alerts_found:
                                    result.append(f"[!] {alert.strip()}")
                                    alerts_found.append(alert)
                    
                    # Progress
                    elapsed = int(time.time() - start_time)
                    if elapsed % 10 == 0:
                        print(f"[*] Monitoring... {elapsed}/{duration}s")
                
            finally:
                # Kill arpwatch
                proc.terminate()
                proc.wait()
                
                # Also kill any remaining arpwatch processes
                subprocess.run(['pkill', '-f', 'arpwatch'], 
                             stderr=subprocess.DEVNULL)
            
            if alerts_found:
                result.append(f"\n[+] Found {len(alerts_found)} ARP anomalies")
            else:
                result.append("\n[+] No ARP anomalies detected")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"[-] arpwatch error: {str(e)}"
    
    def _basic_detection(self, interface, duration, alert_file):
        """Basic detection using arp command"""
        result = []
        result.append(f"[+] Basic ARP detection on {interface}")
        result.append(f"[+] Monitoring for {duration} seconds")
        
        try:
            # Get initial ARP table
            initial_arp = self._get_arp_table()
            arp_changes = []
            
            start_time = time.time()
            while time.time() - start_time < duration:
                time.sleep(5)
                
                current_arp = self._get_arp_table()
                
                # Detect changes
                for ip, mac in current_arp.items():
                    if ip in initial_arp and initial_arp[ip] != mac:
                        change_msg = f"[!] ARP change: {ip} changed from {initial_arp[ip]} to {mac}"
                        if change_msg not in arp_changes:
                            arp_changes.append(change_msg)
                            result.append(change_msg)
                            
                            # Log to file
                            with open(alert_file, 'a') as f:
                                f.write(f"{time.ctime()}: {change_msg}\n")
                
                # Update for next check
                initial_arp.update(current_arp)
                
                elapsed = int(time.time() - start_time)
                print(f"[*] Progress: {elapsed}/{duration}s")
            
            if arp_changes:
                result.append(f"\n[+] Detected {len(arp_changes)} ARP changes")
            else:
                result.append("\n[+] No ARP changes detected")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"[-] Basic detection error: {str(e)}"
    
    def _get_arp_table(self):
        """Get current ARP table"""
        arp_table = {}
        
        try:
            if os.name == 'posix':
                # Linux/Mac
                output = subprocess.run(['arp', '-a'], 
                                      capture_output=True, text=True).stdout
                
                # Parse arp -a output
                lines = output.strip().split('\n')
                for line in lines:
                    if '(' in line and ')' in line:
                        # Extract IP and MAC
                        ip_match = re.search(r'\(([\d\.]+)\)', line)
                        mac_match = re.search(r'at ([0-9a-fA-F:]+)', line)
                        
                        if ip_match and mac_match:
                            ip = ip_match.group(1)
                            mac = mac_match.group(1).lower()
                            arp_table[ip] = mac
            
            elif os.name == 'nt':
                # Windows
                output = subprocess.run(['arp', '-a'], 
                                      capture_output=True, text=True).stdout
                
                for line in output.split('\n'):
                    parts = line.split()
                    if len(parts) >= 3 and '.' in parts[0]:
                        ip = parts[0]
                        mac = parts[1].replace('-', ':').lower()
                        arp_table[ip] = mac
        
        except:
            pass
        
        return arp_table
    
    def _arp_scan_detection(self, interface, duration, alert_file):
        """Use arp-scan tool"""
        try:
            # Check if arp-scan is installed
            result = subprocess.run(['which', 'arp-scan'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                return "[-] arp-scan not installed. Install with: sudo apt install arp-scan"
            
            result = []
            result.append(f"[+] Starting arp-scan detection on {interface}")
            result.append("[+] This will scan for duplicate MAC addresses")
            
            # Get gateway IP
            gateway_ip = self._get_gateway()
            if gateway_ip:
                result.append(f"[+] Gateway: {gateway_ip}")
            
            # Perform multiple scans to detect duplicates
            ip_to_mac = {}
            duplicates = []
            
            start_time = time.time()
            scan_count = 0
            
            while time.time() - start_time < duration and scan_count < 3:
                scan_count += 1
                result.append(f"\n[*] Scan #{scan_count}")
                
                # Run arp-scan
                cmd = f"sudo arp-scan --interface={interface} --localnet"
                output = subprocess.run(cmd, shell=True, 
                                      capture_output=True, text=True).stdout
                
                # Parse results
                for line in output.split('\n'):
                    if '\t' in line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            ip = parts[0].strip()
                            mac = parts[1].strip().lower()
                            
                            # Check for duplicates
                            if ip in ip_to_mac and ip_to_mac[ip] != mac:
                                dup_msg = f"[!] Duplicate IP {ip}: {ip_to_mac[ip]} vs {mac}"
                                if dup_msg not in duplicates:
                                    duplicates.append(dup_msg)
                                    result.append(dup_msg)
                            
                            ip_to_mac[ip] = mac
                
                time.sleep(10)  # Wait between scans
            
            if duplicates:
                result.append(f"\n[+] Found {len(duplicates)} potential ARP spoofing cases")
            else:
                result.append("\n[+] No duplicate MACs detected")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"[-] arp-scan error: {str(e)}"
    
    def _get_gateway(self):
        """Get default gateway IP"""
        try:
            if os.name == 'posix':
                # Linux/Mac
                result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if lines:
                        parts = lines[0].split()
                        return parts[2] if len(parts) > 2 else None
        except:
            pass
        return None

# Test code
if __name__ == "__main__":
    module = ModuleClass()
    print(module.execute())