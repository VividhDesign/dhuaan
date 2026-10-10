"""HTTP API: place search, email subscription, Telegram webhook, manual pipeline trigger."""
import hashlib
import hmac
import json
import os
import re
import time

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, Response
from aws_lambda_powertools.utilities import parameters

from engine.messages import compose
from engine.point import cell_id, forecast_at
from engine.run import default_params
from fn import subscribers, telegram
from fn.alerts import hotspot_brief, load_latest, place_name

logger = Logger()
app = APIGatewayHttpResolver()
SITE = os.environ.get("SITE_URL", "")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_geo = None


def geo():
    global _geo
    if _geo is None:
        _geo = boto3.client("geo-places")
    return _geo


def geocode(q: str, n: int = 5) -> list[dict]:
    r = geo().geocode(QueryText=q[:200], MaxResults=n, Filter={"IncludeCountries": ["IND"]},
                      BiasPosition=[77.1, 28.7])
    out = []
    for it in r.get("ResultItems", []):
        lon, lat = it["Position"]
        out.append({"label": it.get("Title", q), "lat": round(lat, 4), "lon": round(lon, 4)})
    return out


def bad(msg: str, code: int = 400):
    return Response(status_code=code, content_type="application/json", body=json.dumps({"error": msg}))


@app.get("/api/places")
def places():
    q = (app.current_event.get_query_string_value("q") or "").strip()
    if len(q) < 2:
        return {"results": []}
    return {"results": geocode(q)}


@app.post("/api/subscribe/email")
def subscribe_email():
    b = app.current_event.json_body or {}
    email, lang, role = str(b.get("email", "")).strip(), b.get("lang", "en"), b.get("role", "resident")
    try:
        lat, lon = float(b["lat"]), float(b["lon"])
    except (KeyError, TypeError, ValueError):
        return bad("lat/lon required")
    if not EMAIL_RE.match(email) or lang not in ("en", "hi") or role not in ("resident", "school", "official"):
        return bad("invalid email, lang or role")
    cell = cell_id(lat, lon)
    sub = boto3.client("sns").subscribe(
        TopicArn=os.environ["ALERTS_TOPIC"], Protocol="email", Endpoint=email, ReturnSubscriptionArn=True,
        Attributes={"FilterPolicy": json.dumps({"cell": [cell], "lang": [lang]}),
                    "FilterPolicyScope": "MessageAttributes"})
    subscribers.put_email(hashlib.sha256(f"{email}|{cell}".encode()).hexdigest()[:24], cell, lang, role,
                          sub["SubscriptionArn"])
    return {"ok": True, "message": "Check your inbox and confirm the subscription." if lang == "en"
            else "अपना ईमेल देखें और सब्सक्रिप्शन कन्फ़र्म करें।"}


@app.post("/api/run")
def run_now():
    key = app.current_event.get_header_value("x-run-key") or ""
    expected = parameters.get_parameter("/dhuaan/run_key", decrypt=True, max_age=300)
    if not hmac.compare_digest(key, expected):
        return bad("forbidden", 403)
    r = boto3.client("stepfunctions").start_execution(stateMachineArn=os.environ["PIPELINE_ARN"],
                                                      name=f"manual-{int(time.time())}")
    return {"ok": True, "execution": r["executionArn"]}


# ---------------- Telegram ----------------
HELP = {
    "en": ("Dhuaan sends you a smoke forecast for your area — before the smoke arrives.\n"
           "• Share your location (button below) or type your area name, e.g. Rohini\n"
           "• /now — forecast for your area\n• /school — morning indoor/outdoor call for schools\n"
           "• /official — daily fire-hotspot brief\n• /hotspots — top fire clusters now\n"
           "• /hindi — हिंदी में\n• /stop — unsubscribe"),
    "hi": ("धुआँ आपके इलाक़े के लिए धुएँ का पूर्वानुमान भेजता है — धुआँ आने से पहले।\n"
           "• नीचे बटन से लोकेशन भेजें या इलाक़े का नाम लिखें, जैसे रोहिणी\n"
           "• /now — आपके इलाक़े का पूर्वानुमान\n• /school — स्कूलों के लिए सुबह का संदेश\n"
           "• /official — रोज़ का हॉटस्पॉट ब्रीफ़\n• /hotspots — अभी के बड़े आग क्लस्टर\n"
           "• /english — in English\n• /stop — बंद करें"),
}


