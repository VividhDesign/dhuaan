"""Orchestrates one forecast run: fires + winds -> the JSON files the web app and alerts read.

CLI:
    python -m engine.run --live --out ../samples/live
"""
import argparse
import base64
import json
import time
from pathlib import Path

import numpy as np

from . import load_data, param
from .fires import cluster, dedupe, fetch_public_csv, filter_fires, parse_firms_csv, FIRMS_PUBLIC
from .plume import frame_inputs, raw_contributions, s_ref, stagnation_factor
from .receptors import attribution, grid_receptors, summarize_series
from .trajectories import integrate, releases
from .winds import WindGrid, fetch_open_meteo, grid_from_open_meteo, grid_points

VERSION = "1.0"


def default_params() -> dict:
    return load_data("parameters.json")


def build_outputs(fire_rows: list[dict], grid: WindGrid, now: int, params: dict | None = None,
                  wind_source: str = "GFS via Open-Meteo") -> dict:
    params = params or default_params()
    places = load_data("places.json")
    t0 = time.time()

    fires = dedupe(filter_fires(fire_rows, params))
    clusters = cluster(fires, params)
    cell_to_cluster = {c["cell"]: c for c in clusters}
    rel = releases(clusters, params)

    t_now = int(now) // 3600 * 3600
    n_frames = params["forecast_hours"] + 1
    frame_times = t_now + 3600 * np.arange(n_frames, dtype=np.int64)
    traj = integrate(grid, rel, int(frame_times[-1]), dt_s=params["dt_minutes"] * 60)

    spec = params["receptor_grid"]
    g_lat, g_lon = grid_receptors(spec)
    p_lat = np.array([p["lat"] for p in places])
    p_lon = np.array([p["lon"] for p in places])
    scale = 100.0 / s_ref(params)

    n_c = len(clusters)
    grid_index = np.zeros((n_frames, g_lat.size))
    place_contrib = np.zeros((n_frames, max(n_c, 1), len(places)))  # index units, per cluster
    for k, t in enumerate(frame_times):
        fi = frame_inputs(traj, rel, int(t)) if n_c else None
        if fi is None or fi[0].size == 0:
            continue
        lat, lon, age, w, cid = fi
        fg = stagnation_factor(grid, g_lat, g_lon, int(t), params)
        grid_index[k] = raw_contributions(lat, lon, age, w, g_lat, g_lon, params).sum(axis=0) * fg * scale
        fp = stagnation_factor(grid, p_lat, p_lon, int(t), params)
        raw_p = raw_contributions(lat, lon, age, w, p_lat, p_lon, params) * fp[None, :] * scale
        np.add.at(place_contrib[k], cid, raw_p)

    place_index = place_contrib.sum(axis=1)  # (F, places)
    horizon = min(25, n_frames)  # next 24 h
    contrib_24h = place_contrib[:horizon].sum(axis=0)  # (C, places)

    # --- places.json
    places_out = []
    for j, p in enumerate(places):
        summary = summarize_series(place_index[:, j], frame_times, params)
        summary["sources"] = attribution(contrib_24h[:n_c, j], clusters) if n_c else []
        places_out.append({"id": p["id"], "name": p["name"], "lat": p["lat"], "lon": p["lon"],
                           "delhi": p.get("delhi", False), **summary})

    # --- hotspots.json: rank clusters by people-hours under smoke tomorrow
    pops = np.array([p["pop"] for p in places], float)
    impact = (contrib_24h[:n_c] / 100.0 * pops[None, :]).sum(axis=1) if n_c else np.zeros(0)
    order = np.argsort(-impact)
    delhi = np.array([p.get("delhi", False) for p in places])
    delhi_total = contrib_24h[:n_c][:, delhi].sum() if n_c else 0.0
    top25 = order[:25]
    top25_share = int(round(100 * contrib_24h[top25][:, delhi].sum() / delhi_total)) if delhi_total > 0 else None
    by_state: dict[str, int] = {}
    for c in clusters:
        by_state[c["state"]] = by_state.get(c["state"], 0) + c["n_fires"]
    hot = []
    for rank, ci in enumerate(order[:50], start=1):
        c = clusters[ci]
        hot.append({"id": c["id"], "rank": rank, "lat": c["lat"], "lon": c["lon"], "label": c["label"],
                    "district": c["district"], "state": c["state"], "n_fires": c["n_fires"], "frp_mw": c["frp_mw"],
                    "first_seen": c["first_seen"], "last_seen": c["last_seen"], "repeat": False,
                    "impact_people_hours": int(impact[ci])})

    # --- smoke.json: uint8 frames, row-major from the SW corner
    frames = [base64.b64encode(np.clip(np.round(f), 0, 100).astype(np.uint8).tobytes()).decode("ascii")
              for f in grid_index]

    # --- trails.json: hourly puff paths for the animation (strongest puffs first)
    trails = []
    if n_c:
        keep = np.argsort(-rel["w"])[: params.get("max_trails", 2400)]
        w_max = float(rel["w"].max())
        for pi in keep:
            ok = ~np.isnan(traj["lat"][pi])
            if ok.sum() < 2:
                continue
            path = [[round(float(lo), 3), round(float(la), 3), int(t)]
                    for la, lo, t in zip(traj["lat"][pi][ok], traj["lon"][pi][ok], traj["times"][ok])]
            trails.append({"cluster": clusters[int(rel["cluster"][pi])]["id"],
                           "w": round(float(rel["w"][pi]) / w_max, 3), "path": path})

    # --- fires.geojson
    cell = param(params, "cluster_cell_deg")
    feats = []
    for f in fires:
        key = f"{np.floor(f['lat'] / cell) * cell:.1f}_{np.floor(f['lon'] / cell) * cell:.1f}"
        c = cell_to_cluster.get(key)
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(f["lon"], 4), round(f["lat"], 4)]},
                      "properties": {"frp": round(f["frp"], 1), "t": f["t"], "sat": f["sat"], "conf": f["conf"],
                                     "cluster": c["id"] if c else None}})

    last_pass = max((f["t"] for f in fires), default=None)
    meta = {"run_id": time.strftime("%Y%m%dT%H%MZ", time.gmtime(now)), "generated_at": int(now),
            "last_pass_utc": last_pass, "wind_source": wind_source, "fires_24h": len(fires),
            "clusters": n_c, "levels": params["levels"], "version": VERSION,
            "compute_s": round(time.time() - t0, 2)}
    return {
        "meta.json": meta,
        "fires.geojson": {"type": "FeatureCollection", "features": feats},
        "trails.json": {"t_start": int(traj["times"][0]) if len(traj["times"]) else t_now,
                        "t_end": int(frame_times[-1]), "paths": trails},
        "smoke.json": {"grid": {"lon0": spec["lon0"], "lat0": spec["lat0"], "dlon": spec["d"], "dlat": spec["d"],
                                "nx": spec["nx"], "ny": spec["ny"]},
                       "times": frame_times.tolist(), "frames": frames},
        "places.json": places_out,
        "hotspots.json": {"generated_at": int(now), "totals": {"fires_24h": len(fires), "by_state": by_state},
                          "top25_share_delhi_pct": top25_share, "clusters": hot},
        "advice.json": load_data("advice.json"),
    }


