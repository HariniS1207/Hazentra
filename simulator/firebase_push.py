"""
Hazentra Simulator - Firebase Firestore Uploader
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Uploads generated JSON data to Firestore in two modes:

  1. BATCH MODE (default):
     Reads pre-generated JSON files from output/ and writes them all at once.

  2. LIVE MODE (--live):
     Generates readings in real time at the configured interval and streams
     them to Firestore, simulating live sensor nodes for demo purposes.

Setup:
  1. Place your Firebase service account key JSON at:
       simulator/serviceAccountKey.json
     (or set GOOGLE_APPLICATION_CREDENTIALS env var)
  2. pip install firebase-admin
  3. python firebase_push.py --batch       # upload pre-generated data
     python firebase_push.py --live flood  # stream flood scenario live
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

# Defer firebase-admin import to give a clean error if not installed
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
    """Initialise Firebase Admin SDK and return a Firestore client."""
    if not HAS_FIREBASE:
        print("ERROR: firebase-admin is not installed.")
        print("  Install it:  pip install firebase-admin")
        sys.exit(1)

    key = key_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS",
                                      DEFAULT_KEY_PATH)
    if not os.path.exists(key):
        print(f"ERROR: Service account key not found at {key}")
        print("  Download it from Firebase Console -> Project Settings -> "
              "Service Accounts -> Generate New Private Key")
        sys.exit(1)

    cred = credentials.Certificate(key)
    firebase_admin.initialize_app(cred)
    return firestore.client()


# ----------------------------------------------------------------------------
# BATCH UPLOAD
# ----------------------------------------------------------------------------

def batch_upload(db, output_dir=DEFAULT_OUTPUT_DIR, scenario=None):
    """Upload all generated JSON data to Firestore."""
    print("\n=======================================================")
    print("  BATCH UPLOAD TO FIRESTORE")
    print("=======================================================\n")

    # -- 1. Nodes --
    nodes_path = os.path.join(output_dir, "nodes.json")
    if os.path.exists(nodes_path):
        with open(nodes_path) as f:
            nodes = json.load(f)
        for node_id, data in nodes.items():
            db.collection("nodes").document(node_id).set(data)
        print(f"  [OK] Uploaded {len(nodes)} node documents")

    # -- 2. Readings --
    readings_dir = os.path.join(output_dir, "readings")
    if os.path.exists(readings_dir):
        for fname in os.listdir(readings_dir):
            if scenario and scenario not in fname:
                continue
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(readings_dir, fname)
            with open(fpath) as f:
                readings = json.load(f)

            batch = db.batch()
            count = 0
            for r in readings:
                node_id = r.pop("nodeId", "unknown")
                ts = r.get("timestamp", "")
                doc_ref = db.collection("readings").document(node_id) \
                            .collection("logs").document(ts)
                batch.set(doc_ref, r)
                count += 1
                if count % 500 == 0:
                    batch.commit()
                    batch = db.batch()
            batch.commit()
            print(f"  [OK] Uploaded {count} readings from {fname}")

    # -- 3. Anomalies --
    anomalies_dir = os.path.join(output_dir, "anomalies")
    if os.path.exists(anomalies_dir):
        for fname in os.listdir(anomalies_dir):
            if scenario and scenario not in fname:
                continue
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(anomalies_dir, fname)
            with open(fpath) as f:
                anomalies = json.load(f)
            for a in anomalies:
                aid = a.pop("anomalyId", None)
                if aid:
                    db.collection("anomalies").document(aid).set(a)
            print(f"  [OK] Uploaded {len(anomalies)} anomalies from {fname}")

    # -- 4. Alerts --
    alerts_dir = os.path.join(output_dir, "alerts")
    if os.path.exists(alerts_dir):
        for fname in os.listdir(alerts_dir):
            if scenario and scenario not in fname:
                continue
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(alerts_dir, fname)
            with open(fpath) as f:
                alerts = json.load(f)
            for al in alerts:
                alid = al.pop("alertId", None)
                if alid:
                    db.collection("alerts").document(alid).set(al)
            print(f"  [OK] Uploaded {len(alerts)} alerts from {fname}")

    # -- 5. Verifications --
    verif_dir = os.path.join(output_dir, "verifications")
    if os.path.exists(verif_dir):
        for fname in os.listdir(verif_dir):
            if scenario and scenario not in fname:
                continue
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(verif_dir, fname)
            with open(fpath) as f:
                verifications = json.load(f)
            for anomaly_id, responses in verifications.items():
                for phone, data in responses.items():
                    db.collection("verifications").document(anomaly_id) \
                      .collection("responses").document(phone).set(data)
            print(f"  [OK] Uploaded verifications from {fname}")

    print("\n  [OK] Batch upload complete!\n")


# ----------------------------------------------------------------------------
# LIVE STREAMING
# ----------------------------------------------------------------------------

def live_stream(db, scenario_name, interval_sec=30):
    """
    Generate and stream readings to Firestore in real time.
    This simulates live sensor nodes for demo / dashboard testing.
    Press Ctrl+C to stop.
    """
    from generator import FloodNodeGenerator, AirQualityNodeGenerator
    from config import NODES
    import random

    random.seed()  # non-deterministic for live mode

    print("\n=======================================================")
    print(f"  LIVE STREAMING - Scenario: {scenario_name.upper()}")
    print(f"  Interval: {interval_sec}s  |  Press Ctrl+C to stop")
    print("=======================================================\n")

    # Determine which generator method to use
    flood_gen = FloodNodeGenerator("flood-node-01")
    airq_gen = AirQualityNodeGenerator("airq-node-01")

    scenario_map = {
        "normal":          ("normal", "normal"),
        "flood":           ("flood", "normal"),
        "flash_flood":     ("flash_flood", "normal"),
        "fire":            ("normal", "fire"),
        "pollution_drift": ("normal", "pollution_drift"),
        "compound":        ("compound", "compound"),
    }

    flood_scen, airq_scen = scenario_map.get(scenario_name, ("normal", "normal"))

    start_time = datetime.now()
    reading_count = 0

    # Upload node docs
    for nid, ndata in NODES.items():
        db.collection("nodes").document(nid).set({
            **ndata,
            "lastSeen": start_time.isoformat() + "Z",
        })

    try:
        while True:
            now = datetime.now()
            elapsed_min = (now - start_time).total_seconds() / 60.0

            # Generate readings
            flood_reading = flood_gen.generate(
                flood_scen, now, interval_sec / 3600, interval_sec
            )
            airq_reading = airq_gen.generate(
                airq_scen, now, interval_sec / 3600, interval_sec
            )

            # Take just the first reading from each (we're doing one at a time)
            for readings, node_id in [(flood_reading, "flood-node-01"),
                                      (airq_reading, "airq-node-01")]:
                if readings:
                    r = readings[0]
                    r.pop("nodeId", None)
                    ts = r.get("timestamp", now.isoformat() + "Z")

                    # Write to Firestore
                    db.collection("readings").document(node_id) \
                      .collection("logs").document(ts).set(r)

                    # Update node lastSeen
                    db.collection("nodes").document(node_id).update({
                        "lastSeen": ts,
                        "status": "online",
                    })

            reading_count += 2
            elapsed_str = f"{int(elapsed_min)}m{int((elapsed_min % 1) * 60)}s"
            print(f"  [{elapsed_str}] Streamed reading pair #{reading_count // 2} "
                  f"(total: {reading_count} readings)")

            time.sleep(interval_sec)

    except KeyboardInterrupt:
        print(f"\n\n  [OK] Stopped. Total readings streamed: {reading_count}")
        print(f"  [OK] Duration: {(datetime.now() - start_time).total_seconds() / 60:.1f} min\n")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Upload Hazentra synthetic data to Firebase Firestore"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--batch", action="store_true",
                      help="Upload pre-generated JSON files")
    mode.add_argument("--live", metavar="SCENARIO",
                      choices=["normal", "flood", "flash_flood", "fire",
                               "pollution_drift", "compound"],
                      help="Stream readings in real-time for a scenario")

    parser.add_argument("--key", default=None,
                        help="Path to Firebase service account key JSON")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="Directory with generated JSON files (batch mode)")
    parser.add_argument("--scenario", default=None,
                        help="Filter batch upload to a specific scenario")
    parser.add_argument("--interval", type=int, default=30,
                        help="Polling interval in seconds (live mode, default: 30)")

    args = parser.parse_args()

    db = _init_firestore(args.key)

    if args.batch:
        batch_upload(db, args.output_dir, args.scenario)
    else:
        live_stream(db, args.live, args.interval)


if __name__ == "__main__":
    main()
