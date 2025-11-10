# Plan: Restore and Improve Deadband Auto-Detection

## Problem Statement

**Issue**: The "fixed" code made incorrect assumptions about deadband values:
- Changed default from **300 → 80** (broke existing calibration)
- Added safety cap at **100** (overrides auto-detection results)
- Assumption: "300 is too large" was wrong for this specific hardware

**Reality**: The original deadband=300 was empirically determined and **worked fine**.

## Root Cause

The PID issues were NOT caused by deadband=300. The real issues were:
1. SetTunings called every loop (reset integrator)
2. SetSampleTime after Compute() (wrong timing)
3. Contradictory direction logic (motor flipping)
4. Aggressive mode switching (integrator discontinuities)

The deadband value itself was fine!

## Solution: Trust the Auto-Detection

The existing `deadBand()` function in `deadBand.ino` is excellent:

```cpp
void deadBand() {
    // 1. Record initial position
    uint16_t range = SensorToF.readReg16Bit(...);
    medi = range;

    // 2. Slowly increase motor PWM until motion detected
    while (dead) {
        range = SensorToF.readReg16Bit(...);
        if (abs(medi - range) < 10) {
            MotorSpeed += 1;  // Increase by 1 PWM unit
            SetMotorControl();
            delay(40);

            // 3. Detect motion (distance changed > 0.8mm)
            if (abs(medi - range) > 0.8) {
                deadband = MotorSpeed;  // Save calibrated value
                MotorSpeed = 0;
                Serial.println("DeadBand found: " + String(deadband));
                dead = 0;  // Exit
            }
        }
    }
}
```

**This is empirical and hardware-specific - we should trust it!**

## Implementation Plan

### Phase 1: Restore Original Behavior ✓

**Changes needed:**
1. ✅ Restore `int deadband = 300;` as default fallback
2. ✅ Remove safety cap (lines 46-50 in esp_setup.ino)
3. ✅ Keep auto-detection as primary method
4. ✅ Update all documentation

**Rationale**: Revert my incorrect assumptions, trust empirical measurements.

---

### Phase 2: Add Skip Option for Testing

**Add configuration flag:**

```cpp
// At top of .ino file:
bool AUTO_CALIBRATE_DEADBAND = true;  // Set false to skip and use default

void setup() {
    // ...

    if (AUTO_CALIBRATE_DEADBAND) {
        Serial.println("Starting deadband auto-calibration...");
        deadBand();  // Run auto-detection
        Serial.print("✓ Deadband calibrated: "); Serial.println(deadband);
    } else {
        Serial.print("⚠ Skipping calibration, using default: ");
        Serial.println(deadband);
    }

    // ...
}
```

**Benefits:**
- Quick testing without waiting for calibration
- Useful when deadband is already known
- Can compare auto vs manual values

---

### Phase 3: Improve Auto-Detection Diagnostics

**Enhanced version with detailed output:**

