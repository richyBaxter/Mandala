#!/usr/bin/env python3
"""CI step: fetch credible RSS feeds server-side and write news.json.

Replaces the flaky client-side rss2json bridge. Filters for flow/institutional
relevance and tags known entities. Never raises; writes whatever it can.
"""
import json, os, datetime, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Bitcoin Magazine", "https://bitcoinmagazine.com/feed"),
]
KW = ["etf", "inflow", "outflow", "flows", "blackrock", "ibit", "fidelity", "fbtc",
      "grayscale", "gbtc", "ark ", "microstrategy", "strategy", "metaplanet", "saylor",
      "accumulat", "whale", "institution", "treasury", "sovereign", "buys", "bought",
      "sells", "sold", "billion", "holdings", "reserve", "allocation"]

def text(el, tag):
    child = el.find(tag)
    return (child.text or "").strip() if child is not None and child.text else ""

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mandala-ci/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

items = []
for src, url in FEEDS:
    try:
        root = ET.fromstring(fetch(url))
        for it in root.iter("item"):
            title, link, desc = text(it, "title"), text(it, "link"), text(it, "description")
            pub = text(it, "pubDate")
            ts = 0.0
            try:
                ts = parsedate_to_datetime(pub).timestamp() if pub else 0.0
            except Exception:
                ts = 0.0
            if title:
                items.append({"src": src, "title": title, "link": link, "desc": desc, "ts": ts})
    except Exception as e:
        print("feed failed:", src, e)

def match(it):
    t = (it["title"] + " " + it["desc"]).lower()
    return any(k.strip() in t for k in KW)

flt = [i for i in items if match(i)]
use = flt if len(flt) >= 4 else items
use.sort(key=lambda i: i["ts"], reverse=True)
use = use[:12]

out = {
    "items": [{"src": i["src"], "title": i["title"], "link": i["link"],
               "date": (datetime.datetime.utcfromtimestamp(i["ts"]).isoformat() + "Z") if i["ts"] else None}
              for i in use],
    "filtered": len(flt) >= 4,
    "generated": datetime.datetime.utcnow().isoformat() + "Z",
}
with open(os.path.join(os.getcwd(), "news.json"), "w") as f:
    json.dump(out, f)
print(f"wrote news.json: {len(out['items'])} items (filtered={out['filtered']})")
