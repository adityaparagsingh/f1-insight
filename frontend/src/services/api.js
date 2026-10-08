// ---------------------------------------------------------------------------
// F1 INSIGHT API client
// Thin wrapper around the FastAPI backend. All calls return parsed JSON and
// throw an Error with a readable message on failure so pages can render the
// shared error state.
// ---------------------------------------------------------------------------

const BASE_URL =
  (import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
  'http://127.0.0.1:8000/api'

function buildQuery(params) {
  if (!params) return ''
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      if (value.length) search.set(key, value.join(','))
    } else {
      search.set(key, value)
    }
  })
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export async function apiGet(path, params, signal) {
  const url = `${BASE_URL}${path}${buildQuery(params)}`
  let response
  try {
    response = await fetch(url, { signal, headers: { Accept: 'application/json' } })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new Error(
      `Cannot reach the F1 INSIGHT API at ${BASE_URL}. Is the backend running?`,
    )
  }
  const text = await response.text()
  let body = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }
  if (!response.ok) {
    const detail =
      body && typeof body === 'object' && body.detail
        ? typeof body.detail === 'string'
          ? body.detail
          : JSON.stringify(body.detail)
        : `Request failed with status ${response.status}`
    throw new Error(detail)
  }
  return body
}

export const api = {
  baseUrl: BASE_URL,

  health: () => apiGet('/health'),

  seasons: () => apiGet('/seasons'),

  races: (params) => apiGet('/races', params),
  race: (id) => apiGet(`/races/${id}`),

  drivers: (params) => apiGet('/drivers', params),
  driver: (id) => apiGet(`/drivers/${id}`),

  constructors: (params) => apiGet('/constructors', params),
  constructor: (id) => apiGet(`/constructors/${id}`),

  circuits: (params) => apiGet('/circuits', params),
  circuit: (id) => apiGet(`/circuits/${id}`),

  overview: (params) => apiGet('/analytics/overview', params),
  analyticsDrivers: (params) => apiGet('/analytics/drivers', params),
  compareDrivers: (ids) => apiGet('/analytics/drivers/compare', { ids: ids.join(',') }),
  analyticsConstructors: (params) => apiGet('/analytics/constructors', params),
  analyticsCircuits: (params) => apiGet('/analytics/circuits', params),
  analyticsRaces: (params) => apiGet('/analytics/races', params),
  positionChanges: (params) => apiGet('/analytics/races/position-changes', params),
  qualifying: (params) => apiGet('/analytics/qualifying', params),
  pitStops: (params) => apiGet('/analytics/pit-stops', params),

  olapRollup: (params) => apiGet('/olap/rollup', params),
  olapDrilldown: (params) => apiGet('/olap/drilldown', params),
  olapSlice: (params) => apiGet('/olap/slice', params),
  olapDice: (params) => apiGet('/olap/dice', params),
  olapPivot: (params) => apiGet('/olap/pivot', params),

  clusters: (params) => apiGet('/mining/clusters', params),
  prediction: (params) => apiGet('/mining/prediction', params),
  associationRules: (params) => apiGet('/mining/association-rules', params),
  classification: (params) => apiGet('/mining/classification', params),

  insights: () => apiGet('/insights'),
}

export default api
