import type { Bundle } from '../data/types'
import { clock, compact } from '../lib/format'
import { useT } from '../lib/i18n'

export default function Hotspots({ bundle }: { bundle: Bundle }) {
  const { lang } = useT()
  const h = bundle.hotspots
  const replay = bundle.meta.replay ? `&replay=${bundle.meta.replay.date}` : ''
  const copy = () => {
    const txt = h.clusters.slice(0, 10).map(c =>
      `${c.rank}. ${c.label} (${c.state}) · ${c.n_fires} fires · ${c.frp_mw} MW · https://maps.google.com/?q=${c.lat},${c.lon}`).join('\n')
    navigator.clipboard?.writeText(`Dhuaan — top fire clusters by smoke impact (next 24 h)\n${txt}`)
  }
  return (
    <main className="mx-auto w-full max-w-4xl flex-1 overflow-y-auto px-4 py-5">
      <h1 className="text-2xl font-bold text-white">{lang === 'hi' ? 'सबसे ज़्यादा असर वाले आग क्लस्टर' : 'Fire clusters that matter most'}</h1>
      <p className="mt-1 text-sm text-gray-400">
        {lang === 'hi'
          ? 'हर आग बराबर नहीं। यह सूची बताती है कि अगले 24 घंटे में किन क्लस्टर का धुआँ सबसे ज़्यादा लोगों तक पहुँचेगा — मशीनें और टीमें पहले यहाँ भेजें।'
          : 'Not all fires are equal. Ranked by how many people their smoke will reach in the next 24 hours — send residue machinery and field teams here first.'}
      </p>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-line bg-panel p-3"><div className="text-2xl font-bold text-fire">{h.totals.fires_24h}</div><div className="text-xs text-gray-400">fires · 24 h</div></div>
        {Object.entries(h.totals.by_state).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([s, n]) => (
          <div key={s} className="rounded-xl border border-line bg-panel p-3"><div className="text-2xl font-bold text-white">{n}</div><div className="text-xs text-gray-400">{s}</div></div>
        ))}
        {h.top25_share_delhi_pct != null && (
          <div className="rounded-xl border border-line bg-panel p-3"><div className="text-2xl font-bold text-smoke-mod">{h.top25_share_delhi_pct}%</div>
            <div className="text-xs text-gray-400">{lang === 'hi' ? 'दिल्ली के धुएँ में शीर्ष 25 का हिस्सा' : "of Delhi's modelled smoke from the top 25"}</div></div>
        )}
      </div>
      <div className="mt-4 flex items-center justify-between">
        <span className="text-xs text-gray-500">Updated {clock(h.generated_at)}</span>
        <button onClick={copy} className="min-h-10 rounded-lg bg-white/10 px-3 text-sm">Copy top 10 as message</button>
      </div>
      <div className="mt-2 overflow-x-auto rounded-xl border border-line">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel text-xs text-gray-400">
            <tr><th className="p-2">#</th><th className="p-2">Cluster</th><th className="p-2">Fires</th><th className="p-2">FRP (MW)</th><th className="p-2">People-hours under smoke</th><th className="p-2"></th></tr>
          </thead>
          <tbody>
            {h.clusters.slice(0, 30).map(c => (
              <tr key={c.id} className="border-t border-line">
                <td className="p-2 text-gray-400">{c.rank}</td>
                <td className="p-2"><div className="font-medium text-white">{c.label}</div><div className="text-xs text-gray-500">{c.state}</div></td>
                <td className="p-2">{c.n_fires}</td>
                <td className="p-2">{c.frp_mw}</td>
                <td className="p-2">{c.impact_people_hours > 0 ? compact(c.impact_people_hours) : '—'}</td>
                <td className="p-2"><a className="text-violet-300 underline" href={`/?lat=${c.lat}&lon=${c.lon}${replay}`}>map</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-gray-500">Clusters are ~11 km cells named after the nearest district HQ. No individual farm or farmer is identified. Populations are approximate weights.</p>
    </main>
  )
}
