import { useState } from 'react'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { Async, ConstructorLink, DataTable, Panel } from '../components/ui'
import { TelemetryBar } from '../charts'
import { num, pct } from '../utils/format'

export default function Constructors() {
  const [season, setSeason] = useState('')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('points')
  const [order, setOrder] = useState('desc')

  const seasons = useApi(() => api.seasons(), [])
  const query = useApi(
    () =>
      api.constructors({
        season: season || undefined,
        search: search || undefined,
        sort,
        order,
        limit: 100,
      }),
    [season, search, sort, order],
  )

  const items = query.data?.items || []
  const topChart = items
    .slice(0, 12)
    .map((c) => ({ label: c.name, points: Number(c.points), wins: Number(c.wins) }))

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Dimension · dim_constructor</div>
          <h1>Constructor Database</h1>
          <p className="subtitle">
            Team-level aggregates across every era of the championship, with
            drill-through to season histories and driver contributions.
          </p>
        </div>
      </div>

      <div className="toolbar">
        <div className="field">
          <label>Season</label>
          <select className="control" value={season} onChange={(e) => setSeason(e.target.value)}>
            <option value="">All eras</option>
            {(seasons.data || []).slice().reverse().map((s) => (
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
            placeholder="Team name"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="field">
          <label>Sort by</label>
          <select className="control" value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="points">Points</option>
            <option value="wins">Wins</option>
            <option value="podiums">Podiums</option>
            <option value="races">Races</option>
            <option value="avg_finish">Avg finish</option>
            <option value="dnf_rate">DNF rate</option>
            <option value="name">Name</option>
          </select>
        </div>
        <div className="field">
          <label>Order</label>
          <select className="control" value={order} onChange={(e) => setOrder(e.target.value)}>
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>
      </div>

      <Async state={query} label="Loading constructors…">
        {() => (
          <>
            <Panel title="Points & wins in selection" className="mt-2">
              <TelemetryBar
                data={topChart}
                x="label"
                bars={[
                  { key: 'points', name: 'Points', color: '#e10600' },
                  { key: 'wins', name: 'Wins', color: '#2ea8ff' },
                ]}
                height={300}
              />
            </Panel>

            <Panel title={`${(query.data.total || 0).toLocaleString()} constructors`} className="mt-2">
              <DataTable
                columns={[
                  {
                    key: 'name',
                    header: 'Constructor',
                    render: (c) => <ConstructorLink id={c.constructor_id} name={c.name} />,
                  },
                  { key: 'nationality', header: 'Nationality' },
                  { key: 'races', header: 'Entries', align: 'right' },
                  { key: 'wins', header: 'Wins', align: 'right' },
                  { key: 'podiums', header: 'Podiums', align: 'right' },
                  { key: 'points', header: 'Points', align: 'right', render: (c) => num(c.points, 1) },
                  { key: 'avg_finish', header: 'Avg finish', align: 'right', render: (c) => num(c.avg_finish, 2) },
                  { key: 'dnf_rate', header: 'DNF %', align: 'right', render: (c) => pct(c.dnf_rate) },
                  { key: 'first_season', header: 'From', align: 'right' },
                  { key: 'last_season', header: 'To', align: 'right' },
                ]}
                rows={items}
                rowKey={(c) => c.constructor_id}
                empty="No constructors match the filters."
              />
            </Panel>
          </>
        )}
      </Async>
    </>
  )
}
