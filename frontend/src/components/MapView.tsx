import { useEffect, useMemo, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource, ImageSource, Map as MLMap, MapMouseEvent } from 'maplibre-gl'
import type * as GeoJSON from 'geojson'
import type { Bundle } from '../data/types'
import { MAP_STYLE_URL } from '../data/client'
import { levelOf } from '../lib/frames'
import { LEVEL_COLOR } from '../lib/i18n'

const TRAIL_HOURS = 3

/** Pre-render each Smoke Index frame to a tiny PNG (one pixel per 0.1° cell). */
function frameImages(b: Bundle, frames: Uint8Array[]): string[] {
  const { nx, ny } = b.smoke.grid
  const c = document.createElement('canvas')
  c.width = nx; c.height = ny
  const ctx = c.getContext('2d')!
  return frames.map(f => {
    const img = ctx.createImageData(nx, ny)
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const v = f[j * nx + i], o = ((ny - 1 - j) * nx + i) * 4 // row 0 of the frame is the south edge
      const k = Math.min(1, v / 70)
      img.data[o] = 150 - 40 * k; img.data[o + 1] = 140 - 80 * k; img.data[o + 2] = 170 + 60 * k
      img.data[o + 3] = v < 6 ? 0 : Math.round(60 + 150 * k)
    }
    ctx.putImageData(img, 0, 0)
    return c.toDataURL('image/png')
  })
}

function imageCoords(b: Bundle): [[number, number], [number, number], [number, number], [number, number]] {
  const g = b.smoke.grid
  const w = g.lon0 - g.dlon / 2, e = g.lon0 + (g.nx - 0.5) * g.dlon
  const s = g.lat0 - g.dlat / 2, n = g.lat0 + (g.ny - 0.5) * g.dlat
  return [[w, n], [e, n], [e, s], [w, s]]
}

/** TripsLayer-style trails: the last few hours of each puff's path up to time t. */
function trailsAt(b: Bundle, t: number) {
  const lines: GeoJSON.Feature[] = [], heads: GeoJSON.Feature[] = []
  const t0 = t - TRAIL_HOURS * 3600
  for (const tr of b.trails.paths) {
    const p = tr.path
    if (p.length < 2 || p[0][2] > t || p[p.length - 1][2] < t0) continue
    const coords: [number, number][] = []
    for (let k = 0; k < p.length; k++) {
      const [lo, la, tk] = p[k]
      if (tk < t0) continue
      if (tk > t) {
        const [plo, pla, ptk] = p[k - 1] ?? p[k]
        const a = tk === ptk ? 0 : (t - ptk) / (tk - ptk)
        coords.push([plo + (lo - plo) * a, pla + (la - pla) * a])
        break
      }
      coords.push([lo, la])
    }
    if (coords.length >= 2) {
      lines.push({ type: 'Feature', properties: { w: tr.w }, geometry: { type: 'LineString', coordinates: coords } })
      heads.push({ type: 'Feature', properties: { w: tr.w }, geometry: { type: 'Point', coordinates: coords[coords.length - 1] } })
    }
  }
  return { lines: { type: 'FeatureCollection', features: lines } as GeoJSON.FeatureCollection,
    heads: { type: 'FeatureCollection', features: heads } as GeoJSON.FeatureCollection }
}

function placesAt(b: Bundle, k: number, lang: 'en' | 'hi'): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: b.places.map(p => ({
      type: 'Feature', properties: { name: p.name[lang], color: LEVEL_COLOR[levelOf(p.series[k] ?? 0, b.meta.levels)] },
      geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
    })),
  }
}

interface Props {
  bundle: Bundle
  frames: Uint8Array[]
  time: number
  lang: 'en' | 'hi'
  selected: { lat: number; lon: number } | null
  onPick: (lat: number, lon: number) => void
}

