# Deadband Calibration Dashboard Integration Guide

## Overview

This document describes how to integrate the new **Deadband Calibration Mode** into the Train Control Platform dashboard.

## New MQTT Topics

### Control Topics (Dashboard → ESP32):

| Topic | Payload | Description |
|-------|---------|-------------|
| `trenes/deadband/sync` | "True" / "False" | Start/stop calibration experiment |
| `trenes/deadband/direction` | 0 / 1 | Set direction (0=Reverse, 1=Forward) |
| `trenes/deadband/threshold` | 0.01 - 1.0 | Motion detection threshold (cm) |
| `trenes/deadband/apply` | "True" | Apply calibrated value to PID mode |
| `trenes/deadband/request_params` | any | Request current calibration parameters |

### Status Topics (ESP32 → Dashboard):

| Topic | Payload | Description |
|-------|---------|-------------|
| `trenes/deadband/direction/status` | 0 / 1 | Confirmed direction |
| `trenes/deadband/threshold/status` | float | Confirmed threshold (cm) |
| `trenes/deadband/result` | integer | Calibrated deadband PWM value |
| `trenes/deadband/applied` | integer | Deadband applied to PID mode |
| `trenes/deadband/error` | string | Error message if calibration fails |

## UDP Data Format

**CSV format**: `time, pwm, distance, initial_distance, motion_detected`

### Fields:
- `time` (ms): Elapsed time since calibration start
- `pwm` (0-1024): Current motor PWM value
- `distance` (cm): Current distance measurement
- `initial_distance` (cm): Distance when calibration started
- `motion_detected` (0/1): 1 when motion threshold exceeded

### Example Data:
```
0,0,10.52,10.52,0
40,1,10.52,10.52,0
80,2,10.52,10.52,0
120,3,10.51,10.52,0
...
5200,130,10.48,10.52,0
5240,131,10.43,10.52,1  ← Motion detected! Deadband = 131
```

## Dashboard Implementation

### 1. Add New Tab: "Deadband Calibration"

Location: Add after "Configuración de Red" tab

### 2. UI Components Needed

#### 2.1 Control Panel
```python
# Deadband calibration controls
html.Div([
    html.H3("Deadband Calibration"),

    # Direction selector
    html.Label("Direction:"),
    dcc.RadioItems(
        id='deadband-direction',
        options=[
            {'label': 'Forward', 'value': 1},
            {'label': 'Reverse', 'value': 0}
        ],
        value=1,
        inline=True
    ),

    # Motion threshold
    html.Label("Motion Threshold (cm):"),
    dcc.Input(
        id='deadband-threshold',
        type='number',
        value=0.08,
        min=0.01,
        max=1.0,
        step=0.01
    ),

    # Start/Stop button
    html.Button(
        "Start Calibration",
        id='deadband-start-btn',
        n_clicks=0,
        style={'backgroundColor': '#4CAF50'}
    ),

    # Apply button
    html.Button(
        "Apply to PID",
        id='deadband-apply-btn',
        n_clicks=0,
        disabled=True
    ),

    # Status display
    html.Div(id='deadband-status', style={'marginTop': '20px'}),

    # Result display
    html.Div([
        html.H4("Calibration Result:"),
        html.Div(id='deadband-result', style={
            'fontSize': '24px',
            'fontWeight': 'bold',
            'color': '#4CAF50'
        })
    ])
])
```

#### 2.2 Visualization Panel
```python
# Real-time graphs
html.Div([
    # PWM vs Time
    dcc.Graph(id='deadband-pwm-graph'),

    # Distance vs Time
    dcc.Graph(id='deadband-distance-graph'),

    # PWM vs Distance (main calibration curve)
    dcc.Graph(id='deadband-curve-graph')
])
```

### 3. MQTT Callback Functions

#### 3.1 Start/Stop Calibration
```python
@app.callback(
    Output('deadband-status', 'children'),
    Input('deadband-start-btn', 'n_clicks'),
    State('deadband-direction', 'value'),
    State('deadband-threshold', 'value'),
    prevent_initial_call=True
)
def start_deadband_calibration(n_clicks, direction, threshold):
    if n_clicks > 0:
        # Set parameters
        mqtt_client.publish("trenes/deadband/direction", str(direction))
        mqtt_client.publish("trenes/deadband/threshold", str(threshold))

        # Start calibration
        mqtt_client.publish("trenes/deadband/sync", "True")

        return html.Div([
            html.Span("🔄 Calibration in progress...",
                     style={'color': 'orange'})
        ])
    return ""
```

