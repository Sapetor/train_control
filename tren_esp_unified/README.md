# Train ESP32 Unified Firmware

## 📍 **USE THIS FOLDER FOR ARDUINO IDE**

This is the correct folder structure for Arduino IDE upload.

## ✅ Features

**Three Experiment Modes:**
- **PID Mode** - Closed-loop distance control
- **Step Response Mode** - System identification  
- **Deadband Calibration Mode** - Observable auto-detection

**All PID Fixes Applied:**
- SetTunings only called on parameter changes (not every loop)
- Proper configuration order (SetSampleTime before Compute)
- Fixed motor direction logic
- Deadband = 300 (empirically correct value restored)
- No artificial safety caps

## 📤 Upload Instructions

1. Open Arduino IDE
2. File → Open → Select this folder: `tren_esp_unified/`
3. Arduino IDE will open `tren_esp_unified.ino`
4. Select Board: **ESP32 Dev Module**
5. Upload to ESP32

## 🔧 Configuration

Before uploading, verify these settings match your network (lines 50-52):

```cpp
const char* ssid = "TICS322";
const char* password = "esp32esp32";
const char* mqtt_server = "192.168.137.1";
```

## 🚀 Compatible Dashboard

This firmware works with `train_control_platform.py` dashboard.

All three experiment modes are accessible via dashboard tabs:
- Control PID tab
- Step Response tab  
- 🔧 Deadband Calibration tab

## 📝 Version History

- **Current:** Complete version with 3 modes + all fixes
- **Backup:** `tren_esp_unified.ino.backup` (previous version)
