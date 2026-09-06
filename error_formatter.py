"""
KentScript Error Handler
God-tier error messages with smart suggestions
"""

import re
import sys

# Only emit ANSI colors on an interactive terminal. Captured output (e.g. the
# built-in IDE's subprocess) keeps plain text — no raw escape codes.
_COLOR_OK = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class KentScriptSyntaxError(SyntaxError):
    def __init__(self, message, line=None, col=None, code=None, filename=None, source=None):
        super().__init__(message)
        self.lineno = line
        self.line = line
        self.col = col
        self.column = col
        self.offset = col
        self.code = code or source  # support both
        self.filename = filename


class KentScriptTypeError(TypeError):
    """Enhanced type error with line/col info"""
    def __init__(self, message, line=None, col=None, code=None, filename=None, source=None):
        super().__init__(message)
        self.lineno = line
        self.line = line
        self.col = col
        self.column = col
        self.code = code or source
        self.filename = filename


class KentScriptNameError(NameError):
    """Enhanced name error with line/col info"""
    def __init__(self, message, line=None, col=None, code=None, filename=None, source=None):
        super().__init__(message)
        self.lineno = line
        self.line = line
        self.col = col
        self.column = col
        self.code = code or source
        self.filename = filename


# Error codes for debugging
ERROR_CODES = {
    "E000": "UnknownError",
    "E001": "UnexpectedToken",
    "E002": "MissingSemicolon",
    "E003": "UnclosedBracket",
    "E004": "UndefinedName",
    "E005": "TypeMismatch",
    "E006": "InvalidSyntax",
    "E007": "LambdaSyntax",
    "E008": "RuntimeError",
    "E009": "IndexError",
    "E010": "ValueError",
    "E011": "BorrowError",
    "E012": "TypeCheckError",
    "E013": "CodegenError",
    "E014": "ImportError",
}

# Pattern-based suggestions
PATTERNS = [
    {
        "pattern": r"lambda\s*:",
        "code": "E007",
        "error": "invalid lambda syntax",
        "reason": "KentScript uses 'func' instead of 'lambda:'",
        "fix": ("lambda: { code }", "func() { code }"),
        "rank": 1,
    },
    {
        "pattern": r"lambda\s+\w+\s*:",
        "code": "E007",
        "error": "invalid lambda syntax",
        "reason": "KentScript uses '|param| =>' for parameterized lambdas",
        "fix": ("lambda x: x * 2", "|x| => x * 2"),
        "rank": 1,
    },
    {
        "pattern": r"let\s+\w+\s*[^;]\s*$",
        "code": "E002",
        "error": "missing semicolon",
        "reason": "KentScript requires ';' after statements",
        "fix": None,
        "rank": 2,
    },
    {
        "pattern": r"\bdef\s+\w+\s*\(",
        "code": "E006",
        "error": "use 'func' instead of 'def'",
        "reason": "KentScript uses 'func' for function definitions",
        "fix": ("def foo()", "func foo()"),
        "rank": 1,
    },
    {
        "pattern": r"\bNone\b",
        "code": "E006",
        "error": "use 'none' instead of 'None'",
        "reason": "KentScript uses lowercase 'none' for null values",
        "fix": ("None", "none"),
        "rank": 1,
    },
    {
        "pattern": r"\bTrue\b",
        "code": "E006",
        "error": "use 'true' instead of 'True'",
        "reason": "KentScript uses lowercase 'true' for boolean literals",
        "fix": ("True", "true"),
        "rank": 1,
    },
    {
        "pattern": r"\bFalse\b",
        "code": "E006",
        "error": "use 'false' instead of 'False'",
        "reason": "KentScript uses lowercase 'false' for boolean literals",
        "fix": ("False", "false"),
        "rank": 1,
    },
    {
        "pattern": r"\bexcept\s+\w+\s+as\s+\w+",
        "code": "E006",
        "error": "KentScript uses 'except Type { }' block syntax",
        "reason": "KentScript exception handling uses block syntax, not Python's 'as' pattern",
        "fix": ("except ValueError as e:", "except ValueError { }"),
        "rank": 1,
    },
    {
        "pattern": r"#\s",
        "code": "E006",
        "error": "use '::' for comments, not '#'",
        "reason": "KentScript uses '::' for single-line comments",
        "fix": ("# comment", ":: comment"),
        "rank": 1,
    },
    {
        "pattern": r"\bfn\s+\w+\s*\(",
        "code": "E006",
        "error": "use 'func' instead of 'fn'",
        "reason": "KentScript uses 'func' for function definitions",
        "fix": ("fn foo()", "func foo()"),
        "rank": 1,
    },
]


