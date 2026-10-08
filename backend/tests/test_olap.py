"""OLAP endpoint tests: roll-up, drill-down, slice, dice, pivot."""
from __future__ import annotations


def test_rollup_defaults(client):
    r = client.get("/api/olap/rollup", params={"limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["operation"] == "rollup"
    assert body["row_count"] > 0
    assert "points" in body["rows"][0]


def test_rollup_by_season(client):
    r = client.get("/api/olap/rollup", params={"dimensions": "season", "limit": 30})
    assert r.status_code == 200
    body = r.json()
    assert body["dimensions"] == ["season"]
    assert body["row_count"] > 20


def test_rollup_rejects_unknown_dimension(client):
    r = client.get("/api/olap/rollup", params={"dimensions": "banana"})
    assert r.status_code == 422


def test_drilldown_season_level(client):
    r = client.get("/api/olap/drilldown", params={"level": "season", "limit": 30})
    assert r.status_code == 200
    body = r.json()
    assert body["level"] == "season"
    assert body["next_level"] == "race"
    assert body["row_count"] > 20


def test_drilldown_race_level(client):
    r = client.get("/api/olap/drilldown", params={"level": "race", "season": 2023, "limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["level"] == "race"
    assert len(body["rows"]) > 0
    assert "race_name" in body["rows"][0]


def test_drilldown_lap_requires_race_id(client):
    r = client.get("/api/olap/drilldown", params={"level": "lap"})
    assert r.status_code == 422


def test_slice_by_season(client):
    r = client.get("/api/olap/slice", params={"dimension": "season", "value": "2023",
                                              "group_by": "constructor", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["operation"] == "slice"
    assert body["totals"]["entries"] > 0
    assert len(body["breakdown"]) > 0


def test_dice_filters_on_multiple_dimensions(client):
    r = client.get("/api/olap/dice", params={
        "season_from": 2020, "season_to": 2024,
        "constructor_ids": "1,3", "group_by": "season,constructor", "limit": 20,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["operation"] == "dice"
    assert body["row_count"] > 0
    assert "totals" in body


def test_pivot_cross_tabulation(client):
    r = client.get("/api/olap/pivot", params={
        "rows": "constructor", "cols": "season", "measure": "wins",
        "season_from": 2020, "season_to": 2024,
        "limit_rows": 10, "limit_cols": 10,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["operation"] == "pivot"
    assert len(body["columns"]) > 0
    assert len(body["rows"]) > 0
    assert len(body["values"]) == len(body["rows"])
    assert len(body["values"][0]) == len(body["columns"])


def test_pivot_rejects_same_row_and_col(client):
    r = client.get("/api/olap/pivot", params={"rows": "season", "cols": "season"})
    assert r.status_code == 422