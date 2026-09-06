"""On-disk cache for transpiled C output.

The KentScript -> C transpile step (lex + parse + codegen) is the dominant
cost of a build when the binary cache is bypassed (e.g. `--no-cache`, or
`--release`/PGO builds which intentionally always recompile).  The emitted C
depends only on the source text and the transpiler implementation, NOT on gcc
optimization flags, so it can be cached independently of the binary cache and
reused across flag changes.

Keyed on: sha256(source) + cache-version + transpiler-file mtime/size, so any
edit to the transpiler automatically invalidates every entry.
"""

import os
import hashlib
import threading

_CC_DIR = os.path.join(os.path.expanduser("~"), ".cache", "ks_cc")
_CC_VERSION = "1"
_lock = threading.Lock()


def _transpiler_path():
    """Absolute path of the C transpiler module (used for invalidation)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "c_transpiler.py")


def _key(source_code, transpiler_path):
    h = hashlib.sha256()
    try:
        h.update(source_code.encode("utf-8", "replace"))
    except Exception:
        h.update(b"")
    h.update(b"|KSCC|")
    h.update(_CC_VERSION.encode("ascii"))
    try:
        st = os.stat(transpiler_path)
        h.update(("%d.%d" % (st.st_mtime_ns, st.st_size)).encode("ascii"))
    except OSError:
        pass
    return h.hexdigest()


def get_c(source_code, transpiler_path=None):
    """Return cached C source for `source_code`, or None on miss."""
    if source_code is None:
        return None
    if transpiler_path is None:
        transpiler_path = _transpiler_path()
    path = os.path.join(_CC_DIR, _key(source_code, transpiler_path) + ".c")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def put_c(source_code, c_code, transpiler_path=None):
    """Store C source `c_code` for `source_code`."""
    if source_code is None or c_code is None:
        return
    if transpiler_path is None:
        transpiler_path = _transpiler_path()
    path = os.path.join(_CC_DIR, _key(source_code, transpiler_path) + ".c")
    try:
        os.makedirs(_CC_DIR, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(c_code)
        with _lock:
            os.replace(tmp, path)
    except OSError:
        pass


def cache_path_for(source_code, transpiler_path=None):
    """Absolute path of the cache file for `source_code` (diagnostics)."""
    if transpiler_path is None:
        transpiler_path = _transpiler_path()
    return os.path.join(_CC_DIR, _key(source_code, transpiler_path) + ".c")
