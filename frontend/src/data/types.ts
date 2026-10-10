export type Level = 'none' | 'light' | 'moderate' | 'heavy'
export type Lang = 'en' | 'hi'
export type Bi = { en: string; hi: string }

export interface Meta {
  run_id: string
  generated_at: number
  last_pass_utc: number | null
  wind_source: string
  fires_24h: number
  clusters: number
  levels: { light: number; moderate: number; heavy: number }
  version: string
  replay?: { date: string; hour_utc: number }
}

export interface FireProps { frp: number; t: number; sat: string; conf: string; cluster: string | null }
export interface FiresGeo {
  type: 'FeatureCollection'
  features: { type: 'Feature'; geometry: { type: 'Point'; coordinates: [number, number] }; properties: FireProps }[]
}

export interface Trail { cluster: string; w: number; path: [number, number, number][] }
export interface Trails { t_start: number; t_end: number; paths: Trail[] }

export interface Smoke {
  grid: { lon0: number; lat0: number; dlon: number; dlat: number; nx: number; ny: number }
  times: number[]
  frames: string[]
}

export interface Source { label: string; state: string; pct: number }
export interface PlaceForecast {
  id: string
  name: Bi
  lat: number
  lon: number
  delhi: boolean
  series: number[]
  level_24h: Level
  arrival: number | null
  clears: number | null
  peak: { t: number; index: number }
  sources: Source[]
}

export interface Cluster {
  id: string; rank: number; lat: number; lon: number; label: string; district: string; state: string
  n_fires: number; frp_mw: number; first_seen: number; last_seen: number; repeat: boolean; impact_people_hours: number
}
export interface Hotspots {
  generated_at: number
  totals: { fires_24h: number; by_state: Record<string, number> }
  top25_share_delhi_pct: number | null
  clusters: Cluster[]
}

export type Advice = Record<'resident' | 'school' | 'official', Record<Level, { en: string[]; hi: string[] }>>

export interface Bundle {
  meta: Meta
  fires: FiresGeo
  trails: Trails
  smoke: Smoke
  places: PlaceForecast[]
  hotspots: Hotspots
  advice: Advice
}
