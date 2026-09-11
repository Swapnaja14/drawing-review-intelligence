"""
Unit tests for benchmark_utils.py and report_formatter.py

Author: satyajeetvirkar22 <satyajeetvirkar22@gmail.com>
"""

import pytest
import time
from src.utils.benchmark_utils import (
    ExecutionTimer,
    time_function,
    calculate_latency_percentiles,
)
from src.utils.report_formatter import (
    format_markdown_table,
    format_summary_card,
)


def test_execution_timer():
    with ExecutionTimer("test_op") as timer:
        time.sleep(0.01)
        
    assert timer.duration_sec > 0.0
    assert timer.duration_ms > 0.0


def test_time_function_decorator():
    @time_function("sample_func")
    def dummy_task():
        time.sleep(0.01)
        return "done"
        
    res = dummy_task()
    assert res == "done"
    assert dummy_task.last_execution_time_ms > 0.0


def test_calculate_latency_percentiles():
    durations = [10.0, 20.0, 30.0, 40.0, 50.0, 100.0]
    summary = calculate_latency_percentiles(durations, "test_batch")
    
    assert summary.sample_count == 6
    assert summary.min_latency_ms == 10.0
    assert summary.max_latency_ms == 100.0
    assert summary.p50_latency_ms > 0.0
    assert summary.throughput_ops_per_sec > 0.0


def test_format_markdown_table():
    headers = ["ID", "Category", "Status"]
    rows = [
        ["1", "General", "Approved"],
        ["2", "Dimensional", "Pending"],
    ]
    
    table = format_markdown_table(headers, rows)
    assert "Category" in table
    assert "Approved" in table
    assert "Dimensional" in table


def test_format_summary_card():
    metrics = {"total_comments": 15, "approval_rate": "85.5%"}
    card = format_summary_card("Review Summary", metrics)
    
    assert "REVIEW SUMMARY" in card
    assert "Total Comments" in card
    assert "15" in card
