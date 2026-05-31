#!/usr/bin/env python3
"""Generate THE BITCOIN SPIRAL as a standalone SVG (by houtini).

Bitcoin price and the Power Law plotted on a 4-year-cycle polar map.
The Power-Law model is the work of G. Santostasi.

    angle  = position within the 4-year cycle
             (Jan 1 of 2013/2017/2021/2025 -> 0deg / east, counter-clockwise)
    radius = K * log10(price)            ($1 at the centre)

Power Law channel (Santostasi-style):  log10(P) = a + n*log10(d)
    d = days since the genesis block (2009-01-03), n = 5.8
    support    a = -17.2   (orange, lower bound / cycle bottoms)
    resistance a = -16.5   (red,    upper bound / cycle tops)

Overlays:
  - Buy/sell zones  : BTC line coloured green->red by its position in the channel
                      (Power-Law oscillator).
  - Events diary    : markers from data/events.csv (halvings, ETFs, macro).
  - Institutional   : spot-ETF net-flow ticks from data/flows.csv (who's buying).

Usage:  python3 generate.py [output.svg]
Data:   data/btc-monthly.json, data/events.csv, data/flows.csv
"""
import math, json, csv, datetime, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
GENESIS = datetime.date(2009, 1, 3)

# ---------- load data ----------
with open(os.path.join(HERE, "data", "btc-monthly.json")) as f:
    DATA = json.load(f)
MONTHLY = {int(y): v for y, v in DATA["months"].items()}
LAST_UPDATED = DATA.get("_last_updated", "")

def load_csv(name):
    path = os.path.join(HERE, "data", name)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        rows = [r for r in csv.reader(f) if r and not r[0].lstrip().startswith("#")]
    if not rows:
        return []
    head = [c.strip() for c in rows[0]]
    return [dict(zip(head, [c.strip() for c in r])) for r in rows[1:] if len(r) >= len(head)]

EVENTS = load_csv("events.csv")
FLOWS = load_csv("flows.csv")

# ---------- mapping constants ----------
K = 80.0                 # px per decade of price
P0 = 1.0                 # price at radius 0 (notional)
INNER = 56.0             # empty hub radius — opens the crowded centre
CX, CY = 620.0, 630.0
N = 5.8                  # power-law exponent
A_SUP, A_RES = -17.32, -16.5   # support/floor and resistance/cycle-top intercepts
A_FAIR = -17.01                # central fair-value line (canonical Santostasi)
W = H = 1240

# ---------- analytics theme (dark crypto-dashboard) ----------
FONT = "Inter, 'Segoe UI', system-ui, -apple-system, Helvetica, Arial, sans-serif"
T = {
    "bg":      "#0b0e14",  # page background
    "glow":    "#10202e",  # centre radial glow
    "panel":   "#0f141d",  # card fill
    "border":  "#1e2733",  # card / panel border
    "grid":    "#1b2330",  # cycle spokes
    "ring":    "#212b3a",  # price rings
    "ink":     "#e8ecf3",  # primary text
    "muted":   "#8a93a3",  # secondary text
    "faint":   "#525b6b",  # tertiary text
    "btc":     "#f7931a",  # bitcoin orange (accent)
    "support": "#f7931a",  # support spiral
    "resist":  "#ef4351",  # resistance spiral
    "buy":     "#16c784",  # green  (cheap / inflow)
    "fair":    "#f0a92b",  # amber
    "sell":    "#ea3943",  # red    (expensive / outflow)
    "halving": "#a78bfa",  # violet
    "etf":     "#38bdf8",  # sky
    "macro":   "#94a3b8",  # slate
}

# ---------- helpers ----------
def ymid(year, m):
    return datetime.date(year, m, 15)

def days(d):
    return (d - GENESIS).days

def dec_year(d):
    s = datetime.date(d.year, 1, 1)
    e = datetime.date(d.year + 1, 1, 1)
    return d.year + (d - s).days / (e - s).days

def radius(price):
    if price <= 0:
        return INNER
    return INNER + max(2.0, K * (math.log10(price) - math.log10(P0)))

def angle(d):            # CCW radians; Jan 1 2013/17/21/25 -> 0
    phase = ((dec_year(d) - 2013.0) % 4.0) / 4.0
    return 2 * math.pi * phase

def xy(price, d):
    a, r = angle(d), radius(price)
    return CX + r * math.cos(a), CY - r * math.sin(a)

def pl(d, a_coef):
    dd = days(d)
    return 0.0 if dd <= 0 else 10 ** (a_coef + N * math.log10(dd))

