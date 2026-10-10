import { useRef, useState } from 'react'
import type { Bulletin } from '../data/types'
import { audioUrl } from '../data/client'
import { useT } from '../lib/i18n'

export default function BulletinCard({ bulletin }: { bulletin: Bulletin | null }) {
  const { lang } = useT()
  const audio = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState<'hi' | 'en' | null>(null)
  if (!bulletin) return null
  const play = (l: 'hi' | 'en') => {
    const url = audioUrl(l === 'hi' ? bulletin.audio_hi : bulletin.audio_en)
    if (!url) return
    if (playing === l) { audio.current?.pause(); setPlaying(null); return }
    audio.current?.pause()
    audio.current = new Audio(url)
    audio.current.onended = () => setPlaying(null)
    audio.current.play().then(() => setPlaying(l)).catch(() => setPlaying(null))
  }
  const hasAudio = !!audioUrl(bulletin.audio_hi)
  return (
    <section className="rounded-xl border border-line bg-ink/60 p-3" aria-label="Bulletin">
      <h3 className="mb-1 text-sm font-semibold text-white">{lang === 'hi' ? '📻 आज का धुआँ बुलेटिन' : '📻 Smoke bulletin'}</h3>
      <p className="text-sm leading-relaxed text-gray-300" lang={lang}>{bulletin[lang]}</p>
      {hasAudio && (
        <div className="mt-2 flex gap-2">
          <button onClick={() => play('hi')} className="min-h-10 rounded-lg bg-white/10 px-3 text-sm font-medium">{playing === 'hi' ? '❚❚' : '🔊'} हिंदी में सुनें</button>
          <button onClick={() => play('en')} className="min-h-10 rounded-lg bg-white/10 px-3 text-sm font-medium">{playing === 'en' ? '❚❚' : '🔊'} Listen in English</button>
        </div>
      )}
    </section>
  )
}
