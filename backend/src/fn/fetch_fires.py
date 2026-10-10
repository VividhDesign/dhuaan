"""Step 1a: download the latest NASA FIRMS VIIRS detections (3 satellites) into the data lake."""
import time

from aws_lambda_powertools import Logger

from engine.fires import FIRMS_PUBLIC, fetch_public_csv, parse_firms_csv
from fn.common import put_json, put_text

logger = Logger()


@logger.inject_lambda_context(log_event=False)
def handler(event, _ctx):
    run_id = event["run_id"]
    day = time.strftime("%Y-%m-%d", time.gmtime())
    rows, ok = [], []
    for sat in FIRMS_PUBLIC:
        try:
            text = fetch_public_csv(sat)
        except OSError as e:
            logger.warning("FIRMS feed failed", extra={"sat": sat, "error": str(e)})
            continue
        put_text(f"raw/firms/{day}/{run_id}-{sat}.csv", text)
        rows += parse_firms_csv(text, sat)
        ok.append(sat)
    if not ok:
        raise RuntimeError("all FIRMS feeds failed")
    key = f"runs/{run_id}/fire_rows.json"
    put_json(key, rows, gz=True)
    logger.info("fires fetched", extra={"rows": len(rows), "sats": ok})
    return {"fires_key": key, "rows": len(rows), "sats": ok}