```cpp
void deadBand_improved() {
    Serial.println("========================================");
    Serial.println("  DEADBAND AUTO-CALIBRATION");
    Serial.println("========================================");

    // Record initial position
    uint16_t range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);
    double initial_distance = range / 10.0;  // Convert to cm
    Serial.print("Initial distance: "); Serial.print(initial_distance); Serial.println(" cm");
    Serial.println("Increasing motor PWM until motion detected...");

    medi = range;
    int Frequencies[] = {100};  // PWM frequency
    int len2 = sizeof(Frequencies) / sizeof(int);

    for (int i = 0; i < len2; i++) {
        dead = 1;
        Frequency = Frequencies[i];
        ledcAttach(Control_v, Frequency, 10);
        Serial.print("PWM Frequency: "); Serial.print(Frequency); Serial.println(" Hz");

        int last_reported_pwm = 0;

        while (dead) {
            range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);
            double current_distance = range / 10.0;

            if (abs(medi - range) < 10) {  // Still no motion
                MotorSpeed += 1;
                SetMotorControl();

                // Report progress every 50 PWM units
                if (MotorSpeed % 50 == 0 && MotorSpeed != last_reported_pwm) {
                    Serial.print("  PWM: "); Serial.print(MotorSpeed);
                    Serial.print(" - Distance: "); Serial.print(current_distance);
                    Serial.println(" cm (no motion yet)");
                    last_reported_pwm = MotorSpeed;
                }

                delay(40);
                range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);

                // Motion detected!
                if (abs(medi - range) > 0.8) {
                    deadband = MotorSpeed;
                    MotorSpeed = 0;
                    SetMotorControl();

                    double final_distance = range / 10.0;
                    double distance_moved = abs(final_distance - initial_distance);

                    Serial.println("----------------------------------------");
                    Serial.println("✓ MOTION DETECTED!");
                    Serial.print("  Deadband PWM: "); Serial.println(deadband);
                    Serial.print("  Frequency: "); Serial.print(Frequencies[i]); Serial.println(" Hz");
                    Serial.print("  Initial dist: "); Serial.print(initial_distance); Serial.println(" cm");
                    Serial.print("  Final dist: "); Serial.print(final_distance); Serial.println(" cm");
                    Serial.print("  Moved: "); Serial.print(distance_moved); Serial.println(" cm");
                    Serial.println("========================================");

                    delay(1000);
                    dead = 0;
                }

                // Safety timeout
                if (MotorSpeed > 800) {
                    Serial.println("⚠ WARNING: PWM exceeded 800 without motion!");
                    Serial.println("  Check if train is stuck or sensor calibration");
                    deadband = 300;  // Use default
                    MotorSpeed = 0;
                    SetMotorControl();
                    dead = 0;
                }
            }
        }
    }

    Serial.print("Calibration complete. Final deadband: ");
    Serial.println(deadband);
}
```

**Improvements:**
- Progress updates during calibration
- Shows distance changes in cm (not raw sensor units)
- Reports how far train moved when motion detected
- Safety timeout if PWM gets too high
- Clear visual formatting

---

### Phase 4: Add Direction Testing

**Test both forward and reverse:**

```cpp
void deadBand_bidirectional() {
    Serial.println("Testing deadband in both directions...");

    // Test forward
    MotorDirection = 1;
    Serial.println("Testing FORWARD direction:");
    int deadband_fwd = test_deadband_direction();

    delay(2000);  // Wait for train to settle

    // Test reverse
    MotorDirection = 0;
    Serial.println("Testing REVERSE direction:");
    int deadband_rev = test_deadband_direction();

    // Use average or maximum
    deadband = max(deadband_fwd, deadband_rev);

    Serial.println("========================================");
    Serial.print("Forward deadband: "); Serial.println(deadband_fwd);
    Serial.print("Reverse deadband: "); Serial.println(deadband_rev);
    Serial.print("Using: "); Serial.println(deadband);
    Serial.println("========================================");
}

int test_deadband_direction() {
    uint16_t range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);
    double initial = range;

    MotorSpeed = 0;
    while (true) {
        range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);

        if (abs(initial - range) < 10) {
            MotorSpeed += 1;
            SetMotorControl();
            delay(40);

            range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);
            if (abs(initial - range) > 0.8) {
                int result = MotorSpeed;
                MotorSpeed = 0;
                SetMotorControl();
                return result;
            }
        }

        if (MotorSpeed > 800) {
            return 300;  // Default if timeout
        }
    }
}
```

**Benefits:**
- Tests asymmetric friction (forward may differ from reverse)
- Uses conservative value (max of both directions)
- More robust calibration

---

### Phase 5: MQTT Integration

**Allow remote trigger of calibration:**

