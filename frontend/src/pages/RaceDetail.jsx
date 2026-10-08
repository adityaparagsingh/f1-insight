import { useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { Async, DataTable, DriverLink, EmptyState, Panel, Stat, Tabs } from '../components/ui'
import { TelemetryBar } from '../charts'
import { classForPosition, int, secondsFromMs, signed } from '../utils/format'

export default function RaceDetail() {
  const { id } = useParams()
  const query = useApi(() => api.race(id), [id])

  return (
    <Async state={query} label="Loading race timing screen…">
      {(data) => {
        const { race, results, qualifying, pit_stops, fastest_laps, summary } = data
        return (
          <>
            <div className="page-head">
              <div>
                <div className="eyebrow">
                  Round {race.round} · {race.season}
                </div>
                <h1>{race.name}</h1>
                <p className="subtitle">
                  {race.circuit} · {race.location}, {race.country} · {race.date}
                  {race.url && (
                    <>
                      {' · '}
                      <a className="rowlink" href={race.url} target="_blank" rel="noreferrer">
                        Race report ↗
                      </a>
                    </>
                  )}
                </p>
              </div>
            </div>

            <div className="grid grid-6">
              <Stat label="Entries" value={int(summary.entries)} />
              <Stat label="Retirements" value={int(summary.dnfs)} tone="red" />
              <Stat label="Position gainers" value={int(summary.position_gainers)} tone="green" />
              <Stat label="Position losers" value={int(summary.position_losers)} tone="amber" />
              <Stat label="Biggest gain" value={signed(summary.biggest_gain)} tone="blue" />
              <Stat label="Fastest lap" value={secondsFromMs(summary.fastest_lap_seconds)} />
            </div>

            <RaceTabs
              results={results}
              qualifying={qualifying}
              pit_stops={pit_stops}
              fastest_laps={fastest_laps}
            />
          </>
        )
      }}
    </Async>
  )
}

function RaceTabs({ results, qualifying, pit_stops, fastest_laps }) {
  const [tab, setTab] = useState('results')
  const tabs = [
    { id: 'results', label: `Race result (${(results || []).length})` },
    { id: 'quali', label: `Qualifying (${(qualifying || []).length})` },
    { id: 'pits', label: `Pit stops (${(pit_stops || []).length})` },
    { id: 'laps', label: `Fastest laps (${(fastest_laps || []).length})` },
    { id: 'gains', label: 'Position changes' },
  ]

  const finishByPosition = (results || []).map((r) => ({
    label: r.code || r.driver,
    gain: Number(r.position_gain || 0),
  }))

  return (
    <div className="mt-2">
      <Tabs tabs={tabs} active={tab} onChange={setTab} />

      {tab === 'results' &&
        ((results || []).length ? (
          <Panel title="Classification">
            <DataTable
              columns={[
                {
                  key: 'position',
                  header: 'Pos',
                  align: 'right',
                  render: (r) => (
                    <span className={classForPosition(r.position)}>{r.position ?? 'DNF'}</span>
                  ),
                },
                { key: 'grid', header: 'Grid', align: 'right' },
                {
                  key: 'driver',
                  header: 'Driver',
                  render: (r) => <DriverLink id={r.driver_id} name={r.driver} code={r.code} />,
                },
                { key: 'constructor', header: 'Team' },
                { key: 'laps', header: 'Laps', align: 'right' },
                { key: 'points', header: 'Points', align: 'right' },
                { key: 'pit_stop_count', header: 'Stops', align: 'right' },
                {
                  key: 'position_gain',
                  header: 'Gain',
                  align: 'right',
                  render: (r) => signed(r.position_gain),
                },
                { key: 'status', header: 'Status' },
              ]}
              rows={results}
              rowKey={(r) => r.result_id}
            />
          </Panel>
        ) : (
          <EmptyState message="No race classification available." />
        ))}

      {tab === 'quali' &&
        ((qualifying || []).length ? (
          <Panel title="Qualifying classification">
            <DataTable
              columns={[
                { key: 'position', header: 'Pos', align: 'right' },
                {
                  key: 'driver',
                  header: 'Driver',
                  render: (r) => <DriverLink id={r.driver_id} name={r.driver} code={r.code} />,
                },
                { key: 'constructor', header: 'Team' },
                { key: 'q1', header: 'Q1' },
                { key: 'q2', header: 'Q2' },
                { key: 'q3', header: 'Q3' },
              ]}
              rows={qualifying}
              rowKey={(r, i) => `${r.driver_id}-${i}`}
            />
          </Panel>
        ) : (
          <EmptyState message="No qualifying data available for this race." />
        ))}

      {tab === 'pits' &&
        ((pit_stops || []).length ? (
          <Panel title="Pit stops" hint="fastest first">
            <DataTable
              columns={[
                {
                  key: 'duration',
                  header: 'Duration',
                  align: 'right',
                  render: (r) => `${r.duration}s`,
                },
                {
                  key: 'driver',
                  header: 'Driver',
                  render: (r) => (
                    <span>
                      {r.driver}
                      {r.code ? ` (${r.code})` : ''}
                    </span>
                  ),
                },
                { key: 'constructor', header: 'Team' },
                { key: 'lap', header: 'Lap', align: 'right' },
                { key: 'stop_number', header: 'Stop', align: 'right' },
              ]}
              rows={pit_stops}
              rowKey={(r, i) => `${r.driver}-${i}`}
            />
          </Panel>
        ) : (
          <EmptyState message="No pit-stop data available for this race." />
        ))}

      {tab === 'laps' &&
        ((fastest_laps || []).length ? (
          <Panel title="Fastest laps">
            <DataTable
              columns={[
                { key: 'fastest_lap_rank', header: 'Rank', align: 'right' },
                { key: 'driver', header: 'Driver' },
                { key: 'constructor', header: 'Team' },
                { key: 'fastest_lap_time', header: 'Time' },
                { key: 'fastest_lap_speed', header: 'Avg km/h', align: 'right' },
              ]}
              rows={fastest_laps}
              rowKey={(r, i) => `${r.driver}-${i}`}
            />
          </Panel>
        ) : (
          <EmptyState message="No lap-time data available for this race." />
        ))}

      {tab === 'gains' && (
        <Panel title="Positions gained / lost" hint="positive = gained">
          <TelemetryBar
            data={finishByPosition}
            x="label"
            bars={[
              {
                key: 'gain',
                name: 'Positions gained',
                cellColorBy: (entry) => (entry.gain >= 0 ? '#00d17a' : '#e10600'),
              },
            ]}
            height={340}
          />
        </Panel>
      )}
    </div>
  )
}
