import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="state" style={{ marginTop: '4rem' }}>
      <span className="state-icon" style={{ fontSize: '3rem', color: 'var(--red)' }}>🏁</span>
      <h1 style={{ margin: 0 }}>404 — Off track</h1>
      <p className="tiny">
        That page is not on the F1 INSIGHT race control timeline. It may have been
        retired or the link is wrong.
      </p>
      <Link className="btn primary" to="/">
        Back to the command centre
      </Link>
    </div>
  )
}
