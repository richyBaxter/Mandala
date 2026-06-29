#!/usr/bin/env python3
"""Best-effort daily refresh of The Price of Power from FRED (no API key).

Refreshes the fossil block only: the latest WTI/Brent/Henry Hub/gasoline
levels, and three indexed series (each to its first month = 100) for the
chart. The lcoe and non_usd blocks are curated and left untouched. Every
source is wrapped so a failure leaves the committed JSON as-is — the page
never breaks.
"""
import json, os, sys, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ENERGY = os.path.join(HERE, "data", "energy.json")
UA = {"User-Agent": "Mozilla/5.0 (houtini price-of-power fetcher)"}
# label in JSON -> FRED series id
SCALARS = {"wti": "DCOILWTICO", "brent": "DCOILBRENTEU", "henry_hub": "DHHNGSP", "gasoline": "GASREGW"}
# indexed chart lines -> FRED series id
LINES = {"wti_idx": "DCOILWTICO", "gas_idx": "DHHNGSP", "pump_idx": "GASREGW"}
START = "2019-01"  # base month for indexing


def fred_rows(series_id, timeout=25):
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series_id
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return [ln.split(",") for ln in r.read().decode("utf-8", "replace").strip().splitlines()[1:]]


def latest(series_id):
    val = None
    for _date, v in fred_rows(series_id):
        try:
            val = round(float(v), 2)
        except ValueError:
            continue
    return val


def monthly(series_id):
    """Last observation per calendar month from START onward."""
    out = {}
    for date, v in fred_rows(series_id):
        if date[:7] < START:
            continue
        try:
            out[date[:7]] = float(v)
        except ValueError:
            continue
    return out


def main():
    d = json.load(open(ENERGY))
    ok = 0

    # latest scalar levels
    for key, sid in SCALARS.items():
        try:
            v = latest(sid)
            if v is not None:
                d["fossil"][key] = v
                ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"  [skip] {key}: {e}", file=sys.stderr)

    # indexed monthly series for the chart (yearly labels, base month = 100)
    try:
        per = {k: monthly(sid) for k, sid in LINES.items()}
        # build a shared set of year-end-ish month keys: use Jan of each year present
        years = sorted({m[:4] for series in per.values() for m in series})
        labels, idx = [], {k: [] for k in LINES}
        for k, series in per.items():
            base = next((series[m] for m in sorted(series) if series.get(m)), None)
            d.setdefault("_base", {})[k] = base
        for y in years:
            # pick the first available month in that year for each line
            row, has = {}, True
            for k, series in per.items():
                months_y = sorted(m for m in series if m[:4] == y)
                if not months_y:
                    has = False; break
                row[k] = series[months_y[0]]
            if not has:
                continue
            labels.append(y)
            for k in LINES:
                base = d["_base"][k]
                idx[k].append(round(row[k] / base * 100) if base else 100)
        if labels:
            d["fossil"]["labels"] = labels
            for k in LINES:
                d["fossil"][k] = idx[k]
            d.pop("_base", None)
            ok += 1
            print("  indexed lines:", labels)
    except Exception as e:  # noqa: BLE001
        print(f"  [skip] indexed series: {e}", file=sys.stderr)
        d.pop("_base", None)

    d["_last_updated"] = datetime.date.today().isoformat()
    with open(ENERGY, "w") as fh:
        json.dump(d, fh, indent=2); fh.write("\n")
    print(f"price-of-power fetch: {ok} updates "
          f"(WTI {d['fossil']['wti']}, gas {d['fossil']['henry_hub']}, pump {d['fossil']['gasoline']})")


if __name__ == "__main__":
    main()
