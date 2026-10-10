"""Daily smoke bulletin in English and Hindi, built only from the run's own numbers (no LLM needed)."""
from datetime import datetime

from .messages import IST, LEVEL_WORD, when

ORDER = {"none": 0, "light": 1, "moderate": 2, "heavy": 3}


def _top_sources(places: list[dict], k: int = 3) -> list[str]:
    score: dict[str, int] = {}
    for p in places:
        for s in p.get("sources", []):
            score[s["label"]] = score.get(s["label"], 0) + s["pct"]
    return [n for n, _ in sorted(score.items(), key=lambda kv: -kv[1])[:k]]


def build(outputs: dict) -> dict:
    meta, places, hot = outputs["meta.json"], outputs["places.json"], outputs["hotspots.json"]
    now = meta["generated_at"]
    n = meta["fires_24h"]
    affected = sorted([p for p in places if ORDER[p["level_24h"]] >= 2],
                      key=lambda p: (-ORDER[p["level_24h"]], p["arrival"] or 0))
    delhi = [p for p in affected if p.get("delhi")]
    states = sorted(hot["totals"]["by_state"].items(), key=lambda kv: -kv[1])[:2]
    where_en = " and ".join(f"{st} ({c})" for st, c in states)
    where_hi = " और ".join(f"{st} ({c})" for st, c in states)
    date_en = datetime.fromtimestamp(now, IST).strftime("%d %b, %I:%M %p IST").lstrip("0")
    date_hi = datetime.fromtimestamp(now, IST).strftime("%d/%m, %H:%M")

    en = [f"Dhuaan smoke bulletin, {date_en}.",
          f"Satellites detected {n} farm fires in the last 24 hours" + (f", most in {where_en}." if states else ".")]
    hi = [f"धुआँ बुलेटिन, {date_hi}।",
          f"पिछले 24 घंटे में सैटेलाइट ने {n} खेतों की आग देखी" + (f", ज़्यादातर {where_hi} में।" if states else "।")]

    if delhi:
        worst = delhi[0]
        en.append(f"{LEVEL_WORD['en'][worst['level_24h']].capitalize()} is expected over Delhi from {when(worst['arrival'], now, 'en')}"
                  + (f", clearing around {when(worst['clears'], now, 'en')}." if worst["clears"] else ".")
                  + (f" It comes mostly from fires near {', '.join(_top_sources(delhi))}." if delhi[0].get("sources") else ""))
        hi.append(f"दिल्ली में {when(worst['arrival'], now, 'hi')} से {LEVEL_WORD['hi'][worst['level_24h']]} आने की संभावना है"
                  + (f", जो {when(worst['clears'], now, 'hi')} तक छँटेगा।" if worst["clears"] else "।")
                  + (f" यह ज़्यादातर {', '.join(_top_sources(delhi))} के पास की आग से है।" if delhi[0].get("sources") else ""))
    if affected and not delhi:
        names = ", ".join(p["name"]["en"].split(",")[0] for p in affected[:4])
        names_hi = ", ".join(p["name"]["hi"].split(",")[0] for p in affected[:4])
        en.append(f"Smoke is expected over {names} in the next 24 hours; Delhi should stay clear of farm-fire smoke.")
        hi.append(f"अगले 24 घंटे में {names_hi} में धुआँ आ सकता है; दिल्ली में खेतों की आग का धुआँ आने की उम्मीद नहीं।")
    if not affected:
        en.append("Winds are keeping the smoke away from towns and cities; no farm-fire smoke is expected in the next 24 hours.")
        hi.append("हवा धुएँ को शहरों से दूर ले जा रही है; अगले 24 घंटे में खेतों की आग का धुआँ आने की उम्मीद नहीं।")
    share = hot.get("top25_share_delhi_pct")
    if delhi and share:
        en.append(f"Just 25 fire clusters cause about {share}% of this smoke.")
        hi.append(f"इस धुएँ का लगभग {share}% सिर्फ़ 25 आग क्लस्टर से है।")
    if affected:
        en.append("Close windows before it arrives and move morning walks indoors.")
        hi.append("धुआँ आने से पहले खिड़कियाँ बंद करें और सुबह की सैर घर के अंदर करें।")
    return {"generated_at": now, "en": " ".join(en), "hi": " ".join(hi), "affected": [p["id"] for p in affected]}
