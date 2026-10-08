"""Row-level fact transformations: raw API dict -> warehouse row dict.

Pure functions: surrogate keys are resolved by the calling pipeline and
passed in via ``ids``.  All derived metrics and normalisations happen here.
"""
from __future__ import annotations

from typing import Any, Optional

from etl.transform.common import (
    clean_str,
    parse_duration_seconds,
    parse_lap_time_ms,
    parse_lap_time_seconds,
    position_gain,
    to_float,
    to_int,
)
from etl.transform.quality import EtlStats, clamp_position


def _race_time_ms(value: Any) -> Optional[int]:
    """Race winning time: '1:20:53.423' / '66:11.620' -> milliseconds."""
    s = clean_str(value)
    if not s:
        return None
    parts = s.split(":")
    try:
        if len(parts) == 3:
            h, m, sec = parts
            return int(h) * 3_600_000 + int(m) * 60_000 + int(round(float(sec) * 1000))
        if len(parts) == 2:
            m, sec = parts
            return int(m) * 60_000 + int(round(float(sec) * 1000))
        return int(round(float(s) * 1000))
    except ValueError:
        return None


def transform_result(raw: dict, ids: dict, stats: EtlStats) -> Optional[dict]:
    """fact_race_result row from an API Result object."""
    driver_raw = raw.get("Driver") or {}
    if not driver_raw.get("driverId"):
        stats.issue("result without driverId")
        return None

    grid = clamp_position(to_int(raw.get("grid"), 0), stats, "grid")
    position_text = clean_str(raw.get("positionText"), 4)
    position = clamp_position(to_int(raw.get("position")), stats, "position")
    grid = grid or 0

    # Ergast populates `position` even for retirements; only a *numeric*
    # positionText means the driver was officially classified.  Retirements
    # (R/D/E/W/F/N) become NULL so DNF rates, average finish and position gain
    # are computed from classified results only.
    if position_text and not position_text.isdigit():
        position = None

    fastest_lap = raw.get("FastestLap") or {}
    fl_time_raw = fastest_lap.get("time")
    if isinstance(fl_time_raw, dict):
        fl_time_str = clean_str(fl_time_raw.get("time"))
        fl_ms = to_int(fl_time_raw.get("milliseconds"))
    else:
        fl_time_str = clean_str(fl_time_raw)
        fl_ms = parse_lap_time_ms(fl_time_str)
    speed_raw = fastest_lap.get("AverageSpeed") or {}
    fl_speed = to_float(speed_raw.get("speed"))

    time_raw = raw.get("Time")
    if isinstance(time_raw, dict):
        time_ms = to_int(time_raw.get("milliseconds"))
    else:
        time_ms = _race_time_ms(time_raw)

    if position_text and not position_text.isdigit():
        status = clean_str(raw.get("status")) or "Retired"
    else:
        status = clean_str(raw.get("status")) or "Unknown"

    points = to_float(raw.get("points"), 0.0) or 0.0
    laps = to_int(raw.get("laps"), 0) or 0

    if fl_ms:
        fl_seconds = round(fl_ms / 1000.0, 3)
    elif fl_time_str:
        fl_seconds = parse_lap_time_seconds(fl_time_str)
    else:
        fl_seconds = None

    return {
        "race_id": ids["race_id"],
        "driver_id": ids["driver_id"],
        "constructor_id": ids["constructor_id"],
        "circuit_id": ids["circuit_id"],
        "date_id": ids["date_id"],
        "season": ids["season"],
        "grid": grid,
        "position": position,
        "position_text": clean_str(raw.get("positionText"), 4),
        "points": round(points, 2),
        "laps": laps,
        "time_milliseconds": time_ms,
        "fastest_lap_rank": to_int(fastest_lap.get("rank")),
        "fastest_lap_time": fl_time_str,
        "fastest_lap_seconds": fl_seconds,
        "fastest_lap_speed": round(fl_speed, 3) if fl_speed else None,
        "pit_stop_count": 0,  # refreshed after the pit-stop stage
        "status": status,
        "position_gain": position_gain(grid, position),
    }


