# Sources and checks

| What | Value used | Source | Checked |
|---|---|---|---|
| Fire detections | VIIRS S-NPP / NOAA-20 / NOAA-21 NRT 375 m, public 24 h CSVs (South Asia); archive via FIRMS area API (`VIIRS_SNPP_SP`, `VIIRS_NOAA20_SP`) | [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | 10 Oct 2026 (live fetch: 607 fires in domain) |
| Confidence field | public CSVs use `low` / `nominal` / `high`; API may use `l` / `n` / `h` — both handled | FIRMS CSV header | 10 Oct 2026 |
| Winds and mixing height | 925 hPa wind + 10 m wind + boundary-layer height, hourly | [Open-Meteo forecast API](https://open-meteo.com/en/docs), [historical forecast API](https://open-meteo.com/en/docs/historical-forecast-api) | 10 Oct 2026 |
| 2025 season daily fire counts (S-NPP only, domain) | peak 31 Oct 2025: 1,212 detections, ~6,380 MW FRP | FIRMS archive (our query) | 10 Oct 2026 |
| Delhi AQI 31 Oct → 1 Nov 2025 | 218 → 251; 8 stations "very poor"; worst Wazirpur 333 (north-west Delhi) | [The Daily Guardian, citing CPCB](https://thedailyguardian.com/india/delhi-aqi-on-novenmebr-1-2025-delhi-breathes-polluted-air-again-aqi-touches-251-mark-677349/) | 10 Oct 2026 |
| Stubble share of Delhi PM2.5, Nov 2025 (context) | DSS estimates ~8.6% on 7 Nov, forecast ~31% on 9 Nov; 22.4% on 12 Nov | [Daily Pioneer](https://www.dailypioneer.com/2025/india/delhi-tops-pollution-charts-as-aqi-hits-322.html), [SuperKalam summary](https://superkalam.com/current-affairs/08-11-2025/transport-farm-fires-keep-air-very-poor-pg3-ff20afe8-d479-4a81-8588-de8b4b27fa9f) | 10 Oct 2026 |
| Plume spread, decay, release hours | σ = 5 km + 3 km/h × age (max 80 km); 24 h e-folding; 6 hourly releases | design assumptions, see `backend/src/engine/data/parameters.json` | approx |
| Place populations | rough weights for ranking only | approximate city/zone estimates | approx |