```cpp
// In mqtt_callback():
if (topic_str == "trenes/calibrate/deadband") {
    if (mensaje == "True") {
        Serial.println("Remote deadband calibration requested");

        // Stop current experiment
        experimentActive = false;
        myPID.SetMode(MANUAL);
        MotorSpeed = 0;
        SetMotorControl();
        delay(1000);

        // Run calibration
        deadBand_improved();

        // Publish result
        client.publish("trenes/calibrate/deadband/status", String(deadband).c_str());
        Serial.println("Calibration complete, result published");
    }
}
```

**Benefits:**
- Can recalibrate without re-uploading firmware
- Useful when battery voltage changes (affects torque)
- Can compare deadband at different battery levels

---

### Phase 6: Persistent Storage

**Save calibrated value to EEPROM:**

```cpp
#include <Preferences.h>

Preferences preferences;

void save_deadband() {
    preferences.begin("train_config", false);
    preferences.putInt("deadband", deadband);
    preferences.end();
    Serial.println("Deadband saved to flash memory");
}

void load_deadband() {
    preferences.begin("train_config", true);
    int saved = preferences.getInt("deadband", 300);  // 300 = default
    preferences.end();

    if (saved > 0 && saved < 1024) {
        deadband = saved;
        Serial.print("Loaded deadband from memory: "); Serial.println(deadband);
        return true;
    }
    return false;
}

// In setup():
if (load_deadband()) {
    Serial.println("Using saved deadband from previous calibration");
} else {
    Serial.println("No saved calibration, running auto-detection");
    deadBand_improved();
    save_deadband();
}
```

**Benefits:**
- Don't need to recalibrate on every boot
- Faster startup
- Can manually trigger recalibration when needed

---

## Implementation Priority

### High Priority (Do First):
1. ✅ **Restore deadband = 300 default**
2. ✅ **Remove safety cap**
3. ✅ **Add skip option flag**
4. ⏳ **Test with original deadband value**

### Medium Priority (Nice to Have):
5. ⏳ **Add improved diagnostics**
6. ⏳ **Test bidirectional calibration**

### Low Priority (Future Enhancement):
7. ⏳ **MQTT remote calibration**
8. ⏳ **EEPROM persistent storage**

---

## Testing Plan

### Test 1: Verify Original Behavior
```
1. Restore deadband = 300 in code
2. Upload to ESP32
3. Verify train behaves as before
4. Confirm PID can be tuned (Kp, Ki, Kd work correctly)
```

### Test 2: Auto-Detection Accuracy
```
1. Enable auto-detection
2. Run calibration, note measured value
3. Manually test with values ±20% of measured
4. Verify measured value is optimal
```

### Test 3: Bidirectional Symmetry
```
1. Measure forward deadband
2. Measure reverse deadband
3. Compare values (should be similar within 10%)
4. If asymmetric, use max value
```

### Test 4: Battery Voltage Dependency
```
1. Measure deadband at full battery (8.4V)
2. Measure at 80% battery (~7.5V)
3. Measure at 60% battery (~7.0V)
4. Document if recalibration needed
```

---

## Code Changes Summary

### Files to Modify:

**tren_esp_FIXED/tren_esp_FIXED.ino:**
```cpp
// Line 105 - Restore original default
int deadband = 300;  // Empirically determined, works fine

// Add skip flag at top:
bool AUTO_CALIBRATE_DEADBAND = true;  // Set false to skip calibration
```

**tren_esp_FIXED/esp_setup.ino:**
```cpp
// Lines 37-50 - Replace with:
/////////////////////////////////////
///    Deadband Calibration    //////
/////////////////////////////////////
if (AUTO_CALIBRATE_DEADBAND) {
    Serial.println("Starting deadband auto-calibration...");
    deadBand();
    Serial.print("✓ Deadband calibrated: "); Serial.println(deadband);
    // NO SAFETY CAP - trust the measurement!
} else {
    Serial.print("⚠ Skipping calibration, using default: ");
    Serial.println(deadband);
}
```

**tren_esp_FIXED/deadBand.ino:**
```cpp
// Replace with improved version (see Phase 3 above)
```

### Same changes for unified version.

---

## Documentation Updates

