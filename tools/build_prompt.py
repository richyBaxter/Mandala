#!/usr/bin/env python3
"""CI step: gather live BTC signals, compute them deterministically, write the AI prompt.

The model is a writer, not a calculator: every number it sees is computed here in
Python, and the prompt tells it to use only those figures. That keeps the note
consistent with the dashboard and stops the model inventing data.

Signals (each best-effort; a feed that fails is simply left out of the prompt):
  Valuation   Power-Law fair/floor/top, oscillator, and where today's oscillator
              ranks against every month since 2011 (base rate, from data/).
  Trajectory  30- and 90-day price change, plus the Mayer Multiple (price / 200DMA).
  Sentiment   Fear & Greed today, and a month ago.
  Flows       7- and 30-day US spot-ETF net flow (from etf_flows.json, if present).

Outputs:
  prompt.txt          -> user prompt for the model (consumed by actions/ai-inference)
  tools/_metrics.json -> the computed numbers (consumed by write_commentary.py fallback)

Stdlib only. Never raises: if the price feed fails, it writes a minimal prompt so
the pipeline still produces a (neutral) note.
"""
import json, math, datetime, os, urllib.request

GENESIS = datetime.date(2009, 1, 3)
N, A_SUP, A_FAIR, A_RES = 5.8, -17.32, -17.01, -16.5
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UA = {"User-Agent": "mandala-ci"}


def get_json(url, timeout=30):
    """Fetch and parse JSON; return None on any failure (never raises)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return json.load(r)
    except Exception as e:
        print("fetch failed:", url.split("?")[0], "-", e)
        return None


def pl(d, a):
    """Power-Law level for coefficient a on date d."""
    return 10 ** (a + N * math.log10((d - GENESIS).days))


def osc(price, d):
    """Position 0..1 up the floor-to-top channel on date d."""
    lo, hi = math.log10(pl(d, A_SUP)), math.log10(pl(d, A_RES))
    return max(0.0, min(1.0, (math.log10(price) - lo) / (hi - lo)))


metrics = {}
facts = []

# ---- Valuation: Power-Law model + historical base rate -----------------------
data = get_json("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
price = float(data["bitcoin"]["usd"]) if data and "bitcoin" in data else None

if price:
    today = datetime.date.today()
    fair, floor, top = pl(today, A_FAIR), pl(today, A_SUP), pl(today, A_RES)
    osc_pct = round(osc(price, today) * 100)
    vs_fair = round(price / fair * 100)
    metrics.update(price=round(price), fair=round(fair), floor=round(floor),
                   top=round(top), osc_pct=osc_pct, vs_fair_pct=vs_fair)

    # base rate: how today's oscillator ranks against every historical month
    try:
        with open(os.path.join(ROOT, "data", "btc-monthly.json")) as f:
            months = json.load(f)["months"]
        hist, first_year = [], None
        for y, closes in months.items():
            year = int(y)
            first_year = year if first_year is None else min(first_year, year)
            for i, p in enumerate(closes):
                if p and p >= 1:
                    hist.append(osc(p, datetime.date(year, i + 1, 15)))
        if hist:
            pctile = round(100 * sum(1 for h in hist if h <= osc(price, today)) / len(hist))
            metrics.update(osc_pctile=pctile, first_year=first_year)
            facts.append(
                f"Power-Law model (Santostasi): price ${metrics['price']:,} is {vs_fair}% of fair "
                f"value (${metrics['fair']:,}); floor ${metrics['floor']:,}, cycle-top band "
                f"${metrics['top']:,}. The oscillator sits {osc_pct}% up the floor-to-top channel, "
                f"higher than {pctile}% of all months since {first_year}.")
    except Exception as e:
        print("base-rate compute skipped:", e)
    if "osc_pctile" not in metrics:
        facts.append(
            f"Power-Law model (Santostasi): price ${metrics['price']:,} is {vs_fair}% of fair "
            f"value (${metrics['fair']:,}); floor ${metrics['floor']:,}, cycle-top band "
            f"${metrics['top']:,}. The oscillator sits {osc_pct}% up the floor-to-top channel.")

    # ---- Trajectory: 30/90-day change + Mayer Multiple -----------------------
    hist = get_json("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
                    "?vs_currency=usd&days=250&interval=daily")
    closes = [p for _, p in hist["prices"]] if hist and "prices" in hist else []
    if len(closes) >= 200:
        mayer = price / (sum(closes[-200:]) / 200)
        metrics["mayer"] = round(mayer, 2)
        facts.append(f"Mayer Multiple {mayer:.2f} (price divided by its 200-day average; below 1 is "
                     "historically cheap, above 2.4 has only happened near cycle tops).")
    if len(closes) >= 91:
        chg30 = round((price / closes[-31] - 1) * 100)
        chg90 = round((price / closes[-91] - 1) * 100)
        metrics.update(chg30=chg30, chg90=chg90)
        facts.append(f"Price is {chg30:+d}% over the last 30 days and {chg90:+d}% over 90 days.")

# ---- Sentiment: Fear & Greed today vs a month ago ----------------------------
fng = get_json("https://api.alternative.me/fng/?limit=30")
fng_items = fng.get("data") if isinstance(fng, dict) else None
if fng_items:
    now = fng_items[0]
    metrics.update(fng=int(now["value"]), fng_label=now.get("value_classification", ""))
    line = f"Fear & Greed index {metrics['fng']} ({metrics['fng_label']})"
    if len(fng_items) >= 30:
        line += f", versus {int(fng_items[29]['value'])} a month ago"
    facts.append(line + ".")

# ---- Flows: US spot-ETF net flow (written earlier in CI) ---------------------
for path in (os.path.join(os.getcwd(), "etf_flows.json"), os.path.join(ROOT, "etf_flows.json")):
    try:
        with open(path) as f:
            items = json.load(f).get("items", [])
        vals = [it["net_flow_musd"] for it in items if it.get("net_flow_musd") is not None]
        if vals:
            flow7, flow30 = round(sum(vals[-7:])), round(sum(vals[-30:]))
            metrics.update(flow7=flow7, flow30=flow30)
            trend = "net inflows" if flow7 > 0 else "net outflows" if flow7 < 0 else "flat"
            facts.append(f"US spot-ETF net flow: ${flow7:+,}M over 7 days and ${flow30:+,}M over "
                         f"30 days ({trend}).")
        break
    except Exception:
        continue

# ---- Assemble ----------------------------------------------------------------
with open(os.path.join(HERE, "_metrics.json"), "w") as f:
    json.dump(metrics, f)

if facts:
    prompt = ("Today's Bitcoin signals (every figure is pre-computed; use only these, add no "
              "numbers of your own):\n" + "\n".join("- " + f for f in facts) +
              "\n\nWrite the market note as instructed: where price sits versus the long-term "
              "model, the recent trajectory, one historical base rate if given, and a measured "
              "stance. Lead with position, not prediction.")
else:
    prompt = ("Live Bitcoin market data is temporarily unavailable. Write one calm, neutral "
              "sentence noting that live data could not be retrieved right now.")

with open(os.path.join(os.getcwd(), "prompt.txt"), "w") as f:
    f.write(prompt)
print(f"wrote prompt.txt ({len(facts)} signals) and tools/_metrics.json")
