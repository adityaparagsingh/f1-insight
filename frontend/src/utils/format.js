// ---------------------------------------------------------------------------
// Formatting helpers — the API returns real JSON numbers, but pages still
// guard against nulls/strings from the warehouse.
// ---------------------------------------------------------------------------

export function num(value, digits = 2) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function int(value) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return Math.round(n).toLocaleString()
}

export function pct(value, digits = 1) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  const scaled = Math.abs(n) <= 1 ? n * 100 : n
  return `${scaled.toFixed(digits)}%`
}

export function signed(value, digits = 0) {
  if (value === null || value === undefined) return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return `${n > 0 ? '+' : ''}${n.toFixed(digits)}`
}

export function secondsFromMs(ms) {
  if (ms === null || ms === undefined) return '—'
  const n = Number(ms)
  if (Number.isNaN(n)) return '—'
  return `${(n / 1000).toFixed(3)}s`
}

export function ordinal(n) {
  if (n === null || n === undefined) return '—'
  const value = Number(n)
  const suffixes = ['th', 'st', 'nd', 'rd']
  const mod = value % 100
  const suffix = suffixes[(mod - 20) % 10] || suffixes[mod] || suffixes[0]
  return `${value}${suffix}`
}

export function titleCase(text) {
  if (!text) return ''
  return String(text)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function classForPosition(position) {
  const p = Number(position)
  if (p === 1) return 'pos-gold'
  if (p === 2) return 'pos-silver'
  if (p === 3) return 'pos-bronze'
  if (p && p <= 10) return 'pos-points'
  return ''
}
