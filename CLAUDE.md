# Coding Guidelines for Train Control Platform

## Project Overview

This is a Train Control Platform for ESP32-based PID control experiments. It's a unified web application that combines UDP data collection, MQTT parameter synchronization, and a Dash-based web dashboard for real-time train control and data visualization.

**Key Features:**
- Network interface auto-detection for ESP32 communication
- Real-time PID parameter control and synchronization via MQTT
- Step Response experiment mode for system identification
- **Deadband Calibration** - Automated calibration of motor deadband (minimum PWM to overcome static friction)
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
3. **DataManager** - Thread-safe data sharing between UDP receiver and dashboard with queues and locks (supports PID, Step Response, and Deadband modes)
4. **UDPReceiver** - Background thread for receiving sensor data from ESP32 via UDP
5. **TrainControlDashboard** - Dash application with tabs for network config, PID control, step response, deadband calibration, and data visualization

### File Structure

- `train_control_platform.py` - Main monolithic application file (~3400 lines, includes deadband feature)
- `train_control_platform_backup*.py` - Backup versions (historical)
- `network_config.json` - Persisted network configuration
- `experiment_YYYYMMDD_HHMMSS.csv` - Timestamped PID experiment data files
- `step_response_YYYYMMDD_HHMMSS.csv` - Step response experiment data files
- `deadband_YYYYMMDD_HHMMSS.csv` - Deadband calibration data files
- `requirements.txt` - Python dependencies
- `README_platform.md` - User documentation

### ESP32 Firmware Structure

**Arduino IDE Requirement:** The main `.ino` file MUST have the same name as its containing folder.

#### **RECOMMENDED for Multi-Train: Universal Firmware**

**`tren_esp_universal/tren_esp_universal.ino`** - ⭐ **BEST CHOICE**
- ✅ One firmware for ALL trains (no modification needed)
- ✅ Configure via serial commands after upload (`SET_TRAIN:trainA:5555`)
- ✅ EEPROM-based configuration (persists across reboots)
- ✅ LED status feedback (4 patterns)
- ✅ All features: PID, Step Response, Deadband Calibration (~36KB)
- ✅ 100% standalone (no tab files needed)
- ✅ Python configuration tool included

**When to use**: Multi-train deployments, easy ESP32 replacement, no firmware recompilation

#### Alternative: Manual Configuration Firmware

**`tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino`**
- Complete firmware with all features (~29KB)
- Requires manual modification before upload (hardcoded train ID)
- Uses tab files: `actuadores.ino`, `sensores.ino`
- All features: PID, Step Response, Deadband Calibration

**When to use**: Single train, or when firmware code needs modification

#### Legacy Firmware (Archived)

- `tren_esp_unified/tren_esp_unified.ino` - Basic firmware (PID + Step Response only, no deadband)
- `tren_esp_FIXED/tren_esp_FIXED.ino` - Legacy FIXED version
- `tren_esp/tren_esp.ino` - Original legacy firmware

**Note**: Legacy firmware is in `archives/old_firmware/` directory

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
7. **NEVER enable Flask debug mode in production** - Use `debug=False, use_reloader=False` in `dashboard.run()` to prevent context issues

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
5. **Network interfaces not showing in dropdown** - See "WSL + Windows Network Context Issue" below

### WSL + Windows Network Context Issue

**Problem**: When running the dashboard from Windows command prompt while in WSL environment, Flask's debug mode can cause the app to reload in WSL context instead of Windows context. This results in:
- Network interface detection finding WSL interfaces (lo, eth0, docker0) instead of Windows interfaces
- Missing the required Windows network interface (e.g., "Local Area Connection* 12" with IP 192.168.137.1)
- Unable to connect to ESP32 via the correct interface

**Root Cause**:
- Flask debug mode enables auto-reloader (`use_reloader=True` by default)
- The reloader restarts the Python process, which can switch execution context from Windows Python to WSL Python
- WSL Python's `psutil.net_if_addrs()` detects different network interfaces than Windows Python

**Symptoms**:
1. Terminal shows multiple interface detection cycles during startup
2. First detection shows correct Windows interfaces (e.g., "Shared Network: 192.168.137.1")
3. Subsequent reloads show WSL interfaces (e.g., "Corporate: 10.255.255.254", "Ethernet: 172.30.175.156", "Network: 172.17.0.1")
4. Browser dropdown only shows WSL interfaces
5. Terminal shows "Debug mode: on" even when code has `debug=False`

