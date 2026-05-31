# The Bitcoin Spiral: technical reference

The companion to the narrative write-up ([how-it-works.html](../how-it-works.html)).
This is the full mechanism: the maths, the data sources, the exact signal
weighting, and how the pipeline stays secure without a single API key. All of it
is reproducible from this repository.

---

## 1. Architecture

```
                     ┌──────────────────────────────────────────────┐
  free public APIs   │  Your browser (dashboard.html / index.html)  │
  (CoinGecko, etc.)  │  fetch() -> compute -> render. No backend.   │
                     └──────────────────────────────────────────────┘
                                        ▲  static files
                                        │  (GitHub Pages)
   ┌────────────────────────────────────────────────────────────────┐
   │  GitHub Actions, every 6h (.github/workflows/pages.yml)          │
   │  update_prices -> generate.py -> fetch flows/news ->             │
   │  build_prompt -> GitHub Models -> write_commentary -> commit     │
   └────────────────────────────────────────────────────────────────┘
```

Two independent surfaces share one model:

- **Client side.** `dashboard.html` and `index.html` are self-contained HTML, SVG
  and JavaScript. They fetch from free public APIs at runtime and render in the
  browser. No server, no database, no build step.
- **CI side.** A scheduled GitHub Action refreshes the data, regenerates the SVG,
  asks an AI model for a market note, commits the results back, and redeploys to
  GitHub Pages. Cadence: on push to `main`, every 6 hours via cron, and on manual
  dispatch.

---

## 2. Secrets and API keys (the short answer: there are none)

The question "how does it work short of publishing API keys" has a clean answer:
**there are no API keys to publish, because nothing in the stack requires one.**

- Every data source is free, public and keyless (see section 9). No registration,
  no bearer tokens, no secrets in the client bundle. View source on the dashboard
  and you will not find a credential, because there isn't one.
- The single credential anywhere in the system is the **`GITHUB_TOKEN`** that
  GitHub injects into the Action at runtime. It is never committed, never printed,
  and is automatically masked in logs. Its scopes are declared in the workflow and
  nothing more:

  ```yaml
  permissions:
    contents: write   # commit refreshed JSON + SVG back to the repo
    pages: write      # publish to GitHub Pages
    id-token: write   # OIDC for the Pages deploy
    models: read      # GitHub Models inference
  ```

- **GitHub Models** inference is authenticated by that same managed token via the
  `actions/ai-inference` action. There is no OpenAI key, no billing account.
- `.gitignore` blocks the usual footguns regardless (`​.env`, `*.key`, `*.pem`,
  `credentials*.json`, `*token*.txt`) so a stray secret cannot be committed by
  accident.

If you fork this and add a source that *does* need a key, put it in repository
**Actions secrets** and reference it as `${{ secrets.NAME }}`. It stays server side
in CI and never reaches the static client.

---

## 3. The Power-Law model

Bitcoin's long-run price is modelled as a power law of time since the genesis
block (block 0, **2009-01-03**):

```
log10(P) = a + n · log10(d)
```

where `d` is the number of days since genesis and `n = 5.8`. Three parallel lines
(three values of the intercept `a`) define the channel:

| Line | Constant | Role |
|---|---:|---|
| Support / floor | `a = -17.32` | historical cycle bottoms |
| Fair value | `a = -17.01` | central trend |
| Resistance / cycle-top | `a = -16.50` | historical cycle tops |

Defined once in both `generate.py` and the dashboard JS (kept in sync by hand):

```python
N = 5.8
A_SUP, A_FAIR, A_RES = -17.32, -17.01, -16.5
GENESIS = date(2009, 1, 3)

def pl(d, a):                       # price level on date d for intercept a
    days = (d - GENESIS).days
    return 10 ** (a + N * math.log10(days))
```

The exponent `n = 5.8` is Santostasi's published value; the intercepts are
calibrated to fit the established price history and are therefore approximate
(see section 11). They are the one place to retune if you re-fit the model.

---

## 4. The spiral mapping (generate.py)

The SVG is a polar plot. Price becomes radius, calendar time becomes angle.

**Radius** is logarithmic, so each 10x in price is a fixed step outward:

```
radius(P) = INNER + max(2, K · (log10(P) - log10(P0)))
```

with `K = 80` px per decade, `INNER = 56` px (an empty hub so the sub-$10 years
do not collapse into a dot), `P0 = 1` ($1 at the centre), centred at `(620, 630)`
on a `1240 x 1240` canvas.

