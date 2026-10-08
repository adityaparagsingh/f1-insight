"""Race-winner prediction using PRE-RACE information only.

Anti-leakage design
-------------------
Features are strictly information available *before lights out*:
  * grid position / qualifying position
  * driver's historical averages computed from PRIOR races only
    (expanding means shifted by one race)
  * constructor's historical averages from prior races only
  * driver's historical performance at the circuit (prior races only)
  * championship points accumulated BEFORE the race
  * recent form: average of the 5 prior races
Never used: final position, final points of the current race, pit stops,
lap times, fastest laps or anything produced during/after the race.

Evaluation uses a TIME-BASED split (train on earlier seasons, test on the
two most recent seasons) so results are not inflated by random leakage.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy.orm import Session

from app.mining.cache import cached
from app.services.sqlutil import fetch_all

TTL = 1800.0

SQL = """
SELECT f.season, r.round, f.race_id, f.driver_id, f.constructor_id, f.circuit_id,
       f.grid, f.position, f.points,
       q.position AS quali_pos,
       d.full_name AS driver_name, d.code AS driver_code,
       c.name AS constructor_name,
       r.name AS race_name,
       COUNT(*) OVER (PARTITION BY f.race_id) AS field_size,
       MAX(f.points) OVER (PARTITION BY f.race_id) AS race_max_points
FROM fact_race_result f
JOIN dim_driver d ON d.driver_id = f.driver_id
JOIN dim_constructor c ON c.constructor_id = f.constructor_id
JOIN dim_race r ON r.race_id = f.race_id
LEFT JOIN fact_qualifying q
       ON q.race_id = f.race_id AND q.driver_id = f.driver_id
