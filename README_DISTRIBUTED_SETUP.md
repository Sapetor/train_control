# Distributed Multi-Train Setup Guide

## Overview

This guide explains how to run **multiple train dashboards on DIFFERENT PCs**, all connected to the same network and sharing a single MQTT broker.

**Use this deployment when:**
- Each student/user has their own PC
- You want fully independent dashboard operation
- You want distributed load (no single server bottleneck)
- Each train is physically located near its control PC

## Architecture Diagram

```
Network: 192.168.137.x
│
├── Server PC (192.168.137.1)
│   └── Mosquitto MQTT Broker (port 1883)
│       └── Shared by all trains
│
├── PC1 (192.168.137.10)
│   ├── Dashboard for Train A (http://localhost:8050)
│   ├── UDP Receiver (port 5555)
│   └── ESP32 Train A → sends UDP to 192.168.137.10:5555
│                     → connects to MQTT at 192.168.137.1:1883
│                     → topics: trenes/trainA/*
│
├── PC2 (192.168.137.20)
│   ├── Dashboard for Train B (http://localhost:8050)
│   ├── UDP Receiver (port 5556)
│   └── ESP32 Train B → sends UDP to 192.168.137.20:5556
│                     → connects to MQTT at 192.168.137.1:1883
│                     → topics: trenes/trainB/*
│
└── PC3 (192.168.137.30)
    ├── Dashboard for Train C (http://localhost:8050)
    ├── UDP Receiver (port 5557)
    └── ESP32 Train C → sends UDP to 192.168.137.30:5557
                      → connects to MQTT at 192.168.137.1:1883
                      → topics: trenes/trainC/*
```

## Key Differences from Centralized Setup

| Aspect | Centralized | Distributed |
|--------|-------------|-------------|
| **Server** | ONE server PC | Multiple PCs (one per train) |
| **Dashboard Access** | Via URL (/train/trainA) | Localhost on each PC |
| **MQTT Broker** | On server PC | On dedicated server PC |
| **UDP Data** | All trains → server | Each train → its own PC |
| **Load Distribution** | All load on one PC | Distributed across PCs |
| **User Access** | Via network (browser) | Direct on their PC |
| **Scalability** | Limited by server resources | Highly scalable |

## Setup Instructions

### Step 1: Set Up Shared MQTT Broker (Server PC)

**Install Mosquitto on one PC that will act as the central broker:**

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients

# Windows
# Download from: https://mosquitto.org/download/

# macOS
brew install mosquitto
```

**Configure Mosquitto to allow external connections:**

Edit `/etc/mosquitto/mosquitto.conf` (Linux) or `C:\Program Files\mosquitto\mosquitto.conf` (Windows):

```conf
# Listen on all network interfaces
listener 1883 0.0.0.0

# Allow anonymous connections (for local network)
allow_anonymous true

# Optional: Enable logging for debugging
log_dest file /var/log/mosquitto/mosquitto.log
log_type all
```

**Start Mosquitto:**

```bash
# Linux
sudo systemctl start mosquitto
sudo systemctl enable mosquitto  # Auto-start on boot

# Check status
sudo systemctl status mosquitto

# Windows
net start mosquitto

# macOS
brew services start mosquitto
```

**Verify it's running:**

```bash
# On server PC, check it's listening
netstat -an | grep 1883
# Should show: 0.0.0.0:1883 LISTEN

# Test from any PC on network
mosquitto_sub -h 192.168.137.1 -t "test" -v
# (Should connect without errors)
```

**Get server IP address:**

```bash
# Linux/macOS
ip addr show  # or: ifconfig

# Windows
ipconfig

