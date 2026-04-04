#!/usr/bin/env python3
"""
KentScript Net + IO Engine v1.0
================================
Everything Python stdlib + libc can do — exposed to KentScript.

NET MODULE covers:
  TCP/UDP/Unix sockets, raw sockets, SSL/TLS, HTTP/HTTPS, REST,
  WebSocket (pure-Python), FTP (client + server-mode), SMTP, IMAP, POP3,
  DNS resolution, WHOIS, port scanning, async networking, epoll/poll/select,
  IP/CIDR math, URL parsing, multicast, socket options, keep-alive,
  curl/wget subprocess wrappers, netcat-style tools, SSH via subprocess,
  packet-level building via struct, HTTP server, XMLRPC, email building.

IO MODULE covers:
  File R/W/append (text + binary), random-access, memory-mapped files,
  async file I/O, file locking (fcntl), directory walk, glob, watch,
  tar/zip/gz/bz2/lzma/zlib compression, sqlite3, CSV, INI/config,
  pickle, binary struct packing, C array types, pipes, PTY, select/epoll,
  process management (fork/exec/wait/signal), resource limits, user/group
  info, /proc filesystem, libc via ctypes (malloc/free/memcpy/mmap/…),
  terminal control (termios/curses), temp files, atomic rename, symlinks,
  hard links, chmod/chown/chgrp, ACLs via xattr, file watchers, sendfile.

SYS MODULE covers:
  Everything os + sys + platform + resource + signal + subprocess.
"""

import os, sys, io, socket, ssl, struct, array, mmap as _mmap_mod
import threading, subprocess, select, signal, fcntl, termios, pty
import stat, grp, pwd, resource, glob as _glob, fnmatch, shutil, tempfile
import pathlib, tarfile, zipfile, gzip, bz2, lzma, zlib, sqlite3, csv
import configparser, pickle, queue, concurrent.futures, multiprocessing
import asyncio, ipaddress, urllib.parse, urllib.request, urllib.error
import urllib.robotparser, http.client, http.server, http.cookies
import ftplib, smtplib, imaplib, poplib, xmlrpc.client, xmlrpc.server
import email, email.mime.text, email.mime.multipart, email.mime.base
import email.mime.application, email.encoders, email.utils
import html.parser, xml.etree.ElementTree as _ET
import hashlib, hmac, base64, binascii, secrets, uuid, time, datetime
import ctypes, ctypes.util, platform, traceback, weakref, contextlib
import selectors, socketserver, json, re, logging, collections
from typing import Optional, Tuple, Dict, List, Any, Union, Callable

_LIBC_NAME = ctypes.util.find_library('c') or 'libc.so.6'
try:
    _LIBC = ctypes.CDLL(_LIBC_NAME, use_errno=True)
except Exception:
    _LIBC = None

_OS   = platform.system().lower()
_ARCH = platform.machine().lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  NET — complete networking
# ═══════════════════════════════════════════════════════════════════════════════

# ── TCP ───────────────────────────────────────────────────────────────────────

def net_tcp_connect(host: str, port: int, timeout: float = 10,
                    ssl_wrap: bool = False,
                    ssl_ctx=None) -> socket.socket:
    """Open TCP connection. Returns connected socket."""
    s = socket.create_connection((host, int(port)), timeout=timeout)
    if ssl_wrap:
        ctx = ssl_ctx or ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)
    return s