**Solution**:
1. **Disable Flask reloader** in `dashboard.run()`:
   ```python
   def run(self, host='127.0.0.1', port=8050, debug=True, use_reloader=True):
       """Run the dashboard"""
       self.app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)
   ```

2. **Call with reloader disabled**:
   ```python
   # Force disable debug mode and reloader
   import os
   os.environ['FLASK_DEBUG'] = '0'

   dashboard.run(debug=False, use_reloader=False)  # CRITICAL: use_reloader=False
   ```

3. **Verify fix worked**:
   - Only ONE interface detection cycle in terminal (not multiple)
   - No "Debug mode: on" message
   - Dropdown shows Windows interfaces including the ESP32 connection interface
   - `[RENDER_TAB]` and `[CREATE_NETWORK_TAB]` messages appear when switching tabs

**Alternative workaround** (if solution above doesn't work):
- Run Python directly from Windows (not through WSL)
- Clear all Python cache: `del /S /Q __pycache__` and `del /s /q *.pyc`
- Force browser hard refresh: `Ctrl + F5` or `Ctrl + Shift + R`

**Prevention**:
- Always use `use_reloader=False` in production
- Never rely on Flask's auto-reloader in mixed WSL/Windows environments
- Test network interface detection immediately after startup
- Add debug logging to track which Python context is executing

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

## Deadband Calibration Feature

### Overview

The Deadband Calibration feature automates the process of finding the minimum PWM value needed to overcome motor static friction and initiate movement. This is critical for accurate PID control at low speeds.

### How It Works

1. **User configures**:
   - Direction (forward/reverse)
   - Motion threshold (cm) - minimum distance to consider "motion detected"

2. **ESP32 performs calibration**:
   - Gradually increases PWM from 0
   - Monitors distance sensor for motion
   - Records the PWM value when motion is first detected
   - Publishes calibrated deadband value via MQTT

3. **Dashboard displays**:
   - Real-time PWM vs Time graph
   - Real-time Distance vs Time graph
   - Calibration curve (PWM vs Distance)
   - Final deadband value (in PWM units)

4. **Apply to PID**:
   - User can apply calibrated deadband to PID control mode
   - ESP32 adds deadband compensation to PID output

### MQTT Topics

```python
MQTT_TOPICS = {
    'deadband_sync': 'trenes/deadband/sync',              # Start/Stop calibration
    'deadband_direction': 'trenes/deadband/direction',    # Motor direction
    'deadband_threshold': 'trenes/deadband/threshold',    # Motion threshold (cm)
    'deadband_apply': 'trenes/deadband/apply',            # Apply to PID mode
    'deadband_direction_status': 'trenes/deadband/direction/status',
    'deadband_threshold_status': 'trenes/deadband/threshold/status'
}
```

### CSV Data Format

Deadband calibration creates CSV files: `deadband_YYYYMMDD_HHMMSS.csv`

Format: `time_event,pwm,distance,initial_distance,motion_detected`

### Firmware Requirements

**CRITICAL:** The basic `tren_esp_unified/tren_esp_unified.ino` firmware does NOT support deadband calibration. You MUST use `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino` for deadband feature support.

The `tren_esp_unified_FIXED.ino` firmware includes:
- MQTT subscription to `trenes/deadband/*` topics
- Deadband calibration state machine
- Automatic PWM ramping algorithm
- Motion detection logic
- Result publishing to dashboard

### Dashboard Implementation

The deadband tab includes:
- Configuration panel (direction, threshold)
- Start/Stop buttons
- Status display
- Result display with PWM value
- "Apply to PID" button
- Three real-time graphs (PWM, Distance, Calibration Curve)
- Update interval: 500ms via `dcc.Interval`

### Common Issues

1. **Tab not showing**: Fixed in 2025-11-06-v2 by adding deadband tab to `change_language` callback
2. **"publish" attribute error**: Fixed by using `paho.mqtt.publish.single()` instead of `mqtt_sync.publish()`
3. **No MQTT response**: Check that COMPLETE firmware is loaded on ESP32
4. **Motion not detected**: Adjust motion threshold or check sensor calibration

## ESP32 Firmware Parameter Handling

### Step Response Mode Parameter Acceptance

**Issue**: ESP32 firmware originally rejected step response parameters unless already in STEP_MODE, creating a chicken-and-egg problem where:
1. Dashboard couldn't set parameters before starting experiment
2. ESP32 wouldn't accept parameters until in STEP_MODE
3. User saw "Waiting for parameters..." indefinitely

**Solution**: Modified firmware to accept step parameters regardless of current mode:

```cpp
// BEFORE (lines 590-619 in tren_esp_unified_FIXED.ino):
else if (currentExperimentMode != PID_MODE && currentExperimentMode != DEADBAND_MODE) {
    if (topic_str == "trenes/step/amplitude") {
        // Only accept if in STEP_MODE
    }
}

// AFTER (FIXED):
// IMPORTANT: Allow setting step parameters regardless of current mode
// This allows dashboard to set parameters before switching to STEP_MODE
if (topic_str == "trenes/step/amplitude") {
    StepAmplitude = mensaje.toFloat();
    StepAmplitude = constrain(StepAmplitude, 0.0, v_batt);
    client.publish("trenes/step/amplitude/status", String(StepAmplitude, 1).c_str());
}
```

**Additional fix**: Commented out parameter reset on stop to preserve values:
```cpp
// Don't reset parameters when stopping - keep them for next start
// StepAmplitude = 0;
// StepTime = 0;
```

This allows the dashboard to set parameters, stop experiments, and restart without re-entering values.

### Direction Value Mapping

**Issue**: Dashboard and firmware had inverted direction values:
- Dashboard: Forward=0, Reverse=1
- Firmware: Forward=1, Reverse=0

Selecting "Reverse" made the train go forward and vice versa.

**Solution**: Align dashboard with firmware conventions:
```python
# Dashboard radio button values (train_control_platform.py lines 2100-2103):
{'label': f"  {self.t('forward')}", 'value': 1},   # Changed from 0
{'label': f"  {self.t('reverse')}", 'value': 0}    # Changed from 1

# Display logic (line 3395):
direction = self.t('forward') if confirmed['direction'] == 1 else self.t('reverse')
```

### Step Response Baseline Sampling

**Purpose**: Collect baseline samples before applying step input to:
1. Get steady-state reference measurements
2. Identify sensor initialization issues vs. real disturbances
3. Improve data quality for system identification

**Implementation**: Modified firmware to delay step application:

**Firmware changes** (`tren_esp_unified_FIXED.ino`):
```cpp
// NEW: Delay step application to get baseline samples (lines 130-133)
int stepSampleCounter = 0;
const int STEP_DELAY_SAMPLES = 2;  // Number of samples to wait before applying step
double appliedStepValue = 0.0;     // Actual step value being applied (0 initially, then StepAmplitude)

// Modified loop_step_experiment() (lines 315-337):
// Reset counter when experiment starts
stepSampleCounter = 0;
appliedStepValue = 0.0;

// Apply step only after collecting baseline samples
if (stepSampleCounter < STEP_DELAY_SAMPLES) {
    // Baseline period - motor off, step = 0
    appliedStepValue = 0.0;
    MotorSpeed = 0;
    stepSampleCounter++;
} else {
    // Apply the step
    appliedStepValue = StepAmplitude;
    u_step = StepAmplitude * 1024 / v_batt;
    MotorSpeed = constrain(u_step, 0, 1024);
}

// Modified send_udp_step_data() to include appliedStepValue (line 789):
String cadena = String(delta) + "," +
                String(time_now) + "," +
                String(StepMotorDirection) + "," +
                String(v_batt) + "," +
                String(medi) + "," +
                String(StepAmplitude) + "," +
                String(MotorSpeed) + "," +
                String(appliedStepValue);  // NEW: Shows 0.0 during baseline, then StepAmplitude
```

**Dashboard changes** (`train_control_platform.py`):
```python
# Updated CSV header (lines 612-614):
writer.writerow(['time2sinc', 'time_event', 'motor_dir', 'v_batt',
                'output_G', 'step_input', 'PWM_input', 'applied_step'])

# Updated data parsing (lines 635-664):
if len(data_parts) >= 8:
    # Parse new format with applied_step field
    self.latest_data = {
        # ... other fields ...
        'applied_step': float(data_parts[7]),  # NEW: 0 for baseline, then StepAmplitude
    }
elif len(data_parts) >= 7:
    # Backward compatibility for old firmware
    self.latest_data = {
        # ... other fields ...
        'applied_step': float(data_parts[5]),  # Fallback: use step_input
    }
```

**CSV Format**:
- **applied_step column**: Shows `0.0` for first 2 samples (baseline), then actual step amplitude
- Users can easily identify when the step was applied by looking at this column
- Helps distinguish sensor noise from actual step response

**Benefits**:
- Clean baseline data for system identification
- Easy to identify step application time in CSV
- Helps debug sensor initialization issues
- Improves quality of transfer function estimation

## Dashboard Performance Optimization

### Reducing Console Spam

**Issue**: MQTT status refresh interval triggered callback logging every 200ms, flooding the console with:
```
[STEP PARAM CALLBACK] Triggered by: mqtt-status-refresh
[STEP PARAM CALLBACK] Triggered by: mqtt-status-refresh
...
```

**Solution**: Filter out refresh interval triggers from logging (lines 2893-2895):
```python
# Only log actual parameter changes, not refresh intervals
if trigger_id != 'mqtt-status-refresh':
    print(f"[STEP PARAM] Callback triggered by: {trigger_id}")
```

### CSV Download for Multiple Experiment Types

**Issue**: Download CSV button only worked for PID experiments (`experiment_*.csv`), not for Step Response or Deadband calibration.

**Solution**: Enhanced download callback to support all experiment types (lines 2914-2978):
```python
def create_download_callback():
    """Shared download logic for all tabs"""
    pid_files = glob.glob("experiment_*.csv")
    step_files = glob.glob("step_response_*.csv")
    deadband_files = glob.glob("deadband_*.csv")
    all_csv_files = pid_files + step_files + deadband_files

    if all_csv_files:
        active_csv = max(all_csv_files, key=os.path.getmtime)  # Most recent
        file_size = os.path.getsize(active_csv)
        if file_size > 100:  # Ensure file has content
            return dcc.send_file(active_csv)
```

**Implementation**: Added unique download buttons to each tab:
- Control tab: `download-csv-btn-control`
- Step Response tab: `download-csv-btn-step`
- Deadband tab: `download-csv-btn-deadband`

### Dynamic Tab Content Regeneration

**Issue**: Network interface dropdown populated during initial layout creation, never updated when switching tabs or when interfaces changed.

**Solution**: Make tab content dynamic by calling creation methods in `render_tab_content()` callback:
```python
@self.app.callback(
    Output('tab-content', 'children'),
    [Input('main-tabs', 'value'),
     Input('language-store', 'data')]
)
def render_tab_content(active_tab, language_data):
    if active_tab == 'network-tab':
        return self.create_network_tab()  # Regenerates content each time
    # ... other tabs
```

This ensures interface detection runs fresh every time the Network tab is clicked, showing current available interfaces.

## Multi-Train Architecture (2025-11-09)

### Overview

The platform now supports **multi-train control** where multiple ESP32 trains can be controlled from a single web server, each with independent dashboards accessible via unique URLs.

### Architecture Components

#### 1. Multi-Train Wrapper (`multi_train_wrapper.py`)

**Purpose**: Manages multiple train dashboard instances with URL-based routing

**Key Classes**:
- `MultiTrainApp` - Main wrapper that creates and manages multiple train dashboards
- `TrainConfig` (dataclass) - Configuration for a single train
- `TrainConfigManager` - Loads/saves train configurations from `trains_config.json`

**URL Routes**:
- `/` - Landing page with train selection grid
- `/train/{trainId}` - Full dashboard for specific train (e.g., `/train/trainA`)
- `/admin` - Admin panel for viewing/managing train configurations

#### 2. Train Configuration (`trains_config.json`)

**Format**:
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
    }
  },
  "dashboard_host": "127.0.0.1",
  "dashboard_port": 8050
}
```

**Key Fields**:
- `udp_port` - Unique UDP port per train (5555, 5556, 5557, etc.)
- `mqtt_prefix` - Train-specific MQTT topic prefix (e.g., `trenes/trainA`)
- `enabled` - Show/hide train on landing page

#### 3. Data Isolation

**CSV Files**: Automatically prefixed with train ID
- `trainA_experiment_20251109_143052.csv`
- `trainA_step_response_20251109_143052.csv`
- `trainA_deadband_calibration_20251109_143052.csv`

**MQTT Topics**: Train-specific prefixes prevent cross-contamination
- Train A: `trenes/trainA/carroD/p`
- Train B: `trenes/trainB/carroD/p`

**UDP Ports**: Each train listens on different port
- Train A: 5555
- Train B: 5556
- Train C: 5557

#### 4. Updated Data Managers

All data manager classes now accept `train_id` parameter:
```python
DataManager(train_id="trainA")
StepResponseDataManager(train_id="trainA")
DeadbandDataManager(train_id="trainA")
```

CSV filenames are automatically prefixed with train ID in:
- `DataManager.set_csv_file()` - PID experiments
- `StepResponseDataManager.create_step_csv()` - Step response
- `DeadbandDataManager.create_deadband_csv()` - Deadband calibration

### Running Multi-Train Mode

**Start Multi-Train Server**:
```bash
python multi_train_wrapper.py
```

**Access Points**:
- Landing page: `http://127.0.0.1:8050/`
- Train A: `http://127.0.0.1:8050/train/trainA`
- Train B: `http://127.0.0.1:8050/train/trainB`
- Admin: `http://127.0.0.1:8050/admin`

