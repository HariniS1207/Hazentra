# Hazentra — Project Reference (CLAUDE.md)

**Team:** Hacktrix (Allocious Franklin R, Akash N, Harini S, Geethapriya, Malini, Mohamed Al Silmi)
**Event:** Smart India Hackathon 2026 — Problem Statement 26178
**Official PS Title:** AI-Powered Environmental Intelligence Network
**Theme:** Disaster Management | **Category:** Hardware | **Sponsor:** Qualcomm Inc

This document is the single source of truth for anyone (human or AI) working on this
project. Read it before writing any code. It covers what we're building, why, what
makes it different from what already exists, exactly what hardware is real today,
and exactly how the software should be architected and built.

---

## 1. THE PROBLEM

India faces recurring, high-damage environmental hazards — urban and river flooding,
forest fires, hazardous air pollution, extreme heat, landslides, industrial chemical
leaks, and seismic activity — concentrated in states like Assam, Bihar, Kerala,
Maharashtra, Uttarakhand, Himachal Pradesh, and central Indian forest belts. Climate
change is increasing both frequency and intensity.

Three specific, validated gaps exist in how India currently handles this:

1. **No ground-truth layer.** National systems (IMD's Multi-Hazard Early Warning DSS,
   NDMA's SACHET) forecast and broadcast at district/regional granularity. Neither has
   real-time street- or village-level sensing, and neither verifies whether a warning
   matches what's actually happening on the ground before or after dissemination.

2. **Isolated, single-hazard detection.** Even real, deployed low-cost systems (e.g.
   IIT Mandi's AI landslide sensor network, 60+ sites in Himachal Pradesh, >90%
   accuracy, 3-hour advance warning) detect one hazard type in isolation. Nobody
   correlates signals *across* hazard types on a single low-cost sensing platform to
   catch compound or fast-developing risk patterns.

3. **High cost, one-way, low trust.** Commercial-grade IoT environmental monitoring
   (e.g. Aurassure's flood monitoring, deployed with IIT Bombay) is priced for
   institutions and city corporations. It is out of reach for panchayats, NGOs, and
   the rural/last-mile communities who need it most. Alerts are broadcast one-way,
   with no mechanism for the community to confirm ground truth — a documented cause
   of false-alarm fatigue and low public trust in disaster warnings (per CEEW/IFRC
   research across 14 countries).

---

## 2. WHAT ALREADY EXISTS (research findings — read before claiming novelty)

We ran two full adversarial research passes before committing to this direction.
Do not claim Hazentra is the first system of its kind — it is not. Be specific
about what IS actually new.

**Already real and deployed / operational:**
- IMD Multi-Hazard Early Warning Decision Support System (MHEW-DSS) — national,
  GIS-based, satellite/radar/AWS-driven, launched under Mission Mausam, Jan 2024.
  Won National Award for e-Governance 2025, UN Sasakawa Award, GovTech Award 2026.
- NDMA SACHET — national alert dissemination, 30,000+ alerts issued, CAP-based,
  geo-targeted, multi-channel.
- A nationwide Cell Broadcast Alert System with actionable instructions was tested
  in May 2026 (indigenous technology, multilingual, works across 2G–5G).
- IIT Mandi's low-cost AI landslide network — real, deployed, indigenous, low-cost,
  60+ sites, proof that this class of system works technically and economically in
  India.
- Aurassure–IIT Bombay urban flood monitoring — commercial IoT + AI, real deployment.
- Academic literature already covers: IoT multi-hazard sensor node architectures
  (Springer), cross-hazard fusion at regional/satellite scale (e.g. compound
  flood-landslide susceptibility mapping), citizen-sensor/crowdsourced verification
  concepts (research stage, not deployed as an India-specific official-pipeline
  feeder).

**What we found NO evidence of, anywhere:**
- A low-cost, single-platform sensor system that performs **real-time cross-hazard
  correlation across genuinely different sensor types** (not single-hazard, not
  satellite-scale mapping).
- Any system — commercial or government — that runs a **two-way community
  verification loop** (SMS confirm/deny adjusting alert confidence) integrated with
  ground sensors.
- Any system explicitly architected to **feed verified, structured, ground-truth
  alerts into SACHET/NDMA** as a last-mile input layer, rather than operating as an
  isolated parallel system.

**Conclusion used in all our messaging:** Hazentra does not claim to be the first
environmental sensor system or the first AI early-warning system. It claims to be
the first to combine low-cost ground sensing + real-time cross-hazard fusion +
community-verified confidence scoring + explicit integration into India's existing
official warning infrastructure, in one system. Always position it this way —
"complementary, not competitive" — in any generated copy, pitch text, or UI language.

---

## 3. OUR SOLUTION

### 3.1 What is actually built today (prototype reality)

**One integrated ESP32 multi-sensor node**, wired, flashed, and producing live
telemetry over UART serial (115200 baud). Not a distributed multi-node network —
a single platform sensing five distinct hazard signals at one location. This is
real, working hardware.

| Component | Pin Connections | Signal Type | Telemetry Unit | Detects |
|---|---|---|---|---|
| ESP32 Dev Module | Processor (core logic) | — | System cycle count | Data aggregation & decision logic |
| ADXL345 Accelerometer | GPIO 21 (SDA), GPIO 22 (SCL) | I2C Protocol | Acceleration (m/s²) | Ground vibration / seismic motion |
| DHT22 Sensor | GPIO 4 | Digital single-bus | Temperature (°C) | Thermal anomaly / fire detection |
| HC-SR04 Ultrasonic | GPIO 5 (Trig), GPIO 18 (Echo) | Digital pulse | Distance (cm) | Water elevation / flood detection |
| MQ-135 Air Sensor | GPIO 35 | Analog input (ADC) | Raw value (0–4095) | Air quality / gas & smoke detection |
| Soil Moisture Sensor | GPIO 39 | Analog input (ADC) | Moisture (%) | Ground saturation / landslide risk |
| 16x2 LCD Module | GPIO 21 (SDA), GPIO 22 (SCL) | I2C (0x3F) | Visual text display | Local user interface & alerts |

On-device firmware currently applies a **debounce counter (limit = 2)** — two
consecutive positive reads required before a status change fires. This filters
transient sensor noise and should be kept as-is.

**Say this explicitly wherever the project is described: Hazentra's current
prototype is a single integrated 5-sensor node, not a multi-node distributed mesh.**
Do not imply otherwise in the pitch deck, dashboard, or any generated copy.

### 3.2 Final vision (target architecture, roadmap — not built yet)

A distributed network of solar-powered smart sensor nodes deployed at flood-prone
rivers, forests, industrial zones, and vulnerable communities, each running the
same fusion logic locally, connected via LoRaWAN mesh, escalating only
community-verified alerts through multiple channels, with output structured for
direct handoff into NDMA's SACHET pipeline. This is the scaled target the current
prototype's architecture is designed to extend into — always distinguish this
explicitly from what exists today.

---

## 4. INNOVATION STACK (the four things to keep provably real, not just claimed)

1. **Cross-Hazard Fusion Engine** — correlates signals *across different sensor
   types on the same platform* to catch compound risk patterns a single-threshold
   check would miss (see Section 10 for the exact required logic: soil moisture +
   vibration for landslide, gas + temperature for fire, distance + soil trend for
   flood). This must be *actually implemented* as explainable logic — not a
   black-box model, not a claim without code behind it.
2. **Community Verification Layer** — SMS-based confirm/deny loop that adjusts a
   numeric confidence score before an alert escalates. This is our strongest,
   most memorable, most defensible differentiator — prioritize building and
   demoing this working end-to-end over any other feature.
3. **Radical Cost & Openness** — real prototype cost ₹1,419 for the full sensor set
   (see Section 8 for the priced BOM), fully open BOM and design, no vendor
   lock-in, panchayat/NGO self-deployable at scale.
4. **Official-Pipeline Interoperability** — every escalated alert is structured to
   match a SACHET/NDMA-style payload shape. Even in the prototype, generate a real,
   inspectable JSON object with this shape — it makes the "interoperability" claim
   concrete and demoable, not just a slide bullet.

---

## 5. IMPACT (how to talk about it, and what to actually measure)

- **Direct:** closes the last-mile ground-truth gap — hyperlocal, on-the-ground
  multi-hazard sensing vs. district/block-level granularity from national systems.
- **Economic:** order-of-magnitude cheaper than institutional-grade systems —
  realistically ownable by panchayats and NGOs, not just city corporations.
- **Trust & adoption:** community verification directly targets the
  research-documented root cause of last-mile warning failure — false-alarm
  fatigue and low trust — not just a detection-accuracy problem.
- **Systemic:** designed to strengthen (not duplicate) Mission Mausam, SACHET, and
  NDMA's existing investments.

When generating any pitch copy, dashboard language, or reports: always frame impact
in terms of what is **measurable and demoable** (e.g. "reduced false-positive rate
in our test run," "1 working integrated node, real calibrated thresholds") —
never invent adoption numbers, deployment scale, or accuracy percentages that
haven't actually been measured in this project.

---

## 6. HONESTY RULES (apply these everywhere — pitch, docs, code comments, UI copy)

- We have built and demonstrated **one integrated multi-sensor prototype node**
  (5 hazard signals: earthquake, fire, flood, gas leak, landslide risk) — say this
  explicitly, do not imply a multi-node network exists.
- A distributed multi-node mesh, LoRaWAN connectivity, solar power at scale, and a
  full mobile app are **roadmap / next-phase**, not built yet — always distinguish
  "what we built" from "what the architecture is designed to scale to."
- Any dashboard view showing more nodes than physically exist must be clearly
  labeled as a projected/simulated fleet view, not presented as live data.
- Cost figures used anywhere in the project (pitch deck, dashboard, docs) must match
  the actual priced BOM in Section 8, not earlier draft estimates from before
  hardware was purchased.

---

## 7. TECH STACK

| Layer | Technology | Notes |
|---|---|---|
| Node compute | ESP32 WROOM (38-pin) | Single integrated node, as built |
| Seismic sensing | ADXL345 accelerometer | I2C, ground vibration / earthquake |
| Thermal sensing | DHT22 | Temperature/humidity, fire signal |
| Water-level sensing | HC-SR04 ultrasonic | Flood detection |
| Air-quality sensing | MQ-135 | Gas/smoke, analog ADC |
| Ground-saturation sensing | Soil moisture sensor | Landslide risk, analog ADC |
| Local display | 16x2 I2C LCD | On-device status/alerts |
| Serial bridge | Python/Node script to Firebase Admin SDK | Fast path: reads UART, pushes to Firestore |
| Firmware upgrade path | ESP32 WiFi + HTTP/Firebase client | Roadmap: standalone cloud push, no laptop bridge |
| Backend | Firebase (Firestore + Cloud Functions) | Data storage, fusion logic, alert triggers |
| Fusion / anomaly detection | Rule-based + statistical (Cloud Functions) | Deliberately NOT deep learning, explainable and defensible |
| SMS | Fast2SMS | India-native, no-DLT Quick Route |
| Push notifications | Firebase Cloud Messaging | Multi-channel alert dispatch |
| Dashboard | React + Recharts | Live hazard-status panel + sensor trend charts |
| Connectivity (final vision) | LoRaWAN mesh | Roadmap, not built in prototype |

---

## 8. BILL OF MATERIALS (actual priced hardware — already purchased)

Purchased from Majestronicz Chennai, Invoice #2150, 07/09/2026, total **Rs.1,419**
for the complete single-node sensor set:

| Item | Qty | Price |
|---|---|---|
| ESP32 WROOM WiFi Module (38-pin, C-Type) | 1 | Rs.425 |
| MB102 Breadboard | 1 | Rs.69 |
| Ultrasonic Sensor - HC-SR04 | 1 | Rs.79 |
| MQ-2 Smoke Sensor | 1 | Rs.129 |
| Soil Moisture Sensor | 1 | Rs.54 |
| MQ-135 Air Quality Sensor | 1 | Rs.139 |
| Arduino Uno Cable | 1 | Rs.35 |
| M-F Jumper | 10 | Rs.15 |
| M-M Jumper | 10 | Rs.15 |
| F-F Jumper | 5 | Rs.7.50 |
| LED - Red / Yellow / Green | 5 each | Rs.5 each |
| DHT22 - Temp & Humidity Sensor Module | 1 | Rs.150 |
| Resistor Kit Box | 15 | Rs.7.50 |
| MPU 6050 Accelerometer Original IC | 1 | Rs.249 |
| Buzzer 5V | 2 | Rs.30 |

**Note:** The ADXL345 (listed in Section 3.1's pin table) is the accelerometer
actually wired and operational on the board. The MPU6050 on this invoice is an
unused spare — it is not populated on the current prototype. All code, firmware,
and documentation should reference ADXL345 only.

---

## 9. FIRESTORE DATA SCHEMA (define and lock this before writing any other code)

Single-node schema — no per-node partitioning needed at prototype stage.

```
/readings/{timestamp}
  - accel: number        // m/s^2, from accelerometer
  - temp: number          // C, from DHT22
  - distance: number      // cm, from HC-SR04
  - gasRaw: number        // 0-4095 ADC, from MQ-135
  - soilMoisture: number  // %, from soil sensor
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
  - sachetPayload: object  // structured JSON matching SACHET-style shape
  - timestamp: timestamp
```

---

## 10. FUSION LOGIC - IMPLEMENTATION SPEC

Implement as a Firebase Cloud Function triggered on new `/readings` writes.
Keep this rule-based and explainable - this is a deliberate design choice, not a
time-saving shortcut. It must be easy to explain step-by-step to a judge.

**This replaces the on-device flat decision tree (5 independent thresholds).** The
ESP32's job is now: read sensors, debounce, transmit clean raw values. All hazard
evaluation, including fusion, happens in this Cloud Function.

| Hazard | Logic |
|---|---|
| Earthquake | Standalone: total vector acceleration > 4.0 m/s^2 (baseline ~3.5 m/s^2). Keep debounce (2 consecutive reads). No cross-sensor correlation needed, this is a legitimately independent signal. |
| Fire / Gas Leak | Fusion: MQ-135 raw ADC >= 150 AND temperature (DHT22) rising within the same reading window, distinguishes a real fire/gas event from sensor drift or an isolated gas reading. |
| Flood | Fusion: HC-SR04 distance <= 10cm AND soil moisture also rising, tracked across the last several consecutive readings, distinguishes sustained rising flood risk from a one-off sensor glitch. |
| Landslide Risk | Fusion: soil moisture >= 70% AND sustained non-zero vibration trending upward, but staying below the earthquake threshold, distinguishes genuine landslide-precursor conditions from static saturated soil alone. |
| Compound | If two or more distinct hazard fusion rules fire within the same short time window, flag as a higher-priority "compound" event. |

Implementation requirements:
- Maintain a short rolling window (last 5-10 readings) to compute trend direction
  (rising/falling/flat) for temperature, soil moisture, and vibration, not just
  instantaneous values
- Every anomaly must carry a `rawConfidence` score (0-100), never just a boolean
- Calibrate numeric thresholds against real data where possible - CPCB CAAQMS
  baseline ranges for gas-related thresholds is a reasonable reference point

---

## 11. COMMUNITY VERIFICATION LOOP - IMPLEMENTATION SPEC

**This is the highest-risk piece of the build - start it early, not last.**

1. On anomaly creation, trigger an SMS via Fast2SMS to test phone numbers:
   `"[Hazard] risk detected near you. Reply YES if you observe this, NO if not."`
2. Set up a Fast2SMS inbound webhook to a Firebase Cloud Function (HTTP trigger)
   that receives replies and writes to `/verifications/{anomalyId}/responses/{phone}`
3. Confidence scoring: each YES increases `verifiedConfidence`, each NO decreases it
4. When `verifiedConfidence` crosses an escalation threshold (or a timeout passes
   with no denial), auto-write to `/alerts` and trigger multi-channel dispatch
5. **Build and test this against simulated/mocked anomaly triggers first** - this
   does not require real sensor hardware to fully build and test end-to-end

---

## 12. DASHBOARD - BUILD SPEC

**Implementation note:** Built as a zero-build standalone HTML file (Tailwind CSS CDN +
Chart.js + Lucide Icons + Firebase JS SDK) rather than a Create React App. This was an
intentional simplification for hackathon stage-demo reliability — the dashboard works by
opening a single file, with no npm install, no webpack, no build step. A React + Recharts
rewrite is roadmap if the project continues past SIH.

**Dual-mode architecture:**
- **Simulator mode (default):** Client-side scenario simulation for offline/stage demos
  with no Wi-Fi. 7 scenarios, speed controls (1x/2x/5x), play/pause.
- **Firebase Live mode:** Real-time Firestore `onSnapshot` listeners on `/readings`,
  `/anomalies`, and `/alerts`. Toggle via header switch. Firebase config saved to
  localStorage via in-app setup modal.

Features implemented:
- **Live hazard-status panel (primary view)** - 5 clear cards: Earthquake, Fire,
  Flood, Gas Leak, Landslide Risk. Each shows current reading, threshold, and
  status (normal / watch / alert). This is the strongest, most legible visual for
  a single-node build, lead with this, not a map.
- **Live sensor trend charts** (Chart.js) - genuinely continuous multi-sensor
  telemetry is a real strength here, show it.
- **Alert feed** - chronological, clearly distinguishing pending verification /
  community-verified / escalated states.
- **SACHET JSON Inspector** - modal with copy-to-clipboard for NDMA payload review.
- **Hardware line injector** - paste real ESP32 serial output to verify parser live.
- **Multi-node map** - omitted for the prototype per plan. If added later, must be
  labeled "Projected Multi-Node Deployment (Simulated)."
- Prioritize at-a-glance legibility over feature density, judges look at this for
  seconds, not minutes.

---

## 13. SIMULATED DATA GENERATOR (build this FIRST - unblocks everything)

Before real hardware integration is finished, write a script (Node.js or Python)
that writes realistic fake readings into `/readings` on an interval. This becomes
the permanent test harness:

- Simulate a flood: script `distance` falling + `soilMoisture` rising together
- Simulate a fire/gas event: script `gasRaw` spiking + `temp` rising together
- Simulate a landslide: script `soilMoisture` >= 70% sustained + mild upward-trending
  `accel` (below the earthquake threshold)
- Simulate an earthquake: script a sudden `accel` spike above 4.0 m/s^2

Everything downstream (fusion, verification, dashboard) must be built and fully
testable against this simulator alone. When real ESP32 readings are ready via the
serial bridge (Section 16), they write to the exact same schema, a drop-in
replacement, not a rewrite.

---

## 14. BUILD ORDER (do not reorder without good reason)

1. Firestore schema (Section 9) + simulated data generator (Section 13), unblocks
   everything downstream
2. Fusion/anomaly-detection logic (Section 10) against simulated data
3. Community verification loop (Section 11) against simulated anomalies, start
   early, it's the highest-risk piece
4. Alert dispatch + SACHET-style payload structure
5. Dashboard (Section 12), built against the same simulated stream
6. Serial-to-Firestore bridge (Section 16), connect real hardware
7. Full end-to-end rehearsal: physically trigger each hazard (shake for earthquake,
   heat source for fire, water for flood, gas source for leak, wet soil for
   landslide), confirm fusion, verification, dashboard, and alert all fire correctly
8. Record a working end-to-end run on video as a stage-demo fallback
9. (If time remains) Upgrade firmware to push directly over WiFi, removing the
   laptop serial bridge for a cleaner standalone demo

---

## 15. WHAT NOT TO BUILD (protect the team's time)

- No real LoRaWAN mesh for the prototype, explicitly roadmap, keep it that way in
  all messaging
- No custom-trained ML model, the rule-based fusion logic in Section 10 is
  sufficient and more defensible in front of judges than an unexplainable model
- No user authentication/role system unless significant time remains, not needed
  for a demo
- No native mobile app, SMS-based verification covers the "mobile-enabled" PS
  requirement for prototype stage; a full app is roadmap
- No Firebase Cloud Messaging (FCM) push notifications for the prototype — FCM
  requires registered device tokens from a client app, which we don't have yet.
  Alert dispatch uses Fast2SMS broadcast + dashboard live updates. FCM is roadmap
  alongside the mobile app.
- No real integration with SACHET's actual backend (not publicly accessible), a
  well-structured mock payload is the correct scope

---

## 16. HARDWARE-TO-CLOUD BRIDGE & HARDWARE NOTES

**Fast path (build first):** A Python/Node script on a laptop reads the ESP32's
serial output (115200 baud), parses each telemetry line, and pushes it into
`/readings` via the Firebase Admin SDK. No firmware changes required.

**Upgrade path (if time allows):** Add WiFi + an HTTP client/Firebase library
directly into ESP32 firmware so the node pushes to Firestore independently, needed
for a clean standalone demo without a laptop tether. Build only after the fast path
and everything downstream already works.

**Wiring note:** ESP32 + HC-SR04, watch for voltage mismatch. HC-SR04 Echo pin
output on some modules is 5V, which can be unsafe for ESP32 GPIO (3.3V logic); use
a voltage divider or logic-level shifter on the Echo line if needed.

**Reference repos** used for ESP32 + gas/air-quality sensor wiring and firmware
patterns only (GPIO mapping, UART sensor-reading approach), not a source of this
project's fusion, verification, or interoperability logic, which is original:
openairproject sensor-esp32 pattern, TitaniumMonkey ESP32-Air-Quality-Sensor pattern.

---

## 17. REFERENCE SOURCES (cite these accurately, do not embellish)

- IMD Multi-Hazard Early Warning DSS - Mission Mausam, Jan 2024
- NDMA - SACHET national alert dissemination system
- IIT Mandi low-cost AI landslide early-warning network (60+ sites, Himachal Pradesh)
- Aurassure - IIT Bombay urban flood monitoring deployment
- IMD / data.gov.in - historical rainfall data
- CPCB CAAQMS - continuous air-quality monitoring data
- NASA FIRMS - near real-time fire/hotspot satellite detection
- Central Water Commission (CWC) - river/hydrological observation data

---

## 18. ACCEPTANCE CRITERIA (demo-ready checklist)

- [ ] Simulator can trigger all 5 hazard types plus at least 1 compound case
- [ ] Fusion Cloud Function correctly classifies each simulated scenario with a
      sensible confidence score
- [ ] SMS verification round-trip works end-to-end on a real phone
- [ ] Dashboard updates live within a few seconds of a new anomaly/alert
- [ ] A generated `sachetPayload` object is inspectable and well-structured
- [ ] Real ESP32 hardware data flows into the pipeline via the serial bridge
- [ ] A full physical trigger-to-dashboard-to-alert run has been recorded on video
- [ ] All cost figures, node counts, and capability claims across the dashboard,
      pitch deck, and this document match what is actually built

---

*This document should be updated whenever scope, cost figures, or architecture
decisions change. Keep Section 6 (Honesty Rules) and Section 2 (existing prior art)
in mind for every piece of copy, code comment, or generated content, consistency
across the deck, this document, and the actual build is what makes the project
defensible in front of judges.*
