import { NavLink } from 'react-router-dom'
import { useT } from '../lib/i18n'

export default function Header() {
  const { t, lang, setLang } = useT()
  const link = ({ isActive }: { isActive: boolean }) =>
    `px-2.5 py-1.5 rounded-md text-sm ${isActive ? 'bg-white/10 text-white' : 'text-gray-400 hover:text-white'}`
  return (
    <header className="relative z-20 flex items-center justify-between gap-2 border-b border-line bg-ink/95 px-3 py-2 backdrop-blur">
      <NavLink to="/" className="flex items-baseline gap-2">
        <span className="text-lg font-bold text-white">💨 Dhuaan</span>
        <span className="hidden text-xs text-gray-400 sm:inline">{t('tagline')}</span>
      </NavLink>
      <nav className="flex items-center gap-1">
        <NavLink to="/" end className={link}>{t('map')}</NavLink>
        <NavLink to="/hotspots" className={link}>{t('hotspots')}</NavLink>
        <NavLink to="/about" className={link}>{t('about')}</NavLink>
        <button onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
          className="ml-1 min-h-9 rounded-md border border-line px-2 text-sm text-gray-200" aria-label="Language">
          {lang === 'en' ? 'हिं' : 'EN'}
        </button>
      </nav>
    </header>
  )
}
