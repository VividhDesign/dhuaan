import type { Level, Meta, PlaceForecast, Smoke } from '../data/types'

export function decodeFrames(smoke: Smoke): Uint8Array[] {
  return smoke.frames.map(b64 => Uint8Array.from(atob(b64), c => c.charCodeAt(0)))
}

/** Bilinear sample of every frame at lat/lon; null if outside the forecast grid. */
export function sampleSeries(smoke: Smoke, frames: Uint8Array[], lat: number, lon: number): number[] | null {
  const g = smoke.grid
  const fx = (lon - g.lon0) / g.dlon
  const fy = (lat - g.lat0) / g.dlat
  if (fx < 0 || fy < 0 || fx > g.nx - 1 || fy > g.ny - 1) return null
  const ix = Math.min(Math.floor(fx), g.nx - 2), iy = Math.min(Math.floor(fy), g.ny - 2)
  const ax = fx - ix, ay = fy - iy
  return frames.map(f => {
    const v = (j: number, i: number) => f[j * g.nx + i]
    return (v(iy, ix) * (1 - ax) + v(iy, ix + 1) * ax) * (1 - ay) + (v(iy + 1, ix) * (1 - ax) + v(iy + 1, ix + 1) * ax) * ay
  })
}

export function levelOf(index: number, lv: Meta['levels']): Level {
  if (index >= lv.heavy) return 'heavy'
  if (index >= lv.moderate) return 'moderate'
  if (index >= lv.light) return 'light'
  return 'none'
}

export interface Summary { level_24h: Level; arrival: number | null; clears: number | null; peak: { t: number; index: number }; series: number[] }

/** Same rules as engine/receptors.py summarize_series. */
export function summarize(series: number[], times: number[], lv: Meta['levels']): Summary {
  const s = series.map(x => Math.max(0, Math.min(100, Math.round(x))))
  const above = s.map(x => x >= lv.moderate)
  let arrival: number | null = null, clears: number | null = null
  if (above.some(Boolean)) {
    let bestLen = 0, bestStart = 0, runStart: number | null = null
    ;[...above, false].forEach((a, k) => {
      if (a && runStart === null) runStart = k
      else if (!a && runStart !== null) { if (k - runStart > bestLen) { bestLen = k - runStart; bestStart = runStart } runStart = null }
    })
    arrival = times[above.indexOf(true)]
    const end = bestStart + bestLen
    clears = end < times.length ? times[end] : null
  }
  const kPeak = s.indexOf(Math.max(...s))
  const max24 = Math.max(...s.slice(0, Math.min(25, s.length)))
  return { level_24h: levelOf(max24, lv), arrival, clears, peak: { t: times[kPeak], index: s[kPeak] }, series: s }
}

export function km(lat1: number, lon1: number, lat2: number, lon2: number) {
  const r = Math.PI / 180, dLat = (lat2 - lat1) * r, dLon = (lon2 - lon1) * r
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(dLon / 2) ** 2
  return 12742 * Math.asin(Math.sqrt(a))
}

export function nearestPlace(places: PlaceForecast[], lat: number, lon: number) {
  let best = places[0], d = Infinity
  for (const p of places) { const dk = km(lat, lon, p.lat, p.lon); if (dk < d) { d = dk; best = p } }
  return { place: best, km: d }
}
