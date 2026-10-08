"""Association rule mining (Apriori) over discretised race characteristics.

Every transaction = one driver-race entry.  Items are symbolic bins derived
from the warehouse; rules are discovered by MLxtend's Apriori implementation
(support / confidence / lift) — no rule is hard-coded.
"""
from __future__ import annotations

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from sqlalchemy.orm import Session

from app.mining.cache import cached
from app.services.sqlutil import fetch_all

TTL = 1800.0

SQL = """
SELECT f.season, f.race_id, f.driver_id, f.constructor_id,
       f.grid, f.position, f.points, f.position_gain,
       f.pit_stop_count, f.fastest_lap_rank,
       q.position AS quali_pos
FROM fact_race_result f
LEFT JOIN fact_qualifying q
       ON q.race_id = f.race_id AND q.driver_id = f.driver_id
"""

ITEM_DEFINITIONS = {
    "qualifying": "Q_TOP3 / Q_4_10 / Q_11_20 / Q_21P — qualifying position bucket",
    "grid": "GRID_POLE / GRID_TOP3 / GRID_4_10 / GRID_11_20 / GRID_21P — start position bucket",
    "constructor_tier": "CTOR_TIER1 / CTOR_TIER2 / CTOR_TIER3 — constructor end-of-season strength tier (points rank 1-3 / 4-10 / 11+)",
    "pit_stops": "PIT_NONE / PIT_ONE / PIT_TWO_PLUS — pit-stop count during the race",
    "outcome": "OUT_WIN / OUT_PODIUM / OUT_POINTS / OUT_NO_SCORE — race outcome bucket",
    "position_change": "GAINED / LOST / NO_CHANGE — net positions vs grid",
    "reliability": "CLASSIFIED / DNF — race completion status",
    "pace": "FL_FAST / FL_SLOW — fastest-lap rank top-5 vs rest",
}


def _quali_bucket(v):
    if pd.isna(v):
        return None
    v = int(v)
    if v <= 3:
        return "Q_TOP3"
    if v <= 10:
        return "Q_4_10"
    if v <= 20:
        return "Q_11_20"
    return "Q_21P"


def _grid_bucket(v):
    v = int(v or 0)
    if v <= 0:
        return None
    if v == 1:
        return "GRID_POLE"
    if v <= 3:
        return "GRID_TOP3"
    if v <= 10:
        return "GRID_4_10"
    if v <= 20:
        return "GRID_11_20"
    return "GRID_21P"


def _outcome(row):
    pos, pts = row["position"], row["points"]
    if pos == 1:
        return "OUT_WIN"
    if pos is not None and pos <= 3:
        return "OUT_PODIUM"
    if pts and float(pts) > 0:
        return "OUT_POINTS"
    return "OUT_NO_SCORE"


def _gain_bucket(row):
    g = row["position_gain"]
    if g is None or pd.isna(g):
        return None
    if g > 0:
        return "GAINED"
    if g < 0:
        return "LOST"
    return "NO_CHANGE"


def run_association(
    session: Session,
    min_support: float = 0.03,
    min_confidence: float = 0.4,
    min_lift: float = 1.05,
    force: bool = False,
) -> dict:
    key = f"assoc:{min_support}:{min_confidence}:{min_lift}"
    if force:
        from app.mining.cache import _STORE
        _STORE.pop(key, None)
    return cached(key, TTL, lambda: _compute(session, min_support, min_confidence, min_lift))


