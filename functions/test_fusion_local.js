/**
 * Hazentra Cloud Functions Local Logic & Unit Test
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * Tests the JS fusion conditions, payload formatters, and SACHET schemas
 * without requiring live Firestore connections.
 */

const assert = require("assert");

// Test thresholds matching CONFIG in index.js
const CONFIG = {
  thresholds: {
    earthquakeAccel: 4.0,
    gasBaseThreshold: 150,
    gasSpikeDelta: 25,
    floodDist: 10.0,
    landslideSoil: 70.0,
    landslideAccelMin: 3.65,
    landslideAccelMax: 4.0,
  }
};

function evaluateReadingWindow(current, prev, oldest) {
  const tempTrend = current.temp - oldest.temp;
  const soilTrend = current.soilMoisture - oldest.soilMoisture;
  const accelTrend = current.accel - oldest.accel;
  const gasTrend = current.gasRaw - oldest.gasRaw;

  const detected = [];

  // 1. Earthquake (accel > 4.0, 2 reads debounce)
  if (current.accel > CONFIG.thresholds.earthquakeAccel && prev.accel > CONFIG.thresholds.earthquakeAccel) {
    const conf = Math.min(98.0, 70.0 + (current.accel - 4.0) * 20.0);
    detected.push({ type: "earthquake", confidence: Math.round(conf * 10) / 10 });
  }

  // 2 & 4. Fire vs Gas Leak
  const isGasAnomalous = current.gasRaw >= CONFIG.thresholds.gasBaseThreshold &&
    (gasTrend >= CONFIG.thresholds.gasSpikeDelta || current.gasRaw >= 180);

  if (isGasAnomalous) {
    if (tempTrend > 0.3) {
      const conf = Math.min(96.0, 60.0 + (current.gasRaw - 150) / 8.0 + tempTrend * 15.0);
      detected.push({ type: "fire", confidence: Math.round(conf * 10) / 10 });
    } else {
      const conf = Math.min(92.0, 55.0 + (current.gasRaw - 150) / 10.0);
      detected.push({ type: "gas_leak", confidence: Math.round(conf * 10) / 10 });
    }
  }

  // 3. Flood (dist <= 10 across 2 reads AND soil saturated/rising)
  if (current.distance <= CONFIG.thresholds.floodDist && prev.distance <= CONFIG.thresholds.floodDist) {
    if (soilTrend > 1.0 || current.soilMoisture >= 70.0) {
      const conf = Math.min(99.0, 65.0 + (10.0 - current.distance) * 5.0 + (current.soilMoisture - 70) * 0.5);
      detected.push({ type: "flood", confidence: Math.round(conf * 10) / 10 });
    }
  }

  // 5. Landslide
  if (current.soilMoisture >= CONFIG.thresholds.landslideSoil) {
    if (current.accel >= CONFIG.thresholds.landslideAccelMin &&
        current.accel < CONFIG.thresholds.landslideAccelMax &&
        accelTrend > 0.03) {
      const conf = Math.min(88.0, 50.0 + (current.soilMoisture - 70) * 1.0 + (current.accel - 3.5) * 50);
      detected.push({ type: "landslide", confidence: Math.round(conf * 10) / 10 });
    }
  }

  return detected;
}

console.log("Running Hazentra Cloud Functions Unit Tests...\n");

// Test 1: Normal Baseline (no anomalies)
{
  const normalCurr = { accel: 3.5, temp: 33.9, distance: 134.5, gasRaw: 155, soilMoisture: 42.0 };
  const normalPrev = { accel: 3.5, temp: 33.9, distance: 134.5, gasRaw: 154, soilMoisture: 42.0 };
  const normalOldest = { accel: 3.5, temp: 33.8, distance: 134.6, gasRaw: 150, soilMoisture: 41.9 };

  const results = evaluateReadingWindow(normalCurr, normalPrev, normalOldest);
  assert.strictEqual(results.length, 0, "Normal baseline must trigger 0 anomalies");
  console.log("✓ Test 1 Passed: Normal baseline triggers 0 anomalies (No false alarms from ambient gas 155)");
}

