# Multi-Train Deployment Comparison Guide

## Quick Decision Matrix

| Requirement | Centralized | Distributed |
|------------|-------------|-------------|
| **Each user has own PC/laptop** | ❌ Not needed | ✅ Required |
| **Users access via tablets/thin clients** | ✅ Ideal | ❌ Not suitable |
| **Number of trains** | Best for 2-5 | Scales to 10+ |
| **Central monitoring needed** | ✅ Easy via admin panel | ❌ Harder (need separate tool) |
| **Network resilience** | ❌ Single point of failure | ✅ Independent operation |
| **Setup complexity** | ⭐⭐ Moderate | ⭐⭐⭐ More complex |
| **Maintenance** | ⭐⭐⭐ Easier (one place) | ⭐⭐ More places to manage |
| **Performance (many trains)** | ❌ Limited by server | ✅ Distributed load |
| **User experience** | Browser-based | Native (localhost) |

## Architecture Comparison

### Centralized (multi_train_wrapper.py)

```
┌─────────────────────────────────────────────────┐
│          Server PC (192.168.137.1)              │
│  ┌───────────────────────────────────────────┐  │
│  │   Multi-Train Wrapper (Port 8050)         │  │
│  │  ┌─────────────────────────────────────┐  │  │
│  │  │ Dashboard A │ Dashboard B │ Dash C  │  │  │
│  │  │ UDP:5555   │ UDP:5556   │ UDP:5557│  │  │
│  │  └─────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────┘  │
│            ▲                                     │
│            │ MQTT (localhost:1883)               │
│            ▼                                     │
│  ┌───────────────────┐                          │
│  │ Mosquitto Broker  │                          │
│  └───────────────────┘                          │
└─────────────────────────────────────────────────┘
         ▲           ▲           ▲
         │ UDP       │ UDP       │ UDP
         │           │           │
    ESP32 A     ESP32 B     ESP32 C
    (5555)      (5556)      (5557)

Users access via:
- PC/Tablet → http://192.168.137.1:8050/train/trainA
- PC/Tablet → http://192.168.137.1:8050/train/trainB
- PC/Tablet → http://192.168.137.1:8050/train/trainC
```

**Pros:**
- ✅ Single point of management
- ✅ Easy user access (just a URL)
- ✅ Works with any device (tablets, phones, PCs)
- ✅ Central monitoring via admin panel
- ✅ Easier to update (one place)

**Cons:**
- ❌ Server becomes bottleneck
- ❌ Single point of failure
- ❌ All ESP32s send UDP to same PC
- ❌ Performance degrades with many trains

### Distributed (launch_train.py on each PC)

```
┌────────────────────────┐
│   Server PC (.1)       │
│  ┌──────────────────┐  │
│  │ Mosquitto Broker │  │
│  │   Port 1883      │  │
│  └──────────────────┘  │
└────────────────────────┘
          ▲
          │ MQTT
    ┌─────┴─────┬─────────────┐
    │           │             │
┌───┴───────┐ ┌─┴───────────┐ ┌┴────────────┐
│ PC1 (.10) │ │ PC2 (.20)   │ │ PC3 (.30)   │
│┌─────────┐│ │┌───────────┐│ │┌───────────┐│
││Dashboard││ ││Dashboard  ││ ││Dashboard  ││
││  A      ││ ││  B        ││ ││  C        ││
││UDP:5555 ││ ││UDP:5556   ││ ││UDP:5557   ││
│└─────────┘│ │└───────────┘│ │└───────────┘│
└───────────┘ └─────────────┘ └─────────────┘
    ▲              ▲              ▲
    │ UDP          │ UDP          │ UDP
    │              │              │
ESP32 A        ESP32 B        ESP32 C
→.10:5555     →.20:5556      →.30:5557

Users access:
- PC1 user → http://localhost:8050 (Train A)
- PC2 user → http://localhost:8050 (Train B)
- PC3 user → http://localhost:8050 (Train C)
```

**Pros:**
- ✅ Fully independent operation
- ✅ Distributed load
- ✅ Highly scalable
- ✅ No single point of failure
- ✅ Better performance per train

**Cons:**
- ❌ Each PC needs setup
- ❌ More complex to manage
- ❌ Harder to monitor all trains
- ❌ Users need their own PCs

