# Hazentra — Software Implementation Plan

**Team:** Hacktrix | **Event:** Smart India Hackathon 2026 | **PS:** 26178 — AI-Powered
Environmental Intelligence Network | **Theme:** Disaster Management | **Category:** Hardware

**Purpose of this document:** This is the build spec for the software layer of Hazentra,
written to be handed directly to an AI coding assistant (or a developer) to implement.
It covers what hardware is already done, the exact strategy for why this wins, and a
fully structured, phase-by-phase software build plan with concrete technical specs.

---

## PART A — WHERE WE ARE: HARDWARE STATUS

### A.1 What's physically built

A single integrated ESP32 multi-sensor node is wired, flashed, and producing live
telemetry over UART serial (115200 baud). This is real, working hardware — not a
concept.

| Component | Pin Connections | Signal Type | Telemetry Unit | Detects |
|---|---|---|---|---|
| ESP32 Dev Module | Processor (core logic) | — | System cycle count | Data aggregation & decision logic |
| ADXL345 Accelerometer | GPIO 21 (SDA), GPIO 22 (SCL) | I2C Protocol | Acceleration (m/s²) | Ground vibration / seismic motion |
| DHT22 Sensor | GPIO 4 | Digital single-bus | Temperature (°C) | Thermal anomaly / fire detection |
| HC-SR04 Ultrasonic | GPIO 5 (Trig), GPIO 18 (Echo) | Digital pulse | Distance (cm) | Water elevation / flood detection |
| MQ-135 Air Sensor | GPIO 35 | Analog input (ADC) | Raw value (0–4095) | Air quality / gas & smoke detection |
| Soil Moisture Sensor | GPIO 39 | Analog input (ADC) | Moisture (%) | Ground saturation / landslide risk |
| 16x2 LCD Module | GPIO 21 (SDA), GPIO 22 (SCL) | I2C (0x3F) | Visual text display | Local user interface & alerts |

### A.2 Current on-device logic (firmware-level, as built)

- All 5 sensors read on a cycle
- A **debounce counter (limit = 2)** requires two consecutive positive reads before
  a status change fires — this filters transient sensor noise and is a genuinely
  good, keep-as-is design decision
- Current thresholds (single-sensor, independent):
  - Earthquake: total vector acceleration > 4.0 m/s² (baseline ~3.5 m/s²)
  - Fire: temperature > 35.0°C
  - Flood: ultrasonic distance ≤ 10.0 cm
  - Gas leak: MQ-135 raw ADC ≥ 150
  - Landslide risk: soil moisture ≥ 70%
- Output: structured telemetry over Serial at 115200 baud

### A.3 The one hardware-adjacent decision this plan makes

