# Single-Train Mode - Quick Start Guide

## Overview

Single-train mode is the simplest way to use the Train Control Platform. It's perfect for:
- Testing with one train
- Learning the system
- Quick experiments
- Debugging

## How to Run Single-Train Mode

```bash
python train_control_platform.py
```

That's it! The system will:
1. Detect available network interfaces
2. Start UDP receiver on port 5555
3. Start MQTT client
4. Launch dashboard at http://127.0.0.1:8050
5. Wait for you to configure the network interface

## Expected Terminal Output

```
======================================================================
Starting Train Control Platform
VERSION: 2025-11-06-v2 (Step Response Fix + Deadband Tab Debug)
======================================================================

Detecting network interfaces...
Found 3 network interfaces:
  - Local Area Connection* 12
  - Ethernet 2
  - WiFi

UDP Receiver Status:
  - IP: Not configured
  - Port: 5555
  - Running: False
  - Auto-configured: No (configure in dashboard)

Starting dashboard at http://127.0.0.1:8050
Configure network settings in the 'Network Configuration' tab

=== CREATING DASHBOARD LAYOUT ===
  - Created new Dash app (single-train mode)
  - Layout assigned to app (single-train mode)

Layout created with 5 tabs:
  1. 🔧 Configuración de Red
  2. ⚙️ Calibración Deadband ← MOVED TO POSITION 2
  3. 🎛️ Control PID
  4. 📈 Respuesta al Escalón
  5. 📊 Visualización de Datos

Dashboard ready!
```

## Step-by-Step Usage

### 1. Configure Network

1. Open browser: http://127.0.0.1:8050
2. You'll see the **Network Configuration** tab
3. Select your network interface from dropdown
   - Look for the one that can reach your ESP32 (e.g., "Local Area Connection* 12: 192.168.137.1")
4. Click **"Apply Configuration"**
5. System will start UDP receiver on the selected interface

**Terminal should show:**
```
UDP receiver started on 192.168.137.1:5555
MQTT broker IP set to: 192.168.137.1
```

### 2. Configure ESP32

Your ESP32 must be configured to match:
- **UDP Destination IP**: Your selected interface IP (e.g., 192.168.137.1)
- **UDP Destination Port**: 5555
- **MQTT Broker IP**: Same as UDP IP (192.168.137.1)

**Check ESP32 Configuration:**
```bash
# Connect serial monitor (115200 baud)
GET_TRAIN

# Should show:
# Train ID: trainA (or any ID)
# UDP Port: 5555
# MQTT Prefix: trenes/trainA
```

### 3. Test PID Control

1. Click **"Control PID"** tab (3rd tab)
2. Set parameters:
   - Kp: 100
   - Ki: 50
   - Kd: 10
   - Reference: 10 cm
3. Click **"Start Experiment"**
4. Watch real-time graphs update

**Expected behavior:**
- Terminal shows: "Starting PID experiment..."
- Graphs start updating every second
- CSV file created: `experiment_YYYYMMDD_HHMMSS.csv`

### 4. Test Step Response

1. Click **"Step Response"** tab (4th tab)
2. Set parameters:
   - Amplitude: 5.0 V
   - Duration: 10 s
   - Direction: Forward
3. Click **"Start Step Response"**
4. Watch step response graph

**Expected behavior:**
- Terminal shows: "Starting Step Response experiment..."
- Graph shows step input and train response
- CSV file created: `step_response_YYYYMMDD_HHMMSS.csv`

### 5. Test Deadband Calibration

1. Click **"Deadband Calibration"** tab (2nd tab)
2. Set parameters:
   - Direction: Forward
   - Motion Threshold: 0.08 cm
3. Click **"Start Calibration"**
4. Watch PWM increase until train moves

**Expected behavior:**
- Terminal shows: "Starting Deadband Calibration..."
- PWM increases gradually
- When train moves, calibration completes
- Result displayed: "Deadband: XX PWM"
- CSV file created: `deadband_YYYYMMDD_HHMMSS.csv`

## Verification Checklist

Use this checklist to verify single-train mode works correctly:

### Network Configuration
- [ ] Network interfaces listed in dropdown
- [ ] Can select interface and apply configuration
- [ ] UDP receiver starts successfully
- [ ] MQTT broker IP set correctly
- [ ] Configuration saved and persists across restarts