#### 3.2 Apply Calibrated Value
```python
@app.callback(
    Output('deadband-apply-btn', 'disabled'),
    Input('deadband-result', 'children')
)
def enable_apply_button(result):
    # Enable button when calibration completes
    return result is None or result == ""

@app.callback(
    Output('deadband-status', 'children'),
    Input('deadband-apply-btn', 'n_clicks'),
    State('deadband-result', 'children'),
    prevent_initial_call=True
)
def apply_deadband(n_clicks, result):
    if n_clicks > 0:
        mqtt_client.publish("trenes/deadband/apply", "True")
        return html.Div([
            html.Span(f"✓ Deadband {result} applied to PID mode",
                     style={'color': 'green'})
        ])
    return ""
```

### 4. Data Collection & Storage

#### 4.1 UDP Receiver Modification
```python
class DataManager:
    def __init__(self):
        # ... existing code ...

        # NEW: Deadband calibration data
        self.deadband_data_queue = queue.Queue()
        self.latest_deadband_data = None
        self.deadband_history = {
            'time': [],
            'pwm': [],
            'distance': [],
            'initial_distance': [],
            'motion_detected': []
        }

    def add_deadband_data(self, data_string):
        """Parse and store deadband calibration data"""
        try:
            parts = data_string.strip().split(',')
            if len(parts) == 5:
                data = {
                    'time': float(parts[0]),
                    'pwm': int(parts[1]),
                    'distance': float(parts[2]),
                    'initial_distance': float(parts[3]),
                    'motion_detected': int(parts[4])
                }

                with self.data_lock:
                    self.latest_deadband_data = data
                    self.deadband_data_queue.put(data)

                    # Store in history
                    for key in data:
                        self.deadband_history[key].append(data[key])

                    # Write to CSV
                    self.write_deadband_csv(data)
        except Exception as e:
            print(f"Error parsing deadband data: {e}")

    def write_deadband_csv(self, data):
        """Write deadband data to CSV file"""
        if self.deadband_csv_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"deadband_calibration_{timestamp}.csv"
            self.deadband_csv_file = open(filename, 'w', newline='')
            self.deadband_csv_writer = csv.writer(self.deadband_csv_file)
            self.deadband_csv_writer.writerow([
                'time_ms', 'pwm', 'distance_cm',
                'initial_distance_cm', 'motion_detected'
            ])

        self.deadband_csv_writer.writerow([
            data['time'],
            data['pwm'],
            data['distance'],
            data['initial_distance'],
            data['motion_detected']
        ])
        self.deadband_csv_file.flush()
```

#### 4.2 UDP Receiver Detection
```python
def _receive_loop(self):
    """UDP receiver loop - detect data type"""
    while self.running:
        try:
            data, addr = self.udp_socket.recvfrom(1024)
            data_string = data.decode('utf-8')

            # Determine data type by field count
            field_count = len(data_string.split(','))

            if field_count == 8:
                # PID data: time,input,ref,error,kp,ki,kd,output
                self.data_manager.add_data(data_string)
            elif field_count == 7:
                # Step response data
                self.data_manager.add_step_data(data_string)
            elif field_count == 5:
                # NEW: Deadband calibration data
                self.data_manager.add_deadband_data(data_string)

        except Exception as e:
            if self.running:
                print(f"UDP receive error: {e}")
```

### 5. Graph Update Callbacks

#### 5.1 PWM vs Time Graph
```python
@app.callback(
    Output('deadband-pwm-graph', 'figure'),
    Input('graph-update-interval', 'n_intervals')
)
def update_pwm_graph(n):
    data = data_manager.deadband_history

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data['time'],
        y=data['pwm'],
        mode='lines',
        name='Motor PWM',
        line=dict(color='blue', width=2)
    ))

    # Mark motion detection point
    if 1 in data['motion_detected']:
        idx = data['motion_detected'].index(1)
        fig.add_trace(go.Scatter(
            x=[data['time'][idx]],
            y=[data['pwm'][idx]],
            mode='markers',
            name='Motion Detected',
            marker=dict(color='red', size=15, symbol='star')
        ))

    fig.update_layout(
        title='Motor PWM vs Time',
        xaxis_title='Time (ms)',
        yaxis_title='PWM Value',
        hovermode='x unified'
    )

    return fig
```

