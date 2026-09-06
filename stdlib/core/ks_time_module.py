"""
KentScript Time Module - Full Implementation
Fully compatible with Python's time module with optimizations
"""

import time as _time
import datetime as _datetime
from typing import Tuple, Optional, Any, Union
from dataclasses import dataclass
import calendar as _calendar


# Constants
CLOCK_REALTIME = 0
CLOCK_MONOTONIC = 1
CLOCK_PERF_COUNTER = 2
CLOCK_PROCESS_CPUTIME = 3
CLOCK_THREAD_CPUTIME = 4

# Sleep precision for various OSes (approximate)
SLEEP_RESOLUTION = 0.0001  # 0.1ms typical on modern systems


@dataclass
class TimeResult:
    """Result of time operations"""
    seconds: float
    nanoseconds: int = 0
    
    @property
    def total_ns(self) -> int:
        """Get total time in nanoseconds"""
        return int(self.seconds * 1_000_000_000) + self.nanoseconds
    
    @property
    def total_us(self) -> float:
        """Get total time in microseconds"""
        return self.total_ns / 1000
    
    @property
    def total_ms(self) -> float:
        """Get total time in milliseconds"""
        return self.total_ns / 1_000_000


class TimeStruct:
    """Enhanced time.struct_time with additional fields"""
    
    def __init__(self, time_tuple: _time.struct_time):
        self.tm_year = time_tuple.tm_year
        self.tm_mon = time_tuple.tm_mon
        self.tm_mday = time_tuple.tm_mday
        self.tm_hour = time_tuple.tm_hour
        self.tm_min = time_tuple.tm_min
        self.tm_sec = time_tuple.tm_sec
        self.tm_wday = time_tuple.tm_wday
        self.tm_yday = time_tuple.tm_yday
        self.tm_isdst = time_tuple.tm_isdst
    
    def to_tuple(self) -> Tuple:
        """Convert to standard tuple"""
        return (
            self.tm_year, self.tm_mon, self.tm_mday,
            self.tm_hour, self.tm_min, self.tm_sec,
            self.tm_wday, self.tm_yday, self.tm_isdst
        )
    
    def __repr__(self) -> str:
        return f"time.struct_time({self.to_tuple()})"


class TimeDelta:
    """Optimized timedelta"""
    
    __slots__ = ('_seconds', '_microseconds')
    
    def __init__(self, days=0, seconds=0, microseconds=0, 
                 milliseconds=0, minutes=0, hours=0, weeks=0):
        """Initialize timedelta with multiple units"""
        total_seconds = (
            days * 86400 +
            seconds +
            minutes * 60 +
            hours * 3600 +
            weeks * 604800
        )
        total_microseconds = microseconds + milliseconds * 1000
        
        self._seconds = total_seconds
        self._microseconds = total_microseconds
    
    @property
    def total_seconds(self) -> float:
        """Get total seconds including microseconds"""
        return self._seconds + self._microseconds / 1_000_000
    
    def __add__(self, other):
        if isinstance(other, TimeDelta):
            return TimeDelta(
                seconds=self._seconds + other._seconds,
                microseconds=self._microseconds + other._microseconds
            )
        return NotImplemented
    
    def __sub__(self, other):
        if isinstance(other, TimeDelta):
            return TimeDelta(
                seconds=self._seconds - other._seconds,
                microseconds=self._microseconds - other._microseconds
            )
        return NotImplemented
    
    def __mul__(self, scalar):
        if isinstance(scalar, (int, float)):
            return TimeDelta(
                seconds=self._seconds * scalar,
                microseconds=self._microseconds * scalar
            )
        return NotImplemented
    
    def __repr__(self) -> str:
        return f"TimeDelta(seconds={self.total_seconds})"


# ============================================================================
# HIGH-PRECISION TIMING
# ============================================================================

def perf_counter() -> float:
    """High-resolution performance counter (recommended for benchmarking)"""
    return _time.perf_counter()


def perf_counter_ns() -> int:
    """High-resolution performance counter in nanoseconds"""
    return _time.perf_counter_ns()


def monotonic() -> float:
    """Monotonic clock (never goes backwards)"""
    return _time.monotonic()


def monotonic_ns() -> int:
    """Monotonic clock in nanoseconds"""
    return _time.monotonic_ns()


def process_time() -> float:
    """CPU time for current process"""
    return _time.process_time()


def process_time_ns() -> int:
    """CPU time in nanoseconds"""
    return _time.process_time_ns()


def thread_time() -> float:
    """CPU time for current thread"""
    return _time.thread_time()


def thread_time_ns() -> int:
    """CPU time for current thread in nanoseconds"""
    return _time.thread_time_ns()


# ============================================================================
# STANDARD TIME FUNCTIONS
# ============================================================================

def time() -> float:
    """Current wall-clock time (seconds since epoch)"""
    return _time.time()


def time_ns() -> int:
    """Current time in nanoseconds since epoch"""
    return _time.time_ns()


def sleep(seconds: float) -> None:
    """Sleep for specified seconds (supports fractional)"""
    _time.sleep(max(0, seconds))


def sleep_precise(seconds: float, busy_wait: bool = False) -> None:
    """
    Sleep with optional busy-wait for precision
    Useful when SLEEP_RESOLUTION isn't good enough
    """
    if busy_wait:
        start = perf_counter()
        while perf_counter() - start < seconds:
            pass
    else:
        _time.sleep(max(0, seconds))


# ============================================================================
# TIME CONVERSION FUNCTIONS
# ============================================================================

def gmtime(secs: Optional[float] = None) -> TimeStruct:
    """Convert seconds to UTC time structure"""
    if secs is None:
        secs = time()
    return TimeStruct(_time.gmtime(secs))