def pl_xy(d, a_coef, log_offset=0.0):
    p = pl(d, a_coef)
    a = angle(d)
    r = INNER + max(2.0, K * (math.log10(p) - math.log10(P0)) + K * log_offset)
    return CX + r * math.cos(a), CY - r * math.sin(a)

# ---------- position in the Power-Law channel (0 = floor, 1 = cycle-top) ----------
def oscillator(d, price):
    if price <= 0:
        return 0.0
    lo, hi = math.log10(pl(d, A_SUP)), math.log10(pl(d, A_RES))
    t = (math.log10(price) - lo) / (hi - lo)
    return max(0.0, min(1.0, t))

# ---------- power-law sampling ----------
PL_START = datetime.date(2011, 7, 1)
LAST_YEAR = max(MONTHLY)
PL_END = ymid(LAST_YEAR, len(MONTHLY[LAST_YEAR]))

def date_steps(start, end, step):
    out, cur = [], start
    while cur <= end:
        out.append(cur)
        cur += datetime.timedelta(days=step)
    return out

PL_DATES = date_steps(PL_START, PL_END, 8)

def ribbon(a_coef, half):
    outer = [pl_xy(d, a_coef, +half) for d in PL_DATES]
    inner = [pl_xy(d, a_coef, -half) for d in reversed(PL_DATES)]
    pts = outer + inner
    return "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"

def spiral(a_coef):
    pts = [pl_xy(d, a_coef) for d in PL_DATES]
    return "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

# ---------- BTC monthly spiral ----------
btc_pts = []
for year in sorted(MONTHLY):
    for i, price in enumerate(MONTHLY[year]):
        if price >= 1:               # sub-$1 months collapse to centre; skip the noise
            btc_pts.append((ymid(year, i + 1), price))
cur_d, cur_p = btc_pts[-1]
cur_x, cur_y = xy(cur_p, cur_d)
cur_t = oscillator(cur_d, cur_p)

# ---------- build SVG ----------
s = []
s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{FONT}">')
s.append('<defs>'
         f'<radialGradient id="bgglow" cx="50%" cy="50%" r="60%">'
         f'<stop offset="0%" stop-color="{T["glow"]}"/>'
         f'<stop offset="100%" stop-color="{T["bg"]}"/></radialGradient>'
         '<filter id="glow" x="-30%" y="-30%" width="160%" height="160%">'
         '<feGaussianBlur stdDeviation="2.4" result="b"/>'
         '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
         '</filter></defs>')

# background
s.append(f'<rect width="{W}" height="{H}" fill="{T["bg"]}"/>')
s.append(f'<circle cx="{CX}" cy="{CY}" r="540" fill="url(#bgglow)"/>')

# header
s.append(f'<a href="https://houtini.com" target="_blank"><text x="64" y="62" font-size="13" '
         f'font-weight="700" letter-spacing="3" fill="{T["btc"]}">HOUTINI</text></a>')
s.append(f'<text x="64" y="98" font-size="30" font-weight="800" letter-spacing="0.5" '
         f'fill="{T["ink"]}">The Bitcoin Spiral</text>')
s.append(f'<text x="64" y="124" font-size="14" fill="{T["muted"]}">'
         f'Where Bitcoin sits in its 4-year cycle &#183; fourteen years spiralling around the Power-Law curve</text>')

# spokes
for k in range(8):
    a = k * math.pi / 4
    s.append(f'<line x1="{CX+INNER*math.cos(a):.1f}" y1="{CY-INNER*math.sin(a):.1f}" '
             f'x2="{CX+478*math.cos(a):.1f}" y2="{CY-478*math.sin(a):.1f}" '
             f'stroke="{T["grid"]}" stroke-width="1"/>')

# price rings + radial price ticks
for price in (10, 100, 1000, 10000, 100000):
    s.append(f'<circle cx="{CX}" cy="{CY}" r="{radius(price):.1f}" fill="none" '
             f'stroke="{T["ring"]}" stroke-width="1" stroke-dasharray="1,5"/>')

# Power-Law channel — monochrome orange family (floor solid, top lighter dashed,
# fair value dotted). The white price line is the hero.
s.append(f'<path d="{spiral(A_SUP)}" fill="none" stroke="{T["btc"]}" stroke-width="1.6" opacity="0.7"/>')
s.append(f'<path d="{spiral(A_RES)}" fill="none" stroke="#f6b15a" stroke-width="1.4" '
         f'stroke-dasharray="7,5" opacity="0.6"/>')
