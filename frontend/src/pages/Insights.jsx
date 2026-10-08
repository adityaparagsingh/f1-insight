import { useMemo, useState } from 'react'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { Async, EmptyState, Panel, Stat } from '../components/ui'
import { int, num, titleCase } from '../utils/format'

// ---------------------------------------------------------------------------
// Insights — dynamically generated findings computed from the live warehouse.
// ---------------------------------------------------------------------------

export default function Insights() {
  const query = useApi(() => api.insights(), [])
  const [filter, setFilter] = useState('')

  const items = query.data?.items || []
  const categories = useMemo(
    () => Array.from(new Set(items.map((i) => i.category))),
    [items],
  )
  const visible = filter ? items.filter((i) => i.category === filter) : items

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">computed at request time</div>
          <h1>Performance Insights</h1>
          <p className="subtitle">
            Every statement below is derived from the loaded warehouse with live
            SQL and statistics — nothing is hard-coded. Refresh the page after new
            ETL runs to see the numbers move.
          </p>
        </div>
      </div>

      <Async state={query} label="Generating insights from the warehouse…">
        {(data) => (
          <>
            <div className="grid grid-4">
              <Stat label="Insights generated" value={int(data.count)} tone="red" />
              <Stat label="Categories" value={int(categories.length)} tone="blue" />
              <Stat label="Data source" value="Live SQL" tone="green" foot="no static values" />
              <Stat label="Cache TTL" value="5 min" tone="amber" foot="then recomputed" />
            </div>

            <div className="row mt-2" style={{ flexWrap: 'wrap', gap: '0.4rem' }}>
              <button
                type="button"
                className={`btn ${filter === '' ? 'primary' : ''}`}
                onClick={() => setFilter('')}
              >
                All ({items.length})
              </button>
              {categories.map((c) => (
                <button
                  key={c}
                  type="button"
                  className={`btn ${filter === c ? 'primary' : ''}`}
                  onClick={() => setFilter(c)}
                >
                  {titleCase(c)} ({items.filter((i) => i.category === c).length})
                </button>
              ))}
            </div>

            {visible.length === 0 ? (
              <EmptyState message="No insights for this category yet — run the ETL to load more data." />
            ) : (
              <div className="grid grid-2 mt-2">
                {visible.map((item) => (
                  <article className="insight-card" key={item.id}>
                    <span className="insight-cat">{item.category}</span>
                    <h3>{item.title}</h3>
                    <p>{item.text}</p>
                    {item.value !== null && item.value !== undefined && (
                      <div className="metric-pill">
                        <span className="metric-value">
                          {typeof item.value === 'number' ? num(item.value, Math.abs(item.value) < 10 ? 3 : 1) : item.value}
                        </span>
                        {item.unit && <span className="metric-unit">{item.unit}</span>}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </>
        )}
      </Async>

      <Panel title="How insights are produced" className="mt-2" accent={false}>
        <p className="tiny muted">
          The insight engine runs aggregations, window queries and Pearson
          correlations directly on the star schema (fact_race_result,
          fact_qualifying, fact_pit_stop, fact_lap, dim_*). Results are cached for
          five minutes per process; pass <code>?force=true</code> to the API to
          recompute immediately.
        </p>
      </Panel>
    </>
  )
}