## Setup Complexity

### Centralized Setup Time: ~15 minutes

1. Configure trains_config.json (2 min)
2. Start multi_train_wrapper.py (1 min)
3. Configure ESP32s (10 min)
4. Share URLs with users (2 min)

### Distributed Setup Time: ~30 minutes

1. Set up Mosquitto on server PC (5 min)
2. Configure trains_config.json on each PC (5 min)
3. Launch dashboard on each PC (5 min)
4. Configure ESP32s with correct IPs (15 min)

## Command Reference

### Centralized

**Start server:**
```bash
cd train_control
python multi_train_wrapper.py
```

**Access:**
- Landing: http://192.168.137.1:8050/
- Train A: http://192.168.137.1:8050/train/trainA
- Train B: http://192.168.137.1:8050/train/trainB
- Admin: http://192.168.137.1:8050/admin

**Stop server:**
```bash
Ctrl+C
```

### Distributed

**On server PC (MQTT broker):**
```bash
sudo systemctl start mosquitto  # Linux
net start mosquitto             # Windows
```

**On PC1 (Train A):**
```bash
cd train_control
python launch_train.py trainA
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

**Access:**
- PC1: http://localhost:8050 (Train A)
- PC2: http://localhost:8050 (Train B)
- PC3: http://localhost:8050 (Train C)

## Network Requirements

### Centralized

**Server PC:**
- Must be accessible to all users
- Must be able to receive UDP from all ESP32s
- Runs Mosquitto broker
- Runs all dashboards

**User devices:**
- Just need web browser
- Must be on same network as server

**ESP32s:**
- All send UDP to server IP
- All connect to MQTT broker on server

### Distributed

**Server PC:**
- Runs Mosquitto broker only
- Must be accessible to all PCs and ESP32s

**Dashboard PCs:**
- Each runs own dashboard
- Must be accessible to their ESP32 (for UDP)
- Must be able to reach server PC (for MQTT)

**ESP32s:**
- Each sends UDP to its own PC
- All connect to MQTT broker on server PC

## Resource Usage

### Centralized (5 trains)

**Server PC:**
- RAM: ~300MB (50MB × 5 dashboards + 50MB base)
- CPU: ~20% during active experiments
- Network: ~50KB/s (10KB/s × 5 trains)

**User devices:**
- Minimal (just browser)

### Distributed (5 trains)

**Server PC (MQTT broker only):**
- RAM: ~50MB (Mosquitto)
- CPU: <5%
- Network: ~5KB/s (MQTT messages only)

**Each dashboard PC:**
- RAM: ~100MB (single dashboard)
- CPU: ~5% (single train)
- Network: ~10KB/s (single train)

**Total across all PCs:**
- RAM: ~300MB distributed
- CPU: Distributed
- Network: Similar total but distributed

## Maintenance

### Centralized

**Updating platform:**
```bash
# On server PC only
git pull
python multi_train_wrapper.py  # Restart
```

**Adding new train:**
1. Edit trains_config.json
2. Restart server
3. Share new URL

### Distributed

**Updating platform:**
```bash
# On EACH PC
git pull
python launch_train.py trainX  # Restart each
```

**Adding new train:**
1. Set up new PC
2. Install platform
3. Configure trains_config.json
4. Launch dashboard

## Monitoring

### Centralized

**Built-in monitoring:**
- Admin panel shows all trains
- Single console output
- Single log location

**MQTT monitoring:**
```bash
mosquitto_sub -h localhost -t "trenes/#" -v
```

### Distributed

**Monitoring all trains:**
```bash
# From any PC
mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v
```

**Need to check each PC:**
- SSH into each PC
- Check console output
- Check CSV files

## Troubleshooting

### Centralized

**Dashboard not accessible:**
- Check server PC is running
- Check `dashboard_host` in config (should be `0.0.0.0` for network access)
- Check firewall allows port 8050

**Train not appearing:**
- Check trains_config.json has `"enabled": true`
- Restart server

### Distributed

**Dashboard can't connect to MQTT:**
- Check `mqtt_broker_ip` is correct
- Check Mosquitto is running on server PC
- Test: `mosquitto_sub -h 192.168.137.1 -t "test"`

**No UDP data:**
- Check ESP32 sending to correct PC IP
- Check `network_ip` in trains_config.json
- Check firewall allows UDP port

## Best Practices

### Centralized

1. **Use strong server PC** - Handles all load
2. **Monitor server resources** - Watch RAM/CPU
3. **Limit concurrent experiments** - To avoid overload
4. **Use admin panel** - For central monitoring
5. **Backup trains_config.json** - Single point of configuration

### Distributed

1. **Document PC assignments** - Which PC runs which train
2. **Standardize configs** - Same trains_config.json on all PCs
3. **Central MQTT logging** - Monitor broker for all traffic
4. **Automate CSV collection** - Script to gather from all PCs
5. **Use static IPs** - Or DHCP reservations for consistency

## Migration

### From Centralized to Distributed

1. Stop centralized server
2. Install Mosquitto on dedicated server PC
3. Install platform on each user PC
4. Update trains_config.json on each PC
5. Reconfigure ESP32s with new UDP destinations
6. Launch dashboards on each PC

### From Distributed to Centralized

1. Stop all distributed dashboards
2. Choose one PC as server
3. Update trains_config.json with `"dashboard_host": "0.0.0.0"`
4. Reconfigure ESP32s to send UDP to server IP
5. Start multi_train_wrapper.py
6. Share URLs with users

## Real-World Scenarios

### Scenario 1: University Lab (10 students)

**Recommended: Centralized**

- Students access from lab computers
- Instructor monitors via admin panel
- Single point of updates
- Easy to manage

Setup:
```bash
# Server PC in lab
python multi_train_wrapper.py