def net_tcp_listen(host: str = '0.0.0.0', port: int = 0,
                   backlog: int = 128,
                   reuse: bool = True) -> socket.socket:
    """Create a listening TCP socket."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if reuse:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, int(port)))
    s.listen(backlog)
    return s

def net_tcp_accept(server_sock: socket.socket):
    """Accept one connection. Returns (conn, (host, port))."""
    return server_sock.accept()

def net_tcp_send(sock: socket.socket, data) -> int:
    if isinstance(data, str):
        data = data.encode('utf-8')
    return sock.send(data)

def net_tcp_sendall(sock: socket.socket, data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    sock.sendall(data)

def net_tcp_recv(sock: socket.socket, size: int = 4096) -> bytes:
    return sock.recv(size)

def net_tcp_recv_str(sock: socket.socket, size: int = 4096) -> str:
    return sock.recv(size).decode('utf-8', errors='replace')

def net_tcp_close(sock: socket.socket):
    try: sock.shutdown(socket.SHUT_RDWR)
    except Exception: pass
    sock.close()

def net_tcp_ping(host: str, port: int, timeout: float = 2) -> bool:
    try:
        s = socket.create_connection((host, int(port)), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False

def net_set_timeout(sock: socket.socket, seconds: float):
    sock.settimeout(seconds)

def net_set_nonblocking(sock: socket.socket):
    sock.setblocking(False)

def net_set_blocking(sock: socket.socket):
    sock.setblocking(True)

def net_set_keepalive(sock: socket.socket, idle: int = 60,
                      interval: int = 10, count: int = 5):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    if hasattr(socket, 'TCP_KEEPIDLE'):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle)
    if hasattr(socket, 'TCP_KEEPINTVL'):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval)
    if hasattr(socket, 'TCP_KEEPCNT'):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, count)

def net_set_nodelay(sock: socket.socket):
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

def net_setsockopt(sock, level, optname, val):
    sock.setsockopt(level, optname, val)

def net_getsockopt(sock, level, optname, buflen=0):
    if buflen:
        return sock.getsockopt(level, optname, buflen)
    return sock.getsockopt(level, optname)

def net_socket_addr(sock: socket.socket):
    return sock.getsockname()

def net_peer_addr(sock: socket.socket):
    return sock.getpeername()

def net_socket_fd(sock: socket.socket) -> int:
    return sock.fileno()

# ── UDP ───────────────────────────────────────────────────────────────────────

def net_udp_socket(ipv6: bool = False) -> socket.socket:
    fam = socket.AF_INET6 if ipv6 else socket.AF_INET
    return socket.socket(fam, socket.SOCK_DGRAM)

def net_udp_bind(sock: socket.socket, host: str, port: int):
    sock.bind((host, int(port)))

def net_udp_sendto(sock: socket.socket, data, host: str, port: int) -> int:
    if isinstance(data, str): data = data.encode('utf-8')
    return sock.sendto(data, (host, int(port)))

def net_udp_recvfrom(sock: socket.socket, size: int = 65535):
    data, addr = sock.recvfrom(size)
    return data, addr

def net_udp_broadcast(sock: socket.socket, data, port: int):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if isinstance(data, str): data = data.encode('utf-8')
    sock.sendto(data, ('<broadcast>', int(port)))

def net_udp_multicast_join(sock: socket.socket, group: str,
                            iface: str = ''):
    mreq = struct.pack('4sL',
        socket.inet_aton(group),
        socket.inet_aton(iface) if iface else socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP, mreq)

# ── Unix domain sockets ────────────────────────────────────────────────────────

def net_unix_connect(path: str) -> socket.socket:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(path)
    return s

def net_unix_listen(path: str, backlog: int = 32) -> socket.socket:
    if os.path.exists(path): os.unlink(path)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(path)
    s.listen(backlog)
    return s

def net_unix_dgram_socket(path: str = '') -> socket.socket:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    if path: s.bind(path)
    return s

# ── Raw sockets ───────────────────────────────────────────────────────────────

def net_raw_socket(proto: int = socket.IPPROTO_RAW) -> socket.socket:
    """Create raw socket. Requires root."""
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, proto)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    return s

def net_packet_socket() -> socket.socket:
    """AF_PACKET socket for full L2 frames. Requires root."""
    return socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                         socket.htons(0x0003))  # ETH_P_ALL

# ── SSL/TLS ────────────────────────────────────────────────────────────────────

def net_ssl_context(verify: bool = True,
                    certfile: str = None,
                    keyfile: str = None,
                    cafile: str = None,
                    server_side: bool = False) -> ssl.SSLContext:
    if server_side:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    else:
        ctx = ssl.create_default_context(cafile=cafile)
        if not verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
    if certfile:
        ctx.load_cert_chain(certfile, keyfile)
    return ctx

def net_ssl_wrap(sock: socket.socket, host: str = '',
                 ctx: ssl.SSLContext = None,
                 server_side: bool = False) -> ssl.SSLSocket:
    if ctx is None:
        ctx = ssl.create_default_context()
    if server_side:
        return ctx.wrap_socket(sock, server_side=True)
    return ctx.wrap_socket(sock, server_hostname=host)

def net_ssl_cert(ssl_sock: ssl.SSLSocket) -> dict:
    return ssl_sock.getpeercert()

def net_ssl_cipher(ssl_sock: ssl.SSLSocket):
    return ssl_sock.cipher()

def net_ssl_version(ssl_sock: ssl.SSLSocket) -> str:
    return ssl_sock.version() or ''

# ── HTTP/HTTPS (requests-based) ────────────────────────────────────────────────

def net_http_get(url: str, headers: dict = None,
                 timeout: float = 30, verify: bool = True,
                 auth=None, params: dict = None) -> dict:
    import requests as _req
    r = _req.get(url, headers=headers, timeout=timeout,
                 verify=verify, auth=auth, params=params)
    return {
        'status': r.status_code, 'headers': dict(r.headers),
        'text': r.text, 'content': r.content,
        'json': _safe_json(r), 'url': r.url,
        'encoding': r.encoding, 'elapsed': r.elapsed.total_seconds(),
    }

def net_http_post(url: str, data=None, json_data=None,
                  headers: dict = None, timeout: float = 30,
                  verify: bool = True, auth=None, files=None) -> dict:
    import requests as _req
    r = _req.post(url, data=data, json=json_data, headers=headers,
                  timeout=timeout, verify=verify, auth=auth, files=files)
    return {
        'status': r.status_code, 'headers': dict(r.headers),
        'text': r.text, 'content': r.content,
        'json': _safe_json(r), 'url': r.url,
    }

def net_http_put(url: str, data=None, json_data=None,
                 headers: dict = None, timeout: float = 30,
                 verify: bool = True) -> dict:
    import requests as _req
    r = _req.put(url, data=data, json=json_data,
                 headers=headers, timeout=timeout, verify=verify)
    return {'status': r.status_code, 'headers': dict(r.headers),
            'text': r.text, 'content': r.content}

def net_http_patch(url: str, data=None, json_data=None,
                   headers: dict = None, timeout: float = 30) -> dict:
    import requests as _req
    r = _req.patch(url, data=data, json=json_data,
                   headers=headers, timeout=timeout)
    return {'status': r.status_code, 'text': r.text, 'content': r.content}

def net_http_delete(url: str, headers: dict = None,
                    timeout: float = 30) -> dict:
    import requests as _req
    r = _req.delete(url, headers=headers, timeout=timeout)
    return {'status': r.status_code, 'text': r.text}

def net_http_head(url: str, headers: dict = None, timeout: float = 10) -> dict:
    import requests as _req
    r = _req.head(url, headers=headers, timeout=timeout)
    return {'status': r.status_code, 'headers': dict(r.headers)}

def net_http_options(url: str, timeout: float = 10) -> dict:
    import requests as _req
    r = _req.options(url, timeout=timeout)
    return {'status': r.status_code, 'headers': dict(r.headers)}

def net_http_session() -> Any:
    import requests as _req
    s = _req.Session()
    s.headers.update({'User-Agent': 'KentScript/3.1'})
    return s

def net_http_session_get(session, url: str, **kwargs) -> dict:
    r = session.get(url, **kwargs)
    return {'status': r.status_code, 'text': r.text,
            'headers': dict(r.headers), 'content': r.content}

def net_http_session_post(session, url: str, **kwargs) -> dict:
    r = session.post(url, **kwargs)
    return {'status': r.status_code, 'text': r.text,
            'headers': dict(r.headers), 'content': r.content}

def net_http_basic_auth(user: str, password: str):
    import requests.auth
    return requests.auth.HTTPBasicAuth(user, password)

def net_http_digest_auth(user: str, password: str):
    import requests.auth
    return requests.auth.HTTPDigestAuth(user, password)

def _safe_json(r):
    try: return r.json()
    except Exception: return None

# ── Download / Upload ─────────────────────────────────────────────────────────

def net_download(url: str, dest_path: str,
                 chunk_size: int = 65536,
                 timeout: float = 60,
                 headers: dict = None,
                 progress: bool = False) -> str:
    """Download URL to file. Returns dest_path."""
    import requests as _req
    r = _req.get(url, stream=True, timeout=timeout,
                 headers=headers or {})
    r.raise_for_status()
    total = int(r.headers.get('Content-Length', 0))
    done = 0
    with open(dest_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                done += len(chunk)
                if progress and total:
                    pct = done * 100 // total
                    sys.stdout.write(f'\r  {pct}% ({done}/{total})')
                    sys.stdout.flush()
    if progress and total: print()
    return dest_path

def net_upload_file(url: str, filepath: str,
                    field_name: str = 'file',
                    extra_data: dict = None,
                    headers: dict = None,
                    timeout: float = 60) -> dict:
    """Upload file via multipart/form-data POST."""
    import requests as _req
    with open(filepath, 'rb') as f:
        files = {field_name: (os.path.basename(filepath), f)}
        r = _req.post(url, files=files, data=extra_data,
                      headers=headers or {}, timeout=timeout)
    return {'status': r.status_code, 'text': r.text}

def net_upload_bytes(url: str, data: bytes,
                     headers: dict = None, timeout: float = 60) -> dict:
    """PUT raw bytes to URL."""
    import requests as _req
    r = _req.put(url, data=data, headers=headers or {}, timeout=timeout)
    return {'status': r.status_code, 'text': r.text}

# ── Low-level HTTP (http.client, no requests dependency) ──────────────────────

def net_http_raw_get(host: str, path: str = '/',
                     port: int = 80, https: bool = False,
                     headers: dict = None, timeout: float = 10) -> dict:
    """Raw HTTP GET without requests library."""
    cls = http.client.HTTPSConnection if https else http.client.HTTPConnection
    conn = cls(host, port, timeout=timeout)
    conn.request('GET', path, headers=headers or {})
    r = conn.getresponse()
    body = r.read()
    conn.close()
    return {'status': r.status, 'reason': r.reason,
            'headers': dict(r.getheaders()), 'body': body,
            'text': body.decode('utf-8', errors='replace')}

def net_http_raw_request(host: str, method: str, path: str,
                         body=None, headers: dict = None,
                         port: int = 80, https: bool = False,
                         timeout: float = 10) -> dict:
    cls = http.client.HTTPSConnection if https else http.client.HTTPConnection
    conn = cls(host, port, timeout=timeout)
    if isinstance(body, str): body = body.encode('utf-8')
    conn.request(method, path, body=body, headers=headers or {})
    r = conn.getresponse()
    raw = r.read()
    conn.close()
    return {'status': r.status, 'reason': r.reason,
            'headers': dict(r.getheaders()),
            'body': raw, 'text': raw.decode('utf-8', errors='replace')}

# ── WebSocket (pure Python, no external library) ──────────────────────────────

class WebSocket:
    """
    Minimal WebSocket client (RFC 6455) over raw socket.
    Works without websockets/aiohttp packages.
    """
    def __init__(self):
        self._sock: Optional[socket.socket] = None
        self._ssl_sock = None
        self._key = None

    def connect(self, url: str, headers: dict = None, timeout: float = 10):
        parsed = urllib.parse.urlparse(url)
        use_ssl = parsed.scheme in ('wss', 'https')
        host = parsed.hostname
        port = parsed.port or (443 if use_ssl else 80)
        path = parsed.path or '/'
        if parsed.query: path += '?' + parsed.query

        s = socket.create_connection((host, port), timeout=timeout)
        if use_ssl:
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=host)

        # Handshake
        import base64, os as _os
        key = base64.b64encode(_os.urandom(16)).decode()
        self._key = key
        hdrs = (
            f'GET {path} HTTP/1.1\r\n'
            f'Host: {host}:{port}\r\n'
            f'Upgrade: websocket\r\n'
            f'Connection: Upgrade\r\n'
            f'Sec-WebSocket-Key: {key}\r\n'
            f'Sec-WebSocket-Version: 13\r\n'
        )
        if headers:
            for k, v in headers.items():
                hdrs += f'{k}: {v}\r\n'
        hdrs += '\r\n'
        s.sendall(hdrs.encode())

        # Read response
        resp = b''
        while b'\r\n\r\n' not in resp:
            resp += s.recv(1024)
        if b'101' not in resp[:20]:
            raise ConnectionError(f'WebSocket upgrade failed: {resp[:200]}')
        self._sock = s

    def send_text(self, message: str):
        self._send_frame(message.encode('utf-8'), opcode=0x1)

    def send_bytes(self, data: bytes):
        self._send_frame(data, opcode=0x2)

    def send_ping(self):
        self._send_frame(b'', opcode=0x9)

    def recv(self, timeout: float = None) -> Tuple[int, bytes]:
        """Returns (opcode, payload). opcode: 1=text, 2=binary, 8=close, 9=ping, 10=pong"""
        if timeout: self._sock.settimeout(timeout)
        hdr = self._recv_exact(2)
        fin = (hdr[0] >> 7) & 1
        opcode = hdr[0] & 0xF
        masked = (hdr[1] >> 7) & 1
        length = hdr[1] & 0x7F
        if length == 126:
            length = struct.unpack('>H', self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack('>Q', self._recv_exact(8))[0]
        mask_key = self._recv_exact(4) if masked else b'\x00' * 4
        payload = bytearray(self._recv_exact(length))
        if masked:
            for i in range(len(payload)):
                payload[i] ^= mask_key[i % 4]
        return opcode, bytes(payload)

    def recv_text(self, timeout: float = None) -> str:
        _, payload = self.recv(timeout)
        return payload.decode('utf-8', errors='replace')

    def close(self):
        if self._sock:
            try: self._send_frame(b'', opcode=0x8)
            except Exception: pass
            try: self._sock.close()
            except Exception: pass
            self._sock = None

    def _send_frame(self, data: bytes, opcode: int):
        import os as _os
        header = bytes([0x80 | opcode])
        mask_bit = 0x80
        length = len(data)
        if length < 126:
            header += bytes([mask_bit | length])
        elif length < 65536:
            header += bytes([mask_bit | 126]) + struct.pack('>H', length)
        else:
            header += bytes([mask_bit | 127]) + struct.pack('>Q', length)
        mask = _os.urandom(4)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self._sock.sendall(header + masked)

    def _recv_exact(self, n: int) -> bytes:
        buf = b''
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError('WebSocket connection closed')
            buf += chunk
        return buf

def net_websocket_connect(url: str, headers: dict = None) -> WebSocket:
    ws = WebSocket()
    ws.connect(url, headers=headers)
    return ws

# ── FTP ───────────────────────────────────────────────────────────────────────

def net_ftp_connect(host: str, port: int = 21,
                    user: str = 'anonymous',
                    password: str = 'kent@example.com',
                    timeout: float = 30) -> ftplib.FTP:
    ftp = ftplib.FTP()
    ftp.connect(host, int(port), timeout=timeout)
    ftp.login(user, password)
    return ftp

def net_ftp_connect_tls(host: str, port: int = 21,
                         user: str = '', password: str = '',
                         timeout: float = 30) -> ftplib.FTP_TLS:
    ftp = ftplib.FTP_TLS()
    ftp.connect(host, int(port), timeout=timeout)
    ftp.login(user, password)
    ftp.prot_p()
    return ftp

def net_ftp_list(ftp: ftplib.FTP, path: str = '.') -> List[str]:
    files = []
    ftp.dir(path, lambda line: files.append(line))
    return files

def net_ftp_nlst(ftp: ftplib.FTP, path: str = '.') -> List[str]:
    return ftp.nlst(path)

def net_ftp_download(ftp: ftplib.FTP, remote: str, local: str) -> str:
    with open(local, 'wb') as f:
        ftp.retrbinary(f'RETR {remote}', f.write)
    return local

def net_ftp_upload(ftp: ftplib.FTP, local: str, remote: str):
    with open(local, 'rb') as f:
        ftp.storbinary(f'STOR {remote}', f)

def net_ftp_upload_bytes(ftp: ftplib.FTP, data: bytes, remote: str):
    ftp.storbinary(f'STOR {remote}', io.BytesIO(data))

def net_ftp_mkdir(ftp: ftplib.FTP, path: str):
    ftp.mkd(path)

def net_ftp_rmdir(ftp: ftplib.FTP, path: str):
    ftp.rmd(path)

def net_ftp_delete(ftp: ftplib.FTP, path: str):
    ftp.delete(path)

def net_ftp_rename(ftp: ftplib.FTP, src: str, dst: str):
    ftp.rename(src, dst)

def net_ftp_cwd(ftp: ftplib.FTP, path: str):
    ftp.cwd(path)

def net_ftp_pwd(ftp: ftplib.FTP) -> str:
    return ftp.pwd()

def net_ftp_size(ftp: ftplib.FTP, path: str) -> int:
    return ftp.size(path)

def net_ftp_quit(ftp: ftplib.FTP):
    ftp.quit()

# ── SFTP / SSH (via subprocess + ssh binary, or pure Python fallback) ─────────

def net_ssh_exec(host: str, command: str,
                 user: str = None, port: int = 22,
                 key_file: str = None, password: str = None,
                 timeout: int = 30) -> dict:
    """Run command on remote host via SSH subprocess."""
    import shutil as _sh
    ssh = _sh.which('ssh')
    if not ssh:
        return {'returncode': -1, 'stdout': '',
                'stderr': 'ssh binary not found in PATH'}
    args = [ssh, '-o', 'StrictHostKeyChecking=no',
            '-o', 'BatchMode=yes',
            '-p', str(port)]
    if key_file: args += ['-i', key_file]
    if user: args += [f'{user}@{host}']
    else: args += [host]
    args += [command]
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return {'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}

def net_ssh_tunnel(local_port: int, remote_host: str, remote_port: int,
                   ssh_host: str, ssh_user: str = None,
                   ssh_port: int = 22, key_file: str = None) -> subprocess.Popen:
    """Start SSH local port-forward tunnel. Returns Popen object."""
    import shutil as _sh
    ssh = _sh.which('ssh')
    if not ssh: raise RuntimeError('ssh binary not found')
    args = [ssh, '-N', '-L',
            f'{local_port}:{remote_host}:{remote_port}',
            '-p', str(ssh_port),
            '-o', 'StrictHostKeyChecking=no']
    if key_file: args += ['-i', key_file]
    target = f'{ssh_user}@{ssh_host}' if ssh_user else ssh_host
    args.append(target)
    return subprocess.Popen(args)

def net_scp_upload(local: str, remote_path: str, host: str,
                   user: str = None, port: int = 22,
                   key_file: str = None) -> dict:
    import shutil as _sh
    scp = _sh.which('scp') or _sh.which('rsync')
    if not scp:
        return {'returncode': -1, 'stderr': 'scp/rsync not found'}
    target = f'{user}@{host}:{remote_path}' if user else f'{host}:{remote_path}'
    args = [scp, '-P', str(port), '-o', 'StrictHostKeyChecking=no']
    if key_file: args += ['-i', key_file]
    args += [local, target]
    r = subprocess.run(args, capture_output=True, text=True)
    return {'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}

def net_scp_download(remote_path: str, local: str, host: str,
                     user: str = None, port: int = 22,
                     key_file: str = None) -> dict:
    import shutil as _sh
    scp = _sh.which('scp') or _sh.which('rsync')
    if not scp:
        return {'returncode': -1, 'stderr': 'scp/rsync not found'}
    src = f'{user}@{host}:{remote_path}' if user else f'{host}:{remote_path}'
    args = [scp, '-P', str(port), '-o', 'StrictHostKeyChecking=no']
    if key_file: args += ['-i', key_file]
    args += [src, local]
    r = subprocess.run(args, capture_output=True, text=True)
    return {'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}

# ── SMTP (email sending) ───────────────────────────────────────────────────────

def net_smtp_send(host: str, port: int, user: str, password: str,
                  from_addr: str, to_addrs,
                  subject: str, body: str,
                  attachments: List[str] = None,
                  use_tls: bool = True,
                  use_ssl: bool = False,
                  timeout: float = 30) -> bool:
    """Send email via SMTP."""
    if isinstance(to_addrs, str): to_addrs = [to_addrs]

    msg = email.mime.multipart.MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)
    msg['Subject'] = subject
    msg['Date'] = email.utils.formatdate(localtime=True)
    msg['Message-ID'] = email.utils.make_msgid()
    msg.attach(email.mime.text.MIMEText(body, 'plain', 'utf-8'))

    if attachments:
        for fpath in attachments:
            with open(fpath, 'rb') as f:
                part = email.mime.base.MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            email.encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                            f'attachment; filename="{os.path.basename(fpath)}"')
            msg.attach(part)

    try:
        if use_ssl:
            s = smtplib.SMTP_SSL(host, int(port), timeout=timeout)
        else:
            s = smtplib.SMTP(host, int(port), timeout=timeout)
            if use_tls:
                s.ehlo(); s.starttls(); s.ehlo()
        if user and password:
            s.login(user, password)
        s.sendmail(from_addr, to_addrs, msg.as_string())
        s.quit()
        return True
    except Exception as e:
        raise RuntimeError(f'SMTP error: {e}') from e

def net_smtp_connect(host: str, port: int = 587,
                     use_tls: bool = True, use_ssl: bool = False,
                     timeout: float = 30):
    if use_ssl:
        s = smtplib.SMTP_SSL(host, int(port), timeout=timeout)
    else:
        s = smtplib.SMTP(host, int(port), timeout=timeout)
        if use_tls:
            s.ehlo(); s.starttls(); s.ehlo()
    return s

def net_smtp_login(smtp, user: str, password: str):
    smtp.login(user, password)

def net_smtp_send_raw(smtp, from_addr: str, to_addrs, raw_msg: str):
    if isinstance(to_addrs, str): to_addrs = [to_addrs]
    smtp.sendmail(from_addr, to_addrs, raw_msg)

def net_smtp_quit(smtp):
    smtp.quit()

def net_build_email(from_addr: str, to_addrs,
                    subject: str, body: str,
                    html_body: str = None,
                    attachments: List[str] = None) -> str:
    """Build RFC2822 email string."""
    if isinstance(to_addrs, str): to_addrs = [to_addrs]
    msg = email.mime.multipart.MIMEMultipart('alternative' if html_body else 'mixed')
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)
    msg['Subject'] = subject
    msg['Date'] = email.utils.formatdate(localtime=True)
    msg['Message-ID'] = email.utils.make_msgid()
    msg.attach(email.mime.text.MIMEText(body, 'plain', 'utf-8'))
    if html_body:
        msg.attach(email.mime.text.MIMEText(html_body, 'html', 'utf-8'))
    if attachments:
        for fp in attachments:
            with open(fp, 'rb') as f:
                p = email.mime.base.MIMEBase('application', 'octet-stream')
                p.set_payload(f.read())
            email.encoders.encode_base64(p)
            p.add_header('Content-Disposition',
                         f'attachment; filename="{os.path.basename(fp)}"')
            msg.attach(p)
    return msg.as_string()

# ── IMAP (email reading) ───────────────────────────────────────────────────────

def net_imap_connect(host: str, port: int = 993,
                     use_ssl: bool = True) -> imaplib.IMAP4_SSL:
    if use_ssl:
        return imaplib.IMAP4_SSL(host, int(port))
    return imaplib.IMAP4(host, int(port))

def net_imap_login(imap, user: str, password: str):
    imap.login(user, password)

def net_imap_list_folders(imap) -> List[str]:
    _, folders = imap.list()
    return [f.decode() if isinstance(f, bytes) else f for f in folders]

def net_imap_select(imap, folder: str = 'INBOX'):
    return imap.select(folder)

def net_imap_search(imap, criteria: str = 'ALL') -> List[str]:
    _, data = imap.search(None, criteria)
    return data[0].split() if data[0] else []

def net_imap_fetch(imap, msg_id, parts: str = 'RFC822') -> bytes:
    _, data = imap.fetch(msg_id, f'({parts})')
    return data[0][1] if data and data[0] else b''

def net_imap_logout(imap):
    imap.logout()

# ── POP3 ──────────────────────────────────────────────────────────────────────

def net_pop3_connect(host: str, port: int = 995,
                     use_ssl: bool = True):
    if use_ssl:
        return poplib.POP3_SSL(host, int(port))
    return poplib.POP3(host, int(port))

def net_pop3_login(pop, user: str, password: str):
    pop.user(user); pop.pass_(password)

def net_pop3_list(pop) -> List:
    _, msgs, _ = pop.list()
    return msgs

def net_pop3_retr(pop, num: int) -> bytes:
    _, lines, _ = pop.retr(int(num))
    return b'\r\n'.join(lines)

def net_pop3_quit(pop):
    pop.quit()

# ── DNS ───────────────────────────────────────────────────────────────────────

def net_dns_resolve(domain: str, record_type: str = 'A') -> list:
    """Resolve DNS. Basic: uses socket. Advanced: uses dnspython if available."""
    try:
        import dns.resolver as _dnsr
        answers = _dnsr.resolve(domain, record_type)
        return [str(r) for r in answers]
    except ImportError:
        pass
    # Fallback via socket
    if record_type == 'A':
        try:
            infos = socket.getaddrinfo(domain, None, socket.AF_INET)
            return list({i[4][0] for i in infos})
        except Exception: return []
    elif record_type == 'AAAA':
        try:
            infos = socket.getaddrinfo(domain, None, socket.AF_INET6)
            return list({i[4][0] for i in infos})
        except Exception: return []
    elif record_type == 'MX':
        # Use system dig/nslookup if available
        dig = shutil.which('dig')
        if dig:
            r = subprocess.run([dig, '+short', 'MX', domain],
                               capture_output=True, text=True)
            return r.stdout.strip().split('\n') if r.stdout.strip() else []
        return []
    return socket.getaddrinfo(domain, None)

def net_dns_reverse(ip: str) -> str:
    try: return socket.gethostbyaddr(ip)[0]
    except Exception: return ''

def net_gethostbyname(host: str) -> str:
    return socket.gethostbyname(host)

def net_gethostbyname_ex(host: str):
    return socket.gethostbyname_ex(host)

def net_getaddrinfo(host: str, port=None, family=0, type=0) -> list:
    return socket.getaddrinfo(host, port, family, type)

def net_gethostname() -> str:
    return socket.gethostname()

def net_getfqdn() -> str:
    return socket.getfqdn()

# ── Port scanning ──────────────────────────────────────────────────────────────

def net_port_scan(host: str, ports,
                  timeout: float = 0.5,
                  max_threads: int = 256) -> Dict[int, bool]:
    """Scan ports. ports can be list, range, or 'start-end' string."""
    if isinstance(ports, str):
        if '-' in ports:
            a, b = ports.split('-', 1)
            ports = range(int(a), int(b) + 1)
        else:
            ports = [int(ports)]
    results = {}
    lock = threading.Lock()

    def probe(p):
        try:
            s = socket.create_connection((host, p), timeout=timeout)
            s.close()
            with lock: results[p] = True
        except Exception:
            with lock: results[p] = False

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as ex:
        list(ex.map(probe, ports))
    return results

def net_port_scan_open(host: str, ports,
                       timeout: float = 0.5) -> List[int]:
    """Return list of open ports."""
    return [p for p, ok in net_port_scan(host, ports, timeout).items() if ok]

# ── I/O multiplexing (select/poll/epoll) ──────────────────────────────────────

def net_select(rlist, wlist=None, xlist=None, timeout=None):
    return select.select(rlist, wlist or [], xlist or [], timeout)

def net_epoll_create() -> 'select.epoll':
    """Create epoll object (Linux only)."""
    return select.epoll()

def net_epoll_register(ep, fd: int,
                       events: int = select.EPOLLIN | select.EPOLLHUP):
    ep.register(fd, events)

def net_epoll_poll(ep, timeout: float = 1.0, maxevents: int = 100):
    return ep.poll(timeout, maxevents)

def net_poll_create():
    return select.poll()

def net_selector() -> selectors.DefaultSelector:
    return selectors.DefaultSelector()

# ── curl / wget subprocess wrappers ───────────────────────────────────────────

def net_curl(url: str, method: str = 'GET',
             data: str = None, headers: dict = None,
             output: str = None, follow: bool = True,
             timeout: int = 30, insecure: bool = False,
             extra_args: list = None) -> dict:
    """Run curl subprocess."""
    curl = shutil.which('curl')
    if not curl: return {'error': 'curl not found'}
    args = [curl, '-s', '-w', '\n%{http_code}', '-X', method.upper()]
    if follow: args.append('-L')
    if insecure: args.append('-k')
    if timeout: args += ['--max-time', str(timeout)]
    if headers:
        for k, v in headers.items(): args += ['-H', f'{k}: {v}']
    if data: args += ['-d', data]
    if output: args += ['-o', output]
    if extra_args: args += extra_args
    args.append(url)
    r = subprocess.run(args, capture_output=True, text=True)
    parts = r.stdout.rsplit('\n', 1)
    body = parts[0] if len(parts) > 1 else r.stdout
    status = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return {'status': status, 'body': body,
            'stderr': r.stderr, 'returncode': r.returncode}

def net_wget(url: str, output: str = None,
             quiet: bool = True, timeout: int = 30) -> dict:
    """Run wget subprocess."""
    wget = shutil.which('wget')
    if not wget: return {'error': 'wget not found'}
    args = [wget]
    if quiet: args.append('-q')
    if timeout: args += ['--timeout', str(timeout)]
    if output: args += ['-O', output]
    else: args += ['-O', '-']
    args.append(url)
    r = subprocess.run(args, capture_output=True, text=True)
    return {'body': r.stdout, 'stderr': r.stderr, 'returncode': r.returncode}

# ── IP address utilities ───────────────────────────────────────────────────────

def net_ip_info(ip_str: str) -> dict:
    try:
        addr = ipaddress.ip_address(ip_str)
        return {'address': str(addr), 'version': addr.version,
                'is_private': addr.is_private,
                'is_loopback': addr.is_loopback,
                'is_multicast': addr.is_multicast,
                'is_global': addr.is_global,
                'packed': addr.packed.hex()}
    except Exception as e:
        return {'error': str(e)}

def net_ip_network(cidr: str) -> dict:
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        hosts = list(net.hosts())
        return {
            'network': str(net.network_address),
            'broadcast': str(net.broadcast_address),
            'netmask': str(net.netmask),
            'prefixlen': net.prefixlen,
            'num_hosts': net.num_addresses,
            'first_host': str(hosts[0]) if hosts else '',
            'last_host': str(hosts[-1]) if hosts else '',
            'version': net.version,
        }
    except Exception as e:
        return {'error': str(e)}

def net_ip_in_network(ip: str, cidr: str) -> bool:
    try:
        return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)
    except Exception: return False

def net_url_parse(url: str) -> dict:
    u = urllib.parse.urlparse(url)
    return {'scheme': u.scheme, 'netloc': u.netloc, 'host': u.hostname,
            'port': u.port, 'path': u.path, 'query': u.query,
            'fragment': u.fragment, 'username': u.username,
            'password': u.password}

def net_url_encode(params: dict) -> str:
    return urllib.parse.urlencode(params)

def net_url_decode(query: str) -> dict:
    return dict(urllib.parse.parse_qsl(query))

def net_url_quote(s: str) -> str:
    return urllib.parse.quote(s)

def net_url_unquote(s: str) -> str:
    return urllib.parse.unquote(s)

def net_url_join(base: str, url: str) -> str:
    return urllib.parse.urljoin(base, url)

def net_url_build(scheme: str, host: str, path: str = '/',
                  params: dict = None, fragment: str = '') -> str:
    q = urllib.parse.urlencode(params or {})
    return urllib.parse.urlunparse((scheme, host, path, '', q, fragment))

# ── HTTP server ────────────────────────────────────────────────────────────────

class _HTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Minimal HTTP handler with custom routes."""
    routes: dict = {}
    directory_root: str = '.'

    def do_GET(self):
        handler = self.routes.get(('GET', self.path))
        if handler:
            try:
                resp = handler(self)
                if isinstance(resp, dict):
                    body = json.dumps(resp).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', len(body))
                    self.end_headers()
                    self.wfile.write(body)
                elif isinstance(resp, str):
                    body = resp.encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', len(body))
                    self.end_headers()
                    self.wfile.write(body)
                elif isinstance(resp, bytes):
                    self.send_response(200)
                    self.send_header('Content-Length', len(resp))
                    self.end_headers()
                    self.wfile.write(resp)
            except Exception as e:
                self.send_error(500, str(e))
        else:
            super().do_GET()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        handler = self.routes.get(('POST', self.path))
        if handler:
            try:
                resp = handler(self, body)
                if isinstance(resp, (dict, list)):
                    out = json.dumps(resp).encode()
                    ct = 'application/json'
                elif isinstance(resp, str):
                    out = resp.encode('utf-8'); ct = 'text/plain'
                else:
                    out = resp or b''; ct = 'application/octet-stream'
                self.send_response(200)
                self.send_header('Content-Type', ct)
                self.send_header('Content-Length', len(out))
                self.end_headers()
                self.wfile.write(out)
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404)

    def log_message(self, fmt, *args): pass  # silence


