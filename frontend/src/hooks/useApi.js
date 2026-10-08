import { useCallback, useEffect, useRef, useState } from 'react'

// ---------------------------------------------------------------------------
// useApi — declarative data fetching with loading / error / refetch support.
//
//   const { data, loading, error, reload } = useApi(
//     () => api.drivers({ limit: 50 }),
//     [search, sort],
//   )
//
// `fn` must be stable enough for the dependency array to be meaningful.
// ---------------------------------------------------------------------------
export function useApi(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const fnRef = useRef(fn)
  fnRef.current = fn

  const run = useCallback(() => {
    let alive = true
    setState((prev) => ({ ...prev, loading: true, error: null }))
    Promise.resolve()
      .then(() => fnRef.current())
      .then((data) => {
        if (alive) setState({ data, loading: false, error: null })
      })
      .catch((err) => {
        if (alive && err.name !== 'AbortError') {
          setState({ data: null, loading: false, error: err.message || String(err) })
        }
      })
    return () => {
      alive = false
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => run(), [run])

  return { ...state, reload: run }
}

export default useApi
