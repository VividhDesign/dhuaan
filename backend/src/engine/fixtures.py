"""Synthetic but realistic scenario so the frontend can be built without AWS or live data.

python -m engine.fixtures --out ../samples/latest
"""
import argparse
import random
import time

import numpy as np

from .run import build_outputs, default_params, write_outputs
from .winds import uniform_grid

# (lat, lon, fires, mean FRP) — paddy belts in Punjab/Haryana
HOTSPOTS = [
    (30.25, 75.84, 40, 8.0),   # Sangrur
    (30.34, 76.39, 30, 7.0),   # Patiala
    (29.80, 76.40, 22, 6.0),   # Kaithal
    (30.21, 74.95, 25, 7.5),   # Bathinda
    (30.82, 75.17, 18, 6.5),   # Moga
    (29.69, 76.99, 12, 5.0),   # Karnal
    (31.45, 74.93, 15, 6.0),   # Tarn Taran
]


def synthetic(now: int, seed: int = 7):
    rnd = random.Random(seed)
    params = default_params()
    pass_time = (now // 86400) * 86400 + 8 * 3600  # ~13:30 IST afternoon VIIRS pass
    if pass_time > now:
        pass_time -= 86400
    rows = []
    for lat, lon, n, frp in HOTSPOTS:
        for _ in range(n):
            rows.append({"lat": lat + rnd.gauss(0, 0.12), "lon": lon + rnd.gauss(0, 0.12),
                         "frp": max(0.5, rnd.expovariate(1 / frp)), "t": pass_time + rnd.randint(-900, 900),
                         "sat": rnd.choice(["N", "N20", "N21"]), "conf": "nominal"})
    spec = params["wind_grid"]
    times = list(range(pass_time - 6 * 3600, now + 40 * 3600, 3600))
    grid = uniform_grid(spec, times, speed=5.5, direction_deg=315.0)
    # diurnal mixing height: shallow at night (smoke trapped), deep in the afternoon
    hours_ist = ((np.array(times) // 3600) + 5.5) % 24
    blh = np.where((hours_ist >= 10) & (hours_ist <= 17), 1300.0, 250.0)
    grid.blh = np.broadcast_to(blh[:, None, None], grid.u.shape).copy()
    return rows, grid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../samples/latest")
    args = ap.parse_args()
    now = int(time.time())
    rows, grid = synthetic(now)
    out = build_outputs(rows, grid, now, wind_source="synthetic NW wind (fixture)")
    write_outputs(out, args.out)
    m = out["meta.json"]
    print(f"fixture: fires={m['fires_24h']} clusters={m['clusters']} compute={m['compute_s']}s -> {args.out}")


if __name__ == "__main__":
    main()
