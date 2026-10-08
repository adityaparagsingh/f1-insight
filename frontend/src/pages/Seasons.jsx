import { Link } from 'react-router-dom'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { Async, DataTable, Panel, SectionTitle } from '../components/ui'
import { TelemetryArea } from '../charts'
import { int, num } from '../utils/format'

export default function Seasons() {
  const seasons = useApi(() => api.seasons(), [])
  const rows = seasons.data || []

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Dimension · dim_date / dim_race</div>
          <h1>Season Explorer</h1>
          <p className="subtitle">
            Every championship season in the warehouse with calendar size and
            classified results. Select a season to open its full race calendar.
          </p>
        </div>
      </div>

      <Async state={seasons} label="Loading seasons…">
        {() => (
          <>
            <Panel title="Calendar size across history" hint="races per season">
              <TelemetryArea
                data={rows}
                x="season"
                areas={[
                  { key: 'races', name: 'Races', color: '#e10600' },
                  { key: 'results', name: 'Classified results', color: '#2ea8ff' },
                ]}
                height={320}
              />
            </Panel>

            <SectionTitle>{rows.length} seasons</SectionTitle>
            <DataTable
              columns={[
                {
                  key: 'season',
                  header: 'Season',
                  render: (r) => (
                    <Link className="rowlink mono" to={`/races?season=${r.season}`}>
                      {r.season}
                    </Link>
                  ),
                },
                { key: 'races', header: 'Races', align: 'right', render: (r) => int(r.races) },
                { key: 'results', header: 'Results', align: 'right', render: (r) => int(r.results) },
                {
                  key: 'avg_field',
                  header: 'Avg field',
                  align: 'right',
                  render: (r) => num(r.races ? r.results / r.races : null, 1),
                },
                { key: 'first_race', header: 'First race' },
                { key: 'last_race', header: 'Last race' },
              ]}
              rows={rows}
              rowKey={(r) => r.season}
              empty="No seasons loaded."
            />
          </>
        )}
      </Async>
    </>
  )
}
