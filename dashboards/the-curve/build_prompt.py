#!/usr/bin/env python3
"""Assemble the AI-narrative prompt for The Curve. Writes prompt.txt (gitignored)."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "data", "curve.json")))
s = d["spread_2s10s"]["series"]
trough = min(p["v"] for p in s)

facts = f"""DATA (use only these numbers; never invent figures):
- 10-year Treasury yield: {d['ten_year']}% ({d['current_label']}).
- 10Y-2Y spread (2s10s): {d['spread_2s10s_current']} pts now; deepest inversion in the series {trough} pts; it spent 2022-2024 inverted and has since re-steepened above zero.
- NY Fed recession probability: {round(d['recession_prob']*100)}%.
- A yield curve plots Treasury yields from 1 month to 30 years; an upward slope is normal, an inverted (downward) slope has preceded every modern US recession, typically by 6-18 months. The curve often un-inverts shortly before the recession actually arrives."""

instructions = """
TASK: Return a SINGLE JSON object and nothing else (no markdown), with exactly these keys:
"shape", "signal", "now".
- "shape": 3-4 sentences. Define the yield curve and what its slope means; describe today's shape
  versus the 2023 inversion using the numbers above.
- "signal": 3-4 sentences. Explain the 2s10s spread as the recession tell, the inversion-then-re-steepening,
  and the NY Fed probability; note the un-inversion caveat.
- "now": 2-3 sentences. A measured synthesis of what the curve is signalling, without predicting timing.
Use only the numbers provided. Define jargon in passing. Neutral and measured; no price targets, no advice.
"""
out = facts + "\n" + instructions
open(os.path.join(HERE, "prompt.txt"), "w").write(out)
print("wrote prompt.txt (%d chars)" % len(out))