ORDER BY f.season, r.round, f.grid, f.driver_id
"""

FEATURES = [
    "grid",
    "quali_pos",
    "drv_avg_finish_prior",
    "drv_win_rate_prior",
    "drv_podium_rate_prior",
    "con_avg_finish_prior",
    "circuit_avg_finish_prior",
    "pts_before",
    "form5_prior",
]

FEATURE_LABELS = {
    "grid": "Grid position (start)",
    "quali_pos": "Qualifying position",
    "drv_avg_finish_prior": "Driver avg finish (prior races)",
    "drv_win_rate_prior": "Driver win rate (prior races, %)",
    "drv_podium_rate_prior": "Driver podium rate (prior races, %)",
    "con_avg_finish_prior": "Constructor avg finish (prior races)",
    "circuit_avg_finish_prior": "Driver avg finish at circuit (prior)",
    "pts_before": "Championship points before this race",
    "form5_prior": "Recent form: avg finish last 5 races",
}


def _expanding_prior(s: pd.Series) -> pd.Series:
    """Mean of all PRIOR values in the group (current row excluded)."""
    cum = s.cumsum()
    n = pd.Series(np.arange(1, len(s) + 1), index=s.index, dtype=float)
    prior_n = (n - 1).where(n > 1)  # NaN for the first row of each group
    return (cum - s) / prior_n


def build_dataset(session: Session) -> pd.DataFrame:
    df = pd.DataFrame(fetch_all(session, SQL))
    if df.empty:
        return df

    # pymysql returns DECIMAL columns as decimal.Decimal; coerce for pandas
    for col in ("grid", "position", "points", "quali_pos", "field_size",
                "race_max_points"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # DNFs count as last place when building historical averages
    df["pos_for_avg"] = df["position"].fillna(df["field_size"].astype(float))
    df["win_flag"] = (df["position"] == 1).astype(float)
    df["podium_flag"] = (df["position"] <= 3).astype(float)

    g_drv = df.groupby("driver_id", sort=False)
    df["drv_avg_finish_prior"] = g_drv["pos_for_avg"].transform(_expanding_prior)
    df["drv_win_rate_prior"] = g_drv["win_flag"].transform(_expanding_prior) * 100
    df["drv_podium_rate_prior"] = g_drv["podium_flag"].transform(_expanding_prior) * 100

    g_con = df.groupby("constructor_id", sort=False)
    df["con_avg_finish_prior"] = g_con["pos_for_avg"].transform(_expanding_prior)

    g_cc = df.groupby(["driver_id", "circuit_id"], sort=False)
    df["circuit_avg_finish_prior"] = g_cc["pos_for_avg"].transform(_expanding_prior)

    # points accumulated before this race (within the season)
    df["pts_before"] = (
        df.groupby(["driver_id", "season"], sort=False)["points"].cumsum() - df["points"]
    )

    # recent form: mean of the previous up-to-5 races
    df["form5_prior"] = g_drv["pos_for_avg"].transform(
        lambda s: s.rolling(5, min_periods=2).mean().shift(1)
    )

    df["quali_pos"] = df["quali_pos"].fillna(df["grid"])
    df["winner"] = (df["position"] == 1).astype(int)
    return df


def run_prediction(
    session: Session,
    train_until: Optional[int] = None,
    force: bool = False,
) -> dict:
    key = f"prediction:{train_until}"
    if force:
        from app.mining.cache import _STORE
        _STORE.pop(key, None)
    return cached(key, TTL, lambda: _compute(session, train_until))


def _compute(session: Session, train_until: Optional[int]) -> dict:
    df = build_dataset(session)
    if df.empty:
        return {"error": "No race result data available.", "models": {}}

    max_season = int(df["season"].max())
    min_season = int(df["season"].min())
    if train_until is None:
        train_until = max_season - 2
    train_until = max(min_season, min(train_until, max_season - 1))

    model_df = df[
        (df["grid"] > 0)
        & df[FEATURES].notna().all(axis=1)
    ].copy()

    train = model_df[model_df["season"] <= train_until]
    test = model_df[model_df["season"] > train_until]
    split_note = (
        f"time-based split: seasons <= {train_until} train, "
        f"> {train_until} test"
    )
    if len(test) < 50 or len(train) < 50 or train["winner"].sum() < 3:
        # fallback: chronological 80/20 split
        seasons = sorted(model_df["season"].unique())
        cutoff = seasons[max(0, int(len(seasons) * 0.8) - 1)]
        train = model_df[model_df["season"] <= cutoff]
        test = model_df[model_df["season"] > cutoff]
        train_until = int(cutoff)
        split_note = (
            f"fallback chronological split at season {cutoff} "
            "(time-based split produced too few rows)"
        )
    if len(test) == 0 or len(train) == 0:
        return {"error": "Insufficient data to build a train/test split.",
                "split": split_note}

    X_train, y_train = train[FEATURES].astype(float), train["winner"].astype(int)
    X_test, y_test = test[FEATURES].astype(float), test["winner"].astype(int)

    models = {
        "random_forest": RandomForestClassifier(
            n_estimators=200, class_weight="balanced", random_state=42, n_jobs=-1
        ),
        "decision_tree": DecisionTreeClassifier(
            max_depth=6, class_weight="balanced", random_state=42
        ),
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
        ),
    }

    results = {}
    proba_store = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        proba = model.predict_proba(X_test)[:, 1]
        proba_store[name] = proba
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average="binary", zero_division=0
        )
        f1_macro = precision_recall_fscore_support(
            y_test, y_pred, average="macro", zero_division=0
        )[2]
        try:
            auc = float(roc_auc_score(y_test, proba))
        except ValueError:
            auc = None
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist()
        results[name] = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
            "f1_macro": round(float(f1_macro), 4),
            "roc_auc": round(auc, 4) if auc is not None else None,
            "confusion_matrix": {"tn": cm[0][0], "fp": cm[0][1],
                                 "fn": cm[1][0], "tp": cm[1][1]},
        }

    # feature importance (Random Forest) + logistic coefficients
    rf = models["random_forest"]
    importances = sorted(
        [{"feature": f, "label": FEATURE_LABELS[f],
          "importance": round(float(v), 4)}
         for f, v in zip(FEATURES, rf.feature_importances_)],
        key=lambda d: d["importance"], reverse=True,
    )
    lr_coefs = sorted(
        [{"feature": f, "label": FEATURE_LABELS[f],
          "coefficient": round(float(c), 4)}
         for f, c in zip(FEATURES,
                         models["logistic_regression"].named_steps["logisticregression"].coef_[0])],
        key=lambda d: abs(d["coefficient"]), reverse=True,
    )

    # ---- per-race top-1 picks on the test seasons -------------------------
    rf_proba = proba_store["random_forest"]
    picks_frame = test[["race_id", "season", "round", "race_name",
                        "driver_name", "driver_code", "winner"]].copy()
    picks_frame["proba"] = rf_proba
    hits, pick_rows = [], []
    for race_id, grp in picks_frame.groupby("race_id"):
        top = grp.loc[grp["proba"].idxmax()]
        actual = grp[grp["winner"] == 1]
        actual_name = actual["driver_name"].iloc[0] if len(actual) else None
        correct = bool(actual_name and top["driver_name"] == actual_name)
        hits.append(correct)
        pick_rows.append({
            "race_id": int(race_id),
            "season": int(top["season"]),
            "round": int(top["round"]),
            "race_name": top["race_name"],
            "predicted_winner": top["driver_name"],
            "predicted_code": top["driver_code"],
            "probability": round(float(top["proba"]), 4),
            "actual_winner": actual_name,
            "correct": correct,
        })
    pick_rows.sort(key=lambda r: (r["season"], r["round"]))

    return {
        "algorithm": "Random Forest (primary) + Decision Tree + Logistic Regression",
        "task": "Binary classification: will this driver win the race?",
        "target": "winner (position == 1)",
        "features": FEATURES,
        "feature_labels": FEATURE_LABELS,
        "feature_count": len(FEATURES),
        "leakage_policy": (
            "Only pre-race features: grid, qualifying, prior-race historical "
            "averages (shifted), pre-race championship points and prior form. "
            "No final position/points/pit stops/lap times of the current race."
        ),
        "split": split_note,
        "train_until": train_until,
        "sample_size": int(len(model_df)),
        "train_size": int(len(train)),
        "test_size": int(len(test)),
        "train_winners": int(train["winner"].sum()),
        "test_winners": int(y_test.sum()),
        "base_rate": round(float(y_test.mean()), 4),
        "models": results,
        "feature_importances": importances,
        "logistic_coefficients": lr_coefs,
        "winner_picks": {
            "model": "random_forest",
            "races": len(hits),
            "correct": int(sum(hits)),
            "hit_rate": round(float(np.mean(hits)), 4) if hits else None,
            "picks": pick_rows[-25:],
        },
    }