def write_outputs(outputs: dict, outdir: str | Path) -> None:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for name, obj in outputs.items():
        with open(outdir / name, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def fetch_live(params: dict) -> tuple[list[dict], WindGrid]:
    rows = []
    for sat in FIRMS_PUBLIC:
        try:
            rows += parse_firms_csv(fetch_public_csv(sat), sat)
        except OSError as e:  # one satellite feed down shouldn't stop the run
            print(f"warn: FIRMS {sat} failed: {e}")
    spec = params["wind_grid"]
    lats, lons = grid_points(spec)
    grid = grid_from_open_meteo(fetch_open_meteo(lats, lons), spec, params.get("wind_10m_scale", 1.3))
    return rows, grid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="fetch real FIRMS fires and Open-Meteo winds")
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    params = default_params()
    if not args.live:
        ap.error("use --live (or python -m engine.fixtures for synthetic data)")
    rows, grid = fetch_live(params)
    out = build_outputs(rows, grid, int(time.time()), params)
    write_outputs(out, args.out)
    m = out["meta.json"]
    print(f"fires={m['fires_24h']} clusters={m['clusters']} compute={m['compute_s']}s -> {args.out}")
    worst = sorted(out["places.json"], key=lambda p: -p["peak"]["index"])[:6]
    for p in worst:
        print(f"  {p['name']['en']:<28} peak={p['peak']['index']:>3} level24h={p['level_24h']}")


if __name__ == "__main__":
    main()
