# Universal ESP32 Train Control Firmware

## Arduino IDE Requirement

⚠️ **IMPORTANT**: This file MUST be in a folder named `tren_esp_universal` for Arduino IDE to open it.

Current structure:
```
tren_esp_universal/
├── tren_esp_universal.ino  ← Main firmware file
└── README.md               ← This file
```

## Quick Start

### 1. Open in Arduino IDE
```
File → Open → tren_esp_universal/tren_esp_universal.ino
```

### 2. Select Board
```
Tools → Board → ESP32 Arduino → ESP32 Dev Module
```

### 3. Upload
```
Upload button (→)
```

### 4. Configure via Serial
After upload, the ESP32 enters configuration mode (fast LED blink).

**Serial Monitor (115200 baud):**
```
SET_TRAIN:trainA:5555
```

Or use the Python configuration tool:
```bash
python ../configure_train.py
```

## Features

✅ **Universal** - One firmware for ALL trains
✅ **EEPROM Configuration** - Settings persist across reboots
✅ **Serial Commands** - Configure via Serial Monitor or Python tool
✅ **LED Feedback** - Visual status indicators
✅ **Dynamic MQTT Topics** - Auto-generates `trenes/{trainID}/*`
✅ **All Experiment Modes** - PID, Step Response, Deadband

## Serial Commands

| Command | Description | Example |
|---------|-------------|---------|
| `SET_TRAIN:id:port` | Configure train | `SET_TRAIN:trainA:5555` |
| `GET_TRAIN` | Show configuration | `GET_TRAIN` |
| `RESET_TRAIN` | Clear configuration | `RESET_TRAIN` |
| `STATUS` | Connection status | `STATUS` |

## LED Status

| Pattern | Meaning |
|---------|---------|
| Fast blink (200ms) | Waiting for configuration |
| 3 quick flashes | Configuration saved |
| Slow blink (1s) | Connecting to WiFi/MQTT |
| Solid ON | Ready and operational |

## Configuration Examples

```
Train A: SET_TRAIN:trainA:5555
Train B: SET_TRAIN:trainB:5556
Train C: SET_TRAIN:trainC:5557
```

## Troubleshooting

**Serial shows garbage?**
- Set baud rate to 115200

**LED blinking fast?**
- Normal! Send configuration via `SET_TRAIN` command

**Configuration not saving?**
- Use only alphanumeric train IDs (no spaces)

**MQTT not working?**
- Verify train ID matches `trains_config.json`

## Documentation

- **Full Guide**: `../FIRMWARE_CONFIG_GUIDE.md`
- **Quick Reference**: `../QUICK_CONFIG_REFERENCE.md`
- **Implementation**: `../UNIVERSAL_FIRMWARE_IMPLEMENTATION.md`

## Version

**Version**: 1.0.0 (Universal Multi-Train)
**Date**: 2025-11-09
**Base**: tren_esp_unified_FIXED.ino with universal configuration support
