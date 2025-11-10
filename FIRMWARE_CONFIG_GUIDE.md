# ESP32 Universal Firmware Configuration Guide

## Overview

The universal firmware (`tren_esp_universal.ino`) allows **one firmware to be uploaded to all ESP32 train units**, then configured individually via serial commands. Each train stores its unique configuration (Train ID, UDP port) in EEPROM, eliminating the need to modify and recompile firmware for each train.

## Key Features

- **One Firmware, Multiple Trains**: Upload the same firmware to all ESP32s
- **EEPROM Storage**: Configuration persists across power cycles
- **Serial Configuration**: Easy setup via serial commands or Python tool
- **Dynamic MQTT Topics**: Automatically generated based on Train ID
- **LED Status Feedback**: Visual indication of configuration and connection status
- **No Recompilation Needed**: Configure trains in seconds without Arduino IDE

## Files

1. **tren_esp_universal.ino** - Universal firmware (upload to all ESP32s)
2. **configure_train.py** - Python configuration tool
3. **actuadores.ino** - Motor control functions (unchanged)
4. **sensores.ino** - ToF sensor functions (unchanged)

## LED Status Indicators

| LED Pattern | Meaning | Action |
|-------------|---------|--------|
| Fast blink (200ms) | Not configured | Send SET_TRAIN command |
| Slow blink (1s) | Configured, connecting | Wait for WiFi/MQTT connection |
| Solid ON | Operational | Train is ready |
| 3 quick flashes | Config saved | Rebooting... |

## Configuration Parameters

Each train needs two configuration parameters:

### 1. Train ID (String)
- Unique identifier for the train
- Used to generate MQTT topic prefix
- Examples: `trainA`, `trainB`, `trainC`, `train1`, `train2`
- Must be alphanumeric (no spaces or special characters)

### 2. UDP Port (Integer)
- Port number for sending UDP data to dashboard
- Must be unique per train on the same network
- Range: 1024-65535
- Common assignments: 5555, 5556, 5557, 5558, etc.

### Example Configurations

| Train Unit | Train ID | UDP Port | MQTT Prefix |
|------------|----------|----------|-------------|
| ESP32 #1 | trainA | 5555 | trenes/trainA |
| ESP32 #2 | trainB | 5556 | trenes/trainB |
| ESP32 #3 | trainC | 5557 | trenes/trainC |
| ESP32 #4 | train1 | 5558 | trenes/train1 |

## Installation Steps

### Step 1: Upload Universal Firmware

1. Open Arduino IDE
2. Open `tren_esp_unified_FIXED/tren_esp_universal.ino`
3. Connect ESP32 via USB
4. Select board: **ESP32 Dev Module**
5. Select correct COM port (e.g., COM3)
6. Click **Upload**
7. Wait for "Done uploading" message
8. **Repeat for all ESP32 units**

### Step 2: Configure Each ESP32

**Option A: Python Configuration Tool (Recommended)**

```bash
# Interactive mode (auto-detect COM port)
python configure_train.py

# Direct configuration
python configure_train.py --train trainA --udp 5555 --port COM3

# Get current configuration
python configure_train.py --get-config --port COM3
```

**Option B: Serial Monitor (Manual)**

1. Open Arduino IDE Serial Monitor (115200 baud)
2. Send command: `SET_TRAIN:trainA:5555`
3. Wait for confirmation and reboot
4. Verify with: `GET_TRAIN`

### Step 3: Verify Configuration

After configuration, the ESP32 will reboot and show:

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

## Serial Commands Reference

### SET_TRAIN:trainID:port
Configure the ESP32 with Train ID and UDP port.

**Syntax:**
```
SET_TRAIN:trainID:port
```

**Examples:**
```
SET_TRAIN:trainA:5555
SET_TRAIN:trainB:5556
SET_TRAIN:carroD:5557
SET_TRAIN:train1:5558
```

**Response:**
```
Configuring train...
  Train ID: trainA
  UDP Port: 5555
Configuration saved to EEPROM!
[LED flashes 3 times]
Rebooting...
```

### GET_TRAIN
Display current configuration.

**Syntax:**
```
GET_TRAIN
```

**Response:**
```
========================================
CURRENT CONFIGURATION
========================================
Status: CONFIGURED
Train ID: trainA
UDP Port: 5555
MQTT Prefix: trenes/trainA
WiFi: CONNECTED
IP Address: 192.168.1.100
MQTT: CONNECTED
========================================
```

### RESET_TRAIN
Clear configuration and return to config mode.

**Syntax:**
```
RESET_TRAIN
```

**Response:**
```
Configuration cleared!
Rebooting to config mode...
```

### STATUS
Show connection status and parameters.

**Syntax:**
```
STATUS
```

**Response:**
Same as GET_TRAIN.

