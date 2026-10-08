# F1 INSIGHT — OLAP Documentation

OLAP (Online Analytical Processing) is implemented as **ROLAP** — the cube is
the `fact_race_result` fact table conformed with its dimensions, and every
operation compiles down to SQL executed by MySQL in real time.

Endpoints live under `/api/olap/` (see `docs/api.md` for the full list) and are
consumed by the OLAP page of the frontend.

---

## 1. The cube

**Fact**: `fact_race_result` (one row = driver × race)

**Dimensions** (each exposes `{dim}_id`, `{dim}_name`, and for drivers a
`{dim}_code`):

| Dimension          | Key                        | Label              |
|--------------------|----------------------------|--------------------|
| `driver`           | `d.driver_id`              | `d.full_name`      |
| `constructor`      | `c.constructor_id`         | `c.name`           |
| `season`           | `f.season`                 | `f.season`         |
| `circuit`          | `ci.circuit_id`            | `ci.name`          |
| `race`             | `r.race_id`                | `r.name`           |

**Measures** (available in every aggregated result):

| Measure              | Definition                              |
|----------------------|-----------------------------------------|
| `races`              | `COUNT(*)`                              |
| `wins`               | `SUM(position = 1)`                     |
| `podiums`            | `SUM(position <= 3)`                    |
| `points`             | `SUM(points)`                           |
| `avg_finish`         | `AVG(position)` over classified cars    |
| `avg_grid`           | `AVG(grid)` ignoring grid 0             |
| `dnfs`               | `SUM(position IS NULL)`                 |
| `dnf_rate`           | `SUM(position IS NULL) / COUNT(*)`      |
| `avg_position_gain`  | `AVG(position_gain)`                    |
| `avg_pit_stops`      | `AVG(pit_stop_count)`                   |

**Filters** (shared by rollup / dice / pivot): `season`, `season_from`,
`season_to`, `constructor_id`, `circuit_id`, `constructor_ids`,
`circuit_ids`, `driver_ids`.

---

## 2. ROLL-UP — aggregate up dimension hierarchies

Aggregates measures along a comma-separated hierarchy. Removing a dimension
aggregates to a coarser level.

```
GET /api/olap/rollup?dimensions=driver,constructor,season
GET /api/olap/rollup?dimensions=constructor,season&season=2023
```

**Example — constructor-by-season rollup:**

```
GET /api/olap/rollup?dimensions=constructor,season&season_from=2020&limit=50
```

```json
{
  "operation": "rollup",
  "dimensions": ["constructor", "season"],
  "filters": {"season_from": 2020},
  "row_count": 2,
  "rows": [
    {"constructor_id": 6, "constructor_name": "Red Bull",
     "season_id": 2023, "season_name": "2023",
     "races": 44, "wins": 21, "podiums": 30, "points": 860.0,
     "avg_finish": 4.2, "avg_grid": 2.1, "dnfs": 2, "dnf_rate": 0.045,
     "avg_position_gain": 0.5, "avg_pit_stops": 2.1}
  ]
}
```

---

## 3. DRILL-DOWN — descend from coarse to fine detail

Navigates the hierarchy `season → race → driver → lap`. Each level returns the
rows at that level plus the *next* level name and the filters required to
descend further.

```
GET /api/olap/drilldown?level=season            # season aggregates
GET /api/olap/drilldown?level=race&season=2023  # races of a season
GET /api/olap/drilldown?level=driver&race_id=1234
GET /api/olap/drilldown?level=lap&race_id=1234&driver_id=1   # requires race_id
```

**Example — race level:**

```json
{
  "operation": "drilldown",
  "level": "race",
  "next_level": "driver",
  "required_filters": ["race_id"],
  "filters": {"season": 2023, "race_id": null, "driver_id": null},
  "row_count": 1,
  "rows": [
    {"race_id": 1234, "race_name": "2023 R1 — Bahrain Grand Prix",
     "season": 2023, "round": 1, "date": "2023-03-05",
     "circuit": "Bahrain International Circuit", "entries": 20,
     "points": 180.0, "dnfs": 2, "winner": "Max Verstappen"}
  ]
}
```

