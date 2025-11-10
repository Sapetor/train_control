# ESP32 Universal Train Firmware - Complete Guide

## Table of Contents
1. [Overview](#overview)
2. [Quick Reference](#quick-reference)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [MQTT Topics](#mqtt-topics)
6. [Dashboard Integration](#dashboard-integration)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)
9. [Advanced Usage](#advanced-usage)

---

## Overview

### What is Universal Firmware?

The universal firmware (`tren_esp_universal.ino`) allows **one firmware to be uploaded to all ESP32 train units**, then configured individually via serial commands. Each train stores its unique configuration (Train ID, UDP port) in EEPROM, eliminating the need to modify and recompile firmware for each train.

### Key Benefits

- ✅ **One Firmware, Multiple Trains** - Upload once to all ESP32s
- ✅ **EEPROM Storage** - Configuration persists across power cycles
- ✅ **Serial Configuration** - Easy setup in 30 seconds
- ✅ **Dynamic MQTT Topics** - Auto-generated based on Train ID
- ✅ **LED Status Feedback** - Visual indication of state
- ✅ **No Recompilation** - Add new trains instantly

### Time Savings

| Operation | Before | After | Savings |
|-----------|--------|-------|---------|
| Configure new train | 15 min | 30 sec | 97% |
| Replace failed ESP32 | 30 min | 1 min | 97% |
| Add train to lab | 20 min | 1 min | 95% |

---

## Quick Reference

### Serial Commands (115200 baud)

```
SET_TRAIN:trainID:port    Configure train
GET_TRAIN                 Show configuration
RESET_TRAIN               Clear configuration
STATUS                    Show status
```

### Python Configuration Tool

```bash
# Interactive mode
python configure_train.py

# Direct config
python configure_train.py --train trainA --udp 5555 --port COM3

# Check config
python configure_train.py --get-config --port COM3
```

### LED Status Indicators

| LED Pattern | Meaning | Action Required |
|-------------|---------|-----------------|
| Fast blink (200ms) | Not configured | Send `SET_TRAIN` command |
| Slow blink (1s) | Connecting to WiFi/MQTT | Wait for connection |
| Solid ON | Operational and ready | None - ready for experiments |
| 3 quick flashes | Config saved successfully | ESP32 is rebooting |

### Example Configurations

| Train | Command | UDP Port | MQTT Prefix |
|-------|---------|----------|-------------|
| Train A | `SET_TRAIN:trainA:5555` | 5555 | trenes/trainA |
| Train B | `SET_TRAIN:trainB:5556` | 5556 | trenes/trainB |
| Train C | `SET_TRAIN:trainC:5557` | 5557 | trenes/trainC |

---

## Installation

### Step 1: Upload Universal Firmware

**IMPORTANT:** The `.ino` file MUST be in a folder with the same name for Arduino IDE.

1. Open Arduino IDE
2. Navigate to: `tren_esp_universal/tren_esp_universal.ino`
3. Connect ESP32 via USB
4. Select board: **ESP32 Dev Module**
5. Select correct COM port (e.g., COM3, /dev/ttyUSB0)
6. Click **Upload**
7. Wait for "Done uploading" message
8. **Repeat for all ESP32 units** (same firmware for all)

### Step 2: Install Python Configuration Tool (Optional)

If using the Python tool for configuration:

```bash
pip install pyserial
```

### Step 3: Verify Upload

After upload completes:
- LED should blink **fast** (200ms interval)
- Serial monitor shows: `"TRAIN NOT CONFIGURED - ENTERING CONFIG MODE"`

---

## Configuration

### Option A: Python Tool (Recommended)

**Interactive Mode:**
```bash
python configure_train.py
```

The tool will:
1. Auto-detect ESP32 COM ports
2. Show interactive menu
3. Guide you through configuration
4. Validate inputs
5. Show real-time feedback

**Command-Line Mode:**
```bash
# Configure Train A
python configure_train.py --train trainA --udp 5555 --port COM3

# Get current configuration
python configure_train.py --get-config --port COM3

# Reset configuration
python configure_train.py --reset --port COM3

# Specify baud rate
python configure_train.py --baudrate 115200 --port COM3
```

### Option B: Serial Monitor (Manual)

1. Open Arduino IDE Serial Monitor
2. Set baud rate to **115200**
3. Set line ending to **Both NL & CR**
4. Send command: `SET_TRAIN:trainA:5555`
5. Wait for LED to flash 3 times
6. Wait for ESP32 to reboot
7. Verify with: `GET_TRAIN`

### Configuration Parameters

#### Train ID
- Unique identifier for the train
- Used to generate MQTT topic prefix
- **Must be alphanumeric** (no spaces or special characters)
- Examples: `trainA`, `trainB`, `train1`, `carroD`

#### UDP Port
- Port number for sending data to dashboard
- **Must be unique** per train on same network
- Range: 1024-65535 (recommended: 5555-5600)

### Verification

After configuration, ESP32 will reboot and display:

```
========================================
TRAIN CONFIGURATION LOADED
========================================
Train ID: trainA
UDP Port: 5555
MQTT Prefix: trenes/trainA
========================================

Connecting to WiFi: TICS322
WiFi connected!
IP address: 192.168.1.100

MQTT Connected!
Subscribed to all topics with prefix: trenes/trainA

========================================
Setup Complete! Ready for experiments.
Available experiments:
  - PID Control: trenes/trainA/sync
  - Step Response: trenes/trainA/step/sync
  - Deadband Cal: trenes/trainA/deadband/sync
========================================
```

**LED Status:** Solid ON (operational)

---

## MQTT Topics

All MQTT topics are dynamically generated based on Train ID.

**Format:** `trenes/{train_id}/{topic}`

### PID Control Topics (trainA example)

| Topic | Description | Example |
|-------|-------------|---------|
| `/sync` | Start/Stop PID | `trenes/trainA/sync` |
| `/carroD/p` | Kp parameter | `trenes/trainA/carroD/p` |
| `/carroD/i` | Ki parameter | `trenes/trainA/carroD/i` |
| `/carroD/d` | Kd parameter | `trenes/trainA/carroD/d` |
| `/ref` | Reference value | `trenes/trainA/ref` |
| `/carroD/p/status` | Kp confirmation | `trenes/trainA/carroD/p/status` |
| `/carroD/i/status` | Ki confirmation | `trenes/trainA/carroD/i/status` |
| `/carroD/d/status` | Kd confirmation | `trenes/trainA/carroD/d/status` |
| `/ref/status` | Ref confirmation | `trenes/trainA/carroD/ref/status` |
| `/carroD/request_params` | Request all params | `trenes/trainA/carroD/request_params` |

### Step Response Topics

| Topic | Description | Example |
|-------|-------------|---------|
| `/step/sync` | Start/Stop Step | `trenes/trainA/step/sync` |
| `/step/amplitude` | Step amplitude (V) | `trenes/trainA/step/amplitude` |
| `/step/time` | Step duration (s) | `trenes/trainA/step/time` |
| `/step/direction` | Motor direction | `trenes/trainA/step/direction` |
| `/step/vbatt` | Battery voltage | `trenes/trainA/step/vbatt` |
| `/step/amplitude/status` | Amplitude confirmation | `trenes/trainA/step/amplitude/status` |
| `/step/time/status` | Time confirmation | `trenes/trainA/step/time/status` |
| `/step/direction/status` | Direction confirmation | `trenes/trainA/step/direction/status` |
| `/step/vbatt/status` | Vbatt confirmation | `trenes/trainA/step/vbatt/status` |
| `/step/request_params` | Request all params | `trenes/trainA/step/request_params` |

### Deadband Calibration Topics

| Topic | Description | Example |
|-------|-------------|---------|
| `/deadband/sync` | Start/Stop Calibration | `trenes/trainA/deadband/sync` |
| `/deadband/direction` | Motor direction | `trenes/trainA/deadband/direction` |
| `/deadband/threshold` | Motion threshold (cm) | `trenes/trainA/deadband/threshold` |
| `/deadband/result` | Calibrated deadband | `trenes/trainA/deadband/result` |
| `/deadband/apply` | Apply to PID mode | `trenes/trainA/deadband/apply` |
| `/deadband/direction/status` | Direction confirmation | `trenes/trainA/deadband/direction/status` |
| `/deadband/threshold/status` | Threshold confirmation | `trenes/trainA/deadband/threshold/status` |
| `/deadband/request_params` | Request all params | `trenes/trainA/deadband/request_params` |

**Total:** 28 MQTT topics per train (all dynamically generated)

---

## Dashboard Integration

### Multi-Train Configuration

The dashboard platform (`multi_train_wrapper.py`) uses `trains_config.json` to manage multiple trains.

**Example `trains_config.json`:**
```json
{
  "trains": {
    "trainA": {
      "id": "trainA",
      "name": "Train A",
      "udp_port": 5555,
      "mqtt_prefix": "trenes/trainA",
      "enabled": true
    },
    "trainB": {
      "id": "trainB",
      "name": "Train B",
      "udp_port": 5556,
      "mqtt_prefix": "trenes/trainB",
      "enabled": true
    }
  },
  "dashboard_host": "127.0.0.1",
  "dashboard_port": 8050
}
```

**CRITICAL:** ESP32 configuration MUST match dashboard configuration:
- ESP32 Train ID ↔ Dashboard `id`
- ESP32 UDP Port ↔ Dashboard `udp_port`
- ESP32 MQTT Prefix ↔ Dashboard `mqtt_prefix`

### Verification

Check that configuration matches:
```bash
# ESP32 (serial monitor)
GET_TRAIN

# Should show:
# Train ID: trainA
# UDP Port: 5555
# MQTT Prefix: trenes/trainA
```

This MUST match `trains_config.json` entry for trainA.

---

## Troubleshooting

### Issue 1: ESP32 Stuck in Config Mode (Fast LED Blink)

**Symptoms:**
- LED blinks fast continuously
- Serial monitor shows "CONFIGURATION MODE" message
- No WiFi connection

**Solution:**
1. Connect to serial monitor (115200 baud)
2. Send command: `SET_TRAIN:trainA:5555`
3. Wait for 3 LED flashes and reboot
4. Verify with: `GET_TRAIN`

---

### Issue 2: Configuration Not Saving

**Symptoms:**
- Configuration resets after power cycle
- ESP32 returns to config mode after reboot

**Possible Causes:**
1. Invalid train ID (contains spaces or special characters)
2. Invalid UDP port (outside 1024-65535 range)
3. EEPROM write failure

**Solution:**
1. Use alphanumeric train IDs only (e.g., `trainA`, not `train A`)
2. Use ports 5555-5600 for safety
3. Try resetting: `RESET_TRAIN`, then reconfigure

---

### Issue 3: Dashboard Not Receiving MQTT Messages

**Symptoms:**
- Dashboard shows "Waiting for parameters..."
- ESP32 shows "MQTT Connected" but no confirmation in dashboard

**Possible Causes:**
1. Train ID mismatch between ESP32 and dashboard
2. Dashboard subscribed to wrong MQTT prefix

**Solution:**
1. Check ESP32 train ID: `GET_TRAIN`
2. Check `trains_config.json` matches:
   ```json
   "trainA": {
     "mqtt_prefix": "trenes/trainA"  ← Must match ESP32
   }
   ```
3. Use MQTT Explorer tool to monitor topics:
   ```bash
   mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v
   ```
4. Verify ESP32 publishes to `trenes/trainA/*` topics
5. Verify dashboard subscribes to same topics

---

### Issue 4: UDP Data Not Received

**Symptoms:**
- MQTT works but no UDP data in dashboard
- Graphs don't update

**Possible Causes:**
1. Dashboard listening on wrong UDP port
2. UDP port conflict (multiple trains using same port)
3. Firewall blocking UDP

**Solution:**
1. Verify ESP32 UDP port matches dashboard:
   - ESP32: `GET_TRAIN` shows UDP Port: 5555
   - Dashboard: `trains_config.json` shows `"udp_port": 5555`
2. Ensure each train has **unique UDP port**
3. Check Windows Firewall allows Python UDP
4. Test with: `netstat -an | findstr 5555` (Windows) or `netstat -an | grep 5555` (Linux)

---

### Issue 5: Python Tool Can't Find ESP32

**Symptoms:**
- "No ESP32 devices detected"
- COM port not listed

**Solution:**
1. Install USB drivers:
   - CP210x: [Silicon Labs drivers](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers)
   - CH340: [CH340 drivers](http://www.wch-ic.com/downloads/CH341SER_EXE.html)
2. Check Device Manager (Windows) for COM port
3. Try unplugging/replugging USB cable
4. Manually specify port: `python configure_train.py --port COM3`

---

### Issue 6: Serial Monitor Shows Garbled Text

**Symptoms:**
- Random characters in serial monitor
- Can't read configuration output

**Solution:**
1. Set baud rate to **115200** (not 9600)
2. Select "Both NL & CR" line ending
3. Close and reopen serial monitor
4. Press ESP32 RESET button

---

### Issue 7: Two Trains with Same ID

**Symptoms:**
- Both trains respond to same commands
- Mixed data in dashboard

**Solution:**
- Always use **unique Train IDs**
- Check all ESP32s: `GET_TRAIN` on each
- Reconfigure duplicates: `SET_TRAIN:trainB:5556`

---

### Issue 8: Two Trains with Same UDP Port

**Symptoms:**
- Dashboard receives mixed data from both trains

**Solution:**
- Always use **unique UDP ports**
- Check all ESP32s: `GET_TRAIN` on each
- Reassign ports: 5555, 5556, 5557, etc.

---

## Best Practices

### 1. Naming Convention
- Use consistent naming: `trainA`, `trainB`, `trainC` or `train1`, `train2`, `train3`
- Avoid special characters, spaces, or mixed case
- Keep names short (under 10 characters)

### 2. Port Assignment
- Start at 5555 and increment by 1
- Document port assignments:

```
| ESP32 # | Train ID | UDP Port | MQTT Prefix | Last Config | Location |
|---------|----------|----------|-------------|-------------|----------|
| ESP32-1 | trainA   | 5555     | trenes/trainA | 2025-11-10  | Lab A   |
| ESP32-2 | trainB   | 5556     | trenes/trainB | 2025-11-10  | Lab A   |
| ESP32-3 | trainC   | 5557     | trenes/trainC | 2025-11-10  | Lab B   |
```

### 3. Physical Labeling
- Label each ESP32 with train ID (sticker or marker)
- Include UDP port on label for reference
- Example: "Train A - UDP 5555"

### 4. Configuration Backup
After configuring each ESP32:
1. Run `GET_TRAIN` command
2. Save serial output to file: `trainA_config.txt`
3. Store in project documentation folder

### 5. Testing Procedure
For each newly configured ESP32:
- [ ] Verify configuration: `GET_TRAIN`
- [ ] Check WiFi connection (IP address shown)
- [ ] Check MQTT connection (topics subscribed)
- [ ] Test UDP data (dashboard receives data)
- [ ] Test all experiment modes (PID, Step, Deadband)
- [ ] Label ESP32 physically

---

## Advanced Usage

### Batch Configuration Script

Configure multiple ESP32s automatically.

**Windows (`batch_config.bat`):**
```batch
@echo off
echo Configuring Train A on COM3...
python configure_train.py --train trainA --udp 5555 --port COM3
timeout /t 15

echo Configuring Train B on COM4...
python configure_train.py --train trainB --udp 5556 --port COM4
timeout /t 15

echo Configuring Train C on COM5...
python configure_train.py --train trainC --udp 5557 --port COM5
timeout /t 15

echo All trains configured!
pause
```

**Linux (`batch_config.sh`):**
```bash
#!/bin/bash
echo "Configuring Train A..."
python3 configure_train.py --train trainA --udp 5555 --port /dev/ttyUSB0
sleep 15

echo "Configuring Train B..."
python3 configure_train.py --train trainB --udp 5556 --port /dev/ttyUSB1
sleep 15

echo "Configuring Train C..."
python3 configure_train.py --train trainC --udp 5557 --port /dev/ttyUSB2
sleep 15

echo "All trains configured!"
```

### Replacing Failed ESP32

**Scenario:** Train B ESP32 failed, need replacement

**Steps:**
1. Get old configuration from `trains_config.json`:
   ```json
   "trainB": {
     "id": "trainB",
     "udp_port": 5556,
     "mqtt_prefix": "trenes/trainB"
   }
   ```

2. Upload universal firmware to new ESP32

3. Configure with same parameters:
   ```bash
   python configure_train.py --train trainB --udp 5556 --port COM3
   ```

4. Verify:
   ```bash
   python configure_train.py --get-config --port COM3
   ```

5. Plug into system - **no dashboard changes needed!**

### Firmware Updates

**Option A: Preserve Configuration (Recommended)**
1. Upload new `tren_esp_universal.ino` firmware
2. Configuration in EEPROM is **preserved automatically**
3. ESP32 boots with existing Train ID and UDP port

**Option B: Fresh Install**
1. Upload new firmware
2. Configuration is still preserved
3. If needed, reset with: `RESET_TRAIN`
4. Reconfigure with: `SET_TRAIN:trainA:5555`

**Note:** EEPROM configuration survives firmware updates unless explicitly cleared with `RESET_TRAIN`.

---

## FAQ

**Q: Can I change configuration without resetting?**
A: Yes, just send a new `SET_TRAIN` command. It overwrites existing configuration.

**Q: What happens if two trains have the same ID?**
A: Both respond to same MQTT topics, causing conflicts. Always use unique IDs.

**Q: What happens if two trains have the same UDP port?**
A: Dashboard receives mixed data from both. Always use unique ports.

**Q: Can I use old hardcoded firmware and universal firmware together?**
A: Yes, as long as they use different Train IDs and UDP ports.

**Q: How do I know which firmware version is running?**
A: Check serial monitor on boot:
- Universal: "UNIVERSAL Train Control Firmware"
- Old: "Unified Train Control - COMPLETE VERSION"

**Q: Can I configure trains over WiFi?**
A: Not currently. Configuration requires physical USB connection.

**Q: What if I forget a train's configuration?**
A: Connect via serial and send `GET_TRAIN` to retrieve it.

**Q: Can I backup and restore configurations?**
A: Yes. Save output of `GET_TRAIN`. To restore, send `SET_TRAIN` with saved values.

---

## Technical Specifications

### Firmware
- **Platform:** ESP32 (ESP32 Dev Module)
- **Language:** C++ (Arduino framework)
- **Size:** ~36 KB compiled
- **Flash Usage:** ~29% of 1.2MB
- **RAM Usage:** ~15% of 320KB

### Libraries
- PID_v1_bc (PID control)
- WiFi (ESP32 built-in)
- PubSubClient (MQTT client)
- Wire (I2C communication)
- VL53L0X (ToF sensor)
- esp_wifi (WiFi power management)
- Preferences (EEPROM storage)

### Serial Protocol
- **Baud Rate:** 115200
- **Data Bits:** 8
- **Stop Bits:** 1
- **Parity:** None
- **Line Ending:** NL (newline)

### MQTT Protocol
- **Version:** MQTT 3.1.1
- **QoS:** 0 (fire and forget)
- **Topics:** 28 per train (dynamically generated)

### UDP Protocol
- **Port:** Configurable (default: 5555)
- **Packet Size:** ~128 bytes max
- **Format:** CSV string
- **Direction:** ESP32 → Dashboard (one-way)

---

## Contact & Support

For issues or questions:
1. Check Troubleshooting section above
2. Review serial monitor output for errors
3. Run `GET_TRAIN` and `STATUS` commands
4. Monitor MQTT with: `mosquitto_sub -h <broker-ip> -t "trenes/#" -v`
5. Test UDP with network monitoring tools

---

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Firmware Version:** tren_esp_universal.ino v1.0
**Project:** UAI SIMU Train Control Platform
