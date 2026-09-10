"""
app.py
------
Flask + Socket.IO server for the ESP32 Multi-Sensor Disaster Alert dashboard.

Responsibilities:
- Start the SerialReader background thread (real hardware or simulator)
- Re-apply the SAME thresholds/debounce logic as the firmware, server-side,
  so the dashboard doesn't blindly trust a single noisy reading
- Persist every reading + alert transition to SQLite
- Push live updates to connected browsers over WebSocket

Run:
    pip install -r requirements.txt
    python app.py --port COM5          # Windows example
    python app.py --port /dev/ttyUSB0  # Linux example
    python app.py                      # no --port => runs with simulated data
"""

import argparse
import threading

from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO

import database as db
from serial_reader import SerialReader

# ----------------------------------------------------------------------------
# Thresholds & debounce limit — MUST mirror the firmware constants exactly.
# ----------------------------------------------------------------------------
HEAT_TEMP_LIMIT_C = 35.0
FLOOD_DIST_CM_THRESHOLD = 10.0
GAS_PPM_RAW_THRESHOLD = 150
SOIL_SAT_PERCENT_LIMIT = 70
VIBRATION_G_THRESHOLD = 4.0
DEBOUNCE_COUNT_LIMIT = 2

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static",
)
app.config["SECRET_KEY"] = "disaster-alert-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Debounce counters (server-side mirror of the firmware's logic)
_debounce = {"quake": 0, "heat": 0, "flood": 0, "gas": 0, "soil": 0}
_active_disasters = set()
_lock = threading.Lock()

DISASTER_LABELS = {
    "quake": "EARTHQUAKE",
    "heat": "FIRE DISASTER",
    "flood": "FLOOD ALERT",
    "gas": "AIR QUALITY ALERT",
    "soil": "LANDSLIDE RISK",
}


def evaluate_disasters(data: dict):
    """Applies debounce logic identical to checkDisasterConditions() in firmware."""
    triggers = {
        "quake": data["accel"] > VIBRATION_G_THRESHOLD,
        "heat": data["temp"] > HEAT_TEMP_LIMIT_C,
        "flood": data["dist"] <= FLOOD_DIST_CM_THRESHOLD,
        "gas": data["gas"] >= GAS_PPM_RAW_THRESHOLD,
        "soil": data["soil"] >= SOIL_SAT_PERCENT_LIMIT,
    }
    trigger_values = {
        "quake": data["accel"], "heat": data["temp"], "flood": data["dist"],
        "gas": data["gas"], "soil": data["soil"],
    }

    newly_triggered, newly_resolved = [], []

    with _lock:
        for key, is_over in triggers.items():
            _debounce[key] = _debounce[key] + 1 if is_over else 0

            is_active = _debounce[key] >= DEBOUNCE_COUNT_LIMIT
            was_active = key in _active_disasters

            if is_active and not was_active:
                _active_disasters.add(key)
                newly_triggered.append(key)
            elif not is_active and was_active:
                _active_disasters.discard(key)
                newly_resolved.append(key)

        active_now = list(_active_disasters)

    for key in newly_triggered:
        db.open_alert(DISASTER_LABELS[key], trigger_values[key])
    for key in newly_resolved:
        db.resolve_open_alerts(DISASTER_LABELS[key])

    return {
        "active": [DISASTER_LABELS[k] for k in active_now],
        "newly_triggered": [DISASTER_LABELS[k] for k in newly_triggered],
        "newly_resolved": [DISASTER_LABELS[k] for k in newly_resolved],
    }


def handle_reading(data: dict):
    """Callback invoked by SerialReader for every parsed telemetry line."""
    db.save_reading(data)
    status = evaluate_disasters(data)
    socketio.emit("telemetry", {"reading": data, "status": status})


# ----------------------------------------------------------------------------
# HTTP routes
# ----------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/history")
def api_history():
    return jsonify(db.get_recent_readings(limit=100))


@app.route("/api/alerts")
def api_alerts():
    return jsonify(db.get_alert_history(limit=50))


def main():
    parser = argparse.ArgumentParser(description="ESP32 Disaster Alert dashboard server")
    parser.add_argument("--port", default=None, help="Serial port, e.g. COM5 or /dev/ttyUSB0")
    parser.add_argument("--baud", default=115200, type=int, help="Baud rate (default 115200)")
    parser.add_argument("--web-port", default=5000, type=int, help="Web server port (default 5000)")
    args = parser.parse_args()

    db.init_db()

    reader = SerialReader(port=args.port, baudrate=args.baud, on_reading=handle_reading)
    reader.start()

    print(f"[app] Dashboard running at http://localhost:{args.web_port}")
    socketio.run(app, host="0.0.0.0", port=args.web_port, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
