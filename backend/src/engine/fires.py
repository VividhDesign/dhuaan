"""NASA FIRMS active-fire parsing, filtering, de-duplication and clustering."""
import csv
import io
import math
import urllib.request
from calendar import timegm
from datetime import datetime

from . import load_data, param

FIRMS_PUBLIC = {
    "SNPP": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_Asia_24h.csv",
    "N20": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_South_Asia_24h.csv",
    "N21": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-21-viirs-c2/csv/J2_VIIRS_C2_South_Asia_24h.csv",
}
FIRMS_AREA_API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{bbox}/{days}"

LOW_CONFIDENCE = {"l", "low"}


def fetch_public_csv(sat: str, timeout: int = 30) -> str:
    with urllib.request.urlopen(FIRMS_PUBLIC[sat], timeout=timeout) as r:
        return r.read().decode("utf-8")


def fetch_area_csv(key: str, source: str, bbox: str, days: int = 1, date: str | None = None, timeout: int = 30) -> str:
    url = FIRMS_AREA_API.format(key=key, source=source, bbox=bbox, days=days)
    if date:
        url += f"/{date}"
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read().decode("utf-8")


def parse_firms_csv(text: str, sat: str | None = None) -> list[dict]:
    """Parse a FIRMS VIIRS CSV into {lat, lon, frp, t, sat, conf} rows (t = epoch seconds UTC)."""
    rows = []
    for rec in csv.DictReader(io.StringIO(text)):
        try:
            lat, lon = float(rec["latitude"]), float(rec["longitude"])
            frp = float(rec.get("frp") or 0.0)
            hhmm = rec["acq_time"].zfill(4)
            dt = datetime.strptime(f'{rec["acq_date"]} {hhmm}', "%Y-%m-%d %H%M")
        except (KeyError, ValueError):
            continue
        rows.append({
            "lat": lat, "lon": lon, "frp": max(frp, 0.1),
            "t": timegm(dt.timetuple()),
            "sat": sat or rec.get("satellite", ""),
            "conf": (rec.get("confidence") or "").strip().lower(),
        })
    return rows


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def filter_fires(rows: list[dict], params: dict, industrial: dict | None = None) -> list[dict]:
    d = params["source_domain"]
    industrial = industrial if industrial is not None else load_data("industrial_hotspots.json")
    radius = industrial.get("radius_km", 3.0)
    sites = industrial.get("sites", [])
    out = []
    for r in rows:
        if not (d["lon_min"] <= r["lon"] <= d["lon_max"] and d["lat_min"] <= r["lat"] <= d["lat_max"]):
            continue
        if r["conf"] in LOW_CONFIDENCE:
            continue
        if any(haversine_km(r["lat"], r["lon"], s["lat"], s["lon"]) <= radius for s in sites):
            continue
        out.append(r)
    return out


def dedupe(rows: list[dict], cell_deg: float = 0.01, window_s: int = 7200) -> list[dict]:
    """Different satellites see the same fire: same ~1 km cell within 2 h -> keep the strongest."""
    best: dict[tuple, dict] = {}
    for r in sorted(rows, key=lambda r: r["t"]):
        key = (round(r["lat"] / cell_deg), round(r["lon"] / cell_deg), r["t"] // window_s)
        cur = best.get(key)
        if cur is None or r["frp"] > cur["frp"]:
            best[key] = r
    return list(best.values())


def label_point(lat: float, lon: float, hq: list | None = None) -> dict:
    hq = hq if hq is not None else load_data("district_hq.json")
    name, state, dist = None, None, 1e9
    for n, s, la, lo in hq:
        dkm = haversine_km(lat, lon, la, lo)
        if dkm < dist:
            name, state, dist = n, s, dkm
    return {"label": f"near {name}", "district": name, "state": state, "km": round(dist, 1)}


def cluster(rows: list[dict], params: dict) -> list[dict]:
    """Bin fires into ~11 km cells. A cluster is the unit we release smoke from."""
    cell = param(params, "cluster_cell_deg")
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((math.floor(r["lat"] / cell), math.floor(r["lon"] / cell)), []).append(r)
    clusters = []
    for (iy, ix), fs in groups.items():
        w = sum(f["frp"] for f in fs)
        lat = sum(f["lat"] * f["frp"] for f in fs) / w
        lon = sum(f["lon"] * f["frp"] for f in fs) / w
        clusters.append({
            "cell": f"{iy * cell:.1f}_{ix * cell:.1f}",
            "lat": round(lat, 4), "lon": round(lon, 4),
            "n_fires": len(fs), "frp_mw": round(w, 1),
            "first_seen": min(f["t"] for f in fs), "last_seen": max(f["t"] for f in fs),
            **label_point(lat, lon),
        })
    clusters.sort(key=lambda c: -c["frp_mw"])
    max_n = params.get("max_clusters", 400)
    if len(clusters) > max_n:  # keep the run inside Lambda's budget: drop the weakest clusters
        clusters = clusters[:max_n]
    for i, c in enumerate(clusters):
        c["id"] = f"c{i:03d}"
    return clusters
