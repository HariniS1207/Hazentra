"""Quick data-quality inspection of generated output."""
import json, os

output = r"C:\Users\Valarmathi\Hazentra\simulator\output"

# Show nodes
with open(os.path.join(output, "nodes.json")) as f:
    nodes = json.load(f)
print("=== NODES ===")
for nid, n in nodes.items():
    print("  %s: %s (%s) at (%s, %s)" % (nid, n["name"], n["type"], n["lat"], n["lng"]))

# Peek at flood readings
print("\n=== FLOOD SCENARIO - First 3 flood-node readings ===")
with open(os.path.join(output, "readings", "flood_node_flood.json")) as f:
    readings = json.load(f)
for r in readings[:3]:
    print("  %s  WL=%scm  Rain=%smm/hr  Soil=%s%%  Temp=%sC" % (
        r["timestamp"], r["waterLevel"], r["rainfall"], r["soilMoisture"], r["temp"]))

# Peak danger readings
danger = [r for r in readings if r["waterLevel"] < 80]
print("\n  Danger-level readings (WL<80cm): %d" % len(danger))
if danger:
    worst = min(danger, key=lambda r: r["waterLevel"])
    print("  Lowest water level: %scm at %s" % (worst["waterLevel"], worst["timestamp"]))

# Peek at fire readings
print("\n=== FIRE SCENARIO - Peak smoke readings ===")
with open(os.path.join(output, "readings", "airq_node_fire.json")) as f:
    fire_readings = json.load(f)
peak_smoke = sorted(fire_readings, key=lambda r: r.get("smoke", 0), reverse=True)[:3]
for r in peak_smoke:
    print("  %s  Smoke=%sppm  Gas=%sppm  PM2.5=%sug/m3" % (
        r["timestamp"], r["smoke"], r["gas"], r["pm25"]))

# Sample SACHET payload
print("\n=== SAMPLE SACHET PAYLOAD (from flood alert) ===")
with open(os.path.join(output, "alerts", "alerts_flood.json")) as f:
    alerts = json.load(f)
if alerts:
    p = alerts[0]["sachetPayload"]
    print(json.dumps(p, indent=2))

# Verification sample
print("\n=== SAMPLE VERIFICATION RESPONSE ===")
with open(os.path.join(output, "verifications", "verifications_flood.json")) as f:
    verifs = json.load(f)
first_key = list(verifs.keys())[0]
print("  Anomaly: %s" % first_key)
print(json.dumps(verifs[first_key], indent=2))

# Summary
print("\n=== OUTPUT FILE SUMMARY ===")
for root, dirs, files in os.walk(output):
    for f in sorted(files):
        fpath = os.path.join(root, f)
        size_kb = os.path.getsize(fpath) / 1024
        rel = os.path.relpath(fpath, output)
        print("  %-55s %7.1f KB" % (rel, size_kb))
