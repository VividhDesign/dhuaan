"""Step 1b: download the hourly wind + boundary-layer forecast for the 0.5° grid (Open-Meteo)."""
from aws_lambda_powertools import Logger

from engine.run import default_params
from engine.winds import fetch_open_meteo, grid_points
from fn.common import put_json

logger = Logger()


@logger.inject_lambda_context(log_event=False)
def handler(event, _ctx):
    run_id = event["run_id"]
    spec = default_params()["wind_grid"]
    lats, lons = grid_points(spec)
    points = fetch_open_meteo(lats, lons)
    key = f"runs/{run_id}/winds.json"
    put_json(key, points, gz=True)
    logger.info("winds fetched", extra={"points": len(points), "hours": len(points[0]["hourly"]["time"])})
    return {"winds_key": key, "points": len(points)}
