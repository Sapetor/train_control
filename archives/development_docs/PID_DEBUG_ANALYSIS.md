# PID Control Issues and Recommended Fixes

## Executive Summary

The PID controller in the train control system has several critical issues that prevent proper operation:

1. **Configuration timing errors** - SetSampleTime called after Compute()
2. **Integrator windup** - SetTunings called every loop, resetting integral action
3. **Mode switching problems** - Frequent MANUAL/AUTOMATIC switching causes discontinuities
4. **Deadband compensation** - Too aggressive, causing oscillations
5. **Direction logic contradictions** - Motor direction flips unpredictably
6. **Non-standard setpoint handling** - Confusing double-negative setup

---

## Detailed Analysis

### Issue #1: PID Configuration Order

**Location**: `tren_esp.ino` lines 211-214

**Current Code**:
```cpp
myPID.SetTunings(Kp, Ki, Kd);
myPID.SetOutputLimits(umin, umax);
myPID.Compute();
myPID.SetSampleTime(SampleTime);  // ❌ AFTER Compute()!
```

**Problem**:
- SetSampleTime adjusts integral and derivative gain scaling
- Calling it AFTER Compute() means first calculation uses wrong timing
- This affects Ki and Kd effectiveness

**Fix**:
```cpp
// In setup():
myPID.SetSampleTime(SampleTime);
myPID.SetOutputLimits(umin, umax);
myPID.SetMode(AUTOMATIC);

// In loop() - ONLY when parameters change:
if (params_changed) {
    myPID.SetTunings(Kp, Ki, Kd);
}
myPID.Compute();
```

---

### Issue #2: SetTunings Called Every Loop

**Location**: `tren_esp.ino` line 211

**Current Code**:
```cpp
void loop() {
    // ...
    myPID.SetTunings(Kp, Ki, Kd);  // ❌ Every 50ms!
    myPID.Compute();
}
```

**Problem**:
- Many PID libraries reset the integrator when tunings change
- If called every loop, integral term never accumulates
- Ki parameter becomes useless
- Steady-state error persists

**Fix**:
```cpp
// Only call when MQTT updates parameters:
void mqtt_callback(...) {
    if (topic == "trenes/carroD/p") {
        Kp = mensaje.toFloat();
        myPID.SetTunings(Kp, Ki, Kd);  // ✓ Only when changed
    }
}
```

---

### Issue #3: Aggressive Mode Switching

**Location**: `tren_esp.ino` lines 243, 262, 275

**Current Code**:
```cpp
if (medi > 200) {
    myPID.SetMode(MANUAL);  // Disable PID
}
// ...
if ((u >= -lim) && (u <= lim)) {
    myPID.SetMode(MANUAL);  // Disable PID
}
// ...
if (medi < 200) {
    myPID.SetMode(AUTOMATIC);  // Re-enable PID
}
```

**Problem**:
- Switching to MANUAL mode can reset the integrator
- When switching back to AUTOMATIC, there's a control discontinuity
- Causes "bumps" in control output → oscillations

**Fix Option 1 - Keep PID Always On**:
```cpp
// Just clamp the output, don't disable PID
if (medi > 200) {
    MotorSpeed = 0;  // Safety stop
    // Keep PID in AUTOMATIC so it doesn't reset
} else {
    // Apply PID output normally
    MotorSpeed = constrain(abs(u) + deadband, 0, 1024);
}
```

**Fix Option 2 - Use Bumpless Transfer**:
```cpp
if (need_to_disable) {
    u_distancia = 0;  // Pre-set output
    myPID.SetMode(MANUAL);
}
```

---

### Issue #4: Deadband Compensation Too Aggressive

**Location**: `tren_esp.ino` lines 252, 257

**Current Code**:
```cpp
int deadband = 300;  // ❌ Very large!

if (u > lim) {
    MotorSpeed = int(u + deadband);  // PID output 50 → Motor 350!
}
```

**Problem**:
- Deadband should overcome static friction (~50-100 PWM units)
- Adding 300 makes small PID outputs huge
- Example: PID says "move gently" (u=50) → Motor gets 350 → jerky motion
- Causes overshoot and oscillations