# Example: 192.168.137.1
```

### Step 2: Configure trains_config.json

**Create or edit `trains_config.json` on EACH PC:**

```json
{
  "trains": {
    "trainA": {
      "id": "trainA",
      "name": "Train A",
      "udp_port": 5555,
      "mqtt_prefix": "trenes/trainA",
      "pid_limits": {
        "kp_max": 250,
        "ki_max": 150,
        "kd_max": 150
      },
      "enabled": true
    },
    "trainB": {
      "id": "trainB",
      "name": "Train B",
      "udp_port": 5556,
      "mqtt_prefix": "trenes/trainB",
      "pid_limits": {
        "kp_max": 250,
        "ki_max": 150,
        "kd_max": 150
      },
      "enabled": true
    },
    "trainC": {
      "id": "trainC",
      "name": "Train C",
      "udp_port": 5557,
      "mqtt_prefix": "trenes/trainC",
      "pid_limits": {
        "kp_max": 250,
        "ki_max": 150,
        "kd_max": 150
      },
      "enabled": true
    }
  },
  "admin_password": "admin123",
  "dashboard_host": "127.0.0.1",
  "dashboard_port": 8050,
  "network_ip": "192.168.137.1",
  "mqtt_broker_ip": "192.168.137.1"
}
```

**CRITICAL Configuration Fields:**

- `network_ip`: The IP of the PC where the dashboard is running (used for UDP reception)
- `mqtt_broker_ip`: The IP of the server PC running Mosquitto (same for all PCs)
- `udp_port`: Each train must have a unique port (5555, 5556, 5557, etc.)
- `mqtt_prefix`: Each train must have a unique MQTT topic prefix

### Step 3: Configure ESP32 Firmware

**RECOMMENDED: Use Universal Firmware (tren_esp_universal.ino)**

This firmware can be configured via serial commands, no recompilation needed!

#### Upload Universal Firmware

1. Open `tren_esp_universal/tren_esp_universal.ino` in Arduino IDE
2. Select "ESP32 Dev Module"
3. Upload (same firmware to ALL ESP32s)

#### Configure Each ESP32 via Serial

**For Train A (sends to PC1: 192.168.137.10):**

```
Serial Monitor (115200 baud):
SET_TRAIN:trainA:5555
```

Then edit the firmware's WiFi section to set the UDP destination IP:
```cpp
WiFiUDP udp;
IPAddress udpAddress(192, 168, 137, 10);  // PC1's IP
const int udpDestPort = 5555;              // From SET_TRAIN command
```

**For Train B (sends to PC2: 192.168.137.20):**

```
Serial Monitor (115200 baud):
SET_TRAIN:trainB:5556
```

Then edit UDP destination:
```cpp
IPAddress udpAddress(192, 168, 137, 20);  // PC2's IP
const int udpDestPort = 5556;
```

**For Train C (sends to PC3: 192.168.137.30):**

```
Serial Monitor (115200 baud):
SET_TRAIN:trainC:5557
```

Then edit UDP destination:
```cpp
IPAddress udpAddress(192, 168, 137, 30);  // PC3's IP
const int udpDestPort = 5557;
```

**Also configure MQTT broker in firmware:**

```cpp
// In setup() function, set MQTT broker IP
const char* mqtt_server = "192.168.137.1";  // Server PC running Mosquitto
```

#### Verify ESP32 Configuration

Open Serial Monitor after configuration:

```
========================================
TRAIN CONFIGURATION LOADED
Train ID: trainA
UDP Port: 5555
MQTT Prefix: trenes/trainA
========================================
Connecting to WiFi...
Connected! IP: 192.168.1.100
Connecting to MQTT broker at 192.168.137.1...
MQTT Connected!
Subscribed to: trenes/trainA/carroD/p
[LED solid ON]
Ready!
```

### Step 4: Launch Dashboard on Each PC

**On PC1 (Train A):**

```bash
cd train_control
python launch_train.py trainA
```

Expected output:
```
============================================================
LAUNCHING TRAIN: Train A (trainA)
============================================================
UDP Port:      5555
MQTT Prefix:   trenes/trainA
Dashboard:     http://127.0.0.1:8050
============================================================

[MQTT] Generating train-specific topics...
[MQTT] Topics configured for trenes/trainA
[MQTT] Example topics:
  - Kp:   trenes/trainA/carroD/p
  - Sync: trenes/trainA/sync
  - Step: trenes/trainA/step/sync

[TRAIN trainA] Dashboard initialized
[TRAIN trainA] MQTT topics using prefix: trenes/trainA
[TRAIN trainA] UDP receiver on port: 5555

[NETWORK] Auto-configuring network for trainA...
[NETWORK] ✓ UDP receiver started on 192.168.137.10:5555
[NETWORK] ✓ MQTT client connected to 192.168.137.1:1883
[NETWORK] ✓ Ready to send/receive parameters

Starting dashboard on http://127.0.0.1:8050
```

**On PC2 (Train B):**

```bash
cd train_control
python launch_train.py trainB
```

**On PC3 (Train C):**

```bash
cd train_control
python launch_train.py trainC
```

### Step 5: Access Dashboards

Each user opens their browser on **their own PC**:

- PC1 user: http://localhost:8050 (controls Train A)
- PC2 user: http://localhost:8050 (controls Train B)
- PC3 user: http://localhost:8050 (controls Train C)

All dashboards are fully independent with complete functionality:
- PID Control
- Step Response
- Deadband Calibration
- Real-time graphs
- CSV download

## Verification Steps

### 1. Check MQTT Broker Connectivity

From any PC:

```bash
# Subscribe to all train topics
mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v

