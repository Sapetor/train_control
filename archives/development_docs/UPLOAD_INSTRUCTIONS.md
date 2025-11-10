# ESP32 Firmware Upload Instructions

## What You Need to Do

Upload the **LATEST** firmware to your ESP32 to fix the deadband calibration result display issue.

---

## Step-by-Step Instructions

### 1. Open Arduino IDE

### 2. Open the Correct Firmware
- Navigate to: `tren_esp_unified_FIXED/`
- Open: `tren_esp_unified_FIXED.ino`

**CRITICAL:** Make sure you're opening the file in the `tren_esp_unified_FIXED` folder, NOT `tren_esp_unified`!

### 3. Verify the Fix is Present
Before uploading, check that line 396-398 contains:
```cpp
// IMPORTANT: Send final UDP packet with motion_detected=1 before stopping
send_udp_deadband_data();
delay(50);  // Give time for UDP packet to be sent
```

If you don't see this, you have the wrong file open!

### 4. Configure Arduino IDE
- **Board:** ESP32 Dev Module
- **Port:** (Select your ESP32's COM port)
- **Upload Speed:** 921600 (or lower if upload fails)

### 5. Upload
Click the Upload button (→) in Arduino IDE

### 6. Monitor Upload
Watch the progress bar. You should see:
```
Connecting........___
Chip is ESP32-D0WDQ6 (revision 1)
...
Writing at 0x00010000... (100%)
Hard resetting via RTS pin...
```

### 7. Open Serial Monitor
After upload completes:
- Open Serial Monitor (Tools → Serial Monitor)
- Set baud rate to **115200**
- You should see boot messages and "Connected to MQTT broker"

---

## After Upload

### 1. Restart the Dashboard
Run: `start_fresh.bat`

This will:
- Kill old Python processes
- Clear Python cache
- Start fresh dashboard instance

### 2. Test Deadband Calibration

#### What You Should See:

**ESP32 Serial Monitor:**
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

**Python Terminal (Dashboard):**
```
[DEADBAND DEBUG] PWM=50, motion_detected=0, calibrated=0
[DEADBAND DEBUG] PWM=70, motion_detected=0, calibrated=0
[DEADBAND DEBUG] PWM=90, motion_detected=0, calibrated=0
[DEADBAND] ✓ Motion detected! Calibrated deadband = 100 PWM
```

**Dashboard Web Interface:**
- "Calibrating... PWM: 100" → Changes to:
- **"Calibration Result: 100 PWM"** ← THIS IS THE FIX!
- "Apply to PID" button becomes clickable

---

## What Was Fixed

### The Problem
- ESP32 detected motion and printed "✓ MOTION DETECTED! Deadband PWM: 100"
- But dashboard never showed the result
- "Calibration Result" box stayed empty
- "Apply to PID" button didn't work

### The Root Cause
ESP32 called `send_udp_deadband_data()` BEFORE checking for motion, so the final UDP packet with `motion_detected=1` was never sent.

### The Fix
Added lines 396-398 to send final UDP packet AFTER detecting motion, BEFORE stopping the motor:
```cpp
// IMPORTANT: Send final UDP packet with motion_detected=1 before stopping
send_udp_deadband_data();
delay(50);  // Give time for UDP packet to be sent
```

Now the dashboard receives the UDP packet with `motion_detected=1` and displays the result!

---

## Troubleshooting

### "Timed out waiting for packet header" during upload
- Check USB cable is connected
- Try a different USB port
- Lower upload speed to 115200

### ESP32 connects to WiFi but not MQTT
- Check MQTT broker is running on your computer
- Check firewall isn't blocking port 1883
- Verify IP address in ESP32 config matches your network interface

### Calibration still doesn't show result
1. Verify you uploaded the correct file (`tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino`)
2. Check serial monitor output - does it show "✓ MOTION DETECTED!"?
3. Check Python terminal - does it show "[DEADBAND] ✓ Motion detected!"?
4. If ESP32 shows motion but Python doesn't, there's a network issue
5. If Python shows motion but dashboard doesn't, restart with `start_fresh.bat`

### Train doesn't move during calibration
- Check wheels are on track
- Check train isn't stuck
- Check motor direction is correct
- Try manually pushing train slightly to overcome initial friction

---

## Files Involved

### ESP32 Firmware
- `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino` - Main file (812 lines)
- `tren_esp_unified_FIXED/actuadores.ino` - Motor control functions
- `tren_esp_unified_FIXED/sensores.ino` - ToF sensor functions

### Dashboard (no changes needed)
- `train_control_platform.py` - Already has receiving code (lines 728-734)
- `start_fresh.bat` - Use this to restart dashboard

---

## Why This Matters

Without this fix:
- Deadband calibration runs but result never displays
- You can't use "Apply to PID" button
- You have to manually read PWM value from serial monitor and type it into PID tab

With this fix:
- Result automatically displays in dashboard
- "Apply to PID" button works
- Professional, automated workflow

---

Last updated: Nov 6, 2025
