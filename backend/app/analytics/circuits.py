"""Circuit analytics: list, profile, records, pit statistics."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.analytics.common import FACT_RR
from app.services.sqlutil import fetch_all, fetch_one


def circuit_list(
    session: Session,
    search: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    conds, params = ["1=1"], {}
    if search:
        conds.append("(ci.name LIKE :q OR ci.location LIKE :q)")
        params["q"] = f"%{search}%"
    if country:
        conds.append("ci.country = :country")
        params["country"] = country
    where = " AND ".join(conds)
    base = f"""
        SELECT ci.circuit_id, ci.circuit_ref, ci.name, ci.location, ci.country,
               ci.latitude, ci.longitude,
               COUNT(DISTINCT r.race_id) AS races,
               MIN(r.date) AS first_race, MAX(r.date) AS last_race
        FROM dim_circuit ci
        LEFT JOIN dim_race r ON r.circuit_id = ci.circuit_id
        WHERE {where}
        GROUP BY ci.circuit_id, ci.circuit_ref, ci.name, ci.location, ci.country,
                 ci.latitude, ci.longitude
    """
    params["limit"] = int(limit)
    params["offset"] = int(offset)
    total_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = fetch_all(session, f"SELECT COUNT(*) AS n FROM ({base}) t", **total_params)[0]["n"]
    rows = fetch_all(
        session,
        f"SELECT * FROM ({base}) t ORDER BY races DESC, name ASC LIMIT :limit OFFSET :offset",
        **params,
    )
    return {"total": total, "limit": limit, "offset": offset, "items": rows}


def circuit_profile(session: Session, circuit_id: int) -> Optional[dict]:
    profile = fetch_one(
        session,
        """
        SELECT circuit_id, circuit_ref, name, location, country,
               latitude, longitude, altitude, url
        FROM dim_circuit WHERE circuit_id = :id
        """,
        id=circuit_id,
    )
    if profile is None:
        return None

    summary = fetch_one(
        session,
        f"""
        SELECT COUNT(*) AS race_results,
               COUNT(DISTINCT f.race_id) AS races,
               SUM(f.position IS NULL) AS dnfs,
               ROUND(SUM(f.position IS NULL) / COUNT(*), 3) AS dnf_rate,
               SUM(f.grid = 1) AS poles,
               ROUND(AVG(f.position_gain), 2) AS avg_position_gain,
               ROUND(AVG(f.pit_stop_count), 2) AS avg_pit_stops_per_driver
        {FACT_RR}
        WHERE f.circuit_id = :id
        """,
        id=circuit_id,
    )

    top_drivers = fetch_all(
        session,
        f"""
        SELECT d.driver_id, d.full_name AS name, d.code,
               COUNT(*) AS entries,
               SUM(f.position = 1) AS wins,
               SUM(f.position <= 3) AS podiums,
               ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
               ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish
        {FACT_RR}
        WHERE f.circuit_id = :id
        GROUP BY d.driver_id, d.full_name, d.code
        ORDER BY wins DESC, points DESC LIMIT 10
        """,
        id=circuit_id,
    )

    top_constructors = fetch_all(
        session,
        f"""
        SELECT c.constructor_id, c.name,
               COUNT(*) AS entries,
               SUM(f.position = 1) AS wins,
               SUM(f.position <= 3) AS podiums,
               ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
               ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish
        {FACT_RR}
        WHERE f.circuit_id = :id
        GROUP BY c.constructor_id, c.name
        ORDER BY wins DESC, points DESC LIMIT 10
        """,
        id=circuit_id,
    )

    lap_record = fetch_one(
        session,
        """
        SELECT l.lap_milliseconds, l.lap_time, l.season, d.full_name AS driver,
               c.name AS constructor, r.name AS race_name, r.date
        FROM fact_lap l
        JOIN dim_driver d ON d.driver_id = l.driver_id
        JOIN dim_constructor c ON c.constructor_id = l.constructor_id
        JOIN dim_race r ON r.race_id = l.race_id
        WHERE l.circuit_id = :id AND l.lap_milliseconds IS NOT NULL
        ORDER BY l.lap_milliseconds ASC LIMIT 1
        """,
        id=circuit_id,
    )

    lap_stats = fetch_one(
        session,
        """
        SELECT COUNT(*) AS lap_records,
               ROUND(AVG(lap_milliseconds), 0) AS avg_lap_ms,
               MIN(lap_milliseconds) AS fastest_lap_ms
        FROM fact_lap WHERE circuit_id = :id AND lap_milliseconds IS NOT NULL
        """,
        id=circuit_id,
    )

    pit_stats = fetch_one(
        session,
        """
        SELECT COUNT(*) AS pit_stops,
               ROUND(AVG(duration), 3) AS avg_duration,
               MIN(duration) AS fastest_duration
        FROM fact_pit_stop WHERE circuit_id = :id
        """,
        id=circuit_id,
    )

    winners = fetch_all(
        session,
        """
        SELECT r.race_id, r.season, r.round, r.name, r.date,
               d.full_name AS winner, d.code AS winner_code,
               c.name AS constructor
        FROM fact_race_result f
        JOIN dim_race r ON r.race_id = f.race_id
        JOIN dim_driver d ON d.driver_id = f.driver_id
        JOIN dim_constructor c ON c.constructor_id = f.constructor_id
        WHERE f.circuit_id = :id AND f.position = 1
        ORDER BY r.date DESC
        """,
        id=circuit_id,
    )

    fastest_pit_stops = fetch_all(
        session,
        """
        SELECT p.duration, d.full_name AS driver, c.name AS constructor,
               p.lap, r.season, r.name AS race_name
        FROM fact_pit_stop p
        JOIN dim_driver d ON d.driver_id = p.driver_id
        JOIN dim_constructor c ON c.constructor_id = p.constructor_id
        JOIN dim_race r ON r.race_id = p.race_id
        WHERE p.circuit_id = :id AND p.duration IS NOT NULL
        ORDER BY p.duration ASC LIMIT 5
        """,
        id=circuit_id,
    )

    return {
        "profile": profile,
        "summary": summary,
        "top_drivers": top_drivers,
        "top_constructors": top_constructors,
        "lap_record": lap_record,
        "lap_stats": lap_stats,
        "pit_stats": pit_stats,
        "winners": winners,
        "fastest_pit_stops": fastest_pit_stops,
    }
