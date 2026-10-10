"""Step 3a: write the bilingual bulletin and a Hindi voice note (Amazon Polly) for the latest run."""
import boto3
from aws_lambda_powertools import Logger

from engine.bulletin import build
from fn.common import BUCKET, get_json, put_json, s3

logger = Logger()
VOICES = {"hi": ("Kajal", "hi-IN"), "en": ("Kajal", "en-IN")}


def speak(text: str, lang: str, key: str) -> None:
    voice, code = VOICES[lang]
    audio = boto3.client("polly").synthesize_speech(Engine="neural", VoiceId=voice, LanguageCode=code,
                                                    OutputFormat="mp3", Text=text[:2900])
    s3().put_object(Bucket=BUCKET, Key=key, Body=audio["AudioStream"].read(), ContentType="audio/mpeg",
                    CacheControl="public, max-age=60")


@logger.inject_lambda_context(log_event=False)
def handler(event, _ctx):
    outputs = {n: get_json(f"public/latest/{n}") for n in ("meta.json", "places.json", "hotspots.json")}
    b = build(outputs)
    run_id = outputs["meta.json"]["run_id"]
    for lang in ("hi", "en"):
        try:
            speak(b[lang], lang, f"public/latest/bulletin-{lang}.mp3")
            b[f"audio_{lang}"] = f"/data/latest/audio/bulletin-{lang}.mp3?v={run_id}"  # relative to the API URL
        except Exception:  # voice is a bonus; the text bulletin still publishes
            logger.exception("polly failed", extra={"lang": lang})
    put_json("public/latest/bulletin.json", b, cache="public, max-age=60")
    logger.info("bulletin published", extra={"affected": len(b["affected"])})
    return {"affected": b["affected"], "audio_hi": b.get("audio_hi")}
