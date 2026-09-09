"""
Hazentra Synthetic Data Generator — Core Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Generates realistic, IMD/CPCB-calibrated sensor time-series for every
scenario the Hazentra prototype needs to handle:

  • Normal monsoon day  (24 h baseline)
  • Flood build-up      (12 h progressive event)
  • Flash flood          (4 h sudden event)
  • Fire / smoke event   (6 h)
  • Pollution drift      (8 h gradual AQI deterioration)
  • Compound event       (12 h — flood + fire from separate nodes)

Physics modelled:
  - Diurnal temperature / humidity cycles
  - Rainfall → delayed water-level response (1-3 h lag)
  - Rain → soil moisture saturation
  - Sharp vs. gradual gas/smoke rise (fire vs. pollution drift)
  - Correlated sensor noise and occasional sensor glitches

All output matches the Firestore schema in CLAUDE_Hazentra.md Section 9.
"""

import math
import random
import uuid
import copy
from datetime import datetime, timedelta

from config import (
    NODES, NODE_SENSORS, SENSOR_NOISE, THRESHOLDS,
    TEMP_MONSOON, HUMIDITY_MONSOON,
    SACHET_PAYLOAD_TEMPLATE,
)


# ────────────────────────────────────────────────────────────────────────────
# MATH HELPERS
# ────────────────────────────────────────────────────────────────────────────

def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _add_noise(value, sensor_key, lo=None, hi=None):
    """Add Gaussian sensor noise and optionally clamp."""
    sigma = SENSOR_NOISE.get(sensor_key, 0)
    noisy = value + random.gauss(0, sigma)
    if lo is not None or hi is not None:
        noisy = _clamp(noisy, lo if lo is not None else -1e9,
                        hi if hi is not None else 1e9)
    return round(noisy, 2)


def _smooth(t, duration, start, end):
    """Hermite (smoothstep) interpolation from *start* to *end* over *duration*."""
    if duration <= 0:
        return end
    p = _clamp(t / duration, 0.0, 1.0)
    s = p * p * (3 - 2 * p)          # smoothstep
    return start + (end - start) * s


def _diurnal(hour, mean, amplitude, peak_hour=14.0):
    """Sinusoidal 24-h cycle peaking at *peak_hour*."""
    return mean + amplitude * math.sin((hour - peak_hour + 6) * math.pi / 12)


def _hour_of(ts):
    """Fractional hour-of-day from a datetime."""
    return ts.hour + ts.minute / 60.0 + ts.second / 3600.0


