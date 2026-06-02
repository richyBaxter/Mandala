# Arterial Flow: maritime chokepoints

A live macro map of the world's shipping chokepoints. Each node is sized by transit
volume and coloured by how far current traffic sits from its 2024 baseline; when a
chokepoint is constrained, a diversion overlay traces the bleed onto longer routes
(the Red Sea to Cape of Good Hope case). Same architecture as the Bitcoin Spiral:
a GitHub Action fetches public data, a Python transform writes a compact static
JSON, and the browser renders it with no backend and no API key.

**Live:** `/dashboards/maritime/` on the Pages site.

## Files

| File | Role |
|---|---|
| `index.html` | No-build frontend. MapLibre GL JS (CDN, keyless basemap), recoloured to the Mandala dark theme. |
| `transform.py` | Pure functions: `parse_features()` (ArcGIS response -> records) and `build()` (records -> dashboard JSON). No network, fully unit-tested. |
| `fetch.py` | CI step: pulls recent PortWatch records, calls the transform, writes `chokepoint_deviations.json`. Best-effort, never overwrites with empty data. |
| `chokepoints_meta.json` | Static chokepoint coordinates + approximate 2024 baselines. |
| `chokepoint_deviations.json` | The rendered output. Committed copy is an illustrative **sample** (badged in the UI) until CI writes live data. |
| `tests/` | `unittest` suite over a fixture ArcGIS response. |

## Data source

IMF PortWatch "Daily Chokepoints" layer, hosted on ArcGIS Online (public, **no key**):

```
https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/FeatureServer/0/query
```

`fetch.py` queries `?where=1=1&outFields=*&orderByFields=date DESC&f=json` for the most
recent records across all chokepoints. PortWatch's column names have drifted, so
`parse_features()` matches the transit field defensively
(`n_transit_calls` / `portcalls` / `transit_calls` / ...) and folds `import + export`
into a trade figure. If the service name has changed, override it without a code edit:

```bash
PORTWATCH_URL="https://.../FeatureServer/0/query" python3 dashboards/maritime/fetch.py
```

## Method

- **Deviation** = `(7-day mean transit calls - 2024 baseline) / baseline`.
- **Status**: constrained `<= -15%`, elevated `>= +15%`, otherwise normal.
- **Diversion proxy** (`transits_below_baseline_per_day`) = the summed daily transit
  shortfall across all chokepoints, an indicative measure of traffic pushed onto
  longer routes. It is derived from aggregate transit counts, not vessel-level tracking.

The 2024 baselines in `chokepoints_meta.json` are approximate and the honest weak point
of v1; they are the one thing to refine (ideally by computing the 2024 mean live in CI
via an ArcGIS `outStatistics` AVG query). The deviation is only as good as the baseline.

## Run locally

```bash
python3 -m unittest discover -s dashboards/maritime/tests -v   # offline, fixture-based
python3 dashboards/maritime/fetch.py                           # needs network; writes the JSON
python3 -m http.server 8000                                    # open /dashboards/maritime/
```

## CI

A best-effort step in `.github/workflows/pages.yml` runs `fetch.py` on the existing
schedule and commits `chokepoint_deviations.json` back, alongside the Bitcoin refresh.
PortWatch updates daily, so the shared cadence is ample.

**Not investment or routing advice.** Code: MIT.