# Students access via browser
http://lab-server.university.edu:8050/train/trainX
```

### Scenario 2: Remote Learning (5 students)

**Recommended: Distributed**

- Each student has own laptop
- Students work independently
- Better network resilience
- Students have full control

Setup:
```bash
# Instructor's PC runs MQTT broker
# Each student runs on their laptop
python launch_train.py trainX
```

### Scenario 3: Research Lab (3 researchers)

**Recommended: Distributed**

- Each researcher has dedicated workstation
- Long-running experiments
- Need for data independence
- High reliability required

Setup:
```bash
# Each workstation
python launch_train.py trainX
# Data stays local
# Independent operation
```

### Scenario 4: Classroom Demo (2-3 trains)

**Recommended: Centralized**

- Short sessions
- Projected for class
- Easy switching between trains
- Simple setup

Setup:
```bash
# Teacher's laptop
python multi_train_wrapper.py
# Project landing page for class
```

## Hybrid Approach

You can mix both approaches:

**Example: 5 trains total**
- 3 trains on centralized server (for general use)
- 2 trains on dedicated PCs (for research)

Setup:
```bash
# Server PC
python multi_train_wrapper.py  # Runs trainA, trainB, trainC

# Research PC 1
python launch_train.py trainD

# Research PC 2
python launch_train.py trainE
```

All connect to same MQTT broker, each uses unique topics.

## Summary

### Choose Centralized When:
- 👥 Multiple users sharing resources
- 💻 Users don't have their own PCs
- 📊 Central monitoring is important
- 🎓 Educational/demo environment
- 🔧 Easy maintenance is priority

### Choose Distributed When:
- 💪 Each user has their own PC
- 🚀 Performance and scalability matter
- 🔒 Independence and resilience needed
- 🔬 Research or long-term experiments
- 👨‍💻 Users are tech-savvy

### Both Approaches Share:
- ✅ Same trains_config.json format
- ✅ Same ESP32 firmware
- ✅ Same MQTT topic structure
- ✅ Same dashboard features
- ✅ Easy to switch between modes

## Quick Start Links

**Centralized:**
- Full guide: [README_MULTI_TRAIN.md](README_MULTI_TRAIN.md)
- Launch: `python multi_train_wrapper.py`

**Distributed:**
- Full guide: [README_DISTRIBUTED_SETUP.md](README_DISTRIBUTED_SETUP.md)
- Launch: `python launch_train.py trainX`

**ESP32 Configuration:**
- Universal firmware: [tren_esp_universal/](tren_esp_universal/)
- Configuration guide: [FIRMWARE_CONFIG_GUIDE.md](FIRMWARE_CONFIG_GUIDE.md)
