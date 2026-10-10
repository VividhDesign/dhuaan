"""Step 2: fires + winds -> trajectories -> Smoke Index; publish the JSON the app and alerts read."""
import time

from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit

from engine.run import build_outputs, default_params
from engine.winds import grid_from_open_meteo
from fn.common import get_json, put_json

logger = Logger()
metrics = Metrics(namespace="Dhuaan")

LATEST_CACHE = "public, max-age=60"


@metrics.log_metrics
@logger.inject_lambda_context(log_event=False)
def handler(event, _ctx):
    run_id = event["run_id"]
    fires = event["fires"]
    winds = event["winds"]
    params = default_params()
    rows = get_json(fires["fires_key"])
    grid = grid_from_open_meteo(get_json(winds["winds_key"]), params["wind_grid"], params.get("wind_10m_scale", 1.3))
    out = build_outputs(rows, grid, int(time.time()), params)
    out["meta.json"]["run_id"] = run_id
    for name, obj in out.items():
        put_json(f"runs/{run_id}/{name}", obj)
        put_json(f"public/latest/{name}", obj, cache=LATEST_CACHE)
    m = out["meta.json"]
    metrics.add_metric(name="Fires24h", unit=MetricUnit.Count, value=m["fires_24h"])
    metrics.add_metric(name="Clusters", unit=MetricUnit.Count, value=m["clusters"])
    affected = [{"id": p["id"], "level": p["level_24h"]} for p in out["places.json"] if p["level_24h"] in ("moderate", "heavy")]
    logger.info("run published", extra={"fires": m["fires_24h"], "clusters": m["clusters"], "affected": len(affected),
                                        "compute_s": m["compute_s"]})
    return {"run_id": run_id, "fires_24h": m["fires_24h"], "clusters": m["clusters"], "affected_places": affected}