## Python Configuration Tool Usage

### Installation

Requires `pyserial`:

```bash
pip install pyserial
```

### Interactive Mode

```bash
python configure_train.py
```

**Features:**
- Auto-detects ESP32 COM ports
- Interactive menu
- Guided configuration
- Input validation

**Menu Options:**
1. Configure Train (Set ID + UDP Port)
2. Get Current Configuration
3. Get Status
4. Reset Configuration
5. Exit

### Command-Line Mode

**Configure train:**
```bash
python configure_train.py --train trainA --udp 5555 --port COM3
```

**Get configuration:**
```bash
python configure_train.py --get-config --port COM3
```

**Reset configuration:**
```bash
python configure_train.py --reset --port COM3
```

**Specify baud rate:**
```bash
python configure_train.py --baudrate 115200 --port COM3
```

### Auto-Detection

The tool automatically detects ESP32 devices by looking for:
- CP210x USB-to-Serial (most common)
- CH340 USB-to-Serial
- Generic USB-SERIAL adapters

If multiple ESP32s are connected, it prompts you to select which one to configure.

## MQTT Topic Structure

All MQTT topics are dynamically generated based on the Train ID.

**Format:**
```
trenes/{train_id}/{topic}
```

### PID Control Topics

| Topic | Description | Example (trainA) |
|-------|-------------|------------------|
| `/sync` | Start/Stop PID | `trenes/trainA/sync` |
| `/carroD/p` | Kp parameter | `trenes/trainA/carroD/p` |
| `/carroD/i` | Ki parameter | `trenes/trainA/carroD/i` |
| `/carroD/d` | Kd parameter | `trenes/trainA/carroD/d` |
| `/ref` | Reference value | `trenes/trainA/ref` |
| `/carroD/p/status` | Kp confirmation | `trenes/trainA/carroD/p/status` |
| `/carroD/request_params` | Request all params | `trenes/trainA/carroD/request_params` |

### Step Response Topics

| Topic | Description | Example (trainA) |
|-------|-------------|------------------|
| `/step/sync` | Start/Stop Step | `trenes/trainA/step/sync` |
| `/step/amplitude` | Step amplitude (V) | `trenes/trainA/step/amplitude` |
| `/step/time` | Step duration (s) | `trenes/trainA/step/time` |
| `/step/direction` | Motor direction | `trenes/trainA/step/direction` |
| `/step/vbatt` | Battery voltage | `trenes/trainA/step/vbatt` |
| `/step/amplitude/status` | Amplitude confirmation | `trenes/trainA/step/amplitude/status` |
| `/step/request_params` | Request all params | `trenes/trainA/step/request_params` |

### Deadband Calibration Topics

| Topic | Description | Example (trainA) |
|-------|-------------|------------------|
| `/deadband/sync` | Start/Stop Calibration | `trenes/trainA/deadband/sync` |
| `/deadband/direction` | Motor direction | `trenes/trainA/deadband/direction` |
| `/deadband/threshold` | Motion threshold (cm) | `trenes/trainA/deadband/threshold` |
| `/deadband/result` | Calibrated deadband | `trenes/trainA/deadband/result` |
| `/deadband/apply` | Apply to PID mode | `trenes/trainA/deadband/apply` |
| `/deadband/direction/status` | Direction confirmation | `trenes/trainA/deadband/direction/status` |
| `/deadband/request_params` | Request all params | `trenes/trainA/deadband/request_params` |

## Dashboard Integration

### Updating Dashboard for Multiple Trains

The dashboard needs to be configured to listen for multiple trains. Modify the MQTT topic subscriptions:

**Original (single train):**
```python
MQTT_TOPICS = {
    'sync': 'trenes/carroD/sync',
    'kp': 'trenes/carroD/p',
    # ...
}
```

**Updated (multi-train support):**
```python
def get_mqtt_topics(train_id):
    """Generate MQTT topics for specific train"""
    prefix = f"trenes/{train_id}"
    return {
        'sync': f'{prefix}/sync',
        'kp': f'{prefix}/carroD/p',
        'ki': f'{prefix}/carroD/i',
        'kd': f'{prefix}/carroD/d',
        'ref': f'{prefix}/ref',
        # ... add all other topics
    }

# Usage
train_id = "trainA"  # Get from user selection
topics = get_mqtt_topics(train_id)
client.subscribe(topics['sync'])
```

### UDP Port Configuration

Update dashboard UDP receiver to listen on the correct port for each train:

```python
# Single train (original)
UDP_PORT = 5555

# Multi-train support
train_configs = {
    'trainA': {'udp_port': 5555, 'mqtt_prefix': 'trenes/trainA'},
    'trainB': {'udp_port': 5556, 'mqtt_prefix': 'trenes/trainB'},
    'trainC': {'udp_port': 5557, 'mqtt_prefix': 'trenes/trainC'},
}

selected_train = 'trainA'
udp_port = train_configs[selected_train]['udp_port']
mqtt_prefix = train_configs[selected_train]['mqtt_prefix']
```

