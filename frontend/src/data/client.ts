import type { Advice, Bulletin, Bundle, FiresGeo, Hotspots, Meta, PlaceForecast, Smoke, Trails } from './types'

export const DATA_URL = (import.meta.env.VITE_DATA_URL as string | undefined) || '/samples/latest'
export const API_URL = (import.meta.env.VITE_API_URL as string | undefined) || ''
export const TG_BOT = (import.meta.env.VITE_TG_BOT as string | undefined) || ''
export const MAP_STYLE_URL = (import.meta.env.VITE_MAP_STYLE_URL as string | undefined) ||
  'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'

export const REPLAY_URL = DATA_URL.replace(/\/latest$/, '/replay')

export function replayDate(): string | null {
  const d = new URLSearchParams(location.search).get('replay')
  return d && /^\d{4}-\d{2}-\d{2}$/.test(d) ? d : null
}

async function get<T>(name: string, base = DATA_URL): Promise<T> {
  const r = await fetch(`${base}/${name}`, { cache: 'no-cache' })
  if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`)
  return r.json() as Promise<T>
}

export async function loadBundle(replay: string | null = null): Promise<Bundle> {
  const base = replay ? `${REPLAY_URL}/${replay}` : DATA_URL
  const [meta, fires, trails, smoke, places, hotspots, advice] = await Promise.all([
    get<Meta>('meta.json', base), get<FiresGeo>('fires.geojson', base), get<Trails>('trails.json', base),
    get<Smoke>('smoke.json', base), get<PlaceForecast[]>('places.json', base), get<Hotspots>('hotspots.json', base),
    get<Advice>('advice.json', base),
  ])
  const bulletin = await get<Bulletin>('bulletin.json', base).catch(() => null)
  return { meta, fires, trails, smoke, places, hotspots, advice, bulletin }
}

export function audioUrl(rel?: string | null): string | null {
  if (!rel) return null
  if (/^https?:/.test(rel)) return rel
  return API_URL ? `${API_URL}${rel}` : null
}

export async function searchPlaces(q: string, local: PlaceForecast[]): Promise<{ label: string; lat: number; lon: number }[]> {
  const s = q.trim().toLowerCase()
  const fromLocal = local
    .filter(p => p.name.en.toLowerCase().includes(s) || p.name.hi.includes(q.trim()) || p.id.includes(s))
    .map(p => ({ label: p.name.en, lat: p.lat, lon: p.lon }))
  if (!API_URL || s.length < 2) return fromLocal.slice(0, 5)
  try {
    const r = await fetch(`${API_URL}/api/places?q=${encodeURIComponent(q)}`)
    if (!r.ok) throw new Error(String(r.status))
    const j = await r.json() as { results: { label: string; lat: number; lon: number }[] }
    return [...fromLocal.slice(0, 2), ...j.results].slice(0, 6)
  } catch {
    return fromLocal.slice(0, 5)
  }
}

export async function subscribeEmail(body: { email: string; lat: number; lon: number; lang: string; role: string }) {
  const r = await fetch(`${API_URL}/api/subscribe/email`, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
  })
  const j = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error((j as { error?: string }).error || `HTTP ${r.status}`)
  return j as { ok: boolean; message: string }
}
