# F1 INSIGHT — System Architecture

This document describes the end-to-end architecture of the F1 INSIGHT system:
how real Formula 1 data flows from the Jolpica (Ergast-compatible) API through
an idempotent ETL pipeline into a MySQL star-schema warehouse, and how the
FastAPI backend (OLAP + analytics + data mining) and the React frontend consume
it.

---

## 1. Overview

F1 INSIGHT is a three-tier application:

```
┌──────────────────┐      ┌───────────────────────────────┐      ┌───────────────────┐
│  Jolpica F1 API  │      │  Backend (FastAPI + Python)    │      │  Frontend         │
│  (Ergast format) │ ───► │  ETL ─► MySQL star schema      │ ───► │  React + Vite     │
│  api.jolpi.ca    │ HTTP │  ─► REST /api/* + /docs         │ JSON │  Recharts UI      │
└──────────────────┘      └───────────────────────────────┘      └───────────────────┘
        ^                          ^       ^
        │                          │       └── data mining (scikit-learn / MLxtend)
        │                          └────────── OLAP + analytics (ROLAP over MySQL)
        └── real historical F1 data (1950 → current season)
```

- **Data source**: [Jolpica F1](https://api.jolpi.ca/ergast/f1) — a free,
  community-maintained, Ergast-compatible JSON API covering seasons from 1950
  to the current season.
- **ETL**: Python package (`backend/etl/`) that extracts, transforms, cleans
  and idempotently loads into the warehouse.
- **Warehouse**: MySQL 8+ star schema with 6 fact tables, 5 dimensions and an
  `etl_run_log` audit table.
- **Backend**: FastAPI exposing reference data, analytics, OLAP, data-mining
  and insights endpoints under `/api/`.
- **Frontend**: React + Vite + React Router + Recharts single-page app with an
  F1-themed dark UI (12+ routes).

---

## 2. Component diagram

```
 f1-insight/
 ├── database/
 │   └── schema.sql            # authoritative star-schema DDL (source of truth)
 │
 ├── backend/
 │   ├── etl/
 │   │   ├── run.py            # CLI entry point (python -m etl.run)
 │   │   ├── runner.py         # stage orchestration + idempotent runner
 │   │   ├── extract/          # Jolpica HTTP client, rate limiting, retry, cache
 │   │   ├── transform/        # normalisation, enrichment, data-quality tracking
 │   │   ├── load/             # upserts, FK resolution, batch inserts
 │   │   └── pipelines/        # per-stage pipeline implementations
 │   ├── app/
 │   │   ├── main.py           # FastAPI app + CORS + routers under /api
 │   │   ├── api/              # route handlers (reference, analytics, olap,
 │   │   │                     #   mining, insights, health)
 │   │   ├── analytics/        # analytical SQL services (incl. olap.py)
 │   │   ├── mining/           # clustering, prediction, association, classification
 │   │   ├── models/           # SQLAlchemy ORM models (mirror schema.sql)
 │   │   ├── schemas/          # Pydantic response models
 │   │   ├── services/         # shared SQL helpers, dynamic insights engine
 │   │   └── config.py         # environment-driven configuration
 │   ├── alembic/              # migrations (tables are created idempotently)
 │   └── tests/                # pytest suite (ETL, DB, API, analytics, OLAP, mining)
 │
 ├── frontend/
 │   ├── src/
 │   │   ├── pages/            # Dashboard, Seasons, Drivers, Constructors,
 │   │   │                     #   Circuits, Races (+detail pages), OLAP,
 │   │   │                     #   Mining, Insights, About, NotFound
 │   │   ├── components/       # Layout, shared UI (cards, tables, states)
 │   │   ├── charts/           # Recharts wrappers
 │   │   ├── services/api.js   # API client (fetch wrapper)
 │   │   ├── hooks/useApi.js   # loading/empty/error state hook
 │   │   └── styles/global.css # F1 dark theme
 │   └── vite.config.js
 │
 ├── notebooks/                # Jupyter notebooks (ETL, OLAP, mining, insights)
 ├── scripts/                  # helper shell scripts (run, smoke, status)
 ├── docs/                     # SRS, architecture, data dictionary, OLAP,
 │                             #   data mining, API, setup
 ├── docker-compose.yml        # MySQL service (optional)
 └── .env.example              # documented environment template
```

---

## 3. Data flow (end to end)

1. **Extract** — the ETL requests Jolpica endpoints (season list, races,
   results, qualifying, pit stops, laps, driver/constructor standings). The
   HTTP client applies `requests_per_second` throttling, exponential-backoff
   retries on HTTP 429/5xx, and disk caching under `backend/etl/cache/` so
   re-runs do not re-hit the network unnecessarily.
2. **Transform** — raw JSON is flattened, normalised (timings converted to
   milliseconds, DECIMAL coercion, missing values imputed/flagged) and enriched
   with the derived metric `position_gain = grid − position`. Every change is
   counted for the quality report.
3. **Load** — star-schema upserts. Dimension rows are matched on natural keys
   (`driver_ref`, `constructor_ref`, `circuit_ref`, `race_ref`, `full_date`);
   fact rows on `(race_id, driver_id[, lap|stop_number])` or
   `(season, round, driver_id)`. Because the load is an **upsert**, re-running
   a stage never duplicates rows (idempotent).
4. **Serve** — the FastAPI backend exposes analytical SQL (reference, OLAP,
   insights) and in-process data-mining results (cached with a TTL).
5. **Render** — the React app calls `/api/*` and renders charts, timing-style
   tables and cards.

### ETL stage order

| # | Stage            | Scope (full load)          | Tables written                                   |
|---|------------------|----------------------------|--------------------------------------------------|
| 1 | reference        | all seasons                | dim_date, dim_race, dim_circuit, dim_driver, dim_constructor |
| 2 | results          | all seasons                | fact_race_result                                 |
| 3 | qualifying       | all seasons                | fact_qualifying                                  |
| 4 | pitstops         | seasons ≥ 2011 (configurable) | fact_pit_stop                                  |
| 5 | standings        | seasons ≥ 1980 (configurable) | fact_driver_standing, fact_constructor_standing |
| 6 | laps             | seasons ≥ 2015 (configurable) | fact_lap (largest table, 100k+ rows)           |

`fact_lap` dominates the row count (one row per driver per lap) and is the
reason the warehouse comfortably exceeds the 10,000-record requirement with
100,000+ records in practice.

---

## 4. Warehouse model

Star schema (see `database/schema.sql` and `docs/data_dictionary.md`):

- **Dimensions**: `dim_date`, `dim_driver`, `dim_constructor`, `dim_circuit`,
  `dim_race` (a conformed mini-dimension of a Grand Prix).
- **Facts**: `fact_race_result`, `fact_qualifying`, `fact_lap`,
  `fact_pit_stop`, `fact_driver_standing`, `fact_constructor_standing`.
- **Audit**: `etl_run_log` records one row per pipeline run with extract /
  transform / load counts, duplicates removed, missing values fixed, errors and
  status.
- All FKs are real FOREIGN KEY constraints; surrogate keys are AUTO_INCREMENT;
  natural keys are UNIQUE for idempotent upserts. `season` is denormalised into
  the large fact tables as a degenerate dimension for fast filtering.

Tables are created by `database/schema.sql` (MySQL 8+) and mirrored by Alembic
migrations and SQLAlchemy ORM models.

---

## 5. Backend API layer

| Router       | Prefix        | Purpose                                        |
|--------------|---------------|------------------------------------------------|
| health       | `/api`        | `/api/health` — service + warehouse status, row counts, last ETL run |
| reference    | `/api`        | seasons, races, drivers, constructors, circuits (list + detail) |
| analytics    | `/api/analytics` | overview, driver/constructor/circuit/race aggregates, qualifying, pit stops |
| olap         | `/api/olap`   | rollup, drilldown, slice, dice, pivot           |
| mining       | `/api/mining` | clusters, prediction, association-rules, classification |
| insights     | `/api/insights` | dynamically computed findings (SQL/numpy, 5-min cache) |

Interactive OpenAPI documentation is available at `/docs` and `/redoc`.
All routes live under `/api/`; the root `/` returns a small service banner.

### Caching strategy

Data-mining and insight results are computed against the warehouse and cached
in-process with a TTL:

| Endpoint group            | TTL     |
|---------------------------|---------|
| `/api/mining/clusters`    | 15 min  |
| `/api/mining/prediction`  | 30 min  |
| `/api/mining/association-rules` | 30 min |
| `/api/mining/classification` | 30 min |
| `/api/insights`           | 5 min   |

Passing `?force=true` evicts the cache entry and recomputes from the database.
Reference and analytics endpoints always query the database live (no cache),
so newly loaded ETL data is immediately visible there.

---

## 6. Data-mining layer

- **Clustering** — K-Means over a per-driver feature matrix (win rate, podium
  rate, points per race, DNF rate, average finish/qualifying/lap time,
  position gain). Features are standardised; `k` is auto-selected by elbow +
  silhouette (k = 2..8) unless forced; PCA projects the 8-D space to 2-D for
  the scatter chart; results are purely computed, never hard-coded.
- **Prediction** — race-winner binary classification with Random Forest,
  Decision Tree and Logistic Regression trained **only on pre-race features**
  (grid, qualifying, prior-race expanding averages, pre-race championship
  points, prior form) to prevent leakage. Evaluation uses a time-based
  train/test split.
- **Association rules** — MLxtend Apriori over one-hot-encoded symbolic items
  derived from the warehouse (qualifying/grid buckets, constructor tier, pit
  stops, outcome, position change, reliability, pace). Rules report support /
  confidence / lift / leverage / conviction.
- **Classification** — documented composite performance score for every race
  result and driver career; E/S/A/P (Excellent/Strong/Average/Poor) labels are
  derived from thresholds, not hard-coded drivers.

See `docs/data_mining.md` for full details, formulas and parameters.

---

## 7. Frontend architecture

- **Routing** (React Router): `/` Dashboard, `/seasons`, `/drivers`,
  `/drivers/:id`, `/constructors`, `/constructors/:id`, `/circuits`,
  `/circuits/:id`, `/races`, `/races/:id`, `/olap`, `/mining`, `/insights`,
  `/about`, plus a 404 handler.
- **Data access**: `services/api.js` wraps `fetch` and points at
  `VITE_API_BASE_URL` (default `http://127.0.0.1:8000/api`). The
  `useApi` hook centralises loading / empty / error state so every page has
  consistent indicators.
- **Charts**: Recharts (line, bar, area, scatter, pie compositions) fed by
  API payloads.
- **Theme**: plain CSS with an F1 palette — black background, racing red
  accents, white/charcoal text — no UI framework, no TypeScript.

### Pages

| Route             | Purpose                                        |
|-------------------|------------------------------------------------|
| `/`               | Dashboard overview (cards + charts)            |
| `/seasons`        | Season list with race counts                   |
| `/drivers`        | Driver table with filters + sorting            |
| `/drivers/:id`    | Driver profile, career charts                  |
| `/constructors`   | Constructor table                              |
| `/constructors/:id` | Constructor profile + analytics              |
| `/circuits`       | Circuit list                                   |
| `/circuits/:id`   | Circuit profile + venue analytics              |
| `/races`          | Race list                                      |
| `/races/:id`      | Race detail (timing-screen style tables)       |
| `/olap`           | Rollup / drilldown / slice / dice / pivot UI   |
| `/mining`         | Clusters, prediction, association, classification |
| `/insights`       | Dynamically computed findings                  |
| `/about`          | Project documentation links                    |

---

## 8. Configuration & security

- All configuration flows through environment variables (`.env`), loaded by
  `backend/app/config.py` and the Vite frontend. `.env.example` documents every
  variable; **no real credentials are committed** and `.env` is git-ignored.
- CORS is restricted to the configured frontend origins (default localhost
  dev servers).
- The API is designed to be run locally / behind a reverse proxy; MySQL
  listens on 127.0.0.1.
- Data is read-only for API consumers — all mutation happens through the ETL.

---

## 9. Deployment options

1. **Local development (used in this project)** — MySQL from a dedicated local
   datadir, backend uvicorn on `127.0.0.1:8000`, Vite dev server on
   `127.0.0.1:5173`. See `docs/setup.md` and `scripts/`.
2. **Docker Compose (optional)** — `docker compose up -d` starts a MySQL 8.4
   container pre-loaded with `database/schema.sql`. The app itself is run from
   the host so Docker is only required for the database "where practical".

---

## 10. Testing & verification

- Backend pytest suite (`backend/tests/*.py`, `backend/pytest.ini`): ETL
  transforms, warehouse load/idempotency, API endpoints, analytics, OLAP and
  mining. Run with `cd backend && .venv/bin/python -m pytest`.
- Frontend production build: `cd frontend && npm run build` (clean build
  verified).
- Live smoke checks via `scripts/smoke_api.sh` and `scripts/status.sh`.

See `docs/setup.md` for runnable commands and troubleshooting.