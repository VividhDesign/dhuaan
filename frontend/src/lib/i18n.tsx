import { createContext, useContext, useState, type ReactNode } from 'react'
import type { Lang, Level } from '../data/types'

const S = {
  tagline: { en: 'A weather forecast for smoke', hi: 'धुएँ का मौसम पूर्वानुमान' },
  updated: { en: 'Updated', hi: 'अपडेट' },
  lastPass: { en: 'last satellite pass', hi: 'आख़िरी सैटेलाइट पास' },
  fires24: { en: 'farm fires detected in 24 h', hi: 'पिछले 24 घंटे में खेतों की आग' },
  yourArea: { en: 'Your area', hi: 'आपका इलाक़ा' },
  useLocation: { en: 'Use my location', hi: 'मेरी लोकेशन' },
  search: { en: 'Search area, e.g. Rohini', hi: 'इलाक़ा खोजें, जैसे रोहिणी' },
  pickArea: { en: 'Pick your area to see when smoke will reach you.', hi: 'अपना इलाक़ा चुनें — देखें धुआँ कब पहुँचेगा।' },
  outside: { en: 'Outside the forecast area (Punjab–Haryana–Delhi NCR–west UP).', hi: 'यह जगह पूर्वानुमान क्षेत्र से बाहर है।' },
  next24: { en: 'Next 24 hours', hi: 'अगले 24 घंटे' },
  arrives: { en: 'Arrives', hi: 'पहुँचेगा' },
  clears: { en: 'Clears', hi: 'छँटेगा' },
  heaviest: { en: 'Heaviest', hi: 'सबसे घना' },
  comingFrom: { en: 'Coming from farm fires near', hi: 'इन जगहों के पास खेतों की आग से' },
  whatToDo: { en: 'What to do', hi: 'क्या करें' },
  getAlerts: { en: 'Get alerts before smoke arrives', hi: 'धुआँ आने से पहले अलर्ट पाएँ' },
  telegram: { en: 'Alerts on Telegram', hi: 'Telegram पर अलर्ट' },
  emailMe: { en: 'Email me', hi: 'ईमेल करें' },
  email: { en: 'your@email.com', hi: 'आपका ईमेल' },
  now: { en: 'Now', hi: 'अभी' },
  play: { en: 'Play', hi: 'चलाएँ' },
  pause: { en: 'Pause', hi: 'रोकें' },
  map: { en: 'Map', hi: 'नक्शा' },
  hotspots: { en: 'Hotspots', hi: 'हॉटस्पॉट' },
  replay: { en: 'Replay', hi: 'रीप्ले' },
  about: { en: 'About', hi: 'जानकारी' },
  relative: { en: 'Smoke Index is relative (0–100), not a PM2.5 reading.', hi: 'स्मोक इंडेक्स तुलनात्मक (0–100) है, PM2.5 माप नहीं।' },
  loading: { en: 'Loading the latest satellite fires…', hi: 'ताज़ा सैटेलाइट डेटा लोड हो रहा है…' },
  legendFire: { en: 'Fire (last 24 h)', hi: 'आग (24 घंटे)' },
  legendSmoke: { en: 'Smoke trail', hi: 'धुएँ की लकीर' },
} as const

export const LEVEL_TEXT: Record<Level, { en: string; hi: string }> = {
  none: { en: 'No smoke', hi: 'धुआँ नहीं' },
  light: { en: 'Light smoke', hi: 'हल्का धुआँ' },
  moderate: { en: 'Moderate smoke', hi: 'मध्यम धुआँ' },
  heavy: { en: 'Heavy smoke', hi: 'घना धुआँ' },
}
export const LEVEL_COLOR: Record<Level, string> = { none: '#22C55E', light: '#A3A3A3', moderate: '#8B5CF6', heavy: '#6D28D9' }

type Key = keyof typeof S
const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: (k: Key) => string }>({
  lang: 'en', setLang: () => {}, t: k => S[k].en,
})

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem('dhuaan.lang')
    if (saved === 'en' || saved === 'hi') return saved
  } catch { /* storage unavailable */ }
  return navigator.language?.startsWith('hi') ? 'hi' : 'en'
}

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang)
  const setLang = (l: Lang) => {
    setLangState(l)
    try { localStorage.setItem('dhuaan.lang', l) } catch { /* ignore */ }
    document.documentElement.lang = l
  }
  return <Ctx.Provider value={{ lang, setLang, t: k => S[k][lang] }}>{children}</Ctx.Provider>
}

export const useT = () => useContext(Ctx)
