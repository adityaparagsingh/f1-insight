"""Constructor analytics: list, profile, season series, driver contribution."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.analytics.common import FACT_RR
from app.services.sqlutil import fetch_all, fetch_one


def constructor_list(
    session: Session,
    season: Optional[int] = None,
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
    if search:
        conds.append("(c.name LIKE :q OR c.constructor_ref LIKE :q)")
        params["q"] = f"%{search}%"
    where = " AND ".join(conds)

    sort_map = {
        "points": "points", "wins": "wins", "podiums": "podiums", "races": "races",
        "avg_finish": "avg_finish", "dnf_rate": "dnf_rate", "name": "name",
    }
    sort_col = sort_map.get(sort, "points")
    sort_dir = "ASC" if order.lower() == "asc" else "DESC"

    base = f"""
        SELECT c.constructor_id, c.constructor_ref, c.name,
               c.nationality,
               COUNT(*) AS races,
               SUM(f.position = 1) AS wins,
               SUM(f.position <= 3) AS podiums,
               ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
               ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish,
               SUM(f.position IS NULL) AS dnfs,
               ROUND(SUM(f.position IS NULL) / COUNT(*), 3) AS dnf_rate,
               SUM(f.fastest_lap_rank = 1) AS fastest_laps,
               MIN(f.season) AS first_season, MAX(f.season) AS last_season
        {FACT_RR}
        WHERE {where}
        GROUP BY c.constructor_id, c.constructor_ref, c.name, c.nationality
    """
    params["limit"] = int(limit)
    params["offset"] = int(offset)
    total_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = fetch_all(session, f"SELECT COUNT(*) AS n FROM ({base}) t", **total_params)[0]["n"]
    rows = fetch_all(
        session,
        f"SELECT * FROM ({base}) t ORDER BY {sort_col} {sort_dir}, name ASC LIMIT :limit OFFSET :offset",
        **params,
    )
    return {"total": total, "limit": limit, "offset": offset, "items": rows}


def constructor_profile(session: Session, constructor_id: int) -> Optional[dict]:
    profile = fetch_one(
        session,
        """
        SELECT constructor_id, constructor_ref, name, nationality, url
        FROM dim_constructor WHERE constructor_id = :id
        """,
        id=constructor_id,
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
               SUM(f.position IS NULL) AS dnfs,
               ROUND(SUM(f.position IS NULL) / COUNT(*), 3) AS dnf_rate,
               SUM(f.fastest_lap_rank = 1) AS fastest_laps,
               ROUND(AVG(f.position_gain), 2) AS avg_position_gain
        {FACT_RR}
        WHERE f.constructor_id = :id
        """,
        id=constructor_id,
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
               SUM(f.position IS NULL) AS dnfs,
               ROUND(SUM(f.position IS NULL) / COUNT(*), 3) AS dnf_rate
        {FACT_RR}
        WHERE f.constructor_id = :id
        GROUP BY f.season ORDER BY f.season
        """,
        id=constructor_id,
    )

    champ = {
        r["season"]: r["championship_position"]
        for r in fetch_all(
            session,
            """
            SELECT cs.season, cs.position AS championship_position
            FROM fact_constructor_standing cs
            JOIN (SELECT season, MAX(round) AS mr FROM fact_constructor_standing
                  WHERE constructor_id = :id GROUP BY season) m
              ON m.season = cs.season
            WHERE cs.constructor_id = :id AND cs.round = m.mr
            """,
            id=constructor_id,
        )
    }
    for row in seasons:
        row["championship_position"] = champ.get(row["season"])

    # driver contribution per season
    contribution = fetch_all(
        session,
        f"""
        SELECT f.season, d.driver_id, d.full_name AS driver, d.code,
               SUM(f.points) AS points,
               SUM(f.position = 1) AS wins,
               SUM(f.position <= 3) AS podiums,
               COUNT(*) AS races,
               ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish
        {FACT_RR}
        WHERE f.constructor_id = :id
        GROUP BY f.season, d.driver_id, d.full_name, d.code
        ORDER BY f.season, points DESC
        """,
        id=constructor_id,
    )

    wins_by_circuit = fetch_all(
        session,
        f"""
        SELECT ci.circuit_id, ci.name AS circuit, COUNT(*) AS wins
        {FACT_RR}
        WHERE f.constructor_id = :id AND f.position = 1
        GROUP BY ci.circuit_id, ci.name ORDER BY wins DESC LIMIT 10
        """,
        id=constructor_id,
    )

    return {
        "profile": profile,
        "career": career,
        "seasons": seasons,
        "contribution": contribution,
        "wins_by_circuit": wins_by_circuit,
    }