### PID Control
- [ ] Can set Kp, Ki, Kd parameters
- [ ] Can set reference distance
- [ ] Start/Stop buttons work
- [ ] Real-time graph updates
- [ ] Historical graph shows data
- [ ] CSV file created with correct format
- [ ] Download CSV button works

### Step Response
- [ ] Can set amplitude, duration, direction
- [ ] Start button works
- [ ] Step response graph updates
- [ ] CSV file created with correct format
- [ ] Can run multiple experiments without restart

### Deadband Calibration
- [ ] Can set direction and threshold
- [ ] Start button works
- [ ] PWM and distance graphs update
- [ ] Calibration completes when motion detected
- [ ] Result displayed correctly
- [ ] CSV file created

### Data Isolation (Single-Train)
- [ ] CSV files have standard names (no train ID prefix):
  - `experiment_YYYYMMDD_HHMMSS.csv`
  - `step_response_YYYYMMDD_HHMMSS.csv`
  - `deadband_YYYYMMDD_HHMMSS.csv`
- [ ] All experiments use same MQTT topics:
  - `trenes/carroD/p`
  - `trenes/sync`
  - etc.

## Troubleshooting Single-Train Mode

### Issue: No network interfaces shown
**Solution:**
- Run as administrator/sudo
- Check that you're not in WSL environment
- Restart application

### Issue: UDP receiver won't start
**Solution:**
- Check port 5555 not already in use: `netstat -an | findstr 5555`
- Try different interface
- Check firewall allows Python UDP

### Issue: No data from ESP32
**Solution:**
1. Verify ESP32 UDP destination IP matches your interface
2. Verify ESP32 UDP destination port is 5555
3. Check ESP32 connected to same network
4. Check ESP32 serial monitor shows "UDP packet sent"

### Issue: MQTT parameters not updating
**Solution:**
1. Verify MQTT broker running on your interface IP
2. Check ESP32 serial shows "MQTT Connected"
3. Verify ESP32 MQTT topics match dashboard
4. Use MQTT Explorer to monitor topics:
   ```bash
   mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v
   ```

### Issue: Graphs not updating
**Solution:**
1. Check CSV file is being created and has data
2. Verify experiment is actually running (check terminal)
3. Try refreshing browser (Ctrl+F5)
4. Check console for JavaScript errors (F12)

### Issue: App crashes on startup
**Solution:**
1. Check Python version (requires 3.7+)
2. Install dependencies: `pip install -r requirements.txt`
3. Check terminal for error messages
4. Delete `network_config.json` and retry

## File Structure (Single-Train)

When running in single-train mode, files are created in the working directory:

```
train_control/
├── experiment_20251110_143052.csv          ← PID data
├── step_response_20251110_143125.csv       ← Step response data
├── deadband_20251110_143200.csv            ← Deadband data
├── network_config.json                     ← Saved network config
└── train_control_platform.py               ← Main application
```

**Note:** No train ID prefix in CSV filenames for single-train mode.

## Switching to Multi-Train Mode

When ready to use multiple trains:

1. Create `trains_config.json`:
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

2. Run multi-train wrapper:
```bash
python multi_train_wrapper.py
```

3. Access trains via URLs:
- Train A: http://127.0.0.1:8050/train/trainA
- Train B: http://127.0.0.1:8050/train/trainB

See `README_MULTI_TRAIN.md` for details.

## Benefits of Single-Train Mode

1. **Simplicity** - Just run `python train_control_platform.py`
2. **No configuration needed** - Uses default ports and topics
3. **Easy debugging** - Only one train to monitor
4. **Fast iteration** - No need to configure train IDs
5. **Learning** - Perfect for understanding the system

## When to Use Single-Train vs Multi-Train

**Use Single-Train Mode when:**
- Testing with one train
- Learning the platform
- Debugging issues
- Quick experiments
- Home/personal use

**Use Multi-Train Mode when:**
- Managing multiple trains in a lab
- Students need independent dashboards
- Need data isolation between trains
- Sharing access via URLs
- Production deployments

---

**Need help?** Check the main README files:
- `README_platform.md` - General platform documentation
- `README_MULTI_TRAIN.md` - Multi-train mode guide
- `CLAUDE.md` - Development guidelines
