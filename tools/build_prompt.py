#!/usr/bin/env python3
"""CI step: fetch live BTC data, compute Power-Law signals, write the AI prompt.

Outputs:
  prompt.txt          -> user prompt for the model (consumed by actions/ai-inference)
  tools/_metrics.json -> the numbers (consumed by write_commentary.py for the fallback)

Stdlib only. Never raises: if the price feed fails, it writes a minimal prompt so
the pipeline still produces a (neutral) note.
"""
import json, math, datetime, os, urllib.request

GENESIS = datetime.date(2009, 1, 3)
N, A_SUP, A_FAIR, A_RES = 5.8, -17.32, -17.01, -16.5
HERE = os.path.dirname(os.path.abspath(__file__))

def fetch_price():
    req = urllib.request.Request(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        headers={"User-Agent": "mandala-ci"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return float(json.load(r)["bitcoin"]["usd"])

metrics = {}
try:
    price = fetch_price()
    days = (datetime.date.today() - GENESIS).days
    lg = math.log10(days)
    fair = 10 ** (A_FAIR + N * lg)
    sup = 10 ** (A_SUP + N * lg)
    res = 10 ** (A_RES + N * lg)
    osc = max(0.0, min(1.0, (math.log10(price) - math.log10(sup)) / (math.log10(res) - math.log10(sup))))
    metrics = {
        "price": round(price), "fair": round(fair), "floor": round(sup), "top": round(res),
        "osc_pct": round(osc * 100), "vs_fair_pct": round(price / fair * 100),
    }
except Exception as e:
    print("price/compute failed:", e)

with open(os.path.join(HERE, "_metrics.json"), "w") as f:
    json.dump(metrics, f)

if metrics:
    prompt = (
        f"Bitcoin is ${metrics['price']:,} today. Power-Law model: fair value ${metrics['fair']:,}, "
        f"floor ${metrics['floor']:,}, cycle-top band ${metrics['top']:,}. Price is "
        f"{metrics['vs_fair_pct']}% of fair value and {metrics['osc_pct']}% up the floor-to-top channel. "
        "Write a calm 2-3 sentence market note for a Bitcoin dashboard: where price sits versus the "
        "long-term model, what that has historically implied, and a measured stance (accumulate / neutral "
        "/ distribute). No price predictions, no hype, no financial advice."
    )
else:
    prompt = ("Live Bitcoin market data is temporarily unavailable. Write one calm, neutral sentence "
              "noting that live data could not be retrieved right now.")

with open(os.path.join(os.getcwd(), "prompt.txt"), "w") as f:
    f.write(prompt)
print("wrote prompt.txt and tools/_metrics.json")
