# Distributed Multi-Train Quick Start

**Goal:** Run 3 trains on 3 different PCs, all sharing one MQTT broker.

## 5-Minute Setup (TL;DR)

### 1. Server PC (MQTT Broker)

```bash
# Install Mosquitto
sudo apt-get install mosquitto mosquitto-clients

# Edit /etc/mosquitto/mosquitto.conf
listener 1883 0.0.0.0
allow_anonymous true

# Start Mosquitto
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Get server IP
ip addr show
# Example: 192.168.137.1
```

### 2. Each Dashboard PC (PC1, PC2, PC3)

**PC1 (Train A):**
```bash
cd train_control

# Edit trains_config.json
# Set: "network_ip": "192.168.137.10"  (PC1's IP)
# Set: "mqtt_broker_ip": "192.168.137.1"  (Server PC's IP)

# Launch
python launch_train.py trainA

# Access
http://localhost:8050
```

**PC2 (Train B):**
```bash
cd train_control

# Edit trains_config.json
# Set: "network_ip": "192.168.137.20"  (PC2's IP)
# Set: "mqtt_broker_ip": "192.168.137.1"  (Server PC's IP)

# Launch
python launch_train.py trainB

# Access
http://localhost:8050
```

**PC3 (Train C):**
```bash
cd train_control

# Edit trains_config.json
# Set: "network_ip": "192.168.137.30"  (PC3's IP)
# Set: "mqtt_broker_ip": "192.168.137.1"  (Server PC's IP)

# Launch
python launch_train.py trainC

# Access
http://localhost:8050
```

### 3. ESP32 Configuration

**Train A (goes with PC1):**
```
Serial Monitor (115200 baud):
SET_TRAIN:trainA:5555

In firmware:
IPAddress udpAddress(192, 168, 137, 10);  // PC1's IP
const char* mqtt_server = "192.168.137.1";  // Server PC's IP
```

**Train B (goes with PC2):**
```
Serial Monitor (115200 baud):
SET_TRAIN:trainB:5556

In firmware:
IPAddress udpAddress(192, 168, 137, 20);  // PC2's IP
const char* mqtt_server = "192.168.137.1";  // Server PC's IP
```

**Train C (goes with PC3):**
```
Serial Monitor (115200 baud):
SET_TRAIN:trainC:5557

In firmware:
IPAddress udpAddress(192, 168, 137, 30);  // PC3's IP
const char* mqtt_server = "192.168.137.1";  // Server PC's IP
```

## Verification (30 seconds)

### Test MQTT

```bash
# On any PC
mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v

# On PC1, change Kp parameter in dashboard
# You should see:
trenes/trainA/carroD/p 100.0
trenes/trainA/carroD/p/status 100.0
```

### Test UDP

1. Start experiment on PC1's dashboard
2. Check graph updates (UDP data arriving)
3. Check CSV file created: `trainA_experiment_*.csv`

### Test Isolation

```bash
# Send test to Train A
mosquitto_pub -h 192.168.137.1 -t "trenes/trainA/test" -m "hello A"

# Send test to Train B
mosquitto_pub -h 192.168.137.1 -t "trenes/trainB/test" -m "hello B"

# Verify trains don't interfere
```

## Network Diagram

```
192.168.137.1  ← Server PC (Mosquitto)
     ▲
     │ MQTT (all trains connect here)
     │
     ├─────────────┬─────────────┐
     │             │             │
192.168.137.10  192.168.137.20  192.168.137.30
PC1 (Train A)   PC2 (Train B)   PC3 (Train C)
     ▲               ▲               ▲
     │ UDP           │ UDP           │ UDP
     │               │               │
  ESP32 A         ESP32 B         ESP32 C
 (port 5555)     (port 5556)     (port 5557)
```

## Configuration Checklist

**Server PC:**
- [ ] Mosquitto installed
- [ ] Config file edited (listen 0.0.0.0)
- [ ] Mosquitto running
- [ ] Firewall allows port 1883 (TCP)
- [ ] IP address: 192.168.137.1 (example)

**PC1 (Train A):**
- [ ] trains_config.json: `"network_ip": "192.168.137.10"`
- [ ] trains_config.json: `"mqtt_broker_ip": "192.168.137.1"`
- [ ] Firewall allows port 5555 (UDP)
- [ ] Dashboard running: `python launch_train.py trainA`
- [ ] ESP32 A sends UDP to 192.168.137.10:5555
- [ ] ESP32 A connects to MQTT at 192.168.137.1:1883
- [ ] ESP32 A uses topics: `trenes/trainA/*`

**PC2 (Train B):**
- [ ] trains_config.json: `"network_ip": "192.168.137.20"`
- [ ] trains_config.json: `"mqtt_broker_ip": "192.168.137.1"`
- [ ] Firewall allows port 5556 (UDP)
- [ ] Dashboard running: `python launch_train.py trainB`
- [ ] ESP32 B sends UDP to 192.168.137.20:5556
- [ ] ESP32 B connects to MQTT at 192.168.137.1:1883
- [ ] ESP32 B uses topics: `trenes/trainB/*`

**PC3 (Train C):**
- [ ] trains_config.json: `"network_ip": "192.168.137.30"`
- [ ] trains_config.json: `"mqtt_broker_ip": "192.168.137.1"`
- [ ] Firewall allows port 5557 (UDP)
- [ ] Dashboard running: `python launch_train.py trainC`
- [ ] ESP32 C sends UDP to 192.168.137.30:5557
- [ ] ESP32 C connects to MQTT at 192.168.137.1:1883
- [ ] ESP32 C uses topics: `trenes/trainC/*`

