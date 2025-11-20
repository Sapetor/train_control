# MQTT Broker IP Configuration via Serial Port

## Overview

The Universal ESP32 firmware now supports configuring the MQTT broker IP address via USB serial port **without reflashing**. This allows you to easily change the broker IP when switching networks or using different computers.

## Features

- ✅ Configure MQTT broker IP via serial commands
- ✅ Configuration stored in EEPROM (persists across reboots)
- ✅ No need to recompile or reflash firmware
- ✅ Independent of train configuration (can change broker without changing train ID/port)
- ✅ Python tool for easy configuration

## Serial Commands

### Set MQTT Broker IP
```
SET_BROKER:192.168.1.100
```
Sets the MQTT broker IP address and restarts the ESP32.

### Get Current Broker IP
```
GET_BROKER
```
Shows the currently configured MQTT broker IP.

### Get Full Configuration
```
GET_TRAIN
```
or
```
STATUS
```
Shows train ID, UDP port, MQTT broker IP, and connection status.

### Complete Configuration Example
```
SET_TRAIN:trainA:5555
SET_BROKER:192.168.1.100
```

## Method 1: Using Arduino Serial Monitor

1. **Connect ESP32 via USB**
2. **Open Arduino IDE → Tools → Serial Monitor**
3. **Set baud rate to 115200**
4. **Type command and press Enter:**
   ```
   SET_BROKER:192.168.1.100
   ```
5. **ESP32 will save configuration and restart**

## Method 2: Using Python Configuration Tool

### Installation
```bash
pip install pyserial
```

### List Available Ports
```bash
python3 configure_esp32.py --list
```

### Configure Broker IP
```bash
python3 configure_esp32.py --port COM3 --broker 192.168.1.100
```

### Configure Everything at Once
```bash
python3 configure_esp32.py --port /dev/ttyUSB0 --train trainA --udp 5555 --broker 192.168.1.100
```

### Show Current Configuration
```bash
python3 configure_esp32.py --port COM3 --status
```

### Reset Configuration
```bash
python3 configure_esp32.py --port COM3 --reset
```

## Method 3: Using screen/minicom (Linux/Mac)

### Using screen
```bash
screen /dev/ttyUSB0 115200
```

Then type:
```
SET_BROKER:192.168.1.100
```

Exit with: `Ctrl+A` then `K`

### Using minicom
```bash
minicom -D /dev/ttyUSB0 -b 115200
```

## Common Use Cases

### Scenario 1: Moving Between Networks

**Home network (broker at 192.168.1.100):**
```
SET_BROKER:192.168.1.100
```

**Lab network (broker at 10.0.0.50):**
```
SET_BROKER:10.0.0.50
```

### Scenario 2: Windows Hotspot

When using Windows Mobile Hotspot, the broker IP is typically `192.168.137.1`:
```
SET_BROKER:192.168.137.1
```

### Scenario 3: macOS Hotspot

macOS hotspots typically use `172.20.10.1` or similar:
```
SET_BROKER:172.20.10.1
```

### Scenario 4: Ubuntu Hotspot

Ubuntu hotspots typically use `10.42.0.1`:
```
SET_BROKER:10.42.0.1
```

### Scenario 5: Cloud Server

If running the dashboard on a cloud server or different machine:
```
SET_BROKER:192.168.1.50
```

## Troubleshooting

### ESP32 Not Responding to Serial Commands

1. **Check baud rate:** Must be 115200
2. **Try pressing the RESET button** on ESP32
3. **Check serial port:**
   - Windows: COM3, COM4, etc.
   - Linux: /dev/ttyUSB0, /dev/ttyACM0
   - macOS: /dev/cu.usbserial-*
4. **Close other programs** using the serial port (Arduino IDE, PlatformIO, etc.)

### Configuration Doesn't Save

- Wait for the 3 LED flashes indicating successful save
- ESP32 will restart automatically after configuration
- Check that you see "Configuration saved to EEPROM!"

### Can't Connect to MQTT After Changing Broker

1. **Verify broker IP is correct:**
   ```
   GET_BROKER
   ```

2. **Check that MQTT broker is running** on the specified IP:
   ```bash
   # On the dashboard computer
   mosquitto -v
   ```

3. **Verify ESP32 can reach the broker:**
   - Both must be on the same network
   - Check firewall settings
   - Ping the broker IP from another device

### Wrong IP Set by Mistake

Simply send the correct IP:
```
SET_BROKER:192.168.1.100
```

Configuration is overwritten and ESP32 restarts.

## Technical Details

### EEPROM Storage

Configuration is stored in ESP32 Preferences (non-volatile storage):

**Namespace:** `train-config`

**Keys:**
- `train_id` (String) - Train identifier
- `udp_port` (Int) - UDP destination port
- `mqtt_broker` (String) - **NEW:** MQTT broker IP address
- `configured` (Bool) - Configuration status flag

### Default Values

If no broker IP is configured:
- Default: `192.168.137.1` (Windows Mobile Hotspot default)

### Firmware Size

Adding broker configuration increases firmware size by ~500 bytes.

Total firmware size: **~36KB** (well within ESP32 limits)

## Example Workflow

### Initial Setup
```bash
# 1. Flash universal firmware (one time only)
# Upload tren_esp_universal/tren_esp_universal.ino via Arduino IDE

# 2. Configure via serial
python3 configure_esp32.py --port COM3 --train trainA --udp 5555 --broker 192.168.1.100

# 3. Verify configuration
python3 configure_esp32.py --port COM3 --status
```

### Changing Networks
```bash
# Just update the broker IP, no need to touch train ID or UDP port
python3 configure_esp32.py --port COM3 --broker 10.42.0.1
```

### Multiple Trains Setup
```bash
# Train A
python3 configure_esp32.py --port COM3 --train trainA --udp 5555 --broker 192.168.1.100

# Train B (same broker, different train)
python3 configure_esp32.py --port COM4 --train trainB --udp 5556 --broker 192.168.1.100

# Train C
python3 configure_esp32.py --port COM5 --train trainC --udp 5557 --broker 192.168.1.100
```

## Benefits

✅ **No Recompilation** - Change broker IP without Arduino IDE

✅ **Quick Network Changes** - Switch between home/lab/hotspot easily

✅ **Multi-Train Deployment** - Same firmware, different broker IPs if needed

✅ **Easy Replacement** - Replace broken ESP32 without code changes

✅ **User-Friendly** - Students can configure without technical knowledge

## See Also

- **FIRMWARE_CONFIG_GUIDE.md** - Complete firmware configuration guide
- **QUICK_CONFIG_REFERENCE.md** - Quick reference for all serial commands
- **README_platform.md** - Dashboard platform documentation
