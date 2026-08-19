"""
scripts/verify_db.py
--------------------
Database initialisation and structural verification script.

Checks (without inserting any data):
    1. The data/ directory is created automatically.
    2. The SQLite database file is created at data/ucc_database.db.
    3. SQLAlchemy can open a connection.
    4. All six expected tables exist in the schema.
    5. Each table can be queried (SELECT COUNT(*) returns 0 on a fresh DB).

Run from the project root:
    python scripts/verify_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path so src.* imports resolve.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import inspect, text                          # noqa: E402
from src.infrastructure.storage.repository import (          # noqa: E402
    DatabaseEngine,
    _DEFAULT_DB_PATH,
)
from src.infrastructure.storage.models import (              # noqa: E402
    ProjectModel,
    DrawingModel,
    PageModel,
    CommentModel,
    CategoryModel,
    UserModel,
)

EXPECTED_TABLES = [
    "projects",
    "drawings",
    "pages",
    "comments",
    "categories",
    "users",
]


def _header(msg: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {msg}")
    print(f"{'─' * 60}")


def _ok(msg: str) -> None:
    print(f"  ✓  {msg}")


def _fail(msg: str) -> None:
    print(f"  ✗  {msg}")


def run_verification() -> bool:
    all_passed = True

    _header("UCC Analyzer — Database Verification")

    # ------------------------------------------------------------------
    # 1. Initialise engine (creates data/ dir and tables if absent)
    # ------------------------------------------------------------------
    print(f"\n  DB path : {_DEFAULT_DB_PATH}")
    try:
        db = DatabaseEngine()
        _ok("DatabaseEngine initialised without errors.")
    except Exception as exc:
        _fail(f"DatabaseEngine failed: {exc}")
        return False

    # ------------------------------------------------------------------
    # 2. data/ directory exists
    # ------------------------------------------------------------------
    if _DEFAULT_DB_PATH.parent.is_dir():
        _ok(f"data/ directory exists at: {_DEFAULT_DB_PATH.parent}")
    else:
        _fail("data/ directory was NOT created.")
        all_passed = False

    # ------------------------------------------------------------------
    # 3. SQLite file created
    # ------------------------------------------------------------------
    if _DEFAULT_DB_PATH.is_file():
        size_kb = round(_DEFAULT_DB_PATH.stat().st_size / 1024, 1)
        _ok(f"Database file exists ({size_kb} KB).")
    else:
        _fail("Database file was NOT created.")
        all_passed = False

    # ------------------------------------------------------------------
    # 4. Connection test
    # ------------------------------------------------------------------
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT sqlite_version()")).scalar()
        _ok(f"SQLAlchemy connection successful (SQLite {result}).")
    except Exception as exc:
        _fail(f"Connection failed: {exc}")
        all_passed = False

    # ------------------------------------------------------------------
    # 5. Table presence check
    # ------------------------------------------------------------------
    _header("Table Schema Verification")
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())

    for table_name in EXPECTED_TABLES:
        if table_name in existing_tables:
            _ok(f"Table '{table_name}' exists.")
        else:
            _fail(f"Table '{table_name}' is MISSING.")
            all_passed = False

    # ------------------------------------------------------------------
    # 6. Query each table (must return 0 rows on a fresh database)
    # ------------------------------------------------------------------
    _header("Table Queryability Check (no data inserted)")

    model_map = {
        "projects":   ProjectModel,
        "drawings":   DrawingModel,
        "pages":      PageModel,
        "comments":   CommentModel,
        "categories": CategoryModel,
        "users":      UserModel,
    }

    with db.get_session() as session:
        for table_name, model in model_map.items():
            try:
                count = session.query(model).count()
                _ok(f"SELECT COUNT(*) FROM {table_name} → {count} row(s).")
            except Exception as exc:
                _fail(f"Query failed on '{table_name}': {exc}")
                all_passed = False

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    _header("Result")
    if all_passed:
        print("\n  ALL CHECKS PASSED — database layer is ready.\n")
    else:
        print("\n  ONE OR MORE CHECKS FAILED — review output above.\n")

    return all_passed


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