**For Shared Access** (change in trains_config.json):
```json
{
  "dashboard_host": "0.0.0.0",  // Listen on all interfaces
  "dashboard_port": 8050
}
```

Then users access via:
- Landing: `http://192.168.137.1:8050/`
- Train A: `http://192.168.137.1:8050/train/trainA`

### ESP32 Firmware Configuration for Multi-Train

**CRITICAL**: Each ESP32 must be configured with unique MQTT topics and UDP port

#### **RECOMMENDED: Universal Firmware (tren_esp_universal.ino)**

**Location**: `tren_esp_universal/tren_esp_universal.ino`

**Features**:
- ✅ One firmware for ALL trains (no manual modification needed)
- ✅ EEPROM-based configuration via serial commands
- ✅ LED status feedback (4 patterns)
- ✅ All experiment modes included (PID, Step Response, Deadband)
- ✅ 100% standalone (no tab files needed)

**Arduino IDE Requirement**: The .ino file MUST be in a folder with the same name:
```
tren_esp_universal/
└── tren_esp_universal.ino  ← Upload this
```

**Upload Process**:
1. Open `tren_esp_universal/tren_esp_universal.ino` in Arduino IDE
2. Select "ESP32 Dev Module"
3. Upload (same firmware to all ESP32s)
4. LED will blink fast (waiting for configuration)