# You should see messages like:
# trenes/trainA/carroD/p/status 50.0
# trenes/trainB/carroD/i/status 25.0
```

### 2. Test Parameter Updates

On PC1 (Train A dashboard):
1. Go to Control tab
2. Change Kp to 100
3. Click "Update PID"

On server PC, check MQTT traffic:
```bash
mosquitto_sub -h 192.168.137.1 -t "trenes/trainA/#" -v

# Should show:
# trenes/trainA/carroD/p 100.0
# trenes/trainA/carroD/p/status 100.0
```

Verify that **Train B and C are NOT affected** by checking their topics don't change.

### 3. Test UDP Data Reception

On each PC's dashboard:
1. Start an experiment
2. Check that UDP data is being received (graph updates)
3. Verify CSV file is created with train ID prefix (e.g., `trainA_experiment_*.csv`)

### 4. Test Topic Isolation

Send a test command from command line:

```bash
# Publish to Train A
mosquitto_pub -h 192.168.137.1 -t "trenes/trainA/carroD/p" -m "123.4"

# Publish to Train B
mosquitto_pub -h 192.168.137.1 -t "trenes/trainB/carroD/p" -m "456.7"
```

Verify that:
- Train A dashboard shows Kp = 123.4
- Train B dashboard shows Kp = 456.7
- No cross-contamination

## Network Configuration

### Finding Each PC's IP Address

**Linux/macOS:**
```bash
ip addr show
# or
ifconfig
```

**Windows:**
```bash
ipconfig
```

Look for the IP on your local network (e.g., 192.168.137.x or 192.168.1.x)

### Firewall Configuration

**On each PC, allow incoming traffic:**

- **UDP port** for your train (5555, 5556, 5557, etc.) - for ESP32 data
- **Dashboard access** is localhost only (no firewall rule needed)

**On server PC (MQTT broker), allow:**

- **TCP port 1883** - MQTT broker

**Linux (ufw):**
```bash
# On dashboard PCs
sudo ufw allow 5555/udp  # Train A
sudo ufw allow 5556/udp  # Train B
sudo ufw allow 5557/udp  # Train C

