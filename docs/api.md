# F1 INSIGHT — API Documentation

Base URL: `http://127.0.0.1:8000/api` (configurable via `API_HOST` / `API_PORT`
/ `VITE_API_BASE_URL`).

Interactive documentation: **Swagger UI** at `/docs`, **ReDoc** at `/redoc`.

All endpoints are `GET`. Responses are JSON. Errors follow the FastAPI/OpenAPI
convention: `{"detail": "..."}` with an appropriate HTTP status (400/404/422/
500). Pagination uses `limit` + `offset` query parameters.

> Examples in this document are illustrative — values depend on the contents of
> the loaded warehouse.

---

## 1. System

### `GET /api/health`
Service + warehouse status. Returns row counts of the main tables and the most
recent ETL audit row.

```json
{
  "status": "ok",
  "service": "F1 INSIGHT API",
  "version": "1.0.0",
  "database": "connected",
  "time": "2026-10-09T00:00:00Z",
  "warehouse": {
    "seasons": 77, "races": 1172, "drivers": 857, "constructors": 213,
    "circuits": 78, "race_records": 26136, "lap_records": 120000,
    "qualifying_records": 11320, "pit_stop_records": 50000
  },
  "etl_last_run": {
    "run_id": 12, "pipeline": "full", "scope": "all",
    "started_at": "2026-10-08T22:00:00", "finished_at": null,
    "status": "RUNNING", "records_extracted": 40000,
    "records_transformed": 40000, "records_loaded": 200000, "errors": 0
  }
}
```

---

## 2. Reference data

### `GET /api/seasons`
All seasons with race/result counts and date range.

| Query | Type | Default | Notes |
|-------|------|---------|-------|
| —     | —    | —       | returns every season |

```json
[{"season": 2025, "races": 24, "results": 480,
  "first_race": "2025-03-14", "last_race": "2025-11-23"}]
```

### `GET /api/races`
Paginated race list with winners.

| Query       | Type    | Default | Notes                        |
|-------------|---------|---------|------------------------------|
| `season`    | int     | —       | 1950–2100                    |
| `circuit_id`| int     | —       |                              |
| `search`    | string  | —       | text match on race name      |
| `limit`     | int     | 30      | 1–200                        |
| `offset`    | int     | 0       |                              |

```json
{"total": 1172, "limit": 30, "offset": 0, "items": [
  {"race_id": 1001, "season": 2025, "round": 1, "name": "Australian Grand Prix",
   "date": "2025-03-14", "circuit_id": 17, "circuit": "Albert Park Grand Prix Circuit",
   "country": "Australia", "winner": "Max Verstappen",
   "winner_code": "VER", "winning_constructor": "Red Bull", "entries": 20}
]}
```

### `GET /api/races/{race_id}`
Race detail (timing-screen data): winner, results, fastest laps, pit stops,
laps summary. 404 if the race does not exist.

### `GET /api/drivers`
Paginated driver list with career aggregates and sorting.

| Query            | Type    | Default | Notes |
|------------------|---------|---------|-------|
| `season`         | int     | —       | restrict to a season |
| `constructor_id` | int     | —       | restrict to a team  |
| `search`         | string  | —       | name text match     |
| `sort`           | string  | `points`| `points`, `wins`, `podiums`, `races`, `avg_finish`, `avg_grid`, `dnf_rate`, `position_gain`, `name` |
| `order`          | string  | `desc`  | `asc` / `desc`      |
| `limit`/`offset` | int     | 50 / 0  |                     |

```json
{"total": 857, "limit": 2, "offset": 0, "items": [
  {"driver_id": 1, "driver_ref": "hamilton", "code": "HAM",
   "name": "Lewis Hamilton", "full_name": "Lewis Hamilton", "number": 44,
   "nationality": "British", "races": 340, "wins": 103, "podiums": 197,
   "points": 4700.0, "avg_finish": 5.8, "avg_grid": 4.2, "dnf_rate": 9.1,
   "win_rate": 30.3, "podium_rate": 57.9, "teams": "McLaren, Mercedes"}
]}
```

