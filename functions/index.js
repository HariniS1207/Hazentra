/**
 * Hazentra Firebase Cloud Functions — Hardened Production Stack
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * 1. onReadingWritten         : Firestore Trigger (/readings/{timestamp}) -> Cross-Hazard Fusion
 * 2. onAnomalyCreated          : Firestore Trigger (/anomalies/{anomalyId}) -> Fast2SMS outbound & phone session tracking
 * 3. fast2smsWebhook           : HTTP Webhook -> Resolves citizen YES/NO replies (with phone session lookup) & recalculates confidence
 * 4. checkVerificationTimeouts : Scheduled Cron (every 2 mins) -> Auto-escalates pending anomalies if timeout passes with no denial
 * 5. onAlertCreated            : Firestore Trigger (/alerts/{alertId}) -> Broadcasts alert SMS via Fast2SMS & logs SACHET dispatch
 */

require("dotenv").config();
const functions = require("firebase-functions");
const admin = require("firebase-admin");
const axios = require("axios");

if (!admin.apps.length) {
  admin.initializeApp();
}
const db = admin.firestore();

// ============================================================================
// CONFIGURATION & CALIBRATION (CLAUDE.md Section 9 & 10)
// ============================================================================
const CONFIG = {
  nodeId: "hazentra-node-01",
  location: {
    lat: 26.1445,
    lng: 91.7362,
    description: "Guwahati Integrated Monitoring Site",
  },
  thresholds: {
    earthquakeAccel: 4.0,       // m/s^2 (baseline ~3.5)
    gasBaseThreshold: 150,      // Spec threshold (CLAUDE.md Section 10)
    gasSpikeDelta: 25,          // Delta above ambient to avoid false alarms from bench 147-161 range
    floodDist: 10.0,            // cm (sensor distance to water surface)
    landslideSoil: 70.0,        // % saturation
    landslideAccelMin: 3.65,    // m/s^2 micro-tremor precursor
    landslideAccelMax: 4.0,     // below quake threshold
  },
  verification: {
    // Strictly load from environment variable or Firebase Functions config — NEVER hardcode in source
    fast2smsApiKey: process.env.FAST2SMS_API_KEY || (functions.config().fast2sms && functions.config().fast2sms.key) || "",
    testNumbers: ["9876543210", "9876543211", "9876543212"],
    broadcastAlertNumbers: ["9876543210", "9876543211", "9876543212"],
    yesWeight: 8.0,
    noWeight: -12.0,
    escalateThreshold: 65.0,
    timeoutMinutes: 5,          // 5 minutes timeout window
  },
};


