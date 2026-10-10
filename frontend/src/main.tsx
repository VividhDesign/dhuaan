import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import Header from './components/Header'
import LiveMap from './pages/LiveMap'
import Hotspots from './pages/Hotspots'
import About from './pages/About'
import { LangProvider, useT } from './lib/i18n'
import { useBundle } from './data/useBundle'

function App() {
  const { bundle, frames, error } = useBundle()
  const { t } = useT()
  return (
    <div className="flex h-full flex-col">
      <Header />
      {error && <div className="m-4 rounded-lg border border-red-800 bg-red-950 p-3 text-sm">Couldn't load the forecast: {error}</div>}
      {!bundle && !error && <div className="flex flex-1 items-center justify-center text-sm text-gray-400">{t('loading')}</div>}
      {bundle && (
        <Routes>
          <Route path="/" element={<LiveMap bundle={bundle} frames={frames} />} />
          <Route path="/hotspots" element={<Hotspots bundle={bundle} />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<LiveMap bundle={bundle} frames={frames} />} />
        </Routes>
      )}
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LangProvider><BrowserRouter><App /></BrowserRouter></LangProvider>
  </StrictMode>,
)