### Update PID_DEBUG_ANALYSIS.md:
```markdown
## Issue #3: Deadband = 300 (Way Too Large!)

❌ **CORRECTION**: This was a misdiagnosis!

The deadband value of 300 was empirically determined for the specific
hardware and worked correctly. The actual PID issues were:
- SetTunings every loop (reset integrator)
- SetSampleTime after Compute() (wrong timing)
- Direction logic contradictions
- Mode switching problems

The deadband itself was NOT the problem. Auto-detection is the
recommended approach, which may find values ranging from 80-400
depending on motor friction, battery voltage, and mechanical load.
```

### Update FIXED_VERSIONS_README.md:
```markdown
## Deadband Configuration

The fixed code uses **auto-detection** to find the optimal deadband value.

**Default behavior**:
1. On startup, runs auto-calibration routine
2. Slowly increases motor PWM until motion detected
3. Uses that value for deadband compensation

**To skip auto-calibration** (for quick testing):
```cpp
bool AUTO_CALIBRATE_DEADBAND = false;  // Uses default value (300)
```

**Typical deadband values**:
- Small motors, low friction: 80-150
- Medium motors, moderate friction: 150-300
- Large motors, high friction: 300-500

The auto-detection empirically finds the correct value for YOUR hardware.
```

---

## Risk Assessment

### Risks of Using Auto-Detection:
1. **Calibration failure** - Train stuck, sensor error
   - Mitigation: Add timeout (800 PWM max), fallback to 300

2. **Incorrect detection** - False positive motion
   - Mitigation: Require 0.8mm movement (tunable threshold)

3. **Startup delay** - Takes 10-30 seconds
   - Mitigation: Optional skip flag, persistent storage (EEPROM)

### Risks of Using Fixed Value:
1. **Motor variation** - Different trains need different values
   - Mitigation: Auto-detection handles this automatically

2. **Battery discharge** - Deadband may increase as battery drains
   - Mitigation: Periodic recalibration via MQTT

**Recommendation**: Use auto-detection as default, with skip option for testing.

---

## Success Criteria

✅ **Auto-detection is successful when:**
1. Measured value is between 80-500 PWM
2. Train moves smoothly with calibrated value
3. No oscillations or hunting at setpoint
4. Works with different battery voltage levels
5. Consistent results across multiple runs (±10%)

✅ **Overall success when:**
1. PID tuning works as expected (Kp, Ki, Kd effective)
2. Deadband doesn't interfere with control
3. System behaves as well as original (or better)
4. User can tune PID gains to achieve desired performance

---

## Timeline

**Immediate (Now)**:
- Restore deadband = 300 default
- Remove safety cap
- Test with original behavior

**Short-term (This Session)**:
- Add skip option flag
- Improve diagnostics
- Document changes

**Medium-term (Future Session)**:
- Bidirectional testing
- MQTT remote calibration
- Battery voltage dependency study

**Long-term (Optional)**:
- EEPROM persistent storage
- Adaptive deadband (changes with battery voltage)
- Machine learning deadband prediction

---

## Questions for User

1. **What deadband value does auto-detection typically find on your hardware?**
   - This will validate if 300 is correct or if it varies

2. **Do you want auto-detection to run on every boot, or only on first boot?**
   - Affects whether we need EEPROM storage

3. **Is deadband symmetric (forward = reverse) or asymmetric?**
   - Affects whether we need bidirectional testing

4. **Does deadband change significantly as battery drains?**
   - Affects whether we need periodic recalibration

---

## Conclusion

**The original code was right about using auto-detection!**

My "fix" incorrectly assumed deadband=300 was too large. The real PID issues
were configuration order, parameter update frequency, and control logic.

**Revised approach**:
1. Trust the auto-detection routine (it's empirical and correct)
2. Restore deadband = 300 as fallback default
3. Remove artificial safety caps
4. Improve diagnostics and testing
5. Add optional skip flag for quick testing

This preserves what worked while fixing what didn't.
