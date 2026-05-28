#!/usr/bin/env python3
"""CI step: refresh data/btc-monthly.json with REAL monthly closes.

Pulls Binance BTCUSDT monthly candles (history from 2017-08) and overwrites the
corresponding months in the committed data, keeping the established pre-2017
history. The current (incomplete) month's close = latest price, so the spiral's
"you are here" point is always accurate.

Never raises: on any failure it leaves the committed prices untouched, so
generate.py still produces a valid (if slightly stale) spiral.
"""
import json, os, datetime, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "..", "data", "btc-monthly.json")

def fetch_binance_monthly():
    url = "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1M&limit=1000"
    req = urllib.request.Request(url, headers={"User-Agent": "mandala-ci/1.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        rows = json.load(r)
    out = {}
    for k in rows:
        dt = datetime.datetime.utcfromtimestamp(k[0] / 1000)
        c = float(k[4])
        out[(dt.year, dt.month)] = round(c, 2) if c < 100 else round(c)
    return out

def merge(existing_months, binance, today):
    """Pure merge: real Binance value where available, else committed value.
    Stops each year at its last contiguous month; never invents future months."""
    years = sorted({int(y) for y in existing_months} | {y for (y, _m) in binance})
    new = {}
    for y in years:
        ex = existing_months.get(str(y), existing_months.get(y, []))
        if y == today.year:
            maxm = max(today.month, len(ex))
        elif ex:
            maxm = len(ex)
        else:
            ms = [m for (yy, m) in binance if yy == y]
            maxm = max(ms) if ms else 0
        arr = []
        for m in range(1, maxm + 1):
            if (y, m) in binance:
                arr.append(binance[(y, m)])
            elif m <= len(ex):
                arr.append(ex[m - 1])
            else:
                break
        if arr:
            new[str(y)] = arr
    return new

def main():
    try:
        with open(DATA_PATH) as f:
            doc = json.load(f)
    except Exception as e:
        print("cannot read prices:", e); return
    try:
        b = fetch_binance_monthly()
    except Exception as e:
        print("binance fetch failed, keeping committed prices:", e); return
    if not b:
        print("no binance data; keeping committed prices"); return
    today = datetime.date.today()
    doc["months"] = merge(doc["months"], b, today)
    doc["_last_updated"] = today.isoformat()
    with open(DATA_PATH, "w") as f:
        json.dump(doc, f, indent=2)
    recent = {y: v for y, v in doc["months"].items() if int(y) >= 2024}
    print("updated prices through", today, "| recent months:", {y: len(v) for y, v in recent.items()})

if __name__ == "__main__":
    main()
