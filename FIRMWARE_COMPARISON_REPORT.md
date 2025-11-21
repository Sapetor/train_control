# Firmware Comparison Report
## tren_esp_universal.ino vs tren_esp_unified_FIXED.ino

**Date**: 2025-11-21  
**Comparison Focus**: Deadband Calibration, PID Mode, Step Response, and MQTT Handling

---

## CRITICAL FINDINGS

### 1. Step Response Baseline Sampling - MAJOR DIFFERENCE
**Issue**: Universal firmware uses simplified baseline approach, while FIXED uses proper 3-phase approach

#### Universal Firmware (tren_esp_universal.ino)
- **Lines 160-162**: Uses simple counter model
  ```cpp
  int stepSampleCounter = 0;
  const int STEP_DELAY_SAMPLES = 2;
  double appliedStepValue = 0.0;
  ```
- **Lines 695-713**: Two-phase approach (baseline → step)
  - Baseline: 2 samples with motor off
  - Then: Step applied directly

#### FIXED Firmware (tren_esp_unified_FIXED.ino) ✓ SUPERIOR
- **Lines 135-139**: Three-phase approach with sensor warm-up
  ```cpp
  const int STEP_WARMUP_SAMPLES = 5;      // Discard first samples (initialization)
  const int STEP_BASELINE_SAMPLES = 3;    // Baseline samples after warm-up
  int stepWarmupCounter = 0;              // Counts warm-up samples (discarded)
  int stepBaselineCounter = 0;            // Counts baseline samples (recorded)
  ```
- **Lines 352-379**: Three distinct phases
  1. **WARMUP phase (Lines 352-363)**: Discard 5 initial samples for sensor stabilization
  2. **BASELINE phase (Lines 365-372)**: Record 3 baseline samples with motor off
  3. **STEP APPLIED phase (Lines 374-379)**: Apply actual step amplitude

**Impact**: 
- Universal baseline data may be corrupted by sensor initialization noise
- FIXED produces cleaner baseline for system identification
- Dashboard CSV analysis will show better data quality with FIXED

---

### 2. Step Response Time Duration Handling - BUG IN UNIVERSAL
**Issue**: Universal firmware doesn't preserve original duration for status publishing

#### Universal Firmware (tren_esp_universal.ino) - BROKEN
- **Line 688-693**: Uses StepTime directly for status response
  ```cpp
  else if (topic_str == mqtt_prefix + "/step/time") {
    float time_seconds = mensaje.toFloat();
    StepTime = time_seconds * 1000;
    StepTime = constrain(StepTime, 0, 20000);
    client.publish((mqtt_prefix + "/step/time/status").c_str(), String(time_seconds, 1).c_str());
  }
  else if (topic_str == mqtt_prefix + "/step/request_params") {
    // BUG: Publishing StepTime / 1000.0, but StepTime gets modified during experiment
    client.publish((mqtt_prefix + "/step/time/status").c_str(), String(StepTime / 1000.0, 1).c_str());
  }
  ```

#### FIXED Firmware (tren_esp_unified_FIXED.ino) - CORRECT ✓
- **Lines 129, 339, 689, 704**: Maintains separate duration variable
  ```cpp
  uint32_t StepTime = 0;           // Absolute end time (modified during experiment)
  uint32_t StepTimeDuration = 0;   // Original duration in ms (for status publishing)
  
  // In loop_step_experiment() initialization:
  StepTime = tiempo_inicial_step + StepTimeDuration;
  
  // In MQTT callback:
  StepTimeDuration = StepTime;  // Save original duration
  
  // In request_params:
  client.publish((mqtt_prefix + "/step/time/status").c_str(), 
    String(StepTimeDuration / 1000.0, 1).c_str());  // ✓ Uses duration, not modified value
  ```

**Impact**:
- Dashboard requests step params mid-experiment: Gets wrong time value (elapsed instead of duration)
- Status display shows incorrect remaining time
- Users cannot verify correct duration was set

**Fix Required in Universal**: Add `uint32_t StepTimeDuration` variable

---

### 3. PID Sensor Warm-up - MISSING IN UNIVERSAL
**Issue**: Universal firmware applies PID immediately, FIXED includes sensor stabilization

