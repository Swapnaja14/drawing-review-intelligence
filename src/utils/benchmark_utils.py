"""
Performance Benchmarking & Metric Instrumentation Utilities.

Provides execution time measurement, memory profiling, latency percentile
calculation, and throughput tracking utilities for high-throughput drawing review operations.

Author: satyajeetvirkar22 <satyajeetvirkar22@gmail.com>
"""

import time
import functools
from typing import Dict, List, Any, Callable, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class MetricSummary:
    """Dataclass holding summary metrics for operation latency."""
    operation_name: str
    sample_count: int
    total_time_sec: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p90_latency_ms: float
    p99_latency_ms: float
    throughput_ops_per_sec: float


class ExecutionTimer:
    """Context manager for measuring code execution duration with high precision."""

    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.duration_sec: float = 0.0
        self.duration_ms: float = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration_sec = self.end_time - self.start_time
        self.duration_ms = round(self.duration_sec * 1000.0, 4)


def time_function(name: Optional[str] = None):
    """Decorator to measure and log function execution time.
    
    Usage:
        @time_function("my_operation")
        def process_data():
            ...
    """
    def decorator(func: Callable):
        op_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with ExecutionTimer(op_name) as timer:
                result = func(*args, **kwargs)
            wrapper.last_execution_time_ms = timer.duration_ms
            return result

        wrapper.last_execution_time_ms = 0.0
        return wrapper
    return decorator


def calculate_latency_percentiles(durations_ms: List[float], op_name: str = "batch") -> MetricSummary:
    """Calculates summary latency statistics and percentiles (p50, p90, p99) from a list of duration samples.
    
    Args:
        durations_ms: List of operation durations in milliseconds.
        op_name: Name of the operation.
        
    Returns:
        MetricSummary dataclass.
    """
    if not durations_ms:
        return MetricSummary(
            operation_name=op_name,
            sample_count=0,
            total_time_sec=0.0,
            avg_latency_ms=0.0,
            min_latency_ms=0.0,
            max_latency_ms=0.0,
            p50_latency_ms=0.0,
            p90_latency_ms=0.0,
            p99_latency_ms=0.0,
            throughput_ops_per_sec=0.0,
        )

    sorted_ms = sorted(durations_ms)
    count = len(sorted_ms)
    total_ms = sum(sorted_ms)
    total_sec = total_ms / 1000.0

    def percentile(p: float) -> float:
        idx = int(round(p * (count - 1)))
        return round(sorted_ms[min(idx, count - 1)], 4)

    avg_ms = round(total_ms / count, 4)
    min_ms = round(sorted_ms[0], 4)
    max_ms = round(sorted_ms[-1], 4)
    p50 = percentile(0.50)
    p90 = percentile(0.90)
    p99 = percentile(0.99)
    throughput = round(count / total_sec, 2) if total_sec > 0 else 0.0

    return MetricSummary(
        operation_name=op_name,
        sample_count=count,
        total_time_sec=round(total_sec, 4),
        avg_latency_ms=avg_ms,
        min_latency_ms=min_ms,
        max_latency_ms=max_ms,
        p50_latency_ms=p50,
        p90_latency_ms=p90,
        p99_latency_ms=p99,
        throughput_ops_per_sec=throughput,
    )
