#!/usr/bin/env python3
"""
KentScript Debugger - Runtime debugging and step-through execution
"""

import sys
import os
import readline
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field

try:
    from termcolor import colored

    HAS_TERMCOLOR = True
except ImportError:
    HAS_TERMCOLOR = False


@dataclass
class Breakpoint:
    line: int
    condition: Optional[str] = None
    enabled: bool = True
    hits: int = 0


@dataclass
class StackFrame:
    name: str
    line: int
    filename: str
    locals: Dict[str, Any] = field(default_factory=dict)


class DebuggerQuit(Exception):
    """Raised when the user quits a debug session to stop program execution."""


class KentScriptDebugger:
    def __init__(
        self,
        source: str = "",
        filename: str = "<stdin>",
        stop_on_entry: bool = False,
        breakpoint_lines: List[int] = None,
        max_steps: int = 0,
        inspect_vars: List[str] = None,
    ):
        self.source = source
        self.source_lines = source.split("\n") if source else []
        self.filename = filename
        self.stop_on_entry = stop_on_entry
        self.breakpoints: List[Breakpoint] = []
        self.breakpoint_lines: Set[int] = set(breakpoint_lines or [])
        self.max_steps = max_steps
        self.inspect_vars: Set[str] = set(inspect_vars or [])
        self.step_mode = False   # when True, pause at every executed line

        # Execution state
        self.step_count = 0
        self.break_hits: List[dict] = []
        self.running = True
        self.paused = False
        self.current_line = 0
        self.current_env: Optional[Dict] = None

        # Call stack
        self.call_stack: List[StackFrame] = []

        # Breakpoint conditions
        self.conditions: Dict[int, Callable] = {}

        # Auto-continue on certain errors
        self.ignore_errors = False

        # Initialize breakpoints
        for line in self.breakpoint_lines:
            self.breakpoints.append(Breakpoint(line=line))

    def add_breakpoint(self, line: int, condition: Optional[str] = None) -> Breakpoint:
        bp = Breakpoint(line=line, condition=condition)
        self.breakpoints.append(bp)
        self.breakpoint_lines.add(line)
        print(f"[DEBUG] Breakpoint added at line {line}")
        return bp

    def remove_breakpoint(self, line: int) -> bool:
        for bp in self.breakpoints:
            if bp.line == line:
                self.breakpoints.remove(bp)
                self.breakpoint_lines.discard(line)
                print(f"[DEBUG] Breakpoint removed from line {line}")
                return True
        return False

    def list_breakpoints(self) -> List[Breakpoint]:
        return self.breakpoints

    def clear_breakpoints(self):
        self.breakpoints.clear()
        self.breakpoint_lines.clear()
        print("[DEBUG] All breakpoints cleared")

    def check_breakpoint(self, line: int) -> bool:
        for bp in self.breakpoints:
            if bp.enabled and bp.line == line:
                bp.hits += 1
                self.break_hits.append(
                    {"line": line, "hits": bp.hits, "condition": bp.condition}
                )

                # Check condition if exists
                if bp.condition:
                    try:
                        if not eval(bp.condition, {}, self.current_env or {}):
                            return False
                    except:
                        pass

                return True
        return False

    def should_stop(self, line: int, env: Optional[Dict] = None) -> bool:
        """Check if execution should stop at this line"""
        self.current_line = line
        if env:
            self.current_env = env

        # Stop on entry (very first line) when requested
        if self.stop_on_entry and self.step_count == 0:
            self.stop(line, env, "entry")
            return True

        self.step_count += 1

        # Check max steps
        if self.max_steps > 0 and self.step_count >= self.max_steps:
            print(f"[DEBUG] Max steps ({self.max_steps}) reached")
            self.stop(line, env, "max steps")
            return True

        # Step mode: pause at every line until 'continue' clears it
        if self.step_mode:
            self.stop(line, env, "step")
            return True

        # Check breakpoints
        if self.check_breakpoint(line):
            self.stop(line, env, "breakpoint")
            return True

        return False

    def stop(self, line: int, env: Optional[Dict] = None, reason: str = "breakpoint"):
        """Stop execution and enter debug REPL"""
        self.paused = True
        self.current_line = line
        if env:
            self.current_env = env

        self._print_location(line)
        print(f"\n[DEBUG] Stopped: {reason}")
        self._debug_repl()
        if not self.running:
            raise DebuggerQuit()

    def _print_location(self, line: int):
        """Print current location in source"""
        if not self.source_lines:
            print(f"--> {self.filename}:{line}")
            return

        print(f"\n--> {self.filename}:{line}")

        # Show context (3 lines before and after)
        start = max(0, line - 3)
        end = min(len(self.source_lines), line + 2)

        for i in range(start, end):
            marker = ">>>" if (i + 1) == line else "   "
            prefix = (
                f"{marker} {i + 1:4d} | "
                if HAS_TERMCOLOR
                else f"{marker} {i + 1:4d} | "
            )
            content = self.source_lines[i] if i < len(self.source_lines) else ""

            if i == line and HAS_TERMCOLOR:
                print(colored(prefix + content, "cyan", "bold"))
            elif i == line:
                print(prefix + content)
            else:
                print(prefix + content)

    def _print_locals(self, env: Optional[Dict] = None):
        """Print local variables"""
        e = env or self.current_env
        if not e:
            print("[DEBUG] No local variables")
            return

        print("\n[DEBUG] Local variables:")
        for name, value in sorted(e.items()):
            if not name.startswith("_"):
                val_str = str(value)[:50]
                print(f"  {name} = {val_str}")

    def _print_stack(self):
        """Print call stack"""
        if not self.call_stack:
            print("[DEBUG] Call stack empty")
            return

        print("\n[DEBUG] Call stack:")
        for i, frame in enumerate(reversed(self.call_stack[-5:])):
            print(f"  #{i} {frame.name} at {frame.filename}:{frame.line}")

    def show_locals(self):
        """Show local variables (command)"""
        self._print_locals()

    def show_backtrace(self):
        """Show call stack (command)"""
        self._print_stack()

    def _debug_repl(self):
        """Interactive debug REPL"""
        print(
            "\n[DEBUG] Commands: s(tep), n(ext), c(ontinue), b(reak) [line], p(rint) <var>, bt, l(ocals), q(uit), h(elp)"
        )

        while self.paused and self.running:
            try:
                cmd = input("(debug) ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[DEBUG] Interrupting...")
                self.running = False
                break

            if not cmd:
                continue

            parts = cmd.split()
            op = parts[0].lower()
            args = parts[1:]

            if op in ("s", "step"):
                print(f"[DEBUG] Stepping... (total steps: {self.step_count})")
                self.step_mode = True
                self.paused = False
                break

            elif op in ("n", "next", "ni"):
                print("[DEBUG] Next (step over)")
                self.step_mode = True
                self.paused = False
                break

            elif op in ("c", "cont", "continue"):
                print("[DEBUG] Continuing...")
                self.step_mode = False
                self.paused = False
                break

            elif op in ("b", "break"):
                if args:
                    try:
                        line = int(args[0])
                        self.add_breakpoint(line)
                    except ValueError:
                        print("[DEBUG] Usage: break <line>")
                else:
                    print("[DEBUG] Breakpoints:")
                    for bp in self.breakpoints:
                        print(f"  line {bp.line} (hits: {bp.hits})")

            elif op in ("d", "delete"):
                if args:
                    try:
                        line = int(args[0])
                        self.remove_breakpoint(line)
                    except ValueError:
                        print("[DEBUG] Usage: delete <line>")

            elif op in ("p", "print", "ex", "exam"):
                if args:
                    var = args[0]
                    env = self.current_env or {}
                    if var in env:
                        print(f"{var} = {repr(env[var])}")
                    else:
                        print(f"[DEBUG] Variable '{var}' not found")
                else:
                    print("[DEBUG] Usage: print <variable>")

            elif op in ("bt", "back", "where"):
                self._print_stack()

            elif op in ("l", "loc", "locals"):
                self._print_locals()

            elif op in ("s", "source"):
                if args:
                    try:
                        start = int(args[0])
                        end = start + 10
                        for i in range(start - 1, min(end, len(self.source_lines))):
                            print(f"{i + 1:4d} | {self.source_lines[i]}")
                    except:
                        print("[DEBUG] Usage: source <line>")
                else:
                    self._print_location(self.current_line)

            elif op in ("q", "quit", "exit"):
                print("[DEBUG] Quitting...")
                self.running = False
                self.paused = False
                break

            elif op in ("h", "help", "?"):
                print("""
Debugger commands:
  s, step     - Execute next line, step into functions
  n, next     - Execute next line, step over calls
  c, continue - Continue execution
  b, break    - Set breakpoint (b <line>)
  d, delete   - Remove breakpoint (d <line>)
  p, print    - Print variable (p <name>)
  bt, where   - Show call stack
  l, locals   - Show local variables
  source      - Show source around current line
  q, quit     - Quit debugging
  h, help     - Show this help
                """)

            else:
                print(f"[DEBUG] Unknown command: {op}")

    def run_interactive(self):
        """Run the debugger in interactive mode"""
        print("KentScript Debugger")
        print(f"File: {self.filename}")
        print(f"Breakpoints: {len(self.breakpoints)}")
        print("Type 'help' for commands\n")

        self.running = True
        self._debug_repl()

    def evaluate(self, expr: str, env: Optional[Dict] = None) -> Any:
        """Evaluate an expression in the current context"""
        try:
            e = env or self.current_env or {}
            return eval(expr, {"__builtins__": __builtins__}, e)
        except Exception as ex:
            return f"Error: {ex}"


