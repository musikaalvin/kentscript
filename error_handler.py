"""
Centralized Error Handler for KentScript
Wraps error_formatter.py for consistent error handling across all modules
"""

from error_formatter import (
    ErrorFormatter, 
    KentScriptSyntaxError, 
    KentScriptTypeError, 
    KentScriptNameError
)
import sys

class KSError:
    """Centralized error handler with source tracking"""
    
    _current_file = None
    _current_source = None
    _errors: list = []          # accumulated errors (formatted strings)
    _collecting: bool = False   # when True, collect instead of raise

    @classmethod
    def set_context(cls, filename=None, source=None):
        """Set current file context for error reporting"""
        cls._current_file = filename
        cls._current_source = source

    @classmethod
    def begin_collection(cls):
        """Start collecting errors instead of raising immediately."""
        cls._errors = []
        cls._first_error = None  # Store first error
        cls._collecting = True

    @classmethod
    def end_collection(cls):
        """Stop collecting and return only the FIRST error."""
        cls._collecting = False
        errors = cls._errors[:]
        cls._errors = []
        # Return only the first error
        if cls._first_error:
            return [cls._first_error]
        return errors[:1] if errors else []

    @classmethod
    def _record_or_raise(cls, exc, formatted: str):
        """Either collect the error or raise it immediately."""
        if cls._collecting:
            # Only keep the first error
            if cls._first_error is None:
                cls._first_error = formatted
            return  # Don't add subsequent errors
        else:
            exc.formatted = formatted
            raise exc

    @classmethod
    def has_errors(cls) -> bool:
        return bool(cls._errors) or bool(cls._first_error)

    @classmethod
    def wrap_exception(cls, exc_type, exc_value, exc_traceback):
        """Global exception hook to format all unhandled exceptions"""
        # Don't print for KentScript errors - they're handled by the REPL
        exc_name = type(exc_value).__name__
        if exc_name in ('KentScriptSyntaxError', 'KentScriptTypeError', 'KentScriptNameError'):
            # Let the REPL handle these
            return
        
        # Check if already formatted
        if hasattr(exc_value, 'formatted'):
            print(exc_value.formatted, file=sys.stderr)
            return
        
        # Try to extract line info from traceback
        line = None
        col = None
        if exc_traceback:
            line = exc_traceback.tb_lineno
        
        # Format the exception
        formatted = ErrorFormatter.format_exception(
            exc_value,
            filename=cls._current_file,
            source_code=cls._current_source
        )
        print(formatted, file=sys.stderr)
    
    @classmethod
    def syntax_error(cls, message, line=None, col=None, hint=None, suggestion=None, start_line=None, start_col=None):
        """Raise or collect formatted syntax error"""
        formatted = ErrorFormatter.syntax_error(
            message, 
            line=line, 
            col=col, 
            source_lines=cls._current_source,
            filename=cls._current_file,
            hint=hint,
            suggestion=suggestion,
            start_line=start_line,
            start_col=start_col
        )
        exc = KentScriptSyntaxError(
            message, 
            line=line, 
            col=col, 
            source=cls._current_source,
            filename=cls._current_file
        )
        cls._record_or_raise(exc, formatted)
    
    @classmethod
    def runtime_error(cls, message, line=None, col=None, hint=None):
        """Raise or collect formatted runtime error"""
        formatted = ErrorFormatter.runtime_error(
            message, 
            line=line, 
            col=col, 
            source_lines=cls._current_source,
            filename=cls._current_file,
            hint=hint
        )
        exc = RuntimeError(message)
        cls._record_or_raise(exc, formatted)
    
    @classmethod
    def name_error(cls, message, line=None, col=None, hint=None):
        """Raise or collect formatted name error"""
        formatted = ErrorFormatter.name_error(
            message, 
            line=line, 
            col=col, 
            source_lines=cls._current_source,
            filename=cls._current_file,
            hint=hint
        )
        exc = KentScriptNameError(
            message, 
            line=line, 
            col=col, 
            source=cls._current_source,
            filename=cls._current_file
        )
        cls._record_or_raise(exc, formatted)

    @classmethod
    def type_error(cls, message, line=None, col=None, hint=None):
        """Raise or collect formatted type error"""
        formatted = ErrorFormatter.type_error(
            message, 
            line=line, 
            col=col, 
            source_lines=cls._current_source,
            filename=cls._current_file,
            hint=hint
        )
        exc = KentScriptTypeError(
            message, 
            line=line, 
            col=col, 
            source=cls._current_source,
            filename=cls._current_file
        )
        cls._record_or_raise(exc, formatted)
    
    @classmethod
    def index_error(cls, message, index=None, length=None, line=None, col=None):
        """Raise or collect formatted index error"""
        formatted = ErrorFormatter.index_error(
            message, index=index, length=length,
            line=line, col=col,
            source_lines=cls._current_source,
            filename=cls._current_file
        )
        exc = IndexError(message)
        cls._record_or_raise(exc, formatted)

    @classmethod
    def value_error(cls, message, line=None, col=None, hint=None):
        """Raise or collect formatted value error"""
        formatted = ErrorFormatter.format_error(
            "ValueError", message,
            line=line, col=col,
            source_lines=cls._current_source,
            filename=cls._current_file,
            hint=hint
        )
        exc = ValueError(message)
        cls._record_or_raise(exc, formatted)
    
    @classmethod
    def format_exception(cls, exc, filename=None, source=None):
        """Format any exception with error formatter"""
        return ErrorFormatter.format_exception(
            exc, 
            filename=filename or cls._current_file,
            source_code=source or cls._current_source
        )
    
    @classmethod
    def print_exception(cls, exc, filename=None, source=None):
        """Print formatted exception"""
        # Check if exception already has formatted output
        if hasattr(exc, 'formatted'):
            print(exc.formatted, file=sys.stderr)
        else:
            formatted = cls.format_exception(exc, filename, source)
            print(formatted, file=sys.stderr)
