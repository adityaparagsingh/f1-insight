# Notebooks

Exploratory notebooks for the F1 INSIGHT warehouse, OLAP cube, data-mining
tasks and insight engine. Every cell runs against the real MySQL warehouse —
validate it first with `python -m etl.run --all` from `backend/` (see
`docs/setup.md`).

## Notebooks

1. `01_etl_exploration.ipynb` — warehouse row counts, star-schema tour,
   `etl_run_log` audit, derived `position_gain` metric, race volume per decade.
2. `02_olap_analysis.ipynb` — ROLL-UP, DRILL-DOWN, SLICE, DICE and PIVOT with
   the same SQL the `/api/olap/*` endpoints compile.
3. `03_data_mining.ipynb` — K-Means clustering (auto-k), pre-race winner
   prediction, Apriori association rules and E/S/A/P classification via the
   `app.mining` services.
4. `04_insights.ipynb` — the dynamic insight engine (`app.services.insights`),
   including charts and CSV export.

## Running

```bash
cd backend
source .venv/bin/activate
jupyter notebook ../notebooks        # or: jupyter lab
```

Notebooks are also runnable from the repo root: each starts by inserting
`s/backend` onto `sys.path` so `app.*` imports resolve. They require the
backend dependencies (`pip install -r backend/requirements.txt`) and the
`f1_insight` database to be populated.