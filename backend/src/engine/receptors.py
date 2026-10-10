"""Smoke Index at receptors: the heat-map grid and named places."""
import numpy as np

from . import param

LEVELS = ("none", "light", "moderate", "heavy")


def level_of(index: float, params: dict) -> str:
    lv = params["levels"]
    if index >= lv["heavy"]:
        return "heavy"
    if index >= lv["moderate"]:
        return "moderate"
    if index >= lv["light"]:
        return "light"
    return "none"


def grid_receptors(spec: dict):
    j, i = np.meshgrid(np.arange(spec["ny"]), np.arange(spec["nx"]), indexing="ij")
    lat = spec["lat0"] + j.ravel() * spec["d"]
    lon = spec["lon0"] + i.ravel() * spec["d"]
    return lat, lon  # row-major from the south-west corner


def summarize_series(series: np.ndarray, times: np.ndarray, params: dict) -> dict:
    """series: Smoke Index per hourly frame (index 0 = now)."""
    s = np.clip(np.round(series), 0, 100).astype(int)
    mod = params["levels"]["moderate"]
    above = s >= mod
    arrival = clears = None
    if above.any():
        # longest run of hours at or above "moderate"
        best_len, best_start, run_start = 0, 0, None
        for k, a in enumerate(list(above) + [False]):
            if a and run_start is None:
                run_start = k
            elif not a and run_start is not None:
                if k - run_start > best_len:
                    best_len, best_start = k - run_start, run_start
                run_start = None
        arrival = int(times[int(np.argmax(above))])
        end = best_start + best_len
        clears = int(times[end]) if end < len(times) else None
    k_peak = int(np.argmax(s))
    horizon = min(len(s), 25)
    return {
        "series": s.tolist(),
        "level_24h": level_of(float(s[:horizon].max()) if horizon else 0.0, params),
        "arrival": arrival,
        "clears": clears,
        "peak": {"t": int(times[k_peak]), "index": int(s[k_peak])},
    }


def attribution(cluster_contrib_24h: np.ndarray, clusters: list[dict], top: int = 3) -> list[dict]:
    """cluster_contrib_24h: (C,) summed contribution of each cluster to one place over 24 h."""
    total = float(cluster_contrib_24h.sum())
    if total <= 0:
        return []
    by_label: dict[tuple, float] = {}
    for c, val in zip(clusters, cluster_contrib_24h):
        key = (c["district"], c["state"])
        by_label[key] = by_label.get(key, 0.0) + float(val)
    ranked = sorted(by_label.items(), key=lambda kv: -kv[1])[:top]
    return [{"label": d, "state": s, "pct": int(round(100 * v / total))} for (d, s), v in ranked]