**Fix - Use Measured Deadband**:
```cpp
// Use the deadband.ino search results or manual testing
int deadband = 80;  // Typical for small DC motors

// Or use conditional compensation:
if (u > lim) {
    if (abs(u) < 100) {
        MotorSpeed = int(u * 1.5);  // Gentle amplification
    } else {
        MotorSpeed = int(u);  // No compensation for large signals
    }
}
```

**Better Approach - Smooth Deadband Compensation**:
```cpp
int compensate_deadband(double u, int deadband) {
    if (abs(u) < lim) return 0;

    // Smooth transition: small u gets more compensation
    double scale = 1.0 + (deadband / (abs(u) + 1.0));
    return int(abs(u) * scale);
}
```

---

### Issue #5: Contradictory Direction Logic

**Location**: `tren_esp.ino` lines 260-274

**Current Code**:
```cpp
if ((u >= -lim) && (u <= lim)) {
    myPID.SetMode(MANUAL);
    MotorSpeed = 0;
    if (u > 0) MotorDirection = 1;     // Block A
    else MotorDirection = 0;
}

if ((u >= -lim) && (u <= lim) && (abs(ponderado) <= 0.75)) {
    MotorSpeed = 0;
    if (u < 0) MotorDirection = 1;     // Block B - OPPOSITE!
    else MotorDirection = 0;
}
```

**Problem**:
- Both blocks can execute in same loop iteration
- Block A sets direction based on u > 0
- Block B immediately reverses it!
- Motor "shakes" back and forth

**Fix - Remove Conflicting Logic**:
```cpp
// Dead zone - just stop, keep last direction
if ((u >= -lim) && (u <= lim)) {
    MotorSpeed = 0;
    // Don't change MotorDirection - keeps last direction
}
// Or if you must set direction:
else if (u > lim) {
    MotorDirection = 1;
    MotorSpeed = int(u + deadband);
} else if (u < -lim) {
    MotorDirection = 0;
    MotorSpeed = int(-u + deadband);
}
```

---

### Issue #6: Non-Standard Setpoint Configuration

**Location**: `tren_esp_unified.ino` line 101

**Current Code**:
```cpp
double rf = 0;  // Setpoint = 0
double x_ref = 10;  // Actual desired distance = 10 cm
double error_distancia;

PID myPID(&error_distancia, &u_distancia, &rf, Kp, Ki, Kd, DIRECT);

// In loop:
error_distancia = x_ref - medi;  // Manual error calculation
myPID.Compute();  // PID computes: rf - error_distancia = 0 - (x_ref - medi) = medi - x_ref
```

**Analysis**:
- Manual error: `x_ref - medi` (positive when too far)
- PID internal error: `rf - error_distancia = 0 - (x_ref - medi) = medi - x_ref` (negative when too far)
- Signs are inverted!
- Control action ends up correct due to double negative
- **BUT**: Confusing and non-standard

**Standard PID Approach**:
```cpp
// Option 1: Use distance directly as input
PID myPID(&medi, &u_distancia, &x_ref, Kp, Ki, Kd, REVERSE);
// REVERSE because: increasing distance should decrease control (move backward)

// In loop:
myPID.Compute();  // No manual error calculation needed!
```

**Why This Works Better**:
- PID computes: `error = x_ref - medi` (automatically!)
- REVERSE mode: `u = -(Kp*error + Ki*integral + Kd*derivative)`
- When `medi > x_ref` (too far): error negative → u positive → move forward ✓
- Standard PID convention, easier to debug

---

## Recommended Implementation (Minimal Changes)

### Quick Fix for tren_esp_unified.ino:

```cpp
// In setup() - line 137-139:
void setup() {
    // ... other setup ...

    myPID.SetMode(AUTOMATIC);  // ✓ Start in auto mode
    myPID.SetSampleTime(SampleTime);  // ✓ Set sample time ONCE
    myPID.SetOutputLimits(umin, umax);  // ✓ Set limits ONCE

    Serial.println("Setup Complete!");
}

// In loop_pid_experiment() - replace lines 181-186:
void loop_pid_experiment() {
    if (flag_pid == false) {
        flag_pid = true;
        tiempo_inicial_pid = millis();
        PIDMotorDirection = 1;

        // Only set tunings when starting (not every loop!)
        myPID.SetTunings(Kp, Ki, Kd);  // ✓ Once at start
        // Don't call SetMode here - already AUTOMATIC from setup
    }

    // Remove line 181-186, they're redundant now

    // ... sensor reading ...

    error_distancia = x_ref - distancia;
    myPID.Compute();  // ✓ Just compute, no reconfiguration

    // ... rest of control logic ...
}

// In mqtt_callback() - only update tunings when parameters change:
void mqtt_callback(...) {
    if (topic_str == "trenes/carroD/p") {
        Kp = mensaje.toFloat();
        myPID.SetTunings(Kp, Ki, Kd);  // ✓ Update when changed
        client.publish("trenes/carroD/p/status", String(Kp).c_str());
    }
    // Similar for Ki, Kd...
}
```