**Angle** encodes position in the **calendar four-year cycle**, not time since
halving. One full turn is four years, with 1 January of 2013 / 2017 / 2021 / 2025
all landing at 0 degrees (east), running counter-clockwise:

```
phase(d)  = ((decimal_year(d) - 2013) mod 4) / 4
angle(d)  = 2π · phase(d)
xy(P, d)  = (CX + r·cos θ,  CY - r·sin θ)
```

Monthly closes come from `data/btc-monthly.json`; the channel spirals are sampled
from `PL_START = 2011-07-01` to the latest month. Months priced under $1 are
skipped so the noisy early history does not crowd the hub.

---

## 5. The Power-Law oscillator

A single normalised "where in the channel are we" number, `0` at the floor and `1`
at the cycle-top band, on a log scale:

```
osc(P, d) = clamp(  (log10(P) - log10(floor_d)) /
                    (log10(top_d) - log10(floor_d)),  0, 1 )
```

where `floor_d = pl(d, A_SUP)` and `top_d = pl(d, A_RES)`. This drives both the
colour of the price line on the spiral and the headline valuation signal in the
verdict.

---

## 6. Dashboard indicators

All computed client side in `dashboard.html` from the sources in section 9.

| Indicator | Formula | Read | Citation |
|---|---|---|---|
| **Power-Law fair / vs-fair** | `fair = pl(today, A_FAIR)`; `vsFair = price / fair` | <100% = below trend | Santostasi |
| **Oscillator** | section 5 | 0 floor, 1 top | Santostasi |
| **Mayer Multiple** | `price / SMA200(daily close)` | <1 cheap, >2.4 only near tops | Mayer |
| **Pi Cycle Top** | `gap = (2·SMA350 - SMA111) / (2·SMA350) · 100` | gap ≤ 0 means the 111DMA has crossed above 2×350DMA, a historical top signal | Swift |
| **MVRV** | `CapMVRVCur` (market value / realised value) | <1 undervalued, >3.5 euphoria | Mahmudov & Puell |
| **Fear & Greed** | index value 0–100 | <25 extreme fear, >75 extreme greed | Alternative.me |
| **Taker pressure (7d)** | `Σ takerBuyBaseVol / Σ volume · 100` over 7 daily klines | >50% = net aggressive buying | Binance kline field 9 |
| **BTC / Gold** | `price_BTC / price_PAXG` | oz-of-gold per BTC | PAXG proxy |

Moving averages use simple means of daily closes (`SMA(n)` = mean of the last `n`
closes). The price/Power-Law and Mayer charts pull 365 days from CoinGecko; Pi
Cycle and taker pressure pull up to ~1000 daily klines from Binance.

---

## 7. The verdict engine

Six signals are mapped to a score in `[-1, +1]` (negative = distribute, positive =
accumulate), then combined as a weighted mean. The exact definitions
(`dashboard.html`, `renderVerdict()`):

| Signal | Input | Score function | Weight |
|---|---|---|---:|
| Valuation | `osc` (0–1) | `1 - 2·osc` | 1.2 |
| vs Fair | `vsFair` (ratio) | `clamp((1 - vsFair) / 0.4, -1, 1)` | 1.0 |
| Mayer | `mayer` | `clamp((1 - mayer) / 0.6, -1, 1)` | 1.0 |
| Cycle top | `piGap` (%) | `g≤0 → -1; g<5 → -0.7; g<15 → -0.2; else clamp((g-15)/40, 0, 0.3)` | 1.5 |
| Sentiment | `fng` (0–100) | `clamp((50 - fng) / 50, -1, 1)` | 0.6 |
| Flow 7d | `pressure` (%) | `clamp((pressure - 50) / 15, -1, 1)` | 0.5 |

```
composite = Σ(weightᵢ · scoreᵢ) / Σ(weightᵢ)      # over available signals only
```

Any signal whose feed failed is dropped from both sums, so the verdict degrades
gracefully rather than skewing. The composite maps to the banner word:

| Composite | Verdict |
|---|---|
| ≥ +0.40 | ACCUMULATE |
| ≥ +0.15 | LEAN BUY |
| > -0.15 | NEUTRAL / HOLD |
| > -0.40 | LEAN SELL |
| else | DISTRIBUTE |

