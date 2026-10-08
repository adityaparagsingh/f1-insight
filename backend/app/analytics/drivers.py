"""Driver analytics: list, profile, season series, qualifying-vs-finish."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.analytics.common import FACT_RR
from app.services.sqlutil import fetch_all, fetch_one


def driver_list(
    session: Session,
    season: Optional[int] = None,
    constructor_id: Optional[int] = None,
    search: Optional[str] = None,
    sort: str = "points",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    conds, params = ["1=1"], {}
    if season is not None:
        conds.append("f.season = :season")
        params["season"] = season
    if constructor_id is not None:
        conds.append("f.constructor_id = :constructor_id")
        params["constructor_id"] = constructor_id
    if search:
        conds.append("(d.full_name LIKE :q OR d.code LIKE :q OR d.driver_ref LIKE :q)")
        params["q"] = f"%{search}%"
    where = " AND ".join(conds)

    sort_map = {
        "points": "points", "wins": "wins", "podiums": "podiums",
        "races": "races", "avg_finish": "avg_finish", "avg_grid": "avg_grid",
        "dnf_rate": "dnf_rate", "position_gain": "avg_position_gain",
        "name": "name",
    }
    sort_col = sort_map.get(sort, "points")
    sort_dir = "ASC" if order.lower() == "asc" else "DESC"
    if sort_col in ("avg_finish", "avg_grid", "dnf_rate") and sort_dir == "DESC":
        pass  # caller chooses direction explicitly

    base = f"""
        SELECT d.driver_id, d.driver_ref, d.code, d.full_name AS name,
               d.number, d.nationality,
               COUNT(*) AS races,
               SUM(f.position = 1) AS wins,
               SUM(f.position <= 3) AS podiums,
               ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
               ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish,
               ROUND(AVG(NULLIF(f.grid, 0)), 2) AS avg_grid,
               SUM(f.position IS NULL) AS dnfs,
               ROUND(SUM(f.position IS NULL) / COUNT(*), 3) AS dnf_rate,
               ROUND(SUM(f.position = 1) / COUNT(*), 3) AS win_rate,
               ROUND(SUM(f.position <= 3) / COUNT(*), 3) AS podium_rate,
               SUM(f.fastest_lap_rank = 1) AS fastest_laps,
               ROUND(AVG(f.position_gain), 2) AS avg_position_gain,
               GROUP_CONCAT(DISTINCT c.name ORDER BY c.name SEPARATOR ', ') AS teams
        {FACT_RR}
        WHERE {where}
        GROUP BY d.driver_id, d.driver_ref, d.code, d.full_name, d.number, d.nationality
    """
    params["limit"] = int(limit)
    params["offset"] = int(offset)
    total_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = fetch_all(
        session,
        f"SELECT COUNT(*) AS n FROM ({base}) t",
        **total_params,
    )[0]["n"]
    rows = fetch_all(
        session,
        f"SELECT * FROM ({base}) t ORDER BY {sort_col} {sort_dir}, name ASC LIMIT :limit OFFSET :offset",
        **params,
    )
    return {"total": total, "limit": limit, "offset": offset, "items": rows}


def driver_profile(session: Session, driver_id: int) -> Optional[dict]:
    profile = fetch_one(
        session,
        """
        SELECT driver_id, driver_ref, code, forename, surname, full_name AS name,
               number, date_of_birth, nationality, url
        FROM dim_driver WHERE driver_id = :id
        """,
        id=driver_id,
    )
    if profile is None:
        return None

    career = fetch_one(
        session,
        f"""
        SELECT COUNT(*) AS races,
               MIN(f.season) AS first_season, MAX(f.season) AS last_season,
               SUM(f.position = 1) AS wins,
               SUM(f.position <= 3) AS podiums,
               ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
               ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish,
               ROUND(AVG(NULLIF(f.grid, 0)), 2) AS avg_grid,
               SUM(f.position IS NULL) AS dnfs,
               ROUND(SUM(f.position IS NULL) / COUNT(*), 3) AS dnf_rate,
               ROUND(SUM(f.position = 1) / COUNT(*), 3) AS win_rate,
               ROUND(SUM(f.position <= 3) / COUNT(*), 3) AS podium_rate,
               SUM(f.fastest_lap_rank = 1) AS fastest_laps,
               SUM(f.grid = 1) AS poles,
               ROUND(AVG(f.position_gain), 2) AS avg_position_gain,
               SUM(f.position_gain) AS total_position_gain,
               MAX(f.position_gain) AS best_gain
        {FACT_RR}
        WHERE f.driver_id = :id
        """,
        id=driver_id,
    )

    seasons = fetch_all(
        session,
        f"""
        SELECT f.season,
               COUNT(*) AS races,
               SUM(f.position = 1) AS wins,
               SUM(f.position <= 3) AS podiums,
               ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
               ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish,
               ROUND(AVG(NULLIF(f.grid, 0)), 2) AS avg_grid,
               SUM(f.position IS NULL) AS dnfs,
               ROUND(AVG(f.position_gain), 2) AS avg_position_gain,
               GROUP_CONCAT(DISTINCT c.name ORDER BY c.name SEPARATOR ' / ') AS teams
        {FACT_RR}
        WHERE f.driver_id = :id
        GROUP BY f.season ORDER BY f.season
        """,
        id=driver_id,
    )

    # championship positions (from standings snapshots at final round)
    champ = {
        r["season"]: r["championship_position"]
        for r in fetch_all(
            session,
            """
            SELECT ds.season, ds.position AS championship_position
            FROM fact_driver_standing ds
            JOIN (SELECT season, MAX(round) AS mr FROM fact_driver_standing
                  WHERE driver_id = :id GROUP BY season) m
              ON m.season = ds.season
            WHERE ds.driver_id = :id AND ds.round = m.mr
            """,
            id=driver_id,
        )
    }
    for row in seasons:
        row["championship_position"] = champ.get(row["season"])

    # per-race qualifying vs finish (chart data)
    quali_vs_finish = fetch_all(
        session,
        """
        SELECT r.season, r.round, r.name AS race_name, q.position AS quali_pos,
               f.position AS finish_pos, f.grid, f.position_gain, f.points, f.status
        FROM fact_qualifying q
        JOIN fact_race_result f ON f.race_id = q.race_id AND f.driver_id = q.driver_id
        JOIN dim_race r ON r.race_id = q.race_id
        WHERE q.driver_id = :id
        ORDER BY r.season, r.round
        """,
        id=driver_id,
    )

    # recent results
    recent = fetch_all(
        session,
        f"""
        SELECT r.season, r.round, r.name AS race_name, r.date,
               ci.name AS circuit, f.grid, f.position, f.points,
               f.status, f.position_gain, f.fastest_lap_time,
               c.name AS constructor
        {FACT_RR}
        WHERE f.driver_id = :id
        ORDER BY r.date DESC LIMIT 15
        """,
        id=driver_id,
    )

    # wins by circuit
    wins_by_circuit = fetch_all(
        session,
        f"""
        SELECT ci.circuit_id, ci.name AS circuit, COUNT(*) AS wins
        {FACT_RR}
        WHERE f.driver_id = :id AND f.position = 1
        GROUP BY ci.circuit_id, ci.name ORDER BY wins DESC LIMIT 10
        """,
        id=driver_id,
    )

    return {
        "profile": profile,
        "career": career,
        "seasons": seasons,
        "quali_vs_finish": quali_vs_finish,
        "recent_results": recent,
        "wins_by_circuit": wins_by_circuit,
    }


def compare_drivers(session: Session, driver_ids: list[int]) -> dict:
    if not driver_ids:
        return {"drivers": []}
    placeholders = ",".join(str(int(i)) for i in driver_ids[:6])
    rows = fetch_all(
        session,
        f"""
        SELECT d.driver_id, d.full_name AS name, d.code,
               COUNT(*) AS races,
               SUM(f.position = 1) AS wins,
               SUM(f.position <= 3) AS podiums,
               ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
               ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish,
               ROUND(AVG(NULLIF(f.grid, 0)), 2) AS avg_grid,
               ROUND(SUM(f.position IS NULL) / COUNT(*), 3) AS dnf_rate,
               SUM(f.fastest_lap_rank = 1) AS fastest_laps,
               ROUND(AVG(f.position_gain), 2) AS avg_position_gain
        {FACT_RR}
        WHERE f.driver_id IN ({placeholders})
        GROUP BY d.driver_id, d.full_name, d.code
        ORDER BY points DESC
        """,
    )
    return {"drivers": rows}
