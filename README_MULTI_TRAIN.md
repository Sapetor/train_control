# Multi-Train Control Platform Setup Guide

## Overview

The Multi-Train Control Platform allows multiple users to control different ESP32 trains from a single web server. Each user can:
- Access a specific train via a unique URL (e.g., `http://192.168.137.1:8050/train/trainA`)
- Control their train independently without affecting others
- View all available trains from a landing page

## Architecture

```
Single Server (192.168.137.1:8050)
│
├── Landing Page (/)
│   └── Train Selection Grid → /train/{trainId}
│
├── Train Dashboards (/train/trainA, /train/trainB, etc.)
│   ├── Independent UDP Receiver (port 5555, 5556, 5557...)
│   ├── Independent MQTT Topics (trenes/trainA/*, trenes/trainB/*...)
│   ├── Independent CSV Files (trainA_*.csv, trainB_*.csv...)
│   └── Full dashboard features (PID, Step Response, Deadband)
│
└── Admin Panel (/admin)
    └── View/manage train configurations
```

## Quick Start

### 1. Configure Trains

Edit `trains_config.json`:

```json
{
  "trains": {
    "trainA": {
      "id": "trainA",
      "name": "Train A",
      "udp_port": 5555,
      "mqtt_prefix": "trenes/trainA",
      "pid_limits": {"kp_max": 250, "ki_max": 150, "kd_max": 150},
      "enabled": true
    },
    "trainB": {
      "id": "trainB",
      "name": "Train B",
      "udp_port": 5556,
      "mqtt_prefix": "trenes/trainB",
      "pid_limits": {"kp_max": 250, "ki_max": 150, "kd_max": 150},
      "enabled": true
    }
  },
  "admin_password": "admin123",
  "dashboard_host": "127.0.0.1",
  "dashboard_port": 8050
}
```

### 2. Start Multi-Train Server

```bash
python multi_train_wrapper.py
```

Expected output:
```
[CONFIG] Loaded 2 train configurations
[MULTI-TRAIN] Initialized Train A (UDP: 5555, MQTT: trenes/trainA)
[MULTI-TRAIN] Initialized Train B (UDP: 5556, MQTT: trenes/trainB)
[UDP] Started receiver for trainA on port 5555
[UDP] Started receiver for trainB on port 5556

[MULTI-TRAIN] Starting dashboard on http://127.0.0.1:8050
[MULTI-TRAIN] Landing page: http://127.0.0.1:8050/
[MULTI-TRAIN] Admin panel: http://127.0.0.1:8050/admin
[MULTI-TRAIN] Train dashboards:
  - http://127.0.0.1:8050/train/trainA
  - http://127.0.0.1:8050/train/trainB
```

### 3. Access Dashboards

**For users:**
1. Open browser to `http://192.168.137.1:8050/`
2. Click on your assigned train
3. Bookmark the direct URL for next time

**Direct URLs (for sharing with users):**
- Train A: `http://192.168.137.1:8050/train/trainA`
- Train B: `http://192.168.137.1:8050/train/trainB`
- Train C: `http://192.168.137.1:8050/train/trainC`

## ESP32 Firmware Configuration

### Critical: Each ESP32 Must Use Different Topics

**Option 1: Compile-Time Configuration (Recommended)**

Edit `tren_esp_unified_FIXED.ino` before uploading to each ESP32:

```cpp
// Train A configuration
#define TRAIN_ID "trainA"
String mqtt_prefix = "trenes/trainA";

// Train B configuration
#define TRAIN_ID "trainB"
String mqtt_prefix = "trenes/trainB";
```

Then modify all topic subscriptions:
```cpp
// OLD (hardcoded):
client.subscribe("trenes/carroD/p");

// NEW (train-specific):
client.subscribe((mqtt_prefix + "/carroD/p").c_str());
```

**Option 2: EEPROM Storage (Advanced)**

Store train ID in ESP32 EEPROM and load on boot:
```cpp
String train_id = EEPROM.readString(0);  // Read from EEPROM
String mqtt_prefix = "trenes/" + train_id;
```

### UDP Destination Port

Each ESP32 must send UDP packets to its assigned port:

```cpp
// Train A
const int udpDestPort = 5555;

// Train B
const int udpDestPort = 5556;

// Train C
const int udpDestPort = 5557;
```

## User Workflow

### For Students/Users:

1. **Get your train URL** from instructor (e.g., `http://192.168.137.1:8050/train/trainA`)
2. **Bookmark it** for easy access
3. **Open the URL** in your browser
4. **Use the dashboard** normally (all features work independently)

### For Instructors/Admins:

1. **Configure trains** in `trains_config.json`
2. **Start server** with `python multi_train_wrapper.py`
3. **Share train URLs** with students
4. **Monitor all trains** via admin panel: `http://192.168.137.1:8050/admin`

## Configuration Details

### trains_config.json Format

```json
{
  "trains": {
    "trainA": {
      "id": "trainA",               // Unique identifier
      "name": "Train A",            // Display name
      "udp_port": 5555,             // UDP port for this train
      "mqtt_prefix": "trenes/trainA", // MQTT topic prefix
      "pid_limits": {               // Train-specific PID limits
        "kp_max": 250,
        "ki_max": 150,
        "kd_max": 150
      },
      "enabled": true               // Enable/disable train
    }
  },
  "admin_password": "admin123",     // Admin panel password (future use)
  "dashboard_host": "127.0.0.1",    // Server bind address
  "dashboard_port": 8050            // Server port
}
```

### Adding More Trains

To add Train D:

