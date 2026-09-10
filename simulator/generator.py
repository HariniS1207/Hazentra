"""
Hazentra Synthetic Data Generator — Single-Node Multi-Hazard Engine (Hardened)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Simulates telemetry for the single integrated ESP32 node across 7 scenarios:
  1. normal        (24h baseline — all sensors nominal)
  2. earthquake    (1h — sudden vector accel spike >4.0 m/s^2, debounce-verified)
  3. fire          (4h — gasRaw spike >=150 AND temp rising >0.3C — fusion!)
  4. flood         (8h — distance falling <=10cm AND soilMoisture rising — fusion!)
  5. gas_leak      (3h — gasRaw spike >=150 AND temp flat/falling — zero dead zone!)
  6. landslide     (6h — soilMoisture >=70% AND micro-tremor 3.65-4.0 m/s^2)
  7. compound      (6h — flood + fire/gas occurring within 90s window)

Schema:
  /readings/{timestamp}
    - accel: number (m/s^2)
    - temp: number (deg C)
    - distance: number (cm)
    - gasRaw: number (0-4095 ADC)
    - soilMoisture: number (%)
    - cycle: integer (sequence count)
    - timestamp: ISO 8601 UTC string
"""

import math
import random
import uuid
import copy
from datetime import datetime, timezone, timedelta

from config import (
    NODE_INFO, BASELINES, FUSION_RULES,
    SACHET_PAYLOAD_TEMPLATE, VERIFICATION_SETTINGS
)

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _smooth(t, duration, start, end):
    if duration <= 0:
        return end
    p = _clamp(t / duration, 0.0, 1.0)
    s = p * p * (3 - 2 * p)
    return start + (end - start) * s

