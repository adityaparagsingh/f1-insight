import { useParams } from 'react-router-dom'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { Async, DataTable, Panel, SectionTitle, Stat } from '../components/ui'
import { Donut, TelemetryBar, TelemetryLine } from '../charts'
import { num, pct } from '../utils/format'

export default function ConstructorDetail() {
  const { id } = useParams()
  const query = useApi(() => api.constructor(id), [id])

  return (
    <Async state={query} label="Loading constructor profile…">
      {(data) => {
        const { profile, career, seasons, contribution, wins_by_circuit } = data
        const series = (seasons || []).map((s) => ({
          season: s.season,
          points: Number(s.points),
          wins: Number(s.wins),
        }))

        const contributionByTeamSeason = (() => {
          const grouped = {}
          ;(contribution || []).forEach((c) => {
            const key = c.code || c.driver
            grouped[c.season] = grouped[c.season] || { season: c.season }
            grouped[c.season][key] = Number(c.points)
          })
          const rows = Object.values(grouped).sort((a, b) => a.season - b.season)
          const keys = Array.from(
            new Set((contribution || []).map((c) => c.code || c.driver)),
          ).slice(0, 6)
          return { rows: rows.slice(-12), keys }
        })()

        const lastSeasonWins = (() => {
          const byDriver = {}
          ;(contribution || []).forEach((c) => {
            const key = c.code || c.driver
            byDriver[key] = (byDriver[key] || 0) + Number(c.wins)
          })
          return Object.entries(byDriver)
            .map(([name, value]) => ({ name, value }))
            .filter((d) => d.value > 0)
            .sort((a, b) => b.value - a.value)
            .slice(0, 6)
        })()

        return (
          <>
            <div className="profile-head">
              <div className="avatar">{profile.name.slice(0, 3).toUpperCase()}</div>
              <div className="profile-meta">
                <div className="eyebrow">Constructor Profile</div>
                <h2>{profile.name}</h2>
                <div className="meta-row">
                  <span>{profile.nationality || '—'}</span>
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
              <Stat label="Entries" value={(career.races || 0).toLocaleString()} />
              <Stat label="Wins" value={(career.wins || 0).toLocaleString()} tone="red" />
              <Stat label="Podiums" value={(career.podiums || 0).toLocaleString()} tone="amber" />
              <Stat label="Points" value={num(career.points, 1)} tone="green" />
              <Stat label="Avg finish" value={num(career.avg_finish, 2)} />
              <Stat label="DNF rate" value={pct(career.dnf_rate)} tone="blue" />
            </div>

            <SectionTitle>Team telemetry</SectionTitle>
            <div className="grid grid-2">
              <Panel title="Points & wins by season">
                <TelemetryLine
                  data={series}
                  x="season"
                  lines={[
                    { key: 'points', name: 'Points', color: '#e10600' },
                    { key: 'wins', name: 'Wins', color: '#2ea8ff' },
                  ]}
                  height={300}
                />
              </Panel>
              <Panel title="Wins by driver" hint="across all seasons">
                {lastSeasonWins.length ? (
                  <Donut data={lastSeasonWins} />
                ) : (
                  <div className="chart-empty">No wins recorded.</div>
                )}
              </Panel>
            </div>

            <Panel title="Driver contribution by season" className="mt-2" hint="points per driver (recent 12 seasons)">
              {contributionByTeamSeason.rows.length ? (
                <TelemetryBar
                  data={contributionByTeamSeason.rows}
                  x="season"
                  stacked
                  bars={contributionByTeamSeason.keys.map((k) => ({ key: k, name: k }))}
                  height={320}
                />
              ) : (
                <div className="chart-empty">No contribution data.</div>
              )}
            </Panel>

            <div className="grid grid-2 mt-2">
              <Panel title="Season-by-season">
                <DataTable
                  columns={[
                    { key: 'season', header: 'Season' },
                    { key: 'races', header: 'Entries', align: 'right' },
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
                    data={wins_by_circuit.map((w) => ({ label: w.circuit, wins: w.wins }))}
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
          </>
        )
      }}
    </Async>
  )
}
