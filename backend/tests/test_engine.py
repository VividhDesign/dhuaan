import base64
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engine.fires import cluster, dedupe, filter_fires, parse_firms_csv  # noqa: E402
from engine.plume import raw_contributions, s_ref, sigma_km  # noqa: E402
from engine.receptors import attribution, level_of, summarize_series  # noqa: E402
from engine.run import build_outputs, default_params  # noqa: E402
from engine.trajectories import integrate, releases  # noqa: E402
from engine.winds import WindGrid, dir_to_uv, uniform_grid  # noqa: E402

P = default_params()
SPEC = P["wind_grid"]
T0 = 1_791_590_400  # 2026-10-10 00:00 UTC


def test_nw_wind_blows_to_southeast():
    u, v = dir_to_uv(10.0, 315.0)
    assert u > 0 and v < 0
    assert math.isclose(math.hypot(u, v), 10.0)


def test_uniform_wind_gives_straight_line_with_exact_displacement():
    times = list(range(T0, T0 + 10 * 3600, 3600))
    grid = uniform_grid(SPEC, times, speed=5.0, direction_deg=270.0)  # from the west -> moves east
    rel = {"lat0": np.array([30.0]), "lon0": np.array([75.0]), "t0": np.array([T0]),
           "w": np.array([1.0]), "cluster": np.array([0])}
    tr = integrate(grid, rel, T0 + 4 * 3600, dt_s=900)
    lat, lon = tr["lat"][0], tr["lon"][0]
    assert np.allclose(lat, 30.0, atol=1e-9)
    expected_dlon = 5.0 * 4 * 3600 / (111_320 * math.cos(math.radians(30.0)))
    assert math.isclose(lon[-1] - 75.0, expected_dlon, rel_tol=1e-6)


def test_bilinear_interpolation_is_exact_at_nodes_and_linear_between():
    times = [T0, T0 + 3600]
    u = np.zeros((2, SPEC["ny"], SPEC["nx"]))
    for i in range(SPEC["nx"]):
        u[:, :, i] = i  # u grows with x index
    u[1] += 10  # and with time
    g = WindGrid(SPEC["lon0"], SPEC["lat0"], SPEC["d"], times, u, np.zeros_like(u))
    uu, _ = g.sample(np.array([28.0]), np.array([SPEC["lon0"] + 2 * SPEC["d"]]), np.array([T0]))
    assert math.isclose(uu[0], 2.0)
    uu, _ = g.sample(np.array([28.0]), np.array([SPEC["lon0"] + 2.5 * SPEC["d"]]), np.array([T0 + 1800]))
    assert math.isclose(uu[0], 2.5 + 5.0)


def test_kernel_integrates_to_weight():
    params = dict(P)
    xs = np.linspace(-2, 2, 201)
    lat, lon = np.meshgrid(xs + 30.0, xs + 76.0, indexing="ij")
    c = raw_contributions([30.0], [76.0], [0.0], [1.0], lat.ravel(), lon.ravel(), params)
    cell_km2 = (xs[1] - xs[0]) * 111.32 * (xs[1] - xs[0]) * 111.32 * math.cos(math.radians(30.0))
    assert math.isclose(c.sum() * cell_km2, 1.0, rel_tol=0.02)


def test_decay_and_spread_reduce_peak_with_age():
    a = raw_contributions([30.0], [76.0], [0.0], [1.0], [30.0], [76.0], P)[0, 0]
    b = raw_contributions([30.0], [76.0], [24.0], [1.0], [30.0], [76.0], P)[0, 0]
    assert b < a * math.exp(-1)  # e-fold decay plus a wider puff
    assert sigma_km(1000, P) == P["sigma_max_km"]


def test_reference_scenario_peaks_at_target():
    ref = P["reference_scenario"]
    rh = int(P["release_hours"]["value"])
    times = list(range(T0, T0 + 60 * 3600, 3600))
    grid = uniform_grid(SPEC, times, speed=ref["wind_ms"], direction_deg=270.0, blh=None)
    lon_src = 77.0 - ref["distance_km"] / (111.32 * math.cos(math.radians(30.0)))
    rel = {"lat0": np.full(rh, 30.0), "lon0": np.full(rh, lon_src), "t0": T0 + 3600 * np.arange(rh),
           "w": np.full(rh, ref["frp_mw"] / rh), "cluster": np.zeros(rh, int)}
    tr = integrate(grid, rel, T0 + 40 * 3600)
    peak = 0.0
    for k, t in enumerate(tr["times"]):
        ok = ~np.isnan(tr["lat"][:, k])
        if ok.any():
            c = raw_contributions(tr["lat"][ok, k], tr["lon"][ok, k], (t - rel["t0"][ok]) / 3600, rel["w"][ok],
                                  [30.0], [77.0], P).sum()
            peak = max(peak, 100 * c / s_ref(P))
    assert 65 <= peak <= 85  # hourly sampling of the analytic peak


