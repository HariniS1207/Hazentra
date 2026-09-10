"""
Hazentra Hardware-to-Cloud Serial Bridge (Hardened Production Grade)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Connects the physical ESP32 node running on COM4 (115200 baud) directly to Firebase Firestore.
Parses the exact live UART format confirmed from the Arduino Serial Monitor:

  Cycle #186 | Accel: 3.5 m/s^2 | Temp: 33.9 C | Gas: 147 | Dist: 134.5 cm | Soil: 100%

Features:
  - Auto-reconnect loop with backoff if USB cable is unplugged or ESP32 resets
  - Native Firestore Timestamp objects (preserves true UTC dates)
  - Full support for Arduino IDE timestamp prefix or raw UART
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime, timezone

# Robust regex matching integer and floating-point values
LINE_REGEX = re.compile(
    r"(?:.*->\s*)?"                                     # optional Arduino IDE prefix e.g. "19:56:20.232 -> "
    r"Cycle\s*#(?P<cycle>\d+)\s*\|\s*"                  # Cycle #186 |
    r"Accel:\s*(?P<accel>[\d.]+)\s*m/s\^2\s*\|\s*"      # Accel: 3.5 m/s^2 |
    r"Temp:\s*(?P<temp>[\d.]+)\s*C\s*\|\s*"             # Temp: 33.9 C |
    r"Gas:\s*(?P<gasRaw>\d+)\s*\|\s*"                   # Gas: 147 |
    r"Dist:\s*(?P<distance>[\d.]+)\s*cm\s*\|\s*"        # Dist: 134.5 cm |
    r"Soil:\s*(?P<soilMoisture>[\d.]+)%",               # Soil: 100% (or 72.5%)
    re.IGNORECASE
)

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    HAS_FIREBASE = True
except ImportError:
    HAS_FIREBASE = False


def parse_telemetry_line(raw_line):
    """
    Parses a single serial line into a structured reading dictionary.
    Returns None if line does not match the expected telemetry pattern.
    """
    clean = raw_line.strip()
    if not clean:
        return None

    match = LINE_REGEX.search(clean)
    if not match:
        return None

    d = match.groupdict()
    # True UTC timestamp
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    return {
        "cycle": int(d["cycle"]),
        "accel": round(float(d["accel"]), 2),
        "temp": round(float(d["temp"]), 1),
        "gasRaw": int(d["gasRaw"]),
        "distance": round(float(d["distance"]), 1),
        "soilMoisture": round(float(d["soilMoisture"]), 1),
        "timestamp": now_iso,
        "_native_dt": now_utc,
    }


def init_firestore(key_path):
    if not HAS_FIREBASE:
        print("ERROR: firebase-admin not installed. Run: pip install firebase-admin")
        sys.exit(1)

    candidates = [
        key_path,
        os.path.abspath(os.path.join(os.path.dirname(__file__), key_path)) if key_path else None,
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../serviceAccountKey.json")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../simulator/serviceAccountKey.json")),
        "serviceAccountKey.json"
    ]
    resolved = None
    for c in candidates:
        if c and os.path.exists(c):
            resolved = c
            break

    if not resolved:
        print(f"ERROR: serviceAccountKey.json not found at {key_path}")
        sys.exit(1)

    cred = credentials.Certificate(resolved)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()


def run_bridge(port, baud, db, dry_run=False):
    if not HAS_SERIAL:
        print("ERROR: pyserial not installed. Run: pip install pyserial")
        sys.exit(1)

    line_count = 0
    reconnect_delay = 1.0

    print(f"\n=======================================================")
    print(f"  HAZENTRA ESP32 SERIAL BRIDGE (COM PORT: {port})")
    print(f"  Baud Rate: {baud} | Mode: {'DRY RUN' if dry_run else 'FIRESTORE CLOUD'}")
    print(f"=======================================================\n")

    while True:
        ser = None
        try:
            print(f"[BRIDGE] Connecting to {port}...")
            ser = serial.Serial(port, baud, timeout=2)
            print(f"[BRIDGE] Connected to {port}! Streaming telemetry lines...\n")
            reconnect_delay = 1.0  # Reset delay on successful connection

            while True:
                raw = ser.readline().decode("utf-8", errors="replace")
                if not raw:
                    continue

                parsed = parse_telemetry_line(raw)
                if parsed:
                    line_count += 1
                    ts_str = parsed["timestamp"]
                    print(f"[{line_count:04d} | {parsed['timestamp']}] Cycle #{parsed['cycle']} | "
                          f"Accel: {parsed['accel']} m/s^2 | Temp: {parsed['temp']} C | "
                          f"Gas: {parsed['gasRaw']} | Dist: {parsed['distance']} cm | Soil: {parsed['soilMoisture']}%")

                    if not dry_run and db is not None:
                        # Store doc with native Firestore timestamp
                        doc_to_save = dict(parsed)
                        doc_to_save["timestamp"] = parsed["_native_dt"]
                        del doc_to_save["_native_dt"]

                        db.collection("readings").document(ts_str).set(doc_to_save)
                else:
                    stripped = raw.strip()
                    if stripped:
                        print(f"  [RAW/BOOT] {stripped}")

        except serial.SerialException as se:
            print(f"[BRIDGE-WARN] Serial port error: {se}")
            print(f"  Tip: Ensure the Arduino IDE Serial Monitor is CLOSED so {port} is released.")
            print(f"  Reconnecting in {reconnect_delay:.1f}s...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(15.0, reconnect_delay * 1.5)

        except KeyboardInterrupt:
            print(f"\n[BRIDGE] Stopped by user. Processed {line_count} readings.")
            if ser and ser.is_open:
                ser.close()
            break

        except Exception as e:
            print(f"[BRIDGE-ERROR] Unexpected error: {e}")
            time.sleep(2.0)
        finally:
            if ser and ser.is_open:
                ser.close()


def main():
    parser = argparse.ArgumentParser(description="Hazentra ESP32 Serial to Firestore Bridge")
    parser.add_argument("--port", default="COM4", help="Serial COM port (default: COM4)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--key", default="../simulator/serviceAccountKey.json", help="Path to serviceAccountKey.json")
    parser.add_argument("--dry-run", action="store_true", help="Print parsed readings without uploading to Firebase")
    parser.add_argument("--test-line", type=str, help="Test parsing on a single line and exit")
    args = parser.parse_args()

    if args.test_line:
        print("\n--- TEST PARSER ---")
        print("Input :", args.test_line)
        res = parse_telemetry_line(args.test_line)
        print("Parsed:", res)
        if res:
            print("\n[OK] Regex match successful!")
        else:
            print("\n[FAIL] Regex did not match format!")
        return

    db = None
    if not args.dry_run:
        key_path = os.path.abspath(os.path.join(os.path.dirname(__file__), args.key))
        db = init_firestore(key_path)

    run_bridge(args.port, args.baud, db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