def _iso(ts):
    # Ensure timezone-aware UTC representation
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class SingleNodeTelemetryGenerator:
    """Generates continuous telemetry for the single integrated Hazentra node."""

    def __init__(self):
        self.node_id = NODE_INFO["nodeId"]
        self.cycle_counter = 186  # match start cycle from real hardware screenshot

    def _add_noise(self, val, sensor):
        sigma = BASELINES[sensor]["noise_sigma"]
        return round(val + random.gauss(0, sigma), 2)

    def generate_single_reading(self, scenario, elapsed_sec, ts, cycle_num=None):
        """Generates a single reading at a specific elapsed time offset."""
        if cycle_num is None:
            cycle_num = self.cycle_counter
            self.cycle_counter += 1

        elapsed_min = elapsed_sec / 60.0
        hour_of_day = ts.hour + ts.minute / 60.0 + ts.second / 3600.0

        # Base diurnal temperature curve
        amp = BASELINES["temp"]["diurnal_amp"]
        temp_diurnal = BASELINES["temp"]["mean"] + amp * math.sin((hour_of_day - 14) * math.pi / 12)

        accel = BASELINES["accel"]["mean"]
        temp = temp_diurnal
        dist = BASELINES["distance"]["mean"]
        gas = BASELINES["gasRaw"]["mean"]
        soil = BASELINES["soilMoisture"]["mean"]

        # Scenario physics
        if scenario == "normal":
            pass

        elif scenario == "earthquake":
            if 15.0 <= elapsed_min < 15.75:
                accel = random.uniform(4.3, 5.8)  # Sharp seismic event
            elif 15.75 <= elapsed_min < 22.0:
                if random.random() < 0.25:
                    accel = random.uniform(4.05, 4.45)
                else:
                    accel = 3.65 + random.uniform(-0.08, 0.08)

        elif scenario == "fire":
            if elapsed_min < 20:
                pass
            elif elapsed_min < 50:
                gas = _smooth(elapsed_min - 20, 30, 155, 380)
                temp = _smooth(elapsed_min - 20, 30, temp_diurnal, 41.5)
            elif elapsed_min < 140:
                gas = 380 + random.uniform(-25, 40)
                temp = 41.5 + random.uniform(-0.5, 1.2)
            else:
                gas = _smooth(elapsed_min - 140, 60, 380, 160)
                temp = _smooth(elapsed_min - 140, 60, 41.5, temp_diurnal)

        elif scenario == "flood":
            if elapsed_min < 30:
                pass
            elif elapsed_min < 240:
                dist = _smooth(elapsed_min - 30, 210, 135, 7.5)
                soil = _smooth(elapsed_min - 30, 210, 42, 89)
            elif elapsed_min < 380:
                dist = 7.5 + random.uniform(-1.0, 1.0)
                soil = 89 + random.uniform(-2.0, 3.0)
            else:
                dist = _smooth(elapsed_min - 380, 100, 7.5, 95)
                soil = _smooth(elapsed_min - 380, 100, 89, 65)

        elif scenario == "gas_leak":
            if elapsed_min < 15:
                pass
            elif elapsed_min < 45:
                gas = _smooth(elapsed_min - 15, 30, 155, 420)
                temp = temp_diurnal - 0.4
            elif elapsed_min < 120:
                gas = 420 + random.uniform(-30, 30)
                temp = temp_diurnal - 0.3
            else:
                gas = _smooth(elapsed_min - 120, 45, 420, 155)

        elif scenario == "landslide":
            if elapsed_min < 30:
                pass
            elif elapsed_min < 180:
                soil = _smooth(elapsed_min - 30, 150, 42, 82)
                accel = _smooth(elapsed_min - 30, 150, 3.50, 3.82)
            elif elapsed_min < 300:
                soil = 82 + random.uniform(-1.5, 2.5)
                accel = 3.82 + random.uniform(-0.06, 0.08)
            else:
                soil = _smooth(elapsed_min - 300, 60, 82, 60)
                accel = _smooth(elapsed_min - 300, 60, 3.82, 3.50)

        elif scenario == "compound":
            if elapsed_min >= 20:
                dist = _smooth(elapsed_min - 20, 160, 135, 8.0)
                soil = _smooth(elapsed_min - 20, 160, 42, 85)
            if elapsed_min >= 60:
                gas = _smooth(elapsed_min - 60, 40, 155, 360)
                temp = _smooth(elapsed_min - 60, 40, temp_diurnal, 39.5)

        final_accel = self._add_noise(accel, "accel")
        final_temp = self._add_noise(temp, "temp")
        final_dist = max(2.0, self._add_noise(dist, "distance"))
        final_gas = int(_clamp(self._add_noise(gas, "gasRaw"), 0, 4095))
        final_soil = _clamp(self._add_noise(soil, "soilMoisture"), 0, 100)

        return {
            "cycle": cycle_num,
            "timestamp": _iso(ts),
            "accel": round(final_accel, 2),
            "temp": round(final_temp, 1),
            "distance": round(final_dist, 1),
            "gasRaw": final_gas,
            "soilMoisture": round(final_soil, 1),
        }

    def generate(self, scenario, start_time, duration_hours, interval_sec=5):
        total_steps = int(duration_hours * 3600 / interval_sec)
        readings = []

        for step in range(total_steps):
            elapsed_sec = step * interval_sec
            ts = start_time + timedelta(seconds=elapsed_sec)
            r = self.generate_single_reading(scenario, elapsed_sec, ts)
            readings.append(r)

        return readings


# ============================================================================
# CLOUD FUSION SIMULATOR (Matches Cloud Functions)
# ============================================================================

