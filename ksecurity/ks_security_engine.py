#!/usr/bin/env python3
"""
KSecurity Engine - Core Framework
===================================
[KS-SEC-001] Real ethical penetration testing framework
[KS-SEC-002] Metasploit-style module system
[KS-SEC-003] Full integration with KentScript runtime
[KS-SEC-004] Consent and authorization enforcement
[KS-SEC-005] Audit logging for all operations

This is the central dispatcher that loads and manages all KSecurity modules.
Integrates: ARP detection, SSH/FTP bruter, hash cracker, WiFi cracker,
            zip bruter, SMB bruter, credential dumper, file crypter, AI assist.
"""

import os
import sys
import time
import json
import hashlib
import socket
import ipaddress
import threading
import subprocess
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import OrderedDict

# ── Console enhancement: persistent history + dynamic autocomplete ──────────
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.completion import WordCompleter, Completer, Completion
    from prompt_toolkit.formatted_text import ANSI
    _KSEC_PT = True
except Exception:  # pragma: no cover - prompt_toolkit optional
    _KSEC_PT = False

_KSEC_COMMANDS = [
    "exit", "quit", "back", "q", "help", "?", "clear", "show", "search",
    "use", "options", "info", "set", "run", "execute", "exploit", "consent",
    "history", "session", "audit", "scan", "recon", "netaudit",
]


class KSecurityCompleter(Completer):
    """Context-aware autocomplete for the KSecurity console.

    - first word            -> console commands
    - use <frag>            -> module paths (builtin + registered)
    - set <frag>            -> current module option names
    - show <frag>           -> modules / categories / info
    """

    def __init__(self, engine):
        self.engine = engine

    def _module_paths(self):
        paths = set()
        try:
            paths.update(BUILTIN_MODULES.keys())
        except Exception:
            pass
        try:
            paths.update(MODULE_REGISTRY.keys())
        except Exception:
            pass
        return sorted(paths)

    def _option_names(self):
        try:
            mod = self.engine._loaded_module
            if mod is not None:
                return list(mod.info.get("Options", {}).keys())
        except Exception:
            pass
        return []

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()
        trailing_space = text.endswith(" ")
        if words and not trailing_space:
            cur = words[-1]
            first = words[0]
        else:
            cur = ""
            first = words[0] if words else ""

        if first == "use":
            pool = self._module_paths()
        elif first == "set":
            pool = self._option_names()
        elif first == "show":
            pool = ["modules", "categories", "info"]
        elif len(words) <= 1 and not trailing_space:
            pool = _KSEC_COMMANDS
        else:
            pool = []

        for w in pool:
            if w.startswith(cur):
                yield Completion(w, start_position=-len(cur))


# ── Path setup ──────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
_ROOT = _HERE.parent

# ── ANSI Colors ─────────────────────────────────────────────────────────────
class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

    @staticmethod
    def ok(s):    return f"{C.GREEN}[+]{C.RESET} {s}"
    @staticmethod
    def err(s):   return f"{C.RED}[-]{C.RESET} {s}"
    @staticmethod
    def warn(s):  return f"{C.YELLOW}[!]{C.RESET} {s}"
    @staticmethod
    def info(s):  return f"{C.CYAN}[*]{C.RESET} {s}"
    @staticmethod
    def inp(s):   return f"{C.BLUE}[?]{C.RESET} {s}"


# ── Module Registry ──────────────────────────────────────────────────────────
MODULE_REGISTRY = {
    # OFFENSIVE - Active testing modules
    "bruteforce/ssh_ftp": {
        "file": "pybruter_ssh_ftp.py",
        "name": "SSH/FTP Credential Brute Forcer",
        "category": "bruteforce",
        "rank": "Excellent",
        "description": "Multi-threaded SSH and FTP brute force with session handling",
        "requires_auth": True,
        "tags": ["ssh", "ftp", "brute", "credentials", "offensive"],
    },
    "bruteforce/smb": {
        "file": "pyRemoteWinbruter.py",
        "name": "SMB Password Brute Force",
        "category": "bruteforce",
        "rank": "Excellent",
        "description": "Real SMB/NTLM authentication brute force for Windows targets",
        "requires_auth": True,
        "tags": ["smb", "windows", "ntlm", "brute", "offensive"],
    },
    "bruteforce/wifi": {
        "file": "pyWifiCracker.py",
        "name": "WiFi WPA/WPA2/WPA3 Cracker",
        "category": "cracker",
        "rank": "Excellent",
        "description": "WPA handshake and PMKID attack with hashcat/aircrack integration",
        "requires_auth": True,
        "tags": ["wifi", "wpa", "wpa2", "handshake", "aircrack", "offensive"],
    },
    "bruteforce/zip": {
        "file": "pyZipbruter.py",
        "name": "ZIP Archive Password Recovery",
        "category": "postexploit",
        "rank": "Normal",
        "description": "Multi-threaded ZIP password brute force for forensic recovery",
        "requires_auth": True,
        "tags": ["zip", "password", "recovery", "archive"],
    },

    # CRACKER
    "cracker/hash": {
        "file": "pyHashCracker.py",
        "name": "Advanced Hash Cracker",
        "category": "cracker",
        "rank": "Excellent",
        "description": "MD5/SHA1/SHA256/NTLM/bcrypt cracker with hashcat, masks, rules",
        "requires_auth": False,
        "tags": ["hash", "md5", "sha1", "ntlm", "bcrypt", "crack"],
    },

    # POST-EXPLOITATION / COLLECTION
    "exploit/dumper": {
        "file": "pydumper.py",
        "name": "Credential & Data Harvester",
        "category": "exploit",
        "rank": "Excellent",
        "description": "Remote credential harvesting via SMB/SSH for authorized audits",
        "requires_auth": True,
        "tags": ["dump", "credentials", "harvest", "smb", "ssh", "postexploit"],
    },

    # DEFENSIVE / MONITORING
    "defensive/arp_detector": {
        "file": "pyArpspoofdetector.py",
        "name": "ARP Spoof Detector",
        "category": "defensive",
        "rank": "Excellent",
        "description": "Real-time ARP spoofing detection via arpwatch/arp-scan/basic",
        "requires_auth": False,
        "tags": ["arp", "spoof", "detection", "defensive", "mitm"],
    },

    # CRYPTO / ENCODING
    "crypto/crypter": {
        "file": "pyCrypter.py",
        "name": "Advanced File Cryptor",
        "category": "encoder",
        "rank": "Excellent",
        "description": "File encryption/decryption: Fernet, AES, XOR, ROT with PBKDF2",
        "requires_auth": False,
        "tags": ["encrypt", "decrypt", "aes", "fernet", "crypto"],
    },

    # AUXILIARY
    "auxiliary/ai_assist": {
        "file": "pyGpt.py",
        "name": "AI Security Assistant",
        "category": "auxiliary",
        "rank": "Good",
        "description": "AI-powered analysis and report generation for security findings",
        "requires_auth": False,
        "tags": ["ai", "gpt", "assistant", "analysis"],
    },
}

