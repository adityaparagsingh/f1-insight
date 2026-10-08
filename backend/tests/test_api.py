"""API smoke tests: every public route returns 200 with expected shape."""
from __future__ import annotations


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert "warehouse" in body


def test_seasons(client):
    r = client.get("/api/seasons")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) > 30
    assert {"season", "races"} <= set(data[0])


def test_races_paginated(client):
    r = client.get("/api/races", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert len(body["items"]) == 5
    first = body["items"][0]
    assert {"race_id", "name", "season", "round"} <= set(first)


def test_race_detail(client):
    listing = client.get("/api/races", params={"limit": 1}).json()
    race_id = listing["items"][0]["race_id"]
    r = client.get(f"/api/races/{race_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["race"]["race_id"] == race_id
    assert "results" in body


def test_drivers_paginated(client):
    r = client.get("/api/drivers", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 5
    assert "name" in body["items"][0]


def test_driver_detail(client):
    driver_id = client.get("/api/drivers", params={"limit": 1}).json()["items"][0]["driver_id"]
    r = client.get(f"/api/drivers/{driver_id}")
    assert r.status_code == 200
    body = r.json()
    assert "career" in body


def test_constructors_paginated(client):
    r = client.get("/api/constructors", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 5


def test_constructor_detail(client):
    cid = client.get("/api/constructors", params={"limit": 1}).json()["items"][0]["constructor_id"]
    r = client.get(f"/api/constructors/{cid}")
    assert r.status_code == 200


def test_circuits_paginated(client):
    r = client.get("/api/circuits", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 5


def test_circuit_detail(client):
    cid = client.get("/api/circuits", params={"limit": 1}).json()["items"][0]["circuit_id"]
    r = client.get(f"/api/circuits/{cid}")
    assert r.status_code == 200
    assert "profile" in r.json()


def test_analytics_overview(client):
    r = client.get("/api/analytics/overview")
    assert r.status_code == 200
    body = r.json()
    assert "counts" in body
    assert body["counts"]["total_records"] > 0


def test_unknown_route_is_404(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404


def test_docs_available(client):
    assert client.get("/docs").status_code == 200