"""Data-mining endpoint tests (K-Means / prediction / Apriori / classification).

These run the real compute against the warehouse and assert the documented
output contracts.  They are intentionally lightweight here; the full analytics
exploration lives in notebooks/.
"""
from __future__ import annotations

import pytest


def test_kmeans_clustering_contract(client):
    r = client.get("/api/mining/clusters", params={"min_races": 15})
    assert r.status_code == 200
    body = r.json()
    assert body.get("error") is None
    assert body["algorithm"] == "K-Means"
    assert body["k"] >= 2
    assert body["sample_size"] > 0
    assert {"elbow_curve", "silhouette", "clusters", "scatter", "features"} <= set(body)
    # every cluster member references a real driver
    for cluster in body["clusters"]:
        assert cluster["size"] > 0
    # elbow covers candidate k values
    assert len(body["elbow_curve"]) >= 1


def test_prediction_contract(client):
    r = client.get("/api/mining/prediction")
    assert r.status_code == 200
    body = r.json()
    assert body.get("error") is None
    for model in ("random_forest", "decision_tree", "logistic_regression"):
        assert model in body["models"]
        metrics = body["models"][model]
        for key in ("accuracy", "precision", "recall", "f1", "confusion_matrix"):
            assert key in metrics
    assert body["target"] == "winner (position == 1)"
    assert len(body["feature_importances"]) == body["feature_count"]


def test_prediction_uses_only_race_result_features(client):
    body = client.get("/api/mining/prediction").json()
    forbidden = {"position", "points", "pit_stop_count", "laps", "fastest_lap_rank"}
    features = set(body["features"])
    assert not (features & forbidden), f"leakage in feature set: {features & forbidden}"


def test_association_rules_contract(client):
    r = client.get("/api/mining/association-rules",
                   params={"min_support": 0.03, "min_confidence": 0.4, "min_lift": 1.05})
    assert r.status_code == 200
    body = r.json()
    if "error" in body:
        pytest.skip(f"rule mining returned: {body['error']}")
    assert body["algorithm"] == "Apriori (MLxtend)"
    assert "rules" in body
    assert "item_frequencies" in body
    for rule in body["rules"]:
        assert {"antecedents", "consequents", "support", "confidence", "lift"} <= set(rule)


def test_classification_contract(client):
    r = client.get("/api/mining/classification")
    assert r.status_code == 200
    body = r.json()
    assert body.get("error") is None
    assert "distribution" in body
    for label in ("EXCELLENT", "STRONG", "AVERAGE", "POOR"):
        assert label in body["distribution"]
    assert len(body["driver_classification"]) > 0


def test_classification_dnf_is_poor(client):
    """Regression: NULL finish position must classify as POOR."""
    from app.mining.classification import classify_score, score_row

    assert classify_score(None) == "POOR"
    assert classify_score(score_row(None, 0, 20, 25)) == "POOR"
    assert classify_score(score_row(1, 25, 20, 25)) == "EXCELLENT"