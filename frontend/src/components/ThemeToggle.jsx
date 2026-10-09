import useTheme from '../hooks/useTheme'

// ---------------------------------------------------------------------------
// Day / night theme toggle.
//
// A tiny sun that spins its rays, then flips into a crescent moon with
// twinkling stars — F1 race-station style: “lights out” for dark mode,
// “daylight” for light mode. Choice is remembered across visits.
// ---------------------------------------------------------------------------
export default function ThemeToggle() {
  const [theme, toggle] = useTheme()
  const dark = theme === 'dark'

  return (
    <button
      type="button"
      className={`theme-toggle${dark ? '' : ' day'}`}
      onClick={toggle}
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-pressed={!dark}
      title={dark ? 'Lights out — dark mode. Click for daylight.' : 'Daylight — light mode. Click for lights out.'}
    >
      <span className="tt-orb" aria-hidden="true">
        <span className="tt-face tt-day">
          <span className="tt-sun" />
          <span className="tt-rays" />
        </span>
        <span className="tt-face tt-night">
          <span className="tt-moon" />
          <span className="tt-star s1" />
          <span className="tt-star s2" />
          <span className="tt-star s3" />
        </span>
      </span>
      <span className="tt-label">{dark ? 'night' : 'day'}</span>
    </button>
  )
}