# ── Built-in modules (pure Python, no separate file) ────────────────────────

class _PortScannerModule:
    """Real TCP port scanner - built into KSecurity core."""
    MODULE_TYPE = "scanner"

    def __init__(self):
        self.info = {
            'Name': 'Port Scanner',
            'Rank': 'Excellent',
            'Description': 'Fast TCP connect scan with banner grabbing and service detection',
            'Author': 'KSecurity Core',
            'Options': OrderedDict([
                ('RHOST', ('', True, 'Target IP or hostname')),
                ('PORTS', ('1-1024', True, 'Port range: 1-65535, 22,80,443, or common')),
                ('TIMEOUT', ('1.0', False, 'Connection timeout per port (seconds)')),
                ('THREADS', ('100', False, 'Concurrent scan threads')),
                ('BANNER', ('true', False, 'Attempt banner grabbing (true/false)')),
                ('OUTPUT', ('', False, 'Save results to file')),
            ])
        }
        self._results = []
        self._lock = threading.Lock()

    def execute(self):
        host  = self.info['Options']['RHOST'][0].strip()
        ports_str  = self.info['Options']['PORTS'][0].strip()
        timeout    = float(self.info['Options']['TIMEOUT'][0])
        threads_n  = int(self.info['Options']['THREADS'][0])
        do_banner  = self.info['Options']['BANNER'][0].lower() == 'true'
        out_file   = self.info['Options']['OUTPUT'][0].strip()

        if not host:
            return C.err("RHOST not set. Use: set RHOST <ip>")

        # Resolve host
        try:
            ip = socket.gethostbyname(host)
        except socket.gaierror as e:
            return C.err(f"Cannot resolve {host}: {e}")

        # Parse port range
        ports = self._parse_ports(ports_str)
        if not ports:
            return C.err(f"Invalid port spec: {ports_str}")

        print(C.info(f"Scanning {ip} ({host}) — {len(ports)} ports | timeout={timeout}s | threads={threads_n}"))
        print(C.info(f"Scan started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        print()

        self._results = []
        start_time = time.time()

        # Thread pool scan
        from queue import Queue
        q = Queue()
        for p in ports:
            q.put(p)

        def worker():
            while True:
                try:
                    port = q.get_nowait()
                except Exception:
                    return
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    result = sock.connect_ex((ip, port))
                    if result == 0:
                        banner = ""
                        if do_banner:
                            try:
                                sock.settimeout(2)
                                sock.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
                                banner = sock.recv(256).decode('utf-8', errors='replace').split('\r\n')[0][:80]
                            except Exception:
                                pass
                        service = self._guess_service(port)
                        with self._lock:
                            self._results.append((port, 'open', service, banner))
                            print(f"  {C.GREEN}{port:>5}/tcp{C.RESET}  open  {C.CYAN}{service:<15}{C.RESET}  {banner}")
                    sock.close()
                except Exception:
                    pass
                finally:
                    q.task_done()

        workers = [threading.Thread(target=worker, daemon=True) for _ in range(min(threads_n, len(ports)))]
        for w in workers:
            w.start()
        q.join()

        elapsed = time.time() - start_time
        open_count = len(self._results)

        print()
        print(C.info(f"Scan complete in {elapsed:.2f}s — {open_count} open port(s)"))

        if out_file:
            self._save_results(out_file, ip, host, elapsed)
            print(C.ok(f"Results saved to {out_file}"))

        return f"Scan finished: {open_count} open ports on {ip}"

    def _parse_ports(self, spec):
        COMMON = [21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,
                  1723,3306,3389,5900,8080,8443,8888,9090,27017]
        if spec == 'common':
            return COMMON
        ports = []
        for part in spec.split(','):
            part = part.strip()
            if '-' in part:
                a, b = part.split('-', 1)
                ports.extend(range(int(a), int(b)+1))
            else:
                ports.append(int(part))
        return sorted(set(ports))

    def _guess_service(self, port):
        SVC = {21:'ftp',22:'ssh',23:'telnet',25:'smtp',53:'dns',80:'http',
               110:'pop3',111:'rpcbind',135:'msrpc',139:'netbios',143:'imap',
               443:'https',445:'smb',993:'imaps',995:'pop3s',1723:'pptp',
               3306:'mysql',3389:'rdp',5432:'postgresql',5900:'vnc',
               6379:'redis',8080:'http-alt',8443:'https-alt',27017:'mongodb'}
        return SVC.get(port, f"unknown")

    def _save_results(self, path, ip, host, elapsed):
        lines = [
            f"# KSecurity Port Scan — {datetime.now()}",
            f"# Target: {host} ({ip})",
            f"# Elapsed: {elapsed:.2f}s",
            "",
            "PORT     STATE  SERVICE         BANNER",
        ]
        for port, state, svc, banner in sorted(self._results):
            lines.append(f"{port:>5}/tcp  {state:<6} {svc:<15} {banner}")
        Path(path).write_text('\n'.join(lines))


class _NetworkAuditModule:
    """Network interface + ARP table audit — defensive module."""
    MODULE_TYPE = "defensive"

    def __init__(self):
        self.info = {
            'Name': 'Network Audit',
            'Rank': 'Excellent',
            'Description': 'Local network interface audit: ARP table, routes, open sockets',
            'Author': 'KSecurity Core',
            'Options': OrderedDict([
                ('SCOPE', ('full', False, 'full/arp/routes/sockets/interfaces')),
                ('OUTPUT', ('', False, 'Save report to file')),
            ])
        }

    def execute(self):
        scope = self.info['Options']['SCOPE'][0].strip()
        out   = self.info['Options']['OUTPUT'][0].strip()
        report = []

        report.append(f"{'='*60}")
        report.append(f"  KSecurity Network Audit — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"  Host: {socket.gethostname()}")
        report.append(f"{'='*60}")

        if scope in ('full', 'interfaces'):
            report.append("\n[INTERFACES]")
            try:
                out_i = subprocess.check_output(['ip', 'addr'], text=True, stderr=subprocess.DEVNULL)
                report.append(out_i)
            except Exception:
                report.append("  (ip addr unavailable)")

        if scope in ('full', 'arp'):
            report.append("[ARP TABLE]")
            try:
                out_a = subprocess.check_output(['arp', '-n'], text=True, stderr=subprocess.DEVNULL)
                report.append(out_a)
            except Exception:
                try:
                    out_a = subprocess.check_output(['cat', '/proc/net/arp'], text=True)
                    report.append(out_a)
                except Exception:
                    report.append("  (arp table unavailable)")

        if scope in ('full', 'routes'):
            report.append("[ROUTING TABLE]")
            try:
                out_r = subprocess.check_output(['ip', 'route'], text=True, stderr=subprocess.DEVNULL)
                report.append(out_r)
            except Exception:
                report.append("  (routing table unavailable)")

        if scope in ('full', 'sockets'):
            report.append("[LISTENING SOCKETS]")
            try:
                out_s = subprocess.check_output(['ss', '-tlnp'], text=True, stderr=subprocess.DEVNULL)
                report.append(out_s)
            except Exception:
                try:
                    out_s = subprocess.check_output(['netstat', '-tlnp'], text=True, stderr=subprocess.DEVNULL)
                    report.append(out_s)
                except Exception:
                    report.append("  (socket list unavailable)")

        text = '\n'.join(report)
        print(text)

        if out:
            Path(out).write_text(text)
            print(C.ok(f"Audit saved to {out}"))

        return "Network audit complete"


class _OSINTModule:
    """OSINT / Reconnaissance — passive information gathering."""
    MODULE_TYPE = "recon"

    def __init__(self):
        self.info = {
            'Name': 'OSINT Recon',
            'Rank': 'Good',
            'Description': 'Passive recon: DNS lookups, WHOIS, GeoIP, reverse DNS',
            'Author': 'KSecurity Core',
            'Options': OrderedDict([
                ('TARGET', ('', True, 'IP address, domain, or hostname')),
                ('METHODS', ('all', False, 'all/dns/whois/geo/rdns/headers')),
                ('OUTPUT', ('', False, 'Save results to file')),
            ])
        }

    def execute(self):
        target = self.info['Options']['TARGET'][0].strip()
        methods = self.info['Options']['METHODS'][0].strip()
        out    = self.info['Options']['OUTPUT'][0].strip()

        if not target:
            return C.err("TARGET not set")

        lines = [f"{'='*60}", f"  OSINT Recon: {target}", f"  Time: {datetime.now()}", f"{'='*60}", ""]

        # Resolve IP
        try:
            ip = socket.gethostbyname(target)
            lines.append(C.ok(f"Resolved: {target} → {ip}"))
        except Exception as e:
            ip = target if self._is_ip(target) else None
            if not ip:
                return C.err(f"Cannot resolve {target}")
            lines.append(C.warn(f"Used as IP: {ip}"))

        # Reverse DNS
        if methods in ('all', 'rdns'):
            lines.append("\n[Reverse DNS]")
            try:
                hostname = socket.gethostbyaddr(ip)[0]
                lines.append(C.ok(f"PTR: {ip} → {hostname}"))
            except Exception:
                lines.append(C.info("No PTR record"))

        # DNS records
        if methods in ('all', 'dns'):
            lines.append("\n[DNS Records]")
            for rtype in ['A', 'AAAA', 'MX', 'NS', 'TXT']:
                try:
                    result = subprocess.check_output(
                        ['dig', '+short', rtype, target],
                        text=True, stderr=subprocess.DEVNULL, timeout=5
                    ).strip()
                    if result:
                        lines.append(C.ok(f"{rtype}: {result[:200]}"))
                except Exception:
                    pass

        # WHOIS
        if methods in ('all', 'whois'):
            lines.append("\n[WHOIS]")
            try:
                result = subprocess.check_output(
                    ['whois', target], text=True, stderr=subprocess.DEVNULL, timeout=10
                )
                # Extract key fields
                for line in result.splitlines():
                    l = line.lower()
                    if any(k in l for k in ['registrar', 'country', 'creation', 'expir', 'org:', 'netname']):
                        lines.append(f"  {line.strip()}")
            except Exception:
                lines.append(C.info("WHOIS unavailable"))

        # HTTP headers (if domain)
        if methods in ('all', 'headers') and not self._is_ip(target):
            lines.append("\n[HTTP Headers]")
            for scheme in ['https', 'http']:
                try:
                    import urllib.request
                    req = urllib.request.Request(f"{scheme}://{target}", method='HEAD')
                    req.add_header('User-Agent', 'Mozilla/5.0 (Security Audit)')
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        for k, v in resp.headers.items():
                            if k.lower() in ['server', 'x-powered-by', 'x-frame-options',
                                             'content-security-policy', 'strict-transport-security',
                                             'x-content-type-options']:
                                lines.append(C.ok(f"  {k}: {v}"))
                        break
                except Exception:
                    pass

        text = '\n'.join(lines)
        print(text)

        if out:
            Path(out).write_text(text)
            print(C.ok(f"Report saved to {out}"))

        return f"OSINT recon complete for {target}"

    def _is_ip(self, s):
        try:
            ipaddress.ip_address(s)
            return True
        except ValueError:
            return False


class _ReportModule:
    """Generate pentest report from session findings."""
    MODULE_TYPE = "auxiliary"

    def __init__(self):
        self.info = {
            'Name': 'Pentest Report Generator',
            'Rank': 'Good',
            'Description': 'Generate structured pentest report from session findings',
            'Author': 'KSecurity Core',
            'Options': OrderedDict([
                ('TITLE', ('Penetration Test Report', False, 'Report title')),
                ('CLIENT', ('', False, 'Client/target name')),
                ('SCOPE', ('', False, 'Assessment scope')),
                ('TESTER', ('', False, 'Tester name')),
                ('OUTPUT', ('ksecurity_report.md', True, 'Output file path (.md or .txt)')),
                ('FINDINGS', ('', False, 'JSON file with findings to include')),
            ])
        }
        self._session_findings = []

    def add_finding(self, severity, title, description, recommendation):
        self._session_findings.append({
            'severity': severity,
            'title': title,
            'description': description,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat(),
        })

    def execute(self):
        title   = self.info['Options']['TITLE'][0]
        client  = self.info['Options']['CLIENT'][0] or 'Confidential'
        scope   = self.info['Options']['SCOPE'][0] or 'As agreed'
        tester  = self.info['Options']['TESTER'][0] or 'KSecurity'
        out     = self.info['Options']['OUTPUT'][0]

        findings = list(self._session_findings)

        # Load external findings JSON
        ext = self.info['Options']['FINDINGS'][0].strip()
        if ext and Path(ext).exists():
            with open(ext) as f:
                findings.extend(json.load(f))

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        lines = [
            f"# {title}",
            f"",
            f"| Field       | Value |",
            f"|-------------|-------|",
            f"| Client      | {client} |",
            f"| Date        | {now} |",
            f"| Tester      | {tester} |",
            f"| Scope       | {scope} |",
            f"| Framework   | KSecurity v2.0 (KentScript) |",
            f"",
            f"---",
            f"",
            f"## Executive Summary",
            f"",
            f"This report documents the findings of a security assessment conducted against {client}.",
            f"A total of **{len(findings)}** finding(s) were identified during testing.",
            f"",
            f"---",
            f"",
            f"## Findings",
            f"",
        ]

        sev_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4}
        sorted_findings = sorted(findings, key=lambda x: sev_order.get(x.get('severity', 'INFO').upper(), 99))

        for i, f in enumerate(sorted_findings, 1):
            sev = f.get('severity', 'INFO').upper()
            sev_icon = {'CRITICAL':'🔴','HIGH':'🟠','MEDIUM':'🟡','LOW':'🔵','INFO':'⚪'}.get(sev,'⚪')
            lines += [
                f"### {i}. {sev_icon} [{sev}] {f.get('title', 'Untitled')}",
                f"",
                f"**Description:** {f.get('description', '')}",
                f"",
                f"**Recommendation:** {f.get('recommendation', '')}",
                f"",
                f"---",
                f"",
            ]

        lines += [
            f"## Methodology",
            f"",
            f"Testing followed industry-standard methodology:",
            f"- **Reconnaissance**: Passive OSINT and active scanning",
            f"- **Enumeration**: Service identification and version detection",
            f"- **Exploitation**: Targeted, controlled exploitation of findings",
            f"- **Post-Exploitation**: Credential harvesting and privilege assessment",
            f"- **Reporting**: Structured documentation with remediation guidance",
            f"",
            f"## Tools Used",
            f"",
            f"| Tool | Category |",
            f"|------|----------|",
            f"| KSecurity Port Scanner | Reconnaissance |",
            f"| SSH/FTP Bruter | Authentication Testing |",
            f"| Hash Cracker | Credential Analysis |",
            f"| ARP Spoof Detector | Network Monitoring |",
            f"| File Crypter | Data Protection Testing |",
            f"| OSINT Recon | Passive Reconnaissance |",
            f"",
            f"---",
            f"*Generated by KSecurity v2.0 — KentScript Ethical Security Framework*",
        ]

        text = '\n'.join(lines)
        Path(out).write_text(text)
        print(C.ok(f"Report written to: {out}"))
        return f"Report generated: {out} ({len(findings)} findings)"


# ── Built-in module registry ──────────────────────────────────────────────
BUILTIN_MODULES = {
    "scanner/ports":        _PortScannerModule,
    "defensive/netaudit":   _NetworkAuditModule,
    "recon/osint":          _OSINTModule,
    "auxiliary/report":     _ReportModule,
}


# ════════════════════════════════════════════════════════════════════════════
# KSecurityEngine
# ════════════════════════════════════════════════════════════════════════════

class KSecurityEngine:
    """
    Core engine for the KSecurity framework.
    Manages module lifecycle, options, audit logging, and consent enforcement.
    """

    BANNER = f"""
{C.RED}██╗  ██╗███████╗███████╗ ██████╗{C.RESET}{C.WHITE}██╗   ██╗██████╗ ██╗████████╗██╗   ██╗
{C.RED}██║ ██╔╝██╔════╝██╔════╝██╔════╝{C.RESET}{C.WHITE}██║   ██║██╔══██╗██║╚══██╔══╝╚██╗ ██╔╝
{C.RED}█████╔╝ ███████╗█████╗  ██║     {C.RESET}{C.WHITE}██║   ██║██████╔╝██║   ██║    ╚████╔╝ 
{C.RED}██╔═██╗ ╚════██║██╔══╝  ██║     {C.RESET}{C.WHITE}██║   ██║██╔══██╗██║   ██║     ╚██╔╝  
{C.RED}██║  ██╗███████║███████╗╚██████╗{C.RESET}{C.WHITE}╚██████╔╝██║  ██║██║   ██║      ██║   
{C.RED}╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝{C.RESET}{C.WHITE} ╚═════╝ ╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝{C.RESET}

    {C.CYAN}KentScript Ethical Cybersecurity Framework v2.0{C.RESET}
    {C.DIM}For authorized penetration testing and security research only.{C.RESET}
"""

    def __init__(self, log_file: str = "ksecurity_audit.log"):
        self._loaded_module = None
        self._module_path   = None
        self._audit_log     = log_file
        self._session_start = datetime.now()
        self._history       = []
        self._consent_given = False
        self._ksecurity_dir = _HERE

        self._audit(f"KSecurityEngine initialized — session start")

    # ── Audit logging ────────────────────────────────────────────────────
    def _audit(self, msg: str):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry = f"[{ts}] {msg}\n"
        try:
            with open(self._audit_log, 'a') as f:
                f.write(entry)
        except Exception:
            pass

    # ── Module loader ─────────────────────────────────────────────────────
    def _load_external_module(self, module_key: str):
        """Dynamically import a module from the ksecurity directory."""
        info = MODULE_REGISTRY.get(module_key)
        if not info:
            return None, f"Module not found: {module_key}"

        file_path = self._ksecurity_dir / info['file']
        if not file_path.exists():
            return None, f"Module file missing: {file_path}"

        spec = importlib.util.spec_from_file_location(module_key.replace('/', '_'), file_path)
        mod  = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            return None, f"Module load error: {e}"

        if not hasattr(mod, 'ModuleClass'):
            return None, "Module has no ModuleClass"

        return mod.ModuleClass(), None

    def use(self, module_path: str) -> str:
        """Select a module for use."""
        if module_path in BUILTIN_MODULES:
            self._loaded_module = BUILTIN_MODULES[module_path]()
            self._module_path   = module_path
            self._audit(f"USE builtin/{module_path}")
            name = self._loaded_module.info['Name']
            return C.ok(f"Module loaded: {C.BOLD}{name}{C.RESET}\n       Type 'options' to see settings, 'run' to execute.")

        if module_path in MODULE_REGISTRY:
            obj, err = self._load_external_module(module_path)
            if err:
                return C.err(err)
            self._loaded_module = obj
            self._module_path   = module_path
            self._audit(f"USE external/{module_path}")
            name = self._loaded_module.info.get('Name', module_path)
            return C.ok(f"Module loaded: {C.BOLD}{name}{C.RESET}\n       Type 'options' to see settings, 'run' to execute.")

        return C.err(f"No module at path: {module_path}  (use 'show modules' to list)")

    def options(self) -> str:
        """Print current module options."""
        if not self._loaded_module:
            return C.err("No module loaded. Use: use <module/path>")
        m = self._loaded_module
        info = m.info
        lines = [
            f"\n  {C.BOLD}Module: {info.get('Name', self._module_path)}{C.RESET}",
            f"  {info.get('Description', '')}",
            f"  Rank: {info.get('Rank', 'N/A')}  |  Author: {info.get('Author', 'N/A')}",
            "",
            f"  {'Name':<20} {'Current':<25} {'Required':<10} Description",
            f"  {'─'*20} {'─'*25} {'─'*10} {'─'*30}",
        ]
        for opt, val in info.get('Options', {}).items():
            current, required, desc = val
            req_str = C.RED+"yes"+C.RESET if required else "no"
            cur_str = current if current else C.DIM+"<empty>"+C.RESET
            lines.append(f"  {opt:<20} {cur_str:<25} {req_str:<10} {desc}")
        return '\n'.join(lines)

    def set(self, key: str, value: str) -> str:
        """Set module option."""
        if not self._loaded_module:
            return C.err("No module loaded")
        opts = self._loaded_module.info.get('Options', {})
        if key not in opts:
            return C.err(f"Unknown option: {key}")
        old = opts[key]
        opts[key] = (value, old[1], old[2])
        self._audit(f"SET {self._module_path} {key}={value}")
        return C.ok(f"{key} => {value}")

    def run(self) -> str:
        """Execute the loaded module with consent check."""
        if not self._loaded_module:
            return C.err("No module loaded. Use: use <module/path>")

        # Check required options
        for opt, val in self._loaded_module.info.get('Options', {}).items():
            current, required, desc = val
            if required and not current.strip():
                return C.err(f"Required option not set: {opt}\n       Use: set {opt} <value>")

        # Consent gate for offensive modules
        requires_auth = False
        if self._module_path in MODULE_REGISTRY:
            requires_auth = MODULE_REGISTRY[self._module_path].get('requires_auth', False)

        if requires_auth and not self._consent_given:
            return (
                C.warn("This module performs active/offensive operations.\n"
                       f"  Confirm you have explicit authorization to test the target.\n"
                       f"  Type: {C.BOLD}consent{C.RESET} to acknowledge, then run again.")
            )

        # Validate targets
        val_err = self._validate_target()
        if val_err:
            return val_err

        self._audit(f"RUN {self._module_path}")
        print(C.info(f"Running: {self._loaded_module.info.get('Name', self._module_path)}"))
        print()

        try:
            result = self._loaded_module.execute()
            self._audit(f"DONE {self._module_path}: {str(result)[:200]}")
            return result or ""
        except KeyboardInterrupt:
            return C.warn("Module interrupted by user")
        except Exception as e:
            self._audit(f"ERROR {self._module_path}: {e}")
            return C.err(f"Module error: {e}")

    def _validate_target(self) -> Optional[str]:
        """Validate target option if set."""
        opts = self._loaded_module.info.get('Options', {})
        for key in ('RHOST', 'TARGET'):
            if key in opts:
                val = opts[key][0].strip()
                if val:
                    # Warn about public IPs (not block - user has consent)
                    try:
                        ip = socket.gethostbyname(val)
                        addr = ipaddress.ip_address(ip)
                        if not addr.is_private and not addr.is_loopback:
                            self._audit(f"WARN: public IP target {ip}")
                    except Exception:
                        pass
        return None

    def consent(self) -> str:
        self._consent_given = True
        self._audit("CONSENT granted by user")
        return C.ok("Authorization acknowledged. You may now run offensive modules.")

    def show(self, what: str) -> str:
        """Show modules/categories/info."""
        if what == 'modules':
            return self._show_modules()
        if what == 'info':
            return self._show_info()
        if what in ('categories', 'cats'):
            return self._show_categories()
        return C.err(f"Unknown: show {what}  (try: modules, categories, info)")

    def _show_modules(self) -> str:
        lines = [f"\n  {C.BOLD}Available KSecurity Modules{C.RESET}\n"]
        # Built-ins
        lines.append(f"  {C.CYAN}── Built-in Modules ──{C.RESET}")
        for path, cls in sorted(BUILTIN_MODULES.items()):
            obj = cls()
            name = obj.info.get('Name', path)
            rank = obj.info.get('Rank', 'N/A')
            desc = obj.info.get('Description', '')[:55]
            lines.append(f"  {C.GREEN}{path:<30}{C.RESET} {rank:<12} {desc}")
        # External
        lines.append(f"\n  {C.CYAN}── Integrated Modules ──{C.RESET}")
        for path, info in sorted(MODULE_REGISTRY.items()):
            status = C.GREEN+"✓"+C.RESET if (self._ksecurity_dir / info['file']).exists() else C.RED+"✗"+C.RESET
            lines.append(
                f"  {status} {C.GREEN}{path:<30}{C.RESET} {info['rank']:<12} {info['description'][:55]}"
            )
        lines.append(f"\n  Use: {C.BOLD}use <module/path>{C.RESET} to load a module")
        return '\n'.join(lines)

    def _show_categories(self) -> str:
        cats: Dict[str, List[str]] = {}
        for path, info in MODULE_REGISTRY.items():
            cat = info['category']
            cats.setdefault(cat, []).append(path)
        for path, cls in BUILTIN_MODULES.items():
            obj = cls()
            cat = obj.MODULE_TYPE
            cats.setdefault(cat, []).append(f"{path} [builtin]")
        lines = [f"\n  {C.BOLD}Module Categories{C.RESET}\n"]
        for cat, paths in sorted(cats.items()):
            lines.append(f"  {C.CYAN}{cat.upper()}{C.RESET}")
            for p in sorted(paths):
                lines.append(f"    {p}")
        return '\n'.join(lines)

    def _show_info(self) -> str:
        if not self._loaded_module:
            return C.err("No module loaded")
        m = self._loaded_module
        info = m.info
        tags = []
        if self._module_path in MODULE_REGISTRY:
            tags = MODULE_REGISTRY[self._module_path].get('tags', [])
        lines = [
            f"\n  {C.BOLD}Module Information{C.RESET}",
            f"  {'Name:':<15} {info.get('Name', '')}",
            f"  {'Path:':<15} {self._module_path}",
            f"  {'Rank:':<15} {info.get('Rank', 'N/A')}",
            f"  {'Platform:':<15} {info.get('Platform', 'Any')}",
            f"  {'Author:':<15} {info.get('Author', 'N/A')}",
            f"  {'Version:':<15} {info.get('Version', '1.0')}",
            f"  {'Tags:':<15} {', '.join(tags) if tags else 'N/A'}",
            f"  {'Note:':<15} {info.get('Note', 'For authorized use only')}",
            f"\n  {info.get('Description', '')}",
        ]
        return '\n'.join(lines)

    def search(self, query: str) -> str:
        """Search modules by keyword."""
        q = query.lower()
        hits = []
        all_mods = {**{k: {'name': v().info.get('Name',''), 'desc': v().info.get('Description',''),
                            'tags': [v().MODULE_TYPE]} for k, v in BUILTIN_MODULES.items()},
                    **{k: {'name': v['name'], 'desc': v['description'], 'tags': v['tags']}
                       for k, v in MODULE_REGISTRY.items()}}
        for path, info in all_mods.items():
            text = f"{path} {info['name']} {info['desc']} {' '.join(info['tags'])}".lower()
            if q in text:
                hits.append((path, info['name'], info['desc'][:60]))

        if not hits:
            return C.warn(f"No modules found matching: {query}")
        lines = [f"\n  Search results for '{query}':\n"]
        for path, name, desc in hits:
            lines.append(f"  {C.GREEN}{path:<32}{C.RESET} {name:<25} {desc}")
        return '\n'.join(lines)

    def history(self) -> str:
        """Show session history."""
        if not self._history:
            return C.info("No command history yet")
        return '\n'.join(f"  {i+1:>3}. {cmd}" for i, cmd in enumerate(self._history))

    def session_info(self) -> str:
        elapsed = datetime.now() - self._session_start
        return (
            f"\n  {C.BOLD}KSecurity Session{C.RESET}\n"
            f"  Started:  {self._session_start.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"  Elapsed:  {elapsed}\n"
            f"  Consent:  {'granted' if self._consent_given else 'not given'}\n"
            f"  Audit:    {self._audit_log}\n"
        )


# ════════════════════════════════════════════════════════════════════════════
# SecurityFramework - High-level interface used by KentScript runtime
# ════════════════════════════════════════════════════════════════════════════

class SecurityFramework:
    """
    Top-level interface exposing KSecurity as KentScript native functions.
    Called by ks_modules.py when KentScript code imports ksecurity.*
    """

    def __init__(self):
        self._engine = KSecurityEngine()

    # KentScript import bindings
    def port_scan(self, host: str, ports: str = "common", timeout: float = 1.0) -> str:
        self._engine.use("scanner/ports")
        self._engine.set("RHOST", host)
        self._engine.set("PORTS", ports)
        self._engine.set("TIMEOUT", str(timeout))
        self._engine._consent_given = True
        return self._engine.run()

    def hash_crack(self, hash_value: str, hash_type: str = "md5",
                   wordlist: str = "/usr/share/wordlists/rockyou.txt") -> str:
        self._engine.use("cracker/hash")
        self._engine.set("HASH", hash_value)
        self._engine.set("HASH_TYPE", hash_type)
        self._engine.set("WORDLIST", wordlist)
        self._engine._consent_given = True
        return self._engine.run()

    def arp_detect(self, interface: str = "eth0", duration: int = 30) -> str:
        self._engine.use("defensive/arp_detector")
        self._engine.set("INTERFACE", interface)
        self._engine.set("DURATION", str(duration))
        return self._engine.run()

    def osint_recon(self, target: str) -> str:
        self._engine.use("recon/osint")
        self._engine.set("TARGET", target)
        return self._engine.run()

    def encrypt_file(self, path: str, algorithm: str = "aes", password: str = "") -> str:
        self._engine.use("crypto/crypter")
        self._engine.set("TARGET", path)
        self._engine.set("ALGORITHM", algorithm)
        self._engine.set("PASSWORD", password)
        self._engine.set("MODE", "encrypt")
        return self._engine.run()

    def get_engine(self) -> KSecurityEngine:
        return self._engine

    def interactive(self):
        """Launch interactive KSecurity console."""
        SecurityConsole(self._engine).run()


# ════════════════════════════════════════════════════════════════════════════
# SecurityConsole - Interactive REPL
# ════════════════════════════════════════════════════════════════════════════

class SecurityConsole:
    """
    Interactive Metasploit-style console for KSecurity.
    Invoked via: ksecurity.interactive() or `ks --security`
    """

    HELP = f"""
  {C.BOLD}KSecurity Console Commands{C.RESET}

  {C.CYAN}Navigation{C.RESET}
    show modules              List all available modules
    show categories           List modules by category
    show info                 Info on current module
    search <keyword>          Search modules

  {C.CYAN}Module Control{C.RESET}
    use <module/path>         Load a module
    options                   Show module options
    set <OPTION> <value>      Set an option
    run / execute             Run the module
    info                      Alias for show info

  {C.CYAN}Authorization{C.RESET}
    consent                   Acknowledge you have authorization

  {C.CYAN}Session{C.RESET}
    history                   Command history
    session                   Session info
    audit                     Show audit log path
    clear                     Clear screen

  {C.CYAN}Quick Scans{C.RESET}
    scan <host> [ports]       Quick port scan
    recon <target>            Quick OSINT recon
    netaudit                  Local network audit

    help / ?                  Show this help
    exit / quit / back        Exit console

  {C.CYAN}Console Features{C.RESET}
    Tab / type                Autocomplete: modules (use), options (set),
                             subcommands (show), and commands — live from the
                             module registry, not a static list.
    {C.BOLD}↑{C.RESET} / {C.BOLD}↓{C.RESET}                   Command history (persisted in ~/.ksecurity_history)
                             across sessions — this is a real interactive console.
"""

    def __init__(self, engine: KSecurityEngine):
        self._e = engine
        self._running = True

    def run(self):
        print(self._e.BANNER)
        print(C.info(f"Type 'help' for commands, 'show modules' to list all modules"))
        print(C.warn("For authorized penetration testing and security research ONLY"))
        print()

        _read = None
        if _KSEC_PT and sys.stdin.isatty():
            _session = PromptSession(
                history=FileHistory(os.path.expanduser("~/.ksecurity_history")),
                completer=KSecurityCompleter(self._e),
                complete_while_typing=True,
            )

            def _read(prompt):
                return _session.prompt(ANSI(prompt))
        if _read is None:
            def _read(prompt):
                return input(prompt)

        while self._running:
            try:
                module_part = f"{C.DIM}({self._e._module_path}){C.RESET} " if self._e._module_path else ""
                prompt = f"{C.RED}ksecurity{C.RESET} {module_part}{C.CYAN}>{C.RESET} "
                cmd = _read(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not cmd:
                continue

            self._e._history.append(cmd)
            self._dispatch(cmd)

    def _dispatch(self, cmd: str):
        parts = cmd.split(None, 2)
        verb  = parts[0].lower()

        if verb in ('exit', 'quit', 'back', 'q'):
            self._running = False
            print(C.info("Exiting KSecurity console"))
            return

        if verb in ('help', '?'):
            print(self.HELP)
            return

        if verb == 'clear':
            os.system('clear' if os.name != 'nt' else 'cls')
            return

        if verb == 'show':
            what = parts[1] if len(parts) > 1 else ''
            print(self._e.show(what))
            return

        if verb == 'search':
            q = ' '.join(parts[1:]) if len(parts) > 1 else ''
            print(self._e.search(q))
            return

        if verb == 'use':
            path = parts[1] if len(parts) > 1 else ''
            print(self._e.use(path))
            return

        if verb == 'options':
            print(self._e.options())
            return

        if verb == 'info':
            print(self._e.show('info'))
            return

        if verb == 'set':
            if len(parts) < 3:
                print(C.err("Usage: set <OPTION> <value>"))
                return
            print(self._e.set(parts[1].upper(), parts[2]))
            return

        if verb in ('run', 'execute', 'exploit'):
            result = self._e.run()
            if result:
                print(result)
            return

        if verb == 'consent':
            print(self._e.consent())
            return

        if verb == 'history':
            print(self._e.history())
            return

        if verb == 'session':
            print(self._e.session_info())
            return

        if verb == 'audit':
            print(C.info(f"Audit log: {self._e._audit_log}"))
            return

        # Quick commands
        if verb == 'scan':
            host  = parts[1] if len(parts) > 1 else ''
            ports = parts[2] if len(parts) > 2 else 'common'
            if not host:
                print(C.err("Usage: scan <host> [ports]"))
                return
            self._e.use("scanner/ports")
            self._e.set("RHOST", host)
            self._e.set("PORTS", ports)
            self._e._consent_given = True
            result = self._e.run()
            if result:
                print(result)
            return

        if verb == 'recon':
            target = parts[1] if len(parts) > 1 else ''
            if not target:
                print(C.err("Usage: recon <target>"))
                return
            self._e.use("recon/osint")
            self._e.set("TARGET", target)
            result = self._e.run()
            if result:
                print(result)
            return

        if verb == 'netaudit':
            self._e.use("defensive/netaudit")
            result = self._e.run()
            if result:
                print(result)
            return

        print(C.err(f"Unknown command: {verb}  (try 'help')"))


# ── Entrypoint (python -m ksecurity) ─────────────────────────────────────
if __name__ == '__main__':
    engine = KSecurityEngine()
    SecurityConsole(engine).run()
