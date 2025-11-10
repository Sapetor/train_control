# Step Response Parameter Setting - Debug Guide

## Problem
Step response parameters can't be set, showing "waiting for parameters" forever.

## Root Cause
ESP32 only accepts step parameters when in STEP_MODE, but it only enters STEP_MODE when you send `sync=True` with existing valid parameters. This creates a chicken-and-egg problem.

## Solution Applied
Modified mode switch logic to:
1. Send minimal valid parameters (amplitude=1.0, time=1.0)
2. Start step mode briefly with `sync=True`
3. Immediately stop with `sync=False`
4. Request current parameters

This puts ESP32 in STEP_MODE so it can receive parameter updates.

## How to Test

### 1. Restart Dashboard
Run: `start_fresh.bat`

### 2. Switch to Step Response Tab
Click on "Step Response" tab in the dashboard.

**Expected Output in Python Terminal:**
```
[MODE SWITCH] Switching from pid to step
[MODE SWITCH] Telling ESP32 to enter Step Response mode...
[MODE SWITCH] Sending minimal parameters to enable mode switch...
[MODE SWITCH] ESP32 now in STEP_MODE and ready for parameters
```

**Expected Output in ESP32 Serial Monitor:**
```
[MQTT] trenes/sync = False
[PID] Stopped
[MQTT] trenes/step/amplitude = 1.0
[MQTT] trenes/step/time = 1.0
[MQTT] trenes/step/sync = True
[STEP] Started
[MQTT] trenes/step/sync = False
[STEP] Stopped
[MQTT] trenes/step/request_params = 1
```

### 3. Move a Slider (e.g., Amplitude)
Drag the amplitude slider to a new value (e.g., 3.5V).

**Expected Output in Python Terminal:**
```
[STEP PARAM CALLBACK] Triggered by: amplitude-slider
[STEP PARAM] Sent amplitude = 3.5
```

**Expected Output in ESP32 Serial Monitor:**
```
[MQTT] trenes/step/amplitude = 3.5
```

**Expected Output in Python Terminal (MQTT Confirmation):**
```
[MQTT 11:30:15] Updated Step Amplitude to 3.5
```

**Expected in Dashboard:**
Shows: `Amp=3.5V, Time=1.0s, Dir=Forward, VBatt=8.3V ✓`

### 4. Start Experiment
Click "Start Step Test" button.

**Expected Output in Python Terminal:**
```
[STEP START] Starting experiment with confirmed params: {...}
```

**Expected Output in ESP32 Serial Monitor:**
```
[MQTT] trenes/step/sync = True
[STEP] Started
```

**Expected in Dashboard:**
- Button changes to "Stop Step Test" (red)
- Graph starts showing data
- UDP receiver shows packets coming in

---

## Troubleshooting

### Issue: "Waiting for parameters" never clears

**Possible Causes:**
1. ESP32 not in STEP_MODE
2. ESP32 not publishing status confirmations
3. Python not receiving MQTT confirmations

**Diagnosis:**
- Check Python terminal for `[MODE SWITCH]` messages when switching tabs
- Check ESP32 serial for mode switch MQTT messages
- Check if ESP32 current mode is STEP_MODE

### Issue: Parameters sent but not confirmed

**Python shows:**
```
[STEP PARAM] Sent amplitude = 3.5
```

**But ESP32 shows nothing**

**Possible Causes:**
1. ESP32 still in PID_MODE (rejects step parameters)
2. MQTT broker not running
3. Network issue

**Diagnosis:**
- Check ESP32 serial for `[MQTT] trenes/step/amplitude = X`
- If not showing, ESP32 is not in STEP_MODE
- Check MQTT broker is running: `netstat -an | findstr :1883`

### Issue: ESP32 receives but doesn't confirm

**ESP32 shows:**
```
[MQTT] trenes/step/amplitude = 3.5
```

**But Python doesn't show confirmation:**
```
[MQTT] Updated Step Amplitude to 3.5
```

**Possible Causes:**
1. ESP32 not publishing to `/status` topics
2. Python not subscribed to `/status` topics

**Diagnosis:**
- Check firmware line 594: Should have `client.publish("trenes/step/amplitude/status", ...)`
- Check Python line 185: Should subscribe to `step_amplitude_status`
- Add debug to ESP32 to print when publishing status

### Issue: Parameters confirmed but can't start

**Dashboard shows:**
```
Amp=3.5V, Time=1.0s, Dir=Forward, VBatt=8.3V ✓
```

**But "Start Step Test" doesn't work**

**Possible Causes:**
1. Missing parameters (direction or vbatt still None)
2. Validation check failing

**Diagnosis:**
- Check all 4 parameters are set (amplitude, time, direction, vbatt)
- Check start experiment callback for errors

---

## Key Firmware Logic

### ESP32 Parameter Acceptance (line 590)
```cpp
else if (currentExperimentMode != PID_MODE && currentExperimentMode != DEADBAND_MODE)
```
Parameters ONLY accepted when in STEP_MODE.

### ESP32 Mode Switch (line 571-579)
```cpp
if (topic_str == "trenes/step/sync") {
    if (mensaje == "True" && StepTime > 0 && StepAmplitude > 0) {
        currentExperimentMode = STEP_MODE;  // Only sets mode when True + valid params
        experimentActive = true;
    } else {
        experimentActive = false;  // False just stops, doesn't change mode
    }
}
```

### ESP32 Parameter Confirmation (line 594)
```cpp
client.publish("trenes/step/amplitude/status", String(StepAmplitude, 1).c_str());
```

---

## MQTT Topics Reference

### Dashboard → ESP32
- `trenes/step/amplitude` - Set amplitude (V)
- `trenes/step/time` - Set duration (seconds)
- `trenes/step/direction` - Set direction (0=forward, 1=reverse)
- `trenes/step/vbatt` - Set battery voltage limit (V)
- `trenes/step/sync` - Start/stop experiment (True/False)
- `trenes/step/request_params` - Request current parameter values

### ESP32 → Dashboard (Confirmations)
- `trenes/step/amplitude/status` - Confirmed amplitude
- `trenes/step/time/status` - Confirmed time
- `trenes/step/direction/status` - Confirmed direction
- `trenes/step/vbatt/status` - Confirmed vbatt

---

## Files Modified

### train_control_platform.py

**Lines 1563-1581:** Mode switch with workaround
```python
# Send minimal valid parameters first
publish.single(MQTT_TOPICS['step_amplitude'], '1.0', ...)
publish.single(MQTT_TOPICS['step_time'], '1.0', ...)
# Start step mode
publish.single(MQTT_TOPICS['step_sync'], 'True', ...)
# Immediately stop
publish.single(MQTT_TOPICS['step_sync'], 'False', ...)
# Request parameters
publish.single(MQTT_TOPICS['step_request_params'], '1', ...)
```

**Lines 2909-2932:** Parameter send with logging
```python
if trigger_id == 'amplitude-slider':
    publish.single(MQTT_TOPICS['step_amplitude'], str(amp_slider), ...)
    print(f"[STEP PARAM] Sent amplitude = {amp_slider}")
```

---

Last updated: Nov 7, 2025