1. Edit `trains_config.json`:
```json
"trainD": {
  "id": "trainD",
  "name": "Train D",
  "udp_port": 5558,
  "mqtt_prefix": "trenes/trainD",
  "pid_limits": {"kp_max": 250, "ki_max": 150, "kd_max": 150},
  "enabled": true
}
```

2. Restart server: `python multi_train_wrapper.py`

3. Configure ESP32 firmware with Train D settings

4. Share URL: `http://192.168.137.1:8050/train/trainD`

## Data Isolation

### CSV Files

Each train generates separate CSV files:

```
trainA_experiment_20251109_143052.csv
trainA_step_response_20251109_143052.csv
trainA_deadband_calibration_20251109_143052.csv

trainB_experiment_20251109_144023.csv
trainB_step_response_20251109_144023.csv
trainB_deadband_calibration_20251109_144023.csv
```

### MQTT Topics

Each train uses isolated topics:

**Train A:**
- `trenes/trainA/carroD/p` (Kp)
- `trenes/trainA/carroD/i` (Ki)
- `trenes/trainA/step/sync` (Step control)

**Train B:**
- `trenes/trainB/carroD/p` (Kp)
- `trenes/trainB/carroD/i` (Ki)
- `trenes/trainB/step/sync` (Step control)

### UDP Ports

Each train listens on a different port:
- Train A: 5555
- Train B: 5556
- Train C: 5557
- etc.

## Network Setup

### For Shared Access on Local Network

Change `dashboard_host` in `trains_config.json`:

```json
{
  "dashboard_host": "0.0.0.0",  // Listen on all interfaces
  "dashboard_port": 8050
}
```

Then access via:
- `http://<server-ip>:8050/` (landing page)
- `http://<server-ip>:8050/train/trainA` (Train A)

Example: `http://192.168.137.1:8050/train/trainA`

### Firewall Configuration

Ensure these ports are open:
- **8050** - Dashboard web server
- **1883** - MQTT broker (Mosquitto)
- **5555-5560** - UDP receivers (one per train)

## Troubleshooting

### Problem: Train not appearing on landing page

**Solution:**
- Check `trains_config.json` has `"enabled": true`
- Restart server: `python multi_train_wrapper.py`
- Check console for initialization errors

### Problem: No UDP data received

**Solution:**
- Verify ESP32 is sending to correct UDP port
- Check network interface is selected in Network tab
- Verify ESP32 and server are on same network
- Check console for UDP receiver status

### Problem: MQTT commands not working

**Solution:**
- Verify ESP32 subscribed to correct topics (train-specific prefix)
- Check Mosquitto broker is running
- Test with `mosquitto_sub -t "trenes/trainA/#"` to monitor topics
- Verify MQTT prefix matches in both firmware and config

### Problem: Cross-train interference

**Symptoms:** Changing Train A parameters affects Train B

**Solution:**
- Each ESP32 MUST have unique MQTT prefix in firmware
- Verify firmware was uploaded with correct train ID
- Check `mosquitto_sub -t "trenes/#"` to see all traffic

### Problem: Port already in use

**Error:** `OSError: [Errno 98] Address already in use`

**Solution:**
- Kill existing process: `sudo fuser -k 8050/tcp`
- Or change port in trains_config.json

## Performance Considerations

### Resource Usage (Per Train)

- **RAM:** ~50MB per train dashboard
- **CPU:** <5% per train (idle), ~15% during experiments
- **Network:** ~10KB/s per active experiment

### Recommended Limits

- **Small deployments (2-3 trains):** Any modern computer
- **Medium deployments (4-6 trains):** 4GB RAM, dual-core CPU
- **Large deployments (7-10 trains):** 8GB RAM, quad-core CPU

## Backward Compatibility

### Running Single Train (Original Mode)

To use the original single-train platform:

```bash
python train_control_platform.py
```

This continues to work exactly as before.

### Migrating to Multi-Train

1. Backup current setup:
   ```bash
   cp train_control_platform.py train_control_platform_backup.py
   ```

2. Create `trains_config.json` with your trains

3. Run multi-train wrapper:
   ```bash
   python multi_train_wrapper.py
   ```

4. Existing CSV files remain compatible

## Security Notes

### Current Implementation

- **No authentication** - Anyone with URL can access trains
- **Local network only** - Bind to 127.0.0.1 or trusted network
- **No encryption** - MQTT and UDP are unencrypted

### Production Recommendations

1. **Add authentication** - Require login per user/train
2. **Use HTTPS** - Encrypt dashboard traffic
3. **Firewall rules** - Limit access to trusted IPs
4. **MQTT encryption** - Use TLS for MQTT (port 8883)

## Advanced Configuration

### Custom PID Limits Per Train

```json
"trainA": {
  "pid_limits": {"kp_max": 300, "ki_max": 200, "kd_max": 200}
},
"trainB": {
  "pid_limits": {"kp_max": 150, "ki_max": 100, "kd_max": 100}
}
```

### Disabling Trains Temporarily

```json
"trainC": {
  "enabled": false  // Train C won't appear in landing page
}
```

### Multiple Network Interfaces

Server automatically detects all interfaces. Users select their interface in the Network tab (same as single-train mode).

## Support & Contact

For issues or questions:
- Review CLAUDE.md for development guidelines
- Check README_platform.md for original platform documentation
- Consult ESP32 firmware documentation in tren_esp_unified_FIXED/

## Version History

- **2025-11-09** - Multi-train architecture implemented
  - URL-based routing
  - Independent train control
  - Landing page and admin panel
  - Train-specific CSV files and MQTT topics

- **2025-11-06-v2** - Single-train baseline
  - Step response with baseline sampling
  - Deadband calibration
  - Network interface auto-detection
