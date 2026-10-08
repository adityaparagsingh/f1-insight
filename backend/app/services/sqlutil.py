"""Thin SQL helpers used by analytics/OLAP services."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


def _normalize(value: Any) -> Any:
    """Convert DB driver types into JSON-friendly Python scalars."""
    if isinstance(value, Decimal):
        # integral decimals -> int, otherwise float
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", "replace")
    return value


def fetch_all(session: Session, sql: str, **params: Any) -> list[dict]:
    """Run a SQL statement returning rows; yield list[dict]."""
    result = session.execute(text(sql), params)
    return [
        {key: _normalize(val) for key, val in row.items()}
        for row in result.mappings().all()
    ]


def fetch_one(session: Session, sql: str, **params: Any) -> Optional[dict]:
    rows = fetch_all(session, sql, **params)
    return rows[0] if rows else None


def scalar(session: Session, sql: str, **params: Any) -> Any:
    return session.execute(text(sql), params).scalar()