s.append(f'<path d="{spiral(A_FAIR)}" fill="none" stroke="{T["ink"]}" stroke-width="1.2" '
         f'stroke-dasharray="2,5" opacity="0.4"/>')
_fvx, _fvy = pl_xy(ymid(LAST_YEAR, 7), A_FAIR)
s.append(f'<text x="{_fvx:.1f}" y="{_fvy:.1f}" font-size="10.5" fill="{T["muted"]}" '
         f'text-anchor="middle" opacity="0.8">fair value</text>')

# BTC price line — single colour for legibility (valuation is shown by the
# channel position and the buy/sell gauge, not by colouring the line itself)
btc_path = "M " + " L ".join(f"{xy(p, d)[0]:.1f},{xy(p, d)[1]:.1f}" for d, p in btc_pts)
s.append(f'<path d="{btc_path}" fill="none" stroke="{T["ink"]}" stroke-width="2.8" '
         f'stroke-linejoin="round" stroke-linecap="round" filter="url(#glow)"/>')

# price labels (one set, upper-left diagonal)
def plabel(price, txt, ang_deg):
    a, r = math.radians(ang_deg), radius(price)
    s.append(f'<text x="{CX+r*math.cos(a):.1f}" y="{CY-r*math.sin(a):.1f}" font-size="11" '
             f'fill="{T["faint"]}" text-anchor="middle">{txt}</text>')

for price, t in ((10, "$10"), (100, "$100"), (1000, "$1K"),
                 (10000, "$10K"), (100000, "$100K")):
    plabel(price, t, 128)

# year labels on a single radial spoke (north) — a clean radial axis instead
# of labels overlapping the spiral lines.
def year_label(year):
    p = pl(ymid(year, 1), A_SUP)
    r = INNER + max(2.0, K * (math.log10(p) - math.log10(P0)))
    x, y = CX, CY - r
    s.append(f'<rect x="{x-15:.1f}" y="{y-7:.1f}" width="30" height="14" rx="3" '
             f'fill="{T["bg"]}" opacity="0.88"/>')
    s.append(f'<text x="{x:.1f}" y="{y+4:.1f}" font-size="11" font-weight="600" '
             f'fill="{T["muted"]}" text-anchor="middle">{year}</text>')

for _y in range(2012, LAST_YEAR + 1):
    year_label(_y)

# ---------- events diary (single neutral colour) ----------
col = T["muted"]
for ev in EVENTS:
    try:
        y, m, day = (int(x) for x in ev["date"].split("-"))
        ed = datetime.date(y, m, day)
    except (KeyError, ValueError):
        continue
    price = None
    if y in MONTHLY and m <= len(MONTHLY[y]):
        price = MONTHLY[y][m - 1]
    if not price:
        price = pl(ed, A_SUP)
    a, r0 = angle(ed), radius(price)
    x0, y0 = CX + r0 * math.cos(a), CY - r0 * math.sin(a)
    r1 = r0 + 38
    x1, y1 = CX + r1 * math.cos(a), CY - r1 * math.sin(a)
    anchor = "start" if x1 >= CX else "end"
    s.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
             f'stroke="{col}" stroke-width="1" opacity="0.55"/>')
    s.append(f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="3" fill="{col}" '
             f'stroke="{T["bg"]}" stroke-width="1"/>')
    s.append(f'<text x="{x1 + (4 if anchor=="start" else -4):.1f}" y="{y1+3:.1f}" font-size="10.5" '
             f'fill="{col}" font-weight="600" text-anchor="{anchor}">{ev.get("label","")}</text>')

# interactive hover points: historic price + the model levels at each month
# (invisible targets; the dashboard inlines the SVG and shows a tooltip)
s.append('<g class="pts">')
for d, p in btc_pts:
    hx, hy = xy(p, d)
    fv, flv, tpv = pl(d, A_FAIR), pl(d, A_SUP), pl(d, A_RES)
    osc = oscillator(d, p)
    lbl = d.strftime("%b %Y")
    s.append(
        f'<circle class="pt" cx="{hx:.1f}" cy="{hy:.1f}" r="9" fill="none" pointer-events="all" '
        f'data-d="{lbl}" data-price="{p:.0f}" data-fair="{fv:.0f}" data-floor="{flv:.0f}" '
        f'data-top="{tpv:.0f}" data-osc="{osc*100:.0f}" style="cursor:pointer">'
        f'<title>{lbl}\nPrice ${p:,.0f}\nFair ${fv:,.0f} · Floor ${flv:,.0f} · Top ${tpv:,.0f}</title>'
        f'</circle>')
s.append('</g>')

