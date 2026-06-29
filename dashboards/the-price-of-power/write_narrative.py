#!/usr/bin/env python3
"""Merge the model response (env RESPONSE) into narrative.json.

The committed narrative.json holds well-written fallbacks; we overwrite a note
only when the model returned non-empty text for that key, so the page always
reads well even if GitHub Models is unavailable.
"""
import json, os, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
NARR = os.path.join(HERE, "narrative.json")
narr = json.load(open(NARR))

resp = os.environ.get("RESPONSE", "").strip()
model = {}
if resp:
    cleaned = re.sub(r"^```(?:json)?|```$", "", resp.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", cleaned, re.S)
    if m:
        try:
            model = json.loads(m.group(0))
        except json.JSONDecodeError:
            model = {}

used = False
for k in list(narr["notes"].keys()):
    v = model.get(k)
    if isinstance(v, str) and v.strip():
        narr["notes"][k] = v.strip(); used = True

narr["source"] = "github-models" if used else "fallback"
narr["generated"] = datetime.datetime.utcnow().isoformat() + "Z"
with open(NARR, "w") as f:
    json.dump(narr, f, indent=2); f.write("\n")
print("narrative.json:", narr["source"])