**As currently built, hazard evaluation is a flat decision tree — 5 independent
threshold checks, no correlation between sensors.** This is functionally identical
to the single-hazard detection pattern already common in deployed systems (e.g. IIT
Mandi's landslide network) and academic prototypes. It is NOT yet the cross-hazard
fusion this project is positioned around.

**This plan moves hazard evaluation off the ESP32 and into the cloud**, where
multi-reading history and cross-sensor correlation are actually practical to
implement. The ESP32's job becomes: read sensors, debounce, transmit clean raw
values. All hazard logic — including real fusion — lives in Part B below. No
additional hardware or sensors are required for this; it is a software / logic
change only.

---

## PART B — THE WINNING STRATEGY (context for every implementation decision below)

### B.1 What already exists (do not re-invent, do not claim novelty over this)

- IMD's Multi-Hazard Early Warning DSS — national, satellite/radar-driven forecasting
- NDMA's SACHET — national alert dissemination, real, operational
- IIT Mandi's low-cost AI landslide network — real, deployed, 60+ sites, proves
  cheap ground sensing works in India
- Aurassure–IIT Bombay — commercial flood monitoring, institutional pricing

### B.2 What does NOT exist, and is our actual differentiation — everything below
must be built to make these four claims literally, demonstrably true

1. **Real-time cross-hazard fusion at the ground-sensor level** (not satellite-scale
   mapping, not single-hazard detection) — Part C
2. **Community-verified confidence scoring** via a live SMS confirm/deny loop — Part D
3. **Radically low cost, fully open hardware/software** — already true (see CLAUDE.md
   BOM), just needs the software to not add unnecessary cost/complexity
4. **Structured, API-ready output designed for SACHET/NDMA handoff** — Part E

### B.3 Why this wins on the judging criteria that matter

| Criterion | How the software delivers it |
|---|---|
| Technical depth | Real fusion logic (not just 5 if-statements), genuine cloud architecture |
| Innovation | Verification loop + fusion + interoperability stack — see Part B.2 |
| Feasibility | Built on proven, boring tech (Firebase, ESP32, SMS gateway) — not research-grade ML |
| Judge defensibility | Every claim on the pitch deck must map to code that actually exists and runs live |
| Demo potential | Live dashboard reacting in real time to physically-triggered sensor events |
| Honesty / credibility | Explicit "built vs. roadmap" distinction throughout — see CLAUDE.md Section 6 |

**Golden rule for the AI model building this: never implement a feature that looks
good on a slide but isn't real. Every pitch claim must be traceable to working code.**

---

## PART C — FUSION ENGINE (the core innovation — build this with care)

### C.1 Why the current threshold logic must change

The existing 5-independent-threshold design must be replaced with cross-signal
correlation rules. This is not optional polish — it is the specific, load-bearing
claim ("AI Sensor Fusion Engine") on the team's pitch deck.

### C.2 Required fusion rules

| Hazard | Old logic (single-sensor) | New logic (fusion, required) |
|---|---|---|
| Landslide | Soil moisture ≥ 70% alone | Soil moisture ≥ 70% **AND** sustained non-zero vibration trending upward, but below the earthquake threshold, across the last N readings |
| Fire / Gas | MQ-135 ADC ≥ 150 alone | Gas ADC ≥ 150 **AND** temperature rising within the same time window — distinguishes a real fire/gas event from sensor drift |
| Flood | Distance ≤ 10cm alone (single snapshot) | Distance ≤ 10cm **AND** soil moisture also rising, tracked across consecutive readings — distinguishes sustained rise from a one-off glitch |
| Earthquake | Acceleration > 4.0 m/s² | **Stays standalone** — legitimately independent signal, no correlation needed, but keep the debounce logic |

### C.3 Implementation requirements

- Implement as a **Firebase Cloud Function**, triggered on new writes to `/readings`
- Maintain a short rolling window (last 5–10 readings) per sensor to compute trend
  direction (rising/falling/flat), not just instantaneous values
- Every fusion evaluation outputs a `rawConfidence` score (0–100), never a bare
  boolean — this feeds directly into Part D
- Calibrate numeric thresholds against real historical data where possible: IMD
  rainfall data (data.gov.in) for flood-adjacent logic, CPCB CAAQMS baseline ranges
  for gas/air thresholds — do not use arbitrary numbers without at least a stated
  rationale
- Logic must be rule-based/statistical and fully explainable step-by-step — explicitly
  do NOT implement a black-box or trained ML model for this hackathon build; it is
  slower to build, harder to defend live, and unnecessary for what's being claimed

---

## PART D — COMMUNITY VERIFICATION LOOP (highest execution risk — start early)

### D.1 Purpose

Every escalated alert must first pass through a live human confirmation step. This
is the project's single most memorable, most differentiated demo moment — treat it
as equal priority to the fusion engine, not an afterthought.

### D.2 Flow

1. Fusion engine writes a new document to `/anomalies` with `rawConfidence`
2. A Cloud Function triggers an SMS via **Fast2SMS** (India-native, no-DLT Quick
   Route for fast setup) to a configured list of test numbers:
   `"[Hazard type] risk detected near you. Reply YES if you observe this, NO if not."`
3. Fast2SMS inbound webhook → a Firebase Cloud Function (HTTP-triggered) receives
   replies, writes to `/verifications/{anomalyId}/responses/{phone}`
4. Confidence scoring: each `YES` increases `verifiedConfidence`; each `NO`
   decreases it; a timeout with no response leaves `rawConfidence` as the fallback
5. When `verifiedConfidence` crosses an escalation threshold → write to `/alerts`
   and trigger Part E

### D.3 Build and test order

Build and fully test this against **mocked/simulated anomalies** (Part F) before any
real sensor hardware is involved — the entire SMS round-trip can and should be
verified end-to-end without a single physical sensor reading.

---

## PART E — ALERT DISPATCH & OFFICIAL-PIPELINE INTEROPERABILITY

- On `/alerts` write, dispatch:
  - SMS to a broader contact list (Fast2SMS)
  - Push notification via Firebase Cloud Messaging
  - Real-time update to the dashboard (Firestore listener, no extra infra needed)
- Generate a `sachetPayload` object on every alert — a structured JSON object shaped
  to resemble a SACHET/NDMA-style alert schema (hazard type, location, confidence,
  timestamp, description). This does not need a real integration with SACHET's
  actual API (not publicly available for a hackathon team) — it needs to be a real,
  inspectable, well-structured object that makes the "interoperability" claim
  concrete and demoable, not just a bullet point on a slide.

---

## PART F — DATA LAYER: SCHEMA + SIMULATOR (build this FIRST, unblocks everything)

### F.1 Firestore schema

```
/readings/{timestamp}
  - accel: number
  - temp: number
  - distance: number
  - gasRaw: number
  - soilMoisture: number
  - timestamp: timestamp

/anomalies/{anomalyId}
  - type: "earthquake" | "fire" | "flood" | "gas_leak" | "landslide" | "compound"
  - rawConfidence: number (0-100)
  - verifiedConfidence: number (0-100)
  - status: "pending" | "verified" | "denied" | "escalated"
  - timestamp: timestamp

/verifications/{anomalyId}/responses/{phoneNumber}
  - response: "YES" | "NO"
  - timestamp: timestamp

/alerts/{alertId}
  - anomalyId: string
  - hazardType: string
  - confidenceScore: number
  - message: string
  - channelsSent: string[]
  - sachetPayload: object
  - timestamp: timestamp
```

### F.2 Simulated data generator — build this before touching real hardware integration

Write a standalone script (Node.js or Python) that writes realistic fake readings
into `/readings` on an interval, with value ranges informed by real IMD/CPCB data
where applicable. This is the **permanent test harness** for the whole system:

- Simulate a flood by scripting a rising `distance` (falling) + rising `soilMoisture`
  sequence
- Simulate a fire by scripting a `gasRaw` spike + rising `temp` in the same window
- Simulate a landslide by scripting sustained `soilMoisture` ≥70% + a mild, non-zero,
  upward-trending `accel` reading
- Everything downstream (fusion, verification, dashboard) must be built and fully
  testable against this simulator alone — real hardware integration (Part G) is a
  drop-in replacement once the schema matches, not a rewrite

---

## PART G — HARDWARE-TO-CLOUD BRIDGE

Two paths — build the fast one first, upgrade later if time allows.

**Fast path (build today):** A Python/Node script on a laptop reads the ESP32's
serial output (115200 baud), parses each telemetry line, and pushes it into
`/readings` via the Firebase Admin SDK. No firmware changes required.

**Upgrade path (build if time allows):** Add WiFi + an HTTP client / Firebase
library directly into the ESP32 firmware so the node pushes to Firestore
independently, without a laptop bridge — required for a clean, standalone demo on
stage. Do this only after the fast path and everything downstream already works.

---

## PART H — DASHBOARD

React app, built and fully testable against the Part F simulator from day one.

- **Live hazard-status panel** — 5 clear cards (Earthquake / Fire / Flood / Gas /
  Landslide), each showing current reading, threshold, and status
  (normal / watch / alert) — this is the strongest, most legible visual for a
  single-node build
- **Live sensor trend charts** (Recharts) — genuinely continuous multi-sensor
  telemetry is a real strength here, show it
- **Alert feed** — chronological, clearly distinguishing pending verification /
  community-verified / escalated states
- **Multi-node map** — de-emphasize or omit for this build; if included at all,
  label explicitly as "Projected Multi-Node Deployment (Simulated)," never
  presented as live data (this is a hard rule — see CLAUDE.md Section 6)
- Prioritize at-a-glance legibility — a judge looks at this for seconds

---

## PART I — TECH STACK SUMMARY

| Layer | Technology |
|---|---|
| Node compute | ESP32 (as built) |
| Sensors | ADXL345, DHT22, HC-SR04, MQ-135, soil moisture (as built) |
| Local display | 16x2 I2C LCD (as built) |
| Serial bridge | Python/Node script → Firebase Admin SDK |
| Backend | Firebase (Firestore + Cloud Functions) |
| Fusion logic | Rule-based/statistical, JavaScript or Python in Cloud Functions |
| SMS | Fast2SMS (India-native, no-DLT Quick Route) |
| Push notifications | Firebase Cloud Messaging |
| Dashboard | React + Recharts (+ Leaflet only if multi-node map is included) |

---

## PART J — BUILD ORDER (do not reorder without good reason)

1. Firestore schema (Part F.1) + simulator (Part F.2) — unblocks everything else
2. Fusion Cloud Function (Part C) against simulated data
3. Verification loop (Part D) against simulated anomalies — start early, highest risk
4. Alert dispatch + SACHET payload structure (Part E)
5. Dashboard (Part H), built against the same simulated stream
6. Serial-to-Firestore bridge (Part G, fast path) — connect real hardware
7. Full end-to-end rehearsal: physically trigger each hazard (shake for earthquake,
   heat source for fire, water for flood, gas source for leak, wet soil for
   landslide), confirm fusion → verification → dashboard → alert all fire correctly
8. Record a working end-to-end run on video as a stage-demo fallback
9. (If time remains) Upgrade path in Part G — standalone WiFi firmware

---

## PART K — WHAT NOT TO BUILD (protect remaining time)

- No real LoRaWAN mesh — roadmap only, keep saying so consistently
- No custom-trained ML model — the rule-based fusion in Part C is sufficient and
  more defensible
- No user authentication/role system unless significant time remains
- No native mobile app — SMS-based verification satisfies the "mobile-enabled"
  requirement at prototype stage; a full app is roadmap
- No real integration with SACHET's actual backend (not publicly accessible) — a
  well-structured mock payload is the correct scope

---

## PART L — ACCEPTANCE CRITERIA (how the team knows this is demo-ready)

- [ ] Simulator can trigger all 5 hazard types plus at least 1 compound (cross-hazard) case
- [ ] Fusion Cloud Function correctly classifies each simulated scenario with a
      sensible confidence score
- [ ] SMS verification round-trip works end-to-end on a real phone (send → reply → confidence update)
- [ ] Dashboard updates live within a few seconds of a new anomaly/alert
- [ ] A generated `sachetPayload` object is inspectable and well-structured for at
      least one real alert
- [ ] Real ESP32 hardware data flows into the same pipeline via the serial bridge
- [ ] A full physical trigger-to-dashboard-to-alert run has been recorded on video
- [ ] All cost figures, node counts, and capability claims in the dashboard and
      pitch deck match what is actually built (per CLAUDE.md Section 6)

---

## PART M — HANDOFF NOTES FOR THE AI BUILDER

- This document supersedes the multi-node references in earlier drafts of
  CLAUDE.md — the current hardware reality is **one integrated multi-sensor node**,
  not a 2-node split. Update CLAUDE.md's hardware section and the pitch deck's
  Platform Overview panel to match this document before final submission.
- Build in the order specified in Part J — earlier parts are dependencies for later
  ones, and the simulator-first approach is deliberate, not optional.
- When in doubt about whether a feature belongs in this build, check it against
  Part K before implementing.
- Every generated line of pitch copy, dashboard label, or code comment should stay
  consistent with Part B.1 and B.2 — do not let generated content imply the project
  is the first or only system of its kind; the specific, narrow differentiation
  claims in B.2 are the only ones to make.
