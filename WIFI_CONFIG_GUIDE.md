# WiFi Configuration via Serial Port - Quick Reference

## Overview

The Universal ESP32 firmware now supports **complete configuration via serial port** - including WiFi credentials, MQTT broker IP, train ID, and UDP port. **No hardcoded values!**

## 🚀 Quick Start

### Complete Configuration in One Command

```bash
python3 configure_esp32.py --port COM3 \
  --wifi "MyNetwork:MyPassword" \
  --broker 192.168.1.100 \
  --train trainA \
  --udp 5555
```

That's it! Your ESP32 is now fully configured and ready to use.

## Serial Commands

### WiFi Configuration

```
SET_WIFI:MySSID:MyPassword
```

**Examples:**
```
SET_WIFI:HomeWiFi:password123
SET_WIFI:LabNetwork:SuperSecret2024
SET_WIFI:TICS322:esp32esp32
```

### Show WiFi Configuration

```
GET_WIFI
```

Output:
```
========================================
WIFI CONFIGURATION
========================================
SSID: HomeWiFi
Password: 11 characters
Configured: YES
========================================
```

### Complete Configuration Commands

```
SET_TRAIN:trainA:5555           # Train ID and UDP port
SET_BROKER:192.168.1.100        # MQTT broker IP
SET_WIFI:MyNetwork:MyPassword   # WiFi credentials
GET_TRAIN                       # Show all configuration
STATUS                          # Show config + connection status
RESET_TRAIN                     # Clear all configuration
```

## Python Tool Usage

### Configure WiFi Only

```bash
python3 configure_esp32.py --port COM3 --wifi "MyNetwork:MyPassword"
```

### Configure Everything at Once

```bash
# Windows
python3 configure_esp32.py --port COM3 \
  --wifi "HomeWiFi:password123" \
  --broker 192.168.1.100 \
  --train trainA \
  --udp 5555

# Linux
python3 configure_esp32.py --port /dev/ttyUSB0 \
  --wifi "LabNetwork:secret" \
  --broker 10.0.0.50 \
  --train trainB \
  --udp 5556

# macOS
python3 configure_esp32.py --port /dev/cu.usbserial-1420 \
  --wifi "Office:WPA2password" \
  --broker 172.20.10.1 \
  --train trainC \
  --udp 5557
```

### Show Current WiFi Configuration

```bash
python3 configure_esp32.py --port COM3 --status
```

## Arduino Serial Monitor

1. **Open Serial Monitor** (Tools → Serial Monitor)
2. **Set baud rate to 115200**
3. **Type commands:**

```
SET_WIFI:MyNetwork:MyPassword
```

ESP32 responds:
```
Setting WiFi credentials...
  SSID: MyNetwork
  Password: 10 characters

WiFi credentials saved to EEPROM!
  SSID: MyNetwork
  Password: 10 characters

Restarting to connect to WiFi...
```

## Common Scenarios

### Scenario 1: New ESP32 Setup

**Flash firmware once, then configure via serial:**

```bash
# 1. Upload firmware via Arduino IDE (one time)
# Upload: tren_esp_universal/tren_esp_universal.ino

# 2. Configure everything via USB
python3 configure_esp32.py --port COM3 \
  --wifi "TICS322:esp32esp32" \
  --broker 192.168.137.1 \
  --train trainA \
  --udp 5555
```

### Scenario 2: Changing Networks

**Moving from home to lab:**

```bash
# At home
python3 configure_esp32.py --port COM3 --wifi "HomeWiFi:password123"

# At lab (different WiFi and broker)
python3 configure_esp32.py --port COM3 \
  --wifi "LabNetwork:secret" \
  --broker 10.0.0.50
```

**No need to change train ID or UDP port!**

### Scenario 3: Multiple Trains, Same Network

```bash
# Train A
python3 configure_esp32.py --port COM3 \
  --wifi "TICS322:esp32esp32" \
  --broker 192.168.137.1 \
  --train trainA \
  --udp 5555

# Train B (same WiFi/broker, different train)
python3 configure_esp32.py --port COM4 \
  --wifi "TICS322:esp32esp32" \
  --broker 192.168.137.1 \
  --train trainB \
  --udp 5556

# Train C
python3 configure_esp32.py --port COM5 \
  --wifi "TICS322:esp32esp32" \
  --broker 192.168.137.1 \
  --train trainC \
  --udp 5557
```

### Scenario 4: Different Networks per Train

**For students taking trains home:**

```bash
# Student 1's home network
python3 configure_esp32.py --port COM3 \
  --wifi "Student1Home:password" \
  --broker 192.168.1.100 \
  --train trainA \
  --udp 5555

# Student 2's home network
python3 configure_esp32.py --port COM4 \
  --wifi "Student2Home:secret" \
  --broker 192.168.0.50 \
  --train trainB \
  --udp 5556
```

### Scenario 5: Hotspot Configuration

**Windows Mobile Hotspot:**
```bash
python3 configure_esp32.py --port COM3 \
  --wifi "DESKTOP-ABC123 4567:password" \
  --broker 192.168.137.1
```

