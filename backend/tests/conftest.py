"""Shared pytest fixtures for the F1 INSIGHT backend test suite.

The tests run against the *real* local warehouse when it is reachable and are
skipped automatically otherwise, so the pure-unit tests still pass in a fresh
checkout with no database.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `app` and `etl` importable when pytest is invoked from backend/.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def db_ready() -> None:
    """Skip DB-dependent tests when MySQL is not reachable."""
    from sqlalchemy import text

    from app.db import SessionLocal

    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"warehouse database unavailable: {type(exc).__name__}")
    finally:
        session.close()


@pytest.fixture(scope="session")
def client(db_ready):
    """FastAPI TestClient wired to the real app + database."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db(db_ready):
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
