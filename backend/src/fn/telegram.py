"""Minimal Telegram Bot API client (stdlib only)."""
import json
import os
import urllib.request

from aws_lambda_powertools.utilities import parameters

API = "https://api.telegram.org/bot{token}/{method}"


def token() -> str:
    return parameters.get_parameter(os.environ.get("TELEGRAM_TOKEN_PARAM", "/dhuaan/telegram_token"),
                                    decrypt=True, max_age=300)


def call(method: str, payload: dict, timeout: int = 15) -> dict:
    req = urllib.request.Request(API.format(token=token(), method=method), data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def send_message(chat_id: int, text: str, keyboard: dict | None = None) -> dict:
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if keyboard:
        payload["reply_markup"] = keyboard
    return call("sendMessage", payload)


def send_audio(chat_id: int, url: str, caption: str = "") -> dict:
    return call("sendAudio", {"chat_id": chat_id, "audio": url, "caption": caption[:1000]})


LOCATION_KEYBOARD = {
    "keyboard": [[{"text": "📍 Share my location / अपनी लोकेशन भेजें", "request_location": True}]],
    "resize_keyboard": True, "one_time_keyboard": True,
}
