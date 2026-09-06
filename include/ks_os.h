/*
 * ks_os.h - Native OS layer for KentScript (mirrors stdlib/os.ks)
 *
 * The interpreter loads stdlib/os.ks and injects real `os_*` bindings, so its
 * security guards (path-traversal + command-injection) and real operations both
 * run there. In the native (C transpiler) backend, `import` is a no-op and the
 * transpiler routes `os.*` calls to these helpers instead of the bare runtime
 * `system_os_*` functions, so the SAME security policy is enforced in compiled
 * binaries.
 *
 * NOTE: C has no exception mechanism (the transpiler compiles try/except as
 * best-effort no-op per design), so a rejected operation prints a
 * "SecurityError:" message to stderr and returns a safe default WITHOUT
 * performing the OS action. This preserves the security guarantee: dangerous
 * operations are BLOCKED in native just as they raise in the interpreter.
 */

#ifndef KS_OS_H
#define KS_OS_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#include <io.h>
#define ks_os_getcwd _getcwd
#define ks_os_mkdir(path, mode) _mkdir(path)
#else
#include <unistd.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <signal.h>
#endif

/* ---- Security state (mirrors os.ks _os_safe_mode / _os_allowed_dirs) ---- */
static int ks_os_safe_mode = 1;          /* safe mode ON by default */
static const char* ks_os_allowed_dir = NULL; /* optional single allowed prefix */

static void ks_os_set_safe_mode(long long enabled) { ks_os_safe_mode = (int)enabled; }
static void ks_os_set_allowed_dirs(const char* dir) { ks_os_allowed_dir = dir; }

/* ---- Small string helpers ---- */
static int ks_os_str_startswith(const char* s, const char* prefix) {
    if (!s || !prefix) return 0;
    size_t n = strlen(prefix);
    return strncmp(s, prefix, n) == 0;
}
static int ks_os_str_contains(const char* hay, const char* needle) {
    if (!hay || !needle) return 0;
    return strstr(hay, needle) != NULL;
}

/* Validate a path against the same rules as os.ks _validate_path.
 * Returns 1 if allowed, 0 if rejected (and prints the rejection). */
static int ks_os_validate_path(const char* path, const char* op) {
    char norm[4096];
    size_t i, j;

    if (!path || path[0] == '\0') {
        fprintf(stderr, "SecurityError: %s: Path cannot be empty\n", op ? op : "os");
        return 0;
    }

    if (ks_os_safe_mode) {
        /* normalize backslashes -> forward slashes */
        for (i = 0, j = 0; path[i] && j < sizeof(norm) - 1; i++) {
            norm[j++] = (path[i] == '\\') ? '/' : path[i];
        }
        norm[j] = '\0';

        if (ks_os_str_startswith(norm, "/") &&
            !ks_os_str_startswith(norm, "/home/") &&
            !ks_os_str_startswith(norm, "/tmp/")) {
            fprintf(stderr,
                "SecurityError: %s: Absolute paths not allowed in safe mode: %s\n",
                op ? op : "os", path);
            return 0;
        }
        if (ks_os_str_contains(norm, "../")) {
            fprintf(stderr,
                "SecurityError: %s: Path traversal detected: %s\n",
                op ? op : "os", path);
            return 0;
        }
        if (ks_os_allowed_dir && ks_os_allowed_dir[0]) {
            if (!ks_os_str_startswith(norm, ks_os_allowed_dir)) {
                fprintf(stderr,
                    "SecurityError: %s: Path not in allowed directories: %s\n",
                    op ? op : "os", path);
                return 0;
            }
        }
    }
    return 1;
}

/* Validate a command against os.ks system()/popen() injection rules.
 * Returns 1 if allowed, 0 if rejected. */
static int ks_os_check_cmd(const char* cmd, const char* op) {
    if (!cmd || cmd[0] == '\0') {
        fprintf(stderr, "ValidationError: %s: Command cannot be empty\n", op ? op : "os");
        return 0;
    }
    if (ks_os_safe_mode) {
        if (ks_os_str_contains(cmd, ";") || ks_os_str_contains(cmd, "&&") ||
            ks_os_str_contains(cmd, "||") || ks_os_str_contains(cmd, "|") ||
            ks_os_str_contains(cmd, "`") || ks_os_str_contains(cmd, "$(") ||
            ks_os_str_contains(cmd, "${")) {
            fprintf(stderr,
                "SecurityError: %s: Potential command injection detected: %s\n",
                op ? op : "os", cmd);
            return 0;
        }
    }
    return 1;
}

/* ---- Public os.* helpers (real operations, guarded) ---- */
static const char* ks_os_name(void) { return "posix"; }

