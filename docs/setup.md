# F1 INSIGHT — Setup & Run Guide

Step-by-step instructions to install dependencies, initialise the MySQL
warehouse, run the ETL, start the API and the frontend, and verify the whole
system. Companion scripts live in `scripts/`.

---

## 1. Prerequisites

| Tool       | Version      | Notes                                  |
|------------|--------------|----------------------------------------|
| Python     | 3.9+         | 3.11/3.12 recommended                  |
| Node.js    | 18+          | with npm                               |
| MySQL      | 8.0+         | or Docker (see below)                  |
| git        | any          |                                        |

Verify:

```bash
python --version
node --version
npm --version
mysql --version        # or: docker --version
```

---

## 2. Clone & configure

```bash
git clone <repo-url> f1-insight
cd f1-insight

cp .env.example .env                 # backend/env config (project root)
cp frontend/.env.example frontend/.env
```

Edit `.env` if your MySQL credentials differ. The defaults are:

```
DATABASE_URL=mysql+pymysql://f1user:f1pass@127.0.0.1:3306/f1_insight
JOLPICA_BASE_URL=https://api.jolpi.ca/ergast/f1
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

`.env` and `frontend/.env` are git-ignored; **never commit real
credentials** — use `.env.example` as the template.

---

## 3. MySQL — choose one option

### Option A — Docker Compose (recommended when Docker is available)

```bash
docker compose up -d
```

Starts MySQL 8.4 on `127.0.0.1:3306`, creates database `f1_insight` with user
`f1user` / password `f1pass`, and applies `database/schema.sql` automatically
on first boot.

### Option B — local MySQL (no Docker)

Create the database and user, then apply the schema:

```bash
mysql -u root -p -e "
  CREATE DATABASE IF NOT EXISTS f1_insight CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  CREATE USER IF NOT EXISTS 'f1user'@'127.0.0.1' IDENTIFIED BY 'f1pass';
  GRANT ALL PRIVILEGES ON f1_insight.* TO 'f1user'@'127.0.0.1';
  FLUSH PRIVILEGES;
"
mysql -u f1user -pf1pass f1_insight < database/schema.sql
```

If you already have a MySQL server on 3306 you can typically stop it and start
a dedicated instance for this project from an isolated datadir, e.g.:

```bash
mkdir -p /opt/homebrew/var/mysql-f1
mysqld --datadir=/opt/homebrew/var/mysql-f1 --port=3306 \
       --bind-address=127.0.0.1 --socket=/tmp/mysql.sock &
```

> On macOS (Homebrew MySQL) without a password for `root`, omit `-p` above.
> The `scripts/status.sh` helper reports whether MySQL, the API and the
> frontend are reachable.

---

## 4. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The schema can be applied either from `database/schema.sql` (above) or via
Alembic:

```bash
alembic upgrade head
```

Both are idempotent (`CREATE TABLE IF NOT EXISTS`).

---

## 5. Run the ETL (load real F1 data)

Always run from `backend/` with the venv active. The pipeline extracts real
historical data from the Jolpica F1 API, transforms, cleans, and **upserts**
into the star schema, so re-runs never duplicate rows.

```bash
# Full historical warehouse (1950 → current; reference, results, qualifying,
# pit stops ≥ 2011, standings ≥ 1980, laps ≥ 2015). Can take 10–40 minutes.
python -m etl.run --all

# One season end-to-end (faster check)
python -m etl.run --season 2024

# Incremental update of the latest season
python -m etl.run --update