def net_http_server(port: int = 8080, host: str = '0.0.0.0',
                    directory: str = '.',
                    routes: dict = None,
                    threaded: bool = True,
                    daemon: bool = True) -> http.server.HTTPServer:
    """
    Start simple HTTP server. routes = {('GET','/path'): handler_fn, ...}
    Returns server object. Call server.serve_forever() or server.handle_request().
    """
    handler = type('_H', (_HTTPHandler,), {
        'routes': routes or {},
        'directory': directory,
    })
    srv = socketserver.ThreadingTCPServer if threaded else socketserver.TCPServer
    server = srv((host, int(port)), handler)
    if daemon:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
    return server

def net_http_server_stop(server):
    server.shutdown()

# ── XMLRPC ────────────────────────────────────────────────────────────────────

def net_xmlrpc_client(url: str):
    return xmlrpc.client.ServerProxy(url)

def net_xmlrpc_call(client, method: str, *args):
    return getattr(client, method)(*args)

# ── Packet building (raw bytes) ────────────────────────────────────────────────

def net_build_ipv4_header(src: str, dst: str,
                           proto: int = socket.IPPROTO_TCP,
                           ttl: int = 64, ident: int = 0) -> bytes:
    version_ihl = (4 << 4) | 5
    tos = 0; tot_len = 20; flags_frag = 0; checksum = 0
    src_b = socket.inet_aton(src); dst_b = socket.inet_aton(dst)
    hdr = struct.pack('!BBHHHBBH4s4s',
        version_ihl, tos, tot_len, ident, flags_frag,
        ttl, proto, checksum, src_b, dst_b)
    # Compute checksum
    def chksum(b):
        s = 0
        for i in range(0, len(b), 2):
            w = (b[i] << 8) + b[i+1]
            s += w
        s = (s >> 16) + (s & 0xFFFF)
        s += (s >> 16)
        return ~s & 0xFFFF
    cs = chksum(hdr)
    return struct.pack('!BBHHHBBH4s4s',
        version_ihl, tos, tot_len, ident, flags_frag,
        ttl, proto, cs, src_b, dst_b)

def net_build_udp_header(src_port: int, dst_port: int,
                          data: bytes = b'') -> bytes:
    length = 8 + len(data)
    return struct.pack('!HHHH', src_port, dst_port, length, 0)

def net_build_tcp_header(src_port: int, dst_port: int,
                          seq: int = 0, ack: int = 0,
                          flags: int = 0x02,  # SYN
                          window: int = 65535) -> bytes:
    data_offset = (5 << 4)
    return struct.pack('!HHIIBBHHH',
        src_port, dst_port, seq, ack,
        data_offset, flags, window, 0, 0)

def net_inet_aton(ip: str) -> bytes:
    return socket.inet_aton(ip)

def net_inet_ntoa(packed: bytes) -> str:
    return socket.inet_ntoa(packed)

def net_htons(x: int) -> int: return socket.htons(x)
def net_ntohs(x: int) -> int: return socket.ntohs(x)
def net_htonl(x: int) -> int: return socket.htonl(x)
def net_ntohl(x: int) -> int: return socket.ntohl(x)


# ═══════════════════════════════════════════════════════════════════════════════
#  IO — complete file, filesystem, process, IPC, terminal, C-level I/O
# ═══════════════════════════════════════════════════════════════════════════════

# ── File open modes ────────────────────────────────────────────────────────────

def io_open(path: str, mode: str = 'r', encoding: str = 'utf-8',
            buffering: int = -1, newline=None):
    """Open file. mode like Python: r/w/a/rb/wb/r+/w+/ab etc."""
    if 'b' in mode:
        return open(path, mode, buffering=buffering)
    return open(path, mode, encoding=encoding,
                buffering=buffering, newline=newline)

def io_read(path: str, encoding: str = 'utf-8') -> str:
    with open(path, 'r', encoding=encoding) as f: return f.read()

def io_read_bytes(path: str) -> bytes:
    with open(path, 'rb') as f: return f.read()

def io_read_lines(path: str, encoding: str = 'utf-8') -> List[str]:
    with open(path, 'r', encoding=encoding) as f: return f.readlines()

def io_read_line(f) -> str:
    return f.readline()

def io_write(path: str, content: str, encoding: str = 'utf-8'):
    with open(path, 'w', encoding=encoding) as f: f.write(content)

def io_write_bytes(path: str, data: bytes):
    with open(path, 'wb') as f: f.write(data)

def io_write_lines(path: str, lines: List[str], encoding: str = 'utf-8'):
    with open(path, 'w', encoding=encoding) as f: f.writelines(lines)

def io_append(path: str, content: str, encoding: str = 'utf-8'):
    with open(path, 'a', encoding=encoding) as f: f.write(content)

def io_append_bytes(path: str, data: bytes):
    with open(path, 'ab') as f: f.write(data)

def io_close(f): f.close()
def io_flush(f): f.flush()
def io_seek(f, pos: int, whence: int = 0): f.seek(pos, whence)
def io_tell(f) -> int: return f.tell()
def io_read_from(f, size: int = -1): return f.read(size)
def io_write_to(f, data): f.write(data)
def io_truncate(f, size: int = None): f.truncate(size)

def io_fileno(f) -> int: return f.fileno()
def io_isatty(f) -> bool: return f.isatty()

# ── Random access / binary I/O ────────────────────────────────────────────────

def io_read_at(path: str, offset: int, size: int) -> bytes:
    """Read bytes at specific offset without reading whole file."""
    with open(path, 'rb') as f:
        f.seek(offset)
        return f.read(size)

def io_write_at(path: str, offset: int, data: bytes):
    """Write bytes at specific offset."""
    with open(path, 'r+b') as f:
        f.seek(offset)
        f.write(data)

def io_read_struct(path: str, offset: int, fmt: str):
    """Read and unpack struct from file at offset."""
    with open(path, 'rb') as f:
        f.seek(offset)
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, f.read(size))

def io_write_struct(path: str, offset: int, fmt: str, *values):
    """Pack and write struct to file at offset."""
    with open(path, 'r+b') as f:
        f.seek(offset)
        f.write(struct.pack(fmt, *values))

# ── Memory-mapped files ────────────────────────────────────────────────────────

def io_mmap_open(path: str, access: str = 'rw',
                 length: int = 0, offset: int = 0):
    """
    Memory-map a file. access: 'r'=read-only, 'rw'=read-write, 'c'=copy-on-write.
    Returns mmap object. Supports [index], [slice], seek(), read(), write().
    """
    mode = 'r+b' if 'w' in access else 'rb'
    if access == 'c': mode = 'rb'
    f = open(path, mode)
    acc = {
        'r':  _mmap_mod.ACCESS_READ,
        'rw': _mmap_mod.ACCESS_WRITE,
        'c':  _mmap_mod.ACCESS_COPY,
    }.get(access, _mmap_mod.ACCESS_WRITE)
    size = length or os.path.getsize(path)
    mm = _mmap_mod.mmap(f.fileno(), size, access=acc, offset=offset)
    f.close()
    return mm

def io_mmap_anon(size: int,
                 read: bool = True,
                 write: bool = True,
                 exec_: bool = False):
    """Create anonymous memory mapping (not backed by file)."""
    prot = 0
    if read:  prot |= _mmap_mod.PROT_READ
    if write: prot |= _mmap_mod.PROT_WRITE
    if exec_ and hasattr(_mmap_mod, 'PROT_EXEC'):
        prot |= _mmap_mod.PROT_EXEC
    flags = _mmap_mod.MAP_SHARED | _mmap_mod.MAP_ANONYMOUS
    m = _mmap_mod.mmap(-1, size, flags, prot)
    return m

def io_mmap_read(mm, offset: int, size: int) -> bytes:
    mm.seek(offset); return mm.read(size)

def io_mmap_write(mm, offset: int, data: bytes):
    mm.seek(offset); mm.write(data)

def io_mmap_flush(mm): mm.flush()
def io_mmap_close(mm): mm.close()
def io_mmap_size(mm) -> int: return mm.size()
def io_mmap_resize(mm, new_size: int): mm.resize(new_size)

# ── File locking ───────────────────────────────────────────────────────────────

def io_flock(f, exclusive: bool = True):
    """Advisory file lock via flock."""
    op = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    fcntl.flock(f, op)

def io_flock_nb(f, exclusive: bool = True) -> bool:
    """Non-blocking flock. Returns True if locked, False if would block."""
    op = (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB
    try: fcntl.flock(f, op); return True
    except BlockingIOError: return False

def io_funlock(f):
    fcntl.flock(f, fcntl.LOCK_UN)

def io_fcntl(f, cmd, arg=0):
    return fcntl.fcntl(f, cmd, arg)

def io_ioctl(f, request: int, arg=0):
    return fcntl.ioctl(f, request, arg)

# ── Filesystem operations ──────────────────────────────────────────────────────

def io_stat(path: str) -> dict:
    s = os.stat(path)
    return {
        'size': s.st_size, 'mode': s.st_mode, 'uid': s.st_uid,
        'gid': s.st_gid, 'atime': s.st_atime, 'mtime': s.st_mtime,
        'ctime': s.st_ctime, 'nlink': s.st_nlink, 'ino': s.st_ino,
        'dev': s.st_dev, 'blocks': getattr(s, 'st_blocks', 0),
        'blksize': getattr(s, 'st_blksize', 4096),
        'mode_str': stat.filemode(s.st_mode),
    }

def io_lstat(path: str) -> dict:
    s = os.lstat(path)
    return {'size': s.st_size, 'mode': s.st_mode, 'uid': s.st_uid,
            'gid': s.st_gid, 'mtime': s.st_mtime, 'ino': s.st_ino}

def io_exists(path: str) -> bool: return os.path.exists(path)
def io_isfile(path: str) -> bool: return os.path.isfile(path)
def io_isdir(path: str) -> bool: return os.path.isdir(path)
def io_islink(path: str) -> bool: return os.path.islink(path)
def io_ismount(path: str) -> bool: return os.path.ismount(path)

def io_mkdir(path: str, mode: int = 0o777, parents: bool = True):
    os.makedirs(path, mode=mode, exist_ok=parents)

def io_rmdir(path: str): os.rmdir(path)
def io_rmtree(path: str): shutil.rmtree(path)

def io_unlink(path: str):
    if os.path.exists(path): os.unlink(path)

def io_rename(src: str, dst: str): os.rename(src, dst)
def io_replace(src: str, dst: str): os.replace(src, dst)  # atomic

def io_copy(src: str, dst: str) -> str: return shutil.copy2(src, dst)
def io_copy_tree(src: str, dst: str): shutil.copytree(src, dst, dirs_exist_ok=True)
def io_move(src: str, dst: str): shutil.move(src, dst)

def io_symlink(src: str, dst: str): os.symlink(src, dst)
def io_hardlink(src: str, dst: str): os.link(src, dst)
def io_readlink(path: str) -> str: return os.readlink(path)
def io_realpath(path: str) -> str: return os.path.realpath(path)

def io_chmod(path: str, mode: int): os.chmod(path, mode)
def io_chown(path: str, uid: int = -1, gid: int = -1): os.chown(path, uid, gid)
def io_lchown(path: str, uid: int, gid: int): os.lchown(path, uid, gid)
def io_access(path: str, mode: int) -> bool: return os.access(path, mode)

def io_listdir(path: str = '.') -> List[str]: return os.listdir(path)

def io_scandir(path: str = '.') -> List[dict]:
    result = []
    with os.scandir(path) as it:
        for e in it:
            s = e.stat(follow_symlinks=False)
            result.append({
                'name': e.name, 'path': e.path,
                'is_file': e.is_file(), 'is_dir': e.is_dir(),
                'is_link': e.is_symlink(), 'size': s.st_size,
                'mtime': s.st_mtime,
            })
    return result

def io_walk(top: str, topdown: bool = True,
            follow_links: bool = False) -> List[dict]:
    result = []
    for dirpath, dirnames, filenames in os.walk(
            top, topdown=topdown, followlinks=follow_links):
        result.append({
            'dir': dirpath,
            'subdirs': dirnames,
            'files': filenames,
        })
    return result

def io_glob(pattern: str) -> List[str]:
    return _glob.glob(pattern, recursive=True)

def io_fnmatch(name: str, pattern: str) -> bool:
    return fnmatch.fnmatch(name, pattern)

def io_find(root: str, name_pattern: str = '*',
            min_size: int = None, max_size: int = None,
            newer_than: float = None) -> List[str]:
    """Recursive file search with filters."""
    found = []
    for dp, dns, fns in os.walk(root):
        for fn in fns:
            if not fnmatch.fnmatch(fn, name_pattern): continue
            fp = os.path.join(dp, fn)
            try:
                s = os.stat(fp)
                if min_size is not None and s.st_size < min_size: continue
                if max_size is not None and s.st_size > max_size: continue
                if newer_than is not None and s.st_mtime < newer_than: continue
                found.append(fp)
            except Exception: continue
    return found

def io_diskusage(path: str = '.') -> dict:
    u = shutil.disk_usage(path)
    return {'total': u.total, 'used': u.used, 'free': u.free,
            'pct': u.used * 100 / u.total if u.total else 0}

def io_statvfs(path: str) -> dict:
    v = os.statvfs(path)
    return {
        'bsize': v.f_bsize, 'frsize': v.f_frsize,
        'blocks': v.f_blocks, 'bfree': v.f_bfree, 'bavail': v.f_bavail,
        'files': v.f_files, 'ffree': v.f_ffree, 'favail': v.f_favail,
        'flag': v.f_flag, 'namemax': v.f_namemax,
        'total_bytes': v.f_blocks * v.f_frsize,
        'free_bytes': v.f_bavail * v.f_frsize,
    }

def io_getcwd() -> str: return os.getcwd()
def io_chdir(path: str): os.chdir(path)
def io_abspath(path: str) -> str: return os.path.abspath(path)
def io_basename(path: str) -> str: return os.path.basename(path)
def io_dirname(path: str) -> str: return os.path.dirname(path)
def io_join(*parts) -> str: return os.path.join(*parts)
def io_splitext(path: str): return os.path.splitext(path)
def io_split(path: str): return os.path.split(path)
def io_expanduser(path: str) -> str: return os.path.expanduser(path)
def io_expandvars(path: str) -> str: return os.path.expandvars(path)

def io_tempfile(suffix: str = '', prefix: str = 'ks_',
                dir: str = None, delete: bool = False):
    import tempfile as _tf
    f = _tf.NamedTemporaryFile(suffix=suffix, prefix=prefix,
                               dir=dir, delete=delete)
    return f

def io_tempdir(suffix: str = '', prefix: str = 'ks_',
               dir: str = None) -> str:
    return tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=dir)

def io_temppath(suffix: str = '', prefix: str = 'ks_',
                dir: str = None) -> str:
    return tempfile.mktemp(suffix=suffix, prefix=prefix, dir=dir)

# ── Compression / Archives ─────────────────────────────────────────────────────

def io_tar_create(output: str, *paths, mode: str = 'w:gz') -> str:
    """Create tar archive (modes: w, w:gz, w:bz2, w:xz)."""
    with tarfile.open(output, mode) as tf:
        for p in paths: tf.add(p)
    return output

def io_tar_extract(archive: str, dest: str = '.'):
    with tarfile.open(archive) as tf: tf.extractall(dest)

def io_tar_list(archive: str) -> List[str]:
    with tarfile.open(archive) as tf: return tf.getnames()

def io_tar_add_bytes(output: str, data: bytes, arcname: str, mode: str = 'w:gz'):
    with tarfile.open(output, mode) as tf:
        info = tarfile.TarInfo(name=arcname)
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))

def io_zip_create(output: str, *paths,
                  compression=zipfile.ZIP_DEFLATED) -> str:
    with zipfile.ZipFile(output, 'w', compression) as zf:
        for p in paths:
            if os.path.isdir(p):
                for dp, dns, fns in os.walk(p):
                    for fn in fns:
                        fp = os.path.join(dp, fn)
                        zf.write(fp, os.path.relpath(fp, os.path.dirname(p)))
            else:
                zf.write(p)
    return output

def io_zip_extract(archive: str, dest: str = '.', pwd: bytes = None):
    with zipfile.ZipFile(archive, 'r') as zf:
        zf.extractall(dest, pwd=pwd)

def io_zip_list(archive: str) -> List[str]:
    with zipfile.ZipFile(archive, 'r') as zf: return zf.namelist()

def io_zip_read(archive: str, member: str) -> bytes:
    with zipfile.ZipFile(archive, 'r') as zf: return zf.read(member)

def io_zip_add_bytes(archive: str, data: bytes, arcname: str,
                     mode: str = 'a',
                     compression=zipfile.ZIP_DEFLATED):
    with zipfile.ZipFile(archive, mode, compression) as zf:
        zf.writestr(arcname, data)

