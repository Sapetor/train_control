# Deadband Dashboard Integration Guide

## Overview

This guide explains how to integrate the Deadband Calibration tab into `train_control_platform.py`.

**Status**: All backend code is complete (DeadbandDataManager, MQTT topics). This guide shows how to add the UI and callbacks.

---

## Files Created

1. **`deadband_dashboard_code.py`** - UI code (create_deadband_tab method)
2. **`deadband_callbacks_code.py`** - Callback functions
3. **`DEADBAND_INTEGRATION_GUIDE.md`** - This file

---

## Integration Steps

### Step 1: Add Translation Keys

**Location**: Around line 1048 (Spanish) and line 1189 (English)

**Spanish Section** - Add after `'configure_step_first'`:
```python
# Deadband Calibration
'deadband_tab': '🔧 Calibración Deadband',
'deadband_title': 'Calibración de Zona Muerta',
'deadband_config': 'Configuración de Calibración',
'start_calibration': 'Iniciar Calibración',
'stop_calibration': 'Detener Calibración',
'motion_threshold': 'Umbral de Movimiento (cm)',
'deadband_direction': 'Dirección',
'calibration_result': 'Resultado de Calibración',
'apply_to_pid': 'Aplicar a PID',
'deadband_value': 'Valor Deadband',
'calibration_in_progress': '🔄 Calibración en progreso...',
'calibration_complete': '✓ Calibración completa',
'deadband_pwm_graph': 'PWM vs Tiempo',
'deadband_distance_graph': 'Distancia vs Tiempo',
'deadband_curve_graph': 'Curva de Calibración (PWM vs Distancia)',
'pwm_value': 'PWM',
'initial_distance': 'Distancia Inicial',
'motion_detected': 'Movimiento Detectado',
'calibrating': 'Calibrando...',
'deadband_applied': '✓ Deadband aplicado al modo PID',
```

**English Section** - Add after step response translations (around line 1189):
```python
# Deadband Calibration
'deadband_tab': '🔧 Deadband Calibration',
'deadband_title': 'Deadband Calibration',
'deadband_config': 'Calibration Configuration',
'start_calibration': 'Start Calibration',
'stop_calibration': 'Stop Calibration',
'motion_threshold': 'Motion Threshold (cm)',
'deadband_direction': 'Direction',
'calibration_result': 'Calibration Result',
'apply_to_pid': 'Apply to PID',
'deadband_value': 'Deadband Value',
'calibration_in_progress': '🔄 Calibration in progress...',
'calibration_complete': '✓ Calibration complete',
'deadband_pwm_graph': 'PWM vs Time',
'deadband_distance_graph': 'Distance vs Time',
'deadband_curve_graph': 'Calibration Curve (PWM vs Distance)',
'pwm_value': 'PWM',
'initial_distance': 'Initial Distance',
'motion_detected': 'Motion Detected',
'calibrating': 'Calibrating...',
'deadband_applied': '✓ Deadband applied to PID mode',
```

---

### Step 2: Add Tab to Tabs List

**Location**: Around line 1677 in `create_layout()` method

**Find this:**
```python
dcc.Tabs(id='main-tabs', value='control-tab', children=[
    dcc.Tab(label=self.t('network_tab'), value='network-tab'),
    dcc.Tab(label=self.t('control_tab'), value='control-tab'),
    dcc.Tab(label=self.t('step_response_tab'), value='step-response-tab'),
    dcc.Tab(label=self.t('data_tab'), value='data-tab')
]),
```

**Replace with:**
```python
dcc.Tabs(id='main-tabs', value='control-tab', children=[
    dcc.Tab(label=self.t('network_tab'), value='network-tab'),
    dcc.Tab(label=self.t('control_tab'), value='control-tab'),
    dcc.Tab(label=self.t('step_response_tab'), value='step-response-tab'),
    dcc.Tab(label=self.t('deadband_tab'), value='deadband-tab'),
    dcc.Tab(label=self.t('data_tab'), value='data-tab')
]),
```

---

### Step 3: Add Tab Rendering Case

**Location**: Around line 2180 in `render_tab_content` callback

**Find this:**
```python
def render_tab_content(active_tab, language_data):
    if language_data:
        self.current_language = language_data.get('language', 'en')

    if active_tab == 'network-tab':
        return self.create_network_tab()
    elif active_tab == 'control-tab':
        return self.create_control_tab()
    elif active_tab == 'data-tab':
        return self.create_data_tab()
    elif active_tab == 'step-response-tab':
        return self.create_step_response_tab()
    return html.Div(self.t('tab_not_found'))
```

