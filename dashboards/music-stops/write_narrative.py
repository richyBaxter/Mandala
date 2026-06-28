#!/usr/bin/env python3
"""Merge the model response (env RESPONSE) into narrative.json.

The committed narrative.json already holds well-written fallbacks. We overwrite a
note only when the model returned non-empty text for that key, so the page always
reads well even if GitHub Models is unavailable/rate-limited.
"""
import json, os, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
NARR = os.path.join(HERE, "narrative.json")
KEYS = ["cape", "buffett", "concentration", "yieldcurve", "drypowder", "finale"]

with open(NARR) as f:
    narr = json.load(f)

resp = os.environ.get("RESPONSE", "").strip()
model = {}
if resp:
    # strip ```json fences if present, then find the JSON object
    cleaned = re.sub(r"^```(?:json)?|```$", "", resp.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", cleaned, re.S)
    if m:
        try:
            model = json.loads(m.group(0))
        except json.JSONDecodeError:
            model = {}

used_model = False
for k in KEYS:
    v = model.get(k)
    if isinstance(v, str) and v.strip():
        narr["notes"][k] = v.strip()
        used_model = True

narr["source"] = "github-models" if used_model else "fallback"
narr["generated"] = datetime.datetime.utcnow().isoformat() + "Z"

with open(NARR, "w") as f:
    json.dump(narr, f, indent=2)
    f.write("\n")
print("narrative.json:", narr["source"])
