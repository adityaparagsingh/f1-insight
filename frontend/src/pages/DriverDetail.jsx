import { useParams } from 'react-router-dom'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { Async, DataTable, Panel, SectionTitle, Stat } from '../components/ui'
import { ScatterPlot, TelemetryBar, TelemetryLine } from '../charts'
import { int, num, pct, signed } from '../utils/format'

export default function DriverDetail() {
  const { id } = useParams()
  const query = useApi(() => api.driver(id), [id])

  return (
    <Async state={query} label="Loading driver profile…">
      {(data) => {
        const { profile, career, seasons, quali_vs_finish, recent_results, wins_by_circuit } = data
        const initials = (profile.code || profile.surname || 'F1').slice(0, 3)
        const seasonSeries = (seasons || []).map((s) => ({
          season: s.season,
          points: Number(s.points),
          wins: Number(s.wins),
          finish: Number(s.avg_finish),
        }))
        const scatter = (quali_vs_finish || [])
          .filter((r) => r.quali_pos && r.finish_pos)
          .map((r) => ({ x: r.quali_pos, y: r.finish_pos, quali: r.quali_pos, finish: r.finish_pos }))

        return (
          <>
            <div className="profile-head">
              <div className="avatar">{initials}</div>
              <div className="profile-meta">
                <div className="eyebrow">Driver Profile</div>
                <h2>
                  {profile.name}
                  {profile.number ? <span className="mono muted"> · {profile.number}</span> : null}
                </h2>
                <div className="meta-row">
                  <span>{profile.nationality || '—'}</span>
                  <span>Born {profile.date_of_birth || '—'}</span>
                  <span className="mono">
                    {career.first_season}–{career.last_season}
                  </span>
                  {profile.url && (
                    <a href={profile.url} target="_blank" rel="noreferrer" className="rowlink">
                      Wiki ↗
                    </a>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-6 mt-2">
              <Stat label="Starts" value={int(career.races)} />
              <Stat label="Wins" value={int(career.wins)} tone="red" />
              <Stat label="Podiums" value={int(career.podiums)} tone="amber" />
              <Stat label="Poles" value={int(career.poles)} tone="blue" />
              <Stat label="Points" value={num(career.points, 1)} tone="green" />
              <Stat label="Fastest laps" value={int(career.fastest_laps)} />
            </div>

            <div className="grid grid-4 mt-2">
              <Stat label="Win rate" value={pct(career.win_rate)} />
              <Stat label="Podium rate" value={pct(career.podium_rate)} />
              <Stat label="Avg finish" value={num(career.avg_finish, 2)} />
              <Stat label="Avg grid" value={num(career.avg_grid, 2)} />
            </div>

            <SectionTitle>Career telemetry</SectionTitle>
            <div className="grid grid-2">
              <Panel title="Points & wins by season">
                <TelemetryLine
                  data={seasonSeries}
                  x="season"
                  lines={[
                    { key: 'points', name: 'Points', color: '#e10600' },
                    { key: 'wins', name: 'Wins', color: '#2ea8ff' },
                  ]}
                  height={300}
                />
              </Panel>
              <Panel title="Qualifying → finish" hint="every race entry">
                <ScatterPlot
                  data={scatter}
                  x="x"
                  y="y"
                  color="#00d17a"
                  xLabel="Qualifying position"
                  yLabel="Finish position"
                  tooltipFormatter={(v, name) => [v, name]}
                />
              </Panel>
            </div>

            <div className="grid grid-2 mt-2">
              <Panel title="Season-by-season" hint="championship position where known">
                <DataTable
                  columns={[
                    { key: 'season', header: 'Season' },
                    { key: 'teams', header: 'Team' },
                    { key: 'races', header: 'Races', align: 'right' },
                    { key: 'wins', header: 'Wins', align: 'right' },
                    { key: 'podiums', header: 'Podiums', align: 'right' },
                    { key: 'points', header: 'Points', align: 'right', render: (r) => num(r.points, 1) },
                    { key: 'avg_finish', header: 'Avg fin', align: 'right', render: (r) => num(r.avg_finish, 2) },
                    {
                      key: 'championship_position',
                      header: 'Champ.',
                      align: 'right',
                      render: (r) => (r.championship_position ? `P${r.championship_position}` : '—'),
                    },
                  ]}
                  rows={seasons || []}
                  rowKey={(r) => r.season}
                />
              </Panel>
              <Panel title="Wins by circuit">
                {(wins_by_circuit || []).length ? (
                  <TelemetryBar
                    data={(wins_by_circuit || []).map((w) => ({ label: w.circuit, wins: w.wins }))}
                    x="label"
                    layout="vertical"
                    bars={[{ key: 'wins', name: 'Wins', color: '#ffb400' }]}
                    height={340}
                  />
                ) : (
                  <div className="chart-empty">No wins recorded.</div>
                )}
              </Panel>
            </div>

            <SectionTitle>Recent results</SectionTitle>
            <DataTable
              columns={[
                { key: 'season', header: 'Season' },
                { key: 'round', header: 'R', align: 'right' },
                { key: 'race_name', header: 'Grand Prix' },
                { key: 'constructor', header: 'Team' },
                { key: 'grid', header: 'Grid', align: 'right' },
                { key: 'position', header: 'Finish', align: 'right' },
                {
                  key: 'position_gain',
                  header: 'Gain',
                  align: 'right',
                  render: (r) => signed(r.position_gain),
                },
                { key: 'points', header: 'Pts', align: 'right', render: (r) => num(r.points, 0) },
                { key: 'status', header: 'Status' },
              ]}
              rows={recent_results || []}
              rowKey={(r, i) => `${r.season}-${r.round}-${i}`}
            />
          </>
        )
      }}
    </Async>
  )
}