#### Universal Firmware (tren_esp_universal.ino) - NO WARMUP
- **Lines 621-628**: Starts PID immediately
  ```cpp
  void loop_pid_experiment() {
    if (flag_pid == false) {
      flag_pid = true;
      tiempo_inicial_pid = millis();
      Serial.println("[PID] Experiment started!");
      myPID.SetMode(AUTOMATIC);  // ← Immediate activation
      PIDMotorDirection = 1;
    }
  ```

#### FIXED Firmware (tren_esp_unified_FIXED.ino) ✓ BETTER
- **Lines 117-119, 248-284**: Includes 5-sample warm-up phase
  ```cpp
  const int PID_WARMUP_SAMPLES = 5;  // Discard first N samples
  int pidWarmupCounter = 0;
  
  // In loop:
  if (pidWarmupCounter < PID_WARMUP_SAMPLES) {
    pidWarmupCounter++;
    MotorSpeed = 0;
    SetMotorControl();
    if (pidWarmupCounter == PID_WARMUP_SAMPLES) {
      Serial.println("[PID] Sensor warm-up complete, starting control loop...");
      myPID.SetMode(AUTOMATIC);  // ← Activation after warm-up
    }
    return;  // Skip PID computation during warm-up
  }
  ```

**Impact**:
- Universal's first PID readings use unstable sensor data
- FIXED stabilizes sensor before first PID computation
- Better control response and fewer transient errors

---

### 4. Deadband Motion Threshold Logic - SLIGHT DIFFERENCE
**Issue**: Different PWM thresholds for motion detection

#### Universal Firmware (tren_esp_universal.ino) - Line 778
```cpp
if (distance_change >= motion_threshold && MotorSpeed > 10) {
    motion_detected = true;
```
- PWM threshold: **> 10** (ignores readings at PWM ≤ 10)

#### FIXED Firmware (tren_esp_unified_FIXED.ino) - Line 450
```cpp
if (distance_change >= motion_threshold && MotorSpeed > 50) {
    motion_detected = true;
```
- PWM threshold: **> 50** (ignores readings at PWM ≤ 50)

**Analysis**:
- FIXED is more conservative (waits for higher motor power)
- Universal starts detection too early (PWM=11 might be noise)
- FIXED's threshold = 50 PWM (~5% full speed) is reasonable for filtering noise

**Recommendation**: Universal should use **MotorSpeed > 50** for consistency

---

### 5. MQTT Topic Subscriptions - KEY ARCHITECTURAL DIFFERENCE

#### Universal Firmware (DYNAMIC) - Lines 1038-1059
```cpp
// Subscribe to PID topics (DYNAMIC)
client.subscribe((mqtt_prefix + "/sync").c_str());
client.subscribe((mqtt_prefix + "/carroD/p").c_str());
client.subscribe((mqtt_prefix + "/carroD/i").c_str());
client.subscribe((mqtt_prefix + "/carroD/d").c_str());
client.subscribe((mqtt_prefix + "/ref").c_str());
client.subscribe((mqtt_prefix + "/carroD/request_params").c_str());

// Subscribe to Step Response topics (DYNAMIC)
client.subscribe((mqtt_prefix + "/step/sync").c_str());
client.subscribe((mqtt_prefix + "/step/amplitude").c_str());
client.subscribe((mqtt_prefix + "/step/time").c_str());
client.subscribe((mqtt_prefix + "/step/direction").c_str());
client.subscribe((mqtt_prefix + "/step/vbatt").c_str());
client.subscribe((mqtt_prefix + "/step/request_params").c_str());

// Subscribe to Deadband Calibration topics (DYNAMIC)
client.subscribe((mqtt_prefix + "/deadband/sync").c_str());
client.subscribe((mqtt_prefix + "/deadband/direction").c_str());
client.subscribe((mqtt_prefix + "/deadband/threshold").c_str());
client.subscribe((mqtt_prefix + "/deadband/request_params").c_str());
client.subscribe((mqtt_prefix + "/deadband/apply").c_str());
```

#### FIXED Firmware (HARDCODED) - Lines 791-812
```cpp
// Subscribe to PID topics
client.subscribe("trenes/sync");
client.subscribe("trenes/carroD/p");
// ... (hardcoded topics)

// Subscribe to Deadband Calibration topics (NEW)
client.subscribe("trenes/deadband/sync");
client.subscribe("trenes/deadband/direction");
client.subscribe("trenes/deadband/threshold");
client.subscribe("trenes/deadband/request_params");
client.subscribe("trenes/deadband/apply");
```

