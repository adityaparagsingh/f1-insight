"""Qualifying analytics: correlation, grid buckets, per-race results."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.analytics.stats import pearson
from app.services.sqlutil import fetch_all, fetch_one


def _joined_rows(session: Session, season: Optional[int], limit: int = 20000) -> list[dict]:
    where = " WHERE q.season = :season" if season is not None else ""
    params = {"season": season, "limit": int(limit)} if season is not None else {"limit": int(limit)}
    return fetch_all(
        session,
        f"""
        SELECT q.position AS quali_pos, f.position AS finish_pos, f.grid,
               f.position_gain, f.points, q.season, q.race_id, q.driver_id
        FROM fact_qualifying q
        JOIN fact_race_result f ON f.race_id = q.race_id AND f.driver_id = q.driver_id
        {where}
        ORDER BY q.season DESC, q.race_id DESC
        LIMIT :limit
        """,
        **params,
    )


def qualifying_summary(session: Session, season: Optional[int] = None) -> dict:
    rows = _joined_rows(session, season)
    classified = [r for r in rows if r["finish_pos"] is not None]
    correlation = pearson(
        [r["quali_pos"] for r in classified], [r["finish_pos"] for r in classified]
    )
    grid_corr = pearson(
        [r["grid"] for r in classified], [r["finish_pos"] for r in classified]
    )

    # grid bucket analysis
    buckets = [
        ("1-3", 1, 3), ("4-6", 4, 6), ("7-10", 7, 10),
        ("11-15", 11, 15), ("16-20", 16, 20), ("21+", 21, 60),
    ]
    bucket_rows = []
    for label, lo, hi in buckets:
        subset = [r for r in classified if lo <= r["quali_pos"] <= hi]
        if not subset:
            continue
        finishes = [r["finish_pos"] for r in subset]
        bucket_rows.append({
            "bucket": label,
            "races": len(subset),
            "avg_finish": round(sum(finishes) / len(finishes), 2),
            "win_rate": round(sum(1 for f in finishes if f == 1) / len(subset), 4),
            "podium_rate": round(sum(1 for f in finishes if f <= 3) / len(subset), 4),
            "points_per_race": round(
                sum(float(r["points"] or 0) for r in subset) / len(subset), 2
            ),
            "avg_gain": round(
                sum(r["position_gain"] for r in subset
                    if r["position_gain"] is not None)
                / max(sum(1 for r in subset if r["position_gain"] is not None), 1),
                2,
            ),
        })

    # scatter sample (qualifying vs finish)
    scatter = [
        {"x": r["quali_pos"], "y": r["finish_pos"]}
        for r in classified[-1500:]
    ]

    dnfs_by_bucket = []
    for label, lo, hi in buckets:
        subset = [r for r in rows if lo <= r["quali_pos"] <= hi]
        if not subset:
            continue
        dnf = sum(1 for r in subset if r["finish_pos"] is None)
        dnfs_by_bucket.append({"bucket": label, "races": len(subset),
                               "dnf_rate": round(dnf / len(subset), 4)})

    return {
        "sample_size": len(rows),
        "classified": len(classified),
        "correlation_quali_to_finish": correlation,
        "correlation_grid_to_finish": grid_corr,
        "buckets": bucket_rows,
        "dnf_by_bucket": dnfs_by_bucket,
        "scatter": scatter,
    }


def race_qualifying(session: Session, race_id: int) -> list[dict]:
    return fetch_all(
        session,
        """
        SELECT q.position, q.q1, q.q2, q.q3,
               d.driver_id, d.full_name AS driver, d.code,
               c.name AS constructor,
               f.grid, f.position AS finish_pos, f.position_gain, f.points, f.status
        FROM fact_qualifying q
        JOIN dim_driver d ON d.driver_id = q.driver_id
        JOIN dim_constructor c ON c.constructor_id = q.constructor_id
        LEFT JOIN fact_race_result f
               ON f.race_id = q.race_id AND f.driver_id = q.driver_id
        WHERE q.race_id = :id
        ORDER BY q.position
        """,
        id=race_id,
    )


def top_qualifiers(session: Session, season: Optional[int] = None,
                   min_races: int = 5, limit: int = 15) -> list[dict]:
    where = " WHERE q.season = :season" if season is not None else ""
    params: dict = {"limit": int(limit), "min": int(min_races)}
    if season is not None:
        params["season"] = season
    return fetch_all(
        session,
        f"""
        SELECT d.driver_id, d.full_name AS name, d.code,
               COUNT(*) AS sessions,
               ROUND(AVG(q.position), 2) AS avg_quali_pos,
               SUM(q.position = 1) AS poles,
               MIN(q.position) AS best_quali
        FROM fact_qualifying q
        JOIN dim_driver d ON d.driver_id = q.driver_id
        {where}
        GROUP BY d.driver_id, d.full_name, d.code
        HAVING COUNT(*) >= :min
        ORDER BY avg_quali_pos ASC
        LIMIT :limit
        """,
        **params,
    )


def quali_rounds(session: Session, season: int) -> list[dict]:
    """Qualifying positions race-by-race for one driver or whole grid."""
    return fetch_all(
        session,
        """
        SELECT r.round, r.name AS race_name, q.position, d.full_name AS driver
        FROM fact_qualifying q
        JOIN dim_race r ON r.race_id = q.race_id
        JOIN dim_driver d ON d.driver_id = q.driver_id
        WHERE q.season = :season
        ORDER BY r.round, q.position
        """,
        season=season,
    )