**Ubuntu Hotspot:**
```bash
python3 configure_esp32.py --port /dev/ttyUSB0 \
  --wifi "Ubuntu-Hotspot:password" \
  --broker 10.42.0.1
```

**macOS Hotspot:**
```bash
python3 configure_esp32.py --port /dev/cu.usbserial-1420 \
  --wifi "Johns-MacBook-Pro:password" \
  --broker 172.20.10.1
```

## Special Cases

### WiFi SSID with Spaces

**Use quotes around the entire parameter:**

```bash
python3 configure_esp32.py --port COM3 --wifi "My Home Network:password123"
```

### WiFi Password with Special Characters

**Works with most special characters:**

```bash
python3 configure_esp32.py --port COM3 --wifi "Network:P@ssw0rd!2024"
```

**Note:** Avoid colons (`:`) in passwords as they're used as separators.

### No Password (Open Network)

```bash
python3 configure_esp32.py --port COM3 --wifi "OpenNetwork:"
```

Or via serial:
```
SET_WIFI:OpenNetwork:
```

## Troubleshooting

### ESP32 Won't Connect to WiFi

1. **Check WiFi credentials:**
   ```
   GET_WIFI
   ```

2. **Verify SSID and password are correct**

3. **Check WiFi signal strength** - ESP32 must be in range

4. **Verify WiFi is 2.4GHz** - ESP32 doesn't support 5GHz

5. **Try resetting and reconfiguring:**
   ```bash
   python3 configure_esp32.py --port COM3 --reset
   python3 configure_esp32.py --port COM3 --wifi "Network:Password"
   ```

### Wrong WiFi Credentials Set

**Just overwrite with correct ones:**
```bash
python3 configure_esp32.py --port COM3 --wifi "CorrectSSID:CorrectPassword"
```

### WiFi Connects but MQTT Doesn't

1. **Check broker IP:**
   ```bash
   python3 configure_esp32.py --port COM3 --status
   ```

2. **Verify broker is on the same network:**
   - ESP32 should get an IP on the WiFi network
   - Broker IP must be reachable from that network

3. **Update broker IP if needed:**
   ```bash
   python3 configure_esp32.py --port COM3 --broker 192.168.1.100
   ```

### Serial Port Not Responding

1. **Close other programs** (Arduino IDE, PlatformIO)
2. **Unplug and replug USB cable**
3. **Press RESET button on ESP32**
4. **Try again**

## Default Values

If WiFi credentials are not configured, defaults are used:
- **Default SSID:** `TICS322`
- **Default Password:** `esp32esp32`
- **Default Broker:** `192.168.137.1`
- **Default UDP Port:** `5555`

## EEPROM Storage

All configuration is stored in ESP32 Preferences (non-volatile memory):

**Namespace:** `train-config`

**Keys:**
- `wifi_ssid` (String) - WiFi network name
- `wifi_password` (String) - WiFi password
- `mqtt_broker` (String) - MQTT broker IP
- `train_id` (String) - Train identifier
- `udp_port` (Int) - UDP destination port
- `wifi_configured` (Bool) - WiFi credentials status
- `configured` (Bool) - Train configuration status

## Benefits

✅ **No Hardcoded Credentials** - Everything configurable via serial

✅ **One Firmware for All** - Same firmware for all trains and networks

✅ **Easy Network Changes** - Switch WiFi networks without reflashing

✅ **Student-Friendly** - Non-technical users can configure

✅ **Multi-Network Support** - Different trains on different networks

✅ **Hotspot Compatible** - Works with Windows/Ubuntu/macOS hotspots

✅ **Persistent Configuration** - Survives reboots and power loss

✅ **Fast Deployment** - Configure 10 trains in minutes

## Example Workflows

### Instructor Setup for Class

```bash
# Configure 5 trains for classroom
for i in {1..5}; do
  python3 configure_esp32.py --port COM$i \
    --wifi "ClassroomWiFi:password" \
    --broker 192.168.1.100 \
    --train train$i \
    --udp $((5554 + $i))
done
```

### Student Taking Train Home

```bash
# Before leaving: reconfigure for home WiFi
python3 configure_esp32.py --port COM3 \
  --wifi "MyHomeWiFi:mypassword" \
  --broker 192.168.1.50
```

### Returning to Lab

```bash
# Reconfigure for lab WiFi
python3 configure_esp32.py --port COM3 \
  --wifi "LabNetwork:labpassword" \
  --broker 10.0.0.50
```

## Security Notes

⚠️ **WiFi passwords are stored in EEPROM in plain text**

**Recommendations:**
- Use dedicated IoT WiFi networks
- Don't use your main personal WiFi password
- For classroom use, use a shared password that's okay to be visible
- Consider network isolation for ESP32 devices

## See Also

- **MQTT_BROKER_CONFIG_GUIDE.md** - MQTT broker IP configuration
- **FIRMWARE_CONFIG_GUIDE.md** - Complete firmware configuration
- **README_platform.md** - Dashboard platform documentation
