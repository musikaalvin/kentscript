"""
KSecurity Framework - KentScript Ethical Cybersecurity Suite
============================================================
Real, working penetration testing and defensive security modules
integrated natively into the KentScript module system.

Module Categories:
  [OFFENSIVE]   bruteforce, exploit, wifi, smb, dumper
  [DEFENSIVE]   arpdetect, netaudit, osint
  [CRYPTO]      crypter, hashcracker
  [RECON]       scanner, osint
  [AUXILIARY]   ai_assist, reporting

All operations require explicit authorization and consent.
For authorized penetration testing and security research only.
"""

from .ks_security_engine import KSecurityEngine, SecurityFramework

__version__ = "2.0.0"
__all__ = ["KSecurityEngine", "SecurityFramework", "get_framework"]

_framework = None

def get_framework():
    global _framework
    if _framework is None:
        _framework = SecurityFramework()
    return _framework