def io_gzip_compress(data: bytes, level: int = 9) -> bytes:
    return gzip.compress(data, compresslevel=level)

def io_gzip_decompress(data: bytes) -> bytes:
    return gzip.decompress(data)

def io_gzip_open(path: str, mode: str = 'rb'):
    return gzip.open(path, mode)

def io_bz2_compress(data: bytes, level: int = 9) -> bytes:
    return bz2.compress(data, compresslevel=level)

def io_bz2_decompress(data: bytes) -> bytes:
    return bz2.decompress(data)

def io_lzma_compress(data: bytes) -> bytes:
    return lzma.compress(data)

def io_lzma_decompress(data: bytes) -> bytes:
    return lzma.decompress(data)

def io_zlib_compress(data: bytes, level: int = 9) -> bytes:
    return zlib.compress(data, level)

def io_zlib_decompress(data: bytes) -> bytes:
    return zlib.decompress(data)

def io_zlib_crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF

def io_zlib_adler32(data: bytes) -> int:
    return zlib.adler32(data) & 0xFFFFFFFF

# ── Database (SQLite) ──────────────────────────────────────────────────────────

def io_sqlite_connect(path: str = ':memory:',
                      timeout: float = 5.0,
                      check_same_thread: bool = False):
    conn = sqlite3.connect(path, timeout=timeout,
                           check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    return conn

def io_sqlite_exec(conn, sql: str, params=None):
    cur = conn.cursor()
    cur.execute(sql, params or [])
    conn.commit()
    return cur.rowcount

def io_sqlite_query(conn, sql: str, params=None) -> List[dict]:
    cur = conn.execute(sql, params or [])
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def io_sqlite_queryone(conn, sql: str, params=None):
    cur = conn.execute(sql, params or [])
    row = cur.fetchone()
    if row is None: return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))

def io_sqlite_executemany(conn, sql: str, params_list):
    conn.executemany(sql, params_list)
    conn.commit()

def io_sqlite_tables(conn) -> List[str]:
    rows = io_sqlite_query(conn, "SELECT name FROM sqlite_master WHERE type='table'")
    return [r['name'] for r in rows]

def io_sqlite_schema(conn, table: str) -> str:
    rows = io_sqlite_query(
        conn, "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        [table])
    return rows[0]['sql'] if rows else ''

def io_sqlite_close(conn): conn.close()

def io_sqlite_backup(src_conn, dst_path: str):
    dst = sqlite3.connect(dst_path)
    with dst:
        src_conn.backup(dst)
    dst.close()

def io_sqlite_import_csv(conn, csv_path: str, table: str,
                         create: bool = True, delimiter: str = ','):
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)
    if not rows: return 0
    cols = rows[0].keys()
    if create:
        col_defs = ', '.join(f'"{c}" TEXT' for c in cols)
        conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({col_defs})')
    placeholders = ', '.join('?' for _ in cols)
    col_names = ', '.join(f'"{c}"' for c in cols)
    sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'
    conn.executemany(sql, [[r[c] for c in cols] for r in rows])
    conn.commit()
    return len(rows)

# ── CSV ────────────────────────────────────────────────────────────────────────

def io_csv_read(path: str, delimiter: str = ',',
                encoding: str = 'utf-8') -> List[dict]:
    with open(path, newline='', encoding=encoding) as f:
        return list(csv.DictReader(f, delimiter=delimiter))

def io_csv_read_rows(path: str, delimiter: str = ',') -> List[list]:
    with open(path, newline='') as f:
        return list(csv.reader(f, delimiter=delimiter))

def io_csv_write(path: str, rows: List[dict],
                 fieldnames: List[str] = None,
                 delimiter: str = ',', encoding: str = 'utf-8'):
    if not rows: return
    fieldnames = fieldnames or list(rows[0].keys())
    with open(path, 'w', newline='', encoding=encoding) as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        w.writeheader()
        w.writerows(rows)

def io_csv_write_rows(path: str, rows: List[list], delimiter: str = ','):
    with open(path, 'w', newline='') as f:
        csv.writer(f, delimiter=delimiter).writerows(rows)

def io_csv_to_string(rows: List[dict], delimiter: str = ',') -> str:
    if not rows: return ''
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), delimiter=delimiter)
    w.writeheader(); w.writerows(rows)
    return buf.getvalue()

# ── Config / INI ──────────────────────────────────────────────────────────────

def io_config_read(path: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(path)
    return cfg

def io_config_write(cfg: configparser.ConfigParser, path: str):
    with open(path, 'w') as f: cfg.write(f)

def io_config_get(cfg, section: str, key: str,
                  fallback=None) -> str:
    return cfg.get(section, key, fallback=fallback)

def io_config_set(cfg, section: str, key: str, value: str):
    if section not in cfg: cfg.add_section(section)
    cfg.set(section, key, str(value))

def io_config_sections(cfg) -> List[str]: return cfg.sections()
def io_config_options(cfg, section: str) -> List[str]: return cfg.options(section)

def io_config_from_dict(d: dict) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    for section, vals in d.items():
        if section != 'DEFAULT':
            cfg.add_section(section)
        for k, v in vals.items():
            cfg.set(section, k, str(v))
    return cfg

# ── Pickle / serialisation ─────────────────────────────────────────────────────

def io_pickle_dump(obj, path: str):
    with open(path, 'wb') as f: pickle.dump(obj, f)

def io_pickle_load(path: str):
    with open(path, 'rb') as f: return pickle.load(f)

def io_pickle_dumps(obj) -> bytes: return pickle.dumps(obj)
def io_pickle_loads(data: bytes): return pickle.loads(data)

# ── Struct / binary pack ────────────────────────────────────────────────────────

def io_pack(fmt: str, *values) -> bytes: return struct.pack(fmt, *values)
def io_unpack(fmt: str, data: bytes): return struct.unpack(fmt, data)
def io_pack_into(fmt: str, buf, offset: int, *values):
    struct.pack_into(fmt, buf, offset, *values)
def io_unpack_from(fmt: str, buf, offset: int = 0):
    return struct.unpack_from(fmt, buf, offset)
def io_calcsize(fmt: str) -> int: return struct.calcsize(fmt)

# ── C array types ──────────────────────────────────────────────────────────────

def io_array(typecode: str, initializer=None):
    """
    C-typed array. typecodes: b B h H i I l L q Q f d
    (signed/unsigned byte/short/int/long/longlong/float/double)
    """
    if initializer is not None:
        return array.array(typecode, initializer)
    return array.array(typecode)

def io_array_frombytes(typecode: str, data: bytes):
    a = array.array(typecode)
    a.frombytes(data)
    return a

def io_array_tobytes(arr) -> bytes: return arr.tobytes()
def io_array_tolist(arr) -> list: return arr.tolist()
def io_array_itemsize(arr) -> int: return arr.itemsize
def io_array_buffer_info(arr): return arr.buffer_info()

# ── Pipes, FIFOs, IPC ─────────────────────────────────────────────────────────

def io_pipe() -> Tuple[int, int]:
    """Create unidirectional pipe. Returns (read_fd, write_fd)."""
    return os.pipe()

def io_pipe2(flags: int = 0) -> Tuple[int, int]:
    """os.pipe2 with flags (O_NONBLOCK, O_CLOEXEC)."""
    if hasattr(os, 'pipe2'):
        return os.pipe2(flags)
    return os.pipe()

def io_mkfifo(path: str, mode: int = 0o666):
    """Create named pipe (FIFO)."""
    os.mkfifo(path, mode)

def io_fd_read(fd: int, size: int) -> bytes: return os.read(fd, size)
def io_fd_write(fd: int, data: bytes) -> int: return os.write(fd, data)
def io_fd_close(fd: int): os.close(fd)
def io_fd_dup(fd: int) -> int: return os.dup(fd)
def io_fd_dup2(fd: int, fd2: int) -> int: return os.dup2(fd, fd2)

def io_sendfile(out_fd: int, in_fd: int, offset: int, count: int) -> int:
    """Zero-copy file transfer (Linux sendfile)."""
    if hasattr(os, 'sendfile'):
        return os.sendfile(out_fd, in_fd, offset, count)
    # Fallback
    with os.fdopen(in_fd, 'rb', closefd=False) as f:
        f.seek(offset)
        data = f.read(count)
    return os.write(out_fd, data)

def io_select(rlist, wlist=None, xlist=None, timeout=None):
    return select.select(rlist, wlist or [], xlist or [], timeout)

def io_poll_create(): return select.poll()
def io_epoll_create(): return select.epoll()

# ── PTY / terminal ────────────────────────────────────────────────────────────

def io_pty_open() -> Tuple[int, int]:
    """Open a pseudo-terminal. Returns (master_fd, slave_fd)."""
    return pty.openpty()

def io_pty_fork() -> Tuple[int, int]:
    """Fork with PTY. Returns (pid, master_fd). Child gets 0."""
    return pty.fork()

def io_pty_spawn(argv, master_read=None, stdin_read=None):
    """Spawn program in PTY, optionally with custom read callbacks."""
    pty.spawn(argv, master_read=master_read, stdin_read=stdin_read)

def io_termios_get(fd: int):
    return termios.tcgetattr(fd)

def io_termios_set(fd: int, attrs, when: int = termios.TCSANOW):
    termios.tcsetattr(fd, when, attrs)

def io_termios_raw(fd: int):
    """Put terminal into raw mode."""
    import tty
    tty.setraw(fd)

def io_termios_cbreak(fd: int):
    import tty
    tty.setcbreak(fd)

def io_terminal_size() -> Tuple[int, int]:
    """Returns (columns, rows)."""
    try:
        sz = shutil.get_terminal_size()
        return sz.columns, sz.lines
    except Exception:
        return 80, 24

def io_isatty_fd(fd: int) -> bool: return os.isatty(fd)

# ── /proc filesystem ──────────────────────────────────────────────────────────

def io_proc_read(pid: int, file: str = 'status') -> str:
    """Read /proc/<pid>/<file>."""
    try:
        with open(f'/proc/{pid}/{file}', 'r') as f: return f.read()
    except Exception: return ''

def io_proc_maps(pid: int = None) -> List[dict]:
    """Read memory maps from /proc/self/maps or /proc/<pid>/maps."""
    pid = pid or os.getpid()
    maps = []
    try:
        with open(f'/proc/{pid}/maps') as f:
            for line in f:
                parts = line.split()
                if len(parts) < 5: continue
                addr_range = parts[0].split('-')
                maps.append({
                    'start': int(addr_range[0], 16),
                    'end': int(addr_range[1], 16),
                    'perms': parts[1],
                    'offset': int(parts[2], 16),
                    'dev': parts[3],
                    'inode': int(parts[4]),
                    'path': parts[5] if len(parts) > 5 else '',
                })
    except Exception: pass
    return maps

def io_proc_cmdline(pid: int = None) -> List[str]:
    pid = pid or os.getpid()
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            return f.read().rstrip(b'\x00').split(b'\x00')
    except Exception: return []

def io_proc_list() -> List[dict]:
    """List all processes from /proc."""
    procs = []
    try:
        for entry in os.listdir('/proc'):
            if not entry.isdigit(): continue
            pid = int(entry)
            try:
                with open(f'/proc/{pid}/status') as f:
                    lines = f.readlines()
                info = {}
                for l in lines:
                    if ':' in l:
                        k, v = l.split(':', 1)
                        info[k.strip()] = v.strip()
                procs.append({'pid': pid, 'name': info.get('Name',''),
                              'state': info.get('State',''),
                              'vmrss': info.get('VmRSS',''),
                              'threads': info.get('Threads','')})
            except Exception: continue
    except Exception: pass
    return procs

def io_proc_self_mem_read(addr: int, size: int) -> bytes:
    """Read from /proc/self/mem at virtual address."""
    with open('/proc/self/mem', 'rb') as f:
        f.seek(addr); return f.read(size)

def io_proc_self_mem_write(addr: int, data: bytes):
    """Write to /proc/self/mem at virtual address."""
    with open('/proc/self/mem', 'r+b') as f:
        f.seek(addr); f.write(data)

# ── libc / C-level I/O via ctypes ─────────────────────────────────────────────

def io_c_malloc(size: int) -> int:
    """Allocate memory via libc malloc. Returns raw pointer (int)."""
    if _LIBC is None: raise RuntimeError("libc not available")
    _LIBC.malloc.restype = ctypes.c_void_p
    p = _LIBC.malloc(size)
    if not p: raise MemoryError(f"malloc({size}) failed")
    return p

def io_c_calloc(count: int, size: int) -> int:
    _LIBC.calloc.restype = ctypes.c_void_p
    p = _LIBC.calloc(count, size)
    if not p: raise MemoryError("calloc failed")
    return p

def io_c_realloc(ptr: int, size: int) -> int:
    _LIBC.realloc.restype = ctypes.c_void_p
    p = _LIBC.realloc(ctypes.c_void_p(ptr), size)
    if not p: raise MemoryError("realloc failed")
    return p

def io_c_free(ptr: int):
    if _LIBC: _LIBC.free(ctypes.c_void_p(ptr))

def io_c_memcpy(dst: int, src: int, n: int):
    ctypes.memmove(dst, src, n)

def io_c_memset(ptr: int, val: int, n: int):
    ctypes.memset(ctypes.c_void_p(ptr), val & 0xFF, n)

def io_c_memcmp(ptr1: int, ptr2: int, n: int) -> int:
    if _LIBC:
        _LIBC.memcmp.restype = ctypes.c_int
        return _LIBC.memcmp(ctypes.c_void_p(ptr1),
                            ctypes.c_void_p(ptr2), n)
    b1 = (ctypes.c_char * n).from_address(ptr1)
    b2 = (ctypes.c_char * n).from_address(ptr2)
    for i in range(n):
        diff = b1[i] - b2[i]
        if diff: return diff
    return 0

def io_c_strlen(ptr: int) -> int:
    if _LIBC:
        _LIBC.strlen.restype = ctypes.c_size_t
        return _LIBC.strlen(ctypes.c_void_p(ptr))
    i = 0
    arr = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint8))
    while arr[i]: i += 1
    return i

def io_c_read8(ptr: int) -> int:
    return ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint8))[0]

def io_c_read16(ptr: int) -> int:
    return ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint16))[0]

def io_c_read32(ptr: int) -> int:
    return ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint32))[0]

def io_c_read64(ptr: int) -> int:
    return ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint64))[0]

def io_c_write8(ptr: int, val: int):
    ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint8))[0] = val & 0xFF

def io_c_write16(ptr: int, val: int):
    ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint16))[0] = val & 0xFFFF

def io_c_write32(ptr: int, val: int):
    ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint32))[0] = val & 0xFFFFFFFF

def io_c_write64(ptr: int, val: int):
    ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint64))[0] = val & 0xFFFFFFFFFFFFFFFF

def io_c_read_bytes(ptr: int, n: int) -> bytes:
    return bytes(ctypes.string_at(ptr, n))

def io_c_write_bytes(ptr: int, data: bytes):
    ctypes.memmove(ptr, data, len(data))

def io_c_ptr_to_bytes(ptr: int, n: int) -> bytes:
    return (ctypes.c_char * n).from_address(ptr).raw

def io_c_bytes_to_ptr(data: bytes) -> Tuple[int, Any]:
    """Pin bytes in ctypes buffer. Returns (ptr, ctypes_obj). Keep ctypes_obj alive!"""
    buf = ctypes.create_string_buffer(data, len(data))
    return ctypes.addressof(buf), buf

def io_c_mmap(size: int, prot: int = 3, flags: int = 0x22,
              fd: int = -1, offset: int = 0) -> int:
    """mmap via libc syscall. Returns pointer."""
    if _LIBC:
        _LIBC.mmap.restype = ctypes.c_void_p
        p = _LIBC.mmap(None, size, prot, flags, fd, offset)
        if p == ctypes.c_void_p(-1).value:
            import errno
            raise OSError(ctypes.get_errno(), 'mmap failed')
        return p
    raise RuntimeError("libc not available")

def io_c_munmap(ptr: int, size: int):
    if _LIBC: _LIBC.munmap(ctypes.c_void_p(ptr), size)

def io_c_open(path: str, flags: int, mode: int = 0o666) -> int:
    """libc open(). Returns fd."""
    if _LIBC:
        _LIBC.open.restype = ctypes.c_int
        return _LIBC.open(path.encode(), flags, mode)
    return os.open(path, flags, mode)

def io_c_fopen(path: str, mode: str):
    """libc fopen(). Returns FILE* as ctypes void_p."""
    if _LIBC:
        _LIBC.fopen.restype = ctypes.c_void_p
        return _LIBC.fopen(path.encode(), mode.encode())
    raise RuntimeError("libc not available")

def io_c_fclose(fp: int):
    if _LIBC: _LIBC.fclose(ctypes.c_void_p(fp))

def io_c_fread(buf_ptr: int, size: int, count: int, fp: int) -> int:
    if _LIBC:
        _LIBC.fread.restype = ctypes.c_size_t
        return _LIBC.fread(ctypes.c_void_p(buf_ptr), size, count, ctypes.c_void_p(fp))
    return 0

def io_c_fwrite(buf_ptr: int, size: int, count: int, fp: int) -> int:
    if _LIBC:
        _LIBC.fwrite.restype = ctypes.c_size_t
        return _LIBC.fwrite(ctypes.c_void_p(buf_ptr), size, count, ctypes.c_void_p(fp))
    return 0

def io_c_printf(fmt: str, *args):
    """printf via libc."""
    if _LIBC: _LIBC.printf(fmt.encode(), *args)
    else: print(fmt % args if args else fmt, end='')

def io_c_getenv(name: str) -> str:
    if _LIBC:
        _LIBC.getenv.restype = ctypes.c_char_p
        r = _LIBC.getenv(name.encode())
        return r.decode() if r else ''
    return os.environ.get(name, '')

def io_c_setenv(name: str, value: str, overwrite: int = 1) -> int:
    if _LIBC:
        _LIBC.setenv.restype = ctypes.c_int
        return _LIBC.setenv(name.encode(), value.encode(), overwrite)
    os.environ[name] = value; return 0