The lap level switches the query onto `fact_lap`, giving per-lap positions and
times for a race (optionally restricted to one driver).

---

## 4. SLICE — fix one dimension

Keeps the cube only for one dimension value (surrogate id **or** exact label)
and returns totals plus a breakdown by `group_by` (default: `season`; if slicing
on `season`, the default breakdown is `constructor`).

```
GET /api/olap/slice?dimension=constructor&value=Ferrari&group_by=season
GET /api/olap/slice?dimension=season&value=2019
GET /api/olap/slice?dimension=driver&value=1&group_by=constructor
```

**Example:**

```json
{
  "operation": "slice",
  "dimension": "constructor",
  "value": "Ferrari",
  "group_by": "season",
  "totals": {"entries": 2890, "races": 1100, "wins": 243, "podiums": 820,
             "points": 9500.0, "avg_finish": 6.1, "dnfs": 120},
  "breakdown": [
    {"group_value": "2023", "entries": 44, "wins": 1, "points": 406.0, "avg_finish": 7.3},
    ...
  ]
}
```

---

## 5. DICE — filter on multiple dimensions

Applies several filters at once (season range + lists of constructors/circuits/
drivers) and aggregates the resulting sub-cube, with an overall `totals` block.

```
GET /api/olap/dice?season_from=2019&season_to=2023&constructor_ids=1,6&group_by=season,constructor
```

```json
{
  "operation": "dice",
  "group_by": ["season", "constructor"],
  "filters": {"season_from": 2019, "season_to": 2023},
  "totals": {"entries": 880, "wins": 87, "podiums": 220, "points": 6020.0},
  "row_count": 10,
  "rows": [
    {"season_id": 2023, "season_name": "2023",
     "constructor_id": 6, "constructor_name": "Red Bull",
     "races": 22, "wins": 21, "podiums": 30, "points": 860.0, "...": "..."}
  ]
}
```

---

## 6. PIVOT — cross-tabulate two dimensions

Builds a matrix with `rows` dimension as the row axis, `cols` as the column
axis and one `measure` as the cell value. Column and row limits keep the table
wide/tall bounded; row/column totals are computed server-side.

**Measures for pivot**: `points`, `wins`, `podiums`, `races`, `avg_finish`,
`dnfs`, `avg_position_gain`.

```
GET /api/olap/pivot?rows=constructor&cols=season&measure=points&season_from=2020
```

```json
{
  "operation": "pivot",
  "rows_dim": "constructor",
  "cols_dim": "season",
  "measure": "points",
  "filters": {"season_from": 2020},
  "columns": ["2020", "2021", "2022", "2023"],
  "rows": [
    {"key": 6, "label": "Red Bull"},
    {"key": 1, "label": "Mercedes"},
    {"key": 9, "label": "Ferrari"}
  ],
  "values": [[860, 585, 780, 860], [230, 610, 610, 400], [131, 320, 330, 410]],
  "row_totals": [3085.0, 1850.0, 1191.0],
  "col_totals": [1221.0, 1515.0, 1720.0, 1670.0]
}
```

---

## 7. Implementation notes

- All operations are **parameterised SQL** executed live against MySQL — there
  are no pre-aggregated OLAP cubes, which keeps every answer consistent with
  the current warehouse contents.
- `position IS NULL` is treated as DNF throughout (`avg_finish` ignores it,
  `dnfs`/`dnf_rate` count it).
- Integer lists are passed as comma-separated query strings (`?constructor_ids=1,6`).
- Invalid dimensions/measures return HTTP 422 with a descriptive error, e.g.
  `unknown dimension 'team'. allowed: ['circuit', 'constructor', 'driver', 'race', 'season']`.
- Pivot requires `rows_dim ≠ cols_dim`.

## 8. OLAP page (frontend)

The `/olap` route lets users pick an operation, its dimensions/measures/filters
and renders the result as tables and charts. It uses the `useApi` hook so
loading, empty and error states are shown consistently.