def reply_forecast(chat_id: int, lat: float, lon: float, lang: str, role: str) -> None:
    smoke, places_, _ = load_latest()
    fc = forecast_at(smoke, places_, lat, lon, default_params())
    if fc is None:
        telegram.send_message(chat_id, "This location is outside the forecast area (Punjab–Haryana–Delhi NCR–west UP)."
                              if lang == "en" else "यह जगह पूर्वानुमान क्षेत्र (पंजाब–हरियाणा–दिल्ली NCR–पश्चिमी UP) से बाहर है।")
        return
    link = f"{SITE}/?lat={lat:.3f}&lon={lon:.3f}" if SITE else None
    telegram.send_message(chat_id, compose(fc, place_name(fc, lang), int(time.time()), lang, role, link, is_alert=False))


def subscribe_tg(chat_id: int, lat: float, lon: float, lang: str) -> None:
    existing = subscribers.get_tg(chat_id) or {}
    role = existing.get("role", "resident")
    subscribers.put_tg(chat_id, lat, lon, cell_id(lat, lon), lang, role)
    telegram.send_message(chat_id, "✅ Subscribed. You'll get a message before smoke reaches you." if lang == "en"
                          else "✅ सब्सक्राइब हो गया। धुआँ आने से पहले आपको संदेश मिलेगा।")
    reply_forecast(chat_id, lat, lon, lang, role)


def handle_update(upd: dict) -> None:
    msg = upd.get("message") or upd.get("edited_message")
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    sub = subscribers.get_tg(chat_id)
    lang = (sub or {}).get("lang") or ("hi" if (msg.get("from", {}).get("language_code") or "").startswith("hi") else "en")

    if "location" in msg:
        loc = msg["location"]
        subscribe_tg(chat_id, loc["latitude"], loc["longitude"], lang)
        return
    text = (msg.get("text") or "").strip()
    cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else None

    if cmd in ("/start", "/help"):
        telegram.send_message(chat_id, HELP[lang], telegram.LOCATION_KEYBOARD)
    elif cmd in ("/hindi", "/english"):
        lang = "hi" if cmd == "/hindi" else "en"
        if sub:
            subscribers.update_tg(chat_id, lang=lang)
        telegram.send_message(chat_id, HELP[lang], telegram.LOCATION_KEYBOARD)
    elif cmd in ("/school", "/resident", "/official"):
        role = cmd[1:]
        if not sub:
            telegram.send_message(chat_id, "First share your location." if lang == "en" else "पहले अपनी लोकेशन भेजें।",
                                  telegram.LOCATION_KEYBOARD)
            return
        subscribers.update_tg(chat_id, role=role)
        telegram.send_message(chat_id, f"✅ Role set: {role}." if lang == "en" else f"✅ भूमिका: {role}")
    elif cmd == "/now":
        if sub:
            reply_forecast(chat_id, float(sub["lat"]), float(sub["lon"]), lang, sub.get("role", "resident"))
        else:
            telegram.send_message(chat_id, HELP[lang], telegram.LOCATION_KEYBOARD)
    elif cmd == "/hotspots":
        _, _, hot = load_latest()
        telegram.send_message(chat_id, hotspot_brief(hot, lang, 5))
    elif cmd == "/stop":
        subscribers.delete_tg(chat_id)
        telegram.send_message(chat_id, "Unsubscribed." if lang == "en" else "अनसब्सक्राइब हो गया।")
    elif text and not cmd:
        results = geocode(text, 1)
        if results:
            r = results[0]
            telegram.send_message(chat_id, f"📍 {r['label']}")
            subscribe_tg(chat_id, r["lat"], r["lon"], lang)
        else:
            telegram.send_message(chat_id, "Couldn't find that place. Try sharing your location."
                                  if lang == "en" else "जगह नहीं मिली। लोकेशन भेजकर देखें।", telegram.LOCATION_KEYBOARD)


@app.post("/api/telegram/webhook")
def telegram_webhook():
    secret = parameters.get_parameter("/dhuaan/telegram_secret", decrypt=True, max_age=300)
    got = app.current_event.get_header_value("x-telegram-bot-api-secret-token") or ""
    if not hmac.compare_digest(got, secret):
        return bad("forbidden", 403)
    try:
        handle_update(app.current_event.json_body or {})
    except Exception:  # always 200 so Telegram doesn't retry-storm
        logger.exception("telegram update failed")
    return {"ok": True}


@logger.inject_lambda_context(log_event=False)
def handler(event, ctx):
    return app.resolve(event, ctx)