# Subset of stages / tuning
python -m etl.run --all --stage reference,results
python -m etl.run --all --rps 2 --retries 8    # gentler on the public API
python -m etl.run --all --skip-laps
```

CLI reference:

| Flag                 | Meaning                                             |
|----------------------|-----------------------------------------------------|
| `--season YYYY`      | load one season end-to-end                          |
| `--all`              | full historical load                                |
| `--update`           | incremental (default)                               |
| `--stage a,b,c`      | limit to stages: `reference,results,qualifying,pitstops,standings,laps` |
| `--lap-start` / `--pit-start` / `--standings-since` | earliest seasons for the big stages |
| `--skip-laps` / `--skip-pitstops` / `--skip-standings` | skip stages        |
| `--no-cache` / `--refresh-cache` | disable / bypass the raw-response disk cache |
| `--rps N` / `--retries N` | API throttle (default 8 rps, 5 retries)      |
| `--json`             | print the summary as JSON                            |

Raw API responses are cached under `backend/etl/cache/`; logs under
`backend/logs/`. Each run appends a row to `etl_run_log` with extract /
transform / load quality counters (visible on `/api/health`).

**Verification:**

```bash
mysql -uf1user -pf1pass f1_insight -e "
  SELECT 'fact_race_result' t, COUNT(*) c FROM fact_race_result
  UNION ALL SELECT 'fact_qualifying', COUNT(*) FROM fact_qualifying
  UNION ALL SELECT 'fact_pit_stop',   COUNT(*) FROM fact_pit_stop
  UNION ALL SELECT 'fact_lap',        COUNT(*) FROM fact_lap
  UNION ALL SELECT 'fact_driver_standing',     COUNT(*) FROM fact_driver_standing
  UNION ALL SELECT 'fact_constructor_standing',COUNT(*) FROM fact_constructor_standing;"
```

The warehouse should contain **100,000+ rows** (the 2015+ `fact_lap` stage
provides most of the volume) — well above the 10,000-record requirement.

---

## 6. Start the API

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- API root: <http://127.0.0.1:8000/> (service banner)
- Health: <http://127.0.0.1:8000/api/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

---

## 7. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>.

The frontend reads `VITE_API_BASE_URL` from `frontend/.env` (default
`http://127.0.0.1:8000/api`). For production:

```bash
npm run build        # outputs to frontend/dist (clean build expected)
npm run preview
```

---

## 8. Run the tests

```bash
cd backend
.venv/bin/python -m pytest            # 53 tests: ETL, DB, API, analytics, OLAP, mining
```

Database-dependent tests auto-skip when MySQL is not reachable. Use
`pytest -k <keyword>` to run a subset.

---

## 9. Verification checklist (all 19 phases)

| Check | Command |
|-------|---------|
| MySQL running | `mysql -uf1user -pf1pass f1_insight -e "SELECT 1;"` |
| Warehouse loaded | row-count query in section 5 |
| ETL idempotent | re-run a stage/season, confirm counts unchanged |
| API healthy | `curl -s http://127.0.0.1:8000/api/health` |
| OpenAPI present | `curl -s http://127.0.0.1:8000/openapi.json`, or browse `/docs` |
| Insights/mining current | `curl -s "http://127.0.0.1:8000/api/insights?force=true"` and the four `/api/mining/*` endpoints |
| Frontend builds | `cd frontend && npm run build` |
| Tests green | `cd backend && .venv/bin/python -m pytest` |

`scripts/smoke_api.sh` curls a representative set of endpoints and
`scripts/status.sh` reports the state of MySQL / API / frontend.

---

## 10. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `pymysql.err.OperationalError: Access denied` | credentials mismatch — check `.env` against the user you created |
| ETL slow / HTTP 429 storms | the public Jolpica API throttles; lower `--rps` and raise `--retries` (e.g. `--rps 2 --retries 8`); cached responses make re-runs fast |
| `fact_lap` stays empty | laps stage only extracts from `--lap-start` (default 2015); confirm the stage ran (`--stage laps`) and the log shows no errors |
| API up but frontend shows 500s | CORS — `CORS_ORIGINS` must include the frontend origin (default dev origins are pre-configured) |
| Tests skip | MySQL down — start it (section 3) and re-run pytest |
| Ports busy | `API_PORT` / Vite port configurable; `lsof -i :8000` to inspect |
| Mining results stale after ETL | call the endpoints with `?force=true` once to rebuild the in-memory caches |
| Alembic vs schema drift | `database/schema.sql` is the source of truth; apply it directly if needed (`mysql ... < database/schema.sql`) — it is idempotent |