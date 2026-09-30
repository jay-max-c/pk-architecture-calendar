#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = json.loads((ROOT / "baseline_schedule.json").read_text(encoding="utf-8"))
OVR = json.loads((ROOT / "overrides.json").read_text(encoding="utf-8")) if (ROOT / "overrides.json").exists() else {"events":[]}

events = {e["key"]: dict(e) for e in BASE["events"]}
for p in OVR.get("events", []):
    k = p.get("key")
    if k in events:
        events[k].update({a:b for a,b in p.items() if a != "key"})

print("Baseline/override layer ready. Use PK_Y1S1_2026.ics as the subscription feed.")
