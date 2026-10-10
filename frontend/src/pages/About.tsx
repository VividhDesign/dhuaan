import { useT } from '../lib/i18n'

const STEPS = {
  en: [
    ['🛰️ Satellites see the fires', 'NASA’s VIIRS instruments on three satellites detect active fires several times a day (FIRMS). We drop low-confidence points and known industrial flares, merge duplicates, and group fires into ~11 km clusters.'],
    ['🌬️ Wind carries the smoke', 'Every 3 hours we pull the hourly wind forecast at ~750 m (925 hPa) for a 0.5° grid over Punjab, Haryana, Delhi and west UP, plus the boundary-layer height.'],
    ['🧭 We follow each plume', 'Each cluster releases a puff every hour for 6 hours. Each puff is moved forward through the wind field (RK2, 15-minute steps) for up to 36 hours — the same idea as NOAA’s HYSPLIT, simplified.'],
    ['📍 Smoke Index for your area', 'Puffs spread and fade with age (Gaussian plume, 24 h e-folding). Summing them gives a relative Smoke Index (0–100) for every 0.1° cell and hour; a shallow night-time mixing layer raises it because smoke gets trapped.'],
    ['🔔 Warn people, target help', 'If your area will reach “moderate” in the next 24 h you get a message before it arrives. Clusters are ranked by people-hours under smoke so help goes where it matters most.'],
  ],
  hi: [
    ['🛰️ सैटेलाइट आग देखते हैं', 'NASA के तीन सैटेलाइट (VIIRS) दिन में कई बार सक्रिय आग पहचानते हैं। कम भरोसे वाले बिंदु और फ़ैक्टरी की लपटें हटाकर, आग को ~11 किमी के क्लस्टर में जोड़ते हैं।'],
    ['🌬️ हवा धुआँ ले जाती है', 'हर 3 घंटे में पंजाब, हरियाणा, दिल्ली और पश्चिमी UP के ऊपर ~750 मीटर ऊँचाई की हवा का घंटेवार पूर्वानुमान लेते हैं।'],
    ['🧭 हर धुएँ का रास्ता', 'हर क्लस्टर 6 घंटे तक हर घंटे धुएँ का एक "पफ़" छोड़ता है, जिसे हवा के साथ 36 घंटे तक आगे बढ़ाया जाता है (NOAA के HYSPLIT जैसा, सरल रूप)।'],
    ['📍 आपके इलाक़े का स्मोक इंडेक्स', 'पफ़ समय के साथ फैलते और हल्के होते हैं। इन्हें जोड़कर हर 0.1° और हर घंटे का तुलनात्मक स्मोक इंडेक्स (0–100) बनता है।'],
    ['🔔 चेतावनी और मदद', 'अगर अगले 24 घंटे में आपके इलाक़े में "मध्यम" धुआँ आने वाला है, तो पहले ही संदेश मिलता है। क्लस्टर इस हिसाब से क्रम में हैं कि उनका धुआँ कितने लोगों तक पहुँचेगा।'],
  ],
}

export default function About() {
  const { lang } = useT()
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 overflow-y-auto px-4 py-6 text-gray-300">
      <h1 className="text-2xl font-bold text-white">{lang === 'hi' ? 'धुआँ कैसे काम करता है' : 'How Dhuaan works'}</h1>
      <ol className="mt-4 space-y-4">
        {STEPS[lang].map(([h, p]) => (
          <li key={h} className="rounded-xl border border-line bg-panel p-4"><h2 className="font-semibold text-white">{h}</h2><p className="mt-1 text-sm">{p}</p></li>
        ))}
      </ol>
      <h2 className="mt-8 text-lg font-semibold text-white">Limits — read these</h2>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
        <li>The Smoke Index is <b>relative</b>; it is not a PM2.5 measurement or an AQI forecast. Local traffic, dust and industry are not included.</li>
        <li>Satellites pass at fixed times; fires lit after the afternoon pass are only seen on the next pass.</li>
        <li>The plume model is deliberately simple (single transport level, Gaussian spread, fixed decay). It is checked against satellite imagery and last season’s data, not a substitute for official forecasts.</li>
        <li>Fires across the border are counted because smoke does not stop at borders. No individual farm or farmer is identified.</li>
      </ul>
      <h2 className="mt-8 text-lg font-semibold text-white">Built on AWS</h2>
      <p className="mt-2 text-sm">EventBridge Scheduler → Step Functions → Lambda (fetch FIRMS fires, fetch winds, run the numpy model, send alerts) → S3 + CloudFront for the published forecast → this app on Amplify Hosting. Alerts go out via Telegram and Amazon SNS (email, filtered per 0.1° cell); subscribers live in DynamoDB; secrets in SSM Parameter Store; place search on Amazon Location Service. Infrastructure as code with AWS SAM.</p>
      <h2 className="mt-8 text-lg font-semibold text-white">Data</h2>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
        <li>Fires: NASA FIRMS, VIIRS S-NPP / NOAA-20 / NOAA-21 near-real-time 375 m active fires.</li>
        <li>Winds and mixing height: Open-Meteo forecast API.</li>
        <li>Map: © OpenStreetMap contributors, © CARTO / Amazon Location Service.</li>
      </ul>
      <p className="mt-8 text-xs text-gray-500">Team Jhadu uthao Parth — Environmental Hacks 2026 (WeMakeDevs × AWS). Not medical advice; follow official advisories and your doctor.</p>
    </main>
  )
}
