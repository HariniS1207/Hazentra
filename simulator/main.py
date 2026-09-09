"""
Hazentra Simulator — CLI Entry Point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Usage:
  python main.py                          # Generate ALL scenarios
  python main.py --scenario normal        # Single scenario
  python main.py --scenario flood --duration 12 --interval 30
  python main.py --scenario all --format firestore   # Firestore-ready nested JSON
  python main.py --list                   # List available scenarios

Outputs JSON files into simulator/output/ matching the Firestore schema.
"""

import argparse
import json
import os
import sys
from datetime import datetime

from config import NODES
from generator import (
    FloodNodeGenerator,
    AirQualityNodeGenerator,
    generate_node_docs,
    generate_sample_anomalies,
    generate_sample_alerts,
    generate_sample_verifications,
)


# ── Scenario definitions ────────────────────────────────────────────────────

SCENARIOS = {
    "normal": {
        "description": "Normal monsoon day - 24h baseline with light rain, stable water, moderate AQI",
        "duration_hours": 24,
        "flood_node_scenario": "normal",
        "airq_node_scenario": "normal",
    },
    "flood": {
        "description": "Progressive flood - 12h heavy rain -> water level rise -> peak -> recession",
        "duration_hours": 12,
        "flood_node_scenario": "flood",
        "airq_node_scenario": "normal",
    },
    "flash_flood": {
        "description": "Flash flood - 4h sudden cloudburst -> rapid water rise -> partial recession",
        "duration_hours": 4,
        "flood_node_scenario": "flash_flood",
        "airq_node_scenario": "normal",
    },
    "fire": {
        "description": "Fire/smoke event - 6h sharp smoke spike -> sustained -> decay",
        "duration_hours": 6,
        "flood_node_scenario": "normal",
        "airq_node_scenario": "fire",
    },
    "pollution_drift": {
        "description": "Gradual AQI deterioration - 8h slow rise to Very Poor, no sharp spike (contrast case for fusion logic)",
        "duration_hours": 8,
        "flood_node_scenario": "normal",
        "airq_node_scenario": "pollution_drift",
    },
    "compound": {
        "description": "COMPOUND EVENT - flood + fire simultaneously from nearby nodes (12h, cross-hazard fusion test)",
        "duration_hours": 12,
        "flood_node_scenario": "compound",
        "airq_node_scenario": "compound",
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
    print(f"  [OK] Saved: {filepath}  ({size_kb:.1f} KB)")


def generate_scenario(name, scenario_def, start_time, interval_sec,
                      duration_override=None, output_dir="output"):
    """Generate readings for a single scenario and save to JSON."""
    duration = duration_override or scenario_def["duration_hours"]

    _banner(f"Scenario: {name.upper()}")
    print(f"  {scenario_def['description']}")
    print(f"  Duration: {duration}h | Interval: {interval_sec}s | "
          f"Readings per node: {int(duration * 3600 / interval_sec)}")
    print()

    flood_gen = FloodNodeGenerator("flood-node-01")
    airq_gen = AirQualityNodeGenerator("airq-node-01")

    flood_readings = flood_gen.generate(
        scenario_def["flood_node_scenario"],
        start_time, duration, interval_sec,
    )
    airq_readings = airq_gen.generate(
        scenario_def["airq_node_scenario"],
        start_time, duration, interval_sec,
    )

    # ── Save readings ──
    readings_dir = os.path.join(output_dir, "readings")
    _save_json(flood_readings,
               os.path.join(readings_dir, f"flood_node_{name}.json"))
    _save_json(airq_readings,
               os.path.join(readings_dir, f"airq_node_{name}.json"))

    # ── Generate & save anomalies ──
    readings_by_node = {
        "flood-node-01": flood_readings,
        "airq-node-01": airq_readings,
    }
    anomalies = generate_sample_anomalies(readings_by_node)

    if anomalies:
        _save_json(anomalies,
                   os.path.join(output_dir, "anomalies", f"anomalies_{name}.json"))
        print(f"  [!] {len(anomalies)} anomalies detected")

        # ── Generate alerts (from high-confidence anomalies) ──
        alerts = generate_sample_alerts(anomalies)
        if alerts:
            _save_json(alerts,
                       os.path.join(output_dir, "alerts", f"alerts_{name}.json"))
            print(f"  [ALERT] {len(alerts)} alerts escalated (with SACHET payloads)")

        # ── Generate sample verification responses ──
        verifications = generate_sample_verifications(anomalies)
        if verifications:
            _save_json(verifications,
                       os.path.join(output_dir, "verifications",
                                    f"verifications_{name}.json"))
            print(f"  [SMS] {len(verifications)} verification response sets generated")
    else:
        print("  [OK] No anomalies (expected for baseline scenario)")

    total_readings = len(flood_readings) + len(airq_readings)
    print(f"\n  Total readings generated: {total_readings}")
    return flood_readings, airq_readings, anomalies


def main():
    parser = argparse.ArgumentParser(
        description="Hazentra Synthetic Data Generator — "
                    "Generates realistic sensor data calibrated against IMD/CPCB."
    )
    parser.add_argument(
        "--scenario", "-s",
        choices=list(SCENARIOS.keys()) + ["all"],
        default="all",
        help="Scenario to generate (default: all)",
    )
    parser.add_argument(
        "--duration", "-d", type=float, default=None,
        help="Override scenario duration (hours)",
    )
    parser.add_argument(
        "--interval", "-i", type=int, default=30,
        help="Sensor polling interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--start-time", "-t", type=str, default=None,
        help="Start timestamp (ISO format, default: now)",
    )
    parser.add_argument(
        "--output", "-o", type=str, default="output",
        help="Output directory (default: output/)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="List available scenarios and exit",
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable scenarios:")
        for name, s in SCENARIOS.items():
            print(f"  {name:18s} — {s['description']}")
        print(f"\n  {'all':18s} — Generate all scenarios at once")
        return

    # Reproducible output
    import random
    random.seed(args.seed)

    if args.start_time:
        start_time = datetime.fromisoformat(args.start_time)
    else:
        # Default: today at 6:00 AM IST (realistic monsoon morning)
        now = datetime.now()
        start_time = now.replace(hour=6, minute=0, second=0, microsecond=0)

    # Resolve output dir relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, args.output)

    _banner("HAZENTRA SYNTHETIC DATA GENERATOR")
    print(f"  Start time : {start_time.isoformat()}")
    print(f"  Interval   : {args.interval}s")
    print(f"  Seed       : {args.seed}")
    print(f"  Output dir : {output_dir}")

    # ── Generate node registration docs ──
    nodes = generate_node_docs(start_time)
    _save_json(nodes, os.path.join(output_dir, "nodes.json"))
    print(f"  [OK] {len(nodes)} node documents generated")

    # ── Generate scenarios ──
    scenarios_to_run = (
        list(SCENARIOS.keys()) if args.scenario == "all"
        else [args.scenario]
    )

    total_readings = 0
    total_anomalies = 0
    for name in scenarios_to_run:
        scenario_def = SCENARIOS[name]
        flood_r, airq_r, anomalies = generate_scenario(
            name, scenario_def, start_time, args.interval,
            args.duration, output_dir,
        )
        total_readings += len(flood_r) + len(airq_r)
        total_anomalies += len(anomalies)

    _banner("GENERATION COMPLETE")
    print(f"  Scenarios     : {len(scenarios_to_run)}")
    print(f"  Total readings: {total_readings:,}")
    print(f"  Total anomalies: {total_anomalies}")
    print(f"  Output dir    : {output_dir}")
    print()


if __name__ == "__main__":
    main()
