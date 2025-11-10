# Train Control Platform

A unified ESP32-based train control system with advanced network configuration and real-time PID control.

## Features

- **Network Auto-Detection**: Automatically detects all available network interfaces
- **Multi-Network Support**: Handles complex environments with multiple adapters (WiFi, Ethernet, VLAN, WSL)
- **Configuration Persistence**: Remembers your last network settings and auto-applies them on startup
- **Unified Interface**: Single application combining UDP data collection and web dashboard
- **Real-time Control**: Live PID parameter adjustment and data visualization
- **Experiment Management**: Start/stop experiments with automatic data logging

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Platform**:
   ```bash
   python main.py
   ```

3. **Configure Network** (first time only):
   - Open http://127.0.0.1:8050 in your browser
   - Go to "Network Configuration" tab
   - Select your network interface from the dropdown
   - Note the displayed IP address for ESP32 configuration
   - Click "Apply Configuration"
   - **Your settings are automatically saved and will be restored next time!**

4. **ESP32 Setup**:
   - Use the displayed IP address in your ESP32 code
   - Flash the ESP32 with the updated IP
   - Ensure ESP32 is connected to the same network

5. **Run Experiments**:
   - Switch to "PID Control" tab
   - Adjust PID parameters using sliders
   - Set reference distance
   - Click "Start Experiment" to begin data collection
   - Monitor real-time data in the graph

## Network Configuration

The platform automatically detects:
- WiFi adapters
- Ethernet interfaces
- VLAN networks
- Virtual/WSL interfaces

Select the appropriate interface based on your ESP32 connection.

## Data Storage

Experiments are automatically saved as CSV files with timestamps:
- Format: `experiment_YYYYMMDD_HHMMSS.csv`
- Contains: time_event, input, referencia, error, kp, ki, kd, output_PID

## Troubleshooting

- **No interfaces detected**: Click "Refresh Interfaces" button
- **MQTT connection issues**: Verify MQTT broker is running on the selected interface
- **UDP data not received**: Check ESP32 IP configuration and network connectivity
- **Dashboard not loading**: Ensure port 8050 is available

## Architecture

The platform is now modular with these components:
- `main.py` - Main entry point
- `config.py` - Central configuration settings
- `network_manager.py` - Network interface management
- `data_manager.py` - Data handling and UDP communication
- `mqtt_controller.py` - MQTT parameter synchronization
- `dashboard.py` - Web dashboard interface
- `train_control_platform_backup.py` - Original monolithic version (backup)

This modular structure improves maintainability while preserving all functionality.