# On server PC (MQTT broker)
sudo ufw allow 1883/tcp
```

**Windows Firewall:**
1. Control Panel → Windows Defender Firewall → Advanced Settings
2. Inbound Rules → New Rule
3. Port → UDP → Specific local ports → 5555 (or your train's port)
4. Allow the connection → Apply to all profiles → Name it "Train Control UDP"

Repeat for MQTT broker (TCP 1883) on server PC.

## Troubleshooting

### Problem: Dashboard can't connect to MQTT broker

**Symptoms:**
- Dashboard starts but shows "MQTT disconnected"
- No parameter updates work

**Solutions:**
1. Verify `mqtt_broker_ip` in `trains_config.json` is correct
2. Check Mosquitto is running on server PC:
   ```bash
   sudo systemctl status mosquitto  # Linux
   net start mosquitto             # Windows
   ```
3. Test connectivity from dashboard PC:
   ```bash
   mosquitto_sub -h 192.168.137.1 -t "test"
   ```
4. Check firewall allows port 1883

### Problem: No UDP data received

**Symptoms:**
- Dashboard shows no data
- Graphs don't update
- No CSV file created

**Solutions:**
1. Verify ESP32 is sending to correct IP and port
2. Check `network_ip` in `trains_config.json` matches the PC's IP
3. Test UDP reception:
   ```bash
   # On dashboard PC
   nc -u -l 5555  # Listen on UDP port 5555
   # ESP32 should send data here
   ```
4. Check firewall allows UDP port

### Problem: Cross-train interference

**Symptoms:**
- Changing Train A parameters affects Train B

**Solutions:**
1. Verify each ESP32 has unique MQTT prefix in firmware configuration
2. Check MQTT topics are correct:
   ```bash
   mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v
   ```
3. Ensure each ESP32 was configured with different train ID via `SET_TRAIN` command

### Problem: Port already in use

**Error:**
```
OSError: [Errno 98] Address already in use
```

**Solutions:**
1. Kill existing dashboard:
   ```bash
   # Linux/macOS
   sudo fuser -k 8050/tcp

   # Windows
   netstat -ano | findstr :8050
   taskkill /PID <PID> /F
   ```
2. Or launch on different port:
   ```bash
   python launch_train.py trainA 8051
   ```

### Problem: ESP32 not connecting to MQTT broker

**Symptoms:**
- ESP32 serial shows "MQTT connection failed"
- LED blinking slowly

**Solutions:**
1. Verify `mqtt_server` IP in firmware matches server PC
2. Check ESP32 and server are on same network
3. Test MQTT broker from ESP32's network:
   ```bash
   mosquitto_sub -h 192.168.137.1 -t "test"
   ```
4. Verify MQTT topics in firmware match `trains_config.json`

## Data Management

### CSV Files

Each PC creates its own CSV files with train ID prefix:

**PC1 (Train A):**
```
trainA_experiment_20251113_103045.csv
trainA_step_response_20251113_104123.csv
trainA_deadband_20251113_105201.csv
```

**PC2 (Train B):**
```
trainB_experiment_20251113_103045.csv
trainB_step_response_20251113_104123.csv
trainB_deadband_20251113_105201.csv
```

### Collecting All Data

To collect all experiment data from all PCs:

1. Set up a shared network folder
2. Copy CSV files from each PC to the shared folder
3. Or use `scp`/`rsync` to transfer files:

```bash
# From collection PC
scp user@192.168.137.10:~/train_control/trainA_*.csv ./collected_data/
scp user@192.168.137.20:~/train_control/trainB_*.csv ./collected_data/
scp user@192.168.137.30:~/train_control/trainC_*.csv ./collected_data/
```

## Advantages of Distributed Setup

1. **Independent Operation**: Each dashboard runs on its own PC - no single point of failure
2. **Better Performance**: Load is distributed across multiple PCs
3. **Scalability**: Easy to add more trains - just add another PC
4. **Local Control**: Users have direct control on their own machine
5. **Network Resilience**: One PC going down doesn't affect others
6. **Easier Debugging**: Users can see their own dashboard logs

## When to Use Distributed vs Centralized

**Use Distributed When:**
- Each student has their own PC/laptop
- You want maximum independence between trains
- You have many trains (>5) and performance is a concern
- Physical setup allows each train to be near its control PC

**Use Centralized When:**
- Users access via thin clients or tablets
- You want central monitoring and control
- You have fewer trains (<5)
- You want a single point of management
- Users don't have their own PCs

## Switching Between Modes

You can easily switch between distributed and centralized:

**To Distributed:**
```bash
# On each PC
python launch_train.py trainA  # or trainB, trainC, etc.
```

**To Centralized:**
```bash
# On one server PC
python multi_train_wrapper.py
```

The same `trains_config.json` works for both modes!

## Advanced Configuration

### Custom Dashboard Port Per PC

If multiple trains need to run on same PC (unusual), use different ports:

```bash
python launch_train.py trainA 8050
python launch_train.py trainB 8051
```

### Remote MQTT Broker

If MQTT broker is on a different network:

```json
{
  "mqtt_broker_ip": "mqtt.example.com",  // Domain name or remote IP
  "network_ip": "192.168.137.10"         // Local IP for UDP
}
```

### VPN Setup

For distributed PCs across different physical locations:

1. Set up VPN (e.g., WireGuard, OpenVPN)
2. Configure `mqtt_broker_ip` to VPN server IP
3. Configure ESP32 to send UDP over VPN
4. Ensure VPN allows UDP and MQTT traffic

## Quick Start Checklist

- [ ] Server PC: Install and configure Mosquitto broker
- [ ] Server PC: Start Mosquitto and verify it's listening on 0.0.0.0:1883
- [ ] All PCs: Create `trains_config.json` with correct `mqtt_broker_ip`
- [ ] All PCs: Set `network_ip` to each PC's own IP address
- [ ] ESP32s: Upload universal firmware
- [ ] ESP32s: Configure with `SET_TRAIN:trainX:YYYY` command
- [ ] ESP32s: Set UDP destination IP to each train's PC IP
- [ ] ESP32s: Set MQTT broker IP to server PC IP
- [ ] Each PC: Run `python launch_train.py trainX`
- [ ] Each PC: Verify dashboard opens and connects to MQTT
- [ ] Test: Send MQTT command and verify only correct train responds
- [ ] Test: Start experiment and verify UDP data is received
- [ ] Test: Verify CSV files are created with train ID prefix

## Support

For issues:
- Check Mosquitto logs: `/var/log/mosquitto/mosquitto.log`
- Monitor MQTT traffic: `mosquitto_sub -h 192.168.137.1 -t "#" -v`
- Check dashboard console output for errors
- Verify ESP32 serial output shows successful connections

## Version History

- **2025-11-13** - Created distributed setup guide
  - Detailed instructions for multi-PC deployment
  - MQTT broker configuration
  - ESP32 firmware configuration for distributed mode
  - Troubleshooting and verification procedures
