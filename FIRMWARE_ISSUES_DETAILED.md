# Detailed Firmware Issues & Code Snippets
## Exact Line-by-Line Comparison

---

## ISSUE #1: Step Response Baseline Sampling (CRITICAL)

### Current Implementation (Universal) - INCOMPLETE

**File**: `tren_esp_universal/tren_esp_universal.ino`

Lines **160-162** (Variable declarations):
```cpp
int stepSampleCounter = 0;
const int STEP_DELAY_SAMPLES = 2;
double appliedStepValue = 0.0;
```

Lines **695-713** (Implementation):
```cpp
void loop_step_experiment() {
  if (flag_step == false) {
    flag_step = true;
    Serial.println("[STEP] Experiment started!");
    Serial.print("  Amplitude: "); Serial.print(StepAmplitude); Serial.println("V");
    Serial.print("  Duration: "); Serial.print(StepTime / 1000.0); Serial.println("s");
    Serial.print("  Direction: "); Serial.println(StepMotorDirection ? "Forward" : "Reverse");

    delta = millis() - tiempo_inicial_step;
    StepTime = StepTime + millis();

    stepSampleCounter = 0;
    appliedStepValue = 0.0;
    Serial.print("  Waiting for "); Serial.print(STEP_DELAY_SAMPLES); Serial.println(" baseline samples before applying step...");
  }

  read_ToF_sensor();

  if (stepSampleCounter < STEP_DELAY_SAMPLES) {
    appliedStepValue = 0.0;
    MotorSpeed = 0;
    stepSampleCounter++;
    if (stepSampleCounter == STEP_DELAY_SAMPLES) {
      Serial.println("[STEP] Baseline samples collected, applying step now!");
    }
  } else {
    appliedStepValue = StepAmplitude;
    u_step = StepAmplitude * 1024 / v_batt;
    MotorSpeed = constrain(u_step, 0, 1024);
  }
  // ... rest of function
```

**Problems**:
1. Only 2 baseline samples (not enough for stabilization)
2. No sensor warm-up phase (first 5 readings unstable)
3. UDP data sent during unstable period
4. Noise in baseline compromises system identification

---

### Superior Implementation (FIXED) - REFERENCE ✓

**File**: `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino`

Lines **135-139** (Variable declarations):
```cpp
const int STEP_WARMUP_SAMPLES = 5;    // Discard first N samples (sensor initialization)
const int STEP_BASELINE_SAMPLES = 3;  // Baseline samples after warm-up (motor off)
int stepWarmupCounter = 0;            // Counts warm-up samples (discarded)
int stepBaselineCounter = 0;          // Counts baseline samples (recorded)
double appliedStepValue = 0.0;        // Actual step value being applied (0 initially, then StepAmplitude)
```

Lines **329-397** (Implementation):
```cpp
void loop_step_experiment() {
    if (flag_step == false) {
        flag_step = true;
        Serial.println("[STEP] Experiment started!");
        Serial.print("  Amplitude: "); Serial.print(StepAmplitude); Serial.println("V");
        Serial.print("  Duration: "); Serial.print(StepTime / 1000.0); Serial.println("s");
        Serial.print("  Direction: "); Serial.println(StepMotorDirection ? "Forward" : "Reverse");

        delta = millis() - tiempo_inicial_step;
        StepTime = tiempo_inicial_step + StepTimeDuration;

        // Reset counters and applied value
        stepWarmupCounter = 0;
        stepBaselineCounter = 0;
        appliedStepValue = 0.0;
        Serial.print("  Sensor warm-up: "); Serial.print(STEP_WARMUP_SAMPLES); Serial.println(" samples (discarded)");
        Serial.print("  Baseline: "); Serial.print(STEP_BASELINE_SAMPLES); Serial.println(" samples (motor off)");
    }

    read_ToF_sensor();

    // Three-phase approach: WARMUP -> BASELINE -> STEP APPLIED
    if (stepWarmupCounter < STEP_WARMUP_SAMPLES) {
        // PHASE 1: WARMUP - Discard samples to let sensor stabilize
        stepWarmupCounter++;
        MotorSpeed = 0;
        appliedStepValue = 0.0;
        MotorDirection = StepMotorDirection;
        SetMotorControl();
        // DON'T send UDP data during warm-up (sensor readings unstable)
        if (stepWarmupCounter == STEP_WARMUP_SAMPLES) {
            Serial.println("[STEP] Sensor warm-up complete, collecting baseline...");
        }
        return;  // Skip UDP send during warm-up
    }
    else if (stepBaselineCounter < STEP_BASELINE_SAMPLES) {
        // PHASE 2: BASELINE - Motor off, record stable baseline readings
        stepBaselineCounter++;
        MotorSpeed = 0;
        appliedStepValue = 0.0;
        if (stepBaselineCounter == STEP_BASELINE_SAMPLES) {
            Serial.println("[STEP] Baseline collected, applying step now!");
        }
    }
    else {
        // PHASE 3: STEP APPLIED - Apply step input and record response
        appliedStepValue = StepAmplitude;
        u_step = StepAmplitude * 1024 / v_batt;
        MotorSpeed = constrain(u_step, 0, 1024);
    }

    MotorDirection = StepMotorDirection;
    SetMotorControl();
    send_udp_step_data();
    // ... rest of function
```