**Configuration via Serial Commands** (115200 baud):

Configure each ESP32 after upload:
```
Serial Monitor → SET_TRAIN:trainA:5555
Serial Monitor → SET_TRAIN:trainB:5556
Serial Monitor → SET_TRAIN:trainC:5557
```

Or use Python configuration tool:
```bash
python configure_train.py --train trainA --udp 5555 --port COM3
```

**Serial Commands**:
- `SET_TRAIN:trainA:5555` - Configure train ID and UDP port
- `GET_TRAIN` - Display current configuration
- `RESET_TRAIN` - Clear configuration (return to config mode)
- `STATUS` - Show WiFi/MQTT connection status

**LED Status Indicators**:
- **Fast blink (200ms)**: Not configured, waiting for `SET_TRAIN` command
- **3 quick flashes**: Configuration saved successfully, rebooting
- **Slow blink (1s)**: Attempting WiFi/MQTT connection
- **Solid ON**: Connected and operational

**Configuration Storage**:
```cpp
// Stored in ESP32 Preferences (non-volatile memory):
Namespace: "train-config"
├── train_id (String)    : "trainA", "trainB", etc.
├── udp_port (Int)       : 5555, 5556, etc.
└── configured (Bool)    : true/false flag
```

**Dynamic Topic Generation**:
For train configured as "trainA":
- MQTT prefix: `trenes/trainA`
- Topics: `trenes/trainA/carroD/p`, `trenes/trainA/sync`, etc. (28 topics total)
- UDP port: 5555

