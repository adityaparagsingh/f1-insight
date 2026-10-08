import { useState } from 'react'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { Async, CircuitLink, DataTable, Panel } from '../components/ui'
import { num } from '../utils/format'

export default function Circuits() {
  const [search, setSearch] = useState('')
  const [country, setCountry] = useState('')

  const query = useApi(
    () => api.circuits({ search: search || undefined, limit: 200 }),
    [search],
  )
  const items = query.data?.items || []
  const countries = Array.from(new Set(items.map((c) => c.country).filter(Boolean))).sort()
  const filtered = country ? items.filter((c) => c.country === country) : items

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Dimension · dim_circuit</div>
          <h1>Circuit Directory</h1>
          <p className="subtitle">
            Every venue that has hosted a world championship Grand Prix, with
            races, active years and location.
          </p>
        </div>
      </div>

      <div className="toolbar">
        <div className="field" style={{ flex: 1, minWidth: 200 }}>
          <label>Search</label>
          <input
            className="control full"
            placeholder="Circuit or location"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="field">
          <label>Country</label>
          <select className="control" value={country} onChange={(e) => setCountry(e.target.value)}>
            <option value="">All countries</option>
            {countries.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      <Async state={query} label="Loading circuits…">
        {() => (
          <Panel title={`${filtered.length} circuits`} className="mt-2">
            <DataTable
              columns={[
                {
                  key: 'name',
                  header: 'Circuit',
                  render: (c) => <CircuitLink id={c.circuit_id} name={c.name} />,
                },
                { key: 'location', header: 'Location' },
                { key: 'country', header: 'Country' },
                { key: 'races', header: 'Races', align: 'right' },
                {
                  key: 'coords',
                  header: 'Coordinates',
                  render: (c) =>
                    c.latitude && c.longitude ? (
                      <span className="mono tiny">
                        {num(c.latitude, 3)}, {num(c.longitude, 3)}
                      </span>
                    ) : (
                      '—'
                    ),
                },
                { key: 'first_race', header: 'First GP' },
                { key: 'last_race', header: 'Last GP' },
              ]}
              rows={filtered}
              rowKey={(c) => c.circuit_id}
              empty="No circuits match the filters."
            />
          </Panel>
        )}
      </Async>
    </>
  )
}