def _compute(session: Session, min_support: float, min_confidence: float,
             min_lift: float) -> dict:
    df = pd.DataFrame(fetch_all(session, SQL))
    if df.empty:
        return {"error": "No data available for association rule mining."}

    # constructor strength tier (end-of-season points rank within season)
    ctor_points = (
        df.groupby(["season", "constructor_id"])["points"].sum().reset_index()
    )
    ctor_points["rank"] = ctor_points.groupby("season")["points"].rank(
        method="first", ascending=False
    )
    ctor_points["tier"] = ctor_points["rank"].apply(
        lambda r: "CTOR_TIER1" if r <= 3 else ("CTOR_TIER2" if r <= 10 else "CTOR_TIER3")
    )
    df = df.merge(
        ctor_points[["season", "constructor_id", "tier"]],
        on=["season", "constructor_id"], how="left",
    )

    transactions: list[list[str]] = []
    for _, row in df.iterrows():
        items: list[str] = []
        qb = _quali_bucket(row["quali_pos"])
        if qb:
            items.append(qb)
        gb = _grid_bucket(row["grid"])
        if gb:
            items.append(gb)
        if row["tier"]:
            items.append(row["tier"])
        stops = int(row["pit_stop_count"] or 0)
        items.append("PIT_NONE" if stops == 0 else ("PIT_ONE" if stops == 1 else "PIT_TWO_PLUS"))
        items.append(_outcome(row))
        gain = _gain_bucket(row)
        if gain:
            items.append(gain)
        items.append("CLASSIFIED" if row["position"] is not None else "DNF")
        rank = row["fastest_lap_rank"]
        if rank is not None and not pd.isna(rank):
            items.append("FL_FAST" if int(rank) <= 5 else "FL_SLOW")
        transactions.append(items)

    exploded = [(i, item) for i, items in enumerate(transactions) for item in items]
    tx = pd.DataFrame(exploded, columns=["txn", "item"])
    onehot = (
        pd.get_dummies(tx["item"])
        .groupby(tx["txn"]).any()
        .reindex(range(len(transactions)), fill_value=False)
    )

    if onehot.shape[1] < 2 or len(onehot) < 30:
        return {"error": "Not enough transactions/items for rule mining.",
                "dataset_size": int(len(onehot))}

    frequent = apriori(onehot, min_support=min_support, use_colnames=True)
    if frequent.empty:
        return {
            "error": "No frequent itemsets at this support threshold.",
            "parameters": {"min_support": min_support,
                           "min_confidence": min_confidence, "min_lift": min_lift},
            "dataset_size": int(len(onehot)),
            "item_count": int(onehot.shape[1]),
            "rules": [],
        }

    rules = association_rules(frequent, metric="confidence",
                              min_threshold=min_confidence)
    rules = rules[rules["lift"] >= min_lift].copy()
    # drop self-referencing rules (overlap between sides)
    rules = rules[
        rules.apply(
            lambda r: len(set(r["antecedents"]) & set(r["consequents"])) == 0, axis=1
        )
    ]
    rules = rules.sort_values(["lift", "confidence"], ascending=False).head(60)

    rule_rows = [
        {
            "antecedents": sorted(r["antecedents"]),
            "consequents": sorted(r["consequents"]),
            "support": round(float(r["support"]), 4),
            "confidence": round(float(r["confidence"]), 4),
            "lift": round(float(r["lift"]), 4),
            "leverage": round(float(r["leverage"]), 4),
            "conviction": round(float(r["conviction"]), 4)
            if pd.notna(r["conviction"]) else None,
            "count": int(round(float(r["support"]) * len(onehot))),
        }
        for _, r in rules.iterrows()
    ]

    item_freq = (
        onehot.sum().sort_values(ascending=False)
        .head(25)
        .rename("count")
        .reset_index()
        .rename(columns={"index": "item"})
    )
    item_rows = [
        {"item": str(r["item"]), "count": int(r["count"]),
         "frequency": round(float(r["count"]) / len(onehot), 4)}
        for _, r in item_freq.iterrows()
    ]

    return {
        "algorithm": "Apriori (MLxtend)",
        "dataset_size": int(len(onehot)),
        "transaction_definition": "one transaction per driver-race entry",
        "item_definitions": ITEM_DEFINITIONS,
        "item_count": int(onehot.shape[1]),
        "frequent_itemsets": int(len(frequent)),
        "parameters": {
            "min_support": min_support,
            "min_confidence": min_confidence,
            "min_lift": min_lift,
        },
        "rule_count": len(rule_rows),
        "rules": rule_rows,
        "item_frequencies": item_rows,
    }