#### 5.2 Distance vs Time Graph
```python
@app.callback(
    Output('deadband-distance-graph', 'figure'),
    Input('graph-update-interval', 'n_intervals')
)
def update_distance_graph(n):
    data = data_manager.deadband_history

    fig = go.Figure()

    # Distance measurement
    fig.add_trace(go.Scatter(
        x=data['time'],
        y=data['distance'],
        mode='lines',
        name='Current Distance',
        line=dict(color='green', width=2)
    ))

    # Initial distance reference line
    if len(data['initial_distance']) > 0:
        fig.add_trace(go.Scatter(
            x=data['time'],
            y=data['initial_distance'],
            mode='lines',
            name='Initial Distance',
            line=dict(color='gray', width=1, dash='dash')
        ))

    # Motion threshold bands
    if len(data['initial_distance']) > 0:
        threshold = 0.08  # Get from UI state
        initial = data['initial_distance'][0]
        fig.add_hrect(
            y0=initial - threshold,
            y1=initial + threshold,
            fillcolor="yellow",
            opacity=0.2,
            line_width=0,
            annotation_text="Motion threshold"
        )

    fig.update_layout(
        title='Distance vs Time',
        xaxis_title='Time (ms)',
        yaxis_title='Distance (cm)',
        hovermode='x unified'
    )

    return fig
```

#### 5.3 PWM vs Distance Calibration Curve
```python
@app.callback(
    Output('deadband-curve-graph', 'figure'),
    Input('graph-update-interval', 'n_intervals')
)
def update_calibration_curve(n):
    data = data_manager.deadband_history

    fig = go.Figure()

    # Main calibration curve
    fig.add_trace(go.Scatter(
        x=data['pwm'],
        y=data['distance'],
        mode='lines+markers',
        name='Calibration Curve',
        line=dict(color='purple', width=2),
        marker=dict(size=4)
    ))

    # Mark deadband point
    if 1 in data['motion_detected']:
        idx = data['motion_detected'].index(1)
        deadband_pwm = data['pwm'][idx]
        deadband_distance = data['distance'][idx]

        fig.add_trace(go.Scatter(
            x=[deadband_pwm],
            y=[deadband_distance],
            mode='markers+text',
            name=f'Deadband = {deadband_pwm}',
            marker=dict(color='red', size=15, symbol='star'),
            text=[f'{deadband_pwm}'],
            textposition='top center'
        ))

        # Vertical line at deadband
        fig.add_vline(
            x=deadband_pwm,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Deadband: {deadband_pwm} PWM"
        )

    fig.update_layout(
        title='PWM vs Distance (Calibration Curve)',
        xaxis_title='Motor PWM',
        yaxis_title='Distance (cm)',
        hovermode='closest'
    )

    return fig
```

### 6. MQTT Result Handler

```python
def on_mqtt_message(client, userdata, msg):
    """Handle MQTT messages from ESP32"""
    topic = msg.topic
    payload = msg.payload.decode('utf-8')

    # ... existing handlers ...

    # NEW: Deadband calibration result
    if topic == "trenes/deadband/result":
        deadband_value = int(payload)
        data_manager.calibrated_deadband = deadband_value

        # Update UI via callback or store update
        websocket_messages.put({
            'type': 'deadband_result',
            'value': deadband_value
        })

        print(f"✓ Deadband calibration complete: {deadband_value} PWM")

    elif topic == "trenes/deadband/applied":
        applied_value = int(payload)
        print(f"✓ Deadband {applied_value} applied to PID mode")

    elif topic == "trenes/deadband/error":
        error_msg = payload
        print(f"⚠ Deadband calibration error: {error_msg}")
```

### 7. Result Display Callback

```python
@app.callback(
    Output('deadband-result', 'children'),
    Input('ws-message-store', 'data')  # Or use interval polling
)
def display_deadband_result(ws_data):
    """Display calibration result when complete"""
    if ws_data and ws_data.get('type') == 'deadband_result':
        value = ws_data['value']
        return f"{value} PWM"

    # Check data manager for latest result
    if hasattr(data_manager, 'calibrated_deadband'):
        return f"{data_manager.calibrated_deadband} PWM"

    return ""
```

