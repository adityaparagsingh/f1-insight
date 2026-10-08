import { Link } from 'react-router-dom'
import { int as fmtInt } from '../utils/format'

// ---------------------------------------------------------------------------
// Reusable presentational building blocks for every F1 INSIGHT page.
// ---------------------------------------------------------------------------

export function Panel({ title, hint, accent = true, className = '', children }) {
  return (
    <section className={`panel ${accent ? 'accent' : ''} ${className}`}>
      {title && (
        <header className="panel-title">
          <span>{title}</span>
          {hint && <span className="hint">{hint}</span>}
        </header>
      )}
      {children}
    </section>
  )
}

export function SectionTitle({ children }) {
  return <h2 className="section-title">{children}</h2>
}

export function Stat({ label, value, foot, tone = '' }) {
  return (
    <div className={`stat ${tone}`}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {foot && <span className="stat-foot">{foot}</span>}
    </div>
  )
}

export function Badge({ tone = '', children }) {
  return <span className={`badge ${tone}`}>{children}</span>
}

export function Spinner({ label = 'Loading telemetry…' }) {
  return (
    <div className="state">
      <div className="spinner" />
      <span className="tiny">{label}</span>
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="state error">
      <span className="state-icon">⚠</span>
      <strong>Something went wrong</strong>
      <span className="tiny">{error}</span>
      {onRetry && (
        <button className="btn" onClick={onRetry} type="button">
          Retry
        </button>
      )}
    </div>
  )
}

export function EmptyState({ message = 'No data available for this selection.' }) {
  return (
    <div className="state">
      <span className="state-icon">🏁</span>
      <span className="tiny">{message}</span>
    </div>
  )
}

// Wrap async page data: renders spinner / error / children render-prop.
export function Async({ state, children, label }) {
  if (state.loading) return <Spinner label={label} />
  if (state.error) return <ErrorState error={state.error} onRetry={state.reload} />
  if (state.data === null || state.data === undefined) return <EmptyState />
  return children(state.data)
}

export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          className={`tab ${active === tab.id ? 'active' : ''}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}

export function DataTable({ columns, rows, empty = 'No rows.', rowKey, getRowProps }) {
  if (!rows || rows.length === 0) return <EmptyState message={empty} />
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={col.align === 'right' ? 'num' : ''}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={rowKey ? rowKey(row, idx) : idx} {...(getRowProps ? getRowProps(row) : {})}>
              {columns.map((col) => (
                <td key={col.key} className={col.align === 'right' ? 'num' : ''}>
                  {col.render ? col.render(row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function DriverLink({ id, name, code }) {
  if (id === null || id === undefined) return <span>{name || '—'}</span>
  return (
    <Link className="rowlink" to={`/drivers/${id}`}>
      {name || code || `#${id}`}
      {code && <span className="code-pill" style={{ marginLeft: 8 }}>{code}</span>}
    </Link>
  )
}

export function ConstructorLink({ id, name }) {
  if (id === null || id === undefined) return <span>{name || '—'}</span>
  return (
    <Link className="rowlink" to={`/constructors/${id}`}>
      {name}
    </Link>
  )
}

export function CircuitLink({ id, name }) {
  if (id === null || id === undefined) return <span>{name || '—'}</span>
  return (
    <Link className="rowlink" to={`/circuits/${id}`}>
      {name}
    </Link>
  )
}

export function RaceLink({ id, name }) {
  if (id === null || id === undefined) return <span>{name || '—'}</span>
  return (
    <Link className="rowlink" to={`/races/${id}`}>
      {name}
    </Link>
  )
}

export function CountBadge({ value }) {
  return <span className="badge">{fmtInt(value)}</span>
}
