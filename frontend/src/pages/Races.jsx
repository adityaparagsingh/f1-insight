import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { Async, DataTable, Panel, RaceLink } from '../components/ui'
import { num } from '../utils/format'

export default function Races() {
  const [params, setParams] = useSearchParams()
  const season = params.get('season') || ''
  const [search, setSearch] = useState('')
  const [limit] = useState(50)
  const [offset, setOffset] = useState(0)

  const seasons = useApi(() => api.seasons(), [])
  const query = useApi(
    () =>
      api.races({
        season: season || undefined,
        search: search || undefined,
        limit,
        offset,
      }),
    [season, search, offset, limit],
  )

  const items = query.data?.items || []
  const total = query.data?.total || 0

  const setSeason = (value) => {
    const next = new URLSearchParams(params)
    if (value) next.set('season', value)
    else next.delete('season')
    setParams(next)
    setOffset(0)
  }

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Fact · fact_race_result</div>
          <h1>Grand Prix Index</h1>
          <p className="subtitle">
            Every race in the warehouse with its winner, venue and field size.
            Open a race for the full timing-screen breakdown.
          </p>
        </div>
      </div>

      <div className="toolbar">
        <div className="field">
          <label>Season</label>
          <select className="control" value={season} onChange={(e) => setSeason(e.target.value)}>
            <option value="">All seasons</option>
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
            placeholder="Grand Prix or circuit"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setOffset(0)
            }}
          />
        </div>
      </div>

      <Async state={query} label="Loading races…">
        {() => (
          <Panel title={`${total.toLocaleString()} races`} className="mt-2">
            <DataTable
              columns={[
                { key: 'season', header: 'Season', align: 'right' },
                { key: 'round', header: 'R', align: 'right' },
                {
                  key: 'name',
                  header: 'Grand Prix',
                  render: (r) => <RaceLink id={r.race_id} name={r.name} />,
                },
                { key: 'date', header: 'Date' },
                { key: 'circuit', header: 'Circuit' },
                { key: 'country', header: 'Country' },
                { key: 'winner', header: 'Winner' },
                { key: 'winning_constructor', header: 'Team' },
                { key: 'entries', header: 'Field', align: 'right', render: (r) => num(r.entries, 0) },
              ]}
              rows={items}
              rowKey={(r) => r.race_id}
              empty="No races match the filters."
            />
            <div className="row spread mt-2">
              <button className="btn" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
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
        )}
      </Async>
    </>
  )
}