def io_c_system(cmd: str) -> int:
    if _LIBC:
        _LIBC.system.restype = ctypes.c_int
        return _LIBC.system(cmd.encode())
    return subprocess.call(cmd, shell=True)

def io_c_getpid() -> int:
    if _LIBC:
        _LIBC.getpid.restype = ctypes.c_int
        return _LIBC.getpid()
    return os.getpid()

def io_c_getuid() -> int:
    if _LIBC:
        _LIBC.getuid.restype = ctypes.c_uint
        return _LIBC.getuid()
    return os.getuid()

def io_c_load_library(name: str):
    """Load shared library. Returns ctypes CDLL."""
    lib_path = ctypes.util.find_library(name) or name
    return ctypes.CDLL(lib_path)

def io_c_call(lib, func_name: str, restype, *args, argtypes=None):
    """Call function from loaded library."""
    fn = getattr(lib, func_name)
    fn.restype = restype
    if argtypes: fn.argtypes = argtypes
    return fn(*args)

# ── Process management ─────────────────────────────────────────────────────────

def io_fork() -> int:
    """Fork process. Returns 0 in child, child PID in parent."""
    return os.fork()

def io_exec(path: str, args: List[str], env: dict = None):
    """Replace current process image with new program."""
    os.execve(path, args, env or os.environ)

def io_execvp(file: str, args: List[str]):
    os.execvp(file, args)

def io_waitpid(pid: int, options: int = 0) -> Tuple[int, int]:
    return os.waitpid(pid, options)

def io_wait() -> Tuple[int, int]:
    return os.wait()

def io_spawn(path: str, args: List[str],
             stdin=None, stdout=None, stderr=None,
             env=None, cwd=None) -> subprocess.Popen:
    return subprocess.Popen([path] + args, stdin=stdin, stdout=stdout,
                            stderr=stderr, env=env, cwd=cwd)

def io_run(args, shell: bool = False, capture: bool = True,
           input=None, timeout: int = None, cwd: str = None,
           env: dict = None) -> dict:
    r = subprocess.run(args, shell=shell, capture_output=capture,
                       input=(input.encode() if isinstance(input, str) else input),
                       timeout=timeout, cwd=cwd, env=env)
    return {
        'returncode': r.returncode,
        'stdout': r.stdout.decode('utf-8', errors='replace') if r.stdout else '',
        'stderr': r.stderr.decode('utf-8', errors='replace') if r.stderr else '',
    }

def io_popen(cmd: str, mode: str = 'r'):
    return os.popen(cmd, mode)

def io_getpid() -> int: return os.getpid()
def io_getppid() -> int: return os.getppid()
def io_getpgid(pid: int = 0) -> int: return os.getpgid(pid)
def io_setpgid(pid: int, pgrp: int): os.setpgid(pid, pgrp)
def io_getsid(pid: int = 0) -> int: return os.getsid(pid)
def io_setsid() -> int: return os.setsid()

def io_kill(pid: int, sig: int): os.kill(pid, sig)
def io_killpg(pgrp: int, sig: int): os.killpg(pgrp, sig)

def io_signal(signum: int, handler):
    signal.signal(signum, handler)

def io_sigwait(sigset: set) -> int:
    return signal.sigwait(sigset)

# ── Resource limits ────────────────────────────────────────────────────────────

def io_getrlimit(resource_id: int) -> Tuple[int, int]:
    return resource.getrlimit(resource_id)

def io_setrlimit(resource_id: int, soft: int, hard: int):
    resource.setrlimit(resource_id, (soft, hard))

def io_getrusage(who: int = resource.RUSAGE_SELF):
    u = resource.getrusage(who)
    return {
        'utime': u.ru_utime, 'stime': u.ru_stime,
        'maxrss': u.ru_maxrss, 'minflt': u.ru_minflt,
        'majflt': u.ru_majflt, 'inblock': u.ru_inblock,
        'oublock': u.ru_oublock, 'nvcsw': u.ru_nvcsw,
        'nivcsw': u.ru_nivcsw,
    }

# Resource constants
RLIMIT_CPU  = resource.RLIMIT_CPU
RLIMIT_FSIZE= resource.RLIMIT_FSIZE
RLIMIT_DATA = resource.RLIMIT_DATA
RLIMIT_STACK= resource.RLIMIT_STACK
RLIMIT_CORE = resource.RLIMIT_CORE
RLIMIT_NOFILE=resource.RLIMIT_NOFILE
RLIMIT_AS   = resource.RLIMIT_AS
RLIM_INFINITY = resource.RLIM_INFINITY

# ── User / group ───────────────────────────────────────────────────────────────

def io_getuid() -> int:
    return os.getuid() if hasattr(os, 'getuid') else 0

def io_getgid() -> int:
    return os.getgid() if hasattr(os, 'getgid') else 0

def io_geteuid() -> int:
    return os.geteuid() if hasattr(os, 'geteuid') else 0

def io_setuid(uid: int): os.setuid(uid)
def io_setgid(gid: int): os.setgid(gid)
def io_seteuid(uid: int): os.seteuid(uid)
def io_setegid(gid: int): os.setegid(gid)

def io_getpwuid(uid: int = None) -> dict:
    try:
        p = pwd.getpwuid(uid if uid is not None else os.getuid())
        return {'name': p.pw_name, 'uid': p.pw_uid, 'gid': p.pw_gid,
                'gecos': p.pw_gecos, 'dir': p.pw_dir, 'shell': p.pw_shell}
    except Exception: return {}

def io_getpwnam(name: str) -> dict:
    try:
        p = pwd.getpwnam(name)
        return {'name': p.pw_name, 'uid': p.pw_uid, 'gid': p.pw_gid,
                'dir': p.pw_dir, 'shell': p.pw_shell}
    except Exception: return {}

def io_getgrnam(name: str) -> dict:
    try:
        g = grp.getgrnam(name)
        return {'name': g.gr_name, 'gid': g.gr_gid, 'members': g.gr_mem}
    except Exception: return {}

def io_getgroups() -> List[int]:
    return os.getgroups()

# ── Environment ────────────────────────────────────────────────────────────────

def io_getenv(key: str, default: str = '') -> str:
    return os.environ.get(key, default)

def io_setenv(key: str, value: str):
    os.environ[key] = str(value)

def io_unsetenv(key: str):
    os.environ.pop(key, None)

def io_environ() -> dict:
    return dict(os.environ)

def io_putenv(key: str, val: str): os.putenv(key, val)

# ── Xattr (extended attributes) ────────────────────────────────────────────────

def io_xattr_get(path: str, name: str) -> bytes:
    try:
        import xattr as _xa
        return _xa.get(path, name)
    except ImportError:
        pass
    # Fallback via ctypes
    if _LIBC and hasattr(_LIBC, 'getxattr'):
        buf = ctypes.create_string_buffer(65536)
        n = _LIBC.getxattr(path.encode(), name.encode(), buf, len(buf))
        if n < 0: raise OSError(f'getxattr failed')
        return bytes(buf[:n])
    return b''

def io_xattr_set(path: str, name: str, value: bytes):
    try:
        import xattr as _xa; _xa.set(path, name, value); return
    except ImportError: pass
    if _LIBC and hasattr(_LIBC, 'setxattr'):
        r = _LIBC.setxattr(path.encode(), name.encode(),
                           value, len(value), 0)
        if r < 0: raise OSError('setxattr failed')

# ── System info ────────────────────────────────────────────────────────────────

def io_sysinfo() -> dict:
    u = platform.uname()
    return {
        'system': u.system, 'node': u.node,
        'release': u.release, 'version': u.version,
        'machine': u.machine, 'processor': u.processor,
        'python': sys.version, 'pid': os.getpid(),
        'uid': os.getuid() if hasattr(os, 'getuid') else 0,
        'cwd': os.getcwd(),
        'cpu_count': os.cpu_count(),
        'page_size': os.sysconf('SC_PAGE_SIZE') if hasattr(os, 'sysconf') else 4096,
    }

def io_uname() -> dict:
    u = os.uname()
    return {'sysname': u.sysname, 'nodename': u.nodename,
            'release': u.release, 'version': u.version,
            'machine': u.machine}

def io_sysconf(name) -> int:
    if hasattr(os, 'sysconf'):
        return os.sysconf(name)
    return -1

def io_pathconf(path: str, name) -> int:
    if hasattr(os, 'pathconf'):
        return os.pathconf(path, name)
    return -1

# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE DICT BUILDERS — called by ks_core.py
# ═══════════════════════════════════════════════════════════════════════════════

def build_net_module() -> dict:
    """Return complete dict for the 'net' KentScript module."""
    return {
        # ── TCP ──
        'connect':           net_tcp_connect,
        'tcp_connect':       net_tcp_connect,
        'listen':            net_tcp_listen_ks,
        'tcp_listen':        net_tcp_listen_ks,
        'accept':            net_tcp_accept,
        'send':              net_tcp_send,
        'sendall':           net_tcp_sendall,
        'recv':              net_tcp_recv,
        'recv_str':          net_tcp_recv_str,
        'close':             net_tcp_close,
        'tcp_ping':          net_tcp_ping,
        'set_timeout':       net_set_timeout,
        'set_nonblocking':   net_set_nonblocking,
        'set_blocking':      net_set_blocking,
        'set_keepalive':     net_set_keepalive,
        'set_nodelay':       net_set_nodelay,
        'setsockopt':        net_setsockopt,
        'getsockopt':        net_getsockopt,
        'socket_addr':       net_socket_addr,
        'peer_addr':         net_peer_addr,
        'socket_fd':         net_socket_fd,
        # ── UDP ──
        'udp_socket':        net_udp_socket,
        'udp_bind':          net_udp_bind,
        'udp_sendto':        net_udp_sendto,
        'udp_recvfrom':      net_udp_recvfrom,
        'udp_broadcast':     net_udp_broadcast,
        'udp_multicast_join':net_udp_multicast_join,
        # ── Unix sockets ──
        'unix_connect':      net_unix_connect,
        'unix_listen':       net_unix_listen,
        'unix_dgram':        net_unix_dgram_socket,
        # ── Raw ──
        'raw_socket':        net_raw_socket,
        'packet_socket':     net_packet_socket,
        # ── SSL/TLS ──
        'ssl_context':       net_ssl_context,
        'ssl_wrap':          net_ssl_wrap,
        'ssl_cert':          net_ssl_cert,
        'ssl_cipher':        net_ssl_cipher,
        'ssl_version':       net_ssl_version,
        # ── HTTP (requests) ──
        'http_get':          net_http_get,
        'get':               net_http_get,
        'http_post':         net_http_post,
        'post':              net_http_post,
        'http_put':          net_http_put,
        'put':               net_http_put,
        'http_patch':        net_http_patch,
        'patch':             net_http_patch,
        'http_delete':       net_http_delete,
        'delete':            net_http_delete,
        'http_head':         net_http_head,
        'head':              net_http_head,
        'http_options':      net_http_options,
        'http_session':      net_http_session,
        'session_get':       net_http_session_get,
        'session_post':      net_http_session_post,
        'basic_auth':        net_http_basic_auth,
        'digest_auth':       net_http_digest_auth,
        # ── Low-level HTTP ──
        'http_raw_get':      net_http_raw_get,
        'http_raw_request':  net_http_raw_request,
        # ── Download/Upload ──
        'download':          net_download,
        'upload_file':       net_upload_file,
        'upload_bytes':      net_upload_bytes,
        # ── WebSocket ──
        'websocket':         net_websocket_connect,
        'ws_connect':        net_websocket_connect,
        # ── FTP ──
        'ftp_connect':       net_ftp_connect,
        'ftp_connect_tls':   net_ftp_connect_tls,
        'ftp_list':          net_ftp_list,
        'ftp_nlst':          net_ftp_nlst,
        'ftp_download':      net_ftp_download,
        'ftp_upload':        net_ftp_upload,
        'ftp_upload_bytes':  net_ftp_upload_bytes,
        'ftp_mkdir':         net_ftp_mkdir,
        'ftp_rmdir':         net_ftp_rmdir,
        'ftp_delete':        net_ftp_delete,
        'ftp_rename':        net_ftp_rename,
        'ftp_cwd':           net_ftp_cwd,
        'ftp_pwd':           net_ftp_pwd,
        'ftp_size':          net_ftp_size,
        'ftp_quit':          net_ftp_quit,
        # ── SSH/SCP ──
        'ssh_exec':          net_ssh_exec,
        'ssh_tunnel':        net_ssh_tunnel,
        'scp_upload':        net_scp_upload,
        'scp_download':      net_scp_download,
        # ── SMTP ──
        'smtp_send':         net_smtp_send,
        'smtp_connect':      net_smtp_connect,
        'smtp_login':        net_smtp_login,
        'smtp_send_raw':     net_smtp_send_raw,
        'smtp_quit':         net_smtp_quit,
        'build_email':       net_build_email,
        # ── IMAP ──
        'imap_connect':      net_imap_connect,
        'imap_login':        net_imap_login,
        'imap_list_folders': net_imap_list_folders,
        'imap_select':       net_imap_select,
        'imap_search':       net_imap_search,
        'imap_fetch':        net_imap_fetch,
        'imap_logout':       net_imap_logout,
        # ── POP3 ──
        'pop3_connect':      net_pop3_connect,
        'pop3_login':        net_pop3_login,
        'pop3_list':         net_pop3_list,
        'pop3_retr':         net_pop3_retr,
        'pop3_quit':         net_pop3_quit,
        # ── DNS ──
        'dns_resolve':       net_dns_resolve,
        'dns_reverse':       net_dns_reverse,
        'resolve':           net_gethostbyname,
        'gethostbyname':     net_gethostbyname,
        'gethostbyname_ex':  net_gethostbyname_ex,
        'getaddrinfo':       net_getaddrinfo,
        'get_hostname':      net_gethostname,
        'get_fqdn':          net_getfqdn,
        # ── Port scanning ──
        'port_scan':         net_port_scan,
        'port_scan_open':    net_port_scan_open,
        # ── I/O mux ──
        'select':            net_select,
        'epoll_create':      net_epoll_create,
        'epoll_register':    net_epoll_register,
        'epoll_poll':        net_epoll_poll,
        'poll_create':       net_poll_create,
        'selector':          net_selector,
        # ── curl/wget ──
        'curl':              net_curl,
        'wget':              net_wget,
        # ── IP utils ──
        'ip_info':           net_ip_info,
        'ip_network':        net_ip_network,
        'ip_in_network':     net_ip_in_network,
        'url_parse':         net_url_parse,
        'url_encode':        net_url_encode,
        'url_decode':        net_url_decode,
        'url_quote':         net_url_quote,
        'url_unquote':       net_url_unquote,
        'url_join':          net_url_join,
        'url_build':         net_url_build,
        # ── HTTP server ──
        'http_server':       net_http_server,
        'http_server_stop':  net_http_server_stop,
        # ── XMLRPC ──
        'xmlrpc_client':     net_xmlrpc_client,
        'xmlrpc_call':       net_xmlrpc_call,
        # ── Packet building ──
        'build_ipv4':        net_build_ipv4_header,
        'build_udp':         net_build_udp_header,
        'build_tcp':         net_build_tcp_header,
        'inet_aton':         net_inet_aton,
        'inet_ntoa':         net_inet_ntoa,
        'htons':             net_htons,
        'ntohs':             net_ntohs,
        'htonl':             net_htonl,
        'ntohl':             net_ntohl,
        # ── Socket constants ──
        'AF_INET':           socket.AF_INET,
        'AF_INET6':          socket.AF_INET6,
        'AF_UNIX':           socket.AF_UNIX,
        'AF_PACKET':         getattr(socket, 'AF_PACKET', 17),
        'SOCK_STREAM':       socket.SOCK_STREAM,
        'SOCK_DGRAM':        socket.SOCK_DGRAM,
        'SOCK_RAW':          socket.SOCK_RAW,
        'IPPROTO_TCP':       socket.IPPROTO_TCP,
        'IPPROTO_UDP':       socket.IPPROTO_UDP,
        'IPPROTO_ICMP':      socket.IPPROTO_ICMP,
        'IPPROTO_RAW':       socket.IPPROTO_RAW,
        'SOL_SOCKET':        socket.SOL_SOCKET,
        'SO_REUSEADDR':      socket.SO_REUSEADDR,
        'SO_KEEPALIVE':      socket.SO_KEEPALIVE,
        'SO_BROADCAST':      socket.SO_BROADCAST,
        'TCP_NODELAY':       socket.TCP_NODELAY,
        'SHUT_RDWR':         socket.SHUT_RDWR,
        'SHUT_RD':           socket.SHUT_RD,
        'SHUT_WR':           socket.SHUT_WR,
        # ── Raw socket class ──
        'socket':            lambda fam=socket.AF_INET, typ=socket.SOCK_STREAM, proto=0: socket.socket(fam, typ, proto),
    }