**Key Difference**: 
- Universal: Topics dynamically built from `mqtt_prefix` variable
- FIXED: Topics hardcoded with "trenes/" prefix
- **For multi-train**: Universal is superior (allows different prefixes)

---

### 6. Deadband Parameter Status Response - MISSING IN FIXED

#### Universal Firmware (tren_esp_universal.ino) - Lines 979-988
```cpp
else if (topic_str == mqtt_prefix + "/deadband/direction") {
  DeadbandMotorDirection = mensaje.toInt();
  DeadbandMotorDirection = constrain(DeadbandMotorDirection, 0, 1);
  client.publish((mqtt_prefix + "/deadband/direction/status").c_str(), 
    String(DeadbandMotorDirection).c_str());
}
else if (topic_str == mqtt_prefix + "/deadband/threshold") {
  motion_threshold = mensaje.toFloat();
  motion_threshold = constrain(motion_threshold, 0.01, 1.0);
  client.publish((mqtt_prefix + "/deadband/threshold/status").c_str(), 
    String(motion_threshold, 2).c_str());
}
```

#### FIXED Firmware (tren_esp_unified_FIXED.ino) - Lines 731-740
```cpp
else if (topic_str == "trenes/deadband/direction") {
  DeadbandMotorDirection = mensaje.toInt();
  DeadbandMotorDirection = constrain(DeadbandMotorDirection, 0, 1);
  client.publish("trenes/deadband/direction/status", 
    String(DeadbandMotorDirection).c_str());
}
else if (topic_str == "trenes/deadband/threshold") {
  motion_threshold = mensaje.toFloat();
  motion_threshold = constrain(motion_threshold, 0.01, 1.0);
  client.publish("trenes/deadband/threshold/status", 
    String(motion_threshold, 2).c_str());
}
```

**Analysis**: Both implement status responses ✓ (no issue here)

---

### 7. Deadband Result Publishing - TOPIC DIFFERENCE

#### Universal Firmware (tren_esp_universal.ino) - Lines 797, 825
```cpp
String result_topic = mqtt_prefix + "/deadband/result";
client.publish(result_topic.c_str(), String(calibrated_deadband).c_str());

String error_topic = mqtt_prefix + "/deadband/error";
client.publish(error_topic.c_str(), "Timeout - no motion detected");
```

#### FIXED Firmware (tren_esp_unified_FIXED.ino) - Lines 472, 504-505
```cpp
client.publish("trenes/deadband/result", String(calibrated_deadband).c_str());

client.publish("trenes/deadband/result", String(calibrated_deadband).c_str());
client.publish("trenes/deadband/error", "Timeout - no motion detected");
```

**Analysis**: 
- Universal: Dynamic topics (CORRECT for multi-train)
- FIXED: Hardcoded topics (works for single train only)
- Both publish to same topics, so compatible with dashboard

---

## SUMMARY TABLE

| Feature | Universal | FIXED | Status |
|---------|-----------|-------|--------|
| MQTT Topic Dynamism | ✓ DYNAMIC | ✗ HARDCODED | **Uni Better** |
| Step Warmup + Baseline | ✗ 2-phase | ✓ 3-phase | **FIXED Better** |
| Step Duration Preservation | ✗ BUG | ✓ Correct | **FIXED Better** |
| PID Sensor Warm-up | ✗ None | ✓ 5 samples | **FIXED Better** |
| Deadband Motion Threshold | ✗ PWM>10 | ✓ PWM>50 | **FIXED Better** |
| Deadband Status Response | ✓ Included | ✓ Included | **Tie** |
| Configuration System | ✓ EEPROM | ✗ Hardcoded | **Uni Better** |
| File Size | ~36KB | ~29KB | Uni larger |
| Feature Completeness | All modes | All modes | **Tie** |

---

## BUGS AND ISSUES TO FIX IN UNIVERSAL

### CRITICAL
1. **Step Duration Bug (Line 954)**: Add `StepTimeDuration` variable to preserve original duration
2. **PWM Threshold (Line 778)**: Change `MotorSpeed > 10` to `MotorSpeed > 50`

