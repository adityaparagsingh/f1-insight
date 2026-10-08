"""Overview analytics: warehouse counts + dashboard chart datasets."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.analytics.common import FACT_RR
from app.services.sqlutil import fetch_all, scalar


def _counts(session: Session) -> dict:
    tables = [
        "dim_date", "dim_driver", "dim_constructor", "dim_circuit", "dim_race",
        "fact_race_result", "fact_qualifying", "fact_lap", "fact_pit_stop",
        "fact_driver_standing", "fact_constructor_standing",
    ]
    return {
        "seasons": scalar(session, "SELECT COUNT(DISTINCT season) FROM dim_race") or 0,
        "races": scalar(session, "SELECT COUNT(*) FROM dim_race") or 0,
        "drivers": scalar(session, "SELECT COUNT(*) FROM dim_driver") or 0,
        "constructors": scalar(session, "SELECT COUNT(*) FROM dim_constructor") or 0,
        "circuits": scalar(session, "SELECT COUNT(*) FROM dim_circuit") or 0,
        "race_records": scalar(session, "SELECT COUNT(*) FROM fact_race_result") or 0,
        "qualifying_records": scalar(session, "SELECT COUNT(*) FROM fact_qualifying") or 0,
        "lap_records": scalar(session, "SELECT COUNT(*) FROM fact_lap") or 0,
        "pit_stop_records": scalar(session, "SELECT COUNT(*) FROM fact_pit_stop") or 0,
        "driver_standings": scalar(session, "SELECT COUNT(*) FROM fact_driver_standing") or 0,
        "total_records": sum(
            scalar(session, f"SELECT COUNT(*) FROM {t}") or 0 for t in tables
        ),
    }


def _races_by_season(session: Session) -> list[dict]:
    return fetch_all(
        session,
        """
        SELECT season, COUNT(*) AS races, MIN(date) AS first_race, MAX(date) AS last_race
        FROM dim_race GROUP BY season ORDER BY season
        """,
    )


def _champions(session: Session, limit: int = 10) -> list[dict]:
    return fetch_all(
        session,
        """
        WITH final_dr AS (
            SELECT ds.season, ds.driver_id, ds.points,
                   ROW_NUMBER() OVER (PARTITION BY ds.season
                                      ORDER BY ds.round DESC, ds.position ASC) AS rn
            FROM fact_driver_standing ds
            JOIN (SELECT season, MAX(round) AS max_round
                  FROM fact_driver_standing GROUP BY season) m
              ON m.season = ds.season AND m.max_round = ds.round
            WHERE ds.position = 1
        ),
        final_cs AS (
            SELECT cs.season, cs.constructor_id, cs.points,
                   ROW_NUMBER() OVER (PARTITION BY cs.season
                                      ORDER BY cs.round DESC, cs.position ASC) AS rn
            FROM fact_constructor_standing cs
            JOIN (SELECT season, MAX(round) AS max_round
                  FROM fact_constructor_standing GROUP BY season) m
              ON m.season = cs.season AND m.max_round = cs.round
            WHERE cs.position = 1
        )
        SELECT fd.season,
               fd.driver_id,
               dd.full_name AS driver,
               dd.code      AS driver_code,
               fd.points    AS driver_points,
               fc.constructor_id,
               dc.name      AS constructor,
               fc.points    AS constructor_points
        FROM final_dr fd
        JOIN final_cs fc ON fc.season = fd.season AND fc.rn = 1
        JOIN dim_driver dd ON dd.driver_id = fd.driver_id
        JOIN dim_constructor dc ON dc.constructor_id = fc.constructor_id
        WHERE fd.rn = 1
        ORDER BY fd.season DESC
        LIMIT :limit
        """,
        limit=limit,
    )


def _top_drivers(session: Session, season: Optional[int] = None, limit: int = 10) -> list[dict]:
    where, params = ("", {})
    if season is not None:
        where, params = " WHERE f.season = :season", {"season": season}
    params = {**params, "limit": limit}
    return fetch_all(
        session,
        f"""
        SELECT d.driver_id, d.full_name AS name, d.code,
               SUM(f.points) AS points,
               SUM(f.position = 1) AS wins,
               SUM(f.position <= 3) AS podiums,
               COUNT(*) AS races,
               AVG(f.position) AS avg_finish
        {FACT_RR}{where}
        GROUP BY d.driver_id, d.full_name, d.code
        ORDER BY points DESC, wins DESC
        LIMIT :limit
        """,
        **params,
    )


def _constructor_points_by_season(session: Session, seasons_back: int = 8, top_n: int = 6) -> list[dict]:
    return fetch_all(
        session,
        """
        SELECT f.season, c.constructor_id, c.name AS constructor,
               SUM(f.points) AS points,
               SUM(f.position = 1) AS wins
        FROM fact_race_result f
        JOIN dim_constructor c ON c.constructor_id = f.constructor_id
        WHERE f.season >= (SELECT MAX(season) FROM dim_race) - :back
        GROUP BY f.season, c.constructor_id, c.name
        HAVING SUM(f.points) > 0
        ORDER BY f.season, points DESC
        """,
        back=seasons_back - 1,
    )[: 40 * top_n]


def _progression(session: Session, season: Optional[int]) -> dict:
    """Driver championship points progression race-by-race (top 8 drivers)."""
    if season is None:
        season = scalar(session, "SELECT MAX(season) FROM fact_driver_standing")
    if season is None:
        return {"season": None, "rounds": [], "drivers": [], "constructors": []}

    rounds = [r["round"] for r in fetch_all(
        session,
        "SELECT DISTINCT round FROM fact_driver_standing WHERE season = :s "
        "AND round > 0 ORDER BY round",
        s=season,
    )]
    top = fetch_all(
        session,
        """
        SELECT driver_id FROM fact_driver_standing
        WHERE season = :s AND round = (SELECT MAX(round) FROM fact_driver_standing WHERE season = :s)
        ORDER BY position ASC LIMIT 8
        """,
        s=season,
    )
    drivers = []
    for t in top:
        rows = fetch_all(
            session,
            """
            SELECT round, points FROM fact_driver_standing
            WHERE season = :s AND driver_id = :d AND round > 0 ORDER BY round
            """,
            s=season, d=t["driver_id"],
        )
        name = scalar(
            session, "SELECT full_name FROM dim_driver WHERE driver_id = :d", d=t["driver_id"]
        )
        code = scalar(
            session, "SELECT code FROM dim_driver WHERE driver_id = :d", d=t["driver_id"]
        )
        by_round = {r["round"]: float(r["points"]) for r in rows}
        # standings points are cumulative after each round
        cumulative, running = [], 0.0
        for rnd in rounds:
            if rnd in by_round:
                running = by_round[rnd]
            cumulative.append(round(running, 2))
        drivers.append({"driver_id": t["driver_id"], "name": name, "code": code,
                        "points": cumulative})

    ctors = fetch_all(
        session,
        """
        SELECT cs.constructor_id, c.name FROM fact_constructor_standing cs
        JOIN dim_constructor c ON c.constructor_id = cs.constructor_id
        WHERE cs.season = :s AND cs.round = (SELECT MAX(cs2.round) FROM fact_constructor_standing cs2 WHERE cs2.season = :s)
        ORDER BY cs.position ASC LIMIT 6
        """,
        s=season,
    )
    constructors = []
    for t in ctors:
        rows = fetch_all(
            session,
            """
            SELECT round, points FROM fact_constructor_standing
            WHERE season = :s AND constructor_id = :c AND round > 0 ORDER BY round
            """,
            s=season, c=t["constructor_id"],
        )
        by_round = {r["round"]: float(r["points"]) for r in rows}
        cumulative, running = [], 0.0
        for rnd in rounds:
            if rnd in by_round:
                running = by_round[rnd]
            cumulative.append(round(running, 2))
        constructors.append({"constructor_id": t["constructor_id"], "name": t["name"],
                             "points": cumulative})

    return {"season": season, "rounds": rounds, "drivers": drivers,
            "constructors": constructors}


def _recent_races(session: Session, limit: int = 8) -> list[dict]:
    return fetch_all(
        session,
        """
        SELECT r.race_id, r.season, r.round, r.name, r.date,
               ci.name AS circuit, ci.country,
               d.full_name AS winner, d.code AS winner_code,
               c.name AS winning_constructor,
               f.points AS winner_points,
               f.fastest_lap_time AS fastest_lap
        FROM fact_race_result f
        JOIN dim_race r ON r.race_id = f.race_id
        JOIN dim_driver d ON d.driver_id = f.driver_id
        JOIN dim_constructor c ON c.constructor_id = f.constructor_id
        JOIN dim_circuit ci ON ci.circuit_id = f.circuit_id
        WHERE f.position = 1
        ORDER BY r.date DESC, r.season DESC, r.round DESC
        LIMIT :limit
        """,
        limit=limit,
    )


def overview(session: Session, season: Optional[int] = None) -> dict:
    return {
        "counts": _counts(session),
        "races_by_season": _races_by_season(session),
        "champions": _champions(session, limit=12),
        "top_drivers": _top_drivers(session, season=season, limit=10),
        "constructor_points": _constructor_points_by_season(session),
        "progression": _progression(session, season),
        "recent_races": _recent_races(session, limit=8),
    }