// ============================================================================
// 1. CLOUD FUSION ENGINE (Triggered on new /readings doc write)
// ============================================================================
exports.onReadingWritten = functions.firestore
  .document("readings/{timestamp}")
  .onCreate(async (snapshot, context) => {
    const current = snapshot.data();
    if (!current) return null;

    // Fetch the last 9 readings to build a 10-reading rolling window
    const recentSnap = await db.collection("readings")
      .orderBy("timestamp", "desc")
      .limit(10)
      .get();

    const window = recentSnap.docs.map(d => d.data()).reverse();
    if (window.length < 2) return null;

    const oldest = window[0];
    const prev = window[window.length - 2];

    const tempTrend = current.temp - oldest.temp;
    const soilTrend = current.soilMoisture - oldest.soilMoisture;
    const accelTrend = current.accel - oldest.accel;
    const gasTrend = current.gasRaw - oldest.gasRaw;

    const detected = [];

    // Rule 1: Earthquake (Standalone, accel > 4.0, debounce across 2 consecutive readings)
    if (current.accel > CONFIG.thresholds.earthquakeAccel && prev.accel > CONFIG.thresholds.earthquakeAccel) {
      const conf = Math.min(98.0, 70.0 + (current.accel - 4.0) * 20.0);
      detected.push({
        type: "earthquake",
        confidence: Math.round(conf * 10) / 10,
        reason: `Seismic acceleration ${current.accel} m/s^2 exceeded 4.0 m/s^2 across 2 consecutive readings`,
      });
    }

    // Rule 2 & 4: Fire vs Gas Leak (Spec: Gas >= 150 + spike above baseline)
    const isGasAnomalous = current.gasRaw >= CONFIG.thresholds.gasBaseThreshold &&
      (gasTrend >= CONFIG.thresholds.gasSpikeDelta || current.gasRaw >= 180);

    if (isGasAnomalous) {
      // Fire: Gas spike correlated with rising temperature (tempTrend > 0.3)
      if (tempTrend > 0.3) {
        const conf = Math.min(96.0, 60.0 + (current.gasRaw - 150) / 8.0 + tempTrend * 15.0);
        detected.push({
          type: "fire",
          confidence: Math.round(conf * 10) / 10,
          reason: `Gas spike (${current.gasRaw} ADC) correlated with thermal rise (+${tempTrend.toFixed(1)} C trend)`,
        });
      } else {
        // Gas Leak: Gas spike without thermal rise (flat or falling temperature — no dead zone!)
        const conf = Math.min(92.0, 55.0 + (current.gasRaw - 150) / 10.0);
        detected.push({
          type: "gas_leak",
          confidence: Math.round(conf * 10) / 10,
          reason: `Isolated toxic gas spike (${current.gasRaw} ADC) with stable ambient temperature (${current.temp} C)`,
        });
      }
    }

    // Rule 3: Flood (Distance <= 10cm across 2 reads AND soil moisture saturated/rising)
    if (current.distance <= CONFIG.thresholds.floodDist && prev.distance <= CONFIG.thresholds.floodDist) {
      if (soilTrend > 1.0 || current.soilMoisture >= 70.0) {
        const conf = Math.min(99.0, 65.0 + (10.0 - current.distance) * 5.0 + (current.soilMoisture - 70) * 0.5);
        detected.push({
          type: "flood",
          confidence: Math.round(conf * 10) / 10,
          reason: `Water surface distance critical (${current.distance} cm across 2 reads) with ground saturation (${current.soilMoisture}%)`,
        });
      }
    }

    // Rule 5: Landslide (Soil >= 70% AND slope micro-tremor 3.65 - 4.0 m/s^2)
    if (current.soilMoisture >= CONFIG.thresholds.landslideSoil) {
      if (current.accel >= CONFIG.thresholds.landslideAccelMin &&
          current.accel < CONFIG.thresholds.landslideAccelMax &&
          accelTrend > 0.03) {
        const conf = Math.min(88.0, 50.0 + (current.soilMoisture - 70) * 1.0 + (current.accel - 3.5) * 50);
        detected.push({
          type: "landslide",
          confidence: Math.round(conf * 10) / 10,
          reason: `Soil saturation critical (${current.soilMoisture}%) with slope micro-tremors (${current.accel} m/s^2)`,
        });
      }
    }

    if (detected.length === 0) return null;

    // Check for 90-second rolling window Compound Event (CLAUDE.md Section 10)
    let finalType, finalConf, finalReason;
    const ninetySecAgo = new Date(new Date(current.timestamp).getTime() - 90 * 1000);

    const recentHazardsSnap = await db.collection("anomalies")
      .where("timestamp", ">=", ninetySecAgo)
      .get();

    const distinctPastTypes = new Set();
    recentHazardsSnap.forEach(d => {
      const atype = d.data().type;
      if (atype !== "compound") distinctPastTypes.add(atype);
    });
    detected.forEach(d => distinctPastTypes.add(d.type));

    if (distinctPastTypes.size >= 2) {
      finalType = "compound";
      const maxIndividualConf = Math.max(...detected.map(d => d.confidence), 75.0);
      finalConf = Math.min(99.0, maxIndividualConf + 12.0);
      finalReason = "Cross-Hazard Correlation (90s window): " + Array.from(distinctPastTypes).map(t => t.toUpperCase()).join(" + ");
    } else {
      finalType = detected[0].type;
      finalConf = detected[0].confidence;
      finalReason = detected[0].reason;
    }

    // De-duplication check: avoid duplicate anomaly within 3 minutes for same hazard
    const threeMinAgo = new Date(new Date(current.timestamp).getTime() - 3 * 60 * 1000);
    const recentAnomSnap = await db.collection("anomalies")
      .where("type", "==", finalType)
      .where("timestamp", ">=", threeMinAgo)
      .limit(1)
      .get();

    if (!recentAnomSnap.empty) {
      console.log(`[FUSION] De-duplicated ${finalType} anomaly within 3m window`);
      return null;
    }

    const anomalyId = `anomaly-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
    const anomalyDoc = {
      anomalyId,
      nodeId: CONFIG.nodeId,
      type: finalType,
      subHazards: Array.from(distinctPastTypes),
      rawConfidence: Math.round(finalConf * 10) / 10,
      verifiedConfidence: Math.round(finalConf * 10) / 10,
      status: "pending",
      timestamp: current.timestamp,
      reason: finalReason,
      snapshot: current,
    };

    console.log(`[FUSION] Anomaly Recorded: ${finalType} (Confidence: ${anomalyDoc.rawConfidence}%)`);
    // FIXED: Use .doc() instead of .document()
    await db.collection("anomalies").doc(anomalyId).set(anomalyDoc);
    return anomalyDoc;
  });


// ============================================================================
// 2. COMMUNITY VERIFICATION LOOP (Fast2SMS Outbound + Session Tracking)
// ============================================================================
exports.onAnomalyCreated = functions.firestore
  .document("anomalies/{anomalyId}")
  .onCreate(async (snapshot, context) => {
    const anomaly = snapshot.data();
    if (!anomaly) return null;

    const aid = context.params.anomalyId;
    const msg = `[HAZENTRA] ${anomaly.type.toUpperCase()} risk detected near ${CONFIG.location.description}. Reply YES to verify, NO if false. Ref: ${aid}`;

    console.log(`[SMS-DISPATCH] Dispatching verification SMS for ${aid}...`);

    // Record active session for each test phone so reply with bare "YES"/"NO" automatically links to this anomaly
    const batch = db.batch();
    const nowIso = new Date().toISOString();
    CONFIG.verification.testNumbers.forEach(phone => {
      const cleanPhone = phone.replace(/[^0-9]/g, "");
      // FIXED: Use .doc()
      const sessRef = db.collection("active_verifications").doc(cleanPhone);
      batch.set(sessRef, {
        anomalyId: aid,
        hazardType: anomaly.type,
        dispatchedAt: nowIso,
        expiresAt: new Date(Date.now() + CONFIG.verification.timeoutMinutes * 60 * 1000).toISOString(),
      });
    });
    await batch.commit();

    // Outbound Fast2SMS Quick Route call
    if (CONFIG.verification.fast2smsApiKey) {
      try {
        const numbers = CONFIG.verification.testNumbers.join(",");
        await axios.post("https://www.fast2sms.com/dev/bulkV2", {
          route: "q",
          message: msg,
          language: "english",
          flash: 0,
          numbers: numbers,
        }, {
          headers: {
            "authorization": CONFIG.verification.fast2smsApiKey,
            "Content-Type": "application/json",
          },
        });
        console.log(`[SMS-DISPATCH] Fast2SMS sent successfully to ${numbers}`);
      } catch (err) {
        console.error(`[SMS-DISPATCH] Fast2SMS API Error:`, err.response ? err.response.data : err.message);
      }
    } else {
      console.log(`[SMS-MOCK] Simulated Fast2SMS dispatch (FAST2SMS_API_KEY not configured): "${msg}"`);
    }

    return null;
  });


// ============================================================================
// 3. FAST2SMS INBOUND WEBHOOK (Community Reply Processor)
// ============================================================================
exports.fast2smsWebhook = functions.https.onRequest(async (req, res) => {
  try {
    const payload = req.body || req.query;
    const senderRaw = payload.sender || payload.phone || payload.mobile || "unknown";
    const sender = senderRaw.replace(/[^0-9]/g, "");
    const text = (payload.message || payload.text || "").trim().toUpperCase();

    // 1. Try resolving anomalyId from explicit text or URL param
    let anomalyId = payload.anomalyId || (text.match(/anomaly-[a-z0-9-]+/i) || [])[0];

    // 2. If no anomalyId in message (typical user texting "YES" or "NO"), look up active session
    if (!anomalyId && sender) {
      // FIXED: Use .doc()
      const sessSnap = await db.collection("active_verifications").doc(sender).get();
      if (sessSnap.exists) {
        const sdata = sessSnap.data();
        if (new Date() < new Date(sdata.expiresAt)) {
          anomalyId = sdata.anomalyId;
          console.log(`[WEBHOOK] Resolved bare reply from ${sender} to active anomaly: ${anomalyId}`);
        }
      }
    }

    if (!anomalyId) {
      return res.status(400).json({ error: "No active anomaly session found for this number or message." });
    }

    const responseVote = text.includes("YES") ? "YES" : text.includes("NO") ? "NO" : null;
    if (!responseVote) {
      return res.status(400).json({ error: "Invalid response, must contain YES or NO" });
    }

    // FIXED: Use .doc()
    const anomRef = db.collection("anomalies").doc(anomalyId);
    const anomDoc = await anomRef.get();
    if (!anomDoc.exists) {
      return res.status(404).json({ error: "Anomaly not found" });
    }

    const anomaly = anomDoc.data();
    const nowIso = new Date().toISOString();

    // 1. Record individual response: /verifications/{anomalyId}/responses/{phone}
    // FIXED: Use .doc()
    await db.collection("verifications").doc(anomalyId)
      .collection("responses").doc(sender)
      .set({
        response: responseVote,
        timestamp: nowIso,
        rawText: text,
      });

    // Also touch parent document so /verifications is discoverable
    await db.collection("verifications").doc(anomalyId).set({
      anomalyId,
      lastResponseAt: nowIso,
    }, { merge: true });

    // 2. Fetch all votes for this anomaly
    // FIXED: Use .doc()
    const votesSnap = await db.collection("verifications").doc(anomalyId)
      .collection("responses").get();

    let yesVotes = 0;
    let noVotes = 0;
    votesSnap.forEach(d => {
      const v = d.data().response;
      if (v === "YES") yesVotes++;
      if (v === "NO") noVotes++;
    });

    // Confidence recalculation: +8 per YES, -12 per NO
    const adjustedConfidence = Math.max(0, Math.min(100,
      anomaly.rawConfidence + (yesVotes * CONFIG.verification.yesWeight) + (noVotes * CONFIG.verification.noWeight)
    ));

    const isEscalated = adjustedConfidence >= CONFIG.verification.escalateThreshold;
    const updatedStatus = isEscalated ? "escalated" : (noVotes > yesVotes ? "denied" : "pending");

    await anomRef.update({
      verifiedConfidence: Math.round(adjustedConfidence * 10) / 10,
      status: updatedStatus,
      lastVerificationUpdate: nowIso,
    });

    // 3. If escalated and not yet created as alert, escalate to /alerts
    if (isEscalated && anomaly.status !== "escalated") {
      const alertId = `alert-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
      let severity = "warning";
      if (adjustedConfidence > 85.0) severity = "danger";
      else if (adjustedConfidence < 70.0) severity = "watch";

      const sachetPayload = {
        version: "1.0",
        source: "hazentra",
        sourceNodeId: CONFIG.nodeId,
        hazardType: anomaly.type,
        severity: severity,
        confidence: Math.round(adjustedConfidence * 10) / 10,
        verificationStatus: "verified",
        location: CONFIG.location,
        timestamp: nowIso,
        sensorData: anomaly.snapshot || {},
        // FIXED: Use toUpperCase() instead of .upper()
        message: `HAZENTRA ${anomaly.type.toUpperCase()} ${severity.toUpperCase()} - Confidence ${adjustedConfidence.toFixed(0)}% - Community Verified (${yesVotes}Y/${noVotes}N)`,
      };

      // FIXED: Use .doc()
      await db.collection("alerts").doc(alertId).set({
        alertId,
        anomalyId,
        hazardType: anomaly.type,
        confidenceScore: Math.round(adjustedConfidence * 10) / 10,
        message: sachetPayload.message,
        channelsSent: ["sms_fast2sms", "dashboard_live"],
        sachetPayload,
        timestamp: nowIso,
      });

      console.log(`[ALERT] Escalated Alert created: ${alertId} (${anomaly.type}, ${adjustedConfidence}%)`);
    }

    return res.status(200).json({
      success: true,
      anomalyId,
      sender,
      response: responseVote,
      verifiedConfidence: adjustedConfidence,
      status: updatedStatus,
    });
  } catch (err) {
    console.error("[WEBHOOK-ERROR]", err);
    return res.status(500).json({ error: err.message });
  }
});


