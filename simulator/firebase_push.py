"""
Hazentra Simulator — Firebase Firestore Uploader (Hardened)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Uploads generated synthetic data to Firestore matching CLAUDE.md Section 9 schema:
  /readings/{timestamp} -> { accel, temp, distance, gasRaw, soilMoisture, cycle, timestamp }
  /anomalies/{anomalyId}
  /verifications/{anomalyId}/responses/{phone}
  /alerts/{alertId}

Features:
  1. BATCH MODE (--batch): Uploads pre-generated JSON files with native Timestamp conversion.
  2. LIVE STREAMING (--live <scenario>): Continuous time-progressed streaming where scenario
     events (e.g. fire at 20m, flood at 30m) evolve realistically in real time.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    HAS_FIREBASE = True
except ImportError:
    HAS_FIREBASE = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KEY_PATH = os.path.join(SCRIPT_DIR, "serviceAccountKey.json")
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")


def _init_firestore(key_path=None):
    if not HAS_FIREBASE:
        print("ERROR: firebase-admin is not installed.")
        print("  Install it: pip install firebase-admin")
        sys.exit(1)

    key = key_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", DEFAULT_KEY_PATH)
    if not os.path.exists(key):
        print(f"ERROR: Service account key not found at {key}")
        print("  Place your serviceAccountKey.json in the simulator/ directory or specify with --key")
        sys.exit(1)

    cred = credentials.Certificate(key)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()


def _to_native_dt(iso_str):
    """Converts ISO 8601 string to Python datetime with UTC timezone for native Firestore Timestamp storage."""
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def batch_upload(db, output_dir=DEFAULT_OUTPUT_DIR, scenario=None):
    print("\n=======================================================")
    print("  BATCH UPLOAD TO FIRESTORE (NATIVE TIMESTAMP STORAGE)")
    print("=======================================================\n")

    # 1. Node Metadata
    node_file = os.path.join(output_dir, "node_info.json")
    if os.path.exists(node_file):
        with open(node_file, "r", encoding="utf-8") as f:
            node_data = json.load(f)
        db.collection("nodes").document(node_data["nodeId"]).set(node_data)
        print(f"  [OK] Uploaded node metadata for {node_data['nodeId']}")

    # 2. Readings (/readings/{timestamp})
    readings_dir = os.path.join(output_dir, "readings")
    if os.path.exists(readings_dir):
        for fname in sorted(os.listdir(readings_dir)):
            if scenario and scenario not in fname:
                continue
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(readings_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                readings = json.load(f)

            batch = db.batch()
            count = 0
            for r in readings:
                ts_str = r["timestamp"]
                doc_data = dict(r)
                # Store as native Firestore Timestamp
                doc_data["timestamp"] = _to_native_dt(ts_str)

                doc_ref = db.collection("readings").document(ts_str)
                batch.set(doc_ref, doc_data)
                count += 1
                if count % 400 == 0:
                    batch.commit()
                    batch = db.batch()
            batch.commit()
            print(f"  [OK] Uploaded {count} readings from {fname} (with native Timestamps)")

    # 3. Anomalies (/anomalies/{anomalyId})
    anomalies_dir = os.path.join(output_dir, "anomalies")
    if os.path.exists(anomalies_dir):
        for fname in sorted(os.listdir(anomalies_dir)):
            if scenario and scenario not in fname:
                continue
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(anomalies_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                anomalies = json.load(f)
            for a in anomalies:
                aid = a["anomalyId"]
                doc_data = dict(a)
                doc_data["timestamp"] = _to_native_dt(a["timestamp"])
                db.collection("anomalies").document(aid).set(doc_data)
            print(f"  [OK] Uploaded {len(anomalies)} anomalies from {fname}")

    # 4. Alerts (/alerts/{alertId})
    alerts_dir = os.path.join(output_dir, "alerts")
    if os.path.exists(alerts_dir):
        for fname in sorted(os.listdir(alerts_dir)):
            if scenario and scenario not in fname:
                continue
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(alerts_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                alerts = json.load(f)
            for al in alerts:
                alid = al["alertId"]
                doc_data = dict(al)
                doc_data["timestamp"] = _to_native_dt(al["timestamp"])
                if "sachetPayload" in doc_data and "timestamp" in doc_data["sachetPayload"]:
                    doc_data["sachetPayload"]["timestamp"] = _to_native_dt(doc_data["sachetPayload"]["timestamp"])
                db.collection("alerts").document(alid).set(doc_data)
            print(f"  [OK] Uploaded {len(alerts)} alerts from {fname}")

    # 5. Verifications (/verifications/{anomalyId}/responses/{phone})
    verifs_dir = os.path.join(output_dir, "verifications")
    if os.path.exists(verifs_dir):
        for fname in sorted(os.listdir(verifs_dir)):
            if scenario and scenario not in fname:
                continue
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(verifs_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                verifs = json.load(f)
            for aid, phones in verifs.items():
                db.collection("verifications").document(aid).set({"anomalyId": aid}, merge=True)
                for phone, pdata in phones.items():
                    p_doc = dict(pdata)
                    p_doc["timestamp"] = _to_native_dt(pdata["timestamp"])
                    db.collection("verifications").document(aid).collection("responses").document(phone).set(p_doc)
            print(f"  [OK] Uploaded verifications from {fname}")

    print("\n  [OK] Batch upload complete!\n")


def live_stream(db, scenario_name, interval_sec=5, time_scale=1.0):
    """
    Live streaming with accumulating elapsed seconds.
    Ensures scenario physics evolve realistically over time.
    """
    from generator import SingleNodeTelemetryGenerator
    gen = SingleNodeTelemetryGenerator()

    print("\n=======================================================")
    print(f"  LIVE STREAMING — Scenario: {scenario_name.upper()}")
    print(f"  Interval: {interval_sec}s  |  Time Acceleration: {time_scale}x")
    print("  Press Ctrl+C to stop")
    print("=======================================================\n")

    step = 0
    elapsed_sim_seconds = 0.0

    try:
        while True:
            now_dt = datetime.now(timezone.utc)
            # Generate reading at the current simulated elapsed point
            r = gen.generate_single_reading(scenario_name, elapsed_sim_seconds, now_dt)
            ts_str = r["timestamp"]

            doc_data = dict(r)
            doc_data["timestamp"] = _to_native_dt(ts_str)

            if db:
                db.collection("readings").document(ts_str).set(doc_data)

            step += 1
            min_elapsed = elapsed_sim_seconds / 60.0
            print(f"  [{step:04d} | Sim +{min_elapsed:.1f}m] Accel: {r['accel']} m/s^2 | "
                  f"Temp: {r['temp']} C | Gas: {r['gasRaw']} | Dist: {r['distance']} cm | Soil: {r['soilMoisture']}%")

            # Advance simulated time
            elapsed_sim_seconds += (interval_sec * time_scale)
            time.sleep(interval_sec)

    except KeyboardInterrupt:
        print(f"\n  [OK] Live streaming stopped after {step} readings.\n")


def main():
    parser = argparse.ArgumentParser(description="Upload Hazentra Telemetry to Firestore")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--batch", action="store_true", help="Batch upload JSON files")
    group.add_argument("--live", metavar="SCENARIO", help="Live stream simulated readings")

    parser.add_argument("--key", default=None, help="Path to serviceAccountKey.json")
    parser.add_argument("--scenario", default=None, help="Filter batch to specific scenario")
    parser.add_argument("--interval", type=int, default=5, help="Live interval in seconds")
    parser.add_argument("--scale", type=float, default=1.0, help="Simulation time acceleration factor (e.g. 5.0 for 5x fast forward)")
    args = parser.parse_args()

    db = _init_firestore(args.key)
    if args.batch:
        batch_upload(db, scenario=args.scenario)
    else:
        live_stream(db, args.live, args.interval, args.scale)


if __name__ == "__main__":
    main()
