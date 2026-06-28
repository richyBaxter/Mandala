#!/usr/bin/env python3
"""Assemble the AI-narrative prompt from the live numbers.

Writes dashboards/music-stops/prompt.txt (gitignored). The CI step feeds it to
GitHub Models and asks for one JSON object of six short notes; write_narrative.py
merges the result into narrative.json (falling back to the committed text).
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


cape = load("cape.json")
buf = load("buffett.json")
conc = load("concentration.json")
yc = load("yieldcurve.json")
dry = load("drypowder.json")
tl = load("timeline.json")

facts = f"""DATA (use only these numbers; never invent figures):
- Shiller CAPE: {cape['current']['value']} ({cape['current']['label']}); 140-year average {cape['average']}; only-ever-higher Dec 1999 at {cape['peak_1999']['value']}.
- Buffett Indicator (market cap / GDP): {buf['current']['value']}% ({buf['current']['label']}); dot-com peak {buf['peak_dotcom']['value']}%; 2007 peak {buf['peak_2007']['value']}%.
- Concentration: top 5 names ~{conc['top5_total']}% of the S&P 500; tech-sector weight {conc['tech_sector_weight']}%; top-10 weight {conc['top10_history'][-1]['v']}% (2026) vs {conc['top10_history'][0]['v']}% (2015).
- Yield curve (10Y-3M spread): {yc['current']['value']} pts ({yc['current']['label']}); NY Fed recession probability {round(yc['recession_prob']*100)}%.
- Dry powder: Berkshire cash {dry['berkshire_current']['value']}B ({dry['berkshire_current']['label']}); {dry['survey_expect_decline']}% of institutions expect a decline.
- Trigger window: {tl['danger_window']['label']} — IPO lock-up expirations (SpaceX, OpenAI, Anthropic)."""

instructions = """
TASK: Return a SINGLE JSON object and nothing else (no markdown, no prose around it),
with exactly these keys: "cape", "buffett", "concentration", "yieldcurve", "drypowder", "finale".
Each value is 1-2 punchy sentences for a smart non-expert, framing the number in the context of a
possible market bubble. Use only the numbers above. Explain jargon in passing. No price targets,
no financial advice, no invented figures. "finale" ties the trigger window to draining liquidity.
"""

out = facts + "\n" + instructions
with open(os.path.join(HERE, "prompt.txt"), "w") as f:
    f.write(out)
print("wrote prompt.txt (%d chars)" % len(out))
