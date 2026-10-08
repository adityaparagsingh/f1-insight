import { useEffect, useMemo, useState } from 'react'
import api from '../services/api'
import useApi from '../hooks/useApi'
import {
  Async,
  DataTable,
  EmptyState,
  Panel,
  Stat,
  Tabs,
} from '../components/ui'
import { PALETTE, TelemetryBar } from '../charts'
import { int, num, titleCase } from '../utils/format'

// ---------------------------------------------------------------------------
// Data Lab — the five OLAP operations surfaced as backend endpoints:
// roll-up, drill-down, slice, dice and pivot.
// ---------------------------------------------------------------------------

const OPS = [
  { id: 'rollup', label: 'Roll-up' },
  { id: 'drilldown', label: 'Drill-down' },
  { id: 'slice', label: 'Slice' },
  { id: 'dice', label: 'Dice' },
  { id: 'pivot', label: 'Pivot' },
]

const DIMS = [
  ['driver', 'Driver'],
  ['constructor', 'Team'],
  ['season', 'Season'],
  ['circuit', 'Circuit'],
  ['race', 'Race'],
]

const MEASURES = [
  ['points', 'Points'],
  ['wins', 'Wins'],
  ['podiums', 'Podiums'],
  ['races', 'Races'],
  ['avg_finish', 'Avg finish'],
  ['dnfs', 'DNFs'],
  ['avg_position_gain', 'Avg position gain'],
]

const DEFAULT_DRAFT = {
  rollup: { l1: 'driver', l2: 'constructor', l3: 'season', season_from: '', season_to: '', limit: 25 },
  drilldown: { level: 'season', season: '', race_id: '', driver_id: '', limit: 50 },
  slice: { dimension: 'constructor', value: '1', group_by: 'season', limit: 25 },
  dice: {
    season_from: '', season_to: '', constructor_ids: '', circuit_ids: '', driver_ids: '',
    group_by: ['season', 'constructor'], limit: 50,
  },
  pivot: {
    rows: 'constructor', cols: 'season', measure: 'points',
    season_from: '', season_to: '', limit_rows: 15, limit_cols: 15,
  },
}

function DimOptions() {
  return DIMS.map(([v, l]) => (
    <option key={v} value={v}>
      {l}
    </option>
  ))
}