Sentiment and flow are deliberately contrarian (fear and selling push the score
*up*). Cycle top carries the highest weight (1.5) because a confirmed Pi Cycle
cross has historically been the sharpest top signal.

---

## 8. The AI market note pipeline

The note under the verdict banner is regenerated every 6 hours in CI. The design
rule is strict: **the model writes prose, code owns every number.**

1. **`tools/build_prompt.py`** computes four orthogonal signals deterministically
   and writes `prompt.txt` plus `tools/_metrics.json`:
   - **Valuation:** the oscillator, plus its **base-rate percentile**: today's
     oscillator is ranked against the oscillator of *every month since 2011*
     (computed from `data/btc-monthly.json`), e.g. "higher than 84% of all
     months."
   - **Trajectory:** 30- and 90-day price change, and the Mayer Multiple, from a
     single 250-day CoinGecko history call.
   - **Sentiment:** Fear & Greed today versus a month ago.
   - **Demand:** 7- and 30-day spot-ETF net flow from `etf_flows.json`.

   Each signal is best-effort. A failed feed is simply omitted from the prompt;
   the script never raises.

2. **`actions/ai-inference`** sends `prompt.txt` to **GitHub Models**
   (`openai/gpt-4.1-mini`, `max-tokens: 280`) with a system prompt that forbids
   inventing or predicting numbers and asks for 3–4 calm sentences.

3. **`tools/write_commentary.py`** writes `commentary.json`. If the model is
   unavailable or rate-limited, it falls back to a note composed from
   `_metrics.json`, so the dashboard always shows something derived from the last
   good numbers rather than nothing (or worse, a guess).

Why the separation matters: an LLM is excellent at turning numbers into a readable
sentence and unreliable as the *source* of those numbers. Keeping the two jobs
apart means the prose always agrees with the dashboard and never hallucinates a
price target.

---

## 9. Data sources

All free, all public, all keyless.

| Source | Endpoint | Used for | Auth |
|---|---|---|---|
| CoinGecko | `/api/v3/simple/price`, `/coins/bitcoin/market_chart` | spot price, 365d / 250d history | none |
| Binance public | `data-api.binance.vision` klines | taker pressure, Pi Cycle, PAXG (BTC/Gold) | none |
| Alternative.me | `/fng/` | Fear & Greed index | none |
| mempool.space | REST API | hashrate, difficulty, Lightning capacity, fees | none |
| CoinMetrics community | `community-api.coinmetrics.io` `CapMVRVCur` | MVRV (best-effort) | none |
| Farside Investors | `farside.co.uk/bitcoin-etf-flow-all-data` | spot-ETF daily net flows (CI scrape) | none |
| CoinDesk / Cointelegraph / Bitcoin Magazine | RSS | institutional news (CI fetch) | none |
| GitHub Models | `actions/ai-inference` | the AI market note | `GITHUB_TOKEN` (managed) |

Client-side calls that hit CORS or rate limits degrade to "n/a" per panel; the
page never breaks.

---

## 10. Reproduce locally

Standard library only, no dependencies:

```bash
python3 generate.py              # rebuild btc-mandala.svg from data/btc-monthly.json
python3 generate.py out.svg      # custom output path

python3 tools/build_prompt.py    # compute signals -> prompt.txt + tools/_metrics.json
RESPONSE="" python3 tools/write_commentary.py   # exercise the computed fallback note
```

The base-rate and Power-Law maths run fully offline (they only need
`data/btc-monthly.json`). The live signals need outbound network; without it they
are skipped and the pipeline produces a neutral note, which is the intended
degraded behaviour.

To serve the static site locally:

```bash
python3 -m http.server 8000      # then open http://localhost:8000/dashboard.html
```

---

## 11. References and citations

- **Power Law model.** G. Santostasi, *The Bitcoin Power Law Theory* (2018):
  `log10(P) = a + n·log10(d)` with `n ≈ 5.8`. The intercepts used here are
  calibrated to the established price history and are approximate.
- **Mayer Multiple.** Trace Mayer (2016): price divided by the 200-day moving
  average.
- **Pi Cycle Top.** Philip Swift, LookIntoBitcoin (2019): the 111-day MA crossing
  above twice the 350-day MA.
- **MVRV.** Murad Mahmudov and David Puell (2018): market value divided by
  realised value.
- **Fear & Greed Index.** Alternative.me.
- **Genesis block.** Bitcoin block 0, mined 2009-01-03.

**Educational only. Not financial advice.** Code and output: MIT.
