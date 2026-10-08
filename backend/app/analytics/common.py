"""Shared SQL fragments for fact-table analytics (race results centric)."""
from __future__ import annotations

from typing import Optional

# Join path for any fact_race_result query with its dimensions
FACT_RR = """
    FROM fact_race_result f
    JOIN dim_race r        ON r.race_id = f.race_id
    JOIN dim_driver d      ON d.driver_id = f.driver_id
    JOIN dim_constructor c ON c.constructor_id = f.constructor_id
    JOIN dim_circuit ci    ON ci.circuit_id = f.circuit_id
    JOIN dim_date dt       ON dt.date_id = f.date_id
"""

# A "finish" = the driver was classified (position not null)
FINISHED = "f.position IS NOT NULL"
CLASSIFIED_DNF = "f.position IS NULL"

WINNER = "f.position = 1"
PODIUM = "f.position <= 3"


def build_fact_filter(
    season: Optional[int] = None,
    driver_id: Optional[int] = None,
    constructor_id: Optional[int] = None,
    circuit_id: Optional[int] = None,
) -> tuple[str, dict]:
    """Return a WHERE clause fragment (' WHERE ...' or '') + bound params."""
    conds: list[str] = []
    params: dict = {}
    if season is not None:
        conds.append("f.season = :season")
        params["season"] = season
    if driver_id is not None:
        conds.append("f.driver_id = :driver_id")
        params["driver_id"] = driver_id
    if constructor_id is not None:
        conds.append("f.constructor_id = :constructor_id")
        params["constructor_id"] = constructor_id
    if circuit_id is not None:
        conds.append("f.circuit_id = :circuit_id")
        params["circuit_id"] = circuit_id
    where = (" WHERE " + " AND ".join(conds)) if conds else ""
    return where, params


# Canonical measures SQL reused across driver/constructor/circuit summaries
MEASURES = """
    COUNT(*)                                        AS races,
    SUM(f.position = 1)                             AS wins,
    SUM(f.position <= 3)                            AS podiums,
    SUM(f.points)                                   AS points,
    AVG(CASE WHEN f.position IS NOT NULL THEN f.position END) AS avg_finish,
    AVG(NULLIF(f.grid, 0))                          AS avg_grid,
    SUM(f.position IS NULL)                         AS dnfs,
    SUM(f.fastest_lap_rank = 1)                     AS fastest_laps,
    AVG(f.position_gain)                            AS avg_position_gain,
    SUM(f.position_gain)                            AS total_position_gain,
    AVG(f.pit_stop_count)                           AS avg_pit_stops
"""