## Testing Procedure

### 1. Upload Firmware
```bash
# Open Arduino IDE
# File → Open → tren_esp_unified_COMPLETE.ino
# Upload to ESP32
```

### 2. Start Dashboard
```bash
python train_control_platform.py
```

### 3. Run Calibration

**In Dashboard:**
1. Navigate to "Deadband Calibration" tab
2. Select direction (Forward recommended)
3. Set motion threshold (0.08 cm default)
4. Click "Start Calibration"
5. Watch real-time graphs:
   - PWM increases from 0
   - Distance stays constant
   - When motion detected, PWM stops
6. Result displayed: "XXX PWM"
7. Click "Apply to PID" to use in PID experiments

**Expected Behavior:**
- PWM increases: 0 → 50 → 100 → ... → ~300
- Distance constant: 10.52 → 10.52 → 10.52 → ...
- Motion detected: 10.52 → 10.48 (change > 0.08 cm)
- Result: "Deadband = 300 PWM" (approximately)

### 4. Verify CSV Data

```bash
# Check generated file
ls -la deadband_calibration_*.csv

# View contents
cat deadband_calibration_20241104_123456.csv
```

Expected format:
```csv
time_ms,pwm,distance_cm,initial_distance_cm,motion_detected
0,0,10.52,10.52,0
40,1,10.52,10.52,0
...
5200,130,10.48,10.52,1
```

### 5. Apply to PID Mode

1. Click "Apply to PID" button
2. Verify MQTT message: `trenes/deadband/applied = 300`
3. Start PID experiment
4. Verify PID uses new deadband value

## Advanced Features (Optional)

### 1. Bidirectional Calibration

Add button to test both directions:
```python
html.Button("Calibrate Both Directions", id='deadband-bidirectional-btn')

@app.callback(...)
def calibrate_bidirectional(n_clicks):
    # Test forward
    mqtt_client.publish("trenes/deadband/direction", "1")
    mqtt_client.publish("trenes/deadband/sync", "True")

    # Wait for completion...

    # Test reverse
    mqtt_client.publish("trenes/deadband/direction", "0")
    mqtt_client.publish("trenes/deadband/sync", "True")

    # Use max(forward, reverse)
```

### 2. Battery Voltage Tracking

Store deadband vs battery voltage:
```python
calibration_history = {
    8.4: 300,  # Full battery
    7.8: 320,  # 80% battery
    7.2: 350   # 60% battery
}
```

### 3. Automatic Recalibration

Trigger calibration automatically when:
- Battery voltage drops significantly
- PID performance degrades
- User requests via button

## File Structure

```
train_control/
├── tren_esp_unified_FIXED/
│   └── tren_esp_unified_COMPLETE.ino  ← New firmware
│
├── train_control_platform.py  ← Add deadband tab
│
├── deadband_calibration_*.csv  ← Generated data
│
└── DEADBAND_DASHBOARD_INTEGRATION.md  ← This file
```

## Summary Checklist

### Firmware:
- [x] Add DEADBAND_MODE to experiment modes
- [x] Implement loop_deadband_experiment()
- [x] Add MQTT topic handlers
- [x] Create send_udp_deadband_data()
- [x] Restore deadband=300 default
- [x] Remove safety cap

### Dashboard:
- [ ] Add "Deadband Calibration" tab
- [ ] Create control panel UI
- [ ] Add MQTT publish callbacks
- [ ] Implement UDP data parsing
- [ ] Create 3 visualization graphs
- [ ] Add CSV data logging
- [ ] Add "Apply to PID" functionality
- [ ] Test end-to-end workflow

### Documentation:
- [x] MQTT topics documented
- [x] UDP data format specified
- [x] Testing procedure outlined
- [x] Integration guide created

## Next Steps

1. **Test firmware standalone** (Serial monitor)
2. **Implement dashboard tab** (Python code)
3. **Test integration** (full workflow)
4. **Optimize parameters** (threshold, increment, delay)
5. **Add bidirectional testing** (optional)
6. **Document user workflow** (README update)

---

**Questions? Issues?**
- Check Serial monitor for ESP32 debug output
- Verify MQTT broker is running
- Check UDP port 5555 is not blocked
- Ensure ToF sensor is working (distance readings stable)
