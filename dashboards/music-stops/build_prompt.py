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

Each value is 4-5 substantive, technical sentences for a financially-literate reader. For each
indicator: (1) define the metric and how it is constructed; (2) state the current reading with
historical context (where it sits versus its mean, percentile, or prior cycle peaks using only the
numbers above); (3) explain the economic mechanism — why it matters for forward returns or risk;
and (4) give one measured caveat (limitations, structural drivers, or timing uncertainty).
"finale" should explain that valuation sets magnitude while a trigger sets timing, and tie the
window to the liquidity mechanics of IPO lock-up expirations.

Use only the numbers provided — never invent or predict figures. Define jargon in passing. Stay
neutral and measured; no price targets and no financial advice.
"""

out = facts + "\n" + instructions
with open(os.path.join(HERE, "prompt.txt"), "w") as f:
    f.write(out)
print("wrote prompt.txt (%d chars)" % len(out))
