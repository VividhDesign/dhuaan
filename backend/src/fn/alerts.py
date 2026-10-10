"""Step 3: send smoke alerts (Telegram + SNS email) and the daily school/resident/official messages."""
import os
import time

import boto3
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities import parameters

from engine.messages import compose
from engine.point import decode_frames, forecast_at
from engine.run import default_params
from fn import subscribers, telegram
from fn.common import get_json

logger = Logger()
metrics = Metrics(namespace="Dhuaan")
COOLDOWN_S = 12 * 3600
SITE = os.environ.get("SITE_URL", "")


def load_latest():
    return get_json("public/latest/smoke.json"), get_json("public/latest/places.json"), get_json("public/latest/hotspots.json")


def hotspot_brief(hot: dict, lang: str, n: int = 10) -> str:
    rows = hot.get("clusters", [])[:n]
    if not rows:
        return "No significant fire clusters right now." if lang == "en" else "अभी कोई बड़ा आग क्लस्टर नहीं।"
    head = (f"🔥 Top {len(rows)} fire clusters by smoke impact (next 24 h):" if lang == "en"
            else f"🔥 असर के हिसाब से शीर्ष {len(rows)} आग क्लस्टर (अगले 24 घंटे):")
    lines = [head]
    for c in rows:
        lines.append(f"{c['rank']}. {c['label']} ({c['state']}) · {c['n_fires']} fires · {c['frp_mw']} MW · "
                     f"https://maps.google.com/?q={c['lat']},{c['lon']}")
    share = hot.get("top25_share_delhi_pct")
    if share is not None:
        lines.append(f"Top 25 clusters → {share}% of tomorrow's modelled smoke over Delhi.")
    return "\n".join(lines)


def place_name(fc: dict, lang: str) -> str:
    return fc["near"]["name"][lang] if fc["near"]["km"] <= 25 else ("your area" if lang == "en" else "आपके इलाक़े")


@metrics.log_metrics
@logger.inject_lambda_context(log_event=False)
def handler(event, _ctx):
    mode = (event or {}).get("mode", "run")
    params = default_params()
    smoke, places, hot = load_latest()
    frames = decode_frames(smoke)
    now = int(time.time())
    try:
        rel = get_json("public/latest/bulletin.json").get("audio_hi")
        api = parameters.get_parameter("/dhuaan/api_url", max_age=3600)
        audio_hi = f"{api}{rel}" if rel and api else None
    except Exception:
        audio_hi = None
    sent = 0

    for sub in subscribers.all_tg():
        try:
            lat, lon, lang, role = float(sub["lat"]), float(sub["lon"]), sub.get("lang", "en"), sub.get("role", "resident")
            fc = forecast_at(smoke, places, lat, lon, params, frames)
            if fc is None:
                continue
            text = None
            if mode == "run":
                if fc["level_24h"] in ("moderate", "heavy") and now - int(sub.get("last_alert_at", 0)) > COOLDOWN_S:
                    text = compose(fc, place_name(fc, lang), now, lang, role, SITE)
            elif mode == "daily_school" and role == "school":
                text = compose(fc, place_name(fc, lang), now, lang, "school", SITE, is_alert=fc["level_24h"] != "none")
            elif mode == "daily_resident" and role == "resident" and fc["level_24h"] != "none":
                text = compose(fc, place_name(fc, lang), now, lang, "resident", SITE)
            elif mode == "daily_official" and role == "official":
                text = hotspot_brief(hot, lang)
            if text:
                telegram.send_message(int(sub["chat_id"]), text)
                if lang == "hi" and audio_hi and mode == "run":
                    telegram.send_audio(int(sub["chat_id"]), audio_hi, "🔊 धुआँ बुलेटिन")
                if mode == "run":
                    subscribers.update_tg(int(sub["chat_id"]), last_alert_at=now)
                sent += 1
        except Exception:  # one bad subscriber must not stop the rest
            logger.exception("telegram send failed")

    topic = os.environ.get("ALERTS_TOPIC")
    if topic and mode == "run":
        sns = boto3.client("sns")
        cells = {(s["cell"], s.get("lang", "en")) for s in subscribers.all_of("email")}
        for cell, lang in cells:
            la, lo = (float(x) + 0.05 for x in cell.split("_"))
            fc = forecast_at(smoke, places, la, lo, params, frames)
            if fc and fc["level_24h"] in ("moderate", "heavy"):
                sns.publish(TopicArn=topic, Subject="Dhuaan smoke alert" if lang == "en" else "धुआँ अलर्ट",
                            Message=compose(fc, place_name(fc, lang), now, lang, "resident", SITE),
                            MessageAttributes={"cell": {"DataType": "String", "StringValue": cell},
                                               "lang": {"DataType": "String", "StringValue": lang}})
                sent += 1

    metrics.add_metric(name="AlertsSent", unit=MetricUnit.Count, value=sent)
    logger.info("alerts done", extra={"mode": mode, "sent": sent})
    return {"mode": mode, "sent": sent}

