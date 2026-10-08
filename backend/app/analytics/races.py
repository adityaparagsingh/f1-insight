"""Race analytics: race list, race detail (timing screen), position changes."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.analytics.common import FACT_RR
from app.services.sqlutil import fetch_all, fetch_one


def race_list(
    session: Session,
    season: Optional[int] = None,
    circuit_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 30,
    offset: int = 0,
) -> dict:
    conds, params = ["1=1"], {}
    if season is not None:
        conds.append("r.season = :season")
        params["season"] = season
    if circuit_id is not None:
        conds.append("r.circuit_id = :circuit_id")
        params["circuit_id"] = circuit_id
    if search:
        conds.append("(r.name LIKE :q OR ci.name LIKE :q)")
        params["q"] = f"%{search}%"
    where = " AND ".join(conds)
    base = f"""
        SELECT r.race_id, r.season, r.round, r.name, r.date,
               ci.circuit_id, ci.name AS circuit, ci.country,
               wd.full_name AS winner, wd.code AS winner_code,
               wc.name AS winning_constructor,
               (SELECT COUNT(*) FROM fact_race_result f WHERE f.race_id = r.race_id) AS entries
        FROM dim_race r
        JOIN dim_circuit ci ON ci.circuit_id = r.circuit_id
        LEFT JOIN fact_race_result fw ON fw.race_id = r.race_id AND fw.position = 1
        LEFT JOIN dim_driver wd ON wd.driver_id = fw.driver_id
        LEFT JOIN dim_constructor wc ON wc.constructor_id = fw.constructor_id
        WHERE {where}
    """
    params["limit"] = int(limit)
    params["offset"] = int(offset)
    total_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = fetch_all(session, f"SELECT COUNT(*) AS n FROM ({base}) t", **total_params)[0]["n"]
    rows = fetch_all(
        session,
        f"SELECT * FROM ({base}) t ORDER BY t.date DESC, t.round DESC "
        f"LIMIT :limit OFFSET :offset",
        **params,
    )
    return {"total": total, "limit": limit, "offset": offset, "items": rows}


def race_detail(session: Session, race_id: int) -> Optional[dict]:
    race = fetch_one(
        session,
        """
        SELECT r.race_id, r.season, r.round, r.name, r.date, r.url,
               ci.circuit_id, ci.name AS circuit, ci.location, ci.country
        FROM dim_race r
        JOIN dim_circuit ci ON ci.circuit_id = r.circuit_id
        WHERE r.race_id = :id
        """,
        id=race_id,
    )
    if race is None:
        return None

    results = fetch_all(
        session,
        """
        SELECT f.result_id, f.grid, f.position, f.position_text, f.points, f.laps,
               f.time_milliseconds, f.fastest_lap_rank, f.fastest_lap_time,
               f.fastest_lap_speed, f.pit_stop_count, f.status, f.position_gain,
               d.driver_id, d.full_name AS driver, d.code, d.number AS driver_number,
               c.constructor_id, c.name AS constructor
        FROM fact_race_result f
        JOIN dim_driver d ON d.driver_id = f.driver_id
        JOIN dim_constructor c ON c.constructor_id = f.constructor_id
        WHERE f.race_id = :id
        ORDER BY COALESCE(f.position, 999), f.grid
        """,
        id=race_id,
    )

    qualifying = fetch_all(
        session,
        """
        SELECT q.position, q.q1, q.q2, q.q3,
               d.driver_id, d.full_name AS driver, d.code,
               c.name AS constructor
        FROM fact_qualifying q
        JOIN dim_driver d ON d.driver_id = q.driver_id
        JOIN dim_constructor c ON c.constructor_id = q.constructor_id
        WHERE q.race_id = :id
        ORDER BY q.position
        """,
        id=race_id,
    )

    pit_stops = fetch_all(
        session,
        """
        SELECT p.stop_number, p.lap, p.duration, p.duration_ms,
               d.full_name AS driver, d.code, c.name AS constructor
        FROM fact_pit_stop p
        JOIN dim_driver d ON d.driver_id = p.driver_id
        JOIN dim_constructor c ON c.constructor_id = p.constructor_id
        WHERE p.race_id = :id
        ORDER BY p.duration ASC
        """,
        id=race_id,
    )

    # fastest laps of the race
    fastest_laps = fetch_all(
        session,
        """
        SELECT f.fastest_lap_rank, f.fastest_lap_time, f.fastest_lap_seconds,
               f.fastest_lap_speed, d.full_name AS driver, d.code, c.name AS constructor
        FROM fact_race_result f
        JOIN dim_driver d ON d.driver_id = f.driver_id
        JOIN dim_constructor c ON c.constructor_id = f.constructor_id
        WHERE f.race_id = :id AND f.fastest_lap_seconds IS NOT NULL
        ORDER BY f.fastest_lap_seconds ASC
        """,
        id=race_id,
    )

    summary = fetch_one(
        session,
        """
        SELECT COUNT(*) AS entries,
               SUM(f.position IS NULL) AS dnfs,
               ROUND(AVG(f.pit_stop_count), 2) AS avg_pit_stops,
               SUM(f.grid > f.position) AS position_gainers,
               SUM(f.grid < f.position) AS position_losers,
               MAX(f.position_gain) AS biggest_gain,
               MIN(f.fastest_lap_seconds) AS fastest_lap_seconds
        FROM fact_race_result f
        WHERE f.race_id = :id
        """,
        id=race_id,
    )

    return {
        "race": race,
        "results": results,
        "qualifying": qualifying,
        "pit_stops": pit_stops,
        "fastest_laps": fastest_laps,
        "summary": summary,
    }


def position_changes(session: Session, season: Optional[int] = None, limit: int = 20) -> dict:
    where, params = build_where(season)
    params = {**params, "limit": int(limit)}
    biggest_gains = fetch_all(
        session,
        f"""
        SELECT f.position_gain, r.season, r.round, r.name AS race_name,
               d.full_name AS driver, d.code, c.name AS constructor,
               f.grid, f.position
        {FACT_RR}
        {where} AND f.position_gain IS NOT NULL
        ORDER BY f.position_gain DESC, r.date DESC
        LIMIT :limit
        """,
        **params,
    )
    biggest_losses = fetch_all(
        session,
        f"""
        SELECT f.position_gain, r.season, r.round, r.name AS race_name,
               d.full_name AS driver, d.code, c.name AS constructor,
               f.grid, f.position
        {FACT_RR}
        {where} AND f.position_gain IS NOT NULL
        ORDER BY f.position_gain ASC, r.date DESC
        LIMIT :limit
        """,
        **params,
    )
    return {"biggest_gains": biggest_gains, "biggest_losses": biggest_losses}


def build_where(season: Optional[int]) -> tuple[str, dict]:
    if season is not None:
        return " WHERE f.season = :season", {"season": season}
    return "", {}
