#!/usr/bin/env python3
"""Assemble the AI-narrative prompt for The Price of Power. Writes prompt.txt (gitignored)."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "data", "energy.json")))
f, l, n = d["fossil"], d["lcoe"], d["non_usd"]
solar_fall = round((1 - l["solar_now"] / l["solar_2010"]) * 100)
costs = ", ".join(f"{lbl} ${c}/MWh" for lbl, c in zip(l["labels"], l["now"]))

facts = f"""DATA (use only these numbers; never invent figures):
- WTI crude is about ${f['wti']}/barrel, Brent ${f['brent']}/barrel, Henry Hub natural gas ${f['henry_hub']}/MMBtu, US regular gasoline ${f['gasoline']}/gallon ({d['current_label']}).
- Indexed to 2019 = 100, natural gas was the most volatile of the three fuels, spiking hardest in 2022 before falling back; crude and gasoline moved more in step.
- Levelised cost of new electricity ($/MWh), global benchmark: {costs}. Solar PV and onshore wind now cost less than new coal or gas.
- Solar PV's levelised cost has fallen about {solar_fall}% since 2010 (from roughly ${l['solar_2010']}/MWh to ${l['solar_now']}/MWh).
- Estimated share of global oil trade settled OUTSIDE the US dollar is about {n['current_pct']}% and rising; there is no official figure, so it is an estimate, driven by Russia's pivot to Asian buyers and yuan- and rupee-settled cargoes."""

instructions = """
TASK: Return a SINGLE JSON object and nothing else (no markdown), with exactly these keys:
"fossil", "transition", "currency", "now".
- "fossil": 3-4 sentences on today's oil, gas and pump prices and why natural gas is the volatile one;
  reference the indexed comparison.
- "transition": 3-4 sentences on the levelised cost of electricity, why solar and onshore wind now
  undercut new coal and gas, and what the ~90% fall in solar cost means. Define "levelised cost" in passing.
- "currency": 3-4 sentences on oil's slow drift out of the dollar; stress that the share is an estimate,
  that the dollar still dominates, and name the drivers (Russia, yuan/rupee settlement).
- "now": 2-3 sentences. A measured synthesis tying the three together. No predictions, no price targets.
Use only the numbers provided. Neutral and measured; no advice. Define jargon in passing.
"""
out = facts + "\n" + instructions
open(os.path.join(HERE, "prompt.txt"), "w").write(out)
print("wrote prompt.txt (%d chars)" % len(out))