**Configuration Example**:
```
# First boot (not configured)
========================================
TRAIN NOT CONFIGURED - ENTERING CONFIG MODE
Commands:
  SET_TRAIN:trainA:5555 - Configure this ESP32
  GET_TRAIN             - Show configuration
  RESET_TRAIN           - Clear configuration
Waiting for configuration...
[LED fast blink]

# After sending: SET_TRAIN:trainA:5555
Configuring train...
Train ID: trainA
UDP Port: 5555
Configuration saved!
[LED flashes 3 times]
Rebooting...

# After reboot
========================================
TRAIN CONFIGURATION LOADED
Train ID: trainA
UDP Port: 5555
MQTT Prefix: trenes/trainA
========================================
Connecting to WiFi...
Connected! IP: 192.168.1.100
Connecting to MQTT broker...
MQTT Connected!
Subscribed to: trenes/trainA/carroD/p
[LED solid ON]
Ready!
```

**Advantages**:
- Upload once, configure multiple times (no re-upload needed)
- Easy ESP32 replacement (upload firmware → configure via serial)
- No firmware recompilation for different trains
- Configuration persists across reboots
- Clear visual feedback via LED

**Documentation**:
- Full guide: `FIRMWARE_CONFIG_GUIDE.md`
- Quick reference: `QUICK_CONFIG_REFERENCE.md`
- Implementation: `UNIVERSAL_FIRMWARE_IMPLEMENTATION.md`

