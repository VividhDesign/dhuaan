"""Forecast for any lat/lon from a published smoke.json (bilinear sample of the frames)."""
import base64
import math

import numpy as np

from .fires import haversine_km
from .receptors import summarize_series


def decode_frames(smoke: dict) -> np.ndarray:
    g = smoke["grid"]
    return np.stack([np.frombuffer(base64.b64decode(f), np.uint8).reshape(g["ny"], g["nx"]).astype(float)
                     for f in smoke["frames"]])


def sample_series(smoke: dict, lat: float, lon: float, frames: np.ndarray | None = None) -> np.ndarray | None:
    g = smoke["grid"]
    fx = (lon - g["lon0"]) / g["dlon"]
    fy = (lat - g["lat0"]) / g["dlat"]
    if not (0 <= fx <= g["nx"] - 1 and 0 <= fy <= g["ny"] - 1):
        return None  # outside the forecast area
    frames = decode_frames(smoke) if frames is None else frames
    ix, iy = min(int(fx), g["nx"] - 2), min(int(fy), g["ny"] - 2)
    ax, ay = fx - ix, fy - iy
    f = frames
    return ((f[:, iy, ix] * (1 - ax) + f[:, iy, ix + 1] * ax) * (1 - ay)
            + (f[:, iy + 1, ix] * (1 - ax) + f[:, iy + 1, ix + 1] * ax) * ay)


def nearest_place(places: list[dict], lat: float, lon: float) -> tuple[dict, float]:
    best = min(places, key=lambda p: haversine_km(lat, lon, p["lat"], p["lon"]))
    return best, haversine_km(lat, lon, best["lat"], best["lon"])


def forecast_at(smoke: dict, places: list[dict], lat: float, lon: float, params: dict,
                frames: np.ndarray | None = None) -> dict | None:
    series = sample_series(smoke, lat, lon, frames)
    if series is None:
        return None
    out = summarize_series(series, np.asarray(smoke["times"]), params)
    place, km = nearest_place(places, lat, lon)
    out["near"] = {"id": place["id"], "name": place["name"], "km": round(km, 1)}
    out["sources"] = place.get("sources", []) if km <= 40 else []
    return out


def cell_id(lat: float, lon: float) -> str:
    """0.1° subscription cell, used as the SNS filter-policy attribute."""
    return f"{math.floor(lat * 10) / 10:.1f}_{math.floor(lon * 10) / 10:.1f}"