export default function MapView({ bundle, frames, time, lang, selected, onPick }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<MLMap | null>(null)
  const ready = useRef(false)
  const images = useMemo(() => frameImages(bundle, frames), [bundle, frames])
  const pickRef = useRef(onPick)
  pickRef.current = onPick
  const selectedRef = useRef(selected)
  selectedRef.current = selected
  const frameIdx = Math.max(0, Math.min(bundle.smoke.times.length - 1, Math.round((time - bundle.smoke.times[0]) / 3600)))

  useEffect(() => {
    if (!el.current) return
    const m = new maplibregl.Map({
      container: el.current, style: MAP_STYLE_URL, center: [76.4, 29.9], zoom: 6.2, minZoom: 4.5, maxZoom: 12,
      attributionControl: { compact: true }, dragRotate: false, pitchWithRotate: false,
    })
    m.touchZoomRotate.disableRotation()
    // on phones the bottom sheet covers the lower half: keep the map's focus above it
    if (window.innerWidth < 768) m.setPadding({ top: 40, bottom: Math.round(window.innerHeight * 0.42), left: 0, right: 0 })
    map.current = m
    if (import.meta.env.DEV) (window as unknown as { __map: MLMap }).__map = m
    m.on('load', () => {
      m.addSource('smoke', { type: 'image', url: images[frameIdx], coordinates: imageCoords(bundle) })
      m.addLayer({ id: 'smoke', type: 'raster', source: 'smoke', paint: { 'raster-opacity': 0.85, 'raster-resampling': 'linear', 'raster-fade-duration': 0 } })
      const tr = trailsAt(bundle, time)
      m.addSource('trails', { type: 'geojson', data: tr.lines })
      m.addLayer({ id: 'trails', type: 'line', source: 'trails', layout: { 'line-cap': 'round' },
        paint: { 'line-color': '#C4B5FD', 'line-width': 1.4, 'line-opacity': ['interpolate', ['linear'], ['get', 'w'], 0, 0.15, 1, 0.7] } })
      m.addSource('heads', { type: 'geojson', data: tr.heads })
      m.addLayer({ id: 'heads', type: 'circle', source: 'heads',
        paint: { 'circle-radius': 1.8, 'circle-color': '#EDE9FE', 'circle-opacity': ['interpolate', ['linear'], ['get', 'w'], 0, 0.3, 1, 0.9] } })
      m.addSource('fires', { type: 'geojson', data: bundle.fires as GeoJSON.FeatureCollection })
      m.addLayer({ id: 'fires-glow', type: 'circle', source: 'fires',
        paint: { 'circle-radius': ['interpolate', ['linear'], ['sqrt', ['get', 'frp']], 0, 4, 10, 14], 'circle-color': '#F97316', 'circle-opacity': 0.18, 'circle-blur': 1 } })
      m.addLayer({ id: 'fires', type: 'circle', source: 'fires',
        paint: { 'circle-radius': ['interpolate', ['linear'], ['sqrt', ['get', 'frp']], 0, 1.5, 10, 4.5], 'circle-color': '#FB923C', 'circle-stroke-color': '#FED7AA', 'circle-stroke-width': 0.5 } })
      m.addSource('places', { type: 'geojson', data: placesAt(bundle, frameIdx, lang) })
      m.addLayer({ id: 'places', type: 'circle', source: 'places',
        paint: { 'circle-radius': 5, 'circle-color': ['get', 'color'], 'circle-stroke-color': '#0B0F14', 'circle-stroke-width': 1.5 } })
      m.addLayer({ id: 'place-labels', type: 'symbol', source: 'places', minzoom: 6.5,
        layout: { 'text-field': ['get', 'name'], 'text-size': 11, 'text-offset': [0, 1.1], 'text-anchor': 'top', 'text-font': ['Open Sans Regular', 'Noto Sans Regular'] },
        paint: { 'text-color': '#D1D5DB', 'text-halo-color': '#0B0F14', 'text-halo-width': 1.2 } })
      m.addSource('selected', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'selected', type: 'circle', source: 'selected',
        paint: { 'circle-radius': 8, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': '#F9FAFB', 'circle-stroke-width': 2.5 } })
      ready.current = true
      const sel = selectedRef.current
      if (sel) {
        ;(m.getSource('selected') as GeoJSONSource).setData({ type: 'FeatureCollection', features: [
          { type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: [sel.lon, sel.lat] } }] })
        m.easeTo({ center: [sel.lon, sel.lat], zoom: 7, duration: 800 })
      }
    })
    m.on('click', (e: MapMouseEvent) => pickRef.current(e.lngLat.lat, e.lngLat.lng))
    // the container gets its real size after layout; keep the canvas in sync
    const ro = new ResizeObserver(() => m.resize())
    ro.observe(el.current)
    return () => { ro.disconnect(); ready.current = false; m.remove(); map.current = null }
    // the map is created once per data bundle; per-frame updates happen below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bundle, images])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    ;(m.getSource('smoke') as ImageSource | undefined)?.updateImage({ url: images[frameIdx], coordinates: imageCoords(bundle) })
    ;(m.getSource('places') as GeoJSONSource | undefined)?.setData(placesAt(bundle, frameIdx, lang))
  }, [frameIdx, images, bundle, lang])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const tr = trailsAt(bundle, time)
    ;(m.getSource('trails') as GeoJSONSource | undefined)?.setData(tr.lines)
    ;(m.getSource('heads') as GeoJSONSource | undefined)?.setData(tr.heads)
  }, [time, bundle])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    ;(m.getSource('selected') as GeoJSONSource | undefined)?.setData({
      type: 'FeatureCollection',
      features: selected ? [{ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: [selected.lon, selected.lat] } }] : [],
    })
    if (selected) m.easeTo({ center: [selected.lon, selected.lat], zoom: Math.max(m.getZoom(), 7), duration: 600 })
  }, [selected])

  return <div className="absolute inset-0"><div ref={el} className="h-full w-full" aria-label="Smoke forecast map" /></div>
}