// ============================================================================
// 4. VERIFICATION TIMEOUT ESCALATION (Scheduled Cron or HTTP Trigger)
// ============================================================================
exports.checkVerificationTimeouts = functions.pubsub
  .schedule("every 2 minutes")
  .onRun(async (context) => {
    const timeoutCutoff = new Date(Date.now() - CONFIG.verification.timeoutMinutes * 60 * 1000);

    const pendingSnap = await db.collection("anomalies")
      .where("status", "==", "pending")
      .where("timestamp", "<=", timeoutCutoff)
      .get();

    if (pendingSnap.empty) return null;

    console.log(`[TIMEOUT-CHECK] Found ${pendingSnap.size} timed-out pending anomalies`);

    for (const anomDoc of pendingSnap.docs) {
      const a = anomDoc.data();
      const aid = anomDoc.id;

      // Check if there was any NO response
      const responsesSnap = await db.collection("verifications").doc(aid)
        .collection("responses").get();

      let hasDenial = false;
      let yesCount = 0;
      responsesSnap.forEach(d => {
        if (d.data().response === "NO") hasDenial = true;
        if (d.data().response === "YES") yesCount++;
      });

      if (!hasDenial) {
        // Spec rule: Timeout passes with no denial -> rawConfidence stands as fallback, auto-escalate!
        const alertId = `alert-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
        const severity = a.rawConfidence > 85.0 ? "danger" : "warning";
        const nowIso = new Date().toISOString();

        const sachetPayload = {
          version: "1.0",
          source: "hazentra",
          sourceNodeId: CONFIG.nodeId,
          hazardType: a.type,
          severity,
          confidence: a.rawConfidence,
          verificationStatus: "verified_by_timeout",
          location: CONFIG.location,
          timestamp: nowIso,
          sensorData: a.snapshot || {},
          message: `HAZENTRA ${a.type.toUpperCase()} ${severity.toUpperCase()} - Confidence ${a.rawConfidence}% - Auto-verified by timeout (No community denials)`,
        };

        await anomDoc.ref.update({
          status: "escalated",
          verifiedConfidence: a.rawConfidence,
          timeoutEscalatedAt: nowIso,
        });

        await db.collection("alerts").doc(alertId).set({
          alertId,
          anomalyId: aid,
          hazardType: a.type,
          confidenceScore: a.rawConfidence,
          message: sachetPayload.message,
          channelsSent: ["sms_fast2sms", "dashboard_live"],
          sachetPayload,
          timestamp: nowIso,
        });

        console.log(`[TIMEOUT-ESCALATION] Anomaly ${aid} auto-escalated to alert ${alertId}`);
      } else {
        await anomDoc.ref.update({ status: "denied" });
      }
    }

    return null;
  });


// ============================================================================
// 5. ALERT DISPATCH & OFFICIAL PIPELINE DISSEMINATION
// ============================================================================
exports.onAlertCreated = functions.firestore
  .document("alerts/{alertId}")
  .onCreate(async (snapshot, context) => {
    const alert = snapshot.data();
    if (!alert) return null;

    console.log(`[OFFICIAL-DISPATCH] Disseminating SACHET-structured alert: ${alert.alertId}`);
    console.log(`[SACHET-PAYLOAD]`, JSON.stringify(alert.sachetPayload, null, 2));

    // Send broadcast SMS to registered community list via Fast2SMS
    if (CONFIG.verification.fast2smsApiKey) {
      try {
        const numbers = CONFIG.verification.broadcastAlertNumbers.join(",");
        await axios.post("https://www.fast2sms.com/dev/bulkV2", {
          route: "q",
          message: `EMERGENCY ALERT: ${alert.message}`,
          language: "english",
          flash: 0,
          numbers: numbers,
        }, {
          headers: {
            "authorization": CONFIG.verification.fast2smsApiKey,
            "Content-Type": "application/json",
          },
        });
        console.log(`[OFFICIAL-DISPATCH] Broadcast SMS sent to ${numbers}`);
      } catch (err) {
        console.error(`[OFFICIAL-DISPATCH] Fast2SMS Broadcast Error:`, err.response ? err.response.data : err.message);
      }
    } else {
      console.log(`[OFFICIAL-DISPATCH] Simulated emergency broadcast (FAST2SMS_API_KEY not configured): ${alert.message}`);
    }

    return null;
  });