## Troubleshooting

### Issue: ESP32 Stuck in Config Mode (Fast Blinking)

**Symptoms:**
- LED blinks fast continuously
- Serial monitor shows "CONFIGURATION MODE" message
- No WiFi connection

**Solution:**
1. Connect to serial monitor (115200 baud)
2. Send command: `SET_TRAIN:trainA:5555`
3. Wait for reboot
4. Verify with: `GET_TRAIN`

### Issue: Configuration Not Saving

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

### Issue: MQTT Topics Not Working

**Symptoms:**
- Dashboard doesn't receive MQTT messages
- ESP32 shows "MQTT Connected" but no data

**Possible Causes:**
1. Dashboard listening to wrong MQTT prefix
2. Train ID mismatch between firmware and dashboard

**Solution:**
1. Check train ID with: `GET_TRAIN`
2. Verify MQTT prefix matches dashboard configuration
3. Use MQTT Explorer tool to monitor topics
4. Example: If ESP32 uses `trenes/trainA`, dashboard must subscribe to `trenes/trainA/*`

### Issue: UDP Data Not Received

**Symptoms:**
- MQTT works but no UDP data in dashboard
- Graphs don't update

**Possible Causes:**
1. Dashboard listening on wrong UDP port
2. UDP port conflict (multiple trains using same port)
3. Firewall blocking UDP

**Solution:**
1. Verify UDP port matches: `GET_TRAIN`
2. Ensure each train has unique UDP port
3. Check Windows Firewall allows Python UDP
4. Test with: `netstat -an | findstr 5555` (Windows) or `netstat -an | grep 5555` (Linux)

### Issue: Python Tool Can't Find ESP32

**Symptoms:**
- "No ESP32 devices detected"
- COM port not listed

**Solution:**
1. Install CP210x or CH340 USB drivers
2. Check Device Manager (Windows) for COM port
3. Try unplugging/replugging USB cable
4. Manually specify port: `python configure_train.py --port COM3`

### Issue: Serial Monitor Shows Garbled Text

**Symptoms:**
- Random characters in serial monitor
- Can't read configuration output

**Solution:**
1. Set baud rate to **115200** (not 9600)
2. Select "Both NL & CR" line ending
3. Close and reopen serial monitor
4. Press ESP32 RESET button

## Configuration Examples

### Scenario 1: Three Trains in Lab

