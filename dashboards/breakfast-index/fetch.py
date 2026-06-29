#!/usr/bin/env python3
"""Best-effort daily refresh of The Breakfast Index from FRED (no API key).

For each staple, fetch the global price series, take the base-year average as
100, and re-index the latest reading against it. Updates the current (latest)
index point, the per-item change-since-base, and the basket. Historical points
stay curated. Failures leave the committed JSON untouched.
"""
import json, os, sys, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "breakfast.json")
UA = {"User-Agent": "Mozilla/5.0 (houtini breakfast-index fetcher)"}


def fred_monthly(series_id, timeout=25):
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series_id
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        rows = [ln.split(",") for ln in r.read().decode("utf-8", "replace").strip().splitlines()[1:]]
    out = []
    for date, v in rows:
        try:
            out.append((date, float(v)))
        except ValueError:
            continue
    return out


def main():
    d = json.load(open(DATA))
    base_year = d.get("base_year", "2015")
    ok = 0
    for name, sid in d.get("fred", {}).items():
        try:
            obs = fred_monthly(sid)
            base_vals = [v for date, v in obs if date.startswith(base_year)]
            if not base_vals or not obs:
                raise RuntimeError("missing base/latest")
            base = sum(base_vals) / len(base_vals)
            latest = obs[-1][1]
            idx = round(latest / base * 100)
            d["items"][name][-1] = idx  # current-year slot
            ok += 1
            print(f"  {name}: index {idx}")
        except Exception as e:  # noqa: BLE001
            print(f"  [skip] {name}: {e}", file=sys.stderr)

    names = list(d["fred"].keys())
    cur = [{"name": n, "pct": d["items"][n][-1] - 100} for n in names]
    d["change_since_base"] = sorted(cur, key=lambda x: -x["pct"])
    d["index_now"] = round(sum(d["items"][n][-1] for n in names) / len(names))
    d["_last_updated"] = datetime.date.today().isoformat()
    with open(DATA, "w") as f:
        json.dump(d, f, indent=2); f.write("\n")
    print(f"breakfast-index fetch: {ok}/{len(d.get('fred', {}))} series refreshed")


if __name__ == "__main__":
    main()
