# When Does the Music Stop?

A scrolling, single-page data story on the 2026/27 market-bubble warning signs —
part of the [Mandala](../../) project, by **houtini**.

**Live:** https://richybaxter.github.io/Mandala/dashboards/music-stops/

Same architecture as the rest of the repo: a single static `index.html` that
hydrates in the browser from local JSON, charts with **Chart.js** (CDN, no build
step), and a dark **houtini** house theme. Every panel degrades gracefully if a
feed or file is missing.

## The five indicators + the trigger

| # | Chapter | Headline figure | Data |
|---|---------|-----------------|------|
| 1 | Shiller CAPE | 41.6 (2nd-highest in 140 yrs) | `data/cape.json` |
| 2 | Buffett Indicator | 231.7% of GDP | `data/buffett.json` |
| 3 | Concentration | top-5 ≈ 30%, tech ≈ 48% | `data/concentration.json` |
| 4 | Yield curve (10Y−3M) | inverted; recession prob >30% | `data/yieldcurve.json` |
| 5 | Dry powder | Berkshire ~$397B cash | `data/drypowder.json` |
| — | Trigger window | Dec 2026 – May 2027 | `data/timeline.json` |

Narratives beside each chart live in `narrative.json` (AI-written in CI, with a
committed fallback so the page always reads well).

## Data refresh — free, no keys, ~$0/mo

`fetch.py` (stdlib only) refreshes the two genuinely-live series best-effort:

| Series | Source | Cadence |
|--------|--------|---------|
| Yield curve (`T10Y3M`) | FRED CSV (no key) | the fast-mover — daily earns its keep |
| Shiller CAPE (current) | multpl.com scrape | best-effort |

The Buffett Indicator, concentration, dry powder, the NY Fed recession
probability and the timeline are **curated** (slow-moving) and dated in each JSON
`_last_updated`. Refresh by editing the JSON.

The refresh runs in the existing GitHub Actions Pages workflow (`.github/workflows/pages.yml`)
on its schedule, then commits the updated JSON back. **GitHub Actions is free on
public repos and the data sources need no API key — so the sync costs nothing.**

```bash
# refresh locally
python3 dashboards/music-stops/fetch.py
# regenerate the AI prompt (for CI; writes prompt.txt, gitignored)
python3 dashboards/music-stops/build_prompt.py
```

## Develop / preview

```bash
# serve from the repo root so the relative data/ paths resolve
python3 -m http.server 8000
# open http://localhost:8000/dashboards/music-stops/
```

(Opening the file directly with `file://` blocks `fetch()`; use the local server.)

**Educational only. Not financial advice.** The "trigger window" is a narrative
interpretation of public commentary, not a forecast.