### `GET /api/drivers/{driver_id}`
Driver profile: biography fields plus career analytics (year-by-year results,
top circuits, team history). 404 if not found.

### `GET /api/constructors`
Paginated constructor list with aggregates.

| Query       | Type   | Default | Notes |
|-------------|--------|---------|-------|
| `season`    | int    | —       |       |
| `search`    | string | —       |       |
| `sort`      | string | `points`| `points`, `wins`, `podiums`, `races`, `avg_finish`, `dnf_rate`, `name` |
| `order`     | string | `desc`  |       |
| `limit`/`offset` | int | 50 / 0 |  |

### `GET /api/constructors/{constructor_id}`
Constructor profile + analytics.

### `GET /api/circuits`
Paginated circuit list.

| Query       | Type   | Default | Notes |
|-------------|--------|---------|-------|
| `search`    | string | —       |       |
| `country`   | string | —       |       |
| `limit`/`offset` | int | 100 / 0 |  |

### `GET /api/circuits/{circuit_id}`
Circuit profile + venue analytics (top-`profile` key in the detail payload).

---

## 3. Analytics

### `GET /api/analytics/overview`
Dashboard aggregates and chart datasets. Optional `season` filter.

```json
{
  "counts": {"seasons": 77, "races": 1172, "drivers": 857, "constructors": 213,
             "circuits": 78, "race_records": 26136, "qualifying_records": 11320,
             "lap_records": 120000, "pit_stop_records": 50000,
             "driver_standings": 15000, "total_records": 250000},
  "races_by_season": [{"season": 1950, "races": 7}],
  "champions": [{"season": 2025, "driver_id": 1, "driver": "Max Verstappen",
                 "driver_code": "VER", "driver_points": 437.0,
                 "constructor_id": 6, "constructor": "Red Bull",
                 "constructor_points": 680.0}],
  "top_drivers": [{"driver_id": 1, "name": "Max Verstappen", "code": "VER",
                   "points": 437.0, "wins": 9, "podiums": 17, "races": 24,
                   "avg_finish": 3.1}],
  "constructor_points": [{"season": 2025, "constructor_id": 6,
                          "constructor": "Red Bull", "points": 680.0, "wins": 9}],
  "progression": {"season": 2025, "rounds": [1, 2, 3],
                  "drivers": [{"driver_id": 1, "name": "Max Verstappen",
                               "code": "VER", "points": [25, 43, 68]}],
                  "constructors": [{"constructor_id": 6, "name": "Red Bull",
                                    "points": [44, 78, 120]}]},
  "recent_races": [{"race_id": 1001, "season": 2025, "round": 1,
                    "name": "Australian Grand Prix", "date": "2025-03-14",
                    "circuit": "Albert Park Grand Prix Circuit", "country": "Australia",
                    "winner": "Max Verstappen", "winner_code": "VER",
                    "winning_constructor": "Red Bull", "winner_points": 25.0,
                    "fastest_lap": "1:20.841"}]
}
```

### `GET /api/analytics/drivers`
Same shape/logic as `GET /api/drivers` (aggregates + filters + sorting).

### `GET /api/analytics/drivers/compare?ids=1,44`
Side-by-side comparison of two or more drivers (career totals, per-season
series).

### `GET /api/analytics/constructors`
Constructor aggregates (as `GET /api/constructors`).

### `GET /api/analytics/circuits`
Enriched circuit aggregates.

### `GET /api/analytics/races`
Race results overview with filters (`season`, `circuit_id`, `search`,
`limit`, `offset`).

### `GET /api/analytics/races/position-changes`
Biggest position gains/losses.

| Query    | Type | Default | Notes |
|----------|------|---------|-------|
| `season` | int  | —       |       |
| `limit`  | int  | 20      | 1–100 |

### `GET /api/analytics/qualifying`
Qualifying analytics. Without `race_id`: correlation between qualifying and
race position, position buckets and `top_qualifiers` for a `season`. With
`race_id`: the qualifying grid for that race.