### Better Deadband Compensation:

```cpp
// Replace lines 221-236:
if (distancia > 200) {
    // Safety: no object in front
    MotorSpeed = 0;
    // Keep PID in AUTO to avoid reset
} else {
    // Normal operation
    if (abs(u) <= lim) {
        // Dead zone - stop but don't change direction
        MotorSpeed = 0;
    } else if (u > lim) {
        // Forward
        PIDMotorDirection = 1;
        // Use smaller deadband or proportional compensation
        int deadband_comp = min(80, deadband);  // Cap at 80
        MotorSpeed = int(u + deadband_comp);
    } else if (u < -lim) {
        // Reverse
        PIDMotorDirection = 0;
        int deadband_comp = min(80, deadband);  // Cap at 80
        MotorSpeed = int(-u + deadband_comp);
    }
}
```

---

## Testing Procedure

### Phase 1: Verify Basic Operation
1. Set conservative PID gains: Kp=10, Ki=0, Kd=0
2. Set small deadband: 80
3. Place object at 10cm
4. Start experiment, verify motor doesn't oscillate wildly

### Phase 2: Tune Proportional Gain
1. Increase Kp gradually: 10 → 20 → 50 → 100
2. Watch for oscillations
3. Back off when oscillations start
4. Final Kp = 0.5 * oscillation_Kp

### Phase 3: Add Integral Action
1. Start with Ki = Kp * 0.1
2. Verify steady-state error decreases
3. Watch for integral windup (motor saturates)
4. If windup occurs, reduce Ki

### Phase 4: Add Derivative Action
1. Start with Kd = Kp * 0.01
2. Should reduce overshoot
3. If jittery, reduce Kd

### Expected Results:
- **Before fixes**: Oscillates wildly, doesn't converge
- **After fixes**: Smooth approach to setpoint, minimal overshoot

---

## Common PID Tuning Mistakes (Avoid These!)

1. **❌ Starting with all three gains non-zero**
   - ✓ Start with P only, add I, then add D

2. **❌ Using gains from another system**
   - ✓ Every system is different, tune empirically

3. **❌ Ignoring sample time**
   - ✓ Ki and Kd depend on sample time! Change SampleTime → must retune

4. **❌ Mixing control modes**
   - ✓ Keep PID in AUTOMATIC during operation

5. **❌ Not clamping integrator**
   - ✓ Use SetOutputLimits to prevent windup

---

## Summary Checklist

### Critical Fixes (Do these first!):
- [ ] Move SetSampleTime to setup() or before first Compute()
- [ ] Only call SetTunings when parameters actually change
- [ ] Reduce deadband from 300 to ~80
- [ ] Remove contradictory direction logic (lines 269-274)
- [ ] Minimize mode switching (keep AUTOMATIC)

### Recommended Improvements:
- [ ] Refactor to use standard PID setup (distance as input, not error)
- [ ] Add smooth deadband compensation
- [ ] Implement anti-windup protection
- [ ] Add logging for debugging (error, output, mode)

### Tuning Steps:
- [ ] Start with Kp=10, Ki=0, Kd=0
- [ ] Tune Kp until slight oscillation
- [ ] Back off Kp by 50%
- [ ] Add Ki = Kp/10
- [ ] Add Kd = Kp/100 if needed

---

## Additional Resources

- **PID Tuning Guide**: Ziegler-Nichols method for initial gains
- **Deadband Compensation**: Use `deadband.ino` to measure actual deadband
- **Anti-windup**: Conditional integration or back-calculation methods

---

## Contact

If PID still doesn't work after these fixes, check:
1. Sensor noise (plot raw distance measurements)
2. Motor stiction (verify deadband value)
3. Mechanical issues (binding, friction)
4. Power supply (low voltage causes erratic behavior)

