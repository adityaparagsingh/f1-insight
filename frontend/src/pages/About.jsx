import { Link } from 'react-router-dom'
import { Panel, SectionTitle } from '../components/ui'

const ENDPOINTS = [
  ['GET /api/health', 'Service + warehouse row counts'],
  ['GET /api/seasons', 'All seasons with race counts'],
  ['GET /api/races · /api/races/{id}', 'Paginated race list + timing-screen detail'],
  ['GET /api/drivers · /api/drivers/{id}', 'Driver database + career profile'],
  ['GET /api/constructors · /{id}', 'Team database + profile'],
  ['GET /api/circuits · /api/circuits/{id}', 'Circuit database + profile'],
  ['GET /api/analytics/overview', 'Dashboard aggregates'],
  ['GET /api/analytics/drivers', 'Driver aggregates + sorting'],
  ['GET /api/analytics/drivers/compare', 'Side-by-side driver comparison'],
  ['GET /api/analytics/constructors', 'Team aggregates'],
  ['GET /api/analytics/circuits', 'Circuit aggregates'],
  ['GET /api/analytics/races', 'Race results overview'],
  ['GET /api/analytics/races/position-changes', 'Biggest gains / losses'],
  ['GET /api/analytics/qualifying', 'Qualifying analytics'],
  ['GET /api/analytics/pit-stops', 'Pit-stop analytics'],
  ['GET /api/olap/rollup', 'Aggregate up a hierarchy'],
  ['GET /api/olap/drilldown', 'Season → race → driver → lap'],
  ['GET /api/olap/slice', 'Filter the cube on one dimension'],
  ['GET /api/olap/dice', 'Filter on multiple dimensions'],
  ['GET /api/olap/pivot', 'Cross-tabulate two dimensions'],
  ['GET /api/mining/clusters', 'K-Means driver clustering'],
  ['GET /api/mining/prediction', 'Race-winner prediction'],
  ['GET /api/mining/association-rules', 'Apriori rule mining'],
  ['GET /api/mining/classification', 'Composite performance classes'],
  ['GET /api/insights', 'Dynamically computed findings'],
]

const STACK = [
  ['Frontend', 'React 18 · Vite · React Router · Recharts · plain CSS'],
  ['Backend', 'Python 3 · FastAPI · Pydantic · SQLAlchemy'],
  ['Data science', 'Pandas · NumPy · scikit-learn · MLxtend'],
  ['Warehouse', 'MySQL 8 star schema (5 dimensions, 6 fact tables)'],
  ['Source', 'Jolpica F1 API (Ergast-compatible)'],
]

export default function About() {
  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Project documentation</div>
          <h1>About F1 INSIGHT</h1>
          <p className="subtitle">
            A complete Formula 1 performance-analytics and data-mining platform:
            a real-data ETL pipeline into a MySQL star schema, exposed through a
            FastAPI service and an F1 race-control styled React application.
          </p>
        </div>
      </div>

      <div className="grid grid-2">
        <Panel title="What it does">
          <p className="dim">
            F1 INSIGHT ingests the complete Formula 1 historical record — races,
            results, qualifying, pit stops, lap times and championship standings —
            from the Jolpica F1 API, models it as a dimensional warehouse, and
            makes it explorable through three layers:
          </p>
          <div className="stack mt-1">
            <div className="insight-card">
              <span className="insight-cat">OLAP</span>
              <h3>Multidimensional analysis</h3>
              <p>Roll-up, drill-down, slice, dice and pivot operations over the cube.</p>
            </div>
            <div className="insight-card">
              <span className="insight-cat">Data Mining</span>
              <h3>Machine learning</h3>
              <p>K-Means clustering, race-winner prediction and Apriori association rules.</p>
            </div>
            <div className="insight-card">
              <span className="insight-cat">Insights</span>
              <h3>Automatic findings</h3>
              <p>Correlations, extremes and trends computed live — never hard-coded.</p>
            </div>
          </div>
        </Panel>

        <Panel title="Technology stack">
          <div className="stack">
            {STACK.map(([k, v]) => (
              <div key={k} className="row spread">
                <strong>{k}</strong>
                <span className="dim tiny" style={{ textAlign: 'right' }}>{v}</span>
              </div>
            ))}
          </div>
          <SectionTitle>Star schema</SectionTitle>
          <p className="tiny muted">
            Dimensions: <span className="mono">dim_date</span>,{' '}
            <span className="mono">dim_driver</span>,{' '}
            <span className="mono">dim_constructor</span>,{' '}
            <span className="mono">dim_circuit</span>,{' '}
            <span className="mono">dim_race</span>.
          </p>
          <p className="tiny muted mt-1">
            Facts: <span className="mono">fact_race_result</span>,{' '}
            <span className="mono">fact_qualifying</span>,{' '}
            <span className="mono">fact_lap</span>,{' '}
            <span className="mono">fact_pit_stop</span>,{' '}
            <span className="mono">fact_driver_standing</span>,{' '}
            <span className="mono">fact_constructor_standing</span>.
          </p>
        </Panel>
      </div>

      <Panel title="Pipeline" className="mt-2">
        <pre className="mono tiny" style={{ margin: 0, whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
{`Jolpica F1 API
      │  extract (paged, cached, rate-limited, retried)
      ▼
 Python ETL  ──  clean · validate · derive (position_gain = grid − position)
      │  load (idempotent upserts)
      ▼
 MySQL star schema  ──  5 dimensions · 6 fact tables
      │
      ├─► FastAPI analytics + OLAP + mining + insights
      │
      └─► React / Vite F1 race-control UI`}
        </pre>
      </Panel>

      <Panel title="API surface" hint="interactive docs at /docs" className="mt-2">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr><th>Endpoint</th><th>Description</th></tr>
            </thead>
            <tbody>
              {ENDPOINTS.map(([ep, desc]) => (
                <tr key={ep}>
                  <td className="mono tiny nowrap">{ep}</td>
                  <td className="dim tiny">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid grid-2 mt-2">
        <Panel title="Data provenance">
          <p className="dim">
            All statistics in this application are computed directly from the
            warehouse, which is loaded from the public Jolpica F1 API. No value is
            fabricated or hard-coded; aggregates change as new ETL runs add data.
          </p>
          <p className="tiny muted mt-1">
            Jolpica is a community-run, open, Ergast-compatible mirror of Formula 1
            timing and results data.
          </p>
        </Panel>
        <Panel title="Run the project locally">
          <pre className="mono tiny" style={{ margin: 0, whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
{`# backend
cd backend
.venv/bin/python -m etl.run --all
.venv/bin/uvicorn app.main:app --port 8000

# frontend
cd frontend
npm install && npm run dev`}
          </pre>
          <div className="row mt-1">
            <Link className="btn" to="/olap">Open Data Lab</Link>
            <Link className="btn" to="/mining">Open Data Mining</Link>
          </div>
        </Panel>
      </div>
    </>
  )
}