## Common Mistakes

❌ **All ESP32s sending to same PC**
✅ Each ESP32 sends to its own PC's IP

❌ **Same MQTT topics for all trains**
✅ Each train uses unique prefix (trainA, trainB, trainC)

❌ **mqtt_broker_ip = localhost**
✅ mqtt_broker_ip = server PC's actual IP (192.168.137.1)

❌ **network_ip = server PC's IP**
✅ network_ip = each PC's own IP (different for each PC)

❌ **Same UDP port for all trains**
✅ Each train uses unique UDP port (5555, 5556, 5557)

## Troubleshooting

**Problem:** Dashboard shows "MQTT disconnected"
```bash
# Check Mosquitto is running
sudo systemctl status mosquitto

# Test from dashboard PC
mosquitto_sub -h 192.168.137.1 -t "test"

# If fails, check:
# 1. mqtt_broker_ip in trains_config.json
# 2. Firewall on server PC allows port 1883
# 3. Server PC IP is correct
```

**Problem:** No UDP data (graphs don't update)
```bash
# Check ESP32 is sending to correct IP
# In ESP32 firmware, verify:
IPAddress udpAddress(192, 168, 137, 10);  // Must match PC's IP!

# Test UDP reception on PC
nc -u -l 5555

# If no data, check:
# 1. network_ip in trains_config.json matches PC's IP
# 2. Firewall allows UDP port
# 3. ESP32 on same network as PC
```

**Problem:** Wrong train responds to commands
```bash
# Check MQTT topics
mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v

# Each train should show:
trenes/trainA/...  (Train A)
trenes/trainB/...  (Train B)
trenes/trainC/...  (Train C)

# If mixed up, reconfigure ESP32:
SET_TRAIN:trainA:5555  (on ESP32 A)
SET_TRAIN:trainB:5556  (on ESP32 B)
SET_TRAIN:trainC:5557  (on ESP32 C)
```

## Files and Directories

**On each PC:**
```
train_control/
├── launch_train.py              ← Use this to start
├── trains_config.json           ← Edit network_ip per PC
├── train_control_platform.py    ← Main dashboard code
│
├── trainA_experiment_*.csv      ← Data files (Train A on PC1)
├── trainB_experiment_*.csv      ← Data files (Train B on PC2)
├── trainC_experiment_*.csv      ← Data files (Train C on PC3)
│
└── README_DISTRIBUTED_SETUP.md  ← Full guide
```

**On server PC:**
```
/etc/mosquitto/mosquitto.conf    ← Mosquitto config
/var/log/mosquitto/mosquitto.log ← Logs
```

## Key IP Addresses (Example)

| Device | IP Address | Role | Ports |
|--------|------------|------|-------|
| Server PC | 192.168.137.1 | MQTT Broker | 1883 (TCP) |
| PC1 | 192.168.137.10 | Dashboard Train A | 8050 (HTTP), 5555 (UDP) |
| PC2 | 192.168.137.20 | Dashboard Train B | 8050 (HTTP), 5556 (UDP) |
| PC3 | 192.168.137.30 | Dashboard Train C | 8050 (HTTP), 5557 (UDP) |
| ESP32 A | 192.168.137.101 | Train A hardware | - |
| ESP32 B | 192.168.137.102 | Train B hardware | - |
| ESP32 C | 192.168.137.103 | Train C hardware | - |

## Next Steps

1. **Test one train first** - Get Train A working completely before adding B and C
2. **Monitor MQTT traffic** - Keep `mosquitto_sub` running to see all communication
3. **Document your IPs** - Write down which PC has which IP and train
4. **Set up data collection** - Script to gather CSV files from all PCs
5. **Read full guide** - [README_DISTRIBUTED_SETUP.md](README_DISTRIBUTED_SETUP.md) for details

## Useful Commands

```bash
# Find your PC's IP
ip addr show           # Linux
ipconfig              # Windows

# Start dashboard
python launch_train.py trainA

# Monitor all MQTT traffic
mosquitto_sub -h 192.168.137.1 -t "#" -v

# Monitor one train's MQTT traffic
mosquitto_sub -h 192.168.137.1 -t "trenes/trainA/#" -v

# Send test MQTT message
mosquitto_pub -h 192.168.137.1 -t "trenes/trainA/test" -m "hello"

# Test UDP listening
nc -u -l 5555         # Listen on UDP port 5555

# Check Mosquitto status
sudo systemctl status mosquitto      # Linux
net start mosquitto                  # Windows

# View Mosquitto logs
sudo tail -f /var/log/mosquitto/mosquitto.log  # Linux
```

## Support

Full documentation:
- [README_DISTRIBUTED_SETUP.md](README_DISTRIBUTED_SETUP.md) - Complete distributed setup guide
- [DEPLOYMENT_COMPARISON.md](DEPLOYMENT_COMPARISON.md) - Compare centralized vs distributed
- [README_MULTI_TRAIN.md](README_MULTI_TRAIN.md) - Centralized multi-train guide
- [CLAUDE.md](CLAUDE.md) - Development guidelines

For issues, check:
- Mosquitto logs
- Dashboard console output
- ESP32 serial monitor
- MQTT traffic with mosquitto_sub