class C:
    RED = "\033[91m" if _COLOR_OK else ""
    GREEN = "\033[92m" if _COLOR_OK else ""
    YELLOW = "\033[93m" if _COLOR_OK else ""
    CYAN = "\033[96m" if _COLOR_OK else ""
    WHITE = "\033[97m" if _COLOR_OK else ""
    DIM = "\033[2m" if _COLOR_OK else ""
    BOLD = "\033[1m" if _COLOR_OK else ""
    RESET = "\033[0m" if _COLOR_OK else ""


def check_pattern(code):
    """Check code against known patterns and return suggestions"""
    for p in PATTERNS:
        if re.search(p["pattern"], code):
            return p
    return None


def format_error(error_type, message, line=None, col=None, code=None, filename=None, suggestions=None, source_lines=None, hint=None, note=None, suggestion=None, start_line=None, start_col=None, error_code=None):
    """Format error with god-tier messages
    code: source code string or list of lines
    source_lines: alias for code (backwards compatibility)
    hint, note, suggestion: aliases for suggestions (backwards compatibility)
    start_line, start_col: for multi-line errors (ignored in god-tier mode)
    """
    output = []
    
    # Support both code and source_lines
    if code is None and source_lines is not None:
        code = source_lines
    
    # Build suggestions list
    hint_list = []
    if hint:
        hint_list.append(hint)
    if note:
        hint_list.append(note)
    if suggestion:
        hint_list.append(suggestion)
    if suggestions:
        hint_list.extend(suggestions) if isinstance(suggestions, list) else hint_list.append(suggestions)
    output = []

    # Header with error code
    code_str = error_code if error_code else ERROR_CODES.get("E001", "E000")
    if "lambda" in message.lower():
        code_str = ERROR_CODES.get("E007", "E000")
    elif "semicolon" in message.lower():
        code_str = ERROR_CODES.get("E002", "E000")
    elif error_type == "FileNotFoundError":
        code_str = "FileNotFoundError"
    elif error_type == "ImportError":
        code_str = "ImportError"

    output.append(f"{C.RED}{C.BOLD}error{C.RESET}{C.WHITE}: [{code_str}] {message}{C.RESET}")

    # Smart suggestions for common mistakes
    if "unexpected token" in message.lower() and "//" in message:
        hint_list = ["Did you mean a comment? Use '::' instead of '//'", "// is the floor divide operator in KentScript"]
    elif "unexpected token" in message.lower() and "#" in message:
        hint_list = ["Did you mean a comment? Use '::' instead of '#'"]
    elif "unexpected token" in message.lower() and ("def " in message or "def\t" in message):
        hint_list = ["KentScript uses 'func' instead of 'def'"]

    # Location
    loc = f"{filename or '<stdin>'}:{line or '?'}"
    if col:
        loc += f":{col}"
    output.append(f"{C.DIM}  --> {loc}{C.RESET}")
    output.append("")

    # Source with context
    if code and line:
        lines = code.splitlines() if isinstance(code, str) else code
        start = max(0, line - 3)
        end = min(len(lines), line + 2)

        for i in range(start, end):
            num = i + 1
            prefix = f"{C.DIM}{num:>4}{C.RESET} │ "
            line_content = lines[i] if i < len(lines) else ""

            if num == line:
                output.append(f"{prefix}{line_content}")
                if col and col > 0:
                    pointer = " " * max(0, col - 1)
                    output.append(f"{C.DIM}       {pointer}{C.RED}^{' ' * max(0, len(line_content) - col)}{C.RESET}")
            else:
                output.append(f"{C.DIM}{prefix}{line_content}{C.RESET}")

        output.append("")

    # Check for patterns on the ERROR LINE only, not the whole source
    error_line_text = ""
    if code and line:
        lines = code.splitlines() if isinstance(code, str) else code
        if 0 <= line - 1 < len(lines):
            error_line_text = lines[line - 1]
    matched = check_pattern(error_line_text) if error_line_text else None

    if matched:
        output.append(f"{C.CYAN}{C.BOLD}reason:{C.RESET} {matched['reason']}")
        output.append("")

        # Auto-fix preview
        if matched.get("fix"):
            old, new = matched["fix"]
            output.append(f"{C.YELLOW}{C.BOLD}fix:{C.RESET}")
            output.append(f"{C.DIM}  replace:{C.RESET}")
            output.append(f"{C.RED}    {old}{C.RESET}")
            output.append(f"{C.DIM}  with:{C.RESET}")
            output.append(f"{C.GREEN}    {new}{C.RESET}")
        output.append("")
    elif hint_list:
        output.append(f"{C.CYAN}{C.BOLD}help:{C.RESET}")
        for i, s in enumerate(hint_list, 1):
            output.append(f"{C.DIM}  {i}. {s}{C.RESET}")
        output.append("")

    return "\n".join(output)