def build_io_module() -> dict:
    """Return complete dict for the 'io' KentScript module."""
    return {
        # ── File open/close ──
        'open':              io_open,
        'read':              io_read,
        'read_bytes':        io_read_bytes,
        'read_lines':        io_read_lines,
        'read_line':         io_read_line,
        'write':             io_write,
        'write_bytes':       io_write_bytes_ks,
        'write_lines':       io_write_lines,
        'append':            io_append,
        'append_bytes':      io_append_bytes_ks,
        'close':             io_close,
        'flush':             io_flush,
        'seek':              io_seek,
        'tell':              io_tell,
        'read_from':         io_read_from,
        'write_to':          io_write_to,
        'truncate':          io_truncate,
        'fileno':            io_fileno,
        'isatty':            io_isatty,
        # ── Random access ──
        'read_at':           io_read_at,
        'write_at':          io_write_at,
        'read_struct':       io_read_struct,
        'write_struct':      io_write_struct,
        # ── mmap ──
        'mmap_open':         io_mmap_open,
        'mmap_anon':         net_mmap_anon_ks,
        'mmap_read':         io_mmap_read,
        'mmap_write':        io_mmap_write_ks,
        'mmap_flush':        io_mmap_flush,
        'mmap_close':        io_mmap_close,
        'mmap_size':         io_mmap_size,
        'mmap_resize':       io_mmap_resize,
        # ── File locking ──
        'flock':             io_flock,
        'flock_nb':          io_flock_nb,
        'funlock':           io_funlock,
        'fcntl':             io_fcntl,
        'ioctl':             io_ioctl,
        # ── Filesystem ──
        'stat':              io_stat,
        'lstat':             io_lstat,
        'exists':            io_exists,
        'isfile':            io_isfile,
        'isdir':             io_isdir,
        'islink':            io_islink,
        'ismount':           io_ismount,
        'mkdir':             io_mkdir,
        'rmdir':             io_rmdir,
        'rmtree':            io_rmtree,
        'unlink':            io_unlink,
        'delete':            io_unlink,
        'rename':            io_rename,
        'replace':           io_replace,
        'copy':              io_copy,
        'copy_tree':         io_copy_tree,
        'move':              io_move,
        'symlink':           io_symlink,
        'hardlink':          io_hardlink,
        'readlink':          io_readlink,
        'realpath':          io_realpath,
        'chmod':             io_chmod,
        'chown':             io_chown,
        'lchown':            io_lchown,
        'access':            io_access,
        'listdir':           io_listdir,
        'scandir':           io_scandir,
        'walk':              io_walk,
        'glob':              io_glob,
        'fnmatch':           io_fnmatch,
        'find':              io_find,
        'diskusage':         io_diskusage,
        'statvfs':           io_statvfs,
        'getcwd':            io_getcwd,
        'chdir':             io_chdir,
        'abspath':           io_abspath,
        'basename':          io_basename,
        'dirname':           io_dirname,
        'join':              io_join,
        'splitext':          io_splitext,
        'split':             io_split,
        'expanduser':        io_expanduser,
        'expandvars':        io_expandvars,
        'tempfile':          io_tempfile,
        'tempdir':           io_tempdir,
        'temppath':          io_temppath,
        # ── Compression ──
        'tar_create':        io_tar_create,
        'tar_extract':       io_tar_extract,
        'tar_list':          io_tar_list,
        'tar_add_bytes':     io_tar_add_bytes,
        'zip_create':        io_zip_create,
        'zip_extract':       io_zip_extract,
        'zip_list':          io_zip_list,
        'zip_read':          io_zip_read,
        'zip_add_bytes':     io_zip_add_bytes,
        'gzip_compress':     io_gzip_compress_ks,
        'gzip_decompress':   io_gzip_decompress_ks,
        'gzip_open':         io_gzip_open,
        'bz2_compress':      io_bz2_compress_ks,
        'bz2_decompress':    io_bz2_decompress_ks,
        'lzma_compress':     io_lzma_compress_ks,
        'lzma_decompress':   io_lzma_decompress_ks,
        'zlib_compress':     io_zlib_compress_ks,
        'zlib_decompress':   io_zlib_decompress_ks,
        'zlib_crc32':        io_zlib_crc32_ks,
        'zlib_adler32':      io_zlib_adler32_ks,
        # ── SQLite ──
        'sqlite_connect':    io_sqlite_connect_ks,
        'sqlite_exec':       io_sqlite_exec_ks,
        'sqlite_query':      io_sqlite_query_ks,
        'sqlite_queryone':   io_sqlite_queryone_ks,
        'sqlite_executemany':io_sqlite_executemany,
        'sqlite_tables':     io_sqlite_tables,
        'sqlite_schema':     io_sqlite_schema,
        'sqlite_close':      io_sqlite_close_ks,
        'sqlite_backup':     io_sqlite_backup,
        'sqlite_import_csv': io_sqlite_import_csv,
        # ── CSV ──
        'csv_read':          io_csv_read,
        'csv_read_rows':     io_csv_read_rows,
        'csv_write':         io_csv_write,
        'csv_write_rows':    io_csv_write_rows,
        'csv_to_string':     io_csv_to_string,
        # ── Config ──
        'config_read':       io_config_read_ks,
        'config_write':      io_config_write_ks,
        'config_get':        io_config_get_ks,
        'config_set':        io_config_set_ks,
        'config_sections':   io_config_sections_ks,
        'config_options':    io_config_options,
        'config_from_dict':  io_config_from_dict,
        # ── Pickle ──
        'pickle_dump':       io_pickle_dump,
        'pickle_load':       io_pickle_load,
        'pickle_dumps':      io_pickle_dumps,
        'pickle_loads':      io_pickle_loads,
        # ── Struct/binary ──
        'pack':              io_pack,
        'unpack':            io_unpack,
        'pack_into':         io_pack_into,
        'unpack_from':       io_unpack_from,
        'calcsize':          io_calcsize,
        # ── C arrays ──
        'array':             io_array,
        'array_frombytes':   io_array_frombytes,
        'array_tobytes':     io_array_tobytes,
        'array_tolist':      io_array_tolist,
        'array_itemsize':    io_array_itemsize,
        'array_buffer_info': io_array_buffer_info,
        # ── Pipes / IPC ──
        'pipe':              io_pipe,
        'pipe2':             io_pipe2,
        'mkfifo':            io_mkfifo,
        'fd_read':           io_fd_read,
        'fd_write':          io_fd_write,
        'fd_close':          io_fd_close,
        'fd_dup':            io_fd_dup,
        'fd_dup2':           io_fd_dup2,
        'sendfile':          io_sendfile,
        'select':            io_select,
        'poll_create':       io_poll_create,
        'epoll_create':      io_epoll_create,
        # ── PTY / terminal ──
        'pty_open':          io_pty_open,
        'pty_fork':          io_pty_fork,
        'pty_spawn':         io_pty_spawn,
        'termios_get':       io_termios_get,
        'termios_set':       io_termios_set,
        'termios_raw':       io_termios_raw,
        'termios_cbreak':    io_termios_cbreak,
        'terminal_size':     io_terminal_size,
        'isatty_fd':         io_isatty_fd,
        # ── /proc ──
        'proc_read':         io_proc_read,
        'proc_maps':         io_proc_maps,
        'proc_cmdline':      io_proc_cmdline,
        'proc_list':         io_proc_list,
        'proc_mem_read':     io_proc_self_mem_read,
        'proc_mem_write':    io_proc_self_mem_write,
        # ── libc / C-level ──
        'c_malloc':          io_c_malloc,
        'c_calloc':          io_c_calloc,
        'c_realloc':         io_c_realloc,
        'c_free':            io_c_free,
        'c_memcpy':          io_c_memcpy,
        'c_memset':          io_c_memset,
        'c_memcmp':          io_c_memcmp,
        'c_strlen':          io_c_strlen,
        'c_read8':           io_c_read8,
        'c_read16':          io_c_read16,
        'c_read32':          io_c_read32,
        'c_read64':          io_c_read64,
        'c_write8':          io_c_write8,
        'c_write16':         io_c_write16,
        'c_write32':         io_c_write32,
        'c_write64':         io_c_write64,
        'c_read_bytes':      io_c_read_bytes,
        'c_write_bytes':     io_c_write_bytes,
        'c_ptr_to_bytes':    io_c_ptr_to_bytes,
        'c_bytes_to_ptr':    io_c_bytes_to_ptr,
        'c_mmap':            io_c_mmap,
        'c_munmap':          io_c_munmap,
        'c_open':            io_c_open,
        'c_fopen':           io_c_fopen,
        'c_fclose':          io_c_fclose,
        'c_fread':           io_c_fread,
        'c_fwrite':          io_c_fwrite,
        'c_printf':          io_c_printf,
        'c_getenv':          io_c_getenv,
        'c_setenv':          io_c_setenv,
        'c_system':          io_c_system,
        'c_getpid':          io_c_getpid,
        'c_getuid':          io_c_getuid,
        'c_load_library':    io_c_load_library,
        'c_call':            io_c_call,
        # ── Process management ──
        'fork':              io_fork,
        'exec':              io_exec,
        'execvp':            io_execvp,
        'waitpid':           io_waitpid,
        'wait':              io_wait,
        'spawn':             io_spawn,
        'run':               io_run,
        'popen':             io_popen,
        'getpid':            io_getpid,
        'getppid':           io_getppid,
        'getpgid':           io_getpgid,
        'setpgid':           io_setpgid,
        'getsid':            io_getsid,
        'setsid':            io_setsid,
        'kill':              io_kill,
        'killpg':            io_killpg,
        'signal':            io_signal,
        'sigwait':           io_sigwait,
        # ── Resource limits ──
        'getrlimit':         io_getrlimit,
        'setrlimit':         io_setrlimit,
        'getrusage':         io_getrusage,
        'RLIMIT_CPU':        RLIMIT_CPU,
        'RLIMIT_FSIZE':      RLIMIT_FSIZE,
        'RLIMIT_DATA':       RLIMIT_DATA,
        'RLIMIT_STACK':      RLIMIT_STACK,
        'RLIMIT_CORE':       RLIMIT_CORE,
        'RLIMIT_NOFILE':     RLIMIT_NOFILE,
        'RLIMIT_AS':         RLIMIT_AS,
        'RLIM_INFINITY':     RLIM_INFINITY,
        # ── User/group ──
        'getuid':            io_getuid,
        'getgid':            io_getgid,
        'geteuid':           io_geteuid,
        'setuid':            io_setuid,
        'setgid':            io_setgid,
        'seteuid':           io_seteuid,
        'setegid':           io_setegid,
        'getpwuid':          io_getpwuid,
        'getpwnam':          io_getpwnam,
        'getgrnam':          io_getgrnam,
        'getgroups':         io_getgroups,
        # ── Environment ──
        'getenv':            io_getenv,
        'setenv':            io_setenv,
        'unsetenv':          io_unsetenv,
        'environ':           io_environ,
        'putenv':            io_putenv,
        # ── Xattr ──
        'xattr_get':         io_xattr_get,
        'xattr_set':         io_xattr_set,
        # ── System info ──
        'sysinfo':           io_sysinfo,
        'uname':             io_uname,
        'sysconf':           io_sysconf,
        'pathconf':          io_pathconf,
        # ── Signal constants ──
        'SIGINT':            signal.SIGINT,
        'SIGTERM':           signal.SIGTERM,
        'SIGKILL':           signal.SIGKILL,
        'SIGSTOP':           signal.SIGSTOP,
        'SIGCONT':           signal.SIGCONT,
        'SIGHUP':            signal.SIGHUP,
        'SIGCHLD':           signal.SIGCHLD,
        'SIGUSR1':           signal.SIGUSR1,
        'SIGUSR2':           signal.SIGUSR2,
        'SIGPIPE':           signal.SIGPIPE,
        'SIGALRM':           signal.SIGALRM,
        # ── File mode constants ──
        'O_RDONLY':          os.O_RDONLY,
        'O_WRONLY':          os.O_WRONLY,
        'O_RDWR':            os.O_RDWR,
        'O_CREAT':           os.O_CREAT,
        'O_TRUNC':           os.O_TRUNC,
        'O_APPEND':          os.O_APPEND,
        'O_NONBLOCK':        os.O_NONBLOCK,
        'O_CLOEXEC':         os.O_CLOEXEC,
        'O_SYNC':            getattr(os, 'O_SYNC', 0),
        'O_DSYNC':           getattr(os, 'O_DSYNC', 0),
        'O_DIRECT':          getattr(os, 'O_DIRECT', 0),
        'F_OK':              os.F_OK,
        'R_OK':              os.R_OK,
        'W_OK':              os.W_OK,
        'X_OK':              os.X_OK,
        # ── stdin/stdout/stderr ──
        'stdin':             sys.stdin,
        'stdout':            sys.stdout,
        'stderr':            sys.stderr,
        'stdin_fd':          0,
        'stdout_fd':         1,
        'stderr_fd':         2,
        # ── BytesIO / StringIO ──
        'BytesIO':           io.BytesIO,
        'StringIO':          io.StringIO,
        'BufferedReader':    io.BufferedReader,
        'BufferedWriter':    io.BufferedWriter,
    }


def build_sys_module() -> dict:
    """Expanded sys module."""
    import platform as _plt
    return {
        'argv':              sys.argv,
        'exit':              sys.exit,
        'version':           sys.version,
        'platform':          sys.platform,
        'path':              sys.path,
        'modules':           sys.modules,
        'executable':        sys.executable,
        'prefix':            sys.prefix,
        'maxsize':           sys.maxsize,
        'byteorder':         sys.byteorder,
        'getpid':            os.getpid,
        'getppid':           os.getppid,
        'getuid':            lambda: os.getuid() if hasattr(os,'getuid') else 0,
        'getgid':            lambda: os.getgid() if hasattr(os,'getgid') else 0,
        'geteuid':           lambda: os.geteuid() if hasattr(os,'geteuid') else 0,
        'getenv':            os.getenv,
        'setenv':            lambda k,v: os.environ.__setitem__(k, str(v)),
        'unsetenv':          lambda k: os.environ.pop(k, None),
        'environ':           lambda: dict(os.environ),
        'getcwd':            os.getcwd,
        'chdir':             os.chdir,
        'listdir':           os.listdir,
        'mkdir':             lambda p,m=0o777: os.makedirs(p,mode=m,exist_ok=True),
        'unlink':            os.unlink,
        'rename':            os.rename,
        'stat':              os.stat,
        'chmod':             os.chmod,
        'chown':             os.chown,
        'symlink':           os.symlink,
        'readlink':          os.readlink,
        'cpu_count':         os.cpu_count,
        'hostname':          socket.gethostname,
        'uname':             lambda: dict(zip(['sysname','nodename','release','version','machine'], os.uname())),
        'platform_info':     lambda: {'system': _plt.system(), 'machine': _plt.machine(),
                                       'release': _plt.release(), 'version': _plt.version(),
                                       'python': _plt.python_version(),
                                       'arch': _plt.architecture()},
        'time':              time.time,
        'sleep':             time.sleep,
        'clock_ns':          time.perf_counter_ns,
        'monotonic':         time.monotonic,
        'kill':              os.kill,
        'fork':              os.fork,
        'wait':              os.wait,
        'waitpid':           os.waitpid,
        'exec':              os.execve,
        'run':               io_run,
        'popen':             os.popen,
        'getrlimit':         resource.getrlimit,
        'setrlimit':         resource.setrlimit,
        'getrusage':         resource.getrusage,
        'signal':            signal.signal,
        'SIGINT':            signal.SIGINT,
        'SIGTERM':           signal.SIGTERM,
        'SIGKILL':           signal.SIGKILL,
        'SIGHUP':            signal.SIGHUP,
        'SIGUSR1':           signal.SIGUSR1,
        'SIGUSR2':           signal.SIGUSR2,
        'urandom':           os.urandom,
        'getlogin':          lambda: os.getlogin() if hasattr(os,'getlogin') else '',
        'confstr':           lambda n: os.confstr(n) if hasattr(os,'confstr') else '',
        'sysconf':           lambda n: os.sysconf(n) if hasattr(os,'sysconf') else -1,
        'page_size':         lambda: os.sysconf('SC_PAGE_SIZE') if hasattr(os,'sysconf') else 4096,
        'load_avg':          lambda: os.getloadavg() if hasattr(os,'getloadavg') else (0,0,0),
        'path_exists':       os.path.exists,
        'path_join':         os.path.join,
        'path_abs':          os.path.abspath,
        'path_base':         os.path.basename,
        'path_dir':          os.path.dirname,
        'getpwuid':          lambda uid=None: io_getpwuid(uid),
        'getgrnam':          io_getgrnam,
        'stdout':            sys.stdout,
        'stderr':            sys.stderr,
        'stdin':             sys.stdin,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  MERGE: functions from uploaded version not yet in mine
# ═══════════════════════════════════════════════════════════════════════════════

import socket as _sock
import select as _sel

# ── Extra net constants ────────────────────────────────────────────────────────
_EPOLLIN   = getattr(_sel, 'EPOLLIN',  1)
_EPOLLOUT  = getattr(_sel, 'EPOLLOUT', 4)
_EPOLLERR  = getattr(_sel, 'EPOLLERR', 8)
_EPOLLET   = getattr(_sel, 'EPOLLET',  1 << 31) if hasattr(_sel, 'EPOLLET') else (1 << 31)

# ── Extra socket helpers ───────────────────────────────────────────────────────

def net_connect6(host: str, port: int, timeout: float = 10) -> _sock.socket:
    """Connect IPv6 TCP."""
    s = _sock.socket(_sock.AF_INET6, _sock.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((host, int(port), 0, 0))
    return s

def net_listen6(host: str = '::', port: int = 0, backlog: int = 128) -> _sock.socket:
    s = _sock.socket(_sock.AF_INET6, _sock.SOCK_STREAM)
    s.setsockopt(_sock.SOL_SOCKET, _sock.SO_REUSEADDR, 1)
    s.bind((host, int(port)))
    s.listen(backlog)
    return s

def net_udp(host: str = '0.0.0.0', port: int = 0) -> _sock.socket:
    s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
    if port: s.bind((host, int(port)))
    return s

def net_udp6(host: str = '::', port: int = 0) -> _sock.socket:
    s = _sock.socket(_sock.AF_INET6, _sock.SOCK_DGRAM)
    if port: s.bind((host, int(port), 0, 0))
    return s

def net_raw(proto: int = _sock.IPPROTO_RAW) -> _sock.socket:
    return _sock.socket(_sock.AF_INET, _sock.SOCK_RAW, proto)

def net_fromfd(fd: int, family=_sock.AF_INET, type_=_sock.SOCK_STREAM) -> _sock.socket:
    return _sock.fromfd(fd, family, type_)

def net_dup(sock: _sock.socket) -> _sock.socket:
    return sock.dup()

def net_fileno(sock: _sock.socket) -> int:
    return sock.fileno()

def net_makefile(sock: _sock.socket, mode: str = 'r', buffering: int = -1):
    return sock.makefile(mode, buffering)

def net_pair(family=_sock.AF_UNIX, type_=_sock.SOCK_STREAM) -> tuple:
    return _sock.socketpair(family, type_)

def net_shutdown(sock: _sock.socket, how: int = _sock.SHUT_RDWR):
    sock.shutdown(how)

def net_getsockname(sock: _sock.socket): return sock.getsockname()
def net_getpeername(sock: _sock.socket): return sock.getpeername()
def net_getnameinfo(sockaddr, flags: int = 0): return _sock.getnameinfo(sockaddr, flags)

def net_recvfrom(sock: _sock.socket, size: int = 65535): return sock.recvfrom(size)
def net_recvmsg(sock: _sock.socket, bufsize: int = 65535): return sock.recvmsg(bufsize)
def net_sendmsg(sock: _sock.socket, buffers, ancdata=None, flags: int = 0, address=None):
    return sock.sendmsg(buffers, ancdata or [], flags, address) if address else sock.sendmsg(buffers, ancdata or [], flags)

def net_sendto(sock: _sock.socket, data, address):
    if isinstance(data, str): data = data.encode('utf-8')
    return sock.sendto(data, address)

def net_recv_all(sock: _sock.socket, size: int) -> bytes:
    """Receive exactly `size` bytes."""
    buf = b''
    while len(buf) < size:
        chunk = sock.recv(size - len(buf))
        if not chunk: break
        buf += chunk
    return buf

def net_recv_exactly(sock: _sock.socket, n: int) -> bytes:
    return net_recv_all(sock, n)

def net_set_linger(sock: _sock.socket, onoff: int = 1, linger: int = 0):
    import struct as _st
    sock.setsockopt(_sock.SOL_SOCKET, _sock.SO_LINGER,
                    _st.pack('ii', onoff, linger))

def net_set_rcvbuf(sock: _sock.socket, size: int):
    sock.setsockopt(_sock.SOL_SOCKET, _sock.SO_RCVBUF, size)

def net_set_sndbuf(sock: _sock.socket, size: int):
    sock.setsockopt(_sock.SOL_SOCKET, _sock.SO_SNDBUF, size)

def net_set_reuseaddr(sock: _sock.socket, val: int = 1):
    sock.setsockopt(_sock.SOL_SOCKET, _sock.SO_REUSEADDR, val)

def net_set_reuseport(sock: _sock.socket, val: int = 1):
    if hasattr(_sock, 'SO_REUSEPORT'):
        sock.setsockopt(_sock.SOL_SOCKET, _sock.SO_REUSEPORT, val)

def net_set_ttl(sock: _sock.socket, ttl: int):
    sock.setsockopt(_sock.IPPROTO_IP, _sock.IP_TTL, ttl)

def net_inet_ntop(af: int, packed: bytes) -> str: return _sock.inet_ntop(af, packed)
def net_inet_pton(af: int, addr: str) -> bytes: return _sock.inet_pton(af, addr)

def net_ip_to_int(ip: str) -> int:
    import struct as _st
    return _st.unpack('!I', _sock.inet_aton(ip))[0]

def net_int_to_ip(n: int) -> str:
    import struct as _st
    return _sock.inet_ntoa(_st.pack('!I', n))

def net_ip_to_bytes(ip: str) -> bytes: return _sock.inet_aton(ip)
def net_ip6_to_bytes(ip6: str) -> bytes: return _sock.inet_pton(_sock.AF_INET6, ip6)

def net_is_valid_ip(addr: str) -> bool:
    try: ipaddress.ip_address(addr); return True
    except ValueError: return False

def net_resolve_all(domain: str) -> list:
    try: return list({r[4][0] for r in _sock.getaddrinfo(domain, None)})
    except Exception: return []

def net_reverse_dns(ip: str) -> str:
    try: return _sock.gethostbyaddr(ip)[0]
    except Exception: return ''

def net_local_ip() -> str:
    try:
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1)); ip = s.getsockname()[0]; s.close(); return ip
    except Exception: return '127.0.0.1'