**Replace with:**
```python
def render_tab_content(active_tab, language_data):
    if language_data:
        self.current_language = language_data.get('language', 'en')

    if active_tab == 'network-tab':
        return self.create_network_tab()
    elif active_tab == 'control-tab':
        return self.create_control_tab()
    elif active_tab == 'data-tab':
        return self.create_data_tab()
    elif active_tab == 'step-response-tab':
        return self.create_step_response_tab()
    elif active_tab == 'deadband-tab':
        return self.create_deadband_tab()
    return html.Div(self.t('tab_not_found'))
```

---

### Step 4: Add create_deadband_tab Method

**Location**: After `create_step_response_tab()` method (around line 2045)

**Copy the entire `create_deadband_tab` method from `deadband_dashboard_code.py`**

The method signature is:
```python
def create_deadband_tab(self):
    """Create deadband calibration tab"""
    # ... (full code in deadband_dashboard_code.py)
```

---

### Step 5: Add Callbacks

**Location**: In `setup_callbacks()` method, after step response callbacks (around line 2700)

**Copy all 5 callbacks from `deadband_callbacks_code.py`:**

1. `handle_deadband_calibration` - Start/stop and status
2. `apply_deadband_to_pid` - Apply button
3. `update_deadband_pwm_graph` - PWM vs Time
4. `update_deadband_distance_graph` - Distance vs Time
5. `update_deadband_curve_graph` - PWM vs Distance curve

---

### Step 6: Update Mode Indicator (Optional)

**Location**: Around line 2067 in `update_mode_indicator` callback

**Find this:**
```python
def update_mode_indicator(active_tab, language_data):
    """Update the mode indicator badge based on active tab"""
    is_step = active_tab == 'step-response-tab'
    mode_text = 'Step Response' if is_step else 'PID Control'
    badge_color = '#28A745' if is_step else '#007BFF'
```

**Replace with:**
```python
def update_mode_indicator(active_tab, language_data):
    """Update the mode indicator badge based on active tab"""
    if active_tab == 'step-response-tab':
        mode_text = 'Step Response'
        badge_color = '#28A745'
    elif active_tab == 'deadband-tab':
        mode_text = 'Deadband Cal'
        badge_color = '#FFA500'  # Orange
    else:
        mode_text = 'PID Control'
        badge_color = '#007BFF'
```

---

### Step 7: Handle Deadband Result via MQTT

**Location**: In the MQTT callback handler (MQTTParameterSync class around line 240)

Add these topic handlers to `on_message` method:

```python
def on_message(self, client, userdata, msg):
    try:
        topic = msg.topic
        value = msg.payload.decode('utf-8')

        # ... existing handlers ...

        # Deadband calibration result
        elif topic == MQTT_TOPICS['deadband_result']:
            deadband_value = int(value)
            if hasattr(self, 'dashboard') and hasattr(self.dashboard, 'deadband_data_manager'):
                self.dashboard.deadband_data_manager.calibrated_deadband = deadband_value
            print(f"✓ Deadband calibration complete: {deadband_value} PWM")

        # Deadband applied confirmation
        elif topic == MQTT_TOPICS['deadband_applied']:
            applied_value = int(value)
            print(f"✓ Deadband {applied_value} applied to PID mode")

        # Deadband error
        elif topic == MQTT_TOPICS['deadband_error']:
            error_msg = value
            print(f"⚠ Deadband calibration error: {error_msg}")

    except Exception as e:
        print(f"MQTT message error: {e}")
```

---

## Testing the Integration

### 1. Start Dashboard
```bash
python train_control_platform.py
```

### 2. Upload Firmware
Upload `tren_esp_unified_COMPLETE.ino` to ESP32

### 3. Configure Network
- Go to Network tab
- Select interface
- Apply configuration

### 4. Run Calibration

**In Dashboard:**
1. Navigate to "Deadband Calibration" tab (🔧)
2. Select direction (Forward/Reverse)
3. Set motion threshold (default: 0.08 cm)
4. Click "Start Calibration"
5. Watch real-time graphs:
   - PWM increases from 0
   - Distance stays constant
   - When motion detected, PWM stops and result shows
6. Click "Apply to PID" to use in PID experiments

**Expected Behavior:**
- PWM increases: 0 → 50 → 100 → ... → ~300
- Distance constant: 10.52 → 10.52 → 10.52...
- Motion detected: Distance changes > threshold
- Result displayed: "300 PWM" (approximately)
- CSV file created: `deadband_calibration_YYYYMMDD_HHMMSS.csv`