export default function Olap() {
  const [active, setActive] = useState('rollup')
  const [draft, setDraft] = useState(DEFAULT_DRAFT)
  const [query, setQuery] = useState({ op: 'rollup', params: DEFAULT_DRAFT.rollup })

  const seasons = useApi(() => api.seasons(), [])
  const seasonList = seasons.data || []

  const setField = (key, value) =>
    setDraft((d) => ({ ...d, [active]: { ...d[active], [key]: value } }))

  const run = (op = active) => setQuery({ op, params: draft[op] })

  // auto-run whenever the visible operation changes
  useEffect(() => {
    setQuery({ op: active, params: draft[active] })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  const result = useApi(() => {
    const { op, params } = query
    if (op === 'rollup') {
      const dimensions = [params.l1, params.l2, params.l3].filter(Boolean).join(',')
      return api.olapRollup({
        dimensions,
        season_from: params.season_from,
        season_to: params.season_to,
        limit: params.limit,
      })
    }
    if (op === 'drilldown') {
      return api.olapDrilldown({
        level: params.level,
        season: params.season,
        race_id: params.race_id,
        driver_id: params.driver_id,
        limit: params.limit,
      })
    }
    if (op === 'slice') {
      return api.olapSlice({
        dimension: params.dimension,
        value: params.value,
        group_by: params.group_by,
        limit: params.limit,
      })
    }
    if (op === 'dice') {
      return api.olapDice({
        season_from: params.season_from,
        season_to: params.season_to,
        constructor_ids: params.constructor_ids,
        circuit_ids: params.circuit_ids,
        driver_ids: params.driver_ids,
        group_by: params.group_by,
        limit: params.limit,
      })
    }
    return api.olapPivot({
      rows: params.rows,
      cols: params.cols,
      measure: params.measure,
      season_from: params.season_from,
      season_to: params.season_to,
      limit_rows: params.limit_rows,
      limit_cols: params.limit_cols,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query])

  const toggleGroupDim = (dim) => {
    setDraft((d) => {
      const cur = d.dice.group_by
      const next = cur.includes(dim) ? cur.filter((x) => x !== dim) : [...cur, dim]
      return { ...d, dice: { ...d.dice, group_by: next } }
    })
  }

  const runButton = (
    <div className="field">
      <label>&nbsp;</label>
      <button className="btn primary" type="button" onClick={() => run()}>
        Run {OPS.find((o) => o.id === active)?.label}
      </button>
    </div>
  )

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">OLAP · MySQL star schema</div>
          <h1>Data Lab</h1>
          <p className="subtitle">
            Online analytical processing over the F1 cube: roll the hierarchy up,
            drill back down to individual laps, slice and dice the dimensions, and
            pivot any two of them against a chosen measure.
          </p>
        </div>
      </div>

      <Tabs tabs={OPS} active={active} onChange={setActive} />

      {active === 'rollup' && (
        <div className="toolbar">
          <div className="field">
            <label>Level 1</label>
            <select className="control" value={draft.rollup.l1} onChange={(e) => setField('l1', e.target.value)}>
              <DimOptions />
            </select>
          </div>
          <div className="field">
            <label>Level 2</label>
            <select className="control" value={draft.rollup.l2} onChange={(e) => setField('l2', e.target.value)}>
              <option value="">— none —</option>
              <DimOptions />
            </select>
          </div>
          <div className="field">
            <label>Level 3</label>
            <select className="control" value={draft.rollup.l3} onChange={(e) => setField('l3', e.target.value)}>
              <option value="">— none —</option>
              <DimOptions />
            </select>
          </div>
          <div className="field">
            <label>From season</label>
            <select className="control" value={draft.rollup.season_from} onChange={(e) => setField('season_from', e.target.value)}>
              <option value="">Any</option>
              {seasonList.map((s) => <option key={s.season} value={s.season}>{s.season}</option>)}
            </select>
          </div>
          <div className="field">
            <label>To season</label>
            <select className="control" value={draft.rollup.season_to} onChange={(e) => setField('season_to', e.target.value)}>
              <option value="">Any</option>
              {seasonList.map((s) => <option key={s.season} value={s.season}>{s.season}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Limit</label>
            <input className="control" type="number" min="1" max="1000" value={draft.rollup.limit} onChange={(e) => setField('limit', e.target.value)} />
          </div>
          {runButton}
        </div>
      )}

      {active === 'drilldown' && (
        <div className="toolbar">
          <div className="field">
            <label>Level</label>
            <select className="control" value={draft.drilldown.level} onChange={(e) => setField('level', e.target.value)}>
              <option value="season">Season → Race</option>
              <option value="race">Race → Driver</option>
              <option value="driver">Driver → Lap</option>
              <option value="lap">Lap detail</option>
            </select>
          </div>
          <div className="field">
            <label>Season</label>
            <select className="control" value={draft.drilldown.season} onChange={(e) => setField('season', e.target.value)}>
              <option value="">Any</option>
              {seasonList.map((s) => <option key={s.season} value={s.season}>{s.season}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Race id</label>
            <input className="control" type="number" min="1" value={draft.drilldown.race_id} onChange={(e) => setField('race_id', e.target.value)} />
          </div>
          <div className="field">
            <label>Driver id</label>
            <input className="control" type="number" min="1" value={draft.drilldown.driver_id} onChange={(e) => setField('driver_id', e.target.value)} />
          </div>
          <div className="field">
            <label>Limit</label>
            <input className="control" type="number" min="1" max="2000" value={draft.drilldown.limit} onChange={(e) => setField('limit', e.target.value)} />
          </div>
          {runButton}
        </div>
      )}

      {active === 'slice' && (
        <div className="toolbar">
          <div className="field">
            <label>Slice dimension</label>
            <select className="control" value={draft.slice.dimension} onChange={(e) => setField('dimension', e.target.value)}>
              <DimOptions />
            </select>
          </div>
          <div className="field" style={{ flex: 1, minWidth: 160 }}>
            <label>Value (id or exact label)</label>
            <input className="control full" value={draft.slice.value} onChange={(e) => setField('value', e.target.value)} />
          </div>
          <div className="field">
            <label>Break down by</label>
            <select className="control" value={draft.slice.group_by} onChange={(e) => setField('group_by', e.target.value)}>
              <DimOptions />
            </select>
          </div>
          <div className="field">
            <label>Limit</label>
            <input className="control" type="number" min="1" max="1000" value={draft.slice.limit} onChange={(e) => setField('limit', e.target.value)} />
          </div>
          {runButton}
        </div>
      )}

      {active === 'dice' && (
        <div className="toolbar">
          <div className="field">
            <label>From season</label>
            <select className="control" value={draft.dice.season_from} onChange={(e) => setField('season_from', e.target.value)}>
              <option value="">Any</option>
              {seasonList.map((s) => <option key={s.season} value={s.season}>{s.season}</option>)}
            </select>
          </div>
          <div className="field">
            <label>To season</label>
            <select className="control" value={draft.dice.season_to} onChange={(e) => setField('season_to', e.target.value)}>
              <option value="">Any</option>
              {seasonList.map((s) => <option key={s.season} value={s.season}>{s.season}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Team ids</label>
            <input className="control" placeholder="1,6" value={draft.dice.constructor_ids} onChange={(e) => setField('constructor_ids', e.target.value)} />
          </div>
          <div className="field">
            <label>Circuit ids</label>
            <input className="control" placeholder="1,2" value={draft.dice.circuit_ids} onChange={(e) => setField('circuit_ids', e.target.value)} />
          </div>
          <div className="field">
            <label>Driver ids</label>
            <input className="control" placeholder="1,3" value={draft.dice.driver_ids} onChange={(e) => setField('driver_ids', e.target.value)} />
          </div>
          {runButton}
        </div>
      )}

      {active === 'dice' && (
        <div className="row mt-2" style={{ flexWrap: 'wrap', gap: '0.4rem' }}>
          <span className="tiny muted">Group by:</span>
          {DIMS.map(([v, l]) => (
            <button
              key={v}
              type="button"
              className={`btn ${draft.dice.group_by.includes(v) ? 'primary' : ''}`}
              onClick={() => toggleGroupDim(v)}
            >
              {l}
            </button>
          ))}
        </div>
      )}

      {active === 'pivot' && (
        <div className="toolbar">
          <div className="field">
            <label>Rows</label>
            <select className="control" value={draft.pivot.rows} onChange={(e) => setField('rows', e.target.value)}>
              <DimOptions />
            </select>
          </div>
          <div className="field">
            <label>Columns</label>
            <select className="control" value={draft.pivot.cols} onChange={(e) => setField('cols', e.target.value)}>
              <DimOptions />
            </select>
          </div>
          <div className="field">
            <label>Measure</label>
            <select className="control" value={draft.pivot.measure} onChange={(e) => setField('measure', e.target.value)}>
              {MEASURES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="field">
            <label>From season</label>
            <select className="control" value={draft.pivot.season_from} onChange={(e) => setField('season_from', e.target.value)}>
              <option value="">Any</option>
              {seasonList.map((s) => <option key={s.season} value={s.season}>{s.season}</option>)}
            </select>
          </div>
          <div className="field">
            <label>To season</label>
            <select className="control" value={draft.pivot.season_to} onChange={(e) => setField('season_to', e.target.value)}>
              <option value="">Any</option>
              {seasonList.map((s) => <option key={s.season} value={s.season}>{s.season}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Max rows</label>
            <input className="control" type="number" min="1" max="100" value={draft.pivot.limit_rows} onChange={(e) => setField('limit_rows', e.target.value)} />
          </div>
          <div className="field">
            <label>Max cols</label>
            <input className="control" type="number" min="1" max="100" value={draft.pivot.limit_cols} onChange={(e) => setField('limit_cols', e.target.value)} />
          </div>
          {runButton}
        </div>
      )}

      <div className="mt-2">
        <Async state={result} label={`Running ${active}…`}>
          {(data) => <Result op={active} data={data} />}
        </Async>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Result renderers
// ---------------------------------------------------------------------------

function MeasureColumns() {
  return [
    { key: 'races', header: 'Races', align: 'right' },
    { key: 'wins', header: 'Wins', align: 'right' },
    { key: 'podiums', header: 'Podiums', align: 'right' },
    { key: 'points', header: 'Points', align: 'right', render: (r) => num(r.points, 1) },
    { key: 'avg_finish', header: 'Avg finish', align: 'right', render: (r) => num(r.avg_finish, 2) },
    { key: 'dnfs', header: 'DNFs', align: 'right' },
    { key: 'avg_position_gain', header: 'Avg gain', align: 'right', render: (r) => num(r.avg_position_gain, 2) },
  ]
}

function Result({ op, data }) {
  if (!data) return <EmptyState />
  if (data.error) return <EmptyState message={data.error} />

  if (op === 'rollup') return <RollupResult data={data} />
  if (op === 'drilldown') return <DrilldownResult data={data} />
  if (op === 'slice') return <SliceResult data={data} />
  if (op === 'dice') return <DiceResult data={data} />
  return <PivotResult data={data} />
}

function RollupResult({ data }) {
  const rows = data.rows || []
  const dimCols = (data.dimensions || []).map((dim) => ({
    key: dim,
    header: titleCase(dim),
    render: (r) => (
      <span>
        {r[`${dim}_name`]}
        {r[`${dim}_code`] ? <span className="code-pill" style={{ marginLeft: 6 }}>{r[`${dim}_code`]}</span> : null}
      </span>
    ),
  }))
  const chart = rows.slice(0, 15).map((r) => ({
    label: [r.driver_name, r.constructor_name, r.circuit_name, r.race_name, r.season_name]
      .find((v) => v !== undefined && v !== null && v !== '') || '',
    points: Number(r.points) || 0,
  }))
  return (
    <>
      <Panel title={`Roll-up by ${(data.dimensions || []).join(' › ')}`} hint={`${int(data.row_count)} groups`}>
        <DataTable
          columns={[...dimCols, ...MeasureColumns()]}
          rows={rows}
          rowKey={(r, i) => `${i}-${r[`${data.dimensions[0]}_id`]}`}
          empty="No groups for this hierarchy."
        />
      </Panel>
      {chart.length > 0 && (
        <Panel title="Top groups by points" className="mt-2">
          <TelemetryBar
            data={chart}
            x="label"
            bars={[{ key: 'points', name: 'Points', color: '#e10600' }]}
          />
        </Panel>
      )}
    </>
  )
}

function DrilldownResult({ data }) {
  const rows = data.rows || []
  const level = data.level

  const columns = useMemo(() => {
    if (!rows.length) return []
    if (level === 'season') {
      return [
        { key: 'season_name', header: 'Season' },
        { key: 'races', header: 'Races', align: 'right' },
        { key: 'entries', header: 'Entries', align: 'right' },
        { key: 'wins', header: 'Wins', align: 'right' },
        { key: 'points', header: 'Points', align: 'right', render: (r) => num(r.points, 1) },
        { key: 'avg_finish', header: 'Avg finish', align: 'right', render: (r) => num(r.avg_finish, 2) },
        { key: 'dnfs', header: 'DNFs', align: 'right' },
      ]
    }
    if (level === 'race') {
      return [
        { key: 'race_name', header: 'Race' },
        { key: 'circuit', header: 'Circuit' },
        { key: 'winner', header: 'Winner' },
        { key: 'entries', header: 'Entries', align: 'right' },
        { key: 'points', header: 'Points', align: 'right', render: (r) => num(r.points, 1) },
        { key: 'dnfs', header: 'DNFs', align: 'right' },
      ]
    }
    if (level === 'driver') {
      return [
        { key: 'driver_name', header: 'Driver' },
        { key: 'constructor', header: 'Team' },
        { key: 'races', header: 'Races', align: 'right' },
        { key: 'wins', header: 'Wins', align: 'right' },
        { key: 'podiums', header: 'Podiums', align: 'right' },
        { key: 'points', header: 'Points', align: 'right', render: (r) => num(r.points, 1) },
        { key: 'avg_finish', header: 'Avg finish', align: 'right', render: (r) => num(r.avg_finish, 2) },
        { key: 'avg_position_gain', header: 'Avg gain', align: 'right', render: (r) => num(r.avg_position_gain, 2) },
      ]
    }
    return [
      { key: 'lap_name', header: 'Lap' },
      { key: 'driver', header: 'Driver' },
      { key: 'constructor', header: 'Team' },
      { key: 'position', header: 'Pos', align: 'right' },
      { key: 'lap_time', header: 'Lap time' },
      { key: 'lap_milliseconds', header: 'ms', align: 'right' },
    ]
  }, [rows, level])

  return (
    <Panel
      title={`Drill-down · level "${level}"`}
      hint={`${int(data.row_count)} rows${data.next_level ? ` · next: ${data.next_level}` : ''}`}
    >
      {data.required_filters?.length > 0 && (
        <p className="tiny muted mb-1">
          Provide filter(s) to narrow further: {data.required_filters.join(', ')}.
        </p>
      )}
      <DataTable columns={columns} rows={rows} rowKey={(r, i) => i} empty="No rows at this level." />
    </Panel>
  )
}

function SliceResult({ data }) {
  const t = data.totals || {}
  const rows = data.breakdown || []
  const chart = rows.slice(0, 15).map((r) => ({ label: String(r.group_value), points: Number(r.points) || 0 }))
  return (
    <>
      <div className="grid grid-6">
        <Stat label="Entries" value={int(t.entries)} tone="red" />
        <Stat label="Races" value={int(t.races)} />
        <Stat label="Wins" value={int(t.wins)} tone="amber" />
        <Stat label="Podiums" value={int(t.podiums)} />
        <Stat label="Points" value={num(t.points, 1)} tone="blue" />
        <Stat label="Avg finish" value={num(t.avg_finish, 2)} tone="green" />
      </div>
      <Panel
        title={`Slice · ${data.dimension} = ${data.value}`}
        hint={`broken down by ${data.group_by}`}
        className="mt-2"
      >
        <DataTable
          columns={[
            { key: 'group_value', header: titleCase(data.group_by) },
            { key: 'entries', header: 'Entries', align: 'right' },
            { key: 'wins', header: 'Wins', align: 'right' },
            { key: 'points', header: 'Points', align: 'right', render: (r) => num(r.points, 1) },
            { key: 'avg_finish', header: 'Avg finish', align: 'right', render: (r) => num(r.avg_finish, 2) },
          ]}
          rows={rows}
          rowKey={(r, i) => i}
          empty="No rows in this slice."
        />
      </Panel>
      {chart.length > 0 && (
        <Panel title="Points by group" className="mt-2">
          <TelemetryBar data={chart} x="label" bars={[{ key: 'points', name: 'Points', color: '#2ea8ff' }]} />
        </Panel>
      )}
    </>
  )
}

function DiceResult({ data }) {
  const t = data.totals || {}
  const rows = data.rows || []
  const dims = data.group_by || []
  const dimCols = dims.map((dim) => ({
    key: dim,
    header: titleCase(dim),
    render: (r) => r[`${dim}_name`] ?? '—',
  }))
  const chart = rows.slice(0, 15).map((r) => ({
    label: dims.map((d) => r[`${d}_name`]).filter(Boolean).join(' · '),
    points: Number(r.points) || 0,
  }))
  return (
    <>
      <div className="grid grid-4">
        <Stat label="Entries in sub-cube" value={int(t.entries)} tone="red" />
        <Stat label="Wins" value={int(t.wins)} tone="amber" />
        <Stat label="Podiums" value={int(t.podiums)} />
        <Stat label="Points" value={num(t.points, 1)} tone="blue" />
      </div>
      <Panel
        title="Dice · filtered sub-cube"
        hint={`grouped by ${dims.join(' › ')}`}
        className="mt-2"
      >
        <DataTable
          columns={[...dimCols, ...MeasureColumns()]}
          rows={rows}
          rowKey={(r, i) => i}
          empty="No rows match these filters."
        />
      </Panel>
      {chart.length > 0 && (
        <Panel title="Top sub-cube groups by points" className="mt-2">
          <TelemetryBar data={chart} x="label" bars={[{ key: 'points', name: 'Points', color: '#00d17a' }]} />
        </Panel>
      )}
    </>
  )
}

function PivotResult({ data }) {
  const cols = data.columns || []
  const rows = data.rows || []
  const values = data.values || []
  const flat = values.flat()
  const max = flat.length ? Math.max(...flat) : 0
  const cellStyle = (v) => ({
    background: max > 0 ? `rgba(225, 6, 0, ${0.08 + 0.45 * (Number(v) / max)})` : 'transparent',
  })
  if (!rows.length || !cols.length) return <EmptyState message="No pivot cells for this combination." />
  return (
    <Panel
      title={`Pivot · ${data.rows_dim} × ${data.cols_dim}`}
      hint={`measure: ${data.measure}`}
    >
      <div className="table-wrap">
        <table className="data pivot-table">
          <thead>
            <tr>
              <th>{titleCase(data.rows_dim)}</th>
              {cols.map((c) => (
                <th key={c} className="num">{c}</th>
              ))}
              <th className="num">Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.key}>
                <td className="corner">{r.label}{r.code ? ` (${r.code})` : ''}</td>
                {cols.map((c, j) => (
                  <td key={c} className="heat" style={cellStyle(values[i]?.[j])}>
                    {num(values[i]?.[j], data.measure === 'avg_finish' ? 2 : 0)}
                  </td>
                ))}
                <td className="heat" style={{ fontWeight: 700 }}>{num(data.row_totals?.[i], 0)}</td>
              </tr>
            ))}
            <tr>
              <td className="corner">Total</td>
              {cols.map((c, j) => (
                <td key={c} className="heat">{num(data.col_totals?.[j], 0)}</td>
              ))}
              <td className="heat" style={{ fontWeight: 700 }}>{num(flat.reduce((a, b) => a + Number(b), 0), 0)}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="tiny muted mt-1">
        Heat shading scales with the chosen measure; darker cells are larger values
        ({titleCase(data.rows_dim)} rows, {titleCase(data.cols_dim)} columns).
      </p>
    </Panel>
  )
}