### `GET /api/analytics/pit-stops`
Pit-stop analytics: average durations, stop counts, correlation with results.

| Query            | Type | Default | Notes |
|------------------|------|---------|-------|
| `season`         | int  | —       |       |
| `constructor_id` | int  | —       |       |
| `circuit_id`     | int  | —       |       |

---

## 4. OLAP

All OLAP endpoints share the measure set defined in `docs/olap.md`.

### `GET /api/olap/rollup`
Aggregate up `dimensions` (comma-separated). Shared filters apply
(`season`, `season_from`, `season_to`, `constructor_id`, `circuit_id`,
`constructor_ids`, `circuit_ids`, `driver_ids`; `limit` 1–1000, default 200).

```
GET /api/olap/rollup?dimensions=constructor,season&season_from=2020
```

### `GET /api/olap/drilldown`
`level` ∈ `season|race|driver|lap` (+ `season`, `race_id`, `driver_id`,
`limit` 1–2000). Lap level requires `race_id`.

### `GET /api/olap/slice`
`dimension` ∈ `driver|constructor|season|circuit|race`, `value` = id or exact
label, `group_by` optional.

### `GET /api/olap/dice`
`season`/`season_from`/`season_to`, `constructor_ids`, `circuit_ids`,
`driver_ids`, `group_by` (comma-separated, default `season,constructor`).

### `GET /api/olap/pivot`
`rows`, `cols` ∈ the five dimensions (must differ); `measure` ∈ `points`,
`wins`, `podiums`, `races`, `avg_finish`, `dnfs`, `avg_position_gain`;
`limit_rows`/`limit_cols` (default 25 each).

Full details, contracts and matrix examples: `docs/olap.md`.

---

## 5. Data mining

All mining endpoints accept `?force=true` to bypass the in-process cache.

### `GET /api/mining/clusters`
K-Means driver clustering. `k` (2–8, auto by default), `min_races` (5–100,
default 15), `force`.

### `GET /api/mining/prediction`
Winner prediction. `train_until` (season to train through; default two
seasons before the latest), `force`.

### `GET /api/mining/association-rules`
Apriori rules. `min_support` (0.001–0.5, default 0.03), `min_confidence`
(0.05–1.0, default 0.4), `min_lift` (0–10, default 1.05), `force`.

### `GET /api/mining/classification`
E/S/A/P performance classification. `season`, `force`.

Methods, features, formulas and response contracts: `docs/data_mining.md`.

---

## 6. Insights

### `GET /api/insights`
Dynamically computed findings (SQL + numpy against the warehouse, 5-minute
cache).

```json
{
  "count": 12,
  "items": [
    {"id": 1, "category": "Qualifying",
     "title": "Qualifying vs race finish correlation",
     "text": "Across 26,136 classified finishes, ... r = 0.682.",
     "value": 0.682, "unit": "pearson r"},
    {"id": 6, "category": "Qualifying",
     "title": "Pole position conversion",
     "text": "Of 1,055 races started from pole, 447 were converted into wins (42.4%).",
     "value": 42.4, "unit": "%"}
  ]
}
```

---

## 7. Common query parameters

| Parameter | Where | Notes |
|-----------|-------|-------|
| `season`  | many  | year filter (1950–2100) |
| `limit` / `offset` | lists | pagination (bounds per endpoint) |
| `force`   | mining + insights | recompute ignoring cache |
| `ids` (CSV) | compare / dice / pivot | comma-separated integers |

## 8. Error handling

| Status | Meaning |
|--------|---------|
| 404    | resource not found (e.g. `races/99999`) |
| 422    | validation error (bad enum, unknown dimension/measure, missing required param) |
| 500    | unexpected server error (message includes exception type) |

The OLAP and mining services raise `ValueError` for unknown dimensions /
measures; the routers convert these to HTTP 422 with a helpful `detail`, e.g.
`unknown measure 'x'. allowed: ['avg_finish', 'avg_position_gain', 'dnfs', 'podiums', 'points', 'races', 'wins']`.