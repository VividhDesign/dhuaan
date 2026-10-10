"""Wind fields: Open-Meteo multi-location fetch and space-time interpolation."""
import json
import math
import urllib.parse
import urllib.request
from calendar import timegm
from datetime import datetime

import numpy as np

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = [
    "wind_speed_10m", "wind_direction_10m",
    "wind_speed_925hPa", "wind_direction_925hPa",
    "boundary_layer_height",
]


def dir_to_uv(speed, direction_deg):
    """Meteorological convention: direction is where the wind blows FROM.

    A wind from 315° (north-west) blows toward the south-east: u > 0 (east), v < 0 (south).
    """
    th = np.radians(direction_deg)
    return -speed * np.sin(th), -speed * np.cos(th)


class WindGrid:
    """Regular lat/lon grid of hourly u, v (m/s) and boundary-layer height (m)."""

    def __init__(self, lon0, lat0, d, times, u, v, blh=None):
        self.lon0, self.lat0, self.d = float(lon0), float(lat0), float(d)
        self.times = np.asarray(times, dtype=np.int64)
        self.u = np.asarray(u, dtype=np.float64)
        self.v = np.asarray(v, dtype=np.float64)
        self.blh = None if blh is None else np.asarray(blh, dtype=np.float64)
        self.nt, self.ny, self.nx = self.u.shape

    @property
    def lon_max(self):
        return self.lon0 + self.d * (self.nx - 1)

    @property
    def lat_max(self):
        return self.lat0 + self.d * (self.ny - 1)

    def inside(self, lat, lon):
        return (lon >= self.lon0) & (lon <= self.lon_max) & (lat >= self.lat0) & (lat <= self.lat_max)

    def _weights(self, lat, lon, t):
        fx = np.clip((np.asarray(lon) - self.lon0) / self.d, 0, self.nx - 1)
        fy = np.clip((np.asarray(lat) - self.lat0) / self.d, 0, self.ny - 1)
        ft = np.clip((np.asarray(t, dtype=np.float64) - self.times[0]) / 3600.0, 0, self.nt - 1)
        ix = np.minimum(np.floor(fx).astype(int), self.nx - 2)
        iy = np.minimum(np.floor(fy).astype(int), self.ny - 2)
        it = np.minimum(np.floor(ft).astype(int), max(self.nt - 2, 0))
        return ix, iy, it, fx - ix, fy - iy, ft - it

    def _interp(self, field, ix, iy, it, ax, ay, at):
        def plane(k):
            f00 = field[k, iy, ix]
            f10 = field[k, iy, ix + 1]
            f01 = field[k, iy + 1, ix]
            f11 = field[k, iy + 1, ix + 1]
            return (f00 * (1 - ax) + f10 * ax) * (1 - ay) + (f01 * (1 - ax) + f11 * ax) * ay
        if self.nt == 1:
            return plane(np.zeros_like(it))
        return plane(it) * (1 - at) + plane(it + 1) * at

    def sample(self, lat, lon, t):
        w = self._weights(lat, lon, t)
        return self._interp(self.u, *w), self._interp(self.v, *w)

    def sample_blh(self, lat, lon, t):
        if self.blh is None:
            return None
        return self._interp(self.blh, *self._weights(lat, lon, t))


def _parse_time(s: str) -> int:
    return timegm(datetime.strptime(s, "%Y-%m-%dT%H:%M").timetuple())


def fetch_open_meteo(lats: list[float], lons: list[float], past_days: int = 1, forecast_days: int = 2,
                     timeout: int = 60) -> list[dict]:
    """One request for many points (Open-Meteo multi-location). Returns one dict per point."""
    out = []
    for i in range(0, len(lats), 50):  # keep URLs a sane length
        q = urllib.parse.urlencode({
            "latitude": ",".join(f"{x:.2f}" for x in lats[i:i + 50]),
            "longitude": ",".join(f"{x:.2f}" for x in lons[i:i + 50]),
            "hourly": ",".join(HOURLY_VARS),
            "wind_speed_unit": "ms", "timezone": "GMT",
            "past_days": past_days, "forecast_days": forecast_days,
        })
        with urllib.request.urlopen(f"{OPEN_METEO}?{q}", timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        out.extend(data if isinstance(data, list) else [data])
    return out


def grid_points(spec: dict) -> tuple[list[float], list[float]]:
    lats, lons = [], []
    for j in range(spec["ny"]):
        for i in range(spec["nx"]):
            lats.append(spec["lat0"] + j * spec["d"])
            lons.append(spec["lon0"] + i * spec["d"])
    return lats, lons


def grid_from_open_meteo(points: list[dict], spec: dict, scale_10m: float = 1.3) -> WindGrid:
    """Build a WindGrid. Uses 925 hPa winds (transport layer); falls back to scaled 10 m winds."""
    ny, nx = spec["ny"], spec["nx"]
    times = [_parse_time(s) for s in points[0]["hourly"]["time"]]
    nt = len(times)
    u = np.zeros((nt, ny, nx))
    v = np.zeros((nt, ny, nx))
    blh = np.full((nt, ny, nx), np.nan)
    for k, p in enumerate(points):
        j, i = divmod(k, nx)
        h = p["hourly"]
        ws925 = np.array([np.nan if x is None else x for x in h.get("wind_speed_925hPa", [None] * nt)], float)
        wd925 = np.array([np.nan if x is None else x for x in h.get("wind_direction_925hPa", [None] * nt)], float)
        ws10 = np.array([np.nan if x is None else x for x in h.get("wind_speed_10m", [None] * nt)], float) * scale_10m
        wd10 = np.array([np.nan if x is None else x for x in h.get("wind_direction_10m", [None] * nt)], float)
        ws = np.where(np.isnan(ws925), ws10, ws925)
        wd = np.where(np.isnan(wd925), wd10, wd925)
        uu, vv = dir_to_uv(np.nan_to_num(ws), np.nan_to_num(wd))
        u[:, j, i], v[:, j, i] = uu, vv
        if "boundary_layer_height" in h:
            blh[:, j, i] = [np.nan if x is None else x for x in h["boundary_layer_height"]]
    has_blh = not np.all(np.isnan(blh))
    if has_blh:
        blh = np.where(np.isnan(blh), np.nanmean(blh), blh)
    return WindGrid(spec["lon0"], spec["lat0"], spec["d"], times, u, v, blh if has_blh else None)


def uniform_grid(spec: dict, times: list[int], speed: float, direction_deg: float, blh: float | None = 800.0) -> WindGrid:
    """Constant wind everywhere: used for fixtures, calibration and tests."""
    nt = len(times)
    uu, vv = dir_to_uv(speed, direction_deg)
    shape = (nt, spec["ny"], spec["nx"])
    return WindGrid(spec["lon0"], spec["lat0"], spec["d"], times, np.full(shape, uu), np.full(shape, vv),
                    None if blh is None else np.full(shape, blh))


KM_PER_DEG = 111.32


def km_offsets(lat0, lon0, lat, lon):
    """Equirectangular east/north offsets in km (accurate enough at <500 km)."""
    dy = (np.asarray(lat) - lat0) * KM_PER_DEG
    dx = (np.asarray(lon) - lon0) * KM_PER_DEG * math.cos(math.radians(lat0))
    return dx, dy
