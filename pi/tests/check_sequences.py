"""Run every scenario in scenarios.json against the Pi/Jetson kiosk and the web kiosk.
Usage (from pi/):  python tests/check_sequences.py      (needs ncnn, opencv, pyyaml; node for the web part)"""
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).parent
sc = {s["id"]: s for s in json.loads((HERE / "scenarios.json").read_text())}
runs = {"pi ": [sys.executable, str(HERE / "sim_kiosk.py"), str(HERE / "scenarios.json")],
        "web": ["node", str(HERE / "sim_web.mjs"), str(HERE / "scenarios.json")]}
bad = 0
for label, cmd in runs.items():
    out = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    for k, r in out.items():
        exp = sc[k]["expect"]
        ok = len(r["plays"]) == len(exp) and all(a[0] == b[0] and abs(a[1] - b[1]) <= 0.5 for a, b in zip(r["plays"], exp))
        bad += not ok
        print(label, "PASS" if ok else "FAIL", k, sc[k]["desc"], "| played", r["plays"])
print("all passed" if not bad else f"{bad} failed")
sys.exit(1 if bad else 0)
