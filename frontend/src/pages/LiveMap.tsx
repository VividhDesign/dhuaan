import { useCallback, useState } from 'react'
import type { Bundle } from '../data/types'
import MapView from '../components/MapView'
import AreaCard from '../components/AreaCard'
import TimeSlider from '../components/TimeSlider'
import { clock } from '../lib/format'
import { useT } from '../lib/i18n'

function initialSelected(): { lat: number; lon: number } | null {
  const q = new URLSearchParams(location.search)
  const lat = Number(q.get('lat')), lon = Number(q.get('lon'))
  return q.has('lat') && Number.isFinite(lat) && Number.isFinite(lon) ? { lat, lon } : null
}

export default function LiveMap({ bundle, frames }: { bundle: Bundle; frames: Uint8Array[] }) {
  const { t, lang } = useT()
  const times = bundle.smoke.times
  const [time, setTime] = useState(times[0])
  const [playing, setPlaying] = useState(false)
  const [selected, setSelected] = useState<{ lat: number; lon: number; label?: string } | null>(initialSelected)
  const [sheetOpen, setSheetOpen] = useState(true)
  const onTime = useCallback((v: number) => setTime(v), [])
  const m = bundle.meta

  return (
    <div className="relative flex-1 overflow-hidden">
      <MapView bundle={bundle} frames={frames} time={time} lang={lang} selected={selected}
        onPick={(lat, lon) => { setSelected({ lat, lon }); setSheetOpen(true) }} />

      <div className="pointer-events-none absolute left-3 top-3 z-10 max-w-[75%] rounded-lg bg-ink/80 px-3 py-2 text-[11px] text-gray-300 backdrop-blur sm:text-xs">
        <div><span className="text-base font-bold text-fire">🔥 {m.fires_24h}</span> {t('fires24')}</div>
        <div className="mt-0.5 text-gray-400">{t('updated')} {clock(m.generated_at)}{m.last_pass_utc ? ` · ${t('lastPass')} ${clock(m.last_pass_utc)}` : ''}</div>
        <div className="mt-1 flex gap-3 text-gray-400">
          <span><span className="inline-block h-2 w-2 rounded-full bg-fire" /> {t('legendFire')}</span>
          <span><span className="inline-block h-0.5 w-4 bg-violet-300 align-middle" /> {t('legendSmoke')}</span>
        </div>
      </div>

      {/* desktop side panel / mobile bottom sheet */}
      <aside className={`absolute z-10 overflow-y-auto border-line bg-panel/95 p-4 shadow-2xl backdrop-blur
        inset-x-0 bottom-0 max-h-[48%] rounded-t-2xl border-t transition-transform
        md:inset-y-3 md:left-auto md:right-3 md:bottom-auto md:max-h-[calc(100%-6.5rem)] md:w-[380px] md:rounded-2xl md:border
        ${sheetOpen ? '' : 'translate-y-[calc(100%-3.25rem)] md:translate-y-0'}`}>
        <button className="mx-auto mb-2 block h-1.5 w-12 rounded-full bg-gray-600 md:hidden" aria-label="Toggle panel"
          onClick={() => setSheetOpen(o => !o)} />
        <AreaCard bundle={bundle} frames={frames} selected={selected} onSelect={s => { setSelected(s); setSheetOpen(true) }} />
      </aside>

      <div className={`absolute left-3 right-3 z-10 md:left-3 md:right-[400px] md:bottom-3 ${sheetOpen ? 'bottom-[calc(48%+0.5rem)] md:bottom-3' : 'bottom-16'}`}>
        <TimeSlider start={times[0]} end={times[times.length - 1]} value={time} playing={playing}
          onChange={onTime} onToggle={() => setPlaying(p => !p)} />
      </div>
    </div>
  )
}
