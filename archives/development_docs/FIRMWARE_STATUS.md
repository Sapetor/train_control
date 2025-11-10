# Arduino Firmware Status

## CURRENT FIRMWARE (USE THIS)

**Folder:** `tren_esp_unified_FIXED/`
**Main file:** `tren_esp_unified_FIXED.ino`

### Features
- PID Control Mode (original functionality)
- Step Response Mode (with ESP32 mode switching)
- **Deadband Calibration Mode** (new, with fixes)

### Recent Fixes (Nov 6, 2025)
1. **Deadband Algorithm Rewrite** (lines 335-420)
   - Handles noisy ToF sensor (±13cm noise)
   - Always increments PWM regardless of sensor noise
   - Averages 10 readings for initial position
   - Averages 3 readings for current position
   - Only detects motion after PWM > 50

2. **UDP Final Packet Fix** (lines 396-398)
   - Sends final UDP packet with `motion_detected=1` BEFORE stopping motor
   - Critical fix: ensures dashboard receives calibration result
   ```cpp
   // IMPORTANT: Send final UDP packet with motion_detected=1 before stopping
   send_udp_deadband_data();
   delay(50);  // Give time for UDP packet to be sent
   ```

3. **UDP Data Format** (line 770-784)
   ```cpp
   // Format: time, pwm, distance, initial_distance, motion_detected
   String cadena = String(time_now) + "," +
                   String(MotorSpeed) + "," +
                   String(medi) + "," +
                   String(initial_distance) + "," +
                   String(motion_detected ? 1 : 0);
   ```

### How to Upload
1. Open Arduino IDE
2. Open: `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino`
3. Select board: ESP32 Dev Module
4. Select port: (your ESP32 port)
5. Click Upload

### Expected Serial Output During Calibration
```
========================================
Starting Deadband Calibration
========================================
  Direction: Forward
  Motion threshold: 0.50 cm
  Initial distance (averaged): 20.68 cm
  Increasing PWM from 0 until motion detected...
  (Ignoring sensor noise - PWM will increment regardless)
  PWM: 50 - Distance: 20.60 cm (change: 0.08 cm)
========================================
✓ MOTION DETECTED!
  Deadband PWM: 100
  Initial distance: 20.68 cm
  Final distance: 19.96 cm
  Distance moved: 0.72 cm
========================================
```

---

## OLD FIRMWARE (DO NOT USE)

### tren_esp/
- Original modular firmware
- No deadband calibration support
- Outdated

### tren_esp_FIXED/
- Fixed version of original
- No deadband calibration support
- Outdated

### tren_esp_unified/
- First attempt at unified firmware
- Has deadband calibration but with bugs:
  - Original algorithm couldn't handle sensor noise
  - No final UDP packet send
  - Results never reached dashboard
- **DO NOT USE** - superseded by `tren_esp_unified_FIXED/`

---

## Folder Structure Requirements

**IMPORTANT:** Arduino IDE requires the main .ino file to have the **same name as the folder**.

Correct:
```
tren_esp_unified_FIXED/
  ├── tren_esp_unified_FIXED.ino  ← matches folder name
  ├── actuadores.ino
  └── sensores.ino
```

Incorrect:
```
tren_esp_unified_FIXED/
  ├── tren_esp_unified_COMPLETE.ino  ← wrong name!
  ├── actuadores.ino
  └── sensores.ino
```

---

## Integration with Dashboard

The firmware works with `train_control_platform.py` dashboard.

### MQTT Topics Used
- `trenes/deadband/start` - Start calibration
- `trenes/deadband/direction` - Set motor direction (0=forward, 1=backward)
- `trenes/deadband/pwm_increment` - Set PWM increment per step (default: 5)
- `trenes/deadband/pwm_delay` - Set delay between steps in ms (default: 100)
- `trenes/deadband/result` - ESP32 publishes final PWM value here

### UDP Data Stream
Format: `time,pwm,distance,initial_distance,motion_detected`
- Sent to `mqtt_server` IP on port `5555`
- `motion_detected` = 0 during calibration, 1 when motion detected

---

## Testing Checklist

After uploading firmware:

1. **Network Connection**
   - [ ] ESP32 connects to WiFi
   - [ ] ESP32 connects to MQTT broker
   - [ ] Dashboard receives UDP data

2. **PID Mode**
   - [ ] Can start/stop PID experiment
   - [ ] Can adjust Kp, Ki, Kd parameters
   - [ ] Can change reference position
   - [ ] Data appears in dashboard graphs

3. **Step Response Mode**
   - [ ] Can switch to step response mode
   - [ ] ESP32 acknowledges mode switch
   - [ ] Can set step parameters
   - [ ] Step response data collected

4. **Deadband Calibration**
   - [ ] Can start deadband calibration
   - [ ] PWM increments from 0 (see serial monitor)
   - [ ] Motion detected at correct PWM (~100)
   - [ ] **Dashboard shows calibration result** (this was the bug)
   - [ ] "Apply to PID" button works

---

## Troubleshooting

### Dashboard doesn't show calibration result
1. Verify you uploaded `tren_esp_unified_FIXED.ino` with lines 396-398 fix
2. Check ESP32 serial monitor shows "✓ MOTION DETECTED!"
3. Restart dashboard with `start_fresh.bat`
4. Check Python terminal for "[DEADBAND] ✓ Motion detected! Calibrated deadband = X PWM"

### Calibration never detects motion
1. Check ToF sensor is working (serial monitor shows distance readings)
2. Check train can actually move (not stuck, wheels touching track)
3. Check motor direction is correct for your setup
4. If sensor is very noisy, increase `motion_threshold` (currently 0.5 cm)

### PWM doesn't increment
1. Check ESP32 received MQTT start command
2. Check `experimentActive` is true (serial monitor)
3. Verify `loop_deadband_experiment()` is being called

---

## Version History

- **v1.0** (tren_esp) - Original PID control
- **v2.0** (tren_esp_unified) - Added step response + deadband (buggy)
- **v3.0** (tren_esp_unified_FIXED) - Fixed deadband algorithm + UDP packet send

Last updated: Nov 6, 2025