**Key Differences**:
- 3 distinct phases instead of 2
- 5-sample warm-up discarded (sensor initialization)
- 3-sample baseline recorded (clean reference)
- UDP data NOT sent during warm-up
- Much cleaner data for analysis

---

## ISSUE #2: Step Time Duration Bug (CRITICAL)

### Universal Firmware (BROKEN)

**File**: `tren_esp_universal/tren_esp_universal.ino`

Lines **688-693** (Parameter Setting):
```cpp
else if (topic_str == mqtt_prefix + "/step/time") {
  float time_seconds = mensaje.toFloat();
  StepTime = time_seconds * 1000;
  StepTime = constrain(StepTime, 0, 20000);
  client.publish((mqtt_prefix + "/step/time/status").c_str(), String(time_seconds, 1).c_str());
}
```

Lines **952-956** (Status Request - BROKEN):
```cpp
else if (topic_str == mqtt_prefix + "/step/request_params") {
  client.publish((mqtt_prefix + "/step/amplitude/status").c_str(), String(StepAmplitude, 1).c_str());
  client.publish((mqtt_prefix + "/step/time/status").c_str(), String(StepTime / 1000.0, 1).c_str());
  client.publish((mqtt_prefix + "/step/direction/status").c_str(), String(StepMotorDirection).c_str());
  client.publish((mqtt_prefix + "/step/vbatt/status").c_str(), String(v_batt, 1).c_str());
}
```

Lines **688-693** (In loop - problematic):
```cpp
delta = millis() - tiempo_inicial_step;
StepTime = StepTime + millis();  // ← StepTime MODIFIED during experiment!
```

**Problem**: StepTime gets MODIFIED during the experiment (becomes absolute end time), but status request publishes modified value instead of original duration.

**Scenario**:
1. Dashboard: sends `step/time = 5000` (5 seconds)
2. Firmware: StepTime = 5000ms
3. Experiment starts: StepTime becomes 1725345600123 (absolute milliseconds)
4. Dashboard requests params mid-experiment
5. Firmware publishes StepTime / 1000.0 = 1725345600.123 seconds (WRONG!)
6. Dashboard shows incorrect duration

---

### FIXED Firmware (CORRECT) ✓

**File**: `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino`

Lines **129** (New variable):
```cpp
uint32_t StepTime = 0;           // Absolute end time (modified during experiment)
uint32_t StepTimeDuration = 0;   // Original duration in ms (for status publishing) ← NEW
```

Lines **339** (During experiment initialization):
```cpp
StepTime = tiempo_inicial_step + StepTimeDuration;  // ← Uses StepTimeDuration, preserves original
```

Lines **689** (Parameter Setting - FIXED):
```cpp
else if (topic_str == "trenes/step/time") {
  float time_seconds = mensaje.toFloat();
  StepTime = time_seconds * 1000;
  StepTime = constrain(StepTime, 0, 20000);
  StepTimeDuration = StepTime;  // ← SAVE original duration
  client.publish("trenes/step/time/status", String(time_seconds, 1).c_str());
}
```

Lines **704** (Status Request - FIXED):
```cpp
else if (topic_str == "trenes/step/request_params") {
  client.publish("trenes/step/amplitude/status", String(StepAmplitude, 1).c_str());
  client.publish("trenes/step/time/status", String(StepTimeDuration / 1000.0, 1).c_str());  // ← Uses original duration
  client.publish("trenes/step/direction/status", String(StepMotorDirection).c_str());
  client.publish("trenes/step/vbatt/status", String(v_batt, 1).c_str());
}
```

**Solution**: Add StepTimeDuration variable to preserve original value

---

## ISSUE #3: Deadband Motion Threshold PWM Gate (HIGH)

### Universal Firmware

**File**: `tren_esp_universal/tren_esp_universal.ino`  
**Line 778**:
```cpp
if (distance_change >= motion_threshold && MotorSpeed > 10) {
    motion_detected = true;
    calibrated_deadband = MotorSpeed;
```

**Problem**: Detects motion at PWM=11, which is too low and subject to sensor noise

