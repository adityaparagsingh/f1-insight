import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'f1_insight_theme'

export function themeFromStorage() {
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored === 'light' || stored === 'dark' ? stored : null
}

export function systemTheme() {
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme
  document.documentElement.style.colorScheme = theme
}

/**
 * Dark/light theme state for the whole app.
 *
 * The first paint is themed synchronously in main.jsx (no flash-of-inverted-
 * theme), this hook keeps the `data-theme` attribute on <html> in sync,
 * follows the OS preference until the user explicitly toggles, and remembers
 * the choice in localStorage.
 */
export default function useTheme() {
  const [theme, setTheme] = useState(() => themeFromStorage() || systemTheme())

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  // Follow the OS preference, but stop as soon as the user picks a side.
  useEffect(() => {
    if (themeFromStorage()) return
    const mq = window.matchMedia('(prefers-color-scheme: light)')
    const onChange = (e) => setTheme(e.matches ? 'light' : 'dark')
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const toggle = useCallback(() => {
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark'
      try {
        localStorage.setItem(STORAGE_KEY, next)
      } catch {
        /* private mode — theme still applies for this session */
      }
      return next
    })
  }, [])

  return [theme, toggle]
}