def transform_qualifying(raw: dict, ids: dict, stats: EtlStats) -> Optional[dict]:
    """fact_qualifying row from an API QualifyingResult object."""
    driver_raw = raw.get("Driver") or {}
    if not driver_raw.get("driverId"):
        stats.issue("qualifying row without driverId")
        return None
    position = clamp_position(to_int(raw.get("position")), stats, "position")
    if position is None:
        stats.issue("qualifying row with invalid position")
        return None
    return {
        "race_id": ids["race_id"],
        "driver_id": ids["driver_id"],
        "constructor_id": ids["constructor_id"],
        "circuit_id": ids["circuit_id"],
        "date_id": ids["date_id"],
        "season": ids["season"],
        "position": position,
        "q1": clean_str(raw.get("Q1"), 16),
        "q2": clean_str(raw.get("Q2"), 16),
        "q3": clean_str(raw.get("Q3"), 16),
        "q1_seconds": parse_lap_time_seconds(raw.get("Q1")),
        "q2_seconds": parse_lap_time_seconds(raw.get("Q2")),
        "q3_seconds": parse_lap_time_seconds(raw.get("Q3")),
    }


def transform_lap(raw: dict, ids: dict, stats: EtlStats) -> Optional[dict]:
    """fact_lap row from a flattened API lap timing."""
    lap = to_int(raw.get("lap"))
    if lap is None or lap < 1:
        stats.invalid_values_fixed += 1
        return None
    return {
        "race_id": ids["race_id"],
        "driver_id": ids["driver_id"],
        "constructor_id": ids["constructor_id"],
        "circuit_id": ids["circuit_id"],
        "date_id": ids["date_id"],
        "season": ids["season"],
        "lap": lap,
        "position": clamp_position(to_int(raw.get("position")), stats, "lap position"),
        "lap_time": clean_str(raw.get("time"), 16),
        "lap_milliseconds": parse_lap_time_ms(raw.get("time")),
    }


def transform_pit_stop(raw: dict, ids: dict, stats: EtlStats) -> Optional[dict]:
    """fact_pit_stop row from an API PitStop object."""
    stop_no = to_int(raw.get("stop"))
    lap = to_int(raw.get("lap"))
    if stop_no is None or lap is None:
        stats.issue(f"pit stop with invalid stop/lap: {raw.get('stop')}/{raw.get('lap')}")
        return None
    duration = parse_duration_seconds(raw.get("duration"))
    if duration is None:
        stats.missing_values_fixed += 1
        stats.note(f"pit stop duration missing (driver={raw.get('driverId')}, lap={lap})")
    return {
        "race_id": ids["race_id"],
        "driver_id": ids["driver_id"],
        "constructor_id": ids["constructor_id"],
        "circuit_id": ids["circuit_id"],
        "date_id": ids["date_id"],
        "season": ids["season"],
        "stop_number": stop_no,
        "lap": lap,
        "duration": round(duration, 3) if duration is not None else None,
        "duration_ms": int(round(duration * 1000)) if duration is not None else None,
    }


def transform_driver_standing(raw: dict, ids: dict, stats: EtlStats) -> Optional[dict]:
    """fact_driver_standing row from an API DriverStanding object."""
    position = clamp_position(to_int(raw.get("position")), stats, "standing position")
    if position is None:
        stats.issue("driver standing with invalid position")
        return None
    constructors = raw.get("Constructors") or []
    return {
        "race_id": ids.get("race_id"),
        "season": ids["season"],
        "round": ids.get("round", 0),
        "driver_id": ids["driver_id"],
        "constructor_id": ids.get("constructor_id") if constructors else None,
        "points": round(to_float(raw.get("points"), 0.0) or 0.0, 2),
        "position": position,
        "wins": to_int(raw.get("wins"), 0) or 0,
    }


def transform_constructor_standing(raw: dict, ids: dict, stats: EtlStats) -> Optional[dict]:
    position = clamp_position(to_int(raw.get("position")), stats, "standing position")
    if position is None:
        stats.issue("constructor standing with invalid position")
        return None
    return {
        "race_id": ids.get("race_id"),
        "season": ids["season"],
        "round": ids.get("round", 0),
        "constructor_id": ids["constructor_id"],
        "points": round(to_float(raw.get("points"), 0.0) or 0.0, 2),
        "position": position,
        "wins": to_int(raw.get("wins"), 0) or 0,
    }
