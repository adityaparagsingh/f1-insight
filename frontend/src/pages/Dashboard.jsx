import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { Async, DataTable, Panel, RaceLink, SectionTitle, Stat } from '../components/ui'
import { TelemetryArea, TelemetryBar } from '../charts'
import { int, num } from '../utils/format'

export default function Dashboard() {
  const overview = useApi(() => api.overview(), [])
  const insights = useApi(() => api.insights(), [])

  const counts = overview.data?.counts || {}
  const topDrivers = useMemo(
    () =>
      (overview.data?.top_drivers || []).map((d) => ({
        ...d,
        label: d.code || d.name,
      })),
    [overview.data],
  )

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">FIA Race Control · Live Warehouse</div>
          <h1>Season Command Centre</h1>
          <p className="subtitle">
            A 75+ season Formula 1 data warehouse built from the Jolpica F1 API,
            modelled as a MySQL star schema and explored through OLAP and machine
            learning.
          </p>
        </div>
        <Link className="btn primary" to="/olap">
          Open Data Lab →
        </Link>
      </div>

      <Async state={overview} label="Loading warehouse overview…">
        {() => (
          <>
            <div className="grid grid-6">
              <Stat label="Seasons" value={int(counts.seasons)} tone="red" />
              <Stat label="Grands Prix" value={int(counts.races)} />
              <Stat label="Drivers" value={int(counts.drivers)} tone="blue" />
              <Stat label="Constructors" value={int(counts.constructors)} />
              <Stat label="Circuits" value={int(counts.circuits)} tone="amber" />
              <Stat
                label="Total records"
                value={int(counts.total_records)}
                tone="green"
                foot="star-schema rows"
              />
            </div>

            <div className="grid grid-4 mt-2">
              <Stat label="Race results" value={int(counts.race_records)} />
              <Stat label="Qualifying" value={int(counts.qualifying_records)} />
              <Stat label="Lap times" value={int(counts.lap_records)} />
              <Stat label="Pit stops" value={int(counts.pit_stop_records)} />
            </div>

            <SectionTitle>Championship Timeline</SectionTitle>
            <div className="grid grid-2">
              <Panel title="Races per season" hint="calendar size by year">
                <TelemetryArea
                  data={overview.data.races_by_season || []}
                  x="season"
                  areas={[{ key: 'races', name: 'Races', color: '#e10600' }]}
                />
              </Panel>
              <Panel title="All-time win leaders" hint="top 10 by race wins">
                <TelemetryBar
                  data={topDrivers}
                  x="label"
                  bars={[{ key: 'wins', name: 'Wins', color: '#2ea8ff' }]}
                />
              </Panel>
            </div>

            <div className="grid grid-2 mt-2">
              <Panel title="Most recent Grands Prix">
                <DataTable
                  columns={[
                    {
                      key: 'race',
                      header: 'Race',
                      render: (r) => (
                        <span className="nowrap">
                          <RaceLink id={r.race_id} name={r.name} />{' '}
                          <span className="muted tiny">{r.season}</span>
                        </span>
                      ),
                    },
                    { key: 'circuit', header: 'Circuit' },
                    { key: 'winner', header: 'Winner' },
                    { key: 'winning_constructor', header: 'Team' },
                    {
                      key: 'winner_points',
                      header: 'Pts',
                      align: 'right',
                      render: (r) => num(r.winner_points, 0),
                    },
                  ]}
                  rows={overview.data.recent_races || []}
                  rowKey={(r) => r.race_id}
                  empty="No races loaded."
                />
              </Panel>

              <Panel title="Performance insights" hint="generated from live data">
                <Async state={insights} label="Generating insights…">
                  {(data) => (
                    <div className="stack">
                      {(data.items || []).slice(0, 4).map((item) => (
                        <div className="insight-card" key={item.id}>
                          <span className="insight-cat">{item.category}</span>
                          <h3>{item.title}</h3>
                          <p>{item.text}</p>
                        </div>
                      ))}
                      <Link className="btn" to="/insights">
                        View all {data.count} insights
                      </Link>
                    </div>
                  )}
                </Async>
              </Panel>
            </div>
          </>
        )}
      </Async>
    </>
  )
}
