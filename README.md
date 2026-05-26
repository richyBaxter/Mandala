# The Bitcoin Spiral

An open-source chart by **houtini** — Bitcoin price and the **Power Law** plotted on a
**4-year-cycle polar map**, rendered as a clean, embeddable SVG.

![The Bitcoin Spiral](btc-mandala.svg)

## How to read it

| Element | Meaning |
|---|---|
| **Angle** | Position within the 4-year cycle (one full turn = 4 years; Jan of 2013/17/21/25 at east). |
| **Radius** | Price on a log scale — `$1` at the centre, each dashed ring a 10× level (`$10 → $100k`). |
| **Black line** | BTC monthly price, spiralling outward over time. |
| **Orange spiral** | Power-Law **support** (cycle bottoms). |
| **Red spiral** | Power-Law **resistance** (cycle tops). |
| **Green / red bands** | The Power-Law channel either side of each bound. |

The Power Law follows `log10(P) = a + 5.8·log10(d)`, where `d` is days since the
genesis block (2009-01-03), with `a = -17.2` (support) and `a = -16.5` (resistance).

## Indicators & overlays

| Overlay | What it shows | Source |
|---|---|---|
| **Buy / sell colour** | The BTC line is shaded **green → amber → red** by its position in the Power-Law channel (a "cheap vs expensive" oscillator). The legend gauge marks where price sits *now*. | computed from price |
| **Events diary** | Labelled markers for halvings, ETF launches and macro events. | [`data/events.csv`](data/events.csv) |
| **Institutional flow** | Radial ticks along the recent arc — outward green = spot-ETF **net buying**, inward red = **net selling** — a "who's buying" read. | [`data/flows.csv`](data/flows.csv) |

Edit the CSVs and re-run `generate.py` to update any overlay. To refresh ETF flows
from a live free source, see [`fetch_flows.py`](fetch_flows.py):

```bash
FLOWS_URL="https://your-free-source/btc-etf-daily.csv" python3 fetch_flows.py
python3 generate.py
```

> The flow figures shipped here are **approximate seed values**. Wire `fetch_flows.py`
> to a free feed (e.g. Farside Investors) for accurate numbers.

## Embed

The chart is a single self-contained `.svg`:

```html
<img src="https://richybaxter.github.io/btc-mandala/btc-mandala.svg"
     alt="The Bitcoin Spiral" style="max-width:100%;height:auto">
```

Or inline the contents of `btc-mandala.svg` directly for crisp scaling.

## Regenerate / update data

Prices live in [`data/btc-monthly.json`](data/btc-monthly.json) as monthly closes.
Edit them and re-render (only the Python standard library is required):

```bash
python3 generate.py            # writes btc-mandala.svg
python3 generate.py out.svg    # custom output path
```

## Data notes

Prices are **approximate monthly closes**. The 2011–2024 series is well-established
history; 2025–2026 is anchored to verified data points:

- All-time high **$126,198 on 6 Oct 2025**
- ~30% retrace into year-end (~$87k)
- ~**$77k in May 2026**

## Credit & licence

Chart by **houtini**. The underlying **Power-Law model** is the work of
**G. Santostasi**, whose original cyclical "Mandala" visualisation inspired this view.
This repository is for embedding and education — **not financial advice**.

Code and SVG output: [MIT](LICENSE).
