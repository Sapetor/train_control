# Train Control Platform - Complete Documentation
## ESP32-Based PID Control and Step Response Experiments
### Version 2.0 - October 2025

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Quick Start Guide](#quick-start-guide)
3. [Architecture](#architecture)
4. [Features](#features)
5. [Recent Improvements (Oct 2025)](#recent-improvements-oct-2025)
6. [ESP32 Firmware](#esp32-firmware)
7. [Experiment Modes](#experiment-modes)
8. [Network Configuration](#network-configuration)
9. [MQTT Communication Protocol](#mqtt-communication-protocol)
10. [Data Formats](#data-formats)
11. [Development Guidelines](#development-guidelines)
12. [Testing](#testing)
13. [Troubleshooting](#troubleshooting)
14. [Known Issues](#known-issues)

---

## System Overview

The Train Control Platform is a unified system for ESP32-based train control experiments, supporting both PID control and step response experiments. It features a web-based dashboard for real-time control and data visualization, with automatic network configuration and bilingual support.

### Key Components
- **Python Dashboard** (`train_control_platform.py`) - Web interface for control and visualization
- **ESP32 Firmware** (`tren_esp_unified/`) - Unified firmware supporting both experiment modes
- **Communication** - UDP for data collection, MQTT for parameter synchronization

---

## Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```
Required packages:
- dash>=2.14.0
- plotly>=5.15.0
- pandas>=1.5.0
- paho-mqtt>=1.6.0
- psutil>=5.9.0

### 2. Run the Platform
```bash
python train_control_platform.py
```
Access at: http://127.0.0.1:8050

### 3. Configure Network (First Time)
1. Go to "Network Configuration" tab
2. Select your network interface from dropdown
3. Note the IP address for ESP32 configuration
4. Click "Apply Configuration"
5. Settings are automatically saved

### 4. Configure ESP32
1. Open `tren_esp_unified/tren_esp_unified.ino`
2. Update network settings:
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "YOUR_SELECTED_IP";  // From dashboard
```
3. Upload to ESP32

### 5. Run Experiments
- **PID Control**: Adjust Kp, Ki, Kd parameters and reference distance
- **Step Response**: Set amplitude, duration, and direction
- Click "Start Experiment" to begin data collection
- Data is automatically saved to CSV files

---

## Architecture

### Current Implementation (Monolithic)
The platform currently uses a monolithic architecture with all functionality in `train_control_platform.py`:

```
train_control_platform.py (2700+ lines)
├── NetworkManager       - Network interface detection and configuration
├── DataManager          - Thread-safe data handling for PID experiments
├── StepResponseDataManager - Data handling for step response experiments
├── UDPReceiver          - Background UDP data collection
├── MQTTParameterSync    - MQTT communication for parameters
└── TrainControlDashboard - Dash web application
```

**Note**: README mentions modular architecture (main.py, config.py, etc.) but these files don't exist yet.

---

## Features

### Core Features
- ✅ **Dual Experiment Modes** - PID control and step response in one platform
- ✅ **Network Auto-Detection** - Finds all available network interfaces
- ✅ **Configuration Persistence** - Saves and auto-applies settings
- ✅ **Real-time Visualization** - Live graphs with zoom preservation
- ✅ **Bilingual Support** - Spanish/English with persistent preference
- ✅ **Fast Updates** - Near-instant data updates (100ms latency)
- ✅ **Automatic Data Logging** - CSV files with timestamps

### UI Features
- ✅ **Mode Indicator Badge** - Visual indicator of active mode (Blue=PID, Green=Step)
- ✅ **Connection Status** - Real-time UDP and MQTT status display
- ✅ **Parameter Confirmation** - Shows ESP32-confirmed values
- ✅ **Queue Overflow Detection** - Warns when data is being dropped

---

## Recent Improvements (Oct 2025)

### Critical Bug Fixes
1. **Duplicate Code Removal**
   - Removed duplicate WebSocket queue definition
   - Removed duplicate method definitions

2. **MQTT Configuration Fix**
   - Fixed broker IP to use selected interface instead of localhost

3. **Data Safety**
   - Added CSV flush after writes to prevent data loss
   - Queue overflow detection and logging

### Experiment Mode Switching
1. **Safe Mode Switching** (`switch_experiment_mode()` method)
   - Stops UDP receiver
   - Clears data queues
   - Creates new CSV file
   - Switches data managers
   - Restarts UDP receiver

2. **Mode Isolation**
   - Separate CSV files for each mode
   - Prevents data mixing between experiments
   - Mode-specific data managers

### ESP32 Firmware Race Condition Fixes
1. **Direction Persistence** - Fixed bug where motor direction persisted incorrectly
2. **Parameter Isolation** - PID/Step parameters only update in correct mode
3. **Separate Direction Variables** - `PIDMotorDirection` and `StepMotorDirection`
4. **State Reset** - Proper cleanup when stopping experiments

### UI Enhancements
1. **Mode Indicator** - Badge showing current mode at top of dashboard
2. **Enhanced Status Display** - Better connection and parameter feedback
3. **Language Persistence** - Language preference saved and restored

---

## ESP32 Firmware

### Unified Firmware (`tren_esp_unified/`)
Single firmware supporting both PID and step response experiments.

#### Key Features
- Automatic mode switching via MQTT topics
- Separate state management for each mode
- WiFi + MQTT + UDP communication
- ToF sensor support with custom I2C pins

#### Files
- `tren_esp_unified.ino` - Main firmware file
- `actuadores.ino` - Motor control functions
- `sensores.ino` - ToF sensor functions
- `FIXES_APPLIED.txt` - History of critical fixes
- `tren_esp_unified_RACE_FIXES.md` - Recent race condition fixes

#### Critical Fixes Applied (Oct 2025)
- Separate direction variables for each mode
- Direction reset on experiment stop
- Parameter isolation between modes
- Simplified PID control logic

---

## Experiment Modes

### PID Control Mode

#### Features
- Real-time distance tracking with ToF sensor
- Adjustable PID parameters (Kp, Ki, Kd)
- Reference distance setting (1-100cm)
- Deadband compensation
- Automatic integral windup prevention

#### Data Format (CSV)
```
time_event,input,referencia,error,kp,ki,kd,output_PID
```

#### MQTT Topics
- `trenes/sync` - Start/stop experiment
- `trenes/carroD/p` - Kp parameter
- `trenes/carroD/i` - Ki parameter
- `trenes/carroD/d` - Kd parameter
- `trenes/ref` - Reference distance

### Step Response Mode

#### Features
- Open-loop control for system identification
- Adjustable step amplitude (0-8.4V)
- Configurable duration (0-20s)
- Motor direction control
- Battery voltage compensation

#### Data Format (CSV)
```
time2sinc,time_event,motor_dir,v_batt,output_G,step_input,PWM_input
```

#### MQTT Topics
- `trenes/step/sync` - Start/stop experiment
- `trenes/step/amplitude` - Step amplitude (V)
- `trenes/step/time` - Duration (seconds)
- `trenes/step/direction` - Motor direction (0/1)
- `trenes/step/vbatt` - Battery voltage

---

## Network Configuration

### Automatic Detection
The platform detects and classifies network interfaces:
- WiFi adapters
- Ethernet interfaces
- VLAN networks
- Virtual/WSL interfaces
- Shared networks

### Configuration Persistence
Settings saved in `network_config.json`:
```json
{
  "selected_ip": "192.168.137.1",
  "mqtt_broker_ip": "192.168.137.1",
  "udp_port": 5555,
  "mqtt_port": 1883,
  "language": "en"
}
```

### Auto-Apply
On startup, if saved IP is still available, configuration is automatically applied.

---

## MQTT Communication Protocol

### Connection Parameters
- **Broker**: Selected interface IP
- **Port**: 1883 (default)
- **Keep-alive**: 60 seconds
- **QoS**: 0 (fire-and-forget)

### Parameter Synchronization Flow
1. Dashboard sends parameter via MQTT
2. ESP32 receives and applies
3. ESP32 publishes confirmation to `*_status` topic
4. Dashboard updates UI with confirmed value

### Topic Structure
All topics follow pattern: `trenes/[mode]/[parameter][/status]`

---

## Data Formats

### UDP Data Packets
- **Port**: 5555 (default)
- **Protocol**: UDP
- **Format**: CSV string
- **Frequency**: 20Hz (step) or variable (PID)

### CSV File Naming
- **PID**: `experiment_YYYYMMDD_HHMMSS.csv`
- **Step**: `step_response_YYYYMMDD_HHMMSS.csv`

---

## Development Guidelines

### Code Style
- **Indentation**: 4 spaces
- **Classes**: PascalCase (`NetworkManager`)
- **Methods**: snake_case (`add_data`)
- **Constants**: UPPER_SNAKE_CASE (`DEFAULT_UDP_PORT`)
- **Private methods**: Underscore prefix (`_on_connect`)

### Thread Safety
Always use locks when accessing shared data:
```python
with self.data_lock:
    # Access shared data here
```

### Configuration Constants
All configuration values defined at top of file. Never hardcode in methods.

### Bilingual Support
All user-facing text must be in both language dictionaries:
```python
self.translations = {
    'es': {'key': 'Texto en español'},
    'en': {'key': 'English text'}
}
```

### Fast Update System
- 100ms interval checks for new data
- WebSocket-style message queue
- Dual-trigger graph updates (interval + data availability)

---

## Testing

### Test Script (`test_improvements.py`)
Comprehensive test suite for:
- PID data simulation
- Step response data simulation
- Mode switching behavior
- Queue overflow handling

### Testing Procedure

#### Mode Switching Test
1. Set Step Response with reverse direction
2. Run for 5 seconds
3. Stop and switch to PID mode
4. Verify train goes forward (not reverse)

#### Parameter Isolation Test
1. Set Kp=10 in PID mode
2. Switch to Step Response mode
3. Try changing Kp from dashboard
4. Verify Kp remains 10

#### Data Separation Test
1. Run PID experiment
2. Check CSV format
3. Switch to Step Response
4. Verify new CSV created
5. Confirm no data mixing

---

## Troubleshooting

### Common Issues

#### No UDP Data Received
- Check ESP32 IP configuration
- Verify network interface selection
- Ensure ESP32 and PC on same network
- Check firewall settings

#### MQTT Connection Failed
- Verify MQTT broker IP matches selected interface
- Check ESP32 has correct broker IP
- Ensure port 1883 is not blocked

#### Dashboard Not Loading
- Check port 8050 is available
- Verify all dependencies installed
- Check for Python errors in console

#### Wrong Motor Direction
- Ensure using latest firmware with race condition fixes
- Verify direction resets when stopping experiments
- Check mode-specific direction variables

### Console Messages

#### Normal Operation
```
UDP receiver started on 192.168.137.1:5555
[MQTT] Parameter sync connected successfully
[MODE SWITCH] Switching from pid to step
```

#### Warning Messages
```
[WARNING] Data queue full - dropping packet 1000
CSV write error: [specific error]
[MQTT ERROR] Parameter sync failed with code -1
```

---

## Known Issues

### Current Limitations
1. Only one experiment can run at a time
2. Dashboard binds to localhost only (security feature)
3. No authentication (designed for trusted local network)
4. CSV files created in working directory only

### Architecture Mismatch
- README mentions modular architecture but code is monolithic
- Planned refactoring not yet implemented
- All functionality in single 2700+ line file

### Performance
- Queue can overflow at very high data rates (>100Hz)
- Graph updates limited to 1 second intervals for historical data
- Maximum 1000 items in data queue

---

## Future Improvements

### Planned Enhancements
1. **Modular Architecture** - Split into separate modules
2. **WebSocket Implementation** - True WebSocket for real-time updates
3. **Authentication** - Optional security for production use
4. **Data Export** - Multiple format support (JSON, HDF5)
5. **Multi-train Support** - Control multiple trains simultaneously

### Experimental Features
- Custom PID algorithms
- Advanced filtering options
- Machine learning integration for system identification
- Remote access capability

---

## Contact & Support

This is a UAI SIMU (Simulation) project for the Universidad Adolfo Ibáñez.

When making changes:
1. Test with actual ESP32 hardware
2. Verify both language interfaces
3. Test on different network configurations
4. Ensure backward compatibility
5. Update documentation

---

## Version History

- **v2.0 (Oct 2025)** - Race condition fixes, improved mode switching
- **v1.9 (Oct 2025)** - Step response implementation, bilingual support
- **v1.8 (Sep 2025)** - Fast update system, WebSocket-style notifications
- **v1.0 (2024)** - Initial release with PID control

---

*Last Updated: October 28, 2025*
