"""
KentScript Enhanced Runtime Integration
Integrates benchmarking, time module, loops, data types, and optimizations
"""

import sys
import types
from typing import Any, Dict, Optional, Callable
import importlib

# Import all enhancement modules
from benchmark import (
    BenchmarkSuite, BenchmarkResult, TimerContext,
    create_benchmark_suite, quick_time, adaptive_benchmark
)

from ks_time_module import (
    time, sleep, perf_counter, monotonic,
    Timer, StopWatch, measure_duration,
    gmtime, localtime, mktime, strftime,
    TimeDelta
)

from loop_optimizer import (
    Range, for_loop, while_loop, do_while_loop,
    parallel_for, batch_process, EnhancedFor,
    loop_range, LoopOptimization
)

from data_types import (
    LangList, LangDict, LangSet, LangTuple, LangDeque,
    Matrix, String, Integer, Float, Bool,
    TypeConverter, TypeInfo, create_type
)

from ks_optimization import (
    optimize, profile, get_profiler,
    InliningOptimizer, LoopOptimizer,
    FunctionProfiler, get_framework
)


# ============================================================================
# ENHANCED BUILTINS
# ============================================================================

class StdBuiltins:
    """Enhanced builtins for KentScript"""
    
    # Data type constructors
    list = LangList
    dict = LangDict
    set = LangSet
    tuple = LangTuple
    deque = LangDeque
    string = String
    int = Integer
    float = Float
    bool = Bool
    matrix = Matrix
    
    # Loop constructs
    range = Range
    for_loop = for_loop
    while_loop = while_loop
    do_while_loop = do_while_loop
    parallel_for = parallel_for
    batch_process = batch_process
    
    # Time utilities
    Timer = Timer
    StopWatch = StopWatch
    time = time
    sleep = sleep
    perf_counter = perf_counter
    monotonic = monotonic
    
    # Benchmarking
    BenchmarkSuite = BenchmarkSuite
    create_benchmark_suite = create_benchmark_suite
    quick_time = quick_time
    adaptive_benchmark = adaptive_benchmark
    
    # Optimization decorators
    optimize = optimize
    profile = profile
    
    # Utilities
    measure_duration = measure_duration
    type_converter = TypeConverter


def install_enhanced_builtins() -> None:
    """Install enhanced builtins into Python environment"""
    
    # Store original builtins
    import builtins
    
    # Add KentScript enhancements
    builtins.ks = StdBuiltins
    builtins.ks_list = LangList
    builtins.ks_dict = LangDict
    builtins.ks_set = LangSet
    builtins.ks_range = Range
    builtins.ks_timer = Timer
    builtins.ks_benchmark = create_benchmark_suite


# ============================================================================
# RUNTIME ENVIRONMENT
# ============================================================================

class Runtime:
    """KentScript runtime environment"""
    
    def __init__(self, optimization_level: int = 2):
        self.optimization_level = optimization_level
        self.builtins = StdBuiltins()
        self.global_scope: Dict[str, Any] = {}
        self.profiler = FunctionProfiler()
        self._initialize_scope()
    
    def _initialize_scope(self) -> None:
        """Initialize global scope with builtins"""
        # Add all builtins to global scope
        self.global_scope.update({
            'list': LangList,
            'dict': LangDict,
            'set': LangSet,
            'tuple': LangTuple,
            'range': Range,
            'Timer': Timer,
            'StopWatch': StopWatch,
            'time': time,
            'sleep': sleep,
            'perf_counter': perf_counter,
            'benchmark': create_benchmark_suite,
            'optimize': optimize,
            'profile': profile,
        })
        
        # Python builtins
        self.global_scope.update({
            'print': print,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sum': sum,
            'min': min,
            'max': max,
            'sorted': sorted,
            'abs': abs,
            'pow': pow,
            'round': round,
            'divmod': divmod,
            'isinstance': isinstance,
            'type': type,
        })
    
    def execute(self, code: str, local_scope: Optional[Dict] = None) -> Any:
        """Execute KentScript code"""
        scope = {**self.global_scope, **(local_scope or {})}
        
        try:
            return eval(code, scope)
        except SyntaxError:
            # Try as statements
            exec(code, scope)
            return None
    
    def optimize_function(self, func: Callable) -> Callable:
        """Optimize a function using current settings"""
        if self.optimization_level == 0:
            return func
        
        if self.optimization_level >= 2:
            func = self.profiler.profile(func)
        
        return func
    
    def get_profiler(self) -> FunctionProfiler:
        """Get the runtime's profiler"""
        return self.profiler
    
    def print_stats(self) -> None:
        """Print profiling statistics"""
        self.profiler.print_stats()