def format_exception(exc, filename=None, source_code=None):
    """Format any exception"""
    error_type = type(exc).__name__
    message = str(exc)

    line = getattr(exc, "lineno", None) or getattr(exc, "line", None)
    col = getattr(exc, "col", None) or getattr(exc, "column", None) or getattr(exc, "offset", None)

    # If the exception already has formatted output, use it
    if hasattr(exc, "formatted") and exc.formatted:
        return exc.formatted

    # Generate error message based on exception type
    suggestions = []
    code_str = "E000"

    msg_lower = message.lower()

    if hasattr(exc, "ks_class") and hasattr(exc, "ks_message"):
        error_type = exc.ks_class
        message = exc.ks_message
        stack = getattr(exc, "instance", None)
        if stack is not None and hasattr(stack, "attrs"):
            st = stack.attrs.get("stack")
            if st:
                frames = [f for f in st if isinstance(f, dict)]
                shown = "\n".join(
                    f"    at {f.get('function', '?')} ({f.get('file', '?')}:{f.get('line', '?')})"
                    for f in frames[:8]
                )
                message = message + ("\nstack trace:\n" + shown if shown else "")
        return format_error(error_type, message, line, col, source_code, filename, error_code=error_type)

    # Only override message for very generic messages — preserve descriptive ones
    if "lambda" in msg_lower or "E007" in str(getattr(exc, 'code', 'E000')):
        message = "invalid lambda syntax"
        code_str = "E007"
        suggestions = [
            "use func() for anonymous functions",
            "use |x| => expr for short lambdas",
        ]
    elif "semicolon" in msg_lower and "missing" in msg_lower:
        code_str = "E002"
        suggestions = ["add ';' at end of statement"]
    elif "undefined variable" in msg_lower:
        # Keep the original message — it already has helpful info like "Use 'let' to declare"
        code_str = "E004"
    elif "undefined name" in msg_lower or msg_lower.startswith("name '") and "not defined" in msg_lower:
        # Generic Python NameError — give KentScript-specific guidance
        # Extract the variable name from "name 'x' is not defined"
        m = re.search(r"name '(\w+)' is not defined", message)
        var_name = m.group(1) if m else None
        if var_name:
            message = f"undefined variable '{var_name}'"
            suggestions = [f"declare with 'let' before use: let {var_name} = ...;"]
        else:
            message = "undefined variable"
            suggestions = ["declare variable with 'let' before use"]
        code_str = "E004"
    elif "unexpected token" in msg_lower:
        code_str = "E001"
        if "//" in message:
            suggestions = ["Did you mean a comment? Use '::' instead of '//'", "// is the floor divide operator in KentScript"]

    return format_error(error_type, message, line, col, source_code, filename, suggestions if suggestions else None, error_code=code_str)


