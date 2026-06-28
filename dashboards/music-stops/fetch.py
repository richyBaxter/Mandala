#!/usr/bin/env python3
"""Best-effort daily refresh of the live 'music-stops' series.

Standard-library only, mirrors the repo's other fetchers. Every source is
wrapped so a failure leaves the committed JSON untouched — the page never breaks.

Live sources (free, no API key):
  - FRED  T10Y3M  -> yieldcurve.json   (10Y-3M Treasury spread; the fast-mover)
  - multpl.com    -> cape.json         (Shiller CAPE current value, best-effort scrape)

Curated series (Buffett Indicator, concentration, dry powder, recession_prob,
timeline) are documented in README.md and refreshed by hand — they move slowly.
"""
import json, os, re, sys, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
UA = {"User-Agent": "Mozilla/5.0 (houtini music-stops fetcher)"}


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def _save(name, obj):
    with open(os.path.join(DATA, name), "w") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


def refresh_yield_curve():
    """FRED T10Y3M -> monthly spread series + current value."""
    csv = _get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y3M")
    rows = [ln.split(",") for ln in csv.strip().splitlines()[1:]]
    # keep last observation per month where value is numeric
    monthly = {}
    last_date = last_val = None
    for date, val in rows:
        try:
            v = float(val)
        except ValueError:
            continue
        monthly[date[:7]] = round(v, 2)
        last_date, last_val = date, round(v, 2)
    if not monthly:
        raise RuntimeError("no numeric T10Y3M rows")
    # take the most recent 24 months for a clean chart
    keys = sorted(monthly)[-24:]
    series = [{"t": k, "v": monthly[k]} for k in keys]

    d = _load("yieldcurve.json")
    d["series"] = series
    d["current"] = {"value": last_val, "date": last_date[:7],
                    "label": datetime.datetime.strptime(last_date, "%Y-%m-%d").strftime("%b %Y")}
    d["_last_updated"] = datetime.date.today().isoformat()
    _save("yieldcurve.json", d)
    print(f"  yieldcurve: {last_val} ({last_date})  [{len(series)} months]")


def refresh_cape():
    """multpl.com -> current Shiller CAPE value (best-effort scrape)."""
    html = _get("https://www.multpl.com/shiller-pe")
    m = re.search(r"Current\s+Shiller\s+PE\s+Ratio[^0-9]*([0-9]{1,2}\.[0-9]{1,2})", html, re.I)
    if not m:
        m = re.search(r'id="current">\s*([0-9]{1,2}\.[0-9]{1,2})', html)
    if not m:
        raise RuntimeError("could not parse CAPE from multpl")
    val = round(float(m.group(1)), 2)
    today = datetime.date.today()
    d = _load("cape.json")
    d["current"] = {"value": val, "date": today.strftime("%Y-%m"), "label": today.strftime("%b %Y")}
    # update / append the current-year point so the chart tip stays current
    yr = str(today.year)
    pts = [p for p in d["series"] if p["t"] != yr]
    pts.append({"t": yr, "v": val})
    d["series"] = sorted(pts, key=lambda p: p["t"])
    d["_last_updated"] = today.isoformat()
    _save("cape.json", d)
    print(f"  cape: {val}")


def main():
    ok = 0
    for name, fn in (("yield curve", refresh_yield_curve), ("CAPE", refresh_cape)):
        try:
            fn()
            ok += 1
        except Exception as e:  # noqa: BLE001 - best-effort, never fail the build
            print(f"  [skip] {name}: {e}", file=sys.stderr)
    print(f"music-stops fetch: {ok}/2 live series refreshed")


if __name__ == "__main__":
    main()
