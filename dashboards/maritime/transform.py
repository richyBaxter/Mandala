#!/usr/bin/env python3
"""Pure transforms for the Maritime Chokepoints dashboard.

Kept free of any network I/O so it can be unit-tested deterministically against
fixtures. `fetch.py` does the live ArcGIS call and hands the raw response here.

Pipeline:
    parse_features(arcgis_json)  -> normalised records  [{name, date, transit, trade}]
    build(records, meta, ...)    -> the compact dashboard JSON (chokepoint_deviations.json)
"""
import re
import datetime

# PortWatch's column names have drifted over time, so match defensively. The live
# chokepoints layer carries the transit count in `n_total`; older/other layers used
# n_transit_calls / portcalls. If none is present we sum the per-vessel-type counts.
TRANSIT_KEYS = ("n_total", "n_transit_calls", "portcalls", "transit_calls", "n_transit", "vessel_count", "vessels")
TYPE_KEYS = ("n_container", "n_dry_bulk", "n_general_cargo", "n_roro", "n_tanker")
IMPORT_KEYS = ("import", "import_musd", "imports")
EXPORT_KEYS = ("export", "export_musd", "exports")
TRADE_KEYS = ("trade", "trade_musd", "total_trade", "capacity", "capacity_total")
NAME_KEYS = ("portname", "PORTNAME", "chokepoint", "name", "portid")
DATE_KEYS = ("date", "Date", "DATE", "day")

# deviation thresholds (percent vs 2024 baseline)
CONSTRAINED = -15
ELEVATED = 15


def _norm(s):
    """Lowercase, strip punctuation, collapse whitespace, for fuzzy name matching."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(s).lower())).strip()


def _first(attrs, keys):
    for k in keys:
        if k in attrs and attrs[k] not in (None, ""):
            return attrs[k]
    return None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_features(arcgis_json):
    """Extract normalised records from an ArcGIS FeatureServer query response.

    Tolerates the GeoServices shape {"features": [{"attributes": {...}}, ...]}.
    Returns [] for anything malformed (never raises).
    """
    out = []
    try:
        feats = arcgis_json.get("features", []) if isinstance(arcgis_json, dict) else []
    except Exception:
        return out
    for f in feats:
        attrs = f.get("attributes") if isinstance(f, dict) else None
        if not isinstance(attrs, dict):
            continue
        name = _first(attrs, NAME_KEYS)
        if name is None:
            continue
        transit = _num(_first(attrs, TRANSIT_KEYS))
        if transit is None:                       # fall back to summing vessel-type counts
            parts = [_num(attrs.get(k)) for k in TYPE_KEYS if attrs.get(k) is not None]
            parts = [p for p in parts if p is not None]
            if parts:
                transit = sum(parts)
        imp = _num(_first(attrs, IMPORT_KEYS))
        exp = _num(_first(attrs, EXPORT_KEYS))
        trade = _num(_first(attrs, TRADE_KEYS))
        if trade is None and (imp is not None or exp is not None):
            trade = (imp or 0.0) + (exp or 0.0)
        out.append({"name": name, "date": _first(attrs, DATE_KEYS),
                    "transit": transit, "trade": trade})
    return out


def _match_slug(name, meta):
    """Map a record's name to a chokepoint slug via the meta aliases."""
    n = _norm(name)
    for slug, m in meta.items():
        if n == _norm(m["name"]) or n in (_norm(a) for a in m.get("names", [])):
            return slug
        # substring fallback: "suez canal transit" -> suez
        if any(_norm(a) in n for a in m.get("names", [])):
            return slug
    return None


def _status(dev):
    if dev is None:
        return "no-data"
    if dev <= CONSTRAINED:
        return "constrained"
    if dev >= ELEVATED:
        return "elevated"
    return "normal"


def build(records, meta_doc, source="imf-portwatch", now=None, window=7):
    """Aggregate records into the dashboard JSON.

    For each chokepoint: the mean transit calls over its most recent `window`
    dated records, the percent deviation versus its 2024 baseline, a status, and
    the mean trade volume if present. Plus a summary with the aggregate daily
    transit shortfall (a proxy for diverted traffic).
    """
    meta = meta_doc["chokepoints"]
    now = now or datetime.datetime.now(datetime.timezone.utc)

    # bucket records by chokepoint slug
    buckets = {slug: [] for slug in meta}
    for r in records:
        slug = _match_slug(r.get("name"), meta)
        if slug:
            buckets[slug].append(r)

    rows = []
    shortfall = 0.0
    for slug, m in meta.items():
        recs = [r for r in buckets[slug] if r.get("transit") is not None]
        recs.sort(key=lambda r: (r.get("date") is None, r.get("date")), reverse=True)
        recent = recs[:window]
        baseline = _num(m.get("baseline"))

        if recent:
            avg = round(sum(r["transit"] for r in recent) / len(recent), 1)
            trades = [r["trade"] for r in recent if r.get("trade") is not None]
            trade_avg = round(sum(trades) / len(trades), 1) if trades else None
        else:
            avg = trade_avg = None

        dev = None
        if avg is not None and baseline:
            dev = round((avg - baseline) / baseline * 100)
            shortfall += max(0.0, baseline - avg)

        rows.append({
            "id": slug, "name": m["name"], "lat": m["lat"], "lon": m["lon"],
            "transit_7d_avg": avg, "baseline": baseline,
            "deviation_pct": dev, "status": _status(dev),
            "trade_musd_7d_avg": trade_avg,
        })

    # most constrained first; no-data sinks to the bottom
    rows.sort(key=lambda r: (r["deviation_pct"] is None, r["deviation_pct"] if r["deviation_pct"] is not None else 0))
    constrained = [r for r in rows if r["status"] == "constrained"]

    return {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "baseline_year": meta_doc.get("baseline_year", 2024),
        "chokepoints": rows,
        "summary": {
            "tracked": len(rows),
            "constrained_count": len(constrained),
            "transits_below_baseline_per_day": round(shortfall),
            "most_constrained": constrained[0]["id"] if constrained else None,
        },
    }
