"""Shared transformation helpers: parsing, normalisation, derived metrics."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

_NULL_TOKENS = {"", "\\n", "\\N", "null", "None", "N/A", "n/a", "-"}

_TIME_RE = re.compile(r"^(\d+):(\d{2})\.(\d{1,3})$")


def clean_str(value: Any, max_len: Optional[int] = None) -> Optional[str]:
    """Trim/collapse whitespace; map null-ish tokens to None."""
    if value is None:
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    if s.lower() in _NULL_TOKENS or s == "\\N":
        return None
    if max_len is not None:
        s = s[:max_len]
    return s or None


def to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    s = clean_str(value)
    if s is None:
        return default
    try:
        return int(float(s))
    except ValueError:
        return default


def to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    s = clean_str(value)
    if s is None:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def parse_date(value: Any) -> Optional[date]:
    s = clean_str(value)
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_lap_time_ms(value: Any) -> Optional[int]:
    """'1:27.066' -> 87066 ms.  Plain seconds ('27.066') -> 27066 ms."""
    s = clean_str(value)
    if not s:
        return None
    m = _TIME_RE.match(s)
    if m:
        minutes, seconds, millis = m.groups()
        millis = millis.ljust(3, "0")
        return int(minutes) * 60_000 + int(seconds) * 1000 + int(millis)
    try:
        return int(round(float(s) * 1000))
    except ValueError:
        return None


def parse_lap_time_seconds(value: Any) -> Optional[float]:
    ms = parse_lap_time_ms(value)
    return round(ms / 1000.0, 3) if ms is not None else None


def parse_duration_seconds(value: Any) -> Optional[float]:
    """Pit-stop duration: '23.345' -> 23.345. Handles '(2.345)' style extras."""
    s = clean_str(value)
    if not s:
        return None
    s = s.split("(")[0].strip()
    try:
        return round(float(s), 3)
    except ValueError:
        secs = parse_lap_time_seconds(s)
        return secs


def normalize_person_name(value: Any) -> str:
    return clean_str(value) or ""


def full_name(forename: Any, surname: Any) -> str:
    return f"{normalize_person_name(forename)} {normalize_person_name(surname)}".strip()


def position_gain(grid: Optional[int], position: Optional[int]) -> Optional[int]:
    """DERIVED METRIC: grid - finish position (only when both are meaningful)."""
    if grid is None or position is None:
        return None
    if grid <= 0 or position <= 0:
        return None
    return grid - position


def normalize_natural_key(*parts: Any) -> str:
    return "|".join(clean_str(p) or "" for p in parts)