---

#### Alternative: Compile-Time Configuration (Manual Method)

**Only use if you need to modify firmware code.**

Edit `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino` before uploading:

```cpp
// Train A
#define TRAIN_ID "trainA"
String mqtt_prefix = "trenes/trainA";
const int udpDestPort = 5555;

// Train B
#define TRAIN_ID "trainB"
String mqtt_prefix = "trenes/trainB";
const int udpDestPort = 5556;
```

Update all topic subscriptions:
```cpp
// OLD (hardcoded):
client.subscribe("trenes/carroD/p");

// NEW (train-specific):
client.subscribe((mqtt_prefix + "/carroD/p").c_str());
```

**Drawbacks**:
- Must recompile for each train
- Error-prone (easy to upload wrong firmware)
- Cannot reconfigure without re-upload
- Requires modifying ~50+ topic references

### User Workflow

**For Students/End Users**:
1. Instructor provides train URL (e.g., `http://192.168.137.1:8050/train/trainA`)
2. User bookmarks the URL
3. User accesses their dashboard with full control
4. All features work independently (PID, Step Response, Deadband)

**For Instructors/Admins**:
1. Configure trains in `trains_config.json`
2. Start server: `python multi_train_wrapper.py`
3. Share train-specific URLs with users
4. Monitor all trains via admin panel

### Adding New Trains

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

2. Restart server

3. Configure ESP32 firmware with Train D settings

4. Share URL: `http://<server-ip>:8050/train/trainD`

### Backward Compatibility

**Single-Train Mode Still Works**:
```bash
python train_control_platform.py  # Original single-train mode
```

All existing features remain 100% compatible.

### Performance Considerations

**Resource Usage (per train)**:
- RAM: ~50MB per train dashboard
- CPU: <5% idle, ~15% during experiments
- Network: ~10KB/s per active experiment

**Recommended Limits**:
- Small (2-3 trains): Any modern computer
- Medium (4-6 trains): 4GB RAM, dual-core CPU
- Large (7-10 trains): 8GB RAM, quad-core CPU

### Troubleshooting Multi-Train Issues

**Problem**: Train not appearing on landing page
- Check `"enabled": true` in trains_config.json
- Restart server
- Check console for initialization errors

**Problem**: Cross-train interference (Train A command affects Train B)
- Verify each ESP32 has unique MQTT prefix in firmware
- Check with `mosquitto_sub -t "trenes/#"` to see all traffic
- Confirm ESP32 subscribed to correct topics

**Problem**: No UDP data for specific train
- Verify ESP32 sending to correct UDP port
- Check UDP receiver started (console shows port number)
- Ensure ESP32 and server on same network

**Problem**: Port already in use
- Kill existing process: `sudo fuser -k 8050/tcp`
- Or change port in trains_config.json

### Security Notes

**Current Implementation**:
- No authentication (anyone with URL can access)
- Suitable for trusted local networks only
- MQTT and UDP are unencrypted

**Production Recommendations**:
- Add user authentication
- Use HTTPS for dashboard
- Implement MQTT TLS (port 8883)
- Firewall rules to limit access

### Documentation

See `README_MULTI_TRAIN.md` for:
- Complete setup guide
- User workflow examples
- ESP32 firmware modification guide
- Troubleshooting procedures
- Performance tuning

## Contact & Support

This is a UAI SIMU (Simulation) project. When making changes:

1. Test thoroughly with actual ESP32 hardware
2. Verify both Spanish and English interfaces
3. Test network configuration on different network environments
4. Ensure backward compatibility with existing CSV data files
5. Update README_platform.md with any user-facing changes
6. **For deadband feature**: Ensure `tren_esp_unified_FIXED/tren_esp_unified_FIXED.ino` firmware is uploaded to ESP32
7. **For WSL environments**: Always run with `use_reloader=False` to prevent context switching issues
8. **For multi-train mode**: Test with at least 2 trains to verify data isolation and independent control
