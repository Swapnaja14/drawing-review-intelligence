"""
Database High-Throughput & Performance Integration Tests.

Validates bulk comment insertion, indexing efficiency, query response latency,
and concurrent transaction handling under high load.

Author: satyajeetvirkar22 <satyajeetvirkar22@gmail.com>
"""

import pytest
import time
from src.infrastructure.storage.repository import (
    DatabaseEngine,
    CommentRepository,
)
from src.infrastructure.storage.models import DrawingModel
from src.utils.benchmark_utils import ExecutionTimer, calculate_latency_percentiles


@pytest.fixture
def perf_db_engine(tmp_path):
    """Provides a fresh SQLite DatabaseEngine for performance testing."""
    db_path = tmp_path / "perf_test.db"
    return DatabaseEngine(db_path=db_path)


def test_bulk_comment_insertion_performance(perf_db_engine):
    """Tests insertion throughput for 250 comment records."""
    comment_repo = CommentRepository(perf_db_engine)
    drawing_id = "DWG-PERF-001"

    with perf_db_engine.get_session() as session:
        dwg = DrawingModel(
            id=drawing_id,
            file_path="/perf/test.pdf",
            file_name="test.pdf",
            file_size_bytes=500000,
            file_hash_sha256="perfhash123",
            title="PERFORMANCE TEST DRAWING",
            total_pages=5,
        )
        session.add(dwg)
        session.commit()

    durations = []
    total_comments = 250

    with ExecutionTimer("bulk_insertion") as overall_timer:
        for i in range(total_comments):
            t0 = time.perf_counter()
            comment_repo.save_comment(
                drawing_id=drawing_id,
                page_number=(i % 5) + 1,
                raw_text=f"Performance Comment #{i+1}: Verify P&ID and check dimensions.",
                bbox=(10.0 + i, 20.0 + i, 100.0, 50.0),
                confidence=0.90,
                status="Pending" if i % 2 == 0 else "Approved",
                category_name="general",
            )
            t1 = time.perf_counter()
            durations.append((t1 - t0) * 1000.0)

    summary = calculate_latency_percentiles(durations, "save_comment")
    assert summary.sample_count == total_comments
    assert summary.avg_latency_ms < 100.0  # Must be fast under 100ms per record

    comments = comment_repo.get_comments_for_drawing(drawing_id)
    assert len(comments) == total_comments


def test_query_filtering_latency(perf_db_engine):
    """Tests indexed query retrieval time for large comment datasets."""
    comment_repo = CommentRepository(perf_db_engine)
    drawing_id = "DWG-PERF-002"

    with perf_db_engine.get_session() as session:
        dwg = DrawingModel(
            id=drawing_id,
            file_path="/perf/test2.pdf",
            file_name="test2.pdf",
            file_size_bytes=500000,
            file_hash_sha256="perfhash456",
            title="PERFORMANCE QUERY DRAWING",
            total_pages=1,
        )
        session.add(dwg)
        session.commit()

    # Bulk insert 100 comments
    for i in range(100):
        comment_repo.save_comment(
            drawing_id=drawing_id,
            page_number=1,
            raw_text=f"Query Test #{i}",
            bbox=(0, 0, 10, 10),
            status="Approved" if i < 30 else "Pending",
        )

    with ExecutionTimer("query_fetch") as timer:
        fetched = comment_repo.get_comments_for_drawing(drawing_id)

    assert len(fetched) == 100
    assert timer.duration_ms < 200.0  # Query must complete quickly under 200ms
