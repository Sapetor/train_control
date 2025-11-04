# Coding Guidelines for Train Control Platform

## Project Overview

This is a Train Control Platform for ESP32-based PID control experiments. It's a unified web application that combines UDP data collection, MQTT parameter synchronization, and a Dash-based web dashboard for real-time train control and data visualization.

**Key Features:**
- Network interface auto-detection for ESP32 communication
- Real-time PID parameter control and synchronization via MQTT
- Live data visualization with Plotly graphs
- Experiment management with automatic CSV logging
- Bilingual support (Spanish/English)
- Configuration persistence

## Technology Stack

- **Python 3.x**
- **Dash** - Web framework for the dashboard UI
- **Plotly** - Interactive data visualization
- **paho-mqtt** - MQTT client for parameter synchronization with ESP32
- **pandas** - Data processing and CSV handling
- **psutil** - Network interface detection
- **Socket programming** - UDP receiver for ESP32 data
- **Push notification system** - Fast data-availability checking for near-instant updates (100ms latency)

## Code Architecture

### Main Components

1. **MQTTParameterSync** - Handles MQTT communication for PID parameter synchronization with ESP32
2. **NetworkManager** - Manages network interface detection, configuration persistence, and auto-apply functionality
3. **DataManager** - Thread-safe data sharing between UDP receiver and dashboard with queues and locks
4. **UDPReceiver** - Background thread for receiving sensor data from ESP32 via UDP
5. **TrainControlDashboard** - Dash application with tabs for network config, PID control, and data visualization

### File Structure

- `train_control_platform.py` - Main monolithic application file (~1900 lines)
- `train_control_platform_backup.py` - Backup of previous version
- `network_config.json` - Persisted network configuration
- `experiment_YYYYMMDD_HHMMSS.csv` - Timestamped experiment data files
- `requirements.txt` - Python dependencies
- `README_platform.md` - User documentation

## Coding Conventions

### General Principles

1. **Keep the monolithic structure** - The application is currently in a single file. While the README mentions modular components, maintain the current structure unless explicitly refactoring.

2. **Thread safety** - Always use locks when accessing shared data between UDP receiver thread and main dashboard thread:
   ```python
   with self.data_lock:
       # Access shared data here
   ```

3. **Configuration persistence** - Save user settings to `network_config.json` immediately after changes using `save_config()` method.

4. **Bilingual support** - All user-facing text must be added to both `'es'` and `'en'` dictionaries in `self.translations`.

### Code Style

- Use **4 spaces** for indentation (consistent with existing code)
- Class names: **PascalCase** (`NetworkManager`, `DataManager`)
- Method names: **snake_case** (`detect_interfaces`, `add_data`)
- Constants: **UPPER_SNAKE_CASE** (`DEFAULT_UDP_PORT`, `MQTT_TOPICS`)
- Private methods: prefix with underscore (`_on_connect`, `_receive_loop`)

### Comments

- Keep comments **minimal and meaningful**
- Use docstrings for classes and public methods
- Add section dividers for major code blocks:
  ```python
  # =============================================================================
  # Configuration Constants
  # =============================================================================
  ```

### Configuration Constants

All configuration values are defined at the top of the file:

```python
# Network Configuration
DEFAULT_UDP_PORT = 5555
DEFAULT_MQTT_PORT = 1883
UDP_TIMEOUT = 1.0

# Dashboard Configuration
DASHBOARD_HOST = '127.0.0.1'
DASHBOARD_PORT = 8050
DATA_REFRESH_INTERVAL = 1000

# PID Control Limits
PID_KP_MAX = 250
PID_KI_MAX = 150
PID_KD_MAX = 150
```

Never hardcode these values in the methods - always reference the constants.

## Dashboard Development

### Dash Callbacks

- Use `@self.app.callback` decorator for callbacks
- Include `prevent_initial_call=True` when appropriate to avoid unnecessary initial triggers
- Use `callback_context` to identify which input triggered the callback
- Always handle exceptions in callbacks and return meaningful error messages

### Push Notification System

The dashboard uses a fast data-availability checking system for near-instant updates:

- **Fast update check**: `dcc.Interval` at 100ms checks for new data in queue
- **Message queue**: `websocket_messages` queue stores push notifications from UDP/MQTT
- **Data callbacks**: When UDP or MQTT data arrives, it pushes to the queue via `websocket_callback`
- **Graph updates**: Graphs respond to both regular intervals (1s) and fast data checks (100ms)
- **Result**: Average 50ms latency (vs 500ms with 1s polling alone)

**Key components:**
- `_push_websocket_message()` - Adds messages to queue (non-blocking)
- `_get_websocket_message()` - Retrieves messages from queue (non-blocking)
- `check_data_availability()` callback - Checks queue every 100ms and triggers updates
- Graph callbacks have dual inputs: regular interval + `ws-message-store`

### Layout Guidelines

- Use the defined color scheme from `self.colors` dictionary
- Maintain consistent spacing and padding
- Modern, clean design with rounded corners (`borderRadius`)
- Responsive design with flexbox layouts

### Graph Updates

- **Preserve user zoom state** - Use `_handle_zoom_state()` and `_apply_zoom_state()` methods
- Keep separate zoom states for each graph (realtime vs historical)
- Update graphs efficiently without forcing full redraws when user has zoomed

### Performance Optimization

