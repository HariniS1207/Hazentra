# Hazentra — Project Reference (CLAUDE.md)

**Team:** Hacktrix (Allocious Franklin R, Akash N, Harini S, Geethapriya, Malini, Mohamed Al Silmi)
**Event:** Smart India Hackathon 2026 — Problem Statement 26178
**Official PS Title:** AI-Powered Environmental Intelligence Network
**Theme:** Disaster Management | **Category:** Hardware | **Sponsor:** Qualcomm Inc

This document is the single source of truth for anyone (human or AI) working on this
project. Read it before writing any code. It covers what we're building, why, what
makes it different from what already exists, and exactly how the software should be
architected and built.

---

## 1. THE PROBLEM

India faces recurring, high-damage environmental hazards — urban and river flooding,
forest fires, hazardous air pollution, extreme heat, landslides, and industrial
chemical leaks — concentrated in states like Assam, Bihar, Kerala, Maharashtra,
Uttarakhand, Himachal Pradesh, and central Indian forest belts. Climate change is
increasing both frequency and intensity.

Three specific, validated gaps exist in how India currently handles this:

1. **No ground-truth layer.** National systems (IMD's Multi-Hazard Early Warning DSS,
   NDMA's SACHET) forecast and broadcast at district/regional granularity. Neither has
   real-time street- or village-level sensing, and neither verifies whether a warning
   matches what's actually happening on the ground before or after dissemination.

2. **Isolated, single-hazard detection.** Even real, deployed low-cost systems (e.g.
   IIT Mandi's AI landslide sensor network, 60+ sites in Himachal Pradesh, >90%
   accuracy, 3-hour advance warning) detect one hazard type in isolation. Nobody
   correlates signals *across* hazard types (e.g. rainfall + water level + soil
   moisture together, or smoke + wind direction across multiple nodes) to catch
   compound or fast-developing risk patterns.

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
- A low-cost, community-deployable ground sensor network that performs **real-time
  cross-hazard correlation** (not single-hazard, not satellite-scale mapping).
- Any system — commercial or government — that runs a **two-way community
  verification loop** (SMS confirm/deny adjusting alert confidence) integrated with
  ground sensors.
- Any system explicitly architected to **feed verified, structured, ground-truth
  alerts into SACHET/NDMA** as a last-mile input layer, rather than operating as an
  isolated parallel system.

**Conclusion used in all our messaging:** Hazentra does not claim to be the first
environmental sensor network or the first AI early-warning system. It claims to be
the first to combine low-cost ground sensing + real-time cross-hazard fusion +
community-verified confidence scoring + explicit integration into India's existing
official warning infrastructure, in one system. Always position it this way —
"complementary, not competitive" — in any generated copy, pitch text, or UI language.

---

## 3. OUR SOLUTION

Hazentra is a distributed network of solar-powered smart sensor nodes deployed at
flood-prone rivers, forests, industrial zones, and vulnerable communities. Each node:

- Senses locally with on-device edge inference (water level, rainfall, PM2.5/PM10,
  gas/smoke, temperature, humidity, soil moisture/vibration)
- Continues operating without internet (local buffering, SMS fallback)
- Feeds into an AI fusion engine that correlates signals **across hazard types and
  across nodes**, not single-sensor threshold alarms
- Escalates only verified, high-confidence alerts — verified via a real-time SMS
  confirm/deny loop with nearby residents — through multiple channels (SMS, app,
  dashboard)
- Outputs a structured, API-ready payload designed for direct handoff into NDMA's
  SACHET pipeline

Final-vision architecture (target state, follows the PS's full expected solution):
LoRaWAN mesh connectivity across nodes, solar+battery power, GIS risk mapping,
multi-hazard detection (flood, fire, air quality, extreme heat, landslide precursors,
industrial leaks), full mobile app for citizens and field responders, and centralized
authority dashboard.

---

## 4. INNOVATION STACK (the four things to keep provably real, not just claimed)

1. **Cross-Hazard Fusion Engine** — correlates rainfall + water-level rate-of-change +
   soil moisture to distinguish flash-flood vs. slow-rise flood vs. landslide
   precursor; correlates smoke/gas sharpness-of-spike + wind direction across nodes
   to distinguish a fire event from ambient pollution drift. This must be *actually
   implemented* as explainable logic — not a black-box model, not a claim without
   code behind it.
2. **Community Verification Layer** — SMS-based confirm/deny loop that adjusts a
   numeric confidence score before an alert escalates. This is our strongest,
   most memorable, most defensible differentiator — prioritize building and
   demoing this working end-to-end over any other feature.
3. **Radical Cost & Openness** — real target cost ~₹5,800–7,200 per node (see
   Section 8 for the actual priced BOM — do not use outdated ₹4,000–5,000 figures
   still floating in some earlier drafts), fully open BOM and design, no vendor
   lock-in, panchayat/NGO self-deployable.
4. **Official-Pipeline Interoperability** — every escalated alert is structured to
   match a SACHET/NDMA-style payload shape. Even in the prototype, generate a real,
   inspectable JSON object with this shape — it makes the "interoperability" claim
   concrete and demoable, not just a slide bullet.

---

## 5. IMPACT (how to talk about it, and what to actually measure)

- **Direct:** closes the last-mile ground-truth gap — hyperlocal (street/village)
  detection vs. district/block-level granularity from national systems.
- **Economic:** order-of-magnitude cheaper than institutional-grade systems —
  realistically ownable by panchayats and NGOs, not just city corporations.
- **Trust & adoption:** community verification directly targets the
  research-documented root cause of last-mile warning failure — false-alarm
  fatigue and low trust — not just a detection-accuracy problem.
- **Systemic:** designed to strengthen (not duplicate) Mission Mausam, SACHET, and
  NDMA's existing investments.

When generating any pitch copy, dashboard language, or reports: always frame impact
in terms of what is **measurable and demoable** (e.g. "reduced false-positive rate
in our test run," "2 working nodes, real historical-data-calibrated thresholds") —
never invent adoption numbers, deployment scale, or accuracy percentages that
haven't actually been measured in this project.

---

## 6. HONESTY RULES (apply these everywhere — pitch, docs, code comments, UI copy)

- We have built and demonstrated a **2-node physical prototype** (flood node +
  air-quality node) — say this explicitly, do not imply more nodes exist unless
  they actually do.
- Full LoRaWAN mesh, full multi-hazard sensor coverage (heat, landslide, industrial
  leak), and the mobile app are **roadmap / next-phase**, not built yet — always
  distinguish "what we built" from "what the architecture is designed to scale to."
- Any dashboard mockup showing more nodes than physically exist must be clearly
  labeled as a projected/simulated fleet view, not presented as live data.
- Cost figures used anywhere in the project (pitch deck, dashboard, docs) must match
  the actual priced BOM in Section 8, not earlier draft estimates.

---

## 7. TECH STACK

| Layer | Technology | Notes |
|---|---|---|
| Node compute | ESP32 (WROOM, 38-pin) | 2 nodes for prototype: flood node, air-quality node |
| Flood sensing | HC-SR04 ultrasonic | Water-level / distance sensing |
| Air-quality sensing | MQ-135 | Gas-based air-quality proxy (budget swap from PMS7003 laser sensor) |
| Fire/smoke signal | MQ-2 | Smoke/gas detection, feeds fusion logic |
| Environmental context | DHT22 | Temp/humidity, both nodes |
| Stretch sensors | Soil moisture sensor, MPU6050 accelerometer | Available in current hardware kit — optional landslide/vibration precursor signal if time allows |
| Connectivity (prototype) | WiFi (ESP32 built-in) | Primary path to Firebase |
| Connectivity (fallback) | SMS (Fast2SMS) | India-native, no-DLT Quick Route for fast setup, ~₹0.14–0.25/SMS |
| Connectivity (final vision) | LoRaWAN mesh | Roadmap — not built in prototype |
| Backend | Firebase (Firestore + Cloud Functions) | Data storage, fusion logic, alert triggers |
| Fusion / anomaly detection | Rule-based + statistical (JavaScript/Python in Cloud Functions) | NOT deep learning — deliberately explainable and defensible |
| Dashboard frontend | React + Leaflet (map) + Recharts (trends) | Web dashboard for authorities/team demo |
| Mobile / citizen interface | SMS-based for prototype; app is roadmap | Keep prototype scope realistic |
| Alert dispatch | Firebase Cloud Messaging (push) + Fast2SMS (SMS) | Multi-channel dispatch |

---

## 8. BILL OF MATERIALS (actual priced hardware — already purchased)

Purchased from Majestronicz Chennai, Invoice #2150, 07/09/2026, total ₹1,419
(covers one combined sensor set — a second ESP32 + duplicate sensor set is needed
for the full 2-node architecture):

| Item | Qty | Price |
|---|---|---|
| ESP32 WROOM WiFi Module (38-pin, C-Type) | 1 | ₹425 |
| MB102 Breadboard | 1 | ₹69 |
| HC-SR04 Ultrasonic Sensor | 1 | ₹79 |
| MQ-2 Smoke Sensor | 1 | ₹129 |
| Soil Moisture Sensor | 1 | ₹54 |
| MQ-135 Air Quality Sensor | 1 | ₹139 |
| Arduino Uno Cable | 1 | ₹35 |
| Jumper wires (M-F, M-M, F-F) | 25 | ₹37.50 |
| LEDs (Red/Yellow/Green) | 15 | ₹15 |
| DHT22 Temp/Humidity Module | 1 | ₹150 |
| Resistor Kit Box | 15 | ₹7.50 |
| MPU6050 Accelerometer | 1 | ₹249 |
| Buzzer 5V | 2 | ₹30 |

**Action needed:** duplicate the ESP32 + core sensor set (HC-SR04, DHT22 minimum)
to build the second node — current purchase only fully equips one combined node.

---

## 9. FIRESTORE DATA SCHEMA (define and lock this before writing any other code)

```
/nodes/{nodeId}
  - name: string
  - type: "flood" | "air_quality"
  - lat: number, lng: number
  - status: "online" | "offline"
  - lastSeen: timestamp

/readings/{nodeId}/logs/{timestamp}
  - waterLevel, rainfall, pm25, gas, temp, humidity, soilMoisture, vibration
  - timestamp

/anomalies/{anomalyId}
  - nodeId: string
  - type: "flood" | "fire" | "air_quality" | "compound"
  - rawConfidence: number (0-100)
  - verifiedConfidence: number (0-100)
  - status: "pending" | "verified" | "denied" | "escalated"
  - timestamp

/verifications/{anomalyId}/responses/{phoneNumber}
  - response: "YES" | "NO"
  - timestamp

/alerts/{alertId}
  - anomalyId: string
  - hazardType: string
  - confidenceScore: number
  - message: string
  - channelsSent: string[]
  - sachetPayload: object  // structured JSON matching SACHET-style shape
  - timestamp
```

---

## 10. FUSION LOGIC — IMPLEMENTATION SPEC

Implement as a Firebase Cloud Function triggered on new `/readings` writes.
Keep this rule-based and explainable — this is a deliberate design choice, not a
time-saving shortcut. It must be easy to explain step-by-step to a judge.

**Flood detection:**
- Track water-level rate-of-change over the last N readings (not just absolute level)
- Combine with rainfall/humidity trend direction
- If rate-of-rise exceeds a calibrated threshold AND rainfall is trending upward →
  flag anomaly, type "flood", with a computed severity/confidence score
- Calibrate thresholds against real IMD historical rainfall data (data.gov.in) —
  do not use arbitrary numbers

**Fire/air detection:**
- Track PM2.5/gas *sharpness of spike* — a sudden jump over 1-2 readings suggests
  fire/smoke; a slow gradual drift suggests ambient pollution
- Calibrate against real CPCB CAAQMS baseline data
- Flag anomaly, type "fire" or "air_quality" depending on signal shape

**Cross-hazard fusion (the core differentiator — must be genuinely implemented):**
- If a flood-type signal AND an air-quality/fire-type signal both fire within the
  same time window from geographically nearby nodes → flag as "compound" risk,
  a distinct, higher-priority alert category
- This is the concrete evidence behind the "cross-hazard fusion" claim — do not
  ship this as two independent, unconnected detectors

Every anomaly must carry a `rawConfidence` score (0-100), never just a boolean.

---

## 11. COMMUNITY VERIFICATION LOOP — IMPLEMENTATION SPEC

**This is the highest-risk piece of the build — start it early, not last.**

1. On anomaly creation, trigger an SMS via Fast2SMS to test phone numbers:
   `"[Hazard] risk detected near you. Reply YES if you observe this, NO if not."`
2. Set up a Fast2SMS inbound webhook → Firebase Cloud Function (HTTP trigger) that
   receives replies and writes to `/verifications/{anomalyId}/responses/{phone}`
3. Confidence scoring: each YES increases `verifiedConfidence`, each NO decreases it
4. When `verifiedConfidence` crosses an escalation threshold (or a timeout passes
   with no denial), auto-write to `/alerts` and trigger multi-channel dispatch
5. **Build and test this against simulated/mocked anomaly triggers first** — this
   does not require real sensor hardware to fully build and test end-to-end

---

## 12. DASHBOARD — BUILD SPEC

React app, built and testable against simulated data from day one (see Section 13).

- **Map view** (Leaflet): node markers, color-coded by current status/confidence
  (green = normal, yellow = pending verification, red = escalated)
- **Live readings panel**: per-node current values + simple trend sparklines
  (Recharts)
- **Alert feed**: chronological, clearly distinguishing "pending verification" /
  "community-verified" / "escalated" states
- **Node health strip**: battery, connectivity, last-seen per node — if showing
  more nodes than physically exist, label explicitly as "Projected Fleet View
  (Simulated)," never presented as live data
- Prioritize at-a-glance legibility over feature density — judges look at this for
  seconds, not minutes

---

## 13. SIMULATED DATA GENERATOR (build this FIRST — unblocks everything)

Before any hardware is ready, write a script (Node.js or Python) that writes
realistic fake readings into `/readings` on an interval. Base value ranges on real
IMD/CPCB historical data so thresholds are meaningful, not arbitrary. This becomes
the permanent test harness — simulate a flood by scripting rising water-level
values, and the fusion engine, verification loop, and dashboard should all react
correctly before a single real sensor is wired in. When real ESP32 readings are
ready, they should write to the exact same schema and be a near drop-in replacement.

---

## 14. BUILD ORDER (do not reorder without good reason)

1. Firestore schema (Section 9) + simulated data generator (Section 13) — unblocks
   everything downstream
2. Fusion/anomaly-detection logic (Section 10) against simulated data
3. Community verification loop (Section 11) against simulated anomalies — start
   early, it's the highest-risk piece
4. Dashboard (Section 12), built against the same simulated stream
5. Hardware wiring + firmware in parallel (see hardware notes below)
6. Swap simulator inputs for real ESP32 sensor readings once hardware is ready
7. Full end-to-end rehearsal: simulate a flood and a smoke event physically,
   confirm fusion → SMS verification → dashboard update → alert escalation all
   fire correctly, live
8. Record a working end-to-end run on video as a stage-demo fallback

---

## 15. WHAT NOT TO BUILD (protect the team's time)

- No real LoRaWAN mesh for the prototype — explicitly roadmap, keep it that way in
  all messaging
- No custom-trained ML model — the rule-based fusion logic in Section 10 is
  sufficient and more defensible in front of judges than an unexplainable model
- No user authentication/role system unless significant time remains — not needed
  for a demo
- No native mobile app — SMS-based verification covers the "mobile-enabled" PS
  requirement for prototype stage; a full app is roadmap

---

## 16. HARDWARE NOTES (for reference while software work proceeds in parallel)

- ESP32 + HC-SR04: watch for voltage mismatch — HC-SR04 Echo pin output on some
  modules is 5V, which can be unsafe for ESP32 GPIO (3.3V logic); use a voltage
  divider or logic-level shifter on the Echo line if needed
- Current hardware purchase (Section 8) equips one combined sensor node; a second
  ESP32 + duplicate core sensors (HC-SR04, DHT22 minimum) are needed to realize the
  2-node architecture this whole software plan is built around
- Reference repos for ESP32 + gas/air-quality sensor wiring and firmware (used as
  implementation reference only — not a source of this project's fusion,
  verification, or interoperability logic, which is original): openairproject
  sensor-esp32 pattern, TitaniumMonkey ESP32-Air-Quality-Sensor pattern (GPIO
  mapping and UART sensor-reading approach)

---

## 17. REFERENCE SOURCES (cite these accurately, do not embellish)

- IMD Multi-Hazard Early Warning DSS — Mission Mausam, Jan 2024
- NDMA – SACHET national alert dissemination system
- IIT Mandi low-cost AI landslide early-warning network (60+ sites, Himachal Pradesh)
- Aurassure – IIT Bombay urban flood monitoring deployment
- IMD / data.gov.in — historical rainfall data
- CPCB CAAQMS — continuous air-quality monitoring data
- NASA FIRMS — near real-time fire/hotspot satellite detection
- Central Water Commission (CWC) — river/hydrological observation data

---

*This document should be updated whenever scope, cost figures, or architecture
decisions change. Keep Section 6 (Honesty Rules) and Section 2 (existing prior art)
in mind for every piece of copy, code comment, or generated content — consistency
across the deck, this document, and the actual build is what makes the project
defensible in front of judges.*
