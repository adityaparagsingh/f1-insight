"""Performance classification of race results and drivers.

Method (documented, data-driven — no hard-coded labels)
-------------------------------------------------------
For every classified (finished) race result:

    field_size = number of classified finishers in that race
    max_points = points scored by the winner of that race

    performance_score =
        0.60 * (1 - (finish_position - 1) / (field_size - 1))   # track position
      + 0.40 * (points / max_points)                            # championship value

    score >= 0.75  ->  EXCELLENT
    0.50 <= score < 0.75  ->  STRONG
    0.25 <= score < 0.50  ->  AVERAGE
    score < 0.25   ->  POOR

    Did-not-finish (position IS NULL) is always classified POOR.

Driver career classification uses the driver's mean performance score
( minimum 10 races required ) with the same thresholds.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.mining.cache import cached
from app.services.sqlutil import fetch_all, fetch_one

TTL = 1800.0

THRESHOLDS = [
    ("EXCELLENT", 0.75, 1.01),
    ("STRONG", 0.50, 0.75),
    ("AVERAGE", 0.25, 0.50),
    ("POOR", -0.01, 0.25),
]

SQL = """
SELECT f.result_id, f.season, f.race_id, f.driver_id, f.constructor_id,
       f.position, f.points, f.grid, f.position_gain, f.status,
       d.full_name AS driver, d.code,
       c.name AS constructor,
       r.name AS race_name, r.round,
       (SELECT COUNT(*) FROM fact_race_result x
         WHERE x.race_id = f.race_id AND x.position IS NOT NULL) AS field_size,
       (SELECT MAX(y.points) FROM fact_race_result y
         WHERE y.race_id = f.race_id) AS max_points
FROM fact_race_result f
JOIN dim_driver d ON d.driver_id = f.driver_id
JOIN dim_constructor c ON c.constructor_id = f.constructor_id
JOIN dim_race r ON r.race_id = f.race_id
"""


def score_row(position, points, field_size, max_points) -> float | None:
    if position is None:
        return None
    field = max(int(field_size or 1), 2)
    pos_component = 1.0 - (int(position) - 1) / (field - 1)
    mp = float(max_points or 0)
    pts_component = (float(points or 0) / mp) if mp > 0 else 0.0
    return round(0.60 * pos_component + 0.40 * pts_component, 4)


def classify_score(score: float | None) -> str:
    if score is None:
        return "POOR"
    for label, lo, hi in THRESHOLDS:
        if lo <= score < hi:
            return label
    return "POOR"


def run_classification(session: Session, season: int | None = None,
                       force: bool = False) -> dict:
    key = f"classification:{season}"
    if force:
        from app.mining.cache import _STORE
        _STORE.pop(key, None)
    return cached(key, TTL, lambda: _compute(session, season))


def _compute(session: Session, season: int | None) -> dict:
    rows = fetch_all(session, SQL)
    if not rows:
        return {"error": "No race results available."}

    classified_rows, season_rows = [], []
    distribution = {"EXCELLENT": 0, "STRONG": 0, "AVERAGE": 0, "POOR": 0}
    by_season: dict[int, dict] = {}
    driver_scores: dict[int, list[float]] = {}
    driver_meta: dict[int, dict] = {}

    for r in rows:
        score = score_row(r["position"], r["points"], r["field_size"], r["max_points"])
        label = classify_score(score)
        distribution[label] += 1

        s = int(r["season"])
        season_rows.append({"season": s, "score": score, "label": label})
        bucket = by_season.setdefault(
            s, {"EXCELLENT": 0, "STRONG": 0, "AVERAGE": 0, "POOR": 0, "total": 0}
        )
        bucket[label] += 1
        bucket["total"] += 1

        if score is not None:
            driver_scores.setdefault(r["driver_id"], []).append(score)
            driver_meta[r["driver_id"]] = {
                "driver_id": r["driver_id"],
                "name": r["driver"],
                "code": r["code"],
            }

        if season is None or s == season:
            classified_rows.append({
                "season": s,
                "race_name": r["race_name"],
                "driver": r["driver"],
                "code": r["code"],
                "constructor": r["constructor"],
                "grid": r["grid"],
                "position": r["position"],
                "points": r["points"],
                "status": r["status"],
                "performance_score": score,
                "class": label,
            })

    total = sum(distribution.values()) or 1
    distribution_pct = {
        k: {"count": v, "pct": round(v / total * 100, 1)}
        for k, v in distribution.items()
    }

    # season distribution (for chart) — recent 15 seasons
    season_dist = []
    for s in sorted(by_season)[-15:]:
        b = by_season[s]
        season_dist.append({
            "season": s,
            **{k: b[k] for k in ("EXCELLENT", "STRONG", "AVERAGE", "POOR")},
            "total": b["total"],
        })

    # driver career classification (min 10 races with a score)
    drivers = []
    for did, scores in driver_scores.items():
        if len(scores) < 10:
            continue
        mean = sum(scores) / len(scores)
        drivers.append({
            **driver_meta[did],
            "races_scored": len(scores),
            "avg_performance_score": round(mean, 4),
            "class": classify_score(mean),
            "excellent_pct": round(
                sum(1 for s in scores if classify_score(s) == "EXCELLENT")
                / len(scores) * 100, 1
            ),
        })
    drivers.sort(key=lambda d: d["avg_performance_score"], reverse=True)

    sample = classified_rows[-40:]

    return {
        "method": "composite performance score",
        "formula": (
            "score = 0.60 * (1 - (finish-1)/(field_size-1)) + "
            "0.40 * (points / race_winner_points); DNF -> POOR"
        ),
        "thresholds": [
            {"class": label, "min": lo, "max": hi} for label, lo, hi in THRESHOLDS
        ],
        "samples_scanned": len(rows),
        "distribution": distribution_pct,
        "by_season": season_dist,
        "driver_classification": drivers,
        "driver_min_races": 10,
        "season_filter": season,
        "sample_rows": sample,
    }
