#!/usr/bin/env python3
"""CI step: scrape daily Spot-BTC-ETF net flows from Farside Investors.

Farside publishes a free HTML table of daily totals across all US spot Bitcoin
ETFs. Output: etf_flows.json with the last ~90 days of net flows (USD millions).

Best-effort: never raises. If the page layout changes or the request fails, the
script just doesn't write the file — the dashboard then hides the ETF chart.
"""
import json, os, datetime, re, urllib.request
from html.parser import HTMLParser

URL = "https://farside.co.uk/bitcoin-etf-flow-all-data/"
UA = "Mozilla/5.0 (compatible; mandala-ci/1.0; +https://github.com/richyBaxter/Mandala)"

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.cur, self.cell, self.depth = [], None, None, 0
    def handle_starttag(self, tag, attrs):
        if tag == "table": self.depth += 1
        elif self.depth:
            if tag == "tr": self.cur = []
            elif tag in ("td", "th"): self.cell = ""
    def handle_endtag(self, tag):
        if tag == "table" and self.depth: self.depth -= 1
        elif self.depth:
            if tag == "tr" and self.cur is not None:
                self.rows.append(self.cur); self.cur = None
            elif tag in ("td", "th") and self.cell is not None and self.cur is not None:
                self.cur.append(re.sub(r"\s+", " ", self.cell).strip())
                self.cell = None
    def handle_data(self, data):
        if self.cell is not None: self.cell += data

def parse_date(s):
    s = re.sub(r"\s+", " ", s.replace(",", "")).strip()
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%b %d %Y", "%B %d %Y"):
        try: return datetime.datetime.strptime(s, fmt).date()
        except ValueError: continue
    return None

def parse_num(s):
    s = s.replace(",", "").replace("$", "").replace("−", "-").strip()
    # accounting style: (12.3) means -12.3
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    if s in ("", "-", "—", "N/A"):
        return None
    try: return float(s)
    except ValueError: return None

def main():
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept": "text/html"})
        html = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    except Exception as e:
        print("farside fetch failed:", e); return
    p = TableParser(); p.feed(html)
    points = []
    for row in p.rows:
        if len(row) < 3: continue
        d = parse_date(row[0])
        if not d: continue
        # take the last numeric cell as the daily total
        total = None
        for cell in reversed(row):
            v = parse_num(cell)
            if v is not None:
                total = v; break
        if total is None: continue
        points.append({"date": d.isoformat(), "net_flow_musd": round(total, 1)})
    # dedupe + sort + last 90 days
    seen = {}
    for p_ in points: seen[p_["date"]] = p_
    points = sorted(seen.values(), key=lambda x: x["date"])[-90:]
    if not points:
        print("no ETF flow rows parsed; layout may have changed"); return
    out = {"items": points, "source": URL,
           "generated": datetime.datetime.utcnow().isoformat() + "Z"}
    with open(os.path.join(os.getcwd(), "etf_flows.json"), "w") as f:
        json.dump(out, f)
    last = points[-1]
    print(f"wrote etf_flows.json: {len(points)} days, latest {last['date']} = {last['net_flow_musd']} $M")

if __name__ == "__main__":
    main()
