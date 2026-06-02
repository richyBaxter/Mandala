#!/usr/bin/env python3
"""CI step: pull recent IMF PortWatch chokepoint transits and write the dashboard JSON.

Stdlib only. Best-effort: on any network/parse failure it prints and exits WITHOUT
overwriting the committed chokepoint_deviations.json, so the dashboard keeps its
last good (or sample) data rather than going blank.

Data: IMF PortWatch "Daily Chokepoints" layer, hosted on ArcGIS (public, keyless).
The exact service name has drifted; override with the PORTWATCH_URL env var if the
default 404s. Schema is handled defensively in transform.parse_features().
"""
import json
import os
import sys
import datetime
import urllib.request
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import transform  # noqa: E402

DEFAULT_URL = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
               "Daily_Chokepoints_Data/FeatureServer/0/query")
ARCGIS_URL = os.environ.get("PORTWATCH_URL", DEFAULT_URL)
UA = {"User-Agent": "mandala-maritime-ci/1.0 (+https://github.com/richyBaxter/Mandala)"}


def fetch_recent(url, count=800):
    """Fetch the most recent records across all chokepoints (newest first)."""
    qs = urllib.parse.urlencode({
        "where": "1=1",
        "outFields": "*",
        "orderByFields": "date DESC",
        "resultRecordCount": count,
        "returnGeometry": "false",
        "f": "json",
    })
    try:
        req = urllib.request.Request(url + "?" + qs, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except Exception as e:
        print("PortWatch fetch failed:", e)
        return None


def main():
    with open(os.path.join(HERE, "chokepoints_meta.json")) as f:
        meta = json.load(f)

    raw = fetch_recent(ARCGIS_URL)
    records = transform.parse_features(raw) if raw else []

    if not records:
        print("no chokepoint records parsed; keeping existing JSON unchanged")
        return 0

    out = transform.build(records, meta, source="imf-portwatch",
                          now=datetime.datetime.now(datetime.timezone.utc))
    path = os.path.join(HERE, "chokepoint_deviations.json")
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    s = out["summary"]
    print(f"wrote {path}: {s['tracked']} chokepoints, {s['constrained_count']} constrained, "
          f"~{s['transits_below_baseline_per_day']} transits/day below baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
