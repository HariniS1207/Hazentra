"""
Hazentra Simulator — CLI Entry Point (Single-Node Architecture)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Usage:
  python main.py                      # Generate all 7 scenarios with sequential timestamps
  python main.py --scenario fire      # Generate specific scenario
  python main.py --list               # Show scenario descriptions
"""

import argparse
import json
import os
import random
from datetime import datetime, timezone, timedelta

from config import NODE_INFO
from generator import (
    SingleNodeTelemetryGenerator,
    evaluate_fusion_rules,
    generate_alerts_and_verifications
)

SCENARIOS = {
    "normal": {
        "description": "24h normal baseline: all 5 sensors nominal, diurnal temp cycle, 0 anomalies",
        "duration_hours": 24,
        "interval_sec": 30,
    },
    "earthquake": {
        "description": "1h seismic scenario: sudden vector accel spike >4.0 m/s^2, debounce-verified",
        "duration_hours": 1,
        "interval_sec": 5,
    },
    "fire": {
        "description": "4h fire event: MQ-135 gasRaw >=150 (spike) AND DHT22 temp rising >0.3C (Fusion)",
        "duration_hours": 4,
        "interval_sec": 10,
    },
    "flood": {
        "description": "8h river overflow: HC-SR04 distance <=10cm AND soil moisture rising (Fusion)",
        "duration_hours": 8,
        "interval_sec": 15,
    },
    "gas_leak": {
        "description": "3h industrial gas leak: gasRaw >=150 (spike) but temp flat (Zero dead zone)",
        "duration_hours": 3,
        "interval_sec": 10,
    },
    "landslide": {
        "description": "6h saturated slope: soil >=70% AND micro-tremors 3.65-4.0 m/s^2",
        "duration_hours": 6,
        "interval_sec": 15,
    },
    "compound": {
        "description": "6h multi-hazard: flood + fire occurring within 90s correlation window",
        "duration_hours": 6,
        "interval_sec": 15,
    },
}

def _banner(text, width=70):
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)

def _save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    size_kb = os.path.getsize(filepath) / 1024
    print(f"  [OK] Saved: {filepath} ({size_kb:.1f} KB)")


def run_scenario(name, sc_def, start_time, output_dir):
    _banner(f"SCENARIO: {name.upper()}")
    print(f"  {sc_def['description']}")
    print(f"  Duration: {sc_def['duration_hours']}h | Interval: {sc_def['interval_sec']}s")
    print(f"  Start Time (UTC): {start_time.isoformat()}")

    gen = SingleNodeTelemetryGenerator()
    readings = gen.generate(
        name,
        start_time,
        sc_def["duration_hours"],
        sc_def["interval_sec"]
    )

    # Save raw readings
    readings_file = os.path.join(output_dir, "readings", f"readings_{name}.json")
    _save_json(readings, readings_file)
    print(f"  Generated {len(readings)} telemetry readings")

    # Run fusion logic
    anomalies = evaluate_fusion_rules(readings)
    if anomalies:
        anom_file = os.path.join(output_dir, "anomalies", f"anomalies_{name}.json")
        _save_json(anomalies, anom_file)
        print(f"  [!] {len(anomalies)} anomalies detected by Cloud Fusion Engine")

        # Run verification loop simulation & alert generation
        alerts, verifs = generate_alerts_and_verifications(anomalies)
        if alerts:
            alerts_file = os.path.join(output_dir, "alerts", f"alerts_{name}.json")
            _save_json(alerts, alerts_file)
            print(f"  [ALERT] {len(alerts)} alerts escalated with SACHET payloads")

        if verifs:
            verifs_file = os.path.join(output_dir, "verifications", f"verifications_{name}.json")
            _save_json(verifs, verifs_file)
            print(f"  [SMS] {len(verifs)} verification cycles simulated")
    else:
        print("  [OK] 0 anomalies detected (Clean baseline)")

    return len(readings), len(anomalies)


def main():
    parser = argparse.ArgumentParser(description="Hazentra Single-Node Telemetry & Fusion Simulator")
    parser.add_argument("--scenario", "-s", default="all", choices=list(SCENARIOS.keys()) + ["all"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", "-o", default="output")
    parser.add_argument("--list", "-l", action="store_true")
    args = parser.parse_args()

    if args.list:
        print("\nAvailable Scenarios:")
        for k, v in SCENARIOS.items():
            print(f"  {k:15s} : {v['description']}")
        return

    random.seed(args.seed)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, args.output)

    # Use true UTC baseline
    base_start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    _banner("HAZENTRA MULTI-HAZARD SIMULATOR (SINGLE INTEGRATED NODE)")
    print(f"  Node ID     : {NODE_INFO['nodeId']}")
    print(f"  Sensors     : ADXL345, DHT22, HC-SR04, MQ-135, Soil Moisture")
    print(f"  Base Time   : {base_start_time.isoformat()}")
    print(f"  Output Dir  : {output_dir}")

    # Save node metadata
    _save_json(NODE_INFO, os.path.join(output_dir, "node_info.json"))

    scenarios = list(SCENARIOS.keys()) if args.scenario == "all" else [args.scenario]
    total_readings = 0
    total_anomalies = 0

    current_time = base_start_time
    for sc in scenarios:
        r_cnt, a_cnt = run_scenario(sc, SCENARIOS[sc], current_time, output_dir)
        total_readings += r_cnt
        total_anomalies += a_cnt
        # Stagger each scenario in time so documents don't collide when batch uploaded
        current_time += timedelta(hours=SCENARIOS[sc]["duration_hours"] + 1)

    _banner("SIMULATION COMPLETED")
    print(f"  Total Scenarios : {len(scenarios)}")
    print(f"  Total Readings  : {total_readings:,}")
    print(f"  Total Anomalies : {total_anomalies}")
    print(f"  Output Directory: {output_dir}\n")


if __name__ == "__main__":
    main()
