#!/usr/bin/env python3
"""Assemble the AI-narrative prompt for The Breakfast Index. Writes prompt.txt (gitignored)."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "data", "breakfast.json")))
movers = ", ".join(f"{m['name']} +{m['pct']}%" for m in d["change_since_base"])

facts = f"""DATA (use only these numbers; never invent figures):
- Breakfast basket (average of coffee, sugar, wheat, orange juice, indexed to {d['base_year']} = 100) is at {d['index_now']}, i.e. about {d['index_now']-100}% above {d['base_year']}.
- Change since {d['base_year']} by item: {movers}.
- These are global commodity prices (FRED/IMF). Soft commodities are thin markets where weather and crop disease (e.g. citrus greening and hurricanes for orange juice; frost/drought in arabica regions for coffee) move world prices sharply."""

instructions = """
TASK: Return a SINGLE JSON object and nothing else (no markdown), with exactly these keys:
"basket", "movers", "why".
- "basket": 3-4 sentences. Explain the indexed basket and the headline rise; note that the climb is recent and uneven.
- "movers": 3-4 sentences. Identify which items did the work using the numbers; explain these are weather/disease stories, not broad inflation; note thin soft-commodity markets.
- "why": 2-3 sentences. A measured takeaway: a few weather-exposed crops drive the headline; inputs can stay elevated for years.
Use only the numbers provided. Define jargon in passing. Neutral and measured; no price targets, no advice.
"""
out = facts + "\n" + instructions
open(os.path.join(HERE, "prompt.txt"), "w").write(out)
print("wrote prompt.txt (%d chars)" % len(out))
