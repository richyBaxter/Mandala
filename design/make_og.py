#!/usr/bin/env python3
"""Generate the Open Graph share image for The Bitcoin Spiral.

Writes design/og-image.svg (1200x630). Render to og.png (repo root) with any
SVG rasteriser, e.g.:  python3 -c "import cairosvg; cairosvg.svg2png(url='design/og-image.svg', write_to='og.png', output_width=1200, output_height=630)"

Brand values mirror design/tokens.json. Stdlib only.
"""
import math, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, "tokens.json")))["color"]
FONT = "Inter, 'Segoe UI', system-ui, -apple-system, Helvetica, Arial, sans-serif"
W, H = 1200, 630
CX, CY = 900, 315          # spiral centre (right third)

def spiral(r0, k, turns=3.0, start=-0.4, n=260):
    pts = []
    for i in range(n + 1):
        th = turns * 2 * math.pi * (i / n)
        r = r0 * math.exp(k * th)
        pts.append((CX + r * math.cos(th + start), CY - r * math.sin(th + start)))
    return "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

s = []
s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">')
s.append('<defs>'
         f'<radialGradient id="bg" cx="72%" cy="50%" r="62%">'
         f'<stop offset="0%" stop-color="{T["glow"]}"/><stop offset="100%" stop-color="{T["bg"]}"/></radialGradient>'
         f'<linearGradient id="price" x1="0" y1="1" x2="1" y2="0">'
         f'<stop offset="0%" stop-color="{T["buy"]}"/><stop offset="55%" stop-color="{T["fair"]}"/>'
         f'<stop offset="100%" stop-color="{T["sell"]}"/></linearGradient>'
         '<filter id="glow" x="-40%" y="-40%" width="180%" height="180%">'
         '<feGaussianBlur stdDeviation="3" result="b"/><feMerge>'
         '<feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>')

# background
s.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')

# faint rings + spokes around the spiral
for rr in (60, 120, 185, 250):
    s.append(f'<circle cx="{CX}" cy="{CY}" r="{rr}" fill="none" stroke="{T["ring"]}" stroke-width="1" stroke-dasharray="1,6"/>')
for k in range(8):
    a = k * math.pi / 4
    s.append(f'<line x1="{CX}" y1="{CY}" x2="{CX+265*math.cos(a):.1f}" y2="{CY-265*math.sin(a):.1f}" stroke="{T["grid"]}" stroke-width="1"/>')

# channel spirals + price spiral (glowing)
s.append('<g filter="url(#glow)">')
s.append(f'<path d="{spiral(3.2, 0.214)}" fill="none" stroke="{T["accent"]}" stroke-width="2" opacity="0.85"/>')
s.append(f'<path d="{spiral(5.6, 0.214)}" fill="none" stroke="{T["sell"]}" stroke-width="2" opacity="0.7"/>')
s.append(f'<path d="{spiral(4.2, 0.214)}" fill="none" stroke="url(#price)" stroke-width="3.4"/>')
s.append('</g>')
s.append(f'<path d="{spiral(4.9, 0.214)}" fill="none" stroke="{T["ink"]}" stroke-width="1.2" stroke-dasharray="6,5" opacity="0.4"/>')
# "now" dot at outer end of price spiral
th = 3.0 * 2 * math.pi; r = 4.2 * math.exp(0.214 * th)
nx, ny = CX + r * math.cos(th - 0.4), CY - r * math.sin(th - 0.4)
s.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="8" fill="{T["buy"]}" stroke="{T["ink"]}" stroke-width="2" filter="url(#glow)"/>')

# left: brand + title block
s.append(f'<text x="80" y="150" font-size="22" font-weight="800" letter-spacing="5" fill="{T["accent"]}">HOUTINI</text>')
s.append(f'<text x="78" y="248" font-size="78" font-weight="800" letter-spacing="-1.5" fill="{T["ink"]}">The Bitcoin</text>')
s.append(f'<text x="78" y="330" font-size="78" font-weight="800" letter-spacing="-1.5" fill="{T["ink"]}">Spiral</text>')
s.append(f'<text x="80" y="392" font-size="26" fill="{T["muted"]}">Price &amp; the Power Law on a 4-year cycle map</text>')
# feature pills
pills = [("Power-Law oscillator", T["buy"]), ("Mayer · Pi Cycle", T["sky"]), ("ETF flows &amp; sentiment", T["accent"])]
px = 80
for label, col in pills:
    wpx = 22 + len(label.replace("&amp;", "&")) * 11
    s.append(f'<rect x="{px}" y="430" width="{wpx}" height="38" rx="19" fill="{T["panel"]}" stroke="{col}" stroke-opacity="0.5"/>')
    s.append(f'<text x="{px + wpx/2:.0f}" y="455" font-size="17" font-weight="600" fill="{col}" text-anchor="middle">{label}</text>')
    px += wpx + 14
# url
s.append(f'<text x="80" y="545" font-size="20" font-weight="600" fill="{T["faint"]}">richybaxter.github.io/Mandala</text>')

s.append('</svg>')

out = os.path.join(HERE, "og-image.svg")
open(out, "w").write("\n".join(s))
print("wrote", out)