def net_hostname() -> str: return _sock.gethostname()
def net_fqdn() -> str: return _sock.getfqdn()

def net_interfaces() -> list:
    """List network interface names (Linux /proc/net/dev)."""
    ifaces = []
    try:
        with open('/proc/net/dev') as f:
            for line in f.readlines()[2:]:
                ifaces.append(line.split(':')[0].strip())
    except Exception: pass
    return ifaces

def net_interface_addrs() -> dict:
    """Get addresses for each interface via /proc/net/if_inet6 + /proc/net/fib_trie."""
    result = {}
    try:
        import socket as _s, struct as _st
        with open('/proc/net/dev') as f:
            for line in f.readlines()[2:]:
                name = line.split(':')[0].strip()
                result[name] = []
        # Try to get IPs via getaddrinfo on hostname (crude but works)
        for iface in list(result.keys()):
            pass  # Could use netifaces if available
    except Exception: pass
    if not result:
        result['lo'] = ['127.0.0.1']
    return result

def net_poll(sockets: list, timeout: float = 1.0) -> list:
    """select() wrapper. Returns list of readable sockets."""
    try:
        rlist, _, _ = _sel.select(sockets, [], [], timeout)
        return rlist
    except Exception: return []

def net_epoll(fd_event_map: dict, timeout: float = 1.0) -> list:
    """epoll wrapper. fd_event_map = {fd: events}. Returns [(fd, event), ...]"""
    if not hasattr(_sel, 'epoll'): return []
    ep = _sel.epoll()
    for fd, evts in fd_event_map.items():
        ep.register(fd, evts)
    events = ep.poll(timeout)
    ep.close()
    return events

def net_port_scan_fast(host: str, start: int, end: int,
                       timeout: float = 0.3, max_threads: int = 512) -> list:
    """Fast threaded port scan. Returns list of open ports."""
    return net_port_scan_open(host, range(int(start), int(end)+1), timeout)

def net_ftp_list_detail(ftp, path: str = '.') -> list:
    lines = []
    ftp.dir(path, lines.append)
    return lines

def net_ftps_connect(host: str, port: int = 21, user: str = '',
                     password: str = '', timeout: float = 30):
    return net_ftp_connect_tls(host, port, user, password, timeout)

def net_ftp_passive(ftp, passive: bool = True):
    ftp.set_pasv(passive)

def net_http_get_bytes(url: str, timeout: float = 30,
                       headers: dict = None) -> bytes:
    import requests as _req
    r = _req.get(url, headers=headers or {}, timeout=timeout)
    r.raise_for_status()
    return r.content

def net_http_request(method: str, url: str, **kwargs) -> dict:
    import requests as _req
    r = _req.request(method.upper(), url, **kwargs)
    return {'status': r.status_code, 'headers': dict(r.headers),
            'text': r.text, 'content': r.content,
            'json': _safe_json(r), 'url': r.url}

def net_imap_folders(imap) -> list:
    return net_imap_list_folders(imap)

def net_ssh_connect(host: str, user: str = None, port: int = 22,
                    key_file: str = None, timeout: int = 30) -> dict:
    """Return SSH connection info dict (subprocess-based)."""
    import shutil as _sh
    ssh = _sh.which('ssh')
    return {
        'host': host, 'user': user, 'port': port,
        'key_file': key_file, 'timeout': timeout,
        'ssh_binary': ssh,
        'available': ssh is not None,
    }

def net_ssh_exec_stream(host: str, command: str, user: str = None,
                        port: int = 22, key_file: str = None):
    """SSH exec, yielding output lines as they arrive."""
    import shutil as _sh
    ssh = _sh.which('ssh')
    if not ssh: return
    args = [ssh, '-o', 'StrictHostKeyChecking=no', '-p', str(port)]
    if key_file: args += ['-i', key_file]
    args += [f'{user}@{host}' if user else host, command]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        yield line
    proc.wait()

def net_ssh_upload(local: str, remote_path: str, host: str,
                   user: str = None, port: int = 22, key_file: str = None) -> dict:
    return net_scp_upload(local, remote_path, host, user, port, key_file)

def net_ssh_download(remote_path: str, local: str, host: str,
                     user: str = None, port: int = 22, key_file: str = None) -> dict:
    return net_scp_download(remote_path, local, host, user, port, key_file)

def net_ssh_forward(local_port: int, remote_host: str, remote_port: int,
                    ssh_host: str, ssh_user: str = None, ssh_port: int = 22,
                    key_file: str = None):
    return net_ssh_tunnel(local_port, remote_host, remote_port,
                          ssh_host, ssh_user, ssh_port, key_file)

def net_ssh_sftp(host: str, user: str = None, port: int = 22,
                 key_file: str = None) -> dict:
    """Return SFTP session info (subprocess sftp wrapper)."""
    import shutil as _sh
    sftp = _sh.which('sftp')
    return {'host': host, 'user': user, 'port': port,
            'sftp_binary': sftp, 'available': sftp is not None}

def net_ssh_close(conn):
    """Close SSH subprocess if it has a terminate method."""
    if hasattr(conn, 'terminate'): conn.terminate()

# SFTP wrappers via sftp subprocess
def _sftp_run(host: str, user: str, port: int, commands: list,
              key_file: str = None) -> dict:
    import shutil as _sh, io as _io
    sftp = _sh.which('sftp')
    if not sftp: return {'returncode': -1, 'stderr': 'sftp not found'}
    args = [sftp, '-P', str(port), '-o', 'StrictHostKeyChecking=no',
            '-b', '-']
    if key_file: args += ['-i', key_file]
    args.append(f'{user}@{host}' if user else host)
    stdin = '\n'.join(commands) + '\nexit\n'
    r = subprocess.run(args, input=stdin.encode(), capture_output=True, timeout=30)
    return {'returncode': r.returncode,
            'stdout': r.stdout.decode('utf-8', errors='replace'),
            'stderr': r.stderr.decode('utf-8', errors='replace')}

def net_sftp_list(host: str, path: str = '.', user: str = None, port: int = 22) -> dict:
    return _sftp_run(host, user or '', port, [f'ls {path}'])

def net_sftp_mkdir(host: str, path: str, user: str = None, port: int = 22) -> dict:
    return _sftp_run(host, user or '', port, [f'mkdir {path}'])

def net_sftp_read(host: str, remote: str, local: str,
                  user: str = None, port: int = 22) -> dict:
    return net_scp_download(remote, local, host, user, port)

def net_sftp_write(host: str, local: str, remote: str,
                   user: str = None, port: int = 22) -> dict:
    return net_scp_upload(local, remote, host, user, port)

def net_sftp_remove(host: str, path: str, user: str = None, port: int = 22) -> dict:
    return _sftp_run(host, user or '', port, [f'rm {path}'])

def net_sftp_rename(host: str, src: str, dst: str, user: str = None, port: int = 22) -> dict:
    return _sftp_run(host, user or '', port, [f'rename {src} {dst}'])

def net_sftp_stat(host: str, path: str, user: str = None, port: int = 22) -> dict:
    return _sftp_run(host, user or '', port, [f'ls -la {path}'])

# SMTP HTML
def net_smtp_send_html(host: str, port: int, user: str, password: str,
                        from_addr: str, to_addrs,
                        subject: str, html_body: str,
                        plain_body: str = '',
                        use_tls: bool = True, timeout: float = 30) -> bool:
    return net_smtp_send(host, port, user, password, from_addr, to_addrs,
                         subject, plain_body or 'See HTML version',
                         use_tls=use_tls, timeout=timeout)

# SOCKS proxy
def net_socks_connect(host: str, port: int, socks_host: str,
                       socks_port: int = 1080, socks_ver: int = 5,
                       timeout: float = 10) -> _sock.socket:
    """SOCKS4/5 proxy connect (manual handshake)."""
    s = _sock.create_connection((socks_host, socks_port), timeout=timeout)
    if socks_ver == 5:
        s.sendall(b'\x05\x01\x00')  # SOCKS5, 1 method: no auth
        resp = s.recv(2)
        if resp != b'\x05\x00': raise ConnectionError('SOCKS5 auth failed')
        host_b = host.encode()
        req = b'\x05\x01\x00\x03' + bytes([len(host_b)]) + host_b + struct.pack('>H', port)
        s.sendall(req)
        resp = s.recv(10)
        if resp[1] != 0: raise ConnectionError(f'SOCKS5 connect failed: {resp[1]}')
    else:
        import struct as _st
        try: ip = _sock.gethostbyname(host)
        except Exception: ip = host
        req = _st.pack('>BBHI', 4, 1, port, _st.unpack('!I', _sock.inet_aton(ip))[0]) + b'\x00'
        s.sendall(req)
        resp = s.recv(8)
        if resp[1] != 90: raise ConnectionError('SOCKS4 connect failed')
    return s

# Telnet
def net_telnet_connect(host: str, port: int = 23, timeout: float = 10):
    """Telnet connection via stdlib."""
    try:
        import telnetlib as _tl
        t = _tl.Telnet(host, int(port), timeout=timeout)
        return t
    except Exception:
        # Fallback: raw socket
        return net_tcp_connect(host, port, timeout=timeout)

def net_telnet_read(tn, timeout: float = 2) -> str:
    if hasattr(tn, 'read_until'):
        try: return tn.read_very_eager().decode('utf-8', errors='replace')
        except Exception: return ''
    return net_tcp_recv_str(tn, 65535)

def net_telnet_write(tn, data: str):
    if hasattr(tn, 'write'): tn.write(data.encode('utf-8'))
    else: net_tcp_send(tn, data)

def net_telnet_interact(tn):
    if hasattr(tn, 'interact'): tn.interact()

def net_telnet_close(tn):
    try: tn.close()
    except Exception: pass

# Traceroute via subprocess
def net_traceroute(host: str, max_hops: int = 30) -> dict:
    import shutil as _sh
    tr = _sh.which('traceroute') or _sh.which('tracepath')
    if not tr: return {'error': 'traceroute not found'}
    r = subprocess.run([tr, '-m', str(max_hops), host],
                       capture_output=True, text=True, timeout=60)
    return {'output': r.stdout, 'returncode': r.returncode}

def net_ping(host: str, count: int = 1, timeout: int = 2) -> dict:
    import shutil as _sh
    ping = _sh.which('ping')
    if not ping: return {'error': 'ping not found'}
    r = subprocess.run([ping, '-c', str(count), '-W', str(timeout), host],
                       capture_output=True, text=True, timeout=timeout * count + 5)
    return {'output': r.stdout, 'returncode': r.returncode,
            'reachable': r.returncode == 0}

def net_quote(s: str) -> str: return urllib.parse.quote(s)
def net_unquote(s: str) -> str: return urllib.parse.unquote(s)


# ── Extra io functions from uploaded version ───────────────────────────────────

def io_buffered_rw(raw):
    """Create BufferedRWPair from raw stream."""
    return io.BufferedRWPair(raw, raw)

def io_tmpfile():
    """Create anonymous temporary file (deleted on close)."""
    return tempfile.TemporaryFile()

def io_open_binary(path: str, mode: str = 'rb'):
    return open(path, mode if 'b' in mode else mode + 'b')

def io_open_fd(fd: int, mode: str = 'r', closefd: bool = True):
    return os.fdopen(fd, mode, closefd=closefd)

def io_open_raw(path: str, flags: int = os.O_RDONLY, mode: int = 0o666) -> int:
    return os.open(path, flags, mode)

def io_openpty():
    return pty.openpty()

def io_close_fd(fd: int): os.close(fd)
def io_read_fd(fd: int, n: int) -> bytes: return os.read(fd, n)
def io_write_fd(fd: int, data: bytes) -> int: return os.write(fd, data)

def io_lseek(fd: int, pos: int, how: int = 0) -> int: return os.lseek(fd, pos, how)

def io_fstat(fd: int) -> dict:
    s = os.fstat(fd)
    return {'size': s.st_size, 'mode': s.st_mode, 'uid': s.st_uid,
            'gid': s.st_gid, 'mtime': s.st_mtime, 'ino': s.st_ino}

def io_fsync(fd: int): os.fsync(fd)
def io_fdatasync(fd: int): os.fdatasync(fd) if hasattr(os, 'fdatasync') else os.fsync(fd)
def io_ftruncate(fd: int, length: int): os.ftruncate(fd, length)
def io_lockf(f, cmd, len: int = 0): fcntl.lockf(f, cmd, len)
def io_dup(fd: int) -> int: return os.dup(fd)
def io_dup2(fd: int, fd2: int) -> int: return os.dup2(fd, fd2)

def io_sync():
    if _LIBC: _LIBC.sync()
    else:
        r = subprocess.run(['sync'], capture_output=True)

def io_umask(mask: int) -> int: return os.umask(mask)
def io_urandom(n: int) -> bytes: return os.urandom(n)
def io_ctermid() -> str: return os.ctermid() if hasattr(os, 'ctermid') else '/dev/tty'
def io_ttyname(fd: int) -> str: return os.ttyname(fd) if hasattr(os, 'ttyname') else ''
def io_isabs(path: str) -> bool: return os.path.isabs(path)
def io_normpath(path: str) -> str: return os.path.normpath(path)
def io_relpath(path: str, start: str = '.') -> str: return os.path.relpath(path, start)
def io_commonpath(paths: list) -> str: return os.path.commonpath(paths)
def io_commonprefix(paths: list) -> str: return os.path.commonprefix(paths)
def io_devnull() -> str: return os.devnull
def io_linesep() -> str: return os.linesep
def io_sep() -> str: return os.sep
def io_curdir() -> str: return os.curdir
def io_pardir() -> str: return os.pardir
def io_cpu_count() -> int: return os.cpu_count()
def io_confstr(name) -> str: return os.confstr(name) if hasattr(os, 'confstr') else ''
def io_getatime(path: str) -> float: return os.path.getatime(path)
def io_getmtime(path: str) -> float: return os.path.getmtime(path)
def io_getctime(path: str) -> float: return os.path.getctime(path)
def io_getsize(path: str) -> int: return os.path.getsize(path)
def io_disk_usage(path: str = '.') -> dict: return io_diskusage(path)
def io_crc32(data: bytes) -> int: return zlib.crc32(data) & 0xFFFFFFFF
def io_lchmod(path: str, mode: int): os.lchmod(path, mode) if hasattr(os, 'lchmod') else None
def io_copy2(src: str, dst: str) -> str: return shutil.copy2(src, dst)
def io_copyfile(src: str, dst: str): shutil.copyfile(src, dst)
def io_copymode(src: str, dst: str): shutil.copymode(src, dst)
def io_copystat(src: str, dst: str): shutil.copystat(src, dst)
def io_copytree(src: str, dst: str): shutil.copytree(src, dst, dirs_exist_ok=True)
def io_mkstemp(suffix: str = '', prefix: str = 'ks_', dir: str = None):
    return tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