---

### FIXED Firmware

**File**: `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino`  
**Line 450**:
```cpp
if (distance_change >= motion_threshold && MotorSpeed > 50) {
    motion_detected = true;
    calibrated_deadband = MotorSpeed;
```

**Analysis**:
- PWM threshold should be higher to reject noise
- 50 PWM = ~4.9% of full speed (reasonable for robust detection)
- 10 PWM = ~0.98% of full speed (too sensitive)

**Recommendation**: Change Universal to use **PWM > 50**

---

## ISSUE #4: PID Sensor Warm-up (HIGH)

### Universal Firmware (NO WARM-UP)

**File**: `tren_esp_universal/tren_esp_universal.ino`

Lines **621-628**:
```cpp
void loop_pid_experiment() {
  if (flag_pid == false) {
    flag_pid = true;
    tiempo_inicial_pid = millis();
    Serial.println("[PID] Experiment started!");
    myPID.SetMode(AUTOMATIC);  // ← IMMEDIATE, no warm-up
    PIDMotorDirection = 1;
  }

  if (pid_params_changed) {
    myPID.SetTunings(Kp, Ki, Kd);
    // ...
  }

  read_ToF_sensor();
  distancia = medi;
  error_distancia = x_ref - distancia;
  myPID.Compute();  // ← First iteration uses unstable sensor reading
```

**Problem**: First 5 sensor readings are unstable during initialization, but PID uses them immediately

---

### FIXED Firmware (WITH WARM-UP) ✓

**File**: `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino`

Lines **117-119** (Variables):
```cpp
bool flag_pid = true;
uint32_t tiempo_inicial_pid = 0;
bool pid_params_changed = false;
// NEW: Sensor warm-up for PID mode
const int PID_WARMUP_SAMPLES = 5;  // Discard first N samples for sensor stabilization
int pidWarmupCounter = 0;          // Counts warm-up samples (discarded)
```

Lines **248-284** (Implementation):
```cpp
void loop_pid_experiment() {
    if (flag_pid == false) {
        flag_pid = true;
        tiempo_inicial_pid = millis();
        pidWarmupCounter = 0;  // Reset warm-up counter
        Serial.println("[PID] Experiment started!");
        Serial.print("  Sensor warm-up: "); Serial.print(PID_WARMUP_SAMPLES); Serial.println(" samples (stabilizing...)");
        // DON'T set PID to AUTOMATIC yet - wait until after warm-up
        myPID.SetMode(MANUAL);  // Keep PID in manual mode during warm-up
        PIDMotorDirection = 1;
    }

    if (pid_params_changed) {
        myPID.SetTunings(Kp, Ki, Kd);
        pid_params_changed = false;
        Serial.print("[PID] Parameters updated - Kp:");
        Serial.print(Kp); Serial.print(", Ki:");
        Serial.print(Ki); Serial.print(", Kd:");
        Serial.println(Kd);
    }

    read_ToF_sensor();

    // SENSOR WARM-UP: Discard first N readings to let sensor stabilize
    if (pidWarmupCounter < PID_WARMUP_SAMPLES) {
        pidWarmupCounter++;
        MotorSpeed = 0;
        MotorDirection = PIDMotorDirection;
        SetMotorControl();
        // Don't run PID, don't send UDP data during warm-up
        if (pidWarmupCounter == PID_WARMUP_SAMPLES) {
            Serial.println("[PID] Sensor warm-up complete, starting control loop...");
            // NOW activate PID with fresh sensor readings
            myPID.SetMode(AUTOMATIC);
        }
        delay(SampleTime);
        return;  // Skip PID computation and UDP send during warm-up
    }
    
    distancia = medi;
    error_distancia = x_ref - distancia;
    myPID.Compute();  // ← Now uses stable sensor reading
```

**Impact**: 
- Universal has noisy first 5 readings affecting control loop
- FIXED stabilizes before PID activation
- Better response quality

---

## ISSUE #5: MQTT Topic Architecture Difference

### Universal (DYNAMIC) - BETTER FOR MULTI-TRAIN

**File**: `tren_esp_universal/tren_esp_universal.ino`

Lines **52, 59** (Variables):
```cpp
String train_id = "";           // e.g., "trainA", "trainB", "trainC"
String mqtt_prefix = "";        // e.g., "trenes/trainA"
```

Lines **197-198** (Initialization):
```cpp
// Generate MQTT prefix
mqtt_prefix = "trenes/" + train_id;
```

