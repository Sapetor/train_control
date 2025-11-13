# MQTT Communication Troubleshooting Guide

## Problem: ESP32 Shows "Ready" But No Response to Dashboard Commands

You see this in ESP32 serial monitor:
```
========================================
Setup Complete! Ready for experiments.
Available experiments:
  - PID Control: trenes/sync
  - Step Response: trenes/step/sync
  - Deadband Cal: trenes/deadband/sync
========================================
```

But when you click buttons in dashboard (Start Experiment, set Kp, etc.), **nothing happens** - no new messages in ESP32 serial.

---

## Root Causes & Solutions

### Cause 1: MQTT Broker Not Running ⚠️

**Symptom:** Dashboard sends messages but ESP32 never receives them.

**Check:**
```bash
# Windows
netstat -an | findstr 1883

# Linux/WSL
netstat -an | grep 1883
```

**Expected:** Should see `0.0.0.0:1883` or `your-ip:1883` LISTENING

**Solution:** Start MQTT broker:
```bash
# Install mosquitto (if not installed)
# Windows: Download from https://mosquitto.org/download/
# Linux: sudo apt install mosquitto

# Start broker
mosquitto -v
```

---

### Cause 2: Wrong MQTT Broker IP in Dashboard

**Symptom:** Dashboard publishes to wrong IP, ESP32 listening on different IP.

**Check ESP32 Configuration:**
In ESP32 serial monitor, look for:
```
MQTT Server: 192.168.137.1
MQTT Connected!
```

**Check Dashboard Configuration:**
1. Open dashboard Network tab
2. Look at "MQTT Broker IP" field
3. It should match ESP32's MQTT Server IP

**Solution:**
1. In dashboard Network tab, select interface with correct IP
2. Click "Apply Configuration"
3. Verify MQTT Broker IP matches ESP32

---

### Cause 3: ESP32 Hardcoded to Different Broker IP

**Symptom:** ESP32 firmware has hardcoded IP that doesn't match your network.

**Check Firmware:**
```cpp
// In tren_esp_unified_FIXED.ino, look for:
IPAddress mqtt_server(192, 168, 1, 1);  // ← Check this line
```

**Your Network Setup:**
- Dashboard IP: 192.168.137.1 (from Network tab)
- ESP32 MQTT Server: ??? (from serial monitor)

**Solution:** Edit firmware and change MQTT broker IP:
```cpp
// Change this line to match your dashboard IP:
IPAddress mqtt_server(192, 168, 137, 1);  // ← Your IP here
```

Then re-upload firmware to ESP32.

---

### Cause 4: MQTT Topic Mismatch (Multi-Train Confusion)

**Symptom:** Dashboard publishes to `trenes/trainA/sync` but ESP32 listens to `trenes/sync`.

**Check Dashboard Mode:**
- Single-train mode: publishes to `trenes/sync`
- Multi-train mode: publishes to `trenes/trainA/sync`

**Check ESP32 Topics:**
In serial monitor, look for:
```
Subscribed to: trenes/sync  ← Single-train (correct for single-train dashboard)
```
OR
```
Subscribed to: trenes/trainA/sync  ← Multi-train (wrong for single-train dashboard)
```

**Solution:**
- **For single-train dashboard:** Use `tren_esp_unified_FIXED.ino` (subscribes to `trenes/sync`)
- **For multi-train dashboard:** Use `tren_esp_universal.ino` with train ID configured

---

## Step-by-Step Debug Procedure

### Step 1: Verify ESP32 MQTT Connection

In ESP32 serial monitor, you should see:
```
MQTT Server: 192.168.137.1
Connecting to MQTT...
MQTT Connected!
Subscribed to: trenes/sync
Subscribed to: trenes/carroD/p
Subscribed to: trenes/carroD/i
...
```

**If NOT connected:**
- Check MQTT broker running on that IP
- Check ESP32 WiFi connected
- Check firewall allows port 1883

### Step 2: Verify Dashboard MQTT Configuration

1. Start dashboard: `python train_control_platform.py`
2. Open http://127.0.0.1:8050
3. Go to Network Configuration tab
4. Check "MQTT Broker IP" field
5. It should match ESP32's "MQTT Server" IP

### Step 3: Monitor MQTT Traffic

**Terminal 1 - Start MQTT broker (if not running):**
```bash
mosquitto -v
```

**Terminal 2 - Monitor all MQTT messages:**
```bash
# Use the provided debug script
./test_mqtt_debug.sh

# OR manually:
mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v
```

**Terminal 3 - Start dashboard:**
```bash
python train_control_platform.py
```

**In Browser:**
1. Click "Start Experiment" in PID tab

**Expected in Terminal 2:**
```
trenes/sync True
```

**If you see the message:**
- ✅ Dashboard is publishing correctly
- Check ESP32 serial - it should receive and respond
- If ESP32 doesn't show message, check ESP32 MQTT connection

**If NO message:**
- ❌ Dashboard not publishing
- Check MQTT broker running
- Check dashboard connected to MQTT

### Step 4: Check ESP32 Response

When you click "Set Kp = 100" in dashboard:

**Expected in MQTT monitor (Terminal 2):**
```
trenes/carroD/p 100.0
```

**Expected in ESP32 serial:**
```
MQTT Message arrived [trenes/carroD/p]: 100.0
Kp updated: 100.0
Publishing confirmation: trenes/carroD/p/status = 100.0
```