def _iso(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _generate_timestamps(start, duration_hours, interval_seconds):
    """Yield (datetime, elapsed_minutes) tuples."""
    total = int(duration_hours * 3600 / interval_seconds)
    for i in range(total):
        ts = start + timedelta(seconds=i * interval_seconds)
        elapsed_min = (i * interval_seconds) / 60.0
        yield ts, elapsed_min


# ────────────────────────────────────────────────────────────────────────────
# FLOOD NODE GENERATOR
# ────────────────────────────────────────────────────────────────────────────

class FloodNodeGenerator:
    """Generates readings for flood-node-01 (HC-SR04, DHT22, soil, MPU6050)."""

    def __init__(self, node_id="flood-node-01"):
        self.node_id = node_id
        self.node = NODES[node_id]
        # Running state (random-walk memory)
        self._water_level = 310.0   # cm from sensor — normal
        self._soil_moisture = 42.0  # %
        self._vibration_base = 0.02

    def _reset(self):
        self._water_level = 310.0
        self._soil_moisture = 42.0
        self._vibration_base = 0.02

    # ── baseline (normal monsoon day) ───────────────────────────────────

    def _baseline(self, ts):
        hour = _hour_of(ts)

        temp = _diurnal(hour, TEMP_MONSOON["mean"],
                        TEMP_MONSOON["diurnal_amplitude"])
        humidity = _diurnal(hour, HUMIDITY_MONSOON["mean"],
                           -HUMIDITY_MONSOON["diurnal_amplitude"],
                           peak_hour=14.0)

        # Light intermittent rain — more likely late afternoon
        rain_prob = 0.12 + 0.08 * math.sin((hour - 16) * math.pi / 12)
        if random.random() < rain_prob:
            rainfall = random.uniform(0.5, 3.0)
        else:
            rainfall = random.uniform(0.0, 0.3)

        # Water level: gentle random walk around 310 cm
        self._water_level += random.gauss(0, 0.4)
        self._water_level = _clamp(self._water_level, 260, 370)

        # Soil moisture: gentle drift, slight bump when raining
        self._soil_moisture += random.gauss(0, 0.2)
        if rainfall > 1.0:
            self._soil_moisture += 0.15
        self._soil_moisture = _clamp(self._soil_moisture, 30, 58)

        # Vibration: calm baseline
        vibration = abs(random.gauss(self._vibration_base, 0.008))

        return {
            "waterLevel":   _add_noise(self._water_level, "waterLevel", 20, 400),
            "rainfall":     _add_noise(rainfall, "rainfall", 0, 100),
            "temp":         _add_noise(temp, "temp", 10, 50),
            "humidity":     _add_noise(humidity, "humidity", 20, 100),
            "soilMoisture": _add_noise(self._soil_moisture, "soilMoisture", 0, 100),
            "vibration":    _add_noise(vibration, "vibration", 0, 5),
        }

    # ── flood build-up scenario ─────────────────────────────────────────

    def _flood_event(self, ts, elapsed_min, total_min):
        """
        12-hour progressive flood event:
          Phase 1  (0-120 min)  : Rain intensifies from light → heavy
          Phase 2  (120-300 min): Very heavy rain; water level starts falling
                                  (= rising water); soil saturates
          Phase 3  (300-480 min): Peak — water in danger zone, rain eases
          Phase 4  (480-720 min): Slow recession, rain stops
        """
        hour = _hour_of(ts)

        temp = _diurnal(hour, TEMP_MONSOON["mean"] - 2,      # slightly cooler during storm
                        TEMP_MONSOON["diurnal_amplitude"] * 0.5)

        # ── rainfall envelope ──
        if elapsed_min < 120:
            rainfall = _smooth(elapsed_min, 120, 1.5, 22.0)
        elif elapsed_min < 300:
            rainfall = _smooth(elapsed_min - 120, 180, 22.0, 45.0)
            # occasional burst
            if random.random() < 0.08:
                rainfall += random.uniform(10, 25)
        elif elapsed_min < 480:
            rainfall = _smooth(elapsed_min - 300, 180, 45.0, 8.0)
        else:
            rainfall = _smooth(elapsed_min - 480, 240, 8.0, 0.5)

        # ── humidity: spikes with heavy rain ──
        humidity = min(99, 78 + 0.04 * rainfall + random.gauss(0, 1.5))

        # ── water level: drops (water rises) with ~90-min lag after rain ──
        rain_lag_min = max(0, elapsed_min - 90)
        if rain_lag_min < 60:
            self._water_level = _smooth(rain_lag_min, 60, 310, 280)
        elif rain_lag_min < 210:
            self._water_level = _smooth(rain_lag_min - 60, 150, 280, 120)
        elif rain_lag_min < 390:
            self._water_level = _smooth(rain_lag_min - 210, 180, 120, 55)
        elif rain_lag_min < 560:
            # peak danger zone — holds low
            self._water_level = 55 + random.gauss(0, 3)
        else:
            self._water_level = _smooth(rain_lag_min - 560, 200, 55, 200)

        # ── soil moisture: saturates progressively ──
        if elapsed_min < 180:
            self._soil_moisture = _smooth(elapsed_min, 180, 42, 68)
        elif elapsed_min < 420:
            self._soil_moisture = _smooth(elapsed_min - 180, 240, 68, 94)
        else:
            self._soil_moisture = _smooth(elapsed_min - 420, 300, 94, 70)

        # ── vibration: increases during heavy flow ──
        vib_mult = 1.0
        if self._water_level < 120:
            vib_mult = 2.5
        elif self._water_level < 200:
            vib_mult = 1.6
        vibration = abs(random.gauss(self._vibration_base * vib_mult, 0.015))

        return {
            "waterLevel":   _add_noise(self._water_level, "waterLevel", 20, 400),
            "rainfall":     _add_noise(rainfall, "rainfall", 0, 120),
            "temp":         _add_noise(temp, "temp", 10, 50),
            "humidity":     _add_noise(humidity, "humidity", 20, 100),
            "soilMoisture": _add_noise(self._soil_moisture, "soilMoisture", 0, 100),
            "vibration":    _add_noise(vibration, "vibration", 0, 5),
        }

    # ── flash flood (rapid onset) ───────────────────────────────────────

    def _flash_flood(self, ts, elapsed_min, total_min):
        """
        4-hour flash flood:
          0-30 min  : Sudden cloudburst, 40-70 mm/hr
          30-120 min: Water level plummets to danger in ~90 min
          120-180   : Rain eases, water at peak
          180-240   : Rapid partial recession
        """
        hour = _hour_of(ts)
        temp = _diurnal(hour, TEMP_MONSOON["mean"] - 3, 2.0)

        if elapsed_min < 30:
            rainfall = _smooth(elapsed_min, 30, 2.0, 60.0)
        elif elapsed_min < 120:
            rainfall = 55 + random.uniform(-8, 12)
        elif elapsed_min < 180:
            rainfall = _smooth(elapsed_min - 120, 60, 55.0, 5.0)
        else:
            rainfall = _smooth(elapsed_min - 180, 60, 5.0, 0.5)

        humidity = min(99, 85 + 0.03 * rainfall + random.gauss(0, 1.0))

        rain_lag = max(0, elapsed_min - 25)
        if rain_lag < 90:
            self._water_level = _smooth(rain_lag, 90, 310, 50)
        elif rain_lag < 160:
            self._water_level = 50 + random.gauss(0, 4)
        else:
            self._water_level = _smooth(rain_lag - 160, 80, 50, 180)

        if elapsed_min < 60:
            self._soil_moisture = _smooth(elapsed_min, 60, 42, 75)
        elif elapsed_min < 150:
            self._soil_moisture = _smooth(elapsed_min - 60, 90, 75, 95)
        else:
            self._soil_moisture = _smooth(elapsed_min - 150, 90, 95, 65)

        vibration = abs(random.gauss(0.04 if self._water_level > 150 else 0.12,
                                     0.02))
        return {
            "waterLevel":   _add_noise(self._water_level, "waterLevel", 20, 400),
            "rainfall":     _add_noise(rainfall, "rainfall", 0, 120),
            "temp":         _add_noise(temp, "temp", 10, 50),
            "humidity":     _add_noise(humidity, "humidity", 20, 100),
            "soilMoisture": _add_noise(self._soil_moisture, "soilMoisture", 0, 100),
            "vibration":    _add_noise(vibration, "vibration", 0, 5),
        }

    # ── public entry point ──────────────────────────────────────────────

    def generate(self, scenario, start_time, duration_hours, interval_sec):
        self._reset()
        total_min = duration_hours * 60
        readings = []
        for ts, elapsed in _generate_timestamps(start_time, duration_hours,
                                                 interval_sec):
            if scenario == "normal":
                values = self._baseline(ts)
            elif scenario == "flood":
                values = self._flood_event(ts, elapsed, total_min)
            elif scenario == "flash_flood":
                values = self._flash_flood(ts, elapsed, total_min)
            elif scenario == "compound":
                values = self._flood_event(ts, elapsed, total_min)
            else:
                values = self._baseline(ts)

            readings.append({
                "nodeId": self.node_id,
                "timestamp": _iso(ts),
                **values,
            })
        return readings


# ────────────────────────────────────────────────────────────────────────────
# AIR-QUALITY NODE GENERATOR
# ────────────────────────────────────────────────────────────────────────────

class AirQualityNodeGenerator:
    """Generates readings for airq-node-01 (MQ-135, MQ-2, DHT22)."""

    def __init__(self, node_id="airq-node-01"):
        self.node_id = node_id
        self.node = NODES[node_id]
        self._pm25 = 48.0
        self._gas = 95.0
        self._smoke = 55.0

    def _reset(self):
        self._pm25 = 48.0
        self._gas = 95.0
        self._smoke = 55.0

    # ── baseline (normal monsoon day) ───────────────────────────────────

    def _baseline(self, ts):
        hour = _hour_of(ts)

        temp = _diurnal(hour, TEMP_MONSOON["mean"],
                        TEMP_MONSOON["diurnal_amplitude"])
        humidity = _diurnal(hour, HUMIDITY_MONSOON["mean"],
                           -HUMIDITY_MONSOON["diurnal_amplitude"],
                           peak_hour=14.0)

        # PM2.5: Guwahati typical 35-65, peaks morning & evening (traffic)
        traffic_factor = 1.0 + 0.3 * (
            math.exp(-0.5 * ((hour - 8.5) / 1.5) ** 2) +
            math.exp(-0.5 * ((hour - 19) / 1.5) ** 2)
        )
        self._pm25 += random.gauss(0, 1.2)
        self._pm25 = _clamp(self._pm25, 30, 70)
        pm25 = self._pm25 * traffic_factor

        # Gas: low baseline, gentle drift
        self._gas += random.gauss(0, 2.0)
        self._gas = _clamp(self._gas, 60, 140)

        # Smoke: very low baseline
        self._smoke += random.gauss(0, 1.5)
        self._smoke = _clamp(self._smoke, 30, 100)

        return {
            "pm25":     _add_noise(pm25, "pm25", 0, 500),
            "gas":      _add_noise(self._gas, "gas", 0, 1000),
            "smoke":    _add_noise(self._smoke, "smoke", 0, 1000),
            "temp":     _add_noise(temp, "temp", 10, 50),
            "humidity": _add_noise(humidity, "humidity", 20, 100),
        }

    # ── fire / smoke event ──────────────────────────────────────────────

    def _fire_event(self, ts, elapsed_min, total_min):
        """
        6-hour fire/smoke event:
          Phase 1 (0-20 min)   : SHARP spike in MQ-2 smoke — this is the
                                  "sharpness of spike" signal (Section 10)
          Phase 2 (20-60 min)  : MQ-135 gas and PM2.5 catch up
          Phase 3 (60-180 min) : Sustained high readings (active fire)
          Phase 4 (180-360 min): Gradual decay as fire is contained
        """
        hour = _hour_of(ts)
        temp_base = _diurnal(hour, TEMP_MONSOON["mean"],
                             TEMP_MONSOON["diurnal_amplitude"])

        # ── smoke: SHARP rise (key differentiator from pollution drift) ──
        if elapsed_min < 8:
            self._smoke = _smooth(elapsed_min, 8, 60, 180)
        elif elapsed_min < 20:
            self._smoke = _smooth(elapsed_min - 8, 12, 180, 680)
        elif elapsed_min < 180:
            # sustained with fluctuation
            self._smoke = 650 + random.uniform(-60, 80)
        else:
            self._smoke = _smooth(elapsed_min - 180, 180, 650, 90)

        # ── gas: follows smoke with slight delay ──
        if elapsed_min < 15:
            self._gas = _smooth(elapsed_min, 15, 95, 140)
        elif elapsed_min < 40:
            self._gas = _smooth(elapsed_min - 15, 25, 140, 480)
        elif elapsed_min < 180:
            self._gas = 460 + random.uniform(-40, 50)
        else:
            self._gas = _smooth(elapsed_min - 180, 180, 460, 110)

        # ── PM2.5: rises with smoke, peaks slightly after ──
        if elapsed_min < 25:
            self._pm25 = _smooth(elapsed_min, 25, 50, 90)
        elif elapsed_min < 60:
            self._pm25 = _smooth(elapsed_min - 25, 35, 90, 320)
        elif elapsed_min < 180:
            self._pm25 = 300 + random.uniform(-30, 45)
        else:
            self._pm25 = _smooth(elapsed_min - 180, 180, 300, 65)

        # Temperature slightly elevated near fire source
        temp_boost = 0
        if 20 < elapsed_min < 200:
            temp_boost = _smooth(min(elapsed_min, 60), 60, 0, 4.5) \
                         if elapsed_min < 60 else \
                         _smooth(elapsed_min - 60, 140, 4.5, 0)
        temp = temp_base + temp_boost

        humidity = _diurnal(hour, HUMIDITY_MONSOON["mean"] - 5,
                           -HUMIDITY_MONSOON["diurnal_amplitude"],
                           peak_hour=14.0)

        return {
            "pm25":     _add_noise(self._pm25, "pm25", 0, 500),
            "gas":      _add_noise(self._gas, "gas", 0, 1000),
            "smoke":    _add_noise(self._smoke, "smoke", 0, 1000),
            "temp":     _add_noise(temp, "temp", 10, 55),
            "humidity": _add_noise(humidity, "humidity", 15, 100),
        }

    # ── pollution drift (gradual — NOT fire) ────────────────────────────

    def _pollution_drift(self, ts, elapsed_min, total_min):
        """
        8-hour gradual AQI deterioration — no sharp spikes, slow climb.
        This is the CONTRAST case: fusion logic should NOT flag this as fire.
          Phase 1 (0-180 min) : Slow PM2.5 rise from satisfactory → poor
          Phase 2 (180-360 min): Peaks at "very poor" (150-200 μg/m³)
          Phase 3 (360-480 min): Gradual improvement
        """
        hour = _hour_of(ts)
        temp = _diurnal(hour, TEMP_MONSOON["mean"],
                        TEMP_MONSOON["diurnal_amplitude"])
        humidity = _diurnal(hour, HUMIDITY_MONSOON["mean"],
                           -HUMIDITY_MONSOON["diurnal_amplitude"],
                           peak_hour=14.0)

        # PM2.5: slow gradual rise and fall
        if elapsed_min < 180:
            self._pm25 = _smooth(elapsed_min, 180, 50, 140)
        elif elapsed_min < 360:
            self._pm25 = _smooth(elapsed_min - 180, 180, 140, 190)
        else:
            self._pm25 = _smooth(elapsed_min - 360, 120, 190, 60)
        self._pm25 += random.gauss(0, 2.5)   # very gentle noise

        # Gas: mild rise, nothing sharp
        if elapsed_min < 240:
            self._gas = _smooth(elapsed_min, 240, 95, 180)
        else:
            self._gas = _smooth(elapsed_min - 240, 240, 180, 100)

        # Smoke: stays LOW — this is not a fire
        self._smoke = 65 + random.gauss(0, 5)

        return {
            "pm25":     _add_noise(self._pm25, "pm25", 0, 500),
            "gas":      _add_noise(self._gas, "gas", 0, 1000),
            "smoke":    _add_noise(self._smoke, "smoke", 0, 1000),
            "temp":     _add_noise(temp, "temp", 10, 50),
            "humidity": _add_noise(humidity, "humidity", 20, 100),
        }

    # ── public entry point ──────────────────────────────────────────────

    def generate(self, scenario, start_time, duration_hours, interval_sec):
        self._reset()
        total_min = duration_hours * 60
        readings = []
        for ts, elapsed in _generate_timestamps(start_time, duration_hours,
                                                 interval_sec):
            if scenario == "normal":
                values = self._baseline(ts)
            elif scenario == "fire":
                values = self._fire_event(ts, elapsed, total_min)
            elif scenario == "pollution_drift":
                values = self._pollution_drift(ts, elapsed, total_min)
            elif scenario == "compound":
                # Fire event starts 30 min into the compound scenario
                fire_elapsed = max(0, elapsed - 30)
                values = self._fire_event(ts, fire_elapsed, total_min)
            else:
                values = self._baseline(ts)

            readings.append({
                "nodeId": self.node_id,
                "timestamp": _iso(ts),
                **values,
            })
        return readings


# ────────────────────────────────────────────────────────────────────────────
# ANOMALY & ALERT GENERATORS  (for dashboard / verification-loop testing)
# ────────────────────────────────────────────────────────────────────────────

def generate_sample_anomalies(readings_by_node, thresholds=THRESHOLDS):
    """
    Scan generated readings and produce anomaly documents whenever sensor
    values cross the configured thresholds.  This is a SIMPLIFIED version
    of the real fusion logic — just enough to populate /anomalies for
    dashboard and verification-loop testing.
    """
    anomalies = []

    for node_id, readings in readings_by_node.items():
        node_type = NODES[node_id]["type"]

        for i, r in enumerate(readings):
            anomaly = None

            # ── flood detection (simplified) ──
            if node_type == "flood":
                wl = r.get("waterLevel")
                rain = r.get("rainfall", 0)
                soil = r.get("soilMoisture", 0)

                # Rate-of-rise (look back 5 readings ≈ 2.5 min at 30s interval)
                rise_rate = 0
                if i >= 5:
                    prev_wl = readings[i - 5].get("waterLevel", wl)
                    rise_rate = (prev_wl - wl) / 2.5  # cm/min (falling distance = rising water)

                if wl is not None and wl < thresholds["flood"]["water_level_danger"]:
                    raw_conf = min(98, 60 + rise_rate * 3 + (rain / 2) + max(0, soil - 60))
                    anomaly = _make_anomaly(node_id, "flood", raw_conf, r["timestamp"])
                elif wl is not None and wl < thresholds["flood"]["water_level_warning"]:
                    raw_conf = min(80, 30 + rise_rate * 2 + (rain / 3))
                    anomaly = _make_anomaly(node_id, "flood", raw_conf, r["timestamp"])

            # ── fire detection (simplified) ──
            if node_type == "air_quality":
                smoke = r.get("smoke", 0)
                gas = r.get("gas", 0)
                pm25 = r.get("pm25", 0)

                # Rate-of-change for sharpness detection
                smoke_roc = 0
                if i >= 2:
                    prev_smoke = readings[i - 2].get("smoke", smoke)
                    smoke_roc = (smoke - prev_smoke)  # ppm per reading

                if smoke > thresholds["fire"]["smoke_spike"] and smoke_roc > 15:
                    raw_conf = min(97, 50 + smoke_roc * 0.5 + (gas / 10))
                    anomaly = _make_anomaly(node_id, "fire", raw_conf, r["timestamp"])
                elif pm25 > thresholds["air_quality"]["pm25_severe"]:
                    raw_conf = min(85, 35 + (pm25 - 200) / 5)
                    anomaly = _make_anomaly(node_id, "air_quality", raw_conf, r["timestamp"])

            if anomaly:
                anomalies.append(anomaly)

    # De-duplicate: keep at most one anomaly per 5-minute window per node
    return _dedupe_anomalies(anomalies, window_minutes=5)


def _make_anomaly(node_id, hazard_type, raw_confidence, timestamp):
    return {
        "anomalyId": f"anomaly-{uuid.uuid4().hex[:12]}",
        "nodeId": node_id,
        "type": hazard_type,
        "rawConfidence": round(_clamp(raw_confidence, 0, 100), 1),
        "verifiedConfidence": round(_clamp(raw_confidence, 0, 100), 1),
        "status": "pending",
        "timestamp": timestamp,
    }


def _dedupe_anomalies(anomalies, window_minutes=5):
    """Keep only the highest-confidence anomaly per node per time window."""
    if not anomalies:
        return []
    deduped = []
    last_by_node = {}
    for a in sorted(anomalies, key=lambda x: x["timestamp"]):
        key = (a["nodeId"], a["type"])
        if key in last_by_node:
            last_ts = datetime.strptime(last_by_node[key]["timestamp"],
                                        "%Y-%m-%dT%H:%M:%S.000Z")
            curr_ts = datetime.strptime(a["timestamp"],
                                        "%Y-%m-%dT%H:%M:%S.000Z")
            if (curr_ts - last_ts).total_seconds() < window_minutes * 60:
                # Within window — keep higher confidence
                if a["rawConfidence"] > last_by_node[key]["rawConfidence"]:
                    deduped[-1] = a
                    last_by_node[key] = a
                continue
        deduped.append(a)
        last_by_node[key] = a
    return deduped


# ────────────────────────────────────────────────────────────────────────────
# SAMPLE ALERT + SACHET PAYLOAD
# ────────────────────────────────────────────────────────────────────────────

def generate_sample_alerts(anomalies, nodes=NODES):
    """
    Promote high-confidence anomalies to alerts with SACHET-style payloads.
    Simulates the verification loop having already run.
    """
    alerts = []
    for a in anomalies:
        if a["rawConfidence"] < 55:
            continue

        node = nodes[a["nodeId"]]

        # Simulate community verification adjusting confidence
        yes_votes = random.randint(2, 5)
        no_votes = random.randint(0, 1)
        verified_conf = min(100, a["rawConfidence"] + (yes_votes - no_votes) * 4)

        severity = "advisory"
        if verified_conf > 85:
            severity = "danger"
        elif verified_conf > 70:
            severity = "warning"
        elif verified_conf > 55:
            severity = "watch"

        sachet = copy.deepcopy(SACHET_PAYLOAD_TEMPLATE)
        sachet.update({
            "sourceNodeId": a["nodeId"],
            "hazardType": a["type"],
            "severity": severity,
            "confidence": round(verified_conf, 1),
            "verificationStatus": "verified",
            "timestamp": a["timestamp"],
            "message": f"{a['type'].upper()} {severity.upper()} - "
                       f"Confidence {verified_conf:.0f}% - "
                       f"Community-verified ({yes_votes}Y/{no_votes}N)",
        })
        sachet["location"].update({
            "lat": node["lat"],
            "lng": node["lng"],
            "description": node["name"],
        })

        alerts.append({
            "alertId": f"alert-{uuid.uuid4().hex[:12]}",
            "anomalyId": a["anomalyId"],
            "hazardType": a["type"],
            "confidenceScore": round(verified_conf, 1),
            "message": sachet["message"],
            "channelsSent": ["sms", "dashboard", "push"],
            "sachetPayload": sachet,
            "timestamp": a["timestamp"],
        })

    return alerts


# ────────────────────────────────────────────────────────────────────────────
# SAMPLE VERIFICATION RESPONSES
# ────────────────────────────────────────────────────────────────────────────

def generate_sample_verifications(anomalies, test_phones=None):
    """Generate simulated SMS verification responses for anomalies."""
    if test_phones is None:
        test_phones = ["+919876543210", "+919876543211", "+919876543212"]

    verifications = {}
    for a in anomalies:
        if a["rawConfidence"] < 40:
            continue
        responses = {}
        for phone in test_phones:
            # Higher-confidence anomalies more likely to get YES responses
            yes_prob = min(0.95, 0.4 + a["rawConfidence"] / 200)
            ts = datetime.strptime(a["timestamp"], "%Y-%m-%dT%H:%M:%S.000Z")
            reply_delay = timedelta(seconds=random.randint(30, 300))
            responses[phone.replace("+", "")] = {
                "response": "YES" if random.random() < yes_prob else "NO",
                "timestamp": _iso(ts + reply_delay),
            }
        verifications[a["anomalyId"]] = responses
    return verifications


# ────────────────────────────────────────────────────────────────────────────
# NODE REGISTRATION DOCUMENTS
# ────────────────────────────────────────────────────────────────────────────

def generate_node_docs(start_time):
    """Generate /nodes/{nodeId} Firestore documents."""
    docs = {}
    for nid, n in NODES.items():
        docs[nid] = {
            **n,
            "lastSeen": _iso(start_time),
        }
    return docs
