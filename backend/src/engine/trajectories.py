"""Puff releases and forward trajectories (RK2 midpoint) through the wind field."""
import numpy as np

from . import param
from .winds import WindGrid

M_PER_DEG = 111_320.0


def releases(clusters: list[dict], params: dict) -> dict:
    """Each cluster releases one puff per hour for `release_hours`, starting at first detection."""
    rh = int(param(params, "release_hours"))
    lat0, lon0, t0, w, cid = [], [], [], [], []
    for ci, c in enumerate(clusters):
        for k in range(rh):
            lat0.append(c["lat"])
            lon0.append(c["lon"])
            t0.append(c["first_seen"] + k * 3600)
            w.append(c["frp_mw"] / rh)
            cid.append(ci)
    return {k: np.asarray(v) for k, v in
            {"lat0": lat0, "lon0": lon0, "t0": t0, "w": w, "cluster": cid}.items()}


def _velocity_deg(grid: WindGrid, lat, lon, t):
    u, v = grid.sample(lat, lon, t)
    dlat = v / M_PER_DEG
    dlon = u / (M_PER_DEG * np.cos(np.radians(lat)))
    return dlat, dlon  # degrees per second


def integrate(grid: WindGrid, rel: dict, t_end: int, dt_s: int = 900) -> dict:
    """Advance every puff from its release time to t_end.

    Returns hourly snapshots: times (H,), lat/lon (P, H) with NaN where a puff is not yet
    released or has left the wind domain.
    """
    n = len(rel["t0"])
    if n == 0:
        return {"times": np.zeros(0, dtype=np.int64), "lat": np.zeros((0, 0)), "lon": np.zeros((0, 0))}
    t_start = int(rel["t0"].min()) // 3600 * 3600
    out_times = np.arange(t_start, t_end + 1, 3600, dtype=np.int64)
    lat_out = np.full((n, len(out_times)), np.nan)
    lon_out = np.full((n, len(out_times)), np.nan)

    lat = rel["lat0"].astype(float).copy()
    lon = rel["lon0"].astype(float).copy()
    dead = np.zeros(n, dtype=bool)
    t = t_start
    k_out = 0
    while t <= t_end:
        if t == out_times[k_out]:
            alive = (rel["t0"] <= t) & ~dead
            lat_out[alive, k_out] = lat[alive]
            lon_out[alive, k_out] = lon[alive]
            k_out += 1
            if k_out == len(out_times):
                break
        active = (rel["t0"] <= t) & ~dead
        if active.any():
            la, lo = lat[active], lon[active]
            d1lat, d1lon = _velocity_deg(grid, la, lo, t)
            mla, mlo = la + d1lat * dt_s / 2, lo + d1lon * dt_s / 2
            d2lat, d2lon = _velocity_deg(grid, mla, mlo, t + dt_s / 2)
            la, lo = la + d2lat * dt_s, lo + d2lon * dt_s
            lat[active], lon[active] = la, lo
            dead[active] = ~grid.inside(la, lo)
        t += dt_s
    return {"times": out_times, "lat": lat_out, "lon": lon_out}
