import { useMemo, useState } from 'react'
import type { Bundle } from '../data/types'
import { API_URL, TG_BOT, searchPlaces, subscribeEmail } from '../data/client'
import { nearestPlace, sampleSeries, summarize } from '../lib/frames'
import { hourLabel } from '../lib/format'
import { LEVEL_COLOR, LEVEL_TEXT, useT } from '../lib/i18n'

const CHIPS = ['rohini', 'south_delhi', 'gurugram', 'noida', 'ludhiana', 'chandigarh', 'patiala', 'panipat']

interface Props {
  bundle: Bundle
  frames: Uint8Array[]
  selected: { lat: number; lon: number; label?: string } | null
  onSelect: (s: { lat: number; lon: number; label?: string }) => void
}

function Sparkline({ series, color }: { series: number[]; color: string }) {
  const w = 280, h = 44, n = series.length
  const pts = series.map((v, i) => `${(i / (n - 1)) * w},${h - (Math.min(v, 100) / 100) * h}`).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-11" aria-hidden>
      <line x1="0" x2={w} y1={h - 0.35 * h} y2={h - 0.35 * h} stroke="#334155" strokeDasharray="3 3" />
      <polyline points={`0,${h} ${pts} ${w},${h}`} fill={color} fillOpacity="0.18" stroke="none" />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" />
    </svg>
  )
}

export default function AreaCard({ bundle, frames, selected, onSelect }: Props) {
  const { t, lang } = useT()
  const [q, setQ] = useState('')
  const [results, setResults] = useState<{ label: string; lat: number; lon: number }[]>([])
  const [locating, setLocating] = useState(false)
  const [email, setEmail] = useState('')
  const [emailMsg, setEmailMsg] = useState<string | null>(null)

  const fc = useMemo(() => {
    if (!selected) return null
    const series = sampleSeries(bundle.smoke, frames, selected.lat, selected.lon)
    if (!series) return { outside: true as const }
    const s = summarize(series, bundle.smoke.times, bundle.meta.levels)
    const near = nearestPlace(bundle.places, selected.lat, selected.lon)
    return { outside: false as const, ...s, near, sources: near.km <= 40 ? near.place.sources : [] }
  }, [selected, bundle, frames])

  const locate = () => {
    if (!navigator.geolocation) return
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      p => { setLocating(false); onSelect({ lat: p.coords.latitude, lon: p.coords.longitude }) },
      () => setLocating(false), { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 })
  }

  const doSearch = async (value: string) => {
    setQ(value)
    setResults(value.trim().length >= 2 ? await searchPlaces(value, bundle.places) : [])
  }

  const name = selected?.label || (fc && !fc.outside && fc.near.km <= 25 ? fc.near.place.name[lang] : null)

  return (
    <section className="flex flex-col gap-3" aria-label={t('yourArea')}>
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white">{t('yourArea')}{name ? ` · ${name}` : ''}</h2>
        <button onClick={locate} className="min-h-11 rounded-lg bg-white/10 px-3 text-sm font-medium hover:bg-white/15">
          📍 {locating ? '…' : t('useLocation')}
        </button>
      </div>

      <div className="relative">
        <input value={q} onChange={e => doSearch(e.target.value)} placeholder={t('search')}
          className="w-full min-h-11 rounded-lg border border-line bg-ink px-3 text-sm outline-none focus:border-smoke-mod" />
        {results.length > 0 && (
          <ul className="absolute z-10 mt-1 w-full overflow-hidden rounded-lg border border-line bg-panel shadow-xl">
            {results.map(r => (
              <li key={`${r.label}${r.lat}`}>
                <button className="w-full px-3 py-2.5 text-left text-sm hover:bg-white/10"
                  onClick={() => { onSelect(r); setResults([]); setQ(r.label) }}>{r.label}</button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none]">
        {CHIPS.map(id => bundle.places.find(p => p.id === id)).filter(Boolean).map(p => (
          <button key={p!.id} onClick={() => onSelect({ lat: p!.lat, lon: p!.lon, label: p!.name[lang] })}
            className="shrink-0 rounded-full border border-line px-3 py-1.5 text-xs text-gray-300 hover:border-gray-400">
            {p!.name[lang].split(',')[0]}
          </button>
        ))}
      </div>

      {!fc && <p className="text-sm text-gray-400">{t('pickArea')}</p>}
      {fc?.outside && <p className="text-sm text-gray-400">{t('outside')}</p>}
      {fc && !fc.outside && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <span className="h-3 w-3 shrink-0 rounded-full" style={{ background: LEVEL_COLOR[fc.level_24h] }} />
            <div>
              <div className="text-xl font-bold text-white">{LEVEL_TEXT[fc.level_24h][lang]}</div>
              <div className="text-xs text-gray-400">{t('next24')}</div>
            </div>
          </div>
          {fc.arrival && (
            <dl className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg bg-ink p-2"><dt className="text-[11px] text-gray-400">{t('arrives')}</dt><dd className="text-sm font-semibold">{hourLabel(fc.arrival, lang)}</dd></div>
              <div className="rounded-lg bg-ink p-2"><dt className="text-[11px] text-gray-400">{t('heaviest')}</dt><dd className="text-sm font-semibold">{hourLabel(fc.peak.t, lang)}</dd></div>
              <div className="rounded-lg bg-ink p-2"><dt className="text-[11px] text-gray-400">{t('clears')}</dt><dd className="text-sm font-semibold">{fc.clears ? hourLabel(fc.clears, lang) : '36 h+'}</dd></div>
            </dl>
          )}
          <Sparkline series={fc.series} color={LEVEL_COLOR[fc.level_24h === 'none' ? 'light' : fc.level_24h]} />
          {fc.sources.length > 0 && fc.level_24h !== 'none' && (
            <p className="text-sm text-gray-300">{t('comingFrom')}: {fc.sources.map(s => `${s.label} ${s.pct}%`).join(' · ')}</p>
          )}
          <div>
            <h3 className="mb-1 text-sm font-semibold text-white">{t('whatToDo')}</h3>
            <ul className="list-disc space-y-1 pl-5 text-sm text-gray-300">
              {bundle.advice.resident[fc.level_24h][lang].map(a => <li key={a}>{a}</li>)}
            </ul>
          </div>
        </div>
      )}

      <div className="mt-1 rounded-xl border border-line bg-ink/60 p-3">
        <h3 className="mb-2 text-sm font-semibold text-white">🔔 {t('getAlerts')}</h3>
        {TG_BOT && (
          <a href={`https://t.me/${TG_BOT}?start=web`} target="_blank" rel="noreferrer"
            className="mb-2 flex min-h-11 items-center justify-center rounded-lg bg-[#229ED9] text-sm font-semibold text-white">
            {t('telegram')}
          </a>
        )}
        {API_URL && selected && !fc?.outside && (
          <form className="flex gap-2" onSubmit={async e => {
            e.preventDefault()
            try {
              const r = await subscribeEmail({ email, lat: selected.lat, lon: selected.lon, lang, role: 'resident' })
              setEmailMsg(r.message)
            } catch (err) { setEmailMsg(String((err as Error).message)) }
          }}>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder={t('email')}
              className="min-h-11 min-w-0 flex-1 rounded-lg border border-line bg-ink px-3 text-sm outline-none" />
            <button className="min-h-11 rounded-lg bg-white/10 px-3 text-sm font-medium">{t('emailMe')}</button>
          </form>
        )}
        {emailMsg && <p className="mt-2 text-xs text-gray-300">{emailMsg}</p>}
      </div>
      <p className="text-[11px] text-gray-500">{t('relative')}</p>
    </section>
  )
}
