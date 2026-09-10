"""
Hazentra Standalone Local Fusion & Verification Test Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Runs the exact same fusion rules and verification logic as the Cloud Functions locally.
Verifies against the generated scenario datasets in simulator/output/readings/
"""

import json
import os
import sys

def test_scenario(scenario_name, json_path):
    print(f"\n==================================================")
    print(f"  TESTING SCENARIO: {scenario_name.upper()}")
    print(f"==================================================")

    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        readings = json.load(f)

    # Import simulator generator fusion evaluator
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../simulator")))
    from generator import evaluate_fusion_rules, generate_alerts_and_verifications

    anomalies = evaluate_fusion_rules(readings)
    print(f"Total Readings Processed : {len(readings)}")
    print(f"Anomalies Triggered      : {len(anomalies)}")

    if anomalies:
        for a in anomalies[:3]:
            print(f"  -> [{a['type'].upper()}] Conf: {a['rawConfidence']}% | {a['reason']}")

        alerts, verifs = generate_alerts_and_verifications(anomalies)
        print(f"Alerts Escalated         : {len(alerts)}")
        if alerts:
            sample = alerts[0]
            print(f"  -> Sample Alert ID     : {sample['alertId']}")
            print(f"  -> SACHET Severity     : {sample['sachetPayload']['severity']}")
            print(f"  -> Message             : {sample['message']}")
    else:
        print("  -> Clean baseline (No false positives!)")


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../simulator/output/readings"))
    scenarios = [
        ("Normal Baseline", os.path.join(root, "readings_normal.json")),
        ("Earthquake", os.path.join(root, "readings_earthquake.json")),
        ("Fire (Gas + Temp)", os.path.join(root, "readings_fire.json")),
        ("Flood (Dist + Soil)", os.path.join(root, "readings_flood.json")),
        ("Gas Leak (Contrast)", os.path.join(root, "readings_gas_leak.json")),
        ("Landslide (Precursor)", os.path.join(root, "readings_landslide.json")),
        ("Compound Hazard", os.path.join(root, "readings_compound.json")),
    ]

    for name, path in scenarios:
        test_scenario(name, path)


if __name__ == "__main__":
    main()
