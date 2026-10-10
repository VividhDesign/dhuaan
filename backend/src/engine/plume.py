"""Gaussian puffs -> relative Smoke Index (0-100) at receptor points."""
import math
from functools import lru_cache

import numpy as np

from . import param
from .winds import KM_PER_DEG, WindGrid


def sigma_km(age_h, params):
    s = param(params, "sigma0_km") + param(params, "sigma_growth_km_per_h") * np.asarray(age_h, float)
    return np.minimum(s, params.get("sigma_max_km", 80.0))


def raw_contributions(p_lat, p_lon, age_h, w, r_lat, r_lon, params) -> np.ndarray:
    """(P, R) matrix: each puff's raw contribution at each receptor."""
    p_lat, p_lon = np.asarray(p_lat, float)[:, None], np.asarray(p_lon, float)[:, None]
    r_lat, r_lon = np.asarray(r_lat, float)[None, :], np.asarray(r_lon, float)[None, :]
    dy = (r_lat - p_lat) * KM_PER_DEG
    dx = (r_lon - p_lon) * KM_PER_DEG * np.cos(np.radians((r_lat + p_lat) / 2))
    sig = sigma_km(age_h, params)[:, None]
    weight = (np.asarray(w, float) * np.exp(-np.asarray(age_h, float) / param(params, "decay_hours")))[:, None]
    return weight * np.exp(-(dx * dx + dy * dy) / (2 * sig * sig)) / (2 * math.pi * sig * sig)


def _freeze(params):
    keys = ("sigma0_km", "sigma_growth_km_per_h", "decay_hours", "release_hours")
    ref = params["reference_scenario"]
    return tuple(param(params, k) for k in keys) + (params.get("sigma_max_km", 80.0),) + tuple(sorted(ref.items()))


@lru_cache(maxsize=8)
def _s_ref(frozen) -> float:
    s0, g, decay, rh, smax, *ref_items = frozen
    ref = dict(ref_items)
    params = {"sigma0_km": s0, "sigma_growth_km_per_h": g, "decay_hours": decay, "sigma_max_km": smax}
    rh = int(rh)
    # Puffs released hourly at distance D upwind, moving straight at the receptor.
    speed_kmh = ref["wind_ms"] * 3.6
    t = np.arange(0, 48, 0.25)  # hours since first release
    best = 0.0
    for tt in t:
        ages = tt - np.arange(rh)
        ages = ages[ages >= 0]
        if ages.size == 0:
            continue
        x = -ref["distance_km"] + speed_kmh * ages  # puff east of the receptor in km
        lat = np.zeros_like(x)
        lon = x / KM_PER_DEG
        c = raw_contributions(lat, lon, ages, np.full(ages.size, ref["frp_mw"] / rh), [0.0], [0.0], params).sum()
        best = max(best, float(c))
    return best * 100.0 / ref["target_peak"]


def s_ref(params) -> float:
    """Scale so the reference scenario (default: 1,000 MW, 150 km upwind, 5 m/s) peaks at 80."""
    return _s_ref(_freeze(params))


def stagnation_factor(grid: WindGrid, r_lat, r_lon, t, params) -> np.ndarray:
    st = params.get("stagnation", {})
    if not st.get("enabled") or grid.blh is None:
        return np.ones(len(r_lat))
    blh = grid.sample_blh(np.asarray(r_lat), np.asarray(r_lon), np.full(len(r_lat), t))
    return np.clip(st["blh_ref_m"] / np.maximum(blh, 50.0), st["min"], st["max"])


def frame_inputs(traj: dict, rel: dict, t: int):
    """Puffs alive at hourly time t: (lat, lon, age_h, w, cluster)."""
    k = int((t - traj["times"][0]) // 3600) if len(traj["times"]) else -1
    if k < 0 or k >= len(traj["times"]):
        return None
    lat, lon = traj["lat"][:, k], traj["lon"][:, k]
    ok = ~np.isnan(lat)
    age = (t - rel["t0"][ok]) / 3600.0
    return lat[ok], lon[ok], age, rel["w"][ok], rel["cluster"][ok]