### HIGH PRIORITY
3. **Step Response Warmup (Lines 695-713)**: Implement 3-phase approach:
   - Add `STEP_WARMUP_SAMPLES = 5`
   - Add `STEP_BASELINE_SAMPLES = 3`
   - Add `stepWarmupCounter` and `stepBaselineCounter`
   - Skip UDP send during warmup phase

4. **PID Sensor Warm-up (Lines 621-679)**: Add 5-sample warm-up:
   - Add `PID_WARMUP_SAMPLES = 5`
   - Add `pidWarmupCounter`
   - Delay `myPID.SetMode(AUTOMATIC)` until after warmup

---

## INTEGRATION ISSUES WITH DASHBOARD

### Python Dashboard Expectations (train_control_platform.py)

1. **Step Response Data Format** (Lines 815-862):
   ```python
   # Expected: 8 fields including 'applied_step'
   # "time2sinc,time_event,motor_dir,v_batt,output_G,step_input,PWM_input,applied_step"
   ```
   - Universal sends this correctly ✓
   - Dashboard expects `applied_step` to be 0.0 during baseline, then StepAmplitude
   - Dashboard CSV header (Line 808-809) includes 'applied_step' ✓

2. **Deadband Data Format** (Lines 933-992):
   ```python
   # Expected: 5 fields
   # "time,pwm,distance,initial_distance,motion_detected"
   ```
   - Both firmwares send correct format ✓
   - Dashboard detects motion via `motion_detected == 1` flag (Line 967) ✓

3. **MQTT Status Topics** (Lines 358-382):
   - Dashboard handles parameter status from any topic
   - Works with both dynamic (Universal) and hardcoded (FIXED) topics
   - No dashboard changes needed

---

## RECOMMENDATIONS

### For Current Production
**If using single train → Use FIXED firmware**
- Better sensor warm-up (less noise)
- Correct step response timing
- Cleaner baseline phase
- Smaller file size (29KB vs 36KB)

**If using multi-train → Use UNIVERSAL firmware BUT APPLY FIXES**
- Essential: Fix step duration bug
- Important: Implement proper warmup phases
- Verify PWM threshold = 50

### Code Fixes Required (Universal)

```cpp
// Fix 1: Add at line 128 (after StepTime declarations)
uint32_t StepTimeDuration = 0;   // Original duration for status publishing

// Fix 2: Change lines 160-162 to
const int STEP_WARMUP_SAMPLES = 5;
const int STEP_BASELINE_SAMPLES = 3;
int stepWarmupCounter = 0;
int stepBaselineCounter = 0;
int stepSampleCounter = 0;  // For backward compatibility if needed

// Fix 3: Lines 131-134 (PID) add warm-up
const int PID_WARMUP_SAMPLES = 5;
int pidWarmupCounter = 0;

// Fix 4: Lines 695-713 replace with FIXED firmware approach

// Fix 5: Lines 778 change PWM threshold
if (distance_change >= motion_threshold && MotorSpeed > 50) {  // was > 10

// Fix 6: Lines 936-940 preserve duration
else if (topic_str == mqtt_prefix + "/step/time") {
  float time_seconds = mensaje.toFloat();
  StepTime = time_seconds * 1000;
  StepTime = constrain(StepTime, 0, 20000);
  StepTimeDuration = StepTime;  // ADD THIS LINE
  client.publish((mqtt_prefix + "/step/time/status").c_str(), String(time_seconds, 1).c_str());
}

// Fix 7: Lines 952-956 use duration for status
else if (topic_str == mqtt_prefix + "/step/request_params") {
  client.publish((mqtt_prefix + "/step/amplitude/status").c_str(), String(StepAmplitude, 1).c_str());
  client.publish((mqtt_prefix + "/step/time/status").c_str(), String(StepTimeDuration / 1000.0, 1).c_str());  // USE DURATION
  client.publish((mqtt_prefix + "/step/direction/status").c_str(), String(StepMotorDirection).c_str());
  client.publish((mqtt_prefix + "/step/vbatt/status").c_str(), String(v_batt, 1).c_str());
}
```

---

## FILE LOCATIONS
- `/home/user/train_control/tren_esp_universal/tren_esp_universal.ino` (1201 lines)
- `/home/user/train_control/tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino` (905 lines)
- `/home/user/train_control/train_control_platform.py` (4106 lines)

