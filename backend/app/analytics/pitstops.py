"""Pit-stop analytics: durations, counts, correlations."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.analytics.stats import pearson
from app.services.sqlutil import fetch_all, fetch_one


def _filters(season: Optional[int], constructor_id: Optional[int],
             circuit_id: Optional[int]) -> tuple[str, dict]:
    conds, params = ["1=1"], {}
    if season is not None:
        conds.append("p.season = :season")
        params["season"] = season
    if constructor_id is not None:
        conds.append("p.constructor_id = :constructor_id")
        params["constructor_id"] = constructor_id
    if circuit_id is not None:
        conds.append("p.circuit_id = :circuit_id")
        params["circuit_id"] = circuit_id
    return " AND ".join(conds), params


def pit_stop_summary(
    session: Session,
    season: Optional[int] = None,
    constructor_id: Optional[int] = None,
    circuit_id: Optional[int] = None,
) -> dict:
    where, params = _filters(season, constructor_id, circuit_id)

    summary = fetch_one(
        session,
        f"""
        SELECT COUNT(*) AS total_pit_stops,
               COUNT(DISTINCT p.race_id) AS races,
               ROUND(AVG(p.duration), 3) AS avg_duration,
               MIN(p.duration) AS fastest_duration,
               ROUND(AVG(p.lap), 1) AS avg_stop_lap
        FROM fact_pit_stop p
        WHERE {where} AND p.duration IS NOT NULL
        """,
        **params,
    )

    fastest = fetch_all(
        session,
        f"""
        SELECT p.duration, p.lap, p.stop_number,
               d.full_name AS driver, d.code, c.name AS constructor,
               r.season, r.round, r.name AS race_name, r.race_id
        FROM fact_pit_stop p
        JOIN dim_driver d ON d.driver_id = p.driver_id
        JOIN dim_constructor c ON c.constructor_id = p.constructor_id
        JOIN dim_race r ON r.race_id = p.race_id
        WHERE {where} AND p.duration IS NOT NULL
        ORDER BY p.duration ASC
        LIMIT 20
        """,
        **params,
    )

    by_race = fetch_all(
        session,
        f"""
        SELECT r.race_id, r.season, r.round, r.name AS race_name,
               ci.name AS circuit,
               COUNT(*) AS stops,
               ROUND(AVG(p.duration), 3) AS avg_duration,
               MIN(p.duration) AS fastest_duration
        FROM fact_pit_stop p
        JOIN dim_race r ON r.race_id = p.race_id
        JOIN dim_circuit ci ON ci.circuit_id = p.circuit_id
        WHERE {where} AND p.duration IS NOT NULL
        GROUP BY r.race_id, r.season, r.round, r.name, ci.name
        ORDER BY r.season DESC, r.round DESC
        LIMIT 60
        """,
        **params,
    )

    by_constructor = fetch_all(
        session,
        f"""
        SELECT c.constructor_id, c.name,
               COUNT(*) AS stops,
               ROUND(AVG(p.duration), 3) AS avg_duration,
               COUNT(DISTINCT p.race_id) AS races
        FROM fact_pit_stop p
        JOIN dim_constructor c ON c.constructor_id = p.constructor_id
        WHERE {where} AND p.duration IS NOT NULL
        GROUP BY c.constructor_id, c.name
        HAVING COUNT(*) >= 20
        ORDER BY avg_duration ASC
        """,
        **params,
    )

    # duration vs finishing position correlation (per driver-race average)
    pairs = fetch_all(
        session,
        f"""
        SELECT ROUND(AVG(p.duration), 3) AS avg_duration, f.position
        FROM fact_pit_stop p
        JOIN fact_race_result f ON f.race_id = p.race_id AND f.driver_id = p.driver_id
        WHERE {where} AND p.duration IS NOT NULL AND f.position IS NOT NULL
        GROUP BY p.race_id, p.driver_id, f.position
        """,
        **params,
    )
    corr = pearson(
        [p["avg_duration"] for p in pairs], [p["position"] for p in pairs]
    )

    # duration histogram
    hist = fetch_all(
        session,
        f"""
        SELECT FLOOR(p.duration * 2) / 2 AS bucket,
               COUNT(*) AS n
        FROM fact_pit_stop p
        WHERE {where} AND p.duration IS NOT NULL AND p.duration < 90
        GROUP BY FLOOR(p.duration * 2) / 2
        ORDER BY bucket
        """,
        **params,
    )

    return {
        "summary": summary,
        "fastest_stops": fastest,
        "by_race": by_race,
        "by_constructor": by_constructor,
        "duration_histogram": [{"bucket": float(h["bucket"]), "count": h["n"]}
                               for h in hist],
        "correlation_duration_vs_finish": corr,
        "correlation_sample": len(pairs),
    }
