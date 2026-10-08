# Deploying F1 INSIGHT

This guide deploys F1 INSIGHT for public access:

- **React frontend → Vercel** (static hosting, your SPA's natural home).
- **FastAPI backend → Render** (or Railway/Fly.io) — the API needs a real
  process with CPU for pandas/scikit-learn/MLxtend; it does **not** fit
  Vercel serverless (14 s default timeout, no persistent MySQL).
- **MySQL → any managed MySQL** (TiDB Cloud serverless free tier, Railway
  MySQL, Aiven free) pre-loaded from a dump of the completed warehouse.

```
┌──────────────┐   VITE_API_BASE_URL   ┌──────────────────┐  DATABASE_URL   ┌──────────────┐
│  Vercel (FE) │ ────────────────────► │  Render (FastAPI)│ ──────────────► │ Managed MySQL │
│  f1.example  │      (CORS allowed)   │  f1-api.onrender │                 │  f1_insight   │
└──────────────┘                       └──────────────────┘                 └──────────────┘
```

The ETL itself runs **once on your machine** (or on the server) and the data
is shipped as a SQL dump — re-running the Jolpica download in the cloud is
slow and rate-limited, so don't.

---

## 0. Prerequisites

- `vercel` CLI: `npm i -g vercel` then `vercel login`.
- A Render account (free) — or Railway/Fly if you prefer.
- A managed MySQL (free tiers: TiDB Cloud Serverless, Railway MySQL, Aiven).
- A **completed** warehouse: run all ETL stages first, then
  `scripts/status.sh` and confirm `TOTAL ≥ 100000` and `fact_lap ≥ 100000`.

## 1. Ship the data to the cloud MySQL

```bash
./scripts/dump_db.sh                       # → backend/logs/f1_insight_dump.sql.gz
zcat backend/logs/f1_insight_dump.sql.gz | mysql -h <HOST> -u <USER> -p f1_insight
```

Then verify in the cloud: `SELECT COUNT(*) FROM fact_lap;` (~100k+).

## 2. Deploy the backend

**Render (Blueprint):** connect the GitHub repo, choose *New → Blueprint*
(the repo's `render.yaml` is picked up automatically), then set the two
variables in the dashboard:

| Variable | Value |
|---|---|
| `DATABASE_URL` | `mysql+pymysql://USER:PASS@HOST:PORT/f1_insight` |
| `CORS_ORIGINS` | `https://<your-project>.vercel.app` |

Alternative (Railway / Fly.io): `Procfile` is included
(`uvicorn app.main:app --host 0.0.0.0 --port $PORT`); set the same two env
vars and a `web` process.

Check it: `https://<api-host>/api/health` → `"status": "ok"` and
docs at `https://<api-host>/docs`.

## 3. Deploy the frontend to Vercel

```bash
cd frontend
vercel                  # first run: link/create project, use default settings
vercel --prod
```

`frontend/vercel.json` is already configured (Vite build, SPA rewrites).

Set one env var in the Vercel project (Settings → Environment Variables)
**before the production build**, or pass it in the CLI:

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://<api-host>/api` |

> Vite bakes this in at build time — after changing it, redeploy with
> `vercel --prod`.

Verify: open the Vercel URL, join a page like `/olap` or `/insights`
(a non-root route proves the SPA rewrite works), and confirm data loads.

## 4. Environment variables summary

| Variable | Where | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | Vercel | base URL of the deployed API |
| `DATABASE_URL` | Render | `mysql+pymysql://…` to the managed DB |
| `CORS_ORIGINS` | Render | comma-separated allowed origins (Vercel URL) |
| `JOLPICA_REQUESTS_PER_SECOND` | Render | keep `2` if you ever re-run the ETL there |

## 5. Acceptance for the deployed app

- [ ] `/api/health` on the deployed API returns `database: connected`
- [ ] Dashboard loads with charts (overview endpoint 200)
- [ ] `/olap` rollup/drilldown and `/mining` clusters respond (heavier queries)
- [ ] `/insights` renders dynamic insight cards
- [ ] Direct navigation to `/drivers/1` works (SPA rewrite)

## 6. Free-tier caveats

- **Render free** services sleep after ~15 min idle; the first request after
  sleep takes 30–60 s. Keep the DB external so it never sleeps.
- **Managed MySQL free** tiers throttle connections; fine for a class demo.
- The mining/insights endpoints compute on demand (in-memory 15–30 min
  caches). Calling them once after deploy warms the caches.

## Alternative: everything on Vercel (experimental)

Vercel can serve the FastAPI app as serverless functions (`vercel.json` at the
repo root with an `api/` passthrough) plus free managed MySQL. It works for a
demo but the OLAP/mining endpoints risk the 14 s serverless timeout and the
bundle is large (pandas/sklearn/MLxtend). Prefer the split architecture above.