**Train A (ESP32 #1):**
```bash
python configure_train.py --train trainA --udp 5555 --port COM3
```

**Train B (ESP32 #2):**
```bash
python configure_train.py --train trainB --udp 5556 --port COM4
```

**Train C (ESP32 #3):**
```bash
python configure_train.py --train trainC --udp 5557 --port COM5
```

### Scenario 2: Replacing Failed ESP32

**Old ESP32 (trainB):**
- Train ID: `trainB`
- UDP Port: 5556

**New ESP32:**
1. Upload universal firmware
2. Configure with same parameters:
   ```bash
   python configure_train.py --train trainB --udp 5556 --port COM3
   ```
3. Plug into system (no dashboard changes needed)

### Scenario 3: Reconfiguring Train

**Current:**
- Train ID: `train1`
- UDP Port: 5555

**Want to change to:**
- Train ID: `trainA`
- UDP Port: 5558

**Steps:**
1. Reset configuration: `RESET_TRAIN`
2. Wait for reboot to config mode
3. Set new configuration: `SET_TRAIN:trainA:5558`
4. Update dashboard to use new prefix and port

## Advanced Usage

### Batch Configuration Script

Configure multiple ESP32s automatically:

**Windows (batch_config.bat):**
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

**Linux (batch_config.sh):**
```bash
#!/bin/bash
echo "Configuring Train A on /dev/ttyUSB0..."
python3 configure_train.py --train trainA --udp 5555 --port /dev/ttyUSB0
sleep 15

echo "Configuring Train B on /dev/ttyUSB1..."
python3 configure_train.py --train trainB --udp 5556 --port /dev/ttyUSB1
sleep 15

echo "Configuring Train C on /dev/ttyUSB2..."
python3 configure_train.py --train trainC --udp 5557 --port /dev/ttyUSB2
sleep 15

echo "All trains configured!"
```

### Verification Script

Check configuration of all connected ESP32s:

**verify_trains.py:**
```python
import serial.tools.list_ports
import serial
import time

def check_train(port):
    try:
        ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(2)
        ser.write(b'GET_TRAIN\n')
        time.sleep(1)

        print(f"\n{port}:")
        while ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"  {line}")

        ser.close()
    except Exception as e:
        print(f"\n{port}: Error - {e}")

# Find all ESP32s
ports = serial.tools.list_ports.comports()
esp32_ports = [p.device for p in ports if any(k in p.description.upper() for k in ['CP210', 'CH340', 'USB-SERIAL'])]

print("Checking all connected ESP32s...")
for port in esp32_ports:
    check_train(port)
```

**Usage:**
```bash
python verify_trains.py
```

## Best Practices

### 1. Naming Convention
- Use consistent naming: `trainA`, `trainB`, `trainC` or `train1`, `train2`, `train3`
- Avoid special characters, spaces, or mixed case
- Keep names short (under 10 characters)

### 2. Port Assignment
- Start at 5555 and increment by 1
- Document port assignments in a spreadsheet
- Reserve ports for future expansion

### 3. Configuration Tracking
- Label each ESP32 physically (e.g., sticker with "Train A")
- Keep a configuration log:

```
| ESP32 # | Train ID | UDP Port | Last Configured | Notes |
|---------|----------|----------|-----------------|-------|
| ESP32-1 | trainA   | 5555     | 2025-11-10      | Lab A |
| ESP32-2 | trainB   | 5556     | 2025-11-10      | Lab A |
| ESP32-3 | trainC   | 5557     | 2025-11-10      | Lab B |
```

### 4. Backup Configuration
After configuring each ESP32:
1. Run `GET_TRAIN` command
2. Save serial output to file: `trainA_config.txt`
3. Store in project documentation folder

### 5. Testing Procedure
For each newly configured ESP32:
1. Verify configuration: `GET_TRAIN`
2. Check WiFi connection (IP address shown)
3. Check MQTT connection (topics subscribed)
4. Test UDP data (run dashboard and verify data reception)
5. Test experiment modes (PID, Step, Deadband)

## Firmware Updates

When updating the firmware:

### Option A: Preserve Configuration (Recommended)
1. Upload new `tren_esp_universal.ino` firmware
2. Configuration in EEPROM is preserved automatically
3. ESP32 boots with existing Train ID and UDP port

### Option B: Fresh Install
1. Upload new firmware
2. Configuration is still preserved
3. If needed, reset with: `RESET_TRAIN`
4. Reconfigure with: `SET_TRAIN:trainA:5555`

**Note:** EEPROM configuration survives firmware updates unless explicitly cleared with `RESET_TRAIN`.

## Migration from Old Firmware

### Migrating from Hardcoded Topics

**Old firmware:**
```cpp
const char* mqtt_topic = "trenes/carroD/p";
const int udpPort = 5555;
```

**Universal firmware:**
- No code changes needed
- Configure via serial: `SET_TRAIN:carroD:5555`
- Results in identical behavior

**Migration Steps:**
1. Note old train's MQTT prefix and UDP port
2. Upload universal firmware
3. Configure with same values
4. No dashboard changes required

## FAQ

**Q: Can I change configuration without resetting?**
A: Yes, just send a new `SET_TRAIN` command. It will overwrite the existing configuration.

**Q: What happens if I configure two trains with the same ID?**
A: Both trains will respond to the same MQTT topics, causing conflicts. Always use unique IDs.

**Q: What happens if two trains use the same UDP port?**
A: The dashboard will receive mixed data from both trains. Always use unique ports.

**Q: Can I use the old hardcoded firmware and universal firmware together?**
A: Yes, as long as they use different Train IDs and UDP ports.

**Q: How do I know which firmware version is running?**
A: Check the serial monitor on boot:
- Universal firmware shows: "UNIVERSAL Train Control Firmware"
- Old firmware shows: "Unified Train Control - COMPLETE VERSION"

**Q: Can I configure trains over WiFi instead of serial?**
A: Not currently implemented. Configuration requires physical USB connection.

**Q: What if I forget a train's configuration?**
A: Connect via serial and send `GET_TRAIN` command to retrieve it.

**Q: Can I backup and restore configurations?**
A: Configurations are stored in ESP32 EEPROM. To backup, save the output of `GET_TRAIN` command. To restore, send `SET_TRAIN` command with saved values.

## Contact & Support

For issues or questions:
1. Check this guide's Troubleshooting section
2. Review serial monitor output for error messages
3. Verify configuration with `GET_TRAIN` and `STATUS` commands
4. Check MQTT topics with MQTT Explorer tool
5. Test UDP connectivity with network monitoring tools

## Change Log

**Version 1.0 (2025-11-10):**
- Initial universal firmware release
- EEPROM configuration support
- Dynamic MQTT topic generation
- LED status feedback
- Serial command interface
- Python configuration tool

---

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Firmware Version:** tren_esp_universal.ino v1.0
