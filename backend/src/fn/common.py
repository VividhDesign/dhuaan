"""Shared helpers for the Lambda handlers (S3 JSON I/O, run keys)."""
import gzip
import json
import os

import boto3

BUCKET = os.environ.get("BUCKET", "")
_s3 = None


def s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3")
    return _s3


def put_json(key: str, obj, cache: str = "public, max-age=31536000, immutable", gz: bool = False) -> None:
    body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    extra = {"ContentType": "application/json; charset=utf-8", "CacheControl": cache}
    if gz:
        body = gzip.compress(body)
        extra["ContentEncoding"] = "gzip"
    s3().put_object(Bucket=BUCKET, Key=key, Body=body, **extra)


def get_json(key: str):
    obj = s3().get_object(Bucket=BUCKET, Key=key)
    body = obj["Body"].read()
    if obj.get("ContentEncoding") == "gzip":
        body = gzip.decompress(body)
    return json.loads(body)


def put_text(key: str, text: str, content_type: str = "text/csv") -> None:
    s3().put_object(Bucket=BUCKET, Key=key, Body=text.encode("utf-8"), ContentType=content_type)
