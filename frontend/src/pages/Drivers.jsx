import { useMemo, useState } from 'react'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { Async, DataTable, DriverLink, Panel } from '../components/ui'
import { TelemetryBar } from '../charts'
import { num } from '../utils/format'

const SORTS = [
  ['points', 'Points'],
  ['wins', 'Wins'],
  ['podiums', 'Podiums'],
  ['races', 'Races'],
  ['avg_finish', 'Avg finish'],
  ['avg_grid', 'Avg grid'],
  ['dnf_rate', 'DNF rate'],
  ['position_gain', 'Position gain'],
  ['name', 'Name'],
]

export default function Drivers() {
  const [season, setSeason] = useState('')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('points')
  const [order, setOrder] = useState('desc')
  const [limit, setLimit] = useState(50)
  const [offset, setOffset] = useState(0)

  const seasons = useApi(() => api.seasons(), [])
  const query = useApi(
    () =>
      api.drivers({
        season: season || undefined,
        search: search || undefined,
        sort,
        order,
        limit,
        offset,
      }),
    [season, search, sort, order, limit, offset],
  )

  const items = query.data?.items || []
  const total = query.data?.total || 0
  const topChart = useMemo(
    () =>
      [...items]
        .filter((d) => Number(d.points) > 0)
        .sort((a, b) => Number(b.points) - Number(a.points))
        .slice(0, 12)
        .map((d) => ({ label: d.code || d.name, points: Number(d.points) })),
    [items],
  )

  const seasonOptions = seasons.data || []

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Dimension · dim_driver</div>
          <h1>Driver Database</h1>
          <p className="subtitle">
            Career aggregates computed from every classified race result —
            sorting, filtering and drill-through to full driver profiles.
          </p>
        </div>
      </div>

      <div className="toolbar">
        <div className="field">
          <label>Season</label>
          <select className="control" value={season} onChange={(e) => { setSeason(e.target.value); setOffset(0) }}>
            <option value="">All eras</option>
            {seasonOptions.slice().reverse().map((s) => (
              <option key={s.season} value={s.season}>
                {s.season}
              </option>
            ))}
          </select>
        </div>
        <div className="field" style={{ flex: 1, minWidth: 180 }}>
          <label>Search</label>
          <input
            className="control full"
            placeholder="Name, code or ref"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setOffset(0) }}
          />
        </div>
        <div className="field">
          <label>Sort by</label>
          <select className="control" value={sort} onChange={(e) => setSort(e.target.value)}>
            {SORTS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Order</label>
          <select className="control" value={order} onChange={(e) => setOrder(e.target.value)}>
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>
        <div className="field">
          <label>Page size</label>
          <select className="control" value={limit} onChange={(e) => { setLimit(Number(e.target.value)); setOffset(0) }}>
            {[25, 50, 100, 200].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
      </div>

      <Async state={query} label="Loading drivers…">
        {() => (
          <>
            {topChart.length > 0 && (
              <Panel title="Points leaders in selection" className="mt-2">
                <TelemetryBar
                  data={topChart}
                  x="label"
                  bars={[{ key: 'points', name: 'Points', color: '#e10600' }]}
                  height={280}
                />
              </Panel>
            )}

            <Panel title={`${total.toLocaleString()} drivers`} className="mt-2" hint={`rows ${offset + 1}–${offset + items.length}`}>
              <DataTable
                columns={[
                  {
                    key: 'name',
                    header: 'Driver',
                    render: (d) => <DriverLink id={d.driver_id} name={d.name} code={d.code} />,
                  },
                  { key: 'nationality', header: 'Nationality' },
                  { key: 'races', header: 'Races', align: 'right' },
                  { key: 'wins', header: 'Wins', align: 'right' },
                  { key: 'podiums', header: 'Podiums', align: 'right' },
                  { key: 'points', header: 'Points', align: 'right', render: (d) => num(d.points, 1) },
                  { key: 'avg_finish', header: 'Avg finish', align: 'right', render: (d) => num(d.avg_finish, 2) },
                  { key: 'win_rate', header: 'Win %', align: 'right', render: (d) => num(Number(d.win_rate) * 100, 1) },
                  { key: 'teams', header: 'Teams' },
                ]}
                rows={items}
                rowKey={(d) => d.driver_id}
                empty="No drivers match the filters."
              />

              <div className="row spread mt-2">
                <button
                  className="btn"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                >
                  ← Previous
                </button>
                <span className="muted tiny">
                  {offset + 1}–{Math.min(offset + items.length, total)} of {total.toLocaleString()}
                </span>
                <button
                  className="btn"
                  disabled={offset + limit >= total}
                  onClick={() => setOffset(offset + limit)}
                >
                  Next →
                </button>
              </div>
            </Panel>
          </>
        )}
      </Async>
    </>
  )
}
