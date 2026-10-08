"""Unit tests for the pure ETL transformation layer (no database required)."""
from __future__ import annotations

from datetime import date

from etl.transform.common import (
    clean_str,
    full_name,
    parse_date,
    parse_duration_seconds,
    parse_lap_time_ms,
    parse_lap_time_seconds,
    position_gain,
    to_float,
    to_int,
)
from etl.transform.facts import (
    transform_lap,
    transform_pit_stop,
    transform_qualifying,
    transform_result,
)
from etl.transform.quality import EtlStats, clamp_position, dedupe

IDS = {
    "race_id": 10,
    "driver_id": 5,
    "constructor_id": 3,
    "circuit_id": 7,
    "date_id": 20240101,
    "season": 2024,
}


# --------------------------------------------------------------- primitives
def test_clean_str_normalises_and_nulls():
    assert clean_str("  Lewis   Hamilton ") == "Lewis Hamilton"
    assert clean_str("") is None
    assert clean_str("N/A") is None
    assert clean_str("-") is None
    assert clean_str(None) is None
    assert clean_str("abcdef", max_len=3) == "abc"


def test_numeric_parsers():
    assert to_int("42") == 42
    assert to_int("3.9") == 3
    assert to_int("x", default=9) == 9
    assert to_float("3.5") == 3.5
    assert to_float("bad") is None


def test_parse_date_formats():
    assert parse_date("2024-03-02") == date(2024, 3, 2)
    assert parse_date("02/03/2024") == date(2024, 3, 2)
    assert parse_date("not a date") is None


def test_parse_lap_time_ms():
    assert parse_lap_time_ms("1:27.066") == 87_066
    assert parse_lap_time_ms("27.066") == 27_066
    assert parse_lap_time_ms("1:02.5") == 62_500  # pad milliseconds
    assert parse_lap_time_ms("") is None
    assert parse_lap_time_seconds("1:27.066") == 87.066


def test_pit_stop_duration_parsing():
    assert parse_duration_seconds("23.345") == 23.345
    assert parse_duration_seconds("24.0 (2.0)") == 24.0
    assert parse_duration_seconds("") is None


def test_full_name_uses_given_and_family():
    assert full_name("Lewis", "Hamilton") == "Lewis Hamilton"
    assert full_name(None, "Hamilton") == "Hamilton"


def test_position_gain_derivation():
    assert position_gain(5, 2) == 3
    assert position_gain(2, 5) == -3
    assert position_gain(0, 2) is None
    assert position_gain(3, None) is None


# ------------------------------------------------------------- quality tools
def test_dedupe_counts_duplicates():
    stats = EtlStats()
    rows = [{"id": 1}, {"id": 1}, {"id": 2}]
    kept = list(dedupe(rows, key_fn=lambda r: r["id"], stats=stats))
    assert len(kept) == 2
    assert stats.duplicates_removed == 1


def test_clamp_position_rejects_out_of_range():
    stats = EtlStats()
    assert clamp_position(5, stats) == 5
    assert clamp_position(None, stats) is None
    assert clamp_position(999, stats) is None
    assert stats.invalid_values_fixed == 1


# ------------------------------------------------------------ fact transforms
def test_transform_result_derives_position_gain_for_classified_finish():
    raw = {
        "grid": "3",
        "position": "1",
        "positionText": "1",
        "points": "25",
        "laps": "57",
        "status": "Finished",
        "Driver": {"driverId": "verstappen"},
        "Time": {"milliseconds": "5000123"},
        "FastestLap": {"rank": "2", "time": {"time": "1:27.066"}},
    }
    stats = EtlStats()
    row = transform_result(raw, IDS, stats)
    assert row is not None
    assert row["position"] == 1
    assert row["grid"] == 3
    assert row["position_gain"] == 2
    assert row["points"] == 25.0
    assert row["fastest_lap_rank"] == 2
    assert row["fastest_lap_seconds"] == 87.066
    assert row["time_milliseconds"] == 5_000_123


def test_transform_result_retirement_becomes_null_position():
    # Ergast still reports a numeric position for retirements, but the
    # positionText is non-numeric (e.g. "R") -> must become NULL (DNF).
    raw = {
        "grid": "10",
        "position": "18",
        "positionText": "R",
        "points": "0",
        "laps": "12",
        "status": "Accident",
        "Driver": {"driverId": "perez"},
    }
    stats = EtlStats()
    row = transform_result(raw, IDS, stats)
    assert row["position"] is None
    assert row["position_gain"] is None
    assert row["status"] == "Accident"


def test_transform_result_without_driver_is_rejected():
    stats = EtlStats()
    assert transform_result({"grid": "1"}, IDS, stats) is None
    assert stats.errors == 1


def test_transform_qualifying_parses_segments():
    raw = {"position": "2", "Q1": "1:20.100", "Q2": "1:19.500", "Q3": "1:19.000",
           "Driver": {"driverId": "norris"}}
    row = transform_qualifying(raw, IDS, EtlStats())
    assert row["position"] == 2
    assert row["q3_seconds"] == 79.0


def test_transform_lap_rejects_invalid_lap_number():
    stats = EtlStats()
    assert transform_lap({"lap": "0"}, IDS, stats) is None
    assert stats.invalid_values_fixed == 1
    ok = transform_lap({"lap": "5", "position": "3", "time": "1:25.500"}, IDS, stats)
    assert ok["lap"] == 5
    assert ok["lap_milliseconds"] == 85_500


def test_transform_pit_stop_missing_duration_is_counted():
    stats = EtlStats()
    row = transform_pit_stop({"stop": "1", "lap": "20", "duration": ""}, IDS, stats)
    assert row["stop_number"] == 1
    assert row["duration"] is None
    assert stats.missing_values_fixed == 1