**If ESP32 receives but doesn't respond:**
- Check firmware handles the topic correctly
- Look for errors in ESP32 serial
- Verify firmware version has all features

---

## Quick Test Commands

### Test 1: Check MQTT Broker Reachable
```bash
# Try to connect to broker
mosquitto_sub -h 192.168.137.1 -t "test" -C 1
```
**Should:** Wait for message (press Ctrl+C to exit)
**Error:** Connection refused → Broker not running

### Test 2: Publish Test Message
```bash
# Terminal 1: Subscribe
mosquitto_sub -h 192.168.137.1 -t "test" -v

# Terminal 2: Publish
mosquitto_pub -h 192.168.137.1 -t "test" -m "hello"
```
**Should see in Terminal 1:** `test hello`

### Test 3: Simulate Dashboard Command
```bash
# Manually publish PID start command
mosquitto_pub -h 192.168.137.1 -t "trenes/sync" -m "True"
```
**Check ESP32 serial:** Should show "MQTT Message arrived [trenes/sync]: True"

---

## Common Scenarios & Fixes

### Scenario 1: Dashboard Works, ESP32 Silent

**Symptoms:**
- Dashboard shows "Experiment started"
- MQTT monitor shows messages being published
- ESP32 serial shows "MQTT Connected" but no new messages

**Diagnosis:** ESP32 connected to different broker or subscribed to wrong topics

**Fix:**
1. Check ESP32 MQTT Server IP matches your broker
2. Check ESP32 subscribed topics match dashboard publishes
3. Use `mosquitto_sub -h <esp32-mqtt-server-ip> -t "trenes/#" -v` to confirm messages reaching broker

### Scenario 2: Nothing Works, No MQTT Traffic

**Symptoms:**
- Click buttons in dashboard, nothing happens
- MQTT monitor shows no messages
- ESP32 shows "MQTT Connected"

**Diagnosis:** Dashboard not publishing (MQTT client not connected)

**Fix:**
1. Check dashboard terminal for MQTT connection errors
2. Restart MQTT broker: `mosquitto -v`
3. Restart dashboard
4. Check firewall allows port 1883

### Scenario 3: Works Sometimes, Then Stops

**Symptoms:**
- First command works
- Subsequent commands don't work
- ESP32 shows "MQTT Disconnected"

**Diagnosis:** Unstable MQTT connection or broker timeout

**Fix:**
1. Increase MQTT keepalive in firmware
2. Check network stability
3. Use wired connection instead of WiFi if possible
4. Check broker logs for connection drops

---

## Firmware Configuration Checklist

For **single-train mode with `tren_esp_unified_FIXED.ino`**:

**In the firmware code, verify:**

### 1. WiFi Credentials
```cpp
const char* ssid = "YOUR_WIFI_SSID";      // Your WiFi name
const char* password = "YOUR_WIFI_PASS";  // Your WiFi password
```

### 2. MQTT Broker IP
```cpp
IPAddress mqtt_server(192, 168, 137, 1);  // Match your dashboard IP
```

### 3. UDP Destination
```cpp
const int udpDestPort = 5555;  // Dashboard UDP port (usually 5555)
```

### 4. MQTT Topics (Should Already Be Correct)
```cpp
client.subscribe("trenes/sync");
client.subscribe("trenes/carroD/p");
// ... etc
```

---

## Dashboard Configuration Checklist

### 1. Network Tab
- [ ] Interface selected (e.g., "Local Area Connection* 12: 192.168.137.1")
- [ ] "Apply Configuration" clicked
- [ ] Status shows "Connected"

### 2. Terminal Output Should Show
```
UDP receiver started on 192.168.137.1:5555
MQTT broker IP set to: 192.168.137.1
```

### 3. MQTT Broker Running
```bash
# Check with:
netstat -an | findstr 1883  # Windows
netstat -an | grep 1883     # Linux
```

---

## Still Not Working?

If you've tried everything above and it still doesn't work:

### Collect Debug Information

**1. ESP32 Serial Output (full startup):**
```
Copy entire serial output from power-on to "Ready for experiments"
```

**2. Dashboard Terminal Output:**
```
Copy output from "Starting Train Control Platform" onwards
```

**3. MQTT Monitor Output:**
```bash
mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v
# Copy output when you click buttons
```

**4. Network Configuration:**
- Dashboard IP: (from Network tab)
- ESP32 IP: (from serial monitor)
- MQTT Broker IP: (from serial monitor)
- Same network? Yes/No

**5. Firmware Info:**
- File used: tren_esp_unified_FIXED.ino
- MQTT server IP in code: IPAddress mqtt_server(?, ?, ?, ?)
- Upload successful? Yes/No

---

## Pro Tips

### Enable Debug Output in Firmware

Add these prints to see MQTT activity:

```cpp
void callback(char* topic, byte* payload, unsigned int length) {
    // ADD THIS at the start of callback function:
    Serial.print("MQTT Message arrived [");
    Serial.print(topic);
    Serial.print("]: ");
    for (int i = 0; i < length; i++) {
        Serial.print((char)payload[i]);
    }
    Serial.println();

    // ... rest of callback code
}
```

### Run Broker in Verbose Mode

See all MQTT traffic:
```bash
mosquitto -v
```

Output shows:
```
1234567890: Client mosq-abc connected
1234567890: New subscription: trenes/sync QoS 0
1234567890: Received PUBLISH from dashboard (trenes/sync, 4 bytes)
```

---

**Last Updated:** 2025-11-10
**For:** Train Control Platform Single-Train Mode
