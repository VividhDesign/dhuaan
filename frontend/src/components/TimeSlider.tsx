import { useEffect, useRef } from 'react'
import { shortTime } from '../lib/format'
import { useT } from '../lib/i18n'

interface Props { start: number; end: number; value: number; playing: boolean; onChange: (t: number) => void; onToggle: () => void }

const STEP = 15 * 60 // animation advances 15 min per tick

export default function TimeSlider({ start, end, value, playing, onChange, onToggle }: Props) {
  const { t, lang } = useT()
  const v = useRef(value)
  v.current = value
  useEffect(() => {
    if (!playing) return
    const id = window.setInterval(() => {
      const next = v.current + STEP
      onChange(next > end ? start : next)
    }, 110)
    return () => window.clearInterval(id)
  }, [playing, start, end, onChange])

  const hours = Math.round((value - start) / 3600)
  return (
    <div className="flex items-center gap-3 rounded-xl border border-line bg-panel/95 px-3 py-2 shadow-xl backdrop-blur">
      <button onClick={onToggle} aria-label={playing ? t('pause') : t('play')}
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-smoke-mod text-lg font-bold text-white">
        {playing ? '❚❚' : '▶'}
      </button>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex justify-between text-xs text-gray-300">
          <span className="font-semibold text-white">{shortTime(value, lang)}</span>
          <span>{hours === 0 ? t('now') : `+${hours} h`}</span>
        </div>
        <input type="range" min={start} max={end} step={STEP} value={value} aria-label="Forecast time"
          onChange={e => onChange(Number(e.target.value))} className="w-full accent-[#8B5CF6]" />
      </div>
    </div>
  )
}