# captions + you-are-here badge
s.append(f'<text x="990" y="300" font-size="12" font-weight="700" letter-spacing="1.5" '
         f'fill="{T["muted"]}" opacity="0.85">CYCLE TOPS</text>')
s.append(f'<text x="92" y="520" font-size="12" font-weight="700" letter-spacing="1.5" '
         f'fill="{T["muted"]}" opacity="0.85">CYCLE BOTTOMS</text>')
s.append(f'<circle cx="{cur_x:.1f}" cy="{cur_y:.1f}" r="6" fill="{T["btc"]}" '
         f'stroke="{T["ink"]}" stroke-width="1.4" filter="url(#glow)"/>')
hx, hy = cur_x + 120, cur_y + 64
s.append(f'<line x1="{cur_x+6:.1f}" y1="{cur_y+4:.1f}" x2="{hx+8:.1f}" y2="{hy-9:.1f}" '
         f'stroke="{T["muted"]}" stroke-width="1"/>')
badge = f'NOW  ~${cur_p:,.0f}  &#183;  {cur_d.strftime("%b %Y")}'
s.append(f'<rect x="{hx:.1f}" y="{hy-15:.1f}" width="196" height="26" rx="13" '
         f'fill="{T["panel"]}" stroke="{T["btc"]}" stroke-width="1.2"/>')
s.append(f'<circle cx="{hx+15:.1f}" cy="{hy-2:.1f}" r="4" fill="{T["btc"]}"/>')
s.append(f'<text x="{hx+27:.1f}" y="{hy+2:.1f}" font-size="12.5" font-weight="700" '
         f'fill="{T["ink"]}">{badge}</text>')

# ---------- compact key (bottom-right) ----------
lx, ly = 902, H - 196
s.append(f'<rect x="{lx-18}" y="{ly-26}" width="280" height="150" rx="12" '
         f'fill="{T["panel"]}" stroke="{T["border"]}"/>')
s.append(f'<text x="{lx}" y="{ly-4}" font-size="12" font-weight="700" letter-spacing="1.5" '
         f'fill="{T["ink"]}">KEY</text>')
ky = ly + 18
s.append(f'<line x1="{lx}" y1="{ky}" x2="{lx+40}" y2="{ky}" stroke="{T["ink"]}" stroke-width="2.8"/>')
s.append(f'<text x="{lx+50}" y="{ky+4}" font-size="10.5" fill="{T["muted"]}">BTC price</text>')
ky += 24
s.append(f'<line x1="{lx}" y1="{ky}" x2="{lx+40}" y2="{ky}" stroke="{T["btc"]}" stroke-width="1.8" opacity="0.7"/>')
s.append(f'<text x="{lx+50}" y="{ky+4}" font-size="10.5" fill="{T["muted"]}">Power-Law floor</text>')
ky += 24
s.append(f'<line x1="{lx}" y1="{ky}" x2="{lx+40}" y2="{ky}" stroke="#f6b15a" stroke-width="1.6" stroke-dasharray="7,5"/>')
s.append(f'<text x="{lx+50}" y="{ky+4}" font-size="10.5" fill="{T["muted"]}">Cycle-top band</text>')
ky += 24
s.append(f'<line x1="{lx}" y1="{ky}" x2="{lx+40}" y2="{ky}" stroke="{T["ink"]}" stroke-width="1.4" stroke-dasharray="2,5" opacity="0.6"/>')
s.append(f'<text x="{lx+50}" y="{ky+4}" font-size="10.5" fill="{T["muted"]}">Fair value &#183; &#9679; events</text>')
s.append(f'<circle cx="{lx+150}" cy="{ky}" r="3" fill="{T["muted"]}"/>')

# footer
s.append(f'<a href="https://houtini.com" target="_blank"><text x="64" y="{H-52}" '
         f'font-size="14" font-weight="800" fill="{T["btc"]}">houtini</text></a>')
s.append(f'<text x="124" y="{H-52}" font-size="11" fill="{T["muted"]}">'
         f'&#183; data through {LAST_UPDATED} &#183; ATH $126,198 (6 Oct 2025)</text>')
s.append(f'<text x="64" y="{H-34}" font-size="10" fill="{T["faint"]}">'
         f'Power Law model after G. Santostasi &#183; angle = position in the 4-year calendar cycle (not time-since-halving)</text>')
s.append('</svg>')

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "btc-mandala.svg")
with open(out, "w") as f:
    f.write("\n".join(s))
print(f"wrote {out}  (current: {cur_d} ${cur_p:,.0f})")
