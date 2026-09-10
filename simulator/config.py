"""
Hazentra Simulator — Configuration & Constants (Single-Node Architecture)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Calibrated against real ESP32 telemetry (Cycle #186-196):
  Accel: 3.5 m/s^2 | Temp: 33.9 C | Gas: 147-161 | Dist: 134.5-135.3 cm | Soil: 100% (bench test)

Schema strictly follows CLAUDE.md Section 9 & Hazentra_Implementation_Plan.md Part F.1:
  /readings/{timestamp} -> { accel, temp, distance, gasRaw, soilMoisture, timestamp, cycle }
"""

# ============================================================================
# SINGLE INTEGRATED NODE METADATA
# ============================================================================
NODE_INFO = {
    "nodeId": "hazentra-node-01",
    "name": "Hazentra Integrated Environmental Station",
    "location": {
        "lat": 26.1445,
        "lng": 91.7362,
        "description": "Guwahati Integrated Monitoring Site",
    },
    "hardware": {
        "mcu": "ESP32 Dev Module (38-pin)",
        "sensors": [
            "ADXL345 (I2C: GPIO 21/22)",
            "DHT22 (Digital: GPIO 4)",
            "HC-SR04 (Pulse: GPIO 5/18)",
            "MQ-135 (ADC: GPIO 35)",
            "Soil Moisture Sensor (ADC: GPIO 39)",
            "16x2 LCD (I2C: 0x3F)",
        ],
        "baudRate": 115200,
        "debounceLimit": 2,
    },
}

# ============================================================================
# TELEMETRY SENSOR BASELINES (from real hardware serial output)
# ============================================================================
BASELINES = {
    "accel": {
        "mean": 3.50,         # m/s^2 (observed baseline)
        "noise_sigma": 0.03,
        "earthquake_threshold": 4.00,
    },
    "temp": {
        "mean": 33.9,         # deg C (observed ambient)
        "diurnal_amp": 2.5,   # +/- diurnal fluctuation
        "noise_sigma": 0.15,
        "fire_threshold": 35.0,
    },
    "distance": {
        "mean": 135.0,        # cm (observed distance to ground/water)
        "noise_sigma": 0.4,
        "flood_threshold": 10.0,
    },
    "gasRaw": {
        "mean": 155.0,        # raw ADC 0-4095 (observed ambient 147-161)
        "noise_sigma": 3.0,
        "base_threshold": 150, # CLAUDE.md spec threshold
        "spike_delta": 25,    # Delta required to confirm active hazard vs ambient drift
    },
    "soilMoisture": {
        "mean": 42.0,         # % in normal soil (bench test without soil read 100%)
        "noise_sigma": 1.5,
        "saturation_threshold": 70.0,
    },
}

# ============================================================================
# FUSION THRESHOLDS & RULES (CLAUDE.md Section 10 & Plan Part C.2)
# ============================================================================
FUSION_RULES = {
    "earthquake": {
        "accel_threshold": 4.0,       # m/s^2
        "debounce_reads": 2,          # consecutive reads required
        "standalone": True,
    },
    "fire": {
        "gas_threshold": 150,         # spec threshold
        "gas_spike_delta": 25,        # spike above ambient window
        "temp_rising_threshold": 0.3, # deg C trend
    },
    "flood": {
        "distance_threshold": 10.0,   # cm
        "soil_rising_threshold": 1.0, # soil trend rising
        "consecutive_reads": 2,       # consecutive reads debounce
    },
    "gas_leak": {
        "gas_threshold": 150,         # spec threshold
        "gas_spike_delta": 25,        # spike above ambient window
        "temp_flat_threshold": 0.3,   # trend <= 0.3 (eliminates dead zone)
    },
    "landslide": {
        "soil_threshold": 70.0,       # % saturated
        "accel_min": 3.65,            # sustained micro-tremor
        "accel_max": 4.0,             # below earthquake threshold
        "accel_trend_min": 0.03,      # upward micro-vibration trend
    },
    "compound": {
        "time_window_seconds": 90,    # multi-hazard correlation window
    },
}

# ============================================================================
# SACHET ALERT PAYLOAD TEMPLATE (NDMA Interoperability Shape)
# ============================================================================
SACHET_PAYLOAD_TEMPLATE = {
    "version": "1.0",
    "source": "hazentra",
    "sourceNodeId": "hazentra-node-01",
    "hazardType": None,
    "severity": None,            # advisory | watch | warning | danger
    "confidence": None,          # 0-100
    "verificationStatus": None,  # pending | verified | denied | verified_by_timeout
    "location": {
        "lat": 26.1445,
        "lng": 91.7362,
        "description": "Guwahati Integrated Monitoring Site",
    },
    "timestamp": None,
    "sensorData": {},
    "message": None,
}

# ============================================================================
# COMMUNITY VERIFICATION SETTINGS (Fast2SMS)
# ============================================================================
VERIFICATION_SETTINGS = {
    "test_numbers": ["+919876543210", "+919876543211", "+919876543212"],
    "yes_weight": 8.0,
    "no_weight": -12.0,
    "escalation_threshold": 65.0,
    "timeout_seconds": 300,
    "sms_templates": {
        "earthquake": "[HAZENTRA] Seismic tremor detected near {location}. Did you feel shaking? Reply YES or NO. Ref: {anomaly_id}",
        "fire": "[HAZENTRA] Fire/thermal risk detected near {location} (Gas: {gas}, Temp: {temp}C). Do you observe smoke/flames? Reply YES or NO. Ref: {anomaly_id}",
        "flood": "[HAZENTRA] Flood alert near {location} (Water level critical: {dist}cm). Is flooding occurring? Reply YES or NO. Ref: {anomaly_id}",
        "gas_leak": "[HAZENTRA] Hazardous gas spike detected near {location} (Gas ADC: {gas}). Do you smell gas/fumes? Reply YES or NO. Ref: {anomaly_id}",
        "landslide": "[HAZENTRA] Ground instability/landslide precursor near {location} (Soil: {soil}%, Tremor: {accel} m/s2). Reply YES or NO. Ref: {anomaly_id}",
        "compound": "[HAZENTRA] COMPOUND DISASTER ALERT near {location} ({hazards}). Reply YES if severe conditions observed, NO if not. Ref: {anomaly_id}",
    },
}