Lines **1038-1059** (Subscriptions):
```cpp
// Subscribe to PID topics (DYNAMIC)
client.subscribe((mqtt_prefix + "/sync").c_str());
client.subscribe((mqtt_prefix + "/carroD/p").c_str());
// ... all topics use mqtt_prefix variable

// Subscribe to Deadband Calibration topics (DYNAMIC)
client.subscribe((mqtt_prefix + "/deadband/sync").c_str());
client.subscribe((mqtt_prefix + "/deadband/direction").c_str());
client.subscribe((mqtt_prefix + "/deadband/threshold").c_str());
client.subscribe((mqtt_prefix + "/deadband/request_params").c_str());
client.subscribe((mqtt_prefix + "/deadband/apply").c_str());
```

**Advantage**: Same firmware works for any train (trainA, trainB, trainC, etc.)

---

### FIXED (HARDCODED) - ONLY FOR SINGLE TRAIN

**File**: `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino`

Lines **50-52** (Hardcoded):
```cpp
const char* ssid = "TICS322";
const char* password = "esp32esp32";
const char* mqtt_server = "192.168.137.1";
```

Lines **791-812** (Subscriptions):
```cpp
// Subscribe to PID topics
client.subscribe("trenes/sync");  // ← Hardcoded
client.subscribe("trenes/carroD/p");
// ...

// Subscribe to Deadband Calibration topics (NEW)
client.subscribe("trenes/deadband/sync");  // ← Hardcoded
client.subscribe("trenes/deadband/direction");
```

**Limitation**: Only works with "trenes/" prefix, cannot support multiple trains

---

## ISSUE #6: Step Duration Status Response

### Dashboard Integration (train_control_platform.py)

**File**: `train_control_platform.py`  
**Lines 703-704** (How dashboard reads step params):

```python
# Backward compatibility for old firmware without applied_step field
self.latest_data = {
    # ... other fields ...
    'applied_step': float(data_parts[5]),  # Fallback: use step_input
    'full_data': data_string,
    'packet_count': self.total_packets
}

# Add to queue for dashboard with overflow detection
if not self.data_queue.full():
    self.data_queue.put(self.latest_data)
```

**Expected from Universal**: 8-field format with `applied_step`
```
delta,time_now,motor_dir,v_batt,medi,StepAmplitude,MotorSpeed,appliedStepValue
```

**What Universal Sends** (Lines 1094-1101):
```cpp
void send_udp_step_data() {
  uint32_t time_now = millis();
  String cadena = String(delta) + "," +
                  String(time_now) + "," +
                  String(StepMotorDirection) + "," +
                  String(v_batt) + "," +
                  String(medi) + "," +
                  String(StepAmplitude) + "," +
                  String(MotorSpeed) + "," +
                  String(appliedStepValue);  // ✓ Correct
```

**Status**: Compatible ✓ but with bugs above

---

## MQTT CALLBACK COMPARISON

### Universal Firmware - Dynamic Topics

**File**: `tren_esp_universal/tren_esp_universal.ino`  
**Lines 838-1001**:

All callbacks use `mqtt_prefix` variable:
```cpp
if (topic_str == mqtt_prefix + "/sync") { ... }
else if (topic_str == mqtt_prefix + "/carroD/p") { ... }
else if (topic_str == mqtt_prefix + "/step/sync") { ... }
else if (topic_str == mqtt_prefix + "/deadband/sync") { ... }
// etc.
```

**Advantage**: Works for any train ID

---

### FIXED Firmware - Hardcoded Topics

**File**: `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino`  
**Lines 562-754**:

All callbacks use hardcoded strings:
```cpp
if (topic_str == "trenes/sync") { ... }
else if (topic_str == "trenes/carroD/p") { ... }
else if (topic_str == "trenes/step/sync") { ... }
else if (topic_str == "trenes/deadband/sync") { ... }
// etc.
```

**Limitation**: Only works with "trenes/" prefix

---

## SUMMARY OF CHANGES NEEDED IN UNIVERSAL

```cpp
// Add after line 128
uint32_t StepTimeDuration = 0;

// Change lines 160-162 to:
const int STEP_WARMUP_SAMPLES = 5;
const int STEP_BASELINE_SAMPLES = 3;
int stepWarmupCounter = 0;
int stepBaselineCounter = 0;

// Add after line 116
const int PID_WARMUP_SAMPLES = 5;
int pidWarmupCounter = 0;

// Change line 778
if (distance_change >= motion_threshold && MotorSpeed > 50) {  // was > 10

// Modify MQTT callback around lines 936-940
StepTimeDuration = StepTime;  // ADD THIS LINE

// Modify MQTT callback around line 954
String(StepTimeDuration / 1000.0, 1)  // USE DURATION not StepTime

// Replace loop_pid_experiment (lines 621-679) with FIXED version warm-up logic

// Replace loop_step_experiment (lines 695-713) with FIXED version 3-phase logic
```

