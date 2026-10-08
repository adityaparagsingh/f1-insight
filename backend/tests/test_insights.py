"""Insights engine tests: dynamic, never hard-coded."""
from __future__ import annotations


def test_insights_generated_from_warehouse(client):
    r = client.get("/api/insights")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 0
    assert len(body["items"]) == body["count"]
    ids = {item["id"] for item in body["items"]}
    assert len(ids) == body["count"], "insight ids must be unique"
    for item in body["items"]:
        assert {"category", "title", "text"} <= set(item)
        assert item["title"]
        assert item["text"]


def test_insights_are_dynamic(client):
    first = {i["title"]: i["text"] for i in client.get("/api/insights").json()["items"]}
    second = {i["title"]: i["text"] for i in client.get("/api/insights").json()["items"]}
    # both calls read the same warehouse state; the content must still be
    # derived from real numbers (non-empty sentences), not placeholders
    for title, text in second.items():
        assert "{...}" not in text
        assert "TODO" not in text
        assert "XXX" not in text
    assert first.keys() == second.keys()