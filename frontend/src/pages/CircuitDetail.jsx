import { useParams } from 'react-router-dom'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { Async, DataTable, DriverLink, Panel, SectionTitle, Stat } from '../components/ui'
import { TelemetryBar } from '../charts'
import { int, num, secondsFromMs } from '../utils/format'

export default function CircuitDetail() {
  const { id } = useParams()
  const query = useApi(() => api.circuit(id), [id])

  return (
    <Async state={query} label="Loading circuit profile…">
      {(data) => {
        const { profile, summary, top_drivers, top_constructors, lap_stats, pit_stats, winners, fastest_pit_stops } = data
        const recentWinners = (winners || []).slice(0, 40)
        return (
          <>
            <div className="profile-head">
              <div className="avatar">🏁</div>
              <div className="profile-meta">
                <div className="eyebrow">Circuit Profile</div>
                <h2>{profile.name}</h2>
                <div className="meta-row">
                  <span>{profile.location || '—'}</span>
                  <span>{profile.country || '—'}</span>
                  {profile.latitude && (
                    <span className="mono tiny">
                      {num(profile.latitude, 4)}, {num(profile.longitude, 4)}
                    </span>
                  )}
                  {profile.url && (
                    <a href={profile.url} target="_blank" rel="noreferrer" className="rowlink">
                      Wiki ↗
                    </a>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-6 mt-2">
              <Stat label="Grands Prix" value={int(summary.races)} tone="red" />
              <Stat label="Entries" value={int(summary.race_results)} />
              <Stat label="DNF rate" value={num(summary.dnf_rate, 1)} tone="amber" />
              <Stat label="Poles here" value={int(summary.poles)} tone="blue" />
              <Stat
                label="Fastest lap"
                value={secondsFromMs(lap_stats?.fastest_lap_ms)}
                tone="green"
                foot={`${int(lap_stats?.lap_records)} lap records`}
              />
              <Stat
                label="Avg pit stop"
                value={pit_stats?.avg_duration ? `${num(pit_stats.avg_duration, 2)}s` : '—'}
                foot={`${int(pit_stats?.pit_stops)} stops`}
              />
            </div>

            <SectionTitle>Circuit leaders</SectionTitle>
            <div className="grid grid-2">
              <Panel title="Most successful drivers here">
                <TelemetryBar
                  data={(top_drivers || []).slice(0, 10).map((d) => ({
                    label: d.code || d.name,
                    wins: Number(d.wins),
                  }))}
                  x="label"
                  layout="vertical"
                  bars={[{ key: 'wins', name: 'Wins', color: '#e10600' }]}
                  height={340}
                />
                <DataTable
                  columns={[
                    {
                      key: 'name',
                      header: 'Driver',
                      render: (d) => <DriverLink id={d.driver_id} name={d.name} code={d.code} />,
                    },
                    { key: 'entries', header: 'Starts', align: 'right' },
                    { key: 'wins', header: 'Wins', align: 'right' },
                    { key: 'podiums', header: 'Podiums', align: 'right' },
                    { key: 'avg_finish', header: 'Avg fin', align: 'right', render: (d) => num(d.avg_finish, 2) },
                  ]}
                  rows={top_drivers || []}
                  rowKey={(d) => d.driver_id}
                />
              </Panel>
              <Panel title="Most successful teams here">
                <TelemetryBar
                  data={(top_constructors || []).slice(0, 10).map((c) => ({
                    label: c.name,
                    wins: Number(c.wins),
                  }))}
                  x="label"
                  layout="vertical"
                  bars={[{ key: 'wins', name: 'Wins', color: '#2ea8ff' }]}
                  height={340}
                />
                <DataTable
                  columns={[
                    { key: 'name', header: 'Constructor' },
                    { key: 'entries', header: 'Starts', align: 'right' },
                    { key: 'wins', header: 'Wins', align: 'right' },
                    { key: 'podiums', header: 'Podiums', align: 'right' },
                    { key: 'avg_finish', header: 'Avg fin', align: 'right', render: (c) => num(c.avg_finish, 2) },
                  ]}
                  rows={top_constructors || []}
                  rowKey={(c) => c.constructor_id}
                />
              </Panel>
            </div>

            <SectionTitle>Roll of honour</SectionTitle>
            <div className="grid grid-2">
              <Panel title="Winners by season" hint="most recent 40">
                <DataTable
                  columns={[
                    { key: 'season', header: 'Season' },
                    { key: 'name', header: 'Grand Prix' },
                    { key: 'date', header: 'Date' },
                    { key: 'winner', header: 'Winner' },
                    { key: 'constructor', header: 'Team' },
                  ]}
                  rows={recentWinners}
                  rowKey={(r) => r.race_id}
                />
              </Panel>
              <Panel title="Fastest pit stops recorded here">
                <DataTable
                  columns={[
                    { key: 'duration', header: 'Time', align: 'right', render: (r) => `${num(r.duration, 3)}s` },
                    { key: 'driver', header: 'Driver' },
                    { key: 'constructor', header: 'Team' },
                    { key: 'lap', header: 'Lap', align: 'right' },
                    { key: 'season', header: 'Season', align: 'right' },
                  ]}
                  rows={fastest_pit_stops || []}
                  rowKey={(r, i) => `${r.season}-${r.driver}-${i}`}
                  empty="No pit-stop data for this circuit."
                />
              </Panel>
            </div>
          </>
        )
      }}
    </Async>
  )
}
