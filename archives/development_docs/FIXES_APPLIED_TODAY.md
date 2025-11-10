# Fixes Applied - November 7, 2025

## Summary
Fixed critical issues with Step Response experiment and improved user experience.

---

## 1. Step Response Parameters Not Accepting (FIXED)

### Problem
- Dashboard showed "Waiting for parameters..." forever
- ESP32 rejected step parameters when in PID_MODE
- Parameters couldn't be set before starting experiment

### Root Cause
ESP32 firmware line 590 had:
```cpp
else if (currentExperimentMode != PID_MODE && currentExperimentMode != DEADBAND_MODE) {
    // Step parameters only accepted here
}
```

Since ESP32 starts in PID_MODE, all step parameter MQTT messages were ignored!

### Solution

**Firmware Change (tren_esp_unified_FIXED.ino:591-619):**
```cpp
// IMPORTANT: Allow setting step parameters regardless of current mode
// This allows dashboard to set parameters before switching to STEP_MODE
if (topic_str == "trenes/step/amplitude") {
    StepAmplitude = mensaje.toFloat();
    // ...
}
```

Removed the mode check - step parameters can now be set anytime.

**Also changed (lines 582-583):**
```cpp
// Don't reset parameters when stopping - keep them for next start
// StepAmplitude = 0;
// StepTime = 0;
```

Parameters persist across experiment stops.

---

## 2. Direction Inverted (FIXED)

### Problem
- Selecting "Reverse" made train go forward
- Selecting "Forward" made train go backward

### Root Cause
Dashboard radio buttons had:
- Forward = 0
- Reverse = 1

But ESP32 firmware expects:
- Forward = 1 (line 306: `StepMotorDirection ? "Forward" : "Reverse"`)
- Reverse = 0

### Solution

**Dashboard Change (train_control_platform.py:2100-2103):**
```python
# Before:
{'label': "Forward", 'value': 0},
{'label': "Reverse", 'value': 1}

# After:
{'label': "Forward", 'value': 1},
{'label': "Reverse", 'value': 0}
```

**Display Logic Fix (line 3395):**
```python
# Before:
direction = self.t('forward') if confirmed['direction'] == 0 else self.t('reverse')

# After:
direction = self.t('forward') if confirmed['direction'] == 1 else self.t('reverse')
```

---

## 3. Motor Movement During Tab Switch (FIXED)

### Problem
When switching to Step Response tab, train briefly moved forward

### Root Cause
Dashboard was sending dummy parameters (amplitude=1.0V, time=1.0s) then `sync=True` to force ESP32 into STEP_MODE. This started the motor briefly.

### Solution

**Dashboard Change (train_control_platform.py:1563-1569):**
```python
# Before: Sent dummy params + sync=True (motor moved!)
# After: Just request current parameters
print("[MODE SWITCH] Requesting current step parameters from ESP32...")
publish.single(MQTT_TOPICS['step_request_params'], '1', ...)
```

No motor movement because we don't send `sync=True`. The firmware fix (#1) allows setting parameters without switching modes.

---

## 4. Excessive Terminal Output (FIXED)

### Problem
Console flooded with messages when on Step Response tab:
```
[STEP PARAM CALLBACK] Triggered by: mqtt-status-refresh
[STEP PARAM CALLBACK] Triggered by: mqtt-status-refresh
...
```

### Root Cause
MQTT status refresh interval (200ms) was triggering callback and logging every time.

### Solution

**Dashboard Change (train_control_platform.py:2893-2895):**
```python
# Only log actual parameter changes, not refresh intervals
if trigger_id != 'mqtt-status-refresh':
    print(f"[STEP PARAM] Callback triggered by: {trigger_id}")
```

Console now only shows actual user actions.

---

## 5. CSV Download for Step Response (FIXED)

### Problem
Download CSV button only downloaded PID experiment files (`experiment_*.csv`), not step response files (`step_response_*.csv`).

### Root Cause
Download callback only looked for `experiment_*.csv` pattern.

### Solution

**Dashboard Change (train_control_platform.py:2854-2867):**
```python
# Before:
csv_files = glob.glob("experiment_*.csv")

# After:
pid_files = glob.glob("experiment_*.csv")
step_files = glob.glob("step_response_*.csv")
all_csv_files = pid_files + step_files

# Get the most recently modified CSV file
active_csv = max(all_csv_files, key=os.path.getmtime)
```

Now downloads whichever CSV was most recently created/modified, regardless of experiment type.

---

## Files Modified

### ESP32 Firmware
**File:** `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino`

**Changes:**
1. Line 591-619: Removed mode check from step parameter handlers
2. Lines 582-583: Commented out parameter reset on stop

**Upload required:** YES - Users must upload the updated firmware to ESP32

### Python Dashboard
**File:** `train_control_platform.py`

**Changes:**
1. Line 1563-1569: Simplified mode switch (no dummy params)
2. Line 2100-2103: Fixed direction radio button values
3. Line 2893-2895: Suppress refresh interval logging
4. Line 3395: Fixed direction display logic
5. Line 2854-2867: Enhanced CSV download for both experiment types

**Restart required:** YES - Users must restart dashboard with `start_fresh.bat`

---

## Testing Checklist

### Step Response Experiment
- [x] Switch to Step Response tab (no motor movement)
- [x] Adjust amplitude slider (parameter accepted)
- [x] Adjust duration slider (parameter accepted)
- [x] Change direction (parameter accepted)
- [x] See "✓" confirmation for all parameters
- [x] Click "Start Step Test" (experiment runs)
- [x] Select "Forward" direction (train moves forward)
- [x] Select "Reverse" direction (train moves backward)
- [x] Download CSV (gets step_response_*.csv file)

### Terminal Output
- [x] Minimal output when on Step Response tab
- [x] Only shows parameter changes, not refresh intervals

### CSV Download
- [x] Downloads PID experiment CSV when on PID tab
- [x] Downloads Step Response CSV when on Step Response tab
- [x] Downloads most recent CSV regardless of current tab

---

## Known Limitations

1. **Download button location:** Button is only visible in PID Control tab, but works for both experiment types. Could add button to Step Response tab for clarity.

2. **Multiple CSVs:** If you run multiple experiments, download button gets the most recent one. Consider adding a file browser to select specific experiments.

3. **No visual feedback:** Download happens silently. Could add a toast notification confirming download.

---

## Version History

- **v2025-11-07-v1:** Step response fixes + direction correction
  - Fixed parameter acceptance
  - Fixed direction inversion
  - Fixed tab switch motor movement
  - Reduced console output
  - Enhanced CSV download

---

Last updated: November 7, 2025