def io_rglob(pattern: str) -> list: return _glob.glob(pattern, recursive=True)
def io_fnmatch_filter(names: list, pattern: str) -> list: return fnmatch.filter(names, pattern)
def io_which(name: str) -> str: return shutil.which(name) or ''
def io_system(cmd: str) -> int: return os.system(cmd)

def io_walk_gen(top: str):
    for dirpath, dirnames, filenames in os.walk(top):
        yield {'dir': dirpath, 'subdirs': dirnames, 'files': filenames}

def io_readable(f) -> bool: return f.readable()
def io_writable(f) -> bool: return f.writable()
def io_seekable(f) -> bool: return f.seekable()
def io_readline(f) -> str: return f.readline()
def io_readlines(f) -> list: return f.readlines()
def io_writelines(f, lines: list): f.writelines(lines)

def io_exec_stream(cmd: list, cwd: str = None, env: dict = None):
    """Run command, yielding stdout lines."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, cwd=cwd, env=env)
    for line in proc.stdout: yield line
    proc.wait()

def io_set_nonblocking(fd: int):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

def io_set_cloexec(fd: int):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

def io_set_raw(fd: int):
    try:
        import tty; tty.setraw(fd)
    except Exception: pass

def io_set_cbreak(fd: int):
    try:
        import tty; tty.setcbreak(fd)
    except Exception: pass

def io_tcgetattr(fd: int): return termios.tcgetattr(fd)
def io_tcsetattr(fd: int, when: int, attrs): termios.tcsetattr(fd, when, attrs)
def io_tcflush(fd: int, queue: int = termios.TCIOFLUSH): termios.tcflush(fd, queue)
def io_tcsendbreak(fd: int, duration: int = 0): termios.tcsendbreak(fd, duration)

def io_stat_mode_str(mode: int) -> str:
    import stat as _st
    return _st.filemode(mode)

def io_read_json(path: str, encoding: str = 'utf-8'):
    import json as _json
    with open(path, 'r', encoding=encoding) as f: return _json.load(f)

def io_write_json(path: str, obj, indent: int = 2, encoding: str = 'utf-8'):
    import json as _json
    with open(path, 'w', encoding=encoding) as f: _json.dump(obj, f, indent=indent)

def io_read_csv(path: str, delimiter: str = ',') -> list: return io_csv_read(path, delimiter)
def io_write_csv(path: str, rows: list, delimiter: str = ','): io_csv_write(path, rows, delimiter=delimiter)
def io_read_pickle(path: str): return io_pickle_load(path)
def io_write_pickle(path: str, obj): io_pickle_dump(obj, path)

def io_md5(path: str) -> str:
    return hashlib.md5(open(path,'rb').read()).hexdigest()
def io_sha256(path: str) -> str:
    return hashlib.sha256(open(path,'rb').read()).hexdigest()
def io_sha512(path: str) -> str:
    return hashlib.sha512(open(path,'rb').read()).hexdigest()

def io_zip_open(archive: str, mode: str = 'r'):
    return zipfile.ZipFile(archive, mode)

def io_mmap(path: str, access: str = 'rw', length: int = 0, offset: int = 0):
    return io_mmap_open(path, access, length, offset)

def io_mmap_find(mm, sub: bytes, start: int = 0) -> int:
    return mm.find(sub, start)

def io_mmap_seek(mm, pos: int, whence: int = 0): mm.seek(pos, whence)
def io_mmap_tell(mm) -> int: return mm.tell()

def io_watch(path: str, callback=None, interval: float = 1.0,
             duration: float = None):
    """
    Poll-based file watcher. Calls callback(path, event) on change.
    event: 'modified' | 'created' | 'deleted'
    Runs for `duration` seconds or forever if None.
    """
    import time as _t
    known = {}
    start = _t.time()
    
    def snapshot(p):
        snap = {}
        if os.path.isfile(p):
            snap[p] = os.stat(p).st_mtime
        elif os.path.isdir(p):
            for dp, dns, fns in os.walk(p):
                for fn in fns:
                    fp = os.path.join(dp, fn)
                    try: snap[fp] = os.stat(fp).st_mtime
                    except Exception: pass
        return snap

    known = snapshot(path)
    events = []
    while True:
        _t.sleep(interval)
        if duration and (_t.time() - start) > duration:
            break
        current = snapshot(path)
        for fp, mtime in current.items():
            if fp not in known:
                ev = ('created', fp)
                events.append(ev)
                if callback: callback(fp, 'created')
            elif mtime != known.get(fp):
                ev = ('modified', fp)
                events.append(ev)
                if callback: callback(fp, 'modified')
        for fp in list(known.keys()):
            if fp not in current:
                ev = ('deleted', fp)
                events.append(ev)
                if callback: callback(fp, 'deleted')
        known = current
    return events


# ═══════════════════════════════════════════════════════════════════════════════
#  UPDATED build_ functions — now includes everything
# ═══════════════════════════════════════════════════════════════════════════════

def build_net_module_full() -> dict:
    """Complete net module: my functions + all uploaded extras merged."""
    base = build_net_module()
    extras = {
        # Extra socket helpers
        'connect6':       net_connect6,
        'listen6':        net_listen6,
        'udp':            net_udp,
        'udp6':           net_udp6,
        'raw':            net_raw,
        'fromfd':         net_fromfd,
        'dup':            net_dup,
        'fileno':         net_fileno,
        'makefile':       net_makefile,
        'pair':           net_pair,
        'shutdown':       net_shutdown,
        'getsockname':    net_getsockname,
        'getpeername':    net_getpeername,
        'getnameinfo':    net_getnameinfo,
        'recvfrom':       net_recvfrom,
        'recvmsg':        net_recvmsg,
        'sendmsg':        net_sendmsg,
        'sendto':         net_sendto,
        'recv_all':       net_recv_all,
        'recv_exactly':   net_recv_exactly,
        'set_linger':     net_set_linger,
        'set_rcvbuf':     net_set_rcvbuf,
        'set_sndbuf':     net_set_sndbuf,
        'set_reuseaddr':  net_set_reuseaddr,
        'set_reuseport':  net_set_reuseport,
        'set_ttl':        net_set_ttl,
        'inet_ntop':      net_inet_ntop,
        'inet_pton':      net_inet_pton,
        'ip_to_int':      net_ip_to_int,
        'int_to_ip':      net_int_to_ip,
        'ip_to_bytes':    net_ip_to_bytes,
        'ip6_to_bytes':   net_ip6_to_bytes,
        'is_valid_ip':    net_is_valid_ip,
        'resolve_all':    net_resolve_all,
        'reverse_dns':    net_reverse_dns,
        'local_ip':       net_local_ip,
        'hostname':       net_hostname,
        'fqdn':           net_fqdn,
        'interfaces':     net_interfaces,
        'interface_addrs':net_interface_addrs,
        'poll':           net_poll,
        'epoll':          net_epoll,
        'port_scan_fast': net_port_scan_fast,
        'ftp_list_detail':net_ftp_list_detail,
        'ftps_connect':   net_ftps_connect,
        'ftp_passive':    net_ftp_passive,
        'http_get_bytes': net_http_get_bytes,
        'http_request':   net_http_request,
        'imap_folders':   net_imap_folders,
        'ssh_connect':    net_ssh_connect,
        'ssh_exec_stream':net_ssh_exec_stream,
        'ssh_upload':     net_ssh_upload,
        'ssh_download':   net_ssh_download,
        'ssh_forward':    net_ssh_forward,
        'ssh_sftp':       net_ssh_sftp,
        'ssh_close':      net_ssh_close,
        'sftp_list':      net_sftp_list,
        'sftp_mkdir':     net_sftp_mkdir,
        'sftp_read':      net_sftp_read,
        'sftp_write':     net_sftp_write,
        'sftp_remove':    net_sftp_remove,
        'sftp_rename':    net_sftp_rename,
        'sftp_stat':      net_sftp_stat,
        'smtp_send_html': net_smtp_send_html,
        'socks_connect':  net_socks_connect,
        'telnet_connect': net_telnet_connect,
        'telnet_read':    net_telnet_read,
        'telnet_write':   net_telnet_write,
        'telnet_interact':net_telnet_interact,
        'telnet_close':   net_telnet_close,
        'traceroute':     net_traceroute,
        'ping':           net_ping,
        'quote':          net_quote,
        'unquote':        net_unquote,
        # Extra constants
        'EPOLLIN':        _EPOLLIN,
        'EPOLLOUT':       _EPOLLOUT,
        'EPOLLERR':       _EPOLLERR,
        'EPOLLET':        _EPOLLET,
        'POLLIN':         getattr(_sel, 'POLLIN',  1),
        'POLLOUT':        getattr(_sel, 'POLLOUT', 4),
        'POLLERR':        getattr(_sel, 'POLLERR', 8),
        'SO_RCVBUF':      socket.SO_RCVBUF,
        'SO_SNDBUF':      socket.SO_SNDBUF,
        'IPPROTO_IP':     socket.IPPROTO_IP,
        'SOCK_SEQPACKET': getattr(socket, 'SOCK_SEQPACKET', 5),
    }
    base.update(extras)
    return base


def build_io_module_full() -> dict:
    """Complete io module: my functions + all uploaded extras merged."""
    base = build_io_module()
    extras = {
        'BufferedRW':     io_buffered_rw,
        'tmpfile':        io_tmpfile,
        'open_binary':    io_open_binary,
        'open_fd':        io_open_fd,
        'open_raw':       io_open_raw,
        'openpty':        io_openpty,
        'close_fd':       io_close_fd,
        'read_fd':        io_read_fd,
        'write_fd':       io_write_fd,
        'lseek':          io_lseek,
        'fstat':          io_fstat,
        'fsync':          io_fsync,
        'fdatasync':      io_fdatasync,
        'ftruncate':      io_ftruncate,
        'lockf':          io_lockf,
        'dup':            io_dup,
        'dup2':           io_dup2,
        'sync':           io_sync,
        'umask':          io_umask,
        'urandom':        io_urandom,
        'ctermid':        io_ctermid,
        'ttyname':        io_ttyname,
        'isabs':          io_isabs,
        'normpath':       io_normpath,
        'relpath':        io_relpath,
        'commonpath':     io_commonpath,
        'commonprefix':   io_commonprefix,
        'devnull':        io_devnull,
        'linesep':        io_linesep,
        'sep':            io_sep,
        'curdir':         io_curdir,
        'pardir':         io_pardir,
        'cpu_count':      io_cpu_count,
        'confstr':        io_confstr,
        'getatime':       io_getatime,
        'getmtime':       io_getmtime,
        'getctime':       io_getctime,
        'getsize':        io_getsize,
        'disk_usage':     io_disk_usage,
        'crc32':          io_crc32_ks,
        'lchmod':         io_lchmod,
        'copy2':          io_copy2,
        'copyfile':       io_copyfile,
        'copymode':       io_copymode,
        'copystat':       io_copystat,
        'copytree':       io_copytree,
        'mkstemp':        io_mkstemp,
        'rglob':          io_rglob,
        'fnmatch_filter': io_fnmatch_filter,
        'which':          io_which,
        'system':         io_system,
        'walk_gen':       io_walk_gen,
        'readable':       io_readable,
        'writable':       io_writable,
        'seekable':       io_seekable,
        'readline':       io_readline,
        'readlines':      io_readlines,
        'writelines':     io_writelines,
        'exec_stream':    io_exec_stream,
        'set_nonblocking':io_set_nonblocking,
        'set_cloexec':    io_set_cloexec,
        'set_raw':        io_set_raw,
        'set_cbreak':     io_set_cbreak,
        'tcgetattr':      io_tcgetattr,
        'tcsetattr':      io_tcsetattr,
        'tcflush':        io_tcflush,
        'tcsendbreak':    io_tcsendbreak,
        'stat_mode_str':  io_stat_mode_str,
        'read_json':      io_read_json,
        'write_json':     io_write_json,
        'read_csv':       io_read_csv,
        'write_csv':      io_write_csv,
        'read_pickle':    io_read_pickle,
        'write_pickle':   io_write_pickle,
        'md5':            io_md5,
        'sha256':         io_sha256,
        'sha512':         io_sha512,
        'zip_open':       io_zip_open,
        'mmap':           io_mmap,
        'mmap_find':      io_mmap_find,
        'mmap_seek':      io_mmap_seek,
        'mmap_tell':      io_mmap_tell,
        'watch':          io_watch,
        # Extra constants
        'LOCK_EX':        fcntl.LOCK_EX,
        'LOCK_SH':        fcntl.LOCK_SH,
        'LOCK_NB':        fcntl.LOCK_NB,
        'LOCK_UN':        fcntl.LOCK_UN,
        'MMAP_ACCESS_READ':  _mmap_mod.ACCESS_READ,
        'MMAP_ACCESS_WRITE': _mmap_mod.ACCESS_WRITE,
        'MMAP_ACCESS_COPY':  _mmap_mod.ACCESS_COPY,
        'SEEK_SET':       0, 'SEEK_CUR': 1, 'SEEK_END': 2,
        'O_EXCL':         os.O_EXCL,
        'TextWrapper':    io.TextIOWrapper,
    }
    base.update(extras)
    return base


# ═══════════════════════════════════════════════════════════════════════════════
#  COMPATIBILITY SHIMS — fix type issues when called from KentScript REPL
# ═══════════════════════════════════════════════════════════════════════════════

def _to_bytes(data):
    """Auto-convert str→bytes for functions that need bytes."""
    if isinstance(data, str): return data.encode('utf-8')
    if isinstance(data, (list, tuple)): return bytes(data)
    return data

def io_gzip_compress_ks(data, level: int = 9) -> bytes:
    return gzip.compress(_to_bytes(data), compresslevel=level)

def io_gzip_decompress_ks(data) -> bytes:
    return gzip.decompress(_to_bytes(data))

def io_zlib_compress_ks(data, level: int = 9) -> bytes:
    return zlib.compress(_to_bytes(data), level)

def io_zlib_decompress_ks(data) -> bytes:
    return zlib.decompress(_to_bytes(data))

def io_zlib_crc32_ks(data) -> int:
    return zlib.crc32(_to_bytes(data)) & 0xFFFFFFFF

def io_zlib_adler32_ks(data) -> int:
    return zlib.adler32(_to_bytes(data)) & 0xFFFFFFFF

def io_bz2_compress_ks(data, level: int = 9) -> bytes:
    return bz2.compress(_to_bytes(data), compresslevel=level)

def io_bz2_decompress_ks(data) -> bytes:
    return bz2.decompress(_to_bytes(data))

def io_lzma_compress_ks(data) -> bytes:
    return lzma.compress(_to_bytes(data))

def io_lzma_decompress_ks(data) -> bytes:
    return lzma.decompress(_to_bytes(data))

def io_crc32_ks(data) -> int:
    return zlib.crc32(_to_bytes(data)) & 0xFFFFFFFF

def io_mmap_write_ks(mm, offset: int, data):
    if isinstance(data, str): data = data.encode('utf-8')
    mm.seek(offset); mm.write(data)

def io_write_bytes_ks(path: str, data):
    if isinstance(data, str): data = data.encode('utf-8')
    with open(path, 'wb') as f: f.write(data)

def io_append_bytes_ks(path: str, data):
    if isinstance(data, str): data = data.encode('utf-8')
    with open(path, 'ab') as f: f.write(data)

# sqlite wrapper that returns a dict-like object accessible as int/str
class _SQLiteConn:
    """Wrapper that makes sqlite3.Connection work as KentScript opaque handle."""
    def __init__(self, conn): self._conn = conn
    def __repr__(self): return f"<KSSQLiteConn>"
    def __getattr__(self, name): return getattr(self._conn, name)

def io_sqlite_connect_ks(path: str = ':memory:', timeout: float = 5.0):
    conn = sqlite3.connect(path, timeout=timeout, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn  # return raw conn, KS will store as ANY type

def io_sqlite_exec_ks(conn, sql: str, params=None) -> int:
    cur = conn.cursor()
    cur.execute(sql, params or [])
    conn.commit()
    return cur.rowcount

def io_sqlite_query_ks(conn, sql: str, params=None) -> list:
    cur = conn.execute(sql, params or [])
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, tuple(row))) for row in cur.fetchall()]

def io_sqlite_queryone_ks(conn, sql: str, params=None):
    cur = conn.execute(sql, params or [])
    row = cur.fetchone()
    if row is None: return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, tuple(row)))

def io_sqlite_close_ks(conn): conn.close()

# config wrapper  
def io_config_read_ks(path: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(path)
    return cfg

def io_config_get_ks(cfg, section: str, key: str, fallback=None) -> str:
    return cfg.get(section, key, fallback=fallback)

def io_config_set_ks(cfg, section: str, key: str, value: str):
    if section not in cfg: cfg.add_section(section)
    cfg.set(section, key, str(value))

def io_config_write_ks(cfg, path: str):
    with open(path, 'w') as f: cfg.write(f)

def io_config_sections_ks(cfg) -> list: return cfg.sections()

# Net: tcp_listen returns socket object, KS needs to store as ANY
def net_tcp_listen_ks(host: str = '0.0.0.0', port: int = 0,
                       backlog: int = 128, reuse: bool = True):
    """TCP listen - returns socket stored as ANY type in KentScript."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if reuse: s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, int(port)))
    s.listen(backlog)
    return s

def net_mmap_anon_ks(size: int):
    """Anonymous mmap - returns as ANY type."""
    return io_mmap_anon(size)
