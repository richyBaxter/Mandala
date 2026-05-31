#!/usr/bin/env python3
"""CI step: turn the model response (env RESPONSE) into commentary.json.

If RESPONSE is empty (GitHub Models unavailable/preview/rate-limited), fall back
to a computed note from tools/_metrics.json so the dashboard always shows
something useful. Writes commentary.json at the repo root (served by Pages).
"""
import json, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
resp = os.environ.get("RESPONSE", "").strip()

metrics = {}
try:
    with open(os.path.join(HERE, "_metrics.json")) as f:
        metrics = json.load(f)
except Exception:
    pass

if resp:
    text, source = resp, "github-models"
elif metrics:
    osc = metrics.get("osc_pct")
    stance = "accumulation" if osc is not None and osc < 34 else \
             "distribution" if osc is not None and osc > 66 else "neutral"
    text = (f"Bitcoin is around ${metrics['price']:,}, about {metrics['vs_fair_pct']}% of its "
            f"Power-Law fair value (${metrics['fair']:,}) and {osc}% up the floor-to-top channel, "
            f"historically {stance} territory.")
    source = "fallback"
else:
    text, source = "Live market data is temporarily unavailable.", "fallback"

out = {"text": text, "generated": datetime.datetime.utcnow().isoformat() + "Z", "source": source}
with open(os.path.join(os.getcwd(), "commentary.json"), "w") as f:
    json.dump(out, f)
print("wrote commentary.json:", source, "-", text[:80])
