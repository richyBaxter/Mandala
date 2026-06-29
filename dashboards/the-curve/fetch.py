#!/usr/bin/env python3
"""Best-effort daily refresh of The Curve from FRED (no API key).

Updates the current term structure (DGS* constant-maturity yields) and the
10Y-2Y spread series (T10Y2Y). Curated fields (the 2023 inverted snapshot,
recession_prob) are left as-is. Every source is wrapped so a failure leaves the
committed JSON untouched — the page never breaks.
"""
import json, os, sys, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CURVE = os.path.join(HERE, "data", "curve.json")
UA = {"User-Agent": "Mozilla/5.0 (houtini the-curve fetcher)"}
# maturity label -> FRED series id
SERIES = {"1M": "DGS1MO", "3M": "DGS3MO", "6M": "DGS6MO", "1Y": "DGS1", "2Y": "DGS2",
          "3Y": "DGS3", "5Y": "DGS5", "7Y": "DGS7", "10Y": "DGS10", "20Y": "DGS20", "30Y": "DGS30"}


def fred_rows(series_id, timeout=25):
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series_id
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return [ln.split(",") for ln in r.read().decode("utf-8", "replace").strip().splitlines()[1:]]


def latest(series_id):
    val = None
    for date, v in fred_rows(series_id):
        try:
            val = round(float(v), 2)
        except ValueError:
            continue
    return val


def main():
    d = json.load(open(CURVE))
    ok = 0

    # term structure: latest yield per maturity
    try:
        now = []
        for lbl in d["term_structure"]["labels"]:
            v = latest(SERIES[lbl])
            now.append(v if v is not None else d["term_structure"]["now"][d["term_structure"]["labels"].index(lbl)])
        d["term_structure"]["now"] = now
        d["ten_year"] = now[d["term_structure"]["labels"].index("10Y")]
        ok += 1
        print("  term structure:", now)
    except Exception as e:  # noqa: BLE001
        print(f"  [skip] term structure: {e}", file=sys.stderr)

    # 2s10s spread: monthly series (last 24 months) + current
    try:
        monthly, last = {}, None
        for date, v in fred_rows("T10Y2Y"):
            try:
                monthly[date[:7]] = round(float(v), 2); last = round(float(v), 2)
            except ValueError:
                continue
        if monthly:
            keys = sorted(monthly)[-24:]
            d["spread_2s10s"]["series"] = [{"t": k, "v": monthly[k]} for k in keys]
            d["spread_2s10s_current"] = last
            ok += 1
            print("  2s10s:", last)
    except Exception as e:  # noqa: BLE001
        print(f"  [skip] 2s10s: {e}", file=sys.stderr)

    d["_last_updated"] = datetime.date.today().isoformat()
    with open(CURVE, "w") as f:
        json.dump(d, f, indent=2); f.write("\n")
    print(f"the-curve fetch: {ok}/2 live series refreshed")


if __name__ == "__main__":
    main()
