"""Alert and reply text in English and Hindi (deterministic templates; the LLM is optional polish)."""
from datetime import datetime, timedelta, timezone

from . import load_data

IST = timezone(timedelta(hours=5, minutes=30))
LEVEL_WORD = {
    "en": {"none": "no smoke", "light": "light smoke", "moderate": "moderate smoke", "heavy": "heavy smoke"},
    "hi": {"none": "धुआँ नहीं", "light": "हल्का धुआँ", "moderate": "मध्यम धुआँ", "heavy": "घना धुआँ"},
}
EMOJI = {"none": "✅", "light": "🌫️", "moderate": "💨", "heavy": "⚠️💨"}


def when(epoch: int | None, now: int, lang: str) -> str:
    if epoch is None:
        return ""
    t = datetime.fromtimestamp(epoch, IST)
    n = datetime.fromtimestamp(now, IST)
    day_diff = (t.date() - n.date()).days
    h12 = t.hour % 12 or 12
    if lang == "hi":
        part = ("रात" if t.hour >= 20 or t.hour < 5 else "सुबह" if t.hour < 12 else "दोपहर" if t.hour < 16 else "शाम")
        day = {0: "आज", 1: "कल"}.get(day_diff, t.strftime("%d/%m"))
        return f"{day} {part} {h12} बजे"
    ampm = "AM" if t.hour < 12 else "PM"
    day = {0: "today" if t.hour < 18 else "tonight", 1: "tomorrow"}.get(day_diff, t.strftime("%d %b"))
    return f"{h12} {ampm} {day}"


def sources_text(sources: list[dict], lang: str) -> str:
    if not sources:
        return ""
    names = ", ".join(s["label"] for s in sources[:3])
    return f"ज़्यादातर {names} के पास खेतों की आग से।" if lang == "hi" else f"Mostly from farm fires near {names}."


def advice_lines(level: str, role: str, lang: str) -> list[str]:
    return load_data("advice.json")[role][level][lang]


def compose(fc: dict, place_name: str, now: int, lang: str = "en", role: str = "resident",
            link: str | None = None, is_alert: bool = True) -> str:
    level = fc["level_24h"]
    word = LEVEL_WORD[lang][level]
    lines = []
    if level in ("none", "light") and not is_alert:
        lines.append(f"{EMOJI[level]} {place_name}: " +
                     ("अगले 24 घंटे में " + word + "।" if lang == "hi" else f"{word} expected in the next 24 hours."))
    else:
        start, end = when(fc.get("arrival"), now, lang), when(fc.get("clears"), now, lang)
        if lang == "hi":
            head = f"{EMOJI[level]} धुआँ अलर्ट, {place_name}: {word} — {start} से" + (f" {end} तक।" if end else "।")
        else:
            head = f"{EMOJI[level]} Smoke alert, {place_name}: {word} expected from {start}" + (f" to {end}." if end else ".")
        lines.append(head)
        src = sources_text(fc.get("sources", []), lang)
        if src:
            lines.append(src)
    lines += [f"• {a}" for a in advice_lines(level, role, lang)]
    if link:
        lines.append(("नक्शा: " if lang == "hi" else "Map: ") + link)
    lines.append("Smoke Index is relative, not a PM2.5 reading." if lang == "en" else "स्मोक इंडेक्स तुलनात्मक है, PM2.5 माप नहीं।")
    return "\n".join(lines)
