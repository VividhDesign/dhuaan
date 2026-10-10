"""Re-run the forecast for a past date with archived fires (FIRMS standard processing) and archived winds.

python -m engine.replay 2025-10-31 --hour-utc 15 --out ../../samples/replay
(needs FIRMS_KEY in the environment)
"""
import argparse
import os
from calendar import timegm
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .fires import fetch_area_csv, parse_firms_csv
from .run import build_outputs, default_params, write_outputs
from .winds import fetch_open_meteo, grid_from_open_meteo, grid_points

ARCHIVE_SOURCES = {"SNPP": "VIIRS_SNPP_SP", "N20": "VIIRS_NOAA20_SP"}


def replay(date: str, hour_utc: int, firms_key: str, params: dict | None = None) -> dict:
    params = params or default_params()
    now = timegm(datetime.strptime(date, "%Y-%m-%d").timetuple()) + hour_utc * 3600
    d = params["source_domain"]
    bbox = f"{d['lon_min']},{d['lat_min']},{d['lon_max']},{d['lat_max']}"
    start = (datetime.fromtimestamp(now, timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    rows = []
    for sat, src in ARCHIVE_SOURCES.items():
        try:
            rows += parse_firms_csv(fetch_area_csv(firms_key, src, bbox, days=2, date=start), sat)
        except OSError as e:
            print(f"warn: {src}: {e}")
    rows = [r for r in rows if now - 24 * 3600 <= r["t"] <= now]  # what we'd have known at that moment
    spec = params["wind_grid"]
    lats, lons = grid_points(spec)
    end = (datetime.fromtimestamp(now, timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
    grid = grid_from_open_meteo(fetch_open_meteo(lats, lons, start_date=start, end_date=end), spec,
                                params.get("wind_10m_scale", 1.3))
    out = build_outputs(rows, grid, now, params, wind_source="GFS archive via Open-Meteo (replay)")
    out["meta.json"]["replay"] = {"date": date, "hour_utc": hour_utc}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("--hour-utc", type=int, default=15)
    ap.add_argument("--out", default="../../samples/replay")
    a = ap.parse_args()
    out = replay(a.date, a.hour_utc, os.environ["FIRMS_KEY"])
    write_outputs(out, Path(a.out) / a.date)
    m = out["meta.json"]
    print(f"{a.date}: fires={m['fires_24h']} clusters={m['clusters']} compute={m['compute_s']}s")
    for p in sorted(out["places.json"], key=lambda p: -p["peak"]["index"])[:10]:
        print(f"  {p['name']['en']:<28} peak={p['peak']['index']:>3} {p['level_24h']:<9} {p['sources'][:2]}")


if __name__ == "__main__":
    main()