---

## Troubleshooting

### Issue: Tab doesn't appear
- **Check**: Translation keys added correctly
- **Check**: Tab added to dcc.Tabs list
- **Check**: Correct label name: `self.t('deadband_tab')`

### Issue: Graphs not updating
- **Check**: Callbacks added to `setup_callbacks()`
- **Check**: Data manager initialized: `self.deadband_data_manager`
- **Check**: UDP receiver switched: `set_data_manager()`

### Issue: No data received
- **Check**: Firmware uploaded correctly
- **Check**: Network configured
- **Check**: MQTT topics match between firmware and dashboard
- **Check**: UDP port 5555 not blocked

### Issue: Calibration doesn't start
- **Check**: MQTT broker running
- **Check**: ESP32 connected to WiFi
- **Check**: MQTT sync message sent: `trenes/deadband/sync = "True"`

### Issue: Result not showing
- **Check**: MQTT callback handling `deadband_result` topic
- **Check**: `calibrated_deadband` variable updated
- **Check**: Result display callback triggers on interval

---

## Code Structure Summary

```
train_control_platform.py
├── MQTT_TOPICS (✓ Already added - line 94-104)
│   └── deadband_sync, deadband_result, etc.
│
├── DeadbandDataManager (✓ Already added - line 660-765)
│   ├── __init__()
│   ├── create_deadband_csv()
│   ├── add_data() - Parses 5-field CSV
│   └── clear_history()
│
├── TrainControlDashboard
│   ├── __init__() (✓ Already added - line 869)
│   │   └── self.deadband_data_manager = DeadbandDataManager()
│   │
│   ├── translations (⏳ TO ADD)
│   │   ├── Spanish: deadband_tab, deadband_title, etc.
│   │   └── English: deadband_tab, deadband_title, etc.
│   │
│   ├── create_layout() (⏳ TO ADD)
│   │   └── dcc.Tab(label=self.t('deadband_tab'), ...)
│   │
│   ├── create_deadband_tab() (⏳ TO ADD)
│   │   ├── Configuration panel
│   │   ├── Start/Stop buttons
│   │   ├── Result display
│   │   └── 3 graphs
│   │
│   ├── setup_callbacks() (⏳ TO ADD)
│   │   ├── render_tab_content → case 'deadband-tab'
│   │   ├── handle_deadband_calibration
│   │   ├── apply_deadband_to_pid
│   │   ├── update_deadband_pwm_graph
│   │   ├── update_deadband_distance_graph
│   │   └── update_deadband_curve_graph
│   │
│   └── update_mode_indicator() (⏳ TO ADD)
│       └── case 'deadband-tab' → Orange badge
│
└── MQTTParameterSync (⏳ TO ADD)
    └── on_message()
        ├── deadband_result handler
        ├── deadband_applied handler
        └── deadband_error handler
```

---

## Summary Checklist

- [x] Backend complete: DeadbandDataManager, MQTT topics, data manager
- [ ] Add Spanish translations (Step 1)
- [ ] Add English translations (Step 1)
- [ ] Add tab to tabs list (Step 2)
- [ ] Add render case (Step 3)
- [ ] Add create_deadband_tab() method (Step 4)
- [ ] Add 5 callbacks (Step 5)
- [ ] Update mode indicator (Step 6)
- [ ] Add MQTT handlers (Step 7)
- [ ] Test end-to-end

---

## Quick Integration Script

For faster integration, you can use this Python script to make the changes automatically:

```bash
# Backup first!
cp train_control_platform.py train_control_platform_backup.py

# Run integration script (to be created)
python integrate_deadband.py
```

Would you like me to create an automated integration script?

---

## Next Steps

1. **Make the modifications** listed in Steps 1-7
2. **Test the dashboard** - verify tab appears
3. **Test calibration** - upload firmware and run
4. **Verify graphs** - check real-time updates
5. **Test apply** - apply deadband to PID mode
6. **Check CSV** - verify data logging

---

## Support

If you encounter issues:
1. Check console for errors (`python train_control_platform.py`)
2. Check browser console (F12 → Console tab)
3. Check Serial monitor for ESP32 output
4. Verify MQTT broker is running
5. Check UDP port 5555 is accessible

---

**Implementation time**: ~30 minutes for manual integration
**Alternative**: Automated script can do it in seconds

Let me know if you want the automated integration script!