# ============================================================================
# GLOBAL RUNTIME INSTANCE
# ============================================================================

_default_runtime: Optional[Runtime] = None


def get_runtime(optimization_level: int = 2) -> Runtime:
    """Get or create the default runtime"""
    global _default_runtime
    
    if _default_runtime is None:
        _default_runtime = Runtime(optimization_level)
    
    return _default_runtime


def set_optimization_level(level: int) -> None:
    """Set global optimization level"""
    runtime = get_runtime()
    runtime.optimization_level = level


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def benchmark(name: str = "Benchmark") -> BenchmarkSuite:
    """Create a new benchmark suite"""
    return create_benchmark_suite(name)


def timer(name: str = "Timer", verbose: bool = True) -> TimerContext:
    """Create a timer context"""
    return Timer(name, verbose)


def profile_function(func: Callable) -> Callable:
    """Profile a function"""
    runtime = get_runtime()
    return runtime.profiler.profile(func)


def optimize_function(func: Callable, level: int = 2) -> Callable:
    """Optimize a function"""
    runtime = get_runtime()
    runtime.optimization_level = level
    return runtime.optimize_function(func)


def get_loop_range(start: int, stop: int, step: int = 1) -> Range:
    """Get an optimized loop range"""
    return Range(start, stop, step)


# ============================================================================
# FORMATTED OUTPUT
# ============================================================================

class Formatter:
    """Advanced formatting utilities"""
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """Format seconds into readable time"""
        if seconds < 0.001:
            return f"{seconds*1e6:.2f}μs"
        elif seconds < 1:
            return f"{seconds*1e3:.2f}ms"
        elif seconds < 60:
            return f"{seconds:.2f}s"
        else:
            minutes = seconds / 60
            return f"{minutes:.2f}m"
    
    @staticmethod
    def format_bytes(bytes_val: int) -> str:
        """Format bytes into readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                return f"{bytes_val:.2f}{unit}"
            bytes_val /= 1024
        return f"{bytes_val:.2f}PB"
    
    @staticmethod
    def format_number(num: float, precision: int = 2) -> str:
        """Format number with appropriate scale"""
        if abs(num) >= 1e9:
            return f"{num/1e9:.{precision}f}B"
        elif abs(num) >= 1e6:
            return f"{num/1e6:.{precision}f}M"
        elif abs(num) >= 1e3:
            return f"{num/1e3:.{precision}f}K"
        else:
            return f"{num:.{precision}f}"


# ============================================================================
# QUICK API FOR COMMON OPERATIONS
# ============================================================================

class QuickBench:
    """Quick benchmarking API"""
    
    @staticmethod
    def time_function(func: Callable, *args, iterations: int = 100, **kwargs) -> Dict:
        """Quick timing of a function"""
        suite = create_benchmark_suite()
        result = suite.run_benchmark(
            func.__name__,
            func,
            iterations,
            args=args,
            kwargs=kwargs or {}
        )
        return {
            'avg_time': result.avg_time,
            'total_time': result.total_time,
            'min_time': result.min_time,
            'max_time': result.max_time,
            'throughput': result.throughput,
        }
    
    @staticmethod
    def compare_functions(func1: Callable, func2: Callable, 
                         iterations: int = 100) -> Dict:
        """Compare two functions"""
        suite = create_benchmark_suite()
        
        result1 = suite.run_benchmark(
            func1.__name__,
            func1,
            iterations
        )
        
        result2 = suite.run_benchmark(
            func2.__name__,
            func2,
            iterations
        )
        
        comparison = suite.compare_benchmarks(func1.__name__, func2.__name__)
        
        return {
            'func1': func1.__name__,
            'func2': func2.__name__,
            'func1_avg': result1.avg_time,
            'func2_avg': result2.avg_time,
            'speedup': comparison.get('speedup', 0),
            'improvement_percent': comparison.get('improvement_percent', 0),
        }


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize() -> None:
    """Initialize KentScript enhancements"""
    install_enhanced_builtins()
    get_runtime()


# Auto-initialize on import
initialize()
