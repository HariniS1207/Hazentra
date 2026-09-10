# ESP32 Multi-Sensor Disaster Alert System — Software Layer

This is the software side that consumes telemetry from your ESP32 firmware
(the `printSerialTelemetry()` output) and turns it into a live monitoring
dashboard with persistent alert history.

## How it fits together

```
[ ESP32 + Sensors ]  --USB Serial-->  [ serial_reader.py ]  -->  [ database.py (SQLite) ]
                                              |
                                              v
                                     [ app.py: Flask + Socket.IO ]
                                              |
                                              v
                                   [ Browser dashboard (live) ]
```

- The firmware already prints one line per cycle like:
  `Cycle #123 | Accel: 3.5 m/s^2 | Temp: 25.0 C | Gas: 100 | Dist: 50.0 cm | Soil: 30%`
- `serial_reader.py` reads and parses that line every ~0.5s (matching the firmware's `delay(500)`).
- `app.py` re-applies the exact same thresholds and debounce-count-of-2 logic as the
  firmware, server-side — so the dashboard doesn't just trust the LCD, it independently
  confirms each alert. Every reading and every alert transition (triggered/resolved) is
  saved to `disaster_alert.db` (SQLite).
- The dashboard updates live over WebSocket — no page refresh needed.

## Setup

```bash
cd disaster_alert_system/backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The frontend files are referenced relative to `backend/`, so run `app.py` from inside
`backend/` (Flask is configured to find `../frontend/templates` and `../frontend/static`
automatically via the default Flask app structure — see note below).

## Running

**With real hardware attached:**
```bash
python app.py --port /dev/ttyUSB0      # Linux/Mac
python app.py --port COM5              # Windows
```

**Without hardware (simulated data, for development/demo):**
```bash
python app.py
```

Then open **http://localhost:5000** in a browser.

## Project structure notes

- `app.py` expects `frontend/templates` and `frontend/static` to sit one level up from
  `backend/`. If you'd rather keep everything flat, move `frontend/templates` and
  `frontend/static` into `backend/` and Flask's defaults will pick them up with no code
  changes. Alternatively, add this to `app.py`:
  ```python
  app = Flask(__name__, template_folder="../frontend/templates",
              static_folder="../frontend/static")
  ```
  (already the assumption baked into the current `Flask(__name__)` call once you drop
  the frontend folder next to backend — adjust the path if you reorganize.)

## Extending this

- **Cloud/remote alerting:** add a Twilio/SMTP call inside `handle_reading()` in `app.py`
  whenever `status["newly_triggered"]` is non-empty.
- **Multiple devices:** tag each reading with a `device_id` and add it to the DB schema
  and SocketIO room so one dashboard can monitor several ESP32 units.
- **Mobile app:** the same `/api/history` and `/api/alerts` REST endpoints can back a
  simple mobile client — no need to duplicate the threshold logic there.
- **Data export:** SQLite is easy to query directly, or add a `/api/export.csv` route
  using Python's `csv` module for report-ready exports.

## Files

| File | Purpose |
|---|---|
| `backend/serial_reader.py` | Reads/parses ESP32 serial lines (or simulates them) |
| `backend/database.py` | SQLite schema + read/write helpers |
| `backend/app.py` | Flask + Socket.IO server, threshold/debounce re-evaluation |
| `backend/requirements.txt` | Python dependencies |
| `frontend/templates/index.html` | Dashboard page |
| `frontend/static/js/dashboard.js` | Live updates via Socket.IO + Chart.js |
| `frontend/static/css/style.css` | Dashboard styling |
