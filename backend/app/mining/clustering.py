"""Driver performance clustering with K-Means.

Pipeline
--------
1. Build a per-driver feature matrix from the warehouse (real aggregates).
2. Standardise features (StandardScaler).
3. Select K with the Elbow method + Silhouette scores (k = 2..8).
4. Fit K-Means (fixed random_state for reproducibility) — membership is
   *computed*, never hard-coded.
5. Return cluster statistics, PCA-projected scatter data and centroids.
"""
from __future__ import annotations

import threading
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.mining.cache import cached
from app.services.sqlutil import fetch_all

FEATURES = [
    "avg_finish",
    "avg_quali",
    "win_rate",
    "podium_rate",
    "points_per_race",
    "dnf_rate",
    "avg_lap_seconds",
    "avg_position_gain",
]

FEATURE_LABELS = {
    "avg_finish": "Average finishing position",
    "avg_quali": "Average qualifying position",
    "win_rate": "Win rate (%)",
    "podium_rate": "Podium rate (%)",
    "points_per_race": "Points per race",
    "dnf_rate": "DNF rate (%)",
    "avg_lap_seconds": "Average lap time (s)",
    "avg_position_gain": "Average positions gained",
}

_lock = threading.Lock()
TTL = 900.0  # 15 minutes


def build_feature_frame(session: Session, min_races: int = 15) -> pd.DataFrame:
    """One row per driver with career aggregates (min_races threshold)."""
    rows = fetch_all(
        session,
        """
        SELECT d.driver_id, d.full_name AS name, d.code, d.nationality,
               COUNT(*) AS races,
               AVG(CASE WHEN f.position IS NOT NULL THEN f.position END) AS avg_finish,
               AVG(q.position) AS avg_quali,
               SUM(f.position = 1) / COUNT(*) * 100 AS win_rate,
               SUM(f.position <= 3) / COUNT(*) * 100 AS podium_rate,
               SUM(f.points) / COUNT(*) AS points_per_race,
               SUM(f.position IS NULL) / COUNT(*) * 100 AS dnf_rate,
               AVG(f.position_gain) AS avg_position_gain
        FROM fact_race_result f
        JOIN dim_driver d ON d.driver_id = f.driver_id
        LEFT JOIN fact_qualifying q
               ON q.race_id = f.race_id AND q.driver_id = f.driver_id
        GROUP BY d.driver_id, d.full_name, d.code, d.nationality
        HAVING COUNT(*) >= :min_races
        """,
        min_races=int(min_races),
    )
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # pymysql returns DECIMAL columns as decimal.Decimal; coerce for sklearn
    for col in ("races", "avg_finish", "avg_quali", "win_rate", "podium_rate",
                "points_per_race", "dnf_rate", "avg_position_gain"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    laps = pd.DataFrame(fetch_all(
        session,
        """
        SELECT driver_id, AVG(lap_milliseconds) / 1000.0 AS avg_lap_seconds
        FROM fact_lap
        WHERE lap_milliseconds IS NOT NULL
        GROUP BY driver_id
        """,
    ))
    if not laps.empty:
        laps["avg_lap_seconds"] = pd.to_numeric(laps["avg_lap_seconds"], errors="coerce")
        df = df.merge(laps, on="driver_id", how="left")
    else:
        df["avg_lap_seconds"] = np.nan

    # drivers without recorded laps (pre-lap-data eras): median imputation
    for feature in FEATURES:
        if feature not in df:
            df[feature] = np.nan
        if df[feature].isna().all():
            df[feature] = 0.0
        else:
            df[feature] = df[feature].fillna(df[feature].median())
    df = df.dropna(subset=FEATURES).reset_index(drop=True)
    return df


def run_clustering(
    session: Session,
    k: Optional[int] = None,
    min_races: int = 15,
    force: bool = False,
) -> dict:
    key = f"clusters:{k}:{min_races}"
    if force:
        from app.mining.cache import _STORE
        with _lock:
            _STORE.pop(key, None)
    return cached(key, TTL, lambda: _compute(session, k, min_races))


def _compute(session: Session, k: Optional[int], min_races: int) -> dict:
    df = build_feature_frame(session, min_races=min_races)
    if len(df) < 6:
        return {
            "algorithm": "K-Means",
            "error": "Not enough drivers with the minimum number of races "
                     f"({min_races}) to cluster.",
            "sample_size": int(len(df)),
            "features": FEATURES,
            "clusters": [],
        }

    X = df[FEATURES].astype(float).values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    # ---- elbow + silhouette over k = 2..8 --------------------------------
    max_k = min(8, max(3, len(df) // 8))
    elbow = []
    for trial in range(2, max_k + 1):
        km = KMeans(n_clusters=trial, n_init=10, random_state=42)
        labels = km.fit_predict(Xs)
        sil = float(silhouette_score(Xs, labels)) if len(set(labels)) > 1 else 0.0
        elbow.append({"k": trial, "inertia": round(float(km.inertia_), 3),
                      "silhouette": round(sil, 4)})

    if k is None:
        best = max(elbow, key=lambda e: e["silhouette"])
        k = int(best["k"])
        k_selection = f"automatic: max silhouette among k=2..{max_k}"
    else:
        k_selection = "user-specified"
    k = max(2, min(int(k), len(df) - 1))

    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = km.fit_predict(Xs)
    sil_overall = round(float(silhouette_score(Xs, labels)), 4) if k > 1 else 0.0

    # ---- PCA projection for the scatter plot -----------------------------
    pca = PCA(n_components=2)
    coords = pca.fit_transform(Xs)

    df = df.copy()
    df["cluster"] = labels
    df["x"] = np.round(coords[:, 0], 4)
    df["y"] = np.round(coords[:, 1], 4)

    # ---- centroids (in original feature units) ---------------------------
    centroids_raw = scaler.inverse_transform(km.cluster_centers_)

    clusters = []
    for cid in range(k):
        member = df[df["cluster"] == cid].sort_values("points_per_race", ascending=False)
        centroid = {f: round(float(centroids_raw[cid][i]), 3)
                    for i, f in enumerate(FEATURES)}
        clusters.append({
            "cluster": cid,
            "size": int(len(member)),
            "centroid": centroid,
            "avg_races": round(float(member["races"].mean()), 1),
            "drivers": [
                {
                    "driver_id": int(r.driver_id),
                    "name": r.name,
                    "code": r.code,
                    "cluster": int(r.cluster),
                    "races": int(r.races),
                    "x": float(r.x),
                    "y": float(r.y),
                    **{f: round(float(getattr(r, f)), 3) for f in FEATURES},
                }
                for r in member.itertuples()
            ],
        })

    scatter = [
        {"x": float(r.x), "y": float(r.y), "cluster": int(r.cluster),
         "name": r.name, "code": r.code, "driver_id": int(r.driver_id)}
        for r in df.itertuples()
    ]

    # cluster characterisation: which features separate clusters most
    profile = []
    overall_mean = {f: round(float(df[f].mean()), 3) for f in FEATURES}
    for c in clusters:
        deltas = {
            f: round(c["centroid"][f] - overall_mean[f], 3) for f in FEATURES
        }
        profile.append({
            "cluster": c["cluster"],
            "vs_overall": deltas,
            "standout_features": sorted(deltas, key=lambda f: abs(deltas[f]),
                                        reverse=True)[:3],
        })

    return {
        "algorithm": "K-Means",
        "k": k,
        "k_selection": k_selection,
        "elbow_curve": elbow,
        "silhouette": sil_overall,
        "features": FEATURES,
        "feature_labels": FEATURE_LABELS,
        "feature_count": len(FEATURES),
        "sample_size": int(len(df)),
        "min_races": min_races,
        "pca_explained_variance": [round(float(v), 4) for v in pca.explained_variance_ratio_],
        "scaler_means": {f: round(float(scaler.mean_[i]), 3)
                         for i, f in enumerate(FEATURES)},
        "overall_means": overall_mean,
        "clusters": clusters,
        "profile": profile,
        "scatter": scatter,
        "seed": 42,
        "generated_from": "warehouse aggregates (fact_race_result, fact_qualifying, fact_lap)",
    }
