import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import api from '../services/api'
import ThemeToggle from './ThemeToggle'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/seasons', label: 'Seasons' },
  { to: '/drivers', label: 'Drivers' },
  { to: '/constructors', label: 'Teams' },
  { to: '/circuits', label: 'Circuits' },
  { to: '/races', label: 'Races' },
  { to: '/olap', label: 'Data Lab' },
  { to: '/mining', label: 'Data Mining' },
  { to: '/insights', label: 'Insights' },
  { to: '/about', label: 'About' },
]

function ApiStatus() {
  const [status, setStatus] = useState({ state: 'pending', records: null })

  useEffect(() => {
    let alive = true
    const check = () =>
      api
        .health()
        .then((data) => {
          if (!alive) return
          setStatus({
            state: 'ok',
            records: data?.warehouse?.total_records ?? null,
          })
        })
        .catch(() => alive && setStatus({ state: 'bad', records: null }))
    check()
    const timer = setInterval(check, 30000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])

  const label =
    status.state === 'ok'
      ? `API online${status.records ? ` · ${status.records.toLocaleString()} rows` : ''}`
      : status.state === 'bad'
        ? 'API offline'
        : 'Connecting…'

  return (
    <div className="api-chip" title={`Backend: ${api.baseUrl}`}>
      <span className={`dot ${status.state === 'ok' ? 'ok' : status.state === 'bad' ? 'bad' : ''}`} />
      <span>{label}</span>
    </div>
  )
}

export default function Layout() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <span className="brand-mark">F1</span>
          <span className="brand-text">
            <strong>F1 INSIGHT</strong>
            <small>Race Control Analytics</small>
          </span>
        </NavLink>
        <nav className="nav-links">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <span className="topbar-spacer" />
        <div className="topbar-actions">
          <ThemeToggle />
          <ApiStatus />
        </div>
      </header>

      <main className="page">
        <Outlet />
      </main>

      <footer className="page-footer">
        <span>
          F1 INSIGHT · Formula 1 Performance Analytics &amp; Data Mining — MySQL star
          schema · OLAP · K-Means / Random Forest / Apriori
        </span>
        <span className="mono tiny">data: Jolpica F1 API</span>
      </footer>
    </div>
  )
}