- Limit console output in high-frequency operations (UDP receiver prints every 100 packets)
- Use appropriate refresh intervals:
  - Data graphs: 1000ms
  - MQTT status: 200ms (for immediate feedback)
- Implement max queue sizes to prevent memory issues

## MQTT Communication

### Topics Structure

All MQTT topics are defined in `MQTT_TOPICS` dictionary:

```python
MQTT_TOPICS = {
    'sync': 'trenes/sync',
    'kp': 'trenes/carroD/p',
    'ki': 'trenes/carroD/i',
    'kd': 'trenes/carroD/d',
    'reference': 'trenes/ref',
    'kp_status': 'trenes/carroD/p/status',
    'ki_status': 'trenes/carroD/i/status',
    'kd_status': 'trenes/carroD/kd/status',
    'ref_status': 'trenes/carroD/ref/status',
    'request_params': 'trenes/carroD/request_params'
}
```

### Parameter Synchronization Flow

1. Dashboard sends parameter via MQTT publish
2. ESP32 receives and applies parameter
3. ESP32 confirms by publishing to `*_status` topic
4. Dashboard updates UI with confirmed value

Always show **confirmed values** from ESP32, not just sent values.

## Data Handling

### CSV Format

Data files use this structure:
```
time_event,input,referencia,error,kp,ki,kd,output_PID
```

### Thread-Safe Data Access

```python
def add_data(self, data_string):
    with self.data_lock:
        # Parse and store data
        self.latest_data = {...}
        self.data_queue.put(self.latest_data)
        # Write to CSV
```

### UDP Data Reception

- UDP receiver runs in background daemon thread
- Uses 1-second timeout for graceful shutdown
- Automatically creates CSV files with timestamps
- Handles connection loss gracefully

## Network Configuration

### Interface Detection

- Automatically detects all network interfaces using `psutil.net_if_addrs()`
- Classifies interfaces (WiFi, Ethernet, Virtual, VLAN, etc.)
- Filters out loopback (127.0.0.1) and link-local (169.254.*) addresses

### Auto-Apply Saved Config

- On startup, check if saved IP is still available
- If available, automatically apply configuration
- If not available, prompt user to reconfigure

## Testing Guidelines

### Before Testing

1. Ensure dependencies are installed: `pip install -r requirements.txt`
2. Run the application: `python train_control_platform.py`
3. Access dashboard at: `http://127.0.0.1:8050`

### Test Scenarios

1. **Network Configuration**
   - Test interface detection and selection
   - Verify configuration persistence across restarts
   - Test with different network interfaces

2. **PID Control**
   - Send parameters via MQTT
   - Verify parameter confirmation from ESP32
   - Test parameter range limits

3. **Data Collection**
   - Verify UDP data reception
   - Check CSV file creation and writing
   - Test experiment start/stop functionality

4. **Dashboard Functionality**
   - Test language switching
   - Verify graph zoom preservation
   - Check real-time updates

## Common Pitfalls to Avoid

1. **Don't block the main thread** - Use threading for UDP receiver and MQTT client
2. **Don't forget thread locks** - Always lock when accessing shared data
3. **Don't hardcode paths** - Use `os.path.join()` for cross-platform compatibility
4. **Don't skip exception handling** - Especially in callbacks and background threads
5. **Don't ignore configuration persistence** - Save changes immediately
6. **Don't modify zoom state during updates** - Only update when user explicitly zooms

## Security Considerations

- Dashboard binds to `127.0.0.1` (localhost only) by default
- No authentication required (assumes trusted local network)
- MQTT uses no encryption (for local ESP32 communication)
- CSV files are created in working directory (ensure proper permissions)

## Debugging

### Enable Verbose Logging

Uncomment debug print statements in:
- `_on_message()` method for MQTT debugging
- `_receive_loop()` for UDP reception debugging
- `_get_parameter_status_display()` for parameter sync debugging

### Common Issues

1. **No UDP data received** - Check ESP32 IP configuration and network interface selection
2. **MQTT connection fails** - Verify MQTT broker is running on selected interface
3. **Dashboard not loading** - Ensure port 8050 is not in use
4. **Zoom state not preserved** - Check `_handle_zoom_state()` and `_apply_zoom_state()` implementation

## Future Improvements

The README mentions a modular architecture, but the current implementation is monolithic. If refactoring:

1. Split into separate modules: `config.py`, `network_manager.py`, `data_manager.py`, `mqtt_controller.py`, `dashboard.py`
2. Add unit tests for each module
3. Implement proper logging instead of print statements
4. Add authentication for production deployments
5. Consider WebSocket instead of polling for real-time updates

## Git Workflow

This project is **not currently in a git repository**. If initializing git:

1. Create `.gitignore` to exclude:
   - `__pycache__/`
   - `*.pyc`
   - `experiment_*.csv` (data files)
   - `network_config.json` (local configuration)
   - `.claude/` (AI assistant data)

2. Consider semantic commit messages:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `refactor:` for code refactoring
   - `docs:` for documentation updates

## Contact & Support

This is a UAI SIMU (Simulation) project. When making changes:

1. Test thoroughly with actual ESP32 hardware
2. Verify both Spanish and English interfaces
3. Test network configuration on different network environments
4. Ensure backward compatibility with existing CSV data files
5. Update README_platform.md with any user-facing changes