class DebugProxy:
    """Proxy object to wrap interpreter for debugging"""

    def __init__(self, debugger: KentScriptDebugger):
        self.debugger = debugger

    def before_eval(self, node, env: Dict):
        """Called before evaluating a node"""
        line = getattr(node, "line", None)
        if line and self.debugger.should_stop(line, env):
            self.debugger.stop(line, env, "step")

    def after_eval(self, node, result, env: Dict):
        """Called after evaluating a node"""
        pass


def create_debugger(
    source: str = "",
    filename: str = "<stdin>",
    stop_on_entry: bool = False,
    breakpoints: List[int] = None,
    max_steps: int = 0,
    inspect: List[str] = None,
) -> KentScriptDebugger:
    """Factory function to create a debugger"""
    return KentScriptDebugger(
        source=source,
        filename=filename,
        stop_on_entry=stop_on_entry,
        breakpoint_lines=breakpoints,
        max_steps=max_steps,
        inspect_vars=inspect,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="KentScript Debugger")
    parser.add_argument("file", help="KentScript source file")
    parser.add_argument("-s", "--stop", action="store_true", help="Stop at entry")
    parser.add_argument(
        "-b",
        "--break",
        dest="breakpoints",
        action="append",
        type=int,
        help="Breakpoint line",
    )
    parser.add_argument("--steps", type=int, default=0, help="Max steps")
    parser.add_argument(
        "-v", "--var", dest="vars", action="append", help="Variables to watch"
    )

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    with open(args.file, "r") as f:
        source = f.read()

    debugger = KentScriptDebugger(
        source=source,
        filename=args.file,
        stop_on_entry=args.stop,
        breakpoint_lines=args.breakpoints,
        max_steps=args.steps,
        inspect_vars=args.vars,
    )

    print(f"Debugger ready for {args.file}")
    print(f"Breakpoints: {debugger.breakpoint_lines}")