def evaluate_fusion_rules(readings, window_size=10):
    """
    Evaluates rolling-window fusion rules with 90s compound window
    and consecutive-read debounce.
    """
    anomalies = []
    debounce_accel = 0

    for i in range(len(readings)):
        if i < 2:
            continue

        window = readings[max(0, i - window_size + 1):i + 1]
        current = readings[i]
        prev = readings[i - 1]
        oldest = window[0]

        temp_trend = (current["temp"] - oldest["temp"])
        soil_trend = (current["soilMoisture"] - oldest["soilMoisture"])
        accel_trend = (current["accel"] - oldest["accel"])
        gas_trend = (current["gasRaw"] - oldest["gasRaw"])

        detected_hazards = []

        # 1. Earthquake: Standalone, accel > 4.0 m/s^2, 2 consecutive reads
        if current["accel"] > FUSION_RULES["earthquake"]["accel_threshold"]:
            debounce_accel += 1
            if debounce_accel >= FUSION_RULES["earthquake"]["debounce_reads"]:
                conf = min(98.0, 70.0 + (current["accel"] - 4.0) * 20.0)
                detected_hazards.append({
                    "type": "earthquake",
                    "confidence": round(conf, 1),
                    "reason": f"Seismic acceleration {current['accel']} m/s^2 exceeded threshold 4.0 m/s^2 across 2 reads",
                })
        else:
            debounce_accel = 0

        # 2 & 4. Fire vs Gas Leak (Spec: Gas >= 150 + spike above ambient)
        is_gas_anomalous = (current["gasRaw"] >= FUSION_RULES["fire"]["gas_threshold"]) and \
                           (gas_trend >= FUSION_RULES["fire"]["gas_spike_delta"] or current["gasRaw"] >= 180)

        if is_gas_anomalous:
            if temp_trend > FUSION_RULES["fire"]["temp_rising_threshold"]:
                # Fire: Gas spike + thermal rise
                conf = min(96.0, 60.0 + (current["gasRaw"] - 150) / 8.0 + temp_trend * 15.0)
                detected_hazards.append({
                    "type": "fire",
                    "confidence": round(conf, 1),
                    "reason": f"Gas spike ({current['gasRaw']}) correlated with thermal rise (+{temp_trend:.1f}C)",
                })
            else:
                # Gas Leak: Gas spike without thermal rise (No dead zone!)
                conf = min(92.0, 55.0 + (current["gasRaw"] - 150) / 10.0)
                detected_hazards.append({
                    "type": "gas_leak",
                    "confidence": round(conf, 1),
                    "reason": f"Isolated gas spike ({current['gasRaw']}) with stable ambient temp ({current['temp']} C)",
                })

        # 3. Flood: Distance <= 10cm across 2 consecutive reads AND soil moisture saturated/rising
        if current["distance"] <= FUSION_RULES["flood"]["distance_threshold"] and \
           prev["distance"] <= FUSION_RULES["flood"]["distance_threshold"]:
            if soil_trend > FUSION_RULES["flood"]["soil_rising_threshold"] or current["soilMoisture"] >= 70.0:
                conf = min(99.0, 65.0 + (10.0 - current["distance"]) * 5.0 + (current["soilMoisture"] - 70) * 0.5)
                detected_hazards.append({
                    "type": "flood",
                    "confidence": round(conf, 1),
                    "reason": f"Water distance critical ({current['distance']} cm across 2 reads) with ground saturation ({current['soilMoisture']}%)",
                })

        # 5. Landslide: Soil >= 70% AND micro-tremor 3.65 - 4.0 m/s^2
        if current["soilMoisture"] >= FUSION_RULES["landslide"]["soil_threshold"]:
            if FUSION_RULES["landslide"]["accel_min"] <= current["accel"] < FUSION_RULES["landslide"]["accel_max"] and \
               accel_trend > FUSION_RULES["landslide"]["accel_trend_min"]:
                conf = min(88.0, 50.0 + (current["soilMoisture"] - 70) * 1.0 + (current["accel"] - 3.5) * 50)
                detected_hazards.append({
                    "type": "landslide",
                    "confidence": round(conf, 1),
                    "reason": f"Soil saturation critical ({current['soilMoisture']}%) with slope micro-tremors ({current['accel']} m/s^2)",
                })

        if not detected_hazards:
            continue

        # Check 90s rolling window for multi-hazard compound events
        curr_dt = datetime.fromisoformat(current["timestamp"].replace("Z", "+00:00"))
        past_90s_hazards = [
            a for a in anomalies
            if (curr_dt - datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00"))).total_seconds() <= 90
        ]

        distinct_types = set([h["type"] for h in detected_hazards])
        for pa in past_90s_hazards:
            if pa["type"] != "compound":
                distinct_types.add(pa["type"])

        if len(distinct_types) >= 2:
            hazard_names = " + ".join(t.upper() for t in distinct_types)
            compound_conf = min(99.0, max(h["confidence"] for h in detected_hazards) + 12.0)
            anomalies.append({
                "anomalyId": f"anomaly-{uuid.uuid4().hex[:10]}",
                "type": "compound",
                "subHazards": list(distinct_types),
                "rawConfidence": round(compound_conf, 1),
                "verifiedConfidence": round(compound_conf, 1),
                "status": "pending",
                "timestamp": current["timestamp"],
                "reason": f"Cross-hazard correlation (90s window): {hazard_names}",
                "snapshot": current,
            })
        else:
            h = detected_hazards[0]
            anomalies.append({
                "anomalyId": f"anomaly-{uuid.uuid4().hex[:10]}",
                "type": h["type"],
                "rawConfidence": h["confidence"],
                "verifiedConfidence": h["confidence"],
                "status": "pending",
                "timestamp": current["timestamp"],
                "reason": h["reason"],
                "snapshot": current,
            })

    return _dedupe_anomalies(anomalies, window_sec=180)


def _dedupe_anomalies(anomalies, window_sec=180):
    """
    Fixed deduplication: tracks the exact index per hazard type,
    ensuring updates replace the correct entry and do not overwrite other hazards.
    """
    if not anomalies:
        return []
    deduped = []
    last_seen = {}  # htype -> (index_in_deduped, timestamp, confidence)

    for a in sorted(anomalies, key=lambda x: x["timestamp"]):
        htype = a["type"]
        ts = datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00"))

        if htype in last_seen:
            idx, last_ts, last_conf = last_seen[htype]
            if (ts - last_ts).total_seconds() < window_sec:
                if a["rawConfidence"] > last_conf:
                    deduped[idx] = a
                    last_seen[htype] = (idx, ts, a["rawConfidence"])
                continue

        deduped.append(a)
        last_seen[htype] = (len(deduped) - 1, ts, a["rawConfidence"])

    return deduped


# ============================================================================
# ALERT & SACHET PAYLOAD BUILDER
# ============================================================================

def generate_alerts_and_verifications(anomalies):
    """Generates verification responses and escalated alerts with SACHET payloads."""
    alerts = []
    verifications = {}

    for a in anomalies:
        aid = a["anomalyId"]
        htype = a["type"]
        raw_conf = a["rawConfidence"]

        responses = {}
        yes_count = 0
        no_count = 0

        for phone in VERIFICATION_SETTINGS["test_numbers"]:
            yes_prob = min(0.95, 0.45 + raw_conf / 180.0)
            is_yes = random.random() < yes_prob
            if is_yes:
                yes_count += 1
            else:
                no_count += 1

            t_reply = datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00")) + timedelta(seconds=random.randint(15, 90))
            responses[phone.replace("+", "")] = {
                "response": "YES" if is_yes else "NO",
                "timestamp": _iso(t_reply),
            }

        verifications[aid] = responses

        verified_conf = _clamp(
            raw_conf + (yes_count * VERIFICATION_SETTINGS["yes_weight"]) + (no_count * VERIFICATION_SETTINGS["no_weight"]),
            0.0, 100.0
        )
        a["verifiedConfidence"] = round(verified_conf, 1)

        if verified_conf >= VERIFICATION_SETTINGS["escalation_threshold"]:
            a["status"] = "escalated"
            severity = "warning"
            if verified_conf > 85.0:
                severity = "danger"
            elif verified_conf < 70.0:
                severity = "watch"

            sachet = copy.deepcopy(SACHET_PAYLOAD_TEMPLATE)
            sachet.update({
                "hazardType": htype,
                "severity": severity,
                "confidence": round(verified_conf, 1),
                "verificationStatus": "verified",
                "timestamp": a["timestamp"],
                "sensorData": a.get("snapshot", {}),
                "message": f"HAZENTRA {htype.upper()} {severity.upper()} - Confidence {verified_conf:.0f}% - Community Verified ({yes_count}Y/{no_count}N)",
            })

            alerts.append({
                "alertId": f"alert-{uuid.uuid4().hex[:10]}",
                "anomalyId": aid,
                "hazardType": htype,
                "confidenceScore": round(verified_conf, 1),
                "message": sachet["message"],
                "channelsSent": ["sms_fast2sms", "dashboard_live"],
                "sachetPayload": sachet,
                "timestamp": a["timestamp"],
            })
        else:
            a["status"] = "denied" if no_count > yes_count else "pending"

    return alerts, verifications