static char* ks_os_getenv(const char* name, const char* default_val) {
    const char* v;
    if (!name || name[0] == '\0') {
        fprintf(stderr, "ValidationError: Environment variable key cannot be empty\n");
        return (char*)(default_val ? default_val : "");
    }
    v = getenv(name);
    return (char*)(v ? v : (default_val ? default_val : ""));
}

static long long ks_os_putenv(const char* key, const char* value) {
    if (!key || key[0] == '\0') {
        fprintf(stderr, "ValidationError: Environment variable key cannot be empty\n");
        return -1;
    }
    return setenv(key, value ? value : "", 1);
}

static long long ks_os_unsetenv(const char* key) {
    if (!key || key[0] == '\0') {
        fprintf(stderr, "ValidationError: Environment variable key cannot be empty\n");
        return -1;
    }
    return unsetenv(key);
}

static char* ks_os_getcwd(void) {
    static char buf[4096];
    if (getcwd(buf, sizeof(buf))) return buf;
    buf[0] = '\0';
    return buf;
}

static long long ks_os_chdir(const char* path) {
    if (!path || path[0] == '\0') {
        fprintf(stderr, "ValidationError: Path cannot be empty\n");
        return -1;
    }
    if (!ks_os_validate_path(path, "chdir")) return -1;
    return chdir(path);
}

/* listdir returns a real list in the interpreter; native has no list type,
 * so it returns NULL (list-returning ops are a documented native limitation).
 * The path is still validated. */
static void* ks_os_listdir(const char* path) {
    if (!path || path[0] == '\0') path = ".";
    if (!ks_os_validate_path(path, "listdir")) return NULL;
    return NULL;
}

static long long ks_os_mkdir(const char* path, long long mode) {
    if (!path || path[0] == '\0') {
        fprintf(stderr, "ValidationError: Path cannot be empty\n");
        return -1;
    }
    if (!ks_os_validate_path(path, "mkdir")) return -1;
    if (mode == 0) mode = 0755;
    return mkdir(path, (mode_t)mode);
}

static long long ks_os_makedirs(const char* path, long long mode) {
    if (!path || path[0] == '\0') {
        fprintf(stderr, "ValidationError: Path cannot be empty\n");
        return -1;
    }
    if (!ks_os_validate_path(path, "makedirs")) return -1;
    if (mode == 0) mode = 0755;
    /* Best-effort recursive create via mkdir -p semantics using the syscall. */
    {
        char tmp[4096];
        size_t i, len = strlen(path);
        if (len >= sizeof(tmp)) return -1;
        memcpy(tmp, path, len + 1);
        for (i = 1; i < len; i++) {
            if (tmp[i] == '/') {
                tmp[i] = '\0';
                if (access(tmp, F_OK) != 0) mkdir(tmp, (mode_t)mode);
                tmp[i] = '/';
            }
        }
        if (access(path, F_OK) != 0) mkdir(path, (mode_t)mode);
    }
    return 0;
}

static long long ks_os_rmdir(const char* path) {
    if (!path || path[0] == '\0') {
        fprintf(stderr, "ValidationError: Path cannot be empty\n");
        return -1;
    }
    if (!ks_os_validate_path(path, "rmdir")) return -1;
    return rmdir(path);
}

static long long ks_os_remove(const char* path) {
    struct stat st;
    if (!path || path[0] == '\0') {
        fprintf(stderr, "ValidationError: Path cannot be empty\n");
        return -1;
    }
    if (!ks_os_validate_path(path, "remove")) return -1;
    if (stat(path, &st) != 0) {
        fprintf(stderr, "IOError: File does not exist: %s\n", path);
        return -1;
    }
    if (S_ISDIR(st.st_mode)) return rmdir(path);
    return unlink(path);
}

static long long ks_os_rename(const char* src, const char* dst) {
    if (!src || src[0] == '\0') {
        fprintf(stderr, "ValidationError: Source path cannot be empty\n");
        return -1;
    }
    if (!dst || dst[0] == '\0') {
        fprintf(stderr, "ValidationError: Destination path cannot be empty\n");
        return -1;
    }
    if (!ks_os_validate_path(src, "rename")) return -1;
    if (!ks_os_validate_path(dst, "rename")) return -1;
    return rename(src, dst);
}

static long long ks_os_stat(const char* path) {
    if (!path || path[0] == '\0') {
        fprintf(stderr, "ValidationError: Path cannot be empty\n");
        return -1;
    }
    if (!ks_os_validate_path(path, "stat")) return -1;
    return (access(path, F_OK) == 0) ? 0 : -1;
}

static long long ks_os_chmod(const char* path, long long mode) {
    if (!path || path[0] == '\0') {
        fprintf(stderr, "ValidationError: Path cannot be empty\n");
        return -1;
    }
    if (!ks_os_validate_path(path, "chmod")) return -1;
    return chmod(path, (mode_t)mode);
}