// Test 2: Earthquake debounce
{
  const quakeCurr = { accel: 4.5, temp: 33.9, distance: 134.5, gasRaw: 155, soilMoisture: 42.0 };
  const quakePrevNoDebounce = { accel: 3.5, temp: 33.9, distance: 134.5, gasRaw: 155, soilMoisture: 42.0 };
  const quakeOldest = { accel: 3.5, temp: 33.9, distance: 134.5, gasRaw: 155, soilMoisture: 42.0 };

  const r1 = evaluateReadingWindow(quakeCurr, quakePrevNoDebounce, quakeOldest);
  assert.strictEqual(r1.length, 0, "Single quake spike without debounce must not trigger");

  const quakePrevWithDebounce = { accel: 4.2, temp: 33.9, distance: 134.5, gasRaw: 155, soilMoisture: 42.0 };
  const r2 = evaluateReadingWindow(quakeCurr, quakePrevWithDebounce, quakeOldest);
  assert.strictEqual(r2.length, 1);
  assert.strictEqual(r2[0].type, "earthquake");
  console.log("✓ Test 2 Passed: Earthquake requires 2 consecutive reads > 4.0 m/s^2");
}

// Test 3: Fire vs Gas Leak distinction
{
  const fireCurr = { accel: 3.5, temp: 36.5, distance: 134.5, gasRaw: 280, soilMoisture: 42.0 };
  const firePrev = { accel: 3.5, temp: 36.0, distance: 134.5, gasRaw: 250, soilMoisture: 42.0 };
  const fireOldest = { accel: 3.5, temp: 33.0, distance: 134.5, gasRaw: 150, soilMoisture: 42.0 };

  const fireRes = evaluateReadingWindow(fireCurr, firePrev, fireOldest);
  assert.strictEqual(fireRes.length, 1);
  assert.strictEqual(fireRes[0].type, "fire");

  const gasCurr = { accel: 3.5, temp: 33.9, distance: 134.5, gasRaw: 280, soilMoisture: 42.0 };
  const gasPrev = { accel: 3.5, temp: 33.9, distance: 134.5, gasRaw: 250, soilMoisture: 42.0 };
  const gasOldest = { accel: 3.5, temp: 33.9, distance: 134.5, gasRaw: 150, soilMoisture: 42.0 };

  const gasRes = evaluateReadingWindow(gasCurr, gasPrev, gasOldest);
  assert.strictEqual(gasRes.length, 1);
  assert.strictEqual(gasRes[0].type, "gas_leak");
  console.log("✓ Test 3 Passed: Fire (gas + temp rise) vs Gas Leak (gas + temp flat) contrast verified");
}

// Test 4: Flood
{
  const floodCurr = { accel: 3.5, temp: 33.9, distance: 7.5, gasRaw: 155, soilMoisture: 88.0 };
  const floodPrev = { accel: 3.5, temp: 33.9, distance: 8.0, gasRaw: 155, soilMoisture: 85.0 };
  const floodOldest = { accel: 3.5, temp: 33.9, distance: 25.0, gasRaw: 155, soilMoisture: 60.0 };

  const floodRes = evaluateReadingWindow(floodCurr, floodPrev, floodOldest);
  assert.strictEqual(floodRes.length, 1);
  assert.strictEqual(floodRes[0].type, "flood");
  console.log("✓ Test 4 Passed: Flood triggers with distance <= 10cm across 2 reads and soil saturated");
}

// Test 5: Landslide
{
  const landCurr = { accel: 3.75, temp: 33.9, distance: 134.5, gasRaw: 155, soilMoisture: 78.0 };
  const landPrev = { accel: 3.70, temp: 33.9, distance: 134.5, gasRaw: 155, soilMoisture: 77.0 };
  const landOldest = { accel: 3.50, temp: 33.9, distance: 134.5, gasRaw: 155, soilMoisture: 75.0 };

  const landRes = evaluateReadingWindow(landCurr, landPrev, landOldest);
  assert.strictEqual(landRes.length, 1);
  assert.strictEqual(landRes[0].type, "landslide");
  console.log("✓ Test 5 Passed: Landslide triggers with soil >= 70% and micro-tremors (3.65-4.0 m/s^2)");
}

// Test 6: Community verification weight calculation
{
  const rawConf = 70.0;
  const yesVotes = 2;
  const noVotes = 0;
  const verifiedConf = Math.max(0, Math.min(100, rawConf + (yesVotes * 8.0) + (noVotes * -12.0)));
  assert.strictEqual(verifiedConf, 86.0);

  const deniedConf = Math.max(0, Math.min(100, rawConf + (0 * 8.0) + (2 * -12.0)));
  assert.strictEqual(deniedConf, 46.0);
  console.log("✓ Test 6 Passed: Asymmetric community verification math (+8 YES / -12 NO) verified");
}

console.log("\nALL 6 UNIT TESTS PASSED SUCCESSFULLY!\n");