def test_csv_parsing_and_filters():
    csv = ("latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight\n"
           "30.25,75.84,330,0.4,0.4,2026-10-10,0812,N20,nominal,2.0NRT,290,6.5,D\n"
           "30.2501,75.8401,331,0.4,0.4,2026-10-10,0900,N21,high,2.0NRT,290,9.0,D\n"   # same fire, other satellite
           "30.40,75.90,320,0.4,0.4,2026-10-10,0812,N20,low,2.0NRT,290,3.0,D\n"        # low confidence
           "29.48,76.90,350,0.4,0.4,2026-10-10,0812,N20,high,2.0NRT,290,40.0,D\n"      # refinery flare
           "15.0,100.0,330,0.4,0.4,2026-10-10,0812,N20,high,2.0NRT,290,6.0,D\n")       # outside the region
    rows = parse_firms_csv(csv)
    assert len(rows) == 5
    kept = dedupe(filter_fires(rows, P))
    assert len(kept) == 1 and kept[0]["frp"] == 9.0


def test_clusters_label_and_sum():
    rows = [{"lat": 30.25, "lon": 75.84, "frp": 4.0, "t": T0, "sat": "N", "conf": "n"},
            {"lat": 30.26, "lon": 75.85, "frp": 6.0, "t": T0 + 60, "sat": "N", "conf": "n"}]
    cs = cluster(rows, P)
    assert len(cs) == 1 and cs[0]["n_fires"] == 2 and cs[0]["frp_mw"] == 10.0
    assert cs[0]["district"] == "Sangrur" and cs[0]["state"] == "Punjab"


def test_levels_arrival_and_clears():
    assert level_of(10, P) == "none" and level_of(20, P) == "light"
    assert level_of(40, P) == "moderate" and level_of(75, P) == "heavy"
    times = np.arange(10) * 3600
    s = summarize_series(np.array([0, 10, 40, 70, 50, 20, 40, 0, 0, 0]), times, P)
    assert s["arrival"] == 2 * 3600 and s["clears"] == 5 * 3600
    assert s["peak"] == {"t": 3 * 3600, "index": 70} and s["level_24h"] == "heavy"


def test_attribution_sums_to_100():
    cs = [{"district": "Sangrur", "state": "Punjab"}, {"district": "Patiala", "state": "Punjab"},
          {"district": "Sangrur", "state": "Punjab"}]
    a = attribution(np.array([2.0, 1.0, 1.0]), cs)
    assert a[0]["label"] == "Sangrur" and a[0]["pct"] == 75
    assert sum(x["pct"] for x in a) == 100


def test_end_to_end_nw_wind_puts_smoke_over_delhi_not_amritsar():
    now = T0 + 12 * 3600
    rows = [{"lat": 30.25 + 0.02 * i, "lon": 75.84 + 0.02 * i, "frp": 60.0, "t": now - 4 * 3600,  # ~1,800 MW: a peak-season day
             "sat": "N20", "conf": "nominal"} for i in range(30)]
    grid = uniform_grid(SPEC, list(range(now - 24 * 3600, now + 40 * 3600, 3600)), 5.5, 315.0)
    out = build_outputs(rows, grid, now, P)
    places = {p["id"]: p for p in out["places.json"]}
    assert places["rohini"]["peak"]["index"] > 10
    assert places["amritsar"]["peak"]["index"] < 2  # upwind
    assert places["rohini"]["sources"][0]["label"] in {"Sangrur", "Malerkotla", "Barnala"}
    sm = out["smoke.json"]
    frame = np.frombuffer(base64.b64decode(sm["frames"][0]), np.uint8)
    assert frame.size == sm["grid"]["nx"] * sm["grid"]["ny"] and frame.max() <= 100
    assert len(sm["times"]) == P["forecast_hours"] + 1
    assert out["hotspots.json"]["clusters"][0]["rank"] == 1
    assert out["trails.json"]["paths"] and len(out["trails.json"]["paths"][0]["path"][0]) == 3


def test_no_fires_is_quiet_not_broken():
    now = T0
    grid = uniform_grid(SPEC, list(range(now - 3600, now + 40 * 3600, 3600)), 3.0, 0.0)
    out = build_outputs([], grid, now, P)
    assert out["meta.json"]["fires_24h"] == 0
    assert all(p["level_24h"] == "none" for p in out["places.json"])
    assert out["hotspots.json"]["clusters"] == []
