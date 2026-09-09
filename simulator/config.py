"""
Hazentra Simulator — Configuration & Calibration Constants
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
All sensor ranges, thresholds, and noise parameters are calibrated against
real reference data from IMD (rainfall), CPCB (air quality), and CWC
(river hydrology). See CLAUDE_Hazentra.md Section 8-10 for context.

Deployment site: Guwahati, Assam (flood-prone Brahmaputra basin).
Season baseline: September monsoon.
"""

# ============================================================================
# NODE DEFINITIONS — matches Firestore /nodes/{nodeId} schema (Section 9)
# ============================================================================

NODES = {
    "flood-node-01": {
        "name": "Brahmaputra River Bank Station",
        "type": "flood",
        "lat": 26.1445,
        "lng": 91.7362,
        "status": "online",
    },
    "airq-node-01": {
        "name": "Guwahati Urban AQ Station",
        "type": "air_quality",
        "lat": 26.1558,
        "lng": 91.7456,
        "status": "online",
    },
}

# Which sensors each node type physically has
NODE_SENSORS = {
    "flood": [
        "waterLevel", "rainfall", "temp", "humidity",
        "soilMoisture", "vibration",
    ],
    "air_quality": [
        "pm25", "gas", "smoke", "temp", "humidity",
    ],
}

# ============================================================================
# IMD RAINFALL CLASSIFICATION (mm/hour)
# Ref: IMD Technical Circular, data.gov.in historical rainfall
# Guwahati September average: ~280 mm/month ≈ 9.3 mm/day
# Heavy-rain days: 8-12 per month during monsoon peak
# ============================================================================

RAINFALL_CLASSES = {
    "no_rain":           (0.0,  0.5),
    "light":             (0.5,  2.5),
    "moderate":          (2.5,  7.5),
    "heavy":             (7.5,  20.0),
    "very_heavy":        (20.0, 50.0),
    "extremely_heavy":   (50.0, 100.0),
}

# ============================================================================
# CPCB NATIONAL AIR QUALITY INDEX — PM2.5 24-hr avg (μg/m³)
# Ref: CPCB NAQI guidelines / CAAQMS continuous monitoring
# Guwahati typical PM2.5: 35-65 μg/m³ (satisfactory–moderate)
# ============================================================================

PM25_BREAKPOINTS = {
    "good":         (0,   30),
    "satisfactory": (31,  60),
    "moderate":     (61,  90),
    "poor":         (91,  120),
    "very_poor":    (121, 250),
    "severe":       (251, 500),
}

# ============================================================================
# WATER LEVEL — distance from HC-SR04 sensor to water surface (cm)
# Sensor mounted ~4 m above normal water level on bridge/pole
# LOWER reading = HIGHER water = MORE danger
# ============================================================================

WATER_LEVEL_CLASSES = {
    "normal":   (250, 400),
    "elevated": (150, 250),
    "warning":  (80,  150),
    "danger":   (20,  80),
}

# ============================================================================
# GAS / SMOKE SENSOR LEVELS (ppm-equivalent analog readings)
# ============================================================================

GAS_LEVELS = {          # MQ-135 Air Quality
    "clean":     (20,  80),
    "normal":    (80,  150),
    "elevated":  (150, 300),
    "high":      (300, 500),
    "dangerous": (500, 1000),
}

SMOKE_LEVELS = {        # MQ-2 Smoke/Combustible Gas
    "clean":   (20,  80),
    "ambient": (80,  150),
    "smoke":   (300, 600),
    "fire":    (600, 1000),
}

# ============================================================================
# SOIL MOISTURE (% volumetric water content)
# ============================================================================

SOIL_MOISTURE_LEVELS = {
    "dry":         (10, 30),
    "normal":      (30, 55),
    "wet":         (55, 75),
    "saturated":   (75, 90),
    "waterlogged": (90, 100),
}

# ============================================================================
# VIBRATION — MPU6050 accelerometer (g-force RMS)
# ============================================================================

VIBRATION_LEVELS = {
    "calm":        (0.00, 0.05),
    "minor":       (0.05, 0.15),
    "moderate":    (0.15, 0.40),
    "significant": (0.40, 1.00),
}

# ============================================================================
# MONSOON CLIMATE BASELINE — Guwahati, September
# ============================================================================