def syntax_error(msg, **kwargs):
    """Return formatted syntax error (don't print)"""
    return format_error("SyntaxError", msg, **kwargs)


class Colors:
    """For backwards compatibility"""
    RED = C.RED
    GREEN = C.GREEN
    YELLOW = C.YELLOW
    CYAN = C.CYAN
    WHITE = C.WHITE
    DIM = C.DIM
    BOLD = C.BOLD
    RESET = C.RESET


class ErrorFormatter:
    """For backwards compatibility"""
    format_error = staticmethod(format_error)
    format_exception = staticmethod(format_exception)
    syntax_error = staticmethod(syntax_error)
    
    @staticmethod
    def type_error(msg, **kwargs):
        return format_error("TypeError", msg, **kwargs)
    
    @staticmethod
    def name_error(msg, **kwargs):
        return format_error("NameError", msg, **kwargs)
    
    @staticmethod
    def runtime_error(msg, **kwargs):
        return format_error("RuntimeError", msg, **kwargs)
    
    @staticmethod
    def index_error(msg, **kwargs):
        return format_error("IndexError", msg, **kwargs)
    
    @staticmethod
    def format_error_summary(errors):
        """Return only the FIRST error as a string"""
        if errors:
            return errors[0]
        return ""


def error(msg, **kwargs):
    """Print error"""
    print(format_error("Error", msg, **kwargs))


def success(msg):
    print(f"{C.GREEN}✓ {msg}{C.RESET}")


def warning(msg):
    print(f"{C.YELLOW}⚠ {msg}{C.RESET}")


def info(msg):
    print(f"{C.CYAN}ℹ {msg}{C.RESET}")