def localtime(secs: Optional[float] = None) -> TimeStruct:
    """Convert seconds to local time structure"""
    if secs is None:
        secs = time()
    return TimeStruct(_time.localtime(secs))


def mktime(time_tuple: Union[Tuple, TimeStruct]) -> float:
    """Convert time structure to seconds"""
    if isinstance(time_tuple, TimeStruct):
        time_tuple = time_tuple.to_tuple()
    return _time.mktime(time_tuple)


def asctime(time_tuple: Optional[Union[Tuple, TimeStruct]] = None) -> str:
    """Convert time structure to formatted string"""
    if time_tuple is None:
        time_tuple = localtime()
    if isinstance(time_tuple, TimeStruct):
        time_tuple = time_tuple.to_tuple()
    return _time.asctime(time_tuple)


def ctime(secs: Optional[float] = None) -> str:
    """Convert seconds to formatted date string"""
    if secs is None:
        secs = time()
    return _time.ctime(secs)


def strftime(fmt: str, time_tuple: Optional[Union[Tuple, TimeStruct]] = None) -> str:
    """Format time using strftime format string"""
    if time_tuple is None:
        time_tuple = localtime()
    if isinstance(time_tuple, TimeStruct):
        time_tuple = time_tuple.to_tuple()
    return _time.strftime(fmt, time_tuple)


def strptime(date_string: str, fmt: str) -> TimeStruct:
    """Parse time string using format"""
    return TimeStruct(_time.strptime(date_string, fmt))


# ============================================================================
# TIMEZONE FUNCTIONS
# ============================================================================

def timezone() -> int:
    """Offset of local timezone from UTC in seconds"""
    return _time.timezone


def altzone() -> int:
    """Offset of local DST timezone from UTC in seconds"""
    return _time.altzone


def daylight() -> int:
    """Whether DST is defined (0 or non-zero)"""
    return _time.daylight


def tzname() -> Tuple[str, str]:
    """Names of local timezone and DST timezone"""
    return _time.tzname


# ============================================================================
# BENCHMARKING UTILITIES
# ============================================================================

class Timer:
    """Context manager for measuring elapsed time"""
    
    __slots__ = ('_name', '_verbose', '_start', 'elapsed')
    
    def __init__(self, name: str = "Timer", verbose: bool = True):
        self._name = name
        self._verbose = verbose
        self._start = None
        self.elapsed = 0.0
    
    def __enter__(self):
        self._start = perf_counter()
        return self
    
    def __exit__(self, *args):
        self.elapsed = perf_counter() - self._start
        if self._verbose:
            print(f"{self._name}: {self.elapsed:.6f}s")
        return False
    
    def __repr__(self) -> str:
        return f"Timer({self.elapsed:.6f}s)"


class StopWatch:
    """High-precision stopwatch for manual timing"""
    
    __slots__ = ('_start', '_total', '_running')
    
    def __init__(self):
        self._start = None
        self._total = 0.0
        self._running = False
    
    def start(self) -> None:
        """Start the stopwatch"""
        if not self._running:
            self._start = perf_counter()
            self._running = True
    
    def stop(self) -> float:
        """Stop the stopwatch and return elapsed time"""
        if self._running:
            elapsed = perf_counter() - self._start
            self._total += elapsed
            self._running = False
            return elapsed
        return 0.0
    
    def reset(self) -> None:
        """Reset the stopwatch"""
        self._total = 0.0
        self._running = False
        self._start = None
    
    @property
    def total(self) -> float:
        """Get total elapsed time"""
        result = self._total
        if self._running:
            result += perf_counter() - self._start
        return result
    
    def __repr__(self) -> str:
        return f"StopWatch({self.total:.6f}s)"


def measure_duration(func, *args, **kwargs) -> Tuple[Any, float]:
    """
    Measure execution time of a function
    Returns (result, elapsed_time)
    """
    start = perf_counter()
    result = func(*args, **kwargs)
    elapsed = perf_counter() - start
    return result, elapsed


def timed(func):
    """Decorator to time function execution"""
    def wrapper(*args, **kwargs):
        result, elapsed = measure_duration(func, *args, **kwargs)
        print(f"{func.__name__} took {elapsed:.6f}s")
        return result
    return wrapper


# ============================================================================
# ADVANCED UTILITIES
# ============================================================================

def get_clock_source() -> str:
    """Get information about system clock"""
    import platform
    return f"Clock: {platform.platform()}, Resolution: ~{SLEEP_RESOLUTION*1000:.3f}ms"


def estimate_sleep_precision() -> float:
    """Estimate actual sleep precision on this system"""
    samples = []
    target = 0.001  # 1ms
    
    for _ in range(5):
        start = perf_counter()
        _time.sleep(target)
        actual = perf_counter() - start
        samples.append(actual)
    
    import statistics
    return statistics.mean(samples)


def time_function_repeated(func, times: int = 100, *args, **kwargs) -> dict:
    """Time a function multiple times and return statistics"""
    times_list = []
    
    for _ in range(times):
        start = perf_counter()
        func(*args, **kwargs)
        times_list.append(perf_counter() - start)
    
    import statistics
    return {
        'min': min(times_list),
        'max': max(times_list),
        'mean': statistics.mean(times_list),
        'median': statistics.median(times_list),
        'stdev': statistics.stdev(times_list) if len(times_list) > 1 else 0,
        'total': sum(times_list),
        'count': times,
    }


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

# Pre-computed constants for faster access
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
SECONDS_PER_WEEK = 604800
SECONDS_PER_YEAR = 31536000


def get_uptime() -> float:
    """Get system uptime in seconds"""
    return monotonic()


def delta(seconds: float) -> TimeDelta:
    """Create a TimeDelta"""
    return TimeDelta(seconds=seconds)