static long long ks_os_chown(const char* path, long long uid, long long gid) {
    if (!path || path[0] == '\0') {
        fprintf(stderr, "ValidationError: Path cannot be empty\n");
        return -1;
    }
    if (!ks_os_validate_path(path, "chown")) return -1;
    return chown(path, (uid_t)uid, (gid_t)gid);
}

static long long ks_os_link(const char* src, const char* dst) {
    if (!src || src[0] == '\0') return -1;
    if (!dst || dst[0] == '\0') return -1;
    if (!ks_os_validate_path(src, "link")) return -1;
    if (!ks_os_validate_path(dst, "link")) return -1;
    return link(src, dst);
}

static long long ks_os_symlink(const char* src, const char* dst) {
    if (!src || src[0] == '\0') return -1;
    if (!dst || dst[0] == '\0') return -1;
    if (!ks_os_validate_path(dst, "symlink")) return -1;
    return symlink(src, dst);
}

static char* ks_os_readlink(const char* path) {
    static char buf[4096];
    ssize_t n;
    if (!path || path[0] == '\0') return (char*)"";
    if (!ks_os_validate_path(path, "readlink")) return (char*)"";
    n = readlink(path, buf, sizeof(buf) - 1);
    if (n < 0) return (char*)"";
    buf[n] = '\0';
    return buf;
}

static long long ks_os_exists(const char* path) {
    if (!path || path[0] == '\0') return 0;
    if (!ks_os_validate_path(path, "exists")) return 0;
    return (access(path, F_OK) == 0) ? 1 : 0;
}

static long long ks_os_isfile(const char* path) {
    struct stat st;
    if (!path || path[0] == '\0') return 0;
    if (!ks_os_validate_path(path, "isfile")) return 0;
    if (stat(path, &st) != 0) return 0;
    return S_ISREG(st.st_mode) ? 1 : 0;
}

static long long ks_os_isdir(const char* path) {
    struct stat st;
    if (!path || path[0] == '\0') return 0;
    if (!ks_os_validate_path(path, "isdir")) return 0;
    if (stat(path, &st) != 0) return 0;
    return S_ISDIR(st.st_mode) ? 1 : 0;
}

static long long ks_os_islink(const char* path) {
    struct stat st;
    if (!path || path[0] == '\0') return 0;
    if (!ks_os_validate_path(path, "islink")) return 0;
    if (lstat(path, &st) != 0) return 0;
    return S_ISLNK(st.st_mode) ? 1 : 0;
}

static long long ks_os_getpid(void) { return (long long)getpid(); }
static long long ks_os_getppid(void) { return (long long)getppid(); }
static long long ks_os_getuid(void) { return (long long)getuid(); }
static long long ks_os_getgid(void) { return (long long)getgid(); }

static long long ks_os_kill(long long pid, long long sig) {
    if (pid <= 0) {
        fprintf(stderr, "ValidationError: Invalid process ID\n");
        return -1;
    }
    if (sig == 0) sig = 15;
    return kill((pid_t)pid, (int)sig);
}

static long long ks_os_system(const char* cmd) {
    if (!cmd || cmd[0] == '\0') {
        fprintf(stderr, "ValidationError: Command cannot be empty\n");
        return -1;
    }
    if (!ks_os_check_cmd(cmd, "system")) return -1;
    return system(cmd);
}

/* popen returns a file handle in the interpreter; native has no such type,
 * so it returns NULL after applying the injection guard. */
static void* ks_os_popen(const char* cmd, const char* mode) {
    if (!cmd || cmd[0] == '\0') {
        fprintf(stderr, "ValidationError: Command cannot be empty\n");
        return NULL;
    }
    if (!ks_os_check_cmd(cmd, "popen")) return NULL;
    return NULL;
}

/* File I/O on the os module (mirror interpreter's os.write_file/read_file/
 * append_file). These are guarded like the rest of the os surface. */
static void ks_os_write_file(const char* path, const char* content) {
    if (!path || path[0] == '\0') {
        fprintf(stderr, "ValidationError: Path cannot be empty\n");
        return;
    }
    if (!ks_os_validate_path(path, "write_file")) return;
    system_file_write_text(path, content ? content : "");
}

static char* ks_os_read_file(const char* path) {
    if (!path || path[0] == '\0') {
        fprintf(stderr, "ValidationError: Path cannot be empty\n");
        return (char*)"";
    }
    if (!ks_os_validate_path(path, "read_file")) return (char*)"";
    return system_file_read_text(path);
}

static void ks_os_append_file(const char* path, const char* content) {
    FILE* f;
    if (!path || path[0] == '\0') {
        fprintf(stderr, "ValidationError: Path cannot be empty\n");
        return;
    }
    if (!ks_os_validate_path(path, "append_file")) return;
    f = fopen(path, "a");
    if (f) { fputs(content ? content : "", f); fclose(f); }
}

#endif /* KS_OS_H */
