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


def test_analytics_overview_standings_path(client, db):
    """Regression: overview must work when standings rows exist.

    An unqualified `constructor_id` in the constructor-progression query
    raised "Column 'constructor_id' in field list is ambiguous" whenever the
    season had standings data (the earlier suite ran while the standings
    tables were empty, so the bug was masked). Seeds a synthetic season and
    asserts both progression blocks come back.
    """
    from sqlalchemy import text

    season = 2099
    try:
        db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        db.execute(text(
            "INSERT INTO dim_date (date_id, full_date, year, quarter, month,"
            " month_name, day, day_of_week, day_name, week_of_year, is_weekend)"
            " VALUES (900001, '2026-01-01', 2026, 1, 1, 'January', 1, 4,"
            " 'Thursday', 1, 0) ON DUPLICATE KEY UPDATE full_date = full_date"
        ))
        db.execute(text(
            "INSERT INTO dim_circuit (circuit_ref, name) VALUES"
            " ('fetch_test_circuit', 'Fetch Test Circuit')"
            " ON DUPLICATE KEY UPDATE name = name"
        ))
        db.execute(text(
            "INSERT INTO dim_constructor (constructor_ref, name) VALUES"
            " ('fetch_test_ctor', 'Fetch Test Constructor')"
            " ON DUPLICATE KEY UPDATE name = name"
        ))
        db.execute(text(
            "INSERT INTO dim_driver (driver_ref, forename, surname, full_name) VALUES"
            " ('fetch_test_driver', 'Fetch', 'Test', 'Fetch Test')"
            " ON DUPLICATE KEY UPDATE full_name = full_name"
        ))
        db.execute(text(
            "INSERT INTO dim_race (race_ref, season, round, name, date, date_id,"
            " circuit_id) VALUES ('fetch-test-2099', :season, 1, 'Fetch Test GP',"
            " '2026-01-01', 900001, (SELECT circuit_id FROM dim_circuit"
            " WHERE circuit_ref = 'fetch_test_circuit'))"
            " ON DUPLICATE KEY UPDATE name = name"
        ), {"season": season})
        db.execute(text(
            "INSERT INTO fact_race_result (race_id, driver_id, constructor_id,"
            " circuit_id, date_id, season, grid, position, position_text, points,"
            " laps, status, pit_stop_count) VALUES ((SELECT race_id FROM dim_race"
            " WHERE race_ref = 'fetch-test-2099'), (SELECT driver_id FROM dim_driver"
            " WHERE driver_ref = 'fetch_test_driver'), (SELECT constructor_id"
            " FROM dim_constructor WHERE constructor_ref = 'fetch_test_ctor'),"
            " (SELECT circuit_id FROM dim_circuit WHERE circuit_ref ="
            " 'fetch_test_circuit'), 900001, :season, 1, 1, '1', 25, 50,"
            " 'Finished', 0) ON DUPLICATE KEY UPDATE points = points"
        ), {"season": season})
        db.execute(text(
            "INSERT INTO fact_driver_standing (race_id, driver_id, constructor_id,"
            " season, round, position, points, wins) VALUES ((SELECT race_id FROM"
            " dim_race WHERE race_ref = 'fetch-test-2099'), (SELECT driver_id"
            " FROM dim_driver WHERE driver_ref = 'fetch_test_driver'),"
            " (SELECT constructor_id FROM dim_constructor WHERE"
            " constructor_ref = 'fetch_test_ctor'), :season, 1, 1, 25, 0)"
            " ON DUPLICATE KEY UPDATE points = points"
        ), {"season": season})
        db.execute(text(
            "INSERT INTO fact_constructor_standing (race_id, constructor_id,"
            " season, round, position, points, wins) VALUES ((SELECT race_id FROM"
            " dim_race WHERE race_ref = 'fetch-test-2099'), (SELECT"
            " constructor_id FROM dim_constructor WHERE constructor_ref ="
            " 'fetch_test_ctor'), :season, 1, 1, 25, 0)"
            " ON DUPLICATE KEY UPDATE points = points"
        ), {"season": season})
        db.commit()

        r = client.get(f"/api/analytics/overview?season={season}")
        assert r.status_code == 200
        body = r.json()
        assert body["progression"]["season"] == season
        assert body["progression"]["drivers"], "driver progression missing"
        assert body["progression"]["constructors"], "constructor progression missing"
    finally:
        db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table, where in (
            ("fact_constructor_standing", "season = :season"),
            ("fact_driver_standing", "season = :season"),
            ("fact_race_result", "season = :season"),
            ("dim_race", "season = :season"),
            ("dim_driver", "driver_ref = 'fetch_test_driver'"),
            ("dim_constructor", "constructor_ref = 'fetch_test_ctor'"),
            ("dim_circuit", "circuit_ref = 'fetch_test_circuit'"),
            ("dim_date", "date_id = 900001"),
        ):
            db.execute(text(f"DELETE FROM {table} WHERE {where}"), {"season": season})
        db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        db.commit()


def test_unknown_route_is_404(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404


def test_docs_available(client):
    assert client.get("/docs").status_code == 200