TEMP_MONSOON = {
    "mean": 28.0,
    "diurnal_amplitude": 4.5,   # half-range of daily sinusoidal cycle
    "peak_hour": 14.0,          # local solar peak ~2 PM
}

HUMIDITY_MONSOON = {
    "mean": 82.0,
    "diurnal_amplitude": 8.0,   # inversely correlated with temperature
}

# ============================================================================
# SENSOR NOISE — Gaussian σ for each sensor type
# Derived from datasheet tolerances + real-world environmental jitter
# ============================================================================

SENSOR_NOISE = {
    "waterLevel":   1.5,    # cm   (HC-SR04 ±3 mm + environmental bounce)
    "rainfall":     0.3,    # mm/hr
    "pm25":         3.0,    # μg/m³
    "gas":          8.0,    # ppm
    "smoke":        8.0,    # ppm
    "temp":         0.3,    # °C   (DHT22 rated ±0.5 °C)
    "humidity":     1.5,    # %    (DHT22 rated ±2 %)
    "soilMoisture": 2.0,    # %
    "vibration":    0.008,  # g
}

# ============================================================================
# TIMING DEFAULTS
# ============================================================================

DEFAULT_INTERVAL_SECONDS = 30       # sensor polling interval
DEFAULT_NORMAL_DURATION_HOURS = 24  # full-day baseline
DEFAULT_EVENT_DURATION_HOURS = 8    # hazard-event scenario

# ============================================================================
# FUSION / ALERT THRESHOLDS (mirrored from Section 10 for scenario design)
# ============================================================================

THRESHOLDS = {
    "flood": {
        "water_level_warning": 150,     # cm — below this → warning
        "water_level_danger": 80,       # cm — below this → danger
        "water_rise_rate": 5.0,         # cm/min — rate-of-rise threshold
        "rainfall_heavy": 7.5,         # mm/hr — IMD "heavy"
        "soil_moisture_saturated": 75,  # % — saturation point
    },
    "fire": {
        "smoke_spike": 300,             # ppm — sudden spike threshold
        "gas_elevated": 200,            # ppm — elevated gas
        "smoke_rate_of_change": 50,     # ppm/min — sharpness of spike
    },
    "air_quality": {
        "pm25_poor": 91,               # μg/m³ — CPCB "Poor"
        "pm25_very_poor": 121,          # μg/m³ — CPCB "Very Poor"
        "pm25_severe": 251,             # μg/m³ — CPCB "Severe"
    },
}

# ============================================================================
# SACHET-STYLE PAYLOAD TEMPLATE (Section 4.4)
# ============================================================================

SACHET_PAYLOAD_TEMPLATE = {
    "version": "1.0",
    "source": "hazentra",
    "sourceNodeId": None,
    "hazardType": None,
    "severity": None,           # advisory | watch | warning | danger
    "confidence": None,         # 0-100
    "verificationStatus": None, # pending | verified | denied
    "location": {
        "lat": None,
        "lng": None,
        "description": None,
    },
    "timestamp": None,
    "sensorData": {},
    "message": None,
}

# ============================================================================
# COMMUNITY VERIFICATION — test phone numbers & SMS templates
# ============================================================================

TEST_PHONES = ["+919876543210", "+919876543211", "+919876543212"]

SMS_TEMPLATES = {
    "flood": (
        "[HAZENTRA] Flood risk detected near {location}. "
        "Water level rising rapidly. "
        "Reply YES if you observe flooding, NO if not. Ref: {anomaly_id}"
    ),
    "fire": (
        "[HAZENTRA] Fire/smoke detected near {location}. "
        "Reply YES if you observe fire or heavy smoke, NO if not. Ref: {anomaly_id}"
    ),
    "air_quality": (
        "[HAZENTRA] Severe air quality detected near {location}. "
        "PM2.5 at {pm25} μg/m³ (CPCB: {category}). "
        "Reply YES to confirm poor visibility/irritation, NO if not. Ref: {anomaly_id}"
    ),
    "compound": (
        "[HAZENTRA] COMPOUND RISK near {location}: {hazards}. "
        "Reply YES if you observe these conditions, NO if not. Ref: {anomaly_id}"
    ),
}
