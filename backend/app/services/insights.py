"""Dynamic insight engine — every insight is computed from the warehouse.

No value in this module is hard-coded; each insight runs SQL (or numpy
statistics) against the loaded data at request time (5-minute cache).
"""
from __future__ import annotations

from app.analytics.stats import pearson
from app.mining.cache import cached
from app.services.sqlutil import fetch_all, fetch_one
from sqlalchemy.orm import Session

TTL = 300.0


def generate_insights(session: Session, force: bool = False) -> list[dict]:
    if force:
        from app.mining.cache import _STORE
        _STORE.pop("insights", None)
    return cached("insights", TTL, lambda: _compute(session))


def _compute(session: Session) -> list[dict]:
    out: list[dict] = []

    def add(category: str, title: str, text: str, value=None, unit=None):
        out.append({
            "id": len(out) + 1,
            "category": category,
            "title": title,
            "text": text,
            "value": value,
            "unit": unit,
        })

    # 1 ------------------------------------------------ qualifying vs finish
    rows = fetch_all(
        session,
        """
        SELECT q.position AS quali_pos, f.position AS finish_pos
        FROM fact_qualifying q
        JOIN fact_race_result f
          ON f.race_id = q.race_id AND f.driver_id = q.driver_id
        WHERE f.position IS NOT NULL
        """,
    )
    corr = pearson([r["quali_pos"] for r in rows], [r["finish_pos"] for r in rows])
    if corr is not None:
        strength = "strong" if abs(corr) >= 0.6 else (
            "moderate" if abs(corr) >= 0.35 else "weak")
        add(
            "Qualifying",
            "Qualifying vs race finish correlation",
            f"Across {len(rows):,} classified finishes, qualifying position and "
            f"finishing position have a {strength} positive correlation of "
            f"r = {corr:.3f}. Qualifying matters, but "
            f"{round((1 - corr ** 2) * 100)}% of finishing-position variance "
            f"remains unexplained by grid slot alone.",
            corr, "pearson r",
        )

    # 2 -------------------------------------------------- outside top-10 gain
    gain = fetch_one(
        session,
        """
        SELECT ROUND(AVG(position_gain), 2) AS avg_gain, COUNT(*) AS n
        FROM fact_race_result
        WHERE grid > 10 AND position IS NOT NULL AND position_gain IS NOT NULL
        """,
    )
    if gain and gain["n"]:
        add(
            "Race Craft",
            "The midfield recovery effect",
            f"Drivers starting outside the top 10 gained an average of "
            f"{gain['avg_gain']} positions per race across {gain['n']:,} starts — "
            f"evidence that race pace and strategy routinely overturn qualifying form.",
            gain["avg_gain"], "positions/race",
        )

    # 3 --------------------------------------------------- best position gain
    best_gain = fetch_one(
        session,
        """
        SELECT d.full_name AS driver, ROUND(AVG(f.position_gain), 2) AS avg_gain,
               COUNT(*) AS races
        FROM fact_race_result f
        JOIN dim_driver d ON d.driver_id = f.driver_id
        WHERE f.position_gain IS NOT NULL AND f.grid > 0
        GROUP BY d.driver_id, d.full_name
        HAVING COUNT(*) >= 50
        ORDER BY avg_gain DESC LIMIT 1
        """,
    )
    if best_gain:
        add(
            "Race Craft",
            f"{best_gain['driver']} is the greatest recoverer",
            f"With a minimum of 50 starts, {best_gain['driver']} gains an average "
            f"of {best_gain['avg_gain']} positions per race — the highest of any "
            f"driver in the warehouse.",
            best_gain["avg_gain"], "positions/race",
        )

    # 4 ------------------------------------------- constructor circuit mastery
    mastery = fetch_one(
        session,
        """
        SELECT c.name AS constructor, ci.name AS circuit,
               SUM(f.position = 1) AS wins, COUNT(*) AS entries,
               ROUND(SUM(f.position = 1) / COUNT(*), 3) AS win_rate
        FROM fact_race_result f
        JOIN dim_constructor c ON c.constructor_id = f.constructor_id
        JOIN dim_circuit ci ON ci.circuit_id = f.circuit_id
        GROUP BY c.constructor_id, c.name, ci.circuit_id, ci.name
        HAVING SUM(f.position = 1) >= 5 AND COUNT(*) >= 8
        ORDER BY win_rate DESC, wins DESC LIMIT 1
        """,
    )
    if mastery:
        add(
            "Constructors",
            "Dominance at a venue",
            f"{mastery['constructor']} owns the strongest venue record in the data: "
            f"{mastery['wins']} wins from {mastery['entries']} entries at "
            f"{mastery['circuit']} — a {round(mastery['win_rate'] * 100, 1)}% win rate "
            f"(minimum 5 wins).",
            mastery["win_rate"], "win rate",
        )

    # 5 ------------------------------------------------ pit stops vs finishing
    pairs = fetch_all(
        session,
        """
        SELECT ROUND(AVG(p.duration), 3) AS avg_duration, f.position
        FROM fact_pit_stop p
        JOIN fact_race_result f ON f.race_id = p.race_id AND f.driver_id = p.driver_id
        WHERE p.duration IS NOT NULL AND p.duration < 90 AND f.position IS NOT NULL
        GROUP BY p.race_id, p.driver_id, f.position
        """,
    )
    pit_corr = pearson(
        [p["avg_duration"] for p in pairs], [p["position"] for p in pairs]
    )
    if pit_corr is not None:
        add(
            "Pit Stops",
            "Pit-stop pace and race result",
            f"Correlating each driver-race average stop duration with final "
            f"position (n = {len(pairs):,}) yields r = {pit_corr:.3f}. "
            + (f"Slower average stops are associated with worse finishes."
               if pit_corr > 0 else
               f"The relationship is weak/nonlinear — stop duration alone "
               f"does not decide results."),
            pit_corr, "pearson r",
        )

    # 6 ------------------------------------------------------- pole conversion
    pole = fetch_one(
        session,
        """
        SELECT SUM(position = 1) AS conversions, COUNT(*) AS poles
        FROM fact_race_result WHERE grid = 1 AND position IS NOT NULL
        """,
    )
    if pole and pole["poles"]:
        rate = round(pole["conversions"] / pole["poles"] * 100, 1)
        add(
            "Qualifying",
            "Pole position conversion",
            f"Of {pole['poles']:,} races started from pole, "
            f"{pole['conversions']:,} were converted into wins ({rate}%). "
            f"Front-row starts still matter, but almost "
            f"{round(100 - rate)}% of poles are lost during the race.",
            rate, "%",
        )

    # 7 --------------------------------------------------- most competitive yr
    gaps = fetch_all(
        session,
        """
        SELECT season, MAX(round) AS last_round FROM fact_driver_standing
        GROUP BY season HAVING MAX(round) > 3
        """,
    )
    competitive, best_gap = None, None
    for g in gaps:
        top2 = fetch_all(
            session,
            """
            SELECT points FROM fact_driver_standing
            WHERE season = :s AND round = :r ORDER BY position LIMIT 2
            """,
            s=g["season"], r=g["last_round"],
        )
        if len(top2) == 2:
            gap = float(top2[0]["points"]) - float(top2[1]["points"])
            if best_gap is None or gap < best_gap:
                best_gap, competitive = gap, g["season"]
    if competitive is not None:
        add(
            "Championships",
            f"{competitive} was the closest title fight",
            f"The {competitive} drivers' championship was decided by just "
            f"{best_gap:g} points — the smallest final margin across every "
            f"season in the warehouse.",
            best_gap, "points",
        )

    # 8 --------------------------------------------------- reliability trend
    rel = fetch_all(
        session,
        """
        SELECT FLOOR(season / 10) * 10 AS decade,
               ROUND(SUM(position IS NULL) / COUNT(*) * 100, 1) AS dnf_rate,
               COUNT(*) AS entries
        FROM fact_race_result
        GROUP BY FLOOR(season / 10) * 10
        ORDER BY decade
        """,
    )
    if len(rel) >= 2:
        first, last = rel[0], rel[-1]
        trend = "improved" if last["dnf_rate"] < first["dnf_rate"] else "worsened"
        add(
            "Reliability",
            "Reliability across the decades",
            f"DNF rates have {trend}: {first['dnf_rate']}% in the "
            f"{first['decade']}s vs {last['dnf_rate']}% in the "
            f"{last['decade']}s over {last['entries']:,} starts. "
            f"Modern cars finish far more often.",
            last["dnf_rate"], "% DNF",
        )

    # 9 ------------------------------------------------- fastest lap ever
    fastest = fetch_one(
        session,
        """
        SELECT l.lap_time, l.lap_milliseconds, l.season,
               d.full_name AS driver, ci.name AS circuit, r.name AS race_name
        FROM fact_lap l
        JOIN dim_driver d ON d.driver_id = l.driver_id
        JOIN dim_race r ON r.race_id = l.race_id
        JOIN dim_circuit ci ON ci.circuit_id = l.circuit_id
        WHERE l.lap_milliseconds IS NOT NULL
        ORDER BY l.lap_milliseconds ASC LIMIT 1
        """,
    )
    if fastest:
        add(
            "Telemetry",
            "Fastest lap on record",
            f"{fastest['driver']} set the quickest lap in the warehouse: "
            f"{fastest['lap_time']} at {fastest['circuit']} "
            f"({fastest['race_name']}, {fastest['season']}).",
            fastest["lap_milliseconds"], "ms",
        )

    # 10 ------------------------------------------------ position gain extremes
    swing = fetch_one(
        session,
        """
        SELECT f.position_gain, d.full_name AS driver, r.name AS race_name,
               r.season, f.grid, f.position
        FROM fact_race_result f
        JOIN dim_driver d ON d.driver_id = f.driver_id
        JOIN dim_race r ON r.race_id = f.race_id
        WHERE f.position_gain IS NOT NULL
        ORDER BY f.position_gain DESC LIMIT 1
        """,
    )
    if swing:
        add(
            "Race Craft",
            "Biggest single-race recovery",
            f"{swing['driver']} climbed from P{swing['grid']} to "
            f"P{swing['position']} at the {swing['race_name']} "
            f"({swing['season']}) — a gain of {swing['position_gain']} positions, "
            f"the largest in the warehouse.",
            swing["position_gain"], "positions",
        )

    # 11 ------------------------------------------------- points explosion
    top_score = fetch_one(
        session,
        """
        SELECT MAX(f.points) AS pts, d.full_name AS driver, r.name AS race_name,
               r.season, c.name AS constructor
        FROM fact_race_result f
        JOIN dim_driver d ON d.driver_id = f.driver_id
        JOIN dim_constructor c ON c.constructor_id = f.constructor_id
        JOIN dim_race r ON r.race_id = f.race_id
        GROUP BY f.result_id, d.full_name, r.name, r.season, c.name
        ORDER BY pts DESC LIMIT 1
        """,
    )
    if top_score and top_score["pts"]:
        add(
            "Scoring",
            "Biggest single-race haul",
            f"{top_score['driver']} scored {top_score['pts']:g} points for "
            f"{top_score['constructor']} at the {top_score['race_name']} "
            f"({top_score['season']}) — the largest one-race score on record.",
            float(top_score["pts"]), "points",
        )

    # 12 ------------------------------------------------- pit-stop evolution
    stops_trend = fetch_all(
        session,
        """
        SELECT season, ROUND(AVG(cnt), 2) AS avg_stops FROM (
            SELECT race_id, season, COUNT(*) AS cnt
            FROM fact_pit_stop GROUP BY race_id, season
        ) x GROUP BY season ORDER BY season
        """,
    )
    if len(stops_trend) >= 2:
        first, last = stops_trend[0], stops_trend[-1]
        add(
            "Pit Stops",
            "The strategy era",
            f"Average stops per race went from {first['avg_stops']} in "
            f"{first['season']} to {last['avg_stops']} in {last['season']} — "
            f"pit-wall strategy now shapes almost every result.",
            last["avg_stops"], "stops/race",
        )

    return out