class CErrorFormatter:
    """Parse GCC/Clang output and render as beautiful KentScript errors"""

    # Map GCC diagnostic keywords to KentScript error codes + suggestions
    _DIAG_MAP = {
        "error:": ("C001", C.RED, "error"),
        "warning:": ("C002", C.YELLOW, "warning"),
        "note:": ("C003", C.CYAN, "note"),
    }

    @classmethod
    def _parse_c_errors(cls, stderr, c_source):
        """Parse GCC/Clang stderr into structured error records."""
        errors = []
        lines = stderr.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            # Match: file.c:NNN:CC: severity: message
            m = re.match(
                r"^(.+?):(\d+):(\d+):\s+(error|warning|note):\s+(.+)$", line
            )
            if m:
                file_path, lineno, col, severity, message = m.groups()
                lineno = int(lineno)
                col = int(col)

                # Collect continuation lines (indented with | or starting with spaces)
                context_lines = []
                pointer_line = None
                j = i + 1
                while j < len(lines):
                    next_l = lines[j]
                    # Lines that are part of the diagnostic (indented, |, or "note:")
                    if re.match(r"^\s+[|\\^]", next_l) or next_l.strip().startswith("|"):
                        pointer_line = next_l
                        j += 1
                    elif re.match(r"^\s+note:", next_l):
                        break
                    elif next_l and not next_l[0].isspace() and ":" in next_l:
                        break
                    elif next_l.strip() == "":
                        j += 1
                        break
                    else:
                        context_lines.append(next_l)
                        j += 1

                # Collect "note:" lines as additional context
                notes = []
                while j < len(lines):
                    note_m = re.match(
                        r"^.+?:\d+:\d+:\s+note:\s+(.+)$", lines[j]
                    )
                    if note_m:
                        notes.append(note_m.group(1))
                        j += 1
                    elif lines[j].strip().startswith("|") or (lines[j] and lines[j][0].isspace() and "|" in lines[j]):
                        j += 1
                    else:
                        break

                errors.append({
                    "file": file_path,
                    "line": lineno,
                    "col": col,
                    "severity": severity,
                    "message": message.strip(),
                    "pointer": pointer_line,
                    "notes": notes,
                })
                i = j
            else:
                i += 1
        return errors

    @classmethod
    def _map_c_line_to_ks(cls, c_line, ks_source, ks_filename):
        """Try to find the corresponding KentScript line for a C line.

        Strategy: look for #line directives in the C source that map back to .ks
        """
        if not ks_source:
            return c_line, None

        c_lines = ks_source.splitlines() if isinstance(ks_source, str) else ks_source

        # Look backwards from c_line for a #line directive
        start = max(0, c_line - 50)
        for idx in range(c_line - 1, start - 1, -1):
            if idx < len(c_lines):
                m = re.match(r'^\s*#\s*line\s+(\d+)\s+"([^"]+)"', c_lines[idx])
                if m:
                    ks_line = int(m.group(1))
                    origin = m.group(2)
                    if ".ks" in origin or "kent" in origin.lower():
                        return ks_line, origin

        return c_line, None

    @classmethod
    def _categorize_error(cls, message):
        """Classify a C compiler error into a KentScript-level category."""
        msg = message.lower()

        if "makes integer from pointer" in msg or "makes pointer from integer" in msg:
            return {
                "category": "Type Mismatch",
                "code": "E005",
                "suggestion": "KentScript parameters without type annotations default to i64. Add type hints like `func f(name: str)` if you expect strings.",
            }
        if "implicit declaration" in msg:
            return {
                "category": "Undeclared Function",
                "code": "E004",
                "suggestion": "Declare the function before calling it, or check for typos in the function name.",
            }
        if "undefined reference" in msg:
            return {
                "category": "Linker Error",
                "code": "C010",
                "suggestion": "The function is declared but not defined. Make sure all functions have a body.",
            }
        if "unused variable" in msg or "unused" in msg:
            return {
                "category": "Unused Variable",
                "code": "C002",
                "suggestion": "Remove unused variables or prefix with '_' to suppress the warning.",
            }
        if "format" in msg:
            return {
                "category": "Format String Error",
                "code": "C005",
                "suggestion": "Check that format specifiers match argument types.",
            }
        if "expected" in msg:
            return {
                "category": "Syntax Error",
                "code": "E001",
                "suggestion": "Check for missing semicolons, brackets, or incorrect syntax.",
            }
        return {
            "category": "C Compiler Error",
            "code": "C001",
            "suggestion": None,
        }

    @classmethod
    def format_c_compiler_error(cls, stderr, c_source_file, ks_source=None, ks_filename=None):
        """Render GCC/Clang output as beautiful KentScript errors."""
        if not stderr or not stderr.strip():
            return f"{C.RED}{C.BOLD}error{C.RESET}{C.WHITE}: [C001] C compiler failed (no output){C.RESET}\n"

        c_source = None
        if c_source_file:
            try:
                with open(c_source_file, "r") as f:
                    c_source = f.read()
            except:
                pass

        c_errors = cls._parse_c_errors(stderr, c_source)

        if not c_errors:
            # Fallback: raw output with minimal styling
            return f"{C.RED}{C.BOLD}error{C.RESET}{C.WHITE}: [C001] C compilation failed{C.RESET}\n{C.DIM}{stderr}{C.RESET}\n"

        # Deduplicate: group errors at the same location
        seen = set()
        unique_errors = []
        for err in c_errors:
            key = (err["file"], err["line"], err["col"], err["message"])
            if key not in seen:
                seen.add(key)
                unique_errors.append(err)

        # Separate real errors from notes
        real_errors = [e for e in unique_errors if e["severity"] == "error"]
        warnings = [e for e in unique_errors if e["severity"] == "warning"]
        notes = [e for e in unique_errors if e["severity"] == "note"]

        output = []

        # Header
        error_count = len(real_errors)
        warning_count = len(warnings)
        if error_count > 0:
            output.append(
                f"{C.RED}{C.BOLD}compilation failed{C.RESET}{C.WHITE}: "
                f"{error_count} error{'s' if error_count != 1 else ''}"
                f"{f', {warning_count} warning' + ('s' if warning_count != 1 else '') if warning_count > 0 else ''}"
                f"{C.RESET}"
            )
            output.append("")
        elif warning_count > 0:
            output.append(
                f"{C.YELLOW}{C.BOLD}compilation warnings{C.RESET}{C.WHITE}: "
                f"{warning_count} warning{'s' if warning_count != 1 else ''}"
                f"{C.RESET}"
            )
            output.append("")

        # Render each error
        for err in real_errors + warnings:
            info = cls._categorize_error(err["message"])

            # Map C line to KentScript line
            ks_line, ks_origin = cls._map_c_line_to_ks(err["line"], c_source, ks_filename)
            display_file = ks_filename or ks_origin or err["file"]
            display_line = ks_line

            # Error header
            color = C.RED if err["severity"] == "error" else C.YELLOW
            output.append(
                f"{color}{C.BOLD}{err['severity']}{C.RESET}{C.WHITE}: "
                f"[{info['code']}] {info['category']} — {err['message']}{C.RESET}"
            )

            # Location
            loc = f"{display_file}:{display_line or '?'}"
            if err["col"]:
                loc += f":{err['col']}"
            output.append(f"{C.DIM}  --> {loc}{C.RESET}")
            output.append("")

            # Source context from KentScript
            if ks_source and display_line:
                ks_lines = ks_source.splitlines() if isinstance(ks_source, str) else ks_source
                start = max(0, display_line - 3)
                end = min(len(ks_lines), display_line + 2)

                for idx in range(start, end):
                    num = idx + 1
                    prefix = f"{C.DIM}{num:>4}{C.RESET} │ "
                    line_content = ks_lines[idx] if idx < len(ks_lines) else ""

                    if num == display_line:
                        output.append(f"{prefix}{line_content}")
                        if err["col"] and err["col"] > 0:
                            pointer = " " * (err["col"] + 6)
                            output.append(f"{C.DIM}         {pointer}{color}{'^^^'}{C.RESET}")
                    else:
                        output.append(f"{C.DIM}{prefix}{line_content}{C.RESET}")

                output.append("")
            elif c_source:
                # Show C source as fallback
                c_lines = c_source.splitlines() if isinstance(c_source, str) else c_source
                start = max(0, err["line"] - 2)
                end = min(len(c_lines), err["line"] + 1)

                for idx in range(start, end):
                    num = idx + 1
                    prefix = f"{C.DIM}{num:>4}{C.RESET} │ "
                    line_content = c_lines[idx] if idx < len(c_lines) else ""

                    if num == err["line"]:
                        output.append(f"{prefix}{line_content}")
                    else:
                        output.append(f"{C.DIM}{prefix}{line_content}{C.RESET}")

                output.append("")

            # Notes
            for note in err["notes"]:
                output.append(f"{C.CYAN}{C.BOLD}note:{C.RESET} {note}")

            # Suggestion
            if info["suggestion"]:
                output.append("")
                output.append(f"{C.YELLOW}{C.BOLD}help:{C.RESET} {info['suggestion']}")

            output.append("")

        # Summary
        if error_count > 0:
            output.append(
                f"{C.RED}{C.BOLD}error{C.RESET}{C.WHITE}: could not compile {ks_filename or c_source_file}{C.RESET}"
            )

        return "\n".join(output)
